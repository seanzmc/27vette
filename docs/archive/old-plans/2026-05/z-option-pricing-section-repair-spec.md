# Z Option Pricing + Section Repair Spec

## Diagnosis

Change type: workbook/data-only with a small repeatable migration helper recommended. No runtime behavior, dealer submission, visual styling, or generated form-app output should change in this pass.

Risk level: medium-high, because the affected sheets are workbook source sheets for future Z models and the current workbook has several overlapping data regressions: pricing review noise, section placement drift, default-selected rows made non-selectable, and missing display_order values.

Evidence inspected:

- Branch/status:
  - branch: `z06-zr1-migration`
  - status has unrelated/untracked `.DS_Store` files and `backups/`; do not stage or touch these.
- Workbook lock:
  - `/Users/seandm/Projects/27vette/~$stingray_master.xlsx` does not currently exist.
- User CSV:
  - `z-option-canonical-pricing-matrix.csv`
  - headers: `model_key`, `option_sheet`, `option_row`, `option_id`, `rpo`, `option_name`, `current_price`, `matched_future_model_source_review_rows`, `candidate_price`, `parsed_candidate_prices`, `price_candidate_rows`, `price_candidate_summary`, `approved_price`, `classification`, `recommended_workbook_action`, `notes`
  - 646 rows total.
  - 333 blank `approved_price` rows, 313 filled `approved_price` rows.
  - Because the CSV has no `section_id`, it must be joined to the workbook by `option_sheet` + `option_row` before applying decisions.
- Workbook sheets inspected:
  - `z06_options`
  - `zr1_options`
  - `zr1x_options`
  - `section_master` indirectly via pricing script behavior.
- Current pricing helper inspected:
  - `scripts/apply_future_model_option_prices.py`
  - It already blanks display-only/standard sections by `section_master.selection_mode == display_only`, but it is generated from `price_sched_raw`, not from the manual `approved_price` CSV.
- Archived display-order evidence inspected:
  - `archive-2026-05-29/archived/referenceSheets/stingray_master - z06_options.csv`
  - `archive-2026-05-29/archived/referenceSheets/stingray_master - zr1_options.csv`
  - `archive-2026-05-29/archived/referenceSheets/stingray_master - zr1x_options.csv`

Root causes / observed problems:

1. Standard-equipment sections leaked into the pricing review CSV.
   - Treat these section IDs as excluded from price review/application:
     - `sec_stan_001`
     - `sec_1lte_001`
     - `sec_2lte_001`
     - `sec_3lte_001`
     - `sec_incl_001`
     - `sec_safe_001`
     - `sec_stan_002`
     - `sec_tech_001`
   - Joined CSV-to-workbook counts in these sections:
     - 258 total rows
     - `sec_stan_001`: 114
     - `sec_2lte_001`: 57
     - `sec_incl_001`: 18
     - `sec_1lte_001`: 12
     - `sec_safe_001`: 29
     - `sec_tech_001`: 19
     - `sec_3lte_001`: 6
     - `sec_stan_002`: 3
   - By sheet:
     - `z06_options`: 84
     - `zr1_options`: 86
     - `zr1x_options`: 88
   - 194 of those standard-section CSV rows have filled `approved_price`; those should be ignored for workbook price application.

2. Manual approved prices exist for non-standard rows and should drive this pass.
   - Non-standard joined CSV rows: 388
   - Non-standard `approved_price` buckets:
     - numeric: 19
     - `no price` sentinel: 100
     - blank: 269
   - Numeric approved rows by model:
     - `z06`: 6
     - `zr1`: 3
     - `zr1x`: 10
   - `no price` approved rows by model:
     - `z06`: 48
     - `zr1`: 44
     - `zr1x`: 8
   - There are no non-standard `pending` approved rows.
   - Standard-section `pending` rows exist and should be ignored in this pass because those sections are excluded from price review.

3. Required section moves are visible in current workbook state and conflict with user direction.
   - `WUB` is currently in `sec_exha_001` in all three sheets; it must move to `sec_stan_001` for all three models.
   - `UV6` is currently in `sec_2lte_001` in all three sheets; it must move to `sec_1lte_001` for all three models.
   - Current rows:
     - `z06_options` row 57: `WUB`, `sec_exha_001`, selectable `False`, display_order `20`
     - `zr1_options` row 54: `WUB`, `sec_exha_001`, selectable `False`, display_order `20`
     - `zr1x_options` row 46: `WUB`, `sec_exha_001`, selectable `False`, display_order `20`
     - `z06_options` row 23: `UV6`, `sec_2lte_001`, selectable `False`, display_order `10`
     - `zr1_options` row 6: `UV6`, `sec_2lte_001`, selectable `False`, display_order `10`
     - `zr1x_options` row 25: `UV6`, `sec_2lte_001`, selectable `False`, display_order `10`

4. Default-selected Z rows are currently incorrectly non-selectable.
   - These rows should remain `display_behavior=default_selected` but have `selectable=True`, matching the intended behavior where a user can return to the default after choosing a peer.
   - Current bad rows:
     - `z06_options`: 4 rows
       - row 59 `EFR`, `sec_exte_001`, selectable `False`, display_order `10`
       - row 116 `T0E`, `sec_perf_aero_001`, selectable `False`, display_order `10`
       - row 119 `J56`, `sec_perf_brake_001`, selectable `False`, display_order `10`
       - row 153 `719`, `sec_seat_001`, selectable `False`, display_order `10`
     - `zr1_options`: 4 rows
       - row 29 `J6D`, `sec_cali_001`, selectable `False`, display_order `15`
       - row 56 `EFR`, `sec_exte_001`, selectable `False`, display_order `10`
       - row 103 `T0E`, `sec_perf_aero_001`, selectable `False`, display_order `10`
       - row 120 `719`, `sec_seat_001`, selectable `False`, display_order `10`
     - `zr1x_options`: 4 rows
       - row 7 `719`, `sec_seat_001`, selectable `False`, display_order `10`
       - row 15 `EFR`, `sec_exte_001`, selectable `False`, display_order `10`
       - row 23 `T0E`, `sec_perf_aero_001`, selectable `False`, display_order `10`
       - row 30 `J6D`, `sec_cali_001`, selectable `False`, display_order `15`

5. Display orders are missing on many active source rows.
   - Current active missing display_order counts:
     - `z06_options`: 73
     - `zr1_options`: 61
     - `zr1x_options`: 62
   - Archive restoration feasibility by exact `(option_id, rpo, section_id)` key:
     - `z06_options`: 70 restorable from archive, 3 archived as blank (`RXI`, `RYQ`, `V8X`)
     - `zr1_options`: 26 restorable from archive, 33 archived as blank, 2 no archive key (`FEH`, `FEZ`)
     - `zr1x_options`: 29 restorable from archive, 31 archived as blank, 2 no archive key (`FE8`, `FEJ`)
   - This pass should not invent a large new ordering system. Restore exact archived orders where available. For still-missing active rows, assign deterministic per-section orders only if approved as part of this pass; otherwise report them as residual missing-order rows.

## Exact files / sheets / artifacts to change

Primary source workbook:

- `stingray_master.xlsx`
  - `z06_options`
  - `zr1_options`
  - `zr1x_options`

Recommended repeatable helper, if approved:

- Add `scripts/apply_z_option_sheet_repairs.py` or equivalent migration helper with dry-run default and explicit `--write`.

Inputs to read but not modify:

- `z-option-canonical-pricing-matrix.csv`
- `archive-2026-05-29/archived/referenceSheets/stingray_master - z06_options.csv`
- `archive-2026-05-29/archived/referenceSheets/stingray_master - zr1_options.csv`
- `archive-2026-05-29/archived/referenceSheets/stingray_master - zr1x_options.csv`

Do not hand-edit generated sheets:

- Do not edit `form_*` sheets directly.
- Do not edit `form-output/` or `form-app/data.js` in this pass unless a later approved runtime-promotion/generation pass explicitly requires it.

## Proposed smallest safe pass

1. Create/execute a dry-run-first migration helper that:
   - Loads `stingray_master.xlsx` with openpyxl through the project venv.
   - Refuses to write if `~$stingray_master.xlsx` exists.
   - Joins `z-option-canonical-pricing-matrix.csv` rows to workbook rows by `option_sheet` + `option_row`.
   - Applies `approved_price` only when the joined workbook row is not in one of the excluded standard-equipment sections.
   - Interprets approved numeric values as workbook price numbers.
   - Interprets `approved_price` values like `no price`, blank, `n/a`, `na`, or `none` as blank workbook price.
   - Ignores standard-equipment sections entirely for pricing, even if the CSV has numeric or `no price` approved values.
   - Reports ignored standard-section rows separately so the review-noise problem is visible.

2. Move sections in workbook source sheets:
   - `WUB` -> `sec_stan_001` in `z06_options`, `zr1_options`, `zr1x_options`.
   - `UV6` -> `sec_1lte_001` in `z06_options`, `zr1_options`, `zr1x_options`.
   - Preserve option IDs, names, descriptions, detail text, active flags, OVS rows, and prices unless the price rule above applies.

3. Fix default-selected selectable flags:
   - For every row in `z06_options`, `zr1_options`, and `zr1x_options` where `display_behavior == default_selected`, set `selectable=True`.
   - Do not remove `display_behavior=default_selected`.
   - Do not add runtime hardcodes.

4. Restore display_order values:
   - First, restore exact archived display_order values when `(option_id, rpo, section_id)` matches the archive and archive display_order is nonblank.
   - For rows still missing display_order, either:
     - Option A: leave blank and report exact residual rows for user review, or
     - Option B: assign deterministic section-local order values after the current maximum display_order in each section, preserving current row order.
   - Recommended: Option B only for active selectable/customer-facing sections; standard-equipment text rows with blank RPOs may be better reported rather than invented if their UI order is not meaningful yet. This needs approval.

5. Save safely:
   - Use `save_workbook_safely()` from `scripts/corvette_form_generator/workbook.py`.
   - Reopen the saved workbook and verify all expected cell values on disk.

## Constraints repeated back

- Visual preservation: no CSS/HTML/runtime UI changes in this pass.
- No refactor: do not restructure generator/runtime code; only add a narrow migration helper if approved for repeatability.
- No new dependencies.
- Workbook source-of-truth: fix `z06_options`, `zr1_options`, and `zr1x_options` source rows; do not suppress bad data in JavaScript or generated sheets.
- No generated sheet hand-edits.
- Dealer submission boundaries: do not touch dealer endpoint, payload shape, Turnstile behavior, or live app submission logic.
- Do not expand hardcoded model/RPO-specific runtime behavior.
- Do not stage `.DS_Store`, `backups/`, temp workbook files, or unrelated generated output.
- Do not claim workbook changes landed until the workbook is reopened and verified on disk.

## Risks and non-goals

Risks:

- `option_row` in the CSV is row-number based. Before writing, the helper must verify the row still matches the CSV `option_id`/`rpo` where available; otherwise it should stop rather than write the wrong row.
- Standard-equipment rows in the CSV include filled `approved_price` values, including some numeric values; these should be ignored, not written.
- `no price` is review notation, not a workbook price string. It should become a blank price cell unless the user explicitly wants literal text stored.
- Display-order restoration is only partly covered by archive evidence for ZR1/ZR1X. Remaining blanks need either deterministic assignment or a report-only follow-up.
- WUB/UV6 section moves may change which rows are considered standard/display-only in later pricing passes; this is intended by user direction but should be called out in the dry-run report.

Non-goals:

- Do not model PDB/PDD/PDF conditional package pricing in this pass.
- Do not promote Z06/ZR1/ZR1X to runtime.
- Do not change `price_rules`, compatibility rules, exclusive groups, interiors, images, or runtime behavior.
- Do not clean every section-placement issue beyond WUB and UV6 unless user supplies the remaining moves and approves them.
- Do not regenerate app data unless explicitly approved as a separate pass.

## Validation plan

Before write:

```sh
cd /Users/seandm/Projects/27vette
.venv/bin/python scripts/apply_z_option_sheet_repairs.py --dry-run --csv z-option-canonical-pricing-matrix.csv
```

Expected dry-run report must include:

- pricing updates to non-standard rows only
- ignored standard-section CSV row count: 258
- section moves: 6 total (`WUB` and `UV6` across 3 sheets)
- default-selected selectable fixes: 12 total
- display_order restore/update counts by sheet
- residual unresolved rows, if any

Write after approval:

```sh
cd /Users/seandm/Projects/27vette
.venv/bin/python scripts/apply_z_option_sheet_repairs.py --write --csv z-option-canonical-pricing-matrix.csv
```

Workbook/package verification:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
```

On-disk verification must check:

- `WUB` is in `sec_stan_001` on all three Z option sheets.
- `UV6` is in `sec_1lte_001` on all three Z option sheets.
- all `display_behavior=default_selected` rows on the three sheets have `selectable=True`.
- no excluded standard-equipment section rows had prices written from the CSV.
- non-standard numeric/no-price `approved_price` decisions were applied as intended.
- display_order missing counts are reduced as approved and residuals are reported.

Optional targeted dry-run after write:

```sh
.venv/bin/python scripts/apply_future_model_option_prices.py --dry-run --include-details
```

Do not run runtime tests or generators for this workbook-source repair unless the user expands scope to generated artifacts/runtime promotion.

## Approval needed

Please approve one display_order policy before implementation:

- Policy A: restore only exact archive-backed display_order values and report residual blanks.
- Policy B: restore archive-backed values, then assign deterministic section-local display_order values for remaining active rows.

Recommended implementation policy: B for active non-standard/customer-facing option rows, report residual standard-equipment blank-RPO rows separately.
