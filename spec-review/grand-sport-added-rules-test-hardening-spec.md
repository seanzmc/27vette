# Grand Sport Added Rules Test Hardening Spec

## Diagnosis

User added workbook rows to Grand Sport rule and price-rule sheets.

Current inspection results:

- `stingray_master.xlsx` package validation passes with `0` issues.
- No Excel lock file is present.
- `grandSport_price_rules` now has 34 emitted rows in the Grand Sport draft.
- `scripts/generate_grand_sport_form.py` succeeds.
- Grand Sport draft still reports only the expected draft/inactive warning.

Current failures:

- `tests/grand-sport-draft-data.test.mjs`
  - still asserts `draft.priceRules.length === 8`;
  - still asserts `draft.draftMetadata.priceRuleSourceRows === 8`.
- `tests/stingray-generator-stability.test.mjs`
  - still asserts `workbookRows("grandSport_price_rules").length === 8`;
  - `workbookRows()` includes blank Excel range rows, so `section_master` max row expansion to row 1000 causes an empty object to be treated as a real row and fail `step_key` validation.

Observed workbook shape:

- `section_master.max_row === 1000`, but rows 39-1000 are blank.
- `grandSport_options.max_row === 1000`, but the generator correctly reads 269 non-empty option rows.
- `grandSport_ovs` still has 1,614 status rows, matching 269 option rows x 6 variants.
- The generator source path already skips blank records via `rows_from_sheet()`, so the current blank row issue is a test helper issue, not a generator issue.

Risk level: low to medium. The code path is accepting the data; the risk is tests either becoming too brittle for normal workbook growth or too loose to catch broken required rules.

## Goal

Harden tests and generated local artifacts so additional workbook-authored Grand Sport rules and price rules are supported without changing runtime business logic.

## Constraints

- Do not add business logic to scripts.
- Do not mutate workbook data in this pass.
- Preserve Stingray production behavior.
- Keep Grand Sport draft-only and inactive.
- Do not freeze tests to a user-editable row count when the workbook is supposed to grow.
- Keep validation tied to required rule IDs, schema, and reference integrity.
- Use `.venv/bin/python` for project Python commands.

## Exact Files To Change

### Tests

- `tests/grand-sport-draft-data.test.mjs`
  - Replace exact `8` price-rule count assertions with:
    - `draft.priceRules.length >= 8`;
    - every required base package price rule is present;
    - every emitted price rule has required fields.
  - Keep explicit checks for the original FEY/PCQ/PEF price rules.
  - Update metadata assertion to compare `draft.draftMetadata.priceRuleSourceRows` to `draft.priceRules.length`, not a fixed value.

- `tests/stingray-generator-stability.test.mjs`
  - Update `workbookRows()` test helper to skip records where no header has a non-empty value.
  - Replace exact `grandSport_price_rules` row count of `8` with:
    - at least 8 rows;
    - required package rule IDs are present.
  - Keep exact header assertions for `price_rules` and `grandSport_price_rules`.

### Generated Artifacts

- `form-output/inspection/grand-sport-form-data-draft.json`
- `form-output/inspection/grand-sport-form-data-draft.md`
- `form-app/data.js`

Regenerate so local browser testing uses the current workbook-authored rules.

### No Code Changes Expected

No generator code changes are expected unless reference validation exposes a real script bug.

## Local Browser Test Setup

After tests pass:

1. Run `.venv/bin/python scripts/generate_grand_sport_form.py`.
2. Run `.venv/bin/python scripts/generate_stingray_form.py` to package the current Grand Sport draft into `form-app/data.js`.
3. Restore `form-output/stingray-form-data.json` if it only changed by `generated_at`.
4. Start a local static server from repo root:

   ```bash
   /Users/seandm/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m http.server 8080
   ```

5. Open:

   ```text
   http://127.0.0.1:8080/form-app/?model=grandSport
   ```

6. Verify in browser:
   - model is Grand Sport;
   - FEY package auto-adds included items with workbook price overrides;
   - at least one newly added workbook price rule is visible in behavior or exported data;
   - Stingray remains the default model when the `model=grandSport` query is not used.

## Validation Plan

Run:

```bash
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/generate_grand_sport_form.py
.venv/bin/python scripts/generate_stingray_form.py
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
node --test tests/stingray-form-regression.test.mjs
git diff --check
```

Manual browser verification remains pending after the server is started unless explicitly completed with Browser automation.

## Success Criteria

- Added workbook price-rule rows are accepted by scripts.
- Tests no longer fail just because valid workbook-authored price rules were added.
- Tests still prove the required package price rules exist.
- Blank Excel table/range rows do not fail workbook contract tests.
- `form-app/data.js` is packaged with the current Grand Sport draft.
- Local browser test URL is running and ready.
