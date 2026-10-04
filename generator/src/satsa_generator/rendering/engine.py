"""Rendering Engine orchestrates M3 source rendering."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from satsa_generator.canonical.oracle import CanonicalOracle
from satsa_generator.fixture.models import FixtureRecord
from satsa_generator.profiles.models import ProfileDefinition
from satsa_generator.rendering.csv_renderer import CSVRenderer
from satsa_generator.rendering.interfaces import RenderContext
from satsa_generator.rendering.json_renderer import JSONRenderer


@dataclass
class RenderResult:
    """Result of rendering a batch of records."""

    files_written: list[dict[str, Any]]
    oracle_hash: str


class RenderingEngine:
    """Coordinates rendering of canonical records into source files."""

    def __init__(self, output_root: Path, profile: ProfileDefinition):
        self.output_root = output_root
        self.profile = profile
        self.oracle = CanonicalOracle()

        if profile.format == "CSV":
            self.renderer = CSVRenderer()
            self.ext = "csv"
        elif profile.format == "JSON":
            self.renderer = JSONRenderer()
            self.ext = "json"
        else:
            raise ValueError(f"Unsupported format: {profile.format}")

    def render_and_write(self, family: str, records: list[FixtureRecord]) -> dict[str, Any] | None:
        """Render records for a given family and write to disk."""
        if not records:
            return None

        # Build logical filename
        filename = f"{family}_{self.profile.profile_id.lower()}.{self.ext}"
        filepath = self.output_root / filename
        relative_path = filepath.name

        context = RenderContext(
            oracle=self.oracle,
            profile=self.profile,
            output_path=relative_path,
        )

        content = self.renderer.render_records(family, records, context)

        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_bytes(content)

        import hashlib

        return {
            "path": relative_path,
            "byte_size": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        }

    def write_oracle(self, oracle_path: Path) -> str:
        """Write the canonical oracle to disk and return its hash."""
        # Convert entire oracle to dict for JSON serialization
        oracle_data = {
            "mappings": [m.model_dump(mode="json") for m in self.oracle.mappings],
            "provenance": [p.model_dump(mode="json") for p in self.oracle.provenance],
        }

        oracle_path.parent.mkdir(parents=True, exist_ok=True)
        oracle_path.write_text(json.dumps(oracle_data, indent=2), encoding="utf-8")

        return self.oracle.calculate_oracle_hash()
