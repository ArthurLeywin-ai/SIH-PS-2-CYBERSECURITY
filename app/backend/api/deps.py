"""Dependency injection providers for FastAPI routes."""

from __future__ import annotations

from app.backend.persistence.database import get_db
from app.backend.services import (
    AnalyticsService,
    EvidenceService,
    OrganizationService,
    PackageService,
    ProvenanceService,
    SubmissionService,
)
from fastapi import Depends
from sqlalchemy.orm import Session


def get_package_service(session: Session = Depends(get_db)) -> PackageService:
    return PackageService(session)


def get_organization_service(session: Session = Depends(get_db)) -> OrganizationService:
    return OrganizationService(session)


def get_submission_service(session: Session = Depends(get_db)) -> SubmissionService:
    return SubmissionService(session)


def get_evidence_service(session: Session = Depends(get_db)) -> EvidenceService:
    return EvidenceService(session)


def get_provenance_service(session: Session = Depends(get_db)) -> ProvenanceService:
    return ProvenanceService(session)


def get_analytics_service(session: Session = Depends(get_db)) -> AnalyticsService:
    return AnalyticsService(session)

