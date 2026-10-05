"""
Validation models for the 14-gate validation framework.

From GENERATOR_IMPLEMENTATION_PLAN §18:
- Pure/read-only validators returning structured issues.
- Issues contain code, severity (BLOCKING, HIGH, WARNING, INFO), scope, target,
  message, expected, actual.
- Failure conditions defined per gate in §18.1.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GateSeverity(enum.StrEnum):
    """Issue severity levels from GENERATOR_IMPLEMENTATION_PLAN §18.3, §19.5."""

    BLOCKING = "BLOCKING"
    HIGH = "HIGH"
    WARNING = "WARNING"
    INFO = "INFO"


class GateStatus(enum.StrEnum):
    """Outcome status for a validation gate."""

    PASSED = "PASSED"
    FAILED = "FAILED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class ValidationIssue(BaseModel):
    """Structured issue returned by a validation gate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str = Field(min_length=1, max_length=64)
    severity: GateSeverity
    gate_index: int = Field(ge=1, le=14)
    gate_name: str = Field(min_length=1, max_length=128)
    scope: str = Field(min_length=1, max_length=128)
    target: str = Field(min_length=1, max_length=256)
    message: str = Field(min_length=1, max_length=1024)
    expected: str | None = None
    actual: str | None = None
    validator_version: str = "1.0.0"


class GateReport(BaseModel):
    """Report produced by executing a single validation gate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    gate_index: int = Field(ge=1, le=14)
    gate_name: str = Field(min_length=1, max_length=128)
    status: GateStatus
    passed: bool
    issues: tuple[ValidationIssue, ...] = Field(default_factory=tuple)
    metadata: dict[str, Any] = Field(default_factory=dict)
    evaluated_at_utc: str = "2026-10-05T00:00:00Z"


class FullValidationReport(BaseModel):
    """Aggregated validation report across all 14 gates."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    overall_status: GateStatus
    all_passed: bool
    gate_reports: dict[int, GateReport]
    blocking_issue_count: int = 0
    high_issue_count: int = 0
    warning_issue_count: int = 0
    total_issues: int = 0
    evaluated_at_utc: str = "2026-10-05T00:00:00Z"


@dataclass
class ValidationContext:
    """Read-only context passed to validation gates."""

    config: Any
    records: dict[str, list[Any]]
    ledger: Any
    ground_truth: list[Any] = field(default_factory=list)
    receipts: list[Any] = field(default_factory=list)
    operational_root: Path | None = None
    output_root: Path | None = None
    manifest: Any = None
    source_exports_root: Path | None = None
    oracle_root: Path | None = None
    waivers: list[Any] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)
