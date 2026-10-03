from __future__ import annotations

import json

from satsa_generator.fixture.builder import build_fixture
from satsa_generator.fixture.models import (
    FixtureManifest,
    OrganizationRecord,
    SubmissionManifestRecord,
    SubmissionRecord,
)


def test_serialized_fixture_round_trips_through_strict_contract_models(
    tmp_path, fixture_config_path, master_seed
):
    result = build_fixture(
        fixture_config_path, master_seed, output_root=tmp_path / "fixture"
    )

    family_models = {
        "organizations.json": OrganizationRecord,
        "submissions.json": SubmissionRecord,
        "submission_manifests.json": SubmissionManifestRecord,
    }
    for filename, model in family_models.items():
        rows = json.loads(
            (result.operational_root / filename).read_text(encoding="utf-8")
        )
        assert rows
        assert all(model.model_validate(row) for row in rows)

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    FixtureManifest.model_validate(manifest)
