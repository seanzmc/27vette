# Phase 7 Future Model Raw Source Review Map Spec

## Diagnosis

Z06, ZR1, and ZR1X have inactive workbook/runtime scaffolding and header-only normalized source sheets, but the migration source should now be the newly added raw order-guide sheets rather than the older hidden archive preview sheets.

Current evidence from `z06-zr1-migration`:

- Working tree contains user-added workbook changes in `stingray_master.xlsx`.
- The new raw sheets are present and visible:
  - `price_sched_raw`: 306 rows x 11 columns, 11 merged ranges
  - `z06_standard_raw`: 128 rows x 9 columns, 99 merged ranges
  - `z06_eqgrps_raw`: 478 rows x 9 columns, 747 merged ranges
  - `z06_intextmec_raw`: 599 rows x 9 columns, 867 merged ranges
  - `zr1_zr1x_standard_raw`: 124 rows x 11 columns, 103 merged ranges
  - `zr1_zr1x_eqgrps_raw`: 349 rows x 11 columns, 643 merged ranges
  - `zr1_zr1x_intextmec_raw`: 476 rows x 11 columns, 803 merged ranges
- Header-only target source sheets still exist and should remain unpromoted:
  - `z06_options`, `z06_ovs`
  - `zr1_options`, `zr1_ovs`
  - `zr1x_options`, `zr1x_ovs`
- `future_model_source_review` does not exist yet.
- The older hidden archive sheets still exist:
  - `archive_Z06_Ingest`
  - `archive_ZR1_Ingest`
  - `archive_ZR1X_Ingest`
  These should become historical/legacy evidence for comparison only, not the primary source for Phase 7 source population.

The raw order-guide tables have a materially different shape from the previous archive preview data:

- Raw option sheets use order-guide headers at rows 7-9:
  - column A: `Orderable RPO Code`
  - column B: `Ref. Only RPO Code`
  - column C: `Description`
  - variant/status columns begin at column D
- Z06 raw variant columns are:
  - `1YH07` / `1LZ` -> `1lz_h07`
  - `1YH07` / `2LZ` -> `2lz_h07`
  - `1YH07` / `3LZ` -> `3lz_h07`
  - `1YH67` / `1LZ` -> `1lz_h67`
  - `1YH67` / `2LZ` -> `2lz_h67`
  - `1YH67` / `3LZ` -> `3lz_h67`
- Combined ZR1/ZR1X raw variant columns are:
  - `1YR07` / `1LZ` -> `zr1` / `1lz_r07`
  - `1YR07` / `3LZ` -> `zr1` / `3lz_r07`
  - `1YR67` / `1LZ` -> `zr1` / `1lz_r67`
  - `1YR67` / `3LZ` -> `zr1` / `3lz_r67`
  - `1YS07` / `1LZ` -> `zr1x` / `1lz_s07`
  - `1YS07` / `3LZ` -> `zr1x` / `3lz_s07`
  - `1YS67` / `1LZ` -> `zr1x` / `1lz_s67`
  - `1YS67` / `3LZ` -> `zr1x` / `3lz_s67`
- Vertical merged cells are essential source structure, not workbook noise. Example observed in `z06_standard_raw`:
  - rows 10-13 represent one AJ7 option block.
  - `B10:B13` and status columns `D10:I13` are merged.
  - row 10 column C is the option description.
  - row 12 column C is a disclosure statement.
  - The parser must treat the disclosure as part of the same raw option block, not as a separate option row.
- Similar merged option/disclosure spans occur throughout all six option raw sheets.
- The price schedule is a separate raw source:
  - base model prices appear near rows 9-40.
  - option price rows begin under `Additional Options` around row 47.
  - repeated RPOs with different application text and price values exist, so price schedule rows must be review candidates and later price-rule input, not blindly copied into a single option price value.

Root cause: the previous Phase 7 plan assumed the Phase 5 archive-derived preview was the best staging input. That is now stale. Phase 7 should use the true raw order-guide sheets as the source of future-model option/OVS migration, with a parser that preserves merged option/disclosure blocks, variant status tokens, price schedule application text, and raw source provenance.

Change type: workbook schema/data + scripts + generated inspection artifacts + tests. No live runtime promotion.

Risk level: medium. The work will write a workbook-owned review map and eventually normalized future source sheets. Risk to the current live app remains low if future model metadata stays inactive/unpromoted and `form-app/data.js` is not touched.

## Exact Files and Workbook Sheets To Change

### Workbook

Modify `stingray_master.xlsx` only through approved scripts and safe-save helpers:

1. Treat these sheets as read-only raw source inputs:
   - `price_sched_raw`
   - `z06_standard_raw`
   - `z06_eqgrps_raw`
   - `z06_intextmec_raw`
   - `zr1_zr1x_standard_raw`
   - `zr1_zr1x_eqgrps_raw`
   - `zr1_zr1x_intextmec_raw`

2. Create the durable source/review sheet:
   - `future_model_source_review`

3. Keep these normalized sheets header-only until source population is explicitly approved:
   - `z06_options`
   - `z06_ovs`
   - `zr1_options`
   - `zr1_ovs`
   - `zr1x_options`
   - `zr1x_ovs`

4. Do not activate or promote:
   - `model_master` rows for `z06`, `zr1`, `zr1x`
   - `model_workbook_sources` rows for `z06`, `zr1`, `zr1x`
   - `model_registry_promotion` rows for `z06`, `zr1`, `zr1x`

5. Do not edit the raw sheets manually during script runs. The raw sheets are evidence/provenance.

### Scripts

Modify:

- `scripts/corvette_form_generator/future_model_ingest.py`
  - Rename the module docstring and internal terms from archive-only to raw-source-aware.
  - Add raw source sheet metadata for Z06, ZR1, and ZR1X.
  - Add an `openpyxl` merged-cell-aware parser.
  - Keep legacy archive helpers only if useful for comparison tests; do not use them as the default Phase 7 input.
  - Add constants for `future_model_source_review` headers.
  - Add `build_raw_source_blocks()`.
  - Add `build_price_schedule_rows()`.
  - Add `build_raw_source_preview()`.
  - Add `build_source_review_rows()` from raw-source blocks and price candidates.
  - Add review-row loader/validator helpers.
  - Add source/OVS row materialization helpers from approved review rows.

- `scripts/build_future_model_source_preview.py`
  - Change default preview generation to use the new raw-source parser.
  - Preserve non-mutating behavior.
  - Include raw block/disclosure/price-candidate summaries in the generated artifacts.
  - If legacy archive comparison is retained, make it explicit, e.g. `--legacy-archive-compare`; do not silently mix archive rows with raw rows.

Create:

- `scripts/create_future_model_source_review.py`
  - Reads the raw source sheets.
  - Writes/rebuilds `future_model_source_review` only.
  - Saves through `save_workbook_safely()`.
  - Refuses to run if `~$stingray_master.xlsx` exists.
  - Must be idempotent and deterministic.
  - Must not overwrite manually reviewed `approved_*`, `review_status`, `active`, `copy_from_*`, `duplicate_group_id`, or `notes` values unless an explicit `--reset-reviewed-fields` flag is provided.

- `scripts/apply_future_model_source_review.py`
  - Reads `future_model_source_review`.
  - Supports `--model-key z06|zr1|zr1x|all`.
  - Supports `--dry-run` and default non-dry-run.
  - Writes only approved active rows into target `*_options` and `*_ovs` sheets.
  - Saves through `save_workbook_safely()`.
  - Refuses to write unresolved/needs-review rows into active source sheets.

### Tests

Create:

- `tests/test_future_model_raw_source_parser.py`
  - Covers merged block parsing, disclosure attachment, variant column mapping, raw status normalization, combined ZR1/ZR1X model splitting, and price schedule candidate extraction.

- `tests/test_future_model_source_review.py`
  - Covers review row generation, idempotent review preservation, blocked-row validation, and source materialization dry runs.

Modify, if needed:

- `tests/test_future_model_ingest_preview.py`
  - Update expected preview source from legacy archive sheets to raw order-guide sheets.
  - Preserve or move archive tests under explicit legacy comparison coverage only.

- `tests/test_schema_validation_metadata.py`
  - Ensure raw sheets can exist without being treated as active normalized source sheets.
  - Ensure `future_model_source_review` schema is validated only when present.

- `tests/workbook-schema-standardization.test.mjs`
  - Add/adjust accepted raw staging sheet expectations if the workbook schema standardizer flags the new sheets.

### Generated inspection artifacts

Regenerate if implementation touches preview/review output:

- `form-output/inspection/future-model-source-preview.json`
- `form-output/inspection/future-model-source-preview.md`

Optionally create review summary artifacts:

- `form-output/inspection/future-model-source-review.json`
- `form-output/inspection/future-model-source-review.md`

Do not change `form-app/data.js` as part of Phase 7.

## Raw Source Sheet Contract

### Source groups

Use the raw sheets as typed source groups:

| Source group | Sheets | Purpose |
|---|---|---|
| `price_schedule` | `price_sched_raw` | base model prices, option price candidates, conditional application text |
| `standard_equipment` | `z06_standard_raw`, `zr1_zr1x_standard_raw` | model/variant standard-equipment status evidence |
| `equipment_groups` | `z06_eqgrps_raw`, `zr1_zr1x_eqgrps_raw` | equipment group inclusion/upgrade evidence and some option availability |
| `interior_exterior_mechanical` | `z06_intextmec_raw`, `zr1_zr1x_intextmec_raw` | broad option availability, descriptions, disclosures, and compatibility prose |

Raw source group is provenance only. It may contribute candidate section/source-type hints, but final `section_id`, option identity, display behavior, labels, descriptions, and review status belong to `future_model_source_review` and later normalized source sheets.

### Merged-cell parsing requirements

The parser must not rely on `iter_rows(values_only=True)` alone, because merged child cells are blank in `openpyxl`.

For each raw option sheet:

1. Build a merged-cell anchor map:
   - For any coordinate inside a merged range, resolve to the top-left anchor value and the range start/end rows.
   - Preserve the original coordinate and the anchor coordinate separately.

2. Detect variant columns from rows 7-9:
   - row 7 supplies model/body display text.
   - row 8 supplies model/body code.
   - row 9 supplies trim.
   - Map known `(model code, trim)` pairs to canonical `variant_id`.
   - In combined ZR1/ZR1X sheets, split columns into separate model outputs by code prefix (`1YR*` vs `1YS*`).

3. Detect raw option blocks:
   - A block starts on a row whose RPO/status cells are actual top-left cells or unmerged single cells, not on a merged child row.
   - The block end row is the maximum end row across vertical merges in columns A, B, and the variant/status columns for that block.
   - Column C on the block start row is the primary raw option description.
   - Nonblank column C values inside the same block after the start row are disclosure/detail lines for that block.
   - Do not emit disclosure/detail lines as separate option rows.
   - Preserve `raw_start_row`, `raw_end_row`, and contributing `raw_disclosure_rows`.

4. Detect section/category rows:
   - Rows such as `Equipment Groups`, `Additional Options`, `Battery:`, `Brakes:`, etc. have source value but no variant statuses.
   - Preserve the most recent category as `raw_category_context` for subsequent blocks.
   - Do not treat category text as final normalized `section_id` without review.

5. Preserve both RPO columns:
   - `source_orderable_rpo` from column A.
   - `source_ref_rpo` from column B.
   - `source_primary_rpo` is initially column A when present, otherwise column B.
   - Rows with no RPO in either column are valid raw evidence but must be flagged `missing_rpo` and blocked from active source emission until reviewed.

6. Preserve raw and normalized status values:
   - Store raw status token per variant.
   - Store normalized status candidate per variant.
   - Store token notes/flags when the raw status has footnote or inclusion semantics.

### Raw status token normalization

Initial candidate normalization:

| Raw token | Candidate normalized status | Required preservation/flags |
|---|---|---|
| `S` | `standard` | none |
| `S1`, `S2`, etc. | `standard` | preserve suffix as `status_note` / disclosure evidence |
| `A` | `available` | none |
| `A1`, `A2`, etc. | `available` | preserve suffix as `status_note` / disclosure evidence |
| `--` | `unavailable` | none |
| `D` | `available` | flag `dealer_installed_status` / ADI evidence |
| `■` | `standard` candidate | flag `included_in_equipment_group` |
| `□` | `standard` candidate | flag `included_in_equipment_group_upgradeable`; require review before active emission |
| blank | blank | allowed only for variants outside row/model scope; otherwise flag `blank_variant_status` |
| any other token | blank | flag `unknown_status` |

Do not discard the distinction between `S`, `S1`, `A1`, `■`, and `□`. The normalized source sheets may only support `available`, `standard`, and `unavailable`, but the review map must preserve the raw token and semantics for later rule/price/group decisions.

### Price schedule parsing requirements

Parse `price_sched_raw` separately:

- Base model price rows:
  - Use as evidence for future model base-price review and later model/variant metadata work.
  - Do not write into option source sheets during Phase 7.
- Additional option price rows:
  - Capture `price_rpo`, `price_description`, `price_application`, `price_list`, `price_msrp`, `price_invoice`, and `raw_price_row`.
  - Match price candidates to raw option blocks by RPO and, where possible, normalized description text.
  - Repeated RPOs with different application text/prices must be preserved as multiple candidates and flagged as `price_schedule_multiple_candidates`.
  - Conditional rows must not be collapsed into a single `approved_price`; they are likely future `price_rules` or review decisions.
  - Do not copy Grand Sport price values to future models.

## Proposed Workbook Review Sheet Contract

Create `future_model_source_review` with one row per consolidated raw option candidate, not one row per disclosure line.

A consolidated candidate may have multiple contributing raw blocks when the same semantic row appears across `standard`, `equipment_groups`, and `interior_exterior_mechanical` sheets. The row must preserve enough provenance to trace back to every contributing raw sheet/span.

Required columns:

| Column | Purpose |
|---|---|
| `model_key` | `z06`, `zr1`, or `zr1x` |
| `source_group` | Primary source group used for the candidate |
| `raw_source_sheets` | `|`-delimited contributing raw sheets |
| `raw_source_spans` | `|`-delimited `sheet:start-end` references |
| `raw_category_context` | Last raw category/header context, if any |
| `source_orderable_rpo` | Raw orderable RPO from column A |
| `source_ref_rpo` | Raw ref-only RPO from column B |
| `source_primary_rpo` | Initial RPO selected from column A or B |
| `source_option_description` | Raw block-start description |
| `source_disclosure_raw` | Joined disclosure/detail rows from the same merged block |
| `source_detail_raw` | Combined provenance/detail text to carry into normalized source review |
| `candidate_option_id` | Deterministic draft option ID |
| `candidate_section_id` | Candidate section ID when unambiguous |
| `candidate_section_resolution` | `resolved`, `conflict`, or `unresolved` |
| `candidate_section_candidates` | `|`-delimited section candidates for conflicts |
| `candidate_display_behavior` | Derived display behavior if exact source match found |
| `candidate_price` | Single safe price candidate only when unambiguous |
| `price_candidate_rows` | `|`-delimited price schedule raw row refs |
| `price_candidate_summary` | Human-readable price candidate/application summary |
| `review_flags` | `; `-delimited flags, e.g. `section_conflict`, `duplicate_rpo`, `missing_rpo`, `price_schedule_multiple_candidates` |
| `approved_option_id` | Final stable option ID to write to `*_options` |
| `approved_rpo` | Final RPO to write; can remain blank only if row is inactive/review-only |
| `approved_price` | Final option-level price only when safe; blank if price rules are needed |
| `approved_option_name` | Final customer-facing label |
| `approved_description` | Final customer-facing description |
| `approved_detail_raw` | Final provenance/detail raw text |
| `approved_section_id` | Final section ID |
| `approved_selectable` | Final source selectable boolean |
| `approved_display_behavior` | Final display behavior, blank/default unless intentionally set |
| `approved_display_order` | Final display order in target source sheet |
| `copy_from_model_key` | Optional reviewed source model for semantic identity, usually `grand_sport` or `stingray` |
| `copy_from_option_id` | Optional reviewed source option ID for future Grand Sport compatibility rebase |
| `duplicate_group_id` | Optional reviewer-owned identity group for duplicate RPO rows |
| `review_status` | `approved`, `needs_review`, `inactive`, or `deferred` |
| `review_reason` | Human-readable reason/blocker/decision |
| `active` | Whether the reviewed row can be emitted to normalized source sheets |
| `notes` | Free-form reviewer notes |

Variant status columns:

- Raw token columns:
  - `raw_status_1lz_h07`, `raw_status_2lz_h07`, `raw_status_3lz_h07`, `raw_status_1lz_h67`, `raw_status_2lz_h67`, `raw_status_3lz_h67`
  - `raw_status_1lz_r07`, `raw_status_3lz_r07`, `raw_status_1lz_r67`, `raw_status_3lz_r67`
  - `raw_status_1lz_s07`, `raw_status_3lz_s07`, `raw_status_1lz_s67`, `raw_status_3lz_s67`
- Normalized status columns:
  - `status_1lz_h07`, `status_2lz_h07`, `status_3lz_h07`, `status_1lz_h67`, `status_2lz_h67`, `status_3lz_h67`
  - `status_1lz_r07`, `status_3lz_r07`, `status_1lz_r67`, `status_3lz_r67`
  - `status_1lz_s07`, `status_3lz_s07`, `status_1lz_s67`, `status_3lz_s67`

Only columns for the row's model are populated. Valid normalized status values are `available`, `standard`, `unavailable`, or blank when the variant does not belong to that model.

Initial seeding rules:

- Rows with no review flags may be prefilled as:
  - `review_status=approved`
  - `active=True`
  - approved fields copied from candidate/source fields
- Rows with any review flags are prefilled as:
  - `review_status=needs_review`
  - `active=False`
  - approved fields copied from candidate/source fields where safe, but blocked from source emission until reviewed
- Rows containing disclosure/detail text should keep that text in `approved_detail_raw` by default, not in the customer-facing option name.
- Rows with no RPO in either raw RPO column must remain inactive until `approved_rpo` and `approved_option_id` are explicitly reviewed.
- Section conflicts/unresolved sections must remain inactive until `approved_section_id` is explicitly reviewed.
- Duplicate-RPO rows must remain inactive unless `approved_option_id` and, when needed, `duplicate_group_id` or `copy_from_option_id` make the intended identity explicit.
- Rows with multiple price schedule candidates must keep `approved_price` blank or `needs_review` until the option-level price vs price-rule decision is made.
- `□` upgradeable inclusion rows should require review before active emission because OVS status alone cannot express the upgrade path.

## Source Population Rules

`apply_future_model_source_review.py` may write rows only when all are true:

- `model_key` matches selected model.
- `review_status=approved`.
- `active=True`.
- `approved_option_id` is nonblank and unique per model.
- `approved_rpo` is nonblank unless a future explicit exception is approved.
- `approved_section_id` is nonblank and exists in `section_master`.
- Variant status values for the model's variants are all present and known.
- No blocking flags remain unresolved.

For each approved row, write target `*_options`:

- `option_id` = `approved_option_id`
- `rpo` = `approved_rpo`
- `price` = `approved_price`
- `option_name` = `approved_option_name`
- `description` = `approved_description`
- `detail_raw` = `approved_detail_raw`
- `section_id` = `approved_section_id`
- `selectable` = `approved_selectable`
- `display_order` = `approved_display_order`
- `active` = `active`
- `display_behavior` = `approved_display_behavior`

For each approved row and each model variant, write target `*_ovs`:

- `option_id`
- `variant_id`
- `status`

Do not write unresolved or inactive review rows to normalized source sheets. Do not activate `model_workbook_sources` yet.

## Constraints

- Workbook source of truth remains strict.
- The seven raw sheets are now the primary source for future-model option/OVS migration.
- Legacy `archive_*_Ingest` sheets are historical comparison evidence only.
- No new dependencies.
- No runtime promotion in Phase 7.
- No `form-app/app.js` changes.
- No `form-app/data.js` changes.
- No dealer submission endpoint, payload, or Turnstile changes.
- Do not edit generated `form_*` sheets directly.
- Do not edit raw source sheets in-place as part of parsing or review-map creation.
- Do not add compatibility/rule/exclusive-group copying in Phase 7; that remains Phase 8.
- Do not add LZ interiors/runtime metadata in Phase 7; that remains Phase 9.
- Do not solve section conflicts or duplicate RPOs in Python/JS heuristics when they require human review.
- Do not write unresolved rows into active future source sheets.
- Check for `~$stingray_master.xlsx` before workbook writes.
- Save workbook writes only through `save_workbook_safely()`.
- Verify saved workbook rows on disk with `openpyxl` before claiming the workbook change landed.

## Risks

- Merged-cell parsing is the main technical risk. A naive row reader will drop RPO/status values on disclosure rows and can accidentally emit disclosures as separate options.
- The raw sheets intentionally overlap. Some rows appear in standard/equipment group/intextmec sources. Consolidation must preserve provenance and flag real conflicts instead of silently deduping by RPO alone.
- Combined ZR1/ZR1X sheets must split variant columns by model code. A parser that treats all columns as one model would produce invalid OVS rows.
- `■` and `□` tokens carry equipment-group semantics that normalized OVS statuses cannot fully express. The review map must preserve those tokens for later rule/group work.
- Repeated price schedule RPOs with application text are likely price-rule candidates. Collapsing them into a single option price would lose business logic.
- Raw category rows are useful evidence but not final `section_id` values.
- Source population can create partial future model source sheets if run before all review rows are approved. Tests should make partial status explicit and keep model metadata inactive.

## Non-Goals

- Do not populate rule mapping, price rules, grouped rules, exclusive groups, or members.
- Do not copy Grand Sport compatibility behavior yet.
- Do not copy Grand Sport price values.
- Do not wire LZ interiors.
- Do not add `generate_model_form.py`.
- Do not promote Z06, ZR1, or ZR1X into `form-app/data.js`.
- Do not manually review/resolve all flagged rows in this implementation pass unless separately approved.
- Do not update live runtime behavior.

## Validation Plan

1. Confirm branch state and no workbook lock:

   ```sh
   git status --short --branch
   test ! -e './~$stingray_master.xlsx'
   ```

   Expected before implementation: `stingray_master.xlsx` may already be modified by the user-added raw sheets. Do not overwrite or discard those changes.

2. Run raw sheet inspection:

   ```sh
   .venv/bin/python - <<'PY'
   from openpyxl import load_workbook
   wb = load_workbook('stingray_master.xlsx', read_only=False, data_only=False)
   for name in [
       'price_sched_raw',
       'z06_standard_raw', 'z06_eqgrps_raw', 'z06_intextmec_raw',
       'zr1_zr1x_standard_raw', 'zr1_zr1x_eqgrps_raw', 'zr1_zr1x_intextmec_raw',
   ]:
       ws = wb[name]
       print(name, ws.max_row, ws.max_column, len(ws.merged_cells.ranges))
   PY
   ```

3. Write parser tests first:

   ```sh
   .venv/bin/python -m pytest tests/test_future_model_raw_source_parser.py -q
   ```

   Initial expected failure: raw parser helpers do not exist yet.

4. Implement raw-source parser and preview updates.

5. Run raw parser and preview tests:

   ```sh
   .venv/bin/python -m pytest tests/test_future_model_raw_source_parser.py tests/test_future_model_ingest_preview.py -q
   ```

6. Run updated preview and confirm it remains non-mutating:

   ```sh
   .venv/bin/python scripts/build_future_model_source_preview.py
   git diff -- stingray_master.xlsx
   ```

   Expected: no workbook diff from preview generation alone beyond pre-existing user-added raw sheets.

7. Run new review-sheet creation script:

   ```sh
   .venv/bin/python scripts/create_future_model_source_review.py
   ```

8. Verify workbook on disk with `openpyxl`:

   - `future_model_source_review` exists.
   - It has one row per consolidated raw option candidate, not one row per disclosure line.
   - Rows with merged disclosure spans preserve `raw_source_spans` and `source_disclosure_raw`.
   - Rows with review flags are `needs_review` and inactive.
   - Rows with no review flags are approved and active.
   - Future model target source sheets are still 0 rows unless population script is intentionally run.
   - Z06/ZR1/ZR1X metadata remains inactive/unpromoted.

9. Run new source population dry run:

   ```sh
   .venv/bin/python scripts/apply_future_model_source_review.py --model-key all --dry-run
   ```

   Expected: reports approved/blocked counts and writes no workbook changes.

10. If separately approved to test actual source population, run one model at a time, starting with Z06:

   ```sh
   .venv/bin/python scripts/apply_future_model_source_review.py --model-key z06
   ```

   Expected: only approved active Z06 rows are written to `z06_options` and `z06_ovs`; `model_workbook_sources` remains inactive.

11. Run schema validation:

   ```sh
   .venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
   ```

12. Run targeted Python tests:

   ```sh
   .venv/bin/python -m pytest tests/test_future_model_raw_source_parser.py tests/test_future_model_ingest_preview.py tests/test_future_model_source_review.py tests/test_schema_validation_metadata.py
   ```

13. Run workbook schema JS gate:

   ```sh
   node --test tests/workbook-schema-standardization.test.mjs
   ```

14. Review diffs:

   ```sh
   git diff --stat
   git diff -- stingray_master.xlsx scripts/corvette_form_generator/future_model_ingest.py scripts/build_future_model_source_preview.py tests form-output/inspection
   ```

15. Do not run runtime gates unless a diff unexpectedly touches runtime files. If runtime files change, stop and explain before proceeding.

## Clarifications To Confirm Before Implementation

These do not block revising the spec, but they should be confirmed before writing source population logic:

1. Treat `price_sched_raw` as authoritative future-model price evidence, but not as automatic option-level price assignment when the same RPO has multiple application rows. This spec assumes yes.
2. Treat the older hidden `archive_*_Ingest` sheets as legacy comparison evidence only. This spec assumes yes.
3. Preserve disclosure text from merged blocks in `detail_raw`/provenance by default, not in customer-facing option labels. This spec assumes yes.

## Approval Gate

Approve this revised spec before implementation.

Recommended implementation scope after approval:

1. Add the raw merged-cell parser, preview updates, and parser tests.
2. Add review-sheet creation from raw source blocks.
3. Create and validate `future_model_source_review` in `stingray_master.xlsx`.
4. Leave `z06_options`, `zr1_options`, `zr1x_options` and matching OVS sheets header-only unless source population is explicitly approved in the same pass.

Suggested first implementation boundary: raw parser + preview + review map only. Source population from approved rows should be a follow-up once the review sheet is inspectable.
