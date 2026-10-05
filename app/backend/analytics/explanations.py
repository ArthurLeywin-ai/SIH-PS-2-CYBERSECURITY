"""Standardized explainability, neutral rationale formatting, and examiner questions.

Implements guidelines from ARCHITECTURE.md §12.3, §15.2:
- Cautious, evidence-grounded supervisory language
- Strictly avoids asserting wrongdoing or unobserved intent
- Frames signals as 'observed evidence patterns requiring examiner attention'
- Supplies concrete investigation questions for regulatory examiners
"""

from __future__ import annotations


def format_execution_gap_explanation(
    gap_type: str,
    stage_from: str,
    stage_to: str,
    observed_count: int,
    total_eligible: int,
    sample_ids: list[str],
) -> tuple[str, str, list[str]]:
    """Format explanation and investigation questions for execution gaps."""
    short = (
        f"{observed_count} of {total_eligible} {stage_from} records lack corresponding {stage_to} "
        f"evidence in submitted operational data."
    )

    id_preview = ", ".join(sample_ids[:5])
    if len(sample_ids) > 5:
        id_preview += f" ... (+{len(sample_ids) - 5} more)"

    detailed = (
        f"Operational workflow progression analysis observed that {observed_count} out of {total_eligible} "
        f"eligible {stage_from} records do not possess linked or matching {stage_to} documentation in the submitted "
        f"evidence package. Under configured analytical expectations, high-severity alerts and confirmed incidents are "
        f"expected to progress through formal triage, investigation, and disposition stages. "
        f"Affected records: [{id_preview}]. "
        f"This finding represents an observed documentation/workflow gap and warrants examiner inquiry."
    )

    questions = [
        f"Can the entity provide operational records demonstrating how these {stage_from} items were dispositioned?",
        f"Were corresponding {stage_to} records created in local systems but omitted from this regulatory submission?",
        (
            f"Does the entity operate an approved policy exception or automated rule explaining the absence "
            f"of formal {stage_to} steps?"
        ),
    ]

    return short, detailed, questions


def format_negative_space_explanation(
    target_scope: str,
    expected_rule: str,
    observed_state: str,
    context_details: str | None = None,
) -> tuple[str, str, list[str]]:
    """Format explanation and investigation questions for negative-space absence signals (ARCHITECTURE.md §12.3)."""
    short = f"Expected evidence for '{target_scope}' was not observed in submitted scope ({observed_state})."

    detailed = (
        f"Expected evidence was not found in the submitted scope for '{target_scope}'. "
        f"Basis of expectation: {expected_rule}. Current observation: {observed_state}. "
    )
    if context_details:
        detailed += f"Additional context: {context_details}. "
    detailed += (
        "Under configured analytical expectations, the absence of submitted evidence indicates an "
        "evidence gap requiring examiner verification, rather than conclusive proof that the operational activity "
        "did not occur."
    )

    questions = [
        f"Why was evidence for '{target_scope}' absent from the submission for this reporting period?",
        (
            "Are supporting operational logs or reports maintained in external systems not covered "
            "by the current intake pipeline?"
        ),
        "Can the entity produce audit logs verifying whether the expected operational activity was executed?",
    ]

    return short, detailed, questions


def format_statistical_anomaly_explanation(
    metric_name: str,
    observed_val: float | int,
    baseline_val: float | int,
    baseline_method: str,
    deviation: float | str,
    direction: str = "above",
) -> tuple[str, str, list[str]]:
    """Format explanation and investigation questions for statistical anomalies."""
    short = (
        f"Metric '{metric_name}' observed value ({observed_val}) is significantly {direction} "
        f"baseline reference ({baseline_val})."
    )

    detailed = (
        f"Deterministic statistical anomaly detection identified an operational outlier on '{metric_name}'. "
        f"The entity's observed value was {observed_val}, compared against a baseline reference of {baseline_val} "
        f"computed using {baseline_method} (measured deviation: {deviation}). "
        f"Significant divergence from established operational patterns may indicate shifts in detection coverage, "
        f"workflow bottlenecks, or reporting variations."
    )

    questions = [
        f"What operational or technological factors explain the divergence in '{metric_name}' during this period?",
        "Were there underlying changes in sensor configuration, staffing levels, or alert tuning during the period?",
        "Has the entity verified that data extraction queries remained consistent with prior periods?",
    ]

    return short, detailed, questions


def format_peer_deviation_explanation(
    metric_name: str,
    subject_val: float | int,
    peer_median: float | int,
    peer_cohort_desc: str,
    cohort_size: int,
    deviation: float | str,
) -> tuple[str, str, list[str]]:
    """Format explanation and investigation questions for peer cohort deviations."""
    short = (
        f"Entity metric '{metric_name}' ({subject_val}) deviates from matched peer cohort median ({peer_median})."
    )

    detailed = (
        f"Comparative cohort analysis evaluated the subject entity against a peer cohort of {cohort_size} "
        f"regulated entities with matching operational profiles ({peer_cohort_desc}). "
        f"On metric '{metric_name}', the entity recorded {subject_val}, whereas the peer cohort median "
        f"was {peer_median} (deviation: {deviation}). "
        f"Peer comparison serves as supervisory context to identify distinctive operational postures, "
        f"not evidence of non-compliance."
    )

    questions = [
        (
            f"Does the entity's operating model or infrastructure explain the observed variance on '{metric_name}' "
            f"compared to peer institutions?"
        ),
        "Are entity-specific operational definitions or categorization practices driving the numerical variance?",
    ]

    return short, detailed, questions


def format_operational_drift_explanation(
    metric_name: str,
    current_val: float | int,
    baseline_val: float | int,
    current_period: str,
    baseline_period: str,
    pct_change: float,
) -> tuple[str, str, list[str]]:
    """Format explanation and investigation questions for operational drift across submissions."""
    direction = "increase" if pct_change >= 0 else "decrease"
    short = (
        f"Operational drift observed in '{metric_name}': {abs(pct_change):.1f}% {direction} from "
        f"period {baseline_period} to {current_period}."
    )

    detailed = (
        f"Temporal trend analysis identified operational drift in '{metric_name}'. "
        f"The entity recorded {current_val} in reporting period '{current_period}', shifting from {baseline_val} in "
        f"prior period '{baseline_period}' (change: {pct_change:+.1f}%). "
        f"Substantial period-over-period drift suggests notable changes in threat environment, internal controls, "
        f"or data collection."
    )

    questions = [
        (
            f"What organizational, architectural, or procedural changes occurred between '{baseline_period}' "
            f"and '{current_period}' to cause this shift in '{metric_name}'?"
        ),
        "Was this operational shift anticipated by SOC leadership, and are compensating controls in place?",
    ]

    return short, detailed, questions
