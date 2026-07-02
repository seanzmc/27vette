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
- accepts media anywhere under `/wp-content/uploads/pictures/27vette/`, including
  category subfolders such as `/paint/` or `/int/`;
- treats model-prefixed filenames as model-specific winners (`c-` Stingray,
  `e-` Grand Sport, `h-` Z06, `r-` ZR1, `s-` ZR1X, `g-` Grand Sport X);
- treats a single bare RPO filename as a shared fallback for every promoted
  active model with a matching active/selectable option row when that model has
  no model-prefixed candidate for the RPO;
- flags duplicate bare RPO filenames as ambiguous instead of choosing one by
  folder or API order;
- uses stdlib HTTP with an explicit browser-like User-Agent, with optional `WP_USER` / `WP_APP_PASSWORD` only when the public media endpoint requires auth;
- supports deterministic validation with `--media-url-list tests/fixtures/asset-map-sync-media-urls.txt`;
- writes review reports plus `asset_map_sync_manifest.json` to `--report-dir`;
- keeps dry-run/report mode read-only with respect to workbook rows and state files;
- saves workbook changes only when `--apply` is passed, through `save_workbook_safely()`.

Report outputs:

- `asset_map_sync_report.csv`: full reconciliation report. Every row carries `coverage_intent` (`expected` / `not_expected`) and `coverage_intent_reason`. Policy is universal-expected: every active+selectable option card should eventually carry a visual element, so `not_expected` derives only from structural presentation metadata (`section_master.selection_mode=display_only`, active `section_presentation.standard_equipment_bucket`) — never from media or asset_map coverage state.
- `asset_map_missing_images.csv`: the actionable review queue — missing/ambiguous/dead-no-candidate targets classified `expected`, sorted model → section → target for form-consistency triage. Structurally `not_expected` missing rows are excluded here but remain visible in the broad report CSV with their intent columns populated. This file is for triage; it does not imply blank-row seeding or automatic workbook edits.
- `asset_map_unmatched_media.csv`: uploaded media that did not map to a desired active option target, plus unparseable filenames.
- `asset_map_sync_manifest.json`: run contract with workbook path/sheet, included promoted model option sheets, media source mode, `--since` state handling, existing URL verification mode, action counts, planned URL writes/inserts, actionable missing-image count/path plus `broad_missing_images_count`, a `coverage` block (classifier ruleset version + rules, intent counts, actionable count, per-model/per-section intent breakdown, and `section_coverage` stats: per model × section `total_targets` / `covered` / `missing` / `coverage_pct` over ALL desired option targets — the form-consistency view that converges to 100% as images land), unmatched media count/path, unparseable filename count, and report paths.

Coverage-intent classification is report-only: it never adds or applies workbook rows. The universal-expected policy is product policy encoded as the classifier default; the only workbook-derived classifications are structural presentation facts that self-correct when `section_master` / `section_presentation` change.

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
