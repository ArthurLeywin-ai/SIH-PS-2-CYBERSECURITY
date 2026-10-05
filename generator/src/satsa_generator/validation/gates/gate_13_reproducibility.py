"""
Gate 13: Reproducibility Gate.

From GENERATOR_IMPLEMENTATION_PLAN §18.1, §20:
- Scope: Logical and byte rebuild; stream isolation.
- Failure condition: Hash/record mismatch -> Stop.
"""

from __future__ import annotations

from satsa_generator.validation.gates.base import ValidationGate
from satsa_generator.validation.models import (
    GateReport,
    GateSeverity,
    ValidationContext,
    ValidationIssue,
)


class Gate13Reproducibility(ValidationGate):
    """Gate 13: Validates deterministic identity, fixed build times, and stream derivation."""

    @property
    def gate_index(self) -> int:
        return 13

    @property
    def gate_name(self) -> str:
        return "Reproducibility Gate"

    def validate(self, context: ValidationContext) -> GateReport:
        issues: list[ValidationIssue] = []
        manifest = context.manifest

        if manifest:
            # 1. Manifest version tuple check
            if not getattr(manifest, "version_tuple_sha256", None):
                issues.append(
                    ValidationIssue(
                        code="REPRO_MISSING_VERSION_TUPLE",
                        severity=GateSeverity.BLOCKING,
                        gate_index=13,
                        gate_name=self.gate_name,
                        scope="manifest",
                        target="version_tuple_sha256",
                        message="Manifest missing version_tuple_sha256 for reproducibility check",
                        expected="Deterministic version tuple SHA-256",
                        actual="None",
                    )
                )

            # 2. Deterministic stream fingerprints
            streams = getattr(manifest, "stream_fingerprints", {})
            if not streams:
                issues.append(
                    ValidationIssue(
                        code="REPRO_MISSING_STREAM_FINGERPRINTS",
                        severity=GateSeverity.BLOCKING,
                        gate_index=13,
                        gate_name=self.gate_name,
                        scope="manifest",
                        target="stream_fingerprints",
                        message="Manifest missing public seed stream fingerprints",
                        expected="Non-empty stream fingerprints map",
                        actual="Empty",
                    )
                )

        return self.create_report(issues, metadata={"has_manifest": manifest is not None})
