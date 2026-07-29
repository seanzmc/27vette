# Asset Map Exterior Color URL Refresh Spec

> **Archive closure (2026-07-29): COMPLETED.** Implementation is present at `bc68fdd`. Any trailing approval request is historical; current operator commands are owned by `README.md`. Stage C approved this completed plan for archival.

> **Execution status (2026-07-29): SUPERSEDED FOR COMMANDS.** Compatibility-artifact paths and generation commands below describe an older topology and are not operator guidance. Use `README.md` and Pass 4 Stage A of `docs/superpowers/specs/2026-07-23-validation-single-lane-active-surface-cleanup.md` for current commands. This notice does not decide any still-open asset-data work.

## Request

Use the newly pasted exterior color image URLs in `asset_map` to replace the currently active exterior paint image URLs used by Stingray and Grand Sport, and fill the missing metadata columns for the newly pasted asset rows where the target can be identified safely.

## Diagnosis

Source of truth is workbook-owned image metadata in `stingray_master.xlsx` sheet `asset_map`.

Current generator behavior:

- `scripts/generate_stingray_form.py`
  - `load_asset_map(wb, model_key, "option")` reads active `asset_map` rows for the live Stingray generator.
  - Used fields are `image_url`, `image_alt`, `image_fit`, `image_position`.
  - Rows are keyed by exact `model_key`, `target_type`, and `target_id`.
- `scripts/corvette_form_generator/inspection.py`
  - `load_asset_map(wb, model_key)` reads active `asset_map` rows for Grand Sport/Z06 inspection and draft generation.
  - Same target contract: active row + exact model + `target_type=option` + valid `target_id`.
- Runtime consumes generated choice fields only. No runtime image map should be hardcoded.

Workbook evidence:

- `asset_map` headers:
  - `asset_id`, `model_key`, `target_type`, `target_id`, `image_url`, `image_alt`, `image_fit`, `image_position`, `active`, `review_flag`, `notes`
- Existing active Grand Sport paint asset rows are rows 3-12 and use older `expt_*` URLs.
- Existing active Stingray paint asset rows are rows 42-51 and use copied older `expt_*` URLs.
- Newly pasted exterior paint URLs are rows 53-62, currently `model_key=z06` but with missing metadata columns:
  - 53 `imgi_17_gph.png` -> `GPH` / `opt_gph_001` / Red Mist Metallic Tintcoat
  - 54 `imgi_16_g26.png` -> `G26` / `opt_g26_001` / Sebring Orange Tintcoat
  - 55 `imgi_13_g4z.png` -> `G4Z` / `opt_g4z_001` / Roswell Green Metallic
  - 56 `imgi_14_gtr.png` -> `GTR` / `opt_gtr_001` / Admiral Blue Metallic
  - 57 `imgi_11_gec.png` -> `GEC` / `opt_gec_001` / Pitch Gray Metallic
  - 58 `imgi_12_gka.png` -> `GKA` / `opt_gka_001` / Blade Silver Metallic
  - 59 `imgi_10_gba.png` -> `GBA` / `opt_gba_001` / Black
  - 60 `imgi_15_gbk.png` -> `GBK` / `opt_gbk_001` / Competition Yellow Tintcoat Metallic
  - 61 `imgi_9_g8g.png` -> `G8G` / `opt_g8g_001` / Arctic White
  - 62 `imgi_8_gkz.png` -> `GKZ` / `opt_gkz_001` / Torch Red

The URL filenames contain the paint RPOs, and those RPOs are present as exterior paint rows in `stingray_options`, `grandSport_options`, and `z06_options` under `section_id=sec_pain_001`.

Additional newly pasted rows with unambiguous RPO matches:

- Z06 wheel rows 63-69 and 77-83 match active Z06 option IDs by filename RPO.
- Grand Sport wheel rows 70-76 match active Grand Sport option IDs by filename RPO.
- Stingray wheel rows 84-91 match active Stingray option IDs by filename RPO, except `QEB` has both selectable and standard-equipment rows; use selectable `opt_qeb_001`, not standard `opt_qeb_002`.

Unresolved rows:

- Rows 92-93 (`c-07-2.png`, `c-07-1.png`) do not encode an RPO that matches `stingray_options`; leave inactive/review unless the user supplies the intended target.
- Older rows 29-39 are interior-code-like URLs (`huc`, `hvz`, etc.) but do not match current option IDs. The current asset pipeline does not consume interior image targets, so do not activate them in this pass.

## Change Type

Data-only workbook metadata update plus generated artifact refresh.

## Exact Files / Sheets To Change

Workbook source:

- `stingray_master.xlsx`
  - `asset_map` only

Generated artifacts after workbook save:

- `form-output/inspection/grand-sport-*`
- `form-output/inspection/z06-*` only if Z06 rows are filled/activated
- `form-output/stingray-form-data.json`
- `form-output/stingray-form-data.csv`
- `form-app/data.js`
- generated `form_*` workbook sheets from `scripts/generate_stingray_form.py`

Tests may need focused assertions added/updated if current tests do not protect these asset mappings.

## Proposed Workbook Edits

### A. Use the new exterior paint URLs for Grand Sport and Stingray

For each exterior paint RPO above, update the existing active Grand Sport and Stingray option asset rows rather than adding duplicate active rows:

- Grand Sport existing rows 3-12: keep `model_key=grand_sport`, `target_type=option`, `target_id=opt_<rpo>_001`; replace `image_url` with the corresponding row 53-62 `imgi_*_<rpo>.png` URL.
- Stingray existing rows 42-51: keep `model_key=stingray`, `target_type=option`, `target_id=opt_<rpo>_001`; replace `image_url` with the same corresponding row 53-62 URL.

Fill/normalize these fields on the updated active rows:

- `asset_id`: stable current IDs are already present; preserve them.
- `image_alt`: use the paint option label from the owning option sheet.
- `image_fit`: `cover`.
- `image_position`: `center`.
- `active`: `TRUE`.
- `review_flag`: `FALSE`.
- `notes`: update to say the row uses the newly supplied exterior paint image URL matched by RPO.

### B. Complete newly pasted Z06 exterior paint rows

Rows 53-62 currently have `model_key=z06` and are valid Z06 exterior paint assets. Complete them as active option asset rows:

- `asset_id=asset_z06_<rpo>_001`
- `model_key=z06`
- `target_type=option`
- `target_id=opt_<rpo>_001`
- `image_url`: preserve the pasted URL
- `image_alt`: option label from `z06_options`
- `image_fit=cover`
- `image_position=center`
- `active=TRUE`
- `review_flag=FALSE`
- `notes=Matched to z06_options.option_id from pasted image URL RPO.`

This preserves the pasted rows and makes Z06 draft/runtime-promotion artifacts use the same new paint images.

### C. Complete newly pasted wheel rows with unambiguous RPO matches

Complete rows 63-91 using the same metadata pattern when there is exactly one safe selectable target in the same model option sheet:

- `asset_id=asset_<model>_<rpo>_001` using model prefixes `z06`, `gs`, `st` for readability.
- `target_type=option`.
- `target_id` from the matched option row.
- `image_alt` from the option label.
- `image_fit=cover`.
- `image_position=center`.
- `active=TRUE`.
- `review_flag=FALSE`.
- `notes=Matched to <sheet>.option_id from pasted image URL RPO.`

Special case:

- Row 84 `c-qeb.png` / `QEB`: choose Stingray selectable row `opt_qeb_001` in `sec_whee_002`; do not point to standard-equipment mirror `opt_qeb_002`.

### D. Leave unresolved rows inactive/review

Do not activate rows 92-93 until their target IDs are known. Fill only review-safe notes if needed:

- `active=FALSE`
- `review_flag=TRUE`
- notes: `Unresolved pasted asset; filename does not contain a matching option RPO.`

Do not activate rows 29-39 in this pass; the current app/generator path does not consume interior asset targets.

## Constraints / Non-goals

- No runtime JavaScript image exceptions.
- No new asset pipeline or parallel review taxonomy.
- Do not edit generated `form_*` sheets directly.
- Do not change option labels, prices, availability, rules, section ownership, dealer submission behavior, endpoint, or payload shape.
- Preserve existing active model promotion state.
- Preserve user-added URLs exactly unless a URL is clearly assigned to the wrong RPO by filename.
- Do not run stale one-pass option review writers or future-model apply scripts.

## Risk

Medium.

Risks:

- Misassigning an image URL if filename RPO does not reflect visual content.
- Duplicate active `asset_map` rows for the same `(model_key, target_type, target_id)` could make generator output order-dependent.
- Rows 92-93 cannot be safely targeted without more information.

Mitigation:

- Update existing active Stingray/Grand Sport paint rows instead of creating duplicates.
- For pasted rows, only activate unambiguous filename-RPO matches.
- Verify there is at most one active asset row per `(model_key, target_type, target_id)` after save.
- Generate and inspect emitted image URLs for target paint choices.

## Validation Plan

Preflight:

```sh
python3 - <<'PY'
from pathlib import Path
print('lock=present' if Path('~$stingray_master.xlsx').exists() else 'lock=absent')
PY
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
```

After workbook edit:

1. Reopen workbook with `openpyxl` and verify:
   - Grand Sport and Stingray paint asset rows use `imgi_*_<rpo>.png` URLs.
   - Rows 53-62 are active Z06 option assets with complete metadata.
   - Rows 63-91 are active option assets where RPO matching is unambiguous.
   - Rows 92-93 remain inactive/review.
   - No duplicate active `(model_key, target_type, target_id)` rows.
2. Regenerate only required generators:

```sh
.venv/bin/python scripts/generate_grand_sport_form.py
.venv/bin/python scripts/generate_z06_form.py
.venv/bin/python scripts/generate_stingray_form.py
```

3. Focused generated-data verification:
   - `form-app/data.js` Grand Sport and Stingray exterior paint choices emit the new `imgi_*_<rpo>.png` URLs.
   - Z06 draft/live data emits completed asset rows for activated Z06 assets.
4. Targeted tests:

```sh
node --test tests/stingray-form-regression.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/z06-form-data-draft.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

5. Browser smoke:
   - Open local app.
   - Confirm Stingray and Grand Sport exterior paint cards load the new images.
   - Check console for image/JS errors.

## Approval Needed

Approve this scoped workbook/data pass before implementation.
