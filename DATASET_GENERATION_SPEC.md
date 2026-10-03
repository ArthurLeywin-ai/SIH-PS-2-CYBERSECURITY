# DATASET_GENERATION_SPEC.md

## SAT-SA — Phase 4 Synthetic Dataset Generation Design

| Field | Value |
|---|---|
| Project | SAT-SA — Supervisory Analytics Tool for SOC Assessment |
| SIH problem statement | SIH 2026 — SIH26157 |
| Phase | Phase 4 — Synthetic Dataset Generation Design |
| Authoritative inputs | `PROJECT_SPEC.md`, `RESEARCH_REPORT.md`, `ARCHITECTURE.md`, `DATA_SCHEMA.md` |
| Purpose | Complete, reproducible specification for generating difficult synthetic operational evidence and privately separated evaluation truth |
| Scope | Generator and dataset design only; no dataset files, generator code, SQL, application, analytics, ML, or UI implementation |
| Dataset status | Not generated |

> **Hard separation:** SAT-SA analytics receive only operational evidence. Scenario IDs, labels, expected findings, mutation annotations, scenario seeds, and planted-positive indicators remain private.
>
> **Difficulty principle:** The generator creates a heterogeneous operational world first and applies context-aware scenarios second. It does not create arbitrary “normal” rows and flip a suspicious label.

### Decision labels

- **FACT** — directly required by the four authoritative documents.
- **RESEARCH FINDING** — accepted conclusion from the approved research.
- **PROJECT DECISION** — concrete generator-design decision made in this phase.
- **ASSUMPTION** — planning condition to validate during implementation.
- **OPEN QUESTION** — unresolved choice that does not justify inventing certainty.

---

## 1. Purpose, Boundaries, and Success Condition

### 1.1 Technical purpose

The synthetic system must produce periodic multi-organization SOC operational evidence rich enough to build, test, demonstrate, and compare SAT-SA’s:

- execution-gap analysis;
- negative-space analysis;
- historical and peer comparison;
- cross-record consistency checks;
- repetitive-investigation analysis;
- data-quality handling;
- optional anomaly detection;
- evidence provenance and source drill-down;
- transparent prioritization for manual review;
- ability to avoid obvious legitimate unusual cases.

### 1.2 Non-purpose

The dataset does not attempt to recreate national infrastructure, real attacks, classified operations, packet traffic, EDR telemetry, live SIEM streams, malware behavior, attacker timelines, automated response actions, or actual NCIIPC/CSE data. It cannot prove production accuracy.

### 1.3 Success condition

The design is successful only if a later implementation can produce:

1. schema-valid base evidence;
2. deliberate, privately documented concern/control/quality scenarios;
3. source-layout heterogeneity and complete field-level provenance;
4. held-out evaluation without label leakage;
5. exact regeneration from approved versions and seeds;
6. expected contract violations only where privately authorized by a scenario;
7. both concerning-looking legitimate cases and subtle meaningful cases.

**RESEARCH FINDING:** Synthetic success is vulnerable to circularity when the detector and generator share exact thresholds. Therefore generation parameters, scenario realization, and held-out seeds must remain independent from detector tuning.

---

## 2. Dataset Architecture

### 2.1 Package separation

```text
Dataset Build Workspace (private)
    |
    +-- Base Operational World
    |       |
    |       +-- Scenario Mutation Planner (private)
    |       +-- Source Renderers
    |       +-- Canonical Reference / Provenance Builder
    |
    +-- Operational Evidence Package ----------------> SAT-SA ingestion/analytics
    |
    +-- Hidden Ground-Truth Package -----------------> Evaluation harness only
    |
    +-- Private Evaluation Package ------------------> Evaluators/review coordinator
```

The three release packages are independently hashed. A private binding manifest records which operational package, truth package, and evaluation package belong together.

### 2.2 Operational evidence package

The operational package contains only data a hypothetical CSE could submit, plus safe manifests and generator-produced canonical/provenance references needed for contract testing. It contains:

- synthetic organization profiles;
- submissions and evidence-family declarations;
- assets and monitoring coverage;
- alerts, cases, case-alert links, investigations, escalations, actions, resolutions, closures, exceptions, and process changes;
- control/process references and operational/configuration links;
- heterogeneous CSV/JSON source exports;
- source-file and source-record indexes;
- canonical reference records and field-level provenance where included for schema verification;
- schema-profile, vocabulary-mapping, and public dataset manifests;
- public limitations that do not reveal planted scenarios.

It contains **no**:

- `scenario_id` or scenario code;
- true/false, concern/control, positive/negative, or legitimate labels;
- expected finding/category/priority;
- mutation type, mutation locator, or planted-positive flag;
- private scenario seed or hidden split key;
- filename, source ID, row ordering, note phrase, or metadata token encoding those values.

### 2.3 Hidden ground-truth package

The ground-truth package contains the exact private contracts from `DATA_SCHEMA.md`:

- scenario manifest and versions;
- affected entity/period/record links;
- intended analytical family;
- true category: attention, legitimate unusual, normal, data-quality-only, or ambiguous;
- expected evidence and acceptable matching rule;
- confounders/counterevidence;
- mutation provenance and scenario seed;
- expected correlation behavior for overlapping scenarios;
- private generation audit.

It is not mounted, imported, indexed, copied, logged, or exposed to SAT-SA.

### 2.4 Private evaluation package

The evaluation package contains no detector features. It coordinates evaluation through:

- development/validation/held-out split manifest;
- hidden seed/scenario allocation manifest;
- sealed analytical-output location and matching configuration;
- blinded manual-review subset containing operational review packets only;
- reviewer assignment/rubric without labels;
- private answer-key reference into hidden ground truth;
- benchmark hardware/run template;
- result-signing/hash manifest.

### 2.5 Canonical reference boundary

**PROJECT DECISION:** A release may contain a `canonical_reference_private_to_testing` artifact derived from source exports. It has no ground-truth labels and exists to validate mappings/provenance. For end-to-end held-out evaluation, SAT-SA receives only the source exports and public operational manifest; the canonical reference is withheld until ingestion output is sealed.

This prevents the end-to-end test from bypassing source mapping while still permitting precise generator validation.

### 2.6 Proposed logical release structure

This is a design, not created files.

```text
release_<dataset_version>/
  operational_evidence/
    dataset_manifest
    organizations/
    submissions/
    source_exports/
      <organization>/<period>/<source_profile>/
    source_file_manifests/
    source_record_indexes/
    mapping_profiles_public/
    vocabulary_maps_public/
    canonical_reference_private_to_testing/   # withheld in end-to-end runs
    provenance_reference_private_to_testing/  # withheld in end-to-end runs

  ground_truth_private/
    ground_truth_manifest
    scenario_instances/
    scenario_record_links/
    expected_findings/
    generation_audit/

  evaluation_private/
    split_manifest
    hidden_seed_manifest
    blinded_review_packets/
    reviewer_rubric
    answer_key_reference
    benchmark_run_manifest

  binding_private/
    package_binding_manifest
```

### 2.7 Dataset manifest

The public operational manifest includes:

- dataset ID/version and benchmark tier;
- generator version and public build identifier;
- canonical schema version;
- source schema-profile and mapping versions;
- vocabulary versions;
- public seed alias, not hidden scenario seeds;
- organization/period/evidence-family/file/record counts;
- declared synthetic/privacy status;
- deterministic serialization profile;
- each operational file path, byte size, media type, and SHA-256;
- package tree hash;
- known public limitations and intended split name;
- generation completion timestamp derived deterministically or recorded outside byte-reproducible content.

It does not contain a ground-truth hash. The private binding manifest stores operational, ground-truth, and evaluation package hashes.

---

## 3. Generator System Architecture

### 3.1 Components

| Component | Responsibility | Output |
|---|---|---|
| Version/config registry | Freezes schema, generator, scenario, mapping, vocabulary, tier, and split versions | Build configuration snapshot |
| Seed manager | Derives independent deterministic random streams from master seed and labels | Seed ledger; private where required |
| Population builder | Creates organizations, cohorts, source profiles, workflows, assets, and baseline propensities | Base population model |
| Period planner | Creates 4–6 periods, maturity, source coverage, late-arrival schedule, and process boundaries | Period/submission plan |
| Operational-world simulator | Generates natural alert/workflow behavior without scenario labels | Clean heterogeneous evidence graph |
| Scenario planner | Selects eligible entities/periods/records and reserves non-overlapping/overlapping instances | Private scenario plan |
| Scenario mutator | Applies context-aware structural/behavioral mutations or legitimate controls | Mutated operational world + private audit |
| Data-quality mutator | Renders missingness, invalidity, duplicates, schema drift, and partiality | Source-world quality variation |
| Source renderer | Serializes the same world into profile-specific CSV/JSON exports | Heterogeneous source files |
| Canonical reference builder | Applies approved mappings to produce expected canonical/provenance reference | Private contract oracle, no labels |
| Ground-truth writer | Records scenario/record/evidence/mutation truth | Hidden truth package |
| Validation engine | Validates clean base, authorized mutations, distribution sanity, and separation | Validation report/build gate |
| Packager/hasher | Canonically orders, serializes, hashes, and binds packages | Reproducible release artifacts |

### 3.2 Required generation order

1. Freeze versions, tier, split, and master seed.
2. Derive component-specific seed streams.
3. Build organizations, cohorts, workflows, source profiles, and period plan.
4. Build assets, monitoring expectations, and baseline coverage.
5. Simulate alerts, cases, investigations, escalations, actions, resolutions, and closures.
6. Validate the unmutated operational world strictly.
7. Select and reserve scenario subjects based on broad eligibility, not detector thresholds.
8. Apply concerning, legitimate-control, overlap, and data-quality mutations.
9. Render source-specific exports, including late-arrival and revision packages.
10. Build source records, canonical references, field observations, relationships, and provenance.
11. Validate expected scenarios and expected authorized defects.
12. Scan operational output for leakage.
13. Create manifests and SHA-256 hashes.
14. Bind packages privately and seal the release.

### 3.3 Two-stage validity rule

- **Before mutation:** every base-world record and relationship must satisfy the canonical contract unless the base profile explicitly models ordinary optional absence.
- **After mutation:** every new schema/quality violation must match one private authorized mutation. An unintended invalid record fails the build.

The operational package contains only the resulting evidence and natural validation consequences, never the authorization ledger.

---

## 4. Versioning, Seeds, and Reproducibility

### 4.1 Version tuple

A reproducible build is identified by:

`generator_version + generator_build_hash + schema_version + source_profile_set_version + mapping_set_version + vocabulary_set_version + scenario_catalog_version + dataset_tier + split_id + full_seed_ledger`

Changing any member creates a new dataset version.

### 4.2 Seed hierarchy

**PROJECT DECISION:** Use a master seed with deterministic named child streams rather than one global random stream. Child streams are derived from stable labels such as:

- `population`;
- `organization/<id>`;
- `period/<id>`;
- `assets/<organization>`;
- `alerts/<organization>/<period>`;
- `workflow/<organization>/<period>`;
- `notes/<organization>/<period>`;
- `source_profile/<organization>`;
- `quality/<organization>/<period>`;
- `scenario/<scenario_instance>`;
- `serialization`.

Adding a new note template must not unintentionally change alert counts. Component stream independence makes local changes reviewable.

### 4.3 Seed disclosure

- Development fixture seeds may be public.
- Validation seeds may be shared after a validation release freezes.
- Held-out master/scenario seeds remain private until final evaluation is complete.
- Operational packages expose only a non-reversible seed alias/build ID.
- The private truth manifest records exact master and scenario seeds.

### 4.4 Byte-level determinism

Same version tuple must produce the same logical records and bytes. The generator specification therefore requires:

- stable deterministic IDs derived from dataset namespace + logical identity, never execution order alone;
- stable record sorting before serialization;
- UTF-8 encoding and LF line endings;
- deterministic CSV dialect per source profile;
- deterministic JSON key order and number formatting;
- UTC canonical timestamps with original source formatting rendered deterministically;
- fixed archive ordering and metadata if archives are used;
- no current wall-clock value in hashed data content;
- pinned generator dependencies and locale/timezone;
- deterministic handling of floating-point rounding.

### 4.5 Hashes

- SHA-256 for every source/export/reference file;
- SHA-256 for each logical source record as required by schema;
- canonical manifest hash;
- package tree hash from sorted `(relative_path, file_hash, byte_size)` entries;
- separate hidden truth/evaluation package hashes;
- private binding manifest tying all package hashes to one dataset version.

Hashes show that generated artifacts match the sealed release. They do not make data immutable or prove realism.

---

## 5. Synthetic Population

### 5.1 Target population

**PROJECT DECISION — PLANNING TARGET:** The principal development and held-out datasets use 15 organizations. This fits the approved 12–20 range and provides three primary cohorts of five. The large stress tier may use 20 organizations.

Organizations use clearly synthetic identifiers `CSE-001` through `CSE-015`; names remain obviously fictional.

### 5.2 Primary peer cohorts

| Cohort | Organizations | Synthetic sector | Typical scale | Typical operating model | Purpose |
|---|---|---|---|---|---|
| `COHORT-A` | `CSE-001`–`CSE-005` | `SECTOR-ALPHA` with two synthetic subsectors | Large / Very Large | Mostly centralized 24×7 | High-volume, mature workflows |
| `COHORT-B` | `CSE-006`–`CSE-010` | `SECTOR-BETA` with two synthetic subsectors | Medium / Large | Centralized 24×7 or Hybrid | Mixed automation and case practices |
| `COHORT-C` | `CSE-011`–`CSE-015` | `SECTOR-GAMMA` with two synthetic subsectors | Small / Medium / Large | Distributed, Hybrid, or business-hours | Lower volume and heterogeneous operations |

Cohort membership is only a generation context. The eventual peer engine must still evaluate metric comparability, data quality, denominator, source definitions, and period eligibility. Some entity-periods are intentionally ineligible.

### 5.3 Organization profile dimensions

Each organization receives persistent latent parameters drawn around cohort ranges:

- active/critical asset counts and asset-class mixture;
- operating hours and staffing/workflow capacity proxy;
- alert-volume intensity and burstiness;
- severity and category mixture;
- case creation propensity and alerts-per-case distribution;
- investigation depth and note-style mixture;
- escalation propensity conditional on context;
- automation/suppression usage;
- resolution/closure propensity and duration scale;
- remediation propensity for recurring issues;
- monitoring-coverage level and onboarding/decommissioning rate;
- source-system/layout profile;
- baseline data-quality tendency;
- workflow/tool version schedule.

These parameters overlap across organizations and cohorts. Scale band alone must not determine every behavior.

### 5.4 Legitimate diversity constraints

- At least one organization per cohort uses a different operating model.
- At least one organization has genuinely faster normal handling due to approved automation.
- At least one has slower but well-documented workflows.
- At least one has high alert volume with strong investigation coverage.
- At least one has low volume and limited peer eligibility without being concerning.
- Asset criticality and category mix differ independently from raw alert volume.
- Normal period-to-period variation remains material.

### 5.5 Population metadata leakage rule

No organization alias, profile value, source filename, source-system version, or row order may encode its hidden scenario allocation. Scenario allocation occurs after public profile creation.

---

## 6. Reporting Period and Submission Plan

### 6.1 Period design

**PROJECT DECISION:** Main datasets use six consecutive reporting periods `P01`–`P06`. Each release manifest supplies actual synthetic UTC boundaries. Periods are comparable in intended duration, but the generator may create partial coverage and late-arrival behavior.

- `P01`–`P03`: early history and normal variation;
- `P04`: mature pre-current comparison period;
- `P05`: scenario/process-change period;
- `P06`: current/held-out period with mature, immature, or late-arriving state depending on entity.

Four-period variants may be used for smaller tiers. Six periods are preferred for meaningful historical eligibility tests.

### 6.2 Period maturity assignment

Across the population:

- most entity-periods are `MATURE` and complete enough for ordinary analytics;
- a controlled minority are `PARTIAL` with declared missing scope;
- several current periods are `IMMATURE` due to grace/maturation windows;
- some are `UNKNOWN` because source scope is undeclared;
- explicit zero-record families exist separately from omitted families.

Exact assignments and counts are split-specific and private when they intersect scenarios.

### 6.3 Late arrivals and revisions

Late-arrival generation follows this sequence:

1. generate an event inside period `Pn`;
2. omit it from the `Pn` submission according to source/export behavior;
3. include it as a new or revised source record in `Pn+1`;
4. preserve original event time and later received/update time;
5. link corrected submission through `supersedes_submission_id` only when the whole submission is corrected;
6. record mutation provenance privately.

Late arrival can be ordinary, a migration control, or a quality concern. It is not automatically a positive scenario.

### 6.4 Process-change boundaries

Selected organizations receive documented process/tool changes at a period boundary. Examples:

- status vocabulary and timestamp format change;
- case workflow/version change;
- approved automation deployment;
- monitoring platform migration;
- severity mapping revision;
- temporary emergency workflow.

Other organizations receive an undocumented behavioral shift for historical-deviation evaluation. Documented changes include Process Change and, where applicable, Exception records. Undocumented shifts do not.

### 6.5 Submission matrix

Each organization-period normally creates one submission, with controlled exceptions:

- corrected/superseding submission;
- evidence family deliberately absent and declared/not declared;
- split exports from multiple source systems;
- no submission for scheduled-period negative-space/data-quality evaluation;
- source schema version change.

The generator records `DECLARED_COMPLETE`, `DECLARED_PARTIAL`, or `NOT_DECLARED` independently from SAT-SA-assessed completeness.

---

## 7. Operational Evidence Generation Pipeline

### 7.1 Dependency order

| Order | Family | Generation basis | Key downstream use |
|---:|---|---|---|
| 1 | Organization | Cohort/profile plan | Peer eligibility and namespace |
| 2 | Control/Process Reference | Demo/config/source-profile plan | Rule/applicability and review scope |
| 3 | Period/Submission | Period and source plan | Scope, maturity, family completeness |
| 4 | Asset | Organization scale/class mixture | Criticality and monitoring denominator |
| 5 | Monitoring Coverage | Asset expectation, onboarding, exception | Coverage negative space |
| 6 | Alert | Arrival/category/severity process | Detection, recurrence, timing |
| 7 | Case + Case-Alert Link | Case propensity and grouping | Workflow linkage |
| 8 | Investigation | Case/alert workflow, staffing/load | Execution/repetition evidence |
| 9 | Escalation | Applicability and probabilistic behavior | Escalation analysis |
| 10 | Action/Remediation | Recurrence, case outcome, accepted risk | Follow-through analysis |
| 11 | Resolution | Workflow outcome | Substantive resolution evidence |
| 12 | Closure | Administrative lifecycle/disposition | Closure timing and consistency |
| 13 | Exception | Legitimate context with effective interval | False-positive control |
| 14 | Process Change | Tool/workflow regime schedule | Historical eligibility/context |
| 15 | Source Files/Records | Source-profile rendering | Ingestion/provenance |
| 16 | Canonical/Field/Relationship Reference | Approved mappings | Contract validation and traceability |

### 7.2 Organization, submission, and family declarations

- Generate organization profile versions independently from scenarios.
- Generate a submission manifest for each submitted entity-period.
- Create a declaration for every expected evidence family, including explicit `PROVIDED`, `NOT_PROVIDED`, `NOT_APPLICABLE`, or `UNKNOWN`.
- Declared record counts may be correct, missing, or deliberately inconsistent under a private quality mutation.
- An absent family is never rendered as an empty file unless the intended state is explicit zero within a provided family.

### 7.3 Assets and monitoring coverage

- Asset counts depend on scale band with overlapping ranges.
- Asset classes use a cohort-specific mixture with organization random effects.
- Criticality depends on asset class/business-service profile, not randomly independent.
- Assets have active/effective intervals, onboarding, decommissioning, and version changes.
- Monitoring expectations derive from asset profile/control configuration.
- Coverage can be full, partial, onboarding, degraded, suspended, not covered, or unknown.
- Monitoring records represent periodic evidence/declared status, not live telemetry.

### 7.4 Alerts

- Generate alert times from a bursty, non-homogeneous arrival process.
- Generate severity/category from organization/source-specific distributions.
- Associate assets probabilistically, with explicit unresolved/missing cases.
- Include acknowledgement, status, disposition, automation, suppression, and source detection IDs where source profile supports them.
- Optional source IDs are omitted naturally in selected layouts; provenance relies on file/row locator and generated canonical ID.
- Recurrence arises from latent issue signatures and clustered arrivals, not a post hoc suspicious flag.

### 7.5 Cases and links

- Some alerts remain alert-only under legitimate dispositions.
- Cases may group several alerts; a small tail groups many alerts during storms/campaign-like activity.
- Alerts may link to multiple related cases where source semantics permit.
- Link type and source representation vary by profile: direct foreign key, separate link file, or JSON array.
- Base-world links resolve; broken/unresolved variants are introduced only by authorized quality scenarios.

### 7.6 Investigations

- Investigation count and duration depend on case severity, category, asset criticality, workload, operating model, and automation.
- Open investigations may lack end time legitimately.
- Notes combine runbook/template text with generated case-specific facts, actions, conclusions, and evidence references.
- Analyst references are synthetic pseudonyms or roles only.
- Runbook/template/automation fields are populated imperfectly according to source capabilities.

### 7.7 Escalations

Escalation is probabilistic and context-dependent. It uses severity, asset criticality, incident/case type, operating model, source policy, workload, and random variation. Applicability is separately modeled through Control/Process and Exception data. The generator does not use a universal “all critical alerts escalate” rule.

### 7.8 Actions, resolution, and closure

- Remediation propensity increases with recurrence/impact but remains imperfect.
- Actions can remain open, deferred, completed, verified, cancelled, or linked to accepted risk.
- Resolution may precede closure and can be absent when a source combines concepts.
- Closure times depend on workflow path and disposition.
- Duplicate/false-positive/suppressed paths may be faster, but overlap remains with genuine cases.
- Reopened cases create revisions/events rather than destructive changes.

### 7.9 Exceptions and process changes

Legitimate unusual cases require explicit, effective, approved evidence where appropriate. An exception has target, type, applicability, approval state, reason, and interval. Expired, pending, rejected, mismatched, and unresolved exceptions are also generated as controls for correct applicability handling.

### 7.10 Control/process references

Generate a small, versioned catalogue of project-demo controls/processes, clearly marked `PROJECT_DEMO_CONFIGURATION` unless source-submitted. Link references to rules/workflows and selected records. Do not imply NCIIPC certification or invent official organization policies.

---

## 8. Distribution Design

All parameters below are generation families and planning envelopes, not official SOC norms, detector thresholds, or performance claims. Final values live in versioned generator configuration.

### 8.1 Alert volume and arrival

| Dimension | Distribution family | Heterogeneity/context |
|---|---|---|
| Base entity-period count | Gamma-Poisson/negative-binomial mixture | Scale band and cohort affect mean/dispersion; ranges overlap |
| Intra-period time | Non-homogeneous process | Operating hours, day-of-week, shift, maintenance, and source delay |
| Bursts | Cluster process with random duration/intensity | Storms may be legitimate or concerning depending on context |
| Period trend | Multiplicative latent factor with autocorrelation | Allows gradual drift and abrupt scenario shifts |

Avoid equal daily counts, fixed rates, or one Poisson parameter for all entities.

### 8.2 Severity

Severity uses an organization-period categorical draw whose probabilities come from a cohort prior plus organization/source random effects. Planning envelopes may keep `CRITICAL` uncommon and `HIGH` a minority while allowing meaningful overlap. Exact percentages are configuration, not analytics thresholds. Source renderers map canonical severity into text, numeric, or abbreviated source vocabularies.

### 8.3 Categories

Use a versioned synthetic category taxonomy such as authentication/identity, endpoint, network, application, data-access, malware-like detection, policy/control, availability, and other/unknown. Category proportions vary by asset mix and tooling. Tool changes can remap/split categories without changing underlying behavior.

### 8.4 Acknowledgement, investigation, and closure times

Use mixtures of lognormal or gamma-like positive durations with:

- severity and asset-criticality effects;
- disposition/path effects;
- operating-hours/shift effects;
- workload multiplier;
- automation component;
- long-tail component;
- organization random effect;
- measurement rounding by source profile.

No exact duration cutoff determines truth. Concern and legitimate distributions intentionally overlap.

### 8.5 Escalation rates

Generate event-level escalation propensity through a bounded probabilistic model. Inputs include applicability, severity, asset criticality, case type, operating model, workload, period regime, and organization effect. Historical/peer scenario mutations alter latent propensity across a subset; they do not test a detector’s exact rate threshold.

### 8.6 Recurrence

Latent issue signatures produce recurrent alert clusters on one or related assets. Cluster size and gap are heavy-tailed. Some clusters receive tuning/remediation; some recur despite remediation; some have accepted-risk context; some lack apparent follow-through.

### 8.7 Case size

Most cases link to few alerts; a long tail links to many. Use a zero-truncated overdispersed count for alerts per case, plus separate storm/campaign grouping. Some alerts have no case for legitimate reasons.

### 8.8 Workload/backlog

Each organization-period has a latent workload/capacity ratio influenced by arrival bursts, case complexity, operating model, and capacity proxy. It affects queue delay, open-case count, investigation duration, and closure timing without deterministically causing a finding.

### 8.9 Asset criticality and monitoring coverage

Asset criticality is conditional on class/service profile. Coverage is high but imperfect, with onboarding/decommissioning and source-health states. Critical assets are generally more likely to be covered, but legitimate onboarding/maintenance and concerning gaps overlap.

### 8.10 Investigation notes

Notes are generated from several families:

- free-form case-specific narrative;
- approved runbook/template plus case-specific slots;
- automated enrichment block plus analyst conclusion;
- terse false-positive disposition;
- deliberately vague repetitive text;
- multilingual/format variation only if the team can validate it; otherwise defer.

Text length, lexical diversity, template use, and case-specific detail vary by entity/workflow. Exact duplicate rates are not tied directly to true labels.

### 8.11 Remediation activity

Action occurrence and completion depend on recurrence, severity, asset criticality, case conclusion, accepted risk, and workload. Time-to-action is long-tailed. A nontrivial set of normal cases has delayed/open remediation, and some concerning cases have superficial action records, preventing a trivial presence-only detector.

---

## 9. Scenario Realization Principles

### 9.1 Independent scenario selection

A scenario defines an operational condition, not a detector threshold. The planner:

1. selects entity-period candidates meeting broad semantic prerequisites;
2. chooses record groups using a scenario seed;
3. applies a structural or latent-behavior change;
4. preserves natural noise and overlap;
5. records intended evidence privately;
6. validates that the condition exists without requiring one exact detector output.

### 9.2 Prevalence

- Row-level concerning scenarios remain sparse relative to ordinary operations.
- Scenario-level evaluation has enough instances per family for interpretation.
- Legitimate unusual and ambiguous instances are intentionally common enough to punish “unusual equals bad.”
- Held-out prevalence may differ from development prevalence.
- Exact split counts are private and versioned; public operational manifests expose only overall row counts.

### 9.3 Correlation

Some scenarios intentionally share the same root records. The private truth defines an `independence_group`/correlation expectation so evaluation does not reward three findings when one multi-basis finding is appropriate.

### 9.4 Detector independence

The generator configuration may use domain-like latent factors and scenario effect ranges, but it must not import SAT-SA detector rules, priority bands, thresholds, model scores, or expected feature cutoffs. Generator and detector repositories/configurations should remain separately versioned.

---

## 10. Scenario Matrix — Execution Gaps and Negative Space

| ID | Realization in operational evidence | Intended family | Counterexample/ambiguity | Validation of realization |
|---|---|---|---|---|
| `EG-01` | Select serious closed alerts under an applicable workflow; remove qualifying investigation records while keeping investigation family complete; preserve natural closure times | Execution gap + negative space | Approved automated duplicate closure with automation/suppression evidence | Expected-universe alerts have no qualifying relationship; source scope mature/complete |
| `EG-02` | Select applicable serious cases; suppress escalation creation for subset without exception | Execution gap | Cases under workflow version where local escalation is not applicable | Applicability true, grace elapsed, escalation family complete |
| `EG-03` | Move investigation event time after closure or render source timestamps that imply it, without explanatory migration context | Cross-record inconsistency | Documented timezone/tool migration producing apparent ordering issue | Canonical reference retains exact order and context distinction |
| `EG-04` | Close selected applicable cases while omitting required disposition/approval fields/records | Execution gap | Workflow where approval is `NOT_REQUIRED` | Rule applicability and source family adequacy recorded privately |
| `EG-05` | Generate recurrent serious signature; omit linked action/remediation and accepted-risk exception | Execution gap + negative space | Recurrent alerts with completed remediation or active accepted risk | Recurrence exists; action family complete; no qualifying counterevidence |
| `NS-01` | Active critical assets have monitoring expectation but no matching coverage evidence in complete coverage submission | Negative space | Maintenance, onboarding, decommissioning, or explicit not-applicable interval | Expected universe, interval, source family, and exceptions checked |
| `NS-02` | Eligible alerts have no case/investigation evidence after maturation window | Negative space | Alert-only legitimate false-positive/suppression path | No linked case/investigation; submitted families complete |
| `NS-03` | Applicable case has no escalation evidence | Negative space | Emergency workflow redirects escalation with approved exception | Same realization checks as `EG-02`, evaluated as absence wording |
| `NS-04` | Recurring alerts lack remediation/accepted-risk evidence | Negative space | Delayed remediation still open and documented; accepted-risk control | Search spans related asset/alerts/cases/actions and adequate period |

No operational row receives the IDs above.

---

## 11. Scenario Matrix — Historical, Peer, Repetition, and Optional Anomaly

| ID | Realization | Intended family | Legitimate/ambiguous control | Anti-easiness property |
|---|---|---|---|---|
| `HIST-01` | Shift a selected entity’s closure-process latent mixture toward faster handling across a subset of comparable serious alerts in current period | Historical deviation | Approved automation shifts same metric with explicit change/exception | No exact time cutoff; distributions overlap |
| `HIST-02` | Reduce escalation propensity in current period for applicable cases while keeping severity mix broadly comparable | Historical deviation | Documented policy/workflow change changes applicable denominator | Rate shift is noisy, not all-or-none |
| `HIST-03` | Increase arrival/complexity relative to capacity, producing backlog and delay shift | Historical/workload deviation | Planned surge with documented staffing/emergency context | Workload affects several metrics imperfectly |
| `HIST-04` | Abrupt undocumented process parameter change | Historical/change lead | Documented tooling/workflow boundary | Same numerical shift, different evidence context |
| `PEER-01` | Move one eligible entity-period’s normalized metric distribution away from cohort while preserving denominator validity | Peer deviation | None for concern instance | Cohort overlap remains; not every metric deviates |
| `PEER-02` | Entity differs from cohort due to approved operating model/automation | Peer deviation with counterevidence | Legitimate unusual | Deviation magnitude can equal/exceed `PEER-01` |
| `REP-01` | Reuse vague normalized notes across diverse cases; remove case-specific slots while varying superficial tokens | Repetitive investigation | — | Not purely exact duplicates; includes paraphrase/noise |
| `REP-02` | Reuse approved runbook block but retain unique evidence, asset, conclusion, and action content | Repetitive pattern control | Legitimate unusual | High text similarity intentionally legitimate |
| `ANOM-01` | Create a rare multivariate combination of timing, recurrence, volume, and workflow features without a single deterministic rule violation | Optional anomaly lead | Rare but legitimate operating-model combination | Both positive/control rare points; no anomaly-score label |

### 11.1 Historical eligibility controls

For each historical scenario, create separate entity-periods with:

- insufficient history;
- incompatible process boundary;
- partial period;
- valid stable history;
- documented change.

The expected output can therefore be deviation, context-qualified deviation, or insufficient history.

### 11.2 Peer eligibility controls

For each peer scenario, create:

- matched eligible cohort;
- too-small cohort after quality filtering;
- denominator mismatch;
- source-definition mismatch;
- legitimate operating-model difference.

A detector must be able to abstain rather than fall back to all organizations.

---

## 12. Scenario Matrix — Cross-Record and Data Quality

| ID | Source mutation | Canonical/quality expectation | Legitimate/ambiguous control |
|---|---|---|---|
| `XREC-01` | Replace a case-alert foreign source ID with unresolved ID | Broken relationship; raw ID retained | External-system relationship explicitly marked outside submitted scope |
| `XREC-02` | Render closure time before creation time | Invalid temporal sequence | Timezone migration with documented mapping ambiguity |
| `XREC-03` | Case severity conflicts with linked alert severity | Consistency lead, not automatic error | Legitimate re-triage/impact reassessment |
| `XREC-04` | Repeat exact source record and create conflicting duplicate variant | Exact/conflicting duplicate states | Legitimate later revision with version/update time |
| `XREC-05` | Case status remains open while closure record exists | Contradictory state | Reopened case with explicit revision |
| `DQ-01` | Remove optional and required source fields under profile-specific mechanism | Correct `NOT_PROVIDED`/invalid states | Optional absence not used by analytics |
| `DQ-02` | Omit entire evidence family | Submission family `NOT_PROVIDED` | Provided family with explicit zero records |
| `DQ-03` | Render malformed timestamp/token | `INVALID`, original retained | Valid alternate format covered by mapping |
| `DQ-04` | Omit source-native IDs while preserving row locator | Canonical SAT ID + provenance; no failure | Source IDs present in other profiles |
| `DQ-05` | Drift column/key/status vocabulary in new source version | Schema/mapping version change or mismatch | Approved mapping/profile update |
| `DQ-06` | Partial submission with declared scope | `PARTIAL_PERIOD`; absence analytics limited | Undeclared partial submission as harder quality problem |
| `DQ-07` | Deliver prior-period record in later submission | Late-arrival revision | Ordinary timely record |
| `DQ-08` | Use local/no-offset timestamps | Mapping warning or invalid based on profile | Explicit-offset timestamp |
| `DQ-09` | Declare counts inconsistent with parsed rows | Submission quality issue | Correct manifest count |
| `DQ-10` | Supply invalid vocabulary value | Raw preserved, canonical `UNKNOWN`, warning | New value with approved mapping version |

### 12.1 Missing-state mutation mapping

| Intended condition | Source rendering | Canonical reference state |
|---|---|---|
| Explicit numeric/boolean zero | Field present with valid zero/false | `OBSERVED_ZERO` |
| Valid value | Field present and valid | `OBSERVED_VALUE` |
| Field omitted | Column absent, key absent, or empty under profile semantics | `NOT_PROVIDED` |
| Not applicable | Explicit applicability/exception context | `NOT_APPLICABLE` |
| Malformed value | Field present but unparsable/invalid | `INVALID` |
| Expected relation absent in adequate scope | No child/link after search conditions | `NO_SUBMITTED_EVIDENCE` |
| Scope cannot be determined | Incomplete/undeclared source context | `UNKNOWN` |

The generator never substitutes zero for any absent state.

---

## 13. Legitimate Unusual Catalogue

Every item below must occur as a first-class scenario or counterexample in development and held-out data.

| Legitimate condition | Evidence that makes it legitimate/contextual | Pattern that may look unusual |
|---|---|---|
| Approved automation | Active exception, automation state, rule/version, disposition | Very fast closures and repeated text |
| Maintenance window | Approved interval and affected assets/coverage | Missing monitoring evidence and low alerts |
| Approved suppression | Suppression rule, approval, scope, effective interval | Alert-only records or abrupt volume drop |
| Accepted risk | Active accepted-risk exception and owner/reference | Repeated alerts without remediation |
| Emergency process | Emergency exception/process change with interval | Different escalation path and timing |
| Policy/workflow change | Versioned Process Change and control/process link | Historical rate/time shift |
| Tool migration | Mapping/source version change, late arrivals, partial declaration | Broken-looking timestamps/IDs or category shift |
| Onboarding/decommissioning | Asset effective dates and coverage state | Critical asset lacking normal-period coverage |
| Different operating model | Organization profile and cohort eligibility | Peer deviation |
| Standard runbook usage | Runbook/template ID plus case-specific slots/evidence | Highly similar notes |
| Alert storm | Clustered signature, incident/case grouping, automation context | Volume spike and compressed handling |
| False-positive burst | Shared detection rule/disposition and tuning action | Fast closure, duplicate patterns |
| Legitimate re-triage | Case impact/context and change history | Severity mismatch |
| Reopened case | Explicit event/revision | Closed and later open states |

### 13.1 Control quality variation

Not all legitimate evidence is perfect. Some controls deliberately have incomplete approval text or limited source provenance and are labeled `AMBIGUOUS` privately. This tests uncertainty handling instead of rewarding only fully explicit controls.

---

## 14. Source Heterogeneity

### 14.1 Source profile catalogue

| Profile | Format/layout | Identifier behavior | Vocabulary | Timestamp behavior | Relationship representation |
|---|---|---|---|---|---|
| `SRC-A` | Multiple CSV files, snake_case, stable ordering | Most native IDs present | Canonical-like words | ISO 8601 with `Z` | Separate link file |
| `SRC-B` | CSV, mixed/Pascal headings and reordered columns | Some optional child IDs missing | Numeric/abbreviated severity/status | Local timestamps with declared IANA zone | Case ID embedded in alert/case files |
| `SRC-C` | Nested JSON objects by case | IDs present for parent, some generated children lack native IDs | Vendor-like text variants | ISO offsets with milliseconds | Alerts/activities nested arrays |
| `SRC-D` | JSON array/line-oriented export split by family | Mixed ID availability | Lowercase/free-text values including unknowns | Offset and date-only fields depending family | Reference arrays and external IDs |
| `SRC-E` | Versioned CSV/JSON hybrid after migration | Source IDs change namespace/version | Vocabulary drift between periods | Format/precision change at boundary | Old foreign key vs new link objects |

### 14.2 Mapping-profile contract

Each source profile defines:

- file discovery patterns and evidence family;
- delimiter/encoding/JSON object path;
- column/key to canonical field mapping;
- source-ID and namespace behavior;
- timestamp format, timezone assumption, and precision;
- vocabulary mapping version;
- relationship extraction/resolution;
- missing/empty token semantics;
- effective period/source-system version;
- known limitations.

### 14.3 Mapping validation

For each profile, canonical reference generation must prove:

- original field/path/value retained;
- each canonical typed value has correct field observation/state;
- source file and record locators resolve;
- optional source IDs do not break identity/provenance;
- unknown vocabularies remain `UNKNOWN` with raw values;
- source-to-canonical counts/revisions are explainable;
- a source record mapping to both Resolution and Closure preserves one-to-many provenance.

### 14.4 Schema drift

Schema drift is versioned, not random corruption. A source profile may rename a field, change token vocabulary, nest a relationship, or change time precision at a declared boundary. Separate negative scenarios omit the matching profile update to produce a true schema mismatch.

---

## 15. Investigation-Text Generation

### 15.1 Safe synthetic content model

Generate notes from wholly synthetic phrase libraries with slots for:

- synthetic asset alias and alert category;
- observed indicator class, not real indicator;
- steps performed;
- case-specific finding;
- evidence-reference token;
- conclusion/disposition;
- runbook/template identifier;
- remediation/follow-up reference.

No real incident narratives or copied security reports are used.

### 15.2 Text modes

| Mode | Variation | Intended role |
|---|---|---|
| Case-specific free text | High lexical/content variation | Ordinary investigations |
| Runbook plus specifics | High shared block, unique evidence/conclusion | Legitimate repetitive control |
| Automated enrichment plus analyst note | Repeated machine block, variable human conclusion | Automation control |
| Terse but case-specific | Short notes with unique key facts | Ambiguous/normal |
| Vague template | High similarity, superficial token changes, little case evidence | Concerning repetition |
| Exact duplicate | Identical normalized note across diverse cases | Strong but not sole signal |

### 15.3 Anti-shortcut constraints

- Some ordinary and legitimate notes are highly similar.
- Some concerning notes are paraphrased rather than exact duplicates.
- Template/runbook IDs are occasionally missing as ordinary data-quality variation.
- Text similarity alone does not determine private category.
- No scenario code or distinctive “suspicious” phrase appears in notes.

---

## 16. Scenario Allocation and Leakage Prevention

### 16.1 Split-first allocation

Organizations/periods/seeds are assigned to development, validation, and held-out builds before scenario parameters are instantiated. Scenario instances are then drawn independently within each split.

### 16.2 Leakage controls

- No shared scenario seed across splits.
- No record IDs copied across splits.
- No held-out scenario parameter file in detector workspace.
- Template phrase libraries have split-specific variants; common language remains possible but no unique label phrase is shared.
- Mapping/source profiles may be shared where needed, but held-out profile versions include unseen combinations/drift.
- Dataset versions and paths use neutral split codes, not scenario names.
- Row order is randomized deterministically within profile rules, not grouped by scenario.
- Ground truth joins by private stable identifiers, never by exposed scenario columns.

### 16.3 Generator-detector separation

At minimum, configuration directories and release permissions separate:

- generator base-distribution configuration;
- private scenario configuration/seed ledger;
- detector rule/model configuration;
- evaluation matching configuration.

A detector developer may inspect development truth but not held-out truth/seeds before outputs are sealed.

---

## 17. Dataset Splits

### 17.1 Development/training split

Purpose:

- develop ingestion mappings and analytics;
- fit optional unsupervised/novelty components where justified;
- debug evidence/provenance;
- expose scenario truth after generation.

Contents:

- deterministic fixture plus medium development dataset;
- public seeds and truth;
- all analytical families and counterexamples;
- several source profiles and process boundaries.

Rules derived solely from development data must be validated elsewhere.

### 17.2 Validation split

Purpose:

- select provisional thresholds/configuration;
- compare deterministic/statistical/optional ML methods;
- test false positives and evidence packages.

Properties:

- new seeds and scenario instances;
- similar high-level population but altered parameters/prevalence;
- some unseen source-profile combinations;
- truth accessible only after a validation run is sealed, or to a separate evaluator.

Repeated tuning on validation data requires a new validation version or is documented as reuse.

### 17.3 Held-out evaluation split

Purpose:

- final family-level detection and prioritization evaluation;
- end-to-end ingestion/provenance test;
- blinded manual-review comparison.

Properties:

- private master/scenario seeds;
- hidden scenario allocation and prevalence;
- novel combinations, not necessarily novel families;
- operational source exports only during run;
- truth and canonical reference released to evaluation harness after output sealing;
- no model/rule changes based on the same held-out result without declaring it consumed.

### 17.4 Blinded manual-review subset

The subset is stratified privately across:

- attention scenarios;
- legitimate unusual controls;
- normal cases;
- data-quality-only cases;
- ambiguous cases;
- high/medium/routine intended review value;
- multiple organizations/source profiles.

Reviewers receive only operational evidence packets and a neutral rubric. They do not receive SAT-SA priority initially, scenario labels, expected findings, or answer keys. After independent review, SAT-SA findings may be shown for usefulness/time comparison.

### 17.5 Optional model fitting

If Isolation Forest or another optional method is used:

- fit only on an explicitly identified development baseline;
- do not use hidden labels as features;
- do not fit on held-out data;
- freeze feature/model versions before held-out evaluation;
- report deterministic/statistical results separately and perform ablation.

---

## 18. Benchmark Tiers

All volumes are planning targets inherited from `DATA_SCHEMA.md`, not official requirements or validated performance claims.

| Tier | Organizations | Periods | Alerts | Cases | Investigations | Assets | Approx. package size | Role |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Small deterministic fixture | 2–3 | 2 | 500–2,000 | 100–500 | 150–800 | 50–250 | < 25 MB | Golden tests, mappings, provenance, deterministic regeneration |
| Medium development benchmark | 12–16 | 4–6 | 50,000–150,000 | 10,000–40,000 | 15,000–60,000 | 3,000–10,000 | 0.25–2 GB | Main development, history/peer/scenario validation |
| Large performance benchmark | 20 | 6 | 250,000–750,000 | 50,000–200,000 | 80,000–300,000 | 10,000–30,000 | 1–8 GB | Stress, memory, disk, stage timing |
| Held-out evaluation benchmark | 15 | 6 | Within medium target envelope initially | Proportional | Proportional | 3,000–10,000 | Measured after generation | Final end-to-end and manual-review evaluation |

Actions, escalations, resolutions, closures, coverage, provenance, quality, and source records count toward total records and storage.

### 18.1 Tier build policy

- The fixture is manually inspectable and deterministic.
- Medium is the first acceptance target for product development.
- Large is generated only after medium generation and ingestion are stable.
- Held-out size is chosen after medium benchmark results, without changing its private scenario design to make the detector look better.

---

## 19. Hidden Ground-Truth Specification

### 19.1 Required scenario fields

Each private scenario instance contains:

- `scenario_id` and `scenario_version`;
- dataset/generator/schema/mapping/scenario-catalog versions;
- affected organization and reporting period;
- affected operational/source/canonical record references;
- scenario type and intended analytical family/families;
- intended classification: `ATTENTION`, `LEGITIMATE_UNUSUAL`, `NORMAL`, `DATA_QUALITY_ONLY`, or `AMBIGUOUS`;
- expected finding category and acceptable matching constraints;
- expected evidence roles and source paths;
- expected counterevidence/exception behavior;
- confounding factors;
- mutation provenance: base values, changed/removed/added elements, and authorization;
- scenario seed and component seed label;
- correlation/independence group;
- expected abstention state where applicable;
- manual-review guidance and ambiguity notes.

### 19.2 Absent-evidence truth

For negative space, truth links to:

- expected-universe subject;
- relationship/evidence type expected;
- searched evidence families and period;
- observation-adequacy basis;
- private mutation confirming absence;
- relevant exception/counterexample state.

It never creates a fake missing child record.

### 19.3 Expected finding matching

Evaluation matching must tolerate valid implementation variation. It may match by entity, period overlap, finding family, affected-record overlap, and evidence roles rather than exact title or priority. Forbidden interpretations—such as “action definitely never occurred”—are evaluated separately.

### 19.4 Private generation audit

The audit records base-record hashes, mutation sequence, seed labels, before/after references, and validation outcomes. It is not SAT-SA’s application audit log and never enters operational evidence.

---

## 20. Generator Validation Strategy

### 20.1 Validation gates

| Gate | Scope | Failure rule |
|---|---|---|
| Configuration gate | Versions, seed ledger, profile/scenario references | Any unresolved reference fails build |
| Base-world schema gate | Required fields/types/vocabularies | Any unplanned invalidity fails build |
| Base relationship gate | Ownership and foreign relationships | Any unplanned broken link fails build |
| Base temporal gate | Event ordering/effective intervals | Any unplanned impossible sequence fails build |
| Scenario realization gate | Intended condition/counterevidence exists | Missing or over-broad realization fails build |
| Authorized-mutation gate | Post-mutation defect matches private ledger | Unexpected defect or unused authorization fails build |
| Source-render gate | Layout/profile semantics and parseability | Profile mismatch fails build unless scenario-authorized |
| Canonical/provenance gate | Exact source→canonical field/record trace | Missing/ambiguous unplanned lineage fails build |
| Distribution gate | Counts, tails, overlap, cohort variation | Material drift outside versioned envelope fails review/build |
| Leakage gate | Operational files/metadata/text/paths | Any truth token or predictive planted marker fails build |
| Reproducibility gate | Repeat generation | Hash mismatch fails build |
| Package gate | Manifest counts/hashes/binding | Any mismatch fails release |

### 20.2 Referential integrity

Validate:

- organization ownership across all records;
- submission/file/record/canonical chain;
- asset references stay within organization unless explicitly invalid scenario;
- case-alert and child references resolve or have authorized relationship observation;
- exception target and interval resolve;
- control/process links resolve;
- source IDs are unique only within their declared scope when present;
- optional missing source IDs still have unique source-record locators.

### 20.3 Temporal validation

Validate:

- reporting period start < end;
- effective start < end;
- ordinary event ordering and permitted open records;
- source update/ingestion may follow event time;
- late arrivals are scheduled in later submissions;
- process changes split eligible regimes;
- expected impossible-time mutations exactly match truth ledger;
- no silent time correction.

### 20.4 Submission and maturity validation

- family presence declarations agree with rendered files except authorized count/scope mutation;
- complete, partial, immature, and unknown periods are distinguishable;
- provided-zero differs from not provided;
- negative-space concern scenarios use sufficiently complete/mature scopes;
- incomplete controls yield expected indeterminate/data-quality conditions.

### 20.5 Missing-state validation

For each canonical analytical field and relationship:

- value/state compatibility follows `DATA_SCHEMA.md`;
- explicit zero is present in source;
- omitted field is `NOT_PROVIDED`;
- invalid retains original value;
- `NO_SUBMITTED_EVIDENCE` appears only after adequate search scope;
- `NOT_APPLICABLE` has applicability/exception basis;
- unknown scope yields `UNKNOWN`.

### 20.6 Scenario realization validation

A scenario validator uses ground truth privately to verify semantic realization, not detector success. Examples:

- `EG-01`: target alert is serious/closed, qualifying investigation absent, family complete, no active exception;
- `HIST-01`: current latent/distribution shift exists relative to generated history, without exact threshold requirement;
- `REP-02`: shared runbook text and case-specific evidence both exist;
- `LEG-01`: automation/suppression exception is approved, effective, and scoped;
- overlap scenario: affected records and independence group are correctly shared.

### 20.7 Legitimate-control validation

Every legitimate unusual instance must have the intended context record(s), effective interval, approval state where required, and evidence provenance. Missing control evidence downgrades private truth to `AMBIGUOUS` or fails the scenario, rather than silently retaining a legitimate label.

### 20.8 Distribution sanity

Review per organization/cohort/period:

- alert count and burstiness;
- severity/category mix;
- duration median/percentiles/tail;
- case-size distribution;
- investigation coverage and note similarity;
- escalation/action rates with valid denominators;
- backlog/open-case counts;
- asset/criticality/coverage mix;
- source-ID missingness and quality mutation rates;
- scenario prevalence and control balance.

Check for impossible uniformity, identical distributions, complete separation between private categories, or a single feature that reveals truth.

### 20.9 Duplicate validation

Exact duplicate, conflicting duplicate, legitimate revision, repeated alert, and duplicated submission are separate constructs. The validator confirms each has the required IDs/hashes/update/version behavior.

### 20.10 Ground-truth isolation scan

Scan all operational paths, filenames, headers, keys, values, free text, metadata, hashes’ source strings, and manifests for:

- scenario IDs/catalog names;
- truth field names;
- label tokens;
- mutation/debug annotations;
- private seed values;
- answer-key identifiers;
- split-specific marker phrases.

Also confirm the operational build process never reads the truth output after packaging except in the private validator/evaluator.

---

## 21. Data-Quality Mutation Plan

### 21.1 Mutation layers

1. **Ordinary source variability:** optional fields absent, source IDs missing, rounding, allowed unknowns.
2. **Submission quality:** missing families, partial/immature periods, count mismatch, late arrivals.
3. **Record quality:** malformed values, duplicates, broken references, contradictions.
4. **Schema evolution:** renamed/reordered fields, vocabulary change, layout change.
5. **Scenario-authorized defect:** intentionally impossible timestamps or unsupported states.

### 21.2 Mutation rate controls

Rates vary by source profile and entity-period rather than uniformly. Quality defects are sparse enough not to dominate, but numerous enough for robust handling. Some high-quality submissions contain operational concerns; some poor-quality submissions contain normal operations.

### 21.3 Failure behavior

The generator itself fails loudly on accidental contract violations. Deliberate invalid source records are allowed only when the private authorization specifies:

- mutation type;
- target source record/field/relationship;
- expected canonical value/quality state;
- expected downstream eligibility effect;
- scenario/version/seed;
- validation assertion.

---

## 22. Evidence Traceability Generation

### 22.1 Source-first provenance

Every rendered source record receives:

- source file ID and exact path in package;
- stable row/JSON locator;
- source-native record ID when profile supplies it;
- raw logical record SHA-256;
- source system/version and reporting submission;
- parser/profile version reference.

### 22.2 Canonical field provenance

The canonical reference builder creates for each analytical field:

- canonical record/family/field;
- typed normalized value or explicit value state;
- source record/file;
- original field/path and lexical value;
- mapping/transform version;
- field-quality status and diagnostic.

### 22.3 Relationship provenance

Case-alert, case-investigation, escalation, action, coverage, and other relationships retain source foreign ID/path or relationship file/object. Expected-but-absent relationships use Relationship Observation with search scope; they never invent target records.

### 22.4 Finding readiness

The dataset itself does not contain findings. It guarantees that later findings can navigate:

`Finding → Evidence Link → Canonical Field/Relationship → Source Record → Source File → Submission → Manifest/Hash`.

---

## 23. Manual-Review Prioritization Evaluation Design

### 23.1 Review universe

The hidden evaluator constructs candidate review items from scenario-linked and sampled non-scenario records, but SAT-SA independently creates its own queue. Matching compares whether relevant entity/finding/sample evidence appears within review budgets.

### 23.2 Priority evaluation labels

Private truth may define acceptable review-importance ranges, but not a fake numeric “risk truth.” It distinguishes:

- should receive early supervisory attention;
- useful routine review;
- legitimate unusual/control;
- data-quality-first review;
- ambiguous/context required;
- ordinary background.

### 23.3 Avoiding circular priority evaluation

- Ground-truth importance derives from scenario impact/scope and review rationale, not SAT-SA’s factors/weights.
- Legitimate unusual cases can have high apparent severity but should not be rewarded as early operational concern when context is visible.
- Data-quality-only items are evaluated separately from operational concerns.
- Correlated scenarios count once at the root-group level where specified.

### 23.4 Metrics enabled later

The dataset supports precision@k, recall@k, review yield, effort reduction, time-to-first relevant item, family coverage, and manual reviewer agreement. This specification does not claim target values.

---

## 24. Scale and Performance Measurement

### 24.1 Generator measures

- total logical/source/canonical/provenance record counts;
- records generated per second by family;
- total generation wall time;
- validation time;
- package serialization/hashing time;
- peak memory;
- temporary/final disk usage;
- operational/truth/evaluation package sizes;
- compression ratio if deterministic archive used.

### 24.2 SAT-SA pipeline measures using generated data

- source ingestion time;
- parsing/validation time;
- normalization/provenance time;
- analytical run and per-module time;
- peak memory and disk growth;
- finding/evidence correlation time;
- queue/report generation time;
- UI query latency where later measured.

### 24.3 Selecting final size

1. Generate deterministic fixture and verify exact correctness.
2. Generate lower medium envelope and run ingestion/analytics benchmarks.
3. Increase along one dimension at a time: records, text length, entities/periods, relationship density.
4. Identify resource bottleneck and optimize implementation without altering scenario semantics.
5. Freeze a medium target that completes reliably on declared demo hardware with margin.
6. Define large stress tier separately; failure at stress tier does not invalidate a transparently reported medium target.

No claim of records/second or maximum capacity is made until measured on declared hardware and release versions.

---

## 25. Synthetic Privacy, Safety, and Security Rules

### 25.1 Prohibited content

No real:

- organization/CSE name or identifying profile;
- employee/analyst/customer name;
- email/phone/address;
- credentials, keys, tokens, passwords, or secret material;
- IP/hostname/domain/infrastructure identifier unless from an approved documentation-only range and necessary;
- incident narrative, ticket, malware sample, packet, or operational log;
- classified, personal, customer, or sensitive operational data.

Prefer synthetic asset aliases over IP addresses. All text is generated from original synthetic phrase libraries.

### 25.2 Identifier safety

Use clearly synthetic identifiers such as `CSE-007`, `AST-007-0042`, and neutral opaque deterministic IDs. Do not mimic known organizations, vendors, employees, or actual incidents. Optional source IDs may be absent according to source profile.

### 25.3 File safety

Generated source files are passive CSV/JSON only. Free text does not contain executable markup. Values that begin with spreadsheet formula characters may appear only in a dedicated safety-validation case and must be treated as text; no executable formulas/macros are generated.

### 25.4 Truth-package handling

Held-out truth and seeds are sensitive to evaluation validity, not operational classification. Access is restricted to the evaluation owner; release logs must not print truth rows or seeds.

---

## 26. Manifest and Release Contracts

### 26.1 Operational manifest minimum fields

- dataset ID/version, tier, split alias;
- generator version/build hash;
- schema/profile/mapping/vocabulary versions;
- public seed alias;
- organization and period counts;
- family/file/record counts;
- source layout/profile assignments that are safe to disclose;
- deterministic serialization version;
- each file hash/size/media type;
- tree hash;
- synthetic/privacy declaration;
- public limitations;
- build validation summary that contains no scenario results.

### 26.2 Ground-truth manifest

- exact operational package tree hash;
- truth package version/hash;
- scenario catalog version;
- private master/scenario seed ledger hash and encrypted/restricted details;
- scenario counts by family/category;
- expected-finding matcher version;
- generation audit hash;
- truth validator results.

### 26.3 Evaluation manifest

- operational and truth package hashes;
- split and reviewer subset definition;
- output-seal procedure;
- matching/metric versions;
- benchmark environment fields;
- evaluator/reviewer assignments;
- result package hash.

### 26.4 Release immutability rule

A sealed release is never edited in place. Any record, scenario, mapping, manifest, or documentation change creates a new dataset version and new hashes. This is version discipline, not a claim that filesystem bytes are physically immutable.

---

## 27. Generator Implementation Boundary

### 27.1 Defined now

The future generator must implement:

- three separately packaged data domains and private package binding;
- 15-organization main population with three useful cohort contexts;
- 4–6 periods, preferably six for main datasets;
- period maturity, partiality, missing families, late arrivals, revisions, and process boundaries;
- every operational evidence family in `DATA_SCHEMA.md`;
- five source layout profiles and versioned mappings;
- heterogeneous long-tailed operational distributions;
- concerning, legitimate unusual, normal, ambiguous, quality-only, and overlapping scenarios;
- source/canonical/provenance reference generation;
- strict ground-truth isolation and split-first allocation;
- deterministic named seed streams and byte-stable serialization;
- validation gates, authorized mutation ledger, leakage scanning, and hashing;
- benchmark tiers and performance measurement fields;
- synthetic privacy rules.

### 27.2 Deferred to generator implementation planning

- programming language/module layout for the generator;
- concrete configuration-file syntax;
- exact numeric distribution parameters and final scenario counts;
- exact synthetic period dates;
- exact note phrase library;
- physical file partition sizes and archive choice;
- dependency versions and CI workflow;
- implementation of validators, serializers, hashers, and split controls;
- final target size after benchmark;
- actual generated CSV/JSON/reference/truth files;
- detector algorithms, thresholds, ML features, application/backend/frontend, SQL schema, and dashboard.

### 27.3 Forbidden during implementation

- importing detector rules/thresholds into scenario generation;
- exposing truth to analytics or UI;
- silently repairing intentional source defects;
- generating sensitive/real data;
- labeling every unusual case as attention-worthy;
- altering authoritative project/schema documents to fit generator shortcuts;
- claiming realism or performance without validation.

---

## 28. Open Questions Before Generator Implementation

1. What exact synthetic UTC boundaries and durations define `P01`–`P06`?
2. Which final parameter envelopes produce credible volumes/durations without resembling a toy threshold generator?
3. Which organizations receive which source profiles and migration versions in each split?
4. How many instances per scenario family are needed for stable family-level validation while keeping natural prevalence?
5. Which scenario parameters remain private even after development release?
6. What exact safe text and field-length limits will the generator enforce?
7. Which canonical reference artifacts are distributed to developers versus withheld evaluators?
8. Who controls held-out seeds/truth and seals analytical outputs?
9. What target hardware determines medium and large benchmark feasibility?
10. What manual-review subset size is feasible for at least two independent reviewers?
11. Which provisional demo control/process expectations are approved for generation, and how will they be labeled?
12. Does the team need JSON Lines support, or are CSV and JSON array/object exports sufficient?
13. How will deterministic archive metadata be implemented if packages are compressed?
14. Which ambiguous scenarios should accept multiple correct examiner dispositions?
15. What criteria retire a generated release after leakage or realism defects are found?

---

## 29. Dataset Generation Readiness Checklist

| Requirement | Status | Evidence in this specification | Remaining action/blocker |
|---|---|---|---|
| Operational/ground-truth/evaluation package separation | **PASS** | §§2, 16, 19, 26 | Implement and test access boundary |
| No truth labels or scenario markers in operational package | **PASS** | §§2.2, 16.2, 20.10 | Automated leakage scanner required |
| Versioning, named seeds, reproducibility, hashes | **PASS** | §4 and §26 | Choose implementation/dependency versions |
| 12–20 heterogeneous organizations | **PASS** | 15-organization plan in §5 | Freeze exact public profiles |
| Useful peer cohorts of about five | **PASS** | Three cohorts of five | Validate metric-specific eligibility later |
| 4–6 reporting periods | **PASS** | Six-period main plan in §6 | Freeze synthetic boundaries |
| Complete/partial/immature/missing-family periods | **PASS** | §§6.2, 6.5, 20.4 | Freeze split-specific allocation |
| All `DATA_SCHEMA.md` evidence families | **PASS** | §7 dependency pipeline | Implement exact fields/mappings |
| Source files/records/canonical provenance | **PASS** | §§7, 14, 22 | Build canonical oracle and lineage tests |
| Heterogeneous, long-tailed distributions | **PASS** | §8 | Calibrate numeric parameters through generation review |
| Execution-gap scenarios and controls | **PASS** | §10 | Freeze scenario instance counts/seeds |
| Negative-space scenarios and adequate scope | **PASS** | §10 and §20.4 | Implement completeness/maturity validator |
| Historical deviations and process boundaries | **PASS** | §§6.4, 11.1 | Choose effect-size envelopes independently of detector |
| Peer deviations and legitimate peer differences | **PASS** | §§5, 11.2 | Validate cohort overlap/ineligibility |
| Repetition concerns and runbook controls | **PASS** | §§11, 15 | Create original safe phrase library |
| Cross-record/data-quality mutations | **PASS** | §§12, 21 | Implement authorized mutation ledger |
| Legitimate unusual catalogue | **PASS** | §13 | Ensure every held-out family has controls |
| Optional anomaly-supporting cases | **PASS** | `ANOM-01` in §11 | Evaluate usefulness later; no model commitment |
| Non-omniscient generator design | **PASS** | §§8–9, 16.3 | Keep detector config physically separate |
| Missing-state semantics | **PASS** | §12.1 and §20.5 | Validate every canonical field observation |
| Multiple CSV/JSON source layouts | **PASS** | §14 | Decide JSON Lines question |
| Ground-truth structure and mutation provenance | **PASS** | §19 | Implement private schema exactly |
| Development/validation/held-out splits | **PASS** | §17 | Assign owners and seed custody |
| Blinded manual-review subset | **PASS** | §§17.4, 23 | **OPEN:** reviewer count and feasible subset size |
| Benchmark tiers | **PASS** | §18 | Final held-out volume after medium benchmark |
| Generator validation/fail-loud behavior | **PASS** | §20 | Implement gates before release |
| Privacy and safety | **PASS** | §25 | Review phrase/identifier libraries |
| Exact numeric generation parameters | **OPEN** | Deliberately deferred | Parameter calibration/review required before coding |
| Target hardware/performance acceptance | **OPEN** | §24 design only | Hardware and benchmark acceptance must be agreed |
| Generator implementation technology | **OPEN** | Deliberately deferred | Decide in implementation plan; no code yet |

### 29.1 Remaining blockers before generator implementation

1. Approve synthetic period boundaries and exact organization/source-profile matrix.
2. Approve numeric parameter envelopes and scenario-instance counts without referencing detector thresholds.
3. Assign custody for held-out seeds, truth, and output sealing.
4. Approve project-demo control/process expectations used for applicability scenarios.
5. Decide target benchmark hardware and first medium-tier volume.
6. Decide manual-review subset size and reviewer availability.
7. Resolve JSON Lines/archive choices and deterministic serialization details.
8. Review the generator plan specifically for leakage, circularity, and synthetic privacy before any code is written.

No dataset has been generated. The specification is ready for design review, but generator implementation should begin only after the open blockers above have owners or approved assumptions.
