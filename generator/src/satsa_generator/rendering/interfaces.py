"""Renderer interfaces for Milestone 3.

Renderers take canonical FixtureRecords and convert them to raw bytes
(CSV or JSON) adhering to a specified ProfileDefinition.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any

from satsa_generator.fixture.models import FixtureRecord
from satsa_generator.profiles.models import ProfileDefinition
from satsa_generator.provenance.models import (
    FieldProvenance,
    RelationshipProvenance,
    SourceRecordIndex,
)


@dataclass
class RenderContext:
    """Context passed to renderers."""
    profile: ProfileDefinition
    output_path: str  # logical relative path
    indexes: list[SourceRecordIndex] = field(default_factory=list)
    field_provenance: list[FieldProvenance] = field(default_factory=list)
    relationship_provenance: list[RelationshipProvenance] = field(default_factory=list)


class BaseRenderer(abc.ABC):
    """Abstract base class for all source renderers."""

    @abc.abstractmethod
    def render_records(
        self,
        family: str,
        records: list[FixtureRecord],
        context: RenderContext,
    ) -> bytes:
        """Render a list of records to bytes."""
        pass

    def apply_field_mapping(
        self,
        canonical_field: str,
        canonical_value: Any,
        family: str,
        context: RenderContext,
    ) -> tuple[str, Any, list[str] | None] | None:
        """
        Apply profile mapping rules for a specific field.
        Returns (source_field_name, source_value, optional_path) or None if missing.
        """
        family_map = context.profile.family_mappings.get(family, {})
        if canonical_field not in family_map:
            # Pass through identically if not explicitly mapped
            return canonical_field, canonical_value, None

        mapping = family_map[canonical_field]
        if not mapping.is_present:
            return None

        # Convert value based on type overrides (e.g. timestamp formatting)
        source_val = canonical_value
        if canonical_value is None and mapping.default_if_missing is not None:
            source_val = mapping.default_if_missing
        elif isinstance(source_val, str) and ("T" in source_val and ("Z" in source_val or "+00:00" in source_val)) and (canonical_field.endswith("_utc") or canonical_field.endswith("at") or canonical_field == "profile_effective_start_at_utc"):
            if context.profile.timestamp_format == "iso_z":
                source_val = source_val.replace("+00:00", "Z")
            elif context.profile.timestamp_format == "iso_offset_ms":
                # Ensure MS and offset are present, but if it already has Z or +00:00 we might need to normalize
                source_val = source_val.replace("Z", "+00:00")
            elif context.profile.timestamp_format == "local_iana":
                source_val = source_val.replace("+00:00", "").replace("Z", "").replace("T", " ")
            elif context.profile.timestamp_format == "date_only":
                source_val = source_val[:10]

        if mapping.vocabulary and isinstance(source_val, str):
            vocab = mapping.vocabulary.canonical_to_source
            if source_val in vocab:
                source_val = vocab[source_val]
            elif mapping.vocabulary.on_unknown == "fail":
                raise ValueError(f"Unmapped vocabulary value: {source_val}")

        return mapping.source_name, source_val, mapping.path
