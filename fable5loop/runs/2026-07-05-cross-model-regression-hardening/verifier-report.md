# Verifier Report — 2026-07-05 cross-model regression hardening (report-first)

Independent verifier (separate context, read-only, no maker reasoning, no mutating gates).

## Verdict

PASS

## Criteria

| Claim | Status | Evidence |
|---|---|---|
| A1: `.summary-panel padding: 8px` assertion stale | PASS | Test line 734; current `styles.css` has `padding: 14px 12px`. |
| A2: shell-rhythm assertion stale | PASS | `--shell-radius: 8px` absent from current sheet; `--shell-gap: 12px` still present (`styles.css:38`) — maker wording corrected. |
| A3: icon-button `width: 42px` stale | PASS | Test line 766; current value `44px` (`styles.css:665`). |
| A4: `.choice-card` outline failure | PASS (reclassified) | Outline intact at `styles.css:1248` in base block (`:1232`); `cssBlock()` regex matches paint-step override (`styles.css:657`, added `ab878eb` 2026-07-05) first. Test-helper order dependence, not missing style. |
| A5: switching test expects removed `"ready"` stage | PASS | Test lines 584-586 vs `app.js:104` 3-stage array; `bf4576a` (2026-07-04) removed stage; test last updated `834968f` (2026-06-29). |
| B: data.js vs runtime-contract timestamp provenance drift, content in sync | PASS | `git show HEAD:` greps confirm 07-02T20:3x vs 14:10/20:42 timestamps; regen diff = 3 timestamp lines only. |
| C: worktree clean except spec + receipt | PASS | `git status --porcelain` = 2 new paths only; STATE/skill untouched at grading time. |
| D: `z06-runtime-promotion.test.mjs:157` runs `generate_registry.py` (rewrites `form-app/data.js`) | PASS | File read confirms `execFileSync(".venv/bin/python", ["scripts/generate_registry.py"])`. |
| Spec satisfies AGENTS.md §4 | PASS | Diagnosis, exact files, source-of-truth decision, companion impact, constraints, risks/non-goals, validation plan all present; scope tests-only. |
| validation-output.txt covers schema + all 13 README node gates + pytest gate | PASS | All rows present with pass/fail counts. |

## Evidence inspected

See criteria table evidence column; full inspection list in the verifier transcript: styles.css (:38, :657, :665, :734, :1232, :1248), app.js:104, tests/stingray-form-regression.test.mjs (:734, :744, :766, :946), tests/multi-model-runtime-switching.test.mjs (:534-592), tests/z06-runtime-promotion.test.mjs:157, AGENTS.md, README.md validation map, spec, receipt files, git show/log/status output.

## Validation Output Inspected

fable5loop/runs/2026-07-05-cross-model-regression-hardening/validation-output.txt plus the two full gate logs in the receipt folder (stingray-form-regression-full.log, multi-model-runtime-switching-full.log). Verifier did not re-run gates.

## Required Fixes Before Pass

None blocking. Two clarifications (applied by maker after verdict, spec + outcome.md updated):
1. `--shell-gap: 12px` persists in current styles.css; only part of the asserted rhythm is gone.
2. `.choice-card` outline failure is a `cssBlock()` helper order-dependence artifact from `ab878eb` paint-step CSS, not a removed style.

## Durable Lesson Candidates

1. `z06-runtime-promotion` gate rewrites `form-app/data.js` (registry regen), extending the known gate-churn class beyond runtime contracts.
2. Regex-based CSS block extraction in tests is order-dependent; anchor to base selectors or the earliest-match behavior breaks when scoped overrides are added.
3. Restyle/structural UI commits landed without re-running mapped gates; gate coverage docs accurate but enforcement lag exists.

## File Edit Statement

Verifier did not edit files and did not run mutating gates; all inspection read-only (git show/log/status, file reads, grep, receipt logs).

## Raw-log retirement note — 2026-07-29

The independent verifier originally inspected `stingray-form-regression-full.log` and `multi-model-runtime-switching-full.log`. Pass 4 Stage C retired those redundant raw logs after confirming that their decisive gate results, classifications, and verifier judgment remain in this report, `validation-output.txt`, and `outcome.md`. This append-only note records the evidence migration; it does not alter the original criteria or verdict.
