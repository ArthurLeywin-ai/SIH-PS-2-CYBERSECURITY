from __future__ import annotations

import json

import pytest

from satsa_generator.config.models import load_config
from satsa_generator.core.errors import ConfigurationError


def test_valid_fixture_configuration_loads(fixture_config_path):
    config = load_config(fixture_config_path)

    assert config.dataset_namespace == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    assert len(config.organizations) == 3
    assert len(config.periods) == 2
    assert len(config.config_hash()) == 64


def test_invalid_configuration_fails_loudly(tmp_path, fixture_config_path):
    raw = json.loads(fixture_config_path.read_text(encoding="utf-8"))
    raw["periods"][0]["end_utc"] = raw["periods"][0]["start_utc"]
    invalid = tmp_path / "invalid.json"
    invalid.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(ConfigurationError, match="end_utc must be later"):
        load_config(invalid)


def test_missing_required_configuration_fails_clearly(tmp_path, fixture_config_path):
    raw = json.loads(fixture_config_path.read_text(encoding="utf-8"))
    del raw["dataset_namespace"]
    invalid = tmp_path / "missing.json"
    invalid.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(ConfigurationError, match="dataset_namespace"):
        load_config(invalid)


def test_unknown_configuration_key_is_rejected(tmp_path, fixture_config_path):
    raw = json.loads(fixture_config_path.read_text(encoding="utf-8"))
    raw["typo_field"] = True
    invalid = tmp_path / "unknown.json"
    invalid.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(ConfigurationError, match="Extra inputs are not permitted"):
        load_config(invalid)


def test_detector_configuration_is_rejected(tmp_path, fixture_config_path):
    raw = json.loads(fixture_config_path.read_text(encoding="utf-8"))
    raw["detector_threshold"] = 0.9
    invalid = tmp_path / "detector.json"
    invalid.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(ConfigurationError, match="Forbidden detector-related"):
        load_config(invalid)


def test_absolute_versioned_output_path_is_rejected(tmp_path, fixture_config_path):
    raw = json.loads(fixture_config_path.read_text(encoding="utf-8"))
    raw["output_root"] = str(tmp_path / "machine-specific")
    invalid = tmp_path / "absolute.json"
    invalid.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(ConfigurationError, match="must be relative"):
        load_config(invalid)
