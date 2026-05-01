# Stingray Generator Patch Extraction Phase 2 Spec

## Goal

Add the smallest workbook schema support needed to move the next Stingray-only generator corrections into visible workbook data while preserving generated Stingray output exactly except timestamps.

Phase 2 is schema-lite only. It does not add support sheets, runtime behavior, UI changes, Grand Sport cleanup, alias normalization, choice-group schema, color override normalization, or full interior component metadata.

## Current Python-Bound Corrections

- `price_rules`: generated B6P/ZZ3 engine-cover override rows need `body_style_scope`.
- `lt_interiors`: `active_for_stingray`, `requires_r6x`, and R6X include-rule derivation are still inferred in Python.
- `stingray_master`: option display behavior still relies on Python constants for `auto_only`; hidden/display-only behavior needs one explicit workbook field.

## Workbook Schema Changes

### `price_rules`

Add column:

| column | type | allowed values | blank meaning |
| --- | --- | --- | --- |
| `body_style_scope` | text enum | `coupe`, `convertible`, blank | applies to all body styles |

No other `price_rules` columns in Phase 2.

Example rows to add after the column exists:

| price_rule_id | condition_option_id | price_rule_type | target_option_id | price_value | body_style_scope | review_flag | notes |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| `pr_b6p_coupe_opt_bc4_001_001` | `opt_b6p_001` | `override` | `opt_bc4_001` | `595` | `coupe` | `False` | `B6P selected sets coupe LS6 engine cover price to 595` |
| `pr_zz3_convertible_opt_bc4_001_001` | `opt_zz3_001` | `override` | `opt_bc4_001` | `595` | `convertible` | `False` | `ZZ3 selected sets convertible LS6 engine cover price to 595` |

Repeat the same B6P/ZZ3 pattern for `opt_bcp_001` and `opt_bcs_001`.

Generator read:

- Continue reading existing source fields.
- Read `row.get("body_style_scope", "")` instead of relying on generated engine-cover rows.
- Preserve current output fields: `body_style_scope`, `trim_level_scope`, `variant_scope`; keep `trim_level_scope` and `variant_scope` as blank output fields until a later schema pass.

Removable after timestamp-only diff:

- The generated engine-cover price-rule append block for `pr_b6p_coupe_*` and `pr_zz3_convertible_*`.
- Do not remove `CONSOLIDATED_ENGINE_COVERS`; it is still needed for price normalization/status merge/rule suppression until alias/consolidation schema exists.

### `lt_interiors`

Add columns:

| column | type | allowed values | blank meaning |
| --- | --- | --- | --- |
| `active_for_stingray` | boolean text | `True`, `False` | generator may fall back to current inferred behavior during migration only |
| `requires_r6x` | boolean text | `True`, `False` | generator may fall back to current inferred behavior during migration only |
| `included_option_id` | option id text | blank, `opt_r6x_001` | no auto-included option |

Do not add `model_scope` in Phase 2. `active_for_stingray` is the narrowest field needed to preserve current Stingray output and avoid Grand Sport cleanup scope.

Example rows:

| interior_id | active_for_stingray | requires_r6x | included_option_id |
| --- | --- | --- | --- |
| `3LT_AE4_EL9` | `False` | `False` | blank |
| `3LT_AH2_EL9` | `False` | `False` | blank |
| `3LT_R6X_AH2_HVV` | `True` | `True` | `opt_r6x_001` |
| `3LT_R6X_AE4_HUU` | `True` | `True` | `opt_r6x_001` |

Data fill rule:

- Set `active_for_stingray=True` for current active Stingray LT interiors.
- Set `active_for_stingray=False` for `3LT_AE4_EL9` and `3LT_AH2_EL9`.
- Set `requires_r6x=True` and `included_option_id=opt_r6x_001` for current active R6X interiors.
- Set `requires_r6x=False` and blank `included_option_id` for non-R6X interiors.

Generator read:

- Prefer `active_for_stingray` when nonblank; fall back to current trim/interior-id inference only during the migration commit.
- Prefer `requires_r6x` when nonblank; fall back to current `_R6X` inference only during the migration commit.
- Build dynamic `includes opt_r6x_001` rules from `included_option_id` for active interiors.
- Keep `LZ_Interiors` inactive as-is; do not add Grand Sport activation logic.

Removable after timestamp-only diff:

- `GRAND_SPORT_ONLY_INTERIOR_IDS`.
- The hardcoded LT active expression `trim in {"1LT", "2LT", "3LT", "3LT_R6X"} and interior_id not in GRAND_SPORT_ONLY_INTERIOR_IDS`.
- The `_R6X`-based `requires_r6x` derivation for `lt_interiors`.
- The dynamic R6X rule source condition based on `requires_r6x == "True"` should switch to `included_option_id`.

Retain after Phase 2:

- `r6x_price_component()`, `generated_interior_price()`, `INTERIOR_COMPONENT_LABELS`, and `interior_component_metadata()`.
- `LZ_Interiors` inactive handling.

### `stingray_master`

Add column:

| column | type | allowed values | blank meaning |
| --- | --- | --- | --- |
| `display_behavior` | text enum | `selectable`, `display_only`, `auto_only`, `hidden` | derive from existing `active`/`selectable` fields during migration only |

Allowed values:

- `selectable`: normal active selectable option.
- `display_only`: active and visible, not manually selectable.
- `auto_only`: unavailable/inactive in choices, but may be auto-added by rules.
- `hidden`: suppress from visible choices and skip rules/price rules that touch it.

Example rows:

| option_id | active | selectable | display_behavior |
| --- | --- | --- | --- |
| `opt_d30_001` | `True` | `False` | `display_only` |
| `opt_r6x_001` | `True` | `True` | `auto_only` |
| `opt_n26_001` | `False` | `True` | `hidden` |
| `opt_tu7_001` | `False` | `True` | `hidden` |
| `opt_zf1_001` | `False` | `True` | `hidden` |

For alias rows already hidden in Phase 1 (`opt_bc4_002`, `opt_bcp_002`, `opt_bcs_002`, `opt_bc7_002`), set `display_behavior=hidden`, but do not attempt alias removal or consolidation changes in Phase 2.

Generator read:

- Build `display_behavior_by_option_id` from raw `stingray_master` rows before canonicalization.
- For choices:
  - `display_only`: force `status=available`, `selectable=False`, `active=True`.
  - `auto_only`: force `status=unavailable`, `selectable=False`, `active=False`.
  - `hidden`: keep row suppressed from visible choices.
  - `selectable` or blank: use existing status/active/selectable behavior.
- For rules and price rules:
  - Replace `HIDDEN_OPTION_IDS` filtering with a workbook-derived `hidden_option_ids` set from `display_behavior=hidden`.
  - Apply the hidden check before or alongside canonical ID handling so hidden alias rows still suppress source workbook rows that explicitly reference alias IDs.

Removable after timestamp-only diff:

- `AUTO_ONLY_OPTION_IDS`.
- Any future `DISPLAY_ONLY_OPTION_IDS` branch should not return.
- Most `HIDDEN_OPTION_IDS` use can move to workbook-derived `hidden_option_ids`.

Retain after Phase 2:

- `OPTION_ID_ALIASES` and `canonical_option_id()`.
- `CONSOLIDATED_ENGINE_COVERS`.
- Any alias-specific or consolidation-specific logic not directly represented by `display_behavior`.
- `HIDDEN_SECTION_IDS` unless a later section-level display schema is approved.

## Generator Migration Plan

1. Add the columns above to the workbook and populate all required rows.
2. Teach the generator to read new fields with migration fallbacks still present.
3. Run the generator and compare generated output against HEAD with `generated_at` ignored.
4. If output is timestamp-only, remove only the Python constants/branches fully replaced by workbook data.
5. Run generator again and confirm timestamp-only generated diff.
6. Run the full test gate.

## Validation Checks

Workbook validation before generator cleanup:

- Assert no new sheets were added.
- Assert only these new columns were added:
  - `price_rules.body_style_scope`
  - `lt_interiors.active_for_stingray`
  - `lt_interiors.requires_r6x`
  - `lt_interiors.included_option_id`
  - `stingray_master.display_behavior`
- Assert `display_behavior` values are only blank, `selectable`, `display_only`, `auto_only`, `hidden`.
- Assert `price_rules.body_style_scope` values are only blank, `coupe`, `convertible`.
- Assert `lt_interiors.active_for_stingray` and `lt_interiors.requires_r6x` values are only blank, `True`, `False`.
- Assert every nonblank `lt_interiors.included_option_id` exists in `stingray_master.option_id`.
- Assert `opt_r6x_001` has `display_behavior=auto_only`.
- Assert `opt_d30_001` has `display_behavior=display_only`.
- Assert hidden Phase 1 IDs have `display_behavior=hidden`.
- Assert `3LT_AE4_EL9` and `3LT_AH2_EL9` have `active_for_stingray=False`.
- Assert every active R6X interior has `included_option_id=opt_r6x_001`.

Generated-output validation:

- `.venv/bin/python scripts/generate_stingray_form.py`
- Compare `form-output/stingray-form-data.json` with `generated_at` ignored.
- Compare the Stingray model block in `form-app/data.js` with `generated_at` ignored.
- Confirm `form-output/stingray-form-data.csv` is unchanged.
- Confirm Grand Sport generated artifacts are not changed by the Stingray pass.

Test gate:

- `node --test tests/stingray-form-regression.test.mjs`
- `node --test tests/stingray-generator-stability.test.mjs`
- `node --test tests/grand-sport-draft-data.test.mjs`
- `node --test tests/multi-model-runtime-switching.test.mjs`

## Rollback Risk

Risk level: medium.

Main risks:

- `display_behavior=hidden` can accidentally suppress rules or price rules if applied before canonicalization without preserving alias behavior.
- `active_for_stingray` can accidentally reactivate Grand Sport-only EL9 if blanks are treated as `True`.
- `included_option_id` can duplicate R6X include rules if the old `requires_r6x` dynamic path is not removed after parity is proven.
- Adding `body_style_scope` changes source ordering if workbook rows are appended in a different position than generated rows; preserve generated price-rule ordering or normalize ordering in the generator.

Rollback plan:

- Revert the generator patch first; migration fallbacks should make workbook columns inert.
- If needed, restore the workbook from git and rerun `.venv/bin/python scripts/generate_stingray_form.py`.
- Do not proceed to remove Python constants until a timestamp-only diff and full test pass have both been recorded.
