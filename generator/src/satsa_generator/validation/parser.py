"""Parse-back validation logic for M3 tests."""

import contextlib
import csv
import json
from pathlib import Path
from uuid import UUID

from satsa_generator.profiles.catalog import get_profile


def parse_and_validate(
    source_exports_root: Path,
    oracle_root: Path,
    profile_id: str,
    evidence_family: str,
) -> None:
    """Parse generated source artifacts back into canonical state and validate against oracle."""
    profile = get_profile(profile_id)
    fmt = profile.get_format(evidence_family)
    ext = fmt.lower()

    source_path = source_exports_root / f"{evidence_family}_{profile_id.lower()}.{ext}"
    oracle_path = oracle_root / f"{profile_id.lower().replace('-', '_')}_oracle.json"

    if not source_path.exists():
        # Family wasn't rendered by this profile
        return

    # Load Oracle Expectation
    oracle_data = json.loads(oracle_path.read_text(encoding="utf-8"))
    expected_by_id = {
        UUID(r["canonical_record_id"]): r
        for r in oracle_data
        if r["canonical_family"] == evidence_family
    }

    # Load Index to know which record is which
    index_path = oracle_root / f"{profile_id.lower().replace('-', '_')}_index.json"
    index_data = json.loads(index_path.read_text(encoding="utf-8"))
    locators_to_canonical = {
        idx["source_record_locator"]: UUID(idx["canonical_record_id"])
        for idx in index_data
        if idx["evidence_family"] == evidence_family
    }

    # Parse file
    records = []
    if ext == "csv":
        with source_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            records = list(reader)
    elif ext == "json":
        records = json.loads(source_path.read_text(encoding="utf-8"))
    elif ext == "jsonl":
        lines = source_path.read_text(encoding="utf-8").strip().split("\n")
        records = [json.loads(line) for line in lines if line]

    assert len(records) == len(expected_by_id), "Record count mismatch"

    # Reconstruct
    family_map = profile.family_mappings.get(evidence_family, {})

    for idx, row in enumerate(records):
        locator = f"row:{idx + 1}" if ext == "csv" else f"[{idx}]"
        canonical_id = locators_to_canonical.get(locator)
        if not canonical_id:
            raise ValueError(f"No index found for {locator}")

        expected_record = expected_by_id[canonical_id]

        for can_field, expected_val in expected_record["fields"].items():
            fmap = family_map.get(can_field)
            if fmap and not fmap.is_present:
                continue

            # Determine source name and path
            if fmap:
                source_name = fmap.source_name
                path = fmap.path
            else:
                path = None
                if profile.case_naming == "pascal_case":
                    source_name = "".join(x.capitalize() for x in can_field.split("_"))
                elif profile.case_naming in ("camel_case", "mixed"):
                    parts = can_field.split("_")
                    source_name = parts[0] + "".join(x.capitalize() for x in parts[1:])
                else:
                    source_name = can_field

            # Extract raw val
            if path and ext != "csv":
                current = row
                for p in path:
                    current = current.get(p, {})
                raw_val = current if current != {} else None
            else:
                raw_val = row.get(source_name)

            if ext == "csv" and raw_val == "":
                raw_val = None

            # Handle reverse vocab mapping
            if fmap and fmap.vocabulary and raw_val is not None:
                # Need to convert raw_val to correct type for dictionary key
                # CSV parsing yields strings, so we might need type casting if vocab expects int
                vocab_map = fmap.vocabulary.source_to_canonical

                # Check if it matches exactly
                if raw_val in vocab_map:
                    raw_val = vocab_map[raw_val]
                else:
                    # Attempt string-to-int conversion if needed
                    matched = False
                    for k, v in vocab_map.items():
                        if str(k) == str(raw_val):
                            raw_val = v
                            matched = True
                            break
                    if not matched and fmap.vocabulary.on_unknown == "fail":
                        raise ValueError(f"Unmapped vocabulary value during parse-back: {raw_val}")

            # Compare against oracle expectation
            if expected_val is None and fmap and fmap.default_if_missing is not None:
                expected_val = fmap.default_if_missing

            # Normalization comparisons (e.g. string casting for UUIDs/times)
            if expected_val is not None:
                if isinstance(expected_val, list):
                    if isinstance(raw_val, str):
                        with contextlib.suppress(Exception):
                            raw_val = json.loads(raw_val)

                    if isinstance(raw_val, list):
                        raw_set = {str(x) for x in raw_val}
                        exp_set = {str(x) for x in expected_val}
                        if raw_set == exp_set and len(raw_val) == len(expected_val):
                            continue  # bypass further comparison

                        err_msg = (
                            f"Parse-back failure for {canonical_id} field {can_field}: "
                            f"expected '{expected_val}', got '{raw_val}'"
                        )
                        raise ValueError(err_msg)

                if isinstance(expected_val, bool) and isinstance(raw_val, str):
                    raw_val = raw_val.lower() == "true"
                elif (
                    isinstance(expected_val, int)
                    and not isinstance(expected_val, bool)
                    and isinstance(raw_val, str)
                ):
                    raw_val = int(raw_val)
                elif isinstance(expected_val, float) and isinstance(raw_val, str):
                    raw_val = float(raw_val)
                elif raw_val is not None:
                    raw_val = str(raw_val)
                    expected_val = str(expected_val)
                    if (
                        can_field.endswith("_utc")
                        or can_field.endswith("at")
                        or can_field == "profile_effective_start_at_utc"
                    ):
                        ts_format = profile.get_timestamp_format(evidence_family)
                        tz_name = profile.get_timezone(evidence_family)
                        if ts_format == "iso_z" and "+00:00" in expected_val:
                            expected_val = expected_val.replace("+00:00", "Z")
                        elif ts_format in ("iso_offset", "iso_offset_ms"):
                            expected_val = expected_val.replace("Z", "+00:00")
                        elif ts_format == "local_iana":
                            from datetime import datetime

                            try:
                                import zoneinfo

                                dt_str = expected_val.replace("Z", "+00:00")
                                dt = datetime.fromisoformat(dt_str)
                                dt_local = dt.astimezone(zoneinfo.ZoneInfo(tz_name or "UTC"))
                                expected_val = dt_local.strftime("%Y-%m-%d %H:%M:%S")
                            except Exception:
                                expected_val = (
                                    expected_val.replace("+00:00", "")
                                    .replace("Z", "")
                                    .replace("T", " ")
                                )
                        elif ts_format == "date_only":
                            expected_val = expected_val[:10]
            if raw_val != expected_val:
                err_msg = (
                    f"Parse-back failure for {canonical_id} field {can_field}: "
                    f"expected '{expected_val}', got '{raw_val}'"
                )
                raise ValueError(err_msg)

        for rel_name, expected_rel in expected_record.get("relationships", {}).items():
            fmap = family_map.get(rel_name)
            if fmap and not fmap.is_present:
                continue

            if fmap:
                source_name = fmap.source_name
                path = fmap.path
            else:
                path = None
                if profile.case_naming == "pascal_case":
                    source_name = "".join(x.capitalize() for x in rel_name.split("_"))
                elif profile.case_naming in ("camel_case", "mixed"):
                    parts = rel_name.split("_")
                    source_name = parts[0] + "".join(x.capitalize() for x in parts[1:])
                else:
                    source_name = rel_name

            # Extract raw val
            if path and ext != "csv":
                current = row
                for p in path:
                    current = current.get(p, {})
                raw_val = current if current != {} else None
            else:
                raw_val = row.get(source_name)

            if ext == "csv" and raw_val == "":
                raw_val = None

            if raw_val is not None:
                if isinstance(expected_rel, list):
                    if isinstance(raw_val, str):
                        with contextlib.suppress(Exception):
                            raw_val = json.loads(raw_val)

                    if not isinstance(raw_val, list):
                        msg = (
                            f"Parse-back rel failure {canonical_id} rel {rel_name}: "
                            f"expected list, got '{type(raw_val)}'"
                        )
                        raise ValueError(msg)

                    raw_set = {str(x) for x in raw_val}
                    exp_set = {str(x) for x in expected_rel}
                    if raw_set != exp_set:
                        msg = (
                            f"Parse-back rel failure {canonical_id} rel {rel_name}: "
                            f"expected {exp_set}, got {raw_set}"
                        )
                        raise ValueError(msg)

                    if len(raw_val) != len(expected_rel):
                        msg = (
                            f"Parse-back rel failure {canonical_id} rel {rel_name}: "
                            f"expected length {len(expected_rel)}, got {len(raw_val)}"
                        )
                        raise ValueError(msg)
                else:
                    if str(raw_val) != str(expected_rel):
                        err_msg2 = (
                            f"Parse-back rel failure {canonical_id} rel {rel_name}: "
                            f"expected '{expected_rel}', got '{raw_val}'"
                        )
                        raise ValueError(err_msg2)
            elif (
                expected_rel is not None
                and expected_rel != []
                and expected_rel != set()
                and (fmap is None or fmap.is_present)
            ):
                raise ValueError(
                    f"Parse-back rel failure {canonical_id} rel {rel_name}: "
                    f"expected '{expected_rel}', got missing"
                )
