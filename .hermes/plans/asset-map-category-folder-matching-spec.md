# Asset Map Category Folder Matching Spec

Status: Completed 2026-06-29.
Date: 2026-06-29
Branch: `ingest-wizard`

## Diagnosis

The current asset-map sync already discovers WordPress media URLs nested under `/wp-content/uploads/pictures/27vette/` because `scripts/corvette_form_generator/asset_map_sync.py` filters media URLs with `PATH_FILTER in url`.

Root issue: matching logic treats unprefixed filenames as ambiguous when the same RPO exists across multiple promoted models. This blocks intentional model-agnostic assets, where one bare RPO filename should apply to every promoted active model option with the matching RPO unless that model has a model-prefixed URL.

Current evidence inspected:

- `scripts/corvette_form_generator/asset_map_sync.py`
  - `PATH_FILTER = "/wp-content/uploads/pictures/27vette/"`
  - `fetch_media()` includes nested URLs because it checks `PATH_FILTER in url`.
  - `parse_media()` parses only the URL basename, not folders.
  - `build_media_index()` groups model-prefixed files into `exact[(model, rpo)]` and bare files into `bare[rpo]`.
  - `reconcile()` currently allows a bare file only when it is unique to one eligible promoted model; shared RPOs become `flag_ambiguous`.
- `tests/test_asset_map_sync.py`
  - `test_reconcile_reports_missing_without_default_blank_insert_and_flags_ambiguous_bare_media()` currently asserts shared bare `gba.png` is ambiguous for Stingray and Grand Sport.
  - Existing tests cover safe-save, manifest, missing-image reports, and retired legacy flags.
- `asset_map-Sync/asset_map_sync.README.md`
  - Documents safe sync behavior but does not explain shared category-folder matching.
- `AGENTS.md`
  - Documents safe command, report-first default, workbook-safe apply, and active model promotion scope.

Risk level: medium-low. This changes sync planning behavior, not live runtime JS directly. With `--apply`, it can write workbook `asset_map` rows or replace image URLs, so the behavior must stay deterministic, report-first, and test-covered.

Change type: generator/maintenance-tool behavior + tests + workflow docs. No workbook source-data edit is part of this spec.

## Intended Behavior

Add explicit support for model-agnostic shared media assets regardless of their folder location within the media filesystem.

Matching precedence:

1. Model-prefixed filename remains highest priority.
   - Example: `h-q9i.png` maps only to Z06 Q9I.
2. A single bare filename may map to every promoted active model option with the same RPO.
   - Example: `/27vette/paint/gba.png` can fill/insert matching GBA option assets for Stingray, Grand Sport, Z06, and future promoted models when those models have active/selectable GBA option rows.
   - Example: `/27vette/gba.png` follows the same shared fallback behavior; folder location does not change matching rules.
3. If both prefixed and shared bare candidates exist for the same `(model, rpo)`, prefer the model-prefixed candidate and do not mark the shared asset as the chosen URL for that model.
4. If multiple shared bare candidates exist for the same RPO, flag ambiguity instead of choosing by folder/order.
5. Folder names like `paint` and `int` are organizational only. They should not create different rulesets and should not override filename prefixes.

Recommended default for this pass:

- Treat any single bare filename under `/27vette/` as shareable by RPO.
- Keep model-prefixed filenames valid anywhere under `/27vette/.../`.

## Exact Files To Change

Update:

- `scripts/corvette_form_generator/asset_map_sync.py`
  - Keep media classification based on filename identity, not category folder:
    - model-prefixed exact candidates;
    - bare shared fallback candidates.
  - Update reconciliation so a single bare candidate can fill/insert every matching promoted active model option by RPO unless a model-prefixed candidate exists for that model/RPO.
  - Keep deterministic ambiguity handling for duplicate shared candidates.
  - Keep manifest/report shapes stable unless a small `candidate_source` value addition is needed, such as `shared-bare`.

- `tests/test_asset_map_sync.py`
  - Replace the current shared bare ambiguity test so bare `gba.png` fills/inserts all matching model rows.
  - Add test for model-prefixed candidate precedence over shared bare candidate.
  - Add test for duplicate shared bare candidates by RPO producing `flag_ambiguous`, not arbitrary selection.
  - Add test that category folders do not change parsing or matching rules.

- `asset_map-Sync/asset_map_sync.README.md`
  - Document that model-prefixed filenames work anywhere under `/27vette/`.
  - Document that single bare filenames are treated as shared fallback assets by RPO and can apply to all promoted models with matching active/selectable option rows.
  - Document that duplicate shared bare candidates are ambiguous.

Optional update only if needed after implementation:

- `AGENTS.md`
  - Inspect only. Update only if the standing workflow needs to mention shared category-folder matching. Likely inspected-no-change because it already points to the safe command and source-of-truth boundary.

Do not change:

- `stingray_master.xlsx`
- `form-output/*`
- `form-app/data.js`
- Runtime JS/CSS/HTML
- Dealer endpoint, payload shape, or Turnstile behavior

## Companion-File Impact Check

- Workbook sheets: not applicable; no workbook edit in this pass.
- Generated contracts / `form-app/data.js`: not applicable for implementation; no generation expected. A later real `--apply` will require model regeneration and registry generation.
- Tests: update `tests/test_asset_map_sync.py` because current expectations encode old bare-file ambiguity.
- Docs/specs: update `asset_map-Sync/asset_map_sync.README.md`; inspect `AGENTS.md` for whether a short note is needed.
- Gate reminders / profile guidance: inspected-no-change expected; this pass does not change default gates or safe-save rules.
- Legacy entry point: inspect existing legacy-entrypoint test remains valid; do not revive `asset_map-Sync/asset_map_sync.py`.

## Constraints

- Preserve report-first workflow; dry-run remains default.
- Preserve `--apply` safe-save through `save_workbook_safely()`.
- No new dependencies.
- No workbook writes during implementation or tests except temp workbooks in tests.
- Do not infer model identity from folders like `/paint/` or `/int/`; folder names are organizational only.
- Do not add model/RPO-specific exceptions.
- Do not hide ambiguity by picking the first duplicate shared asset.
- Keep active scope based on promoted runtime models from workbook metadata.

## Risks and Non-Goals

Risks:

- A shared bare asset may intentionally be model-specific but placed in a category folder without a model prefix. The mitigation is deterministic reporting and filename-prefix precedence for model-specific overrides.
- Existing reports may show more `insert_filled`/`fill` actions where previously they showed `flag_ambiguous`. This is intended for single bare RPO assets anywhere under `/27vette/`.
- Duplicate category assets for the same RPO must remain visible as review problems.

Non-goals:

- No live WordPress media reorganization.
- No workbook `asset_map` apply in this pass.
- No runtime image rendering change.
- No support for using folder names as model names.
- No blank-row seeding, stale-row deactivation, status-column changes, or legacy sync revival.

## Validation Plan

Run focused Python tests:

```sh
.venv/bin/python -m pytest tests/test_asset_map_sync.py -q
```

Run CLI help guard:

```sh
.venv/bin/python scripts/sync_asset_map.py --help
```

Run a deterministic report-only fixture smoke if the fixture is updated or a temp fixture is created:

```sh
.venv/bin/python scripts/sync_asset_map.py \
  --workbook stingray_master.xlsx \
  --report-dir /tmp/asset-map-sync-shared-folder-smoke \
  --media-url-list tests/fixtures/asset-map-sync-media-urls.txt \
  --no-verify-existing
```

If no fixture update is made, skip the smoke or run it only as a current-behavior check; it should not write the workbook.

Final dirty-tree check:

```sh
git status --short
```

Expected changed files after implementation:

- `scripts/corvette_form_generator/asset_map_sync.py`
- `tests/test_asset_map_sync.py`
- `asset_map-Sync/asset_map_sync.README.md`
- this spec file, updated from spec-only to completed after implementation

## Completion Notes

Completed 2026-06-29 on branch `ingest-wizard`.

Changed files:

- `scripts/corvette_form_generator/asset_map_sync.py`
  - `reconcile()` now prefers model-prefixed media for exact `(model, rpo)` matches.
  - A single bare RPO media URL is now a shared fallback for every matching promoted active model option without an exact model-prefixed candidate.
  - Duplicate bare URLs for the same RPO still produce `bare-ambiguous` / `flag_ambiguous` instead of arbitrary selection.
- `tests/test_asset_map_sync.py`
  - Added coverage for category-folder parsing, shared bare fallback, model-prefixed precedence, and duplicate bare ambiguity.
  - Updated missing-image/unmatched expectations for shared bare fallback behavior.
- `asset_map-Sync/asset_map_sync.README.md`
  - Documented model-prefixed winners, global bare shared fallback behavior, and duplicate-bare ambiguity.
- `.hermes/plans/asset-map-category-folder-matching-spec.md`
  - Updated to Sean's corrected rule and closed with implementation evidence.

Artifacts/workbook/runtime:

- `stingray_master.xlsx`: unchanged.
- `form-output/*`: unchanged.
- `form-app/data.js`: unchanged.
- Runtime JS/CSS/HTML and dealer submission behavior: unchanged.

Gate results:

```sh
.venv/bin/python -m pytest tests/test_asset_map_sync.py -q
# 16 passed in 0.75s

.venv/bin/python scripts/sync_asset_map.py --help
# passed; help renders supported flags

rm -rf /tmp/asset-map-sync-shared-fallback-smoke && \
.venv/bin/python scripts/sync_asset_map.py \
  --workbook stingray_master.xlsx \
  --report-dir /tmp/asset-map-sync-shared-fallback-smoke \
  --media-url-list tests/fixtures/asset-map-sync-media-urls.txt \
  --no-verify-existing
# passed; dry run only; would write 0 URL changes and 0 new rows with the fixture
```

Residual risks / follow-up:

- A real live-media run may now propose more shared bare image fills/inserts than before. Review `asset_map_sync_report.csv` before using `--apply`.
- If duplicate bare files exist for the same RPO anywhere under `/27vette/`, the sync still flags them as ambiguous; resolve by keeping one shared bare file or adding model prefixes.
- A real `--apply` remains a separate workbook-data action: Excel must be closed, then validate workbook package/schema, regenerate active models, and run `generate_registry.py`.
