"""Entity-Level Supervisory Attention Aggregator.

Combines independent analytical signals into an explainable, bounded, deterministic summary:
- Deterministic scoring function decomposable into contributing signals (ARCHITECTURE.md §13)
- Bounded 0.0 - 100.0 scale clearly defined as Supervisory Attention Indicator (not risk probability)
- Decomposable formula:
    * Severity contribution (max 70.0 pts): weighted sum of signals by severity and confidence
    * Diversity contribution (max 15.0 pts): breadth of distinct supervisory dimensions
    * Data-quality gap contribution (max 15.0 pts): missing operational documentation ratio
- Categorical attention bands: LOW (<25), MODERATE (25-49), ELEVATED (50-74), HIGH (>=75)
- Deterministic UUID5 summary identifier
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.backend.analytics.models import (
    SignalSeverity,
    SignalType,
    SupervisoryAttentionSummary,
    SupervisorySignal,
    generate_deterministic_summary_id,
)

# Explicit, documented severity weights
SEVERITY_WEIGHTS: dict[SignalSeverity, float] = {
    SignalSeverity.CRITICAL: 20.0,
    SignalSeverity.HIGH: 12.0,
    SignalSeverity.MEDIUM: 6.0,
    SignalSeverity.LOW: 2.0,
}

MAX_SEVERITY_CONTRIBUTION: float = 70.0
MAX_DIVERSITY_CONTRIBUTION: float = 15.0
MAX_DATA_QUALITY_CONTRIBUTION: float = 15.0


class AttentionAggregator:
    """Aggregates supervisory signals for an entity into a consolidated attention indicator."""

    @staticmethod
    def aggregate(
        organization_id: str,
        signals: list[SupervisorySignal],
        submission_id: str | None = None,
    ) -> SupervisoryAttentionSummary:
        """Deterministically synthesize individual signals into an attention summary.

        Formula:
            Severity Component (C_sev) = min(70.0, sum(weight[severity] * confidence))
            Diversity Component (C_div) = min(15.0, (distinct_signal_types - 1) * 3.75) if total > 0 else 0.0
            Data Quality Component (C_dq) = min(15.0, round((negative_space_signals / total_signals) * 15.0, 2))
            Bounded Attention Score = min(100.0, max(0.0, round(C_sev + C_div + C_dq, 2)))
        """
        total_signals = len(signals)

        # Count by type
        by_type: dict[str, int] = {st.value: 0 for st in SignalType}
        for sig in signals:
            st_val = sig.signal_type.value if isinstance(sig.signal_type, SignalType) else str(sig.signal_type)
            by_type[st_val] = by_type.get(st_val, 0) + 1

        # Count by severity and compute weighted severity contribution
        by_sev: dict[str, int] = {ss.value: 0 for ss in SignalSeverity}
        raw_severity_sum = 0.0
        for sig in signals:
            sev = sig.severity if isinstance(sig.severity, SignalSeverity) else SignalSeverity(str(sig.severity))
            by_sev[sev.value] = by_sev.get(sev.value, 0) + 1
            w = SEVERITY_WEIGHTS.get(sev, 4.0)
            raw_severity_sum += w * float(sig.confidence)

        c_sev = min(MAX_SEVERITY_CONTRIBUTION, round(raw_severity_sum, 2))

        # Diversity contribution: multi-dimensional breadth across the 5 canonical signal types
        distinct_types = sum(1 for cnt in by_type.values() if cnt > 0)
        c_div = 0.0
        if total_signals > 0 and distinct_types > 1:
            c_div = min(MAX_DIVERSITY_CONTRIBUTION, round((distinct_types - 1) * 3.75, 2))

        # Data-quality / negative space gap ratio
        neg_count = by_type.get(SignalType.NEGATIVE_SPACE.value, 0)
        data_quality_gap_index = (neg_count / total_signals) if total_signals > 0 else 0.0
        c_dq = min(MAX_DATA_QUALITY_CONTRIBUTION, round(data_quality_gap_index * MAX_DATA_QUALITY_CONTRIBUTION, 2))

        # Transparent score decomposition
        raw_score = round(c_sev + c_div + c_dq, 2)
        final_score = min(100.0, max(0.0, raw_score))

        score_decomposition = {
            "severity_contribution": c_sev,
            "diversity_contribution": c_div,
            "data_quality_gap_contribution": c_dq,
            "raw_score": raw_score,
            "bounded_score": final_score,
        }

        # Categorical attention bands
        if final_score >= 75.0:
            band = "HIGH"
        elif final_score >= 50.0:
            band = "ELEVATED"
        elif final_score >= 25.0:
            band = "MODERATE"
        else:
            band = "LOW"

        # Deterministic sorting for strongest signals
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
                f"Score decomposition: severity={c_sev:.1f}, diversity={c_div:.1f}, data_quality={c_dq:.1f}. "
                f"Critical/High severity items: {by_sev.get('CRITICAL', 0) + by_sev.get('HIGH', 0)}."
            )

        summary_id = generate_deterministic_summary_id(
            organization_id=organization_id,
            submission_id=submission_id,
            signal_ids=[s.signal_id for s in sorted_signals],
        )

        return SupervisoryAttentionSummary(
            summary_id=summary_id,
            organization_id=organization_id,
            submission_id=submission_id,
            total_signals=total_signals,
            signals_by_type=by_type,
            signals_by_severity=by_sev,
            attention_score=final_score,
            attention_band=band,
            strongest_signals=strongest,
            data_quality_gap_index=round(data_quality_gap_index, 4),
            summary_rationale=rationale,
            score_decomposition=score_decomposition,
            generated_at_utc=datetime.now(UTC),
        )
