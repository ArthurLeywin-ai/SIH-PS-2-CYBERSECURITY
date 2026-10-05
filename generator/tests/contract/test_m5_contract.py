"""
Contract tests for Milestone 5 fixture package and validation outputs.

Validates that Milestone 5 output complies with DATA_SCHEMA.md,
DATASET_GENERATION_SPEC.md, and GENERATOR_IMPLEMENTATION_PLAN.md:
- 18 evidence families in operational package
- Zero private truth, scenario keys, or seeds in operational artifacts
- Private ground truth, authorization ledger, and quality receipts strictly separated
- All 14 validation gate reports present and passing
"""

import json
from pathlib import Path

import pytest

from satsa_generator.fixture.builder import build_fixture, parse_master_seed_hex
from satsa_generator.validation.leakage import ComprehensiveLeakageScanner

_EXPECTED_18_FAMILIES = (
    "organization",
    "submission",
    "submission_manifest",
    "submission_evidence_family",
    "control_process_reference",
    "control_process_subject_link",
    "asset",
    "monitoring_coverage",
    "alert",
    "case",
    "case_alert_link",
    "investigation",
    "escalation",
    "action",
    "resolution",
    "closure",
    "exception",
    "process_change",
)


@pytest.fixture(scope="module")
def m5_fixture(tmp_path_factory):
    out_dir = tmp_path_factory.mktemp("m5_fixture_contract")
    config_path = Path("generator/config/public/base/fixture_config.json")
    if not config_path.exists():
        config_path = Path("config/public/base/fixture_config.json")
    seed_bytes = parse_master_seed_hex(
        "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    )
    result = build_fixture(config_path, seed_bytes, output_root=out_dir, milestone="m5")
    return result, out_dir


def test_m5_operational_files_and_manifest(m5_fixture):
    result, out_dir = m5_fixture
    op_root = result.operational_root
    assert op_root.exists()

    manifest_file = op_root / "fixture_manifest.json"
    assert manifest_file.exists()
    manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert manifest_data["fixture_contract"] == "SATSA-M5-FIXTURE-V1"

    # All 18 families represented in record_counts
    for fam in _EXPECTED_18_FAMILIES:
        assert fam in result.record_counts
        assert result.record_counts[fam] > 0


def test_m5_private_artifacts_separation(m5_fixture):
    result, out_dir = m5_fixture
    private_root = out_dir / "private_ground_truth"
    assert private_root.exists()

    gt_file = private_root / "ground_truth.json"
    assert gt_file.exists()
    gt_data = json.loads(gt_file.read_text(encoding="utf-8"))
    assert gt_data["record_count"] > 0

    ledger_file = private_root / "authorization_ledger.json"
    assert ledger_file.exists()

    quality_file = private_root / "quality_receipts.json"
    assert quality_file.exists()
    quality_data = json.loads(quality_file.read_text(encoding="utf-8"))
    assert len(quality_data) == 13  # all 13 quality mutation operations


def test_m5_14_validation_gates_reports(m5_fixture):
    result, out_dir = m5_fixture
    reports_dir = out_dir / "private_ground_truth" / "validation_reports"
    assert reports_dir.exists()

    full_report_file = reports_dir / "full_validation_report.json"
    assert full_report_file.exists()
    full_report = json.loads(full_report_file.read_text(encoding="utf-8"))
    assert full_report["all_passed"] is True
    assert full_report["overall_status"] == "PASSED"
    assert full_report["blocking_issue_count"] == 0

    # Ensure all 14 gates have individual JSON reports
    for idx in range(1, 15):
        assert str(idx) in full_report["gate_reports"]


def test_m5_zero_leakage_in_operational_evidence(m5_fixture):
    result, out_dir = m5_fixture
    ComprehensiveLeakageScanner.assert_no_leakage(result.operational_root)
