# Pass 6B Outcome Rubric — Durable Manager Apply

## Task summary

- Goal: Complete Pass 6B as one bounded backend checkpoint: durable exact-artifact apply, replay protection, startup recovery, cancellation, and manual resolution.
- Changed surface: Workbook Manager durable schema and backend lifecycle, focused tests, owning specification, operational handoff, and receipt evidence.
- Source of truth: `workbook_domain.service.apply_changeset()` remains the only workbook writer; `WBM_DB` owns immutable manager attempt and recovery evidence.
- Protected boundaries: No canonical workbook mutation during validation, no generated/publication/runtime/dealer change, and no API or browser apply reachability. Pass 7 owns enablement.
- Expected files: `workbook-manager/backend/app/db.py`, `workbook-manager/backend/app/drafts.py`, `tests/test_workbook_manager_changeset_lifecycle.py`, the owning specification, `fable5loop/STATE.md`, and this receipt.

## Required outcome criteria

1. A focused regression fails before implementation for the missing durable apply lifecycle.
2. Apply loads the exact stored ChangeSet, formal preview, and formal approval and invokes only `workbook_domain.service.apply_changeset()`.
3. One immutable apply-attempt owner records identity bindings, timing, exact result or exception evidence, independently observed workbook identity, manager state, and allowed verbs.
4. `approved -> applying` plus the unique active attempt commits before the writer; active and terminal replay cannot duplicate workbook mutation.
5. Every Section 4.1 apply result maps through an explicit fail-closed allowlist; only an exact verified saved receipt reaches `applied`.
6. Exact retry is limited to `apply_retryable` and `apply_restored_retryable`; cancellation preserves attempt history.
7. Startup converts orphaned `applying` attempts to `workbook_state_unknown` without replay; manual resolution durably records restored, applied, or abandoned-unknown evidence.
8. A successful write naturally makes the existing workbook/projection identity stale; no parallel freshness flag or second manager readback is added.
9. Durable schema upgrade preserves prior lifecycle evidence and creates the Pass 6B objects idempotently.
10. Focused lifecycle/schema/shared-service gates pass; protected workbook, generated, runtime, publication, dealer, dependency, and API/UI surfaces remain unchanged.

## Stop condition

Stop after Pass 6B is verified and documented. Do not begin Pass 7 or make apply reachable through FastAPI/browser code.
