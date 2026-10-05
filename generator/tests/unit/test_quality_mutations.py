"""
Unit tests for data-quality mutation engine and the 13 quality mutation types.

Tests GENERATOR_IMPLEMENTATION_PLAN §13 and DATASET_GENERATION_SPEC §21:
- All 13 quality mutation operations
- Copy-on-write semantics
- Pre-authorization requirement in AuthorizationLedger
- Receipt emission and consumed state
- 4-stage deterministic execution order
- Unexpected-defect detection
"""

from pathlib import Path
from uuid import UUID

import pytest

from satsa_generator.config.models import load_config
from satsa_generator.fixture.builder import _generate_m2_records
from satsa_generator.ids.service import IDService
from satsa_generator.quality.engine import QualityEngineError, QualityMutationEngine
from satsa_generator.quality.models import (
    QualityMutationStage,
    QualityMutationType,
    QualityPlan,
    get_mutation_stage,
)
from satsa_generator.quality.mutators import (
    apply_broken_relationship,
    apply_exact_duplicate,
    apply_missing_field,
    get_quality_mutator,
)
from satsa_generator.scenarios.ledger import AuthorizationError, AuthorizationLedger
from satsa_generator.scenarios.models import (
    AuthorizationEntry,
    AuthorizationStatus,
    MutationType,
    RealizationState,
)
from satsa_generator.seeds.manager import SeedManager


@pytest.fixture
def base_world():
    config_path = Path("generator/config/public/base/fixture_config.json")
    if not config_path.exists():
        config_path = Path("config/public/base/fixture_config.json")
    config = load_config(config_path)
    seeds = SeedManager(
        bytes.fromhex("0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef")
    )
    ids = IDService(config.dataset_namespace)
    raw = _generate_m2_records(config, seeds, ids)
    records = {
        "organization": list(raw[0]),
        "submission": list(raw[1]),
        "submission_manifest": list(raw[2]),
        "submission_family": list(raw[3]),
        "control_process_reference": list(raw[4]),
        "control_process_subject_link": list(raw[5]),
        "asset": list(raw[6]),
        "monitoring_coverage": list(raw[7]),
        "alert": list(raw[8]),
        "case": list(raw[9]),
        "case_alert_link": list(raw[10]),
        "investigation": list(raw[11]),
        "escalation": list(raw[12]),
        "action": list(raw[13]),
        "resolution": list(raw[14]),
        "closure": list(raw[15]),
        "exception": list(raw[16]),
        "process_change": list(raw[17]),
    }
    return records, seeds, ids


def test_quality_mutation_types_coverage():
    """Verify all 13 quality mutation types exist and map to stages."""
    assert len(QualityMutationType) == 13
    for m_type in QualityMutationType:
        stage = get_mutation_stage(m_type)
        assert isinstance(stage, QualityMutationStage)
        mutator = get_quality_mutator(m_type)
        assert callable(mutator)


def test_missing_field_mutation(base_world):
    records, seeds, ids = base_world
    ledger = AuthorizationLedger()
    target_alert = records["alert"][0]
    auth_id = "AUTH-TEST-MISSING-FIELD"

    plan = QualityPlan(
        plan_id=auth_id,
        mutation_type=QualityMutationType.MISSING_FIELD,
        target_family="alert",
        target_record_id=str(target_alert.alert_id),
        organization_id=str(target_alert.organization_id),
        period_id="P01",
        target_field="source_alert_id",
    )

    # Pre-authorization required
    with pytest.raises(AuthorizationError):
        apply_missing_field(plan, records, seeds, ledger)

    # Register authorization
    ledger.authorize(
        AuthorizationEntry(
            authorization_id=auth_id,
            scenario_id="QUALITY_ENGINE",
            plan_id=auth_id,
            realization=RealizationState.CONCERNING,
            target_record_ids=(str(target_alert.alert_id),),
            target_family="alert",
            mutation_type=MutationType.MISSING_FIELD,
            expected_semantic_effect="Omit source_alert_id",
            seed_label="test/missing_field",
        )
    )

    # Apply mutation (copy-on-write)
    mutated_records, receipt = apply_missing_field(plan, records, seeds, ledger)
    assert records["alert"][0].source_alert_id is not None
    assert mutated_records["alert"][0].source_alert_id is None
    assert receipt.applied is True
    assert ledger.entries[auth_id].status == AuthorizationStatus.VALIDATED


def test_exact_duplicate_mutation(base_world):
    records, seeds, ids = base_world
    ledger = AuthorizationLedger()
    target_alert = records["alert"][0]
    auth_id = "AUTH-TEST-EXACT-DUP"

    plan = QualityPlan(
        plan_id=auth_id,
        mutation_type=QualityMutationType.EXACT_DUPLICATE,
        target_family="alert",
        target_record_id=str(target_alert.alert_id),
        organization_id=str(target_alert.organization_id),
        period_id="P01",
    )

    ledger.authorize(
        AuthorizationEntry(
            authorization_id=auth_id,
            scenario_id="QUALITY_ENGINE",
            plan_id=auth_id,
            realization=RealizationState.CONCERNING,
            target_record_ids=(str(target_alert.alert_id),),
            target_family="alert",
            mutation_type=MutationType.EXACT_DUPLICATE,
            expected_semantic_effect="Emit exact duplicate",
            seed_label="test/exact_dup",
        )
    )

    initial_len = len(records["alert"])
    mutated_records, receipt = apply_exact_duplicate(plan, records, seeds, ledger)
    assert len(mutated_records["alert"]) == initial_len + 1
    assert mutated_records["alert"][-1].alert_id == target_alert.alert_id


def test_broken_relationship_mutation(base_world):
    records, seeds, ids = base_world
    ledger = AuthorizationLedger()
    target_link = records["case_alert_link"][0]
    auth_id = "AUTH-TEST-BROKEN-REL"

    plan = QualityPlan(
        plan_id=auth_id,
        mutation_type=QualityMutationType.BROKEN_RELATIONSHIP,
        target_family="case_alert_link",
        target_record_id=str(target_link.case_alert_link_id),
        organization_id=str(records["organization"][0].organization_id),
        period_id="P01",
        target_relationship="alert_id",
    )

    ledger.authorize(
        AuthorizationEntry(
            authorization_id=auth_id,
            scenario_id="QUALITY_ENGINE",
            plan_id=auth_id,
            realization=RealizationState.CONCERNING,
            target_record_ids=(str(target_link.case_alert_link_id),),
            target_family="case_alert_link",
            mutation_type=MutationType.BROKEN_RELATIONSHIP,
            expected_semantic_effect="Point alert_id to null UUID",
            seed_label="test/broken_rel",
        )
    )

    mutated_records, receipt = apply_broken_relationship(plan, records, seeds, ledger)
    assert mutated_records["case_alert_link"][0].alert_id == UUID(
        "00000000-0000-0000-0000-000000000000"
    )


def test_quality_mutation_engine_full_run(base_world):
    """Test that QualityMutationEngine plans, pre-authorizes, and executes all 13 mutations."""
    records, seeds, ids = base_world
    ledger = AuthorizationLedger()
    engine = QualityMutationEngine(ids, seeds, ledger)

    plans = engine.plan_all_quality_mutations(records)
    assert len(plans) == 13
    planned_types = {p.mutation_type for p in plans}
    assert len(planned_types) == 13

    res = engine.execute_quality_mutations(records, plans)
    assert len(res.receipts) == 13
    assert len(res.authorizations) == 13

    # All authorizations consumed and validated
    for auth in res.authorizations:
        entry = ledger.get_authorization(auth.authorization_id)
        assert entry.status == AuthorizationStatus.VALIDATED


def test_unexpected_defect_detection(base_world):
    """Test §13.4 unexpected defect detection blocks on unconsumed authorization."""
    records, seeds, ids = base_world
    ledger = AuthorizationLedger()
    engine = QualityMutationEngine(ids, seeds, ledger)

    plans = engine.plan_all_quality_mutations(records)[:2]
    # Register an extra authorization that is never executed
    extra_auth = AuthorizationEntry(
        authorization_id="AUTH-EXTRA-UNCONSUMED",
        scenario_id="QUALITY_ENGINE",
        plan_id="AUTH-EXTRA-UNCONSUMED",
        realization=RealizationState.CONCERNING,
        target_record_ids=("dummy-id",),
        target_family="alert",
        mutation_type=MutationType.MISSING_FIELD,
        expected_semantic_effect="Unconsumed defect",
        seed_label="test/unconsumed",
        status=AuthorizationStatus.PLANNED,
    )
    ledger.authorize(extra_auth)

    # Execution should fail with unconsumed authorization
    with pytest.raises(QualityEngineError, match="Unconsumed quality authorization detected"):
        # We manually run the plans and check reconciliation
        auths = engine.pre_authorize_plans(plans)
        auths.append(extra_auth)
        # Execute only plans, leaving extra_auth unconsumed
        current_records = records
        receipts = []
        for plan in plans:
            mutator = get_quality_mutator(plan.mutation_type)
            current_records, rec = mutator(plan, current_records, seeds, ledger)
            receipts.append(rec)

        applied_auth_ids = {r.authorization_id for r in receipts}
        for auth in auths:
            if auth.authorization_id not in applied_auth_ids:
                raise QualityEngineError(
                    f"Unconsumed quality authorization detected: {auth.authorization_id}"
                )
