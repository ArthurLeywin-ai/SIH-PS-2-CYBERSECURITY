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
    declared_completeness: Literal[
        "DECLARED_COMPLETE", "DECLARED_PARTIAL", "NOT_DECLARED"
    ]
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
    submission_quality_state: Literal[
        "VALID", "WARNING", "INVALID", "INCOMPLETE", "UNKNOWN"
    ]

    @field_validator("declared_missing_families")
    @classmethod
    def validate_missing_family_shape(
        cls, value: list[dict[str, str]] | None
    ) -> list[dict[str, str]] | None:
        if value is None:
            return value
        for entry in value:
            if "evidence_family" not in entry:
                raise ValueError(
                    "each declared_missing_families entry needs evidence_family"
                )
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
    fixture_contract: Literal["SATSA-M1-FIXTURE-V1"]
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
