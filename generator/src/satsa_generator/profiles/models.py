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


class ProfileDefinition(BaseModel):
    """Contract for a heterogeneous source profile (e.g., SRC-A, SRC-B)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    profile_id: Literal["SRC-A", "SRC-B", "SRC-C", "SRC-D", "SRC-E"]
    version: str = "1.0"
    format: Literal["CSV", "JSON", "JSONL"]
    case_naming: Literal["snake_case", "pascal_case", "camel_case", "mixed"] = "snake_case"
    timestamp_format: Literal["iso_z", "iso_offset_ms", "local_iana", "date_only"]
    timezone: str = "UTC" # For local_iana

    # Whether child IDs or relationships are nested
    relationships_nested: bool = False

    # Maps canonical evidence family (e.g., "case", "alert") to its field mappings
    family_mappings: dict[str, dict[str, FieldMapping]] = Field(default_factory=dict)
