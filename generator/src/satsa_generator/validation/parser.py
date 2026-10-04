"""Parse-back validation logic for M3 tests."""

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
    ext = profile.format.lower()
    if ext == "jsonl":
        ext = "jsonl"
    elif ext == "json":
        ext = "json"
    else:
        ext = "csv"

    source_path = source_exports_root / f"{evidence_family}_{profile_id.lower()}.{ext}"
    oracle_path = oracle_root / f"{profile_id.lower().replace('-', '_')}_oracle.json"

    if not source_path.exists():
        # Family wasn't rendered by this profile
        return

    # Load Oracle Expectation
    oracle_data = json.loads(oracle_path.read_text(encoding="utf-8"))
    expected_by_id = {UUID(r["canonical_record_id"]): r for r in oracle_data if r["canonical_family"] == evidence_family}

    # Load Index to know which record is which
    index_path = oracle_root / f"{profile_id.lower().replace('-', '_')}_index.json"
    index_data = json.loads(index_path.read_text(encoding="utf-8"))
    locators_to_canonical = {idx["source_record_locator"]: UUID(idx["canonical_record_id"]) for idx in index_data if idx["evidence_family"] == evidence_family}

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
        locator = f"row:{idx+1}" if ext == "csv" else f"[{idx}]"
        canonical_id = locators_to_canonical.get(locator)
        if not canonical_id:
            raise ValueError(f"No index found for {locator}")

        expected_record = expected_by_id[canonical_id]

        for can_field, fmap in family_map.items():
            if not fmap.is_present:
                continue

            # Extract raw val
            if fmap.path and ext != "csv":
                current = row
                for p in fmap.path:
                    current = current.get(p, {})
                raw_val = current if current != {} else None
            else:
                raw_val = row.get(fmap.source_name)

            # Handle reverse vocab mapping
            if fmap.vocabulary and raw_val is not None:
                # Need to convert raw_val to correct type for dictionary key
                # CSV parsing yields strings, so we might need type casting if vocab expects int
                vocab_map = fmap.vocabulary.source_to_canonical

                # Check if it matches exactly
                if raw_val in vocab_map:
                    raw_val = vocab_map[raw_val]
                else:
                    # Attempt string-to-int conversion if needed
                    for k, v in vocab_map.items():
                        if str(k) == str(raw_val):
                            raw_val = v
                            break

            # Compare against oracle expectation
            expected_val = expected_record["fields"].get(can_field)
            if expected_val is None and fmap.default_if_missing is not None:
                expected_val = fmap.default_if_missing

            # Normalization comparisons (e.g. string casting for UUIDs/times)
            if expected_val is not None:
                if isinstance(expected_val, int) and isinstance(raw_val, str):
                    raw_val = int(raw_val)
                elif isinstance(expected_val, float) and isinstance(raw_val, str):
                    raw_val = float(raw_val)
                elif raw_val is not None:
                    raw_val = str(raw_val)
                    expected_val = str(expected_val)
                    if can_field.endswith("_utc") or can_field.endswith("at") or can_field == "profile_effective_start_at_utc":
                        if profile.timestamp_format == "iso_z" and "+00:00" in expected_val:
                            expected_val = expected_val.replace("+00:00", "Z")
                        elif profile.timestamp_format == "iso_offset_ms":
                             expected_val = expected_val.replace("Z", "+00:00")
                        elif profile.timestamp_format == "local_iana":
                            expected_val = expected_val.replace("+00:00", "").replace("Z", "").replace("T", " ")
                        elif profile.timestamp_format == "date_only":
                            expected_val = expected_val[:10]
            if raw_val != expected_val:
                raise ValueError(f"Parse-back failure for {canonical_id} field {can_field}: expected '{expected_val}', got '{raw_val}'")
