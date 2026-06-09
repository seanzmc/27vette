# `stingray_master.xlsx` workbook sheet index

Generated from read-only inspection of `stingray_master.xlsx` on 2026-06-09.

This index describes what each workbook sheet currently does, which model or models it serves in the current runtime path, and notes about source-of-truth status.

Current browser runtime registry, verified from `form-app/data.js`:

- `stingray` / Stingray: promoted runtime model and default model.
- `grandSport` / Grand Sport: promoted runtime model loaded from `form-output/inspection/grand-sport-form-data-draft.json`.
- `z06` / Z06: promoted runtime model loaded from `form-output/inspection/z06-form-data-draft.json`.
- ZR1 and ZR1X workbook rows exist as future scaffolds but are not currently in `form-app/data.js`.

Important ownership notes:

- Source sheets are the workbook-owned business/data contract.
- `form_*` sheets are generated outputs and should not be edited manually.
- Archive/raw sheets are evidence or ingest material; they are not direct runtime sources.
- `model_workbook_sources` still marks Z06/ZR1/ZR1X source rows inactive, while `model_registry_promotion` and `form-app/data.js` currently promote Z06. Treat that as transition-state metadata when auditing source ownership.

## Sheet index

| Sheet | Rows | What it does | Current runtime model(s) served | Additional notes |
|---|---:|---|---|---|
| `variant_master` | 33 | Canonical variant registry: model year, trim, body style, display name, base price, display order, active flag. | Stingray, Grand Sport, Z06; future rows for ZR1/ZR1X. | Z06 variant rows are active in `variant_master`; ZR1/ZR1X remain inactive future rows. |
| `section_master` | 50 | Canonical option/standard-equipment section definitions: section label, selection mode, required flag, ordering, standard behavior, step key. | Stingray, Grand Sport, Z06. | Shared by model generators; section IDs are referenced by each model option sheet. |
| `price_rules` | 43 | Stingray conditional/override price rules. | Stingray. | Source sheet for generated `form_price_rules` in the Stingray generation path. |
| `grandSport_price_rules` | 48 | Grand Sport conditional/override price rules. | Grand Sport. | Feeds Grand Sport draft/preview artifacts and runtime registry entry through the promoted draft artifact. |
| `stingray_ovs` | 1,621 | Stingray option/variant status matrix. | Stingray. | One row per option/variant status relationship. |
| `rule_mapping` | 239 | Stingray direct option rules: includes, requires, excludes, replace/default-style runtime actions, scopes, and review/lifecycle metadata. | Stingray. | Source for generated Stingray rules. |
| `stingray_options` | 271 | Stingray canonical option rows: option ID, RPO, price, customer copy, section, selectable/active flags, display order, display behavior. | Stingray. | Primary Stingray option source. |
| `grandSport_ovs` | 1,645 | Grand Sport option/variant status matrix. | Grand Sport. | Source for Grand Sport draft/preview artifacts. |
| `grandSport_options` | 274 | Grand Sport canonical option rows: option ID, RPO, price, customer copy, section, selectable/active flags, display order, display behavior. | Grand Sport. | Primary Grand Sport option source. |
| `color_overrides` | 246 | Shared interior/color override relationships: interior ID to option ID, rule type, added RPO. | Stingray, Grand Sport, Z06. | Shared source named by model config/source metadata; generated into `form_color_overrides` for the current generation path. |
| `PriceRef` | 21 | Shared reference prices for interior/component option types by trim/code. | Stingray, Grand Sport, Z06; future ZR1/ZR1X scaffold. | Used by interior/component pricing normalization. |
| `rule_groups` | 26 | Stingray grouped rule definitions such as `requires_any`/`excludes_any`, including source ID and scope metadata. | Stingray. | Parent table for `rule_group_members`. |
| `rule_group_members` | 154 | Stingray grouped-rule target members. | Stingray. | Child/member table for `rule_groups`. |
| `exclusive_groups` | 8 | Stingray exclusive/radio-like option group definitions. | Stingray. | Parent table for `exclusive_group_members`. |
| `exclusive_group_members` | 26 | Stingray exclusive-group option members. | Stingray. | Child/member table for `exclusive_groups`. |
| `grandSport_rule_groups` | 27 | Grand Sport grouped rule definitions such as `requires_any`/`excludes_any`, including source ID and scope metadata. | Grand Sport. | Parent table for `grandSport_rule_group_members`. |
| `grandSport_rule_group_members` | 175 | Grand Sport grouped-rule target members. | Grand Sport. | Child/member table for `grandSport_rule_groups`. |
| `grandSport_exclusive_groups` | 11 | Grand Sport exclusive/radio-like option group definitions. | Grand Sport. | Parent table for `grandSport_exclusive_members`. |
| `grandSport_exclusive_members` | 28 | Grand Sport exclusive-group option members. | Grand Sport. | Child/member table for `grandSport_exclusive_groups`. |
| `grandSport_rule_mapping` | 324 | Grand Sport direct option rules: includes, requires, excludes, replace/default-style runtime actions, scopes, and review/lifecycle metadata. | Grand Sport. | Source for Grand Sport draft/preview rule output. |
| `archive_IDs` | 36 | Historical section/category ID reference material. | None directly. | Archive/evidence sheet, not an active runtime source. |
| `archive_stingray` | 274 | Historical Stingray ingest/source snapshot with original category/status columns. | None directly. | Archive/evidence sheet; use current `stingray_options`/`stingray_ovs` for runtime source. |
| `archive_Z06_Ingest` | 364 | Historical/raw Z06 ingest snapshot. | None directly. | Archive/evidence sheet; use current `z06_options`/`z06_ovs` for Z06 runtime source. |
| `z06_standard_raw` | 128 | Raw Z06 standard-equipment order-guide text/table import. | None directly. | Raw ingest/reference material, not direct runtime data. |
| `z06_eqgrps_raw` | 478 | Raw Z06 equipment-group order-guide text/table import. | None directly. | Raw ingest/reference material, not direct runtime data. |
| `z06_intextmec_raw` | 599 | Raw Z06 interior/exterior/mechanical order-guide text/table import. | None directly. | Raw ingest/reference material, not direct runtime data. |
| `zr1_zr1x_standard_raw` | 124 | Raw ZR1/ZR1X standard-equipment order-guide text/table import. | None directly. | Raw ingest/reference material for future models. |
| `zr1_zr1x_eqgrps_raw` | 349 | Raw ZR1/ZR1X equipment-group order-guide text/table import. | None directly. | Raw ingest/reference material for future models. |
| `zr1_zr1x_intextmec_raw` | 476 | Raw ZR1/ZR1X interior/exterior/mechanical order-guide text/table import. | None directly. | Raw ingest/reference material for future models. |
| `price_sched_raw` | 306 | Raw 2027 Corvette price schedule import. | None directly. | Reference/ingest material; normalized prices belong in model option/price-rule/component sheets. |
| `archive_ZR1_Ingest` | 337 | Historical/raw ZR1 ingest snapshot. | None directly. | Archive/evidence sheet for future model work. |
| `archive_ZR1X_Ingest` | 338 | Historical/raw ZR1X ingest snapshot. | None directly. | Archive/evidence sheet for future model work. |
| `archive_category_master` | 6 | Historical category registry. | None directly. | Retained as historical evidence only; `section_master` is the active section source. |
| `context_choice_copy` | 4 | Workbook-owned tooltip/help copy for body-style/trim/context selector choices. | Stingray, Grand Sport, Z06 where matching generated context choices exist. | Current active rows are wildcard/shared (`model_key=*`). |
| `asset_map` | 94 | Workbook-owned image/media mapping for model cards and option cards. | Stingray, Grand Sport, Z06. | Active rows exist for all three promoted runtime models; inactive/unreviewed Grand Sport rows also exist. |
| `model_master` | 6 | Canonical model registry: model key, runtime registry key, label/year, dataset/export metadata, expected variants, active/default flags. | Stingray, Grand Sport, Z06; future rows for ZR1/ZR1X. | Z06 is active here; ZR1/ZR1X inactive. |
| `model_workbook_sources` | 55 | Model-to-source-sheet registry: option sheet, OVS/status sheet, rule sheets, price sheets, interiors, color overrides, and variant overrides. | Active rows currently serve Stingray and Grand Sport; Z06 rows are present but marked inactive. | Transition-state warning: Z06 is promoted in `model_registry_promotion` and `form-app/data.js`, but this sheet still marks Z06 source rows inactive. Current Z06 generator config names the Z06 sheets directly. |
| `model_variants` | 27 | Model-to-variant membership and display order metadata. | Stingray and Grand Sport active here; Z06/ZR1/ZR1X rows present but inactive. | Transition-state warning: `variant_master` has active Z06 variants, but `model_variants` still marks Z06 inactive. |
| `component_price_rules` | 1 | Header-only substrate for component-level conditional price rules. | None currently. | No data rows at inspection time. |
| `runtime_rule_exceptions` | 5 | Workbook-owned runtime exception metadata for generic runtime rule handling. | Stingray. | Active rows are Stingray-scoped. Use carefully; prefer canonical rule/group sheets when possible. |
| `order_summary_sections` | 12 | Workbook-owned order-summary section labels/order. | Stingray. | Active rows are Stingray-scoped only. |
| `step_order_summary_map` | 14 | Maps runtime steps to order-summary sections. | Stingray. | Active rows are Stingray-scoped only. |
| `variant_option_overrides` | 8 | Stingray model-scoped option/variant overrides for status/selectable/display behavior. | Stingray. | Active subset only; shared schema differs from model-specific `*_variant_overrides` sheets. |
| `lt_interiors` | 133 | LT-family interior definitions: interior IDs, customer labels, materials, price, source details, color overrides, trim/seat/interior codes, section ID, R6X/include metadata. | Stingray, Grand Sport. | Interior source sheet for LT-based models. |
| `runtime_steps` | 29 | Workbook-owned runtime step labels/order/source metadata. | Stingray, Grand Sport. | Active rows exist for Stingray and Grand Sport; no Z06 rows at inspection time. |
| `context_section_master` | 5 | Workbook-owned synthetic context sections for body style / trim selector steps. | Stingray, Grand Sport. | Active rows exist for Stingray and Grand Sport; no Z06 rows at inspection time. |
| `section_presentation` | 34 | Workbook-owned presentation metadata for sections: display labels, step bucket, standard-equipment grouping behavior, ordering. | Stingray, Grand Sport, Z06. | Active model-scoped rows exist for all three promoted runtime models. |
| `standard_equipment_groups` | 25 | Workbook-owned grouping metadata for standard-equipment output. | Stingray, Grand Sport, Z06. | Active model-scoped rows exist for all three promoted runtime models. |
| `rule_phrase_map` | 7 | Parser metadata mapping source text phrases to rule types/directions/review defaults. | Grand Sport and Z-family parsing/audit paths; indirect runtime source. | Metadata used by generator/parser workflows, not browser runtime directly. |
| `option_audit_groups` | 2 | Audit grouping definitions for option parser/review reports. | Grand Sport/Z-family audit paths; indirect runtime source. | Parent table for `option_audit_group_members`. |
| `option_audit_group_members` | 9 | Audit-group member RPO/option rows. | Grand Sport/Z-family audit paths; indirect runtime source. | Child/member table for `option_audit_groups`. |
| `rule_review_groups` | 5 | Model-scoped special rule review/audit metadata. | Grand Sport audit path; indirect runtime source. | Active rows are Grand Sport-scoped. |
| `grandSport_variant_overrides` | 14 | Grand Sport option/variant overrides for selectable/display behavior and section placement. | Grand Sport. | Model-specific override sheet read by Grand Sport generator. |
| `default_selection_rules` | 19 | Workbook-owned default-selection rules by model/condition/body/trim/variant. | Stingray, Grand Sport, Z06; future rows for ZR1/ZR1X. | Active rows exist for all five model keys, but only Stingray/Grand Sport/Z06 are currently runtime models. |
| `z06_rule_mapping` | 56 | Z06 direct option rules: includes, requires, excludes, replace/default-style runtime actions, scopes, and review/lifecycle metadata. | Z06. | Z06 is currently in app runtime through the promoted draft artifact. |
| `z06_price_rules` | 49 | Z06 conditional/override price rules. | Z06. | Source for Z06 draft/preview artifacts. |
| `z06_exclusive_groups` | 13 | Z06 exclusive/radio-like option group definitions. | Z06. | Parent table for `z06_exclusive_members`. |
| `z06_exclusive_members` | 42 | Z06 exclusive-group option members. | Z06. | Child/member table for `z06_exclusive_groups`. |
| `z06_variant_overrides` | 5 | Z06 option/variant overrides for selectable/display behavior and section placement. | Z06. | Model-specific override sheet read by Z06 generator config. |
| `zr1_rule_mapping` | 57 | ZR1 direct option rules scaffold. | None currently. | Future model source sheet; ZR1 is not in `form-app/data.js`. |
| `zr1_price_rules` | 1 | ZR1 price-rule scaffold. | None currently. | Header-only/no data rows at inspection time. |
| `zr1_rule_groups` | 3 | ZR1 grouped rule definitions scaffold. | None currently. | Future model source sheet. |
| `zr1_rule_group_members` | 30 | ZR1 grouped-rule target members scaffold. | None currently. | Future model source sheet. |
| `zr1_exclusive_groups` | 5 | ZR1 exclusive/radio-like group definitions scaffold. | None currently. | Future model source sheet. |
| `zr1_exclusive_members` | 11 | ZR1 exclusive-group option members scaffold. | None currently. | Future model source sheet. |
| `zr1_variant_overrides` | 1 | ZR1 option/variant override scaffold. | None currently. | Header-only/no data rows at inspection time. |
| `zr1x_rule_mapping` | 57 | ZR1X direct option rules scaffold. | None currently. | Future model source sheet; ZR1X is not in `form-app/data.js`. |
| `zr1x_price_rules` | 1 | ZR1X price-rule scaffold. | None currently. | Header-only/no data rows at inspection time. |
| `zr1x_rule_groups` | 3 | ZR1X grouped rule definitions scaffold. | None currently. | Future model source sheet. |
| `zr1x_rule_group_members` | 30 | ZR1X grouped-rule target members scaffold. | None currently. | Future model source sheet. |
| `zr1x_exclusive_groups` | 5 | ZR1X exclusive/radio-like group definitions scaffold. | None currently. | Future model source sheet. |
| `zr1x_exclusive_members` | 11 | ZR1X exclusive-group option members scaffold. | None currently. | Future model source sheet. |
| `zr1x_variant_overrides` | 1 | ZR1X option/variant override scaffold. | None currently. | Header-only/no data rows at inspection time. |
| `model_registry_promotion` | 6 | Workbook-owned runtime promotion registry: runtime key, promotion flag, default model, artifact path/type, legacy alias, display order. | Stingray, Grand Sport, Z06. | Source of promotion state; ZR1/ZR1X rows are inactive/unpromoted. |
| `z06_options` | 250 | Z06 canonical option rows: option ID, RPO, price, customer copy, section, selectable/active flags, display order, display behavior. | Z06. | Primary Z06 option source for Z06 draft/runtime artifact. |
| `z06_ovs` | 1,495 | Z06 option/variant status matrix. | Z06. | Source for Z06 draft/preview artifacts. |
| `zr1_options` | 214 | ZR1 canonical option rows scaffold. | None currently. | Future model source sheet. |
| `zr1_ovs` | 853 | ZR1 option/variant status matrix scaffold. | None currently. | Future model source sheet. |
| `zr1x_options` | 215 | ZR1X canonical option rows scaffold. | None currently. | Future model source sheet. |
| `zr1x_ovs` | 857 | ZR1X option/variant status matrix scaffold. | None currently. | Future model source sheet. |
| `z06_rule_groups` | 36 | Z06 grouped rule definitions such as `requires_any`/`excludes_any`, including source ID and scope metadata. | Z06. | Parent table for `z06_rule_group_members`. |
| `z06_rule_group_members` | 177 | Z06 grouped-rule target members. | Z06. | Child/member table for `z06_rule_groups`. |
| `LZ_Interiors` | 131 | LZ-family interior definitions: interior IDs, customer labels, materials, price, source details, color overrides, trim/seat/interior codes, section ID, R6X/include metadata. | Z06; future ZR1/ZR1X scaffold. | Z06 generator config names this as its interior source. Schema intentionally mirrors `lt_interiors`. |
| `model_interior_scope` | 443 | Model-scoped interior availability/requirements by interior ID and trim. | Grand Sport, Z06; future ZR1/ZR1X scaffold. | No Stingray rows at inspection time; Stingray uses `lt_interiors` active flags/source behavior. |
| `interior_components` | 847 | Model/interior component membership: component RPO, type, label, price reference, display order, active flag. | Stingray, Grand Sport, Z06; future ZR1/ZR1X scaffold. | Active rows exist for all five model keys, but only Stingray/Grand Sport/Z06 are current runtime models. |
| `form_steps` | 15 | Generated runtime step output for the current workbook generation. | Stingray generated output. | Generated sheet; do not hand-edit. Grand Sport/Z06 runtime entries come from draft JSON artifacts, not these workbook `form_*` sheets. |
| `form_context_choices` | 9 | Generated body-style/trim/context choice output for the current workbook generation. | Stingray generated output. | Generated sheet; do not hand-edit. |
| `form_choices` | 1,465 | Generated choice rows for the current workbook generation: option/variant availability, labels, prices, selection metadata, media fields. | Stingray generated output. | Generated sheet; do not hand-edit. |
| `form_standard_equipment` | 468 | Generated standard-equipment rows for the current workbook generation. | Stingray generated output. | Generated sheet; do not hand-edit. |
| `form_rule_groups` | 26 | Generated grouped-rule output for the current workbook generation. | Stingray generated output. | Generated sheet; do not hand-edit. |
| `form_exclusive_groups` | 8 | Generated exclusive-group output for the current workbook generation. | Stingray generated output. | Generated sheet; do not hand-edit. |
| `form_rules` | 151 | Generated direct rule output for the current workbook generation. | Stingray generated output. | Generated sheet; do not hand-edit. |
| `form_price_rules` | 43 | Generated price-rule output for the current workbook generation. | Stingray generated output. | Generated sheet; do not hand-edit. |
| `form_interiors` | 133 | Generated interior output for the current workbook generation. | Stingray generated output. | Generated sheet; do not hand-edit. |
| `form_color_overrides` | 246 | Generated color override output for the current workbook generation. | Stingray generated output. | Generated sheet; do not hand-edit. |
| `form_validation` | 4 | Generated validation findings for the current workbook generation. | Stingray generated output. | Generated sheet; inspect when generation reports validation issues; do not hand-edit. |

## Evidence checked

- `stingray_master.xlsx` sheet names, headers, and row counts were read with `openpyxl` in read-only mode.
- `model_master`, `model_registry_promotion`, `model_workbook_sources`, and `model_variants` rows were inspected for model/runtime scope.
- `form-app/data.js` was evaluated in a Node VM to confirm current runtime model keys: `stingray`, `grandSport`, and `z06`.
- `scripts/corvette_form_generator/model_configs.py` was inspected for direct generator source-sheet names, including Z06’s `z06_options`, `z06_ovs`, Z06 rule/price/group sheets, and `LZ_Interiors`.
