# Phase 7 Review Map To Future Source Sheets Spec

## Diagnosis

The current branch has completed the raw-source review-map staging step for future models. The workbook now contains `future_model_source_review`, and the normalized future source sheets still exist as header-only inactive scaffolds.

Current evidence from `z06-zr1-migration` before this spec:

- Working tree was clean before writing this spec.
- No Excel lock file was present at `./~$stingray_master.xlsx`.
- `form-app/data.js` and `form-app/app.js` had no diff.
- Workbook schema validation passed:
  - `.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx`
  - result: `status=valid`, `issue_count=0`
- Existing future-model gates passed:
  - `.venv/bin/python -m pytest tests/test_future_model_raw_source_parser.py tests/test_future_model_source_review.py tests/test_future_model_ingest_preview.py -q`
  - result: `12 passed`
- Non-mutating preview generation completed:
  - `.venv/bin/python scripts/build_future_model_source_preview.py`
  - result: preview artifacts were rewritten only by timestamp; those timestamp-only diffs were reverted after inspection.
- A one-off raw alignment audit passed with `error_count=0`:
  - audited raw sheets: `z06_standard_raw`, `z06_intextmec_raw`, `zr1_zr1x_standard_raw`, `zr1_zr1x_intextmec_raw`
  - equipment-group raw sheets present but intentionally excluded from parser output: `z06_eqgrps_raw`, `zr1_zr1x_eqgrps_raw`
  - unique parsed option spans:
    - `z06_standard_raw`: 82
    - `z06_intextmec_raw`: 252
    - `zr1_zr1x_standard_raw`: 85
    - `zr1_zr1x_intextmec_raw`: 220
  - model-scoped review row counts:
    - `z06`: 334
    - `zr1`: 305
    - `zr1x`: 305
    - total: 944

Current workbook state inspected with `openpyxl`:

- `future_model_source_review`
  - rows: 944
  - columns: 83
  - counts by model:
    - `z06`: 334
    - `zr1`: 305
    - `zr1x`: 305
  - review status counts:
    - `needs_review`: 932
    - `approved`: 12
  - active counts:
    - `False`: 932
    - `True`: 12
  - top review flags:
    - `duplicate_rpo`: 358
    - `section_unresolved`: 332
    - `missing_rpo`: 153
    - `dealer_installed_status`: 135
    - `included_in_equipment_group`: 65
    - `section_conflict`: 39
    - `price_schedule_multiple_candidates`: 17
- Target normalized sheets are still header-only:
  - `z06_options`: 0 rows
  - `z06_ovs`: 0 rows
  - `zr1_options`: 0 rows
  - `zr1_ovs`: 0 rows
  - `zr1x_options`: 0 rows
  - `zr1x_ovs`: 0 rows
- Future model metadata remains inactive/unpromoted:
  - `model_master.active=False` for `z06`, `zr1`, `zr1x`
  - `model_workbook_sources.active=False` for future-model source roles
  - `model_registry_promotion.promoted_to_runtime=False` and `active=False` for `z06`, `zr1`, `zr1x`

Root cause / need: the next migration step needs a safe, repeatable path from manually reviewed rows in `future_model_source_review` into normalized workbook-owned source sheets. That path must preserve the workbook as source of truth, refuse unresolved review rows, avoid dedupe-by-RPO shortcuts, and keep future models inactive so no live runtime behavior changes.

Change type: workbook data + scripts + tests. No runtime behavior change. No visual change. No generated `form_*` sheet edit.

Risk level: medium. Writing normalized source sheets is workbook data mutation. Live app risk stays low if model metadata and registry promotion remain inactive and `form-app/data.js` is untouched.

## Exact Files And Workbook Sheets To Change

### Create / modify scripts

Create:

- `scripts/apply_future_model_source_review.py`
  - Reads `future_model_source_review`.
  - Supports `--model-key z06|zr1|zr1x|all`.
  - Supports `--dry-run`.
  - Default non-dry-run writes only selected target `*_options` and `*_ovs` sheets.
  - Refuses workbook writes if `~$stingray_master.xlsx` exists.
  - Saves through `save_workbook_safely()`.
  - Verifies saved target sheet rows on disk with `openpyxl` before reporting success.

Modify if needed:

- `scripts/corvette_form_generator/future_model_ingest.py`
  - Add reusable constants for target option and OVS headers if not already available.
  - Add review-row loading helpers if needed.
  - Add validation/materialization helpers for approved review rows.
  - Keep raw parser behavior unchanged except for test-supported helper extraction.

### Tests

Modify / extend:

- `tests/test_future_model_source_review.py`
  - Add tests for materializing approved review rows into normalized option/OVS rows.
  - Add tests proving inactive/needs-review rows are blocked.
  - Add tests proving duplicate `approved_option_id` values are rejected.
  - Add tests proving missing `approved_rpo`, `approved_section_id`, or missing model variant statuses are rejected.
  - Add tests proving `--dry-run` style logic produces counts without mutating a workbook.

Create only if cleaner than expanding the existing file:

- `tests/test_future_model_source_population.py`

Do not modify runtime tests unless a diff unexpectedly touches runtime files.

### Workbook sheets

Write through the approved script only:

- `stingray_master.xlsx`
  - `z06_options`
  - `z06_ovs`
  - `zr1_options`
  - `zr1_ovs`
  - `zr1x_options`
  - `zr1x_ovs`

Read-only inputs:

- `future_model_source_review`
- `section_master`
- `model_variants`
- future-model rows in `model_master`
- future-model rows in `model_workbook_sources`
- future-model rows in `model_registry_promotion`

Must not change in this pass:

- `form-app/app.js`
- `form-app/data.js`
- generated `form_*` workbook sheets
- current Stingray or Grand Sport source sheets
- `model_master`
- `model_workbook_sources`
- `model_registry_promotion`
- dealer submission endpoint/payload/Turnstile code

## Source Population Contract

`future_model_source_review` remains the authoritative staging sheet. Raw source sheets are provenance only. The script may emit only rows that satisfy all approval gates below.

### Eligible review rows

A row is eligible for emission only when all conditions are true:

- `model_key` matches the selected model.
- `review_status` is exactly `approved`.
- `active` is true by the existing workbook boolean parser semantics.
- `approved_option_id` is nonblank.
- `approved_option_id` is unique within the selected model output.
- `approved_rpo` is nonblank.
- `approved_option_name` is nonblank.
- `approved_section_id` is nonblank.
- `approved_section_id` exists in `section_master`.
- `approved_display_order` is nonblank and numeric-ish.
- Every canonical variant for that model has a normalized status column populated with one of:
  - `available`
  - `standard`
  - `unavailable`
- No blocking unresolved flag remains unless an explicit approved override column is added in a later spec. For this pass, the following flags block emission even if `review_status` was accidentally set to `approved`:
  - `section_conflict`
  - `section_unresolved`
  - `missing_rpo`
  - `blank_variant_status`
  - `unknown_status`
  - `candidate_id_collision`
  - `price_type_issue`
- `duplicate_rpo` is not automatically blocking if the reviewer supplied a unique `approved_option_id`; it remains provenance/review evidence because duplicate RPO identity is expected in the raw order guide.
- `dealer_installed_status`, `included_in_equipment_group`, and `included_in_equipment_group_upgradeable` are not automatically blocking if the row is explicitly `approved` and has complete statuses; they remain provenance flags for later rule/group/pricing review.
- `price_schedule_multiple_candidates` blocks emission only when `approved_price` is nonblank. If the reviewer intentionally leaves `approved_price` blank, the option row can emit with blank price and later price-rule work can own the conditional pricing.

### Model variants

Use the canonical target variant sets from `FUTURE_MODEL_SPECS` / workbook metadata:

- `z06`:
  - `1lz_h07`
  - `2lz_h07`
  - `3lz_h07`
  - `1lz_h67`
  - `2lz_h67`
  - `3lz_h67`
- `zr1`:
  - `1lz_r07`
  - `3lz_r07`
  - `1lz_r67`
  - `3lz_r67`
- `zr1x`:
  - `1lz_s07`
  - `3lz_s07`
  - `1lz_s67`
  - `3lz_s67`

Do not infer additional variants from raw status columns. If a future model's variant set changes, update the workbook/model metadata in a separate approved spec.

### Target `*_options` mapping

For each eligible row, write one row to the model target option sheet:

| Target column | Source column |
|---|---|
| `option_id` | `approved_option_id` |
| `rpo` | `approved_rpo` |
| `price` | `approved_price` |
| `option_name` | `approved_option_name` |
| `description` | `approved_description` |
| `detail_raw` | `approved_detail_raw` |
| `section_id` | `approved_section_id` |
| `selectable` | `approved_selectable` |
| `display_order` | `approved_display_order` |
| `active` | `active` |
| `display_behavior` | `approved_display_behavior` |

Sort target option rows by numeric `approved_display_order`, then `approved_option_id`, to keep output deterministic.

### Target `*_ovs` mapping

For each eligible row and every model variant, write one OVS row:

| Target column | Source |
|---|---|
| `option_id` | `approved_option_id` |
| `variant_id` | canonical model variant id |
| `status` | `status_<variant_id>` |

Sort target OVS rows by option display order, then `variant_id` in canonical variant order.

### Dry-run behavior

`--dry-run` must not save the workbook. It should print JSON with at least:

- selected `model_key` / `all`
- eligible option counts by model
- emitted OVS counts by model
- blocked counts by reason
- target sheet names
- current target sheet row counts
- would-write target sheet row counts

Dry-run should return nonzero if validation errors would block a requested write, unless the errors are only expected in rows that are inactive/needs-review and therefore not selected for emission.

### Non-dry-run behavior

For each selected model:

1. Load workbook with `data_only=False`, `read_only=False`.
2. Capture `loaded_mtime_ns` before loading.
3. Validate no Excel lock file exists.
4. Read and validate review rows.
5. Materialize target option/OVS rows.
6. Replace only that model's target option and OVS sheets with headers + emitted rows.
7. Save through `save_workbook_safely()`.
8. Reopen the workbook read-only and verify:
   - target option sheet exists with expected headers and row count
   - target OVS sheet exists with expected headers and row count
   - no other selected/non-selected future source sheets changed unexpectedly
   - `model_master`, `model_workbook_sources`, and `model_registry_promotion` future rows remain inactive/unpromoted

Current expected output if run before additional manual review decisions:

- Only the 12 currently approved/active rows should emit.
- The exact by-model split must be reported by dry-run before any write.
- It is acceptable for this pass to produce partial future source sheets because future model metadata remains inactive and no runtime promotion occurs.
- If the by-model approved counts are surprising, stop before non-dry-run and inspect `future_model_source_review` rather than broadening eligibility in code.

## Constraints

- Workbook source of truth remains strict.
- No new dependencies.
- No runtime promotion.
- No `form-app/app.js` changes.
- No `form-app/data.js` changes.
- No dealer submission endpoint, payload, or Turnstile changes.
- No generated `form_*` sheet edits.
- No hardcoded model-specific runtime behavior.
- Do not parse raw sheets again as the source for population; use `future_model_source_review` so manual review decisions are respected.
- Do not physically unmerge raw sheets.
- Do not dedupe rows by RPO alone.
- Do not activate `model_master`, `model_workbook_sources`, or `model_registry_promotion` rows.
- Do not write `needs_review`, inactive, unresolved, or missing-RPO rows to active normalized source sheets.
- Check for `~$stingray_master.xlsx` before workbook writes.
- Save workbook writes only through `save_workbook_safely()`.
- Verify saved workbook rows on disk with `openpyxl` before claiming the workbook change landed.

## Risks

- The current review map is mostly unresolved: 932 of 944 rows are `needs_review`. This script will initially emit only a small subset unless manual review decisions are added.
- Duplicate RPO rows are common. A simplistic uniqueness rule on RPO would incorrectly collapse distinct option identities. Uniqueness must be on `approved_option_id`.
- Rows with equipment-group or dealer-installed flags may need later rules or price handling. This pass must preserve them as reviewed source rows only when explicitly approved, not invent behavior.
- Blank `approved_price` can mean either no option-level price or deferred price-rule work. Do not convert blank to zero.
- Future source sheets can be populated while future model metadata stays inactive; this is safe for live runtime but may look incomplete if someone inspects target sheets without understanding the approval counts.
- If the script accidentally toggles future model metadata or rewrites `form-app/data.js`, it would affect runtime promotion boundaries. Stop immediately if those files/sheets show diffs.

## Non-Goals

- Do not complete manual review of all 944 rows in this implementation pass.
- Do not resolve duplicate-RPO identity in code.
- Do not add compatibility/rule/exclusive-group copying.
- Do not copy Grand Sport rules or price values.
- Do not build price rules from `price_sched_raw`.
- Do not wire LZ interiors.
- Do not generalize `generate_grand_sport_form.py`.
- Do not generate draft form-data for Z06/ZR1/ZR1X.
- Do not promote Z06, ZR1, or ZR1X into runtime.
- Do not change current live Stingray or Grand Sport runtime behavior.

## Validation Plan

1. Confirm clean branch and no Excel lock file:

   ```sh
   git status --short --branch
   test ! -e './~$stingray_master.xlsx'
   ```

2. Run existing safety gates before editing:

   ```sh
   .venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
   .venv/bin/python -m pytest tests/test_future_model_raw_source_parser.py tests/test_future_model_source_review.py tests/test_future_model_ingest_preview.py -q
   ```

3. Write failing tests for source population:

   ```sh
   .venv/bin/python -m pytest tests/test_future_model_source_population.py -q
   ```

   If extending the existing file instead:

   ```sh
   .venv/bin/python -m pytest tests/test_future_model_source_review.py -q
   ```

   Expected before implementation: tests fail because materialization/apply helpers do not exist.

4. Implement materialization helpers and the apply script.

5. Run targeted tests:

   ```sh
   .venv/bin/python -m pytest tests/test_future_model_raw_source_parser.py tests/test_future_model_source_review.py tests/test_future_model_ingest_preview.py tests/test_future_model_source_population.py -q
   ```

   Omit `tests/test_future_model_source_population.py` if its coverage was added to `tests/test_future_model_source_review.py`.

6. Run dry-run for all models:

   ```sh
   .venv/bin/python scripts/apply_future_model_source_review.py --model-key all --dry-run
   ```

   Expected:
   - no workbook diff
   - JSON reports approved/eligible counts by model
   - JSON reports blocked counts by reason
   - total eligible options matches the current approved/active review count unless manual review rows changed

7. Confirm dry-run did not mutate workbook:

   ```sh
   git diff -- stingray_master.xlsx
   ```

8. If dry-run counts are acceptable, run non-dry-run:

   ```sh
   .venv/bin/python scripts/apply_future_model_source_review.py --model-key all
   ```

9. Verify saved workbook on disk with script output and independent `openpyxl` inspection:

   - `z06_options` row count equals emitted Z06 eligible option count.
   - `z06_ovs` row count equals emitted Z06 eligible option count × 6.
   - `zr1_options` row count equals emitted ZR1 eligible option count.
   - `zr1_ovs` row count equals emitted ZR1 eligible option count × 4.
   - `zr1x_options` row count equals emitted ZR1X eligible option count.
   - `zr1x_ovs` row count equals emitted ZR1X eligible option count × 4.
   - all target sheet headers match the current header-only scaffolds.
   - future model metadata remains inactive/unpromoted.

10. Run workbook schema validation:

    ```sh
    .venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
    ```

11. Run source/review/parser tests again:

    ```sh
    .venv/bin/python -m pytest tests/test_future_model_raw_source_parser.py tests/test_future_model_source_review.py tests/test_future_model_ingest_preview.py tests/test_future_model_source_population.py -q
    ```

12. Review diffs:

    ```sh
    git diff --stat
    git diff -- scripts/corvette_form_generator/future_model_ingest.py scripts/apply_future_model_source_review.py tests spec-review/phase7-review-map-to-source-sheets-spec.md
    git diff -- form-app/app.js form-app/data.js
    ```

    Expected runtime diff: none.

13. Do not run Stingray/Grand Sport runtime gates unless runtime files unexpectedly changed. If they changed, stop and report before proceeding.

## Approval Gate

Approve this spec before implementation.

Recommended implementation boundary after approval:

1. Add tests for review-row-to-source materialization.
2. Add the apply script with dry-run first.
3. Run dry-run and inspect counts.
4. Only then write the normalized future source sheets.
5. Keep future models inactive and unpromoted.
