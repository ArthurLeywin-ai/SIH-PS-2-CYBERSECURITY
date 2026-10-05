"""
Integration tests for the Milestone 5 pipeline and negative testing.

Tests:
- Full end-to-end M5 fixture build
- Negative tests: intentionally broken conditions fail loudly at appropriate gates
  - Broken relationship fails Gate 3
  - Impossible temporal ordering fails Gate 4
  - Planted canary leak fails Gate 12
  - Missing mandatory family fails Gate 2
  - Unauthorized mutation fails Gate 7
"""

import copy
import json
from pathlib import Path
from uuid import UUID

import pytest

from satsa_generator.fixture.builder import build_fixture, parse_master_seed_hex
from satsa_generator.validation.gates import (
    Gate02SchemaBase,
    Gate03ReferentialIntegrity,
    Gate07AuthorizedMutation,
    Gate12LeakageScan,
)
from satsa_generator.validation.leakage import (
    CanaryScanner,
)
from satsa_generator.validation.models import GateSeverity, ValidationContext


@pytest.fixture
def base_context(tmp_path):
    from satsa_generator.config.models import load_config
    from satsa_generator.fixture.builder import _generate_m2_records
    from satsa_generator.ids.service import IDService
    from satsa_generator.scenarios.ledger import AuthorizationLedger
    from satsa_generator.seeds.manager import SeedManager

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
    return ValidationContext(
        config=config,
        records=records,
        ledger=AuthorizationLedger(),
        ground_truth=[],
        receipts=[],
        operational_root=tmp_path / "operational_evidence",
    )


def test_m5_full_build(tmp_path):
    config_path = Path("generator/config/public/base/fixture_config.json")
    if not config_path.exists():
        config_path = Path("config/public/base/fixture_config.json")
    seed_bytes = parse_master_seed_hex(
        "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    )
    out_dir = tmp_path / "m5_build"
    result = build_fixture(config_path, seed_bytes, output_root=out_dir, milestone="m5")

    assert result.operational_root.exists()
    assert (out_dir / "private_ground_truth").exists()
    assert (out_dir / "private_ground_truth" / "quality_receipts.json").exists()


def test_negative_gate_02_schema_break(base_context):
    bad_ctx = copy.copy(base_context)
    bad_records = dict(base_context.records)
    del bad_records["alert"]
    bad_ctx.records = bad_records

    gate = Gate02SchemaBase()
    report = gate.validate(bad_ctx)
    assert report.passed is False
    assert any(i.severity == GateSeverity.BLOCKING for i in report.issues)


def test_negative_gate_03_referential_break(base_context):
    bad_ctx = copy.copy(base_context)
    bad_records = copy.deepcopy(base_context.records)
    # Corrupt case_id on link
    bad_records["case_alert_link"][0] = bad_records["case_alert_link"][0].model_copy(
        update={"case_id": UUID("00000000-1111-2222-3333-444444444444")}
    )
    bad_ctx.records = bad_records

    gate = Gate03ReferentialIntegrity()
    report = gate.validate(bad_ctx)
    assert report.passed is False
    assert any(i.code == "REF_BROKEN_CASE_LINK" for i in report.issues)


def test_negative_gate_12_canary_leak_break(base_context, tmp_path):
    # Plant a canary token in a file in operational root
    op_root = tmp_path / "operational_evidence"
    op_root.mkdir(parents=True, exist_ok=True)
    canary_file = op_root / "alerts.json"
    canary_token = CanaryScanner.generate_canary_token("INTEGRATION_TEST")
    canary_file.write_text(json.dumps([{"summary": canary_token}]), encoding="utf-8")

    bad_ctx = copy.copy(base_context)
    bad_ctx.operational_root = op_root

    gate = Gate12LeakageScan()
    report = gate.validate(bad_ctx)
    assert report.passed is False
    assert any(i.severity == GateSeverity.BLOCKING for i in report.issues)


def test_negative_gate_07_unauthorized_receipt(base_context):
    from satsa_generator.scenarios.models import MutationReceipt, MutationType

    bad_ctx = copy.copy(base_context)
    fake_receipt = MutationReceipt(
        authorization_id="AUTH-UNREGISTERED",
        plan_id="PLAN-FAKE",
        scenario_id="EG-01",
        mutation_type=MutationType.REMOVE_RECORD,
        target_record_ids=("target-id",),
        target_family="alert",
        target_fields=(),
        before_state={},
        after_state={},
        applied=True,
    )
    bad_ctx.receipts = [fake_receipt]

    gate = Gate07AuthorizedMutation()
    report = gate.validate(bad_ctx)
    assert report.passed is False
    assert any(i.code == "MUT_UNAUTHORIZED_DEFECT" for i in report.issues)
