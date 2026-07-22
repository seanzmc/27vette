# Stabilized Main and Model Rehabilitation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore a stable three-model customer form, retire only proven one-use recovery code, reclaim actual transient disk usage, land the current branch on `main` as one comprehensible checkpoint, correct PR #8, and start model rehabilitation from that cleaner baseline.

**Architecture:** Publication remains workbook-owned. GSX, ZR1, and ZR1X stay fully represented in the workbook and retain their assets and runtime contracts, but only `model_registry_promotion.promoted_to_runtime` is turned off so `form-app/data.js` publishes Stingray, Grand Sport, and Z06. The relational database remains a workbook-congruent review and integrity surface; it does not become the authority for copy, pricing, UQT behavior, defaults, or other business decisions.

**Tech Stack:** `stingray_master.xlsx`, Python/openpyxl, workbook-domain/editor write safety, static JavaScript registry, Node test runner, SQLite/FastAPI/React workbook manager, Git/GitHub.

## Global Constraints

- Keep every GSX, ZR1, and ZR1X workbook sheet, source row, model/variant registration, asset row, and generated runtime contract.
- Unpublish only by changing the three `model_registry_promotion.promoted_to_runtime` values from `True` to `False`; do not deactivate `model_master`, `model_variants`, `variant_master`, `model_workbook_sources`, assets, or artifact metadata.
- `stingray_master.xlsx` remains the product/business source of truth.
- Do not hand-edit `form-app/data.js`; regenerate it with `scripts/generate_registry.py`.
- Do not delete the generic compiler, workbook-domain service, promotion tooling, option-quality tooling, or tests that protect active runtime contracts.
- Do not delete or rewrite Fable receipts, `fable5loop/STATE.md`, or Fable contract tests as part of recovery retirement.
- Keep cleanup for cognitive clarity separate from cleanup for disk recovery.
- Run only the main-safety gate defined in Task 4. Do not run GSX/ZR1/ZR1X correctness or option-quality gates as a condition of the stabilization checkpoint.
- Dealer endpoint, payload, model scoping, Turnstile behavior, submission UX, deployment paths, dependencies, and generated contract schemas are out of scope.
- Any workbook write must use the existing guarded writer, create a verified backup, reopen successfully from disk, and restore the backup if post-save verification fails.
- Stop rather than invent product copy, pricing, UQT behavior, availability, defaults, or relationship decisions.

---

## Current Evidence Snapshot (2026-07-21)

- The `ingest-wizard` checkout is clean and matches `origin/ingest-wizard` at `8cf780d`.
- The live comparison is currently `0 behind / 87 ahead` of `origin/main`; the earlier figure of 86 is stale and must be recomputed immediately before the squash.
- The canonical workbook currently publishes six models. GSX, ZR1, and ZR1X each have `model_registry_promotion.promoted_to_runtime=True`.
- The three unfinished models also have active model/source/variant registrations. Those registrations are retained so generation, database import, and later rehabilitation remain possible.
- `form-output/` is about 1.0 GB: approximately 989 MB is ignored `form-output/ingest-wizard/` run output, while all tracked `form-output/` files total about 11 MB.
- Tests occupy about 5.4 MB. Deleting recovery tests or specs is therefore a clarity decision, not a storage strategy.
- PR #8 is open as a draft from `codex/workbook-relational-db` into `main` and currently reports `DIRTY` because its base has moved.
- The PR #8 merge simulation against the expanded workbook produced 216 passing manager tests and seven stale inventory failures; the compiler accepted the 77-sheet/9,091-row workbook without structural errors.
- PR #8 has one current P1 at `scripts/corvette_form_generator/editor_ops.py`: failed post-save verification returns a backup path but leaves the unverified workbook live.

## Definition of Done

- The canonical workbook has exactly three published models: `stingray`, `grand_sport`, and `z06`.
- `form-app/data.js` contains registry keys `stingray`, `grandSport`, and `z06`, defaults to Stingray, and contains none of `grand_sport_x`, `zr1`, or `zr1x`.
- GSX/ZR1/ZR1X workbook data, assets, source registrations, variants, and runtime-contract files remain present.
- Proven one-use recovery code, its dedicated tests, the 7/20 compounded-repair spec, and its README commands are gone only after the caller/contract audit passes.
- Generic compiler, workbook-domain, promotion, registry, option-quality, Fable, and active-runtime protections remain.
- Ignored ingest-wizard run clutter is removed only after an explicit retention audit; tracked generated artifacts are not removed.
- The stabilized tree passes the one main-safety gate in Task 4 and lands on `main` as one squash commit.
- `origin/ingest-wizard` remains available as the historical branch archive.
- PR #8 is updated from the new main baseline, its P1 is fixed, schema semantics come from `workbook_domain.registry`, and inactive registered models import/validate without publication.
- A fresh `codex/model-rehabilitation` branch starts from main after corrected PR #8 is merged.

## Planned File and Data Ownership

**Modify during stabilization**

- `stingray_master.xlsx` — change only three publication booleans in `model_registry_promotion`.
- `form-app/data.js` — regenerated three-model registry.
- `tests/multi-model-runtime-switching.test.mjs` — assert the stable three-model registry and retained inactive contracts.
- `tests/z06-runtime-promotion.test.mjs` — update registry-generation expectations to the stable three-model publication set.
- `README.md` — describe GSX/ZR1/ZR1X as retained but unpublished; remove obsolete recovery commands.

**Delete only after the Task 2 proof passes**

- `scripts/corvette_form_generator/ingest/options_recovery_projection.py`
- `scripts/corvette_form_generator/ingest/options_recovery_changeset.py`
- `tests/test_options_recovery_projection.py`
- `tests/test_options_recovery_changeset.py`
- `docs/ingest/7-20_compounded-repair-spec.md`

**Explicitly preserve**

- `scripts/corvette_form_generator/ingest/wizard/compiler.py`
- `scripts/corvette_form_generator/ingest/wizard/copy_split.py`
- `scripts/corvette_form_generator/ingest/wizard/plan_builder.py`
- `scripts/corvette_form_generator/options_sheet_quality.py`
- `tests/fixtures/options-sheet-quality-allowlist.json`
- `scripts/corvette_form_generator/workbook_domain/`
- `scripts/promote_model.py`, `scripts/generate_form.py`, and `scripts/generate_registry.py`
- `docs/ingest/options-sheet-quality-remediation-spec.md`
- All `fable5loop/runs/`, Fable receipts/state, and `tests/test_fable5_loop_contract.py`
- All six `form-output/runtime/*-runtime-contract.json` files currently present.

---

### Task 1: Unpublish the Three Unfinished Models Without Removing Their Data

**Files and data:**

- Modify: `tests/multi-model-runtime-switching.test.mjs`
- Modify: `tests/z06-runtime-promotion.test.mjs`
- Modify: `stingray_master.xlsx` sheet `model_registry_promotion`
- Regenerate: `form-app/data.js`
- Inspect-no-change: all GSX/ZR1/ZR1X source sheets, `model_master`, `model_variants`, `variant_master`, `model_workbook_sources`, `asset_map`, and their three runtime contracts

**Interface:**

- Consumes: workbook-owned promotion rows loaded by `load_registry_promotions()`.
- Produces: a three-model runtime registry while leaving the unpublished models available to generators and database importers.

- [ ] **Step 1: Add the failing publication-boundary expectations**

  Change the expected registry keys in both Node tests to:

  ```js
  ["grandSport", "stingray", "z06"]
  ```

  In `tests/multi-model-runtime-switching.test.mjs`, also assert:

  ```js
  for (const modelKey of ["grand_sport_x", "zr1", "zr1x"]) {
    assert.equal(Object.hasOwn(registry.models, modelKey), false);
  }
  for (const artifact of [
    "form-output/runtime/grand-sport-x-runtime-contract.json",
    "form-output/runtime/zr1-runtime-contract.json",
    "form-output/runtime/zr1x-runtime-contract.json",
  ]) {
    assert.equal(fs.existsSync(artifact), true, `${artifact} must be retained while unpublished`);
  }
  ```

  Remove test assertions that exercise GSX/ZR1/ZR1X through the published registry. Do not move their business expectations into another active-runtime test during stabilization.

- [ ] **Step 2: Prove the new expectation fails against the current six-model registry**

  Run:

  ```sh
  node --test tests/multi-model-runtime-switching.test.mjs tests/z06-runtime-promotion.test.mjs
  ```

  Expected: failure showing `grand_sport_x`, `zr1`, and `zr1x` are still present in `form-app/data.js`.

- [ ] **Step 3: Preflight the exact workbook change**

  Confirm Excel is closed and `~$stingray_master.xlsx` is absent. Export or construct one version-1 editor batch bound to the current workbook mtime with exactly these items:

  ```json
  {
    "action": "update",
    "sheet": "model_registry_promotion",
    "key": {"model_key": "grand_sport_x"},
    "row": {"promoted_to_runtime": false}
  }
  ```

  Repeat the same update for `zr1` and `zr1x`. The batch must not contain any other sheet, row, or field. Save the batch outside the repository as `/private/tmp/27vette-unpublish-ops.json` and run the no-write preflight:

  ```sh
  .venv/bin/python scripts/apply_workbook_ops.py /private/tmp/27vette-unpublish-ops.json --workbook stingray_master.xlsx
  ```

  Expected: `ok=true`, three prepared updates, complete operation coverage, and no workbook byte change. Stop if the batch proposes changes to `active`, `artifact_path`, model metadata, variants, source registrations, or assets.

- [ ] **Step 4: Apply the exact three-field workbook update**

  Apply only the preflighted batch:

  ```sh
  .venv/bin/python scripts/apply_workbook_ops.py /private/tmp/27vette-unpublish-ops.json --workbook stingray_master.xlsx --write
  ```

  Expected: `ok=true`, a backup path, successful live readback, and an edit-log entry covering only `model_registry_promotion`. If a confirmable warning is returned, review its exact ID and repeat with only that ID in `--confirm-warnings`; do not use `--allow-stale`.

- [ ] **Step 5: Verify preservation before regeneration**

  Reopen the saved workbook read-only and prove:

  - the three target `promoted_to_runtime` values are `False`;
  - Stingray, Grand Sport, and Z06 remain promoted;
  - exactly one promoted default remains and it is Stingray;
  - all six `model_master` rows remain;
  - GSX/ZR1/ZR1X source registrations, variants, assets, and source sheets remain;
  - the backup exists and the canonical workbook opens from disk.

  Stop and restore the backup if any preservation assertion fails.

- [ ] **Step 6: Regenerate only the stable customer publication path**

  ```sh
  .venv/bin/python scripts/generate_form.py --model stingray
  .venv/bin/python scripts/generate_form.py --model grand_sport
  .venv/bin/python scripts/generate_form.py --model z06
  .venv/bin/python scripts/generate_registry.py
  ```

  Expected: the registry generator reports only `stingray`, `grandSport`, and `z06`. Do not regenerate or delete the three unpublished runtime contracts.

- [ ] **Step 7: Update current-state documentation**

  Update `README.md` so it states that GSX, ZR1, and ZR1X remain workbook-backed future models with retained contracts but are intentionally unpublished pending rehabilitation. Keep the generic promotion, generation, registry, workbook-safety, and validation commands.

- [ ] **Step 8: Commit the reversible stabilization boundary**

  ```sh
  git add stingray_master.xlsx form-app/data.js README.md tests/multi-model-runtime-switching.test.mjs tests/z06-runtime-promotion.test.mjs form-output/workbook-edit-log.jsonl form-output/runtime/stingray-runtime-contract.json form-output/runtime/grand-sport-runtime-contract.json form-output/runtime/z06-runtime-contract.json form-output/stingray-form-data.json form-output/stingray-form-data.csv
  git diff --cached --check
  git commit -m "fix: restore stable three-model publication"
  ```

  Stage generated files only when their content changed as part of the three active model runs. Never stage timestamp-only changes or changes to the three unpublished contracts without an explained content reason.

---

### Task 2: Retire Only Proven One-Use Recovery Machinery

**Files:**

- Delete the five candidates listed under “Delete only after the Task 2 proof passes.”
- Modify `README.md` to remove the two obsolete recovery-projection commands and their checkpoint prose.
- Inspect-no-change: generic compiler, splitter, plan builder, option-quality gate/allowlist, workbook-domain service, promotion tooling, Fable receipts/tests.

**Interface:**

- Consumes: repository imports, command references, test collection, CI/docs links, and Fable contract pointers.
- Produces: a smaller active maintenance surface without weakening any reusable compiler or runtime contract.

- [ ] **Step 1: Prove caller and contract isolation**

  Run:

  ```sh
  git grep -n -E 'options_recovery_(projection|changeset)|7-20_compounded-repair-spec'
  git log --all --oneline -- scripts/corvette_form_generator/ingest/options_recovery_projection.py scripts/corvette_form_generator/ingest/options_recovery_changeset.py tests/test_options_recovery_projection.py tests/test_options_recovery_changeset.py docs/ingest/7-20_compounded-repair-spec.md
  ```

  The acceptable active references are limited to the two modules, their two dedicated tests, the 7/20 spec, and the obsolete README command block. Historical text inside committed Fable receipts is evidence, not an active caller, and must remain unchanged. Stop retirement if any import, CLI, CI job, generic test, current spec, or runtime path outside this closed set calls either module.

- [ ] **Step 2: Record the keep/delete boundary in the diff review**

  Before deletion, verify that these reusable protections do not import the candidates and remain independently exercised:

  ```sh
  git grep -n -E 'copy_split|options_sheet_quality|workbook_domain|promote_model|generate_registry' scripts tests README.md docs/ingest
  ```

  Keep `docs/ingest/options-sheet-quality-remediation-spec.md` because it owns generic compiler prevention, not the one-use projection. Keep all Fable run directories even when they mention retired paths.

- [ ] **Step 3: Delete the closed recovery surface and obsolete commands**

  ```sh
  git rm scripts/corvette_form_generator/ingest/options_recovery_projection.py
  git rm scripts/corvette_form_generator/ingest/options_recovery_changeset.py
  git rm tests/test_options_recovery_projection.py
  git rm tests/test_options_recovery_changeset.py
  git rm docs/ingest/7-20_compounded-repair-spec.md
  ```

  Remove only the recovery-projection/checkpoint block formerly at `README.md` lines 106-116. Do not remove the ingest wizard, shared ChangeSet workflow, option-quality gate, generation, promotion, or registry instructions.

- [ ] **Step 4: Verify there is no stale active reference**

  ```sh
  git grep -n -E 'options_recovery_(projection|changeset)|7-20_compounded-repair-spec' -- ':!fable5loop/runs/**'
  PYTHONPATH=scripts .venv/bin/python -m pytest tests/test_ingest_wizard_canonical_compiler.py tests/test_ingest_wizard_exception_flow.py tests/test_workbook_domain_registry.py tests/test_workbook_changeset_service.py -q
  .venv/bin/python scripts/validate_fable5_loop.py
  ```

  Expected: no active reference and all retained generic/Fable contract tests pass. The Fable validator is run because retirement must not silently break receipt/state contracts; it is not permission to edit receipts to force the gate green.

- [ ] **Step 5: Commit the evidence-based retirement**

  ```sh
  git add README.md
  git diff --cached --check
  git commit -m "chore: retire completed options recovery tooling"
  ```

---

### Task 3: Reclaim Actual Disk Space Separately

**Filesystem scope:**

- Candidate: ignored `form-output/ingest-wizard/` only (about 989 MB at this snapshot).
- Preserve: all tracked `form-output/` files (about 11 MB), especially `form-output/runtime/`, `form-output/stingray-form-data.*`, inspection manifests, and `form-output/workbook-edit-log.jsonl`.
- Preserve: repository specs, tests, Fable receipts, workbook backups needed for rollback, and any source evidence not recoverable elsewhere.

**Interface:**

- Consumes: ignore rules, active process check, tracked-file inventory, and run-retention audit.
- Produces: reclaimed local space with no Git diff and no loss of authoritative source/product artifacts.

- [ ] **Step 1: Capture a deletion manifest and prove the target is ignored**

  ```sh
  du -sh form-output/ingest-wizard form-output/runtime tests docs
  git check-ignore -v form-output/ingest-wizard
  git ls-files form-output
  find form-output/ingest-wizard -type f -print > /private/tmp/27vette-ingest-wizard-delete-manifest.txt
  ```

  Stop if the directory is no longer ignored or if any path returned by `git ls-files form-output` is inside the deletion target.

- [ ] **Step 2: Confirm the runs are not active or uniquely authoritative**

  Confirm no ingest wizard process is using the directory. Compare run IDs against tracked Fable outcomes/receipts and the preserved `origin/ingest-wizard` history. If a run contains the only copy of raw source evidence, approvals, or a required continuation artifact, move that exact run to a separately approved archive location before deletion. Do not treat “old” or “large” alone as proof of disposability.

- [ ] **Step 3: Delete only the validated ignored target**

  Resolve the path and require it to equal `/Users/seandm/Projects/27vette/form-output/ingest-wizard` before removing it. Then remove that exact directory and the ignored `form-output/.DS_Store`; do not use a wildcard against `form-output/`.

- [ ] **Step 4: Verify storage recovery and repository preservation**

  ```sh
  du -sh form-output
  git status --short
  git ls-files form-output | while IFS= read -r file; do test -f "$file" || printf 'missing tracked file: %s\n' "$file"; done
  ```

  Expected: roughly 989 MB reclaimed, no missing tracked files, and no Git diff from disk cleanup.

---

### Task 4: Create One Main Checkpoint and Run the Limited Main-Safety Gate

**Git surfaces:**

- Archive source: `origin/ingest-wizard`
- Destination: `main`
- Safety reference: `safety/main-before-ingest-stabilization-20260721`
- Result: one squash commit on `main`

**Interface:**

- Consumes: the clean stabilized branch from Tasks 1-3.
- Produces: a single reviewable main checkpoint and preserved detailed branch history.

- [ ] **Step 1: Refresh and verify the exact branch relationship**

  ```sh
  git fetch origin --prune
  git status --short --branch
  git rev-list --left-right --count origin/main...ingest-wizard
  git rev-parse ingest-wizard
  git rev-parse origin/ingest-wizard
  ```

  Require a clean tree, zero commits on the left side of the comparison, and identical local/remote ingest-wizard hashes. Push `ingest-wizard` normally if the stabilization commits are not yet archived remotely. Never force-push or delete `origin/ingest-wizard`.

- [ ] **Step 2: Prepare updated main and a rollback reference**

  ```sh
  git switch main
  git pull --ff-only origin main
  git branch safety/main-before-ingest-stabilization-20260721
  git merge --squash ingest-wizard
  ```

  Expected: the stabilized content is staged on main without importing the 87-plus branch commits. Stop on conflicts; do not invent conflict resolutions that change workbook/product behavior.

- [ ] **Step 3: Run the one allowed main-safety gate against the squash candidate**

  Run exactly:

  ```sh
  .venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
  .venv/bin/python scripts/generate_form.py --model stingray
  .venv/bin/python scripts/generate_form.py --model grand_sport
  .venv/bin/python scripts/generate_form.py --model z06
  .venv/bin/python scripts/generate_registry.py
  .venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
  node --test tests/multi-model-runtime-switching.test.mjs tests/z06-runtime-promotion.test.mjs
  ```

  Acceptance:

  - workbook package validation reports no issues;
  - schema validation reports no errors;
  - all three active generators succeed;
  - registry generation reports only `stingray`, `grandSport`, and `z06`;
  - model switching passes for those three models and defaults to Stingray;
  - `grand_sport_x`, `zr1`, and `zr1x` are absent from `form-app/data.js`;
  - their three retained runtime-contract files still exist.

  Explicitly do not run recovery projection, GSX/ZR1/ZR1X correctness, comparator, copy-quality, or “prove repaired models” gates. Their known defects are the reason they are unpublished.

- [ ] **Step 4: Review the final staged checkpoint**

  Inspect workbook and generated diffs. Require the workbook change to be limited to the three publication booleans (plus normal workbook package metadata written by the guarded path), the registry to remove only the three unfinished models, and active-model generated diffs to be intentional. Confirm dealer submission code and payload tests were not edited.

- [ ] **Step 5: Commit and push the single main checkpoint**

  ```sh
  git add -A
  git diff --cached --check
  git commit -m "feat: stabilize workbook and ingest baseline"
  git push origin main
  ```

  After the push, verify `origin/ingest-wizard` still resolves to the archived detailed history and `origin/main` resolves to the new single checkpoint.

---

### Task 5: Rebaseline and Correct PR #8

**Files likely modified on `codex/workbook-relational-db`:**

- `scripts/corvette_form_generator/editor_ops.py`
- `workbook-manager/backend/app/catalog.py`
- `workbook-manager/backend/app/workbook_profile.py`
- `workbook-manager/backend/app/model_compiler.py`
- `workbook-manager/backend/app/shared_compiler.py`
- `workbook-manager/backend/app/central_compiler.py`
- `workbook-manager/backend/app/importer.py`
- `workbook-manager/backend/app/migration.py`
- `tests/test_editor_ops_apply.py`
- `tests/workbook_manager/test_catalog_schema.py`
- `tests/workbook_manager/test_workbook_profile.py`
- `tests/workbook_manager/test_model_compiler.py`
- `tests/workbook_manager/test_shared_compiler.py`
- `tests/workbook_manager/test_central_compiler.py`
- `tests/workbook_manager/test_import_promotion.py`
- `tests/workbook_manager/test_completion_audit.py`
- `workbook-manager/README.md`
- PR #8 title/body and review checklist

**Interface:**

- Consumes: stabilized `origin/main`, shared `workbook_domain.registry`, workbook source registrations, and workbook publication metadata.
- Produces: a relational projection that imports every registered model, distinguishes publication from importability, restores failed workbook writes, and reports typed integrity findings without choosing business truth.

- [ ] **Step 1: Bring the open PR branch onto the new main without rewriting its history**

  ```sh
  git fetch origin
  git switch codex/workbook-relational-db
  git pull --ff-only origin codex/workbook-relational-db
  git merge origin/main
  ```

  Resolve content conflicts in favor of the updated main workbook-domain/write-safety contracts, then adapt the database code to those contracts. Do not rebase or force-push the open PR branch. Keep the PR in draft state until all three corrections pass.

- [ ] **Step 2: Write the failing post-save restoration regression**

  Add a test that allows scratch verification, forces `verify_prepared_workbook()` to fail only after `save_workbook_safely()` replaces the live workbook, and asserts:

  ```python
  assert result["ok"] is False
  assert result["status"] == "apply_verification_failed_rolled_back"
  assert workbook_path.read_bytes() == original_bytes
  assert Path(result["backupPath"]).exists()
  ```

  Add or preserve the companion test where restoration itself raises and require `status == "workbook_restore_failed"`, `workbookState == "unknown"`, and both the live-verification evidence and restoration failure to be preserved. Run the exact tests and confirm they fail against PR #8's current return-only behavior.

- [ ] **Step 3: Restore the backup before returning a failed live write**

  In `editor_ops.apply_batch()`, preserve the implementation already present on the updated main branch: reuse `restore_workbook_backup()` from `corvette_form_generator.workbook`, verify the restored bytes, and return the established typed statuses:

  ```python
  if not live_verification["ok"]:
      try:
          restore_workbook_backup(path, backup_path)
          restored_ok = (
              hashlib.sha256(path.read_bytes()).hexdigest()
              == hashlib.sha256(backup_path.read_bytes()).hexdigest()
          )
      except Exception as restore_error:
          return {
              "ok": False,
              "status": "workbook_restore_failed",
              "workbookState": "unknown",
              "errors": [str(restore_error)],
              "backupPath": str(backup_path),
              "verification": live_verification,
          }
      if not restored_ok:
          return {
              "ok": False,
              "status": "workbook_restore_failed",
              "workbookState": "unknown",
              "errors": ["backup restoration could not be verified"],
              "backupPath": str(backup_path),
              "verification": live_verification,
          }
      return {
          "ok": False,
          "status": "apply_verification_failed_rolled_back",
          "workbookState": "restored",
          "errors": live_verification["errors"],
          "backupPath": str(backup_path),
          "verification": live_verification,
      }
  ```

  The real result dictionaries must also retain `backupPath`, `verification`, and error details as the updated-main implementation does. Restore before returning and never append a success edit-log entry for the failed apply.

- [ ] **Step 4: Make `workbook_domain.registry` the single schema-semantics owner**

  Write tests proving database keys, types, booleans, enums, references, and editor-family mappings are derived from `workbook_domain.registry.EDITOR_SHEET_META` and `SOURCE_ROLE_FAMILIES` rather than restated literals.

  Keep only database-specific topology in `workbook-manager/backend/app/catalog.py`: physical SQL table naming, SQL column representation, foreign-key layout, and manager-only central table roles. Replace duplicated `ROLE_KEYS`, `ROLE_BOOLEAN_COLUMNS`, `ROLE_ENUMS`, and equivalent writable-schema declarations with a thin adapter from the shared registry. A mismatch between the adapter and shared registry must fail a contract test.

- [ ] **Step 5: Replace “three live models” with separate discovered sets**

  Model these concepts separately:

  - **known models:** rows present in `model_master`;
  - **importable models:** known models with registered source families in `model_workbook_sources`, whether published or not;
  - **published models:** active rows with `model_registry_promotion.promoted_to_runtime=True`.

  Compiler/import loops and physical table creation must use the validated importable model set. Customer registry parity checks must use the published set. Do not replace `LIVE_MODELS = ("stingray", "grand_sport", "z06")` with a hard-coded six-model tuple.

  Keep SQL identifier safety: discovered model keys and table roles must be validated against workbook registrations and the shared family registry before physical names are constructed or queried.

- [ ] **Step 6: Replace fixed 65-sheet and row-count assertions with source-derived invariants**

  Update the seven stale inventory tests so they assert:

  - every nonempty workbook sheet receives an explicit disposition;
  - the source catalog count equals the workbook's actual nonempty sheet inventory;
  - all registered source families for every importable model map to a physical database table;
  - all physical role registries are complete and internally consistent;
  - inactive/unpublished models are imported and validated but never treated as customer-published;
  - dangling IDs, invalid sections, incomplete variant coverage, duplicate identities, broken exclusive-group references, and inconsistent table families appear as typed findings.

  Counts may still be reported as diagnostics, but 3 models, 65 sheets, 77 sheets, 8,922 rows, and 9,091 rows must not be acceptance constants.

- [ ] **Step 7: Prove inactive GSX/ZR1/ZR1X import without publication**

  Build a fresh database from the stabilized workbook and assert all six registered models have their expected workbook-shaped table families and row provenance. Assert the publication view/API still exposes only Stingray, Grand Sport, and Z06. Database findings for the three unfinished models must remain review surfaces and must not mutate the workbook, `form-app/data.js`, or their publication flags.

- [ ] **Step 8: Run the bounded PR #8 correction gates**

  ```sh
  PYTHONPATH=scripts .venv/bin/python -m pytest tests/workbook_manager tests/test_workbook_manager.py tests/test_editor_ops_apply.py tests/test_workbook_domain_registry.py -q
  node --test tests/workbook_manager/test_frontend_contract.mjs
  npm --prefix workbook-manager/frontend run build
  .venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
  .venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
  ```

  Expected: no P1 reproduction, no duplicate-schema contract drift, no fixed-inventory failures, all inactive model imports represented, frontend contract green, build green, and workbook package/schema green. No live workbook write, registry publication, deployment, or dealer submission is part of this PR gate.

- [ ] **Step 9: Update and merge PR #8 only after review**

  Update the PR body so it describes six importable workbook models, three published models, shared registry ownership, restoration behavior, and the current validation results. Preserve the architectural limitation explicitly: the database can find relational/data-shape defects, but it cannot decide copy, pricing, UQT behavior, defaults, or other business rules.

  Request review of the three bounded corrections. Merge PR #8 into the updated `main` only after the P1 is closed and all Task 5 gates are green.

---

### Task 6: Start Model Rehabilitation From the Corrected Baseline

**Branch:** `codex/model-rehabilitation`

**Interface:**

- Consumes: main after the stabilization checkpoint and corrected PR #8 merge.
- Produces: an isolated rehabilitation workspace using both local-form behavior and typed database findings, with no implicit publication.

- [ ] **Step 1: Create the branch from confirmed current main**

  ```sh
  git switch main
  git pull --ff-only origin main
  git switch -c codex/model-rehabilitation
  ```

- [ ] **Step 2: Establish the two review surfaces without publishing**

  - Import the canonical workbook into a fresh local database and retain typed findings with workbook sheet/row provenance.
  - For browser review, copy the workbook and app into an isolated scratch worktree, temporarily enable GSX/ZR1/ZR1X publication only in that scratch workbook, generate scratch contracts/registry, and run the local form there.
  - Never commit scratch publication flags or scratch `form-app/data.js` to the rehabilitation branch.
  - Keep the canonical branch registry at three published models until a later explicit promotion decision.

- [ ] **Step 3: Use each surface only for what it can prove**

  The database may block or flag:

  - dangling option IDs;
  - broken exclusive-group and relationship references;
  - incomplete variant coverage;
  - invalid sections;
  - duplicate identities;
  - inconsistent table families and source registrations.

  The local form may expose interaction, selection, display-order, summary, total, and switching behavior. Neither surface may decide whether copy, pricing, UQT behavior, availability, or defaults are correct. Those decisions require workbook/business evidence and explicit review.

- [ ] **Step 4: Define rehabilitation acceptance before editing product data**

  Create a model-by-model findings ledger that separates:

  - structural defects with deterministic fixes;
  - runtime behavior defects reproducible in the scratch local form;
  - business-rule questions requiring Sean's decision;
  - corroborating comparator evidence that is not itself source authority.

  Start workbook edits only for deterministic, already-authorized outcomes. Stop at every unresolved business decision. Promotion of any rehabilitated model is a later explicit phase with its own workbook safety, generation, registry, runtime, and dealer-boundary review.

---

## Final Handoff Checklist

### Completed

- [ ] Files, workbook rows, generated artifacts, tests, docs, branches, and PR changes are listed.
- [ ] The stable customer form publishes exactly Stingray, Grand Sport, and Z06.
- [ ] The three unfinished models remain intact and available for rehabilitation.
- [ ] `main` contains one comprehensible squash checkpoint and `origin/ingest-wizard` remains the archive.

### Preserved

- [ ] Workbook business-data ownership and all model source data.
- [ ] Runtime contract schema, generic compiler/service/promotion paths, assets, and Fable receipts.
- [ ] Dealer endpoint, payload, Turnstile behavior, submission UX, deployment path, and dependencies.

### Validation

- [ ] Every command actually run is reported with its real result.
- [ ] The single main-safety gate is reported separately from PR #8's database gates.
- [ ] Gates intentionally not run are named, especially unfinished-model correctness gates and live dealer submission.

### Remaining Risk

- [ ] Known GSX/ZR1/ZR1X product-data defects remain unpublished, not concealed or declared fixed.
- [ ] Database findings remain integrity evidence, not business-rule authority.
- [ ] Any retained ignored run artifact or external archive is identified.
- [ ] Residual follow-up is limited to the fresh rehabilitation branch; none is implied outside that scope.
