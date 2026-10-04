"""Source file/record Index and Provenance models."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SourceRecordIndex(BaseModel):
    """Index mapping a specific source record to its canonical origin."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_file_path: str
    source_profile_id: str
    organization_id: UUID | None = None
    submission_id: UUID | None = None
    evidence_family: str
    canonical_record_id: UUID
    source_record_locator: str  # e.g., "row:5" or "json_path:$[4]"
    source_checksum: str


class FieldProvenance(BaseModel):
    """Provenance for a single field."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_file_path: str
    source_record_locator: str
    source_field_name: str
    canonical_record_id: UUID
    canonical_field_name: str
    raw_value: Any = None


class RelationshipProvenance(BaseModel):
    """Provenance for a relationship between two canonical records."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_file_path: str
    source_record_locator: str
    source_relationship_field: str | None = None
    canonical_subject_id: UUID
    canonical_object_id: UUID | list[UUID]
    relationship_type: str
