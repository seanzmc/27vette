# Grand Sport Brakes And Seatbelt Defaults Spec

## Diagnosis

Two remaining Grand Sport QA issues are both data-owned unless runtime lacks a generic way to interpret the workbook fact.

Current evidence:

- `section_master` currently has `sec_perf_brake_001` as:
  - `section_name=Performance Brakes`
  - `step_key=wheels`
  - `display_order=50`
- The Performance & Aero step currently has:
  - `sec_perf_z52_001` order `10`
  - `sec_exha_001` order `20`
  - `sec_perf_aero_001` order `30`
  - `sec_perf_ground_001` order `40`
- `grandSport_options` seatbelt rows are active/selectable in `sec_seat_001`.
- `opt_719_001` is currently standard in `grandSport_ovs` for all Grand Sport variants, and runtime has a generic fallback in `form-app/app.js`:
  - `if (!selectedOrAutoInSection("sec_seat_001", refreshedAutoAdded)) addDefaultRpo("719");`
- `opt_719_001` is not currently marked with `display_behavior=default_selected`, so the source workbook does not explicitly own the default.
- `lt_interiors` already contains customer-facing evidence for included color seatbelts on some 3LT interiors:
  - `3LT_AH2_HNK` and `3LT_AE4_HNK`: comes with `3F9`
  - `3LT_AH2_HZN` and `3LT_AE4_HZN`: comes with `3N9`
  - additional 3LT interiors may have similar included seatbelt language and need an audit, not a hardcoded subset.
- `color_overrides` currently contains many rows where selected color seatbelts add `D30`; it does not currently express "selected interior includes seatbelt option X" as an auto-add.

Risk level: medium. Moving the brake section is straightforward workbook data. Seatbelt defaults touch selected state, auto-added output, and single-select section reconciliation. The implementation should stay generic and workbook-backed.

## Goal

1. Move Grand Sport `Performance Brakes` back to `Performance & Aero`, second in display order.
2. Make black seatbelt `719` the workbook-owned default selected seatbelt.
3. For 3LT interiors that include a color seatbelt, automatically select/add that color seatbelt when the interior is selected, replacing/suppressing the default `719`.

## Constraints

- Do not activate Grand Sport production runtime.
- Preserve Stingray behavior and generated production path.
- Do not hardcode Grand Sport RPO-specific seatbelt business logic in scripts.
- Prefer workbook data changes over script logic.
- Runtime changes, if needed, must be generic:
  - selected interior can include option IDs;
  - auto-added options in a single-select section replace workbook defaults;
  - no RPO-specific branches for `3F9`, `3N9`, `379`, `3A9`, or `3M9`.
- Do not delete option rows.
- Save workbook through the hardened save path and validate package integrity after workbook mutation.

## Files To Change

Workbook/source:

- `stingray_master.xlsx`
  - `section_master`
  - `grandSport_options`
  - likely `lt_interiors`
  - possibly a workbook rule/source sheet if existing schema can express interior-to-option includes.

Generator/runtime:

- `scripts/corvette_form_generator/inspection.py`
- `form-app/app.js`

Tests:

- `tests/grand-sport-draft-data.test.mjs`
- `tests/multi-model-runtime-switching.test.mjs`
- `tests/stingray-generator-stability.test.mjs`
- `tests/stingray-form-regression.test.mjs`
- `tests/grand-sport-contract-preview.test.mjs` only if counts/contract expectations change.

Generated artifacts:

- `form-output/inspection/grand-sport-*.json`
- `form-output/inspection/grand-sport-*.md`
- `form-output/stingray-form-data.json`
- `form-app/data.js`

## Pass 1: Performance Brakes Section Placement

Workbook `section_master` changes:

- Set `sec_perf_brake_001.step_key=packages_performance`.
- Set `sec_perf_brake_001.display_order=20`.
- To keep Performance & Aero deterministic and avoid order collisions, set:
  - `sec_perf_z52_001.display_order=10`
  - `sec_perf_brake_001.display_order=20`
  - `sec_exha_001.display_order=30`
  - `sec_perf_aero_001.display_order=40`
  - `sec_perf_ground_001.display_order=50`

Expected tests:

- Grand Sport draft places `sec_perf_brake_001` under `packages_performance`.
- Performance & Aero section order is:
  1. Z52 Packages
  2. Performance Brakes
  3. Exhaust
  4. Aero Packages
  5. Ground Effects
- Wheels & Brake Calipers no longer contains `sec_perf_brake_001`.

## Pass 2: Workbook-Owned 719 Default

Workbook `grandSport_options` changes:

- Set `opt_719_001.display_behavior=default_selected`.
- Keep `opt_719_001.active=True`.
- Keep `opt_719_001.selectable=True`.
- Preserve `grandSport_ovs` standard status for all Grand Sport variants.

Runtime verification:

- Existing generic `addWorkbookDefaultChoices()` should pick up `719` because `sec_seat_001` is `single_select_req`.
- Keep the existing fallback `addDefaultRpo("719")` for Stingray/backward compatibility unless tests prove it duplicates or fights workbook defaults.

Expected tests:

- Grand Sport reset/reconcile selects `opt_719_001` from workbook `display_behavior=default_selected`.
- `719` remains visible/selectable as the standard/default seatbelt.

## Pass 3: Interior-Included Color Seatbelts

### Workbook Audit

Inspect `lt_interiors` 3LT rows and identify every active Grand Sport interior whose disclosure says it comes with a color seatbelt:

- `3F9` Torch Red seatbelt
- `3N9` Natural seatbelt
- `379` Orange seatbelt
- `3A9` Santorini Blue seatbelt
- `3M9` Yellow seatbelt, if any interior explicitly includes it

Do not infer from color names alone. Use `Detail from Disclosure` text or an existing explicit field.

### Preferred Workbook Representation

If the existing `lt_interiors.included_option_id` column is available and unused for these rows:

- Set `included_option_id` on the relevant 3LT interior rows to the corresponding seatbelt option ID:
  - `3F9` -> `opt_3f9_001`
  - `3N9` -> `opt_3n9_001`
  - `379` -> `opt_379_001`
  - `3A9` -> `opt_3a9_001`
  - `3M9` -> `opt_3m9_001`

If an interior already needs `included_option_id` for another included option, stop and revise the spec before adding a new schema. Do not overload the column with multiple IDs unless existing code already supports that format.

### Generator Changes

If `included_option_id` is used:

- Update `scripts/corvette_form_generator/inspection.py` so generated `interiors` include a generic field such as `included_option_ids`.
- Preserve existing single `included_option_id` behavior if already present.
- Validate each referenced option ID exists in the model option source and is active for the relevant variant/trim.

### Runtime Changes

Update `form-app/app.js` generically:

- `computeAutoAdded()` should add `interior.included_option_ids` when `state.selectedInterior` is set.
- If an auto-added included option belongs to a single-select section, `removeAutoDefaultDuplicates()` should remove non-user-selected defaults in that section, including `719`.
- Do not block the user from selecting a different seatbelt manually if the runtime already treats user-selected single-select choices as overriding auto-adds. If current logic blocks this, keep the behavior conservative and flag it for browser QA rather than hardcoding exceptions.

Expected tests:

- Selecting a 3LT interior that includes `3F9` auto-adds `3F9` and removes/suppresses default `719`.
- Selecting a 3LT interior that includes `3N9` auto-adds `3N9` and removes/suppresses default `719`.
- Interior-included color seatbelt appears in order output as an auto-added/included item at the workbook option price behavior already used for the option.
- Stingray output remains unchanged except generated timestamp.

## Validation Plan

Run:

```bash
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/generate_grand_sport_form.py
.venv/bin/python scripts/generate_stingray_form.py
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-rule-audit.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/stingray-form-regression.test.mjs
git diff --check
```

Manual browser checks:

- Grand Sport Performance & Aero section order shows Performance Brakes second.
- Grand Sport 1LT/2LT/3LT default seatbelt starts as `719`.
- On 3LT, selecting a Natural Dipped interior auto-adds `3N9` and does not keep `719` selected.
- On 3LT, selecting an Adrenaline Red Dipped or EL9 interior auto-adds `3F9` and does not keep `719` selected.
- Selecting a normal interior with no included color seatbelt keeps `719`.

## Non-Goals

- Do not add image/asset support.
- Do not redesign the seatbelt UI.
- Do not combine Stingray and Grand Sport option sheets.
- Do not create a new rule schema unless `lt_interiors.included_option_id` cannot safely represent the data.
- Do not change seatbelt pricing semantics unless QA shows a double-charge or incorrect charge after the auto-add works.

## Approval Checkpoint

After approval, execute the passes above and report:

- workbook rows changed;
- runtime/generator behavior changed;
- generated artifact counts;
- validation results;
- any remaining manual browser QA risk.
