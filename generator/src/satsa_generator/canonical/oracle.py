"""Canonical Oracle for mapping source outputs back to canonical references."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OracleMappingRecord(BaseModel):
    """Maps a generated source field back to its canonical origin."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_profile: str
    source_file_path: str
    source_record_index: int
    source_field_name: str
    canonical_family: str
    canonical_record_id: UUID
    canonical_field_name: str
    canonical_value: Any
    rendered_value: Any


class ProvenanceEdge(BaseModel):
    """Represents a lineage connection from source up to canonical."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str
    canonical_id: UUID
    relation_type: str


@dataclass
class CanonicalOracle:
    """Independent oracle withholding the canonical reference."""

    mappings: list[OracleMappingRecord] = field(default_factory=list)
    provenance: list[ProvenanceEdge] = field(default_factory=list)

    def register_mapping(self, record: OracleMappingRecord) -> None:
        """Register a new field-level mapping."""
        self.mappings.append(record)

    def register_provenance(self, edge: ProvenanceEdge) -> None:
        """Register a provenance edge."""
        self.provenance.append(edge)

    def get_canonical_for_source(
        self, profile: str, file_path: str, record_index: int
    ) -> dict[str, Any]:
        """Look up all canonical mappings for a specific source record."""
        result = {}
        for m in self.mappings:
            if (
                m.source_profile == profile
                and m.source_file_path == file_path
                and m.source_record_index == record_index
            ):
                result[m.canonical_field_name] = m.canonical_value
        return result

    def calculate_oracle_hash(self) -> str:
        """Return a deterministic hash of the entire oracle."""
        sorted_mappings = sorted(
            [m.model_dump(mode="json") for m in self.mappings],
            key=lambda x: (
                x["source_profile"],
                x["source_file_path"],
                x["source_record_index"],
                x["source_field_name"],
            ),
        )
        content = json.dumps(sorted_mappings, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return hashlib.sha256(content).hexdigest()
