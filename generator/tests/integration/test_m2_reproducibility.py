from __future__ import annotations

from pathlib import Path

from satsa_generator.fixture.builder import build_m2_fixture


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_m2_same_seed_produces_identical_serialized_output(
    tmp_path, fixture_config_path, master_seed
):
    first = build_m2_fixture(fixture_config_path, master_seed, output_root=tmp_path / "run_a")
    second = build_m2_fixture(fixture_config_path, master_seed, output_root=tmp_path / "run_b")

    assert first.tree_sha256 == second.tree_sha256
    assert _tree_bytes(first.operational_root) == _tree_bytes(second.operational_root)


def test_m2_different_seed_changes_serialized_output(
    tmp_path, fixture_config_path, master_seed, different_master_seed
):
    first = build_m2_fixture(fixture_config_path, master_seed, output_root=tmp_path / "run_a")
    second = build_m2_fixture(
        fixture_config_path, different_master_seed, output_root=tmp_path / "run_b"
    )

    assert first.tree_sha256 != second.tree_sha256
    assert _tree_bytes(first.operational_root) != _tree_bytes(second.operational_root)
