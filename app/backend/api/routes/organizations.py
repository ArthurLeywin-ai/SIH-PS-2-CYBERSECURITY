"""Organization discovery and profile query endpoints."""

from __future__ import annotations

from app.backend.api.deps import get_organization_service, get_submission_service
from app.backend.api.schemas import (
    OrganizationResponse,
    SubmissionEvidenceFamilyResponse,
    SubmissionManifestResponse,
    SubmissionResponse,
)
from app.backend.services import OrganizationService, SubmissionService
from fastapi import APIRouter, Depends, Query

router = APIRouter(prefix="/organizations", tags=["Regulated Entities & Organizations"])


@router.get("", response_model=list[OrganizationResponse])
def list_organizations(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    service: OrganizationService = Depends(get_organization_service),
) -> list[OrganizationResponse]:
    """List regulated organizations present in canonical storage."""
    orgs = service.list_organizations(limit=limit, offset=offset)
    return [
        OrganizationResponse(
            organization_id=o.organization_id,
            source_organization_id=o.source_organization_id,
            organization_name=o.organization_name,
            organization_alias=o.organization_alias,
            sector_code=o.sector_code,
            subsector_code=o.subsector_code,
            scale_band=o.scale_band,
            operating_model=o.operating_model,
            entity_criticality_band=o.entity_criticality_band,
            asset_count_declared=o.asset_count_declared,
            critical_asset_count_declared=o.critical_asset_count_declared,
            default_timezone=o.default_timezone,
            organization_status=o.organization_status,
            profile_effective_start_at_utc=o.profile_effective_start_at_utc,
            profile_effective_end_at_utc=o.profile_effective_end_at_utc,
        )
        for o in orgs
    ]


@router.get("/{organization_id}", response_model=OrganizationResponse)
def get_organization(
    organization_id: str,
    service: OrganizationService = Depends(get_organization_service),
) -> OrganizationResponse:
    """Retrieve detailed metadata for an organization."""
    o = service.get_organization(organization_id)
    return OrganizationResponse(
        organization_id=o.organization_id,
        source_organization_id=o.source_organization_id,
        organization_name=o.organization_name,
        organization_alias=o.organization_alias,
        sector_code=o.sector_code,
        subsector_code=o.subsector_code,
        scale_band=o.scale_band,
        operating_model=o.operating_model,
        entity_criticality_band=o.entity_criticality_band,
        asset_count_declared=o.asset_count_declared,
        critical_asset_count_declared=o.critical_asset_count_declared,
        default_timezone=o.default_timezone,
        organization_status=o.organization_status,
        profile_effective_start_at_utc=o.profile_effective_start_at_utc,
        profile_effective_end_at_utc=o.profile_effective_end_at_utc,
    )


@router.get("/{organization_id}/submissions", response_model=list[SubmissionResponse])
def list_organization_submissions(
    organization_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sub_service: SubmissionService = Depends(get_submission_service),
) -> list[SubmissionResponse]:
    """List historical submissions and reporting periods for an organization."""
    subs = sub_service.list_by_organization(organization_id, limit=limit, offset=offset)
    return [
        SubmissionResponse(
            submission_id=s.submission_id,
            source_submission_id=s.source_submission_id,
            organization_id=s.organization_id,
            reporting_period_id=s.reporting_period_id,
            period_maturity_state=s.period_maturity_state,
            reporting_period_start_at_utc=s.reporting_period_start_at_utc,
            reporting_period_end_at_utc=s.reporting_period_end_at_utc,
            submitted_at_utc=s.submitted_at_utc,
            manifests=[
                SubmissionManifestResponse(
                    manifest_id=m.manifest_id,
                    submission_id=m.submission_id,
                    schema_version=m.schema_version,
                    dataset_version=m.dataset_version,
                    generator_version=m.generator_version,
                    tree_sha256=m.tree_sha256,
                    declared_record_counts=m.declared_record_counts or {},
                    created_at_utc=m.created_at_utc,
                )
                for m in (s.manifests or [])
            ],
            families=[
                SubmissionEvidenceFamilyResponse(
                    submission_family_id=f.submission_family_id,
                    evidence_family=f.evidence_family,
                    presence_state=f.presence_state,
                    declared_record_count=f.declared_record_count,
                )
                for f in (s.families or [])
            ],
        )
        for s in subs
    ]
