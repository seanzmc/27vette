# Python Parser Architecture Audit — Form-Data Generation

Date: 2026-06-09
Scope: `scripts/*.py` and `scripts/corvette_form_generator/*` — the pathway from `stingray_master.xlsx` workbook rows to generated form data (form_* sheets, form-output JSON, `form-app/data.js`).
Constraint honored: no workbook schema changes are proposed. Every recommendation works against the sheets that already exist (`model_master`, `model_workbook_sources`, `model_variants`, `model_registry_promotion`, and the per-model source sheets).

---

## 1. Executive Summary

The repository contains **two parallel parsers that build the same generated-data contract through different code**:

1. **Production path** — `generate_stingray_form.py` (1,554 lines, monolithic `main()`): reads source sheets, builds the contract inline, writes `form_*` sheets back into the workbook, writes `form-output/stingray-form-data.json`/`.csv`, and writes `form-app/data.js`.
2. **Draft/inspection path** — `corvette_form_generator/inspection.py` (2,135 lines): `inspect_model_sources()` → `build_contract_preview()` → `build_form_data_draft()`, used by `generate_grand_sport_form.py` and `generate_z06_form.py` to write artifacts under `form-output/inspection/`.

Both paths feed the *same* runtime registry: `model_registry_promotion` embeds Stingray as `current_generation` output and Grand Sport/Z06 as `draft_artifact` JSON. The runtime therefore serves three datasets produced by two different parsers that have already drifted in subtle ways (§3). Roughly **600–700 lines of `generate_stingray_form.py` are near-verbatim copies of `inspection.py` functions**, and the two per-model entry scripts are 91-line clones of each other.

The fix is structural, not cosmetic: collapse to **one parameterized pipeline** (`generate_form.py --model <key>`) built from the shared package, make the workbook metadata sheets the single source of model configuration (they already exist and already carry the data), and delete the dead/vestigial routes inventoried in §4. After that, adding a new Corvette model (ZR1/ZR1X are already scaffolded in `model_master`) requires **zero new Python files** — only workbook rows plus, at most, one interior-reference CSV.

---

## 2. Current Pathways (as-built)

```text
                          stingray_master.xlsx
                                  |
        +-------------------------+--------------------------+
        |                                                    |
  generate_stingray_form.py                    generate_grand_sport_form.py
  (inline parser, Stingray only)               generate_z06_form.py
        |                                      (clones; call inspection.py)
        |  writes                                            |  writes
        |   - form_* sheets (workbook)                       |   - form-output/inspection/*-inspection.{json,md}
        |   - form-output/stingray-form-data.{json,csv}      |   - *-contract-preview.{json,md}
        |   - form-app/data.js  <──────────────┐             |   - *-form-data-draft.{json,md}
        |                                      |             |
        +── build_app_data_registry()          |             |
              └─ registry_promotion.py reads   |             |
                 model_registry_promotion ─────┴── embeds draft JSON artifacts
                 (stingray=current_generation,      via live_contract_data()
                  grandSport/z06=draft_artifact)

  promote_z06_runtime.py  – hardcoded Z06 workbook mutation (model_master,
                            model_registry_promotion, variant_master)
  build_grand_sport_rule_sources.py – GS-only rule-source audit (config-driven
                            internally, but entry point pins GRAND_SPORT_MODEL)
  validate_workbook_schema.py / validate_workbook_package.py /
  repair_workbook_tables.py – thin CLIs over shared modules (healthy pattern)
```

Key structural observations:

- **The shared package is only half-adopted.** `mapping.py`, `workbook.py`, `runtime_metadata.py`, `registry_promotion.py`, and `output.py` are genuinely shared. But `inspection.py` is a second, draft-flavored implementation of the whole contract builder, and `generate_stingray_form.py` predates it and never migrated onto it.
- **A model's "production" status is determined by which parser produced its JSON**, not by a flag on one parser. Stingray data comes from the inline parser; Grand Sport and Z06 runtime data are draft artifacts laundered through `live_contract_data()` (strip provenance fields, flip `status` to `runtime_active`, rename the dataset). That function is an admission that the draft path produces almost-production output — it should simply *be* the production path with a mode switch.
- **Config lives in three places**: Python constants (`model_configs.py`), workbook metadata sheets, and scattered literals inside `generate_stingray_form.py`. `load_model_config_overrides()` reconciles the first two at runtime and raises if they drift — i.e., the code already treats the workbook as authoritative but still requires the Python constants to exist.

---

## 3. Duplication Inventory (DRY violations)

### 3.1 `generate_stingray_form.py` vs `inspection.py` — copy-pasted helpers

| Helper | Stingray copy | inspection.py copy | Drift? |
| --- | --- | --- | --- |
| `load_asset_map` | L98 | L77 | Yes — keying: `dict[target_id]` (per target_type arg) vs `dict[(target_type, target_id)]` |
| `context_choice_copy_rows` / `context_choice_info_tooltip` | L140–182 | L101–143 | Identical |
| `price_ref_key` / `price_ref_prices` | L366–379 | L231–244 | Identical |
| `price_ref_component_prices` / `price_ref_component_price` | L382–404 | L251–273 | **Yes — Stingray normalizes OptionType with `.lower()`; inspection uses `price_ref_component_type_key()` (regex strips non-alphanumerics). Same workbook cell can price differently per path.** |
| `r6x_price_component` / `generated_interior_price` | L407–423 | L276–292 | Identical |
| `INTERIOR_COMPONENT_LABELS` + `interior_component_metadata` | L426–501 | L47–55, L295–359 | Identical |
| `workbook_interior_component_metadata` | L504–528 | L362–386 | Identical |
| `clean_reference_label` / `read_interior_reference` / `seat_code_from_label` | L531–569 | L389–431 | Near-identical (inspection adds missing-file guard) |
| `grouping_fields_for_interior` | L572–606 | L465–507 | **Yes — inspection adds `coded_color_family`, an R6X "Custom Interior trim and seat combinations" family, and `parent_group = seat_label`; Stingray uses `levels[-2]` and has none of the R6X family logic. Interior grouping differs by model purely because of which parser ran.** |
| `truncate_reason` | L620 | L899 | Identical |
| `rows_from_optional_sheet` / `active_source_row` / `runtime_authored_rule` | L275–291 | L720–736 | Identical (and `runtime_metadata.optional_rows` is a third variant) |
| `load_rule_groups` / `load_exclusive_groups` | L294–344 | L814–864 | Identical except config plumbing |
| `grouped_requirement_pairs` | L347–355 | L867–883 | inspection generalizes to `grouped_rule_pairs` |
| body/trim context-choice construction | L805–860 | L1345–1399 | Near-identical inline blocks |
| `label_for` / `draft_label_for` | L609–617 | L906–913 | Identical in intent |
| rule-row assembly loop | L1105–1175 | `build_draft_rules` L916–993 | **Yes — see §3.3** |

### 3.2 Entry scripts and other duplicates

- `generate_grand_sport_form.py` and `generate_z06_form.py` are **91-line byte-level near-clones**; the only differences are the imported config constant, the rule-audit filename literals, and Z06 passing `"z06-inspection"` positionally where GS relies on the `artifact_prefix="grand-sport-inspection"` *default baked into shared code* (`write_inspection_artifacts`, inspection.py L1914). A model-specific default in a shared function is a trap: any future caller that forgets the argument silently writes Grand Sport-named artifacts.
- `registry_model_key()` ("grand_sport" → "grandSport") is defined **three times**: `generate_stingray_form.py` L60, `registry_promotion.py` L56, `runtime_metadata.py` L607 (`_registry_model_key`). `export_slug()` twice.
- `load_variant_option_overrides` exists as **two different functions with the same name and different schemas**: `runtime_metadata.py` L195 (returns status/selectable/active/display_behavior rows, used by Stingray) and `inspection.py` L754 (returns selectable/display_behavior/section_id/note keyed dict, used by draft path). Same sheet, two contracts — overrides of `status`/`active` are honored on the Stingray path and ignored on the draft path.
- `SPECIAL_REVIEW_RPOS = {"EL9","Z25","FEY","Z15"}` lives in `inspection.py` L46 **and** as `GRAND_SPORT_MODEL.special_rule_review_rpos` **and** in the workbook via `load_rule_review_rpos()` — three fallback layers for one set.
- `text_cleanup` dicts in `GRAND_SPORT_MODEL` and `Z06_MODEL` are identical literals.
- `model_configs.py` duplicates what the workbook already owns: `model_master`, `model_workbook_sources` (54 rows), `model_variants` (26 rows), and `model_registry_promotion` carry model label/year/dataset name, every sheet-role mapping, variant lists, and promotion state for all five models including inactive ZR1/ZR1X scaffolds. The Python constants restate it all, and `load_model_config_overrides()` exists solely to reconcile the two.

### 3.3 Behavioral drift between the two rule builders

The Stingray inline loop and `build_draft_rules()` disagree on dedupe semantics:

- Stingray suppresses a `requires` rule only when the pair is covered by an active `requires_any` rule group. The draft path additionally suppresses `excludes` pairs covered by `excludes_any` groups **or exclusive-group membership** (unless `generation_action == "preserve_runtime_exclude"`).
- Stingray injects `manual_rules` (interior → included-option `includes` rows, R6X copy hardcoded); the draft path has no equivalent.
- Stingray filters rules touching `hidden_option_ids`; the draft path filters on `valid_ids` membership instead.

None of these differences are model business rules — they are parser-generation differences that should be decided once and applied to every model.

---

## 4. Non-Functional and Vestigial Routes (verified)

Each item below was verified against the working tree on 2026-06-09.

1. **`refresh_grand_sport_registry_source()` — explicit no-op.** `generate_stingray_form.py` L203–204 (`def ...: return`), still called at L1506. Delete both.
2. **`output.write_app_data()` — unreferenced.** Grep across `scripts/` and `tests/` finds only the definition (output.py L13). Legacy single-model writer superseded by `write_app_data_registry`. Delete.
3. **`build_grand_sport_interiors()` — pure alias** of `build_model_interiors` (inspection.py L609–610), called once. Inline the call; the alias name actively misleads now that Z06 uses it via `LZ_Interiors`.
4. **The `pr_d30_r6x_001` filter/re-extend is a functional no-op.** L694–695 remove the row from `price_rules_raw`; L749 appends it back before any consumer reads the list. Net effect: the row moves to the end of the list (and thus of the `form_price_rules` sheet). If ordering is intentional, it deserves a comment and a sort key; otherwise delete three lines. Either way, it is a hardcoded RPO literal in the parser (§5).
5. **The legacy registry fallback is unreachable in practice.** `build_app_data_registry()` L224–246 (hand-built registry) and `load_grand_sport_registry_data()` L185–200 (which *re-parses `data.js` with string splitting* to recover Grand Sport data) only execute when `model_registry_promotion` has no rows. The sheet has five rows and three active promotions, and `load_registry_promotions()` is documented as authoritative once rows exist. The string-split parse of a generated JS file is the most fragile route in the repo and is dead weight. Replace the fallback with a hard error ("promotion sheet is empty — refusing to guess the registry") and delete both functions.
6. **`coded_color_family(interior, fallback_label)` ignores its first parameter** (inspection.py L461–462) — a stub left from a removed code path. Collapse into `broad_interior_color_family`.
7. **Markdown renderers hardcode Grand Sport.** `render_markdown_report`, `render_contract_preview_markdown`, and `render_form_data_draft_markdown` emit literal `# Grand Sport Inspection` / `# Grand Sport Contract Preview` / `# Grand Sport Form Data Draft` headings and "Grand Sport row..." messages. Consequence on disk today: `form-output/inspection/z06-inspection.md`, `z06-contract-preview.md`, and `z06-form-data-draft.md` are all titled **Grand Sport**. Same for unresolved-issue messages inside `build_contract_preview` ("Grand Sport row has no resolved section" fires for every model). Parameterize with `config.model_label`.
8. **Stingray ignores `config.interior_source_sheet`.** `generate_stingray_form.py` L696 reads the literal `"lt_interiors"` even though the config field (and the workbook `model_workbook_sources` role) exists and the draft path honors it. Harmless today, a landmine for any config-driven future.
9. **`active_interior_flags()` carries a Stingray-shaped hack** (inspection.py L522–525): every model's interiors emit both `active_for_stingray` and `active_for_{model_key}`. The contract field should be model-neutral (`active_for_model` + `model_key`), with `active_for_stingray` preserved only by the Stingray emitter if the runtime still reads it.
10. **`promote_z06_runtime.py` is a one-model script for a generic operation.** Everything it writes (dataset name, registry key, slug, artifact path, variant list) is derivable from `model_master`/`model_variants` plus `--model z06`. As written, promoting ZR1 means cloning another 167-line file.
11. **Heuristic step placement is a silent fallback on one path and an error on the other.** `mapping.step_for_section` falls back to keyword sniffing ("stripe", "spoiler", "lpo", "exhaust"...). The preview path flags `heuristic_section_step_key` as an error; the Stingray production path uses the same heuristic silently. One policy should apply: heuristics are a validation error everywhere (the workbook owns placement via `section_presentation`/`section_master`).
12. **`SECTION_STEP_OVERRIDES` mixes model-specific sections into a shared constant** (`sec_gsce_001`, `sec_gsha_001` are Grand Sport sections living in the map used by every model). With `section_presentation` workbook rows now owning step placement, this whole constant is a fallback that should shrink toward empty rather than grow.

---

## 5. Model-Specific Literals Inside the Parser

The README's own architecture rule is "Scripts should stay procedural and general... Do not add model-specific business exceptions to Python." Current violations in `generate_stingray_form.py`:

- `pr_d30_r6x_001` price-rule ID (L694–695, L749)
- `opt_r6x_001` / R6X copy text in `manual_rules` (L1087–1104)
- `sec_colo_001` as hardcoded `target_section` for injected includes (L1096)
- `sec_stan_002` ranking inside `standard_equipment_preference` (L633–642)
- `"Expected 6 active Stingray variants"` floor (L1209) — should use `config.expected_variant_count` (the draft path already does)
- R6X trim-string conventions (`_R6X` suffix arithmetic) spread across both parsers — acceptable as a shared *generic* pricing concept, but it should live in exactly one pricing module

These either move into workbook rows the schema already supports (the interior-includes rules belong in `rule_mapping`/`interior_components`, which already model includes), or become config-driven generic mechanisms.

---

## 6. Recommended Target Architecture

### 6.1 One pipeline, one entry point

Replace `generate_stingray_form.py`, `generate_grand_sport_form.py`, and `generate_z06_form.py` with a single CLI:

```sh
.venv/bin/python scripts/generate_form.py --model stingray            # production emit
.venv/bin/python scripts/generate_form.py --model z06 --mode draft    # inspection-only
.venv/bin/python scripts/generate_form.py --all                       # every promoted model
```

Pipeline stages, each a pure function over `(workbook rows, ModelConfig)`:

```text
resolve_config(wb, model_key)        # workbook metadata sheets are the source of truth
  -> extract(wb, config)             # raw sheet rows, per configured sheet roles
  -> normalize(raw, config)          # statuses, text cleanup, overrides — ONE implementation
  -> build_contract(normalized)      # variants, steps, sections, contextChoices, choices,
                                     # standardEquipment, ruleGroups, exclusiveGroups, rules,
                                     # priceRules, interiors, colorOverrides, validation
  -> validate(contract, config)      # same checks for every model
  -> emit(contract, config, mode)    # mode=draft  -> inspection artifacts only
                                     # mode=production -> form_* sheets, JSON, CSV, data.js registry
```

The decisive simplification: **`mode` selects emitters, never builders.** The contract for a draft Z06 and a production Stingray is computed by the same code; only what gets written differs. `live_contract_data()` shrinks to nothing because the production emitter never wrote draft provenance in the first place — draft-only fields are added by the draft emitter, not stripped by the promoter.

The current inspection report (`inspect_model_sources`) remains valuable as a separate read-only stage; keep it as `--report` output of the same CLI rather than a separate code path.

### 6.2 Package layout after consolidation

```text
scripts/corvette_form_generator/
  workbook.py          (unchanged: clean/money/intish/rows_from_sheet/write_sheet/save_workbook_safely)
  model_config.py      (dataclass; shrinks — see 6.3)
  config_loader.py     (resolve_config: workbook-first; replaces model_configs.py constants)
  pricing.py           (price_ref_*, r6x_price_component, generated_interior_price — single copy,
                        single OptionType normalization = price_ref_component_type_key)
  interiors.py         (read_interior_reference, grouping_fields_for_interior,
                        build_model_interiors — one implementation, one grouping policy)
  rules.py             (load_rule_groups/exclusive_groups, grouped_rule_pairs,
                        build_rules — one dedupe policy for requires AND excludes)
  contract.py          (choices/sections/steps/context choices/standard equipment)
  runtime_metadata.py  (unchanged loaders; absorb the single load_variant_option_overrides)
  validation.py        (unchanged + the shared validation checks)
  registry.py          (registry_promotion.py + output.py merged; delete write_app_data;
                        single registry_model_key/export_slug)
  render.py            (markdown renderers, parameterized by config.model_label)
  inspection.py        (shrinks to inspect_model_sources + report rendering)
scripts/
  generate_form.py     (the one entry point)
  promote_model.py     (generalized promote_z06_runtime.py: --model <key> [--write])
  build_rule_sources.py (generalized from build_grand_sport_rule_sources.py: --model <key>;
                        it is already config-driven internally — only the entry pins GS)
  validate_workbook_schema.py / validate_workbook_package.py / repair_workbook_tables.py (keep)
```

### 6.3 Configuration strategy (no new workbook schema)

The workbook already owns everything model-specific through existing sheets; the goal is to stop restating it in Python.

- **Delete the per-model constants** `STINGRAY_MODEL` / `GRAND_SPORT_MODEL` / `Z06_MODEL`. Replace with one `DEFAULT_MODEL_CONFIG` (paths, `STEP_ORDER`, `STEP_LABELS`, `CONTEXT_SECTIONS`, `SELECTION_MODE_LABELS`, default sheet-role names) plus `resolve_config(wb, model_key)` which is today's `load_model_config_overrides` made *primary* instead of *override*: model label/year/dataset name from `model_master`; every sheet role from `model_workbook_sources` (rows exist for all three active models); variants from `model_variants`; promotion state from `model_registry_promotion`. Python keeps only what the workbook genuinely cannot express — filesystem paths and cross-model presentation constants that `runtime_steps`/`context_section_master`/`section_presentation` rows already override at runtime anyway.
- **Derive, don't declare, artifact names.** `preview_artifact_prefix`, `draft_artifact_prefix`, the rule-audit paths, and the inspection prefix are all `f"{export_slug}-contract-preview"`-shaped strings. One `artifact_prefix(config, kind)` helper removes four config fields and the dangerous Grand Sport default argument.
- **Collapse the three-layer special-RPO fallback** to two: workbook `load_rule_review_rpos` first, one shared Python default second. Same for `text_cleanup`: one shared default dict, enabled per model by a single boolean (or a workbook metadata row later — not required now).
- **Result for a new model (e.g., ZR1, already scaffolded inactive in `model_master`):** author the source sheets (`zr1_options`, `zr1_ovs`, `zr1_rule_mapping`, ...), add/activate the metadata rows that already have placeholders, optionally add `architectureAudit/zr1_interiors_refactor.csv`, then `generate_form.py --model zr1 --mode draft` → review → `promote_model.py --model zr1 --write` → `generate_form.py --model stingray` to refresh the registry. **No Python edits.**

### 6.4 Single policies to ratify during unification

Because the two parsers drifted, consolidation forces four decisions (recommendations included):

1. **PriceRef OptionType normalization:** use `price_ref_component_type_key` (regex) everywhere — it is the superset of `.lower()` and matches more workbook formatting.
2. **Rule dedupe:** adopt the draft path's behavior (suppress grouped requires *and* grouped/exclusive excludes, honoring `preserve_runtime_exclude`) for all models — it is the newer, more workbook-aware policy. Verify against the Stingray regression test before switching.
3. **Interior grouping:** adopt the inspection version of `grouping_fields_for_interior` (R6X custom family, `coded_color_family` fallback) for all models; confirm Stingray output diffs are intended improvements rather than regressions.
4. **Variant option overrides:** one loader, one field set (the union: status, selectable, active, display_behavior, section_id, note), one application function (`apply_variant_option_override` extended to cover status/active).

`manual_rules` (interior-includes injection) should be retired by authoring those `includes` rows in `rule_mapping` — the sheet and `interior_components` already express this; the validation check `missing_r6x_included_option_*` already polices it.

---

## 7. Migration Plan (safe, incremental)

Each phase ends green on the existing gates: `node --test tests/*.test.mjs` (Stingray regression + stability, GS/Z06 artifact tests, multi-model switching) and `pytest tests/test_*_metadata.py`.

**Phase 0 — Pin behavior.** Add a parity harness: run the current Stingray generator, snapshot `stingray-form-data.json` and `data.js`; these are the diff baseline for every later phase. (The existing `stingray-generator-stability.test.mjs` partially covers this; extend it to full-document comparison for the migration window.)

**Phase 1 — Delete the dead routes** (§4 items 1, 2, 3, 4, 6; renderer parameterization in item 7; literal sheet name in item 8). Zero behavior change except corrected Z06 markdown titles. Re-run Z06/GS generators to refresh mislabeled artifacts.

> **STATUS: COMPLETED 2026-06-09.** Removed `refresh_grand_sport_registry_source` no-op, `write_app_data`, `build_grand_sport_interiors` alias, `coded_color_family` stub, and the `pr_d30_r6x_001` filter/re-extend; replaced the `"lt_interiors"` literals with `MODEL_CONFIG.interior_source_sheet`; parameterized all markdown renderers and preview messages by `model_label`; made `write_inspection_artifacts`'s `artifact_prefix` required (GS entry now passes it explicitly). GS/Z06 inspection artifacts regenerated — Z06 markdown now correctly titled; the Grand Sport draft JSON is byte-identical apart from timestamps, confirming no behavior change. Verified: stingray regression + stability (94 pass), GS preview/draft/rule-audit (34 pass), Z06 preview/draft/runtime suites (57 pass), multi-model switching (40 pass), audit-parser loaders (5 pass), workbook package validation clean, Python metadata tests 25/25. Note: removing the price-rule no-op returns `pr_d30_r6x_001` to its source-sheet position in `form_price_rules`/`priceRules` ordering on the next Stingray regeneration (tests assert membership and count, not order). `workbook-schema-standardization.test.mjs` was not run in the audit sandbox (pre-existing validator runtime exceeds the sandbox shell cap); its inputs and code are untouched by this phase — run it locally with the project venv.

**Phase 2 — Extract shared modules.** Move the §3.1 duplicate helpers out of `generate_stingray_form.py` into `pricing.py`/`interiors.py`/`rules.py`/`contract.py`, importing the inspection implementations where identical. Where drifted (§6.4), keep the Stingray behavior temporarily behind an explicit flag so the parity diff stays empty.

> **STATUS: COMPLETED 2026-06-09.** New modules: `pricing.py` (PriceRef lookups, R6X arithmetic — single regex-based OptionType normalization adopted directly because audit of `PriceRef`/`interior_components` showed Stingray rows never use the formatting variants that distinguish it from `.lower()`, and the parity diff confirmed identical output), `interiors.py` (reference CSV parsing, component metadata, `build_model_interiors`, and `grouping_fields_for_interior` carrying the one drift flag: `legacy_stingray=True`, to be ratified away in Phase 4), `rules.py` (group loaders, pair derivation, `build_draft_rules`), `contract.py` (asset maps, context-choice builders, unified `label_for` with `rpo_fallback_to_id` flag). `workbook.py` gained `rows_from_optional_sheet` and `workbook_truthy`. `generate_stingray_form.py` shrank 1,069 → ~470 effective lines of duplicated helper code removed (603 lines net) and `inspection.py` lost 772 lines; net −1,290/+114 across the phase. Dead `option_key()` discovered and removed. One test updated: `grand-sport-draft-data.test.mjs` source-shape assertions for interior building now point at `interiors.py` (the owning module) instead of `inspection.py`; behavioral assertions unchanged. **Parity proof:** Stingray `form-data.json`, `.csv`, and `data.js` regenerated on Phase 1 vs Phase 2 code are byte-identical apart from `generated_at`; all six GS/Z06 inspection JSON artifacts show zero non-timestamp diff. Gates green: stingray regression+stability 94, GS suites 34, Z06 suites 61, multi-model switching 40, metadata loaders 5, visual-copy standardization 4, Python metadata tests 25. Remaining drift flags to ratify in Phase 4: `legacy_stingray` interior grouping, `rpo_fallback_to_id` labels, rule-dedupe policy (stingray inline loop vs `rules.build_draft_rules`), and the two `load_variant_option_overrides` variants.

**Phase 3 — Single entry point.** Create `generate_form.py`; make the three existing scripts thin shims that call it (preserving documented commands in README/AGENTS), then update docs and delete the shims. Merge the two 91-line clones first — that is pure win with no behavioral risk.

**Phase 4 — Ratify the §6.4 policies.** Flip the flags one at a time, reviewing the Stingray contract diff for each, with workbook fixes (e.g., authoring the interior-includes rules) landing alongside.

**Phase 5 — Workbook-first config.** Replace `model_configs.py` constants with `resolve_config`; delete the legacy registry fallback (§4.5) and replace with a hard error; generalize `promote_z06_runtime.py` → `promote_model.py` and `build_grand_sport_rule_sources.py` → `build_rule_sources.py --model`.

**Phase 6 — Retire `live_contract_data` stripping** by moving draft-only fields into the draft emitter, and tighten `valid step keys`/heuristic placement into a uniform validation error.

---

## 8. Expected Outcomes

- `generate_stingray_form.py` (1,554 lines) + two 91-line clones + `promote_z06_runtime.py` (167) collapse into one ~150-line CLI over the package; net deletion on the order of 1,200–1,500 lines.
- One parser produces every model's contract; "draft vs production" becomes an emit-time flag, so promoted draft artifacts and generated production data can no longer drift.
- Pricing, interior grouping, rule dedupe, and override semantics are each defined exactly once.
- Adding a Corvette model is a workbook-authoring task with a two-command pipeline, matching the README's stated direction ("migrating business rules and runtime metadata out of Python... into workbook-authored data") and the existing ZR1/ZR1X scaffolds.
