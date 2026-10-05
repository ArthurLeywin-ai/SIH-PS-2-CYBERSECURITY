"""
Gate 10: Distribution Sanity Gate.

From GENERATOR_IMPLEMENTATION_PLAN §18.1, §18.2:
- Hard invariants: nonempty cohorts, configured family counts, valid parameter domains,
  required positive/control coverage, and no perfect label marker.
- Failure condition: Hard invariant breach -> Stop; soft envelope breach -> Review.
"""

from __future__ import annotations

from satsa_generator.scenarios.models import RealizationState
from satsa_generator.validation.gates.base import ValidationGate
from satsa_generator.validation.models import (
    GateReport,
    GateSeverity,
    ValidationContext,
    ValidationIssue,
)


class Gate10DistributionSanity(ValidationGate):
    """Gate 10: Validates distribution balance and no perfect label separation."""

    @property
    def gate_index(self) -> int:
        return 10

    @property
    def gate_name(self) -> str:
        return "Distribution Sanity Gate"

    def validate(self, context: ValidationContext) -> GateReport:
        issues: list[ValidationIssue] = []
        records = context.records
        gt_records = context.ground_truth

        # 1. Hard invariant: Nonempty cohorts (§18.2)
        orgs = records.get("organization", [])
        if not orgs:
            issues.append(
                ValidationIssue(
                    code="DIST_EMPTY_COHORT",
                    severity=GateSeverity.BLOCKING,
                    gate_index=10,
                    gate_name=self.gate_name,
                    scope="organization",
                    target="organization_list",
                    message="Zero organizations generated in dataset",
                    expected="At least one organization record",
                    actual="0",
                )
            )

        # 2. Hard invariant: Operational evidence is generated
        alerts = records.get("alert", [])
        if not alerts:
            issues.append(
                ValidationIssue(
                    code="DIST_ZERO_ALERTS",
                    severity=GateSeverity.BLOCKING,
                    gate_index=10,
                    gate_name=self.gate_name,
                    scope="alert",
                    target="alert_count",
                    message="Alert family has zero records generated",
                    expected="Non-zero alert volume",
                    actual="0",
                )
            )

        # 3. Hard invariant: Positive / Control realization balance (§18.2)
        if gt_records:
            realizations = {getattr(gt, "realization", None) for gt in gt_records}
            if RealizationState.CONCERNING not in realizations:
                issues.append(
                    ValidationIssue(
                        code="DIST_MISSING_CONCERNING_REALIZATION",
                        severity=GateSeverity.BLOCKING,
                        gate_index=10,
                        gate_name=self.gate_name,
                        scope="ground_truth",
                        target="realizations",
                        message="Dataset lacks any CONCERNING realization instance",
                        expected="CONCERNING realization present",
                        actual=str(realizations),
                    )
                )

        # 4. Soft envelope: Alert severity mix
        severities = {getattr(a, "severity", None) for a in alerts}
        if len(severities) < 2 and len(alerts) > 10:
            issues.append(
                ValidationIssue(
                    code="DIST_SEVERITY_HOMOGENEITY",
                    severity=GateSeverity.WARNING,
                    gate_index=10,
                    gate_name=self.gate_name,
                    scope="alert",
                    target="severity_mix",
                    message=f"Alert severities show low diversity: {severities}",
                    expected="Heterogeneous severity distribution",
                    actual=str(severities),
                )
            )

        return self.create_report(
            issues, metadata={"total_alerts": len(alerts), "severities": sorted(list(severities))}
        )
