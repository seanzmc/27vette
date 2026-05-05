Yes. I would change the plan by adding a guided import-review GUI layer on top of the existing scripts, not by replacing the scripts.

The current script pipeline is good because it is deterministic, testable, and safe. A GUI should become the control panel for steering the pipeline:

Raw workbook
-> automated parser guesses
-> GUI review/steering
-> saved import-map decisions
-> rerun extractor/audit/proposal
-> review outputs

The GUI should not be the source of truth by itself. It should write structured config files that the scripts already know how to consume.

⸻

The core design change

Right now the workflow is:

run script
open CSV
inspect weirdness
write config/map file
rerun script

A user-friendly version becomes:

upload/select workbook
see detected sheets/ranges/headers
approve or correct parser guesses
save corrections to import maps
rerun pipeline from GUI
review staging/proposal/audit dashboards

The important architecture:

GUI actions
-> write import map/config CSV or JSON
-> run existing scripts
-> display generated reports

Not:

GUI actions
-> directly mutate canonical data

⸻

What the GUI should let the user steer

1. Source workbook setup

The user selects:

model year
make
vehicle family
source workbook path
guide/export type

The GUI then shows:

sheets found
detected sheet roles
detected model groups
detected section ranges
detected variant columns
status symbols found
unresolved/suspicious rows

User can label:

Price Schedule
Standard Equipment
Interior
Exterior
Mechanical
Equipment Groups
Color and Trim
Ignore
Unknown / needs review

This replaces hand-editing sheet_roles.csv.

⸻

2. Sheet role editor

A table like:

Sheet Detected role Confidence User role Scope Notes
Standard Equipment 1 primary_variant_matrix high primary_variant_matrix variant
Equipment Groups 1 derived_equipment_summary high derived_equipment_summary cross-check
Color and Trim 1 model_global_matrix medium model_global_matrix model needs review

When the user saves, it writes:

data/import_maps/corvette_2027/sheet_roles.csv

or a future richer equivalent.

⸻

3. Range/section mapping

This is one of the most valuable GUI pieces.

The GUI should show a sheet preview with detected regions:

rows 1-8: header/legend
rows 9-73: variant matrix
rows 75-90: notes/disclosures

For Color/Trim:

rows 1-52: interior combination matrix
rows 54-88: exterior/interior compatibility matrix
rows 90-93: disclosures

User can adjust:

section start row
section end row
header row
data start row
data end row
section role
scope type

Saved output could become:

data/import_maps/corvette_2027/sheet_sections.csv

or:

data/import_maps/corvette_2027/section_overrides.csv

The extractor then uses that instead of guessing.

⸻

Critical concept: importer maps are user decisions

Every GUI correction should write to a durable map file.

Examples:

sheet_roles.csv
model_codes.csv
status_symbols.csv
phrase_patterns.csv
color_trim_scope.csv
rpo_role_overlaps.csv
schema_decisions.csv
section_family_map.csv
range_overrides.csv

The GUI is not where decisions live. The GUI is how the user edits the decision files.

That keeps everything:

diffable
testable
repeatable
reviewable
portable

⸻

A practical GUI workflow

Step 1: Import session

User starts a session:

2027 Corvette Order Guide Import

The system creates:

build/imports/2027/corvette/import_session.json

with:

source workbook path
import maps used
script versions
timestamp
staging output path
audit output path
review status

⸻

Step 2: Inspect workbook

GUI runs:

inspect_order_guide_export.py

Then shows:

23 sheets detected
5 sheet role types
16 variant-scoped matrix sheets
2 Color/Trim sheets
1 Price Schedule
4 Equipment Group sheets
0 fatal issues

User approves or corrects sheet roles.

⸻

Step 3: Sheet/range review

GUI shows each sheet with a grid preview.

User can confirm:

this is the header row
these are variant columns
this is the data region
these rows are footnotes/disclosures
this sheet is cross-check only
this sheet is model-global

Corrections write to import maps.

⸻

Step 4: Extract staging

GUI runs:

extract_order_guide_staging.py

Then shows dashboards:

variant matrix rows extracted
Color/Trim rows extracted
price rows extracted
ignored rows
unresolved rows
status counts
model_key confidence

User does not edit staging directly. If staging is wrong, user adjusts maps/ranges and reruns extraction.

⸻

Step 5: Audit staging

GUI runs:

audit_order_guide_staging.py

It displays:

primary matrix ready: true
pricing ready: true
equipment groups ready: true
color trim ready: false
RPO overlaps ready: false
canonical proposal ready: false

Clicking a domain opens review rows.

⸻

Step 6: Resolve audit decisions

The GUI presents decision queues.

Color/Trim scope queue

User sees:

Sheet Section Rows Suggested status User decision
Color and Trim 1 interior matrix 49 needs_review accepted_review_only
Color and Trim 1 compatibility matrix 170 needs_review accepted_review_only

Save writes:

color_trim_scope.csv

RPO role overlap queue

User sees:

RPO Orderable count Ref-only count Sample descriptions Decision
B6P 6 2 Coupe Engine Appearance… accepted_expected_overlap
D3V 12 4 Engine lighting… accepted_expected_overlap

Save writes:

rpo_role_overlaps.csv

⸻

Where the GUI should be strongest

1. Visual sheet/range mapping

This is the biggest pain point to solve.

A good GUI should let the user click cells/ranges:

Set as header row
Set as data region
Set as variant columns
Set as disclosure range
Set as ignored range
Set as Color/Trim top section
Set as Color/Trim compatibility section

The GUI does not need Excel-level editing. It needs range labeling.

⸻

2. Model/variant column mapping

The GUI should show detected variant columns:

Column Header text Body code Trim Detected model_key User override
G Stingray Coupe / 1YC07 / 1LT 1YC07 1LT stingray
H Stingray Coupe / 1YC07 / 2LT 1YC07 2LT stingray

User can correct:

model_key
body_style
trim_level
variant_id

This writes to:

model_codes.csv
variant_overrides.csv

⸻

3. Status symbol review

The GUI should surface unknown statuses:

A/D
A/D1
S1
--
□
■

User chooses:

available
standard
not_available
review_only
ignore

This writes to:

status_symbols.csv

Important: preserve raw status.

⸻

4. Footnote and disclosure review

The GUI should show footnote extraction in context:

A/D2 -> status=A/D, footnote=2
HU76 -> RPO=HU7, footnote=6
Performance Textile5 -> text=Performance Textile, footnote=5

User can mark:

correct
wrong split
needs review
do not split

Saved as parser override/mapping evidence.

⸻

5. Review queue dashboards

Instead of opening giant CSVs, the GUI should show:

Review queue: 5134 rows
expected review-only: 3200
no-RPO standard equipment: 1000
ref-only evidence: 600
duplicate/conflicting: 80
unsupported status: 0

Then the user can drill down.

⸻

Recommended GUI screens

Screen 1: Import Sessions

Shows prior imports:

2027 Corvette - raw workbook - staging complete - proposal ready
2026 Corvette - archived
2027 Silverado - inspection only

⸻

Screen 2: Source Workbook Overview

Displays:

source path
sheet count
detected sheets
import map profile
last run status

Buttons:

Run Inspect
Run Extract
Run Audit
Generate Review Packet
Generate Proposal

⸻

Screen 3: Sheet Classifier

User labels sheets.

This writes:

sheet_roles.csv

⸻

Screen 4: Range Mapper

Spreadsheet-like preview.

User labels:

header rows
data rows
matrix regions
Color/Trim top section
Color/Trim compatibility section
disclosures
ignored regions

This is the most important GUI screen.

⸻

Screen 5: Variant Mapper

User reviews variant columns and model_key inference.

Writes:

model_codes.csv
variant_overrides.csv

⸻

Screen 6: Audit Dashboard

Shows readiness domains:

Primary matrix: ready
Pricing: ready
Equipment Groups: ready
Color/Trim: review-only
RPO overlaps: resolved
Canonical proposal: not globally ready
Narrow proposal: ready

⸻

Screen 7: Review Decision Queues

For:

Color/Trim scope
RPO role overlaps
Schema decisions
Section mapping
Conflicts
New candidates
Apply blockers

⸻

Screen 8: Proposal Review

Shows:

broad proposal counts
confident subset counts
availability matrix
source trace samples
multi-model RPOs
missing coverage

⸻

Screen 9: Reconciliation Review

Shows:

matched existing canonical rows
new candidates
conflicts
unavailable canonical context
section mapping needs
source-ref member plan

⸻

Screen 10: Future Apply Plan Review

Eventually, when you build apply planning:

Rows to add
Rows to update
Rows blocked
Source refs to attach
Validation impact

User approves the apply plan explicitly.

⸻

How I would build the GUI technically

Do not start with a full web app.

I would build it in stages.

Phase 1: Local Streamlit app

Fastest useful option.

Pros:

Python-native
works with existing scripts
easy file upload/path input
easy tables
easy buttons
easy previews
easy CSV editing widgets

Command:

streamlit run tools/import_gui/app.py

Structure:

tools/import_gui/
app.py
pages/
1_Source_Overview.py
2_Sheet_Classifier.py
3_Range_Mapper.py
4_Audit_Dashboard.py
5_Review_Queues.py
6_Proposal_Review.py

This would let you use your existing Python importer code directly.

Phase 2: Better spreadsheet/range UI

If Streamlit is not good enough for cell/range mapping, add a stronger grid component or move that part to a small web UI.

Options:

Streamlit + AgGrid
NiceGUI
Panel
React later if needed

But I would not start with React.

Phase 3: Production admin app

Only after workflow stabilizes.

Could become:

FastAPI backend
React frontend
job runner
import session database
file storage

That is later.

⸻

The GUI should not replace scripts

The scripts remain the engine.

The GUI should call commands like:

inspect
extract
audit
generate review packet
proposal readiness
generate broad proposal
audit proposal
filter confident subset
schema alignment
decision packet
reconciliation
triage

Every GUI action should be reproducible from CLI.

That matters because:

you can test scripts
you can debug scripts
you can automate later
you can run headless
you avoid GUI-only hidden state

⸻

The most important data model: Import Session

Eventually, add:

import_sessions/
session_id/
session.json
decisions/
outputs/

A session record might contain:

{
"session_id": "2027_corvette_v1",
"source_workbook": "docs/source/2027/corvette/export.xlsx",
"vehicle_family": "corvette",
"model_year": 2027,
"import_map_profile": "corvette_2027",
"current_stage": "proposal_review",
"outputs": {
"staging": "build/imports/2027/corvette",
"proposal": "build/imports/2027/corvette/proposed/primary_matrix",
"confident_subset": "build/imports/2027/corvette/proposed/primary_matrix_confident"
}
}

This lets the GUI know what to show without guessing paths.

⸻

What changes in the pipeline with GUI steering

The core pipeline remains the same, but adds user checkpoints:

1. Inspect workbook
2. User confirms sheet roles
3. User confirms/edits ranges
4. Extract staging
5. User reviews unresolved rows
6. Audit staging
7. User applies review decisions
8. Proposal readiness
9. Generate proposal
10. User reviews confident subset
11. Schema alignment
12. User resolves schema decisions
13. Reconciliation
14. User resolves section mapping/conflicts
15. Apply plan
16. User approves apply
17. Canonical write

The GUI makes those human decision points explicit instead of burying them in CSV files.

⸻

How to avoid making the GUI dangerous

Use these guardrails:

GUI can edit import maps.
GUI can trigger scripts.
GUI can display generated outputs.
GUI can generate review decisions.
GUI cannot directly edit canonical CSV.
GUI cannot directly edit form-app/data.js.
GUI cannot apply without an approved apply plan.
GUI cannot hide unresolved rows.
GUI cannot silently fill missing source data.

The GUI should have visible stage labels:

Evidence
Staging
Audit
Proposal
Reconciliation
Apply Plan
Canonical

And every screen should say which layer you are editing.

⸻

Recommended revised architecture

Raw Workbook
|
v
Importer Scripts <------ GUI edits import maps/config
|
v
Staging Evidence
|
v
Audit Reports <------ GUI review decisions
|
v
Proposal Artifacts
|
v
Confident Subset
|
v
Schema Alignment / Reconciliation
|
v
Apply Plan <------ GUI explicit approval
|
v
Canonical CSV
|
v
Compiler / App Data

⸻

Where I would start

Start with the GUI areas that save the most pain:

First GUI milestone

Import Session Overview
Sheet Classifier
Range Mapper
Audit Dashboard
Review Queue Viewer

Do not start with apply. Do not start with canonical editing.

First milestone success:

User can select a raw workbook,
run inspect,
label/correct sheet roles and ranges,
rerun extract,
view audit/review queues,
and save decisions to import maps.

That would already be a massive improvement.

⸻

Bottom line

Yes, I would make the importer user-steerable through a GUI.

But the GUI should be a decision/control layer, not a replacement for the scripts and not a direct canonical editor.

Best production architecture:

scripts = deterministic engine
GUI = steering wheel
import maps = saved decisions
staging/proposals = evidence
canonical CSV = approved truth
compiler = app output

That gives you the best of both worlds: a user-friendly workflow without losing the discipline, traceability, and testability you just spent all these passes building.
