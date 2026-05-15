# Mobile Responsiveness UX Spec

> Spec only. Do not implement in this pass. Improve the generated static order-form app so narrow mobile views feel like a simple step-by-step configurator instead of a stacked desktop page with long informational sections.

## Diagnosis

The app already has a mobile breakpoint, but it mostly stacks the existing desktop regions. On phones, the user starts in the current choice panel, then encounters the full step rail and full order summary below it. That creates a long page where progress, pricing, selected items, open requirements, and standard equipment compete with the current task.

Evidence:

- `form-app/index.html` defines the app as three sibling workspace regions: `step-rail`, `choice-panel`, and `summary-panel`.
- `form-app/styles.css` uses a three-column desktop grid for `.workspace`, then collapses it at `760px` into a single column while ordering `.choice-panel`, `.step-rail`, and `.summary-panel`.
- `form-app/app.js` renders all steps as full labeled `.step-link` buttons in `renderStepRail()`.
- `form-app/app.js` renders long option descriptions in every choice card through `renderChoiceCard()`, `renderInteriorCard()`, and `renderContextCard()`.
- `form-app/app.js` renders grouped `Standard & Included` content in both the trim step and the sidebar summary through `renderStandardEquipmentGroups()`, `renderTrimStandardEquipment()`, and `renderStandardEquipment()`.
- `form-app/app.js` renders the sidebar selected/auto/missing lists on every update in `renderSummary()`.

Root cause: mobile layout is structurally responsive but not interaction-responsive. It preserves every desktop information surface in-page instead of prioritizing the next action and hiding secondary content behind compact controls.

Risk level: medium. The desired fix touches layout, generated runtime markup, and regression expectations, but it should not change workbook data, pricing, rules, validation, exports, or selection behavior.

Change type: mixed UI behavior and styling. It changes mobile presentation and disclosure behavior only; it should preserve the underlying configurator logic.

## Goals

1. Make the mobile first viewport answer three questions quickly: what am I configuring, what step am I on, and what should I choose next?
2. Keep only one primary decision surface visible at a time on mobile.
3. Keep price and required-action status visible without forcing the user through the full summary.
4. Collapse long informational sections by default, especially standard/included equipment.
5. Preserve desktop layout and current business behavior.

## Exact Files To Change

### `form-app/index.html`

Add small mobile-only shell targets inside `.workspace` or near it:

- A compact progress region for current step / total steps / previous-next controls.
- A compact summary trigger or inline bar showing total MSRP and open requirement count.
- Optional mobile drawer/backdrop markup if the summary is exposed as a drawer rather than an in-flow disclosure.

Do not remove the existing desktop `nav.step-rail`, `section.choice-panel`, or `aside.summary-panel`; reuse them where practical and hide/reposition with CSS.

### `form-app/app.js`

Add mobile presentation helpers around the existing render flow:

- Extend the element cache with the new mobile progress/summary targets.
- Add a helper such as `currentStepSummary()` to compute current index, total steps, previous step, and next step from `runtimeSteps` and `state.activeStep`.
- Add `renderMobileProgress()` called from `render()` after `renderStepRail()` and `renderStepContent()`.
- Add `renderMobileSummaryBar()` called from `renderSummary()` so mobile has compact pricing and open-requirement status without reading the full summary cards.
- Add event handlers for mobile previous/next and summary expand/collapse controls.
- Add a mobile-specific collapsed mode for informational sections:
  - `renderTrimStandardEquipment()` should render a closed disclosure by default on mobile-sized layouts.
  - `renderStandardEquipment()` should remain collapsed by default and avoid expanding nested groups automatically.
  - Long descriptions in choice cards should remain present in the DOM but be visually clamped or placed inside a disclosure on small screens.

Do not change:

- `handleChoice()`, `handleInterior()`, `handleContextChoice()`, rule reconciliation, pricing calculations, or export shape.
- Workbook-generated data contracts.
- The step order, body-style step, trim-level step, customer-info step, or summary/export behavior.

### `form-app/styles.css`

Replace the current narrow breakpoint behavior with a mobile-specific interaction layout:

- At `max-width: 760px`, make `.workspace` a single-column guided flow with the current choice content first.
- Hide the full vertical `.step-rail` behind a compact progress control or horizontal step scroller. If a scroller is used, only the active step and nearby steps should be visually prominent.
- Move the full `.summary-panel` out of the default reading path on mobile:
  - Preferred: make it a closed disclosure/drawer opened from a compact summary bar.
  - Acceptable smaller slice: render the summary after choices but collapse each card by default except totals/open requirements.
- Make `.choice-grid` and `.interior-choice-grid` one column below mobile width, with stable touch targets and no horizontal overflow.
- Reduce card padding and typography only enough to improve scanability; do not make tap targets smaller than 44px.
- Clamp long `.choice-note`, `.disabled-reason`, `.auto-reason`, and standard-equipment descriptions on mobile, with accessible expansion available where needed.
- Make `.topbar` actions wrap predictably:
  - Model picker gets full width or first row.
  - Reset is secondary.
  - Download/Submit remain easy to find but disabled-state titles are not relied on for mobile explanation.
- Keep `.vehicle-bar` compact, preferably a three-item grid or two-row summary, instead of three tall stacked blocks.
- Ensure modal forms keep existing scroll behavior but use mobile-safe padding and full-width buttons.

### `tests/stingray-form-regression.test.mjs`

Add focused markup/regression assertions that do not require a real browser:

- New mobile progress/summary container IDs exist in `index.html`.
- Runtime exposes/render calls update the mobile progress text or button state for first, middle, and final steps.
- Compact summary still reflects base, options, total, and missing-required state from `renderSummary()`.
- Existing export, submission, standard-equipment, and selection assertions continue to pass.

If browser verification is added separately, do not replace these unit-level guards; use browser checks as visual validation only.

## Constraints

- Preserve current desktop UX unless a desktop change is required to share markup safely.
- Preserve all configurator behavior: selections, auto-add rules, disabled rules, price rules, missing-required validation, customer capture, download build, and dealer submission.
- Preserve the workbook as the source of truth. Do not move business rules into responsive UI code.
- Do not add dependencies or a build step; the app must remain static and runnable from `form-app/index.html`.
- Do not regenerate workbook data unless implementation accidentally changes generated artifacts and must be reconciled.
- Keep standard/included equipment variant-scoped and grouped, but stop letting it dominate the mobile path.
- Use minimum code. No broad redesign, no framework migration, no new routing.

## Proposed Implementation Plan

1. Add mobile shell markup in `form-app/index.html`.
2. Add render helpers in `form-app/app.js` for mobile progress and compact summary state.
3. Add mobile disclosure behavior for long informational sections, starting with standard/included equipment.
4. Update `form-app/styles.css` so mobile shows:
   - compact topbar,
   - compact vehicle context,
   - mobile progress/summary controls,
   - current choices,
   - deferred navigation and summary details.
5. Add focused regression tests in `tests/stingray-form-regression.test.mjs`.
6. Manually verify real mobile widths after tests pass.

## Risks And Mitigations

- Risk: hiding the full step rail could make non-linear navigation harder.
  Mitigation: keep full step access available through a compact progress control or horizontal scroller; preserve `state.activeStep` navigation.

- Risk: collapsing standard/included equipment may hide useful context for trim decisions.
  Mitigation: show a concise count and current trim label, with one tap to expand grouped details.

- Risk: clamping descriptions may hide rule/availability context.
  Mitigation: keep disabled and auto-added reasons visible enough to explain why a card cannot be selected; only clamp secondary informational descriptions.

- Risk: mobile-only behavior could drift from desktop tests.
  Mitigation: keep underlying render functions shared and add regression assertions for the new mobile containers.

## Non-Goals

- No workbook schema changes.
- No changes to option compatibility, pricing, rules, standard-equipment derivation, or exports.
- No model-specific hardcoded business logic.
- No replacement of the static app architecture.
- No visual brand redesign beyond responsive layout and information hierarchy.

## Validation Plan

Required automated gates:

```sh
node --test tests/stingray-form-regression.test.mjs
```

If generated data is touched, also run the project-approved generator flow:

```sh
.venv/bin/python scripts/generate_stingray_form.py
node --test tests/stingray-form-regression.test.mjs
```

Manual verification:

- Open `form-app/index.html` or serve `form-app/` locally.
- Check widths at 320px, 375px, 390px, 430px, 760px, and desktop.
- Smoke path: Body Style -> Trim Level -> Exterior Paint.
- Confirm no horizontal overflow.
- Confirm current step and next action are obvious without scrolling past summary/standard-equipment content.
- Confirm total MSRP and open requirements are visible in compact mobile summary.
- Confirm Standard & Included remains available but collapsed by default on mobile.
- Confirm desktop still shows the existing three-region workspace.

## Approval Gate

Implementation should wait for approval. If approved, implement as one focused UI pass touching only:

- `form-app/index.html`
- `form-app/app.js`
- `form-app/styles.css`
- `tests/stingray-form-regression.test.mjs`

