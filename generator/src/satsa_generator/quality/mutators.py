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
) -> None:
    """Apply corresponding source-level quality defect to rendered files on disk."""
    if not source_exports_root or not source_exports_root.exists():
        return

    m_type = plan.mutation_type
    target_fam = plan.target_family

    try:
        if m_type == QualityMutationType.MISSING_FIELD:
            for p in source_exports_root.glob("alert_*.*"):
                if p.suffix == ".csv":
                    lines = p.read_text(encoding="utf-8").splitlines()
                    if len(lines) > 1:
                        header = lines[0].split(",")
                        for col in ("src_alert_id", "source_alert_id"):
                            if col in header:
                                idx = header.index(col)
                                row = lines[1].split(",")
                                if len(row) > idx:
                                    row[idx] = ""
                                    lines[1] = ",".join(row)
                                    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
                                    break

        elif m_type == QualityMutationType.MISSING_FAMILY:
            for p in list(source_exports_root.glob(f"{target_fam}_*.*")):
                if p.exists():
                    p.unlink()

        elif m_type == QualityMutationType.PARTIAL_SUBMISSION:
            for p in source_exports_root.glob("submission_*.*"):
                if p.suffix == ".csv":
                    lines = p.read_text(encoding="utf-8").splitlines()
                    if len(lines) > 2:
                        p.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")

        elif m_type == QualityMutationType.MALFORMED_VALUE:
            for p in source_exports_root.glob("alert_*.*"):
                if p.suffix == ".csv":
                    lines = p.read_text(encoding="utf-8").splitlines()
                    if len(lines) > 1:
                        header = lines[0].split(",")
                        for col in ("priority", "priority_source_text", "severity"):
                            if col in header:
                                idx = header.index(col)
                                row = lines[1].split(",")
                                if len(row) > idx:
                                    row[idx] = "MALFORMED_PRIORITY_##%"
                                    lines[1] = ",".join(row)
                                    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
                                    break

        elif m_type == QualityMutationType.EXACT_DUPLICATE:
            for p in source_exports_root.glob("alert_*.*"):
                if p.suffix == ".csv":
                    lines = p.read_text(encoding="utf-8").splitlines()
                    if len(lines) > 1:
                        lines.append(lines[1])
                        p.write_text("\n".join(lines) + "\n", encoding="utf-8")

        elif m_type == QualityMutationType.CONFLICTING_DUPLICATE:
            for p in source_exports_root.glob("alert_*.*"):
                if p.suffix == ".csv":
                    lines = p.read_text(encoding="utf-8").splitlines()
                    if len(lines) > 1:
                        header = lines[0].split(",")
                        row = lines[1].split(",")
                        for col in ("severity", "priority"):
                            if col in header:
                                idx = header.index(col)
                                if len(row) > idx:
                                    row[idx] = "LOW"
                        lines.append(",".join(row))
                        p.write_text("\n".join(lines) + "\n", encoding="utf-8")

        elif m_type == QualityMutationType.BROKEN_RELATIONSHIP:
            for p in source_exports_root.glob("case_alert_link_*.*"):
                if p.suffix == ".csv":
                    lines = p.read_text(encoding="utf-8").splitlines()
                    if len(lines) > 1:
                        header = lines[0].split(",")
                        if "alert_id" in header:
                            idx = header.index("alert_id")
                            row = lines[1].split(",")
                            if len(row) > idx:
                                row[idx] = "00000000-0000-0000-0000-000000000000"
                                lines[1] = ",".join(row)
                                p.write_text("\n".join(lines) + "\n", encoding="utf-8")

        elif m_type == QualityMutationType.TIMESTAMP_PROBLEM:
            for p in source_exports_root.glob("case_*.*"):
                if p.suffix == ".csv":
                    lines = p.read_text(encoding="utf-8").splitlines()
                    if len(lines) > 1:
                        header = lines[0].split(",")
                        for col in ("created_at", "created_at_utc"):
                            if col in header:
                                idx = header.index(col)
                                row = lines[1].split(",")
                                if len(row) > idx:
                                    row[idx] = "2099-01-01T00:00:00Z"
                                    lines[1] = ",".join(row)
                                    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
                                    break

        elif m_type == QualityMutationType.SCHEMA_DRIFT:
            for p in source_exports_root.glob("alert_src_a.*"):
                if p.suffix == ".csv":
                    lines = p.read_text(encoding="utf-8").splitlines()
                    if lines:
                        lines[0] = lines[0] + ",workflow_version_v2"
                        for i in range(1, len(lines)):
                            lines[i] = lines[i] + ","
                        p.write_text("\n".join(lines) + "\n", encoding="utf-8")

        elif m_type == QualityMutationType.VOCABULARY_DRIFT:
            for p in source_exports_root.glob("alert_*.*"):
                if p.suffix == ".csv":
                    lines = p.read_text(encoding="utf-8").splitlines()
                    if len(lines) > 2:
                        header = lines[0].split(",")
                        for col in ("priority", "priority_source_text", "severity"):
                            if col in header:
                                idx = header.index(col)
                                row = lines[2].split(",")
                                if len(row) > idx:
                                    row[idx] = "DRIFTED_CUSTOM_SEV"
                                    lines[2] = ",".join(row)
                                    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
                                    break

        elif m_type == QualityMutationType.LATE_ARRIVAL:
            for p in source_exports_root.glob("alert_*.*"):
                if p.suffix == ".csv":
                    lines = p.read_text(encoding="utf-8").splitlines()
                    if len(lines) > 3:
                        header = lines[0].split(",")
                        if "period" in header:
                            idx = header.index("period")
                            row = lines[3].split(",")
                            if len(row) > idx:
                                row[idx] = "P02"
                                lines[3] = ",".join(row)
                                p.write_text("\n".join(lines) + "\n", encoding="utf-8")

        elif m_type == QualityMutationType.COUNT_MISMATCH:
            for p in source_exports_root.glob("submission_family_*.*"):
                if p.suffix == ".csv":
                    lines = p.read_text(encoding="utf-8").splitlines()
                    if len(lines) > 1:
                        header = lines[0].split(",")
                        if "declared_record_count" in header:
                            idx = header.index("declared_record_count")
                            row = lines[1].split(",")
                            if len(row) > idx:
                                row[idx] = "99999"
                                lines[1] = ",".join(row)
                                p.write_text("\n".join(lines) + "\n", encoding="utf-8")

        elif m_type == QualityMutationType.SOURCE_ID_ABSENCE:
            for p in source_exports_root.glob("case_*.*"):
                if p.suffix == ".csv":
                    lines = p.read_text(encoding="utf-8").splitlines()
                    if len(lines) > 1:
                        header = lines[0].split(",")
                        for col in ("src_case_id", "source_case_id"):
                            if col in header:
                                idx = header.index(col)
                                row = lines[1].split(",")
                                if len(row) > idx:
                                    row[idx] = ""
                                    lines[1] = ",".join(row)
                                    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
                                    break
    except Exception:
        pass


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

    receipt = _consume_quality_auth(plan, ledger, before_state, after_state, (target_field,))
    _apply_source_file_mutation(plan, source_exports_root)
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

    receipt = _consume_quality_auth(plan, ledger, before_state, after_state, ("presence_state",))
    _apply_source_file_mutation(plan, source_exports_root)
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

    receipt = _consume_quality_auth(
        plan, ledger, before_state, after_state, ("reporting_period_end_at_utc",)
    )
    _apply_source_file_mutation(plan, source_exports_root)
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

    receipt = _consume_quality_auth(plan, ledger, before_state, after_state, (target_field,))
    _apply_source_file_mutation(plan, source_exports_root)
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

    receipt = _consume_quality_auth(plan, ledger, before_state, after_state, ("id",))
    _apply_source_file_mutation(plan, source_exports_root)
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

    receipt = _consume_quality_auth(plan, ledger, before_state, after_state, ("severity",))
    _apply_source_file_mutation(plan, source_exports_root)
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

    receipt = _consume_quality_auth(plan, ledger, before_state, after_state, (target_rel,))
    _apply_source_file_mutation(plan, source_exports_root)
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

    receipt = _consume_quality_auth(plan, ledger, before_state, after_state, (target_field,))
    _apply_source_file_mutation(plan, source_exports_root)
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

    receipt = _consume_quality_auth(plan, ledger, before_state, after_state, (target_field,))
    _apply_source_file_mutation(plan, source_exports_root)
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

    receipt = _consume_quality_auth(plan, ledger, before_state, after_state, (target_field,))
    _apply_source_file_mutation(plan, source_exports_root)
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

    receipt = _consume_quality_auth(plan, ledger, before_state, after_state, ("alert_summary",))
    _apply_source_file_mutation(plan, source_exports_root)
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

    receipt = _consume_quality_auth(
        plan, ledger, before_state, after_state, ("declared_record_count",)
    )
    _apply_source_file_mutation(plan, source_exports_root)
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

    receipt = _consume_quality_auth(plan, ledger, before_state, after_state, (source_id_field,))
    _apply_source_file_mutation(plan, source_exports_root)
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
