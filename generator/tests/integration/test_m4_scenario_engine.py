"""Integration tests for M4 scenario engine."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from satsa_generator.ids.service import IDService
from satsa_generator.scenarios.engine import ScenarioEngine
from satsa_generator.scenarios.models import (
    RealizationState,
    ScenarioFamily,
)
from satsa_generator.scenarios.truth import LeakageScanner
from satsa_generator.seeds.manager import SeedManager


def test_scenario_engine_full_run(
    master_seed: bytes,
    base_m2_records: dict[str, list[Any]],
    tmp_path: Path,
) -> None:
    """Full execution of ScenarioEngine produces valid mutated world, reports, and truth."""
    seeds = SeedManager(master_seed)
    ids = IDService("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    engine = ScenarioEngine(ids, seeds)

    result = engine.run_scenarios(base_m2_records)

    # 1. Validation reports: all scenarios passed semantic validation
    assert len(result.validation_reports) > 0
    assert all(r.passed for r in result.validation_reports)

    # 2. Ground truth records: all scenarios recorded with private provenance
    assert len(result.ground_truth_records) == len(result.validation_reports)

    # 3. All 7 scenario families are represented in ground truth
    represented_families = {r.scenario_family for r in result.ground_truth_records}
    for family in ScenarioFamily:
        assert family in represented_families, f"Family {family} missing from execution"

    # 4. Realization states: CONCERNING, LEGITIMATE_UNUSUAL, AMBIGUOUS, NORMAL all present
    realizations = {r.realization for r in result.ground_truth_records}
    assert RealizationState.CONCERNING in realizations
    assert RealizationState.LEGITIMATE_UNUSUAL in realizations
    assert RealizationState.AMBIGUOUS in realizations
    assert RealizationState.NORMAL in realizations

    # 5. Ledger completeness: no unused authorizations
    assert result.ledger.validate_completeness() == []

    # 6. Private package written and verified
    private_dir = engine.write_private_package(tmp_path)
    assert (private_dir / "ground_truth.json").is_file()
    assert (private_dir / "authorization_ledger.json").is_file()

    # 7. Zero leakage in operational records
    for _family_name, records in result.records.items():
        for rec in records:
            if hasattr(rec, "model_dump"):
                LeakageScanner.assert_no_leakage(rec.model_dump(mode="json"))


def test_scenario_engine_determinism(
    master_seed: bytes,
    base_m2_records: dict[str, list[Any]],
) -> None:
    """Running ScenarioEngine with the same seed produces identical results."""
    seeds1 = SeedManager(master_seed)
    ids1 = IDService("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    engine1 = ScenarioEngine(ids1, seeds1)
    res1 = engine1.run_scenarios(base_m2_records)

    seeds2 = SeedManager(master_seed)
    ids2 = IDService("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    engine2 = ScenarioEngine(ids2, seeds2)
    res2 = engine2.run_scenarios(base_m2_records)

    assert len(res1.ground_truth_records) == len(res2.ground_truth_records)
    for gt1, gt2 in zip(res1.ground_truth_records, res2.ground_truth_records, strict=True):
        assert gt1.truth_id == gt2.truth_id
        assert gt1.scenario_id == gt2.scenario_id
        assert gt1.classification == gt2.classification
        assert gt1.affected_records == gt2.affected_records
