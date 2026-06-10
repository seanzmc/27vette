# Technical Specification: `stingray_master.xlsx` Cleanup & Reorganization

Date: 2026-06-09. Evidence gathered by read-only inspection of the workbook (openpyxl), `scripts/`, `form-output/`, `form-app/`, and `tests/`.

## 1. Diagnosis

- **Change type:** data-only workbook restructuring plus coordinated generator/validator/test updates. No runtime behavior change for the deployed form app.
- **Root cause of clutter:** the workbook accumulated (a) 13 archive/raw ingest sheets that no script reads, (b) two half-baked features (`component_price_rules`, `standard_equipment_groups`) that are wired into loaders/tests but never consumed, (c) migration-era review/normalization columns that only `schema_validation.py` header-checks, and (d) no sheet ordering or grouping across its **96 sheets**.
- **Risk level:** medium. Column deletions touch header-locked tests (`tests/stingray-generator-stability.test.mjs`, `tests/workbook-schema-standardization.test.mjs`) and `scripts/corvette_form_generator/schema_validation.py`. Sheet reordering and archive extraction are low risk (all reads are by sheet name, never by index).
- **Source-of-truth rules respected:** generated `form_*` sheets are never hand-edited; all writes go through `save_workbook_safely()`; Excel must be closed.

## 2. Runtime column contract (what must be preserved)

A column is **retained** only if it is consumed by at least one of:

1. Generation path: `production.py`, `rules.py`, `interiors.py`, `pricing.py`, `runtime_metadata.py`, `contract.py`, `inspection.py`, `registry_promotion.py`, `promote_model.py`, `model_configs.py`.
2. Authoring/parser path: `build_rule_sources.py`, `rule_phrase_map` loaders.
3. Runtime artifacts: keys present in `form-output/stingray-form-data.json`, `form-output/inspection/*-form-data-draft.json`, `form-app/data.js`, and read by `form-app/app.js`.

Verified consumption highlights:

- `rule_mapping` family: `runtime_authored_rule()` (rules.py:18) consumes `normalization_status` + `generation_action`; `build_draft_rules()` consumes `rule_id`, `source_id`, `rule_type`, `target_id`, `target_type`, `source_type`, `source_section`, `target_section`, `source/target_selection_mode`, `body_style_scope`, `runtime_action`, `disabled_reason`, `original_detail_raw`, `review_flag`.
- `app.js` consumes: `disabled_reason`, `auto_add`, `runtime_action`, `rule_type`, scopes, `condition_type/condition_id`, `exception_type/source_option_id`, image fields, `info_tooltip`, `status_label`, `selection_mode_label`. It does **not** read `review_flag`, `price_semantic`, `source_detail_raw`, `help_text`, `priority` (priority is applied at generation sort time).
- `runtime_metadata._load_rule_rows()` passes `default_selection_rules` and `runtime_rule_exceptions` columns through generically — all their columns are live.
- `section_presentation` consumed fields: `display_label`, `step_key`, `display_behavior`, `section_display_order`, `standard_equipment_bucket`, `standard_equipment_group_type`. `presentation_bucket` is loaded then dropped (0/33 filled, no downstream reader).

## 3. Phase 1 — Remove dead sheets

### 3.1 Extract archive/raw sheets to a companion workbook

These 13 sheets are referenced by **zero** scripts, tests, or app files (verified by full-text search of `scripts/`, `tests/`, `form-app/`). Move them to a new `archive/stingray_archive.xlsx` (git-tracked, read-only evidence), then delete from `stingray_master.xlsx`:

`archive_IDs`, `archive_stingray`, `archive_Z06_Ingest`, `archive_ZR1_Ingest`, `archive_ZR1X_Ingest`, `archive_category_master`, `z06_standard_raw`, `z06_eqgrps_raw`, `z06_intextmec_raw`, `zr1_zr1x_standard_raw`, `zr1_zr1x_eqgrps_raw`, `zr1_zr1x_intextmec_raw`, `price_sched_raw`

Notes: `archive_category_master` appears only inside a message string in `schema_validation.py:565`; update that message. The raw sheets carry ~2,500 rows of order-guide text and are the bulk of the 990 KB file size.

### 3.2 Delete half-baked sheets

| Sheet | Evidence | Required code/test updates |
|---|---|---|
| `component_price_rules` | 0 data rows; sheet name appears nowhere in `scripts/`, `tests/`, or `form-app/` | none |
| `standard_equipment_groups` | `load_standard_equipment_groups()` (runtime_metadata.py:292) is defined but **never called**; its data (`group_type`, `standard_equipment_bucket` semantics) is already owned by `section_presentation` | delete the loader; remove `standardEquipmentGroupHeaders` assertion at stingray-generator-stability.test.mjs:439 |

Result: 96 → 81 sheets.

## 4. Phase 2 — Delete redundant / half-baked columns

### Tier A — dead columns (no functional reader; only header-lock checks)

> **STATUS: COMPLETED 2026-06-10.** 24 columns deleted across 14 sheets; Excel tables on `rule_mapping`, `grandSport_rule_mapping`, `price_rules`, `grandSport_price_rules`, `section_master` rebuilt with shrunk refs. Correction: `option_audit_group_members.option_id` was **retained** — contrary to the original analysis, it is part of the `load_audit_group_members()` contract (returns `option_ids`, consumed by `build_rule_sources.py` and locked by `audit-parser-metadata-loaders.test.mjs`). All other Tier A columns were deleted as specified.

| Sheet(s) | Column | Evidence |
|---|---|---|
| `rule_mapping`, `grandSport_rule_mapping`, `z06_rule_mapping`, `zr1_rule_mapping`, `zr1x_rule_mapping` | `normalization_reason`, `replacement_group_id`, `replacement_rule_id` | read only by `schema_validation.py` header checks; `replacement_rule_id` is 0-filled in 4 of 5 sheets (4/323 in Grand Sport); migration audit residue from `build_rule_sources.py` passes |
| `price_rules`, `grandSport_price_rules`, `z06_price_rules`, `zr1_price_rules`, `zr1x_price_rules` | `price_semantic` | referenced only by `schema_validation.py:704` and workbook-schema-standardization test; never used in price computation (`production.py` pricing path ignores it) |
| `section_master` | `help_text` | 3/49 filled; zero readers |
| `section_presentation` | `presentation_bucket` | 0/33 filled; loaded then never consumed |
| `context_choice_copy` | `copy_id` | zero readers (rows are matched by `model_key`+`context_type`+`value`) |
| `asset_map` | `asset_id` | zero readers (rows matched by `model_key`+`target_type`+`target_id`) |
| ~~`option_audit_group_members`~~ | ~~`option_id`~~ | **RETAINED** — original claim wrong: `load_audit_group_members()` reads it and returns `option_ids` (test-locked contract) |

Required updates for Tier A: remove the columns from `schema_validation.py` expected-header tables (lines ~16–19, 97–98, 160–162, 704+), `tests/stingray-generator-stability.test.mjs` header constants (`ruleMappingHeaders`, `priceRuleHeaders`, `sectionMasterHeaders`, `sectionPresentationHeaders`), `tests/workbook-schema-standardization.test.mjs` (normalization_reason assertion at :237, price_semantic block at :565–589), and `build_rule_sources.py` emit schema so a re-run does not recreate them.

### Tier B — administrative review columns (threaded through audit tooling)

> **STATUS: COMPLETED 2026-06-10.** `review_flag` deleted from all 11 sheets; emission removed from `rules.py`, `production.py` (form_rules/form_price_rules headers), and `inspection.py`; schema checks removed from `BOOLEAN_COLUMNS`/`ROLE_BOOLEAN_COLUMNS`; header locks updated. Generated contracts and `data.js` verified identical to baseline except the removed `review_flag` keys. Notes: (1) the Grand Sport rule-audit gate was unaffected — audit classification is driven by `rule_phrase_map.review_flag_default` and `rule_review_groups`, not the sheet column, so both were retained; (2) the `review_flags` (plural) strip-guards in `registry_promotion.py`/`schema_validation.py` and the z06-runtime-promotion assertion were kept as contract guards.

`review_flag` on `rule_mapping`×5, `price_rules`×5, and `asset_map` is pure review metadata: it is copied into `form_rules`/`form_price_rules` and the JSON artifacts, but `form-app/app.js` never reads it (0 references), and `z06-runtime-promotion.test.mjs:160` already asserts runtime choices carry no review flags.

Deleting it requires coordinated edits because the audit path consumes it: `rules.py:196` (emission), `production.py`/`inspection.py` (review summaries in inspection artifacts), `schema_validation.py` REVIEW_COLUMNS, `build_rule_sources.py` (writes it), `grand-sport-rule-audit` artifacts/test. Execute as its own pass:

1. Stop emitting `review_flag` in `rules.py` / `production.py` outputs and `form_rules`/`form_price_rules` sheets.
2. Drop the column from the 11 source sheets.
3. Update `schema_validation.py`, `build_rule_sources.py`, and the header/contract tests; regenerate artifacts; document the expected contract diff (removed key only) via `scripts/compare-generated-contracts.mjs`.

Conflict note: AGENTS.md lists "validation and review metadata" as workbook-owned. This spec follows the explicit cleanup directive; the audit *sheets* (`rule_phrase_map`, `option_audit_groups`/`_members`, `rule_review_groups`) are retained because loaders and `tests/audit-parser-metadata-loaders.test.mjs` actively read them.

### Columns explicitly retained despite looking deletable

- `normalization_status`, `generation_action` (rule sheets): gate `runtime_authored_rule()` — deleting changes which rules generate.
- `original_detail_raw`: becomes runtime `source_note`.
- `notes` columns everywhere: emitted into rule-group/price-rule contracts and useful for manual editing.
- `included_option_id` (`lt_interiors`/`LZ_Interiors`): read by `production.py` (15/132 filled in `lt_interiors` is by design; 0/130 in `LZ_Interiors` is flagged below).
- Sparse-by-design override columns (`variant_option_overrides.status/selectable`, `section_presentation` overrides, `display_behavior`, scope columns): blank means "no override".

## 5. Phase 3 — Sheet reorganization (functional grouping)

> **STATUS: COMPLETED 2026-06-10.** All 81 sheets reordered into the 9 groups below with tab colors (model control blue `4472C4`, shared structure teal `2E9E9E`, interiors/pricing green `70AD47`, the three model blocks yellow `FFC000`, ZR1/ZR1X scaffolds gray `A6A6A6`, parser/audit orange `ED7D31`, generated red `C00000`). `write_sheet()` in `scripts/corvette_form_generator/workbook.py` now stamps the red tab on every regenerated `form_*` sheet, and the generator's append-at-end behavior keeps the generated group last — order and colors verified to survive full regeneration. Sheet renames remain deferred as specified.

Reorder tabs into the following groups, in this order, with one tab color per group. Reordering is safe: every consumer addresses sheets by name. Run `repair_workbook_tables.py` + `validate_workbook_package.py` after the move.

1. **Model control** (blue): `model_master`, `model_registry_promotion`, `model_workbook_sources`, `model_variants`, `variant_master`
2. **Shared structure & presentation** (teal): `section_master`, `context_section_master`, `section_presentation`, `runtime_steps`, `context_choice_copy`, `order_summary_sections`, `step_order_summary_map`, `default_selection_rules`, `runtime_rule_exceptions`, `variant_option_overrides`, `asset_map`
3. **Shared interiors & pricing** (green): `PriceRef`, `lt_interiors`, `LZ_Interiors`, `model_interior_scope`, `interior_components`, `color_overrides`
4. **Stingray** (yellow): `stingray_options`, `stingray_ovs`, `rule_mapping`, `rule_groups`, `rule_group_members`, `exclusive_groups`, `exclusive_group_members`, `price_rules`
5. **Grand Sport** (yellow): the 9 `grandSport_*` sheets
6. **Z06** (yellow): the 9 `z06_*` sheets
7. **ZR1 / ZR1X scaffolds** (gray): the 14 `zr1_*`/`zr1x_*` sheets — retained as approved future-model scaffolds
8. **Parser/audit metadata** (orange): `rule_phrase_map`, `option_audit_groups`, `option_audit_group_members`, `rule_review_groups`
9. **Generated — do not edit** (red): the 11 `form_*` sheets, last

Deferred (separate approval): renaming Stingray's unprefixed sheets (`rule_mapping` → `stingray_rule_mapping`, etc.) and normalizing `grandSport_`/`LZ_Interiors` casing. Renames touch `model_workbook_sources` rows, `model_configs.py`, `schema_validation.py`, and header-lock tests; not part of this cleanup.

## 6. Phase 4 — Data inconsistency register (flag only; do NOT fix in this pass)

| # | Inconsistency | Location | Follow-up |
|---|---|---|---|
| 1 | ~~Z06 rows inactive in `model_workbook_sources`~~ **RESOLVED upstream** — rows are `active=True`; residual: their `notes` still read "Phase 3 inactive scaffold target; not consumed until model is promoted" (stale text) | `model_workbook_sources` | refresh stale `notes` text |
| 2 | ~~`model_variants` marks Z06 inactive~~ **RESOLVED upstream** — Z06 variant rows are `active=True` real booleans; ZR1/ZR1X correctly inactive | `model_variants` | none |
| 3 | Two variant-override contracts: global `variant_option_overrides` treats `active` as an override *value*; model sheets (`grandSport/z06/zr1/zr1x_variant_overrides`) treat `active` as row activation and use `note` vs `notes` (documented in `load_variant_option_overrides` docstring) | both sheet families | converge on one contract |
| 4 | Interior availability has two pathways: Stingray via `lt_interiors.active_for_stingray`; Grand Sport/Z06 via `model_interior_scope` rows | `lt_interiors`, `model_interior_scope` | migrate Stingray to `model_interior_scope` |
| 5 | `active_for_stingray` column exists (and is read) in `LZ_Interiors`, a Z-family sheet — model-misnamed gating column | `LZ_Interiors` | rename with pathway #4 |
| 6 | Header style drift: interiors sheets use Title Case with spaces (`Interior Name`, `Detail from Disclosure`); `PriceRef` uses `OptionType/Trim/Code/Price`; everything else snake_case | `lt_interiors`, `LZ_Interiors`, `PriceRef` | standardize headers + loaders |
| 7 | Sheet-name prefix drift: `grandSport_*` camelCase vs `z06_*` lowercase vs unprefixed Stingray sheets; `exclusive_group_members` (Stingray) vs `*_exclusive_members` (others) | workbook-wide | rename pass (deferred, §5) |
| 8 | Two runtime artifact pathways: Stingray embeds via `form_*` sheets → `form-app/data.js`; Grand Sport/Z06 load `form-output/inspection/*-form-data-draft.json` at runtime ("draft"-named files serving production) | `model_registry_promotion`, `form-app/data.js` | consolidate artifact naming/path |
| 9 | `z06_rule_mapping` is partially normalized vs Stingray/Grand Sport: `generation_action` 0/55, `source_type` 51/55, `target_selection_mode` 36/55 filled | `z06_rule_mapping` | complete Z06 normalization |
| 10 | `LZ_Interiors.included_option_id` 0/130 vs `lt_interiors` 15/132 — same schema, divergent use of the R6X include pathway | `LZ_Interiors` | confirm Z06 include semantics |
| 11 | `asset_map` has 1–3 rows missing `model_key`/`target_type`/`image_url`/`target_id` | `asset_map` | repair or deactivate rows |
| 12 | ~~Cell-type drift: 767 cells storing booleans/prices as text~~ **RESOLVED 2026-06-10** — all 767 cells retyped to real Excel booleans/numbers (626 bool, 141 price); `validate_workbook_schema` error_count now 0; generated contracts verified byte-identical. The 2 failing `workbook-schema-standardization` subtests turned out to be stale Z06 expectations (test asserted Z06 `model_variants`/`model_workbook_sources` rows inactive, contradicting promotion) and were updated to expect the promoted state | `z06_options`, `z06_rule_groups`, `z06_rule_group_members`, `z06_exclusive_groups`, `z06_exclusive_members`, `z06_rule_mapping`, `LZ_Interiors` | none |

## 7. Constraints (repeated back)

- No live-app behavior change: endpoint, payload shape, Turnstile, and `window.CORVETTE_FORM_DATA` registry untouched.
- No new dependencies; no runtime refactor; no hardcoded model-specific logic added.
- Workbook writes only through `save_workbook_safely()`; Excel closed; verify saved sheets on disk with openpyxl before claiming completion.
- Do not hand-edit `form_*` sheets — they are regenerated after source changes.
- Inconsistencies in §6 are flagged, not fixed.

## 8. Risks & non-goals

- **Risk:** header-lock tests and `schema_validation.py` will fail until updated in the same pass as each column deletion — sequence workbook edit + code/test edit together per phase.
- **Risk:** a future `build_rule_sources.py` re-run could recreate deleted normalization columns if its emit schema isn't updated (included in Phase 2 scope).
- **Risk:** Tier B (`review_flag`) changes the generated contract shape (key removal only); verify with `compare-generated-contracts.mjs`.
- **Non-goals:** sheet renames (§5 deferred), fixing §6 inconsistencies, ZR1/ZR1X promotion, interior pathway migration, any `form-app` styling/behavior change.

## 9. Validation plan (gates per phase)

After each phase:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
node scripts/compare-generated-contracts.mjs before.json after.json   # per model
```

Then the full test suite from AGENTS.md ("Full current suite"). Acceptance criteria:

1. Sheet count 96 → 81; archive workbook contains the 13 extracted sheets unmodified.
2. Generated JSON contracts byte-identical to baseline except documented removed keys (`review_flag` in Tier B).
3. All gates green; `form-app` manual smoke per AGENTS.md Static App Workflow (model switching, pricing, build download, submission modal).
4. §6 register copied into a follow-up task list.
