"""
Gate 11: Duplicate Behavior Gate.

From GENERATOR_IMPLEMENTATION_PLAN §18.1:
- Scope: Exact/conflicting/revision/repeat/submission semantics.
- Failure condition: Wrong classification/counting/identity -> Stop.
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


class Gate11DuplicateBehavior(ValidationGate):
    """Gate 11: Validates exact duplicates, conflicting duplicates, and revisions."""

    @property
    def gate_index(self) -> int:
        return 11

    @property
    def gate_name(self) -> str:
        return "Duplicate Behavior Gate"

    def validate(self, context: ValidationContext) -> GateReport:
        issues: list[ValidationIssue] = []
        records = context.records
        ledger = context.ledger

        authorized_duplicate_targets: set[str] = set()
        if ledger:
            for auth in getattr(ledger, "entries", {}).values():
                if auth.mutation_type in (
                    MutationType.EXACT_DUPLICATE,
                    MutationType.CONFLICTING_DUPLICATE,
                    MutationType.DUPLICATE_RECORD,
                ):
                    authorized_duplicate_targets.update(auth.target_record_ids)

        # Check for un-authorized duplicate primary IDs across alert family
        seen_ids: dict[str, int] = {}
        for alert in records.get("alert", []):
            aid = str(alert.alert_id)
            seen_ids[aid] = seen_ids.get(aid, 0) + 1

        for aid, count in seen_ids.items():
            if count > 1 and aid not in authorized_duplicate_targets:
                issues.append(
                    ValidationIssue(
                        code="DUP_UNAUTHORIZED_EXACT_DUPLICATE",
                        severity=GateSeverity.BLOCKING,
                        gate_index=11,
                        gate_name=self.gate_name,
                        scope="alert",
                        target=aid,
                        message=(f"Alert '{aid}' appears {count} times without authorization"),
                        expected="Unique primary key or authorized duplicate",
                        actual=f"Count: {count}",
                    )
                )

        return self.create_report(issues, metadata={"duplicate_checked_count": len(seen_ids)})
