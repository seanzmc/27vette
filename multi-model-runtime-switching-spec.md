# Phase 6 Multi-Model Runtime Switching Spec

> Spec only. Do not implement until approved. Phase 6 prepares the static form app to switch between Stingray and Grand Sport datasets while preserving the current Stingray runtime, export shape, pricing behavior, rule behavior, variant IDs, and tests.

## Goal

Add the smallest safe multi-model runtime scaffold so the static app can consume either Stingray or Grand Sport form data through the same runtime code path.

Default behavior must remain Stingray:

- The app opens on Stingray.
- Existing Stingray variant IDs remain unchanged.
- Existing Stingray selections, rules, prices, compact order output, plain text summary, and export filenames remain unchanged when Stingray is active.
- Grand Sport is exposed only after its draft/runtime contract is verified by tests.

## Diagnosis

Root cause: the static app currently assumes exactly one global data object and builds all runtime indexes once from that object.

Evidence:

- [form-app/app.js](/Users/seandm/Projects/27vette/form-app/app.js:1) binds `const data = window.STINGRAY_FORM_DATA`.
- [form-app/app.js](/Users/seandm/Projects/27vette/form-app/app.js:39) derives `runtimeSteps`, `variants`, maps, rules, interiors, and exclusive groups at module load from that single `data` object.
- [form-app/app.js](/Users/seandm/Projects/27vette/form-app/app.js:1133) hardcodes `vehicleInformation().model` as `"Corvette Stingray"`, which drives `compactOrder().title` at [form-app/app.js](/Users/seandm/Projects/27vette/form-app/app.js:1251) and `plainTextOrderSummary()` at [form-app/app.js](/Users/seandm/Projects/27vette/form-app/app.js:1274).
- [form-app/app.js](/Users/seandm/Projects/27vette/form-app/app.js:1326) hardcodes `stingray-order-summary.json` and [form-app/app.js](/Users/seandm/Projects/27vette/form-app/app.js:1330) hardcodes `stingray-order-summary.csv`.
- [form-app/app.js](/Users/seandm/Projects/27vette/form-app/app.js:1351) initializes body style and trim from the first Stingray variant and then runs existing default/reconcile behavior.
- [form-app/index.html](/Users/seandm/Projects/27vette/form-app/index.html:75) loads only `form-app/data.js` before `form-app/app.js`.
- [scripts/generate_stingray_form.py](/Users/seandm/Projects/27vette/scripts/generate_stingray_form.py:1312) writes `form-output/stingray-form-data.json`, then [scripts/generate_stingray_form.py](/Users/seandm/Projects/27vette/scripts/generate_stingray_form.py:1314) writes `form-app/data.js` as `window.STINGRAY_FORM_DATA`.
- [tests/grand-sport-draft-data.test.mjs](/Users/seandm/Projects/27vette/tests/grand-sport-draft-data.test.mjs:10) and [tests/grand-sport-contract-preview.test.mjs](/Users/seandm/Projects/27vette/tests/grand-sport-contract-preview.test.mjs:10) currently assert Grand Sport generation does not mutate `form-app/data.js`.
- [scripts/corvette_form_generator/model_configs.py](/Users/seandm/Projects/27vette/scripts/corvette_form_generator/model_configs.py:167) already has `STINGRAY_MODEL`, and [scripts/corvette_form_generator/model_configs.py](/Users/seandm/Projects/27vette/scripts/corvette_form_generator/model_configs.py:190) already has `GRAND_SPORT_MODEL` with the six `e07`/`e67` variants.

Risk level: medium. The implementation touches the central runtime bootstrap and generated data output. The safest approach is to change the data boundary first, keep the rule/selection/export algorithms unchanged, and prove Stingray output is byte-for-byte or deep-equal stable where current tests already assert it.

Behavior class: mixed runtime/data loading only. No pricing logic, rule logic, export schema, workbook schema, or UI redesign.

## Architecture Decision

### `form-app/data.js` Should Become A Registry File

Yes. In Phase 6, keep `form-app/data.js` as the single app-loaded data file, but change its shape from a single Stingray global into a multi-model registry.

Recommended shape:

```js
window.CORVETTE_FORM_DATA = {
  defaultModelKey: "stingray",
  models: {
    stingray: {
      key: "stingray",
      label: "Stingray",
      modelName: "Corvette Stingray",
      exportSlug: "stingray",
      data: { /* existing Stingray generated data */ }
    },
    grandSport: {
      key: "grandSport",
      label: "Grand Sport",
      modelName: "Corvette Grand Sport",
      exportSlug: "grand-sport",
      data: { /* verified Grand Sport generated data */ }
    }
  }
};

window.STINGRAY_FORM_DATA = window.CORVETTE_FORM_DATA.models.stingray.data;
```

Why this is the smallest safe option:

- `index.html` can continue loading `./data.js` and `./app.js` only.
- Existing VM-style tests can still load `form-app/data.js` without coordinating multiple script files.
- The legacy `window.STINGRAY_FORM_DATA` alias preserves existing test and debug assumptions while the runtime migrates to the registry.
- Data loading stays atomic for the static app; there is no new async loader, fetch path, CORS concern, or script ordering problem.

### Do Not Split Model Files In Phase 6

Do not create `form-app/data/stingray.js` or `form-app/data/grand-sport.js` in Phase 6.

Per-model app files are a reasonable later optimization, but they add script-order and test-loader churn before the model-switching behavior is proven. Keep generated inspection/runtime JSON model-scoped under `form-output/`, but keep the static app entrypoint as one generated registry file.

Future-compatible note: if payload size or caching becomes a problem, a later phase can split files like this:

```html
<script src="./data/stingray.js"></script>
<script src="./data/grand-sport.js"></script>
<script src="./data.js"></script>
<script src="./app.js"></script>
```

That split is explicitly out of scope for Phase 6.

## Generated Data Emission

Phase 6 should preserve existing generated Stingray artifacts and add only the minimum registry emission needed for the static app.

Recommended emission contract:

- Keep `form-output/stingray-form-data.json` unchanged in shape.
- Keep `form-output/stingray-form-data.csv` unchanged in shape.
- Keep `window.STINGRAY_FORM_DATA` available as a compatibility alias.
- Add `window.CORVETTE_FORM_DATA` in `form-app/data.js`.
- Add or promote a verified Grand Sport runtime JSON artifact only after the existing Grand Sport draft/preview checks pass.

Grand Sport activation gate:

- Existing Grand Sport draft/preview tests must still prove `scripts/generate_grand_sport_form.py` does not mutate `form-app/data.js`.
- A new registry build step may read the verified Grand Sport draft/runtime JSON and include it in `window.CORVETTE_FORM_DATA.models.grandSport`.
- The runtime must not synthesize missing Grand Sport rules, interiors, color overrides, or price rules. It consumes the active model data exactly as generated.

Do not activate Grand Sport in the picker until these are true:

- Grand Sport data has the same top-level live app keys as Stingray: `dataset`, `variants`, `steps`, `sections`, `contextChoices`, `choices`, `standardEquipment`, `ruleGroups`, `exclusiveGroups`, `rules`, `priceRules`, `interiors`, `colorOverrides`, `validation`.
- Grand Sport has the six expected variants: `1lt_e07`, `2lt_e07`, `3lt_e07`, `1lt_e67`, `2lt_e67`, `3lt_e67`.
- Grand Sport normalization has zero unresolved issues.
- Any deferred Grand Sport surfaces are represented explicitly in `validation` and are not hidden by runtime special cases.

## Static App Loading

`index.html` should continue to load only:

```html
<script src="./data.js?v=6"></script>
<script src="./app.js?v=6"></script>
```

Do not add async loading, `fetch()`, dynamic imports, or per-model script tags in Phase 6.

The runtime bootstrap should resolve data through one helper:

```js
function formDataRegistry() {
  return window.CORVETTE_FORM_DATA || {
    defaultModelKey: "stingray",
    models: {
      stingray: {
        key: "stingray",
        label: "Stingray",
        modelName: "Corvette Stingray",
        exportSlug: "stingray",
        data: window.STINGRAY_FORM_DATA,
      },
    },
  };
}
```

The fallback exists only for compatibility while tests and any manual debug flows are updated.

## Runtime Refactor Boundary

Replace module-level single-data constants with active-model state and rebuilt indexes.

Expected runtime concepts:

- `registry`: the `window.CORVETTE_FORM_DATA` registry.
- `activeModelKey`: `"stingray"` by default.
- `activeModel`: registry entry for `activeModelKey`.
- `data`: active model data object.
- `runtimeSteps`, `variants`, `choicesByOption`, `sectionsById`, `optionsById`, `interiorsById`, `ruleTargetsBySource`, `rulesByTarget`, `priceRulesByTarget`, `ruleGroupsBySource`, `exclusiveGroupByOption`: rebuilt whenever the active model changes.

Required helper boundary:

```js
function activateModel(modelKey, { preserveCustomer = true } = {}) {
  // validate registry key
  // assign active model and data
  // rebuild all data-derived indexes
  // reset model-scoped state
  // initialize first variant
  // reset defaults and reconcile using existing functions
  // render from the body_style step
}
```

Do not change the existing selection/rule/pricing algorithms except to make them read the current active data/indexes.

## Model Switching State Contract

On model switch:

- Reset `state.bodyStyle` to the first variant body style for the new model.
- Reset `state.trimLevel` to the first variant trim for the new model.
- Reset `state.selected`.
- Reset `state.userSelected`.
- Reset `state.selectedInterior`.
- Reset `state.activeStep` to `"body_style"`.
- Run existing `resetDefaults()`.
- Run existing `reconcileSelections()`.
- Render with scroll reset.

Customer information:

- Preserve `state.customer` on model switch.
- Rationale: customer fields are not model-scoped and preserving them avoids needless re-entry when comparing models.
- Keep the existing Reset button behavior: Reset still clears customer information through `resetCustomerInformation()`.

Body style and trim:

- Body style and trim must reset on model change.
- Do not try to map `coupe/1LT` or `convertible/3LT` across models in Phase 6. Mapping creates subtle carryover risks and is not needed for the first safe scaffold.

Selection safety:

- After any model switch, every selected option ID must exist in the active model's current variant choices or be a valid active-model auto-add/interior.
- No selected option, selected interior, auto-added RPO, or standard-equipment row from Grand Sport may remain when switching back to Stingray.
- No selected option, selected interior, auto-added RPO, or standard-equipment row from Stingray may remain when switching to Grand Sport except customer info.

## Minimum UI

Add only a small model picker. Do not do styling polish.

Recommended placement:

- In the existing topbar toolbar near Reset / Export JSON / Export CSV.
- Use a native `<select id="modelSelect">`.
- Options:
  - `Stingray`
  - `Grand Sport`
- Default selected value: `stingray`.

Recommended minimal markup:

```html
<label class="model-picker">
  <span>Model</span>
  <select id="modelSelect">
    <option value="stingray">Stingray</option>
    <option value="grandSport">Grand Sport</option>
  </select>
</label>
```

UI text updates:

- Change the document title and visible `h1` only enough to avoid a Grand Sport page reading as Stingray.
- Initial Stingray view should still render as `Stingray Order Form`.
- Grand Sport view should render as `Grand Sport Order Form`.
- Do not redesign the topbar, workspace, cards, rail, summary panel, or choice cards.

## Order Output Labels

Do not parse the model label out of `variant.display_name`.

Use registry metadata:

- Stingray `modelName`: `Corvette Stingray`
- Grand Sport `modelName`: `Corvette Grand Sport`

`vehicleInformation()` should derive `model` from the active model metadata instead of hardcoding `"Corvette Stingray"`.

`compactOrder()` should keep the current schema:

```json
{
  "title": "2027 Corvette Stingray",
  "submitted_at": "...",
  "customer": {},
  "vehicle": {
    "body_style": "coupe",
    "trim_level": "1LT",
    "display_name": "Corvette Stingray Coupe 1LT",
    "base_price": 73495
  },
  "sections": [],
  "standard_equipment": { "count": 0 },
  "msrp": 0
}
```

Only values should change by active model:

- Stingray title remains `2027 Corvette Stingray`.
- Grand Sport title becomes `2027 Corvette Grand Sport`.
- `plainTextOrderSummary()` uses the same compact order title and vehicle display name.

Export filenames:

- Stingray filenames must remain `stingray-order-summary.json` and `stingray-order-summary.csv`.
- Grand Sport may use `grand-sport-order-summary.json` and `grand-sport-order-summary.csv`.
- Do not add fields to compact JSON or CSV rows.

## Exact Files To Change If Approved

Implementation files:

- Modify: `scripts/corvette_form_generator/output.py`
  - Add a registry writer helper that can serialize multiple model entries and preserve `window.STINGRAY_FORM_DATA`.
- Modify: `scripts/generate_stingray_form.py`
  - Keep existing Stingray JSON/CSV generation.
  - Change app data emission from single `STINGRAY_FORM_DATA` output to registry output with Stingray as `defaultModelKey`.
  - Include Grand Sport only through the approved registry build path after contract verification.
- Modify or create: `scripts/generate_form.sh`
  - If a separate registry build step is added, run it after the model data artifacts are generated.
  - Preserve use of `.venv/bin/python`.
- Modify: `form-app/data.js`
  - Generated output only. It should contain `window.CORVETTE_FORM_DATA` and the compatibility alias `window.STINGRAY_FORM_DATA`.
- Modify: `form-app/index.html`
  - Add the minimal model picker.
  - Keep one data script and one app script.
  - Bump cache query strings.
- Modify: `form-app/app.js`
  - Add active-model registry bootstrap.
  - Rebuild indexes when the active model changes.
  - Add model picker binding.
  - Change `vehicleInformation()` to use active model metadata.
  - Keep selection, rule, price, line item, compact order, plain text, and export schemas intact.
- Modify: `tests/stingray-generator-stability.test.mjs`
  - Load the registry and assert `window.STINGRAY_FORM_DATA` deep-equals `window.CORVETTE_FORM_DATA.models.stingray.data`.
  - Preserve existing Stingray generated contract counts.
- Modify: `tests/stingray-form-regression.test.mjs`
  - Load the registry-backed data.
  - Preserve all existing Stingray behavior assertions.
  - Add explicit default-model assertions.
- Create: `tests/multi-model-runtime-switching.test.mjs`
  - Cover registry shape, default model, switching behavior, reset behavior, Grand Sport labels, and no cross-model data mixing.

Files not to change:

- `form-app/styles.css`, except a minimal selector only if the native picker needs layout containment.
- `stingray_master.xlsx`, except existing generator churn from the required Stingray generation command.
- Existing export schema.
- Existing rule engine behavior.
- Existing pricing behavior.
- Existing Stingray variant IDs.
- Existing line item ordering.

## Test Plan

Run the existing project gates:

```bash
.venv/bin/python scripts/generate_stingray_form.py
node --test tests/stingray-generator-stability.test.mjs
node --test tests/stingray-form-regression.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
```

Add and run:

```bash
node --test tests/multi-model-runtime-switching.test.mjs
```

New test coverage:

- Registry contains `models.stingray` and, after activation gate, `models.grandSport`.
- Registry `defaultModelKey` is `stingray`.
- `window.STINGRAY_FORM_DATA` remains a deep-equal alias of `models.stingray.data`.
- App initialization uses Stingray by default.
- Switching to Grand Sport changes active variants from `*_c07`/`*_c67` to `*_e07`/`*_e67`.
- Switching models resets `selected`, `userSelected`, `selectedInterior`, `bodyStyle`, `trimLevel`, and `activeStep`.
- Switching models preserves `customer` fields.
- Switching back to Stingray restores Stingray default selections and no Grand Sport option IDs remain selected.
- Existing Stingray compact JSON remains unchanged apart from `submitted_at`.
- Existing Stingray plain text summary remains unchanged apart from `Submitted`.
- Grand Sport compact order title is `2027 Corvette Grand Sport`.
- Grand Sport plain text summary starts with `2027 Corvette Grand Sport`.
- Grand Sport vehicle display name comes from the Grand Sport variant.
- No Grand Sport standard equipment rows appear in a Stingray summary after switching back.

Manual verification after tests:

- Open `form-app/index.html`.
- Confirm default page is Stingray.
- Confirm picker shows `Stingray` and `Grand Sport`.
- Select Grand Sport and confirm body style/trim reset to the first Grand Sport variant.
- Select Stingray again and confirm body style/trim reset to the first Stingray variant.
- Confirm Reset still clears customer info.
- Confirm switching models preserves customer info.
- Export Stingray JSON and CSV and confirm filenames remain unchanged.
- Export Grand Sport JSON and CSV and confirm labels say Grand Sport without adding schema fields.

## Non-Goals

- Do not wire Formidable.
- Do not change export schema.
- Do not change rules engine behavior.
- Do not implement future models.
- Do not redesign UI.
- Do not change pricing behavior.
- Do not parse or infer Grand Sport rules in the runtime.
- Do not synthesize Grand Sport interiors or color overrides in the runtime.
- Do not change Stingray variant IDs.
- Do not split app data into multiple script files in Phase 6.

## Residual Risks

- Grand Sport draft data currently has deferred surfaces in tests, including rules, price rules, interiors, and color overrides. Phase 6 must not hide that. It should expose whatever the active data contains and leave full Grand Sport behavioral parity to later data-contract phases.
- Rebuilding indexes on model switch is central to safety. Missing one map, especially `rulesByTarget`, `priceRulesByTarget`, `interiorsById`, or `exclusiveGroupByOption`, can create cross-model contamination.
- Preserving customer info is safe only because customer fields are model-independent and are not used in rules or pricing. If future customer fields become model-specific, this contract should be revisited.
- Keeping one registry file is simplest now, but the file will grow as models are added. Split model files only after this behavior is proven.

## Approval Gate

Implementation should be split into small approved steps:

1. Registry output with Stingray only plus compatibility alias.
2. Runtime active-model scaffold with no visible model picker yet.
3. Minimal model picker and switch/reset behavior.
4. Grand Sport registry activation only after contract verification tests pass.
5. Final full gate run and manual browser check.

No implementation should start until this spec is approved.
