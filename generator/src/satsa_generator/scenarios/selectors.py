"""
Scenario selectors — deterministic subject selection.

Selectors find valid targets based on semantic prerequisites, not arbitrary
row numbers. They use the existing SeedManager for deterministic RNG and
IDService for stable ID generation.

If a selector cannot find a valid target, it FAILS LOUDLY.
"""

from __future__ import annotations

from typing import Any

from satsa_generator.core.errors import GeneratorError
from satsa_generator.ids.service import IDService
from satsa_generator.scenarios.models import (
    ControlContextType,
    RealizationState,
    ScenarioDefinition,
    ScenarioPlan,
)
from satsa_generator.seeds.manager import SeedManager


class SelectionError(GeneratorError):
    """Raised when a selector cannot find a valid target."""


class ScenarioSelector:
    """Deterministic selector for scenario targets.

    Uses semantic prerequisites to find eligible subjects from the
    M2 base-world fixture records. Each selection is backed by a
    named deterministic RNG stream.
    """

    def __init__(self, seeds: SeedManager, ids: IDService) -> None:
        self._seeds = seeds
        self._ids = ids

    def select(
        self,
        scenario: ScenarioDefinition,
        realization: RealizationState,
        records: dict[str, list[Any]],
        organization_id: str,
        period_id: str,
        *,
        reserved_ids: set[str] | None = None,
        control_context_type: ControlContextType | None = None,
        control_context_description: str | None = None,
        control_process_ref_id: str | None = None,
    ) -> ScenarioPlan:
        """Select a valid target for a scenario realization.

        Args:
            scenario: The scenario definition.
            realization: The desired realization state.
            records: Dict mapping family name to list of fixture records.
            organization_id: Target organization ID.
            period_id: Target period ID.
            reserved_ids: Already-reserved record IDs to avoid overlap.
            control_context_type: For LEGITIMATE_UNUSUAL, the control type.
            control_context_description: For LEGITIMATE_UNUSUAL, control description.
            control_process_ref_id: Optional explicit M2 control/process reference ID.

        Returns:
            A ScenarioPlan with selected target records.

        Raises:
            SelectionError: If no valid target can be found.
        """
        if realization not in scenario.applicable_realizations:
            raise SelectionError(
                f"Realization '{realization}' is not applicable for "
                f"scenario '{scenario.scenario_id}'",
                context={
                    "scenario_id": scenario.scenario_id,
                    "realization": realization,
                    "applicable": [r.value for r in scenario.applicable_realizations],
                },
            )

        # Build seed label for deterministic selection
        seed_label = (
            f"development/scenario/{scenario.scenario_id}/"
            f"{organization_id}/{period_id}/{realization}/selector/v1"
        )
        rng = self._seeds.get_rng(seed_label)
        reserved = reserved_ids or set()

        # Dispatch to family-specific selector
        selector_fn = _FAMILY_SELECTORS.get(scenario.scenario_id)
        if selector_fn is None:
            raise SelectionError(
                f"No selector implemented for scenario '{scenario.scenario_id}'",
                context={"scenario_id": scenario.scenario_id},
            )

        target_ids = selector_fn(records, organization_id, rng, reserved)

        # For legitimate control or ambiguous control realization, select M2 control reference
        ctrl_ref_id_str: str | None = None
        ctrl_link_id_str: str | None = None
        if realization == RealizationState.LEGITIMATE_UNUSUAL or control_context_type is not None:
            ctrl_refs = records.get("control_process_reference", [])
            chosen_ref = select_m2_control_reference(
                scenario.scenario_id,
                scenario.evidence_families_touched[0],
                ctrl_refs,
                control_process_ref_id,
            )
            ctrl_ref_id_str = str(chosen_ref.control_process_ref_id)

            # Check for existing subject link in operational records
            links = records.get("control_process_subject_link", [])
            target_ids_set = set(target_ids) | {organization_id}
            for link in links:
                if (
                    str(link.control_process_ref_id) == ctrl_ref_id_str
                    and str(link.subject_id) in target_ids_set
                ):
                    ctrl_link_id_str = str(link.control_process_link_id)
                    break

        plan_id = self._ids.generate(
            "scenario_plan",
            scenario.scenario_id,
            organization_id,
            period_id,
            realization.value,
        )

        return ScenarioPlan(
            plan_id=plan_id,
            scenario_id=scenario.scenario_id,
            realization=realization,
            organization_id=organization_id,
            period_id=period_id,
            target_record_ids=tuple(target_ids),
            target_family=scenario.evidence_families_touched[0],
            seed_label=seed_label,
            control_context_type=control_context_type,
            control_context_description=control_context_description,
            control_process_ref_id=ctrl_ref_id_str,
            control_process_link_id=ctrl_link_id_str,
        )


def select_m2_control_reference(
    scenario_id: str,
    target_family: str,
    control_refs: list[Any],
    preferred_ref_id: str | None = None,
) -> Any:
    """Select a deterministic M2 control/process reference from operational evidence.

    Raises:
        SelectionError: If no control references exist or if a specified reference cannot be found.
    """
    if not control_refs:
        raise SelectionError("No control_process_reference records found in operational evidence")

    if preferred_ref_id:
        for ref in control_refs:
            if (
                str(ref.control_process_ref_id) == preferred_ref_id
                or ref.reference_code == preferred_ref_id
            ):
                return ref
        raise SelectionError(
            f"Specified control reference '{preferred_ref_id}' not found in operational evidence",
            context={"preferred_ref_id": preferred_ref_id},
        )

    # Deterministic matching by scenario/family preference
    code_preference: list[str] = []
    if scenario_id.startswith("EXEC-GAP"):
        code_preference = ["REF-PROC-01", "REF-CTRL-02"]
    elif scenario_id.startswith("NEG-SPACE"):
        code_preference = ["REF-CTRL-01", "REF-PROC-02"]
    elif scenario_id.startswith("HIST-REP"):
        code_preference = ["REF-PROC-01", "REF-CTRL-01"]
    elif scenario_id.startswith("PEER-CMP"):
        code_preference = ["REF-CTRL-02", "REF-PROC-01"]
    elif scenario_id.startswith("CROSS-REC"):
        code_preference = ["REF-PROC-01", "REF-CTRL-02"]
    elif scenario_id.startswith("LEGIT-CTRL"):
        code_preference = ["REF-PROC-02", "REF-CTRL-01"]

    for code in code_preference:
        for ref in control_refs:
            if ref.reference_code == code:
                return ref

    return control_refs[0]


# ---------------------------------------------------------------------------
# Family-specific selector functions
# ---------------------------------------------------------------------------


def _select_exec_gap_001(
    records: dict[str, list[Any]],
    organization_id: str,
    rng: Any,
    reserved: set[str],
) -> list[str]:
    """Select a closed high-severity case for EXEC-GAP-001."""
    cases = records.get("case", [])
    eligible = [
        c
        for c in cases
        if str(c.organization_id) == organization_id
        and c.severity in ("HIGH", "CRITICAL")
        and c.case_status in ("CLOSED", "RESOLVED")
        and str(c.case_id) not in reserved
    ]
    if not eligible:
        raise SelectionError(
            "EXEC-GAP-001: No eligible closed HIGH/CRITICAL case found",
            context={"organization_id": organization_id, "total_cases": len(cases)},
        )
    idx = int(rng.integers(0, len(eligible)))
    return [str(eligible[idx].case_id)]


def _select_exec_gap_002(
    records: dict[str, list[Any]],
    organization_id: str,
    rng: Any,
    reserved: set[str],
) -> list[str]:
    """Select a high-severity case needing escalation for EXEC-GAP-002."""
    cases = records.get("case", [])
    eligible = [
        c
        for c in cases
        if str(c.organization_id) == organization_id
        and c.severity in ("HIGH", "CRITICAL")
        and c.case_status not in ("NEW", "CANCELLED")
        and str(c.case_id) not in reserved
    ]
    if not eligible:
        raise SelectionError(
            "EXEC-GAP-002: No eligible HIGH/CRITICAL case found",
            context={"organization_id": organization_id, "total_cases": len(cases)},
        )
    idx = int(rng.integers(0, len(eligible)))
    return [str(eligible[idx].case_id)]


def _select_neg_space_001(
    records: dict[str, list[Any]],
    organization_id: str,
    rng: Any,
    reserved: set[str],
) -> list[str]:
    """Select a critical asset with expected monitoring for NEG-SPACE-001."""
    assets = records.get("asset", [])
    eligible = [
        a
        for a in assets
        if str(a.organization_id) == organization_id
        and a.asset_criticality in ("HIGH", "CRITICAL")
        and a.monitoring_expected is True
        and str(a.asset_id) not in reserved
    ]
    if not eligible:
        raise SelectionError(
            "NEG-SPACE-001: No eligible critical asset with expected monitoring",
            context={"organization_id": organization_id, "total_assets": len(assets)},
        )
    idx = int(rng.integers(0, len(eligible)))
    return [str(eligible[idx].asset_id)]


def _select_neg_space_002(
    records: dict[str, list[Any]],
    organization_id: str,
    rng: Any,
    reserved: set[str],
) -> list[str]:
    """Select a resolved TRUE_POSITIVE case for NEG-SPACE-002."""
    cases = records.get("case", [])
    eligible = [
        c
        for c in cases
        if str(c.organization_id) == organization_id
        and c.disposition in ("TRUE_POSITIVE", "CONFIRMED_INCIDENT")
        and str(c.case_id) not in reserved
    ]
    if not eligible:
        raise SelectionError(
            "NEG-SPACE-002: No eligible resolved TRUE_POSITIVE case",
            context={"organization_id": organization_id, "total_cases": len(cases)},
        )
    idx = int(rng.integers(0, len(eligible)))
    return [str(eligible[idx].case_id)]


def _select_hist_rep_001(
    records: dict[str, list[Any]],
    organization_id: str,
    rng: Any,
    reserved: set[str],
) -> list[str]:
    """Select cases for recurring false positive pattern HIST-REP-001."""
    cases = records.get("case", [])
    eligible_cases = [
        c
        for c in cases
        if str(c.organization_id) == organization_id and str(c.case_id) not in reserved
    ]
    if len(eligible_cases) < 2:
        # Fall back without reservation if needed
        eligible_cases = [c for c in cases if str(c.organization_id) == organization_id]
    if len(eligible_cases) < 2:
        raise SelectionError(
            "HIST-REP-001: Need at least 2 cases for organization",
            context={
                "organization_id": organization_id,
                "case_count": len(eligible_cases),
            },
        )
    # Select 2 cases for the pattern
    count = min(2, len(eligible_cases))
    indices = rng.choice(len(eligible_cases), size=count, replace=False)
    return [str(eligible_cases[int(i)].case_id) for i in sorted(indices)]


def _select_peer_cmp_001(
    records: dict[str, list[Any]],
    organization_id: str,
    rng: Any,
    reserved: set[str],
) -> list[str]:
    """Select organizations for peer comparison PEER-CMP-001."""
    organizations = records.get("organization", [])

    # Find organizations in the same cohort (using sector as proxy in fixture)
    target_org = None
    for org in organizations:
        if str(org.organization_id) == organization_id:
            target_org = org
            break

    if target_org is None:
        raise SelectionError(
            "PEER-CMP-001: Target organization not found",
            context={"organization_id": organization_id},
        )

    peer_orgs = [
        org
        for org in organizations
        if org.sector_code == target_org.sector_code
        and str(org.organization_id) != organization_id
        and str(org.organization_id) not in reserved
    ]

    if not peer_orgs:
        # Fallback to any other organization in the population
        peer_orgs = [
            org
            for org in organizations
            if str(org.organization_id) != organization_id
            and str(org.organization_id) not in reserved
        ]

    if not peer_orgs:
        # Fallback without reservation
        peer_orgs = [org for org in organizations if str(org.organization_id) != organization_id]

    if not peer_orgs:
        raise SelectionError(
            "PEER-CMP-001: No peer organizations in same cohort or population",
            context={
                "organization_id": organization_id,
                "sector": target_org.sector_code,
            },
        )

    idx = int(rng.integers(0, len(peer_orgs)))
    peer_id = str(peer_orgs[idx].organization_id)
    return [organization_id, peer_id]


def _select_cross_rec_001(
    records: dict[str, list[Any]],
    organization_id: str,
    rng: Any,
    reserved: set[str],
) -> list[str]:
    """Select a case with linked alerts for CROSS-REC-001."""
    cases = records.get("case", [])
    case_alert_links = records.get("case_alert_link", [])

    linked_case_ids = {str(cal.case_id) for cal in case_alert_links}
    eligible = [
        c
        for c in cases
        if str(c.organization_id) == organization_id
        and str(c.case_id) in linked_case_ids
        and c.case_status in ("CLOSED", "RESOLVED")
        and str(c.case_id) not in reserved
    ]

    if not eligible:
        # Fallback without reservation
        eligible = [
            c
            for c in cases
            if str(c.organization_id) == organization_id
            and str(c.case_id) in linked_case_ids
            and c.case_status in ("CLOSED", "RESOLVED")
        ]

    if not eligible:
        raise SelectionError(
            "CROSS-REC-001: No eligible closed case with linked alerts",
            context={"organization_id": organization_id, "total_cases": len(cases)},
        )

    idx = int(rng.integers(0, len(eligible)))
    case = eligible[idx]

    # Collect related record IDs across the chain
    case_id = str(case.case_id)
    related_alert_ids = [
        str(cal.alert_id) for cal in case_alert_links if str(cal.case_id) == case_id
    ]

    return [case_id] + related_alert_ids[:2]


def _select_legit_ctrl_001(
    records: dict[str, list[Any]],
    organization_id: str,
    rng: Any,
    reserved: set[str],
) -> list[str]:
    """Select records for legitimate control scenario LEGIT-CTRL-001."""
    alerts = records.get("alert", [])
    org_alerts = [
        a
        for a in alerts
        if str(a.organization_id) == organization_id and str(a.alert_id) not in reserved
    ]

    if not org_alerts:
        # Fallback without reservation
        org_alerts = [a for a in alerts if str(a.organization_id) == organization_id]

    if not org_alerts:
        raise SelectionError(
            "LEGIT-CTRL-001: No alerts for organization",
            context={"organization_id": organization_id},
        )

    # Select a few alerts to represent a burst
    count = min(3, len(org_alerts))
    indices = rng.choice(len(org_alerts), size=count, replace=False)
    return [str(org_alerts[int(i)].alert_id) for i in sorted(indices)]


def _select_ambig_001(
    records: dict[str, list[Any]],
    organization_id: str,
    rng: Any,
    reserved: set[str],
) -> list[str]:
    """Select an investigation for AMBIG-001."""
    investigations = records.get("investigation", [])
    eligible = [
        inv
        for inv in investigations
        if str(inv.organization_id) == organization_id
        and inv.investigation_status in ("IN_PROGRESS", "BLOCKED", "NOT_STARTED")
        and str(inv.investigation_id) not in reserved
    ]

    if not eligible:
        eligible = [
            inv
            for inv in investigations
            if str(inv.organization_id) == organization_id
            and str(inv.investigation_id) not in reserved
        ]

    if not eligible:
        eligible = [inv for inv in investigations if str(inv.organization_id) == organization_id]

    if not eligible:
        raise SelectionError(
            "AMBIG-001: No eligible investigation found",
            context={
                "organization_id": organization_id,
                "total_investigations": len(investigations),
            },
        )

    idx = int(rng.integers(0, len(eligible)))
    return [str(eligible[idx].investigation_id)]


# ---------------------------------------------------------------------------
# Selector dispatch table
# ---------------------------------------------------------------------------

_FAMILY_SELECTORS = {
    "EXEC-GAP-001": _select_exec_gap_001,
    "EXEC-GAP-002": _select_exec_gap_002,
    "NEG-SPACE-001": _select_neg_space_001,
    "NEG-SPACE-002": _select_neg_space_002,
    "HIST-REP-001": _select_hist_rep_001,
    "PEER-CMP-001": _select_peer_cmp_001,
    "CROSS-REC-001": _select_cross_rec_001,
    "LEGIT-CTRL-001": _select_legit_ctrl_001,
    "AMBIG-001": _select_ambig_001,
}
