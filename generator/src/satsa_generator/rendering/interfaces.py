"""Renderer interfaces for Milestone 3.

Renderers take canonical FixtureRecords and convert them to raw bytes
(CSV or JSON) adhering to a specified ProfileDefinition.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Any

from satsa_generator.canonical.oracle import CanonicalOracle
from satsa_generator.fixture.models import FixtureRecord
from satsa_generator.profiles.models import ProfileDefinition


@dataclass
class RenderContext:
    """Context passed to renderers."""

    oracle: CanonicalOracle
    profile: ProfileDefinition
    output_path: str  # logical relative path


class BaseRenderer(abc.ABC):
    """Abstract base class for all source renderers."""

    @abc.abstractmethod
    def render_records(
        self,
        family: str,
        records: list[FixtureRecord],
        context: RenderContext,
    ) -> bytes:
        """Render a list of records to bytes, populating the oracle."""
        pass

    def apply_field_mapping(
        self,
        canonical_field: str,
        canonical_value: Any,
        family: str,
        context: RenderContext,
    ) -> tuple[str, Any] | None:
        """
        Apply profile mapping rules for a specific field.
        Returns (source_field_name, source_value) or None if missing.
        """
        family_map = context.profile.family_mappings.get(family, {})
        if canonical_field not in family_map:
            # Pass through identically if not explicitly mapped
            return canonical_field, canonical_value

        mapping = family_map[canonical_field]
        if not mapping.is_present:
            return None

        # Convert value based on type overrides (e.g. timestamp formatting)
        source_val = canonical_value
        if canonical_value is None and mapping.default_if_missing is not None:
            source_val = mapping.default_if_missing
        elif hasattr(source_val, "isoformat") and context.profile.timestamp_format == "iso_z":
            source_val = source_val.isoformat().replace("+00:00", "Z")
        elif (
            hasattr(source_val, "isoformat") and context.profile.timestamp_format == "iso_offset_ms"
        ):
            source_val = source_val.isoformat(timespec="milliseconds")
        elif hasattr(source_val, "isoformat") and context.profile.timestamp_format == "local_iana":
            # Simplified for M3, just format as string
            source_val = source_val.strftime("%Y-%m-%dT%H:%M:%S")

        # Basic vocabulary mapping placeholder
        if mapping.vocabulary_type and isinstance(source_val, str):
            # In a real system, would lookup in vocabulary registry
            pass

        # Use the overridden field name
        source_name = mapping.source_name
        return source_name, source_val
