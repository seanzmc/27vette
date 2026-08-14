# Stingray Engine Appearance Display Order Match Grand Sport Spec

> **Archive closure (2026-07-29): COMPLETED.** Implementation is present at `8e6b406`. Any trailing approval request is historical; current operator commands are owned by `README.md`. Stage C approved this completed plan for archival.

> **Execution status (2026-07-29): SUPERSEDED.** This plan records an older generator/artifact topology. Do not run its commands or treat its compatibility paths, `production.py` route, artifact types, or retired test names as current guidance. Current commands and authority are owned by `README.md` and Pass 4 Stage A of `docs/superpowers/specs/2026-07-23-validation-single-lane-active-surface-cleanup.md`. Historical evidence below is preserved verbatim pending Stage C archival.

## Diagnosis

The requested change is workbook-owned display ordering for Stingray Engine Appearance choices. The source of truth is `stingray_master.xlsx`, specifically `stingray_options.display_order` for active rows in `section_id = sec_engi_001`.

Evidence inspected:

- Current branch/status:
  - Branch: `generator-simplification-pass1`
  - `git status --short --branch`: clean at spec time.
- Workbook source rows inspected with `openpyxl` from `stingray_master.xlsx`:
  - `stingray_options` active `sec_engi_001` rows currently order the LS6 covers first, then packages/components/accessories:
    - `opt_bc7_001` / `BC7`: `10`
    - `opt_bcp_001` / `BCP`: `20`
    - `opt_bcs_001` / `BCS`: `30`
    - `opt_bc4_001` / `BC4`: `40`
    - `opt_b6p_001` / `B6P`: `50`
    - `opt_zz3_001` / `ZZ3`: `60`
    - `opt_d3v_001` / `D3V`: `70`
    - `opt_sl9_001` / `SL9`: `80`
    - `opt_slk_001` / `SLK`: `90`
    - `opt_sln_001` / `SLN`: `100`
    - `opt_vup_001` / `VUP`: `110`
  - `grandSport_options` active `sec_engi_001` rows currently use this order:
    - `opt_b6p_001` / `B6P`: `1`
    - `opt_zz3_001` / `ZZ3`: `5`
    - `opt_d3v_001` / `D3V`: `10`
    - `opt_sl9_001` / `SL9`: `11`
    - `opt_bc7_001` / `BC7`: `19`
    - `opt_bcp_002` / `BCP`: `20`
    - `opt_bcs_002` / `BCS`: `30`
    - `opt_bc4_002` / `BC4`: `40`
    - `opt_slk_001` / `SLK`: `50`
    - `opt_sln_001` / `SLN`: `60`
    - `opt_vup_001` / `VUP`: `70`
- Relevant test inspected:
  - `tests/workbook-visual-copy-standardization.test.mjs:86` currently asserts Grand Sport engine-cover display order only and appears stale for `opt_bc7_001`, expecting `10` while the workbook currently has `19`.
- Runtime/generator ownership:
  - `scripts/generate_form.py --model stingray` reads `stingray_options.display_order` through the existing generator path and emits generated workbook sheets plus `form-output/stingray-form-data.json` / `.csv`.
  - `scripts/generate_registry.py` publishes `form-app/data.js` from promoted artifacts.

Root cause:

Stingray `sec_engi_001` display orders are not aligned to the current Grand Sport source ordering. This is source-data drift, not a generator/runtime bug. The existing visual-copy test also encodes stale Grand Sport expected order for `BC7` and does not yet assert Stingray-to-Grand-Sport parity.

Risk level: Low-to-medium.

Change type: workbook source-data + generated artifacts + tests. No generator-code change. No runtime-code change. No styling change.

## Exact Scope

Update only `stingray_options.display_order` for active `section_id = sec_engi_001` rows so the Stingray order matches Grand Sport by RPO/customer meaning.

Planned source row changes:

| RPO | Stingray option_id | Current Stingray order | Grand Sport order | New Stingray order |
| --- | --- | ---: | ---: | ---: |
| B6P | `opt_b6p_001` | 50 | 1 | 1 |
| ZZ3 | `opt_zz3_001` | 60 | 5 | 5 |
| D3V | `opt_d3v_001` | 70 | 10 | 10 |
| SL9 | `opt_sl9_001` | 80 | 11 | 11 |
| BC7 | `opt_bc7_001` | 10 | 19 | 19 |
| BCP | `opt_bcp_001` | 20 | 20 | 20 |
| BCS | `opt_bcs_001` | 30 | 30 | 30 |
| BC4 | `opt_bc4_001` | 40 | 40 | 40 |
| SLK | `opt_slk_001` | 90 | 50 | 50 |
| SLN | `opt_sln_001` | 100 | 60 | 60 |
| VUP | `opt_vup_001` | 110 | 70 | 70 |

Grand Sport rows are the reference and should not be changed in this pass.

## Files / Sheets / Artifacts To Change

Source workbook:

- `stingray_master.xlsx`
  - Sheet: `stingray_options`
  - Column: `display_order`
  - Rows: exact `option_id`s listed above where `section_id = sec_engi_001`.

Tests:

- `tests/workbook-visual-copy-standardization.test.mjs`
  - Replace the stale Grand Sport-only engine-cover order assertion with a cross-model parity assertion by RPO.
  - Expected order should be the current Grand Sport source order listed above.
  - Map Grand Sport paid covers to `_002` option IDs and Stingray paid covers to `_001` option IDs.
  - Keep description assertions only where already intentional; do not broaden copy edits.

Generated outputs after approved workbook edit and regeneration:

- `stingray_master.xlsx` generated `form_*` sheets from `scripts/generate_form.py --model stingray`.
- `form-output/stingray-form-data.json`.
- `form-output/stingray-form-data.csv` if the generator rewrites it normally.
- `form-app/data.js` after `scripts/generate_registry.py`.

Generated outputs not expected to have substantive changes:

- Grand Sport runtime/draft/preview artifacts.
- Z06 artifacts.
- Runtime JS/CSS/HTML.
- Dealer submission code.

If any non-Stingray generated artifacts change while running tests/generators, inspect whether they are timestamp-only or stale-registry side effects and restore unrelated churn before handoff.

## Implementation Plan

1. Preflight:
   - Confirm branch/status.
   - Confirm no Excel lock file exists: `~$stingray_master.xlsx` absent.
   - Run workbook package validation before write.

2. Snapshot target rows:
   - Read `stingray_options` and `grandSport_options` target rows by stable key (`option_id`) and record current `display_order`, `section_id`, `rpo`, and row number.
   - This snapshot is the rollback/evidence ledger.

3. Apply the workbook source-data edit only:
   - Use `.venv/bin/python` and `openpyxl` with `save_workbook_safely()` from `scripts/corvette_form_generator/workbook.py`.
   - Update only `stingray_options.display_order` cells for the exact listed `option_id`s.
   - Do not alter labels, descriptions, active/selectable flags, OVS rows, rules, price rules, exclusive groups, or Grand Sport rows.

4. Verify saved workbook on disk:
   - Reopen `stingray_master.xlsx` with `openpyxl` read-only.
   - Assert each target `stingray_options` row has the new numeric display order.
   - Assert Grand Sport reference rows are unchanged.
   - Assert no duplicate active `(source option sheet, section_id, display_order)` collisions in `stingray_options` / `grandSport_options` through schema validation.

5. Update tests:
   - Update `tests/workbook-visual-copy-standardization.test.mjs` to assert both models use the same `sec_engi_001` order by RPO.
   - Keep this a source-sheet test; do not add runtime JS expectations for a workbook-only ordering pass.

6. Regenerate runtime-facing Stingray artifacts:
   - Run `scripts/generate_form.py --model stingray`.
   - Run `scripts/generate_registry.py` to publish `form-app/data.js`.
   - Do not run Grand Sport/Z06 generation unless a gate proves a promoted artifact is stale or a test requires it.

7. Diff review:
   - Confirm source workbook change is only the intended `stingray_options.display_order` edits plus generated `form_*` sheet churn from the Stingray generator.
   - Confirm generated JSON/data.js changes are order/display-order-only for Stingray Engine Appearance choices, plus timestamps if present.
   - Confirm no runtime code or dealer submission path changed.

## Constraints

- Workbook source of truth: display order belongs in `stingray_options`, not Python or JavaScript.
- Workbook update only: no generator source-code changes, no runtime source-code changes, no CSS/HTML changes.
- Preserve visual styling and interaction behavior; this pass only changes ordering.
- Preserve dealer submission endpoint, modal behavior, Turnstile behavior, and payload shape.
- Preserve labels, descriptions, pricing, status, selectable/active flags, default behavior, includes/requires/excludes, exclusive groups, and price rules.
- No new dependencies.
- Do not edit generated `form_*` sheets directly.
- Use `.venv/bin/python`, not system Python.
- Use `save_workbook_safely()` and stop if Excel lock file exists.
- Preserve workbook bool-like cell storage; this pass edits only numeric `display_order` cells.

## Non-Goals

- No Grand Sport source-row changes.
- No Z06/ZR1/ZR1X source-row changes.
- No engine-cover behavior/default/rule/price cleanup.
- No copy/description normalization except test expectation cleanup directly required by the stale Grand Sport display-order assertion.
- No generator architecture changes.
- No browser styling changes.

## Validation Plan

Preflight:

```sh
git status --short --branch
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
# stop if ./~$stingray_master.xlsx exists
```

Workbook write verification:

```sh
.venv/bin/python - <<'PY'
# Reopen stingray_master.xlsx read-only and assert exact target display_order values.
# Also assert Grand Sport reference values remain unchanged.
PY
```

Regeneration:

```sh
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_registry.py
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Targeted tests:

```sh
node --test tests/workbook-visual-copy-standardization.test.mjs
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Focused generated-data assertion after regeneration:

```sh
node - <<'NODE'
// Load form-output/stingray-form-data.json and form-app/data.js.
// Assert Stingray sec_engi_001 active choices use order:
// B6P=1, ZZ3=5, D3V=10, SL9=11, BC7=19, BCP=20, BCS=30, BC4=40, SLK=50, SLN=60, VUP=70.
// Assert Grand Sport order in form-app/data.js remains the same.
NODE
```

Optional browser smoke if the user wants visual confirmation after tests:

- Serve `form-app` locally.
- Load Stingray.
- Open Exterior Appearance / Engine Appearance.
- Confirm order follows package/component/cover/accessory sequence matching Grand Sport.
- Check browser console for JS errors.

## Acceptance Criteria

- `stingray_options.sec_engi_001` display orders match Grand Sport by RPO as listed above.
- Grand Sport source rows remain unchanged.
- `tests/workbook-visual-copy-standardization.test.mjs` asserts cross-model engine appearance order parity and no longer encodes stale `BC7 = 10` for Grand Sport.
- Regenerated Stingray artifacts and `form-app/data.js` reflect the new order.
- Targeted gates pass.
- No runtime JS/CSS/HTML or dealer submission code changes.

## Approval Question

Approve this workbook-only pass to update `stingray_options.sec_engi_001.display_order` to match the current Grand Sport order, regenerate Stingray/app data, and update the visual-copy test accordingly?
