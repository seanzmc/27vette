# Token Use and Codex Rate-Limit Spec

## Diagnosis

This project has a compact root `AGENTS.md`, but Codex sessions can still become token-heavy because the repository mixes active runtime files, generated artifacts, workbook outputs, archived materials, tests, and import-review scaffolding in one workspace.

Evidence:

- `AGENTS.md` is only 46 lines, but it applies globally to every task in the repository.
- `README.md` identifies the active app surface as `form-app/`, the active workbook workflow as `stingray_master.xlsx`, `scripts/generate_stingray_form.py`, and `form-output/`, and the archive surface as `archived/`.
- `scripts/generate_stingray_form.py` and `tests/stingray-form-regression.test.mjs` are both large files, so loading them casually is expensive.
- `form-app/data.js`, `form-output/stingray-form-data.json`, and `form-output/stingray-form-data.csv` are generated or embedded data surfaces that should be inspected narrowly.
- `archived/` is retained for traceability and should not be pulled into routine tasks unless the task explicitly concerns archived planning, skills, or source-transformation material.

Risk level: low for documentation and workflow changes; medium if prompt-size practices cause an agent to miss relevant generated-data context during workbook or app-generation tasks.

Scope type: behavior-only workflow guidance. This spec does not require code, visual, dependency, schema, workbook, or test behavior changes.

## Exact Files To Change

Required for this request:

- `tokenUse.md`

Potential future changes after approval:

- `AGENTS.md`
- `form-app/AGENTS.md`
- `scripts/AGENTS.md`
- `tests/AGENTS.md`
- `archived/AGENTS.md`
- `docs/AGENTS.md`

## Constraints

- Preserve the current static app behavior in `form-app/`.
- Preserve workbook generation behavior in `scripts/generate_stingray_form.py`.
- Preserve generated contract schemas in `form-output/`.
- Do not add dependencies.
- Do not refactor code as part of token-use work.
- Keep validation commands aligned with the existing root instructions: use `.venv/bin/python scripts/generate_stingray_form.py` for generator runs and `node --test tests/stingray-form-regression.test.mjs` for the core regression gate.
- Prefer repo evidence over broad assumptions.

## Application Plan

### 1. Control Prompt Size

Apply this by making Codex prompts task-shaped instead of project-shaped.

Recommended prompt pattern:

```text
Task: <one concrete outcome>
Scope: <specific files or folders>
Do not touch: <known off-limits areas>
Validation: <exact command>
Output: <expected artifact or answer format>
```

Project-specific examples:

- For app UI work, point Codex at `form-app/index.html`, `form-app/styles.css`, `form-app/app.js`, and only the relevant slice of `form-app/data.js`.
- For workbook generation work, point Codex at `scripts/generate_stingray_form.py`, the relevant helper under `scripts/corvette_form_generator/`, and the exact generated file in `form-output/`.
- For regression work, name the smallest relevant test file first, such as `tests/stingray-form-regression.test.mjs` or one specific file under `tests/stingray/`.
- For archived-material review, explicitly say when `archived/` is in scope; otherwise keep it out of context.

Non-goal:

- Do not replace precision with underspecified prompts. Short prompts should still identify the target files, constraints, and validation gate.

### 2. Reduce and Nest AGENTS.md Context

The current root `AGENTS.md` is small enough to keep, but it mixes universal behavior rules, Python environment rules, generator rules, dependency setup, and validation instructions. If this project grows further, nesting can keep routine sessions from injecting instructions that do not apply.

Recommended structure:

- Root `AGENTS.md`: keep only universal conduct, repo-wide safety rules, and the minimum virtual-environment warning.
- `scripts/AGENTS.md`: generator-specific Python commands, workbook mutation cautions, and script-validation expectations.
- `form-app/AGENTS.md`: static-app constraints, no-build-step reminder, generated `data.js` caution, and browser/manual verification expectations.
- `tests/AGENTS.md`: Node test commands and rules for adding focused regression tests.
- `archived/AGENTS.md`: traceability-only warning and instruction not to use archived files as active source unless explicitly requested.
- `docs/AGENTS.md`: documentation-only constraints, especially when preserving wording or structure.

Risk:

- Over-nesting can hide important global rules from sessions that start at the repo root. Keep any rule that applies everywhere in the root file.

Approval needed before implementation:

- Any actual `AGENTS.md` split should be a separate approved change because it changes default Codex context injection for future tasks.

### 3. Limit MCP Servers

This project usually does not need broad MCP context for routine changes. Most work can be done with filesystem inspection, shell commands, and targeted browser verification.

Recommended defaults:

- Enable browser tooling only when checking `form-app/index.html`, local static serving, screenshots, or manual UI behavior.
- Enable spreadsheet tooling only for direct workbook inspection or mutation of `stingray_master.xlsx`.
- Disable unrelated connectors such as email, calendar, slides, and design tools during normal generator, app, test, or documentation work.
- Avoid loading browser or spreadsheet MCPs for simple text-only documentation tasks like this file.

Project-specific MCP use:

- Static app verification: browser tool is useful after changes to `form-app/index.html`, `form-app/styles.css`, or `form-app/app.js`.
- Workbook verification: spreadsheet tooling can be useful for direct sheet inspection, but generator validation should still use the project venv and regression tests.
- Repository documentation: no MCP server should be required unless the doc references an external or connected artifact.

Risk:

- Disabling spreadsheet or browser tools can save context, but do not skip them when the requested output depends on visual behavior or workbook cell-level fidelity.

### 4. Switch To A Smaller Model For Routine Tasks

Use smaller models for bounded, low-risk tasks where the repo context is clear and the expected output is mechanical.

Good candidates for GPT-5.4 or GPT-5.4-mini:

- Documentation edits to `README.md`, `docs/`, or narrowly scoped new markdown files.
- Mechanical test selector updates.
- Small copy edits in `form-app/`.
- Single-file inspections with an explicit output format.
- Running known validation commands and summarizing results.

Keep a larger model for:

- Workbook-generation logic in `scripts/generate_stingray_form.py`.
- Schema contract changes affecting `form-output/`.
- Cross-file behavior changes involving `form-app/app.js`, generated data, and tests.
- Ambiguous rule interpretation from workbook data.
- Any task where preserving the exact order-form mental model is central.

Risk:

- Smaller models can save rate-limit budget but may be more likely to overgeneralize workbook or rule semantics. Use them only when the task has tight boundaries and the validation gate is objective.

## Recommended Operating Rules

1. Start every non-trivial prompt with the exact file or folder scope.
2. Exclude `archived/`, generated outputs, and large data files unless they are directly relevant.
3. Ask Codex to inspect headers, symbols, or narrow ranges before reading entire generated files.
4. Use repo-native validation commands instead of broad exploratory checks.
5. Treat `form-app/data.js` and `form-output/` as generated artifacts unless the task explicitly asks to inspect or compare them.
6. Use browser and spreadsheet MCPs only when their output is needed for the task result.
7. Reserve larger models for workbook semantics, generated contract changes, and cross-surface behavior.

## Validation Plan

For this documentation-only spec:

- Confirm `tokenUse.md` exists at the repository root.
- Review the file for references to concrete project paths.
- No generator, app, workbook, or regression test command is required because no executable behavior changed.

For any future implementation of nested `AGENTS.md` files:

- Re-read each `AGENTS.md` after editing.
- Confirm root instructions still contain repo-wide safety rules.
- Run no code gates unless generator, app, or test files also changed.

## Handoff Template For Token-Saving Changes

Use this handoff format after future token-use changes:

```text
What changed:
- <files and context/behavior impact>

What did not change:
- <preserved app, workbook, schema, validation, visual, or test behavior>

Gate results:
- <typecheck/lint/test/doc review commands, or "not run: documentation-only">

Manual verification pending:
- <remaining checks or "none">
```
