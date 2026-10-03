# RESEARCH_REPORT.md

**Project:** SAT-SA — Supervisory Analytics Tool for SOC Assessment  
**Problem:** Smart India Hackathon 2026, Problem Statement 26157  
**Phase:** 1 — Research  
**Document status:** Decision-support research; not architecture, schema, UI, or implementation  
**Research cut-off:** Sources accessed during Phase 1 research

> **Evidence labels used throughout**
>
> - **FACT** — directly supported by a cited source.
> - **RESEARCH FINDING** — conclusion derived by comparing sources.
> - **INFERENCE** — reasonable interpretation not explicitly required by a source.
> - **PROJECT RECOMMENDATION** — proposed SAT-SA decision based on the evidence.

## 1. Executive Summary

### 1.1 Source-confidence note

**FACT:** The official SIH page at `https://sih.gov.in/sih2026PS` was not retrievable during this research because it returned an access-denied response. The most complete wording available was a commit-pinned archive that identifies the official SIH page as its source and a second independent archive containing the same substantive statement.[^S01][^S02] The exact official wording should therefore be rechecked before final submission.

**RESEARCH FINDING:** The two archives agree on the problem description, mandatory functions, offline constraint, validation direction, and deliverables. They disagree on the theme label. The theme is therefore unverified; it has no bearing on the product design.

### 1.2 Strongest conclusions

1. **SAT-SA is a supervisory review aid, not a SOC or SIEM.** The statement explicitly excludes real-time monitoring, continuous telemetry collection, and national monitoring. It asks for periodic operational evidence to be analyzed so human examiners can prioritize review.[^S01]
2. **Evidence must remain inspectable.** Each finding needs its basis, calculations, linked source records, limitations, and analysis version. W3C provenance concepts and NIST guidance support retaining lineage and reproducibility rather than presenting a score alone.[^S15][^S16]
3. **Missing evidence is not proof that an action did not occur.** Negative-space findings must describe an observed evidence gap, the expectation that made the evidence relevant, alternate explanations, and a verification question.
4. **Rules and cross-record checks should form the credible core.** They are reproducible, directly explainable, and map closely to the statement. Robust statistics should support historical and peer deviations. ML should add discovery value only where it can be validated.
5. **Peer comparison is high-risk if definitions differ.** NIST warns that cross-organization incident metrics can be invalid when definitions, tools, and practices differ.[^S05] Peer findings therefore require cohort eligibility, normalized denominators, sufficient sample size, and an “insufficient comparison” outcome.
6. **Synthetic validation alone is insufficient.** It is necessary because operational data is unavailable, but the official statement asks for comparison with expert manual review.[^S01] The project needs planted ground truth **and** blinded human review of a held-out sample.
7. **The competitive baseline is already substantial.** Public SIH 26157 repositories claim deterministic rules, offline execution, evidence drill-down, peer comparison, synthetic validation, tests, and audit trails.[^S30][^S31][^S32] SAT-SA should not differentiate merely by having a dashboard or Isolation Forest.
8. **The most defensible differentiator is an evidence-first review package:** multi-basis finding, explicit expectation, evidence availability, provenance, uncertainty, source rows, and a focused investigation question.

### 1.3 Recommended product direction

**PROJECT RECOMMENDATION:** Build a small end-to-end workflow that ingests structured periodic evidence, validates it, runs 6–8 explainable finding families, distinguishes attention from evidence confidence, and presents a prioritized queue from entity to finding to source record. Use historical and peer statistics only when eligibility conditions are met. Include one lightweight anomaly method and one text-similarity method only if held-out evaluation shows incremental value.

**Do not build:** real-time collection, a SIEM, automatic incident response, a generalized LLM assistant, an opaque composite “cyber risk” score, uncontrolled self-learning, or a production national platform.

---

## 2. Official SIH 26157 Requirements

### 2.1 Provenance and sponsor

**FACT:** The archived statement names the National Technical Research Organisation (NTRO) as the organization and describes NCIIPC’s assessment of the cyber resilience of Critical Sector Entities (CSEs). It identifies human examiners as the final authority.[^S01]

**FACT:** Under the Information Technology Act framework, NCIIPC is the national nodal agency for protection of Critical Information Infrastructure. The 2018 Protected System Rules require documented security governance, inventories, audits, SOC-related processes, and sharing of specified information with NCIIPC as required.[^S03]

### 2.2 Requirement matrix

| Requirement | Exact/source-backed meaning | Implication for SAT-SA | Source |
|---|---|---|---|
| Problem | Manual review of samples of SOC alert and case-management records does not scale consistently across many CSEs | Automate analysis and prioritization, not final judgment | [^S01] |
| Objective | Identify entities needing attention, prioritize samples/investigations, detect operational weaknesses and resilience concerns | Produce review queues at entity and finding/sample levels | [^S01] |
| Intended user | NCIIPC supervisory examiner; human remains authority | Human-in-the-loop review and disposition are core | [^S01] |
| Inputs | Periodic alert metadata, case records, investigation workflow, escalation, closure/disposition, and asset/system inventory where available | Batch structured ingestion; tolerate missing tables and fields | [^S01] |
| Data minimization | Minimize raw logs, packet captures, and customer information | Prefer metadata and linked operational records | [^S01] |
| Formats | Structured multi-CSE ingestion; CSV, JSON, database exports, and APIs where available; multiple periods | MVP should prove CSV/JSON; other adapters can follow | [^S01] |
| Execution gaps | Difference between expected process/control and observed operational evidence | Deterministic workflow and relationship checks | [^S01] |
| Negative space | Expected evidence or activity that is absent or materially lower than expected | Explicit expectation registry and evidence-availability checks | [^S01] |
| Anomalies/outliers | Detect unusual and suspicious operational patterns | Robust statistics first; ML as support | [^S01] |
| Peer benchmarking | Compare entities and operational behavior | Cohort definition, normalized rates, uncertainty, no moral judgment | [^S01] |
| Prioritization | Prioritize entities, controls, processes, and alert samples for review | Do not limit the output to organization ranking | [^S01] |
| Risk indicators | Provide entity-level supervisory risk indicators | Label as supervisory attention indicators, not truth/probability | [^S01] |
| Explainability | Give rationale and supporting evidence for a flag | Finding contract must include “what/why/basis/evidence” | [^S01] |
| Traceability/auditability | Findings must be traceable and auditable | Preserve source references, versions, calculations, and review actions | [^S01] |
| Reporting | Dashboards/reports, trends, and drill-down | MVP needs drill-down; exportable review report is strongly indicated | [^S01] |
| Scalability/performance | Work across multiple entities and large evidence volumes | Benchmark records/time/memory; avoid hard-coded demo data | [^S01] |
| Offline deployment | Fully offline/air-gapped; no internet, cloud, SaaS, external AI, or external APIs; local processing | Package all dependencies/models/data locally | [^S01] |
| AI/ML | ML is optional in effect; if used, document architecture, hardware, offline training/inference, update method, explainability, auditability | No cloud model; no unexplained ML score; version every model | [^S01] |
| Validation | Compare results against expert manual review; aim for comparable or better support than manual sampling | Add blinded manual-review study; synthetic truth is not enough | [^S01] |
| Deployment deliverables | Architecture, functional design, analytics methodology, data requirements, prototype, infrastructure, validation, and estimated deployment/operations | Repository documentation must cover all items | [^S01] |
| Evaluation areas | Supervisory support, execution gaps, negative space, explainability/auditability, scalability/performance, innovation/additional insight | Demonstration and test plan should map directly to these areas | [^S01] |
| Submission artifacts | Source link and README/setup; architecture document up to 2 pages; demo up to 2 minutes; presentation up to 5 slides | Respect artifact limits in later phases | [^S01] |

### 2.3 What is not verified

- The archive shows a “Criterion Weight” heading but no numeric weights. **No weights should be invented.**
- The two archives disagree on the theme label. Confirm it on the official portal.
- No official source reviewed specifies universal thresholds, one mandatory algorithm, a final schema, or one mandated technology stack.

### 2.4 Scope interpretation

**RESEARCH FINDING:** The statement expects a complete supervisory workflow, not just anomaly detection. The unit of value is an examiner-ready, evidence-backed review lead.

**PROJECT RECOMMENDATION:** Map every MVP feature to one of the source-backed requirements above. Treat all additional choices—thresholds, peer method, priority formula, database, model—as project decisions subject to validation.

---

## 3. Supervisory Context

### 3.1 What official sources establish

**FACT:** The Protected System Rules require governance structures, a CISO, documented information-security management, inventories, threat/risk analyses, continuity planning, audit and compliance processes, SOC/NOC capabilities, and sharing of relevant information with NCIIPC where required.[^S03]

**FACT:** The Rules state that a SOC analyzes logs regularly for unauthorized, unusual, and malicious activity and documents records. They also establish processes for sharing SOC records and incident information.[^S03]

**FACT:** NIST incident-response guidance treats preparation, detection, response, and recovery as part of cybersecurity risk management. It identifies incident records, timelines, actions, impact, evidence, and follow-up as useful operational information.[^S04][^S05]

### 3.2 What supervisory assessment is trying to learn

**RESEARCH FINDING:** From periodic operational evidence, an examiner can assess whether submitted records are consistent with claimed processes and whether cases appear to receive proportionate handling. The evidence can reveal indicators of:

- **Detection capability:** whether monitored assets generate alerts and whether expected categories appear.
- **Investigation capability:** whether alerts link to cases, owners, notes, actions, and elapsed investigation time.
- **Escalation discipline:** whether defined conditions lead to escalation and whether timing is plausible.
- **Incident response:** whether serious cases have documented containment/remediation/resolution steps where such records are expected.
- **Operational discipline:** whether timestamps, status changes, assignments, and closures form coherent workflows.
- **Governance/oversight:** whether reviews, approvals, and exceptions are documented consistently.
- **Monitoring coverage:** whether critical assets have submitted evidence of monitoring.
- **Cyber resilience:** indirect evidence of the ability to detect, handle, learn from, and recover from adverse events.

### 3.3 Limits of that interpretation

**INFERENCE:** Operational records are evidence about process execution; they are not a complete measurement of security effectiveness. A low alert count can mean strong prevention, poor detection, limited coverage, different tuning, or incomplete submission. Fast closure can mean automation, duplicates, false positives, or superficial review.

**PROJECT RECOMMENDATION:** SAT-SA should never state “the SOC failed” from one metric. It should state what was observed, the expectation/baseline, evidence quality, plausible alternatives, and what the examiner should verify.

---

## 4. SOC Operational Evidence

### 4.1 Realistic evidence classes

NIST incident records include status, summaries, indicators, related incidents, actions, chain-of-custody information where applicable, impact assessments, contacts, evidence lists, comments, and next steps, with timestamps for each step.[^S05] OCSF provides a vendor-neutral vocabulary spanning findings, incidents, detection findings, event logs, and related activity classes; it is useful as terminology inspiration, not as a mandated SAT-SA schema.[^S17]

| Evidence type | Realistic fields/relationships | What it can tell us | What it cannot prove | Potential SAT-SA use |
|---|---|---|---|---|
| Alert metadata | alert ID, entity, time, severity, rule/source, asset, status, disposition | Volume, mix, timing, recurring patterns, routing | Whether the underlying event was truly malicious | Rates, closure timing, recurrence, workflow linkage |
| Case/incident | case ID, linked alerts, category, priority, owner, status, open/close time | Grouping and lifecycle of response work | Quality of unseen analyst reasoning | Orphan alerts, unsupported closure, lifecycle checks |
| Investigation activity | case/alert link, analyst, action, timestamp, note, sequence | Presence, duration, diversity, handoffs | That every action was technically correct | Missing evidence, repetitive text/sequence, timing |
| Escalation | source/target team, reason, level, time, approval | Escalation occurrence and timeliness | That escalation was required without policy context | Expected-vs-observed checks |
| Disposition/closure | outcome, reason, closer, time, approval | How work concluded and elapsed time | Correctness of disposition | Fast closure, contradiction, approval checks |
| Asset inventory | asset ID, class, criticality, owner, environment, active dates | Denominators and criticality context | Actual telemetry coverage by itself | Negative space and normalized rates |
| Monitoring coverage | asset/source onboarding, enabled dates, health, last evidence | Claimed/observed monitoring footprint | Complete detection efficacy | Critical assets with no evidence |
| Remediation/action | issue/alert link, action, owner, due/completion time, status | Follow-through and repeat-event context | Technical effectiveness without verification | Repeated alerts without remediation evidence |
| Policy/expectation | applicability, trigger, expected step, time objective, exception | Why evidence should exist | That the policy is appropriate or current | Deterministic rule basis |
| Submission manifest | files, periods, entity, counts, hashes, source system/export time | Completeness and provenance of the package | Truth of the source system | Intake validation, duplicate/replay detection |
| Analyst/workforce context | team, shift, role, workload where permitted | Possible workload/shift effects | Individual competence or intent | Confounder analysis only; privacy-sensitive |

### 4.2 Important relationships

The minimum useful chain is not necessarily linear, but should support:

`Entity → Asset → Alert ↔ Case → Investigation activity → Escalation/Action → Resolution → Closure`

with policy expectations, reporting period, and source provenance attached. Many-to-many relationships are realistic: several alerts may form one case, and one alert may be referenced in multiple activities.

### 4.3 Likely quality problems

- missing identifiers or broken foreign keys;
- different severity/status vocabularies;
- timezone ambiguity and impossible ordering;
- duplicated/re-exported records;
- late-arriving updates and reopened cases;
- partial periods and changing source systems;
- free-text notes with boilerplate, redaction, or encoding problems;
- stale asset inventory;
- missing “not applicable” or exception records;
- inconsistent units and timestamp precision;
- selection bias because only submitted evidence is visible.

**PROJECT RECOMMENDATION:** Data-quality status must be first-class. “No submitted evidence,” “not applicable,” “not provided,” “invalid,” and “observed zero” must not collapse into one null value.

---

## 5. Execution Gap Research

An execution gap is strongest when there is an explicit applicable expectation and observable evidence that the workflow diverged. It becomes weaker when “expected” is inferred only from peers.

| Candidate | Detection logic | Required evidence | False positives / limitations | Explainability | Type |
|---|---|---|---|---|---|
| High/critical alert with no investigation | Applicable alerts left-join to investigation/case activity; flag absent qualifying activity after allowance window | Alert, severity mapping, policy/applicability, investigation links, period completeness | Auto-suppression, duplicate alert, action stored elsewhere, late data | Show alert, expected step, window, searched tables/keys | Deterministic |
| Required escalation absent | For trigger conditions, verify escalation record/status within policy window | Trigger rule, case severity/impact, escalation evidence, approved exceptions | Local process may not require escalation; severity changed | Show trigger, policy version, exception status, missing relation | Deterministic |
| Investigation after closure | Detect closure before first/last required investigation step, allowing reopening/version history | Ordered status/activity timestamps | Clock skew, batch migration, legacy timestamp semantics | Timeline with offending times and source values | Deterministic |
| Closure without disposition/reason | Closed status and missing required outcome/approval fields | Case record, workflow rule, exception | Optional fields; migrated historical records | Show required fields and submitted null/absence | Deterministic |
| Repeated alert without remediation evidence | Group recurring alert signature on asset; search linked action/remediation after recurrence threshold | Stable alert signature, asset, recurrence window, remediation link | No remediation required, accepted risk, false positives, duplicate telemetry | Show recurrence timeline and evidence searched | Rule + statistical threshold |
| SLA/timeliness deviation | Compare elapsed stage time with applicable objective and context | Reliable timestamps, pause states, objective, exceptions | Queued states, weekends, priority changes | Show calculation, excluded intervals, objective | Deterministic/statistical |
| Unsupported status transition | Validate observed state sequence against versioned allowed transitions | Event history, workflow version | Source export may contain snapshots only | Show observed and permitted transitions | Deterministic |
| Unassigned serious case | Serious case remains unassigned beyond allowance | assignment history, severity, timestamps | Automated queues or team ownership | Show duration and ownership semantics | Deterministic |

**RESEARCH FINDING:** Deterministic checks produce the clearest evidence but depend on policy applicability and export semantics. A rule without an authoritative expectation is merely a heuristic.

**PROJECT RECOMMENDATION:** Every rule must declare its expectation source, applicability conditions, grace period, exclusions, required fields, and behavior when inputs are incomplete.

---

## 6. Negative Space Research

### 6.1 Responsible model of absence

Negative space requires three things:

1. an **expected universe** (assets, alerts, cases, periods, required reports);
2. a **reason evidence should exist** (policy, declared coverage, workflow, recurring schedule); and
3. a **complete-enough observation window** in which absence can be assessed.

The output must say **“expected evidence was not found in the submitted scope”**, not “the action never happened.”

| Scenario | Expected evidence | Absence test | Alternative explanations | False-positive reduction | Finding wording / examiner question |
|---|---|---|---|---|---|
| Critical asset has no monitoring evidence | coverage/onboarding record or relevant alerts/health events during active period | asset universe anti-join to coverage/evidence universe | dormant asset, recent onboarding, alternate tool, stale inventory | active dates, approved exclusions, source coverage manifest, grace period | “No monitoring evidence was found for 18 active critical assets in the submitted sources. Verify coverage or exclusions.” |
| Alert has no investigation record | linked case/activity for applicable alert classes | relationship anti-join after timing allowance | auto-closed duplicate, suppression, external ticketing, late export | disposition exemptions, reconciliation table, complete-period check | “No qualifying investigation record was found for Alert A… in the submitted case/activity data.” |
| Case has no escalation evidence | escalation when trigger applies | trigger set anti-join to escalation/exception | escalation not required, handled locally, record in another tool | explicit trigger and exception registry | “Escalation evidence was not found despite trigger X; verify applicability and external records.” |
| Repeated serious alerts lack remediation evidence | linked action/accepted-risk record after repeated recurrence | recurrence group anti-join | tuning issue, false positives, compensating control, action not exported | stable signature, recurrence duration, action-source manifest | “Repeated events continued without linked remediation or exception evidence in the submission.” |
| Periodic report/submission absent | expected schedule and manifest entry | expected periods minus submitted periods | approved delay, reporting calendar change | schedule version, receipt time, grace period | “The expected report for period P was not present as of cutoff T.” |
| Expected category unexpectedly absent | historically/peer-supported category with coverage | zero/near-zero count conditional on comparable scope | genuine quiet period, taxonomy change, control improvement | minimum history, volume denominator, source-health check | Phrase as unusual absence, not control failure |

### 6.2 Confidence ladder

- **Strong:** explicit policy expectation + complete period + stable identifiers + no exception.
- **Moderate:** declared operational expectation + largely complete data + corroborating source.
- **Weak:** only historical or peer expectation; source coverage uncertain.
- **Indeterminate:** expected universe or observation completeness is unavailable.

**PROJECT RECOMMENDATION:** Negative-space findings should carry both **attention** and **evidence confidence**. Low completeness should lower confidence or produce a data-quality finding—not silently increase operational risk.

---

## 7. Historical Baselines

### 7.1 Candidate methods

NIST notes that an outlier may be an error or a scientifically meaningful observation and should not simply be discarded.[^S10] Median and median absolute deviation (MAD) are robust to extreme values compared with mean and standard deviation.[^S11]

| Method | Appropriate use | Strength | Limitation |
|---|---|---|---|
| Median | Typical elapsed times and rates with skew | Robust and interpretable | Hides multimodality and seasonality |
| Percentiles | “How extreme relative to history?” | Direct rank interpretation | Unstable at small sample sizes |
| IQR | Rule-of-thumb screening for skewed distributions | Simple and robust | Fixed 1.5× rule is not domain validation |
| MAD / modified z-score | Robust standardized deviation | Less distorted by extremes | Degenerate when MAD is zero; threshold contextual |
| Mean / standard deviation | Stable, approximately symmetric metrics | Familiar and efficient | Sensitive to skew and outliers |
| Rolling baseline | Changing operational regimes | Adapts over time | Can absorb persistent degradation or manipulation |
| Seasonal stratification | Shift/day/week/month effects | Reduces calendar false positives | Needs enough data per stratum |
| EWMA/CUSUM/control chart | Sustained changes and change detection | Sensitive to shifts | Independence/distribution assumptions; tuning needed |
| Change-point method | Process/tool migration or abrupt regime change | Helps separate old/new regimes | Hard to explain and unreliable with sparse history |

### 7.2 When a deviation is meaningful

For “historical closure time is four hours; current is two minutes,” a credible flag requires:

- enough current and historical observations for the relevant class;
- the same metric definition and timestamp semantics;
- comparable severity, disposition, asset context, and reporting coverage;
- no known automation, migration, or workflow change that explains the shift;
- a robust effect-size statement (not only a p-value);
- source rows showing whether the shift is broad or caused by duplicates;
- explicit uncertainty when the sample is small.

**RESEARCH FINDING:** There is no source-backed universal minimum sample size or closure-time threshold for all SOCs. Statistical power depends on distribution and effect size; domain interpretation depends on workflow.

**PROJECT RECOMMENDATION:** Architecture should support configurable eligibility rules. For the prototype, pre-register conservative minimum sample sizes by metric through simulation and held-out validation rather than asserting a universal standard. If not met, display “insufficient history.”

---

## 8. Peer Comparison

### 8.1 Defensible cohort construction

Possible eligibility variables are:

- sector/subsector;
- reporting period and duration;
- alert/case definitions and severity mapping;
- organization or monitored-asset scale;
- alert volume/exposure denominator;
- operational model (24×7 vs business hours; centralized vs distributed);
- source-system coverage and data completeness;
- asset criticality mix;
- workflow/taxonomy version.

**FACT:** NIST cautions that incident metrics across organizations can be invalid because definitions, tools, and practices differ; absolute counts alone are not informative.[^S05]

### 8.2 Candidate comparison methods

| Method | Use | Advantages | Risks |
|---|---|---|---|
| Normalized rate | escalations per eligible critical alert; investigations per applicable alert | Controls for volume | Denominator quality is decisive |
| Percentile rank | position within eligible cohort | Easy to explain | Coarse/unstable with few peers |
| Robust z-score | deviation from peer median/MAD | Resistant to extreme peers | Fails with zero MAD/small cohorts |
| Distribution display | show entity and cohort spread | Avoids one-number judgment | Needs careful UX |
| Stratified benchmark | compare within matched attributes | More defensible | Small cells and sparse data |
| Regression/residual | adjust for scale/mix | Handles several covariates | Harder to validate/explain; not MVP-first |

### 8.3 Responsible communication

“Different” does not mean “bad.” It can reflect better automation, different risk, incomplete data, distinct policy, or a mismatch in cohort.

**PROJECT RECOMMENDATION:** A peer-based finding must show: peer eligibility criteria; number of peers; denominator; cohort distribution; entity value; period; data-quality differences; and the phrase “deviation requiring context,” not “poor performance.” Never silently fall back from a small matched cohort to all entities.

---

## 9. Anomaly / ML Research

### 9.1 Method comparison

Scikit-learn distinguishes **outlier detection** (training data may contain anomalies) from **novelty detection** (fit on a clean baseline, then evaluate new observations). It also warns that unsupervised high-dimensional outlier detection is difficult.[^S12]

| Method | Strength | Weakness | Explainability | Offline suitability | Data requirement | SAT-SA usefulness |
|---|---|---|---|---|---|---|
| IQR | Transparent, robust, trivial to reproduce | Univariate; heuristic cutoff | High | Excellent | Modest per group | Strong baseline |
| Modified z/MAD | Robust standardized magnitude | Zero MAD; univariate | High | Excellent | Modest | Strong baseline |
| Control chart/EWMA | Detects sustained temporal shifts | Assumptions and tuning; serial correlation | Medium-high | Excellent | Ordered history | Useful after baseline maturity |
| Isolation Forest | Efficient multivariate isolation; works offline | Score/contamination is not probability; feature scaling/context | Medium with feature values + local comparisons | Excellent | Enough representative rows | Supporting detector |
| Local Outlier Factor | Detects local-density anomalies | Default mode does not score unseen data; sensitive to neighbors/scaling | Medium-low | Excellent | Dense comparable neighborhood | Exploratory/optional |
| DBSCAN | Finds density clusters and noise without cluster count | Parameter sensitivity; weak in high dimensions; memory can grow | Medium | Good | Meaningful distance and density | Exploration, not core MVP |
| k-means distance | Simple cluster deviation | Assumes cluster geometry; forces membership | Medium | Excellent | Scaled numeric features | Limited |
| Autoencoder | Flexible nonlinear representation | Large data, training/tuning, weak explanations, reconstruction error ambiguity | Low | Possible but costly | Large stable data | Not justified for MVP |

### 9.2 NLP and similarity

| Method | Strength | Weakness | Explainability | Recommendation |
|---|---|---|---|---|
| Exact normalized match | Directly shows identical text | Misses paraphrase; boilerplate may be legitimate | Very high | Must-have baseline |
| Token/character n-gram + TF-IDF cosine | Lightweight, offline, reveals shared terms | Short notes/noisy templates; threshold tuning | High if matched passages shown | Preferred MVP similarity method |
| MinHash/locality-sensitive hashing | Scales near-duplicate search | Approximate and less intuitive | Medium | Useful at larger scale |
| Embeddings | Semantic similarity beyond wording | Model packaging, domain fit, explanation, validation | Medium-low | Nice-to-have only after evidence |
| Large language model | Rich semantic analysis | Offline footprint, hallucination, reproducibility, security | Low without controls | Not needed for core prototype |

Scikit-learn documents sparse bag-of-words/TF-IDF representations and their limits, especially for short text.[^S14]

### 9.3 Recommendation

**PROJECT RECOMMENDATION:** Start with rules, MAD/IQR/percentiles, and explicit baselines. Add Isolation Forest only on carefully defined entity-period features and report it as a supporting anomaly lead. Do not blend it invisibly into a risk score. For notes, use normalization, exact duplicates, TF-IDF cosine, and cluster exemplars before embeddings.

---

## 10. Evidence & Explainability

### 10.1 What an examiner needs

NIST’s AI RMF treats validity/reliability, transparency, explainability, accountability, human oversight, and data quality as related risk-management concerns.[^S16] W3C PROV-O defines a general provenance model around entities, activities, and agents.[^S15]

For every finding, the examiner should see:

1. **Finding:** concise observation, entity, period, affected scope.
2. **Why:** the unusual or missing behavior.
3. **Basis:** rule/policy, historical distribution, peer cohort, statistical/model method.
4. **Calculation:** formula, denominator, exclusions, current and reference values.
5. **Evidence:** linked records, timestamps, fields, and relation path.
6. **Source record:** original submitted value or immutable snapshot reference.
7. **Provenance:** file/export, ingestion run, normalization mapping, analysis version.
8. **Uncertainty:** missing fields, sample-size status, alternate explanations.
9. **Question:** a neutral verification prompt.
10. **Review history:** reviewer, disposition, note, and time.

### 10.2 Reproducibility contract

A finding should be reproducible from:

- source-file hash and manifest;
- parser/mapping version;
- rule/model and configuration version;
- analysis run identifier and timestamp;
- feature values and random seed where relevant;
- peer/history membership snapshot;
- exact evidence record identifiers.

A cryptographic hash detects later alteration of the received artifact; it does **not** prove the artifact was truthful when submitted.

### 10.3 Explanation by analytical type

- **Rule:** applicable expectation, observed condition, exception test.
- **Historical:** current metric, window, sample sizes, median/percentile/MAD, effect size.
- **Peer:** cohort definition, cohort size/distribution, normalized entity value.
- **ML:** feature vector, model/version, score threshold, nearest contextual examples or feature-level contribution where valid; state that the score is not probability.

**PROJECT RECOMMENDATION:** Implement the conceptual chain `Finding → Why → Basis → Calculation → Evidence → Source` as a non-negotiable product contract.

---

## 11. Finding Prioritization

### 11.1 Research basis

NIST incident handling recommends prioritization based on functional impact, information impact, and recoverability rather than first-come order.[^S05] SAT-SA’s queue is different—it prioritizes supervisory review—but the same principle supports explicit risk-relevant factors rather than arbitrary order.

### 11.2 Candidate factors

- affected asset/process criticality;
- severity and number of affected records;
- recurrence and persistence;
- deviation magnitude;
- number of independent analytical bases;
- evidence strength and source completeness;
- cross-record contradiction;
- scope/coverage affected;
- uncertainty and data-quality limitations;
- novelty relative to prior reviewed findings.

### 11.3 Avoiding a false “truth score”

**RESEARCH FINDING:** A single additive score can hide compensation: a large anomaly may overwhelm weak evidence, or several correlated signals may be counted repeatedly.

**PROJECT RECOMMENDATION:** Use a transparent review-priority policy with visible factor contributions and guardrails:

- distinguish **attention level** from **evidence confidence**;
- cap or group correlated signals that share the same records/root cause;
- require minimum evidence for High/Critical queue placement;
- keep “data unavailable” separate from “observed poor behavior”;
- allow examiner override with reason;
- display priority as “review earlier,” never likelihood of wrongdoing.

A lexicographic or banded policy may be safer than a pseudo-precise 0–100 score. Exact weights remain an architecture/validation decision.

---

## 12. Cross-Record Consistency

| Check | Logic | Reasoning type | Caveat |
|---|---|---|---|
| Broken reference | case references missing alert/asset; activity references missing case | Deterministic | Export may intentionally omit historical parent |
| Impossible time | close < open; escalation < alert; action outside active period | Deterministic | timezone, clock skew, migration |
| Contradictory state | alert “investigated” but no qualifying activity; case “closed” and active | Deterministic with semantics | snapshots vs event history |
| Unsupported closure | closed serious case lacks disposition/approval required by policy | Deterministic | exceptions or external workflow |
| Duplicate record | same source key/hash or near-identical event | Deterministic/statistical | legitimate re-open/replay |
| Severity inconsistency | alert/case severity conflicts unexpectedly | Rule/statistical | legitimate re-triage |
| Asset mismatch | linked records point to inconsistent entity/asset | Deterministic | aliases/mergers |
| Unusual fan-in/fan-out | many alerts to one case or many cases per alert beyond normal | Statistical | alert storms or campaign grouping |
| Sequence anomaly | investigation steps repeated or skipped relative to workflow | Deterministic/statistical | process variants |

**PROJECT RECOMMENDATION:** Run basic relational and temporal checks before higher-level analytics. Findings based on invalid timestamps or broken joins must be blocked or marked low-confidence.

---

## 13. Repetitive Investigation Analysis

### 13.1 Detection sequence

1. normalize Unicode, whitespace, case, boilerplate IDs, and approved redactions;
2. preserve original text separately;
3. exact-match normalized notes;
4. compute character/token n-gram TF-IDF and cosine similarity;
5. cluster only within comparable case type/time/analyst context;
6. show representative text and differing tokens;
7. compare repetition rate with legitimate templates and historical behavior.

### 13.2 Non-text repetition

Also examine identical action sequences, equal stage durations, repeated dispositions, and recurring alerts handled with the same minimal sequence.

### 13.3 Interpretation limits

Repetition can be legitimate: runbooks, regulatory wording, automated enrichment, standard false-positive dispositions, or bulk incidents. It becomes more informative when combined with implausibly short handling, missing evidence, broad case diversity, or recurrence without remediation.

**PROJECT RECOMMENDATION:** Phrase the result as “possible template-driven investigation pattern” and ask whether the repeated content reflects an approved runbook and whether case-specific evidence exists.

---

## 14. Synthetic Dataset Research

### 14.1 Purpose and non-purpose

A synthetic dataset enables controlled ground truth, repeatability, scale tests, and safe demos. It does not establish production accuracy or operational realism. Public implementations themselves acknowledge that synthetic success can be circular when generation and rules share assumptions.[^S30][^S31]

### 14.2 Recommended design principles

- multiple entities across at least three peer contexts;
- several reporting periods, including a process-change boundary;
- linked assets, alerts, cases, activities, escalations, actions, closures, and manifests;
- skewed/long-tailed elapsed times and heterogeneous alert rates;
- missing values, duplicates, late arrivals, timezone differences, schema drift, and broken links;
- ordinary cases, planted concerning cases, and **legitimate unusual cases**;
- separate generation logic from detection logic where feasible;
- ground truth in a protected evaluation artifact, not visible to the analytics engine;
- held-out seeds/scenarios and a blind review subset;
- explicit provenance for every planted mutation.

### 14.3 Candidate scale—not a final decision

**PROJECT RECOMMENDATION:** Evaluate a prototype target around 12–20 entities, 4–6 periods, and tens of thousands of alerts with proportionate cases/activities. Cohorts should ideally contain at least five eligible entities for a basic peer demonstration. Maintain a smaller deterministic fixture for tests and a larger benchmark set. These are planning ranges, not official requirements or validated capacity targets.

### 14.4 Scenario matrix

| Scenario | Concerning version | Legitimate unusual control case |
|---|---|---|
| Fast closures | many serious alerts closed with no investigation | duplicate sensor storm auto-suppressed under approved rule |
| Low escalation | applicable serious cases lack escalation | local process changed with approved exception |
| Repetitive notes | near-identical notes across diverse cases, no specifics | standard runbook text plus case-specific evidence |
| Coverage gap | active critical assets have no monitoring record | decommissioning/onboarding grace period documented |
| Low alert volume | abrupt unexplained drop with source-health gaps | real maintenance window or improved filtering with records |
| Repeated alerts | recurrence without action/exception | known accepted risk with approved compensating control |
| Broken timing | widespread impossible timestamp sequence | timezone migration with documented conversion issue |

### 14.5 Avoiding an easy dataset

Randomly label rows after generation; inject overlapping signals; vary prevalence; include ambiguous examples; keep benign and concerning distributions partially overlapping; alter field names/formats across submissions; and assess each finding family independently. A detector must not receive hidden scenario labels as features.

---

## 15. Evaluation Methodology

### 15.1 Detection performance

Use held-out ground truth by finding family:

- precision, recall, and F1;
- false-positive and false-negative counts with case review;
- confusion matrix;
- performance by entity, severity, period, and data-quality condition;
- deterministic and ML-supported findings reported separately.

Scikit-learn documents these classification metrics and their trade-offs.[^S18] Aggregate metrics must not hide a weak high-impact finding family.

### 15.2 Ranking/prioritization

- precision@k and recall@k for the top review queue;
- relevant-finding yield per N records reviewed;
- proportion of planted high-impact cases surfaced before a review budget is exhausted;
- review-effort reduction relative to random/manual sampling;
- stability across seeds and periods.

Precision at a cutoff is useful for ranked retrieval but depends on the cutoff and relevant-set size, so it should not stand alone.[^S19]

### 15.3 Explainability and evidence

Measure:

- evidence completeness: required finding fields present;
- valid source links and relationship paths;
- deterministic reproduction of calculations;
- agreement between displayed explanation and actual logic;
- examiner understanding: can a reviewer identify why it was flagged and the next verification step?

### 15.4 Performance

Report records/files/entities processed, wall-clock time, peak memory, artifact size, and hardware/software environment. Test at multiple scales. Do not predeclare a target that has not been benchmarked.

### 15.5 Human evaluation

The official statement asks for comparison with expert manual review.[^S01] Recommended protocol:

1. define a held-out sample and review rubric;
2. have at least two knowledgeable reviewers independently assess it where feasible;
3. blind reviewers to planted labels/system ranking initially;
4. compare agreement and identify disagreements;
5. then provide SAT-SA findings and measure decision time, usefulness, evidence trust, and changed conclusions;
6. document limitations—students or developers are not substitutes for NCIIPC examiners.

### 15.6 Validation hierarchy

1. unit/fixture correctness;
2. synthetic held-out ground truth;
3. independent implementation/recalculation of selected findings;
4. expert/manual review comparison;
5. pilot on de-identified representative operational exports, if access becomes possible.

---

## 16. Existing Solutions / Competitive Research

Repository descriptions and test counts below are **maintainer claims observed in documentation**, not independently executed validations in this research phase.

| Solution | Approach / key features | Evidence & explainability | ML | Offline | Limitations observed | Possible SAT-SA differentiation |
|---|---|---|---|---|---|---|
| SOCRIX | Deterministic indicators, DuckDB, peer scoring, review packs, hashes/audit | Source rows, evidence completeness, explanations | Rules/statistics; no ML judge | Claimed | Synthetic results; pilot needed | Richer expectation/absence confidence; human validation protocol | 
| Charan SAT-SA | Multi-table ingestion, execution/negative-space rules, peer analysis, queue/reports, extensive tests | Deterministic authoritative layer, evidence views | Optional local LLM rephrasing only | Claimed | Explicitly notes synthetic circularity and lack of independent expert validation | Demonstrate blind review, multi-basis lineage, calibrated uncertainty |
| Mohit SAT-SA | Execution gap, peer negative space, Isolation Forest, risk dashboard, audit/reporting | Drill-down and manual review workflow | Isolation Forest | Claimed | Small synthetic benchmark; composite risk interpretation needs scrutiny | Separate attention/confidence; deeper cross-record and negative space |
| 20johan SAT-SA | React/FastAPI/PostgreSQL/Docker stack | Public README provides limited analytical detail | Unclear | Container-oriented | Sparse public methodology/validation detail | Evidence contract and published methodology |
| VETAILS | Python analytics, Node/Vite, SQLite; testing/documentation claims | Points to project docs | Unclear from top-level overview | Claimed/local stack | Requires deeper execution audit | Reproducible analytical package and examiner-centric validation |

Sources: [^S30][^S31][^S32][^S33][^S34]

### 16.1 Competitive baseline

**RESEARCH FINDING:** The following are not novel by themselves: an offline dashboard, seeded synthetic anomalies, simple execution-gap rules, peer z-scores, Isolation Forest, source-row drill-down, report export, and an audit log.

**RESEARCH FINDING:** Public projects reveal the hardest unsolved credibility gaps: independent expert validation, circular synthetic evaluation, defensible peer construction, and honest uncertainty about missing data.

---

## 17. Differentiation Opportunities

| Opportunity | Evidence of value | Competitive gap | Recommendation |
|---|---|---|---|
| Evidence-first finding contract | Official explainability/auditability; provenance standards | Competitors claim evidence views, but depth varies | Make every finding reproducible and source-linked |
| Expectation-aware negative space | Core official requirement | Many demos reduce it to low counts/missing joins | Show expected universe, applicability, completeness, alternatives |
| Separate attention and confidence | NIST AI/data-quality principles | Composite scores can obscure uncertainty | Two-axis queue and explicit insufficient-evidence state |
| Multi-basis correlation without double counting | Official asks multiple analytic types | Common systems list independent alerts | One case package combining rule/history/peer/absence evidence |
| Neutral investigation questions | Human remains authority | Often absent or generic | Generate templated, method-specific verification prompts |
| Ground-truth plus legitimate anomalies | Synthetic circularity acknowledged by competitors | Seeded tests often make anomalies obvious | Include confounders and benign unusual scenarios |
| Blind expert/manual comparison | Official validation direction | Public repos acknowledge no expert validation | Run documented small human evaluation |
| Controlled analytical versioning | Auditability and offline operation | Sometimes only code version/audit log | Snapshot config, rule/model, cohorts, and provenance |

**PROJECT RECOMMENDATION:** Position differentiation as better evidence discipline and evaluation—not as “more AI.”

---

## 18. Failure Modes & False Positives

| Failure | Why it causes a false signal | Detection / mitigation | Remaining limitation |
|---|---|---|---|
| Incomplete submission | Missing links look like absent action | manifests, expected counts, source coverage, completeness score | Source can overstate completeness |
| Missing/renamed fields | Rules silently fail or map wrongly | strict schema checks, mapping report, quarantine | Semantic mismatch may remain |
| Partial/late period | recent alerts have no downstream records yet | cutoff and maturation window | Long delays vary by workflow |
| Legitimate process change | history shift appears anomalous | change log, split baseline, reviewer context | Undocumented changes remain |
| Seasonality/shift effects | volumes and timing change by calendar | stratify or compare like periods | Sparse strata |
| New SOC/source tool | identifiers/status/timestamps change | source-version metadata and migration flag | Incomplete migration docs |
| Merger/asset changes | denominators and ownership jump | effective dates, entity/asset lineage | Alias resolution is difficult |
| Low sample size | unstable percentiles/z-scores | eligibility thresholds and “insufficient data” | Small entities may lack benchmarking |
| Peer mismatch | normal operating difference appears poor | matched cohort and visible criteria | True comparability is imperfect |
| Duplicate/replayed data | inflates volume/recurrence and compresses timing | source keys, hashes, near-duplicate checks | Legitimate repeated alerts can resemble duplicates |
| Alert storm/emergency | rapid bulk handling looks superficial | incident/campaign grouping and declared event context | Context may be missing |
| Automation | fast closures and repetitive notes look suspicious | automation marker, rule/version, disposition context | Automation can still be poorly governed |
| Approved exception | “missing” escalation/remediation | exception evidence and validity period | Exceptions may not be exported |
| Missing telemetry | low alerts interpreted as good or bad | source-health/coverage evidence | True blind spots may be indistinguishable |
| Analyst workload/leave | delays interpreted as process failure | shift/workload aggregates where lawful | Privacy and availability constraints |
| Policy ambiguity | arbitrary expectation drives rule | versioned expectation registry and owner | No authoritative policy available to prototype |
| Model contamination | anomaly model learns bad pattern as normal | held-out baseline, versioning, drift review | Unsupervised ground truth remains weak |
| Threshold overfitting | seeded anomalies always detected | held-out seeds/scenarios and sensitivity analysis | Synthetic-to-real transfer uncertain |
| Reviewer automation bias | high priority treated as truth | uncertainty language, evidence-first UX, override reasons | Human bias cannot be eliminated |

**PROJECT RECOMMENDATION:** Maintain a “limitations and alternative explanations” panel per finding, not only in documentation.

---

## 19. Security & Privacy

### 19.1 Threat model

Inputs may be sensitive and untrusted. Risks include malicious archives/files, formula injection, parser exploits, path traversal, oversized/decompression-bomb files, tampered models/rules, sensitive logs, unauthorized local access, and accidental repository inclusion.

OWASP recommends allowlisted extensions, independent type/signature checks, safe filenames, size controls, and isolated storage for uploads.[^S21] OWASP logging guidance emphasizes access/integrity controls and avoiding unnecessary sensitive data in logs.[^S28] NIST SSDF supports integrating secure-development practices throughout the lifecycle.[^S20]

### 19.2 Recommended controls for later design

- local authentication/role separation appropriate to deployment;
- least-privilege file handling and read-only source preservation;
- allowlisted CSV/JSON/approved archives; reject active content by default;
- archive entry/path/size/count and decompression-ratio limits;
- strict parsers, row/field limits, encoding handling, formula neutralization on export;
- content hashes, signed/versioned rules/models/packages where feasible;
- provenance and append-only audit semantics with protected access;
- no raw note/body content in routine logs;
- configurable retention and secure deletion policy;
- dependency inventory, pinned versions, offline vulnerability-review/update process;
- backups and tested recovery for analysis state.

**INFERENCE:** Final access-control and retention requirements depend on NCIIPC deployment policy and cannot be invented from the public problem statement.

---

## 20. Offline Deployment

### 20.1 Candidate approaches

| Approach | Advantages | Limitations | Best fit |
|---|---|---|---|
| Source + pinned wheelhouse | Transparent, reproducible Python environment; pip documents local wheelhouse installs | OS/architecture-specific wheels; operational complexity | Technical evaluator / controlled Linux host |
| Packaged desktop executable | Simple user launch, no runtime setup | Packaging size, platform-specific builds, update/signing complexity | Single workstation demo/deployment |
| OCI/container bundle | Reproducible filesystem and dependencies; images can be saved/loaded offline | Runtime may be prohibited; platform image concerns | Approved server/workstation environment |
| Prebuilt VM/appliance | Strong isolation and predictable stack | Large artifact, patching and hypervisor dependency | Strict enterprise deployment |

Pip recommends pinning transitive dependencies and can install from an offline wheelhouse; wheelhouses are OS/architecture-specific.[^S22] Docker supports saving and loading image archives, including selected platforms.[^S26][^S27]

### 20.2 Update and integrity process

An offline package still needs controlled updates:

1. build in a controlled connected environment;
2. generate dependency/model/rule inventory and hashes/signatures;
3. malware/vulnerability review;
4. transfer through approved media/process;
5. verify integrity before installation;
6. record installed version and rollback artifact;
7. test migration and reproducibility.

**PROJECT RECOMMENDATION:** Select the deployment mode only after target OS/runtime constraints are confirmed. “Works without network after installation” is not enough; installation, update, model packaging, and help assets must also be offline.

---

## 21. High-Level Technology Research

This section compares candidates; it does **not** select the final architecture.

### 21.1 Processing and analytics

- **Python/pandas or Polars:** mature data preparation and statistics; easy testing. Polars may improve columnar scale, but team familiarity matters.
- **DuckDB:** embedded, columnar analytical SQL, serverless operation, and single-file persistence; suitable for local batch analytics.[^S23]
- **SQLite:** embedded transactional store, serverless and single-file; well suited to review state, settings, and small relational workloads.[^S24]
- **scikit-learn/SciPy/statsmodels:** offline statistical/ML ecosystem. Every chosen dependency must be packaged and versioned.

A future architecture could use one engine or separate analytical and transactional stores. The research does not justify freezing that choice yet.

### 21.2 User interface candidates

- local web application: strong dashboard/drill-down capability, but must bind locally and package all assets;
- desktop wrapper: easier single-app distribution, more packaging/platform work;
- Python dashboard framework: fastest prototype, but long-term UX/testing constraints;
- React or similar frontend + local API: richer UX, larger dependency and build surface.

### 21.3 Testing and browser automation

Candidate tools include pytest for analytical/unit tests, property-based tests for invariant-heavy transformations, and Playwright for local browser flows. Benchmark scripts must report environment and deterministic dataset seed.

### 21.4 High-level processing pattern

`Input → Quarantine/Validation → Normalization → Quality/Provenance → Analytics → Finding/Evidence package → Prioritization → Examiner review/report`

This is a research pattern, not the final component diagram.

---

## 22. Recommended MVP

### MUST HAVE

1. Offline CSV and JSON ingestion for multiple entities and periods.
2. Manifest, schema, relationship, timestamp, duplicate, and completeness validation.
3. Canonical normalized evidence mapping with retained source values/provenance.
4. Six to eight finding families:
   - serious alert with no qualifying investigation evidence;
   - required escalation evidence absent where applicability is explicit;
   - unusually fast closure using history and/or matched peers;
   - critical asset with no submitted monitoring evidence;
   - repeated serious alerts without linked remediation/exception evidence;
   - broken relationships/impossible timelines/contradictory states;
   - repetitive investigation text or sequence;
   - one multivariate anomaly lead, only if validated.
5. Separate attention level, evidence confidence, and data-quality status.
6. Transparent entity/finding queue with factor explanations.
7. Finding detail: why, basis, calculation, evidence, source records, limitations, question.
8. Historical and peer eligibility with “insufficient data” outcomes.
9. Versioned analysis run and review audit history.
10. Synthetic held-out evaluation with legitimate unusual controls.
11. Exportable examiner review package/report.
12. Documented fully offline start-to-finish demo.

### SHOULD HAVE

- database-export adapter;
- trend view across periods;
- exact/TF-IDF note clusters with exemplars;
- configurable expectation/rule registry;
- independent recalculation of selected findings;
- blinded human review mini-study;
- batch performance benchmark and integrity manifest.

### NICE TO HAVE

- embedding-based note similarity after offline validation;
- advanced change-point detection;
- multiple pluggable source mappings;
- container and desktop packaging variants;
- local-only natural-language rephrasing that cannot alter evidence or decisions.

### Explicitly defer

Real-time ingestion, SIEM functions, live threat hunting, automated response, universal risk prediction, cloud services, external LLMs, autoencoders, and uncontrolled model updating.

---

## 23. Recommended Demo Scenario

### 23.1 Story

1. Examiner imports evidence from several CSEs and four reporting periods.
2. SAT-SA verifies package hashes/manifests and reports one partial source and several mapping issues.
3. Analytics produce an entity/finding queue. The UI clearly separates attention priority from evidence confidence.
4. Examiner opens a high-priority finding for a CSE: **critical alerts closed unusually quickly with missing investigation evidence**.
5. The page shows:
   - 8 of 10 applicable critical alerts closed within two minutes;
   - historical median and distribution for comparable alerts;
   - matched peer distribution and cohort definition;
   - missing linked investigation records for six alerts;
   - rule, baseline, peer, and source-data versions;
   - exact alert/case rows and timeline;
   - caveats (automation marker absent; period complete; sample size eligible);
   - neutral question: “Were these alerts closed by an approved automated workflow, and where is the corresponding investigation or exception evidence?”
6. Examiner opens a similar-looking **legitimate unusual** case. Approved duplicate suppression and exception evidence lower its priority/confidence of concern.
7. Examiner records a disposition and exports a review package.

### 23.2 Why this scenario is strong

It demonstrates ingestion, validation, execution gap, negative space, historical and peer comparison, provenance, uncertainty, false-positive control, prioritization, and human judgment in one short workflow. It does not require claiming that SAT-SA proved misconduct.

---

## 24. Recommended Decisions

### 24.1 MVP scope

**Decision:** What must the prototype prove?  
**Recommendation:** One complete examiner workflow with 6–8 explainable finding families and source drill-down.  
**Evidence:** Official focus on supervisory support, prioritization, explainability, and auditability.[^S01]  
**Reason:** Breadth without evidence depth is less credible.  
**Confidence:** High.  
**Uncertain:** Exact final finding count after data experiments.

### 24.2 Analytics methods

**Recommendation:** Deterministic relationship/workflow checks first; robust statistics second.  
**Evidence:** Direct mapping to execution gaps/negative space; NIST robust-outlier cautions.[^S10][^S11]  
**Confidence:** High.  
**Uncertain:** Thresholds and eligibility sizes.

### 24.3 Anomaly methods

**Recommendation:** Consider Isolation Forest as a supporting lead; evaluate against MAD/IQR and ablate it from results. Do not use autoencoders in MVP.  
**Evidence:** Offline efficiency and documented limitations of unsupervised detection.[^S12]  
**Confidence:** Medium.  
**Uncertain:** Whether it adds incremental precision/recall on realistic data.

### 24.4 Negative-space strategy

**Recommendation:** Model expected universe, applicability, observation completeness, exceptions, and searched evidence sources.  
**Evidence:** Official definition plus missing-data risks.[^S01]  
**Confidence:** High.  
**Uncertain:** Authoritative expectations available in real deployments.

### 24.5 Peer comparison

**Recommendation:** Matched cohorts, normalized rates, robust distributions, minimum cohort eligibility, no global fallback.  
**Evidence:** NIST cross-organization comparability warning.[^S05]  
**Confidence:** High.  
**Uncertain:** Which grouping variables will exist in submitted data.

### 24.6 Historical baselines

**Recommendation:** Median/percentiles/MAD, period comparability, rolling or stratified windows only when enough history exists.  
**Evidence:** Robust-statistics guidance.[^S10][^S11]  
**Confidence:** High for method family; Low for thresholds.  
**Uncertain:** window length, seasonal strata, minimum n.

### 24.7 Prioritization

**Recommendation:** Transparent bands with visible factors; separate attention from confidence; de-duplicate correlated evidence.  
**Evidence:** Official review prioritization and NIST risk-based handling principles.[^S01][^S05]  
**Confidence:** High conceptually.  
**Uncertain:** weights/order and reviewer calibration.

### 24.8 Evidence model

**Recommendation:** Conceptually retain source artifact, normalized record, analysis run, rule/model/config version, finding, evidence links, and review action.  
**Evidence:** Official auditability and provenance guidance.[^S01][^S15]  
**Confidence:** High.  
**Uncertain:** final physical schema.

### 24.9 Synthetic dataset

**Recommendation:** Multiple entities/periods, mixed quality, held-out ground truth, concerning and legitimate unusual scenarios.  
**Evidence:** Competitor-reported circularity risks and evaluation needs.[^S30][^S31]  
**Confidence:** High.  
**Uncertain:** exact scale/distributions until generator experiments.

### 24.10 Evaluation

**Recommendation:** Family-level detection, ranking, evidence/reproducibility, performance, and blind manual review.  
**Evidence:** Official expert comparison; established detection and ranked-retrieval metrics.[^S01][^S18][^S19]  
**Confidence:** High.  
**Uncertain:** availability and qualifications of reviewers.

### 24.11 Technology direction

**Recommendation:** Python-centered local analytics; evaluate DuckDB/SQLite and UI packaging in Phase 2.  
**Evidence:** Offline embedded capabilities and ecosystem fit.[^S23][^S24]  
**Confidence:** Medium.  
**Uncertain:** target OS, team skills, concurrent users, deployment policy.

### 24.12 Offline deployment

**Recommendation:** Design for an integrity-verified offline bundle; choose wheelhouse/executable/container only after environment confirmation.  
**Evidence:** Offline packaging and image-transfer documentation.[^S22][^S26][^S27]  
**Confidence:** High on requirement, Medium on packaging.  
**Uncertain:** permitted runtime and update procedure.

---

## 25. PROJECT_SPEC.md — Recommended Changes After Research

| Priority | Current specification | Research finding | Recommended change | Reason |
|---|---|---|---|---|
| Critical | Synthetic planted scenarios are the main stated prototype validation direction | Official statement asks for comparison with expert manual review | Add blinded manual-review comparison and state synthetic validation alone is insufficient | Prevent circular validation |
| High | Prioritization centers on organizations/findings | Official wording includes entities, controls, processes, and alert samples | Explicitly include control/process/sample review queues or tags | Better requirement coverage |
| High | Negative space is described, but evidence availability is not a separate output dimension | Missing submission data can mimic missing action | Add evidence-completeness/confidence status and “indeterminate” outcome | Reduce false accusations |
| High | Peer method deferred; possible attributes listed | NIST warns cross-organization comparisons may be invalid | Require denominator harmonization, cohort eligibility, minimum peer count, and no silent fallback | Defensible benchmarking |
| High | Historical comparison accounts for sample/data quality “where possible” | Robust baselines require explicit eligibility | Make eligibility, comparable periods, and insufficient-history output mandatory | Avoid unstable flags |
| High | Success criteria separate deterministic and ML results | Incremental value is not explicitly required | Require ML ablation against simple robust baselines before inclusion | Avoid decorative ML |
| High | Reporting appears mainly as UI/dashboard | Official statement also asks for reports and lists deliverables | Add exportable examiner review package/report to prototype scope | Meets reporting expectation |
| High | Data ingestion includes records and future APIs | Official source emphasizes minimizing raw logs/PCAP/customer data | Add explicit metadata-first minimization and reject unnecessary sensitive content | Security and scope control |
| Medium | ML controls cover offline inference and updates | Official wording asks for architecture, hardware, offline training/inference, update, explainability, auditability | Add an ML documentation checklist if any model ships | Traceability to requirement |
| Medium | Finding priority is a transparent score | A single score can hide uncertainty and double counting | Specify separate attention and evidence confidence; allow banded/lexicographic policy | Prevent “score = truth” |
| Medium | Finding contract includes evidence and basis | Alternate explanations and evidence searched are not explicit required fields | Add limitations/alternatives, applicability, and evidence-search scope | Responsible negative-space wording |
| Medium | Synthetic direction includes planted scenarios | Legitimate unusual scenarios are not explicit enough | Require benign confounders and false-positive control cases | Harder, more realistic evaluation |
| Medium | Security principles are high level | Upload/archive and logging threats are material | Add untrusted-ingestion, archive limits, formula injection, log redaction, model/rule integrity | Secure offline operation |
| Medium | UI includes source evidence view | Provenance snapshot fields are deferred | Require conceptual provenance fields in Phase 2 without freezing schema | Reproducibility |
| Medium | Official requirements section states framing available to team | Live official page was not verified; archive theme conflicts | Record archive provenance and mandatory official recheck before submission | Evidence honesty |
| Low | Demo/PPT are later deliverables | Official archive provides limits | Record architecture ≤2 pages, demo ≤2 minutes, presentation ≤5 slides | Submission readiness |
| No change required | Human authority, prohibited ML judge, offline operation, non-SIEM scope | Strongly supported by official statement and NIST principles | Retain | Correct core framing |

---

## 26. Open Questions Before Architecture

1. Can the team obtain a current official copy of SIH 26157 and confirm theme, deliverable limits, and any omitted weights?
2. Which exact source tables/files will the canonical prototype submission contain?
3. What policy/expectation registry will justify each deterministic rule?
4. Which 6–8 finding families survive feasibility and evidence-availability review?
5. How will “not provided,” “not applicable,” “invalid,” and true zero be represented?
6. What constitutes a complete reporting period for each evidence type?
7. What historical windows and minimum samples will simulation support?
8. Which peer attributes exist, and what minimum eligible cohort is defensible?
9. How will attention priority, evidence confidence, and data quality interact without double counting?
10. Does Isolation Forest improve held-out outcomes beyond robust univariate/multivariate baselines?
11. What TF-IDF normalization and similarity thresholds work across legitimate templates and concerning repetition?
12. What exact benchmark scale should be achievable on the target offline hardware?
13. Who can perform the manual-review comparison, and what blinded rubric will they use?
14. What target OS, local runtime, user concurrency, and deployment restrictions apply?
15. Is container execution permitted, or is a native/desktop bundle required?
16. What local identity, roles, retention, backup, and secure-deletion policies are expected?
17. Which database choice best supports analytical batch work, review state, provenance, and packaging?
18. What report/export formats are acceptable in an air-gapped environment?
19. Which accessibility and usability tests are mandatory for the examiner workflow?
20. How will source-system schema changes and versioned mappings be governed?

---

## 27. What We Now Know

### What We Now Know

- The problem is prioritization of supervisory attention from periodic SOC operational evidence.
- Human examiners retain authority; explainability and auditability are mandatory design properties.
- Execution gaps are strongest when tied to explicit expectations and cross-record evidence.
- Negative space requires an expected universe and adequate observation completeness.
- Robust historical statistics and carefully matched peers are safer than universal thresholds.
- A model score is not a finding and is not a probability of failure or dishonesty.
- Synthetic ground truth is useful but must be challenged by legitimate anomalies and manual review.
- Existing SIH implementations already cover many headline features.

### What We Should Build

A compact offline examiner workflow that validates structured submissions, generates a small set of transparent findings, correlates multiple bases, shows complete provenance and uncertainty, prioritizes review, and supports reviewer disposition/export.

### What We Should NOT Build

A SIEM, SOC, national monitoring platform, streaming collector, automated incident responder, opaque cyber-risk oracle, cloud-dependent assistant, or model that continually retrains from its own outputs.

### Biggest Technical Risks

1. incomplete/semantically inconsistent source data;
2. weak peer cohorts and unstable baselines;
3. circular synthetic validation;
4. correlated signals double-counted in priority;
5. offline packaging and dependency integrity;
6. untrusted file ingestion;
7. model drift and threshold overfitting.

### Biggest Product Risks

1. examiner treats priority as truth;
2. absence is worded as proof of non-performance;
3. evidence path is too slow or opaque;
4. data-quality warnings are hidden;
5. the demo shows many charts but no credible source-backed case;
6. report language implies wrongdoing rather than a verification need.

### Biggest Competitive Gaps

Based on public repositories, the clearest gaps are independent manual-review validation, realistic false-positive controls, defensible cohort eligibility, explicit evidence-confidence handling, and reproducible multi-basis evidence packages—not the presence of a dashboard or generic anomaly detection.[^S30][^S31][^S32]

---

## 28. Recommended Next Step

Proceed to **Phase 2 — Architecture** with this report and `PROJECT_SPEC.md` as inputs. Phase 2 should:

1. resolve the critical open questions or record assumptions;
2. define the final high-level component boundaries and data flows;
3. define the canonical evidence/provenance model without losing original values;
4. specify interfaces for validation, analytical modules, findings, priority, and review;
5. select storage, UI, packaging, and test technologies against explicit criteria;
6. write non-functional requirements for offline operation, security, reproducibility, and benchmark scale;
7. produce architecture decision records for disputed choices;
8. stop before implementation until the architecture and analytics contracts are reviewed.

---

## 29. References

Each entry records title, author/organization, date where available, URL, support, and relevance.

[^S01]: **SIH26157 — Development of an AI-driven tool for automated SOC operational evidence analysis for supervisory assessment**. SIH 2026 problem-statement archive; source attributed to Smart India Hackathon official portal; archived 2026-09-03. https://github.com/vedantchalke36/sih-2026-problem-statements/blob/dfe64f7694f1f40732548abe98750c20bdc36265/ps_2026/SIH26157.md — Supports the detailed requirement extraction. Relevant as the strongest accessible, commit-pinned copy; live official page must be rechecked.

[^S02]: **SIH26157.md**. Independent SIH problem-statement archive, 2026 snapshot. https://github.com/Vigneshrdy/sih-ps-archive/blob/806b4d7fd6b2a19fdd3d92f08b42ae4d93464ac7/2026/SIH26157.md — Corroborates the substantive statement and exposes the theme-label discrepancy.

[^S03]: **Information Technology (Information Security Practices and Procedures for Protected System) Rules, 2018**, Gazette notification S.O. 2235(E). Ministry of Electronics and Information Technology, Government of India; 2018-06-01 publication. https://www.meity.gov.in/static/uploads/2024/02/NCIIPC-Rules-notification-1.pdf — Supports NCIIPC/protected-system governance, SOC-record, inventory, audit, and information-sharing context.

[^S04]: **NIST SP 800-61 Rev. 3: Incident Response Recommendations and Considerations for Cybersecurity Risk Management**. NIST; 2025-04. https://csrc.nist.gov/pubs/sp/800/61/r3/final — Supports incident response as part of risk management and current NIST context.

[^S05]: **NIST SP 800-61 Rev. 2: Computer Security Incident Handling Guide**. Cichonski, Millar, Grance, Scarfone; NIST; 2012-08. https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-61r2.pdf — Supports incident record fields, prioritization factors, metrics cautions, and cross-organization comparability limits.

[^S06]: **NIST SP 800-92: Guide to Computer Security Log Management**. Kent and Souppaya; NIST; 2006-09. https://csrc.nist.gov/pubs/sp/800/92/final — Supports sound enterprise log-management processes; relevant background, not a SAT-SA implementation mandate.

[^S07]: **The NIST Cybersecurity Framework (CSF) 2.0**. NIST; 2024-02-26. https://www.nist.gov/cyberframework — Supports the Govern/Identify/Protect/Detect/Respond/Recover resilience context.

[^S08]: **NIST SP 800-53 Rev. 5, Update 1: Security and Privacy Controls for Information Systems and Organizations**. NIST; 2020-09, updated 2020-12. https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final — Supports audit/accountability, assessment/monitoring, incident response, and system-integrity control context.

[^S09]: **Best Practices for Event Logging and Threat Detection**. CISA and international partners; 2024-08-21. https://www.cisa.gov/resources-tools/resources/best-practices-event-logging-and-threat-detection — Supports operational importance of logging and threat detection; relevant to evidence quality.

[^S10]: **NIST/SEMATECH e-Handbook of Statistical Methods — Detection of Outliers**. NIST; living handbook, accessed during Phase 1 research. https://www.itl.nist.gov/div898/handbook/eda/section3/eda35h.htm — Supports careful treatment of outliers, masking/swamping, and robust detection context.

[^S11]: **Median Absolute Deviation**. NIST Dataplot reference; updated 2016-04-11. https://www.itl.nist.gov/div898/software/dataplot/refman2/auxillar/mad.htm — Supports MAD as a robust scale statistic.

[^S12]: **Novelty and Outlier Detection — scikit-learn User Guide**. scikit-learn project; stable documentation, accessed during Phase 1 research. https://scikit-learn.org/stable/modules/outlier_detection.html — Supports IF/LOF behavior, novelty-vs-outlier distinction, contamination caveats, and unsupervised limitations.

[^S13]: **DBSCAN — scikit-learn User Guide**. scikit-learn project; stable documentation, accessed during Phase 1 research. https://scikit-learn.org/stable/modules/clustering.html#dbscan — Supports DBSCAN’s density-based approach and scalability/parameter limitations.

[^S14]: **Text Feature Extraction — scikit-learn User Guide**. scikit-learn project; stable documentation, accessed during Phase 1 research. https://scikit-learn.org/stable/modules/feature_extraction.html#text-feature-extraction — Supports bag-of-words, TF-IDF, sparse representation, and short-text limitations.

[^S15]: **PROV-O: The PROV Ontology**. W3C Recommendation; 2013-04-30. https://www.w3.org/TR/prov-o/ — Supports general provenance concepts for entities, activities, and agents.

[^S16]: **NIST AI 100-1: Artificial Intelligence Risk Management Framework (AI RMF 1.0)**. NIST; 2023-01. https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf — Supports validity, reliability, transparency, explainability, accountability, human oversight, and data-quality considerations.

[^S17]: **Open Cybersecurity Schema Framework Schema Browser, v1.9.0 shown**. OCSF; accessed during Phase 1 research. https://schema.ocsf.io/ — Supports common cybersecurity event/finding terminology; relevant as vocabulary inspiration, not a final schema.

[^S18]: **Metrics and Scoring: Quantifying the Quality of Predictions**. scikit-learn project; stable documentation, accessed during Phase 1 research. https://scikit-learn.org/stable/modules/model_evaluation.html — Supports precision, recall, F1, confusion matrices, and metric interpretation.

[^S19]: **Evaluation of Ranked Retrieval Results**, in *Introduction to Information Retrieval*. Manning, Raghavan, and Schütze; Cambridge University Press; 2008. https://nlp.stanford.edu/IR-book/html/htmledition/evaluation-of-ranked-retrieval-results-1.html — Supports precision at cutoff and ranked-retrieval evaluation cautions.

[^S20]: **NIST SP 800-218: Secure Software Development Framework (SSDF) Version 1.1**. NIST; 2022-02. https://csrc.nist.gov/pubs/sp/800/218/final — Supports integrating secure development practices into the lifecycle.

[^S21]: **File Upload Cheat Sheet**. OWASP Cheat Sheet Series; living guidance, accessed during Phase 1 research. https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html — Supports allowlists, independent validation, safe naming, size limits, and isolated storage.

[^S22]: **Repeatable Installs**. Python Packaging Authority/pip documentation; accessed during Phase 1 research. https://pip.pypa.io/en/stable/topics/repeatable-installs/ — Supports dependency pinning, hashes, and offline wheelhouse practices.

[^S23]: **Why DuckDB**. DuckDB Foundation; documentation accessed during Phase 1 research. https://duckdb.org/why_duckdb — Supports embedded, serverless, columnar analytical operation.

[^S24]: **About SQLite**. SQLite project; page updated 2025-11-13. https://www.sqlite.org/about.html — Supports in-process, self-contained, serverless, transactional, single-file operation.

[^S25]: **NIST SP 800-115: Technical Guide to Information Security Testing and Assessment**. Scarfone et al.; NIST; 2008-09. https://csrc.nist.gov/pubs/sp/800/115/final — Supports structured test planning, analysis, and acknowledgement of assessment limitations.

[^S26]: **docker image save**. Docker documentation; accessed during Phase 1 research. https://docs.docker.com/reference/cli/docker/image/save/ — Supports archiving container images for transfer.

[^S27]: **docker image load**. Docker documentation; accessed during Phase 1 research. https://docs.docker.com/reference/cli/docker/image/load/ — Supports loading archived images in disconnected environments.

[^S28]: **Logging Cheat Sheet**. OWASP Cheat Sheet Series; accessed during Phase 1 research. https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html — Supports secure, privacy-aware application logging.

[^S29]: **NISTIR 8312: Four Principles of Explainable Artificial Intelligence**. Phillips et al.; NIST; 2021-09. https://doi.org/10.6028/NIST.IR.8312 — Supports explanation, meaningfulness, explanation accuracy, and knowledge-limit principles.

[^S30]: **SOCRIX repository**. Kabir Sinha et al.; commit-pinned public repository accessed during Phase 1 research. https://github.com/kabir-sinha/socrix/tree/1d6e9bd2ec863457985c656e39d81bcd403a128c — Supports competitive observations about deterministic findings, peer scoring, evidence, audit, offline claims, and synthetic-validation caveats.

[^S31]: **Supervisory Analytics Tool for SOC Assessment (SAT-SA) repository**. Charan89k; commit-pinned public repository accessed during Phase 1 research. https://github.com/Charan89k/Supervisory-Analytics-Tool-for-SOC-Assessment-SAT-SA-/tree/e197e372a677964422beb23140645281887419ee — Supports competitive observations and explicit synthetic/expert-validation limitations.

[^S32]: **SIH26157-SAT-SA repository**. Mohittt0706; commit-pinned public repository accessed during Phase 1 research. https://github.com/Mohittt0706/SIH26157-SAT-SA/tree/f6e2e2f2b826816e912499994404740cdb49e945 — Supports competitive observations about three detectors, dashboard, manual review, synthetic benchmark, and offline claims.

[^S33]: **sat-sa repository**. 20johan06; public repository accessed during Phase 1 research. https://github.com/20johan06/sat-sa — Supports competitive observations about the published stack and limited top-level analytical detail.

[^S34]: **VETAILS-SIH26157 repository**. parvgarg05; public repository accessed during Phase 1 research. https://github.com/parvgarg05/VETAILS-SIH26157 — Supports competitive observations about the local stack, testing claims, and project documentation.

---

## Research Self-Audit

### Source quality

- Primary government, standards, and official technical documentation were preferred.
- The inaccessible live SIH page is disclosed; two commit-pinned archives were cross-checked.
- Competitor claims are labeled as claims and were not treated as independently validated facts.
- No numeric evaluation weights or universal thresholds were invented.

### Technical quality

- Deterministic, statistical, ML, and text methods were compared with limitations.
- Missing data, confounders, false positives, peer mismatch, sample size, and model contamination were addressed.
- ML is recommended only as a supporting layer subject to ablation.

### Product and SIH quality

- The report centers the examiner workflow, evidence traceability, execution gaps, negative space, prioritization, and offline operation.
- It does not redefine SAT-SA as a SIEM, SOC, real-time monitor, or automated response system.
- Recommendations distinguish official requirements from project choices.

### Remaining evidence limitations

- Official live SIH wording and any portal-only evaluation weights remain unverified.
- No real NCIIPC/CSE operational dataset or examiner study was available.
- Competitor repositories were researched from public documentation; their test claims were not rerun.
- Exact thresholds, dataset distributions, model value, deployment target, and final technology choices require later experiments and stakeholder constraints.

**PHASE 1 RESEARCH COMPLETE — READY FOR ARCHITECTURE**
