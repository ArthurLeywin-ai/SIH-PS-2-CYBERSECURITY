"""Deterministic operational fixture builders for Milestones 1 and 2."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from satsa_generator.config.models import GeneratorConfig, load_config
from satsa_generator.core.context import BuildContext, VersionTuple
from satsa_generator.core.errors import (
    FixtureBuildError,
    RelationshipIntegrityError,
    SchemaContractError,
    SeedError,
    TemporalIntegrityError,
)
from satsa_generator.fixture.models import (
    ActionRecord,
    AlertRecord,
    AssetRecord,
    CaseAlertLinkRecord,
    CaseRecord,
    ClosureRecord,
    ControlProcessReferenceRecord,
    ControlProcessSubjectLinkRecord,
    EscalationRecord,
    ExceptionRecord,
    FixtureManifest,
    InvestigationRecord,
    MonitoringCoverageRecord,
    OrganizationRecord,
    ProcessChangeRecord,
    ResolutionRecord,
    SubmissionFamilyDeclarationRecord,
    SubmissionManifestRecord,
    SubmissionRecord,
)
from satsa_generator.ids.service import IDService
from satsa_generator.seeds.manager import SeedManager

_M1_FUTURE_FAMILIES = (
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

_PRIMARY_ID_KEYS = (
    "organization_id",
    "submission_id",
    "manifest_id",
    "submission_family_id",
    "control_process_ref_id",
    "control_process_link_id",
    "asset_id",
    "monitoring_coverage_id",
    "alert_id",
    "case_id",
    "case_alert_link_id",
    "investigation_id",
    "escalation_id",
    "action_id",
    "resolution_id",
    "closure_id",
    "exception_id",
    "process_change_id",
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
    milestone: Literal["m1", "m2", "m3"] = "m1",
) -> FixtureBuildResult:
    """Build a deterministic fixture without truth or scenario metadata."""
    if milestone == "m3":
        return _build_m3_fixture_internal(config_path, master_seed, output_root=output_root)
    elif milestone == "m2":
        return _build_m2_fixture_internal(config_path, master_seed, output_root=output_root)
    return _build_m1_fixture_internal(config_path, master_seed, output_root=output_root)


def build_m2_fixture(
    config_path: Path,
    master_seed: bytes,
    *,
    output_root: Path | None = None,
) -> FixtureBuildResult:
    """Convenience function to build Milestone 2 small base-world fixture."""
    return build_fixture(config_path, master_seed, output_root=output_root, milestone="m2")


def build_m3_fixture(
    config_path: Path,
    master_seed: bytes,
    *,
    output_root: Path | None = None,
) -> FixtureBuildResult:
    """Convenience function to build Milestone 3 source rendering fixture."""
    return build_fixture(config_path, master_seed, output_root=output_root, milestone="m3")


def _build_m1_fixture_internal(
    config_path: Path,
    master_seed: bytes,
    *,
    output_root: Path | None = None,
) -> FixtureBuildResult:
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
    organizations, submissions, submission_manifests = _generate_m1_records(config, seeds, ids)
    validate_fixture_records(organizations, submissions, submission_manifests)
    context = _make_context(
        config, root, seeds.private_ledger_hash(), contract="SATSA-M1-FIXTURE-V1"
    )

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
        dataset_version=f"{config.generator_version}-m1-{context.version.sha256()[:12]}",
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


def _build_m2_fixture_internal(
    config_path: Path,
    master_seed: bytes,
    *,
    output_root: Path | None = None,
) -> FixtureBuildResult:
    config = load_config(config_path)
    if config.tier.value != "deterministic_fixture":
        raise FixtureBuildError(
            "The Milestone 2 fixture builder only accepts tier=deterministic_fixture."
        )

    root = output_root if output_root is not None else Path(config.output_root)
    root = root.expanduser()
    _require_empty_output_root(root)

    operational_root = root / "operational_evidence"
    seeds = SeedManager(master_seed)
    ids = IDService(config.dataset_namespace)

    records = _generate_m2_records(config, seeds, ids)
    validate_m2_fixture_records(*records)

    (
        organizations,
        submissions,
        submission_manifests,
        submission_families,
        control_refs,
        control_links,
        assets,
        coverages,
        alerts,
        cases,
        case_alert_links,
        investigations,
        escalations,
        actions,
        resolutions,
        closures,
        exceptions,
        process_changes,
    ) = records

    context = _make_context(
        config, root, seeds.private_ledger_hash(), contract="SATSA-M2-FIXTURE-V1"
    )

    payloads = {
        "organizations.json": _serialize_records(organizations),
        "submissions.json": _serialize_records(submissions),
        "submission_manifests.json": _serialize_records(submission_manifests),
        "submission_evidence_families.json": _serialize_records(submission_families),
        "control_process_references.json": _serialize_records(control_refs),
        "control_process_subject_links.json": _serialize_records(control_links),
        "assets.json": _serialize_records(assets),
        "monitoring_coverage.json": _serialize_records(coverages),
        "alerts.json": _serialize_records(alerts),
        "cases.json": _serialize_records(cases),
        "case_alert_links.json": _serialize_records(case_alert_links),
        "investigations.json": _serialize_records(investigations),
        "escalations.json": _serialize_records(escalations),
        "actions.json": _serialize_records(actions),
        "resolutions.json": _serialize_records(resolutions),
        "closures.json": _serialize_records(closures),
        "exceptions.json": _serialize_records(exceptions),
        "process_changes.json": _serialize_records(process_changes),
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
        "submission_evidence_family": len(submission_families),
        "control_process_reference": len(control_refs),
        "control_process_subject_link": len(control_links),
        "asset": len(assets),
        "monitoring_coverage": len(coverages),
        "alert": len(alerts),
        "case": len(cases),
        "case_alert_link": len(case_alert_links),
        "investigation": len(investigations),
        "escalation": len(escalations),
        "action": len(actions),
        "resolution": len(resolutions),
        "closure": len(closures),
        "exception": len(exceptions),
        "process_change": len(process_changes),
    }

    manifest = FixtureManifest(
        fixture_contract="SATSA-M2-FIXTURE-V1",
        dataset_id=ids.generate("dataset", config.tier.value, config.split.value),
        dataset_version=f"{config.generator_version}-m2-{context.version.sha256()[:12]}",
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


def _build_m3_fixture_internal(
    config_path: Path,
    master_seed: bytes,
    *,
    output_root: Path | None = None,
) -> FixtureBuildResult:
    config = load_config(config_path)
    if config.tier.value != "deterministic_fixture":
        raise FixtureBuildError(
            "The Milestone 3 fixture builder only accepts tier=deterministic_fixture."
        )

    root = output_root if output_root is not None else Path(config.output_root)
    root = root.expanduser()
    _require_empty_output_root(root)

    source_exports_root = root / "source_exports"
    oracle_root = root / "canonical_reference"

    seeds = SeedManager(master_seed)
    ids = IDService(config.dataset_namespace)

    records = _generate_m2_records(config, seeds, ids)
    validate_m2_fixture_records(*records)

    (
        organizations,
        submissions,
        submission_manifests,
        submission_families,
        control_refs,
        control_links,
        assets,
        coverages,
        alerts,
        cases,
        case_alert_links,
        investigations,
        escalations,
        actions,
        resolutions,
        closures,
        exceptions,
        process_changes,
    ) = records

    context = _make_context(
        config, root, seeds.private_ledger_hash(), contract="SATSA-M3-FIXTURE-V1"
    )

    from satsa_generator.profiles.catalog import get_profile
    from satsa_generator.rendering.engine import RenderingEngine

    # We will simulate heterogeneous sources by assigning different records to different profiles
    # For now, let's use SRC-A for most, SRC-C for cases, etc. to demonstrate heterogeneity
    profile_a = get_profile("SRC-A")
    profile_b = get_profile("SRC-B")
    profile_c = get_profile("SRC-C")
    profile_d = get_profile("SRC-D")
    profile_e = get_profile("SRC-E")

    engine_a = RenderingEngine(source_exports_root, profile_a)
    engine_b = RenderingEngine(source_exports_root, profile_b)
    engine_c = RenderingEngine(source_exports_root, profile_c)
    engine_d = RenderingEngine(source_exports_root, profile_d)
    engine_e = RenderingEngine(source_exports_root, profile_e)

    file_manifests = []

    f_org = engine_a.render_and_write("organization", organizations)
    if f_org:
        file_manifests.append(f_org)

    f_sub = engine_b.render_and_write("submission", submissions)
    if f_sub:
        file_manifests.append(f_sub)

    f_man = engine_c.render_and_write("submission_manifest", submission_manifests)
    if f_man:
        file_manifests.append(f_man)

    f_fam = engine_d.render_and_write("submission_family", submission_families)
    if f_fam:
        file_manifests.append(f_fam)

    f_cr = engine_e.render_and_write("control_process_reference", control_refs)
    if f_cr:
        file_manifests.append(f_cr)

    f_cl = engine_a.render_and_write("control_process_subject_link", control_links)
    if f_cl:
        file_manifests.append(f_cl)

    f_asset = engine_b.render_and_write("asset", assets)
    if f_asset:
        file_manifests.append(f_asset)

    f_cov = engine_c.render_and_write("monitoring_coverage", coverages)
    if f_cov:
        file_manifests.append(f_cov)

    f_al = engine_d.render_and_write("alert", alerts)
    if f_al:
        file_manifests.append(f_al)

    f_ca = engine_c.render_and_write("case", cases)
    if f_ca:
        file_manifests.append(f_ca)

    f_cal = engine_c.render_and_write("case_alert_link", case_alert_links)
    if f_cal:
        file_manifests.append(f_cal)

    f_inv = engine_a.render_and_write("investigation", investigations)
    if f_inv:
        file_manifests.append(f_inv)

    f_esc = engine_b.render_and_write("escalation", escalations)
    if f_esc:
        file_manifests.append(f_esc)

    f_act = engine_c.render_and_write("action", actions)
    if f_act:
        file_manifests.append(f_act)

    f_res = engine_a.render_and_write("resolution", resolutions)
    if f_res:
        file_manifests.append(f_res)

    f_clo = engine_b.render_and_write("closure", closures)
    if f_clo:
        file_manifests.append(f_clo)

    f_exc = engine_c.render_and_write("exception", exceptions)
    if f_exc:
        file_manifests.append(f_exc)

    f_pc = engine_a.render_and_write("process_change", process_changes)
    if f_pc:
        file_manifests.append(f_pc)

    # Write oracle and provenance metadata
    oracle_hash_a = engine_a.write_metadata(oracle_root, "src_a")
    oracle_hash_b = engine_b.write_metadata(oracle_root, "src_b")
    oracle_hash_c = engine_c.write_metadata(oracle_root, "src_c")
    oracle_hash_d = engine_d.write_metadata(oracle_root, "src_d")
    oracle_hash_e = engine_e.write_metadata(oracle_root, "src_e")

    record_counts = {
        "organization": len(organizations),
        "submission": len(submissions),
        "submission_manifest": len(submission_manifests),
        "submission_evidence_family": len(submission_families),
        "control_process_reference": len(control_refs),
        "control_process_subject_link": len(control_links),
        "asset": len(assets),
        "monitoring_coverage": len(coverages),
        "alert": len(alerts),
        "case": len(cases),
        "case_alert_link": len(case_alert_links),
        "investigation": len(investigations),
        "escalation": len(escalations),
        "action": len(actions),
        "resolution": len(resolutions),
        "closure": len(closures),
        "exception": len(exceptions),
        "process_change": len(process_changes),
    }

    manifest = FixtureManifest(
        fixture_contract="SATSA-M2-FIXTURE-V1",  # Assuming M2 schema still holds for counting
        dataset_id=ids.generate("dataset", config.tier.value, config.split.value),
        dataset_version=f"{config.generator_version}-m3-{context.version.sha256()[:12]}",
        generator_version=config.generator_version,
        generator_build_hash=context.version.generator_build_hash,
        schema_version=config.schema_version,
        config_sha256=context.config_hash,
        version_tuple_sha256=context.version.sha256(),
        seed_derivation_version=config.seed_derivation_version,
        stream_fingerprints=seeds.public_ledger(),
        created_at_utc=_deterministic_build_time(config),
        record_counts=record_counts,
        files=file_manifests,
    )

    manifest_bytes = _serialize_object(manifest.model_dump(mode="json"))
    manifest_path = source_exports_root / "fixture_manifest.json"
    manifest_path.write_bytes(manifest_bytes)

    tree_sha256 = _tree_hash(source_exports_root)
    return FixtureBuildResult(
        output_root=root,
        operational_root=source_exports_root,
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


def validate_m2_fixture_records(
    organizations: Sequence[OrganizationRecord],
    submissions: Sequence[SubmissionRecord],
    submission_manifests: Sequence[SubmissionManifestRecord],
    submission_families: Sequence[SubmissionFamilyDeclarationRecord],
    control_refs: Sequence[ControlProcessReferenceRecord],
    control_links: Sequence[ControlProcessSubjectLinkRecord],
    assets: Sequence[AssetRecord],
    coverages: Sequence[MonitoringCoverageRecord],
    alerts: Sequence[AlertRecord],
    cases: Sequence[CaseRecord],
    case_alert_links: Sequence[CaseAlertLinkRecord],
    investigations: Sequence[InvestigationRecord],
    escalations: Sequence[EscalationRecord],
    actions: Sequence[ActionRecord],
    resolutions: Sequence[ResolutionRecord],
    closures: Sequence[ClosureRecord],
    exceptions: Sequence[ExceptionRecord],
    process_changes: Sequence[ProcessChangeRecord],
) -> None:
    """Validate referential integrity, cardinalities, and temporal ordering for M2."""
    all_families = (
        ("organization", organizations),
        ("submission", submissions),
        ("submission_manifest", submission_manifests),
        ("submission_family", submission_families),
        ("control_process_reference", control_refs),
        ("control_process_subject_link", control_links),
        ("asset", assets),
        ("monitoring_coverage", coverages),
        ("alert", alerts),
        ("case", cases),
        ("case_alert_link", case_alert_links),
        ("investigation", investigations),
        ("escalation", escalations),
        ("action", actions),
        ("resolution", resolutions),
        ("closure", closures),
        ("exception", exceptions),
        ("process_change", process_changes),
    )
    for name, seq in all_families:
        if not seq:
            raise SchemaContractError(f"M2 operational family '{name}' must not be empty.")

    # Primary key uniqueness check
    _require_unique("organization_id", [str(r.organization_id) for r in organizations])
    _require_unique("submission_id", [str(r.submission_id) for r in submissions])
    _require_unique("manifest_id", [str(r.manifest_id) for r in submission_manifests])
    _require_unique(
        "submission_family_id", [str(r.submission_family_id) for r in submission_families]
    )
    _require_unique("control_process_ref_id", [str(r.control_process_ref_id) for r in control_refs])
    _require_unique(
        "control_process_link_id", [str(r.control_process_link_id) for r in control_links]
    )
    _require_unique("asset_id", [str(r.asset_id) for r in assets])
    _require_unique("monitoring_coverage_id", [str(r.monitoring_coverage_id) for r in coverages])
    _require_unique("alert_id", [str(r.alert_id) for r in alerts])
    _require_unique("case_id", [str(r.case_id) for r in cases])
    _require_unique("case_alert_link_id", [str(r.case_alert_link_id) for r in case_alert_links])
    _require_unique("investigation_id", [str(r.investigation_id) for r in investigations])
    _require_unique("escalation_id", [str(r.escalation_id) for r in escalations])
    _require_unique("action_id", [str(r.action_id) for r in actions])
    _require_unique("resolution_id", [str(r.resolution_id) for r in resolutions])
    _require_unique("closure_id", [str(r.closure_id) for r in closures])
    _require_unique("exception_id", [str(r.exception_id) for r in exceptions])
    _require_unique("process_change_id", [str(r.process_change_id) for r in process_changes])

    # Index maps
    org_map = {r.organization_id: r for r in organizations}
    sub_map = {r.submission_id: r for r in submissions}
    sub_man_map = {r.manifest_id: r for r in submission_manifests}
    asset_map = {r.asset_id: r for r in assets}
    alert_map = {r.alert_id: r for r in alerts}
    case_map = {r.case_id: r for r in cases}
    ctrl_ref_map = {r.control_process_ref_id: r for r in control_refs}
    res_map = {r.resolution_id: r for r in resolutions}

    # 1. Organization ownership & referential validation
    for sub in submissions:
        if sub.organization_id not in org_map:
            raise RelationshipIntegrityError(
                f"Submission {sub.submission_id} references unknown organization "
                f"{sub.organization_id}."
            )
        manifest = sub_man_map.get(sub.manifest_id)
        if manifest is None:
            raise RelationshipIntegrityError(
                f"Submission {sub.submission_id} references unknown manifest {sub.manifest_id}."
            )
        if manifest.submission_id != sub.submission_id:
            raise RelationshipIntegrityError(
                f"Manifest {manifest.manifest_id} links to submission "
                f"{manifest.submission_id}, expected {sub.submission_id}."
            )

    for fam in submission_families:
        if fam.submission_id not in sub_map:
            raise RelationshipIntegrityError(
                f"Submission family declaration {fam.submission_family_id} references "
                f"unknown submission {fam.submission_id}."
            )

    for ref in control_refs:
        if ref.organization_id is not None and ref.organization_id not in org_map:
            raise RelationshipIntegrityError(
                f"Control reference {ref.control_process_ref_id} references unknown "
                f"organization {ref.organization_id}."
            )

    for link in control_links:
        if link.control_process_ref_id not in ctrl_ref_map:
            raise RelationshipIntegrityError(
                f"Control link {link.control_process_link_id} references unknown "
                f"control reference {link.control_process_ref_id}."
            )
        if link.subject_type == "ORGANIZATION" and link.subject_id not in org_map:
            raise RelationshipIntegrityError(
                f"Control link references unknown organization subject {link.subject_id}."
            )
        elif link.subject_type == "ASSET" and link.subject_id not in asset_map:
            raise RelationshipIntegrityError(
                f"Control link references unknown asset subject {link.subject_id}."
            )

    for asset in assets:
        if asset.organization_id not in org_map:
            raise RelationshipIntegrityError(
                f"Asset {asset.asset_id} references unknown organization {asset.organization_id}."
            )

    for cov in coverages:
        if cov.organization_id not in org_map:
            raise RelationshipIntegrityError(
                f"Monitoring coverage {cov.monitoring_coverage_id} references unknown "
                f"organization {cov.organization_id}."
            )
        asset = asset_map.get(cov.asset_id)
        if asset is None:
            raise RelationshipIntegrityError(
                f"Monitoring coverage {cov.monitoring_coverage_id} references unknown "
                f"asset {cov.asset_id}."
            )
        if cov.organization_id != asset.organization_id:
            raise RelationshipIntegrityError(
                f"Monitoring coverage organization {cov.organization_id} does not match "
                f"asset organization {asset.organization_id}."
            )

    for alert in alerts:
        if alert.organization_id not in org_map:
            raise RelationshipIntegrityError(
                f"Alert {alert.alert_id} references unknown organization {alert.organization_id}."
            )
        if alert.asset_id is not None:
            asset = asset_map.get(alert.asset_id)
            if asset is None:
                raise RelationshipIntegrityError(
                    f"Alert {alert.alert_id} references unknown asset {alert.asset_id}."
                )
            if alert.organization_id != asset.organization_id:
                raise RelationshipIntegrityError(
                    f"Alert organization {alert.organization_id} does not match asset "
                    f"organization {asset.organization_id}."
                )

    for case in cases:
        if case.organization_id not in org_map:
            raise RelationshipIntegrityError(
                f"Case {case.case_id} references unknown organization {case.organization_id}."
            )

    for cal in case_alert_links:
        case = case_map.get(cal.case_id)
        if case is None:
            raise RelationshipIntegrityError(
                f"Case-Alert link {cal.case_alert_link_id} references unknown case {cal.case_id}."
            )
        alert = alert_map.get(cal.alert_id)
        if alert is None:
            raise RelationshipIntegrityError(
                f"Case-Alert link {cal.case_alert_link_id} references unknown alert {cal.alert_id}."
            )
        if case.organization_id != alert.organization_id:
            raise RelationshipIntegrityError(
                f"Case {case.case_id} organization {case.organization_id} does not match "
                f"alert {alert.alert_id} organization {alert.organization_id}."
            )

    for inv in investigations:
        if inv.organization_id not in org_map:
            raise RelationshipIntegrityError(
                f"Investigation {inv.investigation_id} references unknown "
                f"organization {inv.organization_id}."
            )
        if inv.case_id is not None:
            case = case_map.get(inv.case_id)
            if case is None:
                raise RelationshipIntegrityError(
                    f"Investigation {inv.investigation_id} references unknown case {inv.case_id}."
                )
            if inv.organization_id != case.organization_id:
                raise RelationshipIntegrityError(
                    f"Investigation organization {inv.organization_id} does not match "
                    f"case organization {case.organization_id}."
                )
        if inv.alert_id is not None:
            alert = alert_map.get(inv.alert_id)
            if alert is None:
                raise RelationshipIntegrityError(
                    f"Investigation {inv.investigation_id} references unknown alert {inv.alert_id}."
                )
            if inv.organization_id != alert.organization_id:
                raise RelationshipIntegrityError(
                    f"Investigation organization {inv.organization_id} does not match "
                    f"alert organization {alert.organization_id}."
                )

    for esc in escalations:
        if esc.organization_id not in org_map:
            raise RelationshipIntegrityError(
                f"Escalation {esc.escalation_id} references unknown organization "
                f"{esc.organization_id}."
            )
        if esc.case_id is not None:
            case = case_map.get(esc.case_id)
            if case is None:
                raise RelationshipIntegrityError(
                    f"Escalation {esc.escalation_id} references unknown case {esc.case_id}."
                )
            if esc.organization_id != case.organization_id:
                raise RelationshipIntegrityError(
                    f"Escalation organization {esc.organization_id} does not match "
                    f"case organization {case.organization_id}."
                )
        if esc.alert_id is not None:
            alert = alert_map.get(esc.alert_id)
            if alert is None:
                raise RelationshipIntegrityError(
                    f"Escalation {esc.escalation_id} references unknown alert {esc.alert_id}."
                )
            if esc.organization_id != alert.organization_id:
                raise RelationshipIntegrityError(
                    f"Escalation organization {esc.organization_id} does not match "
                    f"alert organization {alert.organization_id}."
                )

    for act in actions:
        if act.organization_id not in org_map:
            raise RelationshipIntegrityError(
                f"Action {act.action_id} references unknown organization {act.organization_id}."
            )
        if act.case_id is not None:
            case = case_map.get(act.case_id)
            if case is None:
                raise RelationshipIntegrityError(
                    f"Action {act.action_id} references unknown case {act.case_id}."
                )
            if act.organization_id != case.organization_id:
                raise RelationshipIntegrityError(
                    f"Action organization {act.organization_id} does not match case "
                    f"organization {case.organization_id}."
                )
        if act.alert_id is not None:
            alert = alert_map.get(act.alert_id)
            if alert is None:
                raise RelationshipIntegrityError(
                    f"Action {act.action_id} references unknown alert {act.alert_id}."
                )
            if act.organization_id != alert.organization_id:
                raise RelationshipIntegrityError(
                    f"Action organization {act.organization_id} does not match alert "
                    f"organization {alert.organization_id}."
                )
        if act.asset_id is not None:
            asset = asset_map.get(act.asset_id)
            if asset is None:
                raise RelationshipIntegrityError(
                    f"Action {act.action_id} references unknown asset {act.asset_id}."
                )
            if act.organization_id != asset.organization_id:
                raise RelationshipIntegrityError(
                    f"Action organization {act.organization_id} does not match asset "
                    f"organization {asset.organization_id}."
                )

    for res in resolutions:
        if res.organization_id not in org_map:
            raise RelationshipIntegrityError(
                f"Resolution {res.resolution_id} references unknown organization "
                f"{res.organization_id}."
            )
        if res.case_id is not None:
            case = case_map.get(res.case_id)
            if case is None:
                raise RelationshipIntegrityError(
                    f"Resolution {res.resolution_id} references unknown case {res.case_id}."
                )
            if res.organization_id != case.organization_id:
                raise RelationshipIntegrityError(
                    f"Resolution organization {res.organization_id} does not match "
                    f"case organization {case.organization_id}."
                )
        if res.alert_id is not None:
            alert = alert_map.get(res.alert_id)
            if alert is None:
                raise RelationshipIntegrityError(
                    f"Resolution {res.resolution_id} references unknown alert {res.alert_id}."
                )
            if res.organization_id != alert.organization_id:
                raise RelationshipIntegrityError(
                    f"Resolution organization {res.organization_id} does not match "
                    f"alert organization {alert.organization_id}."
                )

    for clo in closures:
        if clo.organization_id not in org_map:
            raise RelationshipIntegrityError(
                f"Closure {clo.closure_id} references unknown organization {clo.organization_id}."
            )
        if clo.case_id is not None:
            case = case_map.get(clo.case_id)
            if case is None:
                raise RelationshipIntegrityError(
                    f"Closure {clo.closure_id} references unknown case {clo.case_id}."
                )
            if clo.organization_id != case.organization_id:
                raise RelationshipIntegrityError(
                    f"Closure organization {clo.organization_id} does not match case "
                    f"organization {case.organization_id}."
                )
        if clo.alert_id is not None:
            alert = alert_map.get(clo.alert_id)
            if alert is None:
                raise RelationshipIntegrityError(
                    f"Closure {clo.closure_id} references unknown alert {clo.alert_id}."
                )
            if clo.organization_id != alert.organization_id:
                raise RelationshipIntegrityError(
                    f"Closure organization {clo.organization_id} does not match alert "
                    f"organization {alert.organization_id}."
                )
        if clo.resolution_id is not None:
            res = res_map.get(clo.resolution_id)
            if res is None:
                raise RelationshipIntegrityError(
                    f"Closure {clo.closure_id} references unknown resolution {clo.resolution_id}."
                )
            if clo.organization_id != res.organization_id:
                raise RelationshipIntegrityError(
                    f"Closure organization {clo.organization_id} does not match resolution "
                    f"organization {res.organization_id}."
                )

    for exc in exceptions:
        if exc.organization_id not in org_map:
            raise RelationshipIntegrityError(
                f"Exception {exc.exception_id} references unknown organization "
                f"{exc.organization_id}."
            )
        if exc.target_type == "ASSET" and exc.target_id is not None:
            asset = asset_map.get(exc.target_id)
            if asset is None:
                raise RelationshipIntegrityError(
                    f"Exception {exc.exception_id} references unknown asset target {exc.target_id}."
                )
            if exc.organization_id != asset.organization_id:
                raise RelationshipIntegrityError(
                    f"Exception organization {exc.organization_id} does not match "
                    f"asset target organization {asset.organization_id}."
                )

    for pc in process_changes:
        if pc.organization_id not in org_map:
            raise RelationshipIntegrityError(
                f"Process change {pc.process_change_id} references unknown "
                f"organization {pc.organization_id}."
            )

    # 2. Temporal ordering integrity validation
    for cal in case_alert_links:
        case = case_map[cal.case_id]
        alert = alert_map[cal.alert_id]
        if case.created_at_utc < alert.created_at_utc:
            raise TemporalIntegrityError(
                f"Case {case.case_id} was created at {case.created_at_utc.isoformat()} "
                f"before linked alert {alert.alert_id} created at "
                f"{alert.created_at_utc.isoformat()}."
            )

    for inv in investigations:
        if inv.case_id is not None:
            case = case_map[inv.case_id]
            if inv.started_at_utc < case.created_at_utc:
                raise TemporalIntegrityError(
                    f"Investigation {inv.investigation_id} started before case "
                    f"{case.case_id} was created."
                )
            if case.closed_at_utc and inv.started_at_utc > case.closed_at_utc:
                raise TemporalIntegrityError(
                    f"Investigation {inv.investigation_id} started after case "
                    f"{case.case_id} was closed."
                )

    for esc in escalations:
        if esc.case_id is not None:
            case = case_map[esc.case_id]
            if esc.escalated_at_utc < case.created_at_utc:
                raise TemporalIntegrityError(
                    f"Escalation {esc.escalation_id} occurred before case "
                    f"{case.case_id} was created."
                )
            if case.closed_at_utc and esc.escalated_at_utc > case.closed_at_utc:
                raise TemporalIntegrityError(
                    f"Escalation {esc.escalation_id} occurred after case {case.case_id} was closed."
                )

    for act in actions:
        if act.case_id is not None:
            case = case_map[act.case_id]
            if act.created_at_utc < case.created_at_utc:
                raise TemporalIntegrityError(
                    f"Action {act.action_id} was created before case {case.case_id} was created."
                )

    for res in resolutions:
        if res.case_id is not None:
            case = case_map[res.case_id]
            if res.resolved_at_utc < case.created_at_utc:
                raise TemporalIntegrityError(
                    f"Resolution {res.resolution_id} occurred before case "
                    f"{case.case_id} was created."
                )

    for clo in closures:
        if clo.case_id is not None:
            case = case_map[clo.case_id]
            if clo.closed_at_utc < case.created_at_utc:
                raise TemporalIntegrityError(
                    f"Closure {clo.closure_id} occurred before case {case.case_id} was created."
                )
        if clo.resolution_id is not None:
            res = res_map[clo.resolution_id]
            if clo.closed_at_utc < res.resolved_at_utc:
                raise TemporalIntegrityError(
                    f"Closure {clo.closure_id} occurred before resolution {res.resolution_id}."
                )

    for sub in submissions:
        if sub.submitted_at_utc and sub.submitted_at_utc < sub.reporting_period_end_at_utc:
            raise TemporalIntegrityError(
                f"Submission {sub.submission_id} submitted at {sub.submitted_at_utc} "
                f"before reporting period end {sub.reporting_period_end_at_utc}."
            )
        if sub.received_at_utc < sub.reporting_period_end_at_utc:
            raise TemporalIntegrityError(
                f"Submission {sub.submission_id} received at {sub.received_at_utc} "
                f"before reporting period end {sub.reporting_period_end_at_utc}."
            )


def _generate_m1_records(
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
        profile_rng = seeds.get_rng(f"{config.split.value}/fixture/{org.org_id}/profile/v1")
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
                f"{config.split.value}/fixture/{org.org_id}/{period.period_id}/submission/timing/v1"
            )
            submitted_at = period_end + timedelta(hours=int(timing_rng.integers(8, 49)))
            received_at = submitted_at + timedelta(minutes=int(timing_rng.integers(5, 181)))
            submission_id = ids.generate("submission", org.org_id, period.period_id, "v1")
            manifest_id = ids.generate("submission_manifest", org.org_id, period.period_id, "v1")
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
                        for family in _M1_FUTURE_FAMILIES
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


def _generate_m2_records(
    config: GeneratorConfig,
    seeds: SeedManager,
    ids: IDService,
) -> tuple[
    list[OrganizationRecord],
    list[SubmissionRecord],
    list[SubmissionManifestRecord],
    list[SubmissionFamilyDeclarationRecord],
    list[ControlProcessReferenceRecord],
    list[ControlProcessSubjectLinkRecord],
    list[AssetRecord],
    list[MonitoringCoverageRecord],
    list[AlertRecord],
    list[CaseRecord],
    list[CaseAlertLinkRecord],
    list[InvestigationRecord],
    list[EscalationRecord],
    list[ActionRecord],
    list[ResolutionRecord],
    list[ClosureRecord],
    list[ExceptionRecord],
    list[ProcessChangeRecord],
]:
    """Generate all 18 Milestone 2 operational evidence families in dependency order."""
    organizations: list[OrganizationRecord] = []
    submissions: list[SubmissionRecord] = []
    submission_manifests: list[SubmissionManifestRecord] = []
    submission_families: list[SubmissionFamilyDeclarationRecord] = []
    control_refs: list[ControlProcessReferenceRecord] = []
    control_links: list[ControlProcessSubjectLinkRecord] = []
    assets: list[AssetRecord] = []
    coverages: list[MonitoringCoverageRecord] = []
    alerts: list[AlertRecord] = []
    cases: list[CaseRecord] = []
    case_alert_links: list[CaseAlertLinkRecord] = []
    investigations: list[InvestigationRecord] = []
    escalations: list[EscalationRecord] = []
    actions: list[ActionRecord] = []
    resolutions: list[ResolutionRecord] = []
    closures: list[ClosureRecord] = []
    exceptions: list[ExceptionRecord] = []
    process_changes: list[ProcessChangeRecord] = []

    profile_start = min(_parse_timestamp(period.start_utc) for period in config.periods)
    actor_id = ids.generate("actor", "fixture-generator")

    # 1. Control & Process References
    ref_defs = [
        (
            "REF-CTRL-01",
            "CONTROL",
            "Authentication Anomaly Monitoring Control",
            "AUTHORITATIVE_CONFIGURATION",
        ),
        (
            "REF-CTRL-02",
            "CONTROL",
            "High-Severity Escalation Review Policy",
            "AUTHORITATIVE_CONFIGURATION",
        ),
        (
            "REF-PROC-01",
            "PROCESS",
            "Standard Security Incident Triage Procedure",
            "PROJECT_DEMO_CONFIGURATION",
        ),
        (
            "REF-PROC-02",
            "PROCESS",
            "Endpoint Malware Containment Runbook",
            "PROJECT_DEMO_CONFIGURATION",
        ),
    ]
    for code, ref_type, display, authority in ref_defs:
        ref_id = ids.generate("control_process_reference", code, "v1")
        control_refs.append(
            ControlProcessReferenceRecord(
                control_process_ref_id=ref_id,
                organization_id=None,
                reference_type=ref_type,
                reference_code=code,
                source_reference_id=f"SRC-{code}",
                display_name=display,
                description=f"Synthetic supervisory {ref_type.lower()} reference.",
                authority_type=authority,
                version="1.0",
                effective_start_at_utc=profile_start,
                status="ACTIVE",
            )
        )

    # 2. Organizations
    org_assets_map: dict[str, list[AssetRecord]] = {}

    for org in sorted(config.organizations, key=lambda item: item.org_id):
        profile_rng = seeds.get_rng(f"{config.split.value}/fixture/{org.org_id}/profile/v1")
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
        org_record = OrganizationRecord(
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
        organizations.append(org_record)

        # Control subject links
        for ref in control_refs[:2]:
            link_id = ids.generate("control_process_link", str(organization_id), ref.reference_code)
            control_links.append(
                ControlProcessSubjectLinkRecord(
                    control_process_link_id=link_id,
                    control_process_ref_id=ref.control_process_ref_id,
                    subject_type="ORGANIZATION",
                    subject_id=organization_id,
                    link_role="APPLIES_TO",
                    source_type="RULE_CONFIGURATION",
                    quality_state="VALID",
                    effective_start_at_utc=profile_start,
                )
            )

        # 3. Assets for organization
        asset_specs = [
            ("SERVER", "CRITICAL", "PRODUCTION", "INFRA_TEAM"),
            ("DATABASE", "HIGH", "PRODUCTION", "DATA_TEAM"),
            ("ENDPOINT", "MODERATE", "PRODUCTION", "IT_SUPPORT"),
            ("APPLICATION", "HIGH", "PRODUCTION", "APP_DEV"),
            ("NETWORK", "MODERATE", "DR", "NET_OPS"),
        ]
        org_assets: list[AssetRecord] = []
        for idx, (a_class, a_crit, env, role) in enumerate(asset_specs):
            asset_id = ids.generate("asset", org.org_id, f"asset-{idx:03d}")
            asset = AssetRecord(
                asset_id=asset_id,
                source_asset_id=f"{org.org_id}-AST-{idx + 1:03d}",
                organization_id=organization_id,
                asset_alias=f"{org.org_id.lower()}-{a_class.lower()}-{idx + 1:02d}",
                asset_class=a_class,
                asset_criticality=a_crit,
                environment=env,
                business_service_code=f"SVC-{org.org_id[-3:]}-01",
                monitoring_expected=True,
                monitoring_expectation_basis="ASSET_CLASS_POLICY",
                active_status="ACTIVE",
                effective_start_at_utc=profile_start,
                owner_role_code=role,
                source_system_id=org.source_profile.value,
                asset_profile_version=1,
            )
            assets.append(asset)
            org_assets.append(asset)

            # 4. Monitoring Coverage
            cov_id = ids.generate("monitoring_coverage", str(asset_id), "siem")
            cov = MonitoringCoverageRecord(
                monitoring_coverage_id=cov_id,
                source_coverage_id=f"COV-{asset.source_asset_id}-01",
                organization_id=organization_id,
                asset_id=asset_id,
                monitoring_type="SIEM_ALERTING"
                if a_class in ("SERVER", "DATABASE", "APPLICATION")
                else "ENDPOINT_MONITORING",
                expectation_state="EXPECTED",
                expectation_basis="ASSET_PROFILE",
                coverage_state="COVERED",
                coverage_source_type="DECLARED",
                coverage_start_at_utc=profile_start,
                last_evidence_at_utc=profile_start + timedelta(days=5),
                source_system_id=org.source_profile.value,
                coverage_reason="Continuous monitoring policy active.",
                coverage_quality_state="VALID",
            )
            coverages.append(cov)

        org_assets_map[org.org_id] = org_assets

        # 5. Exceptions & Process Changes
        exc_id = ids.generate("exception", org.org_id, "exc-001")
        exceptions.append(
            ExceptionRecord(
                exception_id=exc_id,
                source_exception_id=f"EXC-{org.org_id}-01",
                organization_id=organization_id,
                exception_type="MAINTENANCE_WINDOW",
                target_type="ASSET",
                target_id=org_assets[0].asset_id,
                applicability_state="APPLIES",
                approved_state="APPROVED",
                approved_by_role_code="CISO_OFFICE",
                reason="Scheduled quarterly server maintenance and patch window.",
                effective_start_at_utc=profile_start + timedelta(days=10),
                effective_end_at_utc=profile_start + timedelta(days=12),
                created_at_utc=profile_start + timedelta(days=8),
                evidence_reference=f"CHG-{org.org_id}-2025-01",
                exception_quality_state="VALID",
            )
        )

        p02_start = (
            _parse_timestamp(config.periods[1].start_utc)
            if len(config.periods) > 1
            else profile_start + timedelta(days=60)
        )
        pc_id = ids.generate("process_change", org.org_id, "pc-001")
        process_changes.append(
            ProcessChangeRecord(
                process_change_id=pc_id,
                organization_id=organization_id,
                change_type="TOOLING",
                effective_at_utc=p02_start,
                previous_version="wf-v1",
                new_version="wf-v2",
                affected_families=["alert", "case", "investigation"],
                change_summary="Upgraded SIEM parser pipeline and investigation runbook templates.",
                approved_state="APPROVED",
            )
        )

    # 6. Periods and Operational Evidence Flow
    all_evidence_families = (
        "organization",
        "asset",
        "monitoring_coverage",
        "alert",
        "case",
        "case_alert_link",
        "investigation",
        "escalation",
        "action",
        "resolution",
        "closure",
        "exception",
        "process_change",
    )

    for period in sorted(config.periods, key=lambda item: item.period_id):
        period_start = _parse_timestamp(period.start_utc)
        period_end = _parse_timestamp(period.end_utc)

        for org in sorted(config.organizations, key=lambda item: item.org_id):
            organization_id = ids.generate("organization", org.org_id)
            org_assets = org_assets_map[org.org_id]

            timing_rng = seeds.get_rng(
                f"{config.split.value}/fixture/{org.org_id}/{period.period_id}/submission/timing/v1"
            )
            submitted_at = period_end + timedelta(hours=int(timing_rng.integers(8, 49)))
            received_at = submitted_at + timedelta(minutes=int(timing_rng.integers(5, 181)))
            submission_id = ids.generate("submission", org.org_id, period.period_id, "v1")
            manifest_id = ids.generate("submission_manifest", org.org_id, period.period_id, "v1")

            # Submissions & Manifests
            submissions.append(
                SubmissionRecord(
                    submission_id=submission_id,
                    source_submission_id=f"SUB-{org.org_id}-{period.period_id}-01",
                    organization_id=organization_id,
                    reporting_period_start_at_utc=period_start,
                    reporting_period_end_at_utc=period_end,
                    submitted_at_utc=submitted_at,
                    received_at_utc=received_at,
                    source_system_set_id=org.source_profile.value,
                    source_system_versions={org.source_profile.value: "fixture-v2"},
                    declared_completeness="DECLARED_COMPLETE",
                    declared_missing_families=[],
                    submission_status="ACCEPTED",
                    period_maturity_state="MATURE",
                    manifest_id=manifest_id,
                    schema_profile_id=ids.generate(
                        "schema_profile", org.source_profile.value, "v1"
                    ),
                    submission_notes="Synthetic Milestone 2 base-world operational submission.",
                    submission_quality_state="VALID",
                )
            )

            submission_manifests.append(
                SubmissionManifestRecord(
                    manifest_id=manifest_id,
                    submission_id=submission_id,
                    manifest_version=1,
                    created_at_utc=received_at,
                    file_count=18,
                    total_bytes=1024,
                    manifest_sha256=hashlib.sha256(
                        f"m2-manifest-{submission_id}".encode()
                    ).hexdigest(),
                    ingestion_run_id=ids.generate(
                        "ingestion_run", org.org_id, period.period_id, "v1"
                    ),
                    created_by_actor_id=actor_id,
                )
            )

            for fam in all_evidence_families:
                fam_id = ids.generate("submission_family", str(submission_id), fam)
                submission_families.append(
                    SubmissionFamilyDeclarationRecord(
                        submission_family_id=fam_id,
                        submission_id=submission_id,
                        evidence_family=fam,
                        presence_state="PROVIDED",
                        declared_record_count=1,
                        observed_parsed_record_count=1,
                        coverage_start_at_utc=period_start,
                        coverage_end_at_utc=period_end,
                        completeness_state="COMPLETE",
                        completeness_reason="Family fully provided in base world.",
                        assessed_at_utc=received_at,
                    )
                )

            # Alerts & Cases for (org, period)
            alert_rng = seeds.get_rng(
                f"{config.split.value}/fixture/{org.org_id}/{period.period_id}/alerts/v1"
            )

            # We generate 6 operational alerts across the period:
            # - Group 0: alerts 0 & 1 -> Case 0 (High incident, Day 5)
            # - Group 1: alerts 2 & 3 -> Case 1 (Medium alert case, Day 25)
            # - Group 2: alert 4      -> Case 2 (High incident, Day 50)
            # - Group 3: alert 5      -> Standalone resolved alert (Day 65, no case)
            t_base_0 = period_start + timedelta(
                days=5, hours=8, minutes=int(alert_rng.integers(0, 30))
            )
            t_base_1 = period_start + timedelta(
                days=25, hours=10, minutes=int(alert_rng.integers(0, 30))
            )
            t_base_2 = period_start + timedelta(
                days=50, hours=14, minutes=int(alert_rng.integers(0, 30))
            )
            t_base_3 = period_start + timedelta(
                days=65, hours=9, minutes=int(alert_rng.integers(0, 30))
            )

            alert_plans = [
                # (index, created_at, category, severity, disp, status)
                (0, t_base_0, "AUTHENTICATION", "HIGH", "TRUE_POSITIVE", "CLOSED"),
                (
                    1,
                    t_base_0 + timedelta(minutes=int(alert_rng.integers(15, 25))),
                    "MALWARE",
                    "CRITICAL",
                    "TRUE_POSITIVE",
                    "CLOSED",
                ),
                (2, t_base_1, "NETWORK", "MEDIUM", "BENIGN", "CLOSED"),
                (
                    3,
                    t_base_1 + timedelta(minutes=int(alert_rng.integers(10, 20))),
                    "ENDPOINT",
                    "LOW",
                    "FALSE_POSITIVE",
                    "CLOSED",
                ),
                (4, t_base_2, "APPLICATION", "HIGH", "CONFIRMED_INCIDENT", "RESOLVED"),
                (5, t_base_3, "DATA_ACCESS", "MEDIUM", "TRUE_POSITIVE", "CLOSED"),
            ]

            period_alerts: list[AlertRecord] = []
            for i, a_created, a_cat, a_sev, a_disp, a_stat in alert_plans:
                a_ack = a_created + timedelta(minutes=int(alert_rng.integers(3, 12)))
                a_res = a_ack + timedelta(hours=2, minutes=int(alert_rng.integers(10, 30)))
                a_clo = (
                    a_res + timedelta(minutes=int(alert_rng.integers(20, 45)))
                    if a_stat == "CLOSED"
                    else None
                )
                alert_id = ids.generate("alert", org.org_id, period.period_id, f"alt-{i:03d}")
                alert = AlertRecord(
                    alert_id=alert_id,
                    source_alert_id=f"ALT-{org.org_id}-{period.period_id}-{i + 1:03d}",
                    organization_id=organization_id,
                    asset_id=org_assets[i % len(org_assets)].asset_id,
                    source_system_id=org.source_profile.value,
                    source_detection_id=f"DET-{a_cat}-01",
                    alert_category=a_cat,
                    alert_type=f"Suspicious {a_cat.title()} Event",
                    severity=a_sev,
                    source_severity_text=a_sev.lower(),
                    created_at_utc=a_created,
                    acknowledged_at_utc=a_ack,
                    resolved_at_utc=a_res,
                    closed_at_utc=a_clo,
                    last_updated_at_utc=(a_clo or a_res) + timedelta(minutes=10),
                    alert_status=a_stat,
                    disposition=a_disp,
                    automation_state="MIXED",
                    suppression_state="NOT_SUPPRESSED",
                    occurrence_count_source=1,
                    alert_summary=f"Operational alert {i + 1} for {org.org_id}.",
                    workflow_version="wf-v1",
                )
                alerts.append(alert)
                period_alerts.append(alert)

            # Cases for (org, period)
            case_groups = [
                (0, [period_alerts[0], period_alerts[1]], "INCIDENT", "HIGH"),
                (1, [period_alerts[2], period_alerts[3]], "ALERT_CASE", "MEDIUM"),
                (2, [period_alerts[4]], "INCIDENT", "HIGH"),
            ]
            for c_idx, c_alerts, c_type, c_sev in case_groups:
                case_id = ids.generate("case", org.org_id, period.period_id, f"case-{c_idx:03d}")
                case_created = max(a.created_at_utc for a in c_alerts) + timedelta(minutes=10)
                case_assigned = case_created + timedelta(minutes=15)
                inv_start = case_assigned + timedelta(minutes=5)
                act_created = inv_start + timedelta(minutes=10)
                act_started = act_created + timedelta(minutes=10)
                act_completed = act_started + timedelta(minutes=30)
                inv_end = act_completed + timedelta(minutes=15)
                case_res = inv_end + timedelta(minutes=15)
                has_open_alert = any(a.alert_status != "CLOSED" for a in c_alerts)
                case_clo = None if has_open_alert else case_res + timedelta(minutes=30)
                case_status = "RESOLVED" if case_clo is None else "CLOSED"
                c_disp = c_alerts[0].disposition or "TRUE_POSITIVE"

                # Align alert resolution/closure with case
                for a_in_c in c_alerts:
                    object.__setattr__(a_in_c, "resolved_at_utc", case_res)
                    object.__setattr__(a_in_c, "closed_at_utc", case_clo)

                case = CaseRecord(
                    case_id=case_id,
                    source_case_id=f"CASE-{org.org_id}-{period.period_id}-{c_idx + 1:03d}",
                    organization_id=organization_id,
                    case_type=c_type,
                    case_category=c_alerts[0].alert_category,
                    severity=c_sev,
                    priority_source_text="P2" if c_sev == "HIGH" else "P3",
                    created_at_utc=case_created,
                    assigned_at_utc=case_assigned,
                    resolved_at_utc=case_res,
                    closed_at_utc=case_clo,
                    last_updated_at_utc=(case_clo or case_res) + timedelta(minutes=10),
                    case_status=case_status,
                    assigned_team_code="SOC_TIER_2",
                    assigned_analyst_pseudonym="ANALYST_042",
                    workflow_version="wf-v1",
                    case_summary=f"Synthetic operational case {c_idx + 1} for {org.org_id}.",
                    disposition=c_disp,
                    case_record_state="FINAL_STATE",
                )
                cases.append(case)

                # Case-Alert Links
                for a_idx, alert_in_case in enumerate(c_alerts):
                    link_id = ids.generate(
                        "case_alert_link", str(case_id), str(alert_in_case.alert_id)
                    )
                    case_alert_links.append(
                        CaseAlertLinkRecord(
                            case_alert_link_id=link_id,
                            case_id=case_id,
                            alert_id=alert_in_case.alert_id,
                            link_type="PRIMARY" if a_idx == 0 else "RELATED",
                            linked_at_utc=case_created,
                            source_link_id=f"LINK-{case.source_case_id}-{alert_in_case.source_alert_id}",
                            link_source="EXPLICIT",
                            link_quality_state="VALID",
                        )
                    )

                # Investigation for case
                inv_id = ids.generate("investigation", str(case_id), "inv-001")
                investigations.append(
                    InvestigationRecord(
                        investigation_id=inv_id,
                        source_investigation_id=f"INV-{case.source_case_id}-01",
                        organization_id=organization_id,
                        case_id=case_id,
                        alert_id=c_alerts[0].alert_id,
                        investigation_sequence=1,
                        started_at_utc=inv_start,
                        ended_at_utc=inv_end,
                        recorded_at_utc=inv_end + timedelta(minutes=5),
                        investigation_status="COMPLETED",
                        analyst_role_code="TIER_2_ANALYST",
                        analyst_pseudonym="ANALYST_042",
                        method_code="RUNBOOK_TRIAGE",
                        runbook_id="RB-SEC-01",
                        template_id="TMPL-01",
                        automation_state="MANUAL",
                        investigation_notes=(
                            f"Investigated operational alert findings for case "
                            f"{case.source_case_id}."
                        ),
                        conclusion_code="CONFIRMED_THREAT"
                        if c_disp == "TRUE_POSITIVE"
                        else "BENIGN_ACTIVITY",
                        disposition=c_disp,
                        workflow_version="wf-v1",
                    )
                )

                # Escalation (for high/critical cases)
                if c_sev in ("HIGH", "CRITICAL"):
                    esc_id = ids.generate("escalation", str(case_id), "esc-001")
                    esc_at = inv_start + timedelta(minutes=8)
                    ack_at = esc_at + timedelta(minutes=5)
                    res_at = esc_at + timedelta(minutes=25)
                    escalations.append(
                        EscalationRecord(
                            escalation_id=esc_id,
                            source_escalation_id=f"ESC-{case.source_case_id}-01",
                            organization_id=organization_id,
                            case_id=case_id,
                            alert_id=c_alerts[0].alert_id,
                            escalated_at_utc=esc_at,
                            escalation_type="INCIDENT_RESPONSE",
                            source_role_code="TIER_2_SOC",
                            target_role_code="INCIDENT_COMMANDER",
                            escalation_level="TIER_3",
                            escalation_reason=(
                                "High severity alert cluster escalated for command review."
                            ),
                            escalation_status="RESOLVED",
                            acknowledged_at_utc=ack_at,
                            resolved_at_utc=res_at,
                            resolution_summary=(
                                "Incident command reviewed and authorized containment."
                            ),
                            policy_trigger_code="REF-CTRL-02",
                            workflow_version="wf-v1",
                        )
                    )

                # Action / Remediation
                act_id = ids.generate("action", str(case_id), "act-001")
                actions.append(
                    ActionRecord(
                        action_id=act_id,
                        source_action_id=f"ACT-{case.source_case_id}-01",
                        organization_id=organization_id,
                        asset_id=c_alerts[0].asset_id,
                        alert_id=c_alerts[0].alert_id,
                        case_id=case_id,
                        action_type="CONTAIN",
                        created_at_utc=act_created,
                        due_at_utc=act_created + timedelta(days=1),
                        started_at_utc=act_started,
                        completed_at_utc=act_completed,
                        action_status="VERIFIED",
                        owner_role_code="SECOPS_ENGINEER",
                        remediation_reference=f"REM-{case.source_case_id}",
                        action_summary=(
                            f"Contained anomalous activity on {c_alerts[0].alert_category} subject."
                        ),
                        verification_state="VERIFIED",
                        workflow_version="wf-v1",
                    )
                )

                # Resolution
                res_id = ids.generate("resolution", str(case_id), "res-001")
                resolutions.append(
                    ResolutionRecord(
                        resolution_id=res_id,
                        source_resolution_id=f"RES-{case.source_case_id}-01",
                        organization_id=organization_id,
                        case_id=case_id,
                        alert_id=c_alerts[0].alert_id,
                        resolved_at_utc=case_res,
                        resolution_type="CONTAINED"
                        if c_disp == "TRUE_POSITIVE"
                        else "NO_ACTION_REQUIRED",
                        resolution_status="VERIFIED",
                        resolution_reason="Remediation steps completed and validated by SOC lead.",
                        approved_by_role_code="SOC_LEAD",
                        verification_reference=f"VERIF-{case.source_case_id}",
                        workflow_version="wf-v1",
                    )
                )

                # Closure (if closed)
                if case_clo is not None:
                    clo_id = ids.generate("closure", str(case_id), "clo-001")
                    closures.append(
                        ClosureRecord(
                            closure_id=clo_id,
                            source_closure_id=f"CLO-{case.source_case_id}-01",
                            organization_id=organization_id,
                            case_id=case_id,
                            alert_id=c_alerts[0].alert_id,
                            resolution_id=res_id,
                            closed_at_utc=case_clo,
                            closure_status="CLOSED",
                            disposition=c_disp,
                            closure_reason=(
                                "All investigative actions verified; ticket "
                                "administratively closed."
                            ),
                            closed_by_role_code="SOC_LEAD",
                            approval_state="APPROVED",
                            approved_at_utc=case_clo,
                            workflow_version="wf-v1",
                        )
                    )

    return (
        organizations,
        submissions,
        submission_manifests,
        submission_families,
        control_refs,
        control_links,
        assets,
        coverages,
        alerts,
        cases,
        case_alert_links,
        investigations,
        escalations,
        actions,
        resolutions,
        closures,
        exceptions,
        process_changes,
    )


def _make_context(
    config: GeneratorConfig,
    root: Path,
    seed_ledger_sha256: str,
    contract: str = "SATSA-M1-FIXTURE-V1",
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
        metadata={"fixture_contract": contract},
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
            (str(item[k]) for k in _PRIMARY_ID_KEYS if k in item),
            "",
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
