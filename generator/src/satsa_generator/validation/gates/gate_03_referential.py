"""
Gate 3: Referential Integrity Gate.

From GENERATOR_IMPLEMENTATION_PLAN §18.1:
- Scope: Ownership, FKs, cardinality, scoped source-ID uniqueness.
- Failure condition: Any unplanned broken/mismatched relation -> Stop.
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


class Gate03ReferentialIntegrity(ValidationGate):
    """Gate 3: Validates organization ownership, foreign keys, and links."""

    @property
    def gate_index(self) -> int:
        return 3

    @property
    def gate_name(self) -> str:
        return "Referential Integrity Gate"

    def validate(self, context: ValidationContext) -> GateReport:
        issues: list[ValidationIssue] = []
        records = context.records
        ledger = context.ledger

        # Build ID sets
        org_ids = {rec.organization_id for rec in records.get("organization", [])}
        case_ids = {rec.case_id for rec in records.get("case", [])}
        alert_ids = {rec.alert_id for rec in records.get("alert", [])}

        # Check authorized broken relationships
        authorized_broken_targets: set[str] = set()
        if ledger:
            for auth in getattr(ledger, "entries", {}).values():
                if auth.mutation_type in (
                    MutationType.BROKEN_RELATIONSHIP,
                    MutationType.REMOVE_RELATIONSHIP,
                ):
                    authorized_broken_targets.update(auth.target_record_ids)

        # 1. Organization Ownership: every submission, alert, case must belong to declared org
        for family in ("submission", "alert", "case", "asset"):
            for rec in records.get(family, []):
                oid = getattr(rec, "organization_id", None)
                if oid and oid not in org_ids:
                    rec_id = str(getattr(rec, f"{family}_id", "unknown"))
                    if rec_id not in authorized_broken_targets:
                        issues.append(
                            ValidationIssue(
                                code="REF_BROKEN_ORGANIZATION_LINK",
                                severity=GateSeverity.BLOCKING,
                                gate_index=3,
                                gate_name=self.gate_name,
                                scope=family,
                                target=rec_id,
                                message=(f"{family} references undeclared organization '{oid}'"),
                                expected="Valid organization_id in records['organization']",
                                actual=str(oid),
                            )
                        )

        # 2. Case-Alert Links
        for link in records.get("case_alert_link", []):
            link_id = str(link.case_alert_link_id)
            if link_id in authorized_broken_targets:
                continue
            if link.case_id not in case_ids:
                issues.append(
                    ValidationIssue(
                        code="REF_BROKEN_CASE_LINK",
                        severity=GateSeverity.BLOCKING,
                        gate_index=3,
                        gate_name=self.gate_name,
                        scope="case_alert_link",
                        target=link_id,
                        message=f"CaseAlertLink references nonexistent case_id '{link.case_id}'",
                        expected="Valid case_id",
                        actual=str(link.case_id),
                    )
                )
            if link.alert_id not in alert_ids:
                issues.append(
                    ValidationIssue(
                        code="REF_BROKEN_ALERT_LINK",
                        severity=GateSeverity.BLOCKING,
                        gate_index=3,
                        gate_name=self.gate_name,
                        scope="case_alert_link",
                        target=link_id,
                        message=f"CaseAlertLink references nonexistent alert_id '{link.alert_id}'",
                        expected="Valid alert_id",
                        actual=str(link.alert_id),
                    )
                )

        return self.create_report(
            issues, metadata={"org_count": len(org_ids), "alert_count": len(alert_ids)}
        )
