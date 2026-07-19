# Independent Verifier Report · Form Mobile UX Consistency

Date: 2026-07-18
Verifier: independent subagent (did not author the change; all evidence reproduced first-hand)
Worktree: `/Users/seandm/Projects/27vette/.claude/worktrees/form-mobile-styling-bugs-31955c`
Rubric: `fable5loop/runs/2026-07-18-form-mobile-ux-consistency/outcome.md` (7 criteria)
Browser target: http://localhost:4173 (static form-app server), Browser pane tab `seed`

(Format note: sections below reorganized post-verdict by the maker to match the loop validator's required headings; all evidence, wording, and the verdict are the verifier's own.)

## Verdict

VERDICT: PASS — all seven rubric criteria reproduced and confirmed with first-hand evidence. One non-blocking advisory (real-input scroll leg, see Advisories).

## Criteria

1. Tooltip scroll fix — PASS
2. In-flow header — PASS
3. Always-visible total — PASS
4. Action relocation (mobile only) — PASS
5. Single sticky Next — PASS
6. Gates green, no generated churn — PASS
7. Dealer boundary preserved — PASS

## Evidence inspected

- Inspected `git diff` of `form-app/app.js`, `form-app/index.html`, `form-app/styles.css`, `tests/stingray-form-regression.test.mjs` (172 insertions, 108 deletions across 4 files; no other tracked files modified).
- Re-ran both mapped gates myself.
- Browser verification at 375×812 (mobile preset), 1280 (desktop preset), and 768×1024 (tablet preset) using DOM state and computed styles via `javascript_tool`, plus a screenshot at mobile width.

## Criterion 1 — Tooltip scroll fix: PASS

Diff evidence (`form-app/app.js`): a capture-phase passive `document.addEventListener("scroll", …, { capture: true, passive: true })` handler calls `closeTooltips()` unless the scroll target is inside a `.tooltip-panel`; a `window.addEventListener("resize", () => closeTooltips())` companion was added. Regression test now asserts both listeners exist in source.

Browser evidence at 375×812, paint step (10 `.info-tooltip` triggers):
- Clicked first trigger: `{openTriggers: 1, openPanels: 1, panelPosition: "fixed", panelDataOpen: "true"}` — floating viewport panel open.
- Dispatched `document.dispatchEvent(new Event('scroll'))` (target = document, exactly the event a real page scroll delivers to the capture listener): `{openTriggers: 0, openPanels: 0, detachedFixedPanels: 0}` — `is-open` removed, `data-open` cleared, no fixed panel remains.
- Screenshot before scroll confirmed the open panel ("Touch-Up Paint Number WA-9567") anchored to its trigger card.

Advisory (environment, not app): real-input verification was not possible in this automation pane — the `computer` scroll action timed out twice without moving the page, and programmatic `window.scrollTo(0,200)` moved `scrollY` to 200 but did not dispatch a scroll event (known pane limitation stated in the task brief). The synthetic document-level dispatch exercises the identical registered listener path a real user scroll takes.

## Criterion 2 — In-flow header: PASS

At 375×812 (fresh page load):
- `#openStepDrawerButton` computed `position: "static"`, rect `{t:15, l:16, w:44, h:44}` — in-flow, 16px left gutter.
- `.topbar` computed `padding: "12px 16px 14px"` (no 52px band), `display: grid`, `grid-template-columns: "44px 137.812px 137.188px"`.
- Row 1 = hamburger (left) + summary pill (rect `{t:15, l:222, w:137, h:44}`, right edge 359 = 375−16 gutter); row 2 = `.brand-block` (rect `{t:71, l:16, w:343}`, spanning `grid-column: 1 / -1`).
- `document.documentElement.scrollWidth` = 375 (no horizontal overflow).
- Regression test now asserts `position: static`, absence of `position: absolute` and `padding: 52px` in the mobile breakpoint.

## Criterion 3 — Always-visible total: PASS

At 375×812: `#mobileSummaryButton` renders in the topbar (`display: flex` computed from `inline-flex`), top at 15px — visible without scrolling; `#mobileSummaryTotal` showed the live total (`$73,495` base build; updates via `renderSummary`); `aria-controls="summaryDrawer"`; clicking it set `.app-shell[data-mobile-drawer="summary"]` (drawer opened). Symmetric affordance confirmed visually in the screenshot: 44px round hamburger left, pill right, same row.

## Criterion 4 — Action relocation (mobile only): PASS

Mobile (375×812):
- `.toolbar` computed `display: "none"` (header toolbar hidden).
- Summary drawer open: `#summaryActionsCard` visible (`display: grid`) with `#summaryResetButton` (enabled), `#summaryDownloadButton` (disabled), `#summarySubmitButton` (disabled) — exact disabled-state parity with the hidden header buttons (`resetButton: false, downloadBuildButton: true, submitDealerButton: true` at the same moment). After completing required selections both drawer Download/Submit flipped to enabled.
- Final step (`delivery`): footer buttons `["Reset Build", "Download Build [disabled]", "Submit to Dealer [disabled]"]` — all three sticky actions present with gating intact.

Desktop 1280: `.toolbar` visible (`display: flex`), all three header buttons visible, `#summaryActionsCard` `display: "none"`, mobile pill hidden.
Tablet 768: same — toolbar visible, all three header buttons visible, `#summaryActionsCard` `display: "none"`, pill `display: "none"`.

## Criterion 5 — Single sticky Next: PASS

Full walk at 375×812 clicking only visible `.step-footer [data-next-step]` buttons, starting at Vehicle Setup stage 1:

| # | step (stage) | visible footers | footer button | inline Continue visible | #mobileNextStep visible |
|---|---|---|---|---|---|
| 1 | model (Model) | 1 | Next: Body Style | 0 | false |
| 2 | model (Body Style) | 1 | Next: Trim Level | 0 | false |
| 3 | model (Trim) | 1 | Next: Exterior Paint | 0 | false |
| 4–12 | paint → accessories | 1 each | Next: <next step label> | 0 | false |
| 13 | delivery | 1 | Reset/Download/Submit (no Next) | 0 | false |

Footer computed `position: "sticky"`. Exactly one primary forward control per step; the walk reached `delivery` via footer clicks only. Desktop 1280: `.vehicle-setup-next-action` ("Continue to …") present and visible (count 1), `.setup-step-footer` present but `display: "none"` — the in-panel action is preserved ≥761px.

## Criterion 6 — Gates green, no generated churn: PASS

## Validation Output Inspected

`fable5loop/runs/2026-07-18-form-mobile-ux-consistency/validation-output.txt` reviewed and its numbers independently reproduced below (89/89, 47/47, three-file `form-app` diff, no generated churn).

Commands run by me:
- `node --test tests/stingray-form-regression.test.mjs` → **89 pass, 0 fail** (duration ~2.5s).
- `node --test tests/multi-model-runtime-switching.test.mjs` → **47 pass, 0 fail** (duration ~2.6s).
- `git status --porcelain -- form-output form-app` after the runs →
  ```
   M form-app/app.js
   M form-app/index.html
   M form-app/styles.css
  ```
  Only the three intended runtime files; `form-app/data.js` untouched; `form-output/` clean.

## Criterion 7 — Dealer boundary preserved: PASS

Browser (375×812, required selections completed: paint `opt_g8g_001`, interior `1LT_AQ9_HTA` via step-rail navigation + card clicks; `#summarySubmitButton.disabled` flipped to false):
- Opened summary drawer (`#mobileSummaryButton`) → `data-mobile-drawer="summary"`; clicked `#summarySubmitButton` → drawer closed first (`data-mobile-drawer` cleared to null), `#dealerSubmitModal` visible (`display: grid`, `visibility: visible`, `position: fixed`, full-viewport 375×812, `hidden: false`).
- Fields present: `#dealerSubmitName`, `#dealerSubmitEmail`, `#dealerSubmitPhone`, `#dealerSubmitComments`, and `#dealerTurnstile` mount — all true.
- `#dealerSubmitCloseButton` click → modal `display: none`, `hidden: true`.

Diff evidence: `git diff form-app/app.js | grep -iE "turnstile|endpoint|payload|fetch|dealerSubmitForm|workers|api"` matched only one unchanged context line (`dealerSubmitForm: …` in the `els` block). The dealer-related additions are entry-point wiring only: three new `els` entries for the summary-drawer buttons and click bindings that call the existing `requestResetBuild` / `downloadBuild` / `openDealerSubmitModal` handlers (drawer closed first for Reset/Submit). No payload, endpoint, validation, or Turnstile code changed.

## Required Fixes Before Pass

None — all criteria passed on the first cycle.

## Durable Lesson Candidates

- Automation-pane scroll limitation: programmatic scrolls (`window.scrollTo`/`scrollBy`) move `scrollY` without dispatching scroll events in the in-app Browser pane, so scroll-listener behavior must be verified with real input or a synthetic `scroll` dispatch on `document`. (Adopted into the compounding skill by the maker.)

## File Edit Statement

The verifier edited only this report file. No source, test, spec, or receipt files were modified by the verifier; gates were re-run read-only and `git status` confirmed the working tree matched the maker's declared four-file diff before and after.

## Advisories (non-blocking)

1. Real-input scroll could not be delivered by the automation pane (computer-tool scroll timed out; programmatic scroll does not dispatch scroll events here). Criterion 1 is evidenced by the diff plus a synthetic document-level scroll dispatch, which exercises the identical listener path. A quick manual thumb-scroll check on a real device would close this last gap.
2. `renderStepContent` now falls through to `renderFinalStepActions()` for any non-vehicle-setup step with no `next` — same behavior as before, just restructured ternary; confirmed correct on the `delivery` step.

## Verdict

All seven rubric criteria reproduced and confirmed with first-hand evidence.

VERDICT: PASS
