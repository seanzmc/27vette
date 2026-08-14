# Spec: complete paint accents + persistent progress checkmarks

Status: implemented 2026-07-05
Date: 2026-07-05
Scope: runtime UI/styling behavior only. No workbook, generator, generated artifact, pricing, selection-rule, or dealer-submission changes.

## Diagnosis

Change type: mixed runtime presentation + runtime navigation-state fix.
Risk: low if scoped to `form-app/app.js` and focused runtime tests; visual smoke still needed because accent colors are presentation.

Evidence inspected:

- Branch/worktree: `git status --short --branch` -> `## main...origin/main`; no dirty files before this spec.
- `form-app/app.js`
  - `PAINT_ACCENTS` at lines 211-221 currently maps only six active paint RPOs: `GKZ`, `G4Z`, `GTR`, `GBK`, `G26`, `GPH`.
  - `applyAccentForPaint()` at lines 250-260 sets `--accent`, `--accent-dark`, `--on-accent`, and `--accent-glow` from the selected paint RPO, falling back to Torch Red.
  - `renderStepRail()` at lines 1950-1970 computes completion from `index < activeIndex && !missingStepKeys.has(step.step_key)`. That correctly suppresses a checkmark for a missing required previous step, but also removes all later completed-step checkmarks when the user navigates back because completion is tied to current position.
- Generated runtime paint inventory from `form-app/data.js`:
  - Active paint RPOs across promoted models are the same ten: `G8G`, `GBA`, `GKA`, `GBK`, `GTR`, `GEC`, `GPH`, `G4Z`, `G26`, `GKZ`.
  - Missing accent mappings are `G8G` Arctic White, `GBA` Black, `GKA` Blade Silver Metallic, and `GEC` Pitch Gray Metallic.
- `form-app/styles.css`
  - Buttons and active step indicators use `var(--accent)` background with `var(--on-accent)` text at lines 190-203 and 503-506, so each accent must carry a readable foreground color.
  - Step completion checkmarks use separate `--ok` / `--ok-bg` at lines 498-500; the progress fix should not restyle completion.
- `tests/stingray-form-regression.test.mjs`
  - Existing test at lines 866-900 proves checkmark suppression for an incomplete previous step and restoration after satisfying it.
  - Missing test: navigate forward far enough to mark steps complete, navigate back to an earlier incomplete/active step, and confirm already completed satisfied steps retain checkmarks.

Root causes:

1. Accent map coverage is incomplete for the active paint list. Unmapped paints fall back to Torch Red, so four paint choices do not affect the theme.
2. Step rail completion is derived from current active index instead of durable user progress. Back navigation makes previously completed satisfied steps look incomplete.

## Source-of-truth decision

- Paint availability and labels remain generated data from the workbook. The active paint list should be discovered from generated `data.choices` in tests, not duplicated as a product source.
- The accent color table is runtime presentation metadata only. It does not change option data, selection rules, generated contracts, or workbook source rows.
- Progress checkmark behavior belongs in runtime JS. It is UI state derived from navigation history plus `missingRequirementDetails()`; no workbook or generator change is needed.

## Exact files expected to change after approval

- `form-app/app.js`
  - Add missing `PAINT_ACCENTS` entries for `G8G`, `GBA`, `GKA`, and `GEC` with contrast-safe `onAccent` values.
  - Add a small progress-state helper, e.g. `state.farthestStepIndex` plus `markStepProgress()` / `resetStepProgress()`, or an equivalent `completedStepKeys` mechanism.
  - Update `renderStepRail()` so a step shows `complete` when it is within the furthest reached path and is not in `missingRequirementDetails()`; current active step stays active, not complete.
  - Reset progress state on `resetModelScopedState()` / model switch.
- `tests/stingray-form-regression.test.mjs`
  - Add/extend tests for all active generated paint RPOs having a mapping and for `accent` vs `onAccent` contrast being at least WCAG 4.5:1.
  - Extend the step-rail regression to prove completed satisfied steps stay checked after navigating back while incomplete steps remain numeric.

No expected changes:

- `stingray_master.xlsx`
- `form-output/*`
- `form-app/data.js`
- Dealer endpoint/payload/modal behavior
- Runtime selection/pricing/summary contracts

## Proposed accent direction

Keep the existing six accents unchanged unless browser smoke shows a readability issue. Add contrast-safe entries for the four missing paints:

- `G8G` Arctic White: light neutral accent, dark `onAccent`.
- `GBA` Black: high-contrast graphite/silver treatment instead of true black-on-dark, dark `onAccent` on the button fill.
- `GKA` Blade Silver Metallic: silver accent, dark `onAccent`.
- `GEC` Pitch Gray Metallic: medium graphite accent with dark or white `onAccent` chosen by contrast check.

The test should validate contrast mechanically so the table cannot regress to unreadable button/active-step text.

## Companion-file impact

- Generated contracts/artifacts: n/a; no generator or data artifact should change.
- Count/ID-sensitive tests: update focused runtime test only; no generated counts expected.
- Docs/specs: this spec is the planning artifact; no README/AGENTS updates expected.
- Gate reminders/profile guidance: n/a; validation commands unchanged.
- Browser/manual verification: required because accent color perception and back-navigation UX are visual/interactive.

## Constraints and non-goals

Standing constraints from `AGENTS.md` apply, especially source boundaries (§3), spec-first approval (§4), dealer boundary (§6), validation (§9), and handoff (§11).

Spec-specific constraints:

- No new dependencies.
- No workbook writes or generated artifact edits.
- Do not use CSS to hide missing required-step state; keep `missingRequirementDetails()` as the completion gate.
- Do not change the green completion style or step labels beyond preserving/removing the `complete` class/checkmark correctly.
- Do not change dealer submission behavior or payloads.
- Do not broaden into vehicle visualizer/layered imagery work.

## Validation plan

After approval and implementation:

1. `node --test tests/stingray-form-regression.test.mjs`
   - Covers accent mapping/contrast and progress checkmark regression.
2. Browser smoke against `form-app/`
   - Select each of the ten active paint colors and inspect console for JS errors.
   - Spot-check contrast/readability for at least the four newly mapped paints in primary buttons and active step indicator.
   - Navigate forward to a later step, then back to an incomplete step; confirm satisfied completed steps retain green checkmarks while the incomplete step remains numeric/uncompleted.
3. `git diff --check`
4. `git status --short`
   - Confirm only approved runtime/test/spec files changed and no generated artifacts moved.

Gates not planned:

- Workbook package/schema validation: not relevant; no workbook or generated source changes.
- Generator/registry regeneration: not relevant and should remain untouched.
- Dealer live submission: not relevant and not safe as routine validation.

## Approval question

Approve this runtime-only pass to update `form-app/app.js` and `tests/stingray-form-regression.test.mjs` under the scope above? If you want, I can make the implementation on a small branch first instead of editing directly on `main`.

## Completion evidence

Implemented on branch `runtime-paint-accent-progress-checkmarks`.

Changed files:

- `form-app/app.js`
  - Added accent mappings for `G8G`, `GBA`, `GKA`, and `GEC`.
  - Adjusted `GTR` accent from `#3f73ff` to contrast-safe `#3367ff` while preserving the blue theme.
  - Added durable step-progress state so satisfied completed steps keep checkmarks after back-navigation, while `missingRequirementDetails()` still suppresses incomplete steps.
- `tests/stingray-form-regression.test.mjs`
  - Added generated paint-RPO accent coverage and contrast tests.
  - Extended the progress rail regression for back-navigation to an incomplete step.
- `.hermes/plans/paint-accent-progress-checkmarks-spec.md`
  - Closed this spec with implementation evidence.

Validation run:

- `node --test tests/stingray-form-regression.test.mjs` -> pass: 89/89.
- Browser smoke at `http://127.0.0.1:8765/` with `python3 -m http.server 8765 --directory form-app`:
  - All ten active paint RPOs mapped and applied to CSS variables.
  - Accent/on-accent contrast results: `G8G` 16.52, `GBA` 8.86, `GKA` 11.96, `GBK` 11.60, `GTR` 4.64, `GEC` 7.64, `GPH` 4.66, `G4Z` 6.18, `G26` 6.61, `GKZ` 4.56.
  - Back-navigation probe: `model` and `exterior_appearance` retained `complete`; active incomplete `base_interior` stayed numeric `8`.
  - Browser console: no messages or JS errors.
- `git diff --check` -> pass.
- `git status --short --branch` -> branch `runtime-paint-accent-progress-checkmarks`; modified `form-app/app.js`, `tests/stingray-form-regression.test.mjs`; untracked this spec file.

Gates not run:

- Workbook/package/schema validation: not relevant; no workbook or generated source changes.
- Generator/registry regeneration: not relevant and intentionally not run; generated artifacts should remain untouched.
- Live dealer submission: not relevant and not safe for routine validation.

Residual risks / follow-up:

- Manual visual taste review remains subjective for the four newly mapped neutral/gray/black paint accents; mechanical contrast and browser CSS-variable smoke passed.
- No follow-up implied unless the visual palette should be tuned after review.
