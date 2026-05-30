# Z Source Hygiene Audit Spec

## Diagnosis

Z06, ZR1, and ZR1X are staged in `stingray_master.xlsx`, but they are not runtime-ready. Early read-only inspection found that some Grand Sport mentions are harmless GM source text or review provenance, while other mentions appear in target Z source sheets and would be misleading if promoted to runtime without cleanup.

Current evidence inspected before this spec:

- Branch: `z06-zr1-migration`
- Runtime registry in `form-app/data.js` currently contains only `stingray` and `grandSport`; no Z model is promoted.
- Workbook validators pass:
  - `.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx`
  - `.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx`
- Relevant staging tests pass:
  - `.venv/bin/python -m pytest tests/test_future_model_source_review.py tests/test_future_model_source_population.py tests/test_future_model_option_review.py tests/test_future_model_option_population.py tests/test_future_model_compatibility_rebase.py tests/test_future_model_lz_interiors.py tests/test_future_model_option_pricing.py -q`
  - Result observed: `26 passed in 0.38s`
- Read-only workbook scan found Grand Sport mentions in:
  - raw/archive sheets: likely source text or historical evidence
  - `future_model_source_review` and `future_model_option_review`: likely internal provenance/copy mapping
  - target Z sheets such as `z06_rule_mapping`, `z06_exclusive_groups`, `zr1_exclusive_groups`, `zr1x_exclusive_groups`: likely cleanup candidates before runtime
  - target Z option sheets: a small number of customer-copy rows with GM multi-model accessory text

Root cause: the current Z strategy combines true raw order-guide parsing, Grand Sport compatibility rebasing, and internal review provenance. That is useful for staging but creates mixed-quality source text. Before runtime work, each Grand Sport mention needs to be classified by where it appears and whether it is source evidence, internal provenance, runtime/customer-facing copy, or an invalid copied Grand Sport rule/note.

Risk level: low for the audit itself because it is read-only. Medium if later cleanup rewrites workbook source rows, because rule text and notes may encode real compatibility decisions.

Change type for this pass: report-only / read-only audit. No workbook, generator, runtime, test, or artifact edits.

## Exact Scope To Inspect

Workbook: `stingray_master.xlsx`, read-only with `.venv/bin/python` and `openpyxl`.

Inspect only these sheets for classification:

- `z06_options`
- `zr1_options`
- `zr1x_options`
- `z06_rule_mapping`
- `zr1_rule_mapping`
- `zr1x_rule_mapping`
- `z06_exclusive_groups`
- `zr1_exclusive_groups`
- `zr1x_exclusive_groups`
- `future_model_source_review`
- `future_model_option_review`

Also use these sheets only as reference context, not as cleanup targets in this pass:

- raw/source sheets such as `z06_*_raw` and `zr1_zr1x_*_raw`
- `grandSport_*` sheets, only to understand copied source/provenance where needed
- `section_master`, only to identify whether a referenced group/section is target-facing

## Classification Output Buckets

Each Grand Sport mention in the inspected target sheets will be classified into exactly one bucket:

1. `safe raw source mention`
   - GM/customer-facing raw accessory text legitimately names multiple models, including Grand Sport, while the row itself is valid for Z06/ZR1/ZR1X.
   - Example pattern: accessory descriptions like “Stingray, Grand Sport, ZR1 and ZR1X models.”
   - Likely action later: may leave as-is, or optionally normalize customer copy if user wants cleaner Z-only language.

2. `internal provenance only`
   - The mention is in review/provenance/copy-tracking fields, not target runtime copy.
   - Example pattern: `grand_sport:opt_...`, `grand_sport_rpo_unique`, `grand_sport_missing` in `future_model_source_review` or `future_model_option_review`.
   - Likely action later: keep until migration is complete; strip from live generated runtime data if any such fields could leak.

3. `must rewrite before runtime`
   - The mention is in a target Z sheet field that would be confusing or incorrect if generated into runtime/customer/dealer-facing data, but the underlying row/rule may still be valid.
   - Example pattern: Z exclusive-group notes saying “Grand Sport wheel center cap choices...”
   - Likely action later: rewrite notes/original detail to Z-specific or neutral language after confirming the rule/group itself is valid.

4. `must delete/deactivate`
   - The mention identifies a row/rule/group copied from Grand Sport that does not apply to the Z model, or references a Grand Sport-only product/rule that should not exist in the target Z source sheet.
   - Example pattern to evaluate: Z rule rows excluding `(Z15) Grand Sport Heritage Graphics` if Z15 is not a valid active Z target/condition.
   - Likely action later: deactivate/delete source row via workbook-safe script after product validation.

5. `needs human product decision`
   - The row might be valid, but automated classification cannot safely decide because the text references model-specific packages, graphics, aero, brakes, wheels, default-required groups, or unclear source provenance.
   - Likely action later: user/dealer/product review before rewrite, delete, or activation.

## Audit Method

1. Check git state and confirm this is report-only.
2. Verify no workbook lock file blocks read-only inspection if present; do not remove lock files.
3. Read `stingray_master.xlsx` with `openpyxl` read-only/data-only mode.
4. For each scoped sheet:
   - scan every string cell for case-insensitive `grand sport`, `grandsport`, or `grand_sport`
   - capture sheet, cell coordinate, header/column name, row number, row key fields, and text excerpt
   - identify whether the field is likely runtime/customer-facing, rule source text, workbook note, or review provenance
5. Classify each hit using the five buckets above.
6. Aggregate counts by sheet and by bucket.
7. Provide representative row-level examples with recommended next action.
8. Do not write files, do not run generators, and do not change workbook or app data.

## Constraints

- No workbook writes.
- No generated `form_*` sheet edits.
- No generated artifact rewrites.
- No `form-app/data.js` changes.
- No runtime promotion or model activation.
- No new dependencies.
- No refactor.
- Preserve current live Stingray and Grand Sport behavior.
- Preserve dealer submission endpoint, payload shape, and Turnstile behavior.
- Treat workbook source rows as source of truth; later cleanup should prefer workbook rows over Python/JavaScript hardcodes.

## Risks and Non-goals

Risks:

- Some Grand Sport text in option descriptions may be legitimate GM copy and should not be blindly removed.
- Some Grand Sport-derived rules may be structurally valid for Z models even if their notes are dirty.
- Some review provenance is intentionally internal and should not be treated as runtime contamination unless it leaks into generated app data.

Non-goals:

- Do not clean the rows in this pass.
- Do not decide Z product correctness for ambiguous graphics/aero/brake/wheel/package rules without human review.
- Do not activate Z models.
- Do not generate runtime artifacts for Z06/ZR1/ZR1X.
- Do not change tests or schema validators.

## Validation Plan

Because this is read-only/report-only:

Required checks already run or to rerun before final handoff:

```sh
git branch --show-current
git status --short --branch
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Audit execution will be a read-only Python inspection script run from the repo root with `.venv/bin/python`.

No generator/test gates are required for the report because no files should change. If any later cleanup is approved, that cleanup will need a separate spec with workbook-safe writes, on-disk verification, regeneration scope, and targeted tests.

## Handoff Format

Final audit handoff will include:

- Overall readiness verdict for Grand Sport contamination only.
- Count table by sheet and bucket.
- Row-level findings with:
  - bucket
  - sheet/cell
  - row key fields (`option_id`, `rule_id`, `group_id`, etc.)
  - text excerpt
  - reason
  - recommended next action
- Separate list of suspected cleanup passes:
  1. safe note rewrites
  2. customer-copy normalization candidates
  3. rows needing human product decision
  4. rows likely requiring delete/deactivate
- What changed / what did not change.
- Validation results.

## Approval Question

Approve this read-only Z source hygiene audit exactly as scoped above?
