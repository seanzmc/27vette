# src/ Images Retirement Spec (Simplification Pass 5)

Date: 2026-07-05
Status: Completed 2026-07-05. See completion record at end.

## Diagnosis

`src/` holds exactly 44 tracked PNGs (~28 MB) and nothing else. Zero tracked files reference any `src/<filename>` path — the runtime uses WordPress-hosted media URLs from workbook `asset_map` rows, not repo-local images. Verified in the simplification audit (verifier claim 4, PASS: `git grep 'src/2-'`, `'src/j57'`, `'nga-s.png'` all 0 hits).

Only live mention of the directory is root `README.md:47` ("reference/archive/visualizer surfaces" dirs list).

## Exact changes

1. `git rm src/*.png` (all 44) → `src/` gone. Deletion, not archive: 28 MB of binaries stay recoverable from git history; the canonical media inventory lives in WordPress + workbook `asset_map`, so repo copies are redundant.
2. Root `README.md:47`: drop `src/` from the reference-dirs list (single line shared with Pass 3's `asset_map-Sync` removal).

## Constraints / non-goals

No workbook `asset_map` changes. No media uploads/deletes on WordPress. No other directory cleanups. Pass 5 only.

## Validation plan

1. `git ls-files src/ | wc -l` → 0; `test ! -d src`.
2. `git grep -nE "src/[A-Za-z0-9_-]+\.png"` → no tracked references (confirms nothing broke).
3. `git diff --check`; independent verifier at closeout.

## Completion record

Implemented 2026-07-05 (staged, not committed). All 44 PNGs removed via git rm; `src/` gone; root `README.md` dirs line updated.

Validation results (real output):

- `git ls-files src/ | wc -l` → 0; `ls src` → "No such file or directory".
- `git grep -E 'src/[A-Za-z0-9_-]+\.png'` → no matches (nothing referenced them; nothing broke).
- `git diff --check` → clean.

Residual risks / follow-up: staged pending commit approval. Binaries remain recoverable from git history; canonical media inventory is WordPress + workbook `asset_map`.
