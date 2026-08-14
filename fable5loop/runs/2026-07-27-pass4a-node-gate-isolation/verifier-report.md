# Independent verifier report — 2026-07-27-pass4a-node-gate-isolation

Verifier ran in a separate context with the rubric, the diff, the repo, and its
own commands. It did not see the maker's reasoning. One cycle.

## Verdict

**PASS with should-fix.** All eight criteria pass on evidence the verifier
produced itself. Four should-fix and three notes; every one is addressed below.
Two of the notes were real gaps in the new guard and were fixed rather than
accepted.

Worktree at end of verification identical to start: 71 tracked files under
`form-output/` + `form-app/` byte-identical, workbook `d11674e3…60bfd`. The
verifier deliberately dirtied runtime contracts twice (C1 replay, C3 break-one)
and restored both times.

## Criteria

| # | Verdict | Evidence the verifier produced |
|---|---|---|
| C1 | PASS | Ran all five HEAD versions via `git show HEAD:tests/<f>` into scratch. Churn reproduced exactly: GS files → `M grand-sport-runtime-contract.json`, Z06 files → `M z06-runtime-contract.json`. Pre-change results matched too (5/1, 18/1, 3/3, 24/24, 7/7). |
| C2 | PASS | Hashed all 71 tracked files under both roots (`git ls-files -z … \| xargs -0 shasum -a 256`), ran the five gates serially, re-hashed after each. `diff` identical every time. |
| C3 | PASS | Stripped only the two `"--output-root", outputRoot,` argv lines from a scratch copy of `z06-contract-preview` → `AssertionError: generation must not write tracked generated artifacts: form-output/runtime/z06-runtime-contract.json (modified)`, 0 pass / 1 fail, and `git status` confirmed the file really was rewritten. |
| C4 | PASS | Built three weakened helpers and ran the guard test against each: **(A)** empty Map → 1 pass / 4 fail; **(B)** no-op assert with real hashing → 2 pass / 3 fail; **(C)** hash only `form-app/data.js` → 1 pass / 4 fail. All five gates still passed under every weakening — which is exactly the vacuity the guard test exists to catch, and it caught all three. |
| C5 | PASS | Read `section_master` itself with openpyxl. Every changed value matches the workbook. **Searched for a fourth stale pin and found none:** re-derived all 13 remaining placement assertions in `grand-sport-draft-data` and all 12 in `grand-sport-contract-preview` from the workbook. Confirmed `sec_lpow_001`-absent is pre-existing and is an emitted-choices claim, not a `section_master` claim — correct as written. |
| C6 | PASS | Absence assertion present in both files and passing on fresh generation. |
| C7 | PASS | Set-difference of every `assert.*` expression, HEAD vs worktree, per file. Total removals: the four `afterAppData`/`beforeAppData` lines, the two `sec_perf_support_001` lines, the two stale display-order pins. Nothing else. Replacement confirmed strictly stronger — `form-app/data.js` is inside the hashed set, plus 70 other files. |
| C8 | PASS | Ran all 18 node gates serially; every count matched, churn empty after each. Sole failure `workbook-schema-standardization` "active explicit excludes…" — file untouched by this diff, recorded in STATE.md as a known baseline failure since 2026-07-26. Schema gate `{"status":"valid","issue_count":0}`. Verified the pytest claim cheaply: `tests/test_fable5_loop_contract.py` 1 failed / 12 passed, failure being this receipt folder. |

## Findings and resolutions

**1. should-fix — receipt claimed a STATE.md edit that had not happened.**
`validation-output.txt` said the stale 2026-07-05 open-failure entry "is
corrected in STATE.md" while `git status fable5loop/STATE.md` was empty. The
verifier also explained *why* `test_validator_rejects_stale_last_session_pointer`
now passes: it picks the latest run dir **that has a `run.json`**, and this
run's folder had none, so `Last session` still correctly resolved to the Pass 3
receipt. **Resolved:** the STATE.md correction is now actually made, and the
tense fixed. The verifier's mechanism note is recorded with it — the test's pass
is contingent on receipt completeness, so it is not yet proof the 2026-07-05
defect is gone; re-checked after `run.json` landed (see validation output).

**2. should-fix — two "recorded below" forward-references with nothing below.**
The pytest re-run and loop-validator lines pointed at output the file did not
contain, and the loop validator was in fact failing at that moment.
**Resolved:** both appended with real output after the receipt completed.

**3. should-fix — the non-scope list omitted Stage A items landing on these exact files.**
Spec §Pass 4 Stage A also calls for moving unique runtime assertions out of the
four preview/draft files and reclassifying them as optional diagnostics, and for
repointing `z06-interior-accessory-cleanup` at runtime-contract data instead of
the draft artifact (it still reads the draft at line 8). Neither was delivered
and neither was listed, while seven other deferred items were — a reader could
infer these five files are Stage-A-done. **Resolved:** `outcome.md`'s non-scope
list now names both, plus the pinned-doc updates and the Stage A exit criteria.

**4. should-fix — README sentence over-claimed which tests are guarded.**
It said "the Grand Sport and Z06 preview/draft rows"; the Z06 row holds five
tests and only three carry the guard —
`z06-performance-package-interactions` and `z06-runtime-rule-corrections` never
invoke `generate_form.py` at all. **Resolved:** the sentence now names the five
files explicitly.

**5. note — the guard could not see an untracked file written into a protected root.**
`git ls-files` enumeration meant a brand-new untracked file under `form-output/`
would pass silently, and the "(added)" branch was only reachable synthetically.
**Fixed rather than accepted:** `artifactPaths()` now unions `git ls-files` with
a recursive directory walk of both roots, and a new test writes a real stray file
into `form-output/inspection/` and asserts the guard reports it `(added)`.

**6. note — a deleted tracked artifact crashed with ENOENT instead of reporting "(removed)".**
`fs.readFileSync` was unguarded, so the post-read threw before the comparison
could classify the removal. **Fixed rather than accepted:** missing paths now
carry a sentinel digest, the comparison classifies added/removed/modified from
it, and a new test deletes a real runtime contract, asserts the `(removed)`
message, and restores it.

**7. note — one provenance claim asserted more firmly than the evidence supports.**
"The workbook has owned 35 and 11 since that section edit" is a claim about
workbook history that a binary `.xlsx` cannot verify. **Resolved:** the claim is
narrowed in `validation-output.txt` to what was actually measured — the workbook
owns those values now, and the checked-in expectations disagreed with both the
workbook and a fresh generation.

## Post-fix state

Findings 5 and 6 changed `tests/lib/tracked-artifacts.mjs` after the verdict, so
the guard test and the five gates were re-run; results are in
`validation-output.txt` under "Post-verifier re-run". The guard test went 5 → 7
tests, and the two new cases exercise the previously synthetic-only branches
against the real filesystem.

## Evidence inspected

`git show HEAD:` for all five changed test files, re-run individually at HEAD;
`git diff tests/ README.md`; `tests/lib/tracked-artifacts.mjs` and three weakened
shadow builds of it; `stingray_master.xlsx` `section_master` read directly with
openpyxl; a full 71-file SHA-256 baseline of `form-output/` + `form-app/`; a
break-one copy of `z06-contract-preview` with the `--output-root` argv removed;
all 18 node gate files; `docs/superpowers/specs/2026-07-23-validation-single-lane-active-surface-cleanup.md`
§Pass 4 Stage A; `fable5loop/STATE.md`.

## Validation Output Inspected

`fable5loop/runs/2026-07-27-pass4a-node-gate-isolation/validation-output.txt`,
re-executed rather than read: the RED baseline, the workbook reads, the break-one,
the vacuity matrix, the assertion set-difference, and all 18 node gates with churn
checks after each. The 18-minute Python suite was not re-run by instruction; its
single failure was verified directly through `tests/test_fable5_loop_contract.py`.

## Required Fixes Before Pass

1. Make the STATE.md correction the receipt claimed, or restate it as pending.
2. Append the actual pytest re-run and loop-validator output the receipt forward-references.
3. Add the two omitted Stage A items — the preview/draft reclassification and the
   `z06-interior-accessory-cleanup` draft-to-runtime repoint — plus the pinned-doc
   updates and Stage A exit criteria to the non-scope list.
4. Correct the README sentence to name the five guarded files rather than "rows".
5. Close the untracked-file blind spot in the guard, or record it as a known limit.
6. Stop the ENOENT crash on a deleted artifact, or record it.
7. Narrow the unverifiable "since that section edit" workbook-history claim.

All applied; post-fix evidence in `validation-output.txt`.

## Durable Lesson Candidates

1. A boundary check enumerated from `git ls-files` is blind to exactly the file a
   misbehaving writer is most likely to produce — a new, untracked one. Union the
   index with a directory walk of the protected root, and prove the added-file
   branch by writing a real stray file, not by mutating the before-map.
2. A guard whose "removed" branch reads the file it is about to classify crashes
   with ENOENT before it can report the removal. The gate still goes red, so the
   defect hides behind a passing suite; carry missing paths as a sentinel value
   and exercise the branch by deleting a real artifact and restoring it.
3. A receipt sentence in the present tense ("is corrected in STATE.md") is a
   claim about the worktree, and `git status` is the cheap check. Same for
   "recorded below" — verify the thing is actually below before writing it.

## File Edit Statement

The verifier edited no repository file. It ran three weakened helper builds and a
break-one test copy in the session scratchpad, and twice dirtied
`form-output/runtime/*-runtime-contract.json` deliberately (the C1 HEAD replay and
the C3 break-one), restoring with `git restore form-output form-app` both times
and confirming clean afterwards. Final state at hand-back: the maker's five
modified test files, two new test files, the README edit, and the untracked run
directory. Workbook `d11674e3…60bfd` unchanged; all 71 tracked files under
`form-output/` and `form-app/` byte-identical to their pre-verification hashes.
