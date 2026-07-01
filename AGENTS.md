# Agent Operating Guide for 27vette

Durable operating guide for AI agents in this repo: source-of-truth boundaries, workflow expectations, validation strategy, and handoff requirements. `README.md` owns the project overview, repository map, and all exact commands. If this guide and the live repo disagree, inspect code/workbook/tests/docs first, then flag the discrepancy.

No-redundancy rule: every instruction fact has one owning file (this file = agent conduct/boundaries/validation/handoff; README = overview/map/commands; `Order-Guide_IngestPrompt.md` + `docs/ingest/` = ingest detail). When updating guidance, edit the owner and fix pointers; never duplicate prose across these files.

## 1. First Principles and Context Gathering

- Verify current repo state before relying on remembered architecture, old plans, or generated artifacts. Check `git status` before editing; never overwrite user work.
- Classify the request by changed surface: docs, styling, runtime behavior, workbook/data, generator/tooling, validation/tests, ingest, or mixed.
- Before editing: read the target and nearby files; search relevant symbols/RPOs/sheet names/tests; trace data definition-to-use; check manifests before assuming dependencies. Do not invent files, scripts, APIs, sheet ownership, selectors, test names, or contract fields.
- Keep changes scoped. No unrelated refactors, data cleanup, redesigns, or artifact refreshes without approval.
- This is a live customer-facing app. Preserve live-customer behavior, generated-data contracts, and dealer-submission boundaries unless explicitly approved.

## 2. Architecture

Pipeline: `stingray_master.xlsx` (canonical workbook) → Python generators/validators → generated artifacts (`form-output/`) → registry publication (`form-app/data.js`) → static browser runtime (`form-app/`) → build download / dealer submission.

For any task, trace: workbook/source row → generator script → generated artifact → runtime consumer → tests/docs encoding expected behavior.

## 3. Source-of-Truth Boundaries

Workbook — canonical for product/business data wherever it can express the decision: model/variant/publication metadata; option placement, availability, selectability, display status/order; customer-facing copy and disclosures; includes/requires/excludes, groups, exclusive groups, auto-adds, defaults; prices, overrides, colors, interiors, components, assets; runtime metadata (steps, sections, summaries, context copy, validation/review metadata). Fix bad source data in the workbook, not by suppressing it in Python/JS. Don't add duplicate sheets/columns/taxonomies until the existing contract is proven insufficient.

Generated artifacts — `form-output/` outputs and `form-app/data.js` are artifacts, never source. Never hand-edit them as a fix; fix workbook data or generator logic, regenerate, and review diffs for unintended drift.

Python — boring and general: read workbook, normalize, validate references, emit artifacts, publish registries, apply approved workbook edits. No hardcoded model-specific business exceptions when the workbook can express the rule. Inspect script help/docs/tests for current invocation details (see README command table).

Runtime JavaScript — consumes generated data; renders, manages interaction, generic validation/selection, summaries, model switching, downloads, dealer-submission UI. Not a hidden product-rule database: if JS seems to need product knowledge, it likely belongs in workbook data or generated metadata.

CSS — presentation only. Styling changes must preserve data contracts, runtime state, validation semantics, payloads, and behavior; never use styling to hide broken data or logic.

## 4. Spec-First Expectations

Non-trivial tasks require an approved spec before edits. Non-trivial: multiple surfaces, runtime-behavior change, workbook writes, generated-contract change, test/gate/script/workflow-doc change, dealer-submission change, broad UI/UX change, or new dependencies/build assumptions.

A spec must include:

- [ ] Diagnosis: root cause / current-state evidence, files/sheets/symbols inspected, risk level, change class.
- [ ] Exact files, sheets, artifacts, or docs expected to change.
- [ ] Source-of-truth decision (workbook / generator / artifact / runtime / styling / docs / tooling).
- [ ] Companion-file impact: updated, inspected-no-change, or n/a per relevant surface.
- [ ] Constraints: no unrelated refactor; no new dependencies unless approved; generated files not source; workbook owns rules where possible; dealer boundaries preserved.
- [ ] Risks and non-goals.
- [ ] Validation plan matched to changed surfaces and risk.

Wait for approval unless the user asked for analysis only. Small isolated docs/typo fixes: lightweight checklist, but still inspect current files and report validation honestly.

## 5. Workbook Safety

`stingray_master.xlsx` writes require: task approved and owning surface identified; Excel closed (lock file `~$stingray_master.xlsx` is an active-risk signal — confirm stale before removing); write through approved tooling / `save_workbook_safely()` in `scripts/corvette_form_generator/workbook.py` (validates a temp copy, refuses on mtime change or lock file); verify the saved workbook on disk before claiming the change landed; regenerate affected artifacts and published data; run surface-appropriate gates. Do not recreate or hand-edit generated workbook sheets — change source rows or generic generator logic, then regenerate.

## 6. Dealer Submission (protected boundary)

Do not change the dealer endpoint, payload shape, model scoping, security/Turnstile behavior, or submission UX without explicit approval. Near submission code: inspect runtime and tests first; validate modal behavior, required fields, payload construction, error handling, and safe failure states. No live dealer submissions as routine validation. In passes that don't touch it, report dealer behavior as preserved/untouched.

## 7. UI/UX and Runtime Work

Classify the change: styling-only, behavior-only, data-only, or mixed. For behavior work, inspect generated data fields and runtime consumers before editing JS. Preserve stable identifiers and generated keys unless a scoped migration is approved. Verify affected customer workflows (model switching, body/trim/variant selection, required steps, option select/deselect, include/require/exclude, summaries, totals, download, dealer modal/payload scoping) as relevant — not just visual appearance. Check mobile/responsive behavior for customer-facing changes. Prefer customer-friendly, mobile-first, visually clear UI. Avoid depending on exact selectors/internals unless they are stable conventions.

## 8. Raw Order-Guide Ingest (summary)

Edge workflow for new-model intake or broad source refresh — never routine maintenance. Preflight is read-only evidence gathering: preserve raw evidence and provenance, invent nothing, keep candidate artifacts transient, and never mutate the workbook, generated artifacts, or `form-app/data.js`. Applying reviewed output later is a separate approved workbook pass with full §5 safety, regeneration, and gates. Detail: `Order-Guide_IngestPrompt.md` and `docs/ingest/`.

## 9. Validation Strategy

Choose gates by changed surface and risk — don't run irrelevant gates from old plans, don't skip relevant ones because a change looked small. Commands live in README ("Workbook And Generator Workflows", "Validation").

- Docs-only: diff review + consistency with README/active docs.
- Workbook writes: package/schema validation, verify saved file on disk, regenerate affected artifacts, review generated diffs.
- Generator changes: representative generation + tests covering the changed contract behavior.
- Registry/publication: verify published bundle and model switching.
- Runtime JS: relevant automated tests + manual verification of affected workflows.
- Styling: inspect affected UI at relevant viewports; confirm behavior preserved.
- Dealer submission: targeted tests/manual checks in a safe context; report untested live behavior.

Report every check run with its result, and every relevant gate not run with the reason. Never claim validation passed without real tool output.

## 10. Companion-File Impact

Proportional to risk. Per changed surface, inspect the companions that may co-change: workbook/data → artifacts, registry, contract tests, docs; generator → outputs, schema tests, script docs, runtime consumers; runtime → generated fields, tests, workflows, dealer flow, docs; styling → HTML/JS state hooks, responsive behavior; tests/gates → workflow docs and tests encoding the old contract; docs → README consistency, no stale references. Report each relevant companion as updated, inspected-no-change, or n/a.

## 11. Handoff Requirements

- [ ] What changed: files, sheets, artifacts, docs, tests, behavior impact.
- [ ] What did not change: preserved behavior, contracts, schemas, deployment paths, dealer boundaries, excluded work.
- [ ] Companion-file impact per §10.
- [ ] Validation: checks run and outcomes; gates not run and why; manual verification still pending.
- [ ] Residual risks and follow-up (say "none implied" rather than inventing work).

When completing an approved spec/plan, close the owning file before handoff: date, changed surfaces, validation results, residual risks, follow-up. Leave no active approval prompts or obsolete next-step claims.

Never: stage temporary workbooks/backups/smoke noise; mix unrelated refactors into a pass; add dependencies without approval; claim workbook or validation results without on-disk/tool evidence.
