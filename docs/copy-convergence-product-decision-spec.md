# Copy-Convergence / Product-Decision Spec

Recommended reasoning level: high.

## Status

Approved and implemented 2026-06-17.

Implementation result:

- Created `docs/copy-convergence-review-2026-06-17.md` from a read-only workbook probe.
- Applied safe GS/Z06-majority copy convergence to Stingray source rows, excluding reviewed/deferred allowlist fields.
- Applied user decisions R-1 through R-6:
  - R-1 UV6 Z06 section drift remains intentional.
  - R-2 SC7 moved to Stingray `sec_lpoe_001`, punctuation normalized, and display order set to `71` to preserve active `(section_id, display_order)` uniqueness.
  - R-3 DRZ copy normalized to `Auto-Dimming Rear Camera Mirror` / `Inside rearview with full camera display`.
  - R-4 EFR/EDU copy updated per model-specific decision.
  - R-5 NGA copy updated per model-specific exhaust-exit decision.
  - R-6 AUP copy/order normalized in `docs/seat-presentation-order-spec.md`: `Asymmetrical Seats` / `Competition Driver Seat, GT2 Passenger Seat`, with active seat order AQ9/AH2/AE4/AUP at 10/20/30/40.
- Extended `tests/workbook-visual-copy-standardization.test.mjs` to load `z06_options`, enforce shared-copy parity with an allowlist, reject trailing-period-only drift, and assert R-1 through R-6 decisions.
- Regenerated Stingray, Grand Sport, Z06, and registry artifacts.
- Updated `tests/stingray-generator-stability.test.mjs` for the already-current Stingray generated rule count of `144`, matching the previously completed rear-script pairwise-exclude retirement.

## Preflight Findings

Current branch/status at spec time:

- Branch: `generator-simplification-pass1`
- Working tree: clean before this spec was written.
- Root `codex-context.md`: not present; `AGENTS.md` remains the active repo guide loaded in context.

Current source evidence inspected:

- `docs/actual-tasks-remaining-6-17.md` lists the recommended next pass as copy convergence / product decisions.
- `docs/persisting-audit-findings-2026-06-14.md` sections 8 and 9 list the persisting copy drift and product-review items.
- `docs/workbook-consistency-review-2026-06-11.md` sections 4, 5, and 6 define the older copy findings, intentional model differences, and human-review rows.
- `tests/workbook-visual-copy-standardization.test.mjs` currently loads only `stingray_options` and `grandSport_options`; it does not load or compare `z06_options`.
- `stingray_master.xlsx` was inspected read-only with `openpyxl`.

Current workbook facts from read-only probe:

- Active option row counts:
  - `stingray_options`: 237
  - `grandSport_options`: 237
  - `z06_options`: 238
- Strict shared active option IDs with one active row in each promoted sheet: 155.
- Current strict shared copy drift:
  - option-name mismatches: 50
  - description mismatches: 86
  - description mismatches that normalize by trailing period only: 33
- Representative name drift still present: AJ7, AP9, AUP, BAZ, BV4, CJ2, CM9, D84, D86, DPB, DPC, DPG.
- Representative description drift still present: 5JR, 5ZC, 5ZD, AJ7, AP9, AUP, BAZ, BV4, CAV, CFX, CJ2, CM9.

Historical product-review rows that required explicit decisions:

| ID | Current evidence | Decision needed before workbook edit |
|---|---|---|
| R-1 `opt_uv6_001` / UV6 | Stingray and Grand Sport use `sec_2lte_001`; Z06 uses `sec_1lte_001`; copy is otherwise equal. | Confirm whether Z06 Head-Up Display belongs as 1LZ standard equipment or should align to `sec_2lte_001`. |
| R-2 `opt_sc7_001` / SC7 | Stingray uses `sec_lpoi_001`; Grand Sport and Z06 use `sec_lpoe_001`; copy differs only by trailing period. | Confirm interior vs exterior LPO placement. |
| R-3 `opt_drz_001` / DRZ | Stingray name/description are swapped relative to Grand Sport and Z06. | Pick canonical name/description pair. |
| R-4 `opt_efr_001` / EFR and `opt_edu_001` / EDU | Stingray uses short exterior-accent copy; Grand Sport and Z06 mention CFV/CFZ ground effects that do not exist on Stingray. | Decide model-specific vs shared accent copy; do not majority-overwrite Stingray blindly. |
| R-5 `opt_nga_001` / NGA | Stingray says corner exit behind rear wheels; Grand Sport says `Standard. Corner Exit`; Z06 says only `Standard`. | Decide per-model exit-style wording. |
| R-6 `sec_seat_002` seat rows | Seat row ordering/multiplicity differs by model and row purpose. | Decide presentation grouping/order separately from copy convergence. |

Known cross-model `option_id` drift that affects review joins but should not be renamed in this pass:

- Z06 uses `_002` IDs where Stingray uses `_001` for U2K, U5G, UE1, and VV4.
- Z06 uses `opt_cfv_002` for CFV; Grand Sport/Stingray do not currently provide an active matching CFV option row.
- This pass may use RPO fallback for review/reporting, but it must not migrate option IDs.

## Diagnosis

Root cause:

- Shared customer copy lives directly in promoted option source sheets, but past cleanup normalized Grand Sport and Z06 copy ahead of Stingray.
- Existing tests pin selected reviewed rows and some period/no-period differences, but they do not provide a durable pairwise/shared-copy guard across all three promoted option sheets.
- A few differences are product decisions, not mechanical style drift. Majority-copying those rows would hide real model semantics in workbook data.

Risk level: medium-high.

Change type: mixed workbook/data + generated artifacts + tests/docs. No runtime JavaScript or styling change intended.

## Ownership Decision

Customer-facing option names, descriptions, sections, and display order are workbook-owned source data:

- Copy edits belong in `stingray_master.xlsx` source sheets.
- Generated workbook `form_*` sheets, `form-output/*`, and `form-app/data.js` are outputs and must be regenerated, not hand-edited.
- Runtime JavaScript should keep rendering generated copy generically.
- Product-review decisions must be explicit workbook/source decisions, not inferred from majority vote.

## Recommended Scope

### Implement now after approval

1. Build a durable review table before workbook edits.

   Produce a Markdown or CSV review artifact under `docs/` listing:

   - strict shared active option IDs across `stingray_options`, `grandSport_options`, and `z06_options`,
   - option_id, RPO, source rows, section IDs, active flags,
   - current names/descriptions per model,
   - whether Grand Sport and Z06 agree,
   - whether drift is name, description, punctuation-only, or substantive,
   - recommended action: mechanical copy, intentional allowlist, or product-decision required.

   Recommended artifact path:

   - `docs/copy-convergence-review-2026-06-17.md`

   The report can be generated by an implementation-time inline Python probe; do not add a permanent script unless repeated review workflow is explicitly approved.

2. Mechanically converge safe shared copy only.

   Allowed automatic copy cohort:

   - active in all three promoted option sheets,
   - exactly one active row per sheet for the same `option_id`,
   - Grand Sport and Z06 agree on the target field,
   - Stingray differs only by style, density, qualifier placement, or trailing punctuation,
   - option ID/RPO is not in the product-decision list or intentional-difference allowlist.

   Recommended default copy source:

   - Use the Grand Sport/Z06 majority value for safe rows.
   - When name and description are complementary, move qualifier text as a pair; do not overwrite only `option_name` if the corresponding description carries the moved qualifier.
   - For punctuation-only accessory descriptions, adopt the Grand Sport/Z06 no-terminal-period style if approved, and update tests in the same pass.

3. Keep product-review rows out of automatic edits.

   Exclude at minimum:

   - R-1 UV6 section placement,
   - R-2 SC7 section placement,
   - R-3 DRZ name/description pair,
   - R-4 EFR/EDU exterior-accent copy,
   - R-5 NGA exhaust-tip description,
   - R-6 `sec_seat_002` seat presentation ordering/multiplicity.

   These rows should appear in the review table with current evidence and decision prompts. They should not be changed unless the user provides explicit row-level decisions before implementation.

4. Add a durable intentional-difference allowlist.

   Initial allowlist must cover known valid model differences from `docs/workbook-consistency-review-2026-06-11.md` section 5, including:

   - EYK/EYT emblem content where model badging differs,
   - VYW floor-mat logo applicability where Z06 copy intentionally differs,
   - WUB standard/selectable placement differences,
   - ZZ3 includes-list differences where Z06 lacks LS6 cover options,
   - SFZ applicability wording if kept model-specific,
   - section taxonomy differences for standard/trim equipment that are not copy defects.

   Keep allowlist narrow and field-specific: `option_id` or RPO, field (`option_name`, `description`, `section_id`), models allowed to differ, and reason.

5. Extend copy tests.

   Update `tests/workbook-visual-copy-standardization.test.mjs`:

   - load `z06_options` alongside `stingray_options` and `grandSport_options`,
   - keep existing focused tests for reviewed brake, roof, engine, and accessory copy where still relevant,
   - add a generic shared active option copy-parity assertion using the allowlist,
   - assert product-decision rows are explicitly excluded or characterized, not silently majority-copied,
   - keep Z06 suffix/no-RPO ID drift out of strict `option_id` parity enforcement unless a separate ID migration is approved.

6. Regenerate affected artifacts.

   Run all active model generators because shared source copy can affect every promoted runtime contract:

   ```sh
   .venv/bin/python scripts/generate_form.py --model stingray
   .venv/bin/python scripts/generate_form.py --model grand_sport
   .venv/bin/python scripts/generate_form.py --model z06
   .venv/bin/python scripts/generate_registry.py
   ```

7. Update docs after implementation.

   - Mark this spec approved/implemented.
   - Update `docs/actual-tasks-remaining-6-17.md` and `docs/persisting-audit-findings-2026-06-14.md` with completed safe-copy scope and still-open product decisions.
   - Keep product-review decisions that were not explicitly resolved visible as follow-up work.

### Explicitly defer

- Majority-overwriting R-1 through R-6 without explicit product decisions.
- Z06 option-ID suffix/no-RPO ID migration.
- Active `sec_tech_001` / connected-service ownership.
- Interior CSV/config stale-surface cleanup.
- Future-model ZR1/ZR1X scaffold display-order cleanup.
- Runtime JavaScript refactors or RPO/model-specific runtime exceptions.
- New dependencies or permanent one-pass cleanup scripts.

## Exact Files and Sheets to Change

Workbook source sheets:

- `stingray_master.xlsx`
  - `stingray_options` for safe Stingray copy convergence.
  - `grandSport_options` only if the review table finds Grand Sport differs from the approved canonical copy for a safe non-decision row.
  - `z06_options` only if the review table finds Z06 differs from the approved canonical copy for a safe non-decision row.

Generated artifacts after regeneration:

- generated workbook `form_*` sheets emitted by the model generation runs,
- `form-output/stingray-form-data.json`,
- `form-output/inspection/grand-sport-runtime-contract.json`,
- `form-output/inspection/grand-sport-form-data-draft.json`,
- `form-output/inspection/z06-runtime-contract.json`,
- `form-output/inspection/z06-form-data-draft.json`,
- `form-app/data.js`.

Tests:

- `tests/workbook-visual-copy-standardization.test.mjs`
- Existing model/runtime gates listed below; add focused assertions to nearby tests only if the copy change affects an already-covered surface.

Docs/report artifacts:

- `docs/copy-convergence-product-decision-spec.md`
- `docs/copy-convergence-review-2026-06-17.md` or equivalent dated review table
- `docs/actual-tasks-remaining-6-17.md`
- `docs/persisting-audit-findings-2026-06-14.md`

## Constraints

- Close Excel before workbook writes.
- Stop if `~$stingray_master.xlsx` exists unless explicitly proven stale.
- Use `save_workbook_safely()` for workbook writes.
- Verify saved workbook cells on disk after writing and before generation.
- Do not edit generated `form_*` sheets, `form-output/*`, or `form-app/data.js` by hand.
- No new dependencies.
- No runtime JavaScript changes.
- No visual styling changes.
- No dealer-submission endpoint, payload, or Turnstile changes.
- No hidden business-rule logic in scripts to suppress workbook data problems.
- Preserve model-specific product truth; do not force all shared RPOs to identical copy when order-guide/product semantics differ.
- Preserve bool-like cell storage shape; do not normalize unrelated workbook cells.
- Touch only approved copy fields and necessary tests/docs/artifacts.

## Required Preflight Before Editing

1. Confirm branch/status and Excel lock state:

```sh
git status --short --branch
python3 - <<'PY'
from pathlib import Path
print(Path('~$stingray_master.xlsx').exists())
PY
```

2. Re-run the read-only drift inventory and save/review the decision table before workbook edits.

3. Stop and ask for product decisions if the safe/mechanical cohort is smaller or riskier than expected, or if R-1 through R-6 need to be changed in the same implementation pass.

## Implementation Plan

1. Create the review table from current workbook data.
2. Convert review rows into three buckets:
   - safe mechanical convergence,
   - intentional-difference allowlist,
   - product-decision required.
3. Patch tests first or in the same pass so the intended guard shape is clear.
4. Apply workbook copy edits through a small safe-save script or workbook operation that touches only approved cells.
5. Reopen `stingray_master.xlsx` read-only and verify edited cells by sheet/option_id/field.
6. Regenerate Stingray, Grand Sport, Z06, then registry.
7. Review generated diffs to confirm drift is expected customer-copy changes plus timestamps, not rule/pricing/schema changes.
8. Update docs/status files.
9. Run validation gates.

## Validation Plan

Workbook/package validation:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Generation:

```sh
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
.venv/bin/python scripts/generate_registry.py
```

Focused and affected tests:

```sh
node --test tests/workbook-visual-copy-standardization.test.mjs
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/z06-contract-preview.test.mjs
node --test tests/z06-form-data-draft.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Diff review:

```sh
git diff -- stingray_master.xlsx tests/workbook-visual-copy-standardization.test.mjs docs form-output form-app/data.js
```

Manual verification still needed after gates:

- Review customer-facing option cards for edited copy in one local browser smoke if large copy changes land.
- Confirm generated build summary/export text still reads correctly for affected copied options.
- Confirm any unresolved R-1 through R-6 decisions remain documented, not accidentally edited.

## Risks and Non-Goals

Risks:

- Copy convergence can accidentally erase model-specific product truth if allowlist is too broad or too narrow.
- Paired name/description moves can produce duplicate or missing qualifiers if fields are edited independently.
- Existing tests intentionally pin some period drift; test updates must reflect the approved punctuation standard, not hide regressions.
- Regenerated artifacts may show large text diffs; diff review must separate expected copy changes from rule/pricing/runtime contract drift.

Non-goals:

- No section-placement decisions without explicit approval.
- No Z06 ID migration.
- No connected-service/standard-equipment ownership changes.
- No runtime behavior changes.
- No cleanup of unrelated workbook rows, generated fields, or optional audit tooling.

## Historical Approval Question

Pre-implementation prompt asked whether to approve this copy-convergence/product-decision pass with the default safe scope: build review table, mechanically converge only safe GS/Z06-majority copy, add a Z06-inclusive copy parity allowlist test, regenerate active models, and leave R-1 through R-6 untouched unless the user provided explicit product decisions.

Historical recommended answer: approve default safe scope first; handle R-1 through R-6 as a follow-up product-decision pass after the review table is visible.
