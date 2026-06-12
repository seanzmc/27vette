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
- `asset_map`

`category_master` is not an active source sheet. Historical evidence sheets (`archive_*` and `*_raw`, including `archive_category_master`) were extracted to `archive/stingray_archive.xlsx` and no longer live in `stingray_master.xlsx`.

Current workbook-owned runtime metadata and audit sheets include:

- `model_workbook_sources`
- `model_variants`
- `model_interior_scope`
- `interior_components`
- `rule_phrase_map`
- `option_audit_groups`
- `option_audit_group_members`
- `rule_review_groups`

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

For workbook schema and live-contract validation, run:

```sh
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

To compare generated JSON contracts while ignoring timestamp fields, run:

```sh
node scripts/compare-generated-contracts.mjs before.json after.json
```

## Workbook Review & Edit Tool (dev only)

`scripts/workbook_editor_server.py` serves a localhost UI for reviewing and editing `stingray_master.xlsx`:

```sh
.venv/bin/python scripts/workbook_editor_server.py
# open http://127.0.0.1:8027/
```

It derives models, sheet registries, schemas, and reference domains live from the workbook (`model_master`, `model_workbook_sources`, `runtime_steps`, `section_master`/`section_presentation`); nothing is hardcoded that a workbook sheet owns.

Write path (Phase 2, see `workbook-editor-phase2-spec.md`):

- Edits queue client-side as typed ops; nothing touches the workbook until Apply.
- Only the 11 model-scoped sheet families registered in `model_workbook_sources` are editable. Generated `form_*` sheets and metadata sheets are read-only.
- Schema-constrained fields are pickers/enums/typed inputs, never free text. Adding an option requires an OVS status for every active variant of the model (the Add Option wizard enforces this; the server re-checks).
- Every apply runs the full gate internally: batch validation (refs, coverage, group integrity, duplicate keys), a dry-run on a temp copy that must pass `validate_workbook_package` + `validate_workbook_schema`, then `save_workbook_safely()` (lock/mtime checks, backup, atomic replace), Excel-table ref maintenance, and a line in the committed `form-output/workbook-edit-log.jsonl`.
- Warnings (display-order collisions, deleting still-referenced keys) block until explicitly confirmed.
- `scripts/apply_workbook_ops.py ops.json [--write] [--confirm-warnings ids] [--allow-stale]` applies an exported batch through the identical pipeline for review-then-apply workflows.

An editor apply is steps 4–5 of the Workbook Update Workflow above, nothing more: regenerate affected artifacts and run the model's gates afterward exactly as for a hand edit. The UI prints the gate commands after each apply.

Review tab (Phase 3, see `workbook-editor-phase3-spec.md`) — read-only:

- `GET /api/lints` runs structural lints over the *current* workbook state (duplicate keys, orphan refs, display-order collisions, display-order cell typing, OVS coverage, group integrity, boolean-as-text). Lints are informational and never gate applies; the Phase 2 batch validator remains the write authority. Lint logic lives in `scripts/corvette_form_generator/editor_lints.py` and is generic over `EDITOR_SHEET_META` — no model/RPO-specific exceptions in code.
- `GET /api/compare` joins `stingray_options`/`grandSport_options`/`z06_options` by `option_id` (RPO fallback for the known Z06 `_002` keys), diffs name/description/section/relative display order, and labels majority vs deviator. Scaffold models (ZR1/ZR1X) are excluded.
- Intentional model differences live in the committed `visualizer/workbook-editor/intentional-differences.json` with per-entry reasons. `status: intentional` suppresses a matched divergence (visible behind the "show intentional" toggle); `status: pending-review` annotates consistency-review §6 items awaiting a product decision. Entries that no longer match any divergence surface as stale. Editing the allowlist is a normal code-reviewed file change, not a workbook write.
- Tests: `tests/test_editor_lints.py` pins the lints/compare to named findings of `workbook-consistency-review-2026-06-11.md` and must stay green against the real workbook.

## Stingray Generator Workflow

Current default command from the repo root:

```sh
cd <repo-root>
.venv/bin/python scripts/generate_form.py --model stingray
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
.venv/bin/python scripts/generate_form.py --model grand_sport
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
.venv/bin/python scripts/generate_form.py --model z06
```

Current expected outputs under `form-output/inspection/`:

- `z06-inspection.json`
- `z06-inspection.md`
- `z06-contract-preview.json`
- `z06-contract-preview.md`
- `z06-form-data-draft.json`
- `z06-form-data-draft.md`
- `z06-runtime-contract.json` (clean contract embedded verbatim by registry promotion)

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
.venv/bin/python scripts/promote_model.py --model z06 --write
.venv/bin/python scripts/generate_form.py --model z06
.venv/bin/python scripts/generate_form.py --model stingray
```

`scripts/promote_model.py --model z06` updates only Z06 rows in `model_master`, `model_registry_promotion`, and the six Z06 rows in `variant_master`. It must use `save_workbook_safely()`, refuse to run while an Excel lock file exists, and verify the saved workbook rows on disk.

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
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
```

Grand Sport source/draft refresh:

```sh
.venv/bin/python scripts/generate_form.py --model grand_sport
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/grand-sport-rule-audit.test.mjs
node --test tests/audit-parser-metadata-loaders.test.mjs
```

Z06 source/draft refresh:

```sh
.venv/bin/python scripts/generate_form.py --model z06
node --test tests/z06-contract-preview.test.mjs
node --test tests/z06-form-data-draft.test.mjs
node --test tests/z06-interior-accessory-cleanup.test.mjs
node --test tests/z06-performance-package-interactions.test.mjs
node --test tests/z06-runtime-rule-corrections.test.mjs
```

Z06 runtime promotion:

```sh
.venv/bin/python scripts/promote_model.py --model z06 --write
.venv/bin/python scripts/generate_form.py --model z06
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
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
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/grand-sport-rule-audit.test.mjs
node --test tests/audit-parser-metadata-loaders.test.mjs
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
