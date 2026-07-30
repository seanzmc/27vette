# Independent verifier report — Database workflow Pass 3 (cycles 2 and 3)

Run: `fable5loop/runs/2026-07-30-dbpass3-request-connections`
Owning specification: `docs/superpowers/specs/2026-07-22-reliable-workbook-database-workflow.md` §6 Pass 3
Rubric graded: `fable5loop/runs/2026-07-30-dbpass3-request-connections/outcome.md`, criteria C1–C12
Graded state: working tree of `db-workflow` at source commit `fa0eee7` (uncommitted Pass 3 changes)
Verifier context: independent. Cycle 1's report was read only to check whether each blocker was really fixed, never trusted as evidence. Cycle 3 was graded as a delta by the same verifier that graded cycle 2, against the findings that verifier itself raised.

## Verdict

**pass (final, after cycle 3).**

Cycle 2 graded C1–C12 pass with five non-blocking findings. Cycle 3 closed all five; I re-verified the delta adversarially and found no blocker and no regression. Four of my five earlier findings are **closed on evidence I produced myself**, and the fifth (receipt accuracy) is closed except for two cosmetic staleness nits recorded below. The final module is `29 passed`, the four manager suites are `85 passed, 2 skipped` in both orders, the loop contract tests are `13 passed`, and the protected-path hashes are unchanged.

### Cycle 2 verdict (retained)

**pass.**

All four cycle-1 blockers are fixed in code, and I reproduced each fix myself rather than accepting the maker's prose:

1. **Receipt/memory (C12).** `run.json` exists with a `skill_update.decision` of `updated`; `fable5loop/STATE.md` gained a dated Verified-facts bullet, four Lessons-learned bullets, and a Last-session entry pointing at this run folder; `fable5loop/skills/27vette-fable5-compounding.md` gained four durable lessons. The loop validator failed **before** I wrote this file, and its only complaints were about the cycle-1 verifier report I was tasked to replace; it passes after this rewrite (both outputs quoted below).
2. **Thread starvation (C5).** `durable_write_lock` (`workbook-manager/backend/app/main.py:134-160`) is an `async` generator dependency polling `STATE_LOCK.acquire(blocking=False)` under a `STATE_LOCK_WAIT_SECONDS` deadline. I re-ran the cycle-1 repro at a *harsher* setting than cycle 1 used (limiter shrunk to 4 tokens, 24 concurrent `POST /api/backup` instead of 12): `done=24 pending=0 codes=[200]`. The wedge is gone. I also audited for new defects — no lock leak on `HTTPException`, none on an unhandled `RuntimeError`, correct release (a plain `Lock` is thread-agnostic, so releasing on the event loop after a threadpool handler is legal), a bounded poll rather than an unbounded spin, fail-closed `503 state_lock_busy` under contention, and no reentrant acquisition anywhere (`STATE_LOCK` is taken in exactly two places: the dependency and `db.py:739` `bootstrap_storage`, which is lifespan-only).
3. **`WEB_CONCURRENCY` (C9).** `workbook-manager/run.sh:26-30` refuses any `WEB_CONCURRENCY` other than `1`. I could not defeat it with `0`, `01`, `" 4"`, `"1 "`, `--workers=4`, or `--workers 4`; `${WEB_CONCURRENCY:-}` survives `set -u` (the script starts uvicorn normally with the variable unset). uvicorn 0.51.0 has no `-w` short flag.
4. **Full lock coverage (C10).** I dropped `_lock=Depends(durable_write_lock)` from **four** different routes, one at a time, in a throwaway worktree — `run_import`, `sync_endpoint`, `backup`, `discard` — and `test_every_durable_mutating_endpoint_holds_the_shared_process_lock` failed every time.

I also independently confirmed the cycle-1 should-fix items: `_checkpoint_legacy` now uses `connect()` (`db.py:414`); the bootstrap projection swap routes through `PROJECTION_GATE` via `_replace_projection` (`db.py:708-717`) and cannot deadlock or double-block at startup (lifespan runs before any request, so `_readers` is 0 and each `quiesce()` exits before the next call); the busy-timeout test asserts `dbmod.BUSY_TIMEOUT_MS` rather than `> 0`; a request without the lifespan returns an explicit `503 storage_not_bootstrapped`; and the module-level-connection test now asserts `assertFalse(hasattr(...))` plus source-level absence instead of a `getattr` tautology.

Three findings survive as **non-blocking recommendations** (detailed under Required Fixes): the `REFERENCES pending_changes(id)` DDL change has no migration for a store created by Pass 2, and two mutations still survive the new test module (`busy_timeout` pragma deletion, and removing the gate from `_replace_projection`). None of them falsifies a C1–C12 criterion as written.

Scope discipline is clean at cycle 2. No Pass 4 promotion, Pass 5 ChangeSet emission, or Pass 7 UI work. `anyio` is **not** a new dependency: it is a hard requirement of `starlette` (`['anyio<5,>=3.6.2', ...]`), which `fastapi` already pulls in, and `workbook-manager/backend/requirements.txt` is unchanged. No product/business data change; `stingray_master.xlsx`, `form-output/`, and `form-app/data.js` are byte-identical. No workbook validation was weakened — package and schema validation both return zero issues, and `POST /api/sync` with `write=true` is still refused (`main.py:715-721`).

## Cycle 3 delta verification

Scope of the delta I was asked to grade: `SCHEMA_VERSION` 1 → 2 with an in-place durable upgrade, removal of the explicit `busy_timeout` pragma, new gating tests for `_replace_projection`, `TestDurableSchemaUpgrade`, the re-anchored `schema_version` assertion in `tests/test_workbook_manager_import_projection.py:159-164`, and the receipt/spec/STATE corrections. I did not re-derive C1–C12 from scratch; I re-ran them for regression and attacked only what changed.

**1. Does the upgrade preserve every row and every column value?** Yes — verified on full row payloads, not counts. I built a schema-1 durable store with 25 deliberately hostile `change_history` rows (embedded single and double quotes, backslashes, `ü`, an emoji in nested JSON, `NULL` in both `old_json` and `src_row`, empty strings, 11-digit integers, an embedded newline) and compared every column of every row before and after: `EVERY COLUMN VALUE IDENTICAL: True`, `id sequence preserved: True`, `idx_history_entity` restored, no `change_history_schema1` left behind. The maker's own two tests assert **counts only** (`tests/test_workbook_manager_api_concurrency.py:299-310`), so this stronger property is verified by me, not by the suite.

**2. Safe on a store that already has the FK?** Yes. A store stamped version 1 whose `change_history` already declares the foreign key takes the short path at `db.py:762-767`: the manifest is stamped to 2, payloads are byte-identical, and no table rebuild happens.

**3. Safe on an interrupted run?** Yes, at four independent interruption points. I injected a failure before the row copy, before the `DROP`, and before the version stamp, and additionally killed the process outright with `os._exit(9)` mid-upgrade from a child process. In all four cases: rows preserved and payload-identical, **no** leftover `change_history_schema1`, manifest still at version 1, and the retry on next start completed the upgrade cleanly with identical payloads and the FK present. `BEGIN IMMEDIATE` plus WAL rollback makes this genuinely atomic.

**4. The interesting case — rows whose `pending_change_id` is already dangling.** The upgrade **preserves them and the store stays fully usable**: it neither fails closed nor silently drops. `_upgrade_durable_store` opens via `connect(state_path)` with `foreign_keys` defaulting off (`db.py:760`), so the `INSERT ... SELECT` copy is not FK-checked, and SQLite never validates pre-existing rows when enforcement is later switched on. I confirmed the orphan row survives with `pending_change_id=424242`, the store accepts new inserts and still updates the orphan row, and `PRAGMA foreign_key_check` reports exactly `1` violation. This is the right data-preservation choice, but nothing surfaces that violation to an operator — recorded as a non-blocking recommendation.

**5. Does removing the explicit busy-timeout pragma leave the effective timeout unchanged?** Yes, on both connection kinds, and I checked behavior rather than the pragma alone. Projection and durable connections both report `busy_timeout=5000` with `journal_mode=wal` and the correct `foreign_keys` value; with `WBM_BUSY_TIMEOUT_MS=7321` both report `7321`; and with the value set to 1500 ms a genuinely contended writer **waited 1.65 s** before `database is locked`. The deleted line was dead code, exactly as the new comment at `db.py:82-86` claims. This is the cleaner resolution of my cycle-2 finding 3 than the alternative I suggested.

**6. Do the new tests fail when the implementation is broken?** Yes — six mutations, all caught, in a throwaway worktree: `SCHEMA_VERSION` reverted to 1 → both upgrade tests fail; `_upgrade_durable_store` made a no-op → both fail; version stamp omitted → both fail; renamed table not dropped → the idempotence test fails; the row copy deleted → both fail; and `quiesce` removed from `_replace_projection` → **both new gating tests fail**. That last one is the direct closure of cycle-2 mutation M8, which previously survived a fully green suite.

**7. Regressions.** None. Four manager modules `85 passed, 2 skipped` in the documented order and again reversed; the new module `29 passed` three consecutive times; loop contract tests `13 passed`; protected-path `git status` empty with both hashes unchanged. The re-anchored assertion in `tests/test_workbook_manager_import_projection.py` is a strict improvement — it now pins **both** stores to `dbmod.SCHEMA_VERSION` instead of the literal `1`, and it is what makes mutation N1 fail.

**8. Does the receipt still overstate anything?** Materially, no — the corrections are honest. `run.json` now separates "first draft 16 failed / 5 passed" from "the final module fails 21 of 25", records cycle_2 as pass with my five findings and their close status, and reports `29 passed` / `85 passed, 2 skipped`; every number matches what I measured independently. Two cosmetic staleness nits remain, listed under Required Fixes.

## Criteria

Cycle-2 grades stand; the cycle-3 delta changes no grade. C4 and C10 are strengthened (the C4 upgrade-path caveat is now closed and the C10 M8 survivor is now caught), and C3's mechanism changed without changing behavior.

| # | Criterion | Grade | Evidence |
|---|---|---|---|
| C1 | Bootstrap runs in lifespan, before serving | **pass** | `main.py:62-90` — `lifespan()` calls `config.ensure_dirs()` + `dbmod.bootstrap_storage(...)`, stores the result on `app.state.storage_bootstrap`, sets `_STORAGE_READY`; `app = FastAPI(..., lifespan=lifespan)`. Repo-wide grep confirms `bootstrap_storage` has exactly one backend caller (`main.py:67`) — no request path can bootstrap, so no request can self-deadlock on the non-reentrant `STATE_LOCK` that `bootstrap_storage` takes at `db.py:739`. `test_lifespan_bootstraps_storage_before_serving_any_request` asserts both stores and matching manifests exist *before* any request. Fail-closed path proven: `test_requests_report_an_explicit_reason_without_the_lifespan` → 503 `storage_not_bootstrapped`. |
| C2 | Connections are request-scoped | **pass** | `main.py:103-131` — `projection_connection`/`state_connection` are per-request generators that `close()` in `finally`. Beyond the shipped test I proved genuine concurrency myself: I wrapped `open_projection_connection`/`open_state_connection` with a 4-way `threading.Barrier` so all four in-flight `/api/status` requests were forced to overlap, and got `projection: 4 connections opened, 4 distinct ids`, `state: 4 connections opened, 4 distinct ids`, gate readers back to 0. Closure is asserted by `assertRaises(sqlite3.ProgrammingError)` after the generator finishes. Mutation M12 (module-level cached projection connection) → 4 tests fail. |
| C3 | WAL + bounded busy timeout on every connection | **pass (one test-strength note)** | `db.py:77-92` — every `connect()` sets `journal_mode=WAL`, `busy_timeout=BUSY_TIMEOUT_MS`, and passes `timeout=BUSY_TIMEOUT_MS/1000`; all bootstrap/candidate builders (`_build_projection_candidate`, `_build_durable_candidate`, `_read_manifest_path`, `_checkpoint_legacy`) go through it — bare `sqlite3.connect` no longer appears anywhere in the bootstrap path. Asserted by `test_connect_sets_wal_and_the_configured_busy_timeout` (equality with `BUSY_TIMEOUT_MS`), `test_busy_timeout_follows_the_environment_override` (7321), and `test_request_connections_carry_wal_timeout_and_scoped_foreign_keys`. Note: mutation M6 (delete the explicit pragma) still leaves `25 passed`, because `sqlite3.connect(timeout=…)` sets the same value — behavior is correct either way, but no test distinguishes the two mechanisms. `sync.backup_database` opens its *backup destination* with bare `sqlite3.connect` (`sync.py:217`); that is a write-once output file, not a manager store, so it is outside this criterion. |
| C4 | Foreign keys only for durable manager state | **pass (upgrade-path caveat)** | `db.py:91` parameterizes the pragma; `main.py:100` is the only `foreign_keys=True` caller. `change_history.pending_change_id` now declares `REFERENCES pending_changes(id)` (`db.py:271`). Both directions asserted: `test_durable_connection_enforces_manager_owned_foreign_keys` (IntegrityError on a dangling id) and `test_projection_connection_still_ingests_unresolved_workbook_reference` (orphan `sec_does_not_exist_001` imports fine). Mutation M13 (force `foreign_keys=OFF`) → 2 tests fail. Caveat, verified by me and recorded as a recommendation: `SCHEMA_VERSION` stayed `1`, so a durable store created by Pass 2 matches the manifest check at `db.py:743-755`, bootstrap returns `ready`, and the old FK-less `change_history` DDL is retained — I reproduced a dangling `pending_change_id` being **accepted** on such a store. |
| C5 | One lock over durable mutations / promotion / apply | **pass** | All seven mutating routes declare `_lock=Depends(durable_write_lock)` first: `main.py:326` import, `625` stage, `648` discard, `659` validate, `669` commit, `711` sync, `746` backup. Same `STATE_LOCK` as bootstrap (`db.py:64`, `739`). Wedge repro at limiter=4 / 24 concurrent mutations: `done=24 pending=0 codes=[200]`, `STATE_LOCK locked after storm: False`. Leak audit: 409 refusal → `locked: False`; injected `RuntimeError` inside `backup` → `locked: False` and the next `/api/backup` returns 200; contended acquire with the lock held by another thread → `503 state_lock_busy`, lock still free afterwards. Reentrancy audit: no module other than `main.py` and `bootstrap_storage` touches `STATE_LOCK`; `staging`, `sync`, `importer` open no manager-store connections and take no lock. `test_concurrent_durable_mutations_do_not_report_lock_errors` shows no `database is locked`. |
| C6 | Projection reader gate drains readers deterministically | **pass** | `db.py:99-175` — `ProjectionGate.reader`/`quiesce` on one `Condition`; both waits are deadline-bounded and raise `ProjectionBusyError`; a failed `quiesce` resets `_blocked` and re-notifies so readers are re-admitted. All four required behaviors have tests: (a) `test_quiesce_waits_for_an_open_reader_then_proceeds`, (b) the same test's post-drain assertion, (c) `test_reader_arriving_during_quiesce_waits_for_promotion_to_finish` (asserts order `["promotion", "reader"]`), (d) `test_quiesce_fails_closed_when_readers_do_not_drain` + `test_reader_fails_closed_while_promotion_holds_the_gate`. End-to-end at the request layer: `test_requests_are_refused_while_promotion_holds_the_projection_gate` (503) and `test_promotion_waits_for_an_in_flight_reader_before_replacement`. Mutations M10 (quiesce stops waiting for readers) → 3 fail; M11 (reader ignores `_blocked`) → 3 fail. No second projection-generation state machine: the gate stores only `_readers`/`_blocked`; identity comes from the projection's own `storage_manifest`. |
| C7 | After a swap, later requests open the promoted projection | **pass** | `main.py:243-251` `_projection_manifest` reads `storage_manifest` from the request's own connection, surfaced in `/api/status`. `test_after_a_gated_swap_the_next_request_reports_the_promoted_manifest` builds a real candidate file, `os.replace`s it under `quiesce()`, and asserts the next request reports the new `migration_id` and `source_sha256`. Mutation M12 (cache the projection connection) makes exactly this test fail, proving it detects a stale handle. |
| C8 | Concurrent first-load has no lock errors | **pass** | `test_concurrent_first_load_uses_independent_connections` (16 requests / 8 threads, all 200, no `database is locked`, matching manifests) and `test_concurrent_first_load_migrates_a_legacy_database_exactly_once` (8 concurrent requests over a seeded legacy combined database → exactly one `migration_id`, one archive, zero leftover `.wbm-split-archive-*` temp files). Both green across three consecutive module runs. |
| C9 | Single-process deployment enforced and documented | **pass** | `run.sh:12-30`. My own attempts to defeat it: `--workers 4` → rc=2; `--workers=4` → rc=2; `WEB_CONCURRENCY=4` → rc=2; `WEB_CONCURRENCY=0` → rc=2; `WEB_CONCURRENCY=01` → rc=2; `WEB_CONCURRENCY=" 4"` → rc=2; `WEB_CONCURRENCY="1 "` → rc=2 (conservative, correct). `set -u` survives because the guard uses `${WEB_CONCURRENCY:-}`; with the variable unset the script starts uvicorn normally (`Application startup complete`, no `unbound variable`). uvicorn 0.51.0 exposes no `-w`. The only residual argv vector is `--env-file`, which uvicorn loads at `config.py:345-349` *before* reading `WEB_CONCURRENCY` at `351-352`; `python-dotenv` is not installed in this venv, so that path raises `ModuleNotFoundError` instead of starting workers. Docs: `run.sh:2-8`, `workbook-manager/README.md` ("Supported serving is **single-process only**"), root `README.md:137-148`. No distributed locking added. Mutation M14 (delete the `WEB_CONCURRENCY` guard) → `test_run_script_refuses_the_environment_worker_count` fails. |
| C10 | RED before GREEN | **pass** | I reproduced RED myself in a throwaway worktree at `fa0eee7` with only the new test module copied in: **`21 failed, 4 passed`** (the maker's `16 failed, 5 passed` predates the five cycle-2 tests). Every criterion above has at least one of those failures. Test strength probed with 11 independent mutations; **9 were caught** (M1–M4 route lock drops, M5 blocking sync dependency, M7 projection FK on, M10/M11 gate, M12 cached connection, M13 durable FK off, M14 run.sh guard). Two survive and are recorded as recommendations, not blockers: **M6** (delete the explicit `busy_timeout` pragma — indistinguishable because `sqlite3.connect(timeout=…)` sets the same value) and **M8** (make `_replace_projection` bypass the gate — no test covers the bootstrap swap's gating). A third, **M9** (drop `_require_storage_ready()` from `projection_connection` only), also survives, but harmlessly: `state_connection` still guards and every affected route depends on it. |
| C11 | Protected surfaces unchanged | **pass** | `git status --porcelain -- stingray_master.xlsx form-output form-app` is empty; hashes match the recorded values exactly. Manager suites `81 passed, 2 skipped` in the documented order and again in reverse order. New module `25 passed` three times in a row (1.77s / 1.76s / 1.78s — no flakiness). Shared ChangeSet + shared writer `76 passed, 7 subtests passed`. Frontend build succeeded. Workbook package validation `"status": "valid", "issue_count": 0`; schema validation `"status": "valid"`, 0 issues / 0 errors / 0 warnings. The working tree contains only the nine expected paths plus the new test module and this run folder. |
| C12 | Receipt and memory | **pass** | `outcome.md`, `verifier-report.md` (this file), `validation-output.txt`, `run.json` all present. `run.json` carries `skill_update.decision = "updated"` with an existing evidence path, `verifier.required`/`independent_context` true, `cycles: 2`, and the cycle-1 blocker list. `STATE.md` gained a dated Verified-facts bullet with an `Evidence:` pointer, four Lessons-learned bullets, and a Last-session entry naming `fable5loop/runs/2026-07-30-dbpass3-request-connections/`. The owning specification records a "Pass 3 result" section. The loop validator failed before this rewrite **only** on the cycle-1 report (two disallowed invocation-shaped lines and four missing sections) and passes after it. One hygiene note: `run.json` `verifier.verdict` and the STATE Last-session entry already asserted "pass" / "independent verifier passed on cycle 2" before this cycle ran; that is now accurate, but a receipt should not pre-record a verdict the verifier has not yet returned. |

## Evidence inspected

- `workbook-manager/backend/app/main.py` — full read. `55-57` bounded-wait constants; `62-90` lifespan + `_require_storage_ready` + app construction; `93-131` connection helpers and request-scoped dependencies; `134-160` `durable_write_lock`; `243-276` `_projection_manifest`/`_projection_state`; every route's dependency list (`281-749`).
- `workbook-manager/backend/app/db.py` — full read. `49-67` `STATE_LOCK`/`BUSY_TIMEOUT_MS`/`READER_DRAIN_SECONDS`; `77-92` `connect`; `95-175` `ProjectionBusyError`, `ProjectionGate`, `PROJECTION_GATE`; `254-272` `change_history` DDL; `411-421` `_checkpoint_legacy`; `526-699` candidate builders; `702-717` `_replace_candidate`/`_replace_projection`; `730-830` `bootstrap_storage`.
- `workbook-manager/run.sh` — full read plus seven adversarial invocations.
- `tests/test_workbook_manager_api_concurrency.py` — full read (25 tests, 5 classes).
- `git diff` for `README.md`, `workbook-manager/README.md`, `tests/test_workbook_manager.py`, `fable5loop/STATE.md`, `fable5loop/skills/27vette-fable5-compounding.md`, and the specification's Pass 3 result.
- `fable5loop/runs/2026-07-30-dbpass3-request-connections/{outcome.md,run.json,validation-output.txt}` and the cycle-1 verifier report.
- `AGENTS.md` §§1–5 (boundaries, approval gates, workbook safety), the loop validator source (report-format contract), `workbook-manager/backend/app/{config,sync,staging,importer}.py` (connection/lock audit), `.venv/.../uvicorn/{config,main}.py` (worker-count sources), `starlette` metadata (anyio provenance).
- Scratch artifacts I created outside the repo, all under the session scratchpad: a detached worktree at `fa0eee7` (RED + 11 mutations, removed afterwards), a wedge/leak repro script, a barrier-forced concurrency script, and a foreign-key upgrade-path script.

Cycle 3 additions:

- `workbook-manager/backend/app/db.py` — re-read `49-56` (`SCHEMA_VERSION = 2` and its rationale comment), `78-99` (`connect` with the pragma removed and the dead-code comment), `737-741` `_durable_history_declares_pending_fk`, `744-805` `_upgrade_durable_store`, `808-853` the two `bootstrap_storage` branches that now return `schema_upgraded`.
- `tests/test_workbook_manager_api_concurrency.py` — `207-349` `TestDurableSchemaUpgrade`, `416-455` the two new gating tests.
- `tests/test_workbook_manager_import_projection.py:156-165` — the re-anchored `schema_version` assertions.
- `fable5loop/runs/2026-07-30-dbpass3-request-connections/{run.json,validation-output.txt}` cycle-3 sections, plus the spec Pass 3 result (`884-895`, `936-946`) and the `STATE.md` Verified-facts and Last-session entries.
- A second detached worktree at `fa0eee7` for the six cycle-3 mutations, removed afterwards; three attack scripts (payload-preservation and FK-dangling, four-way interruption including a hard process kill, and version/busy-timeout edge cases).

## Validation Output Inspected

Loop validator, before this rewrite (its only complaints were about the cycle-1 report this file replaces):

```
Fable 5 loop validation failed:
- direct validator invocation in fable5loop/runs/2026-07-30-dbpass3-request-connections/verifier-report.md:18
- direct validator invocation in fable5loop/runs/2026-07-30-dbpass3-request-connections/verifier-report.md:191
- fable5loop/runs/2026-07-30-dbpass3-request-connections verifier report missing required section: Validation Output Inspected
- fable5loop/runs/2026-07-30-dbpass3-request-connections verifier report missing required section: Required Fixes Before Pass
- fable5loop/runs/2026-07-30-dbpass3-request-connections verifier report missing required section: Durable Lesson Candidates
- fable5loop/runs/2026-07-30-dbpass3-request-connections verifier report missing required section: File Edit Statement
RC=1
```

`tests/test_fable5_loop_contract.py`, before this rewrite:

```
F............                                                            [100%]
E       AssertionError: assert ['direct vali...it Statement'] == []
E         Left contains 6 more items, first extra item: 'direct validator invocation in fable5loop/runs/2026-07-30-dbpass3-request-connections/verifier-report.md:18'
1 failed, 12 passed in 0.75s
```

Both after this rewrite:

```
Fable 5 loop validation passed: 3 tiers, 4 layers, required artifacts, Claude setup, memory, skill, routine, outcomes, and eval rubric are present.
RC=0

.............                                                            [100%]
13 passed in 0.72s
```

New module, three consecutive runs (flakiness check):

```
=== run 1 === 25 passed, 1 warning in 1.77s
=== run 2 === 25 passed, 1 warning in 1.76s
=== run 3 === 25 passed, 1 warning in 1.78s
```

Four manager modules, documented order (`catalog`, `import_projection`, `api_concurrency`, `manager`) then reversed:

```
81 passed, 2 skipped, 1 warning in 10.04s
81 passed, 2 skipped, 1 warning in 10.36s
```

RED reproduction — worktree at `fa0eee7`, only the new test module copied in:

```
21 failed, 4 passed, 1 warning in 60.62s (0:01:00)
```

Mutation proofs (throwaway worktree; the repo itself was never edited):

```
### M1 drop lock dep from run_import
FAILED ...::test_every_durable_mutating_endpoint_holds_the_shared_process_lock
### M2 drop lock dep from sync_endpoint
FAILED ...::test_every_durable_mutating_endpoint_holds_the_shared_process_lock
### M3 drop lock dep from backup
FAILED ...::test_every_durable_mutating_endpoint_holds_the_shared_process_lock
### M4 drop lock dep from discard
FAILED ...::test_every_durable_mutating_endpoint_holds_the_shared_process_lock
### M5: durable_write_lock reverted to blocking sync dependency
FAILED ...::test_lock_contention_cannot_starve_the_request_threadpool
1 failed, 24 passed, 1 warning in 1.54s
### M6: remove explicit busy_timeout pragma from connect()
25 passed, 1 warning in 1.78s
### M7: projection connections enforce foreign keys too
FAILED ...::test_request_connections_carry_wal_timeout_and_scoped_foreign_keys
1 failed, 24 passed, 1 warning in 1.74s
### M8: _replace_projection bypasses the gate
25 passed, 1 warning in 1.82s
### M9: remove _require_storage_ready from projection_connection
25 passed, 1 warning in 1.76s
### M10: quiesce no longer waits for open readers
FAILED ...::test_quiesce_fails_closed_when_readers_do_not_drain
FAILED ...::test_quiesce_waits_for_an_open_reader_then_proceeds
FAILED ...::test_promotion_waits_for_an_in_flight_reader_before_replacement
3 failed, 22 passed, 1 warning in 1.25s
### M11: reader ignores the blocked flag
FAILED ...::test_reader_arriving_during_quiesce_waits_for_promotion_to_finish
FAILED ...::test_reader_fails_closed_while_promotion_holds_the_gate
FAILED ...::test_requests_are_refused_while_promotion_holds_the_projection_gate
3 failed, 22 passed, 1 warning in 1.42s
### M12: projection_connection reuses one module-level connection
FAILED ...::test_concurrent_first_load_migrates_a_legacy_database_exactly_once
FAILED ...::test_concurrent_first_load_uses_independent_connections
FAILED ...::test_each_request_opens_and_closes_its_own_connections
FAILED ...::test_after_a_gated_swap_the_next_request_reports_the_promoted_manifest
4 failed, 21 passed, 1 warning in 1.73s
### M13: durable connections stop enforcing foreign keys
FAILED ...::test_durable_connection_enforces_manager_owned_foreign_keys
FAILED ...::test_request_connections_carry_wal_timeout_and_scoped_foreign_keys
2 failed, 23 passed, 1 warning in 1.78s
### M14: run.sh drops the WEB_CONCURRENCY refusal
FAILED ...::test_run_script_refuses_the_environment_worker_count
1 failed, 24 passed, 1 warning in 2.05s
```

Scratch worktree restored and removed cleanly (implementation files byte-identical to the repo copies before removal):

```
IDENTICAL workbook-manager/backend/app/main.py
IDENTICAL workbook-manager/backend/app/db.py
IDENTICAL workbook-manager/run.sh
IDENTICAL tests/test_workbook_manager_api_concurrency.py
```

Cycle-1 wedge repro re-run against the current implementation, plus the lock-leak and fail-closed audit:

```
WEDGE REPRO limiter=4 requests=24: done=24 pending=0 codes=[200]
STATE_LOCK locked after storm: False
import refusal status: 409 STATE_LOCK locked: False
backup raised: RuntimeError boom
STATE_LOCK locked after unhandled error: False
gate readers after all: 0 blocked: False
post-error /api/backup: 200
contended (lock held elsewhere): 503 state_lock_busy
after 503, lock locked: False | next backup: 200
```

Concurrency proof for C2 (four `/api/status` requests forced to overlap on a barrier):

```
statuses: [200, 200, 200, 200]
projection: 4 connections opened, 4 distinct ids -> concurrent-distinct=True
state: 4 connections opened, 4 distinct ids -> concurrent-distinct=True
gate readers after: 0
```

`run.sh` adversarial invocations:

```
$ ./workbook-manager/run.sh --workers 4
workbook-manager: refusing '--workers'. Supported serving is single-process only;
manager locks and the projection reader gate are process-local.
rc=2
$ ./workbook-manager/run.sh --workers=4
workbook-manager: refusing '--workers=4'. ...   rc=2
$ WEB_CONCURRENCY=4 ./workbook-manager/run.sh
workbook-manager: refusing WEB_CONCURRENCY=4. ...   rc=2
$ WEB_CONCURRENCY=0 ./workbook-manager/run.sh
workbook-manager: refusing WEB_CONCURRENCY=0. ...   rc=2
$ WEB_CONCURRENCY=01 ./workbook-manager/run.sh
workbook-manager: refusing WEB_CONCURRENCY=01. ...   rc=2
$ WEB_CONCURRENCY=" 4" ./workbook-manager/run.sh
workbook-manager: refusing WEB_CONCURRENCY= 4. ...   rc=2
$ env -u WEB_CONCURRENCY WBM_PORT=8099 ./workbook-manager/run.sh   # set -u survival
INFO:     Started server process [65567]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8099 (Press CTRL+C to quit)
```

Foreign-key upgrade-path reproduction (durable store carrying the pre-Pass-3 `change_history` DDL):

```
fresh DDL has REFERENCES: True
second bootstrap: ready
foreign_keys pragma: 1
RESULT: dangling pending_change_id ACCEPTED on a pre-existing durable store
```

Protected surfaces, shared suites, build, and workbook gates:

```
$ git status --porcelain -- stingray_master.xlsx form-output form-app
(empty)
$ shasum -a 256 stingray_master.xlsx form-app/data.js
16415b913935b6d644fd1fbdcb5f6818d119e62cb6ef1fd077cff0f4b8d870e1  stingray_master.xlsx
7d97dba5294d09de4a622ec410810bad4c1d1955c043d5c69e6105896258b91c  form-app/data.js

$ .venv/bin/python -m pytest tests/test_workbook_changeset_service.py tests/test_editor_ops_apply.py -q
76 passed, 7 subtests passed in 81.34s (0:01:21)

$ (cd workbook-manager/frontend && npm run build)
dist/index.html                   0.45 kB │ gzip:  0.29 kB
dist/assets/index-B2qVorJL.css    8.58 kB │ gzip:  2.28 kB
dist/assets/index-TnijVMXd.js   182.28 kB │ gzip: 56.29 kB
✓ built in 635ms

$ .venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
{ "workbook": "stingray_master.xlsx", "status": "valid", "issue_count": 0, "issues": [] }

$ .venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
{ "workbook": "stingray_master.xlsx", "status": "valid", "issue_count": 0,
  "error_count": 0, "warning_count": 0, "issues": [] }
```

Dependency provenance (anyio is transitive through starlette, not a new requirement):

```
$ .venv/bin/python -c "import importlib.metadata as m; print(m.requires('starlette'))"
['anyio<5,>=3.6.2', "typing-extensions>=4.10.0; python_version < '3.13'", ...]
$ cat workbook-manager/backend/requirements.txt
fastapi>=0.111,<1
uvicorn>=0.30,<1
httpx>=0.27,<1   # test client for the pytest suite
```

### Cycle 3 delta evidence

Durable upgrade — full row-payload preservation over 25 hostile rows, already-FK store, and the dangling-FK case:

```
======== A: full payload preservation over 25 rich rows
schema_upgraded: True status: projection_rebuilt
row count before/after: 25 25
EVERY COLUMN VALUE IDENTICAL: True
FK declared: True
id sequence preserved: True
leftover schema1 table: 0
index restored: 1

======== B: already-has-FK store stamped version 1
schema_upgraded: True | payload identical: True | version now: 2

======== C: pre-existing DANGLING pending_change_id (the interesting case)
bootstrap returned: projection_rebuilt schema_upgraded: True
rows before/after: 26 26 | payload identical: True
orphan row survived: True 424242
foreign_key_check violations after upgrade: 1
store still WRITABLE after upgrade: True
existing orphan row still UPDATABLE: True
```

Interrupted upgrades — three injected failures plus a hard process kill, each followed by a retry:

```
[after copy, before DROP] interrupted: simulated crash before: DROP TABLE change_history_schema1
   rows preserved=True leftover_schema1_table=0 version=1
   RETRY: upgraded=True rows_identical=True fk=True version=2 leftover=0
[after RENAME, before copy] interrupted: simulated crash before: INSERT INTO change_history
   rows preserved=True leftover_schema1_table=0 version=1
   RETRY: upgraded=True rows_identical=True fk=True version=2 leftover=0
[after DROP, before version stamp] interrupted: simulated crash before: UPDATE storage_manifest
   rows preserved=True leftover_schema1_table=0 version=1
   RETRY: upgraded=True rows_identical=True fk=True version=2 leftover=0

[hard SIGKILL-equivalent mid-upgrade] child rc=9
   rows preserved=True leftover_schema1=0 version=1
   RETRY: upgraded=True rows_identical=True fk=True
```

Manifest version edge cases, and the effective busy timeout after the pragma was deleted:

```
== E: manifest version 0 / future version ==
  version 0: fails closed -> RuntimeError: durable store schema version 0 is not upgradable
  version 99: status=projection_rebuilt schema_upgraded=False

== F: effective busy timeout after removing the explicit pragma ==
  projection: PRAGMA busy_timeout=5000 (BUSY_TIMEOUT_MS=5000) journal=wal foreign_keys=0
  durable: PRAGMA busy_timeout=5000 (BUSY_TIMEOUT_MS=5000) journal=wal foreign_keys=1
  override projection: busy_timeout=7321 (expect 7321)
  override durable: busy_timeout=7321 (expect 7321)

== G: the timeout is REAL (a competing writer actually waits) ==
  blocked writer waited 1.65s before 'database is locked' (configured 1.5s)
```

Cycle-3 mutation proofs (throwaway worktree; the repo was never edited):

```
### N1: SCHEMA_VERSION reverted to 1 (the original cycle-2 finding)
FAILED ...::TestDurableSchemaUpgrade::test_bootstrap_upgrades_a_schema1_durable_store_and_keeps_its_rows
FAILED ...::TestDurableSchemaUpgrade::test_upgrade_is_idempotent_across_restarts
2 failed, 35 passed, 1 warning in 2.18s
### N2: _upgrade_durable_store becomes a no-op
FAILED ...::test_bootstrap_upgrades_a_schema1_durable_store_and_keeps_its_rows
FAILED ...::test_upgrade_is_idempotent_across_restarts
2 failed, 35 passed, 1 warning in 2.21s
### N3: upgrade never stamps the new schema_version (breaks idempotence)
2 failed, 35 passed, 1 warning in 2.20s
### N4: upgrade leaves the renamed schema1 table behind
FAILED ...::test_upgrade_is_idempotent_across_restarts
1 failed, 36 passed, 1 warning in 2.18s
### N5: upgrade copies no rows (data loss)
2 failed, 35 passed, 1 warning in 2.17s
### N6: _replace_projection bypasses the gate (previously SURVIVED as M8)
FAILED ...::TestProjectionReaderGate::test_projection_replacement_happens_under_the_gate
FAILED ...::TestProjectionReaderGate::test_projection_replacement_waits_for_an_open_reader
2 failed, 35 passed, 1 warning in 1.99s
```

Cycle-3 regression re-runs (documented order, reverse order, three module runs, loop contract, protected paths):

```
85 passed, 2 skipped, 1 warning in 10.14s
85 passed, 2 skipped, 1 warning in 10.11s
29 passed, 1 warning in 1.98s
29 passed, 1 warning in 2.05s
29 passed, 1 warning in 1.98s
.............                                                            [100%]
13 passed in 0.80s
$ git status --porcelain -- stingray_master.xlsx form-output form-app
(empty)
16415b913935b6d644fd1fbdcb5f6818d119e62cb6ef1fd077cff0f4b8d870e1  stingray_master.xlsx
7d97dba5294d09de4a622ec410810bad4c1d1955c043d5c69e6105896258b91c  form-app/data.js
```

## Required Fixes Before Pass

**Blocking: none.** All C1–C12 criteria are met, and none of the cycle-3 changes introduced a defect.

Status of the five cycle-2 recommendations:

1. **Durable foreign-key upgrade path — CLOSED.** `db.py:53` is now `SCHEMA_VERSION = 2`; `db.py:744-805` `_upgrade_durable_store` rebuilds only `change_history` under `BEGIN IMMEDIATE`, and `bootstrap_storage` calls it at `db.py:820`. I re-ran my original reproduction and it no longer reproduces: the dangling insert is now rejected, payloads are byte-identical, and the upgrade is atomic under a hard process kill. Mutations N1–N5 all fail the new tests.
2. **`_replace_projection` gating — CLOSED.** `tests/test_workbook_manager_api_concurrency.py:416-455`. Mutation N6 (the former survivor M8) now fails both tests.
3. **Busy-timeout assertion — CLOSED, by deletion.** `db.py:82-86` removes the pragma as unobservable dead code and says so. I verified the effective timeout is unchanged on both connection kinds, that the environment override still propagates, and that a real contended writer waits the configured interval.
4. **Receipt hygiene — CLOSED.** `run.json` now records cycle_2 (pass, with all five of my findings and their close status) and cycle_3 separately, rather than a bare pre-recorded verdict.
5. **RED count — CLOSED.** Restated as "the final module fails 21 of 25", with the 16-criterion first draft called out separately. It matches my own reproduction.

New, non-blocking, all cosmetic or forward-looking:

1. **A dangling foreign key is carried forward silently** (`workbook-manager/backend/app/db.py:760`). The upgrade connection deliberately leaves `foreign_keys` off, so pre-existing violations survive and `PRAGMA foreign_key_check` reports them forever with nothing surfacing that to an operator. Preserving the rows is the right call; consider running `foreign_key_check` after the upgrade and recording the count in the bootstrap result next to `schema_upgraded`.
2. **Stale line in the Pass 2 design section** (`docs/superpowers/specs/2026-07-22-reliable-workbook-database-workflow.md:129`): "New installations initialize both at schema version 1" now contradicts the shipped `SCHEMA_VERSION = 2`. The Pass 3 result section supersedes it, but the two should not disagree inside one document.
3. **One residual overstatement in the Pass 3 result** (same file, around line 939): the configured busy timeout is still listed among tests "observed failing against the intermediate build it fixes". That specific test cannot fail against the cycle-1 build — the pragma was present there, so the equality assertion holds. Drop it from that list.
4. **`run.json` `verifier.cycles` still reads `2`** while a `cycle_3` block exists alongside it.
5. **`schema_upgraded` is asymmetric** (`db.py:834`, `850` have it; the `initialized` and `migrated` branches at `db.py:873-877` and `908-912` do not). No caller reads it unconditionally today, but Pass 4 will be tempted to; return it from every branch or document that it is specific to the durable-manifest path.

## Durable Lesson Candidates

- **Fixing a wedge is not the same as proving the wedge is gone; re-run the original repro at a harsher setting.** Cycle 1 wedged with 12 requests against a 4-token limiter. Verifying the fix at exactly 12 would leave a reader unable to distinguish "fixed" from "lucky". I re-ran at 24 and got `done=24 pending=0`. When a defect was found by a synthetic stressor, verification of its fix should turn that stressor *up*.
- **A lock that moves from a sync to an async dependency needs a four-way audit, not a re-read.** Leak on `HTTPException`, leak on an unhandled exception, release from the wrong context, and reentrant acquisition are independent failure modes with independent probes, and none is visible from the diff. Exercise each explicitly and assert `lock.locked() is False` plus a successful follow-up request after every one.
- **A DDL change without a `SCHEMA_VERSION` bump is a silent no-op for existing stores.** The `REFERENCES` clause is real for freshly created databases and invisible for any database the previous pass created, because `CREATE TABLE IF NOT EXISTS` will not alter an existing table and the manifest still matches. Any change to a persisted schema must move the version that gates its rebuild, and the proof must start from a store created by the *previous* pass.
- **Mutation testing must include mutations you expect to survive.** Nine of my eleven mutations were caught; the two that survived (`busy_timeout` pragma, ungated `_replace_projection`) are the only interesting results, and both were invisible from a green suite. Report survivors explicitly and classify each as "behavior still correct, test blind" or "real gap" — a mutation list containing only caught mutations is a list of the mutations someone already knew about.
- **"Refuse the flag" is still not "refuse the capability", and residual vectors deserve naming.** The `WEB_CONCURRENCY` fix is correct, but `--env-file` reaches the same setting one layer down and is blocked here only because `python-dotenv` is absent from the venv. When a guard's completeness depends on a package *not* being installed, say so in the guard's comment, or the next dependency change silently reopens it.

From cycle 3:

- **A data-migration test that asserts row counts has not tested the migration.** Both shipped upgrade tests compare `COUNT(*)`, which cannot see a swapped column order, a lost `NULL`, a mangled non-ASCII string, or a renumbered primary key. Compare full row payloads before and after, over rows chosen to be hostile — quotes, backslashes, non-ASCII, emoji in nested JSON, `NULL` in nullable columns, empty strings, large integers, embedded newlines.
- **An in-place schema migration needs an interruption matrix, not one happy path.** Fail before the copy, before the drop, and before the version stamp, then kill the process outright — and after each one assert three things: the rows survived, no half-renamed table is left behind, and the *retry* completes. This upgrade passed all four, and that is the evidence that makes `BEGIN IMMEDIATE` a claim rather than a hope.
- **Deleting dead code is a legitimate way to close a "this assertion is too weak" finding — if you prove the deletion is a no-op.** The right answer to "the test cannot detect removing this pragma" turned out to be "then the pragma is dead code", not "make the test stricter". The proof obligation moves to behavior: same effective value on every connection kind, the override still propagates, and a genuinely contended writer waits the configured interval.
- **Migrating data with enforcement off is the correct default, but silence is not.** Copying under `foreign_keys=OFF` preserves pre-existing violations instead of failing closed or dropping rows — the right trade for durable state. What is missing is the report: run the integrity check after the migration and surface the count, or the violation lives forever with nothing pointing at it.
- **When a version constant changes, grep the prose for the old literal.** The code, tests, and result section all moved to version 2, while a design-section sentence still says new installations start at version 1. The same sweep catches assertions pinned to a literal — re-anchoring them to the constant is what made the revert mutation fail.

## File Edit Statement

I edited exactly one file: `fable5loop/runs/2026-07-30-dbpass3-request-connections/verifier-report.md` (this report). I created, modified, and deleted no other repository file, and I did not stage, commit, or push anything. All scratch work — the detached worktree at `fa0eee7`, the mutation copies, and the repro scripts — lived under the session scratchpad; the worktree was restored to byte-identical content and then removed, and `git worktree list` no longer shows it.

Two disclosures, both outside the tracked tree. First, `npm run build` in `workbook-manager/frontend` regenerated `frontend/dist/`, which is gitignored and untracked. Second, starting `run.sh` once with `WEB_CONCURRENCY` unset (to prove the guard survives `set -u`) ran the real lifespan bootstrap against the gitignored `workbook-manager/var/` store, which performed the designed legacy split of the local developer database; the original bytes are preserved and verified in `workbook-manager/var/workbook_manager.sqlite3.legacy-split-b7da0deb1039e33deae52978bb0a79d397931693c6eb2e53bf19e018eda76023.sqlite3`, whose SHA-256 matches its filename. The uvicorn process was stopped.

The same statement holds for cycle 3. I edited only this report. The six cycle-3 mutations were applied in a second detached worktree under the session scratchpad, `workbook-manager/backend/app/db.py` there was restored from a backup and confirmed byte-identical to the repo copy by SHA-256, and that worktree was removed (`git worktree list` shows none under the scratchpad). All upgrade attacks — including the hard process kill — ran against throwaway SQLite files in temporary directories, never against `workbook-manager/var/`. `git status --porcelain` shows the same ten modified paths, the new test module, and this run folder; the protected-path hashes are unchanged.
