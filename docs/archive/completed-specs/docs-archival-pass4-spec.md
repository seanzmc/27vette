# Docs Archival Spec (Simplification Pass 4)

Date: 2026-07-05
Status: Completed 2026-07-05. See completion record at end.

## Diagnosis

14 docs/plans carry explicit implemented/completed/resolved status but live in active locations, repeating the drift the completed 2026-06-27 cleanout pass fixed. Status evidence verified in the simplification audit (`fable5loop/runs/2026-07-05-simplification-audit/verifier-report.md` claim 5, verifier PASS).

Reference scan (git grep, excluding archives): only path references outside the moving set are five code/test comments naming `docs/derived-swap-eviction-spec-2026-07-02.md` or `workbook-consistency-review-2026-06-11.md`; `docs/merge-readiness/asset-map-image-sync-inventory.csv` has no references (the merge-readiness plan matches are prose, not paths); README.md references none of the targets.

Risk level: low. Docs/file-organization plus comment-only path updates in code/tests. No behavior change.

## Exact changes

Move to `docs/archive/completed-specs/` (git mv):

1. `docs/asset-media-drift/` (all 7 phase files, implemented/CLOSED) → `docs/archive/completed-specs/asset-media-drift/`
2. `docs/asset-media-drift-remediation-spec-2026-06-30.md` (implemented; self-describes as status record)
3. `docs/derived-swap-eviction-spec-2026-07-02.md` (IMPLEMENTED, both phases landed 2026-07-02)

Move to `docs/archive/old-reports/` (git mv):

4. `docs/asset_media-audit-6-30.md` (RESOLVED 2026-07-02)
5. `docs/copy-convergence-review-2026-06-17.md` (dated review; follow-ups tracked in route map)
6. `docs/workbook-consistency-review-2026-06-11.md` (dated review)
7. `docs/merge-readiness/asset-map-image-sync-inventory.csv` (unreferenced inventory); remove then-empty `docs/merge-readiness/`

Delete from active plans (git rm; repo policy "delete as completed", precedent 2026-06-27):

8. `.hermes/plans/agent-instruction-token-efficiency-spec.md` — Status: COMPLETED 2026-07-01
9. `.hermes/plans/asset-map-category-folder-matching-spec.md` — Status: Completed 2026-06-29
10. `.hermes/plans/completed-plans-and-deprecated-docs-cleanout-spec.md` — Status: Completed on 2026-06-27
11. `.hermes/plans/root-archive-folder-cleanout-spec.md` — Status: Completed on 2026-06-27

Comment-only reference updates (no behavior change):

- `scripts/corvette_form_generator/rule_derivation.py:33` → `docs/archive/completed-specs/derived-swap-eviction-spec-2026-07-02.md`
- `tests/test_rule_derivation.py:4` → same
- `tests/workbook-schema-standardization.test.mjs:360` → same
- `tests/z06-form-data-draft.test.mjs:305` → same
- `tests/test_editor_lints.py:6` → `docs/archive/old-reports/workbook-consistency-review-2026-06-11.md`

Explicitly deferred (kept active):

- `docs/fable5-compounding-loop-spec.md`, `docs/fable5-compounding-loop-hardening-spec.md` — `fable5loop/STATE.md` cites them as Evidence; archive only with coordinated STATE update in a later pass.
- `docs/roadmap_wishes.md` (no completion status), `docs/Audit-route-map.md` + `docs/audit-cleanup-overview.md` (Pass 6 scope), `docs/ingest/` (active workflow), all other `.hermes/plans` files (open or keep-historical per the 2026-06-27 classification).

## Constraints / non-goals

Pass 4 only; no other roadmap passes. No workbook writes, no generated-artifact edits, no runtime/data.js changes, no test-logic changes (comments only). Historical prose inside archived payloads is not rewritten.

## Validation plan

1. `git grep` for each moved/deleted filename outside `docs/archive/**`, `archive/**`, `fable5loop/runs/**`, and this spec → no active-path matches.
2. `test ! -d docs/merge-readiness && test ! -d docs/asset-media-drift`.
3. Comment-touched gates prove no breakage: `node --test tests/workbook-schema-standardization.test.mjs tests/z06-form-data-draft.test.mjs` and `.venv pytest tests/test_rule_derivation.py tests/test_editor_lints.py -q`.
4. `git diff --check`.
5. Independent verifier; loop validator after receipt/STATE writes.

## Completion record

Implemented 2026-07-05 (staged, not committed). All named moves/deletions/comment updates landed exactly as scoped; nothing else touched.

Validation results (real output):

- Reference grep for moved/deleted names outside archives/receipts/this spec: no matches.
- `docs/asset-media-drift/` and `docs/merge-readiness/` absent.
- Node gates: `workbook-schema-standardization` + `z06-form-data-draft` → 33/33 pass (worktree needed a local `.venv` symlink to the main repo venv).
- Pytest: `test_rule_derivation.py` green with `PYTHONPATH=scripts`; `test_editor_lints.py` 23 passed, 3 pre-existing RealWorkbookCompareTest failures (identical on unmodified HEAD file — live-workbook state, unrelated to the docstring edit).
- Gate side effect caught and fixed: the z06 node gate rewrote `form-output/runtime/z06-runtime-contract.json` `generated_at`; restored via `git restore` so generated surfaces diff-empty against HEAD.
- `git diff --check`: clean.
- Independent verifier: initial FAIL on the timestamp churn, PASS 11/11 after restore (`fable5loop/runs/2026-07-05-tidy-pass4-pass7/verifier-report.md`).

Deferred as scoped: fable5 loop spec docs (STATE evidence refs), roadmap_wishes, route-map/overview condensation (Pass 6), ingest docs, remaining `.hermes/plans` per the 2026-06-27 classification.

Residual risks / follow-up: changes staged pending commit approval; none other implied.
