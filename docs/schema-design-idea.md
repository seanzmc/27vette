Yes, that makes sense, but I would frame it carefully.

What you are describing is not “backing into raw data.” It is better described as a **reconciliation layer** or **schema-guided importer assist**.

The right version:

```text
raw order guide staging
  + known-good canonical CSV/app-schema data
  -> match/reconciliation report
  -> suggested import maps
  -> unresolved review rows
```

The dangerous version:

```text
raw order guide staging
  + known-good app data
  -> silently fill missing fields
  -> pretend the raw import worked
```

That second one creates a circular system where the importer “passes” because it copied the answer key, not because it correctly read the source.

# The useful way to “cheat”

Once the CSV refactor is fully migrated, the canonical CSV library can act as an **oracle for known data**.

For Stingray, you will already know things like:

```text
RPO B6P exists.
Its label should be Coupe Engine Appearance Package.
It belongs in a certain section.
It appears on certain body/trim variants.
It has known pricing behavior.
It has source text or legacy display metadata.
```

So a script can compare raw staging rows against the known canonical data and say:

```text
Raw row likely maps to existing selectable opt_b6p.
Label similarity: high.
RPO match: exact.
Section match: high.
Variant availability match: high.
Price match: high.
Recommended action: auto-match candidate, review not required.
```

Or:

```text
Raw row has RPO DY0.
Canonical has DY0 as reference-only in one place and orderable in another.
Recommended action: review RPO role overlap.
```

That is very useful.

# What I would not do

I would not design a script that tries to recreate the workbook’s raw layout from the app schema.

That is backwards and brittle.

The workbook layout is source evidence. The app schema is normalized truth. They have different jobs.

Instead, the script should do this:

```text
raw staging row
  -> compare against canonical known rows
  -> assign match confidence
  -> recommend destination
  -> flag mismatch
```

It should never say:

```text
The raw file did not provide this, but canonical data has it, so insert it as if the raw file said it.
```

That is where the breakdown starts.

# Best use cases for canonical-assisted importing

## 1. Matching raw rows to existing selectables

A script can match by:

```text
RPO exact match
label similarity
description similarity
section/sheet family
model_key
body_style
trim_level
price
source detail text
```

Output:

```csv
source_sheet,source_row,raw_rpo,raw_label,matched_selectable_id,match_confidence,match_reasons,review_status
Exterior 1,42,B6P,Coupe Engine Appearance Package,opt_b6p,high,"exact_rpo|label_match|section_match",auto_match_candidate
```

## 2. Generating import-map suggestions

Instead of hard-coding parser knowledge, use the known canonical library to suggest maps.

Example output:

```text
suggested_section_aliases.csv
suggested_rpo_aliases.csv
suggested_label_normalizations.csv
suggested_model_code_mappings.csv
```

These are suggestions, not automatic source-of-truth changes.

## 3. Finding source changes year over year

Once you import a new order guide, compare it to the prior known-good canonical data:

```text
new RPOs
removed RPOs
renamed labels
price changes
availability changes
section moves
new status symbols
new rule phrases
```

That becomes extremely useful for annual order guide updates.

## 4. Validating importer output

After the importer proposes canonical rows, compare those proposals to the existing known-good data for the same model/year.

This catches parser mistakes like:

```text
HTA became H + TA
HU76 became fake RPO HU76
model_key defaulted to corvette
A/D was treated as unknown
Color/Trim got variant-expanded too early
```

## 5. Bootstrapping additional models

For Z06, Grand Sport, ZR1, etc., Stingray canonical data can help with shared RPOs, shared sections, common status semantics, and repeated labels.

But it should not be treated as the oracle for model-specific availability.

# The script I would eventually build

Something like:

```text
scripts/reconcile_order_guide_staging.py
```

Command:

```sh
.venv/bin/python scripts/reconcile_order_guide_staging.py \
  --staging build/imports/2027/corvette \
  --canonical data/corvette/2027 \
  --model-key stingray \
  --out build/imports/2027/corvette/reconciliation/stingray
```

Outputs:

```text
reconciliation_report.json
matched_selectables.csv
unmatched_staging_rows.csv
canonical_rows_missing_from_source.csv
source_rows_missing_from_canonical.csv
availability_comparison.csv
price_comparison.csv
section_mapping_suggestions.csv
rpo_alias_suggestions.csv
```

Important: this script should be read-only over both staging and canonical data.

# Where this fits in the pipeline

Eventually:

```text
1. Raw workbook
2. Staging extractor
3. Staging audit
4. Review packet
5. Proposal readiness report
6. Narrow proposal generator
7. Canonical-assisted reconciliation
8. Human review
9. Apply approved proposal
10. Compile app data
```

Or for known mature models:

```text
1. Raw workbook
2. Staging extractor
3. Reconcile against previous canonical data
4. Generate proposal
5. Review differences
6. Apply approved changes
```

# The main risk

The biggest risk is **circular validation**.

Bad:

```text
canonical data says B6P is available on coupe
importer fails to read B6P availability
script fills B6P availability from canonical
test passes
```

That hides the importer failure.

Good:

```text
canonical data says B6P is available on coupe
raw staging does not show B6P availability
script flags mismatch
human reviews
```

The canonical data should explain what you expected. It should not silently repair what the raw source failed to prove.

# The rule I would enforce

Use canonical/app-schema data as:

```text
matching aid
confidence scorer
diff oracle
suggestion generator
regression comparison
```

Do not use it as:

```text
raw source replacement
silent fallback
automatic truth override
canonical proposal filler
```

# My recommendation

Yes, build toward this. It is a smart idea.

But do it after the first narrow proposal generator exists, not before. The importer currently needs to prove it can produce a clean proposal from raw staging. Once that exists, a reconciliation script becomes incredibly valuable because it can tell you:

```text
This proposal matches known-good canonical data.
This proposal disagrees with known-good canonical data.
This source row is new.
This canonical row is no longer present in the new guide.
This parser likely missed something.
```

That is the safe “cheat.” It does not fake the import. It gives the importer an answer key and forces every mismatch into the open.
