# Form Mobile UX Consistency Spec

Status: IMPLEMENTED 2026-07-18, independent verifier PASS (1 cycle) — see `fable5loop/runs/2026-07-18-form-mobile-ux-consistency/`. Changes uncommitted on `claude/form-mobile-styling-bugs-31955c` pending Sean's device check + push direction. Approved 2026-07-18 by Sean — implement all. Resolved decisions: (1) desktop header stays as-is, action relocation is mobile-only (≤760px); (2) mobile Next = bottom sticky footer only, top progress row shows step counter + Back.
Date: 2026-07-18
Branch: `claude/form-mobile-styling-bugs-31955c`

## Diagnosis (current-state evidence)

All five reported issues reproduced/verified at 375×812 against the live form-app served locally.

1. **Tooltip detaches on scroll (bug).** `positionTooltip()` (`form-app/app.js:446-485`) promotes mobile/summary tooltips to `document.body` with `position: fixed` (`.tooltip-panel[data-floating="viewport"]`, `form-app/styles.css:2019`) and computes coordinates once at open. No scroll or resize listener closes or repositions the panel. Browser proof: with a tooltip open, `window.scrollBy(0,150)` moved the trigger 396→246 while the panel stayed at 422 — panel floats over unrelated content.
2. **Hamburger placement/spacing.** Mobile topbar reserves a 52px top band (`padding: 52px 16px 16px`, `styles.css:2376`) and `.mobile-drawer-button` is absolutely positioned into it (`top: 14px; left: 16px`, `styles.css:2484-2521`). The button floats alone above the brand block, visually outside the form card even though it opens the step drawer (step counter/list). The dead space to its right is unused.
3. **Build summary tile inconsistency.** `.mobile-summary-bar` (`index.html:58-65`, `styles.css:2406`) is a large tile between the header and the step progress row. It opens the same right-hand summary drawer as the desktop "Build Summary" toolbar button, but with a completely different affordance than the hamburger (icon button, left drawer) — two drawer patterns activated two different ways, plus the tile consumes a full row of prime viewport.
4. **Toolbar actions crowd the header.** Reset/Download/Submit occupy a `44px 44px 1fr` grid row in the mobile header (`styles.css:2533-2566`). Submit is disabled most of the session (until required selections complete), so the header's widest control is dead weight during the whole flow. Final step already renders sticky Download/Submit copies (`renderFinalStepActions`, `app.js:2523-2534`) — browser-verified on the `delivery` step.
5. **Sticky Next inconsistency.** Option/context steps render a sticky bottom `step-footer` Next button on mobile (`styles.css:2842-2856`); the Vehicle Setup step suppresses it (`next && !isVehicleSetupStep`, `app.js:2669-2675`) and relies on the top progress-row Next plus an inline "Continue to …" button buried in the highlight panel. Users get a bottom Next on some steps and not others.

Risk level: medium (customer-facing runtime + styling, no data contracts). Change class: mixed styling + runtime-presentation JS + static HTML; no workbook, generator, or generated-artifact changes.

## Proposed changes

### A. Tooltip scroll fix (bug fix)
- In `bindTooltips`/tooltip module (`form-app/app.js`): add a capture-phase, passive `scroll` listener (window + scrollable ancestors via capture on `document`) and a `resize` listener that close any open floating tooltip (`closeTooltips()`). Closing (not live-repositioning) is the simplest correct behavior and matches native tooltip conventions.

### B. Mobile header consolidation
- Replace the absolute-positioned hamburger + 52px padding band with a single in-flow header row: hamburger, brand block, and a compact build-summary control aligned on one grid row (`.topbar` mobile rules, `styles.css` ≤760px block).
- Hamburger keeps `aria-controls="stepRailDrawer"`; same drawer behavior, just laid out in-flow with consistent 16px gutters.

### C. Build summary access unification
- Convert `.mobile-summary-bar` from a full-width tile into a compact right-aligned header control (total + chevron) mirroring the hamburger's weight on the left — two symmetric drawer affordances: left = steps, right = summary.
- Same `#summaryDrawer` drawer, same aria wiring; running total stays always visible in the header (goal: key info visible without hunting).

### D. Relocate Reset / Download / Submit into the summary drawer
- Remove the three-button toolbar row from the mobile header. Add a `summary-actions` block inside `#summaryDrawer` (top or bottom of the drawer) hosting Reset, Download Build, Submit to Dealer — identical handlers/ids preserved via delegation or moved bindings; on desktop ≥1121px the drawer is the docked right sidebar, so the actions live in the right shelf there too (per Sean's direction).
- Keep the existing final-step sticky Download/Submit copies; add Reset alongside them on the final step for symmetry ("copies of the buttons on the last step").
- **Dealer-submission boundary:** button *location* only. Modal, payload, Turnstile, validation, disabled-until-complete gating all untouched. Sean's request is the explicit approval trigger for relocating the submit entry point; confirm on spec approval.

### E. Consistent sticky Next
- Render the sticky bottom `step-footer` Next on **all** steps including Vehicle Setup stages (Model → Body Style → Trim → next step), wired to the existing stage-advance logic (`goToNextStep` already stage-aware).
- Keep the top mobile-progress row for step counter + Back; remove its duplicate Next (single source of forward navigation at the thumb) — OR keep both if Sean prefers; default proposal: bottom-only Next, top row shows progress + Back.
- The inline "Continue to …" button inside the vehicle-setup highlight panel is removed to avoid a third Next variant.

## Files expected to change
- `form-app/app.js` (tooltip listeners; step-footer rendering incl. vehicle setup; final-step Reset; summary-drawer action bindings)
- `form-app/styles.css` (mobile header grid, summary control, drawer actions, step-footer)
- `form-app/index.html` (toolbar/markup restructure, summary drawer actions block)
- `tests/stingray-form-regression.test.mjs` (re-anchor toolbar/mobile-summary/step-footer assertions to the new markup — mapped gate must move with the UI in the same pass)
- Run receipt under `fable5loop/runs/2026-07-18-form-mobile-ux-consistency/`; `fable5loop/STATE.md` closeout update.

## Source-of-truth decision
Runtime presentation (HTML/CSS/JS) only. No workbook, generator, `form-output/`, or `form-app/data.js` changes. Dealer submission logic untouched (UI entry-point relocation only).

## Companion-file impact
- `tests/stingray-form-regression.test.mjs`: updated (see above).
- `tests/multi-model-runtime-switching.test.mjs`: inspect; expected no-change (no stage/model logic touched) — verify.
- Workbook/generated artifacts: n/a.
- Docs: none identified; verify no doc references the toolbar layout.

## Constraints
- No unrelated refactors; no new dependencies; generated files not source; dealer boundaries preserved; stable element ids (`#resetButton`, `#downloadBuildButton`, `#submitDealerButton`, `#openSummaryDrawerButton`, drawers) preserved where tests/aria depend on them.

## Risks / non-goals
- Risk: regression-test re-anchoring churn (known repo pattern; mapped gates updated in-pass, not skipped).
- Risk: desktop ≥1121px docked sidebar gains action buttons — verify no layout overflow; desktop header loses its toolbar (intentional per direction D; flag if Sean wants desktop header unchanged — **open question 1**).
- Open question 2: E proposes bottom-only Next on mobile (top row = progress + Back). Confirm or keep both.
- Non-goals: no visual retheme, no step reordering, no summary-content changes, no dealer modal/payload changes, no model-switch changes.

## Validation plan
- `node --test tests/stingray-form-regression.test.mjs` (re-anchored) + full node gate set for stingray; pytest metadata gates if touched surfaces demand (expected: not).
- Browser verification at 375×812, 768×1024, 1280×800: tooltip open→scroll stays attached-or-closed; drawer open/close both sides; Next flow through all 12 steps incl. Vehicle Setup stages; final-step Reset/Download/Submit; submit modal opens with Turnstile intact; totals correct after reset.
- Gate-churn check: `git status -- form-output form-app` after any gate run; restore timestamp-only churn.
- Independent verifier subagent against the outcome rubric below.

## Outcome rubric (gradable done-state)
1. Open tooltip + scroll 150px: panel either tracks trigger or closes; never floats detached (JS rect assertion + browser proof).
2. No absolutely-positioned header controls at ≤760px; hamburger, brand, summary control share in-flow rows with uniform 16px gutters (computed-style proof).
3. Build total visible in viewport at all times at 375×812 without scrolling (header control).
4. Reset/Download/Submit reachable from summary drawer on mobile AND docked sidebar on desktop; absent from mobile header row; final step shows all three sticky.
5. Every step (incl. all three Vehicle Setup stages) shows exactly one primary Next affordance, sticky at bottom on mobile.
6. All mapped gates green; dealer modal behavior unchanged (open, fields, Turnstile mount, cancel).
