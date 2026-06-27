# Asset Map Sync Closure Spec

Status: Implemented on 2026-06-27.
Date: 2026-06-27
Recommended reasoning level for Sean: medium-high

## Request

Close out the remaining `asset_map` sync workflow work after the manifest-backed apply pass by:

1. hardening the live WordPress media fetch path so routine report-only runs do not depend on an ad hoc browser-UA URL-list workaround; and
2. adding a separate reviewer-friendly missing-images artifact for active/selectable options that still lack confident hosted image coverage.

This is a tooling/reporting closure pass. It should not write `stingray_master.xlsx`, regenerate runtime artifacts, or change browser runtime behavior.

## Diagnosis

Current repo/workflow evidence inspected:

- Branch/status preflight at spec time:
  - branch: `asset-map-sync-apply-pass`
  - status: clean relative to `origin/asset-map-sync-apply-pass`.
- Prior specs:
  - `.hermes/plans/asset-map-sync-hardening-spec.md` is implemented and established the safe CLI, stdlib HTTP, promoted-runtime model scope, deterministic `--media-url-list`, and legacy stub.
  - `.hermes/plans/asset-map-sync-module-setup-spec.md` is implemented and established report/manifest/apply separation, removed schema/lifecycle prototype flags, and kept real workbook apply separately reviewed.
  - `.hermes/plans/asset-map-sync-apply-spec.md` is implemented and added exactly 11 approved `asset_map` rows, regenerated Stingray/Grand Sport/registry artifacts, and left two residual follow-ups: live fetch hardening and remaining `flag_missing`/unmatched/unparseable triage.
- Current sync implementation:
  - `scripts/sync_asset_map.py` is a thin wrapper around `corvette_form_generator.asset_map_sync.main`.
  - `scripts/corvette_form_generator/asset_map_sync.py:131` `_open_json()` sends only `Accept: application/json` plus optional `Authorization`.
  - `scripts/corvette_form_generator/asset_map_sync.py:142` `fetch_media()` uses `_open_json()` for paginated WordPress REST media discovery.
  - `scripts/corvette_form_generator/asset_map_sync.py:459` `_write_reports()` writes only the full `asset_map_sync_report.csv` and `asset_map_unmatched_media.csv`.
  - `scripts/corvette_form_generator/asset_map_sync.py:495` `_write_manifest()` records the report and unmatched paths, but not a dedicated missing-images path/count.
  - `scripts/corvette_form_generator/asset_map_sync.py:617` `run_sync()` can stay report-first; no closure work needs to broaden apply behavior.
  - `scripts/corvette_form_generator/asset_map_sync.py:707` CLI help currently exposes only the supported flags: workbook, asset sheet, report dir, media-url-list, apply, timeout, workers, no-verify-existing, and since.
- Current tests:
  - `tests/test_asset_map_sync.py` covers media parsing, promoted-runtime source discovery, missing/ambiguous reporting, safe temp-workbook apply, manifest fields, dry-run no-save/no-state, apply state boundary, CLI help, unsupported prototype flags, and legacy entrypoint retirement.
  - It does not lock a browser-like WordPress request header, an actionable 401/403 fetch error, or a separate missing-images artifact.
- Current docs/guidance:
  - `AGENTS.md:163` correctly describes the safe report-first command, retired legacy stub, deterministic `--media-url-list`, and safe `--apply` boundary.
  - `asset_map-Sync/asset_map_sync.README.md` documents the safe command and manifest, but does not mention a dedicated missing-images artifact.
- Current live/deterministic probes at spec time:
  - Live report-only command now succeeds from this environment:
    - `.venv/bin/python scripts/sync_asset_map.py --workbook stingray_master.xlsx --report-dir /tmp/asset-map-sync-closure-live --no-verify-existing`
    - Result: fetched `165` images under `/wp-content/uploads/pictures/27vette/`, with `keep: 106`, `flag_missing: 345`, `unmatched media: 96`, and `unparseable files: 32`; no workbook writes.
  - Browser-UA standalone REST probe also fetched `165` media URLs and wrote `/tmp/asset-map-sync-closure-browser-ua-media-urls.txt`.
  - Deterministic fixture command succeeds:
    - `.venv/bin/python scripts/sync_asset_map.py --workbook stingray_master.xlsx --report-dir /tmp/asset-map-sync-closure-fixture --media-url-list tests/fixtures/asset-map-sync-media-urls.txt --no-verify-existing`
    - Result: `keep: 106`, `flag_missing: 345`, `unparseable files: 1`, no URL writes/inserts.
  - The live 403 from the apply spec did not reproduce at spec time, but the code still lacks an explicit browser-like `User-Agent` and still relies on the site accepting Python's default request profile. Closing the workflow should make this deterministic and produce an actionable fallback message if the site blocks the request again.

Root cause:

The asset sync workflow is safe and usable, but the remaining reporting ergonomics are incomplete. The live fetch path has no explicit site-policy-compatible request profile or clear 401/403 guidance, and reviewers still have to filter the full CSV to find missing image coverage even though missing-image review is a routine follow-up artifact.

Risk level: Low-to-medium.

Change type: tooling/reporting + tests + docs/spec closure. No workbook data, generated runtime contracts, runtime JS/CSS/HTML, styling, dealer submission behavior, or dependency changes.

## Ownership Decision

- WordPress REST media remains only a candidate URL source for maintenance reports.
- Workbook `stingray_master.xlsx / asset_map` remains the source of truth for runtime image metadata.
- The sync command should emit review artifacts and apply only explicitly approved workbook changes through the existing safe-save path.
- The missing-images artifact is a report, not a command to seed blank `asset_map` rows and not a new workbook-owned product taxonomy.
- Runtime/generator image consumption remains unchanged and generic.

## Exact Files / Sheets / Artifacts To Change

Expected files to change:

1. `scripts/corvette_form_generator/asset_map_sync.py`
   - Add a module-level browser-like `User-Agent` constant for WordPress REST media requests.
   - Send that `User-Agent` from `_open_json()` alongside `Accept: application/json`.
   - Preserve optional `WP_USER` / `WP_APP_PASSWORD` Basic auth behavior without printing secrets.
   - Catch live fetch 401/403 failures and raise/print an actionable error that names:
     - HTTP status;
     - WordPress media endpoint context;
     - optional auth env vars (`WP_USER` / `WP_APP_PASSWORD`) when private media requires auth;
     - deterministic fallback: `--media-url-list <path>`.
   - Do not add `requests`; keep stdlib HTTP.
   - Add a dedicated missing-images report, recommended filename: `asset_map_missing_images.csv`.
   - Include the missing-images path and count in `asset_map_sync_manifest.json`, recommended fields:
     - `missing_images_path`
     - `missing_images_count`
   - Carry enough source context into report rows to make the artifact useful without cross-filtering the main CSV. Recommended fields for the missing-images CSV:
     - `model_key`
     - `source_sheet`
     - `section_id` when present in the option sheet
     - `target_id`
     - `rpo`
     - `option_name`
     - `action`
     - `candidate_source`
     - `image_status`
     - `note`
   - Include at minimum actions that mean active/selectable image coverage needs review:
     - `flag_missing`
     - `flag_ambiguous`
     - `flag_dead_no_match`
   - For incremental runs, exclude `skip_no_candidate_incremental` from the default missing-images artifact unless implementation makes a separate `incremental_missing_images` classification. The artifact should be a review list, not a noisy cursor delta.
   - Do not create blank `asset_map` rows, add status columns, deactivate stale rows, or broaden `--apply`.

2. `tests/test_asset_map_sync.py`
   - Add focused tests for:
     - WordPress JSON requests include the explicit `User-Agent` and `Accept` headers.
     - Optional Basic auth header is still included when `WP_USER` and `WP_APP_PASSWORD` are set, without changing the public unauthenticated default.
     - A simulated HTTP 403/401 from `fetch_media()` produces an actionable message that mentions `--media-url-list`; do not require live network for this test.
     - Dry-run report writes `asset_map_missing_images.csv` when there are `flag_missing` or `flag_ambiguous` rows.
     - The missing-images artifact contains only review-needed missing/ambiguous rows, not `keep`, `insert_filled`, or unmatched-media rows.
     - Manifest records `missing_images_path` and `missing_images_count`.
     - Existing report/apply boundary tests still pass.

3. `asset_map-Sync/asset_map_sync.README.md`
   - Document the live report command as the normal path.
   - Document `asset_map_missing_images.csv` as the easy-reference list for options still missing/ambiguous images.
   - Keep the dry-run/apply boundary explicit.
   - Keep deterministic validation through `--media-url-list` documented.
   - Keep workbook apply warning intact: real canonical-workbook `--apply` requires reviewed report/manifest and separate approval.

4. `.hermes/plans/asset-map-sync-closure-spec.md`
   - On implementation completion, update status, completion date, changed files, gates, live smoke result, residual risks, and next-step guidance.

5. `.hermes/plans/asset-map-sync-apply-spec.md`
   - Companion update after implementation only: append a short historical note that the live-fetch hardening / missing-image artifact follow-up was handled by this closure spec, or explicitly leave the old next-pass section historical.
   - Do not rewrite the completed apply evidence.

Files expected to inspect but not change:

- `AGENTS.md`
  - Expected inspected-no-change unless implementation changes command names, report filenames, or workflow boundaries enough to stale `AGENTS.md:163`.
- `scripts/sync_asset_map.py`
  - Expected inspected-no-change; public CLI path stays stable.
- `asset_map-Sync/asset_map_sync.py`
  - Expected inspected-no-change; legacy hard-fail deprecation stub stays retired.
- `requirements.txt`
  - Expected inspected-no-change; no new dependency.
- `tests/fixtures/asset-map-sync-media-urls.txt`
  - Expected inspected-no-change unless a test needs one extra deterministic URL; prefer temp-workbook/unit fixtures over changing the global fixture.
- `scripts/corvette_form_generator/contract.py`, `production.py`, `inspection.py`, `scripts/generate_registry.py`
  - Expected inspected-no-change; generator/runtime asset consumption already works and should not change in this closure pass.
- `scripts/corvette_form_generator/editor_ops.py`, `tests/test_editor_ops_apply.py`
  - Expected inspected-no-change; workbook-editor gate reminders are not part of this pass.

Workbook sheets to inspect but not write:

- `stingray_master.xlsx / asset_map`
- `stingray_master.xlsx / model_registry_promotion`
- `stingray_master.xlsx / model_workbook_sources`
- active promoted option sheets resolved by metadata: `stingray_options`, `grandSport_options`, `z06_options`

Generated/runtime artifacts that must remain unchanged:

- `form-output/runtime/*.json`
- `form-output/stingray-form-data.json`
- `form-output/stingray-form-data.csv`
- `form-app/data.js`
- runtime source files under `form-app/` other than generated data, which should not be regenerated in this pass.

## Companion-File Impact Matrix

- Workbook/source data — inspected-no-change. No workbook writes, no schema changes, no row inserts/updates/deactivations.
- Generated runtime contracts / registry data — not applicable; must remain unchanged. No generation required.
- Runtime JS/CSS/HTML — not applicable; no runtime behavior or styling change.
- Tests — update `tests/test_asset_map_sync.py` for fetch hardening and missing-images artifact coverage.
- Docs/specs — update `asset_map-Sync/asset_map_sync.README.md`; update this spec on completion; update or explicitly historical-note `.hermes/plans/asset-map-sync-apply-spec.md` so the old residual follow-up does not read like an unhandled current task.
- Gate reminders / worker guidance — inspected-no-change unless `AGENTS.md` or editor reminders become stale; no checked-in `27vette-gate` file exists in repo evidence.
- Dependencies — inspected-no-change; stdlib only.
- Dealer submission / WordPress order endpoint — not applicable. This pass touches WordPress media REST fetch only, not dealer submission endpoint `https://stingraychevroletcorvette.com/wp-json/corvette-build/v1/submit`.

## Implementation Plan

### Phase 0: Preflight

1. Confirm branch/status and no conflicting dirty work:

```sh
git branch --show-current
git status --short --branch
```

2. Confirm current CLI help remains on the supported surface before editing:

```sh
.venv/bin/python scripts/sync_asset_map.py --help
```

Do not implement if the working tree has unrelated dirty files overlapping the expected files above.

### Phase 1: Add deterministic WordPress request behavior

1. In `scripts/corvette_form_generator/asset_map_sync.py`, add a constant similar to:

```python
WORDPRESS_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/125 Safari/537.36 27vette-asset-map-sync/1.0"
```

Exact string can differ, but it must be explicit, stable, and browser-like enough for common WordPress/WAF policies.

2. Update `_open_json()` to include:

```python
headers = {
    "Accept": "application/json",
    "User-Agent": WORDPRESS_USER_AGENT,
}
```

3. Preserve the existing Basic auth header when `_auth_header_from_env()` returns a value.

4. Add a small helper or error wrapper for HTTP 401/403 from live media fetch. The message must be actionable and deterministic, e.g.:

```text
WordPress media fetch failed with HTTP 403 from https://.../wp-json/wp/v2/media. If media is private, set WP_USER/WP_APP_PASSWORD; otherwise use --media-url-list <path> for deterministic report/apply review.
```

5. Keep pagination and 400-after-last-page behavior unchanged.

### Phase 2: Add the missing-images artifact

1. Extend option-sheet read context so missing report rows can include option display context:

- `option_name` (already read as `name`)
- `section_id` when the source option sheet has that column
- existing `source_sheet`

2. Extend report row construction to include the needed values without changing reconciliation semantics.

3. Update `_write_reports()` to write a third CSV:

```text
asset_map_missing_images.csv
```

4. Populate it from report rows where `action` is in the review-needed set:

```python
MISSING_IMAGE_ACTIONS = {"flag_missing", "flag_ambiguous", "flag_dead_no_match"}
```

5. Sort/order should be stable and reviewer-friendly. Recommended order is the same as the main report, which follows promoted model/source option order. If implementation adds a sort, use `(model_key, source_sheet, section_id, rpo, target_id)`.

6. Extend `SyncResult` and manifest writing so the CLI summary and manifest can name the missing artifact. At minimum, include it in the printed `Reports:` block and manifest fields.

7. Do not use missing-images output to create workbook rows or change `asset_map` lifecycle state.

### Phase 3: Tests

Add/update focused tests in `tests/test_asset_map_sync.py` before or alongside implementation:

1. `test_open_json_sends_browser_like_user_agent`
   - Monkeypatch `asset_map_sync.urlopen` with a fake that inspects the `Request` object.
   - Assert `User-Agent` and `Accept` headers are present.
   - Return a fake response with JSON payload and headers.

2. `test_open_json_preserves_optional_basic_auth_header`
   - Use `monkeypatch.setenv()` for `WP_USER` and `WP_APP_PASSWORD`.
   - Assert `Authorization` starts with `Basic `.
   - Do not assert the secret value in failure output.

3. `test_fetch_media_403_mentions_media_url_list_fallback`
   - Simulate an `HTTPError` with code 403 from `_open_json()` or fake opener.
   - Assert the raised/user-facing message includes `HTTP 403` and `--media-url-list`.

4. `test_missing_images_artifact_written_and_manifested`
   - Use temp workbook/report fixtures.
   - Produce at least one `flag_missing` and one `flag_ambiguous` row.
   - Assert `asset_map_missing_images.csv` exists.
   - Assert manifest includes path/count.

5. `test_missing_images_artifact_excludes_keep_insert_and_unmatched`
   - Use a fixture where there is a `keep`, an `insert_filled`, an unmatched media URL, and a `flag_missing`.
   - Assert only the `flag_missing`/`flag_ambiguous`-class rows appear in the missing artifact.

Keep existing temp-workbook safe-apply tests unchanged except for expected manifest/report path fields.

### Phase 4: Docs/spec closure

1. Update `asset_map-Sync/asset_map_sync.README.md` with:

- normal live report command;
- deterministic `--media-url-list` command;
- report outputs:
  - `asset_map_sync_report.csv`
  - `asset_map_missing_images.csv`
  - `asset_map_unmatched_media.csv`
  - `asset_map_sync_manifest.json`
- explicit note that `asset_map_missing_images.csv` is review-only and does not imply blank-row seeding.

2. After implementation and gates, update this spec to `Status: Implemented ...` with evidence.

3. Add a short historical completion note to `.hermes/plans/asset-map-sync-apply-spec.md` under its residual follow-up or recommended next-pass section, pointing to this closure spec. Do not remove the old apply evidence.

## Validation Plan

Required deterministic gates:

```sh
.venv/bin/python -m pytest tests/test_asset_map_sync.py -q
.venv/bin/python -m py_compile scripts/corvette_form_generator/asset_map_sync.py scripts/sync_asset_map.py asset_map-Sync/asset_map_sync.py
.venv/bin/python scripts/sync_asset_map.py --help
rm -rf /tmp/asset-map-sync-closure-fixture
.venv/bin/python scripts/sync_asset_map.py \
  --workbook stingray_master.xlsx \
  --report-dir /tmp/asset-map-sync-closure-fixture \
  --media-url-list tests/fixtures/asset-map-sync-media-urls.txt \
  --no-verify-existing
.venv/bin/python - <<'PY'
from pathlib import Path
import csv, json
report_dir = Path('/tmp/asset-map-sync-closure-fixture')
manifest = json.loads((report_dir / 'asset_map_sync_manifest.json').read_text(encoding='utf-8'))
missing_path = Path(manifest['missing_images_path'])
assert missing_path.exists(), missing_path
rows = list(csv.DictReader(missing_path.open(encoding='utf-8')))
assert manifest['missing_images_count'] == len(rows), manifest
assert rows, 'expected missing-image rows from current fixture/canonical workbook state'
assert {row['action'] for row in rows} <= {'flag_missing', 'flag_ambiguous', 'flag_dead_no_match'}
print(f"missing_images_count={len(rows)}")
PY
git diff --check -- \
  .hermes/plans/asset-map-sync-closure-spec.md \
  .hermes/plans/asset-map-sync-apply-spec.md \
  asset_map-Sync/asset_map_sync.README.md \
  scripts/corvette_form_generator/asset_map_sync.py \
  tests/test_asset_map_sync.py
```

Required no-unwanted-artifact checks:

```sh
git diff --quiet -- stingray_master.xlsx
git diff --quiet -- form-output/runtime form-output/stingray-form-data.json form-output/stingray-form-data.csv form-app/data.js
git diff --quiet -- requirements.txt scripts/sync_asset_map.py asset_map-Sync/asset_map_sync.py
```

Optional live smoke, not a merge gate because it depends on mutable external WordPress/site policy:

```sh
rm -rf /tmp/asset-map-sync-closure-live
.venv/bin/python scripts/sync_asset_map.py \
  --workbook stingray_master.xlsx \
  --report-dir /tmp/asset-map-sync-closure-live \
  --no-verify-existing
```

Expected optional-live outcome after this pass:

- success with a nonzero media count and emitted `asset_map_missing_images.csv`; or
- actionable failure that includes the HTTP status and points to `--media-url-list` / optional `WP_USER` and `WP_APP_PASSWORD`.

Do not run workbook generators for this closure pass unless implementation unexpectedly touches workbook or generated artifacts. If that happens, stop and classify the drift before keeping it.

## Risks

- The live WordPress endpoint is external and mutable. Required gates must stay fixture/fake-network based; live fetch is a smoke test only.
- Adding a browser-like `User-Agent` should be harmless, but some WAFs can still block automation. The actionable fallback message is part of the fix.
- Missing-image counts will change as workbook source rows or media library contents change. Tests should assert artifact shape/filtering, not fixed canonical counts except in a local probe command.
- If the main report CSV schema changes by adding `section_id` / `option_name`, downstream ad hoc consumers may need to tolerate the new columns. No checked-in consumer was found beyond tests, but implementation should keep additive changes only.

## Non-Goals

- No workbook `asset_map` apply.
- No blank-row seeding.
- No stale-row deactivation.
- No `image_status` workbook column.
- No new Python dependency such as `requests`.
- No generator/runtime asset consumption changes.
- No runtime visual changes.
- No dealer submission endpoint/payload/Turnstile changes.
- No image accuracy triage for the 345 currently missing rows; this pass only makes the review artifact easy to consume.

## Rollback

If implementation fails or live fetch behavior regresses:

1. Revert code/test/docs/spec edits from this pass.
2. Confirm `scripts/sync_asset_map.py --media-url-list tests/fixtures/asset-map-sync-media-urls.txt --no-verify-existing` still runs with the pre-pass behavior.
3. Confirm no workbook/generated artifacts changed with the no-unwanted-artifact checks above.

No workbook or runtime rollback should be needed because this pass must not write source data or generated browser artifacts.

## Completion Notes

Implemented on 2026-06-27 after approval.

Changed files:

- `scripts/corvette_form_generator/asset_map_sync.py`
  - Added explicit browser-like `WORDPRESS_USER_AGENT` for WordPress REST media JSON requests.
  - Preserved optional `WP_USER` / `WP_APP_PASSWORD` Basic auth behavior.
  - Added actionable 401/403 live-fetch fallback messaging that points to `--media-url-list <path>`.
  - Added `asset_map_missing_images.csv` report output for `flag_missing`, `flag_ambiguous`, and `flag_dead_no_match` rows.
  - Added `missing_images_path` and `missing_images_count` to `asset_map_sync_manifest.json`.
  - Added option context (`section_id`, `option_name`) to report rows for reviewability.
- `tests/test_asset_map_sync.py`
  - Added tests for WordPress request headers, optional Basic auth preservation, actionable 403 fallback, missing-images artifact creation/filtering, and manifest fields.
- `asset_map-Sync/asset_map_sync.README.md`
  - Documented live report usage, deterministic fixture usage, all report outputs, and the review-only meaning of `asset_map_missing_images.csv`.
- `.hermes/plans/asset-map-sync-apply-spec.md`
  - Added a historical note that this closure spec handles the apply spec's live-fetch/missing-image-report follow-up.
- `.hermes/plans/asset-map-sync-closure-spec.md`
  - Updated from approved spec to implemented completion record.

Preserved / not changed:

- No workbook rows or schema changed.
- No generated runtime artifacts changed.
- No runtime app JS/CSS/HTML changed.
- No new dependency was added; implementation remains stdlib HTTP.
- `scripts/sync_asset_map.py` stayed unchanged.
- `asset_map-Sync/asset_map_sync.py` stayed a retired hard-fail stub.
- Dealer submission endpoint/payload/Turnstile behavior stayed untouched.

Gate results:

```sh
.venv/bin/python -m pytest tests/test_asset_map_sync.py -q
# 15 passed in 0.70s

.venv/bin/python -m py_compile scripts/corvette_form_generator/asset_map_sync.py scripts/sync_asset_map.py asset_map-Sync/asset_map_sync.py
# passed

.venv/bin/python scripts/sync_asset_map.py --help
# passed; supported CLI surface unchanged

rm -rf /tmp/asset-map-sync-closure-fixture
.venv/bin/python scripts/sync_asset_map.py --workbook stingray_master.xlsx --report-dir /tmp/asset-map-sync-closure-fixture --media-url-list tests/fixtures/asset-map-sync-media-urls.txt --no-verify-existing
# passed; keep: 106, flag_missing: 345, unmatched media: 0, unparseable files: 1

.venv/bin/python - <<'PY'
from pathlib import Path
import csv, json
report_dir = Path('/tmp/asset-map-sync-closure-fixture')
manifest = json.loads((report_dir / 'asset_map_sync_manifest.json').read_text(encoding='utf-8'))
missing_path = Path(manifest['missing_images_path'])
assert missing_path.exists(), missing_path
rows = list(csv.DictReader(missing_path.open(encoding='utf-8')))
assert manifest['missing_images_count'] == len(rows), manifest
assert rows, 'expected missing-image rows from current fixture/canonical workbook state'
assert {row['action'] for row in rows} <= {'flag_missing', 'flag_ambiguous', 'flag_dead_no_match'}
print(f"missing_images_count={len(rows)}")
PY
# missing_images_count=345

rm -rf /tmp/asset-map-sync-closure-live
.venv/bin/python scripts/sync_asset_map.py --workbook stingray_master.xlsx --report-dir /tmp/asset-map-sync-closure-live --no-verify-existing
# optional live smoke passed; fetched 165 images; keep: 106, flag_missing: 345, unmatched media: 96, unparseable files: 32

git diff --quiet -- stingray_master.xlsx
git diff --quiet -- form-output/runtime form-output/stingray-form-data.json form-output/stingray-form-data.csv form-app/data.js
git diff --quiet -- requirements.txt scripts/sync_asset_map.py asset_map-Sync/asset_map_sync.py
# passed; no unwanted workbook/generated/dependency/public-wrapper/stub changes
```

Residual risks / follow-up:

- Live WordPress state and WAF policy remain external and mutable; deterministic report/apply review should still use `--media-url-list` when exact candidate stability matters.
- `asset_map_missing_images.csv` reports current missing/ambiguous/dead coverage only; it does not classify image accuracy or approve workbook rows.
- The remaining image work is content triage: review the missing-images report, upload/rename additional WordPress media, then write a future manifest-backed apply spec for any reviewed candidate set.

## Historical Approval Prompt

Approve this asset-map sync closure pass?

Recommended scope: add explicit WordPress REST request headers plus actionable 401/403 fallback, emit `asset_map_missing_images.csv` and manifest fields, update focused tests/docs/spec closure, and run deterministic gates. No workbook apply, no generated artifact refresh, no runtime change, no dependency change.

## Recommended Next Pass After This One

If this closure pass lands cleanly, no further asset-sync tooling pass is implied by current repo evidence. The remaining image work becomes content triage: review `asset_map_missing_images.csv`, upload/rename additional WordPress images, then run a future manifest-backed apply spec only for a reviewed candidate set.
