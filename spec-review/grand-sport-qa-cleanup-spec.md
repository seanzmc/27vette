# Grand Sport QA Cleanup Spec

## Diagnosis

The current Grand Sport draft is improving, but several remaining issues come from three mixed surfaces:

1. Workbook source rows need cleanup:
   - `grandSport_options`
   - `grandSport_rule_mapping`
   - `grandSport_price_rules`
   - `grandSport_exclusive_groups`
   - `grandSport_exclusive_members`
   - `grandSport_rule_groups`
   - `grandSport_rule_group_members`
   - `section_master`
   - `lt_interiors`
   - `architectureAudit/grand_sport_interiors_refactor.csv`

2. A few requested behaviors need generic runtime support, not hardcoded Grand Sport facts:
   - workbook-owned default-selected options in multi-select sections;
   - workbook-owned grouped exclusions if we want to replace many stripe conflict rows with a compact rule group.

3. Some older code still owns Grand Sport facts that should move to workbook rows:
   - `scripts/corvette_form_generator/inspection.py` currently hardcodes `GRAND_SPORT_ONLY_INTERIOR_IDS` for EL9/Z25 metadata.

Risk level: medium. This touches cross-option compatibility, auto-added line items, default selections, section ordering, and generated form output. Keep the implementation split into small passes and verify each pass.

## Current Evidence

Observed in `stingray_master.xlsx`:

- `Z15` is active, non-selectable, and `display_behavior=display_only`; it still appears as a visible display card.
- `Z25` is active/selectable in `sec_spec_001`.
- `J57 -> J6D` currently exists as an `includes` rule, but the desired rule is `J6D requires J57`.
- `CFL excludes CFZ` already exists in `grandSport_rule_mapping`.
- `FEB` and `FEY` already have an exclusive group in `grandSport_exclusive_groups`.
- `grandSport_rule_groups` is currently empty.
- `sec_exte_001` is `single_select_req`, which prevents `ZYC` from being selected independently with the exterior accent choice.
- Current stripe section ordering is:
  - `sec_stri_001` display order `50`
  - `sec_gsce_001` display order `51`
  - `sec_gsha_001` display order `52`
  Desired order is hash marks, center stripes, then regular stripes.
- Active canonical LS6 cover rows appear to be:
  - `opt_bc7_001`
  - `opt_bcp_002`
  - `opt_bcs_002`
  - `opt_bc4_002`
  Older inactive duplicates still exist:
  - `opt_bcp_001`
  - `opt_bcs_001`
  - `opt_bc4_001`
- Several active rules still reference inactive LS6 duplicate rows. Engine covers need a focused rule audit before mutation.

## Goal

Fix the listed Grand Sport QA notes by moving business facts into workbook rows, adding only generic runtime support where the workbook already has a shape for the behavior, and keeping Grand Sport draft-only until the browser output is verified.

## Non-Goals

- Do not activate Grand Sport production runtime.
- Do not change Stingray workbook rules or Stingray runtime behavior except through generic runtime support that existing Stingray tests prove stable.
- Do not add hardcoded Grand Sport RPO logic to scripts.
- Do not create a new workbook schema unless existing sheets cannot express the behavior.
- Do not delete option rows in this pass. Prefer `active=FALSE`, `display_behavior`, or corrected rule rows.

## Action Plan

### Pass 1: Rule Audit And Canonical IDs

Produce/update an audit artifact that specifically flags:

- duplicate semantic Grand Sport rule rows:
  - `source_id`
  - `rule_type`
  - `target_id`
  - `body_style_scope`
  - `runtime_action`
- active rules where `source_id` or `target_id` is missing from `grandSport_options`;
- active rules where `source_id` or `target_id` points at an inactive option row;
- active rules where the same RPO has both active and inactive option IDs and the rule targets the inactive ID;
- engine-cover rules involving:
  - `BC7`
  - `BCP`
  - `BCS`
  - `BC4`
  - `B6P`
  - `ZZ3`
  - `D3V`
  - `SL9`

Preferred output:

- update `form-output/inspection/grand-sport-rule-audit.json`;
- update `form-output/inspection/grand-sport-rule-audit.md`;
- add a focused summary table in `spec-review/grand-sport-source-cleanup-audit.md` only if the existing generated audit is too broad to review quickly.

Do not change workbook rows until this audit is readable.

### Pass 2: Workbook Row Fixes

#### Engine Covers

Use canonical active IDs:

| RPO | canonical option_id |
| --- | --- |
| `BC7` | `opt_bc7_001` |
| `BCP` | `opt_bcp_002` |
| `BCS` | `opt_bcs_002` |
| `BC4` | `opt_bc4_002` |

Workbook changes:

- Add or correct active convertible rules so `BCP`, `BCS`, and `BC4` use the same `ZZ3` compatibility pattern as `BC7`:
  - `opt_bcp_002 requires opt_zz3_001`, `body_style_scope=convertible`
  - `opt_bcs_002 requires opt_zz3_001`, `body_style_scope=convertible`
  - `opt_bc4_002 requires opt_zz3_001`, `body_style_scope=convertible`
- Keep `opt_bc7_001 requires opt_zz3_001`, `body_style_scope=convertible`.
- Deactivate or remove from runtime any active rules that point at inactive duplicate source rows:
  - `opt_bcp_001`
  - `opt_bcs_001`
  - `opt_bc4_001`
- Preserve existing price rules that set active LS6 cover pricing with `B6P` / `ZZ3`, but ensure all target IDs use canonical active IDs.
- Preserve `gs_excl_ls6_engine_covers`, but remove inactive duplicate members from active membership or mark those members `active=FALSE`.

#### Exterior Accents

Current issue: `EFR`, `EDU`, and `ZYC` share `sec_exte_001`, which is `single_select_req`, so `ZYC` cannot be selected independently.

Workbook changes:

- Change `section_master.sec_exte_001.selection_mode` from `single_select_req` to `multi_select_opt`.
- Add `grandSport_exclusive_groups` row:
  - `group_id=gs_excl_exterior_accents`
  - `selection_mode=single_within_group`
  - `active=True`
  - notes: `EFR and EDU are mutually exclusive; ZYC remains selectable independently.`
- Add `grandSport_exclusive_members` rows:
  - `opt_efr_001`
  - `opt_edu_001`
- Make `EFR` workbook-default selected using the generic default-selection behavior described in Pass 3.
- Leave `ZYC` out of the exclusive group.

#### Wheels And Calipers

Workbook display-order changes:

Primary wheels, `sec_whee_002`:

| RPO | intended order |
| --- | ---: |
| `SWM` | 10 |
| `SWN` | 20 |
| `SWO` | 30 |
| `SWP` | 40 |
| `ROY` | 50 |
| `ROZ` | 60 |
| `STZ` | 70 |

Wheel accessories, `sec_whee_001`:

| group | intended order |
| --- | ---: |
| lug nuts | 10-19 |
| wheel locks | 20-29 |
| center caps | 30-39 |

Calipers, `sec_cali_001`:

- Keep `J6A` first as the normal default caliper.
- Keep `J6D` near `J57`-related calipers, but do not auto-add it from `J57`.
- Add/correct rules:
  - `opt_j6d_001 requires opt_j57_001`
  - `opt_j57_001 excludes opt_j6a_001`, `runtime_action=replace`, disabled reason like `J57 replaces black painted calipers.`
- Remove or deactivate current `opt_j57_001 includes opt_j6d_001`.

#### Stripes

Workbook section display order:

| section_id | section_name | display_order |
| --- | --- | ---: |
| `sec_gsha_001` | GS Hash Marks | 50 |
| `sec_gsce_001` | GS Center Stripes | 51 |
| `sec_stri_001` | Stripes | 52 |

Workbook option behavior:

- Set `opt_z15_001.display_behavior=auto_only`.
- Keep `opt_z15_001.selectable=FALSE`.
- Keep `opt_z15_001.active=TRUE`.
- Do not show `Z15` as a selectable or display-only card.
- Hash mark options should include disclosure text in their displayed description indicating that selecting a hash mark includes/adds `Z15` Grand Sport Heritage Graphics.
- Keep center stripes compatible with hash marks.

Heritage conflict cleanup:

- Preferred: add generic grouped exclusion support in Pass 3 and replace repeated hash-mark-to-full-stripe rows with a compact group:
  - `grandSport_rule_groups.group_id=gs_group_z15_excludes_non_center_stripes`
  - `group_type=excludes_any`
  - `source_id=opt_z15_001`
  - target members: all regular full-length stripe/graphic option IDs that should be unavailable when `Z15` is auto-added.
- If grouped exclusions are not implemented in Pass 3, use explicit `grandSport_rule_mapping` rows with `source_id=opt_z15_001`, not one row per hash mark.
- Deactivate old repeated hash-mark conflict rows after the `Z15` source rule/group is verified.

#### Z25 / EL9

Workbook changes:

- Set `opt_z25_001.display_behavior=auto_only`.
- Set `opt_z25_001.selectable=FALSE`.
- Keep `opt_z25_001.active=TRUE`.
- Add `grandSport_rule_mapping` rows:
  - `3LT_AE4_EL9 includes opt_z25_001`
  - `3LT_AH2_EL9 includes opt_z25_001`
- Add Z25 price disclosure to the displayed EL9 interior description/source note so the price is visible before selection.
- Move EL9 interior choices to the top of the 3LT interior color display by updating `architectureAudit/grand_sport_interiors_refactor.csv` ordering:
  - `3LT_AH2_EL9` should be the first AH2 3LT interior color choice.
  - `3LT_AE4_EL9` should be the first AE4 3LT interior color choice.

Code cleanup:

- Remove hardcoded `GRAND_SPORT_ONLY_INTERIOR_IDS` ownership from `scripts/corvette_form_generator/inspection.py`.
- Preserve `requires_z25` only if it can be derived from workbook data. Preferred derivation:
  - `requires_z25=True` when an active `grandSport_rule_mapping` row has `source_id=<interior_id>`, `rule_type=includes`, and `target_id=opt_z25_001`.
- If `requires_z25` is no longer needed by runtime, remove it from tests instead of preserving stale metadata.

#### Performance Section Split

Add new `section_master` rows under `step_key=packages_performance`.

Use existing section IDs only if they already exist; otherwise add new IDs:

| section_id | section_name | selection_mode | display_order | intended RPOs |
| --- | --- | --- | ---: | --- |
| `sec_perf_support_001` | Performance Support | `multi_select_opt` | 10 | `ERI`, `E60` |
| `sec_perf_ground_001` | Ground Effects | `single_select_opt` | 20 | `CFL`, `CFZ`, inactive `CFV` |
| `sec_perf_z52_001` | Z52 Packages | `single_select_opt` | 30 | `FEB`, `FEY` |
| `sec_perf_aero_001` | Aero Packages | `single_select_req` | 40 | `T0E`, `T0F`, `5ZV` |
| `sec_perf_brake_001` | Performance Brakes | `single_select_req` | 50 | `J56`, `J57` |

Move `grandSport_options.section_id`:

- `ERI`, `E60` -> `sec_perf_support_001`
- `CFL`, `CFZ`, `CFV` -> `sec_perf_ground_001`
- `FEB`, `FEY` -> `sec_perf_z52_001`
- `T0E`, `T0F`, `5ZV` -> `sec_perf_aero_001`
- `J56`, `J57` -> `sec_perf_brake_001`

Default behavior:

- `T0E` should be selected by default using generic default-selection support from Pass 3.
- `J56` should be the standard/default brake row in the Performance Brakes section.
- Selecting `J57` should replace/unselect `J56`.

Rules:

- Add or verify:
  - `opt_t0f_001 includes opt_cfz_001`
  - `opt_t0f_001 requires opt_feb_001`
  - `opt_t0f_001 requires opt_j57_001`
  - `opt_fey_001 excludes opt_t0e_001`, `runtime_action=replace`
  - `opt_cfl_001 excludes opt_cfz_001`
  - `opt_j57_001 excludes opt_j56_001`, `runtime_action=replace`
  - `opt_j57_001 excludes opt_j6a_001`, `runtime_action=replace`
  - `opt_j6d_001 requires opt_j57_001`
- Add price rule:
  - `condition_option_id=opt_t0f_001`
  - `target_option_id=opt_cfz_001`
  - `price_rule_type=override`
  - `price_value=0`
- Keep existing `FEY` auto-add and price override rows for `J57`, `T0F`, `WUB`, and `CFZ`.

## Pass 3: Generic Runtime Support

### Default-Selected Options

Problem: workbook rows can mark standard/default status, but the runtime only default-selects a hardcoded list:

```js
["FE1", "NGA", "BC7"]
```

Add a generic workbook-owned display behavior:

```text
display_behavior=default_selected
```

Semantics:

- option is visible and selectable like a normal option;
- on body/trim reset, runtime selects it by default if:
  - choice is active;
  - choice is not unavailable;
  - choice applies to current body/trim;
  - no user-selected or auto-added option already occupies the same single-select section;
- user can replace or remove it if section rules allow.

Use this for:

- `T0E`
- `EFR`
- `J56`, if J56 is displayed in Performance Brakes

Do not hardcode those RPOs in `form-app/app.js`.

### Grouped Exclusions

Existing `rule_groups` runtime support only handles `requires_any`.

Add generic support for:

```text
group_type=excludes_any
```

Semantics:

- `source_id` excludes every active member in `rule_group_members`.
- The disabled reason should come from `rule_groups.disabled_reason` when present.
- `ruleGroupAppliesToCurrentVariant()` scope fields continue to apply.
- This must work when `source_id` is auto-added, because `Z15` will be auto-added from hash marks.
- Existing `requires_any` behavior must remain unchanged.

Generator updates:

- `build_draft_rules()` should treat grouped exclusions the way it currently treats grouped requirements:
  - grouped exclusion pairs should not need duplicated `grandSport_rule_mapping` rows;
  - audit output should count grouped exclusions separately.

Runtime updates:

- `disableReasonForChoice()` should block a target choice when a selected or auto-added source has an applicable `excludes_any` group containing that target.
- `selectedExcludesTarget()` should include grouped exclusions so auto-added options do not fight with selected excluded targets.
- `reconcileSelections()` should remove already-selected choices that become invalid because an auto-added source such as `Z15` activates a grouped exclusion.

## Reverse Rule Decision

Do not blanket-add reverse rows.

Current runtime checks both directions for `excludes` availability:

- if selected source excludes target, target is disabled;
- if the candidate choice itself excludes an already selected target, the candidate is disabled.

Therefore, reverse `excludes` rows are generally unnecessary and create clutter. Add reverse rows only if a test proves a specific runtime surface does not behave correctly without them.

`requires` and `includes` should remain directional.

## Files To Change

Workbook/source files:

- `stingray_master.xlsx`
- `architectureAudit/grand_sport_interiors_refactor.csv`

Runtime/generator files:

- `scripts/corvette_form_generator/inspection.py`
- `scripts/build_grand_sport_rule_sources.py`
- `form-app/app.js`
- `scripts/generate_stingray_form.py` only if shared generated output wiring requires it

Tests:

- `tests/grand-sport-draft-data.test.mjs`
- `tests/grand-sport-rule-audit.test.mjs`
- `tests/multi-model-runtime-switching.test.mjs`
- `tests/stingray-generator-stability.test.mjs`
- `tests/stingray-form-regression.test.mjs` for generic runtime behavior stability

Generated artifacts:

- `form-output/inspection/grand-sport-form-data-draft.json`
- `form-output/inspection/grand-sport-form-data-draft.md`
- `form-output/inspection/grand-sport-rule-audit.json`
- `form-output/inspection/grand-sport-rule-audit.md`
- `form-app/data.js`

## Tests To Add Or Update

### Workbook Contract Tests

Assert:

- `display_behavior` accepts `default_selected`, `auto_only`, `display_only`, `hidden`, or blank.
- `grandSport_rule_groups` accepts both:
  - `requires_any`
  - `excludes_any`
- `grandSport_rule_group_members` target IDs all exist in `grandSport_options`.
- `grandSport_exclusive_members` option IDs all exist in `grandSport_options`.
- active rule rows do not reference inactive option IDs unless `generation_action` explicitly omits them from runtime.

### Draft Data Tests

Assert:

- `Z15` is not visible as a manual/display-only choice in the Stripes step.
- hash marks include or auto-add `Z15`.
- `Z15` grouped exclusions make regular full-length stripes unavailable while center stripes remain compatible.
- `Z25` is not visible as a manual/display-only choice.
- selecting EL9 interiors can auto-add `Z25`.
- EL9 interiors sort first within their 3LT seat/interior groups.
- `T0E` is default-selected in the Grand Sport runtime.
- `T0F` auto-adds/sets `CFZ` to `$0`.
- `J6D` requires `J57`.
- `J57` replaces `J56` and `J6A` defaults.
- `EFR` and `EDU` are mutually exclusive, while `ZYC` can be selected independently.
- performance sections render in the intended order:
  - Performance Support
  - Ground Effects
  - Z52 Packages
  - Aero Packages
  - Performance Brakes
- stripe sections render in the intended order:
  - GS Hash Marks
  - GS Center Stripes
  - Stripes

### Runtime Tests

Assert:

- generic `display_behavior=default_selected` drives default selection without hardcoded Grand Sport RPO checks.
- generic `excludes_any` rule groups disable and reconcile targets.
- auto-added sources can activate grouped exclusions.
- Stingray still passes existing defaults and compatibility tests.

## Validation Plan

Run after each pass:

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

- Start local server:

```bash
/Users/seandm/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m http.server 8080
```

- Open:

```text
http://127.0.0.1:8080/form-app/?model=grandSport
```

Verify:

- no `Z15` selectable/display card;
- hash mark selection auto-adds `Z15` and blocks non-center stripes;
- center stripes remain compatible with hash marks;
- no `Z25` selectable/display card;
- EL9 appears first and auto-adds `Z25`;
- EFR/EDU are mutually exclusive and ZYC remains independently selectable;
- T0E starts selected by default;
- selecting FEY replaces T0E and auto-adds included package rows at the correct price;
- T0F sets CFZ price to `$0`;
- J6D is unavailable until J57 is selected;
- J57 replaces J56/J6A defaults;
- wheel and performance section order matches the spec.

## Success Criteria

- All listed QA notes are represented as workbook data or generic workbook interpreters.
- No new Grand Sport-specific business facts are hardcoded in runtime scripts.
- Rule clutter is reduced for heritage stripes through grouped exclusions or at least centralized `Z15` source rules.
- Engine cover rules no longer point at inactive duplicate IDs.
- Grand Sport local browser flow matches expected availability, auto-adds, prices, defaults, and display order.
- Stingray regression tests remain green.
