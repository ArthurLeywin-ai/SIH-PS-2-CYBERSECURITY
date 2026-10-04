"""Catalog of M3 Source Profiles."""

from __future__ import annotations

from satsa_generator.profiles.models import FieldMapping, ProfileDefinition
from satsa_generator.profiles.vocabulary import (
    CATEGORY_SRC_D,
    CATEGORY_SRC_E,
    CRITICALITY_BAND_SRC_B,
    CRITICALITY_BAND_SRC_C,
    CRITICALITY_BAND_SRC_D,
    CRITICALITY_BAND_SRC_E,
    DISPOSITION_SRC_D,
    DISPOSITION_SRC_E,
    MATURITY_SRC_B,
    MATURITY_SRC_C,
    MATURITY_SRC_D,
    MATURITY_SRC_E,
    SEVERITY_SRC_B,
    SEVERITY_SRC_C,
    SEVERITY_SRC_D,
    SEVERITY_SRC_E,
    STATUS_SRC_B,
    STATUS_SRC_C,
    STATUS_SRC_D,
    STATUS_SRC_E,
)


def get_src_a() -> ProfileDefinition:
    return ProfileDefinition(
        profile_id="SRC-A",
        format="CSV",
        timestamp_format="iso_z",
        family_mappings={
            "organization": {
                "organization_id": FieldMapping(source_name="organization_id", is_native_id=True),
                "source_organization_id": FieldMapping(source_name="source_organization_id"),
                "organization_name": FieldMapping(source_name="organization_name"),
                "entity_criticality_band": FieldMapping(source_name="entity_criticality_band"),
                "organization_status": FieldMapping(source_name="organization_status"),
                "profile_effective_start_at_utc": FieldMapping(
                    source_name="profile_effective_start_at_utc"
                ),
            },
            "submission": {
                "submission_id": FieldMapping(source_name="submission_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="organization_id"),
                "period_maturity_state": FieldMapping(source_name="period_maturity_state"),
                "reporting_period_start_at_utc": FieldMapping(
                    source_name="reporting_period_start_at_utc"
                ),
            },
            "submission_manifest": {
                "manifest_id": FieldMapping(source_name="manifest_id", is_native_id=True),
                "submission_id": FieldMapping(source_name="submission_id"),
                "created_at_utc": FieldMapping(source_name="created_at_utc"),
            },
            "submission_family": {
                "submission_family_id": FieldMapping(
                    source_name="submission_family_id", is_native_id=True
                ),
                "submission_id": FieldMapping(source_name="submission_id"),
                "evidence_family": FieldMapping(source_name="evidence_family"),
                "presence_state": FieldMapping(source_name="presence_state"),
            },
            "control_process_reference": {
                "control_process_ref_id": FieldMapping(source_name="control_process_ref_id"),
                "organization_id": FieldMapping(source_name="organization_id"),
                "reference_type": FieldMapping(source_name="reference_type"),
                "reference_code": FieldMapping(source_name="reference_code"),
                "display_name": FieldMapping(source_name="display_name"),
            },
            "control_process_subject_link": {
                "control_process_link_id": FieldMapping(source_name="control_process_link_id"),
                "control_process_ref_id": FieldMapping(source_name="control_process_ref_id"),
                "subject_type": FieldMapping(source_name="subject_type"),
            },
            "asset": {
                "asset_id": FieldMapping(source_name="asset_id", is_native_id=True),
                "source_asset_id": FieldMapping(source_name="source_asset_id"),
                "organization_id": FieldMapping(source_name="organization_id"),
                "asset_class": FieldMapping(source_name="asset_class"),
            },
            "monitoring_coverage": {
                "monitoring_coverage_id": FieldMapping(
                    source_name="monitoring_coverage_id", is_native_id=True
                ),
                "organization_id": FieldMapping(source_name="organization_id"),
                "asset_id": FieldMapping(source_name="asset_id"),
                "monitoring_type": FieldMapping(source_name="monitoring_type"),
            },
            "alert": {
                "alert_id": FieldMapping(source_name="alert_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="organization_id"),
                "asset_id": FieldMapping(source_name="asset_id"),
                "created_at_utc": FieldMapping(source_name="created_at_utc"),
                "alert_category": FieldMapping(source_name="alert_category"),
                "severity": FieldMapping(source_name="severity"),
                "disposition": FieldMapping(source_name="disposition"),
            },
            "case": {
                "case_id": FieldMapping(source_name="case_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="organization_id"),
                "case_type": FieldMapping(source_name="case_type"),
                "severity": FieldMapping(source_name="severity"),
                "created_at_utc": FieldMapping(source_name="created_at_utc"),
                "alerts": FieldMapping(source_name="alerts", is_present=False),
            },
            "case_alert_link": {
                "case_alert_link_id": FieldMapping(
                    source_name="case_alert_link_id", is_native_id=True
                ),
                "case_id": FieldMapping(source_name="case_id"),
                "alert_id": FieldMapping(source_name="alert_id"),
                "link_type": FieldMapping(source_name="link_type"),
            },
            "investigation": {
                "investigation_id": FieldMapping(source_name="investigation_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="organization_id"),
                "case_id": FieldMapping(source_name="case_id"),
                "alert_id": FieldMapping(source_name="alert_id"),
                "started_at_utc": FieldMapping(source_name="started_at_utc"),
                "disposition": FieldMapping(source_name="disposition"),
            },
            "escalation": {
                "escalation_id": FieldMapping(source_name="escalation_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="organization_id"),
                "case_id": FieldMapping(source_name="case_id"),
                "alert_id": FieldMapping(source_name="alert_id"),
                "escalated_at_utc": FieldMapping(source_name="escalated_at_utc"),
            },
            "action": {
                "action_id": FieldMapping(source_name="action_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="organization_id"),
                "asset_id": FieldMapping(source_name="asset_id"),
                "alert_id": FieldMapping(source_name="alert_id"),
                "case_id": FieldMapping(source_name="case_id"),
                "action_type": FieldMapping(source_name="action_type"),
            },
            "resolution": {
                "resolution_id": FieldMapping(source_name="resolution_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="organization_id"),
                "case_id": FieldMapping(source_name="case_id"),
                "alert_id": FieldMapping(source_name="alert_id"),
                "resolved_at_utc": FieldMapping(source_name="resolved_at_utc"),
            },
            "closure": {
                "closure_id": FieldMapping(source_name="closure_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="organization_id"),
                "case_id": FieldMapping(source_name="case_id"),
                "alert_id": FieldMapping(source_name="alert_id"),
                "resolution_id": FieldMapping(source_name="resolution_id"),
                "closed_at_utc": FieldMapping(source_name="closed_at_utc"),
            },
            "exception": {
                "exception_id": FieldMapping(source_name="exception_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="organization_id"),
                "exception_type": FieldMapping(source_name="exception_type"),
            },
            "process_change": {
                "process_change_id": FieldMapping(
                    source_name="process_change_id", is_native_id=True
                ),
                "organization_id": FieldMapping(source_name="organization_id"),
                "change_type": FieldMapping(source_name="change_type"),
            },
        },
    )


def get_src_b() -> ProfileDefinition:
    return ProfileDefinition(
        profile_id="SRC-B",
        format="CSV",
        timestamp_format="local_iana",
        case_naming="pascal_case",
        timezone="America/New_York",
        family_mappings={
            "organization": {
                "organization_id": FieldMapping(source_name="OrganizationId", is_native_id=True),
                "source_organization_id": FieldMapping(
                    source_name="SourceOrganizationId", is_present=False
                ),
                "organization_name": FieldMapping(source_name="OrganizationName"),
                "entity_criticality_band": FieldMapping(
                    source_name="EntityCriticalityBand", vocabulary=CRITICALITY_BAND_SRC_B
                ),
                "organization_status": FieldMapping(
                    source_name="OrganizationStatus", vocabulary=STATUS_SRC_B
                ),
                "profile_effective_start_at_utc": FieldMapping(
                    source_name="ProfileEffectiveStartAtUtc"
                ),
            },
            "submission": {
                "submission_id": FieldMapping(source_name="SubmissionId", is_native_id=True),
                "organization_id": FieldMapping(source_name="OrganizationId"),
                "period_maturity_state": FieldMapping(
                    source_name="PeriodMaturityState", vocabulary=MATURITY_SRC_B
                ),
                "reporting_period_start_at_utc": FieldMapping(
                    source_name="ReportingPeriodStartAtUtc"
                ),
            },
            "submission_manifest": {
                "manifest_id": FieldMapping(source_name="ManifestId", is_native_id=True),
                "submission_id": FieldMapping(source_name="SubmissionId"),
                "created_at_utc": FieldMapping(source_name="CreatedAtUtc"),
            },
            "submission_family": {
                "submission_family_id": FieldMapping(
                    source_name="SubmissionFamilyId", is_native_id=True
                ),
                "submission_id": FieldMapping(source_name="SubmissionId"),
                "evidence_family": FieldMapping(source_name="EvidenceFamily"),
                "presence_state": FieldMapping(source_name="PresenceState"),
            },
            "control_process_reference": {
                "control_process_ref_id": FieldMapping(source_name="ControlProcessRefId"),
                "organization_id": FieldMapping(source_name="OrganizationId"),
                "reference_type": FieldMapping(source_name="ReferenceType"),
                "reference_code": FieldMapping(source_name="ReferenceCode"),
                "display_name": FieldMapping(source_name="DisplayName"),
            },
            "control_process_subject_link": {
                "control_process_link_id": FieldMapping(source_name="ControlProcessLinkId"),
                "control_process_ref_id": FieldMapping(source_name="ControlProcessRefId"),
                "subject_type": FieldMapping(source_name="SubjectType"),
            },
            "asset": {
                "asset_id": FieldMapping(source_name="AssetId", is_native_id=True),
                "source_asset_id": FieldMapping(source_name="SourceAssetId"),
                "organization_id": FieldMapping(source_name="OrganizationId"),
                "asset_class": FieldMapping(source_name="AssetClass"),
            },
            "monitoring_coverage": {
                "monitoring_coverage_id": FieldMapping(
                    source_name="MonitoringCoverageId", is_native_id=True
                ),
                "organization_id": FieldMapping(source_name="OrganizationId"),
                "asset_id": FieldMapping(source_name="AssetId"),
                "monitoring_type": FieldMapping(source_name="MonitoringType"),
            },
            "alert": {
                "alert_id": FieldMapping(source_name="AlertId", is_native_id=True),
                "organization_id": FieldMapping(source_name="OrganizationId"),
                "asset_id": FieldMapping(source_name="AssetId"),
                "created_at_utc": FieldMapping(source_name="CreatedAtUtc"),
                "alert_category": FieldMapping(source_name="AlertCategory"),
                "severity": FieldMapping(source_name="Severity", vocabulary=SEVERITY_SRC_B),
                "disposition": FieldMapping(source_name="Disposition"),
            },
            "case": {
                "case_id": FieldMapping(source_name="CaseId", is_native_id=True),
                "organization_id": FieldMapping(source_name="OrganizationId"),
                "case_type": FieldMapping(source_name="CaseType"),
                "severity": FieldMapping(source_name="Severity", vocabulary=SEVERITY_SRC_B),
                "created_at_utc": FieldMapping(source_name="CreatedAtUtc"),
                "alerts": FieldMapping(source_name="Alerts", is_present=False),
            },
            "case_alert_link": {
                "case_alert_link_id": FieldMapping(
                    source_name="CaseAlertLinkId", is_native_id=True
                ),
                "case_id": FieldMapping(source_name="CaseId"),
                "alert_id": FieldMapping(source_name="AlertId"),
                "link_type": FieldMapping(source_name="LinkType"),
            },
            "investigation": {
                "investigation_id": FieldMapping(source_name="InvestigationId", is_native_id=True),
                "organization_id": FieldMapping(source_name="OrganizationId"),
                "case_id": FieldMapping(source_name="CaseId"),
                "alert_id": FieldMapping(source_name="AlertId"),
                "started_at_utc": FieldMapping(source_name="StartedAtUtc"),
                "disposition": FieldMapping(source_name="Disposition"),
            },
            "escalation": {
                "escalation_id": FieldMapping(source_name="EscalationId", is_native_id=True),
                "organization_id": FieldMapping(source_name="OrganizationId"),
                "case_id": FieldMapping(source_name="CaseId"),
                "alert_id": FieldMapping(source_name="AlertId"),
                "escalated_at_utc": FieldMapping(source_name="EscalatedAtUtc"),
            },
            "action": {
                "action_id": FieldMapping(source_name="ActionId", is_native_id=True),
                "organization_id": FieldMapping(source_name="OrganizationId"),
                "asset_id": FieldMapping(source_name="AssetId"),
                "alert_id": FieldMapping(source_name="AlertId"),
                "case_id": FieldMapping(source_name="CaseId"),
                "action_type": FieldMapping(source_name="ActionType"),
            },
            "resolution": {
                "resolution_id": FieldMapping(source_name="ResolutionId", is_native_id=True),
                "organization_id": FieldMapping(source_name="OrganizationId"),
                "case_id": FieldMapping(source_name="CaseId"),
                "alert_id": FieldMapping(source_name="AlertId"),
                "resolved_at_utc": FieldMapping(source_name="ResolvedAtUtc"),
            },
            "closure": {
                "closure_id": FieldMapping(source_name="ClosureId", is_native_id=True),
                "organization_id": FieldMapping(source_name="OrganizationId"),
                "case_id": FieldMapping(source_name="CaseId"),
                "alert_id": FieldMapping(source_name="AlertId"),
                "resolution_id": FieldMapping(source_name="ResolutionId"),
                "closed_at_utc": FieldMapping(source_name="ClosedAtUtc"),
            },
            "exception": {
                "exception_id": FieldMapping(source_name="ExceptionId", is_native_id=True),
                "organization_id": FieldMapping(source_name="OrganizationId"),
                "exception_type": FieldMapping(source_name="ExceptionType"),
            },
            "process_change": {
                "process_change_id": FieldMapping(source_name="ProcessChangeId", is_native_id=True),
                "organization_id": FieldMapping(source_name="OrganizationId"),
                "change_type": FieldMapping(source_name="ChangeType"),
            },
        },
    )


def get_src_c() -> ProfileDefinition:
    return ProfileDefinition(
        profile_id="SRC-C",
        format="JSON",
        timestamp_format="iso_offset_ms",
        case_naming="camel_case",
        relationships_nested=True,
        family_mappings={
            "organization": {
                "organization_id": FieldMapping(source_name="organizationId", is_native_id=True),
                "source_organization_id": FieldMapping(source_name="sourceOrganizationId"),
                "organization_name": FieldMapping(
                    source_name="organizationName", path=["details", "organizationName"]
                ),
                "entity_criticality_band": FieldMapping(
                    source_name="entityCriticalityBand",
                    path=["details", "entityCriticalityBand"],
                    vocabulary=CRITICALITY_BAND_SRC_C,
                ),
                "organization_status": FieldMapping(
                    source_name="organizationStatus",
                    path=["details", "organizationStatus"],
                    vocabulary=STATUS_SRC_C,
                ),
                "profile_effective_start_at_utc": FieldMapping(
                    source_name="profileEffectiveStartAtUtc",
                    path=["details", "profileEffectiveStartAtUtc"],
                ),
            },
            "submission": {
                "submission_id": FieldMapping(source_name="submissionId", is_native_id=True),
                "organization_id": FieldMapping(source_name="organizationId"),
                "period_maturity_state": FieldMapping(
                    source_name="periodMaturityState",
                    path=["details", "periodMaturityState"],
                    vocabulary=MATURITY_SRC_C,
                ),
                "reporting_period_start_at_utc": FieldMapping(
                    source_name="reportingPeriodStartAtUtc",
                    path=["details", "reportingPeriodStartAtUtc"],
                ),
            },
            "submission_manifest": {
                "manifest_id": FieldMapping(source_name="manifestId", is_native_id=True),
                "submission_id": FieldMapping(source_name="submissionId"),
                "created_at_utc": FieldMapping(
                    source_name="createdAtUtc", path=["details", "createdAtUtc"]
                ),
            },
            "submission_family": {
                "submission_family_id": FieldMapping(
                    source_name="submissionFamilyId", is_native_id=True
                ),
                "submission_id": FieldMapping(source_name="submissionId"),
                "evidence_family": FieldMapping(source_name="evidenceFamily"),
                "presence_state": FieldMapping(
                    source_name="presenceState", path=["details", "presenceState"]
                ),
            },
            "control_process_reference": {
                "control_process_ref_id": FieldMapping(source_name="controlProcessRefId"),
                "organization_id": FieldMapping(source_name="organizationId"),
                "reference_type": FieldMapping(
                    source_name="referenceType", path=["details", "referenceType"]
                ),
                "reference_code": FieldMapping(
                    source_name="referenceCode", path=["details", "referenceCode"]
                ),
                "display_name": FieldMapping(
                    source_name="displayName", path=["details", "displayName"]
                ),
            },
            "control_process_subject_link": {
                "control_process_link_id": FieldMapping(source_name="controlProcessLinkId"),
                "control_process_ref_id": FieldMapping(source_name="controlProcessRefId"),
                "subject_type": FieldMapping(
                    source_name="subjectType", path=["details", "subjectType"]
                ),
            },
            "asset": {
                "asset_id": FieldMapping(source_name="assetId", is_native_id=True),
                "source_asset_id": FieldMapping(source_name="sourceAssetId"),
                "organization_id": FieldMapping(source_name="organizationId"),
                "asset_class": FieldMapping(
                    source_name="assetClass", path=["details", "assetClass"]
                ),
            },
            "monitoring_coverage": {
                "monitoring_coverage_id": FieldMapping(
                    source_name="monitoringCoverageId", is_native_id=True
                ),
                "organization_id": FieldMapping(source_name="organizationId"),
                "asset_id": FieldMapping(source_name="assetId"),
                "monitoring_type": FieldMapping(
                    source_name="monitoringType", path=["details", "monitoringType"]
                ),
            },
            "alert": {
                "alert_id": FieldMapping(source_name="alertId", is_native_id=True),
                "organization_id": FieldMapping(source_name="organizationId"),
                "asset_id": FieldMapping(source_name="assetId"),
                "created_at_utc": FieldMapping(
                    source_name="createdAtUtc", path=["details", "createdAtUtc"]
                ),
                "alert_category": FieldMapping(
                    source_name="alertCategory", path=["details", "alertCategory"]
                ),
                "severity": FieldMapping(
                    source_name="severity", path=["details", "severity"], vocabulary=SEVERITY_SRC_C
                ),
                "disposition": FieldMapping(
                    source_name="disposition", path=["details", "disposition"]
                ),
            },
            "case": {
                "case_id": FieldMapping(source_name="caseId", is_native_id=True),
                "organization_id": FieldMapping(source_name="organizationId"),
                "case_type": FieldMapping(source_name="caseType", path=["details", "caseType"]),
                "severity": FieldMapping(
                    source_name="severity", path=["details", "severity"], vocabulary=SEVERITY_SRC_C
                ),
                "created_at_utc": FieldMapping(
                    source_name="createdAtUtc", path=["details", "createdAtUtc"]
                ),
                "alerts": FieldMapping(source_name="alerts", path=["details", "alerts"]),
            },
            "case_alert_link": {
                "case_alert_link_id": FieldMapping(
                    source_name="caseAlertLinkId", is_native_id=True
                ),
                "case_id": FieldMapping(source_name="caseId"),
                "alert_id": FieldMapping(source_name="alertId"),
                "link_type": FieldMapping(source_name="linkType", path=["details", "linkType"]),
            },
            "investigation": {
                "investigation_id": FieldMapping(source_name="investigationId", is_native_id=True),
                "organization_id": FieldMapping(source_name="organizationId"),
                "case_id": FieldMapping(source_name="caseId"),
                "alert_id": FieldMapping(source_name="alertId"),
                "started_at_utc": FieldMapping(
                    source_name="startedAtUtc", path=["details", "startedAtUtc"]
                ),
                "disposition": FieldMapping(
                    source_name="disposition", path=["details", "disposition"]
                ),
            },
            "escalation": {
                "escalation_id": FieldMapping(source_name="escalationId", is_native_id=True),
                "organization_id": FieldMapping(source_name="organizationId"),
                "case_id": FieldMapping(source_name="caseId"),
                "alert_id": FieldMapping(source_name="alertId"),
                "escalated_at_utc": FieldMapping(
                    source_name="escalatedAtUtc", path=["details", "escalatedAtUtc"]
                ),
            },
            "action": {
                "action_id": FieldMapping(source_name="actionId", is_native_id=True),
                "organization_id": FieldMapping(source_name="organizationId"),
                "asset_id": FieldMapping(source_name="assetId"),
                "alert_id": FieldMapping(source_name="alertId"),
                "case_id": FieldMapping(source_name="caseId"),
                "action_type": FieldMapping(
                    source_name="actionType", path=["details", "actionType"]
                ),
            },
            "resolution": {
                "resolution_id": FieldMapping(source_name="resolutionId", is_native_id=True),
                "organization_id": FieldMapping(source_name="organizationId"),
                "case_id": FieldMapping(source_name="caseId"),
                "alert_id": FieldMapping(source_name="alertId"),
                "resolved_at_utc": FieldMapping(
                    source_name="resolvedAtUtc", path=["details", "resolvedAtUtc"]
                ),
            },
            "closure": {
                "closure_id": FieldMapping(source_name="closureId", is_native_id=True),
                "organization_id": FieldMapping(source_name="organizationId"),
                "case_id": FieldMapping(source_name="caseId"),
                "alert_id": FieldMapping(source_name="alertId"),
                "resolution_id": FieldMapping(source_name="resolutionId"),
                "closed_at_utc": FieldMapping(
                    source_name="closedAtUtc", path=["details", "closedAtUtc"]
                ),
            },
            "exception": {
                "exception_id": FieldMapping(source_name="exceptionId", is_native_id=True),
                "organization_id": FieldMapping(source_name="organizationId"),
                "exception_type": FieldMapping(
                    source_name="exceptionType", path=["details", "exceptionType"]
                ),
            },
            "process_change": {
                "process_change_id": FieldMapping(source_name="processChangeId", is_native_id=True),
                "organization_id": FieldMapping(source_name="organizationId"),
                "change_type": FieldMapping(
                    source_name="changeType", path=["details", "changeType"]
                ),
            },
        },
    )


def get_src_d() -> ProfileDefinition:
    return ProfileDefinition(
        profile_id="SRC-D",
        format="JSONL",
        timestamp_format="date_only",
        case_naming="mixed",
        per_family_timestamp_format={
            "alert": "iso_offset",
            "case": "iso_offset",
            "case_alert_link": "iso_offset",
            "investigation": "iso_offset",
            "escalation": "iso_offset",
            "action": "iso_offset",
            "resolution": "iso_offset",
            "closure": "iso_offset",
            "exception": "iso_offset",
            "process_change": "iso_offset",
            "organization": "date_only",
            "submission": "date_only",
            "submission_manifest": "date_only",
            "submission_family": "date_only",
            "control_process_reference": "date_only",
            "control_process_subject_link": "date_only",
            "asset": "date_only",
            "monitoring_coverage": "date_only",
        },
        family_mappings={
            "organization": {
                "organization_id": FieldMapping(source_name="org_id", is_native_id=True),
                "source_organization_id": FieldMapping(source_name="sou_org_id", is_present=False),
                "organization_name": FieldMapping(source_name="org_name"),
                "entity_criticality_band": FieldMapping(
                    source_name="ent_cri_band", vocabulary=CRITICALITY_BAND_SRC_D
                ),
                "organization_status": FieldMapping(
                    source_name="org_status", vocabulary=STATUS_SRC_D
                ),
                "profile_effective_start_at_utc": FieldMapping(source_name="pro_eff_utc"),
            },
            "submission": {
                "submission_id": FieldMapping(source_name="sub_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="org_id"),
                "period_maturity_state": FieldMapping(
                    source_name="per_mat_state", vocabulary=MATURITY_SRC_D
                ),
                "reporting_period_start_at_utc": FieldMapping(source_name="rep_per_utc"),
            },
            "submission_manifest": {
                "manifest_id": FieldMapping(source_name="man_id", is_native_id=True),
                "submission_id": FieldMapping(source_name="sub_id"),
                "created_at_utc": FieldMapping(source_name="cre_at_utc"),
            },
            "submission_family": {
                "submission_family_id": FieldMapping(source_name="sub_fam_id", is_native_id=True),
                "submission_id": FieldMapping(source_name="sub_id"),
                "evidence_family": FieldMapping(source_name="evi_family"),
                "presence_state": FieldMapping(source_name="pre_state"),
            },
            "control_process_reference": {
                "control_process_ref_id": FieldMapping(source_name="con_pro_id"),
                "organization_id": FieldMapping(source_name="org_id"),
                "reference_type": FieldMapping(source_name="ref_type"),
                "reference_code": FieldMapping(source_name="ref_code"),
                "display_name": FieldMapping(source_name="dis_name"),
            },
            "control_process_subject_link": {
                "control_process_link_id": FieldMapping(source_name="con_pro_link_id"),
                "control_process_ref_id": FieldMapping(source_name="con_pro_id"),
                "subject_type": FieldMapping(source_name="sub_type"),
            },
            "asset": {
                "asset_id": FieldMapping(source_name="ass_id", is_native_id=True),
                "source_asset_id": FieldMapping(source_name="sou_ass_id"),
                "organization_id": FieldMapping(source_name="org_id"),
                "asset_class": FieldMapping(source_name="ass_class"),
            },
            "monitoring_coverage": {
                "monitoring_coverage_id": FieldMapping(source_name="mon_cov_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="org_id"),
                "asset_id": FieldMapping(source_name="ass_id"),
                "monitoring_type": FieldMapping(source_name="mon_type"),
            },
            "alert": {
                "alert_id": FieldMapping(source_name="ale_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="org_id"),
                "asset_id": FieldMapping(source_name="ass_id"),
                "created_at_utc": FieldMapping(source_name="cre_at_utc"),
                "alert_category": FieldMapping(source_name="ale_cat", vocabulary=CATEGORY_SRC_D),
                "severity": FieldMapping(source_name="ale_sev", vocabulary=SEVERITY_SRC_D),
                "disposition": FieldMapping(source_name="ale_disp", vocabulary=DISPOSITION_SRC_D),
            },
            "case": {
                "case_id": FieldMapping(source_name="cas_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="org_id"),
                "case_type": FieldMapping(source_name="cas_type"),
                "severity": FieldMapping(source_name="cas_sev", vocabulary=SEVERITY_SRC_D),
                "created_at_utc": FieldMapping(source_name="cre_at_utc"),
                "alerts": FieldMapping(source_name="alerts", is_reference_array=True),
            },
            "case_alert_link": {
                "case_alert_link_id": FieldMapping(source_name="cas_ale_id", is_native_id=True),
                "case_id": FieldMapping(source_name="cas_id"),
                "alert_id": FieldMapping(source_name="ale_id"),
                "link_type": FieldMapping(source_name="lin_type"),
            },
            "investigation": {
                "investigation_id": FieldMapping(source_name="inv_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="org_id"),
                "case_id": FieldMapping(source_name="cas_id"),
                "alert_id": FieldMapping(source_name="ale_id"),
                "started_at_utc": FieldMapping(source_name="sta_at_utc"),
                "disposition": FieldMapping(source_name="inv_disp", vocabulary=DISPOSITION_SRC_D),
            },
            "escalation": {
                "escalation_id": FieldMapping(source_name="esc_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="org_id"),
                "case_id": FieldMapping(source_name="cas_id"),
                "alert_id": FieldMapping(source_name="ale_id"),
                "escalated_at_utc": FieldMapping(source_name="esc_at_utc"),
            },
            "action": {
                "action_id": FieldMapping(source_name="act_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="org_id"),
                "asset_id": FieldMapping(source_name="ass_id"),
                "alert_id": FieldMapping(source_name="ale_id"),
                "case_id": FieldMapping(source_name="cas_id"),
                "action_type": FieldMapping(source_name="act_type"),
            },
            "resolution": {
                "resolution_id": FieldMapping(source_name="res_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="org_id"),
                "case_id": FieldMapping(source_name="cas_id"),
                "alert_id": FieldMapping(source_name="ale_id"),
                "resolved_at_utc": FieldMapping(source_name="res_at_utc"),
            },
            "closure": {
                "closure_id": FieldMapping(source_name="clo_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="org_id"),
                "case_id": FieldMapping(source_name="cas_id"),
                "alert_id": FieldMapping(source_name="ale_id"),
                "resolution_id": FieldMapping(source_name="res_id"),
                "closed_at_utc": FieldMapping(source_name="clo_at_utc"),
            },
            "exception": {
                "exception_id": FieldMapping(source_name="exc_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="org_id"),
                "exception_type": FieldMapping(source_name="exc_type"),
            },
            "process_change": {
                "process_change_id": FieldMapping(source_name="pro_cha_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="org_id"),
                "change_type": FieldMapping(source_name="cha_type"),
            },
        },
    )


def get_src_e() -> ProfileDefinition:
    return ProfileDefinition(
        profile_id="SRC-E",
        format="CSV",
        version="2.0",
        timestamp_format="iso_z",
        case_naming="mixed",
        per_family_format={
            "organization": "CSV",
            "submission": "CSV",
            "submission_manifest": "CSV",
            "submission_family": "CSV",
            "control_process_reference": "CSV",
            "control_process_subject_link": "CSV",
            "asset": "CSV",
            "monitoring_coverage": "CSV",
            "alert": "JSON",
            "case": "JSON",
            "case_alert_link": "JSON",
            "investigation": "JSON",
            "escalation": "JSON",
            "action": "JSON",
            "resolution": "JSON",
            "closure": "JSON",
            "exception": "JSON",
            "process_change": "JSON",
        },
        family_mappings={
            "organization": {
                "organization_id": FieldMapping(source_name="org_id", is_native_id=True),
                "source_organization_id": FieldMapping(source_name="legacy_org_code"),
                "organization_name": FieldMapping(source_name="entity_name"),
                "entity_criticality_band": FieldMapping(
                    source_name="criticality_tier", vocabulary=CRITICALITY_BAND_SRC_E
                ),
                "organization_status": FieldMapping(
                    source_name="lifecycle_status", vocabulary=STATUS_SRC_E
                ),
                "profile_effective_start_at_utc": FieldMapping(source_name="valid_from_utc"),
            },
            "submission": {
                "submission_id": FieldMapping(source_name="sub_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="org_id"),
                "period_maturity_state": FieldMapping(
                    source_name="maturity_level", vocabulary=MATURITY_SRC_E
                ),
                "reporting_period_start_at_utc": FieldMapping(source_name="period_start_utc"),
            },
            "submission_manifest": {
                "manifest_id": FieldMapping(source_name="manifest_id", is_native_id=True),
                "submission_id": FieldMapping(source_name="sub_id"),
                "created_at_utc": FieldMapping(source_name="manifest_timestamp_utc"),
            },
            "submission_family": {
                "submission_family_id": FieldMapping(
                    source_name="family_decl_id", is_native_id=True
                ),
                "submission_id": FieldMapping(source_name="sub_id"),
                "evidence_family": FieldMapping(source_name="family_name"),
                "presence_state": FieldMapping(source_name="presence_status"),
            },
            "control_process_reference": {
                "control_process_ref_id": FieldMapping(source_name="ref_id"),
                "organization_id": FieldMapping(source_name="org_id"),
                "reference_type": FieldMapping(source_name="control_type"),
                "reference_code": FieldMapping(source_name="framework_code"),
                "display_name": FieldMapping(source_name="title"),
            },
            "control_process_subject_link": {
                "control_process_link_id": FieldMapping(source_name="link_id"),
                "control_process_ref_id": FieldMapping(source_name="ref_id"),
                "subject_type": FieldMapping(source_name="target_type"),
            },
            "asset": {
                "asset_id": FieldMapping(source_name="asset_id", is_native_id=True),
                "source_asset_id": FieldMapping(source_name="external_asset_tag"),
                "organization_id": FieldMapping(source_name="org_id"),
                "asset_class": FieldMapping(source_name="device_type"),
            },
            "monitoring_coverage": {
                "monitoring_coverage_id": FieldMapping(
                    source_name="coverage_id", is_native_id=True
                ),
                "organization_id": FieldMapping(source_name="org_id"),
                "asset_id": FieldMapping(source_name="asset_id"),
                "monitoring_type": FieldMapping(source_name="sensor_type"),
            },
            "alert": {
                "alert_id": FieldMapping(source_name="id", is_native_id=True),
                "organization_id": FieldMapping(source_name="org_id"),
                "asset_id": FieldMapping(source_name="target_asset_id"),
                "created_at_utc": FieldMapping(source_name="timestamp_utc"),
                "alert_category": FieldMapping(
                    source_name="event_category", vocabulary=CATEGORY_SRC_E
                ),
                "severity": FieldMapping(source_name="event_severity", vocabulary=SEVERITY_SRC_E),
                "disposition": FieldMapping(source_name="outcome", vocabulary=DISPOSITION_SRC_E),
            },
            "case": {
                "case_id": FieldMapping(source_name="case_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="org_id"),
                "case_type": FieldMapping(source_name="incident_type"),
                "severity": FieldMapping(source_name="severity", vocabulary=SEVERITY_SRC_E),
                "created_at_utc": FieldMapping(source_name="opened_at_utc"),
                "alerts": FieldMapping(source_name="linked_alert_ids", is_reference_array=True),
            },
            "case_alert_link": {
                "case_alert_link_id": FieldMapping(source_name="link_id", is_native_id=True),
                "case_id": FieldMapping(source_name="parent_case_id"),
                "alert_id": FieldMapping(source_name="child_alert_id"),
                "link_type": FieldMapping(source_name="link_role"),
            },
            "investigation": {
                "investigation_id": FieldMapping(source_name="inv_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="org_id"),
                "case_id": FieldMapping(source_name="case_id"),
                "alert_id": FieldMapping(source_name="alert_id"),
                "started_at_utc": FieldMapping(source_name="start_timestamp_utc"),
                "disposition": FieldMapping(source_name="outcome", vocabulary=DISPOSITION_SRC_E),
            },
            "escalation": {
                "escalation_id": FieldMapping(source_name="esc_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="org_id"),
                "case_id": FieldMapping(source_name="case_id"),
                "alert_id": FieldMapping(source_name="alert_id"),
                "escalated_at_utc": FieldMapping(source_name="escalated_timestamp_utc"),
            },
            "action": {
                "action_id": FieldMapping(source_name="action_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="org_id"),
                "asset_id": FieldMapping(source_name="asset_id"),
                "alert_id": FieldMapping(source_name="alert_id"),
                "case_id": FieldMapping(source_name="case_id"),
                "action_type": FieldMapping(source_name="response_action"),
            },
            "resolution": {
                "resolution_id": FieldMapping(source_name="resolution_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="org_id"),
                "case_id": FieldMapping(source_name="case_id"),
                "alert_id": FieldMapping(source_name="alert_id"),
                "resolved_at_utc": FieldMapping(source_name="resolved_timestamp_utc"),
            },
            "closure": {
                "closure_id": FieldMapping(source_name="closure_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="org_id"),
                "case_id": FieldMapping(source_name="case_id"),
                "alert_id": FieldMapping(source_name="alert_id"),
                "resolution_id": FieldMapping(source_name="resolution_id"),
                "closed_at_utc": FieldMapping(source_name="closed_timestamp_utc"),
            },
            "exception": {
                "exception_id": FieldMapping(source_name="exception_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="org_id"),
                "exception_type": FieldMapping(source_name="deviation_category"),
            },
            "process_change": {
                "process_change_id": FieldMapping(source_name="change_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="org_id"),
                "change_type": FieldMapping(source_name="modification_type"),
            },
        },
    )


def get_profile(profile_id: str) -> ProfileDefinition:
    profiles = {
        "SRC-A": get_src_a,
        "SRC-B": get_src_b,
        "SRC-C": get_src_c,
        "SRC-D": get_src_d,
        "SRC-E": get_src_e,
    }
    return profiles[profile_id]()
