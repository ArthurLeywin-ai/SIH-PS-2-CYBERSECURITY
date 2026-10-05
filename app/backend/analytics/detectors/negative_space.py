"""Negative Space Analytics Detector.

Identifies meaningful absence or missing expected evidence patterns (ARCHITECTURE.md §12):
- Expected evidence family absent from a submission
- Declared record counts inconsistent with actual submitted records
- Critical assets declared without active monitoring coverage
- Cautious, objective phrasing strictly adhered to
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.backend.analytics.evidence import EvidenceResolver
from app.backend.analytics.explanations import format_negative_space_explanation
from app.backend.analytics.features import EntityPeriodFeatures
from app.backend.analytics.models import (
    EvidenceReference,
    EvidenceRole,
    SignalSeverity,
    SignalType,
    SupervisorySignal,
)


class NegativeSpaceDetector:
    """Evaluates the meaningful absence of expected operational evidence."""

    DETECTOR_ID = "DET-NEGATIVE-SPACE"
    DETECTOR_VERSION = "1.0.0"

    def __init__(self, resolver: EvidenceResolver | None = None) -> None:
        self.resolver = resolver or EvidenceResolver()

    def detect(self, features: EntityPeriodFeatures) -> list[SupervisorySignal]:
        """Execute negative-space analyses."""
        signals: list[SupervisorySignal] = []

        # 1. Missing Expected Evidence Families
        sig_fam = self._check_missing_expected_families(features)
        if sig_fam:
            signals.extend(sig_fam)

        # 2. Declared vs Actual Record Count Inconsistency
        sig_counts = self._check_declared_vs_actual_counts(features)
        if sig_counts:
            signals.extend(sig_counts)

        # 3. Critical Assets Without Monitoring Coverage
        sig_assets = self._check_unmonitored_critical_assets(features)
        if sig_assets:
            signals.append(sig_assets)

        return signals

    def _check_missing_expected_families(self, features: EntityPeriodFeatures) -> list[SupervisorySignal]:
        signals: list[SupervisorySignal] = []

        # If cases exist (> 0), investigations are expected to be present
        if features.case_count > 0 and features.investigation_count == 0:
            short, detailed, questions = format_negative_space_explanation(
                target_scope="investigations",
                expected_rule="Entities with active cases are expected to provide investigative documentation.",
                observed_state="0 investigation records present while cases exist",
                context_details=f"{features.case_count} cases submitted",
            )
            signals.append(
                SupervisorySignal(
                    signal_id=str(uuid.uuid4()),
                    organization_id=features.organization_id,
                    submission_id=features.submission_id,
                    signal_type=SignalType.NEGATIVE_SPACE,
                    severity=SignalSeverity.HIGH,
                    title="Absence of Expected Investigation Evidence Family",
                    short_rationale=short,
                    detailed_explanation=detailed,
                    basis={
                        "missing_family": "investigations",
                        "case_count": features.case_count,
                        "observed_investigation_count": 0,
                    },
                    observed_value=0,
                    expected_value=f">= 1 (for {features.case_count} cases)",
                    confidence=0.92,
                    evidence_references=[
                        self.resolver.build_reference(
                            record_id=str(c.case_id),
                            evidence_family="cases",
                            role=EvidenceRole.MISSING_EXPECTATION,
                            description=f"Case {c.case_id} lacks investigation counterpart.",
                        )
                        for c in features.cases[:5]
                    ],
                    affected_record_ids=[str(c.case_id) for c in features.cases],
                    detector_id=self.DETECTOR_ID,
                    detector_version=self.DETECTOR_VERSION,
                    investigation_questions=questions,
                    generated_at_utc=datetime.now(UTC),
                )
            )

        # If assets exist (> 0), monitoring coverage declarations are expected
        if features.asset_count > 0 and len(features.coverage) == 0:
            short, detailed, questions = format_negative_space_explanation(
                target_scope="monitoring_coverage",
                expected_rule="Entities with declared IT assets are expected to declare monitoring coverage status.",
                observed_state="0 monitoring coverage records provided",
                context_details=f"{features.asset_count} assets declared in asset inventory",
            )
            signals.append(
                SupervisorySignal(
                    signal_id=str(uuid.uuid4()),
                    organization_id=features.organization_id,
                    submission_id=features.submission_id,
                    signal_type=SignalType.NEGATIVE_SPACE,
                    severity=SignalSeverity.MEDIUM,
                    title="Absence of Expected Monitoring Coverage Declarations",
                    short_rationale=short,
                    detailed_explanation=detailed,
                    basis={
                        "missing_family": "monitoring_coverage",
                        "asset_count": features.asset_count,
                        "observed_coverage_count": 0,
                    },
                    observed_value=0,
                    expected_value=f">= 1 (for {features.asset_count} assets)",
                    confidence=0.88,
                    evidence_references=[
                        self.resolver.build_reference(
                            record_id=str(a.asset_id),
                            evidence_family="assets",
                            role=EvidenceRole.MISSING_EXPECTATION,
                            description=f"Asset {a.asset_id} has no monitoring coverage declaration.",
                        )
                        for a in features.assets[:5]
                    ],
                    affected_record_ids=[str(a.asset_id) for a in features.assets],
                    detector_id=self.DETECTOR_ID,
                    detector_version=self.DETECTOR_VERSION,
                    investigation_questions=questions,
                    generated_at_utc=datetime.now(UTC),
                )
            )

        # Core operational families check
        core_families = {"assets", "alerts"}
        observed_fams = set(features.actual_family_counts.keys()) | set(features.declared_family_counts.keys())
        if observed_fams:
            for missing_core in sorted(core_families - observed_fams):
                short, detailed, questions = format_negative_space_explanation(
                    target_scope=f"{missing_core} evidence family",
                    expected_rule="Submissions are expected to include foundational asset inventory and telemetry.",
                    observed_state=f"No {missing_core} records were declared or observed in the submission",
                )
                signals.append(
                    SupervisorySignal(
                        signal_id=str(uuid.uuid4()),
                        organization_id=features.organization_id,
                        submission_id=features.submission_id,
                        signal_type=SignalType.NEGATIVE_SPACE,
                        severity=SignalSeverity.HIGH,
                        title=f"Missing Expected Evidence Family: {missing_core.capitalize()}",
                        short_rationale=short,
                        detailed_explanation=detailed,
                        basis={"missing_family": missing_core},
                        observed_value=0,
                        expected_value=">= 1",
                        confidence=0.95,
                        detector_id=self.DETECTOR_ID,
                        detector_version=self.DETECTOR_VERSION,
                        investigation_questions=questions,
                        generated_at_utc=datetime.now(UTC),
                    )
                )

        return signals

    def _check_declared_vs_actual_counts(self, features: EntityPeriodFeatures) -> list[SupervisorySignal]:
        signals: list[SupervisorySignal] = []

        for family, declared in features.declared_family_counts.items():
            actual = features.actual_family_counts.get(family, 0)
            if declared != actual and declared > 0:
                short, detailed, questions = format_negative_space_explanation(
                    target_scope=f"{family} record population",
                    expected_rule="Submission declaration specifies expected record count.",
                    observed_state=f"Declared {declared} records, but {actual} actual records were observed",
                )
                signals.append(
                    SupervisorySignal(
                        signal_id=str(uuid.uuid4()),
                        organization_id=features.organization_id,
                        submission_id=features.submission_id,
                        signal_type=SignalType.NEGATIVE_SPACE,
                        severity=SignalSeverity.HIGH,
                        title=f"Declared Record Count Discrepancy for {family.capitalize()}",
                        short_rationale=short,
                        detailed_explanation=detailed,
                        basis={
                            "evidence_family": family,
                            "declared_count": declared,
                            "actual_count": actual,
                            "discrepancy_delta": declared - actual,
                        },
                        observed_value=actual,
                        expected_value=declared,
                        confidence=0.98,
                        evidence_references=[],
                        affected_record_ids=[],
                        detector_id=self.DETECTOR_ID,
                        detector_version=self.DETECTOR_VERSION,
                        investigation_questions=questions,
                        generated_at_utc=datetime.now(UTC),
                    )
                )

        return signals

    def _check_unmonitored_critical_assets(self, features: EntityPeriodFeatures) -> SupervisorySignal | None:
        unmonitored = features.unmonitored_critical_asset_ids
        if not unmonitored:
            return None

        total_crit = features.critical_asset_count
        short, detailed, questions = format_negative_space_explanation(
            target_scope="critical asset monitoring coverage",
            expected_rule=(
                "Critical tier assets (Tier 0/Tier 1) are expected to possess active monitoring coverage records."
            ),
            observed_state=f"{len(unmonitored)} of {total_crit} critical assets lack monitoring coverage",
        )

        refs: list[EvidenceReference] = [
            self.resolver.build_reference(
                record_id=aid,
                evidence_family="assets",
                role=EvidenceRole.TRIGGER,
                description=f"Critical asset {aid} is not covered by any active monitoring record.",
            )
            for aid in sorted(unmonitored)[:10]
        ]

        return SupervisorySignal(
            signal_id=str(uuid.uuid4()),
            organization_id=features.organization_id,
            submission_id=features.submission_id,
            signal_type=SignalType.NEGATIVE_SPACE,
            severity=SignalSeverity.CRITICAL if len(unmonitored) >= 3 else SignalSeverity.HIGH,
            title="Critical Assets Lacking Documented Monitoring Coverage",
            short_rationale=short,
            detailed_explanation=detailed,
            basis={
                "unmonitored_critical_count": len(unmonitored),
                "total_critical_assets": total_crit,
                "unmonitored_ratio": round(len(unmonitored) / total_crit, 4) if total_crit > 0 else 0.0,
            },
            observed_value=len(unmonitored),
            expected_value=0,
            confidence=0.94,
            evidence_references=refs,
            affected_record_ids=sorted(unmonitored),
            detector_id=self.DETECTOR_ID,
            detector_version=self.DETECTOR_VERSION,
            investigation_questions=questions,
            generated_at_utc=datetime.now(UTC),
        )
