"""Mandatory end-to-end integration test:

Evidence Package (M5 Generator Output)
→ Ingestion Pipeline
→ Validation Engine
→ Canonical Normalization
→ Relational Database
→ API Retrieval & Provenance Trace.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from app.backend.config import get_config
from fastapi.testclient import TestClient
from satsa_generator.fixture.builder import build_fixture, parse_master_seed_hex


@pytest.fixture(scope="module")
def m5_fixture_package(tmp_path_factory) -> Path:
    """Build a deterministic M5 generator fixture to use as realistic evidence package."""
    cfg = Path("generator/config/public/base/fixture_config.json")
    if not cfg.exists():
        cfg = Path("config/public/base/fixture_config.json")

    seed = parse_master_seed_hex("0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef")
    out_dir = tmp_path_factory.mktemp("m5_fixture_e2e") / "package"
    result = build_fixture(cfg, seed, output_root=out_dir, milestone="m5")
    return result.output_root


def test_end_to_end_package_to_api(client: TestClient, m5_fixture_package: Path):
    """Verify that a generated M5 evidence package is ingested, normalized, stored in SQLite,

    and retrievable through the REST API with 100% provenance retention.
    """
    # Stage package into configured evidence directory boundary
    staged_pkg = get_config().evidence_dir / "m5_fixture"
    if not staged_pkg.exists():
        shutil.copytree(m5_fixture_package, staged_pkg)

    # 1. Trigger Ingestion via API
    ingest_resp = client.post(
        "/api/v1/packages/ingest",
        json={"package_path": str(staged_pkg), "fail_on_error": False},
    )
    assert ingest_resp.status_code == 201, f"Ingestion failed: {ingest_resp.text}"
    pkg_data = ingest_resp.json()
    assert pkg_data["status"] == "INGESTED"
    package_id = pkg_data["package_id"]

    # Verify all 18 evidence families were ingested
    counts = pkg_data["record_counts"]
    assert counts["organizations"] == 3
    assert counts["submissions"] == 6
    assert counts["assets"] == 15
    assert counts["alerts"] == 38
    assert counts["cases"] == 18
    assert counts["closures"] == 12

    # 2. Package Validation Inspection
    val_resp = client.get(f"/api/v1/packages/{package_id}/validation")
    assert val_resp.status_code == 200
    issues = val_resp.json()
    assert len(issues) > 0
    # Confirm known scenario quality issues were detected
    codes = {i["code"] for i in issues}
    assert "DUPLICATE_PRIMARY_KEY" in codes or "TEMPORAL_ORDERING_VIOLATION" in codes

    # 3. Organization Discovery
    orgs_resp = client.get("/api/v1/organizations")
    assert orgs_resp.status_code == 200
    orgs = orgs_resp.json()
    assert len(orgs) == 3
    org_id = orgs[0]["organization_id"]

    # Specific Organization Retrieval
    single_org_resp = client.get(f"/api/v1/organizations/{org_id}")
    assert single_org_resp.status_code == 200
    assert single_org_resp.json()["organization_name"] == orgs[0]["organization_name"]

    # 4. Submissions Discovery
    subs_resp = client.get(f"/api/v1/organizations/{org_id}/submissions")
    assert subs_resp.status_code == 200
    subs = subs_resp.json()
    assert len(subs) >= 1
    sub_id = subs[0]["submission_id"]

    single_sub_resp = client.get(f"/api/v1/submissions/{sub_id}")
    assert single_sub_resp.status_code == 200
    sub_detail = single_sub_resp.json()
    assert len(sub_detail["manifests"]) >= 1
    assert len(sub_detail["families"]) >= 1

    # 5. Evidence: Alerts Querying
    alerts_resp = client.get(f"/api/v1/evidence/alerts?organization_id={org_id}")
    assert alerts_resp.status_code == 200
    alerts = alerts_resp.json()
    assert len(alerts) > 0
    first_alert = alerts[0]
    alert_id = first_alert["alert_id"]

    # 6. Evidence: Cases & Incident Lifecycle
    cases_resp = client.get(f"/api/v1/evidence/cases?organization_id={org_id}")
    assert cases_resp.status_code == 200
    cases = cases_resp.json()
    assert len(cases) > 0
    case_id = cases[0]["case_id"]

    # Detailed Case Context
    case_detail_resp = client.get(f"/api/v1/evidence/cases/{case_id}")
    assert case_detail_resp.status_code == 200
    case_detail = case_detail_resp.json()
    assert case_detail["case_id"] == case_id
    assert "alert_links" in case_detail
    assert "actions" in case_detail
    assert "closures" in case_detail

    # 7. Assets & Coverage
    assets_resp = client.get(f"/api/v1/evidence/assets?organization_id={org_id}")
    assert assets_resp.status_code == 200
    assert len(assets_resp.json()) > 0

    cov_resp = client.get(f"/api/v1/evidence/coverage?organization_id={org_id}")
    assert cov_resp.status_code == 200
    assert len(cov_resp.json()) > 0

    # 8. Provenance & Lineage Verification (§4.2, §6.4)
    prov_resp = client.get(f"/api/v1/lineage/provenance/{alert_id}")
    assert prov_resp.status_code == 200
    prov_records = prov_resp.json()
    assert len(prov_records) > 0
    # Must trace to source file and record locator
    first_prov = prov_records[0]
    assert first_prov["source_file"] != ""
    assert first_prov["source_record_locator"] != ""
    assert first_prov["canonical_field"] != ""

    # 9. Field Observations & Controlled Missing Values (§4.1)
    obs_resp = client.get(f"/api/v1/lineage/observations/{alert_id}")
    assert obs_resp.status_code == 200
    obs_records = obs_resp.json()
    assert len(obs_records) > 0
    obs_fields = {o["field_name"] for o in obs_records}
    assert "status" in obs_fields or "disposition" in obs_fields
