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


def _get_plan_target_record_ids(plan: QualityPlan) -> tuple[str, ...]:
    """Return explicit target record IDs, including withheld record for partial submission."""
    if plan.mutation_type == QualityMutationType.PARTIAL_SUBMISSION and plan.parameters.get(
        "withheld_record_id"
    ):
        return (plan.target_record_id, str(plan.parameters["withheld_record_id"]))
    return (plan.target_record_id,)


def _verify_quality_auth(plan: QualityPlan, ledger: AuthorizationLedger) -> None:
    """Verify authorization in the ledger prior to mutation."""
    ledger.verify_authorization(
        plan.plan_id,
        expected_scenario_id="QUALITY_ENGINE",
        expected_mutation_type=MutationType(plan.mutation_type.value),
        target_record_ids=_get_plan_target_record_ids(plan),
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
        target_record_ids=_get_plan_target_record_ids(plan),
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
    2. Fail loudly (QualityMutationError) if any required target is missing or invalid.
    3. Modify only the intended record/field/file without side effects.
    4. Return exact mutation details for receipt auditing.
    """
    if not source_exports_root or not source_exports_root.exists():
        return {}

    m_id = plan.plan_id
    m_type = plan.mutation_type
    target_fam = plan.target_family
    target_rec_id = str(plan.target_record_id)

    # 1. Enforce explicit source file (NO FALLBACK to candidates[0] or default SRC-A)
    if not plan.source_file:
        raise QualityMutationError(
            f"Mutation '{m_id}' ({m_type}): missing required explicit source_file"
        )
    source_file_name = plan.source_file
    file_path = source_exports_root / source_file_name

    # 2. Enforce explicit source profile (NO FALLBACK to default profile)
    source_prof = plan.source_profile_id
    if not source_prof:
        raise QualityMutationError(
            f"Mutation '{m_id}' ({m_type}): missing required explicit source_profile_id"
        )

    # 3. Enforce explicit source locator (NO FALLBACK to searching or last row)
    if not plan.source_locator:
        raise QualityMutationError(
            f"Mutation '{m_id}' ({m_type}): missing required explicit source_locator"
        )

    # Handle MISSING_FAMILY by removing rendered file
    if m_type == QualityMutationType.MISSING_FAMILY:
        if not file_path.exists():
            raise QualityMutationError(
                f"Mutation '{m_id}': Target source file '{source_file_name}' for "
                f"MISSING_FAMILY does not exist on disk in {source_exports_root}"
            )
        file_path.unlink()
        return {
            "mutation_id": m_id,
            "mutation_type": "MISSING_FAMILY",
            "source_profile": source_prof,
            "source_file": source_file_name,
            "source_locator": plan.source_locator,
            "deleted": True,
        }

    if not file_path.exists():
        raise QualityMutationError(
            f"Mutation '{m_id}': Target source file '{source_file_name}' does not exist on disk"
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
        raise QualityMutationError(
            f"Mutation '{m_id}': Unsupported source format '{ext}' in '{source_file_name}'"
        )

    if not records:
        raise QualityMutationError(f"Mutation '{m_id}': Source file '{source_file_name}' is empty")

    loc = plan.source_locator.strip()
    target_row_idx: int
    if loc.startswith("row:"):
        try:
            row_num = int(loc.split(":")[1])
            target_row_idx = row_num - 1
        except ValueError as err:
            raise QualityMutationError(
                f"Mutation '{m_id}': Invalid row locator format '{plan.source_locator}'"
            ) from err
    elif loc.startswith("[") and loc.endswith("]"):
        try:
            target_row_idx = int(loc[1:-1])
        except ValueError as err:
            raise QualityMutationError(
                f"Mutation '{m_id}': Invalid index locator format '{plan.source_locator}'"
            ) from err
    else:
        raise QualityMutationError(
            f"Mutation '{m_id}': Unrecognized locator format '{plan.source_locator}'"
        )

    if target_row_idx < 0 or target_row_idx >= len(records):
        raise QualityMutationError(
            f"Mutation '{m_id}': Source locator '{plan.source_locator}' out of bounds "
            f"in '{source_file_name}' (file has {len(records)} records)"
        )

    # 4. Verify record identity at target locator
    rec = records[target_row_idx]
    if m_type == QualityMutationType.PARTIAL_SUBMISSION:
        expected_withheld_id = str(plan.parameters.get("withheld_record_id") or "")
        if not expected_withheld_id:
            raise QualityMutationError(
                f"Mutation '{m_id}': PARTIAL_SUBMISSION requires explicit 'withheld_record_id'"
            )
        withheld_fam = str(plan.parameters.get("withheld_family") or "alert")
        id_candidates = [f"{withheld_fam}_id", "id", "alert_id", "submission_id"]
        matched_id: str | None = None
        for id_col in id_candidates:
            if id_col in rec and rec[id_col]:
                matched_id = str(rec[id_col])
                break
        if not matched_id or matched_id != expected_withheld_id:
            raise QualityMutationError(
                f"Mutation '{m_id}': Record at locator '{plan.source_locator}' in "
                f"'{source_file_name}' has ID '{matched_id}', does not match expected "
                f"withheld record ID '{expected_withheld_id}'"
            )
    else:
        id_candidates = [
            f"{target_fam}_id",
            "id",
            "alert_id",
            "case_id",
            "submission_id",
            "submission_family_id",
            "case_alert_link_id",
            "asset_id",
            "organization_id",
        ]
        matched_id = None
        for id_col in id_candidates:
            if id_col in rec and rec[id_col]:
                matched_id = str(rec[id_col])
                break
        if not matched_id or matched_id != target_rec_id:
            raise QualityMutationError(
                f"Mutation '{m_id}': Record at locator '{plan.source_locator}' in "
                f"'{source_file_name}' has ID '{matched_id}', does not match expected "
                f"target record ID '{target_rec_id}'"
            )

    resolved_locator = plan.source_locator

    # 5. Enforce explicit field / relationship (NO FALLBACK to searching arbitrary columns)
    field_to_modify: str | None = None
    if m_type == QualityMutationType.BROKEN_RELATIONSHIP:
        field_to_modify = plan.target_relationship or plan.source_field
        if not field_to_modify:
            raise QualityMutationError(
                f"Mutation '{m_id}' (BROKEN_RELATIONSHIP): missing explicit target_relationship"
            )
        if field_to_modify not in rec:
            raise QualityMutationError(
                f"Mutation '{m_id}': Relationship field '{field_to_modify}' not found "
                f"in record at {resolved_locator} in '{source_file_name}'"
            )
    elif m_type == QualityMutationType.SCHEMA_DRIFT:
        field_to_modify = plan.source_field or plan.target_field
        if not field_to_modify:
            raise QualityMutationError(
                f"Mutation '{m_id}' (SCHEMA_DRIFT): missing required explicit field to modify"
            )
    elif m_type in (QualityMutationType.PARTIAL_SUBMISSION, QualityMutationType.EXACT_DUPLICATE):
        field_to_modify = None  # record withholding or whole-row duplication
    else:
        field_to_modify = plan.source_field or plan.target_field
        if not field_to_modify:
            raise QualityMutationError(
                f"Mutation '{m_id}' ({m_type}): missing required explicit field to modify"
            )
        if field_to_modify not in rec:
            raise QualityMutationError(
                f"Mutation '{m_id}': Target source field '{field_to_modify}' not found "
                f"in record at {resolved_locator} in '{source_file_name}'"
            )

    row_to_modify = records[target_row_idx]
    before_val = row_to_modify.get(field_to_modify) if field_to_modify else None
    after_val = None

    # 6. Apply the exact mutation operation
    if m_type == QualityMutationType.MISSING_FIELD:
        assert field_to_modify is not None
        row_to_modify[field_to_modify] = ""
        after_val = ""

    elif m_type == QualityMutationType.PARTIAL_SUBMISSION:
        withheld_row = records.pop(target_row_idx)
        after_val = "WITHHELD"
        # Write back and return detailed receipt
        if ext == "csv":
            with file_path.open("w", encoding="utf-8", newline="") as f:
                writer = csv_mod.DictWriter(f, fieldnames=header, lineterminator="\n")
                writer.writeheader()
                writer.writerows(records)
        elif ext == "json":
            file_path.write_text(json_mod.dumps(records, indent=2), encoding="utf-8")
        elif ext == "jsonl":
            file_path.write_text(
                "\n".join(json_mod.dumps(r) for r in records) + "\n", encoding="utf-8"
            )

        return {
            "mutation_id": m_id,
            "mutation_type": "PARTIAL_SUBMISSION",
            "source_profile": plan.source_profile_id,
            "source_file": source_file_name,
            "source_locator": resolved_locator,
            "withheld_record_id": plan.parameters.get("withheld_record_id"),
            "withheld_family": plan.parameters.get("withheld_family"),
            "withheld_source_file": source_file_name,
            "withheld_source_locator": resolved_locator,
            "withheld_record_content": withheld_row,
            "source_before": "PRESENT",
            "source_after": after_val,
        }

    elif m_type == QualityMutationType.MALFORMED_VALUE:
        assert field_to_modify is not None
        malformed = str(plan.parameters.get("malformed_value", "MALFORMED_PRIORITY_##%"))
        row_to_modify[field_to_modify] = malformed
        after_val = malformed

    elif m_type == QualityMutationType.EXACT_DUPLICATE:
        dup_row = dict(row_to_modify)
        records.append(dup_row)
        after_val = "DUPLICATED"

    elif m_type == QualityMutationType.CONFLICTING_DUPLICATE:
        assert field_to_modify is not None
        dup_row = dict(row_to_modify)
        dup_row[field_to_modify] = plan.parameters.get("conflicting_value", "LOW")
        records.append(dup_row)
        after_val = f"CONFLICTING_DUPLICATE({dup_row[field_to_modify]})"

    elif m_type == QualityMutationType.BROKEN_RELATIONSHIP:
        assert field_to_modify is not None
        row_to_modify[field_to_modify] = "00000000-0000-0000-0000-000000000000"
        after_val = "00000000-0000-0000-0000-000000000000"

    elif m_type == QualityMutationType.TIMESTAMP_PROBLEM:
        assert field_to_modify is not None
        corrupted_ts = plan.parameters.get("corrupted_timestamp", "2099-01-01T00:00:00Z")
        row_to_modify[field_to_modify] = corrupted_ts
        after_val = corrupted_ts

    elif m_type == QualityMutationType.SCHEMA_DRIFT:
        assert field_to_modify is not None
        drifted_val = plan.parameters.get("drifted_value", "DRIFTED_V2")
        if ext == "csv":
            if field_to_modify not in header:
                header.append(field_to_modify)
            for r in records:
                if field_to_modify not in r:
                    r[field_to_modify] = ""
            row_to_modify[field_to_modify] = drifted_val
        else:
            row_to_modify[field_to_modify] = drifted_val
        after_val = drifted_val

    elif m_type == QualityMutationType.VOCABULARY_DRIFT:
        assert field_to_modify is not None
        drifted_tok = plan.parameters.get("drifted_token", "DRIFTED_CUSTOM_SEV")
        row_to_modify[field_to_modify] = drifted_tok
        after_val = drifted_tok

    elif m_type == QualityMutationType.LATE_ARRIVAL:
        assert field_to_modify is not None
        delayed_ts = plan.parameters.get("delayed_timestamp", "2099-12-31T23:59:59Z")
        row_to_modify[field_to_modify] = delayed_ts
        after_val = delayed_ts

    elif m_type == QualityMutationType.COUNT_MISMATCH:
        assert field_to_modify is not None
        count_val = str(plan.parameters.get("mismatched_count", "99999"))
        row_to_modify[field_to_modify] = count_val
        after_val = count_val

    elif m_type == QualityMutationType.SOURCE_ID_ABSENCE:
        assert field_to_modify is not None
        row_to_modify[field_to_modify] = ""
        after_val = ""

    # 7. Write back to disk
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
        "mutation_id": m_id,
        "mutation_type": str(m_type),
        "source_profile": plan.source_profile_id,
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
    target_field = plan.target_field or plan.source_field
    if not target_field:
        raise QualityMutationError(
            f"Mutation '{plan.plan_id}' (MISSING_FIELD): missing explicit target_field"
        )

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
        after_state["withheld_record_id"] = src_mut.get("withheld_record_id")
        after_state["evidence_family"] = src_mut.get("withheld_family") or plan.parameters.get(
            "withheld_family"
        )
        after_state["source_profile"] = src_mut.get("source_profile") or plan.source_profile_id
        after_state["source_file"] = src_mut.get("source_file") or plan.source_file
        after_state["source_locator"] = src_mut.get("source_locator") or plan.source_locator
        after_state["mutation_id"] = plan.plan_id
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
    target_field = plan.target_field or plan.source_field
    if not target_field:
        raise QualityMutationError(
            f"Mutation '{plan.plan_id}' (MALFORMED_VALUE): missing explicit target_field"
        )

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
    target_rel = plan.target_relationship or plan.source_field
    if not target_rel:
        raise QualityMutationError(
            f"Mutation '{plan.plan_id}' (BROKEN_RELATIONSHIP): missing explicit target_relationship"
        )

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
    target_field = plan.target_field or plan.source_field
    if not target_field:
        raise QualityMutationError(
            f"Mutation '{plan.plan_id}' (TIMESTAMP_PROBLEM): missing explicit target_field"
        )

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
    target_field = plan.target_field or plan.source_field
    if not target_field:
        raise QualityMutationError(
            f"Mutation '{plan.plan_id}' (SCHEMA_DRIFT): missing explicit target_field"
        )
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
    target_field = plan.target_field or plan.source_field
    if not target_field:
        raise QualityMutationError(
            f"Mutation '{plan.plan_id}' (VOCABULARY_DRIFT): missing explicit target_field"
        )

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
    target_field = plan.target_field or plan.source_field or "alert_summary"
    before_state = {"alert_summary": orig_rec.alert_summary}
    mutated_summary = (orig_rec.alert_summary or "") + " [LATE_ARRIVAL:SUBMISSION_BATCH_2]"
    mutated_rec = orig_rec.model_copy(update={"alert_summary": mutated_summary})
    family_list[found_idx] = mutated_rec
    after_state = {"alert_summary": mutated_summary}

    src_mut = _apply_source_file_mutation(plan, source_exports_root)
    if src_mut:
        after_state["source_mutation"] = src_mut
    receipt = _consume_quality_auth(plan, ledger, before_state, after_state, (target_field,))
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
