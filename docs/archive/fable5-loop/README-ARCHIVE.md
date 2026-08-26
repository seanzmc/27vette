# Retired: Fable 5 compounding loop

The Fable 5 compounding loop is retired as of 2026-08-26. It is not a current
workflow and must not be resumed without a new approved design.

What moved here:

- `README.md` — the former loop entrypoint.
- `source-guidance.md` and `Attachments/` — the imported source article.
- `fable5-loop-contract.json`, `evals/`, `outcomes/`, `routines/`, `skills/` — loop scaffold.
- `fable5-compounding-loop-spec.md`, `fable5-compounding-loop-hardening-spec.md`, `fable-ex-tasks.md` — completed specs and routing guidance.

What stayed put:

- `fable5loop/runs/` — immutable run receipts, kept in place because prior specs,
  receipts, and archived documents link those exact paths. Historical evidence only.
- `fable5loop/STATE.md` — retained and now the repo's general operational handoff,
  validated by `scripts/validate_state_handoff.py`. Its retired detail is in
  `fable5loop/STATE-archive.md`.

The former `scripts/validate_fable5_loop.py` and `tests/test_fable5_loop_contract.py`
were replaced by `scripts/validate_state_handoff.py` and `tests/test_state_handoff.py`.
