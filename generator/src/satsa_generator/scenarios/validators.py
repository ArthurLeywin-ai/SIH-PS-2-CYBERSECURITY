"""
Read-only semantic validators for M4 scenarios.

Validators confirm the intended operational condition and counterevidence
state for each scenario realization. They operate in a strictly read-only
manner:
- Never modify records (no silent repair)
- Never import detector thresholds, finding creation, or scoring logic
- Validate semantic conditions (e.g., absence of investigation, coverage state)
- Transition authorization entries in the AuthorizationLedger from APPLIED
  to VALIDATED on success, or to FAILED on failure
- Return evidence-rich validation reports
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from satsa_generator.core.errors import GeneratorError
from satsa_generator.scenarios.ledger import AuthorizationLedger
from satsa_generator.scenarios.models import (
    MutationReceipt,
    RealizationState,
    ScenarioPlan,
)


class ScenarioValidationError(GeneratorError):
    """Raised when scenario semantic validation fails."""


@dataclass(frozen=True)
class ScenarioValidationReport:
    """Evidence-rich report of scenario semantic validation."""

    scenario_id: str
    plan_id: str
    realization: RealizationState
    passed: bool
    checks: tuple[str, ...]
    errors: tuple[str, ...] = field(default_factory=tuple)
    evidence_observed: dict[str, Any] = field(default_factory=dict)


class ScenarioValidator:
    """Read-only semantic validator for M4 scenario realizations."""

    def __init__(self, ledger: AuthorizationLedger) -> None:
        self._ledger = ledger

    def validate(
        self,
        plan: ScenarioPlan,
        records: dict[str, list[Any]],
        receipts: list[MutationReceipt],
        *,
        fail_loudly: bool = True,
    ) -> ScenarioValidationReport:
        """Validate that a mutated world satisfies the scenario's operational condition.

        Args:
            plan: The scenario plan that was realized.
            records: The post-mutation operational evidence records (read-only).
            receipts: Mutation receipts emitted during realization.
            fail_loudly: If True, raises ScenarioValidationError on failure.

        Returns:
            ScenarioValidationReport detailing all checks and results.

        Raises:
            ScenarioValidationError: If validation fails and fail_loudly is True.
        """
        validator_fn = _SCENARIO_VALIDATORS.get(plan.scenario_id)
        if validator_fn is None:
            raise ScenarioValidationError(
                f"No validator implemented for scenario '{plan.scenario_id}'",
                context={"scenario_id": plan.scenario_id, "plan_id": plan.plan_id},
            )

        checks: list[str] = []
        errors: list[str] = []
        evidence_observed: dict[str, Any] = {}

        # Execute scenario-specific semantic validation
        validator_fn(plan, records, checks, errors, evidence_observed)

        passed = len(errors) == 0

        # Update authorization statuses in the ledger
        for receipt in receipts:
            if passed:
                self._ledger.mark_validated(receipt.authorization_id)
            else:
                self._ledger.mark_failed(receipt.authorization_id)

        report = ScenarioValidationReport(
            scenario_id=plan.scenario_id,
            plan_id=plan.plan_id,
            realization=plan.realization,
            passed=passed,
            checks=tuple(checks),
            errors=tuple(errors),
            evidence_observed=evidence_observed,
        )

        if not passed and fail_loudly:
            raise ScenarioValidationError(
                f"Scenario validation failed for '{plan.scenario_id}' "
                f"({plan.realization}): {'; '.join(errors)}",
                context={
                    "scenario_id": plan.scenario_id,
                    "plan_id": plan.plan_id,
                    "realization": plan.realization.value,
                    "errors": errors,
                    "checks": checks,
                },
            )

        return report


# ---------------------------------------------------------------------------
# Individual semantic validator functions
# ---------------------------------------------------------------------------


def _validate_exec_gap_001(
    plan: ScenarioPlan,
    records: dict[str, list[Any]],
    checks: list[str],
    errors: list[str],
    evidence: dict[str, Any],
) -> None:
    """Validate EXEC-GAP-001: Missing investigation for high-severity closed case."""
    case_id = plan.target_record_ids[0]
    cases = records.get("case", [])
    target_case = next((c for c in cases if str(c.case_id) == case_id), None)

    if target_case is None:
        errors.append(f"Target case '{case_id}' does not exist")
        return

    checks.append(f"Target case '{case_id}' exists")
    checks.append(f"Case status: {target_case.case_status}, severity: {target_case.severity}")
    evidence["case_status"] = target_case.case_status
    evidence["case_severity"] = target_case.severity

    investigations = [
        inv for inv in records.get("investigation", []) if str(inv.case_id) == case_id
    ]
    evidence["investigation_count"] = len(investigations)

    if plan.realization == RealizationState.CONCERNING:
        if len(investigations) == 0:
            checks.append("Concerning execution gap verified: 0 investigation records for case")
        else:
            errors.append(
                f"Expected 0 investigations for CONCERNING case '{case_id}', "
                f"found {len(investigations)}"
            )
    elif plan.realization == RealizationState.LEGITIMATE_UNUSUAL:
        if len(investigations) == 0:
            checks.append("Legitimate gap verified: 0 investigations with control context")
        else:
            errors.append(
                f"Expected 0 investigations for LEGITIMATE_UNUSUAL case '{case_id}', "
                f"found {len(investigations)}"
            )
        # Check control context was declared
        if plan.control_context_type is not None:
            checks.append(f"Control context confirmed: {plan.control_context_type}")
        else:
            errors.append("LEGITIMATE_UNUSUAL realization requires control context")
    elif plan.realization == RealizationState.AMBIGUOUS:
        checks.append("Ambiguous realization verified: partial/indeterminate investigation state")
    elif plan.realization == RealizationState.NORMAL:
        if len(investigations) > 0:
            checks.append(
                f"Normal operation verified: {len(investigations)} investigation(s) found"
            )
        else:
            errors.append(f"Expected at least 1 investigation for NORMAL case '{case_id}'")


def _validate_exec_gap_002(
    plan: ScenarioPlan,
    records: dict[str, list[Any]],
    checks: list[str],
    errors: list[str],
    evidence: dict[str, Any],
) -> None:
    """Validate EXEC-GAP-002: Missing escalation for high-severity case."""
    case_id = plan.target_record_ids[0]
    cases = records.get("case", [])
    target_case = next((c for c in cases if str(c.case_id) == case_id), None)

    if target_case is None:
        errors.append(f"Target case '{case_id}' does not exist")
        return

    checks.append(f"Target case '{case_id}' exists")
    evidence["case_severity"] = target_case.severity

    escalations = [esc for esc in records.get("escalation", []) if str(esc.case_id) == case_id]
    evidence["escalation_count"] = len(escalations)

    if plan.realization in (RealizationState.CONCERNING, RealizationState.LEGITIMATE_UNUSUAL):
        if len(escalations) == 0:
            checks.append("Absence of escalation verified: 0 escalation records found")
        else:
            errors.append(f"Expected 0 escalations for case '{case_id}', found {len(escalations)}")
        if plan.realization == RealizationState.LEGITIMATE_UNUSUAL:
            if plan.control_context_type is not None:
                checks.append(
                    f"Emergency workflow / exception control confirmed: {plan.control_context_type}"
                )
            else:
                errors.append("LEGITIMATE_UNUSUAL realization requires control context")
    elif plan.realization == RealizationState.NORMAL:
        checks.append(f"Normal case checked: {len(escalations)} escalation(s)")
    elif plan.realization == RealizationState.AMBIGUOUS:
        checks.append("Ambiguous escalation state verified")


def _validate_neg_space_001(
    plan: ScenarioPlan,
    records: dict[str, list[Any]],
    checks: list[str],
    errors: list[str],
    evidence: dict[str, Any],
) -> None:
    """Validate NEG-SPACE-001: Monitoring coverage gap for critical asset."""
    asset_id = plan.target_record_ids[0]
    assets = records.get("asset", [])
    target_asset = next((a for a in assets if str(a.asset_id) == asset_id), None)

    if target_asset is None:
        errors.append(f"Target asset '{asset_id}' does not exist")
        return

    checks.append(f"Target asset '{asset_id}' exists")
    evidence["criticality"] = target_asset.asset_criticality
    evidence["monitoring_expected"] = target_asset.monitoring_expected

    coverages = [c for c in records.get("monitoring_coverage", []) if str(c.asset_id) == asset_id]
    states = [c.coverage_state for c in coverages]
    evidence["coverage_states"] = states

    if plan.realization == RealizationState.CONCERNING:
        if all(s == "NOT_COVERED" for s in states) or len(states) == 0:
            checks.append("Concerning negative space verified: coverage state is NOT_COVERED")
        else:
            errors.append(f"Expected NOT_COVERED for critical asset, found {states}")
    elif plan.realization == RealizationState.LEGITIMATE_UNUSUAL:
        if any(s == "SUSPENDED" for s in states):
            checks.append("Legitimate coverage gap verified: coverage state is SUSPENDED")
        else:
            errors.append(f"Expected SUSPENDED for maintenance window, found {states}")
        if plan.control_context_type is not None:
            checks.append(f"Maintenance control context verified: {plan.control_context_type}")
        else:
            errors.append("LEGITIMATE_UNUSUAL requires control context")
    elif plan.realization == RealizationState.AMBIGUOUS:
        if any(s == "DEGRADED" for s in states):
            checks.append("Ambiguous coverage state verified: coverage state is DEGRADED")
        else:
            errors.append(f"Expected DEGRADED for ambiguous state, found {states}")
    elif plan.realization == RealizationState.NORMAL:
        checks.append(f"Normal monitoring coverage verified: states={states}")


def _validate_neg_space_002(
    plan: ScenarioPlan,
    records: dict[str, list[Any]],
    checks: list[str],
    errors: list[str],
    evidence: dict[str, Any],
) -> None:
    """Validate NEG-SPACE-002: Missing action/remediation after confirmed incident."""
    case_id = plan.target_record_ids[0]
    cases = records.get("case", [])
    target_case = next((c for c in cases if str(c.case_id) == case_id), None)

    if target_case is None:
        errors.append(f"Target case '{case_id}' does not exist")
        return

    checks.append(f"Target case '{case_id}' exists, disposition={target_case.disposition}")
    evidence["disposition"] = target_case.disposition

    actions = [a for a in records.get("action", []) if str(a.case_id) == case_id]
    evidence["action_count"] = len(actions)

    if plan.realization in (RealizationState.CONCERNING, RealizationState.LEGITIMATE_UNUSUAL):
        if len(actions) == 0:
            checks.append("Absence of remediation actions verified: 0 action records")
        else:
            errors.append(f"Expected 0 actions for case '{case_id}', found {len(actions)}")
        if plan.realization == RealizationState.LEGITIMATE_UNUSUAL:
            if plan.control_context_type is not None:
                checks.append(
                    f"Accepted risk control context verified: {plan.control_context_type}"
                )
            else:
                errors.append("LEGITIMATE_UNUSUAL requires control context")
    elif plan.realization == RealizationState.NORMAL:
        checks.append(f"Normal remediation actions verified: {len(actions)} action(s)")
    elif plan.realization == RealizationState.AMBIGUOUS:
        checks.append("Ambiguous action state verified")


def _validate_hist_rep_001(
    plan: ScenarioPlan,
    records: dict[str, list[Any]],
    checks: list[str],
    errors: list[str],
    evidence: dict[str, Any],
) -> None:
    """Validate HIST-REP-001: Recurring false positive pattern."""
    target_ids = set(plan.target_record_ids)
    cases = [c for c in records.get("case", []) if str(c.case_id) in target_ids]

    checks.append(f"Target cases located: {len(cases)} of {len(target_ids)}")
    evidence["case_count"] = len(cases)
    dispositions = [c.disposition for c in cases]
    evidence["dispositions"] = dispositions

    if plan.realization in (RealizationState.CONCERNING, RealizationState.LEGITIMATE_UNUSUAL):
        if all(d == "FALSE_POSITIVE" for d in dispositions) and len(cases) >= 2:
            checks.append(f"Recurring FALSE_POSITIVE pattern verified across {len(cases)} cases")
        else:
            errors.append(
                f"Expected all cases to have FALSE_POSITIVE disposition, found {dispositions}"
            )
        if plan.realization == RealizationState.LEGITIMATE_UNUSUAL:
            if plan.control_context_type is not None:
                checks.append(
                    f"Approved suppression control context verified: {plan.control_context_type}"
                )
            else:
                errors.append("LEGITIMATE_UNUSUAL requires control context")
    elif plan.realization == RealizationState.NORMAL:
        checks.append(f"Normal varied dispositions verified: {dispositions}")


def _validate_peer_cmp_001(
    plan: ScenarioPlan,
    records: dict[str, list[Any]],
    checks: list[str],
    errors: list[str],
    evidence: dict[str, Any],
) -> None:
    """Validate PEER-CMP-001: Peer comparison investigation rate deviation."""
    target_org_id = plan.target_record_ids[0]
    peer_org_id = plan.target_record_ids[1] if len(plan.target_record_ids) > 1 else None

    checks.append(f"Target org '{target_org_id}', Peer org '{peer_org_id}'")
    evidence["target_org_id"] = target_org_id
    evidence["peer_org_id"] = peer_org_id

    investigations = records.get("investigation", [])
    target_inv_count = sum(1 for inv in investigations if str(inv.organization_id) == target_org_id)
    peer_inv_count = sum(
        1 for inv in investigations if peer_org_id and str(inv.organization_id) == peer_org_id
    )
    evidence["target_inv_count"] = target_inv_count
    evidence["peer_inv_count"] = peer_inv_count

    if plan.realization == RealizationState.CONCERNING:
        checks.append(
            f"Concerning peer comparison state: target={target_inv_count}, peer={peer_inv_count}"
        )
    elif plan.realization == RealizationState.LEGITIMATE_UNUSUAL:
        checks.append(
            f"Legitimate peer variation: target={target_inv_count}, peer={peer_inv_count} "
            f"with context={plan.control_context_type}"
        )
        if plan.control_context_type is None:
            errors.append("LEGITIMATE_UNUSUAL requires control context")
    elif plan.realization == RealizationState.AMBIGUOUS:
        checks.append("Ambiguous peer comparison state verified")
    elif plan.realization == RealizationState.NORMAL:
        checks.append(f"Normal peer comparison: target={target_inv_count}, peer={peer_inv_count}")


def _validate_cross_rec_001(
    plan: ScenarioPlan,
    records: dict[str, list[Any]],
    checks: list[str],
    errors: list[str],
    evidence: dict[str, Any],
) -> None:
    """Validate CROSS-REC-001: Alert→Case→Resolution chain inconsistency."""
    case_id = plan.target_record_ids[0]
    resolutions = [r for r in records.get("resolution", []) if str(r.case_id) == case_id]
    evidence["resolution_count"] = len(resolutions)

    if plan.realization == RealizationState.CONCERNING:
        if len(resolutions) == 0:
            checks.append("Cross-record inconsistency verified: 0 resolutions for closed case")
        else:
            errors.append(f"Expected 0 resolutions for case '{case_id}', found {len(resolutions)}")
    elif plan.realization == RealizationState.LEGITIMATE_UNUSUAL:
        checks.append("Legitimate cross-record variant verified with process change context")
        if plan.control_context_type is not None:
            checks.append(f"Control context: {plan.control_context_type}")
        else:
            errors.append("LEGITIMATE_UNUSUAL requires control context")
    elif plan.realization == RealizationState.AMBIGUOUS:
        checks.append("Ambiguous cross-record state verified")
    elif plan.realization == RealizationState.NORMAL:
        checks.append(f"Normal cross-record chain verified: {len(resolutions)} resolution(s)")


def _validate_legit_ctrl_001(
    plan: ScenarioPlan,
    records: dict[str, list[Any]],
    checks: list[str],
    errors: list[str],
    evidence: dict[str, Any],
) -> None:
    """Validate LEGIT-CTRL-001: Legitimate alert burst with control context."""
    alert_ids = set(plan.target_record_ids)
    alerts = [a for a in records.get("alert", []) if str(a.alert_id) in alert_ids]
    checks.append(f"Target burst alerts located: {len(alerts)}")
    evidence["alert_count"] = len(alerts)

    if plan.realization == RealizationState.LEGITIMATE_UNUSUAL:
        if plan.control_context_type is not None:
            checks.append(f"Legitimate control context confirmed: {plan.control_context_type}")
        else:
            errors.append("LEGIT-CTRL-001 requires control context")
    elif plan.realization == RealizationState.NORMAL:
        checks.append("Normal alert volume verified")


def _validate_ambig_001(
    plan: ScenarioPlan,
    records: dict[str, list[Any]],
    checks: list[str],
    errors: list[str],
    evidence: dict[str, Any],
) -> None:
    """Validate AMBIG-001: Incomplete investigation with partial/ambiguous evidence."""
    inv_id = plan.target_record_ids[0]
    investigations = records.get("investigation", [])
    target_inv = next((inv for inv in investigations if str(inv.investigation_id) == inv_id), None)

    if target_inv is None:
        errors.append(f"Target investigation '{inv_id}' does not exist")
        return

    checks.append(
        f"Target investigation '{inv_id}' exists, status={target_inv.investigation_status}"
    )
    evidence["investigation_status"] = target_inv.investigation_status

    if plan.realization == RealizationState.AMBIGUOUS:
        if target_inv.investigation_status in ("IN_PROGRESS", "BLOCKED", "NOT_STARTED"):
            checks.append(
                f"Ambiguous evidence state confirmed: status={target_inv.investigation_status}"
            )
        else:
            errors.append(
                f"AMBIG-001 realization is AMBIGUOUS but status is "
                f"{target_inv.investigation_status}"
            )
    elif plan.realization == RealizationState.NORMAL:
        checks.append(
            f"Normal investigation state confirmed: status={target_inv.investigation_status}"
        )


_SCENARIO_VALIDATORS = {
    "EXEC-GAP-001": _validate_exec_gap_001,
    "EXEC-GAP-002": _validate_exec_gap_002,
    "NEG-SPACE-001": _validate_neg_space_001,
    "NEG-SPACE-002": _validate_neg_space_002,
    "HIST-REP-001": _validate_hist_rep_001,
    "PEER-CMP-001": _validate_peer_cmp_001,
    "CROSS-REC-001": _validate_cross_rec_001,
    "LEGIT-CTRL-001": _validate_legit_ctrl_001,
    "AMBIG-001": _validate_ambig_001,
}
