# Token Use and Codex Rate-Limit Spec

## Diagnosis

This project now has two distinct operating modes, and token-saving guidance should preserve that split:

- Production app/workbook mode: `stingray_master.xlsx`, `scripts/generate_stingray_form.py`, `form-output/`, and `form-app/data.js` remain production surfaces unless a task explicitly approves changing them.
- CSV-shadow migration mode: `data/stingray/**/*.csv`, `scripts/stingray_csv_first_slice.py`, `scripts/stingray_csv_shadow_overlay.py`, `tests/stingray/*`, and `build/experimental/form-app/` are the active migration/control-plane surfaces.

Evidence from the current workflow docs:

- `Codex Pickup.md` says the latest pass was Pass 102, a control-plane validation pass for structured non-choice references and interior source namespaces.
- `Chat Pickup.md` says production behavior remains the oracle, there is no source switch/cutover yet, and CSV projection is shadow/experimental only.
- `schema-refactor.md` describes the long-term target: `data/stingray/**/*.csv` plus `data/stingray/datapackage.yaml` become canonical, with the workbook demoted only after parity and cutover.

Evidence from the current codebase:

- `data/stingray/` already contains 23 CSV files under `catalog/`, `logic/`, `pricing/`, `ui/`, and `validation/`.
- `data/stingray/validation/projected_slice_ownership.csv` has 208 lines and records projected-owned, production-guarded, and preserved cross-boundary ownership.
- `scripts/stingray_csv_first_slice.py` loads the CSV package and emits a legacy production-shaped fragment.
- `scripts/stingray_csv_shadow_overlay.py` overlays projected CSV slices onto production data and validates ownership boundaries.
- `docs/stingray-experimental-app-smoke.md` explicitly says the experimental app shell is not CSV cutover and must not replace production `form-app/data.js`.

Risk level: low for this documentation update; medium for future prompt/context changes that blur production-oracle work with CSV-shadow migration work.

Scope type: workflow/spec guidance only. This file does not change app behavior, workbook generation, CSV data, schemas, tests, or generated artifacts.

## Exact Files To Change

Changed for this request:

- `tokenUse.md`

Potential future changes after approval:

- `AGENTS.md`
- `data/stingray/AGENTS.md`
- `scripts/AGENTS.md`
- `tests/stingray/AGENTS.md`
- `form-app/AGENTS.md`
- `docs/AGENTS.md`
- `archived/AGENTS.md`

## Constraints

- Preserve production behavior as the oracle.
- Do not treat CSV-shadow output as production cutover.
- Do not copy `build/experimental/form-app/data.js` into `form-app/data.js`.
- Do not migrate interiors unless explicitly approved.
- Do not create fake selectables or manifest rows for `3LT_*` interior source IDs.
- Keep rule-only legacy IDs guarded only when they are option-like legacy references.
- Preserve ownership categories: projected-owned, production-guarded, and preserved cross-boundary.
- Use evidence/spec-first passes before implementation.
- For implementation passes, use focused RED-first tests and preserve unrelated importer/schema work.
- Use `.venv/bin/python` for project Python commands.
- Do not add dependencies or refactor code as part of token-use work.

## Application Plan

### 1. Control Prompt Size

Use mode-specific prompts. The cheapest useful prompt is not just short; it names the correct surface and excludes the wrong one.

Recommended prompt pattern:

```text
Task: <one concrete outcome>
Mode: <production app/workbook | CSV-shadow migration | docs-only | evidence-only>
Scope: <specific files or folders>
Do not touch: <known off-limits areas>
Validation: <exact command>
Output: <expected artifact or answer format>
```

Project-specific examples:

- CSV-shadow evidence pass: point Codex at `Codex Pickup.md`, `Chat Pickup.md`, `data/stingray/validation/projected_slice_ownership.csv`, the relevant `tests/stingray/*` file, and the narrow function or validator in `scripts/stingray_csv_shadow_overlay.py`.
- CSV-shadow implementation pass: name the pass, the projected RPO/ownership boundary, the exact CSV files, the focused test file, and whether production artifacts are out of scope.
- Production app UI pass: point Codex at `form-app/index.html`, `form-app/styles.css`, `form-app/app.js`, and only the relevant data slice. Say explicitly whether `form-app/data.js` is generated-only or editable for that task.
- Workbook/generator pass: point Codex at `scripts/generate_stingray_form.py`, the relevant helper under `scripts/corvette_form_generator/`, and the exact generated output contract under `form-output/`.
- Docs-only pass: keep the scope to the named markdown files and say whether the answer should patch files or report findings only.
- Archived-material review: explicitly include `archived/`; otherwise keep it out of context.

Non-goals:

- Do not ask Codex to re-read the whole migration history when the pickup docs identify the current pass.
- Do not load entire generated outputs when a header, count, one RPO slice, or one validator function will answer the question.
- Do not collapse production and shadow validation into one broad prompt unless the task is a cutover-readiness review.

### 2. Reduce and Nest AGENTS.md Context

The root `AGENTS.md` is currently compact, but the current workflow would benefit from nested files if the repo keeps expanding. Nesting should mirror operating mode, not just folder ownership.

Recommended structure:

- Root `AGENTS.md`: keep universal conduct, spec-first rules, repo-wide safety rules, project venv requirement, and the warning that production behavior is the oracle.
- `data/stingray/AGENTS.md`: CSV package conventions, ownership-manifest rules, projected-owned/production-guarded/preserved cross-boundary definitions, no fake `3LT_*` selectables, and no cutover claims.
- `scripts/AGENTS.md`: Python command rules, generator vs shadow-overlay boundaries, and the rule that `scripts/generate_stingray_form.py` is production unless explicitly approved.
- `tests/stingray/AGENTS.md`: focused Node test commands, RED-first control-plane pattern, shadow parity expectations, and the distinction between focused pass tests and the full Stingray ladder.
- `form-app/AGENTS.md`: production app constraints, static no-build workflow, generated `data.js` caution, and manual/browser verification expectations.
- `docs/AGENTS.md`: documentation-only constraints, especially preserving stated plan and separating future target architecture from current migration state.
- `archived/AGENTS.md`: traceability-only warning and instruction not to use archived files as active source unless explicitly requested.

Risk:

- Over-nesting can hide global safety rules. Keep spec-first, venv use, production-oracle status, and no-cutover defaults in the root file.

Approval needed before implementation:

- Any actual `AGENTS.md` split should be a separate approved change because it changes default Codex context injection for future tasks.

### 3. Limit MCP Servers

Routine CSV-shadow migration work should not load broad MCP context. The current workflow is mostly filesystem inspection plus project-local Python and Node tests.

Recommended defaults:

- Use no MCP server for docs-only, evidence-only, CSV header inspection, ownership-manifest inspection, or focused Node/Python validation.
- Enable browser tooling only for `form-app/` behavior or `build/experimental/form-app/` smoke checks.
- Enable spreadsheet tooling only for direct workbook inspection or mutation of `stingray_master.xlsx`.
- Disable unrelated connectors such as email, calendar, slides, design tools, and external document connectors during normal generator, app, CSV-shadow, test, or documentation work.

Project-specific MCP use:

- Static production app verification: browser tool is useful after changes to `form-app/index.html`, `form-app/styles.css`, or `form-app/app.js`.
- Experimental app verification: browser tool is useful after running `scripts/build_stingray_experimental_app.py`, but this still does not imply cutover.
- Workbook verification: spreadsheet tooling can be useful for direct sheet inspection, but generator validation should still use the project venv and regression tests.
- CSV-shadow validation: prefer `.venv/bin/python scripts/stingray_csv_first_slice.py`, `.venv/bin/python scripts/stingray_csv_shadow_overlay.py`, and `node --test tests/stingray/...`.

Risk:

- Disabling spreadsheet or browser tools saves context, but do not skip them when the requested result depends on cell-level workbook fidelity or visual/runtime app behavior.

### 4. Switch To A Smaller Model For Routine Tasks

Use smaller models only when the task boundary is tight and the validation gate is objective.

Good candidates for GPT-5.4 or GPT-5.4-mini:

- Documentation edits to `README.md`, `docs/`, pickup docs, or narrowly scoped markdown files.
- CSV header/count inspection.
- Mechanical additions to one already-patterned CSV row family after the spec is approved.
- Focused test selector updates.
- Running known validation commands and summarizing results.
- Single-file evidence reports with an explicit output format.

Keep a larger model for:

- Schema/refactor plan reconciliation across `schema-refactor.md`, pickup docs, CSV data, overlay code, and tests.
- Ownership-boundary decisions in `projected_slice_ownership.csv`.
- Any pass involving `production_guarded`, `preserved_cross_boundary`, rule-only IDs, or interior source namespaces.
- Workbook-generation logic in `scripts/generate_stingray_form.py`.
- Cross-surface changes involving CSV data, overlay output, experimental app data, and shadow parity tests.
- Ambiguous Corvette rule interpretation from workbook/order-guide data.
- Any actual cutover-readiness or canonical-source decision.

Risk:

- Smaller models can save rate-limit budget but are more likely to flatten the current transitional plan into the future target architecture. Do not use them for decisions about cutover, schema ownership, interior migration, or rule semantics.

## Drift Flags From Current State

These flags compare the current codebase and CSV migration progress with `Codex Pickup.md`, `Chat Pickup.md`, and `schema-refactor.md`.

### No Current Drift Found

- The codebase still treats CSV as shadow/experimental. `docs/stingray-experimental-app-smoke.md` says the experimental shell does not change production `form-app/data.js` and is not cutover.
- `scripts/stingray_csv_shadow_overlay.py` overlays projected CSV slices onto production-shaped data instead of replacing production generation.
- Pass 102 intent appears represented in code/tests: structured non-choice references now classify as active choice, production guarded, interior source, or unresolved.
- Current validation evidence shows structured references are allowed with no unresolved refs: active choice `503`, production guarded `43`, interior source `45`, unresolved `0`.
- Focused namespace tests passed: `tests/stingray/interior-source-namespace-control-plane.test.mjs` and `tests/stingray/structured-reference-namespace-report.test.mjs` both passed.
- Current CSV fragment validation emitted `validation_errors: []`.

### Planned Gaps, Not Drift Yet

These are differences from the final `schema-refactor.md` target, but the pickup docs say there is no cutover yet, so they should not be treated as failures by themselves:

- No `data/stingray/datapackage.yaml` exists yet.
- No `data/stingray/meta/` directory exists yet.
- No `data/stingray/support/` directory exists yet.
- No `data/stingray/ui/steps.csv` or `data/stingray/ui/sections.csv` exists yet; `ui/selectable_display.csv` still carries section/category/step fields directly.
- No `pricing/price_lookup_tables.csv` or `pricing/price_lookup_rows.csv` exists yet.
- `scripts/stingray_csv_first_slice.py` still has a hard-coded `TABLES` map and custom validation rather than Frictionless Table Schema validation.
- `scripts/stingray_csv_first_slice.py` supports only a subset of the planned condition engine: `context eq`, `selected is_true`, and `selected_any_in_set is_true`.
- The CSV package includes current migration/control-plane tables such as `logic/rule_groups.csv`, `logic/rule_group_members.csv`, and `validation/projected_slice_ownership.csv`, which are not the whole final schema but are consistent with the shadow migration approach.

### Watch Items

These are not proven drift now, but they are places where future passes could drift from the intended plan:

- Any prompt or implementation that says `data/stingray/**/*.csv` is already canonical would conflict with the pickup docs.
- Any change that writes shadow output into production `form-app/data.js` would conflict with the no-cutover plan.
- Any addition of `3LT_*` rows as fake selectables or production-guarded options would conflict with Pass 102.
- Any broad migration of interiors would conflict with the current "no interior migration yet" direction.
- Any migration pass that removes preserved cross-boundary rows before both source and target are projected-owned would conflict with current ownership policy.
- Any recommendation to shrink context by ignoring `projected_slice_ownership.csv` during CSV-shadow work would be unsafe; that file is central to the current migration control plane.
- Any recommendation to use smaller models for schema-plan reconciliation or ownership decisions would be unsafe.

## Recommended Operating Rules

1. Start every non-trivial prompt with the operating mode: production app/workbook, CSV-shadow migration, docs-only, or evidence-only.
2. For CSV-shadow work, include the current pickup doc and the narrow ownership/test/code surface; exclude production app/generator files unless the pass explicitly needs comparison.
3. For production work, say whether CSV-shadow files are out of scope.
4. Exclude `archived/`, generated outputs, and large data files unless they are directly relevant.
5. Inspect headers, symbols, counts, or one RPO slice before loading entire generated files.
6. Use repo-native validation commands instead of broad exploratory checks.
7. Treat `form-app/data.js`, `form-output/`, and `build/experimental/` as generated artifacts unless the task explicitly says otherwise.
8. Use browser and spreadsheet MCPs only when their output is needed for the task result.
9. Reserve larger models for schema/refactor reconciliation, ownership semantics, interior namespace handling, and cutover decisions.

## Validation Plan

For this documentation-only spec:

- Confirm `tokenUse.md` exists at the repository root.
- Review the file for references to concrete project paths and the current pickup/refactor plan.
- No generator, app, workbook, or full regression test command is required because no executable behavior changed.

For future CSV-shadow implementation passes:

- Run the focused new or changed `tests/stingray/*` test first.
- Run adjacent control-plane tests when ownership, rule-only IDs, or interior source namespaces are involved.
- Run the full Stingray ladder before claiming pass completion when behavior or broad migration surfaces changed.
- Run `git diff --check`.

For future production generator/app changes:

- Use `.venv/bin/python scripts/generate_stingray_form.py` when the generator is changed or generated artifacts must be refreshed.
- Run `node --test tests/stingray-form-regression.test.mjs`.
- Add browser/manual checks only when user-facing app behavior or visuals changed.

## Handoff Template For Token-Saving Changes

Use this handoff format after future token-use changes:

```text
What changed:
- <files and context/behavior impact>

What did not change:
- <preserved app, workbook, schema, validation, visual, production-oracle, or no-cutover behavior>

Gate results:
- <typecheck/lint/test/doc review commands, or "not run: documentation-only">

Manual verification pending:
- <remaining checks or "none">
```
