"""
Gate 12: Leakage Scan Gate.

From GENERATOR_IMPLEMENTATION_PLAN §18.1, §19:
- Scope: Paths, headers, keys, values, notes, IDs, metadata, manifests.
- Failure condition: Unwaived high-confidence leak -> Stop.
"""

from __future__ import annotations

from satsa_generator.validation.gates.base import ValidationGate
from satsa_generator.validation.leakage import ComprehensiveLeakageScanner
from satsa_generator.validation.models import (
    GateReport,
    ValidationContext,
    ValidationIssue,
)


class Gate12LeakageScan(ValidationGate):
    """Gate 12: Comprehensive leakage scan across all operational surfaces."""

    @property
    def gate_index(self) -> int:
        return 12

    @property
    def gate_name(self) -> str:
        return "Leakage Scan Gate"

    def validate(self, context: ValidationContext) -> GateReport:
        issues: list[ValidationIssue] = []
        waivers = context.waivers

        # 1. Scan filesystem operational root if provided
        if context.operational_root and context.operational_root.exists():
            issues.extend(
                ComprehensiveLeakageScanner.scan_operational_directory(
                    context.operational_root, waivers=waivers
                )
            )

        # 2. Scan records in memory
        for family, items in context.records.items():
            for idx, item in enumerate(items[:50]):  # Sample inspection of in-memory objects
                item_dict = item.model_dump(mode="json") if hasattr(item, "model_dump") else {}
                issues.extend(
                    ComprehensiveLeakageScanner.scan_payload(
                        item_dict, path=f"{family}[{idx}]", waivers=waivers
                    )
                )

        return self.create_report(
            issues,
            metadata={
                "scanned_directory": context.operational_root.name
                if context.operational_root
                else None
            },
        )
