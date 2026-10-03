# GENERATOR_IMPLEMENTATION_PLAN.md

## SAT-SA Synthetic Dataset Generator — Implementation Blueprint

| Field | Value |
|---|---|
| Project | SAT-SA — Supervisory Analytics Tool for SOC Assessment |
| SIH problem statement | SIH 2026 — SIH26157 |
| Phase | Generator implementation planning after Phase 4 design |
| Direct authority | `DATASET_GENERATION_SPEC.md` |
| Governing documents | `PROJECT_SPEC.md`, `RESEARCH_REPORT.md`, `ARCHITECTURE.md`, `DATA_SCHEMA.md` |
| Purpose | Implementation-ready blueprint for a future offline synthetic dataset generator |
| Scope | Generator architecture, configuration, generation, private truth, validation, packaging, tests, and milestones only |
| Current state | No generator code and no dataset generated |

> **Hard boundary:** Operational evidence, hidden ground truth, and private evaluation material are separate artifacts with separate access paths. SAT-SA analytics will never receive hidden truth.
>
> **Implementation rule:** The generator models operational conditions independently. It must never query, import, or reproduce detector thresholds merely to create detectable positives.

### Decision labels

- **FACT** — required by the authoritative documents.
- **PROJECT DECISION** — implementation choice made in this plan.
- **ASSUMPTION** — condition that must be verified during implementation.
- **OPEN QUESTION** — unresolved choice retained explicitly.

---

## 1. Implementation Principles

| Principle | Invariant | Why it matters |
|---|---|---|
| Physical and logical truth separation | Operational, truth, and evaluation packages use different output roots, manifests, permissions, and APIs | Prevents accidental feature/label leakage and preserves evaluation validity |
| Generator-detector separation | Generator packages/configuration do not import SAT-SA analytics, rule, priority, or model configuration | Prevents circular success and threshold-shaped data |
| Detector-independent scenarios | Scenarios describe operational conditions and evidence changes, never “make score exceed X” | Allows multiple valid detection approaches and meaningful false negatives |
| Deterministic named random streams | Every component uses a stable child stream derived from master seed + stable label | Changes to notes must not alter alert counts or unrelated records |
| Reproducible builds | Same frozen version tuple and seed ledger produces identical logical output and bytes | Enables debugging, audit, golden tests, and fair comparisons |
| Fail-loud validation | Unexpected schema, relationship, temporal, provenance, leakage, or hash failure stops release | Prevents silent corruption from becoming benchmark truth |
| No silent repair | Intentional defects remain in source output; canonical reference records the expected invalid/missing state | Preserves data-quality scenarios and prevents generator from hiding its own mutations |
| No real/sensitive data | Identifiers, narratives, organizations, people, and infrastructure are synthetic | Prevents privacy/security risk and accidental operational disclosure |
| No label leakage | No truth field, scenario token, seed, mutation marker, filename, row order, or phrase reveals truth | Ensures the detector must infer from operational evidence |
| Source-first provenance | Source file/record/field/raw value precedes canonical reference generation | Makes later finding-to-source traceability testable |
| Schema-valid base world | Unmutated world passes strict schema/referential/temporal checks | Ensures every defect has an explicit cause rather than generator sloppiness |
| Authorized mutations only | Every deliberate defect has a private authorization/expected-state record | Separates intended test defects from implementation bugs |
| Legitimate unusual cases are first-class | Controls use the same scenario machinery, not afterthought flags | Punishes “unusual equals bad” and supports false-positive evaluation |
| Independent human evaluation | Blinded review packets and assignments contain no hidden truth or initial SAT-SA score | Reduces anchoring and preserves manual-review comparison |
| Offline operation | Dependencies, configuration, wheels, documentation, and artifacts are local | Matches SAT-SA’s air-gapped direction and makes builds reproducible |
| Minimal dependency surface | Prefer standard library and already selected project stack | Reduces packaging, supply-chain, and determinism risk |

**FACT:** The generator is an evaluation/data artifact producer. It does not implement SAT-SA analytics, findings, prioritization, or ML.

---

## 2. Recommended Technology Stack

### 2.1 Selected stack

| Technology | Purpose | Selection | Why / constraint |
|---|---|---|---|
| Python 3.12.x | Generator runtime and CLI | **Mandatory** | Matches project direction; strong data/testing ecosystem; pin exact patch release for byte reproducibility |
| NumPy | Deterministic random streams, vectorized sampling, numeric arrays | **Mandatory** | Use pinned bit generator/version; centralizes stochastic behavior |
| Polars | Columnar family generation, joins, validation summaries, scalable CSV/column operations | **Mandatory** | Fits architecture direction and medium/large generation without pandas dependency by default |
| SciPy | Selected distributions and statistical sanity tests not provided cleanly by NumPy | **Optional, approved** | Include only when a named distribution/test genuinely needs it; do not make base fixture depend on it unnecessarily |
| Pydantic v2 | Validate configuration, manifests, private authorization records, and in-memory contract objects | **Mandatory** | Fail-fast typed validation without defining SQL |
| Python `dataclasses` / typed protocols | Lightweight immutable internal domain plans/interfaces | **Mandatory standard library** | Avoid using Pydantic for every high-volume row when performance is unnecessary |
| `json`, `csv`, `tomllib` | Deterministic JSON/CSV serialization and TOML loading | **Mandatory standard library** | Small, offline, explicit dialect/control |
| PyYAML | Human-editable complex catalogs | **Not selected initially** | JSON/TOML + Pydantic avoids another parser and YAML ambiguity; reconsider only if configuration becomes unmanageable |
| DuckDB | Large-build validation queries and benchmark summaries | **Optional development dependency** | Useful for high-volume referential/distribution checks; not generator source of truth and not required for fixture generation |
| `hashlib` and `hmac` | SHA-256 file/tree/config hashes and private seed derivation/aliasing | **Mandatory standard library** | No external cryptographic dependency required for deterministic derivation/integrity hashes |
| `uuid` | UUID representation and namespace-based deterministic IDs | **Mandatory standard library** | IDs derived from stable logical identity; never from scenario label in operational artifacts |
| Faker | Names/addresses/general fake data | **Not selected** | SAT-SA does not need realistic personal data; Faker increases dependency and real-looking privacy risk |
| pytest | Unit, contract, integration, golden, leakage, and reproducibility tests | **Mandatory dev dependency** | Standard test runner and fixtures |
| Hypothesis | Property tests for identities, timestamps, relationships, value states, and serializer invariants | **Mandatory dev dependency once vendored** | Stronger invariant coverage; wheel must be present offline |
| Ruff | Formatting/lint/static hygiene | **Recommended dev dependency** | Fast and small; does not affect generated data |
| mypy or Pyright | Type checking generator interfaces/contracts | **Recommended dev dependency** | Helps keep scenario/operational/private types separated |

### 2.2 Environment and packaging

**PROJECT DECISION:** Use `pyproject.toml` for package metadata and tool configuration, plus fully pinned generator and development lock exports with hashes. Maintain an offline wheelhouse for Python 3.12 and the target OS/architecture.

Required release metadata:

- exact Python implementation and patch version;
- exact dependency versions/hashes;
- generator build commit/archive hash;
- locale and timezone (`C.UTF-8`/UTC or declared equivalents);
- source encoding and serialization version;
- supported target platforms.

The generator CLI should use `argparse` initially. Typer/Rich are unnecessary unless later usability testing justifies them.

### 2.3 Determinism warning

A fixed random seed alone is insufficient. NumPy, Polars, serializer, Python, and dependency versions remain part of the build identity. Upgrading them requires reproducibility/golden revalidation and a new generator/dataset version where bytes or semantics change.

---

## 3. Repository and Module Structure

### 3.1 Proposed repository structure

```text
generator/
  pyproject.toml
  README.md
  requirements/
    generator.lock
    development.lock
    wheelhouse_manifest.json

  config/
    public/
      base/
      organizations/
      cohorts/
      distributions/
      source_profiles/
      vocabularies/
      scenarios/catalog/
      splits/
      benchmarks/
      serialization/
    private/                    # never committed to public repository
      scenarios/instances/
      seeds/
      held_out/
      evaluation/

  src/satsa_generator/
    cli/
    core/
    config/
    seeds/
    ids/
    population/
    periods/
    evidence/
      organizations/
      controls_processes/
      submissions/
      assets/
      monitoring/
      alerts/
      cases/
      investigations/
      escalations/
      actions/
      resolutions/
      closures/
      exceptions/
      process_changes/
    scenarios/
      catalog/
      selection/
      mutation/
      controls/
      validation/
    quality/
    rendering/
      profiles/
      csv/
      json/
    canonical/
    provenance/
    ground_truth/
    splits/
    evaluation/
    validation/
    leakage/
    packaging/
    benchmarks/

  tests/
    unit/
    contract/
    property/
    integration/
    golden/
    mutation/
    leakage/
    reproducibility/
    end_to_end_fixture/

  fixtures/
    expected_small/             # approved golden hashes/manifests, not private truth

  artifacts/                    # generated; ignored by version control
```

### 3.2 Module responsibility and dependency contract

| Module | Responsibility | Inputs | Outputs | May depend on | Must not know about |
|---|---|---|---|---|---|
| `core` | Shared immutable types, errors, build context, stage-result protocol | None | Common contracts | Standard library only | Scenarios, detector, rendering details |
| `config` | Load, validate, resolve, freeze, hash configuration | Public/private config roots | Frozen typed config snapshots | `core`, Pydantic | Generated rows, detector config |
| `seeds` | Master/child derivation, private ledger, public aliases | Frozen build config, master seed | Named RNG handles and seed ledger refs | `core`, NumPy, HMAC | Operational records or scenario semantics |
| `ids` | Stable deterministic UUID/source-ID policy | Dataset namespace and logical keys | IDs | `core`, seed-independent UUID/hash utilities | Private labels in operational IDs |
| `population` | Build organizations, cohorts, persistent latent profiles | Public population config, population RNG | `PopulationPlan` | `core`, `config`, `seeds`, `ids` | Scenario allocations, detector |
| `periods` | Build P01–P06, maturity, submission/source schedules | Population plan, period config/RNG | `PeriodPlan`, `SubmissionPlan` | Population and core services | Findings, detector thresholds |
| `evidence/*` | Generate base-world schema families | Plans, upstream evidence, family RNG | Operational world family records | Only upstream evidence modules | Source renderer internals, truth labels |
| `scenarios/catalog` | Define operational condition contracts and required prerequisites | Public scenario catalog | Scenario definitions | `core`, schema enums | Private instances/seeds, detector |
| `scenarios/selection` | Select eligible subjects and reserve overlap/exclusion | Base world, private instance config/RNG | Private `ScenarioPlan` | Catalog, read-only evidence index | Rendering, detector results |
| `scenarios/mutation` | Apply authorized behavioral/evidence changes | Base world copy, scenario plan | Mutated world + private mutation receipts | Selection/catalog/evidence types | Detector thresholds/scores |
| `scenarios/controls` | Realize legitimate/ambiguous unusual context | Base world, control plan | Operational context records + receipts | Scenario interfaces, evidence types | Finding/priority implementation |
| `scenarios/validation` | Confirm each private scenario exists semantically | Mutated world, plan, receipts | Scenario validation report | Read-only evidence + private truth | Detector outputs during generation |
| `quality` | Apply authorized source/record/schema quality mutations | Operational world/render plan, private authorizations | Mutated source-world plan + receipts | Core, profiles, IDs | Detector behavior |
| `rendering` | Serialize operational world into SRC-A…E layouts | Mutated operational world, source profiles | Source files and render index | Config, IDs, serializers | Ground-truth classifications |
| `canonical` | Independently map rendered source into expected canonical reference | Source files, public mapping/vocab config | Canonical oracle | Rendering outputs, mappings | Scenario truth; detector code |
| `provenance` | Build source file/record/field/relationship lineage | Render index + canonical mapping trace | Provenance oracle | Rendering/canonical | Expected findings/labels |
| `ground_truth` | Write private scenario/record/evidence/mutation truth | Scenario plans/receipts/validation | Hidden truth package | Private scenario APIs, IDs | Operational writer/output API |
| `splits` | Freeze split membership and seed namespaces | Split config | Split plan | Config/seeds/population planner | Detector results |
| `evaluation` | Build blinded review packets and private matching manifests | Sealed operational refs + private truth | Evaluation package | Packaging refs, truth reader | SAT-SA analytics implementation |
| `validation` | Run staged contract/integrity/distribution gates | Build-stage outputs | Machine/human validation reports | Read-only access to relevant layers | Mutating data to “fix” failures |
| `leakage` | Scan operational output for truth/seed/split leakage | Operational package + private forbidden fingerprint set | Leakage findings | Packaging/read-only truth fingerprints | Modifying operational data automatically |
| `packaging` | Deterministic serialization tree, hashes, manifests, package binding | Validated outputs | Sealed packages | Config, hashes, stage outputs | Scenario selection logic |
| `benchmarks` | Measure generator stages/resources | Build stage telemetry | Benchmark report | Core and packaging metadata | Performance promises or detector logic |
| `cli` | Orchestrate approved commands and exit codes | User command/path arguments | Build/report operations | Public service interfaces only | Direct row mutation or private seed content |

### 3.3 Dependency direction

```text
core
  -> config -> seeds / ids
  -> population -> periods -> base evidence families
  -> scenario selection -> scenario/control mutation -> quality mutation
  -> source rendering -> canonical/provenance oracle
  -> ground truth / split evaluation artifacts
  -> staged validation -> leakage scan -> packaging/hashing
```

Cross-cutting validation reads stages but does not write them. `ground_truth` may consume private receipts; operational evidence, rendering, canonical, and provenance modules cannot import `ground_truth`.

### 3.4 Circular-dependency prevention

- Interfaces and enums live in `core`, not downstream packages.
- Evidence modules return immutable family batches/indices through core protocols.
- Scenario modules reference evidence via IDs/index queries, not imports of each family’s implementation.
- Renderers depend on public source-profile contracts, not evidence generator classes.
- Validation uses read-only adapters and returns reports.
- No module loads detector source/configuration.

---

## 4. Configuration Architecture

### 4.1 Configuration domains

| Domain | Example contents | Visibility | Versioning |
|---|---|---|---|
| Public base generation | dataset namespace, period count, enabled families, global safety limits | Developer/public | Semantic version + canonical hash |
| Source profiles | SRC-A…E layouts, columns/keys, timestamps, ID/relationship representation, serializers | Developer/public | Profile ID/version/hash/effective period |
| Vocabularies | Canonical/source severity, status, disposition, category mappings | Developer/public | Vocabulary/mapping version/hash |
| Organization/cohort | 15 synthetic public profiles and allowed parameter envelopes | Developer/public | Population config version/hash |
| Distribution | Distribution families and parameter envelopes/constraints | Developer/public for development; held-out parameter draws private | Version/hash |
| Scenario catalog | Scenario semantics, prerequisites, allowed mutation types, validator IDs | Developer/public | Scenario catalog version/hash |
| Private scenario instances | Exact allocation, subject counts, effect draws, confounders, overlap groups | Private by split | Instance manifest version/hash |
| Split | Development/validation/held-out organization/seed namespace rules | Public at high level; held-out exact allocation private | Split version/hash |
| Benchmark | Tier dimensions and enabled diagnostics | Developer/public | Benchmark config version/hash |
| Serialization | CSV dialects, JSON mode, encoding, ordering, rounding, archive policy | Developer/public | Serialization version/hash |
| Private seed custody | Master seeds, child-ledger bindings, seed aliases | Restricted private | Seed-ledger version/hash |
| Evaluation | Blind sample allocation, answer-key binding, output-seal rules | Restricted private | Evaluation config version/hash |

### 4.2 File format

**PROJECT DECISION:** Use TOML for simple human-maintained base/benchmark/serialization settings and JSON for structured catalogs, mappings, organizations, scenario instances, and manifests. All loaded content is validated through Pydantic models and normalized into canonical JSON before hashing.

Reasons:

- standard-library TOML parser;
- deterministic JSON serialization;
- no YAML implicit typing or unsafe loader risk;
- explicit list/object shapes consistent with `DATA_SCHEMA.md`.

### 4.3 Configuration precedence

Allowed precedence:

1. versioned defaults;
2. selected tier config;
3. split config;
4. explicitly named build override file.

Environment variables may specify paths and private seed input only. They cannot silently override generation parameters. CLI flags select configuration files/versions, output root, and safe runtime limits—not distributions or scenario truth ad hoc.

### 4.4 Freeze process

Before generation:

1. load all required public/private configs;
2. validate references and version compatibility;
3. resolve inheritance/overrides;
4. materialize exact effective configuration;
5. redact private seed values from public snapshot;
6. serialize canonical public and private snapshots separately;
7. hash both;
8. write them to build workspace;
9. prohibit mutable config access during stages.

### 4.5 Detector-threshold prohibition

Configuration schema has no keys named for detector thresholds, finding priority weights, anomaly contamination, model parameters, or expected SAT-SA scores. A static validation rule rejects imports/references to detector configuration paths.

---

## 5. Seed and Deterministic-ID Architecture

### 5.1 Master seed

- Use a 256-bit master seed supplied as private binary/hex input.
- Development fixture master seed may be published.
- Validation/held-out seeds remain under designated custodian control.
- Never derive private seed from dataset name, date, organization ID, or low-entropy integer.

### 5.2 Child derivation

**PROJECT DECISION:** Derive child entropy with HMAC-SHA-256 using the master seed as key and a UTF-8 stable label as message. Feed the resulting entropy into a pinned NumPy `SeedSequence`/`PCG64DXSM` generator.

Stable labels follow a declared grammar:

```text
<split>/<component>/<organization>/<period>/<family>/<purpose>/<version>
```

Unused dimensions are omitted according to documented rules. Labels are unique and registered; duplicate labels fail configuration validation.

### 5.3 Random stream registry

The registry returns a named RNG handle and records only label + non-secret stream fingerprint in public diagnostics. It refuses unnamed/default RNG creation. Direct use of Python global `random`, NumPy global random state, system time, process ID, or nondeterministic hash iteration is prohibited.

### 5.4 Isolation example

- Alert counts use `development/alerts/CSE-001/P01/count/v1`.
- Alert attributes use `development/alerts/CSE-001/P01/attributes/v1`.
- Investigation notes use `development/notes/CSE-001/P01/template/v1`.

Changing note templates/version changes only note streams. Alert count/identity streams remain unchanged.

### 5.5 Deterministic IDs

- Use a dataset-version namespace UUID plus stable logical key to derive canonical UUIDs.
- Logical keys use public operational identity (organization, period, family, ordinal/source locator), never scenario ID/classification.
- Source-native IDs are rendered by source profile and may be absent.
- Scenario truth references operational IDs after they are assigned; operational IDs are never derived from truth labels.
- Changing row sort must not change logical IDs.

### 5.6 Split seeds and custody

- Each split has an independent 256-bit master seed, not a child disclosed from another split.
- Held-out seed is injected only in restricted build environment.
- Public seed alias is an independently generated opaque UUID mapped privately to the seed; it is not a hash of a low-entropy seed.
- Private seed ledger is encrypted/restricted according to team environment; encryption mechanism is an implementation deployment decision.

### 5.7 Seed serialization

Private ledger records seed bytes in one canonical representation, bit-generator name/version, derivation grammar/version, stream labels, and fingerprints. Public manifest stores only alias and derivation-version identifier.

---

## 6. Synthetic World Generation Pipeline

### 6.1 Stage contract

Every stage receives an immutable `BuildContext`, explicit upstream artifacts, and named seed provider. It returns:

- immutable stage artifact or content-addressed snapshot;
- stage manifest with counts/hashes/version;
- validation summary;
- deterministic telemetry;
- success/failure status.

No stage edits an upstream artifact in place.

### 6.2 Pipeline table

| Stage | Inputs | Outputs | Seed stream | Immediate validation | Failure behavior |
|---|---|---|---|---|---|
| Config Freeze | Selected public/private configs | Frozen config snapshots/hashes | None | Schema, reference, version, forbidden-key checks | Stop before any generation |
| Seed Initialization | Master seed(s), derivation version | Seed registry/ledger refs | Master | Label uniqueness and deterministic known-answer test | Stop; do not log secret |
| Population | Cohort/org config | 15 organization profiles and latent parameters | `population/*` | Counts, cohort membership, overlap/diversity constraints | Stop |
| Periods | Population, period/split config | P01–P06 and period/submission plan | `periods/*` | Ordered boundaries, maturity/source schedule validity | Stop |
| Control/Process References | Population, approved demo catalogue | Reference/link base plan | `controls/*` only for optional selection | Valid authority labels/effective intervals | Stop |
| Assets | Population + periods | Asset profile/revision graph | `assets/<org>` | Ownership, active intervals, scale envelope | Stop |
| Monitoring Coverage | Assets, expectations, periods | Base coverage records | `monitoring/<org>/<period>` | Scope and interval consistency | Stop |
| Alerts | Population, periods, assets, workload | Base alerts/latent issue clusters | Separate count/attribute/time streams | Ownership, times, category/severity validity | Stop |
| Cases | Alerts, workflows | Cases + case-alert links | `cases/<org>/<period>` | Link cardinality/ownership/order | Stop |
| Investigations | Cases/alerts, workload/runbooks | Investigation activities/notes plan | Separate count/time/text streams | At least one valid subject ref; base temporal logic | Stop |
| Escalations | Cases/alerts, applicability | Escalation records | `escalations/*` | Base applicability/target/times | Stop |
| Actions | Alerts/cases/assets, recurrence/outcome | Actions/remediation | `actions/*` | Subject references and lifecycle | Stop |
| Resolutions | Cases/alerts/actions | Resolution records | `resolutions/*` | Subject/timing/type validity | Stop |
| Closures | Cases/alerts/resolutions | Closure records | `closures/*` | Base ordering/disposition/approval consistency | Stop |
| Exceptions | Planned ordinary/legitimate contexts | Exception/applicability records | `exceptions/*` | Approval/scope/effective interval | Stop |
| Process Changes | Period/source/workflow plan | Process-change records | `process_changes/*` | Boundary/version consistency | Stop |
| Base-World Validation | Complete unmutated world | Strict validation report + sealed base snapshot | None | Schema/referential/temporal/quality invariants | Stop on any unapproved defect |
| Scenario Selection | Sealed base + private instance config | Private subject reservations/overlap plan | `scenario/<instance>/select` | Eligibility, exclusions, prevalence, split | Stop |
| Scenario/Control Mutations | Base copy + scenario plan | Mutated operational world + private receipts | `scenario/<instance>/realize` | Receipt completeness and local invariants | Stop |
| Quality Mutations | Mutated world + private authorizations | Source-world plan + quality receipts | `quality/<org>/<period>` | Every defect authorized, no collateral defect | Stop |
| Source Rendering | Source-world plan + profiles | SRC-A…E files + render index | `rendering/*` only for deterministic permitted shuffles | Parse-back, ordering, dialect/profile rules | Stop |
| Canonical Reference | Rendered files + mappings/vocab | Canonical oracle | None | Schema/state/mapping counts and values | Stop |
| Provenance | Render/canonical traces | Source/field/relationship lineage oracle | None | Every analytical field/source path resolves | Stop |
| Ground Truth | Private plans/receipts/validators | Hidden truth package | None beyond recorded scenario seeds | Truth schema, record refs, category/control completeness | Stop |
| Full Validation | All packages pre-release | Gate reports | None | All 14 validation layers | Stop on blocking issue |
| Leakage Scan | Operational package + private fingerprints | Findings/report | None | No high-severity leak; reviewed warnings | Stop on unresolved high issue |
| Hashing | Validated files | Per-file/tree/manifest hashes | None | Recompute and compare | Stop |
| Packaging | Hashed artifacts + split rules | Operational/truth/evaluation/binding packages | None | Package membership, no cross-domain files | Stop |
| Reproducibility Verification | Rebuild in clean workspace | Hash comparison report | Same seed | Logical/byte identity | Release blocked on mismatch |

---

## 7. Data-Model Implementation Boundary

This plan does not redefine `DATA_SCHEMA.md`. It maps each approved family to a generator component.

| Schema family | Generator component | Generation order | Key dependencies / implementation boundary |
|---|---|---:|---|
| Organization | `population.organizations` | 1 | Cohort config and public source-profile assignment; source ID optional |
| Control/Process Reference | `evidence.controls_processes` | 2 | Approved demo/config catalogue; no official-policy claim |
| Control/Process Subject Link | `evidence.controls_processes` | After referenced subject exists | Explicit configured/mapped provenance only |
| Submission | `evidence.submissions` | 3 | Organization + period/source plan |
| Submission Evidence-Family Declaration | `evidence.submissions` | 3 | Family plan; distinguishes provided zero/not provided |
| Submission Manifest | `packaging.manifests` / source planning | Before render and finalized after render | Counts/hashes final only after files exist |
| Asset | `evidence.assets` | 4 | Organization profile/period revisions |
| Monitoring Coverage | `evidence.monitoring` | 5 | Asset expectation, period, exception context |
| Alert | `evidence.alerts` | 6 | Organization, asset, issue clusters, period/workload |
| Case / Incident | `evidence.cases` | 7 | Alerts and workflow profile |
| Case-Alert Link | `evidence.cases.links` | 7 | Alert/case identities; source representation deferred to renderer |
| Investigation Activity | `evidence.investigations` | 8 | Case/alert, workload, note/runbook plan |
| Escalation | `evidence.escalations` | 9 | Case/alert, applicability/process context |
| Action / Remediation | `evidence.actions` | 10 | Asset/alert/case, recurrence/outcome |
| Resolution | `evidence.resolutions` | 11 | Case/alert/action workflow |
| Closure | `evidence.closures` | 12 | Case/alert/resolution/disposition |
| Exception / Applicability | `evidence.exceptions` and `scenarios.controls` | Ordinary contexts before scenarios; scenario controls during mutation | Target/effective/approval references |
| Process Change | `evidence.process_changes` | Period/source plan and mutation context | Workflow/tool/mapping version boundary |
| Source File / Artifact | `rendering` + `packaging` | After mutation | Exact bytes/profile/path/hash |
| Source Record | `rendering.index` | During rendering | Stable row/JSON locator and raw-record hash |
| Canonical Evidence Record | `canonical` | After rendering | Mapping/profile/vocabulary; private oracle in held-out |
| Canonical Field Observation | `canonical.fields` / `provenance` | After canonical mapping | Original path/value, state, transform, quality |
| Relationship Observation | `canonical.relationships` / `provenance` | After relationship resolution | Search scope and missing-state semantics |
| Data-Quality Issue | `validation.quality_reference` | After source/canonical validation | Expected quality consequences, not SAT-SA analytics findings |
| Analytical Run / Finding / Basis / Evidence Link | Not generated as operational evidence | N/A | Future SAT-SA output; expected matching remains private evaluation metadata |
| Review / Disposition | Not pre-populated | N/A | Produced by future human review, not generator truth |
| Review Sample / Member | `evaluation.review_samples` | After operational sealing | Private evaluation coordination; members reference operational records, labels withheld |
| Audit Event | SAT-SA application events not pre-generated | N/A | Generator emits separate private generation audit/package logs only |
| Hidden Scenario Ground Truth | `ground_truth` | After scenario validation | Private and physically/logically separate |

**PROJECT DECISION:** Review samples are evaluation artifacts, not submitted operational evidence. SAT-SA review/disposition and application audit events remain future application outputs.

---

## 8. Population Generator

### 8.1 Main population

Generate 15 organizations `CSE-001`–`CSE-015` in three cohorts of five. Organization names, aliases, sectors/subsectors, scale, operating model, and source-profile assignment come from versioned public config, while exact stochastic latent draws are seed-driven.

### 8.2 Persistent profile object

Each organization profile contains stable latent parameters or parameter references for:

- cohort/sector/subsector;
- scale and asset-count envelope;
- operating model and active-hour schedule;
- asset-class/criticality mixture;
- alert base intensity, burstiness, trend persistence, and category/severity priors;
- case-creation and alerts-per-case behavior;
- workflow capacity/workload sensitivity;
- investigation depth, automation, note-style mixture, and runbook usage;
- escalation propensity effects;
- action/remediation and verification propensity;
- closure/disposition/timing effects;
- monitoring expectation/coverage and onboarding/decommissioning behavior;
- source-profile/version schedule;
- baseline quality propensity and ordinary missingness.

### 8.3 Hierarchical sampling

1. Draw cohort-level baseline parameters.
2. Draw organization random effects around the cohort baseline.
3. Clamp only to semantically valid domains, not detector thresholds.
4. Persist organization effects across periods.
5. Apply period random effects and autocorrelated drift later.
6. Keep overlap between cohorts and scale bands.

### 8.4 Diversity assertions

Population validation checks:

- each cohort has approximately five members;
- at least one operating-model difference within each cohort;
- scale bands overlap between cohorts;
- no cohort has one fixed severity/volume/workflow profile;
- at least one naturally fast and one naturally slow entity without concern labels;
- source profiles are not one-to-one with scenario classes;
- truth category prevalence does not become predictable from organization/cohort alone.

### 8.5 Preventing cohort leakage

Scenario allocation is performed only after population/split freeze. Private truth should have concern/control/normal cases across cohorts. A simple classifier using only organization/cohort/public profile must not trivially infer scenario truth; distribution sanity tests measure and review this risk without building SAT-SA ML.

---

## 9. Period and Submission Generator

### 9.1 Configured periods

Period boundaries are a list in split/tier config with IDs `P01`–`P06`, UTC start/end, intended maturity cutoff, and comparison group. Generator logic iterates configured periods; it has no hard-coded dates.

### 9.2 Period states

For each organization-period, the planner produces:

- reporting start/end;
- maturity state (`MATURE`, `PARTIAL`, `IMMATURE`, `UNKNOWN`);
- planned submissions and source systems;
- family presence/completeness plan;
- late-arrival/revision schedule;
- process/source-profile version;
- declared completeness independent of assessed completeness.

### 9.3 Explicit zero versus omission

- `PROVIDED` family with zero records creates a provided file/object according to profile and observed count zero.
- `NOT_PROVIDED` family creates no family export (or a manifest omission consistent with profile), never a zero-count substitute.
- `NOT_APPLICABLE` requires applicability context.
- `UNKNOWN` lacks adequate scope declaration.

### 9.4 Late arrivals

The planner reserves records by logical identity, event period, release submission, and revision. The base event is created once. Rendering determines which submission first contains it. A later arrival retains original event time and a later source update/received time.

### 9.5 Revisions and superseding submissions

- Record revision: same logical source identity/version chain, new source record revision.
- Corrected package: new `submission_id` with `supersedes_submission_id`.
- Exact duplicate package: same file/package hash and duplicate quality authorization.
- No destructive replacement.

### 9.6 Process/source migration

A version schedule changes workflow/source profile at a configured boundary. Documented migration emits Process Change and optionally Exception context. Undocumented shift scenario changes behavior without that evidence.

---

## 10. Operational Evidence Generators

### 10.1 Asset generator

- **Inputs:** organization profile, period/revision schedule, asset distribution config.
- **Latent factors:** scale, class mixture, critical-service mixture, onboarding/decommissioning rates.
- **Distributions:** overdispersed asset count; categorical class/criticality conditional on service profile.
- **Relationships:** one organization; later coverage/alerts.
- **Validation:** source ID optional, SAT ID unique, valid effective interval, ownership.
- **Legitimate variation:** inactive/decommissioning assets, versioned criticality changes.
- **Mutation compatibility:** missing inventory fields, unresolved source IDs, coverage gaps.

### 10.2 Monitoring coverage generator

- **Inputs:** assets, monitoring expectations, periods, ordinary maintenance/onboarding plan.
- **Latent factors:** organization coverage propensity, asset criticality/class, source-health state.
- **Distributions:** conditional categorical state and last-evidence timing.
- **Relationships:** asset, organization, exception where applicable.
- **Validation:** interval overlap, organization match, expectation basis.
- **Legitimate variation:** onboarding, maintenance, partial coverage, decommissioning.
- **Mutations:** remove coverage evidence, omit family, degrade status, create unknown scope.

### 10.3 Alert generator

- **Inputs:** organization/period, assets, latent issue catalogue, workload and source profile.
- **Latent factors:** base intensity, burstiness, category/severity mix, asset exposure, period trend.
- **Distributions:** gamma-Poisson/negative-binomial counts; non-homogeneous event time; clustered recurrence; categorical severity/category.
- **Relationships:** optional asset; future case link.
- **Validation:** period proximity, vocabulary, occurrence count ≥ 1, ownership.
- **Legitimate variation:** storms, false-positive bursts, suppressed/automated alerts.
- **Mutations:** source-ID omission, timestamp issues, severity drift, duplicates.

### 10.4 Case and link generator

- **Inputs:** alerts, organization workflow, period workload.
- **Latent factors:** case propensity, grouping tendency, case-size tail, triage severity change.
- **Distributions:** Bernoulli/logistic case creation; zero-truncated overdispersed alerts per case; rare large groups.
- **Relationships:** many-to-many alert/case links.
- **Validation:** ownership and link cardinality; base foreign keys resolve.
- **Legitimate variation:** alert-only dispositions, campaign/storm grouping, re-triage.
- **Mutations:** broken links, contradictory severity/state, conflicting duplicate.

### 10.5 Investigation generator

- **Inputs:** cases/alerts, workload/capacity, workflow, runbook/template plan.
- **Latent factors:** investigation depth, manual/automation mix, case complexity, analyst-role pool.
- **Distributions:** count per case; positive long-tailed start delay/duration; text-mode mixture.
- **Relationships:** case and/or alert; runbook/template; synthetic role/pseudonym.
- **Validation:** at least one subject reference, valid base timing, bounded safe text.
- **Legitimate variation:** open investigations, terse case-specific notes, standard runbook text.
- **Mutations:** remove qualifying investigation, shift after closure, vague repetition.

### 10.6 Escalation generator

- **Inputs:** cases/alerts, control/applicability context, organization behavior/workload.
- **Latent factors:** contextual escalation propensity and timing.
- **Distributions:** bounded event probability and positive long-tailed delay.
- **Relationships:** case/alert, source/target role, trigger reference.
- **Validation:** subject exists, time order in base, target present.
- **Legitimate variation:** not-applicable workflow, emergency redirect, cancellation/rejection.
- **Mutations:** omit required escalation, lower period propensity, broken target reference.

### 10.7 Action/remediation generator

- **Inputs:** recurrence groups, assets, cases, conclusions, workload, accepted-risk context.
- **Latent factors:** remediation propensity, type, due/completion/verification probability.
- **Distributions:** conditional categorical action/status; long-tailed completion delay.
- **Relationships:** one or more of asset/alert/case.
- **Validation:** valid subject and lifecycle.
- **Legitimate variation:** open/deferred remediation, accepted risk, failed verification.
- **Mutations:** remove apparent remediation, count mismatch, conflicting status.

### 10.8 Resolution generator

- **Inputs:** cases/alerts, actions, investigation conclusions.
- **Latent factors:** resolution type/status and approval/verification behavior.
- **Distributions:** conditional categorical outcome and positive timing.
- **Relationships:** case/alert, action/exception where applicable.
- **Validation:** base resolution not before prerequisite event when semantics require it.
- **Legitimate variation:** false positive, duplicate, accepted risk, no action required.
- **Mutations:** omit resolution, contradictory type, invalid ordering.

### 10.9 Closure generator

- **Inputs:** case/alert lifecycle, resolution, disposition, workload/automation.
- **Latent factors:** administrative delay and approval requirements.
- **Distributions:** mixture of automated/ordinary/heavy-tail closure duration.
- **Relationships:** case/alert, optional resolution, exception.
- **Validation:** base closure lifecycle/disposition; reopen represented as later state/revision.
- **Legitimate variation:** fast approved duplicate closure, reopened case.
- **Mutations:** no disposition/approval, closure-before-creation, contradictory state.

### 10.10 Exception/applicability generator

- **Inputs:** organization, asset/workflow subjects, period/process plan, control catalogue.
- **Latent factors:** ordinary maintenance/automation/accepted-risk contexts plus scenario controls.
- **Distributions:** sparse contextual events; approval states not always perfect.
- **Relationships:** typed target, rule/control/process, effective interval.
- **Validation:** target and effective interval; approved active controls only qualify.
- **Legitimate variation:** pending/expired/rejected/ambiguous evidence.
- **Mutations:** missing approval, out-of-scope/expired context.

### 10.11 Process-change generator

- **Inputs:** period/source/workflow version schedule.
- **Latent factors:** planned policy, workflow, tooling, mapping, automation, or asset-scope changes.
- **Relationships:** organization, affected families, exception where applicable.
- **Validation:** boundary aligns with version/effective interval.
- **Legitimate variation:** temporary emergency/migration periods.
- **Mutations:** undocumented shift or mismatched mapping update.

### 10.12 Control/process reference generator

- **Inputs:** approved synthetic demo catalogue and source-config plan.
- **Output:** versioned references and subject links marked by authority type.
- **Validation:** no invented official attribution; explicit provenance/effective state.
- **Mutation compatibility:** missing/outdated link, changed process version, exception scope.

---

## 11. Scenario Engine

### 11.1 Interface separation

| Interface | Responsibility | Receives | Returns | Prohibited knowledge/action |
|---|---|---|---|---|
| `Scenario` | Immutable catalog definition: semantics, prerequisites, allowed mutations, truth contract, validator ID | Public catalog config | Validated definition | No subject IDs, hidden seed, detector threshold |
| `ScenarioSelector` | Find eligible subjects and choose seeded instances/overlap groups | Read-only base index, private instance config, named RNG | Private `ScenarioPlan` | No mutation, no detector query |
| `ScenarioMutator` | Apply operational/structural change and emit private receipt | Copy-on-write world, plan, named RNG | Mutated world + `MutationReceipt` | No expected detector score/finding creation |
| `ScenarioValidator` | Confirm intended operational condition and counterevidence state | Mutated world, plan, receipt | Pass/fail evidence-rich report | No use of SAT-SA output |
| `ScenarioTruthWriter` | Serialize private truth/record links/seeds/correlation | Valid plan/receipt/report | Ground-truth records | No writes to operational package |

### 11.2 Scenario definition contract

- public ID/version/family/description;
- semantic prerequisites;
- eligible subject family and search query name;
- permitted mutation operations;
- required ordinary context and prohibited conflicts;
- legitimate/ambiguous counterpart references;
- expected evidence roles and private matching policy;
- scenario validator ID/version;
- correlation compatibility/exclusion rules;
- privacy/leakage constraints.

### 11.3 Selection

Selectors operate on broad semantic eligibility: serious closed alerts, active critical assets, mature complete periods, recurring issue groups, etc. They do not filter on future detector thresholds. They reserve subjects to prevent accidental overlap, unless an explicit overlap group permits sharing.

### 11.4 Realization

Mutators use copy-on-write operations such as remove relationship/record, alter latent propensity before downstream generation, shift a timestamp, omit a field/family, add context record, or change source layout. Every operation emits before/after private references and expected canonical/quality consequence.

### 11.5 Validation and rollback

A failed scenario realization stops the build. The engine does not retry arbitrary random draws until the case becomes “detectable.” A bounded, deterministic resampling policy may be defined for infeasible subject selection before mutation; retries and seeds are recorded. After mutation, failure requires configuration/scenario correction and a new build.

### 11.6 Correlation

The planner assigns `correlation_group_id` and `independence_group` privately. Mutations sharing root records are validated jointly. Evaluation later expects one multi-basis package where specified rather than rewarding duplicate findings.

---

## 12. Legitimate-Control Engine

### 12.1 Architecture

Legitimate controls implement the same `Scenario` interfaces with a private classification of `LEGITIMATE_UNUSUAL` or `AMBIGUOUS`. They generate operational context records rather than simply suppressing a truth label.

### 12.2 Control builders

| Control | Operational records/changes | Required imperfection/variation |
|---|---|---|
| Approved automation | Automation state, process change/rule version, approved exception, fast closure path | Some missing explanatory notes; variation in scope |
| Maintenance | Maintenance exception, asset/coverage interval, reduced monitoring/alerts | Partial scope or late documentation in ambiguous variant |
| Suppression | Suppression state/rule, approval/effective interval, tuning action | Some suppressed alerts still create cases |
| Accepted risk | Approved exception, owner role/reference, recurring alerts, absent remediation | Include expired/pending variants not treated as valid controls |
| Emergency workflow | Emergency exception/process change, alternate escalation path | Compressed documentation or later update |
| Policy/workflow change | Process change and control/process links | Gradual transition and mixed old/new records |
| Tool migration | Source/profile/mapping version change, late arrivals, partial declaration | Some unresolved IDs/timezone warnings |
| Onboarding/decommissioning | Asset status/effective interval and coverage state | Boundary ambiguity for selected controls |
| Different operating model | Organization profile/cohort eligibility context | Not every peer metric explained |
| Runbook/template usage | Runbook/template IDs and case-specific note slots | Occasional missing template ID |
| Alert storm | Issue cluster, case grouping, source rule, workload effect | Some true cases mixed into burst |
| False-positive burst | Shared rule/disposition and tuning action | A minority require real investigation |
| Legitimate re-triage | Severity-change context and case impact | Source history may be partial |
| Reopened cases | Closure then explicit reopen revision/event | Conflicting snapshot if one family is delayed |

### 12.3 Ambiguous controls

Controls are not unrealistically perfect. The private truth writer labels a control `AMBIGUOUS` when approval, scope, effective interval, or provenance is incomplete. Scenario validators must not keep a `LEGITIMATE_UNUSUAL` label if the operational evidence no longer supports it.

### 12.4 Balance assertions

Every concerning family has ordinary negatives, legitimate controls, and insufficient/ambiguous cases across development and held-out splits. The validator checks that controls are not confined to one cohort/source profile.

---

## 13. Data-Quality Mutation Engine

### 13.1 Authorization record

Every deliberate defect has a private immutable authorization containing:

- mutation authorization ID/version;
- split/scenario/organization/period;
- target source family/record/field/relationship;
- mutation type and parameters;
- before-state hash/reference;
- expected source rendering;
- expected canonical value/state/quality issue;
- expected eligibility consequence;
- seed label;
- validator ID;
- correlation group;
- status: planned/applied/validated/failed.

### 13.2 Supported mutation operations

| Mutation | Implementation action | Expected consequence |
|---|---|---|
| Missing field | Omit key/column value according to source-profile semantics | `NOT_PROVIDED`; required field may invalidate record |
| Missing family | Do not emit family export and set declaration state | Family `NOT_PROVIDED`, not zero |
| Partial submission | Truncate declared coverage/selected files with declaration or undeclared variant | `PARTIAL_PERIOD`/unknown scope |
| Malformed value | Render unparseable timestamp/type/token | `INVALID`, raw retained |
| Exact duplicate | Emit identical logical record/ID/hash as configured | `DUPLICATE_EXACT` |
| Conflicting duplicate | Emit same scoped source ID with changed content and no valid revision semantics | `DUPLICATE_CONFLICTING` |
| Broken relationship | Replace/omit foreign ID or target record | `BROKEN_RELATIONSHIP`/unresolved observation |
| Timestamp problem | Offset, remove zone, or create impossible order | Warning/invalid/inconsistency per profile |
| Schema drift | Rename/retype/reorder/nest field under new or missing profile version | Valid migration or `SCHEMA_MISMATCH` |
| Vocabulary drift | Emit new token with/without mapping update | Mapped new value or `UNKNOWN` warning |
| Late arrival | Move first appearance/revision to later submission | Late-arrival lineage |
| Count mismatch | Alter declared count, not actual rows | Submission quality issue |
| Source-ID absence | Omit optional native ID; retain stable file/row locator | Valid canonical SAT ID and provenance |

### 13.3 Mutation ordering

Apply semantic scenarios before source-quality mutations unless a scenario explicitly needs quality mutation to realize its condition. Quality operations are ordered deterministically: family/submission → schema/layout → record duplication/relationship → field/value → serialization. Conflicting operations on the same target require declared composition; otherwise configuration fails.

### 13.4 Unexpected-defect detection

Compare post-mutation validation issues against authorization expected signatures. Any extra issue, missing expected issue, mismatched target, or unconsumed authorization blocks the build. Validation never “fixes” the source.

---

## 14. Source Rendering Engine

### 14.1 Renderer contract

Each renderer consumes scenario-free operational domain objects plus quality render directives and emits exact source bytes, file/record index, and render trace. It cannot read ground-truth classification.

Common controls:

- deterministic file partition/order;
- fixed encoding/dialect/number formatting;
- profile-specific empty/missing semantics;
- bounded record/text sizes;
- optional source IDs;
- source-system/version metadata;
- relationship representation;
- deterministic timestamp rendering;
- parse-back validation.

### 14.2 Profile implementations

| Profile | File layout/format | Names/order | IDs | Time/vocabulary | Relationships/missing values | Deterministic order |
|---|---|---|---|---|---|---|
| `SRC-A` | Separate family CSV files | snake_case; stable declared columns | Most native IDs | ISO 8601 `Z`; canonical-like terms | Separate link CSV; empty token rules explicit | Family primary logical key |
| `SRC-B` | CSV exports, mixed/Pascal headings | Profile-version column order | Some child/native IDs absent | Local time + declared IANA zone; numeric/abbrev tokens | Case foreign ID embedded; profile-specific blank/null token | Source event time then stable SAT locator |
| `SRC-C` | Nested JSON by case/submission | camelCase/nested keys | Parent IDs; child IDs optional | ISO offset/milliseconds; vendor-like terms | Alerts/activities arrays; absent keys for not provided | Parent key, then stable child ordinal |
| `SRC-D` | JSON array by family; optional JSON Lines mode | lower/mixed keys | Mixed | Offsets/date precision by family | Reference arrays/external IDs; explicit null only where semantics define it | Stable canonical logical key before rendering |
| `SRC-E` | Versioned CSV/JSON hybrid | Old/new layouts across migration | Namespace/version changes | Time precision/vocabulary changes at boundary | Old FK vs new link object; schema drift controls | Version-specific deterministic rule |

### 14.3 JSON Lines decision

**OPEN QUESTION:** JSON Lines remains configuration-controlled. Implementation sequence:

1. implement JSON array/object mode for SRC-C/D;
2. validate future SAT-SA ingestion expectations;
3. enable `json_mode = "lines"` only under a new source-profile version;
4. use UTF-8, one canonical JSON object per LF-terminated line, deterministic key order.

JSON Lines is not required for the first fixture unless approved before renderer implementation.

### 14.4 Render trace

For every output field/key/row/object, retain private testing trace:

- domain record/field identity;
- file/record locator;
- emitted source key/value bytes/lexical form;
- source ID/namespace behavior;
- profile/version/serializer version;
- quality directive/authorization reference if modified.

The operational file does not contain the trace or authorization.

---

## 15. Canonical Reference and Provenance Builder

### 15.1 Independent oracle

The builder reads rendered source bytes through reference parsers and public mapping/vocabulary configurations. It does not receive pre-render domain rows as authoritative values, ensuring renderer/mapping errors can be caught.

### 15.2 Required chain

```text
Source File
  -> Source Record / locator / raw-record hash
  -> Source Field / path / raw lexical value
  -> Mapping + transform + vocabulary version
  -> Canonical Record / field
  -> Canonical typed value or non-collapsible value state
```

### 15.3 Canonical build steps

1. Verify source file hash/manifest.
2. Parse according to exact source profile/version.
3. assign source-file/source-record IDs and locators;
4. resolve scoped source IDs or generate SAT canonical IDs from stable logical identity;
5. apply timestamp, type, and vocabulary mapping;
6. produce canonical family records;
7. produce field observations for required/analytical optional fields;
8. resolve relationships or produce relationship observations/search scope;
9. produce expected data-quality issues;
10. reconcile against renderer trace without reading scenario truth.

### 15.4 Relationship provenance

For direct FK, link file, nested array, and external ID representations, store original path/value, mapping resolution, target or unresolved source ID, relationship state, source submission, and search scope. Missing expected relationships are created only after adequate family/period search.

### 15.5 Withholding rationale

In held-out end-to-end analysis, canonical/provenance reference is withheld because providing it would bypass ingestion/mapping and reveal expected parse/quality outcomes. SAT-SA first imports source exports and seals its own canonical result. The evaluator then compares it with the oracle.

### 15.6 Independence limitation

The oracle and future SAT-SA may share mapping specifications but should not share implementation code for critical parser/normalization assertions without independent golden checks; otherwise one bug could validate itself.

---

## 16. Ground-Truth Writer

### 16.1 Input boundary

The writer consumes only validated private scenario plans, mutation receipts, control evidence validation, operational ID map, and package/version context. It cannot write to operational directories.

### 16.2 Private record content

For every scenario instance write:

- scenario ID/version/catalog version;
- dataset/generator/schema/mapping/source-profile versions;
- split, organization, period;
- affected records with roles (`AFFECTED`, `SUPPORTING`, `COUNTEREVIDENCE`, `DECOY`, `EXPECTED_BUT_ABSENT`);
- intended analytical family/families;
- classification (`ATTENTION`, `LEGITIMATE_UNUSUAL`, `NORMAL`, `DATA_QUALITY_ONLY`, `AMBIGUOUS`);
- expected evidence and source/provenance paths;
- counterevidence/exception expectation;
- mutation before/after provenance;
- exact scenario seed label/value in private ledger;
- correlation and independence group;
- expected abstention/insufficient-data state where relevant;
- acceptable expected-finding match constraints and forbidden interpretation;
- manual-review guidance and ambiguity notes;
- validator result/hash.

### 16.3 Negative-space representation

For absent evidence, truth points to expected-universe subject, expected relationship/family, searched scope, adequacy basis, and authorization. It never creates a nonexistent record ID.

### 16.4 Security controls

- private output root is passed separately and cannot be nested inside operational root;
- packaging rejects cross-domain paths;
- logs print counts/hashes, not truth rows/seeds;
- developer mode can expose development truth; held-out build requires restricted mode/custodian;
- operational manifest has no truth-package hash.

---

## 17. Dataset Split Implementation

### 17.1 Split object

A frozen `SplitPlan` contains split ID/version, population/tier config references, independent master-seed alias, allowed source profiles/versions, public parameter envelopes, private scenario instance reference, truth visibility policy, and output-seal policy.

### 17.2 Development

- public seed/truth after generation;
- deterministic fixture + medium dataset;
- all scenario/control/quality families;
- stable source profiles for debugging plus selected drift;
- optional model-fitting baseline clearly identified;
- detector development allowed only after operational generation freezes.

### 17.3 Validation

- independent master seed and IDs;
- altered parameter draws/prevalence;
- new scenario instances and profile combinations;
- truth withheld until run seal or controlled by evaluator;
- threshold/config selection allowed, with reuse documented.

### 17.4 Held-out

- independent 256-bit seed under custodian;
- private exact population/scenario/parameter draws;
- source exports only during SAT-SA run;
- no record/source IDs shared with other splits;
- rules/models/features frozen before output;
- outputs hashed/sealed before truth/canonical oracle becomes available;
- consumed held-out release cannot be called held-out for subsequent tuning.

### 17.5 Scenario separation

Families may exist in all splits, but instances, subjects, seeds, effect draws, text variants, and combination patterns differ. Held-out may contain novel combinations and source drift, not completely new undocumented requirements.

### 17.6 Blinded manual-review subset

`evaluation.review_samples` creates Review Sample/Member structures after operational sealing:

- stratified private selection from attention, legitimate, normal, quality-only, and ambiguous classes;
- members reference operational records/evidence packets only;
- neutral sample IDs and ordering independent of truth category;
- no SAT-SA priority in initial packet;
- separate private assignment/answer-key mapping;
- reviewer responses stored later, not pre-generated.

---

## 18. Validation Framework

### 18.1 Gate matrix

| # | Layer | Tests | Failure condition | Output | Continue? |
|---:|---|---|---|---|---|
| 1 | Configuration | Type/schema, version compatibility, references, forbidden detector keys, private/public path separation | Any invalid/unresolved/forbidden config | Config report + frozen hashes | **Stop** |
| 2 | Schema/base | Required types/vocab/limits on unmutated records | Any unplanned invalid record | Family/schema report | **Stop** |
| 3 | Referential integrity | Ownership, FKs, cardinality, scoped source-ID uniqueness | Any unplanned broken/mismatched relation | Relationship report | **Stop** |
| 4 | Temporal integrity | Period/effective/event ordering, allowed open records | Any unplanned impossible sequence | Temporal report | **Stop** |
| 5 | Missing-state semantics | Value/state compatibility, zero/omitted/invalid/not-applicable/absence/unknown | Any mismap or unsupported absence | Field/relationship state report | **Stop** |
| 6 | Scenario realization | Semantic condition, eligible scope, intended context | Scenario absent, too broad, or wrong subject | Private scenario report | **Stop** |
| 7 | Authorized mutation | Expected vs observed defects and consumed authorizations | Extra/missing/mismatched defect/authorization | Private mutation reconciliation | **Stop** |
| 8 | Source rendering | Parse-back, dialect, IDs, time/vocab, stable order, schema profile | Byte/profile mismatch or parser failure | Per-profile report | **Stop** |
| 9 | Canonical/provenance | Source-to-canonical values/states, lineage, relationship scope | Missing/wrong value, state, locator, mapping, or hash | Oracle/provenance report | **Stop** |
| 10 | Distribution sanity | Counts, diversity, tails, overlap, cohort/source balance | Hard invariant breach; soft envelope breach pending review | Statistical report/plots/tables | Stop on hard; review soft |
| 11 | Duplicate behavior | Exact/conflicting/revision/repeat/submission semantics | Wrong classification/counting/identity | Duplicate report | **Stop** |
| 12 | Leakage scan | Paths, headers, keys, values, notes, IDs, metadata, manifests | Unwaived high-confidence leak | Leakage report | **Stop** |
| 13 | Reproducibility | Logical and byte rebuild; stream isolation | Hash/record mismatch | Repro report | **Stop** |
| 14 | Package/hash | Domain membership, hashes, counts, binding, no cross-domain file | Mismatch or forbidden path | Release validation report | **Stop** |

### 18.2 Hard versus reviewable distribution gates

Hard invariants include nonempty cohorts, configured family counts, valid parameter domains, required positive/control coverage, and no perfect label marker. Soft statistical envelopes allow natural seed variation but require recorded review when breached. Review never changes output in place; configuration/version changes trigger rebuild.

### 18.3 Validator architecture

Validators are pure/read-only where feasible. Each returns structured issues with code, severity, scope, evidence, expected/actual, and validator version. They cannot mutate generated artifacts or downgrade issues automatically.

---

## 19. Leakage Detection

### 19.1 Scanner inputs

- finalized operational file tree and public manifest;
- private forbidden-token/fingerprint set generated from truth/scenario/seed configs;
- permitted public scenario-catalog vocabulary allowlist only where documentation files are intentionally excluded from detector inputs;
- neutral identifier grammar and source-profile definitions.

### 19.2 Inspection surfaces

- directory names, filenames, archive entry names, and relative paths;
- CSV headers/cells and JSON keys/values;
- free-text notes/summaries/reasons;
- source/canonical identifiers and prefixes;
- source-system/version strings;
- manifests and metadata;
- serialized configuration included in package;
- hash-input descriptors and public seed aliases;
- row ordering/partition patterns;
- split markers and package names.

### 19.3 Detection methods

1. Exact and case-folded private token match.
2. Regex for scenario ID families, mutation codes, labels, answer keys, seed representations.
3. Encoded/normalized variants: separators removed, base encodings where used by system, Unicode normalization.
4. Identifier grammar check: ensure IDs do not contain scenario/split truth.
5. Metadata key denylist: `scenario`, `truth`, `label`, `expected_finding`, `mutation`, private seed keys.
6. Phrase fingerprint check for scenario-specific text templates.
7. Partition/order test: truth categories must not occupy predictable contiguous ranges.
8. Statistical leakage diagnostic: simple public-profile/ID/layout attributes should not perfectly separate private classes. This is a dataset-quality diagnostic, not SAT-SA ML.
9. Package membership check: no truth/evaluation path, file hash, or binding secret inside operational package.

### 19.4 Hash/source-string handling

Random hexadecimal hashes may coincidentally contain short text fragments. The scanner checks descriptors/preimages used to construct IDs/hashes and exact long forbidden tokens, not arbitrary short substrings in SHA-256 output. Operational IDs cannot be direct hashes of scenario labels.

### 19.5 Severity and false-positive handling

- **Blocking:** exact scenario ID/private seed/label key/truth file, scenario-derived ID/path, answer-key reference.
- **High:** distinctive private phrase or split marker with no operational justification.
- **Warning:** generic words such as “attention,” “expected,” or “mutation” in legitimate documentation/context.

Warnings require human review. Allowlist entries include exact scope, reason, reviewer, expiration/version, and hash. Blocking findings cannot be allowlisted merely for convenience; fix source/config and rebuild.

---

## 20. Reproducibility Tests

### Test A — Logical identity

**Claim:** Same frozen version tuple + same private/public seed ledger produces identical logical records, IDs, relationships, states, and manifests before byte serialization.

Run twice in clean workspaces; canonicalize in-memory/logical output and compare hashes/counts/ordered records. Failure blocks release.

### Test B — Byte identity

**Claim:** Same version tuple/seed produces identical source/export/reference/package bytes.

Compare each relative path, byte size, SHA-256, manifest, and package tree hash. Archive container metadata is included if archives are used.

### Test C — Stream isolation

Change only note-template version/content while holding every other configuration/seed constant. Expected changes are restricted to investigation-note source fields, corresponding source-record/file hashes, canonical note values, note-related provenance, manifests, and dependent private truth fingerprints. Alert counts/IDs/times, assets, cases, and unrelated families must remain identical.

Repeat analogous isolation tests for serialization-only and source-profile changes.

### Test D — Version propagation

Changing a generator component/config/schema/mapping/scenario version creates a new effective configuration hash and dataset version. The build must refuse to publish changed bytes under an existing sealed version.

### Test E — Held-out seed secrecy

- public artifacts contain only independent opaque seed alias;
- exact seed bytes/hex/decimal/base encodings absent;
- child stream fingerprints do not expose seed material;
- no deterministic mapping from dataset name/date/public alias to seed;
- seed has 256-bit entropy and restricted custody;
- leakage scan and repository-history scan pass.

This test establishes implementation controls; it does not claim a mathematical proof against compromise of the private custody environment.

### Additional reproducibility tests

- locale/timezone change does not alter output under declared environment contract;
- shuffled filesystem enumeration does not alter file/record order;
- CPU parallelism setting does not alter bytes;
- validation/report timestamps are excluded from hashed deterministic content or deterministically represented;
- rebuild after dependency update appropriately changes generator version and golden expectations.

---

## 21. Benchmark Generation

### 21.1 Small deterministic fixture

Implementation steps:

1. freeze public seed/config;
2. generate 2–3 organizations × 2 periods;
3. include at least one valid record per required family plus focused scenario/control/quality examples;
4. render minimum two source profiles initially, eventually all five in contract fixtures;
5. generate canonical/provenance oracle and public golden hashes;
6. keep private truth separate;
7. require fast local execution and manual inspectability.

Use for unit, contract, integration, golden, and future ingestion tests.

### 21.2 Medium development benchmark

- 12–16 organizations, 4–6 periods, approved medium envelope;
- all source profiles and scenario/control families;
- collect per-stage timing/memory/disk/count telemetry;
- run full validations and distribution review;
- use as initial application-development benchmark, not a capacity claim.

### 21.3 Large stress benchmark

- 20 organizations × 6 periods within approved stress envelope;
- generated after medium is stable;
- scenario prevalence does not need to scale linearly; operational/background scale does;
- measure renderer/canonical/provenance bottlenecks and temporary disk;
- failure/resource exhaustion is recorded honestly.

### 21.4 Held-out benchmark

- initially 15 organizations × 6 periods within medium envelope;
- independent hidden seed/parameter/scenario allocations;
- operational source exports supplied to SAT-SA; truth/oracle withheld;
- exact size selected after medium results, without tuning scenario semantics to detector performance.

### 21.5 Measurement collection

Each stage emits deterministic counts plus non-deterministic runtime telemetry kept outside byte-stable package content:

- wall/process time;
- peak resident memory;
- temporary/final disk;
- records/bytes by family;
- records generated/serialized per second;
- validation/leakage/hashing time;
- package size;
- environment and parallelism;
- success/failure/retry status.

No promised throughput or maximum size appears until measured on declared hardware.

---

## 22. Testing Strategy

### 22.1 Unit tests

Test config models, seed derivation, ID derivation, distributions’ valid domains, each family generator, each mutation operation, serializers, hash/tree calculation, and manifest construction. Use fixed local inputs; no private held-out data.

### 22.2 Contract tests

Mechanically cover `DATA_SCHEMA.md`:

- field names/types/requiredness/vocabularies;
- optional source IDs and scoped uniqueness;
- seven value states;
- temporal/effective/reporting semantics;
- family relationships/cardinalities;
- control/process references;
- source/canonical/provenance chain;
- ground-truth physical separation.

### 22.3 Integration tests

Run stage subsets and full pipeline across multiple profiles/scenarios:

- base world to render;
- scenario + quality mutation reconciliation;
- render to canonical/provenance oracle;
- truth/evaluation packaging;
- full validation/leakage/hash/package build.

### 22.4 Golden tests

Store approved small-fixture public manifests, file hashes, counts, and selected safe expected excerpts. Private truth golden files remain restricted. Intentional change requires reviewed golden update plus version change.

### 22.5 Property tests

Examples:

- UUID uniqueness and stability;
- organization ownership closure across graph;
- base temporal ordering;
- effective interval validity;
- source-ID absence still has locator/provenance;
- explicit zero never equals omitted;
- one unauthorized mutation cannot appear;
- serialization parse round trip;
- same named seed stream independent of call order;
- control validity depends on effective/approved scope;
- operational paths never descend into truth root.

### 22.6 Leakage tests

Inject known canary truth tokens into test-only operational surfaces and verify scanner blocks each. Test benign generic words and approved operational terms to measure scanner false positives. Test encoded/path/ID/order leakage patterns.

### 22.7 Reproducibility tests

Implement Tests A–E from §20 in clean temporary roots and at least one offline CI/build environment. Compare logical and byte hashes.

### 22.8 Mutation tests

For each mutation type:

- authorized target produces exact expected source/canonical issue;
- nearby records remain unchanged unless declared;
- missing authorization blocks build;
- extra authorization blocks build;
- composition conflicts fail configuration;
- validator does not repair output.

### 22.9 Distribution tests

Check configured envelopes, long tails, overlap, burstiness, cohort diversity, category/severity mixtures, control balance, scenario sparsity, and absence of perfect single-feature separation. Soft failures require reviewed configuration/version change.

### 22.10 End-to-end fixture test

Future test boundary:

`generated source package → SAT-SA ingestion/normalization → compare with withheld canonical/provenance oracle`

This plan defines the fixture/oracle; it does not implement SAT-SA ingestion. Until the application exists, use the independent reference parser path and record the end-to-end test as pending.

---

## 23. Implementation Milestones

### Milestone 1 — Repository, configuration, and seed foundation

- **Deliverables:** package skeleton; dependency locks/wheelhouse plan; typed config models; freeze/hash pipeline; seed registry; deterministic ID service; CLI skeleton; privacy/path guards.
- **Acceptance:** known-answer seed tests; config version/hash; no unnamed RNG; authoritative docs unchanged; offline dependency installation documented.
- **Dependencies:** approval of period boundaries/config format/seed custodian roles.
- **Must not start:** scenario mutation, medium dataset, detector integration.

### Milestone 2 — Small schema-valid base world

- **Deliverables:** population, periods, organization/submission, controls/processes, assets, coverage, alerts, cases, investigations, escalation, actions, resolutions, closures, exceptions/process changes for deterministic fixture.
- **Acceptance:** base world passes schema/referential/temporal checks; all required families represented; no scenario defects.
- **Dependencies:** Milestone 1; approved minimal parameter envelopes.
- **Must not start:** held-out build, ML, SAT-SA analytics.

### Milestone 3 — Source profiles, canonical oracle, and provenance

- **Deliverables:** SRC-A–E renderer contracts; initial CSV/JSON renderers; source file/record indexes; mapping/vocabulary loader; canonical/field/relationship oracle; deterministic serialization/hashes.
- **Acceptance:** parse-back and source→canonical→provenance tests pass; optional source IDs handled; JSON Lines remains disabled/open unless approved.
- **Dependencies:** Milestone 2.
- **Must not start:** scenario truth evaluation against detector.

### Milestone 4 — Scenario and legitimate-control engine

- **Deliverables:** interfaces/catalog/selectors/mutators/validators/truth writer; execution-gap, negative-space, historical, peer, repetition, cross-record, legitimate controls, optional anomaly-support scenario.
- **Acceptance:** each family has positive/control/ambiguous/insufficient realization in fixture; no detector config dependency; ground truth separate.
- **Dependencies:** Milestone 3; approved demo expectations/catalog.
- **Must not start:** tune SAT-SA thresholds from generated truth.

### Milestone 5 — Quality mutations and full validation/leakage

- **Deliverables:** authorization ledger; all quality mutation types; 14 validation gates; leakage scanner; package membership checks.
- **Acceptance:** no unexpected defects; canary leaks blocked; false-positive review workflow; missing states correct; full fixture build fails loudly when intentionally broken.
- **Dependencies:** Milestone 4.
- **Must not start:** large benchmark before fixture reproducibility passes.

### Milestone 6 — Medium development benchmark

- **Deliverables:** 12–16 organization, 4–6 period development release; all profiles/scenarios; benchmark telemetry; distribution review.
- **Acceptance:** complete/reproducible package; resource results documented; no trivial label separation; known limitations recorded.
- **Dependencies:** Milestone 5; target hardware declared.
- **Must not start:** performance claims or held-out tuning.

### Milestone 7 — Validation/held-out and evaluation packaging

- **Deliverables:** independent split plans/seeds; held-out restricted build process; output sealing; blinded Review Sample/Member package; private binding/answer key.
- **Acceptance:** no cross-split IDs/seeds/records; truth custody documented; held-out operational package leak scan passes; evaluator can join truth only after seal.
- **Dependencies:** Milestone 6; seed custodian/reviewer assignments.
- **Must not start:** reviewing held-out truth before SAT-SA outputs are frozen.

### Milestone 8 — Large performance/stress benchmark

- **Deliverables:** 20 organization stress release; stage telemetry; bottleneck/resource report; package-size/disk/memory data.
- **Acceptance:** output correctness and validation remain mandatory even if target time/resource is missed; no unsupported capacity claim.
- **Dependencies:** stable medium and packaging pipeline.
- **Must not start:** production deployment or real SOC integration.

---

## 24. Implementation Risks

| Risk | Failure mode | Mitigation | Residual limitation |
|---|---|---|---|
| Dataset becomes too easy | One feature/ID/layout separates labels | Overlap, legitimate controls, sparse/subtle cases, leakage/distribution diagnostics | Synthetic structure can still bias methods |
| Detector-generator circularity | Generator copies rule thresholds | Repository/config boundary, forbidden keys/imports, independent scenario semantics | Human designers may share assumptions |
| Hidden leakage | Truth token/seed/order reaches operational output | Automated scanner, package root guards, canary tests, private review | Novel leakage channel may be missed |
| Unrealistic distributions | Toy Gaussian/uniform behavior | Hierarchical overdispersed/mixture/long-tail design and human review | No real data to calibrate fully |
| Overcorrelated scenarios | Same records create many easy findings | Reservation/overlap groups and expected correlation contract | Correlation logic is synthetic |
| Insufficient legitimate controls | Unusual always means attention | First-class control engine, per-family balance assertions, ambiguous cases | Control evidence may be cleaner than reality |
| Source renderer bugs | Oracle validates wrong bytes/semantics | Parse-back, independent canonical path, golden profiles | Shared mapping specification can share semantic error |
| Provenance mismatch | Canonical value cannot reach source | Field/relationship lineage gate and withheld oracle | Large provenance volume/storage |
| Reproducibility failure | Same seed differs by order/version/platform | Named streams, pinned stack, stable serializer, Tests A–E | Cross-platform floating/serializer differences require target declaration |
| Excessive size | Memory/disk/time exhaustion | Fixture→medium→large progression, Polars/streaming/partitioning, telemetry | Final scale depends on hardware |
| Dependency bloat | Offline packaging/security complexity | Minimal selected stack, no Faker/YAML by default, pinned wheelhouse | SciPy/Hypothesis wheels add size |
| Accidental truth exposure | Logs/repository/artifacts publish private data | Separate roots/permissions, ignore rules, redacted logs, package membership checks | Team operational discipline required |
| Seed compromise | Held-out reproducible by developers | 256-bit independent seed, custodian, opaque alias, restricted ledger | Custodian environment compromise remains possible |
| Scenario validator overfits | Validator becomes detector clone | Validate semantic condition, not suspicious threshold; separate purpose/review | Some conditions inherently resemble rules |
| Silent repair | Validator normalizes away intended defect | Validators read-only; canonical oracle records invalid state; mutation reconciliation | Developers may accidentally fix at renderer layer |
| Text artifacts leak class | Distinctive phrases identify concerns | Shared phrase families, paraphrase/noise, phrase fingerprint scan | Synthetic language still differs from real notes |

---

## 25. Definition of Done

Generator implementation is complete only when every mandatory item passes for a sealed release. Producing rows is insufficient.

### 25.1 Foundation and offline operation

- [ ] Python/dependency versions are pinned with hashes and offline wheelhouse.
- [ ] Generator runs with network disabled and makes no external calls.
- [ ] Public/private configuration freezes and hashes successfully.
- [ ] Named RNG/ID services are the only randomness/identity paths.
- [ ] Authoritative project documents remain unchanged.

### 25.2 Data contract

- [ ] Base world is schema-valid before mutation.
- [ ] Every required operational evidence family is generated.
- [ ] Optional source IDs and all seven missing states behave correctly.
- [ ] Organization ownership, relationships, temporal semantics, revisions, and source scope pass contract tests.
- [ ] Control/process references and subject links are correctly labeled/provenanced.

### 25.3 Population and realism

- [ ] Main population contains 15 heterogeneous organizations and three useful cohorts.
- [ ] Four–six periods include mature, partial, immature, unknown, late-arrival, and process-change examples.
- [ ] Volumes, durations, recurrence, case size, workload, coverage, notes, and remediation are heterogeneous/long-tailed where designed.
- [ ] No cohort/profile/public attribute trivially predicts truth.
- [ ] Distribution review and limitations are documented.

### 25.4 Scenarios and controls

- [ ] All major execution-gap, negative-space, historical, peer, repetition, cross-record, quality, and optional anomaly-support families exist.
- [ ] Each concerning family has normal, legitimate unusual, and insufficient/ambiguous counterexamples where applicable.
- [ ] Overlap/correlation groups are represented and validated.
- [ ] Scenario selection/realization never imports detector configuration.
- [ ] Every deliberate defect has a consumed private authorization.

### 25.5 Source heterogeneity and provenance

- [ ] SRC-A–E profiles render deterministic valid/intentional-invalid CSV/JSON.
- [ ] Schema/vocabulary/timestamp/ID/relationship variations map correctly.
- [ ] Source file→record→field→mapping→canonical value/state path resolves.
- [ ] Canonical/provenance oracle is withheld during held-out end-to-end analysis.
- [ ] Source/canonical counts and one-to-many mappings reconcile.

### 25.6 Truth, splits, and human evaluation

- [ ] Operational, ground-truth, evaluation, and binding packages are separate.
- [ ] Operational package contains no truth/scenario/seed/mutation marker.
- [ ] Development, validation, and held-out seeds/IDs/instances are separate.
- [ ] Held-out truth custody/output sealing is documented and tested.
- [ ] Blinded Review Sample/Member packets contain operational evidence only.
- [ ] Human-review guidance/answer key remains private.

### 25.7 Validation and reproducibility

- [ ] All 14 validation layers pass.
- [ ] Leakage canary and false-positive tests pass; no unresolved blocking issue.
- [ ] Same version/seed produces identical logical output and bytes.
- [ ] Stream-isolation test proves note changes do not alter alert counts/IDs.
- [ ] Version change produces new dataset identity.
- [ ] Held-out seed is absent from/reasonably unrecoverable from public artifacts.
- [ ] Per-file/tree/package hashes and counts verify after packaging.

### 25.8 Benchmarks and documentation

- [ ] Small deterministic fixture and medium development benchmark are sealed.
- [ ] Held-out benchmark/evaluation package is sealed under restricted process.
- [ ] Large stress benchmark is generated or explicitly deferred with reason after medium measurement.
- [ ] Generation, validation, serialization, hashing, memory, disk, and package metrics are recorded without unsupported claims.
- [ ] Known limitations, synthetic-to-real gap, consumed held-out releases, and environment are documented.

---

## 26. Explicit Non-Goals

This phase and future generator implementation do **not** implement or design:

- SAT-SA execution-gap/negative-space/historical/peer detector logic;
- findings, evidence-correlation algorithms, or finding explanations;
- supervisory priority algorithm or risk score;
- Isolation Forest or any ML model;
- SAT-SA backend/API, frontend, dashboard, or reports;
- physical SQL/DuckDB application schema or migrations;
- SIEM, SOC, EDR, streaming telemetry, threat hunting, or automated response;
- real SOC/CSE integration or ingestion adapter to production systems;
- real organizations, employees, infrastructure, incidents, credentials, or sensitive data;
- production deployment, enterprise identity, retention, or accreditation;
- SIH presentation or demo video.

The generator may create private **expected evaluation contracts**. Those are not SAT-SA findings or algorithms.

---

## 27. Final Consistency Check

| Check | PASS / PARTIAL / OPEN | Evidence | Required action |
|---|---|---|---|
| `PROJECT_SPEC.md` scope | **PASS** | Periodic supervisory evidence only; human evaluation; no SIEM/real-time/response design | Preserve during implementation review |
| `RESEARCH_REPORT.md` recommendations | **PASS** | Heterogeneity, legitimate controls, held-out truth, manual review, false-positive focus | Report synthetic limitations |
| `ARCHITECTURE.md` data flow/provenance | **PASS** | Source-first render→canonical→provenance; offline/versioned packages | Future ingestion remains independent |
| `DATA_SCHEMA.md` families | **PASS** | §7 and implementation mapping cover every operational family and boundaries for review/audit | Contract tests must track schema version |
| `DATASET_GENERATION_SPEC.md` direct authority | **PASS** | Population, periods, profiles, scenarios, splits, validation, package separation preserved | Any deviation needs reviewed spec/version change |
| No scope creep | **PASS** | Explicit non-goals and module boundaries | Reject detector/backend/UI work in generator PRs |
| No schema contradiction | **PASS** | No new canonical family; implementation mapping references approved entities | Do not use implementation-only fields in exports without schema change |
| No hidden-truth leakage | **PASS (design)** | Separate roots/APIs, leakage scanner, package gate | Must pass implemented canary/held-out scan |
| No detector-generator circularity | **PASS (design)** | Config/import prohibition and semantic scenario engine | Enforce repository/code-owner boundaries |
| Offline requirement | **PASS (design)** | Minimal pinned stack and wheelhouse | Build/test with network disabled |
| Source-first provenance | **PASS** | Renderer trace and independent canonical/provenance oracle | Implement withheld-oracle test |
| Legitimate unusual cases | **PASS** | Dedicated control engine, ambiguity, balance assertions | Validate per split/family |
| Human evaluation independence | **PASS (design)** | Blinded samples, no initial SAT-SA score, private answer key | Assign reviewers/custodian |
| Named seed/reproducibility | **PASS (design)** | HMAC labels, stream isolation, Tests A–E | Pin exact bit-generator/dependencies |
| Source heterogeneity | **PASS** | SRC-A–E renderer plan | **OPEN:** approve JSON Lines timing |
| Exact numeric distribution parameters | **OPEN** | Correctly not invented; config architecture prepared | Approve envelopes before Milestone 2/6 |
| Period boundaries | **OPEN** | Config-driven P01–P06 plan | Approve synthetic UTC boundaries |
| Held-out seed/truth custody | **OPEN** | Roles/process specified but person/environment unassigned | Assign custodian and restricted storage |
| Target benchmark hardware/size | **OPEN** | Tier process defined without claims | Declare hardware and initial medium volume |
| Manual-review subset size/reviewers | **OPEN** | Stratified design complete | Confirm feasible size and at least two reviewers where possible |
| Generator code/dataset existence | **OPEN by design** | This is implementation planning only | Begin only after plan/open-decision review |

### 27.1 Required decisions before Milestone 1 closes

1. Approve Python 3.12 exact patch line, package lock method, and offline wheelhouse target platform.
2. Approve config format and private-config storage boundary.
3. Assign held-out seed/truth custodian and access process.
4. Approve synthetic period boundaries and public organization/source-profile matrix.
5. Approve initial parameter envelopes and demo control/process catalogue without detector thresholds.
6. Decide whether JSON Lines enters Milestone 3 or a later source-profile version.
7. Declare first benchmark hardware and manual-review staffing.

No generator code or dataset has been produced by this plan.
