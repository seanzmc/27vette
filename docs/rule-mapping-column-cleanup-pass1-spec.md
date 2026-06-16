# Rule Mapping Column Cleanup — Pass 1 Spec

Recommended reasoning level: high.

## Status

Spec only. Do not implement until approved.

## Diagnosis

The promoted runtime models currently read compatibility rules from these workbook source sheets:

- `rule_mapping` for Stingray
- `grandSport_rule_mapping` for Grand Sport
- `z06_rule_mapping` for Z06

The rule-mapping sheets carry several columns that are not final form logic. They either duplicate data already owned elsewhere in the workbook, preserve old lifecycle/audit state, or exist as generator/report helper fields. Keeping those columns in canonical source sheets makes the workbook look more complicated than the runtime contract actually is and encourages data rows that exist only to satisfy validators/tests.

Current evidence inspected:

- `docs/rule-mapping-cleanup-candidates.md` current classification report.
- `scripts/corvette_form_generator/rules.py:14-24` uses `normalization_status` / `generation_action` only to decide row inclusion.
- `scripts/corvette_form_generator/rules.py:131-195` consumes direct rule rows for Grand Sport/Z06 and emits generated `rules`.
- `scripts/corvette_form_generator/production.py:399-477` consumes direct rule rows for Stingray and emits generated `rules` / `form_rules`.
- `scripts/corvette_form_generator/interiors.py:123-132` uses `rule_type`, `source_id`, `target_id`, and `runtime_authored_rule()` to detect interiors that include `opt_z25_001`.
- `scripts/corvette_form_generator/schema_validation.py:807-875` currently requires and validates lifecycle columns that this pass intends to retire.
- `scripts/corvette_form_generator/editor_ops.py:73-88` exposes rule-mapping enums/refs for columns that this pass intends to retire.
- `scripts/build_rule_sources.py` still references the retired candidates for optional audit/report output and must be updated or explicitly protected from default readiness.
- `form-app/app.js:199-204` indexes generated rules by `source_id` / `target_id`.
- `form-app/app.js:583-593` currently reads generated `body_style_scope`; this pass must not remove it.
- `form-app/app.js:1456-1462` and `form-app/app.js:1577-1587` currently use generated `runtime_action=replace`; this pass must not remove it.
- `tests/stingray-generator-stability.test.mjs:68-85` pins old rule-mapping headers and must be updated with the source-contract change.
- Read-only workbook probe confirmed unpromoted future-model sheets `zr1_rule_mapping` and `zr1x_rule_mapping` currently exist, and `model_workbook_sources` has inactive `rule_mapping_sheet` rows for both (`active=False`).

Risk level: medium. This pass changes workbook source schemas plus generator/schema/editor/audit code. It should be behavior-preserving for live form logic, but bad derivation of source/target sections or mishandling the one `generation_action=preserve_runtime_exclude` row could change generated rules.

Change type: mixed workbook schema + generator/source-contract + tests/docs. No intended customer-facing runtime behavior change.

## Ownership Decision

The workbook should keep only business-rule facts needed for runtime behavior:

- `rule_id`
- `source_id`
- `rule_type`
- `target_id`
- `original_detail_raw`
- `body_style_scope`
- `runtime_action`
- `disabled_reason`

The workbook should not keep duplicated or lifecycle-only rule-mapping columns as canonical source fields:

- `source_type`
- `target_type`
- `source_selection_mode`
- `target_selection_mode`
- `source_section`
- `target_section`
- `normalization_status`
- `generation_action`

Replacement ownership:

- Source/target entity type should be inferred from `source_id` / `target_id` membership in active option rows or active interiors.
- Source/target section should be derived from the source/target option row or interior row metadata.
- Source/target selection mode should be derived from the derived section and `section_master.selection_mode`.
- Row inclusion should be explicit: if a direct rule row should not generate, delete the row or remodel the relationship. Do not preserve suppression lifecycle columns in source sheets.
- The one Grand Sport `generation_action=preserve_runtime_exclude` row must be resolved directly before removing the column.

## Exact Files / Sheets to Change

Workbook source sheets in `stingray_master.xlsx`:

- `rule_mapping`
- `grandSport_rule_mapping`
- `z06_rule_mapping`
- `zr1_rule_mapping`
- `zr1x_rule_mapping`
- `model_workbook_sources`

Remove these columns from all three sheets:

- `target_type`
- `source_type`
- `target_selection_mode`
- `source_selection_mode`
- `target_section`
- `source_section`
- `generation_action`
- `normalization_status`

Also remove any trailing blank header/table columns left behind in `rule_mapping`.

For unpromoted future models:

- Delete or archive `zr1_rule_mapping` and `zr1x_rule_mapping` in the same workbook-safe pass.
- Remove or deactivate their `model_workbook_sources` rows for `source_role=rule_mapping_sheet`.
- Keep ZR1/ZR1X out of generation, registry promotion, and runtime scope.
- Do not touch other ZR1/ZR1X option, OVS, price-rule, rule-group, exclusive-group, or variant-override sheets unless required only to remove stale references to the deleted rule-mapping sheets.
- Document that ZR1/ZR1X direct rule rows will be rebuilt later against the reduced clean rule-mapping schema after Stingray, Grand Sport, and Z06 are stable.

Keep these columns:

- `rule_id`
- `source_id`
- `rule_type`
- `target_id`
- `original_detail_raw`
- `body_style_scope`
- `runtime_action`
- `disabled_reason`

Code files expected to change:

- `scripts/corvette_form_generator/rules.py`
  - Remove lifecycle-column row-inclusion logic.
  - Derive source/target type, section, and selection mode from canonical source data.
  - Preserve generated rule output shape only if intentionally still needed; do not emit deleted workbook fields into live runtime data unless browser/runtime/tests prove they are needed.
- `scripts/corvette_form_generator/production.py`
  - Mirror the same derivation/removal path for Stingray production generation.
  - Prefer a small shared helper from `rules.py` over duplicating derivation logic if that keeps the change contained.
- `scripts/corvette_form_generator/interiors.py`
  - Stop depending on `runtime_authored_rule()` lifecycle semantics for Z25 include detection; direct active source rows should be represented by existing rows.
- `scripts/corvette_form_generator/schema_validation.py`
  - Remove lifecycle-column requirements/checks for `*_rule_mapping`.
  - Add/update source-contract checks for the new reduced rule-mapping headers and direct source/target reference validity.
- `scripts/corvette_form_generator/editor_ops.py`
  - Remove enum/ref metadata for retired rule-mapping columns.
  - Keep enums for `rule_type`, `body_style_scope`, and `runtime_action`.
- `scripts/build_rule_sources.py`
  - Update optional audit/report logic so it does not require retired workbook columns.
  - Infer type/section/mode if the report still needs those diagnostics, or drop those fields from report-only outputs if they have no diagnostic value.
- Tests that currently assert old headers or lifecycle validation, including at least:
  - `tests/stingray-generator-stability.test.mjs`
  - `tests/workbook-schema-standardization.test.mjs`
  - `tests/test_schema_validation_metadata.py`
  - `tests/test_registry_promotion_metadata.py` if fixtures still include retired generated fields
  - Any editor/server tests that derive editable rule-mapping schemas from `editor_ops.py`
  - Any workbook schema/editor tests that currently expect `zr1_rule_mapping` / `zr1x_rule_mapping` to exist or be registered in `model_workbook_sources`

Generated artifacts expected to be regenerated/reviewed, not hand-edited:

- generated `form_*` sheets in `stingray_master.xlsx`, especially `form_rules`
- `form-output/stingray-form-data.json`
- `form-output/stingray-form-data.csv`
- `form-output/inspection/grand-sport-runtime-contract.json`
- `form-output/inspection/grand-sport-form-data-draft.json`
- `form-output/inspection/z06-runtime-contract.json`
- `form-output/inspection/z06-form-data-draft.json`
- `form-app/data.js` after `scripts/generate_registry.py`

Generated `rules` payload-shape intent for Pass 1:

- Preserve the current generated runtime `rules` object shape for promoted models by deriving and emitting these fields from canonical source data rather than from rule-mapping sheet columns:
  - `source_type`
  - `target_type`
  - `source_section`
  - `target_section`
  - `source_selection_mode`
  - `target_selection_mode`
- This pass is primarily workbook source-schema cleanup. It is not intended to trim generated runtime payload fields unless repo evidence during implementation proves a field is unused by runtime, submission payloads, and retained contract tests and the generated-contract comparison makes that trimming explicit.
- If generated fields are trimmed despite the preferred preservation path, the handoff must identify that as approved payload-shape trimming, separate from behavior parity.

## Explicit Constraints

- Preserve live customer/dealer behavior. This is schema/data cleanup, not a form behavior pass.
- Do not remove `body_style_scope` in this pass. It is runtime-read and belongs in a later parity-proven audit pass.
- Do not remove `runtime_action` in this pass. It carries live replacement/default-removal behavior.
- Do not remodel replacement/default semantics in this pass.
- Do not add a parallel taxonomy, review sheet, or new lifecycle column to replace `normalization_status` / `generation_action`.
- Do not hide source-data problems in JavaScript.
- Do not add model/RPO-specific runtime exceptions.
- Do not hand-edit generated `form_*`, `form-output/*`, or `form-app/data.js` artifacts.
- No new dependencies.
- Visual UI should be unchanged.
- Dealer submission payload shape should be unchanged except for any generated debug-only rule fields that are explicitly proven unused by `form-app/app.js` and submission assembly.
- Do not promote ZR1/ZR1X, run ZR1/ZR1X generation, or add ZR1/ZR1X to the runtime registry.
- No workbook write until this updated spec is reviewed and approved.
- Respect pre-existing dirty work. Current preflight showed `docs/rule-mapping-cleanup-candidates.md` modified before this spec; do not overwrite or revert it without explicit user direction.
- The active branch is `generator-simplification-pass1`, currently ahead of `origin/main` by 21 commits and not behind after `git fetch origin main`; do not rebase/merge/push as part of this pass.

## Pass 1 Implementation Plan

### 1. Preflight and snapshot

1. Run:
   - `git status --short --branch`
   - `test ! -e '~$stingray_master.xlsx'`
   - `.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx`
   - `.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx`
2. Snapshot current generated runtime contracts for parity comparison:
   - `cp form-output/stingray-form-data.json /tmp/stingray-rule-mapping-pass1-before.json`
   - `cp form-output/inspection/grand-sport-runtime-contract.json /tmp/grand-sport-rule-mapping-pass1-before.json`
   - `cp form-output/inspection/z06-runtime-contract.json /tmp/z06-rule-mapping-pass1-before.json`
3. Inventory the one `generation_action` row:
   - `grandSport_rule_mapping.gs_rule_opt_cfl_001_excludes_opt_cfz_001`
   - Determine whether deleting it or keeping it as a normal explicit `excludes` row preserves generated/browser behavior.

### 2. Add derivation helpers before workbook write

Add or update small generic helpers so both generation paths can derive removed metadata:

- entity type from `source_id` / `target_id` membership in options/interiors
- entity section from option row `section_id` or interior row section metadata
- selection mode from derived section and `section_master`

Do not use hardcoded RPO/model exceptions.

### 3. Resolve the `generation_action` row

Before deleting the column, handle `grandSport_rule_mapping.gs_rule_opt_cfl_001_excludes_opt_cfz_001` explicitly:

- If the row has no runtime impact because section/exclusive/group metadata already owns the behavior, delete that row from `grandSport_rule_mapping`.
- If the row does have runtime impact, keep it as a normal direct `excludes` row with no lifecycle/generation-action metadata and adjust generic dedupe only as needed.

This decision must be backed by before/after generated contract comparison and at least one focused Grand Sport runtime assertion if behavior is retained.

### 4. Rewrite workbook source headers safely

Use a safe-save workbook migration path, not manual Excel editing:

- Remove the eight retired columns from `rule_mapping`, `grandSport_rule_mapping`, and `z06_rule_mapping`.
- Delete or archive `zr1_rule_mapping` and `zr1x_rule_mapping`.
- Remove or deactivate the `model_workbook_sources` rows that register `zr1_rule_mapping` / `zr1x_rule_mapping` as `rule_mapping_sheet` sources.
- Refresh Excel table refs to the reduced dimensions.
- Save through `save_workbook_safely()`.
- Reopen the workbook from disk and assert exact promoted rule-mapping headers, row counts, future-model rule-mapping sheet absence/archive state, and `model_workbook_sources` state.

The migration helper should be temporary or deleted after verification; do not leave a stale one-pass workbook writer as executable documentation.

### 5. Regenerate and review

Run model generation and registry publication:

```sh
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
.venv/bin/python scripts/generate_registry.py
```

Then compare runtime contracts:

```sh
node scripts/compare-generated-contracts.mjs /tmp/stingray-rule-mapping-pass1-before.json form-output/stingray-form-data.json
node scripts/compare-generated-contracts.mjs /tmp/grand-sport-rule-mapping-pass1-before.json form-output/inspection/grand-sport-runtime-contract.json
node scripts/compare-generated-contracts.mjs /tmp/z06-rule-mapping-pass1-before.json form-output/inspection/z06-runtime-contract.json
```

Expected outcome:

- Rule behavior is unchanged.
- Preferred path: generated `rules` for Stingray, Grand Sport, and Z06 keep `source_type`, `target_type`, `source_section`, `target_section`, `source_selection_mode`, and `target_selection_mode`, with values derived from canonical source sheets instead of retired rule-mapping columns.
- If generated `rules` lose any of those fields, the comparison must identify that as approved payload-shape trimming and prove the fields are unused by runtime/dealer submission before accepting it.
- Contract comparisons must distinguish approved payload-shape trimming from changes to rule relationships, rule counts, `active`, `body_style_scope`, `runtime_action`, `auto_add`, or `disabled_reason`; those behavior-carrying differences are not expected in this pass.
- If counts or active relationships change, stop and classify whether the change is desired row cleanup (for example the resolved CFL/CFZ row) or a regression.

## Validation Plan

Required focused gates:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
node --test tests/stingray-generator-stability.test.mjs
node --test tests/stingray-form-regression.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/z06-form-data-draft.test.mjs
node --test tests/z06-runtime-rule-corrections.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
.venv/bin/python -m pytest tests/test_schema_validation_metadata.py tests/test_registry_promotion_metadata.py -q
```

Optional audit/report gates only if `scripts/build_rule_sources.py` is materially changed and retained:

```sh
.venv/bin/python scripts/build_rule_sources.py --model grand_sport
node --test tests/grand-sport-rule-audit.test.mjs
node --test tests/audit-parser-metadata-loaders.test.mjs
```

Manual/browser verification:

- Not required if generated contract comparison proves no behavior change and runtime tests pass.
- If `runtime_action`, replacement behavior, or the CFL/CFZ row behavior changes unexpectedly, add browser smoke for the affected Grand Sport section before handoff.

## Risks

- Removing source/target section columns without robust derivation could misclassify same-section redundant excludes.
- The one Grand Sport `preserve_runtime_exclude` row may reveal a hidden generator-dedupe workaround that needs direct modeling before column retirement.
- Removing ZR1/ZR1X rule-mapping sheets while leaving stale `model_workbook_sources` rows or tests behind could create confusing future-model readiness failures even though those models are intentionally out of runtime scope.
- `form-app/app.js` currently ignores several emitted rule fields, but tests or submission metadata may still assert payload shape. Any payload trimming must be explicitly reviewed, not dismissed as test-only.
- Optional audit/report tooling may rely on the retired columns for diagnostics. It should be updated or explicitly demoted, not allowed to silently rot.
- Workbook table ref updates are easy to miss after column deletion; package validation and reopen/header checks are mandatory.

## Non-goals

- Do not retire `body_style_scope`.
- Do not retire `runtime_action`.
- Do not remodel replacement/default semantics.
- Do not normalize or delete body-scoped ZZ3/engine-cover rules in this pass.
- Do not change rule-group or exclusive-group schemas except where code needs to derive source/target metadata.
- Do not promote ZR1/ZR1X or touch future-model scaffold rows beyond deleting/archiving `zr1_rule_mapping` / `zr1x_rule_mapping` and removing/deactivating stale references to those sheets.
- Do not redesign optional audit/report output beyond what is required to survive the source-schema cleanup.

## Approval Question

Approve Pass 1 as scoped above: retire duplicate/lifecycle rule-mapping columns for the three runtime models, delete/archive unpromoted ZR1/ZR1X rule-mapping sheets and their workbook-source registrations, derive section/type/mode metadata from canonical source sheets while preserving generated rule payload shape by default, resolve the one Grand Sport `generation_action` row directly, regenerate/compare runtime contracts, and explicitly leave `body_style_scope` and `runtime_action` untouched?
