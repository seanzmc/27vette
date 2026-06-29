# Pass 4 — Reduced Ingest Review UI over Pass 3 interpretation artifacts

Date: 2026-06-28
Branch: `ingest-wizard`
Status: Implemented 2026-06-28 as read-only reduced Ingest Review server/UI integration. Browser manual review remains pending.
Recommended reasoning level for implementation agent: high.

## Purpose

Pass 4 should make the existing local workbook-editor Ingest Review tab useful for real order-guide review by defaulting it to the Pass 3 reduced model/RPO interpretation queue instead of the raw Pass 1 candidate surface.

Pass 3 proved that the raw current smoke surface can be reduced from 14,717 raw candidate/unresolved rows to 1,057 interpreted model/RPO units, with 200 strict `auto_confirmed` units hidden from the active review queue and 855 visible non-blocked review units. Pass 4 should expose that reduced queue in the browser, preserve raw candidate drill-down for evidence/debug, and still write no workbook, generated runtime, or dealer-submission changes.

This is still pre-apply review. It must not create workbook operations, apply manifests, generated artifacts, runtime app data, or model-promotion changes.

## Diagnosis

Current implemented state:

- Pass 0 source profiler writes read-only evidence artifacts.
- Pass 1 candidate normalizer writes raw candidate/unresolved artifacts.
- Pass 2 workbook-editor Ingest Review tab reads Pass 1 artifacts and lists raw candidate families: `options`, `ovs`, `rules`, `price_rules`, and `unresolved`.
- Pass 3 CLI interpreter writes reduced interpretation artifacts, but the local workbook-editor server/UI does not yet load or display them.

Root issue:

- The UI still defaults to raw candidate review, so it does not use the Pass 3 expert interpretation/reduction layer that was created specifically to avoid manual review of the raw ~10k+ candidate surface.

Evidence inspected:

- `docs/ingest/pass-3/expert-interpretation-review-reduction-spec.md`
  - Pass 3 completion evidence says UI/server integration is deferred and should be the next pass.
  - Smoke output: `raw_candidate_total 14717`, `interpreted_option_count 1057`, `hidden_auto_confirmed_count 200`, `visible_review_queue_count 855`, `blocked_count 5`, `reduction_status material_reduction`.
- `scripts/corvette_form_generator/ingest/review_payload.py`
  - `IngestReviewStore` currently loads Pass 0/1 only: `EVIDENCE_FILES`, `CANDIDATE_FILES`, raw candidate families, `summary()`, `list_candidates()`, `candidate()`, `unresolved()`, and `source()`.
  - `validate_review_decisions()` validates raw candidate and unresolved decisions only.
- `scripts/workbook_editor_server.py`
  - Existing read-only endpoints are `/api/ingest/summary`, `/api/ingest/candidates`, `/api/ingest/candidate/<id>`, `/api/ingest/unresolved/<id>`, `/api/ingest/source`, and `/api/ingest/review/validate`.
  - Startup args currently accept `--ingest-evidence-dir` and `--ingest-candidates-dir`, not `--ingest-interpretation-dir`.
- `visualizer/workbook-editor/editor.js`
  - `IngestReviewTab()` fetches `/api/ingest/summary`, defaults `family` to `options`, lists raw candidates via `/api/ingest/candidates`, and exports raw candidate/unresolved decisions with notes saying the export is not a workbook apply manifest.
- `visualizer/workbook-editor/editor.css`
  - Existing `.ingest-*`, `.metric`, `.jsonblock`, and `.badge` styles can support a reduced queue with small targeted additions.
- `tests/test_ingest_review_payload.py`
  - Covers Pass 2 store summary/list/detail/source/decision validation.
- `tests/test_editor_server_ingest_review.py`
  - Covers existing read-only server endpoints and workbook mtime preservation.
- `tests/test_order_guide_ingest_interpreter.py`
  - Provides fixture helpers and Pass 3 artifact generation patterns that Pass 4 tests can reuse.

Risk level: medium.

- Medium because this touches dev-only server/UI behavior and review export shape.
- Low live-customer risk if scope is respected: no workbook writes, generated runtime writes, app runtime changes, dealer payload changes, or model promotion.

Change type: mixed tooling/UI/tests/docs. Not workbook/data, not generated runtime, not customer runtime.

## Exact files to change after approval

Implementation files:

1. `scripts/corvette_form_generator/ingest/review_payload.py`
   - Extend `IngestReviewStore` to optionally load Pass 3 interpretation artifacts.
   - Add interpretation artifact fingerprinting and schema validation.
   - Add reduced-review list/detail methods.
   - Extend decision validation for interpretation-level review decisions.

2. `scripts/workbook_editor_server.py`
   - Add `--ingest-interpretation-dir` startup arg.
   - Wire optional interpretation artifact loading into `IngestReviewStore`.
   - Add read-only endpoints for Pass 3 reduced artifacts.

3. `visualizer/workbook-editor/editor.js`
   - Change the default Ingest Review view to the reduced Pass 3 review queue when interpretation artifacts are configured.
   - Keep raw Pass 1 candidates available as drill-down/debug.
   - Export interpretation-level review decisions with artifact fingerprints and source snapshots.

4. `visualizer/workbook-editor/editor.css`
   - Add only small targeted styles for reduced queue metrics, confidence/reason badges, source occurrence display, and report panels.
   - Preserve existing workbook-editor layout and behavior.

Tests:

5. `tests/test_ingest_review_payload.py`
   - Add store-level coverage for optional interpretation artifacts, reduced queue listing/filtering, detail lookup, report summaries, raw candidate drill-down availability, and interpretation decision validation.

6. `tests/test_editor_server_ingest_review.py`
   - Add server endpoint coverage for interpretation-enabled startup/store state, reduced review endpoints, raw fallback endpoints, validation, and read-only workbook mtime preservation.

7. `tests/test_order_guide_ingest_interpreter.py`
   - Prefer reusing existing fixture helpers from this test rather than duplicating workbook/raw-export fixtures. Add helper exports only if needed and keep behavior assertions in the Pass 4 tests.

Docs/specs:

8. `docs/ingest/pass-4/reduced-review-ui-spec.md`
   - Update status/completion evidence after implementation.

9. `docs/ingest/README.md`
   - Add Pass 4 as the current spec/implementation status.

10. `Order-Guide_IngestPrompt.md`
    - Add the Pass 4 review UI stage to the staged ingest workflow after Pass 3 and before apply planning.

11. `docs/ingest/pass-3/expert-interpretation-review-reduction-spec.md`
    - After implementation, update the Pass 3 next-pass line only if it would otherwise still read like Pass 4 has not been started/implemented. Keep historical completion evidence intact.

Do not change:

- `stingray_master.xlsx`
- tracked `form-output/*`
- `form-app/data.js`
- customer-facing `form-app/*` runtime files
- dealer submission endpoint, payload, Turnstile behavior, or WordPress integration
- model registry/promotion metadata

## Companion-file impact check

| Surface | Status for this spec | Required Pass 4 handling |
|---|---|---|
| Workbook/source data | Not applicable | No workbook writes or row edits. Keep `stingray_master.xlsx` read-only. |
| Generated runtime contracts / `form-output/*` | Not applicable | Do not regenerate or hand-edit tracked generated runtime artifacts. Use `/tmp` or run-scoped ingest dirs for smoke artifacts only. |
| `form-app/data.js` / customer runtime | Not applicable | No changes. Verify clean diff. |
| Dev workbook-editor server | Update | Add optional interpretation-dir arg and read-only endpoints. Preserve existing Pass 1 endpoints. |
| Dev workbook-editor UI | Update | Default to reduced Pass 3 review queue when configured; keep raw candidate drill-down/debug. |
| Review decision export schema | Update | Add interpretation-level decisions while preserving raw candidate/unresolved decisions for drill-down. Keep export explicitly non-apply. |
| Existing Pass 2 payload/server tests | Update | Extend rather than replace; existing raw candidate behaviors must remain covered. |
| Pass 3 interpreter tests | Inspected-no-change by default | Reuse helpers if needed; do not change interpreter semantics unless tests reveal a real defect. |
| Docs/specs | Update | Add this Pass 4 spec to docs index/prompt; close spec after implementation. |
| Gate reminders / AGENTS.md / profile guidance | Inspected-no-change expected | No standing gate change unless implementation discovers stale workflow guidance. |
| Dealer submission | Not applicable | Explicitly unchanged. |

## Required behavior

### Startup and disabled states

Current startup remains valid:

```sh
.venv/bin/python scripts/workbook_editor_server.py \
  --ingest-evidence-dir /tmp/27vette-pass3-evidence \
  --ingest-candidates-dir /tmp/27vette-pass3-candidates
```

Pass 4 adds optional interpretation artifacts:

```sh
.venv/bin/python scripts/workbook_editor_server.py \
  --ingest-evidence-dir /tmp/27vette-pass3-evidence \
  --ingest-candidates-dir /tmp/27vette-pass3-candidates \
  --ingest-interpretation-dir /tmp/27vette-pass3-interpretation
```

Rules:

- If no ingest dirs are configured, the existing disabled summary remains.
- If evidence/candidate dirs are configured without interpretation dir, existing Pass 2 raw review remains available and unchanged.
- If interpretation dir is configured, evidence and candidate dirs must also be configured.
- If interpretation artifacts are missing or malformed, fail closed with a clear server error. Do not silently fall back to raw review while implying the reduced queue is active.

### Server/store contract

`IngestReviewStore.summary()` should include interpretation state when configured:

```json
{
  "enabled": true,
  "mode": "interpretation",
  "interpretation_enabled": true,
  "interpretation_dir": "/tmp/27vette-pass3-interpretation",
  "interpretation_artifacts": {
    "interpretation-summary.json": { "path": "...", "mtime_ns": "...", "size_bytes": 123, "sha256": "..." }
  },
  "interpretation_summary": {
    "raw_candidate_total": 14717,
    "interpreted_option_count": 1057,
    "hidden_auto_confirmed_count": 200,
    "visible_review_queue_count": 855,
    "mechanical_safe_count": 9,
    "review_needed_count": 846,
    "blocked_count": 5,
    "duplicate_rpo_count": 1023,
    "conflicting_duplicate_count": 2,
    "reduction_status": "material_reduction"
  }
}
```

When interpretation is not configured, summary should expose:

```json
{
  "mode": "raw_candidates",
  "interpretation_enabled": false
}
```

Required read-only endpoints:

- Existing endpoints remain:
  - `GET /api/ingest/summary`
  - `GET /api/ingest/candidates?...`
  - `GET /api/ingest/candidate/<candidate_id>`
  - `GET /api/ingest/unresolved/<unresolved_id>`
  - `GET /api/ingest/source?sheet=<sheet>&row=<row>`
  - `POST /api/ingest/review/validate`
- New endpoints:
  - `GET /api/ingest/interpretations?confidence=&model=&reason=&duplicate=&q=&offset=&limit=`
    - Lists reduced visible queue by default: `mechanical_safe`, `review_needed`, and `blocked` interpretation units.
    - Must not include `auto_confirmed` unless `include_auto=true` is explicitly provided.
  - `GET /api/ingest/interpretation/<interpretation_id>`
    - Returns one interpreted model/RPO unit with source occurrences, availability matrix, workbook identity/status context, disclosure evidence, duplicate classification, reason codes, and confidence.
  - `GET /api/ingest/interpretation/reports/duplicates`
    - Returns duplicate report JSON.
  - `GET /api/ingest/interpretation/reports/source-coverage`
    - Returns source-sheet coverage JSON.
  - Optional if useful for UI layout: `GET /api/ingest/interpretation/blocked`
    - Returns `blocked-interpretation.json`.

Do not add POST apply endpoints.

### UI default behavior

When `summary.interpretation_enabled` is true:

- The Ingest Review tab defaults to a reduced queue, not raw Pass 1 candidates.
- Header metrics must show at least:
  - raw candidate total
  - interpreted model/RPO units
  - visible review queue
  - hidden auto-confirmed
  - mechanical-safe
  - review-needed
  - blocked
  - duplicate RPO count
  - reduction status
- The row list should show model/RPO review units with:
  - model key
  - RPO
  - confidence badge
  - duplicate classification badge
  - review reason chips
  - source occurrence count
  - concise workbook match/status summary
- Default filters should prioritize review work:
  - `mechanical_safe`
  - `review_needed`
  - `blocked`
  - `all visible`
  - optional explicit `auto_confirmed` audit view, off by default.
- Search should match model, RPO, reason codes, source descriptions, source sheet, workbook option ID, duplicate classification, and confidence.
- Selecting a row should show detail panels for:
  - reviewer decision
  - expert summary
  - source occurrences with buttons/links to load source rows through `/api/ingest/source`
  - availability matrix
  - workbook identity/status match
  - disclosure/rule evidence
  - duplicate classification and source-sheet roles
  - raw JSON fallback panel.

When interpretation is not configured:

- Existing Pass 2 raw candidate UI remains available and should not regress.
- The UI should clearly label the mode as raw candidate review.

### Raw candidate drill-down/debug

The Pass 4 reduced UI must keep raw Pass 1 candidates accessible.

Acceptable implementation:

- Add a mode toggle inside the Ingest Review tab:
  - `Reduced review` default when Pass 3 artifacts exist.
  - `Raw candidates` for Pass 1/debug.
- Or keep raw candidates in collapsible detail/drill-down panels.

Required behavior:

- Raw candidate endpoints remain unchanged.
- Raw candidate decision export remains possible for debug/manual workflows.
- Source-row drill-down remains available from both reduced and raw views.

### Decision export and validation

Pass 4 review export remains explicitly non-apply.

When interpretation artifacts are configured, `Export decisions JSON` should include:

```json
{
  "version": 2,
  "review_mode": "interpretation",
  "workbook": { "path": "...", "mtimeNs": "..." },
  "evidence_dir": "...",
  "candidates_dir": "...",
  "interpretation_dir": "...",
  "evidence_artifacts": {},
  "candidate_artifacts": {},
  "interpretation_artifacts": {},
  "interpretation_summary": {},
  "interpretation_decisions": [
    {
      "interpretation_id": "interpopt-stingray-eri",
      "model_key": "stingray",
      "rpo": "ERI",
      "interpretation_confidence": "review_needed",
      "decision_state": "accept_for_later_apply",
      "reviewer_notes": "...",
      "review_reason_codes": [],
      "source_occurrences_snapshot": [],
      "availability_matrix_snapshot": {},
      "workbook_identity_match_snapshot": {},
      "workbook_status_match_snapshot": {},
      "duplicate_classification_snapshot": "single_source"
    }
  ],
  "raw_candidate_decisions": [],
  "unresolved_decisions": [],
  "notes": "Exported from Pass 4 reduced Ingest Review; not a workbook apply manifest."
}
```

Validation rules:

- `interpretation_decisions[*].decision_state` must be one of the existing allowed states:
  - `accept_for_later_apply`
  - `edit_before_apply`
  - `skip`
  - `needs_source_review`
  - `blocked_out_of_scope`
- Each interpretation decision must include:
  - `interpretation_id`
  - `model_key`
  - `rpo`
  - `interpretation_confidence`
  - `source_occurrences_snapshot` with at least one source occurrence
  - workbook identity/status snapshots, even if the match is missing or not compared.
- The validator must continue accepting existing Pass 2 raw decision payloads for compatibility.
- No export field is an apply operation. Apply planning remains a separate later pass.

### Visual preservation

- Keep the existing workbook-editor visual system.
- Do not redesign the workbook editor or rename top-level tabs.
- Small additions are allowed for reduced queue badges, metrics, source occurrence lists, and report panels.
- The Ingest Review tab label can remain `Ingest Review`; inside the tab, label the active mode as `Reduced review` or `Raw candidates`.

### Strict boundaries

Pass 4 must not:

- write `stingray_master.xlsx`
- write or regenerate tracked `form-output/*`
- write `form-app/data.js`
- change customer runtime behavior
- change dealer submission behavior
- infer workbook operations from review decisions
- auto-hide non-`auto_confirmed` units from visible review
- treat ZR1/ZR1X inactive workbook scaffolds as canonical truth
- compare raw GM description copy to workbook/form copy for identity

## Acceptance criteria

Functional acceptance:

1. Starting the editor with Pass 0/1/3 dirs shows `Ingest Review` in reduced interpretation mode by default.
2. Summary metrics match `interpretation-summary.json`.
3. The default visible queue excludes `auto_confirmed` units.
4. `auto_confirmed` units are available only through an explicit audit/include-auto control.
5. Selecting a reduced row shows source occurrences, availability matrix, workbook identity/status context, duplicate classification, reason codes, and raw JSON.
6. Source occurrence links call `/api/ingest/source` and return the original Pass 0 source row.
7. Raw Pass 1 candidate view remains available and existing filters/detail behavior still work.
8. Decision export includes interpretation artifact fingerprints and interpretation decision snapshots.
9. Decision validation rejects malformed interpretation decisions and still accepts existing raw Pass 2 decisions.
10. Workbook mtime is unchanged by server endpoint and UI test workflows.

Safety acceptance:

1. `git diff --exit-code -- stingray_master.xlsx form-app/data.js` passes.
2. `git diff --exit-code -- $(git ls-files form-output)` passes.
3. No new apply endpoint or workbook operation path is added.
4. Server/UI labels continue to say review-only / not an apply manifest.

## Tests to write before implementation

Use TDD for implementation.

Store tests in `tests/test_ingest_review_payload.py`:

- Build Pass 0/1/3 fixture artifacts in a temp dir.
- Instantiate `IngestReviewStore(..., interpretation_dir=<dir>)`.
- Assert `summary()` reports `mode: interpretation`, artifact fingerprints, and interpretation metrics.
- Assert `list_interpretations()` returns visible rows by default and excludes `auto_confirmed` unless explicitly requested.
- Assert filters for confidence/model/reason/duplicate/q.
- Assert `interpretation(<id>)` returns source occurrences and workbook context.
- Assert raw `list_candidates()` still works.
- Assert `validate_review_decisions()` accepts well-formed interpretation decisions and rejects missing `source_occurrences_snapshot` / missing RPO / invalid decision state.
- Assert old Pass 2 raw decision payloads still validate.

Server tests in `tests/test_editor_server_ingest_review.py`:

- Configure `EditorHandler.ingest_review` with interpretation artifacts.
- Assert `/api/ingest/summary` reports interpretation mode.
- Assert `/api/ingest/interpretations` lists visible reduced units.
- Assert `/api/ingest/interpretations?include_auto=true` can include auto-confirmed audit rows.
- Assert `/api/ingest/interpretation/<id>` returns detail.
- Assert duplicate/source-coverage report endpoints return JSON.
- Assert existing `/api/ingest/candidates`, `/api/ingest/candidate/<id>`, `/api/ingest/unresolved/<id>`, and `/api/ingest/source` still work.
- Assert workbook mtime does not change.

UI syntax/smoke tests:

- `node --check visualizer/workbook-editor/editor.js`
- If a browser smoke is run, serve only the local dev editor and verify manually:
  - reduced mode loads by default with Pass 3 dirs
  - raw candidate mode still works
  - export JSON contains `review_mode: interpretation`
  - no workbook apply queue is populated by ingest review decisions.

## Validation plan

Required commands after implementation:

```sh
.venv/bin/python -m pytest \
  tests/test_order_guide_ingest_profiler.py \
  tests/test_order_guide_candidate_normalizer.py \
  tests/test_order_guide_ingest_interpreter.py \
  tests/test_ingest_review_payload.py \
  tests/test_editor_server_ingest_review.py -q

node --check visualizer/workbook-editor/editor.js

.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx

git diff --check -- scripts tests visualizer docs Order-Guide_IngestPrompt.md

git diff --exit-code -- stingray_master.xlsx form-app/data.js

git diff --exit-code -- $(git ls-files form-output)

git status --short -- form-output
```

Manual smoke after tests:

```sh
rm -rf /tmp/27vette-pass4-evidence /tmp/27vette-pass4-candidates /tmp/27vette-pass4-interpretation

.venv/bin/python scripts/order_guide_ingest_profiler.py \
  --raw-export "2027 Chevrolet Car Corvette Export_RAW.xlsx" \
  --workbook stingray_master.xlsx \
  --run-id pass4-smoke-evidence \
  --output-dir /tmp/27vette-pass4-evidence

.venv/bin/python scripts/order_guide_candidate_normalizer.py \
  --evidence-dir /tmp/27vette-pass4-evidence \
  --workbook stingray_master.xlsx \
  --run-id pass4-smoke-candidates \
  --output-dir /tmp/27vette-pass4-candidates

.venv/bin/python scripts/order_guide_ingest_interpreter.py \
  --evidence-dir /tmp/27vette-pass4-evidence \
  --candidates-dir /tmp/27vette-pass4-candidates \
  --workbook stingray_master.xlsx \
  --run-id pass4-smoke-interpretation \
  --output-dir /tmp/27vette-pass4-interpretation

.venv/bin/python scripts/workbook_editor_server.py \
  --ingest-evidence-dir /tmp/27vette-pass4-evidence \
  --ingest-candidates-dir /tmp/27vette-pass4-candidates \
  --ingest-interpretation-dir /tmp/27vette-pass4-interpretation
```

Open `http://127.0.0.1:8027/` and verify the reduced Ingest Review behavior manually. Stop before any apply-like workflow; there should be none.

## Risks and non-goals

Risks:

- Review export shape changes can confuse later apply-planning work if not clearly versioned. Use `version: 2` and `review_mode: interpretation`.
- UI could accidentally hide important rows if it treats `auto_confirmed` too broadly. The UI must trust Pass 3 confidence labels and default-hide only `auto_confirmed`.
- Server fallback could mislead reviewers if interpretation artifacts are missing. Fail closed rather than pretending reduced review is active.
- The current Pass 3 duplicate classification is conservative and report-first. UI should expose classifications; it should not promote them to workbook actions.

Non-goals:

- No workbook apply planning.
- No workbook writes.
- No generated runtime artifact writes.
- No changes to customer static app runtime.
- No changes to dealer submission.
- No source extraction changes in Pass 0/1.
- No interpretation logic changes in Pass 3 unless a narrow bug is proven by Pass 4 tests.
- No ZR1/ZR1X canonical workbook apply behavior.

## Historical approval prompt

Historical approved Pass 4 scope: a read-only workbook-editor server/UI pass that uses Pass 3 interpretation artifacts as the default reduced Ingest Review view, preserves raw Pass 1 drill-down/debug, exports versioned interpretation review decisions, and still performs no workbook/generated/runtime/dealer writes. The later Pass 5 correction supersedes Pass 4's original dry-run-apply-planning next-step recommendation.

## Expected next pass after Pass 4

Pass 4 proved the reduced review workflow was technically safe, but user review found it still pointed agents in the wrong direction: too broad, too all-model, and too dependent on abstract labels such as `review_needed`, `mechanical_safe`, and `accept_for_later_apply`. Do not proceed from Pass 4 directly to dry-run apply planning.

The next pass is `docs/ingest/pass-5/focused-model-workbook-build-review-spec.md`. Pass 5 must select target models immediately after Pass 0 header/model profiling, use ZR1/ZR1X plus one comparator as the controlled development scope, and replace abstract review decisions with concrete workbook-destination actions.

## Implementation completion — 2026-06-28

Implemented after approval as a read-only workbook-editor server/UI integration over Pass 3 artifacts.

Changed files:

- `scripts/corvette_form_generator/ingest/review_payload.py`
  - Added optional Pass 3 interpretation artifact loading, artifact fingerprints, reduced interpretation list/detail/report accessors, summary mode fields, and versioned interpretation decision validation.
- `scripts/workbook_editor_server.py`
  - Added `--ingest-interpretation-dir` and read-only interpretation endpoints:
    - `/api/ingest/interpretations`
    - `/api/ingest/interpretation/<interpretation_id>`
    - `/api/ingest/interpretation/reports/duplicates`
    - `/api/ingest/interpretation/reports/source-coverage`
    - `/api/ingest/interpretation/blocked`
- `visualizer/workbook-editor/editor.js`
  - Defaults Ingest Review to the reduced interpretation queue when Pass 3 artifacts are configured.
  - Keeps raw candidate families available in the same tab.
  - Exports `version: 2`, `review_mode: interpretation` decisions with interpretation artifact fingerprints and snapshots.
- `visualizer/workbook-editor/editor.css`
  - Added targeted styling for reduced-review metrics and controls.
- `tests/test_ingest_review_payload.py`
  - Added store-level Pass 4 tests for interpretation summary/list/detail/reports, raw drill-down preservation, and interpretation decision validation.
- `tests/test_editor_server_ingest_review.py`
  - Added read-only server endpoint coverage for interpretation mode and report endpoints.
- `docs/ingest/README.md`, `Order-Guide_IngestPrompt.md`, `docs/ingest/pass-2/interactive-review-wizard-spec.md`, and `docs/ingest/pass-3/expert-interpretation-review-reduction-spec.md`
  - Updated ingest workflow references so apply planning remains after reduced UI review.

Implemented command shape:

```sh
.venv/bin/python scripts/workbook_editor_server.py \
  --ingest-evidence-dir /tmp/27vette-pass4-evidence \
  --ingest-candidates-dir /tmp/27vette-pass4-candidates \
  --ingest-interpretation-dir /tmp/27vette-pass4-interpretation
```

Behavior preserved:

- Starting without `--ingest-interpretation-dir` keeps the existing raw Pass 1 candidate review mode.
- Existing raw candidate, unresolved, source, and validation endpoints remain available.
- No workbook operations or apply endpoints were added.

Validation evidence:

```sh
node --check visualizer/workbook-editor/editor.js
# passed

.venv/bin/python -m pytest tests/test_order_guide_ingest_profiler.py tests/test_order_guide_candidate_normalizer.py tests/test_order_guide_ingest_interpreter.py tests/test_ingest_review_payload.py tests/test_editor_server_ingest_review.py -q
# 17 passed

.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
# status valid; issue_count 0

git diff --check -- scripts tests visualizer docs Order-Guide_IngestPrompt.md
git diff --exit-code -- stingray_master.xlsx form-app/data.js
git diff --exit-code -- $(git ls-files form-output)
git status --short -- form-output
# passed / clean
```

Real-artifact API smoke:

```text
Generated /tmp/27vette-pass4-evidence, /tmp/27vette-pass4-candidates, and /tmp/27vette-pass4-interpretation from the real raw export.
Started workbook editor on port 8127 with all three ingest dirs.
/api/ingest/summary returned mode=interpretation and interpretation_enabled=true.
/api/ingest/summary metrics matched Pass 3 smoke counts: raw_candidate_total 14717, interpreted_option_count 1057, visible_review_queue_count 855, hidden_auto_confirmed_count 200, reduction_status material_reduction.
/api/ingest/interpretations?limit=3 returned review-needed reduced rows and detail lookup worked for the first row.
/api/ingest/interpretations?include_auto=true&confidence=auto_confirmed&limit=3 returned auto-confirmed audit rows and detail lookup worked.
/api/ingest/interpretation/reports/duplicates returned 1023 duplicate report rows.
/api/ingest/candidates?family=options&q=ERI&limit=3 still returned raw Pass 1 candidate rows.
Browser smoke at http://127.0.0.1:8127/ loaded Ingest Review in reduced mode by default with the expected metrics, reduced queue controls, and detail panels including Expert summary and Decision after selecting a row.
```

Manual verification still pending:

- Product review of the broad reduced queue found it was not usable enough to proceed to dry-run apply planning. Pass 5 is the corrective follow-up.
- Optional manual export-file inspection from the browser download flow. API validation for the exported payload shape is covered by tests.

Next pass:

- Implement Pass 5 as the corrective focused-model/workbook-build review pass. Do not write a dry-run apply planning spec until the focused ZR1/ZR1X + comparator queue is usable.
