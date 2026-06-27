# asset_map sync

The old `asset_map-Sync/asset_map_sync.py` entry point is retired because it wrote
`stingray_master.xlsx` directly. Do not run it for maintenance.

Use the safe project command instead:

```sh
.venv/bin/python scripts/sync_asset_map.py --workbook stingray_master.xlsx --report-dir /tmp/asset-map-sync
```

For deterministic review/test runs, avoid live WordPress state and use the
checked-in fixture list:

```sh
.venv/bin/python scripts/sync_asset_map.py --workbook stingray_master.xlsx --report-dir /tmp/asset-map-sync --media-url-list tests/fixtures/asset-map-sync-media-urls.txt --no-verify-existing
```

The supported command:

- defaults to dry-run/report mode;
- resolves default scope from promoted runtime models in `model_registry_promotion`;
- resolves each model's option sheet through `model_workbook_sources`;
- uses stdlib HTTP with an explicit browser-like User-Agent, with optional `WP_USER` / `WP_APP_PASSWORD` only when the public media endpoint requires auth;
- supports deterministic validation with `--media-url-list tests/fixtures/asset-map-sync-media-urls.txt`;
- writes review reports plus `asset_map_sync_manifest.json` to `--report-dir`;
- keeps dry-run/report mode read-only with respect to workbook rows and state files;
- saves workbook changes only when `--apply` is passed, through `save_workbook_safely()`.

Report outputs:

- `asset_map_sync_report.csv`: full reconciliation report.
- `asset_map_missing_images.csv`: review-only list of active/selectable options whose image coverage is missing, ambiguous, or dead with no candidate. This file is for triage; it does not imply blank-row seeding or automatic workbook edits.
- `asset_map_unmatched_media.csv`: uploaded media that did not map to a desired active option target, plus unparseable filenames.
- `asset_map_sync_manifest.json`: run contract with workbook path/sheet, included promoted model option sheets, media source mode, `--since` state handling, existing URL verification mode, action counts, planned URL writes/inserts, missing-image count/path, unmatched media count/path, unparseable filename count, and report paths.

Blank-row seeding, stale-row deactivation, and workbook schema/status-column
changes are not routine asset-map maintenance. They need a separate approved
workbook-data spec before being reintroduced or applied to `stingray_master.xlsx`.

Do not use `--apply` on the canonical workbook from a fresh live media pull. A
real apply requires a reviewed manifest/report and separate approval for the
specific workbook row changes.

After any real workbook apply, run:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Then regenerate affected active models and the registry only if workbook data changed.
