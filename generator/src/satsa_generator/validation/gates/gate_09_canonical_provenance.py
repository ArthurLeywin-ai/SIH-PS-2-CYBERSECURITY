"""Gate 9: Canonical / Provenance Gate.

From GENERATOR_IMPLEMENTATION_PLAN §18.1:
- Scope: Source-to-canonical values/states, lineage, relationship scope.
- Failure condition: Missing/wrong value, state, locator, mapping, or hash -> Stop.
"""

from __future__ import annotations

import contextlib
import csv
import json
from pathlib import Path
from typing import Any

from satsa_generator.validation.gates.base import ValidationGate
from satsa_generator.validation.models import (
    GateReport,
    GateSeverity,
    ValidationContext,
    ValidationIssue,
)


class Gate09CanonicalProvenance(ValidationGate):
    """Gate 9: Validates source-to-canonical lineage, locators, raw values, and relationships."""

    @property
    def gate_index(self) -> int:
        return 9

    @property
    def gate_name(self) -> str:
        return "Canonical/Provenance Gate"

    def validate(self, context: ValidationContext) -> GateReport:
        issues: list[ValidationIssue] = []
        oracle_root = context.oracle_root
        source_root = context.source_exports_root

        # Missing required roots is a blocking failure
        if not oracle_root or not oracle_root.exists():
            issues.append(
                ValidationIssue(
                    code="PROV_ORACLE_ROOT_MISSING",
                    severity=GateSeverity.BLOCKING,
                    gate_index=9,
                    gate_name=self.gate_name,
                    scope="canonical_provenance",
                    target=str(oracle_root) if oracle_root else "None",
                    message="Oracle root directory does not exist or is not specified",
                    expected="Existing directory containing canonical reference artifacts",
                    actual="Missing",
                )
            )
            return self.create_report(issues)

        if not source_root or not source_root.exists():
            issues.append(
                ValidationIssue(
                    code="PROV_SOURCE_ROOT_MISSING",
                    severity=GateSeverity.BLOCKING,
                    gate_index=9,
                    gate_name=self.gate_name,
                    scope="canonical_provenance",
                    target=str(source_root) if source_root else "None",
                    message="Source exports directory does not exist or is not specified",
                    expected="Existing directory containing rendered source exports",
                    actual="Missing",
                )
            )
            return self.create_report(issues)

        # Index and provenance files
        index_files = sorted(list(oracle_root.glob("*_index.json")))
        prov_files = sorted(list(oracle_root.glob("*_provenance.json")))

        if not index_files:
            issues.append(
                ValidationIssue(
                    code="PROV_INDEX_FILES_MISSING",
                    severity=GateSeverity.BLOCKING,
                    gate_index=9,
                    gate_name=self.gate_name,
                    scope="oracle",
                    target="*_index.json",
                    message="No index files found in oracle root",
                    expected="At least one *_index.json file",
                    actual="0 files",
                )
            )

        if not prov_files:
            issues.append(
                ValidationIssue(
                    code="PROV_PROVENANCE_FILES_MISSING",
                    severity=GateSeverity.BLOCKING,
                    gate_index=9,
                    gate_name=self.gate_name,
                    scope="oracle",
                    target="*_provenance.json",
                    message="No provenance files found in oracle root",
                    expected="At least one *_provenance.json file",
                    actual="0 files",
                )
            )

        if issues:
            return self.create_report(issues)

        # Build authorized mutation lookups
        authorized_targets: set[str] = set()
        authorized_types: set[str] = set()
        if context.ledger:
            for entry in context.ledger.entries.values():
                for tid in getattr(entry, "target_record_ids", ()):
                    authorized_targets.add(str(tid))
                m_type = str(getattr(entry, "mutation_type", ""))
                if "." in m_type:
                    m_type = m_type.split(".")[-1]
                authorized_types.add(m_type)

        # Cache parsed source files: path -> list[dict]
        source_cache: dict[Path, list[dict[str, Any]]] = {}

        def _get_source_records(file_p: Path) -> list[dict[str, Any]] | None:
            if file_p in source_cache:
                return source_cache[file_p]
            if not file_p.exists():
                return None
            try:
                records: list[dict[str, Any]] = []
                ext = file_p.suffix.lower()
                if ext == ".csv":
                    with file_p.open("r", encoding="utf-8", newline="") as f:
                        records = list(csv.DictReader(f))
                elif ext == ".json":
                    data = json.loads(file_p.read_text(encoding="utf-8"))
                    records = data if isinstance(data, list) else [data]
                elif ext == ".jsonl":
                    lines = file_p.read_text(encoding="utf-8").strip().split("\n")
                    records = [json.loads(line) for line in lines if line.strip()]
                source_cache[file_p] = records
                return records
            except Exception:
                return None

        # 1. Validate index entries
        for idx_file in index_files:
            try:
                indices = json.loads(idx_file.read_text(encoding="utf-8"))
                for item in indices:
                    locator = item.get("source_record_locator")
                    can_id = item.get("canonical_record_id")
                    src_path_str = item.get("source_file_path", "")
                    src_file = source_root / Path(src_path_str).name

                    if not locator:
                        issues.append(
                            ValidationIssue(
                                code="PROV_MISSING_LOCATOR",
                                severity=GateSeverity.BLOCKING,
                                gate_index=9,
                                gate_name=self.gate_name,
                                scope=idx_file.name,
                                target=str(can_id or "unknown"),
                                message="Source record locator is missing in index entry",
                                expected="Valid locator string (e.g. 'row:1' or '[0]')",
                                actual="None",
                            )
                        )
                    if not can_id:
                        issues.append(
                            ValidationIssue(
                                code="PROV_MISSING_CANONICAL_ID",
                                severity=GateSeverity.BLOCKING,
                                gate_index=9,
                                gate_name=self.gate_name,
                                scope=idx_file.name,
                                target=str(locator or "unknown"),
                                message="Canonical record ID is missing in index entry",
                                expected="Valid UUID",
                                actual="None",
                            )
                        )

                    # Verify source file exists
                    if not src_file.exists():
                        is_auth_missing_fam = "MISSING_FAMILY" in authorized_types
                        if not is_auth_missing_fam:
                            issues.append(
                                ValidationIssue(
                                    code="PROV_SOURCE_FILE_NOT_FOUND",
                                    severity=GateSeverity.BLOCKING,
                                    gate_index=9,
                                    gate_name=self.gate_name,
                                    scope="source_locator",
                                    target=src_path_str,
                                    message=f"Indexed source file '{src_path_str}' not on disk",
                                    expected="Existing source file",
                                    actual="Missing",
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

        # 2. Validate field & relationship provenance
        for prov_file in prov_files:
            try:
                p_data = json.loads(prov_file.read_text(encoding="utf-8"))
                field_prov_list = p_data.get("field_provenance", [])
                rel_prov_list = p_data.get("relationship_provenance", [])

                for fp in field_prov_list:
                    can_id_str = str(fp.get("canonical_record_id", ""))
                    src_file_name = Path(fp.get("source_file_path", "")).name
                    src_path = source_root / src_file_name
                    locator = fp.get("source_record_locator", "")
                    src_field = fp.get("source_field_name", "")
                    expected_raw = fp.get("raw_value")

                    # If file doesn't exist, check authorized missing family
                    if not src_path.exists():
                        if "MISSING_FAMILY" not in authorized_types:
                            issues.append(
                                ValidationIssue(
                                    code="PROV_SOURCE_FILE_MISSING",
                                    severity=GateSeverity.BLOCKING,
                                    gate_index=9,
                                    gate_name=self.gate_name,
                                    scope="field_provenance",
                                    target=src_file_name,
                                    message=f"Source file '{src_file_name}' missing from disk",
                                    expected="Existing rendered source file",
                                    actual="Missing",
                                )
                            )
                        continue

                    records = _get_source_records(src_path)
                    if records is None:
                        continue

                    # Parse locator index
                    row_idx: int | None = None
                    if locator.startswith("row:"):
                        with contextlib.suppress(ValueError):
                            row_idx = int(locator.split(":")[1]) - 1
                    elif locator.startswith("[") and locator.endswith("]"):
                        with contextlib.suppress(ValueError):
                            row_idx = int(locator[1:-1])

                    if row_idx is None or row_idx >= len(records):
                        # Could be authorized partial submission or duplicate
                        is_auth_locator = can_id_str in authorized_targets or any(
                            t in authorized_types for t in ("PARTIAL_SUBMISSION", "MISSING_FAMILY")
                        )
                        if not is_auth_locator:
                            issues.append(
                                ValidationIssue(
                                    code="PROV_LOCATOR_NOT_FOUND",
                                    severity=GateSeverity.BLOCKING,
                                    gate_index=9,
                                    gate_name=self.gate_name,
                                    scope="field_provenance",
                                    target=f"{src_file_name}:{locator}",
                                    message=(
                                        f"Source locator '{locator}' not found in '{src_file_name}'"
                                    ),
                                    expected=f"Record index < {len(records)}",
                                    actual=str(row_idx),
                                )
                            )
                        continue

                    record_row = records[row_idx]
                    actual_raw = record_row.get(src_field)

                    # Compare raw lexical value from disk
                    if actual_raw != expected_raw:
                        # Check authorized mutations for this target or type
                        is_auth_change = can_id_str in authorized_targets or any(
                            t in authorized_types
                            for t in (
                                "MISSING_FIELD",
                                "MALFORMED_VALUE",
                                "SCHEMA_DRIFT",
                                "VOCABULARY_DRIFT",
                                "TIMESTAMP_PROBLEM",
                                "SOURCE_ID_ABSENCE",
                                "EXACT_DUPLICATE",
                                "CONFLICTING_DUPLICATE",
                                "COUNT_MISMATCH",
                            )
                        )
                        if not is_auth_change:
                            issues.append(
                                ValidationIssue(
                                    code="PROV_RAW_VALUE_MISMATCH",
                                    severity=GateSeverity.BLOCKING,
                                    gate_index=9,
                                    gate_name=self.gate_name,
                                    scope="field_lineage",
                                    target=f"{src_file_name}:{locator}:{src_field}",
                                    message=(
                                        f"Raw lexical value mismatch for field '{src_field}'. "
                                        f"Expected '{expected_raw}', got '{actual_raw}'"
                                    ),
                                    expected=str(expected_raw),
                                    actual=str(actual_raw),
                                )
                            )

                # Validate relationship provenance
                for rp in rel_prov_list:
                    sub_id = str(rp.get("canonical_subject_id", ""))
                    src_file_name = Path(rp.get("source_file_path", "")).name
                    src_path = source_root / src_file_name
                    if not src_path.exists():
                        continue

                    # If authorized broken relationship, skip failure
                    is_auth_rel = sub_id in authorized_targets or (
                        "BROKEN_RELATIONSHIP" in authorized_types
                    )
                    records = _get_source_records(src_path)
                    if records is None:
                        continue

                    loc = rp.get("source_record_locator", "")
                    r_idx: int | None = None
                    if loc.startswith("row:"):
                        with contextlib.suppress(ValueError):
                            r_idx = int(loc.split(":")[1]) - 1
                    elif loc.startswith("[") and loc.endswith("]"):
                        with contextlib.suppress(ValueError):
                            r_idx = int(loc[1:-1])

                    if (r_idx is None or r_idx >= len(records)) and not is_auth_rel:
                        issues.append(
                            ValidationIssue(
                                code="PROV_REL_LOCATOR_NOT_FOUND",
                                severity=GateSeverity.BLOCKING,
                                gate_index=9,
                                gate_name=self.gate_name,
                                scope="relationship_provenance",
                                target=f"{src_file_name}:{loc}",
                                message=f"Relationship locator '{loc}' not found",
                                expected=f"Valid row index < {len(records)}",
                                actual=str(r_idx),
                            )
                        )

            except Exception as exc:
                issues.append(
                    ValidationIssue(
                        code="PROV_PARSE_FAILURE",
                        severity=GateSeverity.BLOCKING,
                        gate_index=9,
                        gate_name=self.gate_name,
                        scope="oracle",
                        target=prov_file.name,
                        message=f"Failed to parse provenance file '{prov_file.name}': {exc}",
                        expected="Valid provenance JSON",
                        actual=str(exc),
                    )
                )

        return self.create_report(
            issues,
            metadata={
                "index_files_scanned": len(index_files),
                "provenance_files_scanned": len(prov_files),
            },
        )
