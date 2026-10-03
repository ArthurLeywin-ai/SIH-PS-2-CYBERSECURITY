from __future__ import annotations

import uuid

from hypothesis import given
from hypothesis import strategies as st

from satsa_generator.ids.service import IDService

NAMESPACE = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
KEY_PART = st.text(
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd"),
        whitelist_characters="-_.",
    ),
    min_size=1,
    max_size=40,
).filter(lambda value: bool(value.strip()))


@given(KEY_PART, KEY_PART, KEY_PART)
def test_uuidv5_is_stable_for_arbitrary_valid_logical_keys(first, second, third):
    service = IDService(NAMESPACE)
    generated = service.generate(first, second, third)

    assert generated == IDService(NAMESPACE).generate(first, second, third)
    assert uuid.UUID(generated).version == 5
