# Workbook Copy, Display Order, And Visual Polish Spec

> Spec only. Do not implement in this pass. Standardize workbook-owned option names, descriptions, and display order across Stingray and Grand Sport, and refine the recent visual grouping/tooltip UI based on customer-facing feedback.

## Diagnosis

The current app is functionally working, but the presentation still has two distinct sources of inconsistency:

1. Workbook-owned option copy and display order differ between `stingray_options` and `grandSport_options` for shared RPOs.
2. The recent grouped-choice UI is useful but visually too loud and has copy/tooltips that feel too internal or too busy.

Evidence from current workbook inspection:

- Both source sheets use the same relevant headers: `option_id`, `rpo`, `price`, `option_name`, `description`, `detail_raw`, `section_id`, `selectable`, `display_order`, `active`, `display_behavior`.
- Shared RPO `CF7` differs between models:
  - `stingray_options`: `opt_cf7_001`, `option_name = Body-Color Removable Roof Panel`, `description = blank`, `section_id = sec_roof_001`, `display_order = 10`.
  - `grandSport_options`: `opt_cf7_001`, `option_name = Body-Color Roof Panel`, `description = Removable`, `section_id = sec_roof_001`, `display_order = 10`.
  - `grandSport_options` inactive mirror row `opt_cf7_002` says `Removable Body-Color Roof Panel`, while Stingray inactive mirror row says `Body-Color Removable Roof Panel`.
- Engine appearance shared selections have divergent display order:
  - Stingray: `BC7 = 10`, `BCP = 20`, `BCS = 30`, `BC4 = 40`.
  - Grand Sport: `BC7 = 20`, `BCP = 25`, `BCS = 26`, `BC4 = 27`.
- Engine appearance descriptions also vary for shared RPOs:
  - Stingray `BCP` and `BCS`: `Includes engine lighting`.
  - Grand Sport `BCP` and `BCS`: blank.
  - Stingray `BC4`: `New for 2027. Includes engine lighting`.
  - Grand Sport `BC4`: `New for 2027.`
- Runtime currently renders section labels from `section.selection_mode_label` through `renderModeLabel(section)` in `form-app/app.js`.
- Current selection-mode labels are technically friendly enough to avoid underscores, but still read as system copy, e.g. `Required single choice`, `Optional multiple choice`.
- Recent runtime helper `relationshipBadgesForChoice()` currently builds include badge tooltip copy as `Workbook includes: ...`, which exposes internal workbook terminology to customers.
- Recent include badges currently use `renderInfoTooltip(... icon: true)`, so the include pill has a separate info icon instead of behaving like the `Unavailable` pill where the whole pill is the hover/focus target.
- Recent related-choice group markup currently includes:
  - eyebrow `Related choices`,
  - title text such as `Choose one of these related options` / `Choose one required option`,
  - optional group note,
  - count pill such as `4 options`.
- Recent selected-RPO summary section headings include section totals, which adds visual noise in a sidebar already showing total pricing.

Root cause:

- Shared option rows were authored/model-migrated independently, so small naming, description, and display-order drift accumulated in workbook source sheets.
- The runtime visual pass correctly surfaced relationships but used internal phrasing and multiple simultaneous visual treatments: group tint, accent borders, badges, notes, count pills, and section totals.

Risk level: medium-high for workbook copy/display-order changes, medium for runtime visual polish.

- Workbook edits affect generated workbook sheets, generated app data, selected RPO ordering, option card ordering, downloaded builds, and dealer-visible summaries.
- Runtime polish should be presentation-only, but it touches shared tooltip and badge rendering used across both models.

Change type: mixed data and UI presentation.

- Data-only for workbook copy/display-order standardization.
- Styling/UI-only for recent visual group and tooltip refinements.
- No intended business-rule, pricing, compatibility, export schema, or dealer-submission behavior changes.

## Goals

1. Standardize shared option names between `stingray_options` and `grandSport_options` where the same RPO represents the same customer-facing choice.
2. Standardize shared option descriptions/details when the underlying customer-facing fact is the same.
3. Standardize display order of similar/shared choices across models, especially sections where both models expose the same selection set.
4. Keep the workbook as the source of truth for option names, descriptions, details, and display order.
5. Refine the recent visual grouping UI to feel calmer and more customer-friendly.
6. Remove internal language from include tooltips.
7. Make include pills behave like existing state pills: whole-pill hover/focus, no nested icon, mobile/click support through existing tooltip binding.
8. Make selected-RPO summary less busy by removing per-section totals.

## Exact Files To Change

### `stingray_master.xlsx`

Expected source sheets to edit:

- `stingray_options`
- `grandSport_options`

The first implementation pass should focus on obvious, safe, shared option rows only. It should not attempt a full workbook rewrite in one step.

Initial candidate rows to inspect and likely standardize:

- `CF7` roof panel copy:
  - active rows in `sec_roof_001`
  - inactive mirror rows in `sec_stan_002` if they still feed evidence/tests or generated standard equipment metadata
- Engine appearance LS6 cover names/descriptions/order:
  - Stingray: `opt_bc7_001`, `opt_bcp_001`, `opt_bcs_001`, `opt_bc4_001`
  - Grand Sport: `opt_bc7_001`, `opt_bcp_002`, `opt_bcs_002`, `opt_bc4_002`
- Any additional shared RPOs found by audit where:
  - same `rpo`, same or equivalent `section_id`, active in both models,
  - customer-facing `option_name` differs only by wording/casing/order,
  - `description` differs only by missing duplicated customer-facing facts,
  - `display_order` differs without a clear model-specific reason.

Workbook edit constraints:

- Do not edit generated `form_*` sheets directly.
- Use a workbook-writing script or one-off Python command that imports `save_workbook_safely()` from `scripts/corvette_form_generator/workbook.py`.
- Refuse to save if `~$stingray_master.xlsx` exists.
- Verify saved headers/cells on disk after writing.

### `form-app/app.js`

Presentation refinements only.

Required changes:

1. Include badge tooltip copy:
   - Remove `Workbook includes:` and `Workbook-defined included items.` from customer-facing tooltip text.
   - Tooltip content should be a structured list of included RPOs/labels, e.g. `FE3 Z51 Performance Suspension`, `G0K Rear Axle 5.56 Ratio`.
   - Keep generic source data: use `ruleTargetsBySource`, `rule_type === "includes"`, `ruleAppliesToCurrentVariant(rule)`, and `getEntityLabel(rule.target_id)`.
   - No model-specific package/RPO branches.

2. Include badge behavior:
   - Make the entire `Includes N items` pill the tooltip trigger.
   - Do not render a separate info icon inside the include pill.
   - Pattern should match `renderStatePill()` behavior used for `Unavailable`: text trigger plus tooltip panel.
   - Ensure existing `bindTooltips()` click/touch behavior still applies for mobile.

3. Include badge disabled styling:
   - When the parent card is disabled or auto-added/locked, the include pill should receive a disabled/deactivated class so it visually belongs to the disabled card.
   - Do not make the include pill look like an error; it should appear muted/deactivated when the card is disabled.

4. Unavailable pill contrast:
   - Keep the pill interactive-looking, but make the normal text color slightly darker than the current warning color treatment if needed for readability.
   - Preserve hover/focus color inversion.

5. Related-choice group copy:
   - Remove extra heading copy that implies required selection, specifically `Choose one of these related options` and `Choose one required option`.
   - Keep a subtler label such as `Related options` or no group title beyond the section-level label.
   - Do not expose `group_id` or raw internal terminology to customers.

6. Related-choice count:
   - Remove the `N options` count pill from each relation group.

7. Section mode copy:
   - Make section selection-mode text more customer-friendly in runtime display.
   - Examples to evaluate:
     - `Required single choice` -> `Choose one`
     - `Optional single choice` -> `Choose up to one`
     - `Optional multiple choice` -> `Choose any that apply`
   - Prefer a runtime display mapping only if this is purely presentation text and generated data should remain unchanged. If the workbook already owns `selection_mode_label` and the team wants these labels durable, move the copy change to workbook metadata instead and regenerate.
   - Do not change the underlying `selection_mode` values or behavior.

8. Selected RPO section headings:
   - Remove per-section dollar totals from `summary-section-heading`.
   - Keep section labels only.
   - Keep each row price and overall summary totals.

### `form-app/styles.css`

Required changes:

1. Related-choice group styling:
   - Reduce visual loudness.
   - Use subtler border/background than current pink gradient and heavy accent treatment.
   - Preserve a clear grouping affordance, but avoid competing with selected/disabled card states.
   - Consider a neutral background with a fine left accent rule or a simple inset border.

2. Include pill styling:
   - Add whole-pill tooltip styling similar to `.choice-state.info-tooltip`.
   - Remove nested info icon styling for include pills.
   - Add disabled/deactivated include pill variant for disabled cards.

3. Unavailable pill styling:
   - Darken normal text color enough to communicate interactivity and readability.
   - Preserve hover/focus inversion and accessibility contrast.

4. Summary section heading styling:
   - Update layout after removing section totals.
   - Keep section headings compact and scannable.

### `tests/multi-model-runtime-switching.test.mjs`

Add/adjust focused tests for runtime visual behavior:

- Include badge tooltip does not contain `Workbook includes` or `Workbook-defined`.
- Include badge renders as a whole-pill tooltip trigger with no nested info icon.
- Include badge tooltip includes structured RPO/label list text from included rules.
- Disabled choice with include badge receives a disabled/deactivated include badge class.
- Related-choice group markup no longer contains `Choose one of these related options`, `Choose one required option`, or the count pill.
- Section mode display maps to customer-friendly copy in rendered section headers.
- Selected RPO section headings do not include per-section dollar totals.

### `tests/stingray-form-regression.test.mjs`

Add/adjust tests if workbook copy/display-order changes affect existing Stingray expectations:

- Shared option copy expectations for the initial standardized RPO set.
- Engine appearance order expectations if currently covered by existing tests.
- Section mode label expectations if changed in generated data instead of runtime display mapping.

### Grand Sport tests

Potentially update or add assertions in one of:

- `tests/grand-sport-draft-data.test.mjs`
- `tests/multi-model-runtime-switching.test.mjs`

Use these to verify Grand Sport shared option copy/order standardization when generated data changes.

### Optional one-off script under `scripts/` or `scripts/migrations/`

If more than a couple workbook cells are edited, create a focused migration script rather than ad hoc manual edits. Requirements:

- Use `.venv/bin/python`.
- Import `save_workbook_safely()`.
- Verify lock file absence.
- Print a compact before/after summary of changed cells.
- Be safe to delete after use unless the team wants durable migration history.

## Constraints

- Visual preservation: calm the recent UI without redesigning the entire app.
- No refactor: do not reorganize runtime architecture or generator architecture.
- No new dependencies.
- Workbook source of truth: option names, descriptions, details, and display order should be corrected in workbook source sheets, not patched in JavaScript.
- No hardcoded model-specific business logic in runtime or generators.
- Do not alter selection behavior, compatibility rules, auto-add behavior, pricing, standard equipment derivation, export schema, dealer submission endpoint, payload shape, or Turnstile behavior.
- Do not manually edit generated `form_*` sheets.
- Do not run workbook-writing scripts while Excel has `stingray_master.xlsx` open.
- Do not ignore `~$stingray_master.xlsx`; if present, stop and confirm Excel is closed/stale before proceeding.
- Keep active/inactive source rows intentional. If changing inactive mirror rows, explain whether they feed standard-equipment evidence or only maintain copy consistency.
- Do not bulk-normalize descriptions where model-specific truth differs.
- Use evidence before changing copy: compare `option_name`, `description`, `detail_raw`, `section_id`, `price`, `active`, and downstream generated output.

## Proposed Implementation Plan

### Phase 1: Runtime visual polish from recent grouped-choice feedback

1. Add failing tests for include badge tooltip copy/markup.
2. Add failing tests for related-group copy/count removal.
3. Add failing tests for selected-RPO heading totals removal.
4. Implement minimal `form-app/app.js` changes.
5. Implement minimal `form-app/styles.css` changes.
6. Run targeted runtime tests.
7. Browser-check the grouped-choice and selected-RPO layouts.

### Phase 2: Workbook audit report for shared option copy/order

1. Write an audit script or one-off read-only Python report that compares active rows across `stingray_options` and `grandSport_options` by shared `rpo` and compatible `section_id`.
2. Report mismatches in:
   - `option_name`
   - `description`
   - `detail_raw`
   - `display_order`
   - active/selectable/display behavior if relevant
3. Separate mismatches into:
   - safe obvious wording drift,
   - likely model-specific differences,
   - needs human decision.
4. Review audit output before writing workbook cells.

### Phase 3: First workbook standardization batch

1. Confirm Excel is closed and no workbook lock file exists.
2. Write failing tests for the approved first batch, likely including:
   - `CF7` option name consistency.
   - Engine appearance `BC7/BCP/BCS/BC4` order consistency.
   - Engine appearance customer-facing descriptions, if approved as truly shared facts.
3. Use a safe workbook migration script to update source cells only in `stingray_options` and/or `grandSport_options`.
4. Save through `save_workbook_safely()`.
5. Verify workbook cells on disk with `openpyxl`.
6. Regenerate affected artifacts.
7. Run targeted tests and inspect generated diffs.

## Risks And Mitigations

- Risk: Same RPO does not always mean same customer-facing truth across models.
  - Mitigation: audit `detail_raw`, section, pricing, active status, and model context before standardizing.

- Risk: Changing display order may alter customer expectations or existing regression fixtures.
  - Mitigation: start with sections where both models expose the same choices and there is no model-specific ordering reason, e.g. LS6 engine covers.

- Risk: Workbook writes could corrupt or race with Excel.
  - Mitigation: use `save_workbook_safely()`, lock-file checks, package validation, and on-disk verification.

- Risk: Runtime text mapping could conflict with workbook-owned presentation labels.
  - Mitigation: decide explicitly whether section-mode copy belongs in workbook metadata or runtime presentation; do not maintain duplicate conflicting sources.

- Risk: Include badge tooltip may become too terse if only codes are listed.
  - Mitigation: use `getEntityLabel()` so each bullet has RPO plus label.

- Risk: Calming relation-group styling could make relationships too subtle.
  - Mitigation: keep a clear but quiet border/left accent and preserve badges on individual cards.

## Non-Goals

- No full workbook copy rewrite in one batch.
- No automated rewriting of all descriptions without review.
- No generator hardcoding to mask workbook copy differences.
- No runtime copy overrides for option names/descriptions/display order.
- No changes to business rules, pricing, selected/default logic, or model availability.
- No changes to dealer submission or export schema.
- No new app framework/build system.

## Validation Plan

Runtime visual polish gates:

```sh
node --test tests/multi-model-runtime-switching.test.mjs
node --test tests/stingray-form-regression.test.mjs
```

Workbook copy/display-order gates after source edits:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/generate_stingray_form.py
.venv/bin/python scripts/generate_grand_sport_form.py
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/grand-sport-rule-audit.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Manual verification:

1. Serve the app locally:

```sh
cd /Users/seandm/Projects/27vette-schema-standardization/form-app
../.venv/bin/python -m http.server 8000
```

2. Verify Stingray and Grand Sport:
   - engine appearance option order,
   - roof panel option copy,
   - selected-RPO summary order/copy,
   - option card copy/descriptions,
   - include pill tooltip behavior on desktop and mobile widths,
   - unavailable pill contrast and hover/focus behavior,
   - related-choice boxes are visually calmer.

3. Verify downloaded build still matches selected options and section order.
4. Verify dealer submission modal still opens and validates unchanged.

## Approval Gate

Implementation should wait for approval. Recommended first approved slice:

1. Runtime visual polish only:
   - `form-app/app.js`
   - `form-app/styles.css`
   - `tests/multi-model-runtime-switching.test.mjs`
   - optionally `tests/stingray-form-regression.test.mjs`

Then a second approval/checkpoint for workbook edits after the shared-option audit report is reviewed.
