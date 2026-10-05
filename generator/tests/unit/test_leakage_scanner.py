"""
Unit tests for ComprehensiveLeakageScanner, false-positive review workflow, and canary testing.

Tests GENERATOR_IMPLEMENTATION_PLAN §19:
- All 9 leakage detection methods
- Exact tokens, regex, normalization, denylist keys, template fingerprints
- Package membership checks
- False-positive review workflow with LeakageWaiver
- Canary testing with CanaryScanner
"""

import pytest

from satsa_generator.validation.leakage import (
    CanaryScanner,
    ComprehensiveLeakageScanner,
    LeakageError,
    LeakageWaiver,
)
from satsa_generator.validation.models import GateSeverity


def test_clean_payload_passes():
    payload = {
        "alert_id": "99999999-9999-9999-9999-999999999999",
        "severity": "HIGH",
        "summary": "Standard operational alert for suspicious login",
        "details": {"event_count": 5, "ip_address": "10.0.0.1"},
    }
    issues = ComprehensiveLeakageScanner.scan_payload(payload)
    assert len(issues) == 0
    ComprehensiveLeakageScanner.assert_no_leakage(payload)


def test_forbidden_metadata_keys():
    # §19.3 #5: Metadata key denylist
    leaky_payload = {
        "alert_id": "123",
        "scenario_id": "EXEC-GAP-01",
    }
    issues = ComprehensiveLeakageScanner.scan_payload(leaky_payload)
    assert any(i.code == "LEAK_FORBIDDEN_KEY" for i in issues)
    with pytest.raises(LeakageError):
        ComprehensiveLeakageScanner.assert_no_leakage(leaky_payload)


def test_scenario_pattern_regex():
    # §19.3 #2: Regex for scenario ID families
    patterns = [
        "EXEC-GAP-01",
        "NEG-SPACE-02",
        "HIST-REP-01",
        "PEER-CMP-03",
        "CROSS-REC-01",
        "LEGIT-CTRL-01",
        "AMBIG-01",
    ]
    for pat in patterns:
        leaky_payload = {"notes": f"Observed activity linked to {pat} testing"}
        issues = ComprehensiveLeakageScanner.scan_payload(leaky_payload)
        assert any(i.code == "LEAK_SCENARIO_PATTERN" for i in issues)
        with pytest.raises(LeakageError):
            ComprehensiveLeakageScanner.assert_no_leakage(leaky_payload)


def test_distinctive_private_phrase_fingerprint():
    # §19.3 #6: Phrase fingerprint check
    leaky_payload = {"summary": "Alert closed; qualifying investigation absent"}
    issues = ComprehensiveLeakageScanner.scan_payload(leaky_payload)
    assert any(i.code == "LEAK_PRIVATE_PHRASE" for i in issues)
    with pytest.raises(LeakageError):
        ComprehensiveLeakageScanner.assert_no_leakage(leaky_payload)


def test_waiver_workflow_on_warning():
    # §19.5: Warning terms and waivers
    warning_payload = {"notes": "Analyst drew attention to repeated occurrences"}
    # Without waiver -> returns WARNING issue
    issues = ComprehensiveLeakageScanner.scan_payload(warning_payload)
    assert any(i.code == "LEAK_GENERIC_WARNING" for i in issues)

    # With waiver -> waived
    waiver = LeakageWaiver(
        waiver_id="WAIVE-001",
        scope="*",
        pattern="attention",
        reason="Legitimate analyst operational note phrasing",
        reviewer="auditor_lead",
        version="0.1.0",
    )
    issues_waived = ComprehensiveLeakageScanner.scan_payload(warning_payload, waivers=[waiver])
    assert len(issues_waived) == 0


def test_blocking_finding_cannot_be_waived():
    # §19.5: Blocking findings cannot be allowlisted merely for convenience
    blocking_payload = {"notes": "Found EXEC-GAP-01 anomaly"}
    waiver = LeakageWaiver(
        waiver_id="WAIVE-ILLEGAL",
        scope="*",
        pattern="EXEC-GAP-01",
        reason="Attempting to waive blocking scenario leak",
        reviewer="bad_actor",
        version="0.1.0",
    )
    issues = ComprehensiveLeakageScanner.scan_payload(blocking_payload, waivers=[waiver])
    assert any(i.severity == GateSeverity.BLOCKING for i in issues)
    with pytest.raises(LeakageError):
        ComprehensiveLeakageScanner.assert_no_leakage(blocking_payload, waivers=[waiver])


def test_canary_leak_detection():
    # §19 canary testing: planted canary tokens must be blocked
    clean_payload = {"alert_id": "123", "summary": "Clean summary"}
    canary_token = CanaryScanner.generate_canary_token("TEST_UNIT")
    assert "CANARY_TRUTH_" in canary_token
    canary_payload = CanaryScanner.inject_canary_dict(clean_payload, "summary")

    issues = ComprehensiveLeakageScanner.scan_payload(canary_payload)
    assert any("CANARY_TRUTH_" in i.actual for i in issues)
    with pytest.raises(LeakageError):
        ComprehensiveLeakageScanner.assert_no_leakage(canary_payload)


def test_leaked_seed_and_private_metadata():
    """Verify scanner detects leaked master/private seeds, answer keys, and truth metadata."""
    # 1. Leaked master seed or private seed key
    leaky_seed_payload = {
        "alert_id": "123",
        "master_seed": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    }
    issues1 = ComprehensiveLeakageScanner.scan_payload(leaky_seed_payload)
    assert any(i.code == "LEAK_FORBIDDEN_KEY" for i in issues1)
    with pytest.raises(LeakageError):
        ComprehensiveLeakageScanner.assert_no_leakage(leaky_seed_payload)

    # 2. Leaked answer key or expected finding
    leaky_truth_payload = {
        "alert_id": "123",
        "answer_key": "FINDING-CONCERNING-01",
    }
    issues2 = ComprehensiveLeakageScanner.scan_payload(leaky_truth_payload)
    assert any(i.code == "LEAK_FORBIDDEN_KEY" for i in issues2)
    with pytest.raises(LeakageError):
        ComprehensiveLeakageScanner.assert_no_leakage(leaky_truth_payload)

    # 3. Leaked mutation code / authorization id in free text
    leaky_text_payload = {
        "alert_id": "123",
        "notes": "Corrupted under QUAL-AUTH-1234-abcd per test plan",
    }
    issues3 = ComprehensiveLeakageScanner.scan_payload(leaky_text_payload)
    assert any(i.code == "LEAK_SCENARIO_PATTERN" for i in issues3)
    with pytest.raises(LeakageError):
        ComprehensiveLeakageScanner.assert_no_leakage(leaky_text_payload)

