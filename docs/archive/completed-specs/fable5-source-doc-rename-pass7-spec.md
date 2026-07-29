# Fable5 Source Doc Rename Spec (Simplification Pass 7)

Date: 2026-07-05
Status: Completed 2026-07-05. See completion record at end.

## Diagnosis

`fable5loop/Most people are using Claude Fable 5 like Sonnet 4.6 with a bigger….md` contains a unicode ellipsis; git quotes it (`\342\200\246`) in porcelain output, and the long prose filename is awkward to reference in tooling and docs. Verified in the simplification audit (verifier claim 8, PASS).

Current references (git grep 'Most people are using'):

- `fable5loop/fable5-loop-contract.json:4` — `sourceDocument` field; `scripts/validate_fable5_loop.py:350-352` requires that path to exist.
- `fable5loop/README.md` (line 3 prose reference).
- `fable5loop/STATE.md` (Verified facts bullet + two General rules Evidence refs).
- `docs/fable5-compounding-loop-spec.md`, `docs/fable5-compounding-loop-hardening-spec.md` (active loop docs).
- `fable5loop/runs/2026-07-05-simplification-audit/verifier-report.md` — historical receipt; not rewritten.

## Exact changes

1. `git mv "fable5loop/Most people are using Claude Fable 5 like Sonnet 4.6 with a bigger….md" fable5loop/source-guidance.md`
2. Update path references in: `fable5loop/fable5-loop-contract.json` (`sourceDocument`), `fable5loop/README.md`, `fable5loop/STATE.md`, `docs/fable5-compounding-loop-spec.md`, `docs/fable5-compounding-loop-hardening-spec.md`.
3. Historical run receipts keep old-name mentions (receipts are immutable evidence).

## Constraints / non-goals

No content edits inside the source doc itself. No other renames. Pass 7 only.

## Validation plan

1. `git grep -l 'Most people are using' -- ':!fable5loop/runs'` → no matches (receipts only).
2. `test -f fable5loop/source-guidance.md`.
3. `scripts/validate_fable5_loop.py` (main-repo venv) → pass (validator enforces contract `sourceDocument` existence).
4. `git diff --check`.
5. Independent verifier; receipt + STATE at closeout.

## Completion record

Implemented 2026-07-05 (staged, not committed). `git mv` rename to `fable5loop/source-guidance.md`; all five active reference surfaces updated (contract `sourceDocument`, `fable5loop/README.md`, `fable5loop/STATE.md`, both loop spec docs); historical receipts untouched by design.

Validation results (real output):

- `git grep 'Most people are using'` excluding receipts → only the renamed doc's own first line.
- `test -f fable5loop/source-guidance.md` → present; staged as R (history preserved).
- Loop gate: "Fable 5 loop validation passed" (validator enforces contract `sourceDocument` existence).
- `git diff --check`: clean.
- Independent verifier: PASS (criteria 6-8; report at `fable5loop/runs/2026-07-05-tidy-pass4-pass7/verifier-report.md`).

Residual risks / follow-up: staged pending commit approval; none other implied.
