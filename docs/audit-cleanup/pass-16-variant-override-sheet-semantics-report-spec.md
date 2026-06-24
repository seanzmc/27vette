# Pass 16 — Variant Override Sheet Semantics Report Spec

Status: Completed report-only implementation on 2026-06-24.
Date: 2026-06-23
Recommended reasoning level for implementation agent: high.

Source context:

- `AGENTS.md`
- `docs/metadata-runtime-redundancy-6-23.md`
- `docs/Audit-route-map.md`
- `27vette-workbook-guard` reference `segregated-workbook-behavior-retirement.md`
- `27vette-workbook-guard` reference `workbook-first-existing-pipelines.md`

## Goal

Produce a report-only classification of the active variant override sheet semantics before any workbook row migration, schema change, generator change, or test rewrite.

The report must answer, row by row and behavior class by behavior class:

1. What behavior each variant override row currently owns.
2. Whether the behavior already has a canonical workbook owner elsewhere.
3. Whether the behavior can be retired into existing workbook structures without generator/runtime changes.
4. Which behavior classes need a later implementation spec, and which rows must stay until a safe replacement owner is proven.

This pass is explicitly report-only. It should not change `stingray_master.xlsx`, generated artifacts, runtime JavaScript, Python generator behavior, tests, or browser behavior.

## Diagnosis

Change type for this spec: docs-only.

Change type for the future approved report pass: docs-only/report-only. Risk level: medium-high if later implemented incorrectly, because the variant override sheets currently affect emitted choice status, selectability, activity, display behavior, section placement, and step placement for active promoted models.

Root cause: variant override behavior is split across three workbook sheet contracts with different active semantics and partially overlapping behavior classes:

- `variant_option_overrides`: global/Stingray sheet. Its `active` column is not row activation; it is an emitted override value for the generated choice. `runtime_metadata.load_variant_option_overrides()` therefore reads this sheet with `optional_rows()` rather than `active_rows()`.
- `grandSport_variant_overrides`: Grand Sport model-scoped fallback sheet. Its `active` column is conventional row activation; the loader neutralizes `status` and `active` emitted override values and carries `selectable`, `display_behavior`, `section_id`, and `note`.
- `z06_variant_overrides`: Z06 model-scoped fallback sheet with the same model-scoped contract as Grand Sport.

The sheets are workbook-authored, but they are still architecture-risk surfaces until a report proves which rows are canonical owners and which rows are migration candidates.

## Current evidence inspected for this spec

Current branch/worktree:

- `git status --short --branch`: branch `schema-ingestion-normalization` with existing dirty Pass 15 files:
  - `docs/Audit-route-map.md`
  - `docs/audit-cleanup/pass-15-stingray-z51-suspension-runtime-rule-exception-retirement-spec.md`
  - `docs/metadata-runtime-redundancy-6-23.md`
  - `form-app/data.js`
  - `form-output/runtime/stingray-runtime-contract.json`
  - `form-output/stingray-form-data.json`
  - `stingray_master.xlsx`
  - `tests/stingray-form-regression.test.mjs`
  - `tests/stingray-generator-stability.test.mjs`

Standing docs:

- `docs/metadata-runtime-redundancy-6-23.md` currently classifies variant override behavior as medium-high risk and warns not to delete it cold.
- `docs/Audit-route-map.md` now names the variant override sheets as the next safe architecture-risk surface after Pass 15.
- `AGENTS.md` treats `variant_option_overrides`, `grandSport_variant_overrides`, and `z06_variant_overrides` as canonical-owner review surfaces, not automatic deletion targets.

Workbook row inventory from read-only `openpyxl` probes:

### `variant_option_overrides`

Headers:

```text
model_key, option_id, variant_id, status, selectable, active, display_behavior, notes
```

Rows: 7 total, all currently consumed for Stingray because this sheet's `active` field is an emitted override value, not row activation.

Observed behavior classes:

1. Stingray UQT paid option suppression:
   - Rows 2-5.
   - `option_id=opt_uqt_002` for `2lt_c07`, `3lt_c07`, `2lt_c67`, `3lt_c67`.
   - Overrides: `status=unavailable`, `selectable=False`, `active=False`.
   - Current meaning: the paid UQT option card is available only on 1LT; 2LT/3LT use standard-equipment UQT rows instead.
2. Stingray coupe BC7 default-selected marker:
   - Rows 6-8.
   - `option_id=opt_bc7_001` for `1lt_c07`, `2lt_c07`, `3lt_c07`.
   - Overrides: `active=True`, `display_behavior=default_selected`.
   - Current meaning: coupe BC7 generated choices are marked default-selected while convertible BC7 remains a normal available choice.

Adjacent workbook owners already present:

- `stingray_ovs` owns status for both UQT option IDs and BC7 by variant.
- `stingray_options.opt_uqt_001` is a nonselectable standard-equipment UQT row in `sec_2lte_001`; `stingray_options.opt_uqt_002` is the selectable paid UQT row in `sec_inte_001`.
- `default_selection_rules.default_bc7` already exists with `body_style_scope=coupe`.
- `exclusive_groups.grp_ls6_engine_covers` includes `opt_bc7_001`.

Current generated Stingray behavior:

- `opt_uqt_001` emits six nonselectable standard-equipment rows under `sec_2lte_001`; 2LT/3LT rows are `status=standard`, 1LT rows are `status=available`, all with `selectable=False`.
- `opt_uqt_002` emits selectable paid rows for 1LT and inactive/unavailable rows for 2LT/3LT due to `variant_option_overrides`.
- `opt_bc7_001` coupe choices are `status=standard`, `selectable=True`, `active=True`, `display_behavior=default_selected`; convertible choices are available without `default_selected`.

### `grandSport_variant_overrides`

Headers:

```text
option_id, variant_id, selectable, display_behavior, section_id, active, note
```

Rows: 13 total / 13 active. Model-scoped fallback sheet; `active` is row activation.

Observed behavior classes:

1. Grand Sport UQT included-equipment placement:
   - Rows 2-5.
   - `option_id=opt_uqt_001` for 2LT/3LT coupe/convertible variants.
   - Overrides: `selectable=False`, `display_behavior=display_only`, `section_id=sec_2lte_001` or `sec_3lte_001`.
   - Current meaning: UQT is selectable on 1LT but becomes display-only standard equipment in the proper trim-standard section for 2LT/3LT.
2. Grand Sport coupe BC7 default-selected marker:
   - Rows 6-8.
   - `option_id=opt_bc7_001` for coupe variants only.
   - Overrides: `display_behavior=default_selected`.
   - Current meaning: coupe BC7 is generated as default-selected; convertible BC7 remains a normal available choice.
3. Grand Sport NGA default-selected marker:
   - Rows 9-14.
   - `option_id=opt_nga_001` for all six active Grand Sport variants.
   - Overrides: `display_behavior=default_selected`.
   - Current meaning: standard black exhaust tips appear as default-selected generated choices.

Adjacent workbook owners already present:

- `grandSport_ovs` owns status for UQT, BC7, and NGA by variant.
- `grandSport_options.opt_uqt_001` is selectable in `sec_inte_001`; the override rows move 2LT/3LT UQT into `sec_2lte_001` / `sec_3lte_001` and make it display-only.
- `default_selection_rules.gs_default_bc7_coupe` already exists with `body_style_scope=coupe`.
- `default_selection_rules.gs_default_nga_unless_nwi` already exists.
- Grand Sport engine-cover and exhaust exclusive/default behavior has already been normalized in earlier passes for runtime selection behavior, but generated choice `display_behavior` is still carried by this sheet.

Current generated Grand Sport behavior:

- `opt_uqt_001` is selectable on 1LT in `sec_inte_001` and display-only standard equipment on 2LT/3LT in the trim-standard sections.
- `opt_bc7_001` coupe choices are standard/default-selected; convertible choices are available without default-selected.
- `opt_nga_001` all six choices are standard/default-selected.

### `z06_variant_overrides`

Headers:

```text
option_id, variant_id, selectable, display_behavior, section_id, active, note
```

Rows: 4 total / 4 active. Model-scoped fallback sheet; `active` is row activation.

Observed behavior class:

1. Z06 UQT included-equipment placement:
   - Rows 2-5.
   - `option_id=opt_uqt_001` for 2LZ/3LZ coupe/convertible variants.
   - Overrides: `selectable=False`, `display_behavior=display_only`, `section_id=sec_2lte_001` or `sec_3lte_001`.
   - Current meaning: UQT is selectable on 1LZ but becomes display-only standard equipment in the proper trim-standard section for 2LZ/3LZ.

Adjacent workbook owners already present:

- `z06_ovs` owns UQT status by variant.
- `z06_options.opt_uqt_001` is selectable in `sec_inte_001`; override rows move 2LZ/3LZ UQT into trim-standard sections and make it display-only.
- No Z06 default-selection rule is currently needed for this UQT behavior.

Current generated Z06 behavior:

- `opt_uqt_001` is selectable on 1LZ in `sec_inte_001` and display-only standard equipment on 2LZ/3LZ in trim-standard sections.

## Current code consumers to inventory in the report

The report implementation must inspect and cite exact consumer behavior for:

- `scripts/corvette_form_generator/runtime_metadata.py`
  - `load_variant_option_overrides()` lines 232-276.
  - Distinguishes global `variant_option_overrides` value-active semantics from model-scoped fallback row-active semantics.
- `scripts/corvette_form_generator/production.py`
  - Loads override rows around lines 194-200.
  - Applies `status`, `selectable`, `active`, and `display_behavior` around lines 331-347.
- `scripts/corvette_form_generator/inspection.py`
  - `keyed_variant_option_overrides()` lines 286-290.
  - `apply_variant_option_override()` lines 293-302.
  - Applies `selectable`, `display_behavior`, and `section_id`; status/active effects come from normal status/display behavior logic.
- `scripts/corvette_form_generator/schema_validation.py`
  - `ROLE_BOOLEAN_COLUMNS["variant_option_overrides_sheet"]` validates `active` and `selectable`, but currently does not distinguish value-active vs row-active semantics.
- `scripts/corvette_form_generator/editor_ops.py`
  - Maps `variant_option_overrides_sheet` to the editor's `variant_overrides` family.
- Generated runtime contracts under `form-output/runtime/` for Stingray, Grand Sport, and Z06.
- Browser runtime consumption of emitted choice fields, especially `display_behavior`, `selectable`, `active`, `status`, `section_id`, and `step_key`.

## Current test anchors to inventory in the report

The report implementation must inspect and cite exact assertions in at least:

- `tests/stingray-generator-stability.test.mjs`
  - Current UQT override/source guard at lines 394-417.
- `tests/stingray-form-regression.test.mjs`
  - BC7 default-selected/runtime default behavior and standard-equipment surfaces.
- `tests/grand-sport-draft-data.test.mjs`
  - UQT trim-scoped behavior at lines 239-270.
  - BC7 and NGA default-selected behavior at lines 538-550.
- `tests/grand-sport-contract-preview.test.mjs`
  - Runtime-contract expectations for UQT/BC7/NGA if present.
- `tests/z06-form-data-draft.test.mjs`
  - Z06 UQT and default-selected rows where relevant.
- `tests/z06-contract-preview.test.mjs`
  - Runtime-contract expectations for UQT if present.
- `tests/workbook-schema-standardization.test.mjs` and `tests/workbook-visual-copy-standardization.test.mjs`
  - Header/schema assumptions around active model source sheets and boolean fields.

## Report-only deliverables after approval

Create:

- `docs/audit-cleanup/pass-16-variant-override-sheet-semantics-report.md`

Update after the report is complete:

- `docs/audit-cleanup/pass-16-variant-override-sheet-semantics-report-spec.md`

Optional docs status refresh, only if the report changes the recommended next pass:

- `docs/metadata-runtime-redundancy-6-23.md`
- `docs/Audit-route-map.md`

## Required report contents

The report must include these sections:

1. Executive summary.
2. Source-of-truth table for each override sheet:
   - sheet name
   - row count
   - headers
   - row activation semantics
   - emitted override fields
   - generator path(s)
   - generated contract fields affected
3. Row-level inventory table for all 24 current rows:
   - sheet
   - workbook row number
   - model key
   - option ID / RPO / label
   - variant ID / trim / body
   - override fields
   - current generated choice result
   - current tests that pin it
   - likely canonical owner
   - classification
4. Behavior-class classification:
   - UQT trim-scoped included-equipment placement/selectability.
   - BC7 coupe default-selected display metadata.
   - NGA Grand Sport all-variant default-selected display metadata.
5. Canonical-owner candidates and blockers:
   - `*_ovs` status rows.
   - source option rows.
   - `default_selection_rules` plus exclusive groups.
   - section/standard-equipment metadata.
   - generator derivation from defaults/status where currently missing.
6. Proposed follow-up pass sequence, split by behavior class rather than by sheet deletion.
7. Non-goals and explicit protections.
8. Validation/gate recommendations for each future implementation class.

## Classification vocabulary for the report

Use only these classifications unless the report justifies adding another category:

- `keep-canonical-currently`: row is the clearest current owner and should not be migrated without a new design.
- `candidate-existing-owner`: behavior appears expressible by existing workbook owner(s), but implementation still needs parity proof.
- `candidate-generator-derivation`: source facts already exist, but generator logic would need to derive emitted fields from canonical rows.
- `candidate-source-row-remodel`: current source/OVS rows cannot express the behavior without remodeling option rows or standard-equipment placement metadata.
- `needs-product-decision`: product semantics are unclear; do not migrate until the product rule is confirmed.

Preliminary expected classification, to be verified in the report:

- UQT 2LT/3LT included-equipment behavior: likely `candidate-source-row-remodel` or `candidate-generator-derivation`, because status exists in OVS but selectable/display-only/section placement do not.
- BC7 default-selected rows: likely `candidate-generator-derivation`, because default-selection rules and exclusive groups already exist, but generated `display_behavior=default_selected` still comes from variant override rows.
- Grand Sport NGA default-selected rows: likely `candidate-generator-derivation`, because `gs_default_nga_unless_nwi` and exhaust exclusive-group metadata already exist, but generated `display_behavior=default_selected` still comes from variant override rows.

Do not treat these preliminary labels as implementation approval.

## Explicit non-scope for the report pass

Do not change:

- `stingray_master.xlsx`.
- Any workbook sheet rows, headers, table refs, or schema.
- `scripts/corvette_form_generator/*.py`.
- `form-app/app.js`, CSS, or HTML.
- `form-output/*` or `form-app/data.js`.
- Tests.
- Dealer submission endpoint, payload, or Turnstile behavior.
- Z06 brake/default replacement behavior.
- `runtime_action`, `body_style_scope`, or direct-rule runtime matching.

Do not run workbook-writing scripts. Do not remove variant override rows. Do not propose a single sheet-wide deletion pass unless the report proves every row has the same replacement owner and risk profile.

## Constraints

- Follow `AGENTS.md` spec-first rules.
- Use current workbook and generated artifacts as evidence; do not rely on archived context as source of truth.
- Treat the workbook as source of truth, but do not assume a small workbook override sheet is canonical just because it is workbook-owned.
- Prefer existing workbook owners over new sheets/columns/modules.
- No new dependencies.
- No broad refactor.
- No runtime behavior change.
- No visual change.
- No dealer-submission change.

## Validation plan for the report pass

Preflight/read-only checks:

```sh
git status --short --branch
.venv/bin/python - <<'PY'
from pathlib import Path
raise SystemExit(1 if Path('~$stingray_master.xlsx').exists() else 0)
PY
```

Read-only workbook/report probes:

```sh
.venv/bin/python - <<'PY'
# openpyxl read_only=True inventory of:
# variant_option_overrides
# grandSport_variant_overrides
# z06_variant_overrides
# model_workbook_sources variant_option_overrides_sheet rows
# related *_options, *_ovs, default_selection_rules, exclusive groups/members
PY
```

Generated-contract probes without writing artifacts:

```sh
node - <<'NODE'
// Read form-output/runtime/stingray-runtime-contract.json
// Read form-output/runtime/grand-sport-runtime-contract.json
// Read form-output/runtime/z06-runtime-contract.json
// Emit focused choice summaries for UQT, BC7, and NGA by variant.
NODE
```

Code/test consumer inventory:

```sh
rg -n "load_variant_option_overrides|variant_option_overrides_sheet|apply_variant_option_override|keyed_variant_option_overrides" scripts tests
rg -n "opt_uqt|opt_bc7|opt_nga|default_selected|display_only|variant_option_overrides|grandSport_variant_overrides|z06_variant_overrides" tests
```

Final docs-only checks:

```sh
git diff --check
git diff -- docs/audit-cleanup/pass-16-variant-override-sheet-semantics-report-spec.md docs/audit-cleanup/pass-16-variant-override-sheet-semantics-report.md docs/metadata-runtime-redundancy-6-23.md docs/Audit-route-map.md
```

Do not run model generators for the report pass unless the report explicitly needs fresh temporary outputs. If fresh outputs are needed, write them to `/tmp` where possible and do not check in generated artifacts.

## Risks and mitigations

- Risk: treating `active=False` in `variant_option_overrides` as row deactivation would miss the Stingray UQT suppression rows.
  - Mitigation: report must explain global sheet value-active semantics and cite `runtime_metadata.load_variant_option_overrides()`.
- Risk: deleting UQT override rows because OVS already has `status=standard` would lose selectable/display-only/section placement behavior.
  - Mitigation: classify UQT separately from default-selected rows and include generated choice before/after requirements in any future implementation spec.
- Risk: deleting BC7/NGA override rows because default-selection rules exist would preserve runtime selected state but lose generated `display_behavior=default_selected` metadata unless the generator derives it.
  - Mitigation: classify default-selected rows as generator-derivation candidates, not simple workbook-row deletions.
- Risk: combining Stingray, Grand Sport, and Z06 migrations hides different sheet semantics.
  - Mitigation: report must keep global and model-scoped sheet contracts separate.
- Risk: report recommendations go stale if Pass 15 dirty files are not recognized.
  - Mitigation: report must record the starting dirty worktree and avoid touching Pass 15 artifacts.

## Non-goals

- No workbook edits.
- No generated artifact refresh.
- No runtime JavaScript or generator implementation.
- No test edits.
- No row deletion/deactivation.
- No schema/header normalization.
- No new canonical sheet or column proposal unless the report proves existing workbook owners cannot represent a behavior class.

## Completion evidence

Pass 16 was completed as a report-only classification on 2026-06-24.

Created:

- `docs/audit-cleanup/pass-16-variant-override-sheet-semantics-report.md`

Updated:

- `docs/audit-cleanup/pass-16-variant-override-sheet-semantics-report-spec.md`
- `docs/metadata-runtime-redundancy-6-23.md`
- `docs/Audit-route-map.md`

Read-only probes performed:

- `git status --short --branch`: branch `schema-ingestion-normalization` with no dirty files at Pass 16 start.
- Workbook lock probe: no `~$stingray_master.xlsx` lock file.
- `openpyxl.load_workbook(..., read_only=True, data_only=True)` workbook inventory for `variant_option_overrides`, `grandSport_variant_overrides`, `z06_variant_overrides`, adjacent source sheets, OVS rows, default-selection rules, exclusive groups, and section-presentation metadata.
- Checked-in generated contract JSON inspection for `form-output/runtime/stingray-runtime-contract.json`, `form-output/runtime/grand-sport-runtime-contract.json`, and `form-output/runtime/z06-runtime-contract.json`.
- Code/test consumer inventory through `read_file` / `search_files` for the loader, production/inspection application paths, schema/editor mappings, and UQT/BC7/NGA test anchors.

Report conclusions:

- `variant_option_overrides.active` remains emitted-value metadata, not row activation.
- UQT trim-scoped included-equipment placement/selectability is a source-row remodel or constrained generator-derivation candidate, not a simple OVS-owned deletion candidate.
- Stingray/Grand Sport BC7 and Grand Sport NGA default-selected display metadata are better follow-up candidates for generator derivation from existing `default_selection_rules` plus exclusive groups.
- No sheet-wide variant override deletion pass is recommended.

Gates run after docs edits:

- `git diff --check`: pass.
- Targeted stale active-prompt scan against this spec: pass after final wording cleanup; no active approval prompt remains.
- Targeted docs diff/status review: pass; changed files are docs-only.

Manual verification still pending:

- None for runtime behavior because this was report-only and did not regenerate artifacts or change runtime/source data.
- Future implementation passes still need generated-data parity and local browser/runtime proof before retiring any override rows.

Recommended next pass after Pass 16:

- Historical context: Pass 16 recommended a narrow default-selected display metadata derivation pass for Stingray BC7, Grand Sport BC7, and Grand Sport NGA, while keeping UQT trim-standard placement separate. That follow-up became Pass 17 and was implemented on 2026-06-24. The remaining follow-up on this track is a separate UQT source-ownership spec before any remaining variant override row migration.

## Historical approval prompt

Original pre-approval wording: Pass 16 was requested as a report-only semantics classification to create `docs/audit-cleanup/pass-16-variant-override-sheet-semantics-report.md`, update this spec with completion evidence, optionally refresh standing docs if the report changed next-step guidance, and perform only read-only workbook/generated/code/test probes plus docs-only validation.
