# Grand Sport Phase 4 Normalization Spec

> Spec only. Do not implement this pass. Phase 4 prepares a read-only Grand Sport contract preview outside live app outputs.

## Goal

Normalize Grand Sport option display and form placement enough to preview the existing Stingray contract shape, while preserving raw Grand Sport rule/detail evidence for later rule extraction. The live Stingray app data, runtime, UI, exports, and workbook variant active states must remain unchanged.

## Diagnosis

Phase 3 proved the `grandSport` source sheet is structurally usable for a read-only preview:

- `269` option rows.
- `223` unique RPOs.
- `1,614` variant status cells.
- `1,418` candidate available/standard choice rows.
- `545` candidate standard equipment cells.
- `109` candidate standard option rows.
- `0` missing statuses.
- `0` unknown statuses.
- `0` missing resolved sections.
- `PCQ`, `PDY`, and `PEF` are explicitly mapped through `GRAND_SPORT_MODEL.blank_section_overrides`.

The blocking normalization issue is not missing data. It is contract fit:

- `55` rows have section/category mismatches between the raw Grand Sport row `Category` and the workbook `section_master.category_id`.
- Several mismatches are expected because LPO, wheel accessory, spoiler, included, caliper, OnStar, and special edition sections are reused across category boundaries.
- Grand Sport variants are present in `variant_master` but inactive, which is correct for preserving the current Stingray-only live generator path.
- `123` rows contain rule/detail hot spot language that must remain raw and auditable, but should not become final rules in Phase 4.

Risk level: medium. The work is read-only for app outputs, but it establishes the mapping contract that later Grand Sport generation will depend on.

Behavior class: generator/contract preview only. No runtime, UI, export, styling, or live Stingray behavior changes.

## Files To Change In Phase 4

- Modify: `scripts/corvette_form_generator/model_config.py`
  - Add config fields for Grand Sport normalization without putting model-specific logic into shared helpers.
- Modify: `scripts/corvette_form_generator/model_configs.py`
  - Add Grand Sport-specific section/category resolution config, section labels, step overrides, and deterministic text cleanup options.
- Modify: `scripts/corvette_form_generator/inspection.py`
  - Add preview-building functions that reuse Phase 3 inspection data but emit a contract-shaped read-only preview.
- Modify: `scripts/generate_grand_sport_form.py`
  - Keep it read-only; add preview artifact generation beside the existing inspection artifacts.
- Create: `tests/grand-sport-contract-preview.test.mjs`
  - Validate preview shape, all six variants, resolved section/category/step placement, raw detail preservation, text cleanup notes, and no live app writes.
- Create artifacts at runtime only:
  - `form-output/inspection/grand-sport-contract-preview.json`
  - `form-output/inspection/grand-sport-contract-preview.md`

Files not to change:

- `form-app/app.js`
- `form-app/index.html`
- `form-app/styles.css`
- `form-app/data.js`, except timestamp churn caused only by the required Stingray validation generator
- `form-output/stingray-form-data.json`, except timestamp churn caused only by the required Stingray validation generator
- `stingray_master.xlsx`, except normal workbook timestamp/content churn from the required Stingray validation generator

## Proposed Config Additions

Extend `ModelConfig` with explicit, optional fields:

- `section_category_overrides: Mapping[str, str]`
  - Resolves customer-facing category by section ID when the raw row category conflicts with `section_master`.
  - Used for preview output only. Preserve raw row category separately.
- `option_category_overrides: Mapping[str, str]`
  - Narrow escape hatch for individual option rows that should not follow the section-level category resolution.
- `section_label_overrides: Mapping[str, str]`
  - Customer-facing labels for Grand Sport-specific sections.
- `preview_artifact_prefix: str`
  - For `grand-sport-contract-preview`.
- `text_cleanup: Mapping[str, Any]`
  - Deterministic cleanup rules enabled for customer-facing `label` and `description` only.
- `special_rule_review_rpos: tuple[str, ...]`
  - Initial value: `("EL9", "Z25", "FEY", "Z15")`.

Keep existing `blank_section_overrides` as-is:

- `opt_pcq_001 -> sec_lpoe_001`
- `opt_pdy_001 -> sec_lpoi_001`
- `opt_pef_001 -> sec_lpoi_001`

Do not infer these from option names or descriptions.

## Section/Category Normalization Plan

The preview should preserve three fields for audit and expose resolved fields for contract use:

- `source_category_id`: raw `grandSport.Category`
- `source_section_id`: raw `grandSport.Section`
- `resolved_section_id`: raw section or explicit blank-section override
- `resolved_category_id`: contract category after config-driven normalization
- `section_category_id`: workbook `section_master.category_id`
- `category_resolution_source`: `source`, `section_master`, `section_override`, or `option_override`

Resolution order:

1. Resolve section:
   - Use raw `Section` when present.
   - Use `GRAND_SPORT_MODEL.blank_section_overrides` for `PCQ`, `PDY`, and `PEF`.
   - If still blank, emit an unresolved validation warning and exclude from preview choices until resolved.
2. Resolve category:
   - Use `option_category_overrides[option_id]` when present.
   - Else use `section_category_overrides[resolved_section_id]` when present.
   - Else use `source_category_id` when it is known.
   - Else use `section_master.category_id`.
   - If the final category is unknown, emit an unresolved validation warning.
3. Resolve step:
   - Use existing `step_for_section()` with `GRAND_SPORT_MODEL.section_step_overrides`.
   - Do not add a new top-level step unless a section cannot fit the existing Stingray flow.

Known mismatch groups to address in config:

| Mismatch Group | Count | Phase 4 Resolution |
| --- | ---: | --- |
| `sec_lpoe_001`, raw `cat_exte_001`, section `cat_mech_001` | 18 | Resolve as exterior/accessory category for preview; step stays `aero_exhaust_stripes_accessories`. |
| `sec_whee_001`, raw `cat_exte_001`, section `cat_mech_001` | 7 | Resolve as exterior/wheel accessory category; step stays `wheels`. |
| `sec_spoi_001`, raw `cat_exte_001`, section `cat_mech_001` | 2 | Resolve as exterior/aero category; step stays `aero_exhaust_stripes_accessories`. |
| `sec_perf_001`, raw `cat_exte_001`, section `cat_mech_001` | 5 | Keep performance section placement; preserve raw exterior source category for aero package review. |
| `sec_cali_001`, raw `cat_mech_001`, section `cat_exte_001` | 7 | Resolve as exterior/wheel category; step stays `wheels`. |
| `sec_incl_001`, raw `cat_exte_001`/`cat_mech_001`/`cat_inte_001`, section `cat_stan_001` | 7 | Resolve as standard equipment; preserve raw category for audit. |
| `sec_cust_001`, raw `cat_inte_001`/`cat_exte_001`, section `cat_mech_001` | 3 | Resolve by option-level config if needed; likely delivery/customer-info related for preview. |
| `sec_onst_001`, raw `cat_stan_001`, section `cat_inte_001` | 5 | Resolve as interior trim or standard equipment by option-level review; do not silently collapse. |
| `sec_spec_001`, raw `cat_exte_001`, section `cat_mech_001` | 1 | Map Special Edition into `packages_performance`; preserve label `Special Edition`. |

Grand Sport-specific sections should fit existing steps:

- `sec_gsce_001` GS Center Stripes -> `exterior_appearance`
- `sec_gsha_001` GS Hash Marks -> `exterior_appearance`
- `sec_spec_001` Special Edition -> `packages_performance`
- `sec_colo_001` Color Combination Override -> `interior_trim`

Do not add new top-level steps in Phase 4.

## Text Cleanup Plan

Add a deterministic cleanup pass for preview display fields only:

- Clean `label` from raw `Option Name`.
- Clean `description` from raw `Description`.
- Preserve exact raw fields:
  - `source_option_name`
  - `source_description`
  - `source_detail_raw`

Cleanup rules:

- Trim leading/trailing whitespace.
- Collapse repeated internal whitespace.
- Collapse repeated punctuation such as `!!`, `..`, and duplicate commas.
- Normalize `NEW!  Ground effects` to `New Ground Effects`.
- Normalize leading `NEW!` to `New` when it is marketing text, not an RPO.
- Normalize obvious all-lowercase or inconsistent capitalization in natural-language labels.
- Preserve RPO codes exactly.
- Preserve package names and brand terms such as `Grand Sport`, `Carbon Flash`, `Jake logo`, `Michelin Pilot Sport Cup 2 R`, and `LPO`.
- Remove duplicated repeated phrases only when the exact phrase repeats adjacently.
- Do not rewrite compatibility or rule meaning.
- If cleanup is ambiguous, keep the original display text and emit a `text_cleanup_ambiguous` validation note.

Preview rows should include:

- `label`
- `description`
- `source_option_name`
- `source_description`
- `source_detail_raw`
- `text_cleanup_notes`

## Preview Artifact Shape

Create `form-output/inspection/grand-sport-contract-preview.json`:

```json
{
  "dataset": {
    "name": "2027 Corvette Grand Sport contract preview",
    "model": "Grand Sport",
    "model_year": "2027",
    "source_workbook": "stingray_master.xlsx",
    "source_sheet": "grandSport",
    "generated_at": "ISO-8601 timestamp",
    "status": "read_only_preview"
  },
  "variants": [],
  "steps": [],
  "sections": [],
  "contextChoices": [],
  "choices": [],
  "candidateStandardEquipment": [],
  "ruleDetailHotSpots": {
    "counts": {},
    "rows": []
  },
  "normalization": {
    "blankSectionOverrides": [],
    "sectionCategoryResolutions": [],
    "textCleanupSummary": {},
    "unresolvedIssues": []
  },
  "validation": []
}
```

Contract preview requirements:

- `variants`: include all six configured Grand Sport variants from model config, even though workbook `active` remains `False`.
- `contextChoices`: mirror Stingray body style and trim context shape.
- `steps`: mirror existing Stingray step order.
- `sections`: include resolved Grand Sport section/category/step placement.
- `choices`: include candidate available/standard choices with raw detail preserved.
- `candidateStandardEquipment`: include standard cells separately from selectable choices for inspection.
- `ruleDetailHotSpots`: preserve Phase 3 buckets and add `special_package_review` when a row mentions or is one of `EL9`, `Z25`, `FEY`, `Z15`.
- `validation`: include warnings for unresolved category, unresolved step, ambiguous text cleanup, and remaining section/category mismatches.

Create `form-output/inspection/grand-sport-contract-preview.md`:

- Summary counts.
- Variant inclusion table.
- Section/category resolution summary.
- PCQ/PDY/PEF explicit override confirmation.
- Text cleanup summary and ambiguous cleanup notes.
- Rule/detail hot spot bucket counts.
- Unresolved normalization issues.
- Confirmation that no live app output was written by Grand Sport preview generation.

## Testing Plan

Create `tests/grand-sport-contract-preview.test.mjs` with focused assertions:

- Preview artifacts exist after `scripts/generate_grand_sport_form.py`.
- `dataset.status === "read_only_preview"`.
- `variants.map(v => v.variant_id)` equals:
  - `1lt_e07`
  - `2lt_e07`
  - `3lt_e07`
  - `1lt_e67`
  - `2lt_e67`
  - `3lt_e67`
- `choices.length === 1418` unless Phase 4 explicitly documents a different preview rule.
- `candidateStandardEquipment.length === 545`.
- Every choice has `resolved_section_id`, `resolved_category_id`, and `step_key`.
- `normalization.unresolvedIssues` contains no unresolved section/category mismatches, or the test asserts the exact remaining unresolved list.
- `PCQ`, `PDY`, and `PEF` show `handled_by_explicit_config === true`.
- Every choice preserves `source_detail_raw` as a string.
- At least one cleaned display example is checked, such as `NEW!  Ground effects` -> `New Ground Effects`.
- The Grand Sport script does not mutate `form-app/data.js`.

## Validation Plan

Run exactly:

```bash
.venv/bin/python scripts/generate_stingray_form.py
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
.venv/bin/python scripts/generate_grand_sport_form.py
node --test tests/grand-sport-contract-preview.test.mjs
```

Additional verification:

```bash
git diff -- form-app/data.js form-output/stingray-form-data.json
```

Expected:

- Only `generated_at` changes in live Stingray generated outputs.
- `form-app/data.js` is not written by the Grand Sport script.
- `grand-sport-inspection.json` and `grand-sport-inspection.md` still generate.
- `grand-sport-contract-preview.json` and `grand-sport-contract-preview.md` generate under `form-output/inspection/`.

## Risks

- Section/category mismatches may reflect workbook modeling debt rather than simple display categorization. Mitigation: preserve source category and section category separately.
- Text cleanup can accidentally remove meaning. Mitigation: clean only display fields, keep raw fields exact, and emit validation notes for ambiguous cleanup.
- Preview counts may differ from final generator counts once rules and defaults are implemented. Mitigation: label the artifact `read_only_preview`.
- Grand Sport inactive variants could tempt a workbook edit. Mitigation: use model config inclusion only; do not alter `variant_master.active`.
- Rule hot spot language can look actionable but is out of scope. Mitigation: bucket and preserve, do not generate final rules.

## Non-Goals

- No runtime changes.
- No UI changes.
- No export schema changes.
- No Formidable wiring.
- No final Grand Sport data generation.
- No activation of Grand Sport in the live app.
- No implementation of `Z15`, `Z25`, `EL9`, or `FEY` rules.
- No Stingray behavior changes.

## Approval Boundary

Phase 4 implementation may proceed only after approval of this spec. Approval authorizes read-only preview generation and tests under the files listed above. It does not authorize live app integration, Grand Sport runtime switching, final rule implementation, Formidable wiring, or workbook activation of Grand Sport variants.

