# SAT-SA Project Specification

**Project:** Supervisory Analytics Tool for SOC Assessment (SAT-SA)  
**Smart India Hackathon:** SIH 2026  
**Problem Statement ID:** 26157  
**Document role:** Master product specification and project source of truth  
**Phase:** Phase 0 — Product Definition  
**Status:** Draft for team review  

---

## 1. Purpose of This Document

This document defines what SAT-SA is, what it must do, what it must not do, and how its outputs must be interpreted. It is the authoritative scope reference for later research, architecture, dataset design, implementation, testing, presentation, and demonstration work.

This is a product specification—not an architecture document, data schema, research report, or implementation plan. Technology and algorithm choices are intentionally left open where further research or experimentation is required.

If a later design or feature conflicts with this specification, the conflict must be resolved explicitly by updating this document rather than silently changing the product scope.

---

## 2. Problem Understanding

NCIIPC receives periodic operational evidence from the Security Operations Centres (SOCs) of Critical Sector Entities (CSEs). Depending on what is available, this evidence may include alert metadata, case-management records, investigation workflows, escalation records, closure or disposition information, asset and system inventories, monitoring evidence, and related operational records.

Manually examining large volumes of evidence across multiple entities is:

- time-consuming;
- resource-intensive;
- difficult to scale;
- difficult to perform consistently;
- vulnerable to important patterns being missed during sampling or manual review; and
- difficult to audit when the reasoning behind review decisions is not recorded consistently.

The intended system assists supervisory examiners by automatically analyzing the available evidence and identifying patterns that may deserve supervisory attention, including:

- execution gaps;
- negative space or missing expected evidence;
- anomalous or unusual behavior;
- significant changes from an entity's own historical behavior;
- significant deviations from suitable peers;
- repetitive or suspicious operational patterns; and
- inconsistencies across related records.

The system must not convert these signals into an automatic judgment of wrongdoing, dishonesty, ineffectiveness, or non-compliance. A finding indicates that the submitted evidence contains a pattern requiring examination. The human examiner remains responsible for supervisory judgment.

### 2.1 Plain-language summary

SAT-SA helps an examiner find where to look first. It turns a large collection of SOC operational records into a prioritized set of explainable findings, shows the evidence supporting each finding, and proposes a focused question for manual investigation.

### 2.2 Treatment of submitted data

Submitted information is treated as **evidence to analyze**, not as unquestionable truth and not as a guaranteed tamper-proof record. SAT-SA may identify inconsistencies, implausible combinations, or missing related evidence. It cannot prove that records were fabricated unless an appropriate trusted source and proof mechanism exist.

The correct language is:

> “The submitted evidence contains a pattern or inconsistency that warrants supervisory review.”

The incorrect language is:

> “The organization fabricated its data.”

---

## 3. Product Definition

SAT-SA is an **offline supervisory analytics tool** that analyzes SOC operational evidence from Critical Sector Entities, identifies evidence-backed patterns requiring supervisory attention, prioritizes findings for manual review, and explains each finding using traceable supporting evidence.

SAT-SA is an analytical assistant for an NCIIPC or other authorized supervisory examiner. Its purpose is to support consistent, scalable, evidence-based review—not to operate a SOC or replace the examiner.

### 3.1 Core product principle

> **Do not merely tell the examiner that something looks unusual. Show why it was flagged, show the evidence, and show where to investigate.**

Every important output must follow this chain:

**Finding → Why flagged → Basis → Evidence → Source records → Investigation question**

### 3.2 Product value

SAT-SA should help an examiner move from manually searching a large volume of records to reviewing a prioritized, evidence-backed shortlist. It should improve focus and consistency without hiding uncertainty or removing human control.

---

## 4. Primary User and Stakeholders

### 4.1 Primary user

**NCIIPC / authorized supervisory examiner**

The primary user reviews operational evidence submitted or made available by CSE SOCs and determines which issues require further examination.

The interface must allow the examiner to understand a finding without needing to understand:

- machine-learning mathematics;
- Python or source code;
- database internals;
- model implementation details; or
- unnecessarily complex cybersecurity terminology.

### 4.2 Supporting stakeholders

Supporting stakeholders may include authorized reviewers, assessment teams, technical analysts, and system administrators. Their exact permissions and workflows will be researched and defined later.

### 4.3 Human authority

The tool supports and prioritizes human supervisory review. It does not replace supervisory judgment.

---

## 5. What We Are Building

The prototype must demonstrate one complete, credible vertical workflow from input evidence to human-reviewable findings.

### 5.1 Data ingestion

The system should be capable of ingesting periodic SOC-related operational evidence such as:

- alert metadata;
- case-management records;
- investigation workflow records;
- escalation records;
- alert disposition and closure records;
- asset and system inventory;
- monitoring or telemetry evidence; and
- remediation or action records, where available.

Potential input mechanisms include:

- CSV files;
- JSON files;
- database exports; and
- APIs where available in a future deployment.

For the prototype, offline/local file ingestion is sufficient. Exact supported formats and schemas will be decided after Phase 1 research and dataset design.

### 5.2 Data validation and preparation

The system should:

- validate supported input structures;
- identify required and optional fields;
- clean and normalize fields;
- parse and standardize timestamps;
- handle missing values explicitly;
- identify duplicate records where appropriate;
- identify structural inconsistencies;
- reject or quarantine invalid records safely;
- create useful analytical features; and
- preserve traceability to original source records.

Data correction must not silently destroy or overwrite original evidence. Transformations should be reproducible and documented sufficiently for review.

### 5.3 Analytical capabilities

SAT-SA should support the following complementary analytical categories:

1. **Expected-behavior and rule-based analysis**  
   Compare available evidence with defined operational expectations or workflow relationships.

2. **Historical and statistical baseline analysis**  
   Compare an entity's current behavior with its own suitable historical behavior.

3. **Peer comparison**  
   Compare an entity with an appropriate, explainable peer group.

4. **Negative-space detection**  
   Identify expected evidence that is absent from the available submissions.

5. **Anomaly and deviation detection**  
   Detect unusual values or combinations not adequately captured by predefined rules.

6. **Repetitive-pattern detection**  
   Identify unusually repeated actions, timings, notes, dispositions, or workflow patterns where useful.

7. **Cross-record consistency checks**  
   Compare related records and identify contradictions, broken links, or unsupported claims.

Machine learning may support these methods but must not become the only analytical method or the final decision-maker.

### 5.4 Candidate finding families

The prototype may identify evidence-backed findings such as:

- critical alerts closed without expected investigation evidence;
- critical alerts without expected escalation evidence;
- unusual closure-time behavior;
- unusual acknowledgement or response-time behavior;
- unusual escalation rates or patterns;
- repeated alerts without apparent remediation evidence;
- repetitive or template-like investigation activity;
- critical assets without expected monitoring evidence;
- missing links among alerts, cases, investigations, escalations, and closures;
- significant deviations from the entity's historical baseline;
- significant deviations from an appropriate peer group;
- unusual workload, assignment, or activity patterns; and
- other reproducible operational anomalies supported by evidence.

This is an illustrative list, not a frozen rule catalogue. Phase 1 research and later analytics design must determine which findings are valid, useful, and demonstrable.

### 5.5 Evidence-backed output

Every material finding must include:

- the finding itself;
- a plain-language explanation;
- the analytical basis;
- relevant calculations or comparisons;
- supporting evidence;
- source-record identifiers;
- relevant timestamp and contextual information;
- uncertainty or limitations where material; and
- a clear investigation question.

### 5.6 Prioritization

The system should provide **Supervisory Attention Priority** or **Priority for Manual Review** so that limited examiner effort can be directed effectively.

Permitted representations include:

- High / Medium / Low attention;
- a transparent review-priority score;
- a prioritized findings queue; and
- prioritized entities based on their unresolved findings.

Prioritization must not be presented as:

- a ranking of organizations from best to worst;
- a ranking of how “bad” organizations are;
- a compliance verdict;
- proof of wrongdoing; or
- an automatic institutional judgment.

Where numerical scores are used, their meaning, components, and limitations must be documented. A score must not be labeled as a probability unless it is actually calibrated and validated as one.

---

## 6. Analytical Basis for Supervisory Attention

A finding may be generated using one or more of the following bases.

### 6.1 A. Expected behavior or rules

The available evidence is compared with a defined operational expectation.

Example:

- A critical alert would normally be expected to have supporting investigation or escalation evidence.
- The submitted records show that the alert was closed, but the expected supporting records are absent.
- SAT-SA flags an execution gap or missing evidence for review.

Rules must be versioned, documented, and configurable where requirements can legitimately vary among entities or contexts.

### 6.2 B. Historical behavior

Current behavior is compared with the same entity's suitable historical baseline.

Example:

- Historical critical-alert closure time is normally measured in hours.
- The current period shows many critical alerts closed within seconds or minutes.
- SAT-SA flags a significant historical deviation and shows the baseline, current value, comparison period, and affected records.

The system must avoid treating every change as suspicious. It should account for sample size, data quality, relevant period, and known contextual differences where possible.

### 6.3 C. Peer comparison

An entity is compared with an appropriate peer group rather than an arbitrary universal average.

Possible peer attributes may include sector, operational scale, asset profile, reporting period, or other defensible characteristics. Exact peer methodology is deferred to research.

A peer deviation is an investigative signal, not proof of poor performance. Every peer-based finding must identify:

- the peer-group definition;
- the metric compared;
- the entity value;
- the peer reference value or distribution;
- the degree of deviation; and
- known limitations of the comparison.

### 6.4 D. Negative space

Negative-space analysis identifies evidence that would reasonably be expected to exist but is absent from the available data.

Examples:

- a critical asset exists, but expected monitoring evidence is absent;
- a critical alert exists, but related investigation evidence is missing;
- a case is closed, but expected escalation evidence is absent;
- repeated alerts exist, but expected remediation evidence is missing.

SAT-SA must distinguish:

- **“The expected evidence is missing from the available submission”** from
- **“We proved the underlying action did not occur.”**

Only the first conclusion is ordinarily supported by missing submitted evidence.

### 6.5 Supporting ML or statistical discovery

Anomaly detection, clustering, similarity analysis, or other local analytical methods may identify unusual patterns that are difficult to encode as fixed rules. These outputs must still be converted into explainable findings with evidence and source-record traceability.

“ML score = 0.91” is not an adequate explanation by itself.

---

## 7. Core Finding Contract

Every important finding must conform conceptually to the following contract.

### 7.1 Required fields

| Field | Requirement |
|---|---|
| Finding ID | Stable identifier for the generated finding |
| Entity | CSE or relevant unit to which the finding relates |
| Finding title | Concise description of the detected pattern |
| Finding category | Such as execution gap, negative space, deviation, anomaly, repetition, or inconsistency |
| Attention priority | Priority for manual supervisory review |
| What happened | Plain-language description of the observed pattern |
| Why flagged | Clear explanation of why the pattern deserves attention |
| Analytical basis | Rule, historical baseline, peer comparison, negative space, statistical method, ML method, or combination |
| Calculation/context | Relevant thresholds, comparisons, counts, rates, distributions, or model contribution information |
| Evidence | Human-readable summary of supporting data |
| Source records | Traceable identifiers/references to underlying records |
| Investigation question | Focused question for the examiner |
| Limitations/uncertainty | Material caveats or data-quality concerns |
| Analysis version | Version of rules, models, and relevant configuration |
| Generated time | Time the analysis produced the finding |

The detailed machine-readable schema will be defined later.

### 7.2 Example

**Finding:** High-severity alerts were closed unusually quickly.  
**Why flagged:** 8 of 10 high-severity alerts were closed within two minutes.  
**Basis:** Historical and peer baseline comparison.  
**Context:** Historical median: 4.2 hours; peer median: 3.8 hours.  
**Evidence:** Alert IDs A102, A103, A107, and related records.  
**Investigation question:** Why were these alerts closed so quickly, and where is the expected investigation or escalation evidence?  
**Limitation:** Closure time alone does not establish that the alerts were handled improperly.

### 7.3 Prohibited output style

The system must not produce unsupported conclusions such as:

- “Organization X is suspicious.”
- “Organization X is dishonest.”
- “Organization X is non-compliant.”
- “The SOC failed.”
- “The data was fabricated.”

Instead, it should say:

> “This pattern requires supervisory attention because…”

---

## 8. Explainability, Traceability, and Auditability

Every finding must be understandable without inspecting source code.

### 8.1 Explainability requirements

The system must expose:

- the reason for detection;
- the analytical method used;
- applicable rule and rule version;
- applicable baseline and comparison period;
- peer-group basis where relevant;
- relevant calculation or contribution information;
- supporting records;
- source identifiers;
- relevant timestamps and context;
- data-quality limitations; and
- the investigation question.

### 8.2 Traceability requirements

The examiner must be able to navigate from:

**Finding → evidence summary → source-record references → available source record**

Processing must retain sufficient lineage to identify where normalized values originated. Later architecture work must define the exact provenance and storage mechanisms.

### 8.3 Reproducibility requirements

Where practical, a finding should be reproducible using:

- the same input snapshot;
- the same rule and model versions;
- the same configuration;
- the same code version; and
- controlled random seeds where stochastic methods are used.

### 8.4 Audit history

The project should preserve analysis metadata and examiner actions needed to explain what was generated, when, and under which analytical version. Exact audit-log design is deferred to architecture and security work.

---

## 9. Human-in-the-Loop Operating Model

The conceptual flow is:

**SOC evidence**  
↓  
**Automated validation and analysis**  
↓  
**Potential findings**  
↓  
**Evidence and explanation**  
↓  
**Priority for manual review**  
↓  
**Human examiner**  
↓  
**Supervisory judgment**

The examiner must be able to:

- inspect a finding;
- inspect supporting evidence;
- understand the analytical basis;
- consider limitations;
- follow an investigation question; and
- make or record a human review decision.

The system does not autonomously determine wrongdoing or regulatory outcome.

Potential examiner feedback workflows—such as confirming, dismissing, annotating, or escalating a finding—are desirable but their exact prototype scope will be decided later.

---

## 10. ML and AI Usage

ML/AI is a supporting analytical layer, not the product's sole decision engine.

### 10.1 Permitted uses

Possible uses include:

- anomaly detection;
- clustering;
- similarity detection;
- repetitive investigation detection;
- unusual combination discovery;
- pattern discovery not covered by explicit rules; and
- prioritization support when transparent and validated.

### 10.2 Required controls

The project should prefer:

- local inference;
- versioned models;
- versioned feature definitions;
- controlled and reproducible training or fitting;
- documented training/fitting data;
- strict separation of training and evaluation data where applicable;
- explainable outputs;
- human validation of newly discovered patterns; and
- controlled model updates.

### 10.3 Prohibited design choices

The core system must not rely on:

- uncontrolled continuous self-learning;
- opaque external AI APIs;
- automatic model updates without validation;
- an ML score as the only reason for a finding;
- data leakage between evaluation and model fitting;
- synthetic ground-truth labels used as if they were detector outputs; or
- a claimed probability that has not been calibrated and validated.

The system must remain useful when ML is inappropriate or unavailable for a particular finding.

---

## 11. Offline and Air-Gapped Operation

Offline operation is a hard product requirement.

The system must be designed for:

- fully offline deployment;
- air-gapped environments;
- local data processing;
- no cloud dependency;
- no SaaS dependency;
- no external AI API dependency;
- no Internet requirement during normal operation; and
- local ML inference where ML is used.

Sensitive SOC evidence must not need to leave the controlled environment for a core feature to work.

Later phases must define installation, dependency packaging, updates, backups, and offline verification. “Offline” must be tested rather than treated only as a marketing claim.

---

## 12. Planned User Experience

The prototype should prioritize clarity and a complete examiner journey over visual complexity.

### 12.1 Dashboard

The dashboard should show useful summary information such as:

- number of organizations analyzed;
- number of records analyzed;
- organizations requiring attention;
- high-priority findings;
- major finding categories;
- data-quality warnings; and
- relevant trends or period comparisons.

Every displayed metric must be computed from actual processed data, not hard-coded or derived from hidden synthetic labels.

### 12.2 Organization list

The organization list should show:

- organization identifier/name suitable for the prototype;
- supervisory attention priority;
- high-priority finding count;
- major finding categories;
- period/context; and
- relevant data-quality status.

It must not imply a definitive good/bad ranking.

### 12.3 Organization view

For each CSE, show:

- supervisory attention priority;
- major findings;
- key indicators;
- historical information where relevant;
- peer-comparison information where relevant;
- data coverage or quality indicators; and
- a path to individual findings.

### 12.4 Finding view

For every finding, show:

- finding title;
- category and priority;
- what happened;
- why it was flagged;
- analytical basis;
- calculations and thresholds where relevant;
- historical or peer comparison where relevant;
- evidence summary;
- source-record identifiers;
- investigation question;
- uncertainty or limitations; and
- analytical version information where useful.

### 12.5 Source evidence view

The examiner should be able to inspect the underlying records supporting a finding, with normalized and original values distinguishable where applicable.

### 12.6 Review workflow

A lightweight human-review workflow may allow findings to be marked or annotated using states such as unreviewed, under review, acknowledged, dismissed with reason, or escalated. Exact statuses and whether they belong in the MVP are to be decided later.

### 12.7 Thirty-second comprehension target

A judge or examiner should be able to understand this path quickly:

**Dashboard → Organization → Finding → Why flagged → Evidence → Investigation question → Source records**

---

## 13. Prototype Dataset Direction

Real NCIIPC and CSE SOC data is not available to the team. A realistic synthetic dataset will therefore be required for prototype development and validation.

### 13.1 Dataset goals

The dataset should represent:

- multiple CSEs;
- multiple reporting periods;
- multiple relevant operational evidence types;
- normal or expected behavior;
- realistic variation among entities;
- known planted execution gaps;
- known planted negative-space scenarios;
- known anomalies and deviations;
- known cross-record inconsistencies; and
- difficult but legitimate cases that test false-positive behavior.

### 13.2 Candidate entities

Possible entities include:

- organizations/CSEs;
- alerts;
- cases;
- investigations;
- escalations;
- closures/dispositions;
- assets/systems;
- monitoring evidence; and
- remediation/action records.

Exact tables, fields, identifiers, relationships, volumes, and distributions must not be frozen in this document. They will be defined in the later data specification after research.

### 13.3 Ground truth

Planted scenarios must be stored separately from ordinary analytical inputs so that:

- detection performance can be evaluated;
- the dashboard cannot accidentally read the answer key;
- false positives and false negatives can be measured; and
- judges can be shown that the system detected known scenarios rather than merely producing arbitrary anomaly scores.

### 13.4 Dataset limitations

Synthetic results do not prove performance on real operational data. All demonstrations and metrics must clearly disclose when synthetic data is used.

---

## 14. Core Demonstration Story

The prototype must demonstrate the complete chain below.

1. **Input** — Offline SOC operational evidence from multiple CSEs is selected or uploaded.
2. **Validation** — The system validates, normalizes, and reports data-quality issues.
3. **Analysis** — Multiple analytical methods examine the evidence.
4. **Detection** — The system identifies execution gaps, negative space, anomalies, inconsistencies, or deviations.
5. **Prioritization** — Findings requiring attention first are surfaced.
6. **Explanation** — The system explains why each finding was raised and the basis used.
7. **Evidence** — Supporting source records and calculations are displayed.
8. **Investigation question** — The examiner receives a focused question to pursue.
9. **Human decision** — The examiner performs the final supervisory assessment.

The preferred showcase scenario is a finding supported by more than one basis—for example, a critical-alert closure pattern supported by an expected-workflow rule, a historical deviation, a peer deviation, and missing investigation records. This is a demonstration preference, not a requirement that every finding use every method.

---

## 15. Success Criteria

Exact numerical targets will be set only after the dataset and implementation have been benchmarked. The project must not claim unrealistic or unmeasured performance.

### 15.1 Functional success

The prototype should demonstrate that it can:

- ingest the supported local data formats;
- validate and normalize supported evidence;
- analyze multiple organizations and periods;
- detect predefined planted scenarios;
- generate evidence-backed findings;
- show why each finding was raised;
- trace findings to source records;
- generate useful investigation questions;
- prioritize findings for manual review; and
- support the intended examiner journey.

### 15.2 Analytical success

Where ground truth exists, evaluation should include:

- precision;
- recall;
- F1 score where appropriate;
- false-positive analysis;
- false-negative analysis;
- results by finding family;
- agreement with planted synthetic scenarios;
- robustness across entities and random dataset seeds; and
- separate reporting for deterministic and ML-supported methods.

Evaluation data must be separated appropriately from fitting or threshold-selection data. Rules and ML results should not be blended in a way that hides weak components.

### 15.3 Explainability success

- Every material finding has a plain-language reason.
- Every material finding states its analytical basis.
- Every material finding has supporting evidence.
- Every material finding is traceable to source records.
- Every material finding includes a useful investigation question.
- Material uncertainty and limitations are visible.

### 15.4 Performance success

Measure and report:

- processing time;
- record volume handled;
- memory and resource usage;
- dashboard responsiveness; and
- behavior under the intended offline environment.

Measured capabilities must replace aspirational claims in later documentation and PPT material.

### 15.5 Deployment success

- Normal operation works without Internet access.
- Core features require no external API or cloud service.
- A clean, documented installation can be reproduced.
- Declared dependencies and supported runtime versions are consistent.
- Offline behavior is tested.

### 15.6 Quality success

- The full automated test suite passes.
- Invalid, missing, duplicate, contradictory, and unusual input cases are tested.
- Documentation matches implementation behavior.
- Dashboard values come from real analytical outputs.
- Known limitations are documented honestly.

---

## 16. Constraints

Known constraints include:

- alignment with SIH Problem Statement 26157;
- offline and air-gapped deployment;
- no external cloud or AI API dependency for core operation;
- explainability and source traceability;
- auditability and reproducibility;
- support for human supervisory judgment;
- scalability to meaningful evidence volumes;
- limited hackathon development and demonstration time;
- limited access to real-world SOC operational data;
- reliance on synthetic data for prototype validation; and
- the need for a solution that the team can understand, demonstrate, maintain, and defend.

No arbitrary performance, scale, accuracy, retention, or security certification requirement is added here without supporting evidence.

---

## 17. Out of Scope

SAT-SA is not:

- a SOC;
- a SIEM;
- a real-time monitoring platform;
- a centralized SOC;
- a continuous telemetry or log-collection system;
- a national cyber-monitoring platform;
- an endpoint detection and response product;
- an automated incident-response system;
- an attacker counterattack system;
- a threat-hunting platform operating on live enterprise networks;
- a cyber-forensics attack-reconstruction platform;
- a guaranteed fraud or fabrication detector;
- an automatic compliance-certification engine;
- an autonomous supervisory decision-maker; or
- a replacement for an NCIIPC examiner.

The system analyzes submitted or otherwise available operational evidence for supervisory assessment.

The following are also outside Phase 0 and are not yet commitments:

- production deployment architecture;
- integration with classified systems;
- finalized database selection;
- finalized UI framework;
- finalized ML algorithm;
- finalized rule catalogue;
- finalized data schema;
- real-world operational certification; and
- legally binding evidentiary or compliance conclusions.

---

## 18. Technology Direction

### 18.1 Confirmed requirements

Regardless of framework, the solution must support:

- offline/local operation;
- no mandatory external service;
- reproducible analysis;
- evidence traceability;
- versioned analytical logic;
- explainable findings;
- secure handling of local inputs;
- testability; and
- a clear examiner-facing interface.

### 18.2 Current implementation preferences

The team currently expects to consider:

- a modular implementation rather than a single monolithic application file;
- open-source components suitable for offline packaging;
- Python-based analytics where appropriate;
- local structured storage suitable for the prototype;
- deterministic rules and statistical analysis before ML;
- local ML methods only where they add demonstrable value;
- a browser-based local dashboard or similarly accessible interface; and
- automated tests, evaluation scripts, and benchmarks from the beginning.

These are preferences, not frozen framework decisions.

### 18.3 To be decided later

Phase 1 research and Phase 2 architecture must decide:

- frontend framework;
- backend framework;
- database/storage engine;
- ingestion adapters and exact formats;
- internal canonical data model;
- exact rule engine design;
- historical-baseline methods;
- peer-group methodology;
- negative-space representation;
- ML algorithms and feature sets;
- finding-priority methodology;
- evidence-lineage mechanism;
- audit-log design;
- authentication and authorization appropriate to the prototype;
- packaging and deployment method; and
- hardware/resource target.

No technology should be selected merely because it is popular or visually impressive.

---

## 19. Security and Data-Handling Principles

Detailed threat modeling is deferred, but the following product principles apply:

- process sensitive evidence locally;
- minimize unnecessary duplication of source evidence;
- validate files and structures before analysis;
- fail safely on malformed or unsupported inputs;
- avoid silently modifying original evidence;
- retain transformation and provenance information;
- separate synthetic ground truth from operational inputs;
- avoid hidden network calls;
- avoid committing sensitive or generated local evidence to version control;
- version analytical rules and models; and
- ensure displayed metrics are derived from traceable calculations.

Security claims must be verified. Terms such as “tamper-proof,” “court-ready,” “immutable,” or “production secure” must not be used without a design and evidence supporting them.

---

## 20. Repository as Source of Truth

The future repository—not a chat transcript or slide deck—will be the durable project source of truth.

Planned specification documents may include:

- `PROJECT_SPEC.md` — product scope and requirements;
- `RESEARCH.md` or `RESEARCH_REPORT.md` — validated domain and competitor research;
- `ARCHITECTURE.md` — approved system architecture;
- `DATA_SCHEMA.md` — canonical evidence and synthetic-data schema;
- `ANALYTICS_SPEC.md` — rules, baselines, models, findings, and prioritization;
- `TEST_PLAN.md` — functional, analytical, security, performance, and offline tests; and
- `README.md` — accurate usage and project overview.

Each later document must remain consistent with this specification or propose an explicit update.

---

## 21. Facts, Decisions, and Open Questions

This section prevents assumptions from silently becoming requirements.

### 21.1 Confirmed by the SIH problem framing available to the team

The following are treated as official problem-level facts, subject to verification against the final official SIH text in Phase 1:

- The problem is SIH 26157, Supervisory Analytics Tool for SOC Assessment (SAT-SA).
- The intended domain is supervisory assessment of SOC operational evidence associated with Critical Sector Entities.
- Manual examination of large evidence volumes creates time, resource, scalability, and consistency challenges.
- The tool is expected to identify patterns such as execution gaps, negative space, anomalies/deviations, and matters requiring supervisory attention.
- Explainability, traceability, and support for human supervisory review are central.
- The tool supports examiner judgment rather than replacing it.
- Offline or air-gapped suitability is required.

**Phase 1 must quote and cite the final official statement precisely and correct this list if necessary.**

### 21.2 Agreed project decisions

The team has intentionally decided that:

- the product will be described as an offline supervisory analytics tool;
- the primary user is an NCIIPC/authorized supervisory examiner;
- the core output contract is Finding → Why → Basis → Evidence → Source records → Investigation question;
- submitted information is evidence to analyze, not unquestionable truth;
- findings indicate supervisory attention, not automatic wrongdoing or non-compliance;
- deterministic and statistical analysis will be built before ML;
- ML will be a supporting layer;
- uncontrolled self-learning will not be used;
- synthetic data with planted scenarios will be used for prototype validation;
- the ground-truth answer key will be isolated from detector and dashboard inputs;
- the prototype will demonstrate a complete vertical workflow;
- the implementation and measured results will become the source for later PPT claims; and
- the repository will be the durable source of truth.

### 21.3 To be validated or researched

The following remain open:

- exact official wording and mandatory deliverables of SIH 26157;
- exact evidence types available in realistic supervisory submissions;
- authoritative expected workflows or control expectations;
- which findings are domain-valid and useful to examiners;
- appropriate historical windows and minimum sample sizes;
- defensible peer-group construction;
- treatment of incomplete reporting periods and data-quality gaps;
- valid thresholds and statistical methods;
- prioritization logic and explainable weighting;
- best local ML methods, if any;
- appropriate evaluation methodology and realistic scale targets;
- privacy, retention, access-control, and audit requirements;
- preferred offline packaging and deployment environment;
- whether a review/feedback workflow belongs in the MVP; and
- terminology that must match NCIIPC practice precisely.

---

## 22. Glossary

### CSE — Critical Sector Entity
An organization or entity in a critical sector whose SOC operational evidence may be reviewed by the supervisory authority.

### SOC — Security Operations Centre
The organizational capability responsible for monitoring, investigating, and coordinating response to cybersecurity events within an entity. SAT-SA assesses available operational evidence; it is not itself a SOC.

### Supervisory Analytics
The use of rules, statistics, comparisons, and supporting analytical methods to help an examiner review operational evidence consistently and at scale.

### Finding
A structured, evidence-backed description of a pattern that may require supervisory attention. A finding is not a final judgment.

### Execution Gap
A difference between an expected operational action or workflow and what is supported by the available evidence.

### Negative Space
The absence of evidence that would reasonably be expected to exist. It indicates a question for review, not proof that the underlying action never occurred.

### Anomaly
A value, behavior, or combination that differs materially from a relevant expectation or baseline. An anomaly is not automatically improper.

### Historical Baseline
A reference describing an entity's own suitable past behavior for comparison with a current period.

### Peer Comparison
A comparison between an entity and a defensible group of similar entities. A difference is a signal for review, not a verdict.

### Supervisory Attention
The need for an examiner to review a pattern, gap, inconsistency, or deviation more closely.

### Supervisory Attention Priority
A transparent indication of where limited manual-review effort should be focused first.

### Evidence Traceability
The ability to follow a finding back through its supporting evidence and references to underlying source records.

### Investigation Question
A focused, neutral question produced for the examiner to pursue when reviewing a finding.

### Human-in-the-loop
An operating model in which automation identifies and explains potential findings while an authorized human makes the final supervisory judgment.

### Analytical Basis
The method supporting a finding, such as an expected-workflow rule, historical baseline, peer comparison, negative-space check, statistical analysis, or ML-assisted anomaly detection.

### Source Record
An underlying submitted or available record referenced as support for a finding.

---

## 23. Acceptance Checklist for This Specification

### Scope

- [x] The project is clearly SAT-SA / SIH 26157.
- [x] The purpose is supervisory analytics.
- [x] The system is explicitly not a SIEM or SOC.
- [x] Unsupported real-time monitoring and forensics scope is excluded.

### Analytics

- [x] Execution gaps are included.
- [x] Negative space is included and carefully defined.
- [x] Historical baselines are included.
- [x] Peer comparison is included with caveats.
- [x] Anomaly detection is included.
- [x] Cross-record checks and repetitive patterns are included.
- [x] ML is supporting rather than magical or authoritative.

### Evidence

- [x] Every material finding must explain itself.
- [x] Supporting evidence is required.
- [x] Source records must be traceable.
- [x] An investigation question is required.
- [x] Reproducibility and analytical versions are required.

### Human control

- [x] The examiner remains the final decision-maker.
- [x] Findings do not automatically declare wrongdoing or non-compliance.

### Deployment

- [x] Offline and air-gapped operation is required.
- [x] Core operation has no external cloud or AI API dependency.

### Product

- [x] Dashboard, organization, finding, and evidence views are defined.
- [x] The primary examiner journey is defined.
- [x] Clarity is prioritized over visual complexity.

### Validation

- [x] A synthetic dataset is planned.
- [x] Known planted scenarios are required.
- [x] The ground-truth answer key is separated from analytical inputs.
- [x] Metrics are planned without fabricated targets.

### Scope control

- [x] No unsupported product category is added.
- [x] No accuracy guarantee is made.
- [x] No automatic judgment of an organization is permitted.
- [x] Architecture and framework choices remain appropriately deferred.

---

## 24. Phase 0 Status

- **Project specification completeness:** Substantially complete for Phase 0 and suitable for team review. The product purpose, scope, boundaries, output contract, user journey, deployment constraint, validation direction, and human-control model are defined. Final acceptance depends on checking the exact official SIH 26157 wording during Phase 1.

- **Major unresolved decisions:**
  - authoritative expected workflows and rule catalogue;
  - canonical evidence model and input schemas;
  - peer-group definition and statistical methodology;
  - finding-priority methodology;
  - exact MVP finding families;
  - role and choice of local ML methods;
  - review-workflow depth;
  - production-relevant security, retention, and access-control requirements;
  - final technology stack and offline packaging; and
  - realistic performance and scale targets.

- **Items requiring research in Phase 1:**
  - final official SIH 26157 requirements and terminology;
  - NCIIPC/CSE/SOC supervisory context that can be supported by public sources;
  - realistic operational evidence types and relationships;
  - evidence-quality and negative-space methodology;
  - defensible execution-gap indicators;
  - historical and peer-comparison practices;
  - existing academic, regulatory, and open-source approaches;
  - publicly visible SIH 26157 competitor capabilities and gaps;
  - explainable anomaly-detection options suitable for offline use;
  - synthetic-data design and evaluation methodology;
  - privacy, security, provenance, and audit requirements; and
  - failure modes that could mislead an examiner.

- **Items intentionally deferred to later phases:**
  - final architecture;
  - full data schema;
  - complete analytics and rule specification;
  - technology/framework selection;
  - implementation and code;
  - UI visual design;
  - model training or fitting;
  - performance optimization;
  - deployment packaging;
  - final README;
  - PPT content and screenshots; and
  - demo script and video.

---

## 25. Next Gate

No architecture or implementation should begin until the team reviews and accepts this specification or records required corrections.

After acceptance, proceed to **Phase 1 — Research** and produce a cited `RESEARCH_REPORT.md`. That report should validate the official problem requirements, domain assumptions, candidate analytics, dataset direction, evaluation plan, competitive baseline, and major risks without yet writing the product implementation.
