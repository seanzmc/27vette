# Outcome rubric · 2026-07-06 · Pass B.3 — checkpoint-2 field-note refinements

Source: Sean's 2026-07-06 review-session notes (11 findings). Changed surface: wizard tooling/UI/tests; workbook stays read-only.

Criteria (graded per finding):

1. Section dropdown provenance visible in UI ("from workbook section_master") — and answered in handoff.
2. Redundant "Select all filtered"/"Clear selection" bulk buttons removed; header checkbox owns select-all.
3. Copy bar reworded to a sentence a human parses ("Copy <model>'s decisions into <current>"), overwrite relabeled ("replace decisions already made here") default off; helper line explains it's for mirroring between the ingest's own targets.
4. Price lane: price-state filter (single match / multiple prices / no price) + one-click "Accept all N single-price matches (filtered)" that needs no row-checking; still batch-undoable.
5. Exclusive groups built from a candidate pool picker (searchable checklist of in-scope options, section shown per option), not typed RPO strings; banner notes options in single-select sections rarely need exclusive groups (section selection_mode surfaced).
6. Copy split is marker-aware: numbered in-cell disclosure lines (e.g. "1. Requires …") are matched to the row's status markers (A1/S2…) and split into disclosure automatically; unmatched markers still flag; flagged-exception count drops materially on the real export (record before/after numbers).
7. Status-nuance rows show exactly what needs confirming: per-flagged-status chips with plain-language interpretation (raw symbol → parsed meaning + why flagged); lane help rewritten.
8. Duplicate lane = in-file RPO collisions only: groups candidates whose RPO appears on >1 source sheet within the model scope, shown together, one decision per RPO group; empty when no collisions; workbook comparison stays in the reference line, not this lane.
9. Standard-equipment lane = rows without an orderable RPO plus rows whose decided section is a standard-behavior section (`section_master.standard_behavior`); orderable candidates no longer stranded there.
10. Deferrals lane pre-seeds concrete suggested items per model (interior scope, color overrides, asset images) with one-click record; explanation of purpose (named open items carried into the Pass C plan report).
11. Presentation lane shows friendly sheet names + one-line purpose each ("Form steps", "Section display", …) and explains the hard go-live requirement.

Plus: all wizard + editor suites green; browser proof on real export for findings 4, 5, 6, 8, 9; boundaries preserved; verifier PASS; loop closeout.
