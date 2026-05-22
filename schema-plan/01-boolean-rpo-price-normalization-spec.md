# Spec 01: Boolean, RPO, and Price Primitive Normalization

## Diagnosis

Root cause: equivalent Stingray/Grand Sport workbook columns use different primitive value shapes. Grand Sport especially stores boolean-like fields as strings. Both models have numeric-looking RPOs coerced by Excel to numbers. Price blanks and explicit zero prices must remain distinct.

Evidence from audit:
- grandSport_options.selectable: mixed strings/booleans: "TRUE", "FALSE", False, True.
- stingray_options.selectable: booleans.
- grandSport_rule_mapping.review_flag: string "False".
- grandSport_price_rules.review_flag: mixed string/bool.
- rule/exclusive group active fields often string "True"/"False".
- stingray_options.rpo numeric cells at rows including opt_719_001, opt_379_001, opt_719_002.
- grandSport_options.rpo numeric cells at rows including opt_719_001, opt_379_001, opt_719_002.
- *_options.price blanks are common and must not become zero.

Risk level: high.
Change type: workbook data + validation/test/generator-facing contract, no intended runtime behavior change.

## Exact Files / Sheets To Inspect

Workbook:
- stingray_master.xlsx
  - stingray_options.rpo, price, selectable, active
  - grandSport_options.rpo, price, selectable, active
  - rule_mapping.review_flag
  - grandSport_rule_mapping.review_flag
  - price_rules.review_flag, price_value
  - grandSport_price_rules.review_flag, price_value
  - rule_groups.active
  - rule_group_members.active
  - exclusive_groups.active
  - exclusive_group_members.active
  - grandSport_rule_groups.active
  - grandSport_rule_group_members.active
  - grandSport_exclusive_groups.active
  - grandSport_exclusive_members.active
  - grandSport_variant_overrides.active, selectable
  - PriceRef.Price
  - lt_interiors.Price
  - LZ_Interiors Cost/Price after Spec 02

Code/tests to inspect before edit:
- scripts/generate_stingray_form.py
- scripts/corvette_form_generator/inspection.py
- scripts/corvette_form_generator/workbook.py
- scripts/validate_workbook_package.py
- tests/stingray-generator-stability.test.mjs
- tests/grand-sport-draft-data.test.mjs
- tests/grand-sport-rule-audit.test.mjs

## Constraints

- No runtime behavior change intended.
- No generated file hand edits.
- No Python/JS special cases to hide bad workbook cells.
- No new dependencies.
- Workbook source data should own primitive values.
- RPOs become text strings in workbook cells, not just generator-normalized output.
- Booleans become real Excel booleans.
- Blank price remains blank/null; zero remains numeric 0.

## Proposed Workbook Rules

Boolean columns:
- Store real Excel booleans TRUE/FALSE.
- Do not store text "TRUE", "FALSE", "True", "False".

RPO columns:
- Store as text strings.
- Numeric-looking RPOs must be text: "719", "379".
- Preserve uppercase for alpha RPOs.

Price columns:
- Blank means null/not-priced.
- Numeric 0 means explicit zero-price.
- Numeric positive values remain numbers.
- No string "$0", "N/A", "-", "included" in price cells.

## Implementation Outline

1. Inspect workbook lock.
2. Add or update a workbook validation helper/test that reports:
   - string booleans in known boolean columns.
   - numeric cell types in known RPO columns.
   - invalid price strings in known price columns.
3. Run validation first and confirm it fails on known drift.
4. Write workbook cleanup script using openpyxl and save_workbook_safely().
5. Convert targeted boolean strings to bools.
6. Convert targeted numeric RPOs to text cells.
7. Leave blank prices blank; leave numeric zero as zero.
8. Re-read workbook from disk and assert corrected cell types/values.
9. Regenerate Stingray and Grand Sport artifacts.
10. Run targeted then full gates.

## Validation Plan

Pre-change:
- Validation/check should detect existing drift.

Post-change:
```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/generate_stingray_form.py
.venv/bin/python scripts/generate_grand_sport_form.py
node --test tests/stingray-generator-stability.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/grand-sport-rule-audit.test.mjs
node --test tests/stingray-form-regression.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Manual verification:
- Open/read workbook with openpyxl and verify representative cells:
  - stingray_options opt_719_001 rpo == "719"
  - grandSport_options opt_719_001 rpo == "719"
  - grandSport_options selectable values are booleans.
  - review_flag/active target columns are booleans.
  - blank prices remain blank.

## Risks

- Excel may re-coerce numeric-looking RPOs if cell style is not text.
- Existing generator code may compare active == "True" in some paths; converting to booleans may expose brittle comparisons.
- Safe implementation may need generator active/boolean readers to accept both old and new during transition, but not hide final workbook drift.

## Non-goals

- No NoSQL schema work.
- No option/rule business changes.
- No runtime behavior changes.
- No generated artifact hand edits.
