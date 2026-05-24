# Phase 7 Future Model Source Review Map Spec

## Diagnosis

Z06, ZR1, and ZR1X have inactive workbook/runtime scaffolding, hidden archive ingest sheets, and non-mutating preview artifacts, but they do not yet have reviewed normalized source rows.

Current evidence from `z06-zr1-migration` at `df88a9935be31c54806f63b97e9ff66fea7a4b9c`:

- Branch is clean before this spec, tracking `origin/z06-zr1-migration`.
- `future_model_source_review` does not exist yet.
- Header-only target source sheets exist and contain 0 data rows:
  - `z06_options`, `z06_ovs`
  - `zr1_options`, `zr1_ovs`
  - `zr1x_options`, `zr1x_ovs`
- Hidden archive sheets exist:
  - `archive_Z06_Ingest`: 363 rows
  - `archive_ZR1_Ingest`: 336 rows
  - `archive_ZR1X_Ingest`: 337 rows
- `form-output/inspection/future-model-source-preview.json` currently projects archive rows into draft option/OVS-shaped data:
  - Z06: 363 proposed options, 2178 proposed OVS rows
  - ZR1: 336 proposed options, 1344 proposed OVS rows
  - ZR1X: 337 proposed options, 1348 proposed OVS rows
- Preview review counts show the actual blocker is manual normalization, not runtime wiring:
  - Z06: 14 section conflicts, 109 unresolved sections, 52 missing-RPO rows, 156 duplicate-RPO rows, 252 rows needing review
  - ZR1: 14 section conflicts, 110 unresolved sections, 52 missing-RPO rows, 162 duplicate-RPO rows, 247 rows needing review
  - ZR1X: 14 section conflicts, 111 unresolved sections, 52 missing-RPO rows, 164 duplicate-RPO rows, 248 rows needing review
- `scripts/corvette_form_generator/future_model_ingest.py` currently owns the non-mutating projection through:
  - `FUTURE_MODEL_SPECS`
  - `build_section_candidates()`
  - `resolve_section()`
  - `build_preview_for_model()`
  - `build_future_model_preview()`
- `scripts/build_future_model_source_preview.py` currently writes preview JSON/Markdown only and explicitly does not save the workbook.

Root cause: Phase 5 preview output is not a durable workbook-owned review/approval layer. It is sufficient to show candidate rows and blockers, but not sufficient to safely write normalized `*_options` and `*_ovs` rows. Phase 7 needs a review-owned mapping sheet first, then source population only from approved rows.

Change type: workbook schema/data + scripts + generated inspection artifacts + tests. No live runtime promotion.

Risk level: medium. The work writes the canonical workbook and can affect future source-data generation. Risk to current live app is low if future model metadata remains inactive/unpromoted and `form-app/data.js` is not changed except by unrelated explicit commands.

## Exact Files and Workbook Sheets To Change

### Workbook

Modify `stingray_master.xlsx`:

1. Create source/review sheet:
   - `future_model_source_review`

2. Keep these sheets header-only or source-populated only according to approval status:
   - `z06_options`
   - `z06_ovs`
   - `zr1_options`
   - `zr1_ovs`
   - `zr1x_options`
   - `zr1x_ovs`

3. Do not activate or promote:
   - `model_master` rows for `z06`, `zr1`, `zr1x`
   - `model_workbook_sources` rows for `z06`, `zr1`, `zr1x`
   - `model_registry_promotion` rows for `z06`, `zr1`, `zr1x`

### Scripts

Create:

- `scripts/create_future_model_source_review.py`
  - Reads archive sheets and preview candidates.
  - Writes/rebuilds `future_model_source_review` only.
  - Saves through `save_workbook_safely()`.
  - Refuses to run if `~$stingray_master.xlsx` exists.

- `scripts/apply_future_model_source_review.py`
  - Reads `future_model_source_review`.
  - Supports `--model-key z06|zr1|zr1x|all`.
  - Supports `--dry-run` and default non-dry-run.
  - Writes only approved active rows into target `*_options` and `*_ovs` sheets.
  - Saves through `save_workbook_safely()`.
  - Refuses to write unresolved/needs-review rows into active source sheets.

Modify:

- `scripts/corvette_form_generator/future_model_ingest.py`
  - Add constants for `future_model_source_review` headers.
  - Add `build_source_review_rows()` from preview data.
  - Add review-row loader/validator helpers.
  - Add source/OVS row materialization helpers from approved review rows.
  - Keep existing preview behavior non-mutating.

- `scripts/build_future_model_source_preview.py`
  - Leave default behavior non-mutating.
  - Optionally add no workbook write behavior here; workbook writes should stay in `create_future_model_source_review.py` to keep preview generation safe.

### Tests

Create:

- `tests/test_future_model_source_review.py`

Modify, if needed:

- `tests/test_future_model_ingest_preview.py`
- `tests/workbook-schema-standardization.test.mjs`

### Generated inspection artifacts

Regenerate if implementation touches preview/review output:

- `form-output/inspection/future-model-source-preview.json`
- `form-output/inspection/future-model-source-preview.md`

Optionally create review summary artifacts:

- `form-output/inspection/future-model-source-review.json`
- `form-output/inspection/future-model-source-review.md`

Do not change `form-app/data.js` as part of Phase 7.

## Proposed Workbook Review Sheet Contract

Create `future_model_source_review` with one row per archive option row, not only flagged rows. Expected total initial rows: 1036.

Required columns:

| Column | Purpose |
|---|---|
| `model_key` | `z06`, `zr1`, or `zr1x` |
| `archive_sheet` | Source archive sheet name |
| `archive_row` | Original Excel row number in archive sheet |
| `source_rpo` | Raw archive RPO |
| `source_price` | Raw archive price |
| `source_option_name` | Raw archive option name |
| `source_description` | Raw archive description |
| `source_detail_raw` | Raw archive detail/provenance |
| `source_category` | Raw archive category |
| `candidate_option_id` | Preview-proposed option ID |
| `candidate_section_id` | Preview-resolved section ID when unambiguous |
| `candidate_section_resolution` | `resolved`, `conflict`, or `unresolved` |
| `candidate_section_candidates` | `|`-delimited section candidates for conflicts |
| `candidate_display_behavior` | Preview-derived display behavior if exact source match found |
| `review_flags` | `; `-delimited flags from preview, e.g. `section_conflict`, `duplicate_rpo`, `missing_rpo` |
| `approved_option_id` | Final stable option ID to write to `*_options` |
| `approved_rpo` | Final RPO to write; can remain blank only if row is inactive/review-only |
| `approved_price` | Final numeric/blank price |
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

- `status_1lz_h07`, `status_2lz_h07`, `status_3lz_h07`, `status_1lz_h67`, `status_2lz_h67`, `status_3lz_h67`
- `status_1lz_r07`, `status_3lz_r07`, `status_1lz_r67`, `status_3lz_r67`
- `status_1lz_s07`, `status_3lz_s07`, `status_1lz_s67`, `status_3lz_s67`

Only columns for the row's model are populated. Valid status values are `available`, `standard`, `unavailable`, or blank when the variant does not belong to that model.

Initial seeding rules:

- Rows with no preview flags may be prefilled as:
  - `review_status=approved`
  - `active=True`
  - approved fields copied from candidate/source fields
- Rows with preview flags are prefilled as:
  - `review_status=needs_review`
  - `active=False`
  - approved fields copied from candidate/source fields where safe, but blocked from source emission until reviewed
- Missing-RPO rows must remain inactive until `approved_rpo` and `approved_option_id` are explicitly reviewed.
- Section conflicts/unresolved sections must remain inactive until `approved_section_id` is explicitly reviewed.
- Duplicate-RPO rows must remain inactive unless `approved_option_id` and, when needed, `duplicate_group_id` or `copy_from_option_id` make the intended identity explicit.

## Source Population Rules

`apply_future_model_source_review.py` may write rows only when all are true:

- `model_key` matches selected model.
- `review_status=approved`.
- `active=True`.
- `approved_option_id` is nonblank and unique per model.
- `approved_rpo` is nonblank unless a future explicit exception is approved.
- `approved_section_id` is nonblank and exists in `section_master`.
- Variant status values for the model's variants are all present and known.

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
- No new dependencies.
- No runtime promotion in Phase 7.
- No `form-app/app.js` changes.
- No `form-app/data.js` changes.
- No dealer submission endpoint, payload, or Turnstile changes.
- Do not edit generated `form_*` sheets directly.
- Do not add compatibility/rule/exclusive-group copying in Phase 7; that is Phase 8.
- Do not add LZ interiors/runtime metadata in Phase 7; that is Phase 9.
- Do not solve section conflicts or duplicate RPOs in Python/JS heuristics when they require human review.
- Do not write unresolved rows into active future source sheets.
- Check for `~$stingray_master.xlsx` before workbook writes.
- Save workbook writes only through `save_workbook_safely()`.
- Verify saved workbook rows on disk with `openpyxl` before claiming the workbook change landed.

## Risks

- Review sheet size: 1036 rows plus variant status columns is manageable but larger than prior metadata sheets.
- Human-review burden: 747 rows currently have one or more review flags. This spec creates the review layer; it does not magically resolve those decisions.
- Duplicate RPOs are high risk because future Phase 8 rule rebasing depends on stable option IDs, not RPO alone.
- If `approved_option_id` values drift after rules are copied later, Phase 8 resolver work will be harder.
- Existing preview section candidates use active Stingray/Grand Sport option rows as evidence. That is useful but not authoritative for future-model-only options.
- Source population can create partial future model source sheets if run before all review rows are approved. Tests should make partial status explicit and keep model metadata inactive.

## Non-Goals

- Do not populate rule mapping, price rules, grouped rules, exclusive groups, or members.
- Do not copy Grand Sport compatibility behavior yet.
- Do not copy Grand Sport price values.
- Do not wire LZ interiors.
- Do not add `generate_model_form.py`.
- Do not promote Z06, ZR1, or ZR1X into `form-app/data.js`.
- Do not manually review/resolve all 747 flagged rows in this implementation pass unless separately approved.
- Do not update live runtime behavior.

## Validation Plan

1. Confirm clean branch and no workbook lock:

   ```sh
   git status --short --branch
   test ! -e './~$stingray_master.xlsx'
   ```

2. Run existing preview and confirm it remains non-mutating:

   ```sh
   .venv/bin/python scripts/build_future_model_source_preview.py
   git diff -- stingray_master.xlsx
   ```

   Expected: no workbook diff from preview generation alone.

3. Run new review-sheet creation script:

   ```sh
   .venv/bin/python scripts/create_future_model_source_review.py
   ```

4. Verify workbook on disk with `openpyxl`:

   - `future_model_source_review` exists.
   - Row count is 1036.
   - Counts by `model_key` are:
     - `z06`: 363
     - `zr1`: 336
     - `zr1x`: 337
   - Rows with review flags are `needs_review` and inactive.
   - Rows with no review flags are approved and active.
   - Future model target source sheets are still 0 rows unless population script is intentionally run.

5. Run new source population dry run:

   ```sh
   .venv/bin/python scripts/apply_future_model_source_review.py --model-key all --dry-run
   ```

   Expected: reports approved/blocked counts and writes no workbook changes.

6. If approved to test actual source population, run one model at a time, starting with Z06:

   ```sh
   .venv/bin/python scripts/apply_future_model_source_review.py --model-key z06
   ```

   Expected: only approved active Z06 rows are written to `z06_options` and `z06_ovs`; `model_workbook_sources` remains inactive.

7. Run schema validation:

   ```sh
   .venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
   ```

8. Run targeted Python tests:

   ```sh
   .venv/bin/python -m pytest tests/test_future_model_ingest_preview.py tests/test_future_model_source_review.py tests/test_schema_validation_metadata.py
   ```

9. Run workbook schema JS gate:

   ```sh
   node --test tests/workbook-schema-standardization.test.mjs
   ```

10. If source sheets are populated, run preview again and review diffs:

   ```sh
   .venv/bin/python scripts/build_future_model_source_preview.py
   git diff --stat
   git diff -- stingray_master.xlsx form-output/inspection/future-model-source-preview.json form-output/inspection/future-model-source-preview.md
   ```

11. Do not run runtime gates unless a diff unexpectedly touches runtime files. If runtime files change, stop and explain before proceeding.

## Approval Gate

Approve this spec before implementation.

Recommended implementation scope after approval:

1. Add review-sheet and source-population helpers/tests.
2. Create `future_model_source_review` in `stingray_master.xlsx` from current preview data.
3. Leave `z06_options`, `zr1_options`, `zr1x_options` and matching OVS sheets header-only unless you explicitly approve source population in the same pass.

Suggested first implementation boundary: create and validate the review map only. Source population from approved rows can be a follow-up once the review sheet is inspectable.
