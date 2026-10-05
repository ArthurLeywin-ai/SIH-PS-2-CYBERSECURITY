# SAT-SA Application & Ingestion Layer (Milestone 6)

The **SAT-SA Supervisory Evidence Backend** provides an offline, air-gapped supervisory analytics and evidence processing foundation for cybersecurity regulatory examination.

This milestone (M6) establishes the production-grade application architecture, persistence layer, multi-stage evidence ingestion pipeline, canonical normalization engine, and versioned REST API.

---

## 1. Architectural Overview & Boundaries

The SAT-SA application follows a strict dependency chain designed to isolate raw ingestion from canonical domain logic and future supervisory analytics:

```
Evidence Files (JSON / CSV / JSONL)
                ↓
Ingestion Layer (Reader, Manifest Inspection, Package Discovery)
                ↓
Validation Engine (Schema, UUIDs, Temporal Ordering, Foreign References, Integrity)
                ↓
Canonical Normalization (DATA_SCHEMA.md §4.1 Controlled Value States & §4.2 Provenance)
                ↓
Persistence Layer (SQLite with WAL mode, Indexes, Repositories)
                ↓
Application Services (PackageService, OrganizationService, EvidenceService, ProvenanceService)
                ↓
REST API Layer (FastAPI v1: Health, Readiness, Ingestion, Entities, Evidence, Lineage)
                ↓
[Future M7 Analytics Engine]
                ↓
[Future Findings / Explainability]
                ↓
[Future Examiner UI]
```

### Architectural Separation
- **API Layer (`app/backend/api/`)**: Provides OpenAPI-documented, versioned HTTP routes and explicit Pydantic request/response contracts. It never leaks raw database models.
- **Service Layer (`app/backend/services/`)**: Encapsulates business logic, transactional boundaries, and service orchestration.
- **Ingestion Pipeline (`app/backend/ingestion/`)**: Discovers evidence packages, verifies manifests, parses multi-format files, and streams data with bounded memory.
- **Validation Engine (`app/backend/validation/`)**: Performs multi-stage integrity checks, referential verification, temporal checks, and vocabulary validation without silently discarding evidence.
- **Canonical Normalization (`app/backend/ingestion/normalizer.py`)**: Normalizes raw inputs into the authoritative canonical model, recording provenance and field-level observations.
- **Persistence Layer (`app/backend/persistence/`)**: Manages the SQLite database, schema initialization, models, and repositories.
- **Security Boundaries (`app/backend/security.py`)**: Enforces path traversal prevention, allowed file extension whitelisting, and strict payload size limits.

---

## 2. Directory Structure

```
app/
├── pyproject.toml              # Package definition, scripts, and dependencies
├── README.md                   # Application and setup documentation
├── backend/
│   ├── main.py                 # FastAPI application factory and lifespan handler
│   ├── cli.py                  # CLI entrypoints (`satsa-server`, `satsa-ingest`)
│   ├── config.py               # Central configuration with environment variable overrides
│   ├── errors.py               # Structured application errors and HTTP exception handlers
│   ├── logging.py              # Structured JSON and console logging
│   ├── security.py             # Path traversal, extension, and file size security controls
│   ├── api/
│   │   ├── router.py           # API v1 aggregation router
│   │   ├── deps.py             # Dependency injection providers
│   │   ├── schemas.py          # Pydantic API response and request models
│   │   └── routes/             # Route handlers (health, ingestion, orgs, subs, evidence, lineage)
│   ├── domain/
│   │   ├── types.py            # Authoritative enumerations and ValueState types
│   │   └── models.py           # Immutable Pydantic canonical domain entities
│   ├── ingestion/
│   │   ├── pipeline.py         # End-to-end ingestion pipeline orchestrator
│   │   ├── normalizer.py       # Canonical normalization and provenance generator
│   │   └── reader.py           # Safe, bounded streaming file reader (JSON, JSONL, CSV)
│   ├── validation/
│   │   └── validator.py        # Package validator (manifest, schema, temporal, referential)
│   ├── persistence/
│   │   ├── database.py         # SQLite engine, connection pragmas, and session management
│   │   ├── models.py           # SQLAlchemy declarative models for all 18 families
│   │   └── repositories.py     # Data-access repositories for all evidence families
│   └── services/               # Application service layer
└── tests/
    ├── conftest.py             # Test database and client fixtures
    ├── unit/                   # Unit tests (config, logging, persistence, reader, validator)
    ├── security/               # Security tests (path traversal, oversized inputs, extensions)
    └── integration/            # End-to-end M5 package ingestion and API retrieval tests
```

---

## 3. Setup & Installation

### Prerequisites
- Python 3.12+ (tested on Python 3.14)
- Virtual environment (`venv`)

### Installation
From the repository root:
```bash
# Activate existing venv or create a new one
source generator/venv/bin/activate

# Install the SAT-SA application in editable mode
pip install -e ./app
```

---

## 4. Configuration

The application is configured through environment variables or defaults:

| Variable | Default | Purpose |
|---|---|---|
| `SATSA_HOST` | `127.0.0.1` | Network interface to bind server |
| `SATSA_PORT` | `8000` | HTTP port |
| `SATSA_ENV` | `development` | Environment mode (`development` enables `/docs`) |
| `SATSA_DATABASE_URL` | `sqlite:///./data/satsa.db` | Persistence SQLite database URI |
| `SATSA_EVIDENCE_DIR` | `./evidence` | Staging/evidence root directory |
| `SATSA_MAX_PACKAGE_SIZE`| `524288000` (500 MB) | Max package size limit |
| `SATSA_MAX_FILE_SIZE` | `104857600` (100 MB) | Max single file size limit |
| `SATSA_LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `SATSA_LOG_FORMAT` | `text` | Logging format (`text` or `json`) |

---

## 5. Running the Backend Service

### Starting via CLI
```bash
satsa-server --host 127.0.0.1 --port 8000
```

### Starting via Python
```bash
python3 -m app.backend.cli --host 127.0.0.1 --port 8000
```

Once started in `development` mode, interactive OpenAPI documentation is available locally at:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

---

## 6. Evidence Ingestion

### Option A: Ingest via REST API
```bash
curl -X POST http://127.0.0.1:8000/api/v1/packages/ingest \
  -H "Content-Type: application/json" \
  -d '{"package_path": "/path/to/evidence_package", "fail_on_error": false}'
```

### Option B: Headless Ingestion via CLI
```bash
satsa-ingest /path/to/evidence_package
```

### Ingestion Pipeline Flow:
1. **Security & Path Validation**: Verifies directory traversal safety and boundaries.
2. **Package Discovery**: Discovers `operational_evidence/` and manifest (`fixture_manifest.json`).
3. **Manifest Inspection**: Hashes files on disk and compares against declared SHA-256 hashes.
4. **File Presence Check**: Verifies baseline required evidence files exist.
5. **Schema & Vocabulary Validation**: Validates UUIDs, ISO-8601 timestamps, and controlled vocabularies.
6. **Referential & Temporal Integrity**: Verifies cross-family references and causal ordering.
7. **Canonical Normalization**: Maps raw records to canonical models, resolving exact duplicates (`VAL-003: no double counting`) while preserving lineage.
8. **Provenance Attachment**: Captures file, locator, and field traces in `evidence_provenance`.
9. **Controlled Value State Recording**: Tracks field states in `canonical_field_observations`.
10. **Transactional Persistence**: Atomically inserts all records into SQLite.

---

## 7. REST API Reference

### Health & System Probes
- `GET /api/v1/health`: Basic service liveness and version probe.
- `GET /api/v1/readiness`: Database connectivity and storage readiness probe.

### Packages & Ingestion
- `POST /api/v1/packages/ingest`: Trigger evidence package ingestion.
- `GET /api/v1/packages`: List discovered and ingested packages.
- `GET /api/v1/packages/{package_id}`: Retrieve package details and summary.
- `GET /api/v1/packages/{package_id}/validation`: Retrieve validation findings for a package.

### Regulated Entities (Organizations)
- `GET /api/v1/organizations`: List regulated entities in canonical storage.
- `GET /api/v1/organizations/{organization_id}`: Retrieve specific organization metadata.
- `GET /api/v1/organizations/{organization_id}/submissions`: List submissions for an organization.

### Submissions
- `GET /api/v1/submissions/{submission_id}`: Retrieve submission details, manifests, and declared evidence families.

### Operational Evidence
- `GET /api/v1/evidence/alerts`: Query canonical alerts (filters: `organization_id`, `severity`, `category`, `status`, `limit`, `offset`).
- `GET /api/v1/evidence/alerts/{alert_id}`: Retrieve single alert.
- `GET /api/v1/evidence/cases`: Query canonical cases (filters: `organization_id`, `status`).
- `GET /api/v1/evidence/cases/{case_id}`: Retrieve full case context including linked alerts, investigations, escalations, actions, resolutions, and closures.
- `GET /api/v1/evidence/assets?organization_id=...`: Query enterprise assets.
- `GET /api/v1/evidence/coverage?organization_id=...`: Query monitoring coverage declarations.

### Provenance & Lineage
- `GET /api/v1/lineage/provenance/{canonical_record_id}`: Query exact source-to-canonical trace.
- `GET /api/v1/lineage/observations/{canonical_record_id}`: Query semantic field observations and controlled value states.

---

## 8. Persistence & Canonical Models

All 18 canonical evidence families from `DATA_SCHEMA.md` are supported with dedicated relational tables and indexes:

1. `organizations`
2. `submissions`
3. `submission_manifests`
4. `submission_evidence_families`
5. `control_process_references`
6. `control_process_subject_links`
7. `assets`
8. `monitoring_coverage`
9. `alerts`
10. `cases`
11. `case_alert_links`
12. `investigations`
13. `escalations`
14. `actions`
15. `resolutions`
16. `closures`
17. `exceptions`
18. `process_changes`

Plus system tables:
- `ingestion_packages`: Tracking intake status, manifest/tree hashes, record counts, and validation issues.
- `evidence_provenance`: Exact lineage connecting source files, row locators, and fields to canonical entities.
- `canonical_field_observations`: Preserving controlled missing value states (`NOT_PROVIDED`, `NOT_APPLICABLE`, `INVALID`, etc.).

---

## 9. Testing

The test suite covers unit tests, security attack simulations, and a mandatory end-to-end integration test ingesting an actual M5 generator fixture:

```bash
# Run application test suite
pytest app/tests -v
```

Test breakdown:
- `app/tests/unit/test_config_logging.py`: Config defaults, environment overrides, structured JSON logging.
- `app/tests/unit/test_database_persistence.py`: SQLite initialization, repositories, relationships, transaction rollback.
- `app/tests/unit/test_reader.py`: JSON, JSONL, and CSV streaming with size boundary checks.
- `app/tests/unit/test_validator.py`: Missing file detection, hash verification, UUID checks, duplicate detection, referential integrity.
- `app/tests/security/test_security.py`: Path traversal protection, system root access prevention, oversized payload rejection, filename sanitization.
- `app/tests/integration/test_api_endpoints.py`: Health, readiness, and structured error handling.
- `app/tests/integration/test_end_to_end_ingestion.py`: End-to-end pipeline: M5 fixture build → ingestion → validation → normalization → database → API retrieval with provenance verification.

---

## 10. Air-Gapped & Offline Verification

The application is completely self-contained:
- Zero external cloud AI or analytics APIs
- Zero remote database connections
- Zero telemetry, tracking, or network calls
- Zero external font, CDN, or stylesheet dependencies
- All dependencies run entirely in the local Python environment.

---

## 11. Milestone 6 Scope Boundary Confirmation

In strict compliance with project governance:
- **NO** anomaly detection algorithms or ML models have been implemented in M6.
- **NO** risk scores or supervisory scores have been invented or computed.
- **NO** final examiner dashboard or frontend has been created.
- **NO** fake findings have been injected.

Milestone 6 strictly establishes the production-quality application foundation, database, ingestion pipeline, canonical normalization, provenance retention, and REST API.
