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

For active migration legs such as adding Z06/ZR1/ZR1X to the form runtime, keep the broader path visible without expanding the current scope. The next-step guidance should name the logical next pass, not implement it, unless the user explicitly approves that pass.

## Using This File

Treat this file as the current operating guide, not a freeze on the repo's implementation. Safety rules, source-of-truth rules, generated-file ownership, dealer submission boundaries, and validation gates are strict. Current architecture notes, active sheet lists, named workflow paths, and expected outputs are checkpoints to verify against the repo before acting.

If a task intentionally migrates away from a documented workflow, call that out in the spec, inspect the current scripts/tests/artifacts first, and update this file only when the new workflow is proven.

## Current Architecture

The live customer app is currently a static Corvette order-form runtime for Stingray, Grand Sport, and Z06. It is deployed at `order.stingraychevroletcorvette.com` and supports active dealer submissions.

The current default architecture is:

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

`form-app/data.js` currently exposes `window.CORVETTE_FORM_DATA` with model entries for Stingray, Grand Sport, and Z06. `window.STINGRAY_FORM_DATA` remains as a compatibility alias.

The project is transitioning to workbook-owned business logic. Some model-specific migration status may drift as work lands, so verify the current workbook sheets, generator code, runtime registry, and tests before assuming one model's workflow applies to another. Do not expand transitional generator/runtime seams unless explicitly approved.

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

Before adding a new helper module, review sheet, parallel taxonomy, or redundant column, first prove the existing workbook pipeline cannot express the decision. Prefer filling canonical workbook blanks/metadata and using current source sheets, generators, and runtime data paths over adding another intermediate layer. If an existing sheet already owns the relationship, use that sheet rather than duplicating its meaning somewhere else.

Runtime JavaScript should render and evaluate generated data. It should not become the source of Corvette product knowledge.

If a proposed change requires hardcoded model-specific business logic, flag it before implementing.

## Active Workbook Source Sheets

The canonical workbook is `stingray_master.xlsx`.

Current shared or Stingray-facing sheets include:

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

`archive_category_master` is retained as historical evidence only; `category_master` is not an active source sheet.

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

Current generated sheets are written by the generator and should not be edited manually:

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

Do not edit generated `form_*` sheets directly. Change source sheets, then regenerate.

## Stingray Generator Workflow

Current default command from the repo root:

```sh
cd <repo-root>
.venv/bin/python scripts/generate_stingray_form.py
```

Current expected outputs:

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

Current default command from the repo root:

```sh
cd <repo-root>
.venv/bin/python scripts/generate_grand_sport_form.py
```

Current expected outputs under `form-output/inspection/`:

- `grand-sport-inspection.json`
- `grand-sport-inspection.md`
- `grand-sport-contract-preview.json`
- `grand-sport-contract-preview.md`
- `grand-sport-form-data-draft.json`
- `grand-sport-form-data-draft.md`

This script is currently intentionally non-mutating for `form-app/data.js`. When a change is intended to update live app data, inspect the current production app-data generation path and verify the registry in `form-app/data.js`.

Then run:

```sh
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/grand-sport-rule-audit.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Some Grand Sport artifact names and metadata still reflect the inspection/draft migration path. Do not infer production status from naming alone; inspect the active registry, tests, and deployment intent.

## Z06 Generator Workflow

Current read-only preview/draft command from the repo root:

```sh
cd <repo-root>
.venv/bin/python scripts/generate_z06_form.py
```

Current expected outputs under `form-output/inspection/`:

- `z06-inspection.json`
- `z06-inspection.md`
- `z06-contract-preview.json`
- `z06-contract-preview.md`
- `z06-form-data-draft.json`
- `z06-form-data-draft.md`

This script must not mutate `form-app/data.js` or write `stingray_master.xlsx`.

Then run:

```sh
node --test tests/z06-contract-preview.test.mjs
node --test tests/z06-form-data-draft.test.mjs
```

## Z06 Runtime Promotion Workflow

Use the workbook-owned promotion path when Z06 runtime activation needs to be applied or verified:

```sh
cd <repo-root>
.venv/bin/python scripts/promote_z06_runtime.py --write
.venv/bin/python scripts/generate_z06_form.py
.venv/bin/python scripts/generate_stingray_form.py
```

`scripts/promote_z06_runtime.py` updates only Z06 rows in `model_master`, `model_registry_promotion`, and the six Z06 rows in `variant_master`. It must use `save_workbook_safely()`, refuse to run while an Excel lock file exists, and verify the saved workbook rows on disk.

After promotion or regeneration, run:

```sh
node --test tests/z06-runtime-promotion.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Do not promote ZR1 or ZR1X as part of a Z06 pass unless that scope is explicitly approved.

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

Use these as current default gates. If the relevant scripts, tests, or artifacts have changed, identify the replacement gates in the spec and explain why they supersede the commands below.

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

Z06 source/draft refresh:

```sh
.venv/bin/python scripts/generate_z06_form.py
node --test tests/z06-contract-preview.test.mjs
node --test tests/z06-form-data-draft.test.mjs
```

Z06 runtime promotion:

```sh
.venv/bin/python scripts/promote_z06_runtime.py --write
.venv/bin/python scripts/generate_z06_form.py
.venv/bin/python scripts/generate_stingray_form.py
node --test tests/z06-runtime-promotion.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
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
node --test tests/z06-contract-preview.test.mjs
node --test tests/z06-form-data-draft.test.mjs
node --test tests/z06-runtime-promotion.test.mjs
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
