# Spec: Phase 4B — universal-expected coverage policy and per-section coverage report

Status: Implemented 2026-07-01. Approved and completed; see Section 11 Closure.

Parent: `docs/asset-media-drift-remediation-spec-2026-06-30.md` Section 5, Phase 4 / Finding 6. Predecessor: `phase-4a-media-coverage-intent-classification.md` (Implemented 2026-07-01).

This spec replaces an earlier Phase 4B draft that proposed a workbook-authored `section_master.media_coverage_intent` column with a per-section product-decision seed table. That direction was rejected by product policy review on 2026-07-01 and is recorded here as a non-goal.

Recommended reasoning level for implementation: medium (classifier simplification + report/manifest additions inside one module; no workbook write).

## 0. Product policy (owning decision for this pass)

Stated by product owner 2026-07-01:

- Every active + selectable option card should eventually carry a visual element. "Expected" is universal policy, not a per-section decision.
- `not_expected` is valid only as a structural derivation for rows that never render as option cards (display-only / standard-equipment presentation). An authorable suppression key is a bug vector: if images are later sourced for a section still keyed `not_expected`, the report would hide exactly the gaps being filled.
- Missing-image noise is managed by per-section grouping and coverage statistics (form-consistency view), not by row suppression.

Phase sequencing agreed: 4B = this report-policy pass; 4C = stale-note/runtime-summary cleanup (includes the `autoAddedOptionUsesRequiredSummaryBucket` hardcoded `sec_incl_001` noted in 4A §0); 4D = wildcard/shared `asset_map` semantics (38 repeated identical payload groups measured in 4A §0). 4C and 4D get their own specs.

## 1. Diagnosis

Phase 4A's ruleset (`phase4a-v1`) encodes intent distinctions the universal-expected policy makes wrong or meaningless:

- `section-no-media-precedent -> not_expected` (52 rows) is circular and now contradicts policy: those are real future gaps, not suppressible rows.
- `review` as "unclear whether an image is needed" (164 rows) is void — policy answers that question universally.
- `sibling-model-asset-row`, `section-required`, `section-replaceable-default` distinctions only mattered for guessing intent; under universal-expected they are redundant paths to the same answer.

What survives from 4A: the structural `not_expected` rules (display-only sections, standard-equipment buckets — 5 rows on current data), the additive CSV columns, the reason-token audit trail, the manifest breakdown machinery, and determinism guarantees.

Risk: low. Report/tooling only; no workbook, generated-artifact, or runtime changes. Change class: generator/tooling + tests + docs.

## 2. Recommended smallest safe pass

1. Simplify the classifier to ruleset `phase4b-v1`, binary vocabulary:
   - `target_type` model/context_choice → `expected` (`target_type:<type>`).
   - Section `selection_mode=display_only` → `not_expected` (`section-display-only:<id>`).
   - Active `standard_equipment_bucket` for (model, section) → `not_expected` (`standard-equipment-bucket:<id>`).
   - Everything else (all active+selectable option targets) → `expected`. Reason `universal-expected`, except unmatched/blank section keeps the distinct reason `unmatched-section` (still `expected`) so section data problems stay visible.
   - `review` is removed from the vocabulary. `COVERAGE_INTENTS` becomes binary; `ACTIONABLE_COVERAGE_INTENTS` semantics unchanged (actionable = everything not structurally `not_expected`).
2. Per-section coverage statistics in the manifest (the form-consistency view — this is the new value): for each promoted model × section over desired option targets: `total_targets`, `covered` (existing asset row with a URL), `missing`, `coverage_pct`, plus a per-model rollup. Computed over ALL desired option targets, not just missing rows, so it converges to 100% as images land.
3. Group the review queue for humans: sort `asset_map_missing_images.csv` rows by model_key → section_id → target_id (stable, deterministic). Column schema unchanged.
4. Preserve everything else from 4A: broad report retains all rows with intent columns; missing-images CSV = actionable queue; ruleset version + rules recorded in manifest; dry-run default.

Expected fixture-run shape (from 4A closure numbers, to verify at implementation): broad missing 458 → actionable ~453, structural `not_expected` ~5. The actionable count RISES vs 4A's 401 — that is the policy correction working, not a regression. The noise reduction now lives in section grouping and coverage percentages instead of row exclusion.

## 3. Exact files expected to change

1. `scripts/corvette_form_generator/asset_map_sync.py`
   - `COVERAGE_RULESET_VERSION = "phase4b-v1"`; rewrite `COVERAGE_RULESET` to the §2.1 rules; remove `COVERAGE_REVIEW` from the vocabulary.
   - Simplify `build_coverage_classifier` (drop sibling/required/replaceable-default/media-precedent rules; keep purity and determinism). `SectionCoverageMetadata` keeps `selection_mode` and `standard_equipment_buckets`; `is_required`/`standard_behavior` fields may be dropped if nothing else consumes them.
   - Add `build_section_coverage_stats(desired, existing_rows)` pure helper → per-model/per-section stats per §2.2; wire into the manifest `coverage` block alongside the existing intent counts.
   - Sort missing-images rows per §2.3 before writing.
2. `tests/test_asset_map_sync.py`
   - Update `make_coverage_workbook` expectations: former review/no-precedent cases now assert `expected` with correct reasons; structural cases keep `not_expected`.
   - Drop/replace tests asserting `review` semantics (queue-composition test becomes: queue = all missing minus structural `not_expected`).
   - New: section-coverage-stats test (counts and pct correct against fixture workbook; covers a fully-covered section, a partial one, and an uncovered one) and queue-ordering test.
   - Determinism test retained as-is.
3. `asset_map-Sync/asset_map_sync.README.md` — update: binary vocabulary, universal-expected policy sentence, coverage-stats manifest block, sorted queue.
4. This spec — close per AGENTS.md §11.

Inspected-no-change expectation: `stingray_master.xlsx` (read-only), `schema_validation.py`, `contract.py`, `production.py`, runtime JS/CSS, `form-output/`, `form-app/data.js`, all `*.test.mjs`.

## 4. Source-of-truth decision

Coverage policy is universal product policy encoded as the classifier default — nothing to author. The only workbook-derived classifications are structural presentation facts already owned by `section_master.selection_mode` and `section_presentation.standard_equipment_bucket`, which self-correct when those sheets change. No new workbook surface; no hidden product-rule database (the ruleset is 4 lines and recorded in every manifest).

## 5. Companion-file impact check

- `scripts/corvette_form_generator/asset_map_sync.py`, `tests/test_asset_map_sync.py`, `asset_map-Sync/asset_map_sync.README.md`: updated.
- `stingray_master.xlsx`, `section_master`, `section_presentation`: read-only inputs; no writes.
- `schema_validation.py`: inspected-no-change (no new workbook column → no validator).
- `form-output/*`, `form-app/data.js`, runtime JS, dealer submission: not applicable.
- Parent route map: update Phase 4 status on closure (4B done; 4C/4D queued).

## 6. Constraints

Standing constraints from AGENTS.md apply (§3, §4, §6). Spec-specific:

- No workbook writes; no schema changes; no new CSV columns (values/ordering only).
- Classifier stays pure and deterministic; two identical runs must produce byte-identical CSVs.
- Structural `not_expected` must derive exclusively from live workbook metadata — never from media inventory or asset_map coverage state (no circularity by construction).
- Coverage stats computed over all desired option targets, not the missing subset.
- No wildcard/shared `asset_map` or runtime-summary changes (4C/4D scope).

## 7. Risks and non-goals

Risks:

- Actionable queue grows to ~453 rows; if section grouping + coverage stats prove insufficient for triage, the correct escalation is a prioritization signal (later authoring pass that can only mark priority, never suppression) — flag in closure rather than expanding this pass.
- Tests asserting `review` behavior are load-bearing in the queue-composition test; rewriting them wrong could silently weaken the not_expected-exclusion guarantee. Mitigation: keep an explicit assertion that structural not_expected rows are present in the broad report and absent from the queue.

Non-goals: authored intent columns of any kind (rejected by policy); per-option overrides; workbook writes; stale-note/runtime-summary cleanup (4C); wildcard/shared `asset_map` (4D); live media pull as required validation.

## 8. Validation plan

Run in order, report exact output:

1. `.venv/bin/python -m pytest tests/test_asset_map_sync.py -q` — pass with updated coverage.
2. Fixture sync run (same command as 4A §8.2, fresh report dir) — dry-run only (`apply=false`, `state_written=false`); manifest shows `ruleset_version: phase4b-v1`, binary intent counts, and the per-model/per-section coverage stats; missing-images CSV sorted per §2.3; report before/after counts vs 4A closure (458 broad / 401 actionable baseline).
3. Run twice, diff report CSVs — byte-identical.
4. `.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx` — pass (no workbook change; sanity only).
5. `git diff --check`; `git diff -- form-output form-app/data.js stingray_master.xlsx` — empty.

Gates intentionally not required: model regeneration, registry publication, browser smoke, node test matrix, live WordPress fetch — no generator/runtime/publication/workbook surface changes.

## 9. Handoff requirements

Follow AGENTS.md §11. Spec-specific additions:

- Fixture-run intent counts before (4A closure) vs after, confirming the actionable rise is exactly the former review + no-precedent rows.
- Per-model coverage percentages from the stats block (the new consistency baseline to track).
- Confirmation CSV schemas are unchanged (values/order only) and structural not_expected rows remain in the broad report.
- Recommendation with evidence: whether 4C (stale-note/runtime-summary cleanup) or 4D (wildcard/shared asset_map, 38 repeated payload groups) should go next.

## 10. Approval prompt

Approved by user 2026-07-01; implemented same day.

## 11. Closure (2026-07-01)

Changed surfaces:

- `scripts/corvette_form_generator/asset_map_sync.py`: ruleset `phase4b-v1` (4 rules); `COVERAGE_REVIEW` removed, binary `COVERAGE_INTENTS`; `build_coverage_classifier` simplified — coverage-state/sibling/required/replaceable-default/media-precedent rules deleted, `existing_rows` explicitly unused by policy (`del` with no-circularity comment); unmatched-section now classifies `expected` with its distinct reason; new pure `build_section_coverage_stats()` (per model × section total/covered/missing/coverage_pct over ALL desired option targets) carried on `SyncPlan.section_coverage` and emitted under manifest `coverage.section_coverage`; missing-images queue sorted model → section → target.
- `tests/test_asset_map_sync.py`: classifier cases rewritten to universal-expected; new no-circularity test (classifier output identical with and without existing asset rows); queue test asserts expected-only composition, structural-reason prefixes on excluded rows, and sort order; new section-coverage-stats test (partial/uncovered sections, rollup consistency, pure-helper == manifest). 27 passed.
- `asset_map-Sync/asset_map_sync.README.md`: universal-expected policy, binary vocabulary, sorted queue, `section_coverage` manifest block.

Not changed: `stingray_master.xlsx` (read-only), `schema_validation.py`, `contract.py`, `production.py`, runtime JS/CSS, `form-output/`, `form-app/data.js` (git diff empty), dealer submission. No workbook writes; CSV schemas unchanged (values/ordering only); dry-run default preserved (`apply=false`, `state_written=false`).

Fixture-run results (deterministic fixture, real workbook, read-only):

- Broad missing 458 → actionable 453 (expected 453, structural not_expected 5) — matches the §2 prediction exactly; the +52 vs 4A's 401 is precisely the former review + no-precedent rows returning under policy.
- Queue verified expected-only and sorted; two runs byte-identical.
- Coverage baseline (the new form-consistency numbers to track): stingray 51/144 = 35.4%, grand_sport 61/152 = 40.1%, z06 71/155 = 45.8%.
- Zero-coverage sections surfaced by the stats: sec_cust_001 (all models), sec_badg_001 (GS, Z06), sec_gsce_001 (GS), sec_exte_001 + sec_hash_001 (stingray), sec_incl_001 (Z06 — display-only, structural).

Validation: `pytest tests/test_asset_map_sync.py -q` 27 passed; fixture run dry-run only, manifest `ruleset_version: phase4b-v1`, section_coverage present; run-twice CSV diff clean; `validate_workbook_schema.py` exit 0; `git diff --check` clean; `git diff -- form-output form-app/data.js stingray_master.xlsx` empty. Gates intentionally not run (§8): model regeneration, registry, browser smoke, node matrix, live media fetch — no generator/runtime/workbook surface changed.

Residual risks: 453-row queue relies on section grouping + coverage stats for triage; if that proves insufficient in practice, escalate to a priority-only authoring signal (never suppression) as a new spec.

Recommended next pass: 4C (stale-note/runtime-summary cleanup, including the hardcoded `sec_incl_001` in `form-app/app.js` `autoAddedOptionUsesRequiredSummaryBucket`) before 4D (wildcard/shared `asset_map`) — 4C is smaller, touches runtime boundaries that benefit from being cleaned before asset_map semantics change, and the 38 repeated payload groups measured in 4A are stable and can wait.
