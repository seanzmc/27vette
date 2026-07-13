# Ingest Milestone 2 Exception Queue Browser Flow Implementation Plan

Status: APPROVED FOR IMPLEMENTATION 2026-07-13. Sean explicitly authorized Milestone 2 with “begin milestone 2.” This pass is limited to the read-only browser/API exception workflow defined here. It does not authorize `pass-c-3`, workbook writes, generation, publication, promotion, or dealer changes.

Recommended reasoning level for implementation agents: high.

Parent design: `docs/ingest/canonical-row-compiler-exception-queue-design.md`, especially §§9.3–9.5, §§10.1–10.3, §13 Milestone 2, §14.4, and §§15–17.

Milestone 1 source: `docs/ingest/milestone-1-headless-compiler-comparator-evidence-implementation-plan.md` and receipt `fable5loop/runs/2026-07-13-milestone1-headless-compiler/`.

## 1. Goal

Replace the historical broad-decision review path in the forward ingest wizard with the production compiler flow:

1. select targets and comparators;
2. compile through `WizardSessionStore.compile_canonical_rows()`;
3. review a compact compile/readiness summary;
4. review only typed compiler exceptions;
5. resolve or reopen one exact current subject through workbook-writable controls;
6. recompile automatically after each resolution change;
7. resume a saved compiled run with exact queue/resolution/readiness state.

Legacy decision/review/plan routes remain available for historical/debug runs. They are not the forward path for a new `models_selected` run.

## 2. Diagnosis and source-of-truth decision

Change class: ingest session/API behavior plus browser UI, CSS, tests, and docs. The canonical workbook and raw export remain read-only inputs.

Current evidence:

- `session.py::compile_canonical_rows()` and `compiler_detail()` already own compiler execution and coherent artifact readback.
- `exceptions.py` already owns allowed actions, reason/action compatibility, payload schemas, dispositions, resolution classification, and audit-event contracts.
- `ingest_wizard_server.py` has no `/compile` or `/exceptions` routes.
- `visualizer/ingest-wizard/` still sends newly selected models into historical broad review lanes and still describes comparator data as presentation prefill.
- `list_sessions()` and `session_detail()` already exist, but the browser exposes no visible resume-run path.
- The current real proof contains 800 typed subjects; rendering the full queue and multi-megabyte compiler artifacts in one browser response is not acceptable. The browser API needs compact summary plus filtered/paginated exception views.

Source-of-truth decisions:

- `exception-queue.json` owns current subjects, versions, allowed actions, questions, proposed row previews, evidence references, and gate impact.
- `exceptions.py` owns payload validity and server-derived action disposition. The browser may not invent actions, dispositions, reason codes, or arbitrary payload keys.
- `exception-resolutions.json` owns current/stale/superseded typed resolution state.
- `compile-report.json` owns readiness and counts.
- `option-candidates.json`, comparator evidence, manifest rows, and canonical workbook rows are display evidence only. Browser display adapters may enrich cards but may not alter compiler truth.
- Legacy `decisions.json` is never an input to the production compiler flow.

### Implemented action-to-compiler-effect boundary

Milestone 1's queue vocabulary is broader than its current row-projection consumers. Milestone 2 therefore derives `availableActions` server-side and exposes an exception as reviewer-answerable only when every offered alternative has a complete compiler outcome. The raw queue `allowedActions` remain visible as compiler contract evidence but are not sufficient to authorize a browser control.

| Queue reason/action | Finite browser payload | Current compiler effect | Milestone 2 exposure |
|---|---|---|---|
| `missing_section` / `choose_section` | `{sectionId}` from canonical workbook sections | Recompiles the exact option row with the selected section and clears that subject's blocker | Exposed |
| `missing_price_scope` or `unresolved_price_scope` / `provide_typed_value` | Typed price kind/value plus body/trim scope from target variants or canonical wildcard | Emits the exact typed price row and clears that subject's blocker | Exposed |
| A reason whose only complete outcome is `record_allowed_deferral` | Closed `deferralKind` enum | Records the allowed non-row disposition in compile readiness | Exposed only when no unsupported row-producing alternative exists |
| `mark_not_applicable` paired only with compiler-complete alternatives | Exact action, empty typed payload | Records the non-row not-applicable disposition and clears the exact feature | Exposed only when the full choice set is compiler-complete |
| Relationship selection, comparator confirmation, identity retention, or approved removal without a current row consumer | None | Current compiler cannot yet materialize/evict the exact canonical rows | Actionless tooling blocker; API refuses resolution |

This explicitly covers `choose_relationship`, comparator `provide_typed_value`, `retain_existing`, and `approve_removal`: they are not presented as successful resolutions until their exact compiler consumers exist. A mixed choice set is not partially exposed because that would bias the reviewer toward the only implemented answer.

Compiler mutations use one per-run reentrant lock shared by compile, role confirmation, reparse, model reselection, resolve, and reopen. Resolve/reopen snapshot the aggregate compiler artifacts, session, and audit log and atomically restore the complete prior set if compilation, audit, or response verification fails.

Standing constraints from `AGENTS.md` apply, especially §§3–4, §6, §§8–12.

## 3. Definition of done

Milestone 2 is complete only when all of the following are true:

1. The server implements the approved route convention:
   - `POST /api/wizard/sessions/<run-id>/compile`
   - `GET /api/wizard/sessions/<run-id>/compile`
   - `GET /api/wizard/sessions/<run-id>/exceptions`
   - `POST /api/wizard/sessions/<run-id>/exceptions/resolve`
   - `POST /api/wizard/sessions/<run-id>/exceptions/reopen`
2. Compile GET returns a compact browser view, not the full multi-megabyte manifest/report payload. It includes per-model `compileReady`, `planReady`, `writeReady`, and `deploymentReady`; exact blocker/deferral counts; row/action/family/source-feature counts; queue state counts; and the current artifact bindings needed to detect stale browser state.
3. Exception GET supports model/family/reason/severity/state/actionable/search filters plus deterministic offset/limit pagination and returns filter totals. Default UI view is open actionable subjects; missing-source/actionless blockers remain visible through an explicit blocker filter.
4. Every exception card shows:
   - model, family, severity, reason, question, subject/version, and gate impact;
   - raw evidence with source sheet/row/cells where it can be resolved from bound run artifacts;
   - target workbook/manifest state relevant to the subject;
   - comparator context where present;
   - proposed canonical rows;
   - exact allowed actions and typed payload controls.
5. Browser choices are workbook-writable and finite where the contract requires them:
   - `choose_section`: canonical `section_master` choices;
   - `choose_relationship`: target option IDs plus allowed rule types;
   - comparator-backed proposals: use only the existing `REASON_ACTIONS` contract (`provide_typed_value`, `choose_relationship`, or `mark_not_applicable`, depending on family); no new confirm/reject action taxonomy is introduced;
   - `retain_existing`: concrete existing target IDs;
   - price scope: only allowed scope/value fields;
   - allowed deferral: fixed allowlisted kind plus reason;
   - no generic approve/skip, arbitrary JSON, or copy-to-model action.
6. Resolve requires exact current `subjectId` and `subjectVersion`; the server derives disposition from `ACTION_DISPOSITIONS`, validates through `validate_resolution()`, records reviewer/time metadata outside semantic validity, and refuses stale, unknown, duplicate-current, or type-invalid payloads.
7. Resolve automatically recompiles. A failed recompile restores the prior coherent resolution artifact and leaves the prior compiled artifact/session set loadable.
8. Reopen removes one exact current valid resolution, recompiles, appends one deterministic `resolution_reopened` audit event, and refuses open/stale/superseded subjects. Unchanged retries do not duplicate audit events.
9. Any resolution change invalidates/refuses downstream plan/dry-run/approval state. Milestone 2 does not create or approve a plan.
10. A resumed `compiled_with_exceptions` or `compiled_ready` run restores the exact compile summary, filters, current resolution statuses, and readiness. `models_selected` resumes at the compile screen. Historical decision/plan states still route to the legacy review/plan screens.
11. The forward path after model selection goes to Compile, not broad decision review. Comparator copy is described as context/corroboration only.
12. The UI provides clear loading/error/success states, keyboard labels, mobile stacking, and no live-write control.
13. Focused session/server/UI tests pass, the full affected ingest suite passes, JavaScript syntax passes, and a real browser smoke proves resume, compile summary, filters, one safe fixture resolution, reopen, recompile, readiness refresh, responsive layout, and zero console errors.
14. The live `stingray_master.xlsx`, current export, proof run, `form-output/runtime/**`, `form-app/**`, apply/promotion scripts, and dealer surfaces remain unchanged.

## 4. Pinned service and API contracts

### 4.1 Compact compile view

Add `WizardSessionStore.compiler_summary(run_id)`. It calls `compiler_detail()` first, then returns only browser-safe summary data:

- session identity/state/source;
- compiler binding fields already stored in `session.compiler`;
- model modes/readiness/boundary reasons and blocker/deferral counts;
- manifest action/family/status counts;
- source-feature and family-coverage disposition counts;
- exception state/reason/family/model/severity/actionable counts;
- no full manifest rows, source-feature ledger, comparator fact list, or blocker arrays.

### 4.2 Exception view

Add `WizardSessionStore.exception_queue_view(run_id, *, model, family, reason, severity, state, actionable, query, offset, limit)`.

The service must call `compiler_detail()` before reading/enriching data. It assigns each current subject one state:

- `resolved` when one valid entry matches the exact subject/version;
- `open` otherwise.

Stale and superseded entries are returned as history attached to the durable subject when present; they do not hide the current open subject. Filters and pagination apply after deterministic subject sorting. `limit` is clamped to a bounded browser page size.

Display enrichment is a separate view object and is never persisted into compiler artifacts. It may use existing public canonical/identity helpers and read-only workbook extraction. It must return empty evidence sections honestly when a reference cannot be resolved; it may not invent evidence.

Choice catalogs are computed from canonical workbook/manifest evidence and restricted by the subject’s `allowedActions`.

### 4.3 Resolve

Add `WizardSessionStore.resolve_exception(run_id, *, subject_id, subject_version, action, payload, reviewer)`.

Required behavior:

- current compiled state only;
- exact current subject/version only;
- non-empty reviewer;
- action must be present in the subject contract;
- disposition is derived server-side from `ACTION_DISPOSITIONS`;
- `validate_resolution()` is the final contract gate;
- an existing valid resolution for that subject/version must be reopened before another can be recorded;
- persist candidate resolution state atomically, call `compile_canonical_rows()`, and restore previous resolution bytes if compile refuses before completing;
- return compact summary plus the refreshed subject view.

The API body is exactly `subjectId`, `subjectVersion`, `action`, `payload`, and `reviewer`. Client-supplied disposition, reason code, model, family, or timestamps are ignored/rejected rather than trusted.

### 4.4 Reopen

Add `WizardSessionStore.reopen_exception(run_id, *, subject_id, subject_version, reviewer)`.

Required behavior:

- exact current valid resolution only;
- non-empty reviewer;
- remove that one current entry while preserving stale/superseded history;
- recompile and restore prior resolution bytes on refusal;
- append one `resolution_reopened` event after successful recompile using the existing event-ID contract;
- return compact summary plus refreshed subject view.

### 4.5 HTTP mapping

Server routes are thin adapters. They validate JSON container types and query scalar types, then delegate to the session store. `WizardError.status` remains the HTTP status authority. Route order must place `/compile` and `/exceptions` before the existing catch-all session-detail route.

No public network listener, authentication change, dependency, or browser write endpoint is introduced; the server remains localhost by default.

## 5. Pinned browser flow

### 5.1 Stages

The forward stepper becomes:

1. Choose file
2. Sheet roles
3. Candidates
4. Models
5. Compile
6. Exceptions

Historical Review and Diagnostic Plan sections remain in the document for legacy resume/debug routing but are not reachable from a new production compiler run.

### 5.2 Resume

The file screen shows recent runs from existing `GET /api/wizard/sessions`. Each row shows source file, run ID, state, selected targets when available, and a Resume button.

Resume routing:

- `profiled` / `roles_confirmed` -> Sheet roles
- `parsed` -> Candidates
- `models_selected` -> Compile
- `compiled_with_exceptions` / `compiled_ready` -> Compile summary, then Exceptions
- historical decision states -> legacy Review
- historical plan/dry-run states -> legacy Plan
- terminal apply states -> read-only detail/error; no reopening

### 5.3 Compile summary/readiness

The compile screen shows per-model readiness as four separate fields. It never collapses them to generic valid/invalid. It shows derived/add/update/noop/blocked counts and source/family coverage. Buttons:

- Compile canonical rows / Recompile
- Review open exceptions
- Back to models only when no compiler resolution state would be silently discarded

No plan, approval, write, generation, publication, or promotion action is added.

### 5.4 Typed exception cards

Default filters: state=open and actionable=yes. Cards are grouped/sorted deterministically, one page at a time. Every action label uses concrete workbook language, for example:

- Choose workbook section
- Record this exact relationship
- Confirm this comparator proposal
- Mark this proposal not applicable, with reason
- Keep existing workbook row
- Supply conditional price/scope
- Record allowed media deferral

Actionless blockers explain the missing parser/source support and offer no fake decision control.

After Resolve or Reopen, the browser uses the returned refreshed summary/subject state and then reloads the current exception page. Stale-version 409 responses visibly instruct the reviewer to reload; they never resubmit against a new version automatically.

## 6. Test-first implementation tasks

### Task 1 — session summary and exception view

RED first in new `tests/test_ingest_wizard_exception_flow.py`:

- compact summary omits full rows/ledgers;
- exact readiness/counts;
- deterministic filter/pagination behavior;
- resolved/open/stale history classification;
- evidence and choice enrichment for section, relationship, comparator proposal, price, and ambiguous identity subjects;
- actionless blocker view;
- invalid graph/session binding refusal propagates.

Then implement minimal service methods in `session.py` and, only if separation is required, one display-only helper module under `ingest/wizard/`.

### Task 2 — resolve/reopen lifecycle

RED first in `tests/test_ingest_wizard_exception_flow.py`:

- valid section resolution materializes and refreshes readiness;
- server-derived disposition;
- stale/unknown/invalid action/payload/reviewer refusal;
- duplicate current resolution refusal;
- compile-refusal rollback;
- reopen returns subject to open and logs once;
- stale/superseded reopen refusal;
- no plan/apply artifact creation.

Then implement minimal session methods.

### Task 3 — HTTP routes

RED first in new `tests/test_ingest_wizard_server_milestone2.py` using fixture runs and the real `ThreadingHTTPServer` harness:

- POST/GET compile;
- filtered GET exceptions;
- resolve/reopen happy paths;
- malformed bodies and stale versions;
- HTTP status mapping;
- catch-all route does not swallow new endpoints;
- legacy routes remain available.

Then implement thin routes in `scripts/ingest_wizard_server.py`.

### Task 4 — forward UI and resume

RED first in new `tests/test_ingest_wizard_ui_milestone2.py` plus a lightweight DOM-capable Node harness if current source assertions cannot prove behavior:

- forward stages and no broad review transition;
- visible resume list and state routing;
- compact compile/readiness rendering;
- exception filters/pagination;
- evidence panels and concrete typed controls;
- resolve/reopen request bodies;
- no generic approve/skip/copy-to-model action in compiler flow;
- no write/plan approval button in compiler stages;
- stale/error/loading behavior;
- mobile/accessibility hooks.

Then update `index.html`, `wizard.js`, and `wizard.css`. Preserve historical review/plan code as debug compatibility; do not refactor it broadly.

### Task 5 — proof and closeout

- Build a fresh fixture-backed browser run through models -> compile -> resolve -> reopen.
- Resume the same run after a server/browser reload.
- Use the current ignored Milestone 1 proof run only for read-only summary/filter/card rendering; do not alter its resolutions or audit log.
- Run browser smoke at desktop and mobile width with zero console errors.
- Verify protected paths and input hashes remain unchanged.
- Run independent adversarial verification against the final implementation/test digest.
- Close this plan, parent design status, ingest README, root README only if its workflow summary becomes stale, Fable receipt, and `STATE.md`.

## 7. Exact files

Expected new files:

- `tests/test_ingest_wizard_exception_flow.py`
- `tests/test_ingest_wizard_server_milestone2.py`
- `tests/test_ingest_wizard_ui_milestone2.py`
- `docs/ingest/milestone-2-exception-queue-browser-flow-implementation-plan.md`
- `fable5loop/runs/2026-07-13-milestone2-exception-browser-flow/outcome.md`
- closeout receipt files in the same run directory

Expected modified files:

- `scripts/corvette_form_generator/ingest/wizard/session.py`
- `scripts/ingest_wizard_server.py`
- `visualizer/ingest-wizard/index.html`
- `visualizer/ingest-wizard/wizard.js`
- `visualizer/ingest-wizard/wizard.css`
- `docs/ingest/canonical-row-compiler-exception-queue-design.md`
- `docs/ingest/README.md`
- `README.md` only if its implemented workflow summary becomes stale
- `fable5loop/STATE.md`

Implementation decision: compact summary and exception projection remain private, display-only methods on `WizardSessionStore` so artifact validation, workbook-derived finite choices, freshness checks, and mutation authority stay behind one service boundary. No second public view module or parallel contract was added.

Inspected-no-change unless evidence contradicts this plan:

- `stingray_master.xlsx`
- current raw export
- Milestone 1 proof run artifacts
- `docs/ingest/ingest-wizard-end-to-end-completion-spec.md` (already marks the broad decision-lane path historical/superseded)
- `compiler.py`, `canonical_rows.py`, `identity.py`, `comparator_evidence.py`, and `relationship_compiler.py`
- `exceptions.py` except a narrow reusable public helper that preserves all Milestone 1 contracts
- `plan_builder.py`
- `scripts/ingest_wizard_apply.py`
- `scripts/promote_model.py`
- `form-output/runtime/**`
- `form-app/**`
- dealer-submission code

Expansion into compiler semantics, workbook schema/data, plan projection, generator/runtime behavior, publication, promotion, or dealer flow requires a stop and new authority.

## 8. Validation plan

Run in this order:

1. Per-feature RED then GREEN focused tests.
2. Syntax:
   - `PYTHONPATH=scripts .venv/bin/python -m py_compile ...changed Python files...`
   - `node --check visualizer/ingest-wizard/wizard.js`
   - `git diff --check`
3. Focused Milestone 2:
   - `.venv/bin/python -m pytest tests/test_ingest_wizard_exception_flow.py tests/test_ingest_wizard_server_milestone2.py tests/test_ingest_wizard_ui_milestone2.py -q`
4. Milestone 1 regression:
   - the seven focused compiler suites from the completed Milestone 1 plan.
5. Broad ingest/session/server/UI affected gate:
   - `.venv/bin/python -m pytest tests/test_ingest_wizard*.py tests/test_runtime_metadata_guards.py tests/test_editor_ops_global_families.py tests/test_editor_ops_meta.py -q`
6. Workbook package/schema read-only validation.
7. Browser smoke through the localhost server on a fixture-copy root; desktop and mobile; inspect console and network errors.
8. Protected-surface hashes/status before and after, including live workbook, current export, Milestone 1 proof artifacts, runtime publication, apply/promotion, and dealer surfaces.
9. Full Python suite; classify only independently reproduced pre-existing failures.
10. `.venv/bin/python scripts/validate_fable5_loop.py` after receipt closeout.

## 9. Risks and stop conditions

- Stop if the UI needs a new product/business action not already present in `exceptions.py`.
- Stop if a card cannot offer a workbook-writable finite choice without changing compiler truth; expose it as an actionless blocker rather than inventing a control.
- Stop if evidence enrichment would require adding diagnostic display fields to canonical workbook sheets or runtime contracts.
- Stop if resolve/reopen cannot restore a coherent prior artifact set after a failed recompile.
- Stop if forward-path replacement would delete historical routes or artifacts rather than preserving them as debug compatibility.
- Stop if a real proof-run write would be required; real proof artifacts are read-only display evidence in this milestone.
- No new dependency, workbook column, public network interface, `pass-c-3`, live write, generation, publication, promotion, or dealer change.

## 10. Companion-file impact

| Surface | Milestone 2 disposition |
|---|---|
| Canonical workbook/raw export | Read-only; hash/mtime protected |
| Compiler artifacts/contracts | Read and recompiled in run scope; Milestone 1 semantic contracts preserved |
| Legacy decisions/review/plan | Preserved for historical/debug runs; removed only from new forward navigation |
| Apply/write approvals | No creation or UI controls |
| Generated runtime and registry | Untouched |
| Browser/server | Primary changed surface |
| Dealer submission | Untouched |
| Docs/Fable state | Updated and closed with final evidence |

## 11. Approval record

Sean authorized implementation on 2026-07-13 with “begin milestone 2.” The approved outcome is the exception-queue browser/API flow defined by the already-approved parent design. This authorization does not extend to Milestone 3, `pass-c-3`, workbook mutation, generation, publication, promotion, or dealer changes.

## 12. Outcome — closed 2026-07-13

Milestone 2 is implemented and independently verified PASS. The final workflow provides compact compile/readiness summaries, deterministic typed exception browsing, finite compiler-complete controls, strict stale-input and HTTP refusal, serialized resolve/reopen lifecycle with complete rollback, visible saved-run resume, and desktop/mobile evidence-backed rendering.

Validation: 23 focused tests passed; 298 broad affected tests plus 6 subtests passed; the full repository reported 584 passed plus 13 subtests with four documented pre-existing failures and one expected open-receipt Fable failure subsequently closed by the loop validator. Safe fixture resolve/reopen changed blockers 25 → 24 → 25. The retained real run exposed exactly 75 section and 17 finite price-scope choices, with unsupported action families left as tooling blockers. Workbook package/schema validation passed and protected workbook/source/publication hashes remained unchanged.

Residual boundary: unsupported relationship, identity-retention, comparator-confirmation, and removal actions require explicit compiler consumers before a future browser pass may expose them. Milestone 3 remains separately unapproved; no `pass-c-3`, workbook write, generation, publication, promotion, deployment, or dealer authority is implied.
