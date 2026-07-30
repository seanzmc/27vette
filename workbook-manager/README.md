# Workbook Manager (React + FastAPI + SQLite)

Provisional interface for investigating the disposable SQLite projection of
`stingray_master.xlsx` and collecting legacy staged edits. The workbook remains
canonical. Live manager-to-workbook writes are disabled until the reviewed
ChangeSet route is enabled in Pass 7 of the reliability specification.

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
catalog contract, and Pass 3 request connections plus promotion coordination,
are implemented:

- `POST /api/sync` refuses every `write=true` request. The browser has no live
  write control; dry-run remains available for inspection only.
- `POST /api/import` permits only the first import into a new empty projection.
  It refuses replacement of an active projection until atomic candidate
  promotion is implemented in Pass 4.
- Import is also refused while legacy staged, committed-unsynchronized, or
  failed work exists. An import with blocking findings is labeled `unverified`,
  never verified/current.
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

1. **Initial import** — `POST /api/import` (the UI triggers this only when no
   projection exists).
   Every duplicate identifier, missing sheet/column, and unresolved
   relationship is reported with sheet/row/entity detail. Blocking findings
   make the projection `unverified`. Re-import is contained until Pass 4.
2. **Edit** — Form Structure workspace (models, runtime steps, section
   presentation/order, context sections, variants) and Model Operations
   workspace (options, OVS, exclusive groups + members, rule mapping, rule
   groups + members, pricing, variant overrides, assets, interior scope,
   components; shared interiors/color overrides). Collections come from the
   workbook's own `model_workbook_sources` registry, not a hardcoded list.
3. **Stage** — every add/update/delete is validated (keys, types, enums,
   scoped uniqueness, references) and queued in `pending_changes`. Undo
   discards a staged change without touching data or audit history.
   Deletes are blocked while dependents exist unless explicitly confirmed.
4. **Commit (legacy provisional)** — batch revalidation; every
   change lands in the append-only `change_history` table (timestamp,
   actor, entity, model, op, old/new values, source sheet/row, validation
   result, sync status).
5. **Sync preview only** — `POST /api/sync` with `write=false` can run the
   existing dry-run gate. `write=true` is refused by the API regardless of
   confirmation text or mtime.
6. **Disposable export** — `POST /api/export` can create a comparison workbook
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

```sh
.venv/bin/python -m pytest \
  tests/test_workbook_manager_catalog.py \
  tests/test_workbook_manager_import_projection.py \
  tests/test_workbook_manager_api_concurrency.py \
  tests/test_workbook_manager.py -q
# optional direct shared-writer scratch-copy tests (not an enabled API route):
WBM_SLOW_GATE=1 .venv/bin/python -m pytest tests/test_workbook_manager.py -q
```

API tests skip automatically until the backend requirements are installed.
The normal suite skips two explicit scratch-copy shared-writer tests unless
`WBM_SLOW_GATE=1` is set. Candidate projection promotion and exact preserved-
sheet reconstruction remain Pass 4 work.
