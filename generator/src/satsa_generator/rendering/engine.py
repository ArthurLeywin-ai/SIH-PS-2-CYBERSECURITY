"""Rendering Engine orchestrates M3 source rendering."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from satsa_generator.fixture.models import FixtureRecord
from satsa_generator.profiles.models import ProfileDefinition
from satsa_generator.provenance.models import (
    FieldProvenance,
    RelationshipProvenance,
    SourceRecordIndex,
)
from satsa_generator.rendering.csv_renderer import CSVRenderer
from satsa_generator.rendering.interfaces import RenderContext
from satsa_generator.rendering.json_renderer import JSONRenderer


@dataclass
class RenderResult:
    """Result of rendering a batch of records."""

    files_written: list[dict[str, Any]]
    indexes: list[SourceRecordIndex]
    field_provenance: list[FieldProvenance]
    relationship_provenance: list[RelationshipProvenance]


class RenderingEngine:
    """Coordinates rendering of canonical records into source files."""

    def __init__(self, output_root: Path, profile: ProfileDefinition):
        self.output_root = output_root
        self.profile = profile
        self.indexes: list[SourceRecordIndex] = []
        self.field_provenance: list[FieldProvenance] = []
        self.relationship_provenance: list[RelationshipProvenance] = []

        if self.profile.format == "CSV":
            self.renderer = CSVRenderer()
            self.ext = "csv"
        elif self.profile.format == "JSON":
            self.renderer = JSONRenderer()
            self.ext = "json"
        elif self.profile.format == "JSONL":
            self.renderer = JSONRenderer()
            self.ext = "jsonl"
        else:
            raise ValueError(f"Unsupported format: {profile.format}")

    def render_and_write(
        self,
        family: str,
        records: list[FixtureRecord],
        relationship_records: list[FixtureRecord] | None = None,
        relationship_subject_field: str | None = None,
        relationship_object_field: str | None = None,
        relationship_target_field: str | None = None,
    ) -> dict[str, Any] | None:
        """Render records for a given family and write to disk."""
        if not records:
            return None

        filename = f"{family}_{self.profile.profile_id.lower()}.{self.ext}"
        filepath = self.output_root / filename
        relative_path = filepath.name

        context = RenderContext(
            profile=self.profile,
            output_path=relative_path,
            relationship_records=relationship_records or [],
            relationship_subject_field=relationship_subject_field,
            relationship_object_field=relationship_object_field,
            relationship_target_field=relationship_target_field,
        )

        content = self.renderer.render_records(family, records, context)

        self.indexes.extend(context.indexes)
        self.field_provenance.extend(context.field_provenance)
        self.relationship_provenance.extend(context.relationship_provenance)

        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_bytes(content)

        return {
            "path": relative_path,
            "byte_size": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        }

    def get_provenance_hash(self) -> str:
        """Deterministically hash the provenance."""
        combined = {
            "indexes": sorted(
                [idx.model_dump(mode="json") for idx in self.indexes],
                key=lambda x: x["source_record_locator"],
            ),
            "field_provenance": sorted(
                [fp.model_dump(mode="json") for fp in self.field_provenance],
                key=lambda x: (x["source_record_locator"], x["canonical_field_name"]),
            ),
            "relationship_provenance": sorted(
                [rp.model_dump(mode="json") for rp in self.relationship_provenance],
                key=lambda x: x["source_record_locator"],
            ),
        }
        content = json.dumps(combined, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return hashlib.sha256(content).hexdigest()

    def write_metadata(self, base_path: Path, prefix: str) -> str:
        """Write index and provenance metadata."""
        base_path.mkdir(parents=True, exist_ok=True)

        index_path = base_path / f"{prefix}_index.json"
        index_data = [idx.model_dump(mode="json") for idx in self.indexes]
        index_path.write_text(json.dumps(index_data, indent=2, sort_keys=True), encoding="utf-8")

        prov_path = base_path / f"{prefix}_provenance.json"
        prov_data = {
            "field_provenance": [fp.model_dump(mode="json") for fp in self.field_provenance],
            "relationship_provenance": [
                rp.model_dump(mode="json") for rp in self.relationship_provenance
            ],
        }
        prov_path.write_text(json.dumps(prov_data, indent=2, sort_keys=True), encoding="utf-8")

        return self.get_provenance_hash()
