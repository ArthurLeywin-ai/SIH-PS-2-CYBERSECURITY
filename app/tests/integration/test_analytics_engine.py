"""Integration tests for the Supervisory Analytics Engine and REST API endpoints."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from app.backend.analytics.engine import SupervisoryAnalyticsEngine
from app.backend.config import get_config
from fastapi.testclient import TestClient
from satsa_generator.fixture.builder import build_fixture, parse_master_seed_hex


@pytest.fixture(scope="module")
def m5_fixture_package(tmp_path_factory) -> Path:
    """Build a deterministic M5 generator fixture."""
    cfg = Path("generator/config/public/base/fixture_config.json")
    if not cfg.exists():
        cfg = Path("config/public/base/fixture_config.json")

    seed = parse_master_seed_hex("0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef")
    out_dir = tmp_path_factory.mktemp("m5_fixture_analytics") / "package"
    result = build_fixture(cfg, seed, output_root=out_dir, milestone="m5")
    return result.output_root


def test_analytics_engine_end_to_end_and_determinism(
    client: TestClient,
    m5_fixture_package: Path,
    test_db_session,
):
    """End-to-end integration test:

    Ingest M5 package -> Run Analytics Engine -> Assert Determinism & Traceability -> Test REST APIs.
    """
    # Stage package into active evidence directory boundary
    staged_pkg = get_config().evidence_dir / "analytics_fixture"
    if not staged_pkg.exists():
        shutil.copytree(m5_fixture_package, staged_pkg)

    # 1. Ingest package
    ingest_resp = client.post(
        "/api/v1/packages/ingest",
        json={"package_path": str(staged_pkg), "fail_on_error": False},
    )
    assert ingest_resp.status_code == 201, f"Ingestion failed: {ingest_resp.text}"

    # 2. Retrieve organizations and submissions
    orgs_resp = client.get("/api/v1/organizations")
    assert orgs_resp.status_code == 200
    orgs = orgs_resp.json()
    assert len(orgs) >= 1
    target_org = orgs[0]
    org_id = target_org["organization_id"]

    subs_resp = client.get(f"/api/v1/organizations/{org_id}/submissions")
    assert subs_resp.status_code == 200
    subs = subs_resp.json()
    assert len(subs) >= 1
    sub_id = subs[0]["submission_id"]

    # 3. Direct Engine Execution & Determinism Verification
    engine = SupervisoryAnalyticsEngine(test_db_session)
    run1 = engine.analyze_organization(org_id, persist=False)
    run2 = engine.analyze_organization(org_id, persist=False)

    # Assert 100% determinism across runs
    assert run1.signals_count == run2.signals_count
    assert run1.organization_id == run2.organization_id
    assert len(run1.signals) == len(run2.signals)

    for s1, s2 in zip(run1.signals, run2.signals, strict=True):
        assert s1.signal_type == s2.signal_type
        assert s1.severity == s2.severity
        assert s1.title == s2.title
        assert s1.observed_value == s2.observed_value
        assert s1.expected_value == s2.expected_value
        assert s1.affected_record_ids == s2.affected_record_ids
        assert s1.investigation_questions == s2.investigation_questions

    if run1.attention_summary and run2.attention_summary:
        assert run1.attention_summary.attention_score == run2.attention_summary.attention_score
        assert run1.attention_summary.attention_band == run2.attention_summary.attention_band
        assert run1.attention_summary.total_signals == run2.attention_summary.total_signals

    # 4. Test REST API: POST /api/v1/analytics/run (persist=True)
    api_run_resp = client.post(
        "/api/v1/analytics/run",
        json={"organization_id": org_id, "persist": True},
    )
    assert api_run_resp.status_code == 200, f"API run failed: {api_run_resp.text}"
    api_run_data = api_run_resp.json()
    assert api_run_data["organization_id"] == org_id
    assert "signals" in api_run_data
    assert "attention_summary" in api_run_data
    assert api_run_data["execution_duration_ms"] > 0

    # 5. Test REST API: GET /api/v1/analytics/signals (List & Filters)
    signals_resp = client.get(f"/api/v1/analytics/signals?organization_id={org_id}")
    assert signals_resp.status_code == 200
    signals_list = signals_resp.json()
    assert len(signals_list) == api_run_data["signals_count"]

    if signals_list:
        first_sig = signals_list[0]
        sig_id = first_sig["signal_id"]

        # Filter by severity
        sev = first_sig["severity"]
        sev_resp = client.get(f"/api/v1/analytics/signals?organization_id={org_id}&severity={sev}")
        assert sev_resp.status_code == 200
        for s in sev_resp.json():
            assert s["severity"] == sev

        # Filter by signal_type
        stype = first_sig["signal_type"]
        stype_resp = client.get(f"/api/v1/analytics/signals?organization_id={org_id}&signal_type={stype}")
        assert stype_resp.status_code == 200
        for s in stype_resp.json():
            assert s["signal_type"] == stype

        # 6. Test REST API: GET /api/v1/analytics/signals/{signal_id}
        single_sig_resp = client.get(f"/api/v1/analytics/signals/{sig_id}")
        assert single_sig_resp.status_code == 200
        single_sig = single_sig_resp.json()
        assert single_sig["signal_id"] == sig_id
        assert len(single_sig["short_rationale"]) > 0
        assert len(single_sig["detailed_explanation"]) > 0
        assert len(single_sig["investigation_questions"]) > 0

    # 7. Test REST API: GET /api/v1/analytics/organizations/{organization_id}/attention
    attn_resp = client.get(f"/api/v1/analytics/organizations/{org_id}/attention")
    assert attn_resp.status_code == 200
    attn_data = attn_resp.json()
    assert attn_data["organization_id"] == org_id
    assert 0.0 <= attn_data["attention_score"] <= 100.0
    assert attn_data["attention_band"] in {"LOW", "MODERATE", "ELEVATED", "HIGH"}
    assert len(attn_data["summary_rationale"]) > 0

    # 8. Test REST API: Submission Analytics Run
    sub_run_resp = client.post(
        "/api/v1/analytics/run",
        json={"submission_id": sub_id, "persist": True},
    )
    assert sub_run_resp.status_code == 200
    sub_run_data = sub_run_resp.json()
    assert sub_run_data["submission_id"] == sub_id

    # 9. Test Error Handling
    # Missing both org and sub
    invalid_run = client.post("/api/v1/analytics/run", json={})
    assert invalid_run.status_code == 400

    # Nonexistent signal
    missing_sig = client.get("/api/v1/analytics/signals/nonexistent-sig-id")
    assert missing_sig.status_code == 404

    # Nonexistent organization attention
    missing_attn = client.get("/api/v1/analytics/organizations/nonexistent-org-id/attention")
    assert missing_attn.status_code == 404
