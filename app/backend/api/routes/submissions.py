"""Direct submission inspection endpoints."""

from __future__ import annotations

from app.backend.api.deps import get_submission_service
from app.backend.api.schemas import (
    SubmissionEvidenceFamilyResponse,
    SubmissionManifestResponse,
    SubmissionResponse,
)
from app.backend.services import SubmissionService
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/submissions", tags=["Submissions"])


@router.get("/{submission_id}", response_model=SubmissionResponse)
def get_submission(
    submission_id: str,
    service: SubmissionService = Depends(get_submission_service),
) -> SubmissionResponse:
    """Retrieve detailed submission metadata, manifest, and family declaration."""
    s = service.get_submission(submission_id)
    return SubmissionResponse(
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
