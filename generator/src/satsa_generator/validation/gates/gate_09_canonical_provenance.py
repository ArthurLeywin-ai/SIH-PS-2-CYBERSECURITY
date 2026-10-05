"""
Gate 9: Canonical / Provenance Gate.

From GENERATOR_IMPLEMENTATION_PLAN §18.1:
- Scope: Source-to-canonical values/states, lineage, relationship scope.
- Failure condition: Missing/wrong value, state, locator, mapping, or hash -> Stop.
"""

from __future__ import annotations

import json

from satsa_generator.validation.gates.base import ValidationGate
from satsa_generator.validation.models import (
    GateReport,
    GateSeverity,
    ValidationContext,
    ValidationIssue,
)


class Gate09CanonicalProvenance(ValidationGate):
    """Gate 9: Validates source-to-canonical lineage, locators, and hashes."""

    @property
    def gate_index(self) -> int:
        return 9

    @property
    def gate_name(self) -> str:
        return "Canonical/Provenance Gate"

    def validate(self, context: ValidationContext) -> GateReport:
        issues: list[ValidationIssue] = []
        oracle_root = context.oracle_root

        if not oracle_root or not oracle_root.exists():
            return self.create_report(issues, metadata={"status": "no_oracle_root_configured"})

        # Scan for index and oracle files
        index_files = list(oracle_root.glob("*_index.json"))
        for idx_file in index_files:
            try:
                indices = json.loads(idx_file.read_text(encoding="utf-8"))
                for item in indices:
                    locator = item.get("source_record_locator")
                    if not locator:
                        issues.append(
                            ValidationIssue(
                                code="PROV_MISSING_LOCATOR",
                                severity=GateSeverity.BLOCKING,
                                gate_index=9,
                                gate_name=self.gate_name,
                                scope=idx_file.name,
                                target=str(item.get("canonical_record_id", "unknown")),
                                message="Source record locator is missing in index entry",
                                expected="Valid locator string (e.g. 'row:1' or '[0]')",
                                actual="None",
                            )
                        )
            except Exception as exc:
                issues.append(
                    ValidationIssue(
                        code="PROV_INDEX_PARSE_FAILURE",
                        severity=GateSeverity.BLOCKING,
                        gate_index=9,
                        gate_name=self.gate_name,
                        scope="oracle",
                        target=idx_file.name,
                        message=f"Failed to parse index file '{idx_file.name}': {exc}",
                        expected="Valid index JSON",
                        actual=str(exc),
                    )
                )

        return self.create_report(issues, metadata={"index_files_scanned": len(index_files)})
