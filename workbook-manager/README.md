# Workbook Manager (React + FastAPI + SQLite)

Provisional interface for investigating the disposable SQLite projection of
`stingray_master.xlsx`. Pass 5 adds manager-owned durable update/add/delete
drafts, immutable ChangeSet emission, and durable shared-service preview and
approval lifecycles. Pass 6A independently hardens the shared writer's
post-save restoration; no manager apply route is enabled, and the browser still
exposes only the contained legacy staged-edit flow.
The workbook remains canonical. Live manager-to-workbook writes are disabled
until the reviewed ChangeSet route is enabled in Pass 7 of the reliability
specification.

```text
React interface (frontend/, Vite build served by FastAPI)
    ↓
FastAPI API + validation layer (backend/app/)
    ↓
Disposable verified projection (var/workbook_projection.sqlite3)
    +
Durable workflow/recovery state (var/workbook_manager.sqlite3)
    ↕
openpyxl import/export adapter (backend/app/importer.py, sync.py)
    ↓
stingray_master.xlsx (canonical source)
```

## Current safety status: read-only / provisional

Pass 1 containment remains active. Pass 2 split storage plus the shared backend
catalog contract, Pass 3 request connections plus promotion coordination, and
Pass 4 verified candidate promotion are implemented. Pass 5 is implemented
through its complete final-graph exit gate: durable update/add/delete intent,
exact ChangeSet emission, and shared-service preview and approval lifecycles:

- `POST /api/sync` refuses every `write=true` request. The browser has no live
  write control; dry-run remains available for inspection only.
- `POST /api/import` builds a same-filesystem candidate, validates package and
  schema integrity, proves semantic readback, rechecks source SHA-256 plus mtime,
  and atomically replaces the active projection only after every production gate
  passes. Primary-runtime generated-contract parity remains a separate slow
  acceptance test and is not part of manager import/export execution.
  A failed candidate is deleted and leaves the prior projection byte-identical.
- Import is also refused while legacy staged, committed-unsynchronized, or
  failed work exists, or while a nonterminal durable draft exists. An import
  with blocking findings is labeled `unverified`, never verified/current.
- `POST /api/drafts/{draft_id}/operations` accepts update/add/delete intent only
  when the projection is `current`. It resolves workbook lineage and ownership,
  coalesces sequential edits to one physical row, and records typed
  original-to-final field pairs in durable state. Parent/member additions and
  dependent deletes remain together for complete final-graph preview; no
  individual dependency confirmation can bypass that graph. The route never
  mutates the projection or legacy history. `GET
  /api/drafts/{draft_id}/operations` returns that intent. These are backend
  checkpoint routes, not an enabled browser write workflow.
- `POST /api/drafts/{draft_id}/commit` converts the complete coalesced draft once
  through the shared `workbook-changeset-1` contract, stores the exact
  typed payload in durable state, and transitions the draft to
  `changeset_emitted`. The stored row has database-enforced update/delete
  refusal. This route does not preview, approve, apply, or write the workbook.
- `POST /api/drafts/{draft_id}/preview` accepts only `changeset_emitted` or
  `preview_retryable` drafts against a `current` projection. It passes the exact
  stored ChangeSet to `workbook_domain.service.preview_changeset()`, persists the
  returned dictionary or exception envelope in immutable durable attempt
  history, and maps the result to the specification's preview lifecycle. It
  does not reproduce validation, approve, apply, mutate the projection, or write
  the workbook.
- `POST /api/drafts/{draft_id}/approve` accepts only an exact identity-bound
  formal preview from `preview_ready` or `approval_confirmation_required`, calls
  only `workbook_domain.service.approve_changeset()`, and stores the returned
  dictionary or exception in immutable durable attempt history. It exposes only
  lifecycle-authorized verbs and never applies, mutates the projection, or
  writes the workbook.
- The shared writer now rechecks exact rows, package integrity, and schema
  integrity after a safe save. Any returned or thrown post-save validation/log
  failure restores and SHA-256-verifies the backup or reports the workbook
  state unknown. The backend-only durable apply lifecycle can call it with the
  exact stored ChangeSet/preview/approval artifacts; no API or browser action
  can reach that lifecycle until Pass 7.
- Status reports projection, draft, workbook, generated-artifact, and
  publication states separately. Generated artifacts and publication are
  always `unverified` in this provisional manager workflow.
- Comparison export is available only from a `current` verified projection.
  Outputs are explicitly named `DISPOSABLE-comparison-*.xlsx` under
  `workbook-manager/var/exports/`; they are never write or publication inputs.
- First start migrates a legacy combined `WBM_DB` into the two stores before a
  consumer can open either one. Exact legacy staged/history rows are retained
  as read-only recovery evidence; unresolved records keep import containment
  active. The hashed legacy archive is retained beside `WBM_DB`.
- Storage bootstrap/migration runs in the FastAPI lifespan, so it completes
  before the app serves any request. No request path bootstraps lazily.
- Every request opens its own projection and durable-state connection and
  closes it when the request ends. Both carry WAL and a bounded busy timeout
  (`WBM_BUSY_TIMEOUT_MS`, default 5000 ms). SQLite foreign keys are enforced
  only on durable manager-state connections, where the relationships are
  database-owned; the projection keeps them off so unresolved workbook
  references still import and are *reported* as findings.
- One process-local lock covers bootstrap/migration, durable-state mutations,
  candidate promotion, and workbook apply. Requests take it from an `async`
  dependency that polls a non-blocking acquire with a bounded deadline
  (`WBM_STATE_LOCK_WAIT_SECONDS`, default 30 s → `503`); blocking on it from a
  threadpool worker would park an anyio thread token and can wedge the process
  once every token is parked.
- A projection reader gate blocks new readers and waits for open request-scoped
  projection connections to close before the projection file is replaced — the
  bootstrap swap already goes through it. Requests that arrive while a promotion
  holds the gate fail closed with `503` (`WBM_READER_WAIT_SECONDS`, default
  10 s); a promotion whose readers do not drain (`WBM_READER_DRAIN_SECONDS`,
  default 10 s) refuses to replace anything and re-admits readers. Lock ordering
  is lock-then-reader.
- The app must be served through its lifespan. Requests to an app whose lifespan
  never ran fail closed with `503 storage_not_bootstrapped` instead of an opaque
  missing-table error, so `TestClient` must be entered as a context manager.

The existing stage/validate/commit tables remain legacy provisional workflow
state, not workbook write authority. SQLite-canonical operation is not an
approved direction.

## Setup

```sh
# backend deps (repo venv)
.venv/bin/python -m pip install -r workbook-manager/backend/requirements.txt

# frontend build (one-time per change; FastAPI serves dist/)
cd workbook-manager/frontend && npm install && npm run build
```

## Run

```sh
./workbook-manager/run.sh            # serves API + built UI on :8050
# dev mode with hot reload (optional):
cd workbook-manager/frontend && npm run dev   # :5183, proxies /api → :8050
```

Supported serving is **single-process only**. `run.sh` refuses both `--workers`
and `WEB_CONCURRENCY` (uvicorn reads the worker count from either), because
manager locks and the projection reader gate are process-local; multi-worker
serving is unsupported and no distributed locking exists.

Environment overrides: `WBM_WORKBOOK`, `WBM_DB` (durable state),
`WBM_PROJECTION_DB` (disposable projection), `WBM_VAR_DIR`, `WBM_PORT`,
`WBM_BUSY_TIMEOUT_MS`, `WBM_READER_WAIT_SECONDS`, `WBM_READER_DRAIN_SECONDS`,
`WBM_STATE_LOCK_WAIT_SECONDS`.

## Workflow

1. **Import/re-import** — `POST /api/import` (the UI enables this for a missing
   projection or a current verified projection with no unresolved durable work).
   Every duplicate identifier, missing sheet/column, and unresolved
   relationship is reported with sheet/row/entity detail. Blocking findings
   block candidate promotion and leave the current projection untouched.
2. **Edit (legacy browser)** — Form Structure workspace (models, runtime steps, section
   presentation/order, context sections, variants) and Model Operations
   workspace (options, OVS, exclusive groups + members, rule mapping, rule
   groups + members, pricing, variant overrides, assets, interior scope,
   components; shared interiors/color overrides). Collections come from the
   workbook's own `model_workbook_sources` registry, not a hardcoded list.
3. **Stage (legacy provisional)** — every add/update/delete is validated (keys, types, enums,
   scoped uniqueness, references) and queued in `pending_changes`. Undo
   discards a staged change without touching data or audit history.
   Deletes are blocked while dependents exist; the legacy confirmation bypass
   is removed.
4. **Durable draft operations (backend only)** — update/add/delete requests
   against a current projection resolve one physical workbook target and persist
   one coalesced original-to-final operation in `WBM_DB`. Coordinated
   parent/member additions and dependent deletes remain in one draft. Re-import
   remains blocked until the nonterminal draft has a later lifecycle disposition.
5. **Emit ChangeSet (backend only)** — `POST /api/drafts/{draft_id}/commit`
   commits a nonempty mutable draft into one exact immutable
   `workbook-changeset-1` payload. It does not run the final-graph preview and
   grants no workbook write authority.
6. **Preview ChangeSet (backend only)** — `POST /api/drafts/{draft_id}/preview`
   runs the exact stored ChangeSet through the shared preview service, records
   immutable result/exception evidence, and exposes only lifecycle-authorized
   next verbs. Blocking final-graph references map to `preview_rejected` with
   cancel as the only verb; a retry reuses the ChangeSet and creates a new attempt.
7. **Approve ChangeSet (backend only)** — `POST /api/drafts/{draft_id}/approve`
   sends the exact stored ChangeSet and identity-bound formal preview through
   the shared approval service and records immutable result/exception evidence.
   Confirmation resubmission reuses the same artifacts; re-preview binds a later
   approval to the new preview.
8. **Apply ChangeSet (backend service only, not route-reachable)** — Pass 6B
   routes the exact stored ChangeSet, preview, and approval only through
   `workbook_domain.service.apply_changeset()`. One active durable attempt is
   recorded before the writer runs; exact replay is idempotent, interrupted
   attempts become unknown on startup, and cancellation/manual resolution keep
   immutable history. There is intentionally no FastAPI or browser apply action;
   Pass 7 owns that final enablement.
9. **Commit (legacy provisional)** — batch revalidation; every
   change lands in the append-only `change_history` table (timestamp,
   actor, entity, model, op, old/new values, source sheet/row, validation
   result, sync status).
10. **Sync preview only** — `POST /api/sync` with `write=false` can run the
   existing dry-run gate. `write=true` is refused by the API regardless of
   confirmation text or mtime.
11. **Disposable export** — `POST /api/export` can create a comparison workbook
   under `var/exports/` only when projection state is `current`. The file is
   labeled disposable and must not replace the workbook or feed generation.

## Identity and normalization rules

- `option_id` is **model-scoped** (verified: 144–186 ids overlap across
  models) — SQLite enforces `UNIQUE(model_id, option_id)`; rule/group/price
  ids are stored model-scoped as well; `interior_id` is global.
- Canonical IDs are never rewritten. Display names/ids (`Title Case`,
  confirmed-prefix stripping like `opt_z51_001 → Z51 001`) are derived at
  display time only (`naming.py` / `naming.js`) and are reversible.
- Workbook coordinates and ownership (`src_sheet`, `src_row`, family, physical
  key, model context) are traceability metadata. Shared physical source rows are
  projected once per physical sheet/key even when several models register them.
- `section_master` and the raw-preserved sheets (`PriceRef`,
  `context_choice_copy`, `rule_phrase_map`, `runtime_rule_exceptions`) are
  read-only because no gated write family exists for them. Edit ownership is
  derived from the workbook model/source lifecycle matrix, not runtime
  publication state.

## Tests

Use the exact affected test or class while editing. The command below is the
Pass/checkpoint acceptance inventory, not the inner edit loop. At the 2026-08-10
validation-efficiency checkpoint it completed in 791.25 seconds. Complete
real-workbook promotion, unchanged comparison export, API import/export, and
generated-parity owners take about 68–75 seconds each; the changed-overlay
comparison-export owner takes about 213 seconds because it exercises the full
overlay write and reconstruction-validation path.

```sh
.venv/bin/python -m pytest \
  tests/test_workbook_manager_catalog.py \
  tests/test_workbook_manager_import_projection.py \
  tests/test_workbook_manager_generated_parity.py \
  tests/test_workbook_manager_api_concurrency.py \
  tests/test_workbook_manager_drafts.py \
  tests/test_workbook_manager_changeset_lifecycle.py \
  tests/test_workbook_manager.py -q
# optional direct shared-writer scratch-copy tests (not an enabled API route):
WBM_SLOW_GATE=1 .venv/bin/python -m pytest tests/test_workbook_manager.py -q
```

API tests skip automatically until the backend requirements are installed.
The normal suite skips two explicit scratch-copy shared-writer tests unless
`WBM_SLOW_GATE=1` is set. Pass 4 comparison reconstruction is an exact identity
copy while no draft overlay exists; package/schema validation and independent
semantic readback must pass before the disposable file is returned.

Focused manager behavior classes clone one immutable real-workbook import and
assert that the base projection and canonical workbook hashes remain unchanged.
The unchanged comparison-export assertions and successful projection-promotion
assertions each consume one complete successful result. Keep the distinct real-
workbook promotion success, atomic-replace and source-drift failures, unchanged
and changed-overlay comparison exports, API import/export, scratch-write, and
generated-parity acceptance owners intact and run them once at each pass
checkpoint.
