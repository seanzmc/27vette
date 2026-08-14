# Pass 6A Outcome Rubric — Shared-Writer Post-Save Restoration

Started: 2026-08-09T23:45:00-04:00
Owning specification: `docs/superpowers/specs/2026-07-22-reliable-workbook-database-workflow.md`

## Task summary

- **Goal:** Complete Pass 6A as one bounded checkpoint: make the shared writer restore and SHA-256-verify its backup after every returned or thrown failure from live readback, live package/schema verification, and write-log completion.
- **Changed surface:** `editor_ops.py`, its focused shared-writer tests, owning workflow documentation, and Fable closeout artifacts.
- **Source-of-truth decision:** `editor_ops.apply_batch()` remains the sole physical workbook-write/recovery owner. No manager wrapper or second write path is introduced.
- **Protected boundaries:** No canonical workbook write; no manager apply state/API/UI; no shared ChangeSet artifact change; no generated artifact, publication, customer runtime, dealer, deployment, dependency, commit, or push change.
- **Pattern:** TDD plus independent adversarial verification; maximum three maker/verifier cycles.

## Required outcome criteria

1. Focused fault-injection regressions fail against pre-Pass-6A production behavior before implementation.
2. Once `save_workbook_safely()` returns a backup, live exact-row readback, package validation, schema validation, write-log completion, and success-result construction share one exception restoration boundary.
3. Returned live readback and schema failures restore the backup and return failure evidence rather than reporting success.
4. Thrown live readback, package, schema, and log exceptions restore the backup rather than escaping or leaving a saved workbook.
5. `workbookState="restored"` is returned only after the restored live workbook SHA-256 exactly equals the backup SHA-256.
6. A thrown restore or failed hash proof returns `workbookState="unknown"` and `status="workbook_restore_failed"`.
7. Every failure result preserves the original phase, kind, and detail; restoration evidence separately preserves attempted/verified state, both hashes when available, and restoration error detail.
8. Existing successful applies, returned-readback rollback status, stale refusal, warning policy, exact readback, backup creation, and log output remain compatible.
9. Focused shared-writer/service tests, the complete documented manager inventory, explicit slow copied-workbook writer inventory, frontend build, workbook package/schema gates, and diff checks pass.
10. Canonical workbook, tracked generated artifacts, registry publication, customer runtime, dealer submission, deployment, and dependencies remain unchanged.
11. The owning specification, root and manager README guidance, fixed STATE handoff, and complete run receipt agree that Pass 6A is complete and Pass 6B is next.
12. An independent verifier returns PASS from the final diff and retained execution evidence.

## Stop condition

Stop after Pass 6A is independently verified. Durable manager apply attempts, idempotency, startup recovery/manual resolution, API/browser reachability, and final write enablement remain Passes 6B–7.

## Outcome

Completed: 2026-08-10T01:08:33-04:00

All twelve criteria are satisfied. The first independent verifier cycle found
two contract defects; both were repaired through a second RED/GREEN cycle, and
the independent re-verifier returned PASS with no new blocker. The complete
named acceptance inventory, slow copied-workbook writer inventory, shared
writer/service tests, frontend build, workbook package/schema gates, and
protected-surface/diff checks passed. Pass 6B is next; no manager apply route or
live workbook-write authority was enabled.
