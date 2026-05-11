# Grand Sport Layout, Rules, And Interior Pricing Fix Spec

## Diagnosis

Grand Sport draft behavior is close, but the next QA notes span workbook data, generated draft data, and generic runtime handling.

Root causes from current evidence:

- `BCP` and `BCS` still auto-add `B6P` because `grandSport_rule_mapping` has active rows:
  - `gs_rule_opt_bcp_002_includes_opt_b6p_001`
  - `gs_rule_opt_bcs_002_includes_opt_b6p_001`
- `BC4`, `BCP`, and `BCS` already have workbook rows that include `D3V`, but only `B6P -> D3V` has a current price override.
- `D30` and `R6X` are active, non-selectable rows with `display_behavior=display_only`; `Z15` uses the better pattern: active, non-selectable, `display_behavior=auto_only`.
- Performance, aero, stripes, and accessories placement is workbook-owned through `section_master.step_key`, `section_master.display_order`, and model step labels/order in `scripts/corvette_form_generator/model_configs.py`.
- The draft seat choices currently show:
  - `1LT`: `AQ9` standard, `AE4` available, `AH2` unavailable.
  - `2LT`: `AQ9` standard, `AH2` unavailable, `AE4` unavailable.
  - `3LT`: `AH2` standard, `AQ9` unavailable, `AE4` unavailable.
  This points at `grandSport_ovs` status rows for seat options, not a frontend rendering problem.
- `J56` and `J57` are currently in a required single-select section, but `J57` uses replace rules against `J56`. That makes the selected default disappear instead of behaving like a normal radio replacement.
- `CFL excludes CFZ` exists, but `T0F includes CFZ`; the runtime must continue to block `CFL` when `CFZ` is selected or auto-added by `T0F`.
- Wheel source order is not ascending price if carbon wheels are listed before all lower-priced options.
- `Z25` currently carries the Launch Edition price, while the requested behavior is `EL9 = 1995` and `Z25 = 0`.

Risk level: medium-high. This touches option availability, price display, auto-adds, step order, section ownership, and interior pricing. Split implementation into focused passes.

## Goal

Fix the listed Grand Sport QA issues using workbook data wherever the workbook can express the business fact, and only add generic runtime/generator behavior where current wiring cannot interpret the workbook correctly.

## Constraints

- Do not activate Grand Sport production runtime.
- Preserve Stingray as the live production path.
- Do not hardcode Grand Sport RPO-specific business rules in scripts.
- Prefer workbook edits in:
  - `stingray_master.xlsx`
  - `grandSport_options`
  - `grandSport_ovs`
  - `grandSport_rule_mapping`
  - `grandSport_price_rules`
  - `grandSport_exclusive_groups`
  - `grandSport_exclusive_members`
  - `section_master`
  - `lt_interiors`
- Use generic code only for reusable behaviors:
  - step ordering/labels;
  - auto-only hidden options;
  - selected/auto-added exclusion handling;
  - interior price calculation if current logic double-counts seat vs interior prices.
- Do not delete option rows in this pass. Prefer `active=FALSE`, corrected status rows, corrected rules, or `generation_action=omit_*`.
- Save workbook through the hardened save path and validate package integrity after every workbook mutation.

## Files To Change

Workbook/source:

- `stingray_master.xlsx`
- Potentially `architectureAudit/grand_sport_interiors_refactor.csv` only if interior ordering/pricing must be corrected in the CSV source rather than `lt_interiors`.

Generator/runtime:

- `scripts/corvette_form_generator/model_configs.py`
- `scripts/corvette_form_generator/inspection.py`
- `scripts/generate_stingray_form.py` only if shared model registry or Stingray output needs regenerated support.
- `form-app/app.js`

Tests:

- `tests/grand-sport-draft-data.test.mjs`
- `tests/grand-sport-rule-audit.test.mjs`
- `tests/multi-model-runtime-switching.test.mjs`
- `tests/stingray-generator-stability.test.mjs`
- `tests/stingray-form-regression.test.mjs`
- `tests/grand-sport-contract-preview.test.mjs` if contract preview section placement expectations are still active.

Generated artifacts:

- `form-output/inspection/grand-sport-*.json`
- `form-output/inspection/grand-sport-*.md`
- `form-output/stingray-form-data.json`
- `form-app/data.js`

## Pass 1: Workbook Rule And Price Corrections

### Engine Covers

Workbook changes:

- Mark these rows omitted from runtime:
  - `gs_rule_opt_bcp_002_includes_opt_b6p_001`
  - `gs_rule_opt_bcs_002_includes_opt_b6p_001`
- Verify or add active includes rows:
  - `opt_bcp_002 includes opt_d3v_001`
  - `opt_bcs_002 includes opt_d3v_001`
  - `opt_bc4_002 includes opt_d3v_001`
- Add price overrides:
  - `condition_option_id=opt_bcp_002`, `target_option_id=opt_d3v_001`, `price_rule_type=override`, `price_value=0`
  - `condition_option_id=opt_bcs_002`, `target_option_id=opt_d3v_001`, `price_rule_type=override`, `price_value=0`
  - `condition_option_id=opt_bc4_002`, `target_option_id=opt_d3v_001`, `price_rule_type=override`, `price_value=0`
- Preserve `B6P -> D3V` for the Coupe Engine Appearance Package.

Expected test:

- Selecting `BCP`, `BCS`, or `BC4` auto-adds `D3V` at `$0`.
- Selecting `BCP`, `BCS`, or `BC4` does not auto-add `B6P`.

### Auto-Only Rows

Workbook changes:

- Change `opt_d30_001.display_behavior` from `display_only` to `auto_only`.
- Change `opt_r6x_001.display_behavior` from `display_only` to `auto_only`.
- Keep both active and non-selectable.

Runtime/generator verification:

- Existing hidden auto-only behavior used by `Z15` should apply to `D30` and `R6X`.
- Do not add RPO-specific script branches.

Expected test:

- `D30` and `R6X` do not render as selectable/display cards.
- They can still appear in auto-added/order output when selected context rules add them.

### Ground Effects Conflict

Workbook/runtime verification:

- Keep `opt_cfl_001 excludes opt_cfz_001`.
- Verify `disableReasonForChoice()` checks selected and auto-added IDs so `CFL` is blocked when `T0F` auto-adds `CFZ`.
- If the runtime does not block it, fix the generic selected-context path, not a `T0F/CFL` branch.

Expected test:

- Select `T0F`; `CFZ` is auto-added at `$0`.
- `CFL` is unavailable while `CFZ` is auto-added.

### J56 / J57

Workbook changes:

- Add `grandSport_exclusive_groups` row:
  - `group_id=gs_excl_performance_brakes`
  - `selection_mode=single_within_group`
  - `active=True`
  - notes: `J56 and J57 are mutually exclusive brake choices.`
- Add `grandSport_exclusive_members` rows:
  - `opt_j56_001`, display order `10`, active `True`
  - `opt_j57_001`, display order `20`, active `True`
- Keep `J56` `display_behavior=default_selected`.
- Remove or omit `opt_j57_001 excludes opt_j56_001` if the exclusive group makes it redundant and causes a one-way replacement problem.
- Preserve `opt_j57_001 excludes opt_j6a_001`, `runtime_action=replace`, because caliper default replacement is a separate section.

Expected test:

- `J56` starts selected.
- Selecting `J57` replaces `J56`.
- Selecting `J56` again replaces `J57`.
- There is no trapped state where `J57` cannot be unselected/replaced.

### EL9 / Z25 Price Ownership

Workbook changes:

- Set `opt_z25_001.price=0`.
- Set `lt_interiors` rows:
  - `3LT_AH2_EL9 Price=1995`
  - `3LT_AE4_EL9 Price=1995`, unless investigation proves this row already includes an AE4 seat upcharge that should be separated.
- Preserve:
  - `3LT_AH2_EL9 includes opt_z25_001`
  - `3LT_AE4_EL9 includes opt_z25_001`

Interior pricing investigation:

- Inspect how `adjustedInteriorPrice()` subtracts selected seat `base_price`.
- Inspect generated `data.interiors` for `price`, `seat_code`, `interior_code`, and any component price fields.
- Decide whether the workbook should store total interior package price or color-only delta.

Expected test:

- Selecting an EL9 interior shows the Launch Edition price on the interior choice.
- Auto-added `Z25` appears at `$0`.
- The selected interior and auto-added `Z25` do not double-charge the Launch Edition.

## Pass 2: Step And Section Ownership

### Step Labels And Order

Modify `scripts/corvette_form_generator/model_configs.py`:

- Change step label:
  - `packages_performance`: `Performance & Aero`
  - `aero_exhaust_stripes_accessories`: `Stripes`
- Add new step key after `interior_trim`:
  - `accessories`: `Accessories`

Update model step order:

1. Body Style
2. Trim Level
3. Exterior Paint
4. Exterior Appearance
5. Wheels & Brake Calipers
6. Performance & Aero
7. Stripes
8. Seats
9. Base Interior
10. Seat Belt
11. Interior Trim
12. Accessories
13. Custom Delivery
14. Customer Information
15. Summary

### Section Placement

Workbook `section_master` changes:

- Rename `sec_perf_support_001.section_name` from `Performance Support` to `Mechanical`.
- Move these sections to `wheels`:
  - `sec_perf_brake_001` Performance Brakes
  - `sec_perf_support_001` Mechanical
- Keep or move these sections in `packages_performance` / Performance & Aero:
  - packages: `sec_perf_z52_001`
  - exhaust: `sec_exha_001`
  - aero: `sec_perf_aero_001`
  - ground effects: `sec_perf_ground_001`
- Set section display order within Performance & Aero:
  - `sec_perf_z52_001` order `10`
  - `sec_exha_001` order `20`
  - `sec_perf_aero_001` order `30`
  - `sec_perf_ground_001` order `40`
- Move stripes-only sections to the renamed `aero_exhaust_stripes_accessories` step:
  - `sec_gsha_001`
  - `sec_gsce_001`
  - `sec_stri_001`
- Move exterior and interior accessories to new `accessories` step:
  - `sec_lpoe_001`
  - `sec_lpow_001`
  - `sec_lpoi_001`
  - likely `sec_whee_001` only if the user considers wheel accessories accessory-step content; otherwise keep it under Wheels & Brake Calipers.

Runtime order-section labels:

- Update `form-app/app.js` summary grouping only if order summary section labels still show old `Aero, Exhaust, Stripes & Accessories` or put accessories under the wrong group.
- Keep this generic by mapping step keys to order-summary section keys.

Expected tests:

- Draft steps show `Performance & Aero`, `Stripes`, and `Accessories`.
- `Mechanical` and `Performance Brakes` are under Wheels & Brake Calipers.
- Performance & Aero section order is packages, exhaust, aero, ground effects.
- Stripes step contains hash marks, center stripes, and stripes only.
- Accessories step contains exterior accessories and LPO Interior.

## Pass 3: Wheels And Seat Availability

### Wheels

Workbook changes in `grandSport_options`:

- For active `sec_whee_002` rows, set `display_order` by ascending price:
  - `SWM` `$0`
  - `SWN` `$1095`
  - `SWO` `$1495`
  - `SWP` `$1495`
  - `ROY` `$11995`
  - `ROZ` `$13995`
  - `STZ` `$15500`
- Carbon fiber wheels naturally remain last because their prices are highest.
- Keep deterministic ordering for ties using current source/order preference.

Expected test:

- Grand Sport wheel choices render in ascending price order.

### Seat Availability

Workbook `grandSport_ovs` changes:

- Audit status rows for `opt_aq9_001`, `opt_ah2_001`, and `opt_ae4_002`.
- Correct availability so the seat step shows the intended selectable seat choices per trim.
- Current draft evidence shows 2LT and 3LT optional seats are unavailable:
  - `2LT`: `AH2` unavailable, `AE4` unavailable.
  - `3LT`: `AE4` unavailable.
- Keep canonical active seat option rows in `grandSport_options`; do not reactivate old duplicate AQ9/AH2/AE4 rows unless the status-source shape cannot express trim availability.

Expected test:

- The seat step shows more than only the standard seat where optional seats should be available.
- Interior choices filter correctly by selected seat.
- Prices are not duplicated between seat selection and interior color selection.

## Pass 4: Regenerate And Browser Verify

Run:

```bash
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/generate_grand_sport_form.py
.venv/bin/python scripts/generate_stingray_form.py
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/grand-sport-rule-audit.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/stingray-form-regression.test.mjs
git diff --check
```

Manual browser checks:

```bash
/Users/seandm/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m http.server 8081
```

Open:

```text
http://127.0.0.1:8081/form-app/
```

Switch model to Grand Sport and verify:

- `BCP`, `BCS`, and `BC4` auto-add `D3V` at `$0`, not `B6P`.
- `D30`, `R6X`, `Z15`, and `Z25` never appear as selectable cards.
- `D30`, `R6X`, `Z15`, and `Z25` can still appear as auto-added items when rules add them.
- Step 6 label is `Performance & Aero`.
- Step 7 label is `Stripes`.
- A new `Accessories` step appears after `Interior Trim`.
- Performance & Aero order is packages, exhaust, aero, ground effects.
- Wheels are sorted by ascending price with carbon fiber wheels last.
- Seats show the intended optional seats by trim.
- EL9 price displays on the interior row and `Z25` auto-adds at `$0`.
- Selecting `T0F` auto-adds `CFZ` and blocks `CFL`.
- `J56` and `J57` behave as replaceable radio choices.

## Non-Goals

- Do not solve assets/images in this pass.
- Do not reactivate Grand Sport variants in `variant_master`.
- Do not combine Stingray and Grand Sport option sheets.
- Do not redesign the frontend.
- Do not create a new rule schema unless the existing workbook sheets cannot express the needed behavior.

## Approval Checkpoint

After approval, execute in passes:

1. Workbook rule/price corrections for engine covers, D30/R6X, J56/J57, CFL/CFZ, EL9/Z25.
2. Step/section ownership and label changes.
3. Seat availability and wheel ordering.
4. Regenerate, run gates, and browser smoke test.
