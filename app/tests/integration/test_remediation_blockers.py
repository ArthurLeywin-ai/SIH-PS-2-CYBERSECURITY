"""Explicit regression tests for M6 Remediation Blockers:

1. Test 1: Ground Truth Isolation
   - Ingest an M5 package containing private_ground_truth/
   - Verify operational evidence succeeds
   - Verify NO records in evidence_provenance originate from private_ground_truth
   - Direct SQLite inspection confirms zero ground-truth records
   - Verify API exposes no scenario/oracle fields or ground-truth provenance

2. Test 2: Evidence-Root Boundary Enforcement
   - Package inside configured SATSA_EVIDENCE_DIR: ALLOWED
   - Package outside configured root: REJECTED (HTTP 403 / SECURITY_VIOLATION)
   - Path traversal '../' escaping root: REJECTED (HTTP 403 / SECURITY_VIOLATION)
   - Symlink escaping root: REJECTED (HTTP 403 / SECURITY_VIOLATION)

3. Test 3: Total Package Size Enforcement & Transactional Safety
   - Exceeding configured SATSA_MAX_PACKAGE_SIZE rejected before normalization
   - Zero canonical records persisted on size violation (transactional safety)
   - Structured error message returned
   - Package under limit succeeds

4. Test 4: Format Contract Support (Option A)
   - Multi-format package discovery across JSON, JSONL, and CSV
   - Full canonical normalization and database persistence
"""

from __future__ import annotations

import csv
import json
import shutil
import uuid
from pathlib import Path
from typing import Any

from app.backend.config import get_config
from app.backend.persistence.models import (
    AlertModel,
    AssetModel,
    CaseModel,
    EvidenceProvenanceModel,
    IngestionPackageModel,
    OrganizationModel,
)
from fastapi.testclient import TestClient
from satsa_generator.fixture.builder import build_fixture, parse_master_seed_hex
from sqlalchemy import text
from sqlalchemy.orm import Session


def _build_minimal_records(
    org_id: str | None = None,
    sub_id: str | None = None,
    asset_id: str | None = None,
    alert_id: str | None = None,
    case_id: str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Generate consistent relational records across all 8 mandatory families."""
    o_id = org_id or str(uuid.uuid4())
    s_id = sub_id or str(uuid.uuid4())
    a_id = asset_id or str(uuid.uuid4())
    al_id = alert_id or str(uuid.uuid4())
    c_id = case_id or str(uuid.uuid4())
    man_id = str(uuid.uuid4())
    fam_id = str(uuid.uuid4())
    cov_id = str(uuid.uuid4())

    return {
        "organizations": [
            {
                "organization_id": o_id,
                "organization_name": "Test Financial Corp",
                "organization_status": "ACTIVE",
                "operating_model": "INTERNAL",
                "scale_band": "TIER_1",
                "asset_count_declared": 10,
            }
        ],
        "submissions": [
            {
                "submission_id": s_id,
                "organization_id": o_id,
                "submission_status": "SUBMITTED",
            }
        ],
        "submission_manifests": [
            {
                "manifest_id": man_id,
                "submission_id": s_id,
            }
        ],
        "submission_evidence_families": [
            {
                "submission_family_id": fam_id,
                "submission_id": s_id,
                "evidence_family": "alerts",
                "presence_state": "PRESENT",
                "declared_record_count": 1,
            }
        ],
        "assets": [
            {
                "asset_id": a_id,
                "organization_id": o_id,
                "asset_class": "SERVER",
                "criticality": "TIER_1",
                "operating_status": "ACTIVE",
            }
        ],
        "monitoring_coverage": [
            {
                "monitoring_coverage_id": cov_id,
                "organization_id": o_id,
                "asset_id": a_id,
                "coverage_state": "COVERED",
                "coverage_percentage": 100.0,
            }
        ],
        "alerts": [
            {
                "alert_id": al_id,
                "organization_id": o_id,
                "asset_id": a_id,
                "created_at_utc": "2026-01-15T10:00:00Z",
                "alert_category": "AUTHENTICATION",
                "severity": "HIGH",
                "status": "NEW",
                "disposition": "TRUE_POSITIVE",
                "summary": "Suspicious login attempt detected",
            }
        ],
        "cases": [
            {
                "case_id": c_id,
                "organization_id": o_id,
                "case_type": "SECURITY_INCIDENT",
                "created_at_utc": "2026-01-15T11:00:00Z",
                "status": "OPEN",
            }
        ],
    }


def _create_package_on_disk(
    pkg_dir: Path,
    records: dict[str, list[dict[str, Any]]],
    file_format: str = "json",
) -> None:
    """Write package files in the specified format (.json, .jsonl, .csv)."""
    pkg_dir.mkdir(parents=True, exist_ok=True)
    for family, rec_list in records.items():
        if file_format == "json":
            file_path = pkg_dir / f"{family}.json"
            file_path.write_text(json.dumps(rec_list, indent=2), encoding="utf-8")
        elif file_format == "jsonl":
            file_path = pkg_dir / f"{family}.jsonl"
            lines = [json.dumps(r) for r in rec_list]
            file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        elif file_format == "csv":
            file_path = pkg_dir / f"{family}.csv"
            if rec_list:
                keys = list(rec_list[0].keys())
                with open(file_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=keys)
                    writer.writeheader()
                    for r in rec_list:
                        writer.writerow({k: (v if v is not None else "") for k, v in r.items()})


# ---------------------------------------------------------------------------
# Test 1: Ground Truth Isolation
# ---------------------------------------------------------------------------


def test_ground_truth_isolation(client: TestClient, test_db_session: Session, tmp_path: Path):
    """BLOCKER 1 Regression: Prove private ground truth NEVER enters operational storage.

    - Ingest an M5 package containing operational_evidence/ and private_ground_truth/
    - Verify ingestion succeeds
    - Verify direct SQLite query: ZERO records reference private_ground_truth
    - Verify evidence_provenance contains ONLY operational provenance
    - Verify API returns no scenario/oracle fields
    """
    cfg_file = Path("generator/config/public/base/fixture_config.json")
    if not cfg_file.exists():
        cfg_file = Path("config/public/base/fixture_config.json")

    seed = parse_master_seed_hex("0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef")
    raw_m5_out = tmp_path / "raw_m5_fixture"
    build_result = build_fixture(cfg_file, seed, output_root=raw_m5_out, milestone="m5")

    # Confirm the generator package actually contains private_ground_truth
    private_gt_dir = build_result.output_root / "private_ground_truth"
    assert private_gt_dir.is_dir(), "Fixture must contain private_ground_truth to test isolation"

    # Stage inside configured SATSA_EVIDENCE_DIR
    staged_pkg = get_config().evidence_dir / "isolated_m5_pkg"
    shutil.copytree(build_result.output_root, staged_pkg)

    # Ingest package via API
    resp = client.post(
        "/api/v1/packages/ingest",
        json={"package_path": str(staged_pkg), "fail_on_error": False},
    )
    assert resp.status_code == 201, f"Ingestion failed: {resp.text}"
    pkg_data = resp.json()
    assert pkg_data["status"] == "INGESTED"

    # DIRECT DATABASE INSPECTION (§BLOCKER 1 verification)
    db_session = test_db_session

    # 1. Total records in evidence_provenance table
    prov_count = db_session.query(EvidenceProvenanceModel).count()
    assert prov_count > 0, "Operational evidence provenance must be persisted"

    # 2. Assert NO record references private_ground_truth in source_file
    gt_source_records = db_session.execute(
        text("SELECT count(*) FROM evidence_provenance WHERE source_file LIKE '%private_ground_truth%'")
    ).scalar()
    assert gt_source_records == 0, f"Found {gt_source_records} provenance records with private_ground_truth source!"

    # 3. Assert NO record has ground_truth evidence_family
    gt_family_records = db_session.execute(
        text("SELECT count(*) FROM evidence_provenance WHERE evidence_family LIKE '%ground_truth%'")
    ).scalar()
    assert gt_family_records == 0, f"Found {gt_family_records} provenance records with ground_truth family!"

    # 4. Verify all provenance source files are strictly operational evidence files
    all_prov = db_session.query(EvidenceProvenanceModel).all()
    for prov in all_prov:
        assert "private_ground_truth" not in prov.source_file
        assert not prov.evidence_family.startswith("ground_truth")
        assert prov.evidence_family != "ground_truth_field"
        assert prov.evidence_family != "ground_truth_relationship"

    # 5. Verify API endpoints do not expose oracle/scenario data
    alerts_resp = client.get("/api/v1/evidence/alerts")
    assert alerts_resp.status_code == 200
    alerts = alerts_resp.json()
    for alert in alerts:
        # None of the generator scenario metadata or labels may exist in operational models
        assert "scenario_id" not in alert
        assert "scenario_name" not in alert
        assert "injection_type" not in alert
        assert "is_ground_truth" not in alert
        assert "oracle_label" not in alert


# ---------------------------------------------------------------------------
# Test 2: Evidence-Root Boundary Enforcement
# ---------------------------------------------------------------------------


def test_evidence_root_boundary_enforcement(client: TestClient, tmp_path: Path):
    """BLOCKER 2 Regression: Enforce configured SATSA_EVIDENCE_DIR as security boundary."""
    evidence_boundary = get_config().evidence_dir

    # 1. ALLOWED: Package inside configured root
    allowed_pkg = evidence_boundary / "allowed_package"
    records = _build_minimal_records()
    _create_package_on_disk(allowed_pkg, records, "json")

    allowed_resp = client.post(
        "/api/v1/packages/ingest",
        json={"package_path": str(allowed_pkg), "fail_on_error": True},
    )
    assert allowed_resp.status_code == 201, f"Allowed package failed: {allowed_resp.text}"
    assert allowed_resp.json()["status"] == "INGESTED"

    # 2. REJECTED: Package outside configured root
    outside_dir = tmp_path / "outside_evidence_dir"
    outside_pkg = outside_dir / "rogue_package"
    _create_package_on_disk(outside_pkg, records, "json")

    outside_resp = client.post(
        "/api/v1/packages/ingest",
        json={"package_path": str(outside_pkg), "fail_on_error": True},
    )
    assert outside_resp.status_code == 403, f"Expected 403 for outside package, got {outside_resp.status_code}"
    outside_err = outside_resp.json()
    assert outside_err["error_code"] == "SECURITY_VIOLATION"
    assert "outside permitted root" in outside_err["message"]

    # 3. REJECTED: Traversal with '../' attempting to escape root
    traversal_path = str(evidence_boundary / ".." / outside_dir.name / "rogue_package")
    traversal_resp = client.post(
        "/api/v1/packages/ingest",
        json={"package_path": traversal_path, "fail_on_error": True},
    )
    assert traversal_resp.status_code == 403
    assert traversal_resp.json()["error_code"] == "SECURITY_VIOLATION"

    # 4. REJECTED: Symlink inside root pointing outside root
    symlink_pkg = evidence_boundary / "escaping_symlink_pkg"
    if symlink_pkg.exists() or symlink_pkg.is_symlink():
        symlink_pkg.unlink()
    symlink_pkg.symlink_to(outside_pkg)

    symlink_resp = client.post(
        "/api/v1/packages/ingest",
        json={"package_path": str(symlink_pkg), "fail_on_error": True},
    )
    assert symlink_resp.status_code == 403
    assert symlink_resp.json()["error_code"] == "SECURITY_VIOLATION"


# ---------------------------------------------------------------------------
# Test 3: Total Package Size Enforcement & Transactional Safety
# ---------------------------------------------------------------------------


def test_package_size_limit_and_transactional_safety(
    client: TestClient, test_db_session: Session, monkeypatch
):
    """BLOCKER 4 Regression: Enforce total package size limit and verify zero partial records."""
    evidence_boundary = get_config().evidence_dir

    # Configure a tiny limit: 1500 bytes
    tiny_limit = 1500
    cfg = get_config()
    monkeypatch.setattr(cfg, "max_package_size_bytes", tiny_limit)

    # Count database rows before attempted ingestion
    initial_alerts = test_db_session.query(AlertModel).count()
    initial_orgs = test_db_session.query(OrganizationModel).count()
    initial_pkgs = test_db_session.query(IngestionPackageModel).count()

    # Create oversized package: total ~ 3000 bytes > 1500 limit
    oversized_pkg = evidence_boundary / "oversized_test_package"
    records = _build_minimal_records()
    _create_package_on_disk(oversized_pkg, records, "json")
    # Add filler file to safely exceed limit
    (oversized_pkg / "extra_padding.json").write_bytes(b" " * 2500)

    # Attempt ingestion
    resp = client.post(
        "/api/v1/packages/ingest",
        json={"package_path": str(oversized_pkg), "fail_on_error": True},
    )
    assert resp.status_code == 403, f"Expected 403 for oversized package, got {resp.status_code}"
    err = resp.json()
    assert err["error_code"] == "SECURITY_VIOLATION"
    assert "exceeds configured limit" in err["message"]

    # TRANSACTIONAL SAFETY ASSERTION: Zero partial persistence
    assert test_db_session.query(AlertModel).count() == initial_alerts
    assert test_db_session.query(OrganizationModel).count() == initial_orgs
    assert test_db_session.query(IngestionPackageModel).count() == initial_pkgs

    # Test package under limit succeeds
    monkeypatch.setattr(cfg, "max_package_size_bytes", 500 * 1024 * 1024)  # restore generous limit
    valid_pkg = evidence_boundary / "valid_size_package"
    _create_package_on_disk(valid_pkg, _build_minimal_records(), "json")

    success_resp = client.post(
        "/api/v1/packages/ingest",
        json={"package_path": str(valid_pkg), "fail_on_error": True},
    )
    assert success_resp.status_code == 201
    assert success_resp.json()["status"] == "INGESTED"


# ---------------------------------------------------------------------------
# Test 4: Format Contract Support (Option A: JSON, JSONL, CSV)
# ---------------------------------------------------------------------------


def test_format_contract_json_jsonl_csv(client: TestClient, test_db_session: Session):
    """BLOCKER 3 Regression: Verify discovery and ingestion of .json, .jsonl, and .csv formats."""
    evidence_boundary = get_config().evidence_dir

    # Format 1: JSON Package
    json_pkg = evidence_boundary / "format_contract_json"
    json_recs = _build_minimal_records()
    _create_package_on_disk(json_pkg, json_recs, "json")

    json_resp = client.post(
        "/api/v1/packages/ingest",
        json={"package_path": str(json_pkg), "fail_on_error": True},
    )
    assert json_resp.status_code == 201, f"JSON ingestion failed: {json_resp.text}"
    assert json_resp.json()["status"] == "INGESTED"

    # Format 2: JSONL Package
    jsonl_pkg = evidence_boundary / "format_contract_jsonl"
    jsonl_recs = _build_minimal_records()
    _create_package_on_disk(jsonl_pkg, jsonl_recs, "jsonl")

    jsonl_resp = client.post(
        "/api/v1/packages/ingest",
        json={"package_path": str(jsonl_pkg), "fail_on_error": True},
    )
    assert jsonl_resp.status_code == 201, f"JSONL ingestion failed: {jsonl_resp.text}"
    assert jsonl_resp.json()["status"] == "INGESTED"

    # Format 3: CSV Package
    csv_pkg = evidence_boundary / "format_contract_csv"
    csv_recs = _build_minimal_records()
    _create_package_on_disk(csv_pkg, csv_recs, "csv")

    csv_resp = client.post(
        "/api/v1/packages/ingest",
        json={"package_path": str(csv_pkg), "fail_on_error": True},
    )
    assert csv_resp.status_code == 201, f"CSV ingestion failed: {csv_resp.text}"
    assert csv_resp.json()["status"] == "INGESTED"

    # Verify canonical models exist in database for all 3 formats
    org_count = test_db_session.query(OrganizationModel).count()
    assert org_count >= 3
    alert_count = test_db_session.query(AlertModel).count()
    assert alert_count >= 3
    case_count = test_db_session.query(CaseModel).count()
    assert case_count >= 3
    asset_count = test_db_session.query(AssetModel).count()
    assert asset_count >= 3
