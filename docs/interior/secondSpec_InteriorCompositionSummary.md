# Spec: Priority C — Interior Composition Summary

Status: Spec only. Do not implement until approved.

## Diagnosis

The interior flow is still fragmented across four separate runtime steps:

- `seat`
- `base_interior`
- `seat_belt`
- `interior_trim`

Pass 1 improved the Interior Color step by adding workbook-driven swatch media, visible selected state, and customer-facing compatibility copy. The remaining Priority C issue from `docs/interior/interiorUIcritique.md` is that the customer still lacks a compact “your interior so far” view while moving through Seats, Interior Color, Seat Belt, and Interior Trim.

Current runtime evidence:

- `form-app/app.js`
  - `renderStepContent()` owns per-step body rendering and already special-cases `base_interior` at the Interior Color step.
  - `selectedSeatChoice()` resolves the active selected seat option.
  - `state.selectedInterior` and `interiorsById` resolve selected Interior Color.
  - `lineItems()`, `lineItemsFromInterior()`, and `currentOrder()` already compute selected options, interior component lines, auto-added rows, section totals, and pricing from generated data.
  - `currentOrder().sections` already groups selected rows under workbook-authored order-summary sections including `seats_interior`.
- `tests/stingray-form-regression.test.mjs`
  - Existing tests load the browser runtime and assert interior selection, order output, selected interior identity, and section recap behavior.
  - New Priority C tests should use the same harness rather than adding a new browser/runtime test framework.
- `form-app/styles.css`
  - Existing card/summary/section styles can support a compact inline component without changing the shell or dealer flow.

Root cause:

The runtime has all data needed to summarize the selected interior composition, but it only exposes that data in the global build summary / order output. There is no local interior-progress component rendered inside steps 7–10.

Risk level: medium.

Change type: runtime UI + CSS + tests. No workbook source-data edit is expected for this pass.

## Exact Files To Change

Expected source changes:

1. `form-app/app.js`
   - Add generic helper(s) for the current interior composition state.
   - Render the compact composition panel on the four interior steps only:
     - `seat`
     - `base_interior`
     - `seat_belt`
     - `interior_trim`
   - Use generated/runtime state; do not hardcode model/RPO-specific behavior.

2. `form-app/styles.css`
   - Add compact panel styles.
   - Preserve current card layout and step shell behavior.

3. `tests/stingray-form-regression.test.mjs`
   - Add runtime render tests for the composition panel.
   - Cover incomplete and selected states.
   - Cover at least one auto-added/locked interior-related row if feasible with existing fixtures.

Likely generated artifacts:

- None expected.
- If implementation unexpectedly requires generated data changes, stop and write an amended spec before editing workbook/generator paths.

## Proposed Runtime Design

Add a generic inline panel, tentatively named `renderInteriorCompositionSummary()`.

Render location:

- Immediately below the step header or as the first block in the step body for interior steps.
- Do not render on Vehicle Setup, Exterior Paint, Exterior Appearance, Wheels, Performance, Stripes, Accessories, Delivery, or Summary.

Panel content:

1. Seat
   - Selected seat label and RPO when present.
   - Placeholder such as `Choose seats` when missing.

2. Interior Color
   - Selected interior name/code when present.
   - Placeholder such as `Choose interior color` when missing.

3. Seat Belt
   - Selected or auto-added seat belt color when present.
   - If a premium interior locks the belt through generated rules, show customer-facing text such as `Included with selected interior`.
   - Placeholder such as `Choose seat belt` when no current row exists.

4. Interior Trim
   - Selected interior-trim option rows from current state when present.
   - Placeholder such as `No interior trim selected` when optional and empty.

5. Interior delta
   - Sum only current interior-related selected/auto-added line items already computed by runtime data.
   - Recommended source: `currentOrder().sections.find(section_key === "seats_interior")` plus any selected rows in the active `interior_trim` step if those rows still recap under `seats_interior`.
   - Do not recalculate Corvette product pricing in a new path.

6. Compatibility cue
   - Keep this generic and informational, e.g. `Interior color availability follows the selected seat.`
   - If generated missing requirements exist for interior steps, surface the first missing interior action in customer language.

Interaction behavior:

- Summary rows may include small action buttons/links back to the relevant interior step, but only if low-risk with existing `activateStep()` behavior.
- If action links are added, use generic `data-interior-summary-step="seat"` / etc. handlers.
- Do not auto-advance or mutate selections from the summary panel.

## Constraints

- Keep this pass runtime-generic and data-driven.
- No workbook source edits unless an implementation proof shows an existing generated field is insufficient; if that happens, stop and amend this spec.
- No generated `form-output/*` or `form-app/data.js` hand edits.
- No new dependencies.
- No dealer submission endpoint, payload shape, or Turnstile changes.
- No D30/UQT ownership cleanup in this pass; that remains Priority D.
- No left step-rail completion indicators in this pass; that remains Priority E.
- Do not redesign the global build summary drawer.
- Preserve current Interior Color swatch rendering and selected badge from Pass 1.
- Preserve visual stability: no layout-shift selected states, no broad shell/sidebar restyle.

## Non-Goals

- Reclassifying `UQT` or `D30`.
- Hiding, renaming, repricing, or moving Interior Trim options.
- Adding new workbook metadata sheets.
- Adding local `src-img/` runtime paths.
- Changing order export, dealer submission, or Formidable-ready payload semantics.
- Rebuilding the step rail.

## Risks

1. Duplicate source of pricing truth
   - Risk: recomputing interior totals separately could drift from `currentOrder()`.
   - Mitigation: derive the displayed delta from existing runtime line items/section totals only.

2. Confusing optional vs required rows
   - Risk: Interior Trim may be optional while Seats/Interior Color are required.
   - Mitigation: use placeholders that distinguish required missing choices from optional empty choices.

3. Auto-added seat belt copy
   - Risk: generated auto-added rows can be technically correct but customer-hostile if reason text leaks rule language.
   - Mitigation: display generic customer-facing included/locked copy in the panel; keep detailed rule text in existing tooltips/order metadata.

4. Visual crowding
   - Risk: adding a panel to each interior step could make the screens feel heavier.
   - Mitigation: make it compact, low-height, and scannable; avoid duplicating the full Build Summary drawer.

## Implementation Tasks After Approval

1. Add RED runtime test: panel renders on interior steps only.
   - Modify `tests/stingray-form-regression.test.mjs`.
   - Assert the panel appears for `seat`, `base_interior`, `seat_belt`, and `interior_trim`.
   - Assert the panel does not appear on a non-interior step such as `paint`.

2. Add RED runtime test: incomplete state shows actionable placeholders.
   - Use the existing runtime harness.
   - Initialize a normal Stingray 1LT state before selecting an interior.
   - Assert copy for Seat, Interior Color, Seat Belt, and Interior Trim rows.

3. Add RED runtime test: selected state shows current composition.
   - Select a seat, interior, and seat belt using existing runtime helpers.
   - Assert selected labels/RPOs appear in the panel.
   - Assert the interior delta is formatted as currency and matches existing order data.

4. Implement `interiorCompositionState()` or equivalent helper in `form-app/app.js`.
   - Use existing helpers such as `selectedSeatChoice()`, `interiorsById`, `currentOrder()`, `activeChoiceRows()`, and `computeAutoAdded()`.
   - Keep helper generic across Stingray, Grand Sport, and Z06.

5. Implement `renderInteriorCompositionSummary()` in `form-app/app.js`.
   - Escape workbook/generated strings with existing escaping helpers.
   - Use placeholders for missing selections.
   - Do not mutate state.

6. Render the panel from `renderStepContent()` only for the interior step keys.
   - Recommended set: `new Set(["seat", "base_interior", "seat_belt", "interior_trim"])` near other runtime constants.
   - Insert before step-specific choices.

7. If action links are included, bind them generically.
   - Use `data-interior-summary-step` and `activateStep(stepKey)`.
   - Add test coverage for at least one link.

8. Add CSS in `form-app/styles.css`.
   - Compact card/panel layout.
   - Responsive grid or wrap behavior.
   - No new selected-state layout shifts.

9. Run focused tests and browser smoke.

## Validation Plan

Preflight:

```sh
git status --short --branch
```

Expected implementation gates:

```sh
node --test tests/stingray-form-regression.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

If implementation only touches `form-app/app.js`, `form-app/styles.css`, and runtime tests, no generator run should be required.

Browser smoke:

```sh
cd form-app
../.venv/bin/python -m http.server 8000
```

Manual checks at `http://localhost:8000`:

- Stingray 1LT interior flow:
  - Seats step shows compact composition panel.
  - Interior Color step shows swatches plus composition panel.
  - Seat Belt step shows composition panel and existing belt images.
  - Interior Trim step shows composition panel.
  - Selecting/changing seat updates panel and still updates available interior colors.
  - Selecting/changing interior updates panel and keeps Pass 1 selected badge.
  - Selecting/changing seat belt updates panel.
  - Browser console has no JS errors.

Recommended extra smoke if time permits:

- Switch to Grand Sport and Z06; verify panel renders without model-specific broken labels or missing-data exceptions.

## Approval Question

Approve Priority C implementation: add a compact Interior Composition summary across Seats, Interior Color, Seat Belt, and Interior Trim, runtime-only unless implementation proves a missing generated-data field?
