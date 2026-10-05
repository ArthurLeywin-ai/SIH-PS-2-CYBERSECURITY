"""Canonical domain models representing submitted operational evidence and provenance.

Conforms strictly to DATA_SCHEMA.md.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.backend.domain.types import (
    ActionStatus,
    ActionType,
    AlertCategory,
    AlertSeverity,
    AlertStatus,
    AssetClass,
    AssetCriticality,
    CaseStatus,
    CaseType,
    ClosureStatus,
    Disposition,
    EntityCriticalityBand,
    ExceptionStatus,
    IngestionStatus,
    MonitoringCoverageState,
    OperatingModel,
    OrganizationStatus,
    PeriodMaturityState,
    PresenceState,
    ScaleBand,
    ValidationSeverity,
    ValueState,
)
from pydantic import BaseModel, ConfigDict, Field


class CanonicalDomainModel(BaseModel):
    """Immutable domain model with strict field checking."""

    model_config = ConfigDict(extra="forbid", frozen=True)


# ---------------------------------------------------------------------------
# Ingestion Package & Validation
# ---------------------------------------------------------------------------


class ValidationIssue(CanonicalDomainModel):
    """Structured validation finding recorded during ingestion."""

    code: str
    severity: ValidationSeverity
    scope: str
    target: str
    message: str
    expected: str | None = None
    actual: str | None = None


class IngestionPackage(CanonicalDomainModel):
    """Metadata representing an evidence package discovered and ingested."""

    package_id: UUID
    package_path: str
    package_name: str
    tier: str = "deterministic_fixture"
    split: str = "development"
    status: IngestionStatus = IngestionStatus.DISCOVERED
    manifest_hash: str | None = None
    tree_hash: str | None = None
    record_counts: dict[str, int] = Field(default_factory=dict)
    validation_issues: list[ValidationIssue] = Field(default_factory=list)
    discovered_at_utc: datetime
    completed_at_utc: datetime | None = None


# ---------------------------------------------------------------------------
# Provenance & Observations (DATA_SCHEMA.md §4.2, §6.4)
# ---------------------------------------------------------------------------


class EvidenceProvenance(CanonicalDomainModel):
    """Exact source-to-canonical trace answering which source file, locator, and field produced this record."""

    provenance_id: UUID
    canonical_record_id: UUID
    evidence_family: str
    organization_id: UUID
    submission_id: UUID | None = None
    source_file: str
    source_record_locator: str
    source_field: str
    raw_source_value: str | None = None
    canonical_field: str
    relationship_name: str | None = None
    target_canonical_id: UUID | None = None


class CanonicalFieldObservation(CanonicalDomainModel):
    """Semantic value state tracking for required and optional fields (§4.2)."""

    observation_id: UUID
    canonical_record_id: UUID
    evidence_family: str
    field_name: str
    value_state: ValueState
    raw_value: str | None = None
    normalized_value: str | None = None
    quality_issue: str | None = None


# ---------------------------------------------------------------------------
# 18 Canonical Operational Evidence Families
# ---------------------------------------------------------------------------


class CanonicalOrganization(CanonicalDomainModel):
    organization_id: UUID
    source_organization_id: str | None = None
    organization_name: str
    organization_alias: str | None = None
    sector_code: str
    subsector_code: str | None = None
    scale_band: ScaleBand
    operating_model: OperatingModel
    entity_criticality_band: EntityCriticalityBand
    asset_count_declared: int = 0
    critical_asset_count_declared: int = 0
    default_timezone: str = "UTC"
    profile_effective_start_at_utc: datetime
    profile_effective_end_at_utc: datetime | None = None
    profile_version: int = 1
    organization_status: OrganizationStatus


class CanonicalSubmission(CanonicalDomainModel):
    submission_id: UUID
    source_submission_id: str | None = None
    organization_id: UUID
    reporting_period_id: str | None = None
    period_maturity_state: PeriodMaturityState
    reporting_period_start_at_utc: datetime
    reporting_period_end_at_utc: datetime
    submitted_at_utc: datetime | None = None


class CanonicalSubmissionManifest(CanonicalDomainModel):
    manifest_id: UUID
    submission_id: UUID
    schema_version: str
    dataset_version: str
    generator_version: str
    tree_sha256: str
    declared_record_counts: dict[str, int] = Field(default_factory=dict)
    created_at_utc: datetime


class CanonicalSubmissionEvidenceFamily(CanonicalDomainModel):
    submission_family_id: UUID
    submission_id: UUID
    evidence_family: str
    presence_state: PresenceState
    declared_record_count: int = 0


class CanonicalControlProcessReference(CanonicalDomainModel):
    control_process_ref_id: UUID
    organization_id: UUID
    reference_type: str
    reference_code: str
    display_name: str
    authority_body: str = "PROJECT_DEMO_CONFIGURATION"
    effective_start_at_utc: datetime
    effective_end_at_utc: datetime | None = None


class CanonicalControlProcessSubjectLink(CanonicalDomainModel):
    control_process_link_id: UUID
    control_process_ref_id: UUID
    subject_type: str
    subject_id: UUID


class CanonicalAsset(CanonicalDomainModel):
    asset_id: UUID
    source_asset_id: str | None = None
    organization_id: UUID
    asset_class: AssetClass
    criticality: AssetCriticality
    operating_status: str = "ACTIVE"
    effective_start_at_utc: datetime
    effective_end_at_utc: datetime | None = None


class CanonicalMonitoringCoverage(CanonicalDomainModel):
    monitoring_coverage_id: UUID
    organization_id: UUID
    asset_id: UUID
    monitoring_type: str
    coverage_state: MonitoringCoverageState
    coverage_percentage: float = 100.0
    effective_start_at_utc: datetime
    effective_end_at_utc: datetime | None = None


class CanonicalAlert(CanonicalDomainModel):
    alert_id: UUID
    source_alert_id: str | None = None
    organization_id: UUID
    asset_id: UUID
    created_at_utc: datetime
    ingested_at_utc: datetime | None = None
    alert_category: AlertCategory
    severity: AlertSeverity
    status: AlertStatus
    disposition: Disposition
    rule_identifier: str | None = None
    summary: str


class CanonicalCase(CanonicalDomainModel):
    case_id: UUID
    source_case_id: str | None = None
    organization_id: UUID
    case_type: CaseType
    severity: AlertSeverity
    priority: str = "P2"
    status: CaseStatus
    disposition: Disposition
    created_at_utc: datetime
    assigned_at_utc: datetime | None = None
    started_at_utc: datetime | None = None
    resolved_at_utc: datetime | None = None
    closed_at_utc: datetime | None = None
    primary_assignee: str | None = None


class CanonicalCaseAlertLink(CanonicalDomainModel):
    case_alert_link_id: UUID
    case_id: UUID
    alert_id: UUID
    link_type: str = "PRIMARY"
    linked_at_utc: datetime


class CanonicalInvestigation(CanonicalDomainModel):
    investigation_id: UUID
    organization_id: UUID
    case_id: UUID | None = None
    alert_id: UUID | None = None
    started_at_utc: datetime
    completed_at_utc: datetime | None = None
    analyst_id: str | None = None
    disposition: Disposition | None = None
    summary: str
    notes: str | None = None


class CanonicalEscalation(CanonicalDomainModel):
    escalation_id: UUID
    organization_id: UUID
    case_id: UUID | None = None
    alert_id: UUID | None = None
    escalated_at_utc: datetime
    escalated_from_tier: str = "TIER_1"
    escalated_to_tier: str = "TIER_2"
    reason: str
    approved_by: str | None = None


class CanonicalAction(CanonicalDomainModel):
    action_id: UUID
    organization_id: UUID
    case_id: UUID | None = None
    alert_id: UUID | None = None
    asset_id: UUID | None = None
    action_type: ActionType
    status: ActionStatus
    created_at_utc: datetime
    completed_at_utc: datetime | None = None
    assigned_to: str | None = None
    summary: str


class CanonicalResolution(CanonicalDomainModel):
    resolution_id: UUID
    organization_id: UUID
    case_id: UUID | None = None
    alert_id: UUID | None = None
    resolved_at_utc: datetime
    resolution_type: str = "REMEDIATED"
    summary: str
    accepted_by: str | None = None


class CanonicalClosure(CanonicalDomainModel):
    closure_id: UUID
    organization_id: UUID
    case_id: UUID | None = None
    alert_id: UUID | None = None
    resolution_id: UUID | None = None
    closed_at_utc: datetime
    closure_status: ClosureStatus
    disposition: Disposition
    approved_by: str | None = None
    summary: str


class CanonicalException(CanonicalDomainModel):
    exception_id: UUID
    organization_id: UUID
    exception_type: str
    subject_type: str = "ASSET"
    subject_id: UUID
    status: ExceptionStatus
    reason: str
    approved_by: str | None = None
    effective_start_at_utc: datetime
    effective_end_at_utc: datetime | None = None


class CanonicalProcessChange(CanonicalDomainModel):
    process_change_id: UUID
    organization_id: UUID
    change_type: str
    effective_start_at_utc: datetime
    effective_end_at_utc: datetime | None = None
    description: str
    authorized_by: str | None = None
