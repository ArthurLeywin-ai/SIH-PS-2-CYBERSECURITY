"""Explicit Pydantic schemas for the SAT-SA REST API.

Guarantees stable, deterministic API contracts without leaking raw database objects.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BaseAPISchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")


# ---------------------------------------------------------------------------
# Health & Status
# ---------------------------------------------------------------------------


class HealthResponse(BaseAPISchema):
    status: str = "healthy"
    version: str = "0.1.0"
    mode: str = "offline_supervisor"
    timestamp_utc: datetime


class ReadinessResponse(BaseAPISchema):
    ready: bool
    database_connected: bool
    evidence_directory_accessible: bool
    timestamp_utc: datetime


# ---------------------------------------------------------------------------
# Ingestion Packages
# ---------------------------------------------------------------------------


class IngestPackageRequest(BaseAPISchema):
    package_path: str = Field(..., description="Absolute or relative path to evidence package")
    fail_on_error: bool = Field(False, description="Abort persistence if blocking validation errors occur")


class ValidationIssueSchema(BaseAPISchema):
    code: str
    severity: str
    scope: str
    target: str
    message: str
    expected: str | None = None
    actual: str | None = None


class IngestionPackageResponse(BaseAPISchema):
    package_id: str
    package_path: str
    package_name: str
    tier: str
    split: str
    status: str
    manifest_hash: str | None = None
    tree_hash: str | None = None
    record_counts: dict[str, int] = Field(default_factory=dict)
    validation_issues_count: int = 0
    discovered_at_utc: datetime
    completed_at_utc: datetime | None = None


class IngestionPackageDetailResponse(IngestionPackageResponse):
    validation_issues: list[ValidationIssueSchema] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Organizations
# ---------------------------------------------------------------------------


class OrganizationResponse(BaseAPISchema):
    organization_id: str
    source_organization_id: str | None = None
    organization_name: str
    organization_alias: str | None = None
    sector_code: str
    subsector_code: str | None = None
    scale_band: str
    operating_model: str
    entity_criticality_band: str
    asset_count_declared: int
    critical_asset_count_declared: int
    default_timezone: str
    organization_status: str
    profile_effective_start_at_utc: datetime
    profile_effective_end_at_utc: datetime | None = None


# ---------------------------------------------------------------------------
# Submissions & Manifests
# ---------------------------------------------------------------------------


class SubmissionManifestResponse(BaseAPISchema):
    manifest_id: str
    submission_id: str
    schema_version: str
    dataset_version: str
    generator_version: str
    tree_sha256: str
    declared_record_counts: dict[str, int]
    created_at_utc: datetime


class SubmissionEvidenceFamilyResponse(BaseAPISchema):
    submission_family_id: str
    evidence_family: str
    presence_state: str
    declared_record_count: int


class SubmissionResponse(BaseAPISchema):
    submission_id: str
    source_submission_id: str | None = None
    organization_id: str
    reporting_period_id: str | None = None
    period_maturity_state: str
    reporting_period_start_at_utc: datetime
    reporting_period_end_at_utc: datetime
    submitted_at_utc: datetime | None = None
    manifests: list[SubmissionManifestResponse] = Field(default_factory=list)
    families: list[SubmissionEvidenceFamilyResponse] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Operational Evidence (Alerts, Cases, Assets, Coverages)
# ---------------------------------------------------------------------------


class AlertResponse(BaseAPISchema):
    alert_id: str
    source_alert_id: str | None = None
    organization_id: str
    asset_id: str
    alert_category: str
    severity: str
    status: str
    disposition: str
    rule_identifier: str | None = None
    summary: str
    created_at_utc: datetime
    ingested_at_utc: datetime | None = None


class CaseAlertLinkResponse(BaseAPISchema):
    case_alert_link_id: str
    case_id: str
    alert_id: str
    link_type: str
    linked_at_utc: datetime


class InvestigationResponse(BaseAPISchema):
    investigation_id: str
    organization_id: str
    case_id: str | None = None
    alert_id: str | None = None
    started_at_utc: datetime
    completed_at_utc: datetime | None = None
    analyst_id: str | None = None
    disposition: str | None = None
    summary: str
    notes: str | None = None


class EscalationResponse(BaseAPISchema):
    escalation_id: str
    organization_id: str
    case_id: str | None = None
    alert_id: str | None = None
    escalated_at_utc: datetime
    escalated_from_tier: str
    escalated_to_tier: str
    reason: str
    approved_by: str | None = None


class ActionResponse(BaseAPISchema):
    action_id: str
    organization_id: str
    case_id: str | None = None
    alert_id: str | None = None
    asset_id: str | None = None
    action_type: str
    status: str
    created_at_utc: datetime
    completed_at_utc: datetime | None = None
    assigned_to: str | None = None
    summary: str


class ResolutionResponse(BaseAPISchema):
    resolution_id: str
    organization_id: str
    case_id: str | None = None
    alert_id: str | None = None
    resolved_at_utc: datetime
    resolution_type: str
    summary: str
    accepted_by: str | None = None


class ClosureResponse(BaseAPISchema):
    closure_id: str
    organization_id: str
    case_id: str | None = None
    alert_id: str | None = None
    resolution_id: str | None = None
    closed_at_utc: datetime
    closure_status: str
    disposition: str
    approved_by: str | None = None
    summary: str


class CaseSummaryResponse(BaseAPISchema):
    case_id: str
    source_case_id: str | None = None
    organization_id: str
    case_type: str
    severity: str
    priority: str
    status: str
    disposition: str
    created_at_utc: datetime
    assigned_at_utc: datetime | None = None
    started_at_utc: datetime | None = None
    resolved_at_utc: datetime | None = None
    closed_at_utc: datetime | None = None
    primary_assignee: str | None = None


class CaseDetailResponse(CaseSummaryResponse):
    alert_links: list[CaseAlertLinkResponse] = Field(default_factory=list)
    investigations: list[InvestigationResponse] = Field(default_factory=list)
    escalations: list[EscalationResponse] = Field(default_factory=list)
    actions: list[ActionResponse] = Field(default_factory=list)
    resolutions: list[ResolutionResponse] = Field(default_factory=list)
    closures: list[ClosureResponse] = Field(default_factory=list)


class AssetResponse(BaseAPISchema):
    asset_id: str
    source_asset_id: str | None = None
    organization_id: str
    asset_class: str
    criticality: str
    operating_status: str
    effective_start_at_utc: datetime
    effective_end_at_utc: datetime | None = None


class MonitoringCoverageResponse(BaseAPISchema):
    monitoring_coverage_id: str
    organization_id: str
    asset_id: str
    monitoring_type: str
    coverage_state: str
    coverage_percentage: float
    effective_start_at_utc: datetime
    effective_end_at_utc: datetime | None = None


# ---------------------------------------------------------------------------
# Provenance & Observations
# ---------------------------------------------------------------------------


class EvidenceProvenanceResponse(BaseAPISchema):
    provenance_id: str
    canonical_record_id: str
    evidence_family: str
    organization_id: str
    submission_id: str | None = None
    source_file: str
    source_record_locator: str
    source_field: str
    raw_source_value: str | None = None
    canonical_field: str
    relationship_name: str | None = None
    target_canonical_id: str | None = None


class CanonicalFieldObservationResponse(BaseAPISchema):
    observation_id: str
    canonical_record_id: str
    evidence_family: str
    field_name: str
    value_state: str
    raw_value: str | None = None
    normalized_value: str | None = None
    quality_issue: str | None = None
