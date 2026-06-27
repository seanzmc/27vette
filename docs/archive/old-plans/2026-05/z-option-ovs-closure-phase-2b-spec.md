# Z Runtime Readiness Spec 2B — Option/OVS Decision Closure

## Diagnosis

Phase 2A proved the current Z06/ZR1/ZR1X normalized option and OVS sheets still contain unresolved staging rows. The corrected `scripts/apply_future_model_option_review.py` now emits only rows that are explicitly `review_status=approved`, `active=True`, and have a resolved section, but the workbook source data has not yet been reconciled to that contract.

Evidence inspected:

- Branch/status pre-check:
  - branch: `z06-zr1-migration`
  - Excel lock file `~$stingray_master.xlsx`: absent at spec time.
  - tracked work in progress from Phase 2A:
    - `.hermes/plans/z-option-ovs-closure-pass-spec.md`
    - `.hermes/plans/z-option-ovs-closure-phase-2a-report.json`
    - `.hermes/plans/z-option-ovs-closure-phase-2a-report.md`
    - `scripts/apply_future_model_option_review.py`
    - `tests/test_future_model_option_population.py`
- Phase 2A report:
  - `/Users/seandm/Projects/27vette/.hermes/plans/z-option-ovs-closure-phase-2a-report.md`
  - `/Users/seandm/Projects/27vette/.hermes/plans/z-option-ovs-closure-phase-2a-report.json`
- Workbook source sheet inspected read-only:
  - `future_model_option_review`
- Target normalized sheets referenced by the Phase 2A dry-run:
  - `z06_options`, `z06_ovs`
  - `zr1_options`, `zr1_ovs`
  - `zr1x_options`, `zr1x_ovs`

Current Phase 2A approved-active dry-run results:

| model | current options | approved-active emit | option delta | current OVS | approved-active OVS | OVS delta | would remove | would add | blocked counts |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Z06 | 239 | 164 | -75 | 1434 | 984 | -450 | 75 | 0 | deferred=57, inactive=170, needs_section_review=113 |
| ZR1 | 201 | 141 | -60 | 804 | 564 | -240 | 60 | 0 | deferred=60, inactive=164, needs_section_review=104 |
| ZR1X | 202 | 141 | -61 | 808 | 564 | -244 | 61 | 0 | deferred=60, inactive=164, needs_section_review=104 |

Rows currently present in target option sheets but not eligible under the approved-active contract:

- Z06: 75 rows, all `needs_section_review`, `active=False`, from `z06_intextmec_raw`.
- ZR1: 60 rows, all `needs_section_review`, `active=False`, from `zr1_zr1x_intextmec_raw`.
- ZR1X: 61 rows, all `needs_section_review`, `active=False`, from `zr1_zr1x_intextmec_raw`.

Important shape of the would-remove rows:

- Many are standard-equipment-like rows with no RPO:
  - Z06: 26 of 75 would-remove rows have no source/orderable/ref RPO.
  - ZR1: 25 of 60 would-remove rows have no source/orderable/ref RPO.
  - ZR1X: 25 of 61 would-remove rows have no source/orderable/ref RPO.
- The largest candidate sections among would-remove rows are mostly standard, wheel, interior, tech, customer/custom-stitch, stripe, suspension, aero/ground-effects, and performance package areas.
- This means the pass is not simply a deletion pass. Some rows may be valid standard equipment, interior/customer customization, or package/appearance choices that need explicit workbook decisions before rules/pricing/interiors build on them.

Root cause:

- Prior population logic allowed unresolved inactive rows into the normalized option/OVS target sheets because `suggested_section_id` alone was treated as enough to emit.
- Phase 2A fixed the script predicate, but `future_model_option_review` still contains unresolved rows whose intended runtime fate is not explicit.
- Building rules now would anchor future work to unstable option IDs, especially standard-equipment/no-RPO rows, customer stitch rows, suspension/package rows, aero/ground-effects rows, and Z-specific RPOs remembered as different from Grand Sport mappings.

Change type:

- Workbook/data-only decision closure, followed by dry-run validation.
- No runtime behavior change.
- No `form-app/data.js` regeneration.
- No live app/dealer submission change.

Risk level:

- Medium-high. The pass controls which Z option IDs survive into later rules, interiors, pricing, and runtime-readiness work. Over-pruning could lose valid Z content; over-approving could preserve staging contamination.

## Decision / Ownership

Business decisions belong in workbook source sheet `future_model_option_review`.

Phase 2B should make each unresolved would-remove row explicit by setting final decision fields on `future_model_option_review`, not by suppressing rows in Python or JavaScript.

Allowed row outcomes:

1. **Approve for normalized emission**
   - Use when the row should remain in `*_options`/`*_ovs` and is ready for downstream rules/pricing/interiors.
   - Required fields:
     - `review_status=approved`
     - `active=True`
     - `final_section_id` when the suggested section needs confirmation/override or to make the decision explicit.
     - `final_selectable` when the row is standard/reference/non-customer-selectable or when orderable-RPO inference is not enough.
     - `final_display_order` if the suggested order is missing or wrong.
     - `final_display_behavior` if the runtime card/display behavior must be explicit.
     - `notes` updated with decision/provenance where useful.

2. **Keep deferred/inactive intentionally**
   - Use when the row should not emit yet, but should remain in review queue.
   - Required fields:
     - `review_status=deferred` or retain non-approved status.
     - `active=False`
     - `notes` must explain why, for example: `deferred_phase_2b: needs product decision`, `deferred_phase_2b: exterior paint color pass`, `deferred_phase_2b: interior structure pass`, or `deferred_phase_2b: Z-specific rule/pricing evidence needed`.

3. **Reject/remove from normalized target universe**
   - Use when the row is staging residue, duplicate informational text, not a customer/build option, or should not become a source option row.
   - Required fields:
     - `review_status=deferred` or another existing non-approved status if no explicit rejected status exists.
     - `active=False`
     - `notes` must explain that it is intentionally excluded from normalized option emission.
   - Do not invent a new status unless the workbook/test contract is separately updated.

4. **Explicit provenance exception**
   - Use sparingly when a row is not a simple active approved GM row but must remain in normalized source sheets for a known reason.
   - Requires explicit notes and final fields; if the current script cannot represent this without weakening the approved-active contract, stop and write a separate spec rather than adding a loophole.

## Exact Files / Sheets to Change

Expected workbook source changes:

- `stingray_master.xlsx`
  - Sheet: `future_model_option_review`
  - Scope: only rows for `model_key` in `z06`, `zr1`, `zr1x` whose resolved option ID is in Phase 2A `would_remove_option_ids`, plus any directly related review rows needed to avoid duplicate/contradictory decisions.
  - Fields likely edited:
    - `review_status`
    - `active`
    - `final_section_id`
    - `final_selectable`
    - `final_display_order`
    - `final_display_behavior`
    - `notes`

Expected support artifacts:

- New decision worksheet/report artifact, before workbook write:
  - `.hermes/plans/z-option-ovs-closure-phase-2b-decision-matrix.csv`
  - Purpose: list each would-remove row with model, option ID, RPO, description, suggested/final section, current status, recommended action, rationale, and write target fields.
- Optional human-readable summary:
  - `.hermes/plans/z-option-ovs-closure-phase-2b-decision-matrix.md`

Expected tests/code:

- No script logic change expected if Phase 2A guard remains sufficient.
- Add or adjust tests only if Phase 2B reveals a representational gap, for example needing a formal non-emitting/rejected status or a provenance-exception mechanism.

Target sheets not written in Phase 2B unless explicitly approved:

- `z06_options`, `z06_ovs`
- `zr1_options`, `zr1_ovs`
- `zr1x_options`, `zr1x_ovs`

Generated/runtime artifacts not changed:

- Do not edit generated `form_*` workbook sheets.
- Do not regenerate or edit:
  - `form-output/stingray-form-data.json`
  - `form-output/stingray-form-data.csv`
  - `form-app/data.js`

## Proposed Implementation Steps

### Step 1 — Build the Phase 2B decision matrix, read-only

Create a report from `future_model_option_review` joined to the Phase 2A `would_remove_option_ids`.

For each row include:

- `model_key`
- resolved option ID: `final_option_id` then `suggested_option_id`
- `source_rpo`, `orderable_rpo`, `ref_only_rpo`
- `source_option_description`
- `raw_source_sheet`, `raw_source_span`
- `review_status`, `active`
- `suggested_section_id`, `final_section_id`
- `suggested_display_order`, `final_display_order`
- `final_selectable`, `final_display_behavior`
- `normalized_status_summary`
- existing `notes`
- current presence in `*_options` and `*_ovs`
- recommended action bucket
- proposed target fields
- rationale

Initial recommended action buckets:

- `approve_standard_nonselectable`
  - likely standard/no-RPO rows that should remain as standard equipment if useful to runtime summaries.
- `approve_customer_selectable`
  - clear customer/orderable RPO rows that need final section/selectable/display confirmation.
- `defer_exterior_paint_or_color`
  - color/paint rows not yet in the Z exterior paint pass.
- `defer_interior_structure`
  - interior rows that should wait for the interiors pass.
- `defer_rules_or_pricing_evidence`
  - package/performance/aero/suspension rows needing rule/pricing evidence.
- `exclude_informational_standard_duplicate`
  - rows that are standard-equipment disclosure/informational text and should not become selectable/source options.
- `needs_human_decision`
  - anything ambiguous.

Important memory/context constraint:

- Z models use different RPOs for engine covers, stripes, performance packages, and wheels. Do not mechanically copy Grand Sport decisions for those categories. Mechanically mapped compatibility rows can be treated as likely good only when current source evidence supports them, and later additions are expected when exterior paint colors and Z-specific RPO rules land.

### Step 2 — Review the matrix before write

Do not write the workbook until the matrix is reviewed.

At minimum, stop for user approval if any rows are proposed as `approve_*` from these higher-risk categories:

- engine covers / engine appearance
- stripes
- aero / ground effects
- performance packages such as Z07, ZTK, Z52-related rows
- wheels
- suspension rows such as FE6/FE7/FE8/FEJ/FEH/FEZ
- interior structure rows that may belong to the later interiors pass
- rows with Grand Sport-derived language or provenance ambiguity

Low-risk candidates for direct workbook decision may include no-RPO standard-equipment rows only if the desired runtime representation is clear. If not clear, defer with notes rather than approve by inference.

### Step 3 — Safe workbook write for approved matrix decisions

If the matrix is approved, write only the explicitly approved field changes into `future_model_option_review`.

Workbook safety requirements:

- Confirm Excel lock file is absent immediately before write:
  - `~$stingray_master.xlsx`
- Load workbook with `openpyxl` using project `.venv`.
- Save through `save_workbook_safely()`.
- Verify saved workbook on disk after write by reopening and checking exact edited cells.
- Do not edit target `*_options`/`*_ovs` in this step.

### Step 4 — Re-run Phase 2A dry-run against new review decisions

Run:

```sh
.venv/bin/python scripts/apply_future_model_option_review.py --dry-run --model-key all
```

Expected result after Phase 2B depends on approved decisions:

- Rows approved in `future_model_option_review` should move from `would_remove_option_ids` into approved-active emission.
- Rows intentionally deferred/excluded should remain blocked with explicit notes.
- `error_count` should remain `0`.
- No rows should be silently emitted unless approved-active.

### Step 5 — Stop before write-mode regeneration

Phase 2B should not run write-mode `apply_future_model_option_review.py` unless separately approved as Phase 2C.

The purpose of Phase 2B is to stabilize source review decisions. Phase 2C is the later normalized option/OVS regeneration pass.

## Constraints Repeated Back

- Spec-first: no Phase 2B workbook edits until this spec is approved.
- Workbook source of truth: product decisions belong in `future_model_option_review`, not in Python/JS hardcodes.
- Do not solve unresolved rows by weakening the Phase 2A approved-active predicate.
- Treat Grand Sport-derived rows as staging seeds, not runtime truth.
- Do not mechanically copy Grand Sport decisions for Z-specific engine covers, stripes, performance packages, wheels, suspension, or exterior-paint/color areas.
- Do not build rules on top of unstable option IDs.
- Do not promote Z06/ZR1/ZR1X to runtime in this pass.
- Do not alter live Stingray or Grand Sport behavior.
- Do not change dealer submission endpoint, payload shape, or Turnstile behavior.
- Do not edit generated `form_*` workbook sheets.
- Do not regenerate `form-app/data.js`.
- Use `.venv/bin/python` for Python commands.
- Use `save_workbook_safely()` for workbook writes.
- No new dependencies.
- No broad refactor.

## Non-goals

- Do not regenerate `z06_options`, `zr1_options`, `zr1x_options`, or OVS sheets in Phase 2B unless explicitly expanded.
- Do not complete rules, rule groups, exclusive groups, interiors, prices, colors, or runtime registry promotion.
- Do not resolve exterior paint colors in this pass unless the decision is already obvious and approved in the matrix.
- Do not add model/RPO-specific runtime or generator exceptions.
- Do not invent new review statuses without a separate schema/test update.
- Do not remove internal review provenance from review sheets.

## Risks

- Over-approval risk: approving rows just because they are present in current target sheets may preserve staging contamination.
- Over-pruning risk: deferring/removing valid standard-equipment or customer-selectable rows may make later runtime summaries incomplete.
- Z-specific rule risk: engine cover, stripe, performance package, wheel, suspension, and exterior color rows may look similar to Grand Sport rows but use different Z RPO logic.
- Standard-equipment representation risk: no-RPO standard rows may or may not belong in normalized option sheets depending on downstream summary/runtime expectations.
- Interior pass overlap: some rows may actually belong in the later interiors structure pass rather than option closure.
- Phase coupling risk: changing review decisions without regenerating target sheets leaves existing target sheets temporarily inconsistent, but that is acceptable until Phase 2C because Phase 2B is source-decision closure only.

## Validation Plan

Read-only decision matrix generation:

```sh
.venv/bin/python scripts/apply_future_model_option_review.py --dry-run --model-key all > .hermes/plans/z-option-ovs-closure-phase-2b-prewrite-dry-run.json
```

After any workbook write:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Verify exact `future_model_option_review` edits on disk with an `openpyxl` inspection script that reports:

- edited row count
- exact row numbers / option IDs changed
- old vs new values for edited fields
- no edits outside the approved matrix

Re-run dry-run after workbook write:

```sh
.venv/bin/python scripts/apply_future_model_option_review.py --dry-run --model-key all > .hermes/plans/z-option-ovs-closure-phase-2b-postwrite-dry-run.json
```

Targeted future-model staging gates:

```sh
.venv/bin/python -m pytest \
  tests/test_future_model_source_review.py \
  tests/test_future_model_source_population.py \
  tests/test_future_model_option_review.py \
  tests/test_future_model_option_population.py \
  tests/test_future_model_compatibility_rebase.py \
  tests/test_future_model_lz_interiors.py \
  tests/test_future_model_option_pricing.py \
  -q
```

No Node runtime tests are required unless this pass unexpectedly touches runtime/generated app data.

## Approval Gate

Approve Phase 2B to build the decision matrix first, then pause for review before writing workbook decisions. The first executable deliverable should be the matrix, not a workbook write.
