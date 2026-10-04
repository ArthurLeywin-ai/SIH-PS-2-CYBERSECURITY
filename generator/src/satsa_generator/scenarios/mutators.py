"""
Scenario mutators — narrowly scoped, authorized, deterministic mutations.

Every mutation MUST:
- affect only authorized records
- preserve unrelated fields
- preserve referential integrity (unless the scenario explicitly requires it)
- preserve deterministic IDs
- use a named deterministic RNG stream
- emit a MutationReceipt for the authorization ledger

The mutator does NOT:
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

        Args:
            scenario: The scenario definition.
            plan: The validated scenario plan.
            records: Dict mapping family name to list of fixture records.

        Returns:
            Tuple of (mutated_records, list of mutation receipts).

        Raises:
            MutationError: If the mutation fails or is unauthorized.
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


def _make_auth_and_receipt(
    plan: ScenarioPlan,
    mutation_type: MutationType,
    target_ids: tuple[str, ...],
    target_family: str,
    target_fields: tuple[str, ...],
    expected_effect: str,
    seed_label: str,
    before_state: dict[str, Any],
    after_state: dict[str, Any],
    ledger: AuthorizationLedger,
) -> MutationReceipt:
    """Create authorization entry, register it, consume it, and return receipt."""
    auth_id = f"{plan.plan_id}:{mutation_type}:{target_family}"

    entry = AuthorizationEntry(
        authorization_id=auth_id,
        scenario_id=plan.scenario_id,
        plan_id=plan.plan_id,
        realization=plan.realization,
        target_record_ids=target_ids,
        target_family=target_family,
        mutation_type=mutation_type,
        expected_semantic_effect=expected_effect,
        seed_label=seed_label,
    )
    ledger.authorize(entry)

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
    )
    ledger.consume(receipt)
    return receipt


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
    result = _copy_records(records)
    receipts: list[MutationReceipt] = []
    case_id = plan.target_record_ids[0]

    if plan.realization == RealizationState.CONCERNING:
        # Remove investigations for this case
        investigations = result.get("investigation", [])
        before_ids = [
            str(inv.investigation_id) for inv in investigations if str(inv.case_id) == case_id
        ]
        result["investigation"] = [inv for inv in investigations if str(inv.case_id) != case_id]
        receipts.append(
            _make_auth_and_receipt(
                plan=plan,
                mutation_type=MutationType.REMOVE_RECORD,
                target_ids=(case_id,),
                target_family="investigation",
                target_fields=("case_id",),
                expected_effect=(
                    "Remove all investigation records for high-severity case, "
                    "creating an execution gap where investigation is expected"
                ),
                seed_label=seed_label,
                before_state={"investigation_ids": before_ids},
                after_state={"investigation_ids": []},
                ledger=ledger,
            )
        )
    elif plan.realization == RealizationState.NORMAL:
        # No mutation — case already has investigations (normal behavior)
        receipts.append(
            _make_auth_and_receipt(
                plan=plan,
                mutation_type=MutationType.ALTER_FIELD,
                target_ids=(case_id,),
                target_family="case",
                target_fields=("case_status",),
                expected_effect="Normal case with investigation present (no-op counterexample)",
                seed_label=seed_label,
                before_state={"status": "existing"},
                after_state={"status": "existing"},
                ledger=ledger,
            )
        )
    elif plan.realization == RealizationState.LEGITIMATE_UNUSUAL:
        # Keep investigations removed but add legitimate context
        investigations = result.get("investigation", [])
        before_ids = [
            str(inv.investigation_id) for inv in investigations if str(inv.case_id) == case_id
        ]
        result["investigation"] = [inv for inv in investigations if str(inv.case_id) != case_id]
        receipts.append(
            _make_auth_and_receipt(
                plan=plan,
                mutation_type=MutationType.REMOVE_RECORD,
                target_ids=(case_id,),
                target_family="investigation",
                target_fields=("case_id",),
                expected_effect=(
                    "Remove investigations for case with legitimate automation/exception "
                    "context explaining the absence"
                ),
                seed_label=seed_label,
                before_state={"investigation_ids": before_ids},
                after_state={"investigation_ids": []},
                ledger=ledger,
            )
        )
    elif plan.realization == RealizationState.AMBIGUOUS:
        # Partially remove — leave one investigation but mark incomplete
        investigations = result.get("investigation", [])
        case_invs = [inv for inv in investigations if str(inv.case_id) == case_id]
        if len(case_invs) > 1:
            # Remove all but first
            removed_ids = [str(inv.investigation_id) for inv in case_invs[1:]]
            result["investigation"] = [
                inv for inv in investigations if str(inv.investigation_id) not in removed_ids
            ]
        receipts.append(
            _make_auth_and_receipt(
                plan=plan,
                mutation_type=MutationType.ALTER_FIELD,
                target_ids=(case_id,),
                target_family="investigation",
                target_fields=("investigation_status",),
                expected_effect=(
                    "Partial investigation evidence — insufficient to determine "
                    "whether investigation was completed"
                ),
                seed_label=seed_label,
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
    result = _copy_records(records)
    receipts: list[MutationReceipt] = []
    case_id = plan.target_record_ids[0]

    if plan.realization in (RealizationState.CONCERNING, RealizationState.LEGITIMATE_UNUSUAL):
        escalations = result.get("escalation", [])
        before_ids = [str(esc.escalation_id) for esc in escalations if str(esc.case_id) == case_id]
        result["escalation"] = [esc for esc in escalations if str(esc.case_id) != case_id]
        effect = "Remove escalation records for high-severity case"
        if plan.realization == RealizationState.LEGITIMATE_UNUSUAL:
            effect += " (with legitimate emergency workflow context)"
        receipts.append(
            _make_auth_and_receipt(
                plan=plan,
                mutation_type=MutationType.REMOVE_RECORD,
                target_ids=(case_id,),
                target_family="escalation",
                target_fields=("case_id",),
                expected_effect=effect,
                seed_label=seed_label,
                before_state={"escalation_ids": before_ids},
                after_state={"escalation_ids": []},
                ledger=ledger,
            )
        )
    elif plan.realization in (RealizationState.AMBIGUOUS, RealizationState.NORMAL):
        receipts.append(
            _make_auth_and_receipt(
                plan=plan,
                mutation_type=MutationType.ALTER_FIELD,
                target_ids=(case_id,),
                target_family="escalation",
                target_fields=("escalation_status",),
                expected_effect="Escalation present (normal/ambiguous counterexample)",
                seed_label=seed_label,
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
    result = _copy_records(records)
    receipts: list[MutationReceipt] = []
    asset_id = plan.target_record_ids[0]

    coverages = result.get("monitoring_coverage", [])
    asset_covs = [c for c in coverages if str(c.asset_id) == asset_id]

    if plan.realization == RealizationState.CONCERNING:
        # Set coverage to NOT_COVERED
        new_covs = []
        for cov in coverages:
            if str(cov.asset_id) == asset_id:
                new_cov = cov.model_copy(update={"coverage_state": "NOT_COVERED"})
                new_covs.append(new_cov)
            else:
                new_covs.append(cov)
        result["monitoring_coverage"] = new_covs
        receipts.append(
            _make_auth_and_receipt(
                plan=plan,
                mutation_type=MutationType.ALTER_STATUS,
                target_ids=(asset_id,),
                target_family="monitoring_coverage",
                target_fields=("coverage_state",),
                expected_effect="Set monitoring coverage to NOT_COVERED for critical asset",
                seed_label=seed_label,
                before_state={"coverage_states": [c.coverage_state for c in asset_covs]},
                after_state={"coverage_states": ["NOT_COVERED"] * len(asset_covs)},
                ledger=ledger,
            )
        )
    elif plan.realization == RealizationState.LEGITIMATE_UNUSUAL:
        new_covs = []
        for cov in coverages:
            if str(cov.asset_id) == asset_id:
                new_cov = cov.model_copy(update={"coverage_state": "SUSPENDED"})
                new_covs.append(new_cov)
            else:
                new_covs.append(cov)
        result["monitoring_coverage"] = new_covs
        receipts.append(
            _make_auth_and_receipt(
                plan=plan,
                mutation_type=MutationType.ALTER_STATUS,
                target_ids=(asset_id,),
                target_family="monitoring_coverage",
                target_fields=("coverage_state",),
                expected_effect=("Set monitoring to SUSPENDED with legitimate maintenance context"),
                seed_label=seed_label,
                before_state={"coverage_states": [c.coverage_state for c in asset_covs]},
                after_state={"coverage_states": ["SUSPENDED"] * len(asset_covs)},
                ledger=ledger,
            )
        )
    elif plan.realization == RealizationState.AMBIGUOUS:
        new_covs = []
        for cov in coverages:
            if str(cov.asset_id) == asset_id:
                new_cov = cov.model_copy(update={"coverage_state": "DEGRADED"})
                new_covs.append(new_cov)
            else:
                new_covs.append(cov)
        result["monitoring_coverage"] = new_covs
        receipts.append(
            _make_auth_and_receipt(
                plan=plan,
                mutation_type=MutationType.ALTER_STATUS,
                target_ids=(asset_id,),
                target_family="monitoring_coverage",
                target_fields=("coverage_state",),
                expected_effect="Set monitoring to DEGRADED — insufficient evidence for cause",
                seed_label=seed_label,
                before_state={"coverage_states": [c.coverage_state for c in asset_covs]},
                after_state={"coverage_states": ["DEGRADED"] * len(asset_covs)},
                ledger=ledger,
            )
        )
    else:  # NORMAL
        receipts.append(
            _make_auth_and_receipt(
                plan=plan,
                mutation_type=MutationType.ALTER_FIELD,
                target_ids=(asset_id,),
                target_family="monitoring_coverage",
                target_fields=("coverage_state",),
                expected_effect="Normal monitoring coverage (counterexample)",
                seed_label=seed_label,
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
    result = _copy_records(records)
    receipts: list[MutationReceipt] = []
    case_id = plan.target_record_ids[0]

    if plan.realization in (RealizationState.CONCERNING, RealizationState.LEGITIMATE_UNUSUAL):
        actions = result.get("action", [])
        before_ids = [str(a.action_id) for a in actions if str(a.case_id) == case_id]
        result["action"] = [a for a in actions if str(a.case_id) != case_id]
        effect = "Remove remediation actions for TRUE_POSITIVE case"
        if plan.realization == RealizationState.LEGITIMATE_UNUSUAL:
            effect += " (with accepted-risk exception context)"
        receipts.append(
            _make_auth_and_receipt(
                plan=plan,
                mutation_type=MutationType.REMOVE_RECORD,
                target_ids=(case_id,),
                target_family="action",
                target_fields=("case_id",),
                expected_effect=effect,
                seed_label=seed_label,
                before_state={"action_ids": before_ids},
                after_state={"action_ids": []},
                ledger=ledger,
            )
        )
    else:
        receipts.append(
            _make_auth_and_receipt(
                plan=plan,
                mutation_type=MutationType.ALTER_FIELD,
                target_ids=(case_id,),
                target_family="action",
                target_fields=("action_status",),
                expected_effect="Actions present (normal/ambiguous counterexample)",
                seed_label=seed_label,
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
        effect = (
            "Recurring FALSE_POSITIVE pattern across multiple cases"
            if plan.realization == RealizationState.CONCERNING
            else "Recurring FALSE_POSITIVE with approved suppression/tuning context"
        )
    else:
        effect = "Normal/varied disposition pattern (counterexample)"

    receipts.append(
        _make_auth_and_receipt(
            plan=plan,
            mutation_type=MutationType.ALTER_FIELD,
            target_ids=plan.target_record_ids,
            target_family="case",
            target_fields=("disposition",),
            expected_effect=effect,
            seed_label=seed_label,
            before_state={"case_dispositions": before_disps},
            after_state={"case_dispositions": after_disps, "effect": effect},
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
    result = _copy_records(records)
    receipts: list[MutationReceipt] = []
    target_org = plan.target_record_ids[0]

    if plan.realization == RealizationState.CONCERNING:
        # Remove some investigations for the target org
        investigations = result.get("investigation", [])
        org_inv_count = sum(1 for inv in investigations if str(inv.organization_id) == target_org)
        # Remove ~half to create a notable gap
        rng = seeds.get_rng(seed_label)
        remove_count = max(1, org_inv_count // 2)
        org_invs = [inv for inv in investigations if str(inv.organization_id) == target_org]
        if org_invs:
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
        effect = "Lower investigation rate vs peers (concerning deviation)"
    elif plan.realization == RealizationState.LEGITIMATE_UNUSUAL:
        effect = "Lower investigation rate with approved automation context"
    elif plan.realization == RealizationState.AMBIGUOUS:
        effect = "Investigation rate difference — insufficient context to classify"
    else:
        effect = "Normal investigation rate among peers"

    receipts.append(
        _make_auth_and_receipt(
            plan=plan,
            mutation_type=MutationType.ALTER_PROPENSITY,
            target_ids=plan.target_record_ids,
            target_family="investigation",
            target_fields=("organization_id",),
            expected_effect=effect,
            seed_label=seed_label,
            before_state={"target_org": target_org},
            after_state={"effect": effect},
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
    result = _copy_records(records)
    receipts: list[MutationReceipt] = []
    case_id = plan.target_record_ids[0]

    before_state: dict[str, Any] = {"case_id": case_id}
    if plan.realization == RealizationState.CONCERNING:
        # Remove resolution for this case
        resolutions = result.get("resolution", [])
        before_ids = [str(r.resolution_id) for r in resolutions if str(r.case_id) == case_id]
        result["resolution"] = [r for r in resolutions if str(r.case_id) != case_id]
        effect = "Resolution absent for closed case with linked alerts (cross-record gap)"
        before_state["resolution_ids"] = before_ids
    elif plan.realization == RealizationState.LEGITIMATE_UNUSUAL:
        effect = "Resolution absent but process change explains alternative closure path"
    elif plan.realization == RealizationState.AMBIGUOUS:
        effect = "Partial resolution chain — insufficient to determine completeness"
    else:
        effect = "Full resolution chain present (normal counterexample)"

    target_family = "resolution" if plan.realization == RealizationState.CONCERNING else "case"
    mutation_type = (
        MutationType.REMOVE_RECORD
        if plan.realization == RealizationState.CONCERNING
        else MutationType.ALTER_FIELD
    )

    receipts.append(
        _make_auth_and_receipt(
            plan=plan,
            mutation_type=mutation_type,
            target_ids=plan.target_record_ids,
            target_family=target_family,
            target_fields=("case_id", "resolution_id"),
            expected_effect=effect,
            seed_label=seed_label,
            before_state=before_state,
            after_state={"effect": effect},
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
    result = _copy_records(records)
    receipts: list[MutationReceipt] = []

    effect = f"Alert burst with legitimate control context (realization={plan.realization})"

    receipts.append(
        _make_auth_and_receipt(
            plan=plan,
            mutation_type=MutationType.ADD_CONTEXT_RECORD,
            target_ids=plan.target_record_ids,
            target_family="alert",
            target_fields=("alert_id",),
            expected_effect=effect,
            seed_label=seed_label,
            before_state={"alert_ids": list(plan.target_record_ids)},
            after_state={"control_context": plan.control_context_type},
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
    result = _copy_records(records)
    receipts: list[MutationReceipt] = []
    inv_id = plan.target_record_ids[0]

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

    effect = (
        f"Investigation evidence insufficient to determine outcome (realization={plan.realization})"
    )

    receipts.append(
        _make_auth_and_receipt(
            plan=plan,
            mutation_type=MutationType.ALTER_STATUS,
            target_ids=(inv_id,),
            target_family="investigation",
            target_fields=("investigation_status", "conclusion_code"),
            expected_effect=effect,
            seed_label=seed_label,
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
# Mutator dispatch table
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
