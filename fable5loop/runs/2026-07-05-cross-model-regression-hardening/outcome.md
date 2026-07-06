# Outcome: Cross-model regression hardening (report-first)

Date: 2026-07-05
Task: Prove the cross-model validation surface (Stingray, Grand Sport, Z06, registry publication, generated runtime contracts, model switching) is coherent after the simplification cleanup; classify all gate failures; propose the smallest useful hardening pass. Report-first: no product-surface edits without an approved spec.

## Rubric (task-specific derivative of `fable5loop/outcomes/27vette-loop-outcomes.md`)

1. Scope explicit: only loop artifacts + one spec file may change; workbook, `form-output/`, `form-app/data.js`, dealer submission, ingest untouched.
2. Source evidence read first: AGENTS.md, README validation map, docs/fable-ex-tasks.md, both named test files, generate_form.py, generate_registry.py, form-output/runtime/, form-app/data.js.
3. All README validation-map gates run serially with real recorded output (`validation-output.txt`).
4. Every failure classified as: real regression / stale test expectation / generated-artifact drift / dirty-worktree noise / pre-existing known issue — with file/line + commit evidence.
5. Gate-induced artifact churn restored; worktree clean afterward except loop artifacts + spec.
6. Deliverable includes health summary, evidence, spec (or "no edit justified"), handoff.
7. Independent verifier grades from artifacts only; STATE updated; skill-update decision recorded.

## Result

- **No real regressions.** 13 gates run; 11 fully green.
- 5 failing tests, all classified **stale test expectation** (one via order-dependent test-helper artifact):
  - 4 in `tests/stingray-form-regression.test.mjs` (84/88): assertions encoding pre-Full-Carbon UI vs restyle `afa36fb` (2026-07-03) and later CSS commits. `.summary-panel padding: 8px` (now `14px 12px`), `--shell-radius`-era rhythm block, icon-button `width: 42px` (now `44px`, `styles.css:665`). The `.choice-card outline` case is helper brittleness, not a missing style: outline intact at `styles.css:1248` in the base block (`:1232`), but the test's `cssBlock()` regex matches the paint-step override `#stepContent[data-active-step="paint"] .choice-card` (`styles.css:657`, added by `ab878eb` 2026-07-05) first. Verifier-corrected detail: `--shell-gap: 12px` still present (`styles.css:38`).
  - 1 in `tests/multi-model-runtime-switching.test.mjs` (45/46): asserts a 4th `"ready"` vehicle-setup stage; `bf4576a` (2026-07-04, "drop setup review step") reduced `vehicleSetupStages` to 3 (`form-app/app.js:104`). Test last updated 2026-06-29 (`834968f`).
- **Generated-artifact drift:** timestamp provenance only. Committed `form-app/data.js` carries `generated_at` 2026-07-02T20:32/20:34 while committed `form-output/runtime/*` contracts carry 14:10 — regenerating the registry from tracked contracts changes only 3 timestamp lines across ~156k lines, so content is in sync. Cosmetic; no action proposed.
- **New gate-churn fact:** `tests/z06-runtime-promotion.test.mjs:157` runs `scripts/generate_registry.py`, so the promotion gate rewrites `form-app/data.js` (not just the runtime contracts previously recorded in STATE). All churn restored with `git restore`; worktree verified clean.
- Pre-existing known issues re-confirmed by absence: `test_rule_derivation.py` needs `PYTHONPATH=scripts` (used); `test_editor_lints.py` live-workbook failures are outside this pass's gate set.

## Proposed hardening pass

`.hermes/plans/cross-model-stale-gate-expectations-spec.md` — re-anchor the 5 stale test blocks to current committed UI. Tests-only, no source edits. Approved and implemented same day.

## Implementation (post-approval, 2026-07-05)

- `tests/stingray-form-regression.test.mjs`: `cssBlock()` line-start anchored; breakpoint slice fix (`mobileStart` searched from `narrowDesktopStart` — the paint-step 760px block at `styles.css:692` was silently emptying the narrow-desktop slice); values re-anchored (`14px 12px`, `10px`, `44px`, `44px 44px`, `var(--accent)`, `var(--accent-glow)`); shell test rewritten to full-bleed invariants; retired-`ready` block replaced with trim-stage chip completion + normalization assertion. One additional stale sub-block surfaced during iteration (line ~1000 `ready` chip expectations) — same `bf4576a` class, re-anchored within spec scope.
- `tests/multi-model-runtime-switching.test.mjs`: `ready` hop removed; trim stage asserts the paint CTA; single `goToNextStep()` → paint.
- Implementation verifier: PASS — scope clean, every replaced assertion matched against committed source, all 12 deleted assertions confirmed stale, no live assertion weakened.
- Gates: stingray 88/88, switching 46/46, canaries GS draft-data 19/19 + Z06 promotion 5/5 (158/158). Gate churn restored; `form-output`/`form-app` clean.

## Changed in this run

- `.hermes/plans/cross-model-stale-gate-expectations-spec.md` (new, awaiting approval)
- `fable5loop/runs/2026-07-05-cross-model-regression-hardening/` (this receipt)
- `fable5loop/STATE.md` (verified facts, last-session pointer)
- `fable5loop/skills/27vette-fable5-compounding.md` (gate-churn failure mode extended with data.js/promotion-gate evidence)

Nothing else. Workbook, `form-output/`, `form-app/`, dealer submission, ingest: untouched (gate churn restored).
