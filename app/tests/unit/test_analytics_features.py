"""Unit tests for M7 analytics features and deterministic statistical utilities."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.backend.analytics.features import (
    FeatureExtractor,
    compute_iqr,
    compute_mad,
    compute_median,
)
from app.backend.persistence.models import (
    ActionModel,
    AlertModel,
    AssetModel,
    CaseAlertLinkModel,
    CaseModel,
    ClosureModel,
    EscalationModel,
    InvestigationModel,
    MonitoringCoverageModel,
    ResolutionModel,
    SubmissionEvidenceFamilyModel,
)


def test_pure_statistics_utilities():
    """Verify median, MAD, and IQR with various population sizes and edge cases."""
    # Empty population
    assert compute_median([]) == 0.0
    assert compute_mad([]) == 0.0
    assert compute_iqr([]) == (0.0, 0.0, 0.0)

    # Single value
    assert compute_median([42.0]) == 42.0
    assert compute_mad([42.0]) == 0.0
    assert compute_iqr([42.0]) == (42.0, 42.0, 0.0)

    # Odd length symmetric
    data_odd = [10.0, 20.0, 30.0, 40.0, 50.0]
    assert compute_median(data_odd) == 30.0
    assert compute_mad(data_odd, scale_to_normal=False) == 10.0
    assert abs(compute_mad(data_odd, scale_to_normal=True) - 14.826) < 1e-4

    # Even length
    data_even = [10.0, 20.0, 30.0, 40.0]
    assert compute_median(data_even) == 25.0

    # Constant values (zero variance)
    data_const = [5.0, 5.0, 5.0, 5.0, 5.0]
    assert compute_median(data_const) == 5.0
    assert compute_mad(data_const) == 0.0
    q1, q3, iqr = compute_iqr(data_const)
    assert iqr == 0.0


def test_feature_extractor_empty_population():
    """Verify feature extractor behavior when an organization has no records."""
    features = FeatureExtractor.extract(
        organization_id="org-empty",
        submission_id="sub-empty",
        alerts=[],
        cases=[],
        case_alert_links=[],
        investigations=[],
        escalations=[],
        actions=[],
        resolutions=[],
        closures=[],
        assets=[],
        coverage=[],
        declared_families=[],
    )

    assert features.alert_count == 0
    assert features.case_count == 0
    assert features.investigation_count == 0
    assert features.escalation_count == 0
    assert features.closure_count == 0
    assert features.case_closure_rate == 0.0
    assert features.escalation_rate == 0.0
    assert features.mean_investigation_duration_hours == 0.0
    assert features.median_investigation_duration_hours == 0.0
    assert features.unlinked_critical_alert_ids == []
    assert features.unmonitored_critical_asset_ids == []
    assert features.monitoring_coverage_rate == 0.0


def test_feature_extractor_counts_and_workflow_metrics():
    """Verify feature extraction across a structured operational dataset."""
    now = datetime.now(UTC)
    org_id = "org-test-1"
    sub_id = "sub-test-1"

    # 3 Alerts: 1 Critical, 1 High, 1 Low
    alerts = [
        AlertModel(
            alert_id="alt-1",
            organization_id=org_id,
            asset_id="ast-1",
            alert_category="AUTHENTICATION",
            severity="CRITICAL",
            status="NEW",
            disposition="ESCALATED",
            summary="Crit alert",
            created_at_utc=now - timedelta(hours=5),
        ),
        AlertModel(
            alert_id="alt-2",
            organization_id=org_id,
            asset_id="ast-1",
            alert_category="MALWARE",
            severity="HIGH",
            status="NEW",
            disposition="ESCALATED",
            summary="High alert",
            created_at_utc=now - timedelta(hours=4),
        ),
        AlertModel(
            alert_id="alt-3",
            organization_id=org_id,
            asset_id="ast-2",
            alert_category="POLICY_VIOLATION",
            severity="LOW",
            status="CLOSED",
            disposition="FALSE_POSITIVE",
            summary="Low alert",
            created_at_utc=now - timedelta(hours=3),
        ),
    ]

    # 2 Cases
    cases = [
        CaseModel(
            case_id="cas-1",
            organization_id=org_id,
            case_type="INCIDENT",
            severity="CRITICAL",
            status="CLOSED",
            disposition="RESOLVED",
            created_at_utc=now - timedelta(hours=4),
        ),
        CaseModel(
            case_id="cas-2",
            organization_id=org_id,
            case_type="INVESTIGATION",
            severity="HIGH",
            status="OPEN",
            disposition="INVESTIGATING",
            created_at_utc=now - timedelta(hours=3),
        ),
    ]

    # Link: alt-1 -> cas-1. alt-2 is unlinked!
    links = [
        CaseAlertLinkModel(
            case_alert_link_id="link-1",
            case_id="cas-1",
            alert_id="alt-1",
            link_type="PRIMARY",
            linked_at_utc=now - timedelta(hours=4),
        )
    ]

    # Investigations: 1 for cas-1 (duration 2 hours)
    investigations = [
        InvestigationModel(
            investigation_id="inv-1",
            organization_id=org_id,
            case_id="cas-1",
            analyst_id="agent-1",
            started_at_utc=now - timedelta(hours=4),
            completed_at_utc=now - timedelta(hours=2),
            summary="Investigation complete",
        )
    ]

    # Escalation: 1 for cas-1
    escalations = [
        EscalationModel(
            escalation_id="esc-1",
            organization_id=org_id,
            case_id="cas-1",
            escalated_from_tier="TIER_1",
            escalated_to_tier="TIER_2",
            escalated_at_utc=now - timedelta(hours=3),
            reason="High impact",
        )
    ]

    # Actions: 1 for cas-1
    actions = [
        ActionModel(
            action_id="act-1",
            organization_id=org_id,
            case_id="cas-1",
            action_type="CONTAINMENT",
            status="EXECUTED",
            summary="Isolate host",
            created_at_utc=now - timedelta(hours=3),
        )
    ]

    # Resolutions: 1 for cas-1
    resolutions = [
        ResolutionModel(
            resolution_id="res-1",
            organization_id=org_id,
            case_id="cas-1",
            resolution_type="REMEDIATED",
            resolved_at_utc=now - timedelta(hours=2),
            summary="Host isolated and patched",
        )
    ]

    # Closures: 1 for cas-1
    closures = [
        ClosureModel(
            closure_id="clo-1",
            organization_id=org_id,
            case_id="cas-1",
            closed_at_utc=now - timedelta(hours=1),
            closure_status="RESOLVED",
            disposition="CONTAINED",
            summary="Case closed successfully",
        )
    ]

    # Assets: 1 Tier 0 (monitored), 1 Tier 1 (unmonitored)
    assets = [
        AssetModel(
            asset_id="ast-1",
            organization_id=org_id,
            asset_class="SERVER",
            criticality="TIER_0",
            operating_status="ACTIVE",
            effective_start_at_utc=now - timedelta(days=365),
        ),
        AssetModel(
            asset_id="ast-2",
            organization_id=org_id,
            asset_class="DATABASE",
            criticality="TIER_1",
            operating_status="ACTIVE",
            effective_start_at_utc=now - timedelta(days=365),
        ),
    ]

    # Coverage: only ast-1
    coverage = [
        MonitoringCoverageModel(
            monitoring_coverage_id="cov-1",
            organization_id=org_id,
            asset_id="ast-1",
            monitoring_type="EDR",
            coverage_state="COVERED",
            effective_start_at_utc=now - timedelta(days=30),
        )
    ]

    # Declared families
    families = [
        SubmissionEvidenceFamilyModel(
            submission_family_id="fam-1",
            submission_id=sub_id,
            evidence_family="alerts",
            presence_state="PRESENT",
            declared_record_count=3,
        ),
        SubmissionEvidenceFamilyModel(
            submission_family_id="fam-2",
            submission_id=sub_id,
            evidence_family="cases",
            presence_state="PRESENT",
            declared_record_count=2,
        ),
    ]

    features = FeatureExtractor.extract(
        organization_id=org_id,
        submission_id=sub_id,
        alerts=alerts,
        cases=cases,
        case_alert_links=links,
        investigations=investigations,
        escalations=escalations,
        actions=actions,
        resolutions=resolutions,
        closures=closures,
        assets=assets,
        coverage=coverage,
        declared_families=families,
    )

    # Assert basic counts
    assert features.alert_count == 3
    assert features.critical_alert_count == 1
    assert features.high_alert_count == 1
    assert features.case_count == 2
    assert features.investigation_count == 1
    assert features.escalation_count == 1
    assert features.closure_count == 1
    assert features.asset_count == 2
    assert features.critical_asset_count == 2

    # Rates
    assert features.case_closure_rate == 0.5  # 1 closed / 2 cases
    assert features.escalation_rate == 0.5  # 1 escalated / 2 cases
    assert features.monitoring_coverage_rate == 0.5  # 1 monitored / 2 assets

    # Duration: 2.0 hours
    assert features.mean_investigation_duration_hours == 2.0
    assert features.median_investigation_duration_hours == 2.0

    # Unlinked critical/high alerts: alt-2 is high and has no link!
    assert features.unlinked_critical_alert_ids == ["alt-2"]

    # Unmonitored critical assets: ast-2 is Tier 1 and not in coverage!
    assert features.unmonitored_critical_asset_ids == ["ast-2"]


def test_features_determinism():
    """Assert that running feature extraction multiple times on identical inputs produces identical results."""
    now = datetime.now(UTC)
    org_id = "org-det"
    sub_id = "sub-det"

    alerts = [
        AlertModel(
            alert_id=f"alt-{i}",
            organization_id=org_id,
            asset_id="ast-1",
            alert_category="MALWARE",
            severity="HIGH",
            status="NEW",
            disposition="INVESTIGATING",
            summary=f"Alert {i}",
            created_at_utc=now,
        )
        for i in range(5)
    ]

    f1 = FeatureExtractor.extract(
        organization_id=org_id,
        submission_id=sub_id,
        alerts=alerts,
        cases=[],
        case_alert_links=[],
        investigations=[],
        escalations=[],
        actions=[],
        resolutions=[],
        closures=[],
        assets=[],
        coverage=[],
        declared_families=[],
    )
    f2 = FeatureExtractor.extract(
        organization_id=org_id,
        submission_id=sub_id,
        alerts=alerts,
        cases=[],
        case_alert_links=[],
        investigations=[],
        escalations=[],
        actions=[],
        resolutions=[],
        closures=[],
        assets=[],
        coverage=[],
        declared_families=[],
    )

    assert f1.alert_count == f2.alert_count
    assert f1.critical_alert_count == f2.critical_alert_count
    assert f1.high_alert_count == f2.high_alert_count
    assert f1.unlinked_critical_alert_ids == f2.unlinked_critical_alert_ids
