# Spec: Priority C2 — Interior Visualizer Pane Spike

Status: C2a foundation implemented. Optional workbook-owned visualizer layer fields and a generic runtime layer resolver have landed; production pane mounting and real layer rows remain pending image-source approval.

## Diagnosis

The desired interior experience is a live visualizer pane: a working image stays on screen while Seats, Interior Color, Seat Belt, and Interior Trim selections update the image immediately.

Current evidence:

- `visualizer/visualizer.js`
  - Exists as a dependency-free prototype.
  - Is not loaded by `form-app/index.html`.
  - Reads selected option rows through `state.selected`, `choiceForCurrentVariant()`, and `optionsById`.
  - Looks for `layer_src`, `layer_z`, and `layer_src_full` on choice rows.
  - Auto-prepends `#vetteStage` into `.app-shell` if no mount exists.
- `form-app/index.html`
  - Loads only `data.js` and `app.js` for the customer app.
  - Has no intentional visualizer mount point.
- `form-app/app.js`
  - Interior Color is not stored in `state.selected`; it is stored in `state.selectedInterior` and resolved through `interiorsById`.
  - Existing card media rendering uses generated `image_url`, `image_alt`, `image_fit`, and `image_position`.
- `scripts/corvette_form_generator/contract.py`
  - Current `asset_map` contract supports `image_url`, `image_alt`, `image_fit`, and `image_position`.
  - It already has loaders for `option` and `interior_code` assets, but no layer metadata fields.
- `stingray_master.xlsx` / `asset_map`
  - Current headers are `model_key`, `target_type`, `target_id`, `image_url`, `image_alt`, `image_fit`, `image_position`, `active`, and `notes`.
  - Active rows already cover `interior_code`, `model`, and `option` target types for Stingray, Grand Sport, and Z06.
- `src-img/`
  - Local image files exist and are useful source/reference assets.
  - Runtime images should remain WordPress-hosted and workbook-authored through metadata, not bundled from local `src-img/` paths.

Root cause:

The runtime has enough state to know the selected interior composition, but it does not have a production-owned visualizer contract. The existing prototype expects fields that are not emitted and misses the separate Interior Color state path.

Risk level: medium-high.

Change type: mixed investigation / workbook-source contract / generator / generated artifact / runtime UI / tests. This is not a CSS-only or runtime-only pass.

## Goal

Prove the smallest source-of-truth-safe visualizer path before production wiring:

1. Identify the workbook-owned media contract for visualizer layers.
2. Prove how selected option rows and selected interior rows feed a single layer stack.
3. Keep the Priority C summary panel intact and use it as the interior-state companion to the pane.
4. Avoid hardcoded RPO/model image logic in runtime JavaScript.

## Exact Files / Sheets To Inspect

Required pre-implementation inspection:

- `stingray_master.xlsx`
  - `asset_map`
  - `model_workbook_sources`
  - `model_master`
  - current interior source sheets if layer coverage depends on interior IDs/codes
- `scripts/corvette_form_generator/contract.py`
- `scripts/generate_form.py`
- `scripts/generate_registry.py`
- `form-app/app.js`
- `form-app/index.html`
- `form-app/styles.css`
- `visualizer/visualizer.js`
- `tests/stingray-form-regression.test.mjs`
- `tests/multi-model-runtime-switching.test.mjs`
- Generated runtime contracts under `form-output/` and `form-app/data.js`
- Local reference images under `src-img/` only as source inventory, not as runtime URLs

## Expected Files / Sheets To Change If The Spike Proves Viable

1. `stingray_master.xlsx` / `asset_map`
   - Preferred first attempt: extend the existing media owner with optional visualizer-layer fields rather than creating a parallel sheet.
   - Candidate optional fields to evaluate before approval:
     - `layer_url`
     - `layer_url_full`
     - `layer_z`
     - `layer_role`
   - Use model-scoped rows and existing stable target identifiers such as `target_type=option` and `target_type=interior_code` where possible.

2. `scripts/corvette_form_generator/contract.py`
   - Load optional visualizer layer fields generically from workbook rows.
   - Do not add model/RPO-specific image branching.

3. Generator/runtime contract emitters touched by asset metadata
   - Emit visualizer layer metadata to the runtime rows that own the selected state.
   - Preserve existing `image_url` card/swatch behavior.

4. `form-app/app.js`
   - Add or adapt a generic visualizer layer resolver that combines:
     - selected option rows from `state.selected`
     - selected interior row from `state.selectedInterior`
     - auto-added rows only if the generated layer contract explicitly provides a customer-visible layer
   - Do not mutate selections from the visualizer.

5. `form-app/index.html`
   - Add an intentional mount point only after the data contract is proven.
   - Do not rely on `visualizer/visualizer.js` auto-prepending into `.app-shell`.

6. `form-app/styles.css`
   - Add scoped pane styles compatible with the Priority C summary panel.
   - Preserve current shell/sidebar layout and mobile behavior.

7. Tests
   - Add generated-contract tests for layer metadata when rows exist.
   - Add runtime tests that prove the layer stack updates when selected options and `state.selectedInterior` change.
   - Keep existing regression and multi-model switching coverage green.

Likely generated artifacts if implemented:

- `form-output/*-runtime-contract.json` for affected models
- `form-app/data.js`
- Generated workbook `form_*` sheets only if the generator contract writes these fields there

## Spike Tasks

1. Inventory current media ownership.
   - Count active `asset_map` rows by model and target type.
   - Verify whether current `interior_code` image rows are swatch/card media, layer-ready media, or both.
   - Verify WordPress URL availability and case sensitivity for any proposed runtime image URL.

2. Decide the layer contract.
   - Prefer extending `asset_map` with optional layer fields if it can represent both card images and visualizer layers cleanly.
   - Do not overload existing `image_url` if the current image is a swatch/detail card rather than a composable layer.
   - Add a new workbook source sheet only if `asset_map` cannot express the relationship without ambiguity; document why before editing.

3. Add RED generated-contract tests.
   - Assert selected option/interior rows can carry layer metadata when workbook rows provide it.
   - Assert absence of layer rows produces no runtime crash and no fake placeholder layers.

4. Add RED runtime visualizer tests.
   - Assert a mounted pane can render an empty state safely.
   - Assert changing an option selection changes the layer stack.
   - Assert changing `state.selectedInterior` changes the layer stack.
   - Assert model switching clears/rebuilds the layer stack without stale layers.

5. Implement the smallest generic contract path.
   - Workbook rows own visualizer asset URLs and z-order metadata.
   - Generator emits those fields without model/RPO branches.
   - Runtime reads emitted fields only.

6. Mount the pane only after contract proof.
   - Add explicit markup/mounting, not prototype auto-insertion.
   - Keep the pane local to the interior flow first unless the approved scope expands to full-vehicle visualization.

7. Browser smoke.
   - Verify Seats, Interior Color, Seat Belt, and Interior Trim update the pane.
   - Verify Priority C summary panel still updates.
   - Verify mobile layout does not push required choices below an unusable fold.
   - Verify no console errors.

## Constraints

- Workbook/source rows own media and layer metadata.
- Do not hardcode model/RPO image rules in `form-app/app.js` or `visualizer/visualizer.js`.
- Do not hand-edit generated `form-output/*` or `form-app/data.js`.
- Do not use local `src-img/` paths as runtime URLs.
- No new frontend dependencies.
- No dealer submission endpoint, payload shape, or Turnstile changes.
- Preserve Priority C summary behavior and tests.
- Preserve current Interior Color swatch rendering and selected badge.
- Keep this interior-scoped unless a separate spec approves a whole-vehicle visualizer.

## Non-Goals

- Building full exterior/wheel/stripe visualization.
- Replacing the global Build Summary drawer.
- Reclassifying `UQT` or `D30`.
- Creating placeholder generated layer data that looks real but is not backed by approved image assets.
- Migrating image hosting away from WordPress.
- Reworking workbook-editor UI under `visualizer/workbook-editor/`.

## Risks

1. False visual fidelity
   - Risk: a swatch/detail image may imply a composited cockpit view.
   - Mitigation: only call it a visualizer layer when the asset is intended for compositing; otherwise label it as a preview.

2. Duplicate media contracts
   - Risk: adding another media sheet can drift from `asset_map`.
   - Mitigation: prefer optional fields on `asset_map`; add a new sheet only with explicit proof.

3. Runtime state mismatch
   - Risk: selected options and selected interiors live in different state paths.
   - Mitigation: test `state.selectedInterior` explicitly before wiring production UI.

4. Generated artifact churn
   - Risk: adding fields may touch all promoted model contracts.
   - Mitigation: snapshot before/after generated contracts and separate timestamp/no-op churn from real layer fields.

5. Layout crowding
   - Risk: a live pane plus composition panel can crowd interior steps.
   - Mitigation: keep the pane compact, responsive, and locally scoped to interior steps.

## Validation Plan

Preflight:

```sh
git status --short --branch
.venv/bin/python - <<'PY'
from openpyxl import load_workbook
wb = load_workbook('stingray_master.xlsx', read_only=True, data_only=True)
print(wb['asset_map'].max_row)
print([cell.value for cell in next(wb['asset_map'].iter_rows(min_row=1, max_row=1))])
PY
```

Expected implementation gates if workbook/generator/runtime changes land:

```sh
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
.venv/bin/python scripts/generate_registry.py
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
node --test tests/stingray-form-regression.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Add or extend focused generated-contract tests as the implementation defines the final layer fields.

Browser smoke:

```sh
cd form-app
../.venv/bin/python -m http.server 8000
```

Manual checks at `http://localhost:8000`:

- Interior visualizer mount appears only on approved interior steps.
- Seat, Interior Color, Seat Belt, and Interior Trim changes update the pane immediately.
- Switching models rebuilds the pane without stale layers.
- Missing layer metadata degrades gracefully.
- Console has no JavaScript errors.

## Approval Question

After Priority C lands, approve Priority C2 as a mixed workbook/generator/runtime visualizer spike to prove a workbook-owned interior layer contract before production visualizer wiring?

## C2a Completion Evidence

Implemented foundation only:

- `stingray_master.xlsx` / `asset_map`
  - Added optional layer metadata columns: `layer_url`, `layer_url_full`, `layer_z`, and `layer_role`.
  - No active production layer URLs were added in this pass.
- `scripts/corvette_form_generator/contract.py`
  - Added `ASSET_LAYER_FIELDS`.
  - Allows active `asset_map` rows to be image-only, layer-only, or both.
  - Keeps layer fields absent from runtime rows when workbook rows do not provide layer metadata.
- `scripts/corvette_form_generator/production.py`
  - Added optional layer fields to generated `form_choices` and `form_interiors` sheet headers.
- `scripts/corvette_form_generator/interiors.py`
  - Carries optional interior-code layer fields through generated interior rows when present.
- `scripts/corvette_form_generator/inspection.py`
  - Carries optional layer fields through draft model choice rows when present.
- `form-app/app.js`
  - Added `currentInteriorVisualizerLayers()` as a non-rendering resolver.
  - Combines selected interior-step options, auto-added interior-step options, and `state.selectedInterior` into one ordered layer stack.
  - Does not mount or display a visualizer pane yet.
- `tests/test_asset_visualizer_contract.py`
  - Covers image vs layer field separation, layer-only rows, and absence of blank layer fields.
- `tests/stingray-form-regression.test.mjs`
  - Covers selected option + selected interior layer resolution and no-layer graceful empty state.

Validation run:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
.venv/bin/python scripts/generate_registry.py
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
.venv/bin/python -m unittest tests/test_asset_visualizer_contract.py
node --test tests/stingray-form-regression.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/z06-contract-preview.test.mjs
node --test tests/z06-form-data-draft.test.mjs
git diff --check
```

Generated JSON and `form-app/data.js` produced timestamp-only diffs because no active layer URLs exist yet; those timestamp-only generated diffs were restored after validation. On-disk workbook headers were verified for `asset_map`, `form_choices`, and `form_interiors`.

Image-source timing:

- Image sources were not required for C2a because this pass only established the optional metadata contract and runtime resolver.
- Image sources are required before C2b can mount a meaningful visualizer pane or add active layer rows.
- Minimum C2b sample set should cover one complete interior path with compositable, same-geometry assets:
  - base/cockpit background
  - one seat layer
  - one interior color layer tied to `state.selectedInterior`
  - one seat belt layer
  - one interior trim layer if trim is included in the first pane
  - approved `layer_z` ordering and `layer_role` labels
- Production runtime layer URLs should be WordPress-hosted and workbook-authored, not local `src-img/` paths.
