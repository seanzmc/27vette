# Outcome rubric — Pass 4 Stage B exact retirement

Run: `2026-07-29-pass4b-exact-retirement`

Source commit: `2bb1e76` (`Harden Pass 4 Stage A verification`)

Spec: `docs/superpowers/specs/2026-07-23-validation-single-lane-active-surface-cleanup.md`, Stage B

## Definition of done

C1. `git rm` deletes exactly the six approved Stage B candidates and no other file:

- `form-output/stingray-form-data.json`
- `form-output/stingray-form-data.csv`
- `scripts/corvette_form_generator/production.py`
- `scripts/seat-canonicalization-diff.mjs`
- `tests/seat-canonicalization-diff.test.mjs`
- `tests/unpublished-runtime-contracts.test.mjs`

C2. Current README and route-map guidance no longer describes the removed files or tests as candidates, retained outputs, or executable routes. Historical specs, plans, receipts, and archives remain intact.

C3. A post-deletion scan finds no retired artifact names, exporter symbols, or stale test filenames in active `scripts/`, `tests/`, README, or `docs/route-map.md`.

C4. The canonical all-model generation/metadata gate, package/schema gates, all remaining Node gates, and the full candidate-promotion lane pass from the post-deletion tree.

C5. Default gates leave tracked `form-output/` and `form-app/` files byte-identical. The deleted compatibility outputs are the only generated-file removals.

C6. Workbook data, retained runtime contracts, registry publication, browser runtime, dealer submission, schemas, dependencies, and public interfaces remain unchanged.

C7. An independent verifier confirms the exact deletion boundary, zero active references, migrated assertion ownership, current guidance, validation evidence, and protected surfaces.

C8. The owning specification, Fable receipt, and `STATE.md` record Stage B completion without beginning Stage C.

## Validation plan

- Pre/post tracked-file and stale-reference inventories.
- Workbook package and schema validation.
- Python metadata/route/all-model gate.
- Every remaining `tests/*.test.mjs` file serially with protected retained-artifact hashes before/after.
- Full `tests/test_verify_workbook_candidate.py` candidate lane.
- Focused Fable loop validator and contract tests.
- `git diff --check`, exact deletion list comparison, and protected-surface diff review.

## Rollback

Ordinary Git restoration from source commit `2bb1e76`. No workbook write or publication is authorized.
