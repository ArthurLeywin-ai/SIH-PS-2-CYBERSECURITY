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

# Build the tiny Milestone 1 fixture
satsa-gen build-fixture config/public/base/fixture_config.json \
  --seed 1111111111111111111111111111111111111111111111111111111111111111 \
  --output ./artifacts/m1-fixture

# Other CLI usage
satsa-gen --help
```

The output directory must be absent or empty. The builder will not silently
overwrite artifacts. The fixture writes only:

```text
artifacts/m1-fixture/
  operational_evidence/
    fixture_manifest.json
    organizations.json
    submission_manifests.json
    submissions.json
```

The published seed above is for the development fixture only. Validation and
held-out seeds must not be committed or exposed.

## Key Design Principles

- **Deterministic:** Same seed + same version = identical output bytes.
- **Offline:** No network calls. All dependencies are local.
- **Fail-loud:** Invalid config or impossible states halt generation.
- **Truth-isolated:** No ground-truth leakage into operational evidence.
- **Detector-independent:** Generator never imports SAT-SA analytics config.

## Reproducibility

The fixture uses:

- HMAC-SHA-256 child-seed derivation;
- stable named random streams;
- NumPy `SeedSequence` with `PCG64DXSM`;
- UUIDv5 deterministic identifiers;
- sorted records, sorted JSON keys, fixed separators, UTF-8, and final newlines;
- deterministic build metadata rather than wall-clock timestamps;
- per-file SHA-256 values and a deterministic package-tree hash.

Two clean builds using the same source, configuration, dependency versions,
and master seed must be byte-identical. Changing the seed changes generated
profile/submission values and therefore changes the package-tree hash.

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
    fixture/       # Tiny schema-shaped Milestone 1 fixture
  tests/
    unit/          # Unit tests
    contract/      # DATA_SCHEMA.md contract tests
    integration/   # Integration tests
```

## Current Status

**Milestone 1 foundation implemented and tested.**

Implemented:

- strict immutable JSON/TOML configuration loading and hashing;
- fail-loud validation, unknown-key rejection, portable output-path checks,
  and detector-key rejection;
- deterministic named seed streams and known-answer testing;
- deterministic canonical/source identifier service;
- immutable build context and version identity;
- a tiny schema-shaped organization/submission/manifest fixture;
- deterministic operational-only serialization and hashes;
- unit and integration tests, including offline and byte-identity checks.

Intentionally not implemented yet:

- the full 15-organization population or multi-period simulation;
- operational evidence families beyond the minimal foundation records;
- scenarios, legitimate controls, or data-quality mutations;
- source renderers or the canonical/provenance oracle;
- hidden truth, evaluation packages, dataset splits, or benchmarks;
- SAT-SA ingestion, analytics, findings, prioritization, ML, backend, or UI.

This fixture is a foundation test artifact, not the complete synthetic dataset.

## License

Proprietary — SIH 2026 (SIH26157)
