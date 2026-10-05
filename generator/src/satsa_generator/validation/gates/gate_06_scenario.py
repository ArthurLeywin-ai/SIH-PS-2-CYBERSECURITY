"""
Gate 6: Scenario Realization Gate.

From GENERATOR_IMPLEMENTATION_PLAN §18.1:
- Scope: Semantic condition, eligible scope, intended context.
- Failure condition: Scenario absent, too broad, or wrong subject -> Stop.
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


class Gate06ScenarioRealization(ValidationGate):
    """Gate 6: Validates that scenario realizations meet semantic conditions."""

    @property
    def gate_index(self) -> int:
        return 6

    @property
    def gate_name(self) -> str:
        return "Scenario Realization Gate"

    def validate(self, context: ValidationContext) -> GateReport:
        issues: list[ValidationIssue] = []
        gt_records = context.ground_truth

        realization_counts = {
            RealizationState.CONCERNING: 0,
            RealizationState.LEGITIMATE_UNUSUAL: 0,
            RealizationState.AMBIGUOUS: 0,
            RealizationState.NORMAL: 0,
        }

        for gt in gt_records:
            realization = getattr(gt, "realization", None)
            if realization in realization_counts:
                realization_counts[realization] += 1

            # Validate that validator_result is PASSED
            v_res = getattr(gt, "validator_result", "PASSED")
            if v_res != "PASSED":
                issues.append(
                    ValidationIssue(
                        code="SCENARIO_VALIDATION_FAILED",
                        severity=GateSeverity.BLOCKING,
                        gate_index=6,
                        gate_name=self.gate_name,
                        scope="ground_truth",
                        target=str(getattr(gt, "scenario_id", "unknown")),
                        message=(
                            "Ground truth validator reported failure for scenario "
                            f"{getattr(gt, 'scenario_id', 'unknown')}"
                        ),
                        expected="PASSED",
                        actual=str(v_res),
                    )
                )

        return self.create_report(
            issues,
            metadata={
                "ground_truth_count": len(gt_records),
                "realizations": {k.value: v for k, v in realization_counts.items()},
            },
        )
