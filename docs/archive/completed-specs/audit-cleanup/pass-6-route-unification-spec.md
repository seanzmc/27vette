# Pass 6A — Route Unification Characterization and Output-Orchestration Spec

Status: Implemented 2026-06-21.
Date: 2026-06-21
Recommended reasoning level for implementation agent: high.

## Goal

Create the first safe implementation slice toward internal route unification without flipping Stingray onto the Grand Sport/Z06 draft engine yet.

This pass must:

1. Prove the current generator outputs are fresh from the current route before using them as baselines.
2. Make the `generate_form.py` stdout/output-artifact contract explicit and tested for all active models.
3. Extract shared output orchestration into one model-neutral module while preserving current source-row assembly behavior.
4. Leave the actual Stingray `production.py` vs Grand Sport/Z06 `inspection.py` source-row assembly split for a later Pass 6B unless parity evidence proves it can be removed safely inside this approved slice.

Current public workflow is mostly normalized:

```text
stingray_master.xlsx
  -> scripts/generate_form.py --model <model>
  -> form-output/runtime/<slug>-runtime-contract.json
  -> scripts/generate_registry.py
  -> form-app/data.js
```

Current internal route is not yet congruent:

- Stingray still uses `production.py`.
- Grand Sport/Z06 still use `inspection.py` / draft builders.

This spec is intentionally a characterization/extraction pass, not a blind route flip.

## Prerequisite: Pass 5B must be landed

Pass 6A assumes role-driven schema validation is already in place. Before implementation, verify the current tree has Pass 5B behavior.

Required checks:

```sh
rg -n "LEGACY_MODEL_SOURCES|HEADER_PAIRS" scripts/corvette_form_generator/schema_validation.py && exit 1 || true
rg -n "REQUIRED_GENERATION_SOURCE_ROLES|missing_model_source_role" scripts/corvette_form_generator/schema_validation.py
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
.venv/bin/python -m pytest tests/test_schema_validation_metadata.py -q
```

If `LEGACY_MODEL_SOURCES`, static `HEADER_PAIRS`, or static active-model source-sheet requirements still exist, stop. Implement/restore Pass 5B first. Do not start Pass 6A against legacy schema validation because stale validator assumptions can hide source-role gaps while route code is moving.

## Diagnosis

### Root cause

`generate_form.py` has one CLI surface but still has two engines:

- `scripts/generate_form.py:33` defines `PRODUCTION_MODEL_KEYS = {"stingray"}`.
- `scripts/generate_form.py:36-39` routes Stingray to `production.main()`.
- `scripts/generate_form.py:42-112` routes Grand Sport/Z06 through `run_draft()`.
- `scripts/corvette_form_generator/production.py:158-674` manually assembles Stingray runtime data and compatibility JSON/CSV output.
- `scripts/corvette_form_generator/inspection.py:959-1229` builds Grand Sport/Z06 preview, draft, and clean runtime-contract artifacts.

Passes 1-5 normalized surrounding surfaces only if Pass 5B prerequisite above is green:

- Pass 1 added `build_model_runtime_contract(config, data)` in `scripts/corvette_form_generator/runtime_contract.py`.
- Pass 2 moved all promoted active model artifacts to `form-output/runtime/<slug>-runtime-contract.json`.
- Pass 3 retired generated workbook `form_*` sheets from routine runtime generation.
- Pass 4 made active/generatable model discovery workbook-owned.
- Pass 5A normalized editor gate reminders.
- Pass 5B must make schema validation use workbook source-role metadata before Pass 6A starts.

Remaining route drift is source-row assembly plus output orchestration, not registry publication or final runtime-contract cleanup.

### Current route evidence

From current tree:

- Active promoted runtime artifacts are clean runtime contracts under `form-output/runtime/`.
- `generate_registry.py` is the only normal writer for `form-app/data.js`.
- `production.py` still writes Stingray compatibility artifacts:
  - `form-output/stingray-form-data.json`
  - `form-output/stingray-form-data.csv`
- Grand Sport/Z06 still write optional inspection/preview/draft artifacts under `form-output/inspection/`.
- `production.py` has Stingray-only compatibility behavior, including removing `requires_z25` from interior rows before final output.
- `production.py` has its own rule assembly loop while `inspection.py` uses the shared draft rule builder path.

### Risk level

High.

Generator routing affects all active model runtime contracts. A direct switch of Stingray to the inspection/draft route was previously characterized as not parity-safe during Pass 1 preflight. This pass must not hide that risk by renaming a route flip as cleanup.

### Change type

Generator route orchestration + tests + docs/spec closure. No workbook source-data change intended. No runtime JS/CSS/HTML change intended. No product-rule behavior change intended.

## Pass 6A target design

Pass 6A creates a shared orchestration surface while preserving current source-row assembly engines:

```text
discover_generation_model_configs()
  -> generate_model_artifacts(config)
       -> current production assembly for Stingray
       -> current inspection/draft assembly for Grand Sport/Z06
       -> shared runtime-contract path reporting
       -> explicit optional artifact policy
       -> explicit stdout contract
```

Expected after Pass 6A:

- `generate_form.py` delegates active model generation to one top-level function.
- The top-level function returns a stable JSON-serializable result for every active model.
- Current generated runtime contracts remain parity-matched to fresh current-route baselines.
- Existing source-row assembly remains unchanged unless a smaller extracted helper is covered by parity tests.
- `PRODUCTION_MODEL_KEYS` may remain only inside the new orchestration module as an explicit temporary route-engine classifier. It must not remain as hidden routing logic in `generate_form.py`.
- Pass 6B will remove the source-row assembly split after Pass 6A makes output behavior explicit and baseline-safe.

## Exact files to change

1. `docs/audit-cleanup/pass-6-route-unification-spec.md`
   - This spec must be updated before final handoff with implemented status, changed files, gates, artifact diff review, and residual Pass 6B route work.

2. `scripts/generate_form.py`
   - Remove inline `run_production()` and `run_draft()` orchestration from this file.
   - Import and call `generate_model_artifacts(config)` from the new route orchestration module.
   - Keep workbook-owned model discovery through `discover_generation_model_configs()`.
   - Keep unsupported/inactive model rejection behavior.
   - Print the JSON result returned by `generate_model_artifacts(config)`.
   - Do not directly import `inspection` builders or `production` in this file after the extraction.

3. `scripts/corvette_form_generator/model_generation.py`
   - New module.
   - Define `generate_model_artifacts(config: ModelConfig) -> dict[str, Any]`.
   - Own the temporary route-engine decision for this slice.
   - Call the current Stingray production engine for `config.model_key == "stingray"`.
   - Call the current inspection/preview/draft/runtime-contract flow for `grand_sport` and `z06`.
   - Return one explicit stdout/result schema for all models.
   - Report optional artifacts under named keys instead of making route shape implicit.
   - Keep runtime-contract path reporting uniform for all models.

4. `scripts/corvette_form_generator/production.py`
   - Add a callable function, for example `generate_production_artifacts(config: ModelConfig) -> dict[str, Any]`, that performs current Stingray generation and returns artifact/count metadata instead of relying only on `main()` printing stdout.
   - Keep `main()` as a thin CLI/backward-compatible wrapper around the new callable.
   - Preserve current generated runtime contract, compatibility JSON, and compatibility CSV outputs.
   - Preserve current `workbook_backup`, `json`, `runtime_contract_json`, `csv`, and count fields unless the stdout contract is intentionally changed and tests are updated in the same pass.
   - Do not reintroduce workbook `form_*` writes.

5. `tests/test_generate_form_model_discovery_cli.py`
   - Update the Stingray CLI test to assert the explicit stdout contract after extraction.
   - Add or update Grand Sport and Z06 CLI tests so all active models expose the same top-level stdout keys.
   - Keep the inactive `zr1` rejection test.
   - If output JSON keys change, this file must document the expected new shape through assertions.

6. `tests/test_model_generation_route.py`
   - New focused Python test file.
   - Assert `scripts/generate_form.py` delegates to `generate_model_artifacts()` and no longer contains inline `run_production()` / `run_draft()` route bodies.
   - Assert `generate_model_artifacts()` returns a route-engine field and uniform artifact keys for mocked or lightweight generated results.
   - Assert temporary production-route classifier is named as temporary Pass 6A behavior, not hidden in `generate_form.py`.

7. `docs/Audit-route-map.md`
   - Update only after implementation.
   - Mark Pass 6A as characterization/output-orchestration extraction if implemented.
   - Keep the remaining source-row assembly split visible as Pass 6B unless implementation actually removes it with parity proof.

No other files are in scope for Pass 6A. If implementation needs another file, stop and revise this spec before editing.

## Explicit stdout contract

Current Stingray stdout from `production.py` includes:

```text
workbook
workbook_backup
json
runtime_contract_json
csv
choices
context_choices
standard_equipment
rules
price_rules
interiors
validation_errors
```

`tests/test_generate_form_model_discovery_cli.py` currently asserts this shape for Stingray.

Pass 6A must choose and test one contract:

### Required Pass 6A stdout schema

Every active model result from `scripts/generate_form.py --model <model>` must include these top-level keys:

```text
model_key
model_label
route_engine
runtime_contract_json
runtime_contract_artifacts
compatibility_artifacts
inspection_artifacts
preview_artifacts
draft_artifacts
counts
validation_errors
notes
```

Rules:

- `runtime_contract_json` must point to `form-output/runtime/<slug>-runtime-contract.json` for every active model.
- `compatibility_artifacts` must contain Stingray `json` and `csv` paths while those artifacts are retained.
- `compatibility_artifacts` must be an empty object for Grand Sport/Z06 unless a later spec adds compatibility outputs.
- `inspection_artifacts`, `preview_artifacts`, and `draft_artifacts` must be empty objects for Stingray unless a later spec adds those report outputs.
- `route_engine` may be `production` or `inspection_draft` in Pass 6A. That field is temporary evidence of the remaining split and must be removed or normalized in Pass 6B.
- If any legacy top-level keys (`json`, `csv`, `workbook_backup`) are preserved for backward compatibility, tests must assert both the legacy keys and the new normalized keys. If they are removed, tests and docs must be updated intentionally in this pass.

## Required implementation sequence

### 1. Verify prerequisites and clean worktree

```sh
git status --short --branch
rg -n "LEGACY_MODEL_SOURCES|HEADER_PAIRS" scripts/corvette_form_generator/schema_validation.py && exit 1 || true
rg -n "REQUIRED_GENERATION_SOURCE_ROLES|missing_model_source_role" scripts/corvette_form_generator/schema_validation.py
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
.venv/bin/python -m pytest tests/test_schema_validation_metadata.py -q
.venv/bin/python - <<'PY'
from pathlib import Path
print('excel_lock:', 'present' if Path('~$stingray_master.xlsx').exists() else 'absent')
PY
```

If `~$stingray_master.xlsx` exists, stop. Do not run workbook-writing generation.

### 2. Generate a fresh current-route baseline before copying artifacts

Do not baseline stale checked-in artifacts. First regenerate with the current pre-edit route:

```sh
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
.venv/bin/python scripts/generate_registry.py
```

Then inspect the worktree:

```sh
git status --short -- form-output form-app/data.js stingray_master.xlsx
```

If this current-route regeneration creates unexplained diffs, stop before implementation. Classify them as stale checked-in artifacts, timestamp-only churn, workbook binary churn, or true generated contract drift. Do not preserve stale output as a Pass 6A baseline.

Only after current-route generation is clean or explicitly classified and approved, copy baselines:

```sh
BASE=/tmp/27vette-pass6a-before
rm -rf "$BASE"
mkdir -p "$BASE"
cp form-output/runtime/stingray-runtime-contract.json "$BASE/stingray-runtime-contract.json"
cp form-output/runtime/grand-sport-runtime-contract.json "$BASE/grand-sport-runtime-contract.json"
cp form-output/runtime/z06-runtime-contract.json "$BASE/z06-runtime-contract.json"
cp form-output/stingray-form-data.json "$BASE/stingray-form-data.json"
cp form-output/stingray-form-data.csv "$BASE/stingray-form-data.csv"
cp form-app/data.js "$BASE/data.js"
shasum -a 256 form-output/stingray-form-data.csv > "$BASE/stingray-form-data.csv.sha256"
```

### 3. Add RED tests

Before implementation, add tests that fail while `generate_form.py` owns inline route bodies and stdout shape is route-specific.

Required RED coverage:

- `generate_form.py` delegates to `generate_model_artifacts()`.
- Active model CLI outputs share the Pass 6A stdout schema.
- Stingray still reports retained compatibility artifacts.
- Grand Sport/Z06 still report inspection/preview/draft artifacts as optional report outputs.
- `zr1` remains rejected before generation.
- Runtime-contract path is uniform for all active models.

### 4. Extract orchestration, preserve assembly

Implement only the Pass 6A extraction:

- Move current Grand Sport/Z06 orchestration from `generate_form.py` to `model_generation.py`.
- Add a callable production artifact function in `production.py` so `model_generation.py` does not scrape printed stdout.
- Keep current source-row assembly behavior intact.
- Keep current runtime-contract artifact paths intact.
- Keep compatibility/report artifacts intact.
- Keep product/business behavior out of route orchestration.

### 5. Compare artifacts, including CSV

After implementation, regenerate and compare:

```sh
BASE=/tmp/27vette-pass6a-before
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
.venv/bin/python scripts/generate_registry.py

node scripts/compare-generated-contracts.mjs "$BASE/stingray-runtime-contract.json" form-output/runtime/stingray-runtime-contract.json
node scripts/compare-generated-contracts.mjs "$BASE/grand-sport-runtime-contract.json" form-output/runtime/grand-sport-runtime-contract.json
node scripts/compare-generated-contracts.mjs "$BASE/z06-runtime-contract.json" form-output/runtime/z06-runtime-contract.json
node scripts/compare-generated-contracts.mjs "$BASE/stingray-form-data.json" form-output/stingray-form-data.json
cmp -s "$BASE/stingray-form-data.csv" form-output/stingray-form-data.csv
shasum -a 256 form-output/stingray-form-data.csv
cat "$BASE/stingray-form-data.csv.sha256"
```

CSV parity is required in Pass 6A because the spec preserves the compatibility CSV. If CSV changes, stop and classify the diff before continuing.

### 6. Update docs and spec closure

Before handoff:

- Mark this spec implemented with date, changed files, stdout contract, gate results, and residual Pass 6B work.
- Update `docs/Audit-route-map.md` to say Pass 6A extracted/shared output orchestration but source-row assembly remains split unless implementation proves otherwise.

## Constraints and boundaries

- No workbook source-data edits.
- No workbook metadata migration.
- No new dependencies.
- No runtime JS/CSS/HTML changes.
- No dealer submission endpoint, payload shape, Turnstile, or deployment-path changes.
- No product/RPO-specific hardcode cleanup in this pass.
- Do not remove `runtime_action` or `body_style_scope`.
- Do not remove the GBA / `opt_zyc_001` runtime hardcode here.
- Do not delete compatibility or inspection artifacts.
- Preserve visual/runtime behavior and active model registry semantics.
- Do not hide workbook data problems in Python.
- Do not reintroduce generated workbook `form_*` output into routine runtime generation.
- Do not flip Stingray to the draft/inspection source-row assembly engine in this pass unless the spec is revised and approved with exact parity evidence.

## Risks and mitigations

1. Stale baseline risk
   - Risk: copied checked-in artifacts are stale, so parity compares preserve stale output.
   - Mitigation: run current-route generation before baseline copy and stop on unexplained diffs.

2. Stingray parity drift
   - Risk: route extraction changes sections, choices, rules, color overrides, interiors, compatibility JSON, or CSV.
   - Mitigation: compare runtime contract, compatibility JSON, and CSV against fresh current-route baseline.

3. Stdout contract drift
   - Risk: `generate_form.py` consumers/tests break because Stingray stdout shape changes.
   - Mitigation: name the Pass 6A stdout schema directly and update `tests/test_generate_form_model_discovery_cli.py` intentionally.

4. Draft metadata leak
   - Risk: shared orchestration accidentally promotes draft-only fields or `dataset.status=draft_not_runtime_active`.
   - Mitigation: keep `build_model_runtime_contract()` finalization and registry promotion clean-contract tests.

5. Hidden product-rule rewrite
   - Risk: route extraction patches behavior with model/RPO-specific code.
   - Mitigation: structural pass only; product hardcodes move to later workbook-owned cleanup.

## Non-goals

- No full source-row assembly route flip.
- No business-rule hardcode cleanup.
- No GBA/ZYC runtime exception removal.
- No `runtime_action=replace` or `body_style_scope` migration.
- No Stingray exclusive-group cleanup.
- No Z06 option-ID/no-RPO cleanup.
- No copy allowlist cleanup.
- No workbook row edits.
- No generated workbook `form_*` revival or new workbook generated sheet policy.
- No registry promotion metadata change.
- No compatibility CSV deletion.

## Validation plan

Preflight/prerequisite:

```sh
git status --short --branch
rg -n "LEGACY_MODEL_SOURCES|HEADER_PAIRS" scripts/corvette_form_generator/schema_validation.py && exit 1 || true
rg -n "REQUIRED_GENERATION_SOURCE_ROLES|missing_model_source_role" scripts/corvette_form_generator/schema_validation.py
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
.venv/bin/python -m pytest tests/test_schema_validation_metadata.py -q
.venv/bin/python - <<'PY'
from pathlib import Path
print('excel_lock:', 'present' if Path('~$stingray_master.xlsx').exists() else 'absent')
PY
```

Current-route idempotency baseline before edits:

```sh
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
.venv/bin/python scripts/generate_registry.py
git status --short -- form-output form-app/data.js stingray_master.xlsx
```

Compile / focused Python gates:

```sh
.venv/bin/python -m py_compile \
  scripts/generate_form.py \
  scripts/corvette_form_generator/model_generation.py \
  scripts/corvette_form_generator/production.py \
  scripts/corvette_form_generator/inspection.py \
  scripts/corvette_form_generator/runtime_contract.py

.venv/bin/python -m pytest \
  tests/test_generate_form_model_discovery_cli.py \
  tests/test_model_generation_route.py \
  tests/test_runtime_contract_builder.py \
  tests/test_model_config_metadata.py \
  -q
```

Regeneration and strict parity:

```sh
BASE=/tmp/27vette-pass6a-before
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
.venv/bin/python scripts/generate_registry.py

node scripts/compare-generated-contracts.mjs "$BASE/stingray-runtime-contract.json" form-output/runtime/stingray-runtime-contract.json
node scripts/compare-generated-contracts.mjs "$BASE/grand-sport-runtime-contract.json" form-output/runtime/grand-sport-runtime-contract.json
node scripts/compare-generated-contracts.mjs "$BASE/z06-runtime-contract.json" form-output/runtime/z06-runtime-contract.json
node scripts/compare-generated-contracts.mjs "$BASE/stingray-form-data.json" form-output/stingray-form-data.json
cmp -s "$BASE/stingray-form-data.csv" form-output/stingray-form-data.csv
```

Targeted runtime/model gates:

```sh
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/z06-contract-preview.test.mjs
node --test tests/z06-form-data-draft.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Schema/registry sanity:

```sh
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
.venv/bin/python -m pytest tests/test_registry_promotion_metadata.py tests/test_schema_validation_metadata.py -q
git diff --check
```

Manual/browser smoke after green gates:

- Serve `form-app` locally.
- Switch Stingray, Grand Sport, and Z06.
- Verify body/trim selection, required step completion, option select/deselect, order summary, price totals, build download, and dealer submission modal validation.
- Confirm console has no JS errors.

## Expected non-changes

- Customer-facing app behavior unchanged.
- `form-app/data.js` payload unchanged except timestamp/order formatting if explicitly explained and covered.
- `form-output/runtime/*-runtime-contract.json` unchanged except timestamp fields.
- `form-output/stingray-form-data.json` unchanged except timestamp fields.
- `form-output/stingray-form-data.csv` byte-identical.
- `stingray_master.xlsx` unchanged.
- Dealer submission behavior unchanged.
- Optional audit/report tooling unchanged.

## Completion requirements

When implementing this spec, update this file before final handoff with:

- final status and date;
- changed files;
- Pass 5B prerequisite evidence;
- current-route idempotency/baseline evidence;
- RED route-orchestration/stdout-contract evidence;
- final gate results;
- generated artifact diff review, including CSV comparison;
- final stdout contract shape;
- whether `PRODUCTION_MODEL_KEYS` was removed from `generate_form.py` and where temporary route-engine classification remains;
- whether `production.py` remains active source-row assembly code;
- route-map update status;
- residual risks and recommended Pass 6B scope.

## Completion evidence

Implemented 2026-06-21.

Changed files:

- `scripts/generate_form.py`
- `scripts/corvette_form_generator/model_generation.py`
- `scripts/corvette_form_generator/production.py`
- `tests/test_generate_form_model_discovery_cli.py`
- `tests/test_model_generation_route.py`
- `docs/audit-cleanup/pass-6-route-unification-spec.md`
- `docs/Audit-route-map.md`

Implementation notes:

- `generate_form.py` now discovers workbook-owned active model configs, delegates all active generation to `generate_model_artifacts(base_config)`, and prints that shared result.
- New `model_generation.py` owns Pass 6A output orchestration and the explicit temporary route-engine classifier: `stingray` -> `production`; all other active models -> `inspection_draft`.
- `production.py` now exposes `generate_production_artifacts(config)` so shared orchestration can call Stingray generation without scraping `main()` stdout.
- Current source-row assembly is intentionally preserved: Stingray still uses production assembly; Grand Sport/Z06 still use inspection/draft assembly.
- The Pass 6A stdout contract is explicit and tested. All active models return `model_key`, `model_label`, `route_engine`, `runtime_contract_json`, `runtime_contract_artifacts`, `compatibility_artifacts`, `inspection_artifacts`, `preview_artifacts`, `draft_artifacts`, `counts`, `validation_errors`, and `notes`.
- Stingray also retains legacy compatibility stdout keys including `workbook_backup`, `json`, `runtime_contract_json`, `csv`, and counts.

Pass 5B prerequisite evidence:

- Search for `LEGACY_MODEL_SOURCES|HEADER_PAIRS` in `schema_validation.py`: no matches.
- Search for `REQUIRED_GENERATION_SOURCE_ROLES|missing_model_source_role` in `schema_validation.py`: matched shared role imports/usages and `missing_model_source_role` validation.
- `.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx`: valid, `issue_count: 0`.
- `.venv/bin/python -m pytest tests/test_schema_validation_metadata.py -q`: `22 passed`.
- Excel lock check: `excel_lock: absent`.

Current-route idempotency/baseline evidence:

- Before edits, regenerated the current route for Stingray, Grand Sport, Z06, then registry.
- Current-route generated diffs were classified before baseline copy:
  - `form-app/data.js`: timestamp-only after generated timestamp scrubbing.
  - `form-output/runtime/*.json`: timestamp-only.
  - `form-output/stingray-form-data.json`: timestamp-only.
  - `form-output/inspection/*.json`: timestamp-only.
  - `form-output/inspection/*.md`: generated-line-only.
- Baseline copied to `/tmp/27vette-pass6a-before`.
- Compatibility CSV baseline hash: `1168abba23572a3bbfe9e86d62c2c43e421c47a7da8a54cc08a8e8426f464364`.

RED evidence:

```sh
.venv/bin/python -m pytest tests/test_generate_form_model_discovery_cli.py tests/test_model_generation_route.py -q
```

Result before implementation: `3 failed, 1 passed`.

Failures covered active-model stdout contract drift, missing `generate_form.py` delegation to `model_generation.generate_model_artifacts()`, and missing `scripts/corvette_form_generator/model_generation.py`.

Focused implementation gates:

```sh
.venv/bin/python -m py_compile \
  scripts/generate_form.py \
  scripts/corvette_form_generator/model_generation.py \
  scripts/corvette_form_generator/production.py \
  scripts/corvette_form_generator/inspection.py \
  scripts/corvette_form_generator/runtime_contract.py

.venv/bin/python -m pytest \
  tests/test_generate_form_model_discovery_cli.py \
  tests/test_model_generation_route.py \
  tests/test_runtime_contract_builder.py \
  tests/test_model_config_metadata.py \
  -q
```

Result: `23 passed`.

Generated artifact parity:

- `node scripts/compare-generated-contracts.mjs` matched baseline vs current for:
  - `form-output/runtime/stingray-runtime-contract.json`
  - `form-output/runtime/grand-sport-runtime-contract.json`
  - `form-output/runtime/z06-runtime-contract.json`
  - `form-output/stingray-form-data.json`
- `cmp -s /tmp/27vette-pass6a-before/stingray-form-data.csv form-output/stingray-form-data.csv`: passed.
- Current CSV hash remained `1168abba23572a3bbfe9e86d62c2c43e421c47a7da8a54cc08a8e8426f464364`.

Runtime/model gates:

- `node --test tests/stingray-form-regression.test.mjs`: `86` passed.
- `node --test tests/stingray-generator-stability.test.mjs`: `13` passed.
- `node --test tests/grand-sport-contract-preview.test.mjs`: `6` passed.
- `node --test tests/grand-sport-draft-data.test.mjs`: `19` passed.
- `node --test tests/z06-contract-preview.test.mjs`: `3` passed.
- `node --test tests/z06-form-data-draft.test.mjs`: `23` passed.
- `node --test tests/multi-model-runtime-switching.test.mjs`: `44` passed.

Schema/registry sanity:

- `.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx`: valid, `issue_count: 0`.
- `.venv/bin/python -m pytest tests/test_registry_promotion_metadata.py tests/test_schema_validation_metadata.py -q`: `31 passed`.
- `git diff --check`: passed.

Manual/browser smoke:

- Served `form-app` locally with `.venv/bin/python -m http.server 8000`.
- Browser loaded `http://127.0.0.1:8000/`.
- Verified app globals exposed active models: `stingray`, `grandSport`, `z06`.
- Programmatically switched through all three active models with `activateModel()`, `resetDefaults()`, and `reconcileSelections()`.
- `currentOrder()` returned selected option rows for all three active models.
- Browser console reported no JS messages or errors.

Generated artifact diff review:

- Regeneration and Node tests rewrote generated JSON/Markdown/data.js timestamp fields only.
- No generated artifact payload drift was accepted as part of Pass 6A.
- Generated timestamp churn should be restored before final handoff so retained diffs are code/tests/docs only.

Route-map update:

- `docs/Audit-route-map.md` updated to mark Pass 6A implemented and keep Pass 6B source-row assembly unification visible as the next structural pass.

Residual risks / Pass 6B:

- `production.py` remains active Stingray source-row assembly code.
- `model_generation.py` intentionally retains temporary route classification (`stingray` -> `production`, other active models -> `inspection_draft`).
- Pass 6B should remove the source-row assembly split with fresh baseline parity. Do not include runtime business-rule hardcode cleanup in Pass 6B.

## Recommended next pass after Pass 6A

Pass 6B should remove the remaining source-row assembly split only after Pass 6A makes output orchestration explicit and parity-safe.

After route unification is proven, run separate workbook-owned business-rule cleanup passes:

1. GBA / `opt_zyc_001` runtime hardcode removal if workbook `runtime_rule_exceptions` fully covers behavior.
2. `runtime_action=replace` classification.
3. `body_style_scope` classification.
4. Stingray exclusive-group ID/style drift.
5. Z06 option-ID suffix / no-RPO drift.
6. residual copy allowlist decisions.

Do not start those in Pass 6A.

## Historical approval prompt

Approve Pass 6A implementation as scoped above?
