# Outcome rubric — Database workflow Pass 3 (request connections and promotion coordination)

Date: 2026-07-30
Source commit at start: `fa0eee7` (branch `db-workflow`, clean tree)
Owning specification: `docs/superpowers/specs/2026-07-22-reliable-workbook-database-workflow.md` §6 Pass 3

## Task summary

- **Goal:** Implement exactly the five required changes of Pass 3 — lifespan-run bootstrap, request-scoped projection/durable connections with WAL plus bounded busy timeout, an extended process-local lock plus a projection reader gate, single-process deployment documentation, and concurrent first-load / reader-drain tests before any promotion code may call `os.replace()`.
- **Changed surface:** tooling (manager backend), validation/tests, docs.
- **Source-of-truth decision:** the workbook stays canonical; the projection store stays disposable; the durable store keeps workflow/recovery state. No workbook, generated-artifact, publication, runtime, or dealer authority changes.
- **Protected boundaries:** no write to `stingray_master.xlsx`, `form-output/`, or `form-app/data.js`; Pass 1 write containment stays active; `POST /api/sync` with `write=true` stays refused; no candidate promotion implementation (Pass 4), no ChangeSet emission (Pass 5), no new dependency, no distributed locking, no multi-worker support.
- **Expected files:** `workbook-manager/backend/app/db.py`, `workbook-manager/backend/app/main.py`, `workbook-manager/run.sh`, `workbook-manager/README.md`, `README.md`, `tests/test_workbook_manager_api_concurrency.py` (new), `tests/test_workbook_manager.py` (connection-accessor call sites), and the Pass 3 result section of the owning specification.

## Required outcome criteria

1. **C1 — Bootstrap runs in lifespan, before serving.** Storage bootstrap completes during FastAPI startup: entering the app lifespan with no request creates both stores with matching `storage_manifest` markers. No request path performs first-time bootstrap lazily.
2. **C2 — Connections are request-scoped.** Each request opens its own projection and durable-state connection and closes it when the request ends; no module-level connection object survives a request. Proof must observe two concurrent requests holding two distinct connections, and a closed connection after the request.
3. **C3 — Every connection carries WAL and a bounded busy timeout.** Both request-scoped connections and every bootstrap/candidate connection report `journal_mode=wal` and a nonzero `busy_timeout`.
4. **C4 — Foreign keys are enforced only for durable manager-state relationships.** Durable connections run with `PRAGMA foreign_keys=ON` and reject a `change_history` row referencing a nonexistent `pending_changes` id. Projection connections keep enforcement OFF so unresolved workbook references still import and are *reported* as findings, never rejected by SQLite. A test must prove both directions.
5. **C5 — The process-local lock covers durable-state mutations, promotion, and workbook apply.** Staging/commit/discard/revalidate, sync, backup, and the promotion path serialize on the same lock the Pass 2 bootstrap uses. Proof: concurrent durable mutations do not interleave and no `database is locked` error occurs.
6. **C6 — A projection reader gate drains readers deterministically.** Promotion blocks new projection readers, waits for open request-scoped projection connections to close, and only then performs replacement. Tests must observe: (a) quiesce waits while a reader is open, (b) quiesce proceeds once the reader closes, (c) a reader arriving during quiesce does not enter before quiesce ends, (d) the wait is bounded and fails closed rather than hanging forever. No second durable projection-generation state machine is added.
7. **C7 — After a swap, subsequent requests open the promoted projection.** Replacing the projection file under the gate makes the next request report the new manifest identity (migration id / source hash), proving no stale handle is reused.
8. **C8 — Concurrent first-load has no lock errors.** Concurrent status/first-load requests against a fresh store all succeed, run exactly one migration (one migration id, no duplicate archive or recovery rows), and report no SQLite lock error.
9. **C9 — Single-process deployment is enforced and documented.** `run.sh` refuses a multi-worker invocation; `workbook-manager/README.md` and the root README record single-process-only serving and the Pass 3 state. No distributed locking is added.
10. **C10 — RED before GREEN.** Every criterion above has a focused test that was observed failing before the implementation change, per the owning specification §9.
11. **C11 — Protected surfaces unchanged.** `git status` plus hashes prove `stingray_master.xlsx`, `form-output/`, and `form-app/data.js` are untouched; the existing manager, catalog, projection, shared-writer, shared-ChangeSet suites and the frontend build still pass; workbook package and schema validation pass.
12. **C12 — Receipt and memory.** `outcome.md`, `verifier-report.md`, `validation-output.txt`, and `run.json` exist; `STATE.md` gains verified facts and a last-session pointer; the owning specification records the Pass 3 result.

## Stop conditions

- All required changes implemented through the pinned owners, with real command output recorded in `validation-output.txt`.
- An independent verifier grades C1–C12 from artifacts, diffs, and validation output and returns pass in `verifier-report.md`.
- `STATE.md` and `run.json` updated; skill-update decision recorded.

## Max iterations

3 maker/verifier cycles.
