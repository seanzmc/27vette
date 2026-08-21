# Checkpoint 0 measured baseline — fast layered validation suite

Evidence file for `docs/archive/completed-specs/fast-layered-validation/2026-08-17-fast-layered-validation-suite.md` §9,
Checkpoint 0. Raw tool output, captured 2026-08-17. The durable, queryable form of
these numbers is `tests/validation_catalog.json`; this file is the transcript behind it.

```text
# Checkpoint 0 validation output — fast layered validation suite
# Captured 2026-08-17 on darwin 25.6.0 arm64; node v26.7.0; python 3.14.7 (.venv)
# Worktree: claude/fast-layered-validation-suite-4c31f6 at source commit 3a7fc52
# Method: one process per gate, run serially. Node gates must be serial —
#         the tracked-artifact boundary helper reads form-output/ and form-app/ whole.

## 1. Node gate baseline (all 16 tests/*.test.mjs, serial, wall time per file)

GATE tests/grand-sport-contract-preview.test.mjs exit=1 seconds=1.25 |  |  | 
--- failure detail for tests/grand-sport-contract-preview.test.mjs ---
  AssertionError [ERR_ASSERTION]: Expected values to be strictly equal:
    actual: 22,
    expected: 25,
--- end detail ---
GATE tests/grand-sport-runtime-contract.test.mjs exit=1 seconds=3.07 |  |  | 
--- failure detail for tests/grand-sport-runtime-contract.test.mjs ---
  AssertionError [ERR_ASSERTION]: Expected values to be strictly equal:
    actual: 281,
    expected: 263,
  AssertionError [ERR_ASSERTION]: Expected values to be strictly equal:
    actual: 'https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/brakes/e-g-j6f-o-cmp.webp',
    expected: 'https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/brakes/e-j6f.png',
--- end detail ---
GATE tests/multi-model-runtime-switching.test.mjs exit=0 seconds=4.26 |  |  | 
GATE tests/nonruntime-option-source-purge.test.mjs exit=0 seconds=1.56 |  |  | 
GATE tests/stingray-form-regression.test.mjs exit=1 seconds=2.54 |  |  | 
--- failure detail for tests/stingray-form-regression.test.mjs ---
  AssertionError [ERR_ASSERTION]: included 3A9 should block other seatbelt choices
    actual: true,
    expected: false,
--- end detail ---
GATE tests/stingray-runtime-contract.test.mjs exit=0 seconds=16.46 |  |  | 
GATE tests/tracked-artifacts-guard.test.mjs exit=0 seconds=1.06 |  |  | 
GATE tests/workbook-schema-standardization.test.mjs exit=0 seconds=64.97 |  |  | 
GATE tests/workbook-visual-copy-standardization.test.mjs exit=0 seconds=0.62 |  |  | 
GATE tests/z06-contract-preview.test.mjs exit=0 seconds=1.23 |  |  | 
GATE tests/z06-interior-accessory-cleanup.test.mjs exit=0 seconds=1.71 |  |  | 
GATE tests/z06-performance-package-interactions.test.mjs exit=0 seconds=6.41 |  |  | 
GATE tests/z06-published-runtime.test.mjs exit=0 seconds=0.3 |  |  | 
GATE tests/z06-registry-publication.test.mjs exit=1 seconds=1.21 |  |  | 
--- failure detail for tests/z06-registry-publication.test.mjs ---
  AssertionError [ERR_ASSERTION]: Expected values to be strictly deep-equal:
    actual: [ 'stingray', 'grandSport', 'grand_sport_x', 'z06', 'zr1', 'zr1x' ],
    expected: [ 'stingray', 'grandSport', 'z06' ],
--- end detail ---
GATE tests/z06-runtime-contract.test.mjs exit=1 seconds=1.19 |  |  | 
--- failure detail for tests/z06-runtime-contract.test.mjs ---
  AssertionError [ERR_ASSERTION]: 3LZ_AE4_H8T should allow the included color or Black
    actual: undefined,
    expected: true,
--- end detail ---
GATE tests/z06-runtime-rule-corrections.test.mjs exit=1 seconds=3.91 |  |  | 
--- failure detail for tests/z06-runtime-rule-corrections.test.mjs ---
  AssertionError [ERR_ASSERTION]: 3LZ_AE4_H8T should block other seatbelts
    actual: true,
    expected: false,
--- end detail ---

## 2. Node gate collected counts (tap reporter)

COUNT tests/grand-sport-contract-preview.test.mjs tests=5 pass=4 fail=1
COUNT tests/grand-sport-runtime-contract.test.mjs tests=18 pass=16 fail=2
COUNT tests/multi-model-runtime-switching.test.mjs tests=70 pass=70 fail=0
COUNT tests/nonruntime-option-source-purge.test.mjs tests=6 pass=6 fail=0
COUNT tests/stingray-form-regression.test.mjs tests=91 pass=90 fail=1
COUNT tests/stingray-runtime-contract.test.mjs tests=12 pass=12 fail=0
COUNT tests/tracked-artifacts-guard.test.mjs tests=7 pass=7 fail=0
COUNT tests/workbook-schema-standardization.test.mjs tests=13 pass=13 fail=0
COUNT tests/workbook-visual-copy-standardization.test.mjs tests=8 pass=8 fail=0
COUNT tests/z06-contract-preview.test.mjs tests=2 pass=2 fail=0
COUNT tests/z06-interior-accessory-cleanup.test.mjs tests=7 pass=7 fail=0
COUNT tests/z06-performance-package-interactions.test.mjs tests=21 pass=21 fail=0
COUNT tests/z06-published-runtime.test.mjs tests=4 pass=4 fail=0
COUNT tests/z06-registry-publication.test.mjs tests=2 pass=1 fail=1
COUNT tests/z06-runtime-contract.test.mjs tests=24 pass=23 fail=1
COUNT tests/z06-runtime-rule-corrections.test.mjs tests=15 pass=14 fail=1
COUNT_DONE

## 3. Python per-file baseline (one process per file, serial)

PYFILE tests/test_all_model_runtime_generation.py exit=0 seconds=6.7 | 30 passed in 6.47s
PYFILE tests/test_asset_map_sync.py exit=0 seconds=1.15 | 50 passed in 0.91s
PYFILE tests/test_atomic_registry_write.py exit=0 seconds=0.23 | 9 passed in 0.02s
PYFILE tests/test_corvette_form_generator_contract.py exit=0 seconds=0.3 | 10 passed in 0.08s
PYFILE tests/test_editor_lints.py exit=0 seconds=1.4 | 27 passed in 1.11s
PYFILE tests/test_editor_ops_apply.py exit=0 seconds=147.75 | 63 passed, 13 subtests passed in 147.43s (0:02:27)
PYFILE tests/test_editor_ops_global_families.py exit=0 seconds=4.42 | 16 passed in 4.16s
PYFILE tests/test_editor_ops_meta.py exit=0 seconds=0.34 | 9 passed in 0.09s
PYFILE tests/test_editor_server_payload.py exit=0 seconds=2.23 | 21 passed in 1.89s
PYFILE tests/test_editor_server_write_api.py exit=0 seconds=220.06 | 4 passed in 219.67s (0:03:39)
PYFILE tests/test_fable5_loop_contract.py exit=0 seconds=1.23 | 14 passed in 1.02s
PYFILE tests/test_generate_form_model_discovery_cli.py exit=0 seconds=1.75 | 3 passed in 1.53s
PYFILE tests/test_generation_safety.py exit=0 seconds=0.33 | 13 passed, 8 subtests passed in 0.09s
PYFILE tests/test_model_config_metadata.py exit=0 seconds=150.33 | 23 passed, 88 subtests passed in 150.08s (0:02:30)
PYFILE tests/test_model_generation_route.py exit=0 seconds=13.39 | 23 passed in 13.16s
PYFILE tests/test_options_sheet_quality.py exit=1 seconds=0.59 | 17 failed, 1 passed in 0.14s
--- failures ---
FAILED tests/test_options_sheet_quality.py::test_options_sheet_quality_module_exists
FAILED tests/test_options_sheet_quality.py::test_quality_lint_reports_reference_proven_predicates_on_inactive_sheet[overrides0-option_name_equals_description]
FAILED tests/test_options_sheet_quality.py::test_quality_lint_reports_reference_proven_predicates_on_inactive_sheet[overrides1-description_equals_detail_raw]
FAILED tests/test_options_sheet_quality.py::test_quality_lint_reports_reference_proven_predicates_on_inactive_sheet[overrides2-option_name_multiline]
FAILED tests/test_options_sheet_quality.py::test_quality_lint_reports_reference_proven_predicates_on_inactive_sheet[overrides3-bare_lpo_option_name]
FAILED tests/test_options_sheet_quality.py::test_quality_lint_reports_reference_proven_predicates_on_inactive_sheet[overrides4-hash_derived_option_id]
FAILED tests/test_options_sheet_quality.py::test_quality_lint_reports_reference_proven_predicates_on_inactive_sheet[overrides5-active_option_missing_display_order]
FAILED tests/test_options_sheet_quality.py::test_quality_lint_reports_reference_proven_predicates_on_inactive_sheet[overrides6-standard_option_nonzero_price]
FAILED tests/test_options_sheet_quality.py::test_quality_lint_reports_reference_proven_predicates_on_inactive_sheet[overrides7-selectable_section_standard_missing_zero_price]
FAILED tests/test_options_sheet_quality.py::test_quality_lint_reports_stub_count_above_reference_band
FAILED tests/test_options_sheet_quality.py::test_pure_quality_evaluator_grades_complete_projected_rows_without_workbook_io
FAILED tests/test_options_sheet_quality.py::test_display_only_included_row_may_use_explicit_zero_price
FAILED tests/test_options_sheet_quality.py::test_customer_facing_option_names_have_no_arbitrary_length_limit
FAILED tests/test_options_sheet_quality.py::test_pure_quality_evaluator_reports_each_active_section_order_collision
FAILED tests/test_options_sheet_quality.py::test_quality_allowlist_requires_exact_value_and_reason
FAILED tests/test_options_sheet_quality.py::test_quality_cli_returns_nonzero_and_machine_readable_findings
FAILED tests/test_options_sheet_quality.py::test_canonical_workbook_options_meet_customer_facing_quality_gate
--- end ---
PYFILE tests/test_promote_model.py exit=0 seconds=0.58 | 10 passed in 0.33s
PYFILE tests/test_registry_promotion_metadata.py exit=0 seconds=0.35 | 13 passed, 2 subtests passed in 0.11s
PYFILE tests/test_rule_derivation.py exit=2 seconds=0.29 | 1 error in 0.07s
--- failures ---
ERROR tests/test_rule_derivation.py
--- end ---
PYFILE tests/test_runtime_contract_builder.py exit=0 seconds=3.73 | 13 passed, 11 subtests passed in 3.49s
PYFILE tests/test_runtime_metadata_guards.py exit=1 seconds=0.39 | 1 failed, 10 passed in 0.17s
--- failures ---
FAILED tests/test_runtime_metadata_guards.py::RuntimeMetadataGuardTests::test_live_workbook_default_selection_display_behavior_rows_are_explicit
--- end ---
PYFILE tests/test_schema_validation_metadata.py exit=0 seconds=1.71 | 46 passed, 2 subtests passed in 1.47s
PYFILE tests/test_set_asset_display.py exit=0 seconds=0.36 | 3 passed in 0.13s
PYFILE tests/test_source_assembly_characterization.py exit=2 seconds=0.37 | 1 error in 0.13s
--- failures ---
ERROR tests/test_source_assembly_characterization.py
--- end ---
PYFILE tests/test_verify_workbook_candidate.py exit=1 seconds=694.43 | 2 failed, 14 passed in 694.20s (0:11:34)
--- failures ---
FAILED tests/test_verify_workbook_candidate.py::test_undeclared_semantic_drift_is_reported_and_fails
FAILED tests/test_verify_workbook_candidate.py::test_declaring_drift_moves_it_out_of_unexpected_and_passes
--- end ---
PYFILE tests/test_workbook_bool_hygiene.py exit=0 seconds=0.52 | 7 passed in 0.20s
PYFILE tests/test_workbook_changeset.py exit=0 seconds=0.35 | 33 passed in 0.10s
PYFILE tests/test_workbook_changeset_service.py exit=0 seconds=3.51 | 17 passed in 3.24s
PYFILE tests/test_workbook_domain_registry.py exit=0 seconds=0.35 | 9 passed in 0.10s
PYFILE tests/test_workbook_manager.py exit=0 seconds=810.34 | 63 passed, 2 skipped, 1 warning in 809.72s (0:13:29)
PYFILE tests/test_workbook_manager_api_concurrency.py exit=0 seconds=3.1 | 32 passed, 1 warning in 2.73s
PYFILE tests/test_workbook_manager_apply_rebuild.py exit=0 seconds=0.59 | 7 passed in 0.29s
PYFILE tests/test_workbook_manager_catalog.py exit=0 seconds=0.93 | 5 passed in 0.70s
PYFILE tests/test_workbook_manager_changeset_lifecycle.py exit=0 seconds=1.83 | 36 passed, 36 subtests passed in 1.55s
PYFILE tests/test_workbook_manager_drafts.py exit=0 seconds=0.4 | 6 passed in 0.17s
PYFILE tests/test_workbook_manager_generated_parity.py exit=0 seconds=82.22 | 4 passed in 81.95s (0:01:21)
PYFILE tests/test_workbook_manager_import_projection.py exit=0 seconds=222.91 | 21 passed in 222.63s (0:03:42)
PY_DONE

## 4. Python collection total

$ .venv/bin/python -m pytest tests/ -q --collect-only | tail -1
734 tests collected in 1.61s      # README stated 678

## 5. Import-order probe — the three files that fail when selected alone

$ .venv/bin/python -m pytest <file> -q            # no PYTHONPATH
tests/test_rule_derivation.py                 1 error in 0.07s
tests/test_source_assembly_characterization.py 1 error in 0.13s
tests/test_options_sheet_quality.py           17 failed, 1 passed in 0.14s

$ PYTHONPATH=scripts .venv/bin/python -m pytest <file> -q
tests/test_rule_derivation.py                 15 passed in 0.01s
tests/test_source_assembly_characterization.py 32 passed in 9.33s
tests/test_options_sheet_quality.py           18 passed in 0.27s
tests/test_runtime_metadata_guards.py          1 failed, 10 passed in 0.18s   # fails either way — real stale literal

## 6. Python metadata gate exactly as README publishes it (no PYTHONPATH)

189 passed, 111 subtests passed in 176.60s (0:02:56)
# Green. test_rule_derivation.py passes here but errors alone: a sibling
# inserts scripts/ into sys.path first. Import-order dependence confirmed.

## 7. Dead semantic-drift canary — decisive probe

$ .venv/bin/python -m pytest tests/test_verify_workbook_candidate.py -q -k drift
2 failed, 2 passed, 12 deselected in 201.30s
  test_undeclared_semantic_drift_is_reported_and_fails:
    assert drifting_undeclared['partition']['unexpected_drift'] == ['zr1']
    AssertionError: assert [] == ['zr1']
  test_declaring_drift_moves_it_out_of_unexpected_and_passes:
    assert ...['semantic_drift_vs_retained'] == ['choices', 'standardEquipment']
    AssertionError: assert [] == ['choices', 'standardEquipment']

$ probe form-output/runtime/zr1-runtime-contract.json for EFR
choices 800 []
standardEquipment 318 []

$ probe stingray_master.xlsx zr1_options for rpo=EFR
{'option_id': 'opt_efr_001', 'rpo': 'EFR', 'option_name': 'Carbon Flash Painted Accents',
 'active': True, 'selectable': False, 'section_id': 'sec_exte_001', 'display_order': 10}

# The fixture renames that row and the else-branch proves it was found, so the
# probe target is active in the workbook and absent from the generated contract.
# The mutation cannot drift anything: the semantic_drift stage has no live
# positive proof today.

## 8. Checkpoint 0 deliverable gates

$ .venv/bin/python -m pytest tests/test_validation_catalog.py -q
17 passed in 0.03s

$ git diff --check
(clean, exit 0)
```
