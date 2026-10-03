"""Build the tiny deterministic, operational-only Milestone 1 fixture."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from satsa_generator.config.models import GeneratorConfig, load_config
from satsa_generator.core.context import BuildContext, VersionTuple
from satsa_generator.core.errors import FixtureBuildError, SchemaContractError, SeedError
from satsa_generator.fixture.models import (
    FixtureManifest,
    OrganizationRecord,
    SubmissionManifestRecord,
    SubmissionRecord,
)
from satsa_generator.ids.service import IDService
from satsa_generator.seeds.manager import SeedManager

_FUTURE_FAMILIES = (
    "asset",
    "monitoring_coverage",
    "alert",
    "case",
    "investigation",
    "escalation",
    "action",
    "resolution",
    "closure",
)


@dataclass(frozen=True)
class FixtureBuildResult:
    """Paths and hashes returned by a successful fixture build."""

    output_root: Path
    operational_root: Path
    manifest_path: Path
    tree_sha256: str
    record_counts: dict[str, int]


def parse_master_seed_hex(value: str) -> bytes:
    """Parse exactly 256 bits from a hexadecimal CLI/environment value."""
    if len(value) != 64:
        raise SeedError("Master seed must be exactly 64 hexadecimal characters.")
    try:
        seed = bytes.fromhex(value)
    except ValueError as exc:
        raise SeedError("Master seed must contain hexadecimal characters only.") from exc
    if len(seed) != 32:
        raise SeedError("Master seed must decode to exactly 32 bytes.")
    return seed


def build_fixture(
    config_path: Path,
    master_seed: bytes,
    *,
    output_root: Path | None = None,
) -> FixtureBuildResult:
    """Build a tiny deterministic fixture without truth or scenario metadata."""
    config = load_config(config_path)
    if config.tier.value != "deterministic_fixture":
        raise FixtureBuildError(
            "The Milestone 1 fixture builder only accepts tier=deterministic_fixture."
        )

    root = output_root if output_root is not None else Path(config.output_root)
    root = root.expanduser()
    _require_empty_output_root(root)

    operational_root = root / "operational_evidence"
    seeds = SeedManager(master_seed)
    ids = IDService(config.dataset_namespace)
    organizations, submissions, submission_manifests = _generate_records(
        config, seeds, ids
    )
    validate_fixture_records(organizations, submissions, submission_manifests)
    context = _make_context(config, root, seeds.private_ledger_hash())

    payloads = {
        "organizations.json": _serialize_records(organizations),
        "submission_manifests.json": _serialize_records(submission_manifests),
        "submissions.json": _serialize_records(submissions),
    }
    files = [
        {
            "path": name,
            "byte_size": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        }
        for name, content in sorted(payloads.items())
    ]
    record_counts = {
        "organization": len(organizations),
        "submission": len(submissions),
        "submission_manifest": len(submission_manifests),
    }
    manifest = FixtureManifest(
        fixture_contract="SATSA-M1-FIXTURE-V1",
        dataset_id=ids.generate("dataset", config.tier.value, config.split.value),
        dataset_version=(
            f"{config.generator_version}-m1-{context.version.sha256()[:12]}"
        ),
        generator_version=config.generator_version,
        generator_build_hash=context.version.generator_build_hash,
        schema_version=config.schema_version,
        config_sha256=context.config_hash,
        version_tuple_sha256=context.version.sha256(),
        seed_derivation_version=config.seed_derivation_version,
        stream_fingerprints=seeds.public_ledger(),
        created_at_utc=_deterministic_build_time(config),
        record_counts=record_counts,
        files=files,
    )
    manifest_bytes = _serialize_object(manifest.model_dump(mode="json"))

    operational_root.mkdir(parents=True, exist_ok=False)
    for name, content in payloads.items():
        (operational_root / name).write_bytes(content)
    manifest_path = operational_root / "fixture_manifest.json"
    manifest_path.write_bytes(manifest_bytes)

    tree_sha256 = _tree_hash(operational_root)
    return FixtureBuildResult(
        output_root=root,
        operational_root=operational_root,
        manifest_path=manifest_path,
        tree_sha256=tree_sha256,
        record_counts=record_counts,
    )


def validate_fixture_records(
    organizations: Sequence[OrganizationRecord],
    submissions: Sequence[SubmissionRecord],
    manifests: Sequence[SubmissionManifestRecord],
) -> None:
    """Fail loudly on duplicate IDs, broken ownership, or broken manifest links."""
    if not organizations or not submissions or not manifests:
        raise SchemaContractError("Fixture record families must not be empty.")

    organization_ids = [str(record.organization_id) for record in organizations]
    submission_ids = [str(record.submission_id) for record in submissions]
    manifest_ids = [str(record.manifest_id) for record in manifests]
    _require_unique("organization_id", organization_ids)
    _require_unique("submission_id", submission_ids)
    _require_unique("manifest_id", manifest_ids)

    organization_set = set(organization_ids)
    submission_set = set(submission_ids)
    manifest_by_id = {str(record.manifest_id): record for record in manifests}
    for submission in submissions:
        if str(submission.organization_id) not in organization_set:
            raise SchemaContractError(
                f"Submission {submission.submission_id} references unknown organization."
            )
        manifest = manifest_by_id.get(str(submission.manifest_id))
        if manifest is None:
            raise SchemaContractError(
                f"Submission {submission.submission_id} references unknown manifest."
            )
        if manifest.submission_id != submission.submission_id:
            raise SchemaContractError(
                f"Manifest {manifest.manifest_id} belongs to a different submission."
            )
    for manifest in manifests:
        if str(manifest.submission_id) not in submission_set:
            raise SchemaContractError(
                f"Manifest {manifest.manifest_id} references unknown submission."
            )


def _generate_records(
    config: GeneratorConfig,
    seeds: SeedManager,
    ids: IDService,
) -> tuple[
    list[OrganizationRecord],
    list[SubmissionRecord],
    list[SubmissionManifestRecord],
]:
    organizations: list[OrganizationRecord] = []
    submissions: list[SubmissionRecord] = []
    manifests: list[SubmissionManifestRecord] = []
    profile_start = min(_parse_timestamp(period.start_utc) for period in config.periods)
    empty_files_hash = hashlib.sha256(b"[]\n").hexdigest()
    actor_id = ids.generate("actor", "fixture-generator")

    for org in sorted(config.organizations, key=lambda item: item.org_id):
        profile_rng = seeds.get_rng(
            f"{config.split.value}/fixture/{org.org_id}/profile/v1"
        )
        low, high = {
            "small": (20, 80),
            "medium": (80, 240),
            "large": (240, 700),
            "very_large": (700, 1500),
        }.get(org.scale_band.lower(), (40, 160))
        asset_count = int(profile_rng.integers(low, high + 1))
        critical_count = int(
            profile_rng.integers(max(1, asset_count // 20), max(2, asset_count // 5))
        )
        organization_id = ids.generate("organization", org.org_id)
        organizations.append(
            OrganizationRecord(
                organization_id=organization_id,
                source_organization_id=org.org_id,
                organization_name=org.name,
                organization_alias=org.org_id,
                sector_code=org.sector,
                scale_band=org.scale_band.upper(),
                operating_model=org.operating_model.upper(),
                entity_criticality_band="ELEVATED",
                asset_count_declared=asset_count,
                critical_asset_count_declared=critical_count,
                profile_effective_start_at_utc=profile_start,
                profile_version=1,
                organization_status="ACTIVE",
            )
        )

        for period in sorted(config.periods, key=lambda item: item.period_id):
            period_end = _parse_timestamp(period.end_utc)
            timing_rng = seeds.get_rng(
                f"{config.split.value}/fixture/{org.org_id}/{period.period_id}/"
                "submission/timing/v1"
            )
            submitted_at = period_end + timedelta(
                hours=int(timing_rng.integers(8, 49))
            )
            received_at = submitted_at + timedelta(
                minutes=int(timing_rng.integers(5, 181))
            )
            submission_id = ids.generate(
                "submission", org.org_id, period.period_id, "v1"
            )
            manifest_id = ids.generate(
                "submission_manifest", org.org_id, period.period_id, "v1"
            )
            submissions.append(
                SubmissionRecord(
                    submission_id=submission_id,
                    source_submission_id=f"SUB-{org.org_id}-{period.period_id}-01",
                    organization_id=organization_id,
                    reporting_period_start_at_utc=_parse_timestamp(period.start_utc),
                    reporting_period_end_at_utc=period_end,
                    submitted_at_utc=submitted_at,
                    received_at_utc=received_at,
                    source_system_set_id=org.source_profile.value,
                    source_system_versions={org.source_profile.value: "fixture-v1"},
                    declared_completeness="DECLARED_PARTIAL",
                    declared_missing_families=[
                        {
                            "evidence_family": family,
                            "reason": "Not generated in the Milestone 1 foundation fixture.",
                        }
                        for family in _FUTURE_FAMILIES
                    ],
                    submission_status="CONDITIONALLY_ACCEPTED",
                    period_maturity_state="MATURE",
                    manifest_id=manifest_id,
                    schema_profile_id=ids.generate(
                        "schema_profile", org.source_profile.value, "v1"
                    ),
                    submission_notes=(
                        "Synthetic Milestone 1 foundation fixture; "
                        "later evidence families are intentionally absent."
                    ),
                    submission_quality_state="INCOMPLETE",
                )
            )
            manifests.append(
                SubmissionManifestRecord(
                    manifest_id=manifest_id,
                    submission_id=submission_id,
                    manifest_version=1,
                    created_at_utc=received_at,
                    file_count=0,
                    total_bytes=0,
                    manifest_sha256=empty_files_hash,
                    ingestion_run_id=ids.generate(
                        "ingestion_run", org.org_id, period.period_id, "v1"
                    ),
                    created_by_actor_id=actor_id,
                )
            )

    return organizations, submissions, manifests


def _make_context(
    config: GeneratorConfig, root: Path, seed_ledger_sha256: str
) -> BuildContext:
    build_hash = _generator_source_hash()
    version = VersionTuple(
        generator_version=config.generator_version,
        generator_build_hash=build_hash,
        schema_version=config.schema_version,
        source_profile_set_version=config.source_profile_set_version,
        mapping_set_version=config.mapping_set_version,
        vocabulary_set_version=config.vocabulary_set_version,
        scenario_catalog_version=config.scenario_catalog_version,
        dataset_tier=config.tier,
        split_id=config.split,
        seed_ledger_sha256=seed_ledger_sha256,
    )
    return BuildContext(
        version=version,
        config_hash=config.config_hash(),
        output_root=root,
        operational_root=root / "operational_evidence",
        truth_root=root / "ground_truth_private",
        evaluation_root=root / "evaluation_private",
        binding_root=root / "binding_private",
        dataset_namespace=config.dataset_namespace,
        created_at_utc=_deterministic_build_time(config),
        metadata={"fixture_contract": "SATSA-M1-FIXTURE-V1"},
    )


def _generator_source_hash() -> str:
    package_root = Path(__file__).resolve().parents[1]
    digest = hashlib.sha256()
    for path in sorted(package_root.rglob("*.py")):
        relative = path.relative_to(package_root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        content = path.read_bytes()
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def _deterministic_build_time(config: GeneratorConfig) -> datetime:
    latest = max(_parse_timestamp(period.end_utc) for period in config.periods)
    return latest + timedelta(days=7)


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone(UTC)


def _serialize_records(records: Sequence[Any]) -> bytes:
    ordered = sorted(
        (record.model_dump(mode="json") for record in records),
        key=lambda item: next(
            str(item[key])
            for key in ("organization_id", "submission_id", "manifest_id")
            if key in item
        ),
    )
    return _serialize_object(ordered)


def _serialize_object(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        content = path.read_bytes()
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def _require_empty_output_root(root: Path) -> None:
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise FixtureBuildError(
            f"Output root must not exist or must be empty: {root}. "
            "The fixture builder never silently overwrites existing artifacts."
        )


def _require_unique(field: str, values: Sequence[str]) -> None:
    if len(values) != len(set(values)):
        raise SchemaContractError(f"Fixture contains duplicate {field} values.")
