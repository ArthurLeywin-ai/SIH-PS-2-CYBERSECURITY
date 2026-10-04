"""Catalog of M3 Source Profiles."""

from __future__ import annotations

from satsa_generator.profiles.models import FieldMapping, ProfileDefinition


def get_src_a() -> ProfileDefinition:
    """SRC-A: CSV, snake_case, ISO 8601 with Z."""
    return ProfileDefinition(
        profile_id="SRC-A",
        format="CSV",
        timestamp_format="iso_z",
        case_naming="snake_case",
        family_mappings={
            "organization": {
                "organization_id": FieldMapping(source_name="org_id"),
                "organization_name": FieldMapping(source_name="org_name"),
            }
        },
    )


def get_src_b() -> ProfileDefinition:
    """SRC-B: CSV, Pascal headings, local time."""
    return ProfileDefinition(
        profile_id="SRC-B",
        format="CSV",
        timestamp_format="local_iana",
        case_naming="pascal_case",
        family_mappings={
            "organization": {
                "organization_id": FieldMapping(source_name="OrganizationID"),
                "organization_name": FieldMapping(source_name="OrganizationName"),
            }
        },
    )


def get_src_c() -> ProfileDefinition:
    """SRC-C: JSON nested, iso offsets."""
    return ProfileDefinition(
        profile_id="SRC-C",
        format="JSON",
        timestamp_format="iso_offset_ms",
        case_naming="mixed",
        family_mappings={
            "organization": {
                "organization_id": FieldMapping(source_name="organization_id"),
                "organization_name": FieldMapping(source_name="organizationName"),
            }
        },
    )


def get_profile(profile_id: str) -> ProfileDefinition:
    """Get a profile definition by ID."""
    if profile_id == "SRC-A":
        return get_src_a()
    elif profile_id == "SRC-B":
        return get_src_b()
    elif profile_id == "SRC-C":
        return get_src_c()
    # Mocking D and E for now
    return get_src_a()
