# Agent Instructions for 27vette

## Spec-First Mode

Non-trivial tasks require a spec before edits. Non-trivial means touching more than one file, changing behavior, changing generated data, modifying tests/config, writing the workbook, or changing developer workflow documentation.

The spec must include:

- Diagnosis: root cause, exact files/sheets/symbols to inspect, risk level, and whether the change is behavior-only, styling-only, data-only, docs-only, or mixed.
- Exact files to change.
- Companion-file impact check: tests, generated contracts, docs/specs, gate reminders, and profile/Codex guidance that may encode the old contract; each must be marked update / inspected-no-change / not applicable.
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

## Companion-File Impact Checks

Before editing, identify companion files that may need to change with the direct target. This is required for workbook, generator, runtime, generated-contract, validation, workflow, and guidance changes.

Use this minimum matrix:

- Workbook/source-data changes: inspect affected generated runtime contracts, `form-app/data.js` when promoted data changes, model draft/preview/contract tests, count/ID expectations, and the owning spec/plan.
- Generator/registry changes: inspect generated artifacts, registry publication, schema freshness checks, generated-contract tests, and documented commands.
- Runtime behavior changes: inspect runtime tests, multi-model switching tests, generated fields consumed by runtime, build download, and dealer-submission boundaries.
- Test/gate/workflow changes: inspect this file, `27vette-gate`, workbook-editor gate reminders, and Codex/Hermes worker guidance.
- Spec/docs/guidance changes: inspect owning specs/plans and matching profile/Codex guidance when they steer future agents.

For each companion surface, report one of: updated, inspected-no-change, or not applicable with reason. Do not leave stale generated-contract counts, expected IDs, gate commands, or active approval prompts behind because they were not the primary file.

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

Workbook-owned business data includes model/body/trim/variant status, option placement, active/selectable/display behavior, display order, customer labels/descriptions/disclosures/source detail, includes/requires/excludes/groups, package auto-adds, prices/zero-price policies, color overrides, interiors/components/scope, and validation/review metadata.

Scripts should be boring. They should read workbook tables, normalize rows, validate references, emit artifacts, and apply generic runtime concepts. Avoid adding code such as "if this RPO on this model, do special behavior" when a workbook row can express the rule.

Workbook-owned does not automatically mean normalized or canonical. Exception, override, runtime-specific, and model-specific behavior sheets are architecture-risk surfaces until a review proves they are the right canonical owner. Treat sheets such as `runtime_rule_exceptions` and variant override sheets (`variant_option_overrides`, `grandSport_variant_overrides`, `z06_variant_overrides`) as surfaces requiring canonical-owner review before expansion, defense, migration, or retirement. They are not automatic deletion targets; first prove the behavior they currently own, identify the intended canonical owner, and verify parity before moving or removing rows.

Before adding a new helper module, review sheet, parallel taxonomy, or redundant column, first prove the existing workbook pipeline cannot express the decision. Prefer filling canonical workbook blanks/metadata and using current source sheets, generators, and runtime data paths over adding another intermediate layer. If an existing sheet already owns the relationship, use that sheet rather than duplicating its meaning somewhere else.

Model differences belong in model-scoped workbook rows, shared workbook metadata, or validated generated artifacts. They should not be hidden in one-off Python branches, browser JavaScript exceptions, stale audit scaffolding, or process notes that leak into runtime data.

Runtime JavaScript should render and evaluate generated data. It should not become the source of Corvette product knowledge.

If a proposed change requires hardcoded model-specific business logic, flag it before implementing.

## Active Workbook Source Surfaces

The canonical workbook is `stingray_master.xlsx`. Inspect the current workbook and metadata before editing; do not rely on stale sheet inventories.

Current active source surfaces are organized as:

- shared model/variant/section/promotion metadata, including `model_master`, `model_workbook_sources`, `model_variants`, `variant_master`, `section_master`, and `model_registry_promotion`;
- active model option, OVS/status, rule, price-rule, group/member, exclusive-group/member, and variant-override sheets for Stingray, Grand Sport, and Z06;
- shared runtime metadata such as `runtime_steps`, `context_section_master`, `context_choice_copy`, `section_presentation`, `order_summary_sections`, `step_order_summary_map`, and `default_selection_rules`;
- shared data tables such as interiors, interior components, color overrides, `PriceRef`, and `asset_map`.

`variant_master` owns variant facts and whether those facts are active/usable; `model_variants` owns model membership and generated display order. `model_registry_promotion` remains the separate browser publication decision.

Inactive or future model source sheets are outside the default runtime workflow until explicitly promoted through workbook metadata in an approved pass. Historical/archive/raw sheets are not active workflow inputs unless a scoped spec proves a current consumer.

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

Create it if needed with `python3 -m venv .venv`, activate it, then install `requirements.txt`.

Do not commit `.venv/`.

Do not run workbook generators with bare system Python. Use `.venv/bin/python` or activate `.venv` first.

## Workbook Update Workflow

Default workflow for workbook data edits: identify the business decision and owning sheet; inspect rows, headers, generator consumers, tests, and companions; write/approve a spec for non-trivial changes; make the smallest source-data edit; verify the saved workbook; regenerate artifacts; run gates; review generated diffs for unrelated drift.

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

Asset image maintenance uses `.venv/bin/python scripts/sync_asset_map.py --workbook stingray_master.xlsx --report-dir <dir>`. The retired `asset_map-Sync/asset_map_sync.py` entry point is a deprecation stub and must not contain workbook-writing logic. The safe command defaults to report-only mode, uses promoted runtime models from workbook metadata, supports deterministic `--media-url-list` validation, and may write the workbook only with `--apply` through `save_workbook_safely()`. After any real apply, validate the workbook package and schema before regenerating affected active models and the registry.

## Workbook Review & Edit Tool (dev only)

`scripts/workbook_editor_server.py` serves a localhost UI for reviewing and editing `stingray_master.xlsx`:

```sh
.venv/bin/python scripts/workbook_editor_server.py
# open http://127.0.0.1:8027/
```

The editor derives models, sheet registries, schemas, and reference domains from workbook metadata and must not hardcode workbook-owned business relationships. Treat Apply as a workbook source-data edit: validate before save, save through `save_workbook_safely()`, maintain table refs/logs, regenerate affected models, run `generate_registry.py` when promoted data changes, then run relevant gates. Lint/compare views are review aids, not replacements for generation, registry publication, or runtime tests.

## Model Generation Workflow

Use the same workflow shape for every active model:

```sh
cd <repo-root>
.venv/bin/python scripts/generate_form.py --model <model>
.venv/bin/python scripts/generate_registry.py
```

Current active model keys are `stingray`, `grand_sport`, and `z06`. `generate_form.py` reads workbook-owned source sheets and emits model artifacts; `generate_registry.py` reads promotion metadata and promoted artifacts, then writes `form-app/data.js`. Generatable models come from workbook metadata, while browser publication remains a separate `model_registry_promotion` decision.

Normal generation writes clean runtime contracts. Use `--emit-inspection --inspection-output <dir>` only when a review/spec needs optional inspection, preview, or draft artifacts:

```sh
.venv/bin/python scripts/generate_form.py --model z06 --emit-inspection --inspection-output /tmp/z06-inspection
```

Generated outputs are artifacts, not source of truth. Do not hand-edit generated workbook `form_*` sheets, `form-output/*`, or `form-app/data.js`; change workbook source rows or generic generator logic, regenerate, and review the diff.

If generation reports validation errors, stop and inspect the workbook source rows, generated validation output, and affected JSON artifact before proceeding.

Run model-focused tests after generation; pick the subset that matches the changed model and behavior surface, then broaden when generated app data, registry promotion, or runtime behavior changes:

```sh
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/z06-contract-preview.test.mjs
node --test tests/z06-form-data-draft.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

## Static App Workflow

The app currently has no package install or frontend build step.

Serve it locally with:

```sh
cd <repo-root>/form-app
../.venv/bin/python -m http.server 8000
```

Open `http://localhost:8000`.

For runtime changes, verify model switching, body/trim selection, required-step completion, option select/deselect, summaries, price totals, build download, dealer modal validation, and dealer payload model scoping.

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

Full current default suite: run the workbook schema validator, all model-focused Node tests listed above plus `tests/workbook-schema-standardization.test.mjs`, `tests/workbook-visual-copy-standardization.test.mjs`, `tests/z06-runtime-promotion.test.mjs`, and the Python metadata tests (`tests/test_model_config_metadata.py`, `tests/test_registry_promotion_metadata.py`, `tests/test_schema_validation_metadata.py`). Run Node files sequentially.

## Boundaries

- Do not alter live app behavior during documentation or workbook-only passes.
- Do not add new dependencies unless the user explicitly approves them.
- Do not refactor runtime structure as part of a data cleanup unless the refactor is separately scoped and approved.
- Do not hide workbook data problems in scripts.
- Do not expand hardcoded model-specific Python or JavaScript behavior.
- Do not stage temporary workbooks, Excel lock files, backups, or unrelated generated output.
- Do not claim workbook changes landed until the saved file has been verified on disk.
