# asset_map sync

The old `asset_map-Sync/asset_map_sync.py` entry point was retired and removed
because it wrote `stingray_master.xlsx` directly.

For routine media maintenance, use the complete guarded workflow:

```sh
.venv/bin/python scripts/sync_asset_map.py --complete
```

That one command pulls a stable uncached live inventory, applies every
unambiguous URL replacement and filled insert together, validates the workbook,
regenerates every affected promoted model, republishes `form-app/data.js`, and
increments the `data.js` cache version in `form-app/index.html`. Reports and the
media-revision baseline live in ignored `.asset-map-sync/`.

For a read-only live diagnostic, omit `--complete`:

```sh
.venv/bin/python scripts/sync_asset_map.py
```

For deterministic review/test runs, avoid live WordPress state and use the
checked-in fixture list:

```sh
.venv/bin/python scripts/sync_asset_map.py --workbook stingray_master.xlsx --report-dir /tmp/asset-map-sync --media-url-list tests/fixtures/asset-map-sync-media-urls.txt --no-verify-existing
```

The supported command:

- defaults to dry-run/report mode;
- provides `--complete` as the routine canonical-workbook operation instead of
  selectively applying hand-picked URLs;
- sends cache-bypass headers and requires two identical full WordPress snapshots
  before a complete write;
- collapses duplicate WordPress attachment records that expose the same physical
  URL, so one media file cannot become a false ambiguity;
- resolves default scope from promoted runtime models in `model_registry_promotion`;
- resolves each model's option sheet through `model_workbook_sources`;
- accepts media anywhere under `/wp-content/uploads/pictures/27vette/`, including
  category subfolders such as `/paint/` or `/int/`;
- treats model-prefixed filenames as model-specific winners (`c-` Stingray,
  `e-` Grand Sport, `h-` Z06, `r-` ZR1, `s-` ZR1X, `g-` Grand Sport X);
- accepts any multi-model prefix made from two or more distinct model codes,
  such as `e-g-j6d.webp` or `h-s-r-j6d.webp`; the file is shared by every
  named model, and the narrowest matching group wins when multiple groups
  contain the same model and RPO;
- after exact and shared-model prefixes are absent, resolves configured model fallbacks
  before considering a bare shared filename: Grand Sport → Stingray, Grand
  Sport X → Grand Sport → Stingray, and ZR1 / ZR1X → Z06;
- treats a single bare RPO filename as a shared fallback for every promoted
  active model with a matching active/selectable option row when that model has
  no exact or configured fallback-model candidate for the RPO;
- resolves option media in exact single-model → narrowest shared group →
  configured model fallback → bare generic order, and flags duplicate files
  at the highest available priority as ambiguous instead of silently falling
  through or choosing one by folder or API order;
- uses stdlib HTTP with an explicit browser-like User-Agent, with optional `WP_USER` / `WP_APP_PASSWORD` only when the public media endpoint requires auth;
- supports deterministic validation with `--media-url-list tests/fixtures/asset-map-sync-media-urls.txt`;
- writes review reports plus `asset_map_sync_manifest.json` to `--report-dir`;
- keeps dry-run/report mode read-only with respect to workbook rows and state files;
- saves workbook changes only when `--apply` or `--complete` is passed, through
  `save_workbook_safely()`;
- records WordPress attachment modification times after a successful complete
  run. If a later run sees the same URL with a new modification time, it adds a
  stable `asset_rev` query token so browsers/CDNs fetch the revised image;
- stops ambiguous candidates at the report boundary while continuing to apply
  every independent unambiguous match.

Report outputs:

- `asset_map_sync_report.csv`: full reconciliation report. Every row carries `coverage_intent` (`expected` / `not_expected`) and `coverage_intent_reason`. Policy is universal-expected: every active+selectable option card should eventually carry a visual element, so `not_expected` derives only from structural presentation metadata (`section_master.selection_mode=display_only`, active `section_presentation.standard_equipment_bucket`) — never from media or asset_map coverage state.
- `asset_map_missing_images.csv`: the actionable review queue — missing/ambiguous/dead-no-candidate targets classified `expected`, sorted model → section → target for form-consistency triage. Structurally `not_expected` missing rows are excluded here but remain visible in the broad report CSV with their intent columns populated. This file is for triage; it does not imply blank-row seeding or automatic workbook edits.
- `asset_map_unmatched_media.csv`: uploaded media that did not map to a desired active option target, plus unparseable filenames.
- `asset_map_sync_manifest.json`: run contract with workbook path/sheet, included promoted model option sheets, media source mode, `--since` state handling, existing URL verification mode, action counts, planned URL writes/inserts, actionable missing-image count/path plus `broad_missing_images_count`, a `coverage` block (classifier ruleset version + rules, intent counts, actionable count, per-model/per-section intent breakdown, and `section_coverage` stats: per model × section `total_targets` / `covered` / `missing` / `coverage_pct` over ALL desired option targets — the form-consistency view that converges to 100% as images land), unmatched media count/path, unparseable filename count, and report paths.

Coverage-intent classification is report-only: it never adds or applies workbook rows. The universal-expected policy is product policy encoded as the classifier default; the only workbook-derived classifications are structural presentation facts that self-correct when `section_master` / `section_presentation` change.

Wildcard (shared) asset_map rows:

- `asset_map` supports `model_key="*"` rows for `target_type=option` only. The
  generator load path (`contract.py:load_asset_map`) loads wildcard rows first
  and overlays exact-model rows second, so an exact row always wins for the
  same `(target_type, target_id)`. Blank `model_key` stays invalid; wildcard
  rows for `model` / `context_choice` targets are rejected by
  `validate_workbook_schema.py` (`invalid_wildcard_asset_map_row`).
- Sync treats a wildcard row as coverage for every promoted model desiring the
  target: such targets report `keep` (never `insert_filled`), and section
  coverage stats count them as covered. This is the anti-undo contract — a
  sync run must not re-insert per-model rows for wildcard-covered targets.
- Dry-run and low-level `--apply` never write, edit, or insert wildcard rows.
  Complete mode may update one existing wildcard URL only when every promoted
  model resolves the same single bare generic candidate. Model-prefixed or
  otherwise divergent candidates remain `wildcard_conflict`; complete mode
  never creates wildcard rows.
- A wildcard row is reported `stale_target` only when NO promoted model
  desires the target.
- Wildcard authoring (including migrating repeated identical per-model rows to
  shared rows) is a separate approved workbook-data pass, not sync maintenance.

Blank-row seeding, stale-row deactivation, and workbook schema/status-column
changes are not routine asset-map maintenance. They need a separate approved
workbook-data spec before being reintroduced or applied to `stingray_master.xlsx`.

Use `--complete` for canonical live maintenance. Low-level `--apply` remains for
deterministic fixtures or an explicitly reviewed diagnostic report; it does not
perform stable discovery, safe wildcard replacement, generation, publication,
or cache-version updates.

After a low-level `--apply`, run:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Then regenerate affected active models and the registry only if workbook data
changed. Complete mode performs those steps automatically and rolls the workbook
plus generated/publication files back if its post-save pipeline fails.

## Card sizing and alignment

Media matching and card presentation are separate workbook concerns. The sync
updates `image_url`; it intentionally preserves an existing row's
`image_fit` and `image_position`.

Use the guarded display command to change presentation by RPO. It previews by
default and resolves shared (`model_key="*"`) rows only once:

```sh
.venv/bin/python scripts/set_asset_display.py --rpo AQ9 --rpo AH2 --fit contain
.venv/bin/python scripts/set_asset_display.py --rpo AQ9 --rpo AH2 --fit contain --write
```

`image_fit` controls sizing: `cover` fills and may crop, while `contain` keeps
the whole image visible. `image_position` is alignment within that sizing mode,
so `center` is not the opposite of `contain`. Change alignment independently
when needed:

```sh
.venv/bin/python scripts/set_asset_display.py --rpo <RPO> --position top
```

Repeat `--model <model_key>` to restrict a change; without it, the command
resolves every promoted active model. The command updates existing active
asset rows only, routes writes through the guarded editor-operation pipeline,
and fails closed for unknown RPOs, unpromoted model keys, workbook drift, Excel
locks, package/schema failures, or duplicate active asset rows. As with sync,
review the dry-run before adding `--write`, then regenerate affected models and
the registry.
