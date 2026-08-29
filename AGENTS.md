# Agent Operating Guide for 27vette

Durable operating guide for AI agents: source-of-truth boundaries, approval gates, validation strategy, handoff. `README.md` owns the project overview, repository map, and exact commands. Machine-readable owners (`tests/validation_catalog.json`, `scripts/corvette_form_generator/workbook_domain/registry.py`, script `--help`, module READMEs) beat prose. If this guide and the live repo disagree, inspect the repo, then flag the discrepancy.

Scope rule: this file holds durable principles only. Command syntax, gate inventories, module mechanics, and incident history belong to README, module READMEs, `docs/`, or the archive — not here. Prefer judgment over checklist when a rule below does not cleanly fit the task.

## 1. First Principles

- Verify current repo state before trusting remembered architecture, old plans, or generated artifacts. Check `git status` before editing; never overwrite user work.
- Before editing: read the target and nearby files, search the relevant symbols/RPOs/sheet names/tests, trace data definition-to-use. Do not invent files, scripts, APIs, sheet ownership, selectors, test names, or contract fields.
- Keep changes scoped. No unrelated refactors, data cleanup, redesigns, or artifact refreshes without approval.
- This is a live customer-facing app. Preserve customer behavior, generated-data contracts, and dealer-submission boundaries unless explicitly approved.

## 2. Architecture

Pipeline: `stingray_master.xlsx` (canonical workbook) → Python generators/validators → generated artifacts (`form-output/`) → registry publication (`form-app/data.js`) → static browser runtime (`form-app/`) → build download / dealer submission.

For any task, trace: workbook row → generator script → generated artifact → runtime consumer → tests/docs encoding expected behavior.

## 3. Source-of-Truth Boundaries

**Workbook** — canonical for product and business data wherever it can express the decision: model/variant metadata, option placement and availability, customer copy, rules and relationships, prices, colors, assets, runtime metadata. Fix bad source data in the workbook, not by suppressing it downstream. Don't add sheets, columns, or taxonomies until the existing contract is proven insufficient.

**Generated artifacts** — `form-output/` and `form-app/data.js` are artifacts, never source. Never hand-edit them as a fix; fix workbook data or generator logic, regenerate, review diffs.

**Python** — boring and general: read, normalize, validate, emit, publish, apply approved workbook edits. No hardcoded model-specific business exceptions when the workbook can express the rule.

**Runtime JavaScript** — consumes generated data; rendering, interaction, generic validation, summaries, model switching, downloads, dealer UI. Not a hidden product-rule database: if JS seems to need product knowledge, that knowledge belongs in workbook data or generated metadata.

**CSS** — presentation only. Never use styling to hide broken data or logic.

**Registries own their own shape** — `scripts/corvette_form_generator/workbook_domain/registry.py` owns sheet families, writable columns, and shared workbook-domain enums. Schema validation, promotion parsing, editor operations, and Workbook Manager projections derive from it instead of maintaining parallel lists.

Asset/media data (`asset_map`) is workbook-authored like any other sheet; the sync and display tooling and its exact semantics are owned by `docs/asset-map-sync.md` and README.

## 4. Autonomy and Approval Gates

User review is required for unresolved decisions, not for every non-trivial edit.

When the user requested implementation and the intended outcome is already established by the request, workbook data, existing behavior, tests, docs, or another authoritative repo source, proceed through inspection, implementation, validation, and handoff without intermediate approval.

Before non-trivial edits, form a short working definition of done — diagnosis and evidence, intended outcome and affected surfaces, source-of-truth owner, expected files/artifacts, preserved behavior, validation and rollback. Report it in a progress update or an existing task/spec file. Do not create a new spec file just to satisfy process.

**Proceed** when: implementation was requested, the intended behavior is already defined, evidence supports a single safe direction, the change uses existing architecture and write paths, it stays in scope, it is reversible and validatable, and no protected boundary is crossed. This covers bug fixes, parity restoration, artifact refreshes from an approved source change, and workbook corrections with an already-defined outcome.

**Stop and ask** when the work would: invent product/business behavior (availability, pricing, defaults, relationships, customer rules); change dealer submission (§6); introduce a new dependency, schema, public interface, generated-data contract, security boundary, or deployment path; be destructive or hard to reverse; materially expand scope; choose between approaches with real architectural or customer-facing tradeoffs; or proceed against contradicting repository evidence.

Do not stop merely because a task is large, spans files, or needs several validation steps. Pause only when new decision authority is required. Analysis-only, review-only, and spec-writing requests never authorize implementation.

## 5. Workbook Safety

A workbook write needs no separate approval when implementation was requested, the business outcome is already defined, and existing structures and approved tooling express it. Approval is still required when the edit would *choose* product behavior.

Before writing `stingray_master.xlsx`: confirm the owning sheet and exact row-level change; ensure a recoverable backup/rollback point; confirm Excel is closed (treat `~$stingray_master.xlsx` as an active-risk signal, never remove it without proving it stale); write through approved tooling and `save_workbook_safely()` in `scripts/corvette_form_generator/workbook.py`, preserving its lock, validation, and atomic-replace protections.

After writing: verify the backup exists and the workbook reopens from disk; run package and schema validation; regenerate affected artifacts and published data; review diffs for unintended drift; run the primary tests for each affected surface. On validation failure, do not leave an unverified workbook in place — fix it if the fix stays inside the authorized outcome, otherwise restore the backup and ask.

Never recreate or hand-edit generated workbook sheets. Change source rows or generic generator logic, then regenerate.

Editor surfaces (`scripts/workbook_editor_server.py`, `scripts/apply_workbook_ops.py`, `workbook-manager/`) are interfaces around this same contract, not separate authorities. Every write path routes through approved tooling and `save_workbook_safely()`, then regenerates and validates through the normal gates.

Workbook Manager specifics — its disposable SQLite projection, draft/ChangeSet lifecycle, the single apply-and-rebuild write route, refused legacy sync, comparison exports as review-only artifacts, and single-process serving — are owned by `workbook-manager/README.md` and the Manager's own specification. The durable rules here: the workbook stays canonical, only the approved bound write route may reach it, a verified rollback set precedes any write, and no Manager action deploys, purges production cache, uploads media, or submits to a dealer.

## 6. Dealer Submission (protected boundary)

Do not change the dealer endpoint, payload shape, model scoping, security/Turnstile behavior, or submission UX without explicit approval. Near submission code, inspect runtime and tests first and validate modal behavior, required fields, payload construction, and error handling. No live dealer submissions as routine validation. In passes that don't touch it, report dealer behavior as preserved.

## 7. UI/UX and Runtime Work

Classify the change: styling-only, behavior-only, data-only, or mixed. For behavior work, inspect generated data fields and runtime consumers before editing JS. Preserve stable identifiers and generated keys unless a scoped migration is approved. Verify the affected customer workflows — model switching, selection, rule transitions, required steps, summaries, totals, download, dealer modal — not just appearance, and check mobile/responsive behavior for customer-facing changes.

## 8. Raw Order-Guide Ingest (retired)

Retired 2026-07-23; its imported data was not trustworthy enough to remain executable. No supported raw-ingest command or code path exists. Historical material under `docs/archive/retired-ingest/2026-07-23/` is evidence only, never architecture, test authority, or an instruction to resume.

Future raw-source intake requires a new evidence-first specification and explicit approval. The generic `workbook-changeset-1` contract survives independently as the approved target for reliable Workbook Manager writes.

## 9. Operational Handoff

`fable5loop/STATE.md` is the repo's operational handoff and durable project memory; it does not override the boundaries in this guide. It is read every session, so keep it small — retired detail goes to `fable5loop/STATE-archive.md`, and `scripts/validate_state_handoff.py` enforces the budget.

Keep workflow progress in at most two live files: the owning specification tracks requirements, evidence, and blockers; `STATE.md` carries the operational handoff. After each substantive task, overwrite the fixed `Current handoff` block with what was completed, where it landed, what validation actually ran, the next action, blockers, and the owning spec. Update the owning specification only when requirement status, evidence, blockers, or the planned checkpoint changed — never a session narrative. README files change only when their owned commands, architecture, or operator guidance change.

Under a turn, time, or context ceiling, stop starting new implementation early enough to close out: run the smallest decisive affected-path test and `git diff --check`, update the owning spec and `STATE.md`, and review `git status` and the final diff for stray files. Leave the slice commit-ready. If even closeout is at risk, prioritize truthful status recovery over more tests, and never call an unfinished checkpoint complete.

`.claude/` files are thin launch wrappers; durable procedure belongs in the repo-owned guides, not duplicated there.

## 10. Validation Strategy

`tests/validation_catalog.json` and the CI planning scripts are the executable owners of gate layer, authority, isolation, serialization, changed-surface selection, and sharding. Read them rather than re-deriving gates from prose or old plans. Commands live in README ("Validation").

Choose gates by changed surface and risk — don't run irrelevant gates from an old plan, don't skip relevant ones because the change looked small:

- Docs-only: diff review plus consistency with README/active docs.
- Workbook writes: package/schema validation, verify the saved file on disk, regenerate affected artifacts, review generated diffs.
- Asset/media sync: review report output first; run workbook gates and regeneration only if workbook data actually changed.
- Generator changes: representative generation plus tests covering the changed contract.
- Registry/publication: verify the published bundle and model switching.
- Runtime JS: relevant automated tests plus manual verification of affected workflows.
- Workbook Manager: the focused gates in `workbook-manager/README.md`; include generated-parity before claiming a reconstructed workbook preserves runtime contracts.
- Styling: inspect affected UI at relevant viewports; confirm behavior preserved.
- Dealer submission: targeted tests or safe manual checks; report untested live behavior.

Do not cite `generate_form.py` stdout `validation_errors: 0` as proof of a clean artifact — strict runtime-contract errors abort before that line prints. Use the schema gate, targeted tests, artifact diffs, and byte comparison where parity is the success condition.

Report every check run with its result, and every relevant gate not run with the reason. Never claim validation passed without real tool output.

## 11. Companion-File Impact

Proportional to risk. Per changed surface, inspect what co-changes: workbook/data → artifacts, registry, contract tests, docs; generator → outputs, schema tests, script docs, runtime consumers; runtime → generated fields, tests, workflows, dealer flow; styling → HTML/JS state hooks, responsive behavior; tests/gates → workflow docs and tests encoding the old contract; docs → README consistency and stale references. Report each relevant companion as updated, inspected-no-change, or n/a.

## 12. Handoff and Delivery

Report: what changed (files, sheets, artifacts, tests, behavior); what did not change (preserved contracts, boundaries, excluded work); companion impact per §11; validation run and skipped with reasons; residual risks and follow-up (say "none implied" rather than inventing work); delivery branch, commit, and PR URL.

All commits reach `main` through a pull request. Never commit, push, or merge directly on `main`. Work on a task branch from current `origin/main`; complete implementation, validation, diff review, and the `STATE.md` handoff before delivery; commit only reviewed task files; open a PR to `main` as the final repository action, its body summarizing scope, validation, preserved boundaries, and residual risks. End the user handoff with branch, commit, and PR URL.

Opening the PR is part of completing a requested change and needs no second approval. Merging is separate and requires an explicit request. Analysis-only work with no tracked changes needs no commit or PR.

When completing an approved spec, close it before handoff: date, changed surfaces, validation, residual risks, follow-up. Leave no stale approval prompts or obsolete next-step claims.

Never: stage temporary workbooks, backups, or smoke noise; mix unrelated refactors into a pass; add dependencies without approval; claim workbook or validation results without tool evidence.
