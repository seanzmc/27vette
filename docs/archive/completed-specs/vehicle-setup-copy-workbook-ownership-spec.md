# Vehicle Setup Copy — Workbook Ownership Plan

Status: COMPLETE — implemented and verified 2026-07-22.
Date: 2026-07-22

## Diagnosis

At pass start, `form-app/app.js` owned model-specific Vehicle Setup presentation copy in `vehicleSetupHighlights` (`app.js:109-133`). That was the wrong ownership layer: the copy is model-level product metadata, while the browser should render generated registry metadata generically.

The existing `model_master` sheet is the correct source. It has one active row per model and already owns model identity and metadata. `variant_master` owns configuration facts, `model_variants` owns membership/order, and `model_registry_promotion` owns publication state; none should receive this copy.

Current workbook state matters:

- Six active `model_master` rows: Stingray, Grand Sport, Grand Sport X, Z06, ZR1, and ZR1X.
- Three currently promoted runtime models: Stingray, Grand Sport, and Z06.
- Grand Sport X, ZR1, and ZR1X are active model definitions but are not currently promoted.

This pass must not describe all six as currently published and must not alter promotion state.

Change type: workbook schema/data + generic registry emission + generic runtime consumption + generated registry + tests/docs.

Standing constraints from `AGENTS.md` apply, especially §§3-6 and §§10-12.

## Intended Outcome

1. `model_master` owns all model-specific Vehicle Setup card/highlight copy.
2. All six active model rows contain complete copy, preparing unpromoted models without promoting them.
3. Every promoted model must have complete copy or registry/schema validation fails closed.
4. `form-app/data.js` exposes that copy as `models[key].vehicleSetup` beside `data`.
5. `form-app/app.js` renders `models[key].vehicleSetup` and contains no model-specific Vehicle Setup copy map.
6. Existing `form-output/runtime/*-runtime-contract.json` files remain unchanged because this presentation metadata is registry-level, not ordering-contract data.
7. Pricing, options, selection behavior, model membership, runtime promotion, deployment, and dealer submission remain unchanged.

## Workbook Contract

Add these columns to `model_master`, before `notes`:

- `setup_card_subtitle`
- `setup_eyebrow`
- `setup_title`
- `setup_description`
- `setup_fact_1`
- `setup_fact_2`
- `setup_fact_3`

The seven separate columns are intentional. The runtime has distinct visual roles for card subtitle, eyebrow, title, description, and exactly three compact fact chips. A child sheet, JSON cell, or delimited fact field would add unnecessary parsing and editing complexity.

Populate all seven fields for all six active model rows. Do not rely on `setup_card_subtitle` falling back to `setup_eyebrow`; each visual role must be independently workbook-authored.

### Copy authority before implementation

- Migrate the current Stingray, Grand Sport, and Z06 strings from `vehicleSetupHighlights` verbatim unless the user supplies replacement copy.
- Grand Sport X, ZR1, and ZR1X require exact user-approved values for all seven fields before the live workbook write.
- Do not synthesize new-model marketing/product claims from sibling models, press material, or runtime fallbacks.

Copy approval receipt: before the workbook write, the user explicitly authorized drafting from repository product material and approved the displayed seven-field Grand Sport X, ZR1, and ZR1X copy exactly. The existing three promoted models were migrated without changing their established highlight copy; Stingray's independently required card subtitle uses its existing eyebrow copy.

## Validation Semantics

Extend `MODEL_MASTER_HEADERS` in `scripts/corvette_form_generator/schema_validation.py` with the seven columns in the same order as the workbook.

Extend `validate_registry_promotion_metadata()` at the existing `model_registry_promotion` → `model_master` join:

- Preserve the exact-header check.
- Cross-reference active, promoted rows from `model_registry_promotion`.
- Emit an error for each promoted model missing any of the seven setup-copy fields.
- Validate `setup_fact_1`, `setup_fact_2`, and `setup_fact_3` independently.
- Keep promotion as the hard runtime completeness boundary.

Because this pass intentionally populates all six active rows, add a live-workbook/source assertion covering all six expected model keys and nonblank fields. This protects the authored preparation rows from accidental clearing without changing publication authority.

## Registry Generator

In `scripts/corvette_form_generator/registry_promotion.py`:

1. Extend `RegistryPromotion` with the seven setup-copy values.
2. Populate them from the joined `model_master` row in `load_registry_promotions()`.
3. In `model_registry_entry()`, emit:

```text
models[key].vehicleSetup = {
  cardSubtitle,
  eyebrow,
  title,
  description,
  facts: [setup_fact_1, setup_fact_2, setup_fact_3]
}
```

Both `build_registry_from_promotions()` and `build_registry_from_artifacts()` already call `model_registry_entry()`, so this one emission point must cover both assembly paths. The nested object remains outside `models[key].data`.

The generator must not supply model-specific defaults. Missing promoted-model copy is a validation/generation error, not a reason to reconstruct product copy in Python.

## Browser Runtime

In `form-app/app.js`:

- Delete the model-specific `vehicleSetupHighlights` map.
- Make `activeModelHighlight()` read `registry.models[modelKey].vehicleSetup`.
- Preserve the current generic rendering and HTML escaping in `renderVehicleSetupHighlight()` and `renderModelChoice()`.
- Retain one generic compatibility fallback only for an old or externally malformed registry bundle.
- The fallback may use model label/name but must contain no model-specific product claims.
- Current generated `data.js` must never exercise that fallback for a promoted model; tests must prove this.

“Unpublished model fallback” is not a runtime case: unpromoted models are absent from the generated registry.

## Workbook Manager

Add the seven columns to the explicit `models` `TableSpec` in `workbook-manager/backend/app/specs.py` so import, editing, staging, comparison, and round-trip behavior preserve them.

This does not authorize live writes through Workbook Manager. Its current read-only provisional/write-containment behavior remains unchanged.

## Generated Artifact Boundary

Expected generated change:

- `form-app/data.js`: each promoted registry model gains `vehicleSetup`.

Expected unchanged artifacts:

- Every `form-output/runtime/*-runtime-contract.json` file.
- Other `form-output/*` model artifacts.

Do not run per-model generators for this metadata-only pass. `generate_registry.py` reads `model_master` plus the existing promoted runtime contracts and is the only required publication generator. Capture runtime-contract hashes before the workbook write and verify the same files and hashes afterward.

## Exact Files and Surfaces Expected to Change

- `stingray_master.xlsx` — `model_master` headers and six active rows only.
- `scripts/corvette_form_generator/schema_validation.py` — header and completeness guards.
- `scripts/corvette_form_generator/registry_promotion.py` — loader/dataclass and nested registry emission.
- `workbook-manager/backend/app/specs.py` — `models` column specification.
- `form-app/app.js` — generated metadata consumption; hardcoded map removal.
- `form-app/data.js` — regenerated registry artifact.
- `tests/test_schema_validation_metadata.py` — strict header and promoted-completeness RED/GREEN coverage.
- `tests/test_registry_promotion_metadata.py` — both registry assembly paths emit `vehicleSetup`; missing promoted copy fails.
- `tests/test_workbook_manager.py` — model-copy column import/round-trip preservation.
- `tests/stingray-form-regression.test.mjs` — remove source-string assertions; assert rendered generated copy and no hardcoded map.
- `tests/multi-model-runtime-switching.test.mjs` — cross-model generated-copy switching and no-fallback coverage.
- `README.md` — document `models[key].vehicleSetup` in the registry shape.
- `.hermes/plans/vehicle-setup-copy-workbook-ownership-spec.md` — close with actual implementation evidence before handoff.

Inspect and update only if their exact-header fixtures fail:

- Other tests constructing strict `model_master` fixtures.
- Workbook schema/standardization tests that encode the old header vector.

## Implementation Sequence

1. Confirm branch/status, Excel closed, and no `~$stingray_master.xlsx` lock.
2. Capture workbook mtime and hashes of every checked-in runtime-contract JSON.
3. Add RED tests for the new strict header, promoted completeness, registry shape, runtime consumption, and Workbook Manager preservation.
4. Update schema, registry, manager, and runtime code generically.
5. Apply the reviewed header/row changes through a scoped workbook-edit script using `save_workbook_safely()`; do not use Workbook Manager’s contained live-write route.
6. Verify backup creation, reopen the saved workbook, and assert exact headers and exact six-row values.
7. Run workbook package and schema gates.
8. Run `generate_registry.py`; review `form-app/data.js` for only the intended nested presentation metadata plus expected generation timestamps.
9. Recheck all runtime-contract hashes and confirm zero changes.
10. Run focused Python and Node gates.
11. Manually inspect the three currently promoted models in the checked registry at desktop/mobile widths. If a safe temporary six-model preview is used, it must not change `model_registry_promotion` or checked-in promotion state.
12. Close this plan with changed surfaces, gate output, preserved boundaries, residual risks, and next step per `AGENTS.md` §12.

## Validation Plan

Workbook safety and source contract:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Focused Python tests:

```sh
.venv/bin/python -m pytest \
  tests/test_schema_validation_metadata.py \
  tests/test_registry_promotion_metadata.py \
  tests/test_workbook_manager.py -q
```

Registry publication:

```sh
.venv/bin/python scripts/generate_registry.py
```

Focused runtime tests:

```sh
node --test \
  tests/stingray-form-regression.test.mjs \
  tests/multi-model-runtime-switching.test.mjs
```

Final checks:

- Runtime-contract file inventory and hashes exactly match the pre-change snapshot.
- `git diff --check` passes.
- Workbook diff is limited to seven added `model_master` columns and the six intended row values.
- `form-app/data.js` adds `vehicleSetup` only at registry model level; no `data` contract fields change.
- Source scan finds no `vehicleSetupHighlights` or migrated model-specific copy in `form-app/app.js`.
- Current promotion set remains exactly Stingray, Grand Sport, and Z06.

## Companion-File Impact

| Surface | Planned status |
|---|---|
| Workbook source | Update `model_master`; no other sheet changes. |
| Generated model/runtime contracts | Inspected-no-change; prove by file inventory and hashes. |
| Published registry | Regenerate `form-app/data.js`. |
| Runtime consumer | Update generic Vehicle Setup copy lookup only. |
| Workbook Manager | Update explicit model-table columns and preservation test. |
| Tests | Update schema, registry, manager, Stingray, and switching coverage. |
| README | Update registry shape. |
| Promotion/deployment | No change. |
| Dealer submission | No change. |
| Dependencies/public interfaces | No new dependency; additive registry metadata only. |

## Risks and Stop Conditions

- Stop before workbook write if Excel is open or a workbook lock is present.
- Stop if exact approved Grand Sport X/ZR1/ZR1X copy is unavailable.
- Stop if registry generation requires changing promotion rows.
- Stop if any runtime-contract hash changes.
- Stop if generated diffs alter pricing, rules, options, variants, selection metadata, or dealer-related data.
- Restore the safe-save backup if workbook package/schema validation fails and the correction is not mechanically within this approved schema/copy scope.

## Approval Boundary

Approval of this plan authorizes the ownership migration and the seven-column `model_master` schema described above. It does not authorize inventing copy, promoting Grand Sport X/ZR1/ZR1X, changing model behavior, deploying, or changing dealer submission.

That implementation prerequisite was satisfied before the workbook write: the exact seven-field Grand Sport X, ZR1, and ZR1X copy was approved, and the existing Stingray, Grand Sport, and Z06 copy was retained as specified.

## Completion Receipt — 2026-07-22

### Changed surfaces

- `stingray_master.xlsx`: added the seven approved `model_master` columns before `notes` and populated all six active model rows.
- `scripts/corvette_form_generator/schema_validation.py`: extended the strict header contract and added one error per missing promoted-model setup field.
- `scripts/corvette_form_generator/registry_promotion.py`: loaded, fail-closed validated, and emitted registry-level `vehicleSetup` metadata through the shared entry builder.
- `workbook-manager/backend/app/specs.py`: added all seven fields to the managed `models` table.
- `form-app/app.js`: removed `vehicleSetupHighlights`; the active model now supplies `vehicleSetup`, with only a generic compatibility fallback.
- `form-app/data.js`: regenerated the three-model promoted registry.
- Focused schema, registry, Workbook Manager, Stingray runtime, and multi-model tests were updated.
- `README.md`: documented the registry-level `vehicleSetup` object.

### Workbook safety and artifact evidence

- Excel lock preflight: no `~$stingray_master.xlsx` present.
- Safe write used `save_workbook_safely()` with loaded-mtime protection.
- Backup created and reopened: `backups/stingray_master-20260722-231308.xlsx`.
- A second pre-repair backup was created at `backups/stingray_master-20260722-233644-pre-package-repair.xlsx` before restoring the Office web-extension/shared-string package parts that `openpyxl` had dropped.
- The original `xl/webextensions/*` and `xl/sharedStrings.xml` parts, content-type declarations, and package relationships are preserved in the final workbook.
- Package validation: valid, zero issues.
- Schema validation after registry regeneration: valid, zero errors/warnings.
- On-disk readback confirmed the exact 17-column header, six populated active rows, and unchanged promoted set: Stingray, Grand Sport, Z06.
- Semantic comparison against the pre-write workbook found all 76 non-`model_master` sheets unchanged.
- All six runtime-contract files retained their exact pre-write SHA-256 hashes.
- Removing `vehicleSetup` from the regenerated registry yields an exact match to the prior registry; registry drift is limited to the intended nested metadata.

### Tests and manual verification

- Python metadata gate: 87 passed.
- Focused schema + registry suites: 46 passed.
- Workbook Manager setup-copy import, editor-op, and comparison-export round-trip tests: 3 passed.
- Stingray runtime regression: 90 passed.
- Multi-model runtime switching: 48 passed.
- Desktop browser verification: Stingray, Grand Sport, and Z06 each rendered their workbook-authored title and model switch correctly.
- Mobile browser verification: exact 390×844 CSS viewport, document `scrollWidth` 390, model progress/cards/subtitles/facts visible, and no overlap or horizontal overflow observed.
- `git diff --check`: passed.
- Independent review findings were corrected: active-only completeness gating, field-level malformed-registry fallback, all-six active-model copy coverage, Workbook Manager editor-op coverage, Office package-part preservation, and plan closure.
- Final independent re-review: no unresolved findings.

Known unrelated baseline failures were not changed or suppressed:

- `tests/test_workbook_manager.py::TestStagingWorkflow::test_scaffold_model_rejected` (the same failure was present during the pre-implementation RED run).
- `tests/workbook-schema-standardization.test.mjs` reports the pre-existing Grand Sport `5ZV`/`T0F` duplicate exclusion.
- The options-sheet quality gate reports the pre-existing `grand_sport_x_options:233` name-length issue.
- These surfaces are semantically unchanged outside `model_master`; none is caused by this pass.

### Preserved boundaries and residual risk

- No `model_registry_promotion` row changed; Grand Sport X, ZR1, and ZR1X remain unpromoted.
- No ordering-contract field, option, variant, rule, price, deployment path, dependency, dealer endpoint, payload, Turnstile behavior, or submission UX changed.
- No per-model generator ran and no model runtime contract changed.
- New-model copy is workbook-authored and prepared but will not appear in the checked runtime until those models are separately reviewed and promoted.
- Residual tooling risk: the final workbook preserves its Office web-extension package parts, but the generic `openpyxl` safe-save path does not preserve unsupported package parts automatically; that broader write-path hardening remains a separate follow-up before another workbook mutation relies on those parts.
