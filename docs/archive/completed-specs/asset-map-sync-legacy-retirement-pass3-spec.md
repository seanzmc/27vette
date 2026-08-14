# asset_map-Sync Legacy Retirement Spec (Simplification Pass 3)

Date: 2026-07-05
Status: Completed 2026-07-05. See completion record at end.

## Diagnosis

`asset_map-Sync/asset_map_sync.py` is a retired refusal stub (prints "retired", exits 2); the supported entrypoint is `scripts/sync_asset_map.py` → `corvette_form_generator/asset_map_sync.py`. Verified in the simplification audit (verifier claim 3, PASS). `tests/test_asset_map_sync.py:949-953` (`test_legacy_entrypoint_no_longer_contains_direct_workbook_save`) reads the legacy file as a guard. `asset_map-Sync/asset_map_sync.README.md` documents the LIVE supported workflow (reports, coverage-intent policy, wildcard contract, apply safety) — content must survive.

Live references outside the directory itself: root `README.md:47` dirs list and the guard test only.

## Exact changes

1. `git mv asset_map-Sync/asset_map_sync.README.md docs/asset-map-sync.md` (live workflow doc moves to docs/; opening paragraph adjusted to say the legacy entrypoint was removed, not just retired).
2. `git rm asset_map-Sync/asset_map_sync.py` → directory gone.
3. `tests/test_asset_map_sync.py`: replace `test_legacy_entrypoint_no_longer_contains_direct_workbook_save` with a guard asserting `asset_map-Sync/asset_map_sync.py` does not exist (retired entrypoint must stay gone).
4. Root `README.md:47`: drop `asset_map-Sync` from the reference-dirs list.

## Constraints / non-goals

No changes to the supported sync implementation (`scripts/sync_asset_map.py`, `scripts/corvette_form_generator/asset_map_sync.py`) or its other tests. No workbook writes. Pass 3 only.

## Validation plan

1. `test ! -d asset_map-Sync`.
2. `test -f docs/asset-map-sync.md` staged as R (history preserved).
3. `PYTHONPATH=scripts .venv/bin/python -m pytest tests/test_asset_map_sync.py -q` → pass.
4. `git grep -n "asset_map-Sync"` outside archives/receipts/completed specs → only the new guard test string and doc prose describing the removal.
5. `git diff --check`; independent verifier at closeout.

## Completion record

Implemented 2026-07-05 (staged, not committed). README moved as git rename to `docs/asset-map-sync.md` (opening paragraph updated to "retired and removed"); legacy stub deleted; directory gone; guard test replaced with `test_legacy_entrypoint_stays_removed` asserting absence; root `README.md` dirs line updated.

Validation results (real output):

- `test ! -d asset_map-Sync` → true; `docs/asset-map-sync.md` staged as R.
- `PYTHONPATH=scripts pytest tests/test_asset_map_sync.py -q` → pass (within 36-passed combined run).
- `git grep asset_map-Sync` outside archives/receipts/specs/STATE → only the new guard comment/assertion and the doc's removal prose, as scoped.
- `git diff --check` → clean.

Residual risks / follow-up: staged pending commit approval; none other implied.
