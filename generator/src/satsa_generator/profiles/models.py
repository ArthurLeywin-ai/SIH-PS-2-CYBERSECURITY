"""Source profile definitions and mapping structures for Milestone 3.
Defines how canonical records map to heterogeneous source representations.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FieldMapping(BaseModel):
    """Mapping rules for a single canonical field to its source equivalent."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_name: str
    is_present: bool = True
    default_if_missing: str | None = None
    vocabulary_type: str | None = None


class ProfileDefinition(BaseModel):
    """Contract for a heterogeneous source profile (e.g., SRC-A, SRC-B)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    profile_id: Literal["SRC-A", "SRC-B", "SRC-C", "SRC-D", "SRC-E"]
    format: Literal["CSV", "JSON"]
    timestamp_format: Literal["iso_z", "iso_offset_ms", "local_iana"]
    case_naming: Literal["snake_case", "pascal_case", "camel_case", "mixed"]
    # Maps canonical evidence family (e.g., "case", "alert") to its field mappings
    family_mappings: dict[str, dict[str, FieldMapping]] = Field(default_factory=dict)
