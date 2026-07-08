# Pass B.9 — Review continuity / blocker UX · Outcome rubric

Date: 2026-07-07. Approved scope: Sean's Pass B.9 message (this session): Standard
Equipment lane price exclusion, richer review filters, actionable blocker panel.
No workbook writes, no generated artifacts, no Pass D changes.

## Measurable done criteria

1. **SE lane price exclusion.** `review_queue(model, "standard_equipment")`
   returns zero candidates carrying joined price rows or a `listPrice` — the
   lane keeps only true standard / ref-only / non-priced rows. Fixture proof:
   a priced orderable assigned to a standard-behavior section stays OUT of the
   SE queue; an unpriced orderable assigned the same way and ref-only standard
   rows stay IN.
2. **Decision-state filter on all per-candidate lanes.** The UI shows the
   Needs-decision / Already-decided filter for section, price, copy_split,
   status_nuance, and standard_equipment; server filtering proven by test on
   standard_equipment (decided/undecided partitions correctly).
3. **Price-presence filter.** New `pricePresence` review filter (`priced` /
   `unpriced`) implemented server-side (fail-closed on invalid value) and
   surfaced in the UI for the Standard Equipment lane. Test proves priced vs
   unpriced partition on fixture data.
4. **Workbook-reference filter.** New `workbookRef` review filter
   (`in_workbook` / `new`) matches candidates whose RPO (orderable or
   ref-only) exists in the live workbook option reference; surfaced for
   per-candidate lanes. Test proves both directions on fixture data (PDB/XFR
   in workbook; CC3/C2Z/CC2/AJ7 new).
5. **Section-assigned filter.** New `sectionState` review filter (`assigned` /
   `unassigned`) on non-section per-candidate lanes, keyed on approved
   `assign_section` decisions. Test proves both directions.
6. **Actionable blocker panel.** Progress blockers carry row identity
   (rpo/description/sheet) from the server; the review stage renders a
   blocker panel whenever the current model has blockers (not only after a
   failed mark-complete); each blocker entry jumps to the right model + lane
   (+ RPO search for candidate blockers, models stage for
   variant_reconciliation); saving a decision refreshes progress so resolved
   blockers disappear (refreshReview refetches progress on every save).
7. **Protected boundaries.** No writes to `stingray_master.xlsx`,
   `form-output/` tracked artifacts, `form-app/data.js`, dealer submission.
   Workbook-untouched regression test still green.
8. **Gates.** Wizard suites green: `tests/test_ingest_wizard_decisions.py`,
   `tests/test_ingest_wizard_session.py`, `tests/test_ingest_wizard_plan.py`,
   `tests/test_ingest_wizard_profiler.py` (plus fixtures import). Loop
   validator green after receipt.
9. **Browser proof.** Real-export session driven to the review stage: blocker
   panel visible with live counts, at least one blocker link followed to its
   lane/row, at least one new filter exercised, screenshot captured.

## Non-goals

Workbook apply (Pass D), plan-surface expansion (Pass C.1), new lanes, copy
engine changes, dealer submission, generated artifacts.
