# Pass B.9 — Review continuity / blocker UX

Status: approved by Sean 2026-07-07 (chat message enumerating scope); implemented same day.

Follow-up: Sean's 2026-07-07 field test found the live blocker panel useful but
too visually persistent. The panel is now a collapsible `<details>` element and
remembers collapsed/open state across review refreshes while decisions are being
saved.

Sean's testing friction after B.5–B.8: the Standard Equipment lane still showed
priced rows, the review filters were too thin to work a big lane down, and
blockers only surfaced as an error string after pressing "Mark decisions
complete" — with no way to jump to the offending row.

## Scope

1. **Standard Equipment lane exclusions** (`session.py review_queue`)
   - Exclude any candidate carrying joined price rows or a `listPrice` —
     priced rows are options (or price problems), never standard equipment.
   - The lane keeps: ref-only rows not available-to-order on the model's own
     variant columns, plus reviewer-assigned standard-behavior-section rows —
     both now additionally required to be unpriced.

2. **Richer review filters** (server `review_queue` params + review-stage UI)
   - `decisionState` (`undecided` / `decided`): UI now offered on all
     per-candidate lanes (section, price, copy_split, status_nuance,
     standard_equipment). Server logic unchanged (already lane-generic).
   - `pricePresence` (`priced` / `unpriced`): new; UI on Standard Equipment.
     `priced` = candidate has ≥1 joined price row or a `listPrice`.
   - `workbookRef` (`in_workbook` / `new`): new; UI on per-candidate lanes.
     Matches the candidate's RPO (orderable or ref-only) against the live
     workbook option reference index.
   - `sectionState` (`assigned` / `unassigned`): new; UI on per-candidate
     lanes except section. `assigned` = approved `assign_section` decision.
   - All new params fail closed on unknown values (WizardError).

3. **Actionable blocker panel** (decisions.py `completeness` + wizard.js)
   - `completeness()` blockers now carry row identity for candidate blockers:
     `rpo`, `description` (first line), `sheetName`.
   - The review stage renders a blocker panel whenever the selected model has
     blockers — not only after a failed mark-complete. Grouped by lane +
     reason with a "Review these" jump (sets lane + Needs-decision filter),
     per-row RPO chips (jump = lane + RPO search), presentation-sheet chips
     (jump = presentation lane), and a variant-reconciliation jump to the
     models stage. Other selected models with blockers get a switch link.
   - Every decision save already refetches progress (`refreshReview`), so a
     resolved blocker disappears without further action.
   - 2026-07-07 follow-up: the panel can be collapsed/expanded so it does not
     dominate the review layout while working through a lane.

## Non-goals

No workbook writes, no generated artifacts, no Pass C plan-surface changes,
no Pass D. Stored decision vocabulary unchanged.

## Validation

- New/updated tests in `tests/test_ingest_wizard_decisions.py` (SE price
  exclusion, each new filter both directions + fail-closed, blocker identity
  fields); fixture gains a standard-behavior section and the lane-feeds
  section-list assertion updated.
- Wizard suites: decisions, session, plan, profiler.
- Browser proof on the real 2027 export: blocker panel live, links followed,
  filters exercised (receipt: `fable5loop/runs/2026-07-07-pass-b9-blocker-ux/`).
