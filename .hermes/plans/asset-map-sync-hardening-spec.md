# Asset Map Sync Hardening Spec

Status: Implemented 2026-06-25.
Date: 2026-06-25
Recommended reasoning level for Sean: high

## Completion Evidence

Implemented files:

- `scripts/corvette_form_generator/asset_map_sync.py`
- `scripts/sync_asset_map.py`
- `asset_map-Sync/asset_map_sync.py`
- `asset_map-Sync/asset_map_sync.README.md`
- `tests/test_asset_map_sync.py`
- `tests/fixtures/asset-map-sync-media-urls.txt`
- `AGENTS.md`
- `.hermes/plans/asset-map-sync-hardening-spec.md`

Completion notes:

- The old `asset_map-Sync/asset_map_sync.py` unsafe direct-save implementation was replaced with a hard-fail deprecation stub.
- The supported CLI is `.venv/bin/python scripts/sync_asset_map.py`.
- The importable implementation uses stdlib HTTP; `requirements.txt` was inspected and intentionally not changed.
- Default sync scope resolves promoted runtime models from `model_registry_promotion` and source option sheets from `model_workbook_sources`.
- Required validation can use deterministic media URL fixture input; live WordPress fetch remains optional smoke / next-pass report-only work.
- No real workbook apply was run. No generated runtime artifacts were regenerated.

Gates run:

```sh
.venv/bin/python -m pytest tests/test_asset_map_sync.py -q
.venv/bin/python -m py_compile scripts/corvette_form_generator/asset_map_sync.py scripts/sync_asset_map.py asset_map-Sync/asset_map_sync.py
.venv/bin/python scripts/sync_asset_map.py --help
.venv/bin/python scripts/sync_asset_map.py --workbook stingray_master.xlsx --report-dir /tmp/asset-map-sync-hardening --media-url-list tests/fixtures/asset-map-sync-media-urls.txt --no-verify-existing
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
git diff --check -- AGENTS.md asset_map-Sync/asset_map_sync.README.md asset_map-Sync/asset_map_sync.py scripts/corvette_form_generator/asset_map_sync.py scripts/sync_asset_map.py tests/test_asset_map_sync.py tests/fixtures/asset-map-sync-media-urls.txt .hermes/plans/asset-map-sync-hardening-spec.md
```

Gate results:

- Focused Python tests: 6 passed.
- Fixture dry-run: 95 `keep`, 356 `flag_missing`, 0 URL writes, 0 inserts, 1 unparseable fixture file; reports written under `/tmp/asset-map-sync-hardening`.
- Workbook package validation: valid, 0 issues.
- Workbook schema validation: valid, 0 errors, 0 warnings.

Residual follow-up:

- Run an optional real WordPress report-only sync and inspect candidate rows before approving any workbook `asset_map` apply.
- If a future pass needs `requests`, write a dependency-change spec first; this pass intentionally avoided new dependencies.

## Request

Begin finishing the partially built asset map syncing module currently under `asset_map-Sync/` by making it safe, testable, and explicitly runnable as a workbook maintenance command.

This is the first wiring pass. It should not automatically run during normal form generation yet.

## Diagnosis

The existing runtime/generator asset-map consumption path is already wired. The unfinished surface is the sync/maintenance tool itself.

Current evidence:

- `asset_map-Sync/asset_map_sync.py`
  - Standalone script that reconciles workbook `asset_map` option rows against WordPress media URLs.
  - Default mode is dry-run, but `--apply` writes directly with `wb.save(args.workbook)`.
  - Imports `requests`, which is not present in `requirements.txt`.
  - Uses hardcoded `OPTION_SHEETS`, including inactive/future `zr1_options` and `zr1x_options` when those sheets exist.
  - Defaults `--report-dir` to `.`, which can write report files into the repo root.
  - Exits before help if `requests` is unavailable because import happens at module load.

- `asset_map-Sync/asset_map_sync.README.md`
  - Documents the intended data model and reconcile behavior.
  - Claims the pure core is importable/testable, but the current folder name and standalone layout make normal test imports awkward.
  - States that every active+selectable option should have exactly one `asset_map` row. That is too broad for the current workbook contract unless explicitly scoped as a full media inventory build.

- `requirements.txt`
  - Currently contains only `et_xmlfile` and `openpyxl`.
  - Running `.venv/bin/python asset_map-Sync/asset_map_sync.py --help` fails with `ModuleNotFoundError: No module named 'requests'`.

- `AGENTS.md`
  - Explicitly says `asset_map-Sync/asset_map_sync.py` must remain dry-run/report-only until an approved pass aligns its write path with `save_workbook_safely()` and project dependencies.

- `stingray_master.xlsx / asset_map`
  - Current headers are `model_key`, `target_type`, `target_id`, `image_url`, `image_alt`, `image_fit`, `image_position`, `active`, `notes`.
  - Current active option asset rows have no duplicate active `(model_key, target_type, target_id)` keys.
  - Current `asset_map` is a media map, not an exhaustive inventory of every selectable option.

- `stingray_master.xlsx / model_master` and `model_registry_promotion`
  - Active/promoted runtime models are `stingray`, `grand_sport`, and `z06`.
  - `zr1` and `zr1x` option sheets exist but are inactive/unpromoted scaffolds.
  - A sync command must not treat inactive model sheets as routine active-maintenance inputs by default.

- Existing generator/runtime consumers:
  - `scripts/corvette_form_generator/contract.py`
    - `ASSET_IMAGE_FIELDS = ("image_url", "image_alt", "image_fit", "image_position")`.
    - `load_asset_map()` reads active exact-model asset rows keyed by `(target_type, target_id)`.
    - `option_asset_map()` and `load_model_asset_map()` feed generated data.
  - `scripts/corvette_form_generator/production.py`
    - Merges option asset fields into Stingray generated choices.
  - `scripts/corvette_form_generator/inspection.py`
    - Merges option asset fields into promoted/draft model choices.
  - `scripts/generate_registry.py`
    - Merges model-card assets into the browser registry.
  - Runtime already renders generic media fields from generated data.

Root cause:

The sync tool was built as a useful standalone prototype, but it has not been integrated into the repo's current workbook-first safety rules. Before it can be used as a real maintenance tool, it needs safe-save semantics, active-model discovery from workbook metadata, explicit non-generation invocation, tests, dependency handling, and report-output discipline.

Risk level: Medium.

Change type: mixed workflow/tooling + tests + docs. Potential future workbook writes, but this first pass should be report-only by default and should not change workbook data or generated runtime artifacts unless explicitly approved in a later apply pass.

## Ownership Decision

- Workbook owns image metadata rows in `asset_map`.
- WordPress media library owns candidate hosted image URLs.
- Model option sheets and model metadata own which active model options are eligible for media mapping.
- The sync module should only report or safely update workbook `asset_map` rows. It should not become a runtime image source, generator source of business rules, or automatic generation step.
- Runtime and generator consumption should remain generic and unchanged in this pass.

## Exact Files / Sheets / Artifacts To Change

Expected files to change in this first pass:

1. Create: `scripts/corvette_form_generator/asset_map_sync.py`
   - Move/refactor the importable sync logic here.
   - Keep pure helpers importable for tests.

2. Create: `scripts/sync_asset_map.py`
   - Thin CLI wrapper for the sync command.
   - Should be the documented entry point.

3. Modify/delete: `asset_map-Sync/asset_map_sync.py`
   - Required. Do not leave the old unsafe runnable entry point in place.
   - Replace it with one of these safe outcomes:
     - a delegating wrapper that imports and calls `scripts/corvette_form_generator/asset_map_sync.py` and therefore uses the same safe apply path;
     - a hard-fail deprecation stub that exits non-zero and points users to `.venv/bin/python scripts/sync_asset_map.py`;
     - or delete the old script if no compatibility path is needed.
   - The old direct `--apply` + `wb.save(args.workbook)` implementation at lines 496-499 must not survive the pass.

4. Create: `tests/test_asset_map_sync.py`
   - Unit tests for parser, media indexing, active model/sheet discovery, reconcile behavior, and safe apply boundary.

5. Create: `tests/fixtures/asset-map-sync-media-urls.txt`
   - Deterministic media URL fixture for CLI validation and tests.
   - Keep it small and representative; do not require live WordPress access for required gates.

6. Modify: `asset_map-Sync/asset_map_sync.README.md` or replace with a current docs file
   - Preferred: leave a short compatibility note in `asset_map-Sync/` pointing to the new command, or move current useful content into `docs/asset-map-sync.md`.
   - Avoid preserving stale claims that every active+selectable option must always have an `asset_map` row.

7. Modify: `AGENTS.md`
   - Only after the tool is safe: update the current warning that the helper is report-only until safe-save/dependencies are aligned.
   - The updated guidance should still say asset syncing is an explicit maintenance step, not an automatic generator step.
   - Do not update `AGENTS.md` to call the command safe while any unsafe runnable legacy entry point remains in `asset_map-Sync/`.

8. Modify: this spec file, `.hermes/plans/asset-map-sync-hardening-spec.md`
   - On completion, update status, date, changed files, gates, residual risks, and next pass.

Files to inspect but expected not to change:

- `requirements.txt`
  - This pass chooses stdlib HTTP instead of adding `requests`, so no dependency change is expected.

Workbook sheets to inspect but not write in this first pass unless explicitly approved:

- `stingray_master.xlsx`
  - `asset_map`
  - `model_master`
  - `model_registry_promotion`
  - `model_workbook_sources`
  - active model option sheets resolved through metadata: `stingray_options`, `grandSport_options`, `z06_options`
  - inactive/future sheets such as `zr1_options` and `zr1x_options` only for negative/exclusion tests or explicit user-approved future-model mode.

Generated artifacts that should not change in this first pass:

- `form-output/runtime/*.json`
- `form-output/stingray-form-data.json`
- `form-output/stingray-form-data.csv`
- `form-app/data.js`

If implementation accidentally changes generated artifacts, stop and classify before retaining them.

## Implementation Requirements

### 1. Module placement and command shape

Create an importable module at `scripts/corvette_form_generator/asset_map_sync.py`.

Keep these categories separate:

- pure parsing and reconcile helpers;
- workbook read/discovery helpers;
- media fetch helpers;
- workbook apply helpers;
- CLI argument parsing/output.

Create `scripts/sync_asset_map.py` as the user-facing command. It should call the module's `main()` or equivalent.

Do not call the sync command from `scripts/generate_form.py` or `scripts/generate_registry.py` in this pass.

### 2. Active model and source-sheet discovery

Replace hardcoded default `OPTION_SHEETS` behavior with workbook metadata discovery.

Default scope:

- active promoted runtime models only, resolved through `model_registry_promotion` rows where `active` and `promoted_to_runtime` are true.
- For each promoted model, resolve the source option sheet through `model_workbook_sources.source_role == "source_option_sheet"`.

This is intentional. Do not encode the current coincidence that active/generatable models and promoted runtime models both resolve to `stingray`, `grand_sport`, and `z06` today. Generation eligibility and runtime promotion are separate repo concepts.

Use `model_workbook_sources` to resolve each model's `source_option_sheet` instead of hardcoding sheet names.

Rules:

- Do not include inactive `zr1` or `zr1x` by default.
- If future-model or generatable-but-unpromoted support is desired, require an explicit scope flag such as `--scope generation`, `--include-inactive`, or `--model zr1`.
- Missing inactive/future sheets should not matter for the default run.
- The report should name which models/sheets were included.

### 3. Workbook write safety

Apply mode must use the existing project safe-save path.

Required behavior before any workbook write:

- Check for Excel lock file `~$stingray_master.xlsx` through the existing helper when possible.
- Record workbook mtime after load.
- Save through `save_workbook_safely()` from `scripts/corvette_form_generator/workbook.py`.
- Do not call `wb.save(args.workbook)` directly for the source workbook.
- Do not create `stingray_master.xlsx.bak` in the repo root.
- Reopen the saved workbook and verify expected updated rows/cells.
- Keep dry-run as the default.

If this pass implements only dry-run/report mode and leaves apply disabled, that is acceptable only if the CLI exits clearly when `--apply` is requested and the spec completion marks apply wiring as deferred. Preferred outcome is safe apply support covered by tests.

### 4. Row creation/update policy

Do not treat `asset_map` as a mandatory exhaustive option inventory by default.

Default policy:

- existing live URL: keep;
- existing dead URL with confident candidate: replace in apply mode;
- blank existing URL with confident candidate: fill in apply mode;
- missing row with confident candidate image: insert in apply mode;
- missing row without confident candidate: report only, do not insert a blank row by default;
- ambiguous candidate: report only;
- stale option row: report only by default;
- stale deactivation requires explicit `--deactivate-stale` and safe apply.

If exhaustive blank-row seeding is still needed, make it an explicit opt-in flag such as `--seed-blank-missing`. Do not make it the default.

### 5. WordPress media fetch and credentials

The command should support public read-only media fetch when possible.

Observed current endpoint:

- `https://stingraychevroletcorvette.com/wp-json/wp/v2/media?per_page=1&_fields=source_url&media_type=image` returned HTTP 200 without credentials during analysis.

Required behavior:

- Use Basic auth only if `WP_USER` and `WP_APP_PASSWORD` are set.
- Do not require credentials before running `--help`, parser tests, workbook-only tests, or report generation against supplied fixture/media URLs.
- Never print secrets.
- Keep timeout and pagination behavior explicit.

Dependency choice for this pass:

- Use Python stdlib HTTP. Do not add `requests` to `requirements.txt` in this pass.
- If implementation later proves stdlib HTTP is insufficient, stop and write a dependency-change follow-up instead of quietly adding `requests`.
- `.venv/bin/python scripts/sync_asset_map.py --help` must work without third-party HTTP dependencies.

### 6. Report output discipline

Change default `--report-dir` away from repo root.

Acceptable defaults:

- require explicit `--report-dir`; or
- default to a temp/generated ignored path such as `form-output/reports/asset-map-sync/` if confirmed acceptable.

Reports should include:

- included models and option sheets;
- existing option asset rows;
- candidate media matches;
- actions (`keep`, `fill`, `replace_404`, `insert_filled`, `flag_missing`, `flag_ambiguous`, `stale_option`, etc.);
- whether action is report-only or would write on apply;
- unmatched media.

The `.asset_map_sync_state.json` cursor should live only under the report directory and advance only after a successful `--apply` run.

### 7. Tests

Add focused Python tests that do not require network or real workbook writes.

Minimum coverage:

Parser/media indexing:

- `imgi_47_379.png` parses as no model prefix and RPO `379`.
- `h-stx.png` parses as model `z06`, RPO `stx`.
- `hzp.png` parses as no model prefix, RPO `hzp`.
- `c-qe6_v1.png` parses as model `stingray`, RPO `qe6`.
- model prefix requires a hyphen; a leading letter without hyphen is part of the RPO.

Reconcile behavior:

- existing live URL is kept and curation is not overwritten;
- blank existing URL fills from prefixed exact candidate;
- dead existing URL replaces from prefixed exact candidate;
- bare candidate assigns only when unique after prefixed-model exclusions;
- bare candidate shared across eligible models is ambiguous and not assigned;
- stale option rows are reported but not deleted;
- missing row with candidate can produce insert;
- missing row without candidate reports missing but does not insert blank by default.

Workbook/source discovery:

- default model discovery excludes inactive `zr1`/`zr1x` model rows even if their option sheets exist;
- source option sheets are resolved through `model_workbook_sources`;
- missing optional/inactive future sheets do not fail the default run.

CLI/safety:

- `scripts/sync_asset_map.py --help` runs in the project venv;
- deterministic CLI validation can run from a fixture media URL list without live WordPress access;
- `--apply` path uses `save_workbook_safely()` or an injected save function in tests;
- direct source-workbook `wb.save(args.workbook)` is not used in apply code;
- the old `asset_map-Sync/asset_map_sync.py` entry point no longer contains an unsafe direct apply path;
- report-only mode writes no workbook.

### 8. Documentation

Update docs to reflect the new supported workflow:

```sh
.venv/bin/python scripts/sync_asset_map.py --workbook stingray_master.xlsx --report-dir /tmp/asset-map-sync
```

If apply is implemented:

```sh
.venv/bin/python scripts/sync_asset_map.py --workbook stingray_master.xlsx --report-dir /tmp/asset-map-sync --apply
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
.venv/bin/python scripts/generate_registry.py
```

Docs must preserve the boundary that runtime image URLs remain workbook-authored through `asset_map`; source/reference image files are not bundled directly into the app.

## Companion-File Impact Matrix

- Workbook/source data — inspected-no-change for this first pass. The pass hardens tooling; it should not edit `asset_map` rows unless a later apply pass is approved.
- Generated runtime contracts — inspected-no-change expected. Existing consumers already emit `asset_map` fields; no generated artifact changes should be retained in this first pass.
- Runtime JS/CSS/HTML — inspected-no-change expected. Runtime already renders generic media fields; no visual/runtime behavior change is intended.
- Tests — update required. Add `tests/test_asset_map_sync.py`; existing runtime image tests should remain unchanged unless the implementation exposes stale assumptions.
- Dependencies — inspected-no-change. This pass chooses stdlib HTTP; do not add `requests` or modify `requirements.txt`.
- Docs/specs — update required. Update this spec on completion and update/replace the stale `asset_map-Sync` README. Update `AGENTS.md` only once the safe command exists.
- Gate reminders / worker guidance — inspect. If any workflow reminder mentions the old report-only warning or direct helper path, update to the new explicit command after implementation.
- Profile/Codex guidance — inspect-no-change unless a matching checked-in guidance file encodes the old helper path. Do not edit Hermes profile skills from this repo pass.
- Count/ID-sensitive tests — likely not applicable if no generated artifacts or workbook rows change. If apply mode is tested against the real workbook or generated artifacts are touched, search affected tests for hardcoded image counts/IDs before handoff.

## Constraints

- Preserve workbook source-of-truth ownership for image metadata.
- Do not hardcode runtime image URLs in JavaScript or generator code.
- Do not make WordPress media the runtime source of truth; it is only a candidate URL source for workbook maintenance.
- Do not run this automatically in `generate_form.py` or `generate_registry.py` in this pass.
- Do not edit generated `form-output/*` or `form-app/data.js` directly.
- Do not change option labels, pricing, availability, rules, default selections, dealer submission endpoint, payload shape, Turnstile behavior, or runtime selection logic.
- Do not include inactive/future ZR1/ZR1X sheets in default sync scope.
- Do not create blank `asset_map` rows for every active+selectable option by default.
- Do not introduce a new workbook sheet, review taxonomy, or parallel media database.
- Do not save the workbook unless Excel is closed and the safe-save path succeeds.
- No new dependencies; `requirements.txt` should remain inspected-no-change.

## Non-Goals

- No automatic integration into normal model generation.
- No runtime rendering changes.
- No browser visual redesign.
- No image upload pipeline.
- No direct WordPress write/upload/delete behavior.
- No cleanup of existing unresolved inactive `asset_map` rows beyond reporting.
- No wildcard/shared asset-row migration.
- No interior/context-choice/layered visualizer media expansion.
- No full image coverage push for every selectable option.
- No generated artifact refresh unless an approved apply pass changes workbook data.

## Validation Plan

Preflight:

```sh
git status --short --branch
git branch --show-current
.venv/bin/python -m py_compile asset_map-Sync/asset_map_sync.py
```

After implementation:

```sh
.venv/bin/python -m py_compile scripts/corvette_form_generator/asset_map_sync.py scripts/sync_asset_map.py
.venv/bin/python -m py_compile asset_map-Sync/asset_map_sync.py  # only if retained as wrapper/stub
.venv/bin/python scripts/sync_asset_map.py --help
.venv/bin/python -m pytest tests/test_asset_map_sync.py
.venv/bin/python scripts/sync_asset_map.py --workbook stingray_master.xlsx --report-dir /tmp/asset-map-sync --media-url-list tests/fixtures/asset-map-sync-media-urls.txt --no-verify-existing
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
```

The `--media-url-list` fixture path may use a different exact file name if implementation chooses another fixture location, but the post-implementation merge gate must be deterministic and must not require live WordPress access.

Real WordPress media fetch should be treated as optional smoke / the next report-only pass, not as a required merge gate for this hardening pass.

If apply mode is implemented and approved for a test against the real workbook:

1. Confirm no Excel lock:

```sh
python3 - <<'PY'
from pathlib import Path
print('lock=present' if Path('~$stingray_master.xlsx').exists() else 'lock=absent')
PY
```

2. Run a scoped dry-run first and inspect reports.
3. Run apply only after report review.
4. Reopen workbook with `openpyxl` and verify expected cells/rows.
5. Run workbook validation before generation:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

6. Regenerate affected active models and registry only if workbook data changed:

```sh
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
.venv/bin/python scripts/generate_registry.py
```

7. Run targeted image/runtime gates only if workbook data/generated artifacts changed:

```sh
node --test tests/multi-model-runtime-switching.test.mjs
node --test tests/stingray-form-regression.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/z06-form-data-draft.test.mjs
```

For this first hardening pass, expected generated-artifact gate result should be `not run / not applicable` unless apply mode changes workbook data.

## Risks

- A too-broad sync command could seed hundreds of blank rows and turn `asset_map` into a duplicate option inventory.
- Including inactive ZR1/ZR1X sheets by default could make future scaffold data look like active runtime data.
- Direct workbook save could corrupt or overwrite user work if Excel is open or the file changes after load.
- Network fetch behavior can be flaky; tests and required validation must avoid live network dependence.
- Public WordPress media access may change; command should support optional credentials without requiring them for help/tests.
- Adding `requests` is out of scope for this pass because the spec chooses stdlib HTTP.

## Rollback

- Code/docs changes: revert the touched files.
- Dependency change: not expected; this pass should not modify `requirements.txt`.
- Workbook apply, if later approved and performed: restore from the safe-save backup path produced by `save_workbook_safely()` or revert the workbook file from git if the change was committed.
- Generated artifacts, if accidentally changed: restore from git unless a later approved apply pass intentionally refreshed them.

## Historical Approval Prompt

This first pass was approved to harden and wire `asset_map` sync as an explicit safe maintenance command, with report-only default, promoted-runtime-model discovery, stdlib HTTP, deterministic fixture-based validation, legacy unsafe entry-point retirement, tests, and docs.

Approved implementation scope: command/test/docs hardening only. Do not run `--apply` against the real workbook until a dry-run report has been reviewed.

## Recommended Next Pass After This One

After this hardening pass lands, run a report-only sync against the real workbook and WordPress media library. Use that report to write a separate apply spec that classifies candidate row updates/inserts by confidence, model, and customer-visible image impact before changing `asset_map` rows or regenerating runtime artifacts.
