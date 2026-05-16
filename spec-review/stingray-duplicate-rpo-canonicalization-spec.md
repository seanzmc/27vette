# Stingray Duplicate RPO Canonicalization Spec

Spec only. Do not implement until approved.

## Goal

Collapse active duplicate RPOs in `stingray_options` so each RPO has one canonical option row, preferably the `_001` option ID, while preserving current generated/runtime behavior.

## Canonical Rule

Prefer `_001` as canonical for every duplicate RPO.

If `_001` is currently a mirror/standard-equipment row instead of the selectable row, move the needed selectable/default/status/rule behavior onto `_001` rather than choosing a later duplicate as canonical, unless verification proves `_001` cannot safely own the behavior.

## Constraints

- Workbook is source of truth.
- Do not add Stingray-only code paths.
- Do not invent new sheets if an existing Grand Sport/workbook structure already solves the same problem.
- Deactivate duplicates before deleting them.
- Preserve generated behavior before removing any compensating code.
- Do not remove duplicate rows until rules, statuses, price rules, groups, and standard-equipment behavior are remapped or proven unnecessary.

## Duplicate RPO Manifest

| RPO   | Canonical option_id | Duplicate option_ids                        | Current duplicate purpose              | Transfer target                                   | Required rule/status changes                                                                  | Deactivate in phase | Delete in phase | Risk   |
| ----- | ------------------- | ------------------------------------------- | -------------------------------------- | ------------------------------------------------- | --------------------------------------------------------------------------------------------- | ------------------- | --------------- | ------ |
| `EFR` | `opt_efr_001`       | `opt_efr_002`                               | standard-equipment mirror              | canonical status/standard-equipment output        | verify `EFR` still appears in Standard & Included where needed                                | Phase 1             | Phase 2         | Medium |
| `UQT` | `opt_uqt_001`       | `opt_uqt_002`                               | selectable vs trim-included bridge     | canonical row + variant-scoped override if needed | move 1LT selectable behavior and 2LT/3LT included/display-only behavior to one canonical path | Phase 1 or later    | after parity    | High   |
| `AQ9` | `opt_aq9_001`       | `opt_aq9_002`, `opt_aq9_003`, `opt_aq9_004` | trim mirrors plus selectable seat rows | canonical row + OVS/variant overrides             | verify 1LT/2LT standard behavior and selectable seat behavior                                 | later               | after parity    | High   |

### `EFR`

Canonical row:

- Keep `opt_efr_001`.

Duplicate rows:

- Deactivate `opt_efr_002` first.
- Delete only after generated parity is proven.

Behavior to preserve:

- `EFR` remains default-selected where applicable.
- `EFR` remains in Standard & Included when the selected variant expects it.
- `EFR` remains a member of `exclusive_groups.excl_ext_accents`.

Workbook transfers:

- `stingray_options`: move any needed display/default behavior to `opt_efr_001`.
- `stingray_ovs`: verify canonical status rows cover all variants previously covered by duplicate row.
- `rule_mapping`: remap duplicate references only if they represent behavior still needed.
- `price_rules`: verify no duplicate references.
- `exclusive_group_members`: use only canonical `opt_efr_001`.

Validation:

- No generated artifact references `opt_efr_002`.
- Runtime still default-selects/display-locks `EFR` correctly.

### `UQT`

Canonical row:

- Keep `opt_uqt_001`.

Duplicate rows:

-

| option_id   | canonical\* | trim | price | selectable T/F active T/F | req display_behavior |
| ----------- | ----------- | ---- | ----- | ------------------------- | -------------------- |
| opt_719_001 | \*          |      | 0     | TT                        | default_selected     |
| opt_719_002 |             | stan |       | FT                        |                      |

opt_ae4_001 \* 1LT 1095 TT
Price rule source: 2LT target price 2095
opt_ae4_002 2LT 2095 TT
pr source 3LT target price 595
opt_ae4_003 3LT 595 TT

opt_ah2_001 3ltEqu FT - delete
opt_ah2_002 \* 3LT 0 TT default_selected
pr source 2LT target price 1695
opt_ah2_003 2LT 1695 TT

opt_aq9_001 2ltEqu FT
opt_aq9_002 1ltEqu FT
opt_aq9_003 \* 1LT 0 TT default_selected
rule source 2LT target - default_selected
opt_aq9_004 2LT 0 TT

opt_uqt_001 2ltEqu FT
opt_uqt_002 1LT 1095 TT

opt_cf7_001 \* 0 //default_selected
opt_cf7_002 stan FT

opt_cm9_001 \* 0 //default_selected
opt_cm9_002 stan FT

opt_efr_001 \* 0 //default_selected
opt_efr_002 stan FT

opt_eyt_001 \* 0 //default_selected
opt_eyt_002 stan FT

opt_fe1_001 \* 0 //default_selected
opt_fe1_002 stan FT

opt_j6a_001 \* 0 //default_selected
opt_j6a_002 stan FT

opt_nga_001 \* 0 //default_selected
opt_nga_002 stan FT

opt_qeb_001 \* 0 //default_selected
opt_qeb_002 stan FT
