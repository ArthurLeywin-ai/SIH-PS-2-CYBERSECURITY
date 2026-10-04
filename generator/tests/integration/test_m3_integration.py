"""Test all profiles against all families."""

import json
from pathlib import Path

from satsa_generator.fixture.builder import build_m3_fixture
from satsa_generator.validation.parser import parse_and_validate


def test_exhaustive_profiles(tmp_path: Path, fixture_config_path: Path, master_seed: bytes) -> None:
    # Read the base config
    with open(fixture_config_path) as f:
        config = json.load(f)

    # Ensure all profiles are present in the organizations
    config["organizations"] = [
        {
            "org_id": "CSE-101",
            "name": "Org A",
            "source_profile": "SRC-A",
            "cohort": "COHORT-A",
            "sector": "SECTOR-A",
            "scale_band": "small",
            "operating_model": "hybrid",
        },
        {
            "org_id": "CSE-102",
            "name": "Org B",
            "source_profile": "SRC-B",
            "cohort": "COHORT-B",
            "sector": "SECTOR-B",
            "scale_band": "small",
            "operating_model": "hybrid",
        },
        {
            "org_id": "CSE-103",
            "name": "Org C",
            "source_profile": "SRC-C",
            "cohort": "COHORT-C",
            "sector": "SECTOR-C",
            "scale_band": "small",
            "operating_model": "hybrid",
        },
        {
            "org_id": "CSE-104",
            "name": "Org D",
            "source_profile": "SRC-D",
            "cohort": "COHORT-D",
            "sector": "SECTOR-D",
            "scale_band": "small",
            "operating_model": "hybrid",
        },
        {
            "org_id": "CSE-105",
            "name": "Org E",
            "source_profile": "SRC-E",
            "cohort": "COHORT-E",
            "sector": "SECTOR-E",
            "scale_band": "small",
            "operating_model": "hybrid",
        },
    ]

    test_config_path = tmp_path / "test_config.json"
    with open(test_config_path, "w") as f:
        json.dump(config, f)

    out_dir = tmp_path / "output"
    result = build_m3_fixture(test_config_path, master_seed, output_root=out_dir)

    oracle_dir = out_dir / "canonical_reference"

    all_profiles = ["SRC-A", "SRC-B", "SRC-C", "SRC-D", "SRC-E"]
    all_families = [
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
    ]

    # Explicit coverage matrix tracking (Blocker 6)
    coverage_matrix: dict[tuple[str, str], bool] = {}

    from satsa_generator.profiles.catalog import get_profile

    for profile_id in all_profiles:
        profile = get_profile(profile_id)
        for family in all_families:
            fmt = profile.get_format(family).lower()
            expected_file = result.operational_root / f"{family}_{profile_id.lower()}.{fmt}"
            assert expected_file.exists(), (
                f"Missing required rendered artifact for {profile_id} {family}: {expected_file}"
            )
            assert expected_file.stat().st_size > 0, (
                f"Artifact for {profile_id} {family} is empty: {expected_file}"
            )

            parse_and_validate(result.operational_root, oracle_dir, profile_id, family)
            coverage_matrix[(profile_id, family)] = True

    # Assert complete 90/90 coverage matrix with 0 skips
    assert len(coverage_matrix) == len(all_profiles) * len(all_families)
    assert all(coverage_matrix.values()), (
        "All 90 profile-family combinations must be covered and validated"
    )

    # Heterogeneity feature checks across rendered output
    formats_found = {p.suffix.lower() for p in result.operational_root.iterdir() if p.is_file()}
    assert ".csv" in formats_found, "CSV heterogeneity format must be present"
    assert ".json" in formats_found, "JSON heterogeneity format must be present"

    # Verify migration versions coverage (SRC-E V1 and V2)
    p_e1 = get_profile("SRC-E", version="1.0")
    p_e2 = get_profile("SRC-E", version="2.0")
    assert p_e1.id_namespace == "E1"
    assert p_e2.id_namespace == "E2"
    assert p_e1.version == "1.0"
    assert p_e2.version == "2.0"
