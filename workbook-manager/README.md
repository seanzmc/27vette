# Workbook Manager (React + FastAPI + SQLite)

Workbook-traceable editor and audit console for `stingray_master.xlsx`.
The workbook remains canonical in this stage; SQLite is the relational query,
validation, staging, and audit surface.

```text
stingray_master.xlsx
    -> profiled and compiled into a temporary canonical SQLite candidate
    -> relational, lineage, reconciliation, and runtime-contract gates
    -> atomic promotion to workbook_manager.sqlite3
    -> FastAPI typed API
    -> React registry, findings, edit, history, and sync views
```

The database has central relationship tables plus identical physical 17-role
collections for `stingray`, `grand_sport`, and `z06`. Each model options table
uses `option_id` as its SQLite primary key. `source_table_catalog`,
`schema_mapping`, and `import_lineage` retain exact workbook names and row
provenance; the API resolves logical model/table roles through
`model_table_registry` rather than accepting SQL identifiers.

Each mapping records its workbook source role, reversible transform parameters,
and one approved contract status: `exact`, `identifier_normalized`,
`shared_source_split`, `semantic_alias`, `derived_from_contract`,
`contract_mismatch`, or `decision_required`. The latter two are reserved for
real blocking findings and are never invented; successful current-generation
imports contain neither and do not flatten mappings into a generic status.

## Safety boundary

- Import builds and audits a candidate database before atomic promotion.
- Unknown ownership, missing source roles, contract differences, and required
  business decisions fail closed with source evidence.
- Adds, updates, and deletes are staged and batch-validated before commit.
- Update and delete commits compare their staged old snapshot to the current
  canonical row inside the same immediate transaction used for revalidation
  and apply. A stale row rejects the whole batch with HTTP `409`; it is never
  silently overwritten.
- SQL history is append-only and tracks workbook sync state.
- Malformed or unreadable workbook sources return typed blocking import
  findings and leave the currently promoted database unchanged.
- Workbook writes are never direct. A live sync requires explicit confirmation
  and still uses `editor_ops.apply_batch()` -> `save_workbook_safely()` with
  lock, mtime, dry-run, package/schema, backup, and atomic-replace gates.
- This migration does not change generated runtime contracts or dealer
  submission behavior.

Ambiguous shared-source edits remain intentionally unavailable: a one-model
edit that would fan out through a shared workbook row, or an add whose shared
ownership cannot be represented unambiguously, is rejected rather than guessed.

## Setup

Run from the repository root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install -r workbook-manager/backend/requirements.txt

cd workbook-manager/frontend
npm ci
npm run build
cd ../..
```

The backend test modules also import the shared generator package directly:

```sh
export PYTHONPATH="$PWD/scripts"
```

## Run

```sh
./workbook-manager/run.sh
```

Open `http://127.0.0.1:8050/`. Environment overrides are `WBM_WORKBOOK`,
`WBM_DB`, `WBM_VAR_DIR`, and `WBM_PORT`. To keep a verification run isolated:

```sh
tmp_dir="$(mktemp -d /private/tmp/wbm-audit.XXXXXX)"
WBM_DB="$tmp_dir/audited.sqlite3" \
WBM_VAR_DIR="$tmp_dir/var" \
WBM_WORKBOOK="$PWD/stingray_master.xlsx" \
WBM_PORT=18050 \
./workbook-manager/run.sh
```

## Import

With the server running, import the canonical workbook through the typed API:

```sh
curl --fail-with-body \
  --header 'Content-Type: application/json' \
  --data "{\"workbook_path\":\"$PWD/stingray_master.xlsx\"}" \
  http://127.0.0.1:8050/api/imports
```

A successful response has `status: "validated"`, the three live models, zero
decision-required findings, and zero contract differences. HTTP `409` means
promotion stopped; review the returned source sheet, row, column, code, and
message rather than editing around it.

Primary read surfaces:

```text
GET /api/status
GET /api/imports/{import_run_id}
GET /api/imports/{import_run_id}/findings
GET /api/schema/mappings
GET /api/models
GET /api/models/{model_key}/tables
GET /api/models/{model_key}/tables/{table_role}
GET /api/models/{model_key}/variants
GET /api/models/{model_key}/runtime
GET /api/changes
GET /api/history
```

Write-capable routes (`/api/imports`, `/api/changes`, `/api/sync`, `/api/export`,
and `/api/backup`) must not be used for read-only browser verification. The
React client calls the same typed API and never constructs physical SQL names.

## Full completion audit

Run from the repository root with `PYTHONPATH` exported as shown above:

```sh
.venv/bin/python -m pytest tests/workbook_manager -q
.venv/bin/python -m pytest tests/test_workbook_manager.py -q
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
node --test tests/workbook_manager/test_frontend_contract.mjs
node --test tests/stingray-form-regression.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/z06-form-data-draft.test.mjs
(cd workbook-manager/frontend && npm run build)
git diff --check
```

The Grand Sport and Z06 Node generator tests refresh the generated timestamp in
their tracked runtime-contract files. Treat that as validation output, inspect
the diff, and do not stage a timestamp-only refresh when no generated artifact
change was requested.

Verify preserved source/runtime hashes:

```sh
shasum -a 256 stingray_master.xlsx form-app/data.js
python3 - <<'PY'
import hashlib
import subprocess
from pathlib import Path

files = subprocess.check_output(["git", "ls-files", "form-output"]).decode().splitlines()
digest = hashlib.sha256()
for name in files:
    file_hash = hashlib.sha256(Path(name).read_bytes()).hexdigest()
    digest.update(f"{file_hash}  {name}\n".encode())
print(digest.hexdigest(), "tracked form-output aggregate")
PY
```

Expected values for the completed migration:

```text
stingray_master.xlsx  03e8c9671185f238dde7f4bc8e7003da0f74d842d9cc2f76126f938cbb7b54d6
form-app/data.js       dd60534734c1330085ea74602515e1ab75aa964d3134c230abe0f26217b79e78
form-output aggregate 0a21250e7ea4fb5d93912c200671796eb92c3779aa8a8a77ac862b7dda9d6b03
```

`tests/workbook_manager/test_completion_audit.py` performs the final fresh
database schema audit: three live models, identical 17-role registries,
`option_id` primary keys, zero foreign-key violations, zero unresolved
decisions/contract differences, and no conceptual shared `options` table.

## Editing and sync workflow

1. Import a validated candidate database.
2. Select a model and canonical table role in Model Operations. The UI displays
   both the physical SQL table and workbook source sheet.
3. Stage a change. Validation reports canonical keys and workbook lineage.
4. Review dependencies and validate the complete staged batch.
5. Commit once; the transaction appends corresponding history rows.
6. Run a sync dry-run. A live sync additionally requires `confirm: "SYNC"` and
   the reviewed workbook mtime, then executes the existing guarded write path.
7. After any authorized live workbook write, regenerate and validate affected
   artifacts using the repository-level commands in the root `README.md`.

No live workbook write or dealer submission is part of the completion audit.
