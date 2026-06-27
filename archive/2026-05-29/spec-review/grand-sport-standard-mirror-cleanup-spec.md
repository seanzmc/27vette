# Grand Sport Standard Mirror Cleanup Spec

> Spec only. Do not implement until approved.

## Goal

Finish the next safe slice of Grand Sport source cleanup by removing redundant standard-equipment mirror option rows and consolidating `UQT` into one canonical option row that is chargeable/selectable on `1LT` and included/displayed as standard equipment on `2LT` and `3LT`.

This pass should reduce duplicate active RPO choices in `grandSport_options` without losing the Standard Equipment section in the selected-options sidebar or the generated standard-equipment summary.

## Diagnosis

The Grand Sport draft already populates `standardEquipment` from generated choice rows with `status=standard`. A row does not need to live in a separate `sec_stan_002` mirror section to appear in the Standard Equipment list.

Current active duplicate RPO groups from the saved workbook:

| RPO | Canonical row | Redundant / special row | Current shape |
| --- | --- | --- | --- |
| `719` | `opt_719_001` in `sec_seat_001` | `opt_719_002` in `sec_stan_002` | canonical seat-belt row is `standard` in all GS variants; mirror can go inactive. |
| `CF7` | `opt_cf7_001` in `sec_roof_001` | `opt_cf7_002` in `sec_stan_002` | canonical roof row is `standard` for coupe and unavailable for convertible; mirror can go inactive. |
| `CM9` | `opt_cm9_001` in `sec_roof_001` | `opt_cm9_002` in `sec_stan_002` | canonical convertible roof row is `standard` for convertible and unavailable for coupe; mirror can go inactive. |
| `EFR` | `opt_efr_001` in `sec_exte_001` | `opt_efr_002` in `sec_stan_002` | canonical exterior accent row is `standard` in all GS variants; mirror can go inactive. |
| `EYT` | `opt_eyt_001` in `sec_badg_001` | `opt_eyt_002` in `sec_stan_002` | canonical badge row is `standard` in all GS variants; mirror can go inactive. |
| `J6A` | `opt_j6a_001` in `sec_cali_001` | `opt_j6a_002` in `sec_stan_002` | canonical caliper row is `standard` in all GS variants; mirror can go inactive. |
| `NGA` | `opt_nga_001` in `sec_exha_001` | `opt_nga_002` in `sec_stan_002` | canonical exhaust-tip row is `standard` in all GS variants; mirror can go inactive. |
| `SWM` | `opt_swm_001` in `sec_whee_002` | `opt_swm_002` in `sec_stan_002` | canonical wheel row is `standard` in all GS variants; mirror can go inactive. |
| `AH2` | `opt_ah2_001` in `sec_seat_002` | `opt_ah2_003` in `sec_3lte_001` | 3LT standard seat row plus selectable seat row. Safe only if 3LT standard equipment still includes `AH2` from canonical row. |
| `AQ9` | `opt_aq9_001` in `sec_seat_002` | `opt_aq9_004` in `sec_1lte_001`, `opt_aq9_003` in `sec_2lte_001` | trim standard seat mirrors. Safe only if 1LT/2LT standard equipment still includes `AQ9` from canonical row. |
| `UQT` | should become one canonical row | `opt_uqt_001`, `opt_uqt_002` split behavior today | needs intentional consolidation, not blind deactivation. |

`UQT` currently has both rows active:

- `opt_uqt_001` in `sec_inte_001`, `selectable=TRUE`, statuses `available` for 1LT and `standard` for 2LT/3LT.
- `opt_uqt_002` in `sec_2lte_001`, `selectable=FALSE`, statuses `available` for 1LT and `standard` for 2LT/3LT.

The desired behavior is one canonical `UQT` row:

- selectable/chargeable option on 1LT;
- included/no-cost standard equipment on 2LT and 3LT;
- visible in the selected-options Standard Equipment list for 2LT and 3LT;
- not duplicated as both an Interior Trim option and an Equipment Group mirror.

## Exact Files To Change

- `stingray_master.xlsx`
  - `grandSport_options`
  - `grandSport_ovs`
  - possibly `grandSport_rule_mapping` only if inactive duplicate option IDs are referenced by active rules.
- `tests/grand-sport-contract-preview.test.mjs`
  - update generated count expectations after mirror rows are removed.
- `tests/grand-sport-draft-data.test.mjs`
  - update full matrix, standard-equipment, and status-count expectations.
  - add focused assertions proving standard equipment still includes canonical rows after mirror rows go inactive.
- `tests/multi-model-runtime-switching.test.mjs`
  - add or update a Grand Sport runtime assertion for `UQT` 1LT vs 2LT/3LT behavior if this can be tested without browser UI.
- Generated artifacts after regeneration:
  - `form-output/inspection/grand-sport-contract-preview.json`
  - `form-output/inspection/grand-sport-contract-preview.md`
  - `form-output/inspection/grand-sport-form-data-draft.json`
  - `form-output/inspection/grand-sport-form-data-draft.md`
  - `form-output/inspection/grand-sport-inspection.json`
  - `form-output/inspection/grand-sport-inspection.md`
  - `form-output/inspection/grand-sport-rule-audit.json`
  - `form-output/inspection/grand-sport-rule-audit.md`
  - `form-app/data.js`

No app runtime code should be changed unless validation proves the existing standard-equipment derivation cannot support the desired `UQT` behavior from workbook data.

## Constraints

- Workbook data owns the business decisions.
- Do not add hardcoded Grand Sport business logic to scripts.
- Do not activate Grand Sport variants in `variant_master`.
- Do not delete option rows; prefer `active=FALSE`.
- Keep `grandSport_ovs` coverage for every `grandSport_options.option_id`.
- Preserve Stingray behavior and generated Stingray counts.
- Preserve raw source evidence in inactive rows.
- Do not reintroduce `category`.
- Do not add `section_master.step_key` in this pass.

## Proposed Workbook Changes

### 1. Deactivate Standard Mirror Rows

Set these `grandSport_options.active` values to `FALSE`:

- `opt_719_002`
- `opt_cf7_002`
- `opt_cm9_002`
- `opt_efr_002`
- `opt_eyt_002`
- `opt_j6a_002`
- `opt_nga_002`
- `opt_swm_002`

Expected result:

- `sec_stan_002` duplicate mirrors are removed from the draft choice surface.
- Standard Equipment list still includes these RPOs from the canonical rows whenever those canonical rows are `status=standard`.
- `grandSport_ovs` rows stay intact.

### 2. Collapse Seat Equipment Mirrors If Proven By Tests

Candidate rows to deactivate after proving standard-equipment output remains correct:

- `opt_ah2_003`
- `opt_aq9_004`
- `opt_aq9_003`

Required proof before deactivation:

- 3LT Grand Sport standard equipment still includes `AH2` via `opt_ah2_001`.
- 1LT and 2LT Grand Sport standard equipment still include `AQ9` via `opt_aq9_001`.
- The Seats step still shows only the intended selectable seat rows and does not duplicate trim-equipment mirrors.

If proof fails, leave these rows active and document the generator gap instead of patching runtime behavior.

### 3. Consolidate `UQT`

Preferred source shape:

- Keep `opt_uqt_001` as the canonical active `UQT` row.
- Move `opt_uqt_001.section_id` from `sec_inte_001` to the equipment-group section that should own the customer display. If the workbook currently only has `sec_2lte_001` for this purpose, use `sec_2lte_001` for this pass and flag the naming limitation.
- Keep `opt_uqt_001.selectable=TRUE`.
- Keep `grandSport_ovs` for `opt_uqt_001`:
  - `1lt_e07=available`
  - `1lt_e67=available`
  - `2lt_e07=standard`
  - `2lt_e67=standard`
  - `3lt_e07=standard`
  - `3lt_e67=standard`
- Set `opt_uqt_002.active=FALSE`.
- Leave `opt_uqt_002` OVS rows intact.

Expected runtime behavior from existing generic logic:

- On 1LT, `UQT` appears as a selectable paid option.
- On 2LT/3LT, `UQT` appears as standard/included equipment and should not need a second mirror row.

If current runtime still displays the canonical row as selectable on 2LT/3LT because `selectable=TRUE`, do not add a Grand Sport-specific script patch. Instead, document the needed generic data capability:

- either a workbook field for variant/trim-scoped selectability;
- or a workbook-supported display behavior/status interpretation where `status=standard` rows are locked/included even when the source row is selectable.

### 4. Rebuild Audit Report

Update [grand-sport-source-cleanup-audit.md](/Users/seandm/Projects/27vette/spec-review/grand-sport-source-cleanup-audit.md) after the workbook changes.

The report should show:

- active duplicate RPOs remaining;
- mirror rows deactivated;
- `UQT` final source shape;
- inactive option references in active rules/groups;
- active sections and step placement;
- display-order anomalies.

## Non-Goals

- Do not clean every section placement and display order in this pass.
- Do not move stripes/hash marks/aero/performance unless directly required by duplicate cleanup.
- Do not change Grand Sport rules unless an inactive duplicate option ID must be remapped to a canonical active option.
- Do not add new schemas unless `UQT` cannot be represented with current source data and tests prove the gap.
- Do not change the selected-options sidebar UI.

## Risks

- Deactivating standard mirror rows may reduce `standardEquipment` counts. That is acceptable only if the user-facing Standard Equipment list still contains the RPOs from canonical rows.
- `UQT` may expose a real limitation: current source shape can express variant status, but not trim-scoped selectability independently from status. If so, stop at documentation and do not hardcode a workaround.
- Seat mirrors `AH2` and `AQ9` may be carrying trim-equipment copy that the canonical seat rows do not fully replace. Verify before deactivating.

## Validation Plan

Run, in order:

1. `.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx`
2. `.venv/bin/python scripts/build_grand_sport_rule_sources.py`
3. `.venv/bin/python scripts/generate_grand_sport_form.py`
4. `.venv/bin/python scripts/generate_stingray_form.py`
5. `node --test tests/grand-sport-contract-preview.test.mjs`
6. `node --test tests/grand-sport-draft-data.test.mjs`
7. `node --test tests/grand-sport-rule-audit.test.mjs`
8. `node --test tests/multi-model-runtime-switching.test.mjs`
9. `node --test tests/stingray-generator-stability.test.mjs`
10. `node --test tests/stingray-form-regression.test.mjs`
11. `.venv/bin/python -m py_compile scripts/generate_stingray_form.py scripts/generate_grand_sport_form.py scripts/build_grand_sport_rule_sources.py scripts/validate_workbook_package.py scripts/corvette_form_generator/*.py`
12. `git diff --check`

Manual/browser verification after implementation:

- Grand Sport 1LT: `UQT` appears as a selectable paid option.
- Grand Sport 2LT and 3LT: `UQT` appears in Standard Equipment / included equipment and does not appear as a duplicate chargeable option.
- Canonical standard RPOs still appear in the selected-options Standard Equipment list after mirror rows are inactive.
- Stingray still defaults and behaves unchanged.
