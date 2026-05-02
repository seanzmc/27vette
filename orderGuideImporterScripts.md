# Order Guide Importer Scripts

Yes, but with one important distinction:

You do **not** need the final app architecture fully finished before building import scripts.

You **do** need a stable **import contract**.

That contract is the bridge between raw Chevrolet order guide exports and whatever your final app/compiler structure becomes. The importer should not care whether the current app is still legacy `form-app/data.js`, future CSV package, or some later multi-model configurator. The importer’s job is to produce clean, reviewable staging data and canonical proposals.

The safest mental model:

```text
Raw Chevrolet order guide
  -> importer/profiler
  -> staging tables
  -> mapping/classification layer
  -> canonical proposal
  -> validation
  -> accepted CSV library
  -> compiler/app generation
```

The import scripts should stop before “app behavior.” They should feed the data library. The compiler handles app output.

# The structure you need before writing efficient import scripts

You need these three things pinned down.

## 1. A canonical target shape

Not necessarily perfect, but stable enough that the importer knows where data eventually goes:

```text
catalog/selectables.csv
catalog/variants.csv
ui/selectable_display.csv
ui/availability.csv
logic/dependency_rules.csv
logic/auto_adds.csv
logic/exclusive_groups.csv
pricing/base_prices.csv
pricing/price_rules.csv
support/interiors.csv
support/exterior_colors.csv
support/color_overrides.csv
meta/source_refs.csv
```

The importer does not need to write all of these directly on day one. But it needs to know these are the destination categories.

## 2. A staging schema

This is more important for the importer than the final app.

The importer should first produce raw-ish staging files like:

```text
build/imports/<year>/<guide_key>/
  source_profile.json
  staging_sheets.csv
  staging_variants.csv
  staging_matrix_rows.csv
  staging_price_rows.csv
  staging_option_rows.csv
  staging_color_trim_rows.csv
  staging_note_rows.csv
  staging_rule_candidates.csv
  staging_unresolved_rows.csv
```

That staging layer is your safety net. It lets you inspect what the importer thinks it found before it touches canonical data.

## 3. Import maps/configuration

This is what makes the long-term “any Chevrolet order guide” goal realistic.

Instead of hard-coding Corvette knowledge into the parser, put guide-specific knowledge into maps:

```text
data/import_maps/
  chevrolet_common/
    status_symbols.csv
    phrase_patterns.csv
    section_aliases.csv
    rpo_patterns.csv

  corvette_2027/
    model_group_map.csv
    section_map.csv
    trim_map.csv
    body_code_map.csv
    known_package_phrases.csv
    ignored_rows.csv
```

For future Silverado, Equinox, Camaro, Tahoe, etc., you add or adjust import maps rather than rewriting the importer.

# The importer script family I would build

Keep this as a separate import pipeline, not tangled into the current CSV migration scripts.

```text
scripts/
  inspect_order_guide_export.py
  extract_order_guide_staging.py
  propose_canonical_rows.py
  validate_import_proposal.py
  apply_import_proposal.py
```

## 1. `inspect_order_guide_export.py`

Purpose: identify the structure of the raw file.

It should answer:

```text
What sheets exist?
Which sheets are price schedules?
Which sheets are matrix-style option tables?
Which sheets are color/trim matrices?
What model groups exist?
What variant headers exist?
What RPO columns exist?
What status symbols exist?
What weird rows exist?
```

Command shape:

```sh
.venv/bin/python scripts/inspect_order_guide_export.py \
  --source "docs/source/2027/chevrolet-corvette-export.xlsx" \
  --out build/imports/2027/corvette/source_profile.json
```

This is the “x-ray machine” script.

## 2. `extract_order_guide_staging.py`

Purpose: convert raw workbook structure into staging CSVs.

Command shape:

```sh
.venv/bin/python scripts/extract_order_guide_staging.py \
  --source "docs/source/2027/chevrolet-corvette-export.xlsx" \
  --profile build/imports/2027/corvette/source_profile.json \
  --import-map data/import_maps/corvette_2027 \
  --out build/imports/2027/corvette/staging
```

It should output rows that preserve raw meaning:

```csv
source_sheet,row_number,section_family,model_group,orderable_rpo,ref_rpo,description,variant_label,body_code,trim_level,raw_status,status_symbol,footnote_refs
```

This is still not canonical. It is structured raw evidence.

## 3. `propose_canonical_rows.py`

Purpose: convert staging into proposed canonical CSV rows.

Command shape:

```sh
.venv/bin/python scripts/propose_canonical_rows.py \
  --staging build/imports/2027/corvette/staging \
  --package data/corvette/2027 \
  --model-key stingray \
  --out build/imports/2027/corvette/proposed/stingray
```

This writes proposed files like:

```text
proposed/catalog/selectables.csv
proposed/catalog/variants.csv
proposed/ui/availability.csv
proposed/pricing/base_prices.csv
proposed/logic/dependency_rules.csv
proposed/logic/auto_adds.csv
proposed/logic/exclusive_groups.csv
```

But it should not apply them automatically.

## 4. `validate_import_proposal.py`

Purpose: check the proposal before accepting it.

It should catch:

```text
unknown RPOs
duplicate canonical IDs
unknown statuses
unmapped sections
unresolved notes
rule candidates below confidence threshold
ambiguous prices
missing variant scope
missing source references
option rows with no destination
```

Command shape:

```sh
.venv/bin/python scripts/validate_import_proposal.py \
  --proposal build/imports/2027/corvette/proposed/stingray \
  --package data/corvette/2027
```

## 5. `apply_import_proposal.py`

This should come later.

Purpose: append or merge reviewed proposal rows into canonical CSV.

I would not build this first. Early on, manual review and copy/paste from proposal to canonical CSV is safer.

# The importer should be generic, but not magical

For the stretch goal of “any Chevrolet order guide,” you want a generic parser with brand/model profiles.

Bad:

```python
if sheet_name == "Exterior 1":
    model = "stingray"
```

Better:

```text
section_aliases.csv maps "Exterior 1" -> section_family=exterior, model_group_index=1
model_group_map.csv maps group_index=1 -> model_key=stingray
```

The importer should understand general GM/Chevy order-guide concepts:

```text
sheet
section
model group
variant column
body code
trim level
orderable RPO
reference RPO
description
status cell
footnote
price row
rule phrase
```

It should not inherently know:

```text
B6P means engine appearance package
BCP is an LS6 engine cover
Z51 includes FE3
```

Those meanings should come from data, maps, or parsed source rows.

# What must not slip through the cracks

Here is the “don’t lose data” checklist.

## Source traceability

Every staging row should keep:

```text
source_file
source_sheet
source_row
source_column if applicable
source_cell_range if practical
raw_text
import_batch_id
```

Without this, debugging bad imports becomes swamp lantern work.

## Raw status preservation

Do not just map `A1` to `available`.

Keep both:

```text
raw_status = A1
canonical_status = available
footnote_refs = 1
```

Those suffixes often matter.

## Orderable vs reference RPO

Many rows have:

```text
Orderable RPO Code
Ref. Only RPO Code
```

Do not collapse them too early.

They may mean different things:

```text
customer-selectable option
included component
reference-only feature
package child
standard equipment item
```

## Description text

Always preserve the raw description.

Even if you parse it into rules, keep:

```text
source_detail_raw
```

Descriptions are the forensic record.

## Rule phrase candidates

Parser should flag phrases like:

```text
requires
included with
only available with
not available with
included and only available with
deletes
removes
requires one of
choice of
when ordered with
not available on
available on sold orders only
```

Do not silently ignore these.

## Confidence levels

Rule extraction should include:

```text
confidence = high | medium | needs_review
```

High-confidence rules can become proposals. Medium and needs-review rows go into unresolved/review queues.

## Cross-model RPO reuse

The same RPO may appear across Chevrolet models with different labels, prices, availability, or behavior.

So the future canonical data should avoid treating `rpo` alone as the primary key.

Use:

```text
selectable_id
model_key
model_year
variant_id
rpo
```

## Price schedule weirdness

Prices may vary by:

```text
model
trim
body style
package
equipment group
LPO status
included-zero behavior
```

The price importer should stage prices separately and only canonicalize after scope is clear.

## Color and trim matrix

Do not try to force color/trim sheets into normal option rows.

Color/trim needs specialized staging:

```text
staging_color_trim_rows.csv
```

with columns like:

```text
exterior_color_rpo
interior_code
seat_type
trim_level
availability_symbol
footnotes
```

## Ignored rows need a reason

If the importer ignores a row, it should write:

```text
staging_ignored_rows.csv
```

with:

```text
reason = blank row | header row | duplicate header | legal note | unsupported layout | manually excluded
```

Silent ignores are where bugs nest.

# How this grows from Corvette to any Chevrolet guide

You build the importer in layers.

## Generic layer

Reusable for any Chevrolet guide:

```text
Excel reader
sheet profiler
merged-cell/header detector
RPO extractor
status-symbol parser
price-cell parser
footnote detector
phrase-candidate extractor
staging writer
import report writer
```

## Brand/common GM layer

Shared Chevrolet conventions:

```text
Orderable RPO Code
Ref. Only RPO Code
model code patterns
trim patterns
A/S/D/-- style status symbols
price schedule blocks
common phrase rules
```

## Model-family layer

Specific to Corvette, Silverado, Tahoe, etc.:

```text
sheet group mapping
variant header patterns
section aliases
body code meaning
trim naming
special matrix handling
known unusual phrases
```

## Model-year layer

Specific to a year/export format:

```text
2027 Corvette group ordering
new status symbols
new sheet names
new source quirks
```

That gives you a realistic path to “any Chevrolet order guide” without pretending all guides will be identical.

# What I would do next in this chat

Since the CSV migration is ongoing elsewhere, I would keep this thread focused on the importer and do the next steps in this order:

```text
1. Define staging CSV schemas.
2. Write a source profiler for the uploaded raw export.
3. Generate an import profile report.
4. Review the report to identify recurring sheet/header/status patterns.
5. Build the matrix-row extractor.
6. Build the price-schedule extractor.
7. Build the phrase-candidate extractor.
8. Only then generate canonical proposals.
```

The first real script should be a profiler, not a full importer.

# The first importer milestone

The first milestone should be:

```text
Given the raw Corvette export workbook, produce:
- source_profile.json
- staging_sheets.csv
- staging_variants.csv
- staging_matrix_rows.csv
- staging_status_symbols.csv
- staging_rule_phrase_candidates.csv
- staging_unresolved_rows.csv
```

No canonical CSV changes yet.

Success criteria:

```text
All workbook sheets are classified.
All variant headers are detected or flagged.
All RPO rows are extracted or flagged.
All status symbols are counted and preserved.
All rule-like phrases are detected.
All ignored rows have reasons.
No raw source edits are required.
```

That is the importer foundation.

Once that works for Corvette, you start shaping the parser toward broader Chevrolet exports.
