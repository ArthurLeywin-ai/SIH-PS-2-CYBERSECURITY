"""Repository and data-access layer for SAT-SA persistence.

Provides isolated, transactional access to packages, organizations, submissions,
canonical operational evidence families, provenance records, and field observations.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.backend.persistence.models import (
    AlertModel,
    AssetModel,
    CanonicalFieldObservationModel,
    CaseModel,
    EvidenceProvenanceModel,
    IngestionPackageModel,
    MonitoringCoverageModel,
    OrganizationModel,
    SubmissionEvidenceFamilyModel,
    SubmissionManifestModel,
    SubmissionModel,
)
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, joinedload


class PackageRepository:
    """Data-access for IngestionPackage records."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, package: IngestionPackageModel) -> IngestionPackageModel:
        self.session.add(package)
        self.session.flush()
        return package

    def get_by_id(self, package_id: str | UUID) -> IngestionPackageModel | None:
        stmt = select(IngestionPackageModel).where(IngestionPackageModel.package_id == str(package_id))
        return self.session.scalars(stmt).first()

    def list_packages(
        self,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[IngestionPackageModel]:
        stmt = select(IngestionPackageModel).order_by(desc(IngestionPackageModel.discovered_at_utc))
        if status:
            stmt = stmt.where(IngestionPackageModel.status == status)
        stmt = stmt.limit(limit).offset(offset)
        return list(self.session.scalars(stmt).all())

    def update_status(
        self,
        package_id: str | UUID,
        status: str,
        validation_issues: list[dict[str, Any]] | None = None,
        record_counts: dict[str, int] | None = None,
        manifest_hash: str | None = None,
        tree_hash: str | None = None,
    ) -> IngestionPackageModel | None:
        pkg = self.get_by_id(package_id)
        if not pkg:
            return None
        pkg.status = status
        if validation_issues is not None:
            pkg.validation_issues = validation_issues
        if record_counts is not None:
            pkg.record_counts = record_counts
        if manifest_hash is not None:
            pkg.manifest_hash = manifest_hash
        if tree_hash is not None:
            pkg.tree_hash = tree_hash
        self.session.flush()
        return pkg


class OrganizationRepository:
    """Data-access for Canonical Organizations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, org: OrganizationModel) -> OrganizationModel:
        self.session.add(org)
        self.session.flush()
        return org

    def bulk_create(self, orgs: list[OrganizationModel]) -> None:
        if not orgs:
            return
        self.session.add_all(orgs)
        self.session.flush()

    def get_by_id(self, organization_id: str | UUID) -> OrganizationModel | None:
        stmt = select(OrganizationModel).where(OrganizationModel.organization_id == str(organization_id))
        return self.session.scalars(stmt).first()

    def list_all(self, limit: int = 100, offset: int = 0) -> list[OrganizationModel]:
        stmt = select(OrganizationModel).order_by(OrganizationModel.organization_name).limit(limit).offset(offset)
        return list(self.session.scalars(stmt).all())


class SubmissionRepository:
    """Data-access for Submissions and Manifests."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, submission: SubmissionModel) -> SubmissionModel:
        self.session.add(submission)
        self.session.flush()
        return submission

    def bulk_create(self, submissions: list[SubmissionModel]) -> None:
        if not submissions:
            return
        self.session.add_all(submissions)
        self.session.flush()

    def get_by_id(self, submission_id: str | UUID) -> SubmissionModel | None:
        stmt = (
            select(SubmissionModel)
            .where(SubmissionModel.submission_id == str(submission_id))
            .options(joinedload(SubmissionModel.manifests), joinedload(SubmissionModel.families))
        )
        return self.session.scalars(stmt).first()

    def list_by_organization(
        self,
        organization_id: str | UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[SubmissionModel]:
        stmt = (
            select(SubmissionModel)
            .where(SubmissionModel.organization_id == str(organization_id))
            .options(joinedload(SubmissionModel.manifests), joinedload(SubmissionModel.families))
            .order_by(desc(SubmissionModel.reporting_period_start_at_utc))
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt).unique().all())

    def create_manifest(self, manifest: SubmissionManifestModel) -> SubmissionManifestModel:
        self.session.add(manifest)
        self.session.flush()
        return manifest

    def bulk_create_evidence_families(self, families: list[SubmissionEvidenceFamilyModel]) -> None:
        if not families:
            return
        self.session.add_all(families)
        self.session.flush()


class EvidenceRepository:
    """Data-access for canonical operational evidence families."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # Bulk insert generic models
    def bulk_insert(self, models: list[Any]) -> None:
        if not models:
            return
        self.session.add_all(models)
        self.session.flush()

    # Alerts
    def list_alerts(
        self,
        organization_id: str | UUID | None = None,
        severity: str | None = None,
        category: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AlertModel]:
        stmt = select(AlertModel).order_by(desc(AlertModel.created_at_utc))
        if organization_id:
            stmt = stmt.where(AlertModel.organization_id == str(organization_id))
        if severity:
            stmt = stmt.where(AlertModel.severity == severity)
        if category:
            stmt = stmt.where(AlertModel.alert_category == category)
        if status:
            stmt = stmt.where(AlertModel.status == status)
        stmt = stmt.limit(limit).offset(offset)
        return list(self.session.scalars(stmt).all())

    def get_alert_by_id(self, alert_id: str | UUID) -> AlertModel | None:
        stmt = select(AlertModel).where(AlertModel.alert_id == str(alert_id))
        return self.session.scalars(stmt).first()

    # Cases
    def list_cases(
        self,
        organization_id: str | UUID | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CaseModel]:
        stmt = (
            select(CaseModel)
            .order_by(desc(CaseModel.created_at_utc))
            .options(
                joinedload(CaseModel.alert_links),
                joinedload(CaseModel.investigations),
                joinedload(CaseModel.escalations),
                joinedload(CaseModel.actions),
                joinedload(CaseModel.resolutions),
                joinedload(CaseModel.closures),
            )
        )
        if organization_id:
            stmt = stmt.where(CaseModel.organization_id == str(organization_id))
        if status:
            stmt = stmt.where(CaseModel.status == status)
        stmt = stmt.limit(limit).offset(offset)
        return list(self.session.scalars(stmt).unique().all())

    def get_case_by_id(self, case_id: str | UUID) -> CaseModel | None:
        stmt = (
            select(CaseModel)
            .where(CaseModel.case_id == str(case_id))
            .options(
                joinedload(CaseModel.alert_links),
                joinedload(CaseModel.investigations),
                joinedload(CaseModel.escalations),
                joinedload(CaseModel.actions),
                joinedload(CaseModel.resolutions),
                joinedload(CaseModel.closures),
            )
        )
        return self.session.scalars(stmt).unique().first()

    # Assets & Coverage
    def list_assets(
        self,
        organization_id: str | UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AssetModel]:
        stmt = (
            select(AssetModel)
            .where(AssetModel.organization_id == str(organization_id))
            .order_by(AssetModel.asset_id)
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt).all())

    def list_coverages(
        self,
        organization_id: str | UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MonitoringCoverageModel]:
        stmt = (
            select(MonitoringCoverageModel)
            .where(MonitoringCoverageModel.organization_id == str(organization_id))
            .order_by(MonitoringCoverageModel.monitoring_coverage_id)
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt).all())


class ProvenanceRepository:
    """Data-access for source-to-canonical provenance traces and field observations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def bulk_create_provenance(self, records: list[EvidenceProvenanceModel]) -> None:
        if not records:
            return
        self.session.add_all(records)
        self.session.flush()

    def bulk_create_observations(self, records: list[CanonicalFieldObservationModel]) -> None:
        if not records:
            return
        self.session.add_all(records)
        self.session.flush()

    def get_provenance_by_record_id(
        self,
        canonical_record_id: str | UUID,
        evidence_family: str | None = None,
    ) -> list[EvidenceProvenanceModel]:
        stmt = select(EvidenceProvenanceModel).where(
            EvidenceProvenanceModel.canonical_record_id == str(canonical_record_id)
        )
        if evidence_family:
            stmt = stmt.where(EvidenceProvenanceModel.evidence_family == evidence_family)
        return list(self.session.scalars(stmt).all())

    def get_provenance_by_source_locator(
        self,
        source_file: str,
        source_record_locator: str,
    ) -> list[EvidenceProvenanceModel]:
        stmt = select(EvidenceProvenanceModel).where(
            EvidenceProvenanceModel.source_file == source_file,
            EvidenceProvenanceModel.source_record_locator == source_record_locator,
        )
        return list(self.session.scalars(stmt).all())

    def get_observations_by_record_id(
        self,
        canonical_record_id: str | UUID,
    ) -> list[CanonicalFieldObservationModel]:
        stmt = select(CanonicalFieldObservationModel).where(
            CanonicalFieldObservationModel.canonical_record_id == str(canonical_record_id)
        )
        return list(self.session.scalars(stmt).all())
