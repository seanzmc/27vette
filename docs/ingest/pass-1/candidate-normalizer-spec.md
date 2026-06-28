# Pass 1 — Candidate normalizer spec

Date: 2026-06-27
Branch: `ingest-wizard-pass1-spec`
Status: Spec only. Do not implement until approved.
Recommended reasoning level for implementation agent: high.

## Instruction boundary

This spec is based on the current workspace, the implemented Pass 0 profiler, the root ingest prompt, the normalized ingest contract, current workbook schemas, and the actual Pass 0 smoke artifacts under `/tmp/27vette-ingest-manual-smoke`.

The pre-existing file under `docs/ingest/pass-1/` was intentionally not read and is not used as a reference for this spec, per Sean's instruction.

## Purpose

Implement the first read-only candidate normalizer over Pass 0 evidence artifacts.

Pass 1 should convert proven evidence into reviewable candidate artifacts without treating any candidate as an approved workbook row. The output should help a later review UI show what the raw order guide appears to say, where each statement came from, and what remains unresolved before any workbook apply is possible.

This pass must stay out of the workbook, generated runtime artifacts, browser runtime, and model promotion.

## Diagnosis

Pass 0 now produces evidence artifacts with exact source coordinates and no workbook mutation:

```text
source-layout.json
variant-matrix.json
raw-rows.json
disclosure-links.json
manifest.json
checkpoint-report.md
```

Manual smoke against `2027 Chevrolet Car Corvette Export_RAW.xlsx` returned:

```text
status: passed
source_sheet_count: 23
parsed_matrix_sheet_count: 20
raw_row_count: 1964
variant_column_count: 130
disclosure_link_count: 1088
invariant_failures: []
```

The current gap is the next deterministic layer: translating evidence rows into reviewable candidate families while preserving uncertainty. The normalizer must not jump from raw evidence to workbook writes, and it must not guess canonical option IDs, section IDs, prices, rules, interior rows, or presentation metadata.

Observed current Pass 0 artifact shapes:

- `source-layout.json` rows carry `source_sheet`, `sheet_type`, `model_label`, `header_row`, `base_columns`, `variant_columns`, `section_rows`, `data_row_count`, `status_vocabulary`, `skipped_reason`, and `invariant_warnings`.
- `variant-matrix.json` rows carry source column coordinates, raw variant headers, parsed body/model-code/trim, parsed target model, parsed variant ID, workbook variant/membership matches, resolution status, and evidence notes.
- `raw-rows.json` rows carry source sheet/row/span, section context, orderable/ref-only RPO cells, raw description, primary RPO candidate, status cells, description disclosure markers, row flags, and candidate target family hints.
- `disclosure-links.json` rows carry marker, status-cell evidence, description fragment, phrase hints, candidate relationship hint, and review state.

Current workbook target headers inspected from `stingray_master.xlsx` include:

- Option rows: `option_id`, `rpo`, `price`, `option_name`, `description`, `detail_raw`, `section_id`, `selectable`, `display_order`, `active`, `display_behavior`.
- OVS rows: `option_id`, `variant_id`, `status`.
- Direct rules: `rule_id`, `source_id`, `rule_type`, `target_id`, `original_detail_raw`, `body_style_scope`, `runtime_action`, `disabled_reason`.
- Price rules: `price_rule_id`, `condition_option_id`, `price_rule_type`, `target_option_id`, `price_value`, `body_style_scope`, `trim_level_scope`, `notes`.
- Rule groups/exclusive groups and members as currently documented in the workbook source graph.
- Interior/color/component/presentation sheets exist but Pass 0 only classifies `Price Schedule` and `Color and Trim` as non-matrix evidence; it does not yet extract price/interior rows from those sheets.

Risk level: medium. The pass is read-only, but it defines how future agents and UI will interpret raw evidence. Overconfident candidate IDs or hidden rule inference would recreate the prior convolution problem.

Change type: tooling/docs/tests only. No workbook data, generated runtime data, browser runtime behavior, or dealer-submission behavior changes.

## Exact files and artifacts to change after approval

Expected implementation files:

- `scripts/order_guide_candidate_normalizer.py` — new CLI entry point for read-only candidate normalization from a Pass 0 artifact directory.
- `scripts/corvette_form_generator/ingest/candidate_normalizer.py` — candidate artifact loader, evidence validation, candidate builders, unresolved-review writer, and output path guard reuse.
- `tests/test_order_guide_candidate_normalizer.py` — focused fixture tests for option/OVS/disclosure candidate behavior, unresolved handling, and generated-output path guards.
- `Order-Guide_IngestPrompt.md` — clarify that Pass 1 emits candidate artifacts only after a successful Pass 0 evidence run; candidate outputs remain transient and unapproved.
- `docs/ingest/README.md` — add this current Pass 1 candidate-normalizer spec/status.
- `docs/ingest/pass-1/candidate-normalizer-spec.md` — update to `Implemented` during the implementation pass with changed files, artifact paths, gates, residual risks, and next pass.

Expected run-scoped candidate artifacts from the CLI, not checked in unless explicitly approved:

```text
form-output/ingest/<run-id>/candidate-options.json
form-output/ingest/<run-id>/candidate-ovs.json
form-output/ingest/<run-id>/candidate-rules.json
form-output/ingest/<run-id>/candidate-price-rules.json
form-output/ingest/<run-id>/candidate-summary.json
form-output/ingest/<run-id>/unresolved-review.md
```

Optional if useful and kept read-only:

```text
form-output/ingest/<run-id>/normalizer-manifest.json
form-output/ingest/<run-id>/unresolved-review.json
```

## Proposed CLI contract

Command shape:

```sh
.venv/bin/python scripts/order_guide_candidate_normalizer.py \
  --evidence-dir /tmp/27vette-ingest-manual-smoke \
  --workbook stingray_master.xlsx \
  --run-id manual-smoke-candidates \
  --output-dir /tmp/27vette-ingest-manual-smoke-candidates
```

Required behavior:

1. Read Pass 0 artifacts and canonical workbook only.
2. Require a Pass 0 `manifest.json` with `status: passed` unless an explicit `--allow-failed-evidence` flag is added later by a separate approved spec. Do not include that flag in this pass.
3. Validate required Pass 0 artifact files and required keys before emitting candidates.
4. Refuse any output path that would mutate `stingray_master.xlsx`, `form-app/data.js`, generated workbook `form_*` sheets, promotion metadata, or tracked generated outputs under `form-output/` outside explicitly approved run-scoped ingest artifacts.
5. Emit only run-scoped candidate/review artifacts.
6. Exit non-zero on candidate-normalizer invariant failure.
7. Print a concise summary with artifact directory, candidate counts, unresolved counts, and blocking conditions.

No `--write` mode is allowed in Pass 1. Workbook apply belongs to a later controlled apply pass after review.

## Candidate artifact contracts

### Shared candidate row envelope

Every candidate row must include:

- `candidate_id` — stable artifact-local ID, not a workbook ID.
- `candidate_family` — e.g. `options`, `ovs`, `rules`, `price_rules`, `unresolved`.
- `resolution_status` — `candidate`, `needs_review`, `blocked`, or `out_of_scope`.
- `confidence` — `mechanical`, `source_hint`, or `unresolved`.
- `source_refs` — exact evidence links back to Pass 0 source sheet/row/column/cell coordinates.
- `raw_values` — preserved source values used for the candidate.
- `normalized_values` — normalized review candidate fields.
- `workbook_match` — current workbook match when exact and mechanical, otherwise null/empty.
- `review_notes` — explicit reason for unresolved/review-needed state.

`candidate_id` may be deterministic from source evidence, for example source sheet + source row + primary RPO + model candidate. It must not be used as or presented as a canonical workbook `option_id`, `rule_id`, or `price_rule_id`.

### `candidate-options.json`

Purpose: one reviewable option-like candidate per evidence row where the source row has a valid primary RPO candidate or otherwise clearly needs option review.

Required fields inside the shared envelope:

- `candidate_option_ref` — artifact-local reference used by other candidate files.
- `model_key_candidates` — target models derived from matched variant/status evidence.
- `rpo` — source RPO candidate when valid.
- `orderable_rpo_raw` and `ref_only_rpo_raw`.
- `source_option_name_candidate` — raw description before customer-copy cleanup; do not pretend this is approved `option_name`.
- `source_description_raw`.
- `section_context_raw`.
- `section_id_candidate` — null/blank unless mechanically matched to an existing workbook section by an approved map in this pass. The default should be blank with review notes.
- `status_summary` — counts by model/variant/status from Pass 0 status cells.
- `canonical_option_match` — exact current workbook option match only when it is mechanically safe, such as same model sheet and same RPO with no ambiguity.

Rules:

- Do not mint canonical `option_id` for new rows.
- Do not split customer-facing `option_name` / `description` / `detail_raw` beyond preserving raw text and flagging review needs.
- Do not assign prices in option candidates.
- Do not infer active/selectable/display_behavior as approved workbook values. Candidate defaults may be blank or `needs_review`.
- Section-context rows remain unresolved/section candidates, not option rows.

### `candidate-ovs.json`

Purpose: one reviewable availability/status candidate per Pass 0 status cell with matched variant evidence.

Required fields:

- `candidate_option_ref` linking to `candidate-options.json`.
- `variant_id` from Pass 0 `variant_id_candidate` only when matched.
- `model_key` from Pass 0 variant/model candidate.
- `raw_status`.
- `normalized_status_candidate` limited to `standard`, `available`, `unavailable`, or `unresolved`.
- `status_marker` and status flags.
- `source_cell` coordinate.

Rules:

- Do not emit OVS candidates when variant resolution is unmatched/ambiguous; route to unresolved review.
- Do not collapse disclosure-marked statuses (`A1`, `S1`, `A/D1`, etc.) into clean statuses without preserving marker evidence and review flags.
- Do not emit canonical `option_id` unless an exact current workbook option match exists. Use `candidate_option_ref` for candidate joins.

### `candidate-rules.json`

Purpose: reviewable relationship hints from Pass 0 disclosure evidence, not approved workbook rule rows.

Required fields:

- `candidate_rule_ref` — artifact-local reference, not workbook `rule_id`.
- `source_candidate_option_ref` when linkable.
- `marker`.
- `description_fragment`.
- `phrase_hints`.
- `relationship_hint` from Pass 0, such as `requires`, `excludes`, `includes`, or `included_only_available_with`.
- `target_rpo_tokens` if directly present in the source text and safely tokenized.
- `target_match_status` — exact workbook match, ambiguous, unresolved, or not_applicable.
- `recommended_review_action` — e.g. review direct rule, review group rule, review exclusive group, evidence only.

Rules:

- Do not emit approved `rule_mapping` rows.
- Do not choose direct rule vs group vs exclusive group as a workbook decision. At most recommend review action.
- Do not create `runtime_rule_exceptions` candidates except as explicit blocked/unresolved notes that state canonical sheets could not yet express the behavior.
- Relationship hints remain review-only even when phrase matching is obvious.

### `candidate-price-rules.json`

Purpose for Pass 1: preserve the boundary, not solve price parsing yet.

Current Pass 0 artifacts classify `Price Schedule` as `price_schedule` layout evidence but do not extract price schedule rows. Therefore Pass 1 must not fabricate price-rule candidates from missing evidence.

Allowed outputs in this pass:

- Empty candidate list with a summary explaining `price_schedule_rows_not_extracted_by_pass0`; or
- Blocked/unresolved review entries that identify the `Price Schedule` sheet as out of scope for this normalizer until a price evidence extractor is approved.

Rules:

- Do not infer prices from option rows or descriptions.
- Do not assign direct option `price` values.
- Do not create price override candidates without extracted source price row evidence.

### `unresolved-review.md` and optional `unresolved-review.json`

Must group unresolved items by reason:

- unmatched/ambiguous variant evidence;
- missing or invalid primary RPO;
- section context requires review;
- disclosure relationship hint requires review;
- target RPO token ambiguous/missing;
- price schedule evidence not yet extracted;
- color/trim evidence not yet extracted;
- non-matrix sheets preserved as evidence only;
- any row where candidate output would require guessing.

Each unresolved item must include exact source references and the blocked decision needed.

### `candidate-summary.json`

Must include:

- input evidence directory;
- workbook reference path;
- generated timestamp;
- candidate counts by family;
- unresolved counts by reason;
- exact status vocabulary seen;
- model/variant coverage summary;
- pass/fail status;
- invariant failures.

## Source-of-truth and ownership decisions

Decision: tooling/docs/tests for Pass 1.

Raw evidence artifacts own only source provenance. Candidate artifacts own review queues and mechanical normalizations. The workbook remains the source of truth for approved product/runtime decisions. Generators remain the only path from workbook rows to runtime artifacts. Runtime JavaScript remains out of scope.

Candidate artifacts must target the existing workbook source graph but must not become a new permanent staging taxonomy.

## Candidate scope by source family

| Source evidence | Pass 1 action | Not allowed |
|---|---|---|
| Matrix rows with valid RPO/status evidence | Emit option-like and OVS candidate rows with exact source refs and review status. | Canonical `option_id`, approved section, approved copy split, price, active/selectable/display behavior. |
| Disclosure links with relationship hints | Emit review-only rule candidates and unresolved review entries. | Approved `rule_mapping`, groups, exclusive groups, runtime exceptions. |
| Section/context rows from matrix sheets | Emit unresolved section-placement review notes. | Mint section IDs or assign section placement without a reviewed map. |
| `Price Schedule` evidence | Preserve as unresolved/out-of-scope for price extraction unless Pass 0 is extended later. | Price-rule or option-price candidates from missing row evidence. |
| `Color and Trim` evidence | Preserve as unresolved/out-of-scope for interior/color extraction unless a later pass adds evidence rows. | Interior, component, color override, or scope candidates from layout-only evidence. |
| Existing workbook rows | Use only for exact mechanical match/context. | Treat inactive ZR1/ZR1X scaffold content as canonical expected output. |

## Companion-file impact check

| Surface | Status for Pass 1 implementation | Notes |
|---|---|---|
| Workbook source sheets | inspected-no-change | Candidate normalizer must read `stingray_master.xlsx` only. No workbook writes. |
| Pass 0 artifacts | inspect/update contract consumers | Pass 1 depends on current Pass 0 artifact keys. If implementation needs Pass 0 schema additions, stop and revise this spec rather than silently changing Pass 0 behavior. |
| Tracked generated outputs under `form-output/` | not applicable | No tracked generated output changes except explicitly approved run-scoped ingest artifacts. Prefer `/tmp` for smoke output. |
| `form-app/data.js` | not applicable | Registry publication is out of scope. |
| Runtime JS/CSS/HTML | not applicable | No browser behavior changes. |
| Dealer submission endpoint/payload | not applicable | No runtime/dealer path touched. |
| `Order-Guide_IngestPrompt.md` | update | Add the Pass 1 candidate-output boundary and make clear candidates are transient/unapproved. |
| `docs/ingest/README.md` | update | Add the current Pass 1 candidate-normalizer spec/status. |
| `docs/ingest/pass-2/normalized-ingest-contract.md` | inspected-no-change unless implementation changes sequence/artifact names | Current sequence already names Pass 1 candidate normalizer. Update only for contract drift discovered during implementation. |
| Tests | update | Add focused Python tests for candidate artifacts, unresolved handling, and output path guards. |
| Gate reminders / `AGENTS.md` | inspected-no-change | Current guidance already keeps raw ingest transient and blocks workbook/generated writes without apply pass. |
| Profile/Codex/Hermes guidance | not applicable | No agent-guide behavior change required for read-only candidate normalizer. |

## Constraints repeated back

- Do not read or rely on the pre-existing Pass 1 inventory/diagnosis file.
- CLI first; no UI/wizard tab in this pass.
- No workbook writes.
- No generated workbook `form_*` writes.
- No tracked `form-output/*` changes outside explicitly approved run-scoped ingest artifacts; prefer `/tmp` for manual-smoke output.
- No `form-app/data.js` writes.
- No model promotion.
- No runtime/dealer-submission changes.
- No new dependencies unless separately approved. Use Python standard library plus existing project dependencies.
- Do not guess product data, option IDs, section IDs, rules, prices, interiors, or variant membership.
- Use workbook metadata and schema as reference context only.
- Preserve exact source coordinates, detail disclosures, raw statuses, status markers, and variant matrix context in every candidate or unresolved item.
- Existing workbook source graph remains the target; do not resurrect `future_model_source_review`, `future_model_option_review`, `source_review`, or `option_review` as permanent sheets.
- Keep implementation small and reversible.

## Non-goals

- No interactive browser UI.
- No workbook apply manifest.
- No workbook mutation.
- No generation or registry publication.
- No price extraction from `Price Schedule` in this pass unless Pass 0 evidence is explicitly extended by a revised spec.
- No Color and Trim/interior candidate extraction beyond unresolved classification in this pass.
- No cleanup or retirement of existing ZR1/ZR1X workbook scaffold rows.
- No visualizer/image workflow changes.
- No routine-maintenance workflow changes.

## Risks

1. Candidate IDs mistaken for workbook IDs.
   - Mitigation: use `candidate_id` / `candidate_option_ref` naming and explicitly leave canonical workbook IDs blank unless exact current workbook match exists.

2. Rule hints becoming hidden business logic.
   - Mitigation: `candidate-rules.json` is review-only and cannot emit approved `rule_id`, direct rule rows, groups, or runtime exceptions.

3. Section placement guessed from tab/context names.
   - Mitigation: source section labels become review evidence only unless a reviewed section map exists in the implementation scope.

4. Price/interior overreach.
   - Mitigation: Pass 1 must report `Price Schedule` and `Color and Trim` as unresolved/out-of-scope because Pass 0 currently preserves layout evidence only for those tabs.

5. Generated-output churn.
   - Mitigation: run the all-tracked-`form-output` diff guard, not only runtime-contract checks.

6. ZR1/ZR1X scaffold contamination.
   - Mitigation: use variant metadata only for header reconciliation/context; do not compare candidate row counts/content to inactive scaffold rows.

## Validation plan

Before implementation edits:

```sh
git status --short --branch
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
.venv/bin/python -m pytest tests/test_order_guide_ingest_profiler.py
```

During implementation:

```sh
.venv/bin/python -m pytest tests/test_order_guide_candidate_normalizer.py
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

The `git status --short -- form-output` output must be empty unless the pass explicitly approves checked-in `form-output/ingest/<run-id>/` candidate artifacts. Manual smoke output should normally use `/tmp` so the generated-output guard stays clean.

No Node runtime tests are required unless implementation unexpectedly touches generated/runtime/browser files, which should be treated as scope violation.

## Approval question

Approve Pass 1 implementation as scoped above: a CLI-only, read-only candidate normalizer that consumes Pass 0 artifacts, emits transient review candidates/unresolved reports, and performs no workbook/generated/runtime writes?

Recommended approval: yes, after reviewing the candidate artifact contracts and confirming that price/interior extraction should remain out of scope until a later evidence extractor pass.

## Expected next pass after Pass 1

Pass 2 should be a review UI / interactive wizard spec only after candidate artifacts are proven useful from CLI output. The UI should show candidate rows beside exact source evidence and current workbook context, and should let a human approve/edit/skip/unresolve without writing the workbook.

Controlled workbook apply remains a later separate pass with dry-run default, explicit approval, safe-save, regeneration, and gates.
