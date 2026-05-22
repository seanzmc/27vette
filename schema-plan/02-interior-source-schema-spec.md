# Spec 02: Normalize LZ_Interiors to lt_interiors Source Schema

## Diagnosis

Root cause: lt_interiors and LZ_Interiors represent equivalent interior-source concepts but use different headers and different model-scope metadata. Sean approved keeping lt/LZ interiors with model_interior_scope, and approved normalizing LZ_Interiors to same headers as lt_interiors.

Evidence from audit:
- lt_interiors headers:
  - interior_id, Interior Name, Material, Price, Detail from Disclosure, Color Overrides, Trim, Seat, Interior Code, Suede, Stitch, Two Tone, section_id, active_for_stingray, requires_r6x, included_option_id
- LZ_Interiors headers:
  - Trim, Seat, Interior Code, Interior Name, Material, Suede, Stitch, Two Tone, Cost, Detail from Disclosure, Color Overrides, ID
- Differences:
  - ID vs interior_id.
  - Cost vs Price.
  - LZ_Interiors lacks section_id, active_for_stingray, requires_r6x, included_option_id.

Risk level: high.
Change type: workbook schema/data + generator compatibility; no intended runtime behavior change.

## Exact Files / Sheets To Inspect

Workbook:
- stingray_master.xlsx
  - lt_interiors
  - LZ_Interiors
  - model_interior_scope
  - interior_components
  - PriceRef
  - form_interiors as generated evidence only

Code/tests:
- scripts/generate_stingray_form.py lines around LZ_Interiors loading/emission
- scripts/corvette_form_generator/inspection.py build_grand_sport_interiors
- scripts/corvette_form_generator/runtime_metadata.py if metadata loaders reference interiors
- tests/stingray-form-regression.test.mjs
- tests/grand-sport-draft-data.test.mjs

## Constraints

- Workbook source remains source of truth.
- No direct edits to form_interiors or JSON artifacts.
- No change to model_interior_scope ownership pattern.
- LZ rows are not assumed Stingray-compatible.
- No model_key shared-sheet migration.
- No new dependencies.

## Proposed Canonical LZ_Interiors Header Order

Match lt_interiors:

1. interior_id
2. Interior Name
3. Material
4. Price
5. Detail from Disclosure
6. Color Overrides
7. Trim
8. Seat
9. Interior Code
10. Suede
11. Stitch
12. Two Tone
13. section_id
14. active_for_stingray
15. requires_r6x
16. included_option_id

Mapping:
- ID -> interior_id
- Cost -> Price
- Existing matching fields copied as-is.
- section_id default blank unless explicitly sourced from approved model scope.
- active_for_stingray default FALSE for LZ rows unless evidence proves Stingray compatibility.
- requires_r6x derived from Trim ending/containing _R6X where applicable, else FALSE.
- included_option_id blank unless explicit workbook rule requires it.

## Implementation Outline

1. Inspect LZ_Interiors row count and headers.
2. Inspect generator assumptions for LZ_Interiors.Cost and LZ_Interiors.ID.
3. Add transitional reader support if needed so generator can read new headers without runtime behavior drift.
4. Add workbook validation for LZ_Interiors header equality with lt_interiors.
5. Write safe workbook migration:
   - reorder/add headers.
   - rename ID to interior_id.
   - rename Cost to Price.
   - add missing columns.
   - set active_for_stingray FALSE for all LZ rows unless explicitly approved otherwise.
   - set requires_r6x from Trim/ID pattern if applicable.
6. Save through safe-save helper.
7. Re-read workbook from disk and verify headers/cells.
8. Regenerate artifacts and compare diffs.

## Validation Plan

Commands:
```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/generate_stingray_form.py
.venv/bin/python scripts/generate_grand_sport_form.py
node --test tests/stingray-form-regression.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Manual verification:
- LZ_Interiors header row exactly matches lt_interiors header row.
- LZ_Interiors former ID values now in interior_id.
- LZ_Interiors former Cost values now in Price.
- active_for_stingray values are booleans and default FALSE.
- Generated form_interiors still has expected LZ rows only where generator intentionally emits them.

## Risks

- Existing generator code may still reference Cost or ID.
- Reordering headers may affect scripts using positional access if any exist.
- active_for_stingray default FALSE could expose behavior if prior LZ output was accidentally consumed.

## Non-goals

- No decision yet to remove LZ_Interiors from Stingray generation; see Spec 03.
- No new unified interiors table.
- No NoSQL work.
- No product/business rule edits to interior availability.
