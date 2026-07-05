# Outcome rubric · 2026-07-05 superpowers untrack (simplification Pass 1)

Task-specific derivative of `fable5loop/outcomes/27vette-loop-outcomes.md`.

## Task summary

- Goal: implement simplification-audit Pass 1 only — untrack `.superpowers` transient session state, archive the brainstorm mockups, add the ignore rule; narrow spec before edits.
- Changed surface: repo hygiene (git tracking + `.gitignore` + docs archive) plus loop receipt/STATE.
- Source-of-truth decision: tooling/session workspace; archived mockups become historical docs under `docs/archive/brainstorm/`.
- Protected boundaries: workbook, generated artifacts, runtime app, styling, dealer submission, ingest — untouched.
- Expected files: 6 mockup renames to `docs/archive/brainstorm/2026-06-18-form-visualizer-flow/`, 2 state-file deletions, `.gitignore` rule, spec `.hermes/plans/superpowers-untrack-pass1-spec.md`, this receipt, `fable5loop/STATE.md`.

## Required outcome criteria

1. Spec-first: narrow spec written before any edit, naming exact files, archive-vs-ignore split, and gates.
2. Exact scope: working tree shows only the named changes plus permitted loop artifacts; no other audit passes touched.
3. Archive not delete: mockups preserved as tracked renames (history intact); only transient pid/state files deleted.
4. Ignore rule effective: `git check-ignore` attributes `.superpowers/` paths to the new rule.
5. Independent verifier grades from artifacts only and returns a written verdict.
6. Validation real: spec gates run with real output; loop validator green after receipt/STATE writes.

## Result

All criteria met. Verifier verdict: pass (9/9 criteria). See `verifier-report.md`.
