# Reliable Workbook–Database Workflow

Status: instructional specification; implementation not started.
Recommended implementation reasoning: high.

## Objective

Make the Workbook Manager a reliable interface around `stingray_master.xlsx`.

The workbook remains canonical. SQLite is a disposable, verified projection plus a durable journal of proposed changes. The database must never become an independent source of Corvette product behavior.

This work changes workflow reliability only. It must not change workbook product data, generated form contracts, customer-facing form behavior, runtime publication, or dealer submission.

Standing source-of-truth, workbook-safety, validation, and handoff requirements in `AGENTS.md` apply. This spec adds only the workflow-specific direction below.

## Current Diagnosis

The current workflow is not safe to use for canonical workbook writes:

1. Re-import clears and commits the active database before the replacement import is validated. A malformed workbook copy reduced the imported option count from 1,380 to 0.
2. Import errors are recorded but still promoted. A workbook copy missing `model_master` produced 2,332 errors while still becoming the active database snapshot with 0 models and 1,380 options.
3. Committed unsynced edits survive re-import as old full-row snapshots. A later sync can overwrite unrelated workbook edits made after the original commit.
4. Validation checks individual changes against committed database rows rather than the proposed final batch. Valid parent/member additions cannot be staged together, while dependency confirmation can bypass an invalid final graph.
5. Sequential edits to one row become contradictory sync operations instead of one base-to-final change.
6. Failed sync rows move out of the pending queue without a retry, requeue, or cancel path.
7. The manager duplicates workbook schema semantics already owned by the shared workbook-domain registry. The copies disagree on references, conditional references, enums, and types.
8. Unknown model ownership can be committed to SQLite and then skipped during sync because no workbook sheet resolves.
9. Sync review is bound to workbook mtime but not workbook content hash.
10. The API can race while opening its shared SQLite connection, and the current UI loses model context on some model-key tables.

The existing workbook-congruent relational design described a larger destination but was not implemented. Its fixed model assumptions are also stale. This specification replaces it as the active implementation direction.

## Required Workflow

### 1. Contain unsafe operations

Until the later requirements are complete:

- prevent live workbook sync through the manager;
- prevent re-import when staged or committed-unsynced work exists;
- keep read-only browsing and disposable comparison/export functions available where they are already safe;
- present the manager as provisional rather than current or synchronized.

### 2. Use one workbook contract

Use the existing shared workbook-domain registry as the writable family/key/type/enum/reference authority.

The database, API, browser controls, validation, and sync translation must consume that contract rather than maintain a second handwritten copy. Extend the shared contract only where database mapping or lineage genuinely needs additional metadata.

Model sets must be derived from current workbook metadata. Known, editable/importable, generatable, and runtime-published models are separate sets; none should be hardcoded from an old snapshot.

### 3. Import through a verified candidate

A workbook import must:

1. Read and profile the workbook without changing the active database.
2. Build a separate candidate database.
3. Record source sheet, source row, physical key, and mapping lineage for imported rows.
4. Fail closed on missing required structure, duplicate or blank keys, unresolved or ambiguous references, unproved model ownership, and incomplete mappings.
5. Reconcile every source row as imported or explicitly excluded with a reason.
6. Run relational integrity and current generated-contract parity checks in isolation.
7. Replace the active database atomically only after every required check passes.

A failed candidate must leave the last verified database unchanged.

### 4. Journal field-level changes

Replace full-row history as sync authority with a ChangeSet journal.

Each change must carry:

- the reviewed workbook SHA-256 and mtime;
- workbook family, model context, and physical row key;
- field-level original and proposed values;
- source lineage;
- validation status and sync status.

Before commit, apply all staged changes to one projected final state and validate that graph. Parent/member additions, coordinated deletes, references, uniqueness, and model ownership must be evaluated together.

Sequential edits to one physical row must coalesce into one original-to-final operation. If the workbook changes externally, unrelated fields may be rebased; a field changed both externally and in the ChangeSet must block for explicit resolution.

### 5. Make sync recoverable

Sync must use the exact reviewed ChangeSet and workbook identity.

Required behavior:

- dry-run first;
- verify workbook SHA-256, mtime, and ChangeSet identity immediately before write;
- write only through the shared workbook service and safe-save path;
- read back the exact affected rows;
- restore and verify the backup after any save or readback failure, including exceptions;
- mark only proven operations synchronized;
- support retry, requeue, and cancel for failed work;
- make retries idempotent.

The UI must distinguish database projection current, changes staged, workbook synchronized, and generated/runtime artifacts current. A successful workbook save must not imply runtime publication is current.

### 6. Keep the API and browser thin

The API should expose logical workbook families and model context, not caller-supplied SQL table names. Database connections must have a controlled lifecycle that is safe under concurrent requests.

The browser must preserve model context for every model-owned row and render the reference metadata supplied by the shared contract. Existing workbook rows should be editable without changing their meaning merely by passing through the UI.

Do not add product-rule logic to the API, database, or browser.

## Implementation Approach

Implement in small vertical slices. Do not begin by reorganizing the repository or creating the full file layout from the older design.

For each slice:

1. Locate the current owner and callers in the live repository.
2. Add a failing disposable test for the reproduced workflow defect.
3. Make the smallest change through the existing service boundaries.
4. Run the focused test and the relevant existing workbook-manager gates.
5. Confirm the canonical workbook and generated/runtime surfaces are unchanged.

Recommended slice order:

1. Containment and regression tests.
2. Shared contract adoption and model-lifecycle derivation.
3. Candidate import and atomic promotion.
4. Projected final-state ChangeSet validation and conflict detection.
5. Recoverable sync and post-save restoration.
6. API connection lifecycle and browser model-context repair.
7. End-to-end temporary-workbook verification and documentation update.

## Acceptance Evidence

Implementation is complete only when disposable tests prove all of the following:

- malformed import preserves the prior database byte-for-byte;
- an import with blocking findings is not promoted;
- committed unsynced work blocks re-import or rebases without overwriting unrelated external edits;
- sequential same-row edits produce one valid sync operation;
- parent/member additions and coordinated deletes validate as one final graph;
- invalid references accepted by an old manager-only schema cannot commit;
- unknown model ownership cannot stage or commit;
- failed sync work remains visible and retryable;
- workbook content drift with unchanged mtime is rejected;
- every post-save exception restores and verifies the backup;
- concurrent first-load API requests do not lock or fail;
- real unchanged model-owned workbook rows can round-trip through the browser/API shape;
- database import and sync do not alter generated contracts or form behavior.

Run the relevant commands from the README validation table. Use copied workbooks, temporary databases, isolated generated-output roots, and no live dealer submission.

## Scope and Companion Impact

Expected implementation surfaces are the current workbook-manager import, database, validation, staging/journal, sync, API, browser, and focused test owners discovered at implementation time.

Companion handling:

- Workbook source data: unchanged.
- Generated artifacts and runtime registry: inspected for no change, not regenerated into the tracked tree as implementation output.
- Customer form and dealer submission: unchanged.
- Shared workbook-domain registry: reused; extended only for missing generic contract metadata.
- Workbook Manager documentation and this specification: updated when implementation closes.
- Superseded relational design/plan: historical reference only.

## Non-Goals

- Changing option availability, pricing, defaults, relationships, copy, ordering, or any other product behavior.
- Editing workbook rows to make the database implementation easier.
- Making SQLite canonical.
- Reorganizing code solely to match a proposed directory structure.
- Runtime promotion, deployment, or dealer-submission changes.

## Completion Handoff

Follow `AGENTS.md` handoff requirements. In addition, report the candidate-import result, ChangeSet conflict/retry probes, exact temporary-workbook sync result, and proof that workbook data and generated form behavior remained unchanged.
