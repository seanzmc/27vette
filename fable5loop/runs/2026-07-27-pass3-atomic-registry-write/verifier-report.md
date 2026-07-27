# Independent verifier report — 2026-07-27-pass3-atomic-registry-write

Separate context. Saw the rubric, the diff, and the claimed evidence; not the
maker's reasoning. Instructed to falsify.

## Verdict

**Cycle 1: FAIL.** No rubric hard-failure condition was tripped and the headline
claim is real, but three evidence-backed code defects and several receipt
inaccuracies. All ten findings fixed; post-fix evidence in `validation-output.txt`.

## Criteria

| ID | Result | Basis |
|---|---|---|
| R9.1 | partial | Temp file in the target dir and fsynced; failure-injection proof real. No directory fsync, and the fsync that exists was untested (V2, V3). |
| R9.2 | met | Destination provably never partial — under injected `OSError` and under real `SIGKILL`. |
| R9.3 | met | `--workbook` / `--root` / `--output` honored and isolating; an empty `--root` fails closed rather than falling back to the repo. |
| R9.4 | partial | Bytes identical modulo `generated_at`, independently confirmed. File **mode** silently changed 0644 → 0600 (V1). |
| R9.5 | met | Reproduced: the entire node gate set leaves `data.js` byte-identical; the same gate at HEAD does rewrite it. |
| R9.6 | met | Independent scan including constructed paths and the editor server: no second writer. |
| R9.7 | met | Candidate lane `ok: true`, `boundaryViolations: []`, registry inside the temp root. |
| X1 | partial | Every test carried a "breaks if" docstring, but three named changes no realistic implementation would make (V8). |
| X2 | met, caveat | The atomicity tests do fail against `write_text`; the exact "2 failed / 4 passed" was weakening-specific (V6). |
| X3 | fail | Node parity reproduced exactly and the three failures confirmed pre-existing at HEAD. Python-suite evidence did not exist in the receipt (V9). |
| X5 | fail | Requirements 7/8 correctly restated open, but three claims were inaccurate or unevidenced (V1, V5, V9). |

## Findings

**V1 — medium, real regression.** The atomic write changed `form-app/data.js`
from 0644 to 0600. `NamedTemporaryFile` creates at 0600 and `os.replace` swaps
the inode; the old `path.write_text()` preserved the destination's mode.

```
$ stat -f '%Sp %N' form-app/data.js
-rw-r--r-- form-app/data.js
$ .venv/bin/python scripts/generate_registry.py
$ stat -f '%Sp %N' form-app/data.js
-rw------- form-app/data.js
```

Isolated to the writer, not the caller, by calling `write_text_atomic` and
`Path.write_text` on the same chmod-644 file. Git does not record the bit, so it
survives only until the next checkout — meaning it manifests exactly on the
machine that publishes. No test covered it.

**V2 — medium.** No directory fsync after `os.replace`, so the rename is not
durable. It cannot produce a *truncated* file, because the data blocks are
fsynced before the rename — worst case the previous complete registry survives.
R9.1's stated contract was stronger than the implementation.

**V3 — medium.** A weakened build that kept same-directory staging and the full
cleanup and deleted only `handle.flush()` / `os.fsync()` passed all six tests.
The suite discriminated on staging location and non-truncation, not on the one
property fsync exists for.

**V4 — low/medium.** SIGKILL between the temp write and the replace leaves a
full-size hidden `.data.js.*.tmp` in the served directory with nothing to reap
it. Proven with a script that SIGKILLs itself inside `os.replace`: exit 137, the
destination intact and unchanged, one stray ~6MB temp file remaining.

**V5 — low.** The receipt attributed both churned runtime contracts to the two
grand-sport tests. Isolated per-file runs show the grand-sport tests dirty only
the grand-sport contract; the z06 contract comes from the z06 tests. Five node
files call `generate_form.py` without `--output-root`.

**V6 — low.** The X2 numbers were specific to one weakening: a literal
`write_text` (without the `mkdir`) fails three tests, not two. Also worth
recording: `Path(__file__).resolve()` defeats symlink shadowing, so a
PYTHONPATH-shadowed package must be a real copy.

**V7 — low, technical error.** "A temp file elsewhere would make `os.replace` a
cross-device copy, which is not atomic" is wrong, in three places. `os.replace`
never copies; cross-device raises `OSError(EXDEV)`. `shutil.move` is the one that
falls back to a copy. The test remains worth having — the real consequence is a
hard failure on a host where the repo and /tmp are separate volumes.

**V8 — low.** Two of six tests were near-vacuous.
`test_the_written_bytes_match_the_rendered_registry` compared the writer's output
against the same renderer the writer uses, so it could only detect mangling in
transit; `test_repeated_writes_are_stable` passed under all five weakenings
including plain `write_text`, which is idempotent by construction.

**V9 — medium.** The receipt ended "Python full suite: recorded below" and
recorded nothing; the run directory had no `run.json` and no verifier report, and
`fable5loop/STATE.md` had no entry. The claimed "1 failed on the loop-contract
test" was therefore self-inflicted by the incomplete receipt, not pre-existing.
Arithmetic checked without running the suite: `pytest --collect-only` → 554
collected, prior baseline 546 passed / 0 failed, +6 new tests → 551 + 1 + 2
skipped = 554. Consistent.

**V10 — info.** The new node parity test compares the isolated rebuild against
the *tracked* `data.js`, so it now doubles as a staleness gate; the tracked file
already lags by one `generated_at`. Any future artifact regeneration without
republishing turns it red. Arguably a feature; a new failure mode either way.

## Claims confirmed under adversarial testing

- **R9.5, the headline.** `H1 == H2` across all 17 node test files
  (`1d90db74…1cc08`), zero leftover temp files. At HEAD in a detached worktree,
  the same publication gate *does* rewrite `data.js`. Measured, not asserted.
- **R9.3 isolation cannot be tricked.** `--root <tmp>` alone writes inside the
  temp root; `--root` on an empty temp root raises
  `FileNotFoundError: Promoted model artifact does not exist for stingray` rather
  than falling back to the repo; `--workbook <copy>` produces a byte-identical
  registry. The only way to write inside the repo was an explicit
  `--output form-app/…`, which is documented behavior.
- **R9.4 byte-identity.** Raw field-level diff against `git show HEAD:form-app/data.js`
  is exactly one line, the `generated_at`.
- **R9.6.** Swept `scripts/`, `tests/`, `form-app/` and constructed paths
  (f-strings, `/` joins, `writeFileSync`, `shutil.move/copy`, `open(...,"w")`).
  Only `generate_registry.py` and the candidate lane's temp-root write.
  `workbook_editor_server.py` has no write path to `form-app/`.
- **`write_json_output` unaffected.** The diff is a pure extraction; behaviorally,
  regenerated contracts differ from HEAD's only by `generated_at`, and
  `test_generation_safety.py` + `test_model_config_metadata.py` give 37 passed,
  96 subtests.
- **Gate parity.** 279 pass / 3 fail across 17 files, line-for-line with the
  receipt. The three failures reproduce identically at HEAD in a clean worktree.

## Could not verify

1. The full Python suite (bounded run). Collection count and the single
   loop-contract failure were checked; the 551/1 figure was not observed directly.
2. Real power-loss durability as opposed to SIGKILL — the assessment that a
   missing directory fsync cannot truncate is reasoning from fsync-before-rename
   ordering, not an experiment.
3. A genuine cross-device `os.replace`; the staging-location weakening stayed on
   one volume.
4. Whether `run.json` and the STATE.md entry were deferred to closeout or omitted.

## Evidence inspected

The rubric and validation output; `git diff` for the three modified files and the
new test file; `scripts/corvette_form_generator/output.py`,
`scripts/generate_registry.py`, `scripts/verify_workbook_candidate.py`,
`scripts/workbook_editor_server.py`; `git show HEAD:form-app/data.js`; a detached
worktree at HEAD; five weakened shadow packages; a SIGKILL harness.

## Validation Output Inspected

`fable5loop/runs/2026-07-27-pass3-atomic-registry-write/validation-output.txt`,
re-executed rather than read: the default publish, the isolation flags, the full
node gate set with hashes, the candidate lane, and the weakened-build matrix.

## Required Fixes Before Pass

1. Preserve the destination's file mode across the replace.
2. Fsync the parent directory after the replace.
3. Cover the fsync with a test that fails when it is removed.
4. Reap temp files left by a killed write.
5. Correct the churn attribution, the X2 numbers, and the EXDEV rationale.
6. Replace the two near-vacuous tests.
7. Record the Python suite result and complete the run receipt.

All applied; post-fix evidence in `validation-output.txt`.

## Durable Lesson Candidates

1. Replacing a file by rename changes more than its bytes. `os.replace` swaps the
   inode, so mode, owner, and xattrs come from the temp file — and `tempfile`
   deliberately creates at 0600. Any switch from in-place write to atomic replace
   must carry the destination's metadata across, and needs a test for it, because
   git does not track the mode and the regression only appears on the host that
   writes.
2. A `finally` block is not crash cleanup. It covers exceptions, not SIGKILL — so
   an atomic-write helper needs a sweep for its own debris, and "zero temp files
   left" measured on the clean path proves nothing about the killed path.

## File Edit Statement

The verifier modified no tracked file permanently. Disclosed restores:
`git checkout -- form-app/data.js` after a deliberate no-arg publish;
`git checkout -- form-output/runtime/{grand-sport,z06}-runtime-contract.json`
three times after gate runs; one temporary `ATTACK-data.js` deleted; a detached
worktree created and removed (`git worktree list` confirms none remain). Final
`form-app/data.js` = `1d90db74…`, workbook = `d11674e3…`, mode restored to 0644.
