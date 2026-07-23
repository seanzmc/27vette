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
SQLite database (var/workbook_manager.sqlite3 — normalized, auditable)
    ↕
openpyxl import/export adapter (backend/app/importer.py, sync.py)
    ↓
stingray_master.xlsx (canonical source)
```

## Current safety status: read-only / provisional

Pass 1 containment is active:

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

Environment overrides: `WBM_WORKBOOK`, `WBM_DB`, `WBM_VAR_DIR`, `WBM_PORT`.

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
4. **Commit** — batch revalidation, then one SQLite transaction; every
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
- Workbook coordinates are traceability metadata (`src_sheet`, `src_row`),
  never record identity.
- `section_master` and the raw-preserved sheets (`PriceRef`,
  `context_choice_copy`, `rule_phrase_map`, `runtime_rule_exceptions`) are
  read-only in phase 1 because no gated write family exists for them;
  ZR1/ZR1X scaffolds are visible but locked while their
  `model_workbook_sources` rows are inactive.

## Tests

```sh
.venv/bin/python -m pytest tests/test_workbook_manager.py -q
# optional direct shared-writer scratch-copy tests (not an enabled API route):
WBM_SLOW_GATE=1 .venv/bin/python -m pytest tests/test_workbook_manager.py -q
```

API tests skip automatically until the backend requirements are installed.
The focused suite currently retains two assigned baseline failures: inactive
scaffold ownership is Pass 2 work, and exact `PriceRef` physical-row preservation
is Pass 4 work. See the active reliability specification for those assignments.
