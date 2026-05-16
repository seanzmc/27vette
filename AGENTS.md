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

## Current Architecture

The live customer app is a static Corvette order-form runtime for Stingray and Grand Sport. It is deployed at `order.stingraychevroletcorvette.com` and supports active dealer submissions.

The architecture is:

```text
stingray_master.xlsx
  -> workbook source tables
  -> generator/inspection scripts
  -> generated form_* workbook sheets
  -> form-output artifacts
  -> form-app/data.js
  -> form-app static runtime
  -> build download / dealer submission
```

`form-app/data.js` exposes `window.CORVETTE_FORM_DATA` with model entries for Stingray and Grand Sport. `window.STINGRAY_FORM_DATA` remains as a compatibility alias.

The project is transitioning to workbook-owned business logic. Grand Sport is further along in model-scoped workbook tables; Stingray still has some transitional generator/runtime logic. Do not expand those transitional seams unless explicitly approved.

## Business Rule Philosophy

Business rules belong in the workbook whenever the workbook can represent them.

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

Scripts should be boring. They should read tables, normalize rows, validate references, emit artifacts, and apply generic runtime concepts. Avoid adding code such as "if this RPO on this model, do special behavior" when a workbook row can express the rule.

Runtime JavaScript should render and evaluate generated data. It should not become the source of Corvette product knowledge.

If a proposed change requires hardcoded model-specific business logic, flag it before implementing.

## Active Workbook Source Sheets

The canonical workbook is `stingray_master.xlsx`.

Shared or Stingray-facing sheets include:

- `variant_master`
- `category_master`
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

Grand Sport model-scoped sheets include:

- `grandSport_options`
- `grandSport_ovs`
- `grandSport_rule_mapping`
- `grandSport_price_rules`
- `grandSport_rule_groups`
- `grandSport_rule_group_members`
- `grandSport_exclusive_groups`
- `grandSport_exclusive_members`
- `grandSport_variant_overrides`

Generated sheets are written by the generator and should not be edited manually:

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

Use this workflow for workbook data edits:

1. Identify the business decision and the workbook sheet that should own it.
2. Inspect existing rows, headers, generator consumers, and tests before editing.
3. Write a spec and get approval for non-trivial changes.
4. Make the smallest workbook/source-data edit possible.
5. Verify the workbook saved on disk.
6. Regenerate the affected artifacts.
7. Run targeted tests first, then broader gates if generated app data or runtime behavior changed.
8. Review diffs so generated artifacts do not hide unrelated workbook or runtime changes.

Do not solve bad source data by suppressing it in Python or JavaScript. Correct the workbook row unless there is a documented reason not to.

Do not edit generated `form_*` sheets directly. Change source sheets, then regenerate.

## Stingray Generator Workflow

Run from the repo root:

```sh
cd <repo-root>
.venv/bin/python scripts/generate_stingray_form.py
```

Expected outputs:

- generated `form_*` sheets in `stingray_master.xlsx`
- `form-output/stingray-form-data.json`
- `form-output/stingray-form-data.csv`
- `form-app/data.js`

Then run:

```sh
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
```

If the generator reports validation errors, stop and inspect `form_validation` and the JSON output before proceeding.

## Grand Sport Generator Workflow

Run from the repo root:

```sh
cd <repo-root>
.venv/bin/python scripts/generate_grand_sport_form.py
```

Expected outputs under `form-output/inspection/`:

- `grand-sport-inspection.json`
- `grand-sport-inspection.md`
- `grand-sport-contract-preview.json`
- `grand-sport-contract-preview.md`
- `grand-sport-form-data-draft.json`
- `grand-sport-form-data-draft.md`

This script is intentionally non-mutating for `form-app/data.js`. When a change is intended to update live app data, follow the production app-data generation path and verify the registry in `form-app/data.js`.

Then run:

```sh
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/grand-sport-rule-audit.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Some Grand Sport artifact names and metadata still reflect the inspection/draft migration path. Do not infer production status from naming alone; inspect the active registry, tests, and deployment intent.

## Static App Workflow

The app has no package install or frontend build step.

Serve it locally with:

```sh
cd <repo-root>/form-app
../.venv/bin/python -m http.server 8000
```

Open `http://localhost:8000`.

For runtime changes, verify:

- model switching between Stingray and Grand Sport
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

Docs-only changes:

```sh
git diff -- README.md AGENTS.md codex-context.md
rg -n "stale text or deprecated claim" README.md AGENTS.md codex-context.md
```

Stingray data refresh:

```sh
.venv/bin/python scripts/generate_stingray_form.py
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
```

Grand Sport source/draft refresh:

```sh
.venv/bin/python scripts/generate_grand_sport_form.py
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/grand-sport-rule-audit.test.mjs
```

Runtime or multi-model behavior:

```sh
node --test tests/stingray-form-regression.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Full current suite:

```sh
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/grand-sport-rule-audit.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

## Boundaries

- Do not alter live app behavior during documentation or workbook-only passes.
- Do not add new dependencies unless the user explicitly approves them.
- Do not refactor runtime structure as part of a data cleanup unless the refactor is separately scoped and approved.
- Do not hide workbook data problems in scripts.
- Do not expand hardcoded model-specific Python or JavaScript behavior.
- Do not stage temporary workbooks, Excel lock files, backups, or unrelated generated output.
- Do not claim workbook changes landed until the saved file has been verified on disk.
