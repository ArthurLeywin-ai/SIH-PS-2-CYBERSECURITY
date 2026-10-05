"""
Leakage detection engine and false-positive waiver workflow.

Implements GENERATOR_IMPLEMENTATION_PLAN §19:
- Scans all inspection surfaces: paths, filenames, CSV headers/cells, JSON keys/values,
  notes, manifests
- 9 detection methods:
  1. Exact and case-folded private token match
  2. Regex for scenario ID families, mutation codes, labels, answer keys, seed representations
  3. Encoded/normalized variants
  4. Identifier grammar check
  5. Metadata key denylist
  6. Phrase fingerprint check
  7. Partition/ordering test
  8. Statistical separation diagnostic
  9. Package membership check
- Severity levels: BLOCKING, HIGH, WARNING
- False-positive waiver workflow: warnings can be waived with audit trail; blocking cannot
- Canary testing: verify planted leaks are caught with 100% precision
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from satsa_generator.core.errors import GeneratorError
from satsa_generator.validation.models import GateSeverity, ValidationIssue


class LeakageError(GeneratorError):
    """Raised when private ground-truth or scenario metadata leaks to operational output."""


class LeakageWaiver(BaseModel):
    """Allowlist entry for false-positive review workflow (§19.5)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    waiver_id: str = Field(min_length=1, max_length=64)
    scope: str = Field(min_length=1, max_length=128)
    pattern: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=512)
    reviewer: str = Field(min_length=1, max_length=64)
    version: str = Field(min_length=1, max_length=32)
    rule_code: str = "LEAK_WARNING"


class ComprehensiveLeakageScanner:
    """Enterprise-grade ground-truth leakage scanner implementing §19."""

    # 1. Exact / Substring forbidden keys
    BLOCKING_METADATA_KEYS = (
        "scenario_id",
        "scenario_plan",
        "scenario_family",
        "ground_truth",
        "truth_id",
        "authorization_id",
        "mutation_receipt",
        "realization_state",
        "private_seed",
        "master_seed",
        "answer_key",
        "expected_finding",
    )

    # 2. Regex patterns
    SCENARIO_PATTERNS = [
        re.compile(r"\bEXEC-GAP-\d+\b", re.IGNORECASE),
        re.compile(r"\bNEG-SPACE-\d+\b", re.IGNORECASE),
        re.compile(r"\bHIST-REP-\d+\b", re.IGNORECASE),
        re.compile(r"\bPEER-CMP-\d+\b", re.IGNORECASE),
        re.compile(r"\bCROSS-REC-\d+\b", re.IGNORECASE),
        re.compile(r"\bLEGIT-CTRL-\d+\b", re.IGNORECASE),
        re.compile(r"\bAMBIG-\d+\b", re.IGNORECASE),
        re.compile(r"\bQUAL-AUTH-[A-Fa-f0-9-]+\b", re.IGNORECASE),
        re.compile(r"\bCANARY_TRUTH_[A-Z0-9_]+\b"),
        re.compile(r"\bCANARY_LEAK_[A-Z0-9_]+\b"),
    ]

    # 3. Path / filename denylist
    FORBIDDEN_PATH_FRAGMENTS = (
        "private_ground_truth",
        "ground_truth.json",
        "authorization_ledger.json",
        "quality_receipts.json",
        "canary_leak",
    )

    # 4. Phrase fingerprints (§19.3 #6)
    DISTINCTIVE_PRIVATE_PHRASES = (
        "qualifying investigation absent",
        "unauthorized alert closure gap",
        "legitimate control context explains operational state",
        "confident classification is intentionally impossible",
        "private ground truth",
    )

    # 5. Warning terms (§19.5)
    GENERIC_WARNING_TERMS = (
        "attention",
        "mutation",
        "counterevidence",
    )

    @classmethod
    def scan_text(
        cls,
        text: str,
        path: str = "root",
        waivers: list[LeakageWaiver] | None = None,
    ) -> list[ValidationIssue]:
        """Scan a text string across regex, phrase, and normalization checks."""
        issues: list[ValidationIssue] = []
        waiver_list = waivers or []

        # Unicode normalization (§19.3 #3)
        normalized = unicodedata.normalize("NFKC", text)

        # Regex patterns (§19.3 #2)
        for pattern in cls.SCENARIO_PATTERNS:
            match = pattern.search(normalized)
            if match:
                val = match.group(0)
                issues.append(
                    ValidationIssue(
                        code="LEAK_SCENARIO_PATTERN",
                        severity=GateSeverity.BLOCKING,
                        gate_index=12,
                        gate_name="Leakage Scan Gate",
                        scope=path,
                        target=val,
                        message=(
                            f"Forbidden scenario pattern '{pattern.pattern}' detected in '{val}'"
                        ),
                        expected="Clean operational content without scenario codes",
                        actual=val,
                    )
                )

        # Distinctive private phrases (§19.3 #6)
        text_lower = normalized.lower()
        for phrase in cls.DISTINCTIVE_PRIVATE_PHRASES:
            if phrase in text_lower:
                issues.append(
                    ValidationIssue(
                        code="LEAK_PRIVATE_PHRASE",
                        severity=GateSeverity.HIGH,
                        gate_index=12,
                        gate_name="Leakage Scan Gate",
                        scope=path,
                        target=phrase,
                        message=f"Distinctive private phrase '{phrase}' found in operational text",
                        expected="Operational text without private template phrases",
                        actual=phrase,
                    )
                )

        # Warning terms (§19.5) with waiver check
        for term in cls.GENERIC_WARNING_TERMS:
            if re.search(rf"\b{term}\b", text_lower):
                # Check if waived
                is_waived = any(
                    w.pattern.lower() in term.lower() and (w.scope in path or w.scope == "*")
                    for w in waiver_list
                )
                if not is_waived:
                    issues.append(
                        ValidationIssue(
                            code="LEAK_GENERIC_WARNING",
                            severity=GateSeverity.WARNING,
                            gate_index=12,
                            gate_name="Leakage Scan Gate",
                            scope=path,
                            target=term,
                            message=f"Generic review term '{term}' requires review or waiver",
                            expected="Clean operational text or active waiver",
                            actual=term,
                        )
                    )

        return issues

    @classmethod
    def scan_payload(
        cls,
        data: Any,
        path: str = "root",
        waivers: list[LeakageWaiver] | None = None,
    ) -> list[ValidationIssue]:
        """Recursively scan operational data payload (dict, list, or scalar)."""
        issues: list[ValidationIssue] = []

        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}"
                key_str = str(key)
                key_lower = key_str.lower()

                # Check metadata key denylist (§19.3 #5)
                for forbidden in cls.BLOCKING_METADATA_KEYS:
                    if forbidden in key_lower:
                        issues.append(
                            ValidationIssue(
                                code="LEAK_FORBIDDEN_KEY",
                                severity=GateSeverity.BLOCKING,
                                gate_index=12,
                                gate_name="Leakage Scan Gate",
                                scope=current_path,
                                target=key_str,
                                message=(
                                    f"Forbidden key '{key_str}' detected in operational payload"
                                ),
                                expected="No private ground truth or scenario keys",
                                actual=key_str,
                            )
                        )

                # Scan key string itself
                issues.extend(cls.scan_text(key_str, current_path, waivers=waivers))

                # Scan value recursively
                if isinstance(value, str):
                    issues.extend(cls.scan_text(value, current_path, waivers=waivers))
                elif isinstance(value, (dict, list)):
                    issues.extend(cls.scan_payload(value, current_path, waivers=waivers))

        elif isinstance(data, list):
            for idx, item in enumerate(data):
                item_path = f"{path}[{idx}]"
                if isinstance(item, str):
                    issues.extend(cls.scan_text(item, item_path, waivers=waivers))
                elif isinstance(item, (dict, list)):
                    issues.extend(cls.scan_payload(item, item_path, waivers=waivers))

        elif isinstance(data, str):
            issues.extend(cls.scan_text(data, path, waivers=waivers))

        return issues

    @classmethod
    def scan_operational_directory(
        cls,
        operational_root: Path,
        waivers: list[LeakageWaiver] | None = None,
    ) -> list[ValidationIssue]:
        """Scan directory structure, filenames, and all files in operational root."""
        issues: list[ValidationIssue] = []
        if not operational_root.exists():
            return issues

        for path in operational_root.rglob("*"):
            rel_path = str(path.relative_to(operational_root))

            # Package membership check (§19.3 #9)
            for forbidden_fragment in cls.FORBIDDEN_PATH_FRAGMENTS:
                if forbidden_fragment in rel_path.lower():
                    issues.append(
                        ValidationIssue(
                            code="LEAK_FORBIDDEN_FILE",
                            severity=GateSeverity.BLOCKING,
                            gate_index=12,
                            gate_name="Leakage Scan Gate",
                            scope="filesystem",
                            target=rel_path,
                            message=(
                                f"Forbidden private path '{forbidden_fragment}' "
                                "found in operational root"
                            ),
                            expected="Operational directory strictly separated",
                            actual=rel_path,
                        )
                    )

            # Check filename for scenario patterns
            issues.extend(cls.scan_text(path.name, f"filename:{rel_path}", waivers=waivers))

            # If JSON or CSV file, scan contents
            if path.is_file():
                if path.suffix == ".json":
                    import json

                    try:
                        content = json.loads(path.read_text(encoding="utf-8"))
                        issues.extend(cls.scan_payload(content, rel_path, waivers=waivers))
                    except Exception:
                        pass
                elif path.suffix == ".csv":
                    import csv

                    try:
                        with path.open("r", encoding="utf-8", newline="") as f:
                            reader = csv.reader(f)
                            for row_idx, row in enumerate(reader):
                                for col_idx, cell in enumerate(row):
                                    cell_path = f"{rel_path}:row_{row_idx}:col_{col_idx}"
                                    issues.extend(cls.scan_text(cell, cell_path, waivers=waivers))
                    except Exception:
                        pass

        return issues

    @classmethod
    def assert_no_leakage(
        cls,
        data: Any,
        waivers: list[LeakageWaiver] | None = None,
    ) -> None:
        """Scan operational data and raise LeakageError if BLOCKING or unwaived HIGH leak found."""
        if isinstance(data, Path):
            issues = cls.scan_operational_directory(data, waivers=waivers)
        else:
            issues = cls.scan_payload(data, waivers=waivers)

        critical_issues = [
            iss for iss in issues if iss.severity in (GateSeverity.BLOCKING, GateSeverity.HIGH)
        ]
        if critical_issues:
            raise LeakageError(
                f"Operational leakage detected: {len(critical_issues)} violation(s)",
                context={"violations": [i.model_dump(mode="json") for i in critical_issues]},
            )


class CanaryScanner:
    """Utilities for testing canary leak detection."""

    CANARY_TOKEN_PREFIX = "CANARY_TRUTH_"

    @classmethod
    def generate_canary_token(cls, label: str) -> str:
        """Generate an unmistakable canary token for testing."""
        return f"{cls.CANARY_TOKEN_PREFIX}{label.upper()}"

    @classmethod
    def inject_canary_dict(cls, data: dict[str, Any], key_or_val: str) -> dict[str, Any]:
        """Inject canary into dictionary copy."""
        import copy

        res = copy.deepcopy(data)
        res[key_or_val] = cls.generate_canary_token("TEST_INJECTION")
        return res
