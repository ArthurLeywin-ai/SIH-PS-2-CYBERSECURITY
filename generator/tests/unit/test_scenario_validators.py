"""Unit tests for M4 scenario validators."""

from __future__ import annotations

from typing import Any

import pytest

from satsa_generator.ids.service import IDService
from satsa_generator.scenarios.catalog import get_scenario
from satsa_generator.scenarios.controls import LegitimateControlEngine
from satsa_generator.scenarios.ledger import AuthorizationLedger
from satsa_generator.scenarios.models import (
    AuthorizationStatus,
    ControlContextType,
    RealizationState,
)
from satsa_generator.scenarios.mutators import ScenarioMutator, plan_authorizations
from satsa_generator.scenarios.selectors import ScenarioSelector
from satsa_generator.scenarios.validators import (
    ScenarioValidationError,
    ScenarioValidator,
)
from satsa_generator.seeds.manager import SeedManager

type ValidatorSuite = tuple[
    ScenarioSelector,
    ScenarioMutator,
    LegitimateControlEngine,
    ScenarioValidator,
    AuthorizationLedger,
]


@pytest.fixture
def validator_suite(master_seed: bytes) -> ValidatorSuite:
    seeds = SeedManager(master_seed)
    ids = IDService("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    ledger = AuthorizationLedger()
    selector = ScenarioSelector(seeds, ids)
    mutator = ScenarioMutator(seeds, ledger)
    controls = LegitimateControlEngine(ids, seeds)
    validator = ScenarioValidator(ledger)
    return selector, mutator, controls, validator, ledger


def test_validator_read_only_and_success(
    validator_suite: ValidatorSuite,
    base_m2_records: dict[str, list[Any]],
) -> None:
    """Validator operates in read-only manner and marks authorization VALIDATED on success."""
    selector, mutator, _, validator, ledger = validator_suite
    org_id = str(base_m2_records["organization"][0].organization_id)

    defn = get_scenario("EXEC-GAP-001")
    plan = selector.select(defn, RealizationState.CONCERNING, base_m2_records, org_id, "P01")

    for auth in plan_authorizations(plan):
        ledger.authorize(auth)

    mutated_records, receipts = mutator.mutate(defn, plan, base_m2_records)
    inv_count_before = len(mutated_records["investigation"])

    report = validator.validate(plan, mutated_records, receipts, fail_loudly=True)

    # Read-only check: records dictionary was not modified
    assert len(mutated_records["investigation"]) == inv_count_before

    assert report.passed is True
    assert len(report.checks) > 0
    assert len(report.errors) == 0

    # Ledger entry must now be VALIDATED
    auth_id = receipts[0].authorization_id
    assert ledger.entries[auth_id].status == AuthorizationStatus.VALIDATED


def test_validator_fails_loudly_when_condition_unmet(
    validator_suite: ValidatorSuite,
    base_m2_records: dict[str, list[Any]],
) -> None:
    """Validator fails loudly and marks authorization FAILED if condition is not satisfied."""
    selector, mutator, _, validator, ledger = validator_suite
    org_id = str(base_m2_records["organization"][0].organization_id)

    defn = get_scenario("EXEC-GAP-001")
    plan = selector.select(defn, RealizationState.CONCERNING, base_m2_records, org_id, "P01")

    for auth in plan_authorizations(plan):
        ledger.authorize(auth)

    # Intentionally validate against unmutated records where investigations still exist!
    _, receipts = mutator.mutate(defn, plan, base_m2_records)

    with pytest.raises(ScenarioValidationError, match="Expected 0 investigations"):
        validator.validate(plan, base_m2_records, receipts, fail_loudly=True)

    auth_id = receipts[0].authorization_id
    assert ledger.entries[auth_id].status == AuthorizationStatus.FAILED


def test_validator_legitimate_control_verification(
    validator_suite: ValidatorSuite,
    base_m2_records: dict[str, list[Any]],
) -> None:
    """Validator confirms legitimate control context presence for LEGITIMATE_UNUSUAL."""
    selector, mutator, controls, validator, ledger = validator_suite
    org_id = str(base_m2_records["organization"][0].organization_id)

    defn = get_scenario("NEG-SPACE-001")
    plan = selector.select(
        defn,
        RealizationState.LEGITIMATE_UNUSUAL,
        base_m2_records,
        org_id,
        "P01",
        control_context_type=ControlContextType.MAINTENANCE_WINDOW,
        control_context_description="Scheduled storage array maintenance",
    )

    _, updated_records = controls.declare_control(plan, base_m2_records, is_complete=True)

    for auth in plan_authorizations(plan):
        ledger.authorize(auth)

    mutated_records, receipts = mutator.mutate(defn, plan, updated_records)

    report = validator.validate(plan, mutated_records, receipts, fail_loudly=True)
    assert report.passed is True
    assert any("SUSPENDED" in check for check in report.checks)
    assert any("Maintenance" in check for check in report.checks)


def test_validator_ambiguous_verification(
    validator_suite: ValidatorSuite,
    base_m2_records: dict[str, list[Any]],
) -> None:
    """Validator confirms ambiguous state for AMBIG-001."""
    selector, mutator, _, validator, ledger = validator_suite
    org_id = str(base_m2_records["organization"][0].organization_id)

    defn = get_scenario("AMBIG-001")
    plan = selector.select(defn, RealizationState.AMBIGUOUS, base_m2_records, org_id, "P01")

    for auth in plan_authorizations(plan):
        ledger.authorize(auth)

    mutated_records, receipts = mutator.mutate(defn, plan, base_m2_records)
    report = validator.validate(plan, mutated_records, receipts, fail_loudly=True)

    assert report.passed is True
    assert any("Ambiguous" in check for check in report.checks)
