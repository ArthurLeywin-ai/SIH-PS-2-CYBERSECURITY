"""Health and readiness probe endpoints."""

from __future__ import annotations

from datetime import UTC, datetime

from app.backend.api.schemas import HealthResponse, ReadinessResponse
from app.backend.config import get_config
from app.backend.persistence.database import get_db
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

router = APIRouter(tags=["Health & Readiness"])


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Basic liveness probe confirming service startup."""
    cfg = get_config()
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        mode="offline_supervisor" if not cfg.is_development else "development",
        timestamp_utc=datetime.now(UTC),
    )


@router.get("/readiness", response_model=ReadinessResponse)
def get_readiness(session: Session = Depends(get_db)) -> ReadinessResponse:
    """Readiness probe checking database connectivity and evidence storage availability."""
    db_connected = False
    try:
        session.execute(text("SELECT 1;"))
        db_connected = True
    except Exception:
        db_connected = False

    cfg = get_config()
    ev_accessible = cfg.evidence_dir.exists() and cfg.evidence_dir.is_dir()

    ready = db_connected and ev_accessible
    return ReadinessResponse(
        ready=ready,
        database_connected=db_connected,
        evidence_directory_accessible=ev_accessible,
        timestamp_utc=datetime.now(UTC),
    )
