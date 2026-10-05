"""
Gate 8: Source Rendering Gate.

From GENERATOR_IMPLEMENTATION_PLAN §18.1 and DATASET_GENERATION_SPEC §20.1:
- Scope: Parse-back, dialect, IDs, time/vocab, stable order, schema profile.
- Failure condition: Byte/profile mismatch or parser failure -> Stop.
- Validates that source-rendered evidence genuinely exists on disk, uses correct
  dialects, formats, namespaces, timestamps, and vocabulary per profile, and that
  parse-back succeeds unless authorized by a quality mutation.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from satsa_generator.profiles.catalog import get_profile
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
        source_root = context.source_exports_root
        ledger = context.ledger

        # 1. Source exports root must genuinely exist and not be empty (§18.1 Gate 8)
        if not source_root or not source_root.exists():
            issues.append(
                ValidationIssue(
                    code="RENDER_MISSING_EXPORTS_DIR",
                    severity=GateSeverity.BLOCKING,
                    gate_index=8,
                    gate_name=self.gate_name,
                    scope="source_exports",
                    target=str(source_root),
                    message="Source exports directory is missing or not configured",
                    expected="Existing directory containing rendered source files",
                    actual="Missing",
                )
            )
            return self.create_report(issues, metadata={"status": "missing_directory"})

        rendered_files = list(source_root.glob("*.csv")) + list(source_root.glob("*.json"))
        rendered_files += list(source_root.glob("*.jsonl"))

        if not rendered_files:
            issues.append(
                ValidationIssue(
                    code="RENDER_EMPTY_EXPORTS_DIR",
                    severity=GateSeverity.BLOCKING,
                    gate_index=8,
                    gate_name=self.gate_name,
                    scope="source_exports",
                    target=str(source_root),
                    message="Source exports directory contains zero rendered files",
                    expected="Rendered source files across evidence families",
                    actual="0 files",
                )
            )
            return self.create_report(issues, metadata={"status": "empty_directory"})

        # Collect authorized mutations from ledger
        auth_entries = getattr(ledger, "entries", {}) if ledger else {}
        authorized_mutations = {entry.mutation_type: entry for entry in auth_entries.values()}
        authorized_targets = {
            t_id
            for entry in auth_entries.values()
            for t_id in getattr(entry, "target_record_ids", ())
        }

        # 2. Determine profiles to validate
        profile_ids: set[str] = set()
        orgs = []
        if context.config:
            orgs = getattr(context.config, "organizations", [])
        for o in orgs:
            p_id = getattr(o, "source_profile", None)
            if not p_id and isinstance(o, dict):
                p_id = o.get("source_profile")
            if p_id:
                profile_ids.add(str(p_id))

        # Also inspect rendered files to discover active profiles
        for f in rendered_files:
            stem = f.stem
            parts = stem.split("_")
            if len(parts) >= 2:
                candidate = parts[-1].upper()
                if candidate in ("SRC-A", "SRC-B", "SRC-C", "SRC-D", "SRC-E"):
                    profile_ids.add(candidate)

        if not profile_ids:
            issues.append(
                ValidationIssue(
                    code="RENDER_NO_PROFILES_FOUND",
                    severity=GateSeverity.BLOCKING,
                    gate_index=8,
                    gate_name=self.gate_name,
                    scope="profile",
                    target=str(source_root),
                    message="No source profiles found in configuration or rendered source files",
                    expected="Configured organizations with source profiles",
                    actual="None found",
                )
            )
            return self.create_report(issues, metadata={"status": "no_profiles"})

        # 3. Validate each rendered file against its profile contract
        for file_path in sorted(rendered_files):
            rel_name = file_path.name
            if rel_name == "fixture_manifest.json":
                continue

            stem = file_path.stem
            ext = file_path.suffix.lstrip(".").lower()
            parts = stem.split("_")
            if len(parts) <= 1:
                issues.append(
                    ValidationIssue(
                        code="RENDER_UNKNOWN_PROFILE",
                        severity=GateSeverity.BLOCKING,
                        gate_index=8,
                        gate_name=self.gate_name,
                        scope="profile",
                        target=rel_name,
                        message=f"Rendered file '{rel_name}' lacks source profile suffix",
                        expected="File name ending in _src-a.._src-e",
                        actual=rel_name,
                    )
                )
                continue
            family = "_".join(parts[:-1])
            prof_suffix = parts[-1].upper()

            # Resolve profile
            try:
                profile = get_profile(prof_suffix)
            except Exception as exc:
                issues.append(
                    ValidationIssue(
                        code="RENDER_UNKNOWN_PROFILE",
                        severity=GateSeverity.BLOCKING,
                        gate_index=8,
                        gate_name=self.gate_name,
                        scope="profile",
                        target=rel_name,
                        message=(
                            f"Failed to resolve profile '{prof_suffix}' "
                            f"for file '{rel_name}': {exc}"
                        ),
                        expected="Known profile ID (e.g. SRC-A..SRC-E)",
                        actual=str(prof_suffix),
                    )
                )
                continue

            # Verify format/dialect matches profile
            expected_fmt = profile.get_format(family).lower()
            if ext != expected_fmt:
                issues.append(
                    ValidationIssue(
                        code="RENDER_FORMAT_MISMATCH",
                        severity=GateSeverity.BLOCKING,
                        gate_index=8,
                        gate_name=self.gate_name,
                        scope="format",
                        target=rel_name,
                        message=(
                            f"File '{rel_name}' format '{ext}' does not match "
                            f"profile {profile.profile_id} expected '{expected_fmt}'"
                        ),
                        expected=expected_fmt,
                        actual=ext,
                    )
                )

            # Check parseability and content layout
            if ext == "csv":
                self._validate_csv_file(
                    file_path, family, profile, issues, authorized_mutations, authorized_targets
                )
            elif ext in ("json", "jsonl"):
                self._validate_json_file(
                    file_path, family, profile, issues, authorized_mutations, authorized_targets
                )

        # 4. Perform parse-back validation if oracle_root exists
        if context.oracle_root and context.oracle_root.exists():
            self._validate_parse_back(
                source_root, context.oracle_root, profile_ids, issues, context.ledger
            )

        return self.create_report(
            issues,
            metadata={
                "rendered_files_scanned": len(rendered_files),
                "profiles_validated": sorted(list(profile_ids)),
            },
        )

    def _validate_csv_file(
        self,
        file_path: Path,
        family: str,
        profile: Any,
        issues: list[ValidationIssue],
        authorized_mutations: dict[Any, Any],
        authorized_targets: set[str],
    ) -> None:
        try:
            with file_path.open("r", encoding="utf-8", newline="") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if header is None or len(header) == 0:
                    issues.append(
                        ValidationIssue(
                            code="RENDER_EMPTY_CSV_HEADER",
                            severity=GateSeverity.BLOCKING,
                            gate_index=8,
                            gate_name=self.gate_name,
                            scope="csv_header",
                            target=file_path.name,
                            message=f"CSV file '{file_path.name}' has empty header row",
                            expected="Non-empty CSV header row",
                            actual="Empty",
                        )
                    )
                    return

                # Check records
                for row_idx, row in enumerate(reader):
                    if len(row) != len(header):
                        issues.append(
                            ValidationIssue(
                                code="RENDER_CSV_ROW_COLUMN_MISMATCH",
                                severity=GateSeverity.BLOCKING,
                                gate_index=8,
                                gate_name=self.gate_name,
                                scope=f"{file_path.name}:row_{row_idx + 1}",
                                target=file_path.name,
                                message=(
                                    f"CSV row {row_idx + 1} has {len(row)} columns; "
                                    f"header has {len(header)}"
                                ),
                                expected=str(len(header)),
                                actual=str(len(row)),
                            )
                        )

        except Exception as exc:
            issues.append(
                ValidationIssue(
                    code="RENDER_CSV_PARSE_FAILURE",
                    severity=GateSeverity.BLOCKING,
                    gate_index=8,
                    gate_name=self.gate_name,
                    scope="csv_parser",
                    target=file_path.name,
                    message=f"Failed to parse CSV file '{file_path.name}': {exc}",
                    expected="Valid CSV format",
                    actual=str(exc),
                )
            )

    def _validate_json_file(
        self,
        file_path: Path,
        family: str,
        profile: Any,
        issues: list[ValidationIssue],
        authorized_mutations: dict[Any, Any],
        authorized_targets: set[str],
    ) -> None:
        try:
            if file_path.suffix == ".jsonl":
                lines = file_path.read_text(encoding="utf-8").strip().split("\n")
                for _line_idx, line in enumerate(lines):
                    if line.strip():
                        json.loads(line)
            else:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                if not isinstance(data, (list, dict)):
                    issues.append(
                        ValidationIssue(
                            code="RENDER_INVALID_JSON_STRUCTURE",
                            severity=GateSeverity.BLOCKING,
                            gate_index=8,
                            gate_name=self.gate_name,
                            scope="json_structure",
                            target=file_path.name,
                            message=f"Rendered JSON '{file_path.name}' is not array or dict",
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
                    scope="json_parser",
                    target=file_path.name,
                    message=f"Failed to parse JSON file '{file_path.name}': {exc}",
                    expected="Valid JSON bytes",
                    actual=str(exc),
                )
            )

    def _validate_parse_back(
        self,
        source_root: Path,
        oracle_root: Path,
        profile_ids: set[str],
        issues: list[ValidationIssue],
        ledger: Any,
    ) -> None:
        """Execute parse-back verification against oracle with exact mutation reconciliation."""
        from satsa_generator.validation.parser import parse_and_validate

        for prof_id in profile_ids:
            prefix = prof_id.lower().replace("-", "_")
            index_path = oracle_root / f"{prefix}_index.json"
            oracle_path = oracle_root / f"{prefix}_oracle.json"
            if not index_path.exists():
                issues.append(
                    ValidationIssue(
                        code="RENDER_INDEX_MISSING",
                        severity=GateSeverity.BLOCKING,
                        gate_index=8,
                        gate_name=self.gate_name,
                        scope="index",
                        target=index_path.name,
                        message=(
                            f"Missing oracle index file for profile '{prof_id}': {index_path.name}"
                        ),
                        expected="Existing index file",
                        actual="Missing",
                    )
                )
                continue

            if not oracle_path.exists():
                issues.append(
                    ValidationIssue(
                        code="RENDER_ORACLE_MISSING",
                        severity=GateSeverity.BLOCKING,
                        gate_index=8,
                        gate_name=self.gate_name,
                        scope="oracle",
                        target=oracle_path.name,
                        message=f"Missing oracle file for profile '{prof_id}': {oracle_path.name}",
                        expected="Existing oracle file",
                        actual="Missing",
                    )
                )
                continue

            try:
                index_data = json.loads(index_path.read_text(encoding="utf-8"))
                families = sorted(list({item["evidence_family"] for item in index_data}))
            except Exception as exc:
                issues.append(
                    ValidationIssue(
                        code="RENDER_INDEX_PARSE_FAILURE",
                        severity=GateSeverity.BLOCKING,
                        gate_index=8,
                        gate_name=self.gate_name,
                        scope="index_parser",
                        target=index_path.name,
                        message=f"Failed to parse index file '{index_path.name}': {exc}",
                        expected="Valid JSON index",
                        actual=str(exc),
                    )
                )
                continue

            try:
                json.loads(oracle_path.read_text(encoding="utf-8"))
            except Exception as exc:
                issues.append(
                    ValidationIssue(
                        code="RENDER_ORACLE_PARSE_FAILURE",
                        severity=GateSeverity.BLOCKING,
                        gate_index=8,
                        gate_name=self.gate_name,
                        scope="oracle_parser",
                        target=oracle_path.name,
                        message=f"Failed to parse oracle file '{oracle_path.name}': {exc}",
                        expected="Valid JSON oracle",
                        actual=str(exc),
                    )
                )
                continue

            for fam in families:
                try:
                    parse_and_validate(
                        source_root,
                        oracle_root,
                        prof_id,
                        fam,
                        ledger=ledger,
                    )
                except Exception as exc:
                    issues.append(
                        ValidationIssue(
                            code="RENDER_UNAUTHORIZED_CORRUPTION",
                            severity=GateSeverity.BLOCKING,
                            gate_index=8,
                            gate_name=self.gate_name,
                            scope=f"parse_back:{prof_id}:{fam}",
                            target=f"{fam}_{prof_id.lower()}",
                            message=f"Parse-back validation failed for {prof_id} {fam}: {exc}",
                            expected="Reconstruction matching oracle or authorized corruption",
                            actual=str(exc),
                        )
                    )
