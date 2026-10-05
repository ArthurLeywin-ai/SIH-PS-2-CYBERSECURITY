"""Supervisory Analytics Engine.

Orchestrates:
Feature Extraction -> Detectors Execution -> Signal Correlation -> Attention Synthesis -> Optional Persistence.

Enforces:
- 100% Deterministic execution and ordering
- Traceability back to operational evidence
- Strict isolation from ground-truth / scenario metadata
- Isolated detector failure handling (ARCHITECTURE.md §8.1)
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from typing import Any

from app.backend.analytics.detectors.anomalies import StatisticalAnomalyDetector
from app.backend.analytics.detectors.attention import AttentionAggregator
from app.backend.analytics.detectors.execution_gaps import ExecutionGapDetector
from app.backend.analytics.detectors.negative_space import NegativeSpaceDetector
from app.backend.analytics.detectors.operational_drift import OperationalDriftDetector
from app.backend.analytics.detectors.peer_comparison import PeerComparisonDetector
from app.backend.analytics.evidence import EvidenceResolver
from app.backend.analytics.features import EntityPeriodFeatures
from app.backend.analytics.models import (
    AnalyticsRunResult,
    SignalSeverity,
    SupervisoryAttentionSummary,
    SupervisorySignal,
)
from app.backend.analytics.repository import AnalyticsRepository
from app.backend.errors import NotFoundError
from app.backend.logging import get_logger
from sqlalchemy.orm import Session

logger = get_logger("analytics.engine")

SEV_ORDER = {
    SignalSeverity.CRITICAL: 4,
    SignalSeverity.HIGH: 3,
    SignalSeverity.MEDIUM: 2,
    SignalSeverity.LOW: 1,
}


class SupervisoryAnalyticsEngine:
    """Production-grade supervisory analytics engine for SAT-SA."""

    def __init__(self, session: Session | None = None) -> None:
        self.session = session
        self.resolver = EvidenceResolver(session)
        self.repo = AnalyticsRepository(session) if session else None

        # Instantiate modular detectors
        self.exec_detector = ExecutionGapDetector(self.resolver)
        self.neg_detector = NegativeSpaceDetector(self.resolver)
        self.anom_detector = StatisticalAnomalyDetector(self.resolver)
        self.peer_detector = PeerComparisonDetector(self.resolver)
        self.drift_detector = OperationalDriftDetector(self.resolver)

    def analyze_features(
        self,
        features: EntityPeriodFeatures,
        peer_features: list[EntityPeriodFeatures] | None = None,
        prior_features_list: list[EntityPeriodFeatures] | None = None,
        organization: Any = None,
        all_organizations: list[Any] | None = None,
    ) -> tuple[list[SupervisorySignal], SupervisoryAttentionSummary]:
        """Run all detectors deterministically over in-memory feature set."""
        signals: list[SupervisorySignal] = []

        # 1. Execution Gaps
        try:
            sig_exec = self.exec_detector.detect(features)
            signals.extend(sig_exec)
        except Exception as err:
            logger.error("Detector '%s' failed: %s", self.exec_detector.DETECTOR_ID, err, exc_info=True)

        # 2. Negative Space
        try:
            sig_neg = self.neg_detector.detect(features)
            signals.extend(sig_neg)
        except Exception as err:
            logger.error("Detector '%s' failed: %s", self.neg_detector.DETECTOR_ID, err, exc_info=True)

        # 3. Statistical Anomalies
        try:
            hist_closures = (
                [pf.case_closure_rate for pf in prior_features_list if pf.case_count >= 5]
                if prior_features_list
                else None
            )
            hist_durs: list[float] = []
            if prior_features_list:
                for pf in prior_features_list:
                    hist_durs.extend(pf.investigation_durations_hours)
            hist_dens = (
                [
                    (pf.alert_count / pf.asset_count)
                    for pf in prior_features_list
                    if pf.asset_count > 0 and pf.alert_count >= 20
                ]
                if prior_features_list
                else None
            )

            sig_anom = self.anom_detector.detect(
                features,
                historical_closure_rates=hist_closures,
                historical_durations=hist_durs if hist_durs else None,
                historical_densities=hist_dens,
            )
            signals.extend(sig_anom)
        except Exception as err:
            logger.error("Detector '%s' failed: %s", self.anom_detector.DETECTOR_ID, err, exc_info=True)

        # 4. Peer Comparison
        if peer_features and organization:
            try:
                sig_peer = self.peer_detector.detect(
                    features=features,
                    organization=organization,
                    peer_features=peer_features,
                    all_organizations=all_organizations,
                )
                signals.extend(sig_peer)
            except Exception as err:
                logger.error("Detector '%s' failed: %s", self.peer_detector.DETECTOR_ID, err, exc_info=True)

        # 5. Operational Drift
        if prior_features_list:
            try:
                sig_drift = self.drift_detector.detect(
                    current_features=features,
                    prior_features_list=prior_features_list,
                )
                signals.extend(sig_drift)
            except Exception as err:
                logger.error("Detector '%s' failed: %s", self.drift_detector.DETECTOR_ID, err, exc_info=True)

        # 6. Deterministic Sort
        def sort_key(s: SupervisorySignal) -> tuple[int, float, str, str]:
            s_sev = s.severity if isinstance(s.severity, SignalSeverity) else SignalSeverity(str(s.severity))
            return (-SEV_ORDER.get(s_sev, 0), -s.confidence, s.title, s.signal_id)

        sorted_signals = sorted(signals, key=sort_key)

        # 7. Aggregate Entity Attention
        attention_summary = AttentionAggregator.aggregate(
            organization_id=features.organization_id,
            signals=sorted_signals,
            submission_id=features.submission_id,
        )

        return sorted_signals, attention_summary

    def analyze_organization(self, organization_id: str, persist: bool = True) -> AnalyticsRunResult:
        """Analyze all operational evidence for an organization."""
        return self.run_for_organization(organization_id=organization_id, submission_id=None, persist=persist)

    def analyze_submission(self, submission_id: str, persist: bool = True) -> AnalyticsRunResult:
        """Analyze evidence for a specific submission."""
        if not self.repo:
            raise RuntimeError("Database repository is required to analyze submission.")
        sub = self.repo.get_submission(submission_id)
        if not sub:
            raise NotFoundError(f"Submission '{submission_id}' not found")
        return self.run_for_organization(
            organization_id=str(sub.organization_id), submission_id=submission_id, persist=persist
        )

    def run_for_organization(
        self,
        organization_id: str,
        submission_id: str | None = None,
        persist: bool = True,
    ) -> AnalyticsRunResult:
        """Run full analytics pipeline against canonical database for an organization."""
        if not self.repo or not self.session:
            raise RuntimeError("Database session is required to execute run_for_organization.")

        start_time = time.perf_counter()
        run_id = str(uuid.uuid4())

        org = self.repo.get_organization(organization_id)
        if not org:
            raise NotFoundError(f"Organization '{organization_id}' not found")

        # Load entity features
        features = self.repo.get_entity_features(organization_id, submission_id)

        # Load peer features
        peer_features = self.repo.get_peer_features(exclude_org_id=organization_id)
        all_orgs = self.repo.list_all_organizations()

        # Load historical submissions for drift
        hist_subs = self.repo.get_historical_submissions(organization_id)
        prior_features_list: list[EntityPeriodFeatures] = []
        for sub in hist_subs:
            if str(sub.submission_id) != str(submission_id):
                prior_features_list.append(
                    self.repo.get_entity_features(organization_id, sub.submission_id)
                )

        # Execute analysis
        signals, attention_summary = self.analyze_features(
            features=features,
            peer_features=peer_features,
            prior_features_list=prior_features_list,
            organization=org,
            all_organizations=all_orgs,
        )

        # Persist signals & attention summary if requested
        if persist:
            self.repo.save_signals(signals)
            self.repo.save_attention_summary(attention_summary)
            self.session.commit()

        duration = round(time.perf_counter() - start_time, 4)
        logger.info(
            "Analytics completed for org %s (run %s): %d signals, attention score %.1f (%s) in %.2fs",
            organization_id,
            run_id,
            len(signals),
            attention_summary.attention_score,
            attention_summary.attention_band,
            duration,
        )

        return AnalyticsRunResult(
            run_id=run_id,
            organization_id=organization_id,
            submission_id=submission_id,
            signals=signals,
            attention_summary=attention_summary,
            duration_seconds=duration,
            generated_at_utc=datetime.now(UTC),
        )
