from __future__ import annotations

import json
from pathlib import Path

import pytest

from satsa_generator.core.errors import FixtureBuildError, SchemaContractError
from satsa_generator.fixture.builder import build_fixture, validate_fixture_records
from satsa_generator.fixture.models import OrganizationRecord


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_fixture_builds_with_required_schema_fields(tmp_path, fixture_config_path, master_seed):
    result = build_fixture(fixture_config_path, master_seed, output_root=tmp_path / "fixture")
    files = _tree_bytes(result.operational_root)

    assert set(files) == {
        "fixture_manifest.json",
        "organizations.json",
        "submission_manifests.json",
        "submissions.json",
    }
    organizations = json.loads(files["organizations.json"])
    submissions = json.loads(files["submissions.json"])
    manifests = json.loads(files["submission_manifests.json"])
    assert result.record_counts == {
        "organization": 3,
        "submission": 6,
        "submission_manifest": 6,
    }
    assert {
        "organization_id",
        "organization_name",
        "sector_code",
        "scale_band",
        "operating_model",
        "profile_effective_start_at_utc",
        "profile_version",
        "organization_status",
    } <= set(organizations[0])
    assert {
        "submission_id",
        "organization_id",
        "reporting_period_start_at_utc",
        "reporting_period_end_at_utc",
        "received_at_utc",
        "declared_completeness",
        "submission_status",
        "period_maturity_state",
        "manifest_id",
        "submission_quality_state",
    } <= set(submissions[0])
    assert {"manifest_id", "submission_id", "manifest_sha256"} <= set(manifests[0])


def test_fixture_serialized_output_is_identical(tmp_path, fixture_config_path, master_seed):
    first = build_fixture(fixture_config_path, master_seed, output_root=tmp_path / "a")
    second = build_fixture(fixture_config_path, master_seed, output_root=tmp_path / "b")

    assert first.tree_sha256 == second.tree_sha256
    assert _tree_bytes(first.operational_root) == _tree_bytes(second.operational_root)


def test_different_seed_changes_serialized_output(
    tmp_path, fixture_config_path, master_seed, different_master_seed
):
    first = build_fixture(fixture_config_path, master_seed, output_root=tmp_path / "a")
    second = build_fixture(fixture_config_path, different_master_seed, output_root=tmp_path / "b")

    assert first.tree_sha256 != second.tree_sha256
    assert _tree_bytes(first.operational_root) != _tree_bytes(second.operational_root)


def test_fixture_contains_no_truth_or_detector_fields(tmp_path, fixture_config_path, master_seed):
    result = build_fixture(fixture_config_path, master_seed, output_root=tmp_path / "fixture")
    text = "\n".join(
        content.decode("utf-8") for content in _tree_bytes(result.operational_root).values()
    ).lower()

    for forbidden in (
        "scenario_id",
        "true_label",
        "expected_finding",
        "mutation_annotation",
        "planted_positive",
        "detector_threshold",
        "risk_score",
    ):
        assert forbidden not in text
    assert not (result.output_root / "ground_truth_private").exists()
    assert not (result.output_root / "evaluation_private").exists()


def test_invalid_fixture_relationship_fails_loudly(tmp_path, fixture_config_path, master_seed):
    result = build_fixture(fixture_config_path, master_seed, output_root=tmp_path / "fixture")
    organization_data = json.loads(
        (result.operational_root / "organizations.json").read_text(encoding="utf-8")
    )
    submission_data = json.loads(
        (result.operational_root / "submissions.json").read_text(encoding="utf-8")
    )
    manifest_data = json.loads(
        (result.operational_root / "submission_manifests.json").read_text(encoding="utf-8")
    )
    from satsa_generator.fixture.models import (
        SubmissionManifestRecord,
        SubmissionRecord,
    )

    organizations = [OrganizationRecord.model_validate(row) for row in organization_data]
    submissions = [SubmissionRecord.model_validate(row) for row in submission_data]
    manifests = [SubmissionManifestRecord.model_validate(row) for row in manifest_data]
    invalid_submission = submissions[0].model_copy(
        update={"organization_id": "00000000-0000-0000-0000-000000000000"}
    )
    submissions[0] = invalid_submission

    with pytest.raises(SchemaContractError, match="unknown organization"):
        validate_fixture_records(organizations, submissions, manifests)


def test_existing_output_is_not_silently_overwritten(tmp_path, fixture_config_path, master_seed):
    output = tmp_path / "fixture"
    output.mkdir()
    (output / "unrelated.txt").write_text("preserve me", encoding="utf-8")

    with pytest.raises(FixtureBuildError, match="never silently overwrites"):
        build_fixture(fixture_config_path, master_seed, output_root=output)
