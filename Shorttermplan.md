# Short term plan

Yes. You can speed this up a lot without throwing away the careful work, but it requires changing the unit of work.

Right now the process has been too focused on tiny “protect this relationship” passes. The faster path is to migrate by relationship type / feature slice, not by individual option pair.

The better strategy

Stop asking:

Should this one relationship be reviewed?

Start asking:

What whole category of behavior still lives outside the CSV schema?
Can we migrate that entire behavior type in one pass?

That lets you move faster while still keeping validation.

What I would do next

1. Make Pass 127 a coverage map, not another review report

Purpose:

Compare old/generated relationships against the new CSV relationship files and tell us what is already covered.

The output should classify every legacy relationship as:

covered_in_csv
not_found_in_csv
partially_covered
needs_schema_mapping

This immediately tells you what is truly left.

This matters because schema_refactor already has real migrated relationship files. logic/auto_adds.csv contains real rows like B6P → D3V/SL9, ZZ3 → BC7/SL9, PEF → CAV/RIA, PDY → RYT/S08, PCU → STI/VQK/VWE, and SBT → SC7. ￼ logic/dependency_rules.csv also already has ZZ3 convertible requirements for LS6 covers/BC7. ￼

So the next step should prove:

Already covered: these relationships
Still missing: these relationships

Not ask you to manually decide from scratch.

2. Migrate remaining Stingray behavior in big slices

Once Pass 127 identifies missing behavior, group the remaining work into a few feature slices.

For Stingray, likely slices are:

A. Package includes / auto-adds
B. Requires / excludes / replacement rules
C. Requires-any rule groups
D. Exclusive groups
E. Price rules
F. Variant availability/status
G. Interiors / color overrides / seat pricing

Each slice gets one pass:

extract old behavior
write/update canonical CSV rows
compile shadow output
compare against production
add focused regression tests

That is faster than one pass per option family.

3. Use data.js/production output as the oracle, but not as the schema

This is the speed lever.

Use the existing generated data to extract facts:

data.rules
data.priceRules
data.ruleGroups
data.exclusiveGroups
data.choices
data.interiors

The runtime app already uses those arrays from generated app-shaped data. ￼

So instead of manually recreating every rule, write importer/proposer scripts that say:

Here are all old includes rules.
Here are all old requires rules.
Here are all old excludes rules.
Here are all old price rules.
Here are all old rule groups.
Here are all old exclusive groups.

Then map those into the canonical CSV files.

This keeps care, but removes manual slog.

4. Add “bulk accept with exceptions”

For each relationship type, the script should generate proposed CSV rows.

Then instead of reviewing 200 things manually, you review only:

rows the script could not map
rows that collide
rows that change behavior
rows with ambiguous relationship type
rows missing target/source IDs

That is how you speed up.

The rule should be:

Automatically carry forward obvious legacy behavior.
Manually review only ambiguity.

5. Stop building more reporting layers

The reporting/control-plane stack is now strong enough. More reports will not finish the migration.

The useful reports from here should be only:

coverage map
unmapped rows report
behavior diff report

No more review packets unless they directly drive CSV generation.

The fastest safe workflow

Here is the process I would use for the rest of Stingray.

Pass 127 — Relationship coverage map

No migration yet.

Output:

legacy_relationships.csv
csv_relationship_coverage.csv
uncovered_relationships.csv
coverage-summary.md

Goal:

Find exactly what is left.

Pass 128 — Bulk migrate uncovered auto-add/include relationships

For every old rule_type=includes relationship not already in logic/auto_adds.csv, generate proposed rows.

Then test:

old computeAutoAdded behavior == new CSV auto_add behavior

Pass 129 — Bulk migrate requires/excludes

Move old requires and excludes rules into:

logic/dependency_rules.csv
logic/condition_sets.csv
logic/condition_terms.csv

Where a direct mapping is not possible, output needs_schema_mapping.

Pass 130 — Bulk migrate rule groups

Move requires_any groups into:

logic/rule_groups.csv
logic/rule_group_members.csv

This should cover things like spoiler requirements.

Pass 131 — Bulk migrate exclusive groups

Move old hardcoded EXCLUSIVE_GROUPS into:

logic/exclusive_groups.csv
logic/exclusive_group_members.csv

This is probably a fast win because the old generator still has hardcoded exclusive groups. ￼

Pass 132 — Bulk migrate price rules

Move price behavior into:

pricing/base_prices.csv
pricing/price_rules.csv
pricing/price_policies.csv

Pass 133 — Final Stingray behavior diff

Run a full comparison:

production generated behavior
vs
CSV-compiled shadow behavior

Report only actual behavior differences.

How to handle the five other models

Do not repeat the Stingray process manually five times.

Use Stingray to build the machine.

For the other models, you want this flow:

raw model source
→ extractor
→ proposed canonical CSV rows
→ unmapped exceptions report
→ compile
→ compare

The other models should not start with hand-built CSVs.

They should start with:

copy schema
import model data
auto-map what is obvious
review only exceptions

What to preserve from the careful work

Keep these safeguards:

production behavior remains oracle
no source switch until full diff passes
CSV compiler emits old app-shaped data
tests compare production vs shadow
unresolved references fail loudly
interior-source IDs are not fake selectables
ownership/projection remains explicit

Those are good. Do not throw them away.

What to stop doing:

one tiny pass per report field
manual review before coverage map
manual decisions without showing CSV coverage
new sidecars that do not generate/migrate data

The practical acceleration rule

For every future pass, ask:

Does this pass move behavior into canonical CSV?
Does it prove behavior already moved?
Does it identify exact unmapped behavior?

If the answer is no, skip it.

The next Codex prompt I would use

Recommended Codex reasoning level: high

Pass 127 objective:
Create a legacy-to-CSV relationship coverage map for Stingray on schema_refactor.
Goal:
Determine which production/generated relationships are already represented in the canonical data/stingray CSV files and which are not.
Inputs:

- production/generated Stingray data from form-app/data.js or current production loader
- data.rules
- data.priceRules
- data.ruleGroups
- data.exclusiveGroups
- data/stingray/logic/auto_adds.csv
- data/stingray/logic/dependency_rules.csv
- data/stingray/logic/rule_groups.csv
- data/stingray/logic/rule_group_members.csv
- data/stingray/logic/exclusive_groups.csv
- data/stingray/logic/exclusive_group_members.csv
- data/stingray/pricing/base_prices.csv
- data/stingray/pricing/price_rules.csv
- data/stingray/catalog/item_sets.csv
- data/stingray/catalog/item_set_members.csv
  Output bundle:
  pass127-relationship-coverage-report/
  relationship-coverage-report.md
  legacy-relationships.csv
  csv-relationship-coverage.csv
  uncovered-relationships.csv
  schema-gap-relationships.csv
  Required behavior:
- Report only. Do not migrate.
- One row per legacy relationship.
- Identify relationship type:
  includes
  requires
  excludes
  requires_any
  exclusive_group_member
  price_rule
- Determine whether each is covered by CSV.
- If covered, include covering_file and covering_row_id.
- If not covered, include coverage_status not_found_in_csv.
- If the relationship type cannot map cleanly to current schema, include coverage_status needs_schema_mapping.
- Summarize counts by relationship_type and coverage_status.
- Do not edit runtime, generated artifacts, workbook, manifest, or app files.
  Success criteria:
- We can see exactly what is left to migrate.
- Existing tests still pass.

This pass gets you out of the fog. Then the next passes can actually migrate the uncovered sets in bulk.
