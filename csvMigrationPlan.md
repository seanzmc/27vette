This is very strong. It reads less like “let’s refactor some data” and more like a controlled infrastructure migration with seatbelts, airbags, lane assist, and a guy with orange cones yelling “not yet.” That is good.

My honest take: the plan is safe, disciplined, and probably more comprehensive than you need for the first execution pass. As a master migration plan, it is excellent. As a day-one implementation guide, it is a little heavy. I would keep this as the full safety blueprint, then create a much shorter “First Slice Execution Plan” from it.

Overall verdict

I would approve this plan with one major caveat:

Do not try to execute the whole plan at once.

The plan is good because it correctly protects the most dangerous pieces:

- Current form-app/data.js contract stays stable.
- Excel remains available until CSV parity is proven.
- Python stays during migration instead of switching schema and compiler language at the same time.
- CSV and Excel can run side by side.
- Runtime behavior, exports, pricing, auto-adds, and requirements are treated as behavior to preserve.
- Cutover only happens after validation, parity, QA, and rollback rehearsal.

That is exactly the right mindset.

The thing to watch is process weight. If every phase requires every check immediately, the migration could stall before you get the first tiny win. This plan needs an execution ladder.

⸻

What is especially good

1. The “do not rewrite compiler language yet” decision is correct

This is one of the best parts of the plan.

Switching from Excel to CSV is already a major migration. Switching from Python to Node at the same time would combine two separate risk clouds into one thunder-soup.

Keep Python first. Prove the data architecture. Then decide whether Node is worth it later.

That avoids this nightmare:

Did the behavior change because the schema changed?
Or because the compiler changed?
Or because the runtime changed?
Or because all three formed a tiny conspiracy?

Good call.

⸻

2. Freezing the current data.js contract is exactly right

This is the biggest safety anchor.

Your current app already works from generated data.js. The migration should not start by changing what app.js expects.

This pipeline is the right target:

CSV package
-> compiler
-> same form-output artifacts
-> same form-app/data.js shape
-> same runtime behavior

That lets you swap the engine under the hood without repainting the dashboard.

⸻

3. The dual-source switch is smart

This part is excellent:

STINGRAY_SOURCE=xlsx
STINGRAY_SOURCE=csv
STINGRAY_SOURCE=both

That gives you a clean comparison mode and an emergency rollback path.

I would absolutely keep this.

One small suggestion: make the scripts accept explicit CLI flags too, not just environment variables.

Example:

python scripts/compile_stingray_data.py --source xlsx
python scripts/compile_stingray_data.py --source csv
python scripts/compare_stingray_outputs.py --left xlsx --right csv

Environment variables are fine for CI, but CLI flags are easier when you are manually debugging at 11:47 PM with spreadsheet smoke coming out of your ears.

⸻

4. Deployment/cache safety is a very good catch

Static apps can fail in a sneaky way:

old app.js + new data.js
new app.js + old data.js

Adding metadata like this is smart:

dataset: {
schema_version: 1,
app_contract_version: 1,
build_id: "...",
generated_from: "xlsx",
}

That is not overthinking. That is cheap insurance.

I would keep this near the top of the real implementation list.

⸻

5. The two-tier validation strategy is excellent

You separated:

automated validation/tests
manual QA checklist

That is right.

Automated tests catch repeatable logic problems. Manual QA catches “this technically passes but feels wrong” problems.

For this project, both matter because the form is not just data. It is an interactive sales/customer-facing tool with pricing, selections, exports, and expectations baked into the flow.

⸻

What I would trim or stage more carefully

1. Branch structure may be too formal

This section:

refactor/schema-csv
phase-0-workbook-inventory
phase-1-csv-package-skeleton
phase-2-logic-to-csv
...

is conceptually clean, but in practice it may become too many branches to babysit.

I would simplify:

main
└── refactor/schema-csv

Then use small PRs or commits inside that branch.

Possible commit groups:

phase 0: freeze baseline
phase 1: first CSV slice
phase 2: first compiler pass
phase 3: parity tests
phase 4: replace one hard-coded rule family

You can still name commits/PRs by phase without managing eight nested branches.

2. CI requirements are too heavy for early phases

This list is good for final cutover:

schema-validate
semantic-validate
golden-builds
csv-vs-xlsx-output-parity
stingray-runtime-regression
export-parity
property-fuzz
generated-artifact-staleness
perf-smoke
no-framework-guard

But for phase 1, you probably only need:

existing tests pass
CSV files load
basic schema validation passes
first-slice golden tests pass

Then add the heavier checks as the migration matures.

Otherwise the plan risks becoming a fortress with no door.

3. Workbook inventory gate is useful, but do not let it block the first slice

This line is safe but potentially paralyzing:

No sheet or column may remain needs_review.

That should be a cutover gate, not a first-slice gate.

For the first slice, you only need the workbook columns relevant to:

B6P
SL1
D3V
ZZ3
BCP
BCS
BC4
engine appearance
pricing
body style scope
requirements
exclusivity

Full workbook inventory can run in parallel, but it should not block proving the architecture.

4. Manual QA checklist is excellent, but too big for every phase

The QA checklist is cutover-grade. Keep it.

But create smaller QA profiles:

First-slice QA

Only engine appearance.

Full-data QA

All migrated categories.

Cutover QA

All six variants, browsers, exports, accessibility, deployment/cache.

That way you are not forcing yourself to run a NASA launch checklist every time you move one rule table.

⸻

My recommended adjustment: add “Phase 1A: First Slice Only”

Right now the plan has a lot of great phases, but I would make the first executable milestone extremely explicit.

Add this section near the beginning:

## Phase 1A — First Slice Execution Scope

The first executable migration slice is Engine Appearance only.
Included selectables:

- B6P
- SL1
- D3V
- ZZ3
- BCP
- BCS
- BC4
- BC7 if needed for exclusivity
  Included behaviors:
- B6P is coupe-only.
- ZZ3 is convertible-only.
- B6P auto-adds SL1 at $0.
- Colored LS6 engine covers auto-add D3V at $0 on coupe.
- Colored LS6 engine covers cost $695 on coupe.
- Colored LS6 engine covers cost $595 on coupe when B6P is selected.
- Colored LS6 engine covers require ZZ3 on convertible.
- Only one LS6 engine cover may be selected.
  Out of scope:
- Interiors
- Exterior colors
- Spoilers
- Center caps
- Car covers except SL1 if included by B6P
- Full workbook inventory completion
- Node compiler
- Runtime UI rewrite
- Variant-sharded payloads

Then define success:

### First Slice Success Criteria

- CSV package loads.
- First-slice IDs validate.
- Condition engine works for coupe/convertible and selected-option terms.
- Auto-adds work for B6P -> SL1 and engine cover -> D3V.
- Dependency rule works for convertible engine cover -> ZZ3.
- Exclusive group works for LS6 engine covers.
- Pricing resolves $695 and $595 correctly.
- Golden tests pass.
- New output matches old behavior for first-slice scenarios.
- Existing full app remains powered by xlsx.

That gives you a clean first victory.

⸻

Suggested simplification of the execution order

I would reorder the practical first steps like this:

Step 1: Freeze baseline

Keep this exactly.

python scripts/generate_stingray_form.py
node --test tests/stingray-form-regression.test.mjs

Save fixture copies.

Step 2: Add metadata to generated data.js

Do this early because it protects every later step.

Step 3: Add first-slice CSV files

Only the minimum files:

catalog/variants.csv
catalog/selectables.csv
catalog/item_sets.csv
catalog/item_set_members.csv
logic/condition_sets.csv
logic/condition_terms.csv
logic/auto_adds.csv
logic/dependency_rules.csv
logic/exclusive_groups.csv
logic/exclusive_group_members.csv
pricing/price_books.csv
pricing/base_prices.csv
pricing/price_policies.csv
pricing/price_rules.csv

Delay these unless needed:

ui/_
support/_
meta/\*
price_lookup_tables.csv
price_lookup_rows.csv

Step 4: Build tiny compiler

Not the whole compiler. Just enough to load and evaluate first-slice logic.

Step 5: Add first-slice golden tests

Do not wait until the full validation system is built.

Step 6: Compare old vs new behavior for the slice

This is the magic moment.

Step 7: Replace one hard-coded group in Python

Start with something low-risk like exclusive groups or item sets.

Then proceed.

⸻

One structural concern

The plan says:

The target architecture should follow schema-refactor.md

That is fine, but make sure this document stands alone enough for Codex or future-you to work from it.

I would add a short “source of truth hierarchy” section:

## Source of Truth Hierarchy During Migration

Before cutover:

1. stingray_master.xlsx is production source.
2. data/stingray/\*_/_.csv is experimental migration source.
3. form-app/data.js and form-output/\* are generated artifacts.
   During parity:
4. xlsx and csv outputs are compared.
5. xlsx remains production unless explicitly switched.
   After cutover:
6. data/stingray/\*_/_.csv is canonical.
7. Excel is archived or generated editor surface only.
8. form-app/data.js and form-output/\* remain generated artifacts.

This makes the mental model very clear.

⸻

One missing piece: developer ergonomics

I would add a command table.

Something like:

## Common Commands

Generate from Excel:

````sh
STINGRAY_SOURCE=xlsx python scripts/generate_stingray_form.py

Compile from CSV:

STINGRAY_SOURCE=csv python scripts/compile_stingray_data.py

Compare both:

STINGRAY_SOURCE=both python scripts/compare_stingray_outputs.py

Run first-slice tests:

node --test tests/stingray/first-slice.test.mjs

Run full regression:

node --test tests/*.mjs

Serve app locally:

cd form-app
python3 -m http.server 8000
This will make the plan easier to actually use instead of just admire from across the room like an aircraft carrier.
---
# One naming suggestion
The document title is:
```md
Safe Phased Migration Plan: Excel/Python Stingray Generator → Schema-Driven CSV Data Package

That is accurate but a little long.

For your repo, I might name the file:

safeMigrationPlan.md

But title it:

# Stingray CSV Migration Plan

Then subtitle:

## Safe phased migration from Excel/Python generator to schema-driven CSV Data Package

Tiny readability thing. Not critical.

⸻

The parts I would absolutely keep

Do not cut these:

Freeze current production baseline
Dual-source switch
Preserve frontend contract
Generated build metadata
Static cache safety
Golden builds
Output parity tests
Auto-add provenance rules
Export parity
Rollback plan
Excel generated-only after cutover
No framework guard

Those are the steel beams.

⸻

The parts I would make “later”

These are good, but I would not block the first slice on them:

full property fuzzing
full browser matrix
full accessibility QA
full performance CI
SQLite artifact
optional Node compiler
variant-sharded payloads
string interning
complete editor workbook import/export
all support domain tables
complete workbook inventory gate

Those belong closer to full cutover.

⸻

Final assessment

This migration plan is sound and safe. It correctly avoids the most dangerous traps:

schema rewrite + compiler rewrite + runtime rewrite all at once

It preserves the current app contract, creates a rollback path, and demands parity before cutover. That is exactly how this should be approached.

The main improvement is to add a smaller execution layer underneath it:

Master Plan = this document
First Slice Execution Plan = tiny, concrete, engine appearance only

In other words, keep this as the map of the whole mountain range. Then write a smaller trail guide for the first climb.

My recommended next move:

Create a short first-slice checklist from this plan and start with B6P / SL1 / D3V / ZZ3 / BCP / BCS / BC4 only.

That gives you forward motion without sacrificing the safety net.
````
