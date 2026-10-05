"""SQLAlchemy declarative models for SAT-SA evidence storage.

Strictly follows DATA_SCHEMA.md.
"""

from __future__ import annotations

from datetime import datetime

from app.backend.persistence.database import Base
from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

# ---------------------------------------------------------------------------
# Package & Intake Tracking
# ---------------------------------------------------------------------------


class IngestionPackageModel(Base):
    __tablename__ = "ingestion_packages"

    package_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    package_path: Mapped[str] = mapped_column(String(512), nullable=False)
    package_name: Mapped[str] = mapped_column(String(256), nullable=False)
    tier: Mapped[str] = mapped_column(String(64), default="deterministic_fixture")
    split: Mapped[str] = mapped_column(String(64), default="development")
    status: Mapped[str] = mapped_column(String(32), default="DISCOVERED")
    manifest_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tree_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    record_counts: Mapped[dict] = mapped_column(JSON, default=dict)
    validation_issues: Mapped[list] = mapped_column(JSON, default=list)
    discovered_at_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at_utc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (Index("idx_packages_status", "status"),)


# ---------------------------------------------------------------------------
# Provenance & Observations (DATA_SCHEMA.md §4.2, §6.4)
# ---------------------------------------------------------------------------


class EvidenceProvenanceModel(Base):
    __tablename__ = "evidence_provenance"

    provenance_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    canonical_record_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    evidence_family: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    submission_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    source_file: Mapped[str] = mapped_column(String(256), nullable=False)
    source_record_locator: Mapped[str] = mapped_column(String(64), nullable=False)
    source_field: Mapped[str] = mapped_column(String(128), nullable=False)
    raw_source_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    canonical_field: Mapped[str] = mapped_column(String(128), nullable=False)
    relationship_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    target_canonical_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    __table_args__ = (
        Index("idx_provenance_family_record", "evidence_family", "canonical_record_id"),
        Index("idx_provenance_source", "source_file", "source_record_locator"),
    )


class CanonicalFieldObservationModel(Base):
    __tablename__ = "canonical_field_observations"

    observation_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    canonical_record_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    evidence_family: Mapped[str] = mapped_column(String(64), nullable=False)
    field_name: Mapped[str] = mapped_column(String(128), nullable=False)
    value_state: Mapped[str] = mapped_column(String(32), nullable=False)
    raw_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    quality_issue: Mapped[str | None] = mapped_column(String(256), nullable=True)

    __table_args__ = (
        Index("idx_obs_record_field", "canonical_record_id", "field_name"),
        Index("idx_obs_value_state", "value_state"),
    )


# ---------------------------------------------------------------------------
# 18 Canonical Operational Evidence Families
# ---------------------------------------------------------------------------


class OrganizationModel(Base):
    __tablename__ = "organizations"

    organization_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_organization_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    organization_name: Mapped[str] = mapped_column(String(160), nullable=False)
    organization_alias: Mapped[str | None] = mapped_column(String(80), nullable=True)
    sector_code: Mapped[str] = mapped_column(String(64), nullable=False)
    subsector_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    scale_band: Mapped[str] = mapped_column(String(32), nullable=False)
    operating_model: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_criticality_band: Mapped[str] = mapped_column(String(32), nullable=False)
    asset_count_declared: Mapped[int] = mapped_column(Integer, default=0)
    critical_asset_count_declared: Mapped[int] = mapped_column(Integer, default=0)
    default_timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    profile_effective_start_at_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    profile_effective_end_at_utc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    profile_version: Mapped[int] = mapped_column(Integer, default=1)
    organization_status: Mapped[str] = mapped_column(String(32), nullable=False)

    submissions: Mapped[list[SubmissionModel]] = relationship(
        "SubmissionModel", back_populates="organization", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_org_status", "organization_status"),
        Index("idx_org_sector", "sector_code"),
    )


class SubmissionModel(Base):
    __tablename__ = "submissions"

    submission_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_submission_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.organization_id"), nullable=False, index=True
    )
    reporting_period_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    period_maturity_state: Mapped[str] = mapped_column(String(32), nullable=False)
    reporting_period_start_at_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    reporting_period_end_at_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    submitted_at_utc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    organization: Mapped[OrganizationModel] = relationship("OrganizationModel", back_populates="submissions")
    manifests: Mapped[list[SubmissionManifestModel]] = relationship(
        "SubmissionManifestModel", back_populates="submission", cascade="all, delete-orphan"
    )
    families: Mapped[list[SubmissionEvidenceFamilyModel]] = relationship(
        "SubmissionEvidenceFamilyModel", back_populates="submission", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_sub_period", "reporting_period_start_at_utc", "reporting_period_end_at_utc"),)


class SubmissionManifestModel(Base):
    __tablename__ = "submission_manifests"

    manifest_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    submission_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("submissions.submission_id"), nullable=False, index=True
    )
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(64), nullable=False)
    generator_version: Mapped[str] = mapped_column(String(32), nullable=False)
    tree_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    declared_record_counts: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    submission: Mapped[SubmissionModel] = relationship("SubmissionModel", back_populates="manifests")


class SubmissionEvidenceFamilyModel(Base):
    __tablename__ = "submission_evidence_families"

    submission_family_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    submission_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("submissions.submission_id"), nullable=False, index=True
    )
    evidence_family: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    presence_state: Mapped[str] = mapped_column(String(32), nullable=False)
    declared_record_count: Mapped[int] = mapped_column(Integer, default=0)

    submission: Mapped[SubmissionModel] = relationship("SubmissionModel", back_populates="families")


class ControlProcessReferenceModel(Base):
    __tablename__ = "control_process_references"

    control_process_ref_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.organization_id"), nullable=False, index=True
    )
    reference_type: Mapped[str] = mapped_column(String(64), nullable=False)
    reference_code: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    authority_body: Mapped[str] = mapped_column(String(128), default="PROJECT_DEMO_CONFIGURATION")
    effective_start_at_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    effective_end_at_utc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ControlProcessSubjectLinkModel(Base):
    __tablename__ = "control_process_subject_links"

    control_process_link_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    control_process_ref_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("control_process_references.control_process_ref_id"),
        nullable=False,
        index=True,
    )
    subject_type: Mapped[str] = mapped_column(String(64), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)


class AssetModel(Base):
    __tablename__ = "assets"

    asset_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_asset_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.organization_id"), nullable=False, index=True
    )
    asset_class: Mapped[str] = mapped_column(String(64), nullable=False)
    criticality: Mapped[str] = mapped_column(String(32), nullable=False)
    operating_status: Mapped[str] = mapped_column(String(32), default="ACTIVE")
    effective_start_at_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    effective_end_at_utc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_asset_criticality", "criticality"),
        Index("idx_asset_class", "asset_class"),
    )


class MonitoringCoverageModel(Base):
    __tablename__ = "monitoring_coverage"

    monitoring_coverage_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.organization_id"), nullable=False, index=True
    )
    asset_id: Mapped[str] = mapped_column(String(36), ForeignKey("assets.asset_id"), nullable=False, index=True)
    monitoring_type: Mapped[str] = mapped_column(String(64), nullable=False)
    coverage_state: Mapped[str] = mapped_column(String(32), nullable=False)
    coverage_percentage: Mapped[float] = mapped_column(Float, default=100.0)
    effective_start_at_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    effective_end_at_utc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AlertModel(Base):
    __tablename__ = "alerts"

    alert_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_alert_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.organization_id"), nullable=False, index=True
    )
    asset_id: Mapped[str] = mapped_column(String(36), ForeignKey("assets.asset_id"), nullable=False, index=True)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    ingested_at_utc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    alert_category: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    disposition: Mapped[str] = mapped_column(String(64), nullable=False)
    rule_identifier: Mapped[str | None] = mapped_column(String(256), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        Index("idx_alert_org_sev", "organization_id", "severity"),
        Index("idx_alert_cat", "alert_category"),
    )


class CaseModel(Base):
    __tablename__ = "cases"

    case_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_case_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.organization_id"), nullable=False, index=True
    )
    case_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(16), default="P2")
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    disposition: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    assigned_at_utc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    started_at_utc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_at_utc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    closed_at_utc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    primary_assignee: Mapped[str | None] = mapped_column(String(128), nullable=True)

    alert_links: Mapped[list[CaseAlertLinkModel]] = relationship(
        "CaseAlertLinkModel", backref="case", foreign_keys="CaseAlertLinkModel.case_id"
    )
    investigations: Mapped[list[InvestigationModel]] = relationship(
        "InvestigationModel", backref="case", foreign_keys="InvestigationModel.case_id"
    )
    escalations: Mapped[list[EscalationModel]] = relationship(
        "EscalationModel", backref="case", foreign_keys="EscalationModel.case_id"
    )
    actions: Mapped[list[ActionModel]] = relationship("ActionModel", backref="case", foreign_keys="ActionModel.case_id")
    resolutions: Mapped[list[ResolutionModel]] = relationship(
        "ResolutionModel", backref="case", foreign_keys="ResolutionModel.case_id"
    )
    closures: Mapped[list[ClosureModel]] = relationship(
        "ClosureModel", backref="case", foreign_keys="ClosureModel.case_id"
    )

    __table_args__ = (
        Index("idx_case_org_status", "organization_id", "status"),
        Index("idx_case_created", "created_at_utc"),
    )


class CaseAlertLinkModel(Base):
    __tablename__ = "case_alert_links"

    case_alert_link_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.case_id"), nullable=False, index=True)
    alert_id: Mapped[str] = mapped_column(String(36), ForeignKey("alerts.alert_id"), nullable=False, index=True)
    link_type: Mapped[str] = mapped_column(String(64), default="PRIMARY")
    linked_at_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (Index("idx_link_case_alert", "case_id", "alert_id"),)


class InvestigationModel(Base):
    __tablename__ = "investigations"

    investigation_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.organization_id"), nullable=False, index=True
    )
    case_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("cases.case_id"), nullable=True, index=True)
    alert_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("alerts.alert_id"), nullable=True, index=True)
    started_at_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at_utc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    analyst_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    disposition: Mapped[str | None] = mapped_column(String(64), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class EscalationModel(Base):
    __tablename__ = "escalations"

    escalation_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.organization_id"), nullable=False, index=True
    )
    case_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("cases.case_id"), nullable=True, index=True)
    alert_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("alerts.alert_id"), nullable=True, index=True)
    escalated_at_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    escalated_from_tier: Mapped[str] = mapped_column(String(32), default="TIER_1")
    escalated_to_tier: Mapped[str] = mapped_column(String(32), default="TIER_2")
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)


class ActionModel(Base):
    __tablename__ = "actions"

    action_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.organization_id"), nullable=False, index=True
    )
    case_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("cases.case_id"), nullable=True, index=True)
    alert_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("alerts.alert_id"), nullable=True, index=True)
    asset_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("assets.asset_id"), nullable=True, index=True)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at_utc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    assigned_to: Mapped[str | None] = mapped_column(String(128), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)


class ResolutionModel(Base):
    __tablename__ = "resolutions"

    resolution_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.organization_id"), nullable=False, index=True
    )
    case_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("cases.case_id"), nullable=True, index=True)
    alert_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("alerts.alert_id"), nullable=True, index=True)
    resolved_at_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    resolution_type: Mapped[str] = mapped_column(String(64), default="REMEDIATED")
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    accepted_by: Mapped[str | None] = mapped_column(String(128), nullable=True)


class ClosureModel(Base):
    __tablename__ = "closures"

    closure_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.organization_id"), nullable=False, index=True
    )
    case_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("cases.case_id"), nullable=True, index=True)
    alert_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("alerts.alert_id"), nullable=True, index=True)
    resolution_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("resolutions.resolution_id"), nullable=True, index=True
    )
    closed_at_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    closure_status: Mapped[str] = mapped_column(String(32), nullable=False)
    disposition: Mapped[str] = mapped_column(String(64), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)


class ExceptionModel(Base):
    __tablename__ = "exceptions"

    exception_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.organization_id"), nullable=False, index=True
    )
    exception_type: Mapped[str] = mapped_column(String(64), nullable=False)
    subject_type: Mapped[str] = mapped_column(String(64), default="ASSET")
    subject_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    effective_start_at_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    effective_end_at_utc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ProcessChangeModel(Base):
    __tablename__ = "process_changes"

    process_change_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.organization_id"), nullable=False, index=True
    )
    change_type: Mapped[str] = mapped_column(String(64), nullable=False)
    effective_start_at_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    effective_end_at_utc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    authorized_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
