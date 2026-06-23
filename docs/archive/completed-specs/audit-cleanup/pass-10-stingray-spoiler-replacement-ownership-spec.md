# Pass 10 — Stingray Spoiler Replacement Ownership Spec

Status: Completed implementation on 2026-06-22.
Date: 2026-06-22
Recommended reasoning level for implementation agent: high.
Source report: `docs/audit-cleanup/pass-8-direct-rule-field-classification-report.md`.
Previous pass: `docs/audit-cleanup/pass-9-body-style-scope-retirement-spec.md`.

## Goal

Retire the redundant active Stingray high-wing spoiler direct replacement rows whose behavior is already owned by the workbook-authored `grp_spoiler_high_wing` exclusive group, while explicitly preserving the two product-decision edges that are not safe group-owned cleanup yet.

This is Candidate B from the Pass 8 report. It is a narrow Stingray workbook/source-data cleanup plus generated-artifact and test refresh. It is not a Grand Sport/Z06 replacement migration and not a direct-rule runtime semantics pass.

## Diagnosis

Change type for this spec: docs-only.

Change type for implementation: mixed workbook/data + generated artifacts + tests. Risk level: medium.

Root cause: `rule_mapping` still carries five Stingray `runtime_action=replace` rows that remove `opt_t0a_001` / T0A when a spoiler source is selected. Three active/selectable sources (`opt_5zu_001`, `opt_5zz_001`, `opt_tvs_001`) already share `grp_spoiler_high_wing` with T0A. That exclusive group is the workbook-owned peer-selection mechanism and runtime already removes selected peers generically. Keeping both the exclusive group and direct replace rows duplicates ownership for the same active same-section spoiler peer replacement.

Two rows are not equivalent cleanup:

- `opt_5zw_001` / 5ZW is inactive and is not currently a member of `grp_spoiler_high_wing`. Removing its direct replacement row would silently decide future 5ZW activation behavior.
- `opt_zf1_001` / ZF1 is active/selectable but is not in `grp_spoiler_high_wing`; it has separate Z51 dependency/default-removal behavior. Removing or grouping it would be a product decision, not duplicate cleanup.

Evidence inspected:

- `docs/audit-cleanup/pass-8-direct-rule-field-classification-report.md:65` classifies the current Stingray `runtime_action=replace` rows.
- `docs/audit-cleanup/pass-8-direct-rule-field-classification-report.md:151` defines Candidate B scope and required proof.
- Current read-only workbook probe confirmed the five candidate rows in `rule_mapping`:
  - row 51: `rule_opt_5zu_001_excludes_opt_t0a_001`, `opt_5zu_001` excludes `opt_t0a_001`, `runtime_action=replace`.
  - row 52: `rule_opt_5zw_001_excludes_opt_t0a_001`, `opt_5zw_001` excludes `opt_t0a_001`, `runtime_action=replace`.
  - row 53: `rule_opt_5zz_001_excludes_opt_t0a_001`, `opt_5zz_001` excludes `opt_t0a_001`, `runtime_action=replace`.
  - row 134: `rule_opt_zf1_001_excludes_opt_t0a_001`, `opt_zf1_001` excludes `opt_t0a_001`, `runtime_action=replace`.
  - row 141: `rule_opt_tvs_001_excludes_opt_t0a_001`, `opt_tvs_001` excludes `opt_t0a_001`, `runtime_action=replace`.
- Current read-only workbook probe confirmed `stingray_options` status:
  - 5ZU, 5ZZ, TVS, T0A, and ZF1 are active/selectable in `sec_spoi_001`.
  - 5ZW is inactive/selectable in `sec_spoi_001`.
- Current read-only workbook probe confirmed `exclusive_groups` / `exclusive_group_members`:
  - `grp_spoiler_high_wing` is active with `selection_mode=single_within_group`.
  - Members are `opt_t0a_001`, `opt_tvs_001`, `opt_5zz_001`, and `opt_5zu_001`.
  - 5ZW and ZF1 are not members.
- `tests/stingray-form-regression.test.mjs:430` already asserts the spoiler exclusive group membership.
- `tests/stingray-form-regression.test.mjs:441` already asserts the exclusive group removes selected spoiler peers.
- `tests/stingray-form-regression.test.mjs:1924` covers ZF1/Z51/T0A replacement behavior.
- `tests/stingray-form-regression.test.mjs:2266` currently locks all five direct replacement rows and must be updated if this pass is implemented.

Current working tree note:

- Implementation preflight `git status --short --branch` reported a clean working tree on branch `schema-ingestion-normalization`.

## Ownership decisions for this pass

### Migrate to existing exclusive-group ownership

Delete these direct replace rows from `rule_mapping` after preflight identity proof:

| current row | rule_id | source | target | current runtime_action | canonical owner after pass |
|---:|---|---|---|---|---|
| 51 | `rule_opt_5zu_001_excludes_opt_t0a_001` | `opt_5zu_001` / 5ZU | `opt_t0a_001` / T0A | replace | `grp_spoiler_high_wing` |
| 53 | `rule_opt_5zz_001_excludes_opt_t0a_001` | `opt_5zz_001` / 5ZZ | `opt_t0a_001` / T0A | replace | `grp_spoiler_high_wing` |
| 141 | `rule_opt_tvs_001_excludes_opt_t0a_001` | `opt_tvs_001` / TVS | `opt_t0a_001` / T0A | replace | `grp_spoiler_high_wing` |

Rationale: all three sources and T0A are active/selectable same-section spoiler peers in the active `single_within_group` exclusive group. Runtime already removes selected peer options through generated exclusive-group metadata.

### Preserve as direct replacement for now

Keep these rows unchanged:

| current row | rule_id | source | target | current runtime_action | reason to preserve |
|---:|---|---|---|---|---|
| 52 | `rule_opt_5zw_001_excludes_opt_t0a_001` | `opt_5zw_001` / 5ZW | `opt_t0a_001` / T0A | replace | 5ZW is inactive and not a current group member; deleting it would decide future activation behavior without product evidence. |
| 134 | `rule_opt_zf1_001_excludes_opt_t0a_001` | `opt_zf1_001` / ZF1 | `opt_t0a_001` / T0A | replace | ZF1 is a Z51 dependency/default-removal edge, not a proven high-wing peer-group duplicate. |

Do not add 5ZW or ZF1 to `grp_spoiler_high_wing` in this pass.

## Exact files/sheets/artifacts to change if approved

Source workbook:

- `stingray_master.xlsx`
  - `rule_mapping`

Generated artifacts expected to refresh:

- `form-output/runtime/stingray-runtime-contract.json`
- `form-output/stingray-form-data.json`
- `form-output/stingray-form-data.csv`
- `form-app/data.js`

Tests expected to change:

- `tests/stingray-form-regression.test.mjs`

Docs/status closure to update after implementation:

- `docs/audit-cleanup/pass-10-stingray-spoiler-replacement-ownership-spec.md`
- `docs/Audit-route-map.md`

Do not change in this pass:

- `form-app/app.js`
- `scripts/corvette_form_generator/*`
- `grandSport_rule_mapping`
- `z06_rule_mapping`
- `grandSport_exclusive_groups` / `grandSport_exclusive_members`
- `z06_exclusive_groups` / `z06_exclusive_members`
- `default_selection_rules`
- `runtimeRuleExceptions`
- `rule_groups` / `rule_group_members`
- dealer submission code, endpoint, payload shape, or Turnstile behavior

## Constraints

- Visual preservation: no UI/HTML/CSS/runtime-rendering changes.
- No refactor.
- No new dependencies.
- Workbook remains source of truth; delete source rows only after proving the existing workbook exclusive group owns the behavior.
- Use `save_workbook_safely()` and verify workbook saved on disk.
- Close/avoid Excel. Stop if `~$stingray_master.xlsx` exists.
- Do not hand-edit generated artifacts; regenerate from workbook source.
- Do not change direct-rule runtime matching or `scopeMatches()` semantics.
- Do not delete the `runtime_action` column.
- Do not trim generated `rules.runtime_action` payload shape.
- Do not change `body_style_scope`; Candidate A/Pass 9 already retired current active source values.
- Do not bundle Candidate C/D/E from the Pass 8 report.
- Do not decide 5ZW or ZF1 ownership beyond explicitly preserving them.

## Implementation plan completed

1. Preflight.

   ```sh
   cd /Users/seandm/Projects/27vette
   git status --short --branch
   test ! -e './~$stingray_master.xlsx'
   .venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
   ```

   Before editing, inspect dirty files and confirm no unrelated user changes overlap approved implementation paths. If unrelated dirty files exist, leave them untouched and report them in the handoff.

2. Snapshot current generated Stingray artifacts.

   ```sh
   mkdir -p /tmp/27vette-pass10-before
   cp form-output/runtime/stingray-runtime-contract.json /tmp/27vette-pass10-before/
   cp form-output/stingray-form-data.json /tmp/27vette-pass10-before/
   cp form-app/data.js /tmp/27vette-pass10-before/data.js
   ```

3. Read-only confirm candidate row identity before workbook write.

   For every listed row, assert:

   - `rule_id`
   - `source_id`
   - `rule_type=excludes`
   - `target_id=opt_t0a_001`
   - `runtime_action=replace`
   - blank `body_style_scope`

   Also assert:

   - `opt_5zu_001`, `opt_5zz_001`, `opt_tvs_001`, and `opt_t0a_001` are active/selectable in `stingray_options`.
   - `grp_spoiler_high_wing` is active and contains exactly `opt_t0a_001`, `opt_tvs_001`, `opt_5zz_001`, and `opt_5zu_001` in the current order.
   - `opt_5zw_001` remains inactive and is not a member of `grp_spoiler_high_wing`.
   - `opt_zf1_001` remains active/selectable and is not a member of `grp_spoiler_high_wing`.

4. Apply workbook edit through safe-save helper.

   - Delete only these `rule_mapping` rows:
     - `rule_opt_5zu_001_excludes_opt_t0a_001`
     - `rule_opt_5zz_001_excludes_opt_t0a_001`
     - `rule_opt_tvs_001_excludes_opt_t0a_001`
   - Preserve rows:
     - `rule_opt_5zw_001_excludes_opt_t0a_001`
     - `rule_opt_zf1_001_excludes_opt_t0a_001`
   - Preserve table refs and unrelated row order/values.
   - Do not create a committed one-off apply script unless needed for review; delete it before handoff if created.

5. Verify workbook on disk.

   - Reopen with `openpyxl` read-only.
   - Assert deleted rule IDs are absent from `rule_mapping`.
   - Assert preserved 5ZW and ZF1 rows remain unchanged.
   - Assert `grp_spoiler_high_wing` membership unchanged.
   - Assert no Grand Sport or Z06 direct-rule rows changed.

6. Regenerate affected artifacts.

   ```sh
   .venv/bin/python scripts/generate_form.py --model stingray
   .venv/bin/python scripts/generate_registry.py
   ```

   Do not regenerate Grand Sport or Z06 unless a validation failure proves the registry requires it. If registry generation touches only `form-app/data.js` with Stingray changes embedded, that is expected.

7. Compare generated contracts.

   Use a focused Node diff because the intended row deletion changes rule counts and `form-app/data.js` embeds registry timestamps/data.

   Allow only:

   - Stingray runtime rule count decreases by 3.
   - `runtime_action=replace` count decreases by 3.
   - Removed rule IDs are exactly:
     - `rule_opt_5zu_001_excludes_opt_t0a_001`
     - `rule_opt_5zz_001_excludes_opt_t0a_001`
     - `rule_opt_tvs_001_excludes_opt_t0a_001`
   - Existing `grp_spoiler_high_wing` generated metadata remains unchanged.
   - Preserved direct replacement rows remain present for 5ZW and ZF1.
   - Timestamp fields may change.

   Any other contract delta is a stop condition.

8. Update focused tests.

   In `tests/stingray-form-regression.test.mjs`:

   - Keep or strengthen the `grp_spoiler_high_wing` membership assertion.
   - Keep runtime behavior coverage proving selecting 5ZU/5ZZ/TVS removes T0A through exclusive-group peer removal.
   - Replace the old assertion that all five spoiler sources have direct replace rows with:
     - no direct `source -> opt_t0a_001` replace rows for 5ZU, 5ZZ, or TVS;
     - direct replace rows still present for 5ZW and ZF1;
     - compute/runtime behavior still keeps T0A removed when Z51 + 5ZZ/5ZU/TVS path applies.
   - Keep ZF1/Z51 test coverage intact.

9. Run targeted gates.

   ```sh
   .venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
   .venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
   node --test tests/stingray-form-regression.test.mjs
   node --test tests/multi-model-runtime-switching.test.mjs
   ```

   Add this optional guard if generated delta review is unclear:

   ```sh
   node --test tests/stingray-generator-stability.test.mjs
   ```

10. Review diff.

    - Confirm workbook diff is limited to the three deleted Stingray rule rows.
    - Confirm generated artifacts show only approved Stingray rule deletions plus timestamps/registry embedding.
    - Confirm `form-app/app.js` unchanged.
    - Confirm Grand Sport/Z06 generated model behavior unchanged in `form-app/data.js` except registry timestamp/container churn.
    - Confirm no dealer submission code changed.

11. Close spec/status docs.

    - Update this spec to completed with date, workbook sheets/artifacts/tests changed, gate results, residual risks, and next pass.
    - Update `docs/Audit-route-map.md` so Candidate B no longer appears pending.

## Expected behavior impact

Intended customer-facing behavior impact: none for active 5ZU/5ZZ/TVS spoiler selection.

Why no behavior change is expected:

- 5ZU, 5ZZ, TVS, and T0A are already generated members of `grp_spoiler_high_wing`.
- Runtime already calls generic exclusive-group peer removal when a grouped choice is selected.
- Existing tests already prove selecting 5ZU/5ZZ/TVS removes T0A from selected/userSelected via the exclusive group.
- ZF1 and 5ZW direct replacement behavior is preserved.

Approved generated contract impact:

- Stingray generated rule count should drop by 3.
- Stingray `runtime_action=replace` count should drop by 3.
- Generated exclusive group metadata should remain unchanged.
- Timestamp fields may change.

Any broader delta is a stop condition.

## Risks

- Direct `runtime_action=replace` may currently affect an auto-added/default T0A path not covered by simple manual peer selection; tests must cover Z51/default/auto-added contexts before row deletion is accepted.
- Removing rows can expose stale tests that treated direct replacement rows as the owner rather than generated exclusive-group metadata.
- `form-app/data.js` embeds all promoted models; registry generation may include timestamp/container churn that needs focused diff review.
- The inactive 5ZW row is easy to misclassify as dead cleanup; preserving it avoids silently losing future activation behavior.
- ZF1 may look like another spoiler peer but has separate Z51 dependency/default-removal behavior; preserve it unless a later product decision approves migration.
- Workbook table refs can drift if row deletion is not done through safe workbook helpers.

## Non-goals

- No Grand Sport replacement cleanup.
- No Z06 replacement cleanup.
- No FEY/FEB/JX6/J56/T0E package/default migration.
- No NWI/NGA exhaust default replacement migration.
- No ZF1 migration to `grp_spoiler_high_wing`.
- No 5ZW activation or group membership decision.
- No direct-rule `scopeMatches()` runtime change.
- No `runtime_action` column deletion.
- No generated payload schema trim.
- No UI styling, layout, or visual change.
- No dealer submission change.

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
.venv/bin/python scripts/generate_registry.py
```

Runtime/model tests:

```sh
node --test tests/stingray-form-regression.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Optional if focused diff or generator stability is unclear:

```sh
node --test tests/stingray-generator-stability.test.mjs
```

Diff/status checks:

```sh
git diff --check
git status --short
```

## Completion summary

Completed on 2026-06-22.

Workbook source changes:

- `stingray_master.xlsx` / `rule_mapping`: deleted three redundant active Stingray high-wing direct replacement rows now owned by `grp_spoiler_high_wing`:
  - `rule_opt_5zu_001_excludes_opt_t0a_001`
  - `rule_opt_5zz_001_excludes_opt_t0a_001`
  - `rule_opt_tvs_001_excludes_opt_t0a_001`
- `stingray_master.xlsx` / `rule_mapping`: preserved the 5ZW and ZF1 direct replacement rows unchanged:
  - `rule_opt_5zw_001_excludes_opt_t0a_001`
  - `rule_opt_zf1_001_excludes_opt_t0a_001`
- Workbook backup created by safe-save: `backups/stingray_master-20260622-130954.xlsx`.

Generated artifacts refreshed:

- `form-output/runtime/stingray-runtime-contract.json`
- `form-output/stingray-form-data.json`
- `form-output/stingray-form-data.csv`
- `form-app/data.js`

Tests updated:

- `tests/stingray-form-regression.test.mjs`: spoiler replacement ownership test now asserts 5ZU/5ZZ/TVS no longer carry direct T0A replace rows, 5ZW/ZF1 still do, and 5ZU/5ZZ/TVS still remove selected T0A through `grp_spoiler_high_wing`.

Approved generated deltas:

- Stingray runtime rule count changed from 144 to 141.
- Stingray `runtime_action=replace` rule count changed from 5 to 2.
- Removed generated rule IDs are exactly the three approved 5ZU/5ZZ/TVS direct T0A replacement rows.
- `grp_spoiler_high_wing` generated metadata remained unchanged.
- 5ZW and ZF1 direct replacement rows remained present.

Changed behavior: intended customer-facing behavior unchanged for active 5ZU/5ZZ/TVS spoiler selection. Runtime code unchanged; generated exclusive-group metadata now solely owns those peer replacements.

Validation results:

- Implementation preflight clean tree / branch check — passed on `schema-ingestion-normalization`.
- Excel lock check — passed; `~$stingray_master.xlsx` absent.
- `.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx` — passed before and after workbook write.
- Strong row-identity preflight — passed for every listed row (`rule_id`, `source_id`, `rule_type`, `target_id`, `runtime_action`, `body_style_scope`) plus option/group ownership assertions.
- On-disk workbook verification — passed; `rule_mapping` has 141 rows, 2 `runtime_action=replace` rows, preserved 5ZW/ZF1 rows unchanged, spoiler exclusive-group membership unchanged, and Grand Sport/Z06 replacement counts unchanged.
- `.venv/bin/python scripts/generate_form.py --model stingray` — passed, 141 rules, 0 validation errors.
- `.venv/bin/python scripts/generate_registry.py` — passed, models `stingray`, `grandSport`, `z06`.
- Focused runtime-contract delta script — passed with only approved Stingray rule deletions/count deltas.
- `.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx` — passed.
- `node --test tests/stingray-form-regression.test.mjs` — passed.
- `node --test tests/multi-model-runtime-switching.test.mjs` — passed.

Residual risks:

- No browser smoke was run; Node runtime/model gates covered the generated exclusive-group behavior and dealer payload boundaries.
- 5ZW and ZF1 remain direct replacement rows intentionally; their ownership still needs a later product decision or narrower pass.

Recommended next pass: Candidate C from the Pass 8 report — Grand Sport package/default replacement ownership for FEY/FEB relationships to T0E, JX6, and J56. Keep NWI/NGA exhaust replacement and Z06 brake/default replacement separate.

## Historical approval prompt

Pass 10 / Candidate B implementation was approved on 2026-06-22.

Approval authorized only:

- deleting the three active high-wing peer duplicate direct replace rows for 5ZU, 5ZZ, and TVS from `rule_mapping`;
- preserving the 5ZW and ZF1 direct replace rows;
- regenerating Stingray runtime artifacts and registry;
- updating focused tests only for intentional ownership migration from direct replace rows to `grp_spoiler_high_wing`;
- closing this spec and route-map status.

Approval did not authorize Grand Sport/Z06 replacement cleanup, ZF1 migration, 5ZW activation/group membership changes, direct-rule runtime matching changes, `runtime_action` column deletion, generated payload schema trimming, or dealer submission changes.
