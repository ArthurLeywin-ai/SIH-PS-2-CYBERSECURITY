"""
Typed configuration models using Pydantic v2.

These models validate the generator configuration at load time, ensuring
fail-fast behavior for invalid or contradictory settings. Every configuration
snapshot is frozen and hashed before generation begins.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from satsa_generator.core.types import BenchmarkTier, SourceProfile, SplitID

# -----------------------------------------------------------------------
# Forbidden detector configuration keys
# -----------------------------------------------------------------------

FORBIDDEN_CONFIG_KEYS: frozenset[str] = frozenset(
    {
        "detector_threshold",
        "finding_priority_weight",
        "anomaly_contamination",
        "model_parameter",
        "expected_score",
        "risk_score",
        "detection_rule",
        "priority_band",
        "ml_threshold",
        "anomaly_threshold",
    }
)


class StrictFrozenModel(BaseModel):
    """Base for immutable, typo-intolerant generator configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class PeriodConfig(StrictFrozenModel):
    """Configuration for a single reporting period."""

    period_id: str = Field(
        ...,
        pattern=r"^P\d{2}$",
        description="Period identifier (e.g., P01, P02, ..., P06)",
    )
    start_utc: str = Field(
        ...,
        description="ISO 8601 UTC start timestamp",
    )
    end_utc: str = Field(
        ...,
        description="ISO 8601 UTC end timestamp (exclusive)",
    )
    description: str = Field(
        default="",
        description="Human-readable period description",
    )

    @model_validator(mode="after")
    def validate_interval(self) -> PeriodConfig:
        """Require timezone-aware UTC timestamps and a positive interval."""
        start = _parse_utc(self.start_utc, "start_utc")
        end = _parse_utc(self.end_utc, "end_utc")
        if end <= start:
            raise ValueError("end_utc must be later than start_utc")
        return self


class OrganizationConfig(StrictFrozenModel):
    """Configuration for a synthetic organization's public profile."""

    org_id: str = Field(
        ...,
        pattern=r"^CSE-\d{3}$",
        description="Synthetic organization identifier (e.g., CSE-001)",
    )
    name: str = Field(
        ...,
        min_length=1,
        description="Obviously fictional organization name",
    )
    cohort: str = Field(
        ...,
        pattern=r"^COHORT-[A-Z]$",
        description="Primary peer cohort assignment",
    )
    sector: str = Field(
        ...,
        description="Synthetic sector identifier",
    )
    source_profile: SourceProfile = Field(
        ...,
        description="Assigned source layout profile",
    )
    scale_band: str = Field(
        ...,
        description="Organization scale band (e.g., 'small', 'medium', 'large', 'very_large')",
    )
    operating_model: str = Field(
        ...,
        description="Operating model (e.g., 'centralized_24x7', 'hybrid', 'distributed')",
    )


class GeneratorConfig(StrictFrozenModel):
    """Top-level generator configuration.

    This is the root configuration model that aggregates all sub-configurations.
    It enforces structural validity, reference resolution, and the prohibition
    on detector-related keys.
    """

    # Identity and versioning
    dataset_namespace: str = Field(
        ...,
        description="UUID namespace for deterministic ID generation",
    )
    generator_version: str = Field(
        default="0.1.0",
        description="Generator software version",
    )
    schema_version: str = Field(
        default="0.1.0",
        description="Canonical schema version from DATA_SCHEMA.md",
    )
    source_profile_set_version: str = Field(
        default="0.1.0",
        description="Source profile set version",
    )
    mapping_set_version: str = Field(
        default="0.1.0",
        description="Vocabulary mapping set version",
    )
    vocabulary_set_version: str = Field(
        default="0.1.0",
        description="Controlled vocabulary set version",
    )
    scenario_catalog_version: str = Field(
        default="0.1.0",
        description="Scenario catalog version",
    )
    seed_derivation_version: str = Field(
        default="hmac-sha256-pcg64dxsm-v1",
        pattern=r"^[a-z0-9][a-z0-9._-]{0,63}$",
        description="Versioned named-stream derivation algorithm",
    )

    # Build parameters
    tier: BenchmarkTier = Field(
        default=BenchmarkTier.DETERMINISTIC_FIXTURE,
        description="Benchmark volume tier",
    )
    split: SplitID = Field(
        default=SplitID.DEVELOPMENT,
        description="Dataset split identifier",
    )

    # Paths
    output_root: str = Field(
        default="./output",
        description="Root directory for all generated output",
    )

    # Population
    organizations: tuple[OrganizationConfig, ...] = Field(
        ...,
        min_length=1,
        description="Synthetic organization configurations",
    )

    # Periods
    periods: tuple[PeriodConfig, ...] = Field(
        ...,
        min_length=1,
        description="Reporting period configurations",
    )

    # Safety limits
    max_alerts_per_org_period: int = Field(
        default=50000,
        ge=0,
        description="Safety limit on alerts per organization-period",
    )
    max_text_length: int = Field(
        default=4096,
        ge=64,
        description="Maximum text field length in characters",
    )

    @field_validator("dataset_namespace")
    @classmethod
    def validate_dataset_namespace(cls, value: str) -> str:
        """Require a canonical UUID namespace."""
        try:
            return str(uuid.UUID(value))
        except (ValueError, AttributeError) as exc:
            raise ValueError("dataset_namespace must be a valid UUID") from exc

    @field_validator("output_root")
    @classmethod
    def validate_portable_output_root(cls, value: str) -> str:
        """Keep committed configuration free of machine-specific paths."""
        path = Path(value)
        if not value.strip():
            raise ValueError("output_root must not be empty")
        if path.is_absolute():
            raise ValueError(
                "output_root in versioned configuration must be relative; "
                "use the CLI output override for an absolute runtime path"
            )
        if ".." in path.parts:
            raise ValueError("output_root must not traverse outside the build workspace")
        return value

    @field_validator("organizations")
    @classmethod
    def validate_unique_org_ids(
        cls, v: tuple[OrganizationConfig, ...]
    ) -> tuple[OrganizationConfig, ...]:
        """Ensure organization IDs are unique."""
        ids = [org.org_id for org in v]
        if len(ids) != len(set(ids)):
            duplicates = [oid for oid in ids if ids.count(oid) > 1]
            raise ValueError(f"Duplicate organization IDs: {set(duplicates)}")
        return v

    @field_validator("periods")
    @classmethod
    def validate_unique_period_ids(cls, v: tuple[PeriodConfig, ...]) -> tuple[PeriodConfig, ...]:
        """Ensure period IDs are unique."""
        ids = [p.period_id for p in v]
        if len(ids) != len(set(ids)):
            duplicates = [pid for pid in ids if ids.count(pid) > 1]
            raise ValueError(f"Duplicate period IDs: {set(duplicates)}")
        return v

    @model_validator(mode="before")
    @classmethod
    def reject_forbidden_keys(cls, data: Any) -> Any:
        """Reject any configuration keys that reference detector thresholds.

        From GENERATOR_IMPLEMENTATION_PLAN §4.5: Configuration schema has no keys
        named for detector thresholds, finding priority weights, anomaly
        contamination, model parameters, or expected SAT-SA scores.
        """
        if isinstance(data, dict):
            _scan_for_forbidden_keys(data, path="")
        return data

    def canonical_json(self) -> str:
        """Produce deterministic JSON representation for hashing.

        Key order is sorted, encoding is ASCII-safe, and separators are compact.
        This ensures identical configs produce identical hashes regardless of
        dict iteration order.
        """
        data = self.model_dump(mode="json")
        return json.dumps(data, sort_keys=True, ensure_ascii=True, separators=(",", ":"))

    def config_hash(self) -> str:
        """SHA-256 of the canonical JSON configuration."""
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def _scan_for_forbidden_keys(data: dict[str, Any], path: str) -> None:
    """Recursively scan configuration dict for forbidden detector keys."""
    from satsa_generator.core.errors import ConfigurationError

    for key, value in data.items():
        full_path = f"{path}.{key}" if path else key
        normalized_key = key.lower().replace("-", "_")
        if normalized_key in FORBIDDEN_CONFIG_KEYS:
            raise ConfigurationError(
                f"Forbidden detector-related configuration key: '{full_path}'. "
                f"Generator configuration must not import SAT-SA detector "
                f"thresholds, priority weights, or model parameters.",
                context={"key": full_path, "forbidden_set": list(FORBIDDEN_CONFIG_KEYS)},
            )
        if isinstance(value, dict):
            _scan_for_forbidden_keys(value, full_path)
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    _scan_for_forbidden_keys(item, f"{full_path}[{i}]")


def _parse_utc(value: str, field_name: str) -> datetime:
    """Parse an ISO-8601 timestamp and require an explicit UTC offset."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name} must include an explicit UTC offset")
    if parsed.utcoffset().total_seconds() != 0:
        raise ValueError(f"{field_name} must be normalized to UTC")
    return parsed


def load_config(config_path: Path) -> GeneratorConfig:
    """Load and validate generator configuration from a JSON or TOML file.

    Args:
        config_path: Path to configuration file.

    Returns:
        Validated and frozen GeneratorConfig.

    Raises:
        ConfigurationError: If the file is missing, unreadable, or invalid.
    """
    from satsa_generator.core.errors import ConfigurationError

    if not config_path.exists():
        raise ConfigurationError(
            f"Configuration file not found: {config_path}",
            context={"path": str(config_path)},
        )
    if not config_path.is_file():
        raise ConfigurationError(
            f"Configuration path is not a file: {config_path}",
            context={"path": str(config_path)},
        )

    suffix = config_path.suffix.lower()
    try:
        if suffix == ".json":
            raw = json.loads(config_path.read_text(encoding="utf-8"))
        elif suffix == ".toml":
            import tomllib

            raw = tomllib.loads(config_path.read_text(encoding="utf-8"))
        else:
            raise ConfigurationError(
                f"Unsupported configuration format: {suffix}. Use .json or .toml.",
                context={"path": str(config_path), "suffix": suffix},
            )
    except ConfigurationError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as e:
        raise ConfigurationError(
            f"Failed to parse configuration file: {config_path}: {e}",
            context={"path": str(config_path)},
        ) from e

    if not isinstance(raw, dict):
        raise ConfigurationError(
            "Configuration root must be an object/table.",
            context={"path": str(config_path), "received_type": type(raw).__name__},
        )

    try:
        return GeneratorConfig.model_validate(raw)
    except Exception as e:
        raise ConfigurationError(
            f"Configuration validation failed: {e}",
            context={"path": str(config_path)},
        ) from e


def freeze_config(config: GeneratorConfig) -> tuple[str, str]:
    """Freeze configuration and return (canonical_json, sha256_hash).

    This is step 4-7 of the freeze process from GENERATOR_IMPLEMENTATION_PLAN §4.4.
    After this call, no mutable config access is permitted during stages.
    """
    canonical = config.canonical_json()
    config_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return canonical, config_hash
