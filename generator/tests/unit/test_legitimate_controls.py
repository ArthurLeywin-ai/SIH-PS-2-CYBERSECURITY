"""Unit tests for M4 legitimate control engine."""

from __future__ import annotations

import dataclasses
from typing import Any

import pytest

from satsa_generator.ids.service import IDService
from satsa_generator.scenarios.catalog import get_scenario
from satsa_generator.scenarios.controls import (
    LegitimateControlEngine,
    LegitimateControlError,
)
from satsa_generator.scenarios.ledger import AuthorizationLedger
from satsa_generator.scenarios.models import (
    ControlContextType,
    RealizationState,
)
from satsa_generator.scenarios.mutators import ScenarioMutator, plan_authorizations
from satsa_generator.scenarios.selectors import ScenarioSelector
from satsa_generator.scenarios.truth import GroundTruthWriter
from satsa_generator.scenarios.validators import ScenarioValidator
from satsa_generator.seeds.manager import SeedManager


@pytest.fixture
def control_engine_setup(master_seed: bytes) -> tuple[ScenarioSelector, LegitimateControlEngine]:
    seeds = SeedManager(master_seed)
    ids = IDService("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    selector = ScenarioSelector(seeds, ids)
    engine = LegitimateControlEngine(ids, seeds)
    return selector, engine


def test_complete_control_declaration(
    control_engine_setup: tuple[ScenarioSelector, LegitimateControlEngine],
    base_m2_records: dict[str, list[Any]],
) -> None:
    """Complete control declaration generates APPROVED, VALID exception records."""
    selector, engine = control_engine_setup
    org_id = str(base_m2_records["organization"][0].organization_id)

    defn = get_scenario("NEG-SPACE-001")
    plan = selector.select(
        defn,
        RealizationState.LEGITIMATE_UNUSUAL,
        base_m2_records,
        org_id,
        "P01",
        control_context_type=ControlContextType.MAINTENANCE_WINDOW,
        control_context_description="Quarterly infrastructure maintenance window",
    )

    decl, updated = engine.declare_control(plan, base_m2_records, is_complete=True)

    assert decl.is_complete is True
    assert decl.control_context_type == ControlContextType.MAINTENANCE_WINDOW
    assert len(decl.operational_evidence_ids) >= 1

    # Check that ExceptionRecord was injected into updated records
    new_exceptions = updated["exception"]
    assert len(new_exceptions) == len(base_m2_records["exception"]) + 1

    injected = new_exceptions[-1]
    assert str(injected.exception_id) in decl.operational_evidence_ids
    assert injected.approved_state == "APPROVED"
    assert injected.applicability_state == "APPLIES"
    assert injected.exception_quality_state == "VALID"


def test_ambiguous_control_declaration(
    control_engine_setup: tuple[ScenarioSelector, LegitimateControlEngine],
    base_m2_records: dict[str, list[Any]],
) -> None:
    """Ambiguous control declaration generates PENDING, INCOMPLETE exception records."""
    selector, engine = control_engine_setup
    org_id = str(base_m2_records["organization"][0].organization_id)

    defn = get_scenario("NEG-SPACE-001")
    plan = selector.select(
        defn,
        RealizationState.AMBIGUOUS,
        base_m2_records,
        org_id,
        "P01",
        control_context_type=ControlContextType.MAINTENANCE_WINDOW,
        control_context_description="Unconfirmed maintenance window draft",
    )

    decl, updated = engine.declare_control(plan, base_m2_records, is_complete=False)

    assert decl.is_complete is False
    new_exceptions = updated["exception"]
    injected = new_exceptions[-1]
    assert injected.approved_state == "PENDING"
    assert injected.applicability_state == "PARTIALLY_APPLIES"
    assert injected.exception_quality_state == "INCOMPLETE"


def test_process_change_control_generates_process_change_record(
    control_engine_setup: tuple[ScenarioSelector, LegitimateControlEngine],
    base_m2_records: dict[str, list[Any]],
) -> None:
    """VALID_PROCESS_CHANGE generates ExceptionRecord, ProcessChangeRecord, and SubjectLink."""
    selector, engine = control_engine_setup
    org_id = str(base_m2_records["organization"][0].organization_id)

    defn = get_scenario("CROSS-REC-001")
    plan = selector.select(
        defn,
        RealizationState.LEGITIMATE_UNUSUAL,
        base_m2_records,
        org_id,
        "P01",
        control_context_type=ControlContextType.VALID_PROCESS_CHANGE,
        control_context_description="Automated case resolution migration",
    )

    decl, updated = engine.declare_control(plan, base_m2_records, is_complete=True)

    # Injected exception, process_change, and control_process_subject_link records
    assert len(updated["exception"]) == len(base_m2_records["exception"]) + 1
    assert len(updated["process_change"]) == len(base_m2_records["process_change"]) + 1
    link_count = len(base_m2_records.get("control_process_subject_link", [])) + 1
    assert len(updated["control_process_subject_link"]) == link_count
    assert len(decl.operational_evidence_ids) >= 2
    assert decl.control_process_ref_id is not None
    assert decl.control_process_link_id is not None


def test_every_legitimate_unusual_references_real_m2_control_reference(
    control_engine_setup: tuple[ScenarioSelector, LegitimateControlEngine],
    base_m2_records: dict[str, list[Any]],
) -> None:
    """Every LEGITIMATE_UNUSUAL realization anchors to an existing M2 control/process reference."""
    selector, engine = control_engine_setup
    org_id = str(base_m2_records["organization"][0].organization_id)
    real_m2_ref_ids = {
        str(r.control_process_ref_id) for r in base_m2_records["control_process_reference"]
    }

    defn = get_scenario("EXEC-GAP-001")
    plan = selector.select(
        defn,
        RealizationState.LEGITIMATE_UNUSUAL,
        base_m2_records,
        org_id,
        "P01",
        control_context_type=ControlContextType.APPROVED_AUTOMATION,
    )
    assert plan.control_process_ref_id is not None
    assert plan.control_process_ref_id in real_m2_ref_ids

    decl, updated = engine.declare_control(plan, base_m2_records, is_complete=True)
    assert decl.control_process_ref_id == plan.control_process_ref_id
    assert decl.control_process_ref_id in real_m2_ref_ids

    # Check exception rule_expectation_id matches the real M2 control reference
    injected_exc = updated["exception"][-1]
    assert str(injected_exc.rule_expectation_id) == decl.control_process_ref_id


def test_referenced_subject_links_exist_in_operational_evidence(
    control_engine_setup: tuple[ScenarioSelector, LegitimateControlEngine],
    base_m2_records: dict[str, list[Any]],
) -> None:
    """Subject links created by legitimate control declarations exist in operational records."""
    selector, engine = control_engine_setup
    org_id = str(base_m2_records["organization"][0].organization_id)

    defn = get_scenario("NEG-SPACE-001")
    plan = selector.select(
        defn,
        RealizationState.LEGITIMATE_UNUSUAL,
        base_m2_records,
        org_id,
        "P01",
        control_context_type=ControlContextType.MAINTENANCE_WINDOW,
    )

    decl, updated = engine.declare_control(plan, base_m2_records, is_complete=True)
    assert decl.control_process_link_id is not None

    links = updated.get("control_process_subject_link", [])
    matching_links = [
        link for link in links if str(link.control_process_link_id) == decl.control_process_link_id
    ]
    assert len(matching_links) == 1
    link = matching_links[0]
    assert str(link.control_process_ref_id) == decl.control_process_ref_id
    assert link.link_role in ("EXCEPTION_FOR", "SUPPORTS")


def test_invalid_control_reference_fails_loudly(
    control_engine_setup: tuple[ScenarioSelector, LegitimateControlEngine],
    base_m2_records: dict[str, list[Any]],
) -> None:
    """Nonexistent/invalid control_process_ref_id raises LegitimateControlError."""
    selector, engine = control_engine_setup
    org_id = str(base_m2_records["organization"][0].organization_id)

    defn = get_scenario("EXEC-GAP-001")
    plan = selector.select(
        defn,
        RealizationState.LEGITIMATE_UNUSUAL,
        base_m2_records,
        org_id,
        "P01",
        control_context_type=ControlContextType.APPROVED_AUTOMATION,
    )

    # Corrupt control_process_ref_id to a nonexistent reference ID
    corrupted_plan = dataclasses.replace(
        plan, control_process_ref_id="00000000-0000-0000-0000-000000000999"
    )
    with pytest.raises(LegitimateControlError, match="not found in operational evidence"):
        engine.declare_control(corrupted_plan, base_m2_records, is_complete=True)


def test_provenance_preserved_into_ground_truth(
    control_engine_setup: tuple[ScenarioSelector, LegitimateControlEngine],
    base_m2_records: dict[str, list[Any]],
    master_seed: bytes,
) -> None:
    """Legitimate control provenance is preserved into GroundTruthRecord."""
    selector, engine = control_engine_setup
    org_id = str(base_m2_records["organization"][0].organization_id)
    ids = IDService("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    seeds = SeedManager(master_seed)
    ledger = AuthorizationLedger()
    mutator = ScenarioMutator(seeds, ledger)
    validator = ScenarioValidator(ledger)
    truth_writer = GroundTruthWriter(ids)

    defn = get_scenario("NEG-SPACE-001")
    plan = selector.select(
        defn,
        RealizationState.LEGITIMATE_UNUSUAL,
        base_m2_records,
        org_id,
        "P01",
        control_context_type=ControlContextType.MAINTENANCE_WINDOW,
    )

    decl, updated = engine.declare_control(plan, base_m2_records, is_complete=True)

    # Pre-authorize plan
    for auth in plan_authorizations(plan):
        ledger.authorize(auth)

    mutated, receipts = mutator.mutate(defn, plan, updated)
    report = validator.validate(plan, mutated, receipts, fail_loudly=True)
    gt = truth_writer.build_and_record(plan, receipts, report, control_declaration=decl)

    assert gt.classification == "LEGITIMATE_UNUSUAL"
    assert gt.control_process_ref_id == decl.control_process_ref_id
    assert gt.control_process_link_id == decl.control_process_link_id
    assert gt.control_declaration_id == str(decl.control_declaration_id)
    assert gt.control_process_ref_id is not None
