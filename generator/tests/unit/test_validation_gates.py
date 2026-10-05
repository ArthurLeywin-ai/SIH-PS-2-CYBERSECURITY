"""Unit tests for all 14 generator validation gates.

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
- ValidationRunner orchestration and loud failure behavior
"""

from __future__ import annotations

import copy
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest

from satsa_generator.config.models import load_config
from satsa_generator.fixture.builder import (
    _generate_m2_records,
    build_fixture,
    parse_master_seed_hex,
)
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
    Gate08SourceRendering,
    Gate09CanonicalProvenance,
    Gate10DistributionSanity,
    Gate11DuplicateBehavior,
    Gate12LeakageScan,
    Gate13Reproducibility,
    Gate14PackageHash,
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


@pytest.fixture(scope="module")
def complete_m5_bundle(tmp_path_factory):
    out_dir = tmp_path_factory.mktemp("complete_m5_bundle")
    config_path = Path("generator/config/public/base/fixture_config.json")
    if not config_path.exists():
        config_path = Path("config/public/base/fixture_config.json")
    seed_bytes = parse_master_seed_hex(
        "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    )
    res = build_fixture(config_path, seed_bytes, output_root=out_dir, milestone="m5")

    # Load manifest and build context
    from satsa_generator.fixture.models import FixtureManifest

    manifest_data = json.loads(res.manifest_path.read_text(encoding="utf-8"))
    manifest = FixtureManifest.model_validate(manifest_data)

    op_root = res.operational_root
    priv_root = out_dir / "private_ground_truth"
    source_root = op_root / "source_exports"
    oracle_root = priv_root / "canonical_reference"

    config = load_config(config_path)
    seeds = SeedManager(seed_bytes)
    ids = IDService(config.dataset_namespace)
    raw = _generate_m2_records(config, seeds, ids)
    pydantic_records = {
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

    gt_data = json.loads((priv_root / "ground_truth.json").read_text(encoding="utf-8"))
    gt_list = [GroundTruthRecord.model_validate(item) for item in gt_data.get("records", [])]

    ledger_path = priv_root / "authorization_ledger.json"
    ledger = AuthorizationLedger()
    if ledger_path.exists():
        ledger_data = json.loads(ledger_path.read_text(encoding="utf-8"))
        entries_list = (
            ledger_data if isinstance(ledger_data, list) else ledger_data.get("entries", [])
        )
        for entry_dict in entries_list:
            ledger.authorize(AuthorizationEntry.model_validate(entry_dict))

    context = ValidationContext(
        config=config,
        records=pydantic_records,
        ledger=ledger,
        ground_truth=gt_list,
        receipts=[],
        operational_root=op_root,
        output_root=out_dir,
        private_root=priv_root,
        manifest=manifest,
        source_exports_root=source_root,
        oracle_root=oracle_root,
        extra={
            "master_seed": seed_bytes,
            "config_path": str(config_path),
            "tree_sha256": res.tree_sha256,
            "record_counts": res.record_counts,
        },
    )
    return context, res, out_dir


def test_gate_01_configuration(clean_context):
    gate = Gate01Configuration()
    report = gate.validate(clean_context)
    assert report.passed is True
    assert len(report.issues) == 0

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


# Gate 8: Source Rendering
def test_gate_08_source_rendering_pass(complete_m5_bundle):
    ctx, _, _ = complete_m5_bundle
    gate = Gate08SourceRendering()
    report = gate.validate(ctx)
    assert report.passed is True
    assert len(report.issues) == 0


def test_gate_08_missing_source_root():
    gate = Gate08SourceRendering()
    ctx = ValidationContext(
        config=None,
        records={},
        ledger=None,
        source_exports_root=Path("/nonexistent/source/dir"),
    )
    report = gate.validate(ctx)
    assert report.passed is False
    assert any(i.code == "RENDER_MISSING_EXPORTS_DIR" for i in report.issues)


def test_gate_08_corrupted_csv_fails(complete_m5_bundle, tmp_path):
    ctx, _, _ = complete_m5_bundle
    bad_src = tmp_path / "bad_src"
    shutil.copytree(ctx.source_exports_root, bad_src)

    # Corrupt CSV to empty header
    csv_file = next(bad_src.glob("*.csv"))
    csv_file.write_text("", encoding="utf-8")

    bad_ctx = copy.copy(ctx)
    bad_ctx.source_exports_root = bad_src
    gate = Gate08SourceRendering()
    report = gate.validate(bad_ctx)
    assert report.passed is False
    assert any(i.code == "RENDER_EMPTY_CSV_HEADER" for i in report.issues)


# Gate 9: Canonical Provenance
def test_gate_09_canonical_provenance_pass(complete_m5_bundle):
    ctx, _, _ = complete_m5_bundle
    gate = Gate09CanonicalProvenance()
    report = gate.validate(ctx)
    assert report.passed is True
    assert len(report.issues) == 0


def test_gate_09_missing_oracle_root():
    gate = Gate09CanonicalProvenance()
    ctx = ValidationContext(
        config=None,
        records={},
        ledger=None,
        source_exports_root=Path("/some/path"),
        oracle_root=None,
    )
    report = gate.validate(ctx)
    assert report.passed is False
    assert any(i.code == "PROV_ORACLE_ROOT_MISSING" for i in report.issues)


def test_gate_09_raw_value_mismatch_fails(complete_m5_bundle, tmp_path):
    ctx, _, _ = complete_m5_bundle
    bad_oracle = tmp_path / "bad_oracle"
    shutil.copytree(ctx.oracle_root, bad_oracle)

    # Alter raw value in provenance file for an unauthorized field
    prov_file = next(bad_oracle.glob("*_provenance.json"))
    p_data = json.loads(prov_file.read_text(encoding="utf-8"))
    if p_data.get("field_provenance"):
        p_data["field_provenance"][0]["raw_value"] = "COMPLETELY_UNEXPECTED_VALUE_9999"
        prov_file.write_text(json.dumps(p_data), encoding="utf-8")

    bad_ctx = copy.copy(ctx)
    bad_ctx.oracle_root = bad_oracle
    # Empty ledger so change cannot be authorized
    bad_ctx.ledger = AuthorizationLedger()
    gate = Gate09CanonicalProvenance()
    report = gate.validate(bad_ctx)
    assert report.passed is False
    assert any(i.code == "PROV_RAW_VALUE_MISMATCH" for i in report.issues)


# Gate 10: Distribution Sanity
def test_gate_10_distribution_sanity_pass(clean_context):
    gate = Gate10DistributionSanity()
    report = gate.validate(clean_context)
    assert report.passed is True


def test_gate_10_zero_alerts(clean_context):
    bad_ctx = copy.copy(clean_context)
    bad_records = copy.deepcopy(clean_context.records)
    bad_records["alert"] = []
    bad_ctx.records = bad_records
    gate = Gate10DistributionSanity()
    bad_report = gate.validate(bad_ctx)
    assert bad_report.passed is False
    assert any(i.code == "DIST_ZERO_ALERTS" for i in bad_report.issues)


def test_gate_10_missing_concerning(clean_context):
    bad_ctx = copy.copy(clean_context)
    bad_ctx.ground_truth = [
        bad_ctx.ground_truth[0].model_copy(update={"realization": RealizationState.NORMAL})
    ]
    gate = Gate10DistributionSanity()
    bad_report = gate.validate(bad_ctx)
    assert bad_report.passed is False
    assert any(i.code == "DIST_MISSING_CONCERNING_REALIZATION" for i in bad_report.issues)


def test_gate_10_identical_timestamps_artifact(clean_context):
    bad_ctx = copy.copy(clean_context)
    bad_records = copy.deepcopy(clean_context.records)
    fixed_time = datetime(2026, 1, 1, 12, 0, 0)
    orig_alert = bad_records["alert"][0]
    bad_records["alert"] = [
        orig_alert.model_copy(update={"created_at_utc": fixed_time, "alert_id": UUID(int=i + 1)})
        for i in range(25)
    ]
    bad_ctx.records = bad_records
    gate = Gate10DistributionSanity()
    report = gate.validate(bad_ctx)
    assert any(i.code == "DIST_IDENTICAL_TIMESTAMPS_ARTIFACT" for i in report.issues)


def test_gate_11_duplicate_behavior(clean_context):
    gate = Gate11DuplicateBehavior()
    report = gate.validate(clean_context)
    assert report.passed is True

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


# Gate 13: Reproducibility
def test_gate_13_reproducibility_pass(complete_m5_bundle):
    ctx, _, _ = complete_m5_bundle
    gate = Gate13Reproducibility()
    report = gate.validate(ctx)
    assert report.passed is True
    assert len(report.issues) == 0


def test_gate_13_missing_seed_context():
    gate = Gate13Reproducibility()
    ctx = ValidationContext(
        config=None,
        records={},
        ledger=None,
        manifest=copy.copy(
            type(
                "FakeManifest",
                (),
                {
                    "version_tuple_sha256": "abc",
                    "stream_fingerprints": {"stream": "def"},
                },
            )()
        ),
        extra={},
    )
    report = gate.validate(ctx)
    assert report.passed is False
    assert any(i.code == "REPRO_MISSING_SEED_CONTEXT" for i in report.issues)


def test_gate_13_modified_seed_fails(complete_m5_bundle):
    ctx, _, _ = complete_m5_bundle
    bad_ctx = copy.copy(ctx)
    # Supply a different master seed
    diff_seed = bytes.fromhex("ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff")
    bad_extra = dict(ctx.extra)
    bad_extra["master_seed"] = diff_seed
    bad_ctx.extra = bad_extra

    gate = Gate13Reproducibility()
    report = gate.validate(bad_ctx)
    assert report.passed is False
    assert any(i.code in ("REPRO_BYTE_MISMATCH", "REPRO_TREE_HASH_MISMATCH") for i in report.issues)


# Gate 14: Package / Hash
def test_gate_14_package_hash_pass(complete_m5_bundle):
    ctx, _, _ = complete_m5_bundle
    gate = Gate14PackageHash()
    report = gate.validate(ctx)
    assert report.passed is True
    assert len(report.issues) == 0


def test_gate_14_missing_manifested_file(complete_m5_bundle, tmp_path):
    ctx, _, _ = complete_m5_bundle
    bad_op = tmp_path / "bad_op_missing"
    shutil.copytree(ctx.operational_root, bad_op)

    # Delete one manifested file
    (bad_op / "cases.json").unlink()

    bad_ctx = copy.copy(ctx)
    bad_ctx.operational_root = bad_op
    gate = Gate14PackageHash()
    report = gate.validate(bad_ctx)
    assert report.passed is False
    assert any(i.code == "PKG_MISSING_MANIFESTED_FILE" for i in report.issues)


def test_gate_14_unexpected_file_fails(complete_m5_bundle, tmp_path):
    ctx, _, _ = complete_m5_bundle
    bad_op = tmp_path / "bad_op_unexpected"
    shutil.copytree(ctx.operational_root, bad_op)

    # Add an unmanifested file
    (bad_op / "unmanifested_extra.json").write_text("{}", encoding="utf-8")

    bad_ctx = copy.copy(ctx)
    bad_ctx.operational_root = bad_op
    gate = Gate14PackageHash()
    report = gate.validate(bad_ctx)
    assert report.passed is False
    assert any(i.code == "PKG_UNEXPECTED_UNMANIFESTED_FILE" for i in report.issues)


def test_gate_14_physical_separation_breach(complete_m5_bundle):
    ctx, _, _ = complete_m5_bundle
    bad_ctx = copy.copy(ctx)
    bad_ctx.private_root = ctx.operational_root / "nested_private"
    bad_ctx.private_root.mkdir(exist_ok=True)

    gate = Gate14PackageHash()
    report = gate.validate(bad_ctx)
    assert report.passed is False
    assert any(i.code == "PKG_PHYSICAL_SEPARATION_BREACH" for i in report.issues)


# ValidationRunner End-to-End
def test_validation_runner_all_passed(complete_m5_bundle):
    ctx, _, _ = complete_m5_bundle
    runner = ValidationRunner()
    full_report = runner.run_all(ctx)
    assert full_report.all_passed is True
    assert full_report.blocking_issue_count == 0
    runner.assert_all_passed(full_report)


def test_validation_runner_loud_failure_on_blocking(clean_context):
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
