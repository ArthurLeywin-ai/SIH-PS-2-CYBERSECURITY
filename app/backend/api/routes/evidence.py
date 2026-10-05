"""Operational evidence inspection endpoints (Alerts, Cases, Assets, Coverage)."""

from __future__ import annotations

from app.backend.api.deps import get_evidence_service
from app.backend.api.schemas import (
    ActionResponse,
    AlertResponse,
    AssetResponse,
    CaseAlertLinkResponse,
    CaseDetailResponse,
    CaseSummaryResponse,
    ClosureResponse,
    EscalationResponse,
    InvestigationResponse,
    MonitoringCoverageResponse,
    ResolutionResponse,
)
from app.backend.services import EvidenceService
from fastapi import APIRouter, Depends, Query

router = APIRouter(prefix="/evidence", tags=["Operational Evidence"])


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------


@router.get("/alerts", response_model=list[AlertResponse])
def list_alerts(
    organization_id: str | None = Query(None),
    severity: str | None = Query(None),
    category: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    service: EvidenceService = Depends(get_evidence_service),
) -> list[AlertResponse]:
    """Query canonical alerts with multi-dimensional filtering."""
    alerts = service.list_alerts(
        organization_id=organization_id,
        severity=severity,
        category=category,
        status=status,
        limit=limit,
        offset=offset,
    )
    return [
        AlertResponse(
            alert_id=a.alert_id,
            source_alert_id=a.source_alert_id,
            organization_id=a.organization_id,
            asset_id=a.asset_id,
            alert_category=a.alert_category,
            severity=a.severity,
            status=a.status,
            disposition=a.disposition,
            rule_identifier=a.rule_identifier,
            summary=a.summary,
            created_at_utc=a.created_at_utc,
            ingested_at_utc=a.ingested_at_utc,
        )
        for a in alerts
    ]


@router.get("/alerts/{alert_id}", response_model=AlertResponse)
def get_alert(
    alert_id: str,
    service: EvidenceService = Depends(get_evidence_service),
) -> AlertResponse:
    """Retrieve canonical alert details."""
    a = service.get_alert(alert_id)
    return AlertResponse(
        alert_id=a.alert_id,
        source_alert_id=a.source_alert_id,
        organization_id=a.organization_id,
        asset_id=a.asset_id,
        alert_category=a.alert_category,
        severity=a.severity,
        status=a.status,
        disposition=a.disposition,
        rule_identifier=a.rule_identifier,
        summary=a.summary,
        created_at_utc=a.created_at_utc,
        ingested_at_utc=a.ingested_at_utc,
    )


# ---------------------------------------------------------------------------
# Cases & Incident Lifecycle
# ---------------------------------------------------------------------------


@router.get("/cases", response_model=list[CaseSummaryResponse])
def list_cases(
    organization_id: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    service: EvidenceService = Depends(get_evidence_service),
) -> list[CaseSummaryResponse]:
    """Query canonical cases with status and organization filters."""
    cases = service.list_cases(organization_id=organization_id, status=status, limit=limit, offset=offset)
    return [
        CaseSummaryResponse(
            case_id=c.case_id,
            source_case_id=c.source_case_id,
            organization_id=c.organization_id,
            case_type=c.case_type,
            severity=c.severity,
            priority=c.priority,
            status=c.status,
            disposition=c.disposition,
            created_at_utc=c.created_at_utc,
            assigned_at_utc=c.assigned_at_utc,
            started_at_utc=c.started_at_utc,
            resolved_at_utc=c.resolved_at_utc,
            closed_at_utc=c.closed_at_utc,
            primary_assignee=c.primary_assignee,
        )
        for c in cases
    ]


@router.get("/cases/{case_id}", response_model=CaseDetailResponse)
def get_case_detail(
    case_id: str,
    service: EvidenceService = Depends(get_evidence_service),
) -> CaseDetailResponse:
    """Retrieve full case context: linked alerts, investigations, escalations, actions, resolutions, closures."""
    c = service.get_case(case_id)
    return CaseDetailResponse(
        case_id=c.case_id,
        source_case_id=c.source_case_id,
        organization_id=c.organization_id,
        case_type=c.case_type,
        severity=c.severity,
        priority=c.priority,
        status=c.status,
        disposition=c.disposition,
        created_at_utc=c.created_at_utc,
        assigned_at_utc=c.assigned_at_utc,
        started_at_utc=c.started_at_utc,
        resolved_at_utc=c.resolved_at_utc,
        closed_at_utc=c.closed_at_utc,
        primary_assignee=c.primary_assignee,
        alert_links=[
            CaseAlertLinkResponse(
                case_alert_link_id=lnk.case_alert_link_id,
                case_id=lnk.case_id,
                alert_id=lnk.alert_id,
                link_type=lnk.link_type,
                linked_at_utc=lnk.linked_at_utc,
            )
            for lnk in (c.alert_links or [])
        ],
        investigations=[
            InvestigationResponse(
                investigation_id=i.investigation_id,
                organization_id=i.organization_id,
                case_id=i.case_id,
                alert_id=i.alert_id,
                started_at_utc=i.started_at_utc,
                completed_at_utc=i.completed_at_utc,
                analyst_id=i.analyst_id,
                disposition=i.disposition,
                summary=i.summary,
                notes=i.notes,
            )
            for i in (c.investigations or [])
        ],
        escalations=[
            EscalationResponse(
                escalation_id=e.escalation_id,
                organization_id=e.organization_id,
                case_id=e.case_id,
                alert_id=e.alert_id,
                escalated_at_utc=e.escalated_at_utc,
                escalated_from_tier=e.escalated_from_tier,
                escalated_to_tier=e.escalated_to_tier,
                reason=e.reason,
                approved_by=e.approved_by,
            )
            for e in (c.escalations or [])
        ],
        actions=[
            ActionResponse(
                action_id=act.action_id,
                organization_id=act.organization_id,
                case_id=act.case_id,
                alert_id=act.alert_id,
                asset_id=act.asset_id,
                action_type=act.action_type,
                status=act.status,
                created_at_utc=act.created_at_utc,
                completed_at_utc=act.completed_at_utc,
                assigned_to=act.assigned_to,
                summary=act.summary,
            )
            for act in (c.actions or [])
        ],
        resolutions=[
            ResolutionResponse(
                resolution_id=r.resolution_id,
                organization_id=r.organization_id,
                case_id=r.case_id,
                alert_id=r.alert_id,
                resolved_at_utc=r.resolved_at_utc,
                resolution_type=r.resolution_type,
                summary=r.summary,
                accepted_by=r.accepted_by,
            )
            for r in (c.resolutions or [])
        ],
        closures=[
            ClosureResponse(
                closure_id=clo.closure_id,
                organization_id=clo.organization_id,
                case_id=clo.case_id,
                alert_id=clo.alert_id,
                resolution_id=clo.resolution_id,
                closed_at_utc=clo.closed_at_utc,
                closure_status=clo.closure_status,
                disposition=clo.disposition,
                approved_by=clo.approved_by,
                summary=clo.summary,
            )
            for clo in (c.closures or [])
        ],
    )


# ---------------------------------------------------------------------------
# Assets & Coverage
# ---------------------------------------------------------------------------


@router.get("/assets", response_model=list[AssetResponse])
def list_assets(
    organization_id: str = Query(..., description="Organization identifier"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    service: EvidenceService = Depends(get_evidence_service),
) -> list[AssetResponse]:
    """Query declared enterprise assets for an organization."""
    assets = service.list_assets(organization_id, limit=limit, offset=offset)
    return [
        AssetResponse(
            asset_id=a.asset_id,
            source_asset_id=a.source_asset_id,
            organization_id=a.organization_id,
            asset_class=a.asset_class,
            criticality=a.criticality,
            operating_status=a.operating_status,
            effective_start_at_utc=a.effective_start_at_utc,
            effective_end_at_utc=a.effective_end_at_utc,
        )
        for a in assets
    ]


@router.get("/coverage", response_model=list[MonitoringCoverageResponse])
def list_coverages(
    organization_id: str = Query(..., description="Organization identifier"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    service: EvidenceService = Depends(get_evidence_service),
) -> list[MonitoringCoverageResponse]:
    """Query telemetry and monitoring coverage declarations."""
    coverages = service.list_coverages(organization_id, limit=limit, offset=offset)
    return [
        MonitoringCoverageResponse(
            monitoring_coverage_id=c.monitoring_coverage_id,
            organization_id=c.organization_id,
            asset_id=c.asset_id,
            monitoring_type=c.monitoring_type,
            coverage_state=c.coverage_state,
            coverage_percentage=c.coverage_percentage,
            effective_start_at_utc=c.effective_start_at_utc,
            effective_end_at_utc=c.effective_end_at_utc,
        )
        for c in coverages
    ]
