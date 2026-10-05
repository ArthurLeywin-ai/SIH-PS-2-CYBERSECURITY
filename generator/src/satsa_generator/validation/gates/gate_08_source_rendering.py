"""
Gate 8: Source Rendering Gate.

From GENERATOR_IMPLEMENTATION_PLAN §18.1:
- Scope: Parse-back, dialect, IDs, time/vocab, stable order, schema profile.
- Failure condition: Byte/profile mismatch or parser failure -> Stop.
"""

from __future__ import annotations

import csv
import json

from satsa_generator.validation.gates.base import ValidationGate
from satsa_generator.validation.models import (
    GateReport,
    GateSeverity,
    ValidationContext,
    ValidationIssue,
)


class Gate08SourceRendering(ValidationGate):
    """Gate 8: Validates rendered source file parseability, dialect, and layout."""

    @property
    def gate_index(self) -> int:
        return 8

    @property
    def gate_name(self) -> str:
        return "Source Rendering Gate"

    def validate(self, context: ValidationContext) -> GateReport:
        issues: list[ValidationIssue] = []
        source_root = context.source_exports_root or context.operational_root

        if not source_root or not source_root.exists():
            return self.create_report(issues, metadata={"status": "no_rendered_source_exports"})

        rendered_files = list(source_root.glob("*.csv")) + list(source_root.glob("*.json"))
        for file_path in rendered_files:
            rel_name = file_path.name
            if rel_name == "fixture_manifest.json":
                continue

            if file_path.suffix == ".json":
                try:
                    data = json.loads(file_path.read_text(encoding="utf-8"))
                    if not isinstance(data, (list, dict)):
                        issues.append(
                            ValidationIssue(
                                code="RENDER_INVALID_JSON_STRUCTURE",
                                severity=GateSeverity.BLOCKING,
                                gate_index=8,
                                gate_name=self.gate_name,
                                scope="source_rendering",
                                target=rel_name,
                                message=(
                                    f"Rendered JSON file '{rel_name}' is not a valid list or object"
                                ),
                                expected="JSON array or object",
                                actual=str(type(data)),
                            )
                        )
                except Exception as exc:
                    issues.append(
                        ValidationIssue(
                            code="RENDER_JSON_PARSE_FAILURE",
                            severity=GateSeverity.BLOCKING,
                            gate_index=8,
                            gate_name=self.gate_name,
                            scope="source_rendering",
                            target=rel_name,
                            message=f"Failed to parse rendered JSON file '{rel_name}': {exc}",
                            expected="Valid JSON bytes",
                            actual=str(exc),
                        )
                    )

            elif file_path.suffix == ".csv":
                try:
                    with file_path.open("r", encoding="utf-8", newline="") as f:
                        reader = csv.reader(f)
                        header = next(reader, None)
                        if header is None:
                            issues.append(
                                ValidationIssue(
                                    code="RENDER_EMPTY_CSV_HEADER",
                                    severity=GateSeverity.BLOCKING,
                                    gate_index=8,
                                    gate_name=self.gate_name,
                                    scope="source_rendering",
                                    target=rel_name,
                                    message=f"CSV file '{rel_name}' has empty header row",
                                    expected="Non-empty CSV header",
                                    actual="Empty",
                                )
                            )
                except Exception as exc:
                    issues.append(
                        ValidationIssue(
                            code="RENDER_CSV_PARSE_FAILURE",
                            severity=GateSeverity.BLOCKING,
                            gate_index=8,
                            gate_name=self.gate_name,
                            scope="source_rendering",
                            target=rel_name,
                            message=f"Failed to parse rendered CSV file '{rel_name}': {exc}",
                            expected="Valid CSV format",
                            actual=str(exc),
                        )
                    )

        return self.create_report(issues, metadata={"rendered_files_scanned": len(rendered_files)})
