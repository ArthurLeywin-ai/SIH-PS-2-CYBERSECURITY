from __future__ import annotations

import uuid

import pytest

from satsa_generator.ids.service import IDService

NAMESPACE = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


def test_ids_are_deterministic_and_valid_uuids():
    service = IDService(NAMESPACE)
    first = service.generate("alert", "CSE-001", "P01", "0001")
    second = service.generate("alert", "CSE-001", "P01", "0001")

    assert first == second
    assert str(uuid.UUID(first)) == first


def test_ids_are_stable_across_service_instances():
    assert IDService(NAMESPACE).generate("organization", "CSE-001") == IDService(
        NAMESPACE
    ).generate("organization", "CSE-001")


def test_entity_contexts_do_not_collide():
    service = IDService(NAMESPACE)

    assert service.generate("alert", "CSE-001", "0001") != service.generate(
        "case", "CSE-001", "0001"
    )


def test_empty_or_non_string_key_part_is_rejected():
    service = IDService(NAMESPACE)
    with pytest.raises(ValueError, match="must not be empty"):
        service.generate("alert", "")
    with pytest.raises(TypeError, match="must be a string"):
        service.generate("alert", 1)  # type: ignore[arg-type]
