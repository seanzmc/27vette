# Fable 5 Run Receipts

Every non-trivial Fable 5 run in this repo must leave a receipt folder here before closeout.

Required shape:

```text
fable5loop/runs/YYYY-MM-DD-slug/
  outcome.md
  verifier-report.md
  validation-output.txt
  run.json
```

The receipt proves the run used an outcome rubric, independent verifier, real validation output, timestamped state updates, and an explicit skill-update decision. `scripts/validate_fable5_loop.py` rejects incomplete receipts.

Rules:

- Use one folder per run.
- Keep paths in `run.json` repo-relative.
- Record validator/test command output in `validation-output.txt`.
- Record verifier judgment in `verifier-report.md`; the verifier must not edit files.
- Record every `STATE.md` update and skill-update decision in `run.json`.
- If no skill update is warranted, set `skill_update.decision` to `not_applicable` and point `skill_update.evidence` to the verifier report or outcome note explaining why.
