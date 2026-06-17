# Active Seat / Standard-Equipment Ownership Spec

Recommended reasoning level: high.

## Status

Spec only. Do not implement until approved.

## Diagnosis

After the non-runtime option-source purge, the remaining noisy active emitted rows are not all the same kind of problem.

Current evidence inspected:

- Active branch/status: `generator-simplification-pass1`, clean worktree at inspection time.
- Current architecture in `AGENTS.md`: every active model follows the workbook-to-runtime path; workbook rows own product data/business rules; generated artifacts are outputs.
- Prior purge spec: `docs/active-model-nonruntime-option-row-purge-spec.md` explicitly deferred active seat rows and active standard-equipment / connected-service rows because they currently emit runtime behavior.
- Current workbook/runtime inventory:
  - Stingray has 11 active seat RPO source rows:
    - 8 active selectable `sec_seat_002` rows: `opt_aq9_003`, `opt_ae4_001`, `opt_aq9_004`, `opt_ah2_003`, `opt_ae4_002`, `opt_ah2_002`, `opt_ae4_003`, `opt_aup_001`.
    - 3 active non-selectable trim-standard rows: `opt_aq9_002` in `sec_1lte_001`, `opt_aq9_001` in `sec_2lte_001`, `opt_ah2_001` in `sec_3lte_001`.
    - All 11 emit choices. `opt_aq9_003`, `opt_aq9_001`, and `opt_ah2_001` also emit standard-equipment rows.
  - Grand Sport already uses 4 active canonical seat rows in `grandSport_options.sec_seat_002`: `opt_aq9_001`, `opt_ah2_001`, `opt_ae4_002`, `opt_aup_001`.
  - Z06 already uses 4 active canonical seat rows in `z06_options.sec_seat_002`: `opt_aq9_001`, `opt_ah2_001`, `opt_ae4_002`, `opt_aup_001`.
  - Active `sec_tech_001` / connected-service standard rows still emit visible standard-equipment rows:
    - Stingray: `opt_u5g_001`, `opt_004`, `opt_ive_001`, `opt_008`, `opt_ue1_001`, `opt_u2k_001`, `opt_vv4_001`, `opt_ppw_001`.
    - Grand Sport: `opt_ive_001`, `opt_ppw_001`, `opt_015`.
    - Z06: `opt_129`, `opt_ive_001`, `opt_ppw_001`, `opt_u2k_002`, `opt_u5g_002`, `opt_ue1_002`, `opt_vv4_002`.
- Current generator behavior:
  - `scripts/corvette_form_generator/production.py:105-155` dedupes Stingray standard equipment by `(variant_id, rpo)` and chooses a preferred source row with `standard_equipment_preference()`.
  - `production.py:185-189` derives standard-equipment bucket sections from `section_presentation.standard_equipment_bucket`, otherwise falls back to configured standard sections.
  - Adding `section_presentation.standard_equipment_bucket=True` to `sec_seat_002` would move the seat section itself into the standard-equipment step. That is not safe.
  - `scripts/corvette_form_generator/inspection.py:1057-1075` emits standard-equipment rows from draft choices whose status is `standard`.
- Existing model pattern:
  - Grand Sport and Z06 already carry canonical seat rows plus trim-scoped seat price rules.
  - Stingray has no current seat price rules in `price_rules`; its seat prices are split across duplicate option rows.

Root cause:

Stingray seat source rows still mix two ownership concepts:

1. customer-selectable seat option card ownership; and
2. trim-standard equipment presentation / default ownership.

Grand Sport and Z06 already model seats closer to the desired shape: one canonical seat-row set in `sec_seat_002`, with status/price variation carried by OVS rows and price rules. Stingray still uses extra option IDs to carry trim-specific seat status/price/standard-equipment behavior.

The active `sec_tech_001` rows are different. They are not duplicate seat modeling. They are currently the canonical workbook source for visible standard equipment. The current workbook has no separate standard-equipment source sheet that can replace them without introducing a new owner.

Risk level: high. This pass can affect user-visible seat choices, standard-equipment summaries, selected/default RPOs, interior price math, build download, and dealer payloads.

Change type: workbook/data + generic generator/test updates + generated artifacts. No intended runtime JS behavior change. No new dependencies.

## Ownership Decision

Use existing workbook pathways before adding new ones:

- Seat option-card behavior belongs in canonical active `*_options.sec_seat_002` rows plus matching `*_ovs` status rows.
- Seat trim-specific price behavior belongs in model price-rule sheets, following the existing Grand Sport / Z06 pattern.
- Seat default/standard behavior should come from canonical seat rows whose OVS status is `standard`, not duplicate non-selectable trim-equipment seat rows.
- Active generic standard-equipment / connected-service rows remain workbook option-source rows in this pass. Do not delete `sec_tech_001` rows until a separate workbook-owned standard-equipment source model exists and is proven.

## Recommended Scope

### Implement now: Stingray seat canonicalization only

Bring Stingray seat source shape closer to Grand Sport/Z06 by reducing active Stingray seats to four canonical `sec_seat_002` rows:

- `AQ9` / GT1 Bucket Seats
- `AH2` / GT2 Bucket Seats
- `AE4` / Competition Sport Bucket Seats
- `AUP` / Competition Sport Driver and GT2 Passenger Bucket Seats

Exact approved migration map:

| Final canonical row | RPO | Final section | Final selectable | Final active | Base price | Final display order | Retired source option IDs | Final OVS statuses |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- |
| `opt_aq9_001` | `AQ9` | `sec_seat_002` | `True` | `True` | `0` | `10` | `opt_aq9_002`, `opt_aq9_003`, `opt_aq9_004` | `standard` on `1lt_c07`, `1lt_c67`, `2lt_c07`, `2lt_c67`; `unavailable` on `3lt_c07`, `3lt_c67` |
| `opt_ah2_001` | `AH2` | `sec_seat_002` | `True` | `True` | `1695` | `25` | `opt_ah2_002`, `opt_ah2_003` | `unavailable` on `1lt_c07`, `1lt_c67`; `available` on `2lt_c07`, `2lt_c67`; `standard` on `3lt_c07`, `3lt_c67` |
| `opt_ae4_002` | `AE4` | `sec_seat_002` | `True` | `True` | `2095` | `40` | `opt_ae4_001`, `opt_ae4_003` | `available` on all six Stingray variants |
| `opt_aup_001` | `AUP` | `sec_seat_002` | `True` | `True` | `350` | `80` | none | `unavailable` on `1lt_c07`, `1lt_c67`, `2lt_c07`, `2lt_c67`; `available` on `3lt_c07`, `3lt_c67` |

Exact price-rule additions:

| Price rule ID | condition_option_id | target_option_id | type | price | trim_level_scope | notes |
| --- | --- | --- | --- | ---: | --- | --- |
| `sr_pr_1lt_ae4_seat_001` | `opt_ae4_002` | `opt_ae4_002` | `override` | `1095` | `1LT` | preserve current Stingray 1LT AE4 price from retired `opt_ae4_001` |
| `sr_pr_3lt_ae4_seat_001` | `opt_ae4_002` | `opt_ae4_002` | `override` | `595` | `3LT` | preserve current Stingray 3LT AE4 price from retired `opt_ae4_003` |
| `sr_pr_3lt_ah2_seat_001` | `opt_ah2_001` | `opt_ah2_001` | `override` | `0` | `3LT` | preserve current Stingray 3LT AH2 standard price from retired `opt_ah2_002` |

Rationale:

- These match the canonical Grand Sport / Z06 seat IDs where practical.
- `opt_aq9_001` aligns with Grand Sport/Z06 and intentionally replaces current 1LT standard AQ9 ID `opt_aq9_003`; that ID drift is approved only for seat canonicalization.
- `opt_ah2_001` already emits Stingray 3LT standard AH2 row and matches Grand Sport/Z06.
- `opt_ae4_002` is already the Grand Sport/Z06 canonical AE4 seat ID.
- `opt_aup_001` is already shared.

Do not change this map during implementation without revising spec. Preflight must still prove all references are moved or deleted safely before workbook write.

### Standard-equipment grouping decision

Seat-only grouping drift is approved for this pass.

Approved standard-equipment grouping drift:

- 1LT standard AQ9 may change option ID from `opt_aq9_003` to `opt_aq9_001` and stays in `sec_seat_002` / `Seats`.
- 2LT standard AQ9 may move from `sec_2lte_001` / `2LT Equipment` to `sec_seat_002` / `Seats`.
- 3LT standard AH2 may move from `sec_3lte_001` / `3LT Equipment` to `sec_seat_002` / `Seats`.

No other standard-equipment grouping drift is approved. Active `sec_tech_001` / connected-service rows must stay unchanged.

### Explicitly defer: active connected-service / standard-tech rows

Do not delete these rows in this pass:

- Stingray `sec_tech_001` rows: `opt_u5g_001`, `opt_004`, `opt_ive_001`, `opt_008`, `opt_ue1_001`, `opt_u2k_001`, `opt_vv4_001`, `opt_ppw_001`.
- Grand Sport `sec_tech_001` rows: `opt_ive_001`, `opt_ppw_001`, `opt_015`.
- Z06 `sec_tech_001` rows: `opt_129`, `opt_ive_001`, `opt_ppw_001`, `opt_u2k_002`, `opt_u5g_002`, `opt_ue1_002`, `opt_vv4_002`.

They are active emitted standard equipment and have no replacement owner today.

## Exact Sheets / Files to Change

Expected workbook source changes after approval:

- `stingray_master.xlsx`
  - `stingray_options`
    - rewrite the four canonical seat rows exactly per the migration map above.
    - delete duplicate active Stingray seat rows that no longer own canonical behavior after migration.
  - `stingray_ovs`
    - move full variant status coverage onto the four canonical seat option IDs exactly per the migration map above.
    - delete OVS rows for retired duplicate seat option IDs.
  - `price_rules`
    - add the exact three trim-scoped seat price overrides listed above.
  - Possible reference cleanup if preflight finds references to retired seat IDs:
    - `rule_mapping`
    - `rule_groups` / `rule_group_members`
    - `exclusive_groups` / `exclusive_group_members`
    - `variant_option_overrides`
    - `default_selection_rules`
    - `asset_map`
    - `color_overrides`

Expected code changes:

- Prefer no runtime JS changes.
- Prefer no new sheet.
- No metadata extension in this pass.
- If implementation produces non-seat standard-equipment grouping drift, stop and restore before handoff. Do not patch this with RPO-specific JavaScript.

Expected tests to add/update:

- A source-shape guard, likely new or in `tests/nonruntime-option-source-purge.test.mjs`, asserting:
  - Stingray has only canonical active seat rows in `sec_seat_002` after this pass.
  - no active Stingray non-selectable seat rows remain in `sec_1lte_001`, `sec_2lte_001`, or `sec_3lte_001`.
  - Grand Sport/Z06 canonical seat shape remains unchanged.
  - active `sec_tech_001` rows remain intentionally deferred.
- Update `tests/stingray-generator-stability.test.mjs` count/shape assertions if only approved seat-source row counts move.
- Update or add Stingray runtime tests for:
  - 1LT/2LT/3LT default/standard seat rows still appear correctly.
  - selectable seat cards still work.
  - seat prices remain current by trim.
  - standard-equipment summary remains customer-equivalent.
  - interior price math still uses resolved selected seat price.

Generated outputs to regenerate and diff-review:

- generated `form_*` sheets in `stingray_master.xlsx`
- `form-output/stingray-form-data.json`
- `form-output/stingray-form-data.csv`
- `form-app/data.js`

## Implementation Constraints

- Spec-first: do not implement until approved.
- Workbook owns business data.
- No runtime JS model/RPO special cases.
- No new dependencies.
- No visual styling changes.
- No dealer endpoint, Turnstile, or live submission behavior changes.
- Do not delete active `sec_tech_001` / connected-service rows in this pass.
- Do not delete active Grand Sport or Z06 canonical seat rows.
- Do not delete `interior_components` seat/component rows or `PriceRef` seat/R6X rows.
- Preserve workbook bool cell storage conventions.
- Check for `~$stingray_master.xlsx` before workbook writes.
- Save through `save_workbook_safely()` and verify workbook on disk.
- Delete matching OVS rows whenever retiring an option row.
- Fail preflight if retired seat option IDs still have active references outside the approved migration map.

## Required Preflight Before Workbook Write

1. Snapshot current runtime behavior outside the repo:
   - `form-output/stingray-form-data.json`
   - VM-exported `window.CORVETTE_FORM_DATA` from `form-app/data.js` as JSON.
2. Read-only workbook inventory:
   - exact Stingray seat rows by `option_id`, `rpo`, `section_id`, `active`, `selectable`, `price`, and `display_order`.
   - exact Stingray OVS statuses for all current seat option IDs.
   - all active references to seat option IDs in rule, price, default, variant override, asset, and color sheets.
   - `PriceRef` rows used by seat/interior/R6X pricing.
3. Generate a dry-run migration plan:
   - keep/rewrite canonical IDs.
   - delete IDs.
   - OVS rows moved/deleted.
   - price rules added/updated.
   - expected generated choice and standard-equipment deltas.
   - explicit standard-equipment grouping result: only approved seat-only grouping drift appears; no non-seat grouping drift.
4. Stop if dry-run includes any non-seat row or any active tech/connected-service row.

## Validation Plan

Workbook package/schema:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Regenerate:

```sh
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_registry.py
```

Contract checks:

```sh
node scripts/compare-generated-contracts.mjs /tmp/before-stingray-form-data.json form-output/stingray-form-data.json || true
node scripts/compare-generated-contracts.mjs /tmp/before-corvette-form-data.json /tmp/after-corvette-form-data.json || true
node scripts/seat-canonicalization-diff.mjs /tmp/before-stingray-form-data.json form-output/stingray-form-data.json
node scripts/seat-canonicalization-diff.mjs /tmp/before-corvette-form-data.json /tmp/after-corvette-form-data.json --model stingray
```

`compare-generated-contracts.mjs` is diagnostic in this pass, not pass/fail gate, because approved seat canonicalization changes `option_id` / `choice_id` values. Required pass/fail gate is a seat-aware allowlisted diff (`scripts/seat-canonicalization-diff.mjs` or equivalent checked-in helper) that fails on any non-seat drift and on any unapproved seat-price/default/standard-equipment grouping drift.

Expected contract result:

- Approved ID/key drift is limited to the exact seat migration map above.
- Approved standard-equipment grouping drift is limited to 1LT/2LT AQ9 and 3LT AH2 seat rows moving/normalizing to canonical `sec_seat_002` / `Seats` as described above.
- Customer-facing RPOs, labels, availability, prices, default selections, interiors, order summary, build download, and dealer payload behavior should be equivalent.
- Any non-seat behavior drift is a blocker.

Targeted tests:

```sh
node --test tests/nonruntime-option-source-purge.test.mjs
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
node --test tests/workbook-schema-standardization.test.mjs
node --test tests/workbook-visual-copy-standardization.test.mjs
.venv/bin/python -m pytest tests/test_schema_validation_metadata.py tests/test_registry_promotion_metadata.py -q
```

Manual/browser verification:

- Stingray 1LT/2LT/3LT seat step:
  - standard/default seat preselection still correct.
  - seat switching still works.
  - prices match prior behavior for AQ9/AH2/AE4/AUP by trim.
- Standard equipment/trim summary:
  - standard seats still visible where expected.
  - connected-service/tech standard rows still visible.
- Build download/dealer modal:
  - selected seat and standard-equipment summary still customer-equivalent.
  - do not submit live dealer payload.

## Risks

- Stingray currently uses duplicate option IDs to encode trim-specific seat pricing and standard-equipment presentation. Collapsing rows without price rules will break seat prices.
- `section_presentation.standard_equipment_bucket` is section-scoped and affects step routing. It is not safe to mark `sec_seat_002` as a standard-equipment bucket just to preserve standard-equipment grouping.
- Standard-equipment row `equipment_id` / `option_id` may change during canonicalization. Treat user-visible behavior as the primary contract, but report any payload/key drift explicitly.
- Active `sec_tech_001` rows are not duplicate seat rows. Deleting them would remove visible standard equipment unless a new workbook owner is designed.

## Non-Goals

- No active connected-service / `sec_tech_001` row deletion.
- No new standard-equipment source sheet or metadata extension in this pass.
- No runtime JS hardcodes.
- No Grand Sport/Z06 seat row rewrite unless a preflight proves they are needed for parity.
- No broad standard-equipment redesign.
- No generated artifact hand edits.

## Approval Question

Approve a Stingray-first active seat canonicalization pass scoped above, with active connected-service / standard-tech rows explicitly deferred?

Recommended answer: approve this limited Stingray seat pass first. It aligns Stingray with the Grand Sport/Z06 canonical seat shape while avoiding a broader standard-equipment owner redesign.
