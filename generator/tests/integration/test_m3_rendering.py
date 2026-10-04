"""Integration tests for Milestone 3 (Source Profiles and Canonical Oracle)."""

from pathlib import Path

import pytest

from satsa_generator.fixture.builder import build_m3_fixture
from satsa_generator.profiles.catalog import get_profile
from satsa_generator.validation.parser import parse_and_validate


def test_m3_build_fixture_and_parseback(tmp_path: Path, fixture_config_path: Path, master_seed: bytes) -> None:
    """Verify that M3 build succeeds, generates source files and an oracle."""
    result = build_m3_fixture(fixture_config_path, master_seed, output_root=tmp_path)

    assert result.operational_root.exists()
    assert (result.operational_root / "fixture_manifest.json").exists()

    oracle_dir = tmp_path / "canonical_reference"
    assert oracle_dir.exists()

    # Test True Parse-Back for all profiles
    for profile_id in ["SRC-A", "SRC-B", "SRC-C", "SRC-D", "SRC-E"]:
        # Check an evidence family we know exists, like 'organization' or 'submission'
        for family in ["organization", "submission", "alert", "submission_manifest"]:
            # If the profile wasn't used for this family in builder distribution, it will be skipped by parse_and_validate
            parse_and_validate(result.operational_root, oracle_dir, profile_id, family)


def test_corruption_field_value(tmp_path: Path, fixture_config_path: Path, master_seed: bytes) -> None:
    """Test A - field corruption."""
    result = build_m3_fixture(fixture_config_path, master_seed, output_root=tmp_path)
    csv_file = result.operational_root / "organization_src-a.csv"

    # Corrupt
    content = csv_file.read_text(encoding="utf-8")
    content = content.replace("ACTIVE", "CORRUPTED")
    csv_file.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match="Parse-back failure"):
        parse_and_validate(result.operational_root, tmp_path / "canonical_reference", "SRC-A", "organization")


def test_corruption_missing_record(tmp_path: Path, fixture_config_path: Path, master_seed: bytes) -> None:
    """Test E - missing source record."""
    result = build_m3_fixture(fixture_config_path, master_seed, output_root=tmp_path)
    csv_file = result.operational_root / "organization_src-a.csv"

    # Corrupt by removing last line
    lines = csv_file.read_text(encoding="utf-8").strip().split("\n")
    csv_file.write_text("\n".join(lines[:-1]), encoding="utf-8")

    with pytest.raises(AssertionError, match="Record count mismatch"):
        parse_and_validate(result.operational_root, tmp_path / "canonical_reference", "SRC-A", "organization")


def test_reproducibility(tmp_path: Path, fixture_config_path: Path, master_seed: bytes) -> None:
    """Verify same seed produces byte-identical output hashes."""
    run1 = build_m3_fixture(fixture_config_path, master_seed, output_root=tmp_path / "run1")
    run2 = build_m3_fixture(fixture_config_path, master_seed, output_root=tmp_path / "run2")

    assert run1.tree_sha256 == run2.tree_sha256

def test_different_seed_variation(tmp_path: Path, fixture_config_path: Path, master_seed: bytes) -> None:
    """Verify different seeds produce different outputs."""
    seed1 = b"A" * 32
    seed2 = b"B" * 32
    run1 = build_m3_fixture(fixture_config_path, seed1, output_root=tmp_path / "run1")
    run2 = build_m3_fixture(fixture_config_path, seed2, output_root=tmp_path / "run2")

    assert run1.tree_sha256 != run2.tree_sha256
