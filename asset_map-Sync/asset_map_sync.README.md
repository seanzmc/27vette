# asset_map sync

The old `asset_map-Sync/asset_map_sync.py` entry point is retired because it wrote
`stingray_master.xlsx` directly. Do not run it for maintenance.

Use the safe project command instead:

```sh
.venv/bin/python scripts/sync_asset_map.py --workbook stingray_master.xlsx --report-dir /tmp/asset-map-sync
```

The supported command:

- defaults to dry-run/report mode;
- resolves default scope from promoted runtime models in `model_registry_promotion`;
- resolves each model's option sheet through `model_workbook_sources`;
- uses stdlib HTTP, with optional `WP_USER` / `WP_APP_PASSWORD` only when the public media endpoint requires auth;
- supports deterministic validation with `--media-url-list tests/fixtures/asset-map-sync-media-urls.txt`;
- writes reports to `--report-dir`;
- saves workbook changes only when `--apply` is passed, through `save_workbook_safely()`.

After any real workbook apply, run:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Then regenerate affected active models and the registry only if workbook data changed.
