from __future__ import annotations

import json

from satsa_generator.fixture.builder import build_m2_fixture
from satsa_generator.fixture.models import (
    ActionRecord,
    AlertRecord,
    AssetRecord,
    CaseAlertLinkRecord,
    CaseRecord,
    ClosureRecord,
    ControlProcessReferenceRecord,
    ControlProcessSubjectLinkRecord,
    EscalationRecord,
    ExceptionRecord,
    FixtureManifest,
    InvestigationRecord,
    MonitoringCoverageRecord,
    OrganizationRecord,
    ProcessChangeRecord,
    ResolutionRecord,
    SubmissionFamilyDeclarationRecord,
    SubmissionManifestRecord,
    SubmissionRecord,
)


def test_serialized_m2_fixture_round_trips_through_strict_contract_models(
    tmp_path, fixture_config_path, master_seed
):
    result = build_m2_fixture(fixture_config_path, master_seed, output_root=tmp_path / "m2_fixture")

    family_models = {
        "organizations.json": OrganizationRecord,
        "submissions.json": SubmissionRecord,
        "submission_manifests.json": SubmissionManifestRecord,
        "submission_evidence_families.json": SubmissionFamilyDeclarationRecord,
        "control_process_references.json": ControlProcessReferenceRecord,
        "control_process_subject_links.json": ControlProcessSubjectLinkRecord,
        "assets.json": AssetRecord,
        "monitoring_coverage.json": MonitoringCoverageRecord,
        "alerts.json": AlertRecord,
        "cases.json": CaseRecord,
        "case_alert_links.json": CaseAlertLinkRecord,
        "investigations.json": InvestigationRecord,
        "escalations.json": EscalationRecord,
        "actions.json": ActionRecord,
        "resolutions.json": ResolutionRecord,
        "closures.json": ClosureRecord,
        "exceptions.json": ExceptionRecord,
        "process_changes.json": ProcessChangeRecord,
    }

    for filename, model in family_models.items():
        file_path = result.operational_root / filename
        assert file_path.is_file(), f"Expected file {filename} to exist."
        rows = json.loads(file_path.read_text(encoding="utf-8"))
        assert len(rows) > 0, f"Expected non-empty rows for {filename}."
        for row in rows:
            model.model_validate(row)

    manifest_data = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    manifest = FixtureManifest.model_validate(manifest_data)
    assert manifest.fixture_contract == "SATSA-M2-FIXTURE-V1"
    assert len(manifest.files) == 18
