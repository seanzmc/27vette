# Pass 5 — Focused model ingest and workbook-build review

Date: 2026-06-28
Branch: `ingest-wizard`
Status: Implemented and closed 2026-07-02. See "Implementation closure" at the end of this file.
Recommended reasoning level for implementation agent: high.

## Purpose

Redirect the ingest wizard away from the broad all-model reduced queue and toward the actual near-term product goal: get ZR1 and ZR1X source data into a workbook-build review flow, with one comparator model for control.

Pass 5 does not write the workbook. It narrows the ingest run after source/header profiling, then presents review items as concrete workbook-building work: option rows, OVS/status rows, relationship rows, price rows, duplicate-source handling, and blocked extractor gaps.

The current Pass 4 review UI is safe, but it is too abstract for resolving new-model source data. Pass 5 must replace confusing review states such as `accept_for_later_apply`, `edit_before_apply`, `needs_source_review`, and generic confidence labels as the primary reviewer language. The reviewer should see what workbook structure needs to be built or verified.

## Diagnosis

Root cause:

- Pass 0 correctly profiles all source sheets to resolve headers and variant identifiers.
- Passes 1-4 then continue with broad all-model processing, producing a large cross-model review surface.
- The current Pass 4 UI defaults to a reduced model/RPO queue, but the queue is still not shaped around the intended task: building focused ZR1/ZR1X workbook source sheets.
- Current review language is internal pipeline language (`review_needed`, `mechanical_safe`, `accept_for_later_apply`) rather than workbook-authoring language.
- The user needs interactive, controlled testing around ZR1/ZR1X plus one comparator model, not a broad all-model queue.

Evidence inspected before writing this spec:

- `scripts/order_guide_ingest_profiler.py`
  - Pass 0 CLI has no model-selection argument; it profiles the raw export and writes all resolved evidence.
- `scripts/order_guide_candidate_normalizer.py`
  - Pass 1 CLI has no model-selection argument; it normalizes all Pass 0 evidence.
- `scripts/order_guide_ingest_interpreter.py`
  - Pass 3 CLI has no model-selection argument; it interprets all Pass 1 candidates.
- `scripts/corvette_form_generator/ingest/source_profiler.py`
  - Pass 0 resolves source headers into `variant-matrix.json` with `parsed_target_model` and matched variant metadata.
- `/tmp/27vette-pass4-evidence/variant-matrix.json` smoke evidence from the real raw export:
  - `stingray`: 30 variant columns
  - `grand_sport`: 30 variant columns
  - `z06`: 30 variant columns
  - `zr1`: 20 variant columns
  - `zr1x`: 20 variant columns
  - all 130 variant columns were `matched`.
- `stingray_master.xlsx` read-only probe of `model_workbook_sources`:
  - active rows exist for `stingray`, `grand_sport`, and `z06`.
  - `zr1` and `zr1x` rows exist as inactive scaffold source rows and must not be treated as canonical expected output.
- `visualizer/workbook-editor/editor.js`
  - current Pass 4 UI renders confidence/internal labels and decision states including `accept_for_later_apply`, `edit_before_apply`, `skip`, `needs_source_review`, and `blocked_out_of_scope`.
- `scripts/corvette_form_generator/ingest/review_payload.py`
  - current decision validation allows the same abstract states.
- `docs/ingest/pass-4/reduced-review-ui-spec.md`
  - previous next step pointed toward dry-run apply planning if the reduced queue was useful. User review proved the shape is not useful enough; this Pass 5 supersedes that next step.

Risk level: medium.

Change type for implementation: mixed tooling/UI/tests/docs, still read-only. No workbook writes, no generated runtime writes, no customer runtime behavior change.

## Corrected direction

Pass 5 must make the ingest workflow look like this:

```text
Pass 0: profile source sheets, headers, variant columns, disclosure links
  -> reviewer/CLI selects target models after header/model identification
Pass 1: normalize only selected model scope, preserving all raw evidence
Pass 3: interpret only selected model scope into workbook-destination units
Pass 4 UI: show focused workbook-build lanes, not a broad generic review queue
Later pass: dry-run apply planning only after focused ZR1/ZR1X workbook-build review is usable
```

The default development target for Pass 5 smoke should be:

```text
zr1,zr1x,z06
```

Rationale:

- `zr1` and `zr1x` are the models the user needs next.
- `z06` is the closest active LZ-family comparator and keeps the run controlled.
- The comparator is for structure and sanity checks, not for inventing ZR1/ZR1X data.

Implementation may allow a different comparator via CLI, but tests and docs should use ZR1/ZR1X plus one comparator as the main happy path.

## Exact files to change after approval

Expected implementation files:

- `scripts/order_guide_candidate_normalizer.py`
  - Add `--models` and/or `--selection-file` arguments.
- `scripts/corvette_form_generator/ingest/candidate_normalizer.py`
  - Filter Pass 0 evidence by selected model scope after variant headers have been resolved.
  - Preserve raw rows and non-selected status cells only as source context when needed, not as primary candidates.
- `scripts/order_guide_ingest_interpreter.py`
  - Add the same selected-model input support.
- `scripts/corvette_form_generator/ingest/expert_interpreter.py`
  - Filter interpretation to selected models.
  - Emit workbook-destination review units instead of only generic confidence buckets.
- `scripts/corvette_form_generator/ingest/review_payload.py`
  - Load selected-model metadata and expose workbook-build queues.
  - Replace abstract decision-state validation for the new export version with workbook-build actions.
- `scripts/workbook_editor_server.py`
  - Accept selected-model metadata/artifact input if needed.
  - Serve read-only focused queues and detail endpoints.
- `visualizer/workbook-editor/editor.js`
  - Replace the current primary Ingest Review language with focused workbook-build lanes and action labels.
  - Keep raw candidate drill-down/debug available.
- `visualizer/workbook-editor/editor.css`
  - Minimal styling for workbook-build lanes/actions if needed.
- `tests/test_order_guide_candidate_normalizer.py`
  - Add selected-model filtering tests.
- `tests/test_order_guide_ingest_interpreter.py`
  - Add focused interpretation/workbook-destination tests.
- `tests/test_ingest_review_payload.py`
  - Add export/validation tests for the new action vocabulary.
- `tests/test_editor_server_ingest_review.py`
  - Add endpoint tests proving the focused queue is default when selected-model artifacts are configured.
- `docs/ingest/pass-5/focused-model-workbook-build-review-spec.md`
  - Close this spec after implementation with exact changed files, gates, and residual risks.
- `docs/ingest/README.md`, `Order-Guide_IngestPrompt.md`, `docs/ingest/pass-2/interactive-review-wizard-spec.md`, `docs/ingest/pass-3/expert-interpretation-review-reduction-spec.md`, and `docs/ingest/pass-4/reduced-review-ui-spec.md`
  - Keep the corrected direction explicit: Pass 5 precedes dry-run apply planning.

Possible helper file, only if it keeps the change smaller and more testable:

- `scripts/corvette_form_generator/ingest/model_selection.py`
  - Shared selected-model normalization, validation, and artifact-writing helpers.

Do not refactor unrelated ingest modules.

## Required model-selection behavior

### Selection point

Pass 0 remains broad enough to identify source sheets and variant headers across the raw export. Model selection happens immediately after Pass 0 evidence exists, before Pass 1 candidate explosion.

Required input shape:

```text
--models zr1,zr1x,z06
```

Implementation must persist selection metadata as a durable artifact. `--models` is allowed as the human input, but the pipeline output must not rely on transient CLI args after Pass 1.

Required artifact:

```text
<candidate-output-dir>/model-selection.json
```

The interpreter must consume that artifact by default, copy the same selection metadata into its own output directory, and include the same selection block in `candidate-summary.json`, `interpretation-summary.json`, and `workbook-build-summary.json`.

Required minimum shape:

```json
{
  "version": 1,
  "run_id": "<run-id>",
  "selected_models": ["zr1", "zr1x", "z06"],
  "primary_models": ["zr1", "zr1x"],
  "comparator_models": ["z06"],
  "source_variant_columns": {
    "zr1": 20,
    "zr1x": 20,
    "z06": 30
  },
  "evidence_fingerprints": {
    "variant-matrix.json": "<sha256>",
    "source-layout.json": "<sha256>"
  },
  "selection_source": "cli_models_arg"
}
```

Server/UI cross-check requirement:

- Evidence, candidate, and interpretation directories must agree on selected models, primary models, comparator models, and evidence fingerprints.
- If `model-selection.json` is missing from a focused Pass 5 candidate directory, fail closed and report the missing artifact instead of falling back to broad all-model review.
- If candidate and interpretation selection metadata disagree, fail closed before showing workbook-build queues.
- If evidence fingerprints do not match the evidence directory currently served, fail closed and report the mismatched artifact names.
- The UI must display selected/primary/comparator model state from the persisted artifact, not from hardcoded defaults.

### Validation

The selected models must be validated against Pass 0 `variant-matrix.json`, not guessed from workbook scaffold rows.

Required validations:

- every selected model appears in Pass 0 `variant-matrix.json`;
- every selected model has at least one matched variant column;
- selected model names are canonical model keys;
- ZR1/ZR1X workbook scaffold rows remain inactive and are not used as expected output;
- the comparator model is clearly marked as comparator, not a source for invented ZR1/ZR1X rows.

If selected model validation fails, stop before Pass 1 and report:

- requested model key;
- available model keys from `variant-matrix.json`;
- per-model matched/unmatched variant counts;
- exact source sheets where the model did or did not appear.

## Candidate filtering contract

Pass 1 should process source rows that intersect selected model status columns.

For a raw source row:

- Keep it if at least one selected model has a relevant status cell on that row.
- Emit OVS/status candidates only for selected model variants.
- Preserve source row coordinates, raw description, orderable/ref-only RPO cells, and unfiltered source row context.
- Do not emit non-selected model OVS rows as primary candidates.
- Do not use non-selected models to create ZR1/ZR1X product facts.

Comparator model usage:

- Comparator rows may be shown for structure/reference.
- Comparator status/copy may identify sheet-shape or parser issues.
- Comparator rows must not become default ZR1/ZR1X values.

## Workbook-destination review units

Pass 3/Pass 4 review units should be organized by destination workbook surface, not generic confidence.

Pass 5 must emit a new workbook-build artifact set. These artifacts replace Pass 4 `review-queue.json` as the primary UI/API input when focused-model metadata is present; Pass 4 artifacts may remain available only as drill-down/debug.

Required artifacts in the interpretation output directory:

```text
model-selection.json
workbook-build-summary.json
workbook-build-review-units.json
```

Artifact contracts:

- `workbook-build-summary.json`
  - `version: 1`
  - `review_mode: "focused_workbook_build"`
  - embedded selection metadata from `model-selection.json`
  - artifact fingerprints for evidence, candidate, interpretation, and workbook-build unit files
  - lane counts by `option_rows`, `ovs_rows`, `relationships`, `pricing`, `duplicates_and_source_coverage`, and `blocked_extractor_gaps`
  - counts by selected model and by primary/comparator role
  - `cross_check_status` with `ok: true` only when evidence/candidate/interpretation selection metadata agrees
- `workbook-build-review-units.json`
  - array of workbook-build review units using the required unit fields below
  - every row must carry `lane`, `model_key`, `model_role` (`primary` or `comparator`), `target_workbook_surface`, and `proposed_workbook_action`
  - comparator rows must carry `model_role: "comparator"` and must not produce ZR1/ZR1X target sheets/actions

Required store methods or equivalent server-side functions:

- `selection_metadata()`
- `workbook_build_summary()`
- `list_workbook_build_units(lane=None, model=None, q=None, offset=0, limit=50)`
- `get_workbook_build_unit(review_unit_id)`
- `validate_workbook_build_decisions(payload)`

Required read-only API endpoints:

- `GET /api/ingest/workbook-build/selection`
- `GET /api/ingest/workbook-build/summary`
- `GET /api/ingest/workbook-build/units?lane=&model=&q=&offset=&limit=`
- `GET /api/ingest/workbook-build/unit/<review_unit_id>`
- `POST /api/ingest/workbook-build/validate`

These endpoints must not create workbook operations. They only serve focused review state and validate exported decisions.

Required lanes:

1. `option_rows`
   - target workbook sheet: `zr1_options`, `zr1x_options`, comparator option sheet for comparator rows
   - purpose: create or verify option identity rows.
2. `ovs_rows`
   - target workbook sheet: `zr1_ovs`, `zr1x_ovs`, comparator OVS sheet for comparator rows
   - purpose: create or verify variant availability/status matrix rows.
3. `relationships`
   - target workbook sheets: `*_rule_mapping`, `*_rule_groups`, `*_rule_group_members`, `*_exclusive_groups`, `*_exclusive_members`
   - purpose: preserve source relationship hints and decide canonical representation later.
4. `pricing`
   - target workbook fields/sheets: option price, `*_price_rules`, `PriceRef`, `interior_components`
   - purpose: isolate price rows or price gaps without pretending unsupported price extractors are ready.
5. `duplicates_and_source_coverage`
   - purpose: choose source-sheet coverage and ignore redundant source occurrences without losing evidence.
6. `blocked_extractor_gaps`
   - purpose: show Color/Trim, Price Schedule, or unsupported source structures that need a later extractor or manual source decision.

Each review unit must include:

- `review_unit_id`;
- `lane`;
- `model_key`;
- `rpo` when available;
- `target_sheet` or `target_workbook_surface`;
- `proposed_workbook_action`;
- `workbook_presence` such as `missing`, `existing_active`, `existing_inactive_scaffold`, `duplicate_existing`, or `not_applicable`;
- `required_fields_missing`;
- `source_sheets`;
- `source_refs` / row coordinates;
- `raw_source_snapshot`;
- `status_matrix_summary` for OVS work;
- `relationship_hint_summary` for relationship work;
- `comparator_context` when comparator evidence is shown.

## Replacement action vocabulary

Do not use these as primary reviewer actions in the Pass 5 UI/export:

```text
accept_for_later_apply
edit_before_apply
skip
needs_source_review
blocked_out_of_scope
mechanical_safe
review_needed
```

Allowed Pass 5 workbook-build actions should be concrete:

```text
create_option_row
verify_existing_option_row
create_ovs_rows
verify_status_matrix
create_relationship_candidate
classify_duplicate_source
defer_price_extractor
defer_color_trim_extractor
needs_product_decision
needs_source_mapping_decision
ignore_for_selected_models
blocked_unsupported_source_structure
```

Export shape should be versioned separately from Pass 4, for example:

```json
{
  "version": 3,
  "review_mode": "focused_workbook_build",
  "selected_models": ["zr1", "zr1x", "z06"],
  "primary_models": ["zr1", "zr1x"],
  "comparator_models": ["z06"],
  "selection_fingerprint": "<sha256-of-model-selection.json>",
  "artifact_fingerprints": {
    "workbook-build-summary.json": "<sha256>",
    "workbook-build-review-units.json": "<sha256>"
  },
  "decisions": [
    {
      "review_unit_id": "...",
      "lane": "option_rows",
      "model_key": "zr1",
      "rpo": "...",
      "target_sheet": "zr1_options",
      "proposed_workbook_action": "create_option_row",
      "reviewer_resolution": "approved_for_plan",
      "reviewer_notes": "..."
    }
  ]
}
```

Reviewer resolution may be simple, but must not replace the workbook action:

```text
approved_for_plan
hold_for_question
not_needed
```

The action says what workbook work is implied. The resolution says whether the reviewer accepts that unit for a later dry-run plan.

## UI requirements

The Ingest Review tab should default to focused model workflow when selected-model artifacts are configured.

Required UI behavior:

- Show selected model chips at the top: `ZR1`, `ZR1X`, comparator `Z06`.
- Show those chips only after server-side selection metadata cross-check passes; otherwise show a blocking configuration error.
- Show lane counts by workbook destination, not just confidence counts.
- Default lane should be `option_rows` or an explicit guided order starting with options.
- The first review question should be understandable without knowing pipeline internals:
  - “Create/verify option rows for ZR1/ZR1X?”
  - “Create/verify OVS rows?”
  - “Which relationship hints need canonical workbook rules?”
- Keep raw Pass 1 and Pass 3 artifacts available as drill-down/debug.
- Mark current Pass 4 confidence labels as technical detail only, not primary navigation.
- Remove or demote abstract decision labels from the primary UI.

## Step-by-step workflow to support

Pass 5 should let the user work in this order:

1. Confirm selected models and comparator.
2. Review source-sheet coverage for those models.
3. Review/build option rows.
4. Review/build OVS/status matrix rows.
5. Review relationship hints.
6. Review price/extractor gaps.
7. Export focused decisions for a later dry-run apply-planning pass.

No later step should be required to understand the first step.

## Companion-file impact check

- Workbook/source-data changes: not applicable in Pass 5; no workbook writes allowed.
- Generated runtime contracts: not applicable; `form-output/runtime/*` must remain unchanged.
- `form-app/data.js`: not applicable; must remain unchanged.
- Runtime/dealer submission: not applicable; no customer runtime or dealer payload changes.
- Ingest CLIs: update required for selected-model input and focused workbook-build artifacts.
- Workbook-editor server/UI: update required so review is shaped around selected models and workbook destinations.
- Tests: update required for selected-model filtering, focused review units, new export version/action vocabulary, and legacy label demotion.
- Docs/specs: update required; this spec and ingest docs must say Pass 5 supersedes broad reduced-queue-to-apply-planning direction.
- Gate reminders/profile/Codex guidance: inspect/update only if they steer ingest agents toward broad all-model review or immediate apply planning.

## Constraints repeated back

- No workbook writes in Pass 5.
- No generated workbook `form_*` writes.
- No tracked `form-output/runtime/*` writes.
- No `form-app/data.js` writes.
- No customer runtime behavior changes.
- No dealer submission changes.
- No model promotion changes.
- No new dependencies.
- Do not refactor the whole ingest module if a narrow selected-model filter and workbook-destination layer is enough.
- Do not treat inactive ZR1/ZR1X workbook scaffold rows as canonical expected output.
- Do not mold the parser around a one-off ZR1/ZR1X layout, but do use ZR1/ZR1X plus one comparator as the controlled development scope.
- Do not invent ZR1/ZR1X rows from Z06 or any comparator model.
- Preserve raw evidence and source coordinates.

## Risks and non-goals

Risks:

- Filtering too early could hide source rows needed for relationship context. Mitigation: filter primary candidates by selected models but preserve raw source row context and source refs.
- Comparator evidence could be mistaken for ZR1/ZR1X truth. Mitigation: every comparator field must be explicitly marked comparator-only.
- New action vocabulary could become another abstract taxonomy. Mitigation: each action must name a workbook destination and implied row/surface.
- Existing Pass 4 tests may lock old labels. Mitigation: update tests to assert the new primary vocabulary while keeping old artifact compatibility only as debug/legacy.

Non-goals:

- No workbook apply planning.
- No workbook writes.
- No ZR1/ZR1X runtime promotion.
- No full rewrite of Pass 0-4.
- No price schedule or Color/Trim extractor implementation unless narrowly needed to label blocked extractor gaps.
- No customer-facing copy cleanup.
- No use of old inactive ZR1/ZR1X workbook scaffolds as expected output.

## Validation plan

Required negative guards covered by tests:

- Missing selected model fails before Pass 1 candidate normalization and reports available model keys from `variant-matrix.json`.
- Missing `model-selection.json` fails focused workbook-build server/UI mode instead of falling back to broad all-model review.
- Candidate/interpreter selection mismatch fails closed before serving `/api/ingest/workbook-build/*` queues.
- Evidence fingerprint mismatch fails closed before serving workbook-build queues.
- Non-selected OVS rows are not emitted as primary candidates.
- Comparator evidence cannot create ZR1/ZR1X workbook-build actions or target sheets.
- Inactive ZR1/ZR1X scaffold rows are reported only as `existing_inactive_scaffold`, never as canonical expected output.
- Legacy Pass 2/4 decision labels are not accepted as Pass 5 primary workbook-build actions.

Targeted tests:

```sh
.venv/bin/python -m pytest \
  tests/test_order_guide_candidate_normalizer.py \
  tests/test_order_guide_ingest_interpreter.py \
  tests/test_ingest_review_payload.py \
  tests/test_editor_server_ingest_review.py -q
```

JavaScript syntax check:

```sh
node --check visualizer/workbook-editor/editor.js
```

Workbook/source guard:

```sh
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
git diff --exit-code -- stingray_master.xlsx form-app/data.js
git diff --exit-code -- $(git ls-files form-output)
git status --short -- form-output
```

Real raw-export smoke, using the controlled model scope:

```sh
rm -rf /tmp/27vette-pass5-evidence /tmp/27vette-pass5-candidates /tmp/27vette-pass5-interpretation
.venv/bin/python scripts/order_guide_ingest_profiler.py \
  --raw-export "<raw_export>.xlsx" \
  --workbook stingray_master.xlsx \
  --run-id pass5-smoke-evidence \
  --output-dir /tmp/27vette-pass5-evidence
.venv/bin/python scripts/order_guide_candidate_normalizer.py \
  --evidence-dir /tmp/27vette-pass5-evidence \
  --workbook stingray_master.xlsx \
  --models zr1,zr1x,z06 \
  --run-id pass5-smoke-candidates \
  --output-dir /tmp/27vette-pass5-candidates
.venv/bin/python scripts/order_guide_ingest_interpreter.py \
  --evidence-dir /tmp/27vette-pass5-evidence \
  --candidates-dir /tmp/27vette-pass5-candidates \
  --workbook stingray_master.xlsx \
  --models zr1,zr1x,z06 \
  --primary-models zr1,zr1x \
  --comparator-models z06 \
  --run-id pass5-smoke-interpretation \
  --output-dir /tmp/27vette-pass5-interpretation
```

Manual UI smoke:

```sh
.venv/bin/python scripts/workbook_editor_server.py \
  --port 8127 \
  --ingest-evidence-dir /tmp/27vette-pass5-evidence \
  --ingest-candidates-dir /tmp/27vette-pass5-candidates \
  --ingest-interpretation-dir /tmp/27vette-pass5-interpretation
```

Verify in browser:

- selected-model chips show `ZR1`, `ZR1X`, and comparator `Z06`;
- default queue is workbook-build oriented;
- first lane is option rows or a clearly guided start;
- old abstract actions are not primary UI choices;
- raw candidate drill-down still works;
- export JSON uses `version: 3` and `review_mode: focused_workbook_build`.

Stale-direction scan:

```sh
rg -n "accept_for_later_apply|edit_before_apply|needs_source_review|blocked_out_of_scope|dry-run apply planning|reduced review workflow is usable|all-model|all model" docs/ingest Order-Guide_IngestPrompt.md visualizer scripts tests
```

Any remaining hits must be either legacy compatibility/debug code or historical notes that explicitly point to Pass 5 as the current direction.

## Approval question (resolved)

Historical: this pass was approved and implemented as scoped. No approval is pending.

## Implementation closure

Closed: 2026-07-02.

### Changed files

Ingest tooling:

- `scripts/corvette_form_generator/ingest/model_selection.py` — new shared helper: `--models` parsing, ZR1/ZR1X + Z06 primary/comparator inference, selection validation against Pass 0 `variant-matrix.json` (failure reports available models, per-model matched/unmatched variant counts, and source sheets), `model-selection.json` shape validation, selection fingerprints, evidence-fingerprint assertion, and selected-model row filtering that preserves unfiltered `all_status_cells` context.
- `scripts/corvette_form_generator/ingest/candidate_normalizer.py` — accepts selected/primary/comparator models, persists `model-selection.json`, embeds `selection_metadata` in `candidate-summary.json`, and emits OVS/status candidates only for selected-model variants.
- `scripts/corvette_form_generator/ingest/expert_interpreter.py` — consumes the persisted selection by default (fails closed on missing selection or evidence-fingerprint mismatch), copies it into the interpretation output, filters interpretation to selected models, and emits `workbook-build-summary.json` (selection metadata, selection fingerprint, evidence/candidate/interpretation/unit artifact fingerprints, six-lane counts, model/role counts, cross-check status) plus `workbook-build-review-units.json` keyed by workbook-destination lanes.
- `scripts/order_guide_candidate_normalizer.py`, `scripts/order_guide_ingest_interpreter.py` — `--models`, `--primary-models`, `--comparator-models` CLI arguments.
- `scripts/corvette_form_generator/ingest/review_payload.py` — focused workbook-build store: `model_selection()`, `workbook_build_summary()`, `list_workbook_build_units()`, `workbook_build_unit()`, `validate_workbook_build_decisions()`. Fails closed when a focused run is missing `model-selection.json` or any workbook-build artifact, when candidate/interpretation selection metadata disagree, on evidence-fingerprint mismatch, and on units that leak non-selected models, mislabel comparator/primary roles, or let comparator rows target primary-model sheets. Export validation requires `version: 3`, `review_mode: focused_workbook_build`, the concrete workbook-build action vocabulary, and reviewer resolutions (`approved_for_plan`, `hold_for_question`, `not_needed`); legacy Pass 2/4 labels are rejected as Pass 5 actions and remain accepted only in the legacy raw/interpretation validators.

Server/UI:

- `scripts/workbook_editor_server.py` — read-only `GET /api/ingest/workbook-build/{selection,summary,units,unit/<id>}` and `POST /api/ingest/workbook-build/validate`; no workbook operations are created from ingest review.
- `visualizer/workbook-editor/editor.js` — Ingest Review defaults to the focused workbook-build queue with lane `option_rows` when focused artifacts are configured; selected-model chips (primary/comparator) render from the persisted selection after the server-side cross-check passes; all six lane counts and lane/action filters; guided lane questions; reviewer resolutions replace abstract decision states in the primary UI; legacy reduced-review/raw families remain available but labelled "(debug)"; export uses `version: 3` and `review_mode: focused_workbook_build`.
- `visualizer/workbook-editor/editor.css` — model-chip and lane-question styling.

Tests:

- `tests/test_order_guide_candidate_normalizer.py` — selection artifact/filtering tests plus detailed missing-model failure reporting.
- `tests/test_order_guide_ingest_interpreter.py` — focused workbook-build artifact tests, comparator role/leakage guarantees, inactive-scaffold presence (`existing_inactive_scaffold`), missing-candidate-selection and evidence-fingerprint fail-closed tests.
- `tests/test_ingest_review_payload.py` — workbook-build store/queue/validation tests, fail-closed tests for missing focused artifacts and fingerprint mismatch, comparator/non-selected leakage rejection, legacy-label rejection.
- `tests/test_editor_server_ingest_review.py` — focused endpoints default/read-only tests and export-vocabulary validation via the live server.

Docs:

- `docs/ingest/README.md`, `docs/ingest/pass-5/focused-model-workbook-build-review-spec.md` (this closure). `Order-Guide_IngestPrompt.md`, `docs/ingest/pass-2/interactive-review-wizard-spec.md`, `docs/ingest/pass-3/expert-interpretation-review-reduction-spec.md`, and `docs/ingest/pass-4/reduced-review-ui-spec.md` were inspected and already state that Pass 5 precedes dry-run apply planning — no change needed.

### Gates run (2026-07-02, all passed)

- `.venv/bin/python -m pytest tests/test_order_guide_candidate_normalizer.py tests/test_order_guide_ingest_interpreter.py tests/test_ingest_review_payload.py tests/test_editor_server_ingest_review.py -q` — 25 passed.
- `node --check visualizer/workbook-editor/editor.js` — clean.
- `.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx` — 0 errors / 0 warnings.
- `git diff --exit-code -- stingray_master.xlsx form-app/data.js` and `git diff --exit-code -- $(git ls-files form-output)` — clean; `git status --short -- form-output` — empty. No workbook, registry, or generated-runtime writes.
- Real raw-export smoke (prior 23-sheet source, `--models zr1,zr1x,z06`, `--primary-models zr1,zr1x`, `--comparator-models z06`) into `/tmp/27vette-pass5-{evidence,candidates,interpretation}`: selection persisted with zr1=20/zr1x=20/z06=30 matched variant columns; `workbook-build-summary.json` reports `focused_workbook_build`, cross-check ok, lanes option_rows=609, ovs_rows=609, relationships=221, pricing=0, duplicates_and_source_coverage=589, blocked_extractor_gaps=3; 2031 units with zero comparator/non-selected leakage; ZR1/ZR1X scaffold matches reported as `existing_inactive_scaffold` only.
- Manual browser smoke against `workbook_editor_server.py --port 8127` with the /tmp artifacts: ZR1/ZR1X primary and Z06 comparator chips, focused queue default with lane `option_rows`, six lane counts, guided lane question, reviewer-resolution decision select, raw candidate drill-down intact, decision validation round-trip ok with `version: 3` / `review_mode: focused_workbook_build`.
- Stale-direction scan (`rg` per the validation plan): remaining hits are legacy compatibility/debug code with Pass 5 notes, tests locking the legacy vocabulary for legacy families only, or historical spec notes that explicitly point to Pass 5.

### Residual risks

- The pricing lane is always 0 today because no price extractor exists; price evidence surfaces only as `blocked_extractor_gaps` (`defer_price_extractor`). A later extractor pass must populate the lane before pricing review is meaningful.
- Real-export review volume is still large (609 option-row units for three models). If reviewer sessions find the six-lane queue too big, add per-lane triage ordering before apply planning rather than reverting to abstract confidence labels.
- Comparator-leakage validation blocks comparator units targeting primary sheets by sheet-name prefix; if a future model key prefixes another (none today), tighten the check.
- Workbook-build unit files are trusted after selection/evidence fingerprints pass; unit-file tampering between generation and serving is only caught by the leakage/shape validators, not a units-file fingerprint check.

### Next step

Use the focused ZR1/ZR1X + Z06 queue in a real review session. Only after that review shape proves usable, write a separate dry-run apply-planning spec (per `Order-Guide_IngestPrompt.md`, canonical workbook writes remain a later approved pass with full AGENTS.md §5 safety). None of that is started here.
