"""
Scenario catalog — typed registry of scenario definitions.

Each entry contains enough metadata to describe the scenario's semantics,
prerequisites, applicable realizations, and evidence families. The catalog
is deterministic and versionable. It does NOT encode detector thresholds.

Covers all seven required scenario families:
  A. Execution-gap scenarios
  B. Negative-space scenarios
  C. Historical/repetition scenarios
  D. Peer-comparison scenarios
  E. Cross-record scenarios
  F. Legitimate unusual/control scenarios
  G. Ambiguous/insufficient-evidence scenarios
"""

from __future__ import annotations

from satsa_generator.scenarios.models import (
    ControlContextType,
    RealizationState,
    ScenarioDefinition,
    ScenarioFamily,
)

CATALOG_VERSION = "1.0.0"


def _build_catalog() -> dict[str, ScenarioDefinition]:
    """Build the typed scenario catalog."""
    definitions: list[ScenarioDefinition] = [
        # ---------------------------------------------------------------
        # A. Execution-gap scenarios
        # ---------------------------------------------------------------
        ScenarioDefinition(
            scenario_id="EXEC-GAP-001",
            family=ScenarioFamily.EXECUTION_GAP,
            description=(
                "Investigation missing for a high-severity closed case: "
                "expected investigation activity is absent despite the case "
                "being resolved and closed."
            ),
            prerequisites=[
                "Organization has at least one closed HIGH/CRITICAL case",
                "Case has linked alerts",
            ],
            applicable_realizations=[
                RealizationState.CONCERNING,
                RealizationState.LEGITIMATE_UNUSUAL,
                RealizationState.AMBIGUOUS,
                RealizationState.NORMAL,
            ],
            evidence_families_touched=["case", "investigation", "alert"],
            requires_multiple_records=False,
            supports_ambiguity=True,
            legitimate_control_requirements=[
                ControlContextType.APPROVED_AUTOMATION,
                ControlContextType.APPROVED_EXCEPTION,
            ],
            expected_relationship_impact=["case→investigation"],
            inapplicable_realization_reasons={},
        ),
        ScenarioDefinition(
            scenario_id="EXEC-GAP-002",
            family=ScenarioFamily.EXECUTION_GAP,
            description=(
                "Escalation absent for a case that meets escalation criteria: "
                "the case severity and status suggest escalation was expected "
                "but no escalation record exists."
            ),
            prerequisites=[
                "Organization has at least one HIGH/CRITICAL case",
                "Case is in a status where escalation would be expected",
            ],
            applicable_realizations=[
                RealizationState.CONCERNING,
                RealizationState.LEGITIMATE_UNUSUAL,
                RealizationState.AMBIGUOUS,
                RealizationState.NORMAL,
            ],
            evidence_families_touched=["case", "escalation"],
            requires_multiple_records=False,
            supports_ambiguity=True,
            legitimate_control_requirements=[
                ControlContextType.APPROVED_EXCEPTION,
                ControlContextType.EMERGENCY_WORKFLOW,
            ],
            expected_relationship_impact=["case→escalation"],
            inapplicable_realization_reasons={},
        ),
        # ---------------------------------------------------------------
        # B. Negative-space scenarios
        # ---------------------------------------------------------------
        ScenarioDefinition(
            scenario_id="NEG-SPACE-001",
            family=ScenarioFamily.NEGATIVE_SPACE,
            description=(
                "Monitoring coverage gap for a critical asset: the asset "
                "is marked as monitoring_expected=True but coverage state "
                "is NOT_COVERED or SUSPENDED."
            ),
            prerequisites=[
                "Organization has at least one critical asset",
                "Asset has monitoring_expected=True",
            ],
            applicable_realizations=[
                RealizationState.CONCERNING,
                RealizationState.LEGITIMATE_UNUSUAL,
                RealizationState.AMBIGUOUS,
                RealizationState.NORMAL,
            ],
            evidence_families_touched=["asset", "monitoring_coverage"],
            requires_multiple_records=False,
            supports_ambiguity=True,
            legitimate_control_requirements=[
                ControlContextType.MAINTENANCE_WINDOW,
                ControlContextType.ONBOARDING_DECOMMISSIONING,
                ControlContextType.APPROVED_MONITORING_GAP,
            ],
            expected_relationship_impact=["asset→monitoring_coverage"],
            inapplicable_realization_reasons={},
        ),
        ScenarioDefinition(
            scenario_id="NEG-SPACE-002",
            family=ScenarioFamily.NEGATIVE_SPACE,
            description=(
                "Action/remediation missing after confirmed case resolution: "
                "a case was resolved as TRUE_POSITIVE or CONFIRMED_INCIDENT "
                "but no remediation action exists."
            ),
            prerequisites=[
                "Organization has at least one resolved case",
                "Case disposition is TRUE_POSITIVE or CONFIRMED_INCIDENT",
            ],
            applicable_realizations=[
                RealizationState.CONCERNING,
                RealizationState.LEGITIMATE_UNUSUAL,
                RealizationState.AMBIGUOUS,
                RealizationState.NORMAL,
            ],
            evidence_families_touched=["case", "action", "resolution"],
            requires_multiple_records=False,
            supports_ambiguity=True,
            legitimate_control_requirements=[
                ControlContextType.ACCEPTED_RISK,
                ControlContextType.APPROVED_EXCEPTION,
            ],
            expected_relationship_impact=["case→action"],
            inapplicable_realization_reasons={},
        ),
        # ---------------------------------------------------------------
        # C. Historical / repetition scenarios
        # ---------------------------------------------------------------
        ScenarioDefinition(
            scenario_id="HIST-REP-001",
            family=ScenarioFamily.HISTORICAL_REPETITION,
            description=(
                "Recurring FALSE_POSITIVE disposition pattern: multiple "
                "cases in the same organization share FALSE_POSITIVE "
                "disposition, suggesting a recurring operational weakness "
                "or untuned detection rule."
            ),
            prerequisites=[
                "Organization has at least 2 cases",
            ],
            applicable_realizations=[
                RealizationState.CONCERNING,
                RealizationState.LEGITIMATE_UNUSUAL,
                RealizationState.AMBIGUOUS,
                RealizationState.NORMAL,
            ],
            evidence_families_touched=["case", "alert", "closure"],
            requires_multiple_records=True,
            supports_ambiguity=True,
            legitimate_control_requirements=[
                ControlContextType.APPROVED_SUPPRESSION,
                ControlContextType.VALID_PROCESS_CHANGE,
            ],
            expected_relationship_impact=["alert→case→closure"],
            inapplicable_realization_reasons={},
        ),
        # ---------------------------------------------------------------
        # D. Peer-comparison scenarios
        # ---------------------------------------------------------------
        ScenarioDefinition(
            scenario_id="PEER-CMP-001",
            family=ScenarioFamily.PEER_COMPARISON,
            description=(
                "Organization has significantly lower investigation rate "
                "compared to same-cohort peers for similar case volume. "
                "The difference is not trivially identifiable through "
                "public metadata."
            ),
            prerequisites=[
                "At least 2 organizations in the same cohort",
                "Organizations have comparable case volumes",
            ],
            applicable_realizations=[
                RealizationState.CONCERNING,
                RealizationState.LEGITIMATE_UNUSUAL,
                RealizationState.AMBIGUOUS,
                RealizationState.NORMAL,
            ],
            evidence_families_touched=[
                "organization",
                "case",
                "investigation",
            ],
            requires_multiple_records=True,
            supports_ambiguity=True,
            legitimate_control_requirements=[
                ControlContextType.VALID_ORGANIZATIONAL_CONTEXT,
                ControlContextType.APPROVED_AUTOMATION,
            ],
            expected_relationship_impact=["case→investigation"],
            inapplicable_realization_reasons={},
        ),
        # ---------------------------------------------------------------
        # E. Cross-record scenarios
        # ---------------------------------------------------------------
        ScenarioDefinition(
            scenario_id="CROSS-REC-001",
            family=ScenarioFamily.CROSS_RECORD,
            description=(
                "Alert→Case→Resolution chain inconsistency: an alert "
                "is linked to a case, but the case resolution disposition "
                "contradicts the investigation conclusion or is absent "
                "despite the case being closed."
            ),
            prerequisites=[
                "Organization has at least one case with linked alerts",
                "Case has an investigation or resolution record",
            ],
            applicable_realizations=[
                RealizationState.CONCERNING,
                RealizationState.LEGITIMATE_UNUSUAL,
                RealizationState.AMBIGUOUS,
                RealizationState.NORMAL,
            ],
            evidence_families_touched=[
                "alert",
                "case",
                "case_alert_link",
                "investigation",
                "resolution",
                "closure",
            ],
            requires_multiple_records=True,
            supports_ambiguity=True,
            legitimate_control_requirements=[
                ControlContextType.VALID_PROCESS_CHANGE,
                ControlContextType.APPROVED_EXCEPTION,
            ],
            expected_relationship_impact=[
                "alert→case",
                "case→investigation",
                "case→resolution",
                "case→closure",
            ],
            inapplicable_realization_reasons={},
        ),
        # ---------------------------------------------------------------
        # F. Legitimate unusual / control scenarios
        # ---------------------------------------------------------------
        ScenarioDefinition(
            scenario_id="LEGIT-CTRL-001",
            family=ScenarioFamily.LEGITIMATE_UNUSUAL,
            description=(
                "High alert volume with legitimate operational reason: "
                "an organization experiences an alert burst but has a "
                "documented process change, maintenance window, or "
                "approved exception explaining the volume."
            ),
            prerequisites=[
                "Organization has alert records",
                "Organization has exception or process change records",
            ],
            applicable_realizations=[
                RealizationState.LEGITIMATE_UNUSUAL,
                RealizationState.AMBIGUOUS,
                RealizationState.NORMAL,
            ],
            evidence_families_touched=[
                "alert",
                "exception",
                "process_change",
            ],
            requires_multiple_records=True,
            supports_ambiguity=True,
            legitimate_control_requirements=[
                ControlContextType.LEGITIMATE_BURST,
                ControlContextType.MAINTENANCE_WINDOW,
                ControlContextType.VALID_PROCESS_CHANGE,
            ],
            expected_relationship_impact=[],
            inapplicable_realization_reasons={
                "CONCERNING": (
                    "This scenario specifically models legitimate and baseline operational "
                    "conditions; concerning defect variants belong to the execution-gap "
                    "or negative-space families."
                ),
            },
        ),
        # ---------------------------------------------------------------
        # G. Ambiguous / insufficient-evidence scenarios
        # ---------------------------------------------------------------
        ScenarioDefinition(
            scenario_id="AMBIG-001",
            family=ScenarioFamily.AMBIGUOUS_INSUFFICIENT,
            description=(
                "Incomplete investigation with partial evidence: "
                "a case has an investigation that was started but not "
                "completed, and the available evidence is insufficient "
                "to confidently determine the outcome."
            ),
            prerequisites=[
                "Organization has at least one case with investigation",
            ],
            applicable_realizations=[
                RealizationState.AMBIGUOUS,
                RealizationState.NORMAL,
            ],
            evidence_families_touched=[
                "case",
                "investigation",
                "action",
            ],
            requires_multiple_records=False,
            supports_ambiguity=True,
            legitimate_control_requirements=[],
            expected_relationship_impact=["case→investigation"],
            inapplicable_realization_reasons={
                "CONCERNING": (
                    "Ambiguous scenarios are NOT positive findings; "
                    "insufficient evidence means confident classification is impossible."
                ),
                "LEGITIMATE_UNUSUAL": (
                    "Ambiguous scenarios are NOT clean controls; "
                    "the evidence is genuinely insufficient."
                ),
            },
        ),
    ]

    return {d.scenario_id: d for d in definitions}


# Module-level singleton catalog
_CATALOG: dict[str, ScenarioDefinition] | None = None


def get_catalog() -> dict[str, ScenarioDefinition]:
    """Return the scenario catalog (lazily initialized singleton)."""
    global _CATALOG
    if _CATALOG is None:
        _CATALOG = _build_catalog()
    return dict(_CATALOG)


def get_scenario(scenario_id: str) -> ScenarioDefinition:
    """Get a specific scenario definition by ID.

    Raises:
        KeyError: If the scenario ID is not in the catalog.
    """
    catalog = get_catalog()
    if scenario_id not in catalog:
        raise KeyError(f"Unknown scenario ID: '{scenario_id}'. Available: {sorted(catalog.keys())}")
    return catalog[scenario_id]


def get_scenarios_by_family(family: ScenarioFamily) -> list[ScenarioDefinition]:
    """Get all scenario definitions for a given family."""
    return [d for d in get_catalog().values() if d.family == family]


def validate_catalog() -> list[str]:
    """Validate catalog internal consistency.

    Returns:
        List of validation error messages (empty if valid).
    """
    errors: list[str] = []
    catalog = get_catalog()

    # Check unique IDs
    ids = [d.scenario_id for d in catalog.values()]
    if len(ids) != len(set(ids)):
        errors.append("Duplicate scenario IDs in catalog")

    # Check every family is represented
    represented = {d.family for d in catalog.values()}
    for family in ScenarioFamily:
        if family not in represented:
            errors.append(f"Family '{family}' has no scenario definitions")

    # Check realization consistency
    for defn in catalog.values():
        for real in defn.applicable_realizations:
            if real.value in defn.inapplicable_realization_reasons:
                errors.append(
                    f"Scenario '{defn.scenario_id}' lists '{real}' as both "
                    f"applicable and inapplicable"
                )

    return errors
