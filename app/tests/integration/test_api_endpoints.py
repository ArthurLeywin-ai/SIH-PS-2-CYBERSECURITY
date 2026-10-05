"""Integration tests for FastAPI endpoints and error handling."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_api_health(client: TestClient):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp_utc" in data


def test_api_readiness(client: TestClient):
    resp = client.get("/api/v1/readiness")
    assert resp.status_code == 200
    data = resp.json()
    assert data["database_connected"] is True
    assert "ready" in data


def test_api_not_found_error_structure(client: TestClient):
    resp = client.get("/api/v1/organizations/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
    data = resp.json()
    assert data["error_code"] == "NOT_FOUND"
    assert "Organization '00000000-0000-0000-0000-000000000000' not found" in data["message"]
    assert "request_id" in data
    assert "timestamp_utc" in data


def test_api_invalid_ingest_path(client: TestClient):
    resp = client.post(
        "/api/v1/packages/ingest",
        json={"package_path": "/nonexistent/path/to/evidence", "fail_on_error": True},
    )
    assert resp.status_code == 422
    data = resp.json()
    assert data["error_code"] == "INVALID_EVIDENCE_PACKAGE"
