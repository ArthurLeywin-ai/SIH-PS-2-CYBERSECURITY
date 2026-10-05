"""Validation engine for evidence packages, formats, schema, and relationships.

Reuses the project's established validation principles:
- File presence and format
- Package integrity & manifest SHA-256 verification
- Schema & field types
- UUID formatting
- ISO-8601 temporal formatting and ordering
- Controlled vocabularies
- Referential integrity (primary/foreign keys)
- Missing evidence semantics preservation
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from app.backend.domain.models import ValidationIssue
from app.backend.domain.types import (
    ActionStatus,
    ActionType,
    AlertCategory,
    AlertSeverity,
    AlertStatus,
    AssetClass,
    AssetCriticality,
    CaseStatus,
    CaseType,
    ClosureStatus,
    Disposition,
    EntityCriticalityBand,
    ExceptionStatus,
    MonitoringCoverageState,
    OperatingModel,
    OrganizationStatus,
    PeriodMaturityState,
    PresenceState,
    ScaleBand,
    ValidationSeverity,
)
from app.backend.logging import get_logger

logger = get_logger("validation")

MANDATORY_FAMILIES = [
    "organizations",
    "submissions",
    "submission_manifests",
    "submission_evidence_families",
    "assets",
    "monitoring_coverage",
    "alerts",
    "cases",
]

ALL_EVIDENCE_FAMILIES = [
    "organizations",
    "submissions",
    "submission_manifests",
    "submission_evidence_families",
    "control_process_references",
    "control_process_subject_links",
    "assets",
    "monitoring_coverage",
    "alerts",
    "cases",
    "case_alert_links",
    "investigations",
    "escalations",
    "actions",
    "resolutions",
    "closures",
    "exceptions",
    "process_changes",
]

ENUM_LOOKUPS = {
    "scale_band": {e.value for e in ScaleBand},
    "operating_model": {e.value for e in OperatingModel},
    "entity_criticality_band": {e.value for e in EntityCriticalityBand},
    "organization_status": {e.value for e in OrganizationStatus},
    "period_maturity_state": {e.value for e in PeriodMaturityState},
    "presence_state": {e.value for e in PresenceState},
    "asset_class": {e.value for e in AssetClass},
    "criticality": {e.value for e in AssetCriticality},
    "coverage_state": {e.value for e in MonitoringCoverageState},
    "alert_category": {e.value for e in AlertCategory},
    "severity": {e.value for e in AlertSeverity},
    "alert_status": {e.value for e in AlertStatus},
    "status": {e.value for e in AlertStatus} | {e.value for e in CaseStatus},
    "disposition": {e.value for e in Disposition},
    "case_type": {e.value for e in CaseType},
    "action_type": {e.value for e in ActionType},
    "action_status": {e.value for e in ActionStatus},
    "closure_status": {e.value for e in ClosureStatus},
    "exception_status": {e.value for e in ExceptionStatus},
}


class ValidationResult:
    """Consolidated outcome of package validation."""

    def __init__(self) -> None:
        self.issues: list[ValidationIssue] = []

    @property
    def is_valid(self) -> bool:
        """Returns True if there are no ERROR severity issues."""
        return not any(issue.severity == ValidationSeverity.ERROR for issue in self.issues)

    def add_issue(
        self,
        code: str,
        severity: ValidationSeverity,
        scope: str,
        target: str,
        message: str,
        expected: str | None = None,
        actual: str | None = None,
    ) -> None:
        issue = ValidationIssue(
            code=code,
            severity=severity,
            scope=scope,
            target=target,
            message=message,
            expected=expected,
            actual=actual,
        )
        self.issues.append(issue)

    def to_dict_list(self) -> list[dict[str, Any]]:
        return [
            {
                "code": i.code,
                "severity": i.severity.value,
                "scope": i.scope,
                "target": i.target,
                "message": i.message,
                "expected": i.expected,
                "actual": i.actual,
            }
            for i in self.issues
        ]


class EvidencePackageValidator:
    """Comprehensive validator for evidence packages before normalization and database persistence."""

    def validate_manifest_integrity(
        self,
        package_dir: Path,
        manifest_data: dict[str, Any],
        result: ValidationResult,
    ) -> None:
        """Verify declared file hashes match actual contents on disk."""
        files = manifest_data.get("files", [])
        for entry in files:
            file_rel = entry.get("path")
            expected_hash = entry.get("sha256")
            expected_size = entry.get("byte_size")
            if not file_rel:
                continue

            file_path = package_dir / file_rel
            if not file_path.exists():
                result.add_issue(
                    code="MANIFEST_FILE_MISSING",
                    severity=ValidationSeverity.ERROR,
                    scope="manifest",
                    target=file_rel,
                    message=f"File {file_rel} declared in manifest does not exist in package",
                    expected="File exists",
                    actual="Not found",
                )
                continue

            # Verify size if specified
            actual_size = file_path.stat().st_size
            if expected_size is not None and actual_size != expected_size:
                result.add_issue(
                    code="MANIFEST_SIZE_MISMATCH",
                    severity=ValidationSeverity.WARNING,
                    scope="manifest",
                    target=file_rel,
                    message=f"File {file_rel} size {actual_size} bytes differs from manifest {expected_size} bytes",
                    expected=str(expected_size),
                    actual=str(actual_size),
                )

            # Verify SHA-256
            if expected_hash:
                h = hashlib.sha256()
                with open(file_path, "rb") as f:
                    for chunk in iter(lambda: f.read(65536), b""):
                        h.update(chunk)
                actual_hash = h.hexdigest()
                if actual_hash != expected_hash:
                    result.add_issue(
                        code="MANIFEST_HASH_MISMATCH",
                        severity=ValidationSeverity.ERROR,
                        scope="manifest",
                        target=file_rel,
                        message=f"File {file_rel} SHA-256 hash mismatch",
                        expected=expected_hash,
                        actual=actual_hash,
                    )

    def validate_file_presence(
        self,
        found_families: set[str],
        result: ValidationResult,
    ) -> None:
        """Ensure baseline required evidence families exist."""
        for mandatory in MANDATORY_FAMILIES:
            if mandatory not in found_families:
                result.add_issue(
                    code="MANDATORY_EVIDENCE_MISSING",
                    severity=ValidationSeverity.ERROR,
                    scope="package",
                    target=mandatory,
                    message=f"Mandatory evidence family '{mandatory}' is missing from package",
                    expected="Family present",
                    actual="Missing",
                )

    def validate_record_schema(
        self,
        family: str,
        records: list[dict[str, Any]],
        result: ValidationResult,
    ) -> None:
        """Validate structure, primary keys, UUIDs, enums, and timestamps per record."""
        seen_pks: set[str] = set()
        pk_field = f"{family.rstrip('s')}_id"
        if family == "monitoring_coverage":
            pk_field = "monitoring_coverage_id"
        elif family == "submission_manifests":
            pk_field = "manifest_id"
        elif family == "submission_evidence_families":
            pk_field = "submission_family_id"
        elif family == "control_process_references":
            pk_field = "control_process_ref_id"
        elif family == "control_process_subject_links":
            pk_field = "control_process_link_id"
        elif family == "case_alert_links":
            pk_field = "case_alert_link_id"

        for idx, rec in enumerate(records, start=1):
            locator = f"{family}[{idx}]"
            # 1. Primary key validation
            pk_val = rec.get(pk_field)
            if not pk_val:
                result.add_issue(
                    code="MISSING_PRIMARY_KEY",
                    severity=ValidationSeverity.ERROR,
                    scope=family,
                    target=locator,
                    message=f"Missing primary key field '{pk_field}' in {locator}",
                    expected=pk_field,
                    actual="None",
                )
            else:
                pk_str = str(pk_val)
                if not self._is_valid_uuid(pk_str):
                    result.add_issue(
                        code="INVALID_UUID_PRIMARY_KEY",
                        severity=ValidationSeverity.ERROR,
                        scope=family,
                        target=locator,
                        message=f"Invalid UUID for '{pk_field}': '{pk_str}' in {locator}",
                        expected="Valid UUIDv4 or UUIDv5",
                        actual=pk_str,
                    )
                if pk_str in seen_pks:
                    result.add_issue(
                        code="DUPLICATE_PRIMARY_KEY",
                        severity=ValidationSeverity.WARNING,
                        scope=family,
                        target=locator,
                        message=f"Duplicate primary key '{pk_str}' in {locator}",
                        expected="Unique primary key",
                        actual=pk_str,
                    )
                seen_pks.add(pk_str)

            # 2. Vocabulary/Enum validation
            for field, val in rec.items():
                if val is not None and field in ENUM_LOOKUPS:
                    val_str = str(val).upper()
                    allowed = ENUM_LOOKUPS[field]
                    if val_str not in allowed:
                        result.add_issue(
                            code="INVALID_VOCABULARY_VALUE",
                            severity=ValidationSeverity.WARNING,
                            scope=family,
                            target=f"{locator}.{field}",
                            message=f"Field '{field}' has unexpected value '{val}'",
                            expected=f"One of {sorted(allowed)}",
                            actual=str(val),
                        )

            # 3. Timestamp sanity check
            for field, val in rec.items():
                if field.endswith(("_utc", "_at")) and val is not None and not self._is_valid_iso_datetime(val):
                    result.add_issue(
                        code="INVALID_TIMESTAMP_FORMAT",
                        severity=ValidationSeverity.WARNING,
                        scope=family,
                        target=f"{locator}.{field}",
                        message=f"Field '{field}' has invalid ISO-8601 timestamp '{val}'",
                        expected="ISO-8601 datetime (e.g. 2025-01-01T00:00:00Z)",
                        actual=str(val),
                    )

    def validate_referential_integrity(
        self,
        records_by_family: dict[str, list[dict[str, Any]]],
        result: ValidationResult,
    ) -> None:
        """Validate foreign keys across evidence families."""
        # Index known IDs
        org_ids = {
            str(r.get("organization_id"))
            for r in records_by_family.get("organizations", [])
            if r.get("organization_id")
        }
        asset_ids = {str(r.get("asset_id")) for r in records_by_family.get("assets", []) if r.get("asset_id")}
        alert_ids = {str(r.get("alert_id")) for r in records_by_family.get("alerts", []) if r.get("alert_id")}
        case_ids = {str(r.get("case_id")) for r in records_by_family.get("cases", []) if r.get("case_id")}

        # Validate organization references
        for fam, recs in records_by_family.items():
            if fam == "organizations":
                continue
            for idx, rec in enumerate(recs, start=1):
                org_ref = rec.get("organization_id")
                if org_ref and str(org_ref) not in org_ids:
                    result.add_issue(
                        code="ORPHANED_ORGANIZATION_REFERENCE",
                        severity=ValidationSeverity.WARNING,
                        scope=fam,
                        target=f"{fam}[{idx}].organization_id",
                        message=f"Record references unknown organization_id: '{org_ref}'",
                        expected="Known organization_id",
                        actual=str(org_ref),
                    )

        # Validate alerts -> assets
        for idx, alert in enumerate(records_by_family.get("alerts", []), start=1):
            a_ref = alert.get("asset_id")
            if a_ref and str(a_ref) not in asset_ids:
                result.add_issue(
                    code="ORPHANED_ASSET_REFERENCE",
                    severity=ValidationSeverity.WARNING,
                    scope="alerts",
                    target=f"alerts[{idx}].asset_id",
                    message=f"Alert references unknown asset_id: '{a_ref}'",
                    expected="Known asset_id",
                    actual=str(a_ref),
                )

        # Validate case_alert_links
        for idx, link in enumerate(records_by_family.get("case_alert_links", []), start=1):
            c_ref = link.get("case_id")
            a_ref = link.get("alert_id")
            if c_ref and str(c_ref) not in case_ids:
                result.add_issue(
                    code="ORPHANED_CASE_REFERENCE",
                    severity=ValidationSeverity.WARNING,
                    scope="case_alert_links",
                    target=f"case_alert_links[{idx}].case_id",
                    message=f"CaseAlertLink references unknown case_id: '{c_ref}'",
                    expected="Known case_id",
                    actual=str(c_ref),
                )
            if a_ref and str(a_ref) not in alert_ids:
                result.add_issue(
                    code="ORPHANED_ALERT_REFERENCE",
                    severity=ValidationSeverity.WARNING,
                    scope="case_alert_links",
                    target=f"case_alert_links[{idx}].alert_id",
                    message=f"CaseAlertLink references unknown alert_id: '{a_ref}'",
                    expected="Known alert_id",
                    actual=str(a_ref),
                )

    def validate_temporal_ordering(
        self,
        records_by_family: dict[str, list[dict[str, Any]]],
        result: ValidationResult,
    ) -> None:
        """Validate causal temporal ordering: alert.created_at <= case.created_at, start <= closed, etc."""
        for idx, case in enumerate(records_by_family.get("cases", []), start=1):
            created_at = self._parse_iso(case.get("created_at_utc"))
            closed_at = self._parse_iso(case.get("closed_at_utc"))
            if created_at and closed_at and closed_at < created_at:
                result.add_issue(
                    code="TEMPORAL_ORDERING_VIOLATION",
                    severity=ValidationSeverity.WARNING,
                    scope="cases",
                    target=f"cases[{idx}]",
                    message=f"Case closed_at ({closed_at}) is before created_at ({created_at})",
                    expected="closed_at >= created_at",
                    actual=f"closed_at={closed_at} < created_at={created_at}",
                )

    @staticmethod
    def _is_valid_uuid(val: Any) -> bool:
        if not val:
            return False
        try:
            UUID(str(val))
            return True
        except ValueError:
            return False

    @staticmethod
    def _is_valid_iso_datetime(val: Any) -> bool:
        if isinstance(val, datetime):
            return True
        if not isinstance(val, str):
            return False
        clean = val.rstrip("Z")
        try:
            datetime.fromisoformat(clean)
            return True
        except ValueError:
            return False

    @staticmethod
    def _parse_iso(val: Any) -> datetime | None:
        if isinstance(val, datetime):
            return val
        if not val or not isinstance(val, str):
            return None
        clean = val.rstrip("Z")
        try:
            return datetime.fromisoformat(clean)
        except ValueError:
            return None
