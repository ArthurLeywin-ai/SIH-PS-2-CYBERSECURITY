"""Catalog of M3 Source Profiles."""

from __future__ import annotations

from satsa_generator.profiles.models import FieldMapping, ProfileDefinition
from satsa_generator.profiles.vocabulary import (
    MATURITY_SRC_B,
    SEVERITY_SRC_B,
    SEVERITY_SRC_C,
    SEVERITY_SRC_D,
    STATUS_SRC_B,
    STATUS_SRC_C,
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
            },
            "case": {
                "case_id": FieldMapping(source_name="case_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="organization_id"),
                "case_type": FieldMapping(source_name="case_type"),
                "severity": FieldMapping(source_name="severity"),
                "created_at_utc": FieldMapping(source_name="created_at_utc"),
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
                    source_name="EntityCriticalityBand", vocabulary=SEVERITY_SRC_B
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
            },
            "case": {
                "case_id": FieldMapping(source_name="CaseId", is_native_id=True),
                "organization_id": FieldMapping(source_name="OrganizationId"),
                "case_type": FieldMapping(source_name="CaseType"),
                "severity": FieldMapping(source_name="Severity"),
                "created_at_utc": FieldMapping(source_name="CreatedAtUtc"),
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
                    vocabulary=SEVERITY_SRC_C,
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
                    source_name="periodMaturityState", path=["details", "periodMaturityState"]
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
            },
            "case": {
                "case_id": FieldMapping(source_name="caseId", is_native_id=True),
                "organization_id": FieldMapping(source_name="organizationId"),
                "case_type": FieldMapping(source_name="caseType", path=["details", "caseType"]),
                "severity": FieldMapping(source_name="severity", path=["details", "severity"]),
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
        family_mappings={
            "organization": {
                "organization_id": FieldMapping(source_name="org_id", is_native_id=True),
                "source_organization_id": FieldMapping(source_name="sou_org_id", is_present=False),
                "organization_name": FieldMapping(source_name="org_name"),
                "entity_criticality_band": FieldMapping(
                    source_name="ent_cri_band", vocabulary=SEVERITY_SRC_D
                ),
                "organization_status": FieldMapping(source_name="org_status"),
                "profile_effective_start_at_utc": FieldMapping(source_name="pro_eff_utc"),
            },
            "submission": {
                "submission_id": FieldMapping(source_name="sub_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="org_id"),
                "period_maturity_state": FieldMapping(source_name="per_mat_state"),
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
                "control_process_link_id": FieldMapping(source_name="con_pro_id"),
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
            },
            "case": {
                "case_id": FieldMapping(source_name="cas_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="org_id"),
                "case_type": FieldMapping(source_name="cas_type"),
                "severity": FieldMapping(source_name="sev"),
                "created_at_utc": FieldMapping(source_name="cre_at_utc"),
                "alerts": FieldMapping(source_name="alerts"),
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
        timestamp_format="iso_z",
        version="2.0",
        family_mappings={
            "organization": {
                "organization_id": FieldMapping(source_name="v2_org_id", is_native_id=True),
                "source_organization_id": FieldMapping(source_name="v2_sou_org_id"),
                "organization_name": FieldMapping(source_name="v2_org_name"),
                "entity_criticality_band": FieldMapping(
                    source_name="v2_ent_cri_band", vocabulary=SEVERITY_SRC_B
                ),
                "organization_status": FieldMapping(source_name="v2_org_status"),
                "profile_effective_start_at_utc": FieldMapping(source_name="v2_pro_eff_utc"),
            },
            "submission": {
                "submission_id": FieldMapping(source_name="v2_sub_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="v2_org_id"),
                "period_maturity_state": FieldMapping(source_name="v2_per_mat_state"),
                "reporting_period_start_at_utc": FieldMapping(source_name="v2_rep_per_utc"),
            },
            "submission_manifest": {
                "manifest_id": FieldMapping(source_name="v2_man_id", is_native_id=True),
                "submission_id": FieldMapping(source_name="v2_sub_id"),
                "created_at_utc": FieldMapping(source_name="v2_cre_at_utc"),
            },
            "submission_family": {
                "submission_family_id": FieldMapping(
                    source_name="v2_sub_fam_id", is_native_id=True
                ),
                "submission_id": FieldMapping(source_name="v2_sub_id"),
                "evidence_family": FieldMapping(source_name="v2_evi_family"),
                "presence_state": FieldMapping(source_name="v2_pre_state"),
            },
            "control_process_reference": {
                "control_process_ref_id": FieldMapping(source_name="v2_con_pro_id"),
                "organization_id": FieldMapping(source_name="v2_org_id"),
                "reference_type": FieldMapping(source_name="v2_ref_type"),
                "reference_code": FieldMapping(source_name="v2_ref_code"),
                "display_name": FieldMapping(source_name="v2_dis_name"),
            },
            "control_process_subject_link": {
                "control_process_link_id": FieldMapping(source_name="v2_con_pro_id"),
                "control_process_ref_id": FieldMapping(source_name="v2_con_pro_id"),
                "subject_type": FieldMapping(source_name="v2_sub_type"),
            },
            "asset": {
                "asset_id": FieldMapping(source_name="v2_ass_id", is_native_id=True),
                "source_asset_id": FieldMapping(source_name="v2_sou_ass_id"),
                "organization_id": FieldMapping(source_name="v2_org_id"),
                "asset_class": FieldMapping(source_name="v2_ass_class"),
            },
            "monitoring_coverage": {
                "monitoring_coverage_id": FieldMapping(
                    source_name="v2_mon_cov_id", is_native_id=True
                ),
                "organization_id": FieldMapping(source_name="v2_org_id"),
                "asset_id": FieldMapping(source_name="v2_ass_id"),
                "monitoring_type": FieldMapping(source_name="v2_mon_type"),
            },
            "alert": {
                "alert_id": FieldMapping(source_name="v2_ale_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="v2_org_id"),
                "asset_id": FieldMapping(source_name="v2_ass_id"),
                "created_at_utc": FieldMapping(source_name="v2_cre_at_utc"),
            },
            "case": {
                "case_id": FieldMapping(source_name="v2_cas_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="v2_org_id"),
                "case_type": FieldMapping(source_name="v2_cas_type"),
                "severity": FieldMapping(source_name="v2_sev"),
                "created_at_utc": FieldMapping(source_name="v2_cre_at_utc"),
            },
            "case_alert_link": {
                "case_alert_link_id": FieldMapping(source_name="v2_cas_ale_id", is_native_id=True),
                "case_id": FieldMapping(source_name="v2_cas_id"),
                "alert_id": FieldMapping(source_name="v2_ale_id"),
                "link_type": FieldMapping(source_name="v2_lin_type"),
            },
            "investigation": {
                "investigation_id": FieldMapping(source_name="v2_inv_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="v2_org_id"),
                "case_id": FieldMapping(source_name="v2_cas_id"),
                "alert_id": FieldMapping(source_name="v2_ale_id"),
                "started_at_utc": FieldMapping(source_name="v2_sta_at_utc"),
            },
            "escalation": {
                "escalation_id": FieldMapping(source_name="v2_esc_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="v2_org_id"),
                "case_id": FieldMapping(source_name="v2_cas_id"),
                "alert_id": FieldMapping(source_name="v2_ale_id"),
                "escalated_at_utc": FieldMapping(source_name="v2_esc_at_utc"),
            },
            "action": {
                "action_id": FieldMapping(source_name="v2_act_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="v2_org_id"),
                "asset_id": FieldMapping(source_name="v2_ass_id"),
                "alert_id": FieldMapping(source_name="v2_ale_id"),
                "case_id": FieldMapping(source_name="v2_cas_id"),
                "action_type": FieldMapping(source_name="v2_act_type"),
            },
            "resolution": {
                "resolution_id": FieldMapping(source_name="v2_res_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="v2_org_id"),
                "case_id": FieldMapping(source_name="v2_cas_id"),
                "alert_id": FieldMapping(source_name="v2_ale_id"),
                "resolved_at_utc": FieldMapping(source_name="v2_res_at_utc"),
            },
            "closure": {
                "closure_id": FieldMapping(source_name="v2_clo_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="v2_org_id"),
                "case_id": FieldMapping(source_name="v2_cas_id"),
                "alert_id": FieldMapping(source_name="v2_ale_id"),
                "resolution_id": FieldMapping(source_name="v2_res_id"),
                "closed_at_utc": FieldMapping(source_name="v2_clo_at_utc"),
            },
            "exception": {
                "exception_id": FieldMapping(source_name="v2_exc_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="v2_org_id"),
                "exception_type": FieldMapping(source_name="v2_exc_type"),
            },
            "process_change": {
                "process_change_id": FieldMapping(source_name="v2_pro_cha_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="v2_org_id"),
                "change_type": FieldMapping(source_name="v2_cha_type"),
            },
        },
    )


def get_profile(profile_id: str) -> ProfileDefinition:
    """Get a profile definition by ID."""
    profiles = {
        "SRC-A": get_src_a,
        "SRC-B": get_src_b,
        "SRC-C": get_src_c,
        "SRC-D": get_src_d,
        "SRC-E": get_src_e,
    }
    return profiles[profile_id]()
