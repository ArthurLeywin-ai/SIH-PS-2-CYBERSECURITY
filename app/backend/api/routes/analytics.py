"""Supervisory Analytics API endpoints.

Exposes:
- POST /analytics/run: Trigger deterministic analytics execution
- GET /analytics/signals: Query detected supervisory signals
- GET /analytics/signals/{signal_id}: Retrieve individual signal details with evidence references
- GET /analytics/organizations/{organization_id}/attention: Retrieve entity attention indicator summary
"""

from __future__ import annotations

from app.backend.api.deps import get_analytics_service
from app.backend.api.schemas import (
    AnalyticsRunRequest,
    AnalyticsRunResponse,
    SupervisoryAttentionSummaryResponse,
    SupervisorySignalResponse,
)
from app.backend.errors import InvalidRequestError
from app.backend.services import AnalyticsService
from fastapi import APIRouter, Depends, Query

router = APIRouter(prefix="/analytics", tags=["Supervisory Analytics & Signals"])


@router.post("/run", response_model=AnalyticsRunResponse)
def run_analytics(
    request: AnalyticsRunRequest,
    service: AnalyticsService = Depends(get_analytics_service),
) -> AnalyticsRunResponse:
    """Execute the deterministic supervisory analytics engine for a submission or organization."""
    if not request.organization_id and not request.submission_id:
        raise InvalidRequestError("Either organization_id or submission_id must be provided to run analytics")

    if request.submission_id:
        result = service.run_submission_analytics(request.submission_id, persist=request.persist)
    else:
        assert request.organization_id is not None
        result = service.run_organization_analytics(request.organization_id, persist=request.persist)

    attn_resp = None
    if result.attention_summary:
        attn = result.attention_summary
        attn_resp = SupervisoryAttentionSummaryResponse(
            summary_id=attn.summary_id,
            organization_id=attn.organization_id,
            submission_id=attn.submission_id,
            total_signals=attn.total_signals,
            signals_by_type=attn.signals_by_type,
            signals_by_severity=attn.signals_by_severity,
            attention_score=attn.attention_score,
            attention_band=attn.attention_band,
            strongest_signal_ids=[s.signal_id for s in attn.strongest_signals],
            data_quality_gap_index=attn.data_quality_gap_index,
            summary_rationale=attn.summary_rationale,
            generated_at_utc=attn.generated_at_utc,
        )

    signals_resp = [
        SupervisorySignalResponse(
            signal_id=s.signal_id,
            organization_id=s.organization_id,
            submission_id=s.submission_id,
            signal_type=s.signal_type.value if hasattr(s.signal_type, "value") else str(s.signal_type),
            severity=s.severity.value if hasattr(s.severity, "value") else str(s.severity),
            title=s.title,
            short_rationale=s.short_rationale,
            detailed_explanation=s.detailed_explanation,
            basis=s.basis,
            observed_value=s.observed_value,
            expected_value=s.expected_value,
            confidence=s.confidence,
            evidence_references=[r.to_dict() for r in s.evidence_references],
            affected_record_ids=s.affected_record_ids,
            detector_id=s.detector_id,
            detector_version=s.detector_version,
            investigation_questions=s.investigation_questions,
            generated_at_utc=s.generated_at_utc,
        )
        for s in result.signals
    ]

    return AnalyticsRunResponse(
        organization_id=result.organization_id,
        submission_id=result.submission_id,
        signals_count=result.signals_count,
        signals=signals_resp,
        attention_summary=attn_resp,
        execution_duration_ms=result.execution_duration_ms,
        generated_at_utc=result.generated_at_utc,
    )


@router.get("/signals", response_model=list[SupervisorySignalResponse])
def list_signals(
    organization_id: str | None = Query(None),
    submission_id: str | None = Query(None),
    signal_type: str | None = Query(None),
    severity: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: AnalyticsService = Depends(get_analytics_service),
) -> list[SupervisorySignalResponse]:
    """Query persisted supervisory signals with deterministic ordering."""
    signals = service.list_signals(
        organization_id=organization_id,
        submission_id=submission_id,
        signal_type=signal_type,
        severity=severity,
        limit=limit,
        offset=offset,
    )
    return [
        SupervisorySignalResponse(
            signal_id=s.signal_id,
            organization_id=s.organization_id,
            submission_id=s.submission_id,
            signal_type=s.signal_type,
            severity=s.severity,
            title=s.title,
            short_rationale=s.short_rationale,
            detailed_explanation=s.detailed_explanation,
            basis=s.basis or {},
            observed_value=s.observed_value,
            expected_value=s.expected_value,
            confidence=s.confidence,
            evidence_references=s.evidence_references or [],
            affected_record_ids=s.affected_record_ids or [],
            detector_id=s.detector_id,
            detector_version=s.detector_version,
            investigation_questions=s.investigation_questions or [],
            generated_at_utc=s.generated_at_utc,
        )
        for s in signals
    ]


@router.get("/signals/{signal_id}", response_model=SupervisorySignalResponse)
def get_signal(
    signal_id: str,
    service: AnalyticsService = Depends(get_analytics_service),
) -> SupervisorySignalResponse:
    """Retrieve full details, explainable rationale, and evidence references for a specific signal."""
    s = service.get_signal(signal_id)
    return SupervisorySignalResponse(
        signal_id=s.signal_id,
        organization_id=s.organization_id,
        submission_id=s.submission_id,
        signal_type=s.signal_type,
        severity=s.severity,
        title=s.title,
        short_rationale=s.short_rationale,
        detailed_explanation=s.detailed_explanation,
        basis=s.basis or {},
        observed_value=s.observed_value,
        expected_value=s.expected_value,
        confidence=s.confidence,
        evidence_references=s.evidence_references or [],
        affected_record_ids=s.affected_record_ids or [],
        detector_id=s.detector_id,
        detector_version=s.detector_version,
        investigation_questions=s.investigation_questions or [],
        generated_at_utc=s.generated_at_utc,
    )


@router.get("/organizations/{organization_id}/attention", response_model=SupervisoryAttentionSummaryResponse)
def get_organization_attention(
    organization_id: str,
    service: AnalyticsService = Depends(get_analytics_service),
) -> SupervisoryAttentionSummaryResponse:
    """Retrieve the latest supervisory attention summary and bounded priority indicator for an entity."""
    attn = service.get_organization_attention(organization_id)
    return SupervisoryAttentionSummaryResponse(
        summary_id=attn.summary_id,
        organization_id=attn.organization_id,
        submission_id=attn.submission_id,
        total_signals=attn.total_signals,
        signals_by_type=attn.signals_by_type or {},
        signals_by_severity=attn.signals_by_severity or {},
        attention_score=attn.attention_score,
        attention_band=attn.attention_band,
        strongest_signal_ids=attn.strongest_signal_ids or [],
        data_quality_gap_index=attn.data_quality_gap_index,
        summary_rationale=attn.summary_rationale,
        generated_at_utc=attn.generated_at_utc,
    )
