Audit verdict: do not merge this branch wholesale and advertise all three tools as supported.

The ingest compiler has substantial safety work and test coverage. The existing workbook editor remains the most trustworthy interactive writer. The workbook manager is not ready to write the canonical workbook: it contains reproducible state-loss paths, broken core UI paths, and a second schema/validation authority.

Bluntly: this is currently two competing workbook editors plus an ingest system carrying its previous review system inside it.

1. Critical findings

A. Workbook Manager can overwrite an external workbook edit

The manager treats SQLite as a second source of truth:

- A staged change is committed into change_history.
- A workbook re-import is blocked only when pending_changes exists; committed-but-unsynced history does not block it: workbook-manager/backend/app/main.py:89.
- Re-import refreshes the database and workbook mtime but retains pending history.
- Sync reconstructs updates from the old full-row after_json, not from field-level deltas: workbook-manager/backend/app/sync.py:31.
- The refreshed mtime makes the workbook appear current, so the normal stale check no longer protects the externally changed cells.

I reproduced this against a temporary workbook:

- The external description was successfully re-imported into SQLite.
- The pending sync batch still contained the old description.
- After re-import, the manager reported the workbook as not stale.
- Syncing would therefore overwrite the external description while applying an unrelated price edit.

That is a real data-clobber path. save_workbook_safely() cannot catch it because the re-import has deliberately reset the expected workbook snapshot.

B. Failed Manager syncs become terminal dead ends

sync_workbook() marks history rows sync_failed, while pending_history() selects only sync_status='pending'.

Reproduced result:

- Forced writer failure: one history row became sync_failed.
- The next generated sync batch contained zero operations.
- There is no retry/requeue operation.

A transient lock, package, or writer failure can therefore leave edits committed in SQLite but absent from the workbook, with no supported recovery path.

C. A normal Default Selection Rule edit is broken in the Manager UI

default_selection_rules carries model_key, but it is not marked model_scoped: workbook-manager/backend/app/specs.py:241.

The frontend only sends model_id for schema.model_scoped records. The backend then validates target_option_id against model "".

Reproduced by submitting an unchanged existing Stingray rule through the same backend path:

target_option_id='opt_719_001' does not resolve to options.option_id for model ''

So one of the advertised Model Operations collections cannot update valid existing records through its normal UI contract.

D. Parent/child edits cannot be staged atomically in the Manager

Each staging operation validates references against committed database rows rather than the proposed final batch state.

Reproduced:

1. Stage a new exclusive group.
2. Stage a member of that group.
3. The member is rejected because the newly staged group is not yet in the database.

This affects exclusive groups/members and other relational edits. The existing editor_ops batch validator handles final-state relationships more correctly. The Manager has regressed that behavior by inserting a weaker validator in front of it.

2. Workbook Manager critique

The Manager is a parallel domain implementation, not merely a new UI.

It independently owns:

- Workbook table specifications: workbook-manager/backend/app/specs.py
- Import and normalization: importer.py
- Reference and record validation: validation.py
- Staging semantics: staging.py
- SQLite persistence and history: db.py
- Workbook sync translation: sync.py

It eventually calls editor_ops.apply_batch, which is good, but that means there are now two validation systems. They already differ:

- Manager omits color_overrides.adds_rpo reference validation.
- Manager omits interiors.included_option_id reference validation.
- Manager omits model_interior_scope.requires_option_id reference validation.
- Manager cannot express the conditional reference in default_selection_rules.condition_id.
- Manager cannot express the conditional asset_map.target_type → target_id relationship.
- Invalid records can therefore enter SQLite and fail only at final sync, or remain stranded after a failed sync.

Its main Form Structure view is also materially broken. Browser verification showed every runtime step as “no sections mapped.” The backend associates sections using section_presentation.step_key, but the current workbook legitimately leaves those cells blank and relies on section_master.step_key. The existing editor has that fallback; the Manager does not.

The test suite is not catching these because it is primarily backend fixture testing:

- 28 tests passed.
- 2 slow live-gate tests were skipped by default.
- There are no frontend behavior tests.
- Browser smoke exposed failures the backend suite did not.

There is also a test-hygiene defect: the slow live-write test uses a temporary workbook but the production config.EDIT_LOG_PATH, which points at tracked form-output/workbook-edit-log.jsonl. The branch already contains a test-generated temporary-path audit entry. Running the advertised slow gate can dirty or contaminate the canonical audit log.

Recommendation: do not make the Manager an accepted canonical-workbook writer in its present form.

3. Existing Workbook Editor critique

The existing editor is crude, but its architecture is better aligned with the repository:

- It reads the current workbook directly.
- It derives registered model sheets from workbook metadata.
- It validates the entire proposed final state.
- Writes go through editor_ops.apply_batch and save_workbook_safely.
- It does not create a durable competing copy of workbook rows.

Problems:

A. Dead duplicate frontend

visualizer/workbook-editor/index.html:21 loads editor.js.

visualizer/workbook-editor/workbook-editor.js is an unreferenced 684-line React prototype with:

- React/lucide imports unavailable in the no-build editor.
- Hardcoded models.
- Hardcoded steps and sections.
- Hardcoded schemas and sheet mappings.

It is dead code and a stale alternate source of truth. Delete or archive it.

B. The embedded Ingest Review is now an obsolete competing workflow

The default editor visibly exposes an “Ingest Review” tab. In a normal launch it displays only:

No ingest evidence/candidate directories configured.

When configured, it points at historical candidate/interpretation/workbook-build artifacts rather than the current compiler/typed-exception workflow. This is exactly the overlap AGENTS.md now describes as historical/debug-only.

The tab should not be part of the normal editor navigation. It should either be removed or explicitly moved under a legacy evidence viewer.

C. The editor gate is currently red

The focused editor suite returned:

- 131 passed
- 7 subtests passed
- 3 failed

All three failures are stale real-workbook expectations in tests/test_editor_lints.py:

- Expected Z06 RWJ/WKS display-order collision no longer exists.
- Expected opt_cj2_001 comparison difference no longer exists.
- Expected opt_drz_001 pending-review difference no longer exists.

The same three failures occurred against both the branch workbook and the synthetic main workbook. They are not caused by the pending merge, but they prevent a clean merge claim.

D. Minor misleading state

The server still prints “Workbook editor (read-only)” even though the page and server now support gated writes.

4. Ingest Wizard critique

The new direction is basically correct:

- Narrow model selection.
- Canonical compiler.
- Typed exception queue.
- Workbook remains read-only during intake/review.
- Separate proof and write authority.

The implementation, however, has become an orchestration monolith:

- session.py: 5,429 lines, 108 functions, 15 functions over 100 lines.
- compiler.py: 4,423 lines; compile_canonical_rows() is 812 lines.
- plan_builder.py: 2,113 lines; its two primary builders are 856 and 910 lines.

That size is not just aesthetic. It is why old and current state machines are leaking into each other.

A. Current-plan navigation reaches a broken legacy screen

I resumed a current dry_run_approved run. The plan page exposed “Back to review.”

visualizer/ingest-wizard/wizard.js:2892 merely calls setStage("review"); it does not initialize the old review model state.

Browser result:

- Empty target-model selector.
- Empty decision-type selector.
- Button text: Copy 's finished decisions to
- An enabled “Mark decisions complete” control on this uninitialized screen.

This is a live broken pathway from a current run into a legacy state machine.

B. Production write approval is operationally hidden

approve_write() exists and is exposed through:

POST /api/wizard/sessions/<run>/write/approve

But there is no corresponding browser control or CLI command. scripts/ingest_wizard_apply.py --write consumes authority; it does not create it.

That may have been intended as a temporary safety boundary, but it means the production continuation path is not self-contained or discoverable. Operators must know and manually invoke an undocumented raw HTTP transition.

C. Legacy APIs remain writable

The server still exposes historical decisions, copy-decisions, complete, plan, and approval routes alongside the current compile/exception routes. Historical screens may be necessary for evidence, but they should be read-only. Current sessions should not be able to navigate into or mutate legacy workflow state.

5. Redundancy and ownership overlap

The overlap is currently:

Concern: Workbook schema/table knowledge
Workbook Editor: editor_ops.py
Workbook Manager: specs.py
Ingest Wizard: compiler/plan projection
────────────────────────────────────────
Concern: Reference validation
Workbook Editor: final-state batch validator
Workbook Manager: SQLite validator
Ingest Wizard: compiler and exception validation
────────────────────────────────────────
Concern: Pending changes
Workbook Editor: browser memory
Workbook Manager: SQLite staging/history
Ingest Wizard: run artifacts/plan operations
────────────────────────────────────────
Concern: Workbook operation generation
Workbook Editor: direct editor ops
Workbook Manager: history-to-editor-ops translation
Ingest Wizard: plan builder
────────────────────────────────────────
Concern: Review workflow
Workbook Editor: workbook sheets/lints + legacy ingest tab
Workbook Manager: staged change review
Ingest Wizard: compiler exceptions + legacy decisions
────────────────────────────────────────
Concern: Workbook writing
Workbook Editor: safe writer
Workbook Manager: safe writer via editor ops
Ingest Wizard: safe writer via approved plan
────────────────────────────────────────
Concern: Audit state
Workbook Editor: JSONL log
Workbook Manager: SQLite history plus JSONL
Ingest Wizard: run receipts and approvals

This is too many authorities. The workbook remains nominally canonical, but the Manager’s SQLite row store and the Wizard’s retained compatibility state each behave like alternate operational truth.

6. Recommended destination

Use one workbook domain engine, one change-set contract, and separate thin UIs.

Recommended architecture:

1. One declarative table registry

Consolidate editor_ops.py metadata and Manager specs.py into one registry owning:

- Table/sheet resolution.
- Keys and types.
- Enums.
- Model scoping.
- Union and conditional references.
- Delete dependencies.
- Writable versus read-only surfaces.

The editor, Manager frontend, importer, compiler projection, and tests should all consume this registry.

2. One final-state ChangeSet contract

Every writer should emit the same structure:

- Workbook SHA and mtime precondition.
- Row keys.
- Field-level deltas, not complete replacement rows.
- Provenance and operator.
- Warning acknowledgements.
- Final-state relationship validation.
- Preview/readback result.

editor_ops is the closest current implementation and should be evolved rather than bypassed.

3. SQLite as a journal, not a second workbook

If SQLite is retained:

- Store change sets and audit events.
- Treat imported rows as an explicitly disposable projection.
- Never allow re-import while any committed change set is unsynced.
- Detect conflicts at changed-field level.
- Provide retry/cancel/rebase for failed syncs.
- Do not consider a database commit successful workbook work.

4. Keep one editor UI

My recommendation is:

- Keep the existing editor as the trusted fallback until parity is proven.
- Retain the Manager React frontend as the likely destination.
- Remove its independent validation/write semantics and make it call the shared domain service.
- Retire the existing editor only after every writable collection and final-state relationship has parity tests.

5. Keep ingest separate and narrow

The standalone Ingest Wizard should own only:

- Raw source intake.
- Profiling and target selection.
- Canonical compilation.
- Typed exception resolution.
- Emission of a shared ChangeSet.

Remove the workbook-editor Ingest Review tab from the normal UI.

Make legacy ingest runs read-only archival views. Current sessions must never transition into historical review states.

6. Make post-write state explicit

Both editors currently stop at “workbook changed.” The UI should immediately report:

- Workbook synchronized.
- Generated artifacts stale.
- Registry publication pending.
- Exact next validation/generation gates.

Do not imply the customer application is updated merely because the workbook write succeeded.

7. Main-branch merge forecast

Branch size:

- 46 branch-only commits.
- 3 main-only commits.
- 160 changed files.
- 43,907 insertions and 779 deletions.
- 119 added files.

Direct conflicts detected:

- fable5loop/state/manifest.sha256
- form-output/workbook-edit-log.jsonl

For the workbook-edit log, keep main’s real audit entry and discard the branch’s temporary test-path entry.

The canonical workbook differs between branch and main, but only main changed it after the common base. Git should select main’s workbook without a textual conflict. The danger is operational:

- Any existing branch-side ingest plan approval or temporary-workbook proof is bound to the old workbook hash/mtime.
- Those approvals should become invalid and must be rebuilt after the merge.
- The ingest safety code appears designed to block this stale proof rather than silently reuse it.

What is likely to break after merge:

1. Workbook Manager users can hit the data-clobber, failed-sync, default-rule, atomic-parent/member, and empty-structure paths immediately.
2. README will advertise the Manager as a supported editor before those paths are safe.
3. The editor test gate remains red because of three stale workbook assertions.
4. Existing ingest approvals become stale by design.
5. The conflicting edit log can lose or contaminate audit history if resolved carelessly.
6. Running the Manager slow gate can modify the tracked edit log.
7. Current ingest plans can navigate into a broken legacy review page.
8. The large monolithic diff will be difficult to review as one merge and makes rollback unnecessarily broad.

What does not currently look likely to break:

- The customer runtime.
- Dealer submission behavior.
- Main’s newer Grand Sport 5ZV behavior.
- Workbook package/schema integrity.

I tested branch code against a synthetic main snapshot:

- Workbook Manager: 28 passed, 2 skipped.
- Current compiler/session/apply subset: 171 passed, 11 subtests passed.
- Metadata/promotion/schema/rule tests: 80 passed.
- Runtime tests: 66 passed.
- Main workbook package validation: valid.
- Main workbook schema validation: 0 errors, 0 warnings.

Current branch results included:

- Broad ingest suite: 381 passed, 18 subtests passed.
- Manager: 28 passed, 2 skipped.
- Manager frontend production build: passed.
- Current runtime subset: 65 passed.
- Current workbook package/schema validation: valid.
- Editor suite: 131 passed, 3 failed.

No live canonical-workbook write or dealer submission was performed. Repository status is clean.

8. Recommended merge sequence

Do not merge all 46 commits as one product release.

A. First merge candidate

- Shared editor_ops safety improvements.
- Canonical compiler and typed exception queue.
- Focused ingest tests and authority checks.
- Necessary promotion/model-config fixes.
- Resolve the three stale editor tests.
- Preserve main’s workbook, generated runtime artifacts, and edit log.

B. Hold back or disable

- Workbook Manager write/sync capability.
- README claim that the Manager is a supported canonical editor.
- Default workbook-editor Ingest Review tab.
- Current-to-legacy ingest navigation.
- Dead visualizer/workbook-editor/workbook-editor.js.

C. Second pass

Consolidate schema/change-set ownership, then restore the Manager behind parity and concurrency tests.

Bottom line: the ingest work is worth preserving, but the branch currently packages it with an unsafe second workbook authority and too much legacy
workflow surface. Merge the compiler and safety work selectively; do not merge the Manager as production-ready.

Correction to my earlier report: the two textual merge conflicts are:

    - fable5loop/STATE.md
    - form-output/workbook-edit-log.jsonl

    I previously named fable5loop/state/manifest.sha256; that was incorrect.

    Additional high-severity findings:

    1. Shared writer has a time-of-check/time-of-use race

    scripts/corvette_form_generator/editor_ops.py:1474-1479 validates the batch’s workbook mtime. It then performs potentially lengthy scratch-copy, package, bool-hygiene, and schema validation.

    Before writing, it reopens the current workbook and captures a new mtime at editor_ops.py:1607-1617. That new mtime—not the reviewed batch mtime—is passed to save_workbook_safely().

    Consequently, an external edit made during validation can become the new write base, and the previously reviewed operations can be applied to that changed workbook.

    This qualifies my earlier description of the existing editor as trustworthy: its architecture is still better than the Manager’s, but this race must be fixed before treating any interactive writer as fully safe.

    2. Failed post-write verification does not roll back

    After save_workbook_safely() changes the live workbook, editor_ops.py:1618-1627 performs readback verification. If that verification fails:

    - The function returns apply_verification_failed.
    - It reports the backup path.
    - It does not restore the backup.
    - The workbook remains changed despite a failure response.

    The Manager then marks the history sync_failed at workbook-manager/backend/app/sync.py:114-123, whose comment incorrectly claims the failed write left the workbook untouched.

    This is a dangerous state-reporting error: the database says failed/unsynced while the workbook may already contain the edit.

    3. Two ordinary Manager edits to one row can become unsyncable

    Manager history emits every committed snapshot as a separate full-row update: workbook-manager/backend/app/sync.py:33-69.

    The shared writer rejects contradictory sequential updates to the same fields. A temporary-database probe produced:

    - First edit committed.
    - Second edit committed.
    - Sync batch contained two updates.
    - editor_ops rejected the batch as contradictory.
    - No operations were prepared.

    So a user can edit one option, commit it, edit the same option again before syncing, and permanently strand both edits.

    4. Failed re-import can erase the Manager’s normalized database

    Importer.run() clears imported tables at workbook-manager/backend/app/importer.py:87-103 before proving the replacement import succeeds. clear_imported_data() commits those deletes immediately at db.py:140-145.

    A delegated fault probe:

    - Imported a valid workbook.
    - Attempted to re-import a workbook missing a required sheet.
    - Import raised KeyError.
    - Options table went from 1,154 rows to 0.

    The canonical workbook remains intact, but the Manager database is left empty or inconsistent. Re-import must be transactional or built into a replacement database and atomically swapped only after validation.

    5. The Manager in this branch is already superseded by another branch

    The repository contains codex/workbook-relational-db, which is 28 commits ahead and 5 behind the current branch, with:

    - 48 changed files.
    - 20,713 insertions.
    - 2,582 deletions.

    That follow-on work removes the current backend/app/specs.py approach and introduces a canonical catalog/compiler/migration architecture with broader focused tests.

    Therefore, merging this branch’s Stage-1 Manager would place an older implementation on main immediately before replacing most of it.

    Updated recommendation:

    - Do not merge this branch’s workbook-manager/ subtree as a supported feature.
    - Review and integrate codex/workbook-relational-db separately.
    - Before enabling any writer, fix and test:
      1. The editor_ops.apply_batch() mtime race.
      2. Automatic rollback after post-write verification failure.
      3. Sequential same-row Manager edits.
      4. Transactional re-import.
      5. Failed-sync retry/rebase/cancel.
    - Omit the dead visualizer/workbook-editor/workbook-editor.js; it contains an unreachable direct wb.save(WORKBOOK_PATH) path that bypasses all workbook safety gates.

    The rest of the original audit stands, but the writer-safety risk is higher than initially reported.
