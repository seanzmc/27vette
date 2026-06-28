# Pass 1 — CLI candidate normalizer spec

Date: 2026-06-27
Branch: `ingest-wizard-pass1-spec`
Status: Implemented 2026-06-27.
Recommended reasoning level for implementation agent: high.

## Purpose

Build a CLI-only, read-only candidate normalizer that consumes the implemented Pass 0 evidence artifacts and produces reviewable candidate artifacts.

Pass 1 must make the next step more predictable without creating another hidden staging system. It should organize raw evidence into candidate families, preserve every source reference, and mark uncertain decisions as unresolved. It must not write the workbook, generated outputs, runtime files, or app data.

## Source basis for this spec

This spec is based only on current workspace evidence:

- the implemented Pass 0 profiler files;
- the current workbook schema in `stingray_master.xlsx`;
- the current Pass 0 smoke output under `/tmp/27vette-ingest-manual-smoke`;
- the current project guardrails that keep raw ingest transient until a later approved apply pass.

The Pass 0 smoke output reported:

```text
status: passed
source_sheet_count: 23
parsed_matrix_sheet_count: 20
raw_row_count: 1964
variant_column_count: 130
disclosure_link_count: 1088
invariant_failures: []
```

Pass 0 artifact shapes available to Pass 1:

- `source-layout.json`
  - `source_sheet`
  - `sheet_type`
  - `model_label`
  - `header_row`
  - `base_columns`
  - `variant_columns`
  - `section_rows`
  - `data_row_count`
  - `status_vocabulary`
  - `skipped_reason`
  - `invariant_warnings`
- `variant-matrix.json`
  - source column index/letter
  - raw variant header
  - parsed body style, model code, trim, model, and variant ID
  - matched workbook variant metadata when available
  - resolution status and evidence notes
- `raw-rows.json`
  - source sheet, source row, source row span
  - section context
  - orderable/ref-only RPO cells
  - raw description
  - primary RPO candidate
  - status cells with raw status, parsed base status, markers, and source cell coordinates
  - description disclosure markers
  - row flags and target-family hints
- `disclosure-links.json`
  - marker
  - status-cell evidence
  - description fragment
  - phrase hints
  - candidate relationship hint
  - review state
- `manifest.json`
  - input paths, run ID, status, artifact list, invariant failures

Workbook target schemas currently relevant to Pass 1:

- Options: `option_id`, `rpo`, `price`, `option_name`, `description`, `detail_raw`, `section_id`, `selectable`, `display_order`, `active`, `display_behavior`.
- OVS/status: `option_id`, `variant_id`, `status`.
- Direct rules: `rule_id`, `source_id`, `rule_type`, `target_id`, `original_detail_raw`, `body_style_scope`, `runtime_action`, `disabled_reason`.
- Price rules: `price_rule_id`, `condition_option_id`, `price_rule_type`, `target_option_id`, `price_value`, `body_style_scope`, `trim_level_scope`, `notes`.
- Rule groups, exclusive groups, interiors, color overrides, components, section presentation, and asset map exist, but Pass 1 must only target them when evidence is explicit enough. In the current Pass 0 data, `Price Schedule` and `Color and Trim` are layout evidence only, not extracted row evidence.

## Diagnosis

Pass 0 gives reliable evidence but not candidate rows. The next risk is over-normalizing: converting raw descriptions, status markers, detail disclosures, or section labels into workbook decisions too early.

Pass 1 should add structure without adding authority. It should answer:

- What option-like rows appear in the raw matrix evidence?
- What availability/status values appear per variant?
- Which detail disclosures appear to imply rules or review decisions?
- Which rows cannot be normalized without a human decision?
- Which non-matrix sheets need a later extractor before they can produce candidates?

Risk level: medium. This is read-only, but the artifact contract will shape later review and apply work.

Change type: tooling/docs/tests only.

## Exact files to change after approval

Implementation files:

- `scripts/order_guide_candidate_normalizer.py`
- `scripts/corvette_form_generator/ingest/candidate_normalizer.py`
- `tests/test_order_guide_candidate_normalizer.py`

Documentation/spec files:

- `Order-Guide_IngestPrompt.md`
- `docs/ingest/README.md`
- `docs/ingest/pass-1/candidate-normalizer-spec.md`

No workbook, generated runtime, browser runtime, or app data files should be changed.

## CLI contract

Command:

```sh
.venv/bin/python scripts/order_guide_candidate_normalizer.py \
  --evidence-dir /tmp/27vette-ingest-manual-smoke \
  --workbook stingray_master.xlsx \
  --run-id pass1-candidates \
  --output-dir /tmp/27vette-pass1-candidates
```

Required behavior:

1. Read only the Pass 0 evidence directory and `stingray_master.xlsx`.
2. Require `manifest.json` with `status: passed`.
3. Refuse to run if required Pass 0 artifact files or keys are missing.
4. Reuse the generated-output guard pattern: `/tmp` is preferred; `form-output/ingest/<run-id>/` is allowed only for run-scoped ingest artifacts; other tracked `form-output/*` paths are blocked.
5. Emit candidate and unresolved-review artifacts only.
6. Exit non-zero on invariant failure.
7. Print counts by candidate family and unresolved reason.
8. Provide no `--write` mode.

## Output artifacts

Expected output files:

```text
candidate-options.json
candidate-ovs.json
candidate-rules.json
candidate-price-rules.json
candidate-summary.json
unresolved-review.md
```

Optional output files if useful:

```text
normalizer-manifest.json
unresolved-review.json
```

These files are transient review artifacts. They are not workbook source data.

## Shared candidate envelope

Every candidate row must include:

- `candidate_id` — stable artifact-local ID.
- `candidate_family` — `options`, `ovs`, `rules`, `price_rules`, or another explicit family.
- `resolution_status` — `candidate`, `needs_review`, `blocked`, or `out_of_scope`.
- `confidence` — `mechanical`, `source_hint`, or `unresolved`.
- `source_refs` — exact Pass 0 evidence references, including sheet, row, column/cell where applicable.
- `raw_values` — raw source values used by the candidate.
- `normalized_values` — proposed review fields only.
- `workbook_match` — exact current workbook match when mechanically safe; otherwise blank/null.
- `review_notes` — why the candidate is safe, review-needed, blocked, or out of scope.

`candidate_id` is not a workbook ID. Do not present it as `option_id`, `rule_id`, `group_id`, `price_rule_id`, or any other canonical workbook key.

## `candidate-options.json`

Purpose: one option-like candidate for each matrix evidence row where a valid primary RPO exists or the row clearly requires option review.

Required normalized fields:

- `candidate_option_ref`
- `model_key_candidates`
- `rpo`
- `orderable_rpo_raw`
- `ref_only_rpo_raw`
- `source_description_raw`
- `source_option_name_candidate`
- `section_context_raw`
- `section_id_candidate`
- `status_summary`
- `canonical_option_match`

Rules:

- Do not create canonical `option_id` values for new rows.
- Do not assign `price`.
- Do not assign approved `section_id` unless the match is exact and mechanical.
- Do not split customer-facing `option_name`, `description`, or `detail_raw` as approved copy.
- Do not assign approved `selectable`, `active`, `display_order`, or `display_behavior`.
- Preserve raw descriptions even when they contain disclosures.
- Treat section/context rows as unresolved review items, not option rows.

## `candidate-ovs.json`

Purpose: one availability/status candidate per Pass 0 status cell with matched variant evidence.

Required normalized fields:

- `candidate_option_ref`
- `variant_id`
- `model_key`
- `raw_status`
- `normalized_status_candidate`
- `status_marker`
- `status_flags`
- `source_cell`

Rules:

- Normalized status vocabulary is only `standard`, `available`, `unavailable`, or `unresolved`.
- Preserve status markers such as `A1`, `S1`, `A/D1`, and `■1` through `raw_status` and `status_marker`.
- Do not emit an OVS candidate when variant resolution is unmatched or ambiguous; send it to unresolved review.
- Join to option candidates with `candidate_option_ref`, not canonical `option_id`, unless an exact current workbook option match exists.

## `candidate-rules.json`

Purpose: review-only relationship candidates from detail disclosure evidence.

Required normalized fields:

- `candidate_rule_ref`
- `source_candidate_option_ref`
- `marker`
- `description_fragment`
- `phrase_hints`
- `relationship_hint`
- `target_rpo_tokens`
- `target_match_status`
- `recommended_review_action`

Rules:

- Do not emit approved `rule_mapping` rows.
- Do not emit approved group or exclusive-group rows.
- Do not choose direct rule vs group rule vs exclusive group as an applied workbook decision.
- Do not create runtime exception candidates as a normal path.
- Relationship hints remain hints even when source text looks obvious.

## `candidate-price-rules.json`

Purpose in Pass 1: preserve the boundary.

Current Pass 0 only classifies `Price Schedule` as layout evidence. It does not extract price schedule rows. Therefore Pass 1 must not fabricate price candidates.

Allowed behavior:

- emit an empty candidate list with a summary reason; or
- emit blocked/out-of-scope review entries that name the missing price evidence extractor.

Rules:

- Do not infer prices from descriptions.
- Do not assign option `price` values.
- Do not create price override candidates without extracted source price evidence.

## `unresolved-review.md`

Group unresolved items by reason:

- missing or invalid primary RPO;
- section/context row requires review;
- unmatched or ambiguous variant evidence;
- disclosure relationship requires review;
- target RPO token is missing or ambiguous;
- price schedule rows are not extracted yet;
- color/trim rows are not extracted yet;
- non-matrix sheets are evidence-only;
- any candidate that would require guessing.

Each item must include exact source references and a short statement of the blocked decision.

## `candidate-summary.json`

Required summary fields:

- `input_evidence_dir`
- `workbook`
- `run_id`
- `generated_at`
- `status`
- `candidate_counts`
- `unresolved_counts`
- `status_vocabulary`
- `model_variant_coverage`
- `invariant_failures`
- `artifact_files`

## Invariants

The implementation must fail rather than guess when:

- required Pass 0 artifacts are missing;
- Pass 0 manifest status is not `passed`;
- required artifact keys are missing;
- a status value cannot be normalized to the allowed candidate vocabulary;
- an OVS candidate lacks matched variant evidence;
- a candidate row lacks exact source references;
- output path is outside the allowed transient ingest locations;
- any code path attempts to write workbook/generated/runtime/app files.

## Companion-file impact check

| Surface | Status for Pass 1 implementation | Notes |
|---|---|---|
| Workbook source sheets | inspected-no-change | Read-only reference only. |
| Pass 0 artifacts | inspect/update contract consumers | If implementation needs new Pass 0 fields, stop and revise the spec first. |
| `form-output/*` tracked generated outputs | not applicable | Must remain unchanged unless a run-scoped ingest artifact is explicitly approved. Prefer `/tmp`. |
| `form-app/data.js` | not applicable | Must remain unchanged. |
| Runtime JS/CSS/HTML | not applicable | No runtime behavior changes. |
| Dealer submission | not applicable | No dealer endpoint or payload changes. |
| `Order-Guide_IngestPrompt.md` | update | Add the Pass 1 candidate-only boundary. |
| `docs/ingest/README.md` | update | Point to this Pass 1 spec. |
| Tests | update | Add focused Python tests. |
| Agent/project guidance | inspected-no-change | Current guardrails already require transient ingest and workbook safety. |

## Constraints

- CLI first; no UI in Pass 1.
- No workbook writes.
- No generated workbook `form_*` writes.
- No tracked generated-output writes outside approved run-scoped ingest artifacts.
- No `form-app/data.js` writes.
- No model promotion.
- No runtime/dealer-submission changes.
- No new dependencies unless separately approved.
- No guessed option IDs, section IDs, rules, prices, interiors, or variant memberships.
- Preserve exact source coordinates, raw status values, status markers, detail disclosures, variant matrix context, and unresolved decisions.
- Do not create permanent review/staging workbook sheets.

## Non-goals

- No interactive wizard UI.
- No workbook apply pass.
- No workbook mutation.
- No generation or registry publication.
- No price extraction from `Price Schedule`.
- No interior/color extraction from `Color and Trim`.
- No cleanup or retirement of inactive future-model workbook scaffolds.
- No customer-copy cleanup pass.

## Risks and mitigations

1. Candidate IDs get mistaken for workbook IDs.
   - Use explicit `candidate_*` names and leave canonical IDs blank unless an exact workbook match exists.

2. Rule hints become hidden product logic.
   - Emit rule candidates as review-only evidence with unresolved actions.

3. Section placement gets guessed from sheet names or labels.
   - Preserve source section context; do not assign approved section IDs unless mechanically exact.

4. Price or interior work creeps into Pass 1.
   - Emit blocked/out-of-scope review entries for layout-only sheets.

5. Generated artifacts drift.
   - Run all tracked `form-output` diff guards.

## Validation plan

Before implementation:

```sh
git status --short --branch
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
.venv/bin/python -m pytest tests/test_order_guide_ingest_profiler.py
```

Implementation tests:

```sh
.venv/bin/python -m pytest tests/test_order_guide_candidate_normalizer.py
```

Manual smoke:

```sh
.venv/bin/python scripts/order_guide_ingest_profiler.py \
  --raw-export "2027 Chevrolet Car Corvette Export_RAW.xlsx" \
  --workbook stingray_master.xlsx \
  --run-id pass1-smoke-evidence \
  --output-dir /tmp/27vette-pass1-smoke-evidence

.venv/bin/python scripts/order_guide_candidate_normalizer.py \
  --evidence-dir /tmp/27vette-pass1-smoke-evidence \
  --workbook stingray_master.xlsx \
  --run-id pass1-smoke-candidates \
  --output-dir /tmp/27vette-pass1-smoke-candidates
```

Post-implementation guards:

```sh
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
git diff --check -- scripts tests docs Order-Guide_IngestPrompt.md
git diff --exit-code -- stingray_master.xlsx form-app/data.js
git diff --exit-code -- $(git ls-files form-output)
git status --short -- form-output
```

No Node runtime tests are required unless the implementation touches runtime/generated/browser files, which would be a scope violation.

## Implementation completion — 2026-06-27

Implemented after approval as a CLI-only, read-only normalizer.

Changed files:

- `scripts/order_guide_candidate_normalizer.py` — new CLI entry point for Pass 1 candidate normalization.
- `scripts/corvette_form_generator/ingest/candidate_normalizer.py` — loads Pass 0 evidence, validates manifest/artifact shapes, builds option/OVS/rule candidates, preserves out-of-scope price/interior boundaries, writes unresolved review output, and reuses the ingest output path guard.
- `tests/test_order_guide_candidate_normalizer.py` — focused fixture tests for option/OVS/rule candidate output, failed-manifest rejection, and generated-output path rejection.
- `Order-Guide_IngestPrompt.md` — updated to describe Pass 1 transient candidate artifacts and explicit unresolved status state.
- `docs/ingest/README.md` — marked Pass 1 candidate normalizer as implemented.
- `docs/ingest/pass-1/candidate-normalizer-spec.md` — closed this spec with implementation evidence.

Implemented behavior:

- CLI command:

```sh
.venv/bin/python scripts/order_guide_candidate_normalizer.py \
  --evidence-dir /tmp/27vette-pass1-smoke-evidence \
  --workbook stingray_master.xlsx \
  --run-id pass1-smoke-candidates \
  --output-dir /tmp/27vette-pass1-smoke-candidates
```

- Emits:
  - `candidate-options.json`
  - `candidate-ovs.json`
  - `candidate-rules.json`
  - `candidate-price-rules.json`
  - `candidate-summary.json`
  - `unresolved-review.md`
- Requires Pass 0 `manifest.json` status `passed`.
- Refuses protected generated-output paths outside approved ingest output roots.
- Preserves artifact-local candidate IDs as `candidate_*` values, not workbook IDs.
- Emits price candidates as an empty list and reports `price_schedule_rows_not_extracted` because Pass 0 currently records price schedule layout evidence only.
- Reports `color_trim_rows_not_extracted` because Pass 0 currently records Color and Trim layout evidence only.

Manual smoke result against the real raw export through fresh Pass 0 evidence:

```text
candidate_counts:
  options: 1744
  ovs: 11244
  rules: 791
  price_rules: 0
unresolved_counts:
  color_trim_rows_not_extracted: 2
  disclosure_relationship_requires_review: 8
  missing_or_invalid_primary_rpo: 208
  price_schedule_rows_not_extracted: 1
  section_context_requires_review: 12
  target_rpo_token_ambiguous_or_missing: 707
```

Validation evidence:

```sh
.venv/bin/python -m pytest tests/test_order_guide_candidate_normalizer.py -q
# 3 passed

.venv/bin/python scripts/order_guide_ingest_profiler.py \
  --raw-export "2027 Chevrolet Car Corvette Export_RAW.xlsx" \
  --workbook stingray_master.xlsx \
  --run-id pass1-smoke-evidence \
  --output-dir /tmp/27vette-pass1-smoke-evidence
# status: passed; raw_row_count: 1964; variant_column_count: 130; disclosure_link_count: 1088

.venv/bin/python scripts/order_guide_candidate_normalizer.py \
  --evidence-dir /tmp/27vette-pass1-smoke-evidence \
  --workbook stingray_master.xlsx \
  --run-id pass1-smoke-candidates \
  --output-dir /tmp/27vette-pass1-smoke-candidates
# status: passed; candidate artifacts written under /tmp
```

Residual risks:

- Rule candidates are still review-only phrase/token hints. They are not direct workbook `rule_mapping`, group, or exclusive-group rows.
- Price Schedule and Color and Trim need later evidence extractors before price/interior/color candidates can be reliable.
- Candidate option copy is raw source text. Customer-facing copy cleanup remains a later review concern.

## Expected next pass after Pass 1

After CLI candidate artifacts are reviewed and proven useful, the next safe pass is a review UI / interactive wizard spec. That UI should display candidate rows next to exact source evidence and current workbook context, but still avoid workbook writes until a later controlled apply pass is approved.
