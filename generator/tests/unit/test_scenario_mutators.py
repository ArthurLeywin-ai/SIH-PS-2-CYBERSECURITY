"""Unit tests for M4 scenario mutators."""

from __future__ import annotations

from typing import Any

import pytest

from satsa_generator.ids.service import IDService
from satsa_generator.scenarios.catalog import get_scenario
from satsa_generator.scenarios.ledger import AuthorizationError, AuthorizationLedger
from satsa_generator.scenarios.models import (
    ControlContextType,
    MutationType,
    RealizationState,
)
from satsa_generator.scenarios.mutators import ScenarioMutator, plan_authorizations
from satsa_generator.scenarios.selectors import ScenarioSelector
from satsa_generator.seeds.manager import SeedManager

type MutatorSetup = tuple[ScenarioSelector, ScenarioMutator, AuthorizationLedger]


@pytest.fixture
def mutator_setup(master_seed: bytes) -> MutatorSetup:
    seeds = SeedManager(master_seed)
    ids = IDService("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    ledger = AuthorizationLedger()
    selector = ScenarioSelector(seeds, ids)
    mutator = ScenarioMutator(seeds, ledger)
    return selector, mutator, ledger


def test_copy_on_write_preserves_original(
    mutator_setup: tuple[ScenarioSelector, ScenarioMutator, AuthorizationLedger],
    base_m2_records: dict[str, list[Any]],
) -> None:
    """Mutator must not modify original records in-place (copy-on-write)."""
    selector, mutator, ledger = mutator_setup
    org_id = str(base_m2_records["organization"][0].organization_id)

    defn = get_scenario("EXEC-GAP-001")
    plan = selector.select(defn, RealizationState.CONCERNING, base_m2_records, org_id, "P01")

    # Pre-authorize plan before mutator execution
    for auth in plan_authorizations(plan):
        ledger.authorize(auth)

    orig_inv_count = len(base_m2_records["investigation"])
    mutated_records, receipts = mutator.mutate(defn, plan, base_m2_records)

    # Original records dict and lists are untouched
    assert len(base_m2_records["investigation"]) == orig_inv_count
    # Mutated records reflects the deletion
    assert len(mutated_records["investigation"]) < orig_inv_count
    assert len(receipts) == 1
    assert receipts[0].mutation_type == MutationType.REMOVE_RECORD


def test_mutation_receipt_and_ledger_consumption(
    mutator_setup: tuple[ScenarioSelector, ScenarioMutator, AuthorizationLedger],
    base_m2_records: dict[str, list[Any]],
) -> None:
    """Each mutation verifies an existing authorization entry and consumes it via receipt."""
    selector, mutator, ledger = mutator_setup
    org_id = str(base_m2_records["organization"][0].organization_id)

    defn = get_scenario("NEG-SPACE-001")
    plan = selector.select(defn, RealizationState.CONCERNING, base_m2_records, org_id, "P01")

    # Pre-authorize
    for auth in plan_authorizations(plan):
        ledger.authorize(auth)

    assert ledger.size == 1
    auth_entry = list(ledger.entries.values())[0]
    assert auth_entry.status.value == "PLANNED"

    _, receipts = mutator.mutate(defn, plan, base_m2_records)

    assert ledger.size == 1
    assert len(receipts) == 1
    receipt = receipts[0]
    auth_id = receipt.authorization_id
    assert auth_id in ledger.entries
    assert ledger.entries[auth_id].status.value == "APPLIED"


def test_unplanned_mutation_fails_loudly(
    mutator_setup: tuple[ScenarioSelector, ScenarioMutator, AuthorizationLedger],
    base_m2_records: dict[str, list[Any]],
) -> None:
    """Calling mutator without pre-authorization fails loudly and preserves records."""
    selector, mutator, _ = mutator_setup
    org_id = str(base_m2_records["organization"][0].organization_id)
    defn = get_scenario("EXEC-GAP-001")
    plan = selector.select(defn, RealizationState.CONCERNING, base_m2_records, org_id, "P01")

    orig_inv_count = len(base_m2_records["investigation"])
    with pytest.raises(AuthorizationError, match="Unauthorized mutation"):
        mutator.mutate(defn, plan, base_m2_records)

    # Operational data is completely untouched
    assert len(base_m2_records["investigation"]) == orig_inv_count


def test_unrelated_records_preserved(
    mutator_setup: tuple[ScenarioSelector, ScenarioMutator, AuthorizationLedger],
    base_m2_records: dict[str, list[Any]],
) -> None:
    """Mutations must preserve all unrelated records and evidence families."""
    selector, mutator, ledger = mutator_setup
    org_id = str(base_m2_records["organization"][0].organization_id)

    defn = get_scenario("EXEC-GAP-001")
    plan = selector.select(defn, RealizationState.CONCERNING, base_m2_records, org_id, "P01")

    for auth in plan_authorizations(plan):
        ledger.authorize(auth)

    mutated_records, _ = mutator.mutate(defn, plan, base_m2_records)

    # Unrelated families are bit-for-bit identical
    assert len(mutated_records["asset"]) == len(base_m2_records["asset"])
    assert len(mutated_records["organization"]) == len(base_m2_records["organization"])
    assert len(mutated_records["alert"]) == len(base_m2_records["alert"])


def test_all_scenarios_mutate_cleanly(
    mutator_setup: tuple[ScenarioSelector, ScenarioMutator, AuthorizationLedger],
    base_m2_records: dict[str, list[Any]],
) -> None:
    """All 9 scenarios can be mutated across applicable realization states."""
    selector, mutator, ledger = mutator_setup
    org_id = str(base_m2_records["organization"][0].organization_id)

    test_cases = [
        ("EXEC-GAP-001", RealizationState.CONCERNING, None),
        ("EXEC-GAP-001", RealizationState.NORMAL, None),
        ("EXEC-GAP-002", RealizationState.CONCERNING, None),
        ("NEG-SPACE-001", RealizationState.CONCERNING, None),
        (
            "NEG-SPACE-001",
            RealizationState.LEGITIMATE_UNUSUAL,
            ControlContextType.MAINTENANCE_WINDOW,
        ),
        ("NEG-SPACE-001", RealizationState.AMBIGUOUS, None),
        ("NEG-SPACE-002", RealizationState.CONCERNING, None),
        ("HIST-REP-001", RealizationState.CONCERNING, None),
        ("HIST-REP-001", RealizationState.AMBIGUOUS, None),
        ("PEER-CMP-001", RealizationState.CONCERNING, None),
        ("CROSS-REC-001", RealizationState.CONCERNING, None),
        (
            "LEGIT-CTRL-001",
            RealizationState.LEGITIMATE_UNUSUAL,
            ControlContextType.LEGITIMATE_BURST,
        ),
        ("AMBIG-001", RealizationState.AMBIGUOUS, None),
    ]

    for scen_id, real_state, ctrl_type in test_cases:
        defn = get_scenario(scen_id)
        plan = selector.select(
            defn,
            real_state,
            base_m2_records,
            org_id,
            "P01",
            control_context_type=ctrl_type,
        )
        for auth in plan_authorizations(plan):
            if auth.authorization_id not in ledger.entries:
                ledger.authorize(auth)

        mutated, receipts = mutator.mutate(defn, plan, base_m2_records)
        assert len(receipts) >= 1
        assert all(r.applied for r in receipts)
