from __future__ import annotations

import uuid

import pytest

from satsa_generator.config.models import load_config
from satsa_generator.core.errors import RelationshipIntegrityError, SchemaContractError
from satsa_generator.fixture.builder import _generate_m2_records, validate_m2_fixture_records
from satsa_generator.ids.service import IDService
from satsa_generator.seeds.manager import SeedManager


@pytest.fixture
def m2_records(fixture_config_path, master_seed):
    config = load_config(fixture_config_path)
    seeds = SeedManager(master_seed)
    ids = IDService(config.dataset_namespace)
    return list(_generate_m2_records(config, seeds, ids))


def test_validate_m2_passes_on_valid_generated_records(m2_records):
    validate_m2_fixture_records(*m2_records)


def test_validate_m2_rejects_empty_family(m2_records):
    # Empty alerts family
    m2_records[8] = []
    with pytest.raises(SchemaContractError, match="must not be empty"):
        validate_m2_fixture_records(*m2_records)


def test_validate_m2_rejects_duplicate_ids(m2_records):
    alerts = list(m2_records[8])
    duplicate_alert = alerts[0].model_copy(update={"alert_id": alerts[1].alert_id})
    m2_records[8] = [duplicate_alert] + alerts[1:]
    with pytest.raises(SchemaContractError, match="duplicate alert_id"):
        validate_m2_fixture_records(*m2_records)


def test_validate_m2_rejects_unknown_organization_on_asset(m2_records):
    assets = list(m2_records[6])
    bad_asset = assets[0].model_copy(update={"organization_id": uuid.uuid4()})
    m2_records[6] = [bad_asset] + assets[1:]
    with pytest.raises(RelationshipIntegrityError, match="references unknown organization"):
        validate_m2_fixture_records(*m2_records)


def test_validate_m2_rejects_mismatched_asset_coverage_ownership(m2_records):
    coverages = list(m2_records[7])
    # Change organization_id on first coverage to another org while keeping asset_id
    orgs = m2_records[0]
    different_org_id = orgs[1].organization_id
    bad_cov = coverages[0].model_copy(update={"organization_id": different_org_id})
    m2_records[7] = [bad_cov] + coverages[1:]
    with pytest.raises(RelationshipIntegrityError, match="does not match asset organization"):
        validate_m2_fixture_records(*m2_records)


def test_validate_m2_rejects_broken_case_alert_link(m2_records):
    links = list(m2_records[10])
    bad_link = links[0].model_copy(update={"alert_id": uuid.uuid4()})
    m2_records[10] = [bad_link] + links[1:]
    with pytest.raises(RelationshipIntegrityError, match="references unknown alert"):
        validate_m2_fixture_records(*m2_records)


def test_validate_m2_rejects_broken_investigation_case_link(m2_records):
    investigations = list(m2_records[11])
    bad_inv = investigations[0].model_copy(update={"case_id": uuid.uuid4()})
    m2_records[11] = [bad_inv] + investigations[1:]
    with pytest.raises(RelationshipIntegrityError, match="references unknown case"):
        validate_m2_fixture_records(*m2_records)


def test_validate_m2_rejects_broken_escalation_link(m2_records):
    escalations = list(m2_records[12])
    bad_esc = escalations[0].model_copy(update={"case_id": uuid.uuid4()})
    m2_records[12] = [bad_esc] + escalations[1:]
    with pytest.raises(RelationshipIntegrityError, match="references unknown case"):
        validate_m2_fixture_records(*m2_records)


def test_validate_m2_rejects_broken_closure_resolution_link(m2_records):
    closures = list(m2_records[15])
    bad_clo = closures[0].model_copy(update={"resolution_id": uuid.uuid4()})
    m2_records[15] = [bad_clo] + closures[1:]
    with pytest.raises(RelationshipIntegrityError, match="references unknown resolution"):
        validate_m2_fixture_records(*m2_records)
