"""Line-level source provenance and field observation inspection endpoints."""

from __future__ import annotations

from app.backend.api.deps import get_provenance_service
from app.backend.api.schemas import (
    CanonicalFieldObservationResponse,
    EvidenceProvenanceResponse,
)
from app.backend.services import ProvenanceService
from fastapi import APIRouter, Depends, Query

router = APIRouter(prefix="/lineage", tags=["Lineage & Provenance"])


@router.get("/provenance/{canonical_record_id}", response_model=list[EvidenceProvenanceResponse])
def get_record_provenance(
    canonical_record_id: str,
    evidence_family: str | None = Query(None),
    service: ProvenanceService = Depends(get_provenance_service),
) -> list[EvidenceProvenanceResponse]:
    """Retrieve full source-to-canonical trace for a record (file, row, source field, canonical field)."""
    records = service.get_provenance(canonical_record_id, evidence_family=evidence_family)
    return [
        EvidenceProvenanceResponse(
            provenance_id=p.provenance_id,
            canonical_record_id=p.canonical_record_id,
            evidence_family=p.evidence_family,
            organization_id=p.organization_id,
            submission_id=p.submission_id,
            source_file=p.source_file,
            source_record_locator=p.source_record_locator,
            source_field=p.source_field,
            raw_source_value=p.raw_source_value,
            canonical_field=p.canonical_field,
            relationship_name=p.relationship_name,
            target_canonical_id=p.target_canonical_id,
        )
        for p in records
    ]


@router.get("/observations/{canonical_record_id}", response_model=list[CanonicalFieldObservationResponse])
def get_record_observations(
    canonical_record_id: str,
    service: ProvenanceService = Depends(get_provenance_service),
) -> list[CanonicalFieldObservationResponse]:
    """Retrieve semantic field observations and controlled value states (§4.1) for a record."""
    records = service.get_observations(canonical_record_id)
    return [
        CanonicalFieldObservationResponse(
            observation_id=o.observation_id,
            canonical_record_id=o.canonical_record_id,
            evidence_family=o.evidence_family,
            field_name=o.field_name,
            value_state=o.value_state,
            raw_value=o.raw_value,
            normalized_value=o.normalized_value,
            quality_issue=o.quality_issue,
        )
        for o in records
    ]
