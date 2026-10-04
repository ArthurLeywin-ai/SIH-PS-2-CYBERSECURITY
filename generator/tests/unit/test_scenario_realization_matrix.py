"""Dedicated acceptance test for M4 realization matrix coverage across all 7 scenario families.

Authoritative acceptance requirement:
"each family has positive/control/ambiguous/insufficient realization in fixture;
no detector config dependency; ground truth separate."
"""

from __future__ import annotations

from typing import Any

import pytest

from satsa_generator.ids.service import IDService
from satsa_generator.scenarios.catalog import get_catalog, get_scenario
from satsa_generator.scenarios.engine import ScenarioEngine
from satsa_generator.scenarios.models import (
    RealizationState,
    ScenarioFamily,
)
from satsa_generator.scenarios.selectors import ScenarioSelector, SelectionError
from satsa_generator.seeds.manager import SeedManager


def test_realization_matrix_executed_in_fixture(
    master_seed: bytes,
    base_m2_records: dict[str, list[Any]],
) -> None:
    """Validate that executed fixture contains full realization matrix for all 7 families."""
    seeds = SeedManager(master_seed)
    ids = IDService("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    engine = ScenarioEngine(ids, seeds)

    result = engine.run_scenarios(base_m2_records)

    # 1. Collect executed instances grouped by (family, realization)
    coverage: dict[tuple[ScenarioFamily, RealizationState], list[str]] = {}
    for gt in result.ground_truth_records:
        key = (gt.scenario_family, gt.realization)
        coverage.setdefault(key, []).append(gt.scenario_id)

    # Expected realizations per family according to authoritative M4 specification
    expected_family_realizations: dict[ScenarioFamily, set[RealizationState]] = {
        ScenarioFamily.EXECUTION_GAP: {
            RealizationState.CONCERNING,
            RealizationState.LEGITIMATE_UNUSUAL,
            RealizationState.AMBIGUOUS,
            RealizationState.NORMAL,
        },
        ScenarioFamily.NEGATIVE_SPACE: {
            RealizationState.CONCERNING,
            RealizationState.LEGITIMATE_UNUSUAL,
            RealizationState.AMBIGUOUS,
            RealizationState.NORMAL,
        },
        ScenarioFamily.HISTORICAL_REPETITION: {
            RealizationState.CONCERNING,
            RealizationState.LEGITIMATE_UNUSUAL,
            RealizationState.AMBIGUOUS,
            RealizationState.NORMAL,
        },
        ScenarioFamily.PEER_COMPARISON: {
            RealizationState.CONCERNING,
            RealizationState.LEGITIMATE_UNUSUAL,
            RealizationState.AMBIGUOUS,
            RealizationState.NORMAL,
        },
        ScenarioFamily.CROSS_RECORD: {
            RealizationState.CONCERNING,
            RealizationState.LEGITIMATE_UNUSUAL,
            RealizationState.AMBIGUOUS,
            RealizationState.NORMAL,
        },
        ScenarioFamily.LEGITIMATE_UNUSUAL: {
            RealizationState.LEGITIMATE_UNUSUAL,
            RealizationState.AMBIGUOUS,
            RealizationState.NORMAL,
        },
        ScenarioFamily.AMBIGUOUS_INSUFFICIENT: {
            RealizationState.AMBIGUOUS,
            RealizationState.NORMAL,
        },
    }

    # 2. Assert every family has executed realizations (fail loudly if only in catalog)
    executed_families = {f for (f, _) in coverage}
    for family in ScenarioFamily:
        assert family in executed_families, (
            f"Family {family.value} defined in catalog but has NO executed realization in fixture!"
        )

    # 3. Assert every expected realization for each family is actually executed in the fixture
    total_expected = 0
    for family, expected_realizations in expected_family_realizations.items():
        for real_state in expected_realizations:
            total_expected += 1
            matching = coverage.get((family, real_state), [])
            assert len(matching) > 0, (
                f"Missing executed realization ({family.value}, {real_state.value}) in fixture. "
                f"Expected coverage: {[r.value for r in expected_realizations]}"
            )

    # 4. Total executed scenario instances must equal expected matrix count (25)
    assert len(result.ground_truth_records) == total_expected
    assert len(result.validation_reports) == total_expected

    # 5. Every single executed realization passed validation
    for report in result.validation_reports:
        assert report.passed is True, (
            f"Scenario {report.scenario_id} failed validation: {report.errors}"
        )


def test_inapplicable_realizations_explicitly_documented_and_enforced(
    master_seed: bytes,
    base_m2_records: dict[str, list[Any]],
) -> None:
    """Inapplicable realizations must be documented with reasons and rejected at selection."""
    seeds = SeedManager(master_seed)
    ids = IDService("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    selector = ScenarioSelector(seeds, ids)
    org_id = str(base_m2_records["organization"][0].organization_id)

    # LEGIT-CTRL-001: CONCERNING is inapplicable by definition
    legit_defn = get_scenario("LEGIT-CTRL-001")
    assert RealizationState.CONCERNING not in legit_defn.applicable_realizations
    assert "CONCERNING" in legit_defn.inapplicable_realization_reasons
    assert len(legit_defn.inapplicable_realization_reasons["CONCERNING"]) > 0

    with pytest.raises(SelectionError, match="not applicable"):
        selector.select(legit_defn, RealizationState.CONCERNING, base_m2_records, org_id, "P01")

    # AMBIG-001: CONCERNING and LEGITIMATE_UNUSUAL are inapplicable
    ambig_defn = get_scenario("AMBIG-001")
    assert RealizationState.CONCERNING not in ambig_defn.applicable_realizations
    assert RealizationState.LEGITIMATE_UNUSUAL not in ambig_defn.applicable_realizations
    assert "CONCERNING" in ambig_defn.inapplicable_realization_reasons
    assert "LEGITIMATE_UNUSUAL" in ambig_defn.inapplicable_realization_reasons

    with pytest.raises(SelectionError, match="not applicable"):
        selector.select(ambig_defn, RealizationState.CONCERNING, base_m2_records, org_id, "P01")

    with pytest.raises(SelectionError, match="not applicable"):
        selector.select(
            ambig_defn, RealizationState.LEGITIMATE_UNUSUAL, base_m2_records, org_id, "P01"
        )


def test_all_seven_families_present_in_catalog() -> None:
    """All 7 scenario families must be present in the scenario catalog."""
    catalog = get_catalog()
    catalog_families = {defn.family for defn in catalog.values()}
    for family in ScenarioFamily:
        assert family in catalog_families, f"Family {family.value} missing from catalog"
