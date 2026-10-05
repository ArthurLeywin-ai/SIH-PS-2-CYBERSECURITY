# SAT-SA Synthetic Dataset Generator

## Overview

Deterministic, offline, reproducible synthetic dataset generator for the
**Supervisory Analytics Tool for SOC Assessment (SAT-SA)** project.

The generator produces three strictly separated packages:

1. **Operational Evidence Package** — synthetic SOC operational data that SAT-SA ingests.
2. **Hidden Ground-Truth Package** — private scenario labels, mutation receipts, and audit ledgers.
3. **Private Evaluation Package** — blinded review coordination and answer keys.

> **Hard separation:** SAT-SA analytics receive only operational evidence.
> Scenario IDs, labels, expected findings, and mutation annotations remain private.
> Operational evidence contains zero leakage of ground truth, scenario tokens, or seeds.

## Authoritative Documents

| Document | Purpose |
|---|---|
| `DATASET_GENERATION_SPEC.md` | Generation logic authority (Priority 1) |
| `GENERATOR_IMPLEMENTATION_PLAN.md` | Implementation structure and milestones (Priority 2) |
| `DATA_SCHEMA.md` | Canonical record definitions and provenance chain (Priority 3) |
| `ARCHITECTURE.md` | Technical component design and trust zones (Priority 4) |
| `RESEARCH_REPORT.md` | Research findings and recommendations (Priority 5) |
| `PROJECT_SPEC.md` | Master product scope (Priority 6) |

## Quick Start

```bash
# Create virtual environment (Python 3.12+ supported)
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest
pytest -q

# Run static quality checks
python3 -m compileall src tests
ruff check src tests

# Validate and freeze configuration
satsa-gen validate-config config/public/base/fixture_config.json
satsa-gen freeze-config config/public/base/fixture_config.json

# Build the Milestone 5 validated fixture (Quality mutations + 14 validation gates)
satsa-gen build-fixture config/public/base/fixture_config.json \
  --seed 1111111111111111111111111111111111111111111111111111111111111111 \
  --milestone m5 \
  --output ./artifacts/m5-fixture

# Build Milestone 4 (Scenario-mutated fixture with private ground truth)
satsa-gen build-fixture config/public/base/fixture_config.json \
  --seed 1111111111111111111111111111111111111111111111111111111111111111 \
  --milestone m4 \
  --output ./artifacts/m4-fixture

# Build Milestone 3 (Source profiles SRC-A..E and canonical reconstruction oracle)
satsa-gen build-fixture config/public/base/fixture_config.json \
  --seed 1111111111111111111111111111111111111111111111111111111111111111 \
  --milestone m3 \
  --output ./artifacts/m3-fixture

# Build Milestone 2 (Operational base-world fixture)
satsa-gen build-fixture config/public/base/fixture_config.json \
  --seed 1111111111111111111111111111111111111111111111111111111111111111 \
  --milestone m2 \
  --output ./artifacts/m2-fixture

# Build minimal Milestone 1 foundation fixture
satsa-gen build-fixture config/public/base/fixture_config.json \
  --seed 1111111111111111111111111111111111111111111111111111111111111111 \
  --milestone m1 \
  --output ./artifacts/m1-fixture

# Other CLI usage
satsa-gen --help
```

The output directory must be absent or empty. The builder will not silently
overwrite artifacts. The M5 fixture produces operational evidence alongside a strictly
separated private ground-truth package:

```text
artifacts/m5-fixture/
  operational_evidence/
    fixture_manifest.json (contract: SATSA-M5-FIXTURE-V1)
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
  private_ground_truth/
    ground_truth.json
    authorization_ledger.json
    quality_receipts.json
```

The published seed above is for development and testing fixtures only. Validation and
held-out seeds must not be committed or exposed.

## Key Design Principles

- **Deterministic:** Same seed + same version = identical output bytes.
- **Offline:** No network calls. All dependencies are local.
- **Fail-loud:** Invalid config, referential breaks, or temporal violations halt generation.
- **Truth-isolated:** Zero ground-truth leakage, scenario IDs, or detector markers in operational evidence.
- **Detector-independent:** Generator never imports SAT-SA analytics config or detector thresholds.
- **Authorized Mutation:** Every mutation must be pre-authorized in the authorization ledger and verified post-mutation.
- **Source Heterogeneity:** Realistic dialect, vocabulary, timestamp, naming, and layout diversity across SRC-A through SRC-E.

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
    fixture/       # M1-M5 schema-valid operational fixture builders & models
    scenarios/     # M4 catalog, ledger, selectors, mutators, controls, validators, truth writer
    profiles/      # M3 source profiles (SRC-A through SRC-E catalog, vocabularies, mappings)
    rendering/     # M3 source rendering framework (CSV, JSON, JSONL engines)
    provenance/    # M3 field and relationship lineage tracking and provenance manifests
    canonical/     # M3 canonical reconstruction and independent canonical oracle
    quality/       # M5 quality mutation engine, mutators, and receipts
    validation/    # M5 14 validation gates, framework runner, and leakage scanner
  tests/
    unit/          # Unit tests for core services, gates, catalog, ledger, mutators, leakage
    contract/      # Strict DATA_SCHEMA.md contract round-trip and fixture contract tests
    integration/   # Integration, rendering, pipeline, offline, and reproducibility tests
    property/      # Hypothesis property tests
```

## Current Status

**Milestones 1 through 5 (Foundation through Quality Mutations & Full 14-Gate Validation) are fully implemented and verified.**

Implemented:

- **Milestone 1 (Foundation):** Config models, freeze/hash pipeline, seed manager, deterministic ID service, CLI skeleton.
- **Milestone 2 (Base World):** Deterministic schema-valid base world generator across all 18 canonical evidence families.
- **Milestone 3 (Source Profiles & Canonical Oracle):**
  - Realistic source heterogeneity across profiles `SRC-A` (multi-CSV, snake_case), `SRC-B` (PascalCase, embedded IDs, local timestamps), `SRC-C` (nested case JSON, milliseconds), `SRC-D` (array/lines JSON, external IDs, reference arrays), and `SRC-E` (hybrid CSV/JSON v1/v2 migration boundary with drifted vocabulary and naming).
  - Source-first reference parser and independent canonical reconstruction.
  - Field and relationship provenance tracking against rendered artifacts on disk.
- **Milestone 4 (Scenario & Legitimate-Control Engine):**
  - All 7 scenario families (`EXECUTION_GAP`, `NEGATIVE_SPACE`, `HISTORICAL_REPETITION`, `PEER_COMPARISON`, `CROSS_RECORD`, `LEGITIMATE_UNUSUAL`, `AMBIGUOUS_INSUFFICIENT`) and 9 canonical scenario types.
  - Authorization ledger enforcing `PLANNED -> APPLIED -> VALIDATED` lifecycle with zero collateral mutations.
  - Legitimate unusual control engine with authentic `ExceptionRecord` and `ProcessChangeRecord` entities.
  - Read-only semantic validators confirming operational conditions without silent repair.
  - Private ground truth isolation.
- **Milestone 5 (Quality Mutations & Full 14-Gate Validation):**
  - Quality mutation engine covering all 13 mutation types with 4-stage execution order.
  - Full suite of 14 validation gates executing sequentially with loud, blocking failure behavior:
    1. Gate 01: Configuration Gate
    2. Gate 02: Schema / Base-World Gate
    3. Gate 03: Referential Integrity Gate
    4. Gate 04: Temporal Integrity Gate
    5. Gate 05: Missing-State Semantics Gate
    6. Gate 06: Scenario Realization Gate
    7. Gate 07: Authorized Mutation Gate
    8. Gate 08: Source Rendering Gate
    9. Gate 09: Canonical / Provenance Gate
    10. Gate 10: Distribution Sanity Gate
    11. Gate 11: Duplicate Behavior Gate
    12. Gate 12: Leakage Scan Gate
    13. Gate 13: Reproducibility Gate
    14. Gate 14: Package Hash Gate
  - Comprehensive leakage scanner with all 9 detection methods, canary testing, and false-positive waiver workflow.
  - Strict physical package separation and manifest integrity verification.

Intentionally not implemented yet (Milestone 6+ scope):

- Full multi-organization medium benchmark generation (M6);
- Blinded held-out release and evaluation packaging (M7);
- SAT-SA analytics, detectors, risk scoring, ML models, backend, frontend, and dashboards.

## License

Proprietary — SIH 2026 (SIH26157)
