# Seat Presentation / Order Spec

Recommended reasoning level: high.

## Status

Approved and implemented 2026-06-17.

Implementation result:

- Updated active canonical seat rows in `stingray_options`, `grandSport_options`, and `z06_options`.
- `opt_aup_001` now uses `option_name=Asymmetrical Seats` and `description=Competition Driver Seat, GT2 Passenger Seat` in all promoted option sheets.
- Active `sec_seat_002` display order is now canonical in all promoted option sheets: `AQ9=10`, `AH2=20`, `AE4=30`, `AUP=40`.
- `tests/workbook-visual-copy-standardization.test.mjs` now removes AUP from the copy allowlist and asserts the R-6 copy/order decision.
- Active model artifacts and registry were regenerated.

User product decisions provided 2026-06-17:

- AUP presentation: Option A.
  - canonical `option_name`: `Asymmetrical Seats`
  - canonical `description`: `Competition Driver Seat, GT2 Passenger Seat`
- Canonical seat order: sport escalation with AUP last.

## Diagnosis

Current seat source shape is structurally clean, but AUP presentation is inconsistent.

Evidence inspected 2026-06-17:

- Active branch: `generator-simplification-pass1`.
- `docs/active-seat-standard-equipment-ownership-spec.md` says Stingray active seat canonicalization is complete.
- Before this pass, `docs/copy-convergence-review-2026-06-17.md` classified R-6 as deferred for `sec_seat_002` seat presentation/order.
- Current active `sec_seat_002` rows in promoted option sheets:

| Sheet | Option ID | RPO | Current option_name | Current description | Current display_order | Price |
| --- | --- | --- | --- | --- | ---: | ---: |
| `stingray_options` | `opt_aq9_001` | AQ9 | `GT1 Bucket Seats` | blank | 10 | 0 |
| `stingray_options` | `opt_ah2_001` | AH2 | `GT2 Bucket Seats` | blank | 25 | 1695 |
| `stingray_options` | `opt_ae4_002` | AE4 | `Competition Sport Bucket Seats` | blank | 40 | 2095 |
| `stingray_options` | `opt_aup_001` | AUP | `Competition Sport Driver and GT2 Passenger Bucket Seats` | blank | 80 | 350 |
| `grandSport_options` | `opt_aq9_001` | AQ9 | `GT1 Bucket Seats` | blank | 10 | 0 |
| `grandSport_options` | `opt_ah2_001` | AH2 | `GT2 Bucket Seats` | blank | 25 | 0 |
| `grandSport_options` | `opt_ae4_002` | AE4 | `Competition Sport Bucket Seats` | blank | 40 | 1095 |
| `grandSport_options` | `opt_aup_001` | AUP | `Asymmetrical Seats` | `Competition Driver Seat, GT2 Passenger Seat` | 80 | 350 |
| `z06_options` | `opt_aq9_001` | AQ9 | `GT1 Bucket Seats` | blank | 10 | 0 |
| `z06_options` | `opt_ah2_001` | AH2 | `GT2 Bucket Seats` | blank | 25 | 1695 |
| `z06_options` | `opt_ae4_002` | AE4 | `Competition Sport Bucket Seats` | blank | 40 | 1095 |
| `z06_options` | `opt_aup_001` | AUP | `Asymmetrical Seats` | `Competition Driver Seat, GT2 Passenger Seat` | 80 | 350 |

Root cause:

- The old Stingray duplicate-seat source shape was canonicalized, but the shared AUP customer-facing label was left out of the safe copy cohort as R-6.
- Display order already renders in sport-escalation order with AUP last, but numeric order is non-canonical (`10/25/40/80`) and should be normalized if this pass claims durable canonical seat order.

Risk level: medium.

Change type: workbook/data + tests + generated artifacts. No intended runtime JS behavior change.

## Exact Workbook Changes

Change only active canonical seat rows in promoted option sheets.

### AUP presentation

Set `opt_aup_001` in all promoted sheets to:

| Sheet | option_name | description |
| --- | --- | --- |
| `stingray_options` | `Asymmetrical Seats` | `Competition Driver Seat, GT2 Passenger Seat` |
| `grandSport_options` | `Asymmetrical Seats` | `Competition Driver Seat, GT2 Passenger Seat` |
| `z06_options` | `Asymmetrical Seats` | `Competition Driver Seat, GT2 Passenger Seat` |

This is a source-row copy/presentation edit only. Do not change RPO, option ID, active/selectable, OVS status, price, rules, or section.

### Seat display order

Normalize active `sec_seat_002` display orders in all promoted sheets to:

| RPO | Option ID | Canonical display_order | Reason |
| --- | --- | ---: | --- |
| AQ9 | `opt_aq9_001` | 10 | GT1 baseline |
| AH2 | `opt_ah2_001` | 20 | GT2 next sport step |
| AE4 | `opt_ae4_002` | 30 | full Competition Sport seats |
| AUP | `opt_aup_001` | 40 | asymmetric/mixed-seat presentation last per user decision |

This preserves current visual order while removing non-canonical gaps.

## Exact Files / Sheets To Change

Workbook source:

- `stingray_master.xlsx`
  - `stingray_options`
  - `grandSport_options`
  - `z06_options`

Tests:

- `tests/workbook-visual-copy-standardization.test.mjs`
  - remove AUP from copy allowlist after applying the canonical presentation.
  - assert AUP name/description across all promoted option sheets.
  - assert canonical active seat order across all promoted option sheets.

Generated artifacts after regeneration:

- `form-output/stingray-form-data.json`
- `form-output/stingray-form-data.csv`
- `form-output/inspection/grand-sport-*`
- `form-output/inspection/z06-*`
- `form-app/data.js`
- generated `form_*` workbook sheets touched by `scripts/generate_form.py --model stingray`

Docs after implementation:

- `docs/copy-convergence-product-decision-spec.md`
- `docs/copy-convergence-review-2026-06-17.md`
- `docs/actual-tasks-remaining-6-17.md`
- `docs/persisting-audit-findings-2026-06-14.md`

## Constraints

- Workbook owns customer-facing seat presentation and display order.
- No runtime JS special cases.
- No new dependencies.
- No refactor.
- No visual CSS/layout change.
- No dealer endpoint, payload, Turnstile, or submission behavior change.
- Do not edit generated `form_*` sheets directly.
- Do not touch seat pricing, price rules, OVS availability/status, interiors, `interior_components`, `PriceRef`, `model_interior_scope`, or seatbelt rules.
- Check for `~$stingray_master.xlsx` before workbook write.
- Save through `save_workbook_safely()` and verify workbook cells on disk.
- Preserve existing active promoted `(section_id, display_order)` uniqueness.

## Risks

- Generated order churn: display-order numeric changes preserve visual order but will change generated artifacts.
- Count-sensitive tests should not change, but generated timestamp/order diffs need review.
- AUP copy change affects customer-facing option cards, selected RPO summary, Markdown export, and dealer payload option label text.
- Seat/interior price math is sensitive; gates must confirm no pricing behavior drift.
- Browser smoke still needed to confirm seat card presentation reads correctly.

## Non-goals

- No seat availability/status change.
- No seat pricing correction.
- No interior grouping or component cleanup.
- No `sec_tech_001` / connected-service standard-equipment ownership work.
- No broad residual copy allowlist cleanup beyond AUP.
- No runtime card restyling.

## Validation Plan

Preflight before workbook write:

```sh
git status --short --branch
python - <<'PY'
from pathlib import Path
print(Path('~$stingray_master.xlsx').exists())
PY
```

Workbook/package validation after write:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Regeneration:

```sh
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
.venv/bin/python scripts/generate_registry.py
```

Targeted gates:

```sh
node --test tests/workbook-visual-copy-standardization.test.mjs
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/z06-form-data-draft.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Diff checks:

```sh
git diff --check
git status --short --branch
```

Manual browser verification pending after gates:

- Seat step shows order AQ9 → AH2 → AE4 → AUP for Stingray, Grand Sport, Z06.
- AUP card reads `Asymmetrical Seats` with description `Competition Driver Seat, GT2 Passenger Seat`.
- Seat selection/default behavior still works for 1LT/2LT/3LT and 1LZ/2LZ/3LZ.
- Selected RPO summary and build export use expected AUP label.

## Historical Approval Question

Pre-implementation prompt asked whether to approve this R-6 seat presentation/order pass with the workbook-only source edits above, plus focused test updates, regeneration, and targeted gates.
