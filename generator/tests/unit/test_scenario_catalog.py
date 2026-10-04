"""Unit tests for M4 scenario catalog."""

from __future__ import annotations

import pytest

from satsa_generator.scenarios.catalog import (
    CATALOG_VERSION,
    get_catalog,
    get_scenario,
    get_scenarios_by_family,
    validate_catalog,
)
from satsa_generator.scenarios.models import (
    ControlContextType,
    RealizationState,
    ScenarioFamily,
)


def test_catalog_version_and_validation() -> None:
    """Catalog version must be set and validation must find zero errors."""
    assert CATALOG_VERSION == "1.0.0"
    errors = validate_catalog()
    assert errors == []


def test_all_seven_scenario_families_represented() -> None:
    """All 7 required scenario families must have at least one scenario definition."""
    catalog = get_catalog()
    represented_families = {defn.family for defn in catalog.values()}

    for family in ScenarioFamily:
        assert family in represented_families, f"Family {family} missing from catalog"


def test_scenario_catalog_definitions() -> None:
    """Validate properties of each scenario definition in the catalog."""
    catalog = get_catalog()
    assert len(catalog) >= 8

    expected_scenarios = [
        ("EXEC-GAP-001", ScenarioFamily.EXECUTION_GAP),
        ("EXEC-GAP-002", ScenarioFamily.EXECUTION_GAP),
        ("NEG-SPACE-001", ScenarioFamily.NEGATIVE_SPACE),
        ("NEG-SPACE-002", ScenarioFamily.NEGATIVE_SPACE),
        ("HIST-REP-001", ScenarioFamily.HISTORICAL_REPETITION),
        ("PEER-CMP-001", ScenarioFamily.PEER_COMPARISON),
        ("CROSS-REC-001", ScenarioFamily.CROSS_RECORD),
        ("LEGIT-CTRL-001", ScenarioFamily.LEGITIMATE_UNUSUAL),
        ("AMBIG-001", ScenarioFamily.AMBIGUOUS_INSUFFICIENT),
    ]

    for scen_id, family in expected_scenarios:
        assert scen_id in catalog
        defn = catalog[scen_id]
        assert defn.family == family
        assert len(defn.description) > 0
        assert len(defn.applicable_realizations) > 0
        assert len(defn.evidence_families_touched) > 0


def test_get_scenario_and_get_by_family() -> None:
    """Test lookup helpers and error handling."""
    defn = get_scenario("EXEC-GAP-001")
    assert defn.scenario_id == "EXEC-GAP-001"

    exec_scenarios = get_scenarios_by_family(ScenarioFamily.EXECUTION_GAP)
    assert len(exec_scenarios) == 2
    assert {s.scenario_id for s in exec_scenarios} == {"EXEC-GAP-001", "EXEC-GAP-002"}

    with pytest.raises(KeyError, match="Unknown scenario ID"):
        get_scenario("NON-EXISTENT-999")


def test_realization_state_support() -> None:
    """Each scenario must clearly document applicable and inapplicable realizations."""
    catalog = get_catalog()

    # EXEC-GAP-001 supports all 4 realizations
    exec_001 = catalog["EXEC-GAP-001"]
    assert RealizationState.CONCERNING in exec_001.applicable_realizations
    assert RealizationState.LEGITIMATE_UNUSUAL in exec_001.applicable_realizations
    assert RealizationState.AMBIGUOUS in exec_001.applicable_realizations
    assert RealizationState.NORMAL in exec_001.applicable_realizations

    # LEGIT-CTRL-001 only supports LEGITIMATE_UNUSUAL and NORMAL
    legit_001 = catalog["LEGIT-CTRL-001"]
    assert legit_001.applicable_realizations == [
        RealizationState.LEGITIMATE_UNUSUAL,
        RealizationState.NORMAL,
    ]
    assert "CONCERNING" in legit_001.inapplicable_realization_reasons
    assert "AMBIGUOUS" in legit_001.inapplicable_realization_reasons


def test_legitimate_control_requirements() -> None:
    """Scenarios with LEGITIMATE_UNUSUAL must specify control requirements."""
    catalog = get_catalog()

    exec_001 = catalog["EXEC-GAP-001"]
    assert ControlContextType.APPROVED_AUTOMATION in exec_001.legitimate_control_requirements

    neg_001 = catalog["NEG-SPACE-001"]
    assert ControlContextType.MAINTENANCE_WINDOW in neg_001.legitimate_control_requirements
