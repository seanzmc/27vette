# Checkpoint 2 measured evidence — fast layered validation suite

Evidence file for `docs/superpowers/specs/2026-08-17-fast-layered-validation-suite.md` §9,
Checkpoint 2. Raw tool output from the closing acceptance run, captured 2026-08-17.
The durable, queryable form of these numbers is `tests/validation_catalog.json`;
this file is the transcript behind it.

Environment: darwin 25.6.0 arm64; node v26.7.0; python 3.14.7 (`.venv`).
Method: one process per gate, run serially — the same method as the Checkpoint 0
baseline and the Checkpoint 1 evidence, so all three are comparable.

Timing precision differs from the Checkpoint 1 file: this run measured whole
wall seconds per gate rather than centiseconds. Gate seconds below are therefore
`±1 s`, and the lane totals are the sum of those integers, not a separately
timed figure. Node's own `duration_ms` is exact where a comparison needs it.

## 1. Node lane, all 18 files, closing run

Sixteen files at Checkpoint 1 plus the two parity owners this checkpoint adds.

```text
GATE tests/grand-sport-contract-preview.test.mjs        exit=0 seconds=3  | tests   6 pass   6 fail 0
GATE tests/grand-sport-runtime-contract.test.mjs        exit=0 seconds=2  | tests  19 pass  19 fail 0
GATE tests/multi-model-runtime-switching.test.mjs       exit=0 seconds=4  | tests  70 pass  70 fail 0
GATE tests/nonruntime-option-source-purge.test.mjs      exit=0 seconds=1  | tests   5 pass   5 fail 0
GATE tests/source-to-contract-parity.test.mjs           exit=0 seconds=1  | tests 102 pass 102 fail 0
GATE tests/source-to-registry-parity.test.mjs           exit=0 seconds=2  | tests  29 pass  29 fail 0
GATE tests/stingray-form-regression.test.mjs            exit=0 seconds=4  | tests  91 pass  91 fail 0
GATE tests/stingray-runtime-contract.test.mjs           exit=0 seconds=18 | tests  12 pass  12 fail 0
GATE tests/tracked-artifacts-guard.test.mjs             exit=0 seconds=1  | tests   7 pass   7 fail 0
GATE tests/workbook-schema-standardization.test.mjs     exit=0 seconds=1  | tests  12 pass  12 fail 0
GATE tests/workbook-visual-copy-standardization.test.mjs exit=0 seconds=1 | tests   9 pass   9 fail 0
GATE tests/z06-contract-preview.test.mjs                exit=0 seconds=1  | tests   2 pass   2 fail 0
GATE tests/z06-interior-accessory-cleanup.test.mjs      exit=0 seconds=2  | tests   7 pass   7 fail 0
GATE tests/z06-performance-package-interactions.test.mjs exit=0 seconds=6 | tests  21 pass  21 fail 0
GATE tests/z06-published-runtime.test.mjs               exit=0 seconds=1  | tests   4 pass   4 fail 0
GATE tests/z06-registry-publication.test.mjs            exit=0 seconds=3  | tests   2 pass   2 fail 0
GATE tests/z06-runtime-contract.test.mjs                exit=0 seconds=2  | tests  24 pass  24 fail 0
GATE tests/z06-runtime-rule-corrections.test.mjs        exit=0 seconds=6  | tests  15 pass  15 fail 0
TOTAL 59   | tests 437 pass 437 fail 0
```

Three-point comparison of the whole Node inventory:

| Point | Files | Tests | Failures | Seconds |
|---|---|---|---|---|
| Checkpoint 0 baseline | 16 | 305 | 6, in 5 files | 111.75 |
| Checkpoint 1 | 16 | 305 | 1, `grand-sport-contract-preview` | 55.44 |
| Checkpoint 2 (this run) | 18 | 437 | 0 | 59 |

`grand-sport-contract-preview` is green for the first time since the audit: its
recorded stale `requires: 25` hot-spot literal, the last one Checkpoint 1
deferred, is gone with the other eight aggregate counts in that file. The lane
carries 132 more assertions than Checkpoint 1 for about 4 more seconds, because
both new owners are pure comparison over one already-built snapshot.

## 2. Python lanes, closing run

```text
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
  exit=0 seconds=64

metadata gate (10 files, one process)
  189 passed, 111 subtests passed in 182.71s     exit=0

.venv/bin/python -m pytest tests/test_workbook_truth.py -q
  58 passed in 7.96s                             exit=0

.venv/bin/python -m pytest tests/test_validation_catalog.py -q
  19 passed in 0.04s                             exit=0

.venv/bin/python -m pytest tests/test_verify_workbook_candidate.py -q
  16 passed in 685.88s (0:11:25)                 exit=0

.venv/bin/python scripts/validate_fable5_loop.py
  Fable 5 loop validation passed: 3 tiers, 4 layers, required artifacts,
  Claude setup, memory, skill, routine, outcomes, and eval rubric are present.
                                                 exit=0
```

`test_verify_workbook_candidate.py` is the composed candidate lane and is the
one gate this checkpoint made longer: it now runs twelve stages instead of ten,
building the snapshot from the candidate workbook and running both parity owners
against the candidate contracts and candidate registry. All sixteen tests pass,
including the three that each drive a complete six-model candidate end to end.

## 3. Protected surfaces

```text
git status --porcelain -- form-output form-app
  (no output)

git status --short
   M README.md
   M docs/superpowers/specs/2026-08-17-fast-layered-validation-suite.md
   M scripts/verify_workbook_candidate.py
   M tests/validation_catalog.json

git diff --check
  (clean, working tree and d7786f6..HEAD)
```

Tracked generated artifacts are byte-identical after a lane that generated six
models several times. The canonical workbook was read only; every mutation
canary recorded in the §9 Checkpoint 2 result block ran against copies inside a
disposable `git worktree`.

## 4. What this run does and does not establish

Established: every gate in the closing inventory passes on this machine, at
these versions, run serially, with protected surfaces unchanged.

Not established here:

- Node 22 / Python 3.12 CI reference timings. Still uncaptured, carried from
  Checkpoint 0.
- The thirteen injected-mismatch canaries. They were run by the implementing
  session and are described in the §9 Checkpoint 2 result block; this closing
  run re-established the green baseline, not the canaries.
- Any independent verifier judgment. Checkpoint 2, like Checkpoints 0 and 1, was
  direct specification execution rather than a Fable loop run, so review comes
  from the pull request rather than from a separate verifier context.
