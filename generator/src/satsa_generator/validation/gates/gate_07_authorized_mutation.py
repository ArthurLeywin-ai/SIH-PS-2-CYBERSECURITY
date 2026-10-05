"""
Gate 7: Authorized Mutation Gate.

From GENERATOR_IMPLEMENTATION_PLAN §18.1:
- Scope: Expected vs observed defects and consumed authorizations.
- Failure condition: Extra/missing/mismatched defect/authorization -> Stop.
"""

from __future__ import annotations

from satsa_generator.scenarios.models import AuthorizationStatus
from satsa_generator.validation.gates.base import ValidationGate
from satsa_generator.validation.models import (
    GateReport,
    GateSeverity,
    ValidationContext,
    ValidationIssue,
)


class Gate07AuthorizedMutation(ValidationGate):
    """Gate 7: Reconciles authorizations in ledger with applied receipts."""

    @property
    def gate_index(self) -> int:
        return 7

    @property
    def gate_name(self) -> str:
        return "Authorized Mutation Gate"

    def validate(self, context: ValidationContext) -> GateReport:
        issues: list[ValidationIssue] = []
        ledger = context.ledger
        receipts = context.receipts

        if not ledger:
            return self.create_report(issues, metadata={"status": "no_ledger"})

        entries = getattr(ledger, "entries", {})
        receipt_auth_ids = {r.authorization_id for r in receipts}

        # 1. Check for unconsumed authorizations (§18.1 Gate 7)
        for auth_id, entry in entries.items():
            if (
                entry.status not in (AuthorizationStatus.APPLIED, AuthorizationStatus.VALIDATED)
                and auth_id not in receipt_auth_ids
            ):
                issues.append(
                    ValidationIssue(
                        code="MUT_UNCONSUMED_AUTHORIZATION",
                        severity=GateSeverity.BLOCKING,
                        gate_index=7,
                        gate_name=self.gate_name,
                        scope="ledger",
                        target=auth_id,
                        message=(
                            f"Authorization '{auth_id}' for '{entry.scenario_id}' "
                            "was planned but never consumed"
                        ),
                        expected="APPLIED or VALIDATED status",
                        actual=str(entry.status),
                    )
                )

        # 2. Check for unauthorized receipts (§18.1 Gate 7)
        for receipt in receipts:
            if receipt.authorization_id not in entries:
                issues.append(
                    ValidationIssue(
                        code="MUT_UNAUTHORIZED_DEFECT",
                        severity=GateSeverity.BLOCKING,
                        gate_index=7,
                        gate_name=self.gate_name,
                        scope="receipts",
                        target=receipt.authorization_id,
                        message=(
                            f"Mutation receipt '{receipt.authorization_id}' "
                            "has no matching authorization in ledger"
                        ),
                        expected="Registered authorization",
                        actual="Missing",
                    )
                )

        return self.create_report(
            issues,
            metadata={"total_authorizations": len(entries), "total_receipts": len(receipts)},
        )
