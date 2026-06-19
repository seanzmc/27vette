Spec for first priority pass: Interior Color media + selected affordance + customer-facing copy

Decision:

- Mixed workbook + generator + runtime + tests.
- Keep image ownership in workbook asset_map.
- Keep runtime generic: render media when generated interior rows provide image_url; no hardcoded RPO/image maps in app.js.
- Scope this first pass to priority A and B only:
  A. Interior Color swatches/images + explicit selected badge.
  B. Replace “1 choice” / internal compatibility copy with customer-facing language.
- Defer C/D/E:
  C. Interior composition summary.
  D. Interior Trim / D30 ownership cleanup.
  E. step-rail completion indicators.

Evidence inspected:

- docs/interiorUIcritique.md
- form-app/app.js
  - renderInteriorCard() already supports generic renderCardMedia(interior, ...) if generated interior rows contain image fields.
  - renderInteriorGroups() currently emits the “1 choice” count at app.js:1903.
  - Interior copy currently says Showing colors compatible with ${RPO} ${seat label} at app.js:2444.
- form-app/styles.css
  - .choice-media[data-fit="swatch"] already exists and uses a shorter swatch aspect ratio.
  - selected card state is currently only outline-based.
- scripts/corvette_form_generator/contract.py
  - asset_map currently supports model and option image fields.
  - Current helper filters by exact model_key.
- scripts/corvette_form_generator/interiors.py
  - build_model_interiors() owns generated interior rows.
  - It does not currently merge asset_map image fields into interiors.
- scripts/corvette_form_generator/production.py
  - form_choices already emits ASSET_IMAGE_FIELDS.
  - form_interiors does not yet emit those fields.
- Workbook read-only inspection:
  - asset_map headers: model_key, target_type, target_id, image_url, image_alt, image_fit, image_position, active, notes.
  - active asset rows currently cover model and option, not interior rows.
  - form-app/data.js currently has 0 interior rows with image_url.
  - Seatbelt images already flow through asset_map option rows.
- Hosted URL probe:
  - Lowercase interior swatch URLs are live for at least:
    - https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/hta.png
    - hup.png
    - huq.png
    - htj.png
    - hue.png
    - hul.png
    - hur.png
    - huu.png
    - huw.png
    - hux.png
    - hzb.png
    - hzn.png
  - Uppercase equivalents returned 404, so asset rows should use lowercase hosted filenames.

Current repo state:

- Branch: main
- Dirty/untracked:
  - docs/interiorUIcritique.md
  - src-img/
- No workbook lock file found.
- I have not edited anything.

Exact changes proposed after approval:

1. Workbook: stingray_master.xlsx, sheet asset_map
   - Add active rows for interior swatches using existing sheet shape.
   - Proposed target shape:
     - model_key: active model key, likely stingray, grand_sport, z06 where the interior code exists and hosted URL returns 200.
     - target_type: interior_code
     - target_id: interior code, e.g. HTA, HUP, HUQ
     - image_url: WordPress hosted lowercase URL, e.g. .../hta.png
     - image_alt: customer-facing swatch alt, e.g. HTA Jet Black interior swatch
     - image_fit: swatch
     - image_position: center
     - active: TRUE
   - Do not use local src-img/ paths in runtime.
   - Use src-img/ only as source/reference evidence for matching codes.
   - Verify no duplicate active (model_key, target_type, target_id) rows.

2. Generator: scripts/corvette_form_generator/contract.py
   - Add a generic interior_asset_map() helper or equivalent.
   - It should consume asset_map rows with target_type == "interior_code".
   - Keep exact-model behavior for this pass; do not introduce wildcard model_key="\*" unless separately approved.

3. Generator: scripts/corvette_form_generator/interiors.py
   - Merge interior asset fields into generated interior rows by interior_code.
   - No RPO-specific or model-specific image logic.

4. Generator output headers: scripts/corvette_form_generator/production.py
   - Include ASSET_IMAGE_FIELDS in form_interiors headers so workbook generated sheets and JSON stay aligned.
   - Generated runtime data should then carry image_url, image_alt, image_fit, image_position on applicable interior rows.

5. Runtime: form-app/app.js
   - renderInteriorCard():
     - render a visible “✓ Selected” or “Selected” badge in the reserved availability slot when an interior is selected.
     - preserve the existing no-layout-shift selected outline behavior.
   - renderInteriorGroups():
     - replace or suppress “1 choice”; recommended first pass: suppress for single-choice groups.
   - Interior compatibility copy:
     - replace current copy with customer-facing text:
       “Showing colors compatible with AQ9 GT1 Bucket Seats. Change seats to see additional interior colors.”
     - Add a generic “Change seats” affordance that activates the Seats step, if low-risk with existing data-step/step activation patterns.

6. Runtime CSS: form-app/styles.css
   - Add selected badge styling if needed.
   - Preserve existing .choice-card.selected outline mechanics.
   - Do not add selected-state border-width, padding, transform, or layout-affecting changes.

7. Tests
   - Update/add focused tests in tests/stingray-form-regression.test.mjs:
     - generated/runtime interior rows can render media through renderInteriorGroups().
     - selected interior card includes a selected badge.
     - one-choice group no longer displays “1 choice”.
     - compatibility copy includes “Change seats”.
   - Add generated-contract checks for interior media fields where appropriate.
   - If touching Grand Sport/Z06 generated interiors, update corresponding draft tests:
     - tests/grand-sport-draft-data.test.mjs
     - tests/z06-form-data-draft.test.mjs

Constraints:

- No direct runtime use of src-img/.
- No bundled local images in the form app.
- WordPress hosted URL + workbook asset_map remains the workflow.
- No hardcoded RPO/image maps in JavaScript.
- No dealer submission endpoint/payload changes.
- No D30/UQT ownership cleanup in this pass.
- No broad step-summary redesign in this pass.
- Preserve visual layout stability and current selected-card mechanics.

Risks:

- Some src-img/ files may not yet be hosted at the expected lowercase WordPress URL. Those should not get active workbook rows until verified with HTTP 200.
- Adding target_type=interior_code extends current asset_map semantics. This is still workbook-owned and generic, but it is a generator contract change.
- Generated artifacts will change: form_interiors, model JSON, and form-app/data.js.
- Tests currently assert selected-card styling constraints; implementation must keep those constraints or update tests only where the approved UI change requires it.

Validation plan:

1. Before workbook write:
   - git status --short --branch
   - verify no ~$stingray_master.xlsx
   - probe candidate WordPress URLs with curl
   - inspect duplicate active asset keys in asset_map

2. Workbook/generation:
   - write workbook through save_workbook_safely()
   - reopen workbook with openpyxl and verify added asset_map rows
   - .venv/bin/python scripts/generate_form.py --model stingray
   - if rows are added for all active models:
     - .venv/bin/python scripts/generate_form.py --model grand_sport
     - .venv/bin/python scripts/generate_form.py --model z06
   - .venv/bin/python scripts/generate_registry.py

3. Tests:
   - node --test tests/stingray-form-regression.test.mjs
   - node --test tests/stingray-generator-stability.test.mjs
   - If Grand Sport/Z06 interior media rows are emitted:
     - node --test tests/grand-sport-draft-data.test.mjs
     - node --test tests/z06-form-data-draft.test.mjs
   - node --test tests/multi-model-runtime-switching.test.mjs

4. Browser smoke:
   - serve form-app
   - inspect Interior Color for Stingray 1LT/AQ9
   - confirm swatches render from WordPress URLs
   - confirm selected badge is obvious
   - confirm “1 choice” is gone
   - confirm “Change seats” works, if included
   - check browser console for JS errors

Recommended implementation boundary:

- First pass = A+B only.
- Use the already-hosted lowercase swatch URLs.
- Add generator support for asset_map.target_type=interior_code.
- Do not start the Interior Summary, D30/UQT cleanup, or step-rail completion indicators until this pass is verified.

Approval needed:
Approve Pass 1: Interior Color media + selected badge + customer-facing compatibility copy?

If approved, I recommend starting by creating a short-lived branch from main because the repo is currently on main and has your untracked docs/interiorUIcritique.md and src-img/ work present.
