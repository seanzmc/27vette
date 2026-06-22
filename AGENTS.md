# Agent Instructions for 27vette

## Spec-First Mode

Non-trivial tasks require a spec before edits. Non-trivial means touching more than one file, changing behavior, changing generated data, modifying tests/config, writing the workbook, or changing developer workflow documentation.

The spec must include:

- Diagnosis: root cause, exact files/sheets/symbols to inspect, risk level, and whether the change is behavior-only, styling-only, data-only, docs-only, or mixed.
- Exact files to change.
- Constraints repeated back, including visual preservation, no refactor, no new dependencies, workbook source-of-truth rules, and any explicit user boundaries.
- Risks and non-goals.
- Validation plan.

Wait for approval before implementing. Cite concrete files, workbook sheets, symbols, and code paths. Evidence beats assumption. If a request is risky, split it into smaller approved steps.

## Handoff For Every Task

Every handoff must report:

- What changed: files, workbook sheets, generated artifacts, and behavior impact.
- What did not change: preserved runtime behavior, visual constraints, schemas, deployment paths, and any explicitly excluded work.
- Gate results: typecheck, lint, tests, generator runs, workbook validation, or `not run` with a reason.
- Manual verification still pending, residual risks, and follow-up work.
- Next step guidance: a brief recommended next pass when the task is part of an active multi-pass pathway. Tie the recommendation to current repo evidence, plans/specs, and user-stated goals. If the task is isolated or there is no clear safe continuation, say that no obvious next pass is implied rather than inventing work.

For multi-pass work, keep the broader path visible without expanding the current scope. The next-step guidance should name the logical next pass, not implement it, unless the user explicitly approves that pass.

## Spec and Plan Closure

When completing an approved spec, pass, or implementation plan, update the owning spec/plan file before final handoff. Mark it implemented or completed with the completion date, changed files/sheets/artifacts, gate results, and any residual follow-up.

If a standing reference document or route map would otherwise become stale, either update that document in the same pass or clearly name it as intentionally stale/deferred in the completed spec and handoff. Do not leave active approval prompts, "spec only" status, or obsolete next-step claims in completed spec files unless they are explicitly rewritten as historical context.

## Using This File

Treat this file as the current operating guide, not a freeze on the repo's implementation. Safety rules, source-of-truth rules, generated-file ownership, dealer submission boundaries, and validation gates are strict. Current architecture notes, active sheet lists, named workflow paths, and expected outputs are checkpoints to verify against the repo before acting.

If a task intentionally migrates away from a documented workflow, call that out in the spec, inspect the current scripts/tests/artifacts first, and update this file only when the new workflow is proven.

## Current Architecture

The live customer app is a static Corvette order-form runtime for Stingray, Grand Sport, and Z06. It is deployed at `order.stingraychevroletcorvette.com` and supports active dealer submissions.

The current default architecture is workbook-to-runtime for every active model:

```text
stingray_master.xlsx
  -> workbook source tables for the selected model
  -> scripts/generate_form.py --model <model>
  -> model runtime artifacts under form-output/runtime/
  -> scripts/generate_registry.py
  -> form-app/data.js
  -> form-app static runtime
  -> build download / dealer submission
```

`form-app/data.js` exposes `window.CORVETTE_FORM_DATA` with model entries for Stingray, Grand Sport, and Z06. `window.STINGRAY_FORM_DATA` remains as a compatibility alias.

The workflow contract is the same for each active model: workbook source rows own the product data and business rules, generators emit model artifacts from those rows, the registry publisher writes the browser data bundle, and runtime JavaScript evaluates the generated contract. Do not create or preserve separate model-specific workflow paths unless the user explicitly approves that as a temporary technical exception with a validation plan.

## Business Rule Philosophy

The workbook owns Corvette product data and business rules.

Workbook-owned business data includes:

- model, body style, trim, and variant status
- option placement and section ownership
- active/selectable/display behavior
- display order
- customer-facing labels, descriptions, disclosures, and raw source detail
- explicit includes, requires, excludes, grouped requirements, and exclusive groups
- package includes and auto-add behavior
- price overrides and zero-price package policies
- color overrides
- interior availability, components, and model scoping
- validation and review metadata

Scripts should be boring. They should read workbook tables, normalize rows, validate references, emit artifacts, and apply generic runtime concepts. Avoid adding code such as "if this RPO on this model, do special behavior" when a workbook row can express the rule.

Before adding a new helper module, review sheet, parallel taxonomy, or redundant column, first prove the existing workbook pipeline cannot express the decision. Prefer filling canonical workbook blanks/metadata and using current source sheets, generators, and runtime data paths over adding another intermediate layer. If an existing sheet already owns the relationship, use that sheet rather than duplicating its meaning somewhere else.

Model differences belong in model-scoped workbook rows, shared workbook metadata, or validated generated artifacts. They should not be hidden in one-off Python branches, browser JavaScript exceptions, stale audit scaffolding, or process notes that leak into runtime data.

Runtime JavaScript should render and evaluate generated data. It should not become the source of Corvette product knowledge.

If a proposed change requires hardcoded model-specific business logic, flag it before implementing.

## Active Workbook Source Sheets

The canonical workbook is `stingray_master.xlsx`.

Current shared/base sheets include:

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

`category_master` is not an active source sheet. Historical evidence sheets (`archive_*` and `*_raw`, including `archive_category_master`) were extracted to `archive/stingray_archive.xlsx` and no longer live in `stingray_master.xlsx`.

Current workbook-owned runtime metadata and audit sheets include:

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

Current Grand Sport model-scoped sheets include:

- `grandSport_options`
- `grandSport_ovs`
- `grandSport_rule_mapping`
- `grandSport_price_rules`
- `grandSport_rule_groups`
- `grandSport_rule_group_members`
- `grandSport_exclusive_groups`
- `grandSport_exclusive_members`
- `grandSport_variant_overrides`

Current Z06 model-scoped sheets include:

- `z06_options`
- `z06_ovs`
- `z06_rule_mapping`
- `z06_price_rules`
- `z06_rule_groups`
- `z06_rule_group_members`
- `z06_exclusive_groups`
- `z06_exclusive_members`
- `z06_variant_overrides`

Inactive or future model source sheets are outside the default runtime workflow until explicitly promoted through workbook metadata in an approved pass.

Active runtime contracts are generated under `form-output/runtime/` and published to the browser registry through `scripts/generate_registry.py`. Historical workbook `form_*` generated sheets are not part of the routine runtime workflow and should not be recreated or hand-edited unless a separately approved opt-in debug/export pass defines a named consumer.

Raw GM order-guide ingest is an edge workflow for new-model intake or broad source refreshes, not routine workbook maintenance. Use `Order-Guide_IngestPrompt.md` and `docs/ingest/` for that preflight path; raw ingest should emit transient candidates under `form-output/ingest/<run-id>/` and must not write `stingray_master.xlsx`, generated outputs, or promoted runtime data without a later approved apply pass.

## Workbook Safety

Close Excel before running any script that writes `stingray_master.xlsx`.

Do not ignore `~$stingray_master.xlsx`. It means Excel has or recently had the workbook open. Confirm it is stale before removing it.

If Excel shows a repair/recovery prompt, stop and run:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/repair_workbook_tables.py stingray_master.xlsx
```

Workbook-writing scripts must save through `save_workbook_safely()` in `scripts/corvette_form_generator/workbook.py`. The helper validates a temporary workbook package before replacing the source workbook and refuses to save if the file changed after load or an Excel lock file is present.

After any workbook write, reopen the saved workbook or inspect it with `openpyxl` and verify the expected sheet headers/cells on disk before claiming the change landed.

## Dependency Setup

Use the project virtual environment for Python commands.

Create it if needed:

```sh
cd <repo-root>
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Do not commit `.venv/`.

Do not run workbook generators with bare system Python. Use `.venv/bin/python` or activate `.venv` first.

## Workbook Update Workflow

Use this current default workflow for workbook data edits:

1. Identify the business decision and the workbook sheet that should own it.
2. Inspect existing rows, headers, generator consumers, and tests before editing.
3. Write a spec and get approval for non-trivial changes.
4. Make the smallest workbook/source-data edit possible.
5. Verify the workbook saved on disk.
6. Regenerate the affected artifacts.
7. Run targeted tests first, then broader gates if generated app data or runtime behavior changed.
8. Review diffs so generated artifacts do not hide unrelated workbook or runtime changes.

Do not solve bad source data by suppressing it in Python or JavaScript. Correct the workbook row unless there is a documented reason not to.

Do not add an extra module, staging sheet, review taxonomy, or duplicate scope column when an existing workbook sheet already carries the relationship. Use the current pipeline first: fill the canonical blank cells, source rows, membership rows, or scope rows that the generator already reads. Add a new layer only after documenting why the existing workbook contract cannot represent the decision.

Do not edit generated `form_*` sheets directly or recreate them for routine generation. Change source sheets, then regenerate runtime artifacts.

For workbook schema and live-contract validation, run:

```sh
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

To compare generated JSON contracts while ignoring timestamp fields, run:

```sh
node scripts/compare-generated-contracts.mjs before.json after.json
```

Asset image maintenance has a separate documented helper at `asset_map-Sync/asset_map_sync.py`. Until an approved pass aligns its write path with the workbook safety contract and project dependencies, treat it as a dry-run/report tool only:

```sh
.venv/bin/python asset_map-Sync/asset_map_sync.py --workbook stingray_master.xlsx --report-dir /tmp/asset-map-sync
```

TODO: Decide whether `asset_map_sync.py --apply` should be migrated to `save_workbook_safely()` before it becomes part of routine workbook maintenance.

## Workbook Review & Edit Tool (dev only)

`scripts/workbook_editor_server.py` serves a localhost UI for reviewing and editing `stingray_master.xlsx`:

```sh
.venv/bin/python scripts/workbook_editor_server.py
# open http://127.0.0.1:8027/
```

The editor derives models, sheet registries, schemas, and reference domains from workbook metadata such as `model_master`, `model_workbook_sources`, `runtime_steps`, `section_master`, and `section_presentation`. It should not hardcode business relationships that the workbook owns.

Editor writes follow the same safety contract as hand edits:

- Queue typed operations client-side; do not touch the workbook until Apply.
- Edit source sheets through workbook metadata. Generated `form_*` sheets are outputs and remain read-only.
- Validate references, OVS coverage, group integrity, duplicate keys, display-order collisions, and stale references before save.
- Save through `save_workbook_safely()`, maintain Excel table refs, and write the workbook edit log.
- Treat an editor apply as a workbook source-data edit only. Regenerate affected model artifacts with `scripts/generate_form.py --model <model>`, then run `scripts/generate_registry.py` and the relevant gates.

Editor lint/compare views are review aids. They can surface workbook drift, but they do not replace source-data validation, generation, registry publication, or runtime tests.

## Model Generation Workflow

Use the same workflow shape for every active model:

```sh
cd <repo-root>
.venv/bin/python scripts/generate_form.py --model <model>
.venv/bin/python scripts/generate_registry.py
```

Current active model keys are:

- `stingray`
- `grand_sport`
- `z06`

`scripts/generate_form.py --model <model>` reads the model's workbook-owned source sheets and emits the model artifacts. `scripts/generate_registry.py` reads workbook promotion metadata and promoted model artifacts, then writes `form-app/data.js` for the browser runtime.

Active generatable model keys are discovered from workbook metadata, not a hardcoded CLI list. Activating a future model requires complete active workbook source and variant metadata; publishing it to the browser remains a separate `model_registry_promotion` decision.

Normal generation writes clean runtime contracts. Use `--emit-inspection --inspection-output <dir>` only when a review/spec needs optional inspection, preview, or draft artifacts:

```sh
.venv/bin/python scripts/generate_form.py --model z06 --emit-inspection --inspection-output /tmp/z06-inspection
```

Generated outputs are artifacts, not source of truth. Do not hand-edit generated workbook `form_*` sheets, `form-output/*`, or `form-app/data.js`; change workbook source rows or generic generator logic, regenerate, and review the diff.

If generation reports validation errors, stop and inspect the workbook source rows, generated validation output, and affected JSON artifact before proceeding.

Run model-focused tests after generation:

```sh
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/z06-contract-preview.test.mjs
node --test tests/z06-form-data-draft.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Pick the subset that matches the changed model and behavior surface, then run broader gates when generated app data, registry promotion, or runtime behavior changes.

## Static App Workflow

The app currently has no package install or frontend build step.

Serve it locally with:

```sh
cd <repo-root>/form-app
../.venv/bin/python -m http.server 8000
```

Open `http://localhost:8000`.

For runtime changes, verify:

- model switching between Stingray, Grand Sport, and Z06
- body style and trim selection
- required step completion
- option select/deselect behavior
- standard and included equipment summary
- selected and auto-added RPO summaries
- price totals
- build download
- dealer submission modal validation
- dealer submission payload model scoping

The dealer submission runtime posts to:

```text
https://stingraychevroletcorvette.com/wp-json/corvette-build/v1/submit
```

Do not change endpoint, payload shape, or Turnstile behavior without explicit approval.

## Validation Gates

Use these as current default readiness gates. Existing tests/docs are not proof that a gate is required: classify a gate as default only when failure indicates live runtime risk, generated runtime-contract risk, workbook schema/source-contract risk, model promotion risk, or dealer payload risk. Report/audit drift belongs in the optional audit/report block unless a spec documents the exact runtime-contract failure it uniquely catches.

Docs-only changes:

```sh
git diff -- AGENTS.md README.md docs
rg -n "stale text or deprecated claim" AGENTS.md README.md docs
```

Stingray data refresh:

```sh
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_registry.py
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
```

Grand Sport data refresh:

```sh
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_registry.py
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
```

Retired Grand Sport audit/report tooling:

The former `build_rule_sources.py` report and matching optional tests are no longer current workflow tools. Do not use them as validation gates; use the model generator, workbook schema validation, and runtime contract tests for Grand Sport readiness.

Optional inspection/preview/draft artifact refresh:

```sh
.venv/bin/python scripts/generate_form.py --model grand_sport --emit-inspection --inspection-output /tmp/grand-sport-inspection
.venv/bin/python scripts/generate_form.py --model z06 --emit-inspection --inspection-output /tmp/z06-inspection
```

Use optional inspection output only for review/spec work that needs those artifacts. Do not check in temp inspection output unless the approved pass names it as an expected artifact.

Z06 data refresh:

```sh
.venv/bin/python scripts/generate_form.py --model z06
.venv/bin/python scripts/generate_registry.py
node --test tests/z06-contract-preview.test.mjs
node --test tests/z06-form-data-draft.test.mjs
node --test tests/z06-interior-accessory-cleanup.test.mjs
node --test tests/z06-performance-package-interactions.test.mjs
node --test tests/z06-runtime-rule-corrections.test.mjs
```

Runtime or multi-model behavior:

```sh
node --test tests/stingray-form-regression.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Full current default suite:

```sh
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

## Boundaries

- Do not alter live app behavior during documentation or workbook-only passes.
- Do not add new dependencies unless the user explicitly approves them.
- Do not refactor runtime structure as part of a data cleanup unless the refactor is separately scoped and approved.
- Do not hide workbook data problems in scripts.
- Do not expand hardcoded model-specific Python or JavaScript behavior.
- Do not stage temporary workbooks, Excel lock files, backups, or unrelated generated output.
- Do not claim workbook changes landed until the saved file has been verified on disk.
