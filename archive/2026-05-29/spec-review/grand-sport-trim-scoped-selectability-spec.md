# Grand Sport Trim-Scoped Selectability Spec

> Spec only. Do not implement until approved.

## Goal

Add a workbook-owned way to express variant/trim-scoped selectability so one canonical option row can behave differently by trim without duplicate RPO rows.

Use that capability to:

- make canonical `AQ9` standard for all Grand Sport `1LT` and `2LT` variants;
- deactivate the remaining `AQ9` 2LT mirror row;
- prepare the source model for collapsing `UQT` in a follow-up or the same pass if validation proves the generic capability covers it cleanly.

## Diagnosis

After the standard mirror cleanup, active Grand Sport duplicate RPOs are down to:

- `AQ9`: `opt_aq9_001` canonical seat row plus `opt_aq9_003` 2LT equipment mirror.
- `UQT`: `opt_uqt_001` selectable row plus `opt_uqt_002` equipment mirror.

`AQ9` could not be fully collapsed because canonical `opt_aq9_001` is currently unavailable for 2LT in `grandSport_ovs`, so removing `opt_aq9_003` would drop `AQ9` from 2LT standard equipment.

`UQT` exposes the broader missing source capability:

- 1LT needs selectable/chargeable `UQT`.
- 2LT/3LT need included/display-only standard `UQT`.
- The current source model has one row-level `selectable` value, so it cannot express that difference on a single canonical option row.

## Exact Files To Change

- `stingray_master.xlsx`
  - `grandSport_options`
  - `grandSport_ovs`
  - new optional workbook source surface for variant/trim-scoped selectability, if needed.
- `scripts/corvette_form_generator/inspection.py`
  - read and apply trim/variant-scoped selectability overrides for Grand Sport draft generation.
- `scripts/generate_stingray_form.py`
  - only if the new capability is shared by both model generators; preserve Stingray output unless Stingray opts into the override sheet.
- `scripts/corvette_form_generator/model_config.py`
  - add optional config pointer for the override source if a new sheet is used.
- `scripts/corvette_form_generator/model_configs.py`
  - wire Grand Sport to the override source; do not wire Stingray unless needed.
- `tests/grand-sport-contract-preview.test.mjs`
- `tests/grand-sport-draft-data.test.mjs`
- `tests/grand-sport-rule-audit.test.mjs`
- `tests/multi-model-runtime-switching.test.mjs`
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

## Constraints

- Workbook data owns the business rules.
- Do not hardcode `AQ9` or `UQT` trim behavior in app runtime.
- Do not activate Grand Sport in `variant_master`.
- Do not delete option rows; deactivate superseded duplicate rows.
- Keep `grandSport_ovs` coverage for all `grandSport_options.option_id` rows.
- Preserve Stingray generation and runtime behavior.
- Do not reintroduce `category`.
- Do not add `section_master.step_key` in this pass.

## Proposed Data Shape

Prefer a small optional override sheet instead of adding more overloaded columns to `grandSport_ovs`.

New sheet:

`grandSport_variant_overrides`

Headers:

| Column | Meaning |
| --- | --- |
| `option_id` | Existing `grandSport_options.option_id`. |
| `variant_id` | Existing Grand Sport `variant_master.variant_id`. |
| `selectable` | Optional override for generated choice row selectability. Blank means use `grandSport_options.selectable`. |
| `display_behavior` | Optional override for generated choice row display behavior. Blank means use `grandSport_options.display_behavior`. |
| `section_id` | Optional override for generated choice row section. Blank means use `grandSport_options.section_id`. |
| `active` | Override-row active flag. `TRUE` rows apply; `FALSE` rows are ignored. |
| `note` | Human-readable source explanation. |

Rules:

- The sheet is optional and model-scoped.
- It must not change source option rows globally.
- It applies during generated choice row construction after base option fields and status are read.
- It may only override generated choice-row fields for the specific `option_id + variant_id`.
- It must not change `grandSport_ovs.status`.
- It must validate that `option_id`, `variant_id`, and optional `section_id` resolve.

## AQ9 Workbook Changes

Update `grandSport_ovs` for canonical `opt_aq9_001`:

| option_id | variant_id | status |
| --- | --- | --- |
| `opt_aq9_001` | `1lt_e07` | `standard` |
| `opt_aq9_001` | `1lt_e67` | `standard` |
| `opt_aq9_001` | `2lt_e07` | `standard` |
| `opt_aq9_001` | `2lt_e67` | `standard` |
| `opt_aq9_001` | `3lt_e07` | `unavailable` |
| `opt_aq9_001` | `3lt_e67` | `unavailable` |

Then set in `grandSport_options`:

- `opt_aq9_003.active=FALSE`

Expected result:

- `AQ9` no longer appears as an active duplicate RPO.
- 1LT and 2LT Grand Sport standard equipment still includes `AQ9`.
- Seats step does not gain an extra 2LT selectable `AQ9` card unless the current runtime renders standard selectable rows as defaults. If it does, apply the override sheet:
  - `opt_aq9_001` + `2lt_e07`: `selectable=FALSE`, `section_id=sec_2lte_001`
  - `opt_aq9_001` + `2lt_e67`: `selectable=FALSE`, `section_id=sec_2lte_001`

## UQT Follow-Through

If the override sheet is added in this pass, use it to prove `UQT` can collapse cleanly:

Keep canonical row:

- `opt_uqt_001.active=TRUE`
- `opt_uqt_001.selectable=TRUE`
- `opt_uqt_001.section_id` remains the selectable option section unless the workbook owner chooses a better canonical section.

Add override rows:

| option_id | variant_id | selectable | display_behavior | section_id | active | note |
| --- | --- | --- | --- | --- | --- | --- |
| `opt_uqt_001` | `2lt_e07` | `FALSE` | `display_only` | `sec_2lte_001` | `TRUE` | 2LT included equipment. |
| `opt_uqt_001` | `2lt_e67` | `FALSE` | `display_only` | `sec_2lte_001` | `TRUE` | 2LT included equipment. |
| `opt_uqt_001` | `3lt_e07` | `FALSE` | `display_only` | `sec_3lte_001` | `TRUE` | 3LT included equipment. |
| `opt_uqt_001` | `3lt_e67` | `FALSE` | `display_only` | `sec_3lte_001` | `TRUE` | 3LT included equipment. |

Then set:

- `opt_uqt_002.active=FALSE`

Expected result:

- 1LT shows `UQT` as selectable/chargeable.
- 2LT and 3LT show `UQT` in standard/included equipment, not as a chargeable selectable option.
- No active duplicate `UQT` rows remain.

If implementing `UQT` in this pass creates unexpected runtime behavior, stop after `AQ9`, leave `UQT` documented as the only remaining duplicate, and do not patch the runtime with model-specific logic.

## Generator Behavior

When building choices:

1. Read base option row from `grandSport_options`.
2. Read variant status from `grandSport_ovs`.
3. Look up any active override for `(option_id, variant_id)`.
4. Apply override fields only to that generated choice row:
   - `selectable`
   - `display_behavior`
   - `section_id`
5. Re-resolve section name, step key, selection mode, and choice mode from the overridden section.
6. Apply existing `display_behavior` semantics generically:
   - `auto_only` suppresses manual display.
   - `display_only` emits visible non-selectable rows.
   - blank uses normal status/selectability behavior.

Do not add runtime-specific `if rpo === "UQT"` or `if option_id === ...` behavior.

## Tests To Add Or Update

### Draft Data Tests

Assert:

- `opt_aq9_003` is inactive and absent from emitted active choices.
- `opt_aq9_001` is `standard` for `1lt_e07`, `1lt_e67`, `2lt_e07`, and `2lt_e67`.
- 1LT and 2LT standard equipment includes `AQ9`.
- No active duplicate `AQ9` remains.

If `UQT` is collapsed:

- `opt_uqt_002` is inactive and absent from emitted active choices.
- `opt_uqt_001` is available/selectable on `1lt_e07` and `1lt_e67`.
- `opt_uqt_001` is standard/non-selectable/display-only on 2LT and 3LT variants.
- No active duplicate `UQT` remains.

### Runtime Tests

If `UQT` is collapsed:

- Grand Sport 1LT runtime shows `UQT` as a selectable paid option.
- Grand Sport 2LT/3LT runtime includes `UQT` in Standard & Included and does not allow it as a chargeable selected option.

### Rule Audit Tests

Update duplicate hot spot expectations:

- `AQ9` should no longer be reported as an active duplicate.
- If `UQT` is collapsed, `UQT` should no longer be reported as an active duplicate.
- If `UQT` is deferred, `UQT` remains the only active duplicate with an explicit audit note.

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

Manual browser checks:

- Grand Sport 1LT includes `AQ9` as standard equipment and does not show a duplicate `AQ9` equipment mirror.
- Grand Sport 2LT includes `AQ9` as standard equipment and does not show a duplicate `AQ9` equipment mirror.
- If `UQT` is collapsed: 1LT selectable/paid, 2LT/3LT included/non-chargeable.
- Stingray still defaults and behaves unchanged.

## Non-Goals

- Do not clean broader section/display order in this pass.
- Do not alter Grand Sport activation state.
- Do not change rules unrelated to the affected duplicate rows.
- Do not add runtime patches for specific RPOs.
