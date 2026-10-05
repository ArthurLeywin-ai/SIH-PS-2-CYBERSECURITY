"""Application services providing clear boundaries between persistence, ingestion, and API."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from app.backend.config import ApplicationConfig, get_config
from app.backend.errors import NotFoundError
from app.backend.ingestion.pipeline import IngestionPipeline, IngestionResult
from app.backend.persistence.models import IngestionPackageModel
from app.backend.persistence.repositories import (
    EvidenceRepository,
    OrganizationRepository,
    PackageRepository,
    ProvenanceRepository,
    SubmissionRepository,
)
from sqlalchemy.orm import Session


class PackageService:
    """Manages package discovery, validation status, and ingestion."""

    def __init__(self, session: Session, config: ApplicationConfig | None = None) -> None:
        self.session = session
        self.repo = PackageRepository(session)
        cfg = config or get_config()
        self.pipeline = IngestionPipeline(
            base_dir=cfg.evidence_dir,
            max_file_size_bytes=cfg.max_file_size_bytes,
            max_package_size_bytes=cfg.max_package_size_bytes,
        )

    def ingest(self, package_path: str | Path, fail_on_error: bool = False) -> IngestionResult:
        """Trigger ingestion of an evidence package."""
        return self.pipeline.run(package_path, db_session=self.session, fail_on_error=fail_on_error)

    def list_packages(
        self,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[IngestionPackageModel]:
        return self.repo.list_packages(status=status, limit=limit, offset=offset)

    def get_package(self, package_id: str | UUID) -> IngestionPackageModel:
        pkg = self.repo.get_by_id(package_id)
        if not pkg:
            raise NotFoundError(f"Evidence package '{package_id}' not found")
        return pkg


class OrganizationService:
    """Manages regulated entity profiles and discoveries."""

    def __init__(self, session: Session) -> None:
        self.repo = OrganizationRepository(session)

    def list_organizations(self, limit: int = 100, offset: int = 0):
        return self.repo.list_all(limit=limit, offset=offset)

    def get_organization(self, organization_id: str | UUID):
        org = self.repo.get_by_id(organization_id)
        if not org:
            raise NotFoundError(f"Organization '{organization_id}' not found")
        return org


class SubmissionService:
    """Manages evidence submissions and reporting periods."""

    def __init__(self, session: Session) -> None:
        self.repo = SubmissionRepository(session)

    def list_by_organization(self, organization_id: str | UUID, limit: int = 100, offset: int = 0):
        return self.repo.list_by_organization(organization_id, limit=limit, offset=offset)

    def get_submission(self, submission_id: str | UUID):
        sub = self.repo.get_by_id(submission_id)
        if not sub:
            raise NotFoundError(f"Submission '{submission_id}' not found")
        return sub


class EvidenceService:
    """Manages queries across canonical evidence families and case lifecycles."""

    def __init__(self, session: Session) -> None:
        self.repo = EvidenceRepository(session)

    def list_alerts(
        self,
        organization_id: str | UUID | None = None,
        severity: str | None = None,
        category: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ):
        return self.repo.list_alerts(
            organization_id=organization_id,
            severity=severity,
            category=category,
            status=status,
            limit=limit,
            offset=offset,
        )

    def get_alert(self, alert_id: str | UUID):
        alert = self.repo.get_alert_by_id(alert_id)
        if not alert:
            raise NotFoundError(f"Alert '{alert_id}' not found")
        return alert

    def list_cases(
        self,
        organization_id: str | UUID | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ):
        return self.repo.list_cases(organization_id=organization_id, status=status, limit=limit, offset=offset)

    def get_case(self, case_id: str | UUID):
        case = self.repo.get_case_by_id(case_id)
        if not case:
            raise NotFoundError(f"Case '{case_id}' not found")
        return case

    def list_assets(self, organization_id: str | UUID, limit: int = 100, offset: int = 0):
        return self.repo.list_assets(organization_id, limit=limit, offset=offset)

    def list_coverages(self, organization_id: str | UUID, limit: int = 100, offset: int = 0):
        return self.repo.list_coverages(organization_id, limit=limit, offset=offset)


class ProvenanceService:
    """Provides line-level provenance and field observation traces."""

    def __init__(self, session: Session) -> None:
        self.repo = ProvenanceRepository(session)

    def get_provenance(self, canonical_record_id: str | UUID, evidence_family: str | None = None):
        return self.repo.get_provenance_by_record_id(canonical_record_id, evidence_family=evidence_family)

    def get_observations(self, canonical_record_id: str | UUID):
        return self.repo.get_observations_by_record_id(canonical_record_id)
