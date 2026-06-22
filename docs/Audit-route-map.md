# Audit route map

Status refreshed 2026-06-22 after the Pass 8 report/spec. This document is a code/docs route map; the refresh did not change workbook sheets, runtime code, or generated artifacts.

The main diagnosis: **the active public workflow and generator orchestration are now normalized through one source-assembly facade.** `generate_form.py` delegates every active model to `model_generation.generate_model_artifacts()`, and that module now calls `source_assembly.assemble_model_source()` for Stingray, Grand Sport, and Z06. Pass 6C preserved the existing Stingray compatibility JSON/CSV payload and the Grand Sport/Z06 review payload shapes with timestamp-ignored runtime parity.

## Status and evidence anchors

This file is an audit/action map. Passes 0 through 8 now have implementation evidence under `docs/audit-cleanup/`. Later implementation passes still need their own spec before edits.

Current tree evidence:

- `scripts/generate_form.py` no longer hardcodes `MODEL_CONFIGS` or owns the production/draft route branch; active/generatable models come from workbook discovery and generation delegates to `model_generation.generate_model_artifacts()`.
- `scripts/corvette_form_generator/model_generation.py` now uses one normalized route label, `source_assembly`, and delegates workbook source assembly to `scripts/corvette_form_generator/source_assembly.py` for every active model.
- `scripts/corvette_form_generator/runtime_contract.py` now provides the shared finalization seam used by both active routes.
- `scripts/corvette_form_generator/registry_promotion.py` still supports legacy `current_generation` and `draft_artifact` rows, but active promoted rows now use `artifact_type=runtime_contract`.
- Read-only workbook inspection confirms the promoted rows are now:
  - Stingray: `artifact_type=runtime_contract`, `artifact_path=form-output/runtime/stingray-runtime-contract.json`.
  - Grand Sport: `artifact_type=runtime_contract`, `artifact_path=form-output/runtime/grand-sport-runtime-contract.json`.
  - Z06: `artifact_type=runtime_contract`, `artifact_path=form-output/runtime/z06-runtime-contract.json`.
- `scripts/compare-generated-contracts.mjs` strips only timestamp keys (`generated_at`, `sourceGeneratedAt`, `generatedAt`) and then deep-compares everything else. It is a strict no-drift parity check, not a general validator for approved artifact-shape/path migrations.
- `form-app/app.js` no longer has the product/RPO-specific GBA/ZYC bypass; Pass 7 replaced it with generic `runtimeRuleExceptions` precedence. The workbook exception row remains `ex_gba_zyc`, source `opt_gba_001`, target `opt_zyc_001`.
- `runtime_action=replace` and `body_style_scope` still carry live direct-rule behavior. Pass 8 completed the row-level classification report in `docs/audit-cleanup/pass-8-direct-rule-field-classification-report.md`; any column deletion, row deletion, emitted-rule trim, replacement migration, or direct-rule scope-matcher change still needs a later implementation spec.
- `scripts/corvette_form_generator/editor_ops.py` no longer includes `node --test tests/grand-sport-rule-audit.test.mjs` in Grand Sport default gate reminders; the rule-audit tooling remains optional.
- `scripts/corvette_form_generator/schema_validation.py` now shares generation role lists from `model_configs.py` and no longer uses `LEGACY_MODEL_SOURCES` or `HEADER_PAIRS`.

## Codebase philosophy constraints

- The workbook owns Corvette product data and business rules: model metadata, source sheet roles, promotion metadata, option rows, rule rows, pricing rows, and runtime exceptions.
- Generated workbook `form_*` sheets, `form-output/*`, and `form-app/data.js` are outputs. Do not hand-edit them as source-of-truth fixes.
- Generators should read workbook tables, normalize, validate, and emit artifacts. Avoid hidden model/RPO-specific Python branches when a workbook row can express the decision.
- Runtime JavaScript should render and evaluate generated contracts generically. Product facts such as GBA/ZYC blocking belong in workbook-authored metadata, not runtime special cases.
- Dealer submission endpoint, payload shape, Turnstile behavior, and live model registry semantics are outside this audit unless a later spec explicitly scopes them.
- Route normalization must be parity-first when behavior is not explicitly being changed. If a later pass intentionally changes artifact shape or location, validate that migration with targeted consumer/promotion checks rather than treating timestamp-only contract comparison as sufficient.

## Current route map

**Active model generation route**

`stingray_master.xlsx` → `scripts/generate_form.py --model stingray|grand_sport|z06` → `model_generation.generate_model_artifacts()` → `source_assembly.assemble_model_source()` → `build_model_runtime_contract()` → `form-output/runtime/<slug>-runtime-contract.json` → `generate_registry.py` → `form-app/data.js`.

Stingray still writes compatibility `form-output/stingray-form-data.json` / `.csv` in addition to `form-output/runtime/stingray-runtime-contract.json`. Grand Sport/Z06 still expose optional review payloads only when `--emit-inspection --inspection-output <dir>` is passed. The promoted workbook rows for all active models point at the clean runtime-contract artifacts under `form-output/runtime/`, and `generate_registry.py` embeds those clean contracts.

**Registry route**

This part is mostly normalized. `generate_registry.py` is the only workflow that writes `form-app/data.js`, and it builds the browser registry from workbook promotion metadata and promoted runtime inputs.

## Main drift points to normalize

### 1. Source-row assembly route is normalized for active generation

**Pass 6C normalized:** `model_generation.generate_model_artifacts()` no longer carries a temporary production-vs-review route classifier. Every active model now enters `source_assembly.assemble_model_source()` and reports the same stdout `route_engine` value, `source_assembly`.

Pass 6C was parity-first: it did not rewrite workbook source rows, retire Stingray compatibility JSON/CSV, or change Grand Sport/Z06 explicit review artifact shapes. The source-assembly facade preserves those current payload surfaces while removing the active orchestration split.

**Pass 1 normalized:** one model-neutral runtime-contract builder:

```text
build_model_runtime_contract(config, data)
```

Every active model now uses it, Pass 6A made stdout/output artifact reporting explicit across active models, and Pass 6C moved active generation behind one source-assembly facade.

### 2. Generated workbook `form_*` sheets are Stingray-only

**Pass 3 normalized:** generated workbook `form_*` sheets were retired from the routine runtime-generation workflow.

The active generated runtime source is now the promoted runtime-contract path:

```text
form-output/runtime/<slug>-runtime-contract.json
```

Stingray still writes its compatibility JSON/CSV artifacts, but normal `generate_form.py --model stingray` runs no longer rewrite or save workbook generated sheets. Any future workbook-native generated export should be an explicitly scoped debug/report writer with a named consumer, not the default runtime path.

### 3. Grand Sport/Z06 runtime artifacts still carry “draft/inspection” ancestry

The runtime contract for Grand Sport/Z06 is clean by the time it reaches `form-app/data.js`, because `write_runtime_contract_artifact()` strips draft-only fields and writes a clean runtime artifact. Promotion validates that promoted artifacts are clean; legacy Stingray-compatible contracts may still omit `dataset.status`, while draft status is rejected.

Pass 2 moved active promoted runtime artifacts out of inspection ancestry:

```text
form-output/runtime/stingray-runtime-contract.json
form-output/runtime/grand-sport-runtime-contract.json
form-output/runtime/z06-runtime-contract.json
```

**Pass 2 normalized to that same path set.**

Inspection/preview/draft artifacts remain optional adjacent reports. This was a workbook metadata migration because `model_registry_promotion.artifact_path` owns promoted artifact paths.

### 4. Workbook-owned model discovery is normalized

Pass 4 removed the hardcoded `MODEL_CONFIGS` accepted-model list. Active/generatable models are discovered from workbook metadata:

```text
model_master.active
model_workbook_sources exact-match active required source roles
model_variants exact-match active rows matching expected_variant_count
```

Adding a future model should require workbook rows and assets/interior/rule data, not editing `generate_form.py`. Generatable/preview-eligible is still separate from promoted runtime-active; inactive future scaffold rows must not be accidentally published.

### 5. Stingray has a contract-shape compatibility exception

In the production path, Stingray interiors are built through the shared `build_model_interiors()` helper, but then `requires_z25` is removed “to keep the existing Stingray runtime contract byte-for-byte compatible.”

That is understandable as migration glue, but it is still a model-specific contract shape fork.

**Normalize to:** decide whether `requires_z25` belongs in the runtime schema. Then include it for every model or strip it for every model inside the shared runtime-contract trimming function.

### 6. Rule generation still has duplicated logic

Grand Sport/Z06 use the shared `build_draft_rules()` path in `rules.py`. Stingray still has its own rule assembly loop in `production.py`.

That is a risk area because rules are exactly where hardcoded one-off fixes tend to reappear.

**Normalize to:** one shared rule builder used by all models. If Stingray needs different behavior, represent it in workbook rows or explicit schema fields, not a separate builder path.

### 7. `runtime_action` and `body_style_scope` are live behavior, not cleanup metadata

Pass 8 records that all three active models still emit and consume these fields, with model-specific counts:

- Stingray: 144 active direct rules, 5 `runtime_action=replace`, 8 with `body_style_scope`
- Grand Sport: 122 active direct rules, 6 replace, 9 body-scoped
- Z06: 73 active direct rules, 1 replace, 3 body-scoped

`form-app/app.js` consumes both fields for live behavior. `runtime_action=replace` affects disable/click/removal behavior, and `body_style_scope` gates rule application.

**Do not delete these columns as “cleanup.”** Pass 8 classified each use into candidate canonical owners:

```text
default_selection_rules
exclusive_groups
rule_groups
direct rule_mapping
runtime_rule_exceptions
keep as true special behavior
```

Pass 8 findings: most body-scoped rows are plausible OVS-derived cleanup candidates; Grand Sport BC4/ZZ3 rows 5 and 95 are an apparent duplicate/stale pair; replacement rows split across direct-default, exclusive-peer, default-selection, grouped-dependency, and product-decision candidates. Any migration away from these direct-rule fields still needs generated/runtime parity proof for the behavior, not just a workbook-column deletion.

### 8. GBA/ZYC runtime hardcode is normalized

Pass 7 removed the hardcoded browser exception:

```js
choice.rpo === "GBA" && rule.source_id === "opt_zyc_001"
```

The runtime now uses generated `runtimeRuleExceptions` metadata generically when a candidate source option should replace a currently selected exception target. The corresponding workbook-authored exception remains `ex_gba_zyc`, source `opt_gba_001`, target `opt_zyc_001`.

Remaining product-rule cleanup should not reuse this hardcode. Add workbook metadata or generic generated-data evaluation with focused behavior tests.

### 9. Editor gate reminders are normalized

Pass 5A removed `node --test tests/grand-sport-rule-audit.test.mjs` from Grand Sport default editor gate reminders and added focused `gate_reminders()` tests.

`build_rule_sources.py` and `grand-sport-rule-audit` remain available as optional audit/report tooling, not default readiness gates.

Current default readiness reminders keep:

```text
generate_form.py --model grand_sport
validate_workbook_schema.py
grand-sport-contract-preview.test.mjs
grand-sport-draft-data.test.mjs
```

That removes the Grand Sport-only optional audit burden from the default editor workflow without deleting audit tooling.

### 10. Schema validation is role-driven

Pass 5B made schema validation share the canonical generation source-role lists from `model_configs.py`:

```text
REQUIRED_GENERATION_SOURCE_ROLES
OPTIONAL_GENERATION_SOURCE_ROLES
```

The validator no longer uses `LEGACY_MODEL_SOURCES` or `HEADER_PAIRS`. Active model source sheets are required through exact-match active `model_workbook_sources` rows, and missing required roles emit `missing_model_source_role`. Shared/all rows do not satisfy active generation requirements. Boolean/RPO/price checks for active source sheets are now role-derived rather than hardcoded to Stingray/Grand Sport sheet names.

## Recommended cleanup sequence

### Pass 0 — Baseline promoted inputs and consumers

Goal: prove what the registry consumed before changing builders or artifact surfaces.

Pass 0 read then-current promoted inputs from `model_registry_promotion` and the registry resolver:

```text
stingray     current_generation -> form-output/stingray-form-data.json
grand_sport  draft_artifact     -> form-output/inspection/grand-sport-runtime-contract.json
z06          draft_artifact     -> form-output/inspection/z06-runtime-contract.json
```

Then inventory consumers of:

```text
form-output/stingray-form-data.json
form-output/inspection/*-runtime-contract.json
generated workbook form_* sheets
model_registry_promotion.artifact_path
```

For a no-behavior-change builder pass, snapshot those promoted inputs before/after generation and use `node scripts/compare-generated-contracts.mjs` only where strict timestamp-only parity is expected. Do not use that comparator as the only validation for approved artifact path/shape migrations.

### Pass 1 — Unified runtime contract builder

Status: implemented in `docs/audit-cleanup/pass-1-unified-runtime-contract-builder-spec.md`.

Goal: make Stingray, Grand Sport, and Z06 use the same contract-builder function.

Do not change generated behavior yet. Keep output parity as the success condition. Extract around the clean runtime contract shape first; do not force Stingray workbook sheet writing into the draft/inspection path or vice versa just to make the first refactor look symmetrical.

Success criteria:

```text
generate_form.py --model stingray
generate_form.py --model grand_sport
generate_form.py --model z06
```

all call the same model-neutral runtime-contract builder. Output writers may still differ during this pass, and strict timestamp-only contract parity should hold for the promoted runtime inputs.

### Pass 2 — Artifact surface normalization

Status: implemented in `docs/audit-cleanup/pass-2-runtime-artifact-surface-normalization-spec.md`.

Move every active model to the same clean runtime artifact contract:

```text
form-output/runtime/<slug>-runtime-contract.json
```

Then update `model_registry_promotion.artifact_path` to point to the neutral runtime path for every promoted model, including whatever policy is chosen for Stingray's current-generation input.

Because this pass changes workbook promotion metadata, it must use the workbook safe-save path, refuse Excel lock files, and verify the saved `model_registry_promotion` rows on disk before claiming the change landed. It must also update registry/promotion tests to validate the new path semantics.

### Pass 3 — Generated workbook `form_*` sheet policy

Status: implemented in `docs/audit-cleanup/pass-3-form-sheet-retirement-policy-spec.md`.

Shared Stingray-only workbook `form_*` generated sheets are retired from the routine runtime path. Active generated runtime contracts live under `form-output/runtime/`; optional inspection/preview/draft artifacts are explicit review outputs via `--emit-inspection --inspection-output <dir>`. Do not recreate workbook generated sheets unless a future opt-in debug/report export pass names the consumer.

### Pass 4 — Make model discovery workbook-owned

Status: implemented in `docs/audit-cleanup/pass-4-workbook-owned-model-discovery-spec.md`.

`generate_form.py` no longer keeps a hardcoded `MODEL_CONFIGS` active-model list. Active/generatable models are discovered from `model_master`, exact-match complete active `model_workbook_sources` rows, and valid exact-match active `model_variants` rows. `model_registry_promotion` remains a separate runtime-publication decision.

Adding a future model should not require touching `generate_form.py`, but inactive scaffold rows must remain non-promoted unless the workbook metadata explicitly activates and promotes them.

### Pass 5 — Gate and validator cleanup

Status: implemented in:

- `docs/audit-cleanup/pass-5a-editor-gate-reminders-spec.md`
- `docs/audit-cleanup/pass-5b-schema-validator-role-driven-spec.md`

Pass 5A removed Grand Sport’s optional audit test from default editor gate reminders while preserving optional audit tooling. Pass 5B made schema validation rely on workbook source roles and the canonical generator role constants instead of legacy Stingray/Grand Sport seed assumptions.

### Pass 6A — Route unification characterization and output orchestration

Status: implemented in `docs/audit-cleanup/pass-6-route-unification-spec.md`.

Pass 6A made `generate_form.py` delegate all active models through `model_generation.generate_model_artifacts()`, named the stdout/output-artifact contract, and preserved parity against freshly regenerated current-route baselines. It intentionally kept the source-row assembly split in place: Stingray still uses production assembly, and Grand Sport/Z06 still use inspection/draft assembly.

### Pass 6B — Optional inspection artifact emission

Status: implemented in `docs/audit-cleanup/pass-6b-inspection-artifact-policy-spec.md`.

Pass 6B made Grand Sport/Z06 normal generation write only clean runtime contracts by default, while keeping inspection/preview/draft artifacts available through explicit review mode. It removed routine checked-in Grand Sport/Z06 inspection/preview/draft artifacts and moved tests that need draft/preview data to temp review output. It preserved the source-row assembly split.

### Pass 6C — Source-row assembly route unification

Status: implemented in `docs/audit-cleanup/pass-6c-source-row-assembly-unification-spec.md`.

Pass 6C removed the temporary route-engine classifier in `model_generation.py`, added `source_assembly.assemble_model_source()`, and made Stingray, Grand Sport, and Z06 report the same `source_assembly` route while preserving runtime-contract, review-artifact, and Stingray compatibility parity.

### Pass 7 — Runtime rule exception hardcode cleanup

Status: implemented in `docs/audit-cleanup/pass-7-runtime-rule-exception-hardcode-cleanup-spec.md`.

Pass 7 removed the remaining browser runtime product hardcode for GBA / `opt_zyc_001` by making `form-app/app.js` use workbook-generated `runtimeRuleExceptions.ex_gba_zyc` generically. It did not change workbook rows, generated artifacts, dealer submission behavior, or broader direct-rule field semantics.

Deferred to later separately scoped passes:

- `runtime_action=replace` ownership/migration passes by product area
- Stingray exclusive-group ID/style drift
- Z06 option-ID suffix / no-RPO drift
- residual copy allowlist decisions

### Pass 8 — Direct rule field classification

Status: completed report-only implementation in `docs/audit-cleanup/pass-8-direct-rule-field-classification-report.md`; closure recorded in `docs/audit-cleanup/pass-8-direct-rule-field-classification-spec.md`.

Goal: produce a report-only row classification for active `runtime_action=replace` and `body_style_scope` usage across `rule_mapping`, `grandSport_rule_mapping`, and `z06_rule_mapping` before deleting workbook columns, changing generated `rules` payload fields, or changing browser direct-rule evaluation.

Current preflight counts from the spec:

- `rule_mapping`: 5 `replace` rows; 8 body-scoped rows.
- `grandSport_rule_mapping`: 6 `replace` rows; 9 body-scoped rows.
- `z06_rule_mapping`: 1 `replace` row; 3 body-scoped rows.

Pass 8 was intentionally report-only. Pass 9 implemented Candidate A, the body-style scope retirement parity pass. Any `runtime_action=replace` migration, rule-column deletion, generator payload trim, or direct-rule runtime scope-matcher change still needs a later implementation spec.

### Pass 9 — Body-style scope retirement parity

Status: implemented in `docs/audit-cleanup/pass-9-body-style-scope-retirement-spec.md`.

Pass 9 blanked all current OVS-derived direct-rule `body_style_scope` values in `rule_mapping`, `grandSport_rule_mapping`, and `z06_rule_mapping`; deleted the duplicate Grand Sport copy row `gs_copy_rule_opt_bc4_002_requires_opt_zz3_001_opt_bc4_002_requires_opt_zz3_001_convertible`; regenerated active model runtime artifacts and registry; and updated stale tests to assert OVS-owned scope rather than direct-rule scope. Runtime direct-rule matching code, `runtime_action=replace`, the `body_style_scope` column, and generated payload shape were unchanged.

Recommended next pass: Candidate B from the Pass 8 report — a narrow Stingray spoiler replacement ownership pass for 5ZU/5ZZ/TVS and the 5ZW/ZF1 product-decision edges. Keep Grand Sport/Z06 replacement rows and direct-rule `scopeMatches()` semantics separate.

## Bottom line

The repo is past the worst version of the route problem. The registry, promotion metadata, model discovery, workbook source roles, schema source-contract validation, output orchestration, and active source-assembly facade are normalized for the active models.

The next safe pass is a narrow Stingray spoiler replacement ownership spec/implementation for the Pass 8 Candidate B rows. Do not delete `runtime_action`, trim emitted rule fields, migrate Grand Sport/Z06 replacement behavior, or change direct-rule runtime matching until separately approved.
