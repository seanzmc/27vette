# Z06 Runtime Preview Contract Pass Spec

## Diagnosis

Change type: mixed generator/test/artifact pass, intentionally non-live and non-promotional. The pass should create a Z06 draft/runtime-preview generation path that exercises the current workbook-owned Z06 source rows without adding Z06 to `form-app/data.js` or enabling customer-facing runtime switching.

Risk level: medium-high. Z06 source data is now closer to runtime-ready, but the model remains inactive in `model_master` and there is no Z06 `ModelConfig` or dedicated draft generator equivalent to the Grand Sport inspection/draft flow. The risk is that promoting directly to the app registry would hide contract defects until the live runtime is touched. This pass should expose those defects in draft artifacts and tests first.

Evidence inspected:

- Branch/status:
  - branch: `z06-zr1-migration`
  - status contains only untracked `.DS_Store` files and `backups/`; do not stage or touch those.
- Current model activation state in `stingray_master.xlsx` / `model_master`:
  - `stingray`: active `True`, default model `True`, registry key `stingray`.
  - `grand_sport`: active `True`, registry key `grandSport`.
  - `z06`: active `False`, registry key `z06`, expected variants `6`, dataset name currently says future metadata scaffold.
  - `zr1`: active `False`, expected variants `4`.
  - `zr1x`: active `False`, expected variants `4`.
- Current Z06 source health sampled from `z06_options` after the prior cleanup:
  - 249 source rows, 249 active rows.
  - default-selected rows: `EFR`, `T0E`, `J56`, `719`.
  - default-selected non-selectable rows: 0.
  - active rows missing `display_order`: 0.
  - standard-equipment section rows with prices: 0.
- Current ZR1/ZR1X source health sampled for comparison:
  - `zr1_options`: 213 active rows, default-selected non-selectable rows 0, active missing display_order 0, standard-section priced rows 0.
  - `zr1x_options`: 214 active rows, default-selected non-selectable rows 0, active missing display_order 0, standard-section priced rows 0.
- Existing generator/config files inspected:
  - `scripts/corvette_form_generator/model_configs.py`
    - currently defines `STINGRAY_MODEL` and `GRAND_SPORT_MODEL` only.
    - shared `STEP_ORDER`, `STEP_LABELS`, `CONTEXT_SECTIONS`, `STANDARD_SECTIONS`, and `SECTION_STEP_OVERRIDES` already include the generic step/section machinery needed by draft generation.
  - `scripts/generate_grand_sport_form.py`
    - existing non-live pattern: loads model config overrides, writes inspection, contract preview, and draft artifacts, and does not mutate `form-app/data.js`.
  - `scripts/corvette_form_generator/inspection.py`
    - contains `build_contract_preview()` and `build_form_data_draft()` that can be reused if a Z06 `ModelConfig` is available.
  - `scripts/build_future_z_rule_audit.py`
    - read-only audit already supports `--model-key z06` and reports Z rule/default/exclusive readiness.
- Existing test patterns inspected:
  - `tests/grand-sport-contract-preview.test.mjs`
    - proves preview artifacts exist and generation does not mutate `form-app/data.js`.
  - `tests/grand-sport-draft-data.test.mjs`
    - proves draft contract shape, model variants, steps, choices, standard equipment, rules, price rules, and workbook-specific behavior.
  - `tests/grand-sport-rule-audit.test.mjs`
    - reconciles workbook-authored rules with draft artifacts.

Root cause / why this pass is needed:

Z06 has workbook-owned source sheets and rule/pricing cleanup, but it lacks a non-live generated-data contract. The only live app-data registry currently covers Stingray and Grand Sport. The next safe step is not activation; it is a draft contract path that lets us see whether Z06 source rows, sections, standard equipment, rule mappings, price rules, exclusive groups, interiors, and validation rows generate into the same top-level data shape the runtime expects.

## Exact files / sheets / artifacts to change

Primary code changes:

- Modify `scripts/corvette_form_generator/model_configs.py`
  - Add `Z06_MODEL = ModelConfig(...)` using the shared model-generation machinery.
  - Source sheets expected for Z06:
    - `source_option_sheet="z06_options"`
    - `status_sheet="z06_ovs"`
    - `rule_mapping_sheet="z06_rule_mapping"`
    - `price_rules_sheet="z06_price_rules"`
    - `rule_groups_sheet="z06_rule_groups"`
    - `rule_group_members_sheet="z06_rule_group_members"`
    - `exclusive_groups_sheet="z06_exclusive_groups"`
    - `exclusive_group_members_sheet="z06_exclusive_members"`
  - Variant IDs expected from `future_model_ingest.FUTURE_MODEL_SPECS["z06"]` / workbook source:
    - `1lz_h07`
    - `2lz_h07`
    - `3lz_h07`
    - `1lz_h67`
    - `2lz_h67`
    - `3lz_h67`
  - Use `preview_artifact_prefix="z06-contract-preview"`.
  - Use `draft_artifact_prefix="z06-form-data-draft"`.
  - Keep notes explicit that this is draft-only and not runtime active.

- Create `scripts/generate_z06_form.py`
  - Mirror the Grand Sport read-only generation pattern.
  - Load workbook model config overrides through `load_model_config_overrides(wb, Z06_MODEL)`.
  - Write these artifacts under `form-output/inspection/`:
    - `z06-inspection.json`
    - `z06-inspection.md`
    - `z06-contract-preview.json`
    - `z06-contract-preview.md`
    - `z06-form-data-draft.json`
    - `z06-form-data-draft.md`
  - Include existing Z audit artifact paths if generated by `scripts/build_future_z_rule_audit.py --model-key z06` or explicitly generate them as part of the script only if that can be done without side effects.
  - Print a JSON summary like `generate_grand_sport_form.py`.
  - Must not mutate `form-app/data.js`.
  - Must not write `stingray_master.xlsx`.

- Create `tests/z06-contract-preview.test.mjs`
  - Use the Grand Sport preview test shape, but adapt expected model/variant IDs/counts to Z06.
  - Assert `form-app/data.js` is unchanged by `scripts/generate_z06_form.py`.
  - Assert preview artifacts exist.
  - Assert preview dataset status is `read_only_preview`.
  - Assert dataset model is `Z06`.
  - Assert variants are exactly:
    - `1lz_h07`, `2lz_h07`, `3lz_h07`, `1lz_h67`, `2lz_h67`, `3lz_h67`.
  - Assert preview choices resolve section and step fields with no unresolved normalization issues unless the first implementation run proves a genuine source-data issue that should be fixed in the workbook before relaxing the test.

- Create `tests/z06-form-data-draft.test.mjs`
  - Use the Grand Sport draft test shape, but keep Z06 assertions focused and contract-level in this pass.
  - Assert top-level draft keys match the live generated-data contract:
    - `dataset`, `variants`, `steps`, `sections`, `contextChoices`, `choices`, `standardEquipment`, `ruleGroups`, `exclusiveGroups`, `rules`, `priceRules`, `interiors`, `colorOverrides`, `defaultSelectionRules`, `validation`.
  - Assert `draft.dataset.status === "draft_not_runtime_active"`.
  - Assert `draft.dataset.model === "Z06"`.
  - Assert the six Z06 variants above.
  - Assert `form-app/data.js` is unchanged by draft generation.
  - Assert prior user-approved Z06 business decisions are visible in draft output:
    - `PDB`, `PDD`, `PDF` choices are in `sec_z06_pkg_001`.
    - `ROY`, `ROZ`, `STZ` choices are in `sec_z06_cf_whee_001`.
    - `Z07` remains in `sec_perf_z52_001`.
    - default-selected choices `EFR`, `T0E`, `J56`, and `719` remain selectable in emitted choices.
    - price rules include the Z06 package/wheel override rows and `Z07 -> J57` zero-price override.
    - standard-equipment sections do not emit priced selectable choices.

Optional code change if the first run exposes a generic gap:

- Modify generic inspection/generation helpers in `scripts/corvette_form_generator/inspection.py` only if Z06 reveals a model-general defect in how draft data consumes model-scoped sheets. Do not add hardcoded Z06/RPO logic there.

Generated artifacts expected from this pass:

- `form-output/inspection/z06-inspection.json`
- `form-output/inspection/z06-inspection.md`
- `form-output/inspection/z06-contract-preview.json`
- `form-output/inspection/z06-contract-preview.md`
- `form-output/inspection/z06-form-data-draft.json`
- `form-output/inspection/z06-form-data-draft.md`

Inputs to inspect but not modify unless a defect is proven and separately approved:

- `stingray_master.xlsx`
  - `model_master`
  - `z06_options`
  - `z06_ovs`
  - `z06_rule_mapping`
  - `z06_price_rules`
  - `z06_rule_groups`
  - `z06_rule_group_members`
  - `z06_exclusive_groups`
  - `z06_exclusive_members`
  - `section_master`
  - `variant_master`
- `scripts/corvette_form_generator/future_model_ingest.py`
- `scripts/build_future_z_rule_audit.py`
- Existing Grand Sport generator/tests as pattern references.

Files/surfaces explicitly not to change in this pass:

- Do not set `model_master.active=True` for `z06`.
- Do not add Z06 to `form-app/data.js` / `window.CORVETTE_FORM_DATA`.
- Do not alter `form-app/app.js`, `form-app/index.html`, or `form-app/styles.css` unless the approved implementation discovers a generic draft-contract test helper need that cannot be solved elsewhere.
- Do not change dealer submission endpoint, payload shape, or Turnstile behavior.
- Do not write `stingray_master.xlsx` in this pass.
- Do not hand-edit generated `form_*` workbook sheets.

## Constraints repeated back

- Visual preservation: no live UI or styling changes.
- No live runtime behavior change: Z06 remains inactive and unavailable in the customer-facing registry.
- No dealer-submission change: endpoint, payload shape, modal validation, and Turnstile behavior are untouched.
- No new dependencies.
- No refactor: copy the proven Grand Sport draft/preview pattern with the smallest Z06-specific configuration needed.
- Workbook source-of-truth: if generated Z06 data is wrong because source rows are wrong, fix should be proposed against the workbook source sheets in a later approved pass, not hidden in JavaScript or Python exceptions.
- Generated artifact ownership: `form-output/inspection/z06-*` artifacts are outputs of the new script; `form-app/data.js` remains untouched.
- Existing untracked `.DS_Store` files and `backups/` are unrelated and must not be staged or cleaned as part of this pass.

## Proposed bite-sized implementation plan

### Task 1: Add a Z06 model config

Objective: Give the generic preview/draft generator a Z06 config without activating Z06.

Files:
- Modify `scripts/corvette_form_generator/model_configs.py`.

Steps:
1. Add `Z06_MODEL = ModelConfig(...)` below `GRAND_SPORT_MODEL` or near the existing configs.
2. Reuse the shared constants already used by Stingray and Grand Sport.
3. Point the model-scoped sheets at the Z06 workbook sheets listed above.
4. Set preview/draft artifact prefixes to `z06-contract-preview` and `z06-form-data-draft`.
5. Run:
   - `.venv/bin/python -m py_compile scripts/corvette_form_generator/model_configs.py`

Expected result:
- Python compile passes.
- No workbook or generated artifact is changed by this task.

### Task 2: Add the read-only Z06 generator script

Objective: Generate Z06 inspection, preview, and draft artifacts without app-data mutation.

Files:
- Create `scripts/generate_z06_form.py`.

Steps:
1. Copy the structure of `scripts/generate_grand_sport_form.py`.
2. Import `Z06_MODEL` instead of `GRAND_SPORT_MODEL`.
3. Use `load_model_config_overrides(wb, Z06_MODEL)`.
4. Write artifacts using the configured prefixes.
5. Print JSON summary with model key, model label, source sheet, variant IDs, counts, warnings, preview counts, draft counts, artifact paths, and notes.
6. Run:
   - `.venv/bin/python -m py_compile scripts/generate_z06_form.py`
   - `.venv/bin/python scripts/generate_z06_form.py`

Expected result:
- Script exits 0.
- New `form-output/inspection/z06-*` artifacts are created.
- `form-app/data.js` does not change.

### Task 3: Add a Z06 contract-preview test

Objective: Lock the non-live preview contract and prevent accidental app-data mutation.

Files:
- Create `tests/z06-contract-preview.test.mjs`.

Steps:
1. Start from `tests/grand-sport-contract-preview.test.mjs`.
2. Change script path and artifact paths to Z06.
3. Assert no `form-app/data.js` mutation.
4. Assert dataset status/model and exact variant IDs.
5. Assert preview choices resolve section/step/source text fields.
6. Run:
   - `node --test tests/z06-contract-preview.test.mjs`

Expected result:
- Test passes after Task 2.
- If it fails due to real workbook source issues, stop and report the exact source rows rather than relaxing the assertions.

### Task 4: Add a focused Z06 draft-data test

Objective: Lock the Z06 draft contract and the recently approved Z06 package/pricing decisions.

Files:
- Create `tests/z06-form-data-draft.test.mjs`.

Steps:
1. Start from the top-level contract assertions in `tests/grand-sport-draft-data.test.mjs`.
2. Keep this test focused on Z06 contract shape and approved package/pricing rows, not broad Grand Sport-specific rules.
3. Assert the Z06 draft remains `draft_not_runtime_active`.
4. Assert the six Z06 variant IDs.
5. Assert PDB/PDD/PDF, ROY/ROZ/STZ, Z07 placements.
6. Assert default-selected Z06 choices are selectable.
7. Assert key Z06 price rules are emitted.
8. Run:
   - `node --test tests/z06-form-data-draft.test.mjs`

Expected result:
- Test passes and provides a reusable guard for the next Z06 readiness pass.

### Task 5: Run targeted gates and review generated artifacts

Objective: Prove the new Z06 draft path does not regress live models.

Commands:

```sh
.venv/bin/python scripts/build_future_z_rule_audit.py --model-key z06 --format json
.venv/bin/python scripts/generate_z06_form.py
node --test tests/z06-contract-preview.test.mjs
node --test tests/z06-form-data-draft.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Also run a focused app-data mutation check in tests, and manually review:

```sh
git diff -- scripts/corvette_form_generator/model_configs.py scripts/generate_z06_form.py tests/z06-contract-preview.test.mjs tests/z06-form-data-draft.test.mjs form-output/inspection
```

Expected result:
- New Z06 artifacts exist and are generated from the script.
- Existing Grand Sport draft/preview tests still pass.
- Multi-model runtime switching still passes, proving no registry/runtime promotion happened.
- `form-app/data.js` has no diff.

## Risks and non-goals

Risks:

- Z06 draft generation may expose source-data defects in interiors, variant availability, section mapping, or rules. If so, stop and report exact workbook rows/sheets rather than papering over them.
- The generic `inspection.py` draft helpers may assume Grand Sport-like model metadata in a few spots. If a helper change is needed, it must be model-general and covered by both Z06 and Grand Sport tests.
- Generated artifact counts may shift as workbook source data is corrected. Tests should assert important contracts and business decisions, not brittle whole-file row counts unless those counts are meaningful.

Non-goals:

- No Z06 live activation.
- No ZR1/ZR1X preview generation in this pass. Those should follow after the Z06 path is proven, or be added in a separate model-general expansion pass.
- No workbook data edits.
- No runtime UI changes.
- No dealer submission changes.
- No package-rule redesign beyond verifying that the workbook-authored Z06 package/pricing rules emit into draft data.

## Validation plan

Minimum targeted gates for this pass:

```sh
.venv/bin/python -m py_compile scripts/corvette_form_generator/model_configs.py scripts/generate_z06_form.py
.venv/bin/python scripts/build_future_z_rule_audit.py --model-key z06 --format json
.venv/bin/python scripts/generate_z06_form.py
node --test tests/z06-contract-preview.test.mjs
node --test tests/z06-form-data-draft.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

If generic inspection helpers change, also run:

```sh
node --test tests/grand-sport-rule-audit.test.mjs
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
```

Diff-review checklist before handoff:

- `form-app/data.js` unchanged.
- `stingray_master.xlsx` unchanged.
- Z06 artifacts are the only new generated artifacts unless the tests legitimately regenerate Grand Sport inspection outputs.
- No `.DS_Store`, `backups/`, lock files, or temporary files staged.
- No model-specific product logic added to runtime JavaScript.

## Approval boundary

Approval to implement this spec would authorize the non-live Z06 preview/draft generator, tests, and generated Z06 inspection artifacts only. It would not authorize activating Z06 in the live registry, changing workbook source rows, changing dealer submission behavior, or adding ZR1/ZR1X draft generation.
