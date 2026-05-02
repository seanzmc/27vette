# QA-4 Interior Layout Redesign Spec

## Scope

This task implements the interior color redesign plan for the current post-rules-refactor codebase. The original QA-4 Issue 13 plan was written against an earlier pre-rules-refactor state, so this spec must be treated as a refreshed implementation plan, not a direct replay of the older QA-4 pass. It should preserve the current rules-engine surfaces, including generated `ruleGroups`, `exclusiveGroups`, price-rule behavior, and the existing final selected interior contract.

This task implements only QA-4 Issue 13: the full tiered interior display model. It should be run after the main `debug/QA-4 Implementation Spec.md` pass, which is expected to fix interior-adjacent behavior such as 1LT AE4/HTJ defaulting, 3LT included seatbelt defaults, R6X auto-only behavior, and D30/R6X pricing.

This is a focused data-shaping and UI-layout task plus one pricing correction for R6X/D30. The goal is to replace the current flat `base_interior` card grid with a clearer trim/seat/color/material/final-choice model while preserving the existing final selected interior contract and all currently working compatibility behavior.

## Source Of Truth

- Canonical issue text: `debug/qa-4.md` Issue 13.
- Current implementation: `form-app/app.js` renders `base_interior` as a flat grid filtered by selected trim and seat.
- Current data source: `scripts/generate_stingray_form.py` exports `form_interiors` and `data.interiors` from `lt_interiors`.
- Current interior fields available: `trim_level`, `seat_code`, `interior_code`, `interior_name`, `material`, `suede`, `stitch`, `two_tone`, `requires_r6x`, `price`, `source_note`, and `interior_id`.
- Current rules-engine state: the app now has generated `ruleGroups` and `exclusiveGroups`; new interior layout work must preserve and coexist with those surfaces.

## Diagnosis

The current runtime has the right final-selection primitive, `state.selectedInterior`, but the wrong presentation model for the volume and shape of interior data. After a seat is selected, all matching interior rows render as equal flat cards. That makes 2LT and 3LT interiors hard to scan because color, material, suede, stitch, two-tone, dipped, asymmetrical, and custom interior combinations are collapsed into long option names instead of being grouped by the way a customer evaluates them.

Issue 13 defines the missing display model:

- 1LT is simple and should stay simple.
- 2LT needs grouping by seat, then color, then material/final choices where applicable.
- 3LT needs the broadest grouping, including dipped colors, Santorini Blue, Habanero, Very Dark Atmosphere, Ultimate Suede Jet Black, asymmetrical choices, and custom interior trim/seat combinations.
- One-choice groups should look consistent with richer groups but should not force unnecessary accordion depth.

Risk level: high for UI clarity and regression risk, medium for data contract risk. The task should not change option availability, pricing, auto-add rules, or export semantics except for adding grouping fields needed to render the interior UI.

## Exact Files To Inspect

- `debug/qa-4.md`: Issue 13 hierarchy and display notes.
- `debug/QA-4 Implementation Spec.md`: prerequisite behavior fixes and non-goals.
- `stingray_master.xlsx`: inspect `lt_interiors`, generated `form_interiors`, `color_overrides`, and any generated validation rows before changing the generator.
- `scripts/generate_stingray_form.py`: owns generated interior rows, workbook writes, JSON export, and `form-app/data.js`.
- `form-app/app.js`: owns `base_interior` rendering, `renderInteriorCard()`, `handleInterior()`, `disableReasonForInterior()`, line items, summary, and export behavior.
- `form-app/styles.css`: owns the new tiered interior layout and responsive behavior.
- `tests/stingray-form-regression.test.mjs`: extend with grouping/data contract tests.
- `AGENTS.md`: use the project venv command for generator validation if present.

## Exact Files To Change

Expected source changes:

- `scripts/generate_stingray_form.py`
- `form-app/app.js`
- `form-app/styles.css`
- `tests/stingray-form-regression.test.mjs`

Expected generated artifacts after running the generator:

- `stingray_master.xlsx`
- `form-output/stingray-form-data.json`
- `form-output/stingray-form-data.csv`
- `form-app/data.js`

Avoid changing `form-app/index.html` unless the tiered interior layout needs a new static container. Prefer rendering inside the existing `#stepContent` path.

## Constraints

- Preserve body style and trim as first-class form steps.
- Preserve the selected seat prerequisite for interior selection.
- Preserve exactly one final selected interior via `state.selectedInterior`.
- Preserve summary/export output as the final selected interior ID/code/name/price, not a parent group label.
- Preserve `adjustedInteriorPrice()` behavior, including seat-price subtraction.
- Correct the prior QA-4 pricing mistake for R6X: R6X must not be globally forced to $0.
- R6X should keep its normal $995 price unless D30 is also triggered onto the build.
- R6X should price at $0 only when D30 is triggered/auto-added as part of the selected interior/color override path.
- Preserve D30 as visible-disabled/auto-triggered behavior; do not make D30 manually selectable.
- Do not reintroduce the removed `interior_style` step.
- Do not make R6X, D30, N26, TU7, or custom stitch options manually selectable as part of this layout pass.
- Do not change seatbelt defaults, suspension defaults, spoiler rules, section ordering, sidebar standard equipment behavior, `ruleGroups`, or `exclusiveGroups` in this task unless a change is explicitly required for the R6X/D30 pricing correction.
- Do not change seatbelt defaults, color override pricing, suspension defaults, spoiler rules, section ordering, or sidebar standard equipment behavior in this task.
- Keep all interior display fields consistent across one-choice and multi-choice groups.
- Reduce accordion/collapse depth. Use grouped cards, segmented controls, or compact sections instead of deeply nested disclosures.
- Do not add dependencies.
- Keep card radius at or below the existing 8px pattern.
- Avoid text overlap and horizontal overflow on mobile and desktop.

## Data Model Requirements

Generate deterministic grouping fields for each active Stingray interior row. At minimum, export:

- `interior_trim_level`
- `interior_seat_code`
- `interior_seat_label`
- `interior_color_family`
- `interior_material_family`
- `interior_variant_label`
- `interior_group_display_order`
- `interior_material_display_order`
- `interior_choice_display_order`

R6X/D30 pricing correction data requirements:

- Preserve R6X as an auto-only option where currently intended, but do not globally override its price to $0.
- Generate or preserve a scoped price rule so R6X is $0 only when D30 is present in the selected context.
- The scoped price rule should be data-driven and generic, not an `app.js` RPO-specific branch.
- The normal R6X price should remain $995 in contexts where D30 is not triggered.

## Runtime/UI Requirements

Replace the flat `base_interior` branch in `renderStepContent()` with a tiered renderer.

Expected structure:

- Step header remains `Base Interior`.
- If no seat is selected, keep the existing empty state.
- Once a seat is selected, show a compact selected-seat context label.
- Render color-family groups for interiors matching the current trim and selected seat.
- For a color group with one final choice, render one selectable card with the same field set as multi-choice cards.
- For a color group with multiple choices, show an obvious "more choices" indicator and expose material/final choices without adding more collapse levels than necessary.
- Final choice cards must show interior code, customer-facing label, adjusted price, material/variant details, and disabled reason when applicable.
- The selected final choice should be visibly selected wherever it appears.

Display field consistency:

- Every final choice must have a stable code/RPO field, name field, detail field, price field, and state field.
- Parent group cards or headers may summarize available choice count, material families, and price range, but they must not replace the final choice data.

## Required Coverage From Issue 13

The implementation must preserve the Issue 13 organization:

- 1LT:
  - AQ9: HTA Jet Black, HUP Sky Cool Gray, HUQ Adrenaline Red.
  - AE4: HTJ Jet Black.
- 2LT:
  - AQ9: Jet Black stitch variants, Sky Cool Gray, Adrenaline Red, Natural.
  - AH2: Jet Black, Sky Cool Gray, Adrenaline Red, Natural, split between Napa/perforated and sueded microfiber families where applicable.
  - AE4: Jet Black, Sky Cool Gray, Adrenaline Red, Natural, split between Napa/perforated and sueded microfiber families where applicable.
- 3LT:
  - AH2 and AE4: Jet Black, Sky Cool Gray, Adrenaline Red, Adrenaline Red Dipped, Natural, Natural Dipped, Santorini Blue, Habanero, Very Dark Atmosphere, Ultimate Suede Jet Black, asymmetrical choices, and custom interior trim/seat combinations where present in Issue 13.
  - AUP: Asymmetrical Santorini Blue / Jet Black and Asymmetrical Adrenaline Red / Jet Black.

The labels do not need to be word-for-word duplicates of the source list if the workbook already has cleaner customer-facing names, but the grouping must be semantically equivalent and auditable.

## Implementation Plan

1. Inspect current `data.interiors` and build a table of all active Stingray interiors grouped by trim and seat.
2. Add generator-side grouping helpers for color family, material family, variant label, and display order.
3. Export grouping fields through `form_interiors`, `form-output/stingray-form-data.json`, and `form-app/data.js`.
4. Add validation rows for unmapped or duplicate ambiguous interior group labels.
5. Correct R6X/D30 price-rule generation so R6X remains $995 unless D30 is triggered, and becomes $0 only when D30 is present in the selected context.
6. Replace the `base_interior` flat grid renderer with a tiered renderer using the new grouping fields.
7. Add CSS for grouped interior sections, compact group headers, choice grids, selected states, disabled states, and mobile wrapping.
8. Extend regression tests for the generated grouping fields and key Issue 13 examples.
9. Run generator, tests, and browser checks.

## Risks And Non-Goals

Risks:

- Some current workbook labels may not naturally distinguish the exact Issue 13 color family or material family. Use explicit mappings and validation warnings rather than guessing.
- Parent group selection can accidentally obscure the final selected interior. Keep final cards as the only true selectable interior rows.
- Long labels such as custom interior trim/seat combinations can overflow on mobile if card layout is too tight.
- If the main QA-4 behavior pass is not complete first, R6X/D30 and seatbelt behavior may still look wrong even if the layout is correct.
- R6X/D30 pricing is easy to overcorrect. The fix must avoid another global R6X price override and must prove both the $995 and $0 cases in tests.

Non-goals:

- Do not fix FE1/FE2/FE3/FE4, Z51, spoilers, NWI/NGA, BC7/ZZ3, wheels/calipers, scroll reset, or sidebar duplication here.
- Do not change pricing semantics except to display the existing adjusted interior price.
- Do not change summary/export shape beyond preserving the selected final interior.
- Do not introduce a new interior wizard step sequence unless the existing `base_interior` step cannot support the layout.
- Do not add new dependencies or a generalized rule engine.

## Validation Plan

Automated checks:

- Run the generator using the project venv command from `AGENTS.md` when available, preferably `.venv/bin/python scripts/generate_stingray_form.py`, and confirm zero validation errors.
- Run `node --test tests/stingray-form-regression.test.mjs`.
- Add or update tests that assert:
  - every active Stingray interior has the required grouping fields.
  - 1LT AQ9 has HTA/HUP/HUQ color choices.
  - 1LT AE4 maps to the single HTJ Jet Black path.
  - 2LT AH2 Jet Black has Napa/perforated and sueded microfiber families with stitch variants.
  - 2LT AE4 Natural includes the expected Natural and Natural Two Tone / sueded variants where present.
  - 3LT AH2 includes dipped, Santorini Blue, Habanero, Very Dark Atmosphere, Ultimate Suede Jet Black, asymmetrical, and custom interior groups.
  - 3LT AUP has only the two asymmetrical final choices from Issue 13.
  - no active interior row is dropped from the rendered grouping source.
  - R6X retains its normal $995 price when D30 is not present in the selected context.
  - R6X prices at $0 only when D30 is present/triggered in the selected context.
  - D30 remains non-manually-selectable and only participates through the existing trigger/override path.

Manual/browser checks:

- Serve `form-app/` locally and cache-bust `data.js`/`app.js` if needed.
- Verify 1LT + AQ9 and 1LT + AE4 are simple and do not add unnecessary expansion.
- Verify 2LT + AH2 + Jet Black exposes material/stitch choices cleanly.
- Verify 2LT + AQ9 + Jet Black shows that additional stitch choices are available.
- Verify 3LT + AH2 and 3LT + AE4 expose the full grouped set from Issue 13.
- Verify 3LT + AUP shows only the two asymmetrical choices.
- Select final interiors from one-choice and multi-choice groups and confirm summary/export still reports the final selected interior.
- Verify an R6X-related interior path without D30 keeps R6X priced at $995, and a D30-triggered path prices R6X at $0.
- Check desktop and mobile widths for no overlapping text, no horizontal overflow, and readable long labels.
