# Spec 06: Runtime-Used Provenance Field Classification

## Diagnosis

Root cause: Grand Sport draft JSON includes extra source/provenance fields not present in Stingray runtime JSON. Sean approved preserving fields used in runtime, but risk is uncertain. Need classify fields before promoting or dropping them.

Evidence:
- Stingray choices do not include source_option_name, source_description, text_cleanup_notes.
- Grand Sport draft choices include source_option_name, source_description, text_cleanup_notes.
- Grand Sport draft also includes draftMetadata.
- Both models otherwise have converging generated/runtime contracts.

Risk level: medium.
Change type: inspection first; possible generated contract cleanup later.

## Exact Files / Artifacts To Inspect

Artifacts:
- form-output/stingray-form-data.json
- form-output/inspection/grand-sport-form-data-draft.json
- form-output/inspection/grand-sport-contract-preview.json
- form-app/data.js

Runtime/code:
- form-app/*.js
- scripts/corvette_form_generator/inspection.py
- scripts/generate_grand_sport_form.py
- tests/grand-sport-draft-data.test.mjs
- tests/multi-model-runtime-switching.test.mjs
- tests/stingray-form-regression.test.mjs

Workbook source fields:
- grandSport_options.option_name
- grandSport_options.description
- grandSport_options.detail_raw
- stingray_options.option_name
- stingray_options.description
- stingray_options.detail_raw

## Constraints

- Preserve runtime-used fields.
- Keep draft-only/audit-only fields out of live runtime contract unless approved.
- No runtime behavior change unless field classification proves runtime dependency.
- No generated artifact hand edits.
- No NoSQL scope.

## Field Classification Targets

Grand Sport draft choice fields:
- source_option_name
- source_description
- text_cleanup_notes

Grand Sport draft top-level fields:
- draftMetadata
- ruleDetailHotSpots in preview/metadata
- normalization summaries

Classification categories:
- runtime-required
- generator-test-required
- audit/provenance-only
- migration-temporary
- remove-from-live-contract

## Implementation Outline

Phase 1 inspection:
1. Grep runtime for source_option_name, source_description, text_cleanup_notes, draftMetadata.
2. Grep tests for same fields.
3. Compare final form-app/data.js model entries for Stingray and Grand Sport.
4. Document exact consumers.
5. Recommend contract outcome.

Phase 2 conditional cleanup:
- If runtime-required: preserve field and add Stingray parity or documented model-specific exception.
- If audit-only: keep field in inspection artifacts, not live data.js.
- If test-only: move assertion to inspection/draft tests only.

## Validation Plan

Inspection-only:
```sh
rg -n "source_option_name|source_description|text_cleanup_notes|draftMetadata" form-app scripts tests form-output
```

If code/artifact generation changes:
```sh
.venv/bin/python scripts/generate_grand_sport_form.py
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
node --test tests/stingray-form-regression.test.mjs
```

Manual verification:
- Runtime still renders Grand Sport labels/descriptions correctly.
- Draft artifacts still preserve cleanup/provenance info if needed for audit.
- Live data.js does not grow audit-only contract fields without approval.

## Risks

- Removing draft fields could break migration/debug workflow.
- Promoting draft fields could make unstable cleanup metadata part of public runtime contract.
- Stingray/Grand Sport JSON parity may be desirable but not always required.

## Non-goals

- No workbook source schema edits.
- No text cleanup/business-label changes.
- No NoSQL/provenance collection design.
