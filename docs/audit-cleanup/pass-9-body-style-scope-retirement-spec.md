# Pass 9 — Body-Style Scope Retirement Parity Spec

Status: Completed implementation on 2026-06-22.
Date: 2026-06-22
Recommended reasoning level for implementation agent: high.
Source report: `docs/audit-cleanup/pass-8-direct-rule-field-classification-report.md`.

## Goal

Retire only the direct-rule `body_style_scope` values that Pass 8 classified as OVS-derivable, and remove the one Grand Sport duplicate/stale direct-rule row pair after parity proof.

This is Candidate A from the Pass 8 report. It is a workbook/source-data cleanup plus generated-artifact refresh. It is not a runtime-semantics pass and not a `runtime_action=replace` migration pass.

## Diagnosis

Change type for this spec: docs-only.

Change type for implementation: mixed workbook/data + generated artifacts + tests. Risk level: medium.

Root cause: current `rule_mapping`, `grandSport_rule_mapping`, and `z06_rule_mapping` still carry nonblank direct-rule `body_style_scope` values for relationships where source/target OVS availability already appears to constrain the relationship to coupe or convertible. Keeping both `body_style_scope` and OVS as owners preserves duplicate scope metadata in the pipeline. Pass 8 found one Grand Sport duplicate/stale direct-rule pair with the same source/type/target/scope behavior.

Evidence inspected:

- `docs/audit-cleanup/pass-8-direct-rule-field-classification-report.md:94` lists all current `body_style_scope` classifications.
- `docs/audit-cleanup/pass-8-direct-rule-field-classification-report.md:133` defines Candidate A scope and proof requirements.
- Current read-only workbook probe confirmed scoped rows:
  - `rule_mapping`: 8 scoped rows, no duplicate scoped keys.
  - `grandSport_rule_mapping`: 9 scoped rows, duplicate key `opt_bc4_002` / `requires` / `opt_zz3_001` / `convertible` appears twice.
  - `z06_rule_mapping`: 3 scoped rows, no duplicate scoped keys.
- Runtime consumer remains `form-app/app.js:600`, where direct rules use literal `rule.body_style_scope !== state.bodyStyle` matching.
- Direct-rule `scopeMatches()` conversion remains out of scope.

## Target workbook edits if approved

Use `save_workbook_safely()` through existing workbook helpers. Do not hand-edit workbook package XML. Refuse to run if `~$stingray_master.xlsx` exists.

### `rule_mapping`

Blank `body_style_scope` only for these eight rows/rules. Do not delete rows.

| current row | rule_id | current scope | action |
|---:|---|---|---|
| 54 | `rule_opt_b6p_001_includes_opt_d3v_001` | coupe | blank `body_style_scope` |
| 56 | `rule_opt_bc4_001_includes_opt_d3v_001` | coupe | blank `body_style_scope` |
| 57 | `rule_opt_bc4_002_requires_opt_zz3_001` | convertible | blank `body_style_scope` |
| 58 | `rule_opt_bcp_001_includes_opt_d3v_001` | coupe | blank `body_style_scope` |
| 59 | `rule_opt_bcp_002_requires_opt_zz3_001` | convertible | blank `body_style_scope` |
| 60 | `rule_opt_bcs_001_includes_opt_d3v_001` | coupe | blank `body_style_scope` |
| 61 | `rule_opt_bcs_002_requires_opt_zz3_001` | convertible | blank `body_style_scope` |
| 142 | `rule_opt_bc7_001_requires_opt_zz3_001_convertible` | convertible | blank `body_style_scope` |

### `grandSport_rule_mapping`

Blank `body_style_scope` for the retained OVS-derived rows, and delete only the stale duplicate copy row after pre-change duplicate confirmation.

Recommended duplicate choice:

- Delete `gs_copy_rule_opt_bc4_002_requires_opt_zz3_001_opt_bc4_002_requires_opt_zz3_001_convertible`.
- Keep `gs_rule_opt_bc4_002_requires_opt_zz3_001_convertible` and blank its `body_style_scope`.

Reason: the deleted row has `gs_copy_` ancestry and duplicates source/type/target/scope behavior. The kept row has the model-native `gs_rule_` identifier.

| current row | rule_id | current scope | action |
|---:|---|---|---|
| 3 | `gs_rule_opt_b6p_001_includes_opt_d3v_001` | coupe | blank `body_style_scope` |
| 5 | `gs_copy_rule_opt_bc4_002_requires_opt_zz3_001_opt_bc4_002_requires_opt_zz3_001_convertible` | convertible | delete duplicate row after confirming row 95 still exists |
| 6 | `gs_rule_opt_bc4_002_includes_opt_d3v_001` | coupe | blank `body_style_scope` |
| 7 | `gs_copy_rule_opt_bc7_001_requires_opt_zz3_001_convertible_opt_bc7_001_requires_opt_zz3_001_convertible` | convertible | blank `body_style_scope` |
| 8 | `gs_copy_rule_opt_bcp_002_requires_opt_zz3_001_opt_bcp_002_requires_opt_zz3_001_convertible` | convertible | blank `body_style_scope` |
| 9 | `gs_rule_opt_bcp_002_includes_opt_d3v_001` | coupe | blank `body_style_scope` |
| 10 | `gs_copy_rule_opt_bcs_002_requires_opt_zz3_001_opt_bcs_002_requires_opt_zz3_001_convertible` | convertible | blank `body_style_scope` |
| 11 | `gs_rule_opt_bcs_002_includes_opt_d3v_001` | coupe | blank `body_style_scope` |
| 95 | `gs_rule_opt_bc4_002_requires_opt_zz3_001_convertible` | convertible | keep row, blank `body_style_scope` |

### `z06_rule_mapping`

Blank `body_style_scope` only for these three rows/rules. Do not delete rows.

| current row | rule_id | current scope | action |
|---:|---|---|---|
| 3 | `z06_rule_opt_b6p_001_includes_opt_d3v_001` | coupe | blank `body_style_scope` |
| 47 | `z06_rule_opt_bcw_001_requires_opt_zz3_001_convertible` | convertible | blank `body_style_scope` |
| 49 | `z06_rule_opt_pbc_001_requires_opt_zz3_001_convertible` | convertible | blank `body_style_scope` |

## Exact files/sheets/artifacts to change if approved

Source workbook:

- `stingray_master.xlsx`
  - `rule_mapping`
  - `grandSport_rule_mapping`
  - `z06_rule_mapping`

Generated artifacts expected to refresh:

- `form-output/runtime/stingray-runtime-contract.json`
- `form-output/runtime/grand-sport-runtime-contract.json`
- `form-output/runtime/z06-runtime-contract.json`
- `form-output/stingray-form-data.json`
- `form-output/stingray-form-data.csv`
- `form-app/data.js`

Tests to change only if current assertions explicitly lock the old scoped-row count or duplicate row:

- `tests/workbook-schema-standardization.test.mjs`
- `tests/stingray-form-regression.test.mjs`
- `tests/grand-sport-draft-data.test.mjs`
- `tests/z06-form-data-draft.test.mjs`
- `tests/multi-model-runtime-switching.test.mjs`

Docs/status closure to update after implementation:

- `docs/audit-cleanup/pass-9-body-style-scope-retirement-spec.md`
- `docs/Audit-route-map.md`

Do not change in this pass:

- `form-app/app.js`
- `scripts/corvette_form_generator/*` unless a test proves existing generation cannot preserve parity after workbook cleanup
- `runtime_action` values or rows
- `runtimeRuleExceptions`
- price rules
- dealer submission code, endpoint, payload shape, or Turnstile behavior

## Constraints

- Visual preservation: no UI/HTML/CSS/runtime-rendering changes.
- No refactor.
- No new dependencies.
- Workbook remains source of truth; fix source rows, not generated artifacts by hand.
- Use `save_workbook_safely()` and verify workbook saved on disk.
- Close/avoid Excel. Stop if `~$stingray_master.xlsx` exists.
- Do not normalize blank direct-rule scopes to `*`.
- Do not change direct-rule matching to `scopeMatches()`.
- Do not delete `body_style_scope` column.
- Do not trim generated `rules.body_style_scope` payload field.
- Do not touch `runtime_action=replace` behavior.
- Do not bundle Candidate B/C/D/E from Pass 8.

## Implementation plan completed

1. Preflight.

   ```sh
   cd /Users/seandm/Projects/27vette
   git status --short --branch
   test ! -e './~$stingray_master.xlsx'
   .venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
   ```

2. Snapshot current generated contracts before workbook edit.

   ```sh
   mkdir -p /tmp/27vette-pass9-before
   cp form-output/runtime/stingray-runtime-contract.json /tmp/27vette-pass9-before/
   cp form-output/runtime/grand-sport-runtime-contract.json /tmp/27vette-pass9-before/
   cp form-output/runtime/z06-runtime-contract.json /tmp/27vette-pass9-before/
   cp form-app/data.js /tmp/27vette-pass9-before/data.js
   ```

3. Read-only confirm candidate rows still match this spec.

   - Assert all listed rule IDs exist in expected sheets.
   - Assert `source_id`, `rule_type`, and `target_id` for every listed row still match this spec before editing.
   - Assert their current `body_style_scope` values still match expected values.
   - Assert Grand Sport duplicate key exists exactly twice before delete:
     - source `opt_bc4_002`
     - `rule_type=requires`
     - target `opt_zz3_001`
     - `body_style_scope=convertible`

4. Apply workbook edit through safe-save helper.

   - Blank listed `body_style_scope` values.
   - Delete only `gs_copy_rule_opt_bc4_002_requires_opt_zz3_001_opt_bc4_002_requires_opt_zz3_001_convertible` from `grandSport_rule_mapping`.
   - Preserve table refs and unrelated row order/values.
   - Use a temp/in-session script or existing workbook helpers; do not commit a one-off apply script unless needed for review, and delete it before handoff if created.

5. Verify workbook on disk.

   - Reopen with `openpyxl` read-only.
   - Assert listed retained rule IDs now have blank `body_style_scope`.
   - Assert deleted Grand Sport copy row is absent.
   - Assert kept Grand Sport row `gs_rule_opt_bc4_002_requires_opt_zz3_001_convertible` remains present.
   - Assert no `runtime_action=replace` values changed.

6. Regenerate active models and registry.

   ```sh
   .venv/bin/python scripts/generate_form.py --model stingray
   .venv/bin/python scripts/generate_form.py --model grand_sport
   .venv/bin/python scripts/generate_form.py --model z06
   .venv/bin/python scripts/generate_registry.py
   ```

7. Compare generated contracts.

   - For Stingray and Z06: allow only removed/blank `body_style_scope` field values for targeted rule IDs plus timestamp churn.
   - For Grand Sport: allow only targeted `body_style_scope` value removals, one fewer generated direct rule for the deleted duplicate if generation emits the row today, and timestamp churn.
   - Use `node scripts/compare-generated-contracts.mjs` for strict checks where no count/key change is expected; use a focused Node diff for approved row-field/count deltas.

8. Run targeted gates.

   ```sh
   .venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
   node --test tests/stingray-form-regression.test.mjs
   node --test tests/grand-sport-contract-preview.test.mjs
   node --test tests/grand-sport-draft-data.test.mjs
   node --test tests/z06-contract-preview.test.mjs
   node --test tests/z06-form-data-draft.test.mjs
   node --test tests/multi-model-runtime-switching.test.mjs
   ```

9. Review diff.

   - Confirm workbook diff is limited to approved source rows.
   - Confirm generated artifacts show only approved direct-rule scope/duplicate changes.
   - Confirm `form-app/app.js` unchanged.
   - Confirm no `runtime_action=replace` rows changed.

10. Close spec/status docs.

   - Update this spec to implemented/completed with date, files/sheets/artifacts changed, gates run, residual risks, and next pass.
   - Update `docs/Audit-route-map.md` so Candidate A no longer appears pending.

## Expected behavior impact

Intended customer-facing behavior impact: none.

Why no behavior change is expected:

- Targeted scoped relationships are already constrained by source/target OVS availability.
- Direct rules still check source and target current-variant availability in `ruleAppliesToCurrentVariant()`.
- Runtime matching code remains unchanged.

Approved generated contract impact:

- Targeted rule objects may emit blank/omitted `body_style_scope` instead of `coupe`/`convertible`.
- Grand Sport may emit one fewer direct rule if the duplicate copy row currently emits.
- Timestamp fields may change.

Any broader delta is a stop condition.

## Risks

- OVS availability may not be a perfect substitute for explicit direct-rule scope if target auto-only/display behavior bypasses expected availability checks.
- Deleting the wrong Grand Sport BC4/ZZ3 duplicate could preserve stale copy ancestry instead of model-native row ID.
- Tests may assert old rule counts or rule IDs; update only assertions that lock intentionally retired duplicate/scope metadata.
- Generated artifact timestamp churn can hide unintended deltas unless contract diff is focused.
- Workbook table refs can drift if row deletion is not done through safe workbook helper.

## Non-goals

- No `runtime_action=replace` cleanup.
- No replacement-rule migration to exclusive groups/default-selection rules.
- No direct-rule `scopeMatches()` runtime change.
- No `body_style_scope` column deletion.
- No generated payload schema trim.
- No optional audit/report artifact refresh unless a failing required test proves it is needed.
- No ZR1/ZR1X cleanup.
- No price-rule semantic cleanup.

## Validation plan

Pre-edit:

```sh
git status --short --branch
test ! -e './~$stingray_master.xlsx'
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
```

Post-workbook save:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Generation:

```sh
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
.venv/bin/python scripts/generate_registry.py
```

Runtime/model tests:

```sh
node --test tests/stingray-form-regression.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/z06-contract-preview.test.mjs
node --test tests/z06-form-data-draft.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Diff/status checks:

```sh
git diff --check
git status --short
```

## Completion summary

Completed on 2026-06-22.

Workbook source changes:

- `stingray_master.xlsx` / `rule_mapping`: blanked `body_style_scope` on the eight approved OVS-derived rows.
- `stingray_master.xlsx` / `grandSport_rule_mapping`: blanked `body_style_scope` on the eight retained approved OVS-derived rows.
- `stingray_master.xlsx` / `grandSport_rule_mapping`: deleted duplicate copy row `gs_copy_rule_opt_bc4_002_requires_opt_zz3_001_opt_bc4_002_requires_opt_zz3_001_convertible` and kept `gs_rule_opt_bc4_002_requires_opt_zz3_001_convertible`.
- `stingray_master.xlsx` / `z06_rule_mapping`: blanked `body_style_scope` on the three approved OVS-derived rows.
- Workbook backup created by safe-save: `backups/stingray_master-20260622-120755.xlsx`.

Generated artifacts refreshed:

- `form-output/runtime/stingray-runtime-contract.json`
- `form-output/runtime/grand-sport-runtime-contract.json`
- `form-output/runtime/z06-runtime-contract.json`
- `form-output/stingray-form-data.json`
- `form-app/data.js`

Tests updated:

- `tests/stingray-form-regression.test.mjs`: BC7/ZZ3 guard now asserts blank direct-rule scope plus convertible-only ZZ3 OVS availability.
- `tests/grand-sport-draft-data.test.mjs`: engine-cover include rule expectations now assert blank direct-rule scope.

Approved generated deltas:

- Stingray: 8 targeted rules changed from scoped direct rules to blank `body_style_scope`.
- Grand Sport: 8 targeted retained rules changed from scoped direct rules to blank `body_style_scope`; 1 duplicate direct rule removed; validation message count changed from 122 to 121 active compatibility rules.
- Z06: 3 targeted rules changed from scoped direct rules to blank `body_style_scope`.

Changed behavior: intended customer-facing behavior unchanged. Runtime direct-rule matching code unchanged; source/target OVS availability now owns the retired body-style constraints.

Validation results:

- `.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx` — passed before and after workbook write.
- Strong row-identity preflight — passed for every listed row (`rule_id`, `source_id`, `rule_type`, `target_id`, `body_style_scope`).
- On-disk workbook verification — passed; scoped row count is now zero in all three rule sheets, Grand Sport rule count is 121, and all `runtime_action=replace` counts were preserved.
- `scripts/generate_form.py --model stingray` — passed, 144 rules, 0 validation errors.
- `scripts/generate_form.py --model grand_sport` — passed, 121 draft rules, 0 validation errors.
- `scripts/generate_form.py --model z06` — passed, 73 rules, 0 validation errors.
- `scripts/generate_registry.py` — passed, models `stingray`, `grandSport`, `z06`.
- Focused runtime-contract delta script — passed with only approved rule/scope/count deltas.
- `.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx` — passed.
- `node --test tests/stingray-form-regression.test.mjs` — passed.
- `node --test tests/grand-sport-contract-preview.test.mjs` — passed.
- `node --test tests/grand-sport-draft-data.test.mjs` — passed.
- `node --test tests/z06-contract-preview.test.mjs` — passed.
- `node --test tests/z06-form-data-draft.test.mjs` — passed.
- `node --test tests/multi-model-runtime-switching.test.mjs` — passed.
- `git diff --check` — passed.

Residual risks:

- No browser smoke was run; Node runtime/model gates covered generated behavior and dealer payload boundaries.
- `body_style_scope` column and generated payload field still exist for future direct-rule scope semantics; only current active source values were retired.

Recommended next pass: Candidate B from the Pass 8 report — a narrow Stingray spoiler replacement ownership pass for 5ZU/5ZZ/TVS and the 5ZW/ZF1 product-decision edges. Keep Grand Sport/Z06 replacement rows and direct-rule `scopeMatches()` semantics separate.

## Historical approval prompt

Pass 9 / Candidate A implementation was approved on 2026-06-22, with one tightening: implementation preflight should assert `source_id`, `rule_type`, and `target_id` for every listed row, not only the Grand Sport duplicate.

Approval authorized only:

- blanking approved OVS-derived `body_style_scope` cells;
- deleting the single Grand Sport `gs_copy_...BC4...ZZ3...convertible` duplicate row if preflight still confirms the duplicate pair;
- regenerating active model runtime artifacts and registry;
- updating tests only for intentional scope/duplicate deltas;
- closing this spec and route-map status.

Approval did not authorize runtime `scopeMatches()` changes, `runtime_action=replace` migration, broader rule cleanup, column deletion, generated payload schema trimming, or dealer submission changes.
