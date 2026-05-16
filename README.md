# 27vette

Developer workspace for the 2027 Corvette static order-form app. The live app serves the Stingray and Grand Sport forms at `order.stingraychevroletcorvette.com`, supports customer build downloads, and posts active dealer submissions to Stingray Chevrolet.

## Current State

- Stingray and Grand Sport are live customer-facing forms.
- The browser app is static: `form-app/index.html`, `form-app/styles.css`, `form-app/app.js`, and generated `form-app/data.js`.
- `form-app/data.js` exposes a multi-model registry at `window.CORVETTE_FORM_DATA`; `window.STINGRAY_FORM_DATA` remains as a legacy Stingray alias.
- Dealer submission is handled in the static runtime through the WordPress endpoint `https://stingraychevroletcorvette.com/wp-json/corvette-build/v1/submit` with Cloudflare Turnstile.
- `stingray_master.xlsx` is the canonical business-data workbook for active model data and generated workbook output sheets.
- The repository is actively migrating business rules out of Python and JavaScript and into workbook-authored data. Grand Sport is further along in the model-scoped workbook migration; Stingray still has some transitional generator/runtime helpers that should be retired through focused follow-up passes.

## Architecture

The intended architecture is:

```text
stingray_master.xlsx
  -> workbook source sheets
  -> boring generator/inspection scripts
  -> generated form_* workbook sheets
  -> form-output/*.json and *.csv
  -> form-app/data.js
  -> static browser runtime
  -> download build / submit to dealer
```

The workbook owns Corvette business data: option placement, display status, selectability, variant availability, display order, descriptions, disclosures, explicit rules, rule groups, exclusive groups, package includes, price overrides, color overrides, interior data, and variant status.

Scripts should stay procedural and general. They read workbook tables, normalize shapes, validate references, emit generated artifacts, and apply generic runtime concepts such as includes, requires, excludes, exclusivity, auto-adds, filtering, pricing, and validation. Do not add model-specific business exceptions to Python or JavaScript when the workbook can represent them.

The runtime should render and evaluate the generated contract. It should not infer Corvette ordering logic from hardcoded RPO branches unless a temporary exception is explicitly documented.

## Repository Structure

- `README.md` - project overview, architecture, local run, and roadmap.
- `AGENTS.md` - granular developer workflows and source-of-truth rules.
- `codex-context.md` - current operational context for short implementation passes.
- `stingray_master.xlsx` - canonical workbook and generated `form_*` sheets.
- `form-app/` - static app shell, styles, runtime behavior, and generated data bundle.
- `form-output/` - generated JSON/CSV outputs plus Grand Sport inspection artifacts.
- `scripts/generate_stingray_form.py` - production generator that writes Stingray form sheets, Stingray output artifacts, and the app data registry.
- `scripts/generate_grand_sport_form.py` - Grand Sport inspection/draft generator; it writes inspection artifacts and does not directly mutate `form-app/data.js`.
- `scripts/build_grand_sport_rule_sources.py` - Grand Sport workbook rule-source audit helper.
- `scripts/corvette_form_generator/` - shared model configuration, workbook, mapping, inspection, output, and validation utilities.
- `tests/` - Node test suite for generated data, runtime behavior, multi-model switching, dealer submission payloads, and Grand Sport draft/contract checks.
- `spec-review/` and `architectureAudit/` - active specs, audits, and migration notes.
- `archived/` - retained historical plans, reference workbooks, skills, and deprecated source-transformation materials.

## Generated Data Contract

Each model dataset is expected to expose the same top-level contract:

- `dataset`
- `variants`
- `steps`
- `sections`
- `contextChoices`
- `choices`
- `standardEquipment`
- `ruleGroups`
- `exclusiveGroups`
- `rules`
- `priceRules`
- `interiors`
- `colorOverrides`
- `validation`

The app registry wraps those datasets by model key:

```js
window.CORVETTE_FORM_DATA = {
  defaultModelKey: "stingray",
  models: {
    stingray: { label, modelName, exportSlug, data },
    grandSport: { label, modelName, exportSlug, data }
  }
};
```

## Local App Run

The app can be opened directly in a browser:

```text
form-app/index.html
```

For local browser verification, serve the static folder:

```sh
cd <repo-root>/form-app
../.venv/bin/python -m http.server 8000
```

Open `http://localhost:8000`.

## Dependency Setup

Use the project virtual environment for Python commands:

```sh
cd <repo-root>
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Do not commit `.venv/`.

## Workbook And Generator Workflows

Stingray production refresh:

```sh
cd <repo-root>
.venv/bin/python scripts/generate_stingray_form.py
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
```

The Stingray generator reads `stingray_master.xlsx`, rewrites generated `form_*` sheets, writes `form-output/stingray-form-data.json`, writes `form-output/stingray-form-data.csv`, and updates `form-app/data.js`.

Grand Sport inspection and draft refresh:

```sh
cd <repo-root>
.venv/bin/python scripts/generate_grand_sport_form.py
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
```

The Grand Sport generator writes inspection and draft artifacts under `form-output/inspection/`. By design, that script does not directly mutate `form-app/data.js`; production registry updates are handled by the app-data generation path.

Full model/runtime validation:

```sh
cd <repo-root>
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/grand-sport-rule-audit.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

## Workbook Safety

Close Excel before running a script that writes `stingray_master.xlsx`.

If `~$stingray_master.xlsx` exists, treat it as an Excel lock signal. Confirm it is stale before removing it.

If Excel reports workbook repair/recovery, stop and run:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/repair_workbook_tables.py stingray_master.xlsx
```

Workbook-writing scripts should save through the safe workbook save helper so a temporary workbook is validated before replacing the source file.

## Roadmap

- Continue moving model-specific rules, defaults, pricing exceptions, display behavior, and compatibility cleanup into workbook-authored source tables.
- Keep Stingray and Grand Sport structurally consistent from raw source sheets through generator outputs and runtime contract.
- Add image assets to selectable options through a workbook-authored or generated asset map rather than hardcoded runtime references.
- Improve UX simplicity so customers see less information overload while still preserving ordering accuracy and dealer handoff detail.
- Add stronger model promotion gates for workbook validation, generated schema checks, rule coverage, pricing coverage, export payloads, and dealer submission behavior.
- Reduce remaining monolithic runtime logic once business rules are fully data-owned.
