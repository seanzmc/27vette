# Outcome Rubric — 2026-07-06 Pass B.4: second field-notes round (16 findings)

Sean's second real review session produced 16 numbered findings; several block him from
reaching stage 6 at all. This pass fixes the blockers and usability gaps, and answers the
five findings that are questions, not defects. Same boundaries as all wizard passes: the
canonical workbook stays read-only, tracked `form-output/`/`form-app/` untouched, stored
decision vocabulary unchanged (labels are a language layer).

## Reproduced facts (2026-07-06, real export + live workbook)

- Finding 2 does NOT reproduce on current code: reference-model dropdowns populate with
  grand_sport/stingray/z06 in the browser (dev server 8041). Sean's 8040 server ran stale code.
- Finding 4 root cause: only Equipment Groups sheets carry section-label rows
  ('Additional Options', 'Equipment Groups'); Exterior/Interior/Mechanical sheets have zero
  `sectionLabel` values → the filter is nearly useless as built.
- Finding 3 confirmed: GSX reconciliation card says "disagrees … (mandatory decision)" with
  zero action buttons; the required decision lives un-discoverably in the relationship lane.
- Finding 9 confirmed as the section-lane blocker: `collectRowDecision` throws
  "Pick a section first." even when resolution is Skip; completeness also still demands a
  price decision for skipped rows.
- Finding 16 confirmed: 6 GSX ref-only rows carry 'available' statuses (R9L, CFX, TR7, DRG,
  XFR, BC7) inside the standard-equipment queue; BC7 is S on some models and A on others, so
  the filter must read model-scoped statuses only.
- Finding 14 shape confirmed: comma rule diverges from current names on 233 GSX rows; LPO
  rows read "LPO, <name>, <detail…>"; FA5-class rows ("Trim, interior, …") produce one-word
  generic names; several proposals collide ("Seats" ×3, "Seat belt color" ×5) — collision and
  one-word names are the exception flags Sean asked for.

## Criteria (all measurable; verifier reproduces)

1. **Skip unblocks (F9):** a section-lane decision with resolution `not_needed` saves without
   a section, and a candidate whose section decision is skip is exempt from the price and
   status-nuance completeness requirements. Test: fixture model completes with one skipped
   candidate carrying no price decision; UI saves skip without a section pick.
2. **Reconciliation actionable (F2/F3):** the reconciliation panel shows, for a disagreeing
   model, action buttons that record the mandatory `variant_reconciliation` decision
   (accept-export-variants or flag-for-business-call) and then show the decided state; a
   model with no workbook scaffold is framed as "new model — confirm the export's variants",
   not as an error. Reference-model dropdown shows friendly labels. Test: server
   reconciliation payload carries `workbookHasScaffold` + `decision`; browser click records
   the decision and the GSX blocker clears.
3. **Source-group filter has content (F4):** the review filter offers a source group for
   every candidate (section label where present, sheet name otherwise); filtering by each
   returns a non-empty queue on real data. Test: fixture + real-data check that the dropdown
   is non-empty on all per-candidate lanes and both label kinds filter correctly.
4. **Filter layout (F5, F1):** review controls regrouped — summary, then filters, then a
   visually separated actions row; the stage-3 header says it is a read-only audit step.
   Browser-verified (screenshot in receipt).
5. **Reference bulk-assign (F6):** section lane has "Use <reference>'s section for N checked"
   which assigns each checked row its own workbook-reference section, skips rows without
   one, reports the skip count, and lands in one undoable batch. Auto-assigned rows remain
   editable per row. Test: server-level decisions land per-row correct; fixture UI path.
6. **Inactive / not-selectable capture (F7):** section-lane rows can mark an option
   display-only (`selectable=false`) and/or inactive (`active=false`); the flags persist in
   the decision payload and the plan's option row carries them. Test: plan_builder consumes
   both flags.
7. **Comma-rule splitter (F14):** `propose_copy_split` names = text before the first comma of
   the first body line; LPO rows use the segment between the first and second comma; leading
   "NEW!" markers are stripped; numbered-disclosure peeling and marker matching unchanged
   (still 100% marker reconciliation on the real export); one-word generic names and
   in-scope duplicate proposals are flagged for the exception queue. Tests: LPO, plain,
   FA5-class flag, NEW! strip, marker-match regression, duplicate-name annotation.
8. **SE lane correctness (F16/F15):** ref-only rows with any model-scoped 'available' status
   are excluded from the standard-equipment queue (R9L/CFX/TR7/DRG/XFR excluded for GSX;
   BC7 stays only where its own model's statuses are S); lane copy explains leave-out vs
   skip and that nothing is ever deleted from the workbook. Test: fixture row with A status
   excluded; model-scoped statuses proven by a mixed S/A fixture row.
9. **Group decisions editable (F12):** recorded relationship / exclusive / deferral /
   duplicate decisions each have a working Clear (delete + audit log); exclusive lane lists
   the pick-one sections by name (F11); "needs product decision" copy explains itself (F13).
10. **No regressions:** full wizard/plan/extension suites green; live workbook byte-identical
    after all proofs; tracked form-output/form-app clean; stored decision values unchanged
    (only additive payload keys); Pass C plan flow still builds/approves on fixtures.

## Answers owed in the handoff (no code)

- F1: stage 3 is read-only — yes (audit of the parse; now stated in the UI).
- F8: notes live in decisions.json (`reviewerNote`), shown on recorded decisions, the holds
  report, and the plan's holds list; never written to the workbook.
- F10: reviewed $ overrides the discovered price in the plan (`set_reviewed_price`).
- F13: "needs product decision" = records a business question instead of a rule; it lands in
  the plan report, not the workbook.
- F15: "Leave out" (SE lane action) = this row won't be written as an option row; "Skip —
  don't carry over" (resolution) = same effect recorded as a reviewed no; neither deletes
  anything from the workbook.
