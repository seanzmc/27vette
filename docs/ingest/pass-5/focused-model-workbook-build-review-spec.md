# Pass 5 — Focused model ingest and workbook-build review

Date: 2026-06-28
Branch: `ingest-wizard`
Status: Spec only. Do not implement until approved.
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

Implementation may also support a durable selection artifact:

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
  }
}
```

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
  --raw-export "2027 Chevrolet Car Corvette Export_RAW.xlsx" \
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

## Approval question

Approve Pass 5 implementation as scoped above: a read-only focused-model ingest pass that selects ZR1/ZR1X plus one comparator immediately after Pass 0 header/model profiling, filters later ingest stages to that scope, replaces abstract review decisions with workbook-destination actions, and keeps workbook/generated/runtime/dealer surfaces untouched?

Recommended approval: yes. This is the smallest safe correction before any apply planning, and it addresses the actual usability failure found during Pass 4 review.
