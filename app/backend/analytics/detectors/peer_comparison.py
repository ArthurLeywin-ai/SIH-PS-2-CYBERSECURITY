"""Peer Comparison Analytics Detector.

Implements cohort-based supervisory comparisons against matched peer entities (ARCHITECTURE.md §11):
- Peer cohorts strictly grouped by canonical organization attributes: scale_band and operating_model
- Strict guardrails: minimum cohort size enforced to prevent misleading signals from small samples
- NO silent fallback to scale-only or entity-wide comparison (ARCHITECTURE.md §11.3)
- Compares normalized operational rates (coverage rate, closure rate)
- Records cohort definition, population size, subject value, peer median, and deviation
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.backend.analytics.evidence import EvidenceResolver
from app.backend.analytics.explanations import format_peer_deviation_explanation
from app.backend.analytics.features import (
    EntityPeriodFeatures,
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
from app.backend.persistence.models import OrganizationModel


class PeerComparisonDetector:
    """Evaluates an entity's operational metrics against a matched peer cohort."""

    DETECTOR_ID = "DET-PEER-COMPARISON"
    DETECTOR_VERSION = "1.0.0"

    def __init__(
        self,
        resolver: EvidenceResolver | None = None,
        min_cohort_size: int = 3,
        significant_deviation_mad_multiplier: float = 2.0,
    ) -> None:
        self.resolver = resolver or EvidenceResolver()
        self.min_cohort_size = min_cohort_size
        self.mad_multiplier = significant_deviation_mad_multiplier

    def detect(
        self,
        features: EntityPeriodFeatures,
        organization: OrganizationModel | None,
        peer_features: list[EntityPeriodFeatures] | None = None,
        all_organizations: list[OrganizationModel] | None = None,
    ) -> list[SupervisorySignal]:
        """Execute peer comparative analysis."""
        if not organization or not peer_features or len(peer_features) < self.min_cohort_size:
            # Enforce guardrail: insufficient peers -> produce no misleading signal (ARCHITECTURE.md §11.3)
            return []

        # 1. Filter peer features to matched exact cohort (scale_band + operating_model)
        org_map = {str(o.organization_id): o for o in (all_organizations or [])}
        cohort_features: list[EntityPeriodFeatures] = []

        scale = organization.scale_band or "UNKNOWN"
        op_model = organization.operating_model or "UNKNOWN"

        for pf in peer_features:
            if pf.organization_id == features.organization_id:
                continue
            peer_org = org_map.get(pf.organization_id)
            if peer_org and peer_org.scale_band == scale and peer_org.operating_model == op_model:
                cohort_features.append(pf)

        # Strict guardrail: NO silent fallback to scale-only or all entities
        if len(cohort_features) < self.min_cohort_size:
            return []

        cohort_desc = f"scale_band={scale}, operating_model={op_model} (cohort_size={len(cohort_features)})"
        signals: list[SupervisorySignal] = []

        # Compare Rate 1: Monitoring Coverage Rate
        sig_cov = self._compare_metric(
            features=features,
            cohort=cohort_features,
            metric_name="monitoring_coverage_rate",
            subject_val=features.monitoring_coverage_rate,
            cohort_vals=[pf.monitoring_coverage_rate for pf in cohort_features],
            cohort_desc=cohort_desc,
            lower_is_worse=True,
        )
        if sig_cov:
            signals.append(sig_cov)

        # Compare Rate 2: Case Closure Rate
        if features.case_count >= 3:
            sig_clo = self._compare_metric(
                features=features,
                cohort=cohort_features,
                metric_name="case_closure_rate",
                subject_val=features.case_closure_rate,
                cohort_vals=[pf.case_closure_rate for pf in cohort_features if pf.case_count >= 3],
                cohort_desc=cohort_desc,
                lower_is_worse=True,
            )
            if sig_clo:
                signals.append(sig_clo)

        return signals

    def _compare_metric(
        self,
        features: EntityPeriodFeatures,
        cohort: list[EntityPeriodFeatures],
        metric_name: str,
        subject_val: float,
        cohort_vals: list[float],
        cohort_desc: str,
        lower_is_worse: bool = True,
    ) -> SupervisorySignal | None:
        if len(cohort_vals) < self.min_cohort_size:
            return None

        peer_med = compute_median(cohort_vals)
        peer_mad = compute_mad(cohort_vals)
        effective_mad = max(peer_mad, 0.05)  # floor to prevent division by zero

        deviation = subject_val - peer_med

        # Check significance: subject is far from peer median
        threshold = self.mad_multiplier * effective_mad
        is_significant = (lower_is_worse and deviation < -threshold) or (
            not lower_is_worse and deviation > threshold
        )

        if not is_significant:
            return None

        short, detailed, questions = format_peer_deviation_explanation(
            metric_name=metric_name,
            subject_val=f"{subject_val:.1%}" if "rate" in metric_name else f"{subject_val:.2f}",
            peer_median=f"{peer_med:.1%}" if "rate" in metric_name else f"{peer_med:.2f}",
            peer_cohort_desc=cohort_desc,
            cohort_size=len(cohort_vals),
            deviation=f"{deviation:+.1%}" if "rate" in metric_name else f"{deviation:+.2f}",
        )

        # Subject evidence references (TRIGGER)
        subject_refs: list[EvidenceReference] = []
        affected_ids: list[str] = []

        if "coverage" in metric_name:
            if features.assets:
                for a in features.assets[:5]:
                    aid = str(a.asset_id)
                    affected_ids.append(aid)
                    subject_refs.append(
                        self.resolver.build_reference(
                            record_id=aid,
                            evidence_family="assets",
                            role=EvidenceRole.TRIGGER,
                            description=f"Subject asset {aid} contributing to coverage rate {subject_val:.1%}",
                        )
                    )
            elif features.submission_id:
                affected_ids.append(features.submission_id)
                subject_refs.append(
                    self.resolver.build_reference(
                        record_id=features.submission_id,
                        evidence_family="submissions",
                        role=EvidenceRole.TRIGGER,
                        description=f"Subject submission reporting {metric_name} {subject_val:.1%}",
                    )
                )
        elif "closure" in metric_name and features.cases:
            for c in features.cases[:5]:
                    cid = str(c.case_id)
                    affected_ids.append(cid)
                    subject_refs.append(
                        self.resolver.build_reference(
                            record_id=cid,
                            evidence_family="cases",
                            role=EvidenceRole.TRIGGER,
                            description=f"Subject case {cid} contributing to closure rate {subject_val:.1%}",
                        )
                    )

        # Peer cohort references (PEER_MEMBER)
        peer_refs: list[EvidenceReference] = [
            self.resolver.build_reference(
                record_id=pf.organization_id,
                evidence_family="organizations",
                role=EvidenceRole.PEER_MEMBER,
                description=f"Peer organization with metric value {getattr(pf, metric_name, 0.0):.2f}",
            )
            for pf in cohort[:5]
        ]

        all_refs = subject_refs + peer_refs

        signal_id = generate_deterministic_signal_id(
            organization_id=features.organization_id,
            submission_id=features.submission_id,
            detector_id=self.DETECTOR_ID,
            detector_version=self.DETECTOR_VERSION,
            signal_type=SignalType.PEER_DEVIATION.value,
            finding_key=f"peer_deviation_{metric_name}",
            affected_record_ids=affected_ids,
            basis_identity=f"{metric_name}:{subject_val:.4f}:{peer_med:.4f}",
        )

        return SupervisorySignal(
            signal_id=signal_id,
            organization_id=features.organization_id,
            submission_id=features.submission_id,
            signal_type=SignalType.PEER_DEVIATION,
            severity=SignalSeverity.MEDIUM,
            title=f"Peer Cohort Deviation in {metric_name.replace('_', ' ').title()}",
            short_rationale=short,
            detailed_explanation=detailed,
            basis={
                "metric_name": metric_name,
                "subject_value": round(subject_val, 4),
                "peer_median": round(peer_med, 4),
                "peer_mad": round(peer_mad, 4),
                "deviation": round(deviation, 4),
                "cohort_size": len(cohort_vals),
                "peer_population_size": len(cohort_vals),
                "cohort_description": cohort_desc,
            },
            observed_value=round(subject_val, 4),
            expected_value=round(peer_med, 4),
            confidence=0.85,
            evidence_references=all_refs,
            affected_record_ids=affected_ids,
            detector_id=self.DETECTOR_ID,
            detector_version=self.DETECTOR_VERSION,
            investigation_questions=questions,
            generated_at_utc=datetime.now(UTC),
        )
