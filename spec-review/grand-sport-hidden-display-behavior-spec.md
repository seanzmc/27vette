# Grand Sport Hidden Display Behavior Spec

## Diagnosis

The latest saved workbook validates as an Excel package and the Grand Sport source tables remain structurally sound:

- `stingray_master.xlsx` package validation: valid, 0 issues.
- `grandSport_options`: 269 real option rows, 229 active option rows.
- `grandSport_ovs`: 1614 rows, exactly one row for every `grandSport_options.option_id` x Grand Sport variant pair.
- `grandSport_options`: no duplicate `option_id` values and no active duplicate RPO groups.
- `grandSport_options.section_id`: all values resolve to `section_master`.
- Grand Sport draft preview still builds with 0 validation errors and only the expected draft/pricing warnings.

The validation gap is behavioral:

- `opt_n26_001` / `N26` now has `display_behavior=hidden`.
- `opt_tu7_001` / `TU7` now has `display_behavior=hidden`.
- `hidden` is already a workbook-backed display behavior in the Stingray generator path.
- The Grand Sport shared inspection/draft path in `scripts/corvette_form_generator/inspection.py` currently only applies special handling for:
  - `display_only`
  - `auto_only`
- Because `N26` and `TU7` are currently `active=False`, they are suppressed anyway, but the workbook contract should still recognize `hidden` explicitly so future rows do not rely on incidental inactive suppression.

Risk level: low-to-medium. This is a source contract hardening pass. It should not activate Grand Sport or add runtime business logic.

## Exact Files To Inspect

- `stingray_master.xlsx`
  - `grandSport_options`
  - `grandSport_ovs`
  - `grandSport_variant_overrides`
- `scripts/corvette_form_generator/inspection.py`
  - `display_behavior_status`
  - preview/draft choice construction paths
  - validation output construction
- `scripts/generate_stingray_form.py`
  - existing Stingray `hidden` behavior for reference only
- `scripts/corvette_form_generator/model_configs.py`
  - display behavior labels, if shared labels need extension
- `tests/grand-sport-draft-data.test.mjs`
- `tests/grand-sport-rule-audit.test.mjs`
- `tests/stingray-generator-stability.test.mjs`

## Exact Files To Change

- `scripts/corvette_form_generator/inspection.py`
- `tests/grand-sport-draft-data.test.mjs`
- `tests/grand-sport-rule-audit.test.mjs`
- `tests/stingray-generator-stability.test.mjs`

Optional only if needed:

- `scripts/corvette_form_generator/model_configs.py`

Do not edit workbook data in this pass unless validation proves a source row is malformed. The current workbook source rows are the intended source-of-truth changes.

## Constraints

- Preserve workbook-as-source-of-truth.
- Do not move business rules into runtime scripts.
- Do not activate Grand Sport in `variant_master`.
- Preserve Stingray behavior and generated Stingray output.
- Do not combine model option lists.
- Keep Grand Sport as draft/inspection output until production readiness is explicitly approved.
- Do not remove rows from `grandSport_options`; inactive rows remain allowed.
- Do not treat active non-selectable standard-equipment rows as an error in this pass.
- Do not add new workbook schemas.

## Required Behavior

1. Treat `display_behavior=hidden` as a valid display behavior in the Grand Sport shared draft path.

2. Hidden option rows must be suppressed from:

   - preview `choices`
   - draft `choices`
   - standard equipment output
   - copied/generated rule surfaces where the hidden option is the source or target

3. Hidden option rows may remain in:

   - `grandSport_options`
   - `grandSport_ovs`
   - audit/reporting surfaces as source evidence
   - interior component metadata, if the component is represented through interior data instead of a standalone option card

4. Validation should allow these display behavior values:

   - blank
   - `display_only`
   - `auto_only`
   - `hidden`

5. If any future row uses an unknown `display_behavior`, report it in validation/audit output instead of silently treating it as normal selectable behavior.

## Current Workbook Decisions To Preserve

| option_id | RPO | active | selectable | display_behavior | Meaning |
| --- | --- | --- | --- | --- | --- |
| `opt_n26_001` | `N26` | `False` | `TRUE` | `hidden` | Interior component evidence; no standalone card. |
| `opt_tu7_001` | `TU7` | `False` | `TRUE` | `hidden` | Interior component evidence; no standalone card. |

## Non-Goals

- Do not clean up all active non-selectable standard equipment rows.
- Do not implement a new section-level hidden schema.
- Do not rewrite rule mapping.
- Do not modify price rules.
- Do not move sections or display order.
- Do not regenerate production Stingray output except as a validation gate if required.

## Validation Plan

Run these checks after implementation:

```bash
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python -m py_compile scripts/corvette_form_generator/inspection.py scripts/generate_stingray_form.py scripts/generate_grand_sport_form.py
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/grand-sport-rule-audit.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/stingray-form-regression.test.mjs
git diff --check
```

Manual verification:

- Build or inspect the Grand Sport draft data and confirm no visible `N26` or `TU7` standalone choice cards are emitted.
- Confirm interior/component metadata still carries the relevant component information where applicable.
- Confirm workbook opens in Excel without repair prompt if the workbook was touched.

## Success Criteria

- Workbook package remains valid.
- `hidden` is accepted in the Grand Sport workbook contract.
- `N26` and `TU7` do not appear as standalone Grand Sport draft choices.
- Grand Sport draft still has 0 validation errors.
- Stingray regression tests remain unchanged.
