"""Integration tests for Milestone 3 (Source Profiles and Canonical Oracle)."""

import json
from datetime import UTC
from pathlib import Path

from satsa_generator.canonical.oracle import CanonicalOracle, OracleMappingRecord
from satsa_generator.fixture.builder import build_m3_fixture
from satsa_generator.fixture.models import OrganizationRecord
from satsa_generator.profiles.catalog import get_profile
from satsa_generator.rendering.engine import RenderingEngine


def test_m3_build_fixture(tmp_path: Path, fixture_config_path: Path, master_seed: bytes) -> None:
    """Verify that M3 build succeeds, generates source files and an oracle."""
    result = build_m3_fixture(fixture_config_path, master_seed, output_root=tmp_path)

    # Check outputs exist
    assert result.operational_root.exists()
    assert (result.operational_root / "fixture_manifest.json").exists()

    # Check that CSV/JSON rendered files exist instead of canonical json
    rendered_files = list(result.operational_root.glob("*.*"))
    assert len(rendered_files) > 0

    # Verify the Oracle was built
    oracle_dir = tmp_path / "canonical_reference"
    assert oracle_dir.exists()

    oracle_a = oracle_dir / "oracle_a.json"
    assert oracle_a.exists()

    with oracle_a.open() as f:
        data = json.load(f)
        assert "mappings" in data
        assert len(data["mappings"]) > 0


def test_rendering_engine_csv(tmp_path: Path) -> None:
    """Test the Rendering Engine generates CSV according to profile."""
    profile = get_profile("SRC-A")
    engine = RenderingEngine(tmp_path, profile)

    # Mock records
    from datetime import datetime
    from uuid import uuid4

    record = OrganizationRecord(
        organization_id=uuid4(),
        organization_name="Test Org",
        sector_code="SEC1",
        scale_band="SMALL",
        operating_model="UNKNOWN",
        entity_criticality_band="STANDARD",
        asset_count_declared=10,
        critical_asset_count_declared=1,
        default_timezone="UTC",
        profile_effective_start_at_utc=datetime.now(UTC),
        profile_version=1,
        organization_status="ACTIVE",
    )

    manifest = engine.render_and_write("organization", [record])
    assert manifest is not None

    csv_file = tmp_path / manifest["path"]
    assert csv_file.exists()

    # SRC-A should be CSV
    content = csv_file.read_text()
    assert "org_id" in content
    assert "org_name" in content
    assert "Test Org" in content

    # Check oracle registered the mapping
    assert len(engine.oracle.mappings) > 0

    # Test Parse-back validation (round-trip canonical -> source -> canonical via Oracle)
    canonical_val = engine.oracle.get_canonical_for_source("SRC-A", manifest["path"], 0)
    assert canonical_val["organization_id"] == str(record.organization_id)
    assert canonical_val["organization_name"] == "Test Org"


def test_rendering_engine_json(tmp_path: Path) -> None:
    """Test the Rendering Engine generates JSON according to profile."""
    profile = get_profile("SRC-C")
    engine = RenderingEngine(tmp_path, profile)

    from datetime import datetime
    from uuid import uuid4

    record = OrganizationRecord(
        organization_id=uuid4(),
        organization_name="JSON Org",
        sector_code="SEC1",
        scale_band="SMALL",
        operating_model="UNKNOWN",
        entity_criticality_band="STANDARD",
        asset_count_declared=10,
        critical_asset_count_declared=1,
        default_timezone="UTC",
        profile_effective_start_at_utc=datetime.now(UTC),
        profile_version=1,
        organization_status="ACTIVE",
    )

    manifest = engine.render_and_write("organization", [record])
    assert manifest is not None

    json_file = tmp_path / manifest["path"]
    assert json_file.exists()

    # SRC-C should be JSON
    with json_file.open() as f:
        data = json.load(f)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["organization_id"] == str(record.organization_id)
        assert data[0]["organizationName"] == "JSON Org"


def test_oracle_determinism() -> None:
    """Ensure Oracle determinism by hashing."""
    oracle1 = CanonicalOracle()
    oracle2 = CanonicalOracle()

    from uuid import uuid4

    cid = uuid4()

    m1 = OracleMappingRecord(
        source_profile="SRC-A",
        source_file_path="org.csv",
        source_record_index=0,
        source_field_name="org_id",
        canonical_family="organization",
        canonical_record_id=cid,
        canonical_field_name="organization_id",
        canonical_value=str(cid),
        rendered_value=str(cid),
    )

    oracle1.register_mapping(m1)
    oracle2.register_mapping(m1)

    assert oracle1.calculate_oracle_hash() == oracle2.calculate_oracle_hash()
