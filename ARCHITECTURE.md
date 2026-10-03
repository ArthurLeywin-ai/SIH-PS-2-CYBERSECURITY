# ARCHITECTURE.md

## SAT-SA — Supervisory Analytics Tool for SOC Assessment

| Field | Value |
|---|---|
| SIH problem statement | SIH 2026 — SIH26157 |
| Architecture phase | Phase 2 |
| Inputs | `PROJECT_SPEC.md`, `RESEARCH_REPORT.md` |
| Document purpose | Concrete, implementable technical architecture for the SAT-SA MVP |
| Status | Architecture proposal awaiting project-owner review |
| Scope boundary | Architecture only; no implementation, detailed physical schema, or final analytical thresholds |

> **Required product chain:** **Finding → Why → Basis → Calculation → Evidence → Source Record → Investigation Question**
>
> **Human-control principle:** SAT-SA prioritizes evidence for supervisory review. It does not determine honesty, certify compliance, or replace examiner judgment.

### Decision-label convention

- **FACT** — directly established by the approved source documents.
- **RESEARCH FINDING** — conclusion approved in `RESEARCH_REPORT.md`.
- **PROJECT DECISION** — concrete Phase 2 architecture decision.
- **ASSUMPTION** — condition used to make the architecture implementable but requiring confirmation.
- **OPEN QUESTION** — unresolved issue that must remain visible.

---

## 1. Architecture Goal

### 1.1 Plain-language goal

SAT-SA must turn structured, periodic SOC operational evidence from multiple Critical Sector Entities (CSEs) and reporting periods into a prioritized, evidence-backed review queue for a supervisory examiner.

- **Primary user:** supervisory examiner.
- **Inputs:** initially CSV and JSON evidence packages containing alert, case, investigation, escalation, closure, asset, monitoring, and related operational records where available.
- **Outputs:** validation results, data-quality status, transparent findings, linked source evidence, entity/control/process/sample review queues, investigation questions, examiner dispositions, and offline reports.
- **Human control:** the examiner decides whether a finding is relevant, requires follow-up, is explained, or is dismissed. The examiner may override queue priority with a recorded reason.
- **Technical objective:** every material output must be reproducible from a preserved source submission, versioned mappings, configurations, rules/models, and analysis run.

### 1.2 Explicit non-goals

**FACT:** The product is not a SOC, SIEM, real-time monitoring system, centralized SOC, EDR, threat-hunting platform, automated response platform, counterattack system, national cyber-monitoring platform, forensic reconstruction system, compliance certifier, or autonomous decision-maker.

**PROJECT DECISION:** The architecture has no streaming collection path, agent deployment, live telemetry connector, response actuator, or outbound cloud/AI dependency. Future database-export adapters remain batch-oriented.

### 1.3 Architectural quality priorities

In descending order:

1. evidence integrity and traceability;
2. safe interpretation of missing/incomplete data;
3. explainability and human control;
4. reproducibility and auditability;
5. offline reliability;
6. correctness and testability;
7. development and demonstration feasibility;
8. performance at the prototype benchmark scale;
9. replaceable analytics and maintainability.

---

## 2. System Context and Trust Boundaries

### 2.1 Actors

| Actor | Responsibilities | Prohibited authority |
|---|---|---|
| Examiner | Imports submissions, runs analysis, reviews evidence, records dispositions, exports reports | Cannot silently change source evidence or analytical history |
| Local administrator | Installs/updates approved bundle, manages local configuration/identity, verifies integrity | Does not alter findings without an auditable analytical rerun |
| Mapping/rule maintainer | Defines versioned source mappings and analytical expectations | Cannot activate unreviewed changes silently |
| Analytical module | Produces candidate findings and supporting metadata | Cannot issue supervisory judgment or directly assign final disposition |
| Optional ML module | Produces supporting anomaly leads | Cannot replace deterministic findings, update itself, or claim wrongdoing probability |

### 2.2 Trust zones

1. **Untrusted intake zone** — newly received files; never queried directly by analytics.
2. **Preserved source zone** — immutable-by-application copies plus hashes and manifests.
3. **Validated evidence zone** — parsed records with validation outcomes; invalid rows isolated.
4. **Canonical analytical zone** — normalized evidence, provenance links, quality state, derived features.
5. **Finding and review zone** — findings, evidence links, priority factors, examiner actions, reports.
6. **Controlled configuration zone** — mappings, schemas, rules, cohort definitions, models, and version manifests.

Data may move inward only through explicit validation gates. Reports may leave through an examiner-triggered export path. No analytical module may modify preserved source artifacts.

### 2.3 Deployment assumption

**ASSUMPTION:** The hackathon MVP runs as a single local application on one controlled workstation for one active examiner at a time. It binds only to the loopback interface. This minimizes operational complexity and fits an air-gapped demonstration.

**OPEN QUESTION:** A production deployment may require concurrent users, enterprise identity integration, network-segmented multi-user access, formal retention controls, or a different approved runtime. Those requirements are not publicly specified and must not be invented.

---

## 3. Complete Component Architecture

### 3.1 Component view

```text
OFFLINE USER / EXAMINER
        |
        v
LOCAL WEB UI  <------------------------------->  REPORT / EXPORT SERVICE
        |                                                   |
        v                                                   v
APPLICATION API / ORCHESTRATOR --------------------> REVIEW & AUDIT SERVICE
        |
        +--> INGESTION & QUARANTINE
        |        |
        |        v
        |    VALIDATION & DATA QUALITY
        |        |
        |        v
        |    NORMALIZATION & MAPPING
        |        |
        |        v
        |    CANONICAL EVIDENCE + PROVENANCE
        |
        +--> ANALYTICAL RUN ORCHESTRATOR
                 |
                 +--> EXPECTATION / RULE REGISTRY
                 +--> EXECUTION-GAP MODULE
                 +--> NEGATIVE-SPACE MODULE
                 +--> CROSS-RECORD CONSISTENCY MODULE
                 +--> HISTORICAL BASELINE MODULE
                 +--> PEER COMPARISON MODULE
                 +--> REPETITIVE-INVESTIGATION MODULE
                 +--> OPTIONAL ANOMALY MODULE
                 |
                 v
          CANDIDATE FINDINGS
                 |
                 v
          EVIDENCE CORRELATION & VALIDATION
                 |
                 v
          EXPLANATION BUILDER
                 |
                 v
          PRIORITIZATION ENGINE
                 |
                 v
          EXAMINER QUEUE / FINDING PACKAGE

LOCAL STORAGE BOUNDARY
  - Preserved source files
  - DuckDB analytical/application database
  - Versioned mappings, rules, models, and configuration
  - Local reports and integrity manifests
  - Append-only logical audit events
```

### 3.2 Component responsibility matrix

| Component | Receives | Produces | Must not do |
|---|---|---|---|
| Local Web UI | API views and examiner actions | Validated commands, review state, exports | Read source filesystem directly; compute authoritative findings |
| Application API / Orchestrator | UI commands and internal job requests | Authorized workflows and stable view models | Contain hidden analytical logic |
| Ingestion & Quarantine | Selected local files/directories | Submission, manifest, preserved copy, hashes, intake status | Trust extension/MIME alone; execute file content |
| Validation & Data Quality | Preserved source and mapping candidate | File/row/field/relationship quality results | Convert absence into operational failure |
| Normalization & Mapping | Valid parsed records and mapping version | Canonical records with source lineage | Overwrite original values |
| Evidence & Provenance | Source, normalized records, versions, run events | Traceable evidence graph/references | Claim source authenticity beyond received-artifact integrity |
| Analytical Run Orchestrator | Run request, eligible evidence, frozen configuration snapshot | Module execution plan and run state | Allow configuration/model mutation during a run |
| Analytics Modules | Read-only canonical evidence and run context | Candidate finding packages | Set examiner disposition; mutate evidence |
| Evidence Correlation & Validation | Candidate findings and evidence refs | Merged/de-duplicated validated candidates | Merge merely because titles are similar |
| Explanation Builder | Valid candidate, method-specific context | Plain-language and technical explanation fields | Invent evidence or remove uncertainty |
| Prioritization Engine | Findings, quality/confidence, factors | Attention band, queue order, explanation | Produce hidden 0–100 “truth” score |
| Review & Audit Service | Examiner actions and system lifecycle events | Dispositions, overrides, append-only logical event history | Rewrite prior events |
| Report / Export Service | Selected findings, evidence and review state | Offline report package and export manifest | Fetch external resources or expose unrelated sensitive data |
| Configuration Registry | Approved schemas/mappings/rules/cohorts/models | Immutable version snapshots | Activate unreviewed replacement automatically |

---

## 4. Data Ingestion Layer

### 4.1 Intake package

**PROJECT DECISION:** MVP ingestion accepts individual CSV/JSON files or a controlled directory/package containing them. ZIP support is **Should-have** and, if implemented, must remain in quarantine until archive checks pass. Database exports are future adapters feeding the same submission contract.

Each submission records:

- submission ID and entity identifier claimed by the package;
- reporting period and export time, if supplied;
- discovered files and detected format;
- byte size, cryptographic hash, and import timestamp;
- operator/importing account;
- parser and schema-profile candidates;
- source-system metadata where supplied;
- package-level completeness declarations where supplied;
- original filename stored as metadata, never trusted as a filesystem path.

### 4.2 Intake sequence

1. Discover selected files without recursive escape outside the chosen root.
2. Enforce count, individual-size, total-size, and archive-expansion limits.
3. Inspect extension, media signature where meaningful, encoding, and basic structure.
4. Copy the exact received bytes into the preserved source zone under a generated internal identifier.
5. Compute and record a SHA-256 hash.
6. Create an immutable submission manifest version.
7. Select a mapping/schema profile or request explicit examiner selection.
8. Parse into staging under resource limits.
9. Send parsed records and parser diagnostics to validation.

### 4.3 Source preservation

The application never edits the preserved source copy. Corrections are represented as:

- a new submission;
- a new mapping version; or
- a new normalization/analysis run.

A hash demonstrates that SAT-SA’s preserved copy has not changed since import. It does not prove that the source organization’s data was truthful or complete before submission.

### 4.4 Failure behavior

- Unknown or dangerous format: reject before parsing and retain only an intake event unless policy permits quarantine retention.
- Corrupt file: quarantine, report exact failure, do not partially normalize without explicit recoverable-row policy.
- Partial multi-file package: allow quality assessment but block rules requiring missing evidence families unless configured to emit a data-quality finding.
- Parser crash: isolate the job, record sanitized diagnostics, preserve prior system state, and leave submission unaccepted.
- Duplicate file hash: label as possible repeat; do not double-count unless examiner creates a distinct accepted submission with justification.

---

## 5. Validation and Data-Quality Layer

### 5.1 Validation levels

| Level | Checks | Outcome |
|---|---|---|
| File | readable, allowed format, encoding, structural validity, size limits | accept, quarantine, reject |
| Schema | expected tables/record types, columns, data types, allowed cardinality | mapping-ready, conditional, incompatible |
| Field | required values, identifier format, timestamp parse, vocabulary mapping | valid, warning, invalid |
| Record | logical consistency, duplicate key, internal time order | accepted, accepted-with-warning, isolated |
| Relationship | referenced parent/asset/entity exists or is explicitly external | linked, broken, unresolved |
| Period | start/end coverage, maturity/grace period, late-arriving status | complete, partial, immature, unknown |
| Submission | declared vs observed files/counts, entity consistency, hash manifest | usable, conditionally usable, blocked |

### 5.2 Non-collapsible evidence states

**PROJECT DECISION:** Every field/evidence expectation capable of being absent carries a state distinct from its value.

| State | Meaning | Example | Analytical treatment |
|---|---|---|---|
| `OBSERVED_VALUE` | Valid submitted value exists | escalation count = 0 | May be used as zero/value |
| `OBSERVED_ZERO` | Explicit valid zero | “0 escalations” in complete period | Use as zero with provenance |
| `NOT_PROVIDED` | Field/source expected by mapping but omitted | escalation column absent | Quality limitation; not zero |
| `NOT_APPLICABLE` | Expectation does not apply | no escalation required by configured rule | Exclude from denominator |
| `INVALID` | Submitted value cannot be interpreted | malformed timestamp | Block dependent calculation |
| `NO_SUBMITTED_EVIDENCE` | Searchable expected evidence family present, but matching record not found | no case linked to alert | Candidate negative space, subject to completeness |
| `UNKNOWN` | System cannot determine state | source scope not declared | Indeterminate; no operational conclusion |

These conceptual states will later receive precise schema representation. They must never be reduced to one database null.

### 5.3 Quality classification

Quality is reported at field, record, evidence-family, period, submission, and finding levels. The architecture uses a small ordinal vocabulary rather than a pseudo-precise quality score:

- **Sufficient** — required inputs valid and coverage conditions met.
- **Sufficient with limitations** — analysis allowed; limitations must be shown.
- **Insufficient** — dependent finding cannot be asserted.
- **Indeterminate** — scope or semantics cannot be established.

### 5.4 Quality gates

- Deterministic checks may run only when their required fields and semantics are eligible.
- Historical/peer modules require metric-specific eligibility.
- Negative-space analysis requires an expected universe and observation-completeness status.
- Invalid timestamps cannot contribute to duration calculations.
- Broken relations may produce a consistency finding, but the same broken link cannot independently be treated as proof of an operational gap without qualification.

---

## 6. Normalization and Canonical Evidence Layer

### 6.1 Mapping strategy

**PROJECT DECISION:** Source-specific adapters produce a common canonical evidence representation through versioned declarative mappings plus small, testable transformation functions. Each organization may have a different mapping profile. No source is forced to use another organization’s vocabulary.

A mapping version defines:

- source record family and file/table selector;
- source column/path to canonical field mapping;
- type and timestamp transformations;
- timezone assumptions;
- identifier construction and namespace;
- vocabulary crosswalks for severity/status/disposition;
- relationship key mapping;
- missing-state interpretation;
- effective period and source-system version;
- validation rules and known limitations.

### 6.2 Preservation requirements

For every canonical field or relationship, retain:

- canonical record ID;
- source submission and file ID;
- source record ID or deterministic row locator;
- original source field/path;
- original lexical value;
- normalized value and unit;
- mapping version and transform identifier;
- ingestion run and normalization timestamp;
- quality status and diagnostics.

### 6.3 Canonical evidence families

The conceptual families are Organization, Asset, Alert, Case/Incident, Investigation Activity, Escalation, Action/Remediation, Resolution, Closure, Monitoring Coverage, Exception/Applicability, Submission, and Source Record.

**PROJECT DECISION:** The canonical layer represents events and current attributes separately where source data supports both. A status snapshot must not be misinterpreted as a complete event history.

### 6.4 Identity and relationship resolution

- IDs are namespaced by organization, source system, and record family.
- Source aliases may map to a canonical asset/entity through a versioned resolution record.
- Ambiguous resolution remains unresolved; it is never guessed.
- Many alerts may link to one case; a case may link to many alerts and activities.
- Missing links remain explicit and traceable to the source state.

---

## 7. Evidence and Provenance Layer

### 7.1 Provenance chain

Every finding maintains the following navigable chain:

```text
Finding
  -> Why flagged
  -> Analytical basis/bases
  -> Calculation and context
  -> Evidence references
  -> Canonical record/relationship
  -> Original field/value
  -> Source record locator
  -> Preserved source file
  -> Submission manifest and hash
```

### 7.2 Provenance objects

The architecture requires conceptual records for:

- source artifact and hash;
- submission/import event;
- parser/schema/mapping version;
- normalized record and original-value link;
- analytical run and frozen configuration snapshot;
- rule/model/feature version;
- baseline and peer-cohort membership snapshot;
- candidate and final finding revision;
- evidence link with role and relevance;
- examiner review/audit event;
- report/export manifest.

### 7.3 Evidence roles

Evidence links identify why each record is included:

- **Trigger** — record that caused a candidate detection.
- **Supporting** — corroborating record/statistic.
- **Expected-but-missing reference** — expected universe member and search scope, not a fabricated absent record.
- **Counterevidence/exception** — context reducing or explaining concern.
- **Baseline member** — historical observation used in reference distribution.
- **Peer member** — peer observation/cohort membership used in comparison.
- **Quality limitation** — invalid/missing source condition affecting confidence.

### 7.4 Reproducibility

A run is reproducible only if source hashes, canonical mapping version, rule/model/feature versions, configuration snapshot, cohort/baseline membership, and random seed are available. Re-running creates a new run and finding revision; it does not overwrite the prior result.

---

## 8. Analytics Engine

### 8.1 Analytical run orchestration

**PROJECT DECISION:** Analytics operate as a batch run over an immutable run snapshot. The orchestrator:

1. freezes eligible submissions and periods;
2. freezes mapping/schema/rule/config/model versions;
3. computes the quality/eligibility matrix;
4. executes deterministic consistency checks first;
5. executes execution-gap and negative-space rules;
6. computes historical baselines and peer cohorts;
7. executes statistical and text modules;
8. optionally executes a validated anomaly model;
9. collects candidates through a common module contract;
10. performs evidence validation, correlation, explanation, and prioritization;
11. seals the run manifest.

A module failure is isolated; the run may finish as **Completed with module failures** if unaffected outputs remain valid. The UI and report must list omitted modules.

### 8.2 Module inventory

| Module | Type | Primary purpose | Output language |
|---|---|---|---|
| Cross-record consistency | Deterministic | Broken relationships, impossible times, contradictions, duplicates | “Submitted records are inconsistent…” |
| Execution-gap | Deterministic, sometimes statistical threshold | Expected workflow differs from observed evidence | “Observed workflow did not contain expected step…” |
| Negative-space | Deterministic expectation + completeness reasoning | Expected evidence not found in submitted scope | Required cautious wording |
| Historical baseline | Statistical | Current behavior differs from comparable own history | “Current period deviates from eligible historical baseline…” |
| Peer comparison | Statistical | Entity differs from matched cohort | “Entity differs from peers; context is required…” |
| Repetitive investigation | Deterministic and statistical text similarity | Exact/near-duplicate notes or sequences | “Possible template-driven pattern…” |
| Optional anomaly | ML-based supporting detector | Multivariate unusual entity-period/case pattern | “Model-generated anomaly lead; not proof/probability…” |

### 8.3 Deterministic-first rule

**RESEARCH FINDING:** Deterministic rules and robust statistics provide stronger traceability than opaque ML for the MVP.

**PROJECT DECISION:** No ML output can bypass evidence validation, directly assign final attention priority, or suppress a deterministic finding. The system remains functionally useful when the ML module is disabled or absent.

---

## 9. Expectation and Rule Registry

### 9.1 Purpose

The registry stores versioned analytical expectations without claiming they are universal or officially mandated. Expectations may be project demo rules, source-backed generic expectations, or later organization-specific policies.

### 9.2 Rule contract

Each versioned rule defines:

- rule ID, name, category, owner, and status;
- expectation statement and neutral finding template;
- source/reference and authority type;
- applicability conditions and eligible record families;
- required evidence and required quality state;
- expected relationship/action;
- observation/maturation/grace period;
- exclusions, approved exception types, and denominator logic;
- threshold/configuration parameters;
- incomplete-input behavior: block, lower confidence, or data-quality-only finding;
- evidence roles to capture;
- calculation/explanation template;
- investigation-question template;
- version, effective start/end period, approval state, and checksum;
- tests/validation status.

### 9.3 Lifecycle

`Draft → Reviewed → Active → Superseded/Retired`

Only Active rules may generate queueable findings. Changing a rule creates a new immutable version. Historical runs retain the version used.

### 9.4 No invented policy

**PROJECT DECISION:** Prototype expectations are clearly labeled “demo analytical expectations” unless backed by an authoritative source. A configured severity-to-escalation expectation must not be presented as NCIIPC policy without evidence.

---

## 10. Historical Baseline Engine

### 10.1 Inputs

- entity and metric definition/version;
- current period and eligible historical periods;
- comparable population filters (severity, disposition, asset class, workflow version);
- data-quality and process-change metadata;
- baseline configuration version.

### 10.2 Eligibility gate

A baseline is eligible only when:

- metric semantics are consistent;
- required source families and timestamps are sufficient;
- periods are mature and comparable;
- no unhandled process/source-system boundary spans the window;
- configured minimum observation and period counts are met;
- denominator is valid for rate metrics.

Otherwise the engine returns `INSUFFICIENT_HISTORY` with reasons. It never substitutes a peer baseline silently.

### 10.3 Statistical outputs

Where eligible, produce:

- sample/period counts;
- median and configured percentiles;
- IQR and/or MAD;
- current value/rate;
- robust deviation/effect magnitude;
- baseline window and filters;
- excluded observations and reasons;
- optional rolling/stratified context;
- distribution summary for explanation.

Mean/standard deviation may be supplementary where assumptions are supported. Universal thresholds are not embedded in code; the configuration and validation artifact own them.

### 10.4 Process-change boundaries

Mappings, workflow revisions, automation deployment, source migrations, or approved policy changes can create a boundary. The engine either:

- restricts the baseline to one regime;
- stratifies by regime; or
- declares it ineligible.

---

## 11. Peer Comparison Engine

### 11.1 Cohort creation

A versioned cohort definition specifies candidate filters such as sector/subsector, period duration, metric semantics, monitored-asset scale band, alert-volume band, operational model, asset criticality mix, and source completeness.

Cohort creation has two stages:

1. **Eligibility:** remove entities with incompatible definitions, periods, denominators, or insufficient quality.
2. **Metric comparison:** compute normalized entity and peer values using the same metric version.

### 11.2 Outputs

- cohort ID/version and rationale;
- eligible and excluded entity counts with reasons;
- anonymized or authorized member references;
- current entity value and denominator;
- peer median, percentiles, IQR/MAD where eligible;
- percentile/robust deviation as configured;
- period and metric version;
- quality comparability warnings;
- state: `ELIGIBLE`, `INSUFFICIENT_PEERS`, `INCOMPARABLE`, or `INDETERMINATE`.

### 11.3 Guardrails

- No silent fallback to all entities.
- Minimum cohort size is metric configuration, not a universal constant.
- Absolute counts are not compared when exposure differs; use defensible rates.
- Cohort membership is snapshotted per run.
- A peer deviation is context, not evidence of wrongdoing or poor performance.
- Peer results may strengthen attention only when evidence confidence is sufficient.

---

## 12. Negative-Space Engine

### 12.1 Four-question evaluation

For every possible negative-space candidate, the engine resolves:

1. **Expected universe:** Which assets, alerts, cases, controls, or periods are in scope?
2. **Expectation basis:** Why should matching evidence exist—rule, declared coverage, workflow, or schedule?
3. **Observation adequacy:** Is the submitted source family and time window complete/mature enough?
4. **Evidence search:** Was qualifying evidence found, absent, invalid, external, or excepted?

### 12.2 Output states

| State | Meaning | Queue behavior |
|---|---|---|
| Evidence found | Expectation satisfied in submitted scope | No negative-space finding |
| Expected evidence not found | Eligible universe and adequate observation; no qualifying evidence/exception | Candidate finding |
| Exception found | Approved applicable exception explains absence | Suppress or retain as context per rule |
| Insufficient observation | Missing/partial source or immature period | Data-quality item; no operational assertion |
| Not applicable | Rule applicability false | Exclude |
| Indeterminate | Scope/semantics cannot be established | Non-queueable analytical limitation |

### 12.3 Required phrasing

Generated explanation must be equivalent to:

> “Expected evidence was not found in the submitted scope for the specified period and sources.”

It must identify the searched sources, expected universe, rule, period, grace window, and alternative explanations. It must not say the organization failed to perform the action.

---

## 13. Repetitive-Investigation Module

### 13.1 MVP approach

1. preserve original notes;
2. produce a versioned normalized-text representation;
3. find exact normalized duplicates;
4. compute TF-IDF cosine similarity within comparable case groups;
5. identify repeated action/disposition sequences;
6. retain representative examples and differing terms;
7. combine with handling time, case diversity, and missing case-specific evidence only as separate visible bases.

### 13.2 Guardrails

- Approved templates/runbooks and automated enrichment are counterevidence.
- Similarity alone yields a supporting candidate, not an adverse conclusion.
- Notes are sensitive and are not copied into routine logs.
- Similarity thresholds and text preprocessing are feature-versioned.
- An embedding model is deferred unless later evaluation proves incremental value.

---

## 14. Optional Anomaly / ML Layer

### 14.1 Position in the architecture

ML runs after canonicalization, quality gating, and baseline feature construction. It outputs supporting anomaly candidates into the same evidence-validation path as every other module.

### 14.2 Candidate MVP detector

**PROJECT DECISION:** The architecture provides a replaceable anomaly-module slot. Isolation Forest is the first candidate for evaluation, not a mandatory shipped feature.

### 14.3 Input and output contract

Inputs:

- versioned entity-period or case-level feature matrix;
- eligibility mask and quality metadata;
- fit/evaluation partition identifiers;
- model and feature configuration;
- deterministic random seed.

Outputs:

- candidate record/entity/period reference;
- raw model score and threshold configuration;
- feature values used;
- comparison context or exemplar records where available;
- model/feature/training-data version;
- limitations and insufficient-evidence state.

### 14.4 Model governance

- no internet or external inference;
- no automatic training on examiner dispositions;
- no uncontrolled self-learning;
- no automatic model replacement;
- new model version follows `Candidate → Evaluated → Approved → Active → Retired`;
- active model file and manifest are integrity-checked;
- training/fitting data and held-out evaluation remain separated;
- model must be compared against simple robust baselines;
- module can be disabled without breaking the application;
- a score is neither a probability of wrongdoing nor proof;
- insufficient feature quality yields no ML candidate.

---

## 15. Analytics Module Interface

### 15.1 Common request

Every module receives a read-only run context containing:

- analytical run ID;
- entity/period scope;
- eligible canonical evidence views;
- evidence-family quality matrix;
- frozen configuration and registry versions;
- baseline/cohort services where relevant;
- deterministic seed where relevant;
- resource and time budget.

### 15.2 Common candidate response

Every module returns zero or more candidate findings with:

- module ID, type, and version;
- candidate ID and natural correlation key;
- entity, period, category, and affected scope;
- observation (“what happened”);
- method-specific basis and calculation payload;
- evidence references with roles;
- missing-evidence search specification where relevant;
- applicability and eligibility outcome;
- evidence-confidence proposal with reasons;
- quality dependencies and limitations;
- neutral explanation/question template inputs;
- correlation tags/root-event keys;
- execution diagnostics, not sensitive raw content.

### 15.3 Replaceability

The orchestrator depends only on this contract, not a module’s internal algorithm. A removed ML module, changed rule engine, or upgraded text detector therefore does not change the finding, review, or report interfaces.

---

## 16. Finding Generation Architecture

### 16.1 Lifecycle

```text
Detection
  -> Candidate Finding
  -> Eligibility and Evidence Validation
  -> Correlation / De-duplication
  -> Explanation Construction
  -> Evidence Confidence + Data Quality
  -> Attention Priority
  -> Examiner Queue
  -> Review / Disposition
  -> Report or New Analytical Revision
```

### 16.2 Finding contract

Each queueable finding contains:

- finding ID and revision;
- entity and reporting period;
- title and category;
- attention priority band and priority explanation;
- observation / what happened;
- why flagged;
- analytical basis or independent bases;
- calculation, denominator, context, and exclusions;
- evidence references and source-record links;
- expected-but-missing search scope where applicable;
- investigation question;
- limitations, uncertainty, and alternative explanations;
- evidence confidence;
- data-quality status;
- rule/model/module and feature versions;
- analytical run ID/version;
- generated timestamp;
- review status and later disposition history.

### 16.3 Candidate validation

Before queueing, the evidence validator confirms:

- required evidence references resolve;
- required quality/eligibility conditions are met;
- calculations can be recomputed from frozen inputs;
- absence language matches observation scope;
- source and version references exist;
- counterevidence and exceptions were evaluated;
- the candidate has not been invalidated by an upstream data defect.

Failed validation yields an analytical diagnostic or data-quality item, not a hidden dropped finding.

### 16.4 Correlation and revisions

Candidates sharing the same entity, period, affected records, and root condition may be grouped into one multi-basis finding. Correlation preserves each basis and does not imply independence. A finding is immutable once sealed; changed evidence or logic creates a revision linked to the prior finding.

---

## 17. Attention, Evidence Confidence, and Data Quality

### 17.1 Independent dimensions

| Dimension | Question answered | Example bands |
|---|---|---|
| Attention Level | How early should an examiner review this? | Urgent, High, Medium, Routine |
| Evidence Confidence | How strongly does the submitted evidence support the stated observation? | Strong, Moderate, Limited, Indeterminate |
| Data Quality | How usable/complete are the required inputs? | Sufficient, Sufficient with limitations, Insufficient, Indeterminate |

These are stored, displayed, filtered, and explained independently. They are not averaged into one score.

### 17.2 Important distinctions

- High attention + limited confidence: severe potential scope, but missing source family; review data completeness first.
- Medium attention + strong confidence: well-supported but lower-impact issue.
- Insufficient data quality: block operational finding; produce a data-quality review item if appropriate.
- Strong evidence confidence does not mean the organization acted improperly; it means the observation is well supported by submitted evidence.

---

## 18. Prioritization Architecture

### 18.1 Banded, lexicographic policy

**PROJECT DECISION:** The MVP uses explainable attention bands, not a public 0–100 risk score. Queue order is determined through ordered decision stages:

1. verify minimum queue eligibility and evidence-confidence floor;
2. determine affected criticality/scope band;
3. consider recurrence/persistence and time sensitivity;
4. consider independent corroborating bases;
5. consider deviation magnitude where statistically eligible;
6. apply uncertainty/data-quality guardrails;
7. assign a deterministic tie-break order, such as generation time and stable finding ID.

The exact factor thresholds remain versioned configuration validated in later phases.

### 18.2 Candidate factors

- affected asset/process criticality;
- source alert/case severity;
- number and proportion of affected eligible records;
- recurrence and duration across periods;
- cross-record contradiction;
- magnitude of eligible historical/peer deviation;
- negative-space scope;
- number of genuinely independent analytical bases;
- evidence confidence and data-quality limitations;
- approved exception/counterevidence.

### 18.3 Guardrails

- Findings below the minimum evidence state cannot receive Urgent/High solely from severity.
- Missing source families reduce confidence; they do not automatically raise operational attention.
- Correlated signals are grouped by root-event/correlation key and cannot be counted as independent corroboration.
- Peer or ML deviation alone cannot produce the highest attention band.
- Data-quality findings use a distinct category and queue rationale.
- Every assignment stores the rules/factors that caused it.

### 18.4 Entity queue

Entity-level attention is an aggregation view, not a new truth score. It shows the highest active finding band, counts by category/confidence, affected scope, unresolved data-quality items, and trend. It never labels an entity “good” or “bad.” Findings also expose affected control/process references and prioritized alert/case/source-record samples when those references exist, so examiner queues can be filtered at entity, control, process, finding, and sample levels without inventing a separate risk score.

### 18.5 Examiner override

An authorized examiner may raise, lower, defer, or dismiss queue priority. The override requires a reason and creates an audit event. It does not alter the original system-assigned priority; both remain visible.

---

## 19. High-Level Conceptual Data Model

### 19.1 Major entities

| Concept | Purpose | Important relationships |
|---|---|---|
| Organization/CSE | Supervisory subject and namespace | owns assets/submissions; belongs to peer attributes |
| Control/Process Reference | Versioned supervisory subject or workflow/control label when supplied/configured | applies to entities, rules, records, and findings; may be absent from source data |
| Review Sample | Explicit set of alert/case/source-record references selected for manual review | generated from a finding/priority decision; never replaces the underlying records |
| Asset | Monitored system/service/resource | belongs to entity; referenced by alerts/cases/coverage |
| Alert | SOC-generated operational record | may reference asset; may link to zero/many cases |
| Case/Incident | Work container for one/many alerts | has investigations, escalations, actions, resolution/closure |
| Investigation Activity | Analyst/system action or note | linked to case/alert and actor/time |
| Escalation | Transfer/notification/approval event | linked to case/alert; may have reason/level |
| Action/Remediation | Follow-up or treatment evidence | linked to issue/case/asset; may recur |
| Resolution | Substantive resolution state/event | linked to case; distinct from administrative closure where available |
| Closure | Final closure/disposition evidence | linked to case/alert; may require approval/reason |
| Monitoring Coverage | Declared/observed coverage window | links asset and evidence source/time |
| Exception/Applicability | Approved exception or rule applicability context | applies to entity/asset/case/rule/period |
| Submission | Imported package for entity/period | contains source files and manifests |
| Source Artifact/Record | Preserved bytes and logical row/object | origin of normalized evidence |
| Canonical Evidence Record | Common internal representation | maps to source and cross-record links |
| Data-Quality Result | Validation/coverage outcome | applies at field/record/family/period/submission |
| Analytical Run | Frozen execution context | consumes submissions/versions; produces findings |
| Rule/Expectation | Versioned analytical expectation | used by run/module/finding |
| Baseline | Versioned historical reference | contains eligible historical membership |
| Peer Cohort | Versioned comparison set | contains eligible/excluded members and reasons |
| Feature Set/Model | Optional versioned analytical artifact | used only by an approved run/module |
| Finding | Examiner-ready analytical observation | links bases, evidence, priority, revisions |
| Evidence Link | Typed connection from finding to source/context | trigger/support/counterevidence/baseline/peer/quality |
| Review/Disposition | Human interpretation/action | linked to finding revision and reviewer |
| Audit Event | Append-only logical lifecycle event | actor, action, target, time, prior/current reference |
| Report/Export | Frozen human-readable output | links included findings and export manifest |

### 19.2 Relationship shape

```text
Organization
  +--> Asset
  |      +--> Monitoring Coverage
  |      +--> Alert <----> Case / Incident
  |                         +--> Investigation Activity
  |                         +--> Escalation
  |                         +--> Action / Remediation
  |                         +--> Resolution
  |                         +--> Closure
  |
  +--> Submission --> Source Artifact --> Source Record
                         |                    |
                         +------mapping------+
                                              v
                                    Canonical Evidence
                                              |
Analytical Run --> Rule / Baseline / Cohort / Model
       |                                      |
       +------------------> Finding <---------+
                              |
                              +--> Evidence Links --> Canonical/Source Records
                              +--> Review / Disposition
                              +--> Report / Export
```

### 19.3 Optional and missing relationships

Alert-to-case, case-to-escalation, case-to-remediation, asset-to-coverage, and resolution-to-closure may legitimately be absent, unavailable, or not applicable. The data model represents relationship state and search scope; it does not infer a missing event merely from a null foreign key.

---

## 20. End-to-End Data Flow

| Stage | Input | Processing | Output | Failure behavior |
|---|---|---|---|---|
| 1. Source selection | Local CSV/JSON/package | Discover files and enforce intake boundaries | Candidate submission | No files or disallowed paths: stop safely |
| 2. Quarantine | Candidate files | Type/size/archive checks; preserve bytes; hash | Preserved artifacts + manifest | Corrupt/dangerous: reject/quarantine, no analytics |
| 3. Parsing | Preserved artifacts + selected profile | Resource-bounded parsing | Staging records + parser diagnostics | Isolate file/job; no partial silent acceptance |
| 4. Validation | Staging records | Schema, type, ID, timestamp, duplicate, relationship, period checks | Quality matrix and eligible/invalid records | Invalid dependent data blocked; diagnostics retained |
| 5. Normalization | Eligible records + mapping version | Map vocabularies/IDs/times; retain originals | Canonical evidence + lineage | Ambiguous mapping remains unresolved |
| 6. Quality/provenance sealing | Canonical records + manifest | Link source, versions, missing states, coverage | Eligible run snapshot | Missing provenance blocks queueable findings |
| 7. Run planning | Scope + config registry | Freeze versions; compute module eligibility | Run manifest and plan | Invalid config stops run before analytics |
| 8. Analytics | Read-only snapshot | Deterministic, statistical, text, optional ML modules | Candidate findings | Module failure isolated and disclosed |
| 9. Evidence validation/correlation | Candidates + evidence graph | Recompute, check refs, evaluate exceptions, group overlap | Valid candidate packages | Invalid candidate withheld with diagnostic |
| 10. Explanation | Valid candidates | Render method-specific human/technical explanation | Finding draft | Missing explanation fields block publication |
| 11. Priority | Finding + three dimensions | Apply versioned band policy/guardrails | Queueable finding/entity views | Ineligible evidence cannot receive high band |
| 12. Examiner review | Queue and evidence | Inspect, comment, override, disposition | Review state + audit event | Save is transactional; prior state retained |
| 13. Report/export | Selected sealed findings/reviews | Render local package; hash manifest | Offline report/export | Partial export removed or marked failed |

---

## 21. Failure-Safe Design

| Condition | Safe response | Examiner-visible result |
|---|---|---|
| Required column missing | Mark source family `NOT_PROVIDED`; block dependent modules | Mapping/quality error; no false zero |
| Invalid timestamp | Isolate field/record from temporal calculations | Record-level diagnostic and affected findings blocked/lowered |
| Duplicate ID | Preserve all source rows; classify exact/conflicting duplicate | Duplicate consistency item; no silent overwrite |
| Broken relationship | Record unresolved link and provenance | Consistency finding if eligible; dependent gap qualified |
| Incomplete period | Mark partial/immature | Negative-space/historical modules blocked or limited |
| Peer cohort too small | Return `INSUFFICIENT_PEERS` | No fallback comparison; reason displayed |
| Historical sample insufficient | Return `INSUFFICIENT_HISTORY` | No threshold inference; reason displayed |
| Corrupt source file | Reject/quarantine before canonicalization | Import failure with sanitized diagnostic |
| Parser fails | Roll back staging transaction; preserve source | Submission not accepted; prior data unchanged |
| Model unavailable/corrupt | Disable optional module and record run omission | Deterministic/statistical run continues |
| Rule not applicable | Exclude from eligible universe | Not applicable, no finding |
| Evidence missing | Evaluate expectation + completeness | Cautious negative-space finding or indeterminate state |
| Source records contradict | Preserve both and emit consistency candidate | Contradiction shown; no arbitrary source chosen |
| Report generation fails | No partial final artifact; record failure | Retry possible without rerunning analytics |
| Storage/write failure | Transaction rollback and health error | No half-published finding/review |
| Configuration version missing | Stop run/reproduction | Explicit reproducibility failure |

**PROJECT DECISION:** Analytics prefer false-negative-safe abstention over unsupported claims: when applicability or evidence adequacy cannot be established, return `Indeterminate` instead of inventing certainty.

---

## 22. Security Architecture

### 22.1 Security principles

- assume input files are untrusted and sensitive;
- preserve source integrity while minimizing unnecessary copies;
- parse with least privilege and resource limits;
- deny outbound network access by design;
- expose only loopback application access in the MVP;
- keep secrets and sensitive evidence out of source control and routine logs;
- version and verify dependencies, rules, configurations, and models;
- audit security-relevant and supervisory actions.

### 22.2 Intake controls

- extension allowlist plus structural/content validation;
- generated internal filenames and fixed storage roots;
- canonical-path checks to prevent traversal/symlink escape;
- per-file, total-package, row, field-length, nesting-depth, and time limits;
- archive entry-count, expanded-size, ratio, nested-archive, and path checks if ZIP is supported;
- safe CSV/JSON parsers; no macro/document execution;
- spreadsheet export neutralization for values beginning with formula characters;
- temporary files inside a restricted application directory and secure cleanup;
- parser errors sanitized before logging/display.

### 22.3 Storage and access

- preserved source zone is read-only to normal application operations;
- canonical/finding stores are reachable only through the backend service;
- local reports inherit restrictive permissions;
- audit events record actor, action, target, version, and timestamp;
- routine logs exclude raw notes, customer information, and full sensitive rows;
- backups/retention are deployment policy, not hard-coded.

### 22.4 Authentication and authorization

**PROJECT DECISION:** The architecture defines local roles—Administrator, Examiner, and Read-only Reviewer—and requires an actor identity on review/configuration/audit events. The MVP may use local accounts only; no external identity provider is required.

**ASSUMPTION:** The demonstration runs on a controlled workstation. Password policy, hardware-backed identity, enterprise SSO, and account lifecycle are deployment-specific.

### 22.5 Supply-chain and analytical integrity

- pinned dependency lock and software bill of materials;
- offline package manifest with hashes/signature where available;
- approved rule/model/mapping registry with checksum;
- reject changed model/rule artifacts that do not match active manifests;
- no runtime package download;
- repository excludes imported evidence, local databases, reports, credentials, models not approved for distribution, and generated secrets;
- update artifacts are verified before activation and support rollback.

---

## 23. Offline and Air-Gapped Architecture

### 23.1 Network behavior

**PROJECT DECISION:** Core operation requires no internet, cloud, SaaS, telemetry, external API, external font/CDN, external LLM, or license server. The production build contains no runtime remote URLs. The backend listens on loopback only by default.

### 23.2 Local assets

The offline bundle contains:

- backend/runtime and pinned dependencies;
- compiled frontend JavaScript/CSS/fonts/icons;
- DuckDB engine and local database migrations when implemented;
- schema/mapping/rule/configuration bundles;
- optional approved model and feature manifests;
- offline help/documentation;
- test/health-check metadata;
- package integrity manifest and version information.

### 23.3 Local persistence

- preserved source artifacts in an application-managed directory;
- DuckDB file for canonical evidence, findings, reviews, and audit metadata;
- versioned configuration/model artifacts in read-only release directories;
- generated reports in an explicit export directory.

### 23.4 Update process

`Build in controlled environment → lock and inventory → test → hash/sign → approved transfer media → verify offline → stage → migrate/health check → activate → preserve rollback`

Updates never overwrite historical rule/model versions required for reproduction. If an update requires a migration that would break reproduction, the old runtime or an exportable reproduction package must be retained.

### 23.5 Hidden-call verification

The release test includes operation with network disabled plus inspection that all frontend assets and API routes are local. Any optional update-check or telemetry feature is prohibited rather than merely disabled.

---

## 24. Concrete MVP Technology Stack

### 24.1 Selected stack

| Area | Decision | Reason | Trade-off |
|---|---|---|---|
| Language/runtime | Python 3.12 | Strong offline analytics, parsing, statistics, testing, and team accessibility | Packaging native dependencies requires discipline |
| Data-frame processing | Polars for bulk transforms; NumPy/SciPy for numerical methods | Columnar performance and explicit expressions; robust numerical tools | Smaller team familiarity than pandas; pandas may be needed only for library interop |
| Analytical/application storage | DuckDB, single local database file, with preserved files on filesystem | Embedded, columnar analytics, SQL traceability, no server, simple air-gap packaging | Limited multi-writer concurrency; not the production choice for many concurrent users |
| ML/text | scikit-learn | Offline, mature Isolation Forest/TF-IDF/evaluation support | Model explanations and sparse/high-dimensional limitations remain |
| Backend | FastAPI + Pydantic | Typed local API, automatic validation, clear separation between UI/orchestration/analytics | Adds API layer and Python web runtime |
| Job execution | In-process bounded background job runner with persisted run state | Sufficient for one-workstation MVP; no external queue/server | No horizontal scale; long jobs require careful cancellation/recovery |
| Frontend | React + TypeScript + Vite, compiled and served locally by backend | Usable examiner workflow, strong component/test ecosystem, no runtime CDN | More build complexity than a Python dashboard |
| Charts | Small locally bundled chart library selected during implementation | Distribution/trend views need accessible visuals | Adds frontend dependency; must support tables/text equivalents |
| Unit/integration tests | pytest; Hypothesis where invariants benefit | Strong Python testing; property tests for dates/missing states/mappings | Generated cases require careful constraints |
| Browser tests | Playwright against local application | Reliable end-to-end examiner-flow and offline checks | Browser binaries increase package/test size |
| Packaging | Single OCI image archive for the judged MVP, serving compiled UI and API; source + pinned wheelhouse as documented fallback | Reproducible dependencies, easy offline transfer, stable demo | Requires approved container runtime; target-platform image must be prepared |

### 24.2 Why one DuckDB store for the MVP

**PROJECT DECISION:** Use DuckDB for canonical analytical tables, metadata, findings, reviews, and audit records in the single-user MVP. This avoids synchronization and backup complexity between analytical and transactional stores. Writes are serialized through the backend.

**Trade-off:** If production needs concurrent examiners or strict transactional workloads, review/audit state may later move to SQLite/PostgreSQL while DuckDB remains analytical. The module boundaries prevent UI and analytics from depending directly on storage choice.

### 24.3 Why not Streamlit for the primary UI

A Python dashboard would accelerate initial screens but gives weaker control over evidence navigation, complex review state, accessible interaction, and long-term browser testing. React/FastAPI costs more setup but better supports the examiner workflow and a polished two-minute demonstration.

### 24.4 Packaging assumption and fallback

**ASSUMPTION:** The hackathon demonstration host permits a container runtime. The release is loaded from an offline image archive and exposes only a local port.

**OPEN QUESTION:** If containers are prohibited, Phase 5 must switch to a signed/native bundle or offline Python runtime + wheelhouse. The architecture and storage remain unchanged.

### 24.5 Explicit exclusions

No Redis, Kafka, Elasticsearch, cloud database, external vector database, Kubernetes, external auth service, or LLM is needed for the MVP. These would add operational surface without solving the core supervisory problem.

---

## 25. Performance and Scalability Architecture

### 25.1 Strategy

- batch and columnar processing;
- projection/predicate pushdown in DuckDB/Polars;
- normalize each accepted submission once;
- derive features by entity/period and cache them by run/version;
- avoid loading all source text/records into UI memory;
- paginate/filter server-side;
- generate reports from sealed finding packages rather than full table dumps;
- bound text-pair comparisons within comparable groups to avoid all-pairs explosion;
- make modules independently measurable and cancellable.

### 25.2 Benchmark dimensions

No performance number is declared until measured. The benchmark matrix must vary:

- entities: small, target, stress tiers;
- reporting periods: 1, 4–6, and stress tier;
- files and total bytes;
- alerts, cases, activities, assets, and note lengths;
- relationship density and missingness;
- duplicate/invalid-rate scenarios;
- number of active rules/modules;
- peer cohort and historical-window sizes;
- text-similarity group sizes;
- ML enabled/disabled;
- cold vs warm run.

### 25.3 Measures

- import and validation wall-clock time;
- normalization time;
- per-module and total analytical time;
- evidence-correlation/prioritization time;
- report-generation time;
- startup and first-dashboard time;
- peak resident memory;
- database and preserved-source disk growth;
- UI query latency for queue and finding detail;
- failure/recovery behavior under resource limits.

### 25.4 Benchmark protocol

1. define hardware, OS, runtime, package version, and dataset seed;
2. use small deterministic fixture plus larger held-out synthetic benchmark;
3. repeat runs and report median and spread;
4. confirm record/finding counts and hashes, not only speed;
5. profile each stage independently;
6. report failures and quality reductions;
7. establish acceptance targets only after the first architecture benchmark.

**OPEN QUESTION:** The final target hardware and mandatory record scale must be agreed before implementation acceptance criteria are frozen.

---

## 26. High-Level UI Architecture

### 26.1 User-flow structure

`Dashboard → Entity Queue → Entity Detail → Finding Detail → Evidence / Source Record → Examiner Review → Report / Export`

### 26.2 Required information by level

| Level | Must show |
|---|---|
| Dashboard | submissions/runs, entities/periods analyzed, findings by attention/confidence/category, data-quality warnings, run omissions/status |
| Entity Queue | entity, highest attention band, unresolved finding counts, confidence mix, quality state, affected controls/processes/samples, trend context |
| Entity Detail | period selector, finding list, evidence coverage, historical/peer availability, data-quality limitations, review progress |
| Finding Detail | what happened, why, bases, calculations, three dimensions, limitations, alternatives, question, affected records |
| Evidence / Source | evidence-role list, canonical value, original value, source file/record locator, timeline, baseline/cohort membership, version path |
| Examiner Review | disposition, priority override, notes, follow-up question, reviewer/time, immutable prior actions |
| Report / Export | selected scope, executive summary, evidence packages, limitations, review dispositions, manifest/version/hash |

### 26.3 Thirty-second comprehension target

The top of Finding Detail presents in this order:

1. **Finding**
2. **Why it was flagged**
3. **Evidence summary**
4. **What to investigate**

Technical calculations and provenance are one level deeper but never hidden. Attention, confidence, and quality use labels plus text, not color alone.

### 26.4 UI safety

- Never use “bad organization,” “guilty,” or “confirmed failure.”
- Display insufficient peer/history states explicitly.
- Show when a module did not run.
- Keep model score in technical details with warning text.
- Require confirmation and reason for dismiss/override/export of sensitive records.

---

## 27. Versioning and Reproducibility

### 27.1 Versioned artifact matrix

| Artifact | Version identity | Retention rule |
|---|---|---|
| Source data | submission ID + file hash | Never overwritten by application |
| Manifest | submission manifest version/hash | Retain with source |
| Canonical schema | semantic version + checksum | Retain while referenced |
| Mapping | mapping ID/version/checksum/effective period | Immutable once active |
| Rule/expectation | rule ID/version/checksum/effective period | Immutable once used |
| Configuration | frozen run snapshot hash | Retain per run |
| Feature definition | feature-set ID/version | Retain with model/run |
| Model | model ID/version/file hash/training manifest | Retain while referenced |
| Baseline | metric/config version + membership snapshot | Retain per finding/run |
| Peer cohort | cohort definition version + membership snapshot | Retain per finding/run |
| Analytical run | run ID + complete manifest hash | Immutable when sealed |
| Finding | stable ID + revision | Prior revisions retained |
| Review | review event ID/version | Append-only logical history |
| Report | report ID/version + included finding revisions + hash | Retain/export with manifest |

### 27.2 Reproduction modes

- **Exact reproduction:** same source hashes and all artifact versions; expected identical deterministic outputs and seeded model outputs.
- **Current-method rerun:** same source, newer approved configuration; creates a new run and finding revisions.
- **Independent verification:** recalculate displayed metrics from exported evidence package without relying on UI.

If exact reproduction is impossible because an artifact is missing, the system states this explicitly rather than approximating silently.

---

## 28. Reporting and Export Architecture

### 28.1 Report types

- supervisory queue summary;
- entity assessment package;
- individual finding evidence package;
- data-quality and ingestion report;
- analytical run/reproducibility manifest;
- examiner review/disposition report.

### 28.2 Export safety

Exports are generated locally, include classification/sensitivity notices configurable by deployment, and contain only selected scope. Spreadsheet exports neutralize formulas. Every package includes report version, run/finding revisions, source hash references, included evidence list, generation actor/time, and integrity hash.

### 28.3 Non-authoritative wording

Reports distinguish:

- system observation;
- analytical interpretation;
- uncertainty/limitations;
- examiner disposition.

A system-generated report is not an automatic compliance certificate or final supervisory decision.

---

## 29. Architecture Decision Records

### ADR-001 — Analytical storage

- **Context:** Local multi-entity analytics and persistent examiner state are required without a database server.
- **Options:** DuckDB only; SQLite only; DuckDB + SQLite; PostgreSQL.
- **Decision:** DuckDB only for MVP, plus filesystem source/report storage.
- **Reason:** Best balance of analytical performance, SQL explainability, one-file operation, and low deployment complexity for a single writer.
- **Trade-offs:** Review/audit concurrency is limited; transactional state shares lifecycle with analytics.
- **Consequences:** Backend serializes writes; storage abstraction preserves a later split.

### ADR-002 — Backend architecture

- **Context:** UI, ingestion, analytics, audit, and reports need controlled boundaries.
- **Options:** monolithic script/dashboard; FastAPI local service; desktop-native application.
- **Decision:** Modular monolith using FastAPI, with in-process job orchestration.
- **Reason:** Clear interfaces and testability without distributed-system overhead.
- **Trade-offs:** Long jobs and failure isolation require explicit state/cancellation.
- **Consequences:** No microservices or external queue for MVP.

### ADR-003 — Frontend approach

- **Context:** Evidence drill-down and review workflow must be clear and testable.
- **Options:** server-rendered templates; Streamlit; React/TypeScript; desktop toolkit.
- **Decision:** React/TypeScript compiled offline and served by the backend.
- **Reason:** Best control over examiner UX, state, accessibility, and Playwright testing.
- **Trade-offs:** Higher initial build complexity.
- **Consequences:** All assets are bundled; no CDN/runtime package fetch.

### ADR-004 — Deterministic-first analytics

- **Context:** Core requirements are execution gaps, negative space, evidence, and auditability.
- **Options:** ML-first anomaly platform; rules/statistics first; rules only.
- **Decision:** Deterministic checks first, robust statistics second, ML optional.
- **Reason:** Stronger reproducibility and direct requirement mapping.
- **Trade-offs:** Rules need explicit expectations and may miss unknown patterns.
- **Consequences:** Rule registry and evidence contract are core components.

### ADR-005 — ML as supporting layer

- **Context:** ML may reveal multivariate patterns but risks opacity and overclaiming.
- **Options:** mandatory Isolation Forest; optional replaceable detector; no ML interface.
- **Decision:** Optional detector interface; evaluate Isolation Forest against simple baselines.
- **Reason:** Preserves innovation path without making ML authoritative.
- **Trade-offs:** Additional evaluation/versioning work even if removed.
- **Consequences:** System operates fully with ML disabled; no model auto-update.

### ADR-006 — Evidence/provenance design

- **Context:** Every finding must reach original submitted evidence and be reproducible.
- **Options:** store only normalized rows; copy selected source values into findings; provenance graph/links.
- **Decision:** Preserve source artifacts and maintain typed evidence/provenance links through mappings and runs.
- **Reason:** Supports traceability, corrections, and independent verification.
- **Trade-offs:** More metadata and storage complexity.
- **Consequences:** No analytical module returns unreferenced claims.

### ADR-007 — Offline packaging

- **Context:** Complete air-gapped operation and demo reliability are required.
- **Options:** source install; native executable; OCI image archive; VM appliance.
- **Decision:** OCI image archive as primary hackathon package; pinned wheelhouse/source fallback.
- **Reason:** Reproducible runtime and simple offline transfer.
- **Trade-offs:** Container runtime may not be allowed.
- **Consequences:** Keep platform-independent application design and document fallback.

### ADR-008 — Priority model

- **Context:** Examiner effort must be focused without implying truth.
- **Options:** weighted 0–100 risk score; ML ranking; banded lexicographic policy.
- **Decision:** Versioned, transparent attention bands with independent confidence and quality.
- **Reason:** Easier to defend and prevents false precision.
- **Trade-offs:** Less visually simple than one number; tie-breaking needs policy.
- **Consequences:** Every queue placement has factor-level explanation.

### ADR-009 — Synthetic validation strategy

- **Context:** Real NCIIPC/CSE data is unavailable; synthetic data risks circular success.
- **Options:** one seeded demo dataset; multiple held-out datasets; synthetic plus manual review.
- **Decision:** Deterministic fixtures + held-out multi-seed benchmark + legitimate unusual controls + blinded manual-review sample.
- **Reason:** Tests false positives and reduces generator-detector circularity.
- **Trade-offs:** More dataset/evaluation work.
- **Consequences:** Ground truth is separated from analytical inputs; metrics reported by family.

### ADR-010 — Testing strategy

- **Context:** Evidence correctness and demo reliability require several test levels.
- **Options:** unit tests only; manual demo only; layered automated testing.
- **Decision:** pytest unit/integration, property tests for invariants, golden analytical fixtures, Playwright workflows, offline and benchmark tests.
- **Reason:** Different failure modes require different test scopes.
- **Trade-offs:** Test assets and maintenance consume time.
- **Consequences:** Every active rule/module must have positive, negative, incomplete-data, and counterexample tests.

---

## 30. Non-Functional Requirements

### 30.1 Must-have

| Quality | Requirement |
|---|---|
| Offline | All core functions operate with network disabled; all assets/dependencies local |
| Explainability | Every queueable finding satisfies the full evidence chain and shows limitations |
| Auditability | Imports, runs, configuration activation, reviews, overrides, and exports are recorded |
| Reproducibility | Sealed run retains all referenced versions, membership snapshots, hashes, and seeds |
| Data integrity | Preserved source is immutable-by-application and hash-verified |
| Security | Untrusted files are quarantined/validated; safe parsing and path/archive limits enforced |
| Reliability | Transactional stage boundaries prevent half-published submissions/findings/reviews |
| Human control | Examiner disposition/override is available and system result never becomes final judgment |
| Testability | Modules use common contracts; deterministic outputs have golden/independent recalculation tests |
| Maintainability | Mappings/rules/modules are versioned and replaceable without UI redesign |
| Usability | Finding/why/evidence/question is understandable without reading model internals |
| Portability | Release targets one declared platform and has a documented offline fallback |

### 30.2 Should-have

- resumable/retryable import and analysis jobs;
- accessible keyboard/table navigation and non-color status indicators;
- exportable independent-verification package;
- trend comparison across periods;
- local role separation and configurable retention;
- graceful cancellation of long analytical runs;
- benchmark-based performance acceptance targets.

### 30.3 Future

- approved multi-user deployment and enterprise identity;
- production database split and concurrent scheduling;
- multiple source-system adapters and schema-profile authoring UI;
- signed update infrastructure integrated with deployment policy;
- validated advanced change-point/embedding methods;
- formal retention, backup, disaster-recovery, and accreditation requirements.

---

## 31. Architecture Risks and Mitigations

| Risk | Architectural impact | Mitigation | Residual risk |
|---|---|---|---|
| Incomplete submissions | False negative-space/execution gaps | evidence states, period completeness, quality gates, cautious language | Source may misstate completeness |
| Weak peer cohorts | Invalid comparison | versioned eligibility, minimum cohort, no fallback, display exclusions | Real comparability remains imperfect |
| Unstable history | Noisy deviations | robust statistics, process boundaries, minimum samples, insufficient state | Short-history entities remain limited |
| Correlated findings | Inflated priority | root-event keys, evidence overlap analysis, grouped multi-basis finding | Correlation logic may miss semantic overlap |
| False positives | Wasted examiner effort/trust loss | counterevidence, benign unusual cases, overrides, per-family evaluation | Cannot eliminate ambiguity |
| Synthetic-to-real gap | Demo metrics fail to transfer | held-out generation, manual review, explicit limits, future pilot | No production assurance without real data |
| ML overfitting/opacity | Misleading anomaly leads | optional slot, ablation, versioning, no probability claim | Unsupervised ground truth remains weak |
| Untrusted files | Parser compromise/data leakage | quarantine, limits, safe parser, generated paths, no execution | Parser/library vulnerabilities remain |
| Offline dependency problems | Demo/install failure | OCI archive, lock/SBOM, health check, fallback wheelhouse | Host runtime compatibility |
| Large data/text scale | Long runs/memory failure | columnar query, bounded grouping, pagination, benchmarks | Final target scale unknown |
| Reviewer automation bias | Priority treated as truth | separate dimensions, neutral wording, visible alternatives, override | Human bias cannot be designed away |
| Traceability failure | Finding cannot be defended | evidence validator blocks publication; immutable version refs | Source itself may be incomplete/untruthful |
| Dual meaning of null | False zero/missing inference | explicit evidence-state vocabulary | Poor adapter implementation could still misclassify |
| Configuration drift | Non-reproducible findings | frozen run snapshots and immutable versions | Artifact retention burden |
| Single-file store corruption | Loss of local state | transactional writes, backups/export, integrity health checks | Formal backup policy is unresolved |
| Container restriction | Cannot run target package | fallback offline runtime/wheelhouse, platform abstraction | Alternate package must be tested |
| Scope creep | Build becomes SIEM/generic dashboard | no streaming/response interfaces; ADR review against spec | Presentation language may still overclaim |

---

## 32. Implementation Boundary

### 32.1 What Architecture Now Defines

- complete component boundaries and responsibilities;
- trust zones and end-to-end batch flow;
- validation and non-collapsible missing-data semantics;
- canonical normalization and provenance obligations;
- modular analytics and common module contract;
- rule, baseline, peer, negative-space, text, and optional ML behavior;
- finding lifecycle and required fields;
- independent attention/confidence/quality dimensions;
- transparent banded prioritization and override path;
- high-level conceptual entities and relationships;
- safe failure behavior;
- security and offline design;
- concrete MVP technology and packaging direction;
- benchmark methodology, UI flow, versioning, reports, ADRs, and non-functional requirements.

### 32.2 What Is Deliberately Deferred

- physical DuckDB tables, columns, keys, indexes, and migrations;
- final canonical data dictionary and source mapping files;
- exact synthetic generator and produced dataset;
- final rule catalogue and organization-specific policies;
- final thresholds, sample sizes, grace periods, peer cohort values, and priority bands;
- feature engineering and decision whether Isolation Forest ships;
- implementation of ingestion, backend, analytics, UI, tests, and reports;
- final chart/component visual design;
- final deployment scripts, container image, native fallback, and update signing;
- production identity, retention, backup, concurrency, and target hardware requirements;
- validation results and performance acceptance numbers.

Later phases must not silently alter this architecture. Material changes require a new ADR and project-owner review.

---

## 33. Open Questions and Assumptions Requiring Review

### 33.1 Open questions

1. Is an OCI/container runtime permitted on the actual demonstration/deployment host?
2. What target OS, CPU architecture, memory, disk, and benchmark scale should be accepted?
3. Will the prototype have one examiner or multiple concurrent users?
4. Which exact evidence families and source-file layouts will the synthetic dataset implement first?
5. Which authority/source justifies each active demo expectation?
6. What minimum historical observations/periods and peer cohort sizes pass validation?
7. Which factors and boundaries assign Urgent/High/Medium/Routine attention bands?
8. Who can perform the blinded manual-review comparison?
9. What report formats and sensitivity markings are expected?
10. What retention, backup, encryption-at-rest, and local identity policies apply in the intended environment?
11. Does optional Isolation Forest add measurable value over robust baselines?
12. What accessibility standard and browser version must the offline UI support?

### 33.2 Current assumptions

- periodic batch submissions, not streaming telemetry;
- CSV and JSON are sufficient for the MVP intake demonstration;
- one controlled workstation and one active examiner are adequate for the hackathon;
- the team can build/test a Python + React modular monolith;
- a target-platform OCI image can be prepared for the demo, with fallback documented;
- synthetic data and manual-review samples contain no real sensitive operational data;
- organization-specific policies are configuration supplied later, not invented in code.

---

## 34. Final Architecture Consistency Check

| Check | Result | Evidence in this document |
|---|---|---|
| `PROJECT_SPEC.md` alignment | **YES** | Sections 1–3, 8–19, 26, 32 preserve scope and finding contract |
| Research alignment | **YES** | Deterministic-first, robust baselines, peer guardrails, confidence/quality separation, held-out validation |
| Execution gaps | **YES** | Sections 8–9 and module contract |
| Negative space | **YES** | Section 12 four-question model and cautious states |
| Anomalies | **YES, optional/supporting** | Section 14 |
| Peer comparison | **YES** | Section 11 |
| Prioritization | **YES** | Section 18 banded policy |
| Explainability | **YES** | Sections 7 and 16 |
| Auditability | **YES** | Sections 7, 22, 27–28 |
| Scalability | **YES, benchmark-driven** | Section 25 |
| Offline deployment | **YES, with runtime assumption** | Sections 23–24 |
| Human manual review | **YES** | Sections 1, 16, 18, 26 |
| Scope control | **YES** | No stream collector, response actuator, or cloud path |
| Evidence traceability | **YES** | Finding-to-source path and publication gate |
| Examiner override | **YES** | Audited override preserves original priority |
| ML safety | **YES** | Optional, versioned, disableable, no auto-learning/probability claim |
| Air-gapped completeness | **YES** | Local storage, assets, analytics, models, reports, help, and updates |
| Student-team feasibility | **YES, conditional** | Modular monolith, embedded DB, no distributed services; UI effort remains material |
| Two-minute demo feasibility | **YES** | Preloaded/fast batch run can show import status → queue → evidence → review/export |
| Competitive differentiation | **YES** | Architecture operationalizes Finding → Why → Basis → Calculation → Evidence → Source → Question |

### 34.1 Review conditions

The architecture is ready for review, not approval. Review should focus on:

- acceptance of the concrete stack and container assumption;
- whether one DuckDB store is acceptable for the MVP;
- agreement on the three independent finding dimensions;
- agreement on the banded priority model;
- confirmation of conceptual evidence states and provenance requirements;
- feasibility of React/FastAPI within team capacity;
- ownership and sequence of the next artifacts.

---

## PHASE 2 ARCHITECTURE STATUS

**READY FOR ARCHITECTURE REVIEW**
