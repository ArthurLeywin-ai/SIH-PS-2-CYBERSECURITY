"""Execution Gap Analytics Detector.

Detects discrepancies where expected operational workflow progression differs from observed evidence:
- Critical/high severity alerts with no associated cases
- Cases lacking formal investigation documentation
- Premature closures without investigation or resolution
- Confirmed/severe incidents without escalation or remedial action
- Temporal inversion in lifecycle progression
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.backend.analytics.evidence import EvidenceResolver
from app.backend.analytics.explanations import format_execution_gap_explanation
from app.backend.analytics.features import EntityPeriodFeatures
from app.backend.analytics.models import (
    EvidenceReference,
    EvidenceRole,
    SignalSeverity,
    SignalType,
    SupervisorySignal,
    generate_deterministic_signal_id,
)


class ExecutionGapDetector:
    """Evaluates canonical evidence for broken or missing workflow progressions."""

    DETECTOR_ID = "DET-EXECUTION-GAP"
    DETECTOR_VERSION = "1.0.0"

    def __init__(self, resolver: EvidenceResolver | None = None) -> None:
        self.resolver = resolver or EvidenceResolver()

    def detect(self, features: EntityPeriodFeatures) -> list[SupervisorySignal]:
        """Execute deterministic execution-gap checks."""
        signals: list[SupervisorySignal] = []

        # 1. Unlinked High/Critical Severity Alerts
        sig_alerts = self._check_unlinked_critical_alerts(features)
        if sig_alerts:
            signals.append(sig_alerts)

        # 2. Cases Lacking Investigation Records
        sig_inv = self._check_cases_missing_investigation(features)
        if sig_inv:
            signals.append(sig_inv)

        # 3. Premature or Unsupported Closure
        sig_closure = self._check_unsupported_closure(features)
        if sig_closure:
            signals.append(sig_closure)

        # 4. Severe Cases Without Escalation or Action
        sig_esc = self._check_severe_cases_without_escalation_or_action(features)
        if sig_esc:
            signals.append(sig_esc)

        # 5. Temporal Inversion (Sequence Anomaly)
        sig_temp = self._check_temporal_inversion(features)
        if sig_temp:
            signals.append(sig_temp)

        return signals

    def _check_unlinked_critical_alerts(self, features: EntityPeriodFeatures) -> SupervisorySignal | None:
        unlinked = features.unlinked_critical_alert_ids
        if not unlinked:
            return None

        total_crit = features.critical_alert_count + features.high_alert_count
        short_rat, detailed_exp, questions = format_execution_gap_explanation(
            gap_type="unlinked_critical_alert",
            stage_from="high/critical severity alert",
            stage_to="case",
            observed_count=len(unlinked),
            total_eligible=total_crit,
            sample_ids=unlinked,
        )

        has_critical = any(
            (a.severity or "").upper() == "CRITICAL"
            for a in features.alerts
            if str(a.alert_id) in unlinked
        )
        severity = SignalSeverity.HIGH if has_critical else SignalSeverity.MEDIUM

        refs: list[EvidenceReference] = []
        for aid in sorted(unlinked)[:10]:
            refs.append(
                self.resolver.build_reference(
                    record_id=aid,
                    evidence_family="alerts",
                    role=EvidenceRole.TRIGGER,
                    description=f"Alert {aid} has high/critical severity but no associated case link.",
                )
            )

        signal_id = generate_deterministic_signal_id(
            organization_id=features.organization_id,
            submission_id=features.submission_id,
            detector_id=self.DETECTOR_ID,
            detector_version=self.DETECTOR_VERSION,
            signal_type=SignalType.EXECUTION_GAP.value,
            finding_key="unlinked_critical_alerts",
            affected_record_ids=sorted(unlinked),
            basis_identity=f"unlinked:{len(unlinked)}:{total_crit}",
        )

        return SupervisorySignal(
            signal_id=signal_id,
            organization_id=features.organization_id,
            submission_id=features.submission_id,
            signal_type=SignalType.EXECUTION_GAP,
            severity=severity,
            title="High-Severity Alert Without Case Progression",
            short_rationale=short_rat,
            detailed_explanation=detailed_exp,
            basis={
                "unlinked_count": len(unlinked),
                "total_high_critical_alerts": total_crit,
                "unlinked_ratio": round(len(unlinked) / total_crit, 4) if total_crit > 0 else 0.0,
                "threshold_rule": (
                    "Configured analytical expectation: high/critical alerts require documented case progression."
                ),
            },
            observed_value=len(unlinked),
            expected_value=0,
            confidence=0.95,
            evidence_references=refs,
            affected_record_ids=sorted(unlinked),
            detector_id=self.DETECTOR_ID,
            detector_version=self.DETECTOR_VERSION,
            investigation_questions=questions,
            generated_at_utc=datetime.now(UTC),
        )

    def _check_cases_missing_investigation(self, features: EntityPeriodFeatures) -> SupervisorySignal | None:
        if features.case_count == 0:
            return None

        cases_without_inv = [
            str(c.case_id)
            for c in features.cases
            if str(c.case_id) not in features.cases_with_investigation
        ]
        if not cases_without_inv:
            return None

        short_rat, detailed_exp, questions = format_execution_gap_explanation(
            gap_type="missing_investigation",
            stage_from="case",
            stage_to="investigation",
            observed_count=len(cases_without_inv),
            total_eligible=features.case_count,
            sample_ids=cases_without_inv,
        )

        refs: list[EvidenceReference] = []
        for cid in sorted(cases_without_inv)[:10]:
            refs.append(
                self.resolver.build_reference(
                    record_id=cid,
                    evidence_family="cases",
                    role=EvidenceRole.TRIGGER,
                    description=f"Case {cid} lacks corresponding investigation record in submitted scope.",
                )
            )

        signal_id = generate_deterministic_signal_id(
            organization_id=features.organization_id,
            submission_id=features.submission_id,
            detector_id=self.DETECTOR_ID,
            detector_version=self.DETECTOR_VERSION,
            signal_type=SignalType.EXECUTION_GAP.value,
            finding_key="cases_missing_investigation",
            affected_record_ids=sorted(cases_without_inv),
            basis_identity=f"missing_inv:{len(cases_without_inv)}:{features.case_count}",
        )

        return SupervisorySignal(
            signal_id=signal_id,
            organization_id=features.organization_id,
            submission_id=features.submission_id,
            signal_type=SignalType.EXECUTION_GAP,
            severity=SignalSeverity.HIGH,
            title="Case Record Lacks Investigation Documentation",
            short_rationale=short_rat,
            detailed_explanation=detailed_exp,
            basis={
                "cases_without_investigation_count": len(cases_without_inv),
                "total_cases": features.case_count,
                "missing_investigation_rate": round(len(cases_without_inv) / features.case_count, 4),
            },
            observed_value=len(cases_without_inv),
            expected_value=0,
            confidence=0.90,
            evidence_references=refs,
            affected_record_ids=sorted(cases_without_inv),
            detector_id=self.DETECTOR_ID,
            detector_version=self.DETECTOR_VERSION,
            investigation_questions=questions,
            generated_at_utc=datetime.now(UTC),
        )

    def _check_unsupported_closure(self, features: EntityPeriodFeatures) -> SupervisorySignal | None:
        unsupported: list[str] = []
        for c in features.cases:
            cid = str(c.case_id)
            is_closed = (c.status or "").upper() in {"CLOSED", "RESOLVED"} or cid in features.cases_with_closure
            if is_closed:
                has_inv = cid in features.cases_with_investigation
                has_res = cid in features.cases_with_resolution
                if not has_inv and not has_res:
                    unsupported.append(cid)

        if not unsupported:
            return None

        refs = [
            self.resolver.build_reference(
                record_id=cid,
                evidence_family="cases",
                role=EvidenceRole.TRIGGER,
                description=f"Case {cid} is closed but lacks both investigation and resolution evidence.",
            )
            for cid in sorted(unsupported)[:10]
        ]

        short = f"{len(unsupported)} cases were marked closed without supporting investigation or resolution records."
        detailed = (
            f"Supervisory audit identified {len(unsupported)} cases marked as closed in operational records "
            f"where neither investigation notes nor resolution records were provided in the submission. "
            f"Affected cases: {sorted(unsupported)[:5]}. "
            f"Validating case closure validity requires documented rationale."
        )
        questions = [
            "What criteria and approvals were used to close these cases without documented investigation?",
            "Were resolution details stored in a ticketing system outside this regulatory submission?",
        ]

        signal_id = generate_deterministic_signal_id(
            organization_id=features.organization_id,
            submission_id=features.submission_id,
            detector_id=self.DETECTOR_ID,
            detector_version=self.DETECTOR_VERSION,
            signal_type=SignalType.EXECUTION_GAP.value,
            finding_key="unsupported_closure",
            affected_record_ids=sorted(unsupported),
            basis_identity=f"unsupported:{len(unsupported)}:{features.case_count}",
        )

        return SupervisorySignal(
            signal_id=signal_id,
            organization_id=features.organization_id,
            submission_id=features.submission_id,
            signal_type=SignalType.EXECUTION_GAP,
            severity=SignalSeverity.HIGH,
            title="Unsupported Case Closure",
            short_rationale=short,
            detailed_explanation=detailed,
            basis={"unsupported_closure_count": len(unsupported), "total_cases": features.case_count},
            observed_value=len(unsupported),
            expected_value=0,
            confidence=0.92,
            evidence_references=refs,
            affected_record_ids=sorted(unsupported),
            detector_id=self.DETECTOR_ID,
            detector_version=self.DETECTOR_VERSION,
            investigation_questions=questions,
            generated_at_utc=datetime.now(UTC),
        )

    def _check_severe_cases_without_escalation_or_action(
        self, features: EntityPeriodFeatures
    ) -> SupervisorySignal | None:
        flagged: list[str] = []
        for c in features.cases:
            cid = str(c.case_id)
            if (c.severity or "").upper() in {"CRITICAL", "HIGH"}:
                has_esc = cid in features.cases_with_escalation
                has_act = cid in features.cases_with_action
                if not has_esc and not has_act:
                    flagged.append(cid)

        if not flagged:
            return None

        refs = [
            self.resolver.build_reference(
                record_id=cid,
                evidence_family="cases",
                role=EvidenceRole.TRIGGER,
                description=f"High/Critical severity case {cid} lacks escalation or containment action.",
            )
            for cid in sorted(flagged)[:10]
        ]

        short = f"{len(flagged)} high/critical cases observed without documented escalation or containment action."
        detailed = (
            f"Operational evidence review revealed that {len(flagged)} high-severity cases do not contain "
            f"corresponding escalation records or corrective action records. Under configured analytical "
            f"expectations, high-severity incidents are expected to include documented escalation or containment "
            f"actions. The submitted operational evidence does not show this progression."
        )
        questions = [
            (
                "Were containment actions executed for these high-severity incidents, and if so, "
                "where are the action logs?"
            ),
            "Was senior management or the incident response team notified via out-of-band communication?",
        ]

        signal_id = generate_deterministic_signal_id(
            organization_id=features.organization_id,
            submission_id=features.submission_id,
            detector_id=self.DETECTOR_ID,
            detector_version=self.DETECTOR_VERSION,
            signal_type=SignalType.EXECUTION_GAP.value,
            finding_key="severe_cases_without_escalation_or_action",
            affected_record_ids=sorted(flagged),
            basis_identity=f"unactioned:{len(flagged)}:{features.case_count}",
        )

        return SupervisorySignal(
            signal_id=signal_id,
            organization_id=features.organization_id,
            submission_id=features.submission_id,
            signal_type=SignalType.EXECUTION_GAP,
            severity=SignalSeverity.MEDIUM,
            title="High-Severity Case Without Escalation or Remedial Action",
            short_rationale=short,
            detailed_explanation=detailed,
            basis={"severe_cases_without_action_count": len(flagged), "total_cases": features.case_count},
            observed_value=len(flagged),
            expected_value=0,
            confidence=0.85,
            evidence_references=refs,
            affected_record_ids=sorted(flagged),
            detector_id=self.DETECTOR_ID,
            detector_version=self.DETECTOR_VERSION,
            investigation_questions=questions,
            generated_at_utc=datetime.now(UTC),
        )

    def _check_temporal_inversion(self, features: EntityPeriodFeatures) -> SupervisorySignal | None:
        inversions: list[dict[str, Any]] = []
        case_map = {str(c.case_id): c for c in features.cases}

        for clo in features.closures:
            cid = str(clo.case_id)
            c = case_map.get(cid)
            if c and c.created_at_utc and clo.closed_at_utc and clo.closed_at_utc < c.created_at_utc:
                inversions.append(
                    {
                        "case_id": cid,
                        "created_at": c.created_at_utc.isoformat(),
                        "closed_at": clo.closed_at_utc.isoformat(),
                    }
                )

        for inv in features.investigations:
            if inv.started_at_utc and inv.completed_at_utc and inv.completed_at_utc < inv.started_at_utc:
                inversions.append(
                    {
                        "investigation_id": str(inv.investigation_id),
                        "started_at": inv.started_at_utc.isoformat(),
                        "completed_at": inv.completed_at_utc.isoformat(),
                    }
                )

        if not inversions:
            return None

        affected_ids = [str(item.get("case_id") or item.get("investigation_id")) for item in inversions]
        refs = [
            self.resolver.build_reference(
                record_id=rid,
                evidence_family="closures" if "case_id" in item else "investigations",
                role=EvidenceRole.TRIGGER,
                description=f"Temporal sequence inversion observed: {item}",
            )
            for rid, item in list(zip(affected_ids, inversions, strict=False))[:10]
        ]

        short = f"{len(inversions)} records demonstrate temporal inversion (completion timestamp precedes initiation)."
        detailed = (
            f"Temporal consistency analysis detected {len(inversions)} workflow events where completion or closure "
            f"timestamps chronologically precede creation or initiation timestamps. This represents a potential "
            f"clock skew issue, backdated record entry, or logging inconsistency."
        )
        questions = [
            "Do SOC log collectors or timestamp sources experience NTP synchronization discrepancies?",
            "Were case closure dates entered retrospectively without automated system validation?",
        ]

        signal_id = generate_deterministic_signal_id(
            organization_id=features.organization_id,
            submission_id=features.submission_id,
            detector_id=self.DETECTOR_ID,
            detector_version=self.DETECTOR_VERSION,
            signal_type=SignalType.EXECUTION_GAP.value,
            finding_key="temporal_inversion",
            affected_record_ids=sorted(affected_ids),
            basis_identity=f"inversions:{len(inversions)}",
        )

        return SupervisorySignal(
            signal_id=signal_id,
            organization_id=features.organization_id,
            submission_id=features.submission_id,
            signal_type=SignalType.EXECUTION_GAP,
            severity=SignalSeverity.HIGH,
            title="Temporal Ordering Inversion in Workflow Execution",
            short_rationale=short,
            detailed_explanation=detailed,
            basis={"temporal_inversion_count": len(inversions), "inversions": inversions[:5]},
            observed_value=len(inversions),
            expected_value=0,
            confidence=0.98,
            evidence_references=refs,
            affected_record_ids=sorted(affected_ids),
            detector_id=self.DETECTOR_ID,
            detector_version=self.DETECTOR_VERSION,
            investigation_questions=questions,
            generated_at_utc=datetime.now(UTC),
        )
