# Future-model scaffold display-order cleanup spec

Date: 2026-06-18
Status: Spec only. Do not implement until approved.

## Goal

Remove the known ZR1/ZR1X future-scaffold active option display-order collisions in a controlled, workbook-first sequence, then add a guard so future model scaffolds do not silently drift away from the same source hygiene expected of promoted models.

This is a portability/new-model-readiness cleanup. It should not promote ZR1/ZR1X, change live runtime behavior, or expand future model business data.

## Diagnosis

Root cause: ZR1 and ZR1X are inactive future model scaffolds, so current schema validation excludes their option sheets. Their source rows still contain active option-level display-order collisions that would become promotion/readiness blockers later.

Evidence inspected:

- `docs/actual-tasks-remaining-6-17.md:57-59` records the open item:
  - active promoted `(section_id, display_order)` uniqueness is guarded;
  - future ZR1/ZR1X scaffold rows still need a separate decision.
- `model_master` current state:
  - `stingray`, `grand_sport`, and `z06` are active.
  - `zr1` and `zr1x` are inactive.
- `model_workbook_sources` current state:
  - ZR1 source roles exist but are inactive, including `source_option_sheet -> zr1_options`.
  - ZR1X source roles exist but are inactive, including `source_option_sheet -> zr1x_options`.
- `scripts/corvette_form_generator/schema_validation.py:588-625` already has `validate_option_display_order_uniqueness()`.
- `scripts/corvette_form_generator/schema_validation.py:716` calls that guard only for `source_option_sheet` values discovered through the active metadata source graph.
- `scripts/corvette_form_generator/schema_validation.py:404-420` builds that graph from active `model_master` rows and active `model_workbook_sources`; inactive ZR1/ZR1X source sheets are therefore excluded today.
- `tests/test_schema_validation_metadata.py:201-239` proves duplicate option display orders are rejected for a metadata-discovered active option sheet, including standard sections.

Current workbook collisions found by read-only `openpyxl` inspection:

| Sheet | Section | Display order | Rows |
| --- | --- | ---: | --- |
| `zr1_options` | `sec_stan_001` | `20` | row 54 `opt_wub_001` / WUB, row 131 `opt_u80_001` / U80 |
| `zr1x_options` | `sec_stan_001` | `20` | row 43 `opt_u80_001` / U80, row 46 `opt_wub_001` / WUB |

Reference active-model pattern:

- `z06_options.sec_stan_001` uses `opt_u80_001` / U80 at display order `20` and `opt_wub_001` / WUB at display order `21`.
- Because these are standard-equipment rows and there is no customer-selectable product ordering decision to make, use the existing active Z06 order as the deterministic reference: U80 remains `20`; WUB becomes `21`.

Risk level: Medium for future promotion/readiness; low for current live runtime if the pass is scoped correctly.

Change type by pass:

- Pass 1: workbook/data-only cleanup of inactive future scaffold option rows.
- Pass 2: validator/test guard change to include future scaffold option display-order collisions deliberately.
- Pass 3: docs/status refresh only.

## Controlled pass plan

### Pass 1 — Clean the two future scaffold source collisions

Decision owner: workbook source rows.

Exact workbook cells to change:

- `stingray_master.xlsx`, sheet `zr1_options`:
  - row with `option_id=opt_wub_001`, `rpo=WUB`, `section_id=sec_stan_001`: change `display_order` from `20` to `21`.
  - leave `opt_u80_001` at `20`.
- `stingray_master.xlsx`, sheet `zr1x_options`:
  - row with `option_id=opt_wub_001`, `rpo=WUB`, `section_id=sec_stan_001`: change `display_order` from `20` to `21`.
  - leave `opt_u80_001` at `20`.

Implementation constraints:

- Use a small idempotent workbook writer that saves through `save_workbook_safely()`.
- Stop if Excel lock file `~$stingray_master.xlsx` exists.
- Touch only the two `display_order` cells listed above.
- Do not change labels, descriptions, prices, sections, active/selectable flags, OVS rows, rules, registry promotion rows, runtime JavaScript, dealer submission behavior, or generated artifacts by hand.
- Do not activate or promote ZR1/ZR1X.

Verification for Pass 1:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
.venv/bin/python - <<'PY'
from collections import defaultdict
from openpyxl import load_workbook

wb = load_workbook('stingray_master.xlsx', read_only=True, data_only=True)

def clean(value):
    return '' if value is None else str(value).strip()

def truthy(value):
    return clean(value).lower() not in {'false', '0', 'no', 'inactive', 'disabled'}

def display_key(value):
    text = clean(value)
    if not text:
        return ''
    try:
        number = float(text)
        return str(int(number)) if number.is_integer() else text
    except ValueError:
        return text

for sheet in ('zr1_options', 'zr1x_options'):
    ws = wb[sheet]
    headers = [clean(cell.value) for cell in next(ws.iter_rows(max_row=1))]
    buckets = defaultdict(list)
    rows = []
    for row_number, values in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        row = {header: values[index] if index < len(values) else None for index, header in enumerate(headers) if header}
        if not truthy(row.get('active')):
            continue
        if clean(row.get('section_id')) != 'sec_stan_001':
            continue
        option_id = clean(row.get('option_id'))
        if option_id in {'opt_u80_001', 'opt_wub_001'}:
            rows.append((sheet, row_number, option_id, clean(row.get('rpo')), display_key(row.get('display_order'))))
        buckets[(clean(row.get('section_id')), display_key(row.get('display_order')))].append((row_number, option_id))
    collisions = {key: value for key, value in buckets.items() if len(value) > 1}
    print(sheet, rows, collisions)
    assert not collisions, (sheet, collisions)
PY
```

Expected Pass 1 output:

- Workbook binary changes only.
- No generated artifact changes unless the implementer runs optional future preview generation for inspection.
- Current live `form-app/data.js` should not change because ZR1/ZR1X are inactive and not promoted.

### Pass 2 — Add a future-scaffold display-order guard

Decision owner: validator/test code.

Exact files to change:

- `scripts/corvette_form_generator/schema_validation.py`
- `tests/test_schema_validation_metadata.py`

Recommended behavior:

- Keep the existing active-model `duplicate_option_display_order` guard unchanged.
- Add a separate future-scaffold display-order uniqueness check that deliberately inspects existing inactive `model_workbook_sources` rows where:
  - `source_role == source_option_sheet`,
  - `sheet_name` exists in the workbook,
  - the associated model exists in `model_master` but is inactive.
- Scope the future-scaffold guard only to active rows inside those inactive option sheets, grouped by `(section_id, display_order)`, using the same numeric-normalized `display_order_key()` behavior as the current guard.
- Use a distinct `check_id`, recommended: `duplicate_future_scaffold_option_display_order`.
- Make it an error after Pass 1 is clean, so future scaffold collisions cannot be silently reintroduced.

Why separate check ID:

- It keeps default promoted-model source validation and future-scaffold hygiene distinguishable in reports.
- It avoids misrepresenting inactive scaffolds as promoted runtime sources.
- It lets future implementation decide later whether to broaden more schema checks to inactive model scaffolds without conflating that with this narrow display-order guard.

Pass 2 tests:

- Add/extend a unit test that creates an inactive `zr1` model in `model_master`, inactive `model_workbook_sources.source_option_sheet -> zr1_options`, and duplicate active rows in `zr1_options.sec_stan_001`; assert `duplicate_future_scaffold_option_display_order` is emitted.
- Add/extend a unit test that active promoted duplicate option sheets still emit the existing `duplicate_option_display_order` check ID.
- Confirm clean current workbook passes the default schema validator after Pass 1.

Validation for Pass 2:

```sh
.venv/bin/python -m pytest tests/test_schema_validation_metadata.py -q
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

No generation is required for Pass 2 unless the implementation unexpectedly changes model source metadata or generated artifacts.

### Pass 3 — Refresh standing status docs after the cleanup lands

Decision owner: docs/status only.

Exact docs to change:

- `docs/actual-tasks-remaining-6-17.md`
- This spec file, converting status from `Spec only` to completed/historical after Pass 1 and Pass 2 land.
- Any follow-up status/risk doc that still says future-model scaffold display-order is open, if it is tracked in the working branch.

Validation for Pass 3:

```sh
git diff --check -- docs/actual-tasks-remaining-6-17.md docs/future-model-scaffold-display-order-spec.md
```

## Non-goals

- No ZR1/ZR1X runtime promotion.
- No ZR1/ZR1X data completion beyond the two display-order cells.
- No changes to active Stingray, Grand Sport, or Z06 source rows.
- No generated `form_*` sheet hand edits.
- No generated `form-output/*` or `form-app/data.js` hand edits.
- No broad future-model schema validation beyond active option-row display-order uniqueness.
- No product/copy/price/rule cleanup in this pass.

## Risks

- If the future scaffold rows are later found to require a different GM-authored order, the `21` order may need revision. Current evidence favors the active Z06 standard-equipment pattern and deterministic uniqueness over leaving duplicate rows.
- Adding the future-scaffold guard to default schema validation means future inactive source rows can block default validation if they drift again. This is intentional for display-order collisions only; do not broaden inactive-scaffold checks without a separate spec.
- Workbook writes can create Excel/package damage if not saved safely. Use `save_workbook_safely()` and verify the workbook package after save.

## Approval prompt

Approve controlled Pass 1 + Pass 2 as scoped above?

Recommended answer: approve Pass 1 first, then run Pass 2 only after the workbook has been verified clean. Pass 3 should be done after both land.
