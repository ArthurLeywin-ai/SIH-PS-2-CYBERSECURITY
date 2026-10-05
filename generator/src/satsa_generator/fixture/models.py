"""Strict schema-shaped records used only by the Milestone 1 fixture."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class FixtureRecord(BaseModel):
    """Immutable fixture record with no silently ignored fields."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class OrganizationRecord(FixtureRecord):
    organization_id: UUID
    source_organization_id: str | None = Field(default=None, min_length=1, max_length=256)
    organization_name: str = Field(min_length=1, max_length=160)
    organization_alias: str | None = Field(default=None, max_length=80)
    sector_code: str = Field(min_length=1, max_length=64)
    subsector_code: str | None = Field(default=None, max_length=64)
    scale_band: Literal["SMALL", "MEDIUM", "LARGE", "VERY_LARGE", "UNKNOWN"]
    operating_model: Literal[
        "CENTRALIZED_24X7",
        "CENTRALIZED_BUSINESS_HOURS",
        "DISTRIBUTED",
        "HYBRID",
        "UNKNOWN",
    ]
    entity_criticality_band: Literal["STANDARD", "ELEVATED", "HIGH", "UNKNOWN"]
    asset_count_declared: int = Field(ge=0)
    critical_asset_count_declared: int = Field(ge=0)
    default_timezone: str = Field(default="UTC", max_length=64)
    profile_effective_start_at_utc: datetime
    profile_effective_end_at_utc: datetime | None = None
    profile_version: int = Field(ge=1)
    organization_status: Literal["ACTIVE", "INACTIVE", "UNKNOWN"]

    @model_validator(mode="after")
    def validate_counts_and_time(self) -> OrganizationRecord:
        if self.critical_asset_count_declared > self.asset_count_declared:
            raise ValueError("critical asset count cannot exceed asset count")
        if (
            self.profile_effective_end_at_utc is not None
            and self.profile_effective_end_at_utc <= self.profile_effective_start_at_utc
        ):
            raise ValueError("profile effective end must be after start")
        return self


class SubmissionRecord(FixtureRecord):
    submission_id: UUID
    source_submission_id: str | None = Field(default=None, min_length=1, max_length=256)
    organization_id: UUID
    reporting_period_start_at_utc: datetime
    reporting_period_end_at_utc: datetime
    submitted_at_utc: datetime | None = None
    received_at_utc: datetime
    source_system_set_id: str | None = Field(default=None, max_length=128)
    source_system_versions: dict[str, str] | None = None
    declared_completeness: Literal["DECLARED_COMPLETE", "DECLARED_PARTIAL", "NOT_DECLARED"]
    declared_missing_families: list[dict[str, str]] | None = None
    submission_status: Literal[
        "QUARANTINED",
        "VALIDATING",
        "CONDITIONALLY_ACCEPTED",
        "ACCEPTED",
        "REJECTED",
        "SUPERSEDED",
    ]
    period_maturity_state: Literal["MATURE", "IMMATURE", "PARTIAL", "UNKNOWN"]
    manifest_id: UUID
    schema_profile_id: UUID | None = None
    submission_notes: str | None = None
    supersedes_submission_id: UUID | None = None
    submission_quality_state: Literal["VALID", "WARNING", "INVALID", "INCOMPLETE", "UNKNOWN"]

    @field_validator("declared_missing_families")
    @classmethod
    def validate_missing_family_shape(
        cls, value: list[dict[str, str]] | None
    ) -> list[dict[str, str]] | None:
        if value is None:
            return value
        for entry in value:
            if "evidence_family" not in entry:
                raise ValueError("each declared_missing_families entry needs evidence_family")
            if set(entry) - {"evidence_family", "reason"}:
                raise ValueError("unexpected declared_missing_families field")
        return value

    @model_validator(mode="after")
    def validate_temporal_order(self) -> SubmissionRecord:
        if self.reporting_period_end_at_utc <= self.reporting_period_start_at_utc:
            raise ValueError("reporting period end must be after start")
        if self.submitted_at_utc and self.received_at_utc < self.submitted_at_utc:
            raise ValueError("received_at_utc cannot precede submitted_at_utc")
        return self


class SubmissionManifestRecord(FixtureRecord):
    manifest_id: UUID
    submission_id: UUID
    manifest_version: int = Field(ge=1)
    created_at_utc: datetime
    file_count: int = Field(ge=0)
    total_bytes: int = Field(ge=0)
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    ingestion_run_id: UUID
    created_by_actor_id: UUID


class FixtureManifest(FixtureRecord):
    fixture_contract: Literal[
        "SATSA-M1-FIXTURE-V1",
        "SATSA-M2-FIXTURE-V1",
        "SATSA-M3-FIXTURE-V1",
        "SATSA-M4-FIXTURE-V1",
        "SATSA-M5-FIXTURE-V1",
    ]
    dataset_id: UUID
    dataset_version: str
    generator_version: str
    generator_build_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    schema_version: str
    config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    version_tuple_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    seed_derivation_version: str
    stream_fingerprints: dict[str, str]
    created_at_utc: datetime
    record_counts: dict[str, int]
    files: list[dict[str, Any]]


class SubmissionFamilyDeclarationRecord(FixtureRecord):
    submission_family_id: UUID
    submission_id: UUID
    evidence_family: str = Field(min_length=1, max_length=64)
    presence_state: Literal["PROVIDED", "NOT_PROVIDED", "NOT_APPLICABLE", "UNKNOWN"]
    declared_record_count: int | None = Field(default=None, ge=0)
    observed_parsed_record_count: int | None = Field(default=None, ge=0)
    coverage_start_at_utc: datetime | None = None
    coverage_end_at_utc: datetime | None = None
    completeness_state: Literal["COMPLETE", "PARTIAL", "IMMATURE", "UNKNOWN_SCOPE", "INVALID"]
    completeness_reason: str | None = None
    assessed_at_utc: datetime

    @model_validator(mode="after")
    def validate_coverage(self) -> SubmissionFamilyDeclarationRecord:
        if (
            self.coverage_start_at_utc is not None
            and self.coverage_end_at_utc is not None
            and self.coverage_end_at_utc <= self.coverage_start_at_utc
        ):
            raise ValueError("coverage_end_at_utc must be after coverage_start_at_utc")
        return self


class ControlProcessReferenceRecord(FixtureRecord):
    control_process_ref_id: UUID
    organization_id: UUID | None = None
    reference_type: Literal["CONTROL", "PROCESS"]
    reference_code: str = Field(min_length=1, max_length=64)
    source_reference_id: str | None = Field(default=None, min_length=1, max_length=256)
    display_name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    authority_type: Literal[
        "SOURCE_SUBMITTED",
        "PROJECT_DEMO_CONFIGURATION",
        "AUTHORITATIVE_CONFIGURATION",
        "OTHER",
        "UNKNOWN",
    ]
    source_reference_text: str | None = Field(default=None, max_length=512)
    version: str = Field(min_length=1, max_length=64)
    effective_start_at_utc: datetime
    effective_end_at_utc: datetime | None = None
    status: Literal["DRAFT", "ACTIVE", "SUPERSEDED", "RETIRED", "UNKNOWN"]
    submission_id: UUID | None = None
    source_record_id: UUID | None = None

    @model_validator(mode="after")
    def validate_interval(self) -> ControlProcessReferenceRecord:
        if (
            self.effective_end_at_utc is not None
            and self.effective_end_at_utc <= self.effective_start_at_utc
        ):
            raise ValueError("effective_end_at_utc must be after effective_start_at_utc")
        return self


class ControlProcessSubjectLinkRecord(FixtureRecord):
    control_process_link_id: UUID
    control_process_ref_id: UUID
    subject_type: Literal[
        "ORGANIZATION",
        "ASSET",
        "ALERT",
        "CASE",
        "INVESTIGATION",
        "ESCALATION",
        "ACTION",
        "RESOLUTION",
        "CLOSURE",
        "RULE_EXPECTATION",
        "FINDING",
        "REVIEW_SAMPLE",
    ]
    subject_id: UUID
    link_role: Literal[
        "APPLIES_TO",
        "ASSESSES",
        "AFFECTS",
        "SUPPORTS",
        "EXCEPTION_FOR",
        "PRIORITIZES",
    ]
    effective_start_at_utc: datetime | None = None
    effective_end_at_utc: datetime | None = None
    source_type: Literal[
        "SOURCE_SUBMITTED",
        "MAPPING_DERIVED",
        "RULE_CONFIGURATION",
        "EXAMINER_ASSIGNED",
        "UNKNOWN",
    ]
    source_record_id: UUID | None = None
    quality_state: Literal["VALID", "WARNING", "INVALID", "INCOMPLETE", "UNKNOWN"]

    @model_validator(mode="after")
    def validate_interval(self) -> ControlProcessSubjectLinkRecord:
        if (
            self.effective_start_at_utc is not None
            and self.effective_end_at_utc is not None
            and self.effective_end_at_utc <= self.effective_start_at_utc
        ):
            raise ValueError("effective_end_at_utc must be after effective_start_at_utc")
        return self


class AssetRecord(FixtureRecord):
    asset_id: UUID
    source_asset_id: str | None = Field(default=None, min_length=1, max_length=256)
    organization_id: UUID
    asset_alias: str | None = Field(default=None, max_length=128)
    asset_class: Literal[
        "SERVER",
        "ENDPOINT",
        "NETWORK",
        "APPLICATION",
        "CLOUD_RESOURCE",
        "DATABASE",
        "SERVICE",
        "OTHER",
        "UNKNOWN",
    ]
    asset_criticality: Literal["LOW", "MODERATE", "HIGH", "CRITICAL", "UNKNOWN"]
    environment: Literal["PRODUCTION", "DR", "TEST", "DEVELOPMENT", "OTHER", "UNKNOWN"] | None = (
        None
    )
    business_service_code: str | None = Field(default=None, max_length=128)
    monitoring_expected: bool = True
    monitoring_expectation_basis: (
        Literal["DECLARED", "ASSET_CLASS_POLICY", "RULE_CONFIGURATION", "UNKNOWN"] | None
    ) = None
    active_status: Literal["ACTIVE", "INACTIVE", "DECOMMISSIONING", "UNKNOWN"]
    effective_start_at_utc: datetime
    effective_end_at_utc: datetime | None = None
    owner_role_code: str | None = Field(default=None, max_length=128)
    source_system_id: str | None = Field(default=None, max_length=128)
    asset_profile_version: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def validate_interval(self) -> AssetRecord:
        if (
            self.effective_end_at_utc is not None
            and self.effective_end_at_utc <= self.effective_start_at_utc
        ):
            raise ValueError("effective_end_at_utc must be after effective_start_at_utc")
        return self


class MonitoringCoverageRecord(FixtureRecord):
    monitoring_coverage_id: UUID
    source_coverage_id: str | None = Field(default=None, min_length=1, max_length=256)
    organization_id: UUID
    asset_id: UUID
    monitoring_type: Literal[
        "SIEM_ALERTING",
        "ENDPOINT_MONITORING",
        "NETWORK_MONITORING",
        "APPLICATION_MONITORING",
        "LOG_COLLECTION",
        "OTHER",
        "UNKNOWN",
    ]
    expectation_state: Literal["EXPECTED", "OPTIONAL", "NOT_APPLICABLE", "UNKNOWN"]
    expectation_basis: Literal[
        "DECLARED", "RULE_CONFIGURATION", "ASSET_PROFILE", "EXCEPTION", "UNKNOWN"
    ]
    coverage_state: Literal[
        "COVERED",
        "PARTIALLY_COVERED",
        "NOT_COVERED",
        "ONBOARDING",
        "DEGRADED",
        "SUSPENDED",
        "UNKNOWN",
    ]
    coverage_source_type: Literal[
        "DECLARED", "SOURCE_HEALTH_EXPORT", "CONFIG_EXPORT", "INFERRED", "UNKNOWN"
    ]
    coverage_start_at_utc: datetime
    coverage_end_at_utc: datetime | None = None
    last_evidence_at_utc: datetime | None = None
    source_system_id: str | None = Field(default=None, max_length=128)
    coverage_reason: str | None = None
    exception_id: UUID | None = None
    coverage_quality_state: Literal["VALID", "WARNING", "INVALID", "INCOMPLETE", "UNKNOWN"]

    @model_validator(mode="after")
    def validate_interval(self) -> MonitoringCoverageRecord:
        if (
            self.coverage_end_at_utc is not None
            and self.coverage_end_at_utc <= self.coverage_start_at_utc
        ):
            raise ValueError("coverage_end_at_utc must be after coverage_start_at_utc")
        return self


class AlertRecord(FixtureRecord):
    alert_id: UUID
    source_alert_id: str | None = Field(default=None, min_length=1, max_length=256)
    organization_id: UUID
    asset_id: UUID | None = None
    source_system_id: str | None = Field(default=None, max_length=128)
    source_detection_id: str | None = Field(default=None, max_length=256)
    alert_category: Literal[
        "AUTHENTICATION",
        "ENDPOINT",
        "NETWORK",
        "APPLICATION",
        "DATA_ACCESS",
        "MALWARE",
        "POLICY_VIOLATION",
        "AVAILABILITY",
        "OTHER",
        "UNKNOWN",
    ]
    alert_type: str | None = Field(default=None, max_length=160)
    severity: Literal["INFORMATIONAL", "LOW", "MEDIUM", "HIGH", "CRITICAL", "UNKNOWN"]
    source_severity_text: str = Field(min_length=1, max_length=128)
    created_at_utc: datetime
    acknowledged_at_utc: datetime | None = None
    first_investigated_at_utc: datetime | None = None
    resolved_at_utc: datetime | None = None
    closed_at_utc: datetime | None = None
    last_updated_at_utc: datetime | None = None
    alert_status: Literal[
        "NEW",
        "OPEN",
        "ACKNOWLEDGED",
        "IN_INVESTIGATION",
        "RESOLVED",
        "CLOSED",
        "SUPPRESSED",
        "REOPENED",
        "UNKNOWN",
    ]
    disposition: (
        Literal[
            "TRUE_POSITIVE",
            "FALSE_POSITIVE",
            "BENIGN",
            "DUPLICATE",
            "SUPPRESSED",
            "ACCEPTED_RISK",
            "NO_ACTION_REQUIRED",
            "CONFIRMED_INCIDENT",
            "OTHER",
            "UNKNOWN",
        ]
        | None
    ) = None
    disposition_reason: str | None = None
    automation_state: Literal["MANUAL", "AUTOMATED", "MIXED", "UNKNOWN"] | None = None
    suppression_state: (
        Literal["NOT_SUPPRESSED", "SUPPRESSED", "PARTIALLY_SUPPRESSED", "UNKNOWN"] | None
    ) = None
    suppression_rule_id: str | None = Field(default=None, max_length=128)
    primary_case_source_id: str | None = Field(default=None, min_length=1, max_length=256)
    occurrence_count_source: int | None = Field(default=1, ge=1)
    alert_summary: str | None = None
    workflow_version: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def validate_temporal(self) -> AlertRecord:
        if self.acknowledged_at_utc and self.acknowledged_at_utc < self.created_at_utc:
            raise ValueError("acknowledged_at_utc cannot precede created_at_utc")
        if self.resolved_at_utc and self.resolved_at_utc < self.created_at_utc:
            raise ValueError("resolved_at_utc cannot precede created_at_utc")
        if self.closed_at_utc and self.closed_at_utc < self.created_at_utc:
            raise ValueError("closed_at_utc cannot precede created_at_utc")
        return self


class CaseRecord(FixtureRecord):
    case_id: UUID
    source_case_id: str | None = Field(default=None, min_length=1, max_length=256)
    organization_id: UUID
    case_type: Literal["ALERT_CASE", "INCIDENT", "PROBLEM", "SERVICE_REQUEST", "OTHER", "UNKNOWN"]
    case_category: str | None = Field(default=None, max_length=128)
    severity: Literal["INFORMATIONAL", "LOW", "MEDIUM", "HIGH", "CRITICAL", "UNKNOWN"]
    priority_source_text: str | None = Field(default=None, max_length=128)
    created_at_utc: datetime
    assigned_at_utc: datetime | None = None
    resolved_at_utc: datetime | None = None
    closed_at_utc: datetime | None = None
    last_updated_at_utc: datetime | None = None
    case_status: Literal[
        "NEW",
        "OPEN",
        "ASSIGNED",
        "IN_INVESTIGATION",
        "PENDING",
        "ESCALATED",
        "RESOLVED",
        "CLOSED",
        "REOPENED",
        "CANCELLED",
        "UNKNOWN",
    ]
    assigned_team_code: str | None = Field(default=None, max_length=128)
    assigned_analyst_pseudonym: str | None = Field(default=None, max_length=128)
    workflow_version: str | None = Field(default=None, max_length=64)
    case_summary: str | None = None
    disposition: (
        Literal[
            "TRUE_POSITIVE",
            "FALSE_POSITIVE",
            "BENIGN",
            "DUPLICATE",
            "SUPPRESSED",
            "ACCEPTED_RISK",
            "NO_ACTION_REQUIRED",
            "CONFIRMED_INCIDENT",
            "OTHER",
            "UNKNOWN",
        ]
        | None
    ) = None
    external_case_reference: str | None = Field(default=None, max_length=256)
    case_record_state: Literal["OPEN_STATE", "FINAL_STATE", "REOPENED_STATE", "UNKNOWN"]

    @model_validator(mode="after")
    def validate_temporal(self) -> CaseRecord:
        if self.assigned_at_utc and self.assigned_at_utc < self.created_at_utc:
            raise ValueError("assigned_at_utc cannot precede created_at_utc")
        if self.resolved_at_utc and self.resolved_at_utc < self.created_at_utc:
            raise ValueError("resolved_at_utc cannot precede created_at_utc")
        if self.closed_at_utc and self.closed_at_utc < self.created_at_utc:
            raise ValueError("closed_at_utc cannot precede created_at_utc")
        return self


class CaseAlertLinkRecord(FixtureRecord):
    case_alert_link_id: UUID
    case_id: UUID
    alert_id: UUID
    link_type: Literal["PRIMARY", "RELATED", "DUPLICATE_OF", "CAUSED_BY", "UNKNOWN"]
    linked_at_utc: datetime | None = None
    source_link_id: str | None = Field(default=None, min_length=1, max_length=256)
    link_source: Literal["EXPLICIT", "SOURCE_FOREIGN_KEY", "MAPPING_RESOLUTION", "UNKNOWN"]
    link_quality_state: Literal["VALID", "WARNING", "INVALID", "INCOMPLETE", "UNKNOWN"]


class InvestigationRecord(FixtureRecord):
    investigation_id: UUID
    source_investigation_id: str | None = Field(default=None, min_length=1, max_length=256)
    organization_id: UUID
    case_id: UUID | None = None
    alert_id: UUID | None = None
    investigation_sequence: int | None = Field(default=None, ge=1)
    started_at_utc: datetime
    ended_at_utc: datetime | None = None
    recorded_at_utc: datetime | None = None
    investigation_status: Literal[
        "NOT_STARTED", "IN_PROGRESS", "COMPLETED", "BLOCKED", "CANCELLED", "UNKNOWN"
    ]
    analyst_role_code: str | None = Field(default=None, max_length=128)
    analyst_pseudonym: str | None = Field(default=None, max_length=128)
    method_code: str | None = Field(default=None, max_length=128)
    runbook_id: str | None = Field(default=None, max_length=128)
    template_id: str | None = Field(default=None, max_length=128)
    automation_state: Literal["MANUAL", "AUTOMATED", "MIXED", "UNKNOWN"] | None = None
    investigation_notes: str | None = None
    conclusion_code: str | None = Field(default=None, max_length=128)
    disposition: (
        Literal[
            "TRUE_POSITIVE",
            "FALSE_POSITIVE",
            "BENIGN",
            "DUPLICATE",
            "SUPPRESSED",
            "ACCEPTED_RISK",
            "NO_ACTION_REQUIRED",
            "CONFIRMED_INCIDENT",
            "OTHER",
            "UNKNOWN",
        ]
        | None
    ) = None
    evidence_reference_text: str | None = None
    workflow_version: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def validate_subject_and_temporal(self) -> InvestigationRecord:
        if self.case_id is None and self.alert_id is None:
            raise ValueError("investigation must reference at least one of case_id or alert_id")
        if self.ended_at_utc and self.ended_at_utc < self.started_at_utc:
            raise ValueError("ended_at_utc cannot precede started_at_utc")
        return self


class EscalationRecord(FixtureRecord):
    escalation_id: UUID
    source_escalation_id: str | None = Field(default=None, min_length=1, max_length=256)
    organization_id: UUID
    case_id: UUID | None = None
    alert_id: UUID | None = None
    escalated_at_utc: datetime
    escalation_type: Literal[
        "TECHNICAL",
        "MANAGEMENT",
        "INCIDENT_RESPONSE",
        "BUSINESS_OWNER",
        "VENDOR",
        "EXTERNAL_AUTHORITY",
        "OTHER",
        "UNKNOWN",
    ]
    source_role_code: str | None = Field(default=None, max_length=128)
    target_role_code: str = Field(min_length=1, max_length=128)
    escalation_level: str | None = Field(default=None, max_length=64)
    escalation_reason: str | None = None
    escalation_status: Literal[
        "INITIATED",
        "ACKNOWLEDGED",
        "ACCEPTED",
        "REJECTED",
        "CANCELLED",
        "RESOLVED",
        "UNKNOWN",
    ]
    acknowledged_at_utc: datetime | None = None
    resolved_at_utc: datetime | None = None
    resolution_summary: str | None = None
    policy_trigger_code: str | None = Field(default=None, max_length=128)
    workflow_version: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def validate_subject_and_temporal(self) -> EscalationRecord:
        if self.case_id is None and self.alert_id is None:
            raise ValueError("escalation must reference at least one of case_id or alert_id")
        if self.acknowledged_at_utc and self.acknowledged_at_utc < self.escalated_at_utc:
            raise ValueError("acknowledged_at_utc cannot precede escalated_at_utc")
        if self.resolved_at_utc and self.resolved_at_utc < self.escalated_at_utc:
            raise ValueError("resolved_at_utc cannot precede escalated_at_utc")
        return self


class ActionRecord(FixtureRecord):
    action_id: UUID
    source_action_id: str | None = Field(default=None, min_length=1, max_length=256)
    organization_id: UUID
    asset_id: UUID | None = None
    alert_id: UUID | None = None
    case_id: UUID | None = None
    action_type: Literal[
        "INVESTIGATE",
        "CONTAIN",
        "ERADICATE",
        "RECOVER",
        "PATCH",
        "TUNE_RULE",
        "SUPPRESS",
        "ACCEPT_RISK",
        "MONITOR",
        "OTHER",
        "UNKNOWN",
    ]
    created_at_utc: datetime
    due_at_utc: datetime | None = None
    started_at_utc: datetime | None = None
    completed_at_utc: datetime | None = None
    action_status: Literal[
        "PLANNED",
        "OPEN",
        "IN_PROGRESS",
        "COMPLETED",
        "VERIFIED",
        "DEFERRED",
        "CANCELLED",
        "FAILED",
        "UNKNOWN",
    ]
    owner_role_code: str | None = Field(default=None, max_length=128)
    remediation_reference: str | None = Field(default=None, max_length=256)
    action_summary: str | None = None
    verification_state: (
        Literal[
            "NOT_VERIFIED",
            "VERIFIED",
            "FAILED_VERIFICATION",
            "NOT_APPLICABLE",
            "UNKNOWN",
        ]
        | None
    ) = None
    exception_id: UUID | None = None
    workflow_version: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def validate_subject_and_temporal(self) -> ActionRecord:
        if self.asset_id is None and self.alert_id is None and self.case_id is None:
            raise ValueError("action must reference at least one of asset_id, alert_id, or case_id")
        if self.started_at_utc and self.started_at_utc < self.created_at_utc:
            raise ValueError("started_at_utc cannot precede created_at_utc")
        if self.completed_at_utc and self.completed_at_utc < self.created_at_utc:
            raise ValueError("completed_at_utc cannot precede created_at_utc")
        return self


class ResolutionRecord(FixtureRecord):
    resolution_id: UUID
    source_resolution_id: str | None = Field(default=None, min_length=1, max_length=256)
    organization_id: UUID
    case_id: UUID | None = None
    alert_id: UUID | None = None
    resolved_at_utc: datetime
    resolution_type: Literal[
        "MITIGATED",
        "REMEDIATED",
        "CONTAINED",
        "FALSE_POSITIVE",
        "DUPLICATE",
        "SUPPRESSED",
        "ACCEPTED_RISK",
        "NO_ACTION_REQUIRED",
        "OTHER",
        "UNKNOWN",
    ]
    resolution_status: Literal[
        "PROPOSED", "APPROVED", "IMPLEMENTED", "VERIFIED", "REJECTED", "UNKNOWN"
    ]
    resolution_reason: str | None = None
    approved_by_role_code: str | None = Field(default=None, max_length=128)
    verification_reference: str | None = Field(default=None, max_length=256)
    exception_id: UUID | None = None
    workflow_version: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def validate_subject(self) -> ResolutionRecord:
        if self.case_id is None and self.alert_id is None:
            raise ValueError("resolution must reference at least one of case_id or alert_id")
        return self


class ClosureRecord(FixtureRecord):
    closure_id: UUID
    source_closure_id: str | None = Field(default=None, min_length=1, max_length=256)
    organization_id: UUID
    case_id: UUID | None = None
    alert_id: UUID | None = None
    resolution_id: UUID | None = None
    closed_at_utc: datetime
    closure_status: Literal["CLOSED", "REOPENED", "VOIDED", "UNKNOWN"]
    disposition: Literal[
        "TRUE_POSITIVE",
        "FALSE_POSITIVE",
        "BENIGN",
        "DUPLICATE",
        "SUPPRESSED",
        "ACCEPTED_RISK",
        "NO_ACTION_REQUIRED",
        "CONFIRMED_INCIDENT",
        "OTHER",
        "UNKNOWN",
    ]
    closure_reason: str | None = None
    closed_by_role_code: str | None = Field(default=None, max_length=128)
    approval_state: Literal["NOT_REQUIRED", "PENDING", "APPROVED", "REJECTED", "UNKNOWN"] | None = (
        None
    )
    approved_at_utc: datetime | None = None
    exception_id: UUID | None = None
    workflow_version: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def validate_subject(self) -> ClosureRecord:
        if self.case_id is None and self.alert_id is None:
            raise ValueError("closure must reference at least one of case_id or alert_id")
        return self


class ExceptionRecord(FixtureRecord):
    exception_id: UUID
    source_exception_id: str | None = Field(default=None, min_length=1, max_length=256)
    organization_id: UUID
    exception_type: Literal[
        "APPROVED_AUTOMATION",
        "APPROVED_SUPPRESSION",
        "MAINTENANCE_WINDOW",
        "KNOWN_EXCEPTION",
        "NOT_APPLICABLE",
        "EMERGENCY_PROCESS",
        "POLICY_CHANGE",
        "WORKFLOW_CHANGE",
        "NEW_TOOLING",
        "MIGRATION_PERIOD",
        "ACCEPTED_RISK",
        "TEMPORARY_DECOMMISSIONING",
        "OTHER",
        "UNKNOWN",
    ]
    target_type: Literal[
        "ORGANIZATION",
        "ASSET",
        "ALERT",
        "CASE",
        "INVESTIGATION",
        "ESCALATION",
        "ACTION",
        "CONTROL",
        "PROCESS",
        "RULE",
        "PERIOD",
    ]
    target_id: UUID | None = None
    rule_expectation_id: UUID | None = None
    applicability_state: Literal["APPLIES", "DOES_NOT_APPLY", "PARTIALLY_APPLIES", "UNKNOWN"]
    approved_state: Literal["APPROVED", "PENDING", "REJECTED", "EXPIRED", "UNKNOWN"]
    approved_by_role_code: str | None = Field(default=None, max_length=128)
    reason: str = Field(min_length=1)
    effective_start_at_utc: datetime
    effective_end_at_utc: datetime | None = None
    created_at_utc: datetime
    evidence_reference: str | None = Field(default=None, max_length=256)
    scope_definition: dict[str, Any] | None = None
    exception_quality_state: Literal["VALID", "WARNING", "INVALID", "INCOMPLETE", "UNKNOWN"]

    @model_validator(mode="after")
    def validate_interval(self) -> ExceptionRecord:
        if (
            self.effective_end_at_utc is not None
            and self.effective_end_at_utc <= self.effective_start_at_utc
        ):
            raise ValueError("effective_end_at_utc must be after effective_start_at_utc")
        return self


class ProcessChangeRecord(FixtureRecord):
    process_change_id: UUID
    organization_id: UUID
    change_type: Literal[
        "POLICY",
        "WORKFLOW",
        "TOOLING",
        "MAPPING",
        "AUTOMATION",
        "MERGER",
        "ASSET_SCOPE",
        "OTHER",
    ]
    effective_at_utc: datetime
    end_at_utc: datetime | None = None
    previous_version: str | None = Field(default=None, max_length=64)
    new_version: str | None = Field(default=None, max_length=64)
    affected_families: list[str] = Field(min_length=1)
    change_summary: str = Field(min_length=1)
    approved_state: Literal["APPROVED", "PENDING", "REJECTED", "EXPIRED", "UNKNOWN"]
    exception_id: UUID | None = None

    @model_validator(mode="after")
    def validate_interval(self) -> ProcessChangeRecord:
        if self.end_at_utc is not None and self.end_at_utc <= self.effective_at_utc:
            raise ValueError("end_at_utc must be after effective_at_utc")
        return self
