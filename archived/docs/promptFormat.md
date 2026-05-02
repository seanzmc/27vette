Recommended Codex reasoning level: high for the plan/spec pass. Use medium for the implementation pass after approval.
You are working in the 27vette repo.
Task: Importer Pass 3 - staging integrity and propagation fixes.
The importer is still staging-only. Do not create canonical proposals. Do not modify the app, generator, workbook, production output, or canonical CSV package.
Current state:
Importer scaffold exists.
Importer Pass 2 added layout-aware Color/Trim parsing, section detection, context-aware status parsing, footnote parsing, and body-code model-key inference.
Real-workbook audit shows staging*variants.csv resolves model_key correctly, but other staging outputs with model_key columns are not propagating those model keys.
Variant-scoped A1/S1-style statuses are preserved correctly.
A/D and A/D1 availability cells are not recognized yet.
For customer-facing configurator purposes, A/D and A/Dn should canonicalize to available while preserving raw_status.
Color/Trim top rows now produce interior RPOs cleanly and preserve footnotes.
Color/Trim compatibility rows are not preserving some footnotes because raw interior color header content includes trailing locale text like en-us, blocking trailing-number footnote detection.
staging_unresolved_rows.csv is empty, which may mean unresolved rows are not being captured or the audit reporting is too quiet.
Color/Trim disclosures may be review-only and do not need to become canonical behavior in this pass.
This pass must tighten staging reliability, not expand migration scope.
Hard boundaries:
Do not modify form-app/app.js.
Do not modify form-app/data.js.
Do not modify scripts/generate_stingray_form.py.
Do not modify stingray_master.xlsx.
Do not modify form-output/.
Do not modify canonical data/stingray/\**/\_.csv.
Do not create canonical proposal rows.
Do not merge staging rows into canonical CSV.
Do not add source switching.
Do not add frontend tooling.
Do not edit raw source workbooks.
Keep this additive/staging-only.
Read these files first:
scripts/order_guide_importer.py
scripts/inspect_order_guide_export.py
scripts/extract_order_guide_staging.py
data/import_maps/chevrolet_common/status_symbols.csv
data/import_maps/chevrolet_common/phrase_patterns.csv
data/import_maps/corvette_2027/sheet_roles.csv
data/import_maps/corvette_2027/model_codes.csv
tests/imports/order-guide-import-scaffold.test.mjs
tests/imports/order-guide-layout-aware.test.mjs
generated real-workbook staging output under build/imports/2027/corvette/ if present
docs/source/2027 Chevrolet Car Corvette Export (1).xlsx if present
orderGuideImporterScripts.md if present
Important rules to preserve:
Copy what the workbook visibly says before interpreting it.
Do not invent RPOs, descriptions, details, package memberships, compatibility logic, or availability.
Preserve raw source text and source location.
Keep orderable RPO and ref-only RPO separate.
A/D and A/Dn mean customer-facing Available. Preserve raw_status but canonicalize to available.
Footnote markers are flattened in the .xlsx export as trailing digits. Detect and preserve them before extracting RPO identity.
RPO codes are generally three characters. In RPO-field context, a longer RPO-like token ending in digits may be a real 3-character RPO plus fused footnote marker.
Do not apply that RPO-footnote cleanup globally. Use field context, because some text values and statuses also contain digits.
Color and Trim sheets require separate handling from normal variant matrix sheets.
Color and Trim disclosures may be whole-sheet or page/section-specific evidence.
Variant matrix sheet footnotes are located in availability/status cells such as S1, A1, A/D2.
Equipment Groups should not create primary selectable candidates for Corvette. They are ignored or derived/cross-check evidence unless later explicitly promoted by review.
Price matching from the raw export is staging evidence only. If a price is missing or ambiguous, leave it blank or flag it rather than guessing.
Implementation objectives:
Propagate model_key beyond staging_variants.csv.
Currently staging_variants.csv resolves model_key correctly, but other staging outputs with a model_key column do not.
Fix model_key propagation for:
staging_variant_matrix_rows.csv
staging_color_trim_interior_rows.csv
staging_color_trim_compatibility_rows.csv
staging_color_trim_disclosures.csv
staging_equipment_group_rows.csv
staging_price_rows.csv where practical
staging_rule_phrase_candidates.csv where practical
staging_unresolved_rows.csv where practical
staging_ignored_rows.csv where practical
Use the best available evidence:
variant header/body code mapping
detected sheet section model_key
sheet_roles.csv
model_codes.csv
source sheet group mapping only when explicit enough
Do not default unresolved values to corvette.
corvette is guide_family, not model_key.
If model_key cannot be resolved, leave model_key blank and set confidence/review fields where available:
model_key_confidence=needs_review
review_status=needs_review
reason=unresolved_model_key
If these columns do not exist in a staging file, add them only where useful and consistent.
Add A/D and A/Dn status parsing.
Update status parsing to recognize:
A/D
A/D1
A/D2
A/D10
For these values:
raw_status should remain A/D or A/Dn
status_symbol should be A/D or A, whichever current staging conventions can support cleanly
canonical_status should be available
footnote_refs should preserve the numeric suffix when present
notes or status_detail may record that D/dealer distinction is ignored for customer-facing availability
Do not treat D-only statuses the same unless existing status_symbols.csv already defines them.
This pass only needs A/D and A/Dn support.
Add or update data/import_maps/chevrolet_common/status_symbols.csv if that is the cleanest place to represent this.
Fix Color/Trim compatibility header footnote parsing with locale suffixes.
Color/Trim compatibility headers may contain trailing locale markers such as:
en-us
possible similar locale suffixes
Example issue:
A header that should expose a trailing footnote number fails because the raw text ends with en-us.
Implement a context-aware cleanup for Color/Trim compatibility header parsing:
preserve the full raw header text
create a normalized header text used for parsing
remove or ignore trailing locale markers such as en-us before footnote detection
then detect trailing footnote numbers up to at least 10
preserve parsed header value and footnote_refs
record footnote_scope such as interior_color_header or compatibility_header
Do not globally strip en-us from all fields unless the field context is appropriate.
Do not corrupt legitimate values that happen to contain hyphenated text.
Improve unresolved and ignored row reporting.
staging_unresolved_rows.csv being empty is suspicious. It may be correct, but the importer should prove that.
Add or improve logic so nonblank rows that are not classified or extracted are written to:
staging_unresolved_rows.csv when they appear meaningful but unsupported/ambiguous
staging_ignored_rows.csv when they are safely ignorable, with a reason
Examples of unresolved reasons:
unresolved_model_key
unclassified_nonblank_row
unsupported_sheet_section
suspicious_unparsed_status
color_trim_header_footnote_unresolved
no_variant_context
equipment_group_no_primary_match, if applicable
Examples of ignored reasons:
blank_row
repeated_header
legend_row
decorative_note
already_extracted_disclosure
workbook_lock_or_temp_source
Update import_report.json with counts for:
unresolved rows by reason
ignored rows by reason
model_key resolved/needs_review counts by staging file
status parse rejections by context
A/D statuses parsed
Color/Trim locale suffix cleanups
Color/Trim header footnotes detected after cleanup
Treat Color/Trim disclosures as review evidence only.
Do not over-process disclosures in this pass.
Keep staging_color_trim_disclosures.csv as raw/review evidence:
raw_text
extracted_rpos if obvious
phrase_type if obvious
applies_to_section_role if obvious
confidence
review_status
If disclosure parsing is noisy, mark review_status=needs_review rather than trying to convert it into canonical behavior.
Do not let disclosure parsing block the pass.
Preserve current correct behavior.
Do not regress:
HTA/HUP/HUQ must remain interior RPOs, not fake statuses.
Color/Trim top rows must preserve RPOs and footnotes.
Color/Trim rows must remain model-global, not variant-expanded.
Variant-scoped A1/S1 cells must continue parsing correctly.
Equipment Groups must remain derived/cross-check only.
No canonical proposal generation.
Tests.
Update or add tests under:
tests/imports/order-guide-layout-aware.test.mjs
Add cases for:
A/D parses to canonical_status=available.
A/D2 parses to canonical_status=available and footnote_refs=2.
HU76 in an interior RPO field is preserved as raw_value=HU76 and parsed as interior_rpo=HU7, footnote_refs=6 with medium/high confidence depending on context.
HU76 outside an RPO field is not blindly split.
In-cell disclosures beginning after line breaks like "1. " or "2. " are preserved as detail/disclosure text, not merged into the option name.
Equipment Groups rows do not create selectable candidates.
A Standard Equipment row with no RPO is allowed and does not invent an RPO.
A/D parses as canonical_status=available with raw_status=A/D
A/D1 parses as canonical_status=available with footnote_refs=1
model_key from staging_variants propagates into variant matrix rows
model_key is not defaulted to corvette in non-variant outputs
unresolved body/model context is flagged needs_review instead of silently becoming corvette
Color/Trim compatibility header with trailing en-us still detects trailing footnote number
raw Color/Trim header with en-us is preserved while normalized parse value is cleaned
staging_unresolved_rows.csv receives a synthetic meaningful unclassified row
staging_ignored_rows.csv receives ignored rows with explicit reasons
existing HTA/HUP/HUQ test still passes
Tests should use synthetic workbook fixtures and should not require the real raw workbook to be committed.
Real workbook smoke run.
After tests, smoke run against:
docs/source/2027 Chevrolet Car Corvette Export (1).xlsx
if present.
Then inspect or summarize:
model_key counts by staging file
A/D status count
Color/Trim header locale cleanup count
unresolved row count
ignored row count
Do not commit build/imports output.
Validation commands to run:
.venv/bin/python -m py_compile scripts/order_guide_importer.py
.venv/bin/python -m py_compile scripts/inspect_order_guide_export.py
.venv/bin/python -m py_compile scripts/extract_order_guide_staging.py
node --test tests/imports/order-guide-import-scaffold.test.mjs
node --test tests/imports/order-guide-layout-aware.test.mjs
Smoke run if real workbook exists:
.venv/bin/python scripts/inspect_order_guide_export.py \
--source "docs/source/2027 Chevrolet Car Corvette Export (1).xlsx" \
--out build/imports/2027/corvette/source_profile.json
.venv/bin/python scripts/extract_order_guide_staging.py \
--source "docs/source/2027 Chevrolet Car Corvette Export (1).xlsx" \
--out build/imports/2027/corvette
Then run:
git status --short --untracked-files=all
Acceptance criteria:
No production app/generator/workbook/generated artifact changes.
No canonical CSV proposal generation.
model_key is propagated into non-variant staging outputs where context supports it.
unresolved model_key cases are flagged instead of defaulting to corvette.
A/D and A/Dn statuses parse to canonical_status=available while preserving raw_status and footnotes.
Color/Trim compatibility headers with trailing en-us can still expose footnotes.
HTA/HUP/HUQ remain RPOs, not statuses.
unresolved/ignored rows are written with explicit reasons when synthetic fixtures contain unresolved/ignored content.
import_report.json includes useful counts for these fixes.
synthetic tests pass.
real workbook smoke run exits successfully if workbook exists.
Before editing:
Return a concise implementation plan listing:
files you expect to add
files you expect to modify
how you will propagate model_key
how you will support A/D and A/Dn statuses
how you will clean Color/Trim locale suffixes without corrupting raw values
how you will improve unresolved/ignored reporting
tests you will add/update
validation commands you will run
blockers or assumptions
Wait for approval before making code changes.
