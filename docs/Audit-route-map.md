# Audit result

I did not change repo files, workbook sheets, generated artifacts, or runtime behavior. This is a code/docs audit from the current GitHub repo state.

The main diagnosis: **the public workflow has been mostly normalized, but the internal generation route is still split by model.** `generate_form.py` is now the single entry point, but it still sends **Stingray** through `production.main()` and sends **Grand Sport / Z06** through the inspection/draft/runtime-contract path. The repo docs say every active model should follow the same workbook → generator → registry → runtime contract shape, but the code still has a model-based fork.

## Status and evidence anchors

This file is an audit/action map. Passes 0, 1, and 2 now have implementation evidence under `docs/audit-cleanup/`; later passes still need their own spec before edits.

Current tree evidence:

- `scripts/generate_form.py` still hardcodes `MODEL_CONFIGS` and `PRODUCTION_MODEL_KEYS = {"stingray"}`.
- `scripts/generate_form.py` still routes Stingray to `production.main()` and Grand Sport/Z06 to `run_draft()`.
- `scripts/corvette_form_generator/runtime_contract.py` now provides the shared finalization seam used by both active routes.
- `scripts/corvette_form_generator/registry_promotion.py` still supports legacy `current_generation` and `draft_artifact` rows, but active promoted rows now use `artifact_type=runtime_contract`.
- Read-only workbook inspection confirms the promoted rows are now:
  - Stingray: `artifact_type=runtime_contract`, `artifact_path=form-output/runtime/stingray-runtime-contract.json`.
  - Grand Sport: `artifact_type=runtime_contract`, `artifact_path=form-output/runtime/grand-sport-runtime-contract.json`.
  - Z06: `artifact_type=runtime_contract`, `artifact_path=form-output/runtime/z06-runtime-contract.json`.
- `scripts/compare-generated-contracts.mjs` strips only timestamp keys (`generated_at`, `sourceGeneratedAt`, `generatedAt`) and then deep-compares everything else. It is a strict no-drift parity check, not a general validator for approved artifact-shape/path migrations.
- `form-app/app.js` still has a product/RPO-specific runtime exception: `choice.rpo === "GBA" && rule.source_id === "opt_zyc_001"`. The workbook exception row is `ex_gba_zyc`, source `opt_gba_001`, target `opt_zyc_001`.
- `scripts/corvette_form_generator/editor_ops.py` still includes `node --test tests/grand-sport-rule-audit.test.mjs` in Grand Sport gate reminders, even though `AGENTS.md` classifies that audit/report gate as optional.

## Codebase philosophy constraints

- The workbook owns Corvette product data and business rules: model metadata, source sheet roles, promotion metadata, option rows, rule rows, pricing rows, and runtime exceptions.
- Generated workbook `form_*` sheets, `form-output/*`, and `form-app/data.js` are outputs. Do not hand-edit them as source-of-truth fixes.
- Generators should read workbook tables, normalize, validate, and emit artifacts. Avoid hidden model/RPO-specific Python branches when a workbook row can express the decision.
- Runtime JavaScript should render and evaluate generated contracts generically. Product facts such as GBA/ZYC blocking belong in workbook-authored metadata, not runtime special cases.
- Dealer submission endpoint, payload shape, Turnstile behavior, and live model registry semantics are outside this audit unless a later spec explicitly scopes them.
- Route normalization must be parity-first when behavior is not explicitly being changed. If a later pass intentionally changes artifact shape or location, validate that migration with targeted consumer/promotion checks rather than treating timestamp-only contract comparison as sufficient.

## Current route map

**Stingray route**

`stingray_master.xlsx` → `scripts/generate_form.py --model stingray` → `production.py` → writes workbook `form_*` sheets → writes compatibility `form-output/stingray-form-data.json` / `.csv` plus `form-output/runtime/stingray-runtime-contract.json` → `generate_registry.py` → `form-app/data.js`.

Stingray now reaches registry promotion as `artifact_type=runtime_contract`; the workbook points the promoted input at `form-output/runtime/stingray-runtime-contract.json`.

**Grand Sport / Z06 route**

`stingray_master.xlsx` → `scripts/generate_form.py --model grand_sport|z06` → `inspection.py` → writes inspection report, contract preview, and form-data draft under `form-output/inspection/`, plus clean runtime contracts under `form-output/runtime/` → `generate_registry.py` → `form-app/data.js`.

`run_draft()` in `generate_form.py` does exactly that for non-Stingray models. The promoted Grand Sport/Z06 workbook rows point at the clean runtime-contract artifacts under `form-output/runtime/`, and `generate_registry.py` embeds those clean contracts.

**Registry route**

This part is mostly normalized. `generate_registry.py` is the only workflow that writes `form-app/data.js`, and it builds the browser registry from workbook promotion metadata and promoted runtime inputs.

## Main drift points to normalize

### 1. The model-based builder fork is the biggest remaining architecture problem

`generate_form.py` has one command surface, but `PRODUCTION_MODEL_KEYS = {"stingray"}` still decides whether the model goes to `production.main()` or the draft/inspection path.

Pass 1 unified the final runtime-contract builder, but active runtime models are still assembled by different internal logic:

- Stingray: `production.py`
- Grand Sport / Z06: `inspection.py` → `build_contract_preview()` → `build_form_data_draft()` → `build_model_runtime_contract()`

This is the same class of problem you described: the pathway looks consistent from the outside, but not inside the generator.

**Pass 1 normalized:** one model-neutral runtime-contract builder:

```text
build_model_runtime_contract(config, data)
```

Every active model now uses it. Remaining route work is source-row assembly/output-surface policy, not final contract cleanup.

### 2. Generated workbook `form_*` sheets are Stingray-only

The workbook has generated output sheets such as `form_steps`, `form_choices`, `form_rules`, `form_price_rules`, `form_interiors`, and `form_validation`, and the docs say those are generated outputs that should not be hand-edited.

But only the Stingray production path writes these sheets. The Grand Sport/Z06 path writes JSON/Markdown artifacts under `form-output/inspection/` instead.

This creates a false mental model: the workbook appears to contain the generated form contract for Stingray, while the other active models live outside the workbook.

**Normalize to one of two policies after a consumer audit:**

**Preferred:** retire `form_*` sheets from the runtime pathway and treat them as optional debug/report exports only.

**Alternative:** generate model-scoped workbook output sheets for every active model:

```text
form_stingray_choices
form_grandSport_choices
form_z06_choices
...
```

Do not keep one shared `form_*` surface that is effectively Stingray-owned. Either way, generated sheets remain outputs, not workbook source truth.

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

### 4. Adding future models still requires Python edits

`base_model_config(model_key)` is already generic enough to build a conventional config for any model key. But `generate_form.py` still hardcodes the accepted models in `MODEL_CONFIGS`, and argparse restricts `--model` to those keys.

So adding ZR1/ZR1X or another model still requires Python changes even if the workbook has the right metadata rows.

**Normalize to:** resolve generatable model keys from active/eligible workbook metadata in `model_master` and `model_workbook_sources`, then call `base_model_config(model_key)`. The script should fail if required workbook metadata is missing or incomplete.

Success condition: adding a future model requires workbook rows and assets/interior/rule data, not editing `generate_form.py`. Generatable/preview-eligible is not the same as promoted runtime-active; inactive future scaffold rows must not be accidentally published.

### 5. Stingray has a contract-shape compatibility exception

In the production path, Stingray interiors are built through the shared `build_model_interiors()` helper, but then `requires_z25` is removed “to keep the existing Stingray runtime contract byte-for-byte compatible.”

That is understandable as migration glue, but it is still a model-specific contract shape fork.

**Normalize to:** decide whether `requires_z25` belongs in the runtime schema. Then include it for every model or strip it for every model inside the shared runtime-contract trimming function.

### 6. Rule generation still has duplicated logic

Grand Sport/Z06 use the shared `build_draft_rules()` path in `rules.py`. Stingray still has its own rule assembly loop in `production.py`.

That is a risk area because rules are exactly where hardcoded one-off fixes tend to reappear.

**Normalize to:** one shared rule builder used by all models. If Stingray needs different behavior, represent it in workbook rows or explicit schema fields, not a separate builder path.

### 7. `runtime_action` and `body_style_scope` are live behavior, not cleanup metadata

A repo report records that all three active models still emit and consume these fields, with model-specific counts:

- Stingray: 144 active direct rules, 5 `runtime_action=replace`, 8 with `body_style_scope`
- Grand Sport: 122 active direct rules, 6 replace, 9 body-scoped
- Z06: 73 active direct rules, 1 replace, 3 body-scoped

`form-app/app.js` consumes both fields for live behavior. `runtime_action=replace` affects disable/click/removal behavior, and `body_style_scope` gates rule application.

**Do not delete these columns as “cleanup.”** First classify each use into a canonical owner:

```text
default_selection_rules
exclusive_groups
rule_groups
direct rule_mapping
runtime_rule_exceptions
keep as true special behavior
```

Any migration away from these direct-rule fields needs generated/runtime parity proof for the behavior, not just a workbook-column deletion.

### 8. Runtime JS still has at least one product hardcode

The runtime has a hardcoded exception in `form-app/app.js`:

```js
choice.rpo === "GBA" && rule.source_id === "opt_zyc_001"
```

The corresponding workbook-authored exception is `ex_gba_zyc`, source `opt_gba_001`, target `opt_zyc_001`. This is the cleanest example of “runtime knows Corvette product facts.”

**Normalize to:** add/confirm a focused RED test for the GBA/`opt_zyc_001` behavior, verify the workbook-driven `runtime_rule_exceptions` row covers the runtime case, then remove the hardcoded runtime exception only if the generated exception covers the behavior.

### 9. Editor gate reminders still create a Grand Sport-only audit pathway

Docs say `build_rule_sources.py` and `grand-sport-rule-audit` are optional audit/report tooling, not default readiness. But `editor_ops.py` still includes `node --test tests/grand-sport-rule-audit.test.mjs` in the default Grand Sport gate reminders.

**Normalize to:** split editor gates into:

```text
default readiness gates
optional audit/report gates
```

Otherwise Grand Sport continues to carry a special process burden that Z06 and Stingray do not. This can be a small workflow/config pass independent of the larger route consolidation.

### 10. Schema validation is mostly dynamic, but still has legacy model seeds

The schema validator now builds a source graph from workbook metadata and validates active source-role sheets dynamically.

But it still contains legacy/static model assumptions for Stingray and Grand Sport in `LEGACY_MODEL_SOURCES`, `HEADER_PAIRS`, and required sheet lists.

**Normalize to:** make validation fully role-driven from `model_workbook_sources`, with legacy seeds only for documented backward compatibility or removed entirely once the workbook graph is complete. Add tests for active workbook graph completeness before deleting fallback assumptions.

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

### Pass 3 — Decide the `form_*` sheet policy

Pick one after the consumer audit:

1. Retire shared workbook `form_*` sheets from the runtime path and keep any needed sheet export as an optional debug/report writer, or
2. Generate model-scoped workbook output sheets for every active model.

The current “Stingray writes workbook form sheets, other models write inspection files” setup should be removed. Do not delete `form_*` sheets or stop writing them until current consumers and docs are accounted for.

### Pass 4 — Make model discovery workbook-owned

Replace the hardcoded `MODEL_CONFIGS` list with workbook-driven model discovery from `model_master` plus complete active `model_workbook_sources` rows.

Adding a future model should not require touching `generate_form.py`, but inactive scaffold rows must remain non-promoted unless the workbook metadata explicitly activates and promotes them.

### Pass 5 — Gate and validator cleanup

Remove Grand Sport’s optional audit test from default editor gate reminders, and make schema validation rely on workbook source roles instead of legacy Stingray/Grand Sport seed assumptions.

This should be split if needed:

- editor gate reminder cleanup is a small workflow/config fix;
- schema validator cleanup is a source-contract pass that needs tests for role-driven active sheet discovery, header parity, required source roles, and any retained compatibility fallback.

### Pass 6 — Business-rule hardcode cleanup

After the route is unified, handle the smaller rule cleanup items:

- GBA / `opt_zyc_001` runtime hardcode backed by workbook `ex_gba_zyc`
- `runtime_action=replace` classification
- `body_style_scope` classification
- Stingray exclusive-group ID/style drift
- Z06 option-ID suffix / no-RPO drift
- residual copy allowlist decisions

Those are real, but they should come after the builder/pathway fork is removed unless one is blocking current runtime correctness.

## Bottom line

The repo is past the worst version of the problem. The registry, promotion metadata, workbook source roles, and model metadata are largely workbook-owned now.

The remaining structural issue is narrower and clearer after Passes 1-2:

```text
One CLI entrypoint
but two model-generation engines
and one unresolved generated workbook form_* policy.
```

Next safe pass: decide the generated workbook `form_*` sheet policy from the Pass 0 consumer inventory, without deleting or stopping sheet writes until current consumers and docs are accounted for.
