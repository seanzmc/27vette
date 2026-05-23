# Vehicle Setup Common-Sense UX Cleanup Spec

## Objective:
Make the early configurator flow feel obvious and common-sense instead of exploratory. Fix the mismatched build-summary drawer affordance, move the primary `Next` action out of no-man’s-land, and reduce premature/global actions that compete with the current choice.

## Diagnosis:
Inspected the running app at `http://localhost:8890` after the prior Vehicle Setup pass.

Concrete UX problems observed:
- `form-app/index.html:17-20` places `View Build Summary` in the top-left/header area, but it controls `#summaryDrawer` on the far right side of the screen. This creates a left-control/right-panel mismatch.
- `form-app/app.js:461-473` only toggles `aria-expanded`; it does not update the visible label/icon. After opening the summary drawer, the button can still read like an opener instead of reflecting the open state.
- `form-app/styles.css:1591-1673` turns the summary panel into a right-side fixed drawer at <=1120px, while the opener can still be visually disconnected from that drawer. Browser visual inspection confirmed the opened drawer feels modal/right-side while the trigger remains top-left/background.
- `form-app/app.js:2178-2183` renders the primary next action as a generic footer after the entire step body. `form-app/styles.css:306-314` right-aligns `.step-footer`. On the current setup screen this puts `Continue to Body Style` in the lower-right corner, detached from the model cards and selected highlight.
- The customer’s immediate task is `Choose your model`, but the top action row still gives Reset / Download Build / Submit to Dealer comparable prominence at the beginning of the flow. These buttons are disabled or guarded, but visually they still compete with the next required decision.
- The heavy summary drawer content is useful, but during first-run setup it asks customers to explore and understand a secondary surface before the current decision path is clear.

Root cause:
- The UI currently has correct functional pieces, but their physical placement and state labels do not match the customer’s mental model. Primary progression is rendered as page footer chrome instead of part of the current choice panel, and secondary/global actions are exposed before the customer has enough context.

Risk level:
- Medium.
- This is a runtime/CSS/HTML presentation and interaction pass touching global navigation controls, but it can preserve generated data, pricing, rules, export, and dealer submission behavior.

Change type:
- Mixed visual/runtime behavior.
- No workbook/data-source changes.
- No generated artifact changes.

## Relevant files/areas:
- Modify: `form-app/index.html`
  - `#openSummaryDrawerButton`
  - `.toolbar`
  - possibly add a small status/help text target near top actions if needed.
- Modify: `form-app/app.js`
  - `setMobileDrawer()` around `app.js:461-473`
  - `renderStepContent()` around `app.js:2155-2185`
  - `renderVehicleSetupPanel()` / `renderVehicleSetupHighlight()` if CTA moves inline for setup stages
  - `renderMobileProgress()` if mobile next/back labels need to stay in sync
  - `renderSummary()` if top action disabled-state helper text needs existing missing-requirement counts
- Modify: `form-app/styles.css`
  - `.topbar`, `.toolbar`, `.mobile-drawer-button-right`
  - `.summary-panel` drawer behavior around desktop/tablet breakpoints
  - `.step-footer`
  - new setup/step CTA placement classes if introduced
- Modify tests:
  - `tests/stingray-form-regression.test.mjs`
  - `tests/multi-model-runtime-switching.test.mjs`

## Proposed approach:
1. Make Build Summary controls stateful and spatially sensible.
   - Stop using a top-left text button that says `View Build Summary` while controlling a far-right drawer.
   - Preferred cleanup:
     - Treat the right summary as a true secondary panel/drawer.
     - Put the primary toggle closer to the summary side visually, or make it a compact `Build Summary`/`Hide Summary` control with clear open/closed state.
     - When open, the trigger should show `Hide Build Summary` or the drawer header should own the close action clearly.
     - Icon direction should match panel movement: if the panel slides from the right, use a right-side drawer/collapse affordance, not a left-side feeling control.
   - Keep `#summaryDrawer`, summary content, selected RPOs, requirements, and standard-equipment summary intact.

2. Make summary closed/callable during early setup, not a competing default surface.
   - During Vehicle Setup, summary should be a clearly labelled secondary action, not a dominant panel competing with model/body/trim.
   - Keep an obvious `Build Summary` affordance and current price/requirement status if useful, but do not require customers to explore the drawer to understand the flow.
   - Do not remove the summary or its content; change prominence and affordance only.

3. Move/duplicate the primary next action into the current decision area.
   - For Vehicle Setup stages, render the CTA directly inside or immediately after the setup panel/highlight, not only as a detached bottom-right footer.
   - Example direction:
     - Model stage highlight ends with a primary button: `Continue to Body Style`.
     - Body stage highlight ends with `Continue to Trim Level`.
     - Trim stage highlight ends with `Review Vehicle Setup`.
     - Ready stage uses `Continue to Exterior Paint` in the ready panel.
   - The existing footer can either be hidden for setup stages or converted to a sticky compact bar only when helpful, but avoid two competing next buttons.
   - Keep selection and progression separate: card click previews/selects; CTA advances.

4. Make global actions less noisy while build is incomplete.
   - Keep Reset available, but keep it visually secondary.
   - Keep Download/Submit behavior unchanged and disabled until requirements are complete.
   - Consider moving disabled Download/Submit out of the top-level early visual hierarchy or visually grouping them as `Final actions` / `Available after required choices`.
   - Do not change endpoint, payload, Turnstile, or final-step submit behavior.

5. Make the “what do I do next?” path obvious without extra exploration.
   - The current panel should answer, in order:
     1. What am I choosing right now?
     2. What is currently selected?
     3. What is the next action?
     4. Can I change earlier choices?
   - Setup chips can remain as the local progress/change affordance, but their clickability should be visually obvious enough to act as `Change` affordances.

6. Keep this as a subtraction/placement pass, not a new redesign.
   - No new nested containers.
   - No new copy-heavy intro block.
   - No new product facts unless already present.
   - No workbook/source-data changes.

## Constraints repeated back:
- Preserve one top-level `Vehicle Setup` step.
- Preserve Model -> Body Style -> Trim -> Ready progressive disclosure.
- Preserve card-click preview/selection separate from explicit progression.
- Preserve generated data contracts and workbook source-of-truth rules.
- No workbook edits.
- No generated `form_*`, `form-output/*`, or `form-app/data.js` edits.
- No new dependencies.
- No dealer submission endpoint/payload/Turnstile changes.
- No pricing, availability, selected-RPO, auto-added-RPO, export, or rule behavior changes.
- Do not reintroduce clutter or nested-container feel.

## Risks/assumptions:
- Assumption: the goal is a targeted common-sense UX cleanup, not a full responsive redesign.
- Risk: moving the CTA inline may duplicate existing mobile progress `Next` controls unless the footer/mobile affordances are coordinated.
- Risk: hiding or reducing top actions too much could make export/submit harder to find later. Mitigate by keeping final actions visible/enabled at the final step and preserving drawer/final action buttons.
- Risk: changing drawer state labels requires tests to avoid regressions in `aria-expanded` and mobile drawer behavior.

## Acceptance criteria:
- Build Summary affordance:
  - The summary trigger label/icon reflects state: open vs closed.
  - The trigger’s placement and label make it clear it controls the build summary drawer/panel.
  - When the right-side drawer is open, there is an obvious close/hide affordance in or near the drawer.
  - The drawer content itself is unchanged.
- Next/progression affordance:
  - On Vehicle Setup stages, the primary next action appears adjacent to the selected card/highlight content, not stranded at the bottom-right of the page.
  - There is only one primary next CTA for setup stages.
  - Card clicks still do not auto-advance.
  - `Continue to Body Style`, `Continue to Trim Level`, `Review Vehicle Setup`, and `Continue to Exterior Paint` still advance to the correct places.
- Visual hierarchy:
  - The current decision dominates the page during Vehicle Setup.
  - Summary/export/submit/reset actions are visibly secondary until needed.
  - A first-time customer can infer the next action without opening the summary drawer or scanning the far corner.
- Behavior preservation:
  - Summary drawer opens/closes correctly on desktop/tablet/mobile widths.
  - Mobile step drawer and summary drawer still close with the close button/backdrop/Escape.
  - Download and Submit remain disabled until requirements are complete.
  - Dealer submission payload, endpoint, Turnstile, and export output are unchanged.
- Accessibility:
  - `aria-expanded` remains accurate.
  - Drawer controls have accurate `aria-label`s for open/close state.
  - Inline setup CTA is keyboard reachable and not duplicated with another equivalent setup CTA.

## Validation plan:
- Targeted tests:
  - `node --test tests/stingray-form-regression.test.mjs tests/multi-model-runtime-switching.test.mjs`
- Full current suite because this touches global runtime/layout controls:
  - `node --test tests/stingray-form-regression.test.mjs tests/stingray-generator-stability.test.mjs tests/grand-sport-contract-preview.test.mjs tests/grand-sport-draft-data.test.mjs tests/grand-sport-rule-audit.test.mjs tests/multi-model-runtime-switching.test.mjs`
- Browser smoke:
  - Serve with `cd form-app && ../.venv/bin/python -m http.server 8890`
  - Desktop width:
    - Verify summary toggle state label/icon closed -> open -> closed.
    - Verify Vehicle Setup CTA is visually connected to the active decision area.
    - Verify there is not a second competing setup next button in the bottom-right.
  - Tablet/narrow width around <=1120px:
    - Verify drawer slides from expected side and control label/state still make sense.
  - Mobile width <=760px:
    - Verify existing mobile progress controls still work and do not duplicate/conflict with inline setup CTA.
  - Verify no console errors and no horizontal overflow.

## Recommended reasoning level: medium

## Approval gate:
Do not implement until Sean approves this spec or requests changes.
