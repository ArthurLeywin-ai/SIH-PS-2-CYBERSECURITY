from __future__ import annotations

from pathlib import Path

import pytest

from satsa_generator.core.errors import FixtureBuildError
from satsa_generator.fixture.builder import build_m2_fixture


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_m2_fixture_builds_all_required_families(tmp_path, fixture_config_path, master_seed):
    result = build_m2_fixture(fixture_config_path, master_seed, output_root=tmp_path / "m2")
    files = _tree_bytes(result.operational_root)

    expected_files = {
        "fixture_manifest.json",
        "organizations.json",
        "submissions.json",
        "submission_manifests.json",
        "submission_evidence_families.json",
        "control_process_references.json",
        "control_process_subject_links.json",
        "assets.json",
        "monitoring_coverage.json",
        "alerts.json",
        "cases.json",
        "case_alert_links.json",
        "investigations.json",
        "escalations.json",
        "actions.json",
        "resolutions.json",
        "closures.json",
        "exceptions.json",
        "process_changes.json",
    }
    assert set(files) == expected_files

    # Check non-empty record counts for all 18 evidence families
    assert result.record_counts["organization"] == 3
    assert result.record_counts["submission"] == 6
    assert result.record_counts["submission_manifest"] == 6
    assert result.record_counts["submission_evidence_family"] == 78
    assert result.record_counts["control_process_reference"] == 4
    assert result.record_counts["control_process_subject_link"] == 6
    assert result.record_counts["asset"] == 15
    assert result.record_counts["monitoring_coverage"] == 15
    assert result.record_counts["alert"] == 36
    assert result.record_counts["case"] == 18
    assert result.record_counts["case_alert_link"] == 30
    assert result.record_counts["investigation"] == 18
    assert result.record_counts["escalation"] == 12
    assert result.record_counts["action"] == 18
    assert result.record_counts["resolution"] == 18
    assert result.record_counts["closure"] == 12
    assert result.record_counts["exception"] == 3
    assert result.record_counts["process_change"] == 3


def test_m2_fixture_contains_no_truth_or_detector_fields(
    tmp_path, fixture_config_path, master_seed
):
    result = build_m2_fixture(fixture_config_path, master_seed, output_root=tmp_path / "m2_clean")
    text = "\n".join(
        content.decode("utf-8") for content in _tree_bytes(result.operational_root).values()
    ).lower()

    forbidden = (
        "scenario_id",
        "risk_score",
        "detector_score",
        "ground_truth",
        "true_category",
        "expected_finding",
        "planted_positive",
        "mutation_annotation",
        "scenario_seed",
        "answer_key",
        "anomaly_contamination",
    )
    for term in forbidden:
        assert term not in text, f"Operational evidence leaked forbidden term: {term}"


def test_m2_fixture_refuses_to_overwrite_existing_output_directory(
    tmp_path, fixture_config_path, master_seed
):
    out = tmp_path / "existing_dir"
    out.mkdir()
    (out / "dummy.txt").write_text("pre-existing content", encoding="utf-8")

    with pytest.raises(FixtureBuildError, match="must not exist or must be empty"):
        build_m2_fixture(fixture_config_path, master_seed, output_root=out)
