# Outcome rubric — Pass 3 requirement 9: atomic registry write

Written before any edit.

Run: `2026-07-27-pass3-atomic-registry-write`
Spec: `docs/superpowers/specs/2026-07-23-validation-single-lane-active-surface-cleanup.md`
Scope: Pass 3 requirement 9 only — "`generate_registry.py` remains the only real
`form-app/data.js` writer and operates only after separately approved
promotion/artifact changes. Its write becomes atomic."

Requirements 7 and 8 remain open and are not touched here.

## Boundaries

- No workbook write. `stingray_master.xlsx` SHA-256 identical at start and end.
- No republication as a side effect. `form-app/data.js` may only change if this
  run deliberately republishes it, and the receipt must say so explicitly. The
  intent is that it does **not** change.
- No product or business rule changes. No model promoted.

## Criteria

R9.1 **The write is genuinely atomic.** `write_app_data_registry()` writes to a
temporary file in the destination directory, fsyncs, and `os.replace()`s into
place. Proof is not "the code calls os.replace" — it is a test that injects a
failure *after* the temp file is written and *before* the replace, and shows the
destination is byte-identical to its previous contents, with no partial file and
no leftover temp file.

R9.2 **A crash mid-write cannot leave a truncated registry.** The specific
hazard: `form-app/data.js` is a ~2MB file the browser loads unconditionally. A
half-written one is worse than a stale one. Prove the destination is never
observed in a partial state.

R9.3 **`generate_registry.py` can publish into an isolated root.** It accepts an
explicit workbook and output location so a caller can build a registry without
touching the tracked tree. Default behavior with no arguments is unchanged.

R9.4 **The default path is byte-identical to before.** Running the command with
no arguments produces exactly the bytes it produced before this change, modulo
`generated_at`. Proof by comparison against the committed `form-app/data.js`,
not by inspection.

R9.5 **The gate churn this enables is actually removed.** `tests/z06-registry-publication.test.mjs`
runs `generate_registry.py`; after this change, running that gate must leave
`form-app/data.js` byte-identical. Proof: hash before, run the gate, hash after.
This is the practical payoff and the reason requirement 9 was sequenced first.

R9.6 **`generate_registry.py` is still the only real writer.** A scan proves no
other active-tree code path writes `form-app/data.js`. If one exists, it is
named, not silently tolerated.

R9.7 **Nothing else regresses.** The candidate lane's stage 8 already builds a
registry into a temporary root via `write_app_data_registry`; it must keep
working, and its byte-identity boundary check must still pass.

## Cross-cutting

X1 Every new assertion names the change that would break it.

X2 No test shaped to the implementation: the atomicity test must fail against a
non-atomic `write_text` implementation. Demonstrate that, do not assume it.

X3 Full gate parity; pre-existing failures named with evidence they predate this
run.

X4 Independent verifier in a separate context; evidence-backed failures fixed
before closeout.

X5 Honest receipt. Requirements 7 and 8 restated as open; Pass 3 not marked
complete.

## Failure conditions

- Any workbook byte change.
- `form-app/data.js` changing without the receipt saying so and why.
- An atomicity test that passes against a plain `write_text`.
- Claiming the churn is fixed without a before/after hash across a real gate run.
