"""
Private ground-truth writer and leakage prevention for M4 scenarios.

From GENERATOR_IMPLEMENTATION_PLAN §11.1, §25.6:
- Strictly private: ground-truth records NEVER enter the operational package.
- GroundTruthRecord captures scenario ID, version, realization, classification,
  affected record links, expected evidence, counterevidence, mutation provenance,
  authorization IDs, seeds, correlation group, and validation results.
- LeakageScanner scans operational artifacts to ensure zero leakage of private
  truth IDs, scenario codes, seeds, or mutation receipts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from satsa_generator.core.errors import GeneratorError
from satsa_generator.ids.service import IDService
from satsa_generator.scenarios.catalog import get_scenario
from satsa_generator.scenarios.models import (
    GroundTruthRecord,
    LegitimateControlDeclaration,
    MutationReceipt,
    RealizationState,
    ScenarioPlan,
    TruthRecordRole,
)
from satsa_generator.scenarios.validators import ScenarioValidationReport


class LeakageError(GeneratorError):
    """Raised when private ground-truth or scenario metadata leaks to operational output."""


class GroundTruthWriter:
    """Manages and writes private scenario ground truth."""

    def __init__(self, ids: IDService) -> None:
        self._ids = ids
        self._records: list[GroundTruthRecord] = []

    @property
    def records(self) -> list[GroundTruthRecord]:
        """Return all recorded ground-truth entries."""
        return list(self._records)

    def build_and_record(
        self,
        plan: ScenarioPlan,
        receipts: list[MutationReceipt],
        report: ScenarioValidationReport,
        control_declaration: LegitimateControlDeclaration | None = None,
    ) -> GroundTruthRecord:
        """Construct a GroundTruthRecord from plan execution artifacts and save it.

        Args:
            plan: The scenario plan.
            receipts: Mutation receipts from realization.
            report: The semantic validation report.
            control_declaration: Optional control declaration if realization is legitimate control.

        Returns:
            The recorded GroundTruthRecord.
        """
        definition = get_scenario(plan.scenario_id)

        # Classification mapping
        if plan.realization == RealizationState.CONCERNING:
            classification = "ATTENTION"
        elif plan.realization == RealizationState.LEGITIMATE_UNUSUAL:
            classification = "LEGITIMATE_UNUSUAL"
        elif plan.realization == RealizationState.AMBIGUOUS:
            classification = "AMBIGUOUS"
        else:
            classification = "NORMAL"

        # Affected records list
        affected_records: list[dict[str, Any]] = []
        for target_id in plan.target_record_ids:
            role = (
                TruthRecordRole.AFFECTED
                if plan.realization == RealizationState.CONCERNING
                else TruthRecordRole.COUNTEREVIDENCE
            )
            affected_records.append(
                {
                    "record_id": target_id,
                    "family": plan.target_family,
                    "role": role.value,
                }
            )

        if control_declaration:
            for op_id in control_declaration.operational_evidence_ids:
                affected_records.append(
                    {
                        "record_id": op_id,
                        "family": "control_evidence",
                        "role": TruthRecordRole.SUPPORTING.value,
                    }
                )

        # Mutation provenance
        mutation_provenance: list[dict[str, Any]] = []
        for receipt in receipts:
            mutation_provenance.append(
                {
                    "authorization_id": receipt.authorization_id,
                    "mutation_type": receipt.mutation_type.value,
                    "target_family": receipt.target_family,
                    "target_record_ids": list(receipt.target_record_ids),
                    "target_fields": list(receipt.target_fields),
                    "before_state": receipt.before_state,
                    "after_state": receipt.after_state,
                }
            )

        auth_ids = [r.authorization_id for r in receipts]

        truth_id = self._ids.generate(
            "ground_truth",
            plan.scenario_id,
            plan.organization_id,
            plan.period_id,
            plan.realization.value,
        )

        counterevidence_desc = ""
        if plan.realization == RealizationState.NORMAL:
            counterevidence_desc = "Normal operational evidence present; no defect"
        elif plan.realization == RealizationState.LEGITIMATE_UNUSUAL:
            counterevidence_desc = (
                f"Legitimate control context explains operational state: "
                f"{plan.control_context_description or ''}"
            )

        ambiguity_notes = ""
        abstention_state: str | None = None
        if plan.realization == RealizationState.AMBIGUOUS:
            ambiguity_notes = (
                "Operational evidence is incomplete or conflicting; "
                "confident classification is intentionally impossible."
            )
            abstention_state = "INSUFFICIENT_EVIDENCE"

        record = GroundTruthRecord(
            truth_id=truth_id,
            scenario_id=plan.scenario_id,
            scenario_version=definition.version,
            scenario_family=definition.family,
            plan_id=plan.plan_id,
            realization=plan.realization,
            classification=classification,
            organization_id=plan.organization_id,
            period_id=plan.period_id,
            affected_records=affected_records,
            expected_evidence_description=definition.description,
            counterevidence_description=counterevidence_desc,
            mutation_provenance=mutation_provenance,
            authorization_ids=auth_ids,
            seed_label=plan.seed_label,
            correlation_group_id=plan.correlation_group_id,
            ambiguity_notes=ambiguity_notes,
            abstention_state=abstention_state,
            control_context_type=plan.control_context_type,
            control_context_description=plan.control_context_description,
            evidence_families_touched=definition.evidence_families_touched,
            validator_result="PASSED" if report.passed else "FAILED",
        )

        self._records.append(record)
        return record

    def export_private_manifest(self) -> dict[str, Any]:
        """Export private ground truth manifest for evaluation packaging."""
        return {
            "record_count": len(self._records),
            "records": [r.model_dump(mode="json") for r in self._records],
        }

    def write_to_directory(self, private_dir: Path) -> Path:
        """Write private ground truth to a dedicated private directory.

        Args:
            private_dir: Path to private output directory (never in operational root).

        Returns:
            Path to the written ground_truth.json file.
        """
        private_dir.mkdir(parents=True, exist_ok=True)
        out_file = private_dir / "ground_truth.json"
        manifest = self.export_private_manifest()
        out_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return out_file


class LeakageScanner:
    """Scans operational records and serialized payloads to prevent truth leakage."""

    FORBIDDEN_KEY_SUBSTRINGS = (
        "scenario_id",
        "scenario_plan",
        "ground_truth",
        "truth_id",
        "authorization_id",
        "mutation_receipt",
        "realization_state",
    )

    FORBIDDEN_VALUE_PATTERNS = (
        "EXEC-GAP-",
        "NEG-SPACE-",
        "HIST-REP-",
        "PEER-CMP-",
        "CROSS-REC-",
        "LEGIT-CTRL-",
        "AMBIG-",
        "/scenario/",
    )

    @classmethod
    def scan_operational_dict(cls, data: Any, path: str = "root") -> list[str]:
        """Recursively scan an operational payload (dict, list, or scalar) for forbidden tokens.

        Returns:
            List of detected leakage descriptions (empty if clean).
        """
        leaks: list[str] = []

        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}"
                key_lower = str(key).lower()

                for forbidden in cls.FORBIDDEN_KEY_SUBSTRINGS:
                    if forbidden in key_lower:
                        leaks.append(f"Forbidden key '{key}' found at path '{current_path}'")

                if isinstance(value, str):
                    for pattern in cls.FORBIDDEN_VALUE_PATTERNS:
                        if pattern in value:
                            leaks.append(
                                f"Forbidden value pattern '{pattern}' "
                                f"found at '{current_path}': '{value}'"
                            )
                elif isinstance(value, (dict, list)):
                    leaks.extend(cls.scan_operational_dict(value, current_path))
        elif isinstance(data, list):
            for idx, item in enumerate(data):
                item_path = f"{path}[{idx}]"
                if isinstance(item, (dict, list)):
                    leaks.extend(cls.scan_operational_dict(item, item_path))
                elif isinstance(item, str):
                    for pattern in cls.FORBIDDEN_VALUE_PATTERNS:
                        if pattern in item:
                            leaks.append(
                                f"Forbidden value pattern '{pattern}' "
                                f"found at '{item_path}': '{item}'"
                            )
        elif isinstance(data, str):
            for pattern in cls.FORBIDDEN_VALUE_PATTERNS:
                if pattern in data:
                    leaks.append(f"Forbidden value pattern '{pattern}' found at '{path}': '{data}'")

        return leaks

    @classmethod
    def assert_no_leakage(cls, data: Any) -> None:
        """Scan operational data and raise LeakageError if any leakage is found."""
        leaks = cls.scan_operational_dict(data)
        if leaks:
            raise LeakageError(
                f"Private ground truth leakage detected in operational output "
                f"({len(leaks)} violation(s))",
                context={"violations": leaks},
            )
