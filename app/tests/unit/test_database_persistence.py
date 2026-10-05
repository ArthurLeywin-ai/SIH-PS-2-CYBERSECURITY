"""Unit tests for persistence models, repositories, and transactional integrity."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.backend.persistence.models import (
    AlertModel,
    AssetModel,
    CaseAlertLinkModel,
    CaseModel,
    EvidenceProvenanceModel,
    IngestionPackageModel,
    OrganizationModel,
    SubmissionModel,
)
from app.backend.persistence.repositories import (
    EvidenceRepository,
    OrganizationRepository,
    PackageRepository,
    ProvenanceRepository,
    SubmissionRepository,
)
from sqlalchemy import select
from sqlalchemy.orm import Session


def test_package_repository(test_db_session: Session):
    repo = PackageRepository(test_db_session)
    pkg_id = str(uuid.uuid4())
    pkg = IngestionPackageModel(
        package_id=pkg_id,
        package_path="/tmp/pkg",
        package_name="test_pkg",
        tier="deterministic_fixture",
        split="development",
        status="DISCOVERED",
        record_counts={"alerts": 5},
        validation_issues=[],
        discovered_at_utc=datetime.now(UTC),
    )
    repo.create(pkg)
    test_db_session.commit()

    retrieved = repo.get_by_id(pkg_id)
    assert retrieved is not None
    assert retrieved.package_name == "test_pkg"
    assert retrieved.record_counts["alerts"] == 5

    repo.update_status(pkg_id, "COMPLETED")
    test_db_session.commit()

    updated = repo.get_by_id(pkg_id)
    assert updated.status == "COMPLETED"


def test_organization_and_submission_repositories(test_db_session: Session):
    org_repo = OrganizationRepository(test_db_session)
    sub_repo = SubmissionRepository(test_db_session)

    org_id = str(uuid.uuid4())
    org = OrganizationModel(
        organization_id=org_id,
        organization_name="Test Bank",
        sector_code="FINANCIAL",
        scale_band="LARGE",
        operating_model="HYBRID",
        entity_criticality_band="ELEVATED",
        profile_effective_start_at_utc=datetime.now(UTC),
        organization_status="ACTIVE",
    )
    org_repo.create(org)

    sub_id = str(uuid.uuid4())
    sub = SubmissionModel(
        submission_id=sub_id,
        organization_id=org_id,
        period_maturity_state="MATURE",
        reporting_period_start_at_utc=datetime(2025, 1, 1, tzinfo=UTC),
        reporting_period_end_at_utc=datetime(2025, 3, 31, tzinfo=UTC),
    )
    sub_repo.create(sub)
    test_db_session.commit()

    org_list = org_repo.list_all()
    assert len(org_list) >= 1

    subs = sub_repo.list_by_organization(org_id)
    assert len(subs) == 1
    assert subs[0].submission_id == sub_id


def test_evidence_and_case_lifecycle(test_db_session: Session):
    ev_repo = EvidenceRepository(test_db_session)
    org_id = str(uuid.uuid4())
    asset_id = str(uuid.uuid4())
    alert_id = str(uuid.uuid4())
    case_id = str(uuid.uuid4())

    asset = AssetModel(
        asset_id=asset_id,
        organization_id=org_id,
        asset_class="SERVER",
        criticality="CRITICAL",
        operating_status="ACTIVE",
        effective_start_at_utc=datetime.now(UTC),
    )
    alert = AlertModel(
        alert_id=alert_id,
        organization_id=org_id,
        asset_id=asset_id,
        created_at_utc=datetime.now(UTC),
        alert_category="AUTHENTICATION",
        severity="HIGH",
        status="OPEN",
        disposition="UNDETERMINED",
        summary="Suspicious login spike",
    )
    case = CaseModel(
        case_id=case_id,
        organization_id=org_id,
        case_type="INCIDENT",
        severity="HIGH",
        status="IN_PROGRESS",
        disposition="UNDETERMINED",
        created_at_utc=datetime.now(UTC),
    )
    link = CaseAlertLinkModel(
        case_alert_link_id=str(uuid.uuid4()),
        case_id=case_id,
        alert_id=alert_id,
        link_type="PRIMARY",
        linked_at_utc=datetime.now(UTC),
    )

    ev_repo.bulk_insert([asset, alert, case, link])
    test_db_session.commit()

    alerts = ev_repo.list_alerts(organization_id=org_id, severity="HIGH")
    assert len(alerts) == 1
    assert alerts[0].alert_id == alert_id

    fetched_case = ev_repo.get_case_by_id(case_id)
    assert fetched_case is not None
    assert len(fetched_case.alert_links) == 1
    assert fetched_case.alert_links[0].alert_id == alert_id


def test_provenance_repository(test_db_session: Session):
    repo = ProvenanceRepository(test_db_session)
    rec_id = str(uuid.uuid4())
    prov_id = str(uuid.uuid4())

    prov = EvidenceProvenanceModel(
        provenance_id=prov_id,
        canonical_record_id=rec_id,
        evidence_family="alerts",
        organization_id=str(uuid.uuid4()),
        source_file="alerts.json",
        source_record_locator="row:42",
        source_field="source_severity_text",
        raw_source_value="critical",
        canonical_field="severity",
    )
    repo.bulk_create_provenance([prov])
    test_db_session.commit()

    records = repo.get_provenance_by_record_id(rec_id)
    assert len(records) == 1
    assert records[0].source_record_locator == "row:42"
    assert records[0].raw_source_value == "critical"


def test_transaction_rollback(test_db_engine):
    factory = Session(bind=test_db_engine)
    org_id = str(uuid.uuid4())
    org = OrganizationModel(
        organization_id=org_id,
        organization_name="Rollback Corp",
        sector_code="HEALTHCARE",
        scale_band="MEDIUM",
        operating_model="HYBRID",
        entity_criticality_band="STANDARD",
        profile_effective_start_at_utc=datetime.now(UTC),
        organization_status="ACTIVE",
    )
    factory.add(org)
    factory.flush()
    # Explicit rollback
    factory.rollback()

    retrieved = factory.scalar(select(OrganizationModel).where(OrganizationModel.organization_id == org_id))
    assert retrieved is None
    factory.close()
