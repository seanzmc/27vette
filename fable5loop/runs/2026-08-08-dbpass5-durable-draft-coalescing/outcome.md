# Pass 5 Checkpoint 1 Outcome Rubric — Durable Draft Coalescing

Started: 2026-08-08T18:53:27-04:00
Owning specification: `docs/superpowers/specs/2026-07-22-reliable-workbook-database-workflow.md`

## Task summary

- **Goal:** Establish the first Pass 5 vertical slice: manager-owned durable draft intent that coalesces sequential edits by physical workbook row without mutating the disposable projection.
- **Changed surface:** Workbook Manager backend schema/service, focused tests, owning workflow documentation, and Fable closeout artifacts.
- **Source-of-truth decision:** `stingray_master.xlsx` remains canonical; the verified projection supplies original semantic rows and lineage; `WBM_DB` owns mutable draft intent only.
- **Protected boundaries:** No canonical workbook write, generated-artifact refresh, registry publication, customer-runtime change, deployment, or dealer-submission change. The legacy full-row tables remain recovery evidence and cannot become ChangeSet/write authority.
- **Expected files:** `workbook-manager/backend/app/db.py`, a focused backend draft owner, focused manager tests, the owning specification, `workbook-manager/README.md` if operator-visible status changes, `fable5loop/STATE.md`, and this receipt folder.

## Required outcome criteria

1. A versioned durable draft schema exists in `WBM_DB` and does not exist in the disposable projection.
2. Draft creation fails closed unless the caller proves the verified projection state is `current`.
3. Source sheet, physical key, model ownership, and original projection row are resolved before draft persistence; an empty target sheet cannot be stored.
4. Two updates to the same `(draft, source sheet, family, physical key)` persist one mutable operation with the first original row and latest final row.
5. Update storage records only changed field pairs; reverting all fields to the original removes the no-op operation.
6. The projection row remains unchanged throughout draft editing.
7. Legacy `pending_changes` and `change_history` remain readable recovery/history surfaces and are not written by the new draft path.
8. Focused tests are observed failing for the missing behavior before production edits, then pass after the minimal implementation.
9. Relevant manager checkpoint tests and the Fable loop validator pass; protected workbook/generated/published files remain unchanged.
10. An independent verifier grades the final diff and tool evidence against this rubric without editing files.

## Stop condition

Stop at this checkpoint after criteria 1–10 pass. ChangeSet emission, complete final-graph preview, approval, coordinated delete/add handling, and UI thin-client migration remain later Pass 5 slices in the owning specification; live workbook writes remain disabled through Pass 7.

## Result

**PASS pending independent verification.** Criteria 1–9 are implemented and
covered by the focused and checkpoint acceptance evidence in
`validation-output.txt`. Criterion 10 is satisfied only when
`verifier-report.md` records an independent PASS; until then this checkpoint is
not closed.
