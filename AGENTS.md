# Agent Operating Guide for 27vette

Durable operating guide for AI agents in this repo: source-of-truth boundaries, workflow expectations, validation strategy, and handoff requirements. `README.md` owns the project overview, repository map, and all exact commands. If this guide and the live repo disagree, inspect code/workbook/tests/docs first, then flag the discrepancy.

No-redundancy rule: every instruction fact has one owning file (this file = agent conduct/boundaries/validation/handoff; README = overview/map/commands; `Order-Guide_IngestPrompt.md` + `docs/ingest/` = ingest detail). When updating guidance, edit the owner and fix pointers; never duplicate prose across these files.

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

Asset/media maintenance — `asset_map` remains workbook-authored source data. The safe sync entry is `scripts/sync_asset_map.py`, with exact usage and report contracts owned by `docs/asset-map-sync.md` and README. Treat sync runs as dry-run/report-first review surfaces unless `--apply` is explicitly approved for specific reviewed row changes; wildcard authoring, blank-row seeding, stale-row deactivation, or schema/status-column changes are separate workbook-data work, not routine media maintenance.

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

## 6. Dealer Submission (protected boundary)

Do not change the dealer endpoint, payload shape, model scoping, security/Turnstile behavior, or submission UX without explicit approval. Near submission code: inspect runtime and tests first; validate modal behavior, required fields, payload construction, error handling, and safe failure states. No live dealer submissions as routine validation. In passes that don't touch it, report dealer behavior as preserved/untouched.

## 7. UI/UX and Runtime Work

Classify the change: styling-only, behavior-only, data-only, or mixed. For behavior work, inspect generated data fields and runtime consumers before editing JS. Preserve stable identifiers and generated keys unless a scoped migration is approved. Verify affected customer workflows (model switching, body/trim/variant selection, required steps, option select/deselect, include/require/exclude, summaries, totals, download, dealer modal/payload scoping) as relevant — not just visual appearance. Check mobile/responsive behavior for customer-facing changes. Prefer customer-friendly, mobile-first, visually clear UI. Avoid depending on exact selectors/internals unless they are stable conventions.

## 8. Raw Order-Guide Ingest (summary)

Edge workflow for new-model intake or broad source refresh — never routine maintenance. Preflight is read-only evidence gathering: preserve raw evidence and provenance, invent nothing, keep candidate artifacts transient, and never mutate the workbook, generated artifacts, or `form-app/data.js`. Applying reviewed output later is a separate approved workbook pass with full §5 safety, regeneration, and gates. Detail: `Order-Guide_IngestPrompt.md` and `docs/ingest/`.

Current ingest direction is browser-first for source intake, then compiler/exception driven for production continuation. The current entry path is `scripts/ingest_wizard_server.py`; the production direction is the canonical-row compiler plus typed exception queue in `docs/ingest/canonical-row-compiler-exception-queue-design.md`, with the approved consolidation destination in `docs/ingest/ingest-separation-model-integration-editor-consolidation-spec.md`: ingest owns raw intake, profiling/target selection, canonical compilation, typed exception resolution, and shared ChangeSet emission only. Historical Pass B broad review lanes and Pass C/D.2 decision-to-plan artifacts remain evidence/debug surfaces, not production write authority.

The shared ChangeSet/workbook-service direction does not itself authorize live workbook writes, generated-artifact refresh, registry publication, runtime promotion, deployment, or dealer changes. Those remain separate approved steps with §5 workbook safety and normal regeneration/validation gates. During transition, do not let ingest, the workbook editor, or Workbook Manager keep parallel schemas, validators, writer authority, or canonical row stores when the shared workbook registry/service should own the contract.

Current ingest stops after immutable `workbook-changeset-1` emission. Historical `pass-c-*` plans and approvals are GET-only evidence and never production write authority; `scripts/ingest_wizard_apply.py` is retired. Preview, approval, and any separately authorized workbook write use the shared service through `scripts/apply_workbook_changeset.py`, with exact ChangeSet/preview/approval/workbook binding, §5 workbook safety, and verified rollback. This path does not authorize generation, publication, promotion, deployment, or dealer changes.

## 9. Fable 5 Loop Workflows

Fable 5 loop artifacts under `fable5loop/` are orchestration/memory infrastructure for large, multi-stage work; they do not override this guide's spec, workbook, generated-artifact, runtime, styling, dealer, or ingest boundaries. For any Fable 5 run, start from `fable5loop/README.md`, preserve run receipts/state updates, and run the loop validator when loop artifacts change. Use `docs/fable-ex-tasks.md` as routing guidance for when the loop is appropriate; keep routine model/workbook/runtime edits on the normal repo path unless a task explicitly needs the loop.

Claude Code project files under `.claude/` are thin launch/wrapper surfaces for this repo. They may point agents into `AGENTS.md` and `fable5loop/`, but durable workflow procedure belongs in the repo-owned guides and Fable loop files, not duplicated in `.claude/` wrappers.

## 10. Validation Strategy

Choose gates by changed surface and risk — don't run irrelevant gates from old plans, don't skip relevant ones because a change looked small. Commands live in README ("Workbook And Generator Workflows", "Validation").

- Docs-only: diff review + consistency with README/active docs.
- Workbook writes: package/schema validation, verify saved file on disk, regenerate affected artifacts, review generated diffs.
- Asset/media sync: review manifest/report outputs first; for deterministic checks prefer the fixture media list in README/docs; if a real workbook apply is approved, run workbook package/schema gates, then regenerate affected active models and registry only if workbook data changed.
- Generator changes: representative generation + tests covering the changed contract behavior.
- Registry/publication: verify published bundle and model switching.
- Runtime JS: relevant automated tests + manual verification of affected workflows.
- Styling: inspect affected UI at relevant viewports; confirm behavior preserved.
- Dealer submission: targeted tests/manual checks in a safe context; report untested live behavior.

Report every check run with its result, and every relevant gate not run with the reason. Never claim validation passed without real tool output.

## 11. Companion-File Impact

Proportional to risk. Per changed surface, inspect the companions that may co-change: workbook/data → artifacts, registry, contract tests, docs; generator → outputs, schema tests, script docs, runtime consumers; runtime → generated fields, tests, workflows, dealer flow, docs; styling → HTML/JS state hooks, responsive behavior; tests/gates → workflow docs and tests encoding the old contract; docs → README consistency, no stale references. Report each relevant companion as updated, inspected-no-change, or n/a.

## 12. Handoff Requirements

- [ ] What changed: files, sheets, artifacts, docs, tests, behavior impact.
- [ ] What did not change: preserved behavior, contracts, schemas, deployment paths, dealer boundaries, excluded work.
- [ ] Companion-file impact per §11.
- [ ] Validation: checks run and outcomes; gates not run and why; manual verification still pending.
- [ ] Residual risks and follow-up (say "none implied" rather than inventing work).

When completing an approved spec/plan, close the owning file before handoff: date, changed surfaces, validation results, residual risks, follow-up. Leave no active approval prompts or obsolete next-step claims.

Never: stage temporary workbooks/backups/smoke noise; mix unrelated refactors into a pass; add dependencies without approval; claim workbook or validation results without on-disk/tool evidence.
