# Pass C Spec — Runtime-Skipped Rule Row Deletion

## Status

Completed. This pass follows the user correction: delete all rule rows that current runtime generation skips, use the inventory for rollback/evidence only, and restore only rows with proven runtime-contract impact.

Implementation result: 288 runtime-skipped rows were deleted from `rule_mapping` and `grandSport_rule_mapping`; no `z06_rule_mapping` rows matched the skip predicate; before/after runtime contract comparisons matched for Stingray, Grand Sport, and Z06, so no rows were restored.

## Diagnosis

Pass B classified stale executable entrypoints. That missed the real cleanup target: workbook rule rows that exist mainly so generator/audit code can recognize, skip, count, and test them.

Root cause: older normalization kept dead rule rows in `rule_mapping` / `grandSport_rule_mapping` with lifecycle markers such as `generation_action=omit*` and `normalization_status=omitted|replaced`. Current generation already treats those rows as non-runtime rows, but tests and audit artifacts still preserve the accounting layer.

This pass changes the convention:

- Old convention: preserve skipped rule rows with `normalization_status` / `generation_action` metadata.
- New convention: delete rule rows that current runtime generation skips, unless a before/after runtime-contract comparison proves a specific row was still consumed.

Risk level: High, because this writes `stingray_master.xlsx` and regenerates runtime artifacts. The safety gate is contract comparison, not preserving ambiguous provenance rows.

Change type: mixed workbook/data + editor warning + tests + generated artifacts + docs. Intended runtime behavior impact: none.

## Verified evidence

- `scripts/corvette_form_generator/rules.py:18` defines `runtime_authored_rule(row)`:
  - `normalization_status in {"omitted", "replaced"}` returns false.
  - `generation_action` starting with `omit` returns false.
- `scripts/corvette_form_generator/rules.py:137` skips rows where `runtime_authored_rule(row)` is false.
- `scripts/corvette_form_generator/rules.py:139` skips runtime-authored direct `requires` rows when the source/target pair is already represented by grouped `requires_any` metadata.
- `scripts/corvette_form_generator/rules.py:141` skips runtime-authored direct `excludes` rows when the source/target pair is already represented by grouped `excludes_any` metadata, unless the row carries runtime semantics that prevent dedupe under current code.
- `scripts/build_rule_sources.py:936` writes audit JSON/Markdown artifacts under `form-output/inspection/`; it does not write workbook source rows or runtime app data.
- `tests/grand-sport-rule-audit.test.mjs:98` asserts workbook/audit/draft counts, including omitted-row accounting.
- `tests/grand-sport-rule-audit.test.mjs:143` asserts a specific omitted duplicate row remains visible in the audit.
- `scripts/corvette_form_generator/editor_ops.py:567` currently warns that the repo convention for rules is `normalization_status`, not deletion. That warning is now stale and must be updated.

Read-only workbook counts at spec time:

```text
rule_mapping:
  total rows: 238
  rows where runtime_authored_rule(row) is false: 88
  runtime-authored rows before grouped-rule dedupe: 150

grandSport_rule_mapping:
  total rows: 323
  rows where runtime_authored_rule(row) is false: 195
  runtime-authored rows before grouped-rule dedupe: 128

z06_rule_mapping:
  total rows: 55
  rows where runtime_authored_rule(row) is false: 0
  runtime-authored rows before grouped-rule dedupe: 55
```

## Required deletion policy

Delete every row from `rule_mapping` and `grandSport_rule_mapping` that current runtime rule generation skips.

Deletion targets:

1. All rows where `runtime_authored_rule(row)` is false.
   - Includes `normalization_status=omitted`.
   - Includes `normalization_status=replaced`.
   - Includes any `generation_action` value that starts with `omit`.
   - No exception for historical/audit provenance.
2. Any runtime-authored direct rule row that `build_draft_rules(...)` still skips because grouped-rule dedupe already represents it.
   - Direct `requires` row skipped because `(source_id, target_id)` is in active grouped `requires_any` pairs.
   - Direct `excludes` row skipped because `(source_id, target_id)` is in active grouped `excludes_any` pairs under the exact current generator conditions.
3. Do not delete rows from `z06_rule_mapping` in this pass unless the same runtime-skipped predicate finds one there during implementation. Current evidence says it should find zero.

Restoration policy:

- If deleting a row changes a generated runtime contract beyond timestamps/generated metadata, restore that specific row and document why current generation was still consuming it.
- Do not preserve ambiguous rows before comparison.
- The inventory is for rollback and evidence, not for deciding to keep historical/audit rows.

## Exact workbook sheets to inspect/write

Primary delete targets:

- `rule_mapping`
- `grandSport_rule_mapping`

Control/reference:

- `z06_rule_mapping`

Grouped-rule and exclusive metadata needed to calculate current skip predicates:

- `rule_groups`
- `rule_group_members`
- `exclusive_groups`
- `exclusive_group_members`
- `grandSport_rule_groups`
- `grandSport_rule_group_members`
- `grandSport_exclusive_groups`
- `grandSport_exclusive_members`
- `z06_rule_groups`
- `z06_rule_group_members`
- `z06_exclusive_groups`
- `z06_exclusive_members`

Context sheets for source/target validation and report labels:

- `stingray_options`
- `stingray_ovs`
- `grandSport_options`
- `grandSport_ovs`
- `z06_options`
- `z06_ovs`
- `variant_master`
- `model_master`
- `model_workbook_sources`

Excel table handling:

- `rule_mapping` has table `tbl_stingray_rule_mapping`.
- `grandSport_rule_mapping` has table `tbl_gs_rule_mapping`.
- `z06_rule_mapping` currently has no table object.
- After row deletion, refresh table refs for table-backed sheets to `ws.dimensions` before safe-save.

## Exact files likely to change

Workbook:

- `stingray_master.xlsx`

Editor warning:

- `scripts/corvette_form_generator/editor_ops.py`
  - Update the referenced-delete warning around line 567 so it no longer says repo convention is `normalization_status`, not deletion.
  - New message should reflect the new convention: runtime-skipped rule rows should be deleted when their runtime contract impact is proven absent; referenced deletes still require review because active references can change generated behavior.

Tests:

- `tests/grand-sport-rule-audit.test.mjs`
  - Remove/rewrite assertions that protect omitted-row counts or the presence of specific omitted rows.
- `tests/workbook-schema-standardization.test.mjs`
  - Update any lifecycle-normalization assertions that assume omitted/replaced rule rows are a valid steady-state convention.
  - Prefer a guard that current promoted/source rule sheets do not contain runtime-skipped rule rows after Pass C, except any explicitly restored rows documented with proven runtime impact.
- `tests/stingray-generator-stability.test.mjs`
  - Inspect/update if row-count/header assumptions fail after deletion.
- `tests/grand-sport-draft-data.test.mjs`
  - Inspect/update only if existing assertions mention omit/generation lifecycle rows.
- Editor tests if warning text is asserted:
  - `tests/test_editor_ops_apply.py`
  - `tests/test_editor_server_payload.py`
  - `tests/test_editor_server_write_api.py`

Audit/report code:

- `scripts/build_rule_sources.py`
  - Update only as needed after deleted skipped rows remove omitted-row sections/counts.
  - Do not keep skipped-row accounting alive merely for audit output.

Generated artifacts after regeneration:

- `form-output/stingray-form-data.json`
- `form-output/stingray-form-data.csv`
- `form-app/data.js`
- `form-output/inspection/grand-sport-contract-preview.json`
- `form-output/inspection/grand-sport-form-data-draft.json`
- `form-output/inspection/grand-sport-runtime-contract.json`
- `form-output/inspection/grand-sport-rule-audit.json`
- `form-output/inspection/grand-sport-rule-audit.md`
- `form-output/inspection/z06-*` as control/timestamp-only artifacts if regenerated
- generated workbook `form_*` sheets from Stingray generation

Docs:

- `docs/audit-cleanup/pass-c-dead-end-rule-row-retirement-spec.md`
- `docs/audit-cleanup/pass-c-rule-row-retirement-inventory.md`
- `docs/audit-cleanup-overview.md`

## Implementation plan

### Step 1 — Snapshot baseline runtime contracts

Before workbook changes, snapshot current runtime contracts to `/tmp/27vette-pass-c-before/`:

```sh
mkdir -p /tmp/27vette-pass-c-before /tmp/27vette-pass-c-after
cp form-output/stingray-form-data.json /tmp/27vette-pass-c-before/stingray-form-data.json
cp form-output/inspection/grand-sport-runtime-contract.json /tmp/27vette-pass-c-before/grand-sport-runtime-contract.json
cp form-output/inspection/z06-runtime-contract.json /tmp/27vette-pass-c-before/z06-runtime-contract.json
```

If `form-app/data.js` changes after Stingray regeneration, structurally extract `window.CORVETTE_FORM_DATA` before/after and compare while ignoring timestamp fields.

### Step 2 — Build deletion inventory for rollback/evidence

Generate `docs/audit-cleanup/pass-c-rule-row-retirement-inventory.md` before deleting rows.

For each target row, record:

- sheet
- Excel row number before deletion
- `rule_id`
- `source_id`
- `rule_type`
- `target_id`
- `generation_action`
- `normalization_status`
- `runtime_action`
- skip reason:
  - `runtime_authored_rule_false`
  - `grouped_requires_any_dedupe`
  - `grouped_excludes_any_dedupe`
- raw row values needed for restoration

Inventory action is always `delete` for runtime-skipped rows. It is not a keep/defer review matrix.

Also record rows restored after contract comparison, if any, with the exact contract diff that proved runtime impact.

### Step 3 — Delete all runtime-skipped rows

Use a temporary execution snippet or throwaway script, not a committed one-pass writer.

Required mechanics:

- Refuse to run if `~$stingray_master.xlsx` exists.
- Load `stingray_master.xlsx` with `openpyxl`.
- Compute active grouped `requires_any` and `excludes_any` pairs from the workbook, matching current generator semantics.
- Compute deletion set for `rule_mapping` and `grandSport_rule_mapping`:
  1. `runtime_authored_rule(row)` is false.
  2. OR row is runtime-authored but current `build_draft_rules(...)` grouped-rule dedupe would skip it.
- Delete matching rows bottom-up per sheet.
- Refresh Excel table refs for `rule_mapping` and `grandSport_rule_mapping`.
- Save with `save_workbook_safely()`.
- Reopen the workbook and verify:
  - deleted `rule_id`s are absent.
  - non-deleted runtime-authored rows remain.
  - `z06_rule_mapping` remains unchanged unless deletion predicate found a skipped row there.
  - table refs match sheet dimensions.

### Step 4 — Update editor warning

Patch `scripts/corvette_form_generator/editor_ops.py` around line 567.

The warning should no longer encode the old convention:

```text
(repo convention for rules is normalization_status, not deletion)
```

Replace it with wording aligned to the new convention. Example intent:

```text
(rule deletes are allowed for runtime-skipped rows after contract comparison; active references still require review)
```

Exact phrasing can differ, but it must not instruct users to preserve rule rows via `normalization_status` instead of deleting them.

### Step 5 — Regenerate affected outputs

Run:

```sh
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_form.py --model z06
```

Grand Sport and Stingray are affected. Z06 is a control.

### Step 6 — Compare runtime contracts and restore only proven-impact rows

Copy post-regeneration contracts:

```sh
cp form-output/stingray-form-data.json /tmp/27vette-pass-c-after/stingray-form-data.json
cp form-output/inspection/grand-sport-runtime-contract.json /tmp/27vette-pass-c-after/grand-sport-runtime-contract.json
cp form-output/inspection/z06-runtime-contract.json /tmp/27vette-pass-c-after/z06-runtime-contract.json
```

Compare:

```sh
node scripts/compare-generated-contracts.mjs /tmp/27vette-pass-c-before/stingray-form-data.json /tmp/27vette-pass-c-after/stingray-form-data.json
node scripts/compare-generated-contracts.mjs /tmp/27vette-pass-c-before/grand-sport-runtime-contract.json /tmp/27vette-pass-c-after/grand-sport-runtime-contract.json
node scripts/compare-generated-contracts.mjs /tmp/27vette-pass-c-before/z06-runtime-contract.json /tmp/27vette-pass-c-after/z06-runtime-contract.json
```

If any comparison differs beyond timestamps/generated metadata:

1. Identify the missing/changed generated rule(s).
2. Map the generated diff back to deleted `rule_id` / source-target row(s).
3. Restore only those specific row(s) from the inventory.
4. Regenerate and re-run contract comparison.
5. Document the restored row(s) and explain why the generator was still consuming them.

Do not restore rows for historical/audit provenance alone.

Expected audit artifact result:

- `grand-sport-rule-audit.json` and `.md` may change substantially.
- Omitted-row sections/counts should shrink or disappear.
- Audit drift is acceptable if runtime contracts match.

### Step 7 — Update tests to match the new convention

Remove/rewrite tests that protect skipped-row accounting:

- `tests/grand-sport-rule-audit.test.mjs:98` should stop requiring omitted-row count math as part of the protected contract.
- `tests/grand-sport-rule-audit.test.mjs:143` should stop requiring a specific omitted duplicate row such as `opt_rik_001 -> opt_rin_001` to remain visible in the audit.
- Any schema-standardization test should stop treating `normalization_status=omitted|replaced` rows as a steady-state rule convention.

Add/update tests that protect the new convention:

- No runtime-skipped rows remain in `rule_mapping` / `grandSport_rule_mapping` after Pass C, except rows explicitly restored due to proven runtime-contract impact.
- Generated runtime rules still match pre-pass contracts.
- Active rule groups and exclusive groups still carry the behavior previously duplicated by skipped direct rows.
- `build_rule_sources.py` remains read-only if it is retained.
- Editor warning no longer instructs users to preserve rule rows via `normalization_status` instead of deletion.

### Step 8 — Decide `build_rule_sources.py` after deletion

After all runtime-skipped rows are deleted and tests are updated:

- Keep `build_rule_sources.py` only if it still provides unique read-only diagnostic signal, such as unresolved RPO mentions or parser/source-review hotspots not covered by generator/runtime/schema tests.
- Move it out of default/live readiness gates if it is only audit/report tooling.
- Retire it and its tests only if remaining assertions duplicate generator/runtime/schema coverage.

This decision should be evidence-based after the workbook cleanup, not based on old skipped-row accounting.

## Constraints

- Delete workbook source rows that runtime generation skips; do not preserve them for historical/audit provenance.
- Use runtime contract comparison as the safety check.
- Restore only rows with proven runtime impact.
- Do not add Python/JS suppression to hide workbook clutter.
- No model/RPO-specific runtime exceptions.
- No visual UI changes.
- No new dependencies.
- No dealer submission endpoint, payload, or Turnstile changes.
- Close Excel before workbook writes; refuse if `~$stingray_master.xlsx` exists.
- Use `save_workbook_safely()` for workbook writes.
- Verify saved workbook rows/table refs on disk after save.
- Treat generated `form_*`, `form-output/*`, and `form-app/data.js` as outputs.
- Do not leave a committed one-pass cleanup writer behind.

## Non-goals

Pass C will not:

- Retire `runtime_steps`, `context_section_master`, `section_presentation`, `context_choice_copy`, `order_summary_sections`, `step_order_summary_map`, `runtime_rule_exceptions`, or `variant_option_overrides`.
- Redesign rule runtime behavior beyond deleting rows current generation already skips.
- Normalize all Z06 rules.
- Change pricing, interiors, colors, assets, or model promotion.
- Promote ZR1/ZR1X.

## Validation plan

Pre-write:

```sh
git status --short --branch
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

After workbook write:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Regenerate and compare:

```sh
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_form.py --model z06
node scripts/compare-generated-contracts.mjs /tmp/27vette-pass-c-before/stingray-form-data.json /tmp/27vette-pass-c-after/stingray-form-data.json
node scripts/compare-generated-contracts.mjs /tmp/27vette-pass-c-before/grand-sport-runtime-contract.json /tmp/27vette-pass-c-after/grand-sport-runtime-contract.json
node scripts/compare-generated-contracts.mjs /tmp/27vette-pass-c-before/z06-runtime-contract.json /tmp/27vette-pass-c-after/z06-runtime-contract.json
```

Targeted tests:

```sh
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/grand-sport-rule-audit.test.mjs
node --test tests/workbook-schema-standardization.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Editor tests if `editor_ops.py` warning behavior is asserted or touched by tests:

```sh
.venv/bin/python -m pytest tests/test_editor_ops_apply.py tests/test_editor_server_payload.py tests/test_editor_server_write_api.py -q
```

Diff review:

```sh
git diff --name-only
git diff --stat
```

Review workbook/generated diffs explicitly. Runtime contracts must match except timestamps/generated metadata after any necessary row restoration.

## Expected outcome

- All rows skipped by current runtime rule generation are removed from `rule_mapping` and `grandSport_rule_mapping`, except any specific row restored due to proven runtime-contract impact.
- No historical/audit-only provenance exception remains.
- Tests no longer protect skipped-row counts or skipped-row presence.
- `editor_ops.py` no longer says rule convention is `normalization_status`, not deletion.
- Generated runtime contracts match before/after except timestamps/generated metadata.
- Audit artifacts may change to reflect the removed dead-end rows.
- `build_rule_sources.py` is reclassified after cleanup based on remaining unique diagnostic value.

## Approval question

Approve this revised Pass C implementation?

Recommended approval wording: `Pass C approved`.
