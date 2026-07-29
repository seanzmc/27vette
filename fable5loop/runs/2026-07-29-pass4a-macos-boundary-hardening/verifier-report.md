## Verdict

**PASS**

No implementation fixes required. C7 was provisionally PASS at verifier close because the parent-owned receipt, owning-spec, and STATE updates necessarily follow the independent verdict.

Verifier: `deleg_982c3aa8`; completed 2026-07-29T10:22:09-04:00.

## Criteria

- **C1 — PASS:** The pre-fix transcript records 13 passed / 2 failed in 672.33s. Both failures included `form-output/.DS_Store`; `.gitignore` ignores the file, and its measured mtime fell inside the failing run. The focused regression was independently confirmed GREEN after its recorded RED.
- **C2 — PASS:** The production diff is minimal: `protected_surface_hashes()` adds only `path.name != ".DS_Store"` to its recursive `form-output/` file selection.
- **C3 — PASS:** The exact-basename behavior is selective. Independent probes confirmed `.DS_Store` is excluded, a near-name remains included, and arbitrary file add/modify/remove changes the snapshot. The injected tracked-write candidate test remains present, and all seven shared Node boundary-helper tests passed independently, including the real arbitrary-untracked-file case.
- **C4 — PASS:** The current post-fix transcript records the complete candidate suite at 16 passed in 670.24s. `form-output/.DS_Store` was recreated during that successful run, so the result exercised the repaired path.
- **C5 — PASS:** Fresh evidence records package/schema clean, Python metadata/route/all-model 189 passed plus 111 subtests, editor 59 passed plus 7 subtests, all 18 Node files green serially, and protected tracked hashes unchanged. Post-fix package/schema and diff hygiene also passed.
- **C6 — PASS:** The repair is narrow and preserves the workbook, tracked generated contracts, published registry, runtime application, and dealer-submission boundaries.
- **C7 — PROVISIONAL PASS AT VERIFIER CLOSE:** Stage B had not started: all six exact candidates were independently confirmed tracked and clean, and there were no deleted tracked files. Final receipt/spec/STATE closeout remained the parent action after this verdict.

## Evidence inspected

- Current branch, status, HEAD, source/test diff, and scoped diff fingerprint.
- `scripts/verify_workbook_candidate.py` and all callers of `protected_surface_hashes()`.
- `tests/test_verify_workbook_candidate.py` including the new regression and existing injected tracked-write proof.
- `tests/lib/tracked-artifacts.mjs` and `tests/tracked-artifacts-guard.test.mjs`.
- `fable5loop/runs/2026-07-29-pass4a-macos-boundary-hardening/outcome.md`.
- `fable5loop/runs/2026-07-29-pass4a-macos-boundary-hardening/validation-output.txt`.
- `/tmp/27vette-pass4a-fresh-verification.txt` and `/tmp/27vette-pass4a-macos-boundary-validation.txt`, including timestamps and hashes.
- `AGENTS.md`, the owning cleanup specification, and Stage A/Stage B references.
- Tracking/status of the exact six Stage B candidates.

## Validation Output Inspected

Independent reruns/probes:

- Focused `.DS_Store` regression: 1 passed in 0.09s.
- Shared Node tracked-artifact helper: 7 passed.
- Exact-basename/near-name/arbitrary add-modify-remove probe: passed.
- Protected workbook/generated/runtime/published surfaces: no diff from HEAD.
- Exact six Stage B candidates: tracked and clean.

Recorded current validation inspected:

- Full post-fix candidate lane: 16 passed in 670.24s.
- Package/schema: valid, zero issues.
- Fresh pre-fix unaffected gates: Python 189 + 111 subtests; editor 59 + 7 subtests; all 18 Node files; protected hashes identical.

## Required Fixes Before Pass

None.

The parent must finish C7 by writing the post-verdict receipt metadata, owning-spec closeout note, and STATE update, then run the loop validator and Fable contract tests. That is closeout sequencing, not an implementation defect.

## Durable Lesson Candidates

- Long macOS runs can recreate ignored `.DS_Store` files inside protected generated roots. Exempt only the exact platform-metadata basename and prove arbitrary untracked outputs remain visible.
- A successful rerun is strongest when the ignored metadata was demonstrably recreated during that run; absence alone would not exercise the repaired branch.

## File Edit Statement

The independent verifier did not create, modify, delete, stage, or restore any repository file.
