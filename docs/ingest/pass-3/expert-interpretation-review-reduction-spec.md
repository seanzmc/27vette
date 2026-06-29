# Pass 3 — Expert interpretation and review reduction spec

Date: 2026-06-28
Branch: `ingest-wizard`
Status: Implemented 2026-06-28 as CLI/report-first interpreter. UI/server integration remains deferred.
Recommended reasoning level for implementation agent: high.

## Purpose

Build a read-only expert-interpretation layer between the Pass 1 candidate normalizer and any later workbook apply planning.

Pass 2 proved that the ingest workflow can preserve source evidence and display raw candidates, but it still exposes too many mechanical rows for practical review. The next pass should reduce thousands of row/cell-level candidates into option-level review units that behave more like an expert reading the GM order guide: preserve the source structure, understand repeated RPO appearances across model sheets, compare only safe workbook identity fields, and surface only meaningful decisions.

This pass must not write `stingray_master.xlsx`, generated workbook `form_*` sheets, tracked runtime artifacts, `form-app/data.js`, or dealer-submission/runtime files.

## User direction captured for this pass

- The ingest script should not require manual review of roughly ten thousand candidates.
- It also must not auto-blow through noisy source data and create later cleanup work.
- The desired behavior is an expert order-guide reader with strong comprehension of Corvette option configuration, source structure, and source language.
- Workbook matching must be scoped to RPO identity, not customer-facing copy, because form copy has been rewritten to be more user-friendly.
- Duplicate source RPO rows are expected because the raw export repeats options across model/source sheets. Pass 3 must explicitly help identify the sheet or sheet set that gives the most comprehensive option list per model with the least duplicate noise.

## Source basis and current evidence

Current implemented inputs:

- Pass 0 source profiler:
  - `scripts/order_guide_ingest_profiler.py`
  - `scripts/corvette_form_generator/ingest/source_profiler.py`
  - artifacts: `source-layout.json`, `variant-matrix.json`, `raw-rows.json`, `disclosure-links.json`, `manifest.json`, `checkpoint-report.md`
- Pass 1 candidate normalizer:
  - `scripts/order_guide_candidate_normalizer.py`
  - `scripts/corvette_form_generator/ingest/candidate_normalizer.py`
  - artifacts: `candidate-options.json`, `candidate-ovs.json`, `candidate-rules.json`, `candidate-price-rules.json`, `candidate-summary.json`, `unresolved-review.json`, `unresolved-review.md`
- Pass 2 review UI:
  - `scripts/corvette_form_generator/ingest/review_payload.py`
  - `scripts/workbook_editor_server.py`
  - `visualizer/workbook-editor/editor.js`
  - `visualizer/workbook-editor/editor.css`
  - read-only `/api/ingest/*` endpoints and client-side review-decision export

Fresh pre-spec smoke on the real raw export:

```text
Pass 0 evidence output: /tmp/27vette-pass3-spec-evidence
status: passed
source_sheet_count: 23
parsed_matrix_sheet_count: 20
raw_row_count: 1964
variant_column_count: 130
disclosure_link_count: 1088
invariant_failures: []

Pass 1 candidate output: /tmp/27vette-pass3-spec-candidates
options: 1744
ovs: 11244
rules: 791
price_rules: 0
unresolved items: 938
```

Duplicate-source evidence from the same smoke:

```text
Model        candidate row refs  unique RPOs  duplicate RPOs  extra duplicate refs
stingray     443                 222          213             221
grand_sport  456                 226          221             230
z06          455                 225          219             230
zr1          390                 192          185             198
zr1x         390                 192          185             198
```

Top source sheets by unique RPO count in that smoke:

```text
stingray:     Equipment Groups 1 = 165, Exterior 1 = 97, Interior 1 = 81, Standard Equipment 1 = 54, Mechanical 1 = 44
grand_sport:  Equipment Groups 2 = 171, Exterior 2 = 103, Interior 2 = 81, Standard Equipment 2 = 57, Mechanical 2 = 42
z06:          Equipment Groups 3 = 171, Exterior 3 = 100, Interior 3 = 85, Standard Equipment 3 = 57, Mechanical 3 = 40
zr1/zr1x:     Equipment Groups 4 = 134, Interior 4 = 85, Exterior 4 = 66, Standard Equipment 4 = 60, Mechanical 4 = 41
```

Representative multi-sheet duplicate examples include `UQT`, `C2Z`, `CFV`, `D3V`, `SL9`, `UV6`, and `WUB`, each appearing across equipment-group, section-specific, and/or standard-equipment sheets.

## Diagnosis

Root cause / current gap:

Pass 2 exposes raw candidates accurately, but its review unit is still too low-level. `candidate-ovs.json` creates one candidate per status cell, so a single option repeated across several variants and source sheets can produce many review rows. `candidate-options.json` also keeps source rows as separate candidates, so repeated RPOs across `Equipment Groups`, `Exterior`, `Interior`, `Mechanical`, and `Standard Equipment` appear as duplicates rather than a single interpreted option.

The current normalizer is intentionally conservative and does not yet decide:

- which duplicate source row is the best primary evidence for a model/RPO;
- which duplicate rows are redundant, complementary, or conflicting;
- whether `Equipment Groups` is sufficient as a comprehensive source or whether a minimal sheet set is required;
- whether an option/status matrix is unchanged from current workbook RPO/OVS identity;
- which rows can be hidden from manual review because they match existing workbook identity and status behavior;
- which rows need expert review because source language, footnotes, package behavior, or duplicate conflicts imply real product decisions.

Risk level: medium. This pass remains read-only, but it defines the confidence and reduction contract that later dry-run apply planning may consume. A weak interpretation layer would either flood the reviewer or hide important product decisions.

Change type for first implementation: tooling/tests/docs only, no workbook data, UI/server, generated/runtime, or dealer-submission behavior changes. UI/server work is deferred until the CLI/report interpreter proves material reduction.

## Corrected Pass 3 direction

The Pass 2 completion note originally named Pass 3 as controlled apply planning. That is intentionally superseded by this spec. Apply planning is still needed later, but the safer next pass is expert interpretation and review reduction first.

Expected sequence after this correction:

```text
Pass 0 evidence profiler
  -> Pass 1 candidate normalizer
  -> Pass 2 raw candidate review UI
  -> Pass 3 expert interpretation / reduced review units
  -> Pass 4 reduced review UI over Pass 3 artifacts
  -> Pass 5 focused selected-model workbook-build review
  -> later dry-run apply planning
  -> later controlled workbook apply only after reviewed dry-run output
```

## Exact files to change after approval

### First implementation scope: CLI/report-first only

The first approved Pass 3 implementation must stop after the interpreter proves useful on real smoke output. Do not update the workbook-editor UI/server in the first implementation unless this spec is revised after the CLI/report output demonstrates material review reduction.

Required implementation files for the first pass:

- `scripts/order_guide_ingest_interpreter.py`
  - new CLI entry point that consumes Pass 0 and Pass 1 artifacts and emits reduced interpretation artifacts.
- `scripts/corvette_form_generator/ingest/expert_interpreter.py`
  - new read-only interpreter module for option-level aggregation, RPO-scoped workbook matching, duplicate-source classification, source-sheet coverage analysis, and review queue reduction.

Required tests for the first pass:

- `tests/test_order_guide_ingest_interpreter.py`
  - CLI/module tests for interpretation artifacts, duplicate RPO grouping, RPO-only workbook matching, source-sheet coverage, strict `auto_confirmed` gates, material-reduction reporting, and output path guards.

Required documentation/spec files:

- `docs/ingest/pass-3/expert-interpretation-review-reduction-spec.md`
  - close this spec with implementation evidence after approval and implementation.
- `docs/ingest/README.md`
  - update Pass 3 status after implementation.
- `Order-Guide_IngestPrompt.md`
  - keep the staged output sequence aligned with the implemented Pass 3 artifact contract.

### Deferred UI/server follow-up, not part of the first implementation

Only after the CLI/report output meets the success criteria below should a follow-up UI pass update:

- `scripts/corvette_form_generator/ingest/review_payload.py`
- `scripts/workbook_editor_server.py`
- `visualizer/workbook-editor/editor.js`
- `visualizer/workbook-editor/editor.css`
- `tests/test_ingest_review_payload.py`
- `tests/test_editor_server_ingest_review.py`

That follow-up should make reduced option-level review units the default Ingest Review view while keeping raw Pass 1 candidates available as drill-down/debug evidence.

No workbook binary/source sheet, generated runtime artifact, browser runtime app, registry, or dealer-submission file should be changed.

## Proposed CLI contract

Command:

```sh
.venv/bin/python scripts/order_guide_ingest_interpreter.py \
  --evidence-dir /tmp/27vette-pass3-evidence \
  --candidates-dir /tmp/27vette-pass3-candidates \
  --workbook stingray_master.xlsx \
  --run-id pass3-interpretation \
  --output-dir /tmp/27vette-pass3-interpretation
```

Required behavior:

1. Read only Pass 0 evidence artifacts, Pass 1 candidate artifacts, and `stingray_master.xlsx`.
2. Require Pass 0 `manifest.json` and Pass 1 `candidate-summary.json` with `status: passed`.
3. Reuse the existing ingest output path guard: `/tmp` preferred; `form-output/ingest/<run-id>/` allowed only for run-scoped ingest artifacts; other tracked `form-output/*` paths blocked.
4. Emit interpretation/review-reduction artifacts only.
5. Exit non-zero on invariant failure.
6. Print a concise summary: raw candidate counts, interpreted option count, hidden unchanged count, review queue count, duplicate conflict count, blocked count, and output directory.
7. Provide no workbook write mode and no apply-plan mode.

## Output artifacts

Expected files:

```text
interpretation-summary.json
interpreted-options.json
review-queue.json
duplicate-rpo-report.json
duplicate-rpo-report.md
source-sheet-coverage.json
source-sheet-coverage.md
blocked-interpretation.json
```

Optional if useful:

```text
interpretation-manifest.json
```

These are transient interpretation artifacts. They are not workbook source data and not workbook operations.

## Core review-unit contract

Pass 3 must aggregate to one primary review unit per `model_key + rpo` wherever possible.

Each interpreted option must include:

- `interpretation_id` — stable artifact-local ID, e.g. `interpopt-<model>-<rpo>`.
- `model_key`.
- `rpo`.
- `source_occurrences` — all source rows carrying that RPO for the model, with exact source refs.
- `primary_source_occurrence` — selected best source row if safe; otherwise null.
- `duplicate_classification` — one of:
  - `single_source`
  - `redundant_duplicates`
  - `complementary_duplicates`
  - `conflicting_duplicates`
  - `blocked_duplicate_review`
- `source_sheet_roles` — per occurrence classification:
  - `candidate_primary`
  - `complementary_evidence`
  - `standard_equipment_context`
  - `equipment_group_context`
  - `section_specific_context`
  - `redundant_duplicate`
  - `conflict`
- `availability_matrix` — status by variant/body/trim from Pass 1 OVS candidates, grouped under the option instead of exposed as independent review rows.
- `status_pattern_summary` — compact description of availability/status behavior across variants.
- `disclosure_evidence` — linked disclosure/rule hints for this model/RPO.
- `workbook_identity_match` — RPO-scoped workbook match result.
- `workbook_status_match` — OVS/status comparison result when safe.
- `copy_comparison_status` — must be `not_compared_by_design`.
- `interpretation_confidence` — one of `auto_confirmed`, `mechanical_safe`, `review_needed`, `blocked`.
- `review_reason_codes` — stable filter keys for why the row remains visible.
- `expert_summary` — concise explanation of what the source appears to say and why review is or is not needed.

## Workbook matching rule: RPO identity only

Workbook matching in this pass must be scoped to RPO identity and model context.

Allowed workbook matching fields:

- `model_key`
- `rpo`
- `option_id` only after a unique model+RPO match is found
- workbook OVS/status rows joined through that unique option identity
- section ID may be displayed as context only after identity match

Disallowed as match criteria:

- `option_name`
- `description`
- `detail_raw`
- customer-facing labels/copy
- display copy from runtime/generated artifacts

Reason: the form copy has intentionally been rewritten to be more user friendly. Raw GM copy and workbook customer copy are not expected to match and must not create false drift.

Required match statuses:

- `unique_rpo_match` — exactly one active workbook option row for the model/RPO.
- `missing_in_workbook` — source model/RPO has no workbook option match.
- `duplicate_workbook_rpo` — more than one active workbook option row for the model/RPO.
- `inactive_or_scaffold_match` — match exists only in inactive/future scaffold context.
- `out_of_scope_model` — source model is not approved for workbook apply in this pass.

`copy_comparison_status` must remain `not_compared_by_design` for every interpreted option.

## Duplicate RPO resolution strategy

Pass 3 must not assume a single sheet is globally authoritative. It should compute source-sheet coverage and classify duplicates before selecting any primary source occurrence.

Required analysis:

1. For each model, count unique RPOs by sheet.
2. For each model, compute source-sheet set coverage:
   - single-sheet coverage, especially `Equipment Groups <n>`;
   - two-sheet and three-sheet combinations that maximize unique RPO coverage with minimal duplicate refs;
   - RPOs missing from the top coverage set but present in section-specific sheets.
3. For each duplicate model/RPO, compare source occurrences by:
   - source sheet type/name;
   - raw orderable/ref-only RPO cells;
   - raw description text;
   - status matrix across variants;
   - disclosure markers/fragments;
   - section context.
4. Classify duplicates as:
   - `redundant_duplicates` when repeated rows carry the same effective status/detail evidence;
   - `complementary_duplicates` when one row provides broad equipment-group context and another provides section-specific or standard-equipment context without conflict;
   - `conflicting_duplicates` when status, disclosure, or source description materially disagrees;
   - `blocked_duplicate_review` when the interpreter cannot safely classify the relationship.
5. Select `primary_source_occurrence` only when the duplicate classification is `single_source`, `redundant_duplicates`, or a documented `complementary_duplicates` case with no conflict.
6. Preserve every duplicate occurrence in `source_occurrences`; never discard source evidence.

Important expected finding from the current smoke: `Equipment Groups` sheets appear to have the broadest unique RPO coverage for each model, but they are not automatically the only source of truth. The pass must prove whether they are sufficient as a base list and which section-specific sheets add missing or richer evidence.

## Expert interpretation rules

Pass 3 should start moving from raw phrase hints toward explicit, testable interpretation categories, but it must remain read-only.

Required categories:

- `plain_availability` — no disclosure markers or rule language; availability matrix can be mechanically summarized.
- `standard_equipment_context` — source row appears in standard-equipment context or uses standard/included statuses.
- `equipment_group_inclusion` — row/status suggests equipment-group inclusion, including `■` and footnoted `■1` style symbols.
- `upgradeable_equipment_group_review` — `□` or equivalent upgradeable included-equipment behavior; blocked/review-needed until modeled.
- `dealer_installed_or_adi` — `D` / `A/D` availability preserved as ADI/dealer-installed nuance.
- `requires_relationship_hint` — phrase evidence such as `requires` or `only available with`.
- `includes_relationship_hint` — phrase evidence such as `includes` or `included with`.
- `excludes_relationship_hint` — phrase evidence such as `not available with`.
- `included_only_available_with_hint` — phrase evidence for included-and-only-available wording.
- `price_out_of_scope` — Price Schedule evidence not extracted yet.
- `color_trim_out_of_scope` — Color and Trim evidence not extracted yet.

Each category must include source refs and an explanation. The interpreter may recommend review states, but it must not create workbook rules, groups, price rules, interior rows, color rows, or apply operations.

## Review reduction behavior

Pass 3 must reduce the default review queue by hiding safe/unchanged rows from normal review while preserving drill-down access.

### Success criteria for the CLI/report-first implementation

`interpretation-summary.json` must report these counts for every run:

- `raw_candidate_counts` by family from Pass 1: options, OVS/status, rules, price rules, and unresolved.
- `raw_candidate_total`.
- `interpreted_option_count` after aggregation to model/RPO units.
- `hidden_auto_confirmed_count`.
- `visible_review_queue_count`.
- `mechanical_safe_count`.
- `review_needed_count`.
- `blocked_count`.
- `duplicate_rpo_count`.
- `conflicting_duplicate_count`.
- `source_sheet_coverage` summary by model.

For the first implementation to be considered successful on the real smoke output:

1. `interpreted_option_count` must be materially smaller than the raw Pass 1 candidate surface by aggregating row/cell candidates into model/RPO units.
2. `visible_review_queue_count + blocked_count` must be materially smaller than `raw_candidate_total`; the target is at least a 70% reduction from the raw Pass 1 candidate total, while still preserving all rows in drill-down artifacts.
3. The report must separately state whether the reduction came from aggregation alone, from strict `auto_confirmed` hiding, or both.
4. If those thresholds are not met, the CLI must still exit successfully when artifacts are valid, but it must print and write a `reduction_status: insufficient_reduction` with specific reason codes such as `duplicate_classification_too_weak`, `ovs_comparison_not_trusted`, `too_many_footnotes`, `too_many_conflicts`, or `workbook_match_too_ambiguous`.
5. If reduction is insufficient, implementation must stop at the report and not proceed to UI/default-view work.

Success is not measured by maximizing hidden rows. It is acceptable for `hidden_auto_confirmed_count` to be low if the source contains footnotes, ADI nuance, included-equipment symbols, duplicate conflicts, or ambiguous workbook matches. The important result is a truthful reduced model/RPO interpretation report that explains what still needs expert review.

Recommended confidence behavior:

- `auto_confirmed`
  - unique model/RPO workbook identity match;
  - source availability matrix matches workbook OVS identity/status exactly for every active matched variant;
  - duplicate occurrences are single/redundant with no conflict;
  - no status footnote marker;
  - no disclosure marker or relationship hint;
  - no unresolved target RPO;
  - no ADI/dealer-installed nuance (`D` or `A/D`);
  - no included/upgradeable equipment-group symbol (`■`, `■1`, `□`, or equivalent);
  - no missing workbook match;
  - no duplicate workbook RPO;
  - no source duplicate conflict or blocked duplicate classification.
  - Default report/deferred-UI behavior: hidden from active review, visible in audit/drill-down.

- `mechanical_safe`
  - no workbook match or new source row, but source structure is complete;
  - duplicate handling is single/redundant/complementary without conflict;
  - no relationship/price/interior/color blocker;
  - may include new/missing-in-workbook rows, but those rows remain visible and require later reviewer approval before apply planning;
  - candidate may be eligible for later dry-run apply planning after reviewer approval.
  - Default report/deferred-UI behavior: visible in a smaller `safe new/change` queue.

- `review_needed`
  - relationship hints, footnotes, ADI nuance, duplicate ambiguity, section ambiguity, target-RPO ambiguity, or changed status matrix.
  - Default report/deferred-UI behavior: visible in primary review queue.

- `blocked`
  - price schedule, color/trim, unresolved variants, duplicate conflict, duplicate workbook RPO, or unsupported source shape.
  - Default report/deferred-UI behavior: visible in blocked queue, not eligible for later apply planning.

The first implementation should report `review_needed` + `blocked` + optionally `mechanical_safe` as the reduced visible queue, not raw 10k candidates. A deferred UI pass should use that same default and keep raw candidates available for drill-down.

## Deferred server/UI behavior

This section describes the follow-up UI pass only. It is not part of the first CLI/report-first implementation.

Start command after Pass 3 artifacts exist and after the CLI/report output meets the success criteria above:

```sh
.venv/bin/python scripts/workbook_editor_server.py \
  --workbook stingray_master.xlsx \
  --ingest-evidence-dir /tmp/27vette-pass3-evidence \
  --ingest-candidates-dir /tmp/27vette-pass3-candidates \
  --ingest-interpretation-dir /tmp/27vette-pass3-interpretation
```

If no interpretation directory is supplied, current Pass 2 behavior must continue unchanged.

When interpretation artifacts are supplied:

- Ingest Review should default to `review-queue.json` / interpreted option units.
- Raw Pass 1 candidates should remain accessible under a `Raw candidates` or `Debug candidates` view.
- Each interpreted option detail panel should show:
  - source occurrences grouped by sheet;
  - duplicate classification and primary-source rationale;
  - availability matrix by variant;
  - RPO-scoped workbook match only;
  - copy comparison explicitly marked not compared;
  - disclosure/category evidence;
  - confidence and reason codes;
  - drill-down links to Pass 1 candidates and Pass 0 source rows.

## Explicit no-write boundaries

Pass 3 must not:

- write `stingray_master.xlsx`;
- write generated workbook `form_*` sheets;
- write tracked generated outputs under `form-output/*` outside run-scoped ingest output;
- write `form-app/data.js`;
- regenerate model artifacts;
- promote models;
- POST to the dealer endpoint;
- call `/api/apply` from ingest review;
- convert interpreted options into workbook ops;
- infer price/interior/color rows before dedicated evidence extractors exist;
- compare or overwrite user-friendly workbook/customer copy from raw GM source copy.

## Companion-file impact check

| Surface | Status for Pass 3 implementation | Notes |
|---|---|---|
| Workbook source sheets | inspected-no-change | Read-only RPO/status/context matching only. No workbook writes. |
| Pass 0 evidence artifacts | inspected-no-change unless implementation proves a missing evidence field | Prefer consuming existing `raw-rows`, `variant-matrix`, and `disclosure-links`. If new evidence fields are required, revise Pass 0 contract explicitly. |
| Pass 1 candidate artifacts | inspected-no-change unless implementation proves a missing candidate field | Pass 3 should aggregate existing candidates rather than changing their meaning. |
| Pass 2 review UI/server | inspected-no-change for first implementation | UI/server updates are deferred until the CLI/report-first interpreter proves material reduction on real smoke output. |
| New Pass 3 artifacts | update | Add interpreter CLI/module, artifacts, tests, docs. |
| `form-output/*` tracked generated outputs | not applicable | Must remain unchanged; smoke output should stay under `/tmp`. |
| `form-app/data.js` | not applicable | Must remain unchanged. |
| Customer runtime JS/CSS/HTML | not applicable | Workbook-editor UI is dev tooling, not customer runtime. |
| Dealer submission | not applicable | No endpoint/payload changes. |
| Tests | update | Add interpreter tests only in first implementation; server/payload/UI tests belong to the deferred UI follow-up. |
| `Order-Guide_IngestPrompt.md` | update | Keep Pass 3 artifact list aligned with the implemented CLI/report contract. |
| `docs/ingest/README.md` | update | Update Pass 3 status after implementation. |
| `docs/ingest/pass-2/interactive-review-wizard-spec.md` | inspected-no-change | Already marks the old apply-planning next step as superseded. |
| Agent/project guidance | inspected-no-change | Existing guardrails already cover no workbook/generated writes. |

## Constraints

- Continue on the single `ingest-wizard` branch.
- No new branch per ingest pass unless Sean explicitly asks.
- No workbook writes.
- No generated/runtime/app data writes.
- No model promotion.
- No dealer-submission/runtime changes.
- No new dependencies unless separately approved.
- Match workbook by model/RPO identity only; do not compare raw GM copy to user-friendly form copy.
- Preserve exact source refs and all duplicate source occurrences.
- Do not discard duplicated RPO rows just because a primary source row is selected.
- Use current workbook metadata and source schemas as context; do not create permanent staging sheets.
- Keep price schedule and Color/Trim extraction out of scope until dedicated extractors exist.

## Non-goals

- No canonical workbook apply.
- No apply manifest.
- No dry-run workbook-op plan in this pass.
- No safe-save workflow.
- No regeneration or registry publication.
- No customer runtime changes.
- No price schedule extractor.
- No Color and Trim/interior extractor.
- No customer-copy rewrite from raw GM text.
- No automatic option ID, section ID, rule, group, price, interior, display-order, or copy assignment.
- No deletion or retirement of inactive future-model workbook scaffolds.

## Risks and mitigations

1. The interpreter hides a meaningful source change.
   - Mitigation: only hide `auto_confirmed` rows with unique model/RPO match, non-conflicting duplicates, and matching status identity; preserve all hidden rows in audit output.

2. RPO-only workbook matching misses copy drift.
   - Mitigation: this is intentional. Raw GM copy is not customer copy. Copy review is out of scope and must not drive match confidence.

3. Duplicate RPO resolution picks the wrong primary sheet.
   - Mitigation: require source-sheet coverage reports, duplicate classifications, source occurrence preservation, and primary-source rationale; block conflicts.

4. Equipment Groups look comprehensive but omit section-specific evidence.
   - Mitigation: compute minimal sheet-set coverage and classify complementary sources; do not treat one sheet as globally authoritative without proof.

5. Expert language rules become hidden workbook logic.
   - Mitigation: emit interpretation categories and review reasons only; no workbook ops/rules/groups in Pass 3.

6. The first implementation proves the report but not the UI.
   - Mitigation: intentionally keep Pass 3 CLI/report-first. Add UI only in a follow-up after material reduction is proven on real smoke output.

## Validation plan

Before implementation:

```sh
git status --short --branch
.venv/bin/python -m pytest tests/test_order_guide_ingest_profiler.py tests/test_order_guide_candidate_normalizer.py tests/test_ingest_review_payload.py tests/test_editor_server_ingest_review.py -q
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Implementation tests:

```sh
.venv/bin/python -m pytest \
  tests/test_order_guide_ingest_profiler.py \
  tests/test_order_guide_candidate_normalizer.py \
  tests/test_order_guide_ingest_interpreter.py -q

.venv/bin/python -m py_compile \
  scripts/order_guide_ingest_profiler.py \
  scripts/order_guide_candidate_normalizer.py \
  scripts/order_guide_ingest_interpreter.py \
  scripts/corvette_form_generator/ingest/source_profiler.py \
  scripts/corvette_form_generator/ingest/candidate_normalizer.py \
  scripts/corvette_form_generator/ingest/expert_interpreter.py
```

Manual smoke:

```sh
rm -rf /tmp/27vette-pass3-evidence /tmp/27vette-pass3-candidates /tmp/27vette-pass3-interpretation
.venv/bin/python scripts/order_guide_ingest_profiler.py \
  --raw-export "2027 Chevrolet Car Corvette Export_RAW.xlsx" \
  --workbook stingray_master.xlsx \
  --run-id pass3-smoke-evidence \
  --output-dir /tmp/27vette-pass3-evidence
.venv/bin/python scripts/order_guide_candidate_normalizer.py \
  --evidence-dir /tmp/27vette-pass3-evidence \
  --workbook stingray_master.xlsx \
  --run-id pass3-smoke-candidates \
  --output-dir /tmp/27vette-pass3-candidates
.venv/bin/python scripts/order_guide_ingest_interpreter.py \
  --evidence-dir /tmp/27vette-pass3-evidence \
  --candidates-dir /tmp/27vette-pass3-candidates \
  --workbook stingray_master.xlsx \
  --run-id pass3-smoke-interpretation \
  --output-dir /tmp/27vette-pass3-interpretation
```

Manual report smoke:

- Inspect `interpretation-summary.json` and confirm it reports raw candidate counts, interpreted option count, hidden auto-confirmed count, visible review queue count, mechanical-safe count, review-needed count, blocked count, duplicate RPO count, conflicting duplicate count, and source-sheet coverage by model.
- Confirm `reduction_status` is either `material_reduction` or `insufficient_reduction` with reason codes.
- Confirm any `auto_confirmed` row satisfies the strict gates: exact RPO identity match, exact OVS/status match for active matched variants, no footnotes, no disclosure/rule hints, no unresolved target, no ADI nuance, no `■`/`□` included-equipment symbols, no missing/duplicate workbook match, and no duplicate conflict.
- Inspect a duplicated RPO such as `UQT`, `C2Z`, `CFV`, `D3V`, `SL9`, `UV6`, or `WUB` in `duplicate-rpo-report.md` and confirm source occurrences are grouped by sheet with duplicate classification.
- Confirm `source-sheet-coverage.md` identifies the best sheet or sheet set per model and names RPOs added by complementary sheets.

Post-implementation guards:

```sh
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
git diff --check -- scripts tests visualizer docs Order-Guide_IngestPrompt.md
git diff --exit-code -- stingray_master.xlsx form-app/data.js
git diff --exit-code -- $(git ls-files form-output)
git status --short -- form-output
```

No customer runtime Node tests are required unless implementation touches runtime/generated/browser app files, which would be a scope violation. The first implementation should not touch workbook-editor UI/server files; if it does, stop and revise the spec before continuing.

## Historical approval prompt

Historical approved Pass 3 scope: a CLI/report-first, read-only expert interpretation and review-reduction layer that aggregates raw candidates into model/RPO review units, matches workbook context by RPO identity only, classifies duplicate source rows and source-sheet coverage, reports strict success/reduction metrics, and still performs no workbook/generated/runtime/UI writes.

Recommended approval: yes. This is the right safety step before dry-run apply planning because it directly addresses duplicate RPO noise and avoids forcing manual review of the raw 10k+ candidate surface.

## Expected next pass after Pass 3

Pass 4 is implemented in `docs/ingest/pass-4/reduced-review-ui-spec.md`. It updates the Ingest Review UI/server to consume Pass 3 interpretation artifacts as the default reduced review view when configured. User review found that the broad reduced queue and abstract decision vocabulary were still not usable enough for ZR1/ZR1X intake. Pass 5, scoped in `docs/ingest/pass-5/focused-model-workbook-build-review-spec.md`, must correct direction before dry-run apply planning: early selected-model processing and workbook-destination review lanes.

## Implementation completion — 2026-06-28

Implemented after approval as a CLI/report-first, read-only interpreter. UI/server integration was intentionally not implemented in this pass.

Changed files:

- `scripts/order_guide_ingest_interpreter.py` — new CLI entry point for Pass 3 interpretation artifacts.
- `scripts/corvette_form_generator/ingest/expert_interpreter.py` — new read-only interpreter that aggregates Pass 1 candidates into model/RPO review units, performs RPO-only workbook identity/status comparison, classifies duplicate source occurrences, computes source-sheet coverage, and writes reduced review reports.
- `tests/test_order_guide_ingest_interpreter.py` — focused tests for interpretation artifacts, model/RPO aggregation, duplicate RPO classification, strict `auto_confirmed` gates, path guards, and CLI output.
- `Order-Guide_IngestPrompt.md` — updated Pass 3 wording to reflect implemented CLI/report-first artifacts and the deferred UI/apply sequence.
- `docs/ingest/README.md` — marked Pass 3 as implemented CLI/report-first.
- `docs/ingest/pass-2/interactive-review-wizard-spec.md` — already updated before implementation to mark the older apply-planning next step as superseded by Pass 3 interpretation/reduction.
- `docs/ingest/pass-3/expert-interpretation-review-reduction-spec.md` — closed this spec with implementation evidence.

Implemented behavior:

- Command shape:

```sh
.venv/bin/python scripts/order_guide_ingest_interpreter.py \
  --evidence-dir /tmp/27vette-pass3-evidence \
  --candidates-dir /tmp/27vette-pass3-candidates \
  --workbook stingray_master.xlsx \
  --run-id pass3-smoke-interpretation \
  --output-dir /tmp/27vette-pass3-interpretation
```

- Emits:
  - `interpretation-summary.json`
  - `interpreted-options.json`
  - `review-queue.json`
  - `duplicate-rpo-report.json`
  - `duplicate-rpo-report.md`
  - `source-sheet-coverage.json`
  - `source-sheet-coverage.md`
  - `blocked-interpretation.json`
- Reuses the existing ingest output path guard and refuses protected tracked generated-output paths outside allowed run-scoped ingest roots.
- Matches workbook context by model/RPO identity only; raw GM copy and user-friendly workbook/form copy are not compared.
- Keeps `auto_confirmed` strict: exact model/RPO identity match, exact OVS/status match, no footnotes, no disclosure/rule hints, no ADI nuance, no included/upgradeable equipment symbols, no missing/duplicate workbook match, and no duplicate conflict.
- Preserves every duplicate source occurrence in the interpretation artifacts.

Manual smoke against the real raw export:

```text
Pass 0 -> /tmp/27vette-pass3-evidence: status passed; 23 source sheets; 20 parsed matrix sheets; 1964 raw rows; 130 variant columns; 1088 disclosure links.
Pass 1 -> /tmp/27vette-pass3-candidates: status passed; options 1744; ovs 11244; rules 791; price_rules 0; unresolved items 938.
Pass 3 -> /tmp/27vette-pass3-interpretation: status passed; raw_candidate_total 14717; interpreted_option_count 1057; hidden_auto_confirmed_count 200; visible_review_queue_count 855; mechanical_safe_count 9; review_needed_count 846; blocked_count 5; duplicate_rpo_count 1023; conflicting_duplicate_count 2; reduction_status material_reduction.
```

Source-sheet coverage finding from the smoke:

- `Equipment Groups` remains the broadest single sheet family by unique RPO count for each model.
- The current report found the no-duplicate three-sheet set `Exterior + Interior + Mechanical` covers all unique RPOs for each parsed model in this export. This is a report finding only, not a workbook apply decision.

Validation evidence:

```sh
.venv/bin/python -m pytest tests/test_order_guide_ingest_profiler.py tests/test_order_guide_candidate_normalizer.py tests/test_order_guide_ingest_interpreter.py -q
# 9 passed

.venv/bin/python -m py_compile scripts/order_guide_ingest_profiler.py scripts/order_guide_candidate_normalizer.py scripts/order_guide_ingest_interpreter.py scripts/corvette_form_generator/ingest/source_profiler.py scripts/corvette_form_generator/ingest/candidate_normalizer.py scripts/corvette_form_generator/ingest/expert_interpreter.py tests/test_order_guide_ingest_interpreter.py
# passed
```

Residual risks / follow-up:

- Duplicate classification is intentionally conservative: the first pass proves report value, not workbook apply readiness.
- ZR1/ZR1X remain out-of-scope/inactive scaffold contexts; their parsed source evidence is reported but not treated as canonical workbook truth.
- UI/server integration is deferred. The next pass should load Pass 3 interpretation artifacts into the Ingest Review UI as the default reduced review view while keeping raw Pass 1 candidates available as drill-down/debug.
