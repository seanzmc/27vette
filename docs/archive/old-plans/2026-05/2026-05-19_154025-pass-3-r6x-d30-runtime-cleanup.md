# Pass 3 R6X/D30 Runtime Cleanup Spec

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task after Sean approves it. Fresh subagent per task, then spec compliance review, then code quality review.

**Goal:** Remove the obsolete runtime coupling where D30 changes R6X pricing, and prove R6X and D30 only auto-add independently from their own generated/workbook-authored conditions.

**Architecture:** This is a narrow behavior/test pass. Pass 1 added workbook metadata sheets and Pass 2 added optional metadata loaders, but neither is wired into runtime/generator behavior yet. Pass 3 should not wire the new metadata substrate into generators. It should remove the old R6X/D30 runtime patch and update regression tests to reflect the revised business rule: R6X and D30 do not affect each other's compatibility or price.

**Tech Stack:** Static browser runtime in `form-app/app.js`, generated app data in `form-app/data.js`, Node test runner in `tests/*.test.mjs`, workbook/generator validation via `.venv/bin/python`.

---

## Diagnosis

Root cause:
- `form-app/app.js` currently contains an explicit runtime special case:
  - `interiorComponentPrice(component, autoAdded)` returns `0` when `component.rpo === "R6X" && autoAdded.has("opt_d30_001")`.
- That special case encodes an old business rule/patch: D30 zeroes the R6X interior component when D30 is auto-added.
- Sean clarified this old rule no longer applies. R6X and D30 should not interact with each other at all.

Current behavior evidence:
- `form-app/app.js:737-739` contains the R6X/D30 coupling.
- `tests/stingray-form-regression.test.mjs:1376-1400` currently expects a D30-triggered R6X component to show at `$0`.
- `tests/stingray-form-regression.test.mjs:1896-1910` already asserts `optionPrice("opt_r6x_001")` remains `995` when D30 is present, but does not cover the interior component line-item price path.
- `tests/stingray-form-regression.test.mjs:1863-1879` already asserts R6X is auto-only, D30 is visible/disabled, and D30 remains available to color override auto-add rules.

Risk level:
- Medium-high behavior risk because this affects customer-facing order totals, compact order output, plain text order summaries, and dealer payload/order export line items.
- Narrow implementation risk if constrained to `interiorComponentPrice()` and regression tests.

Change type:
- Behavior + tests only.
- No workbook source-data edits.
- No generator integration.
- No generated data contract shape change.

---

## Approved Business Rule Revision

R6X and D30 should not interact with each other.

Required interpretation:
- R6X may still be conditionally auto-added by R6X interior selection through existing generated include rules.
- D30 may still be conditionally auto-added by its own color/interior override condition through existing generated `colorOverrides` logic.
- D30 must not change R6X price.
- D30 must not require, exclude, suppress, replace, or otherwise alter R6X.
- R6X must not require, exclude, suppress, replace, or otherwise alter D30.
- Do not add `component_price_rules` rows for D30 -> R6X.
- Do not add runtime exceptions between `opt_d30_001` and `opt_r6x_001`.
- Do not add any hardcoded RPO/model-specific replacement for this pair.

---

## Exact Files Likely to Change

Modify:
- `form-app/app.js`
- `tests/stingray-form-regression.test.mjs`

Do not modify in this pass:
- `stingray_master.xlsx`
- `scripts/generate_stingray_form.py`
- `scripts/generate_grand_sport_form.py`
- `scripts/corvette_form_generator/runtime_metadata.py`
- `scripts/migrations/add_workbook_metadata_sheets.py`
- `form-output/**`
- `form-app/data.js`, except if a validation generator run changes timestamp output; revert timestamp-only generated diffs before final handoff.
- Dealer submission endpoint, payload shape, or Turnstile behavior.

Generated artifacts:
- None should be intentionally changed by this pass.
- Running generators for validation may rewrite timestamp fields. Revert timestamp-only generated diffs after validation unless a real source-data change is intentionally approved.

---

## Constraints to Preserve

- Visual preservation: no styling, markup, layout, navigation, or card rendering changes.
- No refactor: do not restructure line item generation, summary/export code, or rule evaluation beyond removing the obsolete R6X/D30 price branch.
- No new dependencies.
- Workbook source-of-truth rules:
  - Do not solve this by adding new runtime business logic.
  - Because the revised rule is “no interaction,” the correct runtime change is deletion of obsolete coupling, not a new workbook row.
- No generated `form_*` workbook sheet edits.
- No dealer submission endpoint, payload shape, or Turnstile behavior changes.
- Keep the pass small and reversible.

---

## Non-goals

- Do not migrate FE1/FE2/Z51, NGA/NWI, GBA/ZYC, or default-selection hardcodes in this pass.
- Do not wire `runtime_metadata.py` into the Stingray or Grand Sport generators.
- Do not populate `component_price_rules`, `runtime_rule_exceptions`, or `default_selection_rules`.
- Do not change how D30 color override rows are generated.
- Do not change R6X interior component generation or PriceRef pricing.
- Do not change Grand Sport draft/runtime behavior unless tests prove the shared runtime behavior is naturally affected and still correct.

---

## Proposed Approach

1. Update the regression test first to encode the new rule.
2. Run the targeted test and confirm it fails against the current runtime branch.
3. Remove the obsolete R6X/D30 price waiver from `form-app/app.js`.
4. Add/adjust assertions proving:
   - D30 auto-add still triggers from its own color/interior condition.
   - R6X component line item keeps normal PriceRef-derived price when D30 is auto-added.
   - No generated option rules or price rules encode a direct R6X/D30 interaction.
   - The app source no longer contains the hardcoded `component.rpo === "R6X" && autoAdded.has("opt_d30_001")` branch.
5. Run targeted and relevant broader validation gates.

---

## Step-by-step Plan

### Task 1: Write failing tests for the revised R6X/D30 rule

**Objective:** Encode the new business rule before changing runtime behavior.

**Files:**
- Modify: `tests/stingray-form-regression.test.mjs`

**Steps:**
1. Rename/update the existing test around `tests/stingray-form-regression.test.mjs:1376`.
   - Old intent: `D30 only zeroes the R6X component`.
   - New intent: `R6X component order output uses PriceRef pricing and D30 does not alter it`.
2. Keep the baseline assertions:
   - `3LT_R6X_AH2_HUU` shows R6X at `$995`.
   - `3LT_R6X_AE4_HUU` shows R6X at `$1,590`.
3. Change the D30-context assertion from `price === 0` to the correct PriceRef-derived value for `3LT_R6X_AH2_HZP_N26`.
   - Expected R6X component price should remain the R6X component price, not a D30-adjusted zero.
   - If unsure, inspect `data.interiors` for `3LT_R6X_AH2_HZP_N26` and its `interior_components` in the test fixture before finalizing the exact number.
4. Keep/assert `d30Runtime.computeAutoAdded().has("opt_d30_001") === true` to prove D30 still auto-adds independently.
5. Strengthen the later generated contract test around `tests/stingray-form-regression.test.mjs:1863` or `:1896`:
   - Assert no generated `data.priceRules` row has `condition_option_id === "opt_d30_001" && target_option_id === "opt_r6x_001"`.
   - Assert no generated `data.rules` row directly connects `opt_d30_001` and `opt_r6x_001` in either direction.
   - Assert `appSource` does not match the obsolete hardcoded branch, e.g. `/component\.rpo\s*===\s*["']R6X["'][\s\S]*autoAdded\.has\(["']opt_d30_001["']\)/`.

**Run to verify failure:**
```sh
node --test tests/stingray-form-regression.test.mjs
```

Expected before runtime fix:
- FAIL in the updated D30/R6X line-item test because `interiorComponentPrice()` still returns `0` for the R6X component when D30 is auto-added.

---

### Task 2: Remove obsolete R6X/D30 runtime price coupling

**Objective:** Make R6X component pricing independent of D30.

**Files:**
- Modify: `form-app/app.js`

**Steps:**
1. Replace:
```js
function interiorComponentPrice(component, autoAdded) {
  if (component.rpo === "R6X" && autoAdded.has("opt_d30_001")) return 0;
  return Number(component.price || 0);
}
```

With:
```js
function interiorComponentPrice(component) {
  return Number(component.price || 0);
}
```

2. Update the call site if desired for clarity:
```js
...components.map((component) => lineItemFromInteriorComponent(interior, component, autoAdded)),
```
may remain unchanged because `lineItemFromInteriorComponent()` still accepts `autoAdded` for compatibility, but the implementation no longer uses it.

3. Optional cleanup within this narrow scope:
   - If no other call needs `autoAdded` for component pricing, simplify only the local helper signature:
```js
function interiorComponentPrice(component) { ... }
function lineItemFromInteriorComponent(interior, component) { ... }
...components.map((component) => lineItemFromInteriorComponent(interior, component)),
```
   - Do not refactor broader line item generation.

**Run to verify pass:**
```sh
node --test tests/stingray-form-regression.test.mjs
```

Expected after runtime fix:
- PASS.

---

### Task 3: Verify no generated R6X/D30 interaction was introduced

**Objective:** Confirm the pass removed coupling instead of moving it somewhere else.

**Files:**
- Read-only checks against:
  - `form-app/app.js`
  - `form-app/data.js`
  - `form-output/stingray-form-data.json`
  - `tests/stingray-form-regression.test.mjs`

**Steps:**
1. Search source for direct runtime coupling:
```sh
rg -n 'R6X|D30|opt_r6x_001|opt_d30_001|componentPriceRules|component\.rpo' form-app/app.js tests/stingray-form-regression.test.mjs
```
2. Ensure any remaining `R6X`/`D30` mentions in tests are assertions about independent auto-add/pricing, not compatibility/price override logic.
3. Confirm no workbook/generator changes were made for this behavior.

Expected:
- `form-app/app.js` has no special branch linking `R6X` to `opt_d30_001`.
- Tests document that R6X and D30 do not interact.

---

### Task 4: Run validation gates

**Objective:** Prove runtime behavior and generated-data contracts still pass.

**Targeted gates:**
```sh
node --test tests/stingray-form-regression.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

**Workbook/package safety gate:**
```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
```

**Recommended broader gates because this is customer-facing runtime/order-output behavior:**
```sh
node --test tests/stingray-generator-stability.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/grand-sport-rule-audit.test.mjs
```

**Only if generated artifacts need regeneration for validation parity:**
```sh
.venv/bin/python scripts/generate_stingray_form.py
.venv/bin/python scripts/generate_grand_sport_form.py
```
Then inspect and revert timestamp-only generated diffs unless a real generated-data change is approved.

---

## Expected Behavior After Pass 3

- R6X auto-add logic remains controlled by generated include rules from selected R6X interiors.
- D30 auto-add logic remains controlled by `data.colorOverrides` for selected color/interior context.
- D30 appearing in `computeAutoAdded()` does not change R6X component price.
- Compact order output and plain text/dealer payload line items show the normal R6X component price for R6X interiors even when D30 is auto-added.
- No direct generated `rules`, `priceRules`, runtime exceptions, or component price rules connect `opt_d30_001` and `opt_r6x_001`.

---

## Rollback Plan

If the change causes unexpected order-output regressions:
1. Revert the `form-app/app.js` change.
2. Revert the related test expectation changes.
3. Do not touch workbook metadata sheets or loaders from Pass 1/2.
4. If generated artifacts were rewritten during validation, restore/revert generated timestamp-only diffs.
5. Re-run:
```sh
node --test tests/stingray-form-regression.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

---

## Risks and Tradeoffs

Risks:
- Customer-facing totals may increase for D30-triggering R6X interiors because the old runtime zeroing is removed.
- Existing tests may have encoded the old patch in multiple places; update only the tests directly tied to R6X/D30 interaction.
- If the old zeroing behavior was compensating for a source-data pricing issue, this pass will expose that issue rather than hiding it. That is acceptable under workbook source-of-truth rules, but should be called out if totals look surprising.

Tradeoffs:
- This pass deliberately removes one hardcoded runtime patch without migrating broader runtime hardcodes. That keeps risk bounded.
- The new Pass 1/2 metadata substrate remains unused in this pass. That is intentional because the revised rule is deletion/no interaction, not a new workbook-authored interaction.

Open questions:
- Confirm the exact expected R6X component price for `3LT_R6X_AH2_HZP_N26` from generated `data.interiors` before writing the final assertion.
- Confirm whether Sean wants a separate later pass for FE1/FE2/Z51, NGA/NWI, GBA/ZYC, and workbook-owned defaults from the original Phase 3.

---

## Final Handoff Requirements

Implementation handoff must report:
- What changed:
  - `form-app/app.js`
  - `tests/stingray-form-regression.test.mjs`
  - any generated artifacts if accidentally changed and whether reverted
- What did not change:
  - workbook sheets
  - metadata loader wiring
  - generated data schema
  - dealer submission endpoint/payload/Turnstile
- Gate results:
  - targeted Node tests
  - workbook package validation
  - broader tests or `not run` with reason
- Manual verification still pending:
  - browser smoke test for R6X interior + D30-triggering color order summary/export
- Residual risks and follow-up work.

---

## Approval Question

Approve Pass 3 as scoped above: remove only the obsolete R6X/D30 runtime price coupling and update tests so R6X and D30 auto-add independently with no mutual compatibility or pricing interaction?
