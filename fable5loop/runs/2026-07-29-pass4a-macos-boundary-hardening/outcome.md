# Outcome rubric — Pass 4 Stage A macOS boundary hardening

Run: `2026-07-29-pass4a-macos-boundary-hardening`
Spec: `docs/superpowers/specs/2026-07-23-validation-single-lane-active-surface-cleanup.md`, Pass 4 Stage A exit gate

## Diagnosis

Fresh Stage A verification reproduced two failures in `tests/test_verify_workbook_candidate.py`. During each 11-minute suite run, macOS recreated ignored Finder metadata at `form-output/.DS_Store`. `protected_surface_hashes()` treated every file below `form-output/` as a protected generated artifact, so the candidate lane reported the OS metadata as a boundary violation even though all tracked generated artifacts remained byte-identical.

The failure is an incomplete Stage A exit-gate boundary, not a product, workbook, generated-contract, publication, runtime, or dealer defect. Per Sean's conditional instruction, this run completes Stage A and does not start Stage B.

## Boundaries

- May change only `scripts/verify_workbook_candidate.py`, its focused test, this receipt, the owning spec closeout, `fable5loop/STATE.md`, and the repo-local Fable skill's durable failure-mode list.
- Must continue detecting arbitrary untracked files and all tracked-file additions, removals, or modifications under protected roots.
- Must ignore only the exact macOS Finder metadata basename `.DS_Store`.
- No canonical workbook, generated runtime contract, published registry, runtime application, or dealer-submission change.
- No Stage B deletion.

## Criteria

C1. A focused regression test fails before the implementation change because `protected_surface_hashes()` includes `form-output/.DS_Store`.

C2. The smallest implementation change excludes only files whose basename is exactly `.DS_Store` from candidate-lane protected-surface hashing.

C3. Existing boundary tests still prove the lane reports a real tracked mutation; the shared Node boundary helper still proves arbitrary untracked-file detection.

C4. The complete `tests/test_verify_workbook_candidate.py` suite passes on the current macOS host even when Finder metadata is recreated during execution.

C5. Fresh Stage A evidence remains green: package/schema validation, the Python metadata/route/all-model gate, editor route tests, all 18 serial Node files, and protected tracked-artifact identity. Any gate not rerun after the two-line implementation fix is explicitly bound to the pre-fix fresh run because the fix changes only candidate-lane hashing.

C6. An independent verifier confirms the fix is narrow, the Stage A claims are accurate after the repair, and Stage B was not started.

C7. The receipt, owning spec, and STATE record the initial failure, root cause, repair, validation, and next action without claiming Stage B work.

### Late C9 correction rubric

The first Stage A verifier, dispatched before the macOS defect was found, completed after the initial closeout and found a separate zero-reference failure. These additional criteria close that finding without reopening Stage B:

C8. `scripts/corvette_form_generator/rules.py` no longer describes Stingray as using a separate `production.py` rule route; the comment matches the executable one-route call through `build_draft_rules`.

C9. Every `.hermes/plans` file that retains a compatibility artifact, `production.py`, seat-diff, or unpublished-contract command/path carries an explicit top-of-file superseded/historical notice. Plans with unresolved product/data questions remain open only for those questions; their old commands are not operator guidance.

C10. A bounded scan finds candidate-name references in active `scripts/` and `tests/` only inside the exact Stage B candidates themselves. The ten plans are mechanically paired with ten superseded notices; README/current route owners remain unchanged. Focused rule/model tests, loop gates, diff hygiene, protected surfaces, and all six undeleted candidates pass verification.

## Process deviation

The task-specific rubric was written after the production edit because the defect surfaced during the requested final verification. TDD order was preserved for the repair: the focused regression test was written and observed failing before `protected_surface_hashes()` changed.

## Skill update decision

Updated. The repo-local Fable skill now records that long macOS runs can recreate ignored `.DS_Store` metadata inside a protected root, and that the safe repair is an exact-basename exemption paired with proof that arbitrary untracked output remains visible.
