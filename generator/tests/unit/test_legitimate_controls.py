"""Unit tests for M4 legitimate control engine."""

from __future__ import annotations

from typing import Any

import pytest

from satsa_generator.ids.service import IDService
from satsa_generator.scenarios.catalog import get_scenario
from satsa_generator.scenarios.controls import LegitimateControlEngine
from satsa_generator.scenarios.models import (
    ControlContextType,
    RealizationState,
)
from satsa_generator.scenarios.selectors import ScenarioSelector
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
    """VALID_PROCESS_CHANGE generates both ExceptionRecord and ProcessChangeRecord."""
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

    # Injected both exception and process_change records
    assert len(updated["exception"]) == len(base_m2_records["exception"]) + 1
    assert len(updated["process_change"]) == len(base_m2_records["process_change"]) + 1
    assert len(decl.operational_evidence_ids) == 2
