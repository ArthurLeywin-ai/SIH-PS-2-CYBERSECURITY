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
