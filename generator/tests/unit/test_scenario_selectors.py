"""Unit tests for M4 scenario selectors."""

from __future__ import annotations

from typing import Any

import pytest

from satsa_generator.ids.service import IDService
from satsa_generator.scenarios.catalog import get_scenario
from satsa_generator.scenarios.models import (
    ControlContextType,
    RealizationState,
)
from satsa_generator.scenarios.selectors import (
    ScenarioSelector,
    SelectionError,
)
from satsa_generator.seeds.manager import SeedManager


@pytest.fixture
def selector(master_seed: bytes) -> ScenarioSelector:
    seeds = SeedManager(master_seed)
    ids = IDService("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    return ScenarioSelector(seeds, ids)


def test_select_all_nine_scenarios(
    selector: ScenarioSelector,
    base_m2_records: dict[str, list[Any]],
) -> None:
    """Selector successfully selects targets for all 9 scenarios."""
    org_id = str(base_m2_records["organization"][0].organization_id)
    period_id = "P01"

    test_scenarios = [
        ("EXEC-GAP-001", RealizationState.CONCERNING, None),
        ("EXEC-GAP-002", RealizationState.CONCERNING, None),
        ("NEG-SPACE-001", RealizationState.CONCERNING, None),
        ("NEG-SPACE-002", RealizationState.CONCERNING, None),
        ("HIST-REP-001", RealizationState.CONCERNING, None),
        ("PEER-CMP-001", RealizationState.CONCERNING, None),
        (
            "LEGIT-CTRL-001",
            RealizationState.LEGITIMATE_UNUSUAL,
            ControlContextType.LEGITIMATE_BURST,
        ),
        ("AMBIG-001", RealizationState.AMBIGUOUS, None),
    ]

    for scen_id, real_state, ctrl_type in test_scenarios:
        defn = get_scenario(scen_id)
        plan = selector.select(
            scenario=defn,
            realization=real_state,
            records=base_m2_records,
            organization_id=org_id,
            period_id=period_id,
            control_context_type=ctrl_type,
        )
        assert plan.scenario_id == scen_id
        assert plan.realization == real_state
        assert plan.organization_id == org_id
        assert len(plan.target_record_ids) > 0


def test_selector_determinism(
    master_seed: bytes,
    base_m2_records: dict[str, list[Any]],
) -> None:
    ns = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    selector1 = ScenarioSelector(SeedManager(master_seed), IDService(ns))
    selector2 = ScenarioSelector(SeedManager(master_seed), IDService(ns))

    defn = get_scenario("EXEC-GAP-001")
    org_id = str(base_m2_records["organization"][0].organization_id)

    plan1 = selector1.select(defn, RealizationState.CONCERNING, base_m2_records, org_id, "P01")
    plan2 = selector2.select(defn, RealizationState.CONCERNING, base_m2_records, org_id, "P01")

    assert plan1.target_record_ids == plan2.target_record_ids
    assert plan1.plan_id == plan2.plan_id


def test_selector_reservation_avoidance(
    selector: ScenarioSelector,
    base_m2_records: dict[str, list[Any]],
) -> None:
    """Selector avoids selecting already reserved target records."""
    defn = get_scenario("EXEC-GAP-001")
    org_id = str(base_m2_records["organization"][0].organization_id)

    plan1 = selector.select(defn, RealizationState.CONCERNING, base_m2_records, org_id, "P01")
    reserved = set(plan1.target_record_ids)

    # If there are other eligible records, plan2 will choose a different one
    cases = [
        c
        for c in base_m2_records["case"]
        if str(c.organization_id) == org_id
        and c.severity in ("HIGH", "CRITICAL")
        and c.case_status in ("CLOSED", "RESOLVED")
    ]
    if len(cases) > 1:
        plan2 = selector.select(
            defn, RealizationState.CONCERNING, base_m2_records, org_id, "P01", reserved_ids=reserved
        )
        assert plan2.target_record_ids[0] not in reserved


def test_inapplicable_realization_fails(
    selector: ScenarioSelector,
    base_m2_records: dict[str, list[Any]],
) -> None:
    """Selecting an inapplicable realization state raises SelectionError."""
    defn = get_scenario("LEGIT-CTRL-001")  # Does not support CONCERNING
    org_id = str(base_m2_records["organization"][0].organization_id)

    with pytest.raises(SelectionError, match="not applicable"):
        selector.select(defn, RealizationState.CONCERNING, base_m2_records, org_id, "P01")


def test_infeasible_selection_fails_loudly(
    selector: ScenarioSelector,
) -> None:
    """Selector raises SelectionError when no eligible targets exist."""
    defn = get_scenario("EXEC-GAP-001")
    empty_records: dict[str, list[Any]] = {"case": []}

    with pytest.raises(SelectionError, match="No eligible"):
        selector.select(defn, RealizationState.CONCERNING, empty_records, "org-none", "P01")
