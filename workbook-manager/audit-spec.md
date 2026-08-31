# Workbook Manager Audit Remediation Specification

Status: proposed 2026-08-29. This specification resolves the remediation scope
identified in `wbookMgrAuditRpt.md`; it does not authorize implementation by
itself. Once implementation is authorized, a checkpoint proceeds under
`AGENTS.md` autonomy rules and must still stop at its exit gate before a later
checkpoint begins; a further explicit approval is required only where a
checkpoint raises a new product, architectural, or protected-boundary decision,
such as Checkpoint 2D's writable-capability expansion.

## 1. Decision, authority, and scope

The Workbook Manager is safe enough to execute its guarded draft-to-apply
pipeline, but the audit proves that it is not yet dependable as the primary
workbook-management interface. This specification closes that gap without
replacing the workbook, durable workflow, immutable ChangeSet, guarded writer,
or generated-publication architecture.

Authority order:

1. `AGENTS.md` owns conduct, source boundaries, approval gates, validation, and
   handoff.
2. `wbookMgrAuditRpt.md` owns the observed 2026-08-29 audit evidence, findings,
   priorities, and recommended remediation direction.
3. This specification owns the remediation requirements, checkpoint boundaries,
   and acceptance mapping for that audit backlog.
4. The live workbook registry, Workbook Manager code, and tests own current
   implementation facts and identify the existing mechanisms to reuse.
5. The root and Workbook Manager READMEs own current commands. The validation
   catalog owns gate selection, isolation, serialization, and CI inventory.

The completed workflow specifications at
`docs/superpowers/specs/2026-07-22-reliable-workbook-database-workflow.md` and
`docs/superpowers/specs/2026-08-21-workbook-manager-ux-recovery.md` are historical
delivery evidence only. They are not implementation authority for this work,
are not required checkpoint reading, and must not override the audit report or
this specification. An implementer may consult them only when live code and
tests do not explain why an existing mechanism is present.

If live code, workbook shape, tests, or a higher authority contradicts this
specification, implementation stops long enough to classify the discrepancy as
stale spec text, implementation debt, or a decision requiring approval. It must
not invent business data or weaken a safety boundary to make a pass green.

### 1.1 Implementation simplicity rule

Use the smallest change that directly fixes the audited behavior and passes the
checkpoint acceptance scenarios. Reuse the current registry, projection,
durable-draft routes and tables, ChangeSet services, shared editor controls,
navigation helpers, and test owners wherever they already provide the needed
path. Extend an existing mechanism before creating a parallel one.

The implementation must not add a framework, abstraction layer, compatibility
path, database migration, lifecycle state, endpoint, payload shape, or custom
editor merely because an earlier specification proposed one or because it might
be useful later. Add such machinery only when live evidence proves the current
mechanisms cannot satisfy the audited outcome; record that evidence and observe
the approval gates in §13. The “Required work” lists below define outcomes and
the expected reuse path, not permission to build every listed idea as a new
subsystem. Where the audit report offers alternatives, choose the simplest one
that is truthful, safe, and fully testable.

### 1.2 In scope

- durable workflow history and recovery presentation;
- reachable management for registered structure families;
- mutable-operation discard and rejected-draft correction;
- accurate apply errors and per-entity model scope;
- consistent Images model scope and practical media triage;
- guided option creation and explicit dependency-delete plans;
- safe raw deletion and Advanced workspace continuity;
- draft-effective connected detail;
- direct management of the four preserved-but-unprojected sheets, following an
  explicit registry/write-capability approval gate;
- Groups discovery, search/diagnostic state, navigation cleanup, human labels,
  responsive containment, dead-control removal, and lifecycle-copy cleanup.

### 1.3 Out of scope and preserved boundaries

This work does not:

- make SQLite canonical or allow draft overlays to masquerade as workbook data;
- change the immutable `workbook-changeset-1` payload or introduce another
  mutation dialect;
- bypass preview, approval, typed Apply and Rebuild confirmation, rollback,
  regeneration, publication, or verified re-import;
- restore legacy staging/sync as a current workflow;
- permit any workbook write outside the existing guarded writer;
- choose product availability, prices, defaults, relationships, labels, copy,
  promotion state, source routing, variant membership, or summary ordering;
- hand-edit generated artifacts or `form-app/data.js`;
- change the customer form, dealer endpoint/payload/Turnstile behavior,
  deployment, production cache purge, or WordPress media;
- add a frontend/backend dependency without separate approval;
- support multiple Uvicorn workers or bypass FastAPI lifespan startup.

## 2. Baseline diagnosis and definition of done

The audit exercised every primary workspace, all six models, all 96
model/collection combinations, and a complete isolated edit/apply/rebuild/
re-import round trip. It found no representative lost operation and proved
rollback after downstream failure. The failure is therefore not the guarded
writer; it is incomplete management coverage, misleading audit/recovery state,
incorrectly scoped presentation, and high-friction graph maintenance.

This specification is complete only when:

1. every P1, P2, and P3 ledger item in §3 has an implemented pass and acceptance
   evidence;
2. every WM-001 through WM-011 finding maps to at least one ledger item and one
   acceptance scenario in §§4 and 10;
3. all registered writable families are reachable through a schema-driven
   editor, and each preserved unprojected sheet has either the approved direct
   management path required by P2.9 or an explicit user-approved exception;
4. an operator can correct a mutable or rejected draft without silently changing
   an immutable ChangeSet or recreating unrelated valid work;
5. audit history, apply failures, per-change model scope, and Images model scope
   never contradict durable evidence;
6. option creation and dependency deletion can produce a complete explicit final
   graph without requiring blind raw-row assembly;
7. draft-effective values and navigation state remain truthful after Save,
   reload, filter reset, and workspace transitions;
8. focused API/UI tests, the current catalog-selected Manager gates, production
   frontend build, and required real-browser scenarios pass for each checkpoint;
9. protected workbook/generated/customer-runtime hashes or diffs prove no change
   for read-only checkpoints, and approved write-capability checkpoints prove the
   full guarded rollback/generation/publication path in isolated copies;
10. the owning spec and `fable5loop/STATE.md` record exact completion evidence,
    open decisions, and the next authorized action at every stop.

## 3. Exhaustive priority ledger

This ledger intentionally preserves all 23 items from audit report §9. An item
must not be deleted, merged away, or declared covered by adjacent work without
its own acceptance evidence. P0 remains empty because the audit found no
confirmed corruption or rollback failure.

### P0

No confirmed P0 defect. Any future evidence of workbook corruption, unverified
rollback presented as safe, direct write bypass, ChangeSet identity loss, or
cross-draft apply immediately creates a P0 stop and supersedes this sequence.

### P1 — required before treating the Manager as primary workbook authority

- [x] **P1.1 / WM-001 — Durable workflow history.** Replace the misleading
  legacy-only Change History presentation with current durable draft/apply
  history; retain legacy rows only under an explicitly labeled legacy surface.
- [x] **P1.2 / WM-002 — Structure management.** Add reachable schema-driven
  editors for promotion, workbook source routing, variant definitions,
  model-variant membership, order-summary sections, and step-summary mappings.
- [ ] **P1.3 / WM-003 — Draft correction.** Add operation discard for mutable
  drafts and an audited fork/correction path for validation-rejected immutable
  drafts.
- [ ] **P1.4 / WM-004 — Apply failure evidence.** Surface apply-attempt failures
  directly and eliminate the false “No recorded warnings or failures” state.
- [ ] **P1.5 / WM-005 — Per-entity model scope.** Render operation/entity-specific
  model context; reserve the union for the draft summary.
- [ ] **P1.6 / WM-006 — Images model scope.** Eliminate disagreement between the
  global model header and Images filters/results/actions.

### P2 — required for dependable daily maintenance

- [ ] **P2.1 / WM-008 — Guided option creation.** Create an option together with
  explicit active-variant OVS coverage.
- [ ] **P2.2 / WM-008 — Dependency-delete planning.** Build an explicit,
  selectable option/group dependency plan and bulk-draft the chosen ordinary
  operations.
- [ ] **P2.3 / WM-007 — Raw-delete safety.** Require confirmation or offer an
  immediate, durable Undo before a no-dependent delete remains in the draft.
- [ ] **P2.4 / WM-007 — Advanced continuity.** Preserve selected model,
  collection, search, page/offset, scroll, and editor context after draft saves.
- [ ] **P2.5 / WM-009 — Media target lookup.** Replace the 837-item native select
  with bounded searchable/paged assignment-target selection.
- [ ] **P2.6 / WM-009 — Media feedback.** Show explicit empty-result and API-error
  states for inventory/media search.
- [ ] **P2.7 / WM-009 — Wildcard conflicts.** Distinguish presentation editing
  from ownership-conflict resolution and provide a truthful resolution path or
  an explicit blocked reason.
- [ ] **P2.8 / WM-010 — Draft-effective details.** Render proposed effective
  values beside authored/base values throughout connected details.
- [ ] **P2.9 / WM-002 — Preserved-sheet management.** Add approved direct
  management for `PriceRef`, `context_choice_copy`, `rule_phrase_map`, and
  `runtime_rule_exceptions`, with registry-owned schemas and guarded writes.

### P3 — usability and polish

- [ ] **P3.1 / WM-011 — Groups index.** Add a browse/index mode with useful
  counts and stable ordering; search must not be required to discover groups.
- [ ] **P3.2 / WM-011 — Search classes.** Distinguish direct identity/name matches
  from descriptive mentions and relationship matches.
- [ ] **P3.3 / WM-011 — Diagnostics mode.** Present diagnostics as a separate
  result state rather than appending them below retained search results.
- [ ] **P3.4 / WM-011 — Query cleanup.** Clear query parameters that are
  irrelevant to the destination workspace while preserving canonical reloadable
  context.
- [ ] **P3.5 / WM-009 and WM-011 — Human labels.** Improve human labels for
  section IDs and raw technical fields without replacing canonical IDs in
  technical evidence.
- [ ] **P3.6 / WM-011 — Narrow containment.** Contain Advanced tables/toolbars at
  390x844 without document-level horizontal overflow.
- [ ] **P3.7 / WM-009 — Coverage control.** Remove button semantics from the dead
  overall-coverage tile or implement a defined filter/navigation action.
- [ ] **P3.8 / WM-011-adjacent audit UX — First-run/lifecycle copy.** Consolidate
  duplicate first-run reload actions and standardize lifecycle naming while
  keeping the exact typed Apply and Rebuild confirmation unchanged.

## 4. Finding-to-pass traceability

| Audit finding | Priority items | Owning implementation checkpoint | Required acceptance scenarios |
|---|---|---|---|
| WM-001 | P1.1 | 1A | HIST-01–04 |
| WM-002 | P1.2, P2.9 | 1B, 2D | STRUCT-01–04, PRES-01–05 |
| WM-003 | P1.3 | 1C | DRAFT-01–05 |
| WM-004 | P1.4 | 1D | APPLY-ERR-01–03 |
| WM-005 | P1.5 | 1D | SCOPE-01–03 |
| WM-006 | P1.6 | 1E | IMG-SCOPE-01–03 |
| WM-007 | P2.3, P2.4 | 2A | RAW-01–04 |
| WM-008 | P2.1, P2.2 | 2A | GRAPH-01–06 |
| WM-009 | P2.5–P2.7, P3.5, P3.7 | 2B, 3B | MEDIA-01–06, POLISH-01–06 |
| WM-010 | P2.8 | 2C | EFFECTIVE-01–04 |
| WM-011 | P3.1–P3.4, P3.6, P3.8 | 3A, 3C | DISC-01–06, NAV-01–03, RESP-01–02 |

The first implementation edit in any checkpoint must update this table if live
evidence proves the mapping wrong. No finding may be removed; a remap must name
the replacement item and preserve its acceptance scenario.

## 5. Cross-cutting product and data contracts

### 5.1 Registry ownership and fail-closed editing

All editing controls derive from
`scripts/corvette_form_generator/workbook_domain/registry.py`. The Manager may
add projection/read-model metadata, but must not create a second writable-column,
enum, reference, key, or parent/member registry in Python or React.

A reachable editor must use the existing versioned schema response and shared
`RecordForm`/`EditorShell`. Unknown controls, missing control metadata, read-only
fields in mutation payloads, immutable-key changes, unresolved references, and
invalid blank semantics fail closed. Contextual editors may add grouping,
prefill, and outcome-oriented labels; they may not reclassify controls.

P2.9 is a deliberate capability expansion. Before implementation, the agent
must inventory each preserved sheet’s exact headers, key, consumers, generated
impact, reference domains, blank semantics, and current preservation behavior.
It then proposes the exact registry family additions and stops for approval
because those additions create new writable capability. After approval,
projection, editor, ChangeSet, writer, validation, and generated-parity paths
must all derive from the registry additions.

### 5.2 Draft-effective versus authored data

Every connected read keeps two explicit layers:

- **Authored/base:** the verified projection imported from the bound workbook.
- **Proposed effective:** the final value after applying the active draft’s
  coalesced operations to that exact physical row or relationship graph.

A draft overlay is never labeled workbook-current or generated-parity-verified.
Stale workbook identity, terminal draft, invalid ownership, ambiguous row
identity, or overlay conflict produces a visible blocked/conflicted state and
must not overwrite authored presentation.

### 5.3 Model scope

Scope is derived from operation ownership and stored `model_context`, never from
an ambient global selector or draft-wide union.

- Draft summary shows the deduplicated union.
- Each review entity shows only its own operation/entity scope.
- Global/shared rows show their complete derived context, not `*` or the current
  header model.
- Images results and mutations use one explicit effective model scope. “All
  models” is allowed only if the global header and Review context expose that
  same state.
- A model switch cancels or ignores stale in-flight responses.

### 5.4 Audit and recovery evidence

The normal history surface is a read model over durable workflow evidence:
`workflow_drafts`, coalesced operations or immutable ChangeSet operations,
preview attempts, approval attempts, apply attempts, asset-resolution evidence,
cancellation/manual-resolution state, workbook identity, actor, timestamps,
affected models, and outcomes.

History rules:

- Applied, cancelled, rejected, restored/retryable, abandoned-unknown, and other
  terminal workflow records remain visible and paginated.
- A record links to the exact durable draft detail and immutable technical
  artifacts.
- Mutable drafts are not called committed/applied history.
- Legacy `change_history` rows remain available only as “Legacy staging history”
  and cannot be combined into current workflow counts without a source label.
- API pagination has stable newest-first ordering with a deterministic tie-break.
- No history read mutates state or requires a current projection.

### 5.5 Error presentation

One normalized presentation adapter classifies messages from preview, approval,
apply, rollback, and manual recovery while preserving the raw immutable result.
The empty state is shown only when all applicable sources contain no messages.
An apply failure summary names:

- failed stage;
- concise exception/error;
- workbook and output rollback state;
- whether retry/cancel is safe;
- the next permitted action.

Unknown restoration must never present retry or cancel as safe.

### 5.6 Coordinated graph operations

Guided workflows compose ordinary typed draft operations; they do not add a
cascade flag, hidden bulk mutation, alternate payload, or automatic business
choice.

Option creation:

1. capture the option row through registry controls;
2. enumerate active variants from workbook-owned model/variant registration;
3. require an explicit OVS status for every required variant;
4. preview the exact option plus OVS operations and any unresolved references;
5. save all operations atomically to one mutable draft or save none.

Dependency deletion:

1. resolve direct and transitive dependents from the final draft-effective graph;
2. classify each by family, physical row, model context, and why it blocks;
3. preselect nothing destructive merely because it is a dependent;
4. let the operator explicitly choose the complete deletion/deactivation plan;
5. reject incomplete plans before lock where deterministically knowable;
6. emit ordinary typed operations atomically and show the exact plan in Review.

Existing shared rows or relationships outside the selected entity must not be
silently deleted. Product-rule decisions remain user-authored.

### 5.7 Navigation and refresh

Draft Save refreshes only the durable evidence needed by the active workspace.
It must not unmount the workspace through a transient global-not-ready state.
Canonical navigation state may preserve model, workspace, entity type/ID,
search mode/query, collection, page/offset, and selected asset ID when they are
valid for the destination. Transient editor dirtiness, secrets, raw result
objects, and stale cross-workspace query parameters are not URL state.

## 6. P1 implementation checkpoints

Each checkpoint is independently useful and must be authorized, RED-tested,
implemented, browser-proved where visible, closed in this specification, and
stopped before the next begins.

### Checkpoint 1A — trustworthy durable workflow history

Objective: close P1.1 / WM-001.

Required work:

1. Add focused RED API tests proving an applied current-workflow draft is absent
   from the existing legacy response/panel.
2. Build a versioned, paginated durable workflow-history read model satisfying
   §5.4. Prefer additive backend composition over changing durable evidence.
3. Make Advanced & Recovery lead with “Workflow history”; move the existing
   source to a separately labeled “Legacy staging history” disclosure.
4. Add terminal-state filters, affected-model filter, outcome summary, actor/time,
   exact draft link, and expandable technical evidence.
5. Prove history remains readable with stale/missing projection and after browser
   reload.

Forbidden: migrating or deleting legacy rows, rewriting immutable attempts,
changing apply semantics, or claiming mutable drafts are applied.

Exit gate: HIST-01–04 pass; an isolated successful apply and a downstream
failure with proven rollback/restoration both appear once with correct evidence;
legacy rows remain separately readable.

**Closed 2026-08-29 — implementation `230ed99`.** The additive
`workbook-manager-workflow-history-1` read model now composes durable draft,
operation, ChangeSet, preview, approval, apply, asset-resolution, cancellation,
and manual-recovery evidence without consulting or mutating the projection.
Server-side status/model filters, deterministic newest-first pagination, a
fixed ten-query budget, invalid-filter refusal, and a write-denying test cover
the read contract. Advanced & Recovery leads with the current workflow record,
keeps retired staging/sync rows in a separately counted legacy disclosure, and
opens the exact durable draft.

Acceptance evidence:

- HIST-01: isolated applied evidence appears once with actor/time, base and
  saved hashes, model and operation count, current generation/publication state,
  and exact-draft navigation.
- HIST-02: an `apply_rebuild_failed_rolled_back` attempt reports the failed
  rebuild/publication stage, exception, restored workbook/generated/publication
  surfaces, verified rollback, and only retry/cancel next actions.
- HIST-03: cancelled and preview-rejected drafts remain independently paginated
  and are never summarized as applied, even with the projection removed.
- HIST-04: one legacy staging row remains readable only in `Legacy staging
  history` and does not change the two-record workflow total.

Checkpoint drift disposition:

| Surface | Checkpoint 1A disposition |
|---|---|
| Registry/workbook authority | Inspected, no change; history reads existing durable evidence only. |
| Projection representation | Inspected, no change; missing-projection API and browser proofs pass. |
| API/read model | Added versioned `/api/workflow-history` with filters, bounded pagination, stable ordering, technical evidence, and explicit invalid-status errors. |
| Editor/mutation capability | No change; authorizer-backed tests prove the history query cannot insert, update, or delete. |
| Draft overlay/review/history | Workflow history is primary; exact-draft navigation refreshes the bound lifecycle before opening Review & Apply; legacy history remains separate. |
| Writer/apply impact | Inspected, no change; immutable attempts are read, never rewritten, and apply semantics are untouched. |
| Generator/publication impact | No change; protected workbook, runtime contracts, registry bundle, and cache-bearing HTML remained byte-identical to preflight. |
| Focused test owner | `test_workbook_manager_api_concurrency.py` and `test_workbook_manager_review_presentation.py`; catalog placement unchanged because no new test file was added. |
| README/User Guide | Updated current/legacy history ownership, workspace names, filters, exact-draft navigation, and recovery availability. |

Validation: focused RED failures proved the missing endpoint (`404`), missing
workflow-first presentation, missing exact-draft refresh, and omitted asset
evidence before each implementation slice. The final catalog-selected Manager
serial group passed; that run on 2026-08-29 collected 356 tests, 2 skips, and 74
subtests with one existing Starlette/httpx deprecation warning. Those numbers are
dated evidence of one run, not a live inventory claim —
`tests/validation_catalog.json` owns collection counts. Python compilation,
frontend production build, and `git diff --check` passed. Isolated real-browser
proof at desktop and 390x844 showed the successful and restored outcomes, separate legacy count,
projection-independent reload, expandable evidence, exact-draft one-change
review, Back/Forward restoration, keyboard focus, zero console errors, and no
document overflow. Checkpoint 1B was separately authorized and is closed below.

### Checkpoint 1B — reachable registered structure management

Objective: close P1.2 / the registered-family half of WM-002.

Families:

- `model_registry_promotion`;
- `model_workbook_sources`;
- `variant_master`;
- `model_variants`;
- `order_summary_sections`;
- `step_order_summary_map`.

Required work:

1. Derive a structure-family index from the registered specs; do not copy the
   list into frontend routing as a second authority.
2. Expose every family through the shared schema/editor shell as a raw fallback.
3. Add contextual promotion, source-routing, variant-membership, and summary-map
   views that compose the same generic editor rather than forking forms.
4. Show lineage, model/shared context, dependencies, active state, and generated
   impact before Save.
5. Provide create/update/delete only where the existing registry and dependency
   contracts permit it; blocked operations display the exact reason.
6. Prove a newly registered writable structure family automatically appears or
   causes an exhaustive completeness test to fail.

No implementation may choose promotion, routing, membership, labels, or order.
Tests use isolated copies and authored fixture values.

Exit gate: STRUCT-01–04 pass; all six families are reachable without Advanced
URL knowledge; schema/control parity is exhaustive; no workbook write occurs on
Save.

**Closed 2026-08-29 — implementation `f0e023d`.** Form Overview now exposes a
registry-derived fixed-sheet structure index through the existing versioned
schema, `ModelOperations`, `RecordForm`, and `EditorShell` path. Promotion,
source routing, variant definitions and membership, order-summary sections, and
step-summary mappings are reachable without Advanced URL knowledge. Contextual
evidence names source lineage, model/shared scope, dependencies, active state,
and guarded generated impact before Save. Action-specific capabilities and
blocked reasons call the same ownership guard as durable mutation; row-specific
delete inspection still uses the shared dependency contract. A synthetic
registered fixed-sheet spec proves API index completeness follows registry
membership.

Acceptance evidence:

- STRUCT-01: all six required families appeared in the registry-derived index
  and opened the shared schema-driven editor; focused endpoint/source tests pass.
- STRUCT-02: an isolated `model_registry_promotion` note update persisted one
  coalesced operation owned by `model_registry_promotion`, source row 2,
  `model_context=["stingray"]`; projection and copied/canonical workbooks stayed
  byte-identical.
- STRUCT-03: create/update/delete capabilities are evaluated independently by
  the durable mutation ownership guard; model creation and read-only sections
  expose the guard's exact blocked reason, while row delete dependencies remain
  enforced by the existing dependency endpoint.
- STRUCT-04: injecting a synthetic writable fixed-sheet `TableSpec` makes both
  `structure_specs()` and the `/api/tables` response include its schema and
  capabilities; removing Manager exposure can no longer pass against a closed
  family list.

Checkpoint drift disposition:

| Surface | Checkpoint 1B disposition |
|---|---|
| Registry/workbook authority | Inspected, no change; index membership, writable fields, controls, and ownership derive from registered specs. |
| Projection representation | Inspected, no schema change; isolated import remained package/schema-valid and semantic-readback verified. |
| API/read model | `/api/tables` now returns model-aware registry-derived structure-family context while preserving the existing schema inventory. |
| Editor/mutation capability | Existing shared browser/editor accepts the derived family index; Save still emits ordinary durable draft operations only. |
| Draft overlay/review/history | One isolated structure update appeared as one owned durable operation and survived reload; no lifecycle/history contract changed. |
| Writer/apply impact | Inspected, no change; no Apply/Rebuild or workbook write ran. |
| Generator/publication impact | No change; canonical workbook, copied workbook, six runtime contracts, published data, and cache-bearing HTML retained preflight SHA-256 values. |
| Focused test owner | `test_workbook_manager_catalog.py` and `test_workbook_manager_form_graph.py`; no new catalog entry required. |
| README/User Guide | Updated structure-index architecture and operator steps. |

Validation: initial focused RED runs failed on the absent registry selector,
family response, and Form Overview path. PR review then reproduced two P2
defects: stale rows/actions remained available during a family transition, and
table editability incorrectly advertised model creation. Loaded table/model
identity now fail-closes every action during transitions, and the API delegates
each action to the durable mutation guard. A three-second CDP network delay
proved loading state, zero stale rows/key metadata, disabled Add, correct
post-load source-routing rows/key, the model-create refusal, and zero console
errors. Final focused owners passed. The catalog-selected Manager
serial group passed; that run on 2026-08-29 collected 33 focused-owner tests and
335 group tests, 2 skips, and 74 subtests with one existing Starlette/httpx
deprecation warning. Those numbers are dated evidence of one run, not a live
inventory claim — `tests/validation_catalog.json` owns collection counts. Python
compilation, frontend production build, and `git diff --check` passed. Isolated
import reported package/schema-valid and verified semantic readback. Real Chrome at desktop and 390x844 reached counts 1/11/32/6/11/13 for
the six families, opened promotion evidence, saved exactly one correctly owned
draft update, preserved it after reload, reported zero console/runtime errors,
and measured no document overflow (1425=1425; 390=390). Workbook-write,
generation/publication, dealer, deployment, and WordPress mutation gates were
not run because this checkpoint saves draft intent only; protected hashes prove
those surfaces unchanged. Residual risk: none implied. Checkpoint 1C remains
unauthorized.

### Checkpoint 1C — correctable mutable and rejected drafts

Objective: close P1.3 / WM-003.

Required work:

1. Add a visible remove/discard action for each mutable draft operation with a
   semantic confirmation and resulting graph/impact preview.
2. Reuse existing coalescing semantics so full reversion removes effective
   intent rather than creating a compensating no-op.
3. Add one atomic “Create correction draft” action for `preview_rejected`:
   preserve the rejected ChangeSet/attempt, terminally cancel the old draft with
   an explicit correction reason, create a new mutable draft bound to the same
   current projection, and copy the selected operations as fresh mutable intent.
4. Default the correction draft to all rejected operations selected, but let the
   operator exclude operations before creation; show counts and affected models.
5. Refuse correction when workbook/projection identity changed, restoration is
   unknown, another nonterminal draft exists, or operation ownership no longer
   resolves. The safe next action must be explicit.
6. Replace impossible “fix and revalidate” copy with the actual available action.

The transition must be transactional: either old-draft terminal disposition and
new draft creation both persist, or neither does. It must not mutate the stored
ChangeSet, preview, or attempt JSON.

Exit gate: DRAFT-01–05 pass, including a six-OVS rejection corrected without
recreating an unrelated valid operation.

### Checkpoint 1D — truthful failure and entity scope presentation

Objective: close P1.4/P1.5 (WM-004/WM-005).

Required work:

1. Make the warning/failure empty-state predicate include preview, approval,
   apply, rollback, and manual-recovery messages.
2. Add the concise apply summary from §5.5 above raw JSON.
3. Extend semantic review summaries so each entity carries its exact operation
   IDs and derived model context; render that scope per entity.
4. Keep the draft-wide union only in the draft summary and apply-impact overview.
5. Prove shared/global row context, mixed-model drafts, single-model drafts, and
   an apply failure with successful rollback.

Exit gate: APPLY-ERR-01–03 and SCOPE-01–03 pass; no contradictory empty state or
scope label remains.

### Checkpoint 1E — one visible Images model scope

Objective: close P1.6 / WM-006.

Pinned product behavior: “Clear filters” clears secondary Images filters but
preserves the current global model. An explicit “All models” choice may still be
provided, but selecting it must update the global header/context before results
or actions become available.

Required work:

1. Centralize effective scope derivation; local filter state cannot silently
   diverge from application context.
2. Make Clear filters preserve the selected model.
3. Ensure deep links/reloads reconcile selected asset ownership with visible
   scope and show a refusal rather than silently switching models.
4. Bind all asset draft operations and Review links to the same visible scope.
5. Guard stale responses during model changes.

Exit gate: IMG-SCOPE-01–03 pass for single-model clear, explicit all-model mode,
and rapid model switching.

## 7. P2 implementation checkpoints

### Checkpoint 2A — coordinated graph maintenance and safe raw operations

Objective: close P2.1, P2.2, P2.3, and P2.4 / WM-007 and WM-008.

Required subpasses:

1. inventory option-add requirements and dependency families directly from the
   registry, projection, final-graph preview, and current tests;
2. add RED helper/API tests for complete active-variant OVS enumeration and
   dependent classification;
3. implement the option + OVS workflow in §5.6;
4. implement explicit option/group dependency plans in §5.6;
5. make plan save atomic and idempotent against the active mutable draft;
6. add confirmation plus immediate draft Undo for raw no-dependent deletes;
7. keep model, collection, query, offset, scroll, and editor context after every
   Save/Delete/Undo by refreshing draft evidence in place;
8. show pre-lock incompleteness when deterministically known while retaining
   final-graph preview as authority.

Forbidden: automatic cascade selection, hidden OVS defaults, invented statuses,
partial bulk persistence, or bypassing final-graph validation.

Exit gate: GRAPH-01–06 and RAW-01–04 pass; isolated browser proof creates one
option with complete OVS coverage, plans a connected delete without committing
unselected dependencies, undoes a raw delete, and retains Advanced context.

### Checkpoint 2B — practical and truthful media triage

Objective: close P2.5, P2.6, and P2.7 / the operational portion of WM-009.

Required work:

1. reuse the existing bounded media/record reference pattern for a searchable,
   paged target picker with human primary labels and canonical secondary IDs;
2. define loading, no-results, API-error, retry, stale-inventory, and selection
   states; never collapse an error into an empty result;
3. split “Edit presentation” from “Resolve ownership conflict”;
4. for wildcard conflicts, show candidate wildcard/current exact ownership,
   affected targets/models, allowed ordinary asset operations, and any reason an
   unambiguous resolution cannot be authored;
5. keep fingerprint binding and reconciliation refresh semantics intact;
6. preserve assignment target, candidate URL, and unsaved-close protection.

Exit gate: MEDIA-01–06 pass with bounded query counts and real-browser evidence
for no results, API failure/retry, paged assignment, resolvable conflict, and
blocked ambiguous conflict. No WordPress mutation occurs.

### Checkpoint 2C — draft-effective connected details

Objective: close P2.8 / WM-010.

Required work:

1. create one backend/helper overlay adapter for projected row + exact coalesced
   draft operation; do not patch headings independently in React;
2. expose authored and proposed effective fields, changed-field list, operation
   identity, stale/conflict state, and direct impact;
3. apply it to option, group, section, and structure detail surfaces that permit
   draft edits, plus asset detail where ordinary operations exist;
4. use explicit before/after treatment; proposed deletion must not disappear as
   if never authored;
5. prove Save, close/reopen, hard reload, Back/Forward, full reversion, stale
   binding, add, modify, and pending delete.

Exit gate: EFFECTIVE-01–04 pass and no surface shows a “Draft modified” badge
beside only the stale authored value.

### Checkpoint 2D — direct management of preserved sheets

Objective: close P2.9 / the unprojected-sheet half of WM-002.

Authorization gate: this checkpoint first produces the exact four-family
registry/write proposal required by §5.1 and stops for explicit approval. No
implementation follows merely from approval of an earlier checkpoint.

Required family inventory:

| Sheet | Required management outcome | Consumer/impact proof required before approval |
|---|---|---|
| `PriceRef` | direct browse/search and guarded add/update/delete | pricing/interior component readers, key/reference semantics, affected-model derivation |
| `context_choice_copy` | contextual choice-copy browse and guarded add/update/delete | generated context-choice consumer, body/context references, copy fields |
| `rule_phrase_map` | direct browse/search and guarded add/update/delete | parser/generator consumers, phrase uniqueness/order/default semantics |
| `runtime_rule_exceptions` | direct browse/search and guarded add/update/delete, including a truthful empty state | runtime-exception consumer, model/option references, active/empty-sheet behavior |

Required work after approval:

1. register each family once in the workbook-domain registry with complete keys,
   columns, controls, references, active/blank semantics, and ownership;
2. project rows with exact source lineage and round-trip preserved values;
3. expose contextual or schema-driven raw editing without a custom write path;
4. include the families in ChangeSet parsing, dependency inspection, preview,
   guarded apply, affected-model derivation, export/re-import, and history;
5. add complete-candidate inventory tests so empty `runtime_rule_exceptions` is a
   positively represented empty family, not omitted coverage;
6. prove generated parity from an isolated copied-workbook edit for each family,
   including a no-runtime-impact case where appropriate;
7. update READMEs only after commands/architecture/operator guidance actually
   change.

Exit gate: PRES-01–05 pass; all four sheets are represented and editable through
the guarded lane; no row is lost on unchanged export/re-import; generated impact
matches fresh isolated generation; the canonical workbook remains untouched by
validation.

## 8. P3 implementation checkpoints

### Checkpoint 3A — discoverable Groups, classified search, diagnostics mode

Objective: close P3.1, P3.2, and P3.3.

Required work:

1. add a paginated Groups index scoped by model and group type, with authored
   label first, canonical ID second, member count, active state, stable sort, and
   explicit empty state;
2. retain search, but classify every result as direct identity/name, descriptive
   mention, or relationship; one record may expose multiple reasons without
   appearing as unexplained duplicates;
3. make ranking deterministic and direct matches precede mentions;
4. make diagnostics a distinct navigation/result mode with its own heading,
   count, parameters, and empty/error state;
5. preserve Back/Forward and reload for index, search, detail, and diagnostics.

Exit gate: DISC-01–06 pass with query budgets and real-browser proof.

### Checkpoint 3B — human technical labels and dead coverage control

Objective: close P3.5/P3.7 and the remaining presentation portion of WM-009.

Required work:

1. centralize human display labels using workbook-authored names and registry
   field labels; do not manufacture business labels from IDs;
2. lead section filters/cards with authored section name and retain section ID as
   secondary technical evidence;
3. give raw columns and relationship types plain labels while preserving exact
   field/table/ID evidence in details;
4. either render overall coverage as a noninteractive summary or give it one
   defined action that sets visible filters and navigation state. A button with
   no handler is forbidden;
5. test keyboard semantics and accessible names for every changed control.

Exit gate: POLISH-01–06 pass; no dead button semantics remain and canonical
identifiers stay recoverable.

### Checkpoint 3C — navigation cleanup, narrow Advanced, first-run copy

Objective: close P3.4/P3.6/P3.8 and the remaining WM-011-adjacent audit items.

Required work:

1. define valid query keys per workspace in the existing navigation-state owner;
   destination navigation drops irrelevant keys without deleting model/draft or
   canonical entity context that remains valid;
2. contain wide tables/toolbars inside an accessible horizontal region, keep
   primary controls visible, and prevent document-level overflow at 390x844;
3. replace icon-only destructive raw actions with visible text or a reliably
   associated accessible label and confirmation/Undo state;
4. expose one first-run import/reload primary action; secondary status details may
   link to it but must not duplicate the action;
5. standardize Save-to-draft, Lock changes, Validate changes, Approve changes,
   Apply and Rebuild, Retry, Cancel, correction, and recovery language across
   banners, tray, Review, Images, and Advanced;
6. preserve the exact `APPLY AND REBUILD` typed confirmation and all safety-state
   distinctions.

Exit gate: NAV-01–03 and RESP-01–02 pass at desktop and 390x844 with keyboard
navigation, no document overflow, no duplicate first-run primary action, and no
unsafe lifecycle wording.

## 9. Implementation surfaces and migration/drift map

The agent must trace live definitions/usages before editing. Expected surfaces
are guidance, not permission to invent or modify absent symbols.

| Concern | Likely implementation owners | Companion impact to inspect |
|---|---|---|
| Workflow history | `backend/app/drafts.py`, `main.py`, durable DB read helpers, `HistoryView.jsx`, `api.js` | durable schema/migrations only if unavoidable; legacy recovery tests; User Guide |
| Structure management | workbook-domain registry, `catalog.py`, structure/explorer routes, `FormStructure.jsx`, shared editor | workbook schema validation, dependency APIs, generated ownership |
| Draft correction | `drafts.py`, lifecycle routes/models, `ChangesSync.jsx`, API client | terminal-state set, import containment, concurrency/transaction tests |
| Apply errors/scope | `apply_rebuild.py`, review summary assembler, `ChangesSync.jsx` | immutable attempt shape, recovery actions, mixed-model tests |
| Images scope/triage | `AssetManager.jsx`, navigation state, asset workspace/resolutions APIs | fingerprint/stale behavior, review links, image parity owner |
| Graph workflows/raw continuity | registry relationship metadata, dependency APIs, `ModelOperations.jsx`, `RecordForm`/editor shell | final-graph preview, coalescing, atomic operation API, navigation |
| Draft-effective detail | explorer/form-graph overlay helpers, connected components | stale/conflict classification, review summary identity |
| Preserved sheets | workbook-domain registry, importer/projection, catalog, changeset/writer consumers | package/schema, generated parity, export/re-import, affected models |
| Search/Groups/diagnostics | `explorer.py`, connected components, navigation state | pagination, ranking, query budgets, deep links |
| Responsive/copy | `styles.css`, shared components, User Guide after implementation | frontend build, keyboard/accessibility, 390x844 browser proof |
| Validation inventory | `tests/validation_catalog.json`, focused test owners | catalog change scope, README drift checks, state-handoff count claims |

For every checkpoint, record a drift table with these states:

- registry/workbook authority;
- projection representation;
- API/read-model representation;
- editor/mutation capability;
- draft overlay/review/history representation;
- writer/apply impact;
- generator/publication impact;
- focused test owner;
- README/User Guide impact, recorded as updated without contradicting the
  catalog: published commands equal the catalog's, named gates still exist, no
  hand-maintained collection count, and only catalog layer names.

A green comparison over two surfaces that both omit a family is not parity.
Coverage tests enumerate the union of registry families, projected families,
editable routes, and relevant generated consumers, then classify every member.

## 10. Acceptance scenario catalog

### History

- **HIST-01:** Successful isolated Apply/Rebuild appears exactly once with actor,
  time, workbook hashes, affected models, operation count, generation/publication
  outcome, and exact draft link.
- **HIST-02:** Downstream failure with proven restoration shows failed stage,
  error, restored surfaces, and retry/cancel availability.
- **HIST-03:** Cancelled and preview-rejected drafts remain discoverable without
  being labeled applied.
- **HIST-04:** Legacy staging row appears only under labeled legacy history and
  does not increment current workflow totals.

### Structure and preserved families

- **STRUCT-01:** Each of the six registered structure families is reachable from
  Form Overview or a structure index and opens the shared schema-driven editor.
- **STRUCT-02:** A structure update saves one correctly owned draft operation and
  leaves workbook/projection/generated outputs unchanged.
- **STRUCT-03:** Add/delete capability and blocked reasons match registry and
  dependency authority for every structure family.
- **STRUCT-04:** Adding a synthetic writable structure spec in a patched registry
  makes completeness follow it or fail with the missing family name.
- **PRES-01:** Every one of the four preserved sheets has registry, projection,
  browse, schema, and guarded mutation coverage.
- **PRES-02:** Unchanged import/export/re-import preserves exact cell values,
  types, row order where semantically owned, formulas, and unrelated sheets.
- **PRES-03:** One isolated copied-workbook edit per family reaches the intended
  cell and no other workbook row.
- **PRES-04:** Fresh isolated generation/publication shows exactly the expected
  affected models/contracts or proves no runtime impact.
- **PRES-05:** Empty `runtime_rule_exceptions` remains visible and add-capable,
  and is included in total-family coverage.

### Draft correction

- **DRAFT-01:** Discarding one mutable operation leaves unrelated operations and
  exact navigation context intact.
- **DRAFT-02:** Full reversion coalesces to no effective operation and updates
  Review/history truthfully.
- **DRAFT-03:** A rejected option-with-missing-OVS draft creates one correction
  draft; the original immutable ChangeSet and failed attempt remain byte-equal.
- **DRAFT-04:** Correction refuses stale projection, ownership conflict, unknown
  restoration, and a competing nonterminal draft with actionable reasons.
- **DRAFT-05:** Forced failure between old-draft cancellation and new-draft
  creation rolls back both sides transactionally.

### Apply evidence and scope

- **APPLY-ERR-01:** Apply-only error prevents the “No recorded warnings or
  failures” empty state.
- **APPLY-ERR-02:** Proven rollback summary permits only safe retry/cancel; unknown
  restoration permits only manual recovery.
- **APPLY-ERR-03:** Raw immutable attempt JSON remains accessible and unchanged.
- **SCOPE-01:** Mixed Stingray/Grand Sport draft shows each entity’s own scope and
  the two-model union only in the summary.
- **SCOPE-02:** Shared/global operation shows its derived complete model context.
- **SCOPE-03:** Missing/ambiguous model context fails closed rather than borrowing
  the current selector.

### Images

- **IMG-SCOPE-01:** Clear filters under ZR1X keeps header, results, and operations
  scoped to ZR1X.
- **IMG-SCOPE-02:** Explicit All models updates header/context before cross-model
  cards become actionable.
- **IMG-SCOPE-03:** Rapid model switching cannot render or save a stale prior-model
  response.
- **MEDIA-01:** Search no matches shows a clear empty state and keeps query/edit
  context.
- **MEDIA-02:** API failure shows error and Retry; it is not rendered as no
  results.
- **MEDIA-03:** Target lookup searches and pages bounded results with human label,
  canonical ID, type, and model context.
- **MEDIA-04:** Assignment selection survives editor refresh and dirty-close
  protection.
- **MEDIA-05:** Resolvable wildcard conflict emits explicit ordinary draft
  operations with before/after ownership.
- **MEDIA-06:** Ambiguous conflict remains blocked with evidence and does not
  imply presentation edits resolve ownership.

### Graph maintenance and Advanced

- **GRAPH-01:** Guided add enumerates every active model variant independently of
  current OVS rows.
- **GRAPH-02:** Missing one OVS decision blocks save before lock and names the
  variant.
- **GRAPH-03:** Atomic option + OVS save emits exactly one option and one OVS row
  per required variant; forced mid-batch failure persists none.
- **GRAPH-04:** Option deletion plan classifies every direct/transitive dependent
  and preselects no destructive action.
- **GRAPH-05:** Incomplete plan is visibly invalid before lock and final-graph
  preview independently rejects it.
- **GRAPH-06:** Group plan respects draft-effective member adds/deletes and shared
  relationship ownership.
- **RAW-01:** No-dependent delete requires confirmation and offers immediate Undo.
- **RAW-02:** Undo removes only that effective operation.
- **RAW-03:** Save/delete/undo retain collection, query, page, scroll, model, and
  open editor context.
- **RAW-04:** Reload/deep link restores canonical Advanced context without stale
  cross-workspace state.

### Draft-effective values

- **EFFECTIVE-01:** Updated option/group/section/structure title and fields show
  authored and proposed values after Save and reload.
- **EFFECTIVE-02:** Added row renders as proposed-only; pending delete remains
  visible with deletion treatment.
- **EFFECTIVE-03:** Full reversion removes proposed treatment.
- **EFFECTIVE-04:** Stale/conflicted overlay never replaces authored value and
  blocks mutation with the exact reason.

### Discovery, polish, navigation, and responsive behavior

- **DISC-01:** Groups index loads useful first-page results without a query.
- **DISC-02:** Direct Z51 match ranks ahead of description mentions and every
  result explains its class.
- **DISC-03:** Relationship match names the relationship evidence.
- **DISC-04:** Diagnostics replace search mode and do not append below stale
  results.
- **DISC-05:** Index/search/diagnostics each survive reload and Back/Forward.
- **DISC-06:** Stable pagination and bounded query counts hold for all modes.
- **POLISH-01:** Section cards/filters lead with workbook-authored names.
- **POLISH-02:** Raw field labels are human-readable and preserve exact technical
  names in evidence.
- **POLISH-03:** No label is invented from an opaque canonical ID.
- **POLISH-04:** Changed controls have correct keyboard semantics and accessible
  names.
- **POLISH-05:** Overall coverage tile is either static or performs its documented
  action and updates visible filters.
- **POLISH-06:** Wildcard conflict and presentation-edit actions have distinct,
  outcome-specific labels.
- **NAV-01:** Workspace transition drops irrelevant query/mode keys and preserves
  valid model/draft/entity context.
- **NAV-02:** One first-run primary import/reload action is visible and operable.
- **NAV-03:** Lifecycle labels are consistent and never describe an unavailable
  action.
- **RESP-01:** Advanced at 390x844 has no document-level horizontal overflow;
  wide tables scroll in a labeled contained region.
- **RESP-02:** Destructive controls, confirmation/Undo, editor footer, focus, and
  errors remain keyboard-visible at desktop and 390x844.

## 11. Test ownership and validation strategy

Implementation selects exact gates from the live READMEs and
`tests/validation_catalog.json`; this specification does not freeze command
strings or measured counts.

The catalog owns gate selection, isolation, serialization, measured timings, and
collection counts. README no longer mirrors that inventory; it must only avoid
contradicting it. A checkpoint that edits README therefore satisfies four
drift checks in `tests/test_validation_catalog.py`: a published command naming a
cataloged script must equal that catalog command exactly, every gate name in
README must still exist on disk, README must not hand-maintain a pytest
collection count, and any `Layer N` reference must name a catalog layer. Prefer
pointing at the catalog over copying it.

### 11.1 Focused owners

Prefer bounded owner files rather than expanding the monolithic Manager suite:

- durable history and correction lifecycle: existing draft/lifecycle owners or a
  new focused history owner;
- structure/preserved-family completeness: catalog, control metadata, import
  projection, generated parity;
- Review failure/scope: review presentation and apply/rebuild owners;
- Images scope/triage: images workspace parity and asset resolution owners;
- graph workflows/Advanced continuity/draft-effective details: connected editing,
  form graph, and dependency-focused owners;
- Groups/search/navigation/responsive behavior: connected editing/form graph plus
  dependency-free frontend helper tests and browser proof.

Any new test file must be added to the validation catalog with measured
isolation/serialization metadata; suite and `serial_group` membership is a
deliberate declaration, not an automatic consequence of being a Manager test.
Keep the catalog edit purely additive — a new gate object plus the suite
memberships it joins. `scripts/catalog_change_scope.py` classifies the diff:
removing or retargeting a gate, or editing `schema`, `ci`, `serial_groups`, or
an existing gate's `command`, `layer`, `test_files`, `changed_surfaces`, or
`serial_group`, selects the complete validation inventory on that pull request,
while a pure addition selects only the CI contract owners and the new gate. Any
catalog edit runs `tests/test_catalog_change_scope.py` and
`tests/test_validation_catalog.py`.

Tests must derive family coverage from the registry and include forced mutations
so completeness cannot pass over a shrunken universe.

### 11.2 Required layers per checkpoint

Every checkpoint:

1. RED proof against the unmodified implementation;
2. exact focused tests while editing;
3. current catalog-selected Manager serial group in one process locally; CI no
   longer runs it that way — the planner splits the owner into five disjoint
   partitions across parallel jobs, so per-partition wall clock is not
   comparable to the local run, and CI omits the separately cataloged
   `test_asset_map_sync.py` unless `asset_map` actually changed;
4. the catalog's `ci.always_gate_ids` set, which every pull request runs
   regardless of changed surface: `py.test_validation_catalog`,
   `py.test_run_layered_validation`, `py.test_codex_finding_disposition`,
   `py.test_source_parity_canaries`, `py.test_workbook_truth`, and
   `cmd.release_candidate_lane`. A UI-only checkpoint still owns their result;
5. frontend production build for frontend changes;
6. API schema, pagination, stable ordering, query-budget, no-write, and error-state
   tests for changed read models;
7. real browser at desktop and 390x844 for visible workflows, including console,
   focus, overflow, reload, and Back/Forward evidence;
8. `git diff --check`, changed-file/status review, protected-boundary diff/hash
   evidence, and `scripts/validate_state_handoff.py` after any `STATE.md` edit
   **or any catalog edit** — the validator now checks every count that a
   `STATE.md` sentence attributes to `tests/validation_catalog.json` against the
   catalog itself, so a catalog change can invalidate handoff prose that this
   checkpoint did not touch. Never write an inventory count into `STATE.md`
   without re-deriving it from the catalog at write time;
9. PR Release candidate and review-disposition gates before merge.

Checkpoints changing workbook-domain registry, projection, ChangeSet parsing,
writer capability, affected-model derivation, generation, or publication also
run current package/schema, generated-parity, copied-workbook Apply/Rebuild, and
composed all-model candidate gates as selected by repository authority. These
runs use isolated workbook/output roots unless an exact canonical write is
separately requested and approved.

### 11.3 Gate-write and stale-artifact handling

- A test that generates or writes must declare and use its catalog-owned isolated
  output/workbook path.
- Manager serial-group members run together as cataloged; protected-root hashers
  do not run concurrently with a process writing those roots.
- Before and after each gate, inspect tracked workbook/generated/runtime paths.
  Unexpected churn is a failure, not cleanup permission.
- Fresh-generation parity compares exact candidate output against independent
  workbook authority and enumerates candidate families on both sides.
- A read-only UI checkpoint records protected hashes or an equivalent clean diff.
- A registry/write-capability checkpoint proves source row → projection → schema
  → operation → ChangeSet → guarded copied-workbook write → fresh generation →
  re-import. Green import/package checks alone do not prove runtime parity.
- Catalog-derived counts are the only citable inventory numbers. A checkpoint
  that re-measures a gate updates the catalog rather than prose, and quotes a
  measured pass count only as dated evidence of one run.
- No live dealer submission, production deployment/cache purge, or WordPress
  media mutation is a validation step.

## 12. Checkpoint execution and handoff protocol

Before each checkpoint:

1. verify branch, current `origin/main`, status, and unrelated work;
2. read the live specification sections, target files, symbol definitions/usages,
   neighboring tests, READMEs, validation catalog entries, and current handoff;
3. write a definition of done naming diagnosis, operator outcome, authorities,
   affected/protected surfaces, RED test, gates, rollback, and stop conditions;
4. confirm the checkpoint is explicitly authorized and no earlier exit gate is
   open.

During implementation:

- use test-first RED/GREEN changes;
- keep one independently useful slice per PR where practical;
- update this spec only for requirement status, evidence, decisions, blockers, or
  checkpoint changes;
- do not start later-priority polish to make an earlier pass look complete.

At checkpoint closeout:

- mark only evidence-backed ledger items complete;
- record exact tests/build/browser proof and relevant gates not run;
- when the checkpoint added or retargeted a catalog gate, record the scope
  `scripts/catalog_change_scope.py` assigned and whether the full inventory
  therefore ran;
- record companion files as updated, inspected-no-change, or not applicable;
- update `fable5loop/STATE.md` with the exact next authorized action;
- inspect final status/diff and preserve unrelated work;
- deliver through a task branch and PR; do not merge without separate authority.

## 13. Approval gates and mandatory stops

Explicit approval is required before:

- starting any implementation checkpoint from this spec;
- adding writable registry families for the four preserved sheets in Checkpoint
  2D;
- introducing a durable DB migration, new terminal lifecycle state, public API
  break, dependency, workbook schema/column, generated contract field, or
  deployment assumption;
- editing `schema`, `ci`, or `serial_groups` in `tests/validation_catalog.json`,
  or retargeting or removing an existing gate, because those reroute selection
  for gates the checkpoint does not own;
- choosing product data or conflict resolution when workbook authority does not
  establish the answer;
- changing canonical workbook data or applying against the canonical workbook;
- changing dealer, security, WordPress media, deployment, or customer runtime.

Stop immediately when:

- a workbook lock is present;
- exact workbook/projection/draft identity cannot be reconciled;
- immutable artifacts would need mutation to implement correction;
- rollback cannot be hash-proven;
- a family’s ownership/key/reference semantics are unresolved;
- a test owner is missing or a parity universe can shrink silently;
- current implementation contradicts a pinned requirement in a way that requires
  product or architecture choice;
- work would need a later checkpoint to satisfy the current exit gate.

## 14. Completion record

Each authorized checkpoint appends one concise dated record containing:

- ledger items closed;
- files/families/APIs changed;
- RED and acceptance evidence;
- browser and protected-boundary proof;
- relevant checks not run and why;
- residual risk or “none implied”;
- branch, commit, PR, CI, and review disposition;
- exact next authorized action.

- **2026-08-29 — Checkpoint 1B / P1.2 / WM-002:** closed by implementation
  `f0e023d`; registry-derived structure index, shared schema editor, contextual
  pre-Save evidence, capability/dependency refusal, synthetic completeness,
  isolated durable-save proof, desktop/mobile Chrome proof, protected hashes,
  focused owners, frontend build, and the catalog-selected Manager serial gate
  are recorded above with that run's dated counts. No workbook, generated,
  customer-runtime, dealer, dependency, schema, or deployment boundary changed. Residual risk: none
  implied. Delivery branch `feat/workbook-manager-structure-management`;
  implementation `f0e023d`, review remediation `3c37031`, closeout `48dffda`,
  and PR #62 (`https://github.com/seanzmc/27vette/pull/62`) are delivered. Both
  P2 review threads are resolved with code and test evidence; current-head CI is
  pending. Checkpoint 1C requires new explicit authorization.
