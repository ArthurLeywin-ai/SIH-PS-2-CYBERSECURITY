"""Deterministic Statistical Anomaly Detector.

Implements explainable statistical anomaly detection without opaque ML (ARCHITECTURE.md §10, §14):
- Median / MAD (Median Absolute Deviation)
- Interquartile Range (IQR)
- Extreme workflow velocity and duration outliers
- Volume surges and low closure rate outliers
- Complete calculation transparency (baseline value, method, threshold, deviation)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.backend.analytics.evidence import EvidenceResolver
from app.backend.analytics.explanations import format_statistical_anomaly_explanation
from app.backend.analytics.features import (
    EntityPeriodFeatures,
    compute_iqr,
    compute_mad,
    compute_median,
)
from app.backend.analytics.models import (
    EvidenceRole,
    SignalSeverity,
    SignalType,
    SupervisorySignal,
)


class StatisticalAnomalyDetector:
    """Evaluates canonical operational metrics against statistical baselines."""

    DETECTOR_ID = "DET-STATISTICAL-ANOMALY"
    DETECTOR_VERSION = "1.0.0"

    def __init__(
        self,
        resolver: EvidenceResolver | None = None,
        min_cases_for_rate_analysis: int = 5,
        min_cases: int | None = None,
        min_investigations: int | None = None,
        default_baseline_closure_rate: float = 0.70,
        investigation_duration_outlier_hours: float = 72.0,  # 3 days
    ) -> None:
        self.resolver = resolver or EvidenceResolver()
        self.min_cases = min_cases if min_cases is not None else min_cases_for_rate_analysis
        self.min_investigations = min_investigations if min_investigations is not None else 3
        self.default_closure_rate = default_baseline_closure_rate
        self.duration_outlier_threshold = investigation_duration_outlier_hours

    def detect(
        self,
        features: EntityPeriodFeatures,
        historical_closure_rates: list[float] | None = None,
        historical_durations: list[float] | None = None,
    ) -> list[SupervisorySignal]:
        """Execute statistical anomaly evaluations."""
        signals: list[SupervisorySignal] = []

        # 1. Abnormally Low Closure Rate
        sig_closure = self._check_abnormally_low_closure_rate(features, historical_closure_rates)
        if sig_closure:
            signals.append(sig_closure)

        # 2. Extended Investigation Duration Outliers
        sig_dur = self._check_extended_investigation_durations(features, historical_durations)
        if sig_dur:
            signals.append(sig_dur)

        # 3. Alert Volume per Asset Outlier
        sig_vol = self._check_alert_density_outlier(features)
        if sig_vol:
            signals.append(sig_vol)

        # 4. Zero Escalation Despite Critical Alerts
        sig_zero_esc = self._check_zero_escalation_anomaly(features)
        if sig_zero_esc:
            signals.append(sig_zero_esc)

        return signals

    def _check_abnormally_low_closure_rate(
        self,
        features: EntityPeriodFeatures,
        historical_closure_rates: list[float] | None = None,
    ) -> SupervisorySignal | None:
        if features.case_count < self.min_cases:
            return None

        current_rate = features.case_closure_rate

        # Baseline: historical median or configured supervisory standard (70%)
        if historical_closure_rates and len(historical_closure_rates) >= 3:
            baseline = compute_median(historical_closure_rates)
            mad = compute_mad(historical_closure_rates)
            threshold = max(0.20, baseline - 2.0 * mad)
            method = f"HISTORICAL_MEDIAN_MAD (n={len(historical_closure_rates)})"
        else:
            baseline = self.default_closure_rate
            threshold = 0.30
            method = "SUPERVISORY_REFERENCE_BENCHMARK"

        if current_rate < threshold:
            deviation = round(current_rate - baseline, 4)
            short, detailed, questions = format_statistical_anomaly_explanation(
                metric_name="case_closure_rate",
                observed_val=f"{current_rate:.1%}",
                baseline_val=f"{baseline:.1%}",
                baseline_method=method,
                deviation=f"{deviation:+.1%}",
                direction="below",
            )

            severity = SignalSeverity.HIGH if current_rate < 0.20 else SignalSeverity.MEDIUM

            return SupervisorySignal(
                signal_id=str(uuid.uuid4()),
                organization_id=features.organization_id,
                submission_id=features.submission_id,
                signal_type=SignalType.STATISTICAL_ANOMALY,
                severity=severity,
                title="Abnormally Low Case Closure Rate",
                short_rationale=short,
                detailed_explanation=detailed,
                basis={
                    "metric": "case_closure_rate",
                    "observed_closure_rate": current_rate,
                    "baseline_reference": baseline,
                    "threshold": threshold,
                    "deviation": deviation,
                    "baseline_method": method,
                    "case_count": features.case_count,
                    "closed_case_count": features.closed_case_count,
                },
                observed_value=current_rate,
                expected_value=baseline,
                confidence=0.88,
                evidence_references=[
                    self.resolver.build_reference(
                        record_id=str(c.case_id),
                        evidence_family="cases",
                        role=EvidenceRole.SUPPORTING,
                        description=f"Case {c.case_id} remains open or unresolved.",
                    )
                    for c in features.cases
                    if (c.status or "").upper() != "CLOSED"
                ][:10],
                affected_record_ids=[
                    str(c.case_id) for c in features.cases if (c.status or "").upper() != "CLOSED"
                ],
                detector_id=self.DETECTOR_ID,
                detector_version=self.DETECTOR_VERSION,
                investigation_questions=questions,
                generated_at_utc=datetime.now(UTC),
            )

        return None

    def _check_extended_investigation_durations(
        self,
        features: EntityPeriodFeatures,
        historical_durations: list[float] | None = None,
    ) -> SupervisorySignal | None:
        durations = features.investigation_durations_hours
        if not durations or len(durations) < self.min_investigations:
            return None

        # Compute IQR/MAD over available durations
        all_durs = (historical_durations or []) + durations
        q1, q3, iqr = compute_iqr(all_durs)
        med = compute_median(all_durs)
        mad = compute_mad(all_durs)

        # Robust upper outlier threshold
        threshold = max(self.duration_outlier_threshold, med + 3.0 * mad, q3 + 1.5 * iqr)

        outlier_invs = []
        for inv in features.investigations:
            if inv.started_at_utc and inv.completed_at_utc:
                dur = (inv.completed_at_utc - inv.started_at_utc).total_seconds() / 3600.0
                if dur > threshold:
                    outlier_invs.append((str(inv.investigation_id), round(dur, 2)))

        if not outlier_invs:
            return None

        max_dur = max(d for _, d in outlier_invs)
        deviation = round(max_dur - med, 2)

        short, detailed, questions = format_statistical_anomaly_explanation(
            metric_name="investigation_duration_hours",
            observed_val=f"{max_dur}h (median={features.median_investigation_duration_hours:.1f}h)",
            baseline_val=f"{med:.1f}h",
            baseline_method=f"IQR_MAD_THRESHOLD (threshold={threshold:.1f}h)",
            deviation=f"+{deviation}h",
            direction="above",
        )

        affected_ids = [iid for iid, _ in outlier_invs]
        refs = [
            self.resolver.build_reference(
                record_id=iid,
                evidence_family="investigations",
                role=EvidenceRole.TRIGGER,
                description=f"Investigation {iid} duration ({dur}h) exceeds statistical threshold ({threshold:.1f}h).",
            )
            for iid, dur in outlier_invs[:10]
        ]

        return SupervisorySignal(
            signal_id=str(uuid.uuid4()),
            organization_id=features.organization_id,
            submission_id=features.submission_id,
            signal_type=SignalType.STATISTICAL_ANOMALY,
            severity=SignalSeverity.MEDIUM,
            title="Statistical Outlier in Investigation Duration",
            short_rationale=short,
            detailed_explanation=detailed,
            basis={
                "metric": "investigation_duration_hours",
                "outlier_count": len(outlier_invs),
                "threshold_hours": round(threshold, 2),
                "median_hours": round(med, 2),
                "mad_hours": round(mad, 2),
                "max_duration_hours": max_dur,
            },
            observed_value=max_dur,
            expected_value=round(med, 2),
            confidence=0.86,
            evidence_references=refs,
            affected_record_ids=affected_ids,
            detector_id=self.DETECTOR_ID,
            detector_version=self.DETECTOR_VERSION,
            investigation_questions=questions,
            generated_at_utc=datetime.now(UTC),
        )

    def _check_alert_density_outlier(self, features: EntityPeriodFeatures) -> SupervisorySignal | None:
        if features.asset_count == 0 or features.alert_count < 20:
            return None

        density = features.alert_count / features.asset_count
        # Flag extreme alert density (> 50 alerts per asset for standard scale)
        if density > 50.0:
            short, detailed, questions = format_statistical_anomaly_explanation(
                metric_name="alert_density_per_asset",
                observed_val=f"{density:.2f}",
                baseline_val="5.0 - 20.0",
                baseline_method="DENSITY_HEURISTIC_THRESHOLD",
                deviation=f"{density - 20.0:.2f}",
                direction="above",
            )

            return SupervisorySignal(
                signal_id=str(uuid.uuid4()),
                organization_id=features.organization_id,
                submission_id=features.submission_id,
                signal_type=SignalType.STATISTICAL_ANOMALY,
                severity=SignalSeverity.MEDIUM,
                title="Extreme Alert Volume Density per Asset",
                short_rationale=short,
                detailed_explanation=detailed,
                basis={
                    "metric": "alert_density_per_asset",
                    "alert_count": features.alert_count,
                    "asset_count": features.asset_count,
                    "density": round(density, 2),
                },
                observed_value=round(density, 2),
                expected_value=15.0,
                confidence=0.82,
                evidence_references=[],
                affected_record_ids=[],
                detector_id=self.DETECTOR_ID,
                detector_version=self.DETECTOR_VERSION,
                investigation_questions=questions,
                generated_at_utc=datetime.now(UTC),
            )

        return None

    def _check_zero_escalation_anomaly(self, features: EntityPeriodFeatures) -> SupervisorySignal | None:
        if features.critical_alert_count >= 5 and features.case_count >= 5 and features.escalation_count == 0:
            short, detailed, questions = format_statistical_anomaly_explanation(
                metric_name="escalation_rate",
                observed_val="0.0%",
                baseline_val="15.0% - 35.0%",
                baseline_method="STATISTICAL_EXPECTATION_CRITICAL_ALERTS",
                deviation="-100%",
                direction="below",
            )

            return SupervisorySignal(
                signal_id=str(uuid.uuid4()),
                organization_id=features.organization_id,
                submission_id=features.submission_id,
                signal_type=SignalType.STATISTICAL_ANOMALY,
                severity=SignalSeverity.MEDIUM,
                title="Zero Escalations Observed Despite Severe Threat Activity",
                short_rationale=short,
                detailed_explanation=detailed,
                basis={
                    "critical_alert_count": features.critical_alert_count,
                    "case_count": features.case_count,
                    "escalation_count": 0,
                    "escalation_rate": 0.0,
                },
                observed_value=0.0,
                expected_value="> 0.0",
                confidence=0.85,
                evidence_references=[],
                affected_record_ids=[],
                detector_id=self.DETECTOR_ID,
                detector_version=self.DETECTOR_VERSION,
                investigation_questions=questions,
                generated_at_utc=datetime.now(UTC),
            )

        return None
