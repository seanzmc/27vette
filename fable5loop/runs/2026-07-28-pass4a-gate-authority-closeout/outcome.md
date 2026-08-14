# Outcome rubric — Pass 4 Stage A gate-authority closeout

Run: `2026-07-28-pass4a-gate-authority-closeout`
Spec: `docs/superpowers/specs/2026-07-23-validation-single-lane-active-surface-cleanup.md`, Pass 4 Stage A

The bounded definition of done was stated in the session before the remaining edits: finish Stage A without changing the workbook, generated contracts, published registry, runtime behavior, or dealer flow; preserve current behavior; prove each retained gate has a current source/runtime root; update the command matrix and route map; prepare but do not execute the Stage B deletion list.

## Boundaries

- No canonical workbook write in this slice. The preceding `6a6a425` schema slice already owns and verifies its workbook correction.
- No tracked generated runtime contract or published registry write.
- No runtime JavaScript, CSS, dealer endpoint, payload, Turnstile, or submission UX change.
- `form-app/index.html` contains a concurrent unrelated favicon edit and is excluded from this run.
- No Stage B deletion is authorized or performed.

## Criteria

C1. **Stingray authority is current.** `stingray-generator-stability` is replaced by `stingray-runtime-contract`; it generates through `generate_form.py` into a temporary root, consumes the strict runtime contract, checks protected-artifact identity, retains package/workbook/source-to-output invariants, and no longer reads the compatibility JSON, compares it with the published registry, pins broad retained-artifact counts, or asserts on Python source strings.

C2. **Grand Sport and Z06 runtime guarantees use strict contracts.** The former `grand-sport-draft-data` and `z06-form-data-draft` gates become runtime-contract gates that generate into isolated roots without `--emit-inspection`. Draft-only provenance/status assertions are removed or remain in optional preview diagnostics; runtime assertions are not owned by preview artifacts.

C3. **Preview tests are optional diagnostics only.** `grand-sport-contract-preview` and `z06-contract-preview` retain raw-source/provenance evidence; duplicated section/wheel runtime assertions are removed. README labels them non-readiness diagnostics.

C4. **Z06 publication boundaries are explicit.** The read-only promoted runtime gate is named `z06-published-runtime`; `z06-registry-publication` remains the separate isolated publication gate. Neither writes tracked `form-app/data.js`.

C5. **Z06 interior cleanup uses current runtime data.** It generates and reads `form-output/runtime/z06-runtime-contract.json` below a temporary root and does not request or read draft artifacts.

C6. **Editor reminders name the current lane.** `editor_ops.gate_reminders()` no longer emits preview/draft test commands; it returns package/schema checks, affected-model generation, registry generation, and the composed candidate verifier with changed-model reporting. Tests pin that route and reject stale preview/draft reminders.

C7. **README and route map describe one authority per gate.** README classifies all 18 Node files as default readiness, optional diagnostics, or the Stage B retirement candidate; the Python metadata command contains both `test_model_generation_route.py` and `test_all_model_runtime_generation.py`; `docs/route-map.md` reflects runtime-contract-only promotion, optional inspection, atomic isolated registry publication, and the compatibility artifacts' zero-reader status.

C8. **Active current guidance uses new gate names.** README, route map, scripts, and tests contain no stale executable command using the four retired gate filenames. Historical and superseded specs/plans, archived material, receipts, STATE chronology, and Stage C plan-classification surfaces are not rewritten to erase history.

C9. **Stage B list is exact and unexecuted.** Proposed `git rm` list for separate approval:

- `form-output/stingray-form-data.json`
- `form-output/stingray-form-data.csv`
- `scripts/corvette_form_generator/production.py`
- `scripts/seat-canonicalization-diff.mjs`
- `tests/seat-canonicalization-diff.test.mjs`
- `tests/unpublished-runtime-contracts.test.mjs`

Stage A removed the compatibility exporter import/result/writer from `model_generation.py`, the `source_assembly` compatibility marker, and every active test dependency; README and route-map now state that the retained files have no producer or reader. Stage B therefore deletes only the exact six files above and removes their candidate wording from active guidance. Real promotion-path enumeration must continue to resolve only the three promoted runtime contracts.

Explicitly retained: all six runtime contracts, all six derived-swap manifests, the two optional preview tests, `window.STINGRAY_FORM_DATA`, `scripts/compare-generated-contracts.mjs`, `scripts/compare_workbook_bool_hygiene.py`, and every protected operator/write tool named in the spec.

C10. **Exit gates are real and no-churn.** All 18 Node files pass serially and tracked `form-output/` + `form-app/` hashes match before/after; package and schema gates report zero issues; the README Python metadata gate and editor apply suite pass; candidate-lane tests complete; loop validation passes; `git diff --check` passes. Every omission or timeout is reported rather than inferred.

## Skill update decision

Deferred. The useful procedural lesson is to fingerprint mixed staged/unstaged work with `git diff HEAD`, not worktree-only `git diff`. The profile's existing 27vette Fable skill is curator-protected in this environment, so this run records the lesson in `STATE.md` and the verifier report rather than claiming a skill edit.
