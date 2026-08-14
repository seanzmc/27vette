# Outcome rubric — Pass 3 requirements 7 and 8

Written before any edit.

Run: `2026-07-27-pass3-promotion-type-closure`
Spec: `docs/superpowers/specs/2026-07-23-validation-single-lane-active-surface-cleanup.md`
Scope: Pass 3 requirement 7 (record the consumer closure, then restrict promotion
artifact metadata to `runtime_contract` and remove the `current_generation` /
`draft_artifact` acceptance and production consumers) and requirement 8 (remove
`build_registry_from_promotions()` and the old artifact-resolution fallbacks).

These are deletions. The spec gates them on a recorded closure, and requirement 7
says explicitly: **if external compatibility remains, stop for a separate
decision rather than silently preserving the fallback as release authority.**

## Boundaries

- No workbook write. `stingray_master.xlsx` SHA-256 identical at start and end.
- Nothing published. `form-app/data.js` and `form-output/` byte-identical.
- No product or business rule changes. No model promoted.

## Criteria

C1 **The closure is recorded before the deletion, and it is exhaustive.** Every
consumer of `artifact_type in {current_generation, draft_artifact}` and of
`build_registry_from_promotions()` is enumerated with file and line, classified as
fixture / active-code / active-doc / external-operator. Constructed references
count: a filename-only grep is insufficient here, as this codebase has already
proven once.

C2 **The external/operator question is answered explicitly, not skipped.** The
receipt states whether any operator instruction, README, runbook, or UI offers
these artifact types, and cites what was searched. If any remain, the run stops
and says so.

C3 **`runtime_contract` becomes the only accepted promotion artifact type**, in
one place. `REGISTRY_PROMOTION_ARTIFACT_TYPES` is the shared authority; schema
validation, promotion parsing, and the editor must all narrow from it rather than
each carrying their own list.

C4 **The blank-`artifact_type` default no longer resolves to a retired value.**
Today a blank cell means `draft_artifact`. After this it must mean
`runtime_contract` or fail — whichever, stated and tested.

C5 **`artifact_path` becomes unconditionally required** for a promoted row. The
`!= "current_generation"` escape disappears, in both `registry_promotion.py` and
`schema_validation.py`.

C6 **The dead functions are gone**, not merely unreferenced:
`current_generation_artifact_path()`, `promotion_requires_runtime_contract_assertion()`
(already zero-caller), `load_promotion_data()`, and
`build_registry_from_promotions()`. `artifact_path_for_promotion()` survives only
if it retains a real caller and no longer branches.

C7 **Deleting the tests does not delete the guarantees.** For each removed test in
`tests/test_registry_promotion_metadata.py`, state what it guarded and where that
guard now lives. A *passing* assertion removed with its fixture is the dangerous
case. Ordering, default-model, setup-copy, and duplicate-key behavior must remain
covered against strict runtime contracts.

C8 **A workbook that names a retired artifact type is rejected, not ignored.**
Proof by construction: a fixture workbook with `artifact_type=current_generation`
must fail promotion loading and schema validation with a message naming the
allowed set.

C9 **The registry still publishes identically.** The default no-arg
`generate_registry.py` produces the same bytes as before, modulo `generated_at`,
and the candidate lane's stage 8 still builds its registry.

## Cross-cutting

X1 Every new assertion names the change that would break it.

X2 No test shaped to the implementation: the negative proofs in C8 must fail
against the pre-change code, demonstrated rather than assumed.

X3 Full gate parity; pre-existing failures named with evidence they predate this
run.

X4 Independent verifier in a separate context; evidence-backed failures fixed
before closeout.

X5 Honest receipt. If requirements 7 and 8 complete Pass 3, say so and say what
Pass 3 leaves for Pass 4. If anything is deferred, name it.

## Failure conditions

- Deleting a consumer that turns out to have a live caller.
- Removing a passing assertion without stating where the guarantee moved.
- Narrowing the artifact-type vocabulary in one module but not the others.
- Any workbook or published-artifact byte change.
- Proceeding past an unresolved external/operator consumer instead of stopping.
