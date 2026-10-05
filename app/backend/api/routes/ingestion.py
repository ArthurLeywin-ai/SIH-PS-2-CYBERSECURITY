"""Package ingestion and validation endpoints."""

from __future__ import annotations

from typing import Any

from app.backend.api.deps import get_package_service
from app.backend.api.schemas import (
    IngestionPackageDetailResponse,
    IngestionPackageResponse,
    IngestPackageRequest,
    ValidationIssueSchema,
)
from app.backend.services import PackageService
from fastapi import APIRouter, Depends, Query, status

router = APIRouter(prefix="/packages", tags=["Evidence Ingestion & Packages"])


@router.post("/ingest", response_model=IngestionPackageResponse, status_code=status.HTTP_201_CREATED)
def ingest_package(
    req: IngestPackageRequest,
    service: PackageService = Depends(get_package_service),
) -> Any:
    """Trigger ingestion and validation for an evidence package."""
    result = service.ingest(req.package_path, fail_on_error=req.fail_on_error)
    pkg = service.get_package(result.package_id)
    return IngestionPackageResponse(
        package_id=pkg.package_id,
        package_path=pkg.package_path,
        package_name=pkg.package_name,
        tier=pkg.tier,
        split=pkg.split,
        status=pkg.status,
        manifest_hash=pkg.manifest_hash,
        tree_hash=pkg.tree_hash,
        record_counts=pkg.record_counts or {},
        validation_issues_count=len(pkg.validation_issues or []),
        discovered_at_utc=pkg.discovered_at_utc,
        completed_at_utc=pkg.completed_at_utc,
    )


@router.get("", response_model=list[IngestionPackageResponse])
def list_packages(
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: PackageService = Depends(get_package_service),
) -> list[IngestionPackageResponse]:
    """List all ingested and discovered packages."""
    packages = service.list_packages(status=status_filter, limit=limit, offset=offset)
    return [
        IngestionPackageResponse(
            package_id=pkg.package_id,
            package_path=pkg.package_path,
            package_name=pkg.package_name,
            tier=pkg.tier,
            split=pkg.split,
            status=pkg.status,
            manifest_hash=pkg.manifest_hash,
            tree_hash=pkg.tree_hash,
            record_counts=pkg.record_counts or {},
            validation_issues_count=len(pkg.validation_issues or []),
            discovered_at_utc=pkg.discovered_at_utc,
            completed_at_utc=pkg.completed_at_utc,
        )
        for pkg in packages
    ]


@router.get("/{package_id}", response_model=IngestionPackageDetailResponse)
def get_package(
    package_id: str,
    service: PackageService = Depends(get_package_service),
) -> IngestionPackageDetailResponse:
    """Retrieve full package details and validation issues."""
    pkg = service.get_package(package_id)
    return IngestionPackageDetailResponse(
        package_id=pkg.package_id,
        package_path=pkg.package_path,
        package_name=pkg.package_name,
        tier=pkg.tier,
        split=pkg.split,
        status=pkg.status,
        manifest_hash=pkg.manifest_hash,
        tree_hash=pkg.tree_hash,
        record_counts=pkg.record_counts or {},
        validation_issues_count=len(pkg.validation_issues or []),
        validation_issues=[
            ValidationIssueSchema(
                code=iss["code"],
                severity=iss["severity"],
                scope=iss["scope"],
                target=iss["target"],
                message=iss["message"],
                expected=iss.get("expected"),
                actual=iss.get("actual"),
            )
            for iss in (pkg.validation_issues or [])
        ],
        discovered_at_utc=pkg.discovered_at_utc,
        completed_at_utc=pkg.completed_at_utc,
    )


@router.get("/{package_id}/validation", response_model=list[ValidationIssueSchema])
def get_package_validation(
    package_id: str,
    service: PackageService = Depends(get_package_service),
) -> list[ValidationIssueSchema]:
    """Retrieve structured validation findings for a package."""
    pkg = service.get_package(package_id)
    return [
        ValidationIssueSchema(
            code=iss["code"],
            severity=iss["severity"],
            scope=iss["scope"],
            target=iss["target"],
            message=iss["message"],
            expected=iss.get("expected"),
            actual=iss.get("actual"),
        )
        for iss in (pkg.validation_issues or [])
    ]
