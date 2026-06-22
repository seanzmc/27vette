# asset_map_sync

Seeds and maintains the `asset_map` sheet of `stingray_master.xlsx`, and refreshes
each option's image URL from the WordPress.com media library. One script does both
the initial build (empty/partial sheet) and ongoing maintenance (deltas only) — the
behavior is driven entirely by the state it finds, so it is safe to run repeatedly.

---

## 1. What it does

For every Corvette option that is **active and selectable**, `asset_map` should hold
exactly one row, and that row's `image_url` should point at the live image in the
media library. This module makes that true in a single idempotent pass:

- inserts a row for any active+selectable option missing from `asset_map`
- fills/refreshes `image_url` from the media library
- replaces URLs that have gone dead (404)
- flags options whose image is missing or ambiguous
- flags rows whose option is no longer active+selectable (stale), without deleting them

It never rebuilds `asset_map` from scratch — curation columns (`image_alt`,
`image_fit`, `image_position`, `notes`) are preserved on existing rows.

---

## 2. Data model

Three inputs, each the source of truth for exactly one thing:

| Source | Owns | Key fields |
| --- | --- | --- |
| `{model}_options` sheets | which rows should exist | `option_id`, `rpo`, `active`, `selectable`, `option_name` |
| WordPress media library | the URL value | `source_url` under `/wp-content/uploads/pictures/27vette/` |
| `asset_map` sheet | display curation | `image_alt`, `image_fit`, `image_position`, `notes`, `active` |

Two distinct join keys:

- **`asset_map` row ↔ option:** `asset_map.target_id == {model}_options.option_id`
  (identical format, e.g. `opt_eyt_001`).
- **option/row ↔ media:** `(model_key, rpo)`, where `rpo` is read from the option
  sheet's `rpo` column (authoritative) and the media side's RPO is parsed from the
  filename.

```
 {model}_options sheets             WP media library
 (active AND selectable)            (/pictures/27vette/**)
        | option_id, rpo, name             | source_url
        v                                  v
   desired set  ------- join on -------  media index
   (model, target_id)  (model, rpo)     exact[(model, rpo)]   <- prefixed files
        |                                bare[rpo]            <- unprefixed files
        |                                       |
        +------------------ reconcile() ---------+
                                 |  keep / fill / replace_404 /
                                 |  insert / stale / flag
                                 v
                      asset_map sheet  +  two CSV reports
```

---

## 3. Filename → (model, rpo) parsing

Media filenames are inconsistent; the parser normalizes them. Order of operations on
the lowercased URL basename (extension stripped):

1. **Strip `imgi_<n>_` scrape prefix** if present: `imgi_47_379` → `379`.
2. **Detect model prefix** — a single letter `c/e/h/r/s/g` **followed by a hyphen**:
   `h-stx` → model `z06`, stem `stx`. A leading letter with **no hyphen** is part of
   the RPO, not a model indicator (`hzp` → RPO `hzp`). This distinction is load-bearing;
   do not "simplify" it away.
3. **Take the first token** as the RPO, splitting on `-` or `_`, and require exactly
   3 alphanumerics. Trailing qualifiers are discarded: `c-j6n-c` → `j6n`,
   `c-qe6_v1` → `qe6`, `h-j6n-23x10-cp` → `j6n`.

Model letter map:

| Letter | model_key |
| --- | --- |
| `c` | `stingray` |
| `e` | `grand_sport` |
| `h` | `z06` |
| `r` | `zr1` |
| `s` | `zr1x` |
| `g` | `grand_sport_x` |

(E-Ray is discontinued and intentionally unmapped.)

---

## 4. Matching & URL resolution

For a row `(model, rpo)`, a candidate image is resolved in this order:

1. **Prefixed exact match** — a file parsed as `(model, rpo)` (e.g. `h-stx.png` for a
   z06 row). Highest confidence.
2. **Bare unique** — an unprefixed file for `rpo` where exactly one model still needs
   it. "Needs it" = the set of models with an active+selectable option for that RPO,
   **minus** any model that already has a prefixed file. If that leftover set is exactly
   this row's model, the bare file is assigned.
3. **Bare ambiguous** — an unprefixed file for an `rpo` claimed by more than one
   eligible model. Left unassigned and flagged; the fix is to add a `c/e/h/r/s/g`
   prefix to the filename. The script never guesses here.

Given a candidate, the row's URL is reconciled against what's already there:

| Existing `image_url` | Candidate found | Result |
| --- | --- | --- |
| live (2xx/3xx) | — | **keep** (existing URL trusted) |
| dead (404 / unreachable) | yes | **replace_404** |
| dead | no | flag (`flag_dead_no_match`) |
| blank | yes | **fill** |
| blank | no | flag (`flag_missing` / `flag_ambiguous`) |

Existing-URL liveness is checked with a `HEAD` request (falling back to `GET` on 405),
run concurrently. Skip with `--no-verify-existing`.

---

## 5. Row lifecycle

- **Insert** — desired option with no `asset_map` row → a new row is appended.
  Defaults: `image_url` = matched candidate or blank, `image_alt` = `option_name`,
  `image_fit` = `cover`, `image_position` = `center`, `active` = `TRUE`,
  `notes` = `auto-seeded`.
- **Update** — existing row: only `image_url` (and optionally `image_status`) is
  touched. Curation columns are never overwritten.
- **Stale** — `asset_map` option row whose option is no longer active+selectable →
  flagged `stale_option`. The row, URL, and notes are left intact unless
  `--deactivate-stale` is passed (which sets `active = FALSE`). Rows are never deleted.

---

## 6. CLI reference

```
python asset_map_sync.py --workbook PATH [options]
```

| Flag | Default | Purpose |
| --- | --- | --- |
| `--workbook PATH` | required | Path to `stingray_master.xlsx` |
| `--asset-sheet NAME` | `asset_map` | Target sheet |
| `--apply` | off (dry run) | Write changes; without it, nothing is written |
| `--report-dir DIR` | `.` | Where the CSV reports (and `--since auto` cursor) are written |
| `--since DATE` | off | Incremental: only media modified after `DATE` (`YYYY-MM-DD`/ISO), or `auto` for a saved, self-advancing cursor |
| `--status-col` | off | Maintain an `image_status` column in `asset_map` |
| `--deactivate-stale` | off | Set `active = FALSE` on stale rows |
| `--no-verify-existing` | off | Skip 404-checking existing URLs |
| `--timeout SECS` | `10` | Per-request timeout |
| `--workers N` | `16` | Concurrency for URL liveness checks |

Default runs are a **dry run**: two CSV reports are produced and nothing is written.
`--apply` backs the workbook up to `*.bak` before saving.

---

## 7. Environment & dependencies

```bash
pip install requests openpyxl
export WP_USER="wordpress-login-username"          # login name, not display name/email
export WP_APP_PASSWORD="xxxx xxxx xxxx xxxx xxxx xxxx"   # WP application password; spaces ok
```

The app password authenticates Basic auth against
`https://stingraychevroletcorvette.com/wp-json/wp/v2/media`.

---

## 8. Output

### `asset_map_sync_report.csv`
One row per reconciled/considered option, columns:
`scope, model_key, target_id, rpo, action, candidate_source, existing_url, new_url, image_status, note`.

`action` vocabulary:

| action | meaning |
| --- | --- |
| `keep` | existing URL live, untouched |
| `fill` | blank URL populated |
| `replace_404` | dead URL replaced |
| `insert_filled` / `insert_blank` / `insert_ambiguous` | new row appended (with / without / pending-disambiguation URL) |
| `stale_option` | option no longer active+selectable |
| `flag_missing` / `flag_dead_no_match` / `flag_ambiguous` | needs attention |
| `dead_no_match_incremental` / `skip_no_candidate_incremental` | suppressed flag on an incremental run (image was outside the window) |

`image_status` values (also written in-sheet with `--status-col`):
`ok`, `missing`, `url_dead`, `ambiguous`, `stale_option`.

### `asset_map_unmatched_media.csv`
Library files not assigned to any row: source URL, parsed model/RPO, and reason
(no desired option for that `(model, rpo)`, or filename didn't yield a 3-char RPO).

---

## 9. Configuration (constants near the top of the module)

| Constant | Role |
| --- | --- |
| `OPTION_SHEETS` | maps each `{model}_options` sheet name → `model_key`. Add `zr1_options`, `zr1x_options`, `grandSportX_options` rows as those sheets land. Missing sheets are skipped silently. |
| `MODEL_PREFIX` | filename letter → `model_key` |
| `PATH_FILTER` | media path scope (`/wp-content/uploads/pictures/27vette/`, subfolders included) |
| `TARGET_TYPE` | which `asset_map` rows are managed (`option`); `model`-type rows are left alone |
| `NEW_ROW_FIT` / `NEW_ROW_POSITION` / `NEW_ROW_NOTE` | defaults stamped on inserted rows |

---

## 10. Operational modes

- **Build (first run):** run with no `--since`. Every active+selectable option is
  seeded and URLs filled. Review the dry-run report, then `--apply`.
- **Maintenance (recurring):** `--since auto --apply`, hooked into the form-generation
  pipeline. Pulls only recently modified media, adds rows for newly-active options,
  refreshes changed URLs, flags drop-outs. Run a periodic **full** sync (no `--since`)
  for complete coverage checking, since incremental runs suppress missing/dead flags
  for images outside the pull window.

---

## 11. Safety

- Dry run is the default; writes require `--apply`.
- `--apply` always writes a `*.bak` backup first.
- Stale options are flagged, not deleted; curation columns are never overwritten.
- The `image_status` column is only added when `--status-col` is passed, so the
  existing schema is untouched by default.

---

## 12. Integration notes (for wiring)

- **Invocation:** pure CLI; call as a subprocess from the form-generation scripts.
  Exits non-zero with a message on missing credentials, a missing target sheet, or
  missing required columns; exits 0 otherwise. Check the return code.
- **Importable core:** `reconcile(desired, exact, bare, existing_rows, alive, incremental)`
  is a pure function (no I/O) returning report rows, URL writes, inserts, status map,
  and used-media set — usable directly if you'd rather drive it in-process than shell out.
  `read_option_sheets(wb)`, `build_media_index(urls)`, and `parse_media(url)` are
  likewise side-effect-free and unit-testable.
- **Ordering in the pipeline:** run as a maintenance step *before* the `data.js` emit so
  the freshest URLs are materialized in `asset_map` when the build reads the workbook.
- **Reports:** land in `--report-dir`; the `--since auto` cursor (`.asset_map_sync_state.json`)
  lives there too and advances only on `--apply`.

---

## 13. Known limitations

- `model`-type `asset_map` rows are out of scope (base-car images aren't RPO-keyed).
  Folding them in requires their naming convention and a parser branch.
- Bare-RPO files shared across models require a model-letter prefix to disambiguate;
  until then they're flagged, not assigned.
- The live network path (auth + pagination) is validated by the first real dry run;
  the parser, matching, reconcile, and read/write paths are covered by an end-to-end
  test against a synthetic workbook.
