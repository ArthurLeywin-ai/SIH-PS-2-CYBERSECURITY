"""Source profile definitions and mapping structures for Milestone 3.
Defines how canonical records map to heterogeneous source representations.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class VocabularyMap(BaseModel):
    """Deterministic vocabulary mapping from Canonical -> Source -> Canonical."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    # E.g. {"HIGH": "3", "LOW": "1"}
    canonical_to_source: dict[str, str | int]

    # E.g. {"3": "HIGH", "1": "LOW"}
    source_to_canonical: dict[str | int, str]

    # How to handle unknown/unmapped strings during parser validation
    on_unknown: Literal["fail", "pass_through"] = "fail"


class FieldMapping(BaseModel):
    """Mapping rules for a single canonical field to its source equivalent."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_name: str
    is_present: bool = True
    default_if_missing: str | int | None = None
    vocabulary: VocabularyMap | None = None
    # For nested JSON like 'attributes.category'
    path: list[str] | None = None
    # Optional Source ID logic
    is_native_id: bool = False
    # Reference array support (e.g., case.alerts -> array of references)
    is_reference_array: bool = False


TimestampFormat = Literal["iso_z", "iso_offset", "iso_offset_ms", "local_iana", "date_only"]
FormatType = Literal["CSV", "JSON", "JSONL"]
CaseNamingType = Literal["snake_case", "pascal_case", "camel_case", "mixed", "custom"]


class ProfileDefinition(BaseModel):
    """Contract for a heterogeneous source profile (e.g., SRC-A, SRC-B)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    profile_id: Literal["SRC-A", "SRC-B", "SRC-C", "SRC-D", "SRC-E"]
    version: str = "1.0"
    format: FormatType
    case_naming: CaseNamingType = "snake_case"
    timestamp_format: TimestampFormat
    timezone: str = "UTC"  # For local_iana

    # Per-family overrides for hybrid profiles or mixed formats:
    per_family_format: dict[str, FormatType] = Field(default_factory=dict)
    per_family_timestamp_format: dict[str, TimestampFormat] = Field(default_factory=dict)
    per_family_timezone: dict[str, str] = Field(default_factory=dict)

    # Whether child IDs or relationships are nested
    relationships_nested: bool = False

    # Namespace for source identifiers (e.g., "E1", "E2" for SRC-E migration periods)
    id_namespace: str | None = None
    # JSON mode for JSON profiles: "array" (default) or "lines" (JSONL)
    json_mode: Literal["array", "lines"] = "array"

    # Maps canonical evidence family (e.g., "case", "alert") to its field mappings
    family_mappings: dict[str, dict[str, FieldMapping]] = Field(default_factory=dict)

    def get_format(self, family: str) -> FormatType:
        return self.per_family_format.get(family, self.format)

    def get_timestamp_format(self, family: str) -> TimestampFormat:
        return self.per_family_timestamp_format.get(family, self.timestamp_format)

    def get_timezone(self, family: str) -> str:
        return self.per_family_timezone.get(family, self.timezone)
