# Vehicle Setup Progressive Disclosure Spec

## User feedback

The first Vehicle Setup pass reduced page turns, but it over-corrected into a dense first screen. The user likes the consolidation direction, but the current page presents too much at once, repeats `1LT / 2LT / 3LT` too many times, and keeps the standard/selected-RPO sidebar visually present too early. The desired direction is paced, smoother, modern, sleek, and simple: fewer hard page turns, less effort, but not all information shouting at once.

## Diagnosis

Root cause: the first approved pass collapsed Model, Body Style, and Trim Level into one visible page by rendering all three choice groups simultaneously in `renderVehicleSetupContent()`. That removed the choppy full-page step turns, but also removed the original pacing benefit. The always-visible right summary/standard equipment rail compounds the first-screen overload, and the setup copy repeats body/trim availability too aggressively.

Evidence inspected:
- Branch/status: `hermes/hermes-62195f2e`, clean before this spec.
- `form-app/app.js`
  - `modelStep` now labels the first runtime step as `Vehicle Setup`.
  - `vehicleSetupStepKeys` and `visibleRuntimeSteps()` skip `body_style` and `trim_level` as standalone rail pages.
  - `renderVehicleSetupContent()` renders Model, Body Style, and Trim Level all at once.
  - `renderVehicleSetupGroup()` and `renderContextCard(..., { setup: true })` drive the setup cards.
  - `setMobileDrawer()`, `openSummaryDrawerButton`, `mobileSummaryButton`, and `summary-panel` already support drawer behavior at narrower breakpoints.
- `form-app/styles.css`
  - `.vehicle-setup-*` styles control the dense setup layout.
  - `.summary-panel` becomes off-canvas only at `max-width: 1120px`; desktop still shows the heavy summary panel.
  - `.mobile-summary-bar` only appears at mobile widths, and the current opener icon treatment is not obvious enough for all breakpoints.

Risk level: medium runtime UX risk. This is runtime-only presentation/navigation behavior, but it affects the first customer interaction and summary-panel access across breakpoints.

Change type: runtime-only UX/presentation plus tests. No workbook/data/generator changes.

## Proposed UX direction

Keep one visible top-level step named `Vehicle Setup`, but turn it into a guided setup card rather than a three-section wall.

### 1. Progressive setup inside the same step

Within `Vehicle Setup`, show only one primary decision panel at a time:

1. Model
2. Body Style
3. Trim Level

The user stays on Step 1 in the rail. Instead of full page turns, the content area transitions between subpanels with a short fade/slide animation.

Recommended behavior:
- Initial state: Model panel open.
- After selecting a model, reveal/advance to Body Style.
- After selecting a body style, reveal/advance to Trim Level.
- After selecting trim, show a clean ready state with CTA: `Continue to Exterior Paint`.
- Previously completed subchoices collapse into compact chips, e.g. `Stingray`, `Coupe`, `1LT`, with `Change` buttons.
- Do not auto-jump to Exterior Paint on trim selection; make the final CTA intentional.
- Preserve keyboard/mouse access: collapsed chips/buttons can reopen any setup subpanel.

This keeps pacing without bringing back rail/page churn.

### 2. Reduce repeated trim/body text

Remove the repeated phrases that currently stack in the user's face:
- Model cards should not repeat `Coupe / Convertible | 1LT / 2LT / 3LT` prominently.
- Body cards should not say `Available with 1LT, 2LT, 3LT` when all visible models currently share those trims.
- Trim cards should not repeat full variant names like `Corvette Stingray Coupe 1LT` on every card.

Suggested replacement copy:
- Model card:
  - Title: `Stingray` or `Grand Sport`
  - Small note: one short descriptor if available, otherwise no note.
- Body card:
  - Title: `Coupe` / `Convertible`
  - Price: starting MSRP for the selected model/body.
  - Small note: `Removable roof panel` / `Power retractable hardtop` only if we can use generic copy without adding business-rule risk; otherwise omit.
- Trim card:
  - Title: `1LT`, `2LT`, `3LT`
  - Price: selected body/model MSRP.
  - Optional one-line label from existing tooltip/detail, but avoid full variant display name.
  - Keep full trim explanation behind the info tooltip.

### 3. Make the summary sidebar callable at all breakpoints

The heavy right `Order summary` rail should not be fully visible by default on desktop during early setup.

Use existing drawer machinery, but extend it to all breakpoints:
- Hide/collapse `.summary-panel` by default at desktop, tablet, and mobile.
- Add an obvious labelled opener, not just an icon:
  - `View Build Summary`
  - Secondary text/badge: current total or `Open requirements` count.
- Keep existing summary content and behavior inside the drawer.
- Use a slide-in transition from the right with backdrop.
- Keep close button and Escape/backdrop close behavior.
- Make sure `Submit to Dealer`, download, RPO lists, open requirements, and standard/included summary remain unchanged when the drawer is open.

### 4. Keep a lightweight inline setup summary

Replace the sense of “everything at once” with a compact current-build strip inside the setup card:

`Current setup: Stingray • Coupe • 1LT • $73,495`

This gives orientation without showing the full selected-RPO/sidebar content.

### 5. Motion style

Use subtle motion only:
- Fade/slide between setup subpanels.
- Respect `prefers-reduced-motion: reduce`.
- No new dependencies.
- No complex animation framework.

## Exact files to change

Runtime:
- `form-app/app.js`
  - Add vehicle setup substep state, e.g. `state.vehicleSetupStage` or a small helper that derives the active setup panel.
  - Update `renderVehicleSetupContent()` to render progressive subpanels instead of all groups fully expanded.
  - Add handlers for setup-stage advance/change buttons.
  - Simplify setup-specific card copy to reduce trim/body repetition.
  - Reuse/extend `setMobileDrawer("summary")` for all breakpoints.
  - Update topbar summary opener label/contents if needed.

Styles:
- `form-app/styles.css`
  - Add progressive setup panel/chip styles.
  - Add fade/slide transition classes.
  - Make summary drawer behavior apply at all breakpoints, not only `max-width: 1120px`.
  - Add a clear `View Build Summary` opener style.
  - Respect `prefers-reduced-motion`.

Tests:
- `tests/multi-model-runtime-switching.test.mjs`
  - Assert Vehicle Setup initially presents only the active setup panel and collapsed/available subchoice affordances.
  - Assert selecting model/body/trim advances through setup subpanels without leaving Step 1.
  - Assert `Continue to Exterior Paint` appears only at the appropriate ready state, or remains present but not visually primary until setup is complete, depending on implementation.
  - Assert model switching still resets body/trim/defaults correctly.
- `tests/stingray-form-regression.test.mjs`
  - Update mobile/progress/sidebar assertions to cover all-breakpoint summary drawer behavior.
  - Assert summary content remains available through the drawer and not deleted.
  - Assert repeated `1LT / 2LT / 3LT` copy is reduced in the Vehicle Setup render.

No planned changes:
- `stingray_master.xlsx`
- generated `form_*` sheets
- `form-output/*`
- `form-app/data.js`
- generator scripts
- dealer submission endpoint/payload/Turnstile behavior

## Constraints

- Runtime-only UX pass.
- No workbook edits.
- No generated data hand edits.
- No new dependencies.
- No runtime refactor beyond the minimum needed to support setup subpanels and summary drawer availability.
- Preserve active model/body/trim state fields and generated data contracts.
- Preserve pricing/rule/selection semantics.
- Preserve download, dealer submission, Turnstile, and payload shape.
- Preserve current multi-model behavior for Stingray and Grand Sport.
- Do not hardcode model/RPO-specific business rules.
- Any copy added should be generic or derived from existing generated labels/tooltips; avoid inventing product facts unless explicitly approved.

## Risks

- All-breakpoint summary drawer can hide important open requirements if the opener is not obvious enough.
- Progressive setup state can become confusing if the user changes an earlier choice after choosing later choices; tests must cover recalculation/reset behavior.
- Animations can feel gimmicky or harm accessibility if too strong; keep subtle and respect reduced-motion.
- Existing tests may assume summary panel is visible at desktop widths; update only where the UX contract is intentionally changing.

## Non-goals

- Do not revert to three full rail/page steps unless explicitly requested.
- Do not change workbook source data.
- Do not change model/body/trim availability or pricing rules.
- Do not redesign every option step.
- Do not change the final order summary/export/dealer submission flow.
- Do not deploy from this pass.

## Validation plan

Targeted runtime gates:

```sh
node --test tests/stingray-form-regression.test.mjs tests/multi-model-runtime-switching.test.mjs
```

Full current suite after targeted gates pass:

```sh
node --test tests/stingray-form-regression.test.mjs tests/stingray-generator-stability.test.mjs tests/grand-sport-contract-preview.test.mjs tests/grand-sport-draft-data.test.mjs tests/grand-sport-rule-audit.test.mjs tests/multi-model-runtime-switching.test.mjs
```

Manual/browser verification:

```sh
cd form-app
/Users/seandm/Projects/27vette/.venv/bin/python -m http.server 8765
```

Check:
- First screen is less dense than the current all-at-once setup page.
- Model -> Body -> Trim progresses smoothly within Vehicle Setup.
- The user can reopen/change earlier setup choices without losing expected defaults.
- `Continue to Exterior Paint` leads to the paint step.
- Summary drawer is obvious and callable at desktop/tablet/mobile widths.
- Summary drawer contains the same selected RPOs, auto-added RPOs, open requirements, and totals as before.
- No browser console errors.
- Reduced-motion setting avoids transition effects.

## Approval needed

Before implementation, confirm this direction. Suggested approval phrase:

`approved: implement progressive vehicle setup disclosure`
