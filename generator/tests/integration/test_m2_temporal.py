from __future__ import annotations

from datetime import timedelta

import pytest

from satsa_generator.config.models import load_config
from satsa_generator.core.errors import TemporalIntegrityError
from satsa_generator.fixture.builder import _generate_m2_records, validate_m2_fixture_records
from satsa_generator.ids.service import IDService
from satsa_generator.seeds.manager import SeedManager


@pytest.fixture
def m2_records(fixture_config_path, master_seed):
    config = load_config(fixture_config_path)
    seeds = SeedManager(master_seed)
    ids = IDService(config.dataset_namespace)
    return list(_generate_m2_records(config, seeds, ids))


def test_validate_m2_rejects_case_created_before_linked_alert(m2_records):
    cases = list(m2_records[9])
    # Shift first case creation to 1 day earlier than its alerts
    bad_case = cases[0].model_copy(
        update={"created_at_utc": cases[0].created_at_utc - timedelta(days=10)}
    )
    m2_records[9] = [bad_case] + cases[1:]
    with pytest.raises(TemporalIntegrityError, match="before linked alert"):
        validate_m2_fixture_records(*m2_records)


def test_validate_m2_rejects_investigation_before_case_creation(m2_records):
    investigations = list(m2_records[11])
    bad_inv = investigations[0].model_copy(
        update={"started_at_utc": investigations[0].started_at_utc - timedelta(days=5)}
    )
    m2_records[11] = [bad_inv] + investigations[1:]
    with pytest.raises(TemporalIntegrityError, match="started before case .* was created"):
        validate_m2_fixture_records(*m2_records)


def test_validate_m2_rejects_investigation_after_case_closure(m2_records):
    investigations = list(m2_records[11])
    bad_inv = investigations[0].model_copy(
        update={"started_at_utc": investigations[0].started_at_utc + timedelta(days=5)}
    )
    m2_records[11] = [bad_inv] + investigations[1:]
    with pytest.raises(TemporalIntegrityError, match="started after case .* was closed"):
        validate_m2_fixture_records(*m2_records)


def test_validate_m2_rejects_escalation_before_case_creation(m2_records):
    escalations = list(m2_records[12])
    bad_esc = escalations[0].model_copy(
        update={"escalated_at_utc": escalations[0].escalated_at_utc - timedelta(days=5)}
    )
    m2_records[12] = [bad_esc] + escalations[1:]
    with pytest.raises(TemporalIntegrityError, match="occurred before case .* was created"):
        validate_m2_fixture_records(*m2_records)


def test_validate_m2_rejects_closure_before_resolution(m2_records):
    closures = list(m2_records[15])
    bad_clo = closures[0].model_copy(
        update={"closed_at_utc": closures[0].closed_at_utc - timedelta(hours=2)}
    )
    m2_records[15] = [bad_clo] + closures[1:]
    with pytest.raises(TemporalIntegrityError, match="occurred before resolution"):
        validate_m2_fixture_records(*m2_records)


def test_validate_m2_rejects_submission_before_period_end(m2_records):
    submissions = list(m2_records[1])
    bad_sub = submissions[0].model_copy(
        update={
            "submitted_at_utc": submissions[0].reporting_period_start_at_utc + timedelta(days=1)
        }
    )
    m2_records[1] = [bad_sub] + submissions[1:]
    with pytest.raises(TemporalIntegrityError, match="before reporting period end"):
        validate_m2_fixture_records(*m2_records)
