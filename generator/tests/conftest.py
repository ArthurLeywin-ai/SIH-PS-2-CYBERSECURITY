"""Shared Milestone 1 test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def fixture_config_path() -> Path:
    return (
        Path(__file__).resolve().parents[1] / "config" / "public" / "base" / "fixture_config.json"
    )


@pytest.fixture
def master_seed() -> bytes:
    return bytes.fromhex("11" * 32)


@pytest.fixture
def different_master_seed() -> bytes:
    return bytes.fromhex("22" * 32)


@pytest.fixture
def base_m2_records(fixture_config_path: Path, master_seed: bytes) -> dict[str, list[object]]:
    from satsa_generator.config.models import load_config
    from satsa_generator.fixture.builder import _generate_m2_records
    from satsa_generator.ids.service import IDService
    from satsa_generator.seeds.manager import SeedManager

    config = load_config(fixture_config_path)
    seeds = SeedManager(master_seed)
    ids = IDService(config.dataset_namespace)
    records = _generate_m2_records(config, seeds, ids)

    return {
        "organization": list(records[0]),
        "submission": list(records[1]),
        "submission_manifest": list(records[2]),
        "submission_family": list(records[3]),
        "control_process_reference": list(records[4]),
        "control_process_subject_link": list(records[5]),
        "asset": list(records[6]),
        "monitoring_coverage": list(records[7]),
        "alert": list(records[8]),
        "case": list(records[9]),
        "case_alert_link": list(records[10]),
        "investigation": list(records[11]),
        "escalation": list(records[12]),
        "action": list(records[13]),
        "resolution": list(records[14]),
        "closure": list(records[15]),
        "exception": list(records[16]),
        "process_change": list(records[17]),
    }
