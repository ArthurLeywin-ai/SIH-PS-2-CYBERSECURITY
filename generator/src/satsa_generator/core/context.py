"""
Build context — immutable snapshot of the current generation run.

The BuildContext is created once at the start of a generation run and
passed immutably to every stage. No stage may modify it. It carries
frozen configuration hashes, version identifiers, output roots, and
the seed registry reference.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any

from satsa_generator.core.types import BenchmarkTier, PackageDomain, SplitID


@dataclass(frozen=True)
class VersionTuple:
    """Unique identity of a reproducible build.

    From DATASET_GENERATION_SPEC §4.1:
    generator_version + generator_build_hash + schema_version +
    source_profile_set_version + mapping_set_version +
    vocabulary_set_version + scenario_catalog_version +
    dataset_tier + split_id + full_seed_ledger
    """

    generator_version: str
    generator_build_hash: str
    schema_version: str
    source_profile_set_version: str
    mapping_set_version: str
    vocabulary_set_version: str
    scenario_catalog_version: str
    dataset_tier: BenchmarkTier
    split_id: SplitID
    seed_ledger_sha256: str

    def canonical_json(self) -> str:
        """Deterministic JSON serialization for hashing."""
        data = {
            "generator_version": self.generator_version,
            "generator_build_hash": self.generator_build_hash,
            "schema_version": self.schema_version,
            "source_profile_set_version": self.source_profile_set_version,
            "mapping_set_version": self.mapping_set_version,
            "vocabulary_set_version": self.vocabulary_set_version,
            "scenario_catalog_version": self.scenario_catalog_version,
            "dataset_tier": self.dataset_tier.value,
            "split_id": self.split_id.value,
            "seed_ledger_sha256": self.seed_ledger_sha256,
        }
        return json.dumps(data, sort_keys=True, ensure_ascii=True, separators=(",", ":"))

    def sha256(self) -> str:
        """SHA-256 hash of the canonical JSON representation."""
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class BuildContext:
    """Immutable context for a single generation run.

    Created once at initialization and passed to every stage. Stages
    receive this as a read-only reference — they cannot modify any field.

    Attributes:
        version: The frozen version tuple identifying this build.
        config_hash: SHA-256 of the frozen effective configuration.
        output_root: Root directory for all generated output.
        operational_root: Output path for operational evidence package.
        truth_root: Output path for hidden ground-truth package.
        evaluation_root: Output path for private evaluation package.
        binding_root: Output path for private binding manifest.
        dataset_namespace: UUID namespace for deterministic ID generation.
        created_at_utc: Build creation timestamp (excluded from hashed content).
        metadata: Additional frozen key-value metadata.
    """

    version: VersionTuple
    config_hash: str
    output_root: Path
    operational_root: Path
    truth_root: Path
    evaluation_root: Path
    binding_root: Path
    dataset_namespace: str
    created_at_utc: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate physical path separation between package domains."""
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
        roots = {
            PackageDomain.OPERATIONAL: self.operational_root,
            PackageDomain.GROUND_TRUTH: self.truth_root,
            PackageDomain.EVALUATION: self.evaluation_root,
            PackageDomain.BINDING: self.binding_root,
        }
        resolved = {domain: root.resolve() for domain, root in roots.items()}

        # No domain root may be nested inside another
        for domain_a, path_a in resolved.items():
            for domain_b, path_b in resolved.items():
                if domain_a == domain_b:
                    continue
                if path_a == path_b or _is_subpath(path_a, path_b):
                    from satsa_generator.core.errors import ConfigurationError

                    raise ConfigurationError(
                        f"Package domain roots must be physically separate: "
                        f"{domain_a.value} ({path_a}) overlaps with "
                        f"{domain_b.value} ({path_b})",
                        context={"domain_a": domain_a.value, "domain_b": domain_b.value},
                    )


def _is_subpath(child: Path, parent: Path) -> bool:
    """Check if child is a proper subdirectory of parent."""
    try:
        child.relative_to(parent)
        return child != parent
    except ValueError:
        return False
