# Spec: Phase 3 — workbook-author default-selected display derivation

Status: implemented 2026-06-30. Validation completed with one unrelated pre-existing gate failure noted below.

Parent: `docs/asset-media-drift-remediation-spec-2026-06-30.md` (Section 4, "Phase 3"). Phase 1 and Phase 2 are complete. This spec is the standalone implementation plan for removing the Python hardcoded default-selected display derivation allowlist without changing current promoted-model customer behavior.

## 0. Re-validation at time of writing this phase spec

Repo state after Phase 2 commit: `git status --short --branch` shows `phase-2-shared-assembly-extraction...origin/phase-2-shared-assembly-extraction` with no dirty files. This spec is written on that branch.

Current source evidence:

- `scripts/corvette_form_generator/runtime_metadata.py:20-26` defines `_DEFAULT_SELECTED_DISPLAY_RULE_IDS_BY_MODEL`, currently:
  - `stingray`: `default_bc7`
  - `grand_sport`: `gs_default_bc7_coupe`, `gs_default_nga_unless_nwi`
  - no `z06` entry.
- `runtime_metadata.py:302-340` applies that map inside `derived_default_selected_display_behavior(...)`. The function otherwise already uses workbook-authored `default_selection_rules`, active single-selection exclusive groups, choice status/selectability/active state, and body/trim/variant scopes.
- `production.py:181` loads `default_selection_rules`; `production.py:384-387` calls `derived_default_selected_display_behavior(...)` only when a choice does not already have `display_behavior`.
- `inspection.py:655` and `inspection.py:978` load `default_selection_rules`; `inspection.py:832-835` calls the same derivation for preview/draft choices only when no `display_behavior` is already present.
- `default_selection_rules` workbook headers currently are `model_key`, `rule_id`, `target_option_id`, `condition_type`, `condition_id`, `body_style_scope`, `trim_level_scope`, `variant_scope`, `priority`, `active`, `notes`. There is no workbook-authored field that says a default-selection rule should also emit `display_behavior=default_selected`.
- Active `default_selection_rules` row inventory from read-only `openpyxl`:
  - Stingray: `default_fe1`, `default_nga`, `default_719`, `default_bc7`.
  - Grand Sport: `gs_default_j6d_with_j57`, `gs_default_nga_unless_nwi`, `gs_default_bc7_coupe`, `gs_default_t0e`.
  - Z06: `z06_default_719`, `z06_default_efr`, `z06_default_t0e`, `z06_default_r8e_tax`.
  - Future unpromoted model rows also exist for `zr1` and `zr1x`; they are not generated/promoted in this phase.
- Current generated runtime contracts show these `display_behavior=default_selected` choices:
  - Stingray: `opt_719_001`/719 and `opt_efr_001`/EFR come directly from `stingray_options.display_behavior`; `opt_bc7_001`/BC7 is derived through the Python allowlist. `default_nga` is intentionally not derived.
  - Grand Sport: `opt_719_001`/719, `opt_efr_001`/EFR, `opt_eyt_001`/EYT, `opt_jx6_001`/JX6, and `opt_t0e_001`/T0E come directly from `grandSport_options.display_behavior`; `opt_bc7_001`/BC7 and `opt_nga_001`/NGA are derived through the Python allowlist.
  - Z06: 66 default-selected choices across 11 option ids come directly from `z06_options.display_behavior`; none are derived from `_DEFAULT_SELECTED_DISPLAY_RULE_IDS_BY_MODEL`. `z06_default_r8e_tax` emits as a workbook default-selection rule but current Z06 R8E choices intentionally have blank `display_behavior`.
- `form-app/app.js:1363-1384` consumes `choice.display_behavior === "default_selected"` generically in `addWorkbookDefaultChoices(...)`. Runtime JavaScript does not inspect Python rule-id allowlists.

Conclusion: the hardcoded Python map is a real second source of truth, but current promoted-model choice behavior can be preserved by moving only the three currently allowlisted derivation approvals onto their owning `default_selection_rules` workbook rows. Z06 should not get newly derived default-selected display behavior in this pass; its existing option-row-authored `display_behavior=default_selected` choices remain unchanged, and R8E remains blank unless separately approved.

## 1. Diagnosis

The workbook owns default-selection behavior through `default_selection_rules`, and option/source rows already own many direct `display_behavior=default_selected` facts. However, three rule-derived display defaults still depend on `_DEFAULT_SELECTED_DISPLAY_RULE_IDS_BY_MODEL` in Python. That map is not visible to workbook authors and must be hand-edited for any new model or new rule-derived default display behavior.

Risk level: medium. The current runtime behavior is working, but the authority split is the same drift pattern as Phase 2 at smaller blast radius: one workbook rule can be present and active while a hidden Python map silently decides whether it also gets display metadata.

Change type: workbook schema/data + generator metadata loading + tests. Runtime JavaScript should not change.

## 2. Exact files/sheets/artifacts expected to change

1. `stingray_master.xlsx`
   - Add a `display_behavior` column to the existing `default_selection_rules` sheet.
   - Populate exactly these active rows with `default_selected`:
     - `stingray` / `default_bc7`
     - `grand_sport` / `gs_default_bc7_coupe`
     - `grand_sport` / `gs_default_nga_unless_nwi`
   - Leave all other existing active rows blank, including:
     - Stingray `default_fe1`, `default_nga`, `default_719`
     - Grand Sport `gs_default_j6d_with_j57`, `gs_default_t0e`
     - Z06 `z06_default_719`, `z06_default_efr`, `z06_default_t0e`, `z06_default_r8e_tax`
     - future `zr1`/`zr1x` rows.
   - This is a workbook authoring signal, not a product-behavior expansion.

2. `scripts/corvette_form_generator/runtime_metadata.py`
   - Remove `_DEFAULT_SELECTED_DISPLAY_RULE_IDS_BY_MODEL` entirely.
   - Add a pinned workbook-owned loader, `load_default_selection_display_rules(wb, model_key)`, near `load_default_selection_rules(...)`.
   - `load_default_selection_rules(wb, model_key)` must continue returning the emitted runtime/default-selection rule contract without the internal `display_behavior` authoring column, so generated `defaultSelectionRules` payload shape does not drift solely because this authoring column exists.
   - `load_default_selection_display_rules(wb, model_key)` reads the same `default_selection_rules` sheet, keeps rows whose cleaned `display_behavior` is `default_selected`, and returns the rule fields needed by `derived_default_selected_display_behavior(...)`.
   - `derived_default_selected_display_behavior(...)` must gate on `rule.get("display_behavior") == "default_selected"` from the workbook-loaded display-rule rows, not on any Python model/rule-id allowlist. Preserve the existing non-allowlist guards: standard status, selectable/active true, active single-selection exclusive-group membership, target option id match, condition type in `{always, unless_selected_rpo}`, and body/trim/variant scope checks.

3. `scripts/corvette_form_generator/production.py`
   - Load both `default_selection_rules = load_default_selection_rules(...)` for emitted runtime contract data and `default_selection_display_rules = load_default_selection_display_rules(...)` for derivation.
   - Pass `default_selection_display_rules` into `derived_default_selected_display_behavior(...)`.
   - Do not change section/status/display-behavior logic beyond this substitution.

4. `scripts/corvette_form_generator/inspection.py`
   - Same split as `production.py`: emitted `default_selection_rules` remains payload data; `default_selection_display_rules` feeds derivation.
   - Preserve the existing rule/preview/draft flow and do not change option-row-authored `display_behavior` handling.

5. `tests/test_runtime_metadata_guards.py`
   - Add focused unit tests for `load_default_selection_rules(...)`, `load_default_selection_display_rules(...)`, and `derived_default_selected_display_behavior(...)` using an in-memory workbook.
   - Required assertions:
     - `load_default_selection_rules(...)` strips the workbook-only `display_behavior` column from emitted rows.
     - `load_default_selection_display_rules(...)` returns only active rows with `display_behavior=default_selected` for the requested model/global scope.
     - `derived_default_selected_display_behavior(...)` derives from a workbook-flagged row without a Python allowlist.
     - A matching default-selection row without `display_behavior=default_selected` does not derive display metadata.
     - No `_DEFAULT_SELECTED_DISPLAY_RULE_IDS_BY_MODEL` symbol remains in `runtime_metadata.py`.

6. Existing Node tests to update only if expectations need to become explicit, not for broad count churn:
   - `tests/stingray-generator-stability.test.mjs` already checks Stingray BC7 derived behavior and Stingray NGA not-derived behavior.
   - `tests/grand-sport-draft-data.test.mjs` already checks Grand Sport BC7 and NGA derived behavior, plus other option-row defaults.
   - `tests/z06-form-data-draft.test.mjs` already checks Z06 option-row defaults and R8E blank `display_behavior`.
   - `tests/multi-model-runtime-switching.test.mjs` already checks runtime seeding/reconciliation from generated `display_behavior=default_selected`.
   - Prefer adding small workbook-column assertions only if the Python tests do not sufficiently guard the source-of-truth move.

7. `docs/asset-media-drift/phase-3-default-selected-display-authoring.md`
   - Include this spec in the implementation diff and update it to `implemented` with validation evidence before final handoff.

8. Generated artifacts expected during validation only:
   - `form-output/runtime/stingray-runtime-contract.json`
   - `form-output/runtime/grand-sport-runtime-contract.json`
   - `form-output/runtime/z06-runtime-contract.json`
   - `form-output/stingray-form-data.json`
   - `form-output/stingray-form-data.csv`
   - `form-app/data.js`
   These should be regenerated and compared, then restored if the only diffs are generated timestamps. Final checked-in generated artifact diffs are not expected for this parity-preserving pass.

## 3. Source-of-truth decision

Workbook source rows own both default-selection behavior and the decision that a default-selection rule should emit `display_behavior=default_selected`. The new `default_selection_rules.display_behavior` column is the workbook-authored presentation intent for rule-derived defaults.

Generator code owns only generic interpretation:

- emitted `defaultSelectionRules` remains the existing runtime/default-selection contract;
- display derivation reads the workbook-authored display metadata from the same source rows;
- Python no longer owns a model/rule-id allowlist.

Runtime JavaScript stays unchanged and continues consuming generated `choice.display_behavior` generically.

## 4. Companion-file impact check

- `form-output/runtime/stingray-runtime-contract.json`, `form-output/runtime/grand-sport-runtime-contract.json`, `form-output/runtime/z06-runtime-contract.json` — must be timestamp-normalized identical before/after. This proves the source-of-truth move did not change current promoted-model customer behavior.
- `form-output/stingray-form-data.json` — must be timestamp-normalized identical before/after using `scripts/compare-generated-contracts.mjs` or an equivalent generated-timestamp-normalized JSON comparator.
- `form-output/stingray-form-data.csv` — must be byte-identical before/after.
- `form-app/data.js` — regenerate only after parity proof and restore timestamp-only churn before final handoff. No final `form-app/data.js` diff expected.
- `scripts/corvette_form_generator/model_configs.py` — inspect; no change expected. Model config should not gain a replacement allowlist.
- `form-app/app.js` — inspect; no change expected. Runtime already consumes choice-level `display_behavior` generically.
- `tests/stingray-generator-stability.test.mjs`, `tests/grand-sport-draft-data.test.mjs`, `tests/z06-form-data-draft.test.mjs`, `tests/multi-model-runtime-switching.test.mjs` — run unmodified unless a focused workbook-column assertion is needed; these are the runtime/generator behavior net for current defaults.
- `tests/test_runtime_metadata_guards.py` — update with focused Python coverage for the new workbook-owned loader and no-Python-allowlist guard.
- `tests/workbook-schema-standardization.test.mjs` / `scripts/validate_workbook_schema.py` — inspect/run after workbook schema edit; update only if they intentionally pin the old `default_selection_rules` header shape.
- README/AGENTS.md — not applicable; this does not change generator invocation, runtime workflow, dealer submission, or standing operating policy.

## 5. Constraints

- Excel must be closed and no `~$stingray_master.xlsx` lock file may exist before writing `stingray_master.xlsx`.
- Workbook writes must use the repo safe-save path (`save_workbook_safely()` or an existing approved workbook-write helper that uses it), then verify the saved workbook on disk by reopening and checking the new header plus the three populated rows.
- Do not add Z06-derived default-selected display behavior in this pass. Existing Z06 option-row-authored `display_behavior=default_selected` choices stay as-is; `z06_default_r8e_tax` remains blank in generated choice display behavior unless a later product decision changes it.
- Do not add a replacement Python allowlist, model-specific table, or hardcoded RPO/rule-id branch.
- Do not change runtime JavaScript, CSS, dealer submission, endpoints, payload construction, or Turnstile/security behavior.
- Do not change which `default_selection_rules` rows exist, active state, target option ids, condition types, scopes, or priorities beyond adding the `display_behavior` authoring column and the three current parity-preserving values.
- Do not change `display_behavior` on option source rows or variant override sheets in this pass.
- No new dependencies.
- Treat generated artifacts as proof outputs, not source. Restore timestamp-only generated churn before final handoff.

## 6. Risks and non-goals

Risks:

- Adding a workbook column can accidentally alter emitted `defaultSelectionRules` payload shape if the loader does not strip the workbook-only authoring field. The spec requires focused tests for this.
- A broad implementation could treat every `default_selection_rules` row as display metadata and newly mark FE1/NGA/719/J6D/T0E/R8E choices as `default_selected`. That is out of scope and must fail parity validation.
- Workbook write safety is higher risk than the previous generator-only Phase 2; safe-save and on-disk verification are mandatory.

Non-goals:

- No product decision on whether Z06 `z06_default_719`, `z06_default_efr`, `z06_default_t0e`, or `z06_default_r8e_tax` should also be default-selected display metadata. Current Z06 display behavior is preserved.
- No cleanup of future `zr1`/`zr1x` rows, even though those rows are visible in `default_selection_rules`.
- No Phase 4 work: wildcard/shared asset rows, media-coverage policy, Finding 9 stale-note cleanup, or asset-map scope semantics.
- No deletion of default-selection rules or exclusive groups.
- No runtime behavior unification beyond replacing the Python allowlist with workbook-authored metadata.

## 7. Validation plan

Run in this order and report actual output:

1. Preflight:
   - `git status --short --branch`
   - Check no Excel lock file exists: `python3 - <<'PY' ... Path('~$stingray_master.xlsx').exists() ... PY` or equivalent.
   - `.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx` — must be valid before edits.
2. Baseline current generated outputs before code/workbook changes:
   - `.venv/bin/python scripts/generate_form.py --model stingray`
   - `.venv/bin/python scripts/generate_form.py --model grand_sport`
   - `.venv/bin/python scripts/generate_form.py --model z06`
   - `.venv/bin/python scripts/generate_registry.py`
   - Copy the three runtime contracts plus `form-output/stingray-form-data.{json,csv}` to a `/tmp` baseline directory.
   - `git status --short -- form-output form-app/data.js stingray_master.xlsx` and classify any pre-existing generated drift before editing.
3. Apply the workbook edit with a safe-save helper:
   - Add `display_behavior` header to `default_selection_rules`.
   - Set exactly the three parity-preserving rows to `default_selected`.
   - Save safely and reopen the saved workbook to verify header and row values on disk.
   - Run the standalone workbook package gate and capture its output: `.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx`.
4. Implement the loader/call-site/test changes from Section 2.
5. Focused Python tests:
   - `.venv/bin/python -m pytest tests/test_runtime_metadata_guards.py -q`
   - If the implementation touches neighboring metadata loaders, also run `.venv/bin/python -m pytest tests/test_schema_validation_metadata.py -q`.
6. Regenerate all three promoted model artifacts, but do not run `generate_registry.py` yet:
   - `.venv/bin/python scripts/generate_form.py --model stingray`
   - `.venv/bin/python scripts/generate_form.py --model grand_sport`
   - `.venv/bin/python scripts/generate_form.py --model z06`
7. Parity proof before registry publication:
   - `node scripts/compare-generated-contracts.mjs <before-stingray-runtime.json> form-output/runtime/stingray-runtime-contract.json`
   - same for Grand Sport and Z06 runtime contracts.
   - `node scripts/compare-generated-contracts.mjs <before-stingray-form-data.json> form-output/stingray-form-data.json`
   - `cmp -s <before-stingray-form-data.csv> form-output/stingray-form-data.csv`
   - If any real non-timestamp diff appears, stop and flag it immediately. Do not proceed by choosing production-precedent behavior or by publishing the registry.
8. After parity passes, run `.venv/bin/python scripts/generate_registry.py`.
9. Run the behavior companion tests sequentially:
   ```sh
   for t in \
     tests/stingray-generator-stability.test.mjs \
     tests/grand-sport-draft-data.test.mjs \
     tests/z06-form-data-draft.test.mjs \
     tests/multi-model-runtime-switching.test.mjs
   do
     node --test "$t"
   done
   ```
10. Workbook/schema gates:
    - `.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx`
    - `.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx`
    - `node --test tests/workbook-schema-standardization.test.mjs`
11. Syntax/static checks:
    - `.venv/bin/python -m py_compile scripts/corvette_form_generator/runtime_metadata.py scripts/corvette_form_generator/production.py scripts/corvette_form_generator/inspection.py tests/test_runtime_metadata_guards.py`
    - `git diff --check`
12. Final cleanup:
    - Review `git diff --name-only` and generated JSON diffs.
    - Restore timestamp-only generated artifact churn (`form-output/*`, `form-app/data.js`) before final handoff unless a real, approved generated diff remains.
    - Confirm final diffs are limited to `stingray_master.xlsx`, the runtime metadata/generator/test code, and this spec closure update.

## 8. Handoff requirements for this phase

On completion, report per AGENTS.md Section 15:

- Exact workbook change: new `default_selection_rules.display_behavior` column and the three rows set to `default_selected`.
- Exact code change: removal of `_DEFAULT_SELECTED_DISPLAY_RULE_IDS_BY_MODEL`, new workbook-owned loader, and production/inspection call-site split between emitted default rules and display-derivation rules.
- Explicit statement that Z06 behavior did not change and that `z06_default_r8e_tax` remains non-display-default unless a future product decision changes it.
- Companion-file impact matrix: generated contracts, `form-app/data.js`, runtime JS, model configs, Node tests, Python tests, docs/guidance.
- Validation results from Section 7, including comparator output for all three runtime contracts and Stingray compatibility artifacts.
- Confirmation that generated timestamp-only churn was restored, or a precise list of approved generated diffs if any remain.
- Confirmation that dealer submission, runtime JS, CSS, source-assembly routing, and Phase 4 items were untouched.
- Gates not run and why.
- Residual risks/manual verification pending.

## 9. Implementation evidence

Implemented changes:

- `stingray_master.xlsx` now has `default_selection_rules.display_behavior`.
- Exactly these rows are populated with `default_selected`:
  - `stingray` / `default_bc7`
  - `grand_sport` / `gs_default_bc7_coupe`
  - `grand_sport` / `gs_default_nga_unless_nwi`
- All other active default-selection rows remain blank for this field, including Z06 `z06_default_719`, `z06_default_efr`, `z06_default_t0e`, and `z06_default_r8e_tax`.
- `runtime_metadata.py` removed `_DEFAULT_SELECTED_DISPLAY_RULE_IDS_BY_MODEL`, added `load_default_selection_display_rules(...)`, and strips workbook-only `display_behavior` from emitted `load_default_selection_rules(...)` rows.
- `production.py` and `inspection.py` now feed the workbook-owned display-rule rows into `derived_default_selected_display_behavior(...)` while preserving the emitted `defaultSelectionRules` payload.
- `tests/test_runtime_metadata_guards.py` now covers the workbook-only authoring column, display-rule loader, derivation/no-derivation behavior, and no Python rule-id allowlist.

Validation run:

- Preflight `git status --short --branch`: branch `phase-2-shared-assembly-extraction...origin/phase-2-shared-assembly-extraction`; only this untracked spec existed before implementation.
- Excel lock check: `lock_exists: False`.
- Pre-edit `.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx`: `status: valid`, `issue_count: 0`.
- Pre-edit `.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx`: `status: valid`, `error_count: 0`, `warning_count: 0`.
- Baseline regenerated and copied to `/tmp/27vette-phase3-default-selected-baseline-20260630231434`.
- Workbook safe-save used `save_workbook_safely()`; backup created at `backups/stingray_master-20260630-231507.xlsx`.
- On-disk verification found only three `default_selection_rules.display_behavior` values: the approved Stingray BC7 and Grand Sport BC7/NGA rows.
- Post-save standalone `.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx`: `status: valid`, `issue_count: 0`.
- `.venv/bin/python -m pytest tests/test_runtime_metadata_guards.py -q`: `10 passed`.
- `.venv/bin/python -m pytest tests/test_runtime_metadata_guards.py tests/test_schema_validation_metadata.py -q`: `39 passed`.
- `.venv/bin/python -m py_compile scripts/corvette_form_generator/runtime_metadata.py scripts/corvette_form_generator/production.py scripts/corvette_form_generator/inspection.py tests/test_runtime_metadata_guards.py`: exit `0`.
- Regenerated promoted model artifacts for Stingray, Grand Sport, and Z06.
- Timestamp-normalized parity via `scripts/compare-generated-contracts.mjs` passed for:
  - Stingray runtime contract
  - Grand Sport runtime contract
  - Z06 runtime contract
  - `form-output/stingray-form-data.json`
- `cmp -s` CSV parity for `form-output/stingray-form-data.csv`: exit `0`.
- `.venv/bin/python scripts/generate_registry.py`: exit `0`.
- Behavior companion tests passed:
  - `node --test tests/stingray-generator-stability.test.mjs`: 14 passed
  - `node --test tests/grand-sport-draft-data.test.mjs`: 19 passed
  - `node --test tests/z06-form-data-draft.test.mjs`: 24 passed
  - `node --test tests/multi-model-runtime-switching.test.mjs`: 46 passed
- Final standalone `.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx`: `status: valid`, `issue_count: 0`.
- Final `.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx`: `status: valid`, `error_count: 0`, `warning_count: 0`.

Validation exception:

- `node --test tests/workbook-schema-standardization.test.mjs` failed on the pre-existing Z06 replace-rule assertion: rows 82-86 in `z06_rule_mapping` (`T0F/T0G/Z07/PDD/PDF` replacing `CBF`) are reported by the test.
- This failure is unrelated to Phase 3. The rows are present with the same values in the pre-Phase-3 safe-save backup `backups/stingray_master-20260630-231507.xlsx` and in the current workbook.
- Phase 3 did not edit `z06_rule_mapping`, Z06 generated parity passed, and `z06-form-data-draft.test.mjs` passed.

Generated artifact cleanup:

- Regenerated `form-output/*` and `form-app/data.js` changes were timestamp-only / parity-equivalent and were restored before handoff.

Preserved boundaries:

- No runtime JavaScript, CSS, dealer submission code, source-assembly routing, option-row `display_behavior`, variant override sheet, default-selection rule target/scope/priority/active values, Z06 behavior, or Phase 4 asset/media scope changed.