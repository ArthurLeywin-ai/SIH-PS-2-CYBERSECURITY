"""Authoritative Regression Tests for Milestone 7 Remediation Blockers.

Validates:
1. True Determinism: Identical inputs produce identical signal IDs, summary IDs, explanations, and ordering.
2. Submission Isolation: Two submissions for the same organization operate strictly on provenance-scoped records.
3. Complete Evidence Traceability: Every queueable signal contains real evidence references resolving to provenance.
4. No Silent Peer Fallback: Matched peer cohort strictly requires exact scale_band + operating_model.
5. Decomposable Attention Score: Transparent mathematical formula with explicit component breakdown.
6. Defensible Statistical Anomalies: Minimum sample-size guardrails with complete mathematical exposure in basis.
7. Neutral Analytical Language: Absence of unsupported official policy claims.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.backend.analytics.detectors.anomalies import StatisticalAnomalyDetector
from app.backend.analytics.detectors.attention import AttentionAggregator
from app.backend.analytics.detectors.execution_gaps import ExecutionGapDetector
from app.backend.analytics.detectors.peer_comparison import PeerComparisonDetector
from app.backend.analytics.engine import SupervisoryAnalyticsEngine
from app.backend.analytics.evidence import EvidenceResolver
from app.backend.analytics.features import FeatureExtractor
from app.backend.analytics.models import (
    EvidenceRole,
    SignalSeverity,
    SignalType,
    SupervisorySignal,
)
from app.backend.analytics.repository import AnalyticsRepository
from app.backend.persistence.models import (
    AlertModel,
    AssetModel,
    CaseModel,
    EvidenceProvenanceModel,
    MonitoringCoverageModel,
    OrganizationModel,
    SubmissionEvidenceFamilyModel,
    SubmissionModel,
)


def _seed_org_and_submission(
    session,
    org_id: str,
    sub_id: str,
    org_name: str = "Test Org",
    scale: str = "TIER_1",
    op_model: str = "INTERNAL",
    start_dt: datetime | None = None,
    end_dt: datetime | None = None,
) -> tuple[OrganizationModel, SubmissionModel]:
    org = session.get(OrganizationModel, org_id)
    if not org:
        org = OrganizationModel(
            organization_id=org_id,
            organization_name=org_name,
            sector_code="FINANCIAL",
            scale_band=scale,
            operating_model=op_model,
            entity_criticality_band="TIER_1",
            profile_effective_start_at_utc=datetime(2025, 1, 1, tzinfo=UTC),
            organization_status="ACTIVE",
        )
        session.add(org)

    sub = session.get(SubmissionModel, sub_id)
    if not sub:
        sub = SubmissionModel(
            submission_id=sub_id,
            organization_id=org_id,
            period_maturity_state="SUBMITTED",
            reporting_period_start_at_utc=start_dt or datetime(2026, 1, 1, tzinfo=UTC),
            reporting_period_end_at_utc=end_dt or datetime(2026, 1, 31, tzinfo=UTC),
        )
        session.add(sub)
    session.flush()
    return org, sub


def _record_provenance(
    session,
    canonical_id: str,
    family: str,
    org_id: str,
    sub_id: str,
    source_file: str = "operational.json",
):
    prov = EvidenceProvenanceModel(
        provenance_id=f"prov-{family}-{canonical_id}",
        canonical_record_id=canonical_id,
        evidence_family=family,
        organization_id=org_id,
        submission_id=sub_id,
        source_file=source_file,
        source_record_locator=f"id:{canonical_id}",
        source_field="id",
        canonical_field=f"{family.rstrip('s')}_id",
    )
    session.add(prov)
    session.flush()
    return prov


def test_blocker_1_true_determinism_under_identical_inputs():
    """Prove that for identical analytical input, signal IDs and summary IDs are 100% deterministic (UUID5)."""
    now = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)

    # Input features
    cases = [
        CaseModel(case_id=f"case-{i}", organization_id="org-det", severity="HIGH", status="OPEN", created_at_utc=now)
        for i in range(5)
    ]
    alerts = [
        AlertModel(alert_id=f"alt-{i}", organization_id="org-det", severity="HIGH", status="NEW", created_at_utc=now)
        for i in range(5)
    ]

    features = FeatureExtractor.extract(
        organization_id="org-det",
        submission_id="sub-det",
        alerts=alerts,
        cases=cases,
    )

    resolver = EvidenceResolver(session=None)
    exec_det = ExecutionGapDetector(resolver)

    # Run 1
    signals_1 = exec_det.detect(features)
    summary_1 = AttentionAggregator.aggregate("org-det", signals_1, "sub-det")

    # Run 2
    signals_2 = exec_det.detect(features)
    summary_2 = AttentionAggregator.aggregate("org-det", signals_2, "sub-det")

    assert len(signals_1) > 0
    assert len(signals_1) == len(signals_2)
    assert summary_1.summary_id == summary_2.summary_id
    assert summary_1.attention_score == summary_2.attention_score

    for s1, s2 in zip(signals_1, signals_2, strict=True):
        assert s1.signal_id == s2.signal_id, "Signal ID must be deterministic across identical analytical inputs!"
        assert s1.signal_type == s2.signal_type
        assert s1.severity == s2.severity
        assert s1.title == s2.title
        assert s1.short_rationale == s2.short_rationale
        assert s1.detailed_explanation == s2.detailed_explanation
        assert s1.basis == s2.basis
        assert s1.observed_value == s2.observed_value
        assert s1.expected_value == s2.expected_value
        assert s1.confidence == s2.confidence
        assert [r.to_dict() for r in s1.evidence_references] == [r.to_dict() for r in s2.evidence_references]
        assert s1.affected_record_ids == s2.affected_record_ids
        assert s1.detector_id == s2.detector_id
        assert s1.investigation_questions == s2.investigation_questions


def test_blocker_2_submission_scoping_multi_submission_isolation(test_db_session):
    """Prove that two submissions for the SAME organization operate strictly on provenance-scoped records."""
    org_id = "org-multi-sub"
    sub_1_id = "sub-period-jan"
    sub_2_id = "sub-period-feb"

    _seed_org_and_submission(
        test_db_session,
        org_id,
        sub_1_id,
        start_dt=datetime(2026, 1, 1, tzinfo=UTC),
        end_dt=datetime(2026, 1, 31, tzinfo=UTC),
    )
    _seed_org_and_submission(
        test_db_session,
        org_id,
        sub_2_id,
        start_dt=datetime(2026, 2, 1, tzinfo=UTC),
        end_dt=datetime(2026, 2, 28, tzinfo=UTC),
    )

    # Populate Sub-1 operational records (1 asset, 5 alerts, 1 case)
    ast1_id = "ast-sub1"
    test_db_session.add(
        AssetModel(
            asset_id=ast1_id,
            organization_id=org_id,
            asset_class="SERVER",
            criticality="TIER_1",
            operating_status="ACTIVE",
            effective_start_at_utc=datetime(2025, 1, 1, tzinfo=UTC),
        )
    )
    _record_provenance(test_db_session, ast1_id, "assets", org_id, sub_1_id)

    sub1_alert_ids = [f"sub1-alt-{i}" for i in range(5)]
    for aid in sub1_alert_ids:
        test_db_session.add(
            AlertModel(
                alert_id=aid,
                organization_id=org_id,
                asset_id=ast1_id,
                alert_category="AUTHENTICATION",
                severity="LOW",
                status="NEW",
                disposition="OPEN",
                summary=f"Summary for {aid}",
                created_at_utc=datetime(2026, 1, 10, tzinfo=UTC),
            )
        )
        _record_provenance(test_db_session, aid, "alerts", org_id, sub_1_id)

    sub1_case_id = "sub1-case-1"
    test_db_session.add(
        CaseModel(
            case_id=sub1_case_id,
            organization_id=org_id,
            case_type="INCIDENT",
            severity="LOW",
            status="OPEN",
            disposition="OPEN",
            created_at_utc=datetime(2026, 1, 11, tzinfo=UTC),
        )
    )
    _record_provenance(test_db_session, sub1_case_id, "cases", org_id, sub_1_id)

    # Populate Sub-2 operational records (1 asset, 25 alerts, 8 cases)
    ast2_id = "ast-sub2"
    test_db_session.add(
        AssetModel(
            asset_id=ast2_id,
            organization_id=org_id,
            asset_class="SERVER",
            criticality="TIER_1",
            operating_status="ACTIVE",
            effective_start_at_utc=datetime(2025, 1, 1, tzinfo=UTC),
        )
    )
    _record_provenance(test_db_session, ast2_id, "assets", org_id, sub_2_id)

    sub2_alert_ids = [f"sub2-alt-{i}" for i in range(25)]
    for aid in sub2_alert_ids:
        test_db_session.add(
            AlertModel(
                alert_id=aid,
                organization_id=org_id,
                asset_id=ast2_id,
                alert_category="AUTHENTICATION",
                severity="HIGH",
                status="NEW",
                disposition="OPEN",
                summary=f"Summary for {aid}",
                created_at_utc=datetime(2026, 2, 10, tzinfo=UTC),
            )
        )
        _record_provenance(test_db_session, aid, "alerts", org_id, sub_2_id)

    sub2_case_ids = [f"sub2-case-{i}" for i in range(8)]
    for cid in sub2_case_ids:
        test_db_session.add(
            CaseModel(
                case_id=cid,
                organization_id=org_id,
                case_type="INCIDENT",
                severity="HIGH",
                status="OPEN",
                disposition="OPEN",
                created_at_utc=datetime(2026, 2, 11, tzinfo=UTC),
            )
        )
        _record_provenance(test_db_session, cid, "cases", org_id, sub_2_id)

    test_db_session.commit()

    repo = AnalyticsRepository(test_db_session)

    # Features for Sub-1
    feat_sub1 = repo.get_entity_features(org_id, sub_1_id)
    assert feat_sub1.alert_count == 5, "Sub-1 must only see its own 5 alerts!"
    assert feat_sub1.case_count == 1, "Sub-1 must only see its own 1 case!"
    assert set(feat_sub1.unlinked_critical_alert_ids) == set()  # Only LOW alerts

    # Features for Sub-2
    feat_sub2 = repo.get_entity_features(org_id, sub_2_id)
    assert feat_sub2.alert_count == 25, "Sub-2 must only see its own 25 alerts!"
    assert feat_sub2.case_count == 8, "Sub-2 must only see its own 8 cases!"
    assert len(feat_sub2.unlinked_critical_alert_ids) == 25

    # Engine analysis for Sub-1
    engine = SupervisoryAnalyticsEngine(test_db_session)
    result_sub1 = engine.analyze_submission(sub_1_id, persist=False)
    for s in result_sub1.signals:
        for ref in s.evidence_references:
            assert not ref.record_id.startswith("sub2-"), (
                f"Sub-1 signal contaminated with Sub-2 evidence reference {ref.record_id}!"
            )

    # Engine analysis for Sub-2
    result_sub2 = engine.analyze_submission(sub_2_id, persist=False)
    for s in result_sub2.signals:
        for ref in s.evidence_references:
            assert not ref.record_id.startswith("sub1-"), (
                f"Sub-2 signal contaminated with Sub-1 evidence reference {ref.record_id}!"
            )


def test_blocker_3_queueable_signals_have_real_evidence_references(test_db_session):
    """Prove that every generated supervisory signal contains non-empty evidence references."""
    org_id = "org-ev-trace"
    sub_id = "sub-ev-trace"

    _seed_org_and_submission(test_db_session, org_id, sub_id)

    # Add asset, unlinked high alerts and declared discrepancy
    ast_id = "ast-trace-1"
    test_db_session.add(
        AssetModel(
            asset_id=ast_id,
            organization_id=org_id,
            asset_class="SERVER",
            criticality="TIER_1",
            operating_status="ACTIVE",
            effective_start_at_utc=datetime(2025, 1, 1, tzinfo=UTC),
        )
    )
    _record_provenance(test_db_session, ast_id, "assets", org_id, sub_id)

    aid = "alt-unlinked-trace"
    test_db_session.add(
        AlertModel(
            alert_id=aid,
            organization_id=org_id,
            asset_id=ast_id,
            alert_category="AUTHENTICATION",
            severity="HIGH",
            status="NEW",
            disposition="OPEN",
            summary="Unlinked critical alert for traceability test",
            created_at_utc=datetime(2026, 1, 5, tzinfo=UTC),
        )
    )
    _record_provenance(test_db_session, aid, "alerts", org_id, sub_id)

    fam_id = "fam-decl-trace"
    test_db_session.add(
        SubmissionEvidenceFamilyModel(
            submission_family_id=fam_id,
            submission_id=sub_id,
            evidence_family="alerts",
            presence_state="PRESENT",
            declared_record_count=10,  # Discrepancy: declared 10, actual 1
        )
    )
    _record_provenance(test_db_session, fam_id, "submission_evidence_families", org_id, sub_id)
    test_db_session.commit()

    engine = SupervisoryAnalyticsEngine(test_db_session)
    result = engine.analyze_submission(sub_id, persist=False)

    assert len(result.signals) > 0
    for sig in result.signals:
        assert len(sig.evidence_references) > 0, (
            f"Signal '{sig.title}' ({sig.signal_type}) must contain evidence references!"
        )
        for ref in sig.evidence_references:
            assert ref.role in {
                EvidenceRole.TRIGGER,
                EvidenceRole.SUPPORTING,
                EvidenceRole.BASELINE_MEMBER,
                EvidenceRole.PEER_MEMBER,
                EvidenceRole.MISSING_EXPECTATION,
                EvidenceRole.QUALITY_LIMITATION,
            }
            assert len(ref.record_id) > 0


def test_blocker_4_no_silent_peer_fallback():
    """Prove that insufficient exact cohort match (scale_band + operating_model) does NOT fall back silently."""
    resolver = EvidenceResolver(session=None)
    detector = PeerComparisonDetector(resolver, min_cohort_size=3)

    subject_org = OrganizationModel(
        organization_id="org-subj",
        organization_name="Subject Org",
        scale_band="TIER_1",
        operating_model="INTERNAL",
    )
    subject_features = FeatureExtractor.extract(
        organization_id="org-subj",
        submission_id="sub-subj",
        assets=[
            AssetModel(
                asset_id="ast-1", organization_id="org-subj", criticality="TIER_1", operating_status="ACTIVE"
            )
        ],
        coverage=[],  # 0% coverage
    )

    # Peers: only 2 match INTERNAL (insufficient for min_cohort_size=3), but 5 match HYBRID with same scale TIER_1
    peer_orgs = [
        OrganizationModel(organization_id="p1", scale_band="TIER_1", operating_model="INTERNAL"),
        OrganizationModel(organization_id="p2", scale_band="TIER_1", operating_model="INTERNAL"),
        OrganizationModel(organization_id="p3", scale_band="TIER_1", operating_model="HYBRID"),
        OrganizationModel(organization_id="p4", scale_band="TIER_1", operating_model="HYBRID"),
        OrganizationModel(organization_id="p5", scale_band="TIER_1", operating_model="HYBRID"),
    ]
    def _make_peer_feature(pid: str):
        return FeatureExtractor.extract(
            organization_id=pid,
            assets=[AssetModel(asset_id=f"ast-{pid}", organization_id=pid)],
            coverage=[
                MonitoringCoverageModel(
                    monitoring_coverage_id=f"c-{pid}",
                    asset_id=f"ast-{pid}",
                    coverage_state="COVERED",
                    coverage_percentage=100.0,
                    organization_id=pid,
                )
            ],
        )

    peer_feats = [_make_peer_feature(pid) for pid in ["p1", "p2", "p3", "p4", "p5"]]

    # Must produce ZERO signals because exact cohort size is 2 < 3
    signals = detector.detect(
        features=subject_features,
        organization=subject_org,
        peer_features=peer_feats,
        all_organizations=peer_orgs,
    )
    assert signals == [], "Must NOT silently fall back to scale-only peer cohort!"

    # Now add 3rd exact cohort peer
    peer_orgs.append(OrganizationModel(organization_id="p6", scale_band="TIER_1", operating_model="INTERNAL"))
    peer_feats.append(_make_peer_feature("p6"))

    # Now exact cohort is 3 -> signals eligible
    signals_with_cohort = detector.detect(
        features=subject_features,
        organization=subject_org,
        peer_features=peer_feats,
        all_organizations=peer_orgs,
    )
    assert len(signals_with_cohort) == 1
    sig = signals_with_cohort[0]
    assert sig.signal_type == SignalType.PEER_DEVIATION
    assert "scale_band=TIER_1, operating_model=INTERNAL" in sig.basis["cohort_description"]


def test_blocker_5_attention_score_decomposition_and_bounds():
    """Verify that Supervisory Attention Indicator is bounded (0-100) and strictly decomposable."""
    # 1. Zero signals
    summary_empty = AttentionAggregator.aggregate("org-test", [])
    assert summary_empty.attention_score == 0.0
    assert summary_empty.score_decomposition["raw_score"] == 0.0
    assert summary_empty.score_decomposition["bounded_score"] == 0.0

    # 2. Multi-dimensional signals
    s_crit = SupervisorySignal(
        signal_id="s1",
        organization_id="org-test",
        signal_type=SignalType.EXECUTION_GAP,
        severity=SignalSeverity.CRITICAL,
        title="Unlinked Critical Alerts",
        short_rationale="",
        detailed_explanation="",
        observed_value=1,
        confidence=1.0,
    )
    s_high = SupervisorySignal(
        signal_id="s2",
        organization_id="org-test",
        signal_type=SignalType.NEGATIVE_SPACE,
        severity=SignalSeverity.HIGH,
        title="Missing Documentation",
        short_rationale="",
        detailed_explanation="",
        observed_value=1,
        confidence=1.0,
    )
    s_med = SupervisorySignal(
        signal_id="s3",
        organization_id="org-test",
        signal_type=SignalType.STATISTICAL_ANOMALY,
        severity=SignalSeverity.MEDIUM,
        title="Investigation Duration Outlier",
        short_rationale="",
        detailed_explanation="",
        observed_value=1,
        confidence=0.80,
    )

    summary = AttentionAggregator.aggregate("org-test", [s_crit, s_high, s_med])
    decomp = summary.score_decomposition

    # Verify decomposition math: C_sev + C_div + C_dq == raw_score
    # C_sev: 20*1.0 + 12*1.0 + 6*0.8 = 36.8
    # C_div: (3 types - 1) * 3.75 = 7.5
    # C_dq: (1 NEGATIVE_SPACE / 3 signals) * 15.0 = 5.0
    # raw_score = 36.8 + 7.5 + 5.0 = 49.30
    assert decomp["severity_contribution"] == 36.8
    assert decomp["diversity_contribution"] == 7.5
    assert decomp["data_quality_gap_contribution"] == 5.0
    assert decomp["raw_score"] == 49.30
    assert decomp["bounded_score"] == 49.30
    assert summary.attention_score == 49.30
    assert 0.0 <= summary.attention_score <= 100.0


def test_blocker_6_statistical_anomaly_sample_size_guardrails():
    """Verify statistical anomaly detector requires defensible empirical sample sizes and exposes basis math."""
    resolver = EvidenceResolver(session=None)
    detector = StatisticalAnomalyDetector(resolver)

    features = FeatureExtractor.extract(
        organization_id="org-test",
        cases=[
            CaseModel(case_id=f"c-{i}", organization_id="org-test", status="OPEN", created_at_utc=datetime.now(UTC))
            for i in range(10)
        ],  # 10 cases, 0% closure
    )

    # 1. Historical closure rates with n >= 3
    hist_closures = [0.80, 0.85, 0.82, 0.78, 0.84]
    signals = detector.detect(features, historical_closure_rates=hist_closures)

    closure_sigs = [s for s in signals if "Closure Rate" in s.title]
    assert len(closure_sigs) == 1
    sig = closure_sigs[0]
    assert sig.signal_type == SignalType.STATISTICAL_ANOMALY
    assert sig.basis["sample_size"] == 5
    assert "HISTORICAL_MEDIAN_MAD" in sig.basis["baseline_method"]
    assert "threshold" in sig.basis
    assert "deviation" in sig.basis
    assert "limitations" in sig.basis
    assert len(sig.evidence_references) > 0


def test_blocker_7_no_invented_policy_language():
    """Verify that generated rationales do not assert unbacked regulatory standards or statutory mandates."""
    now = datetime.now(UTC)
    features = FeatureExtractor.extract(
        organization_id="org-test",
        alerts=[
            AlertModel(
                alert_id="a1",
                organization_id="org-test",
                severity="CRITICAL",
                status="NEW",
                created_at_utc=now,
            )
        ],
        cases=[
            CaseModel(
                case_id="c1",
                organization_id="org-test",
                severity="CRITICAL",
                status="OPEN",
                created_at_utc=now,
            )
        ],
    )

    resolver = EvidenceResolver(session=None)
    exec_det = ExecutionGapDetector(resolver)
    signals = exec_det.detect(features)

    for s in signals:
        text = f"{s.title} {s.short_rationale} {s.detailed_explanation}".lower()
        assert "established supervisory standards" not in text
        assert "nciipc" not in text
        assert "statutory standard" not in text
        assert "evidentiary standards" not in text


def test_test_a_and_b_unresolved_provenance_and_ambiguous_exclusion(test_db_session):
    """Test A & B: Ambiguous records without valid submission mapping resolve to None and are excluded."""
    from app.backend.ingestion.normalizer import EvidenceNormalizer

    org_id = "org-ambig-test"
    sub_1 = "sub-jan-2026"
    sub_2 = "sub-feb-2026"

    _seed_org_and_submission(
        test_db_session,
        org_id,
        sub_1,
        start_dt=datetime(2026, 1, 1, tzinfo=UTC),
        end_dt=datetime(2026, 1, 31, tzinfo=UTC),
    )
    _seed_org_and_submission(
        test_db_session,
        org_id,
        sub_2,
        start_dt=datetime(2026, 2, 1, tzinfo=UTC),
        end_dt=datetime(2026, 2, 28, tzinfo=UTC),
    )

    # Initialize EvidenceNormalizer with both submissions
    normalizer = EvidenceNormalizer(
        submissions=[
            {
                "submission_id": sub_1,
                "organization_id": org_id,
                "reporting_period_start_at_utc": "2026-01-01T00:00:00Z",
                "reporting_period_end_at_utc": "2026-01-31T23:59:59Z",
            },
            {
                "submission_id": sub_2,
                "organization_id": org_id,
                "reporting_period_start_at_utc": "2026-02-01T00:00:00Z",
                "reporting_period_end_at_utc": "2026-02-28T23:59:59Z",
            },
        ]
    )

    # Operational record: Alert with timestamp outside both periods (March 15) and no explicit submission_id
    raw_ambiguous_alert = {
        "alert_id": "alt-ambig-1",
        "organization_id": org_id,
        "asset_id": "ast-ambig-1",
        "severity": "HIGH",
        "status": "NEW",
        "disposition": "OPEN",
        "alert_category": "AUTHENTICATION",
        "summary": "Ambiguous alert outside periods",
        "created_at_utc": "2026-03-15T12:00:00Z",
    }

    norm_alert = normalizer._normalize_alerts(raw_ambiguous_alert, "operational.json", 1)

    # Test A: Provenance submission_id MUST be None
    prov_records = [p for p in normalizer.provenance_records if p.canonical_record_id == "alt-ambig-1"]
    assert len(prov_records) >= 1
    for ambig_prov in prov_records:
        assert ambig_prov.submission_id is None, (
            f"Ambiguous record must have submission_id=None, got {ambig_prov.submission_id}!"
        )

    # Seed asset and ambiguous alert + provenance into DB
    ast_model = AssetModel(
        asset_id="ast-ambig-1",
        organization_id=org_id,
        asset_class="SERVER",
        criticality="TIER_1",
        operating_status="ACTIVE",
        effective_start_at_utc=datetime(2025, 1, 1, tzinfo=UTC),
    )
    test_db_session.add(ast_model)
    test_db_session.add(norm_alert)
    test_db_session.add(
        EvidenceProvenanceModel(
            provenance_id="prov-ambig-1",
            canonical_record_id="alt-ambig-1",
            evidence_family="alerts",
            organization_id=org_id,
            submission_id=None,  # Unresolved
            source_file="operational.json",
            source_record_locator="row:1",
            source_field="alert_id",
            canonical_field="alert_id",
        )
    )
    test_db_session.commit()

    # Test B: Prove ambiguous record is NOT included in either submission's scoped feature set
    repo = AnalyticsRepository(test_db_session)
    feat_sub1 = repo.get_entity_features(org_id, sub_1)
    assert not any(a.alert_id == "alt-ambig-1" for a in feat_sub1.alerts), (
        "Ambiguous alert must NOT appear in Sub-1 scoped feature set!"
    )

    feat_sub2 = repo.get_entity_features(org_id, sub_2)
    assert not any(a.alert_id == "alt-ambig-1" for a in feat_sub2.alerts), (
        "Ambiguous alert must NOT appear in Sub-2 scoped feature set!"
    )


def test_test_c_statistical_anomaly_sample_size_ladder():
    """Test C: Sample size ladder for closure rate anomalies (n=0,1,2 -> None; n>=3 -> valid MAD signal)."""
    resolver = EvidenceResolver(session=None)
    detector = StatisticalAnomalyDetector(resolver)

    features = FeatureExtractor.extract(
        organization_id="org-test-c",
        cases=[
            CaseModel(
                case_id=f"case-c-{i}",
                organization_id="org-test-c",
                status="OPEN",
                created_at_utc=datetime.now(UTC),
            )
            for i in range(10)
        ],  # 10 cases, 0% closure
    )

    # Ladder 1: n = 0 (empty or None)
    sigs_0a = detector.detect(features, historical_closure_rates=None)
    assert not any("Closure Rate" in s.title for s in sigs_0a)

    sigs_0b = detector.detect(features, historical_closure_rates=[])
    assert not any("Closure Rate" in s.title for s in sigs_0b)

    # Ladder 2: n = 1
    sigs_1 = detector.detect(features, historical_closure_rates=[0.80])
    assert not any("Closure Rate" in s.title for s in sigs_1)

    # Ladder 3: n = 2
    sigs_2 = detector.detect(features, historical_closure_rates=[0.80, 0.85])
    assert not any("Closure Rate" in s.title for s in sigs_2)

    # Ladder 4: n = 3 (minimum required sample size reached)
    sigs_3 = detector.detect(features, historical_closure_rates=[0.80, 0.85, 0.82])
    closure_sigs_3 = [s for s in sigs_3 if "Closure Rate" in s.title]
    assert len(closure_sigs_3) == 1
    sig = closure_sigs_3[0]

    assert sig.signal_type == SignalType.STATISTICAL_ANOMALY
    assert sig.basis["sample_size"] == 3
    assert sig.basis["sample_size"] >= 3
    assert "baseline_reference" in sig.basis
    assert "threshold" in sig.basis
    assert "deviation" in sig.basis
    assert "limitations" in sig.basis
    assert "HISTORICAL_MEDIAN_MAD" in sig.basis["baseline_method"]
    assert "CONFIGURED_ANALYTICAL_EXPECTATION" not in sig.basis["baseline_method"]


def test_test_d_family_specific_provenance_filtering_with_colliding_ids(test_db_session):
    """Test D: Intentionally colliding canonical IDs across two families are partitioned by evidence_family."""
    org_id = "org-coll-test"
    sub_a = "sub-coll-a"
    sub_b = "sub-coll-b"

    _seed_org_and_submission(test_db_session, org_id, sub_a)
    _seed_org_and_submission(test_db_session, org_id, sub_b)

    colliding_id = "collision-1"

    # Asset for foreign key
    test_db_session.add(
        AssetModel(
            asset_id="ast-coll",
            organization_id=org_id,
            asset_class="SERVER",
            criticality="TIER_1",
            operating_status="ACTIVE",
            effective_start_at_utc=datetime(2025, 1, 1, tzinfo=UTC),
        )
    )
    _record_provenance(test_db_session, "ast-coll", "assets", org_id, sub_a)

    # Alert in Submission A
    test_db_session.add(
        AlertModel(
            alert_id=colliding_id,
            organization_id=org_id,
            asset_id="ast-coll",
            alert_category="AUTHENTICATION",
            severity="HIGH",
            status="NEW",
            disposition="OPEN",
            summary="Alert with collision id",
            created_at_utc=datetime(2026, 1, 10, tzinfo=UTC),
        )
    )
    _record_provenance(test_db_session, colliding_id, "alerts", org_id, sub_a)

    # Case in Submission B
    test_db_session.add(
        CaseModel(
            case_id=colliding_id,
            organization_id=org_id,
            case_type="INCIDENT",
            severity="HIGH",
            status="OPEN",
            disposition="OPEN",
            created_at_utc=datetime(2026, 2, 10, tzinfo=UTC),
        )
    )
    _record_provenance(test_db_session, colliding_id, "cases", org_id, sub_b)
    test_db_session.commit()

    repo = AnalyticsRepository(test_db_session)

    # Submission A must see ONLY the alert, NOT the case
    feat_a = repo.get_entity_features(org_id, sub_a)
    assert [a.alert_id for a in feat_a.alerts] == [colliding_id]
    assert len(feat_a.cases) == 0, (
        f"Submission A must have 0 cases, but found {[c.case_id for c in feat_a.cases]}!"
    )

    # Submission B must see ONLY the case, NOT the alert
    feat_b = repo.get_entity_features(org_id, sub_b)
    assert len(feat_b.alerts) == 0, (
        f"Submission B must have 0 alerts, but found {[a.alert_id for a in feat_b.alerts]}!"
    )
    assert [c.case_id for c in feat_b.cases] == [colliding_id]

