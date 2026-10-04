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

# Build the Milestone 4 scenario-mutated fixture with private ground truth
satsa-gen build-fixture config/public/base/fixture_config.json \
  --seed 1111111111111111111111111111111111111111111111111111111111111111 \
  --milestone m4 \
  --output ./artifacts/m4-fixture

# Build the Milestone 2 operational base-world fixture
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
overwrite artifacts. The M4 fixture produces operational evidence alongside a strictly
separated private ground-truth package:

```text
artifacts/m4-fixture/
  operational_evidence/
    fixture_manifest.json (contract: SATSA-M4-FIXTURE-V1)
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
```

The published seed above is for the development fixture only. Validation and
held-out seeds must not be committed or exposed.

## Key Design Principles

- **Deterministic:** Same seed + same version = identical output bytes.
- **Offline:** No network calls. All dependencies are local.
- **Fail-loud:** Invalid config, referential breaks, or temporal violations halt generation.
- **Truth-isolated:** Zero ground-truth leakage, scenario IDs, or detector markers in operational evidence.
- **Detector-independent:** Generator never imports SAT-SA analytics config or detector thresholds.
- **Authorized Mutation:** Every mutation must be pre-authorized in the authorization ledger and verified post-mutation.

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
    fixture/       # M1-M4 schema-valid operational fixture builders & models
    scenarios/     # M4 catalog, ledger, selectors, mutators, controls, validators, truth writer
    rendering/     # Source rendering framework (SRC-A through SRC-E)
    provenance/    # Lineage tracking and provenance manifests
    canonical/     # Canonical schemas, field mappings, and canonical oracle
  tests/
    unit/          # Unit tests for core services, catalog, ledger, selectors, mutators, controls
    contract/      # Strict DATA_SCHEMA.md contract round-trip and fixture contract tests
    integration/   # Integration, referential, temporal, offline, and scenario engine tests
    property/      # Hypothesis property tests
```

## Current Status

**Milestone 4 (Scenario and Legitimate-Control Engine) implemented and validated.**

Implemented:

- **Scenario Models & Catalog:** Strict schemas for all 7 scenario families (`EXECUTION_GAP`, `NEGATIVE_SPACE`, `HISTORICAL_REPETITION`, `PEER_COMPARISON`, `CROSS_RECORD`, `LEGITIMATE_UNUSUAL`, `AMBIGUOUS_INSUFFICIENT`) and 9 canonical scenario definitions with explicit prerequisites and applicable realization states.
- **Authorization Ledger:** Enforces `PLANNED -> APPLIED -> VALIDATED` lifecycle; detects and rejects unauthorized mutations, conflicting authorizations on identical target records, and duplicate authorization IDs; validates complete consumption of all planned authorizations.
- **Deterministic Selectors:** Target reservation preventing collateral mutations, semantic prerequisite filtering, and deterministic selection via seed streams.
- **Copy-on-Write Mutators:** Immutable mutation pipeline generating detailed `MutationReceipt` entries capturing exact before/after state and provenance.
- **Read-Only Semantic Validators:** Verifies expected operational conditions after mutation without performing silent repairs; records passed/failed assertions in `ScenarioValidationReport`.
- **Legitimate-Control Engine:** Produces genuine operational `ExceptionRecord` and `ProcessChangeRecord` entities for legitimate unusual and ambiguous control contexts.
- **Private Ground-Truth Separation:** Outputs `ground_truth.json` and `authorization_ledger.json` in a distinct `private_ground_truth/` directory; `LeakageScanner` verifies zero leakage of ground truth, scenario tokens, or private metadata into operational packages.
- **Milestone 4 Fixture & CLI Integration:** `build_m4_fixture` producing `SATSA-M4-FIXTURE-V1` contract with deterministic tree SHA-256 and bitwise reproducibility.
- **Comprehensive Test Suite:** 112 passing tests across unit, contract, integration, temporal, and reproducibility test suites.

Intentionally not implemented yet (Milestone 5+ scope):

- Quality mutations, 14 validation gates, and canary leakage scanner test cases (M5);
- Full multi-organization large-scale dataset generation;
- SAT-SA analytics, detectors, risk scoring, ML models, backend, frontend, and dashboards.

## License

Proprietary — SIH 2026 (SIH26157)

