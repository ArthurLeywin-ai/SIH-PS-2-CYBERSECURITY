"""
Integration test for Milestone 5 reproducibility.

Tests GENERATOR_IMPLEMENTATION_PLAN §20 (Reproducibility Tests A and B):
- Same seed produces identical logical records, IDs, relationships, states, and manifests
- Same seed produces identical operational and private bytes
- Different seeds produce different outputs
"""

from pathlib import Path

from satsa_generator.fixture.builder import build_fixture, parse_master_seed_hex


def test_m5_reproducibility_same_seed(tmp_path):
    config_path = Path("generator/config/public/base/fixture_config.json")
    if not config_path.exists():
        config_path = Path("config/public/base/fixture_config.json")
    seed_hex = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    seed_bytes = parse_master_seed_hex(seed_hex)

    out1 = tmp_path / "run1"
    out2 = tmp_path / "run2"

    res1 = build_fixture(config_path, seed_bytes, output_root=out1, milestone="m5")
    res2 = build_fixture(config_path, seed_bytes, output_root=out2, milestone="m5")

    # Tree SHA-256 must match exactly
    assert res1.tree_sha256 == res2.tree_sha256
    assert res1.record_counts == res2.record_counts

    # Operational files byte-for-byte check
    op1_files = sorted(list(res1.operational_root.glob("*.json")))
    op2_files = sorted(list(res2.operational_root.glob("*.json")))
    assert [f.name for f in op1_files] == [f.name for f in op2_files]

    for f1, f2 in zip(op1_files, op2_files, strict=True):
        assert f1.read_bytes() == f2.read_bytes()

    # Private files byte-for-byte check
    priv1 = out1 / "private_ground_truth"
    priv2 = out2 / "private_ground_truth"

    for artifact_name in (
        "ground_truth.json",
        "authorization_ledger.json",
        "quality_receipts.json",
    ):
        assert (priv1 / artifact_name).read_bytes() == (priv2 / artifact_name).read_bytes()

    # Full validation report byte-for-byte check
    val_report1 = priv1 / "validation_reports" / "full_validation_report.json"
    val_report2 = priv2 / "validation_reports" / "full_validation_report.json"
    assert val_report1.read_bytes() == val_report2.read_bytes()


def test_m5_reproducibility_different_seed(tmp_path):
    config_path = Path("generator/config/public/base/fixture_config.json")
    if not config_path.exists():
        config_path = Path("config/public/base/fixture_config.json")
    seed1 = parse_master_seed_hex(
        "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    )
    seed2 = parse_master_seed_hex(
        "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210"
    )

    out1 = tmp_path / "diff_run1"
    out2 = tmp_path / "diff_run2"

    res1 = build_fixture(config_path, seed1, output_root=out1, milestone="m5")
    res2 = build_fixture(config_path, seed2, output_root=out2, milestone="m5")

    assert res1.tree_sha256 != res2.tree_sha256
