"""
Gate 2: Schema / Base Gate.

From GENERATOR_IMPLEMENTATION_PLAN §18.1:
- Scope: Required types/vocab/limits on unmutated records across all 18 families.
- Failure condition: Any unplanned invalid record -> Stop.
"""

from __future__ import annotations

from satsa_generator.fixture.models import FixtureRecord
from satsa_generator.validation.gates.base import ValidationGate
from satsa_generator.validation.models import (
    GateReport,
    GateSeverity,
    ValidationContext,
    ValidationIssue,
)

_EXPECTED_18_FAMILIES = (
    "organization",
    "submission",
    "submission_manifest",
    "submission_family",
    "control_process_reference",
    "control_process_subject_link",
    "asset",
    "monitoring_coverage",
    "alert",
    "case",
    "case_alert_link",
    "investigation",
    "escalation",
    "action",
    "resolution",
    "closure",
    "exception",
    "process_change",
)


class Gate02SchemaBase(ValidationGate):
    """Gate 2: Validates operational record schemas, types, and required families."""

    @property
    def gate_index(self) -> int:
        return 2

    @property
    def gate_name(self) -> str:
        return "Schema/Base Gate"

    def validate(self, context: ValidationContext) -> GateReport:
        issues: list[ValidationIssue] = []
        records = context.records

        # 1. 18-Family coverage check
        for family in _EXPECTED_18_FAMILIES:
            if family not in records:
                issues.append(
                    ValidationIssue(
                        code="SCHEMA_MISSING_FAMILY",
                        severity=GateSeverity.BLOCKING,
                        gate_index=2,
                        gate_name=self.gate_name,
                        scope="records",
                        target=family,
                        message=(
                            f"Mandatory evidence family '{family}' is missing from records dict"
                        ),
                        expected="All 18 evidence families present",
                        actual="Missing",
                    )
                )

        # 2. Per-record validation
        for family, items in records.items():
            for idx, item in enumerate(items):
                # Verify is a valid FixtureRecord instance or Pydantic model
                if not isinstance(item, FixtureRecord):
                    issues.append(
                        ValidationIssue(
                            code="SCHEMA_INVALID_RECORD_TYPE",
                            severity=GateSeverity.BLOCKING,
                            gate_index=2,
                            gate_name=self.gate_name,
                            scope=f"{family}[{idx}]",
                            target=str(type(item)),
                            message=(
                                f"Record {idx} in family '{family}' does not inherit from "
                                "FixtureRecord"
                            ),
                            expected="FixtureRecord subclass",
                            actual=str(type(item)),
                        )
                    )
                    continue

                # Vocabulary check for Alert severity
                if family == "alert":
                    valid_severities = {
                        "CRITICAL",
                        "HIGH",
                        "MEDIUM",
                        "LOW",
                        "INFORMATIONAL",
                        "UNKNOWN",
                    }
                    sev = getattr(item, "severity", None)
                    if sev is not None and sev not in valid_severities:
                        issues.append(
                            ValidationIssue(
                                code="SCHEMA_INVALID_VOCABULARY",
                                severity=GateSeverity.BLOCKING,
                                gate_index=2,
                                gate_name=self.gate_name,
                                scope=f"alert[{idx}]",
                                target=str(item.alert_id),
                                message=f"Invalid alert severity vocabulary '{sev}'",
                                expected=f"One of {valid_severities}",
                                actual=str(sev),
                            )
                        )

        counts = {f: len(records.get(f, [])) for f in _EXPECTED_18_FAMILIES}
        return self.create_report(issues, metadata={"record_counts": counts})
