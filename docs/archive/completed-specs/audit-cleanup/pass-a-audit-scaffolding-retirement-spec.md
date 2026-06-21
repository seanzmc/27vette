# Pass A Spec — Audit Scaffolding Retirement

## Status

Proposed. Do not implement until explicitly approved after review.

## Diagnosis

The workbook and normal validation gates currently protect audit-only metadata that was created for an earlier Grand Sport/rule-source investigation. That makes workbook cleanup ineffective: removing obsolete audit sheets from `stingray_master.xlsx` breaks tests/schema checks because the repo treats historical audit scaffolding as part of the required workbook contract.

The immediate root cause is not the workbook rows themselves; it is that audit-only sheets are referenced by required scripts/tests/docs:

- `option_audit_groups`
- `option_audit_group_members`
- `rule_review_groups`

Current read-only evidence from the audit:

- These three sheets are present in `stingray_master.xlsx`.
- They have no Excel table objects.
- They have no workbook formula or defined-name references.
- They are not consumed by `form-app/app.js` or live generated runtime data directly.
- They are consumed by audit/inspection paths:
  - `scripts/corvette_form_generator/runtime_metadata.py`
    - `load_audit_group_members()` reads `option_audit_groups` and `option_audit_group_members`.
    - `load_rule_review_rpos()` reads `rule_review_groups`.
  - `scripts/build_rule_sources.py`
    - Uses `load_audit_group_members()` and `load_rule_review_rpos()` for rule-source/audit classification.
  - `scripts/corvette_form_generator/inspection.py`
    - Uses `load_rule_review_rpos()` for special-review RPO hot spots in inspection/preview reporting.
  - Tests currently assert these sheets/columns as required workbook contracts.

Risk level: Medium.

Change type: Mixed cleanup — workbook/data-only plus script/test/docs cleanup. Intended runtime behavior impact: none.

## Exact files and workbook sheets to change

### Workbook

Edit `stingray_master.xlsx` through the project safe-save path.

Remove these workbook sheets:

- `option_audit_groups`
- `option_audit_group_members`
- `rule_review_groups`

Do not edit generated `form_*` sheets directly.

### Scripts

Review and update/remove references in:

- `scripts/corvette_form_generator/runtime_metadata.py`
  - Remove or quarantine `load_audit_group_members()` if no retained script needs it.
  - Remove or narrow `load_rule_review_rpos()` so normal generation/inspection no longer requires `rule_review_groups`.
- `scripts/build_rule_sources.py`
  - If this script is retained, make historical audit grouping optional/fallback-code-only and not dependent on workbook audit sheets.
  - If this script is now historical one-off tooling, retire it or move it out of normal gates in a later pass; do not let it continue protecting workbook audit sheets.
- `scripts/corvette_form_generator/inspection.py`
  - Remove required `rule_review_groups` dependency from normal inspection/preview generation.
  - Preserve inspection output shape only where current tests or useful reports still require it; do not preserve obsolete special-review taxonomy just to keep row counts.

### Tests

Update tests that currently protect these sheets as required workbook contract:

- `tests/audit-parser-metadata-loaders.test.mjs`
  - Remove tests that require workbook-owned audit group/review-group loader behavior, or rewrite as legacy/fallback unit tests not tied to active workbook sheets.
- `tests/grand-sport-rule-audit.test.mjs`
  - Remove assertions requiring `option_audit_groups`, `option_audit_group_members`, or `rule_review_groups` rows.
  - Keep rule-audit assertions only if they protect live/current rule-source behavior.
- `tests/workbook-schema-standardization.test.mjs`
  - Remove boolean/type checks for retired sheets/columns.
- Any generated contract tests that indirectly assert special-review counts or hot-spot buckets should be updated to the new report-only contract.

### Docs/context

Update references so future agents do not resurrect these sheets:

- `AGENTS.md`
  - Remove the audit sheets from active workbook-owned runtime metadata lists.
  - If needed, mention that these audit sheets were retired as historical scaffolding.
- `README.md`
  - Remove them from active workbook source/runtime metadata lists.
- Any root workflow/spec docs found by search that call them active required sheets.

### Generated artifacts

Expected generated artifacts may change only if inspection/report outputs currently include audit hot-spot text/counts from `rule_review_groups`.

Do not hand-edit:

- `form-output/*`
- `form-app/data.js`
- generated workbook `form_*` sheets

Regenerate only through the approved generator commands if script/test changes require refreshed artifacts.

## Constraints

- Preserve customer-facing runtime behavior.
- Preserve dealer submission endpoint, payload shape, and Turnstile behavior.
- No runtime UI changes.
- No new dependencies.
- No broad generator refactor.
- No model/RPO-specific JavaScript exceptions.
- Do not solve workbook cleanup by hiding bad data in runtime code.
- Treat `stingray_master.xlsx` as source of truth and write it only through `save_workbook_safely()`.
- Stop if `~$stingray_master.xlsx` exists unless explicitly confirmed stale.
- Do not touch unrelated workbook sheets or current Z06/Grand Sport runtime-rule behavior.
- Do not delete current generators/promoters merely because they mention old audit concepts; first classify workflow entrypoint vs stale one-pass/audit tooling.

## Non-goals

This pass will not retire or redesign these sheets:

- `context_section_master`
- `section_presentation`
- `runtime_steps`
- `context_choice_copy`
- `order_summary_sections`
- `step_order_summary_map`
- `runtime_rule_exceptions`
- `variant_option_overrides`

Those sheets either feed generated contracts or currently affect runtime behavior. They need a separate runtime-metadata consolidation pass.

This pass will not normalize rule/exclusive/price behavior, Z06 package behavior, interiors, pricing, or model promotion.

## Implementation plan

1. Reference scan
   - Search for all references to the three target sheet names.
   - Classify each reference as live generation, inspection/report-only, test guard, docs, or stale historical context.

2. Gate decoupling first
   - Remove these sheets from required workbook-schema and metadata tests.
   - Update/retire audit loader tests so they no longer make the workbook sheets mandatory.
   - Update docs so these sheets are no longer listed as active runtime/workbook metadata.

3. Script cleanup
   - Remove direct dependency on these sheets from normal generation/inspection paths.
   - If audit scripts are retained, make the old grouping/review behavior optional and code-local, not workbook-contract-required.
   - Prefer deleting/quarantining stale one-pass/audit tooling over preserving executable historical scaffolding.

4. Workbook cleanup
   - Confirm Excel is closed/no workbook lock file exists.
   - Use a small safe-save script/helper to remove the three sheets from `stingray_master.xlsx`.
   - Reopen the saved workbook with `openpyxl` and verify the three sheets are absent.
   - Verify package integrity with the workbook package/schema validators.

5. Regenerate/review only as needed
   - If generator outputs changed only by timestamps or by intended removal of audit-report fields, call that out.
   - Restore unrelated generated churn before handoff if it is not part of this pass.

## Validation plan

Run after implementation:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
node --test tests/stingray-form-regression.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Run targeted tests affected by script/test cleanup. Expected list after edits, adjusted if references show a better target set:

```sh
node --test tests/audit-parser-metadata-loaders.test.mjs
node --test tests/grand-sport-rule-audit.test.mjs
node --test tests/workbook-schema-standardization.test.mjs
```

If `scripts/generate_form.py --model grand_sport` or `--model z06` still exercises inspection paths touched by this pass, also run:

```sh
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/z06-contract-preview.test.mjs
node --test tests/z06-form-data-draft.test.mjs
```

If Stingray generation is needed after workbook removal:

```sh
.venv/bin/python scripts/generate_form.py --model stingray
node --test tests/stingray-generator-stability.test.mjs
```

## Expected outcome

- The three audit-only sheets are gone from `stingray_master.xlsx`.
- Normal form/workbook validation no longer requires historical audit metadata.
- Runtime form behavior remains unchanged.
- Required gates protect the live form contract, not old one-off audit scaffolding.
- Any retained audit/report tooling is explicitly optional and does not force obsolete workbook sheets to exist.

## Risks

- `build_rule_sources.py` or related Grand Sport rule-audit tests may still be used for current diagnostics. If so, retire only the workbook-sheet dependency, not the entire script.
- Inspection markdown/JSON counts may change if special-review RPO rows are removed. This is acceptable only if those counts are historical audit decoration, not current runtime-readiness validation.
- Workbook safe-save may rewrite workbook internals; review diffs and generated artifacts carefully.
- If tests are overfitted to old sheet presence, they must be updated intentionally rather than worked around with empty replacement sheets.

## Approval question

Approve Pass A implementation exactly as scoped above?

Recommended approval wording: `Pass A approved`.

## Completion output — 2026-06-13T20:33:57Z

Status: Completed.

What changed:

- Removed the three audit-only workbook sheets from `stingray_master.xlsx` through `save_workbook_safely()`:
  - `option_audit_groups`
  - `option_audit_group_members`
  - `rule_review_groups`
- Removed the retired audit-sheet loaders from `scripts/corvette_form_generator/runtime_metadata.py`:
  - `load_audit_group_members()`
  - `load_rule_review_rpos()`
- Updated retained audit/inspection code to use code-local fallback sets instead of workbook audit sheets:
  - `scripts/build_rule_sources.py`
  - `scripts/corvette_form_generator/inspection.py`
- Updated tests so normal gates no longer require the retired workbook sheets:
  - `tests/audit-parser-metadata-loaders.test.mjs`
  - `tests/grand-sport-rule-audit.test.mjs`
  - `tests/workbook-schema-standardization.test.mjs`
- Updated active docs/sheet indexes so these sheets are not advertised as active workbook metadata:
  - `AGENTS.md`
  - `README.md`
  - `docs/workbook-sheet-index.md`

What did not change:

- No runtime JavaScript behavior was intentionally changed.
- No dealer submission endpoint, payload shape, or Turnstile behavior was changed.
- No new dependencies were added.
- No replacement/empty workbook sheets were added for the retired audit sheets.
- Generated `form-output/*` and `form-app/data.js` churn produced by validation generator runs was restored because it was unrelated to Pass A.

Workbook verification:

```text
{'backup': 'backups/stingray_master-20260613-163054.xlsx', 'remaining': []}
{'option_audit_groups': False, 'option_audit_group_members': False, 'rule_review_groups': False}
```

Reference cleanup verification:

```text
Retired loader refs in active scripts/tests: none
```

Validation run:

```sh
.venv/bin/python -m py_compile scripts/corvette_form_generator/runtime_metadata.py scripts/corvette_form_generator/inspection.py scripts/build_rule_sources.py
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/build_rule_sources.py --model grand_sport
```

Generator/validator results:

```text
validate_workbook_package.py: status=valid, issue_count=0
validate_workbook_schema.py: status=valid, issue_count=0, error_count=0, warning_count=0
generate_form.py --model grand_sport: inspection/draft/runtime-contract artifacts generated successfully; validation_warnings=1 existing model warning
generate_form.py --model z06: inspection/draft/runtime-contract artifacts generated successfully; validation_warnings=1 existing model warning
generate_form.py --model stingray: choices=1464, context_choices=8, standard_equipment=467, rules=150, price_rules=42, interiors=130, validation_errors=0
build_rule_sources.py --model grand_sport: rule_mapping_rows=323, copied_rule_candidates=91, raw_detail_rule_candidates=262, skipped_requires_review=4, unresolved_rpo_mentions=6
```

Node/Python gates run sequentially after final workbook cleanup:

```text
node --test tests/audit-parser-metadata-loaders.test.mjs: pass 3 / fail 0
node --test tests/stingray-form-regression.test.mjs: pass 82 / fail 0
node --test tests/stingray-generator-stability.test.mjs: pass 12 / fail 0
node --test tests/grand-sport-contract-preview.test.mjs: pass 9 / fail 0
node --test tests/grand-sport-draft-data.test.mjs: pass 19 / fail 0
node --test tests/grand-sport-rule-audit.test.mjs: pass 10 / fail 0
node --test tests/workbook-schema-standardization.test.mjs: pass 9 / fail 0
node --test tests/workbook-visual-copy-standardization.test.mjs: pass 4 / fail 0
node --test tests/z06-contract-preview.test.mjs: pass 3 / fail 0
node --test tests/z06-form-data-draft.test.mjs: pass 16 / fail 0
node --test tests/z06-runtime-promotion.test.mjs: pass 4 / fail 0
node --test tests/z06-interior-accessory-cleanup.test.mjs: pass 7 / fail 0
node --test tests/z06-performance-package-interactions.test.mjs: pass 17 / fail 0
node --test tests/z06-runtime-rule-corrections.test.mjs: pass 11 / fail 0
node --test tests/multi-model-runtime-switching.test.mjs: pass 40 / fail 0
.venv/bin/python -m pytest tests/test_model_config_metadata.py tests/test_registry_promotion_metadata.py tests/test_schema_validation_metadata.py -q: 26 passed
```

Diff review after restoring unrelated generated churn:

```text
AGENTS.md                                          |   3 -
README.md                                          |   3 -
docs/workbook-sheet-index.md                       |   3 -
scripts/build_rule_sources.py                      |  11 ++--
scripts/corvette_form_generator/inspection.py      |  13 ++++-
scripts/corvette_form_generator/runtime_metadata.py|  62 ---------------------
stingray_master.xlsx                               | Bin 711111 -> 708583 bytes
tests/audit-parser-metadata-loaders.test.mjs       |  60 --------------------
tests/grand-sport-rule-audit.test.mjs              |  36 ++++++------
tests/workbook-schema-standardization.test.mjs     |   3 -
```

Manual verification still pending:

- None required for live browser behavior from this pass; no runtime UI path was intentionally changed.
- If desired, the next review can open the workbook in Excel to confirm the three retired sheets are absent visually, but package/schema/openpyxl verification already passed.

Recommended next pass:

- Pass B: retire stale one-pass writer/apply/repair scripts now that the first audit-only workbook scaffold has been removed from normal gates. Keep that pass separate from runtime metadata consolidation.
