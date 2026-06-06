# Spec: layered vehicle visualizer integration (trimmed)

Status: awaiting approval
Scope: optional, data-driven layered visualizer. Two passes only.
Deferred (separate spec, discuss after this lands): section regrouping +
vehicle-setup layout shift to make the car primary. NOT in this spec.

## Diagnosis

Change type: mixed — optional runtime JS + asset contract (generator + workbook
`asset_map`) + tests. NOT dealer-submission, NOT pricing, NOT selection rules.

Evidence inspected:

- `visualizer/visualizer.js`
  - Reads choice rows for `layer_src`, `layer_z`, `layer_src_full`.
  - `desiredLayers()` (lines 78-94) iterates **only `state.selected`**.
  - Auto-mounts `#vetteStage`, prepends to `.app-shell` if absent (117-128).
  - Monkey-patches global `render` (222-234).
- `form-app/app.js`
  - Global `render({...})` exists at line 3015; called at 1588/1618/3107.
  - Real selected-entity set is broader — `allSelectedIds()` style at 683-688:
    `state.selected` + `state.selectedInterior` + `computeAutoAdded()` keys.
  - Helpers visualizer leans on exist: `optionsById`, `interiorsById`,
    `choiceForCurrentVariant()`, `currentVariant()`.
- `form-app/index.html`
  - Loads `./data.js?v=26`, `./app.js?v=26`. No visualizer wired.
  - Mount host `.app-shell` exists (line 12).
- `scripts/generate_stingray_form.py`
  - `ASSET_IMAGE_FIELDS = ("image_url","image_alt","image_fit","image_position")`
    (line 86). `asset_fields()` at 89. Field lists at 1337, 1531.
  - No layer fields emitted anywhere.
- `scripts/corvette_form_generator/inspection.py`
  - Parallel asset path for Grand Sport / Z draft; same image-only fields.
- `stingray_master.xlsx` → `asset_map` headers:
  `asset_id, model_key, target_type, target_id, image_url, image_alt,
  image_fit, image_position, active, review_flag, notes`. No layer columns.

Root cause / gaps (all verified):

1. Generator emits no `layer_src*` → visualizer renders nothing even when
   wired. This is the core integration work.
2. `desiredLayers()` misses selected interior and auto-added/included visual
   equipment → interior color + bundled visual options would not render.
3. Monkey-patching another file's global `render` is fragile (works today,
   hidden coupling). Replace with one explicit call.

Risk level: low if kept optional + no-op when no `layer_src` rows exist.
Higher only if dropped in as-is (state gap + global wrap).

## Pass 1 — optional visualizer substrate (runtime only)

Files:

- `form-app/visualizer.js` — move runtime here so static app serves it.
- `form-app/index.html` — add `<script src="./visualizer.js?v=NN"></script>`
  after `app.js`. Bump cache version consistently.
- `form-app/app.js` — add ONE guarded call at end of `render()`:
  `if (window.renderVisualizer) { try { window.renderVisualizer(); } catch (e) { console.warn("[visualizer]", e); } }`
- `visualizer/visualizer.js` — delete monkey-patch block (222-234). Keep file
  in `visualizer/` as source-of-record OR delete after move; pick one to avoid
  drift (recommend delete, single copy under `form-app/`).
- `visualizer/export-layers.jsx` — unchanged; stays tooling, not app runtime.

Behavior:

- Fix `desiredLayers()` to consume the same set `app.js` uses:
  `state.selected` ∪ (`state.selectedInterior` if set) ∪ `computeAutoAdded()`
  keys. Resolve each id via existing helpers (`choiceForCurrentVariant`,
  `optionsById`, `interiorsById`). Skip any row without `layer_src`.
- No-op safe: zero `layer_src` rows ⇒ renders nothing, touches no selection /
  pricing / submission state.
- Preserve existing `image_url` card rendering. Visualizer is additive.

No CSS work required (auto-mount + injected styles suffice). Layout/placement
deferred to the separate layout spec.

## Pass 2 — asset layer contract (generator + workbook)

Workbook `asset_map` — add optional columns only:

- `layer_src` (web-sized layer path)
- `layer_z` (stacking int; blank ⇒ visualizer DEFAULT_Z by section)
- `layer_src_full` (optional 2500px master for export; blank ⇒ falls back)

Do NOT add `layer_role` / new `target_type` values in this pass. Existing
`target_type=option` and `target_type=interior` cover current needs. Revisit
only if a real body-base layer proves it can't be carried by a paint/interior
row.

Generator changes (both paths, keep multi-model aligned):

- `scripts/generate_stingray_form.py`
  - Extend `ASSET_IMAGE_FIELDS` (or add `ASSET_LAYER_FIELDS`) + `asset_fields()`
    to read/emit the three layer fields.
  - Include in `form_choices` + `choices` field lists (1337, 1531) + data.js /
    JSON / CSV output where image fields already flow.
- `scripts/corvette_form_generator/inspection.py`
  - Mirror the same emission for Grand Sport / Z draft data.

No-op until real layer rows populated. Existing image fields untouched.

## Constraints

- Workbook = source of truth. Reuse `asset_map`; no parallel image framework.
- No new dependencies. No runtime refactor beyond the single render hook.
- No model/RPO-specific visual logic in JS.
- No change to dealer endpoint, payload, Turnstile, pricing, selection rules.
- Do not edit generated `form_*` sheets directly.
- Workbook write requires Excel closed, no `~$stingray_master.xlsx` lock;
  verify file on disk after write.

## Validation

1. Serve: `cd form-app && ../.venv/bin/python -m http.server 8000`. Smoke:
   model switch; body/trim; paint/wheel/caliper/exterior selection updates
   stack; interior selection updates stack; option without `layer_src` does
   nothing; reset rebuilds; build download still works; dealer modal validates.
2. Regenerate:
   - `.venv/bin/python scripts/generate_stingray_form.py`
   - `.venv/bin/python scripts/generate_grand_sport_form.py`
   - `.venv/bin/python scripts/generate_z06_form.py` (if shared contract changed)
3. Tests:
   - `node --test tests/stingray-form-regression.test.mjs`
   - `node --test tests/stingray-generator-stability.test.mjs`
   - `node --test tests/grand-sport-draft-data.test.mjs`
   - `node --test tests/z06-form-data-draft.test.mjs`
   - `node --test tests/multi-model-runtime-switching.test.mjs`

## Non-goals (this spec)

- No section regrouping (paint/aero/wheels/calipers/stripes grouping).
- No vehicle-setup layout shift / car-primary view / right-shelf or inline
  option layout. Tracked for the follow-up layout spec.
- No `layer_role` / new `target_type`. No dealer image attachment. No ZR1/ZR1X
  runtime promotion. No product-rule changes.

## Next step

After this lands and a few real `layer_src` rows render correctly: open the
layout spec — collapse similar sections into grouped exterior/interior views and
shift vehicle-setup-review to a car-primary layout (option shelf right or inline
below the stage). That spec depends on this contract existing, not the reverse.
