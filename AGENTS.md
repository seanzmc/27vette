# Agent Operating Guide for 27vette

Durable operating guide for AI agents in this repo: source-of-truth boundaries, workflow expectations, validation strategy, and handoff requirements. `README.md` owns the project overview, repository map, and all exact commands. If this guide and the live repo disagree, inspect code/workbook/tests/docs first, then flag the discrepancy.

No-redundancy rule: every instruction fact has one owning file (this file = agent conduct/boundaries/validation/handoff; README = overview/map/commands; archived ingest material = historical evidence only). When updating guidance, edit the owner and fix pointers; never duplicate prose across these files.

## 1. First Principles and Context Gathering

- Verify current repo state before relying on remembered architecture, old plans, or generated artifacts. Check `git status` before editing; never overwrite user work.
- Classify the request by changed surface: docs, styling, runtime behavior, workbook/data, asset/media data, generator/tooling, validation/tests, ingest, editor/workbook-service surfaces, or mixed.
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

Asset/media maintenance — `asset_map` remains workbook-authored source data. The safe sync entry is `scripts/sync_asset_map.py`, with exact usage and report contracts owned by `docs/asset-map-sync.md` and README. Bare sync runs are read-only diagnostics; `--complete` is the routine guarded canonical-workbook path that applies unambiguous matches, validates, regenerates affected models, republishes the registry, and bumps the browser data cache version. Low-level `--apply` is only for deterministic fixtures or an explicitly reviewed diagnostic report and does not perform the complete pipeline. Card-presentation edits use `scripts/set_asset_display.py`, preview by default, and require `--write`. Wildcard authoring, blank-row seeding, stale-row deactivation, or schema/status-column changes are separate workbook-data work, not routine media maintenance.

Workbook shape authority — `scripts/corvette_form_generator/workbook_domain/registry.py` owns registered sheet families, writable columns, and shared workbook-domain enums such as `model_registry_promotion.artifact_type`. Schema validation, promotion parsing, editor operations, and Workbook Manager projections must derive from that registry instead of adding parallel header, writeability, or artifact-type lists.

## 4. Autonomy and Approval Gates

User review is required for unresolved decisions, not for every non-trivial edit.

When the user has requested implementation and the intended outcome is already established by the request, workbook data, existing runtime behavior, tests, documentation, or another authoritative repository source, the agent may proceed through inspection, implementation, validation, and handoff without intermediate approval.

Before non-trivial edits, create a concise working definition of done that identifies:

- Current diagnosis and supporting repository evidence.
- Intended outcome and affected surfaces.
- Source-of-truth owner.
- Expected files, sheets, and generated artifacts.
- Important constraints and preserved behavior.
- Validation and rollback plan.

This working definition may be reported in a progress update or recorded in an existing task/spec file. Do not create a new spec file solely to satisfy process when the work is otherwise clear and bounded.

### Proceed Without Additional Approval

Proceed autonomously when all of the following are true:

- The user requested implementation rather than analysis or review only.
- The intended product behavior is already defined.
- Repository evidence supports a single safe implementation direction.
- The change uses existing architecture, schemas, write paths, and dependencies.
- The work remains within the requested scope.
- The change is reversible and can be validated through existing gates.
- No protected boundary below is crossed.

This includes narrow bug fixes, parity restoration, implementation corrections, generated-artifact refreshes from an approved source change, and workbook corrections whose intended business outcome is already defined.

### Require User Approval

Stop and request approval before proceeding when the work requires:

- Choosing or inventing product/business behavior, including availability, pricing, defaults, relationships, customer-facing rules, or other ordering decisions not already established by an authoritative source.
- Changing the dealer-submission endpoint, payload, model scoping, security/Turnstile behavior, or submission UX.
- Introducing a new dependency, schema, public interface, generated-data contract, security boundary, deployment path, or build-system assumption.
- Making a destructive or difficult-to-reverse change.
- Materially expanding the requested scope.
- Choosing between approaches with meaningful architectural or customer-facing tradeoffs.
- Proceeding despite repository evidence that contradicts the requested assumption or intended outcome.

Do not stop merely because a task is non-trivial, spans multiple files, changes implementation logic, or requires several validation steps. Pause only when new decision authority is required.

Analysis-only, review-only, and spec-writing requests never authorize implementation.

## 5. Workbook Safety

A workbook write does not require separate user approval when the user requested implementation, the intended business outcome is already defined, and the change can be expressed through existing workbook structures and approved write tooling.

Before writing `stingray_master.xlsx`:

- Confirm the owning workbook surface and exact intended row-level change.
- Record the current workbook state and ensure a recoverable backup or equivalent rollback point will be created.
- Confirm Excel is closed. Treat `~$stingray_master.xlsx` as an active-risk signal; never remove it without establishing that it is stale.
- Use approved tooling and `save_workbook_safely()` in `scripts/corvette_form_generator/workbook.py`.
- Preserve lock, mtime, temporary-copy validation, package validation, schema validation, and atomic replacement protections.

After writing:

- Verify the backup exists and the saved workbook can be reopened from disk.
- Run package and schema validation.
- Regenerate all affected artifacts and published data.
- Review workbook and generated diffs for unintended changes.
- Run the primary tests for every affected surface.
- If validation fails, do not leave an unverified workbook in place. Correct the failure only when the fix remains within the authorized outcome; otherwise restore the backup and request direction.

Separate approval is still required when the workbook edit would create or choose product/business behavior rather than implement an already-established decision.

Do not recreate or hand-edit generated workbook sheets. Change source rows or generic generator logic, then regenerate.

Workbook editor surfaces (`scripts/workbook_editor_server.py`, `scripts/apply_workbook_ops.py`, and `workbook-manager/`) are interfaces around the same workbook-write safety contract, not separate authorities. The workbook remains canonical unless a separately approved stage changes that. Any editor or manager write path must route through `editor_ops.apply_batch`/approved tooling and `save_workbook_safely()`, then regenerate and validate affected artifacts through the normal gates.

Workbook Manager keeps its SQLite projection disposable/rebuildable while durable manager state records recovery/audit state and browser-authored draft intent; comparison exports remain explicitly `DISPOSABLE-*` review artifacts, never workbook replacements or generation inputs. The browser may emit, preview, and approve the shared immutable ChangeSet, and Asset Manager may add fingerprint-bound `asset_map` operations plus operational ignores to that same draft. Only `POST /api/drafts/{draft_id}/apply-rebuild` may reach the exact bound writer and downstream local generation/publication pipeline. It must prepare a verified rollback set first, derive affected promoted models from stored operation ownership, stage generation off-path, publish only a complete candidate, and restore/hash-verify workbook and outputs on failure. Draft Save still does not write or regenerate. Legacy `POST /api/sync write=true` remains permanently refused; no Manager action deploys, purges production cache, uploads WordPress media, or submits to a dealer. Nonterminal drafts keep replacement import contained. Serve it only through the single-process lifespan path documented in `workbook-manager/README.md`/`workbook-manager/run.sh`; do not use multiple uvicorn workers or bypass lifespan in tests. Package/schema validation and semantic readback prove projection reconstruction, not primary runtime-contract parity unless the separate generated-parity gate has actually run.

## 6. Dealer Submission (protected boundary)

Do not change the dealer endpoint, payload shape, model scoping, security/Turnstile behavior, or submission UX without explicit approval. Near submission code: inspect runtime and tests first; validate modal behavior, required fields, payload construction, error handling, and safe failure states. No live dealer submissions as routine validation. In passes that don't touch it, report dealer behavior as preserved/untouched.

## 7. UI/UX and Runtime Work

Classify the change: styling-only, behavior-only, data-only, or mixed. For behavior work, inspect generated data fields and runtime consumers before editing JS. Preserve stable identifiers and generated keys unless a scoped migration is approved. Verify affected customer workflows (model switching, body/trim/variant selection, required steps, option select/deselect, include/require/exclude, summaries, totals, download, dealer modal/payload scoping) as relevant — not just visual appearance. Check mobile/responsive behavior for customer-facing changes. Prefer customer-friendly, mobile-first, visually clear UI. Avoid depending on exact selectors/internals unless they are stable conventions.

## 8. Raw Order-Guide Ingest (retired)

The raw order-guide ingest wizard, compiler/exception queue, ChangeSet emitter, deployment proof, browser UI, and helper libraries were retired on 2026-07-23 because their imported data was not trustworthy enough to remain an executable workspace workflow. There is no supported raw-ingest command or active ingest code path.

Historical specifications, reports, and prompts live under `docs/archive/retired-ingest/2026-07-23/`; Fable receipts remain chronological evidence. They are not current architecture, test authority, or instructions to resume the retired implementation. Preserve raw source files and ignored local run artifacts as evidence unless a separately approved cleanup names them.

Any future raw-source intake requires a new evidence-first specification and explicit approval. It must not restore archived behavior merely because code or tests once existed. Workbook writes, generation, publication, promotion, deployment, and dealer changes remain separately governed by §§5–7 and §10.

The generic `workbook-changeset-1` parser/service remains the approved target contract for reliable Workbook Manager writes. That contract is independent of ingest and does not imply a current non-ingest producer until the Manager's owning specification implements one.

## 9. Fable 5 Loop Workflows

Fable 5 loop artifacts under `fable5loop/` are orchestration/memory infrastructure for large, multi-stage work; they do not override this guide's spec, workbook, generated-artifact, runtime, styling, or dealer boundaries. For any Fable 5 run, start from `fable5loop/README.md`, preserve run receipts/state updates, and run the loop validator when loop artifacts change. Use `docs/fable-ex-tasks.md` as routing guidance for when the loop is appropriate; keep routine model/workbook/runtime edits on the normal repo path unless a task explicitly needs the loop.

Keep workflow progress in at most two live files: the owning specification is the sole detailed tracker for requirements, acceptance evidence, blockers, and pass-level decisions; `fable5loop/STATE.md` is the centralized operational handoff. Run receipts are immutable evidence, not parallel progress trackers. After every substantive repository task, update the fixed `Current handoff` block in `STATE.md` before declaring the task complete, even when the task did not use Fable and produced no receipt. That block must say what was just completed, where it landed, what validation is actually complete, the exact next action, blockers or closeout gaps, the owning specification when one exists, and the latest completed receipt. Update the owning specification only when the task changes its requirement status, acceptance evidence, blockers, or planned checkpoint; do not copy a session narrative into it. README files change only when their owned commands, architecture, or operator guidance change.

For any bounded run with a turn, tool-call, time, or context ceiling, reserve the final three available turns—or begin at the first ceiling warning when the remaining allowance is not visible—for checkpoint closeout. Stop starting implementation work at that point. Use the reserved capacity to run the smallest decisive affected-path test and `git diff --check`; update the owning specification with exact completed/open requirements, validation, blockers, and next step when those facts changed; rewrite the fixed `fable5loop/STATE.md` handoff; finish the current run receipt sufficiently for recovery when the task used Fable, including checks not run; and inspect `git status` plus the final diff for unrelated or temporary files. Leave the slice commit-ready. Commit and push only when the user requested it or the active workflow already authorizes it. If even the reserved closeout cannot finish, prioritize truthful spec/status recovery over broader tests or additional implementation, and never describe that checkpoint as pass-complete.

Claude Code project files under `.claude/` are thin launch/wrapper surfaces for this repo. They may point agents into `AGENTS.md` and `fable5loop/`, but durable workflow procedure belongs in the repo-owned guides and Fable loop files, not duplicated in `.claude/` wrappers.

## 10. Validation Strategy

Choose gates by changed surface and risk — don't run irrelevant gates from old plans, don't skip relevant ones because a change looked small. Commands live in README ("Workbook And Generator Workflows", "Validation").

Treat `tests/validation_catalog.json` and the CI planning scripts as the executable owners for gate layer, authority, isolation, serialization, changed-surface selection, and full-suite sharding. Do not re-derive those from README prose or old plans. Local and CI layered runs should use the active virtualenv interpreter and the README-owned Node/toolchain setup; Layer 4 is diagnostic unless the task explicitly calls for a full inventory.

- Docs-only: diff review + consistency with README/active docs.
- Workbook writes: package/schema validation, verify saved file on disk, regenerate affected artifacts, review generated diffs.
- Asset/media sync: review manifest/report outputs first; for deterministic checks prefer the fixture media list in README/docs; if a real workbook apply is approved, run workbook package/schema gates, then regenerate affected active models and registry only if workbook data changed.
- Generator changes: representative generation + tests covering the changed contract behavior.
- Registry/publication: verify published bundle and model switching.
- Runtime JS: relevant automated tests + manual verification of affected workflows.
- Workbook Manager import/projection/draft/export: use the focused manager gates in `workbook-manager/README.md`; include the generated-parity acceptance test before claiming reconstructed workbooks preserve primary runtime contracts.
- Styling: inspect affected UI at relevant viewports; confirm behavior preserved.
- Dealer submission: targeted tests/manual checks in a safe context; report untested live behavior.

For generation validation, do not cite `generate_form.py` stdout `validation_errors: 0` as independent proof of a clean artifact; strict runtime-contract errors abort before that summary can print. Use the workbook schema gate, relevant targeted tests, regenerated artifact diffs, and isolated byte comparisons where parity is the success condition.

Report every check run with its result, and every relevant gate not run with the reason. Never claim validation passed without real tool output.

## 11. Companion-File Impact

Proportional to risk. Per changed surface, inspect the companions that may co-change: workbook/data → artifacts, registry, contract tests, docs; generator → outputs, schema tests, script docs, runtime consumers; runtime → generated fields, tests, workflows, dealer flow, docs; styling → HTML/JS state hooks, responsive behavior; tests/gates → workflow docs and tests encoding the old contract; docs → README consistency, no stale references. Report each relevant companion as updated, inspected-no-change, or n/a.

## 12. Handoff Requirements

- [ ] What changed: files, sheets, artifacts, docs, tests, behavior impact.
- [ ] What did not change: preserved behavior, contracts, schemas, deployment paths, dealer boundaries, excluded work.
- [ ] Companion-file impact per §11.
- [ ] Validation: checks run and outcomes; gates not run and why; manual verification still pending.
- [ ] Residual risks and follow-up (say "none implied" rather than inventing work).
- [ ] Delivery: branch name, commit SHA, pushed remote branch, and pull-request URL.

### Pull-Request-Only Delivery

All repository commits must reach `main` through a pull request. Never commit
directly on `main`, push commits directly to `main`, or merge a completed task
locally into `main`.

For every implementation or documentation task that changes tracked files:

1. Work on a task branch created from current `origin/main`. If edits began on
   `main`, preserve them, create the task branch before committing, and confirm
   `main` itself remains unchanged.
2. Complete the scoped implementation, required validation, diff review, and
   `fable5loop/STATE.md` handoff update before delivery.
3. Commit only the reviewed task files to the task branch and push that branch.
4. Create a pull request targeting `main` as the final repository action of the
   task. The PR body must summarize scope, validation, preserved boundaries,
   and residual risks or explicitly state that none are implied.
5. End the user handoff with the branch, commit, and PR URL. Do not begin the
   next checkpoint or make additional repository edits after opening the PR.

Creating a PR is authorized as part of completing a user-requested repository
change; it does not require a second approval. Merging remains a separate action
and requires an explicit user request or an active workflow that expressly
authorizes merge after review. Analysis-only or review-only work with no tracked
changes does not require an empty commit or PR.

When completing an approved spec/plan, close the owning file before handoff: date, changed surfaces, validation results, residual risks, follow-up. Leave no active approval prompts or obsolete next-step claims.

Never: stage temporary workbooks/backups/smoke noise; mix unrelated refactors into a pass; add dependencies without approval; claim workbook or validation results without on-disk/tool evidence.
