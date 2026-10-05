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
from satsa_generator.quality.models import QualityMutationType, QualityPlan
from satsa_generator.quality.mutators import (
    QualityMutationError,
    _apply_source_file_mutation,
)
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


# ===========================================================================
# Focused Regression Tests for M5 Blocker Remediation
# ===========================================================================


def test_m5_source_representation_derived_from_finalized_m4_state(complete_m5_bundle):
    """Verify that M5 source exports are derived from the finalized M4 state."""
    ctx, _, _ = complete_m5_bundle
    source_root = ctx.source_exports_root
    alert_csv = source_root / "alert_src-a.csv"
    assert alert_csv.exists()

    # The number of alerts in the rendered file should correspond to post-M4 realization
    lines = alert_csv.read_text(encoding="utf-8").strip().splitlines()
    data_rows = lines[1:]  # exclude header
    # Must have records rendered from post-M4 alerts
    assert len(data_rows) >= len(ctx.records["alert"]) - 2  # allowing duplicate/partial mutations


def test_quality_mutation_exact_targeting(tmp_path):
    """Verify quality mutation targets exact record, locator, and field without side effects."""
    source_dir = tmp_path / "exact_target_source"
    source_dir.mkdir()
    csv_file = source_dir / "alert_src-a.csv"
    id1 = "11111111-1111-1111-1111-111111111111"
    id2 = "22222222-2222-2222-2222-222222222222"
    id3 = "33333333-3333-3333-3333-333333333333"

    csv_file.write_text(
        f"alert_id,source_alert_id,severity\n"
        f"{id1},src-01,CRITICAL\n"
        f"{id2},src-02,HIGH\n"
        f"{id3},src-03,LOW\n",
        encoding="utf-8",
    )

    plan = QualityPlan(
        plan_id="qp-exact-1",
        mutation_type=QualityMutationType.MISSING_FIELD,
        target_family="alert",
        target_record_id=id2,
        organization_id="org-1",
        period_id="P01",
        source_profile_id="SRC-A",
        source_file="alert_src-a.csv",
        source_locator="row:2",
        source_field="source_alert_id",
    )

    receipt_details = _apply_source_file_mutation(plan, source_dir)
    assert receipt_details["source_file"] == "alert_src-a.csv"
    assert receipt_details["source_locator"] == "row:2"

    rows = csv_file.read_text(encoding="utf-8").strip().splitlines()[1:]
    assert rows[0].split(",")[1] == "src-01"  # row 1 untouched
    assert rows[1].split(",")[1] == ""  # row 2 mutated
    assert rows[2].split(",")[1] == "src-03"  # row 3 untouched


def test_quality_mutation_wrong_record_fails(tmp_path):
    """Verify that targeting a record ID that does not match the locator fails loudly."""
    source_dir = tmp_path / "wrong_rec_source"
    source_dir.mkdir()
    csv_file = source_dir / "alert_src-a.csv"
    id1 = "11111111-1111-1111-1111-111111111111"
    id2 = "22222222-2222-2222-2222-222222222222"

    csv_file.write_text(
        f"alert_id,source_alert_id,severity\n{id1},src-01,CRITICAL\n{id2},src-02,HIGH\n",
        encoding="utf-8",
    )

    # Locator row:2 points to id2, but plan specifies id1 -> mismatch
    plan = QualityPlan(
        plan_id="qp-mismatch",
        mutation_type=QualityMutationType.MISSING_FIELD,
        target_family="alert",
        target_record_id=id1,
        organization_id="org-1",
        period_id="P01",
        source_profile_id="SRC-A",
        source_file="alert_src-a.csv",
        source_locator="row:2",
        source_field="source_alert_id",
    )

    with pytest.raises(QualityMutationError, match="does not match expected target record ID"):
        _apply_source_file_mutation(plan, source_dir)


def test_quality_mutation_wrong_locator_fails(tmp_path):
    """Verify that an out-of-bounds locator fails loudly."""
    source_dir = tmp_path / "wrong_loc_source"
    source_dir.mkdir()
    csv_file = source_dir / "alert_src-a.csv"
    csv_file.write_text(
        "alert_id,severity\n11111111-1111-1111-1111-111111111111,HIGH\n", encoding="utf-8"
    )

    plan = QualityPlan(
        plan_id="qp-bad-loc",
        mutation_type=QualityMutationType.MISSING_FIELD,
        target_family="alert",
        target_record_id="11111111-1111-1111-1111-111111111111",
        organization_id="org-1",
        period_id="P01",
        source_profile_id="SRC-A",
        source_file="alert_src-a.csv",
        source_locator="row:999",
        source_field="severity",
    )

    with pytest.raises(QualityMutationError, match="out of bounds"):
        _apply_source_file_mutation(plan, source_dir)


def test_quality_mutation_wrong_source_field_fails(tmp_path):
    """Verify that specifying a non-existent source field fails loudly."""
    source_dir = tmp_path / "wrong_fld_source"
    source_dir.mkdir()
    csv_file = source_dir / "alert_src-a.csv"
    id1 = "11111111-1111-1111-1111-111111111111"
    csv_file.write_text(f"alert_id,severity\n{id1},HIGH\n", encoding="utf-8")

    plan = QualityPlan(
        plan_id="qp-bad-fld",
        mutation_type=QualityMutationType.MISSING_FIELD,
        target_family="alert",
        target_record_id=id1,
        organization_id="org-1",
        period_id="P01",
        source_profile_id="SRC-A",
        source_file="alert_src-a.csv",
        source_locator="row:1",
        source_field="nonexistent_field_xyz",
    )

    with pytest.raises(QualityMutationError, match="not found in record"):
        _apply_source_file_mutation(plan, source_dir)


def test_quality_mutation_missing_target_fails(tmp_path):
    """Verify that a missing target file fails loudly."""
    source_dir = tmp_path / "empty_source"
    source_dir.mkdir()

    plan = QualityPlan(
        plan_id="qp-missing-file",
        mutation_type=QualityMutationType.MISSING_FIELD,
        target_family="nonexistent_family",
        target_record_id="11111111-1111-1111-1111-111111111111",
        organization_id="org-1",
        period_id="P01",
        source_profile_id="SRC-A",
        source_file="nonexistent.csv",
        source_locator="row:1",
        source_field="severity",
    )

    with pytest.raises(QualityMutationError, match="does not exist on disk"):
        _apply_source_file_mutation(plan, source_dir)


def test_gate_08_unrelated_mutation_cannot_excuse_corruption(complete_m5_bundle, tmp_path):
    """Verify Gate 8 fails when an unrelated field is corrupted on an alert."""
    ctx, _, _ = complete_m5_bundle
    bad_src = tmp_path / "bad_src_gate8"
    shutil.copytree(ctx.source_exports_root, bad_src)

    # Corrupt alert_category in alert_src-a.csv without authorization
    alert_csv = bad_src / "alert_src-a.csv"
    lines = alert_csv.read_text(encoding="utf-8").splitlines()
    header = lines[0].split(",")
    if "alert_category" in header:
        cat_idx = header.index("alert_category")
        row = lines[1].split(",")
        row[cat_idx] = "UNAUTHORIZED_CORRUPTED_CATEGORY"
        lines[1] = ",".join(row)
        alert_csv.write_text("\n".join(lines) + "\n", encoding="utf-8")

    bad_ctx = copy.copy(ctx)
    bad_ctx.source_exports_root = bad_src
    gate = Gate08SourceRendering()
    report = gate.validate(bad_ctx)
    assert report.passed is False
    assert any(i.code == "RENDER_UNAUTHORIZED_CORRUPTION" for i in report.issues)


def test_gate_08_wrong_record_mutation_cannot_excuse_corruption(complete_m5_bundle, tmp_path):
    """Verify Gate 8 fails when corruption occurs on a record other than the authorized target."""
    ctx, _, _ = complete_m5_bundle
    bad_src = tmp_path / "bad_src_wrong_rec"
    shutil.copytree(ctx.source_exports_root, bad_src)

    # Corrupt the last row instead of an authorized row
    alert_csv = bad_src / "alert_src-a.csv"
    lines = alert_csv.read_text(encoding="utf-8").splitlines()
    if len(lines) > 5:
        header = lines[0].split(",")
        sev_idx = header.index("severity")
        row = lines[-1].split(",")
        row[sev_idx] = "UNKNOWN_SEV_CORRUPTION"
        lines[-1] = ",".join(row)
        alert_csv.write_text("\n".join(lines) + "\n", encoding="utf-8")

    bad_ctx = copy.copy(ctx)
    bad_ctx.source_exports_root = bad_src
    gate = Gate08SourceRendering()
    report = gate.validate(bad_ctx)
    assert report.passed is False
    assert any(i.code == "RENDER_UNAUTHORIZED_CORRUPTION" for i in report.issues)


def test_gate_09_wrong_source_file_fails(complete_m5_bundle, tmp_path):
    """Verify Gate 9 fails when provenance points to a non-existent source file."""
    ctx, _, _ = complete_m5_bundle
    bad_oracle = tmp_path / "bad_oracle_file"
    shutil.copytree(ctx.oracle_root, bad_oracle)

    prov_file = next(bad_oracle.glob("*_provenance.json"))
    p_data = json.loads(prov_file.read_text(encoding="utf-8"))
    if p_data.get("field_provenance"):
        p_data["field_provenance"][0]["source_file_path"] = "nonexistent_file_99.csv"
        prov_file.write_text(json.dumps(p_data), encoding="utf-8")

    bad_ctx = copy.copy(ctx)
    bad_ctx.oracle_root = bad_oracle
    gate = Gate09CanonicalProvenance()
    report = gate.validate(bad_ctx)
    assert report.passed is False
    assert any(i.code == "PROV_SOURCE_FILE_MISSING" for i in report.issues)


def test_gate_09_wrong_source_field_fails(complete_m5_bundle, tmp_path):
    """Verify Gate 9 fails when provenance points to a non-existent source field."""
    ctx, _, _ = complete_m5_bundle
    bad_oracle = tmp_path / "bad_oracle_fld"
    shutil.copytree(ctx.oracle_root, bad_oracle)

    prov_file = next(bad_oracle.glob("*_provenance.json"))
    p_data = json.loads(prov_file.read_text(encoding="utf-8"))
    if p_data.get("field_provenance"):
        p_data["field_provenance"][0]["source_field_name"] = "ghost_field_not_in_source"
        prov_file.write_text(json.dumps(p_data), encoding="utf-8")

    bad_ctx = copy.copy(ctx)
    bad_ctx.oracle_root = bad_oracle
    gate = Gate09CanonicalProvenance()
    report = gate.validate(bad_ctx)
    assert report.passed is False
    assert any(i.code == "PROV_SOURCE_FIELD_MISSING" for i in report.issues)


def test_gate_09_wrong_locator_fails(complete_m5_bundle, tmp_path):
    """Verify Gate 9 fails when provenance has an out-of-bounds locator."""
    ctx, _, _ = complete_m5_bundle
    bad_oracle = tmp_path / "bad_oracle_loc"
    shutil.copytree(ctx.oracle_root, bad_oracle)

    prov_file = next(bad_oracle.glob("*_provenance.json"))
    p_data = json.loads(prov_file.read_text(encoding="utf-8"))
    if p_data.get("field_provenance"):
        p_data["field_provenance"][0]["source_record_locator"] = "row:99999"
        prov_file.write_text(json.dumps(p_data), encoding="utf-8")

    bad_ctx = copy.copy(ctx)
    bad_ctx.oracle_root = bad_oracle
    gate = Gate09CanonicalProvenance()
    report = gate.validate(bad_ctx)
    assert report.passed is False
    assert any(i.code == "PROV_LOCATOR_NOT_FOUND" for i in report.issues)


def test_gate_09_wrong_relationship_provenance_fails(complete_m5_bundle, tmp_path):
    """Verify Gate 9 fails when relationship foreign key is corrupted without authorization."""
    ctx, _, _ = complete_m5_bundle
    bad_src = tmp_path / "bad_src_rel"
    shutil.copytree(ctx.source_exports_root, bad_src)

    # Corrupt case_alert_link_src-a.csv alert_id on row 2
    link_csv = bad_src / "case_alert_link_src-a.csv"
    if link_csv.exists():
        lines = link_csv.read_text(encoding="utf-8").splitlines()
        if len(lines) > 2:
            header = lines[0].split(",")
            if "alert_id" in header:
                idx = header.index("alert_id")
                row = lines[2].split(",")
                row[idx] = "00000000-0000-0000-0000-000000000000"
                lines[2] = ",".join(row)
                link_csv.write_text("\n".join(lines) + "\n", encoding="utf-8")

    bad_ctx = copy.copy(ctx)
    bad_ctx.source_exports_root = bad_src
    gate = Gate09CanonicalProvenance()
    report = gate.validate(bad_ctx)
    assert report.passed is False
    assert any(i.code == "PROV_RELATIONSHIP_MISMATCH" for i in report.issues)


def test_gate_10_pathological_alert_concentration_fails(clean_context):
    """Verify Gate 10 fails when 100% of alerts have identical timestamp."""
    bad_ctx = copy.copy(clean_context)
    bad_records = copy.deepcopy(clean_context.records)
    fixed_time = datetime(2026, 1, 1, 12, 0, 0)
    orig_alert = bad_records["alert"][0]
    bad_records["alert"] = [
        orig_alert.model_copy(update={"created_at_utc": fixed_time, "alert_id": UUID(int=i + 1)})
        for i in range(10)
    ]
    bad_ctx.records = bad_records
    gate = Gate10DistributionSanity()
    report = gate.validate(bad_ctx)
    assert report.passed is False
    assert any(i.code == "DIST_PATHOLOGICAL_TIMESTAMP_CONCENTRATION" for i in report.issues)


def test_gate_10_pathological_uniformity_fails(clean_context):
    """Verify Gate 10 detects degenerate severity uniformity."""
    bad_ctx = copy.copy(clean_context)
    bad_records = copy.deepcopy(clean_context.records)
    orig_alert = bad_records["alert"][0]
    bad_records["alert"] = [
        orig_alert.model_copy(
            update={
                "severity": "INFORMATIONAL",
                "alert_id": UUID(int=i + 1),
                "created_at_utc": datetime(2026, 1, 1, 12, i, 0),
            }
        )
        for i in range(15)
    ]
    bad_ctx.records = bad_records
    gate = Gate10DistributionSanity()
    report = gate.validate(bad_ctx)
    assert any(i.code == "DIST_PATHOLOGICAL_UNIFORMITY" for i in report.issues)


def test_gate_10_negative_case_duration_fails(clean_context):
    """Verify Gate 10 fails when closure timestamp precedes case creation timestamp."""
    bad_ctx = copy.copy(clean_context)
    bad_records = copy.deepcopy(clean_context.records)
    if bad_records.get("case") and bad_records.get("closure"):
        c = bad_records["case"][0]
        cl = bad_records["closure"][0]
        # Make closure earlier than case creation
        earlier_time = c.created_at_utc - timedelta(days=10)
        bad_records["closure"][0] = cl.model_copy(
            update={"case_id": c.case_id, "created_at_utc": earlier_time}
        )
    bad_ctx.records = bad_records
    gate = Gate10DistributionSanity()
    report = gate.validate(bad_ctx)
    assert report.passed is False
    assert any(i.code == "DIST_NEGATIVE_CASE_DURATION" for i in report.issues)


def test_gate_14_hash_mismatch_fails(complete_m5_bundle, tmp_path):
    """Verify Gate 14 fails when a manifested file is altered without updating manifest."""
    ctx, _, _ = complete_m5_bundle
    bad_op = tmp_path / "bad_op_hash"
    shutil.copytree(ctx.operational_root, bad_op)

    # Tamper with an operational payload file
    target_file = bad_op / "alerts.json"
    content = target_file.read_bytes()
    target_file.write_bytes(content + b" ")

    bad_ctx = copy.copy(ctx)
    bad_ctx.operational_root = bad_op
    gate = Gate14PackageHash()
    report = gate.validate(bad_ctx)
    assert report.passed is False
    assert any(i.code == "PKG_HASH_MISMATCH" for i in report.issues)


def test_gate_14_size_mismatch_fails(complete_m5_bundle, tmp_path):
    """Verify Gate 14 fails when a manifested file has wrong size."""
    ctx, _, _ = complete_m5_bundle
    bad_op = tmp_path / "bad_op_size"
    shutil.copytree(ctx.operational_root, bad_op)

    # Truncate an operational payload file
    target_file = bad_op / "cases.json"
    target_file.write_bytes(b"[]")

    bad_ctx = copy.copy(ctx)
    bad_ctx.operational_root = bad_op
    gate = Gate14PackageHash()
    report = gate.validate(bad_ctx)
    assert report.passed is False
    assert any(i.code == "PKG_SIZE_MISMATCH" for i in report.issues)


def test_quality_mutation_missing_source_profile_fails(tmp_path):
    """Verify that a quality mutation missing explicit source_profile_id fails loudly."""
    source_dir = tmp_path / "missing_prof_source"
    source_dir.mkdir()
    (source_dir / "alert_src-a.csv").write_text("alert_id,source_alert_id\nid1,s1\n")
    plan = QualityPlan(
        plan_id="qp-no-prof",
        mutation_type=QualityMutationType.MISSING_FIELD,
        target_family="alert",
        target_record_id="id1",
        organization_id="org-1",
        period_id="P01",
        source_file="alert_src-a.csv",
        source_locator="row:1",
        source_field="source_alert_id",
        source_profile_id=None,
    )
    with pytest.raises(QualityMutationError, match="missing required explicit source_profile_id"):
        _apply_source_file_mutation(plan, source_dir)


def test_quality_mutation_missing_source_file_fails(tmp_path):
    """Verify that a quality mutation missing explicit source_file fails loudly."""
    source_dir = tmp_path / "missing_file_source"
    source_dir.mkdir()
    plan = QualityPlan(
        plan_id="qp-no-file",
        mutation_type=QualityMutationType.MISSING_FIELD,
        target_family="alert",
        target_record_id="id1",
        organization_id="org-1",
        period_id="P01",
        source_profile_id="SRC-A",
        source_file=None,
        source_locator="row:1",
        source_field="source_alert_id",
    )
    with pytest.raises(QualityMutationError, match="missing required explicit source_file"):
        _apply_source_file_mutation(plan, source_dir)


def test_quality_mutation_missing_source_locator_fails(tmp_path):
    """Verify that a quality mutation missing explicit source_locator fails loudly."""
    source_dir = tmp_path / "missing_loc_source"
    source_dir.mkdir()
    (source_dir / "alert_src-a.csv").write_text("alert_id,source_alert_id\nid1,s1\n")
    plan = QualityPlan(
        plan_id="qp-no-loc",
        mutation_type=QualityMutationType.MISSING_FIELD,
        target_family="alert",
        target_record_id="id1",
        organization_id="org-1",
        period_id="P01",
        source_profile_id="SRC-A",
        source_file="alert_src-a.csv",
        source_locator=None,
        source_field="source_alert_id",
    )
    with pytest.raises(QualityMutationError, match="missing required explicit source_locator"):
        _apply_source_file_mutation(plan, source_dir)


def test_quality_mutation_missing_field_to_modify_fails(tmp_path):
    """Verify that a quality mutation missing explicit field to modify fails loudly."""
    source_dir = tmp_path / "missing_fld_source"
    source_dir.mkdir()
    (source_dir / "alert_src-a.csv").write_text("alert_id,source_alert_id\nid1,s1\n")
    plan = QualityPlan(
        plan_id="qp-no-fld",
        mutation_type=QualityMutationType.MISSING_FIELD,
        target_family="alert",
        target_record_id="id1",
        organization_id="org-1",
        period_id="P01",
        source_profile_id="SRC-A",
        source_file="alert_src-a.csv",
        source_locator="row:1",
        source_field=None,
        target_field=None,
    )
    with pytest.raises(QualityMutationError, match="missing required explicit field to modify"):
        _apply_source_file_mutation(plan, source_dir)


def test_quality_mutation_broken_rel_missing_relationship_fails(tmp_path):
    """Verify that BROKEN_RELATIONSHIP missing explicit target_relationship fails loudly."""
    source_dir = tmp_path / "missing_rel_source"
    source_dir.mkdir()
    (source_dir / "case_alert_link_src-a.csv").write_text(
        "case_alert_link_id,alert_id\nlink1,alert1\n"
    )
    plan = QualityPlan(
        plan_id="qp-no-rel",
        mutation_type=QualityMutationType.BROKEN_RELATIONSHIP,
        target_family="case_alert_link",
        target_record_id="link1",
        organization_id="org-1",
        period_id="P01",
        source_profile_id="SRC-A",
        source_file="case_alert_link_src-a.csv",
        source_locator="row:1",
        target_relationship=None,
        source_field=None,
    )
    with pytest.raises(QualityMutationError, match="missing explicit target_relationship"):
        _apply_source_file_mutation(plan, source_dir)


def test_partial_submission_explicit_targeting_contract(tmp_path):
    """Verify PARTIAL_SUBMISSION requires explicit withheld ID, locator, and emits receipt."""
    source_dir = tmp_path / "part_sub_source"
    source_dir.mkdir()
    csv_file = source_dir / "alert_src-a.csv"
    id1 = "11111111-1111-1111-1111-111111111111"
    id2 = "22222222-2222-2222-2222-222222222222"
    id3 = "33333333-3333-3333-3333-333333333333"
    csv_file.write_text(
        f"alert_id,source_alert_id,severity\n{id1},s1,HIGH\n{id2},s2,MEDIUM\n{id3},s3,LOW\n",
        encoding="utf-8",
    )

    # 1. Missing withheld_record_id fails
    bad_plan1 = QualityPlan(
        plan_id="qp-part-missing-id",
        mutation_type=QualityMutationType.PARTIAL_SUBMISSION,
        target_family="submission",
        target_record_id="sub-1",
        organization_id="org-1",
        period_id="P01",
        source_profile_id="SRC-A",
        source_file="alert_src-a.csv",
        source_locator="row:2",
        parameters={},
    )
    with pytest.raises(QualityMutationError, match="requires explicit 'withheld_record_id'"):
        _apply_source_file_mutation(bad_plan1, source_dir)

    # 2. Wrong record ID at locator fails
    bad_plan2 = QualityPlan(
        plan_id="qp-part-wrong-id",
        mutation_type=QualityMutationType.PARTIAL_SUBMISSION,
        target_family="submission",
        target_record_id="sub-1",
        organization_id="org-1",
        period_id="P01",
        source_profile_id="SRC-A",
        source_file="alert_src-a.csv",
        source_locator="row:2",
        parameters={"withheld_record_id": id1, "withheld_family": "alert"},
    )
    with pytest.raises(QualityMutationError, match="does not match expected withheld record ID"):
        _apply_source_file_mutation(bad_plan2, source_dir)

    # 3. Wrong/out of bounds locator fails
    bad_plan3 = QualityPlan(
        plan_id="qp-part-bad-loc",
        mutation_type=QualityMutationType.PARTIAL_SUBMISSION,
        target_family="submission",
        target_record_id="sub-1",
        organization_id="org-1",
        period_id="P01",
        source_profile_id="SRC-A",
        source_file="alert_src-a.csv",
        source_locator="row:99",
        parameters={"withheld_record_id": id2, "withheld_family": "alert"},
    )
    with pytest.raises(QualityMutationError, match="out of bounds"):
        _apply_source_file_mutation(bad_plan3, source_dir)

    # 4. Valid explicit targeting succeeds and removes ONLY row 2 (id2)
    good_plan = QualityPlan(
        plan_id="qp-part-good",
        mutation_type=QualityMutationType.PARTIAL_SUBMISSION,
        target_family="submission",
        target_record_id="sub-1",
        organization_id="org-1",
        period_id="P01",
        source_profile_id="SRC-A",
        source_file="alert_src-a.csv",
        source_locator="row:2",
        parameters={"withheld_record_id": id2, "withheld_family": "alert"},
    )
    receipt = _apply_source_file_mutation(good_plan, source_dir)
    assert receipt["withheld_record_id"] == id2
    assert receipt["withheld_family"] == "alert"
    assert receipt["source_file"] == "alert_src-a.csv"
    assert receipt["source_locator"] == "row:2"
    assert receipt["mutation_id"] == "qp-part-good"
    assert receipt["withheld_record_content"]["alert_id"] == id2

    remaining_rows = csv_file.read_text(encoding="utf-8").strip().splitlines()[1:]
    assert len(remaining_rows) == 2
    assert id1 in remaining_rows[0]
    assert id3 in remaining_rows[1]
    assert id2 not in "\n".join(remaining_rows)


def test_gate_08_loud_failures_on_corrupt_files(complete_m5_bundle, tmp_path):
    """Verify Gate 8 emits loud blocking failures for corrupt or missing index/oracle/profile."""
    ctx, _, _ = complete_m5_bundle

    # Missing oracle index file
    bad_oracle = tmp_path / "bad_oracle_missing_index"
    shutil.copytree(ctx.oracle_root, bad_oracle)
    for p in bad_oracle.glob("*_index.json"):
        p.unlink()

    bad_ctx = copy.copy(ctx)
    bad_ctx.oracle_root = bad_oracle
    gate = Gate08SourceRendering()
    report = gate.validate(bad_ctx)
    assert report.passed is False
    assert any(i.code == "RENDER_INDEX_MISSING" for i in report.issues)

    # Corrupt index JSON
    bad_oracle2 = tmp_path / "bad_oracle_corrupt_index"
    shutil.copytree(ctx.oracle_root, bad_oracle2)
    for p in bad_oracle2.glob("*_index.json"):
        p.write_text("{corrupt: json}", encoding="utf-8")
    bad_ctx.oracle_root = bad_oracle2
    report = gate.validate(bad_ctx)
    assert report.passed is False
    assert any(i.code == "RENDER_INDEX_PARSE_FAILURE" for i in report.issues)

    # Corrupt oracle JSON
    bad_oracle3 = tmp_path / "bad_oracle_corrupt_oracle"
    shutil.copytree(ctx.oracle_root, bad_oracle3)
    for p in bad_oracle3.glob("*_oracle.json"):
        p.write_text("{invalid: json", encoding="utf-8")
    bad_ctx.oracle_root = bad_oracle3
    report = gate.validate(bad_ctx)
    assert report.passed is False
    assert any(i.code == "RENDER_ORACLE_PARSE_FAILURE" for i in report.issues)

    # Rendered file lacking profile suffix
    bad_src = tmp_path / "bad_src_missing_suffix"
    shutil.copytree(ctx.source_exports_root, bad_src)
    (bad_src / "orphan.csv").write_text("alert_id\n1\n", encoding="utf-8")
    bad_ctx_src = copy.copy(ctx)
    bad_ctx_src.source_exports_root = bad_src
    report = gate.validate(bad_ctx_src)
    assert report.passed is False
    assert any(i.code == "RENDER_UNKNOWN_PROFILE" for i in report.issues)


def test_gate_08_reconciliation_negative_dimensions(complete_m5_bundle, tmp_path):
    """Verify Gate 8 fails when mutation authorization mismatches along any dimension."""
    ctx, _, _ = complete_m5_bundle
    bad_src = tmp_path / "bad_src_dim"
    shutil.copytree(ctx.source_exports_root, bad_src)

    # Corrupt an alert severity to LOW in row 1
    alert_csv = bad_src / "alert_src-a.csv"
    lines = alert_csv.read_text(encoding="utf-8").splitlines()
    header = lines[0].split(",")
    row1 = lines[1].split(",")
    alert_id = row1[header.index("alert_id")]
    row1[header.index("severity")] = "LOW"
    lines[1] = ",".join(row1)
    alert_csv.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Mismatch dimension 1: wrong profile (SRC-B instead of SRC-A)
    ledger_wrong_prof = AuthorizationLedger()
    ledger_wrong_prof.authorize(
        AuthorizationEntry(
            authorization_id="AUTH-WRONG-PROF",
            scenario_id="QUALITY_ENGINE",
            plan_id="AUTH-WRONG-PROF",
            realization=RealizationState.CONCERNING,
            target_record_ids=(alert_id,),
            target_family="alert",
            mutation_type=MutationType.CONFLICTING_DUPLICATE,
            source_profile="SRC-B",
            source_file="alert_src-a.csv",
            source_locator="row:1",
            source_field="severity",
            expected_semantic_effect="Conflicting duplicate",
            seed_label="test/wrong_prof",
        )
    )
    bad_ctx = copy.copy(ctx)
    bad_ctx.source_exports_root = bad_src
    bad_ctx.ledger = ledger_wrong_prof
    gate = Gate08SourceRendering()
    report = gate.validate(bad_ctx)
    assert report.passed is False
    assert any(i.code == "RENDER_UNAUTHORIZED_CORRUPTION" for i in report.issues)

    # Mismatch dimension 2: wrong file
    ledger_wrong_file = AuthorizationLedger()
    ledger_wrong_file.authorize(
        AuthorizationEntry(
            authorization_id="AUTH-WRONG-FILE",
            scenario_id="QUALITY_ENGINE",
            plan_id="AUTH-WRONG-FILE",
            realization=RealizationState.CONCERNING,
            target_record_ids=(alert_id,),
            target_family="alert",
            mutation_type=MutationType.CONFLICTING_DUPLICATE,
            source_profile="SRC-A",
            source_file="other_file.csv",
            source_locator="row:1",
            source_field="severity",
            expected_semantic_effect="Conflicting duplicate",
            seed_label="test/wrong_file",
        )
    )
    bad_ctx.ledger = ledger_wrong_file
    report = gate.validate(bad_ctx)
    assert report.passed is False
    assert any(i.code == "RENDER_UNAUTHORIZED_CORRUPTION" for i in report.issues)

    # Mismatch dimension 3: wrong locator
    ledger_wrong_loc = AuthorizationLedger()
    ledger_wrong_loc.authorize(
        AuthorizationEntry(
            authorization_id="AUTH-WRONG-LOC",
            scenario_id="QUALITY_ENGINE",
            plan_id="AUTH-WRONG-LOC",
            realization=RealizationState.CONCERNING,
            target_record_ids=(alert_id,),
            target_family="alert",
            mutation_type=MutationType.CONFLICTING_DUPLICATE,
            source_profile="SRC-A",
            source_file="alert_src-a.csv",
            source_locator="row:99",
            source_field="severity",
            expected_semantic_effect="Conflicting duplicate",
            seed_label="test/wrong_loc",
        )
    )
    bad_ctx.ledger = ledger_wrong_loc
    report = gate.validate(bad_ctx)
    assert report.passed is False
    assert any(i.code == "RENDER_UNAUTHORIZED_CORRUPTION" for i in report.issues)


def test_gate_09_loud_failures_on_corrupt_files(complete_m5_bundle, tmp_path):
    """Verify Gate 9 emits loud blocking failures for corrupt source/index/provenance."""
    ctx, _, _ = complete_m5_bundle

    # Corrupt source file triggers PROV_SOURCE_FILE_CORRUPT
    bad_src = tmp_path / "bad_src_prov_corrupt"
    shutil.copytree(ctx.source_exports_root, bad_src)
    for p in bad_src.glob("*.csv"):
        p.write_bytes(b"\x00\xff\xfe\x00corrupt")
        break

    bad_ctx = copy.copy(ctx)
    bad_ctx.source_exports_root = bad_src
    gate = Gate09CanonicalProvenance()
    report = gate.validate(bad_ctx)
    assert report.passed is False
    assert any(i.code == "PROV_SOURCE_FILE_CORRUPT" for i in report.issues)

    # Corrupt index JSON triggers PROV_INDEX_PARSE_FAILURE
    bad_oracle = tmp_path / "bad_oracle_prov_index"
    shutil.copytree(ctx.oracle_root, bad_oracle)
    for p in bad_oracle.glob("*_index.json"):
        p.write_text("{unparseable", encoding="utf-8")
        break
    bad_ctx2 = copy.copy(ctx)
    bad_ctx2.oracle_root = bad_oracle
    report2 = gate.validate(bad_ctx2)
    assert report2.passed is False
    assert any(i.code == "PROV_INDEX_PARSE_FAILURE" for i in report2.issues)

    # Corrupt provenance JSON triggers PROV_PARSE_FAILURE
    bad_oracle2 = tmp_path / "bad_oracle_prov_json"
    shutil.copytree(ctx.oracle_root, bad_oracle2)
    for p in bad_oracle2.glob("*_provenance.json"):
        p.write_text("{bad: json", encoding="utf-8")
        break
    bad_ctx3 = copy.copy(ctx)
    bad_ctx3.oracle_root = bad_oracle2
    report3 = gate.validate(bad_ctx3)
    assert report3.passed is False
    assert any(i.code == "PROV_PARSE_FAILURE" for i in report3.issues)


def test_gate_10_distribution_pathologies_comprehensive(clean_context):
    """Verify Gate 10 detects zero-variance, uniformity, and bounded distribution pathologies."""
    gate = Gate10DistributionSanity()

    # 1. Suspiciously uniform alert spacing
    bad_ctx1 = copy.copy(clean_context)
    alerts1 = copy.deepcopy(clean_context.records["alert"])
    base_t = datetime(2026, 1, 1, 0, 0, 0)
    for idx, a in enumerate(alerts1):
        alerts1[idx] = a.model_copy(update={"created_at_utc": base_t + timedelta(seconds=idx * 60)})
    bad_ctx1.records = copy.copy(clean_context.records)
    bad_ctx1.records["alert"] = alerts1
    report1 = gate.validate(bad_ctx1)
    assert any(i.code == "DIST_SUSPICIOUSLY_UNIFORM_ALERT_SPACING" for i in report1.issues)

    # 2. Alert category homogeneity
    bad_ctx2 = copy.copy(clean_context)
    alerts2 = copy.deepcopy(clean_context.records["alert"])
    if len(alerts2) >= 15:
        for idx, a in enumerate(alerts2):
            alerts2[idx] = a.model_copy(update={"alert_category": "PATHOLOGICAL_SINGLE_CATEGORY"})
        bad_ctx2.records = copy.copy(clean_context.records)
        bad_ctx2.records["alert"] = alerts2
        report2 = gate.validate(bad_ctx2)
        assert any(i.code == "DIST_ALERT_CATEGORY_HOMOGENEITY" for i in report2.issues)

    # 3. Excessive case duration (> 365 days)
    bad_ctx3 = copy.copy(clean_context)
    cases3 = copy.deepcopy(clean_context.records["case"])
    closures3 = copy.deepcopy(clean_context.records["closure"])
    if cases3 and closures3:
        c = cases3[0]
        closures3[0] = closures3[0].model_copy(
            update={"case_id": c.case_id, "created_at_utc": c.created_at_utc + timedelta(days=400)}
        )
        bad_ctx3.records = copy.copy(clean_context.records)
        bad_ctx3.records["case"] = cases3
        bad_ctx3.records["closure"] = closures3
        report3 = gate.validate(bad_ctx3)
        assert any(i.code == "DIST_EXCESSIVE_CASE_DURATION" for i in report3.issues)

    # 4. Zero variance case duration
    bad_ctx4 = copy.copy(clean_context)
    cases4 = copy.deepcopy(clean_context.records["case"])
    closures4 = copy.deepcopy(clean_context.records["closure"])
    if len(cases4) >= 5 and len(closures4) >= 5:
        for idx in range(5):
            c = cases4[idx]
            closures4[idx] = closures4[idx].model_copy(
                update={
                    "case_id": c.case_id,
                    "created_at_utc": c.created_at_utc + timedelta(seconds=120),
                }
            )
        bad_ctx4.records = copy.copy(clean_context.records)
        bad_ctx4.records["case"] = cases4
        bad_ctx4.records["closure"] = closures4[:5]
        report4 = gate.validate(bad_ctx4)
        assert any(i.code == "DIST_ZERO_VARIANCE_CASE_DURATION" for i in report4.issues)

    # 5. Pathological note duplication
    bad_ctx5 = copy.copy(clean_context)
    invs5 = copy.deepcopy(clean_context.records["investigation"])
    if len(invs5) >= 5:
        for idx in range(len(invs5)):
            invs5[idx] = invs5[idx].model_copy(
                update={"summary": "IDENTICAL COPY-PASTE INVESTIGATION NOTE"}
            )
        bad_ctx5.records = copy.copy(clean_context.records)
        bad_ctx5.records["investigation"] = invs5
        report5 = gate.validate(bad_ctx5)
        assert any(i.code == "DIST_PATHOLOGICAL_NOTE_DUPLICATION" for i in report5.issues)

    # 6. Identical entity alert distributions
    bad_ctx6 = copy.copy(clean_context)
    orgs6 = copy.deepcopy(clean_context.records["organization"])
    alerts6 = copy.deepcopy(clean_context.records["alert"])
    if len(orgs6) >= 2 and len(alerts6) >= 10:
        half = len(alerts6) // 2
        for idx in range(half):
            alerts6[idx] = alerts6[idx].model_copy(
                update={
                    "organization_id": orgs6[0].organization_id,
                    "created_at_utc": base_t + timedelta(seconds=idx * 7),
                }
            )
            alerts6[half + idx] = alerts6[half + idx].model_copy(
                update={
                    "organization_id": orgs6[1].organization_id,
                    "created_at_utc": base_t + timedelta(seconds=idx * 7),
                }
            )
        bad_ctx6.records = copy.copy(clean_context.records)
        bad_ctx6.records["organization"] = orgs6[:2]
        bad_ctx6.records["alert"] = alerts6[: 2 * half]
        report6 = gate.validate(bad_ctx6)
        assert any(i.code == "DIST_IDENTICAL_ENTITY_ALERT_DISTRIBUTIONS" for i in report6.issues)
