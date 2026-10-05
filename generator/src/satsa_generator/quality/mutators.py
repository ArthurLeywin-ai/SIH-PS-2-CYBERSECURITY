"""
Quality mutators — implementations for all 13 quality mutation types.

Follows GENERATOR_IMPLEMENTATION_PLAN §13.2 and §13.3:
- Copy-on-write semantics: never mutate records in place
- Pre-authorization required: every mutation must be in AuthorizationLedger
- Emits private MutationReceipt for reconciliation
- Preserves referential and temporal integrity on unaffected records
"""

from __future__ import annotations

import uuid
from datetime import timedelta
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


def apply_missing_field(
    plan: QualityPlan,
    records: dict[str, list[Any]],
    seeds: SeedManager,
    ledger: AuthorizationLedger,
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
    return new_records, receipt


def apply_missing_family(
    plan: QualityPlan,
    records: dict[str, list[Any]],
    seeds: SeedManager,
    ledger: AuthorizationLedger,
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
    return new_records, receipt


def apply_partial_submission(
    plan: QualityPlan,
    records: dict[str, list[Any]],
    seeds: SeedManager,
    ledger: AuthorizationLedger,
) -> tuple[dict[str, list[Any]], MutationReceipt]:
    """Truncate submission coverage and declare partial period."""
    _verify_quality_auth(plan, ledger)
    new_records = _copy_records(records)
    submissions = new_records["submission"]

    found_idx = -1
    for idx, rec in enumerate(submissions):
        if str(rec.submission_id) == plan.target_record_id:
            found_idx = idx
            break

    if found_idx == -1:
        raise QualityMutationError(f"Submission '{plan.target_record_id}' not found")

    orig_rec = submissions[found_idx]
    before_state = {
        "declared_completeness": orig_rec.declared_completeness,
        "period_maturity_state": orig_rec.period_maturity_state,
    }
    mutated_rec = orig_rec.model_copy(
        update={
            "declared_completeness": "DECLARED_PARTIAL",
            "period_maturity_state": "PARTIAL",
        }
    )
    submissions[found_idx] = mutated_rec
    after_state = {
        "declared_completeness": "DECLARED_PARTIAL",
        "period_maturity_state": "PARTIAL",
    }

    receipt = _consume_quality_auth(
        plan, ledger, before_state, after_state, ("declared_completeness", "period_maturity_state")
    )
    return new_records, receipt


def apply_malformed_value(
    plan: QualityPlan,
    records: dict[str, list[Any]],
    seeds: SeedManager,
    ledger: AuthorizationLedger,
) -> tuple[dict[str, list[Any]], MutationReceipt]:
    """Inject an unparseable malformed value into a text/metadata field."""
    _verify_quality_auth(plan, ledger)
    new_records = _copy_records(records)
    family_list = new_records[plan.target_family]
    target_field = plan.target_field or "priority_source_text"
    malformed_val = plan.parameters.get("malformed_value", "MALFORMED_PRIORITY_##%")

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
    mutated_rec = orig_rec.model_copy(update={target_field: malformed_val})
    family_list[found_idx] = mutated_rec
    after_state = {target_field: malformed_val}

    receipt = _consume_quality_auth(plan, ledger, before_state, after_state, (target_field,))
    return new_records, receipt


def apply_exact_duplicate(
    plan: QualityPlan,
    records: dict[str, list[Any]],
    seeds: SeedManager,
    ledger: AuthorizationLedger,
) -> tuple[dict[str, list[Any]], MutationReceipt]:
    """Emit an identical logical duplicate record."""
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
    before_state = {"duplicate_count": 0}
    after_state = {"duplicate_count": 1, "record_id": plan.target_record_id}

    receipt = _consume_quality_auth(
        plan, ledger, before_state, after_state, (f"{plan.target_family}_id",)
    )
    return new_records, receipt


def apply_conflicting_duplicate(
    plan: QualityPlan,
    records: dict[str, list[Any]],
    seeds: SeedManager,
    ledger: AuthorizationLedger,
) -> tuple[dict[str, list[Any]], MutationReceipt]:
    """Emit the same scoped source ID with changed content and unincremented version."""
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

    new_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"conflict-{plan.target_record_id}")
    conflicting_rec = found_rec.model_copy(
        update={
            f"{plan.target_family}_id": new_uuid,
            "severity": "CRITICAL" if getattr(found_rec, "severity", None) != "CRITICAL" else "LOW",
        }
    )
    family_list.append(conflicting_rec)

    before_state = {"conflicting": False}
    after_state = {
        "conflicting": True,
        "source_id": getattr(found_rec, f"source_{plan.target_family}_id", None),
    }

    receipt = _consume_quality_auth(
        plan, ledger, before_state, after_state, (f"source_{plan.target_family}_id", "severity")
    )
    return new_records, receipt


def apply_broken_relationship(
    plan: QualityPlan,
    records: dict[str, list[Any]],
    seeds: SeedManager,
    ledger: AuthorizationLedger,
) -> tuple[dict[str, list[Any]], MutationReceipt]:
    """Replace a foreign relationship ID with an unresolved target."""
    _verify_quality_auth(plan, ledger)
    new_records = _copy_records(records)
    family_list = new_records[plan.target_family]
    target_fk = plan.target_relationship or "alert_id"
    broken_uuid = UUID("00000000-0000-0000-0000-000000000000")

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
    before_state = {target_fk: str(getattr(orig_rec, target_fk, None))}
    mutated_rec = orig_rec.model_copy(update={target_fk: broken_uuid})
    family_list[found_idx] = mutated_rec
    after_state = {target_fk: str(broken_uuid)}

    receipt = _consume_quality_auth(plan, ledger, before_state, after_state, (target_fk,))
    return new_records, receipt


def apply_timestamp_problem(
    plan: QualityPlan,
    records: dict[str, list[Any]],
    seeds: SeedManager,
    ledger: AuthorizationLedger,
) -> tuple[dict[str, list[Any]], MutationReceipt]:
    """Create an inconsistent timestamp or out-of-order sequence."""
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
    offset_time = orig_time + timedelta(days=400)
    before_state = {target_field: orig_time.isoformat()}
    mutated_rec = orig_rec.model_copy(update={target_field: offset_time})
    family_list[found_idx] = mutated_rec
    after_state = {target_field: offset_time.isoformat()}

    receipt = _consume_quality_auth(plan, ledger, before_state, after_state, (target_field,))
    return new_records, receipt


def apply_schema_drift(
    plan: QualityPlan,
    records: dict[str, list[Any]],
    seeds: SeedManager,
    ledger: AuthorizationLedger,
) -> tuple[dict[str, list[Any]], MutationReceipt]:
    """Alter schema metadata or profile version string."""
    _verify_quality_auth(plan, ledger)
    new_records = _copy_records(records)
    family_list = new_records[plan.target_family]
    target_field = plan.target_field or "workflow_version"

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
    drifted_version = "v2_drifted_layout"
    before_state = {target_field: getattr(orig_rec, target_field, None)}
    mutated_rec = orig_rec.model_copy(update={target_field: drifted_version})
    family_list[found_idx] = mutated_rec
    after_state = {target_field: drifted_version}

    receipt = _consume_quality_auth(plan, ledger, before_state, after_state, (target_field,))
    return new_records, receipt


def apply_vocabulary_drift(
    plan: QualityPlan,
    records: dict[str, list[Any]],
    seeds: SeedManager,
    ledger: AuthorizationLedger,
) -> tuple[dict[str, list[Any]], MutationReceipt]:
    """Emit an unmapped or new vocabulary token."""
    _verify_quality_auth(plan, ledger)
    new_records = _copy_records(records)
    family_list = new_records[plan.target_family]
    target_field = plan.target_field or "priority_source_text"
    drift_token = "DRIFT_TIER_99_UNKNOWN"

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
    mutated_rec = orig_rec.model_copy(update={target_field: drift_token})
    family_list[found_idx] = mutated_rec
    after_state = {target_field: drift_token}

    receipt = _consume_quality_auth(plan, ledger, before_state, after_state, (target_field,))
    return new_records, receipt


def apply_late_arrival(
    plan: QualityPlan,
    records: dict[str, list[Any]],
    seeds: SeedManager,
    ledger: AuthorizationLedger,
) -> tuple[dict[str, list[Any]], MutationReceipt]:
    """Move record submission reference to a later submission."""
    _verify_quality_auth(plan, ledger)
    new_records = _copy_records(records)
    family_list = new_records[plan.target_family]
    submissions = new_records["submission"]
    later_sub = submissions[-1] if len(submissions) > 1 else submissions[0]

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
    before_state = {"submission_id": str(getattr(orig_rec, "submission_id", None))}
    mutated_rec = orig_rec.model_copy(update={"submission_id": later_sub.submission_id})
    family_list[found_idx] = mutated_rec
    after_state = {"submission_id": str(later_sub.submission_id)}

    receipt = _consume_quality_auth(plan, ledger, before_state, after_state, ("submission_id",))
    return new_records, receipt


def apply_count_mismatch(
    plan: QualityPlan,
    records: dict[str, list[Any]],
    seeds: SeedManager,
    ledger: AuthorizationLedger,
) -> tuple[dict[str, list[Any]], MutationReceipt]:
    """Alter declared count in submission family declaration without changing actual rows."""
    _verify_quality_auth(plan, ledger)
    new_records = _copy_records(records)
    sub_fams = new_records["submission_family"]

    found_idx = -1
    for idx, rec in enumerate(sub_fams):
        if str(rec.submission_family_id) == plan.target_record_id:
            found_idx = idx
            break

    if found_idx == -1:
        raise QualityMutationError(f"Submission family '{plan.target_record_id}' not found")

    orig_rec = sub_fams[found_idx]
    actual_count = orig_rec.declared_record_count or 0
    mismatched_count = actual_count + 15
    before_state = {"declared_record_count": actual_count}
    mutated_rec = orig_rec.model_copy(update={"declared_record_count": mismatched_count})
    sub_fams[found_idx] = mutated_rec
    after_state = {"declared_record_count": mismatched_count}

    receipt = _consume_quality_auth(
        plan, ledger, before_state, after_state, ("declared_record_count",)
    )
    return new_records, receipt


def apply_source_id_absence(
    plan: QualityPlan,
    records: dict[str, list[Any]],
    seeds: SeedManager,
    ledger: AuthorizationLedger,
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
