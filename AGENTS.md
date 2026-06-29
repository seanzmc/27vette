# Agent Operating Guide for 27vette

This file is the durable operating guide for AI agents working in this repository. It explains how to act safely across bug fixes, feature expansion, documentation updates, workbook/data maintenance, generated artifacts, and UI/UX styling for the static Corvette order-form application.

Use `README.md` for the broad project overview. Use this file for source-of-truth boundaries, workflow expectations, validation strategy, and handoff requirements. If this guide and the live repo disagree, inspect the code, workbook, tests, and docs before acting; then call out the discrepancy in the spec or handoff.

## 1. First Principles

Checklist before any task:

- [ ] Treat this file as an operating guide, not a frozen implementation map.
- [ ] Verify the current repo state before relying on remembered architecture, old plans, or generated artifacts.
- [ ] Check git status before editing and avoid overwriting user-owned work.
- [ ] Classify the request by changed surface: docs, styling, runtime behavior, workbook/data, generator/tooling, validation/tests, ingest/review, or mixed.
- [ ] Inspect relevant source files, tests, docs, scripts, generated artifacts, and workbook metadata before changing anything.
- [ ] Prefer evidence from the current repo over stale plans, archived reports, or old agent context.
- [ ] Keep changes scoped. Do not mix unrelated refactors, data cleanup, UI redesign, or generated-output refreshes into a task unless approved.

This repository supports a customer-facing order-form application. Preserve live-customer behavior, generated-data contracts, and dealer-submission boundaries unless the user explicitly approves a change to those surfaces.

## 2. High-Level Architecture

The system is a workbook-to-runtime static app pipeline:

1. The canonical workbook (`stingray_master.xlsx`) stores Corvette product data, business rules, presentation metadata, model/variant metadata, asset metadata, and publication decisions where the workbook can represent them.
2. Python scripts read, validate, normalize, and transform workbook data into generated artifacts.
3. Generated runtime artifacts are written under generated-output locations such as `form-output/`.
4. Registry/publication tooling packages promoted generated artifacts into the static app data bundle (`form-app/data.js`).
5. The static app (`form-app/index.html`, `form-app/styles.css`, `form-app/app.js`, and generated `form-app/data.js`) renders and operates the customer-facing form in the browser.
6. The browser runtime supports model selection, configuration choices, summaries, pricing, build download, and dealer-submission flow.

When working on a task, trace the path from source to consumer:

- [ ] Workbook/source data: what row, sheet, or metadata owns the fact?
- [ ] Generator/tooling: what script reads or transforms it?
- [ ] Generated artifact: what contract/data bundle exposes it?
- [ ] Runtime: what HTML/CSS/JS consumes or presents it?
- [ ] Tests/docs: what existing checks or guidance encode the expected behavior?

Keep architecture descriptions structural and durable. Do not rely on temporary branches, run IDs, line numbers, or current-pass implementation history.

## 3. Source-of-Truth Boundaries

Use the right ownership surface before editing.

### Workbook-owned data and rules

The workbook is the canonical source for product and business data when it can express the decision. Workbook-owned information may include:

- model, body, trim, variant, and publication metadata;
- option placement, availability, selectability, display status, and display order;
- customer-facing names, descriptions, disclosures, source details, and visual-copy metadata;
- includes, requires, excludes, groups, exclusive groups, package auto-adds, and default selections;
- prices, price overrides, zero-price policies, colors, interiors, components, and assets;
- runtime metadata such as steps, sections, summaries, context copy, and validation/review metadata.

Checklist for workbook/data changes:

- [ ] Identify the business decision and the workbook surface that should own it.
- [ ] Inspect workbook metadata and current rows before assuming a sheet is active or canonical.
- [ ] Prefer fixing source workbook data over suppressing bad data in Python or JavaScript.
- [ ] Do not add duplicate sheets, columns, helper modules, or review taxonomies until the existing workbook contract has been proven insufficient.

### Generated artifacts

Generated outputs are artifacts, not source of truth. This includes generated runtime contracts, compatibility outputs, inspection/review outputs, and the published browser data bundle.

- [ ] Do not hand-edit generated outputs as a fix.
- [ ] If generated output is wrong, inspect workbook source data and generator logic.
- [ ] Regenerate affected artifacts after source or generator changes.
- [ ] Review generated diffs for intended changes and unrelated drift.

### Python scripts

Python should be boring and general. It should read workbook/source inputs, normalize data, validate references, emit artifacts, publish registries, or safely apply approved workbook edits.

- [ ] Avoid hardcoded model-specific business exceptions when the workbook can express the rule.
- [ ] Keep script behavior generic unless a scoped spec documents why a special case is necessary.
- [ ] Inspect script help, docs, and current implementation before using uncommon flags or assuming invocation details.

### Runtime JavaScript

Runtime JavaScript should consume generated data, render the form, manage interactions, apply generic validation/selection behavior, build summaries, handle model switching, create downloads, and manage dealer-submission UI.

- [ ] Do not make JavaScript a hidden product-rule database.
- [ ] If runtime code appears to need product knowledge, first check whether that knowledge belongs in workbook data or generated metadata.
- [ ] Protect generated data contracts and dealer-submission payload semantics.

### Styling

CSS owns presentation: layout, spacing, typography, responsive behavior, visual hierarchy, and affordances.

- [ ] Styling-only changes must preserve generated data, runtime state, validation semantics, payloads, and behavior.
- [ ] Do not use styling changes to hide broken data or broken runtime logic.

## 4. Spec-First Expectations

Non-trivial tasks require a spec before edits. Non-trivial includes:

- touching more than one meaningful surface;
- changing runtime behavior;
- writing the workbook;
- changing generated data or generated-data contracts;
- modifying tests, validation gates, scripts, config, or developer workflow documentation;
- changing dealer-submission behavior or payloads;
- making broad UI/UX changes;
- adding dependencies or changing build/deployment assumptions.

A spec must include:

- [ ] Diagnosis: root cause or current-state evidence, exact files/sheets/symbols inspected, risk level, and change class.
- [ ] Exact files, workbook sheets, generated artifacts, or docs expected to change.
- [ ] Source-of-truth decision: workbook, generator, generated artifact, runtime, styling, docs, or tooling.
- [ ] Companion-file impact check: updated, inspected-no-change, or not applicable for relevant companion surfaces.
- [ ] Constraints: no unrelated refactor, no new dependencies unless approved, generated files are not source, workbook owns business rules where possible, preserve dealer-submission boundaries, and any user-specific boundaries.
- [ ] Risks and non-goals.
- [ ] Validation plan matched to the changed surfaces and risk.

Wait for approval before implementing a spec unless the user explicitly asks only for analysis or a content plan. For small isolated docs/typo changes, keep the checklist lightweight but still inspect current files and report validation honestly.

## 5. Context Gathering Before Edits

Before editing:

- [ ] Check git status and identify existing user changes.
- [ ] Read the direct target file and nearby files.
- [ ] Search for relevant symbols, fields, RPOs, sheet names, selectors, endpoints, test names, and docs references.
- [ ] Trace data from definition to use instead of guessing shapes or imports.
- [ ] Inspect project manifests or neighboring imports before assuming a dependency is available.
- [ ] For workbook tasks, inspect current workbook metadata and generator consumers.
- [ ] For runtime tasks, inspect generated data consumed by the runtime.
- [ ] For docs/guidance tasks, inspect README and active docs for consistency.

Do not invent files, scripts, APIs, sheet ownership, selectors, test names, or generated contract fields. If the repo can answer the question, inspect it.

## 6. Script and Tooling Roles by Intent

Describe scripts by purpose, input category, output category, and mutation boundary. Do not treat this guide as a command reference; inspect script help, README, docs, and tests for current invocations.

Stable script categories:

- Model artifact generation: reads workbook source/metadata for a selected model and emits generated runtime artifacts.
- Registry publication: reads workbook publication metadata and generated runtime artifacts, then writes the browser data bundle.
- Workbook schema/source-contract validation: checks workbook shape, references, and contract expectations.
- Workbook package integrity and repair: validates or repairs workbook packaging/table integrity without inventing product data.
- Workbook review/edit tooling: provides local review and approved apply paths for workbook source-data edits.
- Asset maintenance: validates or updates workbook-owned asset metadata through approved workbook-write paths.
- Generated contract comparison: compares generated outputs while ignoring intentional volatile fields.
- Raw order-guide ingest preflight/review: reads raw source evidence and emits transient review artifacts.

Checklist when using scripts:

- [ ] Identify whether the script is read-only, writes generated artifacts, writes the workbook, or publishes runtime data.
- [ ] Use the project virtual environment for Python tooling unless current docs say otherwise.
- [ ] Do not run workbook-writing scripts while Excel has the workbook open.
- [ ] Verify outputs on disk before claiming a write landed.
- [ ] If a script changes behavior, update or run tests that cover the changed intent.
- [ ] If examples are needed in docs or specs, label them as examples and direct agents to current script help/docs for exact flags.

## 7. Workbook Safety and Data Maintenance

Workbook writes require extra care because `stingray_master.xlsx` is the canonical business-data source.

Checklist for workbook writes:

- [ ] Confirm the task is approved and the owning workbook surface is identified.
- [ ] Confirm Excel is closed before writing the workbook.
- [ ] Treat workbook lock files as active-risk signals; do not ignore them.
- [ ] Use approved workbook-write tooling or code paths that save safely and validate the workbook package before replacing the source.
- [ ] After writing, verify the saved workbook on disk by reopening or inspecting expected sheets/headers/cells.
- [ ] Regenerate affected generated artifacts and published data when promoted runtime data changes.
- [ ] Run validation based on changed surfaces.
- [ ] Do not claim workbook changes landed until saved file verification is complete.

Do not recreate or hand-edit generated workbook sheets as routine workflow. Change workbook source rows or generic generator logic, then regenerate artifacts.

## 8. Generated Artifacts and Registry Publication

Generated outputs connect workbook/tooling changes to the browser runtime.

Checklist:

- [ ] Determine whether a file is source, generated runtime output, optional review output, or published browser data.
- [ ] Treat `form-output/` outputs and `form-app/data.js` as generated unless a current doc or spec explicitly says otherwise.
- [ ] Do not manually patch generated artifacts to make tests pass.
- [ ] If workbook or generator changes affect promoted runtime data, regenerate the relevant artifacts and registry bundle.
- [ ] Inspect generated diffs for unexpected churn before handoff.
- [ ] Keep optional inspection/review artifacts separate from promoted runtime data unless an approved pass changes that boundary.

## 9. Static App Runtime and UI/UX Work

The customer app is a static browser runtime:

- HTML provides the shell and durable document structure.
- CSS controls visual presentation, responsiveness, spacing, hierarchy, and affordances.
- JavaScript consumes generated data and manages rendering, interaction handling, model switching, validation display, summaries, pricing, build download, and dealer-submission UI.
- Generated data provides product facts and business rules to the runtime.

Checklist for UI/UX changes:

- [ ] Classify the change as styling-only, behavior-only, data-only, or mixed.
- [ ] For styling-only work, preserve data contracts, element semantics, selection state, validation behavior, summaries, download data, and dealer payloads.
- [ ] For runtime behavior work, inspect generated data fields and current runtime consumers before editing JavaScript.
- [ ] Preserve stable identifiers and generated keys unless a scoped data/model migration is approved.
- [ ] Validate relevant user workflows, not just visual appearance, when behavior changes.
- [ ] Check mobile/responsive behavior for customer-facing UI changes.
- [ ] Prefer customer-friendly, mobile-first, visually clear interfaces with fewer redundant explanatory surfaces.
- [ ] Avoid prescribing or depending on exact selectors, class names, or component internals unless they are stable public conventions in the current code.

Runtime behavior changes should be verified through workflows such as model switching, body/trim/variant selection, required-step completion, option select/deselect, include/require/exclude behavior, summaries, totals, build download, dealer modal validation, and payload scoping as relevant to the change.

## 10. Dealer Submission and Live-Customer Boundaries

Dealer submission is a protected live-customer boundary.

Checklist:

- [ ] Do not change dealer endpoint, payload shape, model scoping, security/Turnstile behavior, or submission UX without explicit approval.
- [ ] For changes near submission code, inspect the current runtime and tests before editing.
- [ ] Validate modal behavior, required fields, payload construction, error handling, and safe failure states when submission behavior is in scope.
- [ ] Do not perform live dealer submissions as routine validation unless explicitly approved.
- [ ] In docs-only, workbook-only, or styling-only passes, report that dealer behavior was preserved or not touched.

## 11. Raw GM Order-Guide Ingest Boundaries

Raw GM order-guide ingest is an edge workflow for new-model intake or broad source refreshes. It is not routine workbook maintenance.

Durable boundaries:

- [ ] Treat raw ingest preflight as evidence gathering and review preparation unless a separate approved apply path exists.
- [ ] Preserve raw source evidence, row alignment, merged-cell meaning, source spans, and provenance.
- [ ] Do not invent missing product data.
- [ ] Keep candidate/review artifacts transient until reviewed and approved for application.
- [ ] Read-only ingest preflight must not mutate `stingray_master.xlsx`, generated runtime artifacts, `form-app/data.js`, or promoted runtime data.
- [ ] Use `Order-Guide_IngestPrompt.md`, `docs/ingest/`, script help, and current tests for detailed ingest invocation and pass structure.
- [ ] Do not embed current run IDs, temporary paths, current model selections, or pass-specific smoke commands in this guide as default workflow.

If ingest output is later applied to the workbook, treat that as a separate workbook/data change with its own approved spec, workbook safety checks, regeneration, validation, and handoff.

## 12. Validation Strategy

Choose validation based on changed surfaces and risk. Do not run irrelevant gates just because they are listed in an old plan; do not skip relevant gates because a change looked small.

Validation goals:

- workbook package integrity and safe-save correctness;
- workbook schema/source-contract safety;
- generated artifact freshness and diff review;
- registry/model-promotion safety;
- runtime behavior and generated-data consumption;
- UI appearance, responsiveness, and accessibility-relevant affordances;
- dealer-submission boundary preservation;
- docs/guidance consistency.

Checklist:

- [ ] For docs-only changes, review diffs and check consistency with README/active docs.
- [ ] For workbook writes, validate workbook integrity/schema, verify saved workbook on disk, regenerate affected artifacts, and review generated diffs.
- [ ] For generator changes, run representative generation and tests covering changed contract behavior.
- [ ] For registry/publication changes, verify the published data bundle and model switching behavior.
- [ ] For runtime JavaScript changes, run relevant automated tests and manually verify affected customer workflows.
- [ ] For styling changes, inspect the affected UI at relevant viewport sizes and confirm runtime behavior was preserved.
- [ ] For dealer-submission changes, run targeted tests/manual checks in a safe context and report any untested live behavior.
- [ ] Report every validation command/check that was run and its result.
- [ ] Report every relevant gate not run with the reason.

Long command blocks belong in README, dedicated docs, package scripts, test docs, or script help when intentionally maintained there. If this guide includes examples in the future, label them clearly as examples rather than exhaustive required gates.

## 13. Companion-File Impact Checks

Before editing, identify companion surfaces that may need to change with the direct target. Apply this concept proportionally; tiny typo fixes do not need broad ceremony, but source-contract, runtime, workbook, generator, validation, and workflow changes do.

Checklist by changed surface:

- [ ] Workbook/data changes: inspect generated artifacts, registry publication, source-contract tests, model/runtime tests, README/docs, and any owning spec.
- [ ] Generator/tooling changes: inspect generated outputs, schema/contract tests, script docs/help, README/AGENTS guidance, and downstream runtime consumers.
- [ ] Runtime behavior changes: inspect generated data fields, runtime tests, UI workflows, dealer flow, payload construction, and docs that describe behavior.
- [ ] Styling changes: inspect affected HTML/JS state hooks, responsive behavior, visual docs/specs, and ensure data/behavior contracts are preserved.
- [ ] Validation/test changes: inspect workflow docs, gate reminders, CI/local instructions, and tests that might encode the old contract.
- [ ] Docs/guidance changes: inspect README and active docs for consistency; avoid duplicating large sections or leaving stale references.
- [ ] Ingest/review changes: inspect ingest docs, transient artifact boundaries, tests, editor/review surfaces, and no-mutation guarantees.

For handoff, report each relevant companion surface as updated, inspected-no-change, or not applicable with a reason.

## 14. Documentation Maintenance and README Alignment

Use documentation layers intentionally:

- `README.md`: broad project overview, current state, repository map, and stable workflow references.
- `AGENTS.md`: how agents should act safely and comprehensively.
- `docs/`: deeper workflow docs, ingest docs, plans, reviews, and historical context where maintained.
- Script help/tests: current invocation details and executable behavior.

Checklist for docs work:

- [ ] Do not copy large README sections into AGENTS.md.
- [ ] Do not turn AGENTS.md into a script reference manual.
- [ ] Keep AGENTS.md focused on durable source-of-truth rules, workflow expectations, validation strategy, and handoff requirements.
- [ ] Remove or rewrite brittle details such as exact line numbers, temporary paths, pass history, current branch names, and current-model-only examples.
- [ ] Keep specific file names only when they represent stable ownership surfaces or durable entry points.
- [ ] If uncertain whether a detail is durable, add a TODO-style note or point to the owning doc instead of inventing policy.

## 15. Handoff Requirements

Every handoff must be concise but complete.

Report:

- [ ] What changed: files, workbook sheets, generated artifacts, docs, tests, and behavior impact.
- [ ] What did not change: preserved runtime behavior, visual constraints, data contracts, schemas, deployment paths, dealer-submission boundaries, and explicitly excluded work.
- [ ] Companion-file impact: updated, inspected-no-change, or not applicable for relevant surfaces.
- [ ] Validation results: commands/checks run and outcomes.
- [ ] Gates not run and why.
- [ ] Manual verification still pending.
- [ ] Residual risks.
- [ ] Follow-up or next pass guidance; if none is implied, say so rather than inventing work.

When completing an approved spec, pass, or implementation plan, update the owning spec/plan before final handoff when such a file exists. Mark it completed with date, changed surfaces, validation results, residual risks, and follow-up. Do not leave active approval prompts or obsolete next-step claims in completed specs unless rewritten as historical context.

## 16. Durable Boundaries and Anti-Patterns

Do not:

- [ ] overwrite user changes or ignore existing git status;
- [ ] hand-edit generated outputs as source;
- [ ] hide workbook-owned business rules in JavaScript or one-off Python branches when the workbook can express them;
- [ ] add hardcoded model-specific exceptions without an approved spec and documented reason;
- [ ] write `stingray_master.xlsx` while Excel has it open or while lock-file risk is unresolved;
- [ ] claim workbook changes landed before verifying the saved file on disk;
- [ ] change dealer endpoint, payload, model scoping, security behavior, or submission UX without explicit approval;
- [ ] add dependencies without explicit approval;
- [ ] mix unrelated refactors into data, docs, styling, or bug-fix work;
- [ ] stage temporary workbooks, backup files, smoke outputs, or unrelated generated noise;
- [ ] treat raw ingest preflight artifacts as approved workbook/runtime data;
- [ ] claim validation passed without real tool output.

Do:

- [ ] fix the source of truth when possible;
- [ ] keep scripts generic and boring;
- [ ] regenerate outputs through the intended pipeline;
- [ ] validate proportionally to risk;
- [ ] report exactly what changed, what was preserved, and what remains uncertain.
