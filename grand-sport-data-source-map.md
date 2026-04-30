# Grand Sport Data Source Map

Status: read-only source map. No code changes are part of this artifact.

## Current Front-End Data Path

Grand Sport front-end data is not built directly by `form-app/app.js`. It is generated as an inspection/draft artifact and then embedded into the multi-model registry.

1. `scripts/generate_stingray_form.py` builds the Stingray app data.
2. During that run, `refresh_grand_sport_registry_source()` rebuilds Grand Sport inspection artifacts.
3. `build_form_data_draft(GRAND_SPORT_MODEL)` in `scripts/corvette_form_generator/inspection.py` creates the Grand Sport draft data.
4. `load_grand_sport_registry_data()` reads `form-output/inspection/grand-sport-form-data-draft.json`.
5. `write_app_data_registry()` writes `form-app/data.js` with `window.CORVETTE_FORM_DATA.models.grandSport.data`.

Note: `form-output/inspection/grand-sport-draft-data.json` is not present. The current draft artifact is `form-output/inspection/grand-sport-form-data-draft.json`.

## Workbook Sheets Feeding Grand Sport

| Source | Used for |
| --- | --- |
| `grandSport` | Raw option rows, RPOs, prices, labels, descriptions, raw details, source category/section, selectable flag, and six Grand Sport variant status cells. |
| `variant_master` | Grand Sport variant metadata for `1lt_e07`, `2lt_e07`, `3lt_e07`, `1lt_e67`, `2lt_e67`, `3lt_e67`. |
| `category_master` | Category names and validation for resolved category IDs. |
| `section_master` | Section names, section category, selection mode, required flag, display order, and standard behavior. |
| `lt_interiors` | Grand Sport interior rows and interior IDs. |
| `PriceRef` | Interior component prices for seats, stitching, suede, two-tone, and related component lines. |

Non-workbook input: `architectureAudit/grand_sport_interiors_refactor.csv` supplies interior hierarchy/grouping labels used by `read_interior_reference()`.

## Direct Workbook Fields

From `grandSport`:

- `option_id` -> option identity.
- `RPO` -> `rpo`.
- `Price` -> `base_price`.
- `Option Name` -> `source_option_name`, then customer `label` after cleanup.
- `Description` -> `source_description`, then customer `description` after cleanup.
- `Detail` -> `source_detail_raw`.
- `Category` -> `source_category_id`, then category resolution input.
- `Section` -> `source_section_id`, then section resolution input.
- `Selectable` -> normalized `selectable`.
- `1lt_e07`, `2lt_e07`, `3lt_e07`, `1lt_e67`, `2lt_e67`, `3lt_e67` -> normalized `status` per variant.

From `variant_master`:

- `variant_id`, `model_year`, `trim_level`, `body_style`, `display_name`, `base_price`, `display_order`, `active`.

From `section_master`:

- `section_id`, `section_name`, `category_id`, `selection_mode`, `is_required`, `display_order`, `standard_behavior`.

From `lt_interiors`:

- `interior_id`, `Interior Name`, `Material`, `Price`, `Detail from Disclosure`, `Color Overrides`, `Trim`, `Seat`, `Interior Code`, `Suede`, `Stitch`, `Two Tone`, `section_id`.

From `PriceRef`:

- `OptionType`, `Trim`, `Code`, `Price`.

## `GRAND_SPORT_MODEL` Overrides

Defined in `scripts/corvette_form_generator/model_configs.py`.

| Config field | Current Grand Sport use |
| --- | --- |
| `source_option_sheet` | Uses workbook sheet `grandSport`. |
| `variant_ids` | Restricts Grand Sport to the six `_e07` / `_e67` variants. |
| `step_order`, `step_labels` | Defines runtime step flow and labels. |
| `context_sections` | Creates synthetic Body Style and Trim Level steps. |
| `body_style_display_order` | Orders coupe before convertible. |
| `selection_mode_labels` | Human labels for section selection modes. |
| `standard_sections` | Marks standard-equipment sections. |
| `section_step_overrides` | Maps sections to runtime steps; Grand Sport adds `sec_gsha_001`, `sec_spec_001`, `sec_colo_001`. |
| `blank_section_overrides` | Resolves blank sections for `opt_pcq_001`, `opt_pdy_001`, `opt_pef_001`. |
| `section_category_overrides` | Resolves known section/category mismatches for Grand Sport sections. |
| `option_category_overrides` | Resolves option-specific category placement for `opt_bv4_001`, `opt_pin_001`, `opt_r8c_001`. |
| `section_label_overrides` | Renames Grand Sport-specific sections like center stripes and hash marks. |
| `exclusive_groups` | Emits the five Grand Sport exclusive groups. |
| `text_cleanup` | Enables limited cleanup of display labels/descriptions while preserving raw source fields. |
| `special_rule_review_rpos` | Flags `EL9`, `Z25`, `FEY`, `Z15` in rule hot-spot metadata. |
| `interior_reference_path` | Points to `architectureAudit/grand_sport_interiors_refactor.csv`. |

## `inspection.py` Generated/Transformed Fields

Key transforms:

- Normalizes statuses: `Available`, `Standard`, `Not Available` -> `available`, `standard`, `unavailable`.
- Normalizes `Selectable` to `True` / `False`.
- Parses prices with `money()`.
- Applies blank-section overrides.
- Resolves category from option override, section override, source category, or section master.
- Resolves `step_key` from section/category plus model config.
- Applies limited text cleanup to `label` and `description`.
- Preserves raw text in `source_option_name`, `source_description`, `source_detail_raw`.
- Creates `contextChoices` for body style and trim.
- Creates preview `choices` only for available/standard cells.
- Expands draft `choices` to the full six-variant matrix, including unavailable rows.
- Creates `standardEquipment` from draft choices with `status === "standard"`.
- Emits `exclusiveGroups` from `GRAND_SPORT_MODEL.exclusive_groups`.
- Leaves `ruleGroups`, `rules`, `priceRules`, and `colorOverrides` empty/deferred.
- Builds `interiors` from `lt_interiors`, `PriceRef`, and the Grand Sport interior reference CSV.
- Builds `interior_components` for seat upgrades, `R6X`, stitching, suede, and two-tone interior component lines.
- Builds `draftMetadata.ruleDetailHotSpots` from raw detail/description/name text.

## Emitted Into `form-app/data.js`

`form-app/data.js` receives:

- `window.CORVETTE_FORM_DATA.defaultModelKey = "stingray"`.
- `window.CORVETTE_FORM_DATA.models.stingray.data` from the Stingray generator.
- `window.CORVETTE_FORM_DATA.models.grandSport.data` from `form-output/inspection/grand-sport-form-data-draft.json`.
- `window.STINGRAY_FORM_DATA` as the Stingray legacy alias.

Grand Sport `data` currently includes:

- `dataset`
- `variants`
- `steps`
- `sections`
- `contextChoices`
- `choices`
- `standardEquipment`
- `ruleGroups`
- `exclusiveGroups`
- `rules`
- `priceRules`
- `interiors`
- `colorOverrides`
- `validation`
- `draftMetadata`

Current Grand Sport counts in the draft: 6 variants, 14 steps, 34 sections, 1,614 choices, 545 standard-equipment rows, 5 exclusive groups, 132 interiors, 0 rules, 0 ruleGroups, 0 priceRules.

## Where To Make Future Corrections

| Correction type | Durable edit location |
| --- | --- |
| Section/category placement | Prefer `GRAND_SPORT_MODEL` config for Grand Sport-specific exceptions. Use workbook `grandSport`, `section_master`, or `category_master` only when correcting source data globally. |
| Option display labels | Source text is workbook `grandSport` `Option Name`. For customer-facing cleanup that must preserve raw source, add model-scoped display override/cleanup config and apply it in `inspection.py`. |
| Descriptions | Source text is workbook `grandSport` `Description`. For display-only cleanup, add model-scoped override/cleanup config in `inspection.py`. |
| Display order | Option order currently follows preview/draft generation order from workbook rows. Section order comes from `section_master.display_order`; step order comes from `GRAND_SPORT_MODEL.step_order`. Use model config/generator transforms for Grand Sport-only order cleanup. |
| Hidden/deactivated options | Add Grand Sport model-scoped hidden/component-only config and apply it in `inspection.py`. Do not add runtime hiding unless explicitly approved. |
| Exclusive groups | `GRAND_SPORT_EXCLUSIVE_GROUPS` in `model_configs.py`. |
| Rules/requires/excludes/includes | Future Grand Sport model-scoped rule config plus `inspection.py` emission into `rules` / `ruleGroups`. Keep raw `source_detail_raw` as evidence. |
| Price rules | Future Grand Sport model-scoped price-rule config plus `inspection.py` emission into `priceRules`. |
| Interiors | `lt_interiors`, `PriceRef`, `architectureAudit/grand_sport_interiors_refactor.csv`, and `build_grand_sport_interiors()` in `inspection.py`. |
| Interior component lines | `PriceRef`, `INTERIOR_COMPONENT_LABELS`, and `interior_component_metadata()` in `inspection.py`. |

## Special Investigation: N26, TU7, Custom Stitching

### Root Cause

`N26`, `TU7`, `36S`, `37S`, and `38S` still appear as standalone Grand Sport choices because the `grandSport` workbook sheet marks them as `Selectable = yes` and assigns them visible sections. `inspection.py` currently carries those rows into `choices` whenever a variant status is available/standard.

At the same time, Grand Sport interiors already emit these RPOs as interior component lines from `lt_interiors` + `PriceRef`. The duplication is data-generation behavior, not runtime behavior.

### Evidence Table

| RPO | Workbook source | Generated choice | Current section/step | Selectable? | Component lines already emitted? | Recommended fix |
| --- | --- | --- | --- | --- | --- | --- |
| `N26` | `grandSport` row 138, `opt_n26_001`, `Section=sec_inte_001`, `Selectable=yes`, all six variants `Available`. | `choice_id=1lt_e07__opt_n26_001` plus five more variant rows; label `Steering wheel`; base price `695`. | `Interior Trim` / `interior_trim`; `selection_mode=multi_select_opt`; active in all six variants. | Yes, `selectable=True`. | Yes. 54 Grand Sport interiors include `N26` component metadata as `Sueded Microfiber`, price `695`. | Generator transform with model config: treat `N26` as Grand Sport component-only/hidden standalone choice while preserving source row and interior component output. Do not fix in runtime. |
| `TU7` | `grandSport` row 202, `opt_tu7_001`, `Section=sec_inte_001`, `Selectable=yes`, 1LT unavailable and 2LT/3LT available. | `choice_id=2lt_e07__opt_tu7_001` active row plus matrix rows; label `Seats`; base price `595`. | `Interior Trim` / `interior_trim`; `selection_mode=multi_select_opt`; active for 2LT/3LT coupe/convertible. | Yes, `selectable=True`. | Yes. 16 Grand Sport interiors include `TU7` component metadata as `Two-Tone`, price `595`. | Generator transform with model config: treat `TU7` as Grand Sport component-only/hidden standalone choice while preserving source row and interior component output. Do not fix in runtime. |
| `36S` | `grandSport` row 7, `opt_36s_001`, `Section=sec_cust_002`, `Selectable=yes`, 1LT unavailable and 2LT/3LT available. | `choice_id=2lt_e07__opt_36s_001` active row plus matrix rows; label `Competition Yellow custom leather stitch`; base price `495`. | `Custom Stitch` / `interior_trim`; `selection_mode=single_select_opt`; active for 2LT/3LT coupe/convertible. | Yes, `selectable=True`. | Yes. 13 Grand Sport interiors include `36S` component metadata as `Yellow Stitching`, price `495`. | Generator transform with model config: hide/deactivate `sec_cust_002` standalone choices or mark `36S` component-only for Grand Sport. Component-only is cleaner because it matches current interior output. |
| `37S` | `grandSport` row 8, `opt_37s_001`, `Section=sec_cust_002`, `Selectable=yes`, 1LT unavailable and 2LT/3LT available. | `choice_id=2lt_e07__opt_37s_001` active row plus matrix rows; label `Santorini Blue custom leather stitch`; base price `495`. | `Custom Stitch` / `interior_trim`; `selection_mode=single_select_opt`; active for 2LT/3LT coupe/convertible. | Yes, `selectable=True`. | Yes. 13 Grand Sport interiors include `37S` component metadata as `Blue Stitching`, price `495`. | Generator transform with model config: hide/deactivate `sec_cust_002` standalone choices or mark `37S` component-only for Grand Sport. |
| `38S` | `grandSport` row 9, `opt_38s_001`, `Section=sec_cust_002`, `Selectable=yes`, 1LT unavailable and 2LT/3LT available. | `choice_id=2lt_e07__opt_38s_001` active row plus matrix rows; label `Adrenaline Red custom leather stitch`; base price `495`. | `Custom Stitch` / `interior_trim`; `selection_mode=single_select_opt`; active for 2LT/3LT coupe/convertible. | Yes, `selectable=True`. | Yes. 18 Grand Sport interiors include `38S` component metadata as `Red Stitching`, price `495`. | Generator transform with model config: hide/deactivate `sec_cust_002` standalone choices or mark `38S` component-only for Grand Sport. |

### Recommended Durable Fix

Add Grand Sport model-scoped component-only or hidden-option configuration, then apply it in `inspection.py` while building preview/draft choices.

Recommended shape:

- `component_only_option_ids`: `opt_n26_001`, `opt_tu7_001`, `opt_36s_001`, `opt_37s_001`, `opt_38s_001`
- Or `hidden_section_ids`: `sec_cust_002` plus explicit component-only IDs for `N26` and `TU7`.

Use the first option if the goal is to keep the meaning precise: these RPOs are not bad source rows; they are interior component RPOs that should be surfaced through selected interiors, not as independent Grand Sport choices.

Do not edit `form-app/app.js` for this fix. The runtime is correctly rendering the generated choices it receives.
