Report-only architecture cleanup pass completed. No code, workbook, generated artifacts, or docs were changed.

Workspace note:

- Branch: generator-simplification-pass1
- Status: untracked docs/cleanup-risk-remaining.md existed before this report pass. I read it as relevant context but did not edit it.
- codex-context.md only exists under archive-2026-05-29/, so I treated AGENTS.md and live repo evidence as current.

Validation run:

- .venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
- Result: valid, 0 issues.

Architecture findings ranked by cleanup priority

1. Rule behavior surfaces: runtime_action and body_style_scope
   Risk: Critical for cleanup, medium current live risk if left alone.

Evidence:

- Workbook active direct rule rows:
  - rule_mapping: 144 active rows
    - 5 runtime_action=replace
    - 8 active rows with body_style_scope
  - grandSport_rule_mapping: 122 active rows
    - 6 runtime_action=replace
    - 9 active rows with body_style_scope
  - z06_rule_mapping: 73 active rows
    - 1 runtime_action=replace
    - 3 active rows with body_style_scope
- Generated live app data still emits and runtime consumes these fields:
  - Stingray: 144 rules, 5 replace rules, 8 body-scoped rules
  - Grand Sport: 122 rules, 6 replace rules, 9 body-scoped rules
  - Z06: 73 rules, 1 replace rule, 3 body-scoped rules
- Runtime consumers:
  - form-app/app.js:553-563: ruleAppliesToCurrentVariant() directly filters rules by rule.body_style_scope.
  - form-app/app.js:931-958: disableReasonForChoice() treats runtime_action=replace differently from normal excludes.
  - form-app/app.js:1433-1439: removeReplaceRuleTargets() deletes selected targets for replace rules.
- Generator consumers/emitters:
  - scripts/corvette_form_generator/rules.py:160-200
  - scripts/corvette_form_generator/production.py:417-469

Assessment:

- runtime_action is not cleanup metadata. It is live behavior.
- body_style_scope is also live behavior for direct rules, price rules, default rules, groups, and runtime exceptions. It cannot be retired as a simple rule-mapping-column cleanup.
- The safe cleanup is not “delete columns.” It is to remodel specific behavior classes into workbook-owned canonical structures.

Notable replace-rule buckets:

- Stingray replace rules remove opt_t0a_001 under Z51/aero-type sources.
- Grand Sport replace rules cover J57/J6A, FEY/T0E, FEB/FEY brake replacements, and NWI/NGA.
- Z06 has one replace rule: z06_rule_opt_j57_001_excludes_opt_j6a_001.

Recommended next pass:

- Rule behavior classification report:
  - Classify each runtime_action=replace row as:
    - default replacement,
    - exclusive peer replacement,
    - package-included replacement,
    - or true special behavior.
  - Do not edit yet.
  - Output should be a row-level table with proposed canonical owner: default_selection_rules, _\_exclusive_groups, _\_rule_groups, direct \*\_rule_mapping, or keep.

2. Runtime hardcoded RPO exception: GBA / opt_zyc_001
   Risk: High architecture risk, probably narrow behavior risk.

Evidence:

- form-app/app.js:935 has:
  - if (choice.rpo === "GBA" && rule.source_id === "opt_zyc_001") continue;
- This is the only exact .rpo === "..." hardcode found in form-app/app.js.
- Workbook already has a runtime-rule-exception row:
  - runtime_rule_exceptions row 5:
    - model stingray
    - source opt_gba_001
    - target opt_zyc_001
    - type remove_target_when_source_selected
    - reason: ZYC Body-Color Accents are not available with Black exterior paint.
- Tests already assert workbook/group behavior around GBA/ZYC:
  - tests/stingray-form-regression.test.mjs:2184-2198
  - tests/z06-form-data-draft.test.mjs:217-224
  - tests/multi-model-runtime-switching.test.mjs:908-911

Assessment:

- This is the clearest active violation of “runtime JS should not encode product/RPO knowledge.”
- Because a workbook exception path exists, this should be reviewed as a small generic-runtime cleanup candidate.
- It should not be removed blindly; the runtime behavior it protects needs a RED test first.

Recommended next pass:

- Narrow runtime exception cleanup spec:
  - Prove whether runtime_rule_exceptions and/or workbook excludes_any groups fully replace the hardcoded GBA/opt_zyc_001 skip.
  - Add a runtime test that fails if removing the hardcode regresses GBA/ZYC/CFL behavior.
  - Then remove only the hardcoded line if the generic workbook-driven path covers it.

3. Interior stale edge routes: interior_reference_path and CSV files
   Status: Completed 2026-06-18.
   Original risk: Medium current risk, high cleanup/review value.

Evidence:

- interior_reference_path no longer exists in active config surfaces:
  - `ModelConfig.interior_reference_path` was removed.
  - the `base_model_config()` CSV-path assignment was removed.
- Current active generator code no longer consumes config.interior_reference_path.
  - A source guard now rejects reintroducing it in active interior pipeline sources.
- Current shared interior builder is workbook-owned:
  - scripts/corvette_form_generator/interiors.py:118-185
  - It reads model_interior_scope, interior_components, lt_interiors / LZ_Interiors, and PriceRef.
  - It hard-fails if model_interior_scope is missing: interiors.py:141-145.
- Workbook has active interior scope rows:
  - model_interior_scope: 572 active rows
    - Stingray 130
    - Grand Sport 132
    - Z06 130
    - ZR1 90
    - ZR1X 90
  - interior_components: 846 active rows
- The stale CSV files are deleted:
  - architectureAudit/stingray_interiors_refactor.csv
  - architectureAudit/grand_sport_interiors_refactor.csv
- Current tests already guard workbook-owned grouping:
  - tests/grand-sport-draft-data.test.mjs:624-647
  - tests/stingray-form-regression.test.mjs:44-46 and later model_interior_scope coverage
  - tests/z06-form-data-draft.test.mjs:407-439

Assessment:

- Completed cleanup removed the dead config/file surfaces rather than creating another parallel hierarchy source.
- Keep the guard; do not reintroduce CSV/reference hierarchy paths for active interior generation.

4. Optional audit/report tooling: build_rule_sources.py and audit tests
   Risk: Medium.

Evidence:

- README.md:49 and README.md:291-296 correctly label scripts/build_rule_sources.py and audit tests as opt-in, not default readiness.
- AGENTS.md:356-362 also correctly labels the audit block as optional.
- scripts/build_rule_sources.py writes artifacts:
  - form-output/inspection/<model>-rule-audit.json
  - form-output/inspection/<model>-rule-audit.md
  - write calls at scripts/build_rule_sources.py:915-922
- tests/grand-sport-rule-audit.test.mjs invokes:
  - scripts/build_rule_sources.py --model grand_sport
  - scripts/generate_form.py --model grand_sport
  - see tests/grand-sport-rule-audit.test.mjs:57-68
- tests/audit-parser-metadata-loaders.test.mjs imports parser helpers from build_rule_sources.py and validates workbook-owned rule_phrase_map.
- Edge route found:
  - scripts/corvette_form_generator/editor_ops.py:583-587 includes node --test tests/grand-sport-rule-audit.test.mjs in Grand Sport post-apply gate reminders.
  - That conflicts with the “optional, not default readiness” classification in AGENTS.md / README.md.

Assessment:

- build_rule_sources.py still has value as opt-in provenance/audit tooling.
- But because it writes inspection artifacts and its test invokes generation, it should not be surfaced as a default editor apply gate.
- The main cleanup is not deleting the tool; it is aligning editor gate reminders with the documented default readiness boundary.

Recommended next pass:

- Editor gate-boundary cleanup:
  - Remove tests/grand-sport-rule-audit.test.mjs from default editor_ops.py Grand Sport GATE_COMMANDS, or split it into an explicitly optional audit command list.
  - Keep README/AGENTS optional audit block unchanged unless wording needs to mention the editor split.
  - No workbook change expected.

5. Stale docs detected
   Risk: Low for runtime, medium for future-agent steering.

Evidence:

- docs/interior-pipeline-assessment.md:27-33 says production reads MODEL_CONFIG.interior_reference_path.
- Current production.py evidence does not match that; active interior generation now routes through build_model_interiors(MODEL_CONFIG) at production.py:394, and the active interiors.py builder uses workbook model_interior_scope.
- docs/interior-pipeline-assessment.md:55-58 says model_interior_scope has no Stingray rows; current workbook has 130 active Stingray rows.
- docs/cleanup-risk-remaining.md is untracked and appears to be a saved copy of the prior risk ranking. I did not modify it.

Assessment:

- These docs are not runtime risks, but they are agent-steering risks. They can cause future specs to target already-retired CSV behavior.
- Fix after, or as part of, the interior stale-surface retirement pass.

Recommended next pass:

- Docs refresh only after confirming whether you want the CSV/config field removed. Otherwise update docs to distinguish “config field/file remnants still exist” from “active generator still consumes CSV.”

Recommended implementation order

1. Runtime hardcoded RPO exception spec
   - Smallest architecture-risk reducer.
   - Targets one clear runtime product hardcode.
   - Likely files: form-app/app.js, runtime tests.
   - No workbook write unless evidence shows missing workbook metadata.

2. Interior stale-surface retirement spec
   - Removes likely-dead config/file remnants.
   - Good portability cleanup.
   - Needs generated contract parity.

3. Editor optional-audit gate split
   - Aligns workbook editor handoff commands with AGENTS/README default readiness.
   - Keeps audit tooling opt-in.

4. Rule replace/body-scope row-level classification report
   - Bigger analysis pass.
   - Should precede any attempt to retire runtime_action or body_style_scope.

What changed:

- Nothing.

What did not change:

- No workbook sheets.
- No generated form\_\* sheets.
- No form-output.
- No form-app/data.js.
- No runtime behavior.
- No docs.

Gate results:

- validate_workbook_schema.py: passed, 0 issues.
- No generators run; report-only audit avoided artifact churn.
- No Node tests run; no implementation changed.

Manual verification pending:

- Before deleting interior_reference_path/CSVs, run a full contract parity pass.
- Before removing the GBA/opt_zyc_001 runtime hardcode, add/confirm focused runtime coverage for GBA/ZYC/CFL behavior.
- Before changing editor gate reminders, confirm whether the workbook editor UI treats GATE_COMMANDS as required gates or user-facing reminders.
