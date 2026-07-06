# Spec: Re-anchor stale Stingray/switching gate expectations to current committed UI

Status: implemented 2026-07-05 (approved by user; verifier PASS). Both test files re-anchored; gates green: stingray-form-regression 88/88, multi-model-runtime-switching 46/46, canaries grand-sport-draft-data 19/19 + z06-runtime-promotion 5/5 (gate timestamp churn restored). Validation results in `fable5loop/runs/2026-07-05-cross-model-regression-hardening/`. Residual risk: none implied.

## Diagnosis

Cross-model regression hardening pass (2026-07-05) ran the full README validation map on a clean worktree at `901539a`. Results:

- Real regressions: **none**.
- 5 failing tests, all stale expectations encoding pre-restyle UI:
  - `tests/stingray-form-regression.test.mjs` — 4 failures (84/88 pass):
    - `mobile shell exposes compact progress and summary targets` — asserts `.summary-panel { padding: 8px }` (old theme).
    - `shell containers share one spacing and radius rhythm` — `--shell-gap: 12px` survives (`styles.css:38`) but the rest of the asserted rhythm (`--shell-radius: 8px`, `.topbar,\n.workspace` radius block, old vehicle-bar negations) no longer matches the Full Carbon sheet.
    - `summary drawer is callable from desktop and condensed at smaller breakpoints` — asserts `.reset-icon-button/.download-icon-button width: 42px`; current committed value is `44px` (`styles.css:665`).
    - `vehicle setup exposes paced readability hooks without changing option step content` — asserts `outline: 2px solid transparent` inside the `.choice-card` block. The outline IS present in the base block (`styles.css:1232`, outline at `:1248`), but the test's `cssBlock()` regex helper matches the first occurrence of `.choice-card {`, which since `ab878eb` (2026-07-05) is the paint-step override `#stepContent[data-active-step="paint"] .choice-card` (`styles.css:657`). This one is test-helper brittleness (order-dependent regex), not a missing style — fix by anchoring the helper or the assertion to the base selector, not by weakening the style check.
  - `tests/multi-model-runtime-switching.test.mjs` — 1 failure (45/46 pass):
    - `runtime progressively advances vehicle setup panels before exterior paint` — asserts a 4th `"ready"` setup stage and that `Continue to Exterior Paint` is absent at `trim_level` stage. `bf4576a` (2026-07-04, "drop setup review step") reduced `vehicleSetupStages` to `["model", "body_style", "trim_level"]` (`form-app/app.js:104`); the continue CTA now renders at trim stage.

Root cause: deliberate, committed UI changes (`afa36fb` Full Carbon restyle 2026-07-03; `bf4576a` review-step drop 2026-07-04; `ab878eb` paint-step CSS 2026-07-05) landed without running/updating the Stingray and switching gates. Regression test last updated 2026-07-05 (`ab878eb`) without fixing these blocks; switching test last updated 2026-06-29 (`834968f`). Failures are **stale test expectations plus one order-dependent test-helper artifact**, not runtime defects. Independent verifier confirmed classification (run receipt `verifier-report.md`). While these gates are red, real Stingray/switching regressions would be masked.

Change class: tests/gates only. Risk: low (no runtime, workbook, generated, or dealer surface).

## Files expected to change

- `tests/stingray-form-regression.test.mjs` — the 4 named test blocks only.
- `tests/multi-model-runtime-switching.test.mjs` — the 1 named test block only.

No other files. Explicitly untouched: `form-app/app.js`, `form-app/styles.css`, `form-app/data.js`, `form-output/**`, `stingray_master.xlsx`, dealer submission code/tests, ingest surfaces.

## Source-of-truth decision

Committed runtime (`form-app/app.js`, `form-app/styles.css` at HEAD) is the approved current behavior (shipped via `afa36fb`..`ab878eb`). Tests re-anchor to it. No source edits.

## Approach

1. For each failing CSS assertion: replace old-theme literal with the equivalent invariant from current committed `styles.css` at the same altitude (e.g. assert `.summary-panel` exists with its current committed padding value; assert current shared-rhythm tokens if an equivalent exists, otherwise drop the assertion for the retired design decision and keep the surrounding behavior assertions). For the `.choice-card` outline case, fix the order-dependent `cssBlock()`/regex anchoring so it targets the base `.choice-card` block (`styles.css:1232`) instead of the paint-step override — the style itself is intact.
2. For the switching test: rewrite the setup-stage walk to the 3-stage flow — trim stage may show `Continue to Exterior Paint`; one `goToNextStep()` from completed trim goes to `paint`. Preserve all other assertions in the block.
3. Iterate each gate until green; failures beyond the first in each block re-anchored the same way.
4. Do not weaken non-stale assertions; anything that looks like a genuine behavior mismatch (not theme/stage drift) stops the pass and gets reported instead of patched.

## Companion-file impact

- README validation map: inspected, no change (test names/surfaces unchanged).
- AGENTS.md: no change.
- `form-app/*` runtime/styles: inspected, no change.
- Generated artifacts: no change (gate timestamp churn restored during this pass).

## Constraints

No unrelated refactor; no new dependencies; generated files stay untouched; workbook untouched; dealer boundary untouched.

## Risks and non-goals

- Risk: re-encoding exact CSS values recreates brittleness at next restyle. Mitigation: prefer structural/token-level assertions over pixel literals where the current sheet offers them; keep the same protective intent.
- Non-goal: fixing the `form-app/data.js` vs `form-output/runtime/*` timestamp provenance mismatch (content in sync; cosmetic; separate decision).
- Non-goal: adding new gates or CI wiring.

## Validation plan

- `node --test tests/stingray-form-regression.test.mjs` → 88/88.
- `node --test tests/multi-model-runtime-switching.test.mjs` → 46/46.
- Re-run one GS and one Z06 gate as cross-model canary (`grand-sport-draft-data`, `z06-runtime-promotion`), then `git restore` timestamp churn in `form-output/runtime/` and `form-app/data.js`.
- `git status` clean except the two test files.
