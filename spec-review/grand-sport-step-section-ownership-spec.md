# Grand Sport Step/Section Ownership Spec

## Diagnosis

Grand Sport option source data is structurally ready for a step/section ownership pass:

- `stingray_master.xlsx` package validation passes with 0 issues.
- `grandSport_options` has 269 real option rows and 229 active option rows.
- `grandSport_ovs` has exact coverage: 1614 rows for 269 Grand Sport option rows x 6 Grand Sport variants.
- `grandSport_options` has no duplicate `option_id` values.
- `grandSport_options` has no active duplicate RPO groups.
- Every `grandSport_options.section_id` resolves to `section_master`.
- Grand Sport draft preview currently builds with 0 validation errors.

The blocker is ownership clarity:

- Section names, selection modes, required flags, and section display order live in `section_master`.
- Option-to-section assignment lives in `grandSport_options.section_id`.
- Section-to-step placement still lives mostly in code:
  - `STEP_ORDER` in `scripts/corvette_form_generator/model_configs.py`
  - `STEP_LABELS` in `scripts/corvette_form_generator/model_configs.py`
  - `SECTION_STEP_OVERRIDES` in `scripts/corvette_form_generator/model_configs.py`
  - fallback name heuristics in `scripts/corvette_form_generator/mapping.py`
  - `STANDARD_SECTIONS` in `scripts/corvette_form_generator/model_configs.py`
- `section_master` currently has no `category` column and no `step_key` column.
- Current code references to `category` / `category_master` are documentation/audit remnants, not active generator inputs. For this pass, category serves no exclusive functional purpose and should not be reintroduced.

Risk level: medium. This affects where options render in the generated form, but should be implemented as workbook-owned placement plus narrow generator wiring, not runtime business logic.

## Exact Files To Inspect

- `stingray_master.xlsx`
  - `section_master`
  - `grandSport_options`
  - `stingray_options`
  - `grandSport_ovs`
  - `grandSport_variant_overrides`
- `scripts/corvette_form_generator/model_configs.py`
  - `STEP_ORDER`
  - `STEP_LABELS`
  - `SECTION_STEP_OVERRIDES`
  - `STANDARD_SECTIONS`
- `scripts/corvette_form_generator/mapping.py`
  - `step_for_section`
- `scripts/corvette_form_generator/inspection.py`
  - `resolved_step_key`
  - section row generation
  - step row generation
- `scripts/generate_stingray_form.py`
  - Stingray-specific direct use of `STEP_ORDER`, `STEP_LABELS`, and `step_for_section`
- Tests:
  - `tests/grand-sport-contract-preview.test.mjs`
  - `tests/grand-sport-draft-data.test.mjs`
  - `tests/multi-model-runtime-switching.test.mjs`
  - `tests/stingray-form-regression.test.mjs`
  - `tests/stingray-generator-stability.test.mjs`

## Exact Files To Change

Workbook:

- `stingray_master.xlsx`
  - `section_master`

Code:

- `scripts/corvette_form_generator/inspection.py`
- `scripts/corvette_form_generator/mapping.py`
- `scripts/corvette_form_generator/model_configs.py`

Tests:

- `tests/grand-sport-contract-preview.test.mjs`
- `tests/grand-sport-draft-data.test.mjs`
- `tests/multi-model-runtime-switching.test.mjs`
- `tests/stingray-generator-stability.test.mjs`

Optional only if Stingray assertions need to be kept synchronized:

- `tests/stingray-form-regression.test.mjs`

Do not change `scripts/generate_stingray_form.py` unless the shared mapping change requires a narrow compatibility patch. Stingray output must remain stable.

## Constraints

- Preserve workbook-as-source-of-truth.
- Do not add business logic to runtime scripts.
- Do not activate Grand Sport in `variant_master`.
- Do not combine Stingray and Grand Sport option lists.
- Preserve `stingray_options` and `stingray_ovs` as Stingray source inputs.
- Preserve `grandSport_options` and `grandSport_ovs` as Grand Sport source inputs.
- Do not reintroduce `category`.
- Do not archive or delete source sheets in this pass.
- Do not modify price rules in this pass.
- Do not simplify rule sheets in this pass.
- Do not clean unrelated copy or option descriptions.

## Workbook Contract

Add one column to `section_master`:

| column | purpose |
| --- | --- |
| `step_key` | Explicit generated-form step ownership for each section. |

Do not add `category`.

Do not add a new step sheet in this pass. `STEP_ORDER` and `STEP_LABELS` may remain code-owned runtime shell config for now, because they also include synthetic context steps (`body_style`, `trim_level`, `customer_info`, `summary`) that are not normal source workbook sections.

`section_master.step_key` should become the source of truth for normal source section placement. Code-owned overrides should remain only for:

- synthetic context sections;
- emergency compatibility fallback;
- sections that intentionally do not appear in `section_master`.

## Initial Section Placement Target

Populate `section_master.step_key` as follows.

### Standard Equipment

| section_id | section_name | step_key |
| --- | --- | --- |
| `sec_1lte_001` | 1LT Equipment | `standard_equipment` |
| `sec_2lte_001` | 2LT Equipment | `standard_equipment` |
| `sec_3lte_001` | 3LT Equipment | `standard_equipment` |
| `sec_incl_001` | Included | `standard_equipment` |
| `sec_stan_001` | Standard Equipment | `standard_equipment` |
| `sec_stan_002` | Standard Options | `standard_equipment` |
| `sec_safe_001` | Safety Features | `standard_equipment` |
| `sec_tech_001` | Technology | `standard_equipment` |

### Exterior Paint And Appearance

| section_id | section_name | step_key |
| --- | --- | --- |
| `sec_pain_001` | Paint | `paint` |
| `sec_roof_001` | Roof | `exterior_appearance` |
| `sec_exte_001` | Exterior Accents | `exterior_appearance` |
| `sec_badg_001` | Badges | `exterior_appearance` |
| `sec_engi_001` | Engine Appearance | `exterior_appearance` |
| `sec_gsce_001` | GS Center Stripes | `aero_exhaust_stripes_accessories` |
| `sec_gsha_001` | GS Hash Marks | `aero_exhaust_stripes_accessories` |

Note: `sec_gsce_001` and `sec_gsha_001` move to the stripes/accessories step per the user’s browser-test feedback. Keep labels as Grand Sport-specific display labels via existing label overrides unless a workbook label cleanup is explicitly approved.

### Wheels, Calipers, And Performance

| section_id | section_name | step_key |
| --- | --- | --- |
| `sec_whee_002` | Wheels | `wheels` |
| `sec_cali_001` | Caliper Color | `wheels` |
| `sec_whee_001` | Wheel Accessory | `wheels` |
| `sec_perf_001` | Performance | `packages_performance` |
| `sec_susp_001` | Suspension | `packages_performance` |
| `sec_exha_001` | Exhaust | `packages_performance` |
| `sec_spec_001` | Special Edition | `packages_performance` |

This keeps the current runtime step keys for now. A later label-only pass can rename:

- `packages_performance` from `Packages & Performance` to `Aero Packages & Performance`, if still desired.
- `aero_exhaust_stripes_accessories` from `Aero, Exhaust, Stripes & Accessories` to `Stripes & Accessories`, once exhaust/performance ownership is stable.

### Aero, Stripes, And Accessories

| section_id | section_name | step_key |
| --- | --- | --- |
| `sec_stri_001` | Stripes | `aero_exhaust_stripes_accessories` |
| `sec_spoi_001` | Spoiler | `aero_exhaust_stripes_accessories` |
| `sec_lpoe_001` | LPO Exterior | `aero_exhaust_stripes_accessories` |
| `sec_lpow_001` | LPO Wheels | `aero_exhaust_stripes_accessories` |

### Interior

| section_id | section_name | step_key |
| --- | --- | --- |
| `sec_seat_002` | Seats | `seat` |
| `sec_intc_001` | 1LT Interior | `base_interior` |
| `sec_intc_002` | 2LT Interior | `base_interior` |
| `sec_intc_003` | 3LT Interior | `base_interior` |
| `sec_seat_001` | Seat Belt | `seat_belt` |
| `sec_inte_001` | Interior Trim | `interior_trim` |
| `sec_lpoi_001` | LPO Interior | `interior_trim` |
| `sec_colo_001` | Color Override | `interior_trim` |
| `sec_cust_002` | Custom Stitch | `interior_trim` |
| `sec_onst_001` | OnStar | `interior_trim` |

### Delivery

| section_id | section_name | step_key |
| --- | --- | --- |
| `sec_cust_001` | Custom Delivery | `delivery` |

## Generator Changes

1. Update `resolved_step_key` / `step_for_section` so the resolution order is:

   1. `section_master.step_key`, when present.
   2. model config `section_step_overrides`, for backward compatibility.
   3. `standard_sections`, for backward compatibility.
   4. existing heuristic fallback.

2. Validate `section_master.step_key` values against `config.step_order` plus `standard_equipment`.

3. Emit validation errors for:

   - missing `step_key` on a source section with active Grand Sport choices;
   - unknown `step_key`;
   - Grand Sport section that falls back to heuristic placement instead of workbook-owned placement.

4. Keep current `STEP_ORDER` as the runtime order source for this pass.

5. Keep current `STEP_LABELS` as the runtime label source for this pass.

6. Reduce Grand Sport-specific `section_step_overrides` to only entries that remain genuinely runtime-owned after `section_master.step_key` is populated.

7. Do not change how options are assigned to sections in this pass. If browser-test feedback requires moving an option to another section, that belongs in a later workbook option-row cleanup or price-rule pass.

## Category Decision

Do not use `category` for this pass.

Current evidence:

- `section_master` no longer has a `category` column.
- Current generator code does not use `category_master` for step placement.
- Active routing is by `section_id`, `standard_sections`, override maps, and name heuristics.

Conclusion:

- `category` serves no exclusive functional purpose for current form generation.
- Do not re-add it.
- Do not make step placement depend on category.
- Leave any archived category reference sheets alone until a separate archive cleanup pass.

## Expected Output Changes

Grand Sport draft output should change only where section-to-step placement is intentionally corrected. The key expected placement changes are:

- `sec_gsha_001` moves from `exterior_appearance` to `aero_exhaust_stripes_accessories`.
- `sec_gsce_001` remains or moves to `aero_exhaust_stripes_accessories` depending on current output state.
- `sec_exha_001` moves to `packages_performance`.
- `sec_whee_001` moves to `wheels`.
- Standard equipment sections remain `standard_equipment`.
- Interior sections remain in their current interior steps.

Stingray output should remain stable unless the shared `section_master.step_key` values intentionally alter Stingray routing. If a `section_master.step_key` change would alter Stingray unexpectedly, stop and split Stingray compatibility into a separate spec instead of silently changing Stingray.

## Tests To Add Or Update

1. Workbook contract test:

   - `section_master` contains `step_key`.
   - every non-empty `section_id` row has a valid `step_key`.
   - no `category` column is required or referenced.

2. Grand Sport placement test:

   Assert generated Grand Sport draft sections resolve to the workbook-owned step keys for:

   - `sec_gsha_001`
   - `sec_gsce_001`
   - `sec_exha_001`
   - `sec_whee_001`
   - `sec_perf_001`
   - `sec_cali_001`
   - `sec_lpoi_001`

3. Override-reduction test:

   - Grand Sport should not require a model-specific override for sections already populated with `section_master.step_key`.

4. Regression tests:

   - Existing Stingray regression tests still pass.
   - Existing Grand Sport draft/runtime switching tests still pass.

## Validation Plan

Run:

```bash
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python -m py_compile scripts/corvette_form_generator/inspection.py scripts/corvette_form_generator/mapping.py scripts/corvette_form_generator/model_configs.py scripts/generate_grand_sport_form.py scripts/generate_stingray_form.py
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/stingray-form-regression.test.mjs
git diff --check
```

Manual verification after implementation:

- Open `stingray_master.xlsx` in Excel and confirm no repair dialog.
- Run local Grand Sport browser test and verify:
  - heritage/hash-mark sections are in the stripes/accessories step;
  - exhaust appears with performance;
  - wheels, calipers, and wheel accessories are grouped in the wheels step;
  - standard equipment does not duplicate visible selectable options.

## Non-Goals

- No price-rule changes.
- No rule-sheet simplification.
- No option copy cleanup.
- No display-order rewrite beyond step ownership.
- No Grand Sport runtime activation.
- No category restoration.
- No new model option source sheets.

## Success Criteria

- `section_master.step_key` owns normal section-to-step placement.
- Grand Sport draft generation does not need Grand Sport-specific step overrides for sections now covered by workbook rows.
- Grand Sport sections render in the intended steps without adding runtime business logic.
- Stingray regression tests pass.
- Workbook package remains Excel-safe.
