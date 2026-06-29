# Pass 2 — Interactive ingest review wizard spec

Date: 2026-06-27
Branch: `ingest-wizard`
Status: Implemented 2026-06-28.
Recommended reasoning level for implementation agent: high.

## Branch policy

Pass 0 and Pass 1 have been fast-forward merged into local `main`, then this branch was created from that merged main state:

```text
main -> ingest-wizard
```

Use `ingest-wizard` as the continuing ingest branch for the remaining ingest work. Do not create a new branch for every ingest pass unless Sean explicitly asks for an isolated branch.

## Purpose

Build an interactive review wizard for Pass 1 candidate artifacts.

The wizard should help a human reviewer inspect candidate options, OVS/status rows, rule hints, and unresolved items beside exact raw source evidence and current workbook context. It should make review decisions clearer and more repeatable without writing `stingray_master.xlsx` or generated/runtime files.

Pass 2 is a review/decision-capture pass only. It must not apply candidates to the workbook.

## Source basis

Current implemented inputs:

- Pass 0 evidence profiler:
  - `scripts/order_guide_ingest_profiler.py`
  - `scripts/corvette_form_generator/ingest/source_profiler.py`
  - evidence artifacts: `source-layout.json`, `variant-matrix.json`, `raw-rows.json`, `disclosure-links.json`, `manifest.json`, `checkpoint-report.md`
- Pass 1 candidate normalizer:
  - `scripts/order_guide_candidate_normalizer.py`
  - `scripts/corvette_form_generator/ingest/candidate_normalizer.py`
  - current implemented candidate artifacts: `candidate-options.json`, `candidate-ovs.json`, `candidate-rules.json`, `candidate-price-rules.json`, `candidate-summary.json`, `unresolved-review.md`
  - Pass 2 required candidate artifacts after prerequisite update: `candidate-options.json`, `candidate-ovs.json`, `candidate-rules.json`, `candidate-price-rules.json`, `candidate-summary.json`, `unresolved-review.json`, `unresolved-review.md`
- Existing local workbook editor:
  - `scripts/workbook_editor_server.py`
  - `scripts/corvette_form_generator/editor_ops.py`
  - `visualizer/workbook-editor/editor.js`
  - `visualizer/workbook-editor/editor.css`

Current editor behavior:

- Serves localhost-only UI from `127.0.0.1`.
- Derives workbook models, sheet families, schemas, references, and existing workbook context from `stingray_master.xlsx`.
- Exposes read endpoints for workbook payload, sheet payloads, lints, and compare views.
- Exposes write endpoints `/api/validate` and `/api/apply` for normal workbook-editor operations, but Pass 2 ingest wizard must not use apply as part of candidate review.

Current Pass 1 smoke output against the real raw export produced:

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

## Diagnosis

Pass 1 artifacts are useful but too large/noisy to review directly in JSON. The next bottleneck is human review quality:

- candidates need filtering by family, model, RPO, source sheet, status, and unresolved reason;
- every decision must show exact source evidence so the reviewer does not guess;
- current workbook matches/context must be visible next to candidate values;
- rule/disclosure hints need review states rather than hidden parser decisions;
- unresolved review needs machine-readable rows for filters, category counts, exact evidence display, and decision export;
- review decisions need to be captured as a durable artifact for a later apply pass;
- workbook writes remain too risky until the review-decision contract is proven.

Risk level: medium. This pass should not write the workbook, but it creates the review-decision contract that a later controlled apply pass may consume.

Change type: mixed tooling/UI/tests/docs, no workbook data/runtime behavior changes.

## Exact files to change after approval

Expected implementation files:

- `scripts/corvette_form_generator/ingest/candidate_normalizer.py`
  - first add a Pass 1-compatible `unresolved-review.json` artifact;
  - keep `unresolved-review.md` as the human-readable report;
  - do not duplicate unresolved derivation in the UI.
- `scripts/order_guide_candidate_normalizer.py`
  - no new write mode; continue routing through the protected output-dir guard.
- `scripts/workbook_editor_server.py`
  - add optional ingest candidate/evidence directory arguments;
  - add read-only ingest review API endpoints;
  - keep candidate review separate from `/api/apply`.
- `scripts/corvette_form_generator/ingest/review_payload.py`
  - load/validate Pass 0 + Pass 1 artifacts;
  - build UI-friendly candidate/review payloads;
  - join candidates to source evidence and current workbook context;
  - validate review-decision export shape.
- `visualizer/workbook-editor/editor.js`
  - add an `Ingest Review` tab;
  - render candidate lists, filters, detail panels, source evidence, workbook context, and review decision controls;
  - provide client-side export of review decisions.
- `visualizer/workbook-editor/editor.css`
  - styles for ingest review panels, evidence/source cells, status chips, unresolved badges, and decision controls.
- `tests/test_ingest_review_payload.py`
  - focused Python tests for payload construction, candidate/evidence joins, source-reference preservation, out-of-scope sections, and review-decision validation.
- `tests/test_order_guide_candidate_normalizer.py`
  - assert `unresolved-review.json` is emitted and contains categories, reasons, source refs, raw values, and candidate references without parsing Markdown.
- `tests/test_editor_server_payload.py` or a new server-focused test file
  - verify new `/api/ingest/*` endpoints are read-only and return expected payload/errors.
- `docs/ingest/pass-1/candidate-normalizer-spec.md`
  - update completion evidence after adding `unresolved-review.json` as a compatibility artifact for Pass 2.
- `docs/ingest/pass-2/interactive-review-wizard-spec.md`
  - close with implementation evidence after approval and implementation.
- `docs/ingest/README.md`
  - point to this Pass 2 spec and status.
- `Order-Guide_IngestPrompt.md`
  - remove the stale `docs/ingest/pass-2/normalized-ingest-contract.md` pointer;
  - clarify Pass 2 review-decision artifacts are still transient and not workbook rows.

No workbook binary/source sheet, generated runtime artifact, browser runtime app, registry, or dealer-submission file should be changed.

## Pass 1 unresolved JSON prerequisite

Pass 2 must not parse `unresolved-review.md` and must not recompute unresolved categories from raw Pass 0 evidence. Markdown remains a human-readable report only.

Before the review UI work, add a small machine-readable unresolved artifact to the Pass 1 normalizer:

```text
unresolved-review.json
```

Required top-level fields:

- `version`
- `run_id`
- `generated_at`
- `input_evidence_dir`
- `workbook`
- `unresolved_counts`
- `items`

Each item must include:

- `unresolved_id` — stable artifact-local ID.
- `reason` — stable filter key matching `candidate-summary.json.unresolved_counts` keys.
- `category` — broader UI grouping, such as `source_shape`, `rpo_identity`, `section_context`, `relationship_hint`, `price_out_of_scope`, or `color_trim_out_of_scope`.
- `severity` — `review`, `blocked`, or `out_of_scope`.
- `candidate_refs` — related `candidate_id` values when they exist.
- `source_refs` — exact Pass 0 evidence coordinates.
- `raw_values` — raw source values/status/disclosure markers needed for review.
- `normalized_values` — normalized parser values or empty object when no safe normalization exists.
- `blocked_decision` — concise statement of the decision that cannot be made mechanically.
- `suggested_decision_states` — allowed reviewer choices for this unresolved item.

Rules:

- The UI unresolved filters must read `unresolved-review.json`, not Markdown.
- `candidate-summary.json.artifact_files` must include `unresolved-review.json` after the compatibility update.
- Every unresolved item that points at source data must carry exact source evidence; summary-only unresolved rows are allowed only for whole-sheet out-of-scope notices and must say so explicitly.
- `unresolved-review.md` should be rendered from the same unresolved item data structure so JSON and Markdown counts cannot drift.

## Proposed server contract

Start command:

```sh
.venv/bin/python scripts/workbook_editor_server.py \
  --workbook stingray_master.xlsx \
  --ingest-evidence-dir /tmp/27vette-pass1-smoke-evidence \
  --ingest-candidates-dir /tmp/27vette-pass1-smoke-candidates
```

If no ingest directories are supplied, the workbook editor should continue working exactly as it does today and the Ingest Review tab may show a disabled/empty state.

New read-only endpoints:

```text
GET /api/ingest/summary
GET /api/ingest/candidates?family=<options|ovs|rules|price_rules|unresolved>&status=<...>&model=<...>&q=<...>
GET /api/ingest/candidate/<candidate_id>
GET /api/ingest/unresolved/<unresolved_id>
GET /api/ingest/source?sheet=<source_sheet>&row=<source_row_index>
```

Optional endpoint for validation only, no file or workbook write:

```text
POST /api/ingest/review/validate
```

`POST /api/ingest/review/validate` may validate a review-decision JSON payload and return errors/warnings. It must not write the workbook, candidate directory, evidence directory, `form-output`, or `form-app`.

Do not add a server-side review-decision save endpoint in this pass unless implementation proves a safe no-workbook-write path and this spec is revised before implementation. The default decision artifact should be exported client-side as a downloaded JSON file.

## Review UI contract

Add a top-level `Ingest Review` tab to the existing workbook editor.

Required panels:

1. Run summary
   - Pass 0 manifest status and paths.
   - Pass 1 candidate counts and unresolved counts.
   - Candidate/evidence artifact timestamps, file sizes, and hashes/mtimes.
   - Clear banner that this tab is review-only and cannot apply workbook changes.

2. Candidate browser
   - Filter by candidate family.
   - Filter by model, variant, source sheet, RPO, status, resolution status, and unresolved reason where available.
   - Text search over candidate IDs, RPOs, raw description, workbook match, source sheet, and review notes.
   - Pagination or virtualization; the real smoke produced 11,244 OVS candidates and must not freeze the browser.

3. Candidate detail panel
   - Candidate envelope fields.
   - Exact source refs from Pass 0.
   - Raw values and normalized review values side-by-side.
   - Current workbook match/context when exact.
   - Linked OVS/status cells for option candidates.
   - Linked disclosure/rule candidates for option candidates.
   - Linked option candidate for OVS/rule candidates.

4. Source evidence panel
   - Source sheet name, row, row span, and cell coordinates.
   - Raw orderable/ref-only RPO, description, status cells, marker(s), and raw variant header(s).
   - Disclosure fragment(s) and marker link(s).
   - No hidden interpretation: if a rule/action/target is only a hint, label it as a hint.

5. Workbook context panel
   - Existing workbook option match if present.
   - Existing model/variant context.
   - Existing section context, option ID, option name, section, active/selectable/display behavior where available.
   - Reference-domain choices from existing editor payload, but displayed as context only.

6. Review decision panel
   - Legacy Pass 2 per-candidate decision states:
     - `accept_for_later_apply`
     - `edit_before_apply`
     - `skip`
     - `needs_source_review`
     - `blocked_out_of_scope`
   - Reviewer notes.
   - Optional proposed target family and canonical key fields, still review decisions only.
   - No direct workbook queueing by default.
   - Current direction note: these abstract states were later proven too vague for ZR1/ZR1X intake. Pass 5 replaces them as primary reviewer language with workbook-destination actions.

7. Export decisions
   - Download a review-decision JSON artifact.
   - Include run metadata, workbook path/mtime, evidence/candidate artifact fingerprints, reviewer timestamp, decisions, and unresolved items.
   - Historical Pass 2 note: the exported artifact was originally expected to feed apply planning. Current direction routes through Pass 3, Pass 4, and then Pass 5 focused workbook-build review before any dry-run apply planning.

## Review-decision artifact contract

Exported file name suggestion:

```text
ingest-review-decisions-<run-id>.json
```

Required top-level fields:

- `version`
- `created_at`
- `workbook`
  - `path`
  - `mtime_ns`
- `evidence_dir`
- `candidates_dir`
- `evidence_artifacts`
  - per-file `path`, `mtime_ns`, `size_bytes`, and `sha256`
- `candidate_artifacts`
  - per-file `path`, `mtime_ns`, `size_bytes`, and `sha256`
- `candidate_summary`
- `decisions`
- `unresolved_rollup`
- `notes`

Each decision must include:

- `candidate_id`
- `candidate_family`
- `decision_state`
- `reviewer_notes`
- `source_refs`
- `raw_values_snapshot`
- `normalized_values_snapshot`
- `workbook_match_snapshot`
- optional `proposed_target`
  - `sheet_family`
  - `model_key`
  - `canonical_key`
  - `field_overrides`

Each unresolved decision must include:

- `unresolved_id`
- `reason`
- `category`
- `decision_state`
- `reviewer_notes`
- `source_refs`
- `raw_values_snapshot`
- `normalized_values_snapshot`
- optional `candidate_refs`

Rules:

- `proposed_target` is still not an applied workbook op.
- Do not use row numbers as stable workbook targets.
- Preserve raw and normalized snapshots so later apply planning can detect stale candidate drift.
- Preserve candidate/evidence file fingerprints so Pass 3 can detect regenerated `/tmp` artifacts at the same path.
- Validation must fail if a decision lacks source refs or if `decision_state` is outside the allowed vocabulary.

## Explicit no-write boundaries

Pass 2 must not:

- write `stingray_master.xlsx`;
- write generated workbook `form_*` sheets;
- write tracked generated outputs under `form-output/*`;
- write `form-app/data.js`;
- regenerate model artifacts;
- promote models;
- POST to the dealer endpoint;
- call `/api/apply` from the ingest review UI;
- convert review decisions into workbook ops;
- infer price/interior/color candidates that Pass 1 explicitly marked out of scope.

The existing workbook editor's normal Pending Changes / Apply feature may remain available for routine workbook editing, but the Ingest Review tab must not enqueue or apply ingest-derived workbook ops in this pass.

## Companion-file impact check

| Surface | Status for Pass 2 implementation | Notes |
|---|---|---|
| Workbook source sheets | inspected-no-change | Read-only context only. |
| Pass 0 evidence artifacts | inspected-no-change | UI consumes current contract; if new evidence fields are needed, revise Pass 0/Pass 1 specs first. |
| Pass 1 candidate artifacts | update | Add `unresolved-review.json`; update candidate summary artifact list; keep Markdown as companion report. |
| `form-output/*` tracked generated outputs | not applicable | Must remain unchanged. Smoke artifacts should stay under `/tmp`. |
| `form-app/data.js` | not applicable | Must remain unchanged. |
| Runtime app JS/CSS/HTML | not applicable | Workbook-editor UI is dev tooling, not customer runtime. |
| Dealer submission | not applicable | No dealer endpoint/payload changes. |
| Workbook editor server | update | Add read-only ingest endpoints and optional startup args. |
| Workbook editor UI | update | Add Ingest Review tab and styles. |
| Tests | update | Add focused payload/server tests. Browser smoke optional but recommended after UI implementation. |
| `Order-Guide_IngestPrompt.md` | update | Remove stale contract path, add `unresolved-review.json`, and add Pass 2 review-decision artifact boundary. |
| `docs/ingest/README.md` | update | Point to this Pass 2 spec/status. |
| Agent/project guidance | inspected-no-change | Existing guardrails cover no workbook/generated writes. |

## Constraints

- Continue on the single `ingest-wizard` branch.
- No new branch per ingest pass.
- No workbook writes.
- No generated/runtime/app data writes.
- No model promotion.
- No new dependencies unless separately approved.
- Use existing workbook-editor patterns before adding a separate web app.
- Preserve exact source coordinates and raw evidence in every review detail.
- Use `unresolved-review.json` for unresolved filters/categories/evidence; do not parse Markdown for UI data.
- Keep rule/detail-disclosure interpretation review-only.
- Keep price/interior/color extraction out of scope until their evidence extractors exist.
- Keep browser UI responsive for thousands of candidates.

## Non-goals

- No canonical workbook apply.
- No apply manifest.
- No safe-save workflow.
- No regeneration or registry publication.
- No customer runtime changes.
- No price schedule extractor.
- No Color and Trim/interior extractor.
- No copy-cleanup workflow.
- No automatic option ID, section ID, rule, group, price, interior, or display-order assignment.

## Risks and mitigations

1. Review UI accidentally becomes an apply UI.
   - Mitigation: Ingest Review exports decision JSON only; it must not call `/api/apply` or enqueue workbook ops.

2. Candidate volume makes the UI unusable.
   - Mitigation: require filters and pagination/virtualized rendering; test against real candidate counts.

3. Reviewers lose source context.
   - Mitigation: candidate detail must show exact source refs, raw cells, status markers, and disclosure fragments.

4. Decisions become stale after artifacts or workbook change.
   - Mitigation: export workbook mtime, candidate/evidence artifact fingerprints, candidate snapshots, and source refs for later stale checks.

5. UI implies confidence that parser does not have.
   - Mitigation: surface `resolution_status`, `confidence`, unresolved reasons, and review notes prominently.

6. Existing editor apply endpoint creates safety confusion.
   - Mitigation: add explicit copy/UI separation: normal workbook editor Apply exists, but ingest review decisions are export-only in Pass 2.

## Validation plan

Before implementation:

```sh
git status --short --branch
.venv/bin/python -m pytest tests/test_order_guide_ingest_profiler.py tests/test_order_guide_candidate_normalizer.py -q
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Implementation tests:

```sh
.venv/bin/python -m pytest tests/test_order_guide_candidate_normalizer.py tests/test_ingest_review_payload.py tests/test_editor_server_payload.py -q
.venv/bin/python -m py_compile \
  scripts/order_guide_candidate_normalizer.py \
  scripts/workbook_editor_server.py \
  scripts/corvette_form_generator/ingest/candidate_normalizer.py \
  scripts/corvette_form_generator/ingest/review_payload.py
```

Manual smoke setup:

```sh
rm -rf /tmp/27vette-pass2-evidence /tmp/27vette-pass2-candidates
.venv/bin/python scripts/order_guide_ingest_profiler.py \
  --raw-export "2027 Chevrolet Car Corvette Export_RAW.xlsx" \
  --workbook stingray_master.xlsx \
  --run-id pass2-smoke-evidence \
  --output-dir /tmp/27vette-pass2-evidence
.venv/bin/python scripts/order_guide_candidate_normalizer.py \
  --evidence-dir /tmp/27vette-pass2-evidence \
  --workbook stingray_master.xlsx \
  --run-id pass2-smoke-candidates \
  --output-dir /tmp/27vette-pass2-candidates
.venv/bin/python scripts/workbook_editor_server.py \
  --workbook stingray_master.xlsx \
  --ingest-evidence-dir /tmp/27vette-pass2-evidence \
  --ingest-candidates-dir /tmp/27vette-pass2-candidates
```

Manual browser smoke:

- Open `http://127.0.0.1:8027/`.
- Open `Ingest Review` tab.
- Confirm summary counts match `candidate-summary.json`.
- Confirm unresolved filters and unresolved detail panels are driven by `unresolved-review.json`.
- Filter options by a known RPO and inspect source evidence/workbook context.
- Open a rule candidate and confirm disclosure fragment and target token hints are visible as hints.
- Open unresolved categories for price schedule and color/trim and confirm they are blocked/out-of-scope.
- Set several decision states and export review-decision JSON.
- Confirm browser console has no JavaScript errors.

Post-implementation guards:

```sh
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
git diff --check -- scripts tests visualizer docs Order-Guide_IngestPrompt.md
git diff --exit-code -- stingray_master.xlsx form-app/data.js
git diff --exit-code -- $(git ls-files form-output)
git status --short -- form-output
```

No customer runtime Node tests are required unless implementation touches runtime/generated/browser app files, which would be a scope violation. If only workbook-editor UI changes, focused Python tests plus manual localhost browser smoke are the relevant gates.

## Implementation completion — 2026-06-28

Implemented after approval on the single `ingest-wizard` branch.

Changed files:

- `scripts/corvette_form_generator/ingest/candidate_normalizer.py` — emits `unresolved-review.json` alongside the Markdown report, from the same unresolved item data.
- `scripts/corvette_form_generator/ingest/review_payload.py` — new read-only Pass 2 payload/fingerprint/decision-validation helper.
- `scripts/workbook_editor_server.py` — optional `--ingest-evidence-dir` and `--ingest-candidates-dir` args plus read-only `/api/ingest/*` endpoints and decision validation.
- `visualizer/workbook-editor/editor.js` — new `Ingest Review` tab with candidate/unresolved browsing, detail panels, review decisions, validation, and client-side decision export.
- `visualizer/workbook-editor/editor.css` — styles for the Ingest Review panels, candidate list, metrics, JSON evidence blocks, and decision controls.
- `tests/test_order_guide_candidate_normalizer.py` — asserts machine-readable unresolved JSON output and artifact list.
- `tests/test_ingest_review_payload.py` — focused review payload, fingerprint, source lookup, and decision-validation tests.
- `tests/test_editor_server_ingest_review.py` — server endpoint tests for read-only ingest summary/list/detail/source/validation paths.
- `docs/ingest/pass-1/candidate-normalizer-spec.md` — updated Pass 1 artifact contract and completion evidence for the `unresolved-review.json` compatibility artifact.
- `docs/ingest/pass-2/interactive-review-wizard-spec.md` — closed this spec with implementation evidence.
- `docs/ingest/README.md` — marked Pass 2 as implemented.

Implemented behavior:

- Pass 1 now emits `unresolved-review.json` with categories, severities, candidate refs, exact source refs, raw/normalized values, blocked decisions, and suggested decision states.
- The workbook editor still works without ingest directories; the Ingest Review tab shows a disabled/empty state.
- When ingest directories are supplied, the server exposes read-only endpoints for summary, candidates, candidate detail, unresolved detail, source evidence, and decision validation.
- The UI displays candidate counts, unresolved counts, artifact fingerprints including `sha256`, candidate/unresolved filters, source/raw/normalized/workbook context, and review decision controls.
- Review decisions export client-side as JSON with workbook metadata, evidence/candidate artifact fingerprints, candidate snapshots, unresolved decisions, and notes.
- The Ingest Review tab does not enqueue workbook ops and does not call `/api/apply`.

Validation evidence:

```sh
.venv/bin/python -m pytest tests/test_order_guide_ingest_profiler.py tests/test_order_guide_candidate_normalizer.py tests/test_ingest_review_payload.py tests/test_editor_server_ingest_review.py tests/test_editor_server_payload.py -q
# 32 passed

.venv/bin/python -m py_compile scripts/order_guide_ingest_profiler.py scripts/order_guide_candidate_normalizer.py scripts/workbook_editor_server.py scripts/corvette_form_generator/ingest/source_profiler.py scripts/corvette_form_generator/ingest/candidate_normalizer.py scripts/corvette_form_generator/ingest/review_payload.py tests/test_order_guide_ingest_profiler.py tests/test_order_guide_candidate_normalizer.py tests/test_ingest_review_payload.py tests/test_editor_server_ingest_review.py
# passed

node --check visualizer/workbook-editor/editor.js
# passed

.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
# valid; 0 issues

git diff --check -- scripts tests visualizer docs Order-Guide_IngestPrompt.md
# passed

git diff --exit-code -- stingray_master.xlsx form-app/data.js
git diff --exit-code -- $(git ls-files form-output)
git status --short -- form-output
# no output
```

Manual smoke:

```text
Pass 0 -> /tmp/27vette-pass2-smoke-evidence: status passed; 23 source sheets; 20 parsed matrix sheets; 1964 raw rows; 130 variant columns; 1088 disclosure links.
Pass 1 -> /tmp/27vette-pass2-smoke-candidates: status passed; options 1744; ovs 11244; rules 791; price_rules 0; unresolved items 938.
Server API smoke on http://127.0.0.1:8027: /api/ingest/summary, /api/ingest/candidates, /api/ingest/source, and /api/ingest/review/validate returned expected JSON.
Browser smoke: opened Ingest Review tab, confirmed summary counts and candidate detail panels load, and browser console reported 0 JavaScript errors.
```

Known residual issue:

- A broader editor test sweep also ran and reported 99 passed / 3 failed in `tests/test_editor_lints.py` real-workbook assertions (`opt_rwj_001`, `opt_cj2_001`, `opt_drz_001`). Those failures are in existing lint/compare real-workbook expectations and are not caused by the Pass 2 ingest review code path; they are left for a separate workbook/editor-lint expectation cleanup pass.

## Expected next pass after Pass 2

Historical note: this originally pointed directly to controlled apply planning. Sean corrected the next-step direction on 2026-06-28 after reviewing the Pass 2 UI: Pass 3 first added expert interpretation and review reduction, scoped in `docs/ingest/pass-3/expert-interpretation-review-reduction-spec.md`; Pass 4 put that reduced queue in the browser, scoped in `docs/ingest/pass-4/reduced-review-ui-spec.md`. User review of Pass 4 showed the broad reduced queue and abstract decision labels were still not usable for the actual ZR1/ZR1X intake task. Pass 5, scoped in `docs/ingest/pass-5/focused-model-workbook-build-review-spec.md`, is now required before apply planning: select target models after Pass 0 header/model profiling and review concrete workbook-destination lanes.
