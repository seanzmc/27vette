I split this into two approval-gated specs that can be worked in parallel by subagents, with one important constraint: dry-run/review work can run concurrently, but actual writes to stingray_master.xlsx must be serialized because both specs touch the same workbook and must use safe-save.

    Read-only checks performed:
    - Git status: clean
    - Excel lock file: absent
    - Workbook schema validation: valid, 0 issues
    - Workbook package validation: valid, 0 issues
    - No files changed

    Current confirmed workbook state:
    - LZ_Interiors: 132 non-empty rows
      - 1LZ: 4
      - 2LZ: 40
      - 3LZ: 73
      - 3LZ_R6X: 15
      - section_id: blank for all 132
    - model_interior_scope: 132 rows, all grand_sport; no z06, zr1, zr1x
    - interior_components: 395 rows
      - stingray: 197
      - grand_sport: 198
      - no z06, zr1, zr1x
    - Z option/OVS sheets are populated:
      - z06_options: 239; z06_ovs: 1434
      - zr1_options: 201; zr1_ovs: 804
      - zr1x_options: 202; zr1x_ovs: 808
    - Z rule/group/exclusive/price sheets exist but are empty.
    - Z model_workbook_sources rows point to the right sheets, including LZ_Interiors, but all remain inactive.
    - Z model_master and model_registry_promotion rows remain inactive/unpromoted.

    Recommended split:

    1. Spec A: Z compatibility rules/groups/exclusives
    2. Spec B: Z LZ interior runtime-readiness
    3. Later separate spec: generic Z draft generator / promotion

    Do not bundle generator generalization or runtime promotion into these two specs.

    ────────────────────────────────────────
    SPEC A — Z compatibility rules/groups/exclusives
    ────────────────────────────────────────

    Objective:
    Populate the Z06/ZR1/ZR1X workbook source sheets for compatibility rules, grouped rules, and exclusive groups by rebasing Grand Sport’s canonical compatibility data through each Z model’s option universe.

    Change type:
    - Workbook-source data + supporting scripts/tests.
    - No live runtime behavior change.
    - No promotion.
    - No form-app/data.js mutation.

    Diagnosis:
    - Z option/OVS source sheets now exist and are populated.
    - Z compatibility source sheets exist with Grand Sport-compatible headers but have 0 rows:
      - z06_rule_mapping
      - z06_rule_groups
      - z06_rule_group_members
      - z06_exclusive_groups
      - z06_exclusive_members
      - same for zr1 and zr1x
    - Grand Sport already owns the canonical compatibility behavior:
      - grandSport_rule_mapping: 321 rows
      - grandSport_rule_groups: 2 rows
      - grandSport_rule_group_members: 20 rows
      - grandSport_exclusive_groups: 10 rows
      - grandSport_exclusive_members: 27 rows
    - Grand Sport rule rows include 19 source_type=interior rows. Those should be deferred from this spec unless the interiors spec defines a safe LZ mapping first.

    Exact workbook sheets to change after approval:
    - z06_rule_mapping
    - z06_rule_groups
    - z06_rule_group_members
    - z06_exclusive_groups
    - z06_exclusive_members
    - zr1_rule_mapping
    - zr1_rule_groups
    - zr1_rule_group_members
    - zr1_exclusive_groups
    - zr1_exclusive_members
    - zr1x_rule_mapping
    - zr1x_rule_groups
    - zr1x_rule_group_members
    - zr1x_exclusive_groups
    - zr1x_exclusive_members

    Do not change in this spec:
    - z06_price_rules
    - zr1_price_rules
    - zr1x_price_rules
    - model_master
    - model_workbook_sources
    - model_registry_promotion
    - form_* generated sheets directly
    - form-app/data.js
    - Grand Sport source rows

    Exact code/test files to change after approval:
    - Add:
      - scripts/corvette_form_generator/future_model_compatibility.py
      - scripts/apply_future_model_compatibility_sources.py
      - tests/test_future_model_compatibility_rebase.py
    - Update:
      - tests/workbook-schema-standardization.test.mjs
        - It currently expects future rule/group/exclusive sheets to be header-only. That expectation must become: headers match canonical shape, populated rows are internally valid, and future models remain inactive/unpromoted.
    - Possibly update:
      - scripts/corvette_form_generator/schema_validation.py
        - Only if we want schema validation to explicitly validate inactive future compatibility sheets. Otherwise keep validation in the new compatibility test module.

    Proposed implementation approach:
    1. Build a read-only compatibility preview.
       - Source: Grand Sport rule/group/exclusive sheets.
       - Targets: z06, zr1, zr1x.
       - Resolve Grand Sport option IDs to target option IDs by unique active RPO match.
       - Do not assume option IDs are always identical, even though many currently are.
       - Report:
         - proposed row counts by target sheet
         - skipped/unresolved rows
         - unmapped RPOs
         - deferred source_type=interior rules
         - pruned groups/members
         - dropped replacement references
       - No workbook writes in this phase.

    2. Human review gate before write.
       - Review the preview report.
       - Confirm which mechanically mappable rows should be written.
       - Confirm all skipped rows are acceptable as explicit deferrals.

    3. Apply approved rows.
       - Write only approved/reviewed rows.
       - Use deterministic Z-prefixed IDs.
       - Preserve Grand Sport behavior fields where applicable:
         - rule_type
         - target_type
         - source_type
         - target_selection_mode
         - source_selection_mode
         - generation_action
         - runtime_action
         - disabled_reason
         - normalization_status
         - normalization_reason
       - Recompute source_section and target_section from target option rows.
       - Rebase replacement_group_id only if the replacement group is emitted.
       - Rebase replacement_rule_id only if the referenced target rule is emitted.
       - Exclude unresolved rows rather than silently writing broken references.

    4. Human review gate after write.
       - Review workbook diff and generated preview/verification summary.
       - Confirm future model metadata stayed inactive.

    Constraints:
    - Grand Sport compatibility is the canonical template.
    - Workbook rows own business rules.
    - No runtime JS special cases.
    - No model promotion.
    - No price-rule population in this spec.
    - No generated sheet hand edits.
    - No new dependencies.
    - Workbook writes must use save_workbook_safely().
    - Actual workbook writes must not run concurrently with the interiors spec write.

    Risks:
    - Same RPO does not guarantee identical applicability across Grand Sport and Z models; human review is required.
    - Some Grand Sport rules reference options not present on Z models.
    - source_type=interior rows depend on the interiors spec.
    - Required exclusive groups can break runtime expectations if a target model has no valid member/default.
    - Existing tests currently assert the Z compatibility sheets are empty.

    Validation plan:
    Pre-write:
    - Dry-run preview exits 0.
    - Preview report reviewed by human.
    - No unresolved rows silently written.
    - Explicit approval to write workbook.

    Post-write:
    - .venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
    - .venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
    - .venv/bin/python -m pytest tests/test_future_model_compatibility_rebase.py
    - node --test tests/workbook-schema-standardization.test.mjs
    - node --test tests/grand-sport-rule-audit.test.mjs
    - node --test tests/grand-sport-draft-data.test.mjs
    - node --test tests/multi-model-runtime-switching.test.mjs
    - Open workbook read-only with openpyxl and verify:
      - target headers match canonical headers
      - all option references exist in the target model option sheet
      - no duplicate active IDs
      - future model metadata remains inactive/unpromoted

    Concurrency:
    - Can run in parallel with Spec B during dry-run/review/script/test development.
    - Workbook write must be serialized.

    ────────────────────────────────────────
    SPEC B — Z LZ interior runtime-readiness
    ────────────────────────────────────────

    Objective:
    Make LZ_Interiors runtime-ready for Z06/ZR1/ZR1X by filling reviewed section IDs and adding model-specific model_interior_scope and interior_components rows.

    Change type:
    - Workbook-source data + supporting validation/tests.
    - No live runtime behavior change.
    - No promotion.

    Diagnosis:
    - Z metadata already points interior_source_sheet to LZ_Interiors, but those metadata rows are inactive.
    - LZ_Interiors exists and matches lt_interiors headers.
    - LZ_Interiors has 132 rows, but every section_id is blank.
    - Current generic draft path uses:
      - scripts/corvette_form_generator/inspection.py::build_model_interiors
      - scripts/corvette_form_generator/runtime_metadata.py::load_model_interior_scope_map
      - scripts/corvette_form_generator/runtime_metadata.py::load_interior_components
    - Once model_interior_scope rows exist for a model, component-bearing interiors require matching workbook-owned interior_components rows or generation fails.
    - Therefore Z interiors need both scope rows and model-specific component rows before promotion.

    Exact workbook sheets to change after approval:
    - LZ_Interiors
      - Fill section_id for all 132 non-empty rows.
    - model_interior_scope
      - Add Z model rows.
    - interior_components
      - Add Z model-specific component rows.

    Possible workbook sheets to inspect only:
    - lt_interiors
    - PriceRef
    - section_master
    - model_variants
    - model_workbook_sources
    - model_master
    - model_registry_promotion

    Do not change in this spec:
    - model_master.active
    - model_workbook_sources.active
    - model_registry_promotion
    - form_* generated sheets directly
    - form-app/data.js
    - Z rules/groups/exclusives
    - Stingray runtime behavior

    Exact code/test files to change after approval:
    - Add one focused preview/apply helper, recommended:
      - scripts/corvette_form_generator/future_model_lz_interiors.py
      - scripts/apply_future_model_lz_interiors.py
    - Add:
      - tests/test_future_model_lz_interiors.py
    - Possibly update:
      - scripts/corvette_form_generator/schema_validation.py
        - Add referential/trim-scope checks for future-model LZ interior readiness.
      - tests/test_schema_validation_metadata.py
        - Add coverage for Z LZ scope/component validation.

    Proposed section_id policy:
    Mirror the existing lt_interiors section mapping unless you want new LZ-specific section IDs.

    Current lt_interiors section usage:
    - 1LT rows → sec_intc_001
    - 2LT rows → sec_intc_002
    - 3LT / 3LT_R6X rows → sec_intc_003

    Proposed LZ_Interiors mapping:
    - 1LZ → sec_intc_001
    - 2LZ → sec_intc_002
    - 3LZ → sec_intc_003
    - 3LZ_R6X → sec_intc_003

    Review note:
    - This is structurally clean, but check whether those section labels are customer-facing as 1LT/2LT/3LT Interior. If they are, we should either add model-scoped presentation metadata or create LZ-specific section IDs in a later/expanded spec.

    Proposed model_interior_scope rows:
    - z06
      - Include all LZ_Interiors rows:
        - 1LZ
        - 2LZ
        - 3LZ
        - 3LZ_R6X
      - Expected rows: 132
    - zr1
      - Include:
        - 1LZ
        - 3LZ
        - 3LZ_R6X
      - Exclude:
        - 2LZ
      - Expected rows: 92
    - zr1x
      - Same as zr1
      - Expected rows: 92

    Proposed trim_level values:
    - 1LZ rows → 1LZ
    - 2LZ rows → 2LZ
    - 3LZ rows → 3LZ
    - 3LZ_R6X rows → 3LZ

    Proposed interior_components rows:
    - Generate model-specific rows from the same component semantics currently used by Grand Sport/Stingray, but sourced/frozen into workbook rows.
    - Expected additions:
      - z06: 198 rows
      - zr1: 128 rows
      - zr1x: 128 rows
      - Total new Z component rows: 454
    - Component types expected:
      - seat
      - r6x
      - stitching
      - suede
      - two_tone
    - Rows must be keyed by model_key; do not rely on shared/global component rows.

    Proposed implementation approach:
    1. Build a read-only LZ interior preview.
       - Report proposed section_id fills.
       - Report proposed scope rows/counts by model and trim.
       - Report proposed component rows/counts by model, trim, component type.
       - Report any missing PriceRef references.
       - No workbook writes.

    2. Human review gate before write.
       - Confirm section ID policy.
       - Confirm 3LZ_R6X should scope as trim_level=3LZ.
       - Confirm ZR1/ZR1X exclusion of 2LZ.
       - Confirm component rows can be generated from existing legacy component semantics and then workbook-owned.

    3. Apply approved workbook rows.
       - Use save_workbook_safely().
       - Verify workbook on disk after save.
       - Do not activate model metadata or promotion rows.

    4. Human review gate after write.
       - Review workbook diff and verification report.
       - Confirm expected row counts and exclusions.

    Constraints:
    - Workbook owns interior source facts.
    - No runtime special cases.
    - No generated sheet hand edits.
    - No promotion.
    - No new dependencies.
    - No changes to live dealer submission behavior.
    - Workbook writes must be serialized with Spec A.

    Risks:
    - Reusing sec_intc_* may leak LT-facing labels unless presentation metadata is already generic enough.
    - Adding scope rows without component rows will make future draft generation fail for component-bearing interiors.
    - LZ_Interiors has formatting/trailing rows beyond the 132 non-empty rows; scripts must count actual non-empty records, not worksheet max_row.
    - ZR1/ZR1X must be explicitly tested to exclude all 2LZ interiors.

    Validation plan:
    Pre-write:
    - Dry-run preview exits 0.
    - Human approves:
      - section ID policy
      - trim scoping
      - component row generation

    Post-write:
    - .venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
    - .venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
    - .venv/bin/python -m pytest tests/test_future_model_lz_interiors.py
    - node --test tests/workbook-schema-standardization.test.mjs
    - node --test tests/grand-sport-draft-data.test.mjs
    - node --test tests/multi-model-runtime-switching.test.mjs
    - Open workbook read-only with openpyxl and verify:
      - LZ_Interiors.section_id nonblank for all 132 non-empty rows
      - z06 scope rows = 132
      - zr1 scope rows = 92
      - zr1x scope rows = 92
      - zr1/zr1x have zero 2LZ scope rows
      - z06 component rows = 198
      - zr1 component rows = 128
      - zr1x component rows = 128
      - no duplicate active (model_key, interior_id, rpo, component_type)
      - no component row references an unscoped interior for that model
      - future model metadata remains inactive/unpromoted

    Concurrency:
    - Can run in parallel with Spec A during dry-run/review/script/test development.
    - Workbook write must be serialized.

    ────────────────────────────────────────
    HOLD FOR LATER — generic generator/promotion
    ────────────────────────────────────────

    Do not include this in either concurrent spec.

    Reason:
    - Current generation seams are still Grand Sport-specific in places.
    - scripts/generate_grand_sport_form.py imports GRAND_SPORT_MODEL directly.
    - scripts/corvette_form_generator/model_configs.py defines Stingray/Grand Sport configs, but no Z model config factory yet.
    - inspection.write_inspection_artifacts() writes Grand Sport-named artifacts.
    - build_grand_sport_rule_sources.py is Grand Sport-specific.
    - Promotion substrate exists, but flipping future model_registry_promotion rows would affect live form-app/data.js.

    Later spec should cover:
    - scripts/generate_model_form.py --model-key <model_key>
    - wrapper compatibility for generate_grand_sport_form.py
    - generic model config creation from workbook metadata
    - Z draft artifact names
    - Z draft-data tests
    - one-model-at-a-time promotion: Z06, then ZR1, then ZR1X

    ────────────────────────────────────────
    Approval options
    ────────────────────────────────────────

    You can approve either or both:

    - “Approve Spec A dry-run only”
    - “Approve Spec B dry-run only”
    - “Approve both dry-runs concurrently”
    - “Revise the specs first: …”

    I would not approve workbook writes yet. The next safe step is concurrent dry-run/preview implementation for both specs, then human review of the proposed rows before either subagent writes stingray_master.xlsx.
