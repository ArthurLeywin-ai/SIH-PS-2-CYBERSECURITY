# SAT-SA Synthetic Dataset Generator

## Overview

Deterministic, offline, reproducible synthetic dataset generator for the
**Supervisory Analytics Tool for SOC Assessment (SAT-SA)** project.

This generator produces three strictly separated packages:

1. **Operational Evidence Package** — synthetic SOC data that SAT-SA ingests.
2. **Hidden Ground-Truth Package** — private scenario labels and mutation provenance.
3. **Private Evaluation Package** — blinded review coordination and answer keys.

> **Hard separation:** SAT-SA analytics receive only operational evidence.
> Scenario IDs, labels, expected findings, and mutation annotations remain private.

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

# CLI usage
satsa-gen --help
```

## Key Design Principles

- **Deterministic:** Same seed + same version = identical output bytes.
- **Offline:** No network calls. All dependencies are local.
- **Fail-loud:** Invalid config or impossible states halt generation.
- **Truth-isolated:** No ground-truth leakage into operational evidence.
- **Detector-independent:** Generator never imports SAT-SA analytics config.

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
  tests/
    unit/          # Unit tests
    contract/      # DATA_SCHEMA.md contract tests
    integration/   # Integration tests
```

## Current Status

**Milestone 1** — Repository, configuration, seed, and deterministic fixture foundation.

## License

Proprietary — SIH 2026 (SIH26157)
