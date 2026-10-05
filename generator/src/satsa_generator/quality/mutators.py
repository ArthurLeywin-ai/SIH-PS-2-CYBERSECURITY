"""Quality mutators — implementations for all 13 quality mutation types.

Follows GENERATOR_IMPLEMENTATION_PLAN §13.2 and §13.3:
- Copy-on-write semantics: never mutate records in place
- Pre-authorization required: every mutation must be in AuthorizationLedger
- Emits private MutationReceipt for reconciliation
- Preserves referential and temporal integrity on unaffected records
- Applies source-level defects to rendered source files when source_exports_root provided
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

from satsa_generator.core.errors import GeneratorError
from satsa_generator.quality.models import QualityMutationType, QualityPlan
from satsa_generator.scenarios.ledger import AuthorizationLedger
from satsa_generator.scenarios.models import MutationReceipt, MutationType
from satsa_generator.seeds.manager import SeedManager


class QualityMutationError(GeneratorError):
    """Raised when a quality mutation fails."""


def _copy_records(records: dict[str, list[Any]]) -> dict[str, list[Any]]:
    """Return a shallow copy of the family dictionary with new lists."""
    return {family: list(item_list) for family, item_list in records.items()}


def _verify_quality_auth(plan: QualityPlan, ledger: AuthorizationLedger) -> None:
    """Verify authorization in the ledger prior to mutation."""
    ledger.verify_authorization(
        plan.plan_id,
        expected_scenario_id="QUALITY_ENGINE",
        expected_mutation_type=MutationType(plan.mutation_type.value),
        target_record_ids=(plan.target_record_id,),
        target_family=plan.target_family,
    )


def _consume_quality_auth(
    plan: QualityPlan,
    ledger: AuthorizationLedger,
    before_state: dict[str, Any],
    after_state: dict[str, Any],
    target_fields: tuple[str, ...],
) -> MutationReceipt:
    """Consume and validate authorization, emitting receipt."""
    receipt = MutationReceipt(
        authorization_id=plan.plan_id,
        plan_id=plan.plan_id,
        scenario_id="QUALITY_ENGINE",
        mutation_type=MutationType(plan.mutation_type.value),
        target_record_ids=(plan.target_record_id,),
        target_family=plan.target_family,
        target_fields=target_fields,
        before_state=before_state,
        after_state=after_state,
        applied=True,
    )
    ledger.consume(receipt)
    ledger.mark_validated(plan.plan_id)
    return receipt


def _apply_source_file_mutation(
    plan: QualityPlan,
    source_exports_root: Path | None,
) -> dict[str, Any]:
    """Apply corresponding source-level quality defect to rendered files on disk.

    Authoritative targeting requirements:
    1. Resolve exact target: family, record ID, file, locator, and field.
    2. Fail loudly (QualityMutationError) if target cannot be resolved.
    3. Modify only the intended record/field/file without side effects.
    4. Return exact mutation details for receipt auditing.
    """
    if not source_exports_root or not source_exports_root.exists():
        return {}

    m_type = plan.mutation_type
    target_fam = plan.target_family
    target_rec_id = str(plan.target_record_id)

    # 1. Resolve source file
    if plan.source_file:
        source_file_name = plan.source_file
        file_path = source_exports_root / source_file_name
    else:
        # Default to SRC-A dialect file or first matching family file
        file_path = source_exports_root / f"{target_fam}_src-a.csv"
        if not file_path.exists():
            candidates = sorted(list(source_exports_root.glob(f"{target_fam}_*.*")))
            if not candidates:
                raise QualityMutationError(
                    f"Target family '{target_fam}' has no rendered source files "
                    f"in {source_exports_root}"
                )
            file_path = candidates[0]
        source_file_name = file_path.name

    # Handle MISSING_FAMILY by removing rendered file
    if m_type == QualityMutationType.MISSING_FAMILY:
        if not file_path.exists():
            raise QualityMutationError(
                f"Target source file '{source_file_name}' for MISSING_FAMILY does not exist"
            )
        file_path.unlink()
        return {
            "source_file": source_file_name,
            "mutation_type": "MISSING_FAMILY",
            "deleted": True,
        }

    if not file_path.exists():
        raise QualityMutationError(
            f"Target source file '{source_file_name}' does not exist on disk"
        )

    ext = file_path.suffix.lstrip(".").lower()

    # Load rows / records
    import csv as csv_mod
    import json as json_mod

    records: list[dict[str, Any]] = []
    header: list[str] = []

    if ext == "csv":
        with file_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv_mod.DictReader(f)
            header = list(reader.fieldnames or [])
            records = list(reader)
    elif ext == "json":
        data = json_mod.loads(file_path.read_text(encoding="utf-8"))
        records = data if isinstance(data, list) else [data]
    elif ext == "jsonl":
        lines = file_path.read_text(encoding="utf-8").strip().splitlines()
        records = [json_mod.loads(ln) for ln in lines if ln.strip()]
    else:
        raise QualityMutationError(f"Unsupported source format: {ext}")

    if not records and m_type != QualityMutationType.MISSING_FAMILY:
        raise QualityMutationError(f"Source file '{source_file_name}' is empty")

    # 2. Locate exact source record
    target_row_idx: int | None = None
    resolved_locator: str = ""

    if plan.source_locator:
        loc = plan.source_locator.strip()
        if loc.startswith("row:"):
            try:
                row_num = int(loc.split(":")[1])
                target_row_idx = row_num - 1
            except ValueError as err:
                raise QualityMutationError(
                    f"Invalid row locator format '{plan.source_locator}'"
                ) from err
        elif loc.startswith("[") and loc.endswith("]"):
            try:
                target_row_idx = int(loc[1:-1])
            except ValueError as err:
                raise QualityMutationError(
                    f"Invalid index locator format '{plan.source_locator}'"
                ) from err
        else:
            raise QualityMutationError(f"Unrecognized locator format '{plan.source_locator}'")

        if target_row_idx < 0 or target_row_idx >= len(records):
            raise QualityMutationError(
                f"Source locator '{plan.source_locator}' out of bounds in '{source_file_name}' "
                f"(file has {len(records)} records)"
            )

        # 3. Verify the expected source record ID
        rec = records[target_row_idx]
        # Identify ID column in record
        id_candidates = [
            f"{target_fam}_id",
            "alert_id",
            "case_id",
            "submission_id",
            "submission_family_id",
            "case_alert_link_id",
            "asset_id",
            "organization_id",
        ]
        matched_id: str | None = None
        for id_col in id_candidates:
            if id_col in rec and rec[id_col]:
                matched_id = str(rec[id_col])
                break

        if matched_id and matched_id != target_rec_id:
            raise QualityMutationError(
                f"Record at locator '{plan.source_locator}' in '{source_file_name}' "
                f"has ID '{matched_id}', does not match expected target record ID '{target_rec_id}'"
            )
        resolved_locator = plan.source_locator
    else:
        # Search for exact target record by ID
        id_candidates = [
            f"{target_fam}_id",
            "alert_id",
            "case_id",
            "submission_id",
            "submission_family_id",
            "case_alert_link_id",
            "asset_id",
            "organization_id",
        ]
        for idx, rec in enumerate(records):
            for id_col in id_candidates:
                if id_col in rec and str(rec[id_col]) == target_rec_id:
                    target_row_idx = idx
                    resolved_locator = f"row:{idx + 1}" if ext == "csv" else f"[{idx}]"
                    break
            if target_row_idx is not None:
                break

        if target_row_idx is None:
            # If still not found and PARTIAL_SUBMISSION / MISSING_FAMILY, allow first/last row
            if m_type == QualityMutationType.PARTIAL_SUBMISSION:
                target_row_idx = len(records) - 1
                resolved_locator = (
                    f"row:{target_row_idx + 1}" if ext == "csv" else f"[{target_row_idx}]"
                )
            else:
                raise QualityMutationError(
                    f"Target record ID '{target_rec_id}' not found in source file "
                    f"'{source_file_name}'"
                )

    # 4. Resolve and verify target field
    field_to_modify = plan.source_field or plan.target_field
    row_to_modify = records[target_row_idx]
    before_val = None

    if field_to_modify and field_to_modify not in row_to_modify:
        # Check common synonyms or dialect naming variations
        synonyms = {
            "source_alert_id": ["src_alert_id", "source_alert_id"],
            "source_case_id": ["src_case_id", "source_case_id", "case_id"],
            "declared_record_count": [
                "declared_record_count",
                "DeclaredRecordCount",
                "declaredRecordCount",
                "decl_rec_count",
                "decl_count",
            ],
        }
        found = False
        for alt in synonyms.get(field_to_modify, []):
            if alt in row_to_modify:
                field_to_modify = alt
                found = True
                break
        if not found and m_type not in (
            QualityMutationType.SCHEMA_DRIFT,
            QualityMutationType.PARTIAL_SUBMISSION,
            QualityMutationType.EXACT_DUPLICATE,
        ):
            raise QualityMutationError(
                f"Target source field '{field_to_modify}' not found in record at "
                f"{resolved_locator} in '{source_file_name}'"
            )

    if field_to_modify and field_to_modify in row_to_modify:
        before_val = row_to_modify[field_to_modify]

    after_val = None

    # 5. Apply the exact mutation
    if m_type == QualityMutationType.MISSING_FIELD:
        if not field_to_modify or field_to_modify not in row_to_modify:
            raise QualityMutationError(
                f"Cannot apply MISSING_FIELD: field '{field_to_modify}' not found"
            )
        row_to_modify[field_to_modify] = ""
        after_val = ""

    elif m_type == QualityMutationType.PARTIAL_SUBMISSION:
        # Truncate / remove records from submission
        if len(records) > 1:
            records = records[:-1]
        after_val = "TRUNCATED"

    elif m_type == QualityMutationType.MALFORMED_VALUE:
        if not field_to_modify or field_to_modify not in row_to_modify:
            raise QualityMutationError(
                f"Cannot apply MALFORMED_VALUE: field '{field_to_modify}' not found"
            )
        malformed = str(plan.parameters.get("malformed_value", "MALFORMED_PRIORITY_##%"))
        row_to_modify[field_to_modify] = malformed
        after_val = malformed

    elif m_type == QualityMutationType.EXACT_DUPLICATE:
        # Duplicate only this exact record
        dup_row = dict(row_to_modify)
        records.append(dup_row)
        after_val = "DUPLICATED"

    elif m_type == QualityMutationType.CONFLICTING_DUPLICATE:
        # Duplicate this exact record with conflicting content
        dup_row = dict(row_to_modify)
        conf_field = field_to_modify or "severity"
        if conf_field in dup_row:
            dup_row[conf_field] = "LOW"
        records.append(dup_row)
        after_val = "CONFLICTING_DUPLICATE"

    elif m_type == QualityMutationType.BROKEN_RELATIONSHIP:
        rel_field = plan.target_relationship or "alert_id"
        if rel_field not in row_to_modify:
            # Look for foreign key columns
            for col in ("alert_id", "case_id", "asset_id"):
                if col in row_to_modify:
                    rel_field = col
                    break
        if rel_field in row_to_modify:
            before_val = row_to_modify[rel_field]
            row_to_modify[rel_field] = "00000000-0000-0000-0000-000000000000"
            after_val = "00000000-0000-0000-0000-000000000000"
        else:
            raise QualityMutationError(
                "Cannot apply BROKEN_RELATIONSHIP: no relationship field found in record"
            )

    elif m_type == QualityMutationType.TIMESTAMP_PROBLEM:
        ts_field = field_to_modify or "created_at_utc"
        if ts_field not in row_to_modify:
            for col in ("created_at", "created_at_utc", "started_at_utc"):
                if col in row_to_modify:
                    ts_field = col
                    break
        if ts_field in row_to_modify:
            row_to_modify[ts_field] = "2099-01-01T00:00:00Z"
            after_val = "2099-01-01T00:00:00Z"
        else:
            raise QualityMutationError(
                f"Cannot apply TIMESTAMP_PROBLEM: timestamp field '{ts_field}' not found"
            )

    elif m_type == QualityMutationType.SCHEMA_DRIFT:
        # Introduce drifted schema attribute
        if ext == "csv":
            if "workflow_version_v2" not in header:
                header.append("workflow_version_v2")
            for r in records:
                r["workflow_version_v2"] = ""
            row_to_modify["workflow_version_v2"] = "DRIFTED_V2"
        else:
            row_to_modify["workflow_version_v2"] = "DRIFTED_V2"
        after_val = "DRIFTED_V2"

    elif m_type == QualityMutationType.VOCABULARY_DRIFT:
        v_field = field_to_modify or "severity"
        if v_field in row_to_modify:
            row_to_modify[v_field] = "DRIFTED_CUSTOM_SEV"
            after_val = "DRIFTED_CUSTOM_SEV"
        else:
            raise QualityMutationError(
                f"Cannot apply VOCABULARY_DRIFT: field '{v_field}' not found"
            )

    elif m_type == QualityMutationType.LATE_ARRIVAL:
        # Alter timestamp to a subsequent period
        p_field = "created_at_utc" if "created_at_utc" in row_to_modify else "period"
        if p_field in row_to_modify:
            row_to_modify[p_field] = (
                "2099-12-31T23:59:59Z" if p_field == "created_at_utc" else "P02"
            )
            after_val = row_to_modify[p_field]
        else:
            raise QualityMutationError(
                "Cannot apply LATE_ARRIVAL: neither 'created_at_utc' nor 'period' found"
            )

    elif m_type == QualityMutationType.COUNT_MISMATCH:
        c_field = field_to_modify or "declared_record_count"
        if c_field in row_to_modify:
            row_to_modify[c_field] = "99999"
            after_val = "99999"
        else:
            raise QualityMutationError(
                f"Cannot apply COUNT_MISMATCH: field '{c_field}' not found in record"
            )

    elif m_type == QualityMutationType.SOURCE_ID_ABSENCE:
        # Blank out source ID
        id_field = field_to_modify or (
            "src_case_id" if "src_case_id" in row_to_modify else f"{target_fam}_id"
        )
        if id_field in row_to_modify:
            row_to_modify[id_field] = ""
            after_val = ""
        else:
            raise QualityMutationError(
                f"Cannot apply SOURCE_ID_ABSENCE: ID field '{id_field}' not found"
            )

    # 6. Write back to disk
    if ext == "csv":
        with file_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv_mod.DictWriter(f, fieldnames=header, lineterminator="\n")
            writer.writeheader()
            writer.writerows(records)
    elif ext == "json":
        file_path.write_text(json_mod.dumps(records, indent=2), encoding="utf-8")
    elif ext == "jsonl":
        file_path.write_text("\n".join(json_mod.dumps(r) for r in records) + "\n", encoding="utf-8")

    return {
        "source_file": source_file_name,
        "source_locator": resolved_locator,
        "source_field": field_to_modify,
        "source_before": before_val,
        "source_after": after_val,
    }


def apply_missing_field(
    plan: QualityPlan,
    records: dict[str, list[Any]],
    seeds: SeedManager,
    ledger: AuthorizationLedger,
    source_exports_root: Path | None = None,
) -> tuple[dict[str, list[Any]], MutationReceipt]:
    """Omit an optional/conditional field from a record (yielding NOT_PROVIDED)."""
    _verify_quality_auth(plan, ledger)
    new_records = _copy_records(records)
    family_list = new_records[plan.target_family]
    target_field = plan.target_field or "source_alert_id"

    found_idx = -1
    for idx, rec in enumerate(family_list):
        rec_id = str(getattr(rec, f"{plan.target_family}_id", getattr(rec, "id", None)))
        if rec_id == plan.target_record_id:
            found_idx = idx
            break

    if found_idx == -1:
        raise QualityMutationError(
            f"Target record '{plan.target_record_id}' not found in {plan.target_family}"
        )

    orig_rec = family_list[found_idx]
    before_state = {target_field: getattr(orig_rec, target_field, None)}
    mutated_rec = orig_rec.model_copy(update={target_field: None})
    family_list[found_idx] = mutated_rec
    after_state = {target_field: None}

    src_mut = _apply_source_file_mutation(plan, source_exports_root)
    if src_mut:
        after_state["source_mutation"] = src_mut
    receipt = _consume_quality_auth(plan, ledger, before_state, after_state, (target_field,))
    return new_records, receipt


def apply_missing_family(
    plan: QualityPlan,
    records: dict[str, list[Any]],
    seeds: SeedManager,
    ledger: AuthorizationLedger,
    source_exports_root: Path | None = None,
) -> tuple[dict[str, list[Any]], MutationReceipt]:
    """Mark a family declaration as NOT_PROVIDED or omit its records."""
    _verify_quality_auth(plan, ledger)
    new_records = _copy_records(records)
    sub_families = new_records["submission_family"]

    found_idx = -1
    for idx, rec in enumerate(sub_families):
        if str(rec.submission_family_id) == plan.target_record_id:
            found_idx = idx
            break

    if found_idx == -1:
        for idx, rec in enumerate(sub_families):
            if rec.evidence_family == plan.target_family:
                found_idx = idx
                break

    if found_idx == -1:
        raise QualityMutationError(
            f"Submission family declaration for '{plan.target_family}' not found"
        )

    orig_rec = sub_families[found_idx]
    before_state = {"presence_state": orig_rec.presence_state}
    mutated_rec = orig_rec.model_copy(update={"presence_state": "NOT_PROVIDED"})
    sub_families[found_idx] = mutated_rec
    after_state = {"presence_state": "NOT_PROVIDED"}

    src_mut = _apply_source_file_mutation(plan, source_exports_root)
    if src_mut:
        after_state["source_mutation"] = src_mut
    receipt = _consume_quality_auth(plan, ledger, before_state, after_state, ("presence_state",))
    return new_records, receipt


def apply_partial_submission(
    plan: QualityPlan,
    records: dict[str, list[Any]],
    seeds: SeedManager,
    ledger: AuthorizationLedger,
    source_exports_root: Path | None = None,
) -> tuple[dict[str, list[Any]], MutationReceipt]:
    """Truncate or invalidate coverage period for a submission."""
    _verify_quality_auth(plan, ledger)
    new_records = _copy_records(records)
    submissions = new_records["submission"]

    found_idx = -1
    for idx, rec in enumerate(submissions):
        if str(rec.submission_id) == plan.target_record_id:
            found_idx = idx
            break

    if found_idx == -1:
        raise QualityMutationError(f"Target submission '{plan.target_record_id}' not found")

    orig_rec = submissions[found_idx]
    before_state = {"reporting_period_end_at_utc": orig_rec.reporting_period_end_at_utc.isoformat()}
    truncated_end = (
        orig_rec.reporting_period_start_at_utc
        + (orig_rec.reporting_period_end_at_utc - orig_rec.reporting_period_start_at_utc) / 2
    )
    mutated_rec = orig_rec.model_copy(update={"reporting_period_end_at_utc": truncated_end})
    submissions[found_idx] = mutated_rec
    after_state = {"reporting_period_end_at_utc": truncated_end.isoformat()}

    src_mut = _apply_source_file_mutation(plan, source_exports_root)
    if src_mut:
        after_state["source_mutation"] = src_mut
    receipt = _consume_quality_auth(
        plan, ledger, before_state, after_state, ("reporting_period_end_at_utc",)
    )
    return new_records, receipt


def apply_malformed_value(
    plan: QualityPlan,
    records: dict[str, list[Any]],
    seeds: SeedManager,
    ledger: AuthorizationLedger,
    source_exports_root: Path | None = None,
) -> tuple[dict[str, list[Any]], MutationReceipt]:
    """Inject an unparseable lexical value into a record."""
    _verify_quality_auth(plan, ledger)
    new_records = _copy_records(records)
    family_list = new_records[plan.target_family]
    target_field = plan.target_field or "priority_source_text"

    found_idx = -1
    for idx, rec in enumerate(family_list):
        rec_id = str(getattr(rec, f"{plan.target_family}_id", getattr(rec, "id", None)))
        if rec_id == plan.target_record_id:
            found_idx = idx
            break

    if found_idx == -1:
        raise QualityMutationError(
            f"Target record '{plan.target_record_id}' not found in {plan.target_family}"
        )

    orig_rec = family_list[found_idx]
    malformed_val = plan.parameters.get("malformed_value", "MALFORMED_PRIORITY_##%")
    before_state = {target_field: getattr(orig_rec, target_field, None)}
    mutated_rec = orig_rec.model_copy(update={target_field: malformed_val})
    family_list[found_idx] = mutated_rec
    after_state = {target_field: malformed_val}

    src_mut = _apply_source_file_mutation(plan, source_exports_root)
    if src_mut:
        after_state["source_mutation"] = src_mut
    receipt = _consume_quality_auth(plan, ledger, before_state, after_state, (target_field,))
    return new_records, receipt


def apply_exact_duplicate(
    plan: QualityPlan,
    records: dict[str, list[Any]],
    seeds: SeedManager,
    ledger: AuthorizationLedger,
    source_exports_root: Path | None = None,
) -> tuple[dict[str, list[Any]], MutationReceipt]:
    """Emit an exact duplicate of a target record."""
    _verify_quality_auth(plan, ledger)
    new_records = _copy_records(records)
    family_list = new_records[plan.target_family]

    found_rec = None
    for rec in family_list:
        rec_id = str(getattr(rec, f"{plan.target_family}_id", getattr(rec, "id", None)))
        if rec_id == plan.target_record_id:
            found_rec = rec
            break

    if found_rec is None:
        raise QualityMutationError(
            f"Target record '{plan.target_record_id}' not found in {plan.target_family}"
        )

    family_list.append(found_rec)
    before_state = {"count": len(family_list) - 1}
    after_state = {"count": len(family_list), "duplicated_id": plan.target_record_id}

    src_mut = _apply_source_file_mutation(plan, source_exports_root)
    if src_mut:
        after_state["source_mutation"] = src_mut
    receipt = _consume_quality_auth(plan, ledger, before_state, after_state, ("id",))
    return new_records, receipt


def apply_conflicting_duplicate(
    plan: QualityPlan,
    records: dict[str, list[Any]],
    seeds: SeedManager,
    ledger: AuthorizationLedger,
    source_exports_root: Path | None = None,
) -> tuple[dict[str, list[Any]], MutationReceipt]:
    """Emit a duplicate record with conflicting attribute values."""
    _verify_quality_auth(plan, ledger)
    new_records = _copy_records(records)
    family_list = new_records[plan.target_family]

    found_rec = None
    for rec in family_list:
        rec_id = str(getattr(rec, f"{plan.target_family}_id", getattr(rec, "id", None)))
        if rec_id == plan.target_record_id:
            found_rec = rec
            break

    if found_rec is None:
        raise QualityMutationError(
            f"Target record '{plan.target_record_id}' not found in {plan.target_family}"
        )

    conflict_rec = found_rec.model_copy(update={"severity": "LOW"})
    family_list.append(conflict_rec)
    before_state = {"count": len(family_list) - 1, "severity": found_rec.severity}
    after_state = {"count": len(family_list), "conflicting_severity": "LOW"}

    src_mut = _apply_source_file_mutation(plan, source_exports_root)
    if src_mut:
        after_state["source_mutation"] = src_mut
    receipt = _consume_quality_auth(plan, ledger, before_state, after_state, ("severity",))
    return new_records, receipt


def apply_broken_relationship(
    plan: QualityPlan,
    records: dict[str, list[Any]],
    seeds: SeedManager,
    ledger: AuthorizationLedger,
    source_exports_root: Path | None = None,
) -> tuple[dict[str, list[Any]], MutationReceipt]:
    """Break a foreign key or target record link."""
    _verify_quality_auth(plan, ledger)
    new_records = _copy_records(records)
    family_list = new_records[plan.target_family]
    target_rel = plan.target_relationship or "alert_id"

    found_idx = -1
    for idx, rec in enumerate(family_list):
        rec_id = str(getattr(rec, f"{plan.target_family}_id", getattr(rec, "id", None)))
        if rec_id == plan.target_record_id:
            found_idx = idx
            break

    if found_idx == -1:
        raise QualityMutationError(
            f"Target record '{plan.target_record_id}' not found in {plan.target_family}"
        )

    orig_rec = family_list[found_idx]
    broken_id = UUID("00000000-0000-0000-0000-000000000000")
    before_state = {target_rel: str(getattr(orig_rec, target_rel, None))}
    mutated_rec = orig_rec.model_copy(update={target_rel: broken_id})
    family_list[found_idx] = mutated_rec
    after_state = {target_rel: str(broken_id)}

    src_mut = _apply_source_file_mutation(plan, source_exports_root)
    if src_mut:
        after_state["source_mutation"] = src_mut
    receipt = _consume_quality_auth(plan, ledger, before_state, after_state, (target_rel,))
    return new_records, receipt


def apply_timestamp_problem(
    plan: QualityPlan,
    records: dict[str, list[Any]],
    seeds: SeedManager,
    ledger: AuthorizationLedger,
    source_exports_root: Path | None = None,
) -> tuple[dict[str, list[Any]], MutationReceipt]:
    """Inject an impossible future timestamp or inverted temporal ordering."""
    _verify_quality_auth(plan, ledger)
    new_records = _copy_records(records)
    family_list = new_records[plan.target_family]
    target_field = plan.target_field or "created_at_utc"

    found_idx = -1
    for idx, rec in enumerate(family_list):
        rec_id = str(getattr(rec, f"{plan.target_family}_id", getattr(rec, "id", None)))
        if rec_id == plan.target_record_id:
            found_idx = idx
            break

    if found_idx == -1:
        raise QualityMutationError(
            f"Target record '{plan.target_record_id}' not found in {plan.target_family}"
        )

    orig_rec = family_list[found_idx]
    orig_time = getattr(orig_rec, target_field)
    future_time = orig_time + timedelta(days=365 * 10)
    before_state = {target_field: orig_time.isoformat()}
    mutated_rec = orig_rec.model_copy(update={target_field: future_time})
    family_list[found_idx] = mutated_rec
    after_state = {target_field: future_time.isoformat()}

    src_mut = _apply_source_file_mutation(plan, source_exports_root)
    if src_mut:
        after_state["source_mutation"] = src_mut
    receipt = _consume_quality_auth(plan, ledger, before_state, after_state, (target_field,))
    return new_records, receipt


def apply_schema_drift(
    plan: QualityPlan,
    records: dict[str, list[Any]],
    seeds: SeedManager,
    ledger: AuthorizationLedger,
    source_exports_root: Path | None = None,
) -> tuple[dict[str, list[Any]], MutationReceipt]:
    """Apply schema version drift to a target record."""
    _verify_quality_auth(plan, ledger)
    new_records = _copy_records(records)
    family_list = new_records[plan.target_family]

    found_idx = -1
    for idx, rec in enumerate(family_list):
        rec_id = str(getattr(rec, f"{plan.target_family}_id", getattr(rec, "id", None)))
        if rec_id == plan.target_record_id:
            found_idx = idx
            break

    if found_idx == -1:
        raise QualityMutationError(
            f"Target record '{plan.target_record_id}' not found in {plan.target_family}"
        )

    orig_rec = family_list[found_idx]
    target_field = plan.target_field or "workflow_version"
    before_state = {target_field: getattr(orig_rec, target_field, "wf-v1")}
    drift_val = "wf-v2.0-drift"
    mutated_rec = orig_rec.model_copy(update={target_field: drift_val})
    family_list[found_idx] = mutated_rec
    after_state = {target_field: drift_val}

    src_mut = _apply_source_file_mutation(plan, source_exports_root)
    if src_mut:
        after_state["source_mutation"] = src_mut
    receipt = _consume_quality_auth(plan, ledger, before_state, after_state, (target_field,))
    return new_records, receipt


def apply_vocabulary_drift(
    plan: QualityPlan,
    records: dict[str, list[Any]],
    seeds: SeedManager,
    ledger: AuthorizationLedger,
    source_exports_root: Path | None = None,
) -> tuple[dict[str, list[Any]], MutationReceipt]:
    """Inject an unmapped vocabulary token into a record."""
    _verify_quality_auth(plan, ledger)
    new_records = _copy_records(records)
    family_list = new_records[plan.target_family]
    target_field = plan.target_field or "priority_source_text"

    found_idx = -1
    for idx, rec in enumerate(family_list):
        rec_id = str(getattr(rec, f"{plan.target_family}_id", getattr(rec, "id", None)))
        if rec_id == plan.target_record_id:
            found_idx = idx
            break

    if found_idx == -1:
        raise QualityMutationError(
            f"Target record '{plan.target_record_id}' not found in {plan.target_family}"
        )

    orig_rec = family_list[found_idx]
    drifted_token = "DRIFTED_CUSTOM_SEV"
    before_state = {target_field: getattr(orig_rec, target_field, None)}
    mutated_rec = orig_rec.model_copy(update={target_field: drifted_token})
    family_list[found_idx] = mutated_rec
    after_state = {target_field: drifted_token}

    src_mut = _apply_source_file_mutation(plan, source_exports_root)
    if src_mut:
        after_state["source_mutation"] = src_mut
    receipt = _consume_quality_auth(plan, ledger, before_state, after_state, (target_field,))
    return new_records, receipt


def apply_late_arrival(
    plan: QualityPlan,
    records: dict[str, list[Any]],
    seeds: SeedManager,
    ledger: AuthorizationLedger,
    source_exports_root: Path | None = None,
) -> tuple[dict[str, list[Any]], MutationReceipt]:
    """Annotate a record as arriving late in a subsequent reporting submission."""
    _verify_quality_auth(plan, ledger)
    new_records = _copy_records(records)
    family_list = new_records[plan.target_family]

    found_idx = -1
    for idx, rec in enumerate(family_list):
        rec_id = str(getattr(rec, f"{plan.target_family}_id", getattr(rec, "id", None)))
        if rec_id == plan.target_record_id:
            found_idx = idx
            break

    if found_idx == -1:
        raise QualityMutationError(
            f"Target record '{plan.target_record_id}' not found in {plan.target_family}"
        )

    orig_rec = family_list[found_idx]
    before_state = {"alert_summary": orig_rec.alert_summary}
    mutated_summary = (orig_rec.alert_summary or "") + " [LATE_ARRIVAL:SUBMISSION_BATCH_2]"
    mutated_rec = orig_rec.model_copy(update={"alert_summary": mutated_summary})
    family_list[found_idx] = mutated_rec
    after_state = {"alert_summary": mutated_summary}

    src_mut = _apply_source_file_mutation(plan, source_exports_root)
    if src_mut:
        after_state["source_mutation"] = src_mut
    receipt = _consume_quality_auth(plan, ledger, before_state, after_state, ("alert_summary",))
    return new_records, receipt


def apply_count_mismatch(
    plan: QualityPlan,
    records: dict[str, list[Any]],
    seeds: SeedManager,
    ledger: AuthorizationLedger,
    source_exports_root: Path | None = None,
) -> tuple[dict[str, list[Any]], MutationReceipt]:
    """Alter declared count in submission manifest without changing actual rows."""
    _verify_quality_auth(plan, ledger)
    new_records = _copy_records(records)
    sub_families = new_records["submission_family"]

    found_idx = -1
    for idx, rec in enumerate(sub_families):
        if str(rec.submission_family_id) == plan.target_record_id:
            found_idx = idx
            break

    if found_idx == -1:
        raise QualityMutationError(f"Target submission family '{plan.target_record_id}' not found")

    orig_rec = sub_families[found_idx]
    before_state = {"declared_record_count": orig_rec.declared_record_count}
    mismatch_count = (orig_rec.declared_record_count or 0) + 9999
    mutated_rec = orig_rec.model_copy(update={"declared_record_count": mismatch_count})
    sub_families[found_idx] = mutated_rec
    after_state = {"declared_record_count": mismatch_count}

    src_mut = _apply_source_file_mutation(plan, source_exports_root)
    if src_mut:
        after_state["source_mutation"] = src_mut
    receipt = _consume_quality_auth(
        plan, ledger, before_state, after_state, ("declared_record_count",)
    )
    return new_records, receipt


def apply_source_id_absence(
    plan: QualityPlan,
    records: dict[str, list[Any]],
    seeds: SeedManager,
    ledger: AuthorizationLedger,
    source_exports_root: Path | None = None,
) -> tuple[dict[str, list[Any]], MutationReceipt]:
    """Omit optional native source ID while retaining canonical UUID."""
    _verify_quality_auth(plan, ledger)
    new_records = _copy_records(records)
    family_list = new_records[plan.target_family]
    source_id_field = f"source_{plan.target_family}_id"

    found_idx = -1
    for idx, rec in enumerate(family_list):
        rec_id = str(getattr(rec, f"{plan.target_family}_id", getattr(rec, "id", None)))
        if rec_id == plan.target_record_id:
            found_idx = idx
            break

    if found_idx == -1:
        raise QualityMutationError(
            f"Target record '{plan.target_record_id}' not found in {plan.target_family}"
        )

    orig_rec = family_list[found_idx]
    before_state = {source_id_field: getattr(orig_rec, source_id_field, None)}
    mutated_rec = orig_rec.model_copy(update={source_id_field: None})
    family_list[found_idx] = mutated_rec
    after_state = {source_id_field: None}

    src_mut = _apply_source_file_mutation(plan, source_exports_root)
    if src_mut:
        after_state["source_mutation"] = src_mut
    receipt = _consume_quality_auth(plan, ledger, before_state, after_state, (source_id_field,))
    return new_records, receipt


_QUALITY_MUTATOR_MAP = {
    QualityMutationType.MISSING_FIELD: apply_missing_field,
    QualityMutationType.MISSING_FAMILY: apply_missing_family,
    QualityMutationType.PARTIAL_SUBMISSION: apply_partial_submission,
    QualityMutationType.MALFORMED_VALUE: apply_malformed_value,
    QualityMutationType.EXACT_DUPLICATE: apply_exact_duplicate,
    QualityMutationType.CONFLICTING_DUPLICATE: apply_conflicting_duplicate,
    QualityMutationType.BROKEN_RELATIONSHIP: apply_broken_relationship,
    QualityMutationType.TIMESTAMP_PROBLEM: apply_timestamp_problem,
    QualityMutationType.SCHEMA_DRIFT: apply_schema_drift,
    QualityMutationType.VOCABULARY_DRIFT: apply_vocabulary_drift,
    QualityMutationType.LATE_ARRIVAL: apply_late_arrival,
    QualityMutationType.COUNT_MISMATCH: apply_count_mismatch,
    QualityMutationType.SOURCE_ID_ABSENCE: apply_source_id_absence,
}


def get_quality_mutator(mutation_type: QualityMutationType):
    """Retrieve mutator function for a quality mutation type."""
    mutator = _QUALITY_MUTATOR_MAP.get(mutation_type)
    if mutator is None:
        raise QualityMutationError(f"No mutator registered for quality mutation '{mutation_type}'")
    return mutator
