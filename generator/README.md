# SAT-SA Synthetic Dataset Generator

## Overview

Deterministic, offline, reproducible synthetic dataset generator for the
**Supervisory Analytics Tool for SOC Assessment (SAT-SA)** project.

The planned generator will produce three strictly separated packages:

1. **Operational Evidence Package** — synthetic SOC data that SAT-SA ingests.
2. **Hidden Ground-Truth Package** — private scenario labels and mutation provenance.
3. **Private Evaluation Package** — blinded review coordination and answer keys.

> **Hard separation:** SAT-SA analytics receive only operational evidence.
> Scenario IDs, labels, expected findings, and mutation annotations remain private.
> Milestone 1 builds only a tiny operational-evidence fixture; it does not
> create either private package.

## Authoritative Documents

| Document | Purpose |
|---|---|
| `PROJECT_SPEC.md` | Master product scope |
| `RESEARCH_REPORT.md` | Research findings and recommendations |
| `ARCHITECTURE.md` | Technical component design and trust zones |
| `DATA_SCHEMA.md` | Canonical record definitions and provenance chain |
| `DATASET_GENERATION_SPEC.md` | Generation logic authority |
| `GENERATOR_IMPLEMENTATION_PLAN.md` | Implementation structure and milestones |

## Quick Start

```bash
# Create virtual environment (Python 3.12 required)
python3.12 -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Validate and freeze configuration
satsa-gen validate-config config/public/base/fixture_config.json
satsa-gen freeze-config config/public/base/fixture_config.json

# Build the Milestone 2 operational base-world fixture (default)
satsa-gen build-fixture config/public/base/fixture_config.json \
  --seed 1111111111111111111111111111111111111111111111111111111111111111 \
  --milestone m2 \
  --output ./artifacts/m2-fixture

# Build the minimal Milestone 1 foundation fixture
satsa-gen build-fixture config/public/base/fixture_config.json \
  --seed 1111111111111111111111111111111111111111111111111111111111111111 \
  --milestone m1 \
  --output ./artifacts/m1-fixture

# Other CLI usage
satsa-gen --help
```

The output directory must be absent or empty. The builder will not silently
overwrite artifacts. The M2 fixture writes all 18 canonical operational evidence families:

```text
artifacts/m2-fixture/
  operational_evidence/
    fixture_manifest.json
    organizations.json
    submissions.json
    submission_manifests.json
    submission_evidence_families.json
    control_process_references.json
    control_process_subject_links.json
    assets.json
    monitoring_coverage.json
    alerts.json
    cases.json
    case_alert_links.json
    investigations.json
    escalations.json
    actions.json
    resolutions.json
    closures.json
    exceptions.json
    process_changes.json
```

The published seed above is for the development fixture only. Validation and
held-out seeds must not be committed or exposed.

## Key Design Principles

- **Deterministic:** Same seed + same version = identical output bytes.
- **Offline:** No network calls. All dependencies are local.
- **Fail-loud:** Invalid config, referential breaks, or temporal violations halt generation.
- **Truth-isolated:** Zero ground-truth leakage, scenario IDs, or detector markers in operational evidence.
- **Detector-independent:** Generator never imports SAT-SA analytics config or detector thresholds.

## Reproducibility & Integrity

The generator and fixture builder use:

- HMAC-SHA-256 child-seed derivation from master seed;
- Stable named random streams (`SeedManager`);
- NumPy `SeedSequence` with `PCG64DXSM`;
- Deterministic UUIDv5 identifiers partitioned by domain namespace;
- Referential integrity validation across all foreign keys;
- Temporal ordering integrity checks (`created_at <= assigned_at <= started_at <= resolved_at <= closed_at`);
- Sorted records, sorted JSON keys, fixed separators, UTF-8, and final newlines;
- Deterministic build metadata rather than wall-clock timestamps;
- Per-file SHA-256 values and a deterministic package-tree hash.

Two clean builds using the same source, configuration, dependency versions,
and master seed are byte-identical.

## Repository Structure

```
generator/
  pyproject.toml
  README.md
  src/satsa_generator/
    core/          # Shared types, errors, build context
    config/        # Configuration loading, validation, freeze/hash
    seeds/         # Master/child seed derivation, RNG registry
    ids/           # Deterministic UUID/source-ID service
    cli/           # Command-line interface
    fixture/       # M1 and M2 schema-valid operational fixture builders & models
  tests/
    unit/          # Unit tests for core services and builder
    contract/      # Strict DATA_SCHEMA.md contract round-trip tests
    integration/   # Integration, referential, temporal, offline, and reproducibility tests
    property/      # Hypothesis property tests
```

## Current Status

**Milestone 2 (Small Schema-Valid Base World) implemented and tested.**

Implemented:

- Complete Pydantic schemas for all 18 operational evidence families per `DATA_SCHEMA.md`;
- Base-world generation logic populating operational entities across organizations, periods, assets, coverages, alerts, cases, triage investigations, escalations, remediation actions, resolutions, closures, exceptions, and process changes;
- Comprehensive referential integrity validator (`validate_m2_fixture_records`);
- Temporal ordering validator enforcing causal lifecycle consistency;
- Offline, byte-identical deterministic serialization with SHA-256 manifest and tree hash;
- Comprehensive test suite (51 passing unit, contract, integration, temporal, and reproducibility tests).

Intentionally not implemented yet (Milestone 3+ scope):

- Source renderers (SRC-A through SRC-E CSV/JSON format exporters);
- Canonical oracle and provenance graph;
- Scenarios, legitimate controls, or data-quality mutations (M4);
- Hidden ground-truth and evaluation answer key packages (M4);
- Full multi-organization large-scale dataset generation.

## License

Proprietary — SIH 2026 (SIH26157)
