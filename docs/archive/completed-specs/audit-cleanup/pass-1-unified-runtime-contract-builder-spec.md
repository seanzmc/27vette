# Pass 1 — Unified Runtime Contract Builder Spec

Status: Implemented; previously blocked Stingray generator parity gate completed on 2026-06-21.
Date: 2026-06-21

## Goal

Create a shared runtime-contract build/finalization seam used by both current active generation routes:

- Stingray current-generation path in `scripts/corvette_form_generator/production.py`.
- Grand Sport/Z06 inspection/draft path in `scripts/corvette_form_generator/inspection.py`.

This pass is no-behavior-change. It must preserve the current promoted inputs and strict timestamp-ignored parity from Pass 0.

## Preflight evidence

Branch/status at spec time:

```text
## schema-ingestion-normalization...origin/main
schema-ingestion-normalization
excel_lock: absent
```

Pass 0 report:

- `docs/audit-cleanup/pass-0-promoted-input-baseline.md`
- Current promoted inputs:
  - `stingray`: `current_generation` -> `form-output/stingray-form-data.json`
  - `grand_sport`: `draft_artifact` -> `form-output/inspection/grand-sport-runtime-contract.json`
  - `z06`: `draft_artifact` -> `form-output/inspection/z06-runtime-contract.json`
- Baseline copies:
  - `/tmp/27vette-pass0-baseline-20260621T032938Z/stingray-form-data.json`
  - `/tmp/27vette-pass0-baseline-20260621T032938Z/grand-sport-runtime-contract.json`
  - `/tmp/27vette-pass0-baseline-20260621T032938Z/z06-runtime-contract.json`

Current code evidence:

- `scripts/generate_form.py:36-41` hardcodes `MODEL_CONFIGS` and `PRODUCTION_MODEL_KEYS = {"stingray"}`.
- `scripts/generate_form.py:52-55` routes Stingray to `production.main()`.
- `scripts/generate_form.py:58-87` routes Grand Sport/Z06 through inspection/preview/draft/runtime-contract artifact output.
- `scripts/corvette_form_generator/production.py:793-822` assembles the Stingray generated data dict, calls `live_contract_data(data)`, and writes `form-output/stingray-form-data.json`.
- `scripts/corvette_form_generator/inspection.py:958-1201` builds the Grand Sport/Z06 draft dataset.
- `scripts/corvette_form_generator/inspection.py:1213-1226` calls `live_contract_data(draft)` to write clean `*-runtime-contract.json` artifacts.
- `scripts/corvette_form_generator/registry_promotion.py:146-172` currently owns `live_contract_data()`.
- `tests/test_registry_promotion_metadata.py:195-228` already covers `live_contract_data()` trimming/status behavior.

Important characterization result from spec preflight:

- A read-only experiment using `inspection.build_contract_preview()` + `inspection.build_form_data_draft()` + `live_contract_data()` for Stingray does not match current `form-output/stingray-form-data.json`.
- Differences include at least:
  - section count: current Stingray promoted input has 51 sections, inspection-derived Stingray runtime has 32;
  - rule count: current has 144 rules, inspection-derived has 113;
  - color override count: current has 245, inspection-derived has 237;
  - payload shape differences such as explicit empty `display_behavior` fields.
- Therefore Pass 1 must not switch Stingray wholesale to the inspection/draft engine while claiming no behavior drift.

## Diagnosis

The remaining route split has two layers:

1. Runtime-contract finalization is duplicated by route:
   - Stingray uses `production.py` to assemble data, then calls `live_contract_data()` and writes `stingray-form-data.json`.
   - Grand Sport/Z06 use `inspection.py` to assemble a draft, then call `live_contract_data()` and write `*-runtime-contract.json`.
2. Source-row/data assembly is still materially different:
   - Stingray production emits generated workbook `form_*` sheets and a Stingray JSON/CSV artifact.
   - Grand Sport/Z06 emit inspection/preview/draft/runtime-contract artifacts.
   - Directly reusing the inspection builder for Stingray is not parity-safe today.

Root cause: the repo has a shared final runtime cleanup function, but it is housed in registry promotion and reached indirectly from two separate engines. The safe first refactor is to move the runtime-contract finalization boundary into a model-neutral generator module and make both existing engines call it, without changing the current source-row assembly or output surfaces.

Change type: generator-only + test-only + docs/spec progress update. No workbook/source-data change.

Risk level: medium. The intended source edit is small, but all promoted generated runtime inputs are touched by validation generators, and a mistaken change to finalization could affect live runtime data.

## User direction captured

The preferred future direction is to retire generated workbook `form_*` sheets from the workflow.

Pass 1 should support that direction by separating runtime-contract finalization from workbook-sheet writing. It should not add new dependencies on `form_*` sheets and should not make `form_*` harder to retire.

Actual `form_*` retirement is not part of Pass 1. It remains a later scoped pass because Pass 0 found active editor/test/docs consumers of the generated sheet surface.

## Exact files to change

Implementation files:

1. Add `scripts/corvette_form_generator/runtime_contract.py`
   - New model-neutral runtime-contract finalization module.
   - Proposed public function:

     ```python
     def build_model_runtime_contract(config: ModelConfig, data: dict[str, Any]) -> dict[str, Any]:
         ...
     ```

   - It should apply the existing live-runtime cleanup/status behavior by delegating to the existing `registry_promotion.live_contract_data()` or by moving that implementation while preserving its public import for compatibility.
   - It should not read or write the workbook.
   - It should not know about `form_*` sheets.
   - It should not inspect model keys for product-specific behavior.

2. Update `scripts/corvette_form_generator/production.py`
   - Replace direct `live_contract_data(data)` usage with `build_model_runtime_contract(MODEL_CONFIG, data)`.
   - Keep existing workbook `form_*` sheet writer calls unchanged for this pass.
   - Keep existing `form-output/stingray-form-data.json` and `.csv` output paths unchanged.
   - Do not change the Stingray source-row assembly loop, rule loop, `requires_z25` compatibility strip, section emission, or color override behavior in this pass.

3. Update `scripts/corvette_form_generator/inspection.py`
   - Replace the local import/call to `live_contract_data(draft)` inside `write_runtime_contract_artifact()` with `build_model_runtime_contract(config, draft)` or a helper that has access to `config`.
   - If changing `write_runtime_contract_artifact()` signature is needed, update `scripts/generate_form.py` call sites without changing output paths.
   - Keep preview/draft/inspection artifact paths and draft payloads unchanged.

4. Update `scripts/generate_form.py` only if the `write_runtime_contract_artifact()` call signature changes.
   - Keep `PRODUCTION_MODEL_KEYS = {"stingray"}` in place for this pass.
   - Keep accepted `MODEL_CONFIGS` unchanged for this pass.

Tests:

5. Add `tests/test_runtime_contract_builder.py` or extend `tests/test_registry_promotion_metadata.py`.
   - Prove `build_model_runtime_contract()` converts draft datasets to runtime-active contracts and strips draft-only fields exactly as the current `live_contract_data()` behavior does.
   - Add a small source-usage guard that both active generator routes import/use `build_model_runtime_contract`, unless a better behavior-level test is practical.
   - Keep existing `live_contract_data()` tests green for backward compatibility if that function remains exported.

Spec/progress docs:

6. Update this file after implementation with:
   - actual changed files;
   - generated artifact handling;
   - gate results;
   - whether generated/workbook timestamp churn was restored.

## Files/sheets/artifacts not to change

Do not intentionally change:

- `stingray_master.xlsx` source rows or workbook metadata.
- `model_registry_promotion` rows or artifact paths.
- `form-output/stingray-form-data.json` payload, except timestamp-only regeneration churn during validation.
- `form-output/inspection/grand-sport-runtime-contract.json` payload, except timestamp-only regeneration churn during validation.
- `form-output/inspection/z06-runtime-contract.json` payload, except timestamp-only regeneration churn during validation.
- `form-app/data.js` payload, except timestamp-only publication churn during validation if `generate_registry.py` is run.
- Generated workbook `form_*` sheet policy.
- Dealer submission endpoint, payload shape, or Turnstile behavior.
- Runtime JS behavior.

## Constraints

- Preserve current runtime behavior and generated contract shape.
- No workbook source-of-truth changes.
- No new dependencies.
- No product/RPO/model-specific new logic.
- No `form_*` retirement in this pass, but do not add dependencies on `form_*`.
- Do not normalize artifact paths in this pass.
- Do not make future-model discovery workbook-owned in this pass.
- Do not remove `runtime_action`, `body_style_scope`, or GBA runtime hardcode in this pass.
- If generator validation creates timestamp-only or workbook binary churn, review it and restore unrelated generated/workbook churn before handoff unless the user explicitly approves checking it in.

## Risks

1. Weak unification risk:
   - A wrapper around `live_contract_data()` could be too shallow if described as full route unification.
   - Mitigation: name this pass accurately as the shared runtime-contract finalization seam; leave source-row assembly unification and `form_*` retirement as later passes.

2. Hidden behavior drift risk:
   - Moving finalization could accidentally alter draft-only trimming, dataset status, validation filtering, or emitted payload keys.
   - Mitigation: use strict Pass 0 baseline comparisons for all promoted inputs after generator runs.

3. Test brittleness risk:
   - Source-string tests can become brittle.
   - Mitigation: prefer behavior tests for `build_model_runtime_contract()` and keep any source-usage guard narrow and migration-specific.

4. Workbook churn risk:
   - Running Stingray generation writes `stingray_master.xlsx` through `save_workbook_safely()` even if payloads match.
   - Mitigation: inspect status after gates and restore timestamp-only/generated/workbook churn not part of the approved code pass.

5. Future `form_*` retirement risk:
   - Editing production code around sheet writes could accidentally entrench them.
   - Mitigation: isolate runtime-contract finalization from sheet writer code; do not refactor sheet emission except to avoid coupling it to runtime finalization.

## Non-goals

- No full switch of Stingray to `inspection.build_form_data_draft()`.
- No deletion or retirement of generated workbook `form_*` sheets.
- No artifact path normalization to `form-output/runtime/`.
- No workbook metadata migration.
- No model discovery refactor.
- No schema validator cleanup.
- No editor gate cleanup.
- No runtime business-rule hardcode cleanup.
- No browser/runtime UI change.

## Implementation outline

1. Add `runtime_contract.py` with `build_model_runtime_contract(config, data)`.
2. Delegate to the existing `live_contract_data()` behavior so the payload contract remains unchanged.
3. Change production output finalization to call the new shared builder.
4. Change inspection runtime artifact writing to call the new shared builder.
5. Add focused tests for the new builder and route usage.
6. Run targeted generation/parity gates.
7. Restore any validation-only generated/workbook timestamp churn not intended for the code pass.
8. Update this spec's status/results section before handoff.

## Validation plan

Before implementation:

```sh
git status --short --branch
python3 - <<'PY'
from pathlib import Path
print('excel_lock:', 'present' if Path('~$stingray_master.xlsx').exists() else 'absent')
PY
```

Implementation checks:

```sh
.venv/bin/python -m py_compile \
  scripts/generate_form.py \
  scripts/corvette_form_generator/runtime_contract.py \
  scripts/corvette_form_generator/production.py \
  scripts/corvette_form_generator/inspection.py

.venv/bin/python -m pytest \
  tests/test_runtime_contract_builder.py \
  tests/test_registry_promotion_metadata.py \
  -q
```

Promoted input parity gates:

```sh
BASE=/tmp/27vette-pass1-before
mkdir -p "$BASE"
cp form-output/stingray-form-data.json "$BASE/stingray-form-data.json"
cp form-output/inspection/grand-sport-runtime-contract.json "$BASE/grand-sport-runtime-contract.json"
cp form-output/inspection/z06-runtime-contract.json "$BASE/z06-runtime-contract.json"

.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
.venv/bin/python scripts/generate_registry.py

node scripts/compare-generated-contracts.mjs "$BASE/stingray-form-data.json" form-output/stingray-form-data.json
node scripts/compare-generated-contracts.mjs "$BASE/grand-sport-runtime-contract.json" form-output/inspection/grand-sport-runtime-contract.json
node scripts/compare-generated-contracts.mjs "$BASE/z06-runtime-contract.json" form-output/inspection/z06-runtime-contract.json
```

Targeted runtime/model gates:

```sh
node --test tests/stingray-generator-stability.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/z06-form-data-draft.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Generated artifact/worktree review:

```sh
git status --short
git diff --stat
git diff -- scripts/corvette_form_generator/production.py scripts/corvette_form_generator/inspection.py scripts/corvette_form_generator/runtime_contract.py scripts/generate_form.py tests/test_runtime_contract_builder.py docs/audit-cleanup/pass-1-unified-runtime-contract-builder-spec.md
```

If generated JSON/Markdown, `form-app/data.js`, or workbook binary changes are timestamp-only validation churn, restore them before final handoff and rerun the focused checks needed to prove retained artifacts are still valid.

## Implementation results

Implemented files:

- Added `scripts/corvette_form_generator/runtime_contract.py` with `build_model_runtime_contract(config, data)`.
- Updated `scripts/corvette_form_generator/production.py` so Stingray finalizes runtime JSON through `build_model_runtime_contract(MODEL_CONFIG, data)`.
- Updated `scripts/corvette_form_generator/inspection.py` so runtime-contract artifact writing finalizes through `build_model_runtime_contract(config, draft)`.
- Updated `scripts/generate_form.py` to pass the resolved model config into `write_runtime_contract_artifact()`.
- Added `tests/test_runtime_contract_builder.py` for the shared finalization behavior and route-usage guard.

Generated/workbook handling:

- No workbook source rows or metadata were intentionally changed.
- Grand Sport/Z06 generator/test runs produced timestamp-only generated inspection artifact churn; those generated files were restored.
- Stingray generator was rerun after the Excel lock cleared. The regenerated promoted input matched the Pass 1 before snapshot after timestamp stripping.

Gate results:

```text
.venv/bin/python -m py_compile scripts/generate_form.py scripts/corvette_form_generator/runtime_contract.py scripts/corvette_form_generator/production.py scripts/corvette_form_generator/inspection.py
PASS

.venv/bin/python -m pytest tests/test_runtime_contract_builder.py tests/test_registry_promotion_metadata.py -q
PASS: 11 passed

.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
PASS

node scripts/compare-generated-contracts.mjs <baseline>/grand-sport-runtime-contract.json form-output/inspection/grand-sport-runtime-contract.json
PASS: contracts match

node scripts/compare-generated-contracts.mjs <baseline>/z06-runtime-contract.json form-output/inspection/z06-runtime-contract.json
PASS: contracts match

node scripts/compare-generated-contracts.mjs /tmp/27vette-pass1-finish-20260621T061020Z/stingray-form-data.json form-output/stingray-form-data.json
PASS: contracts match after rerunning scripts/generate_form.py --model stingray

node --test tests/grand-sport-draft-data.test.mjs
PASS: 19 passed

node --test tests/z06-form-data-draft.test.mjs
PASS: 23 passed

node --test tests/multi-model-runtime-switching.test.mjs
PASS: 44 passed

node --test tests/stingray-generator-stability.test.mjs
FAIL: pre-existing workbook metadata expectation mismatch for Z06 order-summary sections; actual workbook data includes required_charges / Required Charges / 15 while this test's shared expected list has 11 sections.
```

Previously blocked, now complete:

- `.venv/bin/python scripts/generate_form.py --model stingray`: PASS after Excel lock cleared.
- `.venv/bin/python scripts/generate_registry.py`: PASS; registry generation output reported `stingray`, `grandSport`, and `z06` models with `STINGRAY_FORM_DATA` legacy alias.
- Full Stingray regenerated-artifact parity: PASS against `/tmp/27vette-pass1-finish-20260621T061020Z/stingray-form-data.json`.

Residual risk:

- The code path change is intentionally small and behavior-preserving; strict timestamp-ignored parity passed for all three promoted Pass 1 inputs.
- The `tests/stingray-generator-stability.test.mjs` Z06 expected-order-summary failure remains unrelated to this code change and should be handled as a separate test/workbook expectation cleanup, not hidden in this pass.
