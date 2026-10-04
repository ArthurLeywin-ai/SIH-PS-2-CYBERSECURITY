"""Integration tests for Milestone 3 (Source Profiles and Canonical Oracle)."""

from pathlib import Path

import pytest

from satsa_generator.fixture.builder import build_m3_fixture
from satsa_generator.validation.parser import parse_and_validate


def test_m3_build_fixture_and_parseback(
    tmp_path: Path, fixture_config_path: Path, master_seed: bytes
) -> None:
    """Verify that M3 build succeeds, generates source files and an oracle."""
    result = build_m3_fixture(fixture_config_path, master_seed, output_root=tmp_path)

    assert result.operational_root.exists()
    assert (result.operational_root / "fixture_manifest.json").exists()

    oracle_dir = tmp_path / "canonical_reference"
    assert oracle_dir.exists()

    # Test True Parse-Back for all profiles
    for profile_id in ["SRC-A", "SRC-B", "SRC-C", "SRC-D", "SRC-E"]:
        for family in [
            "organization",
            "submission",
            "submission_manifest",
            "submission_family",
            "control_process_reference",
            "control_process_subject_link",
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
        ]:
            # If the profile wasn't used for this family in builder distribution,
            # it will be skipped by parse_and_validate
            parse_and_validate(result.operational_root, oracle_dir, profile_id, family)


def test_corruption_field_value(
    tmp_path: Path, fixture_config_path: Path, master_seed: bytes
) -> None:
    """Test A - field corruption."""
    result = build_m3_fixture(fixture_config_path, master_seed, output_root=tmp_path)
    csv_file = result.operational_root / "organization_src-a.csv"

    # Corrupt
    content = csv_file.read_text(encoding="utf-8")
    content = content.replace("ACTIVE", "CORRUPTED")
    csv_file.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match="Parse-back failure"):
        parse_and_validate(
            result.operational_root, tmp_path / "canonical_reference", "SRC-A", "organization"
        )


def test_corruption_missing_record(
    tmp_path: Path, fixture_config_path: Path, master_seed: bytes
) -> None:
    """Test E - missing source record."""
    result = build_m3_fixture(fixture_config_path, master_seed, output_root=tmp_path)
    csv_file = result.operational_root / "organization_src-a.csv"

    # Corrupt by removing last line
    lines = csv_file.read_text(encoding="utf-8").strip().split("\n")
    csv_file.write_text("\n".join(lines[:-1]), encoding="utf-8")

    with pytest.raises(AssertionError, match="Record count mismatch"):
        parse_and_validate(
            result.operational_root, tmp_path / "canonical_reference", "SRC-A", "organization"
        )


def test_corruption_relationship_id(
    tmp_path: Path, fixture_config_path: Path, master_seed: bytes
) -> None:
    """Test - broken relationship ID."""
    result = build_m3_fixture(fixture_config_path, master_seed, output_root=tmp_path)
    csv_file = result.operational_root / "submission_src-b.csv"

    content = csv_file.read_text(encoding="utf-8")
    org_id = content.split("\n")[1].split(",")[1]
    bad_id = org_id[:-1] + ("f" if org_id[-1] != "f" else "0")
    content = content.replace(org_id, bad_id)
    csv_file.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match="Parse-back relationship failure|Parse-back failure"):
        parse_and_validate(
            result.operational_root, tmp_path / "canonical_reference", "SRC-B", "submission"
        )


def test_corruption_vocabulary(
    tmp_path: Path, fixture_config_path: Path, master_seed: bytes
) -> None:
    """Test - vocabulary corruption."""
    result = build_m3_fixture(fixture_config_path, master_seed, output_root=tmp_path)
    csv_file = result.operational_root / "submission_src-b.csv"

    # Corrupt numeric vocabulary value
    content = csv_file.read_text(encoding="utf-8")
    lines = content.split("\n")
    if len(lines) > 1 and lines[1]:
        parts = lines[1].split(",")
        # replace period_maturity_state (third column) with 99
        parts[2] = "99"
        lines[1] = ",".join(parts)
        csv_file.write_text("\n".join(lines), encoding="utf-8")

    with pytest.raises(ValueError, match="Parse-back failure"):
        parse_and_validate(
            result.operational_root, tmp_path / "canonical_reference", "SRC-B", "submission"
        )


def test_corruption_missing_relationship(
    tmp_path: Path, fixture_config_path: Path, master_seed: bytes
) -> None:
    """Test - missing relationship."""
    result = build_m3_fixture(fixture_config_path, master_seed, output_root=tmp_path)
    # asset in SRC-B is CSV, if we remove organization_id it becomes empty.
    csv_file = result.operational_root / "asset_src-b.csv"

    content = csv_file.read_text(encoding="utf-8")
    # Replace the organization_id (second column) with empty string in the first data row
    lines = content.split("\n")
    if len(lines) > 1 and lines[1]:
        parts = lines[1].split(",")
        parts[2] = (
            ""  # org_id is 3rd col (asset_id, source_asset_id, organization_id)
        )
        lines[1] = ",".join(parts)
        csv_file.write_text("\n".join(lines), encoding="utf-8")

    with pytest.raises(ValueError, match="Parse-back relationship failure|Parse-back failure"):
        parse_and_validate(
            result.operational_root, tmp_path / "canonical_reference", "SRC-B", "asset"
        )


def test_corruption_wrong_related_id(
    tmp_path: Path, fixture_config_path: Path, master_seed: bytes
) -> None:
    """Test - wrong related ID (using another valid UUID)."""
    import uuid

    result = build_m3_fixture(fixture_config_path, master_seed, output_root=tmp_path)
    csv_file = result.operational_root / "submission_src-b.csv"

    content = csv_file.read_text(encoding="utf-8")
    lines = content.split("\n")
    if len(lines) > 1 and lines[1]:
        parts = lines[1].split(",")
        # replace organization_id (second column) with a random valid UUID
        parts[1] = str(uuid.uuid4())
        lines[1] = ",".join(parts)
        csv_file.write_text("\n".join(lines), encoding="utf-8")

    with pytest.raises(ValueError, match="Parse-back relationship failure|Parse-back failure"):
        parse_and_validate(
            result.operational_root, tmp_path / "canonical_reference", "SRC-B", "submission"
        )


def test_reproducibility(tmp_path: Path, fixture_config_path: Path, master_seed: bytes) -> None:
    """Verify same seed produces byte-identical output hashes."""
    run1 = build_m3_fixture(fixture_config_path, master_seed, output_root=tmp_path / "run1")
    run2 = build_m3_fixture(fixture_config_path, master_seed, output_root=tmp_path / "run2")

    assert run1.tree_sha256 == run2.tree_sha256


def test_different_seed_variation(
    tmp_path: Path, fixture_config_path: Path, master_seed: bytes
) -> None:
    """Verify different seeds produce different outputs."""
    seed1 = b"A" * 32
    seed2 = b"B" * 32
    run1 = build_m3_fixture(fixture_config_path, seed1, output_root=tmp_path / "run1")
    run2 = build_m3_fixture(fixture_config_path, seed2, output_root=tmp_path / "run2")

    assert run1.tree_sha256 != run2.tree_sha256
