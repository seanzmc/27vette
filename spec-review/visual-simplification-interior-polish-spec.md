# Visual Simplification and Interior Polish Spec

## Request

Refine the current visual pass by removing redundant instructional labels and relationship pills, keeping the improved related-options containers, moving required-state communication to section titles, and improving the Interior Color step/card presentation.

User-provided screenshot inspected:

- `/Users/seandm/Projects/27vette/spec-review/SCR-20260522-lodz.png`

Screenshot evidence:

- Step header shows `Interior Color`.
- The section immediately below also shows `Interior Color`, creating redundant labeling in the same viewport.
- The step header also repeats the full variant declaration, while the right summary panel repeats `Corvette Grand Sport Convertible 2LT`.
- Interior color group cards currently feel flat: simple border, transparent background, no dimensional/inset treatment.
- Interior group cards show useful expandable color-family grouping, but the card presentation could better communicate that each group is an interactive container.

## Diagnosis

### Root cause

The previous phase added customer-friendly section mode text and relationship badges, but the resulting UI still over-explains simple interactions:

- `renderModeLabel(section)` in `form-app/app.js` maps workbook section selection modes to customer-facing phrases like `Choose one`, `Choose up to one`, and `Choose any that apply`.
- `relationshipBadgesForChoice(choice)` still emits visual pills for single-choice exclusive groups:
  - optional single-choice groups show `Choose one`
  - required single-choice groups show `Required choice`
- `renderStepContent()` renders the mode label inside every `.section-title` for ordinary sections, context sections, and currently renders `Interior Color` as both the step `<h2>` and the interior section `<h3>`.
- Interior group styles in `form-app/styles.css` are intentionally plain:
  - `.interior-group` has `border: 1px solid var(--line)`, `border-radius: 8px`, and `background: transparent`
  - hover/microinteraction is primarily on child choice cards, not the group card itself.

### Exact files/symbols to inspect and change

- `form-app/app.js`
  - `exclusiveGroupVisualLabel(group)` around lines 1110-1114
  - `relationshipBadgesForChoice(choice, { disabled })` around lines 1128-1148
  - `renderRelationshipBadge(badge)` around lines 1163-1178
  - `renderChoiceRelationshipBadges(choice, { disabled })` around lines 1180-1188
  - `renderModeLabel(section)` around lines 1481-1490
  - `renderInteriorGroups(interiors)` around lines 1530-1582
  - `renderStepContent({ resetScroll })` around lines 1819-1898
- `form-app/styles.css`
  - `.section-title` / `.section-title span` around lines 297-309
  - `.interior-color-section` around lines 394-396
  - `.interior-group` / `.interior-group-header` around lines 398-411
  - `.interior-group > summary.interior-group-header::before` around lines 417-424
  - `.interior-group[open] .interior-group-header::before` around lines 426-428
  - `.interior-group-title`, `.interior-group-summary`, `.interior-group-count`, `.interior-group-body` around lines 430-457
  - `.choice-relationship-badge` styles around lines 644-705
- `tests/multi-model-runtime-switching.test.mjs`
  - Recent phase-1 tests around the relationship badges, section labels, and selected-RPO summary.
- `tests/stingray-form-regression.test.mjs`
  - Existing test `selection modes have friendly display labels` and any assertions depending on visible mode labels.

### Risk level

Medium-low.

This is mostly visual/rendering copy and CSS. Risk is higher than a pure CSS tweak because removing required/exclusive badges requires preserving accessibility and required-state discoverability elsewhere.

### Change type

Mixed visual/UI rendering and tests.

No workbook, generated artifact, pricing, rule, export, or dealer submission changes are intended.

## Approved scope for this phase

### 1. Remove section mode helper copy from visible section headers

Remove visible text such as:

- `Choose one`
- `Choose up to one`
- `Choose any that apply`
- `Choose required options`

from `.section-title` headings in the active step body.

Implementation direction:

- Replace the visual use of `renderModeLabel(section)` in `renderStepContent()` with an empty string or remove the `<span>` entirely when it only contains selection-mode guidance.
- Keep underlying workbook fields and runtime selection behavior unchanged.
- Do not remove required-state logic; only remove the redundant instructional label.

Acceptance:

- Ordinary section headings no longer show `Choose one`, `Choose up to one`, or `Choose any that apply`.
- Tests assert the old phrases are absent from rendered step content.

### 2. Remove `Choose one` relationship pills from option cards

Remove visual pills used only to say an option is part of a single-choice exclusive group.

Implementation direction:

- In `relationshipBadgesForChoice(choice)`, stop pushing badges for non-required exclusive groups.
- Do not remove related-options containers. `renderChoiceRelationGroup()` should continue to wrap visible exclusive-group peers.
- Keep `data-choice-relation-group` on containers for tests/debugging.
- Keep include badges (`Includes N items`) because those communicate package contents and retain the tooltip target.

Acceptance:

- Cards in optional exclusive groups do not show `Choose one` pills.
- Related-options containers still render around grouped choices.
- Include pills still render and still expose structured tooltips.

### 3. Replace `Required choice` pills with required section-title indicator

Required single-choice groups should not show `Required choice` pills on every card.

Implementation direction:

- Stop rendering required relationship pills from `relationshipBadgesForChoice(choice)`.
- Add a required marker to the relevant section heading when a section has a required selection state.
- Suggested markup:
  - `<h3>Performance Brakes <span class="required-mark" aria-hidden="true">*</span></h3>`
  - optional visually hidden accessible text, e.g. `<span class="sr-only">required</span>`, if an existing screen-reader utility class exists; otherwise add a small utility class.
- Required marker should apply when:
  - `section.selection_mode === "single_select_req"`, or
  - `truthyValue(section.is_required)`, or
  - the section contains an active required exclusive group in the current choices.
- Style the marker in red/accent and keep it compact/universal.

Acceptance:

- No `Required choice` pills visible on cards.
- Required sections show a red `*` in the section title.
- Required behavior and open requirements remain unchanged.

### 4. Clean up Interior Color redundant labels

The Interior Color step should not repeat `Interior Color` as both the page-level step heading and first section heading.

Implementation direction:

- For `state.activeStep === "base_interior"`, remove the redundant section `<h3>Interior Color</h3>` or replace it with a more contextual, non-duplicative label.
- Recommended approach:
  - Keep the step header `<h2>Interior Color</h2>`.
  - Replace the section title row with a quieter support row, e.g. the compatibility sentence and optional total count only if needed.
  - Avoid adding another full variant declaration inside the main panel.
- Consider moving the `interiors.length` count out of a headline-level row, or remove it if it does not improve UX.

Acceptance:

- On the Interior Color step, the main content does not show `Interior Color` twice.
- Variant declaration is not duplicated inside the section body.
- The compatibility sentence remains because it explains why only certain interiors are shown.

### 5. Add microinteractivity/dimensional inset treatment to interior groups

Interior color groups should feel like interactive/recessed containers, not flat boxes.

Implementation direction:

- Update `.interior-group` and related selectors in `form-app/styles.css`.
- Desired direction:
  - Slightly recessed/inset card surface, e.g. inner shadow, subtle darker inset border, warm panel background.
  - Hover/focus-within state that gives gentle dimension without a loud glow.
  - Open state that makes the group look active and expanded.
  - Preserve disclosure affordance (`▸` / `▾`) and keyboard behavior.
- Example style direction, not exact required values:
  - `background: rgba(248, 243, 234, 0.55);`
  - `box-shadow: inset 0 1px 3px rgba(32, 24, 16, 0.08), 0 1px 0 rgba(255,255,255,0.45);`
  - `transition: box-shadow 140ms ease, border-color 140ms ease, background 140ms ease, transform 140ms ease;`
  - hover/focus-within: slightly deeper inset shadow and border contrast.

Acceptance:

- Interior group cards have a subtle recessed/inset dimensional style.
- Hover/focus-within gives a small but perceptible interaction cue.
- Open/closed details remain usable with keyboard and pointer.
- Interior choice card styling remains intact.

## Constraints repeated back

- Visual preservation: keep the overall Corvette order-form look, spacing rhythm, warm panel colors, selected state styling, and recently improved related-options containers.
- No refactor: make targeted rendering/style changes only; do not reorganize runtime architecture.
- No new dependencies or build step.
- Workbook source-of-truth rules: do not patch workbook data or generated data for this visual pass.
- Do not edit generated `form_*` workbook sheets or generated artifacts.
- Do not change pricing, selection, include/exclude, required behavior, default selection, export output, dealer submission payload, endpoint, Turnstile behavior, or confirmation flow.
- Keep related-options containers; remove only the extra pills/instructional labels that are not adding UX value.
- Keep include pills and include tooltip behavior from phase 1.
- Keep mobile support for tooltip/pill interactions.
- Preserve accessibility: required state should remain perceivable after removing repeated card pills.

## Risks

- Removing visible section mode labels may make some sections less explicit, but the user preference is that these labels do not improve UX.
- Replacing required pills with a `*` requires clear styling and/or accessible text so required state is still understandable.
- Interior group inset styling could become too heavy or conflict with choice-card shadow styling if not tuned in browser.
- The right summary variant declaration remains by design; removing the step-header variant meta is out of scope unless explicitly approved because it is global step-header behavior.

## Non-goals

- No workbook copy/name/display-order cleanup in this phase.
- No generated artifact regeneration.
- No functional change to exclusive group behavior.
- No functional change to required validation or missing requirement calculation.
- No change to selected-RPO grouping, export format, dealer submission, or order totals.
- No redesign of the full interior step layout beyond redundancy cleanup and group card microinteractivity.

## Test plan

Use TDD for implementation.

1. Update/add failing tests first.

Targeted assertions in `tests/multi-model-runtime-switching.test.mjs`:

- Render Grand Sport Performance & Aero.
- Assert related-options containers still exist.
- Assert old visible section labels are absent:
  - `Choose one`
  - `Choose up to one`
  - `Choose any that apply`
- Assert old card relationship pills are absent:
  - `Required choice`
  - `choice-relationship-badge required`
  - `choice-relationship-badge exclusive`
- Assert include pills remain:
  - `choice-relationship-badge includes info-tooltip`
  - `Includes N items`
- Assert at least one required section title includes `required-mark`.
- Render Interior Color step and assert it does not duplicate `Interior Color` in both step header and section title.

2. Verify RED.

Run:

```sh
node --test tests/multi-model-runtime-switching.test.mjs
```

Expected before implementation: FAIL on the new assertions.

3. Implement the smallest app/style changes.

Files:

- `form-app/app.js`
- `form-app/styles.css`

4. Verify GREEN.

Run:

```sh
node --test tests/multi-model-runtime-switching.test.mjs
node --test tests/stingray-form-regression.test.mjs
git diff --check
```

5. Manual browser QA.

Serve locally:

```sh
cd /Users/seandm/Projects/27vette-schema-standardization/form-app
../.venv/bin/python -m http.server 8001
```

Verify:

- Grand Sport Performance & Aero:
  - related-options containers remain
  - no `Choose one` / `Required choice` pills
  - no section mode helper labels
  - required section title has a red `*`
  - include pills still work as tooltip targets
- Interior Color:
  - no duplicate `Interior Color` section heading under the step heading
  - compatibility sentence remains
  - interior group cards feel subtly recessed and interactive
  - details open/close normally
- Sidebar summary and totals remain unchanged except for already-approved visual behavior.

## Approval gate

This is a non-trivial visual/runtime/test change under the workspace guidelines. Do not implement until this spec is approved.
