"""
Gate 14: Package / Hash Gate.

From GENERATOR_IMPLEMENTATION_PLAN §18.1:
- Scope: Domain membership, hashes, counts, binding, no cross-domain file.
- Failure condition: Mismatch or forbidden path -> Stop.
"""

from __future__ import annotations

import hashlib

from satsa_generator.validation.gates.base import ValidationGate
from satsa_generator.validation.models import (
    GateReport,
    GateSeverity,
    ValidationContext,
    ValidationIssue,
)


class Gate14PackageHash(ValidationGate):
    """Gate 14: Validates package domain membership, file integrity hashes, and counts."""

    @property
    def gate_index(self) -> int:
        return 14

    @property
    def gate_name(self) -> str:
        return "Package/Hash Gate"

    def validate(self, context: ValidationContext) -> GateReport:
        issues: list[ValidationIssue] = []
        op_root = context.operational_root
        manifest = context.manifest

        if not op_root or not op_root.exists():
            return self.create_report(issues, metadata={"status": "no_operational_root_on_disk"})

        # 1. Package membership / forbidden files check
        forbidden_files = {
            "ground_truth.json",
            "authorization_ledger.json",
            "quality_receipts.json",
        }
        for file_path in op_root.glob("*"):
            if file_path.name in forbidden_files:
                issues.append(
                    ValidationIssue(
                        code="PKG_FORBIDDEN_FILE_MEMBERSHIP",
                        severity=GateSeverity.BLOCKING,
                        gate_index=14,
                        gate_name=self.gate_name,
                        scope="package_membership",
                        target=file_path.name,
                        message=(
                            f"Forbidden private artifact '{file_path.name}' found in "
                            "operational package"
                        ),
                        expected="Operational package contains only operational evidence",
                        actual=file_path.name,
                    )
                )

        # 2. Manifest file hash & size verification
        if manifest:
            files_list = getattr(manifest, "files", [])
            for file_entry in files_list:
                rel_path = (
                    file_entry.get("path")
                    if isinstance(file_entry, dict)
                    else getattr(file_entry, "path", None)
                )
                expected_sha = (
                    file_entry.get("sha256")
                    if isinstance(file_entry, dict)
                    else getattr(file_entry, "sha256", None)
                )
                expected_size = (
                    file_entry.get("byte_size")
                    if isinstance(file_entry, dict)
                    else getattr(file_entry, "byte_size", None)
                )

                disk_path = op_root / rel_path
                if not disk_path.exists():
                    issues.append(
                        ValidationIssue(
                            code="PKG_MISSING_MANIFESTED_FILE",
                            severity=GateSeverity.BLOCKING,
                            gate_index=14,
                            gate_name=self.gate_name,
                            scope="manifest_verification",
                            target=str(rel_path),
                            message=(
                                f"Manifested file '{rel_path}' does not exist in "
                                "operational package"
                            ),
                            expected="File exists on disk",
                            actual="Missing",
                        )
                    )
                    continue

                content = disk_path.read_bytes()
                actual_sha = hashlib.sha256(content).hexdigest()
                actual_size = len(content)

                if actual_sha != expected_sha:
                    issues.append(
                        ValidationIssue(
                            code="PKG_SHA256_MISMATCH",
                            severity=GateSeverity.BLOCKING,
                            gate_index=14,
                            gate_name=self.gate_name,
                            scope="manifest_verification",
                            target=str(rel_path),
                            message=f"SHA-256 mismatch for file '{rel_path}'",
                            expected=expected_sha,
                            actual=actual_sha,
                        )
                    )

                if actual_size != expected_size:
                    issues.append(
                        ValidationIssue(
                            code="PKG_SIZE_MISMATCH",
                            severity=GateSeverity.BLOCKING,
                            gate_index=14,
                            gate_name=self.gate_name,
                            scope="manifest_verification",
                            target=str(rel_path),
                            message=f"Byte size mismatch for file '{rel_path}'",
                            expected=str(expected_size),
                            actual=str(actual_size),
                        )
                    )

        return self.create_report(
            issues, metadata={"operational_root": op_root.name if op_root else None}
        )
