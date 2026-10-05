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

from app.backend.domain.types import IngestionStatus, ValidationSeverity
from app.backend.errors import (
    InvalidPackageError,
    PackageValidationFailureError,
)
from app.backend.ingestion.normalizer import EvidenceNormalizer
from app.backend.ingestion.reader import EvidenceFileReader
from app.backend.logging import get_logger
from app.backend.persistence.database import get_db_session
from app.backend.persistence.models import (
    EvidenceProvenanceModel,
    IngestionPackageModel,
)
from app.backend.persistence.repositories import (
    EvidenceRepository,
    OrganizationRepository,
    PackageRepository,
    ProvenanceRepository,
    SubmissionRepository,
)
from app.backend.security import validate_path_traversal
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

    def __init__(
        self,
        base_dir: Path | None = None,
        max_file_size_bytes: int = 100 * 1024 * 1024,
    ) -> None:
        self.base_dir = base_dir
        self.reader = EvidenceFileReader(max_file_size_bytes=max_file_size_bytes)
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

        # 1. Path & Traversal Validation
        pkg_path = validate_path_traversal(pkg_path, self.base_dir) if self.base_dir else pkg_path.resolve()

        if not pkg_path.exists():
            raise InvalidPackageError(f"Evidence package path does not exist: {pkg_path}")

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

            # Ingest rich ground truth provenance if present in package
            self._ingest_ground_truth_provenance(pkg_path, prov_repo)

            # Persist generated field observations and provenance
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

    def _read_all_evidence_files(
        self,
        evidence_dir: Path,
    ) -> tuple[dict[str, list[dict[str, Any]]], dict[str, str]]:
        """Read all canonical json files present in evidence directory."""
        records: dict[str, list[dict[str, Any]]] = {}
        files_map: dict[str, str] = {}

        for family in ALL_EVIDENCE_FAMILIES:
            target_file = evidence_dir / f"{family}.json"
            if target_file.exists():
                data = self.reader.read_json(target_file)
                if isinstance(data, list):
                    records[family] = data
                    files_map[family] = target_file.name
                elif isinstance(data, dict):
                    records[family] = [data]
                    files_map[family] = target_file.name

        return records, files_map

    def _ingest_ground_truth_provenance(self, pkg_path: Path, prov_repo: ProvenanceRepository) -> None:
        """If package contains private_ground_truth/canonical_reference/*_provenance.json, ingest it."""
        ref_dir = pkg_path / "private_ground_truth" / "canonical_reference"
        if not ref_dir.is_dir():
            return

        for p_file in ref_dir.glob("*_provenance.json"):
            try:
                data = self.reader.read_json(p_file)
                if not isinstance(data, dict):
                    continue
                field_provs = data.get("field_provenance", [])
                rel_provs = data.get("relationship_provenance", [])
                extra_models: list[EvidenceProvenanceModel] = []

                for item in field_provs:
                    rec_id = item.get("canonical_record_id")
                    if not rec_id:
                        continue
                    extra_models.append(
                        EvidenceProvenanceModel(
                            provenance_id=str(uuid.uuid4()),
                            canonical_record_id=str(rec_id),
                            evidence_family="ground_truth_field",
                            organization_id="UNKNOWN",
                            submission_id=None,
                            source_file=item.get("source_file_path", p_file.name),
                            source_record_locator=item.get("source_record_locator", "unknown"),
                            source_field=item.get("source_field_name", "unknown"),
                            raw_source_value=str(item.get("raw_value")) if item.get("raw_value") is not None else None,
                            canonical_field=item.get("canonical_field_name", "unknown"),
                            relationship_name=None,
                            target_canonical_id=None,
                        )
                    )

                for item in rel_provs:
                    subj_id = item.get("canonical_subject_id")
                    obj_id = item.get("canonical_object_id")
                    if not subj_id:
                        continue
                    extra_models.append(
                        EvidenceProvenanceModel(
                            provenance_id=str(uuid.uuid4()),
                            canonical_record_id=str(subj_id),
                            evidence_family="ground_truth_relationship",
                            organization_id="UNKNOWN",
                            submission_id=None,
                            source_file=item.get("source_file_path", p_file.name),
                            source_record_locator=item.get("source_record_locator", "unknown"),
                            source_field=item.get("source_relationship_field", "unknown"),
                            raw_source_value=str(obj_id) if obj_id else None,
                            canonical_field=item.get("relationship_type", "relationship"),
                            relationship_name=item.get("relationship_type"),
                            target_canonical_id=str(obj_id) if obj_id else None,
                        )
                    )

                prov_repo.bulk_create_provenance(extra_models)
                logger.info("Ingested %d ground truth provenance records from %s", len(extra_models), p_file.name)
            except Exception as err:
                logger.warning("Could not ingest ground truth provenance from %s: %s", p_file.name, err)

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
