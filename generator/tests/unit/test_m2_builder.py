from __future__ import annotations

import pytest

from satsa_generator.config.models import load_config
from satsa_generator.core.errors import FixtureBuildError
from satsa_generator.fixture.builder import _generate_m2_records, build_fixture, build_m2_fixture
from satsa_generator.ids.service import IDService
from satsa_generator.seeds.manager import SeedManager


def test_generate_m2_records_populates_all_families(fixture_config_path, master_seed):
    config = load_config(fixture_config_path)
    seeds = SeedManager(master_seed)
    ids = IDService(config.dataset_namespace)

    records = _generate_m2_records(config, seeds, ids)
    assert len(records) == 18
    for family_records in records:
        assert len(family_records) > 0


def test_build_m2_fixture_convenience_alias(tmp_path, fixture_config_path, master_seed):
    result = build_m2_fixture(fixture_config_path, master_seed, output_root=tmp_path / "m2_alias")
    assert result.operational_root.exists()
    assert result.manifest_path.is_file()
    assert result.record_counts["alert"] > 0
    assert result.record_counts["case"] > 0


def test_build_fixture_rejects_non_deterministic_tier(tmp_path, master_seed, monkeypatch):

    config_dict = {
        "dataset_namespace": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "tier": "small",
        "split": "development",
        "organizations": [
            {
                "org_id": "CSE-001",
                "name": "Org 1",
                "cohort": "COHORT-A",
                "sector": "SECTOR-A",
                "source_profile": "SRC-A",
                "scale_band": "small",
                "operating_model": "centralized_24x7",
            }
        ],
        "periods": [
            {
                "period_id": "P01",
                "start_utc": "2025-01-01T00:00:00Z",
                "end_utc": "2025-04-01T00:00:00Z",
            }
        ],
    }
    import json

    cfg_file = tmp_path / "non_fixture_config.json"
    cfg_file.write_text(json.dumps(config_dict), encoding="utf-8")

    with pytest.raises(FixtureBuildError, match="only accepts tier=deterministic_fixture"):
        build_fixture(cfg_file, master_seed, milestone="m2", output_root=tmp_path / "out")
