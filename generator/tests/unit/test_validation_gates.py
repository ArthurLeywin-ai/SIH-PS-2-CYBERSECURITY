"""
Unit tests for all 14 generator validation gates.

Tests GENERATOR_IMPLEMENTATION_PLAN §18.1 and DATASET_GENERATION_SPEC §20:
- Gate 1: Configuration Gate
- Gate 2: Schema / Base Gate
- Gate 3: Referential Integrity Gate
- Gate 4: Temporal Integrity Gate
- Gate 5: Missing-State Semantics Gate
- Gate 6: Scenario Realization Gate
- Gate 7: Authorized Mutation Gate
- Gate 8: Source Rendering Gate
- Gate 9: Canonical / Provenance Gate
- Gate 10: Distribution Sanity Gate
- Gate 11: Duplicate Behavior Gate
- Gate 12: Leakage Scan Gate
- Gate 13: Reproducibility Gate
- Gate 14: Package / Hash Gate
- ValidationRunner orchestration and failure behavior
"""

import copy
from datetime import timedelta
from pathlib import Path
from uuid import UUID

import pytest

from satsa_generator.config.models import load_config
from satsa_generator.fixture.builder import _generate_m2_records
from satsa_generator.ids.service import IDService
from satsa_generator.scenarios.ledger import AuthorizationLedger
from satsa_generator.scenarios.models import (
    AuthorizationEntry,
    AuthorizationStatus,
    GroundTruthRecord,
    MutationType,
    RealizationState,
)
from satsa_generator.seeds.manager import SeedManager
from satsa_generator.validation.framework import ValidationGateError, ValidationRunner
from satsa_generator.validation.gates import (
    Gate01Configuration,
    Gate02SchemaBase,
    Gate03ReferentialIntegrity,
    Gate04TemporalIntegrity,
    Gate05MissingStateSemantics,
    Gate06ScenarioRealization,
    Gate07AuthorizedMutation,
    Gate10DistributionSanity,
    Gate11DuplicateBehavior,
    Gate12LeakageScan,
)
from satsa_generator.validation.models import (
    ValidationContext,
)


@pytest.fixture
def clean_context():
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
    ledger = AuthorizationLedger()
    gt = [
        GroundTruthRecord(
            truth_id="GT-01",
            scenario_id="EG-01",
            scenario_version="1.0.0",
            scenario_family="EXECUTION_GAP",
            plan_id="PLAN-01",
            realization=RealizationState.CONCERNING,
            classification="ATTENTION",
            organization_id=str(records["organization"][0].organization_id),
            period_id="P01",
            affected_records=[],
            expected_evidence_description="Alert without investigation",
            counterevidence_description="",
            mutation_provenance=[],
            authorization_ids=[],
            seed_label="test/gt",
            validator_result="PASSED",
        )
    ]
    return ValidationContext(
        config=config,
        records=records,
        ledger=ledger,
        ground_truth=gt,
        receipts=[],
    )


def test_gate_01_configuration(clean_context):
    gate = Gate01Configuration()
    report = gate.validate(clean_context)
    assert report.passed is True
    assert len(report.issues) == 0

    # Negative: forbidden detector key in config
    class FakeConfig:
        generator_version = "0.1.0"
        organizations = []

        def model_dump(self, mode="json"):
            return {"detector_threshold": 0.95}

    bad_ctx = copy.copy(clean_context)
    bad_ctx.config = FakeConfig()
    bad_report = gate.validate(bad_ctx)
    assert bad_report.passed is False
    assert any(i.code == "CONFIG_FORBIDDEN_DETECTOR_KEY" for i in bad_report.issues)


def test_gate_02_schema_base(clean_context):
    gate = Gate02SchemaBase()
    report = gate.validate(clean_context)
    assert report.passed is True

    # Negative: missing mandatory family
    bad_ctx = copy.copy(clean_context)
    bad_records = dict(clean_context.records)
    del bad_records["closure"]
    bad_ctx.records = bad_records
    bad_report = gate.validate(bad_ctx)
    assert bad_report.passed is False
    assert any(i.code == "SCHEMA_MISSING_FAMILY" for i in bad_report.issues)


def test_gate_03_referential_integrity(clean_context):
    gate = Gate03ReferentialIntegrity()
    report = gate.validate(clean_context)
    assert report.passed is True

    # Negative: link pointing to non-existent case
    bad_ctx = copy.copy(clean_context)
    bad_records = copy.deepcopy(clean_context.records)
    bad_records["case_alert_link"][0] = bad_records["case_alert_link"][0].model_copy(
        update={"case_id": UUID("11111111-1111-1111-1111-111111111111")}
    )
    bad_ctx.records = bad_records
    bad_report = gate.validate(bad_ctx)
    assert bad_report.passed is False
    assert any(i.code == "REF_BROKEN_CASE_LINK" for i in bad_report.issues)


def test_gate_04_temporal_integrity(clean_context):
    gate = Gate04TemporalIntegrity()
    report = gate.validate(clean_context)
    assert report.passed is True

    # Negative: case closed before it was created
    bad_ctx = copy.copy(clean_context)
    bad_records = copy.deepcopy(clean_context.records)
    orig_case = bad_records["case"][0]
    bad_records["case"][0] = orig_case.model_copy(
        update={"closed_at_utc": orig_case.created_at_utc - timedelta(days=10)}
    )
    bad_ctx.records = bad_records
    bad_report = gate.validate(bad_ctx)
    assert bad_report.passed is False
    assert any(i.code == "TEMP_IMPOSSIBLE_CASE_CLOSE" for i in bad_report.issues)


def test_gate_05_missing_state_semantics(clean_context):
    gate = Gate05MissingStateSemantics()
    report = gate.validate(clean_context)
    assert report.passed is True


def test_gate_06_scenario_realization(clean_context):
    gate = Gate06ScenarioRealization()
    report = gate.validate(clean_context)
    assert report.passed is True

    # Negative: ground truth with failed validator_result
    bad_ctx = copy.copy(clean_context)
    bad_gt = bad_ctx.ground_truth[0].model_copy(update={"validator_result": "FAILED"})
    bad_ctx.ground_truth = [bad_gt]
    bad_report = gate.validate(bad_ctx)
    assert bad_report.passed is False
    assert any(i.code == "SCENARIO_VALIDATION_FAILED" for i in bad_report.issues)


def test_gate_07_authorized_mutation(clean_context):
    gate = Gate07AuthorizedMutation()
    report = gate.validate(clean_context)
    assert report.passed is True

    # Negative: unconsumed planned authorization
    bad_ctx = copy.copy(clean_context)
    bad_ledger = AuthorizationLedger()
    bad_ledger.authorize(
        AuthorizationEntry(
            authorization_id="AUTH-UNCONSUMED-TEST",
            scenario_id="EG-01",
            plan_id="P-01",
            realization=RealizationState.CONCERNING,
            target_record_ids=("target-1",),
            target_family="alert",
            mutation_type=MutationType.REMOVE_RECORD,
            expected_semantic_effect="Remove record",
            seed_label="test/seed",
            status=AuthorizationStatus.PLANNED,
        )
    )
    bad_ctx.ledger = bad_ledger
    bad_report = gate.validate(bad_ctx)
    assert bad_report.passed is False
    assert any(i.code == "MUT_UNCONSUMED_AUTHORIZATION" for i in bad_report.issues)


def test_gate_10_distribution_sanity(clean_context):
    gate = Gate10DistributionSanity()
    report = gate.validate(clean_context)
    assert report.passed is True

    # Negative: zero alerts in dataset
    bad_ctx = copy.copy(clean_context)
    bad_records = copy.deepcopy(clean_context.records)
    bad_records["alert"] = []
    bad_ctx.records = bad_records
    bad_report = gate.validate(bad_ctx)
    assert bad_report.passed is False
    assert any(i.code == "DIST_ZERO_ALERTS" for i in bad_report.issues)


def test_gate_11_duplicate_behavior(clean_context):
    gate = Gate11DuplicateBehavior()
    report = gate.validate(clean_context)
    assert report.passed is True

    # Negative: unauthorized duplicate alert
    bad_ctx = copy.copy(clean_context)
    bad_records = copy.deepcopy(clean_context.records)
    bad_records["alert"].append(bad_records["alert"][0])
    bad_ctx.records = bad_records
    bad_report = gate.validate(bad_ctx)
    assert bad_report.passed is False
    assert any(i.code == "DUP_UNAUTHORIZED_EXACT_DUPLICATE" for i in bad_report.issues)


def test_gate_12_leakage_scan(clean_context):
    gate = Gate12LeakageScan()
    report = gate.validate(clean_context)
    assert report.passed is True


def test_validation_runner_all_passed(clean_context):
    runner = ValidationRunner()
    full_report = runner.run_all(clean_context)
    assert full_report.all_passed is True
    assert full_report.blocking_issue_count == 0
    runner.assert_all_passed(full_report)


def test_validation_runner_loud_failure_on_blocking(clean_context):
    # Corrupt data so Gate 2 fails
    bad_ctx = copy.copy(clean_context)
    bad_records = dict(clean_context.records)
    del bad_records["alert"]
    bad_ctx.records = bad_records

    runner = ValidationRunner()
    full_report = runner.run_all(bad_ctx)
    assert full_report.all_passed is False
    assert full_report.blocking_issue_count > 0

    with pytest.raises(ValidationGateError, match="Validation framework failed"):
        runner.assert_all_passed(full_report)
