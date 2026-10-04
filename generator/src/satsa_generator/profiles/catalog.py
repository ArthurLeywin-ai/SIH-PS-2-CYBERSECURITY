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
    """SRC-A: CSV, snake_case, stable declared columns, most native IDs present, ISO 8601 UTC."""
    return ProfileDefinition(
        profile_id="SRC-A",
        format="CSV",
        timestamp_format="iso_z",
        family_mappings={
            "organization": {
                "organization_id": FieldMapping(source_name="organization_id", is_native_id=True),
                "source_organization_id": FieldMapping(source_name="source_organization_id", is_native_id=True),
                "organization_name": FieldMapping(source_name="organization_name"),
                "entity_criticality_band": FieldMapping(source_name="entity_criticality_band"),
                "organization_status": FieldMapping(source_name="organization_status"),
                "profile_effective_start_at_utc": FieldMapping(source_name="profile_effective_start_at_utc"),
            },
            "submission": {
                "submission_id": FieldMapping(source_name="submission_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="organization_id"),
                "period_maturity_state": FieldMapping(source_name="period_maturity_state"),
                "reporting_period_start_at_utc": FieldMapping(source_name="reporting_period_start_at_utc"),
            },
            "submission_manifest": {
                "manifest_id": FieldMapping(source_name="manifest_id", is_native_id=True),
                "submission_id": FieldMapping(source_name="submission_id"),
                "created_at_utc": FieldMapping(source_name="created_at_utc"),
            },
            "alert": {
                "alert_id": FieldMapping(source_name="alert_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="organization_id"),
                "created_at_utc": FieldMapping(source_name="created_at_utc"),
            }
        }
    )


def get_src_b() -> ProfileDefinition:
    """SRC-B: CSV, mixed/Pascal-style headings, local timestamps, numeric/abbrev vocab, optional child IDs absent."""
    return ProfileDefinition(
        profile_id="SRC-B",
        format="CSV",
        timestamp_format="local_iana",
        timezone="America/New_York",
        family_mappings={
            "organization": {
                "organization_id": FieldMapping(source_name="OrganizationID", is_native_id=True),
                # source_organization_id intentionally omitted to test absent optional IDs
                "source_organization_id": FieldMapping(source_name="SrcOrgID", is_present=False),
                "organization_name": FieldMapping(source_name="OrgName"),
                "entity_criticality_band": FieldMapping(source_name="Criticality", vocabulary=SEVERITY_SRC_B),
                "organization_status": FieldMapping(source_name="Status", vocabulary=STATUS_SRC_B),
                "profile_effective_start_at_utc": FieldMapping(source_name="EffectiveStart"),
            },
            "submission": {
                "submission_id": FieldMapping(source_name="SubmissionID", is_native_id=True),
                "organization_id": FieldMapping(source_name="OrganizationID"),
                "period_maturity_state": FieldMapping(source_name="Maturity", vocabulary=MATURITY_SRC_B),
                "reporting_period_start_at_utc": FieldMapping(source_name="PeriodStart"),
            },
            "submission_manifest": {
                "manifest_id": FieldMapping(source_name="ManifestID", is_native_id=True),
                "submission_id": FieldMapping(source_name="SubmissionID"),
                "created_at_utc": FieldMapping(source_name="CreatedAt"),
            },
            "alert": {
                "alert_id": FieldMapping(source_name="AlertID", is_native_id=True),
                "organization_id": FieldMapping(source_name="OrganizationID"),
                "created_at_utc": FieldMapping(source_name="CreatedAt"),
            }
        }
    )


def get_src_c() -> ProfileDefinition:
    """SRC-C: Nested JSON, camelCase/nested keys, parent IDs present, ISO offsets/ms, vendor vocab."""
    return ProfileDefinition(
        profile_id="SRC-C",
        format="JSON",
        timestamp_format="iso_offset_ms",
        relationships_nested=True,
        family_mappings={
            "organization": {
                "organization_id": FieldMapping(source_name="organizationId", is_native_id=True),
                "source_organization_id": FieldMapping(source_name="sourceId", path=["metadata", "sourceId"]),
                "organization_name": FieldMapping(source_name="name", path=["details", "name"]),
                "entity_criticality_band": FieldMapping(source_name="criticality", vocabulary=SEVERITY_SRC_C, path=["details", "criticality"]),
                "organization_status": FieldMapping(source_name="status", vocabulary=STATUS_SRC_C),
                "profile_effective_start_at_utc": FieldMapping(source_name="effectiveStart"),
            },
            "submission": {
                "submission_id": FieldMapping(source_name="submissionId", is_native_id=True),
                "organization_id": FieldMapping(source_name="organizationId"),
                "period_maturity_state": FieldMapping(source_name="maturityState"),
                "reporting_period_start_at_utc": FieldMapping(source_name="reportingPeriodStart"),
            },
            "submission_manifest": {
                "manifest_id": FieldMapping(source_name="manifestId", is_native_id=True),
                "submission_id": FieldMapping(source_name="submissionId"),
                "created_at_utc": FieldMapping(source_name="createdAt"),
            },
            "alert": {
                "alert_id": FieldMapping(source_name="alertId", is_native_id=True),
                "organization_id": FieldMapping(source_name="organizationId"),
                "created_at_utc": FieldMapping(source_name="createdAt"),
            }
        }
    )


def get_src_d() -> ProfileDefinition:
    """SRC-D: JSON lines, mixed ID availability, lowercase vocab, date-only representations."""
    return ProfileDefinition(
        profile_id="SRC-D",
        format="JSONL",
        timestamp_format="date_only",
        family_mappings={
            "organization": {
                "organization_id": FieldMapping(source_name="id", is_native_id=True),
                "source_organization_id": FieldMapping(source_name="src_id", is_present=False),
                "organization_name": FieldMapping(source_name="org_name"),
                "entity_criticality_band": FieldMapping(source_name="severity", vocabulary=SEVERITY_SRC_D),
                "organization_status": FieldMapping(source_name="status"),
                "profile_effective_start_at_utc": FieldMapping(source_name="start_date"),
            },
            "submission": {
                "submission_id": FieldMapping(source_name="sub_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="org_id"),
                "period_maturity_state": FieldMapping(source_name="state"),
                "reporting_period_start_at_utc": FieldMapping(source_name="start_date"),
            },
            "submission_manifest": {
                "manifest_id": FieldMapping(source_name="man_id", is_native_id=True),
                "submission_id": FieldMapping(source_name="sub_id"),
                "created_at_utc": FieldMapping(source_name="date"),
            },
            "alert": {
                "alert_id": FieldMapping(source_name="alert_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="org_id"),
                "created_at_utc": FieldMapping(source_name="date"),
            }
        }
    )


def get_src_e() -> ProfileDefinition:
    """SRC-E: Versioned CSV/JSON hybrid. Uses CSV with vocabulary drift."""
    return ProfileDefinition(
        profile_id="SRC-E",
        version="2.0",
        format="CSV",
        timestamp_format="iso_z",
        family_mappings={
            "organization": {
                "organization_id": FieldMapping(source_name="v2_org_id", is_native_id=True),
                "source_organization_id": FieldMapping(source_name="v2_src_id"),
                "organization_name": FieldMapping(source_name="v2_name"),
                "entity_criticality_band": FieldMapping(source_name="v2_crit", vocabulary=SEVERITY_SRC_B),
                "organization_status": FieldMapping(source_name="v2_status"),
                "profile_effective_start_at_utc": FieldMapping(source_name="v2_start"),
            },
            "submission": {
                "submission_id": FieldMapping(source_name="v2_sub_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="v2_org_id"),
                "period_maturity_state": FieldMapping(source_name="v2_state"),
                "reporting_period_start_at_utc": FieldMapping(source_name="v2_start"),
            },
            "submission_manifest": {
                "manifest_id": FieldMapping(source_name="v2_man_id", is_native_id=True),
                "submission_id": FieldMapping(source_name="v2_sub_id"),
                "created_at_utc": FieldMapping(source_name="v2_created"),
            },
            "alert": {
                "alert_id": FieldMapping(source_name="v2_alert_id", is_native_id=True),
                "organization_id": FieldMapping(source_name="v2_org_id"),
                "created_at_utc": FieldMapping(source_name="v2_created"),
            }
        }
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
