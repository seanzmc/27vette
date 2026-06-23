# Pass D Spec - Required Gate Split

## Status

Completed, then superseded by retirement on 2026-06-22.

Pass D originally demoted the Grand Sport rule-audit helper and parser-loader tests from default readiness to optional audit/report status. A later approved retirement pass deleted the runnable tooling entirely:

- `scripts/build_rule_sources.py`
- `tests/grand-sport-rule-audit.test.mjs`
- `tests/audit-parser-metadata-loaders.test.mjs`

No proof exception was found that those files uniquely protected current generated runtime contracts, workbook schema/source contracts, model promotion, dealer payload behavior, or live runtime behavior.

## Current Contract

Do not use the retired rule-audit path as a validation gate. Grand Sport readiness now relies on current workflow gates:

- `scripts/generate_form.py --model grand_sport`
- `scripts/generate_registry.py` when promoted app data is refreshed
- `scripts/validate_workbook_schema.py stingray_master.xlsx` when workbook/source contracts are in scope
- `tests/grand-sport-contract-preview.test.mjs`
- `tests/grand-sport-draft-data.test.mjs`
- `tests/multi-model-runtime-switching.test.mjs` when registry or runtime switching can be affected

If rule provenance reporting is needed again, write a new approved report-only spec instead of restoring this retired path.

## Validation

For retirement cleanup, verify the runnable files are absent and current workflow docs do not list the retired commands as active gates.
