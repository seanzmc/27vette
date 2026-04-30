# Grand Sport Clean Source Data Plan

Status: plan only. No code changes, app-data changes, or Stingray behavior changes are part of this pass.

## Goal

Normalize Grand Sport into the same workbook/source-data workflow as Stingray. Grand Sport data should look like Stingray data so it can slot into the same generator/form workflow with model-specific data differences, not a separate schema or Python patch layer.

## Direction

- Keep `stingray_master.xlsx` as the shared working workbook for now.
- Do not create `grand_sport_master.xlsx`.
- Add Grand Sport clean/source tabs that mirror the existing Stingray tabs and naming style.
- Normalize Grand Sport raw headers, statuses, sections, categories, option IDs, selectable flags, and active flags so they match the Stingray source contract.
- Any differences should be model-specific data differences, not workflow/schema differences.
- Python should not patch Grand Sport into shape. Python should read Grand Sport sheets that already match the expected shape, validate them, and generate form data.

## Existing Stingray-Like Source Pattern

Current Stingray source/generator inputs in `stingray_master.xlsx`:

| Existing sheet | Current role |
| --- | --- |
| `stingray_master` | Normalized option source rows. |
| `option_variant_status` | Unpivoted option/variant/status matrix. |
| `rule_mapping` | Requires/excludes/includes source rules. |
| `price_rules` | Source price rules. |
| `variant_master` | Variant metadata. |
| `category_master` | Category reference. |
| `section_master` | Section reference and selection modes. |
| `lt_interiors` | LT interior source rows. |
| `PriceRef` | Interior/component price reference. |
| `color_overrides` | Interior color override source rows. |

Current Grand Sport problem:

- The `grandSport` sheet is still raw-ish import data with different headers: `RPO`, `Price`, `Option Name`, `Detail`, `Category`, `Section`, and wide variant status columns.
- `inspection.py` and `GRAND_SPORT_MODEL` currently compensate with config overrides for section/category placement, label cleanup, exclusive groups, interiors, and normalization.
- That was useful for inspection, but it should not become the durable Grand Sport workflow.

## Proposed Grand Sport Tabs

Use model-prefixed tabs inside `stingray_master.xlsx` that mirror the Stingray source setup.

| Proposed tab | Mirrors | Purpose |
| --- | --- | --- |
| `grandSport_master` | `stingray_master` | Normalized Grand Sport option source rows. |
| `grandSport_option_variant_status` | `option_variant_status` | Unpivoted Grand Sport option/variant/status matrix. |
| `grandSport_rule_mapping` | `rule_mapping` | Grand Sport rules when approved. Initially empty or review-only. |
| `grandSport_price_rules` | `price_rules` | Grand Sport price rules when approved. Initially empty. |
| `grandSport_interiors` | `lt_interiors` / generated interior workflow | Grand Sport-specific clean interior source rows if shared `lt_interiors` cannot remain the source. |
| `grandSport_color_overrides` | `color_overrides` | Grand Sport color overrides if needed. Initially empty unless validated. |
| `grandSport_interior_components` | Current interior component output concept | Only add if needed to make component RPOs explicit in source; keep aligned with the current `interior_components_json` output model. |

Keep shared reference sheets unless Grand Sport needs model-specific reference rows:

- `variant_master`
- `category_master`
- `section_master`
- `PriceRef`

If shared sheets become ambiguous, add model-scoped rows or model-prefixed equivalent sheets only after a specific collision is proven.

## `grandSport_master` Contract

Match `stingray_master` headers as closely as possible:

| Column | Required meaning |
| --- | --- |
| `option_id` | Normalized stable option ID. |
| `rpo` | RPO code. |
| `price` | Base option price. |
| `option_name` | Clean customer-facing option label. |
| `description` | Clean customer-facing description. |
| `detail_raw` | Preserved raw detail text for future rule extraction. |
| `section_id` | Clean section ID from `section_master`. |
| `selectable` | `TRUE`/`FALSE` using the same semantics as Stingray. |
| `display_order` | Option order within section. |
| `source_domain (main / interior)` | `main`, `interior`, or equivalent current Stingray value. |
| `active` | `TRUE`/`FALSE`, controlling whether the source row is emitted. |

Recommended additions only if the current Stingray workflow needs the same concept:

- `source_option_name`
- `source_description`
- `source_detail_raw`
- `component_only`

Prefer not to add new columns unless the Stingray path can also understand or ignore them cleanly.

## Correction Type Map

| Correction type | Grand Sport source location |
| --- | --- |
| Header normalization | Rename/reshape `grandSport` into `grandSport_master` with Stingray-style headers. |
| Option ID normalization | `grandSport_master.option_id`; avoid Python aliases except as temporary migration checks. |
| Section/category normalization | `grandSport_master.section_id`, shared `section_master`, shared `category_master`. |
| Variant status unpivoting | `grandSport_option_variant_status`. |
| Selectable vs component-only options | `grandSport_master.selectable`, `grandSport_master.active`, and a narrow component-only convention aligned with Stingray interior output. |
| Hidden/deactivated options | `grandSport_master.active=FALSE` or all statuses `unavailable`; avoid runtime hiding. |
| Display label cleanup | `grandSport_master.option_name`. |
| Description cleanup | `grandSport_master.description`. |
| Raw rule evidence | `grandSport_master.detail_raw`; later copied into `grandSport_rule_mapping.original_detail_raw`. |
| Choice groups/exclusive groups | Prefer a Grand Sport source tab mirroring generated `form_exclusive_groups`, e.g. `grandSport_exclusive_groups`, if the Stingray workflow accepts source groups. Otherwise migrate current config groups into a workbook source tab before expanding rules. |
| Rules/requires/excludes/includes | `grandSport_rule_mapping`, same shape as `rule_mapping`. |
| Price rules | `grandSport_price_rules`, same shape as `price_rules`. |
| Interiors | `grandSport_interiors` only if `lt_interiors` is not clean enough as the shared source. |
| Interior components | Keep current component output concept. Add `grandSport_interior_components` only if source needs explicit component rows. |

## N26/TU7/36S/37S/38S Handling

These RPOs should not be standalone selectable Grand Sport choices. They should be emitted through selected interiors as component lines.

### In `grandSport_master`

| option_id | rpo | option_name | section_id | selectable | active | intended meaning |
| --- | --- | --- | --- | --- | --- | --- |
| `opt_n26_001` | `N26` | `Sueded Microfiber` | `sec_inte_001` | `FALSE` | `FALSE` | Interior component only. |
| `opt_tu7_001` | `TU7` | `Two-Tone Seats` | `sec_inte_001` | `FALSE` | `FALSE` | Interior component only. |
| `opt_36s_001` | `36S` | `Yellow Stitching` | `sec_cust_002` | `FALSE` | `FALSE` | Interior component only. |
| `opt_37s_001` | `37S` | `Blue Stitching` | `sec_cust_002` | `FALSE` | `FALSE` | Interior component only. |
| `opt_38s_001` | `38S` | `Red Stitching` | `sec_cust_002` | `FALSE` | `FALSE` | Interior component only. |

### In Interior Source

Interior rows should carry these RPOs as components, matching current generated behavior:

| Example interior | Component RPO | Component label | Component price |
| --- | --- | --- | ---: |
| `1LT_AE4_HTJ_N26` | `N26` | `Sueded Microfiber` | 695 |
| `2LT_AH2_HTN_TU7` | `TU7` | `Two-Tone` | 595 |
| `2LT_AQ9_H1Y_36S` | `36S` | `Yellow Stitching` | 495 |
| `2LT_AQ9_H1Y_37S` | `37S` | `Blue Stitching` | 495 |
| `2LT_AQ9_H1Y_38S` | `38S` | `Red Stitching` | 495 |

Durable rule: an RPO that appears as an interior component must not also appear as a selectable Grand Sport option unless explicitly allowed by a source-data flag and test.

## What Python Should Read vs Derive

Python should read from source sheets:

- normalized option rows from `grandSport_master`;
- variant statuses from `grandSport_option_variant_status`;
- section/category placement from `section_master`, `category_master`, and option `section_id`;
- display labels/descriptions from source columns;
- raw detail text from `detail_raw`;
- exclusive groups, rules, price rules, and interiors from Grand Sport source tabs when those tabs exist.

Python may still derive:

- `choice_id`;
- `status_label`;
- `choice_mode` from `selection_mode`;
- context body/trim choices from `variant_master`;
- full variant matrix from unpivoted status rows;
- standard-equipment rows from `status=standard`;
- generated JSON structures and validation reports.

Python should not own long-term Grand Sport corrections:

- header normalization;
- hidden/component-only option decisions;
- section/category patches;
- label/description cleanup;
- exclusive-group membership;
- rules or price scopes.

## Migration Steps

1. Keep the current raw `grandSport` sheet as import evidence until the clean sheet is verified.
2. Create `grandSport_master` with headers matching `stingray_master`.
3. Copy rows from `grandSport` into `grandSport_master`, normalizing header names and values.
4. Normalize statuses out of wide columns into `grandSport_option_variant_status`.
5. Normalize section IDs and category alignment so Grand Sport rows resolve without Python overrides.
6. Normalize `selectable` and `active` values to match Stingray semantics.
7. Set `N26`, `TU7`, `36S`, `37S`, and `38S` to non-selectable/non-active standalone option rows and preserve their component meaning through interiors.
8. Move current Grand Sport exclusive group membership out of Python config and into a workbook tab that mirrors Stingray generated group shape.
9. Add `grandSport_rule_mapping` and `grandSport_price_rules` with Stingray-like headers, even if initially empty.
10. Keep `detail_raw` intact for future rule extraction.
11. Update Grand Sport generation to read the clean Grand Sport tabs.
12. Remove Grand Sport Python/config patches only after generated output matches the approved Grand Sport runtime behavior.

## Python/Config To Remove After Clean Sheets Exist

Remove or shrink these once the workbook owns the data:

- `GRAND_SPORT_SECTION_CATEGORY_OVERRIDES`
- `GRAND_SPORT_OPTION_CATEGORY_OVERRIDES`
- `GRAND_SPORT_SECTION_LABEL_OVERRIDES`
- `GRAND_SPORT_EXCLUSIVE_GROUPS`
- `blank_section_overrides` for `PCQ`, `PDY`, `PEF`
- Grand Sport-specific display text cleanup in `inspection.py`
- future Grand Sport hidden/component-only lists in Python

Keep generic code:

- table reading;
- validation;
- field derivation;
- artifact writing;
- multi-model registry writing.

## Validation Checks

Source validation should fail if:

- `grandSport_master` headers drift from the Stingray-style contract;
- any `grandSport_master.option_id` is blank or duplicated;
- any `grandSport_option_variant_status.option_id` is missing from `grandSport_master`;
- any status is not `available`, `standard`, or `unavailable`;
- any `variant_id` is not one of the six Grand Sport variants;
- any `section_id` is missing from `section_master`;
- any section/category relationship needs a Python override;
- any active/selectable option has no active variant status;
- any inactive option is referenced by an active exclusive group, rule, or price rule without an explicit review flag;
- `N26`, `TU7`, `36S`, `37S`, or `38S` appear as selectable Grand Sport choices;
- an interior component RPO is also selectable as a standalone option without an explicit allow flag;
- raw `detail_raw` is lost during normalization.

Regression validation should assert:

- Stingray generated output is unchanged.
- Grand Sport still loads from the multi-model registry.
- Grand Sport has valid Base Interior choices.
- `N26`, `TU7`, `36S`, `37S`, and `38S` export only through selected interior component lines.
- Grand Sport exclusive groups still work after moving group membership out of Python.

## Implementation Phases

### Phase 1: Normalize Source Tabs

- Add `grandSport_master`.
- Add `grandSport_option_variant_status`.
- Normalize headers and statuses from the raw `grandSport` sheet.
- Do not switch the runtime yet.

### Phase 2: Align Placement And Selectability

- Normalize section/category placement in workbook data.
- Normalize `selectable` and `active`.
- Mark component-only RPOs so they stop appearing as standalone choices.
- Add validation tests against the clean tabs.

### Phase 3: Move Groups And Empty Rule Surfaces

- Move current Grand Sport exclusive groups into workbook source.
- Add empty Stingray-shaped `grandSport_rule_mapping` and `grandSport_price_rules`.
- Keep rules/price rules inactive until explicitly approved.

### Phase 4: Switch Grand Sport Generator Input

- Point Grand Sport generation at the clean Grand Sport tabs inside `stingray_master.xlsx`.
- Remove equivalent Python/config patches.
- Confirm generated Grand Sport data is equivalent except for approved source-data cleanup.

### Phase 5: Add Rules And Price Rules Later

- Use `detail_raw` to populate `grandSport_rule_mapping`.
- Add scoped `grandSport_price_rules`.
- Keep all additions model-scoped and covered by tests.
