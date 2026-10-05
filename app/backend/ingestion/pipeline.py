"""End-to-end evidence ingestion pipeline.

Orchestrates:
Package Discovery -> Security Validation -> Manifest Inspection -> File & Schema Validation
-> Parsing -> Canonical Normalization -> Provenance Attachment -> Transactional Persistence.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.backend.config import get_config
from app.backend.domain.types import IngestionStatus, ValidationSeverity
from app.backend.errors import (
    InvalidPackageError,
    PackageValidationFailureError,
    SecurityViolationError,
)
from app.backend.ingestion.normalizer import EvidenceNormalizer
from app.backend.ingestion.reader import EvidenceFileReader
from app.backend.logging import get_logger
from app.backend.persistence.database import get_db_session
from app.backend.persistence.models import (
    IngestionPackageModel,
)
from app.backend.persistence.repositories import (
    EvidenceRepository,
    OrganizationRepository,
    PackageRepository,
    ProvenanceRepository,
    SubmissionRepository,
)
from app.backend.security import SecurityError, validate_package_safety
from app.backend.validation.validator import (
    ALL_EVIDENCE_FAMILIES,
    EvidencePackageValidator,
    ValidationResult,
)
from sqlalchemy.orm import Session

logger = get_logger("ingestion.pipeline")


@dataclass
class IngestionResult:
    """Outcome of an ingestion run."""

    package_id: str
    package_path: str
    status: IngestionStatus
    record_counts: dict[str, int] = field(default_factory=dict)
    issues: list[dict[str, Any]] = field(default_factory=list)
    manifest_hash: str | None = None
    tree_hash: str | None = None
    duration_seconds: float = 0.0


class IngestionPipeline:
    """Production ingestion pipeline for SAT-SA evidence packages."""

    FAMILY_FILE_CANDIDATES: dict[str, list[str]] = {
        "organizations": ["organizations", "organization"],
        "submissions": ["submissions", "submission"],
        "submission_manifests": ["submission_manifests", "submission_manifest", "manifests", "manifest"],
        "submission_evidence_families": [
            "submission_evidence_families",
            "submission_evidence_family",
            "submission_families",
            "submission_family",
        ],
        "control_process_references": ["control_process_references", "control_process_reference"],
        "control_process_subject_links": ["control_process_subject_links", "control_process_subject_link"],
        "assets": ["assets", "asset"],
        "monitoring_coverage": ["monitoring_coverage", "coverage"],
        "alerts": ["alerts", "alert"],
        "cases": ["cases", "case"],
        "case_alert_links": ["case_alert_links", "case_alert_link"],
        "investigations": ["investigations", "investigation"],
        "escalations": ["escalations", "escalation"],
        "actions": ["actions", "action"],
        "resolutions": ["resolutions", "resolution"],
        "closures": ["closures", "closure"],
        "exceptions": ["exceptions", "exception"],
        "process_changes": ["process_changes", "process_change"],
    }

    def __init__(
        self,
        base_dir: Path | None = None,
        max_file_size_bytes: int | None = None,
        max_package_size_bytes: int | None = None,
    ) -> None:
        cfg = get_config()
        self.base_dir = base_dir if base_dir is not None else cfg.evidence_dir
        self.max_file_size_bytes = max_file_size_bytes or cfg.max_file_size_bytes
        self.max_package_size_bytes = max_package_size_bytes or cfg.max_package_size_bytes
        self.reader = EvidenceFileReader(max_file_size_bytes=self.max_file_size_bytes)
        self.validator = EvidencePackageValidator()

    def run(
        self,
        package_input: str | Path,
        db_session: Session | None = None,
        fail_on_error: bool = True,
    ) -> IngestionResult:
        """Execute complete ingestion pipeline for a given package path."""
        start_time = time.perf_counter()
        pkg_path = Path(package_input)

        # 1. Path, Traversal, Symlink, and Package-Size Safety Validation
        try:
            pkg_path = validate_package_safety(
                pkg_path,
                base_dir=self.base_dir,
                max_package_size_bytes=self.max_package_size_bytes,
            )
        except SecurityError as err:
            logger.warning("Security violation for package '%s': %s", package_input, err)
            raise SecurityViolationError(str(err)) from err

        if not pkg_path.exists():
            raise InvalidPackageError(f"Evidence package path does not exist: {pkg_path}")

        if not pkg_path.is_dir():
            raise InvalidPackageError(f"Evidence package path must be a directory: {pkg_path}")

        # 2. Package Discovery: locate operational evidence folder
        evidence_dir = pkg_path
        if (pkg_path / "operational_evidence").is_dir():
            evidence_dir = pkg_path / "operational_evidence"

        package_id = str(uuid.uuid4())
        package_name = pkg_path.name
        logger.info("Starting ingestion for package '%s' (ID: %s)", package_name, package_id)

        # Determine manifest if available
        manifest_data = self._load_manifest(evidence_dir)
        manifest_hash = self._compute_manifest_hash(evidence_dir)
        tree_hash = self._compute_tree_hash(evidence_dir)

        # 3. Read Raw Records from Evidence Files
        records_by_family, found_files = self._read_all_evidence_files(evidence_dir)

        # 4. Validation
        val_result = ValidationResult()
        if manifest_data:
            self.validator.validate_manifest_integrity(evidence_dir, manifest_data, val_result)

        self.validator.validate_file_presence(set(records_by_family.keys()), val_result)

        for family, recs in records_by_family.items():
            self.validator.validate_record_schema(family, recs, val_result)

        self.validator.validate_referential_integrity(records_by_family, val_result)
        self.validator.validate_temporal_ordering(records_by_family, val_result)

        has_errors = any(i.severity == ValidationSeverity.ERROR for i in val_result.issues)

        # 5. Persistence Session
        if db_session:
            return self._persist_and_finalize(
                session=db_session,
                package_id=package_id,
                package_path=str(pkg_path),
                package_name=package_name,
                records_by_family=records_by_family,
                found_files=found_files,
                pkg_path=pkg_path,
                val_result=val_result,
                manifest_hash=manifest_hash,
                tree_hash=tree_hash,
                start_time=start_time,
                has_errors=has_errors,
                fail_on_error=fail_on_error,
            )
        else:
            with get_db_session() as session:
                return self._persist_and_finalize(
                    session=session,
                    package_id=package_id,
                    package_path=str(pkg_path),
                    package_name=package_name,
                    records_by_family=records_by_family,
                    found_files=found_files,
                    pkg_path=pkg_path,
                    val_result=val_result,
                    manifest_hash=manifest_hash,
                    tree_hash=tree_hash,
                    start_time=start_time,
                    has_errors=has_errors,
                    fail_on_error=fail_on_error,
                )

    def _persist_and_finalize(
        self,
        session: Session,
        package_id: str,
        package_path: str,
        package_name: str,
        records_by_family: dict[str, list[dict[str, Any]]],
        found_files: dict[str, str],
        pkg_path: Path,
        val_result: ValidationResult,
        manifest_hash: str | None,
        tree_hash: str | None,
        start_time: float,
        has_errors: bool,
        fail_on_error: bool,
    ) -> IngestionResult:
        pkg_repo = PackageRepository(session)
        counts = {family: len(recs) for family, recs in records_by_family.items()}

        package_model = IngestionPackageModel(
            package_id=package_id,
            package_path=package_path,
            package_name=package_name,
            tier="deterministic_fixture",
            split="development",
            status=IngestionStatus.FAILED.value if has_errors else IngestionStatus.INGESTED.value,
            manifest_hash=manifest_hash,
            tree_hash=tree_hash,
            record_counts=counts,
            validation_issues=val_result.to_dict_list(),
            discovered_at_utc=datetime.now(UTC),
            completed_at_utc=datetime.now(UTC),
        )
        pkg_repo.create(package_model)

        if has_errors and fail_on_error:
            session.commit()
            duration = time.perf_counter() - start_time
            logger.error("Ingestion failed for package %s with %d errors", package_name, len(val_result.issues))
            raise PackageValidationFailureError(
                f"Package '{package_name}' failed validation",
                details=val_result.to_dict_list(),
            )

        if not has_errors:
            # 6. Canonical Normalization
            normalizer = EvidenceNormalizer()
            normalized_by_family: dict[str, list[Any]] = {}

            # Strict dependency ordering
            for family in ALL_EVIDENCE_FAMILIES:
                recs = records_by_family.get(family, [])
                if recs:
                    source_file = found_files.get(family, f"{family}.json")
                    normalized_models = normalizer.normalize_all(family, recs, source_file)
                    normalized_by_family[family] = normalized_models

            # 7. Relational Persistence
            org_repo = OrganizationRepository(session)
            sub_repo = SubmissionRepository(session)
            ev_repo = EvidenceRepository(session)
            prov_repo = ProvenanceRepository(session)

            if "organizations" in normalized_by_family:
                org_repo.bulk_create(normalized_by_family["organizations"])
            if "submissions" in normalized_by_family:
                sub_repo.bulk_create(normalized_by_family["submissions"])
            if "submission_manifests" in normalized_by_family:
                ev_repo.bulk_insert(normalized_by_family["submission_manifests"])
            if "submission_evidence_families" in normalized_by_family:
                sub_repo.bulk_create_evidence_families(normalized_by_family["submission_evidence_families"])

            for family in ALL_EVIDENCE_FAMILIES:
                if family in {"organizations", "submissions", "submission_manifests", "submission_evidence_families"}:
                    continue
                if family in normalized_by_family:
                    ev_repo.bulk_insert(normalized_by_family[family])

            # Persist generated field observations and provenance from operational evidence
            prov_repo.bulk_create_provenance(normalizer.provenance_records)
            prov_repo.bulk_create_observations(normalizer.observations)

        session.commit()
        duration = round(time.perf_counter() - start_time, 4)
        logger.info(
            "Ingestion completed for package %s: status=%s, records=%d in %.2fs",
            package_name,
            package_model.status,
            sum(counts.values()),
            duration,
        )

        return IngestionResult(
            package_id=package_id,
            package_path=package_path,
            status=IngestionStatus(package_model.status),
            record_counts=counts,
            issues=val_result.to_dict_list(),
            manifest_hash=manifest_hash,
            tree_hash=tree_hash,
            duration_seconds=duration,
        )

    @staticmethod
    def _clean_csv_row(row: dict[str, str]) -> dict[str, Any]:
        """Normalize empty string CSV cells to None for schema consistency."""
        cleaned: dict[str, Any] = {}
        for k, v in row.items():
            if k is None:
                continue
            clean_k = k.strip()
            if v is None:
                cleaned[clean_k] = None
            elif isinstance(v, str):
                clean_v = v.strip()
                if clean_v == "" or clean_v.upper() in {"NULL", "NONE"}:
                    cleaned[clean_k] = None
                else:
                    cleaned[clean_k] = clean_v
            else:
                cleaned[clean_k] = v
        return cleaned

    def _read_all_evidence_files(
        self,
        evidence_dir: Path,
    ) -> tuple[dict[str, list[dict[str, Any]]], dict[str, str]]:
        """Discover and read evidence files for all canonical families across .json, .jsonl, and .csv formats."""
        records: dict[str, list[dict[str, Any]]] = {}
        files_map: dict[str, str] = {}

        for family in ALL_EVIDENCE_FAMILIES:
            candidates = self.FAMILY_FILE_CANDIDATES.get(family, [family])
            matched = False
            for base_name in candidates:
                if matched:
                    break
                for ext in (".json", ".jsonl", ".csv"):
                    target_file = evidence_dir / f"{base_name}{ext}"
                    if target_file.exists() and target_file.is_file():
                        if ext == ".json":
                            data = self.reader.read_json(target_file)
                            recs = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
                        elif ext == ".jsonl":
                            recs = [rec for _, rec in self.reader.read_jsonl(target_file)]
                        elif ext == ".csv":
                            raw_csv = [rec for _, rec in self.reader.read_csv(target_file)]
                            recs = [self._clean_csv_row(r) for r in raw_csv]
                        records[family] = recs
                        files_map[family] = target_file.name
                        matched = True
                        break

        return records, files_map

    def _load_manifest(self, evidence_dir: Path) -> dict[str, Any] | None:
        for name in ["fixture_manifest.json", "manifest.json", "submission_manifest.json"]:
            m_path = evidence_dir / name
            if m_path.exists():
                data = self.reader.read_json(m_path)
                if isinstance(data, dict):
                    return data
        return None

    def _compute_manifest_hash(self, evidence_dir: Path) -> str | None:
        for name in ["fixture_manifest.json", "manifest.json"]:
            m_path = evidence_dir / name
            if m_path.exists():
                h = hashlib.sha256()
                with open(m_path, "rb") as f:
                    for chunk in iter(lambda: f.read(65536), b""):
                        h.update(chunk)
                return h.hexdigest()
        return None

    def _compute_tree_hash(self, directory: Path) -> str:
        h = hashlib.sha256()
        for p in sorted(directory.rglob("*")):
            if p.is_file():
                h.update(p.relative_to(directory).as_posix().encode("utf-8"))
                with open(p, "rb") as f:
                    for chunk in iter(lambda: f.read(65536), b""):
                        h.update(chunk)
        return h.hexdigest()
