# Asset Map Sync Module Setup Spec

Status: Spec only. Do not implement until approved.
Date: 2026-06-26
Recommended reasoning level for Sean: high

## Request

Set up the asset-map sync module properly before using it for real workbook `asset_map` maintenance.

This is the next pass after `.hermes/plans/asset-map-sync-hardening-spec.md`. The first pass made the command safe enough to run report-only and moved the old unsafe entry point behind a deprecation stub. This pass should make the module/report contract disciplined enough that a later apply pass can be reviewed and executed without hidden workbook-shape changes or unreviewed lifecycle edits.

## Diagnosis

Current state from repo evidence:

- Branch/status preflight: `main`, clean relative to `origin/main` at spec time.
- Implemented safe command:
  - `scripts/sync_asset_map.py` imports `corvette_form_generator.asset_map_sync.main`.
  - `asset_map-Sync/asset_map_sync.py` is a hard-fail deprecation stub.
  - `asset_map-Sync/asset_map_sync.README.md` points to `.venv/bin/python scripts/sync_asset_map.py --workbook stingray_master.xlsx --report-dir /tmp/asset-map-sync`.
- Current module shape:
  - `scripts/corvette_form_generator/asset_map_sync.py` is a single 657-line module that mixes CLI parsing, WordPress fetch, media parsing, workbook discovery, reconcile planning, report writing, and workbook mutation/apply.
  - `run_sync()` currently computes a report and applies cell/row mutations to the in-memory workbook before checking `apply`; dry-run does not save, but the plan/apply boundary is not explicit.
  - The CLI still exposes prototype-style mutating flags:
    - `--status-col` can add an `image_status` column, which is not part of the current `asset_map` workbook header contract.
    - `--deactivate-stale` can set `active=FALSE` based on the current `active+selectable` source-option inventory, which is too broad to treat as routine without review.
    - `--seed-blank-missing` can seed blank `asset_map` rows and risks turning `asset_map` into a duplicate option inventory.
    - `--since auto` writes `.asset_map_sync_state.json` after apply, but the report/apply review contract is not yet explicit.
- Current tests:
  - `tests/test_asset_map_sync.py` covers parser behavior, promoted-runtime model discovery, missing/ambiguous reporting, safe-save injection for a confident insert, CLI help, and the retired legacy entry point.
  - It does not yet lock a report manifest/source-inventory contract, plan-before-apply separation, rejection of schema-expanding flags, or report-driven apply review boundaries.
- Workbook source shape:
  - `stingray_master.xlsx / asset_map` headers are `model_key`, `target_type`, `target_id`, `image_url`, `image_alt`, `image_fit`, `image_position`, `active`, `notes`.
  - Active duplicate keys: none for `(model_key, target_type, target_id)` in the current workbook.
  - Active rows by target type from read-only probe: `stingray` option 24/model 1, `grand_sport` option 34/model 1, `z06` option 37/model 1.
  - There are inactive/blank-target legacy rows in `asset_map`; this pass should report but not clean them.
- Live report-only probe run during spec:
  - Command: `.venv/bin/python scripts/sync_asset_map.py --workbook stingray_master.xlsx --report-dir /tmp/asset-map-sync-next-spec --no-verify-existing`
  - Result: fetched 165 WordPress image URLs under `/wp-content/uploads/pictures/27vette/`.
  - Report counts: 95 `keep`, 345 `flag_missing`, 11 `insert_filled`, 96 unmatched media, 32 unparseable files.
  - Candidate inserts proposed by current matching:
    - Stingray: `opt_j6a_001`, `opt_j6f_001`, `opt_j6e_001`, `opt_j6n_001`, `opt_j6b_001`.
    - Grand Sport: `opt_17a_001`, `opt_20a_001`, `opt_55a_001`, `opt_75a_001`, `opt_97a_001`, `opt_dx4_001`.
  - These are useful candidates, but they are not approved workbook edits. The next code pass should improve report discipline before any apply pass changes `asset_map`.

Root cause:

The hardening pass safely replaced the unsafe one-off script, but it intentionally left the new implementation compact and transitional. It can now run, but it is not yet a clean report-first maintenance module: reporting, plan construction, and workbook mutation are still interleaved, and optional CLI flags can alter workbook schema or lifecycle state without a separate reviewed spec.

Risk level: Medium.

Change type: workflow/tooling + tests + docs. No workbook data edits, generated artifacts, runtime behavior, styling, dealer submission behavior, or dependencies should change in this setup pass.

## Ownership Decision

- Workbook `asset_map` remains the source of truth for runtime image metadata.
- WordPress media remains only a candidate URL source for maintenance reports.
- The sync module should build reviewable reports/plans and apply only explicitly approved workbook changes through `save_workbook_safely()`.
- The sync module should not define new product/business rules, runtime image behavior, or a parallel media database.
- Runtime and generator asset consumers should remain unchanged in this pass.

## Exact Files / Sheets / Artifacts To Change

Expected files to change:

1. `scripts/corvette_form_generator/asset_map_sync.py`
   - Keep the public import path stable.
   - Refactor into explicit phases:
     - scope discovery;
     - media fetch/list loading;
     - pure reconcile/plan building;
     - report/manifest writing;
     - workbook apply from an already-built plan.
   - Dry-run/report generation must not mutate workbook cells/rows, even in memory.
   - Add a run manifest under `--report-dir`, for example `asset_map_sync_manifest.json`, containing at minimum:
     - workbook path and asset sheet;
     - included model keys and source option sheets;
     - media source mode (`live` vs `media-url-list`), media URL count, and whether existing URL verification ran;
     - action counts and insert/write counts;
     - command options that affect planning;
     - timestamp;
     - explicit `apply: false` for dry-runs.
   - Keep CSV reports, but make the manifest the source inventory / review contract.
   - Remove, hide, or hard-fail unsupported prototype flags that can change workbook shape/lifecycle without a reviewed apply spec:
     - `--status-col` should not add `image_status` to the current workbook contract in this pass.
     - `--deactivate-stale` should not deactivate rows in this pass.
     - `--seed-blank-missing` should not seed blank rows in this pass.
   - If implementation keeps any of those flags for future compatibility, they must exit non-zero with a message that the behavior requires a separate approved workbook-data spec.
   - Preserve `--media-url-list`, `--no-verify-existing`, `--timeout`, `--workers`, and normal report-only live fetch behavior.
   - Preserve safe-save usage for any retained `--apply` path, but do not broaden real apply behavior in this pass.

2. `tests/test_asset_map_sync.py`
   - Add focused tests for:
     - manifest creation and required manifest fields;
     - manifest included models/sheets sourced from `model_registry_promotion` + `model_workbook_sources`;
     - dry-run/report path leaves workbook rows/cells unchanged;
     - unsupported schema/lifecycle flags fail clearly or are absent from help, depending on implementation choice;
     - apply code, if retained, applies from the plan phase and uses injected safe-save;
     - report-only mode never creates `.asset_map_sync_state.json`.
   - Keep existing parser, discovery, reconcile, CLI help, and legacy-stub tests.

3. `asset_map-Sync/asset_map_sync.README.md`
   - Update the README to describe the report-first workflow and manifest artifact.
   - State that blank-row seeding, stale-row deactivation, and schema/status-column changes are not routine workflow and need a separate approved workbook-data pass.

4. `.hermes/plans/asset-map-sync-module-setup-spec.md`
   - On implementation completion, update status, completion date, changed files, gates, residual risks, and recommended next pass.

Files to inspect but expected not to change:

- `AGENTS.md`
  - Expected inspected-no-change unless the supported command/help text changes enough that the standing asset-map maintenance guidance would become stale.
- `scripts/corvette_form_generator/editor_ops.py`
  - Expected inspected-no-change. This is the live workbook-editor gate reminder surface (`GATE_COMMANDS` / `gate_reminders()`), and this pass should not change editor reminder behavior.
- `tests/test_editor_ops_apply.py`
  - Expected inspected-no-change. Existing `GateRemindersTest` coverage should remain valid unless the implementation changes gate reminders, which is not expected.
- `requirements.txt`
  - Expected inspected-no-change. Continue using stdlib HTTP; no `requests` dependency.
- `scripts/sync_asset_map.py`
  - Expected inspected-no-change unless the module entrypoint name changes. Public CLI path should remain stable.
- `asset_map-Sync/asset_map_sync.py`
  - Expected inspected-no-change; keep the hard-fail deprecation stub.
- `tests/fixtures/asset-map-sync-media-urls.txt`
  - Expected inspected-no-change unless an added manifest test needs one more deterministic URL.
- Checked-in 27vette-gate guidance file
  - Not applicable at spec time: repo file search found no live checked-in file named `27vette-gate`. The Hermes profile skill exists outside the repo and should not be edited from this pass.

Workbook sheets to inspect but not write:

- `stingray_master.xlsx / asset_map`
- `stingray_master.xlsx / model_registry_promotion`
- `stingray_master.xlsx / model_workbook_sources`
- active promoted source option sheets resolved by metadata: `stingray_options`, `grandSport_options`, `z06_options`

Generated artifacts that should not change:

- `form-output/runtime/*.json`
- `form-output/stingray-form-data.json`
- `form-output/stingray-form-data.csv`
- `form-app/data.js`

If implementation accidentally changes generated artifacts or workbook data, stop, classify the drift, and restore it unless a separate apply spec has been approved.

## Implementation Requirements

### 1. Plan/report/apply separation

Create an explicit internal representation for the sync plan/report rows before applying workbook edits. Exact class names are flexible, but the code should make this separation obvious.

Required behavior:

- Report-only mode loads the workbook read-only when practical, or at minimum never mutates workbook cells/rows before deciding to save.
- Workbook mutation happens only inside the apply phase.
- Apply phase consumes the already-built plan and writes only the planned URL updates/row inserts.
- The plan records enough context for review: model, source sheet, target option id, RPO, existing URL, candidate URL, action, candidate source, and note.

### 2. Manifest/report contract

Write `asset_map_sync_manifest.json` in the report directory on every successful run.

Minimum manifest fields:

- `version`
- `generated_at_utc`
- `workbook_path`
- `asset_sheet`
- `apply`
- `media_source`
- `since_argument`
- `resolved_modified_after`
- `incremental`
- `state_path`
- `state_read`
- `state_written`
- `media_url_count`
- `verify_existing`
- `included_sources`: list of `{model_key, option_sheet}`
- `action_counts`
- `url_write_count`
- `insert_count`
- `unmatched_count`
- `unparseable_count`
- `report_path`
- `unmatched_path`

Do not include secrets or environment variable values.

`--since auto` lifecycle requirements:

- If `--since auto` remains supported, the manifest must state whether a prior `.asset_map_sync_state.json` was read, the resolved `modified_after` value used for the WordPress query, and whether this run wrote state.
- Report-only/dry-run mode must never write `.asset_map_sync_state.json`, including when `--since auto` is supplied.
- If `--apply` remains supported, state may be written only after safe-save succeeds; failed apply must not advance the cursor.
- Add focused tests for report-only `--since auto` with and without an existing state file, and for the apply-success/apply-failure state-write boundary if apply remains supported.
- If the implementation cannot make this lifecycle explicit in this pass, hard-fail `--since auto` with a clear message and test that failure instead.

### 3. Unsupported prototype flags

This setup pass should prevent accidental workbook schema/lifecycle changes that are not part of the normal `asset_map` source contract.

Preferred outcome:

- Remove `--status-col`, `--deactivate-stale`, and `--seed-blank-missing` from the supported help output.
- If a compatibility reason requires keeping the flags visible, make them exit non-zero with a message that the behavior requires a separate workbook-data spec.

Rationale:

- `image_status` is not part of the current `asset_map` header contract.
- Stale row deactivation depends on product/media intent, not just whether an option is currently active+selectable.
- Blank-row seeding would make `asset_map` behave like an exhaustive option inventory, which the current workflow explicitly avoids.

### 4. Apply boundary

Do not run a real workbook apply in this pass.

If the code keeps `--apply` available, keep it safe-save-backed and covered with temp-workbook tests only. Do not add a new real-workbook apply command such as `--apply-from-report` unless the implementation stays limited to temp/test coverage and the user approves the exact behavior in this spec.

A later apply spec should use the manifest/report output from this setup pass to classify actual row inserts/updates before touching `stingray_master.xlsx`.

### 5. Documentation

Document the safe report workflow:

```sh
.venv/bin/python scripts/sync_asset_map.py --workbook stingray_master.xlsx --report-dir /tmp/asset-map-sync
```

For deterministic validation:

```sh
.venv/bin/python scripts/sync_asset_map.py --workbook stingray_master.xlsx --report-dir /tmp/asset-map-sync --media-url-list tests/fixtures/asset-map-sync-media-urls.txt --no-verify-existing
```

Docs should say real `--apply` requires a reviewed report and separate approval when changing the canonical workbook.

## Companion-File Impact Matrix

- Workbook/source data — inspected-no-change. This pass must not edit workbook rows or schema.
- Generated runtime contracts — not applicable / must remain unchanged. No generation or registry publication is expected.
- Runtime JS/CSS/HTML — not applicable. Runtime already consumes generated media fields generically.
- Tests — update required. Expand `tests/test_asset_map_sync.py` for manifest, plan/apply separation, dry-run non-mutation, and unsupported mutating flags.
- Workbook-editor gate reminders — inspected-no-change expected for `scripts/corvette_form_generator/editor_ops.py` and `tests/test_editor_ops_apply.py`. This asset sync CLI is outside the workbook-editor apply reminder path; do not change `GATE_COMMANDS` / `gate_reminders()` unless implementation proves the command contract affects editor reminders.
- Dependencies — inspected-no-change. Continue stdlib HTTP; no `requirements.txt` change.
- Docs/specs — update required. Update `asset_map-Sync/asset_map_sync.README.md` and this spec on completion. Inspect `AGENTS.md` for stale command/help claims.
- Gate reminders / worker guidance — inspected-no-change expected. Repo inspection found no live checked-in `27vette-gate` file; do not edit Hermes profile skills from this repo pass. If a checked-in worker/gate guidance file is added or discovered during implementation, inspect it and report updated / inspected-no-change before handoff.
- Profile/Codex guidance — not applicable. Do not edit Hermes profile skills from this repo pass.
- Count/ID-sensitive tests — not applicable unless implementation accidentally regenerates app data, which should be restored.

## Constraints

- Preserve workbook source-of-truth ownership for image metadata.
- Do not hardcode image URLs in JavaScript, generators, or tests beyond deterministic fixture URLs.
- Do not make WordPress media a runtime source of truth.
- Do not add dependencies.
- Do not run sync automatically from `generate_form.py` or `generate_registry.py`.
- Do not edit generated artifacts directly.
- Do not change option labels, pricing, availability, rules, default selections, dealer submission endpoint, payload shape, Turnstile behavior, or runtime selection logic.
- Do not include inactive/future ZR1/ZR1X sheets in default sync scope.
- Do not create blank `asset_map` rows for every active/selectable option.
- Do not add a new workbook sheet, review taxonomy, or parallel media database.
- Do not save `stingray_master.xlsx` in this pass.

## Non-Goals

- No workbook `asset_map` row apply.
- No generated artifact refresh.
- No live runtime image rollout.
- No browser visual smoke requirement.
- No image upload/write/delete behavior in WordPress.
- No wildcard/shared asset-row migration.
- No interior/context-choice/layered visualizer media expansion.
- No cleanup of legacy blank/inactive `asset_map` rows.
- No full image coverage push for all selectable options.

## Validation Plan

Preflight:

```sh
git status --short --branch
git branch --show-current
.venv/bin/python scripts/sync_asset_map.py --help
```

After implementation:

```sh
.venv/bin/python -m py_compile scripts/corvette_form_generator/asset_map_sync.py scripts/sync_asset_map.py asset_map-Sync/asset_map_sync.py
.venv/bin/python scripts/sync_asset_map.py --help
.venv/bin/python -m pytest tests/test_asset_map_sync.py -q
.venv/bin/python scripts/sync_asset_map.py --workbook stingray_master.xlsx --report-dir /tmp/asset-map-sync-module-setup --media-url-list tests/fixtures/asset-map-sync-media-urls.txt --no-verify-existing
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
git diff --check -- scripts/corvette_form_generator/asset_map_sync.py scripts/sync_asset_map.py asset_map-Sync/asset_map_sync.py asset_map-Sync/asset_map_sync.README.md tests/test_asset_map_sync.py tests/fixtures/asset-map-sync-media-urls.txt AGENTS.md .hermes/plans/asset-map-sync-module-setup-spec.md
```

Post-gate drift check:

```sh
git status --short
git diff --exit-code -- stingray_master.xlsx form-output/runtime form-output/stingray-form-data.json form-output/stingray-form-data.csv form-app/data.js
```

Expected result: only approved code/test/docs/spec files are dirty. No workbook binary or generated artifact diffs should remain.

Optional smoke, not required for merge:

```sh
.venv/bin/python scripts/sync_asset_map.py --workbook stingray_master.xlsx --report-dir /tmp/asset-map-sync-live-report --no-verify-existing
```

Treat live WordPress fetch as optional because network/media-library state is external and mutable.

## Risks

- Over-refactoring the module could hide behavior changes in a tooling pass. Keep public CLI behavior stable except for explicitly unsupported prototype flags.
- Removing or hard-failing prototype flags may surprise anyone using them locally, but keeping them risks unreviewed workbook schema/lifecycle changes.
- Manifest contents can become another stale contract if not covered by tests.
- Live media reports are inherently time-sensitive; required validation must use fixture inputs.
- If `--apply` is retained without a report-review gate, a later user could still apply fresh live candidates directly. This pass should at least make the plan/apply boundary clear and documented; a stricter `--apply-from-report` workflow can be a later approved pass if needed.

## Rollback

- Revert changed code/test/docs/spec files.
- No workbook rollback should be needed because this pass must not save `stingray_master.xlsx`.
- No generated artifact rollback should be needed; restore from git if accidental generation occurs.

## Approval Prompt

Approve this asset-map sync module setup pass?

Recommended scope: refactor/report-contract hardening only; no real workbook apply, no generated artifact refresh, no dependency change, no runtime behavior change.

## Recommended Next Pass After This One

After this setup pass lands, use the manifest-backed live report to write a narrow `asset_map` apply spec. That apply spec should classify the 11 current `insert_filled` candidates by visual confidence/customer impact, inspect the exact workbook rows before save, run safe apply only after approval, regenerate affected active models plus registry, and review generated image diffs as an intentional runtime image rollout.
