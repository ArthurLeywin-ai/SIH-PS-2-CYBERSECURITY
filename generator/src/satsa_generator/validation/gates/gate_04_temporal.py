"""
Gate 4: Temporal Integrity Gate.

From GENERATOR_IMPLEMENTATION_PLAN §18.1:
- Scope: Period/effective/event ordering, allowed open records.
- Failure condition: Any unplanned impossible sequence -> Stop.
"""

from __future__ import annotations

from satsa_generator.scenarios.models import MutationType
from satsa_generator.validation.gates.base import ValidationGate
from satsa_generator.validation.models import (
    GateReport,
    GateSeverity,
    ValidationContext,
    ValidationIssue,
)


class Gate04TemporalIntegrity(ValidationGate):
    """Gate 4: Validates temporal sequencing, period bounds, and event order."""

    @property
    def gate_index(self) -> int:
        return 4

    @property
    def gate_name(self) -> str:
        return "Temporal Integrity Gate"

    def validate(self, context: ValidationContext) -> GateReport:
        issues: list[ValidationIssue] = []
        records = context.records
        ledger = context.ledger

        authorized_temporal_targets: set[str] = set()
        if ledger:
            for auth in getattr(ledger, "entries", {}).values():
                if auth.mutation_type in (
                    MutationType.ALTER_TIMESTAMP,
                    MutationType.TIMESTAMP_PROBLEM,
                ):
                    authorized_temporal_targets.update(auth.target_record_ids)

        # 1. Submission period bounds
        for sub in records.get("submission", []):
            if sub.reporting_period_start_at_utc >= sub.reporting_period_end_at_utc:
                issues.append(
                    ValidationIssue(
                        code="TEMP_INVALID_PERIOD_BOUNDS",
                        severity=GateSeverity.BLOCKING,
                        gate_index=4,
                        gate_name=self.gate_name,
                        scope="submission",
                        target=str(sub.submission_id),
                        message=(
                            f"Submission start time ({sub.reporting_period_start_at_utc}) "
                            f">= end time ({sub.reporting_period_end_at_utc})"
                        ),
                        expected="start_utc < end_utc",
                        actual=(
                            f"{sub.reporting_period_start_at_utc} >= "
                            f"{sub.reporting_period_end_at_utc}"
                        ),
                    )
                )

        # 2. Case open vs close temporal order
        for case in records.get("case", []):
            case_id = str(case.case_id)
            if case_id in authorized_temporal_targets:
                continue
            if case.closed_at_utc and case.closed_at_utc < case.created_at_utc:
                issues.append(
                    ValidationIssue(
                        code="TEMP_IMPOSSIBLE_CASE_CLOSE",
                        severity=GateSeverity.BLOCKING,
                        gate_index=4,
                        gate_name=self.gate_name,
                        scope="case",
                        target=case_id,
                        message=(
                            f"Case closed_at_utc ({case.closed_at_utc}) "
                            f"precedes created_at_utc ({case.created_at_utc})"
                        ),
                        expected="closed_at_utc >= created_at_utc",
                        actual=f"{case.closed_at_utc} < {case.created_at_utc}",
                    )
                )

        # 3. Exception effective bounds
        for exc in records.get("exception", []):
            exc_id = str(exc.exception_id)
            if exc_id in authorized_temporal_targets:
                continue
            if exc.effective_end_at_utc and exc.effective_end_at_utc < exc.effective_start_at_utc:
                issues.append(
                    ValidationIssue(
                        code="TEMP_INVALID_EXCEPTION_INTERVAL",
                        severity=GateSeverity.BLOCKING,
                        gate_index=4,
                        gate_name=self.gate_name,
                        scope="exception",
                        target=exc_id,
                        message="Exception effective end precedes start",
                        expected="end >= start",
                        actual=f"{exc.effective_end_at_utc} < {exc.effective_start_at_utc}",
                    )
                )

        return self.create_report(issues)
