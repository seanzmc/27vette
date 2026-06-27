# Pass 17 — Default-Selected Display Metadata Derivation Spec

Status: Implemented 2026-06-24.
Date: 2026-06-24
Recommended reasoning level for implementation agent: high.

Source context:

- `AGENTS.md`
- Root `codex-context.md`: absent during spec creation; archived codex context remains retired historical context and must not be used as current guidance.
- `docs/audit-cleanup/pass-16-variant-override-sheet-semantics-report.md`
- `docs/metadata-runtime-redundancy-6-23.md`
- `docs/Audit-route-map.md`
- `27vette-workbook-guard` reference `variant-override-semantics-classification.md`

## Implementation completion evidence

Implemented on 2026-06-24.

Changed source files and workbook sheets:

- `scripts/corvette_form_generator/runtime_metadata.py`
  - Added shared `derived_default_selected_display_behavior()` logic backed by workbook `default_selection_rules` plus active single-selection exclusive groups.
  - Kept a narrow Pass 17 rule-id drift guard so derivation covers only Stingray `default_bc7`, Grand Sport `gs_default_bc7_coupe`, and Grand Sport `gs_default_nga_unless_nwi`.
- `scripts/corvette_form_generator/production.py`
  - Applies derived default-selected display metadata in the Stingray choice emission path after status/selectability/active resolution and before writing `display_behavior`.
- `scripts/corvette_form_generator/inspection.py`
  - Applies the same derived display metadata in the Grand Sport/Z06 inspection/runtime-contract preview path. The guard prevents Z06 expansion in this pass.
- `stingray_master.xlsx`
  - `variant_option_overrides`: deleted only the three Stingray BC7 rows for `1lt_c07`, `2lt_c07`, and `3lt_c07`.
  - `grandSport_variant_overrides`: deleted only the three Grand Sport BC7 rows for `1lt_e07`, `2lt_e07`, and `3lt_e07`, plus the six Grand Sport NGA rows for all active Grand Sport variants.
  - Preserved all UQT rows in `variant_option_overrides`, `grandSport_variant_overrides`, and `z06_variant_overrides`.
- `tests/stingray-generator-stability.test.mjs`
  - Added guards that Stingray BC7 override rows are gone, BC7 coupe choices still emit `default_selected`, Stingray NGA did not gain `default_selected`, and UQT override rows remain.
- `tests/grand-sport-draft-data.test.mjs`
  - Added guards that Grand Sport BC7/NGA override rows are gone while Grand Sport UQT display-only standard rows remain.
- Regenerated artifacts:
  - `form-output/runtime/stingray-runtime-contract.json`
  - `form-output/runtime/grand-sport-runtime-contract.json`
  - `form-output/stingray-form-data.json`
  - `form-output/stingray-form-data.csv`
  - `form-app/data.js`

Completion validation:

- Preflight/package:
  - `git status --short --branch`
  - lock-file probe: `LOCKFILE_ABSENT`
  - `.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx`: valid, 0 issues.
- Workbook save verification:
  - Safe-saved via `save_workbook_safely()`; backup created at `backups/stingray_master-20260624-102850.xlsx`.
  - Reopened workbook read-only and asserted exact BC7/NGA row deletion plus UQT/Z06 preservation.
  - `.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx`: valid, 0 issues after save.
- Regeneration:
  - `.venv/bin/python scripts/generate_form.py --model stingray`
  - `.venv/bin/python scripts/generate_form.py --model grand_sport`
  - `.venv/bin/python scripts/generate_registry.py`
- Parity/field guards:
  - `node scripts/compare-generated-contracts.mjs /tmp/pass-17-before/stingray-runtime-contract.json /tmp/pass-17-after/stingray-runtime-contract.json`: contracts match.
  - `node scripts/compare-generated-contracts.mjs /tmp/pass-17-before/grand-sport-runtime-contract.json /tmp/pass-17-after/grand-sport-runtime-contract.json`: contracts match.
  - `node scripts/compare-generated-contracts.mjs /tmp/pass-17-before/stingray-form-data.json /tmp/pass-17-after/stingray-form-data.json`: contracts match.
  - `cmp /tmp/pass-17-before/stingray-form-data.csv /tmp/pass-17-after/stingray-form-data.csv`: no diff.
  - `form-app/data.js` payload parity after normalizing `dataset.generated_at`: pass.
  - Focused field guard: `PASS17_FIELD_GUARDS_OK` for BC7/NGA/UQT and no Stingray NGA drift.
- Targeted gates:
  - `.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx`: valid, 0 issues.
  - `node --test tests/stingray-generator-stability.test.mjs`: 13/13 pass.
  - `node --test tests/stingray-form-regression.test.mjs`: 87/87 pass.
  - `node --test tests/grand-sport-draft-data.test.mjs`: 19/19 pass.
  - `node --test tests/grand-sport-contract-preview.test.mjs`: 6/6 pass.
  - `node --test tests/multi-model-runtime-switching.test.mjs`: 46/46 pass.
- Local browser/runtime proof:
  - Served `form-app` with `../.venv/bin/python -m http.server 8000`.
  - Browser console probe returned `PASS17_BROWSER_RUNTIME_PROOF_OK`.
  - Covered Stingray coupe 1LT/2LT/3LT BC7 default/paid-peer replacement/restoration, Grand Sport coupe 1LT/2LT/3LT BC7 default/paid-peer replacement/restoration, Grand Sport all six variants NGA/NWI replacement/restoration with WUB preserved as enabler, and Stingray/Grand Sport UQT smoke.
  - Browser console messages/errors after proof: none.

Residual risk and follow-up:

- UQT was deferred/accepted as-is during Pass 17 because its then-current rows owned selectability, display-only behavior, and trim-standard section placement that OVS/default rules did not own. Historical follow-up: Pass 18 later implemented UQT single-canonical-option source ownership.
- `z06_variant_overrides` remained unchanged during Pass 17 and still carried Z06 UQT display-only standard rows.
- Recommended next pass at Pass 17 closure was UQT source ownership; that follow-up became Pass 18 and was implemented on 2026-06-24. Do not delete variant override sheets wholesale.

## Goal

Implement the narrow default-selected display metadata cleanup identified by Pass 16.

The future implementation should derive emitted `display_behavior=default_selected` for only these current variant-override behavior rows from existing workbook-owned default/exclusive/source metadata, then remove only the redundant override rows after generated-data and browser/runtime parity proof:

- Stingray BC7 coupe default-selected display metadata.
- Grand Sport BC7 coupe default-selected display metadata.
- Grand Sport NGA all-variant default-selected display metadata.

UQT trim-scoped included-equipment behavior is intentionally deferred and accepted as-is for this pass. Do not modify or reinterpret UQT override rows.

## Diagnosis

Change type for this spec: docs-only.

Change type for the future implementation pass: mixed workbook/data + generator + generated artifacts + tests, with no intended runtime UX behavior change.

Risk level: medium. The target rows currently affect emitted choice `display_behavior`, which the browser runtime uses in `resetDefaults()` / `addWorkbookDefaultChoices()` to seed selectable defaults. The cleanup is safe only if generated contracts preserve the same default-selected choices and local browser/runtime proof confirms the same selected-state behavior after the rows are removed.

Root cause from Pass 16:

- BC7 and Grand Sport NGA runtime default/restoration behavior already has normal workbook owners in `default_selection_rules` plus exclusive groups.
- The generated choice field `display_behavior=default_selected` still comes from variant override rows rather than from those normal owners.
- UQT rows are a different behavior class: they carry selectability, `display_behavior=display_only`, and trim-standard `section_id` placement that OVS/default rules do not own. UQT is not an active cleanup candidate for this pass.

Current worktree evidence at spec creation:

- Branch/status: `schema-ingestion-normalization...origin/main` with pre-existing Pass 16 docs changes:
  - `docs/Audit-route-map.md`
  - `docs/audit-cleanup/pass-16-variant-override-sheet-semantics-report-spec.md`
  - `docs/metadata-runtime-redundancy-6-23.md`
  - `docs/audit-cleanup/pass-16-variant-override-sheet-semantics-report.md`
- Root `codex-context.md` was absent.
- No workbook or generated artifact probes in this spec pass were write-mode; this spec should be the only new file from this pass.

## Evidence inspected for this spec

Pass 16 report evidence:

- `variant_option_overrides` has 7 consumed Stingray rows. Rows 6-8 are BC7 default-selected display metadata; rows 2-5 are UQT suppression and are deferred.
- `grandSport_variant_overrides` has 13 active rows. Rows 6-8 are BC7 default-selected display metadata; rows 9-14 are NGA default-selected display metadata; rows 2-5 are UQT display-only placement and are deferred.
- `z06_variant_overrides` has 4 active UQT rows only and is entirely out of scope for this pass.

Generator/code evidence:

- `scripts/corvette_form_generator/runtime_metadata.py`
  - `load_variant_option_overrides()` lines 232-276 split global emitted-value `active` semantics from model-scoped row activation semantics.
  - `load_default_selection_rules()` lines 279-280 reads active workbook default-selection rows.
  - `_load_rule_rows()` lines 287-298 strips workbook `active`/`model_key` and returns sorted rule rows.
- `scripts/corvette_form_generator/production.py`
  - `build_production_source_data()` loads `default_selection_rules` around line 179 and emits them at line 624.
  - It loads/applies variant overrides around lines 194-200 and 331-339.
  - It writes choice `display_behavior` around lines 372-373.
- `scripts/corvette_form_generator/inspection.py`
  - `display_behavior_status()` lines 271-283 applies display behavior to status/selectability.
  - `keyed_variant_option_overrides()` / `apply_variant_option_override()` lines 286-302 apply fallback override rows.
  - `build_contract_preview()` applies overrides around lines 792-827 and emits choice `display_behavior`.
  - `build_form_data_draft()` loads `default_selection_rules` around lines 964-970 and emits them at line 1191.
- `form-app/app.js`
  - `generatedDefaultRules()` lines 622-624 reads generated default-selection rules.
  - `resetDefaults()` lines 1332-1350 calls `addWorkbookDefaultChoices()` and `addGeneratedDefaultChoices()`.
  - `addWorkbookDefaultChoices()` lines 1352-1373 uses choice `display_behavior=default_selected` to seed selectable workbook defaults.
  - `reconcileSelections()` lines 1693-1717 re-adds workbook/default choices after selection reconciliation.

Test evidence:

- `tests/stingray-generator-stability.test.mjs:394-417` currently pins Stingray UQT override rows and guards against hardcoded `opt_uqt_002` logic. It does not currently assert BC7 override-row retirement.
- `tests/stingray-form-regression.test.mjs:529-609` pins Stingray BC7 selected-state behavior and peer replacement/restoration.
- `tests/grand-sport-draft-data.test.mjs:538-550` pins Grand Sport BC7 coupe and NGA generated `display_behavior=default_selected` metadata.
- `tests/multi-model-runtime-switching.test.mjs` contains active exclusive-group expectations for Stingray/Grand Sport engine-cover and exhaust groups.
- `tests/grand-sport-contract-preview.test.mjs` did not have direct BC7/NGA default-selected assertions in the Pass 16 grep probe, but it remains a reasonable Grand Sport contract gate if generated data changes.

## Exact files, sheets, and symbols to inspect before implementation

Workbook sheets, read-only first:

- `variant_option_overrides`
  - Inspect rows for `option_id=opt_bc7_001` and `option_id=opt_uqt_002`.
  - Confirm BC7 rows are only `1lt_c07`, `2lt_c07`, `3lt_c07` with `display_behavior=default_selected`.
  - Confirm UQT rows 2-5 remain present and are explicitly out of scope.
- `grandSport_variant_overrides`
  - Inspect rows for `option_id=opt_bc7_001`, `option_id=opt_nga_001`, and `option_id=opt_uqt_001`.
  - Confirm BC7 rows are only coupe variants `1lt_e07`, `2lt_e07`, `3lt_e07`.
  - Confirm NGA rows cover all six active Grand Sport variants.
  - Confirm UQT rows 2-5 remain present and are explicitly out of scope.
- `default_selection_rules`
  - `default_bc7`
  - `gs_default_bc7_coupe`
  - `gs_default_nga_unless_nwi`
  - Also inspect `default_nga` for Stingray as an out-of-scope drift sentinel; this pass must not silently add new Stingray NGA `display_behavior=default_selected` output.
- `exclusive_groups` / `exclusive_group_members`
  - `grp_ls6_engine_covers` and members including `opt_bc7_001`.
  - `excl_exhaust_path` as an out-of-scope Stingray NGA sentinel.
- `grandSport_exclusive_groups` / `grandSport_exclusive_members`
  - `gs_excl_ls6_engine_covers` and members including `opt_bc7_001`.
  - `gs_excl_exhaust_path` and members `opt_nga_001`, `opt_nwi_001`.
- `stingray_ovs`, `grandSport_ovs`
  - BC7 coupe/convertible statuses.
  - Grand Sport NGA all-variant statuses.
- `stingray_options`, `grandSport_options`
  - `opt_bc7_001`, `opt_nga_001`, and UQT rows for source context.

Generator/runtime symbols:

- `scripts/corvette_form_generator/runtime_metadata.py`
  - `load_default_selection_rules()`
  - `_load_rule_rows()`
  - `load_variant_option_overrides()`
  - New helper should live here if shared derivation logic is needed; do not add a new module unless current files cannot express the helper cleanly.
- `scripts/corvette_form_generator/production.py`
  - `build_production_source_data()`
  - Stingray choice loop applying variant overrides and emitting `display_behavior`.
- `scripts/corvette_form_generator/inspection.py`
  - `display_behavior_status()`
  - `keyed_variant_option_overrides()`
  - `apply_variant_option_override()`
  - `build_contract_preview()` choice loop.
  - `build_form_data_draft()` draft choice emission.
- `form-app/app.js`
  - `resetDefaults()`
  - `addWorkbookDefaultChoices()`
  - `reconcileSelections()`
  - `handleChoice()`
  - Browser proof should inspect state through the existing runtime hooks; do not change these symbols unless the implementation proves generator-only derivation cannot preserve behavior.

Generated artifacts to inspect/baseline:

- `form-output/runtime/stingray-runtime-contract.json`
- `form-output/stingray-form-data.json`
- `form-output/stingray-form-data.csv`
- `form-output/runtime/grand-sport-runtime-contract.json`
- `form-app/data.js`

## Expected files and sheets to change in the implementation pass

Workbook source:

- `stingray_master.xlsx`
  - `variant_option_overrides`: delete only the three BC7 rows:
    - `opt_bc7_001` / `1lt_c07`
    - `opt_bc7_001` / `2lt_c07`
    - `opt_bc7_001` / `3lt_c07`
  - `grandSport_variant_overrides`: delete only the nine default-selected rows:
    - `opt_bc7_001` / `1lt_e07`, `2lt_e07`, `3lt_e07`
    - `opt_nga_001` / `1lt_e07`, `2lt_e07`, `3lt_e07`, `1lt_e67`, `2lt_e67`, `3lt_e67`
  - Preserve all UQT rows in `variant_option_overrides`, `grandSport_variant_overrides`, and `z06_variant_overrides`.
  - Refresh affected Excel table refs through the workbook safe-save path if row deletion changes table dimensions.

Generator code:

- `scripts/corvette_form_generator/runtime_metadata.py`
  - Expected small shared helper for deriving default-selected choice keys from `default_selection_rules` plus current choice/variant/source metadata and exclusive-group ownership.
  - The helper must be generic and data-driven where possible, but it must include drift guards so it does not expand this pass beyond the BC7/NGA row set. If generic derivation would also add `default_selected` to out-of-scope rows such as Stingray NGA or Z06 defaults, stop and revise the spec rather than shipping hidden behavior drift.
- `scripts/corvette_form_generator/production.py`
  - Apply the helper in the Stingray choice emission path after status/selectability/active resolution and before writing `display_behavior`.
- `scripts/corvette_form_generator/inspection.py`
  - Apply the same helper in the contract-preview/draft path for Grand Sport.
  - Do not change Z06 UQT behavior.

Tests:

- `tests/stingray-generator-stability.test.mjs`
  - Keep the existing UQT source guard.
  - Add or adjust assertions proving Stingray BC7 override rows are no longer required while generated BC7 coupe choices remain `display_behavior=default_selected`.
  - Add a negative guard that UQT rows remain in `variant_option_overrides`.
- `tests/stingray-form-regression.test.mjs`
  - Keep or strengthen BC7 browser/runtime selected-state assertions for coupe default, paid-cover replacement, paid-cover removal restoring BC7, and selecting BC7 back.
- `tests/grand-sport-draft-data.test.mjs`
  - Keep generated BC7/NGA `display_behavior=default_selected` assertions.
  - Add workbook/source guard that `grandSport_variant_overrides` retains UQT rows and no longer carries BC7/NGA default-selected rows after the workbook cleanup.
- `tests/multi-model-runtime-switching.test.mjs`
  - Use only if implementation needs an additional multi-model runtime guard for Grand Sport BC7/NGA selected-state behavior; otherwise leave unchanged and rely on existing group metadata tests plus browser proof.

Generated artifacts expected to change after regeneration:

- `form-output/runtime/stingray-runtime-contract.json`
- `form-output/stingray-form-data.json`
- `form-output/stingray-form-data.csv`
- `form-output/runtime/grand-sport-runtime-contract.json`
- `form-app/data.js`

The intended generated payload delta is timestamp-only after normalizing timestamps. Any non-timestamp payload change must be allowlisted and explained before handoff. In particular, no new Stingray NGA default-selected output, no UQT output drift, and no Z06 output drift are approved by this spec.

Spec closure:

- `docs/audit-cleanup/pass-17-default-selected-display-metadata-derivation-spec.md` must be updated from spec-only to implemented/completed before final handoff if the implementation pass is approved and completed.
- `docs/metadata-runtime-redundancy-6-23.md` and `docs/Audit-route-map.md` should be updated only if the implementation changes the recommended next pass or standing route-map status.

## Implementation approach

1. Preflight:
   - Verify branch/status and list pre-existing dirty files.
   - Confirm no Excel lock file exists.
   - Validate workbook package before writing.
   - Snapshot current generated runtime contracts and relevant compatibility artifacts to `/tmp/pass-17-before/`.
2. Characterize current default-selected candidates:
   - Read workbook default-selection rules and exclusive groups.
   - Build a report of candidate derived `(model_key, option_id, variant_id)` pairs.
   - Required candidate set:
     - Stingray BC7 coupe: three variants.
     - Grand Sport BC7 coupe: three variants.
     - Grand Sport NGA: six variants.
   - Required non-candidate set:
     - all UQT rows.
     - Stingray NGA unless explicitly re-scoped by a new spec.
     - Z06 rows and defaults.
3. Add RED tests/guards before workbook deletion:
   - Assert generated BC7/NGA default-selected output can be produced from default rules when override rows are absent, preferably by direct helper characterization or a temp-copy workbook probe.
   - Assert UQT override rows are still required/preserved.
4. Implement derivation:
   - Use `default_selection_rules` as the primary owner.
   - Require source/OVS status and exclusive-group membership to match the existing default-selected generated shape.
   - Do not infer UQT display-only behavior from standard status.
   - Do not hardcode browser runtime RPO behavior.
5. Delete only approved workbook rows with `save_workbook_safely()`:
   - Remove the three Stingray BC7 default-selected override rows.
   - Remove the three Grand Sport BC7 and six Grand Sport NGA default-selected override rows.
   - Preserve all UQT rows and `z06_variant_overrides` unchanged.
   - Reopen/inspect the saved workbook and verify exact row counts and remaining row identities on disk before generating.
6. Regenerate Stingray and Grand Sport, then registry.
7. Run generated parity checks and targeted tests.
8. Run local browser/runtime proof for BC7 and NGA.
9. Review diffs and restore unrelated timestamp-only or non-target generated churn if it appears outside the approved artifact set.
10. Update this spec with completion evidence before final handoff.

## UQT deferred / accepted-as-is documentation

For this pass, UQT is not a cleanup candidate.

Implementation must document UQT as intentionally deferred in three places:

1. This spec's completion evidence.
2. Any changed source/test comments that mention variant overrides.
3. Final handoff.

Required UQT assertions for implementation:

- `variant_option_overrides` still contains the four Stingray `opt_uqt_002` rows with `status=unavailable`, `selectable=False`, `active=False`.
- `grandSport_variant_overrides` still contains the four Grand Sport `opt_uqt_001` rows with `selectable=False`, `display_behavior=display_only`, and trim-standard `section_id` values.
- `z06_variant_overrides` remains unchanged.
- Generated UQT choices are byte/structure equivalent to the baseline except timestamps.

Rationale: UQT rows carry selectability and section placement behavior that OVS/default-selection rules do not own. Removing them without a separate source-row/section-placement design would hide a data modeling problem in generator code.

## Validation plan for implementation

Preflight:

```sh
git status --short --branch
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python - <<'PY'
from pathlib import Path
raise SystemExit(1 if Path('~$stingray_master.xlsx').exists() else 0)
PY
```

Read-only candidate/guard probes before writing:

```sh
.venv/bin/python - <<'PY'
# Inspect default_selection_rules, variant override sheets, *_ovs, and exclusive groups.
# Print/verify the exact candidate set:
# - stingray opt_bc7_001 coupe variants only
# - grand_sport opt_bc7_001 coupe variants only
# - grand_sport opt_nga_001 all six variants only
# Also print/verify non-candidates:
# - all UQT override rows
# - Stingray NGA
# - Z06 rows/defaults
PY
```

Baseline generated artifacts:

```sh
mkdir -p /tmp/pass-17-before /tmp/pass-17-after
cp form-output/runtime/stingray-runtime-contract.json /tmp/pass-17-before/
cp form-output/runtime/grand-sport-runtime-contract.json /tmp/pass-17-before/
cp form-output/stingray-form-data.json /tmp/pass-17-before/
cp form-output/stingray-form-data.csv /tmp/pass-17-before/
cp form-app/data.js /tmp/pass-17-before/
```

Workbook write verification after row deletion:

```sh
.venv/bin/python - <<'PY'
# Reopen stingray_master.xlsx read-only.
# Assert variant_option_overrides has only the four UQT rows for the target set and no opt_bc7_001 rows.
# Assert grandSport_variant_overrides has the four UQT rows and no opt_bc7_001/opt_nga_001 default-selected rows.
# Assert z06_variant_overrides is unchanged.
PY
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
```

Regeneration:

```sh
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_registry.py
```

Generated parity / allowlist checks:

```sh
cp form-output/runtime/stingray-runtime-contract.json /tmp/pass-17-after/
cp form-output/runtime/grand-sport-runtime-contract.json /tmp/pass-17-after/
cp form-output/stingray-form-data.json /tmp/pass-17-after/
cp form-output/stingray-form-data.csv /tmp/pass-17-after/
cp form-app/data.js /tmp/pass-17-after/
node scripts/compare-generated-contracts.mjs /tmp/pass-17-before/stingray-runtime-contract.json /tmp/pass-17-after/stingray-runtime-contract.json
node scripts/compare-generated-contracts.mjs /tmp/pass-17-before/grand-sport-runtime-contract.json /tmp/pass-17-after/grand-sport-runtime-contract.json
node scripts/compare-generated-contracts.mjs /tmp/pass-17-before/stingray-form-data.json /tmp/pass-17-after/stingray-form-data.json
cmp /tmp/pass-17-before/stingray-form-data.csv /tmp/pass-17-after/stingray-form-data.csv
```

If any comparator fails for non-timestamp fields, run a focused allowlist probe and stop unless the only differences are explicitly approved:

- Removed workbook source rows from variant override sheets.
- Timestamp fields in generated artifacts.
- No choice/status/selectable/active/display_behavior/section_id/step_key drift for BC7, NGA, UQT, or unrelated choices.

Targeted tests:

```sh
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
node --test tests/stingray-generator-stability.test.mjs
node --test tests/stingray-form-regression.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Local browser/runtime proof:

Serve the app:

```sh
cd form-app
../.venv/bin/python -m http.server 8000
```

Then in the browser/runtime console or equivalent automated probe:

- Stingray coupe 1LT/2LT/3LT:
  - activate Stingray;
  - set coupe + trim;
  - `resetDefaults()` then `reconcileSelections()`;
  - assert `opt_bc7_001` is selected;
  - select a paid engine-cover peer such as BCP and assert BC7 is removed;
  - remove the paid peer and assert BC7 is restored;
  - select BC7 back and assert the paid peer is removed.
- Grand Sport coupe 1LT/2LT/3LT:
  - activate Grand Sport;
  - set coupe + trim;
  - assert `opt_bc7_001` selected by default and peer replacement/restoration works for engine-cover peers.
- Grand Sport all six variants:
  - assert `opt_nga_001` selected by default unless NWI is selected;
  - select NWI and assert NGA is replaced;
  - remove NWI and assert NGA restores;
  - confirm WUB remains an enabler and not an exhaust-tip peer.
- UQT smoke:
  - Stingray UQT paid option remains selectable only on 1LT and suppressed for 2LT/3LT.
  - Grand Sport 1LT UQT remains selectable in Interior Trim.
  - Grand Sport 2LT/3LT UQT remains display-only standard equipment.

After browser proof, check console errors and stop the server.

Final diff/status checks:

```sh
git diff --check
git status --short
git diff -- docs/audit-cleanup/pass-17-default-selected-display-metadata-derivation-spec.md scripts/corvette_form_generator/runtime_metadata.py scripts/corvette_form_generator/production.py scripts/corvette_form_generator/inspection.py tests/stingray-generator-stability.test.mjs tests/stingray-form-regression.test.mjs tests/grand-sport-draft-data.test.mjs tests/grand-sport-contract-preview.test.mjs tests/multi-model-runtime-switching.test.mjs
```

## Risks and mitigations

- Risk: generic derivation marks out-of-scope defaults such as Stingray NGA or Z06 defaults as `default_selected`.
  - Mitigation: precompute candidate and non-candidate sets before workbook writes; add an allowlist probe that fails on any out-of-scope `display_behavior` drift.
- Risk: removing BC7/NGA override rows preserves generated data but breaks browser restoration loops.
  - Mitigation: run local browser/runtime proof for BC7 and NGA replacement/removal/restoration paths, not only generated JSON tests.
- Risk: UQT rows are accidentally removed or reinterpreted because they share the same sheets.
  - Mitigation: add explicit UQT preservation assertions before and after workbook save; treat UQT as accepted-as-is in spec/handoff.
- Risk: workbook row deletion corrupts Excel table refs or cell typing.
  - Mitigation: use `save_workbook_safely()`, refresh table refs as needed, validate package, and reopen the workbook read-only to verify rows on disk.
- Risk: generated timestamp/artifact churn hides payload drift.
  - Mitigation: snapshot before/after artifacts and use timestamp-ignored contract comparison plus focused field-level probes for target options.
- Risk: implementation hides product logic in model/RPO-specific generator branches.
  - Mitigation: derivation must be data-driven from workbook default rules, OVS/source rows, and exclusive groups; any hardcoded target allowlist may only be used as a validation/drift guard, not as the business rule owner.

## Non-goals

Do not change:

- UQT behavior, UQT rows, or UQT generated output.
- `z06_variant_overrides` or Z06 default behavior.
- Variant override sheet headers or schema.
- `runtime_action`, `body_style_scope`, direct-rule matching, or replacement semantics.
- Runtime JavaScript unless generator-only derivation proves impossible and a revised implementation spec is approved.
- Visual styling, layout, dealer submission endpoint/payload/Turnstile behavior.
- `form-app/app.js` behavior or customer-facing interaction semantics.
- Any unrelated workbook rows, generated artifacts, tests, docs, or workflow code.
- Whole-sheet deletion of `variant_option_overrides`, `grandSport_variant_overrides`, or `z06_variant_overrides`.

## Historical approval prompt

Pass 17 was approved and implemented on 2026-06-24. The approved implementation derived BC7/NGA `display_behavior=default_selected` from existing workbook default/exclusive/source metadata, deleted only the now-redundant BC7/NGA variant override rows after parity proof, preserved/deferred UQT exactly as-is, regenerated Stingray/Grand Sport/registry artifacts, ran the targeted gates and local browser/runtime proof, and updated this spec with completion evidence before handoff.
