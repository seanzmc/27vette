# Outcome rubric — Pass 3 stage 1: the composed candidate lane

Written before any edit.

Run: `2026-07-26-pass3-candidate-lane`
Spec: `docs/superpowers/specs/2026-07-23-validation-single-lane-active-surface-cleanup.md`
Scope: Pass 3 requirements 1–6 and 10–12 — `scripts/verify_workbook_candidate.py`
per §3.7, its readiness report per §3.7.1, its test per requirement 12, and the
Node-harness data-path override requirement 4 needs.

Deliberately **not** in this stage, and stated so the receipt cannot imply
otherwise: requirement 7 (restrict promotion artifact metadata, remove
`current_generation`/`draft_artifact` consumers), requirement 8 (remove
`build_registry_from_promotions()` and the fallbacks), and requirement 9
(atomic `generate_registry.py` write). Those are deletions gated on a consumer
closure record and belong in a separate stage with their own rubric.

## Boundaries

- The verifier never writes a tracked path. `stingray_master.xlsx`,
  `form-output/`, and `form-app/data.js` must be byte-identical after every run
  of it, including failing runs and runs interrupted mid-stage.
- No model is promoted. Nothing is published.
- No product or business rule changes.

## Criteria

P1 **Stage order is real and observable.** The stages run in §3.7's order
(1 copy → 2 package → 3 schema → 4 options quality → 5 discovery → 6 generate
all → 7 strict-validate all → 8 candidate registry → 9 browser harness →
10 report → 11 byte-identity assertion). The report records which stage each
result came from, and a proof exists that a failure at stage N leaves stages
N+1… unrun rather than merely unreported.

P2 **Fail-closed at the earliest applicable stage.** A workbook defect that
stages 2–4 can see must fail there, not survive to generation. Proof: inject a
defect of each shape reachable by a test and record the stage that caught it.

P3 **Changed-model scoping never reduces the generated set (§3.7.1.2/5).** With
`--changed-model z06`, the run still generates, validates, and registers every
promoted plus active/generatable model. Proof is the generated set from a run
that declares one model, compared against a run that declares none — they must
be equal.

P4 **`unexpected_drift` fails the run (§3.7.1.3).** A model outside the declared
touched set whose fresh contract differs semantically from its retained contract
is reported as `unexpected_drift` and the exit status is nonzero. Semantic
comparison ignores only generation timestamps, and the drift key must be stable
entity identity, not array position — a section reorder that changes no field is
not drift.

P5 **A global-family edit marks every model touched (§3.7.1.1).** Rows in
`GLOBAL_SHEET_FAMILIES` mark the touched set as all models. Since stage 1 does
not itself apply ChangeSets, this is proven at the level the verifier owns: the
declared-changed input accepts the all-models marking and the partition reflects
it.

P6 **The report is a stable, versioned, machine-readable file** written to a
caller-selected path, carrying a schema version and, per model: `model_key`,
`generated`, `validation_findings`, `contract_sha256`, `declared_changed`, and
`semantic_drift_vs_retained` (§3.7.1.4). The report is the interface the database
workflow consumes; nothing requires scraping console output. Proof: the test
asserts the field set, not just that a file exists.

P7 **One validator, one lane.** The verifier calls
`runtime_contract.assert_runtime_contract()` with config binding. It defines no
second acceptance check, does not re-implement generation, and does not
reimplement the stage sequence anywhere else (§3.8's standing rule).

P8 **The browser stage runs against the candidate registry, not the published
one.** Proof: with a deliberately broken candidate registry the harness stage
fails, while `form-app/data.js` on disk is untouched and still valid. A harness
that silently falls back to the tracked `data.js` fails this criterion — that is
the specific failure mode to test for, because it would make the stage pass
while proving nothing.

P9 **Byte-identity is asserted by the tool itself, not only by its test**
(§3.7.11). The verifier hashes the protected surfaces at start and re-checks at
exit, and reports a boundary violation rather than relying on the caller to
notice.

## Cross-cutting

X1 Every new assertion names the change that would break it.

X2 No test is shaped to the implementation. Specifically: each of requirement
12's five required proofs must fail against a deliberately weakened verifier,
not merely pass against the current one.

X3 Full gate parity; pre-existing failures named with evidence they predate the
run.

X4 Independent verifier in a separate context; its evidence-backed failures
fixed before closeout.

X5 Honest receipt. The deferred requirements above are restated in the receipt
as still open, and the spec's Pass 3 section is not marked complete.

## Failure conditions

- Any tracked-path write by the verifier, on any code path.
- A changed-model input that narrows generation, validation, or the registry.
- The browser stage passing by reading the published registry.
- Drift detection keyed on array position.
- Reporting Pass 3 as complete when stage 1 covers requirements 1–6 and 10–12.
