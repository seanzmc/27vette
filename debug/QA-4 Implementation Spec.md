# QA-4 Implementation Spec

## Scope

This pass should resolve the QA-4 "New Issues" list and implement the full tiered interior display model from Issue 13. It is a mixed data-contract, runtime-behavior, and styling task. The riskiest area is interior selection because it changes the user-facing mental model from a flat `base_interior` card grid into a grouped trim/seat/color/material/final-choice flow while preserving the existing single selected interior contract.

## Diagnosis

Root cause by area:

- Suspension defaults and FE3 visibility: `scripts/generate_stingray_form.py` currently leaves FE3 as an included/standard-equipment choice instead of a selectable suspension tile, while `form-app/app.js` has special runtime defaulting and Z51 reconciliation for FE1/FE2 but no explicit FE3/FE4 mutual-default model.
- Exterior ordering and section grouping: section-to-step mapping and section display order are generated in `scripts/generate_stingray_form.py`; runtime sorting in `form-app/app.js` already honors `section_display_order` and `display_order`, so source ordering should be fixed in the generator/workbook contract rather than by ad hoc DOM sorting.
- Spoiler rules: `scripts/generate_stingray_form.py` injects T0A manual rules and keeps same-section `excludes` for T0A, but QA-4 needs one-way replacement behavior where other spoilers remove T0A without T0A blocking TVS/5ZZ/5ZU, and ZYC only conflicts with GBA.
- Exhaust defaults: `form-app/app.js` removes NGA when NWI is selected, but does not restore NGA when NWI is later unselected.
- Scroll reset: `renderStepContent()` calls `els.stepContent.scrollTo(...)`, but the reported behavior means the actual scrolling container may be the page, `.choice-panel`, or another ancestor, so this needs browser verification rather than another blind `scrollTo` tweak.
- Standard/Included duplication: `form-app/index.html` has both `#selectedStandardEquipmentList` inside the Selected RPOs summary card and a standalone `#standardEquipmentList` card; `form-app/app.js` renders both.
- Interior selection: generated `form_interiors` rows already contain useful fields (`trim_level`, `seat_code`, `interior_code`, `interior_name`, `material`, `suede`, `stitch`, `two_tone`, `requires_r6x`), but runtime renders them as one flat grid filtered only by trim and selected seat. Issue 13 requires a tiered presentation and a consistent display-field model for one-choice and multi-choice groups.
- R6X/D30 color override: `AUTO_ONLY_OPTION_IDS` currently hides D30, but R6X still appears as a selectable `interior_trim` option. Color override auto-add and pricing must be reconciled so R6X is auto-only and $0 when added with interiors that already include its price, while D30 remains charge-bearing when triggered.
- Seatbelt defaults: auto-added included seatbelts currently appear as auto-added rows but do not become the active replaceable default in the seatbelt selection group. The runtime needs a default-selection layer that can be overridden without treating the default as a final manual selection.

Risk level:

- High: Issue 13 interior tiering, because it touches the generated data shape, runtime rendering, selection semantics, summary/export rows, and mobile layout.
- Medium: FE3/FE4, spoiler replacement, seatbelt defaults, R6X/D30 pricing/default behavior, because they affect pricing and selected/exported RPOs.
- Low to medium: display order, sidebar duplication, and scroll reset, because they are UI/routing fixes but still need browser checks.

## Exact Files To Inspect

- `stingray_master.xlsx`: inspect source sheets before mutation, especially `stingray_master`, `section_master`, `rule_mapping`, `price_rules`, `lt_interiors`, `color_overrides`, and generated `form_*` sheets.
- `scripts/generate_stingray_form.py`: owns generated steps, section mapping, display order, hidden/auto-only IDs, manual rules, generated interiors, generated rules, generated price rules, `form_*` sheet writes, `form-output/stingray-form-data.json`, and `form-app/data.js`.
- `form-app/app.js`: owns defaults, reconciliation, auto-add behavior, disabled reasons, line items, interior rendering, summary rendering, exports, and scroll behavior.
- `form-app/index.html`: owns sidebar structure and static script cache-busting.
- `form-app/styles.css`: owns the tiered interior layout, card states, responsive behavior, and sidebar standard-equipment presentation.
- `tests/stingray-form-regression.test.mjs`: existing contract regression suite; extend rather than replacing.
- `debug/qa-1.md`, `debug/qa-2.md`, `debug/qa-3.md`: inspect only for prior intent and issue continuity, not as a source of current truth.

## Exact Files To Change

Expected source changes:

- `scripts/generate_stingray_form.py`
- `form-app/app.js`
- `form-app/index.html`
- `form-app/styles.css`
- `tests/stingray-form-regression.test.mjs`

Expected generated artifacts after running the generator:

- `stingray_master.xlsx`
- `form-output/stingray-form-data.json`
- `form-output/stingray-form-data.csv`
- `form-app/data.js`

Do not hand-edit generated JSON/CSV/`data.js` except as a temporary diagnostic. Final changes must come from the workbook/generator path so reruns do not reintroduce the defects.

## Constraints

- Preserve the current body style and trim as first-class form steps.
- Preserve the one-variant-at-a-time order-flow mental model.
- Preserve selected interior as one final selected interior row in summary/export unless a separate workbook contract is added later.
- Do not reintroduce the removed `interior_style` step.
- Do not make R6X or D30 manually selectable unless the issue text is explicitly revised.
- Do not add new dependencies.
- Do not redesign the whole app shell while implementing interior tiering. Keep visual changes scoped to the affected option groups, sidebar duplication, and scroll behavior.
- Keep all interior display fields consistent across one-choice and expandable groups.
- Reduce nested accordion levels where possible; use progressive grouped sections/cards, not a deeply nested disclosure tree.
- Do not hide customer-relevant availability or pricing changes in summary/export. If an option is selected, defaulted, auto-added, or priced, it must be auditable.

## Issue Plan

### Group A - Contract and runtime selection rules

Issues covered: 1, 3, 4, 5, 7, 11, 12.

Implementation requirements:

- FE3 must be generated as an active selectable Suspension choice for valid variants. It should still be auto/default-selected when Z51 is selected.
- FE1 remains the default suspension when no overriding suspension/Z51 selection exists.
- FE2 overrides FE1.
- Z51 overrides FE1/FE2 and causes FE3 to become the current suspension default.
- FE4 overrides FE3 and vice versa.
- Existing Z51 effects that make FE1 and FE2 unavailable or removed must persist.
- T0A remains selectable only when Z51 is selected, but T0A must not disable TVS, 5ZZ, or 5ZU.
- TVS/5ZZ/5ZU should remove T0A when chosen, with customer-facing copy equivalent to "Removes T0A when Z51 is selected" instead of "Conflicts with T0A".
- ZYC should remain selected when another spoiler such as TVS is selected; only GBA should conflict with ZYC.
- NGA should be restored automatically when NWI is unselected and no other exhaust-tip choice is active.
- 1LT AE4/HTJ should auto-select because it is the only available interior color path for that trim/seat.
- Seatbelt options included by a 3LT interior should behave as replaceable defaults: remove 719 from selected rows, show the included seatbelt as current/default, allow the user to override it with another seatbelt, and avoid listing both standard 719 and the included default as selected.
- R6X must become auto-only for the listed interiors. It should not render as a selectable Color Override tile. D30 should be the only Color Override card, disabled unless a color combination triggers it.
- If both D30 and R6X are triggered, D30 keeps its charge and R6X contributes $0 because its cost is already in the selected interior.

Preferred implementation shape:

- Add explicit generator-side metadata for auto-only/default-only behavior where it belongs in the contract.
- Keep runtime reconciliation centralized in `reconcileSelections()` or a small helper it calls; do not scatter one-off deletion rules across render functions.
- Extend `lineItems()` only as needed to distinguish manual selections, replaceable defaults, and auto-added RPOs without duplicate customer-facing rows.

### Group B - Display order, section organization, sidebar, and scroll

Issues covered: 2, 6, 8, 9, 10.

Implementation requirements:

- Exterior Appearance section order must be Roof, Exterior Accents, Badges, Engine Appearance.
- Engine Appearance option order must be BC7, BCP, BCS, BC4, B6P, ZZ3, D3V, SL9, SLK, SLN, VUP.
- BC7 must have the "Requires ZZ3 Convertible Engine Appearance Package" requirement and label only for Convertible. Coupe BC7 remains selectable without the ZZ3 requirement label/rule.
- Wheels, Brake Calipers, and Wheel Accessories should appear together in one runtime step with section order Wheels, Brake Calipers, Wheel Accessories. Moving sections between generated runtime categories is allowed if that is the cleanest way to produce the desired order.
- Remove the standalone Standard & Included card at the bottom of the sidebar. Keep the Standard & Included section inside the Selected RPOs summary card.
- Fix Next Step scroll reset against the actual scroll container. Verify a long-to-short transition such as section 8 to section 9 in a browser.

Preferred implementation shape:

- Use generator section order/mapping changes for ordering issues.
- Use `index.html` plus `renderStandardEquipment()` cleanup for sidebar duplication.
- For scroll reset, detect whether `window`, `.choice-panel`, or `#stepContent` is the actual scrolled element before changing code.

### Group C - Tiered interior display model

Issue covered: 13.

Target model:

- The user should select interiors through a hierarchy that reads as:
  1. active trim level
  2. selected seat family (`AQ9`, `AH2`, `AE4`, `AUP`)
  3. color family (`Jet Black`, `Sky Cool Gray`, `Adrenaline Red`, `Natural`, dipped colors, asymmetrical/custom groups, etc.)
  4. material family when applicable (`Napa leather seating surfaces with perforated inserts`, `Sueded microfiber seat inserts and sueded microfiber wrapped steering wheel`, or the current workbook material equivalent)
  5. final interior choice, including stitch/two-tone/suede variants
- One-choice groups should render with the same fields and visual structure as expandable groups, but should not add unnecessary extra disclosure levels.
- Groups with additional choices need an obvious indicator that more options are available.
- Selecting the final option must still set exactly one `state.selectedInterior` value.
- Pricing shown on grouped cards must reflect the current selected seat price subtraction.
- Disabled/requirement states must still use `disableReasonForInterior()` and rule-derived reasons.
- Summary/export should continue to report the final selected interior ID/code/name/price, not just the group label.

Data-model requirements:

- Generate enough grouping fields for deterministic rendering. At minimum, derive and export:
  - `interior_trim_level`
  - `interior_seat_code`
  - `interior_color_family`
  - `interior_material_family`
  - `interior_variant_label`
  - `interior_group_display_order`
  - `interior_choice_display_order`
  - `interior_group_has_children` or equivalent computed runtime signal
- Prefer deriving these from existing `lt_interiors` columns first (`Trim`, `Seat`, `Interior Code`, `Interior Name`, `Material`, `Suede`, `Stitch`, `Two Tone`, `interior_id`). Add explicit mapping tables only where the workbook text is not enough to produce the Issue 13 grouping.
- Keep R6X-specific custom interior combinations grouped under the Issue 13 custom interior trim/seat combination buckets and tied to auto-add R6X behavior.

Runtime/UI requirements:

- Replace the flat `base_interior` grid path with a tiered interior renderer.
- Keep the selected seat prerequisite: if no seat is selected, show the existing empty state.
- Avoid nested cards. Use section bands or compact grouped rows for seat/color/material/final choices.
- Keep card radius at or below the current 8px pattern.
- Ensure mobile layout does not overflow or overlap long interior names.
- Do not use viewport-scaled font sizes.

Acceptance examples:

- 1LT + AE4 should lead to one HTJ Jet Black final choice that auto-selects or clearly becomes the only current interior without an unnecessary expansion.
- 2LT + AH2 + Jet Black should expose the Napa/perforated and sueded microfiber families and their stitch variants.
- 3LT + AH2 should expose dipped, Santorini Blue, Habanero, Very Dark Atmosphere, Ultimate Suede Jet Black, asymmetrical, and custom interior combinations according to the Issue 13 outline.
- 3LT + AUP should expose only the two asymmetrical seat choices listed in Issue 13.

## Risks And Non-Goals

Risks:

- Some Issue 13 display labels may not map cleanly from current workbook fields. If the source workbook cannot distinguish a requested grouping reliably, log the ambiguous rows and use an explicit mapping table instead of guessing.
- Changing selection defaults can alter export totals and selected RPO lists. Tests must cover both visual selection state and exported order rows.
- R6X/D30 pricing can double-count if R6X is treated like a normal option instead of an auto-only zero-dollar add.
- Removing same-section spoiler blocks can accidentally allow invalid combinations if replacement behavior is not modeled separately from availability blocking.

Non-goals:

- Do not solve the older copy/display-field cleanup from Still Existing Issue 1 except where labels are directly named in the new issues.
- Do not implement the future workbook-driven summary/export inclusion flag from Still Existing Issue 3.
- Do not complete the full inactive-label audit from Still Existing Issue 4 outside rows touched by QA-4.
- Do not add generalized package/rule engines beyond what is needed for these named issues.
- Do not redesign standard equipment beyond removing the duplicate sidebar surface.

## Validation Plan

Automated checks:

- Run the generator and confirm it reports zero validation errors.
- Run `node --test tests/stingray-form-regression.test.mjs`.
- Add or update regression tests for:
  - FE3 selectable tile, FE1 default, FE2 override, Z51 -> FE3 default, FE4/FE3 mutual override.
  - T0A does not block TVS/5ZZ/5ZU; TVS/5ZZ/5ZU remove T0A; ZYC only conflicts with GBA.
  - NWI unselect restores NGA.
  - 1LT AE4 HTJ single interior auto/default behavior.
  - R6X absent from selectable choices and auto-added at $0 for listed interiors.
  - D30 charge persists when D30 and R6X are both auto-added.
  - 3LT included seatbelt default replaces 719 but remains user-overridable.
  - Exterior Appearance and Engine Appearance display order.
  - Wheels/Calipers/Wheel Accessories section order in the combined step.
  - Only one Standard & Included sidebar surface remains.
  - Tiered interior grouping fields exist and key acceptance examples map to the expected groups.

Manual/browser checks:

- Serve `form-app/` locally and cache-bust `data.js`/`app.js` if needed.
- Verify the main path: Coupe -> 1LT -> AE4 -> Base Interior shows HTJ as the single current interior path.
- Verify 2LT AH2 Jet Black exposes material/stitch options without nested-card clutter.
- Verify 3LT AH2 and AE4 expose the full Issue 13 grouped sets.
- Verify a 3LT interior that includes a colored seatbelt replaces 719 in the visible selected list and export.
- Verify selecting and unselecting NWI restores NGA.
- Verify long-to-short Next Step navigation scrolls to the top of the new step.
- Verify sidebar has one Standard & Included surface, inside Selected RPOs.
- Verify desktop and mobile widths for no text overlap, no horizontal overflow, and readable long interior labels.
