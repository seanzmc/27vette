# Stabilized Main and Model Rehabilitation — Revision 2

**Status:** COMPLETE — implemented and verified 2026-07-21. Integration transport remains intentionally unperformed pending explicit approval.

## Goal

Create one stable three-model customer publication, remove only closed recovery machinery and real transient disk clutter, land one comprehensible stabilization checkpoint, then reassess PR #8 and model rehabilitation from that new baseline.

This revision preserves the direction in `raw_Nextsteps.md` while removing duplicated generation, speculative PR implementation, unnecessary gates, and ambiguous cleanup.

## Current evidence (2026-07-21)

- Branch `ingest-wizard` matches `origin/ingest-wizard` at `8cf780d` and is `0 behind / 87 ahead` of `origin/main`.
- The worktree is not clean: `nextSteps.md` and `raw_Nextsteps.md` are untracked. This file will also be untracked until intentionally added.
- The workbook has six promoted models. The intended stable publication is Stingray, Grand Sport, and Z06; Grand Sport X, ZR1, and ZR1X remain workbook-backed and generatable.
- All six runtime-contract files exist. `form-app/data.js` currently publishes six models and defaults to Stingray.
- Workbook package validation passes.
- Workbook schema validation currently fails on two active duplicate display-order pairs:
  - `grand_sport_x_options`: `opt_cfv_001` and `opt_cfz_001` both use `sec_perf_ground_001 / display_order=20`.
  - `zr1x_options`: `opt_uqt_001` and `opt_cj2_001` both use `sec_stan_001 / display_order=10`.
- The guarded editor dry run performs schema validation. A three-boolean-only unpublication batch therefore cannot pass as currently proposed.
- The retained Grand Sport X and ZR1X runtime contracts do not currently mirror these workbook rows closely enough to use regeneration as a stabilization step. For example, the Grand Sport X contract orders CFL/CFV/CFZ differently, and the ZR1X contract places UQT in a different section. Those are rehabilitation findings, not permission for incidental contract churn here.
- `form-output/ingest-wizard/` is ignored transient output, occupies about 989 MB, contains no tracked files and no `.xlsx` source workbook, and is not preserved by Git branch history.
- PR #8 is open, draft, dirty/conflicting, and already checked out at `.worktrees/codex-workbook-relational-db`.
- The current `ingest-wizard` branch already contains the post-save rollback fix and regression in `editor_ops.py` / `test_editor_ops_apply.py`; PR #8 does not yet contain that behavior.

## Standing boundaries

Standing source-of-truth, workbook-write, generated-artifact, dealer-submission, validation, and handoff constraints from `AGENTS.md` apply. In particular:

- `stingray_master.xlsx` remains canonical for publication and display order.
- Generated runtime contracts and `form-app/data.js` are regenerated outputs, never hand-edited fixes.
- No product copy, pricing, availability, defaults, relationship behavior, dealer behavior, schema, dependency, deployment path, or public interface is changed here.
- Grand Sport X, ZR1, and ZR1X remain active workbook models with all source sheets, registrations, variants, assets, and runtime contracts retained.
- This pass does not prove those three models correct. It only restores a stable publication boundary and clears two deterministic schema collisions by preserving workbook physical-row tie order. The unpublished contracts remain byte-identical rehabilitation baselines.

## Definition of done

- The two existing display-order collisions are resolved mechanically while preserving workbook physical-row tie order:
  - `grand_sport_x_options.opt_cfz_001.display_order`: `20 -> 21`, preserving CFL 10, CFV 20, CFZ 21.
  - `zr1x_options.opt_cj2_001.display_order`: `10 -> 11`, preserving UQT 10, CJ2 11, U80 20.
- Only `model_registry_promotion.promoted_to_runtime` changes for `grand_sport_x`, `zr1`, and `zr1x`: `True -> False`.
- No other workbook value changes.
- `form-app/data.js` publishes exactly `stingray`, `grandSport`, and `z06`, with Stingray still the default.
- All three unpublished models remain registered, active/generatable, asset-backed, and represented by retained runtime contracts.
- Contract-level tests for unpublished models remain; registry-switching tests no longer require unpublished registry entries.
- Proven one-use recovery modules/tests and obsolete README commands are retired without deleting their completed historical spec or breaking current documentation pointers.
- Ignored `form-output/ingest-wizard/` clutter is removed intentionally; tracked outputs remain.
- One final stabilization acceptance gate runs on the complete candidate. No unfinished-model correctness or option-quality gate is added beyond the schema-collision proof needed for the guarded write.
- The stabilized content is prepared as one squash checkpoint. Push/merge transport requires explicit approval at execution time.
- PR #8 implementation and model rehabilitation are deferred until the stabilized main baseline exists and is re-inspected.

## Exact stabilization surfaces

### Modify

- `stingray_master.xlsx`
  - `grand_sport_x_options`: one display-order cell.
  - `zr1x_options`: one display-order cell.
  - `model_registry_promotion`: three publication booleans.
- `form-app/data.js` — regenerate from the final promotion rows and retained contracts.
- `form-output/workbook-edit-log.jsonl` — append the guarded five-operation write receipt produced by the approved writer.
- `tests/multi-model-runtime-switching.test.mjs` — assert only the three published registry models and published customer workflows.
- `tests/unpublished-runtime-contracts.test.mjs` — new direct-contract home for retained GSX/ZR1/ZR1X baseline assertions that no longer belong in registry-switching tests.
- `tests/z06-runtime-promotion.test.mjs` — update the expected publication set and registry-generator result order.
- `README.md` — describe the three unpublished but retained models and remove obsolete recovery commands.
- `docs/ingest/ingest-separation-model-integration-editor-consolidation-spec.md` — replace the stale “executable handoff” pointer with a historical-completion pointer; §8 of the 7/20 spec has no remaining promotion step.
- `nextSteps_v2.md` — close with the actual implementation receipt before final handoff.

### Delete after the caller/ownership check

- `scripts/corvette_form_generator/ingest/options_recovery_projection.py`
- `scripts/corvette_form_generator/ingest/options_recovery_changeset.py`
- `tests/test_options_recovery_projection.py`
- `tests/test_options_recovery_changeset.py`

### Preserve

- `docs/ingest/7-20_compounded-repair-spec.md` as completed historical evidence.
- `fable5loop/STATE.md`, all Fable receipts/runs, and Fable contract tests.
- Generic compiler, ChangeSet/workbook-domain service, promotion tooling, option-quality tooling, generators, and active-runtime tests.
- Every model/source/variant/asset registration and all six runtime-contract files.
- All six runtime-contract files byte-for-byte. Grand Sport X, ZR1, and ZR1X contract/source reconciliation belongs to rehabilitation, not stabilization.
- Dealer endpoint, payload, Turnstile, submission UX, deployment, and dependencies.

## Implementation sequence

### 1. Resolve repository and workbook preflight

1. Recheck branch/status, workbook package validity, Excel lock state, and current workbook mtime.
2. Decide the disposition of root `nextSteps.md` and `raw_Nextsteps.md` before any squash operation. Do not let `git add -A` decide implicitly.
3. Snapshot the five target workbook values and the two affected runtime contracts outside the repository for rollback/diff comparison.
4. Construct one complete editor batch with the exact current `workbookMtimeNs` and exactly five update items:
   - `grand_sport_x_options / opt_cfz_001 / display_order=21`;
   - `zr1x_options / opt_cj2_001 / display_order=11`;
   - three `model_registry_promotion / promoted_to_runtime=false` updates.
5. The batch contains no other field, row, or sheet change. Do not use `--allow-stale`.

The two display-order updates are mechanical schema closure, not a broader model-correctness pass: each assigns the later physical row the nearest unused integer while preserving the current tie-resolved order.

### 2. Dry-run, apply, and verify the one workbook batch

1. Run the complete batch without `--write`.
2. Require prepared-operation coverage `5/5`, zero schema errors on the candidate workbook, zero Boolean-hygiene errors, and exact readback for all five operations.
3. Stop if any unrelated workbook issue appears or any operation expands beyond the five approved cells.
4. Apply that exact reviewed batch through `scripts/apply_workbook_ops.py --write` only after implementation approval.
5. Verify the backup exists, the saved workbook reopens from disk, and all five values read back exactly.
6. Verify every preserved model, source, variant, asset, artifact path, and active flag is unchanged.
7. Run standalone workbook package validation immediately after the save.

If any post-save verification fails, require the existing guarded rollback behavior and do not continue to generation.

### 3. Regenerate only the publication registry

1. Do not regenerate any model runtime contract. Registry publication can be updated independently, while the two unpublished source/contract mismatches are deliberately deferred to rehabilitation.
2. Regenerate `form-app/data.js` from workbook promotion metadata.
3. Require all six runtime-contract files to remain byte-identical to their pre-pass snapshots.
4. Require no business-copy, price, availability, rule, default, group, asset, variant, or unpublished-contract drift.
5. Verify the registry has exactly `stingray`, `grandSport`, and `z06`, with Stingray as default, and that the three unpublished contract files still exist.

### 4. Correct tests without discarding future-model protection

1. Update registry-publication expectations in the two existing Node files.
2. Move GSX/ZR1/ZR1X-specific assertions that currently depend on registry entries into `tests/unpublished-runtime-contracts.test.mjs`, which loads the retained contract JSON directly. These assertions protect the retained baseline; they do not claim parity with the corrected workbook until rehabilitation regenerates and reviews those contracts.
3. Run the new direct-contract test once as a preservation check after the move. Do not include it in the final stabilization acceptance gate or expand its expectations during this pass.
4. Run generator-writing and registry-reading Node files sequentially, never in one concurrent `node --test` invocation.

### 5. Retire only the closed recovery surface

1. Search active code, tests, CI/workflow files, README, and current ingest docs for imports or executable references to the two recovery modules.
2. Record for each module: completed purpose, last output, replacement owner, and why the generic compiler/workbook service now owns future work.
3. Stop if an active caller exists outside the two modules, their dedicated tests, completed spec, and obsolete README command block.
4. Delete only the two modules and their dedicated tests.
5. Remove only the obsolete recovery command block from README.
6. Keep `docs/ingest/7-20_compounded-repair-spec.md`; update the current integration spec so it describes that file as completed historical evidence rather than a remaining executable handoff.
7. Treat references in `fable5loop/STATE.md` and receipts as allowed history. Do not edit them to force a grep or validator green.
8. Run one focused retained-owner smoke covering the canonical compiler, workbook-domain registry, and shared ChangeSet service. The Fable validator is not a default gate because no Fable artifact changes.

### 6. Remove actual transient disk clutter

The ignored run tree is transient evidence, not workbook/product authority. The completed tracked specs and receipts own the durable history, and the 7/20 spec records that its promotion handoff has no remaining step.

1. Confirm no ingest-wizard process is using `form-output/ingest-wizard/`.
2. Confirm the directory is ignored and contains no tracked file or `.xlsx` source workbook.
3. Delete exactly `form-output/ingest-wizard/`; do not use a wildcard against `form-output/`.
4. Do not create a path-only deletion manifest or attempt to use `origin/ingest-wizard` as an archive. Git does not contain these files.
5. Accept that historical local artifact links will no longer resolve after intentional transient cleanup; their tracked receipts, counts, hashes, and conclusions remain.
6. Verify every tracked `form-output/` file still exists and that disk cleanup creates no Git diff.

If an active continuation run or unique external input is discovered during step 1 or 2, stop and preserve only that exact item outside the ignored tree; do not retain the entire 989 MB directory by default.

### 7. Run one final stabilization acceptance gate

Run this once on the complete candidate, after generation and cleanup:

1. Workbook package validation.
2. Workbook schema validation — zero errors, including zero duplicate display-order errors.
3. Exact workbook probe for the five approved cell changes and preserved registrations/assets/contracts.
4. Registry generation/result inspection for exactly the three published models and Stingray default.
5. Sequential Node execution:
   - `tests/z06-runtime-promotion.test.mjs` first because it writes the registry;
   - `tests/multi-model-runtime-switching.test.mjs` second because it reads the registry.
6. Focused retained-owner Python smoke from Task 5.
7. Generated-diff review requiring only the approved registry publication change, byte-identical runtime contracts, and a final `git status` audit.

Do not run GSX/ZR1/ZR1X correctness, comparator, copy-quality, broad ingest, Fable, or live dealer gates as stabilization acceptance. The unpublished models remain unfinished by design.

No intermediate commit is accepted before the post-write package/schema/generated-diff checks are complete.

### 8. Prepare one squash checkpoint

1. Refresh `origin/main` and confirm the branch relationship immediately before integration.
2. Preserve `origin/ingest-wizard` as the detailed historical branch.
3. Prepare one squash commit containing only reviewed stabilization paths. Use an explicit path allowlist; never use `git add -A`.
4. Review the staged workbook, generated, test, docs, and deletion diffs. Require no unexpected file.
5. Stop before pushing or merging unless the user explicitly approves the transport. Preferred default: a squash PR/checkpoint through the repository’s accepted main-integration path; direct push to `main` is not implied by this spec.

## Deferred follow-ups — not implementation scope

### PR #8 rebaseline

After the stabilized checkpoint exists on main:

1. Work in the existing `.worktrees/codex-workbook-relational-db` checkout; do not try to switch that branch in the root worktree.
2. Merge the new main baseline without rewriting PR history.
3. Reinventory the complete remaining diff and conflicts; do not rely on the historical 216/7 test result.
4. Confirm whether the main-branch rollback fix/test resolves the PR P1 after merge.
5. Re-run current manager/backend/frontend gates and record fresh results.
6. Write a separate bounded correction spec for only the remaining duplicate-registry and importable-vs-published-model findings. Do not prescribe files or implementation until this post-merge inspection is complete.

### Model rehabilitation

After corrected PR #8 is merged, create a fresh rehabilitation branch from confirmed main. Use the retained unpublished contracts and workbook/database findings as review surfaces. Publication remains off until a later explicit promotion decision. Database findings may identify structural defects but do not decide copy, price, availability, defaults, or other business truth.

## Companion-file impact

- Workbook/data: updated in the five exact cells; all other workbook surfaces inspected-no-change.
- Generated contracts: all six inspected and required byte-identical; source/contract reconciliation for unpublished models is deferred to rehabilitation.
- Registry: regenerated to the three-model publication set.
- Runtime JS/dealer behavior: inspected-no-change; no application logic edit.
- Tests: publication expectations updated; unpublished contract assertions retained in a separate direct-contract test outside the registry path and final stabilization gate.
- Docs: README current state/obsolete commands updated; current ingest pointer corrected; completed/Fable history retained.
- Build/deployment/dependencies: not applicable.

## Stop conditions

Stop and request direction if:

- the five-operation dry run reports any additional workbook error;
- either display-order update changes workbook physical-row tie order;
- regeneration produces non-allowlisted contract drift;
- a recovery module has an active caller or unique behavior with no retained owner;
- ignored output contains an active continuation artifact or unique external input;
- branch/main divergence changes or integration conflicts affect workbook/product behavior;
- any push, deployment, or dealer change would be required.

## Handoff

Follow `AGENTS.md` handoff requirements. Report the five exact workbook cells, byte-identical runtime-contract proof, registry keys/default, retired files, deleted transient size, preserved surfaces, every command and result, skipped gates with reasons, staged squash paths, and whether merge/push was intentionally not performed.

## Implementation receipt — 2026-07-21

### Workbook and publication

- Guarded dry run: `validated`, operation coverage `5/5`, schema errors `0`, Boolean-hygiene errors `0`, exact prepared readback `5/5`.
- Guarded live write: `applied`, five operations, backup `backups/stingray_master-20260721-222936.xlsx`.
- Backup SHA-256 `aa4cb04e929b2dce3e42e02b1e09b315f6529942e58438ec30dc28e2edd16ba0` matches the complete pre-write workbook snapshot. Saved workbook SHA-256 is `514a4498648b31210e4b9e106e45c6939cf4abf935635dc38498c7610851ec30`.
- Full workbook cell comparison against the pre-write snapshot found exactly the approved five changes and no others: CFZ `20 -> 21`, CJ2 `10 -> 11`, and three `promoted_to_runtime` values `True -> False`.
- `form-app/data.js` now publishes exactly `stingray`, `grandSport`, and `z06`; Stingray remains default and all three retained registry entries are semantically identical to their pre-pass entries.
- All six runtime contracts retained their exact pre-pass SHA-256 hashes.

### Recovery retirement ownership

- `options_recovery_projection.py` completed the one-use Deliverable 4.1 projection and Checkpoint 1 review packet. Its final tracked result is recorded in `docs/ingest/7-20_compounded-repair-spec.md`; future canonical compilation belongs to the retained ingest compiler and typed exception path.
- `options_recovery_changeset.py` emitted the completed immutable ChangeSet `6c156ef7b4216d3dd85b48f7`. Future ChangeSet parsing, preview, approval, guarded apply, rollback, and receipts belong to the retained workbook-domain ChangeSet service.
- Active caller scans found no production, CI, README, or current executable-doc caller outside the retired pair and dedicated tests. References left in the completed 7/20 spec and Fable receipts are historical evidence.

### Cleanup and validation

- Deleted exactly ignored `form-output/ingest-wizard/` after confirming no active ingest process, the `.gitignore` rule, no tracked file, and no `.xlsx` source workbook. Removed size: approximately 989 MB. Every tracked `form-output/` file remains.
- Workbook package validation: valid, `0` issues.
- Workbook schema validation: valid, `0` errors and `0` warnings.
- Retained-owner Python smoke: `78 passed, 7 subtests passed`.
- Unpublished direct-contract preservation check: `2 passed`.
- Sequential Node acceptance: Z06 promotion `5 passed`; multi-model runtime switching `47 passed`.
- `git diff --check`: passed.
- Not run by design: GSX/ZR1/ZR1X correctness/comparator/copy-quality gates, broad ingest suites, Fable validator, live dealer submission, deployment. Those surfaces were either intentionally unpublished, unchanged, or outside this stabilization pass.

### Preserved and deferred

- Dealer endpoint, payload, Turnstile behavior, submission UX, runtime application code, dependencies, deployment path, model/source/variant/asset registrations, and all runtime contracts remain unchanged.
- Root `nextSteps.md` and `raw_Nextsteps.md` remain untracked historical inputs and are excluded from the stabilization checkpoint. This completed file is the tracked owner plan.
- PR #8 rebaseline and unpublished-model rehabilitation remain deferred until this checkpoint reaches `main` through an explicitly approved transport.
