# Pass 6B Independent Verifier Report

## Verdict

PASS after two evidence-backed repair checkpoints. The verifier ran in a separate read-only context and edited no files.

## Cycle 1 — FAIL

The initial review passed exact stored-artifact loading, pre-writer durability, active-attempt uniqueness, terminal replay, startup recovery, manual resolution, schema migration, natural projection staleness, and protected boundaries. It found four blockers:

1. Proven-unchanged non-transient exceptions mapped to unknown instead of `apply_rejected`.
2. A dictionary merely claiming restored state could gain retry authority without a complete, exactly bound formal receipt.
3. A minimal identity dictionary could be accepted as an applied receipt without operation coverage, exact readback, schema, or Boolean-hygiene proof.
4. Mapping tests sampled representative rows instead of the complete Section 4.1 vocabulary.

It also found one stale README sentence saying no manager apply action called the writer.

## Cycle 2 — FAIL, narrow

The first repair closed the four original blockers and expanded the mapping/exception matrix. Re-verification found one nested-proof hole: missing counters compared equal as `None == None`. It also found that a malformed dictionary carrying only the receipt schema string was labeled `formal_receipt` even when formal validation rejected it.

## Cycle 3 — PASS

The final correction requires positive integer `rawCount`, `rawCovered`, `preparedCount`, `preparedChecked`, and verification `preparedCount`; coverage and readback counts must agree. The empty-counter near-miss is rejected, and only a complete exactly bound formal receipt receives `artifact_kind=formal_receipt`. Focused regressions exercise both corrections, and `git diff --check` passes.

## Criteria

1. PASS — the focused RED was observed before implementation and is summarized in `validation-output.txt` with its provenance limitation.
2. PASS — manager apply loads the exact stored ChangeSet, formal preview, and formal approval and invokes only the shared service.
3. PASS — schema 8 owns one finalizable-then-immutable apply envelope plus immutable manual resolution evidence.
4. PASS — `applying` and the unique active attempt commit before the writer; active and terminal replay cannot duplicate mutation.
5. PASS — every Section 4.1 result and exception identity branch maps explicitly and malformed near-misses fail closed.
6. PASS — retry authority is limited to the exact retryable states and restored retry requires a complete bound receipt; cancellation preserves history.
7. PASS — startup converts interrupted apply to unknown without replay; restored/applied/abandoned manual resolutions preserve evidence.
8. PASS — a saved workbook naturally makes the existing identity comparison stale; no parallel freshness state was added.
9. PASS — schema 8 upgrades preserve prior approval evidence and add the new objects idempotently without a projection schema bump.
10. PASS WITH BASELINE EXCEPTION — focused and shared gates pass and protected boundaries are clean. The sole broad-inventory failure reproduces identically at unchanged HEAD and is recorded separately.

## Evidence inspected

- `workbook-manager/backend/app/db.py`
- `workbook-manager/backend/app/drafts.py`
- `tests/test_workbook_manager_changeset_lifecycle.py`
- `workbook-manager/README.md`
- Pass 6B and Sections 4/4.1 of the owning specification
- Current diff and protected-surface status

## Validation Output Inspected

The verifier directly ran the lifecycle file during cycle 1 (`32 passed` plus
`25 subtests`) and inspected the focused RED/GREEN and broader command results
retained in `validation-output.txt`. Later cycles intentionally reran only cheap
focused checks and `git diff --check`, not the 13-minute inventory.

## Required Fixes Before Pass

None.

## Durable Lesson Candidates

Outcome-mapping tests should enumerate the authoritative vocabulary and malformed near-misses. Schema labels alone do not confer artifact authority; exact identity, complete structure, and positive proof counts do. This is task-specific confirmation of existing fail-closed guidance, so no skill update is required.

## File Edit Statement

The independent verifier edited no repository files.
