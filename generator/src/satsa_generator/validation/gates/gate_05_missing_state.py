"""
Gate 5: Missing-State Semantics Gate.

From GENERATOR_IMPLEMENTATION_PLAN §18.1:
- Scope: Value/state compatibility across the 7 missing states (DATA_SCHEMA §4):
  OBSERVED_VALUE, OBSERVED_ZERO, NOT_PROVIDED, NOT_APPLICABLE, INVALID,
  NO_SUBMITTED_EVIDENCE, UNKNOWN.
- Failure condition: Any mismap or unsupported absence -> Stop.
"""

from __future__ import annotations

from satsa_generator.validation.gates.base import ValidationGate
from satsa_generator.validation.models import (
    GateReport,
    GateSeverity,
    ValidationContext,
    ValidationIssue,
)


class Gate05MissingStateSemantics(ValidationGate):
    """Gate 5: Validates non-collapsible missing state semantics."""

    @property
    def gate_index(self) -> int:
        return 5

    @property
    def gate_name(self) -> str:
        return "Missing-State Semantics Gate"

    def validate(self, context: ValidationContext) -> GateReport:
        issues: list[ValidationIssue] = []
        records = context.records

        # 1. Submission Family presence state vocabulary
        valid_presence = {"PROVIDED", "NOT_PROVIDED", "NOT_APPLICABLE", "UNKNOWN"}
        for fam in records.get("submission_family", []):
            if fam.presence_state not in valid_presence:
                issues.append(
                    ValidationIssue(
                        code="MISSING_STATE_INVALID_PRESENCE",
                        severity=GateSeverity.BLOCKING,
                        gate_index=5,
                        gate_name=self.gate_name,
                        scope="submission_family",
                        target=str(fam.submission_family_id),
                        message=f"Invalid presence_state '{fam.presence_state}'",
                        expected=f"One of {valid_presence}",
                        actual=fam.presence_state,
                    )
                )

        # 2. Verify numeric zero vs null distinction (OBSERVED_ZERO vs NOT_PROVIDED)
        for sub_fam in records.get("submission_family", []):
            if sub_fam.presence_state == "PROVIDED" and sub_fam.declared_record_count is None:
                issues.append(
                    ValidationIssue(
                        code="MISSING_STATE_UNSUPPORTED_NULL_COUNT",
                        severity=GateSeverity.BLOCKING,
                        gate_index=5,
                        gate_name=self.gate_name,
                        scope="submission_family",
                        target=str(sub_fam.submission_family_id),
                        message="Declared count is null for PROVIDED family",
                        expected="Non-negative integer (0 is OBSERVED_ZERO, not null)",
                        actual="None",
                    )
                )

        return self.create_report(issues)
