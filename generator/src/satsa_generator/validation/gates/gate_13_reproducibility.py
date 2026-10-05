"""Gate 13: Reproducibility Gate.

From GENERATOR_IMPLEMENTATION_PLAN §18.1, §20 and DATASET_GENERATION_SPEC §20:
- Scope: Logical and byte rebuild; stream isolation; deterministic IDs; identical receipts.
- Failure condition: Hash/record mismatch -> Stop.
"""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

from satsa_generator.validation.gates.base import ValidationGate
from satsa_generator.validation.models import (
    GateReport,
    GateSeverity,
    ValidationContext,
    ValidationIssue,
)


class Gate13Reproducibility(ValidationGate):
    """Gate 13: Genuinely validates reproducibility through independent second build."""

    @property
    def gate_index(self) -> int:
        return 13

    @property
    def gate_name(self) -> str:
        return "Reproducibility Gate"

    def validate(self, context: ValidationContext) -> GateReport:
        issues: list[ValidationIssue] = []
        manifest = context.manifest

        # Skip recursive rebuild if this is an internal rebuild validation
        if context.extra.get("is_rebuild", False):
            return self.create_report(issues, metadata={"status": "rebuild_subtask"})

        # 1. Manifest version tuple & streams check
        if not manifest:
            issues.append(
                ValidationIssue(
                    code="REPRO_MISSING_MANIFEST",
                    severity=GateSeverity.BLOCKING,
                    gate_index=13,
                    gate_name=self.gate_name,
                    scope="manifest",
                    target="fixture_manifest.json",
                    message="Manifest missing in validation context",
                    expected="Valid FixtureManifest instance",
                    actual="None",
                )
            )
            return self.create_report(issues)

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

        # 2. Genuine Rebuild & Byte-for-Byte Comparison
        master_seed = context.extra.get("master_seed")
        config_path_raw = context.extra.get("config_path")

        if not master_seed or not config_path_raw:
            issues.append(
                ValidationIssue(
                    code="REPRO_MISSING_SEED_CONTEXT",
                    severity=GateSeverity.BLOCKING,
                    gate_index=13,
                    gate_name=self.gate_name,
                    scope="reproducibility",
                    target="master_seed",
                    message="Master seed or config path missing from validation context",
                    expected="Valid master_seed bytes and config_path",
                    actual="None",
                )
            )
            return self.create_report(issues)

        op_root = context.operational_root
        if not op_root or not op_root.exists():
            issues.append(
                ValidationIssue(
                    code="REPRO_OPERATIONAL_ROOT_MISSING",
                    severity=GateSeverity.BLOCKING,
                    gate_index=13,
                    gate_name=self.gate_name,
                    scope="operational_evidence",
                    target=str(op_root) if op_root else "None",
                    message="Operational root missing for reproducibility comparison",
                    expected="Existing directory containing operational artifacts",
                    actual="Missing",
                )
            )
            return self.create_report(issues)

        config_path = Path(config_path_raw)
        try:
            from satsa_generator.fixture.builder import _build_m5_fixture_internal

            with tempfile.TemporaryDirectory() as tmp_dir_str:
                tmp_root = Path(tmp_dir_str)
                rebuild_res = _build_m5_fixture_internal(
                    config_path,
                    master_seed,
                    output_root=tmp_root,
                    run_validation=False,
                )

                # A. Operational evidence byte equality
                rebuild_op_root = rebuild_res.operational_root
                curr_op_files = {
                    p.relative_to(op_root): p for p in op_root.rglob("*") if p.is_file()
                }
                rebuild_op_files = {
                    p.relative_to(rebuild_op_root): p
                    for p in rebuild_op_root.rglob("*")
                    if p.is_file()
                }

                if set(curr_op_files.keys()) != set(rebuild_op_files.keys()):
                    issues.append(
                        ValidationIssue(
                            code="REPRO_FILE_SET_MISMATCH",
                            severity=GateSeverity.BLOCKING,
                            gate_index=13,
                            gate_name=self.gate_name,
                            scope="operational_package",
                            target="file_inventory",
                            message="Rebuilt operational files set does not match original",
                            expected=str(sorted(str(k) for k in curr_op_files)),
                            actual=str(sorted(str(k) for k in rebuild_op_files)),
                        )
                    )

                for rel_p, curr_p in curr_op_files.items():
                    if rel_p in rebuild_op_files:
                        reb_p = rebuild_op_files[rel_p]
                        curr_bytes = curr_p.read_bytes()
                        reb_bytes = reb_p.read_bytes()
                        if curr_bytes != reb_bytes:
                            issues.append(
                                ValidationIssue(
                                    code="REPRO_BYTE_MISMATCH",
                                    severity=GateSeverity.BLOCKING,
                                    gate_index=13,
                                    gate_name=self.gate_name,
                                    scope="operational_evidence",
                                    target=str(rel_p),
                                    message=f"Byte mismatch in operational file '{rel_p}'",
                                    expected=hashlib.sha256(curr_bytes).hexdigest(),
                                    actual=hashlib.sha256(reb_bytes).hexdigest(),
                                )
                            )

                # B. Private artifacts byte equality
                priv_root = context.private_root
                rebuild_priv_root = tmp_root / "private_ground_truth"
                if priv_root and priv_root.exists() and rebuild_priv_root.exists():
                    for priv_name in (
                        "ground_truth.json",
                        "authorization_ledger.json",
                        "quality_receipts.json",
                    ):
                        f_orig = priv_root / priv_name
                        f_reb = rebuild_priv_root / priv_name
                        if f_orig.exists() and f_reb.exists():
                            orig_b = f_orig.read_bytes()
                            reb_b = f_reb.read_bytes()
                            if orig_b != reb_b:
                                issues.append(
                                    ValidationIssue(
                                        code="REPRO_PRIVATE_ARTIFACT_MISMATCH",
                                        severity=GateSeverity.BLOCKING,
                                        gate_index=13,
                                        gate_name=self.gate_name,
                                        scope="private_ground_truth",
                                        target=priv_name,
                                        message=f"Byte mismatch in private artifact '{priv_name}'",
                                        expected=hashlib.sha256(orig_b).hexdigest(),
                                        actual=hashlib.sha256(reb_b).hexdigest(),
                                    )
                                )

                # C. Tree hash equality
                if rebuild_res.tree_sha256 != context.extra.get("tree_sha256"):
                    issues.append(
                        ValidationIssue(
                            code="REPRO_TREE_HASH_MISMATCH",
                            severity=GateSeverity.BLOCKING,
                            gate_index=13,
                            gate_name=self.gate_name,
                            scope="manifest",
                            target="tree_sha256",
                            message="Rebuild tree SHA-256 differs from original build",
                            expected=str(context.extra.get("tree_sha256")),
                            actual=str(rebuild_res.tree_sha256),
                        )
                    )

        except Exception as exc:
            issues.append(
                ValidationIssue(
                    code="REPRO_REBUILD_EXECUTION_FAILURE",
                    severity=GateSeverity.BLOCKING,
                    gate_index=13,
                    gate_name=self.gate_name,
                    scope="reproducibility",
                    target="rebuild",
                    message=f"Failed to execute reproducible rebuild: {exc}",
                    expected="Clean rebuild without exceptions",
                    actual=str(exc),
                )
            )

        return self.create_report(issues, metadata={"rebuild_executed": True})
