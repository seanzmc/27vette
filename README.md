# 27vette

Developer workspace for the 2027 Corvette static order-form app. The live app serves the Stingray, Grand Sport, and Z06 forms at `order.stingraychevroletcorvette.com`, supports customer build downloads, and posts active dealer submissions to Stingray Chevrolet.

## Current State

- Stingray, Grand Sport, and Z06 are live customer-facing forms in the static browser runtime.
- The app runs from `form-app/index.html`, `form-app/styles.css`, `form-app/app.js`, and generated `form-app/data.js`; there is no frontend package install or build step for the customer app.
- `form-app/data.js` exposes the active multi-model registry at `window.CORVETTE_FORM_DATA`; `window.STINGRAY_FORM_DATA` remains as a legacy compatibility alias for the Stingray dataset.
- The registry currently defaults to Stingray and contains `stingray`, `grandSport`, and `z06` model entries, each with generated model data and model-card image metadata from the workbook `asset_map` sheet.
- Runtime promotion is workbook-owned. `model_master`, `model_registry_promotion`, and `variant_master` decide which models reach the registry; `scripts/promote_model.py` applies promotion rows, and registry generation embeds promoted `*-runtime-contract.json` artifacts verbatim.
- ZR1 and ZR1X have model-scoped source sheets in the workbook but are unpromoted future models (`promoted_to_runtime` is false). They do not appear in the runtime registry.
- Dealer submission is handled in the static runtime through the WordPress endpoint `https://stingraychevroletcorvette.com/wp-json/corvette-build/v1/submit` with Cloudflare Turnstile. Do not change the endpoint, payload shape, or Turnstile behavior without explicit approval.
- `stingray_master.xlsx` is the canonical business-data workbook for active model data and generated workbook output sheets. Historical evidence sheets were extracted to `archive/stingray_archive.xlsx`.
- The repository owns business rules and runtime metadata in workbook-authored data wherever the workbook can represent them. Some Grand Sport and Z06 artifact names still carry draft/inspection wording from the migration path; inspect active registry data and tests before treating that wording as runtime status.

## Architecture

The current architecture is:

```text
stingray_master.xlsx
  -> workbook source and metadata sheets
  -> generator/inspection scripts
  -> form-output runtime-contract JSON / compatibility CSV / inspection artifacts
  -> form-app/data.js multi-model registry
  -> static browser runtime
  -> download build / submit to dealer
```

The workbook owns Corvette business data and runtime metadata wherever it can represent them: option placement, display status, selectability, variant availability, display order, descriptions, disclosures, explicit rules, rule groups, exclusive groups, package includes, price overrides, color overrides, interior data and model scoping, variant status, model assets, runtime steps, context sections, section presentation, default selections, runtime rule exceptions, order-summary grouping, and model registry promotion.

Scripts should stay procedural and general. They read workbook tables, normalize shapes, validate references, emit generated artifacts, and apply generic runtime concepts such as includes, requires, excludes, exclusivity, auto-adds, filtering, pricing, and validation. Do not add model-specific business exceptions to Python or JavaScript when the workbook can represent them.

The runtime should render and evaluate the generated contract. It should not infer Corvette ordering logic from hardcoded RPO branches unless a temporary exception is explicitly documented.

## Repository Structure

- `README.md` - project overview, architecture, local run, workflows, and roadmap.
- `AGENTS.md` - granular developer workflows, source-of-truth rules, validation gates, and handoff requirements.
- `docs/` - current planning, review, workbook editor, and ingest/schema docs. The stale workbook sheet index was archived to `docs/archive/workbook-sheet-index-2026-06-12.md`.
- `stingray_master.xlsx` - canonical workbook, source/metadata sheets, and generated `form_*` sheets.
- `form-app/` - static app shell, styles, runtime behavior, and generated data bundle.
- `form-output/` - generated Stingray JSON/CSV compatibility outputs, clean promoted runtime contracts under `form-output/runtime/`, and opt-in inspection/preview/draft artifacts under `form-output/inspection/`.
- `scripts/generate_form.py` - single model-artifact generator entry point. `--model stingray` writes Stingray JSON/CSV compatibility outputs and a clean runtime contract; `--model grand_sport` and `--model z06` write clean runtime contracts by default. Use `--emit-inspection --inspection-output <dir>` for optional inspection/preview/draft review artifacts.
- `scripts/generate_registry.py` - publishes promoted runtime artifacts from `model_registry_promotion` into `form-app/data.js`.
- `scripts/promote_model.py` - workbook-driven runtime promotion (`--model <key> --write`).
- `scripts/validate_workbook_schema.py` - workbook schema and live-contract validation.
- `scripts/validate_workbook_package.py` / `scripts/repair_workbook_tables.py` - workbook package integrity checks and table repair.
- `scripts/compare-generated-contracts.mjs` - compares generated JSON contracts while ignoring timestamp fields.
- `scripts/corvette_form_generator/` - shared model configuration, workbook I/O, runtime metadata, mapping, pricing, interiors, rules, contract, production, inspection, registry promotion, schema validation, output, and validation utilities.
- `tests/` - Node and Python tests for generated data, runtime behavior, multi-model switching, workbook schema/visual-copy standardization, Z06 promotion and rule corrections, dealer submission payloads, and workbook-owned metadata.
- `architectureAudit/` - retained audits and migration notes.
- `archive/` - extracted historical workbook evidence (`stingray_archive.xlsx`).
- `archive-2026-05-29/`, `backups/` - retained historical snapshots and workbook backups.
- `product/`, `dist_updates/` - GM product reference PDFs and distribution updates.
- `visualizer/`, `src/` - 2D visualizer scripts, exterior/wheel image assets, and the local workbook review tool under `visualizer/workbook-editor/` (separate from the order-form runtime).
- `scripts/workbook_editor_server.py` - localhost-only server for the workbook review/editing UI. See [Workbook Editor Workflow](#workbook-editor-workflow) for start, review, edit/apply, exported ops, and post-apply regeneration steps.
- `visualizer/workbook-editor/intentional-differences.json` - committed allowlist of intentional cross-model option differences consumed by the compare view (and, later, the cross-model copy-parity test). Entries carry a per-option reason and a status: `intentional` suppresses the divergence (still visible behind the "show intentional" toggle); `pending-review` annotates items awaiting a product decision (consistency-review §6 R-items).
- `scripts/apply_workbook_ops.py` - applies an exported ops.json batch through the same gated pipeline (`--write` to actually apply; default is validate + dry-run).

## Workbook Source Surfaces

The canonical workbook is `stingray_master.xlsx`. Active surfaces include shared/Stingray sheets, model-scoped sheets per model, workbook-owned runtime metadata and audit sheets, and generated output sheets.

Shared or Stingray-facing source sheets:

- `model_master`
- `model_registry_promotion`
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
- `asset_map`

Workbook-owned runtime metadata and audit sheets:

- `model_workbook_sources`
- `model_variants`
- `model_interior_scope`
- `interior_components`
- `runtime_steps`
- `context_section_master`
- `context_choice_copy`
- `section_presentation`
- `order_summary_sections`
- `step_order_summary_map`
- `default_selection_rules`
- `runtime_rule_exceptions`
- `variant_option_overrides`
- `rule_phrase_map`

Model-scoped source sheets exist for Grand Sport (`grandSport_*`) and Z06 (`z06_*`) in the active normalized workflow. ZR1 (`zr1_*`) and ZR1X (`zr1x_*`) rows/sheets are inactive historical scaffolds that should be reprocessed before they are used as ingest truth.

The active normalized model-scoped shape is:

- `<model>_options`
- `<model>_ovs`
- `<model>_rule_mapping`
- `<model>_price_rules`
- `<model>_rule_groups`
- `<model>_rule_group_members`
- `<model>_exclusive_groups`
- `<model>_exclusive_members`
- `<model>_variant_overrides`

Existing ZR1 and ZR1X scaffold rows remain unpromoted and should be treated as historical seed data until a clean reprocess/apply pass replaces or retires them.

`category_master` is not an active source sheet. Historical evidence sheets (`archive_*` and `*_raw`) were extracted to `archive/stingray_archive.xlsx` and no longer live in `stingray_master.xlsx`.

Generated runtime contracts are output surfaces and should not be edited by hand. Active runtime payloads live under `form-output/runtime/` and are published to `form-app/data.js` by `scripts/generate_registry.py`. Historical workbook `form_*` generated sheets are retired from the routine workflow; use source workbook rows plus regeneration instead of recreating or editing workbook generated sheets.

## Generated Data Contract

Each model dataset exposes a shared top-level contract:

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
- `validation`

The Stingray dataset additionally carries `runtimeRuleExceptions`. All promoted runtime models carry workbook-owned `orderSummary` metadata (`sections` and `stepMap`); browser runtime code reads that generated metadata instead of synthesizing order-summary grouping from hardcoded fallback constants. Verify the embedded contract rather than assuming non-promoted draft artifacts have the same key parity.

The app registry wraps those datasets by runtime model key and includes model-level presentation assets:

```js
window.CORVETTE_FORM_DATA = {
  defaultModelKey: "stingray",
  models: {
    stingray: { key, label, modelName, exportSlug, image_url, image_alt, image_fit, image_position, data },
    grandSport: { /* same shape */ },
    z06: { /* same shape */ }
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

When runtime behavior changes, manually verify model switching between Stingray, Grand Sport, and Z06, body style and trim selection, required step completion, option selection/deselection, standard and included equipment summaries, selected and auto-added RPO summaries, price totals, build download, dealer submission modal validation, and dealer submission payload model scoping.

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

## Workbook Editor Workflow

`scripts/workbook_editor_server.py` serves a localhost-only UI for reviewing and editing `stingray_master.xlsx`. It derives models, sheet registries, schemas, and reference domains from the live workbook (`model_master`, `model_workbook_sources`, `runtime_steps`, `section_master`, and `section_presentation`); the editor does not hardcode workbook-owned sheet relationships.

Start the editor from the repo root:

```sh
cd <repo-root>
.venv/bin/python scripts/workbook_editor_server.py
```

Open `http://127.0.0.1:8027/`. Optional flags:

```sh
.venv/bin/python scripts/workbook_editor_server.py --port 8030
.venv/bin/python scripts/workbook_editor_server.py --workbook /path/to/stingray_master.xlsx
```

Review tab:

- `/api/lints` runs informational structural lints over the current workbook state: duplicate keys, orphan references, display-order collisions and cell typing, OVS coverage, group integrity, and boolean-as-text. Lints do not gate editor applies; the batch validator remains the write authority.
- `/api/compare` compares `stingray_options`, `grandSport_options`, and `z06_options` by option ID, diffs copy/section/relative display order, and labels majority vs. deviator rows. ZR1/ZR1X scaffold sheets are excluded.
- Intentional cross-model differences live in `visualizer/workbook-editor/intentional-differences.json`. `status: intentional` suppresses a matched divergence by default; `status: pending-review` annotates items waiting for a product decision. Editing this allowlist is a normal reviewed file change, not a workbook write.

Editing and Apply behavior:

- Edits queue client-side as typed operations. Nothing touches `stingray_master.xlsx` until Apply.
- Only the model-scoped sheet families registered in `model_workbook_sources` are editable. Workbook metadata sheets and any unregistered/generated/debug sheets are read-only in the editor.
- Schema-constrained fields use pickers, enums, or typed inputs. Adding an option must include OVS coverage for every active variant of that model; the Add Option wizard and server both check this.
- Apply runs the full workbook gate internally: batch validation, dry-run on a temp copy, `validate_workbook_package`, `validate_workbook_schema`, `save_workbook_safely()` lock/mtime checks, backup, atomic replace, Excel-table ref maintenance, and an entry in `form-output/workbook-edit-log.jsonl`.
- Warnings such as display-order collisions or deleting still-referenced keys block until explicitly confirmed.

For review-then-apply workflows, export the ops batch and use the CLI wrapper. The default is validate + dry-run only:

```sh
.venv/bin/python scripts/apply_workbook_ops.py ops.json
.venv/bin/python scripts/apply_workbook_ops.py ops.json --write
.venv/bin/python scripts/apply_workbook_ops.py ops.json --write --confirm-warnings warning_id_1,warning_id_2
```

An editor Apply is only the workbook-write step. After any successful apply, regenerate the affected model artifacts, run the relevant gates below, and review diffs before treating the change as complete.

## Workbook And Generator Workflows

Stingray production refresh:

```sh
cd <repo-root>
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_registry.py
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
```

The Stingray generator reads `stingray_master.xlsx`, writes compatibility outputs at `form-output/stingray-form-data.json` and `form-output/stingray-form-data.csv`, and writes `form-output/runtime/stingray-runtime-contract.json`. It does not routinely save workbook generated sheets. `scripts/generate_registry.py` publishes the current promoted model registry to `form-app/data.js`.

Grand Sport source/runtime-contract refresh:

```sh
cd <repo-root>
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_registry.py
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
```

Z06 source/runtime-contract refresh:

```sh
cd <repo-root>
.venv/bin/python scripts/generate_form.py --model z06
.venv/bin/python scripts/generate_registry.py
node --test tests/z06-contract-preview.test.mjs
node --test tests/z06-form-data-draft.test.mjs
node --test tests/z06-interior-accessory-cleanup.test.mjs
node --test tests/z06-performance-package-interactions.test.mjs
node --test tests/z06-runtime-rule-corrections.test.mjs
```

The Grand Sport and Z06 generators build inspection/preview/draft data in memory but write only clean promoted runtime contracts under `form-output/runtime/` by default. Use `scripts/generate_form.py --model <model> --emit-inspection --inspection-output <dir>` when review artifacts are needed. `scripts/generate_registry.py` embeds the promoted `form-output/runtime/*-runtime-contract.json` artifacts verbatim; draft-only provenance never reaches `form-app/data.js`. By design, model generator runs do not directly mutate `form-app/data.js`.

Retired Grand Sport rule-audit tooling:

The former `build_rule_sources.py` report and matching optional tests were retired after they stopped protecting current runtime readiness. Use the model generator, workbook schema validation, and runtime contract tests for current Grand Sport coverage.

Runtime promotion verification / reapply (workbook-owned):

```sh
cd <repo-root>
.venv/bin/python scripts/promote_model.py --model z06 --write
.venv/bin/python scripts/generate_form.py --model z06
.venv/bin/python scripts/generate_registry.py
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
node --test tests/z06-runtime-promotion.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Z06 is already promoted in the current workbook/runtime state. Use this sequence only when promotion rows need to be verified or deliberately reapplied after workbook promotion metadata changes. Do not promote ZR1 or ZR1X as part of another model's pass unless that scope is explicitly approved.

Full default model/runtime validation:

```sh
cd <repo-root>
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/workbook-schema-standardization.test.mjs
node --test tests/workbook-visual-copy-standardization.test.mjs
node --test tests/z06-contract-preview.test.mjs
node --test tests/z06-form-data-draft.test.mjs
node --test tests/z06-runtime-promotion.test.mjs
node --test tests/z06-interior-accessory-cleanup.test.mjs
node --test tests/z06-performance-package-interactions.test.mjs
node --test tests/z06-runtime-rule-corrections.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
.venv/bin/python -m pytest tests/test_model_config_metadata.py tests/test_registry_promotion_metadata.py tests/test_schema_validation_metadata.py -q
```

## Workbook Safety

Close Excel before running a script that writes `stingray_master.xlsx`.

If `~$stingray_master.xlsx` exists, treat it as an Excel lock signal. Confirm it is stale before removing it.

If Excel reports workbook repair/recovery, stop and run:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/repair_workbook_tables.py stingray_master.xlsx
```

Workbook-writing scripts should save through `save_workbook_safely()` in `scripts/corvette_form_generator/workbook.py` so a temporary workbook is validated before replacing the source file. The helper refuses to save if the file changed after load or an Excel lock file is present. After workbook writes, verify the saved workbook on disk before claiming the change landed.

## Roadmap

- Continue moving model-specific rules, defaults, pricing exceptions, display behavior, presentation metadata, and compatibility cleanup into workbook-authored source tables.
- Keep Stingray, Grand Sport, and Z06 structurally consistent from raw source sheets through generator outputs and runtime contract.
- Complete ZR1 and ZR1X source-data review before any promotion pass; both remain unpromoted future models.
- Retire remaining draft/inspection naming only when the production promotion path and generated registry behavior are proven.
- Add and maintain image assets through workbook-authored/generated asset maps rather than hardcoded runtime references.
- Improve UX simplicity so customers see less information overload while still preserving ordering accuracy and dealer handoff detail.
- Add stronger model promotion gates for workbook validation, generated schema checks, rule coverage, pricing coverage, export payloads, and dealer submission behavior.
- Reduce remaining monolithic runtime logic once business rules and runtime metadata are fully data-owned.
