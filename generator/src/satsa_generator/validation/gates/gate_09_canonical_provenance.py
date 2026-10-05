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
            except Exception as exc:
                issues.append(
                    ValidationIssue(
                        code="PROV_SOURCE_FILE_CORRUPT",
                        severity=GateSeverity.BLOCKING,
                        gate_index=9,
                        gate_name=self.gate_name,
                        scope="source_file",
                        target=file_p.name,
                        message=f"Source file '{file_p.name}' is corrupt or unreadable: {exc}",
                        expected="Readable, well-formed source file",
                        actual=str(exc),
                    )
                )
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
                        is_auth_missing_file = False
                        if context.ledger:
                            for entry in context.ledger.entries.values():
                                t_fam = getattr(entry, "target_family", "")
                                m_tp = str(getattr(entry, "mutation_type", ""))
                                if "." in m_tp:
                                    m_tp = m_tp.split(".")[-1]
                                if t_fam and t_fam in src_file.name and m_tp == "MISSING_FAMILY":
                                    is_auth_missing_file = True
                                    break
                        if not is_auth_missing_file:
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
            prof_parts = prov_file.stem.split("_")
            if len(prof_parts) < 2:
                issues.append(
                    ValidationIssue(
                        code="PROV_UNKNOWN_PROFILE",
                        severity=GateSeverity.BLOCKING,
                        gate_index=9,
                        gate_name=self.gate_name,
                        scope="profile",
                        target=prov_file.name,
                        message=f"Provenance file '{prov_file.name}' lacks valid profile prefix",
                        expected="File name starting with <profile>_provenance.json",
                        actual=prov_file.name,
                    )
                )
                continue
            prof_suffix = f"{prof_parts[0].upper()}-{prof_parts[1].upper()}"
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
                        is_auth_missing_file = False
                        if context.ledger:
                            for entry in context.ledger.entries.values():
                                t_fam = getattr(entry, "target_family", "")
                                m_tp = str(getattr(entry, "mutation_type", ""))
                                if "." in m_tp:
                                    m_tp = m_tp.split(".")[-1]
                                if t_fam and t_fam in src_file_name and m_tp == "MISSING_FAMILY":
                                    is_auth_missing_file = True
                                    break
                        if not is_auth_missing_file:
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

                    # Check if this record was explicitly withheld by PARTIAL_SUBMISSION
                    is_withheld = False
                    if context.ledger:
                        for entry in context.ledger.entries.values():
                            m_tp = str(getattr(entry, "mutation_type", ""))
                            if "." in m_tp:
                                m_tp = m_tp.split(".")[-1]
                            t_ids = [str(x) for x in getattr(entry, "target_record_ids", ())]
                            if m_tp == "PARTIAL_SUBMISSION" and can_id_str in t_ids:
                                s_file = getattr(entry, "source_file", None)
                                if not s_file or s_file == src_file_name:
                                    is_withheld = True
                                    break
                    if is_withheld:
                        continue

                    # Parse locator index
                    row_idx: int | None = None
                    if locator.startswith("row:"):
                        with contextlib.suppress(ValueError):
                            clean_loc = locator.split(".")[0]
                            row_idx = int(clean_loc.split(":")[1]) - 1
                    elif locator.startswith("["):
                        with contextlib.suppress(ValueError):
                            close_bracket = locator.find("]")
                            if close_bracket != -1:
                                row_idx = int(locator[1:close_bracket])

                    if row_idx is None or row_idx >= len(records):
                        # Could be authorized partial submission or missing family
                        is_auth_locator = False
                        if context.ledger:
                            for entry in context.ledger.entries.values():
                                t_ids = [str(x) for x in getattr(entry, "target_record_ids", ())]
                                t_fam = getattr(entry, "target_family", "")
                                m_tp = str(getattr(entry, "mutation_type", ""))
                                if "." in m_tp:
                                    m_tp = m_tp.split(".")[-1]
                                if m_tp in ("PARTIAL_SUBMISSION", "MISSING_FAMILY") and (
                                    can_id_str in t_ids or (t_fam and t_fam in src_file_name)
                                ):
                                    is_auth_locator = True
                                    break
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

                    # Check source field exists in source row (top-level or nested)
                    has_field = False
                    actual_raw = None
                    if src_field in record_row:
                        has_field = True
                        actual_raw = record_row[src_field]
                    elif "." in locator:
                        parts = locator.split(".")[1:]
                        curr = record_row
                        found = True
                        for part in parts:
                            if isinstance(curr, dict) and part in curr:
                                curr = curr[part]
                            else:
                                found = False
                                break
                        if found:
                            has_field = True
                            actual_raw = curr

                    if not has_field:
                        is_auth_missing_field = False
                        if context.ledger:
                            for entry in context.ledger.entries.values():
                                t_ids = [str(x) for x in getattr(entry, "target_record_ids", ())]
                                t_fld = getattr(entry, "target_field", None)
                                s_fld = getattr(entry, "source_field", None)
                                s_file = getattr(entry, "source_file", None)
                                s_loc = getattr(entry, "source_locator", None)
                                s_prof = getattr(entry, "source_profile", None)
                                m_tp = str(getattr(entry, "mutation_type", ""))
                                if "." in m_tp:
                                    m_tp = m_tp.split(".")[-1]

                                if can_id_str not in t_ids or m_tp != "MISSING_FIELD":
                                    continue
                                if s_file and s_file != src_file_name:
                                    continue
                                if s_loc and s_loc != locator:
                                    continue
                                if s_prof and s_prof != prof_suffix:
                                    continue

                                allowed_fields = {f for f in (t_fld, s_fld) if f}
                                if allowed_fields and (
                                    src_field in allowed_fields
                                    or fp.get("canonical_field_name") in allowed_fields
                                ):
                                    is_auth_missing_field = True
                                    break
                        if not is_auth_missing_field:
                            issues.append(
                                ValidationIssue(
                                    code="PROV_SOURCE_FIELD_MISSING",
                                    severity=GateSeverity.BLOCKING,
                                    gate_index=9,
                                    gate_name=self.gate_name,
                                    scope="field_provenance",
                                    target=f"{src_file_name}:{locator}:{src_field}",
                                    message=(
                                        f"Source field '{src_field}' not found in source "
                                        f"record at '{locator}'"
                                    ),
                                    expected=f"Field '{src_field}' in record",
                                    actual="Missing",
                                )
                            )
                        continue

                    # Compare raw lexical value from disk
                    if actual_raw != expected_raw:
                        # Must be an exact authorized mutation for this record ID and field
                        is_auth_change = False
                        if context.ledger:
                            for entry in context.ledger.entries.values():
                                t_ids = [str(x) for x in getattr(entry, "target_record_ids", ())]
                                t_fld = getattr(entry, "target_field", None)
                                s_fld = getattr(entry, "source_field", None)
                                s_file = getattr(entry, "source_file", None)
                                s_loc = getattr(entry, "source_locator", None)
                                s_prof = getattr(entry, "source_profile", None)
                                m_tp = str(getattr(entry, "mutation_type", ""))
                                if "." in m_tp:
                                    m_tp = m_tp.split(".")[-1]

                                if can_id_str not in t_ids:
                                    continue
                                if s_file and s_file != src_file_name:
                                    continue
                                if (
                                    s_loc
                                    and m_tp not in ("EXACT_DUPLICATE", "CONFLICTING_DUPLICATE")
                                    and s_loc != locator
                                ):
                                    continue
                                if s_prof and s_prof != prof_suffix:
                                    continue

                                can_fld = fp.get("canonical_field_name")
                                allowed_fields = {f for f in (t_fld, s_fld) if f}
                                if allowed_fields and (
                                    src_field in allowed_fields or can_fld in allowed_fields
                                ):
                                    is_auth_change = True
                                    break

                                if m_tp == "CONFLICTING_DUPLICATE" and (
                                    src_field == "severity" or can_fld == "severity"
                                ):
                                    is_auth_change = True
                                    break

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

                    records = _get_source_records(src_path)
                    if records is None:
                        continue

                    loc = rp.get("source_record_locator", "")
                    r_idx: int | None = None
                    if loc.startswith("row:"):
                        with contextlib.suppress(ValueError):
                            clean_loc = loc.split(".")[0]
                            r_idx = int(clean_loc.split(":")[1]) - 1
                    elif loc.startswith("["):
                        with contextlib.suppress(ValueError):
                            close_bracket = loc.find("]")
                            if close_bracket != -1:
                                r_idx = int(loc[1:close_bracket])

                    is_auth_rel = False
                    if context.ledger:
                        for entry in context.ledger.entries.values():
                            t_ids = [str(x) for x in getattr(entry, "target_record_ids", ())]
                            s_file = getattr(entry, "source_file", None)
                            s_loc = getattr(entry, "source_locator", None)
                            s_prof = getattr(entry, "source_profile", None)
                            t_rel = getattr(entry, "target_relationship", None)
                            s_fld = getattr(entry, "source_field", None)
                            m_tp = str(getattr(entry, "mutation_type", ""))
                            if "." in m_tp:
                                m_tp = m_tp.split(".")[-1]

                            if sub_id not in t_ids or m_tp not in (
                                "BROKEN_RELATIONSHIP",
                                "REMOVE_RELATIONSHIP",
                            ):
                                continue

                            if s_file and s_file != src_file_name:
                                continue
                            if s_loc and s_loc != loc:
                                continue
                            if s_prof and s_prof != prof_suffix:
                                continue

                            allowed_rels = {r for r in (t_rel, s_fld) if r}
                            rel_field = rp.get("source_relationship_field")
                            if allowed_rels and rel_field and rel_field not in allowed_rels:
                                continue

                            is_auth_rel = True
                            break

                    is_auth_rel_loc = is_auth_rel
                    if not is_auth_rel_loc and context.ledger:
                        for entry in context.ledger.entries.values():
                            t_ids = [str(x) for x in getattr(entry, "target_record_ids", ())]
                            t_fam = getattr(entry, "target_family", "")
                            m_tp = str(getattr(entry, "mutation_type", ""))
                            if "." in m_tp:
                                m_tp = m_tp.split(".")[-1]
                            if m_tp in ("PARTIAL_SUBMISSION", "MISSING_FAMILY") and (
                                sub_id in t_ids or (t_fam and t_fam in src_file_name)
                            ):
                                is_auth_rel_loc = True
                                break

                    if (r_idx is None or r_idx >= len(records)) and not is_auth_rel_loc:
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
                        continue

                    if r_idx is not None and r_idx < len(records):
                        rec_row = records[r_idx]
                        rel_field = rp.get("source_relationship_field")
                        if rel_field and rel_field in rec_row:
                            actual_val = rec_row[rel_field]
                            if (
                                actual_val in ("00000000-0000-0000-0000-000000000000", "", None)
                                and not is_auth_rel
                            ):
                                issues.append(
                                    ValidationIssue(
                                        code="PROV_RELATIONSHIP_MISMATCH",
                                        severity=GateSeverity.BLOCKING,
                                        gate_index=9,
                                        gate_name=self.gate_name,
                                        scope="relationship_provenance",
                                        target=f"{src_file_name}:{loc}:{rel_field}",
                                        message=(
                                            f"Broken relationship value '{actual_val}' for field "
                                            f"'{rel_field}' without authorization"
                                        ),
                                        expected="Valid target foreign key",
                                        actual=str(actual_val),
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
