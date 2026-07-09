# Ingest Milestone 0 Safety Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

Status: In progress. Approved by Sean on 2026-07-09 through the parent production design. This milestone authorizes safety tooling, tests, and documentation only; it does not authorize any workbook write or model promotion.

**Goal:** Make every current pre-production ingest plan diagnostic-only, prove the exact temporary-workbook effects, classify all writer blockers, and close the promotion/discovery parity gap before canonical compiler work begins.

**Architecture:** `editor_ops.py` owns canonical operation preparation, finite warning policy, reference validation, raw-to-prepared coverage, and exact saved-cell readback. `WizardSessionStore` owns scoped approvals, pre-write authority, diagnostic eligibility, and immutable refusal/report behavior. The CLI and browser expose those service contracts without inventing authority. `promote_model.py` remains a separate explicit tooling path and gains membership/discovery parity, but this milestone never calls it with `--write`.

**Tech Stack:** Python 3, `openpyxl`, `pytest`/`unittest`, the existing static ingest-wizard JavaScript, and existing workbook package/schema/generator utilities. No new dependencies.

## Global Constraints

- Preserve `stingray_master.xlsx`, generated `form-output/` runtime artifacts, `form-app/data.js`, runtime JavaScript behavior, and dealer-submission boundaries.
- Do not create or hand-edit canonical workbook sheets. Do not promote a model.
- Keep `pass-c-1` and `pass-c-2` permanently non-writable. Milestone 0 may diagnose them and must return `ok=true`, `status=validated_write_blocked` when mechanical dry-run execution succeeds.
- Only future `pass-c-3` plans with both scoped approvals can be write candidates; this milestone must still refuse write approval because compiler artifacts do not exist.
- Schema-disabled execution remains available only for diagnostic fixture dry-runs. Both `editor_ops.apply_batch()` and the ingest service must refuse `write=True` when schema validation is disabled; fixture write tests must mock a successful schema gate or use a complete fixture, never a production bypass.
- `CONFIRMABLE_WARNING_KINDS` initially contains only `scaffold`. `dorder`, `refdel`, unknown kinds, and warning drift are blockers. The blanket `--confirm-plan-warnings` behavior is retired.
- Exact readback is against prepared operations after workbook coercion, while raw-operation coverage must equal the combined raw plan count.
- Keep each task small, test-first, and independently reviewable. No unrelated refactors and no new dependencies.

---

### Task 1: Register the complete reference surface and finite warning policy

**Files:**

- Modify: `scripts/corvette_form_generator/editor_ops.py`
- Modify: `tests/test_editor_ops_apply.py`
- Modify: `tests/test_editor_ops_global_families.py`
- Modify: `tests/test_editor_ops_meta.py`

- [x] Add failing tests proving option/interior union endpoints validate for direct and price rules; global option references are detected in `model_interior_scope.requires_option_id`, `default_selection_rules.target_option_id`, condition-aware `condition_id`, `color_overrides.adds_rpo`, and option-typed `asset_map.target_id`; non-option asset targets do not create false option references; interior references include `model_interior_scope`, `interior_components`, direct/price unions, and color overrides; `asset_map` and `interior_components` accept canonical operations.

- [x] Run the focused red gate and confirm the new assertions fail for missing registration/reference behavior:

  ```sh
  .venv/bin/python -m pytest tests/test_editor_ops_apply.py tests/test_editor_ops_global_families.py tests/test_editor_ops_meta.py -q
  ```

- [x] Extend `EDITOR_SHEET_META`, `GLOBAL_SHEET_FAMILIES`, and reference helpers with explicit typed/conditional rules. Resolve global references within each row's `model_key`; resolve direct/price endpoints against the target model's option-or-interior entity universe. Do not infer types from column names.

- [x] Add `CONFIRMABLE_WARNING_KINDS = {"scaffold"}` and warning classification/fingerprinting helpers. Make `refdel`, `dorder`, and unknown warning kinds unconfirmable at the writer boundary. Confirmation may contain only currently emitted, allowlisted IDs; stale or extra IDs fail closed.

- [x] Add failing then green tests proving a surviving reference emits `refdel`, same-batch delete/remap closes it, only `scaffold` can be explicitly confirmed, and `dorder`/`refdel`/unknown or stale confirmations cannot reach a write.

- [x] Add failing then green tests proving `apply_batch(write=True, run_schema_validation=False)` is refused before mutation. Adapt compact fixture write tests by mocking a successful schema validation result; do not add an unsafe production flag.

- [x] Re-run the focused gate and review the diff for model-generic behavior only.

- [x] Commit the task with message: `fix(ingest): close reference and warning gaps`.

### Task 2: Prove raw-operation coverage and exact temporary-workbook readback

**Files:**

- Modify: `scripts/corvette_form_generator/editor_ops.py`
- Modify: `tests/test_editor_ops_apply.py`
- Modify: `tests/test_editor_ops_global_families.py`

- [x] Add failing tests for coalesced update coverage, add/update field equality after Boolean/integer coercion, delete absence, exact created-sheet headers, and a deliberately tampered scratch workbook producing `readback_failed`.

- [x] Require the result contract to include `operationCoverage.rawCount`, `operationCoverage.rawCovered`, `operationCoverage.preparedCount`, and `verification.preparedChecked`; assert raw coverage equals the flattened batch count and prepared checks equal the prepared-operation count.

- [x] Run the focused red gate:

  ```sh
  .venv/bin/python -m pytest tests/test_editor_ops_apply.py tests/test_editor_ops_global_families.py tests/test_editor_ops_meta.py -q
  ```

- [x] Track the contributing raw operation indices/effects through flattening and coalescing. Reject contradictory or dropped raw effects instead of silently reporting full coverage.

- [x] After saving the temporary workbook, reopen it and verify every prepared effect: exact headers for creates, exact canonical key and every coerced planned field for add/update, and absence for deletes. Return `readback_failed` on any mismatch before a live mutation is possible.

- [x] Reuse the same verifier after a future safe live save; expose the failure state contract `apply_verification_failed` without making any current plan writable.

- [x] Re-run the focused gate and review that dry-run keeps the source workbook byte-identical.

- [x] Commit the task with message: `fix(ingest): verify exact prepared workbook effects`.

### Task 3: Scope approvals and close live-write authority before mutation

**Files:**

- Modify: `scripts/corvette_form_generator/ingest/wizard/session.py`
- Modify: `tests/test_ingest_wizard_plan.py`
- Modify: `tests/test_ingest_wizard_apply.py`

- [x] Add failing tests for `plan-approval-2` with `scope=dry_run_evidence`, run/target/plan/workbook bindings, and omission of unavailable compiler hashes. Add state coverage for new diagnostic approval while accepting historical `plan_approved` only for legacy dry-run evidence.

- [x] Add failing refusal tests proving `pass-c-1`, `pass-c-2`, legacy approvals, missing/wrong `write-approval-1`, wrong scope, disabled schema validation, stale report SHA, warning drift, unknown warnings, mixed-target ineligibility, and already-applied replay all stop before `apply_batch(write=True)`. Assert workbook bytes, dry-run report, and absence of apply report/log/backup remain unchanged.

- [x] Run the focused red gate:

  ```sh
  .venv/bin/python -m pytest tests/test_ingest_wizard_plan.py tests/test_ingest_wizard_apply.py -q
  ```

- [x] Introduce explicit approval/report schema constants: `plan-approval-2`, `write-approval-1`, and `pass-d-2`. `approve_plan()` creates diagnostic authority only. `approve_write()` derives all bindings from stored artifacts and refuses until an exact `pass-c-3` plan has a current `pass-d-2` report with `ok=true`, `status=validated_write_eligible`, and `writeEligibility.eligible=true`.

- [x] Put one pre-write authority function before the first possible live mutation. It must validate both approval scopes/schemas, plan/report/input hashes, workbook mtime/SHA and lock state, schema validation, exact warning acceptance/fingerprint, allowed deferrals, atomic target eligibility, and replay state.

- [x] Compute diagnostic blockers from the mechanically validated result before any mutation: non-writable plan/approval schema, blank option `selectable`/`active`, delete/re-add identity churn, unresolved/unconfirmable warnings/references, operation coverage/readback, and deployment-continuity blockers. A clean-but-ineligible dry-run returns `ok=true`, `status=validated_write_blocked`, structured `writeEligibility`, and `liveWriteBlockedReason`; execution failures remain `ok=false`.

- [x] Make the report's `verification` and operation counts come from `editor_ops` prepared effects. Preserve atomic multi-target semantics: one blocked target makes top-level eligibility false.

- [x] Re-run the focused gate and confirm no test invokes a live workbook write from a pre-`pass-c-3` plan.

- [x] Commit the task with message: `fix(ingest): require scoped prewrite authority`.

### Task 4: Expose diagnostic-only approval in the CLI, server, and browser

**Files:**

- Modify: `scripts/ingest_wizard_apply.py`
- Modify: `scripts/ingest_wizard_server.py`
- Modify: `visualizer/ingest-wizard/wizard.js`
- Modify: `tests/test_ingest_wizard_apply.py`
- Modify: `tests/test_ingest_wizard_server.py`
- Modify: `tests/test_ingest_wizard_ui_blockers.py`

- [x] Add failing CLI tests proving a blocked diagnostic dry-run exits zero, any blocked `--write` exits nonzero without mutation, `--no-schema-validation --write` is refused, and the obsolete blanket `--confirm-plan-warnings` flag cannot confer authority.

- [x] Add failing HTTP tests proving `/plan/approve` returns the scoped diagnostic approval and `/write/approve` returns 409 without creating `write-approval.json` for a pre-`pass-c-3` or ineligible run.

- [x] Add a static UI regression assertion that approval copy says “dry-run evidence” and never says plan approval is ready for workbook apply.

- [x] Run the focused red gate:

  ```sh
  .venv/bin/python -m pytest tests/test_ingest_wizard_apply.py tests/test_ingest_wizard_server.py tests/test_ingest_wizard_ui_blockers.py -q
  ```

- [x] Retire blanket warning confirmation in the CLI, add the write-approval endpoint, and update browser state/copy for diagnostic approval. The browser must not offer live write in Milestone 0.

- [x] Re-run the focused gate and manually inspect the rendered approval status strings for legacy and new diagnostic states.

- [x] Commit the task with message: `fix(ingest): expose diagnostic approval scope`.

### Task 5: Make promotion activation match generator discovery

**Files:**

- Modify: `scripts/promote_model.py`
- Create: `tests/test_promote_model.py`
- Modify: `README.md`

- [ ] Add failing tests proving promotion activates every exact target `(model_key, variant_id)` membership, keeps unrelated memberships unchanged, verifies both `variant_master.active` and `model_variants.active`, fails verification for incomplete discovery metadata, discovers a complete promoted fixture with the expected variants, and is idempotent.

- [ ] Run the focused red gate:

  ```sh
  .venv/bin/python -m pytest tests/test_promote_model.py tests/test_model_config_metadata.py tests/test_registry_promotion_metadata.py tests/test_schema_validation_metadata.py -q
  ```

- [ ] Extend the promotion plan/apply path to activate target membership rows. Extend on-disk verification to call `discover_generation_model_configs()` and require the target config and expected variants. Return structured discovery failure evidence; do not weaken the existing discovery contract.

- [ ] Add `tests/test_promote_model.py` to the README Python metadata gate. Do not change generator logic, workbook data, registry publication, or runtime code.

- [ ] Re-run the focused gate. Then run `scripts/promote_model.py --model zr1` without `--write` and compare the workbook SHA before/after to prove no mutation.

- [ ] Commit the task with message: `fix(promotion): activate discoverable memberships`.

### Task 6: Run the Milestone 0 safety proof and close the checkpoint

**Files:**

- Modify: `docs/ingest/canonical-row-compiler-exception-queue-design.md`
- Modify: `docs/ingest/milestone-0-safety-closure-implementation-plan.md`
- Inspect/update if needed: `README.md`
- Transient only: a fresh ignored run under `form-output/ingest-wizard/`

- [ ] Run all focused Milestone 0 suites:

  ```sh
  .venv/bin/python -m pytest \
    tests/test_editor_ops_apply.py \
    tests/test_editor_ops_global_families.py \
    tests/test_editor_ops_meta.py \
    tests/test_ingest_wizard_plan.py \
    tests/test_ingest_wizard_apply.py \
    tests/test_ingest_wizard_server.py \
    tests/test_ingest_wizard_server_pass_b.py \
    tests/test_ingest_wizard_ui_blockers.py \
    tests/test_promote_model.py \
    tests/test_model_config_metadata.py \
    tests/test_registry_promotion_metadata.py \
    tests/test_schema_validation_metadata.py -q
  ```

- [ ] Run the full Python test suite and relevant Node/static UI tests from the live README. Record every command and result; do not claim a gate without actual output.

- [ ] Create a fresh D.2-equivalent diagnostic run without mutating the historical D.2 artifacts. Approve it only as `dry_run_evidence`, execute the default CLI dry-run against `stingray_master.xlsx`, and capture workbook SHA before/after.

- [ ] Verify the fresh report has `schemaVersion=pass-d-2`, `ok=true`, `status=validated_write_blocked`, `writeEligibility.eligible=false`, explicit plan/flag/identity/reference/product blockers, exact readback counts, and byte-identical workbook fingerprints. Confirm there is no write approval, apply report, edit log, backup, generated runtime refresh, registry publication, or promotion.

- [ ] Update the parent design and this plan with completion date, exact changed surfaces, validation results, residual risks, and the next checkpoint: headless compiler plus comparator evidence index. Remove no historical evidence.

- [ ] Request a final code review, resolve only in-scope findings, rerun affected gates, and commit the checkpoint with message: `docs(ingest): close milestone zero safety proof`.

## Non-goals and Deferred Work

- Do not implement `compiler.py`, `identity.py`, `comparator.py`, `exceptions.py`, the canonical-row manifest, exception queue UI, or `pass-c-3` plan projection in this milestone.
- Do not repair current D.2 option semantics, identity churn, references, price/rule coverage, or deployment blockers; detect and report them.
- Do not authorize or exercise live workbook write, generation publication, runtime registry publication, or model promotion.
- Do not change customer runtime or dealer behavior.
