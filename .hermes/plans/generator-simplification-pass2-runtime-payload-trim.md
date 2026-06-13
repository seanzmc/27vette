# Generator Simplification Pass 2 Spec: Runtime Payload Trim

## Diagnosis

Pass 1 removed a duplicate draft-preview build and reduced draft generator runtime without changing emitted contracts. The next safe simplification is to trim fields that are still emitted into runtime payloads even though the browser does not consume them from choice rows.

Current runtime payload issue:

- `form-app/data.js` is about 6,962,956 bytes in the current workspace.
- Parsed `window.CORVETTE_FORM_DATA` JSON is about 4,696,255 characters.
- Candidate runtime-only trim savings measured from current `form-app/data.js`:
  - `source_detail_raw`: ~356,247 JSON chars
  - choice-level `choice_mode`: ~102,349 JSON chars
  - choice-level `selection_mode`: ~156,030 JSON chars
  - choice-level `selection_mode_label`: ~199,690 JSON chars
  - combined `source_detail_raw` + choice-level mode duplicates: ~814,316 JSON chars

Evidence inspected:

- `form-app/app.js`
  - Reads section-level `selection_mode` / `choice_mode`, not choice-level copies:
    - `section.selection_mode` in required/default logic.
    - `section.choice_mode` in single-choice behavior.
    - `renderModeLabel(section)` uses `section.selection_mode_label`.
  - Reads `choice.status_label` in `renderChoiceCard()` as the fallback tooltip when `choice.description` is blank, so `status_label` is not a Pass 2 removal candidate unless runtime fallback logic is added first.
  - Reads `data.validation` to surface generated errors, so `validation` is not a Pass 2 removal candidate.
  - Reads `interior.source_note` for interior tooltips, so `interiors.source_note` is not a Pass 2 removal candidate.
  - Reads group `notes` through `customerSafeGroupNote()`, so group `notes` are not a Pass 2 removal candidate.
  - Build download and dealer submission use compact order/standard-equipment summaries, not `source_detail_raw`.

- `scripts/corvette_form_generator/registry_promotion.py`
  - `live_contract_data()` already strips draft-only fields from draft artifacts before writing clean runtime contracts.
  - It currently strips `draftMetadata`, `source_option_name`, `source_description`, `text_cleanup_notes`, and staging/review provenance fields.
  - It does not yet strip runtime-unused choice/debug fields like `source_detail_raw` or duplicated choice-level section mode fields.

- `scripts/corvette_form_generator/production.py`
  - Stingray production builds `choices` with `choice_mode`, `selection_mode`, `selection_mode_label`, and `source_detail_raw`.
  - `form-output/stingray-form-data.json` and `form-app/data.js` are emitted from the production `data` object.
  - `build_app_data_registry()` embeds the current Stingray generation plus promoted runtime-contract artifacts for other models.

- Existing tests that will need deliberate updates:
  - `tests/stingray-form-regression.test.mjs` currently asserts choice-level `selection_mode_label` exists; after this pass, that assertion should be section-level only.
  - Preview/draft tests intentionally assert `source_detail_raw` in preview/draft artifacts; those should remain unchanged because Pass 2 trims runtime payloads only.

Risk level: Medium.

Change type: mixed generator + generated runtime artifacts + tests. No workbook business-rule change. No visual styling change. No dealer-submission behavior change.

## Exact Scope

Pass 2 should trim runtime payload only. It should not refactor generator architecture beyond the minimal shared trim helper needed to keep Stingray and promoted-model runtime contracts consistent.

### Runtime fields to remove in this pass

Remove these fields from live runtime contracts and `form-app/data.js` wherever they occur in runtime data objects:

- `source_detail_raw`
- choice-level `choice_mode`
- choice-level `selection_mode`
- choice-level `selection_mode_label`

Rationale:

- `source_detail_raw` is audit/provenance/debug detail. Keep it in preview/draft/audit artifacts, but do not ship it in live runtime payload.
- Choice-level `choice_mode`, `selection_mode`, and `selection_mode_label` duplicate section-level metadata. Runtime behavior reads those values from `data.sections` by `choice.section_id`.

### Fields explicitly not removed in this pass

Do not remove:

- `choice.status_label`
  - Runtime currently uses it as fallback tooltip text in `renderChoiceCard()`.
  - A later pass can remove it only after adding/validating a generic runtime fallback from `choice.status`.

- `data.validation`
  - Runtime currently displays generated error rows from `data.validation`.

- `interiors.source_note`
  - Runtime currently uses it for interior tooltip text.

- Group `notes`
  - Runtime currently filters and displays customer-safe group notes.

- `description`, `status`, `selectable`, `active`, `display_behavior`, `base_price`, `display_order`, `standard_equipment_group_type`, image fields, rule fields, price-rule fields, default-selection rules, color overrides, order-summary metadata, or dealer payload fields.

## Files To Change

Expected code changes:

1. `scripts/corvette_form_generator/registry_promotion.py`
   - Add a clearly named runtime-trim field set for payload-only fields, separate from draft/staging provenance fields.
   - Extend `live_contract_data()` / `_strip_live_contract_provenance()` so clean runtime contracts strip:
     - `source_detail_raw`
     - `choice_mode`
     - `selection_mode`
     - `selection_mode_label`
   - Keep draft artifacts untouched.
   - Keep `assert_runtime_contract()` aligned so runtime contracts with the removed fields are treated as non-clean if appropriate.

2. `scripts/corvette_form_generator/production.py`
   - Ensure Stingray production emits the trimmed runtime data to runtime-facing artifacts consistently.
   - Preferred smallest implementation:
     - Build the full internal `data` object as today.
     - Derive `runtime_data = live_contract_data(data)` for runtime-facing JSON/app registry emit.
     - Use `runtime_data` for `form-output/stingray-form-data.json` and `build_app_data_registry(runtime_data)` unless implementation evidence shows another downstream tool requires root JSON to stay rich.
     - Keep CSV output unchanged; its field list already excludes the trim candidates except standard selected fields.
   - If retaining full `form-output/stingray-form-data.json` is necessary, document why and only trim `form-app/data.js`; otherwise prefer making root runtime JSON and app data consistent.

3. `tests/stingray-form-regression.test.mjs`
   - Replace choice-level `selection_mode_label` expectations with section-level assertions.
   - Add a runtime payload test that loads `form-app/data.js` and asserts no runtime model choice or standard-equipment row contains:
     - `source_detail_raw`
     - `choice_mode`
     - `selection_mode`
     - `selection_mode_label`
   - Add/keep assertions that section-level mode metadata remains present where needed.
   - Add/keep assertions that `status_label`, `validation`, `interiors.source_note`, and group `notes` are still available where runtime currently consumes them.

4. `tests/workbook-schema-standardization.test.mjs` or a focused runtime-contract test file
   - Extend existing provenance-leak guards to cover the newly stripped runtime fields for `form-app/data.js` and promoted runtime-contract artifacts.
   - Do not assert these fields are absent from draft/preview artifacts.

Expected generated artifact changes after implementation and regeneration:

- `form-output/stingray-form-data.json` if using the preferred consistent runtime JSON path.
- `form-app/data.js`
- `form-output/inspection/grand-sport-runtime-contract.json`
- `form-output/inspection/z06-runtime-contract.json`

Generated artifacts that should not have structural changes, except timestamps if regenerated and then restored/ignored:

- `form-output/inspection/grand-sport-contract-preview.json`
- `form-output/inspection/grand-sport-form-data-draft.json`
- `form-output/inspection/z06-contract-preview.json`
- `form-output/inspection/z06-form-data-draft.json`
- workbook source sheets
- generated workbook `form_*` sheets, except normal Stingray generator timestamp/table churn if production generation runs

## Constraints

- Preserve live browser behavior.
- Preserve visual output and styling.
- Preserve dealer submission endpoint, payload shape, modal behavior, and Turnstile behavior.
- Preserve workbook source-of-truth rules; do not move product logic into JavaScript or hardcode model/RPO exceptions.
- No new dependencies.
- No broad generator refactor in Pass 2.
- Keep rich preview/draft/audit artifacts useful for investigation; trim only runtime-facing contracts/payloads.
- Do not remove fields just because they look redundant; remove only fields proven unused by runtime and dealer/build paths.
- Do not integrate generation into the workbook editor in this pass.
- If Excel is open or `~$stingray_master.xlsx` exists, do not run the Stingray production generator until the lock condition is resolved.

## Non-Goals

- No workbook-editor `/api/generate` or post-apply generation endpoint.
- No minification of `form-app/data.js`.
- No removal of `status_label` in this pass.
- No trimming of `validation`, group `notes`, or interior `source_note`.
- No change to runtime rules, pricing, default selection, includes/excludes, interiors, color overrides, or order summaries.
- No schema/workbook cleanup.
- No performance rewrite beyond reducing emitted runtime bytes.

## Implementation Plan

1. Create or stay on a pass branch, not `main`.
   - Confirm with:
     - `git status --short --branch`
     - `git branch --show-current`

2. Add runtime-trim support in `registry_promotion.py`.
   - Keep the trim helper generic over dictionaries/lists.
   - Keep naming clear enough to distinguish:
     - draft-only provenance fields
     - runtime payload trim fields
   - Ensure `live_contract_data()` still changes draft dataset status from `draft_not_runtime_active` to `runtime_active` as before.

3. Apply the same trim to Stingray production runtime output.
   - Build full `data` for generation internals.
   - Derive `runtime_data` for root JSON/app registry emit.
   - Pass the trimmed current-generation data into `build_app_data_registry()` so all models embedded in `form-app/data.js` use the same runtime contract shape.

4. Regenerate runtime-facing artifacts.
   - Grand Sport and Z06 draft generators should update only runtime-contract artifacts structurally; preview/draft artifacts should remain structurally equivalent aside from timestamps.
   - Stingray generation should update `form-app/data.js` and, if following the preferred path, `form-output/stingray-form-data.json`.

5. Update tests.
   - Adjust obsolete choice-level mode-label assertions.
   - Add explicit absence checks for stripped fields in runtime data.
   - Add preservation checks for retained runtime-consumed fields.

6. Review diffs.
   - Confirm `source_detail_raw`, choice-level `choice_mode`, choice-level `selection_mode`, and choice-level `selection_mode_label` disappeared only from runtime-facing artifacts.
   - Confirm draft/preview artifacts still retain source evidence.
   - Confirm no workbook source data changed.

## Validation Plan

Before implementation:

```sh
git status --short --branch
test ! -e '~$stingray_master.xlsx'
```

Syntax:

```sh
.venv/bin/python -m py_compile \
  scripts/corvette_form_generator/registry_promotion.py \
  scripts/corvette_form_generator/production.py
```

Generation:

```sh
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Structural drift checks:

- Capture pre-change generated JSON from a clean HEAD temp worktree.
- After implementation, compare preview/draft artifacts against baseline with `scripts/compare-generated-contracts.mjs`; they should match ignoring timestamps.
- Compare runtime contracts/app data after stripping the approved trim fields from the baseline; no other structural differences should remain.

Targeted tests:

```sh
node --test tests/grand-sport-contract-preview.test.mjs \
  tests/grand-sport-draft-data.test.mjs \
  tests/z06-contract-preview.test.mjs \
  tests/z06-form-data-draft.test.mjs \
  tests/stingray-form-regression.test.mjs \
  tests/multi-model-runtime-switching.test.mjs
```

If generated workbook sheets or production behavior show any non-timestamp churn, also run:

```sh
node --test tests/stingray-generator-stability.test.mjs
```

Browser smoke before claiming customer-facing behavior is verified:

- Load the form with `form-app/data.js` after regeneration.
- Verify default model loads.
- Switch between promoted models in the runtime selector.
- Open several option sections and confirm single-select/multi-select behavior still works from section metadata.
- Confirm option cards with blank descriptions still show acceptable tooltip/fallback behavior from retained `status_label`.
- Confirm standard-equipment summary still renders.
- Download build and compare payload shape at a high level.
- Open dealer submission modal and confirm validation/UI behavior; do not submit a live dealer payload unless explicitly approved.

## Acceptance Criteria

- Runtime-facing payloads no longer contain `source_detail_raw`, choice-level `choice_mode`, choice-level `selection_mode`, or choice-level `selection_mode_label`.
- Preview/draft/audit artifacts still retain source evidence needed for reviews.
- `form-app/app.js` behavior is unchanged.
- `status_label`, `validation`, group `notes`, and interior `source_note` remain available because runtime consumes them today.
- Targeted Node gates pass.
- Runtime structural comparison proves the only approved data-contract differences are the removed fields and timestamps.
- Browser smoke shows no customer-facing regression.

## Approval Question

Approve Pass 2 as scoped above: trim only proven-unused runtime payload fields, keep draft/audit artifacts rich, and defer workbook-editor post-save generation plus data.js minification/status-label removal to later passes?
