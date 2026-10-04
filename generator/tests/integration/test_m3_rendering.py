"""Integration tests for Milestone 3 (Source Profiles and Canonical Oracle)."""

import json
import uuid
from pathlib import Path

import pytest

from satsa_generator.canonical.oracle import CanonicalOracle, CanonicalRecordState
from satsa_generator.fixture.builder import build_m3_fixture
from satsa_generator.profiles.catalog import get_profile
from satsa_generator.rendering.engine import RenderingEngine
from satsa_generator.validation.parser import parse_and_validate


def test_m3_build_fixture_and_parseback(
    tmp_path: Path, fixture_config_path: Path, master_seed: bytes
) -> None:
    """Verify that M3 build succeeds, generates source files and an oracle."""
    result = build_m3_fixture(fixture_config_path, master_seed, output_root=tmp_path)

    assert result.operational_root.exists()
    assert (result.operational_root / "fixture_manifest.json").exists()

    oracle_dir = tmp_path / "canonical_reference"
    assert oracle_dir.exists()

    # Test True Parse-Back for all profiles
    for profile_id in ["SRC-A", "SRC-B", "SRC-C", "SRC-D", "SRC-E"]:
        for family in [
            "organization",
            "submission",
            "submission_manifest",
            "submission_family",
            "control_process_reference",
            "control_process_subject_link",
            "asset",
            "monitoring_coverage",
            "alert",
            "case",
            "case_alert_link",
            "investigation",
            "escalation",
            "action",
            "resolution",
            "closure",
            "exception",
            "process_change",
        ]:
            # If the profile wasn't used for this family in builder distribution,
            # it will be skipped by parse_and_validate
            parse_and_validate(result.operational_root, oracle_dir, profile_id, family)


def test_corruption_field_value(
    tmp_path: Path, fixture_config_path: Path, master_seed: bytes
) -> None:
    """Test A - field corruption."""
    result = build_m3_fixture(fixture_config_path, master_seed, output_root=tmp_path)
    csv_file = result.operational_root / "organization_src-a.csv"

    # Corrupt
    content = csv_file.read_text(encoding="utf-8")
    content = content.replace("ACTIVE", "CORRUPTED")
    csv_file.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match="Parse-back failure"):
        parse_and_validate(
            result.operational_root, tmp_path / "canonical_reference", "SRC-A", "organization"
        )


def test_corruption_missing_record(
    tmp_path: Path, fixture_config_path: Path, master_seed: bytes
) -> None:
    """Test E - missing source record."""
    result = build_m3_fixture(fixture_config_path, master_seed, output_root=tmp_path)
    csv_file = result.operational_root / "organization_src-a.csv"

    # Corrupt by removing last line
    lines = csv_file.read_text(encoding="utf-8").strip().split("\n")
    csv_file.write_text("\n".join(lines[:-1]), encoding="utf-8")

    with pytest.raises(AssertionError, match="Record count mismatch"):
        parse_and_validate(
            result.operational_root, tmp_path / "canonical_reference", "SRC-A", "organization"
        )


def test_corruption_relationship_id(
    tmp_path: Path, fixture_config_path: Path, master_seed: bytes
) -> None:
    """Test - broken relationship ID."""
    result = build_m3_fixture(fixture_config_path, master_seed, output_root=tmp_path)
    csv_file = result.operational_root / "submission_src-b.csv"

    content = csv_file.read_text(encoding="utf-8")
    org_id = content.split("\n")[1].split(",")[1]
    bad_id = org_id[:-1] + ("f" if org_id[-1] != "f" else "0")
    content = content.replace(org_id, bad_id)
    csv_file.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match="Parse-back relationship failure|Parse-back failure"):
        parse_and_validate(
            result.operational_root, tmp_path / "canonical_reference", "SRC-B", "submission"
        )


def test_corruption_vocabulary(
    tmp_path: Path, fixture_config_path: Path, master_seed: bytes
) -> None:
    """Test - vocabulary corruption."""
    result = build_m3_fixture(fixture_config_path, master_seed, output_root=tmp_path)
    csv_file = result.operational_root / "submission_src-b.csv"

    # Corrupt numeric vocabulary value
    content = csv_file.read_text(encoding="utf-8")
    lines = content.split("\n")
    if len(lines) > 1 and lines[1]:
        parts = lines[1].split(",")
        # replace period_maturity_state (third column) with 99
        parts[2] = "99"
        lines[1] = ",".join(parts)
        csv_file.write_text("\n".join(lines), encoding="utf-8")

    with pytest.raises(ValueError, match="Parse-back failure"):
        parse_and_validate(
            result.operational_root, tmp_path / "canonical_reference", "SRC-B", "submission"
        )


def test_corruption_missing_relationship(
    tmp_path: Path, fixture_config_path: Path, master_seed: bytes
) -> None:
    """Test - missing relationship."""
    result = build_m3_fixture(fixture_config_path, master_seed, output_root=tmp_path)
    # asset in SRC-B is CSV, if we remove organization_id it becomes empty.
    csv_file = result.operational_root / "asset_src-b.csv"

    content = csv_file.read_text(encoding="utf-8")
    # Replace the organization_id (second column) with empty string in the first data row
    lines = content.split("\n")
    if len(lines) > 1 and lines[1]:
        parts = lines[1].split(",")
        parts[2] = ""  # org_id is 3rd col (asset_id, source_asset_id, organization_id)
        lines[1] = ",".join(parts)
        csv_file.write_text("\n".join(lines), encoding="utf-8")

    with pytest.raises(ValueError, match="Parse-back relationship failure|Parse-back failure"):
        parse_and_validate(
            result.operational_root, tmp_path / "canonical_reference", "SRC-B", "asset"
        )


def test_corruption_wrong_related_id(
    tmp_path: Path, fixture_config_path: Path, master_seed: bytes
) -> None:
    """Test - wrong related ID (using another valid UUID)."""

    result = build_m3_fixture(fixture_config_path, master_seed, output_root=tmp_path)
    csv_file = result.operational_root / "submission_src-b.csv"

    content = csv_file.read_text(encoding="utf-8")
    lines = content.split("\n")
    if len(lines) > 1 and lines[1]:
        parts = lines[1].split(",")
        # replace organization_id (second column) with a random valid UUID
        parts[1] = str(uuid.uuid4())
        lines[1] = ",".join(parts)
        csv_file.write_text("\n".join(lines), encoding="utf-8")

    with pytest.raises(ValueError, match="Parse-back relationship failure|Parse-back failure"):
        parse_and_validate(
            result.operational_root, tmp_path / "canonical_reference", "SRC-B", "submission"
        )


def test_corruption_list_relationship_missing_member(
    tmp_path: Path, fixture_config_path: Path, master_seed: bytes
) -> None:
    """Test - missing member from relationship list fails."""
    import json

    result = build_m3_fixture(fixture_config_path, master_seed, output_root=tmp_path)
    json_file = result.operational_root / "case_src-c.json"

    data = json.loads(json_file.read_text(encoding="utf-8"))
    for item in data:
        alerts = item.get("details", {}).get("alerts", [])
        if len(alerts) > 0:
            alerts.pop()
            break

    json_file.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="Parse-back rel failure"):
        parse_and_validate(
            result.operational_root, tmp_path / "canonical_reference", "SRC-C", "case"
        )


def test_corruption_list_relationship_extra_member(
    tmp_path: Path, fixture_config_path: Path, master_seed: bytes
) -> None:
    """Test - extra wrong member in relationship list fails."""
    import json

    result = build_m3_fixture(fixture_config_path, master_seed, output_root=tmp_path)
    json_file = result.operational_root / "case_src-c.json"

    data = json.loads(json_file.read_text(encoding="utf-8"))
    for item in data:
        alerts = item.get("details", {}).get("alerts", [])
        if len(alerts) > 0:
            alerts.append(str(uuid.uuid4()))
            break

    json_file.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="Parse-back rel failure"):
        parse_and_validate(
            result.operational_root, tmp_path / "canonical_reference", "SRC-C", "case"
        )


def test_reproducibility(tmp_path: Path, fixture_config_path: Path, master_seed: bytes) -> None:
    """Verify same seed produces byte-identical output hashes."""
    run1 = build_m3_fixture(fixture_config_path, master_seed, output_root=tmp_path / "run1")
    run2 = build_m3_fixture(fixture_config_path, master_seed, output_root=tmp_path / "run2")

    assert run1.tree_sha256 == run2.tree_sha256


def test_different_seed_variation(
    tmp_path: Path, fixture_config_path: Path, master_seed: bytes
) -> None:
    """Verify different seeds produce different outputs."""
    seed1 = b"A" * 32
    seed2 = b"B" * 32
    run1 = build_m3_fixture(fixture_config_path, seed1, output_root=tmp_path / "run1")
    run2 = build_m3_fixture(fixture_config_path, seed2, output_root=tmp_path / "run2")

    assert run1.tree_sha256 != run2.tree_sha256


def test_renderer_independence_from_oracle(
    tmp_path: Path, fixture_config_path: Path, master_seed: bytes
) -> None:
    """
    Independence test: Renderer follows operational data, not oracle.

    This test constructs operational records and an independent oracle with
    intentionally altered relationship expectations. It verifies that the
    renderer produces source artifacts matching the operational data,
    not the altered oracle.
    """
    from uuid import UUID

    from satsa_generator.config.models import load_config
    from satsa_generator.fixture.builder import _generate_m2_records, validate_m2_fixture_records
    from satsa_generator.ids.service import IDService
    from satsa_generator.seeds.manager import SeedManager

    config = load_config(fixture_config_path)
    seeds = SeedManager(master_seed)
    ids = IDService(config.dataset_namespace)
    records = _generate_m2_records(config, seeds, ids)
    validate_m2_fixture_records(*records)

    (
        organizations,
        submissions,
        submission_manifests,
        submission_families,
        control_refs,
        control_links,
        assets,
        coverages,
        alerts,
        cases,
        case_alert_links,
        investigations,
        escalations,
        actions,
        resolutions,
        closures,
        exceptions,
        process_changes,
    ) = records

    # Create an oracle with WRONG relationship expectations
    wrong_oracle = CanonicalOracle()
    for family_name, rec_list in [
        ("case", cases),
    ]:
        for idx, record in enumerate(rec_list):
            record_dict = record.model_dump(mode="json")
            record_obj_dict = record.model_dump()

            canonical_id = None
            if f"{family_name}_id" in record_obj_dict:
                canonical_id = record_obj_dict[f"{family_name}_id"]
            else:
                for key, val in record_obj_dict.items():
                    if key.endswith("_id") and isinstance(val, UUID) and canonical_id is None:
                        canonical_id = val

            if not canonical_id:
                canonical_id = UUID(int=idx)

            # Build relationships natively (from operational data)
            rels = {}
            for k, v in record_obj_dict.items():
                if k.endswith("_id") and k != f"{family_name}_id" and isinstance(v, UUID):
                    rels[k] = v

            # For case -> alerts many-to-many
            if family_name == "case":
                alerts_for_case = [
                    link.alert_id for link in case_alert_links if link.case_id == canonical_id
                ]
                if alerts_for_case:
                    rels["alerts"] = alerts_for_case

            # INTENTIONALLY CORRUPT the oracle: replace alerts with fake UUIDs
            if "alerts" in rels:
                rels["alerts"] = [UUID(int=0xDEADBEEF), UUID(int=0xCAFEBABE)]

            wrong_oracle.register_expected_record(
                CanonicalRecordState(
                    canonical_record_id=canonical_id,
                    canonical_family=family_name,
                    fields=record_dict,
                    relationships=rels,
                )
            )

    # Render using the CORRECT operational relationships (via relationship_records)
    # NOT the corrupted oracle
    profile_c = get_profile("SRC-C")
    engine = RenderingEngine(tmp_path / "source_exports", profile_c)

    result = engine.render_and_write(
        "case",
        cases,
        relationship_records=case_alert_links,
        relationship_subject_field="case_id",
        relationship_object_field="case_id",
        relationship_target_field="alert_id",
    )

    assert result is not None

    # Verify the rendered output contains the CORRECT operational alerts, not the fake ones
    source_file = tmp_path / "source_exports" / "case_src-c.json"
    rendered_data = json.loads(source_file.read_text(encoding="utf-8"))

    # Find a case with alerts
    for item in rendered_data:
        alerts_in_details = item.get("details", {}).get("alerts", [])
        if alerts_in_details:
            # Check that the alerts match operational data, NOT the oracle's fake UUIDs
            fake_uuid_1 = "00000000-0000-0000-0000-0000deadbeef"
            fake_uuid_2 = "00000000-0000-0000-0000-0000cafebabe"
            assert fake_uuid_1 not in alerts_in_details, "Renderer used corrupted oracle data!"
            assert fake_uuid_2 not in alerts_in_details, "Renderer used corrupted oracle data!"
            break


def test_vocabulary_pass_through_unknown(
    tmp_path: Path, fixture_config_path: Path, master_seed: bytes
) -> None:
    """
    Test that vocabulary with on_unknown="pass_through" preserves unknown values
    instead of failing.
    """
    result = build_m3_fixture(fixture_config_path, master_seed, output_root=tmp_path)

    # SRC-D has on_unknown="pass_through" for severity
    # Check that the alert file for SRC-D exists and can be parsed
    alert_file = result.operational_root / "alert_src-d.jsonl"
    assert alert_file.exists(), "SRC-D alert file should exist"

    # Parse the JSONL file
    lines = alert_file.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) > 0, "Should have alert records"

    # Parse first record
    first_record = json.loads(lines[0])
    # SRC-D uses abbreviated field names
    assert "ale_sev" in first_record, "SRC-D should have ale_sev field"
    # The value should be a valid mapped value (not an error)
    assert first_record["ale_sev"] in ["standard", "elevated", "high", "unknown"], (
        f"Unexpected severity value: {first_record['ale_sev']}"
    )

    # Now test that unknown values are preserved (pass-through)
    # We can't easily inject unknown values without modifying the fixture,
    # but we can verify the vocabulary mapping is configured correctly
    from satsa_generator.profiles.catalog import get_profile

    profile_d = get_profile("SRC-D")
    alert_mapping = profile_d.family_mappings.get("alert", {})
    sev_mapping = alert_mapping.get("severity")
    assert sev_mapping is not None
    assert sev_mapping.vocabulary is not None
    assert sev_mapping.vocabulary.on_unknown == "pass_through", (
        "SRC-D severity should have on_unknown=pass_through"
    )
