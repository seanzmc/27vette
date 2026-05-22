# Spec 03: Resolve Stingray Generator Use of LZ_Interiors

## Diagnosis

Root cause: Stingray generator currently reads LZ_Interiors and emits rows with active_for_stingray False. Sean flagged uncertainty because LZ interiors are not Stingray-compatible. Need evidence before changing behavior.

Evidence from audit/action plan:
- scripts/generate_stingray_form.py reads LZ_Interiors around rows 994-1019.
- Emitted LZ rows have active_for_stingray False.
- Grand Sport generation uses lt_interiors plus model_interior_scope/interior_components, not a direct grandSport_interiors sheet.

Risk level: high if behavior changes; medium if inspection-only.
Change type: inspection first; possible generator behavior-only cleanup after approval.

## Exact Files / Sheets To Inspect

Workbook:
- stingray_master.xlsx
  - LZ_Interiors
  - lt_interiors
  - model_interior_scope
  - form_interiors generated evidence only

Code:
- scripts/generate_stingray_form.py
- scripts/corvette_form_generator/inspection.py
- scripts/corvette_form_generator/model_configs.py
- form-app/data.js downstream evidence only

Artifacts/tests:
- form-output/stingray-form-data.json
- form-output/inspection/grand-sport-form-data-draft.json
- tests/stingray-form-regression.test.mjs
- tests/grand-sport-draft-data.test.mjs
- tests/multi-model-runtime-switching.test.mjs

## Constraints

- Do not remove LZ rows from generation until consumers are known.
- No workbook edits in inspection phase.
- No runtime behavior changes without separate approval.
- Preserve model_interior_scope approach.
- No NoSQL scope.

## Phase 1: Inspection Spec

Objective: classify Stingray LZ_Interiors consumption.

Steps:
1. Trace all generated Stingray interiors from LZ_Interiors.
2. Check whether inactive active_for_stingray False rows appear in final JSON interiors.
3. Check runtime filters for active_for_stingray or source_sheet.
4. Check tests that assume LZ rows exist or do not exist.
5. Compare form_interiors vs stingray-form-data.json interiors count.
6. Report one of:
   - harmless inactive reference/provenance;
   - legacy artifact not consumed;
   - wrong source inclusion affecting runtime;
   - needed shared-source bridge for future models.

Phase 1 validation:
- No files changed.
- Report exact consumers and row counts.

## Phase 2: Conditional Cleanup Spec

Only proceed if Phase 1 proves LZ rows are legacy/unconsumed or wrong.

Possible changes:
- Remove LZ_Interiors read/emission from scripts/generate_stingray_form.py; or
- Keep read but exclude from Stingray JSON/runtime export; or
- Move LZ output to inspection-only artifact.

Required approval question:
- Should LZ_Interiors remain in Stingray generated form_interiors as inactive reference rows, or be removed from Stingray generation entirely?

## Validation Plan If Cleanup Approved

```sh
.venv/bin/python scripts/generate_stingray_form.py
.venv/bin/python scripts/generate_grand_sport_form.py
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Manual verification:
- Stingray interior selector unchanged.
- Grand Sport draft interiors unchanged unless explicitly approved.
- No dealer submission payload change.

## Risks

- Removing inactive LZ rows could break generator stability tests or downstream assumptions.
- LZ rows might be used as Grand Sport/Z06/ZR1 future reference despite not being Stingray-compatible.
- Generated diff could be large if form_interiors changes.

## Non-goals

- No workbook schema normalization; Spec 02 owns that.
- No interior business-rule changes.
- No runtime refactor.
