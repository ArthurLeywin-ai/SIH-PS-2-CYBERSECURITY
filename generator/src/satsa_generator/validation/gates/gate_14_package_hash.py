"""Gate 14: Package / Hash Gate.

From GENERATOR_IMPLEMENTATION_PLAN §18.1 and DATASET_GENERATION_SPEC §20:
- Scope: Bidirectional domain membership, hashes, sizes, counts, binding, physical separation.
- Failure condition: Mismatch, missing file, unexpected unmanifested file, or forbidden path.
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
    """Gate 14: Validates package membership, integrity hashes, and separation."""

    @property
    def gate_index(self) -> int:
        return 14

    @property
    def gate_name(self) -> str:
        return "Package/Hash Gate"

    def validate(self, context: ValidationContext) -> GateReport:
        issues: list[ValidationIssue] = []
        op_root = context.operational_root
        priv_root = context.private_root
        manifest = context.manifest

        if not op_root or not op_root.exists():
            issues.append(
                ValidationIssue(
                    code="PKG_OPERATIONAL_ROOT_MISSING",
                    severity=GateSeverity.BLOCKING,
                    gate_index=14,
                    gate_name=self.gate_name,
                    scope="package_membership",
                    target=str(op_root) if op_root else "None",
                    message="Operational root directory does not exist or is not specified",
                    expected="Existing directory containing operational package",
                    actual="Missing",
                )
            )
            return self.create_report(issues)

        if not manifest:
            issues.append(
                ValidationIssue(
                    code="PKG_MANIFEST_MISSING",
                    severity=GateSeverity.BLOCKING,
                    gate_index=14,
                    gate_name=self.gate_name,
                    scope="package_membership",
                    target="fixture_manifest.json",
                    message="Fixture manifest missing in validation context",
                    expected="Valid FixtureManifest instance",
                    actual="None",
                )
            )
            return self.create_report(issues)

        # 1. Physical directory separation check
        if priv_root and priv_root.exists():
            try:
                op_root.resolve().relative_to(priv_root.resolve())
                issues.append(
                    ValidationIssue(
                        code="PKG_PHYSICAL_SEPARATION_BREACH",
                        severity=GateSeverity.BLOCKING,
                        gate_index=14,
                        gate_name=self.gate_name,
                        scope="package_separation",
                        target=str(op_root),
                        message="Operational package is nested inside private ground truth root",
                        expected="Physical separation of operational and private packages",
                        actual=str(op_root),
                    )
                )
            except ValueError:
                pass

            try:
                priv_root.resolve().relative_to(op_root.resolve())
                issues.append(
                    ValidationIssue(
                        code="PKG_PHYSICAL_SEPARATION_BREACH",
                        severity=GateSeverity.BLOCKING,
                        gate_index=14,
                        gate_name=self.gate_name,
                        scope="package_separation",
                        target=str(priv_root),
                        message="Private ground truth is nested inside operational package root",
                        expected="Physical separation of operational and private packages",
                        actual=str(priv_root),
                    )
                )
            except ValueError:
                pass

        # 2. Forbidden private files check
        forbidden_file_names = {
            "ground_truth.json",
            "authorization_ledger.json",
            "quality_receipts.json",
        }
        for file_path in op_root.rglob("*"):
            if file_path.is_file() and (
                file_path.name in forbidden_file_names or file_path.name.endswith("_oracle.json")
            ):
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

        # 3. Direction A: Every manifested file exists with correct hash and byte size
        manifested_paths: set[str] = set()
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

            if not rel_path:
                continue

            manifested_paths.add(str(rel_path))
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
                            f"Manifested file '{rel_path}' does not exist in operational package"
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
                        code="PKG_HASH_MISMATCH",
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

        # 4. Direction B: Every actual file on disk must be in manifest
        actual_files_on_disk = [p for p in op_root.rglob("*") if p.is_file()]
        for actual_file in actual_files_on_disk:
            rel_disk_path = actual_file.relative_to(op_root).as_posix()
            if rel_disk_path == "fixture_manifest.json":
                continue

            if rel_disk_path not in manifested_paths:
                issues.append(
                    ValidationIssue(
                        code="PKG_UNEXPECTED_UNMANIFESTED_FILE",
                        severity=GateSeverity.BLOCKING,
                        gate_index=14,
                        gate_name=self.gate_name,
                        scope="package_membership",
                        target=rel_disk_path,
                        message=(
                            f"Unexpected unmanifested file '{rel_disk_path}' in operational package"
                        ),
                        expected="File is represented in fixture manifest",
                        actual="Unmanifested",
                    )
                )

        return self.create_report(
            issues,
            metadata={
                "operational_files_count": len(actual_files_on_disk),
                "manifested_files_count": len(manifested_paths),
            },
        )
