# Fallback Retirement / Boundary-Narrowing Spec

Recommended reasoning level: high.

## Status

Approved and implemented 2026-06-17.

2026-06-17 review findings addressed before implementation:

- Missing generated `orderSummary` metadata must raise a clearly named missing-generated-data error; returning an empty list/object is not allowed because downstream helpers can synthesize malformed raw step-key sections or fail later.
- Optional regeneration comparisons must create `/tmp/before-*` snapshots before running generation.
- Source guards must cover all retired browser fallback symbols and fallback expressions, not only `orderSectionDefinitions` and `stepOrderSectionKeys`.

Implementation result:

- Browser order-summary fallback constants and fallback expressions were removed from `form-app/app.js`.
- Missing generated `orderSummary.sections` or `orderSummary.stepMap` now raises a clearly named missing-generated-data runtime error.
- `tests/multi-model-runtime-switching.test.mjs` guards the retired symbols/expressions, active model generated metadata counts, and missing-metadata failure mode.
- Python fallback constants remain, with docstrings/comments narrowed to unpromoted compatibility / promoted completeness-check semantics.
- No workbook changes or generated artifact changes were intended.

## Diagnosis

Pass E completed workbook-owned runtime metadata coverage for every promoted model, but some runtime/generator fallback surfaces remain. The remaining problem is not missing workbook data; it is boundary clarity. Promoted models should use generated workbook-owned metadata, while fallback constants should either be removed from the browser runtime or explicitly scoped to unpromoted compatibility / generator completeness checks.

Current evidence inspected:

- Active branch/status: `generator-simplification-pass1`, clean worktree at inspection time.
- `docs/persisting-audit-findings-2026-06-14.md` now recommends this as the first implementation pass after the docs status refresh.
- `docs/audit-cleanup/pass-e-runtime-metadata-inventory.md` says Pass E option (a) completed workbook-owned coverage:
  - `runtime_steps`: 14 rows each for `stingray`, `grand_sport`, and `z06`.
  - `context_section_master`: 2 rows each for `stingray`, `grand_sport`, and `z06`.
  - `order_summary_sections`: 11 rows each for `stingray`, `grand_sport`, and `z06`.
  - `step_order_summary_map`: 13 rows each for `stingray`, `grand_sport`, and `z06`.
- Current `form-app/data.js` probe confirms all active registry models emit:
  - `steps=14`
  - `orderSummary.sections=11`
  - `orderSummary.stepMap=13`
- Browser fallback surfaces remain in `form-app/app.js`:
  - `orderSectionDefinitions` at `form-app/app.js:141-153`.
  - `stepOrderSectionKeys` at `form-app/app.js:156-170`.
  - `orderSummarySections()` falls back to `orderSectionDefinitions` when `data.orderSummary?.sections` is missing at `form-app/app.js:1070-1078`.
  - `orderSummaryStepMap()` falls back to `Object.fromEntries(stepOrderSectionKeys)` at `form-app/app.js:1080-1082`.
  - `orderSectionLabels` / `orderSectionOrder` are derived only from those fallback definitions and currently have no uses outside the fallback path.
- Python fallback/base-config surfaces remain in `scripts/corvette_form_generator/model_configs.py`:
  - `STEP_ORDER`
  - `STEP_LABELS`
  - `CONTEXT_SECTIONS`
- Generator loaders already guard promoted models:
  - `runtime_metadata.load_runtime_steps()` raises for promoted models with no workbook-owned `runtime_steps` rows, but still returns `source: fallback_config` for unpromoted models.
  - `runtime_metadata.load_context_sections()` raises for promoted models with no workbook-owned `context_section_master` rows, but still returns fallback sections for unpromoted models.
  - `runtime_metadata.load_order_summary_metadata()` raises for promoted models missing `order_summary_sections` or `step_order_summary_map` rows.
- Tests already protect part of the intended boundary:
  - `tests/test_runtime_metadata_guards.py` asserts unpromoted models can use fallback rows and promoted models cannot.
  - `tests/stingray-generator-stability.test.mjs` requires promoted models to have workbook-owned runtime metadata rows.
  - `tests/grand-sport-contract-preview.test.mjs`, `tests/grand-sport-draft-data.test.mjs`, `tests/z06-contract-preview.test.mjs`, and `tests/z06-form-data-draft.test.mjs` assert Grand Sport/Z06 generated order-summary metadata.
  - `tests/stingray-form-regression.test.mjs` asserts Stingray `data.orderSummary.sections` and `data.orderSummary.stepMap` are present and drive order output.
- `README.md:155` still says promoted runtime-contract models may omit keys their contract does not use, including `orderSummary`. That is stale for active promoted models after Pass E.
- `AGENTS.md` did not show the same stale `orderSummary` fallback claim during inspection.

Root cause:

Pass E intentionally completed workbook metadata first and left Python/JavaScript fallback constants in place for a later pass. That later pass is now safe for active promoted models because the workbook rows and generated-data tests exist. The implementation should separate two cases:

1. Browser runtime for active promoted app data: should not synthesize order-summary labels/grouping from hardcoded constants.
2. Generator/model-config compatibility for unpromoted/future models and completeness validation: may still need base defaults or expected step keys, but those constants must be clearly scoped as compatibility/default inputs rather than the source of promoted runtime metadata.

Risk level: medium. This pass touches runtime JavaScript, generator metadata boundaries, tests, and README/docs. Intended customer behavior is unchanged, but removing a browser fallback can expose missing generated metadata immediately if a future registry artifact is incomplete.

Change type: mixed runtime + generator/test/docs. No workbook data change intended. No generated artifact hand edits.

## Ownership Decision

- Active promoted model runtime metadata belongs in `stingray_master.xlsx` and generated model artifacts.
- Browser runtime should render generated `data.orderSummary` metadata. It should not own or silently synthesize active-model order-summary section labels or step grouping.
- Python `STEP_ORDER`, `STEP_LABELS`, and `CONTEXT_SECTIONS` should not be deleted cold in this pass because:
  - loaders still use them as expected-key/completeness inputs,
  - `tests/test_runtime_metadata_guards.py` intentionally preserves fallback behavior for unpromoted models,
  - future inactive models may still need compatibility scaffolding before promotion.
- Python fallback/base-config constants should be narrowed by naming/docs/tests, not expanded. If implementation proves a constant is only used for active promoted runtime output, move that value into workbook rows or fail generation rather than adding another fallback.

## Recommended Scope

### Implement now

1. Retire browser order-summary fallbacks for active runtime data.
   - Remove `orderSectionDefinitions`, `orderSectionLabels`, `orderSectionOrder`, and `stepOrderSectionKeys` from `form-app/app.js` if no other use appears during implementation.
   - Change `orderSummarySections()` to return generated `data.orderSummary.sections` when present and otherwise throw a clearly named missing-generated-data error. Do not return an empty list: `sectionKeyForStep()`, `sectionLabelForKey()`, and `sectionedOrderRecap()` can otherwise synthesize raw step-key sections or fail later on missing `vehicle` / `pricing_summary` sections.
   - Change `orderSummaryStepMap()` to return generated `data.orderSummary.stepMap` when present and otherwise throw the same clearly named missing-generated-data error. Do not return an empty object.
   - Do not replace the fallback with a new hardcoded constant under another name.

2. Add a source/runtime guard that hardcoded browser order-summary fallback constants do not come back.
   - Add or extend a JS test to assert `form-app/app.js` no longer contains `orderSectionDefinitions`, `orderSectionLabels`, `orderSectionOrder`, or `stepOrderSectionKeys`.
   - Guard against fallback expressions as well, including `Object.fromEntries(stepOrderSectionKeys)` and fallback mapping from `orderSectionDefinitions`.
   - Add or preserve runtime tests that prove each active registry model has generated `orderSummary.sections` and `orderSummary.stepMap` before order-summary helpers are used.

3. Boundary-narrow Python config fallback wording.
   - Update `scripts/corvette_form_generator/model_configs.py` module comments/docstrings so `STEP_ORDER`, `STEP_LABELS`, and `CONTEXT_SECTIONS` are described as base config / unpromoted compatibility / completeness expectations, not active promoted runtime metadata ownership.
   - Update `runtime_metadata.py` docstrings or error messages if needed so loader behavior is clear: promoted models must have workbook rows; fallback is compatibility-only for unpromoted models.
   - Do not delete Python fallback constants in this pass unless implementation proves all callers can use workbook metadata for promoted and unpromoted paths without breaking `tests/test_runtime_metadata_guards.py` or future-model scaffold behavior.

4. Update stale docs.
   - `README.md`: remove or rewrite the claim that promoted runtime-contract models may omit `orderSummary`. Current active promoted models should be documented as carrying workbook-owned `orderSummary` metadata.
   - `docs/persisting-audit-findings-2026-06-14.md`: mark fallback-retirement/boundary-narrowing complete after implementation and move the next-pass recommendation to display-order guard or whichever remaining item is still first.
   - `docs/audit-cleanup/pass-e-runtime-metadata-inventory.md`: update only if implementation changes the stated fallback boundary.

### Explicitly defer

- Full deletion or redesign of Python `STEP_ORDER`, `STEP_LABELS`, and `CONTEXT_SECTIONS` if they are still needed as unpromoted compatibility/default inputs or promoted completeness-check inputs.
- Moving `section_presentation`, `context_choice_copy`, `runtime_rule_exceptions`, or variant override topology.
- Workbook row changes to runtime metadata sheets.
- Any product copy, section order, option order, rule, price, interior, dealer payload, or generated contract behavior change.

## Exact Files to Change

Expected runtime/code changes:

- `form-app/app.js`
  - Remove browser order-summary fallback constants and fallback use.
  - Keep order-summary helper behavior data-driven from `data.orderSummary`.
  - Do not change order output shape for generated active models.

- `scripts/corvette_form_generator/model_configs.py`
  - Update comments/docstrings around `STEP_ORDER`, `STEP_LABELS`, and `CONTEXT_SECTIONS` to classify them as compatibility/default inputs and promoted-model completeness expectations.
  - Avoid behavior changes unless a trivial rename/comment-only clarification is insufficient.

- `scripts/corvette_form_generator/runtime_metadata.py`
  - Optional wording/docstring updates to clarify promoted vs unpromoted fallback semantics.
  - Avoid loader behavior changes unless needed by tests; current promoted-model guards are already in place.

Expected test changes:

- `tests/stingray-form-regression.test.mjs` or `tests/multi-model-runtime-switching.test.mjs`
  - Add a source guard that `form-app/app.js` no longer contains `orderSectionDefinitions` / `stepOrderSectionKeys`.
  - Add/keep active-model checks that Stingray, Grand Sport, and Z06 generated data all carry `orderSummary.sections` and `orderSummary.stepMap`.

- `tests/test_runtime_metadata_guards.py`
  - Keep unpromoted fallback tests unless the implementation explicitly removes unpromoted compatibility and updates the future-model workflow. That broader removal is not recommended in this pass.
  - If docstrings/error messages change, update expected error text only as needed.

- Existing model tests likely to run without logic changes:
  - `tests/stingray-form-regression.test.mjs`
  - `tests/multi-model-runtime-switching.test.mjs`
  - `tests/grand-sport-contract-preview.test.mjs`
  - `tests/grand-sport-draft-data.test.mjs`
  - `tests/z06-contract-preview.test.mjs`
  - `tests/z06-form-data-draft.test.mjs`

Expected docs changes:

- `README.md`
  - Remove/rewrite stale `orderSummary` omission language for promoted runtime models.

- `docs/persisting-audit-findings-2026-06-14.md`
  - Mark this pass complete after implementation.
  - Update the recommended next pass queue.

- `docs/fallback-retirement-boundary-narrowing-spec.md`
  - Mark approved/implemented after implementation.

Generated artifacts:

- None expected if only runtime JS/comments/tests/docs change.
- If generation is run as a validation step and timestamp-only artifacts change, restore unrelated generated churn before handoff unless the implementation intentionally changes generated contracts.

## Constraints

- Preserve live customer/dealer behavior.
- No workbook writes.
- No generated artifact hand edits.
- No new dependencies.
- No model/RPO-specific runtime exceptions.
- No visual/CSS/layout change.
- No dealer endpoint, Turnstile, payload shape, or submission semantics change.
- Do not hide missing workbook data by adding another browser/Python fallback.
- Do not remove unpromoted compatibility fallback behavior unless explicitly approved as a broader future-model workflow change.
- Respect any pre-existing dirty work. Inspect dirty files before editing and avoid overwriting unrelated changes.

## Required Preflight Before Editing

1. Confirm branch/status:

```sh
git status --short --branch
```

2. Confirm active generated registry carries order-summary metadata for all promoted models:

```sh
node - <<'NODE'
const fs = require('fs');
const vm = require('vm');
global.window = {};
vm.runInThisContext(fs.readFileSync('form-app/data.js', 'utf8'));
for (const [key, entry] of Object.entries(window.CORVETTE_FORM_DATA.models)) {
  const model = entry.data;
  console.log(key, {
    steps: model.steps?.length ?? 0,
    orderSummarySections: model.orderSummary?.sections?.length ?? 0,
    orderSummaryStepMap: Object.keys(model.orderSummary?.stepMap || {}).length,
  });
}
NODE
```

Expected result for `stingray`, `grandSport`, and `z06`:

- `steps=14`
- `orderSummarySections=11`
- `orderSummaryStepMap=13`

3. Confirm no hidden uses of the browser fallback constants exist before removing them:

```sh
rg -n "orderSectionDefinitions|orderSectionLabels|orderSectionOrder|stepOrderSectionKeys|Object\.fromEntries\(stepOrderSectionKeys\)|orderSectionDefinitions\.map" form-app/app.js tests
```

4. Confirm current Python fallback boundary and tests:

```sh
rg -n "STEP_ORDER|STEP_LABELS|CONTEXT_SECTIONS|fallback_config|load_runtime_steps|load_context_sections|load_order_summary_metadata" scripts tests/test_runtime_metadata_guards.py
```

5. Stop and revise this spec if any promoted model lacks generated `orderSummary` metadata or if browser fallback constants have unanticipated non-fallback uses.

## Implementation Plan

1. Add/update tests first.
   - Add source guard for removed browser fallback constants.
   - Add or extend active registry metadata checks for all promoted models.

2. Remove browser order-summary fallback constants and fallback branches from `form-app/app.js`.
   - Keep helper names if they are useful, but make them data-only.
   - Prefer a clear missing-generated-data failure in tests/development over silent hardcoded fallback.

3. Update Python comments/docstrings to narrow fallback boundaries.
   - Keep current promoted-model guard behavior.
   - Keep unpromoted compatibility tests green unless separately approved otherwise.

4. Update README/docs.
   - Correct promoted-model `orderSummary` language.
   - Mark this spec and the persistence handoff with the implementation result.

5. Run targeted gates and review the diff.

## Validation Plan

No workbook/generator artifact change is expected. Use runtime/test/docs gates:

```sh
node --test tests/stingray-form-regression.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/z06-contract-preview.test.mjs
node --test tests/z06-form-data-draft.test.mjs
.venv/bin/python -m pytest tests/test_runtime_metadata_guards.py -q
git diff --check
```

If implementation touches generator loader behavior beyond comments/docstrings, also run:

```sh
.venv/bin/python -m pytest tests/test_model_config_metadata.py tests/test_registry_promotion_metadata.py tests/test_schema_validation_metadata.py -q
```

If implementation regenerates artifacts for comparison, run and review:

```sh
cp form-output/stingray-form-data.json /tmp/before-stingray-form-data.json
cp form-output/inspection/grand-sport-runtime-contract.json /tmp/before-grand-sport-runtime-contract.json
cp form-output/inspection/z06-runtime-contract.json /tmp/before-z06-runtime-contract.json
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
.venv/bin/python scripts/generate_registry.py
node scripts/compare-generated-contracts.mjs /tmp/before-stingray-form-data.json form-output/stingray-form-data.json
node scripts/compare-generated-contracts.mjs /tmp/before-grand-sport-runtime-contract.json form-output/inspection/grand-sport-runtime-contract.json
node scripts/compare-generated-contracts.mjs /tmp/before-z06-runtime-contract.json form-output/inspection/z06-runtime-contract.json
```

Expected result:

- Active model order-summary grouping/labels unchanged.
- Active model current-order output unchanged.
- No generated choices, rules, prices, interiors, colors, standard equipment, or dealer payload fields change.
- Browser no longer owns hardcoded order-summary fallback definitions.
- Python fallback semantics remain explicitly bounded to unpromoted compatibility / completeness checks.

Manual/browser verification:

- Not required if runtime tests pass and no generated contract changes occur.
- If runtime helper behavior changes more broadly than order-summary fallback removal, browser-smoke model switching plus order-summary/download output for Stingray, Grand Sport, and Z06.

## Risks

- Removing browser fallbacks can make incomplete generated data fail harder. That is desired for promoted models, but tests must prove current active data is complete first.
- Deleting Python constants too aggressively could break future-model/unpromoted draft workflows or promoted completeness checks. Keep that as boundary narrowing unless a separate spec approves full removal.
- README/docs can drift again if they keep broad “models may omit keys” language. Update docs with the promoted-model boundary.
- A source guard that only scans strings can be brittle; pair it with active runtime/data tests so the guard protects architecture while behavior tests protect output.

## Non-Goals

- No workbook metadata row changes.
- No generated artifact changes as a goal.
- No variant override topology migration.
- No runtime rule exception migration.
- No section/copy/order cleanup beyond order-summary fallback ownership.
- No future-model promotion.
- No dealer submission behavior changes.
- No full removal of unpromoted generator compatibility fallbacks unless separately approved.

## Handoff Requirements

The implementation handoff must report:

- What changed: runtime JS fallback removal, any Python boundary wording, tests, docs.
- What did not change: workbook, generated artifacts unless intentionally regenerated, dealer boundaries, visual behavior, active model order-summary output.
- Gate results: exact commands and pass/fail output.
- Manual verification pending or skipped with reason.
- Next step guidance: likely display-order guard pass unless this implementation exposes a more urgent metadata-boundary issue.

## Approval

Approved and implemented 2026-06-17.
