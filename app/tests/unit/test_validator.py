"""Unit tests for package validation rules."""

from __future__ import annotations

import uuid

from app.backend.validation.validator import EvidencePackageValidator, ValidationResult


def test_validator_file_presence_missing_mandatory():
    validator = EvidencePackageValidator()
    result = ValidationResult()

    # Empty found families set
    validator.validate_file_presence(set(), result)
    assert not result.is_valid
    codes = [i.code for i in result.issues]
    assert "MANDATORY_EVIDENCE_MISSING" in codes


def test_validator_record_schema_missing_pk():
    validator = EvidencePackageValidator()
    result = ValidationResult()

    records = [{"organization_name": "No PK Corp"}]
    validator.validate_record_schema("organizations", records, result)
    assert not result.is_valid
    assert any(i.code == "MISSING_PRIMARY_KEY" for i in result.issues)


def test_validator_record_schema_invalid_uuid():
    validator = EvidencePackageValidator()
    result = ValidationResult()

    records = [{"organization_id": "not-a-valid-uuid", "organization_name": "Bad UUID"}]
    validator.validate_record_schema("organizations", records, result)
    assert not result.is_valid
    assert any(i.code == "INVALID_UUID_PRIMARY_KEY" for i in result.issues)


def test_validator_duplicate_primary_key():
    validator = EvidencePackageValidator()
    result = ValidationResult()

    dup_id = str(uuid.uuid4())
    records = [
        {"alert_id": dup_id, "summary": "Alert 1"},
        {"alert_id": dup_id, "summary": "Alert 1 duplicate"},
    ]
    validator.validate_record_schema("alerts", records, result)
    assert any(i.code == "DUPLICATE_PRIMARY_KEY" for i in result.issues)


def test_validator_referential_integrity():
    validator = EvidencePackageValidator()
    result = ValidationResult()

    records_by_family = {
        "organizations": [{"organization_id": str(uuid.uuid4())}],
        "assets": [{"asset_id": str(uuid.uuid4()), "organization_id": str(uuid.uuid4())}],  # unknown org
        "alerts": [
            {"alert_id": str(uuid.uuid4()), "organization_id": str(uuid.uuid4()), "asset_id": str(uuid.uuid4())}
        ],
    }
    validator.validate_referential_integrity(records_by_family, result)
    assert any(i.code == "ORPHANED_ORGANIZATION_REFERENCE" for i in result.issues)
    assert any(i.code == "ORPHANED_ASSET_REFERENCE" for i in result.issues)


def test_validator_temporal_ordering_violation():
    validator = EvidencePackageValidator()
    result = ValidationResult()

    records_by_family = {
        "cases": [
            {
                "case_id": str(uuid.uuid4()),
                "created_at_utc": "2025-05-01T12:00:00Z",
                "closed_at_utc": "2025-04-01T12:00:00Z",  # closed before created
            }
        ]
    }
    validator.validate_temporal_ordering(records_by_family, result)
    assert any(i.code == "TEMPORAL_ORDERING_VIOLATION" for i in result.issues)
