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
            parse_and_validate(result.operational_root, oracle_dir, profile_id, family)
