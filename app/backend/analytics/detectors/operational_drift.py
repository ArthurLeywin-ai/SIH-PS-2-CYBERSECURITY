"""Operational Drift Analytics Detector.

Implements temporal comparison across submissions for the same organization (ARCHITECTURE.md §10):
- Compares current reporting period metrics against prior submission baseline
- Enforces minimum sample size guardrails to avoid flagging trivial fluctuations
- Evaluates alert volume trends, closure-rate shifts, and coverage degradation
- Records baseline period, comparison period, absolute change, and relative change
- Every signal includes concrete evidence references to current and baseline operational scope
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.backend.analytics.evidence import EvidenceResolver
from app.backend.analytics.explanations import format_operational_drift_explanation
from app.backend.analytics.features import EntityPeriodFeatures
from app.backend.analytics.models import (
    EvidenceReference,
    EvidenceRole,
    SignalSeverity,
    SignalType,
    SupervisorySignal,
    generate_deterministic_signal_id,
)


class OperationalDriftDetector:
    """Evaluates temporal shifts across multiple submissions for the same entity."""

    DETECTOR_ID = "DET-OPERATIONAL-DRIFT"
    DETECTOR_VERSION = "1.0.0"

    def __init__(
        self,
        resolver: EvidenceResolver | None = None,
        min_alerts_for_drift: int = 10,
        volume_drift_threshold_pct: float = 50.0,
        rate_drop_threshold_pct: float = 25.0,
    ) -> None:
        self.resolver = resolver or EvidenceResolver()
        self.min_alerts = min_alerts_for_drift
        self.volume_threshold = volume_drift_threshold_pct
        self.rate_drop_threshold = rate_drop_threshold_pct

    def detect(
        self,
        current_features: EntityPeriodFeatures,
        prior_features_list: list[EntityPeriodFeatures] | None = None,
    ) -> list[SupervisorySignal]:
        """Execute temporal drift analysis against historical submissions."""
        if not prior_features_list:
            # Insufficient history guardrail: single period has no baseline (ARCHITECTURE.md §10.2)
            return []

        prior_sorted = sorted(
            [pf for pf in prior_features_list if pf.submission_id != current_features.submission_id],
            key=lambda x: str(x.submission_id),
        )
        if not prior_sorted:
            return []

        baseline = prior_sorted[-1]
        signals: list[SupervisorySignal] = []

        curr_period = current_features.submission_id or "CURRENT_PERIOD"
        base_period = baseline.submission_id or "PRIOR_PERIOD"

        # 1. Alert Volume Surge or Collapse
        if current_features.alert_count >= self.min_alerts or baseline.alert_count >= self.min_alerts:
            base_vol = baseline.alert_count
            curr_vol = current_features.alert_count
            pct_change = (
                ((curr_vol - base_vol) / base_vol) * 100.0
                if base_vol > 0
                else (100.0 if curr_vol > 0 else 0.0)
            )

            if abs(pct_change) >= self.volume_threshold:
                short, detailed, questions = format_operational_drift_explanation(
                    metric_name="alert_volume",
                    current_val=curr_vol,
                    baseline_val=base_vol,
                    current_period=curr_period,
                    baseline_period=base_period,
                    pct_change=pct_change,
                )

                refs: list[EvidenceReference] = []
                affected_ids: list[str] = []

                # Current period sample alerts
                for a in current_features.alerts[:5]:
                    aid = str(a.alert_id)
                    affected_ids.append(aid)
                    refs.append(
                        self.resolver.build_reference(
                            record_id=aid,
                            evidence_family="alerts",
                            role=EvidenceRole.TRIGGER,
                            description=f"Current period alert {aid} contributing to volume {curr_vol}",
                        )
                    )

                # Scope references
                if current_features.submission_id:
                    refs.append(
                        self.resolver.build_reference(
                            record_id=current_features.submission_id,
                            evidence_family="submissions",
                            role=EvidenceRole.TRIGGER,
                            description=f"Current reporting period submission {curr_period}",
                        )
                    )
                if baseline.submission_id:
                    refs.append(
                        self.resolver.build_reference(
                            record_id=baseline.submission_id,
                            evidence_family="submissions",
                            role=EvidenceRole.BASELINE_MEMBER,
                            description=f"Baseline comparison submission {base_period} (volume={base_vol})",
                        )
                    )

                signal_id = generate_deterministic_signal_id(
                    organization_id=current_features.organization_id,
                    submission_id=current_features.submission_id,
                    detector_id=self.DETECTOR_ID,
                    detector_version=self.DETECTOR_VERSION,
                    signal_type=SignalType.OPERATIONAL_DRIFT.value,
                    finding_key="alert_volume_drift",
                    affected_record_ids=sorted(affected_ids),
                    basis_identity=f"vol:{curr_vol}:{base_vol}:{curr_period}:{base_period}",
                )

                signals.append(
                    SupervisorySignal(
                        signal_id=signal_id,
                        organization_id=current_features.organization_id,
                        submission_id=current_features.submission_id,
                        signal_type=SignalType.OPERATIONAL_DRIFT,
                        severity=SignalSeverity.MEDIUM,
                        title="Significant Operational Alert Volume Drift",
                        short_rationale=short,
                        detailed_explanation=detailed,
                        basis={
                            "metric": "alert_volume",
                            "baseline_period": base_period,
                            "comparison_period": curr_period,
                            "baseline_value": base_vol,
                            "current_value": curr_vol,
                            "absolute_change": curr_vol - base_vol,
                            "percent_change": round(pct_change, 2),
                        },
                        observed_value=curr_vol,
                        expected_value=base_vol,
                        confidence=0.86,
                        evidence_references=refs,
                        affected_record_ids=sorted(affected_ids),
                        detector_id=self.DETECTOR_ID,
                        detector_version=self.DETECTOR_VERSION,
                        investigation_questions=questions,
                        generated_at_utc=datetime.now(UTC),
                    )
                )

        # 2. Case Closure Rate Degradation
        if current_features.case_count >= 5 and baseline.case_count >= 5:
            base_rate = baseline.case_closure_rate
            curr_rate = current_features.case_closure_rate
            rate_drop = (base_rate - curr_rate) * 100.0  # percentage points
            if rate_drop >= self.rate_drop_threshold:
                pct_change = -rate_drop
                short, detailed, questions = format_operational_drift_explanation(
                    metric_name="case_closure_rate",
                    current_val=f"{curr_rate:.1%}",
                    baseline_val=f"{base_rate:.1%}",
                    current_period=curr_period,
                    baseline_period=base_period,
                    pct_change=pct_change,
                )

                refs = []
                affected_ids = []

                # Current open cases
                for c in current_features.cases:
                    if (c.status or "").upper() != "CLOSED":
                        cid = str(c.case_id)
                        affected_ids.append(cid)
                        if len(refs) < 5:
                            refs.append(
                                self.resolver.build_reference(
                                    record_id=cid,
                                    evidence_family="cases",
                                    role=EvidenceRole.TRIGGER,
                                    description=f"Current period open case {cid}",
                                )
                            )

                if current_features.submission_id:
                    refs.append(
                        self.resolver.build_reference(
                            record_id=current_features.submission_id,
                            evidence_family="submissions",
                            role=EvidenceRole.TRIGGER,
                            description=f"Current reporting period submission {curr_period} (closure={curr_rate:.1%})",
                        )
                    )
                if baseline.submission_id:
                    refs.append(
                        self.resolver.build_reference(
                            record_id=baseline.submission_id,
                            evidence_family="submissions",
                            role=EvidenceRole.BASELINE_MEMBER,
                            description=f"Baseline comparison submission {base_period} (closure={base_rate:.1%})",
                        )
                    )

                signal_id = generate_deterministic_signal_id(
                    organization_id=current_features.organization_id,
                    submission_id=current_features.submission_id,
                    detector_id=self.DETECTOR_ID,
                    detector_version=self.DETECTOR_VERSION,
                    signal_type=SignalType.OPERATIONAL_DRIFT.value,
                    finding_key="closure_rate_degradation",
                    affected_record_ids=sorted(affected_ids),
                    basis_identity=f"closure:{curr_rate:.4f}:{base_rate:.4f}:{curr_period}:{base_period}",
                )

                signals.append(
                    SupervisorySignal(
                        signal_id=signal_id,
                        organization_id=current_features.organization_id,
                        submission_id=current_features.submission_id,
                        signal_type=SignalType.OPERATIONAL_DRIFT,
                        severity=SignalSeverity.HIGH,
                        title="Substantial Degradation in Case Closure Rate",
                        short_rationale=short,
                        detailed_explanation=detailed,
                        basis={
                            "metric": "case_closure_rate",
                            "baseline_period": base_period,
                            "comparison_period": curr_period,
                            "baseline_rate": round(base_rate, 4),
                            "current_rate": round(curr_rate, 4),
                            "percentage_point_drop": round(rate_drop, 2),
                        },
                        observed_value=round(curr_rate, 4),
                        expected_value=round(base_rate, 4),
                        confidence=0.90,
                        evidence_references=refs,
                        affected_record_ids=sorted(affected_ids),
                        detector_id=self.DETECTOR_ID,
                        detector_version=self.DETECTOR_VERSION,
                        investigation_questions=questions,
                        generated_at_utc=datetime.now(UTC),
                    )
                )

        # 3. Monitoring Coverage Rate Drop
        if baseline.monitoring_coverage_rate > 0.50:
            cov_drop = (baseline.monitoring_coverage_rate - current_features.monitoring_coverage_rate) * 100.0
            if cov_drop >= 15.0:
                short, detailed, questions = format_operational_drift_explanation(
                    metric_name="monitoring_coverage_rate",
                    current_val=f"{current_features.monitoring_coverage_rate:.1%}",
                    baseline_val=f"{baseline.monitoring_coverage_rate:.1%}",
                    current_period=curr_period,
                    baseline_period=base_period,
                    pct_change=-cov_drop,
                )

                refs = []
                affected_ids = []

                for aid in current_features.unmonitored_critical_asset_ids[:5]:
                    affected_ids.append(aid)
                    refs.append(
                        self.resolver.build_reference(
                            record_id=aid,
                            evidence_family="assets",
                            role=EvidenceRole.TRIGGER,
                            description=f"Current asset {aid} lacks active coverage",
                        )
                    )

                if current_features.submission_id:
                    refs.append(
                        self.resolver.build_reference(
                            record_id=current_features.submission_id,
                            evidence_family="submissions",
                            role=EvidenceRole.TRIGGER,
                            description=(
                                f"Current submission {curr_period} "
                                f"(coverage={current_features.monitoring_coverage_rate:.1%})"
                            ),
                        )
                    )
                if baseline.submission_id:
                    refs.append(
                        self.resolver.build_reference(
                            record_id=baseline.submission_id,
                            evidence_family="submissions",
                            role=EvidenceRole.BASELINE_MEMBER,
                            description=(
                                f"Baseline submission {base_period} "
                                f"(coverage={baseline.monitoring_coverage_rate:.1%})"
                            ),
                        )
                    )

                signal_id = generate_deterministic_signal_id(
                    organization_id=current_features.organization_id,
                    submission_id=current_features.submission_id,
                    detector_id=self.DETECTOR_ID,
                    detector_version=self.DETECTOR_VERSION,
                    signal_type=SignalType.OPERATIONAL_DRIFT.value,
                    finding_key="coverage_rate_drop",
                    affected_record_ids=sorted(affected_ids),
                    basis_identity=(
                        f"cov:{current_features.monitoring_coverage_rate:.4f}:"
                        f"{baseline.monitoring_coverage_rate:.4f}:{curr_period}:{base_period}"
                    ),
                )

                signals.append(
                    SupervisorySignal(
                        signal_id=signal_id,
                        organization_id=current_features.organization_id,
                        submission_id=current_features.submission_id,
                        signal_type=SignalType.OPERATIONAL_DRIFT,
                        severity=SignalSeverity.HIGH,
                        title="Downturn in Declared Monitoring Coverage",
                        short_rationale=short,
                        detailed_explanation=detailed,
                        basis={
                            "metric": "monitoring_coverage_rate",
                            "baseline_period": base_period,
                            "comparison_period": curr_period,
                            "baseline_coverage": round(baseline.monitoring_coverage_rate, 4),
                            "current_coverage": round(current_features.monitoring_coverage_rate, 4),
                            "percentage_point_drop": round(cov_drop, 2),
                        },
                        observed_value=round(current_features.monitoring_coverage_rate, 4),
                        expected_value=round(baseline.monitoring_coverage_rate, 4),
                        confidence=0.92,
                        evidence_references=refs,
                        affected_record_ids=sorted(affected_ids),
                        detector_id=self.DETECTOR_ID,
                        detector_version=self.DETECTOR_VERSION,
                        investigation_questions=questions,
                        generated_at_utc=datetime.now(UTC),
                    )
                )

        return signals
