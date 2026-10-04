"""Contract tests for Milestone 4 scenario and legitimate-control engine."""

from __future__ import annotations

import json
from pathlib import Path

from satsa_generator.fixture.builder import build_fixture, build_m4_fixture
from satsa_generator.scenarios.truth import LeakageScanner


def test_m4_fixture_contract(
    tmp_path: Path,
    fixture_config_path: Path,
    master_seed: bytes,
) -> None:
    """Build M4 fixture and verify operational evidence, manifest, and private ground truth."""
    out_dir = tmp_path / "m4_build"
    result = build_m4_fixture(
        config_path=fixture_config_path,
        master_seed=master_seed,
        output_root=out_dir,
    )

    # 1. Operational evidence exists
    assert result.operational_root.exists()
    assert result.manifest_path.is_file()

    # 2. Manifest contract is SATSA-M4-FIXTURE-V1
    manifest_data = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest_data["fixture_contract"] == "SATSA-M4-FIXTURE-V1"
    assert "m4" in manifest_data["dataset_version"]

    # 3. Private ground-truth package exists strictly separate from operational root
    private_root = out_dir / "private_ground_truth"
    assert private_root.is_dir()
    assert (private_root / "ground_truth.json").is_file()
    assert (private_root / "authorization_ledger.json").is_file()

    # 4. Operational root contains NO ground truth or scenario files
    operational_files = [f.name for f in result.operational_root.iterdir()]
    assert "ground_truth.json" not in operational_files
    assert "authorization_ledger.json" not in operational_files
    assert "scenario_instances.json" not in operational_files

    # 5. Leakage scan: every operational file passes zero-leakage check
    for file_path in result.operational_root.glob("*.json"):
        content = json.loads(file_path.read_text(encoding="utf-8"))
        LeakageScanner.assert_no_leakage(content)

    # 6. Convenience alias in build_fixture
    alias_dir = tmp_path / "m4_alias"
    alias_result = build_fixture(
        config_path=fixture_config_path,
        master_seed=master_seed,
        output_root=alias_dir,
        milestone="m4",
    )
    assert alias_result.tree_sha256 == result.tree_sha256


def test_m4_fixture_determinism(
    tmp_path: Path,
    fixture_config_path: Path,
    master_seed: bytes,
) -> None:
    """Building M4 fixture twice with the same seed yields bitwise identical operational tree."""
    out1 = tmp_path / "m4_det_1"
    out2 = tmp_path / "m4_det_2"

    res1 = build_m4_fixture(
        config_path=fixture_config_path, master_seed=master_seed, output_root=out1
    )
    res2 = build_m4_fixture(
        config_path=fixture_config_path, master_seed=master_seed, output_root=out2
    )

    assert res1.tree_sha256 == res2.tree_sha256
    assert res1.record_counts == res2.record_counts

    # Verify ground truth is also deterministic
    gt1 = (out1 / "private_ground_truth" / "ground_truth.json").read_text(encoding="utf-8")
    gt2 = (out2 / "private_ground_truth" / "ground_truth.json").read_text(encoding="utf-8")
    assert gt1 == gt2
