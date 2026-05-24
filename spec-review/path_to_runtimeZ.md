# Path to Runtime: Z06, ZR1, ZR1X

Audit complete. No file or workbook edits made.

Durable project fact recorded: Z06, ZR1, and ZR1X reuse Grand Sport compatibility rules and exclusive groups. Real differences are option set and standard/included availability.

---

## Current State

### Branch / Repo

| Item | Value |
|------|-------|
| Branch | `schemaHarden` |
| Repo status | clean |
| Excel lock file | none |
| Schema validation | `valid`, `issue_count: 0` |

```
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

### Runtime Registry

`form-app/data.js` currently exposes:

- Default model: `stingray`
- Runtime models: `stingray`, `grandSport`
- `window.STINGRAY_FORM_DATA` alias still matches Stingray data
- **Z06, ZR1, and ZR1X are not in runtime.**

### Future Model Workbook State

**`model_master`** — inactive rows for: `z06`, `zr1`, `zr1x`

**`model_variants`** — already mapped:

| Model | Count | Variants |
|-------|-------|----------|
| Z06 | 6 | `1lz_h07`, `2lz_h07`, `3lz_h07`, `1lz_h67`, `2lz_h67`, `3lz_h67` |
| ZR1 | 4 | `1lz_r07`, `3lz_r07`, `1lz_r67`, `3lz_r67` |
| ZR1X | 4 | `1lz_s07`, `3lz_s07`, `1lz_s67`, `3lz_s67` |

**`model_workbook_sources`** — inactive source-role rows for all three future models.

**`model_registry_promotion`** — inactive/unpromoted rows for all three future models.

### Future Source Sheets

Header-only, empty normalized sheets exist for all three:

- `z06_options`, `z06_ovs`, `rules`, `price rules`, `groups`, `exclusives`, `variant overrides`
- `zr1_options`, `zr1_ovs`, `rules`, `price rules`, `groups`, `exclusives`, `variant overrides`
- `zr1x_options`, `zr1x_ovs`, `rules`, `price rules`, `groups`, `exclusives`, `variant overrides`

All are currently **0 data rows**.

### Archive / Preview State

**Hidden archive sheets:**

| Sheet | Rows |
|-------|------|
| `archive_Z06_Ingest` | 363 |
| `archive_ZR1_Ingest` | 336 |
| `archive_ZR1X_Ingest` | 337 |

**Phase 5 preview artifacts:**

- `form-output/inspection/future-model-source-preview.json`
- `form-output/inspection/future-model-source-preview.md`

### Preview Summary

| Metric | Z06 | ZR1 | ZR1X |
|--------|-----|-----|------|
| Proposed options | 363 | 336 | 337 |
| Proposed OVS rows | 2178 | 1344 | 1348 |
| Status: available | 910 | 450 | 442 |
| Status: standard | 990 | 684 | 692 |
| Status: unavailable | 278 | 210 | 214 |
| Section resolved | 240 | 212 | 212 |
| Section conflict | 14 | 14 | 14 |
| Section unresolved | 109 | 110 | 111 |
| Missing RPO | 52 | 52 | 52 |
| Duplicate RPO rows | 156 | 162 | 164 |

### Grand Sport Canonical Rule State

| Sheet | Count |
|-------|-------|
| `grandSport_rule_mapping` | 321 rows (excludes: 243, includes: 55, requires: 23) |
| `grandSport_exclusive_groups` | 9 active groups |
| `grandSport_exclusive_members` | 26 active members |
| `grandSport_rule_groups` | 1 active grouped exclusion |
| `grandSport_rule_group_members` | 18 active members |
| `grandSport_variant_overrides` | 13 rows |

### Interior State

| Sheet | Detail |
|-------|--------|
| `LZ_Interiors` | hidden, 132 rows |
| `model_interior_scope` active | `grand_sport`: 132 |
| `interior_components` active | `stingray`: 197, `grand_sport`: 198 |

No active Z06/ZR1/ZR1X interior scope/component rows yet.

### Runtime Metadata Gaps

- `runtime_steps` — Stingray and Grand Sport only
- `context_section_master` — Stingray and Grand Sport only
- `section_presentation` — Stingray and Grand Sport only
- `order_summary_sections` — Stingray only
- `step_order_summary_map` — Stingray only
- `asset_map` — Stingray and Grand Sport only, no future model rows
- `runtime_rule_exceptions` — Stingray only
- `model_presentation` sheet does not exist yet
- `form-app/app.js` — hardcoded setup highlight copy for Stingray and Grand Sport only
- `form-app/app.js` — hardcoded GBA / `opt_zyc_001` runtime exception
- Runtime order-summary fallback still works as compatibility fallback, but new promoted models should have generated `data.orderSummary`

### Generator State

- Registry promotion is workbook-owned through `model_registry_promotion`
- Schema validation is metadata-aware enough to validate source/promotion scaffolds
- No generic `generate_model_form.py` yet
- `scripts/generate_grand_sport_form.py` still imports `GRAND_SPORT_MODEL`
- `scripts/build_grand_sport_rule_sources.py` still imports `GRAND_SPORT_MODEL`
- `ModelConfig` constants only define Stingray and Grand Sport as Python constants, though workbook metadata exists for future models

---

## Main Verdict

Next work is mostly **not runtime work**. It is source-data normalization and model-draft generation.

Because Z06, ZR1, and ZR1X share Grand Sport compatibility and exclusive-group behavior, do not spend effort rediscovering those rules from raw order-guide text. Treat Grand Sport as the canonical compatibility/exclusive template and rebase it onto each future model only after each model's option IDs are resolved.

**Accuracy-critical work:**

1. Turn archive rows into correct normalized `*_options` and `*_ovs`
2. Resolve section placement, missing-RPO rows, duplicate RPO identities, and standard/available/unavailable status
3. Wire LZ interiors and model-scoped runtime metadata
4. Copy/rebase Grand Sport compatibility/exclusive groups through an ID resolver
5. Generate draft contracts
6. Promote only after review

---

## Todo List: Z06, ZR1, ZR1X to Runtime

### 1. Freeze the Rule Strategy

- Record Grand Sport as the compatibility/exclusive canonical template for:
  - `*_rule_mapping`
  - `*_rule_groups`
  - `*_rule_group_members`
  - `*_exclusive_groups`
  - `*_exclusive_members`
- Do not parse raw Z06/ZR1/ZR1X detail text as primary rule source for compatibility
- Use raw detail text only as audit/provenance and to catch option-specific includes or model-only packages not part of shared compatibility
- Add tests later proving future model compatibility/exclusive contracts match Grand Sport after source/target ID rebasing

---

### 2. Create a Human-Review Mapping Layer for Phase 5 Preview Output

Add a review-owned mapping table before writing normalized rows.

**Recommended workbook sheet:** `future_model_source_review`

**Suggested columns:**

| Column | Purpose |
|--------|---------|
| `model_key` | |
| `archive_sheet` | |
| `archive_row` | |
| `rpo` | |
| `source_option_name` | |
| `source_category` | |
| `candidate_option_id` | |
| `approved_option_id` | |
| `approved_section_id` | |
| `review_status` | |
| `review_reason` | |
| `copy_from_model_key` | |
| `copy_from_option_id` | |
| `notes` | |
| `active` | |

**This should resolve:**

| Issue | Z06 | ZR1 | ZR1X |
|-------|-----|-----|------|
| Unresolved section rows | 109 | 110 | 111 |
| Section conflicts | 14 | 14 | 14 |
| Missing-RPO rows | 52 | 52 | 52 |
| Duplicate-RPO rows | 156 | 162 | 164 |

**Priority review examples:**

- `UQT` section conflict
- `AQ9` / `AH2` seat section conflicts
- `B4Z` / `G0K` standard vs included placement conflicts
- `SC7` LPO Exterior vs LPO Interior conflict
- `DY0`, `N3W`, `CFV`, `LT6`, `R8E`, `SOE`, `FE6`, `M1M` unresolved rows
- All missing-RPO standard-equipment rows

---

### 3. Populate Normalized Option and OVS Source Sheets

After review mapping is approved, write source rows into:

- `z06_options`, `z06_ovs`
- `zr1_options`, `zr1_ovs`
- `zr1x_options`, `zr1x_ovs`

**`*_options` owns:**

- Stable `option_id`
- RPO
- Price when directly owned by option
- Polished label/description
- Raw detail provenance
- Final `section_id`
- `selectable`/`display`/`active` flags
- Display order

**`*_ovs` owns:**

- Exact variant availability: `available`, `standard`, `unavailable`

**Rules:**

- Standard equipment stays as status data in OVS — not separate runtime hardcoding
- Do not write unresolved rows into final source sheets unless clearly marked inactive/review

**Validation:**

- Option count matches reviewed expected count
- OVS row count equals reviewed option rows × variant count unless intentionally scoped
- No blank variant statuses
- No unknown statuses
- All active source rows have valid `section_id`
- All active OVS rows reference known `option_id` and model variant

---

### 4. Create a Deterministic Option-ID Resolver Against Grand Sport

Needed before copying rules. Build model-specific maps:

- Grand Sport `option_id` → Z06 `option_id`
- Grand Sport `option_id` → ZR1 `option_id`
- Grand Sport `option_id` → ZR1X `option_id`

**Match priority:**

1. Exact reviewed `copy_from_option_id`
2. Exact RPO + same semantic section
3. Exact RPO + reviewed duplicate group
4. Manual review override
5. Unresolved — do not copy rule/member

**Output review artifact:**

- Resolved mappings
- Missing Grand Sport source options per target model
- Duplicate candidate mappings
- Target options with no Grand Sport equivalent
- Rules/groups that cannot be copied safely

> This is the key safety step. Grand Sport rules may be shared, but rule rows reference option IDs — not just RPOs.

---

### 5. Rebase Grand Sport Compatibility Rules for Each Future Model

**Populate** from `grandSport_rule_mapping` using the GS → target option-ID resolver:

- `z06_rule_mapping`
- `zr1_rule_mapping`
- `zr1x_rule_mapping`

**Preserve:**

- `rule_type`, `target_type`, `target_selection_mode`, `source_selection_mode`
- `generation_action`
- Body/trim/variant scopes where still meaningful
- `runtime_action`, `disabled_reason`, review/provenance notes

**Rewrite:**

- `rule_id` with model prefix
- `source_id`, `target_id`
- Any scope values that use Grand Sport variant IDs

**Do not copy a rule if:**

- Source option cannot resolve
- Target option cannot resolve
- Grand Sport rule references a GS-only package not present in target model
- Variant scope cannot map cleanly

**Expected outcome:** compatibility behavior matches Grand Sport where options exist; unresolved cases are explicit review rows, not silent omissions.

---

### 6. Rebase Grand Sport Grouped Rules

**Populate** from `grandSport_rule_groups` / `grandSport_rule_group_members`:

- `z06_rule_groups`, `z06_rule_group_members`
- `zr1_rule_groups`, `zr1_rule_group_members`
- `zr1x_rule_groups`, `zr1x_rule_group_members`

Current Grand Sport grouped rule: `gs_group_z15_excludes_non_center_stripes` (18 active members)

**Rewrite:**

- Group IDs with model prefix
- Source option ID via resolver
- Member target IDs via resolver
- Scopes where applicable

---

### 7. Rebase Grand Sport Exclusive Groups

**Populate** from `grandSport_exclusive_groups` / `grandSport_exclusive_members`:

- `z06_exclusive_groups`, `z06_exclusive_members`
- `zr1_exclusive_groups`, `zr1_exclusive_members`
- `zr1x_exclusive_groups`, `zr1x_exclusive_members`

**Current active Grand Sport groups:**

- LS6 engine covers
- Center caps
- Indoor car covers
- Rear script badges
- Suede compartment liners
- Ground effects
- Z52 packages
- Exterior accents
- Performance brakes

**Rewrite:** group IDs with model prefix, member option IDs via resolver, display order and selection mode preserved.

**Review carefully:**

- Engine-cover group naming may not be LS6 for Z06/ZR1/ZR1X if engine/package naming differs
- Group behavior can be identical while notes/customer copy should be model-appropriate

---

### 8. Build Price Rules from Future Model Price Schedule

Do not blindly copy all Grand Sport price rules.

**Populate:**

- `z06_price_rules`
- `zr1_price_rules`
- `zr1x_price_rules`

**Use:**

- Future model price schedule / raw order guide pricing
- Reviewed options
- Scoped conditions where same RPO has different price by model/body/trim/interior

**Copy Grand Sport price-rule patterns only when:**

- The same target option exists
- The same contextual pricing behavior applies
- The actual price value is verified for the future model

---

### 9. Handle Variant Overrides as Model-Specific Cleanup

**Populate:**

- `z06_variant_overrides`
- `zr1_variant_overrides`
- `zr1x_variant_overrides`

**Use for:**

- Duplicate/canonical row suppression
- Selectable/display behavior that differs by trim/body
- Section overrides for ambiguous duplicate RPOs

> Do not use variant overrides to hide bad source normalization. If a row should be inactive or split, fix the source option/OVS row first.

---

### 10. Wire LZ Interiors per Model

**Current blocker:** `LZ_Interiors` exists, but future models have no active interior scope/component rows.

**Add active rows for `model_interior_scope`:** `z06`, `zr1`, `zr1x`

**Add active rows for `interior_components`:** `z06`, `zr1`, `zr1x`

**Also activate** each future model's `model_workbook_sources.interior_source_sheet = LZ_Interiors`

**Review:**

- Z06 has 1LZ/2LZ/3LZ
- ZR1 and ZR1X have 1LZ/3LZ only
- `LZ_Interiors` includes trims: `1LZ`, `2LZ`, `3LZ`, `3LZ_R6X`
- Scope rows must not expose 2LZ interiors to ZR1/ZR1X if those trims do not exist
- Component pricing must still use `PriceRef` correctly
- R6X/D30 behavior must be verified per model

---

### 11. Add Runtime Metadata Rows for Future Models

Before runtime promotion, add model-scoped rows for:

- `runtime_steps`
- `context_section_master`
- `section_presentation`
- `order_summary_sections`
- `step_order_summary_map`
- `asset_map`
- `default_selection_rules` (if needed)
- `runtime_rule_exceptions` (only if actually needed)

Likely copy from Grand Sport where same step/section behavior applies: runtime steps, context section model/body/trim setup, section presentation, standard-equipment grouping, selected-RPO summary grouping.

**Must fix before promotion:**

- `order_summary_sections` and `step_order_summary_map` are Stingray-only — new models should not rely on runtime fallback
- `asset_map` needs at least model selector images for Z06/ZR1/ZR1X if UI should look complete
- Runtime setup highlight copy is still hardcoded for Stingray/Grand Sport only

---

### 12. Move Model Presentation Highlights into Workbook/Generated Data

**Current runtime hardcode:** `form-app/app.js:104` has Stingray/Grand Sport `vehicleSetupHighlights`.

Before adding three more models, either:

- ✅ **Preferred:** create `model_presentation` workbook sheet and emit generated highlight metadata
- ❌ **Not preferred:** knowingly add temporary runtime copy for Z06/ZR1/ZR1X

**Preferred sheet:** `model_presentation`

**Suggested columns:**

| Column | |
|--------|--|
| `model_key` | |
| `eyebrow` | |
| `title` | |
| `description` | |
| `fact_1` | |
| `fact_2` | |
| `fact_3` | |
| `active` | |
| `display_order` | |
| `source_note` | |

**Runtime should render:** generated model presentation when present; fallback only for old data.

---

### 13. Generalize the Grand Sport Draft Generator

**Add:** `scripts/generate_model_form.py --model-key <model_key>`

**Keep:** `scripts/generate_grand_sport_form.py` as wrapper/alias.

**Generic generator must:**

- Load `ModelConfig` from workbook metadata
- Read model source sheets from `model_workbook_sources`
- Generate inspection, contract-preview, and draft form-data artifacts for any active model
- Support LZ interiors through `interior_source_sheet`
- Use model-specific artifact prefixes: `z06-form-data-draft`, `zr1-form-data-draft`, `zr1x-form-data-draft`

> Required so new models can reach runtime without new one-off Python constants.

---

### 14. Generalize Grand Sport Rule Audit Tooling

**Add:** `scripts/build_model_rule_sources.py --model-key <model_key>`

**Keep:** `scripts/build_grand_sport_rule_sources.py` as compatibility wrapper.

**Use to audit:**

- Copied Grand Sport rule parity
- Unresolved source/target option mappings
- Exclusive group member parity
- Model-specific missing options
- Price-rule review needs

---

### 15. Activate Source Metadata Only After Source Sheets Are Populated

Once normalized future source sheets contain reviewed rows:

- Set future source-role rows active in `model_workbook_sources`
- Set `model_master.active = TRUE`

Do not promote to runtime yet. Run:

```
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

**Expected:**

- Future source sheets validated by active metadata
- No header drift
- No broken option/OVS/rule references

---

### 16. Generate Draft Artifacts for Each Future Model

```bash
.venv/bin/python scripts/generate_model_form.py --model-key z06
.venv/bin/python scripts/generate_model_form.py --model-key zr1
.venv/bin/python scripts/generate_model_form.py --model-key zr1x
```

**Expected artifacts:**

```
form-output/inspection/z06-inspection.json
form-output/inspection/z06-contract-preview.json
form-output/inspection/z06-form-data-draft.json
# matching .md files
# matching ZR1/ZR1X artifacts
```

**Review for each:**

- Variants, choices, standard equipment
- Rules, price rules, exclusive groups
- Interiors
- Validation warnings/errors
- Unresolved normalization issues

---

### 17. Add Parity and Model-Specific Contract Tests

**Add tests for:**

- Z06/ZR1/ZR1X source sheet headers and active metadata
- OVS variant coverage
- No unresolved active section IDs
- Generated draft artifacts have correct variant counts
- Generated standard equipment counts match source OVS standard statuses
- Grand Sport compatibility rules rebase cleanly:
  - Same count or explicit reviewed exceptions
  - No source/target IDs pointing back to Grand Sport
  - No unresolved copied rules
- Exclusive group parity:
  - Same selection modes as Grand Sport
  - All copied members resolve
  - Group IDs are model-prefixed
- LZ interiors:
  - Z06 sees 1LZ/2LZ/3LZ scope
  - ZR1/ZR1X do not expose 2LZ
  - R6X component pricing remains correct
- Runtime registry excludes future models until promotion rows are enabled
- Runtime registry includes all five models after promotion rows are enabled

---

### 18. Promote One Model at a Time

**Suggested promotion order:** Z06 → ZR1 → ZR1X

**Reason:**

- Z06 has 6 variants like Grand Sport — will shake out LZ/option normalization with less variant-count difference risk
- ZR1/ZR1X have 4 variants — should follow once generic 4-variant model generation is proven

**For each promotion:**

- Set `model_registry_promotion.active = TRUE`
- Set `promoted_to_runtime = TRUE`
- Set `artifact_path` to the reviewed draft artifact
- Keep `default_model = FALSE`
- Regenerate `form-app/data.js` through the Stingray generator/registry writer

---

### 19. Runtime Verification After Promotion

For each promoted model, verify:

- `form-app/data.js` contains the new registry key
- Model switcher shows the model
- Default remains Stingray
- Body style choices are correct
- Trim choices are correct
- Unavailable variants are absent
- Standard equipment appears correctly
- Standard/included options are locked correctly
- Selectable options can be selected/deselected
- Exclusive groups behave like Grand Sport
- Price totals are correct
- Build download filename/export slug is correct
- Dealer submission payload includes the active model key
- No endpoint/payload/Turnstile drift

---

### 20. Full Gates Before Considering Runtime-Ready

**Run all scripts:**

```bash
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
.venv/bin/python scripts/generate_stingray_form.py
.venv/bin/python scripts/generate_model_form.py --model-key z06
.venv/bin/python scripts/generate_model_form.py --model-key zr1
.venv/bin/python scripts/generate_model_form.py --model-key zr1x
```

**Run all tests:**

```bash
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
node --test tests/workbook-schema-standardization.test.mjs
# new future-model draft/runtime tests
```

**Manual smoke:**

- Local static app
- Model switcher
- Body/trim selection
- Option behavior
- Standard/included summaries
- Price totals
- Build download
- Dealer modal validation
- Dealer payload model scoping

---

## Recommended Phase Breakdown

| Phase | Name | Scope |
|-------|------|-------|
| **7** | Review-map and normalize future options/OVS | Build review mapping layer. Resolve section conflicts/unresolved rows/missing RPO/duplicates. Populate `*_options` and `*_ovs`. No compatibility copying. No runtime promotion. |
| **8** | Grand Sport compatibility/exclusive rebase | Build option-ID resolver. Copy/rebase Grand Sport rules, grouped rules, exclusive groups, and members. Produce unresolved mapping audit. No runtime promotion. |
| **9** | LZ interiors and runtime metadata | Add Z06/ZR1/ZR1X interior scope and components. Add runtime steps/context/section/order-summary/default metadata. Add model assets and presentation metadata. |
| **10** | Generic model generator | Add `generate_model_form.py --model-key`. Generalize Grand Sport draft path. Generate draft artifacts for Z06/ZR1/ZR1X. |
| **11** | Accuracy review and cleanup | Compare draft artifacts against source sheets. Fix prices, standard equipment, labels, sections, and unresolved rule mappings. Add tests for each model. |
| **12** | Runtime promotion | Promote one model at a time through `model_registry_promotion`. Regenerate `form-app/data.js`. Run full gates and manual smoke. |

---

## Key Non-Goals Until the Relevant Phase Is Approved

- Do not directly promote archive preview rows into runtime
- Do not promote Z06/ZR1/ZR1X before draft artifacts pass review
- Do not copy price rules blindly from Grand Sport
- Do not solve missing sections in Python/JS
- Do not hardcode future-model compatibility in runtime
- Do not change dealer submission endpoint, payload shape, or Turnstile behavior
- Do not remove runtime fallbacks until all promoted models have generated metadata

---

## Most Important Practical Next Step

**Start Phase 7 with a review-map-driven source population pass.**

That is the bottleneck. Once option IDs and OVS statuses are accurate, the shared Grand Sport compatibility/exclusive behavior becomes a deterministic rebase problem instead of a discovery problem.
