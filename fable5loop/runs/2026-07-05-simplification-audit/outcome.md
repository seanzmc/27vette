# Outcome rubric · 2026-07-05 repo simplification audit

Task-specific derivative of `fable5loop/outcomes/27vette-loop-outcomes.md`.

## Task summary

- Goal: read-only repo simplification audit covering route normalization, stale artifact cleanup, docs/archive hygiene, obsolete workflow retirement, and confusing repo surfaces; deliverable is a ranked cleanup roadmap with small reversible implementation passes and validation gates.
- Changed surface: none (analysis only). Writes limited to the loop-required run receipt and `fable5loop/STATE.md` update.
- Source-of-truth decision: no source changes; roadmap items defer to their owning surfaces (workbook / generator / docs / tooling) with spec-first gates where AGENTS.md requires them.
- Protected boundaries: workbook, generated artifacts, runtime app, styling, dealer submission, ingest — all untouched.
- Expected files: `fable5loop/runs/2026-07-05-simplification-audit/*` and `fable5loop/STATE.md` only.

## Required outcome criteria

1. Scope is explicit: audit names what it inspected and confirms no repo file edits outside the loop receipt/STATE.
2. Source evidence is read first: every roadmap claim cites concrete repo evidence (tracked-file listings, grep results, file/line references, doc status lines).
3. Independent verifier: a separate-context verifier graded the audit's 11 claims plus rubric criteria from artifacts only and returned a written verdict.
4. Validation is real: `scripts/validate_fable5_loop.py` run after receipt/STATE writes with real output captured.
5. Memory compounds: verified facts and last-session pointer written to `STATE.md` with timestamps and Evidence references.
6. Safety boundaries handled: no workbook writes, no generated-artifact edits, no dealer-submission changes; recommendations that touch protected surfaces are flagged spec-first.

## Result

All criteria met. Verifier verdict: pass (all 11 claims + 3 rubric criteria). See `verifier-report.md`.
