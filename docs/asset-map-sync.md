# Keep form pictures in sync

The form does not guess which picture belongs to which option. That pairing lives
in the workbook sheet `asset_map`. This command compares that sheet with the
pictures already uploaded to the website and reports — or, when you ask it to,
writes — the obvious one-to-one matches.

You do not need to know Python. You do need Excel closed, and you should read
the report before writing anything.

The command to run is `scripts/sync_asset_map.py`. An older folder named
`asset_map-Sync/` is gone on purpose. Do not recreate it.

## Start here

From the repo root, with Excel closed:

```sh
# Look first. This does not change the workbook.
.venv/bin/python scripts/sync_asset_map.py

# After the report looks right, do the full live update.
.venv/bin/python scripts/sync_asset_map.py --complete
```

`--complete` is the normal live job. One command:

1. Pulls a fresh picture list from the website a few times and writes only
   after two back-to-back lists match. If they never match, it stops without
   writing.
2. Updates every obvious picture match in `stingray_master.xlsx`.
3. Checks the saved workbook.
4. Rebuilds every promoted model that actually changed.
5. Republishes `form-app/data.js`.
6. Bumps the `data.js?v=` number in `form-app/index.html` so browsers pick up
   the new bundle.

Both the look-first run and `--complete` write reports into `.asset-map-sync/`.
That folder is local review output, not source data. Ask for `--help` any time
you want the live flag list.

## What this is for

Think of three piles:

- **The form** needs a picture for each live card: option, model, coupe, and
  convertible.
- **The workbook** stores the official URL for each of those cards.
- **The website** already has the uploaded files under
  `/wp-content/uploads/pictures/27vette/`, including subfolders such as
  `/paint/` or `/int/`.

This command lines those piles up. It does **not** upload pictures, delete
pictures, or change how a card is cropped. It only updates picture URLs in
`asset_map` when the match is unambiguous.

A 3-character option code such as `J6D` is an **RPO**. The filename is how the
command decides which picture belongs to which RPO.

## Everyday workflow

1. Close `stingray_master.xlsx`. If a lock file named `~$stingray_master.xlsx`
   is present, Excel still has the workbook open.
2. Run the look-first command above.
3. Open `.asset-map-sync/asset_map_sync_manifest.json` for the totals, then
   `.asset-map-sync/asset_map_missing_images.csv` for the work queue.
4. Fix leftover problems in the media library or by renaming files. Do not
   hand-edit generated form files to paper over a missing picture.
5. When the leftover problems are only "we still need a picture" or "a person
   has to choose between two files," run `--complete`. The command will apply
   every obvious match and leave the rest in the report.
6. If `--complete` fails after it has already saved the workbook, it puts the
   workbook and generated files back. Do not keep using a half-updated tree.

A look-first run is always safe. `--complete` writes the live workbook, so
review the report first.

## How pictures get matched

The command only looks at current **promoted** models: rows in
`model_registry_promotion` that are both active and promoted to the runtime
form. Each of those models points at its option sheet through
`model_workbook_sources`.

It then asks: which cards should have a picture?

- Every **active and selectable** option row
- The model card itself
- Coupe and convertible body-style cards

Inactive or non-selectable option rows are ignored.

### Option pictures

Name the file from the RPO, then add a model prefix only when the picture is
not meant for every model.

| Filename | Meaning |
|---|---|
| `j6d.webp` | Shared fallback for every promoted model that has RPO `J6D` |
| `c-j6d.webp` | Stingray only |
| `e-j6d.webp` | Grand Sport only |
| `h-j6d.webp` | Z06 only |
| `r-j6d.webp` | ZR1 only |
| `s-j6d.webp` | ZR1X only |
| `g-j6d.webp` | Grand Sport X only |
| `e-g-j6d.webp` | Shared by Grand Sport and Grand Sport X |
| `h-s-r-j6d.webp` | Shared by Z06, ZR1X, and ZR1 |

A WordPress `imgi_12_` prefix on the filename is ignored. `imgi_12_c-j6d.webp`
is treated the same as `c-j6d.webp`. A shared prefix must name each model only
once: `e-g-j6d.webp` is valid, `e-e-j6d.webp` is not.

The command tries matches in this order and **stops at the first level that
has any file**:

1. Exact one-model prefix (`c-`, `e-`, `h-`, `r-`, `s-`, `g-`)
2. The narrowest shared group that names this model. `e-g-j6d.webp` beats
   `c-e-g-j6d.webp` for Grand Sport.
3. A configured fallback model, when this model has no file of its own:
   Grand Sport can use Stingray; Grand Sport X can use Grand Sport, then
   Stingray; ZR1 and ZR1X can use Z06.
4. A bare shared filename such as `j6d.webp`

If that winning level has **one** file, the match is used. If it has **two or
more**, the command reports the card as ambiguous and does not quietly pick
one, fall through to a lower level, or choose by folder or upload order.

Two WordPress attachment records that point at the exact same URL count as one
file, not as a conflict.

### Model cards and body-style cards

Model-card files use the model name, not an RPO:

`stingray`, `grand-sport` / `grandSport`, `z06`, `zr1`, `zr1x`,
`grand-sport-x` / `grandSportX`

Body-style files use a short code:

| Filename | Meaning |
|---|---|
| `c07-1.webp` | Stingray coupe, main picture |
| `c07-2.webp` | Stingray coupe, hover picture |
| `c67-1.webp` | Stingray convertible, main picture |
| `e07-1.webp` | Grand Sport coupe, main picture |

`07` is coupe, `67` is convertible. `1` is the main image, `2` is the hover
image. The leading letter is the same model prefix used for options.

## What the command will change

When a match is obvious, a write run can:

- Fill a blank `image_url` on an existing row (`fill`)
- Replace an existing URL with the current website file (`replace_canonical`)
- Add a new `asset_map` row that already has a URL (`insert_filled`)
- On `--complete` only, update one existing shared `model_key="*"` URL when
  every promoted model agrees on the same bare filename
  (`replace_shared_canonical`)

New rows are marked active, noted `auto-seeded`, and default to `cover` /
`center`. Existing rows keep the crop and alignment they already have.

The command keeps going when some cards are ambiguous. Those stay in the
report. Clear matches are still applied.

## What the command will not do

- Upload, rename, or delete website pictures
- Change card crop or alignment (`image_fit` / `image_position`)
- Create shared `model_key="*"` rows
- Turn old rows off
- Insert blank placeholder rows
- Invent a picture when two files could both be right
- Touch inactive models or non-selectable option rows

Turning old rows off, seeding blank rows, adding shared rows, or changing
sheet columns is separate workbook work. This command will refuse the old
flags `--seed-blank-missing`, `--deactivate-stale`, and `--status-col`.

## How to read the reports

Every run writes four files into `--report-dir` (default `.asset-map-sync/`):

| File | What it is |
|---|---|
| `asset_map_sync_manifest.json` | The scoreboard: what was scanned, what would change, and coverage totals |
| `asset_map_sync_report.csv` | Every card the command considered |
| `asset_map_missing_images.csv` | The work queue: cards that should have a picture and still do not |
| `asset_map_unmatched_media.csv` | Website files that did not land on any current card, plus unreadable filenames |

Start with the manifest, then the missing-images CSV. Use the full report when
you need the story behind one card.

### Common actions in the CSV

| Action | Meaning |
|---|---|
| `keep` | Already correct, or already covered by a shared `*` row |
| `fill` | Blank URL, one obvious file |
| `replace_canonical` | Current URL does not match the current website file |
| `insert_filled` | No row yet, and one obvious file is ready |
| `replace_shared_canonical` | `--complete` can safely update a shared `*` URL |
| `flag_missing` | This card should have a picture and none was found |
| `flag_ambiguous` | Two or more files tied at the winning naming level |
| `flag_dead_no_match` | The current URL looks dead, and no replacement was found. This only appears if you turned on `--verify-existing-network` |
| `wildcard_conflict` | A shared `*` row exists, but the obvious file is not a safe shared replacement. A person has to decide |
| `stale_target` | This `asset_map` row is leftover. The command reports it and leaves it alone |
| `skip_no_candidate_incremental` | An incremental `--since` run did not see a file for this card. That does not mean the picture is missing from the whole library |

`candidate_source` tells you why a file won: `prefixed`,
`shared-prefix:e-g`, `model-fallback:stingray`, `bare-shared`, and so on.

Ambiguous website files stay attached to their card in the main report. They
are not copied into the unmatched-media list.

### Which missing pictures actually matter

Every live selectable option card is expected to get a picture eventually.
The report marks that as `coverage_intent=expected`.

A few cards are `not_expected` because of how the form is built, not because
someone forgot an upload:

- the section is display-only
- the section is a standard-equipment list

Those structural cases stay in the full report. They are left out of
`asset_map_missing_images.csv` so the work queue stays useful.

Coverage numbers in the manifest are a progress meter: how many option cards
already have a URL, by model and section. A shared `*` row counts as covered
for every promoted model that needs that option. These labels are report-only.
They never add or change workbook rows, and they do not look at whether a
picture already exists when deciding expected vs not expected.

## Shared pictures that apply to every model

`asset_map` can store one option picture for every model with `model_key="*"`.
Blank `model_key` is invalid. Shared rows are only allowed for options, not
for model cards or body-style cards.

If a shared row already covers an option, the command reports `keep` and will
not add a second per-model row. A model-specific row still wins over the
shared row for that one model.

A shared row is reported `stale_target` only when **no** promoted model still
wants that option.

Creating or collapsing shared rows is a separate workbook edit. This command
never creates them. A look-first run and low-level `--apply` never edit them.
`--complete` may update one existing shared URL only when every promoted model
resolves the same single bare filename.

## Extra options

These are real flags on `scripts/sync_asset_map.py`. Most people never need
them.

| Flag | What it does |
|---|---|
| `--workbook PATH` | Workbook to read. `--complete` can only use the live `stingray_master.xlsx` |
| `--asset-sheet NAME` | Sheet to update. Default is `asset_map` |
| `--report-dir PATH` | Where reports go. Default is `.asset-map-sync/` |
| `--media-url-list PATH` | Use a text file of URLs instead of asking the website. One URL per line; `#` comments are ignored |
| `--apply` | Write obvious URL changes to the workbook, then stop. No rebuild, no publish, no cache bump |
| `--complete` | The full live job described above |
| `--timeout SECONDS` | Website timeout. Default `10` |
| `--workers N` | Parallel checks when dead-link probing is on. Default `16` |
| `--verify-existing-network` | Check whether current workbook URLs still respond. Off by default |
| `--no-verify-existing` | Does nothing. Dead-link checks are already off |
| `--since DATE` | Only ask the website for pictures newer than this date |
| `--since auto` | Same idea, using the timestamp saved from the last run, minus 6 hours. A successful `--apply --since auto` updates that saved cursor |

`--complete` cannot be combined with `--media-url-list` or `--since`. It always
uses a full live inventory.

`--apply` is the low-level write. Use it for a checked-in test list or for a
report you have already read. After `--apply`, check the workbook yourself:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Then rebuild the models that changed and republish the registry only if the
workbook actually changed. `--complete` does that follow-through for you.

A safe dry run against the checked-in test list:

```sh
.venv/bin/python scripts/sync_asset_map.py \
  --workbook stingray_master.xlsx \
  --report-dir /tmp/asset-map-sync \
  --media-url-list tests/fixtures/asset-map-sync-media-urls.txt
```

### Talking to the website

Live runs call
`https://stingraychevroletcorvette.com/wp-json/wp/v2/media` and keep only
files under `/wp-content/uploads/pictures/27vette/`.

The command sends a normal browser-style User-Agent and asks the site not to
serve a cached list. If the media library is private, set `WP_USER` and
`WP_APP_PASSWORD` in the environment. If the site answers 401 or 403 and you
are not applying a live change, use `--media-url-list` instead.

`--complete` pulls the full list more than once, with cache-busting, and
writes nothing unless two pulls are identical. If the inventory will not
settle, it stops before touching the workbook.

After a successful `--complete`, it remembers each file's WordPress
modification time in `.asset-map-sync/.asset_map_sync_state.json`. If the same
URL later comes back with a newer modification time, the saved form URL gets
an `asset_rev=...` suffix so browsers and CDNs fetch the new file. A look-first
run does not write that state file.

## Card crop and alignment are a different command

This sync updates `image_url`. It leaves `image_fit` and `image_position`
alone on rows that already exist.

To change how a card shows the picture, use `scripts/set_asset_display.py`.
It previews by default:

```sh
.venv/bin/python scripts/set_asset_display.py --rpo AQ9 --rpo AH2 --fit contain
.venv/bin/python scripts/set_asset_display.py --rpo AQ9 --rpo AH2 --fit contain --write
.venv/bin/python scripts/set_asset_display.py --rpo AQ9 --position top
```

- `cover` fills the card and may crop
- `contain` shows the whole picture
- `swatch` is the third sizing mode
- `position` is alignment inside that sizing, such as `center`, `top`, or
  `50% 30%`. `center` is not the opposite of `contain`

Repeat `--model <model_key>` to limit the change. With no `--model`, every
promoted model is included. A shared `*` row is updated once, not once per
model. The command only edits existing active rows, and it stops if an RPO is
unknown, a model is not promoted, Excel has the file open, or two active rows
claim the same card.

Review the preview, add `--write`, then rebuild the models that changed and
republish the registry.

## Workbook Manager

Workbook Manager's Asset Manager uses this same matching logic. Reviewers can
put picture decisions into a Manager draft. That draft does **not** run this
CLI's `--apply` or `--complete`, does not change WordPress, and does not write
the workbook. The Manager's separate Apply and Rebuild step is the only path
that can do that.

## If something looks wrong

- **Excel lock / save refused:** close the workbook and try again. Do not
  delete `~$stingray_master.xlsx` unless you have confirmed it is leftover.
- **Website fetch failed:** for a live write, fix access or set
  `WP_USER` / `WP_APP_PASSWORD`. For a report, use `--media-url-list`.
- **Inventory did not stabilize:** wait and rerun `--complete`. Nothing was
  written.
- **Ambiguous card:** keep one file at that naming level, or give the files
  clearer prefixes. Do not expect the command to guess.
- **Unmatched website file:** the filename did not map to a current promoted
  option, model card, or body-style card. Rename it or ignore it.
- **Unparseable filename:** the command could not find a 3-character RPO in
  the name.
- **Shared-row conflict:** leave it for a person. `--complete` will not
  overwrite a shared row with a model-specific file.

Exact commands also live in the README. This file is the detailed operator
guide for matching, reports, and the limits of the command.
