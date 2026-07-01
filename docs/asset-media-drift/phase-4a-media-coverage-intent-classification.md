# Spec: Phase 4A — media coverage intent classification

Status: Spec only. Do not implement until approved.

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

Do not introduce a permanent workbook taxonomy or a new workbook column in Phase 4A. If the report-first slice proves meaningful reduction but exposes ambiguous policy decisions, write a Phase 4B workbook-data spec for an explicit workbook-authored coverage-intent surface.

## 3. Exact files expected to change for implementation

1. `scripts/corvette_form_generator/asset_map_sync.py`
   - Add a pure helper for coverage-intent classification.
   - Thread coverage intent through `read_option_sheets`, `read_model_targets`, `read_bodystyle_targets`, `reconcile`, and `add_report` row construction.
   - Add `coverage_intent` to `asset_map_sync_report.csv` and `asset_map_missing_images.csv` as an additive column.
   - Split missing-image metrics by coverage intent in the manifest payload.
   - Preserve the raw broad report and all current action values. Do not rename existing CSV columns.

2. `tests/test_asset_map_sync.py`
   - Add focused tests for the pure classifier.
   - Add a report-writing test proving:
     - `coverage_intent` is emitted in both report CSVs.
     - broad missing rows are still represented somewhere.
     - actionable missing count excludes `not_expected` rows.
     - `review` rows are not silently dropped.
   - Add a manifest test proving counts are broken down by coverage intent.

3. `asset_map-Sync/asset_map_sync.README.md`
   - Document the new report column and manifest metrics.
   - Keep the warning that missing-image reports are review-only and do not imply automatic workbook edits.
   - Explicitly state that Phase 4A is report-only and does not add or apply workbook rows.

4. `docs/asset-media-drift/phase-4a-media-coverage-intent-classification.md`
   - Update this spec from `Spec only` to `Implemented` on completion, with changed files, command results, residual risks, and recommended next pass.

No other files should change in this implementation pass unless evidence during implementation shows a directly required companion update. In particular, do not edit `stingray_master.xlsx`, `form-output/`, `form-app/data.js`, `form-app/app.js`, `form-app/styles.css`, `scripts/corvette_form_generator/contract.py`, or registry/generator code for this Phase 4A slice.

## 4. Source-of-truth decision

Phase 4A is a report/tooling classification pass, not the final source-of-truth migration.

- Workbook/source metadata remains authoritative for option rows, section membership, status/selectability, and presentation metadata.
- The sync tool may derive a provisional coverage-intent classification from existing workbook metadata for review purposes.
- The sync tool must not become a hidden permanent product-rule database. Any classification that needs human/product judgment or durable authoring must be promoted in a later workbook-data spec.
- Generated artifacts and runtime data remain outputs and are not hand-edited.

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

- No workbook writes.
- No generated artifact writes required.
- No runtime JavaScript/CSS/HTML changes.
- No dealer submission endpoint, payload, Turnstile/security, or submission UX changes.
- No new dependencies.
- No live WordPress/media-network dependency in required validation; use the checked-in fixture list for deterministic gates.
- Preserve report CSV columns; new columns must be additive only.
- Preserve the broad reconciliation report; do not hide data problems by deleting rows from all outputs.
- Keep the classifier conservative. Ambiguous rows should become `review`, not `not_expected`.
- Do not add wildcard/shared `asset_map` semantics in this pass.
- Do not migrate repeated identical media rows in this pass.
- Do not change `load_asset_map` exact-model semantics in this pass.

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
   - Must show additive report schema with `coverage_intent` present.
   - Must show manifest counts by coverage intent.
   - Must show actionable missing count lower than or equal to broad missing count; if equal, stop and explain why the classifier failed to reduce noise before proceeding to any next pass.

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

On completion, report:

- Changed files and exact behavior impact.
- Confirmation that `stingray_master.xlsx`, `form-output/`, `form-app/data.js`, runtime JS/CSS, and dealer-submission code were untouched.
- New report CSV columns and manifest fields.
- Fixture-run counts: broad missing count, actionable expected missing count, review count, not-expected count, URL writes, inserts, unmatched, and unparseable counts.
- Validation command results from Section 8.
- Any classifications that look product-questionable and should become a Phase 4B workbook-authored policy decision.
- Whether Phase 4B should be workbook-authored media intent, wildcard/shared `asset_map`, or stale-note/runtime-summary cleanup based on the reduction evidence.

## 10. Approval prompt

Approve Phase 4A as a report-only implementation pass:

- Add media coverage intent classification to `asset_map_sync` reports/manifest.
- Add focused tests and README documentation.
- Do not write the workbook, regenerate artifacts, change runtime behavior, or add wildcard/shared `asset_map` semantics.
