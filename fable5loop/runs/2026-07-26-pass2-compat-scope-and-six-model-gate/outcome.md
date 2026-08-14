# Outcome rubric — Pass 2 requirements 8 and 10

Written before any edit. Pass/fail is decided against this text, not against
whatever the implementation happens to produce.

Run: `2026-07-26-pass2-compat-scope-and-six-model-gate`
Spec: `docs/superpowers/specs/2026-07-23-validation-single-lane-active-surface-cleanup.md`
Scope: Pass 2 requirement 8 (Stingray compatibility export disposition) and
requirement 10 (six-model executable harness). These are the last two open Pass 2
requirements; requirement 10 explicitly gates the start of Pass 3.

## Boundaries

- The canonical workbook is not written. `stingray_master.xlsx` must be
  byte-identical at the end of the run.
- No tracked artifact under `form-output/` and no `form-app/data.js` change.
  This run adds a gate; it does not republish.
- No product/business rule is changed. No model is promoted.

## Requirement 8 — criteria

R8.1 **Consumer scan is exhaustive and recorded.** Every reader of
`form-output/stingray-form-data.json` and `.csv` in the active tree (excluding
`archive/` and `.claude/worktrees/`) is enumerated with file and line. A file
that only *writes* or asserts the writer's return value is classified as a
writer-side reference, not a consumer. The two artifacts are classified
separately — one may have a consumer while the other does not.

R8.2 **Secondary-output status is proven, not asserted.** The compatibility
export must not be reachable from source construction, runtime-contract
building, readiness gating, promotion, or registry publication. Proof is a call
path, not a reading of the module docstring.

> **Corrected 2026-07-26 during execution.** R8.1 as written assumed a text
> search over the artifact filenames would find every consumer. It does not.
> `registry_promotion.current_generation_artifact_path()` builds the path from
> `export_slug(model_key)` by f-string, so no grep for `stingray-form-data`
> reaches it. A consumer scan that only greps filenames is insufficient; it must
> also enumerate constructed paths. The corrected R8.1 requires resolving every
> promotion row's artifact path through the real resolver and reporting the
> result, which is what the receipt does.

R8.3 **Parity proof against the collapsed builder.** Regenerate Stingray from
the unchanged canonical workbook into an isolated `--output-root`, then compare
the produced compatibility artifacts to the tracked published ones:
- JSON via `scripts/compare-generated-contracts.mjs`, timestamps excluded.
- CSV byte-for-byte, no normalization.
Any non-timestamp difference must be individually explained. A blanket
allowlist fails this criterion.

R8.4 **Disposition is stated with its consequence.** The receipt says, for each
artifact, whether it is retained and why, and — if an artifact has zero
consumers — records it as an explicit Pass 4 Stage B deletion candidate rather
than silently keeping it. Deleting it inside this run is out of scope; Stage B
owns approved deletion.

## Requirement 10 — criteria

R10.1 **The model set comes from the workbook, not from a constant.** The
harness derives the active/generatable model set by reading workbook metadata
through a path independent of `discover_generation_model_configs()`, and fails
if discovery and the workbook disagree. A test that hardcodes six keys and
compares discovery to that constant does not satisfy this: it cannot tell a
workbook change from a discovery bug.

R10.2 **Every discovered model is generated through the real entrypoint** —
`scripts/generate_form.py`, the same command an operator runs — into one
isolated candidate root. Not `assemble_model_source()` called in-process.

R10.3 **Each written artifact passes the strict validator.** The harness loads
the runtime contract from disk and calls
`runtime_contract.assert_runtime_contract()` bound to that model's config. A
weaker inline check (status string, error-count scan) does not satisfy this;
requirement 10's whole purpose is that generation and the gate call the same
validator.

R10.4 **Variant counts are checked against workbook-declared expectations.**
`model_master.expected_variant_count` per model, read independently of the
generator.

R10.5 **One explicit six-model-green assertion exists** and names the count, so
a silently shrinking model set fails rather than passing vacuously.

R10.6 **Protected surfaces are hashed before and after** and asserted
unchanged, including every file under `form-output/`.

R10.7 **The harness fails for the right reason.** At least one negative proof:
the strict validation step is shown to reject a contract the weak check would
have accepted. Without this, R10.3 is unfalsified.

R10.8 The Pass 2 gate command block in the spec runs green as written,
including `tests/test_all_model_runtime_generation.py`, which currently does
not exist and therefore currently makes that block fail.

## Cross-cutting criteria

X1 **No test is shaped to the implementation.** For each new assertion: state
what workbook or source change would break it. An assertion nothing can break
is not coverage.

X2 **Full gate parity.** Python suite and the Node gates end at or above the
recorded baseline. Any pre-existing failure is named as pre-existing with
evidence that it predates this run — not merely asserted.

X3 **Independent verifier in a separate context** reviews rubric, diff, and
validation output without maker reasoning, and its evidence-backed failures are
fixed before closeout.

X4 **Honest receipt.** Every published delta is disclosed. If a claim in this
rubric turns out false during execution, the rubric section is corrected in
place with a dated note rather than quietly satisfied.

## Failure conditions

- Any workbook or tracked-artifact byte change.
- Requirement 10 harness passing while a model is missing from the set.
- Compatibility artifacts retained on the strength of an archived-doc reference.
- A parity difference accepted without a per-item explanation.
