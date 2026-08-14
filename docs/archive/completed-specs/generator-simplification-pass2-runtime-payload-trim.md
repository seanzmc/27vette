# Generator Simplification Pass 2 Spec: Runtime Payload Trim

> **Archive closure (2026-07-29): COMPLETED.** Implementation is present at `3d41f6b` with current path-aware trim coverage. Any trailing approval request is historical; current operator commands are owned by `README.md`. Stage C approved this completed plan for archival.

> **Execution status (2026-07-29): SUPERSEDED.** This plan records an older generator/artifact topology. Do not run its commands or treat its compatibility paths, `production.py` route, artifact types, or retired test names as current guidance. Current commands and authority are owned by `README.md` and Pass 4 Stage A of `docs/superpowers/specs/2026-07-23-validation-single-lane-active-surface-cleanup.md`. Historical evidence below is preserved verbatim pending Stage C archival.

## Diagnosis

Pass 1 now leaves the repo on a unified publication workflow: `scripts/generate_form.py --model <model>` emits a model artifact, then `scripts/generate_registry.py` is the only entry point that writes `form-app/data.js` from workbook-promoted artifacts. Pass 2 should reinforce that single path to runtime across all active models; it should not reintroduce direct app-registry writes from the Stingray production generator.

The next safe simplification is to trim fields that are still emitted into runtime-facing artifacts even though the browser does not consume them from choice rows.

Current runtime payload issue:

- `form-app/data.js` is about 6,970,313 bytes in the current workspace.
- Parsed `window.CORVETTE_FORM_DATA` JSON is about 6,970,207 characters.
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
  - `build_registry_from_artifacts()` is the current registry publication path used by `scripts/generate_registry.py`.
  - `build_registry_from_promotions()` / `load_promotion_data()` still exist as helpers/tests, but current runtime publication does not pass freshly built Stingray data directly into the registry.

- `scripts/corvette_form_generator/production.py`
  - Stingray production builds `choices` with `choice_mode`, `selection_mode`, `selection_mode_label`, and `source_detail_raw`.
  - It currently writes generated workbook `form_*` sheets, `form-output/stingray-form-data.json`, and `form-output/stingray-form-data.csv`.
  - It no longer writes `form-app/data.js`; `scripts/generate_registry.py` publishes the browser registry after model artifacts are refreshed.

- `scripts/generate_form.py`
  - Is the active single model-artifact entry point for `stingray`, `grand_sport`, and `z06`.
  - The old per-model entrypoints `scripts/generate_stingray_form.py`, `scripts/generate_grand_sport_form.py`, and `scripts/generate_z06_form.py` are absent in the current tree.

- `scripts/generate_registry.py`
  - Is the only workflow entry point that writes `form-app/data.js`.
  - Uses `build_registry_from_artifacts()` to load promoted artifacts from `model_registry_promotion`.

- `stingray_master.xlsx / model_registry_promotion`
  - `stingray` is promoted as `artifact_type=current_generation`, default model, artifact path blank, resolved to `form-output/stingray-form-data.json`.
  - `grand_sport` is promoted as `artifact_type=draft_artifact`, artifact path `form-output/inspection/grand-sport-runtime-contract.json`.
  - `z06` is promoted as `artifact_type=draft_artifact`, artifact path `form-output/inspection/z06-runtime-contract.json`.

- Existing tests that will need deliberate updates:
  - `tests/stingray-form-regression.test.mjs` currently asserts choice-level `selection_mode_label` exists; after this pass, that assertion should be section-level only.
  - `tests/workbook-schema-standardization.test.mjs` already has the live-registry provenance-leak guard and should be extended for runtime payload trim fields.
  - `tests/test_registry_promotion_metadata.py` currently treats `source_detail_raw` as acceptable runtime-contract content in at least one fixture/assertion; update that fixture to reflect runtime trimming.
  - `tests/test_schema_validation_metadata.py` currently treats `source_detail_raw` as non-leaking live-contract content; update the expected leak classification for Pass 2 runtime payload trim fields.
  - `tests/z06-runtime-promotion.test.mjs` already verifies promoted Z06 runtime data strips draft-only provenance; extend it to cover the new runtime payload trim fields if that is the most local runtime-promotion test point.
  - Preview/draft tests intentionally assert `source_detail_raw` in preview/draft artifacts; those should remain unchanged because Pass 2 trims runtime payloads only.

Risk level: Medium.

Change type: mixed generator + generated runtime artifacts + tests. No workbook business-rule change. No visual styling change. No dealer-submission behavior change.

## Exact Scope

Pass 2 should trim runtime payload only. It should not refactor generator architecture beyond the minimal shared trim helper needed to keep Stingray and promoted-model runtime contracts consistent.

The desired runtime path after this pass is:

```text
scripts/generate_form.py --model stingray
  -> generated form_* sheets + form-output/stingray-form-data.json runtime-facing artifact

scripts/generate_form.py --model grand_sport
  -> form-output/inspection/grand-sport-runtime-contract.json runtime-facing artifact

scripts/generate_form.py --model z06
  -> form-output/inspection/z06-runtime-contract.json runtime-facing artifact

scripts/generate_registry.py
  -> form-app/data.js from model_registry_promotion artifacts
```

Do not add a second app-registry publication path in `production.py`.

### Runtime fields to remove in this pass

Remove these fields from live runtime contracts and `form-app/data.js` only at the runtime payload paths proven unused by the browser:

- `source_detail_raw` from runtime `choices[]` rows and runtime `standardEquipment[]` rows.
- `choice_mode`, `selection_mode`, and `selection_mode_label` from runtime `choices[]` rows, or from another field path only after proving that path is a choice-row duplicate.

Do not implement this as a generic recursive stripper for `choice_mode`, `selection_mode`, or `selection_mode_label`. Runtime still reads section and group metadata from these keys, including:

- `section.selection_mode` in required/default logic.
- `section.choice_mode` in single-choice behavior.
- `section.selection_mode_label` through `renderModeLabel(section)`.
- `group.selection_mode` for exclusive-group behavior.

Rationale:

- `source_detail_raw` is audit/provenance/debug detail. Keep it in preview/draft/audit artifacts, but do not ship it in live runtime payload.
- Choice-level `choice_mode`, `selection_mode`, and `selection_mode_label` duplicate section-level metadata. Runtime behavior reads those values from `data.sections` by `choice.section_id`; section and exclusive-group metadata must remain intact.

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
   - Extend `live_contract_data()` / `_strip_live_contract_provenance()` with path-aware runtime payload trimming so clean runtime contracts strip:
     - `source_detail_raw` from runtime `choices[]` and `standardEquipment[]` rows.
     - `choice_mode`, `selection_mode`, and `selection_mode_label` from runtime `choices[]` rows only.
   - Preserve `choice_mode`, `selection_mode`, and `selection_mode_label` in `sections`; preserve `selection_mode` in `exclusiveGroups` and any other group/section metadata.
   - Keep draft artifacts untouched.
   - Keep `assert_runtime_contract()` aligned so promoted runtime-contract artifacts with the removed fields are treated as non-clean if appropriate.
   - If hardening `artifact_type=current_generation` validation for Stingray, do it deliberately: either standardize Stingray `dataset.status` to `runtime_active` in the emitted JSON or use a payload-clean assertion that does not accidentally require draft-artifact status fields on the legacy Stingray current-generation artifact.

2. `scripts/corvette_form_generator/production.py`
   - Ensure Stingray production emits the trimmed runtime data to runtime-facing artifacts consistently.
   - Preferred smallest implementation:
     - Build the full internal `data` object as today.
     - Derive `runtime_data = live_contract_data(data)` for the runtime-facing Stingray JSON artifact.
     - Use `runtime_data` for `form-output/stingray-form-data.json`.
     - Do not write or build `form-app/data.js` from `production.py`; `scripts/generate_registry.py` must continue to publish `form-app/data.js` from promoted artifacts.
     - Keep CSV output unchanged; its field list already excludes the trim candidates.
   - Keep generated workbook `form_*` sheets rich unless there is separate evidence to trim them. `form_choices` and `form_standard_equipment` may continue to carry workbook/debug columns because they are generated workbook artifacts, not the runtime registry payload.
   - If retaining full `form-output/stingray-form-data.json` is necessary, document why before implementation; otherwise prefer making the Stingray promoted artifact and app registry data consistent.

3. `scripts/corvette_form_generator/schema_validation.py`
   - Align live-contract leak detection with the new runtime payload trim field set so `validate_workbook_schema.py` can catch stale promoted artifacts or stale `form-app/data.js` after Pass 2.
   - Preserve the existing `app_registry_stale` behavior: after any model artifact changes, `scripts/generate_registry.py` is required before schema validation passes.

4. `tests/stingray-form-regression.test.mjs`
   - Replace choice-level `selection_mode_label` expectations with section-level assertions.
   - Add a runtime payload test that loads `form-app/data.js` and asserts no runtime model choice or standard-equipment row contains:
     - `source_detail_raw`
     - `choice_mode`
     - `selection_mode`
     - `selection_mode_label`
   - Add/keep assertions that section-level mode metadata remains present where needed.
   - Add/keep assertions that `status_label`, `validation`, `interiors.source_note`, and group `notes` are still available where runtime currently consumes them.

5. `tests/workbook-schema-standardization.test.mjs`
   - Extend existing provenance-leak guards to cover the newly stripped runtime fields for `form-app/data.js` and promoted runtime-contract artifacts.
   - Do not assert these fields are absent from draft/preview artifacts.

6. `tests/test_registry_promotion_metadata.py`
   - Update registry-promotion fixtures/assertions so clean runtime contracts do not include `source_detail_raw` or duplicated choice-level mode fields.
   - Keep coverage that `build_registry_from_artifacts()` loads `form-output/stingray-form-data.json` for Stingray and `*-runtime-contract.json` artifacts for promoted draft-derived models.

7. `tests/test_schema_validation_metadata.py`
   - Update the live-contract leak unit test to classify `source_detail_raw`, `choice_mode`, `selection_mode`, and `selection_mode_label` as runtime-payload leaks while keeping draft/provenance classifications clear.

8. `tests/z06-runtime-promotion.test.mjs` or another focused promoted-runtime test
   - Add an assertion that promoted Z06 runtime data in `form-app/data.js` is stripped of the new runtime payload fields, not just draft-only provenance.

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
- No workbook source-data cleanup or workbook schema cleanup. Extending schema validation to enforce the runtime-payload contract is in scope.
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
   - Derive `runtime_data` for the root Stingray JSON runtime-facing artifact.
   - Write `form-output/stingray-form-data.json` from `runtime_data`.
   - Leave `form-app/data.js` publication to `scripts/generate_registry.py` so all active models use the workbook-promoted artifact path.

4. Regenerate runtime-facing artifacts.
   - Grand Sport and Z06 draft generators should update only runtime-contract artifacts structurally; preview/draft artifacts should remain structurally equivalent aside from timestamps.
   - Stingray generation should update `form-output/stingray-form-data.json`; `form-app/data.js` should update only after `scripts/generate_registry.py`.

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
  scripts/corvette_form_generator/production.py \
  scripts/corvette_form_generator/schema_validation.py \
  scripts/generate_registry.py \
  scripts/generate_form.py
```

Generation:

```sh
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_registry.py
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Structural drift checks:

- Capture pre-change generated JSON from a clean HEAD temp worktree.
- After implementation, compare preview/draft artifacts against baseline with `scripts/compare-generated-contracts.mjs`; they should match ignoring timestamps.
- Compare runtime contracts/app data after stripping the approved trim fields from the baseline; no other structural differences should remain.

Targeted tests:

```sh
for t in \
  tests/stingray-form-regression.test.mjs \
  tests/stingray-generator-stability.test.mjs \
  tests/grand-sport-contract-preview.test.mjs \
  tests/grand-sport-draft-data.test.mjs \
  tests/workbook-schema-standardization.test.mjs \
  tests/z06-contract-preview.test.mjs \
  tests/z06-form-data-draft.test.mjs \
  tests/z06-runtime-promotion.test.mjs \
  tests/multi-model-runtime-switching.test.mjs
do
  node --test "$t"
done

.venv/bin/python -m pytest \
  tests/test_registry_promotion_metadata.py \
  tests/test_schema_validation_metadata.py \
  -q
```

Because Pass 2 changes generated runtime artifacts and the app registry contract, run the full current default suite before handoff:

```sh
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
for t in \
  tests/stingray-form-regression.test.mjs \
  tests/stingray-generator-stability.test.mjs \
  tests/grand-sport-contract-preview.test.mjs \
  tests/grand-sport-draft-data.test.mjs \
  tests/workbook-schema-standardization.test.mjs \
  tests/workbook-visual-copy-standardization.test.mjs \
  tests/z06-contract-preview.test.mjs \
  tests/z06-form-data-draft.test.mjs \
  tests/z06-runtime-promotion.test.mjs \
  tests/z06-interior-accessory-cleanup.test.mjs \
  tests/z06-performance-package-interactions.test.mjs \
  tests/z06-runtime-rule-corrections.test.mjs \
  tests/multi-model-runtime-switching.test.mjs
do
  node --test "$t"
done
.venv/bin/python -m pytest \
  tests/test_model_config_metadata.py \
  tests/test_registry_promotion_metadata.py \
  tests/test_schema_validation_metadata.py \
  -q
```

Do not run the optional Grand Sport audit/report block unless this pass intentionally touches `scripts/build_rule_sources.py`, `tests/grand-sport-rule-audit.test.mjs`, `tests/audit-parser-metadata-loaders.test.mjs`, or `form-output/inspection/grand-sport-rule-audit.json` / `.md`.

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
- Targeted Node and Python gates pass, followed by the full current default suite before handoff.
- Runtime structural comparison proves the only approved data-contract differences are the removed fields and timestamps.
- Browser smoke shows no customer-facing regression.

## Approval Question

Approve Pass 2 as scoped above: trim only proven-unused runtime payload fields, keep draft/audit artifacts rich, and defer workbook-editor post-save generation plus data.js minification/status-label removal to later passes?
