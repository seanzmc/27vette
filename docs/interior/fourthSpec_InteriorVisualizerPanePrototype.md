# Spec: Priority C2b — Interior Visualizer Pane Prototype

Status: Spec only. Do not implement until approved and sample layer image URLs are available.

## Diagnosis

Priority C2a established the safe foundation for a live interior visualizer:

- `stingray_master.xlsx` / `asset_map`
  - Has optional layer metadata columns: `layer_url`, `layer_url_full`, `layer_z`, and `layer_role`.
  - Current active `asset_map` rows include model, option, and interior-code image rows across Stingray, Grand Sport, and Z06.
  - Current active layer rows: `0`.
- `scripts/corvette_form_generator/contract.py`
  - Defines `ASSET_LAYER_FIELDS`.
  - Allows image-only, layer-only, or image+layer asset rows.
- `scripts/corvette_form_generator/production.py`
  - Emits optional layer fields into generated `form_choices` and `form_interiors` sheet headers.
- `scripts/corvette_form_generator/interiors.py`
  - Carries optional `interior_code` layer fields through interior rows.
- `scripts/corvette_form_generator/inspection.py`
  - Carries optional layer fields through draft model choice rows.
- `form-app/app.js`
  - Has `currentInteriorVisualizerLayers()`.
  - Combines selected interior-step option rows, auto-added interior-step option rows, and `state.selectedInterior` into a sorted layer stack.
  - Does not mount or render a pane yet.
- `visualizer/visualizer.js`
  - Still exists as an older prototype.
  - Uses old field names (`layer_src`, `layer_src_full`) rather than the C2a contract (`layer_url`, `layer_url_full`).
  - Reads only `state.selected`; it does not handle `state.selectedInterior`.
  - Auto-inserts `#vetteStage`, which is not acceptable for production wiring.

Root cause:

The app now knows how to resolve a visualizer layer stack, but no active workbook-owned layer assets exist and no intentional visualizer mount/render path exists in the customer runtime.

Risk level: medium-high.

Change type: mixed workbook source data + generator artifacts + runtime UI + CSS + tests + browser smoke.

## Goal

Prototype the smallest visible interior-only visualizer pane using one complete workbook-authored sample path.

This pass is not meant to production-polish the layout. The user has explicitly accepted that UI layout can be fine-tuned later. The goal is to prove the end-to-end path:

```text
WordPress-hosted layer asset URLs
  -> stingray_master.xlsx / asset_map layer fields
  -> scripts/generate_form.py --model <model>
  -> scripts/generate_registry.py
  -> form-app/data.js
  -> currentInteriorVisualizerLayers()
  -> visible interior visualizer pane updates immediately
```

## Required Image Inputs Before Implementation

Implementation should not start until at least one complete same-geometry sample set is available as WordPress-hosted URLs or otherwise approved production-like URLs.

Minimum sample path:

1. Base/cockpit background layer.
2. One seat layer.
3. One interior color layer tied to `state.selectedInterior` / `target_type=interior_code`.
4. One seat belt layer.
5. One interior trim layer if trim is included in this first pane.
6. Approved `layer_z` values.
7. Approved `layer_role` labels.
8. Matching canvas/aspect/geometry across all layers.
9. Compositable transparency where a layer overlays another.
10. CORS-compatible hosting if browser canvas/export is included later.

Preferred first sample:

- Model: Stingray.
- Body/trim: one simple 1LT coupe path unless the available assets dictate another path.
- Interior path should use existing stable target IDs:
  - seat option `target_type=option`, `target_id=<seat option_id>`.
  - interior color `target_type=interior_code`, `target_id=<interior_code>`.
  - seat belt option `target_type=option`, `target_id=<seat belt option_id>`.
  - interior trim option `target_type=option`, `target_id=<trim option_id>` if included.

Local `src-img/` files may be used as source/reference inventory only. Runtime layer URLs should not point to local `src-img/` paths.

## Exact Files / Sheets To Inspect

Before editing:

- `stingray_master.xlsx`
  - `asset_map`
  - relevant option source sheet for the chosen model (`stingray_options`, `grandSport_options`, or `z06_options`)
  - relevant OVS/source availability sheet for the chosen sample path
  - interior source rows and `model_interior_scope` if the sample uses `target_type=interior_code`
- `form-app/app.js`
  - `interiorCompositionStepKeys`
  - `currentInteriorVisualizerLayers()`
  - `renderStepContent()`
  - current Interior Composition Summary rendering
- `form-app/styles.css`
- `form-app/index.html`
- `visualizer/visualizer.js`
  - Inspect but do not reuse as-is unless adapted to C2a field names and `state.selectedInterior`.
- `scripts/corvette_form_generator/contract.py`
- `scripts/corvette_form_generator/production.py`
- `scripts/corvette_form_generator/interiors.py`
- `scripts/generate_form.py`
- `scripts/generate_registry.py`
- `tests/test_asset_visualizer_contract.py`
- `tests/stingray-form-regression.test.mjs`
- `tests/multi-model-runtime-switching.test.mjs`

## Exact Files / Sheets Expected To Change

Expected source changes after approval:

1. `stingray_master.xlsx` / `asset_map`
   - Add or update active layer rows for one complete sample path.
   - Use `layer_url`, `layer_url_full`, `layer_z`, and `layer_role`.
   - Preserve existing `image_url` card/swatch behavior.
   - Avoid duplicate active rows for the same `(model_key, target_type, target_id)` unless deliberately representing separate roles and documented.

2. `form-app/app.js`
   - Add a scoped interior visualizer pane renderer, e.g. `renderInteriorVisualizerPane()`.
   - Use `currentInteriorVisualizerLayers()` as the only layer source.
   - Render only on `interiorCompositionStepKeys` initially.
   - Render an empty/fallback state when no layer rows exist.
   - Do not mutate selection state from the pane.
   - Do not add model/RPO-specific image logic.

3. `form-app/styles.css`
   - Add minimal pane styles.
   - Keep the pane compact and visually subordinate to choices for this prototype.
   - Defer production layout polish to a later pass.

4. `tests/test_asset_visualizer_contract.py`
   - Add focused coverage for sample layer rows if implementation uses a helper or fixture path.

5. `tests/stingray-form-regression.test.mjs`
   - Add runtime tests for pane rendering and layer-stack updates.

Likely generated artifacts after approval:

- `form-output/stingray-form-data.json` if the first sample uses Stingray.
- `form-output/inspection/grand-sport-runtime-contract.json` and/or `form-output/inspection/z06-runtime-contract.json` only if the sample rows target those models or generator output changes globally.
- `form-app/data.js` after `scripts/generate_registry.py`.
- Generated workbook sheets such as `form_choices` and `form_interiors` after `scripts/generate_form.py --model <model>`.

## Proposed Runtime Design

Add a small visualizer pane next to or above the interior step content. Initial placement should favor low-risk integration over perfect layout:

- Render only on:
  - `seat`
  - `base_interior`
  - `seat_belt`
  - `interior_trim`
- Use the existing Priority C composition summary as the textual companion.
- Use `currentInteriorVisualizerLayers()` for the image stack.
- Use simple stacked `<img>` elements sorted by `z`.
- Escape text and keep alt text generic.
- If no layers exist, show a compact empty state such as `Visualizer preview will appear when image layers are available.`
- If only partial layers exist, render available layers without fake placeholders.
- Do not include export/download image behavior in this pass unless explicitly approved.

Potential markup shape:

```text
<section class="interior-visualizer-pane" aria-label="Interior visualizer preview">
  <div class="interior-visualizer-stage">
    <img class="interior-visualizer-layer" ...>
  </div>
  <p class="interior-visualizer-caption">Preview updates as you choose seats, color, belts, and trim.</p>
</section>
```

Do not load `visualizer/visualizer.js` directly unless it is refactored to the current contract. The safer first implementation is to keep the new pane logic inside `form-app/app.js` and later decide whether the prototype file should be retired or rewritten.

## Constraints

- Workbook/source rows own visualizer layer URLs and z-order metadata.
- Runtime JavaScript must stay generic and data-driven.
- No hardcoded model/RPO image maps.
- No local `src-img/` runtime URLs.
- No new frontend dependencies.
- No dealer submission endpoint, payload shape, Turnstile behavior, order export, or build download changes.
- Do not replace the global Build Summary drawer.
- Preserve Priority C Interior Composition Summary behavior.
- Preserve current Interior Color swatch rendering and selected badge.
- Keep the first pane interior-scoped only.
- Layout is prototype-grade in this pass; production UI polish, sticky behavior, and responsive fine-tuning are deferred.

## Non-Goals

- Full-vehicle exterior/wheel/stripe visualization.
- Exporting a flattened build image.
- Reworking `visualizer/workbook-editor/`.
- Migrating image hosting away from WordPress.
- Adding broad image coverage across all models/options.
- Final production layout polish.
- Creating fake generated layer data not backed by approved image assets.

## Risks

1. Misleading visual fidelity
   - Risk: one sample path may look more complete than actual layer coverage.
   - Mitigation: label the pane as a preview and render only real workbook-backed layers.

2. Bad layer geometry
   - Risk: mismatched image dimensions or camera angles can make the pane unusable.
   - Mitigation: require one same-geometry sample set before implementation.

3. Runtime CORS/canvas issues
   - Risk: WordPress image hosting may block future export/canvas use.
   - Mitigation: do not include export in this pass; verify normal `<img>` display first.

4. Generated artifact churn
   - Risk: generator runs can update timestamps across artifacts.
   - Mitigation: review generated diffs and restore unrelated timestamp-only churn if layer rows are scoped to one model.

5. Layout crowding
   - Risk: pane + composition summary + choices can crowd the interior flow.
   - Mitigation: keep the pane compact in this pass; defer production layout tuning.

## Implementation Tasks After Approval

1. Verify sample image URLs.
   - Confirm each URL returns HTTP 200.
   - Confirm the image dimensions/geometry are compatible.
   - Confirm URLs are production-like and not local `src-img/` paths.

2. Add RED tests.
   - Generated/workbook contract test: active layer rows are emitted onto the correct generated choice/interior rows.
   - Runtime test: pane renders on interior steps only.
   - Runtime test: changing selected option/interior changes layer stack markup.
   - Runtime test: no layer data renders a safe empty state.

3. Write workbook `asset_map` rows.
   - Use `save_workbook_safely()`.
   - Verify saved headers/rows on disk with `openpyxl`.

4. Regenerate affected artifacts.
   - At minimum for Stingray sample:
     - `.venv/bin/python scripts/generate_form.py --model stingray`
     - `.venv/bin/python scripts/generate_registry.py`
   - Add Grand Sport/Z06 generation only if their source data or contracts are touched.

5. Implement the pane renderer.
   - Use `currentInteriorVisualizerLayers()`.
   - Do not wire the old prototype's auto-insertion behavior.
   - Render no fake layers.

6. Add minimal CSS.
   - Keep sizing stable.
   - Ensure mobile does not make choices unusable.

7. Browser smoke.
   - Verify pane appears on interior steps.
   - Verify layer changes after selecting the sample seat/interior/seat belt/trim.
   - Verify empty/partial layer states do not crash.
   - Verify console has no JS errors.

## Validation Plan

Preflight:

```sh
git status --short --branch
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python - <<'PY'
from openpyxl import load_workbook
wb = load_workbook('stingray_master.xlsx', read_only=True, data_only=True)
ws = wb['asset_map']
headers = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
print(headers)
print('rows', ws.max_row)
wb.close()
PY
```

Expected gates for a Stingray-first sample:

```sh
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_registry.py
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
.venv/bin/python -m unittest tests/test_asset_visualizer_contract.py
node --test tests/stingray-form-regression.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

If Grand Sport or Z06 rows are touched, add:

```sh
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/z06-contract-preview.test.mjs
node --test tests/z06-form-data-draft.test.mjs
```

Browser smoke:

```sh
cd form-app
../.venv/bin/python -m http.server 8000
```

Manual checks at `http://localhost:8000`:

- Pane appears on approved interior steps only.
- Pane updates immediately for sample seat, interior color, seat belt, and trim selections covered by layer rows.
- Priority C composition summary still updates.
- Missing layer metadata degrades gracefully.
- Mobile layout remains usable enough for prototype review.
- Browser console has no JavaScript errors.

## Approval Question

Approve Priority C2b as a Stingray-first interior visualizer pane prototype once one complete sample layer image set is available, with production layout polish deferred to a later pass?
