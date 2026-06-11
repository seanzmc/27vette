# 27vette merge divergence report
Date: 2026-06-10
Compared: diffs/ (snapshot of live 27vette main) vs local repo /Users/seandm/Projects/27vette-vis (branch work/27vette-copy-2026-06-09, c46811c)

Direction convention: LIVE = diffs/ snapshot (production main). LOCAL = this repo.

## High-level picture
Two-sided divergence:
- LOCAL did a large generator refactor (unified entry points + module split), workbook reorg/cleanup (archive-sheet extraction, audit-column removal, tab colors, type normalization), retired the review_flag taxonomy, fixed Stingray interior grouping labels, and added a runtime-contract promotion pipeline.
- LIVE advanced independently with: a requires_any UX/correctness fix in app.js, a new GS rule group (gs_group_j57_z52_requirement), and schema_validation additions (price_semantic block + lifecycle column enforcement) that depend on workbook columns LOCAL removed.

Identical on both sides: form-app/index.html, styles.css, stingray-form-data.csv, mapping.py, model_config.py, validation.py, workbook_package.py, validate_* scripts, repair_workbook_tables.py, compare-generated-contracts.mjs.

## Script/file layout
LIVE per-model scripts (generate_stingray_form.py, generate_grand_sport_form.py, generate_z06_form.py, promote_z06_runtime.py, build_grand_sport_rule_sources.py) were replaced LOCALLY by generate_form.py --model, promote_model.py --model, build_rule_sources.py --model, plus new modules corvette_form_generator/{contract,interiors,pricing,production,rules}.py. ~85% mechanical extraction; behavioral deltas listed below.

## Runtime behavior (form-app)
1. app.js — LIVE is strictly ahead. requiresAnyReason() on LIVE simulates the candidate selection (candidateSelectedIds + computeAutoAdded(extraIds)) so unselected options get a predictive "Requires one of X" reason and auto-added includes don't false-positive. LOCAL only explains after selection. MERGE: take LIVE's requiresAnyReason + computeAutoAdded(extraIds). Only difference in the file.
2. data.js — LOCAL is the newer regeneration (06-10 vs 06-08/09). Same 3 models, same counts except one item. Differences:
   a. review_flag removed from all 465 rules/priceRules entries (LOCAL). Live values were all "False"/"" — no information loss.
   b. Stingray interior_parent_group_label normalized: descriptive material text / color names -> canonical seat labels (AE4/AQ9/AH2/AUP), matching GS and Z06. LOCAL is the data-quality fix.
   c. BUSINESS RULE DELTA: GS ruleGroup gs_group_j57_z52_requirement (requires_any: J57 -> FEB or FEY) exists ONLY ON LIVE (27 groups/176 members vs 26/174 locally). Source rows were deleted from LOCAL workbook grandSport_rule_groups (-1 row) / grandSport_rule_group_members (-2 rows). DECISION NEEDED: intentional retirement or lost during reorg? If unintentional, restore the workbook rows and regenerate.

## Workbook (stingray_master.xlsx)
- LIVE 96 sheets vs LOCAL 81: 15 removed locally, all archive/raw/orphan (archive_*, *_raw, component_price_rules, standard_equipment_groups). Sheet order fully reorganized + tab colors on all sheets locally.
- Columns removed locally (audit taxonomy retirement): review_flag + price_semantic from *_price_rules; review_flag + normalization_reason + replacement_group_id + replacement_rule_id from *_rule_mapping; help_text (section_master); presentation_bucket (section_presentation); copy_id (context_choice_copy); asset_id + review_flag (asset_map); review_flag from form_rules/form_price_rules.
- Real data deltas (type-normalized): only (1) GS J57/Z52 group deletion, (2) model_registry_promotion artifact_path for GS and Z06: *-form-data-draft.json -> *-runtime-contract.json, (3) regenerated form_interiors labels/hierarchy (123 rows, plus 2 EL9 rows moved to Santorini Blue family). Hundreds of apparent cell diffs were text-vs-typed storage only ('True'/'1790' text on LIVE vs bool/number LOCAL) — no price or active-flag changes.

## Generator code (corvette_form_generator + scripts)
LOCAL-only fixes/features (lost if LIVE overwrote LOCAL):
- Unified --model entry points and module split.
- Replace-rule survival in grouped-excludes dedupe (rules.py, production.py).
- Production excludes dedupe against rule groups / exclusive groups (LIVE deduped only requires).
- Shared interior grouping for Stingray production (seat-label parent group, broad_interior_color_family fallback, R6X -> Custom Interior family).
- price_ref_component_type_key OptionType normalization (TwoTone/two_tone match).
- Variant overrides now honor status + active.
- Runtime-contract pipeline: write_runtime_contract_artifact, assert_runtime_contract/find_draft_only_fields; promotion loads artifact verbatim and refuses draft-only fields. NOTE: LIVE's promotion rows point at *-form-data-draft.json — they FAIL under LOCAL code until repointed (LOCAL workbook already repoints them; runtime-contract artifacts exist locally only).
- heuristic_section_step_key validation; expected_variant_count from MODEL_CONFIG; missing-CSV tolerance in read_interior_reference; red tabColor on generated sheets; workbook-first model_configs (base_model_config — requires workbook metadata sheets; with a workbook lacking model_master/model_workbook_sources/model_variants metadata it would resolve wrong sheet names, e.g. grand_sport_options vs grandSport_options).
- promote_model.py derives registry_key/slug/variants/artifact_path from workbook; no longer sets display_order=3; fails fast on missing rows.

LIVE-only features (lost if LOCAL overwrote LIVE):
1. review_flag end-to-end (output fields, form_* sheet columns, rule-source column, schema checks). LOCAL retired it deliberately.
2. schema_validation.py price_semantic block (6 checks: missing_price_semantic_column, unknown_price_semantic, included_zero_price_nonzero, self_trim_price_shape, package_price_by_component_shape, review_required_price_missing_flag) + lifecycle enforcement (normalization_reason, replacement_group_id, replacement_rule_id). LIVE is strictly newer here (06-06); these checks depend on workbook columns LOCAL removed. DECISION NEEDED: retire the columns (keep LOCAL) or keep the taxonomy (keep LIVE checks + restore columns). Cannot keep both as-is.
3. Production manual interior-includes rule synthesis (rule_{interior_id}_includes_{option_id}, R6X et al.) — LOCAL relies on workbook rule_mapping rows instead. Verify the workbook carries equivalent rows before merging, else includes rules silently disappear.
4. pr_d30_r6x_001 price-rule reordering (LIVE re-appended it last; LOCAL keeps sheet order).
5. Registry fallback when model_registry_promotion has no promoted rows (LOCAL hard-fails — arguably intentional).
6. Hardcoded model configs that work without workbook metadata (incl. GS special_rule_review_rpos tuple).
7. Dead code LOCAL deleted: load_standard_equipment_groups, load_component_price_rules, output.write_app_data, presentation_bucket field — low risk.

## Generated inspection artifacts
- grand-sport/z06 contract-preview + inspection JSON: timestamp-only noise.
- grand-sport-rule-audit.json: substantive — mirrors the J57/Z52 group delta.
- *-form-data-draft.json: review_flag removal + the J57 group; nothing else.
- LOCAL-only new artifacts: grand-sport-runtime-contract.json, z06-runtime-contract.json (and z06 per AGENTS.md).

## Merge decision list (the only real conflicts)
1. GS gs_group_j57_z52_requirement: keep (restore rows in LOCAL workbook + regen) or confirm intentional deletion.
2. review_flag / price_semantic / lifecycle taxonomy: LOCAL retired columns; LIVE added validation on them. Pick one contract; if retiring, drop LIVE's schema checks and migrate the live workbook columns out; if keeping, restore columns + checks on top of LOCAL structure.
3. Manual interior-includes rules (R6X etc.): verify LOCAL workbook rule_mapping covers what LIVE synthesized in code; otherwise data loss.
4. app.js requires_any preview: take LIVE.
5. Promotion artifact_path contract: LOCAL's runtime-contract path is the stricter, newer design; live workbook rows must be migrated with the code (they ship together or promotion breaks).

Everything else merges cleanly as: take LOCAL structure (refactor, workbook reorg, interior labels, dedupe/normalization fixes), then layer LIVE's app.js fix and resolve decisions 1–3.
