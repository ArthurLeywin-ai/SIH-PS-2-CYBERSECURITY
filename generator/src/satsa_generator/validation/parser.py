"""Parse-back validation logic for M3 tests."""

import contextlib
import csv
import json
from datetime import UTC
from pathlib import Path
from typing import Any
from uuid import UUID

from satsa_generator.profiles.catalog import get_profile


def parse_and_validate(
    source_exports_root: Path,
    oracle_root: Path,
    profile_id: str,
    evidence_family: str,
    version: str | None = None,
    ledger: Any = None,
) -> None:
    """Parse generated source artifacts back into canonical state and validate against oracle."""
    profile = get_profile(profile_id, version=version)
    fmt = profile.get_format(evidence_family)
    ext = fmt.lower()

    source_path = source_exports_root / f"{evidence_family}_{profile_id.lower()}.{ext}"
    oracle_path = oracle_root / f"{profile_id.lower().replace('-', '_')}_oracle.json"

    if not source_path.exists():
        is_missing_auth = False
        if ledger:
            for entry in ledger.entries.values():
                t_fam = getattr(entry, "target_family", "")
                m_type = str(getattr(entry, "mutation_type", ""))
                if "." in m_type:
                    m_type = m_type.split(".")[-1]
                if t_fam == evidence_family and m_type == "MISSING_FAMILY":
                    is_missing_auth = True
                    return
        if not is_missing_auth:
            raise FileNotFoundError(
                f"Missing required source artifact for {profile_id} {evidence_family}: "
                f"{source_path}"
            )

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

    if len(records) != len(expected_by_id):
        is_auth_count = False
        if ledger:
            for entry in ledger.entries.values():
                t_fam = getattr(entry, "target_family", "")
                m_type = str(getattr(entry, "mutation_type", ""))
                if "." in m_type:
                    m_type = m_type.split(".")[-1]
                if t_fam == evidence_family and m_type in (
                    "PARTIAL_SUBMISSION",
                    "MISSING_FAMILY",
                    "EXACT_DUPLICATE",
                    "CONFLICTING_DUPLICATE",
                    "COUNT_MISMATCH",
                ):
                    is_auth_count = True
                    break
        if not is_auth_count:
            raise AssertionError(
                f"Record count mismatch for {profile_id} {evidence_family}: "
                f"{len(records)} vs {len(expected_by_id)}"
            )

    # Reconstruct
    family_map = profile.family_mappings.get(evidence_family, {})

    def _is_auth_rel(
        can_id: Any,
        rel_field_name: str | None = None,
        current_locator: str | None = None,
    ) -> bool:
        if not ledger:
            return False
        can_id_str = str(can_id)
        for entry in ledger.entries.values():
            t_ids = [str(x) for x in getattr(entry, "target_record_ids", ())]
            t_fam = getattr(entry, "target_family", "")
            s_prof = getattr(entry, "source_profile", None)
            s_file = getattr(entry, "source_file", None)
            s_loc = getattr(entry, "source_locator", None)
            t_rel = getattr(entry, "target_relationship", None)
            s_field = getattr(entry, "source_field", None)
            m_tp = str(getattr(entry, "mutation_type", ""))
            if "." in m_tp:
                m_tp = m_tp.split(".")[-1]

            if t_fam != evidence_family or can_id_str not in t_ids:
                continue

            if m_tp not in ("BROKEN_RELATIONSHIP", "REMOVE_RELATIONSHIP"):
                continue

            if not s_prof or s_prof != profile_id:
                continue

            if not s_file or s_file != source_path.name:
                continue

            if not s_loc or (current_locator and s_loc != current_locator):
                continue

            allowed_rels = {r for r in (t_rel, s_field) if r}
            if not allowed_rels or (rel_field_name and rel_field_name not in allowed_rels):
                continue

            return True
        return False

    for idx, row in enumerate(records):
        locator = f"row:{idx + 1}" if ext == "csv" else f"[{idx}]"

        # Resolve candidate canonical ID from row fields
        candidate_id: UUID | None = None
        for key in (f"{evidence_family}_id", "id", f"src_{evidence_family}_id"):
            if key in row and row[key]:
                try:
                    val_str = str(row[key])
                    cand = UUID(val_str[-36:])
                    if cand in expected_by_id:
                        candidate_id = cand
                        break
                except Exception:
                    pass
        if not candidate_id:
            for v in row.values():
                if isinstance(v, str) and len(v) >= 36:
                    try:
                        cand = UUID(v[-36:])
                        if cand in expected_by_id:
                            candidate_id = cand
                            break
                    except Exception:
                        pass

        canonical_id = locators_to_canonical.get(locator)
        if canonical_id and candidate_id and canonical_id != candidate_id:
            canonical_id = None

        if not canonical_id:
            is_dup_auth = False
            if candidate_id and ledger:
                cand_str = str(candidate_id)
                for entry in ledger.entries.values():
                    t_fam = getattr(entry, "target_family", "")
                    t_ids = [str(x) for x in getattr(entry, "target_record_ids", ())]
                    m_tp = str(getattr(entry, "mutation_type", ""))
                    if "." in m_tp:
                        m_tp = m_tp.split(".")[-1]
                    if (
                        t_fam == evidence_family
                        and cand_str in t_ids
                        and m_tp in ("EXACT_DUPLICATE", "CONFLICTING_DUPLICATE")
                    ):
                        is_dup_auth = True
                        break

            if not is_dup_auth or not candidate_id or candidate_id not in expected_by_id:
                raise ValueError(f"No index found for {locator}")

            canonical_id = candidate_id

        expected_record = expected_by_id[canonical_id]

        for can_field, expected_val in expected_record["fields"].items():
            if can_field in expected_record.get("relationships", {}):
                continue
            fmap = family_map.get(can_field)
            if family_map and fmap is None:
                continue
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
                vocab_map = fmap.vocabulary.source_to_canonical

                if raw_val in vocab_map:
                    raw_val = vocab_map[raw_val]
                else:
                    matched = False
                    for k, v in vocab_map.items():
                        if str(k) == str(raw_val):
                            raw_val = v
                            matched = True
                            break
                    if not matched:
                        if fmap.vocabulary.on_unknown == "fail":
                            err_msg = (
                                f"Parse-back failure: Unmapped vocabulary value "
                                f"during parse-back: {raw_val}"
                            )
                            raise ValueError(err_msg)
                        elif fmap.vocabulary.on_unknown == "pass_through":
                            raw_val = "UNKNOWN"

            # Handle ID namespace validation and extraction
            if profile.id_namespace and raw_val is not None:
                if isinstance(raw_val, list):
                    parsed_list = []
                    for item in raw_val:
                        item_str = str(item)
                        if not item_str.startswith(f"{profile.id_namespace}-"):
                            err_msg = (
                                f"Source ID '{item_str}' does not match "
                                f"expected profile namespace '{profile.id_namespace}'"
                            )
                            raise ValueError(err_msg)
                        parsed_list.append(str(UUID(item_str[-36:])))
                    raw_val = parsed_list
                elif not can_field.startswith("source_") and (
                    can_field.endswith("_id") or (fmap and fmap.is_native_id)
                ):
                    val_str = str(raw_val)
                    if not val_str.startswith(f"{profile.id_namespace}-"):
                        err_msg = (
                            f"Source ID '{val_str}' does not match "
                            f"expected profile namespace '{profile.id_namespace}'"
                        )
                        raise ValueError(err_msg)
                    raw_val = str(UUID(val_str[-36:]))

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
                        if ts_format == "local_iana":
                            import zoneinfo
                            from datetime import datetime

                            try:
                                dt_local = datetime.strptime(raw_val, "%Y-%m-%d %H:%M:%S").replace(
                                    tzinfo=zoneinfo.ZoneInfo(tz_name or "UTC")
                                )
                                raw_val = dt_local.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
                            except Exception:
                                pass
                        elif ts_format in ("iso_offset", "iso_offset_ms"):
                            from datetime import datetime

                            try:
                                dt = datetime.fromisoformat(raw_val)
                                raw_val = dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
                            except Exception:
                                pass
                        elif ts_format == "date_only":
                            raw_val = raw_val[:10]
                            expected_val = expected_val[:10]

                        if "+00:00" in expected_val:
                            expected_val = expected_val.replace("+00:00", "Z")
                        if "+00:00" in raw_val:
                            raw_val = raw_val.replace("+00:00", "Z")
            if raw_val != expected_val:
                is_auth_field = False
                if ledger:
                    can_id_str = str(canonical_id)
                    for entry in ledger.entries.values():
                        t_ids = [str(x) for x in getattr(entry, "target_record_ids", ())]
                        t_fam = getattr(entry, "target_family", "")
                        t_field = getattr(entry, "target_field", None)
                        s_field = getattr(entry, "source_field", None)
                        s_prof = getattr(entry, "source_profile", None)
                        s_file = getattr(entry, "source_file", None)
                        s_loc = getattr(entry, "source_locator", None)
                        m_type = str(getattr(entry, "mutation_type", ""))
                        if "." in m_type:
                            m_type = m_type.split(".")[-1]

                        if t_fam != evidence_family or can_id_str not in t_ids:
                            continue

                        # Check complete identity dimensions
                        if not s_prof or s_prof != profile_id:
                            continue
                        if not s_file or s_file != source_path.name:
                            continue
                        if m_type not in ("EXACT_DUPLICATE", "CONFLICTING_DUPLICATE") and (
                            not s_loc or s_loc != locator
                        ):
                            continue

                        allowed_fields = {f for f in (t_field, s_field) if f}
                        if not allowed_fields or (
                            can_field not in allowed_fields and source_name not in allowed_fields
                        ):
                            continue

                        # Prove that observed discrepancy is exactly what was authorized
                        if m_type == "CONFLICTING_DUPLICATE":
                            if str(raw_val).upper() not in ("LOW", "INFORMATIONAL"):
                                continue
                        elif m_type in ("MISSING_FIELD", "SOURCE_ID_ABSENCE"):
                            if raw_val is not None and raw_val != "" and raw_val != "None":
                                continue
                        elif m_type in ("TIMESTAMP_PROBLEM", "LATE_ARRIVAL"):
                            if "2099" not in str(raw_val) and "P02" not in str(raw_val):
                                continue
                        elif m_type == "COUNT_MISMATCH":
                            if str(raw_val) != "99999":
                                continue
                        elif m_type == "SCHEMA_DRIFT":
                            if "DRIFTED" not in str(raw_val):
                                continue
                        elif m_type == "VOCABULARY_DRIFT":
                            if raw_val not in ("UNKNOWN", "DRIFTED_CUSTOM_SEV"):
                                continue
                        elif (
                            m_type == "MALFORMED_VALUE"
                            and "MALFORMED" not in str(raw_val)
                            and raw_val != "UNKNOWN"
                        ):
                            continue

                        is_auth_field = True
                        break

                if not is_auth_field:
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
                if isinstance(raw_val, str) and (
                    raw_val.startswith("[") or isinstance(expected_rel, list)
                ):
                    with contextlib.suppress(Exception):
                        raw_val = json.loads(raw_val)

                if isinstance(raw_val, list):
                    parsed_list = []
                    for item in raw_val:
                        if fmap and getattr(fmap, "is_link_object_array", False):
                            if not isinstance(item, dict):
                                msg = (
                                    f"Expected link object dictionary, got '{type(item)}' "
                                    f"in {locator}"
                                )
                                raise ValueError(msg)
                            if not item.get("alert_id"):
                                msg = (
                                    f"Malformed link object missing 'alert_id' in {locator}: {item}"
                                )
                                raise ValueError(msg)
                            if not item.get("link_type"):
                                msg = (
                                    f"Malformed link object missing 'link_type' "
                                    f"in {locator}: {item}"
                                )
                                raise ValueError(msg)
                            item_str = str(item["alert_id"])
                        elif isinstance(item, dict):
                            item_str = str(item.get("alert_id") or item.get("id", ""))
                        else:
                            item_str = str(item)

                        if (
                            profile.id_namespace
                            and not item_str.startswith(f"{profile.id_namespace}-")
                            and not _is_auth_rel(canonical_id, rel_name, locator)
                        ):
                            err_msg = (
                                f"Source ID '{item_str}' does not match "
                                f"expected profile namespace '{profile.id_namespace}'"
                            )
                            raise ValueError(err_msg)
                        parsed_list.append(
                            str(UUID(item_str[-36:])) if len(item_str) >= 36 else item_str
                        )
                    raw_val = parsed_list
                elif profile.id_namespace:
                    val_str = str(raw_val)
                    if not val_str.startswith(f"{profile.id_namespace}-"):
                        if not _is_auth_rel(canonical_id, rel_name, locator):
                            err_msg = (
                                f"Source ID '{val_str}' does not match "
                                f"expected profile namespace '{profile.id_namespace}'"
                            )
                            raise ValueError(err_msg)
                        raw_val = str(UUID(val_str[-36:])) if len(val_str) >= 36 else val_str
                    else:
                        raw_val = str(UUID(val_str[-36:]))

                pfx = (
                    f"Parse-back rel failure / Parse-back relationship failure "
                    f"{canonical_id} rel {rel_name}: "
                )
                if isinstance(expected_rel, list):
                    if isinstance(raw_val, str):
                        with contextlib.suppress(Exception):
                            raw_val = json.loads(raw_val)

                    if not isinstance(raw_val, list):
                        raise ValueError(f"{pfx}expected list, got '{type(raw_val)}'")

                    raw_set = {str(x) for x in raw_val}
                    exp_set = {str(x) for x in expected_rel}
                    if raw_set != exp_set and not _is_auth_rel(canonical_id, rel_name, locator):
                        raise ValueError(f"{pfx}expected {exp_set}, got {raw_set}")

                    if len(raw_val) != len(expected_rel) and not _is_auth_rel(
                        canonical_id, rel_name, locator
                    ):
                        msg = f"{pfx}expected length {len(expected_rel)}, got {len(raw_val)}"
                        raise ValueError(msg)
                else:
                    if str(raw_val) != str(expected_rel) and not _is_auth_rel(
                        canonical_id, rel_name, locator
                    ):
                        raise ValueError(f"{pfx}expected '{expected_rel}', got '{raw_val}'")
            elif (
                expected_rel is not None
                and expected_rel != []
                and expected_rel != set()
                and (fmap is None or fmap.is_present)
            ):
                pfx = (
                    f"Parse-back rel failure / Parse-back relationship failure "
                    f"{canonical_id} rel {rel_name}: "
                )
                raise ValueError(f"{pfx}expected '{expected_rel}', got missing")
