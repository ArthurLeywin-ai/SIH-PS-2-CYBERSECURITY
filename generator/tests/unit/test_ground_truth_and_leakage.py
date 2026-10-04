"""Unit tests for M4 private ground truth and leakage prevention."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from satsa_generator.ids.service import IDService
from satsa_generator.scenarios.catalog import get_scenario
from satsa_generator.scenarios.controls import LegitimateControlEngine
from satsa_generator.scenarios.ledger import AuthorizationLedger
from satsa_generator.scenarios.models import (
    ControlContextType,
    RealizationState,
    TruthRecordRole,
)
from satsa_generator.scenarios.mutators import ScenarioMutator
from satsa_generator.scenarios.selectors import ScenarioSelector
from satsa_generator.scenarios.truth import (
    GroundTruthWriter,
    LeakageError,
    LeakageScanner,
)
from satsa_generator.scenarios.validators import ScenarioValidator
from satsa_generator.seeds.manager import SeedManager

type TruthSetup = tuple[
    ScenarioSelector,
    ScenarioMutator,
    LegitimateControlEngine,
    ScenarioValidator,
    GroundTruthWriter,
]


@pytest.fixture
def truth_setup(master_seed: bytes) -> TruthSetup:
    seeds = SeedManager(master_seed)
    ids = IDService("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    ledger = AuthorizationLedger()
    selector = ScenarioSelector(seeds, ids)
    mutator = ScenarioMutator(seeds, ledger)
    controls = LegitimateControlEngine(ids, seeds)
    validator = ScenarioValidator(ledger)
    truth_writer = GroundTruthWriter(ids)
    return selector, mutator, controls, validator, truth_writer


def test_ground_truth_record_creation(
    truth_setup: TruthSetup,
    base_m2_records: dict[str, list[Any]],
    tmp_path: Path,
) -> None:
    """GroundTruthRecord captures full private provenance and serializes to disk."""
    selector, mutator, _, validator, truth_writer = truth_setup
    org_id = str(base_m2_records["organization"][0].organization_id)

    defn = get_scenario("EXEC-GAP-001")
    plan = selector.select(defn, RealizationState.CONCERNING, base_m2_records, org_id, "P01")

    mutated_records, receipts = mutator.mutate(defn, plan, base_m2_records)
    report = validator.validate(plan, mutated_records, receipts, fail_loudly=True)

    gt_record = truth_writer.build_and_record(plan, receipts, report)

    assert gt_record.scenario_id == "EXEC-GAP-001"
    assert gt_record.classification == "ATTENTION"
    assert gt_record.validator_result == "PASSED"
    assert len(gt_record.affected_records) >= 1
    assert gt_record.affected_records[0]["role"] == TruthRecordRole.AFFECTED.value
    assert len(gt_record.mutation_provenance) >= 1
    assert len(gt_record.authorization_ids) >= 1

    # Test writing to private directory
    private_dir = tmp_path / "private_truth"
    written_file = truth_writer.write_to_directory(private_dir)
    assert written_file.exists()
    assert written_file.is_file()


def test_classification_mapping_for_all_realizations(
    truth_setup: TruthSetup,
    base_m2_records: dict[str, list[Any]],
) -> None:
    """Verify classifications: CONCERNING->ATTENTION, LEGITIMATE_UNUSUAL, etc."""
    selector, mutator, controls, validator, truth_writer = truth_setup
    org_id = str(base_m2_records["organization"][0].organization_id)

    defn = get_scenario("NEG-SPACE-001")

    # CONCERNING
    plan_c = selector.select(defn, RealizationState.CONCERNING, base_m2_records, org_id, "P01")
    mut_c, rec_c = mutator.mutate(defn, plan_c, base_m2_records)
    rep_c = validator.validate(plan_c, mut_c, rec_c)
    gt_c = truth_writer.build_and_record(plan_c, rec_c, rep_c)
    assert gt_c.classification == "ATTENTION"

    # LEGITIMATE_UNUSUAL
    plan_l = selector.select(
        defn,
        RealizationState.LEGITIMATE_UNUSUAL,
        base_m2_records,
        org_id,
        "P01",
        control_context_type=ControlContextType.MAINTENANCE_WINDOW,
    )
    decl_l, upd_l = controls.declare_control(plan_l, base_m2_records, is_complete=True)
    mut_l, rec_l = mutator.mutate(defn, plan_l, upd_l)
    rep_l = validator.validate(plan_l, mut_l, rec_l)
    gt_l = truth_writer.build_and_record(plan_l, rec_l, rep_l, control_declaration=decl_l)
    assert gt_l.classification == "LEGITIMATE_UNUSUAL"

    # AMBIGUOUS
    plan_a = selector.select(defn, RealizationState.AMBIGUOUS, base_m2_records, org_id, "P01")
    mut_a, rec_a = mutator.mutate(defn, plan_a, base_m2_records)
    rep_a = validator.validate(plan_a, mut_a, rec_a)
    gt_a = truth_writer.build_and_record(plan_a, rec_a, rep_a)
    assert gt_a.classification == "AMBIGUOUS"
    assert gt_a.abstention_state == "INSUFFICIENT_EVIDENCE"

    # NORMAL
    plan_n = selector.select(defn, RealizationState.NORMAL, base_m2_records, org_id, "P01")
    mut_n, rec_n = mutator.mutate(defn, plan_n, base_m2_records)
    rep_n = validator.validate(plan_n, mut_n, rec_n)
    gt_n = truth_writer.build_and_record(plan_n, rec_n, rep_n)
    assert gt_n.classification == "NORMAL"


def test_leakage_scanner_clean_data() -> None:
    """Clean operational data passes leakage scanner with zero violations."""
    clean_payload = {
        "cases": [
            {
                "case_id": "11111111-1111-1111-1111-111111111111",
                "severity": "HIGH",
                "disposition": "TRUE_POSITIVE",
                "status": "CLOSED",
            }
        ]
    }
    leaks = LeakageScanner.scan_operational_dict(clean_payload)
    assert leaks == []
    # assert_no_leakage does not raise
    LeakageScanner.assert_no_leakage(clean_payload)


def test_leakage_scanner_detects_forbidden_keys() -> None:
    """Forbidden keys in operational dictionary trigger LeakageError."""
    leaky_dict = {
        "scenario_id": "EXEC-GAP-001",
        "data": "some value",
    }
    with pytest.raises(LeakageError, match="leakage detected"):
        LeakageScanner.assert_no_leakage(leaky_dict)


def test_leakage_scanner_detects_forbidden_values() -> None:
    """Forbidden values (scenario codes, seeds) trigger LeakageError."""
    leaky_payload = {
        "records": [
            {"notes": "Planted for scenario EXEC-GAP-001 evaluation"},
        ]
    }
    with pytest.raises(LeakageError, match="leakage detected"):
        LeakageScanner.assert_no_leakage(leaky_payload)

    leaky_seed_payload = {
        "provenance": {"seed": "development/scenario/EXEC-GAP-001/v1"},
    }
    with pytest.raises(LeakageError, match="leakage detected"):
        LeakageScanner.assert_no_leakage(leaky_seed_payload)
