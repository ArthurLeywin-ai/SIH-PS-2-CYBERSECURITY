"""Entity-Level Supervisory Attention Aggregator.

Combines independent analytical signals into an explainable, bounded, deterministic summary:
- Deterministic scoring function decomposable into contributing signals
- Categorical attention bands: LOW, MODERATE, ELEVATED, HIGH
- Data-quality and evidence-gap indicator ratio
- Identifies top-priority strongest signals for regulatory focus
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.backend.analytics.models import (
    SignalSeverity,
    SignalType,
    SupervisoryAttentionSummary,
    SupervisorySignal,
)

SEVERITY_WEIGHTS: dict[SignalSeverity, float] = {
    SignalSeverity.CRITICAL: 25.0,
    SignalSeverity.HIGH: 15.0,
    SignalSeverity.MEDIUM: 8.0,
    SignalSeverity.LOW: 3.0,
}


class AttentionAggregator:
    """Aggregates supervisory signals for an entity into a consolidated attention indicator."""

    @staticmethod
    def aggregate(
        organization_id: str,
        signals: list[SupervisorySignal],
        submission_id: str | None = None,
    ) -> SupervisoryAttentionSummary:
        """Deterministically synthesize individual signals into an attention summary."""
        total_signals = len(signals)

        # Count by type
        by_type: dict[str, int] = {st.value: 0 for st in SignalType}
        for sig in signals:
            st_val = sig.signal_type.value if isinstance(sig.signal_type, SignalType) else str(sig.signal_type)
            by_type[st_val] = by_type.get(st_val, 0) + 1

        # Count by severity
        by_sev: dict[str, int] = {ss.value: 0 for ss in SignalSeverity}
        raw_score = 0.0
        for sig in signals:
            sev = sig.severity if isinstance(sig.severity, SignalSeverity) else SignalSeverity(str(sig.severity))
            by_sev[sev.value] = by_sev.get(sev.value, 0) + 1
            raw_score += SEVERITY_WEIGHTS.get(sev, 5.0)

        # Diversity factor: entities with multi-dimensional concerns receive an additional breadth adjustment
        distinct_types = sum(1 for cnt in by_type.values() if cnt > 0)
        diversity_adjustment = min(10.0, distinct_types * 2.0) if total_signals > 0 else 0.0

        # Bounded between 0.0 and 100.0
        final_score = min(100.0, raw_score + diversity_adjustment)

        # Attention band
        if final_score >= 75.0:
            band = "HIGH"
        elif final_score >= 50.0:
            band = "ELEVATED"
        elif final_score >= 25.0:
            band = "MODERATE"
        else:
            band = "LOW"

        # Data-quality / negative space gap ratio
        neg_count = by_type.get(SignalType.NEGATIVE_SPACE.value, 0)
        data_quality_gap_index = (neg_count / total_signals) if total_signals > 0 else 0.0

        # Deterministic sorting for strongest signals: highest severity first, then confidence desc, then title asc
        sev_rank = {
            SignalSeverity.CRITICAL: 4,
            SignalSeverity.HIGH: 3,
            SignalSeverity.MEDIUM: 2,
            SignalSeverity.LOW: 1,
        }

        def sort_key(s: SupervisorySignal) -> tuple[int, float, str, str]:
            s_sev = s.severity if isinstance(s.severity, SignalSeverity) else SignalSeverity(str(s.severity))
            return (-sev_rank.get(s_sev, 0), -s.confidence, s.title, s.signal_id)

        sorted_signals = sorted(signals, key=sort_key)
        strongest = sorted_signals[:5]

        # Explainable summary rationale
        if total_signals == 0:
            rationale = "No adverse supervisory signals or operational documentation gaps were observed."
        else:
            top_types = [st for st, count in sorted(by_type.items(), key=lambda x: -x[1]) if count > 0]
            top_str = ", ".join(t.replace("_", " ").lower() for t in top_types[:3])
            rationale = (
                f"Generated {total_signals} operational signals indicating {band.lower()} "
                f"supervisory attention priority (score: {final_score:.1f}/100). "
                f"Primary signal drivers include {top_str}. "
                f"Critical/High severity items: {by_sev.get('CRITICAL', 0) + by_sev.get('HIGH', 0)}."
            )

        return SupervisoryAttentionSummary(
            summary_id=str(uuid.uuid4()),
            organization_id=organization_id,
            submission_id=submission_id,
            total_signals=total_signals,
            signals_by_type=by_type,
            signals_by_severity=by_sev,
            attention_score=final_score,
            attention_band=band,
            strongest_signals=strongest,
            data_quality_gap_index=data_quality_gap_index,
            summary_rationale=rationale,
            generated_at_utc=datetime.now(UTC),
        )
