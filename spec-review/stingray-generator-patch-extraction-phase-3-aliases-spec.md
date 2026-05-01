# Stingray Generator Patch Extraction Phase 3 Alias Spec

## Goal

Move option alias and LS6 engine-cover consolidation behavior out of `scripts/generate_stingray_form.py` and into visible workbook data while preserving current generated Stingray output exactly except `generated_at`.

This phase is schema-lite for aliases only. It does not change runtime behavior, UI, exports, Grand Sport cleanup, broad rule migration, interior component schema, choice group schema, or color override handling.

## Recommendation

Use a new workbook sheet: `option_aliases`.

Do not put alias columns on `stingray_master`. Aliases describe relationships between source rows, statuses, rules, price rules, and model scope. A relationship sheet is cleaner, avoids repeating canonical IDs on every option row, and can later hold Grand Sport duplicate mappings without mutating the source option sheets.

## Workbook Schema

### New sheet: `option_aliases`

| column | allowed values | required | purpose |
| --- | --- | --- | --- |
| `source_option_id` | option id | yes | Raw workbook option id to canonicalize. |
| `canonical_option_id` | option id | yes | Generated option id used in form choices, rules, prices, exports. |
| `model_scope` | `stingray`, `grand_sport`, `all` | yes | Controls which model generator applies the alias. |
| `merge_status` | `best_status`, `canonical_only` | yes | How variant statuses are merged. |
| `merge_option_row` | `canonical_only`, `overlay_missing`, `ignore_source` | yes | How option row fields are selected. |
| `preserve_price` | `canonical`, `source`, `max`, `min` | yes | Which option row price wins after collapse. |
| `suppress_source_rules` | `True`, `False` | yes | Whether rules originating from the alias source row should be dropped after canonicalization. |
| `active` | `True`, `False` | yes | Allows disabling a mapping without deleting it. |
| `reason` | free text | no | Human-readable audit note. |

### Stingray rows

| source_option_id | canonical_option_id | model_scope | merge_status | merge_option_row | preserve_price | suppress_source_rules | active | reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `opt_bc4_002` | `opt_bc4_001` | `stingray` | `best_status` | `canonical_only` | `canonical` | `True` | `True` | `Collapse duplicate B6P/ZZ3 Blue LS6 engine cover row into canonical selectable cover.` |
| `opt_bcp_002` | `opt_bcp_001` | `stingray` | `best_status` | `canonical_only` | `canonical` | `True` | `True` | `Collapse duplicate B6P/ZZ3 Edge Red LS6 engine cover row into canonical selectable cover.` |
| `opt_bcs_002` | `opt_bcs_001` | `stingray` | `best_status` | `canonical_only` | `canonical` | `True` | `True` | `Collapse duplicate B6P/ZZ3 Sterling Silver LS6 engine cover row into canonical selectable cover.` |
| `opt_bc7_002` | `opt_bc7_001` | `stingray` | `best_status` | `canonical_only` | `canonical` | `False` | `True` | `Collapse convertible BC7 row into canonical BC7 option while preserving convertible availability.` |

## Generator Read Rules

Load active rows from `option_aliases` where `model_scope` is the current model key or `all`.

Build:

- `alias_to_canonical[source_option_id] = canonical_option_id`
- `canonical_to_aliases[canonical_option_id] = [source_option_id]`
- `alias_config_by_source[source_option_id] = row`

Validation before use:

- `source_option_id != canonical_option_id`.
- Every `source_option_id` exists in the current source option sheet.
- Every `canonical_option_id` exists in the current source option sheet.
- No active `source_option_id` maps to more than one canonical id for the same model.
- No alias cycles: canonical ids must not also be source aliases in the same active model scope.
- Allowed enum values only.

## Merge Semantics

### Option rows

Current Stingray parity should use `merge_option_row=canonical_only` and `preserve_price=canonical`.

Algorithm:

1. Read all raw option rows.
2. For each row, compute `generated_option_id = alias_to_canonical.get(option_id, option_id)`.
3. If the raw row is an alias source and `merge_option_row=canonical_only`, do not create or overwrite the generated option row from it.
4. Use the canonical source row as the generated option row.
5. Preserve canonical row fields including `price`, `section_id`, `selectable`, `display_order`, `display_behavior`, label, description, and detail text.

This removes the current special `CONSOLIDATED_ENGINE_COVERS` price override only after workbook canonical rows already contain the desired generated values. For current Stingray parity, `opt_bc4_001`, `opt_bcp_001`, and `opt_bcs_001` must remain priced at `695` in `stingray_master`.

### Variant statuses

`merge_status=best_status` means combine status cells for the canonical id plus all active aliases using the existing `best_status()` precedence.

Current Stingray parity:

- `opt_bc4_001`, `opt_bcp_001`, and `opt_bcs_001` keep availability from their `_002` alias rows where those rows carry availability.
- `opt_bc7_001` keeps convertible availability from `opt_bc7_002`.
- The current one-off branch that forces `opt_bc7_001` available on `c67` variants should be removable once alias status merge proves parity.

`canonical_only` is reserved for future aliases where alias status rows should not affect generated availability.

### Rules

Canonicalize `source_id` and `target_id` through `alias_to_canonical`.

After canonicalization:

- Drop a rule when its raw `source_id` is an alias row with `suppress_source_rules=True` and the rule would duplicate package/consolidation behavior already represented elsewhere.
- Keep rules when `suppress_source_rules=False`, but emit the canonical id.
- Preserve existing downstream filters for redundant same-section excludes, requires-any suppressions, and replacement behavior.

Current Stingray parity:

- Rules from `opt_bc4_002`, `opt_bcp_002`, and `opt_bcs_002` that require/exclude B6P are suppressed.
- `opt_bc7_002` rules can canonicalize to `opt_bc7_001` so the existing BC7/ZZ3 convertible requirement remains represented.
- Do not add new `rule_mapping` columns in Phase 3 unless implementation proves a specific rule cannot be represented by alias sheet semantics alone.

### Price rules

Canonicalize `condition_option_id` and `target_option_id` through `alias_to_canonical`.

After canonicalization:

- Drop exact duplicate price rules by `price_rule_id` only if duplicate IDs already exist.
- Otherwise preserve row order and values.

Current Stingray parity:

- Existing Phase 2 `price_rules` rows already target canonical engine-cover ids.
- No extra price-rule schema is needed in Phase 3.

### Exclusive group members

When building `form_exclusive_groups` and runtime `exclusiveGroups`, canonicalize each member id through `alias_to_canonical`, then de-duplicate while preserving first-seen order.

Current Stingray parity:

- `grp_ls6_engine_covers` remains `opt_bc7_001|opt_bcp_001|opt_bcs_001|opt_bc4_001`.
- No `_002` alias ids should appear in Stingray generated exclusive groups, choices, exports, or selected option output.

### Selected/export output

Generated choices, selected option state, order summaries, JSON exports, CSV exports, and app data should only use canonical option ids.

No runtime migration or alias-aware selection is required in Phase 3 because generated Stingray output already excludes alias ids.

## Grand Sport Preparation

The `model_scope` column allows Grand Sport aliases to be added later without changing the Phase 3 schema.

For Grand Sport, later rows can use:

- `model_scope=grand_sport`
- the same `source_option_id` and `canonical_option_id` pairs where appropriate
- potentially different `suppress_source_rules` values if Grand Sport source rules need preservation

Do not apply Stingray aliases to Grand Sport unless `model_scope=all` is explicitly chosen. For Phase 3, use `model_scope=stingray` only.

## Python Removals After Proven Parity

Remove after generated Stingray diff is timestamp-only:

- `OPTION_ID_ALIASES`
- `canonical_option_id()` hardcoded dictionary behavior, replacing it with workbook-driven lookup
- `CONSOLIDATED_ENGINE_COVERS`
- The canonical cover price override `if option_id in CONSOLIDATED_ENGINE_COVERS: option["price"] = "695"`
- The hardcoded alias status merge expression `f"{row['option_id'][:-3]}002"`
- The BC7 convertible availability branch
- The hardcoded stale consolidated-cover/B6P rule suppression keyed to `CONSOLIDATED_ENGINE_COVERS`

Retain:

- Generic alias lookup helpers backed by `option_aliases`
- Generic status merge using `best_status()`
- Existing non-alias rule filters: requires-any suppressions, redundant same-section excludes, and T0A replacement logic
- Phase 2 `display_behavior` handling

## Safety Sequence

1. Add `option_aliases` with the four Stingray rows above.
2. Teach generator to load aliases and compute canonical ids from the workbook.
3. Keep old Python constants active as fallback only.
4. Run `.venv/bin/python scripts/generate_stingray_form.py`.
5. Compare generated Stingray JSON with `generated_at` ignored; compare app Stingray block similarly; confirm CSV unchanged.
6. Remove hardcoded alias/consolidation constants and branches listed above.
7. Regenerate and confirm timestamp-only generated diff again.
8. Run full test gate.

## Validation Checks

Workbook checks:

- `option_aliases` exists with exactly the approved columns.
- Only active rows with `model_scope in {"stingray", "all"}` are used for Stingray.
- All enum fields are valid.
- Source and canonical option ids exist in `stingray_master`.
- No duplicate active `source_option_id` for Stingray.
- No alias cycles.
- Current four Stingray aliases are present and active.
- Canonical engine-cover rows have the current generated prices:
  - `opt_bc4_001.price=695`
  - `opt_bcp_001.price=695`
  - `opt_bcs_001.price=695`

Generated checks:

- No generated Stingray choice uses an `_002` engine-cover id.
- `opt_bc4_001`, `opt_bcp_001`, `opt_bcs_001`, and `opt_bc7_001` retain current availability by variant.
- `grp_ls6_engine_covers` members remain unchanged.
- BC7 convertible ZZ3 requirement remains present.
- Engine-cover scoped price rules remain unchanged.
- `form-output/stingray-form-data.json` differs only by `generated_at`.
- `form-output/stingray-form-data.csv` has no diff.
- Grand Sport artifacts are not changed by the Stingray pass.

Test gate:

- `node --test tests/stingray-form-regression.test.mjs`
- `node --test tests/stingray-generator-stability.test.mjs`
- `node --test tests/grand-sport-draft-data.test.mjs`
- `node --test tests/multi-model-runtime-switching.test.mjs`

## Rollback Risk

Risk level: medium-high.

Main risks:

- Incorrect status merge can make engine-cover options unavailable or over-available.
- Suppressing alias source rules too broadly can remove the BC7/ZZ3 convertible requirement.
- Canonicalizing rules without de-duplication can create duplicate runtime rules.
- Applying Stingray aliases to Grand Sport accidentally can change Grand Sport draft output.
- Removing `CONSOLIDATED_ENGINE_COVERS` before canonical rows carry the correct workbook price can change LS6 cover pricing.

Rollback plan:

- Revert generator changes first; the new `option_aliases` sheet is inert until read.
- If workbook rollback is needed, remove only `option_aliases`.
- Re-run `.venv/bin/python scripts/generate_stingray_form.py` and confirm generated output returns to timestamp-only baseline.
