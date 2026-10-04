from __future__ import annotations

import pytest

from satsa_generator.core.errors import SeedError
from satsa_generator.seeds.manager import SeedManager

STREAM = "development/fixture/CSE-001/P01/submission/timing/v1"


def test_same_master_seed_and_label_produce_same_child_seed(master_seed):
    first = SeedManager(master_seed).get_child_seed_bytes(STREAM)
    second = SeedManager(master_seed).get_child_seed_bytes(STREAM)

    assert first == second


def test_same_stream_produces_same_values_across_runs(master_seed):
    first = SeedManager(master_seed).get_rng(STREAM).integers(0, 10_000, size=20)
    second = SeedManager(master_seed).get_rng(STREAM).integers(0, 10_000, size=20)

    assert first.tolist() == second.tolist()


def test_different_streams_are_independent(master_seed):
    manager = SeedManager(master_seed)

    assert manager.get_child_seed_bytes(STREAM) != manager.get_child_seed_bytes(
        STREAM.replace("timing", "attributes")
    )


def test_different_master_seeds_change_child_seed(master_seed, different_master_seed):
    assert SeedManager(master_seed).get_child_seed_bytes(STREAM) != SeedManager(
        different_master_seed
    ).get_child_seed_bytes(STREAM)


def test_unnamed_stream_is_rejected(master_seed):
    with pytest.raises(SeedError, match="must not be empty"):
        SeedManager(master_seed).get_rng("")


def test_known_answer_for_pinned_algorithm(master_seed):
    assert SeedManager(master_seed).verify_known_answer(STREAM, 3353372658309250958)


def test_public_ledger_is_sorted_and_contains_no_seed(master_seed):
    manager = SeedManager(master_seed)
    manager.get_rng("z/stream")
    manager.get_rng("a/stream")

    ledger = manager.public_ledger()
    assert list(ledger) == ["a/stream", "z/stream"]
    assert master_seed.hex() not in str(ledger)
