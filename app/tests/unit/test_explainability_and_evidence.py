"""Unit tests verifying explainability contracts, evidence traceability, and ground-truth isolation."""

from __future__ import annotations

import inspect
from datetime import UTC, datetime

from app.backend.analytics.evidence import EvidenceResolver
from app.backend.analytics.explanations import (
    format_execution_gap_explanation,
    format_negative_space_explanation,
    format_operational_drift_explanation,
    format_peer_deviation_explanation,
    format_statistical_anomaly_explanation,
)
from app.backend.analytics.models import (
    EvidenceReference,
    EvidenceRole,
    SignalSeverity,
    SignalType,
    SupervisorySignal,
)
from app.backend.persistence.models import EvidenceProvenanceModel


def test_explainability_formatters_non_empty_and_examiner_ready():
    """Verify all explanation formatters produce detailed rationales and concrete examiner questions."""
    # 1. Execution gap
    short, detailed, questions = format_execution_gap_explanation(
        gap_type="test_gap",
        stage_from="alert",
        stage_to="case",
        observed_count=3,
        total_eligible=10,
        sample_ids=["id-1", "id-2"],
    )
    assert "3 of 10 alert" in short
    assert len(detailed) > 50
    assert len(questions) >= 2
    assert all(q.endswith("?") for q in questions)

    # 2. Negative space
    short, detailed, questions = format_negative_space_explanation(
        target_scope="assets",
        expected_rule="Inventory must be provided",
        observed_state="0 records observed",
    )
    assert "was not observed" in short
    assert "rather than conclusive proof that the operational activity did not occur" in detailed
    assert len(questions) >= 2

    # 3. Statistical anomaly
    short, detailed, questions = format_statistical_anomaly_explanation(
        metric_name="closure_rate",
        observed_val="10%",
        baseline_val="80%",
        baseline_method="MEDIAN_MAD",
        deviation="-70%",
        direction="below",
    )
    assert "significantly below" in short
    assert "closure_rate" in detailed
    assert len(questions) >= 2

    # 4. Peer deviation
    short, detailed, questions = format_peer_deviation_explanation(
        metric_name="escalation_rate",
        subject_val="5%",
        peer_median="25%",
        peer_cohort_desc="Tier 1 banks",
        cohort_size=5,
        deviation="-20%",
    )
    assert "deviates from matched peer cohort median" in short
    assert "Peer comparison serves as supervisory context" in detailed
    assert len(questions) >= 2

    # 5. Operational drift
    short, detailed, questions = format_operational_drift_explanation(
        metric_name="alert_volume",
        current_val=500,
        baseline_val=200,
        current_period="SUB-02",
        baseline_period="SUB-01",
        pct_change=150.0,
    )
    assert "150.0% increase" in short
    assert "SUB-01" in detailed and "SUB-02" in detailed
    assert len(questions) >= 2


def test_evidence_resolver_with_and_without_provenance(test_db_session):
    """Verify evidence resolver builds references and enriches with provenance when available."""
    resolver = EvidenceResolver(session=test_db_session)

    # 1. Resolve record without provenance record in DB
    ref1 = resolver.build_reference(
        record_id="rec-unknown",
        evidence_family="alerts",
        role=EvidenceRole.TRIGGER,
        description="Trigger alert",
    )
    assert ref1.record_id == "rec-unknown"
    assert ref1.evidence_family == "alerts"
    assert ref1.role == EvidenceRole.TRIGGER
    assert ref1.source_file is None

    # 2. Add provenance record to DB
    prov = EvidenceProvenanceModel(
        provenance_id="prov-1",
        canonical_record_id="rec-known",
        evidence_family="alerts",
        organization_id="org-1",
        submission_id="sub-1",
        source_file="alerts.jsonl",
        source_record_locator="line:42",
        source_field="id",
        canonical_field="alert_id",
    )
    test_db_session.add(prov)
    test_db_session.commit()

    # 3. Resolve record with provenance record in DB
    ref2 = resolver.build_reference(
        record_id="rec-known",
        evidence_family="alerts",
        role=EvidenceRole.SUPPORTING,
    )
    assert ref2.record_id == "rec-known"
    assert ref2.source_file == "alerts.jsonl"
    assert ref2.source_record_locator == "line:42"


def test_strict_isolation_from_ground_truth():
    """Verify that runtime analytics engine has ZERO import or call dependencies on generator ground truth."""
    import app.backend.analytics
    import app.backend.analytics.detectors
    import app.backend.analytics.engine
    import app.backend.analytics.evidence
    import app.backend.analytics.features
    import app.backend.analytics.models
    import app.backend.analytics.repository

    modules = [
        app.backend.analytics,
        app.backend.analytics.detectors,
        app.backend.analytics.engine,
        app.backend.analytics.evidence,
        app.backend.analytics.features,
        app.backend.analytics.models,
        app.backend.analytics.repository,
    ]

    for mod in modules:
        source = inspect.getsource(mod)
        assert "private_ground_truth" not in source, f"Forbidden reference to private_ground_truth in {mod.__name__}"
        assert "oracle" not in source.lower() or "oracle" in "oracle_label", (
            f"Possible forbidden oracle reference in {mod.__name__}"
        )
        assert "satsa_generator.scenarios" not in source, (
            f"Forbidden import of generator scenario metadata in {mod.__name__}"
        )
        assert "generator_metadata" not in source, (
            f"Forbidden reference to generator_metadata in {mod.__name__}"
        )


def test_signal_contract_completeness():
    """Verify that every SupervisorySignal strictly satisfies the contract from M7 specification."""
    now = datetime.now(UTC)
    ref = EvidenceReference(
        record_id="rec-1",
        evidence_family="cases",
        role=EvidenceRole.TRIGGER,
    )

    sig = SupervisorySignal(
        signal_id="sig-test-123",
        organization_id="org-spec",
        submission_id="sub-spec",
        signal_type=SignalType.EXECUTION_GAP,
        severity=SignalSeverity.CRITICAL,
        title="Test Signal Contract",
        short_rationale="Short rationale summary",
        detailed_explanation="Detailed explainable finding for examiners",
        basis={"test_metric": 42},
        observed_value=42,
        expected_value=0,
        confidence=0.99,
        evidence_references=[ref],
        affected_record_ids=["rec-1"],
        detector_id="DET-TEST",
        detector_version="1.0.0",
        investigation_questions=["Why was this observed?"],
        generated_at_utc=now,
    )

    d = sig.to_dict()
    # Contract validation: Section 4 of prompt
    assert d["signal_id"] == "sig-test-123"
    assert d["organization_id"] == "org-spec"
    assert d["submission_id"] == "sub-spec"
    assert d["signal_type"] == "EXECUTION_GAP"
    assert d["severity"] == "CRITICAL"
    assert d["title"] == "Test Signal Contract"
    assert d["short_rationale"] == "Short rationale summary"
    assert d["detailed_explanation"] == "Detailed explainable finding for examiners"
    assert d["basis"] == {"test_metric": 42}
    assert d["observed_value"] == 42
    assert d["expected_value"] == 0
    assert d["confidence"] == 0.99
    assert len(d["evidence_references"]) == 1
    assert d["evidence_references"][0]["record_id"] == "rec-1"
    assert d["affected_record_ids"] == ["rec-1"]
    assert d["detector_id"] == "DET-TEST"
    assert d["detector_version"] == "1.0.0"
    assert d["investigation_questions"] == ["Why was this observed?"]
    assert d["generated_at_utc"] == now.isoformat()
