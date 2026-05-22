# Workbook Schema Standardization Spec Index

Status: draft specs for approval
Scope: workbook schema standardization across Stingray and Grand Sport only
Out of scope: NoSQL migration, live app behavior changes unless explicitly called out in a later approved implementation spec
Source inputs:
- schema-plan/audit-report-only.md
- schema-plan/action-plan.md

## Overall Diagnosis

Current workbook source graph is mostly aligned at header level for primary model sheets, but still drifts in value shape, interior-source schema, rule lifecycle semantics, and generated/draft provenance surfaces.

Highest-risk drift:
1. Boolean-like cells stored as mixed strings and booleans.
2. Numeric-looking RPOs stored as Excel numbers.
3. LZ_Interiors not matching lt_interiors headers despite representing same interior-source concept.
4. Stingray generator reads LZ_Interiors even though Sean expects LZ interiors not to be Stingray-compatible.
5. category_master appears in active source graph references but no live sheet exists.
6. grandSport_rule_mapping uses semi-freeform generation_action values while auditability requires retained source rows plus explicit normalization status.
7. Grand Sport draft fields may or may not belong in final runtime contract.

## Approved Decisions Baked Into These Specs

- Keep model-specific source sheets.
- Keep grandSport_variant_overrides model-specific.
- Remove category_master from active source graph references.
- Continue lt_interiors/LZ_Interiors plus model_interior_scope as interior organization pattern.
- Normalize LZ_Interiors to same header shape as lt_interiors.
- Numeric-looking RPOs must be text strings.
- Boolean fields must be real booleans.
- Blank price means null/not-priced; zero means explicit zero-price.
- Ignore NoSQL plans.
- Keep omitted/grouped binary rule rows in source for auditability, using normalization_status/reason metadata.

## Spec Series

1. 01-boolean-rpo-price-normalization-spec.md
   - Normalize workbook primitive value shapes: booleans, RPO text, price blank/zero semantics.

2. 02-interior-source-schema-spec.md
   - Normalize LZ_Interiors headers to lt_interiors shape and preserve model_interior_scope as model ownership layer.

3. 03-stingray-lz-interiors-consumer-spec.md
   - Investigate and decide whether Stingray generation should read LZ_Interiors; implement only after evidence.

4. 04-model-specific-contracts-category-cleanup-spec.md
   - Document model-specific sheet contracts and remove category_master from active source graph references.

5. 05-rule-lifecycle-auditability-spec.md
   - Add controlled generation_action/lifecycle metadata while preserving grouped-rule audit rows.

6. 06-runtime-provenance-contract-spec.md
   - Classify Grand Sport draft/provenance fields and preserve only runtime-used fields in final runtime contract.

7. 07-validation-suite-spec.md
   - Add validation checks for drift once schema decisions above land.

## Recommended Implementation Order

1. 01 primitive values.
2. 02 LZ_Interiors schema.
3. 03 Stingray/LZ consumer decision.
4. 04 sheet contracts/category cleanup.
5. 05 rule lifecycle.
6. 06 runtime provenance.
7. 07 validation suite.

## Global Constraints

- Do not edit generated form_* sheets directly.
- Do not hand-edit form-output/* or form-app/data.js.
- Workbook is source of truth.
- Prefer workbook-owned normalization over Python/JavaScript special cases.
- No new dependencies.
- No runtime endpoint/payload/Turnstile changes.
- Preserve visual/runtime behavior unless individual spec explicitly approves behavior change.
- Use .venv/bin/python for workbook/generator commands.
- Close Excel before workbook writes; respect ~$stingray_master.xlsx lock.
- Save workbook only through project safe-save helper.
- Verify workbook on disk after write.

## Global Gates

Minimum gates after any workbook/source-schema change:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/generate_stingray_form.py
.venv/bin/python scripts/generate_grand_sport_form.py
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/grand-sport-rule-audit.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

If a spec is docs-only or inspection-only, report skipped gates with reason.
