"""Deterministic Statistical Anomaly Detector.

Implements explainable statistical anomaly detection without opaque ML (ARCHITECTURE.md §10, §14):
- Median / MAD (Median Absolute Deviation) and Interquartile Range (IQR)
- Extreme workflow velocity and investigation duration outliers
- Abnormally low case closure rate against historical baseline or configured expectations
- Alert density anomaly evaluated against empirical historical sample (minimum sample size >= 3)
- Complete calculation transparency: observed value, baseline, method, sample size, threshold, deviation, limitations
"""

from __future__ import annotations

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
    EvidenceReference,
    EvidenceRole,
    SignalSeverity,
    SignalType,
    SupervisorySignal,
    generate_deterministic_signal_id,
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
        historical_densities: list[float] | None = None,
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

        # 3. Alert Volume per Asset Outlier (only with defensible baseline sample >= 3)
        if historical_densities:
            sig_vol = self._check_alert_density_outlier(features, historical_densities)
            if sig_vol:
                signals.append(sig_vol)

        return signals

    def _check_abnormally_low_closure_rate(
        self,
        features: EntityPeriodFeatures,
        historical_closure_rates: list[float] | None = None,
    ) -> SupervisorySignal | None:
        if features.case_count < self.min_cases:
            return None

        current_rate = features.case_closure_rate

        # Baseline: historical median with MAD or configured reference benchmark
        if historical_closure_rates and len(historical_closure_rates) >= 3:
            baseline = compute_median(historical_closure_rates)
            mad = compute_mad(historical_closure_rates)
            threshold = max(0.20, baseline - 2.0 * mad)
            method = f"HISTORICAL_MEDIAN_MAD (n={len(historical_closure_rates)})"
            sample_size = len(historical_closure_rates)
        else:
            baseline = self.default_closure_rate
            threshold = 0.30
            method = "CONFIGURED_ANALYTICAL_EXPECTATION"
            sample_size = 1

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

            affected_cases = [str(c.case_id) for c in features.cases if (c.status or "").upper() != "CLOSED"]
            refs: list[EvidenceReference] = [
                self.resolver.build_reference(
                    record_id=str(c.case_id),
                    evidence_family="cases",
                    role=EvidenceRole.SUPPORTING,
                    description=f"Case {c.case_id} remains open or unresolved.",
                )
                for c in features.cases
                if (c.status or "").upper() != "CLOSED"
            ][:10]

            signal_id = generate_deterministic_signal_id(
                organization_id=features.organization_id,
                submission_id=features.submission_id,
                detector_id=self.DETECTOR_ID,
                detector_version=self.DETECTOR_VERSION,
                signal_type=SignalType.STATISTICAL_ANOMALY.value,
                finding_key="abnormally_low_closure_rate",
                affected_record_ids=affected_cases,
                basis_identity=f"closure_rate:{current_rate:.4f}:{baseline:.4f}:{sample_size}",
            )

            return SupervisorySignal(
                signal_id=signal_id,
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
                    "sample_size": sample_size,
                    "limitations": f"Requires minimum sample of >= {self.min_cases} cases in reporting period",
                    "case_count": features.case_count,
                    "closed_case_count": features.closed_case_count,
                },
                observed_value=current_rate,
                expected_value=baseline,
                confidence=0.88,
                evidence_references=refs,
                affected_record_ids=affected_cases,
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

        signal_id = generate_deterministic_signal_id(
            organization_id=features.organization_id,
            submission_id=features.submission_id,
            detector_id=self.DETECTOR_ID,
            detector_version=self.DETECTOR_VERSION,
            signal_type=SignalType.STATISTICAL_ANOMALY.value,
            finding_key="extended_investigation_durations",
            affected_record_ids=affected_ids,
            basis_identity=f"duration:{max_dur}:{med:.2f}:{len(all_durs)}",
        )

        return SupervisorySignal(
            signal_id=signal_id,
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
                "sample_size": len(all_durs),
                "threshold_hours": round(threshold, 2),
                "median_hours": round(med, 2),
                "mad_hours": round(mad, 2),
                "max_duration_hours": max_dur,
                "baseline_method": "IQR_MAD_THRESHOLD",
                "limitations": f"Requires minimum sample of >= {self.min_investigations} completed investigations",
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

    def _check_alert_density_outlier(
        self,
        features: EntityPeriodFeatures,
        historical_densities: list[float],
    ) -> SupervisorySignal | None:
        if features.asset_count == 0 or features.alert_count < 20 or len(historical_densities) < 3:
            return None

        density = features.alert_count / features.asset_count
        med_density = compute_median(historical_densities)
        mad_density = compute_mad(historical_densities)
        threshold = med_density + 3.0 * max(mad_density, 1.0)

        if density > threshold:
            deviation = round(density - med_density, 2)
            short, detailed, questions = format_statistical_anomaly_explanation(
                metric_name="alert_density_per_asset",
                observed_val=f"{density:.2f}",
                baseline_val=f"{med_density:.2f}",
                baseline_method=f"HISTORICAL_MEDIAN_MAD (n={len(historical_densities)})",
                deviation=f"+{deviation:.2f}",
                direction="above",
            )

            sample_alert_ids = [str(a.alert_id) for a in features.alerts[:5]]
            refs: list[EvidenceReference] = [
                self.resolver.build_reference(
                    record_id=aid,
                    evidence_family="alerts",
                    role=EvidenceRole.TRIGGER,
                    description=f"Alert {aid} contributing to aggregate density ({density:.2f} alerts/asset)",
                )
                for aid in sample_alert_ids
            ]
            for asset in features.assets[:5]:
                refs.append(
                    self.resolver.build_reference(
                        record_id=str(asset.asset_id),
                        evidence_family="assets",
                        role=EvidenceRole.SUPPORTING,
                        description=f"Asset {asset.asset_id} included in density calculation denominator",
                    )
                )

            signal_id = generate_deterministic_signal_id(
                organization_id=features.organization_id,
                submission_id=features.submission_id,
                detector_id=self.DETECTOR_ID,
                detector_version=self.DETECTOR_VERSION,
                signal_type=SignalType.STATISTICAL_ANOMALY.value,
                finding_key="alert_density_outlier",
                affected_record_ids=sample_alert_ids,
                basis_identity=f"density:{density:.2f}:{med_density:.2f}:{len(historical_densities)}",
            )

            return SupervisorySignal(
                signal_id=signal_id,
                organization_id=features.organization_id,
                submission_id=features.submission_id,
                signal_type=SignalType.STATISTICAL_ANOMALY,
                severity=SignalSeverity.MEDIUM,
                title="Statistical Anomaly in Alert Volume Density per Asset",
                short_rationale=short,
                detailed_explanation=detailed,
                basis={
                    "metric": "alert_density_per_asset",
                    "observed_density": round(density, 2),
                    "baseline_median": round(med_density, 2),
                    "baseline_mad": round(mad_density, 2),
                    "threshold": round(threshold, 2),
                    "deviation": deviation,
                    "sample_size": len(historical_densities),
                    "baseline_method": f"HISTORICAL_MEDIAN_MAD (n={len(historical_densities)})",
                    "limitations": "Requires at least 20 alerts, non-zero assets, and historical sample size >= 3",
                    "alert_count": features.alert_count,
                    "asset_count": features.asset_count,
                },
                observed_value=round(density, 2),
                expected_value=round(med_density, 2),
                confidence=0.84,
                evidence_references=refs,
                affected_record_ids=sample_alert_ids,
                detector_id=self.DETECTOR_ID,
                detector_version=self.DETECTOR_VERSION,
                investigation_questions=questions,
                generated_at_utc=datetime.now(UTC),
            )

        return None
