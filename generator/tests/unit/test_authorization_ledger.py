"""Unit tests for M4 authorization ledger."""

from __future__ import annotations

import pytest

from satsa_generator.scenarios.ledger import (
    AuthorizationError,
    AuthorizationLedger,
)
from satsa_generator.scenarios.models import (
    AuthorizationEntry,
    AuthorizationStatus,
    MutationReceipt,
    MutationType,
    RealizationState,
)


def _make_entry(
    auth_id: str = "auth-1",
    scenario_id: str = "EXEC-GAP-001",
    target_ids: tuple[str, ...] = ("case-001",),
    mutation_type: MutationType = MutationType.REMOVE_RECORD,
    target_family: str = "investigation",
) -> AuthorizationEntry:
    return AuthorizationEntry(
        authorization_id=auth_id,
        scenario_id=scenario_id,
        plan_id="plan-1",
        realization=RealizationState.CONCERNING,
        target_record_ids=target_ids,
        target_family=target_family,
        mutation_type=mutation_type,
        expected_semantic_effect="Remove investigation",
        seed_label="dev/seed/1",
    )


def _make_receipt(
    auth_id: str = "auth-1",
    scenario_id: str = "EXEC-GAP-001",
    target_ids: tuple[str, ...] = ("case-001",),
    mutation_type: MutationType = MutationType.REMOVE_RECORD,
    target_family: str = "investigation",
) -> MutationReceipt:
    return MutationReceipt(
        authorization_id=auth_id,
        plan_id="plan-1",
        scenario_id=scenario_id,
        mutation_type=mutation_type,
        target_record_ids=target_ids,
        target_family=target_family,
        target_fields=("case_id",),
        before_state={"count": 1},
        after_state={"count": 0},
    )


def test_authorize_and_consume() -> None:
    """Register authorization and consume it with a receipt."""
    ledger = AuthorizationLedger()
    entry = _make_entry()
    ledger.authorize(entry)

    assert ledger.size == 1
    assert ledger.is_authorized("case-001", MutationType.REMOVE_RECORD.value)

    receipt = _make_receipt()
    ledger.consume(receipt)

    assert ledger.entries["auth-1"].status == AuthorizationStatus.APPLIED
    # Already consumed, so is_authorized returns False
    assert not ledger.is_authorized("case-001", MutationType.REMOVE_RECORD.value)


def test_duplicate_authorization_rejected() -> None:
    """Duplicate authorization IDs must raise AuthorizationError."""
    ledger = AuthorizationLedger()
    entry = _make_entry(auth_id="duplicate-id")
    ledger.authorize(entry)

    with pytest.raises(AuthorizationError, match="Duplicate authorization ID"):
        ledger.authorize(entry)


def test_conflicting_authorization_rejected() -> None:
    """Conflicting mutations on the same target must raise AuthorizationError."""
    ledger = AuthorizationLedger()
    entry1 = _make_entry(auth_id="auth-1", scenario_id="EXEC-GAP-001", target_ids=("target-1",))
    entry2 = _make_entry(auth_id="auth-2", scenario_id="EXEC-GAP-002", target_ids=("target-1",))

    ledger.authorize(entry1)
    with pytest.raises(AuthorizationError, match="Conflicting authorization"):
        ledger.authorize(entry2)


def test_unauthorized_consumption_rejected() -> None:
    """Consuming an authorization that was never registered must raise AuthorizationError."""
    ledger = AuthorizationLedger()
    receipt = _make_receipt(auth_id="unregistered-auth")

    with pytest.raises(AuthorizationError, match="Unauthorized mutation"):
        ledger.consume(receipt)


def test_double_consumption_rejected() -> None:
    """Consuming the same authorization twice must raise AuthorizationError."""
    ledger = AuthorizationLedger()
    entry = _make_entry()
    ledger.authorize(entry)
    receipt = _make_receipt()

    ledger.consume(receipt)
    with pytest.raises(AuthorizationError, match="already been consumed"):
        ledger.consume(receipt)


def test_status_transitions() -> None:
    """Test transitions from PLANNED -> APPLIED -> VALIDATED or FAILED."""
    ledger = AuthorizationLedger()
    entry = _make_entry()
    ledger.authorize(entry)
    assert ledger.entries["auth-1"].status == AuthorizationStatus.PLANNED

    receipt = _make_receipt()
    ledger.consume(receipt)
    assert ledger.entries["auth-1"].status == AuthorizationStatus.APPLIED

    ledger.mark_validated("auth-1")
    assert ledger.entries["auth-1"].status == AuthorizationStatus.VALIDATED

    # Cannot validate unknown ID
    with pytest.raises(AuthorizationError, match="Cannot validate unknown"):
        ledger.mark_validated("unknown-id")


def test_unused_authorization_completeness_check() -> None:
    """Ledger completeness check must fail if planned authorizations were never consumed."""
    ledger = AuthorizationLedger()
    entry = _make_entry(auth_id="unused-auth")
    ledger.authorize(entry)

    with pytest.raises(AuthorizationError, match="unused authorization"):
        ledger.validate_completeness()

    # Once consumed, completeness check succeeds
    receipt = _make_receipt(auth_id="unused-auth")
    ledger.consume(receipt)
    assert ledger.validate_completeness() == []


def test_export_private() -> None:
    """Exporting ledger returns serializable dictionary list in insertion order."""
    ledger = AuthorizationLedger()
    ledger.authorize(_make_entry("auth-1"))
    ledger.authorize(_make_entry("auth-2", target_ids=("target-2",)))

    exported = ledger.export_private()
    assert len(exported) == 2
    assert exported[0]["authorization_id"] == "auth-1"
    assert exported[1]["authorization_id"] == "auth-2"
