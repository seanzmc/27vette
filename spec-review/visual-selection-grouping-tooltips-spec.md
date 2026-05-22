# Visual Selection Grouping And Tooltip Formatting Spec

> Spec only. Do not implement in this pass. Improve the static order-form app presentation for selected RPOs, visually related option groups, and long package/tooltips while preserving workbook-owned business rules and all identifying keys.

## Diagnosis

The app logic is working, but three visual patterns make the customer experience harder than it needs to be:

1. The sidebar `Selected RPOs` list is a flat list, while the exported build already has a more customer-friendly sectioned structure.
2. Mutually exclusive options and package-related choices are visually indistinguishable from unrelated choices until the user interacts with them.
3. Long package descriptions/tooltips are rendered as plain paragraphs, so includes lists like `(SB7) ... and (VWD) ...` become a dense code-heavy sentence for lay users.

Evidence:

- `form-app/index.html:78-86` defines the summary sidebar as flat `#selectedList` and `#autoList` unordered lists.
- `form-app/app.js:1760-1767` renders `selectedItems` and `autoItems` as ungrouped `<li><strong>RPO</strong> label - price</li>` entries.
- `form-app/app.js:1854-1891` already builds sectioned order recap data through `sectionedOrderRecap(items, pricing)` for export/submission.
- `form-app/app.js:1937-1968` uses the sectioned order shape in `compactOrder()`.
- `form-app/app.js:2011-2035` exports the downloaded Markdown by section, which is closer to the desired selected-RPO presentation.
- `form-app/app.js:188-192` indexes `data.exclusiveGroups` by option, and `form-app/app.js:1032-1069` contains generic exclusive-group helpers. These can drive visual grouping without changing group IDs or behavior.
- `form-app/data.js` generated data includes `exclusiveGroups[].group_id`, `selection_mode`, `option_ids`, and `notes`; examples from current generated data include `grp_ls6_engine_covers`, `excl_center_caps`, `gs_excl_center_caps`, and required-single groups such as `gs_excl_performance_brakes`.
- `form-app/app.js:553-668` and `form-app/app.js:871-889` already use `rules` and `computeAutoAdded()` for package includes and auto-added items. Package relationships can be surfaced visually from the same generic rule data instead of adding product-specific code.
- `form-app/app.js:218-229` currently escapes tooltip content and renders it as a single text node inside `.tooltip-panel`.
- `form-app/app.js:1333-1352` passes `choice.description` or `choice.status_label` to `renderInfoTooltip()` for option details.
- `form-app/styles.css:772-785` styles all summary-list items uniformly.
- `form-app/styles.css:856-880` caps tooltip width at `min(280px, 72vw)` and styles tooltip content as one compact text block.
- Existing tests in `tests/multi-model-runtime-switching.test.mjs:412-503` already verify exclusive-group data and behavior for both models; new visual tests should build on those runtime seams.

Root cause: the runtime has enough generated data to present relationships clearly, but the rendering layer treats each choice and selected item independently. The tooltip renderer also only supports plain text, so structured package information cannot breathe visually.

Risk level: medium. This is mostly presentation-only, but it touches shared render helpers used across both Stingray and Grand Sport, and the selected summary is adjacent to dealer submission/export data. The implementation must avoid changing selection logic, pricing, generated data contracts, or submission/export payloads.

Change type: mixed UI behavior and styling only. No workbook source-data, generator, pricing, compatibility, export schema, or dealer-submission behavior should change.

## Goals

1. Make the in-app `Selected RPOs` sidebar feel like the downloaded/exported build: sectioned, scannable, and priced.
2. Give customers a visual cue before interaction when choices are related:
   - single-choice/mutually exclusive groups,
   - required single-choice groups,
   - packages that include sub-items or auto-add related RPOs.
3. Keep all internal terminology and keys unchanged: no renaming `exclusiveGroups`, `ruleGroups`, `choice groups`, `group_id`, `option_id`, or generated data fields.
4. Make long package/tooltips customer-friendly by detecting RPO-code patterns and formatting them into structured bullet lists when useful.
5. Preserve the current static app architecture, current visual brand direction, and all business behavior.

## Exact Files To Change

### `form-app/app.js`

Modify runtime rendering helpers only.

Required changes:

1. Add a generic summary renderer for selected items that reuses the same sectioning concepts as export:
   - Use `lineItems()`, `sectionedOrderRecap(items, pricing)`, `orderSummarySections()`, and existing `section_key` / `section_label` fields.
   - Render `#selectedList` as sectioned groups instead of one flat list.
   - Keep auto-added RPOs in `#autoList`, but apply the same row layout so selected and auto-added items look related.
   - Include clear columns/regions for RPO, label, and price.
   - Keep the existing empty states: `No selections yet.` and `No auto-added RPOs.`
   - Do not change `currentOrder()`, `compactOrder()`, `buildMarkdown()`, `plainTextOrderSummary()`, `exportCsv()`, or `dealerSubmissionPayload()` except if a helper extraction is needed with identical output.

2. Add generic relationship metadata helpers for choice cards:
   - `relationshipBadgeForChoice(choice)` or equivalent.
   - For exclusive groups, use `optionExclusiveGroup(choice.option_id)` and `exclusiveGroupAllowsSingleSelection()` / `exclusiveGroupRequiresSelection()`.
   - Badge copy should be customer-friendly, not internal: e.g. `Choose one`, `Required choice`, `Related options`.
   - Preserve internal keys in data attributes only if needed for tests/debugging, e.g. `data-exclusive-group="grp_ls6_engine_covers"`; do not show raw group IDs to customers.
   - For package/include relationships, inspect active `rules` where `rule_type === "includes"`, `source_id === choice.option_id`, and `ruleAppliesToCurrentVariant(rule)`.
   - Surface a concise package indicator such as `Includes 3 items` and optionally an expandable/tooltip list of included RPO labels from `getEntityLabel(rule.target_id)`.
   - Do not create model-specific branches for Z51, Z52, B6P, PDV, or any other RPO.

3. Render visual option groups within each section before mapping to cards:
   - In `renderStepContent()` around `form-app/app.js:1681-1694`, group choices inside a section when they share an active exclusive group.
   - Keep original workbook/source display order inside and outside groups.
   - Avoid duplicating a choice if it belongs to a group.
   - Render grouped choices inside a wrapper such as `.choice-relation-group` with a small header/eyebrow.
   - Header should describe the relationship in customer language using `selection_mode`:
     - `single_within_group`: `Choose one of these related options`.
     - `required_single_within_group`: `Choose one required option`.
   - Use `group.notes` only as optional helper text when it is customer-safe; never require notes to exist.
   - Non-grouped choices remain in the normal `.choice-grid`.

4. Add structured tooltip rendering while preserving escaping and accessibility:
   - Replace the current plain-text-only `renderInfoTooltip(content, ...)` internals with a helper that can render safe structured HTML.
   - Keep `aria-label` as readable plain text.
   - Add a parser such as `formatTooltipContent(content)` that:
     - leaves short/simple text unchanged,
     - only switches to structured mode above a conservative threshold, e.g. 120-140 characters or 3+ RPO-code matches,
     - detects RPO patterns like `(XXX)` / `(XXXX)` using a generic regex such as `/\(([A-Z0-9]{2,4})\)/g`,
     - splits `Includes ...` text into a lead sentence and bullet rows where each bullet starts with the code and associated phrase,
     - preserves remaining description text before or after the detected includes list,
     - safely escapes every text fragment before insertion.
   - The parser must be generic and tolerate descriptions without `Includes`, without codes, or with parenthetical text that is not an RPO.
   - Structured tooltip markup should be usable for option details, auto-added reasons, disabled reasons, and standard-equipment details without breaking existing simple tooltips.

5. Expose any new pure helpers in the `window.__testApi` injection used by `tests/multi-model-runtime-switching.test.mjs` only if tests need direct access.

Do not change:

- `handleChoice()`, `handleInterior()`, `handleContextChoice()`.
- `computeAutoAdded()` semantics.
- `disableReasonForChoice()` semantics.
- `removeOtherExclusiveGroupOptions()` semantics.
- Price calculations or `lineItems()` output.
- Export, CSV, Markdown, or dealer submission payload shape.

### `form-app/styles.css`

Add presentation styles for the new summary, relation-group, badge, and tooltip structures.

Required changes:

1. Sectioned selected-RPO summary:
   - Style `#selectedList` section wrappers compactly inside `.summary-card`.
   - Use a scannable row layout: RPO pill/code, label, right-aligned price.
   - Show section headers similar to export sections but sized for sidebar use.
   - Keep readable mobile behavior inside the existing summary drawer.

2. Related choice groups:
   - Add `.choice-relation-group` wrapper styling that visually groups related cards without making the section look heavy.
   - Recommended direction: subtle tinted background, thin accent border, rounded corners, compact header, and the normal `.choice-grid` nested inside.
   - Add `.choice-relation-heading`, `.choice-relation-title`, `.choice-relation-note`, and/or `.choice-relation-count` as needed.
   - Preserve card hover/selected/disabled visual states inside groups.
   - Ensure grouped cards still align with ungrouped cards and do not create horizontal overflow.

3. Relationship badges on cards:
   - Add a subtle badge style near the top or bottom of `.choice-card`, distinct from disabled/auto-added state pills.
   - Use neutral/accent styling for `Choose one` and package `Includes N` indicators.
   - Do not make badges look like selected/disabled states.

4. Structured tooltips:
   - Increase tooltip max width enough for bullet readability, e.g. `min(360px, 82vw)`, while preserving viewport positioning from `positionTooltip()`.
   - Add styles for `.tooltip-content`, `.tooltip-lead`, `.tooltip-list`, `.tooltip-list li`, `.tooltip-code`, and `.tooltip-tail` or equivalent.
   - Keep color contrast accessible on the current dark tooltip background.
   - Ensure keyboard/focus behavior is unchanged.

5. Preserve existing desktop/mobile shell behavior introduced by the current app. Do not undo the mobile summary drawer/progress layout.

### `tests/multi-model-runtime-switching.test.mjs`

Add focused runtime tests using the existing `loadRuntime()` seam.

Required test coverage:

1. Summary renderer:
   - After selecting a variant and options, `renderSummary()` output for `#selectedList` contains section headings matching exported `compactOrder().sections` or `currentOrder().sections` labels.
   - Selected rows include separate RPO, label, and price regions/classes.
   - Auto-added list still renders auto-added reason tooltips and remains separate from selected list.

2. Exclusive group visual metadata:
   - Rendering a known Stingray exclusive group option such as `grp_ls6_engine_covers` includes a customer-facing `Choose one` or related badge and a non-customer-facing data marker if implemented.
   - Rendering a known Grand Sport required exclusive group option such as `gs_excl_performance_brakes` includes a `Required choice`/`Choose one required option` visual cue.
   - Existing exclusive group behavior tests must remain unchanged.

3. Grouped section markup:
   - Rendering a step/section containing multiple exclusive-group peers emits a `.choice-relation-group` wrapper once and preserves the peer option IDs.
   - Non-grouped choices still render as ordinary `.choice-card` entries.

4. Structured tooltip parser:
   - A long includes description like `LPO. Includes (SB7) Corvette Racing Themed Graphics Package ... and (VWD) Stingray R logo wheel center caps. Genuine Corvette Accessory.` renders a structured list with `SB7` and `VWD` bullets.
   - Simple tooltip strings still render as plain escaped text.
   - Malicious-looking strings are escaped; no raw HTML injection is possible.

### `tests/stingray-form-regression.test.mjs`

Add or update assertions only if this file already owns broad summary/download regression expectations that need to reflect the new visual markup. Otherwise prefer keeping the new visual tests in `tests/multi-model-runtime-switching.test.mjs` where the runtime helper seam is already robust.

### `form-app/index.html`

No structural changes are expected. Only touch this file if implementation proves a semantic wrapper is needed for accessibility. If touched, preserve IDs used by the runtime:

- `#selectedList`
- `#selectedStandardEquipmentList`
- `#autoList`
- `#summaryDrawer`
- all dealer submission IDs and Turnstile markup

## Constraints

- Visual preservation: keep the current brand palette, card design, static-app feel, and desktop/mobile shell. Improve hierarchy and scanability rather than redesigning the whole app.
- No refactor: do not reorganize the runtime into modules, add a framework, add a build step, or broadly rename helpers.
- No new dependencies.
- Workbook source of truth: do not move business rules into hardcoded JavaScript. Use existing generated `rules`, `ruleGroups`, `exclusiveGroups`, `sections`, `choices`, and order-summary metadata generically.
- Do not change identifying keys or generated data field names: preserve `exclusiveGroups`, `ruleGroups`, `group_id`, `selection_mode`, `option_ids`, `option_id`, `rpo`, and source workbook IDs.
- Do not change app behavior: selections, mutual exclusion, auto-add, requires/excludes validation, pricing, standard equipment, build download, and dealer submission must remain functionally identical.
- Do not change dealer submission endpoint, payload shape, Turnstile behavior, or confirmation flow.
- Do not edit `stingray_master.xlsx` or generated `form_*` sheets for this visual pass.
- Do not regenerate app data unless implementation unexpectedly reveals a stale generated artifact; if data is regenerated, stop and review scope before proceeding.

## Proposed Implementation Plan

1. Add tests for structured tooltip formatting as pure helper expectations.
2. Implement the safe tooltip formatter and update `renderInfoTooltip()` / `renderStatePill()` to use it while preserving plain-text `aria-label`.
3. Add tests for card-level relationship badges using known Stingray and Grand Sport choices.
4. Implement generic exclusive-group and include-count badge helpers; render badges in `renderChoiceCard()`.
5. Add tests for grouped step markup within a section.
6. Update the `renderStepContent()` section rendering path to group active exclusive-group peers in wrappers while preserving order and ungrouped choices.
7. Add tests for selected-RPO summary sectioning and row classes.
8. Replace flat `#selectedList` rendering in `renderSummary()` with a sectioned selected-summary helper based on existing order sectioning; style `#autoList` rows similarly.
9. Add CSS for sectioned summary rows, relation groups, relationship badges, and structured tooltips.
10. Run targeted tests, then manually verify desktop and mobile layouts.

## Risks And Mitigations

- Risk: grouped wrappers could disturb display order in long accessory sections.
  - Mitigation: preserve the first peer's original position as the group insertion point and sort grouped peers by existing `display_order` / label only.

- Risk: group wrappers could make large accessory sections feel even longer.
  - Mitigation: keep group headers compact and visually subtle; group only active groups with 2+ visible peers in the current section.

- Risk: package include badges could imply all included items are currently selectable or visible.
  - Mitigation: count only active rules that apply to the current variant; label as `Includes N` and use tooltip copy that says these are workbook-defined included items.

- Risk: tooltip parser could split normal prose incorrectly.
  - Mitigation: only structure content above the threshold and with multiple valid RPO-code matches, and fall back to escaped plain text when parsing confidence is low.

- Risk: wider tooltips could overflow small screens.
  - Mitigation: retain `positionTooltip()` viewport clamping and set CSS `max-width: min(360px, 82vw)` with wrapping bullets.

- Risk: summary visual changes accidentally affect export/submission data.
  - Mitigation: do not change `currentOrder()`, `compactOrder()`, `buildMarkdown()`, `plainTextOrderSummary()`, `exportCsv()`, or dealer submission payload creation; add tests that compare selected summary labels to existing order sections.

## Non-Goals

- No workbook edits.
- No generator changes.
- No schema changes.
- No data cleanup of descriptions or notes.
- No model-specific hardcoding for particular RPOs/packages.
- No changes to compatibility, pricing, auto-add, required-choice, or exclusive-choice behavior.
- No changes to export file format, dealer submission payload, or live endpoint.
- No full visual redesign beyond these targeted usability improvements.

## Validation Plan

Required automated gates:

```sh
node --test tests/multi-model-runtime-switching.test.mjs
node --test tests/stingray-form-regression.test.mjs
```

If implementation touches broader runtime behavior or shared summary/export helpers, run the full current suite:

```sh
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/grand-sport-rule-audit.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Manual verification:

1. Serve the app:

```sh
cd /Users/seandm/Projects/27vette-schema-standardization/form-app
../.venv/bin/python -m http.server 8000
```

2. Open `http://localhost:8000`.
3. Verify Stingray desktop:
   - choose a trim/body style,
   - select options across paint, wheels, accessories, and package-like choices,
   - confirm `Selected RPOs` is sectioned like the downloaded build,
   - confirm selected row prices and totals still match.
4. Verify Grand Sport desktop:
   - inspect accessory sections with known exclusive groups,
   - confirm related options are visibly grouped before interaction,
   - confirm choosing one exclusive peer still clears the other peer exactly as before.
5. Verify packages/tooltips:
   - inspect package descriptions such as PDV and package-like Grand Sport choices,
   - confirm long includes text becomes readable with code bullets,
   - confirm short tooltips still look normal.
6. Verify mobile widths at 375px, 430px, and 760px:
   - no horizontal overflow,
   - grouped choices remain readable,
   - summary rows and tooltips fit in the drawer.
7. Verify exports/submission boundaries:
   - Download Build still produces the same sectioned Markdown structure.
   - Dealer submission modal still opens, validates required fields, and keeps the existing Turnstile area and endpoint behavior.

## Approval Gate

Implementation should wait for approval. If approved, implement as one focused visual-runtime pass touching only:

- `form-app/app.js`
- `form-app/styles.css`
- `tests/multi-model-runtime-switching.test.mjs`
- optionally `tests/stingray-form-regression.test.mjs`
- optionally `form-app/index.html` only if accessibility requires semantic wrapper markup
