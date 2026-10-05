"""
Base abstract class for the 14 validation gates.

From GENERATOR_IMPLEMENTATION_PLAN §18.3:
- Pure/read-only validators.
- Returns structured issues with code, severity, scope, target, message, expected, actual.
- Cannot mutate generated artifacts or downgrade issues automatically.
"""

from __future__ import annotations

import abc

from satsa_generator.validation.models import (
    GateReport,
    GateSeverity,
    GateStatus,
    ValidationContext,
    ValidationIssue,
)


class ValidationGate(abc.ABC):
    """Abstract base class for all 14 generator validation gates."""

    @property
    @abc.abstractmethod
    def gate_index(self) -> int:
        """1-indexed gate number (1 to 14)."""

    @property
    @abc.abstractmethod
    def gate_name(self) -> str:
        """Human-readable gate title."""

    @abc.abstractmethod
    def validate(self, context: ValidationContext) -> GateReport:
        """Perform read-only validation and return a GateReport."""

    def create_report(
        self,
        issues: list[ValidationIssue],
        metadata: dict[str, any] | None = None,
        evaluated_at_utc: str = "2026-10-05T00:00:00Z",
    ) -> GateReport:
        """Create a GateReport from a list of detected issues."""
        has_blocking = any(i.severity == GateSeverity.BLOCKING for i in issues)
        has_high = any(i.severity == GateSeverity.HIGH for i in issues)
        has_warning = any(i.severity == GateSeverity.WARNING for i in issues)

        if has_blocking or has_high:
            status = GateStatus.FAILED
            passed = False
        elif has_warning:
            status = GateStatus.REVIEW_REQUIRED
            passed = True  # warnings allow soft review unless strict mode fails
        else:
            status = GateStatus.PASSED
            passed = True

        return GateReport(
            gate_index=self.gate_index,
            gate_name=self.gate_name,
            status=status,
            passed=passed,
            issues=tuple(issues),
            metadata=metadata or {},
            evaluated_at_utc=evaluated_at_utc,
        )
