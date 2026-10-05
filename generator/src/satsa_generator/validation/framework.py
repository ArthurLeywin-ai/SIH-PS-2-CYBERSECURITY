"""
Validation framework orchestrator — runs all 14 validation gates.

From GENERATOR_IMPLEMENTATION_PLAN §18:
- Staged validation execution across all 14 layers.
- Full reporting with machine-readable JSON artifacts.
- Stop on any blocking issue; review soft distribution issues.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from satsa_generator.core.errors import GeneratorError
from satsa_generator.validation.gates import ALL_GATES, ValidationGate
from satsa_generator.validation.models import (
    FullValidationReport,
    GateReport,
    GateSeverity,
    GateStatus,
    ValidationContext,
)


class ValidationGateError(GeneratorError):
    """Raised when a validation gate encounters a blocking failure."""


class ValidationRunner:
    """Orchestrates staged validation gates and produces comprehensive reports."""

    def __init__(
        self,
        gates: Sequence[type[ValidationGate]] | None = None,
    ) -> None:
        gate_classes = gates if gates is not None else ALL_GATES
        self._gates: list[ValidationGate] = [g_cls() for g_cls in gate_classes]

    @property
    def gates(self) -> tuple[ValidationGate, ...]:
        """Registered validation gate instances."""
        return tuple(self._gates)

    def run_all(
        self,
        context: ValidationContext,
        *,
        stop_on_first_blocking: bool = False,
    ) -> FullValidationReport:
        """Run all registered gates in order and compile FullValidationReport."""
        reports: dict[int, GateReport] = {}
        blocking_count = 0
        high_count = 0
        warning_count = 0
        total_issues = 0

        for gate in self._gates:
            report = gate.validate(context)
            reports[gate.gate_index] = report

            for issue in report.issues:
                total_issues += 1
                if issue.severity == GateSeverity.BLOCKING:
                    blocking_count += 1
                elif issue.severity == GateSeverity.HIGH:
                    high_count += 1
                elif issue.severity == GateSeverity.WARNING:
                    warning_count += 1

            if stop_on_first_blocking and blocking_count > 0:
                break

        overall_status = GateStatus.PASSED
        all_passed = True
        if blocking_count > 0 or high_count > 0:
            overall_status = GateStatus.FAILED
            all_passed = False
        elif warning_count > 0:
            overall_status = GateStatus.REVIEW_REQUIRED

        eval_time = (
            context.manifest.created_at_utc.isoformat()
            if context.manifest and getattr(context.manifest, "created_at_utc", None)
            else "2026-10-05T00:00:00Z"
        )

        return FullValidationReport(
            overall_status=overall_status,
            all_passed=all_passed,
            gate_reports=reports,
            blocking_issue_count=blocking_count,
            high_issue_count=high_count,
            warning_issue_count=warning_count,
            total_issues=total_issues,
            evaluated_at_utc=eval_time,
        )

    def write_reports(
        self,
        report: FullValidationReport,
        output_dir: Path,
    ) -> Path:
        """Serialize validation reports to a dedicated private reports directory."""
        output_dir.mkdir(parents=True, exist_ok=True)
        reports_dir = output_dir / "validation_reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        # Write overall report
        overall_file = reports_dir / "full_validation_report.json"
        overall_data = report.model_dump(mode="json")
        overall_file.write_text(json.dumps(overall_data, indent=2), encoding="utf-8")

        # Write individual gate reports
        for gate_idx, g_report in report.gate_reports.items():
            slug = g_report.gate_name.lower().replace(" ", "_").replace("/", "_")
            gate_file = reports_dir / f"gate_{gate_idx:02d}_{slug}.json"
            gate_data = g_report.model_dump(mode="json")
            gate_file.write_text(json.dumps(gate_data, indent=2), encoding="utf-8")

        return reports_dir

    def assert_all_passed(self, report: FullValidationReport) -> None:
        """Assert all gates passed without BLOCKING/HIGH issues; raise ValidationGateError."""
        if not report.all_passed:
            failed_gates = []
            for idx, rep in report.gate_reports.items():
                if not rep.passed:
                    msgs = [
                        i.message
                        for i in rep.issues
                        if i.severity in (GateSeverity.BLOCKING, GateSeverity.HIGH)
                    ]
                    failed_gates.append(f"Gate {idx} ({rep.gate_name}): {msgs}")
            raise ValidationGateError(
                f"Validation framework failed with {report.blocking_issue_count} blocking issue(s)",
                context={"failed_gates": failed_gates},
            )
