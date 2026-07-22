# Workbook Manager (React + FastAPI + SQLite)

Interactive editor for `stingray_master.xlsx`: investigate, add, edit,
validate, and remove workbook records through a form-based UI instead of
direct spreadsheet manipulation.

```text
React interface (frontend/, Vite build served by FastAPI)
    ↓
FastAPI API + validation layer (backend/app/)
    ↓
SQLite database (var/workbook_manager.sqlite3 — normalized, auditable)
    ↕
openpyxl import/export adapter (backend/app/importer.py, sync.py)
    ↓
stingray_master.xlsx (canonical in Stage 1)
```

## Stage 1 status (current)

The workbook remains canonical. Import populates SQLite; edits are staged,
validated, and committed to SQLite with an append-only audit trail; approved
changes synchronize back to the workbook **only** through the repo's existing
gated pipeline (`editor_ops.apply_batch` → `save_workbook_safely()`), which
enforces Excel-lock refusal, staleness checks, batch validation, temp-copy
dry-run, package + schema validation, automatic backup, and atomic replace.
Stage 2 (SQLite canonical, Excel becomes import/export format) requires no
API or React changes — only the sync direction flips.

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

1. **Import** — `POST /api/import` (the UI triggers this on first load).
   Every duplicate identifier, missing sheet/column, and unresolved
   relationship is reported with sheet/row/entity detail; nothing is
   silently dropped (rows with issues still import; first occurrence wins
   on duplicates).
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
5. **Sync** — dry-run first (full gate, no write), then an explicit
   confirmation writes the workbook with an automatic timestamped backup
   (`backups/`) and an entry in `form-output/workbook-edit-log.jsonl`.
   After a live write, regenerate artifacts per the repo README gates.
6. **Export** — `POST /api/export` regenerates a comparison workbook under
   `var/exports/` from the database (unmanaged sheets preserved verbatim)
   for diffing against the live workbook.

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
# full editor_ops dry-run + scratch-copy live-write gates (slower):
WBM_SLOW_GATE=1 .venv/bin/python -m pytest tests/test_workbook_manager.py -q
```

API tests skip automatically until the backend requirements are installed.
