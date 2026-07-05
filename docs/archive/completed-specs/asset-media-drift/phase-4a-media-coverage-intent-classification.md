# Spec: Phase 4A — media coverage intent classification

Status: Implemented 2026-07-01. Approved and completed; see Section 11 Closure.

Parent: `docs/asset-media-drift-remediation-spec-2026-06-30.md` Section 5, Phase 4 / Finding 6. Phases 1, 2, Phase 3, and the post-Phase-3 guardrail hardening have landed on `phase-2-shared-assembly-extraction`. This spec is the recommended first slice of the remaining Phase 4 bucket: reduce missing-image review noise without changing workbook product data, generated runtime artifacts, or customer behavior.

## 0. Re-validation at time of writing

Repo state checked before writing this spec:

- Branch: `phase-2-shared-assembly-extraction`.
- `git status --short --branch`: clean before this spec file was created.

Current source evidence inspected:

- `scripts/corvette_form_generator/asset_map_sync.py`
  - `discover_promoted_option_sources` resolves promoted runtime models from `model_registry_promotion` and option sheets from `model_workbook_sources`.
  - `read_option_sheets` currently treats every active + selectable option row as a desired option media target.
  - `_write_reports` writes both the full `asset_map_sync_report.csv` and `asset_map_missing_images.csv`; the missing report is a filtered view of actions in `MISSING_IMAGE_ACTIONS`.
  - `build_sync_plan` includes desired option targets, model-card targets, and body-style context-choice targets before reconciliation.
- `scripts/corvette_form_generator/contract.py`
  - `load_asset_map` reads active exact-model `asset_map` rows for runtime generation.
  - `option_asset_map`, `bodystyle_asset_map`, and `load_model_asset_map` consume existing generated media fields only; they do not decide which blank workbook rows should exist.
- `scripts/corvette_form_generator/schema_validation.py`
  - `validate_asset_map_uniqueness` now guards duplicate active `asset_map` identities.
  - `validate_default_selection_display_behavior` is a recent precedent for a narrow allowed-value validator on a workbook-authored authoring signal.
- `asset_map-Sync/asset_map_sync.README.md`
  - documents that the supported sync command is dry-run by default, writes review reports and a manifest, and only saves workbook changes with `--apply`.
  - explicitly says `asset_map_missing_images.csv` is review-only and does not imply blank-row seeding or automatic workbook edits.
  - says blank-row seeding, stale-row deactivation, and workbook schema/status-column changes need a separate approved workbook-data spec.
- `docs/asset_media-audit-6-30.md`
  - Finding 6 says sync uses active + selectable option rows as media coverage policy, producing a broad missing-image list that is too noisy to equal “should have an image.”
  - It recommends keeping the broad report but adding a workbook-authored or metadata-derived “image expected” classification before treating a row as a real missing-image gap.
- `form-app/app.js`
  - inspected only for Phase 4 proximity: `autoAddedOptionUsesRequiredSummaryBucket` still hardcodes `sec_incl_001`, but this spec intentionally does not change runtime summary behavior.

Current workbook/read-only probes:

- `asset_map` headers: `model_key`, `target_type`, `target_id`, `image_url`, `image_alt`, `image_fit`, `image_position`, `hover_image_url`, `hover_image_alt`, `hover_image_position`, `active`, `notes`.
- Active `asset_map` rows: 192; inactive rows: 2.
- Active rows by target type: option 183, model 3, context_choice 6.
- Active wildcard/shared rows: 0.
- Active rows missing `image_url`: 0.
- Active duplicate exact keys: 0.
- Repeated active option payload groups across models: 38, confirming wildcard/shared support remains a separate later maintenance-reduction opportunity.
- Promoted option sources: `stingray -> stingray_options`, `grand_sport -> grandSport_options`, `z06 -> z06_options`.
- Active/selectable option rows by promoted model:
  - Stingray: 144.
  - Grand Sport: 152.
  - Z06: 155.

Current report-only sync probe:

Command run read-only with the deterministic fixture list:

```sh
.venv/bin/python scripts/sync_asset_map.py \
  --workbook stingray_master.xlsx \
  --report-dir /tmp/27vette-asset-map-phase4a-spec \
  --media-url-list tests/fixtures/asset-map-sync-media-urls.txt \
  --no-verify-existing
```

Result:

- `apply=false`; `state_written=false`.
- `action_counts`: `flag_missing=458`, `replace_canonical=2`.
- `url_write_count=2`, `insert_count=0`.
- `missing_images_count=458`.
- Missing-image rows by model: Stingray 146, Grand Sport 155, Z06 157.
- Missing-image rows by target type: option 449, model 3, context_choice 6.
- Top noisy sections include LPO exterior, stripes, LPO interior, engine appearance, and wheel sections.

Important interpretation of the probe:

- The fixture contains only three media URLs, so this probe is not a live media completeness audit. It is useful here because it proves the current report path still classifies nearly every desired target without fixture coverage as missing.
- The current broad report is still useful as a raw reconciliation/debug artifact, but it is not the same thing as a product/content decision that an option should have a card image.

## 1. Diagnosis

`asset_map_sync.py` currently uses active + selectable option rows as the media coverage policy. That is too broad for the review workflow.

The workbook/source pipeline distinguishes many kinds of selectable options: paint, wheels, stripes, interiors, dealer/admin rows, LPO accessories, included/standard-adjacent rows, package-related rows, and other configuration choices. Not all of those necessarily need customer-facing card images. When the sync tool labels all uncovered active/selectable options as `flag_missing`, real image gaps can be buried in expected-no-image or low-priority rows.

This is a source-of-truth boundary issue: whether a row is expected to have an image is content/workbook policy, not something the sync script should infer permanently from active/selectable alone.

Risk level: medium for workflow quality; low for current runtime correctness. Current generated runtime output is not known broken. The problem is review signal quality and the risk of future workbook/media maintenance hiding real gaps in a broad missing-image bucket.

Change type: report/tooling first. No workbook write in this Phase 4A implementation.

## 2. Recommended smallest safe pass

Add a report-only media coverage intent classification to the asset-map sync/report path before any workbook schema change, wildcard row migration, or runtime change.

The first implementation should:

1. Preserve the current broad reconciliation report.
2. Preserve the current dry-run/report-first default.
3. Add a separate, explicit coverage-intent classification to report rows and the missing-images review output.
4. Derive that classification from existing workbook metadata where possible, without adding a new workbook column in this pass.
5. Include reduction metrics in the manifest so the team can decide whether a later workbook-authored column is justified.
6. Avoid any `asset_map` blank-row seeding, stale-row deactivation, image URL writes, generated artifact regeneration, or runtime behavior changes.

Recommended implementation approach:

- Add a small pure helper in `scripts/corvette_form_generator/asset_map_sync.py`, near `read_option_sheets`, that classifies each desired target into a coverage intent.
- Start with a conservative metadata-derived classification:
  - `target_type=model`: `expected`.
  - `target_type=context_choice`: `expected`.
  - `target_type=option`: classify from the source option row plus existing section metadata.
- For option rows, use existing fields already available to `read_option_sheets` or cheaply joinable from workbook metadata:
  - `section_id` from the option sheet.
  - section presentation / section master metadata if needed.
  - option row `display_behavior`, `status`, `selectable`, and `active` only as supporting context, not as the sole policy.
- The initial classifier must be intentionally conservative. If a row cannot be confidently classified as expected or not expected, mark it `review` rather than suppressing it.

Recommended vocabulary:

- `expected`: likely should have customer-facing media; keep in the actionable missing-image queue when uncovered.
- `review`: unclear; retain in a secondary review queue and report metrics.
- `not_expected`: likely not expected to have a card image; keep in the broad report but exclude from the actionable missing-image count.

CSV semantics after classification: `asset_map_missing_images.csv` becomes the actionable review queue and contains only `expected` and `review` rows; `not_expected` missing rows remain visible solely in the broad `asset_map_sync_report.csv` (with `coverage_intent`/`coverage_intent_reason` populated), so the noise reduction is realized in the review CSV itself, not just in a manifest metric.

Evidence requirements for each classification (strengtheners, all additive):

- Emit a `coverage_intent_reason` column alongside `coverage_intent` in both report CSVs: a short stable token naming the metadata rule that fired (for example `section:lpo_interior`, `target_type:model`, `unmatched-section`). This makes every suppression auditable and gives Phase 4B concrete workbook-destination lanes instead of abstract states.
- Include a per-section breakdown in the manifest (`section_id` x `coverage_intent` counts per model) so the team can judge which sections drive the reduction and which need a product decision.
- Record the classifier rule-set identity in the manifest (a version string or ordered rule list) so fixture-run counts stay comparable across future runs.

Reduction success metrics and stop condition (Pass 3 precedent: prove reduction before building on it):

- Success: on the deterministic fixture run, the actionable `expected` missing count is materially lower than the broad missing count — target at least a 30% reduction — and the `review` bucket stays below 40% of broad missing rows. A classifier that dumps most rows into `review` has not reduced anything.
- Stop condition: if either threshold fails, do not proceed to a Phase 4B workbook-column spec on this evidence. Close Phase 4A honestly with the per-section breakdown and recommend either a refined metadata rule or a direct workbook-authored intent surface.

Do not introduce a permanent workbook taxonomy or a new workbook column in Phase 4A. If the report-first slice proves meaningful reduction but exposes ambiguous policy decisions, write a Phase 4B workbook-data spec for an explicit workbook-authored coverage-intent surface.

## 3. Exact files expected to change for implementation

1. `scripts/corvette_form_generator/asset_map_sync.py`
   - Add a pure helper for coverage-intent classification.
   - Thread coverage intent through `read_option_sheets`, `read_model_targets`, `read_bodystyle_targets`, `reconcile`, and `add_report` row construction.
   - Add `coverage_intent` and `coverage_intent_reason` to `asset_map_sync_report.csv` and `asset_map_missing_images.csv` as additive columns.
   - Split missing-image metrics by coverage intent in the manifest payload, including the per-section breakdown and classifier rule-set identity from Section 2.
   - Preserve the raw broad report and all current action values. Do not rename existing CSV columns.

2. `tests/test_asset_map_sync.py`
   - Add focused tests for the pure classifier, including determinism (same input rows in shuffled order produce identical intents) and a reason token for every classified row.
   - Add a report-writing test proving:
     - `coverage_intent` and `coverage_intent_reason` are emitted in both report CSVs.
     - `asset_map_missing_images.csv` contains only `expected` and `review` rows; excluded `not_expected` missing rows remain present in the broad report CSV.
     - actionable missing count excludes `not_expected` rows.
     - `review` rows are not silently dropped.
   - Add a manifest test proving counts are broken down by coverage intent and per section, and that the rule-set identity is present.

3. `asset_map-Sync/asset_map_sync.README.md`
   - Document the new report columns (`coverage_intent`, `coverage_intent_reason`) and manifest metrics.
   - Keep the warning that missing-image reports are review-only and do not imply automatic workbook edits.
   - Explicitly state that Phase 4A is report-only and does not add or apply workbook rows.

4. `docs/asset-media-drift/phase-4a-media-coverage-intent-classification.md`
   - Close per AGENTS.md §11 on completion (status, changed surfaces, validation results, residual risks, next pass).

No other files should change in this implementation pass unless evidence during implementation shows a directly required companion update. In particular, do not edit `stingray_master.xlsx`, `form-output/`, `form-app/data.js`, `form-app/app.js`, `form-app/styles.css`, `scripts/corvette_form_generator/contract.py`, or registry/generator code for this Phase 4A slice.

## 4. Source-of-truth decision

Phase 4A is a report/tooling classification pass, not the final source-of-truth migration.

- Workbook/source metadata remains authoritative for option rows, section membership, status/selectability, and presentation metadata.
- The sync tool may derive a provisional coverage-intent classification from existing workbook metadata for review purposes.
- The sync tool must not become a hidden permanent product-rule database. Any classification that needs human/product judgment or durable authoring must be promoted in a later workbook-data spec. (General boundary doctrine: AGENTS.md §3.)

## 5. Companion-file impact check

- `stingray_master.xlsx`: not applicable for Phase 4A implementation. Read-only inspection only; no workbook writes.
- `asset_map`: inspected as the owning media metadata sheet; no row edits in Phase 4A.
- `section_master` / `section_presentation`: inspected as existing metadata sources; no workbook edits in Phase 4A.
- `scripts/corvette_form_generator/asset_map_sync.py`: updated; this is the implementation owner.
- `scripts/corvette_form_generator/contract.py`: inspected-no-change. Runtime media loading should stay exactly as-is.
- `scripts/corvette_form_generator/schema_validation.py`: inspected-no-change unless implementation adds an allowed-value validator for a new workbook-authored column, which this spec explicitly excludes.
- `tests/test_asset_map_sync.py`: updated with classifier/report/manifest tests.
- `asset_map-Sync/asset_map_sync.README.md`: updated to document the new report fields and review-only boundary.
- `form-output/*`: not applicable; no generation should be run as a required part of this report-only pass.
- `form-app/data.js`: not applicable; no registry publication.
- `form-app/app.js`: inspected-no-change; runtime summary cleanup is a later separate Phase 4 slice.
- Dealer submission behavior: not applicable; no runtime/dealer code touched.
- Parent route map `docs/asset-media-drift-remediation-spec-2026-06-30.md`: optional inspected-no-change for implementation. Do not update it unless the implementation closes Phase 4A and needs route-map status refresh.

## 6. Constraints

Standing constraints from AGENTS.md apply (§3 generated artifacts are never source; §4 no new dependencies or unrelated refactors; §6 dealer boundary untouched). Spec-specific constraints:

- No workbook writes.
- No generated artifact writes required.
- No runtime JavaScript/CSS/HTML changes.
- No live WordPress/media-network dependency in required validation; use the checked-in fixture list for deterministic gates.
- Preserve report CSV columns; new columns must be additive only.
- Preserve the broad reconciliation report; do not hide data problems by deleting rows from all outputs.
- Keep the classifier conservative. Ambiguous rows should become `review`, not `not_expected`.
- Classification must be deterministic and pure: same workbook metadata in, same intents out, with stable row ordering so report diffs stay reviewable across runs.
- Do not add wildcard/shared `asset_map` semantics, migrate repeated identical media rows, or change `load_asset_map` exact-model semantics in this pass.

## 7. Risks and non-goals

Risks:

- A too-aggressive classifier could suppress real missing media gaps. Mitigation: default unclear cases to `review`, keep the broad report, and report counts for `expected`, `review`, and `not_expected` separately.
- Existing section taxonomy may not be sufficient to encode final media intent. Mitigation: Phase 4A is report-first; if reduction is not strong or classifications are questionable, stop and spec a workbook-authored intent surface rather than burying more logic in Python.
- Fixture-based sync counts are not live media completeness counts. Mitigation: use fixture output only for deterministic regression; treat live media pulls as optional smoke, not required proof.

Non-goals:

- No workbook schema/column addition.
- No `asset_map` row migration.
- No wildcard/shared `asset_map` support.
- No runtime media rendering change.
- No runtime summary `sec_incl_001` cleanup.
- No stale Grand Sport note cleanup unless separately approved as a small docs/config cleanup.
- No attempt to resolve the unrelated Z06 replace-rule schema-standardization red gate.

## 8. Validation plan

Run in this order and report exact output:

1. `.venv/bin/python -m pytest tests/test_asset_map_sync.py -q`
   - Must pass with the new classifier/report/manifest coverage.

2. `.venv/bin/python scripts/sync_asset_map.py --workbook stingray_master.xlsx --report-dir /tmp/27vette-asset-map-phase4a --media-url-list tests/fixtures/asset-map-sync-media-urls.txt --no-verify-existing`
   - Must remain dry-run only: `apply=false`, `state_written=false`.
   - Must produce `asset_map_sync_report.csv`, `asset_map_missing_images.csv`, `asset_map_unmatched_media.csv`, and `asset_map_sync_manifest.json`.
   - Must show additive report schema with `coverage_intent` and `coverage_intent_reason` present.
   - Must show manifest counts by coverage intent, the per-section breakdown, and the rule-set identity.
   - Must meet the Section 2 reduction thresholds (>=30% actionable reduction; `review` < 40% of broad missing). If not met, stop and report per the Section 2 stop condition instead of proceeding to any next pass.
   - Run the command twice and diff the report CSVs to prove deterministic output (timestamp/manifest run fields excepted).

3. `.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx`
   - Must pass or report known unrelated failures separately. Phase 4A should not introduce workbook schema errors.

4. `git diff --check`
   - Must pass.

5. `git diff -- form-output form-app/data.js stingray_master.xlsx`
   - Must be empty. If any artifact/workbook churn appears from incidental commands, restore it before handoff.

Gates intentionally not required:

- Model regeneration via `scripts/generate_form.py`: not required because Phase 4A should not change generator/runtime output.
- `scripts/generate_registry.py`: not required because no runtime data publication changes.
- Browser smoke: not required because runtime code and generated data are untouched.
- Live WordPress media fetch: optional smoke only; deterministic fixture validation is the required gate.

## 9. Handoff requirements for implementation

Follow the standard handoff format in AGENTS.md §11. Spec-specific additions to report:

- New report CSV columns and manifest fields, with fixture-run counts: broad missing, actionable `expected` missing, `review`, `not_expected`, URL writes, inserts, unmatched, unparseable.
- Whether the Section 2 reduction thresholds were met, with the per-section breakdown.
- Any classifications that look product-questionable and should become a Phase 4B workbook-authored policy decision.
- Recommended Phase 4B direction based on the reduction evidence: workbook-authored media intent, wildcard/shared `asset_map`, or stale-note/runtime-summary cleanup.

## 10. Approval prompt

Approved by user 2026-07-01; implemented same day.

## 11. Closure (2026-07-01)

Changed surfaces:

- `scripts/corvette_form_generator/asset_map_sync.py`: added `SectionCoverageMetadata` + `read_section_coverage_metadata()` (tolerates missing sheets), pure `build_coverage_classifier()` (ruleset `phase4a-v1`, 10 ordered rules), optional `classify_coverage` param on `reconcile()` (default None = empty columns, preserving old callers), additive `coverage_intent`/`coverage_intent_reason` columns in both CSVs, missing-images CSV filtered to the actionable queue (`expected`+`review`; `not_expected` stays in the broad report), `build_coverage_summary()` manifest block (ruleset version/rules, intent counts, actionable count, per-model/per-section breakdown) plus `broad_missing_images_count`.
- `tests/test_asset_map_sync.py`: +4 tests (rule/reason coverage for all 11 classifier outcomes, shuffled-input determinism, actionable-queue vs broad-report composition, manifest breakdown/ruleset). 25 passed total.
- `asset_map-Sync/asset_map_sync.README.md`: documented new columns, queue semantics, manifest coverage block, and the report-only boundary.

Not changed: `stingray_master.xlsx`, `form-output/`, `form-app/*` (git diff empty), `contract.py`, `schema_validation.py`, registry/generator code, dealer submission. No workbook writes; dry-run default preserved (`apply=false`, `state_written=false`).

Fixture-run results (deterministic fixture, real workbook, read-only):

- Broad missing 458 → actionable missing-images CSV 401 rows; intents: expected 237, review 164, not_expected 57.
- Reduction thresholds: 48.3% actionable reduction vs broad expected-only baseline (target ≥30%) — met; review bucket 35.8% of broad (limit <40%) — met.
- `expected` drivers: existing-asset-row 181, sibling-model-asset-row 22, section-required 20, target_type 9, replaceable-default 5.
- `not_expected` drivers: section-no-media-precedent 52 (sec_whee_001 22, sec_cust_001 11, sec_perf_ground_001 6, sec_gsce_001 5, sec_perf_z52_001 3, sec_z06_pkg_001 3, sec_jake_001 2), display-only/standard-equipment 5.
- Top `review` load: sec_stri_001 (52 across models), sec_lpoe_001 (45), sec_engi_001, sec_lpoi_001.
- Determinism: two runs, report CSVs byte-identical.

Validation: `pytest tests/test_asset_map_sync.py -q` 25 passed; fixture sync run dry-run-only with all four artifacts and new columns/manifest fields present; run-twice diff clean; `validate_workbook_schema.py` exit 0, issues []; `git diff --check` clean; `git diff -- form-output form-app/data.js stingray_master.xlsx` empty. Gates intentionally not run (per Section 8): model regeneration, registry publication, browser smoke, live WordPress fetch — no generator/runtime/publication surface changed.

Residual risks / product-questionable classifications for Phase 4B:

- `section-no-media-precedent` marks 52 rows not_expected purely because no option in those sections has authored media yet — circular if a section (e.g. wheel accessories, ground effects) SHOULD get images but never has. These seven sections need a product decision.
- Fixture counts are not live media completeness; live pull remains optional smoke.

Recommended Phase 4B: workbook-authored media-intent surface, seeded from this run's per-section breakdown — the 7 no-precedent sections plus the stripes/LPO-exterior review load are exactly the concrete decision lanes it should encode. Wildcard/shared asset_map and runtime-summary cleanup remain separate later slices.
