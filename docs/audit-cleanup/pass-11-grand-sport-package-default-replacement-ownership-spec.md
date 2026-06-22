# Pass 11 — Grand Sport Package/Default Replacement Ownership Spec

Status: Completed implementation on 2026-06-22.
Date: 2026-06-22
Recommended reasoning level for implementation agent: high.
Source report: `docs/audit-cleanup/pass-8-direct-rule-field-classification-report.md`.
Previous related passes:

- `docs/audit-cleanup/pass-9-body-style-scope-retirement-spec.md`
- `docs/audit-cleanup/pass-10-stingray-spoiler-replacement-ownership-spec.md`

## Goal

Retire the Grand Sport direct `runtime_action=replace` rows whose behavior can be owned by workbook-authored package/default metadata for FEY/FEB relationships to T0E, JX6, and J56.

This is Candidate C from the Pass 8 report. It is a narrow Grand Sport workbook/source-data cleanup plus generated-artifact and test refresh. It is not a runtime direct-rule semantics pass, not a `runtime_action` column deletion pass, not the NWI/NGA exhaust pass, and not the Z06 brake/default replacement pass.

## Diagnosis

Change type for the original spec: docs-only.

Change type for implementation: mixed workbook/data + generated artifacts + tests. Risk level: medium-high.

Root cause: `grandSport_rule_mapping` still carries direct `runtime_action=replace` rows for package/default behavior that now has clearer workbook owners:

- Z52 package selection and mutual exclusion is already workbook-owned by `grandSport_exclusive_groups.gs_excl_z52_packages`.
- Brake peer/default ownership is already mostly workbook-owned by `grandSport_exclusive_groups.gs_excl_performance_brakes`, whose active members are JX6, J56, and J57 with `selection_mode=required_single_within_group`.
- J57 already soft-defaults J6D through `default_selection_rules.gs_default_j6d_with_j57`, not through a hard include.
- FEB already includes J56, and FEY already includes J57, T0F, and CFZ through `grandSport_rule_mapping` include rows.
- T0E is currently a default-selected Grand Sport aero row, but Grand Sport has no explicit `default_selection_rules` row or exclusive group for the T0E/T0F aero peers. FEY still needs to remove T0E when it auto-adds/includes T0F.

The implementation should move only proven package/default ownership into workbook metadata and then delete only direct replacement rows whose behavior remains equivalent.

Evidence inspected:

- `docs/audit-cleanup/pass-8-direct-rule-field-classification-report.md:77` classifies the Grand Sport `runtime_action=replace` rows.
- `docs/audit-cleanup/pass-8-direct-rule-field-classification-report.md:163` defines Candidate C scope and required proof.
- `docs/Audit-route-map.md:318` names Candidate C as the recommended next pass after Pass 10.
- Current read-only workbook probe confirmed these relevant `grandSport_options` rows:
  - `opt_t0e_001` / T0E: active/selectable, `sec_perf_aero_001`, `display_behavior=default_selected`, display order 10.
  - `opt_t0f_001` / T0F: active/selectable, `sec_perf_aero_001`, display order 20.
  - `opt_jx6_001` / JX6: active/selectable, `sec_perf_brake_001`, `display_behavior=default_selected`, display order 5.
  - `opt_j56_001` / J56: active, `selectable=False`, `display_behavior=display_only`, `sec_perf_brake_001`, display order 10.
  - `opt_j57_001` / J57: active/selectable, `sec_perf_brake_001`, display order 20.
  - `opt_feb_001` / FEB and `opt_fey_001` / FEY: active/selectable in `sec_perf_z52_001`.
- Current read-only workbook probe confirmed these relevant `grandSport_rule_mapping` rows:
  - `gs_rule_opt_feb_001_includes_opt_j56_001`: FEB includes J56.
  - `gs_rule_opt_fey_001_includes_opt_j57_001`: FEY includes J57.
  - `gs_rule_opt_fey_001_includes_opt_t0f_001`: FEY includes T0F.
  - `gs_rule_opt_fey_001_includes_opt_cfz_001`: FEY includes CFZ.
  - `gs_rule_opt_t0f_001_includes_opt_cfz_001`: T0F includes CFZ.
  - `gs_rule_opt_t0f_001_requires_opt_j57_001`: T0F requires J57.
  - `gs_rule_opt_j57_001_excludes_opt_j6a_001_replace`: J57 replaces default caliper J6A. This is outside Candidate C and must remain.
  - `gs_rule_opt_fey_001_excludes_opt_t0e_001_replace`: FEY replaces T0E.
  - `gs_rule_opt_feb_001_excludes_opt_jx6_001_replace`: FEB replaces JX6.
  - `gs_rule_opt_fey_001_excludes_opt_jx6_001_replace`: FEY replaces JX6.
  - `gs_rule_opt_fey_001_excludes_opt_j56_001_replace`: FEY replaces J56.
  - `gs_rule_opt_nwi_001_excludes_opt_nga_001_replace`: NWI replaces NGA. This is Candidate D and must remain.
- Current read-only workbook probe confirmed these relevant exclusive groups:
  - `gs_excl_z52_packages`: active `single_within_group`, members `opt_feb_001`, `opt_fey_001`.
  - `gs_excl_performance_brakes`: active `required_single_within_group`, members `opt_jx6_001`, `opt_j56_001`, `opt_j57_001`.
  - No current Grand Sport aero exclusive group exists for T0E/T0F.
- Current read-only workbook probe confirmed these relevant `default_selection_rules` rows:
  - `gs_default_j6d_with_j57`: J57 soft-defaults J6D when J57 is selected/included unless the caliper section already has a user-selected choice.
  - `gs_default_nga_unless_nwi`: NGA exhaust default. Candidate D, not this pass.
  - `gs_default_bc7_coupe`: BC7 coupe default. Not this pass.
  - No Grand Sport T0E default rule currently exists.
  - No Grand Sport JX6 default rule currently exists.
- `tests/grand-sport-draft-data.test.mjs:369` currently expects the FEY/T0E direct replace row in the deterministic rule-key list.
- `tests/grand-sport-draft-data.test.mjs:532` currently asserts J56 display-only shape and still expects the FEB/JX6, FEY/JX6, and FEY/J56 direct replace rows.
- `tests/grand-sport-draft-data.test.mjs:610` already asserts J57 does not hard-include J6D and `gs_default_j6d_with_j57` owns the caliper soft default.
- `tests/multi-model-runtime-switching.test.mjs:190` currently lists Grand Sport exclusive groups and will need an expected group update if this pass adds an aero group.
- `form-app/app.js:1526` still removes direct replacement targets through `removeReplaceRuleTargets()`.
- `form-app/app.js:1628` has generic included-target exclusive peer reconciliation for generated exclusive-group metadata.
- `form-app/app.js:1542` applies generated workbook default-selection rules.

Current working tree note:

- Implementation preflight must re-run `git status --short --branch`. Initial spec-writing preflight saw branch `schema-ingestion-normalization`; dirty state must be rechecked before any implementation edits.

## Ownership decisions for this pass

### Migrate T0E replacement to Grand Sport aero default/group ownership

Target decision:

- Add a Grand Sport-specific default-selection row for T0E:
  - `model_key=grand_sport`
  - `rule_id=gs_default_t0e`
  - `target_option_id=opt_t0e_001`
  - `condition_type=unless_selected_section`
  - `condition_id=sec_perf_aero_001`
  - wildcard body/trim/variant scopes
  - active True
- Add a Grand Sport-specific aero exclusive group if preflight confirms current runtime needs explicit exclusive-group metadata to remove a user-selected T0E when FEY includes T0F:
  - `group_id=gs_excl_performance_aero`
  - `selection_mode=required_single_within_group`
  - active True
  - members in display order: `opt_t0e_001`, `opt_t0f_001`

Then delete this direct replace row only after parity proof:

| current workbook row from probe | rule_id | source | target | current runtime_action | canonical owner after pass |
|---:|---|---|---|---|---|
| 97 | `gs_rule_opt_fey_001_excludes_opt_t0e_001_replace` | `opt_fey_001` / FEY | `opt_t0e_001` / T0E | replace | `gs_default_t0e` plus `gs_excl_performance_aero` and existing FEY -> T0F include |

Rationale: FEY includes T0F. T0F and T0E are the active Grand Sport aero choices in `sec_perf_aero_001`; T0E is the default choice. The workbook should express T0E restoration/defaulting and T0F/T0E peer replacement through default/exclusive metadata, not a FEY-specific direct replacement row.

### Migrate JX6/J56 package brake replacement to existing brake group ownership

Target decision:

- Keep `gs_excl_performance_brakes` active with `selection_mode=required_single_within_group`.
- Keep members exactly `opt_jx6_001`, `opt_j56_001`, and `opt_j57_001` in the current order unless preflight proves the workbook has already changed.
- Add a Grand Sport-specific JX6 default-selection row only if runtime parity tests prove explicit default restoration is needed beyond the source row's `display_behavior=default_selected`:
  - recommended `rule_id=gs_default_jx6`
  - `target_option_id=opt_jx6_001`
  - `condition_type=unless_selected_section`
  - `condition_id=sec_perf_brake_001`
  - wildcard body/trim/variant scopes
  - active True
- Preserve FEB -> J56 include and FEY -> J57 include rows.

Delete these direct replace rows only after parity proof:

| current workbook row from probe | rule_id | source | target | current runtime_action | canonical owner after pass |
|---:|---|---|---|---|---|
| 117 | `gs_rule_opt_feb_001_excludes_opt_jx6_001_replace` | `opt_feb_001` / FEB | `opt_jx6_001` / JX6 | replace | existing FEB -> J56 include plus `gs_excl_performance_brakes` required group and optional `gs_default_jx6` |
| 118 | `gs_rule_opt_fey_001_excludes_opt_jx6_001_replace` | `opt_fey_001` / FEY | `opt_jx6_001` / JX6 | replace | existing FEY -> J57 include plus `gs_excl_performance_brakes` required group and optional `gs_default_jx6` |
| 119 | `gs_rule_opt_fey_001_excludes_opt_j56_001_replace` | `opt_fey_001` / FEY | `opt_j56_001` / J56 | replace | existing FEY -> J57 include plus `gs_excl_performance_brakes`; J56 remains FEB's display-only included brake member |

Rationale: JX6/J56/J57 are already workbook-authored required brake peers. FEB includes J56, FEY includes J57, and the active required exclusive group is the canonical owner for peer replacement. J56 is not a customer-selectable standalone card; it remains a display-only brake member included by FEB and replaced by J57/FEY through group semantics, not by a FEY-specific direct replace row.

### Preserve direct replacement rows outside Candidate C

Keep these rows unchanged:

| rule_id | reason to preserve |
|---|---|
| `gs_rule_opt_j57_001_excludes_opt_j6a_001_replace` | Cross-section brake/caliper default replacement. J57/J6D soft default exists, but J6A removal is still a separate caliper default edge and is not part of FEY/FEB package replacement cleanup. |
| `gs_rule_opt_nwi_001_excludes_opt_nga_001_replace` | Candidate D exhaust default replacement. It needs a separate NWI/NGA ownership proof and must not be bundled here. |

Do not change Z06 replacement rows, Stingray replacement rows, direct-rule runtime matching, or generated `runtime_action` payload semantics in this pass.

## Exact files/sheets/artifacts to change if approved

Source workbook:

- `stingray_master.xlsx`
  - `grandSport_rule_mapping`
  - `grandSport_exclusive_groups` only if adding `gs_excl_performance_aero`
  - `grandSport_exclusive_members` only if adding `gs_excl_performance_aero`
  - `default_selection_rules`

Generated artifacts expected to refresh:

- `form-output/runtime/grand-sport-runtime-contract.json`
- `form-output/grand-sport-form-data.json`
- `form-output/grand-sport-form-data.csv`
- `form-app/data.js`

Tests expected to change:

- `tests/grand-sport-draft-data.test.mjs`
- `tests/grand-sport-contract-preview.test.mjs` only if preview counts or expected group inventory change
- `tests/multi-model-runtime-switching.test.mjs`

Docs/status closure to update after implementation:

- `docs/audit-cleanup/pass-11-grand-sport-package-default-replacement-ownership-spec.md`
- `docs/Audit-route-map.md`

Do not change in this pass:

- `form-app/app.js`
- `scripts/corvette_form_generator/*`
- `rule_mapping`
- `z06_rule_mapping`
- Stingray/Z06 exclusive groups or default-selection rows
- `runtimeRuleExceptions`
- `runtime_action` workbook columns
- generated rule payload field names
- direct-rule `scopeMatches()` / body-style semantics
- dealer submission code, endpoint, payload shape, or Turnstile behavior

## Constraints

- Visual preservation: no UI/HTML/CSS/runtime-rendering changes.
- No refactor.
- No new dependencies.
- Workbook remains source of truth; use workbook default-selection/exclusive-group metadata, not Grand Sport/RPO-specific JavaScript.
- Use `save_workbook_safely()` and verify workbook saved on disk.
- Close/avoid Excel. Stop if `~$stingray_master.xlsx` exists.
- Do not hand-edit generated artifacts; regenerate from workbook source.
- Do not delete the `runtime_action` column.
- Do not trim generated `rules.runtime_action` payload shape.
- Do not change `body_style_scope`; Pass 9 already retired current OVS-derived source values.
- Do not migrate NWI/NGA exhaust replacement in this pass.
- Do not migrate J57/J6A caliper replacement in this pass.
- Do not change Z06 replacement/default behavior.
- Preserve Grand Sport J57 -> J6D soft-default ownership through `gs_default_j6d_with_j57`; do not reintroduce a J57 includes J6D hard auto-add.

## Implementation plan if approved

1. Preflight.

   ```sh
   cd /Users/seandm/Projects/27vette
   git status --short --branch
   test ! -e './~$stingray_master.xlsx'
   .venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
   ```

   Before editing, inspect dirty files and confirm no unrelated user changes overlap approved implementation paths. If unrelated dirty files exist, leave them untouched and report them in the handoff.

2. Snapshot current generated Grand Sport artifacts.

   ```sh
   mkdir -p /tmp/27vette-pass11-before
   cp form-output/runtime/grand-sport-runtime-contract.json /tmp/27vette-pass11-before/
   cp form-output/grand-sport-form-data.json /tmp/27vette-pass11-before/
   cp form-app/data.js /tmp/27vette-pass11-before/data.js
   ```

3. Read-only confirm candidate row identity before workbook write.

   For every direct row targeted for deletion, assert:

   - `rule_id`
   - `source_id`
   - `rule_type=excludes`
   - `target_id`
   - `runtime_action=replace`
   - blank `body_style_scope`

   Specifically assert these identities:

   - `gs_rule_opt_fey_001_excludes_opt_t0e_001_replace`: `opt_fey_001` excludes `opt_t0e_001`.
   - `gs_rule_opt_feb_001_excludes_opt_jx6_001_replace`: `opt_feb_001` excludes `opt_jx6_001`.
   - `gs_rule_opt_fey_001_excludes_opt_jx6_001_replace`: `opt_fey_001` excludes `opt_jx6_001`.
   - `gs_rule_opt_fey_001_excludes_opt_j56_001_replace`: `opt_fey_001` excludes `opt_j56_001`.

   Also assert:

   - `opt_t0e_001`, `opt_t0f_001`, `opt_jx6_001`, `opt_j56_001`, `opt_j57_001`, `opt_feb_001`, and `opt_fey_001` are active in `grandSport_options` with the expected section/selectable/display behavior listed in Diagnosis.
   - FEB -> J56 include remains present.
   - FEY -> J57 include remains present.
   - FEY -> T0F include remains present.
   - `gs_excl_z52_packages` contains exactly `opt_feb_001`, `opt_fey_001`.
   - `gs_excl_performance_brakes` contains exactly `opt_jx6_001`, `opt_j56_001`, `opt_j57_001` and has `selection_mode=required_single_within_group`.
   - `gs_rule_opt_j57_001_excludes_opt_j6a_001_replace` and `gs_rule_opt_nwi_001_excludes_opt_nga_001_replace` remain present before editing and are not in the deletion set.

4. Apply workbook edit through safe-save helper.

   - Add `default_selection_rules.gs_default_t0e` as described above.
   - Add `grandSport_exclusive_groups.gs_excl_performance_aero` and its members `opt_t0e_001`, `opt_t0f_001` if preflight confirms no equivalent active group already exists.
   - Add `default_selection_rules.gs_default_jx6` only if runtime parity requires explicit restoration beyond existing default-selected source metadata and required brake group behavior.
   - Delete only these `grandSport_rule_mapping` rows:
     - `gs_rule_opt_fey_001_excludes_opt_t0e_001_replace`
     - `gs_rule_opt_feb_001_excludes_opt_jx6_001_replace`
     - `gs_rule_opt_fey_001_excludes_opt_jx6_001_replace`
     - `gs_rule_opt_fey_001_excludes_opt_j56_001_replace`
   - Preserve these rows unchanged:
     - `gs_rule_opt_j57_001_excludes_opt_j6a_001_replace`
     - `gs_rule_opt_nwi_001_excludes_opt_nga_001_replace`
   - Preserve table refs and unrelated row order/values.
   - Do not create a committed one-off apply script unless needed for review; delete it before handoff if created.

5. Verify workbook on disk.

   - Reopen with `openpyxl` read-only.
   - Assert deleted rule IDs are absent from `grandSport_rule_mapping`.
   - Assert preserved J57/J6A and NWI/NGA direct replacement rows remain unchanged.
   - Assert the new/default rows exist exactly once and are active.
   - Assert `gs_excl_z52_packages` and `gs_excl_performance_brakes` membership/order remain unchanged.
   - Assert `gs_excl_performance_aero` membership/order if added.
   - Assert no Stingray or Z06 direct-rule rows changed.

6. Regenerate affected artifacts.

   ```sh
   .venv/bin/python scripts/generate_form.py --model grand_sport
   .venv/bin/python scripts/generate_registry.py
   ```

   Do not regenerate Stingray or Z06 model artifacts directly unless a validation failure proves it is required. Registry generation may rewrite `form-app/data.js`; review model-scoped deltas carefully.

7. Compare generated contracts.

   Use a focused diff because the intended row deletion changes Grand Sport rule counts and default/group metadata.

   Allow only:

   - Grand Sport runtime rule count decreases by 4.
   - Grand Sport `runtime_action=replace` count decreases by 4.
   - Removed Grand Sport rule IDs are exactly:
     - `gs_rule_opt_fey_001_excludes_opt_t0e_001_replace`
     - `gs_rule_opt_feb_001_excludes_opt_jx6_001_replace`
     - `gs_rule_opt_fey_001_excludes_opt_jx6_001_replace`
     - `gs_rule_opt_fey_001_excludes_opt_j56_001_replace`
   - `gs_rule_opt_j57_001_excludes_opt_j6a_001_replace` remains present.
   - `gs_rule_opt_nwi_001_excludes_opt_nga_001_replace` remains present.
   - FEY/FEB include rows remain present.
   - `gs_excl_performance_brakes` remains present with unchanged member order.
   - New `gs_default_t0e` and, if used, `gs_default_jx6` default-selection rows emit for Grand Sport only.
   - New `gs_excl_performance_aero` emits for Grand Sport only if added.
   - Timestamp fields may change.

   Any other contract delta is a stop condition.

8. Update focused tests.

   In `tests/grand-sport-draft-data.test.mjs`:

   - Keep J56 display-only shape assertions.
   - Keep FEB -> J56 include assertion.
   - Keep FEY -> J57/T0F/CFZ include assertions.
   - Replace current assertions that FEY/T0E, FEB/JX6, FEY/JX6, and FEY/J56 direct replace rows exist with assertions that those direct replace rows are absent.
   - Add assertions for `gs_default_t0e` and, if used, `gs_default_jx6` in `draft.defaultSelectionRules`.
   - Add/strengthen assertions for `gs_excl_performance_brakes` membership and required selection mode.
   - Add assertions for `gs_excl_performance_aero` if added.
   - Keep `gs_default_j6d_with_j57` and no J57 -> J6D hard include assertions intact.

   In `tests/multi-model-runtime-switching.test.mjs`:

   - Update expected Grand Sport exclusive-group inventory if `gs_excl_performance_aero` is added.
   - Add runtime behavior coverage for the actual replacement paths:
     - baseline Grand Sport reset/defaults select T0E and JX6.
     - selecting FEB removes/suppresses JX6 and auto-adds/locks J56.
     - switching to FEY removes/suppresses JX6 and J56, auto-adds/locks J57 and T0F, and leaves J6D as a selected soft default when appropriate.
     - removing FEY/FEB restores T0E and JX6 through workbook default/group metadata when no package/aero/brake peer remains.
     - user-selected brake/aero peers are not overwritten by default restoration while an active peer exists.
   - Verify Grand Sport behavior without adding RPO-specific runtime code.

   In `tests/grand-sport-contract-preview.test.mjs`:

   - Update count-sensitive preview expectations only for intentional group/default/rule deltas.

9. Run targeted gates.

   ```sh
   .venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
   .venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
   node --test tests/grand-sport-contract-preview.test.mjs
   node --test tests/grand-sport-draft-data.test.mjs
   node --test tests/multi-model-runtime-switching.test.mjs
   ```

   Add this optional guard if generated delta review is unclear or registry churn affects other model payloads:

   ```sh
   node --test tests/stingray-form-regression.test.mjs
   node --test tests/z06-runtime-promotion.test.mjs
   ```

10. Review diff.

    - Confirm workbook diff is limited to approved Grand Sport rule/default/group rows.
    - Confirm generated artifacts show only approved Grand Sport rule deletions plus new Grand Sport default/group metadata and timestamps/registry embedding.
    - Confirm `form-app/app.js` unchanged.
    - Confirm Stingray/Z06 generated model behavior unchanged in `form-app/data.js` except registry timestamp/container churn.
    - Confirm no dealer submission code changed.

11. Close spec/status docs.

    - Update this spec to completed with date, workbook sheets/artifacts/tests changed, gate results, residual risks, and next pass.
    - Update `docs/Audit-route-map.md` so Candidate C no longer appears pending and the next recommended pass moves to Candidate D only if repo evidence still supports it.

## Expected behavior impact

Intended customer-facing behavior impact: none for valid Grand Sport package selections. The same package/default outcomes should remain:

- T0E is the Grand Sport default aero choice until T0F or another aero peer is selected/auto-added.
- FEY includes T0F and should remove/suppress T0E.
- JX6 is the Grand Sport default brake choice until J56/J57 is selected/auto-added.
- FEB includes J56 and should remove/suppress JX6.
- FEY includes J57 and should remove/suppress JX6 and J56.
- J57 still soft-defaults J6D calipers through workbook default metadata.

The intended ownership impact is source cleanup: four direct `runtime_action=replace` rows are retired from `grandSport_rule_mapping`, while equivalent behavior is owned by workbook default-selection and exclusive-group metadata.

## Risks and stop conditions

Risks:

- T0E/T0F may need explicit Grand Sport aero group metadata for user-selected T0E removal when FEY includes T0F. If a runtime test fails without the group, add the group rather than restoring an RPO-specific JavaScript branch.
- J56 is display-only and non-selectable. The implementation must prove generic included-target exclusive peer reconciliation removes it when FEY includes J57.
- Default-selection restoration can accidentally re-add T0E/JX6 over a selected or auto-added peer if condition/group metadata is wrong.
- Required exclusive-group behavior can affect missing-requirement reporting. Tests must cover both selected state and missing requirement output after programmatic clearing.
- Generated registry refresh may embed unrelated timestamp churn. Diff review must separate timestamp/container churn from behavior changes.

Stop conditions:

- Any implementation needs `form-app/app.js` RPO-specific logic.
- Any implementation changes dealer submission payload, endpoint, modal validation, or Turnstile behavior.
- Generated diffs include Stingray/Z06 substantive data changes.
- Workbook preflight finds candidate row identity drift that changes the deletion set.
- Runtime behavior for FEB/FEY package selection differs from current intended behavior.
- NWI/NGA or J57/J6A direct replacement rows are modified.

## Non-goals

- Delete or rename the `runtime_action` column.
- Trim generated `runtime_action` fields from rule payloads.
- Change direct-rule `scopeMatches()` behavior.
- Migrate NWI/NGA exhaust replacement ownership.
- Migrate J57/J6A brake/caliper replacement ownership.
- Change Z06 package/default behavior.
- Add new dependencies.
- Refactor generator/runtime architecture.
- Change visual styling or layout.
- Change dealer submission behavior.

## Implementation completed

Completed on 2026-06-22.

Source workbook changes:

- `stingray_master.xlsx`
  - `grandSport_rule_mapping`: deleted exactly four Grand Sport direct replacement rows:
    - `gs_rule_opt_fey_001_excludes_opt_t0e_001_replace`
    - `gs_rule_opt_feb_001_excludes_opt_jx6_001_replace`
    - `gs_rule_opt_fey_001_excludes_opt_jx6_001_replace`
    - `gs_rule_opt_fey_001_excludes_opt_j56_001_replace`
  - `default_selection_rules`: added active `gs_default_t0e` for Grand Sport T0E restoration unless `sec_perf_aero_001` already has a selected/auto-added choice.
  - `grandSport_exclusive_groups`: added active `gs_excl_performance_aero` with `required_single_within_group`.
  - `grandSport_exclusive_members`: added active `gs_excl_performance_aero` members `opt_t0e_001` and `opt_t0f_001`.

Generated artifact changes:

- `form-output/runtime/grand-sport-runtime-contract.json`
- `form-app/data.js`

Test changes:

- `tests/grand-sport-draft-data.test.mjs`
- `tests/multi-model-runtime-switching.test.mjs`

Docs/status changes:

- `docs/audit-cleanup/pass-11-grand-sport-package-default-replacement-ownership-spec.md`
- `docs/Audit-route-map.md`

Preserved behavior and boundaries:

- `form-app/app.js` unchanged.
- Generator scripts unchanged.
- Stingray and Z06 source rule sheets unchanged.
- `runtime_action` workbook columns and generated rule payload shape unchanged.
- `gs_rule_opt_j57_001_excludes_opt_j6a_001_replace` preserved.
- `gs_rule_opt_nwi_001_excludes_opt_nga_001_replace` preserved.
- Dealer submission endpoint, payload shape, modal validation, and Turnstile behavior unchanged.

Generated contract delta proof:

- Grand Sport runtime rule count changed from 121 to 117.
- Grand Sport `runtime_action=replace` count changed from 6 to 2.
- Removed runtime rule IDs were exactly the four approved FEY/FEB package/default replacement rows.
- Added generated metadata was limited to `gs_excl_performance_aero` and `gs_default_t0e`, plus timestamp churn.
- Preserved direct replacement rows remained present for J57/J6A and NWI/NGA.

Gate results:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
# pass: status valid, issue_count 0

.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
# pass: status valid, issue_count 0

.venv/bin/python scripts/generate_form.py --model grand_sport
# pass: generated Grand Sport runtime contract, validation_errors 0

.venv/bin/python scripts/generate_registry.py
# pass: registry_generated for stingray, grandSport, z06

node --test tests/grand-sport-contract-preview.test.mjs
# pass: 6/6

node --test tests/grand-sport-draft-data.test.mjs
# pass: 19/19

node --test tests/multi-model-runtime-switching.test.mjs
# pass: 45/45
```

Residual risks / follow-up:

- Browser smoke was not run; coverage here is workbook/source verification, generated contract diff proof, and Node runtime tests.
- Candidate D, the NWI/NGA exhaust default replacement pass, remains separate and should be the next cleanup only after a fresh preflight confirms repo evidence still matches the Pass 8 classification.

## Historical approval prompt

Approved by the user on 2026-06-22: implement Pass 11 / Candidate C as scoped above.
