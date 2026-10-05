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

## 6. Evidence Ingestion & Boundaries

### Supported Evidence Formats
The ingestion pipeline automatically discovers and ingests operational evidence across all supported formats:
- **JSON (`.json`)**: Formatted arrays or single-record objects.
- **JSONL (`.jsonl`)**: Line-delimited JSON objects streaming large volumes safely.
- **CSV (`.csv`)**: Header-driven comma-separated values with automatic null/whitespace sanitization.

Evidence families are discovered dynamically via canonical names (e.g. `alerts.json`, `alerts.jsonl`, `alerts.csv`) and standard variations without altering canonical domain models.

### Evidence Root Security Boundary
The application enforces `SATSA_EVIDENCE_DIR` as the strict security boundary for package intake:
- **Allowed**: Any package directory resolving inside the configured `SATSA_EVIDENCE_DIR`.
- **Rejected (HTTP 403 / `SECURITY_VIOLATION`)**:
  - Paths resolving outside `SATSA_EVIDENCE_DIR` (e.g. `/tmp/package`, `/home/user/evidence`).
  - Path traversal attempts (`../`) escaping the permitted root.
  - Symlinks escaping the permitted boundary.

External packages must be staged into `SATSA_EVIDENCE_DIR` before submission.

### Package & File Size Limits
To prevent denial-of-service and memory exhaustion attacks:
- **Total Package Maximum (`SATSA_MAX_PACKAGE_SIZE`)**: The pipeline recursively calculates total package size before parsing and rejects oversized packages. No partial records remain in storage.
- **Per-File Maximum (`SATSA_MAX_FILE_SIZE`)**: Every individual evidence file is verified before loading.

### Private Ground Truth Isolation
The ingestion pipeline strictly enforces ground-truth isolation:
- `private_ground_truth/` is treated as **generator-only material**.
- The application **NEVER** reads, ingests, persists, or exposes private ground truth, oracle labels, scenario IDs, or generator metadata.
- Operational storage (`evidence_provenance`) contains **ONLY** operational evidence provenance tracing to submitted operational evidence files.

### Ingestion Flow:
```bash
# Ingest via REST API
curl -X POST http://127.0.0.1:8000/api/v1/packages/ingest \
  -H "Content-Type: application/json" \
  -d '{"package_path": "/path/inside/evidence_dir/package", "fail_on_error": false}'

# Ingest headlessly via CLI
satsa-ingest /path/inside/evidence_dir/package
```

1. **Security & Boundary Validation**: Validates canonical path against `SATSA_EVIDENCE_DIR`, verifies symlink confinement, and checks total package byte size against `SATSA_MAX_PACKAGE_SIZE`.
2. **Package Discovery**: Discovers operational files in package root or `operational_evidence/`.
3. **Manifest Inspection**: Hashes files on disk and compares against declared SHA-256 hashes if a manifest exists.
4. **File Presence Check**: Verifies mandatory evidence families exist.
5. **Schema & Vocabulary Validation**: Validates UUIDs, ISO-8601 timestamps, and controlled vocabularies.
6. **Referential & Temporal Integrity**: Verifies cross-family references and causal ordering.
7. **Canonical Normalization**: Maps raw records (.json, .jsonl, .csv) to canonical models, resolving exact duplicates (`VAL-003: no double counting`) while preserving operational lineage.
8. **Operational Provenance Attachment**: Captures operational file, locator, and field traces in `evidence_provenance`.
9. **Controlled Value State Recording**: Tracks field states in `canonical_field_observations`.
10. **Transactional Persistence**: Atomically inserts all records into SQLite. Failed packages leave zero partial operational evidence.

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
- `supervisory_signals`: Persisted explainable signals flagged by supervisory analytics detectors.
- `supervisory_attention_summaries`: Aggregated entity-level attention summaries, bands, and data quality gap indexes.

---

## 9. Supervisory Analytics Engine (Milestone 7)

Milestone 7 introduces the deterministic, auditable, explainable supervisory analytics layer that operates directly on canonical operational evidence.

### 9.1 Analytics Architecture

```text
Canonical Operational Evidence
              ↓
Analytics Read/Feature Layer (features.py)
              ↓
Deterministic Supervisory Detectors (detectors/)
  ├── Execution Gap Detector (unlinked alerts, missing investigations, premature closures)
  ├── Negative Space Detector (missing expected families, count discrepancies, unmonitored assets)
  ├── Statistical Anomaly Detector (median/MAD, IQR thresholds, duration outliers)
  ├── Peer Comparison Detector (cohort grouping by scale/operating model, size >= 3)
  └── Operational Drift Detector (period-over-period drift in volume, closure rate, coverage)
              ↓
Supervisory Signals with Evidence References & Lineage (models.py, evidence.py)
              ↓
Explainable Supervisory Rationale & Examiner Questions (explanations.py)
              ↓
Entity-Level Attention Aggregator & Summaries (detectors/attention.py)
              ↓
REST API Endpoints & Examiner Persistence (/api/v1/analytics/*)
```

### 9.2 The Supervisory Signal Contract

Every generated signal implements a strict typed contract (`SupervisorySignal` dataclass & `SupervisorySignalModel`):
- `signal_id`: Unique deterministic UUID.
- `organization_id`: Target entity identifier.
- `submission_id`: Applicable submission reporting period.
- `signal_type`: Deterministic category (`EXECUTION_GAP`, `NEGATIVE_SPACE`, `STATISTICAL_ANOMALY`, `PEER_DEVIATION`, `OPERATIONAL_DRIFT`).
- `severity`: Attention level (`INFORMATIONAL`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
- `title`: Concise supervisory title.
- `short_rationale`: 1-2 sentence executive summary for examiners.
- `detailed_explanation`: Complete multi-paragraph factual rationale.
- `basis`: Typed calculation dictionary containing metrics, thresholds, baselines, and deviations.
- `observed_value` & `expected_value`: Explicit quantitative or categorical comparison points.
- `confidence`: Calibrated strength indicator [0.0, 1.0].
- `evidence_references`: Granular links with `record_id`, `evidence_family`, `field_path`, `role`, and source file location.
- `affected_record_ids`: Explicit primary key list of operational records involved.
- `detector_id` & `detector_version`: Immutable detector provenance.
- `investigation_questions`: Actionable questions tailored for human examiners.
- `generated_at_utc`: Deterministic ISO 8601 UTC timestamp.

### 9.3 Supervisory Semantics & Cautionary Phrasing

The engine strictly adheres to supervisory jurisprudence:
> **A supervisory signal indicates "requires examiner attention / inquiry", NEVER "wrongdoing proved".**
> **Absence of evidence is NEVER proof that an action never occurred.**

Explanations are strictly framed with cautious, neutral phrasing:
- *"No supporting record was observed"*
- *"Evidence gap detected requiring examiner inquiry"*
- *"The absence of records in this submission does not constitute conclusive proof that the operational activity did not occur"*

### 9.4 Entity-Level Supervisory Attention Indicator

Rather than an arbitrary "risk score", the engine computes an explainable **Supervisory Attention Indicator** (bounded between `0.0` and `100.0`):
- **Deterministic formula**: Weighted combination of signal severity base scores, signal diversity, and evidence gap indexes.
- **Categorical Bands**: `LOW` (0-20), `MODERATE` (21-45), `ELEVATED` (46-70), `HIGH` (71-100).
- **Fully Decomposable**: Includes breakdown by signal type, severity distribution, top 5 strongest signals, and human-readable summary rationale.

### 9.5 Analytics REST API Endpoints

- `POST /api/v1/analytics/run`: Executes analytics for an organization or submission, returning signals and attention summary. Supports `persist=true`.
- `GET /api/v1/analytics/signals`: Lists persisted supervisory signals with pagination (`limit`, `offset`) and filtering (`organization_id`, `submission_id`, `signal_type`, `severity`).
- `GET /api/v1/analytics/signals/{signal_id}`: Retrieves full detail, evidence references, and investigation questions for a specific signal.
- `GET /api/v1/analytics/organizations/{organization_id}/attention`: Retrieves current attention indicator summary and priority band for an entity.

---

## 10. Testing & Verification

The application test suite covers 73 automated tests verifying all layers:

```bash
# Run application test suite
generator/venv/bin/pytest app/tests -v

# Run generator test suite
generator/venv/bin/pytest generator/tests

# Check code compilation
generator/venv/bin/python3 -m compileall app

# Check linting and style
generator/venv/bin/ruff check app
```

Test breakdown:
- `app/tests/unit/test_analytics_features.py`: Deterministic feature extraction, counts, rates, durations, empty population behavior, and pure statistics utilities (`median`, `MAD`, `IQR`).
- `app/tests/unit/test_detectors.py`: Comprehensive tests for all 5 detectors + Attention Aggregator, testing clean workflows, unlinked alerts, temporal inversions, missing families, count discrepancies, duration outliers, peer deviation cohorts, drift thresholds, and zero baseline handling.
- `app/tests/unit/test_analytics_isolation.py`: Verifies zero references or imports of `private_ground_truth`, scenario labels, oracle data, or generator metadata.
- `app/tests/unit/test_explainability_and_evidence.py`: Verifies signal contract completeness, examiner questions, evidence reference resolution, and lineage enrichment.
- `app/tests/integration/test_analytics_engine.py`: End-to-end integration test: M5 fixture build → ingestion → analytics run → determinism verification across runs → REST API queries and filters.
- `app/tests/integration/test_remediation_blockers.py`: Regression verification for M6 remediation blockers: Ground Truth Isolation, Evidence-Root Boundary Enforcement, Package Size Enforcement, and Format Contract.

---

## 11. Air-Gapped & Offline Verification

The application is completely self-contained:
- Zero external cloud AI or analytics APIs
- Zero remote database connections
- Zero telemetry, tracking, or network calls
- Zero external font, CDN, or stylesheet dependencies
- All statistical evaluations (median, MAD, IQR) implemented natively in Python.

---

## 12. Milestone Scope Boundary Confirmation

In strict compliance with project governance:
- **NO** machine learning models (Isolation Forest, neural nets, autoencoders) in M7.
- **NO** frontend dashboards in M7.
- **NO** private ground truth or scenario oracle access at runtime.
- **NO** modifications to authoritative specifications or generator code.
