# Z Runtime Readiness Spec 2 — Option/OVS Closure Pass

## Diagnosis

The Z06/ZR1/ZR1X option staging is not closed enough to build runtime rules on top of it. The workbook has unresolved review rows and the normalized target option/OVS sheets include option IDs that do not correspond to active approved review rows.

Evidence inspected on branch `z06-zr1-migration`:

- `git status --short --branch`
  - branch: `z06-zr1-migration`
  - current working tree has only untracked repo clutter/spec/backups/DS_Store entries at inspection time; no tracked source modifications were reported in this shell state.
  - Excel lock file `~$stingray_master.xlsx`: absent.
- Workbook sheet `future_model_option_review`:
  - total rows: `944`
  - Z06 rows: `334`
    - `approved`: `164`
    - `needs_section_review`: `113`
    - `deferred`: `57`
    - `active=True`: `164`
    - `active=False`: `170`
  - ZR1 rows: `305`
    - `approved`: `141`
    - `needs_section_review`: `104`
    - `deferred`: `60`
    - `active=True`: `141`
    - `active=False`: `164`
  - ZR1X rows: `305`
    - `approved`: `141`
    - `needs_section_review`: `104`
    - `deferred`: `60`
    - `active=True`: `141`
    - `active=False`: `164`
- Normalized target option/OVS sheets:
  - `z06_options`: `239` rows; active approved review option IDs: `164`; beyond active approved IDs: `75`; approved IDs missing from option sheet: `0`.
  - `zr1_options`: `201` rows; active approved review option IDs: `141`; beyond active approved IDs: `60`; approved IDs missing from option sheet: `0`.
  - `zr1x_options`: `202` rows; active approved review option IDs: `141`; beyond active approved IDs: `61`; approved IDs missing from option sheet: `0`.
  - OVS shape is internally complete relative to current option sheets:
    - `z06_ovs`: `1434` rows, 239 unique option IDs, no OVS IDs missing from `z06_options`, no options without OVS.
    - `zr1_ovs`: `804` rows, 201 unique option IDs, no OVS IDs missing from `zr1_options`, no options without OVS.
    - `zr1x_ovs`: `808` rows, 202 unique option IDs, no OVS IDs missing from `zr1x_options`, no options without OVS.
- All option IDs beyond active approved review IDs are traceable back to `future_model_source_review`/`future_model_option_review`, but they are currently `needs_section_review` and `active=False` review rows that nevertheless have a suggested section.
  - Z06: 75 beyond rows map to inactive `needs_section_review` rows with sections.
  - ZR1: 60 beyond rows map to inactive `needs_section_review` rows with sections.
  - ZR1X: 61 beyond rows map to inactive `needs_section_review` rows with sections.
- `scripts/apply_future_model_option_review.py --dry-run --model-key all` currently reports no errors, but it plans from any row with `suggested_section_id`; it does not require `review_status=approved` or `active=True` before emitting to target option/OVS sheets.
  - Current dry-run would keep Z06 at 239 options / 1434 OVS rows.
  - Current dry-run would increase ZR1 from 201 to 203 options and OVS from 804 to 812 by adding inactive `needs_section_review` rows `opt_feh_002` and `opt_fez_001`.
  - Current dry-run would increase ZR1X from 202 to 204 options and OVS from 808 to 816 by adding inactive `needs_section_review` rows `opt_fe8_002` and `opt_fej_001`.
- Code-level issue in `scripts/apply_future_model_option_review.py`:
  - `build_future_option_population_plan()` uses `selected_rows = [row for row in model_rows if clean(row.get("suggested_section_id"))]` for duplicate detection and emits every row with `suggested_section_id`.
  - `_validation_errors_for_selected_row()` validates `suggested_section_id` only.
  - `_option_row_from_review()` writes `section_id` from `suggested_section_id` only.
  - It ignores `review_status`, `active`, `final_section_id`, and `final_selectable` for emission decisions.

Root cause:

The current future option population path treats “has a suggested section” as eligible for normalized source emission. That made inactive `needs_section_review` rows leak into `z06_options`, `zr1_options`, and `zr1x_options`. The result is unstable option IDs: some rows are present in normalized target sheets even though the review sheet says they are not active/approved. Building rules now would anchor rule IDs and targets to an option universe that is partly unresolved.

Change type: mixed workbook/data + generator/test closure pass. It should not touch runtime behavior or dealer submission.

Risk level: medium-high because this pass may remove currently staged option/OVS rows from future-model source sheets and may require many human section/active/deferred decisions before Z runtime promotion.

## Decision / Ownership

- Source-of-truth decisions belong in `future_model_option_review` and, where needed, `future_model_source_review`.
- `z06_options`, `z06_ovs`, `zr1_options`, `zr1_ovs`, `zr1x_options`, `zr1x_ovs` are normalized target source sheets derived from the review decisions; they should not contain rows whose provenance is unresolved or inactive.
- Generator/apply logic should enforce the review contract generically:
  - emit only rows that are explicitly `active=True` and `review_status=approved` unless a separately approved status is introduced.
  - use final override fields when present, including `final_section_id`, `final_selectable`, `final_display_order`, and `final_display_behavior`.
  - report unresolved/deferred rows in dry-run output instead of silently materializing them.

## Exact Files / Sheets to Change

Expected code/test files:

- `scripts/apply_future_model_option_review.py`
  - Add explicit eligibility predicate for option/OVS emission:
    - eligible if `active=True` and `review_status=approved` and a resolved section is present.
    - blocked/deferred otherwise, counted by status/reason.
  - Use resolved/final fields consistently:
    - `option_id`: `final_option_id` then `suggested_option_id`.
    - `section_id`: `final_section_id` then `suggested_section_id`.
    - `selectable`: `final_selectable` when present, otherwise based on `orderable_rpo`.
    - `display_order`: `final_display_order` then `suggested_display_order`.
    - `display_behavior`: `final_display_behavior`.
  - Add dry-run closure reporting:
    - unresolved counts by `review_status`, active flag, missing section, missing statuses, duplicate option ID.
    - normalized target rows beyond active approved review rows.
    - planned rows added/removed by model.
  - Preserve explicit `--dry-run` and safe-save behavior.

- `tests/test_future_model_option_population.py`
  - Add tests proving inactive `needs_section_review` rows with sections are not emitted.
  - Add tests proving `final_section_id` and `final_selectable` override suggested/default values.
  - Add tests proving dry-run reports blocked `needs_section_review`/`deferred` rows distinctly.

- Potentially `scripts/create_future_model_option_review.py`
  - Only if inspection shows it regenerates/overwrites human final fields incorrectly. Current inspection shows it preserves `HUMAN_DECISION_FIELDS`; no change expected unless implementation reveals drift.

Workbook sheets likely changed after code guard is approved:

- `stingray_master.xlsx`
  - `future_model_option_review`
    - close or explicitly defer all unresolved rows before runtime:
      - Z06: 113 `needs_section_review`, 57 `deferred`
      - ZR1: 104 `needs_section_review`, 60 `deferred`
      - ZR1X: 104 `needs_section_review`, 60 `deferred`
    - add explicit `notes` / final decisions for derived/interior/customer-option rows so their provenance is understandable.
  - Derived normalized target source sheets regenerated from approved review rows only:
    - `z06_options`, `z06_ovs`
    - `zr1_options`, `zr1_ovs`
    - `zr1x_options`, `zr1x_ovs`

No generated runtime artifacts should be changed in this pass:

- Do not edit/regenerate `form-output/stingray-form-data.json`, `form-output/stingray-form-data.csv`, or `form-app/data.js` unless explicitly scoped later.
- Do not edit generated `form_*` workbook sheets.

## Proposed Implementation Phases

### Phase 2A — Closure report / guard first

1. Add eligibility/reporting changes to `scripts/apply_future_model_option_review.py`.
2. Add tests for the new eligibility contract.
3. Run dry-run against workbook.
4. Produce a closure report listing:
   - approved active rows that would emit.
   - inactive or unresolved rows currently present in normalized target sheets.
   - rows that need human decisions, grouped by model, section, RPO, and candidate copy source.
   - rows with no RPO / standard/interior/customer-option characteristics.
   - exact option IDs that would be removed from each target option sheet if regenerated under the approved-only contract.

This phase may be implemented before touching the workbook because it exposes the true delta and prevents more unresolved rows from being emitted.

### Phase 2B — Workbook decision closure

1. Review the Phase 2A closure report.
2. For each unresolved row, decide one of:
   - approve for source emission with final section/status/selectable/display metadata.
   - defer intentionally with a reason and keep inactive.
   - mark as derived/interior/customer-option provenance with explicit note if it is not a direct active review row but should remain in a normalized source sheet.
3. Use workbook-safe write path for any workbook edits.
4. Reopen workbook and verify decisions on disk.

If human product/UX decisions are required for many rows, stop with the closure report and do not mass-approve by inference.

### Phase 2C — Regenerate normalized option/OVS target sheets

1. Run `scripts/apply_future_model_option_review.py --dry-run --model-key all`.
2. Confirm the plan emits only approved active rows plus any explicitly approved provenance exceptions.
3. Run `scripts/apply_future_model_option_review.py --model-key all` only after the dry-run delta is reviewed.
4. Verify:
   - no target option IDs beyond the active approved/provenance-exception set.
   - no active approved IDs missing from target option sheets.
   - every target option has expected OVS rows for its model variants.
   - OVS IDs all resolve to target option sheets.

## Constraints Repeated Back

- Spec-first: no edits until this spec is approved.
- Workbook source-of-truth rules remain strict.
- Do not solve unresolved business decisions by hiding rows in Python/JS.
- Do not add model/RPO-specific runtime hardcodes.
- Do not promote Z06/ZR1/ZR1X to runtime in this pass.
- Do not alter live Stingray or Grand Sport behavior.
- Do not change dealer submission endpoint, payload, or Turnstile behavior.
- Do not hand-edit generated `form_*` sheets or runtime app data.
- Use `.venv/bin/python` for Python commands.
- If writing `stingray_master.xlsx`, require no Excel lock, use `save_workbook_safely()`, and verify saved cells on disk.
- Preserve visual/runtime behavior.
- No new dependencies.
- No broad refactor.

## Non-goals

- Do not build rules on top of current unstable option IDs.
- Do not complete rules, interiors, prices, exclusive groups, or runtime registry promotion in this pass.
- Do not decide product truth for rows without evidence; classify them and stop if human review is needed.
- Do not remove internal review provenance from review sheets.
- Do not regenerate `form-app/data.js`.

## Risks

- If the apply script is corrected to approved-only emission before workbook decisions are complete, the target option sheets will shrink substantially:
  - at least 75 Z06 rows, 60 ZR1 rows, and 61 ZR1X rows are currently beyond active approved review IDs.
- Some beyond rows are likely standard equipment, derived interior/package/customer rows, or valid future options that need an explicit source/provenance decision rather than deletion.
- Current dry-run would add four more inactive unresolved suspension rows for ZR1/ZR1X; this confirms the generator guard must come before another write.
- `final_section_id` / `final_selectable` are currently ignored by the apply script; correcting this could change target rows if those final fields diverge from suggested fields.

## Validation Plan

Code/test guard phase:

```sh
.venv/bin/python -m pytest tests/test_future_model_option_population.py -q
.venv/bin/python scripts/apply_future_model_option_review.py --dry-run --model-key all
```

Workbook package/schema validation after any workbook write:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Future-model staging gates after option/OVS regeneration:

```sh
.venv/bin/python -m pytest \
  tests/test_future_model_source_review.py \
  tests/test_future_model_source_population.py \
  tests/test_future_model_option_review.py \
  tests/test_future_model_option_population.py \
  tests/test_future_model_compatibility_rebase.py \
  tests/test_future_model_lz_interiors.py \
  tests/test_future_model_option_pricing.py \
  -q
```

If normalized option/OVS sheets are written, add a scoped verification script that prints for each model:

- target option row count
- active approved/provenance-exception review ID count
- target IDs beyond allowed set; expected `0`
- allowed IDs missing from target option sheet; expected `0`
- OVS option IDs without target option; expected `0`
- target options without OVS rows; expected `0`
- blocked unresolved counts by status/reason

No Node runtime tests are required unless this pass unexpectedly changes `form-app/data.js` or runtime code.

## Approval Gate

Approve this spec to implement Phase 2A first: add the apply-script eligibility/report guard and tests, then produce the closure report/dry-run delta. Workbook decision edits and target option/OVS writes should follow only after the report makes the unresolved row classes explicit.
