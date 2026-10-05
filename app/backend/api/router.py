"""Master API v1 Router for SAT-SA."""

from __future__ import annotations

from app.backend.api.routes import (
    evidence,
    health,
    ingestion,
    organizations,
    provenance,
    submissions,
)
from fastapi import APIRouter

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(health.router)
api_v1_router.include_router(ingestion.router)
api_v1_router.include_router(organizations.router)
api_v1_router.include_router(submissions.router)
api_v1_router.include_router(evidence.router)
api_v1_router.include_router(provenance.router)
