# Vehicle Setup Equipment and Source-Backed Copy Spec

## Objective:
Improve the first three Vehicle Setup stages so they feel more guided and customer-friendly without reintroducing clutter or instant/ambiguous progression. Add an optional way to inspect the actual trim-included equipment during trim selection, incorporate short GM-source-backed model/engine copy, and replace the sterile trim sentence `sets the comfort and finish level` with clearer customer language.

## Diagnosis:
Current inspected state:
- `form-app/app.js:104-119` contains hardcoded Vehicle Setup model highlights for Stingray and Grand Sport. The copy already references LS6 and Grand Sport performance facts, but it is runtime-owned presentation copy and should stay short/source-backed if this remains a presentation-only pass.
- `form-app/app.js:1709-1719` renders trim highlight copy with the title `${trimLabel} sets the comfort and finish level`, which is the exact phrase to replace. It is generic and does not explain what the user can compare.
- `form-app/app.js:1931-1981` already has generic standard-equipment rendering helpers:
  - `renderStandardEquipmentGroups(rows, initiallyOpen, openGroupName)`
  - `standardEquipmentRows()`
  - `trimEquipmentRows()`
  - `renderTrimStandardEquipment()`
- `form-app/app.js:1845-1889` currently renders only one Vehicle Setup panel at a time. The trim panel could reuse existing `trimEquipmentRows()` data for an optional disclosure without new data or generated artifacts.
- `form-app/styles.css:344-545` contains current compact setup and highlight styling. Any new equipment disclosure needs to be light and visually subordinate, not a nested container stack.
- `/Users/seandm/Projects/27vette/spec-review/gs_presser.md` provides GM source copy/facts, including:
  - refreshed Stingray uses the next-generation LS6 6.7L V8 (`gs_presser.md:80-88`)
  - LS6 output: 535 hp / 520 lb-ft (`gs_presser.md:21-31`, `111-127`)
  - Grand Sport is purist RWD with Magnetic Ride Control standard and available Z52 packages (`gs_presser.md:35-41`, `153-157`)
  - Grand Sport X/eAWD facts exist (`gs_presser.md:45-60`, `224-258`) but there is no inspected app model entry for Grand Sport X yet, so do not surface X-specific claims as if selectable.

Root cause:
- The flow now has better pacing, but the selected-state support is still a little too abstract. The trim stage asks the customer to choose a trim without giving a convenient, optional look at what equipment that trim actually includes.
- The previous over-clutter problem came from too many always-visible summaries. The fix should add information as a user-controlled disclosure, not a permanently open block.

Risk level:
- Medium.
- This is a multi-file runtime/CSS/test change in a live customer app, but it can be behavior-preserving if scoped to presentation and reused generated data.

Change type:
- Mixed presentation/runtime behavior.
- No workbook/data-source change proposed in this pass.
- No generated artifact change proposed in this pass.

## Relevant files/areas:
- Modify: `form-app/app.js`
  - `vehicleSetupHighlights`
  - `trimLevelHighlight()`
  - `renderVehicleSetupHighlight()` if needed for optional secondary actions/details
  - `renderVehicleSetupPanel()` / `renderVehicleSetupContent()` for trim-stage equipment disclosure
  - existing standard-equipment helpers around `renderStandardEquipmentGroups()`, `trimEquipmentRows()`, `renderTrimStandardEquipment()`
- Modify: `form-app/styles.css`
  - Vehicle setup styles around `.vehicle-setup-highlight`, `.vehicle-setup-panel`, `.setup-choice-grid`
  - Add minimal styles for a compact `details` disclosure such as `.vehicle-setup-equipment-disclosure`
- Modify: `tests/stingray-form-regression.test.mjs`
  - Assert new trim copy and optional disclosure render contract.
- Modify: `tests/multi-model-runtime-switching.test.mjs`
  - Assert setup flow still does not auto-advance and model switching still preserves scroll if touched by render changes.
- Read-only source reference: `spec-review/gs_presser.md`

## Proposed approach:
1. Keep the existing one-top-level-step progressive flow:
   - Model -> Body Style -> Trim Level -> Ready.
   - Card click selects/previews only.
   - CTA moves forward.
   - Setup chips remain the only persistent local progress summary.

2. Add optional trim-included-equipment disclosure only on the Trim Level stage:
   - Under the trim highlight, render a compact closed-by-default `<details>` block labeled along the lines of:
     - `See what this trim includes`
     - summary subtext/count: `${trimEquipmentRows().length} included items`
   - Body uses existing `renderStandardEquipmentGroups(trimEquipmentRows(), false, openGroupName)` or a lighter wrapper around that existing helper.
   - Keep it closed by default on all breakpoints to avoid front-loading information.
   - Do not duplicate the heavy Build Summary drawer; this is only trim equipment context.
   - If no trim equipment rows exist, omit the disclosure or show the existing empty state inside the disclosure.

3. Replace the trim highlight copy:
   - Current title: `${trimLabel} sets the comfort and finish level`
   - Proposed direction: `${trimLabel} defines the cabin and included equipment`
   - Proposed fallback description:
     - `Trim level sets the interior presentation, technology baseline, and included equipment before you choose colors, wheels, packages, and accessories.`
   - Keep generated tooltip/detail text as the first source when available, but improve the fallback and facts.
   - Proposed facts:
     - `Included equipment baseline`
     - `Interior and technology content`
     - `Next: exterior paint`

4. Refresh source-backed model/engine copy without adding brochure-length text:
   - Stingray highlight should remain concise and source-backed by `gs_presser.md:80-88` and engine specs:
     - LS6 6.7L V8
     - 535 hp / 520 lb-ft
     - next-generation V8 / everyday supercar positioning
   - Grand Sport highlight should remain concise and source-backed by `gs_presser.md:35-41`:
     - purist RWD
     - standard Magnetic Ride Control
     - available Z52 performance packages
   - Do not mention Grand Sport X/eAWD in selectable model copy unless the app actually exposes a Grand Sport X model entry.
   - Do not add long press-release paragraphs; use 1 headline, 1 short body sentence, and 3 fact pills.

5. Keep visual density under control:
   - No new full-width intro panel.
   - No nested card-in-card stack.
   - New equipment disclosure should look like a slim expandable row or soft panel within the selected highlight area.
   - Keep the model/body/trim cards visible without forcing a scroll past a large information block.

6. Tests:
   - Add/adjust runtime tests to verify:
     - Trim highlight no longer contains `sets the comfort and finish level`.
     - Trim setup stage includes a closed optional disclosure for included equipment.
     - Disclosure pulls from generated `standardEquipment`/`trimEquipmentRows()` rather than hardcoded equipment names.
     - Model highlight copy includes source-backed LS6/Grand Sport facts without adding Grand Sport X claims.
     - Existing explicit progression and scroll-preservation tests still pass.

## Constraints repeated back:
- Preserve the approved progressive Vehicle Setup flow.
- Preserve visual cleanliness: no clutter, no nested-container feel, no always-visible wall of equipment.
- No workbook edits in this pass.
- No generated `form_*` workbook sheet edits.
- No generated artifact edits to `form-app/data.js` or `form-output/*`.
- No new dependencies.
- No runtime business-rule hardcoding; use generated equipment rows already present in `data.standardEquipment`.
- Do not change price, rules, availability, payload shape, dealer endpoint, Turnstile behavior, export behavior, or build-summary contents.
- Keep GM press-release facts short and source-backed; do not invent unsupported claims.
- Do not surface Grand Sport X-specific performance/eAWD details as selectable model guidance unless/until the app exposes that model/variant path.

## Risks/assumptions:
- Assumption: This pass is presentation-only and should not migrate copy to workbook-owned metadata yet. A future workbook-owned setup-copy sheet would be better if these highlights become a long-term source-of-truth surface.
- Risk: Hardcoded model highlight copy is still runtime-owned product copy. Keep it explicitly small and source-backed to avoid expanding business logic in JavaScript.
- Risk: `trimEquipmentRows()` may be long for some variants. Closed-by-default disclosure prevents overload, but open state may still be lengthy. If it feels heavy in browser QA, cap visible groups or use a tighter grouped summary in a follow-up spec.
- Risk: Mobile spacing may need adjustment so the disclosure does not push the CTA too far down.

## Acceptance criteria:
- Model stage:
  - Customer sees concise source-backed model guidance and fact pills.
  - No instant auto-advance on model card click.
  - No Grand Sport X/eAWD claims appear unless a selectable Grand Sport X model exists.
- Body style stage:
  - Flow and copy remain focused on roof/body choice.
  - No new redundant summary surface is introduced.
- Trim stage:
  - The phrase `sets the comfort and finish level` is gone.
  - New copy explains that trim affects cabin/interior/technology/included-equipment baseline.
  - Customer can optionally expand `See what this trim includes` or equivalent.
  - The disclosure is closed by default and uses actual generated trim equipment rows for the current model/body/trim.
  - Changing trim updates the disclosure content.
- Visual/layout:
  - Cards remain the primary interaction surface.
  - The equipment disclosure is subordinate and not styled as another heavy nested container.
  - No horizontal overflow at desktop or mobile widths.
- Behavior preservation:
  - Selection and progression remain separate actions.
  - Setup chip `Change` behavior still works.
  - Model switching inside Vehicle Setup still preserves scroll.
  - Pricing, generated rules, selected RPOs, build summary, download, and dealer submission behavior are unchanged.

## Validation plan:
- Targeted tests:
  - `node --test tests/stingray-form-regression.test.mjs tests/multi-model-runtime-switching.test.mjs`
- Full current suite because runtime rendering changes touch setup flow:
  - `node --test tests/stingray-form-regression.test.mjs tests/stingray-generator-stability.test.mjs tests/grand-sport-contract-preview.test.mjs tests/grand-sport-draft-data.test.mjs tests/grand-sport-rule-audit.test.mjs tests/multi-model-runtime-switching.test.mjs`
- Browser smoke:
  - Serve with `cd form-app && ../.venv/bin/python -m http.server 8890`
  - Verify Model -> Body Style -> Trim Level -> Ready on desktop width.
  - Verify trim equipment disclosure is closed initially, expands cleanly, and updates after selecting another trim.
  - Verify no console errors.
  - Spot-check mobile/narrow width for overflow and excessive above-the-fold pushdown.

## Recommended reasoning level: medium

## Approval gate:
Do not implement until Sean approves this spec or requests changes.
