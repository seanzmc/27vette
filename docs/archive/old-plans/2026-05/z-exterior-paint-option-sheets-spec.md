# Z Exterior Paint Option-Sheet Canonicalization Spec

## Diagnosis

Change type: workbook/data-only source canonicalization with a narrow migration helper recommended. No runtime behavior, generated app data, dealer submission behavior, CSS/HTML, or runtime promotion should change in this pass.

Risk level: medium. The data decision is simple because the user confirmed paint colors do not differ by model in name, description, RPO, price, or compatibility. The operational risk is that the Z option sheets and OVS sheets are workbook source sheets, and the current review/apply path can rewrite option sheets without preserving prices.

User-provided product decision:

- Exterior paint colors are identical across Stingray, Grand Sport, Z06, ZR1, and ZR1X.
- Names, descriptions, RPOs, pricing, and compatibility are the same across all models.

Evidence inspected:

- Branch/status:
  - branch: `z06-zr1-migration`
  - current tracked workbook changes already exist from the prior Z pricing/section repair pass: `stingray_master.xlsx` modified.
  - untracked helper/spec artifacts from prior work exist, plus unrelated `.DS_Store`/`backups/` clutter.
- Excel lock:
  - `/Users/seandm/Projects/27vette/~$stingray_master.xlsx` is absent at spec time.
- Current canonical paint section:
  - `section_master` row 29: `sec_pain_001`, section name `Paint`, `selection_mode=single_select_req`, `display_order=10`.
- Current live-model paint rows:
  - `stingray_options`: 10 rows in `sec_pain_001`.
  - `grandSport_options`: 10 rows in `sec_pain_001`.
  - Both use the same option IDs and RPOs.
- Current Z paint rows:
  - `z06_options`: 0 rows in `sec_pain_001`.
  - `zr1_options`: 0 rows in `sec_pain_001`.
  - `zr1x_options`: 0 rows in `sec_pain_001`.
- Current OVS paint rows:
  - `stingray_ovs`: 60 paint OVS rows = 10 paint options x 6 variants.
  - `grandSport_ovs`: 60 paint OVS rows = 10 paint options x 6 variants.
  - `z06_ovs`: 0 paint OVS rows.
  - `zr1_ovs`: 0 paint OVS rows.
  - `zr1x_ovs`: 0 paint OVS rows.
- Current Z variants:
  - Z06 variants: `1lz_h07`, `2lz_h07`, `3lz_h07`, `1lz_h67`, `2lz_h67`, `3lz_h67`.
  - ZR1 variants: `1lz_r07`, `3lz_r07`, `1lz_r67`, `3lz_r67`.
  - ZR1X variants: `1lz_s07`, `3lz_s07`, `1lz_s67`, `3lz_s67`.
- Current review/provenance sheets:
  - `future_model_source_review` headers include approved fields and per-Z variant statuses.
  - `future_model_option_review` headers include final fields and review status, but no price field.
- Current future apply path inspected:
  - `scripts/apply_future_model_option_review.py`
  - It materializes `*_options`/`*_ovs` from `future_model_option_review` rows.
  - `_option_row_from_review()` currently writes `price: ""` for every emitted option row.
  - Therefore this pass must not run that writer to regenerate Z option sheets unless the writer is separately extended to preserve/apply prices. Running it now would risk wiping direct Z option prices already repaired in the prior pass.

Canonical exterior paint rows to add to each Z option sheet:

| option_id | rpo | price | option_name | description | section_id | selectable | display_order | active | display_behavior |
|---|---|---:|---|---|---|---|---:|---|---|
| `opt_g8g_001` | `G8G` | 0 | Arctic White | Touch-Up Paint Number WA-9567 | `sec_pain_001` | True | 10 | True | blank |
| `opt_gba_001` | `GBA` | 0 | Black | Touch-Up Paint Number WA-8555 | `sec_pain_001` | True | 20 | True | blank |
| `opt_gka_001` | `GKA` | 0 | Blade Silver Metallic | Touch-Up Paint Number WA-240K | `sec_pain_001` | True | 30 | True | blank |
| `opt_gbk_001` | `GBK` | 995 | Competition Yellow Tintcoat Metallic | Touch-Up Paint Number WA-233K | `sec_pain_001` | True | 40 | True | blank |
| `opt_gtr_001` | `GTR` | 500 | Admiral Blue Metallic | New for 2027. Touch-Up Paint Number WA-705U. | `sec_pain_001` | True | 50 | True | blank |
| `opt_gec_001` | `GEC` | 0 | Pitch Gray Metallic | New for 2027. Touch-Up Paint Number WA-243F. | `sec_pain_001` | True | 60 | True | blank |
| `opt_gph_001` | `GPH` | 995 | Red Mist Metallic Tintcoat | Touch-Up Paint Number WA-245F | `sec_pain_001` | True | 70 | True | blank |
| `opt_g4z_001` | `G4Z` | 500 | Roswell Green Metallic | Touch-Up Paint Number WA-247L | `sec_pain_001` | True | 80 | True | blank |
| `opt_g26_001` | `G26` | 995 | Sebring Orange Tintcoat | Touch-Up Paint Number WA-418C | `sec_pain_001` | True | 90 | True | blank |
| `opt_gkz_001` | `GKZ` | 0 | Torch Red | Touch-Up Paint Number WA-9075 | `sec_pain_001` | True | 100 | True | blank |

Display-order decision:

- Use the Grand Sport style spacing (`10`, `20`, ..., `100`) rather than Stingray's `1`..`10`, because recent Z sheet repairs also use section-local tens and it leaves room for future insertions.
- This does not change the visible order relative to Stingray/Grand Sport.

## Decision / Ownership

Decision: workbook source data.

The paint rows belong in:

- `z06_options`, `zr1_options`, `zr1x_options`
- `z06_ovs`, `zr1_ovs`, `zr1x_ovs`

For provenance and future-review alignment, add matching approved rows to:

- `future_model_source_review`
- `future_model_option_review`

Important boundary:

- Do not run `scripts/apply_future_model_option_review.py` in write mode during this pass, because it currently emits blank option prices.
- If a future pass wants option-review-driven regeneration to be authoritative, it should first extend the review/apply path to carry price or run a price reapplication immediately after regeneration.

## Exact files / sheets to change

Expected file changes after approval:

- `stingray_master.xlsx`
  - `z06_options`
  - `zr1_options`
  - `zr1x_options`
  - `z06_ovs`
  - `zr1_ovs`
  - `zr1x_ovs`
  - `future_model_source_review`
  - `future_model_option_review`

Recommended support script:

- Add `scripts/apply_z_exterior_paint_options.py`
  - dry-run default
  - explicit `--write`
  - idempotent by option ID and model
  - uses `save_workbook_safely()`
  - verifies saved workbook on disk

Do not change:

- `form_*` generated sheets
- `form-output/`
- `form-app/data.js`
- runtime JS/CSS/HTML
- model metadata activation/promotion sheets
- dealer submission code/path
- existing Stingray or Grand Sport source rows
- rule, rule group, exclusive group, price-rule, interior, or color_override logic

## Proposed implementation steps

1. Add the dry-run/write helper.

2. Build the canonical paint rows from `grandSport_options` rows in `sec_pain_001`:
   - assert exactly 10 rows are present.
   - assert their option IDs/RPOs/names/descriptions/prices match `stingray_options` by RPO.
   - normalize display orders to `10` through `100` in the canonical paint order.

3. For each target model/sheet:
   - append missing paint rows to `z06_options`, `zr1_options`, `zr1x_options`.
   - if a paint option ID is already present, verify it matches canonical fields rather than duplicate it.
   - set all paint rows active/selectable with `section_id=sec_pain_001`.
   - write `price` as the canonical numeric price, including explicit `0` for no-upcharge colors.

4. Add OVS rows:
   - Z06: 10 paint options x 6 variants = 60 OVS rows.
   - ZR1: 10 paint options x 4 variants = 40 OVS rows.
   - ZR1X: 10 paint options x 4 variants = 40 OVS rows.
   - Each status should be `available` because the user confirmed the same compatibility across all models.
   - If rows already exist, verify/update to `available` rather than duplicate.

5. Add provenance/review rows:
   - `future_model_source_review`: 30 approved rows, one per model x paint option.
     - `model_key`: `z06`, `zr1`, or `zr1x`
     - `source_group`: `exterior_paint`
     - `raw_source_sheets`: a stable workbook-owned/provenance label, for example `grandSport_options; stingray_options; user_confirmed_same_across_models`
     - `raw_source_spans`: stable option ID or source row reference.
     - `source_orderable_rpo` / `source_primary_rpo` / `approved_rpo`: paint RPO.
     - `source_option_description` / `approved_option_name`: paint name.
     - `source_detail_raw` or `approved_description`: touch-up paint description.
     - `approved_option_id`: canonical option ID.
     - `approved_price`: canonical price.
     - `approved_section_id`: `sec_pain_001`.
     - `approved_selectable`: `True`.
     - `approved_display_order`: canonical display order.
     - `review_status`: `approved`.
     - `active`: `True`.
     - all model-relevant raw/status columns: `available` for that model's variants; leave unrelated model status columns blank.
     - `notes`: user-confirmed same name/RPO/description/price/compatibility across all models.
   - `future_model_option_review`: 30 matching approved rows, one per model x paint option.
     - include final fields matching the target option rows.
     - `normalized_status_summary` should include all variant statuses for that model.
     - `review_status=approved`, `active=True`.
   - The helper must avoid duplicate review rows by a stable key, preferably `(model_key, source_group/raw_source_sheet, source_rpo)` or `(model_key, final_option_id/source_rpo)` with preflight duplicate reporting.

6. Save safely:
   - refuse if `~$stingray_master.xlsx` exists.
   - use `save_workbook_safely()`.
   - reopen saved workbook and verify exact row counts and cell values.

## Constraints repeated back

- Spec-first: no workbook edit until this spec is approved.
- Workbook source-of-truth: put the paint rows in workbook source sheets, not in JavaScript or generated artifacts.
- No runtime behavior change.
- No generated `form_*` hand edits.
- No `form-app/data.js` regeneration in this pass.
- No dealer submission endpoint/payload/Turnstile changes.
- No new dependencies.
- No broad refactor.
- Do not add hardcoded model/RPO-specific runtime exceptions.
- Do not disturb prior Z pricing/section repairs.
- Do not use `apply_future_model_option_review.py` write mode in this pass unless separately modified to preserve prices and explicitly re-approved.

## Risks and non-goals

Risks:

- Future option-review regeneration currently blanks prices. Adding review rows improves provenance, but does not make that writer safe for priced option regeneration yet.
- If the helper only appends direct option rows and skips review rows, a later regeneration could remove paint rows. This spec avoids that by adding review rows too.
- Paint rows may need default-selection behavior later, but Stingray/Grand Sport paint rows currently do not carry `display_behavior=default_selected`; this pass should preserve that structure.
- Color/interior override behavior is not validated for Z interiors in this pass. Existing `color_overrides` already references the shared paint option IDs, but Z interior scoping is a separate pass.

Non-goals:

- Do not implement Z color/interior override rules.
- Do not update or add `color_overrides` rows.
- Do not change stripe/exterior color exclusion rules beyond giving those existing rules real paint option IDs to target later.
- Do not run Z runtime promotion.
- Do not regenerate app data.
- Do not solve the future option-review price-preservation gap in the same pass unless explicitly expanded.

## Validation plan

Pre-write dry-run:

```sh
cd /Users/seandm/Projects/27vette
.venv/bin/python scripts/apply_z_exterior_paint_options.py --dry-run
```

Expected dry-run report:

- confirms 10 canonical paint rows from Stingray/Grand Sport.
- would add/update 30 option rows total:
  - 10 in `z06_options`
  - 10 in `zr1_options`
  - 10 in `zr1x_options`
- would add/update 140 OVS rows total:
  - 60 in `z06_ovs`
  - 40 in `zr1_ovs`
  - 40 in `zr1x_ovs`
- would add/update 30 `future_model_source_review` rows.
- would add/update 30 `future_model_option_review` rows.
- reports no duplicate option IDs or OVS duplicates.

Write after approval:

```sh
.venv/bin/python scripts/apply_z_exterior_paint_options.py --write
```

Workbook validation:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Post-write idempotence:

```sh
.venv/bin/python scripts/apply_z_exterior_paint_options.py --dry-run
```

Expected: `total_updates=0` or equivalent no-op report.

Post-write inspection should verify:

- each Z option sheet has exactly 10 active/selectable `sec_pain_001` rows.
- each Z option sheet has the exact canonical paint RPO/name/description/price/display_order values.
- each Z OVS sheet has available rows for every paint option x model variant.
- `future_model_source_review` and `future_model_option_review` include approved active paint rows for all three Z models.
- future model metadata remains inactive/unpromoted.

Do not run Node runtime tests unless this pass unexpectedly touches generated/runtime app data.

## Approval needed

Approve this spec to implement the helper and write the workbook-source paint rows, OVS rows, and review/provenance rows.
