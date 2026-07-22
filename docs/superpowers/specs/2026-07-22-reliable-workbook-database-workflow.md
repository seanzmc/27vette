# Reliable Workbook–Database Workflow Implementation Specification

Status: implementation specification; not started.
Recommended implementation reasoning: high.

## 1. Goal and authority boundary

Make the Workbook Manager a reliable editing interface around
`stingray_master.xlsx` without turning SQLite into a second source of Corvette
product behavior.

The workbook remains canonical. The manager consists of:

- a disposable, verified SQLite projection used for browsing and lookup;
- durable drafts and exact `workbook-changeset-1` lifecycle artifacts used to
  propose changes;
- the existing shared ChangeSet service as the only manager-to-workbook write
  route.

This work changes workflow reliability only. It does not change workbook
product data, generated form contracts, customer-facing form behavior,
publication decisions, deployment, or dealer submission.

Standing source-of-truth, workbook-safety, approval, validation, and handoff
requirements in `AGENTS.md` apply. This specification owns only the
Workbook Manager implementation direction.

## 2. Current evidence and baseline

The audit in `docs/db_audit-7-22.md` proved these defects against disposable
workbooks and databases:

1. Import clears and commits the active projection before the new source is
   validated.
2. Import findings do not prevent promotion; duplicate rows use first-wins.
3. Re-import ignores committed-unsynchronized work and can make stale full-row
   snapshots overwrite unrelated external workbook edits.
4. Staging validates individual rows against committed SQLite state instead of
   validating the proposed final workbook graph.
5. Sequential edits to one row become contradictory operations.
6. Failed sync work leaves the only pending queue and has no supported retry,
   requeue, or cancel path.
7. `workbook-manager/backend/app/specs.py` duplicates and disagrees with
   `scripts/corvette_form_generator/workbook_domain/registry.py`.
8. Unknown model ownership can commit and later be skipped because no target
   sheet resolves.
9. Manager sync binds mtime but not workbook SHA-256 or the reviewed operation
   set.
10. `editor_ops.apply_batch()` does not restore the backup when post-save
    readback raises an exception.
11. The FastAPI app shares a lazily initialized connection across request
    threads.
12. The API/browser lose model context for some model-key families and do not
    faithfully expose all reference metadata.

Current focused baseline, rerun on 2026-07-22:

```text
.venv/bin/python -m pytest tests/test_workbook_manager.py -q
1 failed, 27 passed, 2 skipped
```

The existing failure is
`TestStagingWorkflow.test_scaffold_model_rejected`. It belongs to the model
lifecycle/contract pass below; do not change workbook lifecycle data to restore
the stale expectation.

The 2026-07-16 relational design and plan are historical evidence only. Do not
implement their fixed three-model topology, prescribed module tree, or
SQLite-canonical direction.

## 3. Pinned architecture decisions

These decisions are not left to the implementing agent.

### 3.1 Separate disposable projection from durable workflow state

Use two physical stores:

- `workbook-manager/var/workbook_projection.sqlite3`: current verified
  workbook projection. Candidate import replaces only this file.
- `workbook-manager/var/workbook_manager.sqlite3`: durable manager state for
  drafts, immutable ChangeSet payloads, preview/approval/receipt artifacts,
  status transitions, failure detail, and legacy recovery records.

Support the same split under test/environment overrides. Add a dedicated
projection-path override rather than changing the meaning of `WBM_DB`.

The projection file must not contain the durable journal. Candidate promotion
must therefore be unable to erase drafts, approvals, receipts, retry history,
or unresolved legacy work.

The projection represents the last verified workbook import. Draft or committed
changes are overlays; they do not mutate projection rows before a proven
workbook write. After a successful workbook write, mark the projection stale
until a verified re-import succeeds.

### 3.2 Adopt the existing ChangeSet contract; do not invent another

The manager must emit the exact immutable contract owned by:

- `workbook_domain.changeset` (`workbook-changeset-1`);
- `workbook_domain.service` (preview, approval, apply, receipt).

One user commit of the current draft emits one immutable ChangeSet. Before
emission, all edits to the same `(sheet, family, physical key)` coalesce into a
single original-to-final row change. The emitted payload may contain that
physical key only once.

Field pairs, workbook SHA-256/mtime, source sheet, family, key, provenance,
semantic fingerprint, preview fingerprint, approval fingerprint, warning
acknowledgements, and receipt must retain the meanings already defined by the
shared service. Do not create manager-specific variants of those fields.

### 3.3 Choose fail-closed staleness instead of automatic rebase

This implementation does not add field-level automatic rebase.

- Re-import is blocked while any non-cancelled draft or any non-terminal,
  non-cancelled ChangeSet exists. `applied`, `cancelled`, and a recorded manual
  resolution are terminal for this guard.
- Preview/apply rejects any workbook SHA-256 or mtime drift.
- A stale ChangeSet remains visible but cannot be edited or written. The user
  may cancel it, re-import the workbook, and create a new draft.
- No stale full-row snapshot may be synchronized.

This preserves unrelated external workbook edits without adding a conflict
merge engine. Automatic field-level rebase is a separate future feature.

### 3.4 Reuse final-state validation

Draft collection may perform immediate shape/type/reference hints, but those
hints do not grant commit or write authority.

Authoritative validation is one projected-final-state run of the complete
coalesced ChangeSet through `preview_changeset()` and
`editor_ops.apply_batch(write=False)`. This is the existing shared operation
projection and validation boundary.

Parent/member additions, coordinated deletes, uniqueness, conditional and
union references, and model ownership must therefore be judged against the
complete proposed final graph. Remove `confirm_dependencies` as an integrity
bypass. Warning acknowledgement may confirm only warnings classified as
confirmable by the shared service.

### 3.5 Keep the existing SQL shape unless correctness requires less

This pass is not a relational redesign. Retain the current shared conceptual
tables unless a table must change to derive its schema from the shared registry
or to enforce verified import ownership/references. Do not create per-model
physical table families, a compiler framework, ORM layer, plugin system, or new
database dependency.

## 4. State and transition contract

Persist exact immutable artifacts and a small manager state machine. Status is
batch-level because the workbook write is atomic.

Legal lifecycle:

```text
draft
  -> cancelled
  -> changeset_emitted

changeset_emitted
  -> preview_failed
  -> preview_ready
  -> stale
  -> cancelled

preview_failed | stale
  -> cancelled

preview_ready
  -> approved
  -> stale
  -> cancelled

approved
  -> applying
  -> stale
  -> cancelled

applying
  -> applied
  -> apply_failed
  -> restored
  -> workbook_state_unknown

apply_failed | restored
  -> retry_pending
  -> cancelled

retry_pending
  -> applying
  -> stale
  -> cancelled

workbook_state_unknown
  -> restored
  -> applied
  -> abandoned_unknown
```

Rules:

- `draft` is mutable; emitted ChangeSets and lifecycle artifacts are immutable.
- Retry reuses the exact ChangeSet, preview, and approval identities. It is
  allowed only if the workbook still matches the bound SHA-256/mtime and the
  prior receipt proves `untouched` or `restored`.
- `workbook_state_unknown` blocks retry, import, and new write approval until a
  manual recovery step records the live workbook hash and resolves the outcome:
  `restored` only when the base hash is proven, `applied` only when exact final
  rows are proven, or `abandoned_unknown` when the operator preserves the
  unresolved evidence and requires a verified re-import before any new draft or
  write.
- Cancellation never deletes history. It makes the draft/ChangeSet ineligible
  for preview or write.
- A successful retry is idempotent: one workbook mutation and one terminal
  applied receipt. Repeating the request returns the existing terminal result.
- Legacy `pending_changes`/`change_history` rows are never silently converted
  into trusted ChangeSets. On migration, preserve them in a read-only recovery
  record with their original JSON and status. If any are staged or unsynced,
  keep import/write containment active until they are explicitly cancelled or
  recreated as a reviewed draft.

## 5. Model and schema authority

### 5.1 Workbook family contract

`scripts/corvette_form_generator/workbook_domain/registry.py` is the only
writable family/key/type/enum/reference authority.

Add one manager adapter at
`workbook-manager/backend/app/catalog.py`. It may add database-only facts such
as SQL table name, source-role routing, fixed-sheet routing, display label, and
lineage columns. It must import key/type/enum/reference/conditional-reference
semantics from the shared registry rather than restating them.

Migrate importer, DDL, validation hints, API schema responses, UI controls,
ChangeSet emission, and comparison export to this adapter. Delete
`backend/app/specs.py` only after no production or test import remains.

Add a mechanical parity test that enumerates every writable registry family and
proves that the manager adapter exposes the same key, types, enums, ordinary
references, union references, and conditional references.

### 5.2 Model lifecycle sets

Derive and name four different sets:

- **known**: every nonblank unique `model_master.model_key`;
- **editable/importable**: a family-dependent predicate over active workbook
  model metadata and the family's routing mode;
- **generatable**: the exact result of
  `model_configs.discover_generation_model_configs()`;
- **published**: active `model_registry_promotion` rows with
  `promoted_to_runtime=True`.

Do not duplicate the generation predicate. Reuse
`discover_generation_model_configs()` for the generatable set and the current
registry-promotion reader for publication state.

Unknown models are always rejected. A model need not be published to be a valid
editable/importable workbook model. For families routed through
`SOURCE_ROLE_FAMILIES`, an edit requires an active exact
`(model_key, source_role)` registration and resolvable source sheet. For
fixed-sheet families routed through `GLOBAL_SHEET_FAMILIES`, use the fixed sheet
plus that family's key/model semantics and the appropriate known/active-model
predicate; do not require or invent a `model_workbook_sources` row.

Replace the stale scaffold test with lifecycle assertions derived from a
disposable workbook fixture: unknown rejected, inactive source role rejected,
active source-backed unpublished model accepted, fixed-sheet model-key family
accepted without an invented source-role row, and publication state does not
grant edit ownership.

## 6. Implementation passes

Implement in order. Keep containment active until Pass 6 explicitly re-enables
the reviewed ChangeSet write path. Each pass is a reviewable vertical slice;
do not reorganize the repository first.

### Pass 1 — Contain unsafe paths

Required changes:

1. Refuse `POST /api/sync` when `write=true` with an explicit provisional/read-
   only response. Remove or disable the browser write control; do not hide a
   still-callable write route behind CSS.
2. Refuse re-import when an active projection exists until candidate promotion
   is implemented. A first import into a new empty projection is allowed, but
   must not be reported as verified when blocking findings exist.
3. Independently refuse import when staged, committed-unsynchronized, stale,
   failed, restored, or unknown legacy/workflow state exists.
4. Keep browsing and comparison export available. Clearly label exported files
   disposable and keep them outside tracked workbook/generated paths.
5. Show a persistent `Read-only / provisional` banner and report projection,
   draft, workbook, generated-artifact, and publication states separately.
6. Update `workbook-manager/README.md` and the root README pointer so neither
   describes live manager sync as currently safe.

Pass 1 exit gate: no API or browser path can mutate `stingray_master.xlsx` or
destructively replace an existing projection database.

### Pass 2 — Adopt the shared contract and lifecycle predicates

Required changes:

1. Add the registry-derived `catalog.py` adapter and parity tests.
2. Move current `specs.py` consumers to the adapter without changing product
   behavior or SQL naming merely for cleanup.
3. Carry model context for both physically model-scoped tables and families
   whose key includes `model_key`.
4. Enforce family-specific source ownership before a draft can be created.
5. Expose ordinary, union, and conditional references in the API schema.
6. Render finite controls where the registry defines finite values. Keep free
   text only where the shared contract is actually free text.
7. Correct the stale lifecycle test using derived workbook predicates.
8. Delete `specs.py` only after the mechanical no-consumer and parity gates pass.

Pass 2 exit gate: every manager-writable family has one key/type/enum/reference
definition and unknown or unowned models cannot create drafts.

### Pass 3 — Build and atomically promote a verified projection

Required changes:

1. Open the source workbook read-only and record its SHA-256 and mtime before
   candidate work begins.
2. Build a new candidate projection file in the same filesystem as the active
   projection. Never clear or mutate the active file during compilation.
3. Enable SQLite foreign-key enforcement on candidate and request connections.
4. Record exact sheet, row, family, physical key, model ownership, and source
   disposition for every nonblank source row.
5. Reconcile each source row to exactly one disposition:
   `imported`, `preserved_raw`, or `excluded`. An exclusion must include sheet,
   row, field, value, reason token, and contract impact.
6. Treat missing required sheets/columns, blank or duplicate keys, unresolved or
   ambiguous references, unproved model ownership, incomplete row
   reconciliation, and generated-contract drift as blocking. Do not promote an
   `imported_with_issues` candidate.
7. Preserve unowned sheets/columns losslessly for comparison export; do not
   interpret them as writable families.
8. Run `PRAGMA foreign_key_check` and reconstruct a comparison workbook in a
   temporary output root.
9. Generate contracts for the current **published** set from both the source
   workbook and reconstructed comparison workbook in isolated output roots, then
   compare them with the repository comparator (timestamp-insensitive).
10. Recheck the source workbook SHA-256/mtime. Checkpoint and close the candidate
    so promotion does not depend on candidate `-wal` or `-shm` sidecars.
11. Under the projection-promotion lock, block new projection requests and drain
    existing projection connections. Atomically replace the projection file,
    fsync the file and parent directory as supported, remove only proven-stale
    projection sidecars, then reopen subsequent requests against the new
    projection generation. Durable-state connections remain independent.
12. On any exception or blocking finding, delete/quarantine the candidate and
    leave the prior projection bytes unchanged.

Do not make exact row counts part of the contract. Tests should derive counts
from their fixture/source workbook.

Pass 3 exit gate: malformed or incomplete imports leave the prior projection
byte-for-byte unchanged; only a reconciled, relationally valid, contract-parity
candidate becomes current.

### Pass 4 — Replace staged full rows with draft-to-ChangeSet emission

Required changes:

1. Store draft intent in the durable state database, not the projection.
2. Build draft rows from the projection plus earlier edits to the same physical
   key. Record only changed field pairs for updates.
3. Coalesce sequential edits and eliminate no-op reversions before ChangeSet
   emission.
4. Resolve source sheet and model ownership before accepting a draft operation;
   no operation may be committed with an empty target sheet.
5. Emit one exact immutable `workbook-changeset-1` payload per commit.
6. Preview the complete ChangeSet through `workbook_domain.service`. Persist the
   exact preview artifact and status; do not reproduce its validation logic.
7. Remove the dependency-confirmation bypass. Coordinated deletes and
   parent/member additions pass or fail as one final graph.
8. Keep legacy full-row history visible as read-only recovery evidence, not
   write authority.

Pass 4 exit gate: sequential same-row edits emit one operation; valid
parent/member additions and coordinated deletes preview together; invalid final
graphs cannot produce an approvable preview.

### Pass 5 — Harden the shared write boundary and recovery

Required changes:

1. Fix post-save exception restoration in
   `scripts/corvette_form_generator/editor_ops.py`, because the shared writer—not
   a manager wrapper—owns physical workbook recovery.
2. Enclose save, live readback, schema/package verification, and write-log
   completion in one restoration boundary.
3. After any post-save returned failure or exception, restore the backup and
   hash-verify it before returning `workbookState=restored`. Return
   `workbookState=unknown` when restoration cannot be proven.
4. Preserve the original failure and any restoration failure in the result.
5. Drive manager apply only through `workbook_domain.service.apply_changeset()`
   with the exact ChangeSet, preview, and approval artifacts.
6. Persist every attempt and receipt. Implement retry and cancel according to
   Section 4; do not mark individual operations applied after an atomic batch
   failure.
7. Read back exact affected rows before terminal `applied` status. Mark the
   projection stale after success.

Pass 5 exit gate: injected failures after physical save restore and hash-verify
the backup; failed/restored work remains visible and retryable; repeated retry
cannot duplicate a workbook mutation.

### Pass 6 — Repair connection lifecycle and make the UI a thin client

Required changes:

1. Initialize paths/schema through FastAPI lifespan. Use request-scoped SQLite
   connections; do not share `_conn` across threads.
2. Keep WAL and a bounded busy timeout. Serialize state mutations, candidate
   promotion, and workbook apply with one process-local mutation lock. The
   supported deployment remains the single-process `run.sh`; document that
   multi-worker serving is unsupported rather than adding distributed locking.
3. Resolve API resources only from the allowlisted catalog; never accept a raw
   SQL table name outside it.
4. Fix Form Structure section-to-step fallback using the workbook master
   section metadata already imported by the manager.
5. Carry model context through schema response, form payload, draft, ChangeSet,
   preview, history, and receipt for every model-owned family.
6. Show lineage, blocking findings, exact ChangeSet/preview identity, warnings,
   failure detail, retry/cancel controls, and separate workflow statuses.
7. Do not report generated artifacts or runtime publication current after a
   workbook write. This pass does not run or publish generators; report those
   states as stale/unverified until separately proven outside the manager.
8. Re-enable the browser/API workbook write action only after Passes 1–6 gates
   pass. The action must require the exact approved artifacts, not a typed
   `SYNC` string plus mtime.

Pass 6 exit gate: concurrent first-load requests do not lock or fail; a real
unchanged model-owned row round-trips through the API/browser payload without
losing model context or changing meaning; only the bound ChangeSet service can
reach a live write.

A manager `applied` receipt means only that the workbook write and exact
readback were proven. It is not repository or customer-runtime completion. The
enclosing operational workflow must then run the affected package/schema,
generation, generated-contract comparison, and registry-verification gates from
the README before reporting the overall workflow current. That post-write work
remains outside automatic manager execution and must not publish or deploy
without the normal repository authority.

## 7. Expected implementation surfaces

Expected existing owners:

- `workbook-manager/backend/app/config.py`
- `workbook-manager/backend/app/db.py`
- `workbook-manager/backend/app/importer.py`
- `workbook-manager/backend/app/validation.py`
- `workbook-manager/backend/app/staging.py`
- `workbook-manager/backend/app/sync.py`
- `workbook-manager/backend/app/main.py`
- `workbook-manager/backend/app/schemas.py`
- `workbook-manager/frontend/src/api.js`
- `workbook-manager/frontend/src/App.jsx`
- `workbook-manager/frontend/src/components/RecordForm.jsx`
- `workbook-manager/frontend/src/components/ChangesSync.jsx`
- `workbook-manager/frontend/src/components/FormStructure.jsx`
- `tests/test_workbook_manager.py`
- `scripts/corvette_form_generator/workbook_domain/registry.py`
- `scripts/corvette_form_generator/editor_ops.py`
- `workbook-manager/README.md`
- `README.md`
- this specification

Expected new owner:

- `workbook-manager/backend/app/catalog.py`

Small focused test modules or state/import helpers may be added when they make a
pass independently testable. Do not create the broad module tree from the
superseded plan, move all current tests preemptively, or refactor unrelated
generator/runtime code.

## 8. Acceptance matrix

Implementation is complete only when disposable tests prove:

| Audit risk | Required proof |
|---|---|
| Destructive import | malformed candidate preserves the prior projection SHA-256 |
| Import with issues | blocking findings prevent promotion and current-status claims |
| Journal loss on projection swap | drafts/artifacts remain unchanged across candidate promotion |
| Stale overwrite | any workbook hash/mtime drift blocks preview/apply; no external field is overwritten |
| Per-row validation | parent/member adds and coordinated deletes pass as one valid final graph |
| Sequential edits | one physical row appears once with original-to-final field pairs |
| Schema drift | manager catalog mechanically matches the shared registry |
| Unknown model | unknown/unowned model cannot create a draft or ChangeSet |
| Failed sync | failure remains visible with retry/cancel; retry is idempotent |
| Weak write binding | tampered ChangeSet, preview, approval, SHA, or mtime is rejected |
| Readback exception | backup is restored and hash-verified, or state is explicitly unknown |
| Connection race | concurrent first-load/status requests succeed without database lock errors |
| UI context loss | unchanged real model-key rows round-trip with the correct model and references |
| False readiness | workbook save leaves generated/publication status stale or unverified |

## 9. Validation and execution rules

For every pass:

1. Add a failing disposable regression before changing the implementation.
2. Run the focused test and observe the intended failure.
3. Make the smallest change through the owners above.
4. Run the focused test, then the current manager suite.
5. Recheck `git status` and prove the canonical workbook, tracked generated
   artifacts, runtime registry, deployment, and dealer code did not change.
6. Record the pass result in this specification before moving to the next pass.

Required final gates:

```sh
.venv/bin/python -m pytest tests/test_workbook_manager.py -q
WBM_SLOW_GATE=1 .venv/bin/python -m pytest tests/test_workbook_manager.py -q
cd workbook-manager/frontend && npm run build
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
git diff --check
```

Additional required focused tests include the shared ChangeSet service and
`editor_ops` fault-injection tests covering the changed write boundary. Run
generated-contract comparisons only in temporary workbooks/output roots; do not
refresh tracked `form-output/` or `form-app/data.js` as implementation output.

Browser-smoke the built manager against a copied workbook and temporary state/
projection databases. Cover model navigation, structure mapping, an unchanged
real-row edit, coordinated batch validation, stale workbook display, preview
binding, forced failure, retry/cancel, and post-write stale status. No live
dealer submission and no write to the canonical workbook are validation steps.

## 10. Scope control and stop conditions

The implementing agent may proceed through these passes without intermediate
approval when repository evidence supports the pinned design and all work stays
inside this specification.

Stop and request direction only if implementation would require:

- choosing or changing workbook product/business behavior;
- changing a shared public ChangeSet contract rather than using it as written;
- adding a dependency or supporting multi-process/distributed manager writes;
- changing generated/runtime contracts, publication, deployment, or dealer
  submission;
- discarding or guessing how to convert real legacy staged/unsynced work;
- accepting a candidate despite a blocking reconciliation or parity finding;
- materially expanding beyond reliability of the current manager workflow.

Do not stop merely because a pass spans several files or needs new focused
tests. Do not “solve” reliability by suppressing findings, weakening workbook
validation, editing workbook rows, or hiding unsafe actions only in the UI.

## 11. Non-goals

- Automatic field-level rebase or conflict merge.
- SQLite as canonical business-data storage.
- Per-model physical SQL table families.
- A new workbook compiler framework, ORM, API version, frontend framework, or
  dependency.
- Rewriting the fallback workbook editor or ingest workflow.
- Editing option availability, pricing, defaults, relationships, copy, ordering,
  lifecycle, or publication rows.
- Automatic generation, registry publication, deployment, or dealer submission
  inside the manager. The enclosing approved workbook workflow still performs
  the required post-write generation and verification before overall completion.

## 12. Companion impact and completion handoff

Companion disposition:

- Workbook source data: unchanged; hash/status proof required.
- Generated artifacts and `form-app/data.js`: inspected-no-change; temporary
  parity outputs only.
- Customer form and dealer submission: unchanged.
- Shared registry: reused; only generic metadata needed by existing writable
  families may be added.
- Shared ChangeSet contract/service: reused; no parallel contract.
- Shared writer: hardened only for post-save restoration correctness.
- Workbook Manager docs and root README pointer: updated to match actual safety
  state and commands.
- Superseded relational design/plan: retained as historical, not edited back
  into active instructions.

Follow `AGENTS.md` handoff requirements. Also report:

- projection candidate/promotion evidence;
- durable-state preservation evidence;
- exact ChangeSet/preview/approval/receipt identities from the disposable test;
- conflict/staleness and retry probes;
- post-save restoration hash proof;
- concurrent API result;
- browser-smoke result;
- proof that the canonical workbook and tracked generated/runtime surfaces were
  unchanged.