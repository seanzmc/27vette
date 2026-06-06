27vette — GM Order-Guide Ingest Prompt (First Pass → source_review staging schema)

You are ingesting a GM Corvette online order-guide Excel export into the 27vette staging schema. This is the first processing pass. Everything downstream — rule engines, price assignment, per-model compatibility sheets, and the final \*\_options runtime sheets — depends on this pass being lossless and correct. If this pass is wrong, the whole pipeline goes sideways, so you will work in checkpointed stages and stop-and-report rather than guess.

Hard guardrails (read first)

Do NOT use the corvette-ingest-v3 skill. It targets a different, lossy output (a 6-column / 3-value matrix) and will pull you off course. Specifically it (a) collapses availability to only Standard/Available/Not Available, throwing away ■ equipment-group membership, □ upgradeable, and D/ADI nuance; (b) keeps no provenance; © flattens footnotes into one blob with no marker→footnote map; (d) has no price-candidate or base-price hooks; (e) hard-codes 6 LT variants and chokes on the 8-variant ZR1/ZR1X sheet. We need the opposite: preserve everything, parse into atomic columns. Ignore that skill entirely.
Preserve all existing data. Every in-scope source row produces at least one output row. Raw columns hold the source value verbatim. Normalized columns are added alongside raw columns, never instead of them.
Never invent an RPO, price, name, or availability value. Blank is a valid, correct answer. A flag is better than a guess.
Never overwrite the source export or the live master workbook. Write output to a new sheet in a working copy.
Stop-and-report on any invariant failure (see Checkpoints). Do not silently repair.
Inputs

<raw_export>.xlsx — the GM export. Numbered section tabs (the data to ingest).
stingray_master.xlsx — reference only, for: the exact target schema (future_model_source_review), the price schedule (price_sched_raw), and existing examples (future_model_option_review, z06_options). Read it; do not modify it.
Source layout (what the GM export looks like)

Each section tab follows this shape:

Row 1: model name (e.g. Stingray, ZR1 and ZR1X).
Row 2: legend — S = Standard A = Available -- = Not Available D = ADI Available ■ = Included in Equipment Group □ = Included in Equipment Group but upgradeable.
Row 3: header — Orderable RPO Code | Ref. Only RPO Code | Description | <variant columns…>. Each variant header is a multi-line cell: <body/model label>\n<model code>\n<trim>, e.g. Coupe\n1YC07\n1LT or ZR1X Convertible\n1YS67\n3LZ.
Row 4+: data rows. Some sheets contain a bare section-label row (e.g. a lone Equipment Groups cell) — treat it as context, not an option row.
Tab → model mapping

Tabs are grouped by category and suffixed by series number. Series number = model:

Suffix Model(s) model_key
…1 Stingray stingray
…2 Grand Sport grandSport
…3 Z06 z06
…4 ZR1 and ZR1X (mixed in one sheet) zr1, zr1x
Category prefixes: Standard Equipment, Equipment Groups, Interior, Exterior, Mechanical, Color and Trim.

Color and Trim tabs are OUT OF SCOPE for this pass. They are an interior color/trim matrix with a different shape and feed a separate interiors pipeline (lt_interiors / LZ_Interiors / color_overrides). Do not force them into this schema. Note their presence in your final report and move on.
Series-4 split (critical)

The …4 tabs contain ZR1 and ZR1X in the same rows, distinguished only by their variant columns (1YR…/1YS…). Produce separate output rows for model_key = zr1 and model_key = zr1x, each carrying only its own variant columns. ZR1/ZR1X only ship 1LZ and 3LZ trims (no 2LZ).

Target schema: source_review

Produce one combined sheet (model-agnostic; the model_key column separates models), column-for-column matching future_model_source_review in the master. Columns, in order, grouped by purpose:

Provenance — model_key, source_group, raw_source_sheets, raw_source_spans, raw_category_context

Parsed RPO — source_orderable_rpo, source_ref_rpo, source_primary_rpo

Parsed primary content — source_option_description, source_disclosure_raw, source_disclosure_map, source_detail_raw

Candidate (auto-suggested, best-effort) — candidate_option_id, candidate_section_id, candidate_section_resolution, candidate_section_candidates, candidate_display_behavior, candidate_price, price_candidate_rows, price_candidate_summary, base_model_list_price, base_model_dfc, base_model_total_price

Review — review_flags, approved_option_id, approved_rpo, approved_price, approved_option_name, approved_description, approved_detail_raw, approved_section_id, approved_selectable, approved_display_behavior, approved_display_order, copy_from_model_key, copy_from_option_id, duplicate_group_id, review_status, review_reason, active, notes

Per-variant matrix (three parallel families) — for every variant key present, emit a triplet: raw*status*<vk>, status*<vk>, status_note*<vk>.

The approved** columns are intentionally shaped to map 1:1 onto the final *\_options schema (option_id, rpo, price, option_name, description, detail_raw, section_id, selectable, display_order, active, display_behavior). Leave them blank in this pass — they are filled during human review / downstream processing. This pass fills only the source*_, candidate\__, _*status*_, provenance, and review_flags columns.
Variant keys

Derive each key from the multi-line header: key = <trim lowercased>\_<last 3 chars of the model code>. Body letter: C=Stingray, E=Grand Sport, H=Z06, R=ZR1, S=ZR1X; suffix 07=Coupe, 67=Convertible. Derive the key set from the actual headers — do not hard-code — but the full canonical set is:

stingray: 1lt_c07 2lt_c07 3lt_c07 1lt_c67 2lt_c67 3lt_c67
grandSport: 1lt_e07 2lt_e07 3lt_e07 1lt_e67 2lt_e67 3lt_e67
z06: 1lz_h07 2lz_h07 3lz_h07 1lz_h67 2lz_h67 3lz_h67
zr1: 1lz_r07 3lz_r07 1lz_r67 3lz_r67
zr1x: 1lz_s07 3lz_s07 1lz_s67 3lz_s67
Parsing rules

1. Footnote-marker un-fusion (apply at read time, before anything else)

GM superscript footnote digits flatten into ordinary trailing digits fused to the preceding token. RPO codes are always exactly 3 characters.

Any RPO-like token longer than 3 chars ending in digits → real RPO is the first 3 chars; the trailing digits are a footnote marker. (Prevents phantom RPOs like HU76, EL98.)
A name/description ending directly in a digit with no space → strip the trailing digit run as a marker.
Status cells too: S1, A1, A/D1, ■1 → status symbol = S/A/A/D/■, marker = trailing digit. Capture the marker into status*note*<vk>; keep the full original (e.g. A/D1) in raw*status*<vk>. 2. RPO consolidation

source_orderable_rpo = col A verbatim; source_ref_rpo = col B verbatim (after un-fusion).
source_primary_rpo = orderable if present, else ref, else blank. Standard-equipment rows often legitimately have no RPO — leave blank, never mint one. 3. Description split

The Description cell packs name + descriptive text + in-cell disclosures.

source*option_description = the full descriptive text (everything before the disclosure block), preserved whole.
In-cell disclosures begin after a line break with 1. , then 2. , etc. Split them out:
source_disclosure_raw = the raw disclosure block as it appears.
source_disclosure_map = normalized N=<text> entries joined with |, e.g. 1=Always use seat belts… | 2=Also includes tonneau grille.
source_detail_raw = any clearly-separable trailing detail that is not a numbered disclosure; else blank.
For the eventual name/description split (used later in approved*_): name = text up to the first comma; description = the remainder. You may pre-compute this into candidate\__ notes, but the authoritative name/description split happens at review time — do not destroy source_option_description. 4. Per-variant matrix (the part v3 gets wrong — do not lose data)

For each variant column, write all three:

raw*status*<vk> = the cell verbatim, including ■, □, D, A/D, and any fused footnote digit.
status*<vk> = normalized coarse value, one of exactly: standard, available, unavailable (or blank if the source cell is blank). Mapping:
S → standard
A, A/D → available
-- → unavailable
■ / □ → preserve raw, set normalized to standard and add a review_flag (equip_group_membership) so the equipment-group nuance is not silently lost. Do not discard ■/□.
any symbol not covered above → leave status blank, set raw verbatim, flag unknown_status_symbol.
status_note*<vk> = the footnote marker digit fused to this cell, if any; else blank. Every digit captured here must resolve against source_disclosure_map; if it doesn’t, flag orphan_status_note. 5. Provenance

source_group: map the category tab → standard_equipment (Standard Equipment), interior_exterior_mechanical (Interior / Exterior / Mechanical / Equipment Groups), exterior_paint (paint rows). Use raw_category_context for finer context (e.g. Paint, Equipment Groups) when a section-label row applies.
raw_source_sheets = the GM tab name(s) the row came from. raw_source_spans = <tab>:<startrow>-<endrow> (1-based, matching the export). These make every output row traceable and are what the checkpoints reconcile against. 6. Price candidate hooks (do not force a single price)

From price_sched_raw:

Base Model Prices (keyed by model code, e.g. 1YC07): set base_model_list_price, base_model_dfc, and base_model_total_price (list + DFC) per row’s model.
Additional Options (keyed by Option Code = RPO; price sits in the Factory/List column; the Description column often carries a trim/condition qualifier): match source_primary_rpo.
Collect all matching rows into price_candidate_rows and a human-readable price_candidate_summary.
Set candidate_price only when exactly one unambiguous match exists. If an RPO has multiple conditional prices (e.g. PDB, PDD, PDF vary by wheel; E60 is trim-gated), leave candidate_price blank and flag price_ambiguous. Never average or pick. 7. Candidate IDs (best-effort, non-authoritative)

candidate*option_id: opt*<rpo lowercased>_001, or opt_<seq>\_001 when no RPO. Reconcile real IDs at review time.
candidate_section_id / candidate_section_resolution / candidate_section_candidates: best-effort section guess from category + name; populate the resolution/candidates columns when uncertain rather than forcing one. candidate_display_behavior: default sensible value, flag if unsure.
Checkpoints (required)

Work in stages and persist intermediate state to disk after each stage (e.g. a JSON/parquet snapshot of parsed rows + a running flag log) so the run can resume without re-reading from scratch. After each section tab and again at the end, emit a checkpoint report and assert the invariants below. Cadence: one checkpoint per section tab, plus one final reconciliation across the whole export.

Per-tab checkpoint report

For the tab just parsed, print: tab name, model_key(s), source row span, # in-scope rows read, # output rows written, the derived variant-key list, a 2-row sample (raw + parsed side by side), and any flags raised.

Invariants (a failure = stop and report, do not continue)

Row conservation. Output rows for a tab == in-scope source rows (× the ZR1/ZR1X fan-out where applicable). Legend/header/section-label rows are excluded and counted separately. Report the arithmetic.
3-char RPO. No value in source*primary_rpo exceeds 3 characters. (Catches un-fusion misses.)
No fabricated RPO. Every non-blank source_primary_rpo appears in that row’s orderable or ref source cell.
Variant completeness. The number of raw_status*<vk> columns populated for a row == the number of variant columns in its source header. No phantom or missing variants.
Normalized vocabulary. Every status*<vk> ∈ {standard, available, unavailable, blank}. Anything else is flagged, not coerced.
Note↔map integrity. Every status_note*<vk> digit resolves to an entry in that row’s source*disclosure_map; orphans flagged.
Price honesty. No candidate_price is set where price_candidate_rows shows >1 distinct price. Ambiguities are flagged.
No data loss vs. raw. For a random sample of rows per tab, confirm raw_status*<vk> reproduces the source cell exactly (including ■/□/D/fused digits).
Final reconciliation

Across the whole export: total source rows in scope, total output rows, per-model row counts, total flags by type, and an explicit list of out-of-scope tabs skipped (the Color and Trim tabs). End with a clear PASS/FAIL line. On FAIL, list the failing invariant(s) and the offending rows; do not write a “clean” output.

Output

Write a new sheet source*review (or <run-id>\_source_review) into a working copy of the master workbook — never the original. One combined sheet, all in-scope models, model_key distinguishing them, columns exactly matching future_model_source_review.
Optionally also emit the slimmer option_review view (matching future_model_option_review: model_key, raw_source_sheet, raw_source_span, orderable_rpo, ref_only_rpo, source_rpo, source_option_description, source_disclosure_raw, raw_status_summary, normalized_status_summary, suggested*_, final\__, review_status, active, notes), where raw_status_summary / normalized_status_summary are the per-variant triplets collapsed to vk=value; … strings.
Do not touch any live runtime sheet (_\_options, _\_ovs, \*\_rule_mapping, interiors, etc.).
Stop-and-report conditions

Stop and ask rather than guess if: a tab’s header doesn’t match the expected Orderable / Ref / Description / variants shape; a variant header can’t be parsed into a key; a status symbol isn’t in the legend; the price schedule sections can’t be located; or any invariant above fails. Report what you saw, where (tab + row span), and what’s ambiguous.
