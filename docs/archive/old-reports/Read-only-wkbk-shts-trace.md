# Read-only trace of extraneous workbook sheets

**Short answer:**

- Do not retire these as one bundle. Most are used indirectly by generation and/or emitted into the runtime contract. The clean runtime-safe retirement candidates are only the audit/review trio, and even those are still used by rule-audit tooling/tests.

## Current workbook state:

- No workbook formulas or defined names reference any of these sheets.
- None of these sheets currently have Excel table objects.
- form-app/app.js never reads the workbook directly; it reads generated form-app/data.js.
- Current branch/status checked: generator-simplification-pass1, with unrelated untracked dist_updates/6.15.md.

## Classification:

### Sheet: option_audit_groups

Form generation / runtime use: Not used by live form runtime. Used by rule-source/audit tooling.
Current evidence: runtime_metadata.py:477 loads audit group members; scripts/build_rule_sources.py:960-963 uses it for engine-cover audit grouping. 1
active group row.
Retire call: Runtime-safe to retire, but not tooling-safe unless build_rule_sources.py, tests, and docs are updated.
────────────────────────────────────────

### Sheet: option_audit_group_members

Form generation / runtime use: Same as above. Not runtime.
Current evidence: 8 active engine-cover member rows; consumed with option_audit_groups.
Retire call: Same: good first cleanup candidate if we retire/update audit tooling.
────────────────────────────────────────

### Sheet: rule_review_groups

Form generation / runtime use: Not live runtime. Used by inspection/rule-audit/draft reporting.
Current evidence: runtime_metadata.py:515 loader; inspection.py:431 and inspection.py:659 use it for special review RPO hot spots; 4 active Grand Sport
rows.
Retire call: Runtime-safe to retire, but would alter inspection/rule-audit behavior and tests.
────────────────────────────────────────

### Sheet: context_section_master

Form generation / runtime use: Yes, generation input. Indirect runtime data via generated sections.
Current evidence: runtime_metadata.py:125; production.py:199-202; inspection.py:648-654. 4 active rows for Stingray/Grand Sport body/trim context
sections.
Retire call: Do not delete casually. Generator has config fallback, but deleting it moves ownership back to Python config and breaks workbook-ownership
tests.
────────────────────────────────────────

### Sheet: section_presentation

Form generation / runtime use: Yes, important generation input. Indirect runtime behavior.
Current evidence: runtime_metadata.py:158; production.py:203-209, 233-240, 257-285, 322; inspection.py:645-646, 807. Controls hidden sections, display
labels/order, step placement, standard-equipment bucket/group type. 33 active rows across Stingray/Grand Sport/Z06.
Retire call: Do not retire without replacing its responsibilities. This one is useful.
────────────────────────────────────────

### Sheet: runtime_steps

Form generation / runtime use: Yes, generation input. Runtime uses generated data.steps.
Current evidence: runtime_metadata.py:88; production.py:198, 288-293, 823-831; form-app/app.js:173, 472-473. 28 active Stingray/Grand Sport rows. Current
live contracts show 14 generated steps per promoted model.
Retire call: Do not retire as-is. There is fallback config, but deletion would undo workbook ownership and break tests.
────────────────────────────────────────

### Sheet: context_choice_copy

Form generation / runtime use: Yes, generation input. Runtime displays generated trim card tooltips.
Current evidence: contract.py:73-115, 131-183; production.py:189, 295-297. Current live data emits 6 Stingray tooltips and 6 Grand Sport tooltips; none
for Z06 because rows are for 1LT/2LT/3LT, not 1LZ/2LZ/3LZ.
Retire call: Keep if those trim tooltips matter. If you do not want tooltip copy in workbook/runtime, this could be retired with a visible UI copy
change.
────────────────────────────────────────

### Sheet: order_summary_sections

Form generation / runtime use: Yes, emitted for Stingray runtime only. Runtime consumes if present.
Current evidence: runtime_metadata.py:263-287; production.py:197, 841; form-app/app.js:1068-1079. 11 active Stingray rows; current
form-output/stingray-form-data.json has 11 order summary sections. Grand Sport/Z06 have 0 and use JS fallback.
Retire call: Low-value/partial sheet, but not unused. Removing would make Stingray fall back to app constants and likely change vehicle label from
workbook “Model” to fallback “Vehicle”. Candidate for either completion across models or deliberate retirement with runtime fallback normalization.
────────────────────────────────────────

### Sheet: step_order_summary_map

Form generation / runtime use: Same as above.
Current evidence: 13 active Stingray step-map rows; emitted as data.orderSummary.stepMap; runtime uses sectionKeyForStep().
Retire call: Same as order_summary_sections. Partial but real.
────────────────────────────────────────

### Sheet: runtime_rule_exceptions

Form generation / runtime use: Yes, emitted for Stingray runtime and consumed by JS.
Current evidence: runtime_metadata.py:245; production.py:196, 840; form-app/app.js:609-640. 4 active Stingray exception rows currently emitted.
Retire call: Do not delete until migrated into canonical workbook rules/groups. Deleting changes runtime behavior.
────────────────────────────────────────

### Sheet: variant_option_overrides

Form generation / runtime use: Yes, generation input. Affects generated choices.
Current evidence: runtime_metadata.py:194-238; production.py:210-216, 347-355; inspection.py:657, 704-797. 7 Stingray rows, including UQT variant
restrictions and display behavior overrides.
Retire call: Do not retire unless equivalent logic is represented in OVS/source rows or model-scoped override sheets. Active column semantics are special
here: it is an override value, not row activation.

## Current generated/runtime proof:

- form-app/data.js registry models: stingray, grandSport, z06.
- Stingray live data currently has:
  - steps: 14
  - contextChoices: 8
  - runtimeRuleExceptions: 4
  - orderSummary.sections: 11
  - orderSummary.stepMap: 13
  - trim tooltips present
- Grand Sport live data currently has:
  - steps: 14
  - trim tooltips present
  - no runtimeRuleExceptions
  - no generated orderSummary
- Z06 live data currently has:
  - steps: 14
  - no trim tooltips from context_choice_copy
  - no runtimeRuleExceptions
  - no generated orderSummary

## Recommendation:

A. First safe cleanup pass: retire or move option_audit_groups, option_audit_group_members, and maybe rule_review_groups from the runtime workbook contract, but only with corresponding updates to build_rule_sources.py, inspection/rule-audit tests, README/AGENTS wording, and schema tests. This should be runtime-safe.
B. Second pass: decide whether order_summary_sections + step_order_summary_map should be completed for Grand Sport/Z06 or intentionally removed in favor of app constants. They are partial and redundant-ish, but currently used for Stingray.
C. Do not retire section_presentation, runtime_steps, context_section_master, context_choice_copy, runtime_rule_exceptions, or variant_option_overrides until each responsibility is migrated or explicitly accepted as a behavior change.

What changed:

- Nothing. Read-only audit only.

Gates:

- Not run: no generator/test gate was needed because I made no edits.
- Read-only checks run:
  - git status --short --branch
  - openpyxl workbook inventory for the listed sheets
  - repo reference search
  - Node inspection of form-app/data.js and generated JSON contracts
  - openpyxl scan for formulas/defined names referencing these sheets

Manual verification still pending:

- If you want to actually retire any sheet, the next step should be a spec for that specific cleanup pass and then targeted gates after edits.
