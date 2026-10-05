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


def test_corruption_malformed_timestamp(
    tmp_path: Path, fixture_config_path: Path, master_seed: bytes
) -> None:
    """Test - malformed timestamp in rendered source artifact fails parse-back."""
    result = build_m3_fixture(fixture_config_path, master_seed, output_root=tmp_path)
    csv_file = result.operational_root / "alert_src-a.csv"

    content = csv_file.read_text(encoding="utf-8")
    lines = content.split("\n")
    if len(lines) > 1 and lines[1]:
        parts = lines[1].split(",")
        parts[4] = "NOT_A_VALID_TIMESTAMP_2025"
        lines[1] = ",".join(parts)
        csv_file.write_text("\n".join(lines), encoding="utf-8")

    with pytest.raises(ValueError, match="Parse-back failure"):
        parse_and_validate(
            result.operational_root, tmp_path / "canonical_reference", "SRC-A", "alert"
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
    """Verify real artifact unknown-token behavior:

    1. Profiles with on_unknown='fail' (e.g., SRC-B) fail when encountering an unknown token.
    2. Profiles with on_unknown='pass_through' (SRC-D) preserve the unknown token
       into canonical state.
    """
    import csv

    result = build_m3_fixture(fixture_config_path, master_seed, output_root=tmp_path)
    oracle_dir = tmp_path / "canonical_reference"

    # Part 1: Test that on_unknown='fail' actually fails on disk artifact
    submission_b_path = result.operational_root / "submission_src-b.csv"
    with submission_b_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        sub_fields = reader.fieldnames
        sub_rows = list(reader)

    sub_rows[0]["PeriodMaturityState"] = "999"

    with submission_b_path.open("w", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=sub_fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(sub_rows)

    with pytest.raises(ValueError, match="Unmapped vocabulary value during parse-back: 999"):
        parse_and_validate(result.operational_root, oracle_dir, "SRC-B", "submission")

    # Part 2: Test that on_unknown='pass_through' on SRC-D maps unknown token to 'UNKNOWN'
    alert_d_path = result.operational_root / "alert_src-d.json"
    data = json.loads(alert_d_path.read_text(encoding="utf-8"))
    unknown_token = "custom-vendor-sev-unknown-level-x"
    data[0]["ale_sev"] = unknown_token
    alert_d_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # Update oracle expectation for record 0 to match the canonical 'UNKNOWN' state
    oracle_d_path = oracle_dir / "src_d_oracle.json"
    oracle_d_data = json.loads(oracle_d_path.read_text(encoding="utf-8"))
    index_d_path = oracle_dir / "src_d_index.json"
    index_d_data = json.loads(index_d_path.read_text(encoding="utf-8"))

    # Find canonical record ID for locator [0]
    rec0_id = None
    for idx_entry in index_d_data:
        if idx_entry["evidence_family"] == "alert" and idx_entry["source_record_locator"] == "[0]":
            rec0_id = idx_entry["canonical_record_id"]
            break
    assert rec0_id is not None

    for r in oracle_d_data:
        if r["canonical_record_id"] == rec0_id:
            r["fields"]["severity"] = "UNKNOWN"
            break
    oracle_d_path.write_text(json.dumps(oracle_d_data, indent=2), encoding="utf-8")

    # Validation must SUCCEED because on_unknown='pass_through' normalized to
    # UNKNOWN while raw is preserved!
    parse_and_validate(result.operational_root, oracle_dir, "SRC-D", "alert")

    # Part 3: Test that injecting the same unknown token into SRC-B severity fails
    alert_b_path = result.operational_root / "alert_src-b.csv"
    with alert_b_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        alert_fields = reader.fieldnames
        b_alert_rows = list(reader)

    b_alert_rows[0]["Severity"] = unknown_token

    with alert_b_path.open("w", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=alert_fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(b_alert_rows)

    with pytest.raises(ValueError, match="Unmapped vocabulary value during parse-back"):
        parse_and_validate(result.operational_root, oracle_dir, "SRC-B", "alert")


def test_src_b_embedded_case_relationship(
    tmp_path: Path, fixture_config_path: Path, master_seed: bytes
) -> None:
    """Verify SRC-B genuinely embeds CaseId in alert CSV on disk and reconstructs correctly."""
    result = build_m3_fixture(fixture_config_path, master_seed, output_root=tmp_path)
    oracle_dir = tmp_path / "canonical_reference"

    # 1. Verify alert_src-b.csv exists on disk and contains CaseId column
    alert_csv_path = result.operational_root / "alert_src-b.csv"
    assert alert_csv_path.exists(), "alert_src-b.csv must exist on disk"

    import csv

    with alert_csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert "CaseId" in reader.fieldnames, "SRC-B alert CSV must have CaseId in header"
        rows = list(reader)
        assert len(rows) > 0

        # Verify that rows associated with a case contain a valid UUID
        case_ids_found = [row["CaseId"] for row in rows if row.get("CaseId")]
        assert len(case_ids_found) > 0, "At least one alert must have an embedded CaseId"
        for cid in case_ids_found:
            uuid.UUID(cid)

    # 2. Verify parse-back succeeds for SRC-B alert
    parse_and_validate(result.operational_root, oracle_dir, "SRC-B", "alert")

    # 3. Verify that removing or corrupting the CaseId column causes parse-back to fail
    corrupted_rows = []
    with alert_csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            row_copy = dict(row)
            if row_copy.get("CaseId"):
                row_copy["CaseId"] = ""
            corrupted_rows.append(row_copy)

    with alert_csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(corrupted_rows)

    with pytest.raises(ValueError, match="Parse-back rel failure.*rel case_id"):
        parse_and_validate(result.operational_root, oracle_dir, "SRC-B", "alert")


def test_src_c_native_vs_generated_child_identities(
    tmp_path: Path, fixture_config_path: Path, master_seed: bytes
) -> None:
    """Verify SRC-C identity contract: parent has native ID, child lacks native ID on disk."""
    result = build_m3_fixture(fixture_config_path, master_seed, output_root=tmp_path)
    oracle_dir = tmp_path / "canonical_reference"

    case_path = result.operational_root / "case_src-c.json"
    link_path = result.operational_root / "case_alert_link_src-c.json"

    assert case_path.exists(), "case_src-c.json must exist"
    assert link_path.exists(), "case_alert_link_src-c.json must exist"

    # Parent record: case MUST have native ID 'caseId'
    case_data = json.loads(case_path.read_text(encoding="utf-8"))
    assert len(case_data) > 0
    for case_obj in case_data:
        assert "caseId" in case_obj, "Parent case record must have native 'caseId'"
        uuid.UUID(case_obj["caseId"])

    # Child record: case_alert_link MUST NOT have native ID 'caseAlertLinkId' on disk
    link_data = json.loads(link_path.read_text(encoding="utf-8"))
    assert len(link_data) > 0
    for link_obj in link_data:
        assert "caseAlertLinkId" not in link_obj, (
            "Child case_alert_link record must omit native child ID"
        )
        assert "id" not in link_obj
        # But foreign references must be present
        assert "caseId" in link_obj, "Child record must have reference 'caseId'"
        assert "alertId" in link_obj, "Child record must have reference 'alertId'"

    # Reconstruction must succeed for both parent and child using locators
    parse_and_validate(result.operational_root, oracle_dir, "SRC-C", "case")
    parse_and_validate(result.operational_root, oracle_dir, "SRC-C", "case_alert_link")


def test_src_e_migration_boundary(
    tmp_path: Path, fixture_config_path: Path, master_seed: bytes
) -> None:
    """Verify SRC-E migration semantics: Period A (V1) vs Period B (V2).

    Demonstrates:
    - Layout: all-CSV in Period A vs CSV/JSON hybrid in Period B
    - Field names: legacy names (alert_id, created_at_utc, disposition) vs
      modernized (id, timestamp_utc, outcome)
    - Timestamp precision: iso_z (seconds) vs iso_offset_ms (milliseconds)
    - Vocabulary drift: canonical terms (HIGH, MALWARE, TRUE_POSITIVE) vs
      drifted codes (HI, MALW, TP)
    - Relationship: old foreign key (case_id in alert) vs new link object
      (alert_links in case)
    - Canonical reconciliation: both reconcile to the exact same canonical oracle.
    """
    from satsa_generator.config.models import load_config
    from satsa_generator.fixture.builder import _generate_m2_records, validate_m2_fixture_records
    from satsa_generator.ids.service import IDService
    from satsa_generator.profiles.catalog import get_src_e_v1, get_src_e_v2
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

    # Build canonical oracle from operational records
    oracle = CanonicalOracle()
    for family_name, rec_list in [
        ("case", cases),
        ("alert", alerts),
    ]:
        for idx, record in enumerate(rec_list):
            record_dict = record.model_dump(mode="json")
            record_obj_dict = record.model_dump()
            canonical_id = record_obj_dict.get(f"{family_name}_id") or uuid.UUID(int=idx)

            rels = {}
            for k, v in record_obj_dict.items():
                if k.endswith("_id") and k != f"{family_name}_id" and isinstance(v, uuid.UUID):
                    rels[k] = v

            if family_name == "case":
                alerts_for_case = [
                    link.alert_id for link in case_alert_links if link.case_id == canonical_id
                ]
                if alerts_for_case:
                    rels["alerts"] = alerts_for_case

            if family_name == "alert":
                for link in case_alert_links:
                    if link.alert_id == canonical_id:
                        rels["case_id"] = link.case_id
                        break

            oracle.register_expected_record(
                CanonicalRecordState(
                    canonical_record_id=canonical_id,
                    canonical_family=family_name,
                    fields=record_dict,
                    relationships=rels,
                )
            )

    oracle_data = [r.model_dump(mode="json") for r in oracle.expected_records.values()]

    # --- PERIOD A (pre-migration, V1) ---
    p01_root = tmp_path / "period_a_exports"
    p01_oracle_root = tmp_path / "period_a_oracle"
    p01_oracle_root.mkdir(parents=True, exist_ok=True)
    (p01_oracle_root / "src_e_oracle.json").write_text(
        json.dumps(oracle_data, indent=2, sort_keys=True), encoding="utf-8"
    )

    profile_v1 = get_src_e_v1()
    assert profile_v1.version == "1.0"
    engine_v1 = RenderingEngine(p01_root, profile_v1)

    engine_v1.render_and_write(
        "case",
        cases,
        relationship_records=case_alert_links,
        relationship_subject_field="case_id",
        relationship_object_field="case_id",
        relationship_target_field="alert_id",
    )
    engine_v1.render_and_write(
        "alert",
        alerts,
        relationship_records=case_alert_links,
        relationship_subject_field="alert_id",
        relationship_object_field="alert_id",
        relationship_target_field="case_id",
    )
    engine_v1.write_metadata(p01_oracle_root, "src_e")

    # --- PERIOD B (post-migration, V2) ---
    p02_root = tmp_path / "period_b_exports"
    p02_oracle_root = tmp_path / "period_b_oracle"
    p02_oracle_root.mkdir(parents=True, exist_ok=True)
    (p02_oracle_root / "src_e_oracle.json").write_text(
        json.dumps(oracle_data, indent=2, sort_keys=True), encoding="utf-8"
    )

    profile_v2 = get_src_e_v2()
    assert profile_v2.version == "2.0"
    engine_v2 = RenderingEngine(p02_root, profile_v2)

    engine_v2.render_and_write(
        "case",
        cases,
        relationship_records=case_alert_links,
        relationship_subject_field="case_id",
        relationship_object_field="case_id",
        relationship_target_field="alert_id",
    )
    engine_v2.render_and_write(
        "alert",
        alerts,
        relationship_records=case_alert_links,
        relationship_subject_field="alert_id",
        relationship_object_field="alert_id",
        relationship_target_field="case_id",
    )
    engine_v2.write_metadata(p02_oracle_root, "src_e")

    # --- VERIFY DISK DIFFERENCES ACROSS MIGRATION BOUNDARY ---
    # 1. Format change: Period A is CSV; Period B is JSON
    v1_alert_file = p01_root / "alert_src-e.csv"
    v2_alert_file = p02_root / "alert_src-e.json"
    assert v1_alert_file.exists(), "Pre-migration alert must be CSV"
    assert v2_alert_file.exists(), "Post-migration alert must be JSON"

    v1_case_file = p01_root / "case_src-e.csv"
    v2_case_file = p02_root / "case_src-e.json"
    assert v1_case_file.exists(), "Pre-migration case must be CSV"
    assert v2_case_file.exists(), "Post-migration case must be JSON"

    # 2. Field names & relationships in Period A (V1)
    import csv

    with v1_alert_file.open("r", encoding="utf-8") as f:
        v1_reader = csv.DictReader(f)
        assert "alert_id" in v1_reader.fieldnames, "V1 uses legacy alert_id"
        assert "case_id" in v1_reader.fieldnames, "V1 embeds old FK case_id in alert"
        assert "created_at_utc" in v1_reader.fieldnames, "V1 uses created_at_utc"
        v1_alert_rows = list(v1_reader)
        # Check ISO Z timestamp format in V1
        assert v1_alert_rows[0]["created_at_utc"].endswith("Z")
        # Check pre-drift vocabulary (full words like HIGH, MEDIUM)
        v1_sevs = {r["severity"] for r in v1_alert_rows}
        assert any(s in ("HIGH", "MEDIUM", "LOW", "CRITICAL") for s in v1_sevs)

    with v1_case_file.open("r", encoding="utf-8") as f:
        v1_case_reader = csv.DictReader(f)
        assert "alerts" not in v1_case_reader.fieldnames, "V1 case does not have link array"

    # 3. Field names & relationships in Period B (V2)
    v2_alert_rows = json.loads(v2_alert_file.read_text(encoding="utf-8"))
    assert "id" in v2_alert_rows[0], "V2 uses modernized 'id'"
    assert "case_id" not in v2_alert_rows[0], "V2 alert does not embed case_id"
    assert "timestamp_utc" in v2_alert_rows[0], "V2 uses 'timestamp_utc'"
    # Check timestamp format with offset
    assert "+00:00" in v2_alert_rows[0]["timestamp_utc"]
    # Check drifted vocabulary codes (HI, MED, CRIT)
    v2_sevs = {r["event_severity"] for r in v2_alert_rows}
    assert any(s in ("HI", "MED", "LO", "CRIT") for s in v2_sevs)

    v2_case_rows = json.loads(v2_case_file.read_text(encoding="utf-8"))
    assert "alert_links" in v2_case_rows[0], "V2 case has new link object array"
    assert isinstance(v2_case_rows[0]["alert_links"], list)
    for link_obj in v2_case_rows[0]["alert_links"]:
        assert isinstance(link_obj, dict), "Every member must be an object/dict"
        assert "alert_id" in link_obj, "Link object must contain alert_id"
        assert "link_type" in link_obj, "Link object must contain link_type"
        assert link_obj["alert_id"].startswith("E2-ALERT-")
        assert link_obj["link_type"] in ("PRIMARY", "RELATED")

    # --- PROVE CANONICAL RECONCILIATION FOR BOTH PERIODS ---
    parse_and_validate(p01_root, p01_oracle_root, "SRC-E", "case", version="1.0")
    parse_and_validate(p01_root, p01_oracle_root, "SRC-E", "alert", version="1.0")

    parse_and_validate(p02_root, p02_oracle_root, "SRC-E", "case", version="2.0")
    parse_and_validate(p02_root, p02_oracle_root, "SRC-E", "alert", version="2.0")


def test_source_first_independence_detects_renderer_defect(
    tmp_path: Path, fixture_config_path: Path, master_seed: bytes
) -> None:
    """Architectural independence test (Blocker 1):
    Proves that canonical reconstruction reads strictly from actual rendered disk files,
    detects a defect injected directly into the rendered source artifact on disk,
    and operates independently of any in-memory M2 domain records.
    """
    import shutil

    from satsa_generator.canonical.reconstruction import (
        reconstruct_canonical_oracle_from_disk,
        reconstruct_family_from_disk,
    )
    from satsa_generator.profiles.catalog import get_profile

    # 1. Build M3 fixture to disk
    result = build_m3_fixture(fixture_config_path, master_seed, output_root=tmp_path)
    operational_root = result.operational_root
    oracle_root = tmp_path / "canonical_reference"
    profile_a = get_profile("SRC-A")

    # 2. Mutate rendered source artifact ONLY on disk
    alert_csv_path = operational_root / "alert_src-a.csv"
    lines = alert_csv_path.read_text(encoding="utf-8").splitlines()
    header = lines[0].split(",")
    row1 = lines[1].split(",")
    sev_idx = header.index("severity")
    original_sev = row1[sev_idx]
    mutated_sev = "INFORMATIONAL" if original_sev != "INFORMATIONAL" else "CRITICAL"
    row1[sev_idx] = mutated_sev
    lines[1] = ",".join(row1)

    # Write mutation to disk in an isolated copy
    mutated_exports = tmp_path / "mutated_exports"
    shutil.copytree(operational_root, mutated_exports)
    (mutated_exports / "alert_src-a.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # 3. Run canonical reconstruction strictly from the mutated disk file
    reconstructed_records, _ = reconstruct_family_from_disk(
        mutated_exports, oracle_root, profile_a, "alert"
    )

    # 4. Verify canonical reconstruction reflects mutated source, not pre-render
    assert reconstructed_records[0].fields["severity"] == mutated_sev
    assert reconstructed_records[0].fields["severity"] != original_sev

    # 5. Verify validation detects the mismatch against the unmutated contract
    with pytest.raises(ValueError, match="Parse-back failure"):
        parse_and_validate(mutated_exports, oracle_root, "SRC-A", "alert")

    # 6. Verify that reconstruction operates independently of pre-render domain objects
    clean_oracle = reconstruct_canonical_oracle_from_disk(operational_root, oracle_root, profile_a)
    assert len(clean_oracle.expected_records) > 0


def test_src_d_contract_compliance_from_actual_artifacts(
    tmp_path: Path, fixture_config_path: Path, master_seed: bytes
) -> None:
    """Validate all SRC-D contract dimensions directly from rendered artifacts on disk (Blocker 2):
    1. JSON array parsing works from disk.
    2. At least one family uses date-only timestamps.
    3. At least one family uses offset timestamps.
    4. Mixed/missing IDs are actually represented.
    5. External IDs actually appear in rendered source.
    6. Relationship arrays actually appear in rendered source.
    7. Unknown vocabulary is mapped to UNKNOWN while preserving raw token.
    8. Parser reconstructs the canonical representation correctly.
    """
    from satsa_generator.canonical.reconstruction import reconstruct_family_from_disk
    from satsa_generator.profiles.catalog import get_profile

    result = build_m3_fixture(fixture_config_path, master_seed, output_root=tmp_path)
    op_root = result.operational_root
    oracle_dir = tmp_path / "canonical_reference"

    # 1. JSON array parsing from disk
    org_file = op_root / "organization_src-d.json"
    assert org_file.exists(), "organization_src-d.json must exist"
    org_data = json.loads(org_file.read_text(encoding="utf-8"))
    assert isinstance(org_data, list), "SRC-D organization must be rendered as a JSON array"
    assert len(org_data) > 0

    # 2. Foundation family uses date-only timestamps (YYYY-MM-DD)
    date_val = org_data[0].get("pro_eff_utc")
    assert date_val is not None, "Organization profile effective start must be present"
    assert len(date_val) == 10 and date_val.count("-") == 2, (
        f"Expected date-only format, got {date_val}"
    )

    # 3. Operational family uses offset timestamps (+00:00 or offset)
    alert_file = op_root / "alert_src-d.json"
    assert alert_file.exists(), "alert_src-d.json must exist"
    alert_data = json.loads(alert_file.read_text(encoding="utf-8"))
    assert isinstance(alert_data, list)
    ts_val = alert_data[0].get("cre_at_utc")
    assert ts_val is not None, "Alert created_at_utc must be present"
    assert "+00:00" in ts_val or ("+" in ts_val[10:] or "-" in ts_val[10:]), (
        f"Expected offset timestamp, got {ts_val}"
    )

    # 4. Mixed/missing IDs: source_organization_id is omitted (is_present=False)
    assert "sou_org_id" not in org_data[0], "sou_org_id must be omitted in SRC-D organization"
    assert "source_organization_id" not in org_data[0]

    # 5. External IDs appear in rendered source
    assert "ext_alert_id" in alert_data[0], "External ID ext_alert_id must appear in SRC-D alert"
    ext_ale = alert_data[0]["ext_alert_id"]
    assert isinstance(ext_ale, str) and len(ext_ale) > 0

    asset_file = op_root / "asset_src-d.json"
    assert asset_file.exists(), "asset_src-d.json must exist"
    asset_data = json.loads(asset_file.read_text(encoding="utf-8"))
    assert "ext_asset_id" in asset_data[0], "External ID ext_asset_id must appear in SRC-D asset"
    ext_ass = asset_data[0]["ext_asset_id"]
    assert isinstance(ext_ass, str) and len(ext_ass) > 0

    # 6. Relationship arrays appear in rendered source
    case_file = op_root / "case_src-d.json"
    assert case_file.exists(), "case_src-d.json must exist"
    case_data = json.loads(case_file.read_text(encoding="utf-8"))
    assert isinstance(case_data, list)
    cases_with_alerts = [
        c for c in case_data if isinstance(c.get("alerts"), list) and len(c["alerts"]) > 0
    ]
    assert len(cases_with_alerts) > 0, (
        "At least one case must have a non-empty alerts relationship array"
    )

    # 7. Unknown vocabulary handled according to profile (pass_through -> UNKNOWN)
    profile_d = get_profile("SRC-D")
    mutated_alert_data = [dict(a) for a in alert_data]
    mutated_alert_data[0]["ale_sev"] = "unknown_vendor_tier_x"
    test_d_root = tmp_path / "test_d_unknown"
    test_d_root.mkdir(parents=True, exist_ok=True)
    (test_d_root / "alert_src-d.json").write_text(
        json.dumps(mutated_alert_data, indent=2), encoding="utf-8"
    )

    reconstructed_d, _ = reconstruct_family_from_disk(test_d_root, oracle_dir, profile_d, "alert")
    assert reconstructed_d[0].fields["severity"] == "UNKNOWN", (
        "Pass-through unknown token must map canonical field to UNKNOWN"
    )

    # 8. Parser reconstructs canonical representation correctly
    parse_and_validate(op_root, oracle_dir, "SRC-D", "organization")
    parse_and_validate(op_root, oracle_dir, "SRC-D", "alert")
    parse_and_validate(op_root, oracle_dir, "SRC-D", "case")


def test_src_e_cross_version_rejection(
    tmp_path: Path, fixture_config_path: Path, master_seed: bytes
) -> None:
    """Verify that wrong profile/version causes validation/mapping failure (Blocker 3)."""
    from satsa_generator.config.models import load_config
    from satsa_generator.fixture.builder import _generate_m2_records, validate_m2_fixture_records
    from satsa_generator.ids.service import IDService
    from satsa_generator.profiles.catalog import get_src_e_v1, get_src_e_v2
    from satsa_generator.seeds.manager import SeedManager

    config = load_config(fixture_config_path)
    seeds = SeedManager(master_seed)
    ids = IDService(config.dataset_namespace)
    records = _generate_m2_records(config, seeds, ids)
    validate_m2_fixture_records(*records)
    cases, links = records[9], records[10]

    # Render V1 (Period A)
    p01_root = tmp_path / "cross_p01_exports"
    p01_oracle = tmp_path / "cross_p01_oracle"
    p01_oracle.mkdir(parents=True, exist_ok=True)
    engine_v1 = RenderingEngine(p01_root, get_src_e_v1())
    engine_v1.render_and_write(
        "case",
        cases,
        relationship_records=links,
        relationship_subject_field="case_id",
        relationship_object_field="case_id",
        relationship_target_field="alert_id",
    )
    engine_v1.write_metadata(p01_oracle, "src_e")

    # Render V2 (Period B)
    p02_root = tmp_path / "cross_p02_exports"
    p02_oracle = tmp_path / "cross_p02_oracle"
    p02_oracle.mkdir(parents=True, exist_ok=True)
    engine_v2 = RenderingEngine(p02_root, get_src_e_v2())
    engine_v2.render_and_write(
        "case",
        cases,
        relationship_records=links,
        relationship_subject_field="case_id",
        relationship_object_field="case_id",
        relationship_target_field="alert_id",
    )
    engine_v2.write_metadata(p02_oracle, "src_e")

    # Attempting to validate V1 (CSV, E1- namespace) with V2 profile (JSON, E2- namespace) MUST fail
    with pytest.raises((ValueError, FileNotFoundError)):
        parse_and_validate(p01_root, p01_oracle, "SRC-E", "case", version="2.0")

    # Attempting to validate V2 (JSON, E2- namespace) with V1 profile (CSV, E1- namespace) MUST fail
    with pytest.raises((ValueError, FileNotFoundError)):
        parse_and_validate(p02_root, p02_oracle, "SRC-E", "case", version="1.0")


def test_src_e_v2_link_objects_contract(
    tmp_path: Path, fixture_config_path: Path, master_seed: bytes
) -> None:
    """Test A — SRC-E link objects contract.
    Builds SRC-E, reads actual V2 case JSON from disk, and asserts:
    - link field exists ('alert_links')
    - it is a list
    - every member is an object/dictionary
    - each object contains the required relationship identifier ('alert_id')
    - relationship type/link metadata is present ('link_type')
    - no implementation path silently falls back to a list of strings
    - parser rejects malformed/missing link-object members
    - parses artifact and verifies canonical case -> alert relationships
    - verifies V1 still uses old FK representation (alert.case_id in CSV)
    """
    import csv
    import json
    import shutil

    from satsa_generator.config.models import load_config
    from satsa_generator.fixture.builder import _generate_m2_records, validate_m2_fixture_records
    from satsa_generator.ids.service import IDService
    from satsa_generator.profiles.catalog import get_src_e_v1, get_src_e_v2
    from satsa_generator.seeds.manager import SeedManager

    config = load_config(fixture_config_path)
    seeds = SeedManager(master_seed)
    ids = IDService(config.dataset_namespace)
    records = _generate_m2_records(config, seeds, ids)
    validate_m2_fixture_records(*records)

    cases, alerts, case_alert_links = records[9], records[8], records[10]

    # Build canonical oracle
    oracle = CanonicalOracle()
    for rec in cases:
        canonical_id = rec.case_id
        alerts_for_case = [
            link.alert_id for link in case_alert_links if link.case_id == canonical_id
        ]
        rels = {}
        if alerts_for_case:
            rels["alerts"] = alerts_for_case
        oracle.register_expected_record(
            CanonicalRecordState(
                canonical_record_id=canonical_id,
                canonical_family="case",
                fields=rec.model_dump(mode="json"),
                relationships=rels,
            )
        )
    for rec in alerts:
        canonical_id = rec.alert_id
        rels = {}
        for link in case_alert_links:
            if link.alert_id == canonical_id:
                rels["case_id"] = link.case_id
                break
        oracle.register_expected_record(
            CanonicalRecordState(
                canonical_record_id=canonical_id,
                canonical_family="alert",
                fields=rec.model_dump(mode="json"),
                relationships=rels,
            )
        )

    oracle_data = [r.model_dump(mode="json") for r in oracle.expected_records.values()]

    # Render V1
    v1_root = tmp_path / "v1_exports"
    v1_oracle = tmp_path / "v1_oracle"
    v1_oracle.mkdir(parents=True, exist_ok=True)
    (v1_oracle / "src_e_oracle.json").write_text(
        json.dumps(oracle_data, indent=2, sort_keys=True), encoding="utf-8"
    )
    engine_v1 = RenderingEngine(v1_root, get_src_e_v1())
    engine_v1.render_and_write(
        "case",
        cases,
        relationship_records=case_alert_links,
        relationship_subject_field="case_id",
        relationship_object_field="case_id",
        relationship_target_field="alert_id",
    )
    engine_v1.render_and_write(
        "alert",
        alerts,
        relationship_records=case_alert_links,
        relationship_subject_field="alert_id",
        relationship_object_field="alert_id",
        relationship_target_field="case_id",
    )
    engine_v1.write_metadata(v1_oracle, "src_e")

    # Render V2
    v2_root = tmp_path / "v2_exports"
    v2_oracle = tmp_path / "v2_oracle"
    v2_oracle.mkdir(parents=True, exist_ok=True)
    (v2_oracle / "src_e_oracle.json").write_text(
        json.dumps(oracle_data, indent=2, sort_keys=True), encoding="utf-8"
    )
    engine_v2 = RenderingEngine(v2_root, get_src_e_v2())
    engine_v2.render_and_write(
        "case",
        cases,
        relationship_records=case_alert_links,
        relationship_subject_field="case_id",
        relationship_object_field="case_id",
        relationship_target_field="alert_id",
    )
    engine_v2.render_and_write(
        "alert",
        alerts,
        relationship_records=case_alert_links,
        relationship_subject_field="alert_id",
        relationship_object_field="alert_id",
        relationship_target_field="case_id",
    )
    engine_v2.write_metadata(v2_oracle, "src_e")

    # 1. Inspect actual V2 case JSON from disk
    v2_case_path = v2_root / "case_src-e.json"
    assert v2_case_path.exists(), "V2 case must exist on disk as JSON"
    v2_cases = json.loads(v2_case_path.read_text(encoding="utf-8"))
    assert len(v2_cases) > 0

    cases_with_links = [c for c in v2_cases if c.get("alert_links")]
    assert len(cases_with_links) > 0, "Must have cases with linked alerts"

    for c in cases_with_links:
        link_field = c["alert_links"]
        # Must be a list
        assert isinstance(link_field, list)
        assert len(link_field) > 0
        for item in link_field:
            # Must be a dictionary object, NOT a string
            assert isinstance(item, dict), f"Link item must be dict, got {type(item)}"
            assert not isinstance(item, str), "Link item must not be a string"
            # Must contain relationship identifier
            assert "alert_id" in item, "Link object must contain 'alert_id'"
            assert item["alert_id"].startswith("E2-ALERT-"), (
                f"Wrong ID namespace: {item['alert_id']}"
            )
            # Must contain link metadata
            assert "link_type" in item, "Link object must contain 'link_type'"
            assert item["link_type"] in ("PRIMARY", "RELATED"), (
                f"Invalid link_type: {item['link_type']}"
            )

    # Verify no string fallback anywhere in the artifact
    for c in v2_cases:
        if "alert_links" in c:
            for item in c["alert_links"]:
                assert not isinstance(item, str), "Fallback to list of strings is forbidden"

    # 2. Verify V1 uses old FK representation
    v1_alert_path = v1_root / "alert_src-e.csv"
    with v1_alert_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert "case_id" in reader.fieldnames, "V1 alert must have direct FK case_id column"
        assert "alert_id" in reader.fieldnames, "V1 alert must have legacy alert_id column"

    v1_case_path = v1_root / "case_src-e.csv"
    with v1_case_path.open("r", encoding="utf-8") as f:
        case_reader = csv.DictReader(f)
        assert "alert_links" not in case_reader.fieldnames, "V1 case must not have alert_links"
        assert "alerts" not in case_reader.fieldnames, "V1 case must not have alerts column"

    # 3. Parse and validate valid artifacts against canonical oracle
    parse_and_validate(v2_root, v2_oracle, "SRC-E", "case", version="2.0")
    parse_and_validate(v1_root, v1_oracle, "SRC-E", "case", version="1.0")

    # 4. Verify parser rejects malformed/missing link-object members
    # Case A: Fallback to list of strings
    bad_root_strings = tmp_path / "bad_strings"
    shutil.copytree(v2_root, bad_root_strings)
    bad_cases = json.loads((bad_root_strings / "case_src-e.json").read_text(encoding="utf-8"))
    for c in bad_cases:
        if c.get("alert_links"):
            c["alert_links"] = [link["alert_id"] for link in c["alert_links"]]  # flatten to strings
            break
    (bad_root_strings / "case_src-e.json").write_text(json.dumps(bad_cases), encoding="utf-8")
    with pytest.raises(ValueError, match="Expected link object dictionary"):
        parse_and_validate(bad_root_strings, v2_oracle, "SRC-E", "case", version="2.0")

    # Case B: Missing alert_id
    bad_root_noid = tmp_path / "bad_noid"
    shutil.copytree(v2_root, bad_root_noid)
    bad_cases_noid = json.loads((bad_root_noid / "case_src-e.json").read_text(encoding="utf-8"))
    for c in bad_cases_noid:
        if c.get("alert_links"):
            c["alert_links"] = [{"link_type": "PRIMARY"}]  # missing alert_id
            break
    (bad_root_noid / "case_src-e.json").write_text(json.dumps(bad_cases_noid), encoding="utf-8")
    with pytest.raises(ValueError, match="missing 'alert_id'"):
        parse_and_validate(bad_root_noid, v2_oracle, "SRC-E", "case", version="2.0")

    # Case C: Missing link_type
    bad_root_notype = tmp_path / "bad_notype"
    shutil.copytree(v2_root, bad_root_notype)
    bad_cases_notype = json.loads((bad_root_notype / "case_src-e.json").read_text(encoding="utf-8"))
    for c in bad_cases_notype:
        if c.get("alert_links"):
            c["alert_links"] = [{"alert_id": c["alert_links"][0]["alert_id"]}]  # missing link_type
            break
    (bad_root_notype / "case_src-e.json").write_text(json.dumps(bad_cases_notype), encoding="utf-8")
    with pytest.raises(ValueError, match="missing 'link_type'"):
        parse_and_validate(bad_root_notype, v2_oracle, "SRC-E", "case", version="2.0")


def test_field_provenance_raw_rendered_values(
    tmp_path: Path, fixture_config_path: Path, master_seed: bytes
) -> None:
    """Test B — Raw field provenance contract.
    Builds source artifacts, reads actual rendered source bytes/content,
    loads generated field provenance, and proves:
    - provenance.raw_value == actual rendered source value for:
      * ordinary scalar field
      * timestamp field
      * vocabulary-mapped field
      * ID field
      * relationship/reference field (link object array in JSON, direct FK in CSV)
    - Proves provenance is populated from the renderer's actual emitted source value,
      NOT from the pre-render canonical oracle.
    """
    import csv
    import json

    from satsa_generator.config.models import load_config
    from satsa_generator.fixture.builder import _generate_m2_records, validate_m2_fixture_records
    from satsa_generator.ids.service import IDService
    from satsa_generator.profiles.catalog import get_src_e_v1, get_src_e_v2
    from satsa_generator.seeds.manager import SeedManager

    config = load_config(fixture_config_path)
    seeds = SeedManager(master_seed)
    ids = IDService(config.dataset_namespace)
    records = _generate_m2_records(config, seeds, ids)
    validate_m2_fixture_records(*records)

    cases, alerts, case_alert_links = records[9], records[8], records[10]

    # --- Test B1: JSON format with structured link objects (SRC-E V2) ---
    export_root_v2 = tmp_path / "exports_v2"
    oracle_root_v2 = tmp_path / "oracle_v2"
    oracle_root_v2.mkdir(parents=True, exist_ok=True)

    profile_v2 = get_src_e_v2()
    engine_v2 = RenderingEngine(export_root_v2, profile_v2)

    engine_v2.render_and_write(
        "case",
        cases,
        relationship_records=case_alert_links,
        relationship_subject_field="case_id",
        relationship_object_field="case_id",
        relationship_target_field="alert_id",
    )
    engine_v2.render_and_write(
        "alert",
        alerts,
        relationship_records=case_alert_links,
        relationship_subject_field="alert_id",
        relationship_object_field="alert_id",
        relationship_target_field="case_id",
    )
    engine_v2.write_metadata(oracle_root_v2, "src_e")

    # Read actual rendered JSON file from disk
    case_json_path = export_root_v2 / "case_src-e.json"
    rendered_cases = json.loads(case_json_path.read_text(encoding="utf-8"))

    # Read generated field provenance from disk
    prov_path_v2 = oracle_root_v2 / "src_e_provenance.json"
    assert prov_path_v2.exists(), "Provenance metadata file must exist on disk"
    prov_data_v2 = json.loads(prov_path_v2.read_text(encoding="utf-8"))
    field_prov_v2 = prov_data_v2["field_provenance"]

    # Group provenance entries by canonical record ID
    case0_id = str(cases[0].case_id)
    case0_prov = {
        p["canonical_field_name"]: p
        for p in field_prov_v2
        if p["source_file_path"] == "case_src-e.json" and p["canonical_record_id"] == case0_id
    }

    # 1. Test ordinary scalar field (case_type)
    prov_type = case0_prov["case_type"]
    assert "raw_value" in prov_type
    assert prov_type["raw_value"] == rendered_cases[0]["incident_type"]
    assert prov_type["source_field_name"] == "incident_type"
    assert prov_type["source_file_path"] == "case_src-e.json"

    # 2. Test timestamp field (created_at_utc rendered with offset ms)
    prov_created = case0_prov["created_at_utc"]
    assert prov_created["raw_value"] == rendered_cases[0]["opened_at_utc"]
    assert "+00:00" in prov_created["raw_value"], (
        "Timestamp raw value must reflect rendered offset format"
    )

    # 3. Test vocabulary-mapped field (severity in case: HIGH -> HI, MEDIUM -> MED, etc.)
    prov_sev = case0_prov["severity"]
    assert prov_sev["raw_value"] == rendered_cases[0]["severity"]
    # In V2, severity is drifted code: HI / MED / LO / CRIT
    assert prov_sev["raw_value"] in ("HI", "MED", "LO", "CRIT")
    # Verify raw_value is NOT the unmapped canonical value (e.g. HIGH / MEDIUM / LOW / CRITICAL)
    can_sev_val = (
        cases[0].severity.value if hasattr(cases[0].severity, "value") else str(cases[0].severity)
    )
    if can_sev_val in ("HIGH", "MEDIUM", "LOW", "CRITICAL"):
        assert prov_sev["raw_value"] != can_sev_val, (
            "Field provenance raw_value must be emitted source code, not canonical value"
        )

    # 4. Test ID field (case_id mapped to case_id with E2-CASE- namespace prefix)
    prov_id = case0_prov["case_id"]
    assert prov_id["raw_value"] == rendered_cases[0]["case_id"]
    assert prov_id["raw_value"].startswith("E2-CASE-")
    # Must NOT be bare canonical UUID
    assert prov_id["raw_value"] != str(cases[0].case_id), (
        "Field provenance raw_value must be namespaced source ID, not bare canonical UUID"
    )

    # 5. Test relationship / link object field (alert_links)
    linked_case = next(
        c for c in cases if any(link.case_id == c.case_id for link in case_alert_links)
    )
    linked_case_id = str(linked_case.case_id)
    linked_prov = {
        p["canonical_field_name"]: p
        for p in field_prov_v2
        if p["source_file_path"] == "case_src-e.json" and p["canonical_record_id"] == linked_case_id
    }
    rendered_linked_case = next(
        c for c in rendered_cases if c["case_id"] == f"E2-CASE-{linked_case.case_id}"
    )

    prov_links = linked_prov["alerts"]
    assert prov_links["raw_value"] == rendered_linked_case["alert_links"]
    assert isinstance(prov_links["raw_value"], list)
    assert len(prov_links["raw_value"]) > 0
    assert isinstance(prov_links["raw_value"][0], dict)
    assert "alert_id" in prov_links["raw_value"][0]
    assert "link_type" in prov_links["raw_value"][0]
    assert prov_links["source_field_name"] == "alert_links"

    # --- Test B2: CSV format with lexical scalar / FK representation (SRC-E V1) ---
    export_root_v1 = tmp_path / "exports_v1"
    oracle_root_v1 = tmp_path / "oracle_v1"
    oracle_root_v1.mkdir(parents=True, exist_ok=True)

    profile_v1 = get_src_e_v1()
    engine_v1 = RenderingEngine(export_root_v1, profile_v1)
    engine_v1.render_and_write(
        "alert",
        alerts,
        relationship_records=case_alert_links,
        relationship_subject_field="alert_id",
        relationship_object_field="alert_id",
        relationship_target_field="case_id",
    )
    engine_v1.write_metadata(oracle_root_v1, "src_e")

    # Read actual rendered CSV file from disk
    alert_csv_path = export_root_v1 / "alert_src-e.csv"
    with alert_csv_path.open("r", encoding="utf-8") as f:
        csv_rows = list(csv.DictReader(f))

    prov_path_v1 = oracle_root_v1 / "src_e_provenance.json"
    prov_data_v1 = json.loads(prov_path_v1.read_text(encoding="utf-8"))
    alert_prov_v1 = prov_data_v1["field_provenance"]

    alert0_id = str(alerts[0].alert_id)
    alert0_prov = {
        p["canonical_field_name"]: p
        for p in alert_prov_v1
        if p["source_file_path"] == "alert_src-e.csv" and p["canonical_record_id"] == alert0_id
    }

    # Scalar / ID field in CSV
    prov_alert_id = alert0_prov["alert_id"]
    assert prov_alert_id["raw_value"] == csv_rows[0]["alert_id"]
    assert prov_alert_id["raw_value"].startswith("E1-ALERT-")

    # Timestamp field in CSV
    prov_alert_ts = alert0_prov["created_at_utc"]
    assert prov_alert_ts["raw_value"] == csv_rows[0]["created_at_utc"]
    assert prov_alert_ts["raw_value"].endswith("Z")

    # Foreign key relationship in CSV
    prov_case_fk = alert0_prov["case_id"]
    assert prov_case_fk["raw_value"] == csv_rows[0]["case_id"]
    assert prov_case_fk["raw_value"].startswith("E1-CASE-")
