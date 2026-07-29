# Live Runtime Merge Readiness Spec: Intentional Image Artifact Sync + Red-Gate Cleanup

> **Execution status (2026-07-29): SUPERSEDED.** This plan records an older generator/artifact topology. Do not run its commands or treat its compatibility paths, `production.py` route, artifact types, or retired test names as current guidance. Current commands and authority are owned by `README.md` and Pass 4 Stage A of `docs/superpowers/specs/2026-07-23-validation-single-lane-active-surface-cleanup.md`. Historical evidence below is preserved verbatim pending Stage C archival.

Recommended reasoning level for Sean/Codex: high. This is a narrow ASAP merge-readiness pass. The new option-card images are intentional and should ship. Preserve runtime logic/selection/dealer behavior while allowing the intended workbook-owned image metadata to flow into generated runtime artifacts.

## Diagnosis

Current branch: `generator-simplification-pass1` at `e03230c`, clean at spec-revision time. `main` is an ancestor, so these are current-branch internal readiness issues, not main-gate/main-data mismatches.

The branch has already moved toward the intended primary runtime structure:

```text
stingray_master.xlsx source rows
  -> scripts/generate_form.py --model <model>
  -> promoted model artifacts
  -> scripts/generate_registry.py
  -> form-app/data.js
  -> browser runtime
```

The remaining issues to clear before live merge are:

1. generated runtime artifacts need to be synced to current workbook-owned `asset_map` image metadata;
2. one stale current-branch test still asserts pre-decision Stingray seat display orders;
3. validation needs a repeatable order because some tests regenerate artifacts as side effects.

### Issue A: runtime artifacts are stale relative to intentional workbook-owned image metadata

Evidence from current branch only:

```sh
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_registry.py
```

That sequence produced customer-facing image metadata diffs in:

- `form-output/stingray-form-data.json`
- `form-output/stingray-form-data.csv`
- `form-output/inspection/grand-sport-runtime-contract.json`
- `form-output/inspection/z06-runtime-contract.json`
- `form-app/data.js`
- `stingray_master.xlsx` generated workbook churn from Stingray generation

Observed image-metadata drift by generated runtime artifact:

- Stingray: 42 choice image diffs, RPOs `719`, `3N9`, `379`, `3A9`, `3F9`, `3M9`, `QE6`.
- Grand Sport: 24 wheel image URL diffs, RPOs `SWM`, `SWN`, `SWO`, `SWP`.
- Z06: 78 choice image diffs, RPOs `719`, `3N9`, `379`, `3A9`, `3F9`, `3M9`, `J6A`, `J6B`, `J6D`, `J6E`, `J6F`, `J6L`, `J6N`.

Sample workbook source evidence:

- `asset_map.opt_swm_001` for `grand_sport` is active and currently points to `.../27vette/swm.png`; checked Grand Sport runtime artifact currently uses older `.../27vette/imgi_79_swm.png`.
- `asset_map.opt_qe6_001` for `stingray` is active and points to `.../27vette/qe6.png`; checked Stingray runtime artifact currently uses older `.../27vette/c-qe6_v1.png`.
- `asset_map.opt_719_001` rows for active models are active and point to `.../27vette/imgi_47_719.png`; checked artifacts do not consistently emit those option-card image fields.
- `asset_map.opt_j6a_001` for `z06` is active and points to `.../27vette/h-j6a-23x13-cp.png`; checked Z06 runtime artifact currently lacks that generated option-card image metadata.

Root cause: current branch generators now read active workbook `asset_map` option-target rows, but checked generated artifacts have not been refreshed. The new images are intentional additions and should be allowed into live runtime. This is an artifact-sync problem, not a reason to suppress image metadata in code or deactivate workbook rows.

Cleanest resolution: keep `asset_map` as the source of truth, regenerate active model artifacts plus registry, review the generated diff as an intentional image-metadata rollout plus timestamps/generated workbook churn, and commit the generated runtime artifacts needed for live runtime.

### Issue B: one current-branch test asserts stale Stingray seat display order

Failing test:

- `tests/nonruntime-option-source-purge.test.mjs:186`

It expects Stingray active `sec_seat_002` order:

```text
AQ9 10
AH2 25
AE4 40
AUP 80
```

But the current workbook/product-decision guard already treats this as the canonical active promoted order in `tests/workbook-visual-copy-standardization.test.mjs:158`:

```text
AQ9 10
AH2 20
AE4 30
AUP 40
```

Root cause: stale duplicate test expectation in a source-row purge test. The product/display-order behavior is already owned by `tests/workbook-visual-copy-standardization.test.mjs` and workbook source rows.

Cleanest resolution: remove or narrow the duplicate seat-order assertion from `tests/nonruntime-option-source-purge.test.mjs`. That test should continue guarding retired source rows and deferred `sec_tech_001` rows, but it should not duplicate the visual-copy/product-decision seat-order contract.

### Issue C: some current-branch tests write generated artifacts and can make later freshness checks red

Observed after running generator-writing Node tests:

- `form-app/data.js` dirtied
- Grand Sport inspection/runtime artifacts dirtied
- Z06 inspection/runtime artifacts dirtied

Then schema freshness can report `app_registry_stale` if run after those side-effecting tests. A standalone clean run of `node --test tests/workbook-schema-standardization.test.mjs` passed after restoring artifacts.

Root cause: gate-order and test-side-effect issue. Not a customer-facing runtime bug, but it can make the final merge gate look red or leave generated churn behind.

Cleanest ASAP resolution: run freshness/parity gates in a deliberate order and finish with reviewed generated artifacts in the intended synced state. Do not refactor side-effecting tests into temp-output tests in this pass unless they still block repeatability after artifact sync.

## Risk Level

Medium.

The intended customer-facing change is option-card imagery sourced from workbook `asset_map`. The risk is accidentally accepting unrelated generated/runtime drift under cover of the image sync.

Change type: generated artifact sync + test cleanup + validation workflow discipline. No runtime JS behavior change, no styling change, no dealer submission behavior change.

## Exact Scope

### Workbook source

Default: do not change workbook source rows for this pass.

`asset_map` rows are treated as intentional source-of-truth image metadata. Only inspect them and verify they explain the generated image diffs.

Workbook edits are allowed only if validation proves a specific `asset_map` row is wrong or malformed, for example:

- missing active row for an intended checked/generated image;
- typo/broken URL in an active row;
- wrong `model_key`, `target_type`, or `target_id` that causes an intended image to miss the runtime contract.

Do not deactivate image rows merely to preserve older checked artifacts.

### Tests

Change only:

- `tests/nonruntime-option-source-purge.test.mjs`

Preferred edit:

- Keep the retired Stingray seat-row absence assertions.
- Keep the deferred active `sec_tech_001` standard-equipment assertions.
- Remove the duplicate hardcoded seat display-order assertion, or narrow it to active seat IDs/RPOs if the purge test still needs to prove row collapse.
- Do not move the canonical seat presentation/order contract out of `tests/workbook-visual-copy-standardization.test.mjs`.

Do not change runtime behavior to satisfy this test.

### Generated artifacts to commit after review

Regenerate and commit intentional generated output for the active runtime path:

- `form-output/stingray-form-data.json`
- `form-output/stingray-form-data.csv` if rewritten by Stingray generation
- `form-output/inspection/grand-sport-runtime-contract.json`
- `form-output/inspection/z06-runtime-contract.json`
- `form-app/data.js`
- `stingray_master.xlsx` generated `form_*` sheet churn only if required by `scripts/generate_form.py --model stingray` and verified as generated-output-only

Generated preview/draft/report artifacts may change timestamps or image metadata as generator side effects:

- `form-output/inspection/grand-sport-contract-preview.*`
- `form-output/inspection/grand-sport-form-data-draft.*`
- `form-output/inspection/grand-sport-inspection.*`
- `form-output/inspection/z06-contract-preview.*`
- `form-output/inspection/z06-form-data-draft.*`
- `form-output/inspection/z06-inspection.*`

Review these diffs. Commit them only if they are necessary to keep the generated artifact set internally consistent; otherwise restore timestamp-only/report-only churn before handoff.

### Runtime code

Do not edit:

- `form-app/app.js`
- `form-app/index.html`
- `form-app/styles.css` / CSS assets
- dealer submission code or endpoint

If a runtime code diff appears, stop and classify it before proceeding.

## Constraints

- Preserve runtime logic: model switching, option selection, auto-adds, requirements, price totals, build download, and dealer submission behavior must remain unchanged.
- Allow the intentional customer-facing image metadata rollout from workbook `asset_map`.
- Preserve browser runtime structure; do not edit `form-app/app.js` for this pass.
- Preserve dealer submission endpoint, payload shape, modal behavior, and Turnstile behavior.
- Preserve workbook source-of-truth discipline: image metadata belongs in `asset_map`, not hardcoded runtime JS or generated artifacts by hand.
- Do not add dependencies.
- Do not refactor generator architecture.
- Do not touch copy/product allowlist rows, `sec_tech_001` ownership, `runtime_action`, or `body_style_scope` in this pass.
- Do not commit unrelated generated timestamp churn unless final diff review proves it is needed for artifact consistency.

## Implementation Plan

1. Preflight.

```sh
git status --short --branch
git branch --show-current
test ! -e './~$stingray_master.xlsx'
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

2. Snapshot pre-generation runtime artifacts.

```sh
mkdir -p /tmp/27vette-live-runtime-sync-before
cp form-output/stingray-form-data.json /tmp/27vette-live-runtime-sync-before/
cp form-output/stingray-form-data.csv /tmp/27vette-live-runtime-sync-before/
cp form-output/inspection/grand-sport-runtime-contract.json /tmp/27vette-live-runtime-sync-before/
cp form-output/inspection/z06-runtime-contract.json /tmp/27vette-live-runtime-sync-before/
cp form-app/data.js /tmp/27vette-live-runtime-sync-before/
```

3. Inventory image diffs and prove they map to active `asset_map` rows.

Create a temporary or checked helper only if necessary. The inventory should compare current checked artifacts against post-generation artifacts and classify every image-field diff as:

```text
model_key,option_id,rpo,section_id,field,before_value,after_value,asset_map_value,classification
```

Allowed classifications:

- `intentional_asset_map_addition`: field was absent before and now comes from active `asset_map`.
- `intentional_asset_map_replacement`: field changed from older checked value to active `asset_map` value.
- `timestamp_only`: generated timestamp or report timestamp.

Any other classification is a stop condition.

4. Update the stale test.

Edit `tests/nonruntime-option-source-purge.test.mjs` only. Remove/narrow the duplicate hardcoded seat display-order expectation. Keep the source-row purge assertions.

5. Regenerate active model artifacts and registry.

```sh
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_registry.py
```

6. Diff review.

Confirm generated diffs are limited to:

- intentional image metadata additions/replacements explained by `asset_map`;
- generated timestamps;
- expected Stingray generated workbook sheet churn;
- the stale test cleanup.

Confirm no runtime JS logic changed:

```sh
git diff -- form-app/app.js form-app/index.html form-app/*.css
```

7. Validate.

Run the gates in the order below. If side-effecting tests dirty generated artifacts after the reviewed sync, rerun `scripts/generate_registry.py` or restore only unrelated timestamp/report churn before final status.

## Validation Plan

Preflight and syntax:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
.venv/bin/python -m py_compile \
  scripts/generate_form.py \
  scripts/generate_registry.py \
  scripts/corvette_form_generator/inspection.py \
  scripts/corvette_form_generator/production.py \
  scripts/corvette_form_generator/contract.py \
  scripts/corvette_form_generator/workbook.py
```

Generation:

```sh
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_registry.py
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Image-diff proof:

- Run the inventory described above.
- Every image-field diff in runtime artifacts and `form-app/data.js` must map to active `asset_map` rows.
- No non-image/non-timestamp payload drift is allowed unless separately explained and approved.

Readiness gates:

```sh
for t in \
  tests/stingray-form-regression.test.mjs \
  tests/stingray-generator-stability.test.mjs \
  tests/grand-sport-contract-preview.test.mjs \
  tests/grand-sport-draft-data.test.mjs \
  tests/workbook-schema-standardization.test.mjs \
  tests/workbook-visual-copy-standardization.test.mjs \
  tests/z06-contract-preview.test.mjs \
  tests/z06-form-data-draft.test.mjs \
  tests/z06-runtime-promotion.test.mjs \
  tests/z06-interior-accessory-cleanup.test.mjs \
  tests/z06-performance-package-interactions.test.mjs \
  tests/z06-runtime-rule-corrections.test.mjs \
  tests/multi-model-runtime-switching.test.mjs \
  tests/nonruntime-option-source-purge.test.mjs \
  tests/seat-canonicalization-diff.test.mjs
 do
  node --test "$t"
done
.venv/bin/python -m pytest \
  tests/test_model_config_metadata.py \
  tests/test_registry_promotion_metadata.py \
  tests/test_schema_validation_metadata.py \
  tests/test_runtime_metadata_guards.py \
  tests/test_workbook_bool_hygiene.py \
  -q
```

After side-effecting tests:

```sh
git status --short
.venv/bin/python scripts/generate_registry.py
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Restore only unrelated timestamp/report churn. Keep reviewed intentional runtime artifact sync diffs.

Browser smoke, no submit:

```sh
cd form-app
../.venv/bin/python -m http.server 8000
```

Manual/browser checks:

- Load default Stingray.
- Switch to Grand Sport.
- Switch to Z06.
- Confirm no console errors.
- Confirm order summary still renders for all three promoted models.
- Spot-check the intentional image-bearing sections:
  - Stingray seat belts / wheels as applicable;
  - Grand Sport wheels `SWM`, `SWN`, `SWO`, `SWP`;
  - Z06 calipers and seat belts.
- Confirm option selection/default behavior still works in at least one single-select section and one multi-select section.
- Open dealer submission modal validation only; do not submit a live payload.

## Acceptance Criteria

- Current branch generated runtime artifacts are synced to workbook-owned `asset_map` image metadata.
- All image additions/replacements in `form-app/data.js` and promoted runtime artifacts are explained by active `asset_map` rows.
- `tests/nonruntime-option-source-purge.test.mjs` no longer asserts stale `10/25/40/80` Stingray seat order.
- Canonical active seat order remains guarded by `tests/workbook-visual-copy-standardization.test.mjs` as `10/20/30/40`.
- No `form-app/app.js`, CSS, HTML, dealer endpoint, dealer payload shape, or runtime selection logic changes.
- Full current-branch gates pass with side-effecting generated artifacts either retained as reviewed intentional sync or restored as unrelated churn.
- Browser smoke confirms the image rollout does not break model switching, order summary rendering, or option interactions.

## Non-Goals

- No broad visual redesign.
- No new asset naming convention decision beyond accepting the current active `asset_map` rows.
- No copy convergence decisions.
- No `sec_tech_001` ownership migration.
- No rule-mapping cleanup for `runtime_action` or `body_style_scope`.
- No runtime JS refactor.
- No deployment step.

## Approval Question

Approve this revised merge-readiness pass to ship the intentional workbook-owned option-card images, clean up the stale seat-order test, and prove current-branch generator/registry repeatability before merge?
