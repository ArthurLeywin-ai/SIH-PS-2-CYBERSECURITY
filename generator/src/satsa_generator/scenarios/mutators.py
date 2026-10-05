"""
Scenario mutators — narrowly scoped, authorized, deterministic mutations.

Every mutation MUST:
- affect only authorized records
- preserve unrelated fields
- preserve referential integrity (unless the scenario explicitly requires it)
- preserve deterministic IDs
- use a named deterministic RNG stream
- consume a pre-existing AuthorizationEntry from the authorization ledger
- emit a MutationReceipt for the authorization ledger

The mutator does NOT:
- self-authorize mutations (authorization happens prior to mutator execution)
- globally rewrite datasets
- use random mutation without a named stream
- silently repair mutations
- import detector thresholds or scores
"""

from __future__ import annotations

from typing import Any

from satsa_generator.core.errors import GeneratorError
from satsa_generator.scenarios.ledger import AuthorizationLedger
from satsa_generator.scenarios.models import (
    AuthorizationEntry,
    AuthorizationStatus,
    MutationReceipt,
    MutationType,
    RealizationState,
    ScenarioDefinition,
    ScenarioPlan,
)
from satsa_generator.seeds.manager import SeedManager


class MutationError(GeneratorError):
    """Raised when a mutation fails or violates safety constraints."""


class ScenarioMutator:
    """Applies narrowly scoped mutations to M2 fixture records.

    Uses copy-on-write semantics: mutated records are returned as new
    lists alongside the originals. The mutator never modifies records
    in place.
    """

    def __init__(
        self,
        seeds: SeedManager,
        ledger: AuthorizationLedger,
    ) -> None:
        self._seeds = seeds
        self._ledger = ledger

    def mutate(
        self,
        scenario: ScenarioDefinition,
        plan: ScenarioPlan,
        records: dict[str, list[Any]],
    ) -> tuple[dict[str, list[Any]], list[MutationReceipt]]:
        """Apply scenario mutations to a copy of the records.

        Requires pre-existing authorization in the ledger. If no matching
        authorization exists, fails loudly without modifying operational records.

        Args:
            scenario: The scenario definition.
            plan: The validated scenario plan.
            records: Dict mapping family name to list of fixture records.

        Returns:
            Tuple of (mutated_records, list of mutation receipts).

        Raises:
            MutationError: If the mutator fails.
            AuthorizationError: If the mutation is not pre-authorized.
        """
        mutator_fn = _SCENARIO_MUTATORS.get(scenario.scenario_id)
        if mutator_fn is None:
            raise MutationError(
                f"No mutator implemented for scenario '{scenario.scenario_id}'",
                context={"scenario_id": scenario.scenario_id},
            )

        # Build seed label for deterministic mutation
        seed_label = (
            f"development/scenario/{scenario.scenario_id}/"
            f"{plan.organization_id}/{plan.period_id}/"
            f"{plan.realization}/mutator/v1"
        )

        return mutator_fn(plan, records, self._seeds, self._ledger, seed_label)


# ---------------------------------------------------------------------------
# Utility: deep copy records dict with mutable lists
# ---------------------------------------------------------------------------


def _copy_records(records: dict[str, list[Any]]) -> dict[str, list[Any]]:
    """Shallow copy of record dict with independent list copies."""
    return {k: list(v) for k, v in records.items()}


def _verify_authorization_exists(
    plan: ScenarioPlan,
    mutation_type: MutationType,
    target_ids: tuple[str, ...],
    target_family: str,
    ledger: AuthorizationLedger,
) -> AuthorizationEntry:
    """Verify that an authorization entry was pre-planned in the ledger.

    Mutators MUST NOT create authorizations. If no valid authorization exists,
    this fails loudly with AuthorizationError, guaranteeing operational data
    remains untouched.
    """
    auth_id = f"{plan.plan_id}:{mutation_type.value}:{target_family}"
    return ledger.verify_authorization(
        authorization_id=auth_id,
        expected_scenario_id=plan.scenario_id,
        expected_mutation_type=mutation_type,
        target_record_ids=target_ids,
        target_family=target_family,
    )


def _consume_authorized_receipt(
    plan: ScenarioPlan,
    mutation_type: MutationType,
    target_ids: tuple[str, ...],
    target_family: str,
    target_fields: tuple[str, ...],
    before_state: dict[str, Any],
    after_state: dict[str, Any],
    ledger: AuthorizationLedger,
) -> MutationReceipt:
    """Consume pre-authorized entry and return MutationReceipt."""
    auth_id = f"{plan.plan_id}:{mutation_type.value}:{target_family}"
    receipt = MutationReceipt(
        authorization_id=auth_id,
        plan_id=plan.plan_id,
        scenario_id=plan.scenario_id,
        mutation_type=mutation_type,
        target_record_ids=target_ids,
        target_family=target_family,
        target_fields=target_fields,
        before_state=before_state,
        after_state=after_state,
        applied=True,
    )
    ledger.consume(receipt)
    return receipt


# ---------------------------------------------------------------------------
# Authorization planning (private, called by ScenarioEngine BEFORE mutation)
# ---------------------------------------------------------------------------


def _plan_auth_exec_gap_001(plan: ScenarioPlan) -> list[AuthorizationEntry]:
    case_id = plan.target_record_ids[0]
    if plan.realization in (RealizationState.CONCERNING, RealizationState.LEGITIMATE_UNUSUAL):
        m_type = MutationType.REMOVE_RECORD
        t_fam = "investigation"
        effect = (
            "Remove all investigation records for high-severity case, "
            "creating an execution gap where investigation is expected"
            if plan.realization == RealizationState.CONCERNING
            else (
                "Remove investigations for case with legitimate "
                "automation/exception context explaining the absence"
            )
        )
    elif plan.realization == RealizationState.AMBIGUOUS:
        m_type = MutationType.ALTER_FIELD
        t_fam = "investigation"
        effect = (
            "Partial investigation evidence — insufficient to determine "
            "whether investigation was completed"
        )
    else:  # NORMAL
        m_type = MutationType.ALTER_FIELD
        t_fam = "case"
        effect = "Normal case with investigation present (no-op counterexample)"

    auth_id = f"{plan.plan_id}:{m_type.value}:{t_fam}"
    return [
        AuthorizationEntry(
            authorization_id=auth_id,
            scenario_id=plan.scenario_id,
            plan_id=plan.plan_id,
            realization=plan.realization,
            target_record_ids=(case_id,),
            target_family=t_fam,
            mutation_type=m_type,
            expected_semantic_effect=effect,
            seed_label=plan.seed_label,
            status=AuthorizationStatus.PLANNED,
        )
    ]


def _plan_auth_exec_gap_002(plan: ScenarioPlan) -> list[AuthorizationEntry]:
    case_id = plan.target_record_ids[0]
    t_fam = "escalation"
    if plan.realization in (RealizationState.CONCERNING, RealizationState.LEGITIMATE_UNUSUAL):
        m_type = MutationType.REMOVE_RECORD
        effect = "Remove escalation records for high-severity case"
        if plan.realization == RealizationState.LEGITIMATE_UNUSUAL:
            effect += " (with legitimate emergency workflow context)"
    else:
        m_type = MutationType.ALTER_FIELD
        effect = "Escalation present (normal/ambiguous counterexample)"

    auth_id = f"{plan.plan_id}:{m_type.value}:{t_fam}"
    return [
        AuthorizationEntry(
            authorization_id=auth_id,
            scenario_id=plan.scenario_id,
            plan_id=plan.plan_id,
            realization=plan.realization,
            target_record_ids=(case_id,),
            target_family=t_fam,
            mutation_type=m_type,
            expected_semantic_effect=effect,
            seed_label=plan.seed_label,
            status=AuthorizationStatus.PLANNED,
        )
    ]


def _plan_auth_neg_space_001(plan: ScenarioPlan) -> list[AuthorizationEntry]:
    asset_id = plan.target_record_ids[0]
    t_fam = "monitoring_coverage"
    if plan.realization == RealizationState.CONCERNING:
        m_type = MutationType.ALTER_STATUS
        effect = "Set monitoring coverage to NOT_COVERED for critical asset"
    elif plan.realization == RealizationState.LEGITIMATE_UNUSUAL:
        m_type = MutationType.ALTER_STATUS
        effect = "Set monitoring to SUSPENDED with legitimate maintenance context"
    elif plan.realization == RealizationState.AMBIGUOUS:
        m_type = MutationType.ALTER_STATUS
        effect = "Set monitoring to DEGRADED — insufficient evidence for cause"
    else:
        m_type = MutationType.ALTER_FIELD
        effect = "Normal monitoring coverage (counterexample)"

    auth_id = f"{plan.plan_id}:{m_type.value}:{t_fam}"
    return [
        AuthorizationEntry(
            authorization_id=auth_id,
            scenario_id=plan.scenario_id,
            plan_id=plan.plan_id,
            realization=plan.realization,
            target_record_ids=(asset_id,),
            target_family=t_fam,
            mutation_type=m_type,
            expected_semantic_effect=effect,
            seed_label=plan.seed_label,
            status=AuthorizationStatus.PLANNED,
        )
    ]


def _plan_auth_neg_space_002(plan: ScenarioPlan) -> list[AuthorizationEntry]:
    case_id = plan.target_record_ids[0]
    t_fam = "action"
    if plan.realization in (RealizationState.CONCERNING, RealizationState.LEGITIMATE_UNUSUAL):
        m_type = MutationType.REMOVE_RECORD
        effect = "Remove remediation actions for TRUE_POSITIVE case"
        if plan.realization == RealizationState.LEGITIMATE_UNUSUAL:
            effect += " (with accepted-risk exception context)"
    else:
        m_type = MutationType.ALTER_FIELD
        effect = "Actions present (normal/ambiguous counterexample)"

    auth_id = f"{plan.plan_id}:{m_type.value}:{t_fam}"
    return [
        AuthorizationEntry(
            authorization_id=auth_id,
            scenario_id=plan.scenario_id,
            plan_id=plan.plan_id,
            realization=plan.realization,
            target_record_ids=(case_id,),
            target_family=t_fam,
            mutation_type=m_type,
            expected_semantic_effect=effect,
            seed_label=plan.seed_label,
            status=AuthorizationStatus.PLANNED,
        )
    ]


def _plan_auth_hist_rep_001(plan: ScenarioPlan) -> list[AuthorizationEntry]:
    m_type = MutationType.ALTER_FIELD
    t_fam = "case"
    if plan.realization == RealizationState.CONCERNING:
        effect = "Recurring FALSE_POSITIVE pattern across multiple cases"
    elif plan.realization == RealizationState.LEGITIMATE_UNUSUAL:
        effect = "Recurring FALSE_POSITIVE with approved suppression/tuning context"
    elif plan.realization == RealizationState.AMBIGUOUS:
        effect = "Ambiguous historical baseline / borderline recurrence pattern"
    else:
        effect = "Normal/varied disposition pattern (counterexample)"

    auth_id = f"{plan.plan_id}:{m_type.value}:{t_fam}"
    return [
        AuthorizationEntry(
            authorization_id=auth_id,
            scenario_id=plan.scenario_id,
            plan_id=plan.plan_id,
            realization=plan.realization,
            target_record_ids=plan.target_record_ids,
            target_family=t_fam,
            mutation_type=m_type,
            expected_semantic_effect=effect,
            seed_label=plan.seed_label,
            status=AuthorizationStatus.PLANNED,
        )
    ]


def _plan_auth_peer_cmp_001(plan: ScenarioPlan) -> list[AuthorizationEntry]:
    m_type = MutationType.ALTER_PROPENSITY
    t_fam = "investigation"
    if plan.realization == RealizationState.CONCERNING:
        effect = "Lower investigation rate vs peers (concerning deviation)"
    elif plan.realization == RealizationState.LEGITIMATE_UNUSUAL:
        effect = "Lower investigation rate with approved automation context"
    elif plan.realization == RealizationState.AMBIGUOUS:
        effect = "Investigation rate difference — insufficient context to classify"
    else:
        effect = "Normal investigation rate among peers"

    auth_id = f"{plan.plan_id}:{m_type.value}:{t_fam}"
    return [
        AuthorizationEntry(
            authorization_id=auth_id,
            scenario_id=plan.scenario_id,
            plan_id=plan.plan_id,
            realization=plan.realization,
            target_record_ids=plan.target_record_ids,
            target_family=t_fam,
            mutation_type=m_type,
            expected_semantic_effect=effect,
            seed_label=plan.seed_label,
            status=AuthorizationStatus.PLANNED,
        )
    ]


def _plan_auth_cross_rec_001(plan: ScenarioPlan) -> list[AuthorizationEntry]:
    if plan.realization == RealizationState.CONCERNING:
        m_type = MutationType.REMOVE_RECORD
        t_fam = "resolution"
        effect = "Resolution absent for closed case with linked alerts (cross-record gap)"
    elif plan.realization == RealizationState.LEGITIMATE_UNUSUAL:
        m_type = MutationType.ALTER_FIELD
        t_fam = "case"
        effect = "Resolution absent but process change explains alternative closure path"
    elif plan.realization == RealizationState.AMBIGUOUS:
        m_type = MutationType.ALTER_FIELD
        t_fam = "case"
        effect = "Partial resolution chain — insufficient to determine completeness"
    else:
        m_type = MutationType.ALTER_FIELD
        t_fam = "case"
        effect = "Full resolution chain present (normal counterexample)"

    auth_id = f"{plan.plan_id}:{m_type.value}:{t_fam}"
    return [
        AuthorizationEntry(
            authorization_id=auth_id,
            scenario_id=plan.scenario_id,
            plan_id=plan.plan_id,
            realization=plan.realization,
            target_record_ids=plan.target_record_ids,
            target_family=t_fam,
            mutation_type=m_type,
            expected_semantic_effect=effect,
            seed_label=plan.seed_label,
            status=AuthorizationStatus.PLANNED,
        )
    ]


def _plan_auth_legit_ctrl_001(plan: ScenarioPlan) -> list[AuthorizationEntry]:
    m_type = MutationType.ADD_CONTEXT_RECORD
    t_fam = "alert"
    effect = f"Alert burst with legitimate control context (realization={plan.realization})"

    auth_id = f"{plan.plan_id}:{m_type.value}:{t_fam}"
    return [
        AuthorizationEntry(
            authorization_id=auth_id,
            scenario_id=plan.scenario_id,
            plan_id=plan.plan_id,
            realization=plan.realization,
            target_record_ids=plan.target_record_ids,
            target_family=t_fam,
            mutation_type=m_type,
            expected_semantic_effect=effect,
            seed_label=plan.seed_label,
            status=AuthorizationStatus.PLANNED,
        )
    ]


def _plan_auth_ambig_001(plan: ScenarioPlan) -> list[AuthorizationEntry]:
    m_type = MutationType.ALTER_STATUS
    t_fam = "investigation"
    effect = (
        f"Investigation evidence insufficient to determine outcome (realization={plan.realization})"
    )

    auth_id = f"{plan.plan_id}:{m_type.value}:{t_fam}"
    return [
        AuthorizationEntry(
            authorization_id=auth_id,
            scenario_id=plan.scenario_id,
            plan_id=plan.plan_id,
            realization=plan.realization,
            target_record_ids=plan.target_record_ids,
            target_family=t_fam,
            mutation_type=m_type,
            expected_semantic_effect=effect,
            seed_label=plan.seed_label,
            status=AuthorizationStatus.PLANNED,
        )
    ]


def plan_authorizations(plan: ScenarioPlan) -> list[AuthorizationEntry]:
    """Deterministically plan required mutation authorizations for a scenario plan.

    Called by the scenario planner/engine BEFORE any mutator executes.
    Mutators cannot self-authorize.
    """
    planner_fn = _SCENARIO_AUTH_PLANNERS.get(plan.scenario_id)
    if planner_fn is None:
        raise MutationError(
            f"No authorization planner implemented for scenario '{plan.scenario_id}'",
            context={"scenario_id": plan.scenario_id},
        )
    return planner_fn(plan)


# ---------------------------------------------------------------------------
# EXEC-GAP-001: Missing investigation for high-severity case
# ---------------------------------------------------------------------------


def _mutate_exec_gap_001(
    plan: ScenarioPlan,
    records: dict[str, list[Any]],
    seeds: SeedManager,
    ledger: AuthorizationLedger,
    seed_label: str,
) -> tuple[dict[str, list[Any]], list[MutationReceipt]]:
    """Remove investigations linked to target case, or add context for controls."""
    case_id = plan.target_record_ids[0]

    if plan.realization in (RealizationState.CONCERNING, RealizationState.LEGITIMATE_UNUSUAL):
        mutation_type = MutationType.REMOVE_RECORD
        target_family = "investigation"
    elif plan.realization == RealizationState.AMBIGUOUS:
        mutation_type = MutationType.ALTER_FIELD
        target_family = "investigation"
    else:  # NORMAL
        mutation_type = MutationType.ALTER_FIELD
        target_family = "case"

    # Pre-authorization verification: fails loudly before touching records if unauthorized
    _verify_authorization_exists(plan, mutation_type, (case_id,), target_family, ledger)

    result = _copy_records(records)
    receipts: list[MutationReceipt] = []

    if plan.realization == RealizationState.CONCERNING:
        investigations = result.get("investigation", [])
        before_ids = [
            str(inv.investigation_id) for inv in investigations if str(inv.case_id) == case_id
        ]
        result["investigation"] = [inv for inv in investigations if str(inv.case_id) != case_id]
        receipts.append(
            _consume_authorized_receipt(
                plan=plan,
                mutation_type=mutation_type,
                target_ids=(case_id,),
                target_family=target_family,
                target_fields=("case_id",),
                before_state={"investigation_ids": before_ids},
                after_state={"investigation_ids": []},
                ledger=ledger,
            )
        )
    elif plan.realization == RealizationState.NORMAL:
        receipts.append(
            _consume_authorized_receipt(
                plan=plan,
                mutation_type=mutation_type,
                target_ids=(case_id,),
                target_family=target_family,
                target_fields=("case_status",),
                before_state={"status": "existing"},
                after_state={"status": "existing"},
                ledger=ledger,
            )
        )
    elif plan.realization == RealizationState.LEGITIMATE_UNUSUAL:
        investigations = result.get("investigation", [])
        before_ids = [
            str(inv.investigation_id) for inv in investigations if str(inv.case_id) == case_id
        ]
        result["investigation"] = [inv for inv in investigations if str(inv.case_id) != case_id]
        receipts.append(
            _consume_authorized_receipt(
                plan=plan,
                mutation_type=mutation_type,
                target_ids=(case_id,),
                target_family=target_family,
                target_fields=("case_id",),
                before_state={"investigation_ids": before_ids},
                after_state={"investigation_ids": []},
                ledger=ledger,
            )
        )
    elif plan.realization == RealizationState.AMBIGUOUS:
        investigations = result.get("investigation", [])
        case_invs = [inv for inv in investigations if str(inv.case_id) == case_id]
        if len(case_invs) > 1:
            removed_ids = [str(inv.investigation_id) for inv in case_invs[1:]]
            result["investigation"] = [
                inv for inv in investigations if str(inv.investigation_id) not in removed_ids
            ]
        receipts.append(
            _consume_authorized_receipt(
                plan=plan,
                mutation_type=mutation_type,
                target_ids=(case_id,),
                target_family=target_family,
                target_fields=("investigation_status",),
                before_state={"investigation_count": len(case_invs)},
                after_state={"investigation_count": min(1, len(case_invs))},
                ledger=ledger,
            )
        )

    return result, receipts


# ---------------------------------------------------------------------------
# EXEC-GAP-002: Missing escalation
# ---------------------------------------------------------------------------


def _mutate_exec_gap_002(
    plan: ScenarioPlan,
    records: dict[str, list[Any]],
    seeds: SeedManager,
    ledger: AuthorizationLedger,
    seed_label: str,
) -> tuple[dict[str, list[Any]], list[MutationReceipt]]:
    """Remove escalations linked to target case."""
    case_id = plan.target_record_ids[0]
    target_family = "escalation"
    if plan.realization in (RealizationState.CONCERNING, RealizationState.LEGITIMATE_UNUSUAL):
        mutation_type = MutationType.REMOVE_RECORD
    else:
        mutation_type = MutationType.ALTER_FIELD

    _verify_authorization_exists(plan, mutation_type, (case_id,), target_family, ledger)

    result = _copy_records(records)
    receipts: list[MutationReceipt] = []

    if plan.realization in (RealizationState.CONCERNING, RealizationState.LEGITIMATE_UNUSUAL):
        escalations = result.get("escalation", [])
        before_ids = [str(esc.escalation_id) for esc in escalations if str(esc.case_id) == case_id]
        result["escalation"] = [esc for esc in escalations if str(esc.case_id) != case_id]
        receipts.append(
            _consume_authorized_receipt(
                plan=plan,
                mutation_type=mutation_type,
                target_ids=(case_id,),
                target_family=target_family,
                target_fields=("case_id",),
                before_state={"escalation_ids": before_ids},
                after_state={"escalation_ids": []},
                ledger=ledger,
            )
        )
    else:
        receipts.append(
            _consume_authorized_receipt(
                plan=plan,
                mutation_type=mutation_type,
                target_ids=(case_id,),
                target_family=target_family,
                target_fields=("escalation_status",),
                before_state={"status": "existing"},
                after_state={"status": "existing"},
                ledger=ledger,
            )
        )

    return result, receipts


# ---------------------------------------------------------------------------
# NEG-SPACE-001: Monitoring coverage gap
# ---------------------------------------------------------------------------


def _mutate_neg_space_001(
    plan: ScenarioPlan,
    records: dict[str, list[Any]],
    seeds: SeedManager,
    ledger: AuthorizationLedger,
    seed_label: str,
) -> tuple[dict[str, list[Any]], list[MutationReceipt]]:
    """Alter monitoring coverage state for target asset."""
    asset_id = plan.target_record_ids[0]
    target_family = "monitoring_coverage"
    if plan.realization in (
        RealizationState.CONCERNING,
        RealizationState.LEGITIMATE_UNUSUAL,
        RealizationState.AMBIGUOUS,
    ):
        mutation_type = MutationType.ALTER_STATUS
    else:
        mutation_type = MutationType.ALTER_FIELD

    _verify_authorization_exists(plan, mutation_type, (asset_id,), target_family, ledger)

    result = _copy_records(records)
    receipts: list[MutationReceipt] = []

    coverages = result.get("monitoring_coverage", [])
    asset_covs = [c for c in coverages if str(c.asset_id) == asset_id]

    if plan.realization == RealizationState.CONCERNING:
        new_state = "NOT_COVERED"
    elif plan.realization == RealizationState.LEGITIMATE_UNUSUAL:
        new_state = "SUSPENDED"
    elif plan.realization == RealizationState.AMBIGUOUS:
        new_state = "DEGRADED"
    else:
        new_state = None

    if new_state is not None:
        new_covs = [
            cov.model_copy(update={"coverage_state": new_state})
            if str(cov.asset_id) == asset_id
            else cov
            for cov in coverages
        ]
        result["monitoring_coverage"] = new_covs
        receipts.append(
            _consume_authorized_receipt(
                plan=plan,
                mutation_type=mutation_type,
                target_ids=(asset_id,),
                target_family=target_family,
                target_fields=("coverage_state",),
                before_state={"coverage_states": [c.coverage_state for c in asset_covs]},
                after_state={"coverage_states": [new_state] * len(asset_covs)},
                ledger=ledger,
            )
        )
    else:
        receipts.append(
            _consume_authorized_receipt(
                plan=plan,
                mutation_type=mutation_type,
                target_ids=(asset_id,),
                target_family=target_family,
                target_fields=("coverage_state",),
                before_state={"coverage_states": [c.coverage_state for c in asset_covs]},
                after_state={"coverage_states": [c.coverage_state for c in asset_covs]},
                ledger=ledger,
            )
        )

    return result, receipts


# ---------------------------------------------------------------------------
# NEG-SPACE-002: Missing action/remediation
# ---------------------------------------------------------------------------


def _mutate_neg_space_002(
    plan: ScenarioPlan,
    records: dict[str, list[Any]],
    seeds: SeedManager,
    ledger: AuthorizationLedger,
    seed_label: str,
) -> tuple[dict[str, list[Any]], list[MutationReceipt]]:
    """Remove actions linked to target case."""
    case_id = plan.target_record_ids[0]
    target_family = "action"
    if plan.realization in (RealizationState.CONCERNING, RealizationState.LEGITIMATE_UNUSUAL):
        mutation_type = MutationType.REMOVE_RECORD
    else:
        mutation_type = MutationType.ALTER_FIELD

    _verify_authorization_exists(plan, mutation_type, (case_id,), target_family, ledger)

    result = _copy_records(records)
    receipts: list[MutationReceipt] = []

    if plan.realization in (RealizationState.CONCERNING, RealizationState.LEGITIMATE_UNUSUAL):
        actions = result.get("action", [])
        before_ids = [str(a.action_id) for a in actions if str(a.case_id) == case_id]
        result["action"] = [a for a in actions if str(a.case_id) != case_id]
        receipts.append(
            _consume_authorized_receipt(
                plan=plan,
                mutation_type=mutation_type,
                target_ids=(case_id,),
                target_family=target_family,
                target_fields=("case_id",),
                before_state={"action_ids": before_ids},
                after_state={"action_ids": []},
                ledger=ledger,
            )
        )
    else:
        receipts.append(
            _consume_authorized_receipt(
                plan=plan,
                mutation_type=mutation_type,
                target_ids=(case_id,),
                target_family=target_family,
                target_fields=("action_status",),
                before_state={"status": "existing"},
                after_state={"status": "existing"},
                ledger=ledger,
            )
        )

    return result, receipts


# ---------------------------------------------------------------------------
# HIST-REP-001: Recurring false positive pattern
# ---------------------------------------------------------------------------


def _mutate_hist_rep_001(
    plan: ScenarioPlan,
    records: dict[str, list[Any]],
    seeds: SeedManager,
    ledger: AuthorizationLedger,
    seed_label: str,
) -> tuple[dict[str, list[Any]], list[MutationReceipt]]:
    """Mark multiple cases with FALSE_POSITIVE pattern."""
    mutation_type = MutationType.ALTER_FIELD
    target_family = "case"
    _verify_authorization_exists(plan, mutation_type, plan.target_record_ids, target_family, ledger)

    result = _copy_records(records)
    receipts: list[MutationReceipt] = []

    target_ids = set(plan.target_record_ids)
    before_disps: dict[str, str] = {}
    after_disps: dict[str, str] = {}

    if plan.realization in (RealizationState.CONCERNING, RealizationState.LEGITIMATE_UNUSUAL):
        new_cases = []
        for c in result.get("case", []):
            if str(c.case_id) in target_ids:
                before_disps[str(c.case_id)] = c.disposition
                after_disps[str(c.case_id)] = "FALSE_POSITIVE"
                new_cases.append(c.model_copy(update={"disposition": "FALSE_POSITIVE"}))
            else:
                new_cases.append(c)
        result["case"] = new_cases

    receipts.append(
        _consume_authorized_receipt(
            plan=plan,
            mutation_type=mutation_type,
            target_ids=plan.target_record_ids,
            target_family=target_family,
            target_fields=("disposition",),
            before_state={"case_dispositions": before_disps},
            after_state={"case_dispositions": after_disps},
            ledger=ledger,
        )
    )

    return result, receipts


# ---------------------------------------------------------------------------
# PEER-CMP-001: Peer comparison deviation
# ---------------------------------------------------------------------------


def _mutate_peer_cmp_001(
    plan: ScenarioPlan,
    records: dict[str, list[Any]],
    seeds: SeedManager,
    ledger: AuthorizationLedger,
    seed_label: str,
) -> tuple[dict[str, list[Any]], list[MutationReceipt]]:
    """Create peer-comparison conditions."""
    mutation_type = MutationType.ALTER_PROPENSITY
    target_family = "investigation"
    _verify_authorization_exists(plan, mutation_type, plan.target_record_ids, target_family, ledger)

    result = _copy_records(records)
    receipts: list[MutationReceipt] = []
    target_org = plan.target_record_ids[0]

    if plan.realization == RealizationState.CONCERNING:
        investigations = result.get("investigation", [])
        protected_ids = {
            t_id
            for entry in ledger.entries.values()
            if entry.plan_id != plan.plan_id and entry.target_family == "investigation"
            for t_id in entry.target_record_ids
        }
        org_invs = [
            inv
            for inv in investigations
            if str(inv.organization_id) == target_org
            and str(inv.investigation_id) not in protected_ids
        ]
        if not org_invs:
            org_invs = [inv for inv in investigations if str(inv.organization_id) == target_org]
        if org_invs:
            org_inv_count = len(org_invs)
            rng = seeds.get_rng(seed_label)
            remove_count = max(1, org_inv_count // 2)
            remove_indices = set(
                int(i)
                for i in rng.choice(
                    len(org_invs), size=min(remove_count, len(org_invs)), replace=False
                )
            )
            remove_ids = {str(org_invs[i].investigation_id) for i in remove_indices}
            result["investigation"] = [
                inv for inv in investigations if str(inv.investigation_id) not in remove_ids
            ]

    receipts.append(
        _consume_authorized_receipt(
            plan=plan,
            mutation_type=mutation_type,
            target_ids=plan.target_record_ids,
            target_family=target_family,
            target_fields=("organization_id",),
            before_state={"target_org": target_org},
            after_state={"target_org": target_org},
            ledger=ledger,
        )
    )

    return result, receipts


# ---------------------------------------------------------------------------
# CROSS-REC-001: Alert→Case→Resolution chain inconsistency
# ---------------------------------------------------------------------------


def _mutate_cross_rec_001(
    plan: ScenarioPlan,
    records: dict[str, list[Any]],
    seeds: SeedManager,
    ledger: AuthorizationLedger,
    seed_label: str,
) -> tuple[dict[str, list[Any]], list[MutationReceipt]]:
    """Create cross-record inconsistency in alert→case→resolution chain."""
    if plan.realization == RealizationState.CONCERNING:
        mutation_type = MutationType.REMOVE_RECORD
        target_family = "resolution"
    else:
        mutation_type = MutationType.ALTER_FIELD
        target_family = "case"

    _verify_authorization_exists(plan, mutation_type, plan.target_record_ids, target_family, ledger)

    result = _copy_records(records)
    receipts: list[MutationReceipt] = []
    case_id = plan.target_record_ids[0]
    before_state: dict[str, Any] = {"case_id": case_id}

    if plan.realization == RealizationState.CONCERNING:
        resolutions = result.get("resolution", [])
        before_ids = [str(r.resolution_id) for r in resolutions if str(r.case_id) == case_id]
        result["resolution"] = [r for r in resolutions if str(r.case_id) != case_id]
        before_state["resolution_ids"] = before_ids

    receipts.append(
        _consume_authorized_receipt(
            plan=plan,
            mutation_type=mutation_type,
            target_ids=plan.target_record_ids,
            target_family=target_family,
            target_fields=("case_id", "resolution_id"),
            before_state=before_state,
            after_state={"case_id": case_id},
            ledger=ledger,
        )
    )

    return result, receipts


# ---------------------------------------------------------------------------
# LEGIT-CTRL-001: Legitimate alert burst
# ---------------------------------------------------------------------------


def _mutate_legit_ctrl_001(
    plan: ScenarioPlan,
    records: dict[str, list[Any]],
    seeds: SeedManager,
    ledger: AuthorizationLedger,
    seed_label: str,
) -> tuple[dict[str, list[Any]], list[MutationReceipt]]:
    """No operational mutation — this scenario adds control context only."""
    mutation_type = MutationType.ADD_CONTEXT_RECORD
    target_family = "alert"
    _verify_authorization_exists(plan, mutation_type, plan.target_record_ids, target_family, ledger)

    result = _copy_records(records)
    receipts: list[MutationReceipt] = []

    receipts.append(
        _consume_authorized_receipt(
            plan=plan,
            mutation_type=mutation_type,
            target_ids=plan.target_record_ids,
            target_family=target_family,
            target_fields=("alert_id",),
            before_state={"alert_ids": list(plan.target_record_ids)},
            after_state={"control_context": str(plan.control_context_type)},
            ledger=ledger,
        )
    )

    return result, receipts


# ---------------------------------------------------------------------------
# AMBIG-001: Incomplete investigation
# ---------------------------------------------------------------------------


def _mutate_ambig_001(
    plan: ScenarioPlan,
    records: dict[str, list[Any]],
    seeds: SeedManager,
    ledger: AuthorizationLedger,
    seed_label: str,
) -> tuple[dict[str, list[Any]], list[MutationReceipt]]:
    """Mark investigation as ambiguous/insufficient evidence state."""
    mutation_type = MutationType.ALTER_STATUS
    target_family = "investigation"
    inv_id = plan.target_record_ids[0]
    _verify_authorization_exists(plan, mutation_type, (inv_id,), target_family, ledger)

    result = _copy_records(records)
    receipts: list[MutationReceipt] = []

    investigations = result.get("investigation", [])
    target_inv = next((inv for inv in investigations if str(inv.investigation_id) == inv_id), None)
    before_status = target_inv.investigation_status if target_inv else "UNKNOWN"
    before_disp = target_inv.disposition if target_inv else None

    if plan.realization == RealizationState.AMBIGUOUS and target_inv is not None:
        updated_invs = []
        for inv in investigations:
            if str(inv.investigation_id) == inv_id:
                updated_inv = inv.model_copy(
                    update={
                        "investigation_status": "IN_PROGRESS",
                        "ended_at_utc": None,
                        "conclusion_code": None,
                        "disposition": None,
                        "investigation_notes": (
                            "Investigation inconclusive: partial evidence gathered; "
                            "insufficient telemetry to determine case disposition."
                        ),
                    }
                )
                updated_invs.append(updated_inv)
            else:
                updated_invs.append(inv)
        result["investigation"] = updated_invs

    receipts.append(
        _consume_authorized_receipt(
            plan=plan,
            mutation_type=mutation_type,
            target_ids=(inv_id,),
            target_family=target_family,
            target_fields=("investigation_status", "conclusion_code"),
            before_state={
                "investigation_id": inv_id,
                "status": before_status,
                "disposition": before_disp,
            },
            after_state={
                "investigation_id": inv_id,
                "status": (
                    "IN_PROGRESS"
                    if plan.realization == RealizationState.AMBIGUOUS
                    else before_status
                ),
            },
            ledger=ledger,
        )
    )

    return result, receipts


# ---------------------------------------------------------------------------
# Mutator and Auth Planner dispatch tables
# ---------------------------------------------------------------------------

_SCENARIO_MUTATORS = {
    "EXEC-GAP-001": _mutate_exec_gap_001,
    "EXEC-GAP-002": _mutate_exec_gap_002,
    "NEG-SPACE-001": _mutate_neg_space_001,
    "NEG-SPACE-002": _mutate_neg_space_002,
    "HIST-REP-001": _mutate_hist_rep_001,
    "PEER-CMP-001": _mutate_peer_cmp_001,
    "CROSS-REC-001": _mutate_cross_rec_001,
    "LEGIT-CTRL-001": _mutate_legit_ctrl_001,
    "AMBIG-001": _mutate_ambig_001,
}

_SCENARIO_AUTH_PLANNERS = {
    "EXEC-GAP-001": _plan_auth_exec_gap_001,
    "EXEC-GAP-002": _plan_auth_exec_gap_002,
    "NEG-SPACE-001": _plan_auth_neg_space_001,
    "NEG-SPACE-002": _plan_auth_neg_space_002,
    "HIST-REP-001": _plan_auth_hist_rep_001,
    "PEER-CMP-001": _plan_auth_peer_cmp_001,
    "CROSS-REC-001": _plan_auth_cross_rec_001,
    "LEGIT-CTRL-001": _plan_auth_legit_ctrl_001,
    "AMBIG-001": _plan_auth_ambig_001,
}
