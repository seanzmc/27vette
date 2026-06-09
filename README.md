# 27vette

Developer workspace for the 2027 Corvette static order-form app. The live app serves the Stingray and Grand Sport forms at `order.stingraychevroletcorvette.com`, supports customer build downloads, and posts active dealer submissions to Stingray Chevrolet.

## Current State

- Stingray and Grand Sport are live customer-facing forms in the static browser runtime.
- The app runs from `form-app/index.html`, `form-app/styles.css`, `form-app/app.js`, and generated `form-app/data.js`; there is no frontend package install or build step for the customer app.
- `form-app/data.js` exposes the active multi-model registry at `window.CORVETTE_FORM_DATA`; `window.STINGRAY_FORM_DATA` remains as a legacy compatibility alias for the Stingray dataset.
- The registry currently defaults to Stingray and contains `stingray` and `grandSport` model entries, each with generated model data and model-card image metadata from the workbook `asset_map` sheet.
- Dealer submission is handled in the static runtime through the WordPress endpoint `https://stingraychevroletcorvette.com/wp-json/corvette-build/v1/submit` with Cloudflare Turnstile. Do not change the endpoint, payload shape, or Turnstile behavior without explicit approval.
- `stingray_master.xlsx` is the canonical business-data workbook for active model data and generated workbook output sheets.
- The repository is actively migrating business rules and runtime metadata out of Python and JavaScript and into workbook-authored data. Grand Sport is live in the runtime registry, but some Grand Sport artifact names and validation messages still carry draft/inspection wording from the migration path. Inspect active registry data and tests before treating that wording as runtime status.

## Architecture

The current architecture is:

```text
stingray_master.xlsx
  -> workbook source and metadata sheets
  -> generator/inspection scripts
  -> generated form_* workbook sheets
  -> form-output JSON/CSV/inspection artifacts
  -> form-app/data.js multi-model registry
  -> static browser runtime
  -> download build / submit to dealer
```

The workbook owns Corvette business data and runtime metadata wherever it can represent them: option placement, display status, selectability, variant availability, display order, descriptions, disclosures, explicit rules, rule groups, exclusive groups, package includes, price overrides, color overrides, interior data, variant status, model assets, runtime steps, context sections, section presentation, default selections, runtime rule exceptions, and order-summary grouping.

Scripts should stay procedural and general. They read workbook tables, normalize shapes, validate references, emit generated artifacts, and apply generic runtime concepts such as includes, requires, excludes, exclusivity, auto-adds, filtering, pricing, and validation. Do not add model-specific business exceptions to Python or JavaScript when the workbook can represent them.

The runtime should render and evaluate the generated contract. It should not infer Corvette ordering logic from hardcoded RPO branches unless a temporary exception is explicitly documented.

## Repository Structure

- `README.md` - project overview, architecture, local run, workflows, and roadmap.
- `AGENTS.md` - granular developer workflows, source-of-truth rules, validation gates, and handoff requirements.
- `codex-context.md` - short current operational context for implementation passes.
- `stingray_master.xlsx` - canonical workbook, source/metadata sheets, and generated `form_*` sheets.
- `form-app/` - static app shell, styles, runtime behavior, and generated data bundle.
- `form-output/` - generated Stingray JSON/CSV outputs plus Grand Sport inspection, contract preview, rule-audit, and draft artifacts.
- `scripts/generate_form.py` - single generator entry point for every model. `--model stingray` runs the production pathway (form sheets, output artifacts, app data registry); `--model grand_sport` and `--model z06` run the read-only inspection/draft pathway and do not mutate `form-app/data.js`.
- `scripts/build_rule_sources.py` - workbook rule-source audit helper (`--model grand_sport`).
- `scripts/promote_model.py` - workbook-driven runtime promotion (`--model <key> --write`).
- `scripts/corvette_form_generator/` - shared model configuration, workbook, runtime metadata, mapping, pricing, interiors, rules, contract, production, inspection, output, and validation utilities.
- `scripts/migrations/` - workbook metadata backfills and one-off migration helpers.
- `tests/` - Node and Python tests for generated data, runtime behavior, multi-model switching, dealer submission payloads, workbook-owned metadata, and Grand Sport draft/contract checks.
- `architectureAudit/` - retained audits and migration notes.
- `archived/` - retained historical plans, reference workbooks, skills, and deprecated source-transformation materials.

## Workbook Source Surfaces

The active workbook source surfaces include shared/Stingray sheets, Grand Sport model-scoped sheets, workbook-owned runtime metadata sheets, and generated output sheets.

Current shared or Stingray-facing sheets include:

- `variant_master`
- `section_master`
- `stingray_options`
- `stingray_ovs`
- `rule_mapping`
- `price_rules`
- `rule_groups`
- `rule_group_members`
- `exclusive_groups`
- `exclusive_group_members`
- `color_overrides`
- `lt_interiors`
- `LZ_Interiors`
- `PriceRef`

`archive_category_master` is retained as historical evidence only; `category_master` is not an active source sheet.

Grand Sport model-scoped source sheets include:

- `grandSport_options`
- `grandSport_ovs`
- `grandSport_rule_mapping`
- `grandSport_price_rules`
- `grandSport_rule_groups`
- `grandSport_rule_group_members`
- `grandSport_exclusive_groups`
- `grandSport_exclusive_members`
- `grandSport_variant_overrides`

Workbook-owned runtime/metadata sheets currently include:

- `asset_map`
- `default_selection_rules`
- `runtime_rule_exceptions`
- `order_summary_sections`
- `variant_option_overrides`
- `runtime_steps`
- `context_section_master`
- `section_presentation`

Generated sheets are output surfaces and should not be edited by hand:

- `form_steps`
- `form_context_choices`
- `form_choices`
- `form_standard_equipment`
- `form_rule_groups`
- `form_exclusive_groups`
- `form_rules`
- `form_price_rules`
- `form_interiors`
- `form_color_overrides`
- `form_validation`

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
- `defaultSelectionRules`
- `runtimeRuleExceptions`
- `orderSummary`
- `validation`

The app registry wraps those datasets by runtime model key and includes model-level presentation assets:

```js
window.CORVETTE_FORM_DATA = {
  defaultModelKey: "stingray",
  models: {
    stingray: {
      label,
      modelName,
      exportSlug,
      image_url,
      image_alt,
      image_fit,
      image_position,
      data
    },
    grandSport: {
      label,
      modelName,
      exportSlug,
      image_url,
      image_alt,
      image_fit,
      image_position,
      data
    }
  }
};

window.STINGRAY_FORM_DATA = window.CORVETTE_FORM_DATA.models.stingray.data;
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

When runtime behavior changes, manually verify model switching, body style and trim selection, required step completion, option selection/deselection, standard and included equipment summaries, selected and auto-added RPO summaries, price totals, build download, dealer submission modal validation, and dealer submission payload model scoping.

## Dependency Setup

Use the project virtual environment for Python commands:

```sh
cd <repo-root>
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Do not commit `.venv/`. Do not run workbook generators with bare system Python; use `.venv/bin/python` or activate `.venv` first.

## Workbook And Generator Workflows

Stingray production refresh:

```sh
cd <repo-root>
.venv/bin/python scripts/generate_form.py --model stingray
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
```

The Stingray generator reads `stingray_master.xlsx`, rewrites generated `form_*` sheets, writes `form-output/stingray-form-data.json`, writes `form-output/stingray-form-data.csv`, and updates `form-app/data.js`.

Grand Sport inspection and draft refresh:

```sh
cd <repo-root>
.venv/bin/python scripts/generate_form.py --model grand_sport
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/grand-sport-rule-audit.test.mjs
```

The Grand Sport generator writes inspection, contract preview, rule-audit, and draft artifacts under `form-output/inspection/`. By design, that script does not directly mutate `form-app/data.js`; production registry updates are handled by the app-data generation path.

Full model/runtime validation:

```sh
cd <repo-root>
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/grand-sport-rule-audit.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
node --test tests/audit-parser-metadata-loaders.test.mjs
.venv/bin/python -m pytest tests/test_model_config_metadata.py -q
```

## Workbook Safety

Close Excel before running a script that writes `stingray_master.xlsx`.

If `~$stingray_master.xlsx` exists, treat it as an Excel lock signal. Confirm it is stale before removing it.

If Excel reports workbook repair/recovery, stop and run:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/repair_workbook_tables.py stingray_master.xlsx
```

Workbook-writing scripts should save through the safe workbook save helper in `scripts/corvette_form_generator/workbook.py` so a temporary workbook is validated before replacing the source file. After workbook writes, verify the saved workbook on disk before claiming the change landed.

## Roadmap

- Continue moving model-specific rules, defaults, pricing exceptions, display behavior, presentation metadata, and compatibility cleanup into workbook-authored source tables.
- Keep Stingray and Grand Sport structurally consistent from raw source sheets through generator outputs and runtime contract.
- Retire remaining draft/inspection naming only when the production promotion path and generated registry behavior are proven.
- Add and maintain image assets through workbook-authored/generated asset maps rather than hardcoded runtime references.
- Improve UX simplicity so customers see less information overload while still preserving ordering accuracy and dealer handoff detail.
- Add stronger model promotion gates for workbook validation, generated schema checks, rule coverage, pricing coverage, export payloads, and dealer submission behavior.
- Reduce remaining monolithic runtime logic once business rules and runtime metadata are fully data-owned.
