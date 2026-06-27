# Pass 16 — Variant Override Sheet Semantics Report

Status: Completed report-only classification.
Date: 2026-06-24

## Executive summary

This pass was read-only except for this report and the matching spec/docs status updates.

The three active variant override sheets are not one uniform cleanup surface:

- `variant_option_overrides` is a global/Stingray contract. Its `active` column is an emitted override value, not row activation. All 7 rows are consumed. Deleting or filtering `active=False` rows would lose the Stingray UQT paid-option suppression for 2LT/3LT.
- `grandSport_variant_overrides` and `z06_variant_overrides` are model-scoped fallback contracts. Their `active` column is row activation. They currently carry `selectable`, `display_behavior`, and `section_id` overrides.
- UQT included-equipment placement/selectability is not fully owned by `*_ovs`; OVS owns status only. The current override rows also move choices into trim-standard sections and make them display-only/nonselectable. Treat UQT as a source-row remodel or generator-derivation candidate, not a simple deletion candidate.
- BC7 and Grand Sport NGA default-selected rows are cleaner candidates for generator derivation. Existing `default_selection_rules` plus exclusive groups already own most runtime selected/restoration behavior, but generated `display_behavior=default_selected` still comes from override rows for Stingray/Grand Sport BC7 and Grand Sport NGA.
- Do not propose a sheet-wide delete pass. Split follow-up implementation by behavior class: default-selected metadata first, then UQT trim-standard placement after a dedicated design/spec.

## Preflight and evidence sources

Preflight:

- `git status --short --branch`: `## schema-ingestion-normalization...origin/main`; no dirty files at Pass 16 start.
- Workbook lock probe: no `~$stingray_master.xlsx` lock file.
- Workbook inspection used `openpyxl.load_workbook(..., read_only=True, data_only=True)`.
- Generated contract inspection read checked-in JSON under `form-output/runtime/`; no generator was run.
- No workbook writes, generator writes, runtime edits, or tests were changed.

Primary evidence inspected:

- `stingray_master.xlsx` sheets: `variant_option_overrides`, `grandSport_variant_overrides`, `z06_variant_overrides`, `model_workbook_sources`, `*_options`, `*_ovs`, `default_selection_rules`, `exclusive_groups`, `exclusive_group_members`, `section_presentation`.
- Generated contracts: `form-output/runtime/stingray-runtime-contract.json`, `form-output/runtime/grand-sport-runtime-contract.json`, `form-output/runtime/z06-runtime-contract.json`.
- Code consumers: `scripts/corvette_form_generator/runtime_metadata.py`, `production.py`, `inspection.py`, `schema_validation.py`, `editor_ops.py`, `model_config.py`.
- Test consumers: `tests/stingray-generator-stability.test.mjs`, `tests/stingray-form-regression.test.mjs`, `tests/grand-sport-draft-data.test.mjs`, `tests/z06-form-data-draft.test.mjs`, `tests/workbook-schema-standardization.test.mjs`, `tests/workbook-visual-copy-standardization.test.mjs`.

## Source-of-truth summary by override sheet

| Sheet | Rows | Headers | Row activation semantics | Emitted override fields | Generator path(s) | Generated fields affected |
|---|---:|---|---|---|---|---|
| `variant_option_overrides` | 7 | `model_key`, `option_id`, `variant_id`, `status`, `selectable`, `active`, `display_behavior`, `notes` | `active` is an emitted choice value, not row activation. `runtime_metadata.load_variant_option_overrides()` reads with `optional_rows()` and keeps `active=False` rows. | `status`, `selectable`, `active`, `display_behavior`, `notes` | `runtime_metadata.py:232-276`; Stingray `production.py:194-200`, `production.py:331-339` | choice `status`, `selectable`, `active`, `display_behavior` |
| `grandSport_variant_overrides` | 13 / 13 active | `option_id`, `variant_id`, `selectable`, `display_behavior`, `section_id`, `active`, `note` | `active` is conventional row activation. Loader uses `active_rows()` only because no global rows are sourced for Grand Sport. | `selectable`, `display_behavior`, `section_id`, `note`; `status`/emitted `active` are neutralized by loader | `runtime_metadata.py:232-276`; `inspection.py:286-302`, `inspection.py:663-664`, `inspection.py:792-827` | choice `selectable`, `display_behavior`, `section_id`, derived `step_key`; display behavior then affects emitted `status`/`active` via `display_behavior_status()` |
| `z06_variant_overrides` | 4 / 4 active | `option_id`, `variant_id`, `selectable`, `display_behavior`, `section_id`, `active`, `note` | Same model-scoped row-activation contract as Grand Sport. | `selectable`, `display_behavior`, `section_id`, `note`; `status`/emitted `active` are neutralized by loader | same loader/inspection path as Grand Sport | choice `selectable`, `display_behavior`, `section_id`, derived `step_key`; display behavior then affects emitted `status`/`active` |

## Code consumer inventory

- `scripts/corvette_form_generator/runtime_metadata.py:232-276` is the central loader and explicitly documents the split semantics. Lines 250-254 read global `variant_option_overrides` with `optional_rows()` for model/global rows. Lines 255-256 fall back to the model-scoped sheet with `active_rows()` only if no global rows were sourced. Lines 267-272 emit `status`/`active` only for value-active global rows and normalize `section_id`/`note` for fallback rows.
- `scripts/corvette_form_generator/production.py:194-200` loads Stingray overrides into a keyed map. `production.py:331-339` applies override `status`, `selectable`, `active`, and `display_behavior` before emitting choices; `production.py:372-373` writes `display_behavior` when present.
- `scripts/corvette_form_generator/inspection.py:286-302` keys and applies model-scoped overrides. `inspection.py:792-827` applies the override per choice, optionally honors override `status`, calls `display_behavior_status()`, and emits `section_id`, `selectable`, `active`, and `display_behavior`.
- `scripts/corvette_form_generator/schema_validation.py:38-45` validates `active` and `selectable` as boolean columns for any `variant_option_overrides_sheet` role, but it does not distinguish global value-active semantics from model-scoped row-active semantics.
- `scripts/corvette_form_generator/editor_ops.py:44` maps `variant_option_overrides_sheet` into the editor `variant_overrides` family.
- `scripts/corvette_form_generator/model_config.py:43` carries the configured fallback sheet name for model config resolution.

## Test anchor inventory

- `tests/stingray-generator-stability.test.mjs:394-417` pins the four Stingray UQT override rows in `variant_option_overrides` and guards against hardcoded `opt_uqt_002` logic in the generator.
- `tests/stingray-form-regression.test.mjs:529-609` pins runtime BC7 default/replacement behavior for Stingray engine covers. It proves runtime selected-state behavior, not the source of generated `display_behavior=default_selected`.
- `tests/grand-sport-draft-data.test.mjs:239-270` pins Grand Sport UQT placement: 1LT UQT stays selectable in `sec_inte_001`; 2LT/3LT UQT becomes standard, nonselectable, and in `sec_2lte_001`/`sec_3lte_001` with `step_key=standard_equipment`.
- `tests/grand-sport-draft-data.test.mjs:538-550` pins Grand Sport BC7 coupe `default_selected` metadata and Grand Sport NGA all-variant `default_selected` metadata.
- `tests/z06-form-data-draft.test.mjs:201-212` and `:529-535` pin default-selected Z06 choices as selectable, but those checks are broader than the UQT override class. Current Z06 UQT display-only rows are not directly named in this file.
- `tests/workbook-schema-standardization.test.mjs:50-57`, `:88-90`, and `:127-131` include `grandSport_variant_overrides` / `z06_variant_overrides` in source-sheet/header/type coverage and assert Grand Sport variant override `active`/`selectable` cell types are boolean.
- `tests/workbook-visual-copy-standardization.test.mjs` reads active option rows across promoted option sheets; it is adjacent source-data hygiene, not a direct override-semantics pin.
- `tests/grand-sport-contract-preview.test.mjs` and `tests/z06-contract-preview.test.mjs` did not contain direct `UQT`/`BC7`/`NGA` override assertions in the current grep probe.

## Row-level inventory and classification

Classification vocabulary:

- `keep-canonical-currently`: current row is the clearest owner until a replacement design exists.
- `candidate-existing-owner`: behavior appears expressible by existing workbook owner(s), but parity proof is still required.
- `candidate-generator-derivation`: source facts already exist, but generator logic would need to derive emitted fields from canonical rows.
- `candidate-source-row-remodel`: current source/OVS rows cannot express the behavior without remodeling source rows or standard-equipment placement metadata.
- `needs-product-decision`: product semantics are unclear.

| Sheet row | Model | Option / RPO / label | Variant | Override fields | Current generated choice result | Current tests | Likely canonical owner | Classification |
|---|---|---|---|---|---|---|---|---|
| `variant_option_overrides:2` | Stingray | `opt_uqt_002` / UQT / Performance Data and Video Recorder | `2lt_c07` / 2LT coupe | `status=unavailable`, `selectable=False`, `active=False` | paid UQT emits in `sec_inte_001` as unavailable, nonselectable, inactive, price 1495 | `stingray-generator-stability.test.mjs:394-417` | OVS/source rows do not fully replace this; paid 1LT-only source model or generator derivation needed | `candidate-source-row-remodel` |
| `variant_option_overrides:3` | Stingray | `opt_uqt_002` / UQT / Performance Data and Video Recorder | `3lt_c07` / 3LT coupe | same | same | same | same | `candidate-source-row-remodel` |
| `variant_option_overrides:4` | Stingray | `opt_uqt_002` / UQT / Performance Data and Video Recorder | `2lt_c67` / 2LT convertible | same | same | same | same | `candidate-source-row-remodel` |
| `variant_option_overrides:5` | Stingray | `opt_uqt_002` / UQT / Performance Data and Video Recorder | `3lt_c67` / 3LT convertible | same | same | same | same | `candidate-source-row-remodel` |
| `variant_option_overrides:6` | Stingray | `opt_bc7_001` / BC7 / Black LS6 Engine Cover | `1lt_c07` / 1LT coupe | `active=True`, `display_behavior=default_selected` | BC7 coupe emits standard/selectable/active/default-selected in `sec_engi_001` | `stingray-form-regression.test.mjs:582-609` for runtime behavior; generated metadata not directly pinned there | `default_selection_rules.default_bc7` + `exclusive_groups.grp_ls6_engine_covers`; generator would need to derive display metadata | `candidate-generator-derivation` |
| `variant_option_overrides:7` | Stingray | `opt_bc7_001` / BC7 / Black LS6 Engine Cover | `2lt_c07` / 2LT coupe | same | same | same | same | `candidate-generator-derivation` |
| `variant_option_overrides:8` | Stingray | `opt_bc7_001` / BC7 / Black LS6 Engine Cover | `3lt_c07` / 3LT coupe | same | same | same | same | `candidate-generator-derivation` |
| `grandSport_variant_overrides:2` | Grand Sport | `opt_uqt_001` / UQT / Performance Data and Video Recorder | `2lt_e07` / 2LT coupe | `selectable=False`, `display_behavior=display_only`, `section_id=sec_2lte_001` | UQT emits standard/nonselectable/display-only in `sec_2lte_001`, `step_key=standard_equipment`, price 1495 | `grand-sport-draft-data.test.mjs:239-270` | OVS status + option row do not own section/selectability; section/standard-equipment metadata or source-row remodel needed | `candidate-source-row-remodel` |
| `grandSport_variant_overrides:3` | Grand Sport | `opt_uqt_001` / UQT / Performance Data and Video Recorder | `2lt_e67` / 2LT convertible | same, `section_id=sec_2lte_001` | same | same | same | `candidate-source-row-remodel` |
| `grandSport_variant_overrides:4` | Grand Sport | `opt_uqt_001` / UQT / Performance Data and Video Recorder | `3lt_e07` / 3LT coupe | `selectable=False`, `display_behavior=display_only`, `section_id=sec_3lte_001` | UQT emits standard/nonselectable/display-only in `sec_3lte_001`, `step_key=standard_equipment`, price 1495 | same | same | `candidate-source-row-remodel` |
| `grandSport_variant_overrides:5` | Grand Sport | `opt_uqt_001` / UQT / Performance Data and Video Recorder | `3lt_e67` / 3LT convertible | same, `section_id=sec_3lte_001` | same | same | same | `candidate-source-row-remodel` |
| `grandSport_variant_overrides:6` | Grand Sport | `opt_bc7_001` / BC7 / Black LS6 Engine Cover | `1lt_e07` / 1LT coupe | `display_behavior=default_selected` | BC7 coupe emits standard/selectable/active/default-selected | `grand-sport-draft-data.test.mjs:538-545` | `default_selection_rules.gs_default_bc7_coupe` + `gs_excl_ls6_engine_covers`; generator would need to derive display metadata | `candidate-generator-derivation` |
| `grandSport_variant_overrides:7` | Grand Sport | `opt_bc7_001` / BC7 / Black LS6 Engine Cover | `2lt_e07` / 2LT coupe | same | same | same | same | `candidate-generator-derivation` |
| `grandSport_variant_overrides:8` | Grand Sport | `opt_bc7_001` / BC7 / Black LS6 Engine Cover | `3lt_e07` / 3LT coupe | same | same | same | same | `candidate-generator-derivation` |
| `grandSport_variant_overrides:9` | Grand Sport | `opt_nga_001` / NGA / Black Exhaust Tips | `1lt_e07` / 1LT coupe | `display_behavior=default_selected` | NGA emits standard/selectable/active/default-selected in `sec_exha_001` | `grand-sport-draft-data.test.mjs:547-550` | `default_selection_rules.gs_default_nga_unless_nwi` + `gs_excl_exhaust_path`; generator would need to derive display metadata | `candidate-generator-derivation` |
| `grandSport_variant_overrides:10` | Grand Sport | `opt_nga_001` / NGA / Black Exhaust Tips | `2lt_e07` / 2LT coupe | same | same | same | same | `candidate-generator-derivation` |
| `grandSport_variant_overrides:11` | Grand Sport | `opt_nga_001` / NGA / Black Exhaust Tips | `3lt_e07` / 3LT coupe | same | same | same | same | `candidate-generator-derivation` |
| `grandSport_variant_overrides:12` | Grand Sport | `opt_nga_001` / NGA / Black Exhaust Tips | `1lt_e67` / 1LT convertible | same | same | same | same | `candidate-generator-derivation` |
| `grandSport_variant_overrides:13` | Grand Sport | `opt_nga_001` / NGA / Black Exhaust Tips | `2lt_e67` / 2LT convertible | same | same | same | same | `candidate-generator-derivation` |
| `grandSport_variant_overrides:14` | Grand Sport | `opt_nga_001` / NGA / Black Exhaust Tips | `3lt_e67` / 3LT convertible | same | same | same | same | `candidate-generator-derivation` |
| `z06_variant_overrides:2` | Z06 | `opt_uqt_001` / UQT / Performance Data and Video Recorder | `2lz_h07` / 2LZ coupe | `selectable=False`, `display_behavior=display_only`, `section_id=sec_2lte_001` | UQT emits standard/nonselectable/display-only in `sec_2lte_001`, `step_key=standard_equipment`, price 0 | no direct UQT-specific Z06 test found; adjacent `z06-form-data-draft.test.mjs` default-selectability guard | OVS status + option row do not own section/selectability; section/standard-equipment metadata or source-row remodel needed | `candidate-source-row-remodel` |
| `z06_variant_overrides:3` | Z06 | `opt_uqt_001` / UQT / Performance Data and Video Recorder | `2lz_h67` / 2LZ convertible | same, `section_id=sec_2lte_001` | same | same | same | `candidate-source-row-remodel` |
| `z06_variant_overrides:4` | Z06 | `opt_uqt_001` / UQT / Performance Data and Video Recorder | `3lz_h07` / 3LZ coupe | `selectable=False`, `display_behavior=display_only`, `section_id=sec_3lte_001` | UQT emits standard/nonselectable/display-only in `sec_3lte_001`, `step_key=standard_equipment`, price 0 | same | same | `candidate-source-row-remodel` |
| `z06_variant_overrides:5` | Z06 | `opt_uqt_001` / UQT / Performance Data and Video Recorder | `3lz_h67` / 3LZ convertible | same, `section_id=sec_3lte_001` | same | same | same | `candidate-source-row-remodel` |

## Behavior-class classification

### 1. UQT trim-scoped included-equipment placement/selectability

Rows:

- Stingray: `variant_option_overrides:2-5` for `opt_uqt_002` paid UQT suppression on 2LT/3LT.
- Grand Sport: `grandSport_variant_overrides:2-5` for `opt_uqt_001` display-only placement on 2LT/3LT.
- Z06: `z06_variant_overrides:2-5` for `opt_uqt_001` display-only placement on 2LZ/3LZ.

Current adjacent owners:

- `*_ovs` owns variant status. For example, Grand Sport and Z06 UQT 2/3 trims are `standard`, while 1LT/1LZ are `available`.
- Source option sheets own base option row section/selectability. Grand Sport and Z06 have a selectable `opt_uqt_001` in `sec_inte_001`; the override rows move only specific variants to trim-standard sections.
- `section_presentation` identifies `sec_2lte_001` / `sec_3lte_001` as standard-equipment buckets, but it does not currently map a source option/variant into those sections.

Classification: `candidate-source-row-remodel`.

Reason: existing status rows alone cannot emit the full behavior. A future implementation must decide whether to remodel UQT source rows, add/extend generic section-placement metadata, or derive display-only standard placement from a normalized rule. Do not delete these rows until generated choice parity and local runtime behavior are proven.

### 2. BC7 coupe default-selected display metadata

Rows:

- Stingray: `variant_option_overrides:6-8`.
- Grand Sport: `grandSport_variant_overrides:6-8`.

Current adjacent owners:

- `default_selection_rules.default_bc7` and `default_selection_rules.gs_default_bc7_coupe` already own coupe default/restoration behavior.
- `exclusive_groups.grp_ls6_engine_covers` and Grand Sport `gs_excl_ls6_engine_covers` own peer replacement behavior.
- `*_ovs` owns coupe `standard` and convertible `available` status.

Classification: `candidate-generator-derivation`.

Reason: runtime default/restoration semantics have canonical owners, but generated `display_behavior=default_selected` still comes from the override rows. A future pass can likely derive this display metadata from active default-selection rules plus OVS/body scope, then delete only the BC7 override rows after generated-data and browser parity.

### 3. Grand Sport NGA all-variant default-selected display metadata

Rows:

- Grand Sport: `grandSport_variant_overrides:9-14`.

Current adjacent owners:

- `default_selection_rules.gs_default_nga_unless_nwi` owns the default/restoration rule.
- `gs_excl_exhaust_path` owns required NGA/NWI peer behavior.
- `grandSport_ovs` owns standard status for all six variants.

Classification: `candidate-generator-derivation`.

Reason: runtime default behavior already has normal workbook owners, but generated `display_behavior=default_selected` still comes from the override rows. This should be grouped with the BC7 default-selected derivation pass, not with UQT source-row remodeling.

## Canonical-owner candidates and blockers

### `*_ovs` status rows

Useful for status, but insufficient alone for UQT because OVS cannot express `selectable=False`, `display_behavior=display_only`, or `section_id` movement. Useful for default-selected derivation because OVS can identify `standard` variants when combined with default-selection scope.

### Source option rows

Useful for base label/price/section/selectability. Blocker for current UQT behavior: a single active source row cannot currently be both a selectable paid/available option in one variant and a display-only trim-standard row in another without the override layer or additional generic metadata.

### `default_selection_rules` plus exclusive groups

Strong candidates for BC7 and Grand Sport NGA runtime behavior. Blocker: current generators do not derive choice-level `display_behavior=default_selected` from those rules for these rows.

### Section / standard-equipment metadata

`section_presentation` already marks trim-equipment buckets for active models. Blocker: it does not currently express per-option/per-variant movement from a customer-selectable section into a trim-standard section.

### Generator derivation

Plausible for BC7/NGA default-selected metadata. Higher-risk for UQT unless a source model is chosen first, because derivation from status alone would be too implicit and could misclassify other standard rows.

## Recommended follow-up pass sequence

A. Default-selected display metadata derivation, report-backed implementation spec.

- Scope: Stingray BC7, Grand Sport BC7, Grand Sport NGA only.
- Goal: derive generated `display_behavior=default_selected` from existing default-selection rules plus OVS/variant/body scope and exclusive groups, then retire only the corresponding override rows.
- Non-goals: UQT, `runtime_action`, `body_style_scope`, Z06 default behavior, section movement.
- Required gates: regenerate Stingray and Grand Sport plus registry; generated choice allowlist for only BC7/NGA override-row removal and equivalent `display_behavior`; `tests/stingray-form-regression.test.mjs`; `tests/stingray-generator-stability.test.mjs` if the source guard changes; `tests/grand-sport-draft-data.test.mjs`; local browser/default replay for BC7 and NGA.

B. UQT trim-standard placement design/spec.

- Scope: all active-model UQT override rows, but only after source modeling is chosen.
- Decision required: remodel source option rows, add generic variant section-placement metadata, or derive display-only standard placement from a clearly constrained workbook owner.
- Required gates: active affected model generators, registry, UQT generated-choice parity by variant, Grand Sport/Z06 draft tests, Stingray generator stability, local browser check that 1LT/1LZ UQT remains selectable while 2/3 trims show the correct standard-equipment rows.

C. Variant override schema/editor semantics cleanup.

- Scope: only after rows are reduced or semantics are clarified.
- Goal: make validators/editor copy distinguish global emitted-value `active` from model-scoped row-activation `active` so future agents do not misread the sheets.
- Required gates: workbook schema validation, workbook schema standardization tests, editor payload/gate-reminder tests if touched.

## Non-goals and protections

This report does not approve:

- workbook edits or override-row deletion;
- generator/runtime implementation;
- schema/header changes;
- test rewrites;
- generated artifact refresh;
- dealer submission changes;
- `runtime_action` / `body_style_scope` cleanup;
- Z06 brake/default replacement changes;
- a single sheet-wide variant override deletion pass.

## Validation recommendations by future implementation class

Default-selected derivation:

```sh
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_registry.py
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
```

UQT remodel/derivation:

```sh
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
.venv/bin/python scripts/generate_registry.py
node --test tests/stingray-generator-stability.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/z06-form-data-draft.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Schema/editor semantics cleanup:

```sh
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
node --test tests/workbook-schema-standardization.test.mjs
node --test tests/workbook-visual-copy-standardization.test.mjs
.venv/bin/python -m pytest tests/test_model_config_metadata.py tests/test_schema_validation_metadata.py -q
```

Any implementation pass that edits `stingray_master.xlsx` must use the workbook safe-save path, verify no Excel lock exists, inspect saved workbook rows on disk, regenerate affected artifacts, and review generated diffs before handoff.
