"""Unit tests for M7 supervisory analytics detectors."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.backend.analytics.detectors.anomalies import StatisticalAnomalyDetector
from app.backend.analytics.detectors.attention import AttentionAggregator
from app.backend.analytics.detectors.execution_gaps import ExecutionGapDetector
from app.backend.analytics.detectors.negative_space import NegativeSpaceDetector
from app.backend.analytics.detectors.operational_drift import OperationalDriftDetector
from app.backend.analytics.detectors.peer_comparison import PeerComparisonDetector
from app.backend.analytics.evidence import EvidenceResolver
from app.backend.analytics.features import EntityPeriodFeatures
from app.backend.analytics.models import (
    SignalSeverity,
    SignalType,
    SupervisorySignal,
)
from app.backend.persistence.models import (
    AlertModel,
    AssetModel,
    CaseModel,
    ClosureModel,
    InvestigationModel,
    OrganizationModel,
)


def _make_features(org_id: str = "org-test", sub_id: str = "sub-test", **kwargs) -> EntityPeriodFeatures:
    """Helper to build EntityPeriodFeatures with default values."""
    feat = EntityPeriodFeatures(organization_id=org_id, submission_id=sub_id)
    for k, v in kwargs.items():
        setattr(feat, k, v)
    return feat


# ---------------------------------------------------------------------------
# 1. Execution Gap Detector Tests
# ---------------------------------------------------------------------------


def test_execution_gap_clean_workflow():
    """When workflow is fully documented and progressing, zero execution gap signals are generated."""
    resolver = EvidenceResolver(session=None)
    detector = ExecutionGapDetector(resolver)

    features = _make_features(
        unlinked_critical_alert_ids=[],
        case_count=5,
        cases_with_investigation={"cas-1", "cas-2", "cas-3", "cas-4", "cas-5"},
        cases=[
            CaseModel(
                case_id=f"cas-{i}",
                organization_id="org-test",
                case_type="INCIDENT",
                severity="LOW",
                status="CLOSED",
                disposition="RESOLVED",
                created_at_utc=datetime.now(UTC),
            )
            for i in range(1, 6)
        ],
        cases_with_closure={"cas-1", "cas-2", "cas-3", "cas-4", "cas-5"},
    )

    signals = detector.detect(features)
    assert signals == []


def test_execution_gap_unlinked_critical_alerts():
    """Unlinked critical alerts generate an EXECUTION_GAP signal with affected record IDs."""
    resolver = EvidenceResolver(session=None)
    detector = ExecutionGapDetector(resolver)

    now = datetime.now(UTC)
    alerts = [
        AlertModel(
            alert_id="alt-crit-1",
            organization_id="org-test",
            asset_id="ast-1",
            alert_category="MALWARE",
            severity="CRITICAL",
            status="NEW",
            disposition="ESCALATED",
            summary="Ransomware detected",
            created_at_utc=now,
        ),
        AlertModel(
            alert_id="alt-crit-2",
            organization_id="org-test",
            asset_id="ast-1",
            alert_category="EXPLOITATION",
            severity="HIGH",
            status="NEW",
            disposition="INVESTIGATING",
            summary="Exploit attempt",
            created_at_utc=now,
        ),
    ]

    features = _make_features(
        alert_count=2,
        critical_alert_count=1,
        high_alert_count=1,
        alerts=alerts,
        unlinked_critical_alert_ids=["alt-crit-1", "alt-crit-2"],
    )

    signals = detector.detect(features)
    assert len(signals) == 1
    sig = signals[0]
    assert sig.signal_type == SignalType.EXECUTION_GAP
    assert sig.severity == SignalSeverity.HIGH
    assert "alt-crit-1" in sig.affected_record_ids
    assert "alt-crit-2" in sig.affected_record_ids
    assert len(sig.investigation_questions) > 0


def test_execution_gap_temporal_inversion():
    """Cases closed before they were created trigger a temporal inversion signal."""
    resolver = EvidenceResolver(session=None)
    detector = ExecutionGapDetector(resolver)

    t2 = datetime.now(UTC)
    t1 = t2 - timedelta(hours=2)

    # Case created at t2, but closure timestamp is t1!
    cases = [
        CaseModel(
            case_id="cas-inverted",
            organization_id="org-test",
            case_type="INCIDENT",
            severity="MEDIUM",
            status="CLOSED",
            disposition="RESOLVED",
            created_at_utc=t2,
        )
    ]
    closures = [
        ClosureModel(
            closure_id="clo-inverted",
            organization_id="org-test",
            case_id="cas-inverted",
            closed_at_utc=t1,
            closure_status="RESOLVED",
            disposition="RESOLVED",
            summary="Closed early",
        )
    ]

    features = _make_features(
        case_count=1,
        cases=cases,
        closures=closures,
        cases_with_closure={"cas-inverted"},
        cases_with_investigation={"cas-inverted"},
    )

    signals = detector.detect(features)
    assert any("Temporal" in s.title and "Inversion" in s.title for s in signals)


# ---------------------------------------------------------------------------
# 2. Negative Space Detector Tests
# ---------------------------------------------------------------------------


def test_negative_space_missing_mandatory_family():
    """Missing mandatory evidence family generates a NEGATIVE_SPACE signal with supervisory language."""
    resolver = EvidenceResolver(session=None)
    detector = NegativeSpaceDetector(resolver)

    # Submission with alerts and cases, but missing 'assets'
    features = _make_features(
        declared_family_counts={"alerts": 10, "cases": 2},
        actual_family_counts={"alerts": 10, "cases": 2},
    )

    signals = detector.detect(features)
    missing_fams = [s for s in signals if "Missing Expected Evidence Family" in s.title]
    assert len(missing_fams) >= 1
    sig = missing_fams[0]
    assert sig.signal_type == SignalType.NEGATIVE_SPACE

    # Verify supervisory wording rule: absence of evidence is not proof of wrongdoing
    assert "No supporting record was observed" in sig.short_rationale or "was not observed" in sig.short_rationale
    assert "conclusive proof that the operational activity did not occur" in sig.detailed_explanation


def test_negative_space_count_discrepancy():
    """Declared record count higher than actual records flags evidence gap."""
    resolver = EvidenceResolver(session=None)
    detector = NegativeSpaceDetector(resolver)

    features = _make_features(
        declared_family_counts={"alerts": 100},
        actual_family_counts={"alerts": 20},
    )

    signals = detector.detect(features)
    disc = [s for s in signals if "Discrepancy" in s.title]
    assert len(disc) == 1
    assert disc[0].basis["declared_count"] == 100
    assert disc[0].basis["actual_count"] == 20


def test_negative_space_unmonitored_critical_assets():
    """Critical tier assets lacking monitoring coverage generate a NEGATIVE_SPACE signal."""
    resolver = EvidenceResolver(session=None)
    detector = NegativeSpaceDetector(resolver)

    assets = [
        AssetModel(
            asset_id="ast-crit-unmon",
            organization_id="org-test",
            asset_class="SERVER",
            criticality="TIER_0",
            operating_status="ACTIVE",
            effective_start_at_utc=datetime.now(UTC),
        )
    ]

    features = _make_features(
        asset_count=1,
        critical_asset_count=1,
        assets=assets,
        unmonitored_critical_asset_ids=["ast-crit-unmon"],
    )

    signals = detector.detect(features)
    unmon = [s for s in signals if "Critical Assets Lacking" in s.title]
    assert len(unmon) == 1
    assert "ast-crit-unmon" in unmon[0].affected_record_ids


# ---------------------------------------------------------------------------
# 3. Statistical Anomaly Detector Tests
# ---------------------------------------------------------------------------


def test_anomaly_detector_normal_baseline():
    """Normal operational rates produce zero statistical anomaly signals."""
    resolver = EvidenceResolver(session=None)
    detector = StatisticalAnomalyDetector(resolver)

    features = _make_features(
        alert_count=50,
        case_count=10,
        asset_count=10,
        case_closure_rate=0.75,
        median_investigation_duration_hours=12.0,
        escalation_count=2,
    )

    signals = detector.detect(features)
    assert signals == []


def test_anomaly_detector_low_closure_rate_and_long_duration():
    """Extremely low closure rate and excessive duration trigger STATISTICAL_ANOMALY signals."""
    resolver = EvidenceResolver(session=None)
    detector = StatisticalAnomalyDetector(resolver)

    now = datetime.now(UTC)
    invs = [
        InvestigationModel(
            investigation_id="inv-1",
            organization_id="org-test",
            case_id="cas-1",
            started_at_utc=now - timedelta(hours=14),
            completed_at_utc=now,
            summary="Normal investigation",
        ),
        InvestigationModel(
            investigation_id="inv-2",
            organization_id="org-test",
            case_id="cas-1",
            started_at_utc=now - timedelta(hours=15),
            completed_at_utc=now,
            summary="Normal investigation",
        ),
        InvestigationModel(
            investigation_id="inv-3",
            organization_id="org-test",
            case_id="cas-1",
            started_at_utc=now - timedelta(hours=140),
            completed_at_utc=now,
            summary="Prolonged investigation outlier",
        ),
    ]

    features = _make_features(
        case_count=20,
        case_closure_rate=0.05,  # 5% closure rate
        median_investigation_duration_hours=15.0,
        investigation_durations_hours=[14.0, 15.0, 140.0],
        investigations=invs,
        escalation_count=3,
        asset_count=5,
        alert_count=10,
    )

    signals = detector.detect(features, historical_durations=[12.0, 14.0, 16.0, 13.0, 14.0, 15.0])
    assert len(signals) >= 2
    types = {s.title for s in signals}
    assert any("Low Case Closure Rate" in t for t in types)
    assert any("Investigation Duration" in t for t in types)


# ---------------------------------------------------------------------------
# 4. Peer Comparison Detector Tests
# ---------------------------------------------------------------------------


def test_peer_comparison_insufficient_cohort():
    """Fewer than 3 peers in cohort must return 0 signals to prevent misleading comparisons."""
    resolver = EvidenceResolver(session=None)
    detector = PeerComparisonDetector(resolver, min_cohort_size=3)

    subject_features = _make_features(org_id="org-subj", case_count=10, case_closure_rate=0.1)
    peer1 = _make_features(org_id="org-peer1", case_count=10, case_closure_rate=0.9)

    subject_org = OrganizationModel(
        organization_id="org-subj",
        scale_band="TIER_1",
        operating_model="CENTRALIZED",
        organization_name="Subj Org",
        sector_code="FIN",
        subsector_code="BANK",
        default_timezone="UTC",
        organization_status="ACTIVE",
        profile_effective_start_at_utc=datetime.now(UTC),
    )
    peer_orgs = [
        OrganizationModel(
            organization_id="org-peer1",
            scale_band="TIER_1",
            operating_model="CENTRALIZED",
            organization_name="Peer 1",
            sector_code="FIN",
            subsector_code="BANK",
            default_timezone="UTC",
            organization_status="ACTIVE",
            profile_effective_start_at_utc=datetime.now(UTC),
        )
    ]

    signals = detector.detect(
        features=subject_features,
        peer_features=[peer1],
        organization=subject_org,
        all_organizations=[subject_org] + peer_orgs,
    )
    assert signals == []


def test_peer_comparison_significant_deviation():
    """Cohort size >= 3 with large deviation produces a PEER_DEVIATION signal."""
    resolver = EvidenceResolver(session=None)
    detector = PeerComparisonDetector(resolver, min_cohort_size=3)

    # Subject has closure rate 0.10, peers have median ~0.88
    subject_features = _make_features(org_id="org-subj", case_count=10, case_closure_rate=0.10)
    p1 = _make_features(org_id="p1", case_count=10, case_closure_rate=0.85)
    p2 = _make_features(org_id="p2", case_count=10, case_closure_rate=0.88)
    p3 = _make_features(org_id="p3", case_count=10, case_closure_rate=0.90)

    orgs = [
        OrganizationModel(
            organization_id=oid,
            scale_band="TIER_1",
            operating_model="CENTRALIZED",
            organization_name=oid,
            sector_code="FIN",
            subsector_code="BANK",
            default_timezone="UTC",
            organization_status="ACTIVE",
            profile_effective_start_at_utc=datetime.now(UTC),
        )
        for oid in ["org-subj", "p1", "p2", "p3"]
    ]

    signals = detector.detect(
        features=subject_features,
        peer_features=[p1, p2, p3],
        organization=orgs[0],
        all_organizations=orgs,
    )

    assert len(signals) >= 1
    sig = signals[0]
    assert sig.signal_type == SignalType.PEER_DEVIATION
    assert sig.basis["peer_population_size"] == 3
    assert sig.basis["peer_median"] > 0.8


# ---------------------------------------------------------------------------
# 5. Operational Drift Detector Tests
# ---------------------------------------------------------------------------


def test_operational_drift_insufficient_history():
    """Single period or empty prior features returns 0 drift signals."""
    resolver = EvidenceResolver(session=None)
    detector = OperationalDriftDetector(resolver)

    features = _make_features(alert_count=100)
    signals = detector.detect(features, prior_features_list=[])
    assert signals == []


def test_operational_drift_detected():
    """Alert surge (> 40% increase) generates an OPERATIONAL_DRIFT signal."""
    resolver = EvidenceResolver(session=None)
    detector = OperationalDriftDetector(resolver)

    prior = _make_features(sub_id="sub-prior", alert_count=50, case_closure_rate=0.80)
    current = _make_features(sub_id="sub-curr", alert_count=150, case_closure_rate=0.75)

    signals = detector.detect(current, prior_features_list=[prior])
    assert len(signals) >= 1
    vol_sig = [s for s in signals if "alert_volume" in s.basis["metric"]][0]
    assert vol_sig.signal_type == SignalType.OPERATIONAL_DRIFT
    assert vol_sig.observed_value == 150
    assert vol_sig.expected_value == 50
    assert vol_sig.basis["percent_change"] == 200.0


# ---------------------------------------------------------------------------
# 6. Attention Aggregator Tests
# ---------------------------------------------------------------------------


def test_attention_aggregator_bounded_and_explainable():
    """Verify that supervisory attention score is bounded (0-100) and priority bands are accurate."""
    aggregator = AttentionAggregator()

    # Empty signals -> score 0.0, band LOW
    empty_summary = aggregator.aggregate(organization_id="org-test", signals=[])
    assert empty_summary.attention_score == 0.0
    assert empty_summary.attention_band == "LOW"
    assert empty_summary.total_signals == 0

    # Critical signals -> score increases deterministically
    crit_signal = SupervisorySignal(
        signal_id="sig-1",
        organization_id="org-test",
        signal_type=SignalType.EXECUTION_GAP,
        severity=SignalSeverity.CRITICAL,
        title="Unlinked Critical Alerts",
        short_rationale="Short",
        detailed_explanation="Detailed",
        basis={},
        observed_value=5,
        confidence=0.95,
        evidence_references=[],
        affected_record_ids=["alt-1"],
        detector_id="DET-01",
        detector_version="1.0.0",
        investigation_questions=["Q?"],
        generated_at_utc=datetime.now(UTC),
    )

    high_signal = SupervisorySignal(
        signal_id="sig-2",
        organization_id="org-test",
        signal_type=SignalType.NEGATIVE_SPACE,
        severity=SignalSeverity.HIGH,
        title="Missing Asset Evidence",
        short_rationale="Short",
        detailed_explanation="Detailed",
        basis={},
        observed_value=1,
        confidence=0.90,
        evidence_references=[],
        affected_record_ids=[],
        detector_id="DET-02",
        detector_version="1.0.0",
        investigation_questions=["Q?"],
        generated_at_utc=datetime.now(UTC),
    )

    summary = aggregator.aggregate(organization_id="org-test", signals=[crit_signal, high_signal])
    assert summary.total_signals == 2
    # Decomposable: Severity (20*0.95 + 12*0.9 = 29.8) + Diversity ((2-1)*3.75 = 3.75)
    # + Data Quality (0.5*15 = 7.5) = 41.05
    assert summary.score_decomposition["severity_contribution"] == 29.80
    assert summary.score_decomposition["diversity_contribution"] == 3.75
    assert summary.score_decomposition["data_quality_gap_contribution"] == 7.50
    assert summary.attention_score == 41.05
    assert summary.attention_band == "MODERATE"
    assert len(summary.strongest_signals) == 2
    assert summary.data_quality_gap_index == 0.5


# ---------------------------------------------------------------------------
# 7. Additional Edge Case & Robustness Tests
# ---------------------------------------------------------------------------


def test_execution_gap_inapplicable_workflow_low_severity():
    """Low severity case closed as FALSE_POSITIVE does not require escalation/action records."""
    resolver = EvidenceResolver(session=None)
    detector = ExecutionGapDetector(resolver)

    case = CaseModel(
        case_id="cas-low",
        organization_id="org-test",
        case_type="INCIDENT",
        severity="LOW",
        status="CLOSED",
        disposition="FALSE_POSITIVE",
        created_at_utc=datetime.now(UTC),
    )
    features = _make_features(
        case_count=1,
        cases=[case],
        cases_with_investigation={"cas-low"},
        cases_with_closure={"cas-low"},
        cases_with_escalation_or_action=set(),
    )

    signals = detector.detect(features)
    # Must not flag unescalated severe case
    assert not any("Unescalated Severe Cases" in s.title for s in signals)


def test_execution_gap_multiple_organizations_partitioning():
    """Signals generated for one organization must never be attributed to another."""
    resolver = EvidenceResolver(session=None)
    detector = ExecutionGapDetector(resolver)

    feat_clean = _make_features(org_id="org-clean", case_count=1, unlinked_critical_alert_ids=[])
    feat_gaps = _make_features(org_id="org-gaps", case_count=1, unlinked_critical_alert_ids=["alt-crit-1"])

    clean_signals = detector.detect(feat_clean)
    assert clean_signals == []

    gap_signals = detector.detect(feat_gaps)
    assert len(gap_signals) == 1
    assert gap_signals[0].organization_id == "org-gaps"


def test_negative_space_declared_but_empty_evidence():
    """When a family is declared with non-zero count but 0 records arrive, flag gap."""
    resolver = EvidenceResolver(session=None)
    detector = NegativeSpaceDetector(resolver)

    features = _make_features(
        declared_family_counts={"investigations": 5},
        actual_family_counts={"investigations": 0},
    )

    signals = detector.detect(features)
    assert any("Discrepancy" in s.title and "investigations" in s.title.lower() for s in signals)


def test_anomaly_detector_tiny_population_no_false_alarm():
    """Tiny populations below minimum sample size thresholds should not produce spurious anomaly signals."""
    resolver = EvidenceResolver(session=None)
    detector = StatisticalAnomalyDetector(resolver, min_cases=5, min_investigations=5)

    features = _make_features(
        case_count=2,  # Below min_cases of 5
        case_closure_rate=0.0,
        investigation_durations_hours=[100.0, 200.0],  # Below min_investigations of 5
    )

    signals = detector.detect(features)
    assert signals == []


def test_anomaly_detector_constant_values_zero_mad():
    """Identical values producing zero MAD should be safely handled without division by zero."""
    resolver = EvidenceResolver(session=None)
    detector = StatisticalAnomalyDetector(resolver, min_investigations=3)

    features = _make_features(
        case_count=10,
        case_closure_rate=0.8,
        investigation_durations_hours=[10.0, 10.0, 10.0, 10.0, 10.0],
    )

    signals = detector.detect(features, historical_durations=[10.0, 10.0, 10.0, 10.0, 10.0])
    # No duration outlier should be flagged
    assert not any("Duration" in s.title for s in signals)


def test_peer_comparison_equal_to_median():
    """When subject metric equals peer median, no deviation signal is produced."""
    resolver = EvidenceResolver(session=None)
    detector = PeerComparisonDetector(resolver, min_cohort_size=3)

    subject_features = _make_features(org_id="org-subj", case_count=10, case_closure_rate=0.80)
    p1 = _make_features(org_id="p1", case_count=10, case_closure_rate=0.80)
    p2 = _make_features(org_id="p2", case_count=10, case_closure_rate=0.80)
    p3 = _make_features(org_id="p3", case_count=10, case_closure_rate=0.80)

    orgs = [
        OrganizationModel(
            organization_id=oid,
            scale_band="TIER_1",
            operating_model="CENTRALIZED",
            organization_name=oid,
            sector_code="FIN",
            subsector_code="BANK",
            default_timezone="UTC",
            organization_status="ACTIVE",
            profile_effective_start_at_utc=datetime.now(UTC),
        )
        for oid in ["org-subj", "p1", "p2", "p3"]
    ]

    signals = detector.detect(
        features=subject_features,
        peer_features=[p1, p2, p3],
        organization=orgs[0],
        all_organizations=orgs,
    )
    assert signals == []


def test_operational_drift_stable_periods():
    """Identical or near-identical metric values across periods produce no drift signal."""
    resolver = EvidenceResolver(session=None)
    detector = OperationalDriftDetector(resolver)

    prior = _make_features(sub_id="sub-prior", alert_count=100, case_closure_rate=0.80)
    current = _make_features(sub_id="sub-curr", alert_count=102, case_closure_rate=0.79)

    signals = detector.detect(current, prior_features_list=[prior])
    assert signals == []


def test_operational_drift_zero_baseline():
    """Zero baseline in previous period is safely handled without ZeroDivisionError."""
    resolver = EvidenceResolver(session=None)
    detector = OperationalDriftDetector(resolver)

    prior = _make_features(sub_id="sub-prior", alert_count=0, case_closure_rate=0.0)
    current = _make_features(sub_id="sub-curr", alert_count=50, case_closure_rate=0.80)

    signals = detector.detect(current, prior_features_list=[prior])
    assert len(signals) >= 1
    # Check that it cleanly flagged volume shift with 100.0% change
    vol_sig = [s for s in signals if "alert_volume" in s.basis["metric"]][0]
    assert vol_sig.basis["percent_change"] == 100.0
