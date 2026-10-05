"""Deterministic feature and metric extraction layer for supervisory analytics.

Provides:
- Robust, reproducible feature computation across canonical evidence models
- Pure statistical utilities (Median, MAD, IQR) for explainable anomaly detection
- Stable sorting and deterministic handling of empty, null, or zero-denominator cases
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Any

from app.backend.persistence.models import (
    ActionModel,
    AlertModel,
    AssetModel,
    CaseAlertLinkModel,
    CaseModel,
    ClosureModel,
    EscalationModel,
    InvestigationModel,
    MonitoringCoverageModel,
    ResolutionModel,
    SubmissionEvidenceFamilyModel,
)

# ---------------------------------------------------------------------------
# Pure Statistical Helpers (Deterministic, No External ML Libraries)
# ---------------------------------------------------------------------------


def compute_median(values: list[float | int]) -> float:
    """Compute median deterministically."""
    if not values:
        return 0.0
    sorted_vals = sorted(float(v) for v in values)
    return float(statistics.median(sorted_vals))


def compute_mad(values: list[float | int], scale_to_normal: bool = True) -> float:
    """Compute Median Absolute Deviation (MAD).

    If scale_to_normal is True, multiplies by 1.4826 to approximate normal standard deviation.
    """
    if len(values) < 2:
        return 0.0
    med = compute_median(values)
    abs_deviations = [abs(float(v) - med) for v in values]
    mad = compute_median(abs_deviations)
    return mad * 1.4826 if scale_to_normal else mad


def compute_iqr(values: list[float | int]) -> tuple[float, float, float]:
    """Compute (Q1, Q3, IQR) using linear interpolation."""
    if not values:
        return 0.0, 0.0, 0.0
    sorted_vals = sorted(float(v) for v in values)
    n = len(sorted_vals)
    if n == 1:
        return sorted_vals[0], sorted_vals[0], 0.0

    # Quantiles using standard method
    mid = n // 2
    if n % 2 == 0:
        lower_half = sorted_vals[:mid]
        upper_half = sorted_vals[mid:]
    else:
        lower_half = sorted_vals[:mid]
        upper_half = sorted_vals[mid + 1 :]

    q1 = compute_median(lower_half)
    q3 = compute_median(upper_half)
    return q1, q3, q3 - q1


# ---------------------------------------------------------------------------
# Entity Period Features
# ---------------------------------------------------------------------------


@dataclass
class EntityPeriodFeatures:
    """Comprehensive analytical feature set extracted for an entity during a submission or period."""

    organization_id: str
    submission_id: str | None

    # Population counts
    alert_count: int = 0
    critical_alert_count: int = 0
    high_alert_count: int = 0
    medium_alert_count: int = 0
    low_alert_count: int = 0

    case_count: int = 0
    open_case_count: int = 0
    closed_case_count: int = 0

    investigation_count: int = 0
    escalation_count: int = 0
    action_count: int = 0
    resolution_count: int = 0
    closure_count: int = 0

    asset_count: int = 0
    critical_asset_count: int = 0
    covered_asset_count: int = 0

    # Workflow Rates
    alert_to_case_ratio: float = 0.0
    critical_alert_case_link_rate: float = 0.0
    case_investigation_rate: float = 0.0
    case_closure_rate: float = 0.0
    escalation_rate: float = 0.0
    monitoring_coverage_rate: float = 0.0

    # Durations (in hours)
    investigation_durations_hours: list[float] = field(default_factory=list)
    median_investigation_duration_hours: float = 0.0
    mean_investigation_duration_hours: float = 0.0

    case_lifecycle_durations_hours: list[float] = field(default_factory=list)
    median_case_lifecycle_duration_hours: float = 0.0

    # Workflow link sets
    linked_alert_ids: set[str] = field(default_factory=set)
    unlinked_critical_alert_ids: list[str] = field(default_factory=list)
    cases_with_investigation: set[str] = field(default_factory=set)
    cases_with_escalation: set[str] = field(default_factory=set)
    cases_with_action: set[str] = field(default_factory=set)
    cases_with_resolution: set[str] = field(default_factory=set)
    cases_with_closure: set[str] = field(default_factory=set)

    # Negative-space & schema checks
    declared_family_counts: dict[str, int] = field(default_factory=dict)
    actual_family_counts: dict[str, int] = field(default_factory=dict)
    unmonitored_critical_asset_ids: list[str] = field(default_factory=list)

    # Raw model references for granular inspection
    alerts: list[AlertModel] = field(default_factory=list)
    cases: list[CaseModel] = field(default_factory=list)
    investigations: list[InvestigationModel] = field(default_factory=list)
    escalations: list[EscalationModel] = field(default_factory=list)
    actions: list[ActionModel] = field(default_factory=list)
    resolutions: list[ResolutionModel] = field(default_factory=list)
    closures: list[ClosureModel] = field(default_factory=list)
    assets: list[AssetModel] = field(default_factory=list)
    coverage: list[MonitoringCoverageModel] = field(default_factory=list)
    declared_families: list[SubmissionEvidenceFamilyModel] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert scalar features to a dictionary for API and logging."""
        return {
            "organization_id": self.organization_id,
            "submission_id": self.submission_id,
            "alert_count": self.alert_count,
            "critical_alert_count": self.critical_alert_count,
            "high_alert_count": self.high_alert_count,
            "case_count": self.case_count,
            "open_case_count": self.open_case_count,
            "closed_case_count": self.closed_case_count,
            "investigation_count": self.investigation_count,
            "escalation_count": self.escalation_count,
            "asset_count": self.asset_count,
            "covered_asset_count": self.covered_asset_count,
            "monitoring_coverage_rate": round(self.monitoring_coverage_rate, 4),
            "alert_to_case_ratio": round(self.alert_to_case_ratio, 4),
            "critical_alert_case_link_rate": round(self.critical_alert_case_link_rate, 4),
            "case_investigation_rate": round(self.case_investigation_rate, 4),
            "case_closure_rate": round(self.case_closure_rate, 4),
            "escalation_rate": round(self.escalation_rate, 4),
            "median_investigation_duration_hours": round(self.median_investigation_duration_hours, 2),
            "median_case_lifecycle_duration_hours": round(self.median_case_lifecycle_duration_hours, 2),
        }


# ---------------------------------------------------------------------------
# Feature Extractor
# ---------------------------------------------------------------------------


class FeatureExtractor:
    """Extracts typed, deterministic feature sets from raw operational records."""

    @staticmethod
    def extract(
        organization_id: str,
        submission_id: str | None = None,
        alerts: list[AlertModel] | None = None,
        cases: list[CaseModel] | None = None,
        case_alert_links: list[CaseAlertLinkModel] | None = None,
        investigations: list[InvestigationModel] | None = None,
        escalations: list[EscalationModel] | None = None,
        actions: list[ActionModel] | None = None,
        resolutions: list[ResolutionModel] | None = None,
        closures: list[ClosureModel] | None = None,
        assets: list[AssetModel] | None = None,
        coverage: list[MonitoringCoverageModel] | None = None,
        declared_families: list[SubmissionEvidenceFamilyModel] | None = None,
    ) -> EntityPeriodFeatures:
        """Derive normalized features deterministically from model instances."""
        al_list = alerts or []
        cs_list = cases or []
        cal_list = case_alert_links or []
        inv_list = investigations or []
        esc_list = escalations or []
        act_list = actions or []
        res_list = resolutions or []
        clo_list = closures or []
        ast_list = assets or []
        cov_list = coverage or []
        fam_list = declared_families or []

        # 1. Alert breakdowns
        critical_alerts = [a for a in al_list if (a.severity or "").upper() == "CRITICAL"]
        high_alerts = [a for a in al_list if (a.severity or "").upper() == "HIGH"]
        medium_alerts = [a for a in al_list if (a.severity or "").upper() == "MEDIUM"]
        low_alerts = [a for a in al_list if (a.severity or "").upper() == "LOW"]

        # 2. Case breakdowns
        open_cases = [c for c in cs_list if (c.status or "").upper() in {"OPEN", "IN_PROGRESS", "ACTIVE"}]
        closed_cases = [c for c in cs_list if (c.status or "").upper() in {"CLOSED", "RESOLVED"}]

        # 3. Link mappings
        linked_alert_ids = {str(link.alert_id) for link in cal_list if link.alert_id}
        cases_with_inv = {str(i.case_id) for i in inv_list if i.case_id}
        cases_with_esc = {str(e.case_id) for e in esc_list if e.case_id}
        cases_with_act = {str(a.case_id) for a in act_list if a.case_id}
        cases_with_res = {str(r.case_id) for r in res_list if r.case_id}
        cases_with_clo = {str(c.case_id) for c in clo_list if c.case_id}

        unlinked_crit = [
            str(a.alert_id)
            for a in (critical_alerts + high_alerts)
            if str(a.alert_id) not in linked_alert_ids
        ]

        # 4. Ratios
        alert_count = len(al_list)
        case_count = len(cs_list)
        critical_high_count = len(critical_alerts) + len(high_alerts)

        alert_to_case_ratio = (case_count / alert_count) if alert_count > 0 else 0.0
        crit_link_rate = (
            ((critical_high_count - len(unlinked_crit)) / critical_high_count)
            if critical_high_count > 0
            else 1.0
        )
        case_inv_rate = (len(cases_with_inv) / case_count) if case_count > 0 else 0.0
        case_clo_rate = (len(closed_cases) / case_count) if case_count > 0 else 0.0
        esc_rate = (len(cases_with_esc) / case_count) if case_count > 0 else 0.0

        # 5. Asset & Coverage
        covered_asset_ids = {
            str(cov.asset_id)
            for cov in cov_list
            if cov.asset_id and (cov.coverage_state or "").upper() in {"COVERED", "PARTIAL", "FULL"}
        }
        asset_count = len(ast_list)
        cov_rate = (len(covered_asset_ids) / asset_count) if asset_count > 0 else 0.0

        critical_assets = [
            ast
            for ast in ast_list
            if (ast.criticality or "").upper() in {"TIER_1", "TIER_0", "CRITICAL", "HIGH"}
        ]
        unmonitored_crit = [
            str(ast.asset_id) for ast in critical_assets if str(ast.asset_id) not in covered_asset_ids
        ]

        # 6. Durations
        inv_durations: list[float] = []
        for inv in inv_list:
            if inv.started_at_utc and inv.completed_at_utc and inv.completed_at_utc >= inv.started_at_utc:
                dur = (inv.completed_at_utc - inv.started_at_utc).total_seconds() / 3600.0
                inv_durations.append(dur)

        median_inv_dur = compute_median(inv_durations)
        mean_inv_dur = float(statistics.mean(inv_durations)) if inv_durations else 0.0

        case_durations: list[float] = []
        case_creation_map = {str(c.case_id): c.created_at_utc for c in cs_list if c.created_at_utc}
        for clo in clo_list:
            created = case_creation_map.get(str(clo.case_id))
            if created and clo.closed_at_utc and clo.closed_at_utc >= created:
                dur = (clo.closed_at_utc - created).total_seconds() / 3600.0
                case_durations.append(dur)

        median_case_dur = compute_median(case_durations)

        # 7. Declared vs Actual family counts
        declared_counts: dict[str, int] = {}
        for fam in fam_list:
            if fam.evidence_family:
                declared_counts[fam.evidence_family] = fam.declared_record_count or 0

        actual_counts: dict[str, int] = {
            "alerts": alert_count,
            "cases": case_count,
            "case_alert_links": len(cal_list),
            "investigations": len(inv_list),
            "escalations": len(esc_list),
            "actions": len(act_list),
            "resolutions": len(res_list),
            "closures": len(clo_list),
            "assets": asset_count,
            "monitoring_coverage": len(cov_list),
        }

        return EntityPeriodFeatures(
            organization_id=organization_id,
            submission_id=submission_id,
            alert_count=alert_count,
            critical_alert_count=len(critical_alerts),
            high_alert_count=len(high_alerts),
            medium_alert_count=len(medium_alerts),
            low_alert_count=len(low_alerts),
            case_count=case_count,
            open_case_count=len(open_cases),
            closed_case_count=len(closed_cases),
            investigation_count=len(inv_list),
            escalation_count=len(esc_list),
            action_count=len(act_list),
            resolution_count=len(res_list),
            closure_count=len(clo_list),
            asset_count=asset_count,
            critical_asset_count=len(critical_assets),
            covered_asset_count=len(covered_asset_ids),
            alert_to_case_ratio=alert_to_case_ratio,
            critical_alert_case_link_rate=crit_link_rate,
            case_investigation_rate=case_inv_rate,
            case_closure_rate=case_clo_rate,
            escalation_rate=esc_rate,
            monitoring_coverage_rate=cov_rate,
            investigation_durations_hours=inv_durations,
            median_investigation_duration_hours=median_inv_dur,
            mean_investigation_duration_hours=mean_inv_dur,
            case_lifecycle_durations_hours=case_durations,
            median_case_lifecycle_duration_hours=median_case_dur,
            linked_alert_ids=linked_alert_ids,
            unlinked_critical_alert_ids=unlinked_crit,
            cases_with_investigation=cases_with_inv,
            cases_with_escalation=cases_with_esc,
            cases_with_action=cases_with_act,
            cases_with_resolution=cases_with_res,
            cases_with_closure=cases_with_clo,
            declared_family_counts=declared_counts,
            actual_family_counts=actual_counts,
            unmonitored_critical_asset_ids=unmonitored_crit,
            alerts=al_list,
            cases=cs_list,
            investigations=inv_list,
            escalations=esc_list,
            actions=act_list,
            resolutions=res_list,
            closures=clo_list,
            assets=ast_list,
            coverage=cov_list,
            declared_families=fam_list,
        )
