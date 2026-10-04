"""Source-first canonical reconstruction from rendered source artifacts.

Reads rendered bytes directly from disk through reference parsers, applying
profile mappings, vocabulary transformations, timestamp normalization, and
relationship extraction to construct authoritative CanonicalOracle and provenance.
"""

from __future__ import annotations

import contextlib
import csv
import json
from datetime import UTC
from pathlib import Path
from typing import Any
from uuid import UUID

from satsa_generator.canonical.oracle import CanonicalOracle, CanonicalRecordState
from satsa_generator.profiles.models import ProfileDefinition
from satsa_generator.provenance.models import RelationshipProvenance

_ALL_FAMILIES = (
    "organization",
    "submission",
    "submission_manifest",
    "submission_family",
    "control_process_reference",
    "control_process_subject_link",
    "asset",
    "monitoring_coverage",
    "alert",
    "case",
    "case_alert_link",
    "investigation",
    "escalation",
    "action",
    "resolution",
    "closure",
    "exception",
    "process_change",
)


def reconstruct_family_from_disk(
    source_exports_root: Path,
    oracle_root: Path,
    profile: ProfileDefinition,
    family: str,
) -> tuple[list[CanonicalRecordState], list[RelationshipProvenance]]:
    """Parse a rendered family file from disk and reconstruct its canonical records."""
    fmt = profile.get_format(family)
    ext = fmt.lower()
    source_path = source_exports_root / f"{family}_{profile.profile_id.lower()}.{ext}"

    if not source_path.exists():
        err_msg = (
            f"Missing required source artifact for profile {profile.profile_id} "
            f"family '{family}': {source_path}"
        )
        raise FileNotFoundError(err_msg)

    # Load Index to map source locators to canonical IDs
    prefix = profile.profile_id.lower().replace("-", "_")
    index_path = oracle_root / f"{prefix}_index.json"
    if not index_path.exists():
        raise FileNotFoundError(f"Missing required index file: {index_path}")

    index_data = json.loads(index_path.read_text(encoding="utf-8"))
    locators_to_canonical = {
        idx["source_record_locator"]: UUID(idx["canonical_record_id"])
        for idx in index_data
        if idx["evidence_family"] == family
    }

    # Parse raw records from disk
    records: list[dict[str, Any]] = []
    if ext == "csv":
        with source_path.open("r", encoding="utf-8", newline="") as f:
            records = list(csv.DictReader(f))
    elif ext == "json":
        data = json.loads(source_path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            records = data
        elif isinstance(data, dict):
            records = [data]
    elif ext == "jsonl":
        lines = source_path.read_text(encoding="utf-8").strip().split("\n")
        records = [json.loads(line) for line in lines if line.strip()]

    family_map = profile.family_mappings.get(family, {})
    canonical_records: list[CanonicalRecordState] = []
    rel_provenance_list: list[RelationshipProvenance] = []

    for idx, row in enumerate(records):
        locator = f"row:{idx + 1}" if ext == "csv" else f"[{idx}]"
        canonical_id = locators_to_canonical.get(locator)
        if not canonical_id:
            raise ValueError(
                f"No index entry found for {family} locator '{locator}' in {index_path}"
            )

        fields: dict[str, Any] = {}
        relationships: dict[str, UUID | list[UUID]] = {}

        for can_field, fmap in family_map.items():
            if not fmap.is_present:
                if fmap.default_if_missing is not None:
                    fields[can_field] = fmap.default_if_missing
                continue

            # Extract raw value from row according to mapping path
            if fmap.path and ext != "csv":
                current: Any = row
                for p in fmap.path:
                    if isinstance(current, dict):
                        current = current.get(p)
                    else:
                        current = None
                        break
                raw_val = current
            else:
                raw_val = row.get(fmap.source_name)

            if ext == "csv" and raw_val == "":
                raw_val = None

            # Reverse vocabulary transformation
            if fmap.vocabulary and raw_val is not None:
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
                                f"Unmapped vocabulary value during "
                                f"canonical reconstruction: {raw_val}"
                            )
                            raise ValueError(err_msg)
                        elif fmap.vocabulary.on_unknown == "pass_through":
                            raw_val = "UNKNOWN"

            # Reverse ID namespace validation and extraction
            if profile.id_namespace and raw_val is not None:
                if isinstance(raw_val, list):
                    parsed_list = []
                    for item in raw_val:
                        if isinstance(item, dict):
                            alert_id_val = item.get("alert_id") or item.get("id")
                            if not alert_id_val:
                                err_msg = (
                                    f"Malformed link object missing alert_id in {locator}: {item}"
                                )
                                raise ValueError(err_msg)
                            item_str = str(alert_id_val)
                            if not item_str.startswith(f"{profile.id_namespace}-"):
                                err_msg = (
                                    f"Source ID '{item_str}' does not match "
                                    f"expected profile namespace '{profile.id_namespace}'"
                                )
                                raise ValueError(err_msg)
                            parsed_list.append(item_str[-36:])
                        else:
                            item_str = str(item)
                            if not item_str.startswith(f"{profile.id_namespace}-"):
                                err_msg = (
                                    f"Source ID '{item_str}' does not match "
                                    f"expected profile namespace '{profile.id_namespace}'"
                                )
                                raise ValueError(err_msg)
                            parsed_list.append(item_str[-36:])
                    raw_val = parsed_list
                elif not can_field.startswith("source_") and (
                    can_field.endswith("_id") or fmap.is_native_id
                ):
                    val_str = str(raw_val)
                    if not val_str.startswith(f"{profile.id_namespace}-"):
                        err_msg = (
                            f"Source ID '{val_str}' does not match "
                            f"expected profile namespace '{profile.id_namespace}'"
                        )
                        raise ValueError(err_msg)
                    raw_val = val_str[-36:]

            # Timestamp normalization to canonical UTC representation
            if raw_val is not None and (
                can_field.endswith("_utc")
                or can_field.endswith("at")
                or can_field == "profile_effective_start_at_utc"
            ):
                raw_val = str(raw_val)
                ts_format = profile.get_timestamp_format(family)
                tz_name = profile.get_timezone(family)
                if ts_format == "local_iana":
                    import zoneinfo
                    from datetime import datetime

                    with contextlib.suppress(Exception):
                        dt_local = datetime.strptime(raw_val, "%Y-%m-%d %H:%M:%S").replace(
                            tzinfo=zoneinfo.ZoneInfo(tz_name or "UTC")
                        )
                        raw_val = dt_local.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
                elif ts_format in ("iso_offset", "iso_offset_ms"):
                    from datetime import datetime

                    with contextlib.suppress(Exception):
                        dt = datetime.fromisoformat(raw_val)
                        raw_val = dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
                elif ts_format == "iso_z":
                    if "+00:00" in raw_val:
                        raw_val = raw_val.replace("+00:00", "Z")

            fields[can_field] = raw_val

            # Relationship extraction from source representation
            if fmap.is_reference_array or fmap.is_link_object_array or can_field == "alerts":
                if raw_val is not None:
                    if isinstance(raw_val, str):
                        with contextlib.suppress(Exception):
                            raw_val = json.loads(raw_val)
                    if isinstance(raw_val, list):
                        ref_ids = []
                        for x in raw_val:
                            if isinstance(x, dict):
                                alert_id_val = x.get("alert_id") or x.get("id")
                                if not alert_id_val:
                                    err_msg = (
                                        f"Malformed link object missing alert_id in {locator}: {x}"
                                    )
                                    raise ValueError(err_msg)
                                alert_id_str = str(alert_id_val)
                                if profile.id_namespace and not alert_id_str.startswith(
                                    f"{profile.id_namespace}-"
                                ):
                                    err_msg = (
                                        f"Source ID '{alert_id_str}' in link object does not "
                                        f"match expected profile namespace '{profile.id_namespace}'"
                                    )
                                    raise ValueError(err_msg)
                                ref_ids.append(UUID(alert_id_str[-36:]))
                            else:
                                ref_ids.append(UUID(str(x)[-36:]))
                        relationships["alerts"] = ref_ids
                        rel_provenance_list.append(
                            RelationshipProvenance(
                                source_file_path=str(source_path.name),
                                source_record_locator=locator,
                                source_relationship_field=fmap.source_name,
                                canonical_subject_id=canonical_id,
                                canonical_object_id=ref_ids,
                                relationship_type="alerts",
                            )
                        )
            elif can_field.endswith("_id") and can_field != f"{family}_id" and raw_val is not None:
                try:
                    target_uuid = UUID(str(raw_val)[-36:])
                    relationships[can_field] = target_uuid
                    rel_provenance_list.append(
                        RelationshipProvenance(
                            source_file_path=str(source_path.name),
                            source_record_locator=locator,
                            source_relationship_field=fmap.source_name,
                            canonical_subject_id=canonical_id,
                            canonical_object_id=target_uuid,
                            relationship_type=can_field,
                        )
                    )
                except (ValueError, TypeError):
                    pass

        canonical_records.append(
            CanonicalRecordState(
                canonical_record_id=canonical_id,
                canonical_family=family,
                fields=fields,
                relationships=relationships,
            )
        )

    return canonical_records, rel_provenance_list


def reconstruct_canonical_oracle_from_disk(
    source_exports_root: Path,
    oracle_root: Path,
    profile: ProfileDefinition,
    families: tuple[str, ...] = _ALL_FAMILIES,
) -> CanonicalOracle:
    """Reconstruct an entire CanonicalOracle strictly from rendered source artifacts on disk."""
    oracle = CanonicalOracle()
    all_rel_provenance: list[RelationshipProvenance] = []

    # 1. Parse and reconstruct each family independently from disk
    for family in families:
        records, rel_provenance = reconstruct_family_from_disk(
            source_exports_root, oracle_root, profile, family
        )
        all_rel_provenance.extend(rel_provenance)
        for record in records:
            oracle.register_expected_record(record)

    # 2. Cross-family relationship reconciliation (e.g. Case <-> Alert bidirectional links)
    case_alerts_map: dict[UUID, list[UUID]] = {}
    alert_case_map: dict[UUID, UUID] = {}

    # Gather case->alerts from case records (reference array)
    for rec in oracle.expected_records.values():
        if rec.canonical_family == "case" and "alerts" in rec.relationships:
            case_alerts = rec.relationships["alerts"]
            if isinstance(case_alerts, list):
                case_alerts_map[rec.canonical_record_id] = case_alerts
                for a_id in case_alerts:
                    alert_case_map[a_id] = rec.canonical_record_id

    # Gather alert->case from alert records (embedded foreign key)
    for rec in oracle.expected_records.values():
        if rec.canonical_family == "alert" and "case_id" in rec.relationships:
            c_id = rec.relationships["case_id"]
            if isinstance(c_id, UUID):
                alert_case_map[rec.canonical_record_id] = c_id
                if c_id not in case_alerts_map:
                    case_alerts_map[c_id] = []
                if rec.canonical_record_id not in case_alerts_map[c_id]:
                    case_alerts_map[c_id].append(rec.canonical_record_id)

    # Gather links from case_alert_link family if present
    for rec in oracle.expected_records.values():
        if rec.canonical_family == "case_alert_link":
            c_id = rec.fields.get("case_id")
            a_id = rec.fields.get("alert_id")
            if c_id and a_id:
                try:
                    c_uuid = UUID(str(c_id)[-36:])
                    a_uuid = UUID(str(a_id)[-36:])
                    alert_case_map[a_uuid] = c_uuid
                    if c_uuid not in case_alerts_map:
                        case_alerts_map[c_uuid] = []
                    if a_uuid not in case_alerts_map[c_uuid]:
                        case_alerts_map[c_uuid].append(a_uuid)
                except (ValueError, TypeError):
                    pass

    # Apply reconciled relationships to records
    reconciled_records: dict[UUID, CanonicalRecordState] = {}
    for rec_id, rec in oracle.expected_records.items():
        new_rels = dict(rec.relationships)
        if rec.canonical_family == "case" and rec_id in case_alerts_map:
            new_rels["alerts"] = case_alerts_map[rec_id]
        elif rec.canonical_family == "alert" and rec_id in alert_case_map:
            new_rels["case_id"] = alert_case_map[rec_id]

        reconciled_records[rec_id] = CanonicalRecordState(
            canonical_record_id=rec.canonical_record_id,
            canonical_family=rec.canonical_family,
            fields=rec.fields,
            relationships=new_rels,
        )

    return CanonicalOracle(expected_records=reconciled_records)
