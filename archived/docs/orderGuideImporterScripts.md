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

# Prompt

I agree that the whole app doesn't need to be built, but obviously I would want a schema that is not still being developed when I build these scripts so that is definitely a blocking task that I am still working on, but getting there. Again, this conversation should be dedicated primarily to a plan to build the import scripts and your most recent response hit almost every pain point involved with the raw order guides. A couple of things that I want to note: Equipment Groups 1-4 contains no unique information compared to standard equipment, interior, exterior, and mechanical sheets. There are rows that exist in the other sheets that are not in equipment groups though but it is exclusively standard equipment/ auto added, included features. Nothing selectable.
The other thing I want to point out is that the Colors and Trim sheets are the only sheets that contain information that applies to all variants of the model.

Yes, those two notes materially improve the importer plan.

They change the sheet taxonomy from “parse every sheet as a possible source of canonical truth” to a much cleaner model:

```text
Primary variant-scoped sheets:
  Standard Equipment
  Interior
  Exterior
  Mechanical

Derived / cross-check sheets:
  Equipment Groups

Model-global sheets:
  Color and Trim

Price source:
  Price Schedule
```

That is a much better importer design. The raw export should be parsed with explicit sheet roles instead of treating every sheet equally.

# Big adjustment 1: Equipment Groups should not create selectables

Your clarification is important:

> Equipment Groups 1-4 contains no unique selectable information.

So the importer should **not** use Equipment Groups as a source for new canonical `selectables`.

Instead, Equipment Groups should be treated as a **derived audit/support source**.

## What Equipment Groups should do

It can still be useful for:

```text
confirming package contents
confirming standard/included equipment
capturing included/ref-only features
cross-checking that primary sheets did not miss anything
supporting standard-equipment reports
building import confidence
```

But it should not independently generate:

```text
catalog/selectables.csv
ui/selectable_display.csv
pricing/base_prices.csv
```

unless a row is explicitly missing from the primary sheets and gets flagged for review.

## Importer behavior

For Equipment Groups, I would create:

```text
staging_equipment_group_rows.csv
```

but mark every row with:

```text
source_role = derived_equipment_summary
canonical_candidate = false
selectable_candidate = false
```

Possible row dispositions:

```text
derived_standard_equipment
derived_auto_added_feature
derived_included_feature
crosscheck_only
needs_review_missing_primary_match
```

The important rule:

```text
Equipment Groups can confirm or explain.
Equipment Groups should not create customer-selectable options.
```

Tiny goblin-proofing detail: if Equipment Groups contains a row that cannot be matched to Standard Equipment, Interior, Exterior, or Mechanical, the importer should not silently discard it. It should write that row to:

```text
staging_unresolved_rows.csv
```

with:

```text
reason = equipment_group_row_has_no_primary_match
```

# Big adjustment 2: Color and Trim is model-global

This also changes the importer logic.

The Color and Trim sheets should not be parsed like variant matrix sheets. They apply to all variants of the model, so staging should preserve that broader scope.

Instead of expanding immediately into every variant, the importer should stage rows as:

```text
scope_type = model
model_key = stingray
applies_to_all_variants = true
```

Then the canonical proposal or compiler can later decide whether to fan those into variant-level generated choice rows.

## Correct staging behavior

For Color and Trim, create something like:

```text
staging_color_trim_rows.csv
```

with columns like:

```csv
source_sheet,source_row,model_key,scope_type,exterior_color_rpo,interior_code,seat_code,trim_level,raw_status,status_symbol,footnote_refs,raw_text
```

The key is this:

```text
Do not duplicate Color and Trim rows across every variant during staging.
```

Keep them model-global until the canonical proposal or compiler needs variant-specific output.

# Updated source precedence

The importer should have an explicit source priority table.

```text
Price Schedule
  Source of truth for prices.

Standard Equipment / Interior / Exterior / Mechanical
  Source of truth for variant-scoped availability and option rows.

Color and Trim
  Source of truth for model-wide color/interior/trim compatibility.

Equipment Groups
  Derived summary / cross-check / included-feature support only.
```

That source precedence should live in an import map, not hard-coded into the parser.

Example:

```csv
sheet_family,source_role,canonical_priority,creates_selectables,creates_prices,creates_rules,notes
Price Schedule,price_source,100,false,true,false,Primary price source
Standard Equipment,primary_variant_matrix,90,true,false,true,Variant-scoped standard and included rows
Interior,primary_variant_matrix,90,true,false,true,Variant-scoped interior rows
Exterior,primary_variant_matrix,90,true,false,true,Variant-scoped exterior rows
Mechanical,primary_variant_matrix,90,true,false,true,Variant-scoped mechanical rows
Color and Trim,model_global_matrix,85,true,false,true,Model-wide color and trim compatibility
Equipment Groups,derived_equipment_summary,20,false,false,false,Cross-check and standard/included feature audit only
```

This gives you one central place to adjust behavior if another Chevrolet guide uses a different structure.

# Updated staging files

I would now define staging output like this:

```text
build/imports/<year>/<guide_key>/
  source_profile.json

  staging_sheets.csv
  staging_variants.csv
  staging_variant_matrix_rows.csv
  staging_color_trim_rows.csv
  staging_price_rows.csv
  staging_equipment_group_rows.csv
  staging_rule_phrase_candidates.csv
  staging_unresolved_rows.csv
  staging_ignored_rows.csv
  import_report.json
```

## `staging_sheets.csv`

Purpose: classify every sheet.

```csv
sheet_name,sheet_role,section_family,model_group_index,model_key,scope_type,creates_canonical_candidates,notes
Standard Equipment 1,primary_variant_matrix,standard_equipment,1,stingray,variant,true,
Equipment Groups 1,derived_equipment_summary,equipment_groups,1,stingray,variant,false,Cross-check only
Color and Trim 1,model_global_matrix,color_trim,1,stingray,model,true,Applies to all model variants
Price Schedule,price_source,pricing,,all,model,true,
```

## `staging_variant_matrix_rows.csv`

Only for:

```text
Standard Equipment
Interior
Exterior
Mechanical
```

This captures variant-scoped rows.

```csv
source_sheet,source_row,model_key,section_family,orderable_rpo,ref_rpo,description,variant_id,body_code,body_style,trim_level,raw_status,status_symbol,footnote_refs,canonical_status,source_detail_raw
```

## `staging_equipment_group_rows.csv`

Only for Equipment Groups.

```csv
source_sheet,source_row,model_key,equipment_group_rpo,orderable_rpo,ref_rpo,description,row_kind,matched_primary_row_key,match_status,source_detail_raw
```

Where:

```text
row_kind = standard_feature | included_feature | auto_added_feature | reference_only | unknown
match_status = matched_primary | no_primary_match | duplicate_summary | needs_review
```

## `staging_color_trim_rows.csv`

Only for Color and Trim.

```csv
source_sheet,source_row,model_key,scope_type,exterior_color_rpo,exterior_color_name,interior_code,interior_label,seat_code,trim_level,raw_status,status_symbol,footnote_refs,canonical_status,source_detail_raw
```

With:

```text
scope_type = model
```

not variant.

# Updated importer flow

The pipeline becomes:

```text
1. Profile workbook.
2. Classify sheets by role.
3. Extract primary variant matrix rows.
4. Extract model-global color/trim rows.
5. Extract price rows.
6. Extract Equipment Groups as derived/cross-check rows.
7. Match Equipment Groups rows back to primary rows.
8. Extract rule phrase candidates from all relevant raw text.
9. Generate unresolved/review queues.
10. Only then generate canonical proposals.
```

Equipment Groups now gets used at step 7, not as a primary source.

# What this means for “any Chevrolet order guide”

This actually helps the stretch goal.

Instead of assuming all Chevrolet guides work like Corvette, your importer can have configurable sheet roles:

```text
primary_variant_matrix
model_global_matrix
derived_equipment_summary
price_source
legal_notes
unknown
```

For Corvette, Equipment Groups is derived.

For some other Chevrolet model, Equipment Groups might contain unique selectable package data. In that case, the model-family import map can say:

```text
Equipment Groups = primary_package_source
```

But for Corvette, your map says:

```text
Equipment Groups = derived_equipment_summary
```

That is the right level of generality. The parser stays generic. The source behavior lives in the import profile.

# Schema blocking task: what must be stable first?

You are right that the final canonical schema should be mostly stable before building the proposal generator.

But you do **not** need to wait on every final app detail to build the first two import scripts.

## Can build now

These are safe before the canonical schema is final:

```text
inspect_order_guide_export.py
extract_order_guide_staging.py
```

Why?

Because staging is raw evidence. It does not need to perfectly match final canonical tables.

## Should wait for schema stability

These should wait until the CSV schema is stable:

```text
propose_canonical_rows.py
validate_import_proposal.py
apply_import_proposal.py
```

The split looks like this:

```text
Safe now:
  raw workbook -> staging evidence

Blocked by final schema:
  staging evidence -> canonical CSV proposals
```

That lets you move forward without building against a moving target.

# Crack-prevention checklist

Given your two clarifications, I would add these checks to the importer.

## Equipment Groups checks

```text
Every Equipment Groups row must be classified as non-selectable.
Every Equipment Groups row should match a primary row or be flagged.
No canonical selectable may be created solely from Equipment Groups.
No price may be created solely from Equipment Groups.
No active dependency/auto-add may be created solely from Equipment Groups without review.
```

## Color and Trim checks

```text
Every Color and Trim row must have model-level scope.
No Color and Trim staging row should be prematurely duplicated per variant.
Color/interior compatibility should be preserved as matrix data.
Footnotes/status suffixes must be retained.
Canonical proposal may expand to variants only after validation.
```

## Source priority checks

```text
If the same RPO appears in primary sheets and Equipment Groups, primary sheet wins.
If the same price appears in a descriptive sheet and Price Schedule, Price Schedule wins.
If a color/interior compatibility conflict exists, Color and Trim wins unless manually overridden.
If Equipment Groups has unmatched content, flag it instead of promoting it.
```

# Revised importer milestones

I would now frame the importer project like this:

## Importer Pass 1: source profiler

Outputs:

```text
source_profile.json
staging_sheets.csv
import_report.json
```

Success criteria:

```text
All sheets classified.
Equipment Groups classified as derived.
Color and Trim classified as model-global.
Primary variant matrix sheets detected.
No canonical rows generated.
```

## Importer Pass 2: primary matrix extractor

Outputs:

```text
staging_variants.csv
staging_variant_matrix_rows.csv
staging_status_symbols.csv
```

Success criteria:

```text
Standard Equipment, Interior, Exterior, Mechanical rows extracted.
Variant headers detected.
Raw statuses preserved.
Footnote refs preserved.
```

## Importer Pass 3: color and trim extractor

Outputs:

```text
staging_color_trim_rows.csv
```

Success criteria:

```text
Color and Trim rows are model-scoped.
No premature variant expansion.
Raw matrix status preserved.
```

## Importer Pass 4: equipment group cross-check extractor

Outputs:

```text
staging_equipment_group_rows.csv
```

Success criteria:

```text
Equipment Group rows are non-selectable.
Rows are matched to primary sheets where possible.
Unmatched rows are flagged.
```

## Importer Pass 5: price extractor

Outputs:

```text
staging_price_rows.csv
```

Success criteria:

```text
Prices parsed from Price Schedule.
Price scope preserved.
No descriptive-sheet price overrides accepted without review.
```

## Importer Pass 6: rule phrase candidate extractor

Outputs:

```text
staging_rule_phrase_candidates.csv
staging_unresolved_rows.csv
```

Success criteria:

```text
Requires / includes / not available / removes / choice-of phrases detected.
Confidence levels assigned.
Ambiguous phrases flagged for review.
```

Only after those would I build:

```text
Importer Pass 7: canonical proposal generator
```

# Bottom line

Your two corrections make the importer architecture cleaner:

```text
Equipment Groups = derived cross-check, not selectable source.
Color and Trim = model-global matrix, not variant-scoped option sheet.
```

That should be baked into the import map and staging schemas from the beginning.

You still need the canonical CSV schema to settle before writing proposal/app-facing scripts, but you can safely begin with profiler and staging extraction scripts now. Those scripts preserve raw evidence, classify source roles, and make sure nothing slips through the cracks while the final schema finishes hardening.

# Design requirement

Yes. The importer absolutely needs to follow this practice, or it will recreate the same mess at higher speed.

The importer should **not** treat every repeated RPO row as a new real option. It should treat order-guide rows as raw evidence, then compile them into:

```text
canonical option identity
+ context-specific status
+ display placement
+ relationship rules
+ source provenance
```

## Importer rule

```text
Never resolve option identity from RPO alone.
RPO is a code, not always a unique option record.
```

The importer needs to distinguish:

```text
same RPO, same real option, repeated for display
same RPO, different production option_id because of context
same RPO, display-only Standard Equipment duplicate
same RPO, package/included duplicate
same RPO, ambiguous and requiring review
```

## The importer pipeline should be staged

Instead of:

```text
Order guide row -> selectables.csv
```

it should be:

```text
raw order guide rows
    ↓
staging rows with sheet/range/source provenance
    ↓
duplicate-RPO classification
    ↓
canonical option identity resolution
    ↓
status/availability cascade
    ↓
relationship/rule extraction
    ↓
human review report
    ↓
approved canonical CSV output
```

That prevents the importer from blindly creating fake duplicate options.

## Status model the importer should emit

For each option/context, it should be able to assign statuses like:

```text
optional
standard_choice
standard_fixed
included_auto
unavailable
display_only
requires_review
```

That is where your cascade comes in:

```text
model/year -> body -> trim -> variant -> option override
```

So if B6P is optional on one model but standard fixed on ZR1 coupe, that is not two random B6P options. It is one canonical option with different status rules.

## Relationship extraction must use resolved identity

When the importer finds something like:

```text
RPO A not available with RPO B
```

it should not immediately write:

```text
A excludes B
```

It should first resolve:

```text
Which A?
Which B?
In what section?
Customer-facing or display-only?
Context-specific?
Is this a true option relationship, package include, default behavior, or display note?
```

If it cannot answer that deterministically, it should output:

```text
requires_review
```

not invent a rule.

## This should become an importer design requirement

I would put this in the importer plan/spec, not necessarily `AGENTS.md`:

```text
Importer must preserve raw source rows and classify duplicate RPOs before generating canonical option/rule CSVs. It must not create canonical options or relationships from RPO-only matching when multiple production/source rows share the same RPO. Ambiguous duplicates must be staged for review.
```

That principle will matter more as soon as you move beyond Stingray into Z06, ZR1, ZR1X, Grand Sport, or other Chevy models. Otherwise the importer will just mass-produce the exact duplicate/display artifact problem we are now catching manually.

Importer must preserve raw source rows and classify duplicate RPOs before generating canonical option/rule CSVs. It must not create canonical options or relationships from RPO-only matching when multiple production/source rows share the same RPO. Ambiguous duplicates must be staged for review.
