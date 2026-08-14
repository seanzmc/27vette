# Pass 5 Checkpoint 3 Outcome Rubric — Durable Preview Lifecycle

Started: 2026-08-09

## Task summary

- **Goal:** Complete Pass 5 requirement 6 as one bounded checkpoint: preview an emitted immutable ChangeSet only through the shared workbook-domain service, persist exact immutable result/attempt evidence, and map the service outcome to the specified manager lifecycle.
- **Changed surface:** Workbook Manager backend schema/service/API, focused tests, owning workflow documentation, and Fable closeout artifacts.
- **Source-of-truth decision:** `stingray_master.xlsx` remains canonical; the emitted `workbook-changeset-1` remains immutable; `workbook_domain.service.preview_changeset()` exclusively owns preview validation; `WBM_DB` owns manager lifecycle and immutable attempt evidence.
- **Protected boundaries:** No live workbook write; no projection mutation; no generated artifact or registry publication; no browser workflow enablement; no approval/apply implementation; no add/delete implementation; no dealer, deployment, dependency, commit, or push change.
- **Expected files:** `workbook-manager/backend/app/db.py`, `workbook-manager/backend/app/drafts.py`, `workbook-manager/backend/app/main.py`, `tests/test_workbook_manager_changeset_lifecycle.py`, `workbook-manager/README.md`, the owning specification, `fable5loop/STATE.md`, and this receipt folder.
- **Pattern:** TDD plus adversarial verification, maximum three maker/verifier cycles.

## Required outcome criteria

1. A failing lifecycle regression is observed before production implementation.
2. Preview is refused unless the projection is `current`, and the shared service is not called on refusal.
3. A `changeset_emitted` draft loads its exact persisted ChangeSet and calls `workbook_domain.service.preview_changeset()` without reproducing workbook validation logic.
4. Every service-returned dictionary is persisted byte-for-semantically exact inside one immutable manager attempt envelope, classified as formal preview artifact versus early refusal, and mapped exactly through specification §4.1.
5. A service exception persists its class/message and independently measured workbook identity evidence; unchanged identity maps only allowlisted transient read exceptions to `preview_retryable`, other exceptions to `preview_rejected`, and unprovable/mismatched identity to `stale`.
6. Attempt IDs, start/completion timestamps, ChangeSet identity, resulting manager state, and exact allowed verbs are durable; attempt update/delete is refused by the database.
7. Retry is accepted only from `preview_retryable`, reuses the immutable ChangeSet, and creates a distinct attempt. Other non-previewable states fail closed without invoking the shared service.
8. The API exposes only this preview step and does not approve, apply, mutate the projection, or write the workbook.
9. Schema migration preserves existing durable drafts/ChangeSets and a verified version-3 projection across restart.
10. Focused lifecycle, draft, concurrency, and shared ChangeSet/service gates pass; protected workbook/generated/runtime surfaces remain unchanged.
11. The owning specification records requirement 6 and checkpoint evidence; Workbook Manager guidance, fixed `STATE.md` handoff, and a complete run receipt agree without duplicating detailed progress.
12. An independent verifier returns PASS from final artifacts and validation evidence.

## Stop condition

Stop after requirement 6 is independently verified. Requirements 7–8, approval, coordinated add/delete behavior, removal of the legacy dependency-confirmation bypass, apply/write hardening, and UI enablement remain later checkpoints/passes.
