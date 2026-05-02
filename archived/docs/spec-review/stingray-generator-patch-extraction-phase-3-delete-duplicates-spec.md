# Stingray Generator Patch Extraction Phase 3 Delete-Duplicates Spec

## Goal

Remove duplicate Stingray LS6 engine-cover source rows from workbook data and then remove the Python alias/consolidation logic that only exists to compensate for those duplicates.

This replaces the alias-sheet approach. Do not create `option_aliases`, canonical alias logic, source/canonical ID mapping, suppress-source-rule logic, or alias-aware runtime behavior.

## Scope

In scope:

- Delete duplicate Stingray engine-cover source rows.
- Transfer any needed availability/status/rule behavior into canonical `_001` rows before deletion.
- Preserve generated Stingray output exactly except `generated_at`.
- Remove now-obsolete Python alias/consolidation branches only after parity is proven.

Out of scope:

- Runtime/UI/export changes.
- Grand Sport cleanup.
- Broad rule migration.
- Interior component schema.
- Choice group schema.
- Color override changes.

## Duplicate IDs

Delete these duplicate Stingray source IDs:

- `opt_bc4_002`
- `opt_bcp_002`
- `opt_bcs_002`
- `opt_bc7_002`

Keep only:

- `opt_bc4_001`
- `opt_bcp_001`
- `opt_bcs_001`
- `opt_bc7_001`

## Where Duplicate IDs Currently Exist

Source workbook references found:

- `stingray_master`
  - one row each for `opt_bc4_002`, `opt_bcp_002`, `opt_bcs_002`, `opt_bc7_002`
- `option_variant_status`
  - six rows per duplicate ID, 24 rows total
- `rule_mapping`
  - `opt_bc4_002`: requires `opt_b6p_001`, requires `opt_zz3_001`
  - `opt_bcp_002`: requires `opt_b6p_001`, requires `opt_zz3_001`
  - `opt_bcs_002`: requires `opt_b6p_001`, requires `opt_zz3_001`
  - `opt_bc7_002`: included by `opt_zz3_001`
- Generated/reference-only surfaces:
  - `form_rules` contains generated rows derived from `_002` source rules.
  - `stingray` and `grandSport` source sheets contain some `_002` IDs, but this Phase 3 cleanup targets the Stingray operational source sheets listed above. Do not mutate Grand Sport source data in this pass.

No `_002` references are needed in `price_rules`; current price rules already target canonical `_001` IDs.

## Transfer Plan Before Deletion

### `stingray_master`

Delete these rows:

- `opt_bc4_002`
- `opt_bcp_002`
- `opt_bcs_002`
- `opt_bc7_002`

Keep canonical rows and verify they contain current generated values:

| option_id | price | section_id | selectable | display_order | active | display_behavior |
| --- | ---: | --- | --- | ---: | --- | --- |
| `opt_bc7_001` | `0` | `sec_engi_001` | `True` | `10` | `True` | blank |
| `opt_bcp_001` | `695` | `sec_engi_001` | `True` | `20` | `True` | blank |
| `opt_bcs_001` | `695` | `sec_engi_001` | `True` | `30` | `True` | blank |
| `opt_bc4_001` | `695` | `sec_engi_001` | `True` | `40` | `True` | blank |

Do not copy duplicate `_002` labels or detail text into canonical rows unless parity fails. Current canonical detail behavior is already the generated source truth:

- canonical BC4/BCP/BCS rows include D3V and “without B6P”
- B6P/ZZ3 scoped pricing is represented in `price_rules`
- BC7 convertible behavior is represented by status rows and the explicit BC7/ZZ3 rule

### `option_variant_status`

Delete all 24 `_002` rows after transfer.

Transfer status information to canonical rows:

- `opt_bc4_001`: set convertible variants `1lt_c67`, `2lt_c67`, `3lt_c67` from `unavailable` to `available`.
- `opt_bcp_001`: set convertible variants `1lt_c67`, `2lt_c67`, `3lt_c67` from `unavailable` to `available`.
- `opt_bcs_001`: set convertible variants `1lt_c67`, `2lt_c67`, `3lt_c67` from `unavailable` to `available`.
- `opt_bc7_001`: set convertible variants `1lt_c67`, `2lt_c67`, `3lt_c67` from `unavailable` to `available`.

Leave coupe status as-is:

- `opt_bc7_001` remains `standard` on coupe.
- BC4/BCP/BCS remain `available` on coupe.

This transfer replaces the current Python status merge and the BC7 convertible availability branch.

### `rule_mapping`

Delete duplicate-source package rules:

- `rule_opt_bc4_002_requires_opt_b6p_001`
- `rule_opt_bc4_002_requires_opt_zz3_001`
- `rule_opt_bcp_002_requires_opt_b6p_001`
- `rule_opt_bcp_002_requires_opt_zz3_001`
- `rule_opt_bcs_002_requires_opt_b6p_001`
- `rule_opt_bcs_002_requires_opt_zz3_001`

Do not move these to canonical rows. Their behavior is already represented by:

- canonical BC4/BCP/BCS base price `695`
- existing B6P/ZZ3 scoped price rules setting BC4/BCP/BCS to `595`
- existing canonical BC4/BCP/BCS include-D3V rules
- existing canonical BC4/BCP/BCS “without B6P” rules, with redundant same-section behavior already handled by generator filtering

Replace the BC7 duplicate target rule:

- Delete `rule_opt_zz3_001_includes_opt_bc7_002`.
- Ensure canonical rule `rule_opt_bc7_001_requires_opt_zz3_001_convertible` remains present and active in source `rule_mapping`.

Do not add a new ZZ3 includes BC7 rule unless parity proves it is required. Current generated output already relies on the canonical BC7/ZZ3 convertible requirement row, not a visible `_002` target.

### `price_rules`

No `_002` rows should exist. Verify only.

Keep canonical rows:

- `pr_b6p_coupe_opt_bc4_001_001`
- `pr_zz3_convertible_opt_bc4_001_001`
- `pr_b6p_coupe_opt_bcp_001_001`
- `pr_zz3_convertible_opt_bcp_001_001`
- `pr_b6p_coupe_opt_bcs_001_001`
- `pr_zz3_convertible_opt_bcs_001_001`
- canonical D3V price rules for BC4/BCP/BCS

## Behavior That Must Remain

### BC7 convertible / ZZ3

After deleting `opt_bc7_002`:

- `opt_bc7_001` must be `available` on convertible variants.
- `rule_opt_bc7_001_requires_opt_zz3_001_convertible` must remain in `rule_mapping`.
- Generated rule output must still contain the BC7 convertible-only ZZ3 requirement.
- The Python branch forcing BC7 convertible status can be removed only after the canonical status rows prove parity.

### LS6 exclusive group

The LS6 engine-cover exclusive group must remain exactly:

- `opt_bc7_001`
- `opt_bcp_001`
- `opt_bcs_001`
- `opt_bc4_001`

No `_002` IDs should appear in generated `exclusiveGroups`, `form_exclusive_groups`, choices, order output, CSV, or app exports.

## Python Removals After Parity

Remove only after generated Stingray output is timestamp-only:

- `OPTION_ID_ALIASES`
- hardcoded `canonical_option_id()` dictionary behavior
- `CONSOLIDATED_ENGINE_COVERS`
- canonical cover price override for consolidated covers
- hardcoded `_002` status merge expression
- BC7 convertible availability branch, if canonical status rows now represent it
- stale consolidated-cover/B6P rule suppression keyed to `CONSOLIDATED_ENGINE_COVERS`

Retain:

- Phase 2 `display_behavior` handling.
- Existing non-engine-cover rule filters: requires-any suppressions, redundant same-section excludes, T0A replacement behavior.
- Existing `price_rules.body_style_scope` handling.

## Implementation Safety Sequence

1. Inspect all workbook references to the four duplicate IDs.
2. Build row-level transfer plan:
   - canonical status updates
   - duplicate source row deletions
   - duplicate status row deletions
   - duplicate rule row deletions/replacements
3. Update canonical rows/statuses/rules as needed.
4. Delete duplicate rows from source workbook sheets.
5. Reopen workbook and verify no `_002` rows remain in `stingray_master`, `option_variant_status`, `rule_mapping`, or `price_rules`.
6. Run `.venv/bin/python scripts/generate_stingray_form.py`.
7. Confirm generated output is unchanged except `generated_at`.
8. Remove now-obsolete Python alias/consolidation logic.
9. Regenerate.
10. Confirm generated output is unchanged except `generated_at`.
11. Run the full test gate.

## Validation Requirements

Workbook validation:

- No rows remain for `opt_bc4_002`, `opt_bcp_002`, `opt_bcs_002`, or `opt_bc7_002` in:
  - `stingray_master`
  - `option_variant_status`
  - `rule_mapping`
  - `price_rules`
- Canonical BC4/BCP/BCS prices remain `695`.
- Canonical BC7 price remains `0`.
- Canonical BC4/BCP/BCS are `available` on all six Stingray variants.
- Canonical BC7 is `standard` on coupe and `available` on convertible.
- `rule_opt_bc7_001_requires_opt_zz3_001_convertible` remains present.
- No `price_rules` row references a duplicate `_002` ID.

Generated validation:

- No generated choice, rule, price rule, exclusive group, compact order, or export references:
  - `opt_bc4_002`
  - `opt_bcp_002`
  - `opt_bcs_002`
  - `opt_bc7_002`
- Canonical engine-cover rows retain current prices.
- Canonical engine-cover rows retain current variant availability.
- BC7 convertible requirement/availability remains correct.
- LS6 engine-cover exclusive group remains `opt_bc7_001`, `opt_bcp_001`, `opt_bcs_001`, `opt_bc4_001`.
- `form-output/stingray-form-data.json` differs only by `generated_at`.
- `form-output/stingray-form-data.csv` has no functional diff.
- Grand Sport artifacts are not changed by this Stingray cleanup.

Test gate:

- `.venv/bin/python scripts/generate_stingray_form.py`
- `node --test tests/stingray-form-regression.test.mjs`
- `node --test tests/stingray-generator-stability.test.mjs`
- `node --test tests/grand-sport-draft-data.test.mjs`
- `node --test tests/multi-model-runtime-switching.test.mjs`

## Rollback Risk

Risk level: medium.

Main risks:

- Missing a status transfer can make canonical engine covers unavailable on convertible.
- Deleting the BC7/ZZ3 duplicate target rule before confirming canonical BC7/ZZ3 requirement parity can change convertible validation.
- Removing `CONSOLIDATED_ENGINE_COVERS` before verifying canonical prices can change BC4/BCP/BCS pricing.
- Accidentally deleting Grand Sport duplicate rows would change Grand Sport draft output; do not touch `grandSport` in this phase.

Rollback plan:

- Revert generator changes first.
- Restore deleted workbook rows from git if parity fails.
- Regenerate with `.venv/bin/python scripts/generate_stingray_form.py`.
- Confirm generated output returns to timestamp-only baseline before trying a narrower cleanup.
