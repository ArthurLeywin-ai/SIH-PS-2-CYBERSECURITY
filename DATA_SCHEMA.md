# DATA_SCHEMA.md

## SAT-SA — Canonical Data Contract and Synthetic Dataset Design

| Field | Value |
|---|---|
| Project | SAT-SA — Supervisory Analytics Tool for SOC Assessment |
| SIH problem statement | SIH 2026 — SIH26157 |
| Phase | Phase 3 — Data Schema & Synthetic Dataset Design |
| Authoritative inputs | `PROJECT_SPEC.md`, `RESEARCH_REPORT.md`, `ARCHITECTURE.md` |
| Purpose | Concrete logical data contract for later synthetic generation, ingestion, analytics, evaluation, and evidence traceability |
| Scope | Schema and dataset design only; no data files, SQL, migrations, generators, or application code |
| Status | Proposed schema awaiting review |

> **Core separation:** Submitted operational evidence, SAT-SA-derived analytical data, and synthetic ground truth are three different data planes. They must never be silently mixed.
>
> **Core traceability chain:** **Finding → Evidence Link → Canonical Record/Field → Source Record → Source File → Submission → Manifest/Hash**

### Decision labels

- **FACT** — directly established by the authoritative project documents.
- **RESEARCH FINDING** — conclusion accepted from `RESEARCH_REPORT.md`.
- **PROJECT DECISION** — concrete Phase 3 schema decision.
- **ASSUMPTION** — design condition requiring later confirmation.
- **OPEN QUESTION** — unresolved choice that remains visible.

---

## 1. Data-Model Overview

### 1.1 What SAT-SA receives

SAT-SA receives periodic, structured operational evidence submitted for one organization and one or more reporting periods. The MVP accepts CSV and JSON representations of organizations, assets, monitoring coverage, alerts, cases, investigations, escalations, actions/remediation, resolutions, closures, and approved exceptions where available.

The model is intentionally not a real-time telemetry schema. It contains no packet capture, live endpoint stream, continuous SIEM event bus, response actuator, attacker reconstruction, or unnecessary threat-intelligence feed.

**FACT:** The authoritative project documents define SAT-SA as an offline supervisory-analysis tool for periodic structured SOC evidence, with human judgment remaining final.

**RESEARCH FINDING:** Missing submitted evidence cannot safely prove that an operational action did not occur. The schema therefore models observation scope, missing-state semantics, provenance, and approved exceptions explicitly.

**ASSUMPTION:** The MVP can identify each organization, reporting period, and source system sufficiently to namespace source identifiers. Where this is not true, canonicalization must retain an unresolved/unknown state rather than guess.

**OPEN QUESTION:** Final field-length, file-size, and text-size limits will be set after generator and ingestion benchmarks; this document defines bounded types but does not invent untested limits for every free-text field.

### 1.2 Why the evidence families exist

| Evidence family | Supervisory purpose |
|---|---|
| Organization | Defines entity identity and attributes needed for defensible peer eligibility |
| Submission | Defines reporting scope, period, source systems, and declared completeness |
| Asset | Supplies monitored-universe and criticality denominators |
| Monitoring Coverage | States whether/when an asset was expected or observed to be monitored |
| Alert | Represents detection evidence and supports volume, severity, recurrence, acknowledgement, and closure analysis |
| Case/Incident | Represents work grouping and response lifecycle |
| Investigation | Represents investigative activity, timing, notes, methods, and outcomes |
| Escalation | Represents handoff/notification evidence where escalation is applicable |
| Action/Remediation | Represents follow-through for recurring or resolved issues |
| Resolution and Closure | Separates substantive resolution from administrative closure where the source permits |
| Exception/Applicability | Represents legitimate automation, suppression, maintenance, emergency, policy-change, or not-applicable context |
| Control/Process Reference | Provides a versioned subject for rules, findings, and control/process/sample prioritization when supplied or configured |
| Source/Provenance | Makes every normalized value and finding traceable to the received submission |

### 1.3 Operational relationship

```text
Organization
    |
    +--- Assets
    |       |
    |       +--- Monitoring Coverage
    |
    +--- Alerts <------------------+
            |                      |
            +--- Case-Alert Link --+
                    |
                    +--- Cases
                            |
                            +--- Investigations
                            +--- Escalations
                            +--- Actions / Remediation
                            +--- Resolutions
                            +--- Closures

Exceptions / Applicability may reference an organization, asset, alert,
case, investigation, escalation, action, rule, process, or reporting period.
```

### 1.4 Provenance relationship

```text
Submission
    |
    +--- Source Files
            |
            +--- Source Records
                    |
                    +--- Canonical Records
                            |
                            +--- Canonical Field Observations
                                    |
                                    +--- Original field/path/value
```

### 1.5 Source, canonical, and derived records

- A **source record** is the row or JSON object exactly as received and located within a preserved source file.
- A **canonical record** is the normalized representation of that source evidence. It is still operational evidence, not an analytical conclusion.
- A **derived analytical record** is produced by SAT-SA from canonical evidence, such as a duration, baseline, cohort statistic, finding, or priority.
- A **ground-truth record** exists only for synthetic evaluation and is never detector input.

**PROJECT DECISION:** Original submitted values are retained through field-level provenance even when a canonical value is mapped or converted.

---

## 2. Three Strictly Separated Data Planes

### 2.1 Plane A — Submitted operational evidence

This plane contains received source artifacts and normalized canonical evidence:

- organizations and reporting metadata;
- assets and monitoring coverage;
- alerts and cases;
- investigations, escalations, actions, resolutions, and closures;
- approved exceptions/applicability context;
- source files, records, field paths, and original values.

It answers **what was submitted**. It does not contain anomaly labels, expected detector outputs, or planted scenario identifiers.

### 2.2 Plane B — Derived analytical data

This plane contains SAT-SA calculations and workflow state:

- quality assessments and relationship diagnostics;
- closure/investigation durations;
- normalized rates and recurrence features;
- historical baseline summaries;
- peer cohorts and comparison summaries;
- text-similarity groups;
- optional anomaly scores;
- candidate/final findings, evidence links, attention bands, reviews, and reports.
- review samples/members and append-only logical audit events.

Every derived value must identify the analytical run, method/configuration version, calculation inputs, and supporting canonical records.

### 2.3 Plane C — Synthetic ground truth

This plane contains hidden evaluation-only information:

- planted scenario and version;
- affected organization, period, and record identifiers;
- intended analytical family;
- expected finding/counter-finding;
- legitimate-versus-attention label;
- confounders and mutation provenance;
- expected evidence set.

**PROJECT DECISION:** Ground truth is stored outside the operational-evidence package and outside the application database used by the detector. The dashboard and analytical modules cannot read it.

### 2.4 Separation invariant

```text
Synthetic Generator
        |
        +---- Operational Evidence Package ----> SAT-SA Analytics
        |
        +---- Hidden Ground Truth -------------> Evaluation Harness Only

Evaluation Harness receives analytical outputs separately and joins them to
Hidden Ground Truth after analysis completes.
```

Violation of this invariant invalidates evaluation results.

---

## 3. Logical Type System and Field Conventions

### 3.1 Logical types

This document uses implementation-neutral logical types.

| Type | Meaning and validation |
|---|---|
| `UUID` | SAT-SA-generated opaque identifier in canonical UUID text form; globally unique in its entity family |
| `SOURCE_ID` | Source-provided identifier, 1–256 Unicode characters after safe normalization; original preserved |
| `CODE` | Controlled uppercase token, normally 1–64 ASCII characters plus `_`/`-` |
| `STRING(n)` | Trimmed Unicode string with maximum character length `n` |
| `TEXT` | Bounded Unicode free text; implementation limit required; no markup execution |
| `BOOLEAN` | `true` or `false`; absence is represented separately by value state |
| `INTEGER` | Signed whole number with declared nonnegative/range rule where applicable |
| `DECIMAL(p,s)` | Exact decimal; percentages stored as fractions only where explicitly named `_ratio` |
| `TIMESTAMP_UTC` | Instant normalized to UTC with original timestamp/offset preserved in provenance |
| `DATE` | Calendar date without time; used only when the source has date-level precision |
| `DURATION_SECONDS` | Nonnegative integer seconds; derived unless explicitly identified as source-provided |
| `HASH_SHA256` | 64 lowercase hexadecimal characters |
| `JSON_OBJECT` | Bounded structured metadata using documented keys; not a substitute for core typed fields |
| `JSON_ARRAY<T>` | Ordered, bounded array whose members all satisfy logical type `T`; use `JSON_ARRAY<OBJECT>` only when each object has a documented shape |
| `ENUM` | One value from a versioned controlled vocabulary |

### 3.2 Requiredness

- **R — Required:** canonical record cannot be accepted without a valid value.
- **C — Conditional:** required when stated condition applies; otherwise explicit missing state is required.
- **O — Optional:** may be absent, but the semantic absence state must be represented when analytically relevant.
- **D — Derived:** never accepted as authoritative submitted evidence unless separately represented as a source value.
- **GT — Ground truth only:** prohibited from operational evidence and detector input.

### 3.3 Identifier policy

Every canonical entity has:

1. a SAT-SA-generated `UUID` primary identifier;
2. a source identifier where provided;
3. organization/source-system namespace metadata;
4. source-record provenance.

**PROJECT DECISION:** Source identifiers are never assumed globally unique. Their uniqueness scope is normally `(organization_id, source_system_id, record_family, source_id)` unless a mapping profile documents a narrower or wider scope.

### 3.4 Timestamp policy

- Canonical instant fields end in `_at_utc`.
- Reporting intervals use `_start_at_utc` and `_end_at_utc` with half-open semantics `[start, end)`.
- Original strings, timezone/offset, and precision are retained in field provenance.
- A timestamp without a source timezone is not silently interpreted; a versioned mapping assumption may normalize it while retaining a warning.
- Events are never reordered to make a workflow look valid.

### 3.5 Common canonical-record envelope

Every canonical operational record conceptually includes these fields, even where family tables below omit repetition.

| Field | Type | Req. | Description and validation |
|---|---|---:|---|
| `canonical_record_id` | UUID | R | SAT-SA identifier for this normalized record/revision |
| `record_family` | ENUM | R | One canonical evidence family |
| `organization_id` | UUID | R | Owning CSE; must resolve to Organization |
| `submission_id` | UUID | R | Submission from which this version originated |
| `source_record_id` | UUID | R | Exact source row/object provenance |
| `mapping_version_id` | UUID | R | Mapping version used for normalization |
| `record_version` | INTEGER | R | Positive source/canonical revision sequence within identity |
| `record_effective_start_at_utc` | TIMESTAMP_UTC | O | When the represented state became effective |
| `record_effective_end_at_utc` | TIMESTAMP_UTC | O | Exclusive end; must be after start |
| `record_quality_state` | ENUM | R | `VALID`, `WARNING`, `INVALID`, `INCOMPLETE`, or `UNKNOWN` |
| `normalized_at_utc` | TIMESTAMP_UTC | R | Ingestion processing time, not operational event time |
| `is_current_revision` | BOOLEAN | R | Convenience flag; historical revisions remain retained |

### 3.6 Source and derived naming

- Source-provided identifiers use `source_*_id`.
- SAT-generated canonical identifiers use family-specific `*_id`.
- Derived values use explicit names such as `closure_duration_seconds_derived`.
- Counts end in `_count`; fractions in `[0,1]` end in `_ratio`; percent display is a UI concern.
- Ambiguous fields such as `date`, `time`, `score`, `risk`, or `status_text` are prohibited without qualification.

---

## 4. Controlled Missing-Value Semantics

### 4.1 Required states

| Value state | Meaning | Typed value rule | Example |
|---|---|---|---|
| `OBSERVED_VALUE` | Valid nonzero/nonempty value was submitted or validly mapped | Typed canonical value present | severity = `HIGH` |
| `OBSERVED_ZERO` | Source explicitly supplied a valid numeric zero/false/empty-count with zero semantics | Typed value is exactly zero/false | escalation count = 0 |
| `NOT_PROVIDED` | Expected field/source was omitted from submitted structure | Typed value absent | escalation field not exported |
| `NOT_APPLICABLE` | Field/evidence does not apply under known context | Typed value absent | no escalation target for non-applicable rule |
| `INVALID` | Submitted value exists but fails parse/validation | Typed value absent; original retained | malformed timestamp |
| `NO_SUBMITTED_EVIDENCE` | Qualifying related record was searched for in an adequate submitted scope and not found | No fabricated record/value | no investigation linked to eligible alert |
| `UNKNOWN` | SAT-SA cannot establish value or absence semantics | Typed value absent | submission scope undeclared |

### 4.2 Representation

**PROJECT DECISION:** Canonical family records store typed values. A companion `canonical_field_observation` record stores the semantic `value_state`, original field/value, mapping, and validation status for every required field and every optional field used by analytics.

Rules:

- A non-null typed value requires `OBSERVED_VALUE` or `OBSERVED_ZERO`.
- A null typed value requires one of the other five states.
- `NO_SUBMITTED_EVIDENCE` applies to relationship/evidence searches only after scope adequacy is established; it is not the default state for a null field.
- Database null may physically represent no typed value later, but never carries meaning without the companion state.

### 4.3 Relationship absence

Missing relationships use a `relationship_observation` object rather than inventing a child record. It states source subject, relationship type, expected target family, value state, searched submission/families/period, and quality basis.

---

## 5. Submitted Operational Evidence — Organization and Submission

### 5.1 Organization / CSE

| Field | Type | Req. | Vocabulary/unit | Description and validation |
|---|---|---:|---|---|
| `organization_id` | UUID | R | — | SAT-SA-generated primary identifier |
| `source_organization_id` | SOURCE_ID | O | — | Source identifier where supplied; unique within dataset/workspace when present |
| `organization_name` | STRING(160) | R | — | Synthetic display name for dataset; no real CSE name |
| `organization_alias` | STRING(80) | O | — | Short synthetic code such as `CSE-007` |
| `sector_code` | CODE | R | versioned sector vocabulary | Peer attribute; unknown mapping uses `UNKNOWN` plus source value |
| `subsector_code` | CODE | O | versioned mapping | Finer peer attribute where available |
| `scale_band` | ENUM | R | `SMALL`, `MEDIUM`, `LARGE`, `VERY_LARGE`, `UNKNOWN` | Relative synthetic/declared operational scale; not employee count |
| `operating_model` | ENUM | R | `CENTRALIZED_24X7`, `CENTRALIZED_BUSINESS_HOURS`, `DISTRIBUTED`, `HYBRID`, `UNKNOWN` | Peer eligibility context |
| `entity_criticality_band` | ENUM | O | `STANDARD`, `ELEVATED`, `HIGH`, `UNKNOWN` | Coarse synthetic supervisory context; not a real official classification |
| `asset_count_declared` | INTEGER | O | count ≥ 0 | Source-declared active asset count at profile date |
| `critical_asset_count_declared` | INTEGER | O | count ≥ 0 | Must not exceed declared asset count |
| `default_timezone` | STRING(64) | O | IANA zone | Used only as an explicit mapping assumption; not a substitute for source offset |
| `profile_effective_start_at_utc` | TIMESTAMP_UTC | R | — | Start of this profile version |
| `profile_effective_end_at_utc` | TIMESTAMP_UTC | O | — | Exclusive end after start |
| `profile_version` | INTEGER | R | ≥ 1 | Version within organization |
| `organization_status` | ENUM | R | `ACTIVE`, `INACTIVE`, `UNKNOWN` | Dataset/reporting participation state |

**Privacy:** No legal name, physical address, employee name, contact, credential, or real infrastructure identifier is required.

### 5.2 Submission

| Field | Type | Req. | Vocabulary/unit | Description and validation |
|---|---|---:|---|---|
| `submission_id` | UUID | R | — | SAT-SA-generated primary identifier |
| `source_submission_id` | SOURCE_ID | O | — | Submitter’s package/export identifier |
| `organization_id` | UUID | R | FK | Owning organization |
| `reporting_period_start_at_utc` | TIMESTAMP_UTC | R | inclusive | Must precede end |
| `reporting_period_end_at_utc` | TIMESTAMP_UTC | R | exclusive | Defines submitted reporting scope |
| `submitted_at_utc` | TIMESTAMP_UTC | O | — | Source-declared submission time |
| `received_at_utc` | TIMESTAMP_UTC | R | — | SAT-SA ingestion event time |
| `source_system_set_id` | STRING(128) | O | — | Identifier for declared set of source systems |
| `source_system_versions` | JSON_OBJECT | O | bounded map | Source names to versions; no secrets |
| `declared_completeness` | ENUM | R | `DECLARED_COMPLETE`, `DECLARED_PARTIAL`, `NOT_DECLARED` | Submitter assertion, not SAT-SA assessment |
| `declared_missing_families` | JSON_ARRAY<OBJECT> | O | family/reason entries | Each object must contain `evidence_family` and may contain a bounded `reason`; must be consistent with declaration |
| `submission_status` | ENUM | R | `QUARANTINED`, `VALIDATING`, `CONDITIONALLY_ACCEPTED`, `ACCEPTED`, `REJECTED`, `SUPERSEDED` | Intake lifecycle |
| `period_maturity_state` | ENUM | R | `MATURE`, `IMMATURE`, `PARTIAL`, `UNKNOWN` | SAT-SA assessment used for absence/timing analytics |
| `manifest_id` | UUID | R | FK | Links immutable manifest version |
| `schema_profile_id` | UUID | O | FK | Expected source schema profile |
| `submission_notes` | TEXT | O | bounded | Non-sensitive scope/context note |
| `supersedes_submission_id` | UUID | O | self-FK | Corrected/replacement package; no overwrite |
| `submission_quality_state` | ENUM | R | quality vocabulary | Overall assessment, separate from declared completeness |

### 5.3 Submission evidence-family declaration

This record prevents an absent file from being mistaken for an observed zero.

| Field | Type | Req. | Description and validation |
|---|---|---:|---|
| `submission_family_id` | UUID | R | Primary identifier |
| `submission_id` | UUID | R | Parent submission |
| `evidence_family` | ENUM | R | One canonical family |
| `presence_state` | ENUM | R | `PROVIDED`, `NOT_PROVIDED`, `NOT_APPLICABLE`, `UNKNOWN` |
| `declared_record_count` | INTEGER | O | Nonnegative source assertion |
| `observed_parsed_record_count` | INTEGER | D | Nonnegative parsed count |
| `coverage_start_at_utc` | TIMESTAMP_UTC | O | Earliest declared family coverage |
| `coverage_end_at_utc` | TIMESTAMP_UTC | O | Exclusive coverage end |
| `completeness_state` | ENUM | R | `COMPLETE`, `PARTIAL`, `IMMATURE`, `UNKNOWN_SCOPE`, `INVALID` |
| `completeness_reason` | TEXT | O | Human-readable reason |
| `assessed_at_utc` | TIMESTAMP_UTC | R | Assessment time |

---

## 6. Submitted Operational Evidence — Source and Provenance

### 6.1 Submission manifest

| Field | Type | Req. | Description and validation |
|---|---|---:|---|
| `manifest_id` | UUID | R | Primary identifier |
| `submission_id` | UUID | R | One manifest version belongs to one submission |
| `manifest_version` | INTEGER | R | Positive; immutable once accepted |
| `created_at_utc` | TIMESTAMP_UTC | R | SAT-SA manifest creation time |
| `file_count` | INTEGER | R | Nonnegative |
| `total_bytes` | INTEGER | R | Nonnegative |
| `manifest_sha256` | HASH_SHA256 | R | Hash of canonicalized manifest representation |
| `ingestion_run_id` | UUID | R | Intake/normalization workflow identifier |
| `created_by_actor_id` | UUID | R | Local actor/service identity |

### 6.2 Source file

| Field | Type | Req. | Description and validation |
|---|---|---:|---|
| `source_file_id` | UUID | R | SAT-SA-generated primary identifier |
| `submission_id` | UUID | R | Parent submission |
| `original_filename` | STRING(255) | R | Metadata only; never trusted as path |
| `internal_storage_name` | STRING(128) | R | Generated non-user-controlled name |
| `relative_preserved_path` | STRING(512) | R | Must stay inside preserved source root |
| `media_type_detected` | STRING(128) | R | Detected type, not browser-provided trust |
| `format_code` | ENUM | R | `CSV`, `JSON`, `ZIP`, `OTHER_REJECTED` |
| `byte_size` | INTEGER | R | ≥ 0 |
| `sha256` | HASH_SHA256 | R | Hash of exact received bytes |
| `encoding_detected` | STRING(64) | O | e.g. UTF-8; uncertain detection carries warning |
| `record_family_declared` | ENUM | O | Source/manifest declaration |
| `record_family_mapped` | ENUM | O | Mapping-selected family |
| `source_system_id` | STRING(128) | O | Source system namespace |
| `source_system_version` | STRING(128) | O | Version where available |
| `file_status` | ENUM | R | `QUARANTINED`, `PARSED`, `PARTIAL`, `INVALID`, `REJECTED`, `DUPLICATE` |
| `duplicate_of_source_file_id` | UUID | O | Exact-hash duplicate reference |
| `parser_version` | STRING(64) | O | Parser version used |
| `preserved_at_utc` | TIMESTAMP_UTC | R | Ingestion time |

### 6.3 Source record

| Field | Type | Req. | Description and validation |
|---|---|---:|---|
| `source_record_id` | UUID | R | SAT-SA-generated identifier for exact source row/object |
| `source_file_id` | UUID | R | Parent file |
| `source_native_record_id` | SOURCE_ID | O | Source-provided row/object identifier |
| `record_family_detected` | ENUM | R | Mapped family or `UNKNOWN` |
| `record_locator_type` | ENUM | R | `CSV_ROW`, `JSON_POINTER`, `JSON_PATH`, `OTHER` |
| `record_locator` | STRING(512) | R | Stable locator, such as row number or JSON Pointer |
| `raw_record_sha256` | HASH_SHA256 | R | Hash of canonicalized exact logical source record |
| `parse_status` | ENUM | R | `PARSED`, `PARTIAL`, `INVALID`, `SKIPPED` |
| `source_record_version` | STRING(64) | O | Source-declared revision/sequence |
| `source_updated_at_utc` | TIMESTAMP_UTC | O | Source operational update time if supplied |
| `parsed_at_utc` | TIMESTAMP_UTC | R | Processing time |
| `parse_diagnostic_count` | INTEGER | R | ≥ 0 |

### 6.4 Canonical field observation

| Field | Type | Req. | Description and validation |
|---|---|---:|---|
| `field_observation_id` | UUID | R | Primary identifier |
| `canonical_record_id` | UUID | R | Canonical record receiving the value/state |
| `canonical_record_family` | ENUM | R | Needed for typed resolution |
| `canonical_field_name` | CODE | R | Must exist in schema version |
| `value_state` | ENUM | R | One non-collapsible missing/value state |
| `source_record_id` | UUID | R | Origin/source search anchor |
| `original_field_path` | STRING(512) | O | Column name or JSON path; absent for searched relationship |
| `original_value_text` | TEXT | O | Exact lexical value, bounded; sensitive local data |
| `normalized_value_text` | TEXT | O | Reproducible display form of typed value |
| `mapping_version_id` | UUID | R | Mapping used |
| `transform_id` | STRING(128) | O | Versioned transform reference |
| `field_quality_state` | ENUM | R | Field-level quality status |
| `diagnostic_code` | CODE | O | Machine-readable validation code |
| `observed_at_utc` | TIMESTAMP_UTC | R | Normalization time |

### 6.5 Relationship observation

| Field | Type | Req. | Description and validation |
|---|---|---:|---|
| `relationship_observation_id` | UUID | R | Primary identifier |
| `subject_record_family` | ENUM | R | Source family of subject |
| `subject_record_id` | UUID | R | Canonical subject |
| `relationship_type` | ENUM | R | e.g. `ALERT_TO_CASE`, `CASE_TO_INVESTIGATION` |
| `target_record_family` | ENUM | R | Expected/observed target family |
| `target_record_id` | UUID | O | Present only when relationship resolves |
| `source_target_id_text` | SOURCE_ID | O | Unresolved source foreign identifier |
| `value_state` | ENUM | R | Includes `OBSERVED_VALUE`, `NO_SUBMITTED_EVIDENCE`, etc. |
| `search_submission_id` | UUID | R | Scope in which target was searched |
| `search_period_start_at_utc` | TIMESTAMP_UTC | O | Search scope |
| `search_period_end_at_utc` | TIMESTAMP_UTC | O | Search scope |
| `relationship_quality_state` | ENUM | R | Valid/warning/invalid/incomplete/unknown |
| `diagnostic_code` | CODE | O | e.g. `BROKEN_FOREIGN_KEY` |

---

## 7. Submitted Operational Evidence — Asset and Monitoring Coverage

### 7.1 Asset

| Field | Type | Req. | Vocabulary/unit | Description and validation |
|---|---|---:|---|---|
| `asset_id` | UUID | R | — | SAT-SA primary identifier |
| `source_asset_id` | SOURCE_ID | O | — | Source identifier where supplied; unique within organization/source system/effective interval when present |
| `organization_id` | UUID | R | FK | Owning entity |
| `asset_alias` | STRING(128) | O | — | Synthetic/non-sensitive display alias |
| `asset_class` | ENUM | R | asset-class vocabulary | Server, endpoint, network, application, cloud resource, database, service, other, unknown |
| `asset_criticality` | ENUM | R | asset-criticality vocabulary | Used for attention context, not proof of risk |
| `environment` | ENUM | O | `PRODUCTION`, `DR`, `TEST`, `DEVELOPMENT`, `OTHER`, `UNKNOWN` | Operational context |
| `business_service_code` | STRING(128) | O | — | Synthetic service grouping |
| `monitoring_expected` | BOOLEAN | C | — | Source/config declaration; state required if absent |
| `monitoring_expectation_basis` | ENUM | O | `DECLARED`, `ASSET_CLASS_POLICY`, `RULE_CONFIGURATION`, `UNKNOWN` | Why coverage is expected |
| `active_status` | ENUM | R | `ACTIVE`, `INACTIVE`, `DECOMMISSIONING`, `UNKNOWN` | At effective interval |
| `effective_start_at_utc` | TIMESTAMP_UTC | R | — | Asset active/profile interval start |
| `effective_end_at_utc` | TIMESTAMP_UTC | O | — | Exclusive end; after start |
| `owner_role_code` | STRING(128) | O | — | Role/team only; no real person required |
| `source_system_id` | STRING(128) | O | — | Inventory source |
| `asset_profile_version` | INTEGER | R | ≥ 1 | Supports change over time |

### 7.2 Monitoring coverage

| Field | Type | Req. | Vocabulary/unit | Description and validation |
|---|---|---:|---|---|
| `monitoring_coverage_id` | UUID | R | — | Primary identifier |
| `source_coverage_id` | SOURCE_ID | O | — | Source identifier |
| `organization_id` | UUID | R | FK | Must match asset organization |
| `asset_id` | UUID | R | FK | Covered asset |
| `monitoring_type` | ENUM | R | `SIEM_ALERTING`, `ENDPOINT_MONITORING`, `NETWORK_MONITORING`, `APPLICATION_MONITORING`, `LOG_COLLECTION`, `OTHER`, `UNKNOWN` | Type of declared/observed coverage; does not imply live ingestion by SAT-SA |
| `expectation_state` | ENUM | R | `EXPECTED`, `OPTIONAL`, `NOT_APPLICABLE`, `UNKNOWN` | Whether evidence should exist |
| `expectation_basis` | ENUM | R | `DECLARED`, `RULE_CONFIGURATION`, `ASSET_PROFILE`, `EXCEPTION`, `UNKNOWN` | Why expected |
| `coverage_state` | ENUM | R | monitoring-status vocabulary | Observed/declared state |
| `coverage_source_type` | ENUM | R | `DECLARED`, `SOURCE_HEALTH_EXPORT`, `CONFIG_EXPORT`, `INFERRED`, `UNKNOWN` | Provenance strength |
| `coverage_start_at_utc` | TIMESTAMP_UTC | R | — | Effective start |
| `coverage_end_at_utc` | TIMESTAMP_UTC | O | — | Exclusive end |
| `last_evidence_at_utc` | TIMESTAMP_UTC | O | — | Last submitted monitoring/health evidence; not SAT-SA live telemetry |
| `source_system_id` | STRING(128) | O | — | Monitoring source identifier |
| `coverage_reason` | TEXT | O | — | Bounded context |
| `exception_id` | UUID | O | FK | Approved exception if state not covered |
| `coverage_quality_state` | ENUM | R | quality | Evidence adequacy |

**Negative-space rule support:** An active critical asset with `monitoring_expected=true` and adequate inventory/submission scope can be compared against Monitoring Coverage. Absence becomes `NO_SUBMITTED_EVIDENCE`, not a fabricated `NOT_MONITORED` record.

---

## 8. Submitted Operational Evidence — Alert

| Field | Type | Req. | Vocabulary/unit | Description and validation |
|---|---|---:|---|---|
| `alert_id` | UUID | R | — | SAT-SA primary identifier |
| `source_alert_id` | SOURCE_ID | O | — | Source identifier where supplied; unique in organization/source system scope when present |
| `organization_id` | UUID | R | FK | Owning entity |
| `asset_id` | UUID | O | FK | Referenced asset; unresolved/missing state retained |
| `source_system_id` | STRING(128) | O | — | Originating alert platform/export where supplied; file/mapping provenance remains authoritative when absent |
| `source_detection_id` | STRING(256) | O | — | Detection/rule/signature ID; useful for recurrence |
| `alert_category` | ENUM | R | versioned category vocabulary | Source-specific term mapped; raw retained |
| `alert_type` | STRING(160) | O | — | More specific normalized/source type |
| `severity` | ENUM | R | severity vocabulary | Mapping confidence retained |
| `source_severity_text` | STRING(128) | R | — | Original source severity for explanation |
| `created_at_utc` | TIMESTAMP_UTC | R | event time | Must lie in/near declared period or produce warning |
| `acknowledged_at_utc` | TIMESTAMP_UTC | O | event time | Normally ≥ created; violation retained and flagged |
| `first_investigated_at_utc` | TIMESTAMP_UTC | O | source summary only | If supplied; detailed investigation remains authoritative evidence family |
| `resolved_at_utc` | TIMESTAMP_UTC | O | event time | Substantive resolution where source combines lifecycle |
| `closed_at_utc` | TIMESTAMP_UTC | O | event time | Supports closure analysis; not silently derived from case |
| `last_updated_at_utc` | TIMESTAMP_UTC | O | source update | May be after reporting period |
| `alert_status` | ENUM | R | alert-status vocabulary | Current state at source export |
| `disposition` | ENUM | O | disposition vocabulary | Explicit state if absent |
| `disposition_reason` | TEXT | O | — | Bounded source text |
| `automation_state` | ENUM | O | `MANUAL`, `AUTOMATED`, `MIXED`, `UNKNOWN` | Where source identifies automation |
| `suppression_state` | ENUM | O | `NOT_SUPPRESSED`, `SUPPRESSED`, `PARTIALLY_SUPPRESSED`, `UNKNOWN` | Does not imply approval |
| `suppression_rule_id` | STRING(128) | O | — | Source rule reference |
| `primary_case_source_id` | SOURCE_ID | O | source hint | Normalized relationship is stored in Case-Alert Link |
| `occurrence_count_source` | INTEGER | O | count ≥ 1 | Source aggregation count if alert represents multiple events |
| `alert_summary` | TEXT | O | — | Synthetic/non-sensitive summary; bounded |
| `workflow_version` | STRING(64) | O | — | Helps process-change boundaries |

### 8.1 Derived alert values—not submitted fields

The following belong to Plane B:

- `acknowledgement_duration_seconds_derived`;
- `closure_duration_seconds_derived`;
- `recurrence_key_derived`;
- `recurrence_count_derived`;
- `has_qualifying_investigation_derived`;
- `historical_percentile_derived`;
- `peer_percentile_derived`.

They must not overwrite source timestamps or counts.

---

## 9. Submitted Operational Evidence — Case and Alert Relationship

### 9.1 Case / Incident

| Field | Type | Req. | Vocabulary/unit | Description and validation |
|---|---|---:|---|---|
| `case_id` | UUID | R | — | SAT-SA primary identifier |
| `source_case_id` | SOURCE_ID | O | — | Source identifier where supplied; unique in organization/source system scope when present |
| `organization_id` | UUID | R | FK | Owning entity |
| `case_type` | ENUM | R | `ALERT_CASE`, `INCIDENT`, `PROBLEM`, `SERVICE_REQUEST`, `OTHER`, `UNKNOWN` | Source workflow classification |
| `case_category` | STRING(128) | O | — | Mapped category |
| `severity` | ENUM | R | severity | May differ from alerts legitimately; mismatch is context |
| `priority_source_text` | STRING(128) | O | — | Raw source priority if separate from severity |
| `created_at_utc` | TIMESTAMP_UTC | R | event time | Case creation |
| `assigned_at_utc` | TIMESTAMP_UTC | O | event time | First assignment where available |
| `resolved_at_utc` | TIMESTAMP_UTC | O | event time | Source summary; detailed Resolution may exist |
| `closed_at_utc` | TIMESTAMP_UTC | O | event time | Source summary; detailed Closure may exist |
| `last_updated_at_utc` | TIMESTAMP_UTC | O | source update | Can be later than closure for corrections |
| `case_status` | ENUM | R | case-status vocabulary | Current export state |
| `assigned_team_code` | STRING(128) | O | — | Synthetic role/team, not real person |
| `assigned_analyst_pseudonym` | STRING(128) | O | — | Synthetic/pseudonymous; stable only within dataset if needed |
| `workflow_version` | STRING(64) | O | — | Process boundary context |
| `case_summary` | TEXT | O | — | Synthetic bounded summary |
| `disposition` | ENUM | O | disposition | May also be represented by Closure; inconsistency can be tested |
| `external_case_reference` | STRING(256) | O | — | Reference to external workflow, synthetic only |
| `case_record_state` | ENUM | R | `OPEN_STATE`, `FINAL_STATE`, `REOPENED_STATE`, `UNKNOWN` | Helps snapshot interpretation |

### 9.2 Case-alert link

| Field | Type | Req. | Description and validation |
|---|---|---:|---|
| `case_alert_link_id` | UUID | R | Primary identifier |
| `case_id` | UUID | R | FK unless deliberately broken in source staging; canonical unresolved link uses Relationship Observation |
| `alert_id` | UUID | R | FK |
| `link_type` | ENUM | R | `PRIMARY`, `RELATED`, `DUPLICATE_OF`, `CAUSED_BY`, `UNKNOWN` |
| `linked_at_utc` | TIMESTAMP_UTC | O | Source event time |
| `source_link_id` | SOURCE_ID | O | Source relationship identifier |
| `link_source` | ENUM | R | `EXPLICIT`, `SOURCE_FOREIGN_KEY`, `MAPPING_RESOLUTION`, `UNKNOWN` |
| `link_quality_state` | ENUM | R | quality |

**Cardinality:** Alert `0..* ↔ 0..*` Case. Zero may be legitimate, missing, unresolved, or a negative-space condition depending on rule and scope.

---

## 10. Submitted Operational Evidence — Investigation

| Field | Type | Req. | Vocabulary/unit | Description and validation |
|---|---|---:|---|---|
| `investigation_id` | UUID | R | — | SAT-SA primary identifier |
| `source_investigation_id` | SOURCE_ID | O | — | Source identifier where supplied |
| `organization_id` | UUID | R | FK | Owning entity |
| `case_id` | UUID | O | FK | At least one of case/alert must be observed or unresolved reference recorded |
| `alert_id` | UUID | O | FK | Direct alert investigation where applicable |
| `investigation_sequence` | INTEGER | O | ≥ 1 | Source order within case; no silent reordering |
| `started_at_utc` | TIMESTAMP_UTC | R | event time | Investigation start |
| `ended_at_utc` | TIMESTAMP_UTC | O | event time | May be absent for open activity; if present normally ≥ start |
| `recorded_at_utc` | TIMESTAMP_UTC | O | source update | Distinguishes documentation time from action time |
| `investigation_status` | ENUM | R | investigation-status vocabulary | Current state/outcome |
| `analyst_role_code` | STRING(128) | O | — | Role/team, not real identity |
| `analyst_pseudonym` | STRING(128) | O | — | Synthetic/pseudonymous stable token |
| `method_code` | STRING(128) | O | — | Investigation method type |
| `runbook_id` | STRING(128) | O | — | Source/template/runbook reference |
| `template_id` | STRING(128) | O | — | Approved template reference where available |
| `automation_state` | ENUM | O | `MANUAL`, `AUTOMATED`, `MIXED`, `UNKNOWN` | Context for repetition/timing |
| `investigation_notes` | TEXT | O | bounded Unicode | Input for repetition analysis; synthetic only in dataset; never logged routinely |
| `conclusion_code` | STRING(128) | O | mapped/source conclusion | Source-specific mapping retained |
| `disposition` | ENUM | O | disposition vocabulary | Outcome where represented here |
| `evidence_reference_text` | TEXT | O | bounded | Source references without requiring raw forensic data |
| `workflow_version` | STRING(64) | O | — | Process-change context |

### 10.1 Investigation note constraints

- Notes have an implementation-defined safe maximum length.
- Plain text only; HTML/script is not interpreted.
- Exact source text is preserved locally; normalized text and TF-IDF features are derived Plane B data.
- Repetition does not imply poor investigation; `runbook_id`, `template_id`, automation, exception, and case-specific fields are counterevidence.

---

## 11. Submitted Operational Evidence — Escalation

| Field | Type | Req. | Vocabulary/unit | Description and validation |
|---|---|---:|---|---|
| `escalation_id` | UUID | R | — | SAT-SA primary identifier |
| `source_escalation_id` | SOURCE_ID | O | — | Source identifier where supplied |
| `organization_id` | UUID | R | FK | Owning entity |
| `case_id` | UUID | O | FK | At least case or alert reference required/observed |
| `alert_id` | UUID | O | FK | Direct alert escalation |
| `escalated_at_utc` | TIMESTAMP_UTC | R | event time | Escalation occurrence |
| `escalation_type` | ENUM | R | escalation-type vocabulary | Operational/management/external/etc. |
| `source_role_code` | STRING(128) | O | — | Originating role/team |
| `target_role_code` | STRING(128) | R | — | Destination role/team; no real person required |
| `escalation_level` | STRING(64) | O | — | Source level/tier |
| `escalation_reason` | TEXT | O | — | Bounded source text |
| `escalation_status` | ENUM | R | `INITIATED`, `ACKNOWLEDGED`, `ACCEPTED`, `REJECTED`, `CANCELLED`, `RESOLVED`, `UNKNOWN` | Lifecycle |
| `acknowledged_at_utc` | TIMESTAMP_UTC | O | event time | Normally ≥ escalated time |
| `resolved_at_utc` | TIMESTAMP_UTC | O | event time | Normally ≥ escalated time |
| `resolution_summary` | TEXT | O | — | Bounded context |
| `policy_trigger_code` | STRING(128) | O | — | Source/config trigger reference, not invented policy |
| `workflow_version` | STRING(64) | O | — | Process boundary |

---

## 12. Submitted Operational Evidence — Action / Remediation

| Field | Type | Req. | Vocabulary/unit | Description and validation |
|---|---|---:|---|---|
| `action_id` | UUID | R | — | SAT-SA primary identifier |
| `source_action_id` | SOURCE_ID | O | — | Source identifier where supplied |
| `organization_id` | UUID | R | FK | Owning entity |
| `asset_id` | UUID | O | FK | At least one asset/alert/case subject required or unresolved reference recorded |
| `alert_id` | UUID | O | FK | Related alert |
| `case_id` | UUID | O | FK | Related case |
| `action_type` | ENUM | R | `INVESTIGATE`, `CONTAIN`, `ERADICATE`, `RECOVER`, `PATCH`, `TUNE_RULE`, `SUPPRESS`, `ACCEPT_RISK`, `MONITOR`, `OTHER`, `UNKNOWN` | Operational/remediation action |
| `created_at_utc` | TIMESTAMP_UTC | R | event time | Action creation |
| `due_at_utc` | TIMESTAMP_UTC | O | event time | Due date/time |
| `started_at_utc` | TIMESTAMP_UTC | O | event time | Start |
| `completed_at_utc` | TIMESTAMP_UTC | O | event time | Completion; normally ≥ created/start |
| `action_status` | ENUM | R | action-status vocabulary | Lifecycle |
| `owner_role_code` | STRING(128) | O | — | Synthetic team/role |
| `remediation_reference` | STRING(256) | O | — | Synthetic ticket/change reference |
| `action_summary` | TEXT | O | — | Bounded description |
| `verification_state` | ENUM | O | `NOT_VERIFIED`, `VERIFIED`, `FAILED_VERIFICATION`, `NOT_APPLICABLE`, `UNKNOWN` | Whether outcome was checked |
| `exception_id` | UUID | O | FK | Accepted risk/exception context |
| `workflow_version` | STRING(64) | O | — | Process boundary |

**Recurrence use:** Analytics may derive repeated-alert groups from alert signatures and search actions linked to any member, case, or asset. Lack of an Action record is not enough without source-family completeness and expectation basis.

---

## 13. Submitted Operational Evidence — Resolution and Closure

### 13.1 Resolution

| Field | Type | Req. | Vocabulary/unit | Description and validation |
|---|---|---:|---|---|
| `resolution_id` | UUID | R | — | Primary identifier |
| `source_resolution_id` | SOURCE_ID | O | — | Source identifier where supplied |
| `organization_id` | UUID | R | FK | Owning entity |
| `case_id` | UUID | O | FK | At least case or alert subject required |
| `alert_id` | UUID | O | FK | Optional direct resolution |
| `resolved_at_utc` | TIMESTAMP_UTC | R | event time | Substantive resolution time |
| `resolution_type` | ENUM | R | `MITIGATED`, `REMEDIATED`, `CONTAINED`, `FALSE_POSITIVE`, `DUPLICATE`, `SUPPRESSED`, `ACCEPTED_RISK`, `NO_ACTION_REQUIRED`, `OTHER`, `UNKNOWN` | What resolved means |
| `resolution_status` | ENUM | R | `PROPOSED`, `APPROVED`, `IMPLEMENTED`, `VERIFIED`, `REJECTED`, `UNKNOWN` | Resolution lifecycle |
| `resolution_reason` | TEXT | O | — | Bounded explanation |
| `approved_by_role_code` | STRING(128) | O | — | Role only |
| `verification_reference` | STRING(256) | O | — | Synthetic evidence/ticket reference |
| `exception_id` | UUID | O | FK | Accepted-risk/suppression context |
| `workflow_version` | STRING(64) | O | — | Process boundary |

### 13.2 Closure

| Field | Type | Req. | Vocabulary/unit | Description and validation |
|---|---|---:|---|---|
| `closure_id` | UUID | R | — | Primary identifier |
| `source_closure_id` | SOURCE_ID | O | — | Source identifier where supplied |
| `organization_id` | UUID | R | FK | Owning entity |
| `case_id` | UUID | O | FK | At least case or alert subject required |
| `alert_id` | UUID | O | FK | Optional direct closure |
| `resolution_id` | UUID | O | FK | Link where resolution is separate |
| `closed_at_utc` | TIMESTAMP_UTC | R | event time | Administrative closure time |
| `closure_status` | ENUM | R | `CLOSED`, `REOPENED`, `VOIDED`, `UNKNOWN` | Closure lifecycle |
| `disposition` | ENUM | R | disposition vocabulary | Supports duplicate/false positive/accepted risk/etc. |
| `closure_reason` | TEXT | O | — | Bounded source explanation |
| `closed_by_role_code` | STRING(128) | O | — | Role/team only |
| `approval_state` | ENUM | O | `NOT_REQUIRED`, `PENDING`, `APPROVED`, `REJECTED`, `UNKNOWN` | Workflow control context |
| `approved_at_utc` | TIMESTAMP_UTC | O | event time | Conditional on approval |
| `exception_id` | UUID | O | FK | Exception/suppression/accepted-risk context |
| `workflow_version` | STRING(64) | O | — | Process boundary |

**PROJECT DECISION:** Resolution and closure remain separate canonical families. Sources that combine them may map one source record to both canonical records with shared provenance or populate only Closure, depending on the mapping profile. The mapping must not fabricate a resolution event.

---

## 14. Submitted Operational Evidence — Exception, Applicability, and Process Change

### 14.1 Exception / Applicability

| Field | Type | Req. | Vocabulary/unit | Description and validation |
|---|---|---:|---|---|
| `exception_id` | UUID | R | — | Primary identifier |
| `source_exception_id` | SOURCE_ID | O | — | Source reference |
| `organization_id` | UUID | R | FK | Owning entity |
| `exception_type` | ENUM | R | exception-type vocabulary | Approved automation, suppression, maintenance, etc. |
| `target_type` | ENUM | R | `ORGANIZATION`, `ASSET`, `ALERT`, `CASE`, `INVESTIGATION`, `ESCALATION`, `ACTION`, `CONTROL`, `PROCESS`, `RULE`, `PERIOD` | Polymorphic target family |
| `target_id` | UUID | O | typed reference | Required unless target is whole organization/period via separate scope |
| `rule_expectation_id` | UUID | O | config FK | Rule/expectation to which exception applies |
| `applicability_state` | ENUM | R | `APPLIES`, `DOES_NOT_APPLY`, `PARTIALLY_APPLIES`, `UNKNOWN` | Explicit applicability result |
| `approved_state` | ENUM | R | `APPROVED`, `PENDING`, `REJECTED`, `EXPIRED`, `UNKNOWN` | Only approved active exceptions reduce concern |
| `approved_by_role_code` | STRING(128) | O | — | Role, not real person |
| `reason` | TEXT | R | — | Bounded explanation |
| `effective_start_at_utc` | TIMESTAMP_UTC | R | — | Start |
| `effective_end_at_utc` | TIMESTAMP_UTC | O | — | Exclusive end |
| `created_at_utc` | TIMESTAMP_UTC | R | source event | Record creation |
| `evidence_reference` | STRING(256) | O | — | Synthetic approval/change reference |
| `scope_definition` | JSON_OBJECT | O | bounded | Structured scope when one target ID is insufficient |
| `exception_quality_state` | ENUM | R | quality | Provenance/validity assessment |

### 14.2 Exception vocabulary

`APPROVED_AUTOMATION`, `APPROVED_SUPPRESSION`, `MAINTENANCE_WINDOW`, `KNOWN_EXCEPTION`, `NOT_APPLICABLE`, `EMERGENCY_PROCESS`, `POLICY_CHANGE`, `WORKFLOW_CHANGE`, `NEW_TOOLING`, `MIGRATION_PERIOD`, `ACCEPTED_RISK`, `TEMPORARY_DECOMMISSIONING`, `OTHER`, `UNKNOWN`.

### 14.3 Process-change boundary

| Field | Type | Req. | Description and validation |
|---|---|---:|---|
| `process_change_id` | UUID | R | Primary identifier |
| `organization_id` | UUID | R | Owning entity |
| `change_type` | ENUM | R | `POLICY`, `WORKFLOW`, `TOOLING`, `MAPPING`, `AUTOMATION`, `MERGER`, `ASSET_SCOPE`, `OTHER` |
| `effective_at_utc` | TIMESTAMP_UTC | R | Baseline boundary time |
| `end_at_utc` | TIMESTAMP_UTC | O | Temporary change end |
| `previous_version` | STRING(64) | O | Prior workflow/tool version |
| `new_version` | STRING(64) | O | New version |
| `affected_families` | JSON_ARRAY<ENUM> | R | Ordered, bounded list of canonical evidence families; values must use the record-family vocabulary |
| `change_summary` | TEXT | R | Synthetic/non-sensitive explanation |
| `approved_state` | ENUM | R | Approval state |
| `exception_id` | UUID | O | Related exception/change authorization |

This record permits historical baselines to split or abstain at known regime changes.

### 14.4 Control / Process Reference

Control and process references are versioned supervisory subjects used to connect expectations, findings, and prioritized review scopes. They may be supplied by a source submission or configured locally. Their presence does not mean SAT-SA certifies the control or process.

| Field | Type | Req. | Description and validation |
|---|---|---:|---|
| `control_process_ref_id` | UUID | R | SAT-SA-generated primary identifier |
| `organization_id` | UUID | O | Owning organization when the reference is entity-specific; absent for reusable generic references |
| `reference_type` | ENUM | R | `CONTROL` or `PROCESS` |
| `reference_code` | CODE | R | Versioned canonical code; unique within organization/generic namespace, type, and version |
| `source_reference_id` | SOURCE_ID | O | Source-provided control/process identifier where supplied |
| `display_name` | STRING(200) | R | Neutral name used in examiner queues and reports |
| `description` | TEXT | O | Bounded description; must not imply certification |
| `authority_type` | ENUM | R | `SOURCE_SUBMITTED`, `PROJECT_DEMO_CONFIGURATION`, `AUTHORITATIVE_CONFIGURATION`, `OTHER`, `UNKNOWN` |
| `source_reference_text` | STRING(512) | O | Policy/framework/source citation or local reference where supplied |
| `version` | STRING(64) | R | Reference-definition version |
| `effective_start_at_utc` | TIMESTAMP_UTC | R | Start of applicability |
| `effective_end_at_utc` | TIMESTAMP_UTC | O | Exclusive end after start |
| `status` | ENUM | R | `DRAFT`, `ACTIVE`, `SUPERSEDED`, `RETIRED`, `UNKNOWN` |
| `submission_id` | UUID | O | Provenance when source-submitted |
| `source_record_id` | UUID | O | Exact source record when source-submitted |

### 14.5 Control / Process Subject Link

This link permits a control or process to apply to an operational record, rule/expectation, finding, or review sample without adding control columns to every evidence family.

| Field | Type | Req. | Description and validation |
|---|---|---:|---|
| `control_process_link_id` | UUID | R | Primary identifier |
| `control_process_ref_id` | UUID | R | Referenced control/process definition |
| `subject_type` | ENUM | R | `ORGANIZATION`, `ASSET`, `ALERT`, `CASE`, `INVESTIGATION`, `ESCALATION`, `ACTION`, `RESOLUTION`, `CLOSURE`, `RULE_EXPECTATION`, `FINDING`, or `REVIEW_SAMPLE` |
| `subject_id` | UUID | R | Typed subject reference |
| `link_role` | ENUM | R | `APPLIES_TO`, `ASSESSES`, `AFFECTS`, `SUPPORTS`, `EXCEPTION_FOR`, or `PRIORITIZES` |
| `effective_start_at_utc` | TIMESTAMP_UTC | O | Link applicability start |
| `effective_end_at_utc` | TIMESTAMP_UTC | O | Exclusive end after start |
| `source_type` | ENUM | R | `SOURCE_SUBMITTED`, `MAPPING_DERIVED`, `RULE_CONFIGURATION`, `EXAMINER_ASSIGNED`, or `UNKNOWN` |
| `source_record_id` | UUID | O | Provenance when supplied/mapped from operational evidence |
| `quality_state` | ENUM | R | Validity/usability of the link |

**PROJECT DECISION:** A control/process reference is never created merely because a finding category has a similar name. It requires submitted/configured provenance or an explicit examiner assignment.

---

## 15. Relationship and Identifier Contract

### 15.1 Core relationships

| Relationship | Cardinality | Required? | Legitimate absence handling |
|---|---|---|---|
| Organization → Submission | `1 → 0..*` | Submission must have one organization | Organization may have no submission for a period; schedule evaluation is separate |
| Submission → Source File | `1 → 1..*` for accepted submission | Yes for accepted | Empty package rejected |
| Source File → Source Record | `1 → 0..*` | No | Header-only/invalid file allowed as quality evidence |
| Source Record → Canonical Record | `1 → 0..*` | No | Invalid/skipped source record may normalize to none; one source record may create resolution + closure |
| Organization → Asset | `1 → 0..*` | Asset must have organization | Inventory family may be not provided |
| Asset → Monitoring Coverage | `1 → 0..*` | No | Absence needs relationship observation and adequate scope |
| Organization → Alert | `1 → 0..*` | Alert must have organization | Explicit zero differs from no alert file |
| Alert ↔ Case | `0..* ↔ 0..*` | No | Case-alert link or unresolved relationship observation |
| Case → Investigation | `1 → 0..*` | Investigation may alternatively link directly to alert | Missing relation may be gap, not automatic failure |
| Case/Alert → Escalation | `1 → 0..*` | No | Applicability and grace period determine expectation |
| Asset/Alert/Case → Action | `1 → 0..*` | No | At least one action subject when Action exists |
| Case/Alert → Resolution | `1 → 0..*` | No | Some sources combine resolution/closure |
| Case/Alert → Closure | `1 → 0..*` | No | Open records legitimately lack closure |
| Exception → Target | `0..* → 1 scope` | Yes conceptually | Unresolved target makes exception insufficient/invalid |
| Control/Process Reference → Subject | `1 → 0..*` | No | A reference may exist before it is linked; links require explicit provenance/configuration |
| Finding → Evidence Link | `1 → 1..*` for queueable operational finding | Yes | Quality-only system diagnostics may have source/file evidence instead |
| Review Sample → Review Sample Member | `1 → 1..*` for a sealed nonempty sample | Yes when sealed | Draft sample may temporarily be empty |
| Finding → Review/Disposition | `1 → 0..*` | No | Unreviewed findings legitimately have no review event |
| Lifecycle object → Audit Event | `1 → 0..*` | Required for auditable actions defined in architecture | Historical imported objects may carry an explicit audit-gap limitation |

### 15.2 Identifier source and nullability

| Entity | Primary ID | Source ID | Uniqueness scope | Missing source ID allowed? |
|---|---|---|---|---|
| Organization | `organization_id` | `source_organization_id` | dataset/workspace when present | Yes |
| Submission | `submission_id` | `source_submission_id` | organization/source system | Yes |
| Source File | `source_file_id` | original filename is not identity | submission | N/A |
| Source Record | `source_record_id` | `source_native_record_id` | file/family | Yes; locator required |
| Asset | `asset_id` | `source_asset_id` | organization/source system/effective interval when present | Yes; source record locator required |
| Alert | `alert_id` | `source_alert_id` | organization/source system when present | Yes; source record locator required |
| Case | `case_id` | `source_case_id` | organization/source system when present | Yes; source record locator required |
| Investigation | `investigation_id` | `source_investigation_id` | organization/source system when present | Yes; source record locator required |
| Escalation | `escalation_id` | `source_escalation_id` | organization/source system when present | Yes; source record locator required |
| Action | `action_id` | `source_action_id` | organization/source system when present | Yes; source record locator required |
| Resolution | `resolution_id` | `source_resolution_id` | organization/source system when present | Yes; source record locator required |
| Closure | `closure_id` | `source_closure_id` | organization/source system when present | Yes; source record locator required |
| Exception | `exception_id` | `source_exception_id` | organization/source system | Yes if generated from explicit synthetic/context record |
| Control/Process Reference | `control_process_ref_id` | `source_reference_id` | organization/generic namespace, type, and version when present | Yes |

**PROJECT DECISION:** Canonicalization never generates a fake source business ID. SAT-SA generates its own UUID and records `NOT_PROVIDED` for the source ID when the family permits it.

---

## 16. Data-Quality Metadata

### 16.1 Quality status vocabulary

- `VALID`
- `WARNING`
- `INVALID`
- `INCOMPLETE`
- `PARTIAL_PERIOD`
- `IMMATURE_PERIOD`
- `DUPLICATE_EXACT`
- `DUPLICATE_CONFLICTING`
- `BROKEN_RELATIONSHIP`
- `UNKNOWN_SCOPE`
- `SCHEMA_MISMATCH`
- `UNKNOWN`

These may be issue codes or aggregate states. Aggregate usability remains `SUFFICIENT`, `SUFFICIENT_WITH_LIMITATIONS`, `INSUFFICIENT`, or `INDETERMINATE`.

### 16.2 Data-quality issue

| Field | Type | Req. | Description and validation |
|---|---|---:|---|
| `quality_issue_id` | UUID | R | Primary identifier |
| `scope_type` | ENUM | R | `FIELD`, `RECORD`, `RELATIONSHIP`, `EVIDENCE_FAMILY`, `SUBMISSION`, `PERIOD`, `FINDING` |
| `scope_id` | UUID | R | Typed target reference |
| `organization_id` | UUID | O | Owning entity when applicable |
| `submission_id` | UUID | O | Source submission when applicable |
| `issue_code` | CODE | R | Stable machine-readable code |
| `quality_status` | ENUM | R | Quality vocabulary |
| `usability_state` | ENUM | R | Aggregate usability |
| `severity` | ENUM | R | `INFO`, `WARNING`, `ERROR`, `BLOCKING` — quality severity, not cyber severity |
| `message` | TEXT | R | Sanitized explanation |
| `affected_field_name` | CODE | O | Field scope |
| `related_source_record_id` | UUID | O | Provenance |
| `detected_at_utc` | TIMESTAMP_UTC | R | Validation time |
| `validator_version` | STRING(64) | R | Reproducibility |
| `resolved_state` | ENUM | R | `OPEN`, `ACKNOWLEDGED`, `RESOLVED_BY_RESUBMISSION`, `ACCEPTED_LIMITATION` |

### 16.3 Quality aggregation

- Field issues roll up to record usability.
- Record/relationship issues roll up to evidence-family and submission completeness.
- Period completeness combines family coverage, maturity, and late-arrival rules.
- Finding quality is calculated from only the fields/relationships it depends on.
- A high volume of warnings does not automatically equal operational risk.

---

## 17. Temporal Semantics

### 17.1 Time dimensions

| Time concept | Meaning | Examples |
|---|---|---|
| Event time | When operational action occurred | alert created, investigation started, escalation occurred |
| Source update time | When source record was last changed | case corrected after closure |
| Submission time | When CSE/export declares package submitted | `submitted_at_utc` |
| Ingestion time | When SAT-SA received/processed data | `received_at_utc`, `normalized_at_utc` |
| Reporting period | Scope the package claims to cover | `[period_start, period_end)` |
| Effective interval | When a profile, coverage, exception, or rule applies | asset/exception start/end |
| Analytical run time | When SAT-SA froze and processed evidence | run started/completed |
| Process-change boundary | When comparable workflow/tool regime changes | tooling migration effective time |

### 17.2 Late-arriving data

A source record is late-arriving when its operational event time falls inside a prior reporting period but it is first received in a later submission. It retains:

- original event time;
- source update time if provided;
- first received submission/time;
- later revision provenance;
- late-arrival quality/context flag.

Historical findings are not overwritten. A later rerun creates a new run/finding revision.

### 17.3 Invalid ordering

Investigation after closure, closure before alert/case creation, escalation before alert creation, or negative duration is preserved exactly and receives quality/consistency diagnostics. SAT-SA does not silently reorder or clamp timestamps.

### 17.4 Precision and timezone

- Original precision (`DATE`, minute, second, millisecond) is retained in provenance.
- Canonical `TIMESTAMP_UTC` requires a resolvable instant.
- A mapping-applied default timezone creates a warning and records the mapping assumption.
- Daylight-saving ambiguities must resolve explicitly or remain invalid/unknown.

### 17.5 Period maturity

A period can be `MATURE`, `IMMATURE`, `PARTIAL`, or `UNKNOWN`. Negative-space and timing findings declare the maturity/grace rule they used.

---

## 18. Controlled Vocabularies and Source Mappings

### 18.1 Core vocabularies

| Vocabulary | Allowed canonical values |
|---|---|
| Severity | `INFORMATIONAL`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`, `UNKNOWN` |
| Alert status | `NEW`, `OPEN`, `ACKNOWLEDGED`, `IN_INVESTIGATION`, `RESOLVED`, `CLOSED`, `SUPPRESSED`, `REOPENED`, `UNKNOWN` |
| Case status | `NEW`, `OPEN`, `ASSIGNED`, `IN_INVESTIGATION`, `PENDING`, `ESCALATED`, `RESOLVED`, `CLOSED`, `REOPENED`, `CANCELLED`, `UNKNOWN` |
| Investigation status | `NOT_STARTED`, `IN_PROGRESS`, `COMPLETED`, `BLOCKED`, `CANCELLED`, `UNKNOWN` |
| Disposition | `TRUE_POSITIVE`, `FALSE_POSITIVE`, `BENIGN`, `DUPLICATE`, `SUPPRESSED`, `ACCEPTED_RISK`, `NO_ACTION_REQUIRED`, `CONFIRMED_INCIDENT`, `OTHER`, `UNKNOWN` |
| Escalation type | `TECHNICAL`, `MANAGEMENT`, `INCIDENT_RESPONSE`, `BUSINESS_OWNER`, `VENDOR`, `EXTERNAL_AUTHORITY`, `OTHER`, `UNKNOWN` |
| Action status | `PLANNED`, `OPEN`, `IN_PROGRESS`, `COMPLETED`, `VERIFIED`, `DEFERRED`, `CANCELLED`, `FAILED`, `UNKNOWN` |
| Asset criticality | `LOW`, `MODERATE`, `HIGH`, `CRITICAL`, `UNKNOWN` |
| Monitoring status | `COVERED`, `PARTIALLY_COVERED`, `NOT_COVERED`, `ONBOARDING`, `DEGRADED`, `SUSPENDED`, `UNKNOWN` |
| Exception type | Values in §14.2 |
| Finding category | `EXECUTION_GAP`, `NEGATIVE_SPACE`, `HISTORICAL_DEVIATION`, `PEER_DEVIATION`, `CROSS_RECORD_INCONSISTENCY`, `REPETITIVE_INVESTIGATION`, `ANOMALY_LEAD`, `DATA_QUALITY` |
| Attention level | `URGENT`, `HIGH`, `MEDIUM`, `ROUTINE` |
| Evidence confidence | `STRONG`, `MODERATE`, `LIMITED`, `INDETERMINATE` |
| Finding data quality | `SUFFICIENT`, `SUFFICIENT_WITH_LIMITATIONS`, `INSUFFICIENT`, `INDETERMINATE` |
| Evidence role | `TRIGGER`, `SUPPORTING`, `EXPECTED_UNIVERSE`, `SEARCH_SCOPE`, `COUNTEREVIDENCE`, `EXCEPTION`, `BASELINE_MEMBER`, `PEER_MEMBER`, `QUALITY_LIMITATION`, `SOURCE_CONTEXT` |

### 18.2 Vocabulary mapping

| Field | Type | Req. | Description |
|---|---|---:|---|
| `vocabulary_mapping_id` | UUID | R | Primary identifier |
| `mapping_version_id` | UUID | R | Parent mapping version |
| `vocabulary_name` | CODE | R | Target vocabulary |
| `source_system_id` | STRING(128) | R | Source namespace |
| `source_value_text` | STRING(256) | R | Exact source token |
| `canonical_value` | CODE | R | Allowed target value or `UNKNOWN` |
| `mapping_confidence` | ENUM | R | `EXACT`, `APPROXIMATE`, `MANUAL_REVIEW`, `UNKNOWN` |
| `effective_start_at_utc` | TIMESTAMP_UTC | R | Effective mapping start |
| `effective_end_at_utc` | TIMESTAMP_UTC | O | Exclusive end |
| `mapping_note` | TEXT | O | Rationale/limitations |

**PROJECT DECISION:** Unknown source vocabulary is preserved and mapped to `UNKNOWN` with a quality warning. It is never forced into the closest canonical category silently.

---

## 19. Derived Analytical Data Contract

Derived records are Plane B. They are not accepted as submitted operational evidence.

### 19.1 Analytical run

| Field | Type | Req. | Description |
|---|---|---:|---|
| `analytical_run_id` | UUID | R | Primary identifier |
| `run_status` | ENUM | R | `PLANNED`, `RUNNING`, `COMPLETED`, `COMPLETED_WITH_FAILURES`, `FAILED`, `CANCELLED` |
| `scope_submission_ids` | JSON_ARRAY<UUID> | R | Ordered, de-duplicated frozen submission list |
| `scope_organization_ids` | JSON_ARRAY<UUID> | R | Ordered, de-duplicated frozen entity list |
| `schema_version` | STRING(32) | R | Canonical schema version |
| `mapping_version_set_hash` | HASH_SHA256 | R | Frozen mapping set |
| `rule_set_version` | STRING(64) | R | Active rule set |
| `configuration_hash` | HASH_SHA256 | R | Complete run config |
| `feature_set_version` | STRING(64) | O | Optional ML/text features |
| `model_version_id` | UUID | O | Optional model |
| `random_seed` | INTEGER | O | Required for stochastic module |
| `started_at_utc` | TIMESTAMP_UTC | R | Run time |
| `completed_at_utc` | TIMESTAMP_UTC | O | Completion time |
| `run_manifest_sha256` | HASH_SHA256 | O | Present when sealed |
| `module_failures` | JSON_ARRAY<OBJECT> | O | Sanitized entries with documented keys `module_id`, `module_version`, `failure_code`, and bounded `reason` |

### 19.2 Derived metric

| Field | Type | Req. | Description |
|---|---|---:|---|
| `derived_metric_id` | UUID | R | Primary identifier |
| `analytical_run_id` | UUID | R | Producing run |
| `metric_definition_id` | UUID | R | Versioned formula/semantic definition |
| `subject_type` | ENUM | R | Entity, asset, alert, case, period, cohort, etc. |
| `subject_id` | UUID | R | Target subject |
| `period_start_at_utc` | TIMESTAMP_UTC | O | Metric period |
| `period_end_at_utc` | TIMESTAMP_UTC | O | Metric period |
| `numeric_value` | DECIMAL | O | Typed numerical result |
| `text_value` | STRING(512) | O | Non-numeric result where defined |
| `unit_code` | CODE | R | `SECONDS`, `COUNT`, `RATIO`, `PERCENTILE`, `RAW_SCORE`, etc. |
| `eligibility_state` | ENUM | R | `ELIGIBLE`, `INSUFFICIENT_HISTORY`, `INSUFFICIENT_PEERS`, `INCOMPARABLE`, `INSUFFICIENT_QUALITY`, `INDETERMINATE` |
| `input_record_count` | INTEGER | R | ≥ 0 |
| `calculation_inputs_hash` | HASH_SHA256 | R | Reproducibility |
| `quality_state` | ENUM | R | Derived result quality |

### 19.3 Historical baseline summary

Includes `baseline_id`, metric definition/version, entity, window, comparable filters, eligible/excluded counts, median, configured percentiles, IQR, MAD, current value, effect magnitude, process-boundary ID, eligibility state, membership snapshot hash, and run ID. Exact statistical thresholds are deferred.

### 19.4 Peer cohort summary

Includes `peer_cohort_id`, cohort-definition version, metric version, target entity/period, eligible/excluded member counts, denominator definition, peer median/percentiles/IQR/MAD, entity value, percentile/deviation, quality-comparability notes, membership snapshot hash, and state (`ELIGIBLE`, `INSUFFICIENT_PEERS`, `INCOMPARABLE`, `INDETERMINATE`).

### 19.5 Optional anomaly output

Includes candidate subject, raw model score, threshold/configuration reference, feature-set version, model version, feature-input hash, quality state, and explanation context. It never stores “probability of wrongdoing.”

---

## 20. Finding, Evidence, and Review Contract

### 20.1 Finding

| Field | Type | Req. | Description and validation |
|---|---|---:|---|
| `finding_id` | UUID | R | Stable identity across revisions |
| `finding_revision_id` | UUID | R | Immutable revision identifier |
| `revision_number` | INTEGER | R | ≥ 1 |
| `analytical_run_id` | UUID | R | Producing run |
| `organization_id` | UUID | R | Subject entity |
| `period_start_at_utc` | TIMESTAMP_UTC | R | Finding scope |
| `period_end_at_utc` | TIMESTAMP_UTC | R | Exclusive end |
| `finding_category` | ENUM | R | Finding vocabulary |
| `title` | STRING(240) | R | Neutral concise title |
| `what_happened` | TEXT | R | Observation, not allegation |
| `why_flagged` | TEXT | R | Basis summary |
| `attention_level` | ENUM | R | Independent review urgency band |
| `evidence_confidence` | ENUM | R | Independent support strength |
| `finding_data_quality` | ENUM | R | Independent input usability |
| `calculation_summary` | TEXT | R | Human-readable metric/denominator/context |
| `calculation_payload` | JSON_OBJECT | R | Versioned typed inputs/results; no hidden ground truth |
| `investigation_question` | TEXT | R | Neutral examiner prompt |
| `limitations_uncertainty` | TEXT | R | Alternative explanations and constraints |
| `priority_explanation` | TEXT | R | Why queue band/order was assigned |
| `correlation_key` | STRING(256) | O | Groups shared root condition |
| `affected_record_count` | INTEGER | R | ≥ 0 |
| `rule_version_id` | UUID | O | Deterministic expectation basis |
| `model_version_id` | UUID | O | Optional supporting model |
| `feature_set_version` | STRING(64) | O | Text/ML version |
| `generated_at_utc` | TIMESTAMP_UTC | R | Generation time |
| `finding_status` | ENUM | R | `ACTIVE`, `SUPERSEDED`, `WITHDRAWN_BY_RERUN`, `ARCHIVED` |

### 20.2 Analytical basis

A finding may contain multiple basis records. Each basis identifies type (`RULE`, `HISTORICAL`, `PEER`, `NEGATIVE_SPACE`, `CONSISTENCY`, `TEXT_SIMILARITY`, `ML_ANOMALY`), method/version, independence group, calculation reference, and plain-language explanation. Shared evidence/root causes use the same independence group to prevent double counting.

### 20.3 Evidence link

| Field | Type | Req. | Description and validation |
|---|---|---:|---|
| `evidence_link_id` | UUID | R | Primary identifier |
| `finding_revision_id` | UUID | R | Parent finding revision |
| `evidence_role` | ENUM | R | Controlled role vocabulary |
| `canonical_record_family` | ENUM | O | Target family |
| `canonical_record_id` | UUID | O | Target record |
| `field_observation_id` | UUID | O | Exact field/value provenance |
| `source_record_id` | UUID | O | Direct source context |
| `derived_metric_id` | UUID | O | Calculation/baseline/peer result |
| `relationship_observation_id` | UUID | O | Missing/broken relation support |
| `relevance_summary` | TEXT | R | Why evidence matters |
| `display_order` | INTEGER | R | ≥ 1 |
| `evidence_validation_state` | ENUM | R | `VALID`, `LIMITED`, `INVALID`, `MISSING_REFERENCE` |

At least one resolvable source/canonical/quality evidence path is required for a queueable finding.

### 20.4 Review / disposition

Review/disposition is structured human workflow state. It is not submitted evidence and is not synthetic ground truth.

| Field | Type | Req. | Description and validation |
|---|---|---:|---|
| `review_event_id` | UUID | R | Immutable review-event identifier |
| `finding_revision_id` | UUID | R | Exact finding revision reviewed |
| `examiner_actor_id` | UUID | R | Local authenticated/pseudonymous actor identifier |
| `review_status` | ENUM | R | `IN_REVIEW`, `NEEDS_INFORMATION`, `EXPLAINED`, `CONFIRMED_FOR_FOLLOW_UP`, `DISMISSED`, or `DEFERRED`; `UNREVIEWED` is represented by absence of a review event |
| `disposition_code` | ENUM | O | `NO_DISPOSITION`, `FOLLOW_UP_REQUIRED`, `LEGITIMATE_EXPLANATION`, `DATA_CORRECTION_REQUIRED`, `DUPLICATE_FINDING`, `OUT_OF_SCOPE`, `OTHER` |
| `examiner_notes` | TEXT | O | Bounded human note; no hidden ground-truth label |
| `follow_up_question` | TEXT | O | Examiner-authored/requested follow-up |
| `system_attention_level` | ENUM | R | Original system-assigned band copied by reference/value for review context |
| `priority_override_level` | ENUM | O | Examiner-selected attention band; does not overwrite system value |
| `priority_override_reason` | TEXT | C | Required when override is present |
| `created_at_utc` | TIMESTAMP_UTC | R | Review event time |
| `supersedes_review_event_id` | UUID | O | Prior review event replaced by this event; history retained |
| `audit_event_id` | UUID | R | Corresponding audit event |

### 20.5 Review sample

A review sample is an explicit examiner-facing shortlist of records selected for manual review. It may be generated from a finding, entity queue, control/process scope, or an examiner request. It never replaces the underlying source/canonical records.

| Field | Type | Req. | Description and validation |
|---|---|---:|---|
| `review_sample_id` | UUID | R | Primary identifier |
| `analytical_run_id` | UUID | R | Run from which system-selected members were drawn |
| `organization_id` | UUID | R | Subject entity |
| `finding_revision_id` | UUID | O | Parent finding when sample is finding-specific |
| `control_process_ref_id` | UUID | O | Control/process scope where applicable |
| `sample_type` | ENUM | R | `FINDING_EVIDENCE`, `ALERT_SAMPLE`, `CASE_SAMPLE`, `CONTROL_SAMPLE`, `PROCESS_SAMPLE`, `DATA_QUALITY_SAMPLE`, or `EXAMINER_DEFINED` |
| `title` | STRING(240) | R | Neutral display title |
| `selection_method` | ENUM | R | `RULE_AFFECTED_RECORDS`, `PRIORITY_RANKED`, `STRATIFIED`, `RANDOM_BASELINE`, `EXAMINER_SELECTED`, or `OTHER` |
| `selection_method_version` | STRING(64) | R | Reproducible selection definition |
| `selection_rationale` | TEXT | R | Why these records were selected |
| `attention_level` | ENUM | O | Inherited/assigned review urgency; not a truth label |
| `created_by_type` | ENUM | R | `SYSTEM` or `EXAMINER` |
| `created_by_actor_id` | UUID | O | Required when examiner-created |
| `created_at_utc` | TIMESTAMP_UTC | R | Creation time |
| `sample_status` | ENUM | R | `DRAFT`, `SEALED`, `SUPERSEDED`, or `ARCHIVED` |
| `member_count` | INTEGER | R | Nonnegative; sealed samples require at least one member |

### 20.6 Review sample member

| Field | Type | Req. | Description and validation |
|---|---|---:|---|
| `review_sample_member_id` | UUID | R | Primary identifier |
| `review_sample_id` | UUID | R | Parent sample |
| `member_rank` | INTEGER | R | Positive stable order within sample |
| `member_type` | ENUM | R | `ALERT`, `CASE`, `INVESTIGATION`, `ESCALATION`, `ACTION`, `SOURCE_RECORD`, or `FINDING_EVIDENCE` |
| `canonical_record_family` | ENUM | O | Required for canonical operational members |
| `canonical_record_id` | UUID | O | Canonical member reference |
| `source_record_id` | UUID | O | Direct source-record member/reference |
| `evidence_link_id` | UUID | O | Finding-evidence member/reference |
| `selection_reason` | TEXT | R | Why this member is in the sample |
| `selection_factor_payload` | JSON_OBJECT | O | Documented method-specific factors; no hidden ground truth |
| `member_status` | ENUM | R | `INCLUDED`, `REMOVED_BY_EXAMINER`, `SUPERSEDED`, or `UNRESOLVED_REFERENCE` |
| `added_at_utc` | TIMESTAMP_UTC | R | Membership creation time |

Exactly one resolvable member path is required among canonical record, source record, and evidence link, except an explicitly `UNRESOLVED_REFERENCE` member retained for audit.

### 20.7 Audit event

Audit events provide an append-only logical history of imports, analytical runs, configuration activation, reviews, priority overrides, and exports. The schema does not claim cryptographic or physical immutability.

| Field | Type | Req. | Description and validation |
|---|---|---:|---|
| `audit_event_id` | UUID | R | Primary identifier |
| `event_sequence` | INTEGER | R | Positive monotonic sequence within one local workspace/audit stream |
| `occurred_at_utc` | TIMESTAMP_UTC | R | Event time |
| `actor_id` | UUID | O | Local actor; absent only for identified system service events |
| `actor_type` | ENUM | R | `SYSTEM`, `ADMINISTRATOR`, `EXAMINER`, `READ_ONLY_REVIEWER`, or `UNKNOWN` |
| `event_type` | ENUM | R | Versioned event code such as `SUBMISSION_IMPORTED`, `RUN_SEALED`, `FINDING_REVIEWED`, `PRIORITY_OVERRIDDEN`, `CONFIG_ACTIVATED`, or `REPORT_EXPORTED` |
| `target_type` | ENUM | R | Audited object family |
| `target_id` | UUID | R | Audited object identifier |
| `analytical_run_id` | UUID | O | Related run where applicable |
| `submission_id` | UUID | O | Related submission where applicable |
| `prior_version_ref` | STRING(256) | O | Prior object/version reference |
| `current_version_ref` | STRING(256) | O | Resulting object/version reference |
| `reason` | TEXT | O | Required by the relevant action policy, including priority override |
| `event_payload` | JSON_OBJECT | O | Bounded, documented metadata without unnecessary sensitive source content |
| `outcome` | ENUM | R | `SUCCEEDED`, `FAILED`, `PARTIAL`, or `DENIED` |
| `previous_audit_event_id` | UUID | O | Prior event in the same logical stream |
| `event_payload_sha256` | HASH_SHA256 | O | Integrity check for stored payload; does not make the audit log tamper-proof |

---

## 21. Synthetic Dataset Package Contract

### 21.1 Logical package structure

This is a contract, not generated files.

```text
operational_evidence/
  dataset_manifest
  organizations
  submissions
  submission_evidence_families
  assets
  monitoring_coverage
  alerts
  cases
  case_alert_links
  investigations
  escalations
  actions
  resolutions
  closures
  exceptions
  process_changes
  control_process_references      # source-submitted/config-import subset only
  control_process_subject_links   # operational/config links only; finding/sample links are Plane B
  source_file_manifests
  source_record_indexes
  source_specific_exports/     # deliberately varied CSV/JSON layouts

ground_truth_private/
  scenario_manifest
  scenario_record_links
  expected_findings
  generation_audit

evaluation_private/
  split_manifest
  reviewer_sample_manifest
```

The operational package does not contain `scenario_id`, true labels, expected findings, or mutation annotations.

### 21.2 Planning target

**PROJECT DECISION — PLANNING TARGET, NOT REQUIREMENT:**

- 12–20 synthetic organizations;
- at least three peer contexts with approximately five eligible entities where possible;
- 4–6 reporting periods;
- tens of thousands to low hundreds of thousands of alerts for the target benchmark;
- proportional cases, investigations, escalations, actions, assets, and coverage records;
- both complete and deliberately imperfect submissions;
- one smaller deterministic fixture and one larger held-out benchmark.

Exact scale is set only after generation and architecture benchmarks.

### 21.3 Required evidence-family availability

Every target dataset must include Organization, Submission, Source/Provenance, Asset, Alert, Case, Case-Alert Link, and Data-Quality context. Monitoring Coverage, Investigation, Escalation, Action, Resolution, Closure, Exception, and Process Change must be present in enough organizations/periods to exercise the intended analytics. Some deliberate family absences are required, but the manifest must distinguish them from observed zero.

---

## 22. Synthetic Scenario Matrix

Scenario IDs below are design identifiers stored only in private ground truth.

| Scenario ID | Class | Operational evidence pattern | Expected analytical family | Ground-truth category | Important confounder/control |
|---|---|---|---|---|---|
| `NORM-01` | Normal | Ordinary medium alert investigated, resolved, and closed | None | Legitimate | Natural timing variation |
| `NORM-02` | Normal | Critical alert investigated and escalated under applicable rule | None | Legitimate | Different analysts/notes |
| `NORM-03` | Normal | Recurring alert followed by completed remediation | None | Legitimate | Some recurrence after action |
| `NORM-04` | Normal | False-positive alert closed with case-specific evidence | None | Legitimate | Fast but plausible closure |
| `EG-01` | Execution gap | Critical alert closed after grace window with no qualifying investigation, complete source family | Execution gap + negative space | Attention | No approved automation/exception |
| `EG-02` | Execution gap | Applicable serious case lacks required escalation | Execution gap | Attention | Escalation family complete |
| `EG-03` | Execution gap | Investigation timestamp occurs after closure | Cross-record/temporal | Attention or quality | No timezone migration exception |
| `EG-04` | Execution gap | Closed case lacks required disposition/approval evidence | Execution gap | Attention | Rule applicability explicit |
| `EG-05` | Execution gap | Repeated serious alert signature on critical asset without action/remediation evidence | Execution gap + negative space | Attention | Complete action family |
| `NS-01` | Negative space | Active critical asset expected to be covered has no monitoring evidence | Negative space | Attention | Complete inventory/coverage window |
| `NS-02` | Negative space | Alert has no case/investigation evidence | Negative space | Attention | Adequate mature period |
| `NS-03` | Negative space | Applicable case has no escalation evidence | Negative space | Attention | No exception |
| `NS-04` | Negative space | Repeated alert group has no linked remediation or accepted-risk evidence | Negative space | Attention | Stable recurrence key |
| `HIST-01` | Historical | Closure-time distribution shifts sharply faster than eligible own history | Historical deviation | Attention/Review | Similar severity/disposition mix |
| `HIST-02` | Historical | Escalation rate drops materially relative to own comparable history | Historical deviation | Attention/Review | Valid denominator |
| `HIST-03` | Historical | Workload rises unusually with growing backlog | Historical deviation | Attention/Review | Period complete |
| `HIST-04` | Historical | Sudden process shift at undocumented boundary | Historical/change lead | Review | No process-change record |
| `PEER-01` | Peer | Entity rate differs meaningfully in eligible matched cohort | Peer deviation | Review | Cohort quality sufficient |
| `PEER-02` | Peer legitimate | Entity differs due to approved operating model/automation | Peer deviation + counterevidence | Legitimate unusual | Exception/process context present |
| `REP-01` | Repetition | Nearly identical vague notes across diverse cases with little case-specific evidence | Repetitive investigation | Review/Attention | Not linked to approved template |
| `REP-02` | Repetition legitimate | Standard runbook text repeated, but case-specific evidence/conclusions vary | Repetitive investigation | Legitimate unusual | Runbook/template IDs present |
| `XREC-01` | Consistency | Broken source foreign key from case to alert | Cross-record quality | Data quality | Preserve unresolved source ID |
| `XREC-02` | Consistency | Closure before case creation | Cross-record inconsistency | Data quality/Review | No timezone assumption explains it |
| `XREC-03` | Consistency | Case severity unexpectedly conflicts with linked alerts | Cross-record statistical/rule | Review | Include legitimate re-triage controls |
| `XREC-04` | Consistency | Exact duplicate plus conflicting duplicate variant | Duplicate/quality | Data quality | Distinguish exact/conflicting |
| `LEG-01` | Legitimate unusual | Approved automation closes duplicate alert storm quickly | Counterexample | Legitimate unusual | Automation + suppression exception |
| `LEG-02` | Legitimate unusual | Maintenance window suppresses monitoring evidence | Counterexample | Legitimate unusual | Approved maintenance exception |
| `LEG-03` | Legitimate unusual | Emergency workflow changes escalation path temporarily | Counterexample | Legitimate unusual | Emergency exception and effective interval |
| `LEG-04` | Legitimate unusual | New tooling changes status vocabulary and timestamps | Mapping/process change | Legitimate unusual | Process-change boundary and mapping version |
| `LEG-05` | Legitimate unusual | Migration causes late-arriving records and partial period | Quality/context | Legitimate unusual | Submission declared partial |
| `LEG-06` | Legitimate unusual | Accepted-risk decision explains no remediation | Counterexample | Legitimate unusual | Approved, active exception |
| `SUBTLE-01` | Subtle concern | Small group of recurring critical alerts lacks case-specific investigation amid mostly normal operations | Multi-basis | Attention | Low prevalence, no obvious volume spike |
| `OVERLAP-01` | Overlap | Fast closure + repetitive notes + missing escalation share same cases | Multi-basis correlated | Attention | Must produce one correlated package, not triple priority |

### 22.1 Scenario coverage requirement

Every analytical family must have:

- at least one positive scenario;
- at least one ordinary negative case;
- at least one legitimate unusual counterexample;
- at least one incomplete/indeterminate case;
- at least one overlapping/correlated case where applicable.

---

## 23. Hidden Ground-Truth Contract

### 23.1 Scenario ground truth

| Field | Type | Req. | Description |
|---|---|---:|---|
| `scenario_id` | CODE | GT | Stable private scenario identifier |
| `scenario_version` | STRING(32) | GT | Scenario definition version |
| `dataset_version` | STRING(32) | GT | Dataset release |
| `organization_source_id` | SOURCE_ID | GT | Entity in operational package |
| `period_start_at_utc` | TIMESTAMP_UTC | GT | Affected period |
| `period_end_at_utc` | TIMESTAMP_UTC | GT | Affected period |
| `scenario_type` | ENUM | GT | Normal, gap, negative space, history, peer, repetition, inconsistency, legitimate unusual |
| `intended_analytical_family` | ENUM | GT | Expected detector family |
| `true_category` | ENUM | GT | `ATTENTION`, `LEGITIMATE_UNUSUAL`, `NORMAL`, `DATA_QUALITY_ONLY`, `AMBIGUOUS` |
| `expected_finding_category` | ENUM | GT | May be none for normal/control |
| `expected_attention_band_range` | STRING(64) | GT | Optional acceptable range; not detector input |
| `expected_evidence_description` | TEXT | GT | Evidence the evaluator expects |
| `confounding_factors` | JSON_OBJECT | GT | Legitimate alternatives/overlap |
| `mutation_summary` | TEXT | GT | Generator mutation, private |
| `evaluation_notes` | TEXT | GT | Ambiguity and matching rules |

### 23.2 Scenario-record link

Contains `scenario_id`, operational record family, source/canonical synthetic identifier, link role (`AFFECTED`, `SUPPORTING`, `COUNTEREVIDENCE`, `DECOY`, `EXPECTED_BUT_ABSENT`), and expected evidence role. For absent evidence, link to the expected-universe subject and relationship type rather than a nonexistent fake record.

### 23.3 Expected finding

Defines acceptable match keys: organization, period overlap, finding family, affected record set/threshold, expected/forbidden interpretation, and whether multiple planted signals should correlate into one finding.

### 23.4 Ground-truth access control

- Stored in a physically/logically separate private evaluation directory or database.
- Excluded from SAT-SA import package, DuckDB operational database, UI, exports, logs, and feature generation.
- Evaluation occurs only after analytical outputs are sealed.
- Developers may use public training fixtures, but final benchmark seeds/scenarios should be held out where feasible.

---

## 24. Dataset Difficulty and Realism Rules

### 24.1 Required difficulty properties

- overlapping normal and concerning distributions;
- variable organization size, asset mix, alert volume, and operating model;
- source vocabulary/schema differences by organization/system;
- long-tailed durations rather than fixed constants;
- ordinary missingness mixed with meaningful missing evidence;
- exact and conflicting duplicates;
- broken and unresolved links;
- late arrivals and record revisions;
- timezone/precision variation;
- partial and immature periods;
- documented and undocumented process changes;
- legitimate automation/suppression/maintenance/emergency cases;
- low-prevalence subtle cases and high-volume distractors;
- correlated signals that must not be double counted.

### 24.2 Required counterbalances

For every concerning pattern, include a plausible benign version:

- fast closure with approved automation;
- low escalation where escalation is not applicable;
- no monitoring during approved maintenance/decommissioning;
- repeated notes from an approved runbook with case-specific evidence;
- no remediation under active accepted-risk decision;
- late/odd timestamps during documented migration;
- peer difference due to operating model.

For every obvious quality defect, include some operational findings in otherwise high-quality data and some high-quality behavior in poor-quality submissions. This prevents simplistic “bad data equals bad organization” logic.

---

## 25. Data-Generation Rules

These are generator requirements for the next phase, not generated values.

### 25.1 Organization and peer distributions

- Use at least three synthetic sector/context groups with overlap.
- Vary scale, operating model, asset count, severity mix, and source system.
- Do not make all entities in one peer group identical.
- Ensure some entities are intentionally ineligible for specific peer metrics.

### 25.2 Arrival and volume

- Alert arrivals are bursty and time-dependent, not perfectly uniform.
- Include weekday/shift/period effects where appropriate.
- Entity alert volumes differ materially but overlap between size bands.
- Include occasional alert storms with explicit benign/context variants.

### 25.3 Severity and category

- Severity distributions differ by entity and source mapping.
- Critical alerts are a minority but not all problematic.
- Source severities use several vocabularies and mapping versions.
- Category mix changes modestly across periods and may change at tooling boundaries.

### 25.4 Durations and workflow

- Acknowledgement, investigation, escalation, remediation, and closure durations are right-skewed/long-tailed.
- Durations depend imperfectly on severity, disposition, shift, and organization.
- Avoid exact repeated durations except planted automation/template scenarios.
- Open cases legitimately lack end/closure times.
- Timestamps remain logically valid unless the scenario explicitly plants inconsistency.

### 25.5 Relationships

- Some cases group multiple alerts; some alerts remain without cases for legitimate dispositions.
- Investigation, escalation, and action counts vary per case.
- Relationship missingness includes legitimate, incomplete, broken, and concerning cases with distinct ground truth.
- Source foreign IDs and canonical IDs remain separate.

### 25.6 Investigation text

- Use synthetic templates with parameterized case-specific details.
- Vary wording, length, analyst pseudonym, runbook, conclusions, and evidence references.
- Legitimate template cases retain meaningful differences.
- Concerning repetitive cases remove or flatten case-specific content.
- Do not generate real names, addresses, IPs, secrets, or copied operational text.

### 25.7 Missingness and quality

- Missingness is not uniformly random; source-system/version and submission quality influence it.
- Explicit zero, omitted field, invalid value, not-applicable, and no related record must be generated separately.
- Duplicate submissions and corrected submissions use provenance/supersession, not destructive replacement.

### 25.8 Reproducibility and independence

- Generator version and seed are recorded privately.
- Base behavior generation and scenario mutation are separately versioned.
- Detector rule thresholds are not used verbatim to generate all positives.
- Held-out scenario parameters/seeds are not tuned against the detector.

---

## 26. Benchmark Volume Tiers

All tiers are planning envelopes, not SIH requirements or performance claims. File sizes depend heavily on text and serialization.

| Tier | Organizations | Periods | Alerts | Cases | Investigations | Assets | Approx. serialized size | Purpose |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Deterministic fixture | 2–3 | 2 | 500–2,000 | 100–500 | 150–800 | 50–250 | < 25 MB | Unit/integration/golden tests |
| Small | 4–6 | 3 | 5,000–15,000 | 1,000–4,000 | 1,500–6,000 | 500–1,500 | 25–250 MB | Developer iteration and demo rehearsal |
| Medium / target | 12–16 | 4–6 | 50,000–150,000 | 10,000–40,000 | 15,000–60,000 | 3,000–10,000 | 0.25–2 GB | MVP benchmark and peer/history evaluation |
| Large / stress | 20 | 6 | 250,000–750,000 | 50,000–200,000 | 80,000–300,000 | 10,000–30,000 | 1–8 GB | Scaling/memory limit exploration |

Actions, escalations, resolutions, closures, coverage, exceptions, source records, and provenance scale proportionally and must be counted in total-record benchmarks.

### 26.1 Later measurement protocol

For each tier record import, validation, normalization, per-module analysis, finding correlation, and report times; peak memory; disk size; UI query latency; hardware/runtime; dataset seed/version; and output correctness. Do not publish capacity claims before measurement.

---

## 27. Schema-Level Validation Test Catalogue

| Test ID | Condition | Expected schema/quality outcome |
|---|---|---|
| `VAL-001` | Missing required canonical field | Record invalid; field state `NOT_PROVIDED`; dependent analytics blocked |
| `VAL-002` | Invalid timestamp lexical value | Field state `INVALID`; original retained; temporal metric blocked |
| `VAL-003` | Duplicate source ID with identical content | `DUPLICATE_EXACT`; no double counting |
| `VAL-004` | Duplicate source ID with conflicting content | `DUPLICATE_CONFLICTING`; preserve both source records; unresolved revision |
| `VAL-005` | Broken alert/case foreign key | Relationship state/quality `BROKEN_RELATIONSHIP`; source ID retained |
| `VAL-006` | Wrong numeric/boolean data type | `INVALID`; no coercion unless mapping explicitly defines it |
| `VAL-007` | Unknown vocabulary value | Canonical `UNKNOWN`, raw retained, mapping warning |
| `VAL-008` | Negative source duration | Preserve source field as invalid; never use as canonical duration |
| `VAL-009` | Closure before creation | Cross-record temporal inconsistency; no timestamp rewriting |
| `VAL-010` | Investigation after closure | Valid records plus inconsistency candidate; exception/process context evaluated |
| `VAL-011` | Reporting end ≤ start | Submission rejected/invalid period |
| `VAL-012` | Exact duplicate submission hash | Mark possible duplicate; require explicit acceptance/supersession |
| `VAL-013` | Missing investigation evidence family | Family `NOT_PROVIDED`; no alert-level `NO_SUBMITTED_EVIDENCE` operational claim |
| `VAL-014` | Provided investigation file has zero records | `PROVIDED` + observed count zero; distinct from absent file |
| `VAL-015` | Schema profile/version mismatch | `SCHEMA_MISMATCH`; parser/mapping halted or conditional |
| `VAL-016` | Timestamp has no timezone and no mapping assumption | `INVALID`/`UNKNOWN`; no UTC instant |
| `VAL-017` | Timestamp normalized by declared default timezone | Valid with warning and mapping provenance |
| `VAL-018` | Asset coverage absent in complete coverage family | Relationship state `NO_SUBMITTED_EVIDENCE`; negative-space eligibility depends on expectation |
| `VAL-019` | Asset coverage absent because family omitted | `NOT_PROVIDED`; data-quality finding only |
| `VAL-020` | Rule marked not applicable by active exception | Exclude expected-universe member; no operational finding |
| `VAL-021` | Exception expired before event | Exception not applicable; preserve reference/context |
| `VAL-022` | Late-arriving case update | New source/canonical revision; prior run remains reproducible |
| `VAL-023` | Source record maps to resolution and closure | Two canonical records share provenance; no duplicate source claim |
| `VAL-024` | Ground-truth field appears in operational package | Package/evaluation integrity failure; reject benchmark |
| `VAL-025` | Source field contains spreadsheet formula prefix | Preserve safely; neutralize only on spreadsheet export |
| `VAL-026` | Excessive note/field length | Intake validation according to bounded limit; no resource exhaustion |
| `VAL-027` | Peer cohort below configured minimum | `INSUFFICIENT_PEERS`; no global fallback |
| `VAL-028` | Historical observations below minimum | `INSUFFICIENT_HISTORY`; no universal threshold |
| `VAL-029` | Conflicting case and closure dispositions | Preserve both; cross-record inconsistency/context candidate |
| `VAL-030` | Alert has explicit occurrence count 0 where minimum is 1 | `INVALID`, not `OBSERVED_ZERO` |

Each active field/rule later requires positive, negative, boundary, invalid, missing, and legitimate-exception tests.

---

## 28. Privacy and Safety Contract

The synthetic dataset must contain:

- no real organization/CSE names;
- no real employee or analyst names;
- no real customer information;
- no real credentials, keys, tokens, passwords, or secrets;
- no copied incident narratives;
- no real IP addresses unless a reserved documentation range is truly required; synthetic asset IDs are preferred;
- no real hostnames, domains, ticket IDs, or infrastructure paths;
- no classified or sensitive operational data.

Use clearly synthetic identifiers such as `CSE-007`, `AST-007-0042`, `ALT-007-P03-001245`, and pseudonyms that cannot be mistaken for real people. Free text must be generated from original synthetic templates and must not contain executable markup.

**PROJECT DECISION:** The dataset may model sensitivity and provenance behavior without containing genuinely sensitive information.

---

## 29. Schema, Mapping, Dataset, Scenario, and Generator Versioning

### 29.1 Version identifiers

| Artifact | Required version fields | Change rule |
|---|---|---|
| Canonical schema | `schema_version`, schema checksum | Major for incompatible semantics; minor for backward-compatible additions; patch for clarifications |
| Source schema profile | `schema_profile_id`, version, checksum, effective period | New version for field/layout semantics change |
| Mapping | `mapping_version_id`, semantic version, checksum, source-system scope, effective period | Immutable once used by sealed run |
| Vocabulary | vocabulary name/version/checksum | New version for mappings/allowed values change |
| Dataset | `dataset_version`, manifest checksum | New version for any operational evidence content change |
| Scenario | `scenario_version`, definition checksum | New version for mutation/label/matching change |
| Generator | `generator_version`, build checksum, seed | New version for behavior-generation logic change |
| Ground truth | ground-truth manifest version/checksum | Coupled to exact dataset/scenario versions |

### 29.2 Compatibility

A dataset manifest declares the canonical target schema and source profile versions. An analytical run freezes exact versions. A later schema change never mutates an old normalized dataset/run silently; it creates a migration/new normalization run with a new version.

### 29.3 Minimum dataset manifest metadata

- dataset ID/version and created time;
- generator/scenario versions and public seed identifier where allowed;
- operational package hash;
- schema/profile/mapping versions;
- organization/period/family counts;
- benchmark tier;
- privacy/synthetic declaration;
- ground-truth manifest hash stored privately, not embedded in operational package;
- known limitations and intended split.

---

## 30. What Is Defined Now and What Is Deferred

### 30.1 Defined now

- three-plane data separation;
- logical types and naming conventions;
- canonical record envelope;
- non-collapsible missing states;
- organization, submission, source/provenance, asset, monitoring, alert, case/link, investigation, escalation, action, resolution, closure, exception, and process-change fields;
- control/process references and subject links;
- identifiers, cardinalities, and legitimate missing relationships;
- field/record/family/submission/period/finding quality metadata;
- temporal semantics and controlled vocabularies;
- derived analytical/finding/evidence contracts;
- structured review/disposition, review sample/member, and audit-event contracts;
- hidden ground-truth schema and access boundary;
- scenario coverage, difficulty, generation rules, benchmark tiers, validation tests, privacy, and versioning.

### 30.2 Deliberately deferred

- physical DuckDB table definitions and storage layout;
- SQL DDL, indexes, constraints, views, and migrations;
- actual CSV/JSON filenames and generated content;
- source adapters and mapping files;
- synthetic generator implementation and final distributions;
- exact data volumes after benchmarking;
- final thresholds, grace periods, statistical parameters, minimum samples/peers, and priority policy values;
- final finding/rule catalogue;
- final ML/text feature list and model decision;
- backend/frontend/test implementation;
- production retention, encryption, identity, and access-control policies.

---

## 31. Open Questions Before Dataset Generation

1. Which 12–20 synthetic organizations, sector groups, scale bands, and operating models will form the first target dataset?
2. Which four to six reporting-period durations will be used, and what maturation delay applies?
3. What source schema variations will each synthetic organization export?
4. Which canonical fields are required in the first generator release versus later optional families?
5. Which demo rule expectations and applicability policies will be represented, and how are they labeled as project assumptions?
6. What minimum sample/cohort values will be used provisionally for generation—not final analytics?
7. What final safe length limits apply to identifiers, notes, JSON metadata, and files?
8. How many normal, attention, legitimate-unusual, ambiguous, and quality-only scenarios are required per family?
9. Which scenarios/seeds are hidden from detector developers for final evaluation?
10. Who owns the private ground truth and controls access during validation?
11. How will synthetic review/manual-assessment samples be selected and blinded?
12. Which exact medium-tier volume is feasible on target hardware?
13. Should the MVP operational package expose canonical-form CSV/JSON in addition to varied source exports, or require ingestion mappings for all evidence?
14. Which sector vocabulary should use generic synthetic labels versus realistic but non-identifying sector names?
15. What constitutes acceptable ambiguity in expected-finding matching for evaluation?

---

## 32. Final Consistency Check

| Check | Result | Schema support |
|---|---|---|
| `PROJECT_SPEC.md` evidence/finding concepts | **YES** | Submitted families, derived findings, evidence links, review data |
| Execution gaps | **YES** | Explicit workflow records, rules/applicability, relationships, timing |
| Negative space | **YES** | expected universe, family completeness, relationship observations, exceptions |
| Historical baselines | **YES** | multi-period profiles, process boundaries, baseline summaries |
| Peer comparison | **YES** | peer attributes, denominators, cohort summaries, insufficient-peer state |
| Optional anomalies | **YES** | versioned derived metrics/model output without truth labels |
| Cross-record checks | **YES** | typed IDs, links, timestamps, revisions, quality issues |
| Repetitive investigations | **YES** | notes, templates/runbooks, pseudonyms, text feature versioning |
| Evidence traceability | **YES** | field → record → file → submission → manifest/hash |
| Manual validation | **YES** | review/disposition plus private expected findings |
| Control/process prioritization | **YES** | versioned Control/Process Reference and typed Subject Link |
| Alert/case/source review samples | **YES** | structured Review Sample and Review Sample Member contracts |
| Review and auditability | **YES** | structured Review/Disposition plus append-only logical Audit Event |
| Architecture canonical layer | **YES** | source preservation, versioned mapping, canonical envelope |
| Source-ID optionality | **YES** | SAT-SA UUID is authoritative; source-provided IDs are optional and scoped when present |
| Non-collapsible missing states | **YES** | field and relationship observations distinguish all seven states |
| Structured array typing | **YES** | list-valued fields use bounded `JSON_ARRAY<T>` rather than `JSON_OBJECT` |
| Temporal reconstruction | **YES** | event/update/ingestion/effective/reporting times and revisions |
| Legitimate unusual cases | **YES** | exceptions, process changes, counter-scenarios |
| Ground-truth isolation | **YES** | private store excluded from detector/application database/UI |
| Multi-entity/multi-period scale | **YES** | organization/submission/period keys and benchmark tiers |
| Student implementability | **YES, subject to review** | Manageable normalized families; complex generic provenance limited to two companion tables |
| Scope control | **YES** | No real-time telemetry, packets, EDR, response actuation, or threat-feed schema |

### 32.1 Review focus

Reviewers should specifically approve or change:

- the field-level observation approach for missing semantics/provenance;
- required versus optional fields per family;
- separate Resolution and Closure families;
- polymorphic Exception target contract;
- organization/peer attributes;
- target benchmark tiers;
- scenario matrix and legitimate-control coverage;
- ground-truth physical/logical separation;
- whether this logical model remains feasible for the planned DuckDB implementation.

---

## PHASE 3 DATA SCHEMA STATUS

**READY FOR DATASET GENERATION REVIEW**
