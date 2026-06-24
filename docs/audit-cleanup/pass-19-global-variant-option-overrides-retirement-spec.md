# Pass 19 — Global Variant Option Overrides Retirement Spec

Status: Spec only. Do not implement until approved.
Date: 2026-06-24
Recommended reasoning level for implementation agent: high.

Source context:

- `AGENTS.md`
- `docs/audit-cleanup/pass-16-variant-override-sheet-semantics-report.md`
- `docs/audit-cleanup/pass-17-default-selected-display-metadata-derivation-spec.md`
- `docs/audit-cleanup/pass-18-uqt-single-canonical-option-source-ownership-spec.md`
- `docs/metadata-runtime-redundancy-6-23.md`
- `docs/Audit-route-map.md`
- `27vette-workbook-guard` reference `variant-override-semantics-classification.md`

## Goal

Retire the now-empty global `variant_option_overrides` behavior contract from the active workflow without changing generated/runtime Corvette behavior.

The intended end state is:

- Active models use only their model-scoped `variant_option_overrides_sheet` from `model_workbook_sources`:
  - Stingray: `stingray_variant_overrides`
  - Grand Sport: `grandSport_variant_overrides`
  - Z06: `z06_variant_overrides`
- The loader no longer gives the historical global `variant_option_overrides` sheet precedence over a configured model-scoped sheet.
- The empty global workbook sheet is removed only if the preflight proves no active source role or current consumer still requires it.
- Generated runtime contracts remain equivalent after timestamp normalization.

This is a no-behavior-change cleanup pass. It should reduce the chance that future work reintroduces global emitted-value override semantics for active models.

## Diagnosis

Change type for this spec: docs-only.

Change type for the future implementation pass: mixed generator/workbook/test/docs, with no intended runtime data or UX behavior change. Generated artifacts may be rewritten during validation, but any timestamp-only churn should be restored before handoff unless a real payload change is explicitly classified.

Risk level: medium-high.

Root cause:

- Before Pass 18, `variant_option_overrides` still carried active Stingray UQT suppression behavior and had special semantics:
  - `active` was an emitted choice override value, not row activation.
  - `load_variant_option_overrides()` read the global sheet first and only used a model-scoped fallback sheet when no global rows were found.
- Pass 18 moved active Stingray UQT behavior to `stingray_variant_overrides`, leaving `variant_option_overrides` with 0 rows.
- The historical loader branch remains in `runtime_metadata.py`, so an empty global sheet still has implicit priority semantics and could silently shadow model-scoped sheets if rows are reintroduced.
- Active model-scoped sheets remain canonical and must not be retired in this pass.

## Current evidence inspected for this spec

Branch/worktree:

- `git status --short --branch` was run before writing this spec.
- `docs/audit-cleanup/pass-19-global-variant-option-overrides-retirement-spec.md` did not exist before this spec.

Workbook read-only probe via `openpyxl` after Pass 18:

- `variant_option_overrides`
  - rows: 0
  - active rows: 0
  - headers: `model_key`, `option_id`, `variant_id`, `status`, `selectable`, `active`, `display_behavior`, `notes`
- `stingray_variant_overrides`
  - rows: 4
  - active rows: 4
  - headers: `option_id`, `variant_id`, `selectable`, `display_behavior`, `section_id`, `active`, `note`
- `grandSport_variant_overrides`
  - rows: 4
  - active rows: 4
  - same model-scoped contract shape.
- `z06_variant_overrides`
  - rows: 4
  - active rows: 4
  - same model-scoped contract shape.
- `model_workbook_sources`
  - rows: 53
  - active rows: 33
  - active `variant_option_overrides_sheet` roles:
    - `grand_sport` -> `grandSport_variant_overrides`
    - `z06` -> `z06_variant_overrides`
    - `stingray` -> `stingray_variant_overrides`
  - No active model currently points to `variant_option_overrides`.

Code consumers identified:

- `scripts/corvette_form_generator/runtime_metadata.py`
  - `load_variant_option_overrides()` currently reads `optional_rows(wb, "variant_option_overrides")` first and uses the configured fallback sheet only when no global rows are found.
  - `optional_rows()` already returns `[]` for missing optional sheets, so deleting the empty sheet is mechanically possible if no explicit consumer requires it.
- `scripts/corvette_form_generator/production.py`
  - Stingray production calls `load_variant_option_overrides(wb, MODEL_CONFIG.model_key, MODEL_CONFIG.variant_option_overrides_sheet)`.
  - After Pass 18, it applies model-scoped `section_id`, `selectable`, and `display_behavior` generically.
- `scripts/corvette_form_generator/inspection.py`
  - Grand Sport/Z06 inspection path calls `load_variant_option_overrides(wb, config.model_key, config.variant_option_overrides_sheet)` through `keyed_variant_option_overrides()`.
- `scripts/corvette_form_generator/model_configs.py`
  - `OPTIONAL_GENERATION_SOURCE_ROLES = ("variant_option_overrides_sheet",)`.
  - The optional role should stay; this pass targets the global sheet/precedence, not the model-scoped role.
- `scripts/corvette_form_generator/schema_validation.py`
  - `ROLE_BOOLEAN_COLUMNS["variant_option_overrides_sheet"] = ("active", "selectable")` applies to model-scoped role sheets.
  - `variant_option_overrides` is not listed in `REQUIRED_SHEETS`.
- `scripts/corvette_form_generator/editor_ops.py`
  - `SOURCE_ROLE_FAMILIES["variant_option_overrides_sheet"] = "variant_overrides"` should remain for model-scoped sheet editing.
- Tests:
  - `tests/stingray-generator-stability.test.mjs` asserts Stingray no longer depends on global emitted-value UQT overrides and constructs temporary `stingray_variant_overrides` coverage.
  - `tests/workbook-schema-standardization.test.mjs` expects future model source roles such as `zr1_variant_overrides` / `zr1x_variant_overrides`, which are model-scoped and out of scope for deletion.

Standing docs after Pass 18:

- `docs/metadata-runtime-redundancy-6-23.md` already classifies `variant_option_overrides` as 0 rows and as a historical/global contract surface requiring a separate sheet-retirement spec.
- `docs/Audit-route-map.md` says the global sheet/loader path should not be deleted without a separate sheet-retirement spec.

## Proposed implementation

### Phase 0 — mandatory preflight / stop conditions

Before editing, run a read-only probe and stop if any condition fails:

1. Confirm no Excel lock file exists:

```sh
test ! -e '~$stingray_master.xlsx'
```

2. Confirm `variant_option_overrides` has 0 data rows.
3. Confirm no active `model_workbook_sources` row uses `sheet_name=variant_option_overrides`.
4. Confirm active `variant_option_overrides_sheet` roles exist for all promoted active models:
   - Stingray -> `stingray_variant_overrides`
   - Grand Sport -> `grandSport_variant_overrides`
   - Z06 -> `z06_variant_overrides`
5. Confirm model-scoped UQT rows are still present in the three model-scoped override sheets.

If any global rows exist, or if an active model still points at `variant_option_overrides`, do not implement the retirement. Instead, write a findings-only report and return for a source-owner decision.

### Phase 1 — code cleanup

Change `scripts/corvette_form_generator/runtime_metadata.py`:

- Update `load_variant_option_overrides()` so it reads only the configured `fallback_sheet` / model-scoped sheet.
- Remove the hardcoded global first-read from `optional_rows(wb, "variant_option_overrides")`.
- Preserve normalized output fields:
  - `option_id`
  - `variant_id`
  - `status`
  - `selectable`
  - `active`
  - `display_behavior`
  - `section_id`
  - `note`
  - `notes`
- Preserve model-scoped active-row semantics:
  - `active` controls row activation for model-scoped sheets.
  - It should not emit an `active` override value from model-scoped rows.
- Preserve optional-role behavior:
  - Missing or blank configured sheet returns `[]`.
  - Do not make `variant_option_overrides_sheet` required for future inactive/unpromoted models unless the schema source-role pass separately approves that.

Do not remove `OPTIONAL_GENERATION_SOURCE_ROLES` or `SOURCE_ROLE_FAMILIES["variant_option_overrides_sheet"]`; those are still needed for model-scoped override sheets.

### Phase 2 — workbook cleanup

If Phase 0 proves the global sheet is empty and unreferenced:

- Delete the `variant_option_overrides` worksheet from `stingray_master.xlsx` through a safe-save helper.
- Do not delete or modify:
  - `stingray_variant_overrides`
  - `grandSport_variant_overrides`
  - `z06_variant_overrides`
  - future/inactive `zr1_variant_overrides` / `zr1x_variant_overrides` source roles, if present
- After saving, verify on disk with `openpyxl`:
  - `variant_option_overrides` sheet is absent.
  - the three active model-scoped override sheets are present with 4 active UQT rows each.
  - active promoted model source roles still point to model-scoped sheets.

If deleting the sheet creates workbook/package/editor issues, keep the sheet absent from active source roles and leave the physical sheet in place with a documented reason. Do not compensate by adding hidden runtime behavior.

### Phase 3 — tests / guards

Update tests to guard the retired contract:

- `tests/stingray-generator-stability.test.mjs`
  - Replace assumptions that `variant_option_overrides` exists with a guard that the global sheet is absent or has 0 rows.
  - Add/keep assertions that no active model source role points at `variant_option_overrides`.
  - Keep the UQT guard proving Stingray model-scoped overrides emit standard/display-only trim equipment.
- Add a focused loader test if needed in the existing Node/Python test surface:
  - Global `variant_option_overrides` rows should no longer shadow configured model-scoped sheets.
  - A configured model-scoped sheet should still load active rows and ignore inactive rows.

Do not add a new dependency.

### Phase 4 — generated artifact parity

Because this is no-behavior-change cleanup:

- Snapshot current promoted runtime contracts before edits.
- Regenerate affected active models and registry after edits.
- Compare generated contracts after normalizing timestamp fields.
- If generated artifacts are timestamp-only, restore generated artifact churn before handoff so the final diff contains only source/workbook/test/docs changes.
- If any non-timestamp payload drift appears, stop and classify it before proceeding.

## Exact files/sheets expected to change if implemented

Expected source/test/docs changes:

- `scripts/corvette_form_generator/runtime_metadata.py`
- `tests/stingray-generator-stability.test.mjs`
- `docs/audit-cleanup/pass-19-global-variant-option-overrides-retirement-spec.md`
- `docs/metadata-runtime-redundancy-6-23.md`
- `docs/Audit-route-map.md`

Expected workbook change:

- `stingray_master.xlsx`
  - Delete physical sheet `variant_option_overrides` only if Phase 0 and package/editor checks prove it is safe.
  - No active model-scoped override sheet rows should change.

Expected generated artifacts:

- No final generated artifact payload drift.
- Temporary timestamp-only rewrites may occur during validation and should be restored unless a real behavior change is explicitly approved.

## Constraints

- Preserve visual/runtime behavior.
- Preserve dealer submission endpoint, payload shape, and Turnstile behavior.
- No new dependencies.
- No runtime JavaScript changes unless a test reveals a true generic bug; if so, stop and rescope.
- Do not delete model-scoped variant override sheets.
- Do not migrate UQT behavior again.
- Do not change Z06 replacement/direct-rule behavior.
- Do not change `variant_option_overrides_sheet` as a model-scoped source role.
- Do not hide workbook source-role problems in Python fallbacks.
- Do not edit generated artifacts by hand.

## Risks

1. Loader behavior risk.
   - Removing the global first-read changes behavior if a hidden active model still relies on global rows.
   - Phase 0 must prove there are no global rows and no active source-role references.

2. Future model scaffold risk.
   - Inactive ZR1/ZR1X metadata may still mention model-scoped override sheets.
   - This pass must not make future/inactive scaffold generation stricter than current source metadata supports.

3. Workbook editor/schema risk.
   - The editor uses the `variant_option_overrides_sheet` role family, not necessarily the global sheet.
   - If the physical global sheet is deleted, editor/schema checks must still support model-scoped override sheets.

4. Generated timestamp churn risk.
   - Generators and some tests rewrite timestamp fields.
   - Validation must snapshot/compare/restore so final diffs do not imply customer-facing data changes.

## Non-goals

- Retiring `stingray_variant_overrides`, `grandSport_variant_overrides`, or `z06_variant_overrides`.
- Normalizing Z06 replacement behavior.
- Consolidating `variant_master` and `model_variants`.
- Retiring generated workbook `form_*` sheets.
- Changing raw order-guide ingest.
- Changing runtime JavaScript rendering/evaluation.
- Refactoring the model generation route.

## Validation plan

Preflight:

```sh
git status --short --branch
test ! -e '~$stingray_master.xlsx'
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python - <<'PY'
from openpyxl import load_workbook
wb = load_workbook('stingray_master.xlsx', read_only=True, data_only=True)
# Fail if variant_option_overrides has rows or active model source roles still point to it.
PY
mkdir -p /tmp/pass-19-before /tmp/pass-19-after
cp form-output/runtime/stingray-runtime-contract.json /tmp/pass-19-before/
cp form-output/runtime/grand-sport-runtime-contract.json /tmp/pass-19-before/
cp form-output/runtime/z06-runtime-contract.json /tmp/pass-19-before/
cp form-app/data.js /tmp/pass-19-before/data.js
```

After workbook save:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
.venv/bin/python - <<'PY'
from openpyxl import load_workbook
wb = load_workbook('stingray_master.xlsx', read_only=True, data_only=True)
assert 'variant_option_overrides' not in wb.sheetnames
for sheet in ('stingray_variant_overrides', 'grandSport_variant_overrides', 'z06_variant_overrides'):
    assert sheet in wb.sheetnames
print('PASS19_WORKBOOK_OVERRIDE_SURFACES_OK')
PY
```

Generation / parity:

```sh
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
.venv/bin/python scripts/generate_registry.py
cp form-output/runtime/stingray-runtime-contract.json /tmp/pass-19-after/
cp form-output/runtime/grand-sport-runtime-contract.json /tmp/pass-19-after/
cp form-output/runtime/z06-runtime-contract.json /tmp/pass-19-after/
node scripts/compare-generated-contracts.mjs /tmp/pass-19-before/stingray-runtime-contract.json /tmp/pass-19-after/stingray-runtime-contract.json
node scripts/compare-generated-contracts.mjs /tmp/pass-19-before/grand-sport-runtime-contract.json /tmp/pass-19-after/grand-sport-runtime-contract.json
node scripts/compare-generated-contracts.mjs /tmp/pass-19-before/z06-runtime-contract.json /tmp/pass-19-after/z06-runtime-contract.json
```

If only timestamps changed, restore generated churn before final handoff and verify registry sync:

```sh
git checkout -- form-app/data.js form-output/runtime/stingray-runtime-contract.json form-output/runtime/grand-sport-runtime-contract.json form-output/runtime/z06-runtime-contract.json form-output/stingray-form-data.json form-output/stingray-form-data.csv
.venv/bin/python scripts/generate_registry.py
# Only keep registry/generated diffs if a non-timestamp payload change was approved; otherwise restore and report no generated artifact diff.
```

Targeted gates:

```sh
.venv/bin/python -m py_compile scripts/corvette_form_generator/runtime_metadata.py
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
node --test tests/stingray-generator-stability.test.mjs
node --test tests/stingray-form-regression.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/z06-interior-accessory-cleanup.test.mjs
node --test tests/workbook-schema-standardization.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
git diff --check
```

Z06 gate note:

- If `tests/z06-interior-accessory-cleanup.test.mjs` rewrites `form-output/runtime/z06-runtime-contract.json`, use the same snapshot/restore pattern from Pass 18 and require a final clean diff for that artifact unless a real Z06 payload change is explicitly classified.

Browser proof:

- Browser proof is optional if generated contracts are timestamp-normalized identical and runtime JS is untouched.
- If any generated payload drift is retained, run a local browser proof for UQT selectable vs standard/display-only behavior across Stingray, Grand Sport, and Z06.

## Completion requirements

If implemented, update this spec to `Implemented` with:

- changed files/sheets/artifacts,
- workbook package/schema results,
- generated parity results,
- exact gates run,
- whether the physical `variant_option_overrides` sheet was deleted or retained with reason,
- residual risks and next-step guidance.

Update standing docs if they would otherwise still describe the global sheet as an active future cleanup item.

## Approval prompt

Approve Pass 19 as a no-behavior-change cleanup to retire the empty global `variant_option_overrides` contract: preflight that no active model or row still uses it, update the loader to use only configured model-scoped override sheets, delete the physical empty sheet only if package/editor/schema checks allow it, add tests preventing global sheet reintroduction/shadowing, prove generated runtime contracts are timestamp-normalized identical, restore timestamp-only generated churn, and update this spec plus standing docs with completion evidence before handoff.
