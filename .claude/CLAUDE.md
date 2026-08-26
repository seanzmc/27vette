# 27vette Claude Project Context

Before non-trivial work, read:

1. `AGENTS.md`
2. `fable5loop/STATE.md` — start with the `Current handoff` block
3. Task-relevant repo files

`AGENTS.md` is the source of truth for workflow, spec, workbook, generated-artifact,
runtime, styling, and dealer-submission boundaries; do not duplicate it here.

After every substantive repository task, overwrite the `Current handoff` block in
`fable5loop/STATE.md`, then run `.venv/bin/python scripts/validate_state_handoff.py`
if that file changed. Retired detail belongs in `fable5loop/STATE-archive.md`;
the retired Fable 5 loop scaffold is archived under `docs/archive/fable5-loop/`.
