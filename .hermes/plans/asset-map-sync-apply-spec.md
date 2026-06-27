# Asset Map Sync Apply Spec

Status: Implemented on 2026-06-26.
Date: 2026-06-26
Recommended reasoning level for Sean: high

## Request

Apply the currently reviewable `asset_map` `insert_filled` candidates from the manifest-backed asset sync report, then regenerate the affected active model artifacts and registry as an intentional runtime image rollout.

This is the follow-up pass after `.hermes/plans/asset-map-sync-module-setup-spec.md`. That pass made the sync command report-first, added `asset_map_sync_manifest.json`, removed supported schema/lifecycle-changing prototype flags, and kept real canonical-workbook apply out of scope.

## Diagnosis

Current repo/workflow evidence:

- Branch preflight during spec writing: `main`; `git status --short --branch` reported `## main...origin/main`.
- Current CLI help exposes only the supported report/apply flags:
  - `--workbook`
  - `--asset-sheet`
  - `--report-dir`
  - `--media-url-list`
  - `--apply`
  - `--timeout`
  - `--workers`
  - `--no-verify-existing`
  - `--since`
- Unsupported prototype flags are no longer in supported help:
  - `--status-col`
  - `--deactivate-stale`
  - `--seed-blank-missing`
- Normal live CLI fetch currently failed with `HTTP Error 403: Forbidden` from the WordPress media endpoint when using Python urllib's default user agent.
- A read-only media inventory workaround using the same WordPress REST endpoint with a browser-like `User-Agent` fetched 165 image URLs under `/wp-content/uploads/pictures/27vette/` and wrote `/tmp/asset-map-sync-apply-spec-media-urls.txt`.
- Running the sync command against that URL list produced a manifest-backed report:

```sh
.venv/bin/python scripts/sync_asset_map.py \
  --workbook stingray_master.xlsx \
  --report-dir /tmp/asset-map-sync-apply-spec-report \
  --media-url-list /tmp/asset-map-sync-apply-spec-media-urls.txt \
  --no-verify-existing
```

Report/manifest evidence:

- Manifest: `/tmp/asset-map-sync-apply-spec-report/asset_map_sync_manifest.json`
- CSV report: `/tmp/asset-map-sync-apply-spec-report/asset_map_sync_report.csv`
- Unmatched media report: `/tmp/asset-map-sync-apply-spec-report/asset_map_unmatched_media.csv`
- Manifest fields of interest:
  - `apply: false`
  - `asset_sheet: asset_map`
  - `media_source: media-url-list`
  - `media_url_count: 165`
  - `verify_existing: false`
  - `included_sources`: `stingray_options`, `grandSport_options`, `z06_options`
  - `action_counts`: `keep: 95`, `flag_missing: 345`, `insert_filled: 11`
  - `url_write_count: 0`
  - `insert_count: 11`
  - `unmatched_count: 96`
  - `unparseable_count: 32`
  - `state_written: false`

Root cause / opportunity:

The workbook `asset_map` currently lacks active rows for 11 promoted-model selectable option images where the hosted media filenames provide confident matches. The sync report can now identify those insert candidates without mutating the workbook. Applying them would add option-card images for five Stingray brake-caliper choices and six Grand Sport hash-mark choices.

Risk level: Medium.

Change type: workbook source-data + generated runtime artifacts + tests/gates. Runtime logic, styling, pricing, option availability, rules, dealer submission behavior, and dependencies must not change.

## Ownership Decision

- Workbook `stingray_master.xlsx / asset_map` owns runtime image metadata.
- WordPress media remains a candidate URL source, not a runtime source of truth.
- The apply pass should add only reviewed `asset_map` rows for exact approved `(model_key, target_type, target_id)` keys.
- Generated runtime artifacts under `form-output/` and `form-app/data.js` should be regenerated from workbook source rows and reviewed as an intentional image-field rollout.
- Runtime JavaScript should remain generic and unchanged; it already renders generated image fields.

## Candidate Classification

All candidates below currently have no existing `asset_map` row for their exact `(model_key, option, target_id)` key. `image_alt` should be copied from the workbook option name by the sync apply code, with `image_fit=cover`, `image_position=center`, `active=True`, and `notes=auto-seeded`.

Visual spot-check evidence:

- A contact sheet was created at `/tmp/asset-map-sync-apply-spec-candidates-contact.jpg` from the 11 candidate URLs.
- Visual review found no obvious wrong-image class. The five Stingray candidates show wheel/brake-caliper closeups; the six Grand Sport candidates show rear-quarter hash marks in the expected color families.
- Two red caliper/hash-mark variants are visually close to each other; confidence is still acceptable because their filenames/RPOs match the candidate rows, but exact Bright Red vs Edge Red and Torch Red vs Red Mist color nuance should get a manual spot check before final approval/deploy.

| # | Model | Source sheet row | Target option | RPO | Option name | Section | Candidate URL | Match source | Confidence | Customer impact / note |
|---|---|---:|---|---|---|---|---|---|---|---|
| 1 | Stingray | `stingray_options:4` | `opt_j6a_001` | `J6A` | Black Painted Calipers | `sec_cali_001` | `https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/c-j6a-c.png` | prefixed | High | Adds brake-caliper option image; black caliper is visually subtle but matches the wheel/caliper class and prefixed Stingray/RPO filename. |
| 2 | Stingray | `stingray_options:5` | `opt_j6f_001` | `J6F` | Bright Red-Painted Calipers | `sec_cali_001` | `https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/c-j6f-c.png` | prefixed | High | Adds visible red caliper image. Manual spot check should confirm red shade, but filename is exact/prefixed. |
| 3 | Stingray | `stingray_options:6` | `opt_j6e_001` | `J6E` | Velocity Yellow-Painted Calipers | `sec_cali_001` | `https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/c-j6e-c.png` | prefixed | High | Adds visible yellow caliper image; strong visual/RPO match. |
| 4 | Stingray | `stingray_options:7` | `opt_j6n_001` | `J6N` | Edge Red-Painted Calipers | `sec_cali_001` | `https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/c-j6n-c.png` | prefixed | Medium-high | Adds red caliper image. Manual spot check should confirm Edge Red vs Bright Red nuance; filename is exact/prefixed. |
| 5 | Stingray | `stingray_options:8` | `opt_j6b_001` | `J6B` | Blue-Painted Calipers | `sec_cali_001` | `https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/c-j6b.png` | prefixed | High | Adds visible blue caliper image; strong visual/RPO match. |
| 6 | Grand Sport | `grandSport_options:63` | `opt_17a_001` | `17A` | Blade Silver Hash Marks | `sec_gsha_001` | `https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/17a.png` | bare-unique | High | Adds Grand Sport hash-mark image; silver/gray visual match. Bare filename is acceptable because report classified the RPO as unique to Grand Sport in promoted scope. |
| 7 | Grand Sport | `grandSport_options:64` | `opt_20a_001` | `20A` | Admiral Blue Hash Marks | `sec_gsha_001` | `https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/20a.png` | bare-unique | High | Adds Grand Sport hash-mark image; blue visual match. |
| 8 | Grand Sport | `grandSport_options:65` | `opt_55a_001` | `55A` | Competition Yellow Hash Marks. | `sec_gsha_001` | `https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/55a.png` | bare-unique | High | Adds Grand Sport hash-mark image; yellow visual match. Do not fix the trailing period in option copy in this pass. |
| 9 | Grand Sport | `grandSport_options:66` | `opt_75a_001` | `75A` | Torch Red Hash Marks | `sec_gsha_001` | `https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/75a.png` | bare-unique | High | Adds Grand Sport hash-mark image; red visual match. Manual spot check should confirm red shade. |
| 10 | Grand Sport | `grandSport_options:67` | `opt_97a_001` | `97A` | Carbon Flash Hash Marks | `sec_gsha_001` | `https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/97a.png` | bare-unique | High | Adds Grand Sport hash-mark image; black/dark visual match. |
| 11 | Grand Sport | `grandSport_options:68` | `opt_dx4_001` | `DX4` | Red Mist Hash Marks | `sec_gsha_001` | `https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/dx4.png` | bare-unique | Medium-high | Adds Grand Sport hash-mark image; darker red visual match. Manual spot check should confirm Red Mist vs Torch Red nuance. |

Workbook source-row inspection before spec writing:

- `stingray_options` rows 4-8 are active/selectable caliper options with display orders 10-50 and no existing `asset_map` row for their candidate keys.
- `grandSport_options` rows 63-68 are active/selectable hash-mark options with display orders 10-60 and no existing `asset_map` row for their candidate keys.
- No candidate is in Z06 scope.
- No candidate requires a workbook schema change.

## Exact Files / Sheets / Artifacts To Change

Expected files/sheets to change during implementation:

1. `stingray_master.xlsx / asset_map`
   - Add exactly 11 rows, one for each approved candidate above.
   - Expected row fields:
     - `model_key`: `stingray` or `grand_sport`
     - `target_type`: `option`
     - `target_id`: candidate option id
     - `image_url`: candidate URL
     - `image_alt`: workbook option name
     - `image_fit`: `cover`
     - `image_position`: `center`
     - `active`: `TRUE` / boolean true following existing sheet convention
     - `notes`: `auto-seeded`
   - Do not edit existing `asset_map` rows.
   - Do not add `image_status` or any schema column.
   - Do not deactivate stale rows.
   - Do not seed blank rows.

2. Generated runtime artifacts from affected active models:
   - `form-output/runtime/stingray-runtime-contract.json`
   - `form-output/runtime/grand-sport-runtime-contract.json`
   - any model-specific generated JSON/CSV files that `scripts/generate_form.py --model stingray` and `--model grand_sport` intentionally rewrite, including `form-output/stingray-form-data.json` and `form-output/stingray-form-data.csv` for Stingray compatibility.
   - `form-app/data.js` after `scripts/generate_registry.py`.

3. Owning spec on completion:
   - `.hermes/plans/asset-map-sync-apply-spec.md`
   - Mark implemented, record workbook rows changed, generated artifact diffs reviewed, gates run, manual verification, and residual follow-up.

Files expected to inspect but not change:

- `scripts/corvette_form_generator/asset_map_sync.py`
  - Expected inspected-no-change unless implementation discovers the apply path cannot safely reproduce the reviewed plan.
- `tests/test_asset_map_sync.py`
  - Expected inspected-no-change unless the apply command behavior differs from the module-setup tests.
- `asset_map-Sync/asset_map_sync.README.md`
  - Expected inspected-no-change; current README already says real apply requires reviewed report and separate approval.
- `AGENTS.md`
  - Expected inspected-no-change; current asset image maintenance guidance remains accurate.
- `scripts/corvette_form_generator/contract.py`
  - Expected inspected-no-change. It already loads active `asset_map` rows and exposes `option_asset_map()`.
- `scripts/corvette_form_generator/production.py`
  - Expected inspected-no-change. It already merges `option_assets` into generated choices.
- `scripts/corvette_form_generator/inspection.py`
  - Expected inspected-no-change unless Grand Sport generated/draft asset propagation fails.
- `scripts/generate_registry.py`
  - Expected inspected-no-change. It publishes regenerated promoted artifacts and model assets generically.
- `tests/grand-sport-draft-data.test.mjs`, `tests/multi-model-runtime-switching.test.mjs`, `tests/stingray-form-regression.test.mjs`, `tests/stingray-generator-stability.test.mjs`
  - Expected inspected-no-change unless existing assertions need to explicitly allow the intentional new image fields.

Generated artifacts that must not change except for approved image-field additions and timestamps:

- Z06 runtime artifacts.
- Runtime logic files under `form-app/` other than generated `form-app/data.js`.
- Dealer payload/submission behavior.

## Implementation Plan

### Phase 0: Approval and clean preflight

Do not implement until Sean approves this spec.

After approval:

1. Check branch/status and confirm no conflicting dirty files:

```sh
git status --short --branch
git branch --show-current
```

2. Check workbook lock and package before any write:

```sh
python3 - <<'PY'
from pathlib import Path
lock = Path('~$stingray_master.xlsx')
if lock.exists():
    raise SystemExit(f'Excel lock file exists: {lock}')
print('no workbook lock file')
PY
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
```

3. Recreate or reuse a reviewed media URL list. If normal live CLI fetch still returns 403, use the browser-UA URL-list workaround and document that the manifest `media_source` will be `media-url-list`:

```sh
python3 - <<'PY'
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode
import json
out = Path('/tmp/asset-map-sync-apply-approved-media-urls.txt')
endpoint = 'https://stingraychevroletcorvette.com/wp-json/wp/v2/media'
path_filter = '/wp-content/uploads/pictures/27vette/'
ua = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/125 Safari/537.36'
urls = []
page = 1
while True:
    params = {'per_page': 100, 'page': page, '_fields': 'source_url', 'media_type': 'image'}
    req = Request(endpoint + '?' + urlencode(params), headers={'Accept': 'application/json', 'User-Agent': ua})
    with urlopen(req, timeout=30) as resp:
        batch = json.loads(resp.read().decode('utf-8'))
        total_pages = int(resp.headers.get('x-wp-totalpages', page))
    for item in batch:
        url = (item.get('source_url') or '').strip()
        if path_filter in url:
            urls.append(url)
    if page >= total_pages:
        break
    page += 1
out.write_text('\n'.join(urls) + '\n', encoding='utf-8')
print(out)
print(len(urls))
PY
```

### Phase 1: Rebuild reviewed dry-run report and stop on drift

Run a fresh dry-run report from the exact media list that will be used for apply:

```sh
rm -rf /tmp/asset-map-sync-apply-approved-dry-run
.venv/bin/python scripts/sync_asset_map.py \
  --workbook stingray_master.xlsx \
  --report-dir /tmp/asset-map-sync-apply-approved-dry-run \
  --media-url-list /tmp/asset-map-sync-apply-approved-media-urls.txt \
  --no-verify-existing
```

Then run this executable allowlist probe before any workbook save and capture its output in the implementation handoff. The probe must fail unless all of these are true:

- Manifest has `apply: false`.
- Manifest has `url_write_count: 0`.
- Manifest has `insert_count: 11`.
- The `insert_filled` set exactly matches the 11 candidate `(model_key, source_sheet, target_id, rpo, new_url)` rows in this spec.
- No exact candidate key already exists in `asset_map`.
- Each source option row is still active/selectable and has the same option name/source row intent listed above.
- No Z06 candidate appears.

```sh
.venv/bin/python - <<'PY'
from __future__ import annotations

import csv
import json
from pathlib import Path

from openpyxl import load_workbook

REPORT_DIR = Path('/tmp/asset-map-sync-apply-approved-dry-run')
WORKBOOK = Path('stingray_master.xlsx')
EXPECTED = {
    ('stingray', 'stingray_options', 'opt_j6a_001', 'j6a', 'https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/c-j6a-c.png'): ('Black Painted Calipers', 'sec_cali_001'),
    ('stingray', 'stingray_options', 'opt_j6f_001', 'j6f', 'https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/c-j6f-c.png'): ('Bright Red-Painted Calipers', 'sec_cali_001'),
    ('stingray', 'stingray_options', 'opt_j6e_001', 'j6e', 'https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/c-j6e-c.png'): ('Velocity Yellow-Painted Calipers', 'sec_cali_001'),
    ('stingray', 'stingray_options', 'opt_j6n_001', 'j6n', 'https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/c-j6n-c.png'): ('Edge Red-Painted Calipers', 'sec_cali_001'),
    ('stingray', 'stingray_options', 'opt_j6b_001', 'j6b', 'https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/c-j6b.png'): ('Blue-Painted Calipers', 'sec_cali_001'),
    ('grand_sport', 'grandSport_options', 'opt_17a_001', '17a', 'https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/17a.png'): ('Blade Silver Hash Marks', 'sec_gsha_001'),
    ('grand_sport', 'grandSport_options', 'opt_20a_001', '20a', 'https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/20a.png'): ('Admiral Blue Hash Marks', 'sec_gsha_001'),
    ('grand_sport', 'grandSport_options', 'opt_55a_001', '55a', 'https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/55a.png'): ('Competition Yellow Hash Marks.', 'sec_gsha_001'),
    ('grand_sport', 'grandSport_options', 'opt_75a_001', '75a', 'https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/75a.png'): ('Torch Red Hash Marks', 'sec_gsha_001'),
    ('grand_sport', 'grandSport_options', 'opt_97a_001', '97a', 'https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/97a.png'): ('Carbon Flash Hash Marks', 'sec_gsha_001'),
    ('grand_sport', 'grandSport_options', 'opt_dx4_001', 'dx4', 'https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/dx4.png'): ('Red Mist Hash Marks', 'sec_gsha_001'),
}

manifest = json.loads((REPORT_DIR / 'asset_map_sync_manifest.json').read_text(encoding='utf-8'))
assert manifest['apply'] is False, manifest
assert manifest['insert_count'] == 11, manifest
assert manifest['url_write_count'] == 0, manifest

rows = list(csv.DictReader((REPORT_DIR / 'asset_map_sync_report.csv').open(encoding='utf-8')))
insert_rows = [row for row in rows if row['action'] == 'insert_filled']
actual = {
    (row['model_key'], row['source_sheet'], row['target_id'], row['rpo'], row['new_url'])
    for row in insert_rows
}
assert actual == set(EXPECTED), sorted(actual ^ set(EXPECTED))
assert not any(row['model_key'] == 'z06' for row in insert_rows), insert_rows

wb = load_workbook(WORKBOOK, read_only=True, data_only=True)
try:
    asset_ws = wb['asset_map']
    asset_headers = [cell.value for cell in next(asset_ws.iter_rows(min_row=1, max_row=1))]
    asset_idx = {header: i for i, header in enumerate(asset_headers)}
    existing_keys = {
        (
            str(row[asset_idx['model_key']] or '').strip(),
            str(row[asset_idx['target_type']] or '').strip(),
            str(row[asset_idx['target_id']] or '').strip(),
        )
        for row in asset_ws.iter_rows(min_row=2, values_only=True)
    }
    for model_key, source_sheet, target_id, rpo, url in EXPECTED:
        assert (model_key, 'option', target_id) not in existing_keys, (model_key, target_id)
        ws = wb[source_sheet]
        headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
        idx = {header: i for i, header in enumerate(headers)}
        matches = [row for row in ws.iter_rows(min_row=2, values_only=True) if row[idx['option_id']] == target_id]
        assert len(matches) == 1, (source_sheet, target_id, len(matches))
        row = matches[0]
        expected_name, expected_section = EXPECTED[(model_key, source_sheet, target_id, rpo, url)]
        assert str(row[idx['rpo']]).lower() == rpo, (target_id, row[idx['rpo']], rpo)
        assert row[idx['option_name']] == expected_name, (target_id, row[idx['option_name']], expected_name)
        assert row[idx['section_id']] == expected_section, (target_id, row[idx['section_id']], expected_section)
        assert row[idx['active']] is True, (target_id, row[idx['active']])
        assert row[idx['selectable']] is True, (target_id, row[idx['selectable']])
finally:
    wb.close()

print('dry-run allowlist probe passed: exact 11 insert_filled candidates, no pre-existing asset_map keys')
PY
```

If the allowlist probe fails, stop and refresh this spec instead of applying.

### Phase 2: Safe apply only after approval and dry-run parity

Run the apply command against the same media URL list:

```sh
rm -rf /tmp/asset-map-sync-apply-approved-apply
.venv/bin/python scripts/sync_asset_map.py \
  --workbook stingray_master.xlsx \
  --report-dir /tmp/asset-map-sync-apply-approved-apply \
  --media-url-list /tmp/asset-map-sync-apply-approved-media-urls.txt \
  --no-verify-existing \
  --apply
```

Immediately verify the saved workbook on disk:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Then run this post-apply manifest/read-back probe and capture its output. It must prove the apply manifest still reports `insert_count: 11` and `url_write_count: 0`, and that the workbook now contains exactly the 11 approved active option rows with no duplicate active `(model_key, target_type, target_id)` keys:

```sh
.venv/bin/python - <<'PY'
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from openpyxl import load_workbook

REPORT_DIR = Path('/tmp/asset-map-sync-apply-approved-apply')
WORKBOOK = Path('stingray_master.xlsx')
EXPECTED = {
    ('stingray', 'option', 'opt_j6a_001'): ('https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/c-j6a-c.png', 'Black Painted Calipers'),
    ('stingray', 'option', 'opt_j6f_001'): ('https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/c-j6f-c.png', 'Bright Red-Painted Calipers'),
    ('stingray', 'option', 'opt_j6e_001'): ('https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/c-j6e-c.png', 'Velocity Yellow-Painted Calipers'),
    ('stingray', 'option', 'opt_j6n_001'): ('https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/c-j6n-c.png', 'Edge Red-Painted Calipers'),
    ('stingray', 'option', 'opt_j6b_001'): ('https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/c-j6b.png', 'Blue-Painted Calipers'),
    ('grand_sport', 'option', 'opt_17a_001'): ('https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/17a.png', 'Blade Silver Hash Marks'),
    ('grand_sport', 'option', 'opt_20a_001'): ('https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/20a.png', 'Admiral Blue Hash Marks'),
    ('grand_sport', 'option', 'opt_55a_001'): ('https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/55a.png', 'Competition Yellow Hash Marks.'),
    ('grand_sport', 'option', 'opt_75a_001'): ('https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/75a.png', 'Torch Red Hash Marks'),
    ('grand_sport', 'option', 'opt_97a_001'): ('https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/97a.png', 'Carbon Flash Hash Marks'),
    ('grand_sport', 'option', 'opt_dx4_001'): ('https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/dx4.png', 'Red Mist Hash Marks'),
}

manifest = json.loads((REPORT_DIR / 'asset_map_sync_manifest.json').read_text(encoding='utf-8'))
assert manifest['apply'] is True, manifest
assert manifest['insert_count'] == 11, manifest
assert manifest['url_write_count'] == 0, manifest

wb = load_workbook(WORKBOOK, read_only=True, data_only=True)
try:
    ws = wb['asset_map']
    headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
    idx = {header: i for i, header in enumerate(headers)}
    active_keys = []
    rows_by_key = {}
    for excel_row, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        key = tuple(str(row[idx[field]] or '').strip() for field in ('model_key', 'target_type', 'target_id'))
        active = row[idx['active']] is True or str(row[idx['active']]).strip().lower() == 'true'
        if active and all(key):
            active_keys.append(key)
            rows_by_key[key] = (excel_row, row)
    duplicates = [key for key, count in Counter(active_keys).items() if count > 1]
    assert not duplicates, duplicates
    for key, (url, alt) in EXPECTED.items():
        assert key in rows_by_key, key
        excel_row, row = rows_by_key[key]
        assert row[idx['image_url']] == url, (excel_row, key, row[idx['image_url']], url)
        assert row[idx['image_alt']] == alt, (excel_row, key, row[idx['image_alt']], alt)
        assert row[idx['image_fit']] == 'cover', (excel_row, key, row[idx['image_fit']])
        assert row[idx['image_position']] == 'center', (excel_row, key, row[idx['image_position']])
        assert str(row[idx['notes']] or '').strip() == 'auto-seeded', (excel_row, key, row[idx['notes']])
finally:
    wb.close()

print('post-apply read-back probe passed: exact 11 approved asset_map rows present, no duplicate active keys')
PY
```

### Phase 3: Regenerate affected artifacts

Because the approved rows affect Stingray and Grand Sport option cards only, regenerate those two active models and publish the registry:

```sh
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_registry.py
```

Do not regenerate Z06 unless a validation failure proves it is needed. If unrelated generated artifacts change, classify the drift and restore it unless it is required by this approved image rollout.

### Phase 4: Review generated image diffs as intentional rollout

Before running broader gates that may rewrite artifacts, snapshot the relevant generated outputs:

```sh
mkdir -p /tmp/asset-map-sync-apply-baseline
# Use git show or cp pre-apply files before generation during implementation.
```

After generation, review diffs and prove the only intentional payload changes are image-field additions for the approved candidate options plus timestamps/expected generated metadata churn. Capture either the output of the executable probe below, or equivalent reviewer output that lists the changed JSON paths and proves the same constraint.

Expected image-field additions:

- Stingray choices for:
  - `opt_j6a_001`
  - `opt_j6f_001`
  - `opt_j6e_001`
  - `opt_j6n_001`
  - `opt_j6b_001`
- Grand Sport choices for:
  - `opt_17a_001`
  - `opt_20a_001`
  - `opt_55a_001`
  - `opt_75a_001`
  - `opt_97a_001`
  - `opt_dx4_001`

The review should assert:

- No option/rule/pricing/default-selection/dealer payload fields changed because of this pass.
- New image fields are sourced from active workbook `asset_map` rows.
- Z06 payloads are unchanged except for any timestamp-only output caused by a required gate.
- `form-app/data.js` embeds the regenerated Stingray and Grand Sport image fields after `generate_registry.py`.

Use this generated-diff probe after saving pre-generation baselines for the files under `/tmp/asset-map-sync-apply-baseline/` with the same relative names. The probe fails on any non-image-field change outside timestamps/expected generated metadata and fails if any approved image field is missing from the generated artifacts:

```sh
.venv/bin/python - <<'PY'
from __future__ import annotations

import json
from pathlib import Path

BASELINE = Path('/tmp/asset-map-sync-apply-baseline')
ROOT = Path('.')
APPROVED = {
    'stingray': {
        'opt_j6a_001': 'https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/c-j6a-c.png',
        'opt_j6f_001': 'https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/c-j6f-c.png',
        'opt_j6e_001': 'https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/c-j6e-c.png',
        'opt_j6n_001': 'https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/c-j6n-c.png',
        'opt_j6b_001': 'https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/c-j6b.png',
    },
    'grand_sport': {
        'opt_17a_001': 'https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/17a.png',
        'opt_20a_001': 'https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/20a.png',
        'opt_55a_001': 'https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/55a.png',
        'opt_75a_001': 'https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/75a.png',
        'opt_97a_001': 'https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/97a.png',
        'opt_dx4_001': 'https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/dx4.png',
    },
}
ALLOWED_IMAGE_FIELDS = {'image_url', 'image_alt', 'image_fit', 'image_position'}
IGNORED_LEAF_NAMES = {'generated_at', 'generated_at_utc', 'generatedAt', 'timestamp'}
FILES = [
    Path('form-output/runtime/stingray-runtime-contract.json'),
    Path('form-output/runtime/grand-sport-runtime-contract.json'),
    Path('form-output/stingray-form-data.json'),
]

def walk(value, path=()):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from walk(child, path + (str(key),))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk(child, path + (f'[{index}]',))
    else:
        yield path, value

def indexed_choices(doc):
    result = {}
    def visit(value):
        if isinstance(value, dict):
            option_id = value.get('option_id')
            if option_id:
                result.setdefault(option_id, []).append(value)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(doc)
    return result

def allowed_change(path):
    leaf = path[-1] if path else ''
    return leaf in IGNORED_LEAF_NAMES or leaf in ALLOWED_IMAGE_FIELDS

for rel in FILES:
    before = json.loads((BASELINE / rel).read_text(encoding='utf-8'))
    after = json.loads((ROOT / rel).read_text(encoding='utf-8'))
    before_flat = dict(walk(before))
    after_flat = dict(walk(after))
    changed = {path for path in before_flat.keys() | after_flat.keys() if before_flat.get(path) != after_flat.get(path)}
    disallowed = sorted(path for path in changed if not allowed_change(path))
    assert not disallowed, [('.'.join(path), before_flat.get(path), after_flat.get(path)) for path in disallowed[:20]]
    model_key = 'grand_sport' if 'grand-sport' in rel.name else 'stingray'
    choices = indexed_choices(after)
    for option_id, expected_url in APPROVED[model_key].items():
        assert option_id in choices, (rel, option_id)
        urls = {choice.get('image_url') for choice in choices[option_id]}
        non_empty_urls = {url for url in urls if url}
        assert expected_url in non_empty_urls, (rel, option_id, urls, expected_url)
        assert non_empty_urls == {expected_url}, (rel, option_id, urls, expected_url)
    print(f'{rel}: {len(changed)} changed leaf path(s), all limited to image fields/timestamps')

registry_text = Path('form-app/data.js').read_text(encoding='utf-8')
for model_expected in APPROVED.values():
    for option_id, expected_url in model_expected.items():
        assert option_id in registry_text, option_id
        assert expected_url in registry_text, expected_url

print('generated-diff probe passed: generated changes limited to approved image fields/timestamps and registry contains approved URLs')
PY
```

### Phase 5: Browser/manual smoke

Because this is an intentional customer-facing image rollout, run a lightweight local browser smoke after generation:

```sh
cd form-app
../.venv/bin/python -m http.server 8000
```

Open `http://localhost:8000` and manually verify:

- Stingray brake-caliper option cards show the five new images.
- Grand Sport hash-mark option cards show the six new images.
- Model switching still works.
- Option selection/deselection still works for the touched sections.
- Browser console has no JavaScript errors.

If browser smoke is not run, state that manual visual verification is pending.

## Companion-File Impact Matrix

- Workbook/source data — update required. `stingray_master.xlsx / asset_map` gets exactly 11 approved rows.
- Generated runtime contracts — update required for Stingray and Grand Sport. Review and retain only approved image-field diffs plus timestamps/expected generated metadata.
- Registry/browser data — update required. Run `scripts/generate_registry.py` and review `form-app/data.js` as the intentional image rollout surface.
- Runtime JS/CSS/HTML — inspected-no-change expected. Existing runtime renders generated image fields generically.
- Tests — inspected-no-change expected unless stale assertions fail. Run focused Stingray, Grand Sport, and multi-model tests.
- Sync module/tests — inspected-no-change expected. This pass uses the existing report/apply command; it should not change sync behavior.
- Dependencies — not applicable / no change.
- Docs/specs — update required for this spec on completion. `asset_map-Sync/asset_map_sync.README.md` and `AGENTS.md` inspected-no-change expected.
- Gate reminders / worker guidance — inspected-no-change expected. No checked-in `27vette-gate` file was found during module-setup work; do not edit Hermes profile skills from this repo pass.
- Count/ID-sensitive generated tests — inspect failures if any test encodes stale generated-contract counts or absence of image fields for touched IDs; update only when the old expectation is proven stale against the current generated contract.

## Constraints

- Preserve workbook source-of-truth ownership for image metadata.
- Do not make WordPress media a runtime source of truth.
- Do not add dependencies.
- Do not run sync automatically from `generate_form.py` or `generate_registry.py`.
- Do not edit generated artifacts directly.
- Do not change option labels, copy, pricing, availability, rules, default selections, dealer submission endpoint, payload shape, Turnstile behavior, or runtime selection logic.
- Do not include inactive/future ZR1/ZR1X sheets in default sync scope.
- Do not create blank `asset_map` rows for every active/selectable option.
- Do not add `image_status`, new asset-map columns, a new workbook sheet, a review taxonomy, or a parallel media database.
- Do not deactivate stale `asset_map` rows.
- Do not apply any candidate outside the 11-row allowlist in this spec.
- Do not treat the 345 `flag_missing`, 96 unmatched media, or 32 unparseable files as cleanup scope for this pass.

## Non-Goals

- No broad image coverage push.
- No stale-row cleanup.
- No unmatched media cleanup.
- No unparseable filename cleanup.
- No WordPress upload/write/delete behavior.
- No live fetch hardening for the 403/default-user-agent issue unless a separate tooling pass approves it.
- No wildcard/shared asset-row migration.
- No interior/context-choice/layered visualizer media expansion.
- No option copy cleanup, including the trailing period in `Competition Yellow Hash Marks.`.

## Validation Plan

Preflight / dry-run review:

```sh
git status --short --branch
git branch --show-current
python3 - <<'PY'
from pathlib import Path
lock = Path('~$stingray_master.xlsx')
if lock.exists():
    raise SystemExit(f'Excel lock file exists: {lock}')
print('no workbook lock file')
PY
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/sync_asset_map.py --workbook stingray_master.xlsx --report-dir /tmp/asset-map-sync-apply-approved-dry-run --media-url-list /tmp/asset-map-sync-apply-approved-media-urls.txt --no-verify-existing
```

Apply and workbook validation after approval:

```sh
.venv/bin/python scripts/sync_asset_map.py --workbook stingray_master.xlsx --report-dir /tmp/asset-map-sync-apply-approved-apply --media-url-list /tmp/asset-map-sync-apply-approved-media-urls.txt --no-verify-existing --apply
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Generation:

```sh
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_registry.py
```

Focused tests:

```sh
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Post-gate drift checks:

```sh
git diff --check -- .hermes/plans/asset-map-sync-apply-spec.md asset_map-Sync/asset_map_sync.README.md AGENTS.md scripts/corvette_form_generator/asset_map_sync.py tests/test_asset_map_sync.py
git status --short
git diff -- form-output/runtime form-output/stingray-form-data.json form-output/stingray-form-data.csv form-app/data.js
git diff -- stingray_master.xlsx
```

Manual/browser smoke:

```sh
cd form-app
../.venv/bin/python -m http.server 8000
```

Then verify the touched option cards visually and check the browser console.

## Risks

- The live WordPress REST endpoint currently blocks default Python urllib requests with 403, so the implementation may need to use a reviewed `--media-url-list` snapshot unless a separate tooling fix is approved.
- Applying from a fresh live media list without the allowlist probe could pick up additional media-library changes. Stop if the candidate set drifts.
- The Grand Sport candidates are `bare-unique` rather than model-prefixed. They are acceptable only because the current report finds them unique in promoted-model scope; if that uniqueness changes, stop.
- Red color variants are visually close. Manual spot check should confirm red shade before deployment.
- Generated artifact diffs are intentional for image fields but should not mask unrelated product/rule/pricing drift.

## Rollback

If apply succeeds but generated review or smoke fails:

1. Revert the 11 added `asset_map` rows through a safe workbook edit path or restore the workbook from the safe-save backup produced by `save_workbook_safely()`.
2. Validate workbook package/schema after rollback.
3. Regenerate Stingray, Grand Sport, and registry back to the prior source state.
4. Restore generated artifacts from git if the workbook rollback is not retained.

No runtime-code rollback should be needed because runtime code is out of scope.

## Completion Notes

Implemented on 2026-06-26 after approval.

Changed files/sheets/artifacts:

- `stingray_master.xlsx / asset_map`
  - Added exactly 11 approved active option rows: five Stingray brake-caliper image rows and six Grand Sport hash-mark image rows.
  - No existing `asset_map` rows were edited, no schema/status column was added, no stale rows were deactivated, and no blank option inventory rows were seeded.
- Generated artifacts:
  - `form-output/runtime/stingray-runtime-contract.json`
  - `form-output/runtime/grand-sport-runtime-contract.json`
  - `form-output/stingray-form-data.json`
  - `form-output/stingray-form-data.csv`
  - `form-app/data.js`
- `tests/stingray-generator-stability.test.mjs`
  - Updated stale Stingray generated-contract rule and price-rule count expectations from `141`/`45` to the already-current generated contract counts `145`/`49`. `HEAD:form-output/stingray-form-data.json` already had `rules: 145` and `priceRules: 49`; this was not caused by the asset-map rows, but the focused gate was stale and failed until updated.
- `.hermes/plans/asset-map-sync-apply-spec.md`
  - Recorded implementation results and gate evidence.

Preflight and dry-run evidence:

- Created branch `asset-map-sync-apply-pass` from up-to-date `main` (`HEAD...origin/main` was `0 0`).
- Confirmed no Excel lock file before workbook write.
- `.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx` passed before apply.
- Created `/tmp/asset-map-sync-apply-approved-media-urls.txt` with 165 WordPress media URLs under `/wp-content/uploads/pictures/27vette/` using the documented browser-UA workaround for the live urllib 403.
- Dry-run command passed:
  - `.venv/bin/python scripts/sync_asset_map.py --workbook stingray_master.xlsx --report-dir /tmp/asset-map-sync-apply-approved-dry-run --media-url-list /tmp/asset-map-sync-apply-approved-media-urls.txt --no-verify-existing`
  - Summary: `keep: 95`, `flag_missing: 345`, `insert_filled: 11`, `unmatched media: 96`, `unparseable files: 32`.
- Dry-run allowlist probe passed: exact 11 `insert_filled` candidates, no Z06 rows, and no pre-existing exact `asset_map` keys.

Apply and workbook validation evidence:

- Apply command passed:
  - `.venv/bin/python scripts/sync_asset_map.py --workbook stingray_master.xlsx --report-dir /tmp/asset-map-sync-apply-approved-apply --media-url-list /tmp/asset-map-sync-apply-approved-media-urls.txt --no-verify-existing --apply`
  - Result: `APPLIED: 0 url change(s), 11 row insert(s).`
  - Safe-save backup: `backups/stingray_master-20260626-220800.xlsx`.
- `.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx` passed after apply.
- `.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx` passed after apply.
- Post-apply read-back probe passed: exact 11 approved `asset_map` rows present with expected URL/alt/fit/position/notes and no duplicate active keys.

Generation and generated-diff evidence:

- Regenerated affected active models and registry:
  - `.venv/bin/python scripts/generate_form.py --model stingray`
  - `.venv/bin/python scripts/generate_form.py --model grand_sport`
  - `.venv/bin/python scripts/generate_registry.py`
- Generated-diff probe passed:
  - `form-output/runtime/stingray-runtime-contract.json`: 121 changed leaf paths, all limited to image fields/timestamps.
  - `form-output/runtime/grand-sport-runtime-contract.json`: 145 changed leaf paths, all limited to image fields/timestamps.
  - `form-output/stingray-form-data.json`: 121 changed leaf paths, all limited to image fields/timestamps.
  - `form-app/data.js` contains the approved option IDs and URLs.
- Additional CSV check passed: `form-output/stingray-form-data.csv` contains the five approved Stingray caliper image filenames.

Gate results:

- Focused Node gates passed sequentially:
  - `node --test tests/stingray-form-regression.test.mjs` (`87` pass)
  - `node --test tests/stingray-generator-stability.test.mjs` (`14` pass)
  - `node --test tests/grand-sport-contract-preview.test.mjs` (`6` pass)
  - `node --test tests/grand-sport-draft-data.test.mjs` (`19` pass)
  - `node --test tests/multi-model-runtime-switching.test.mjs` (`46` pass)

Browser smoke:

- Served `form-app` locally with `../.venv/bin/python -m http.server 8000`.
- Browser smoke passed:
  - Stingray Wheels & Brake Calipers step rendered all five new caliper images.
  - Grand Sport Stripes step rendered all six new hash-mark images.
  - Model switching to Grand Sport worked.
  - Grand Sport hash-mark selection/deselection worked for `opt_20a_001`.
  - Browser console had no JavaScript errors.

Companion-file impact:

- Workbook/source data — updated exactly as approved.
- Generated runtime contracts — updated for Stingray and Grand Sport image fields only, plus generated timestamps/metadata.
- Registry/browser data — updated through `scripts/generate_registry.py`.
- Runtime JS/CSS/HTML — inspected-no-change; no runtime source files changed.
- Tests — updated `tests/stingray-generator-stability.test.mjs` for a stale generated-contract count gate unrelated to the image rollout.
- Sync module/tests — inspected-no-change; no sync code changed.
- Dependencies — not applicable / no change.
- Docs/specs — this spec updated; `asset_map-Sync/asset_map_sync.README.md` and `AGENTS.md` were not changed.
- Gate reminders / worker guidance — not applicable; no checked-in `27vette-gate` file exists in the repo, and Hermes profile skills were not edited.

Residual risks / follow-up:

- Live WordPress media fetch from the sync CLI still returns 403 with the default Python urllib user agent; this pass used the reviewed media-url-list workflow instead of changing sync fetch behavior.
  - Historical note: the follow-up closure spec `.hermes/plans/asset-map-sync-closure-spec.md` handles the live-fetch hardening and dedicated missing-images artifact.
- Red shade distinctions remain visually close; the browser smoke verified images render but did not independently certify color accuracy beyond filename/RPO and visual class.
- The remaining `flag_missing`, unmatched media, and unparseable filename rows remain out of scope for this apply pass; the closure spec adds a report artifact for that triage surface.

## Historical Approval Prompt

Approve this narrow manifest-backed `asset_map` apply pass?

Recommended scope: apply exactly the 11 reviewed image rows, regenerate Stingray + Grand Sport + registry, review generated image diffs as intentional, and run focused gates plus browser smoke. No stale cleanup, no schema change, no runtime logic change, no dependency change, no broader image coverage push.

## Recommended Next Pass After This One

After this apply pass lands and visual smoke is complete, the next safe pass is either:

A. a small live-fetch hardening spec for the WordPress REST 403/default-user-agent issue, if the team wants routine live reports to work without a separate media-url-list workaround; or
B. a separate report-only image coverage triage for the remaining `flag_missing`, unmatched, and unparseable rows.

Recommendation: choose A first if asset-map sync will be reused soon; otherwise defer both until another concrete image rollout is needed.
