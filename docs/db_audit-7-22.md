Verdict: HOLD.

The Workbook Manager is not currently a reliable workbook workflow. Keep `stingray_master.xlsx` canonical, but disable database re-import and live sync until the critical state-loss and conflict paths are fixed.

The approved relational design is directionally useful, but effectively unimplemented and partly stale. None of its planned compiler/catalog/migration modules exist, and its hardcoded three-model assumption no longer matches the workbook, which currently exposes six active models and three runtime-promoted models.

Current architecture

The reachable path is:

`workbook-manager/run.sh`
→ `backend/app/main.py`
→ shared conceptual SQLite tables defined by `backend/app/specs.py`
→ in-place workbook import
→ staged full-row snapshots
→ committed SQLite rows/history
→ translation back to `editor_ops.apply_batch()`
→ `save_workbook_safely()`

SQLite is therefore acting as both a workbook projection and a second mutable authority, without the conflict controls needed to reconcile those roles.

Critical findings

1. Re-import can erase the last valid database

Proven:

- `workbook-manager/backend/app/importer.py:88-95` clears the active database before validating the new workbook.
- `workbook-manager/backend/app/db.py:140-145` commits those deletions immediately.
- Disposable probe: removing `model_workbook_sources` caused a `KeyError`; the options count changed from 1,380 to 0.

Required correction:

- Compile/import into a new candidate SQLite file.
- Complete mapping, reference, reconciliation, and contract gates there.
- Atomically replace the current database only after all gates pass.
- Preserve the prior verified database on every error.

2. Re-import can make stale committed edits overwrite external workbook changes

Proven:

- `/api/import` blocks only staged rows, not committed-unsynced history: `backend/app/main.py:96-108`.
- History stores full `new_json` row snapshots: `backend/app/staging.py:303-320`.
- Sync reconstructs operations from those old snapshots: `backend/app/sync.py:40-69`.
- The re-import refreshes the stored workbook mtime: `backend/app/importer.py:142-145`.

Disposable probe:

- Committed a price edit.
- Externally changed the row description in the workbook.
- Re-imported.
- SQLite showed the external description, while the pending sync batch retained the old description and would overwrite it.
- The status reported the import as current because the mtime had been refreshed.

Required correction:

- Block re-import while any unsynced journal entry exists, or implement an explicit field-level rebase.
- Store field deltas with the base workbook SHA-256, mtime, and original field values.
- Detect same-field conflicts; preserve unrelated external edits.
- Never mark an old change current merely because a re-import captured a new mtime.

3. Staging does not validate the proposed final graph

Proven:

- Per-record validation queries only committed tables: `backend/app/validation.py:124-201`.
- Batch validation does not build a projected final state: `backend/app/staging.py:157-228`.
- A new exclusive group and its member cannot be staged together; the member is rejected because the parent is not committed yet.
- Delete confirmation can bypass existing dependencies without proving the dependent rows are removed in the same batch: `backend/app/staging.py:91-101`.

Required correction:

- Represent all pending edits as one final-state ChangeSet.
- Apply add/update/delete operations to an in-memory or transaction-local projection.
- Validate relationships, uniqueness, coordinated deletes, and parent/member additions against that projected graph exactly once.
- Remove `confirm_dependencies` as a substitute for valid final state. Confirmation may acknowledge a warning, not bypass relational integrity.

4. Several failure paths permanently strand committed work

Proven:

- Sync selects only `sync_status='pending'`: `backend/app/sync.py:33-37`.
- Any failed write changes those rows to `sync_failed`: `backend/app/sync.py:114-121`.
- No retry, requeue, or cancel transition exists.
- Disposable probe forced a sync failure; the next batch contained zero operations.
- Two committed edits to the same row generate two operations. `editor_ops` rejected them as contradictory, leaving both unsyncable.

Required correction:

- Coalesce journal entries by physical workbook key into base → final desired state.
- Introduce an explicit state machine such as:
  `draft → validated → committed → sync_pending → syncing → synced`
  with supported `sync_failed → retry_pending` and `cancelled`.
- Retain the exact failure and workbook state.
- Make retry idempotent.

High findings

5. Workbook schema semantics have competing owners

`backend/app/specs.py:1-9` claims to mirror the editor contract, but the canonical shared registry is already:

`scripts/corvette_form_generator/workbook_domain/registry.py:1-7`

Mechanical comparison found missing manager validation for:

- `color_overrides.option_id`
- `color_overrides.adds_rpo`
- `interiors.included_option_id`
- `model_interior_scope.requires_option_id`
- `default_selection_rules.condition_id` conditional references
- `asset_map.target_type → target_id` conditional references
- `model_workbook_sources.source_role` enum
- `interiors.Price` typing

Disposable proof: invalid `color_overrides.adds_rpo` staged and committed successfully, then the canonical editor rejected it.

Required correction:

- Delete the independent writable semantics in `backend/app/specs.py`.
- Derive database/API/UI metadata from `workbook_domain.registry`.
- Extend that registry where SQL mapping or lineage metadata is genuinely missing.
- Add a mechanical parity test so a writable family cannot diverge again.

6. Model ownership is not enforced

Proven:

- Foreign keys are intentionally disabled: `backend/app/db.py:11-13`.
- Model-scoped rows use free-text `model_id`.
- `_editable_guard()` permits an unknown model when no registry row exists: `backend/app/staging.py:46-62`.

Disposable probe:

- An option for `not_a_model` staged and committed.
- It had an empty source sheet.
- Sync skipped it because no target sheet could be resolved.

Required correction:

- Derive separate known, importable/editable, generatable, and published model sets from workbook metadata.
- Enforce model ownership through SQL foreign keys and service-level guards.
- Reject unknown, unpublished-only, or inactive source roles according to their actual lifecycle—not hardcoded model names.
- Do not implement the old plan’s fixed `LIVE_MODELS = ("stingray", "grand_sport", "z06")` without rebaselining it against the current workbook.

7. Import “with issues” is promoted as usable state

`backend/app/importer.py:121-145` records errors but still commits and updates the authoritative import metadata. Duplicate rows use first-wins behavior at `backend/app/importer.py:233-265`.

That contradicts the approved fail-closed design and is not workbook congruence.

Required correction:

- Classify findings as informational, contract mismatch, or decision required.
- Block candidate promotion on duplicate keys, missing identifiers, unresolved references, ambiguous ownership, missing required columns/sheets, or runtime-contract drift.
- Require:
  `source rows = imported rows + explicitly excluded rows`
- Give every exclusion exact sheet, row, field, value, reason, and contract impact.

8. Sync review binds only mtime, not workbook content

The manager records workbook SHA during import but does not include it in sync batches:

- Batch carries only mtime: `backend/app/sync.py:70-75`.
- `editor_ops` supports SHA verification when supplied: `scripts/corvette_form_generator/editor_ops.py:1225-1233`.

A probe changed workbook bytes while preserving mtime; the manager/editor identity check accepted it.

Required correction:

- Bind preview and write to exact workbook SHA-256 and mtime.
- Bind the reviewed operation set or ChangeSet hash as well.
- On write, verify all three immediately before live load and again before safe save.

9. A readback exception can escape after workbook mutation

`editor_ops.apply_batch()` restores the backup when live readback returns a failed result, but the call itself is outside an exception-restoration boundary:

`scripts/corvette_form_generator/editor_ops.py:1417-1427`

A disposable fault-injection probe caused live readback to throw after save; the workbook copy remained mutated.

Required correction:

- Wrap save plus all post-save verification in one restoration boundary.
- Any exception after save must restore and hash-verify the backup.
- Return `workbookState: restored` or `workbookState: unknown`; never imply untouched state.

Workflow/API findings

10. First-load API initialization races

`backend/app/main.py:41-50` lazily initializes one global SQLite connection without synchronization. Browser smoke produced an initial Form Structure `500` with:

`sqlite3.OperationalError: database is locked`

Retrying after initialization succeeded.

Required correction:

- Use FastAPI lifespan initialization and per-request connections or a serialized connection manager.
- Do not share an unsynchronized connection across worker threads.
- Add a concurrent first-load API test.

11. Current UI does not faithfully represent database relationships

Examples:

- Every Form Structure runtime step displayed “no sections mapped.” `backend/app/main.py:154-167` joins only `section_presentation.step_key` and ignores the master-section fallback.
- `RecordForm.jsx:28-34` sends model context only for `schema.model_scoped`.
- Model-key tables such as `default_selection_rules` are not marked `model_scoped`, so the UI sends `model_id=""`.
- An unchanged real default rule then fails its option reference against model `""`.

Required correction:

- Carry model context for every model-key family through schema response, UI payload, validation, history, and sync.
- Expose union and conditional reference metadata as finite controls.
- Fix structure fallback mapping.
- Browser-test actual unchanged workbook rows, not only synthetic adds.

12. Current focused tests are red

Actual result:

`1 failed, 27 passed, 2 skipped`

Failure:

`TestStagingWorkflow.test_scaffold_model_rejected`

This is partly a stale lifecycle expectation—the workbook has advanced—but it also demonstrates that model lifecycle handling is not derived consistently.

What needs to happen, in order

Pass A — Contain unsafe paths

1. Disable live `/api/sync` writes.
2. Disable re-import when staged or committed-unsynced changes exist.
3. Keep browsing and disposable export available.
4. Label the manager “read-only/provisional” until the following passes close.

Exit gate: no API path can mutate the canonical workbook or destructively replace the active database.

Pass B — Establish one workbook domain contract

1. Make `workbook_domain.registry` the only writable schema authority.
2. Add SQL mapping, ownership, conditional-reference, and lifecycle metadata there.
3. Remove `backend/app/specs.py` after all consumers migrate.
4. Derive model lifecycle sets from current workbook predicates.
5. Add mechanical registry/API/UI parity tests.

Exit gate: every writable family has one key/type/enum/reference definition.

Pass C — Build a verified disposable projection

1. Profile every workbook sheet and header.
2. Compile central and model-owned rows with exact lineage.
3. Build a candidate SQLite file with foreign keys enabled.
4. Reconcile every source row.
5. Run `PRAGMA foreign_key_check`.
6. Reconstruct a comparison workbook.
7. Generate and compare all currently promoted runtime contracts.
8. Atomically promote only a fully verified candidate.

Exit gate: malformed import leaves the previous database byte-for-byte unchanged.

Pass D — Replace full-row history with a final-state ChangeSet journal

Each ChangeSet needs:

- workbook SHA-256 and mtime;
- model and workbook family;
- canonical physical key;
- field-level before/after values;
- source sheet/row lineage;
- deterministic operation ordering;
- projected-final-state validation result;
- explicit status and retry history.

Exit gates:

- sequential edits to one row coalesce;
- unrelated workbook edits survive rebase;
- same-field conflicts block;
- parent/member additions and coordinated deletes validate together.

Pass E — Make sync recoverable and verifiable

1. Dry-run from the exact ChangeSet and workbook identity.
2. Persist the reviewed preview hash.
3. Require exact preview/ChangeSet/workbook binding for write.
4. Catch and restore on every post-save exception.
5. Support retry, requeue, and cancel.
6. Read back exact rows.
7. Mark only proven operations synced.

Exit gates:

- forced failure remains retryable;
- repeated retry is idempotent;
- rollback is hash-verified;
- no history row is silently skipped.

Pass F — Separate workbook and runtime publication state

Expose distinct statuses:

- database projection current;
- staged changes present;
- workbook synchronized;
- generated artifacts stale/current;
- runtime registry published/current.

After a workbook write, require package/schema validation, affected generation, runtime-contract comparison, and registry verification before the workflow reports current. Do not conflate a successful workbook save with customer-runtime readiness.

Pass G — Repair the API/UI as a thin client

1. Use controlled database connection lifecycle.
2. Resolve tables only by allowlisted model/family roles.
3. Surface lineage and blocking findings.
4. Carry model context consistently.
5. Render conditional/union references.
6. Remove any legacy route after the new route is proven.
7. Browser-smoke model navigation, structure, real-row editing, conflict display, retry, and post-write status.

Validation performed

- Workbook package validation: passed, 0 issues.
- Workbook schema validation: passed, 0 errors and 0 warnings.
- Workbook Manager tests: 27 passed, 1 failed, 2 skipped.
- Multiple disposable import/staging/sync probes reproduced the failures above.
- Browser smoke used a temporary workbook and database; no live sync was triggered.
- Final Git state: clean, `main...origin/main`.
- Canonical workbook, generated artifacts, runtime registry, deployment paths, and dealer-submission code were not modified.

Recommended immediate decision: treat the database as a disposable query projection plus a durable ChangeSet journal—not as a second business-data authority. Implement Pass A first, then rebaseline the approved design around the current shared registry and current model lifecycle before building the larger relational schema.

The independent audits confirm the same HOLD verdict. No change to the recommended sequence.

One additional confirmed failure strengthens Pass C: removing `model_master` produced 2,332 import errors, but the importer still committed the database as the active snapshot—with 0 models and 1,380 options. Import errors therefore need to block candidate promotion, not merely label the active database `imported_with_issues`.

All three audits were read-only against repository data or disposable copies. The canonical workbook, database, generated artifacts, and dealer boundaries remained untouched; the worktree stayed clean.