# Rule Normalization Pass 4 — Price Rule Semantic Classification Spec

> Status: implemented after approval. Workbook source sheets now carry `price_semantic` metadata; runtime price-rule emission remains unchanged.

## Goal

Normalize price-rule modeling semantics across Stingray, Grand Sport, and Z06 without changing the runtime pricing engine or product prices.

The current runtime contract is intentionally simple: every emitted price rule is `price_rule_type = override`, and `form-app/app.js` returns the first scoped matching override for a target option. That implementation should remain unchanged in this pass.

The problem is that workbook price rules now use the same generic override shape for several different business meanings:

- included-equipment zeroing, where an included target should not double-charge;
- conditional component/package discounts, where a selected source changes the target's displayed price;
- package price varies by selected component, especially Z06 PDB/PDD/PDF with ROY/ROZ/STZ;
- self/trim-scoped option price overrides, such as seat or UQT price by trim;
- possible legacy zero overrides that are behaviorally valid but semantically unclear from row data alone.

Pass 4 should add workbook-owned semantic classification directly to the existing `*_price_rules` sheets, so audits and tests can distinguish those meanings while the generated runtime data continues to emit the existing `override` rules.

This is a structure/readiness pass. Do not change customer-facing prices unless a row is proven to be semantically misclassified or self-contradictory and the correction is explicitly in scope.

## Diagnosis

### Root cause

After Passes 1-3, rule/exclusive/default behavior is much more canonical. Price rules remain structurally flat. Every current model price-rule sheet uses the same header shape:

```text
price_rule_id, condition_option_id, price_rule_type, target_option_id, price_value,
body_style_scope, trim_level_scope, review_flag, notes
```

That shape is sufficient for runtime evaluation, but insufficient for workbook review. A `price_rule_type = override` row can mean either:

1. "source includes target; target price becomes $0 to avoid double charge";
2. "source changes target price to a nonzero discounted/adjusted amount";
3. "component selection determines visible package price";
4. "target option's own trim-scoped price differs from its base price".

The workbook already has the owning sheet: `*_price_rules`. Adding a semantic metadata column to those sheets is preferable to adding a parallel review sheet or model-specific runtime logic.

### Evidence inspected

Files/docs:

- `AGENTS.md`
- `codex-context.md`
- `docs/hermes-plans/rule-normalization-pass3-z06-replace-defaults.md`
- `27vette-workbook-guard/references/rule-exclusive-price-normalization.md`
- `27vette-workbook-guard/references/z06-package-combo-pricing.md`
- `27vette-workbook-guard/references/z-option-pricing-section-repair.md`

Runtime/generator surfaces:

- `form-app/app.js`
  - `optionPrice()` currently reads `priceRulesByTarget`, checks variant/body/trim scope, and applies `price_rule_type = override` when `condition_option_id` is selected.
- `form-app/data.js`
  - generated runtime price rules already emit `price_rule_type` and `price_value`.
- `scripts/generate_stingray_form.py` and shared generator helpers that load workbook `*_price_rules` into generated data.
- `tests/stingray-generator-stability.test.mjs`
- `tests/grand-sport-draft-data.test.mjs`
- `tests/z06-form-data-draft.test.mjs`
- `tests/z06-performance-package-interactions.test.mjs`
- `tests/z06-runtime-rule-corrections.test.mjs`
- `tests/workbook-schema-standardization.test.mjs`

Workbook sheets inspected:

- `price_rules`
- `grandSport_price_rules`
- `z06_price_rules`
- `zr1_price_rules`
- `zr1x_price_rules`
- corresponding option sheets for source/target RPO identification

Current active price-rule counts observed:

| Model | Active price rules | Notes |
| --- | ---: | --- |
| Stingray | 42 | mostly included-zero and LS6 engine-cover component price overrides |
| Grand Sport | 45 | included-zero, LS6 component price overrides, self/trim seat price rows |
| Z06 | 45 | BCW discounts, included-zero rows, package-by-wheel prices, self/trim rows |
| ZR1 | 0 | source sheet exists but no active price rules |
| ZR1X | 0 | source sheet exists but no active price rules |

Read-only semantic classification snapshot:

| Model | Included-zero | Conditional component price | Package price by component | Self/trim price | Unclear zero |
| --- | ---: | ---: | ---: | ---: | ---: |
| Stingray | 35 | 6 | 0 | 0 | 1 (`Z51 -> TVS = 0`) |
| Grand Sport | 32 | 6 | 0 | 4 | 3 (`B6P/ZZ3 -> D3V/SL9 = 0` rows with blank notes) |
| Z06 | 31 | 2 | 9 | 3 | 0 |
| ZR1 | 0 | 0 | 0 | 0 | 0 |
| ZR1X | 0 | 0 | 0 | 0 | 0 |

Important Z06 examples:

- Included-zero:
  - `T0F -> CFZ = 0`
  - `T0G -> CFV = 0`
  - `Z07 -> J57 = 0`
  - `PDB/PDD/PDF -> included components = 0`
- Package price varies by component:
  - `ROY -> PDB = 16000`
  - `ROZ -> PDB = 17000`
  - `STZ -> PDB = 17500`
  - `ROY -> PDD = 25495`
  - `ROZ -> PDD = 26495`
  - `STZ -> PDD = 26995`
  - `ROY -> PDF = 26495`
  - `ROZ -> PDF = 27495`
  - `STZ -> PDF = 27995`
- Conditional component price:
  - `B6P -> BCW = 895` for coupe
  - `ZZ3 -> BCW = 895` for convertible
- Self/trim price:
  - `AH2 -> AH2 = 0` on 3LZ
  - `AE4 -> AE4 = 595` on 3LZ
  - `UQT -> UQT = 1495` on 1LZ

## Proposed scope

### In scope

1. Add semantic metadata directly to all model price-rule sheets, not to a parallel taxonomy.

   Proposed new column:

   ```text
   price_semantic
   ```

   Allowed values:

   - `included_zero`
     - Source includes target, so the target should price at 0 while included/auto-added.
   - `conditional_component_price`
     - Source condition changes a separately selectable/displayed component target to a nonzero price.
   - `package_price_by_component`
     - Selected component/wheel changes the visible package row price.
   - `self_trim_price`
     - Condition and target are the same option, with body/trim/variant scope changing that option's own effective price.
   - `review_required`
     - Temporary classification for rows that are valid runtime overrides but not safely classifiable from current workbook evidence.

   Do not add a new sheet. Do not add a JavaScript enum. Keep the semantic owner in the workbook price-rule row.

2. Add schema/test guards for semantic classification.

   RED guard should fail before implementation because `price_semantic` is currently absent.

   Guard expectations:

   - Every populated row in `price_rules`, `grandSport_price_rules`, `z06_price_rules`, `zr1_price_rules`, and `zr1x_price_rules` has the `price_semantic` header once the migration lands.
   - Every active row with `price_rule_type = override` has a nonblank allowed `price_semantic`.
   - `price_semantic = included_zero` must have `price_value = 0`.
   - `price_semantic = package_price_by_component` must target a package-like row and should have nonzero `price_value` unless explicitly reviewed.
   - `price_semantic = self_trim_price` must have `condition_option_id == target_option_id` and a nonblank body/trim/variant scope.
   - `price_semantic = review_required` is allowed only with `review_flag = True` and a note explaining what needs human/product confirmation.

3. Classify current rows without changing the runtime price result.

   Initial target classifications:

   - Stingray:
     - Most `price_value = 0` rows with include/included notes -> `included_zero`.
     - B6P/ZZ3 LS6 engine-cover $595 rows -> `conditional_component_price`.
     - `Z51 -> TVS = 0` should be reviewed carefully. If it represents selected source changing target price to zero but not an include, classify as `conditional_component_price`; if it represents included-equipment zeroing, classify as `included_zero`; otherwise mark `review_required` and do not change behavior.
   - Grand Sport:
     - FEY/PCQ/PEF/interior/PDY include rows -> `included_zero`.
     - B6P/ZZ3 LS6 engine-cover $595 rows -> `conditional_component_price`.
     - Seat self/trim rows -> `self_trim_price`.
     - Blank-note B6P/ZZ3 -> D3V/SL9 zero rows should be classified only after confirming they are included-zero from matching rules/notes; otherwise mark `review_required`.
   - Z06:
     - T0F/T0G/Z07/PDB/PDD/PDF package-included component zero rows -> `included_zero`.
     - BCW $895 body-scoped rows -> `conditional_component_price`.
     - ROY/ROZ/STZ -> PDB/PDD/PDF package price rows -> `package_price_by_component`.
     - AH2/AE4/UQT self/trim rows -> `self_trim_price`.
   - ZR1/ZR1X:
     - Add the column/header if absent to preserve schema parity, but do not invent price rows.

4. Keep generated runtime contract stable unless an existing test proves metadata should be emitted.

   Preferred implementation: `price_semantic` stays workbook/audit metadata and is not emitted to live `form-app/data.js` unless tests establish a need. Runtime only needs `price_rule_type = override`, `price_value`, scope, condition, and target.

   If draft/inspection artifacts already preserve source metadata for audit, emitting `price_semantic` there is acceptable, but strip it from live app data unless runtime uses it.

5. Add or update audit/readability tests.

   Tests should make the business meaning visible without relying on comments alone:

   - Z06 package price rows are explicitly `package_price_by_component`.
   - Z06 included component zero rows are explicitly `included_zero`.
   - Z06 BCW body-scoped rows are explicitly `conditional_component_price`.
   - Grand Sport seat rows are `self_trim_price`.
   - `review_required` rows, if any, are counted and reported with row IDs.

### Out of scope

- Do not change price numbers in this pass unless a row is self-contradictory and the spec is amended before implementation.
- Do not rewrite `form-app/app.js` pricing logic.
- Do not add model/RPO-specific JavaScript pricing exceptions.
- Do not introduce a new price-review sheet or parallel taxonomy.
- Do not solve all Z06 user-facing product-rule bugs.
- Do not repair option-sheet base prices from CSV/backups in this pass.
- Do not promote ZR1 or ZR1X.
- Do not change dealer submission, Turnstile, styling, deployment, or export payload shape.

## Exact files and sheets likely to change

### Workbook source

`stingray_master.xlsx`:

- `price_rules`
- `grandSport_price_rules`
- `z06_price_rules`
- `zr1_price_rules`
- `zr1x_price_rules`

Likely workbook operation:

- Add `price_semantic` header to each model price-rule sheet.
- Populate existing active rows with allowed semantic values.
- Preserve existing `price_rule_id`, condition/target IDs, price values, scopes, review flags, and notes.

### Generator/schema/tests

Likely modify:

- `scripts/corvette_form_generator/schema_validation.py`
  - Add allowed price semantic validation.
  - Validate semantic/value/target invariants.
- Generator helpers only if header parsing assumes the exact old price-rule schema.
  - If `rows_from_sheet()` already tolerates extra columns, generator changes may be unnecessary.
- `tests/workbook-schema-standardization.test.mjs`
  - Add RED/GREEN guard for price-rule semantic columns and allowed values.
  - Update price-rule header parity expectations if needed.
- `tests/z06-form-data-draft.test.mjs`
  - Assert Z06 package/component price-rule semantics at the source/audit level or generated draft level, depending on whether draft emits semantic metadata.
- `tests/grand-sport-draft-data.test.mjs`
  - Assert Grand Sport self/trim and included-zero classifications if generated draft exposes metadata.
- `tests/stingray-generator-stability.test.mjs`
  - Assert generated runtime price output is unchanged except timestamps if semantics are workbook-only.

### Generated artifacts

Only after approved workbook writes:

- `form-output/inspection/z06-form-data-draft.json`
- `form-output/inspection/z06-form-data-draft.md`
- possibly Grand Sport inspection/draft artifacts if the generator emits semantic metadata there
- `form-output/stingray-form-data.json`
- `form-app/data.js` only if regeneration naturally rewrites it; payload should remain price-equivalent
- generated `form_*` workbook sheets inside `stingray_master.xlsx` if the production generator saves them

Restore unrelated timestamp-only generated churn before handoff.

## Implementation approach after approval

### Step 1 — Preflight

Run from repo root:

```sh
git branch --show-current
git status --short --branch
if [ -e './~$stingray_master.xlsx' ]; then echo LOCK_PRESENT; else echo NO_LOCK_FILE; fi
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Stop before workbook writes if there is an Excel lock file or unrelated tracked churn.

### Step 2 — RED guard

Add a test/validator guard that fails because `price_semantic` is absent from current price-rule sheets.

The failure should report:

- sheet name;
- row number;
- `price_rule_id`;
- condition RPO / target RPO;
- current `price_value`;
- candidate semantic inferred from current evidence;
- reason if inference is ambiguous.

Do not write workbook data until the RED failure is observed.

### Step 3 — Classification design

Before writing, produce a dry-run classification report with these buckets:

```text
included_zero
conditional_component_price
package_price_by_component
self_trim_price
review_required
```

The report should list every `review_required` row explicitly and should not silently guess based on price value alone.

Recommended inference order:

1. `condition_option_id == target_option_id` plus body/trim/variant scope -> `self_trim_price`.
2. Z06 ROY/ROZ/STZ condition targeting PDB/PDD/PDF package rows -> `package_price_by_component`.
3. `price_value = 0` plus matching `includes` rule or include/included note -> `included_zero`.
4. nonzero scoped condition/target override -> `conditional_component_price`.
5. otherwise -> `review_required`.

For included-zero detection, inspect corresponding `*_rule_mapping.includes` rows when notes are blank. Do not rely only on English note text if a workbook rule row can prove the relationship.

### Step 4 — Safe-save workbook migration

Use a narrow idempotent migration script or temporary command script that:

- Stops if `~$stingray_master.xlsx` exists.
- Loads workbook with `read_only=False` and captures `loaded_mtime_ns`.
- Adds only the approved `price_semantic` column to the five price-rule sheets if missing.
- Writes only `price_semantic` values and, if necessary, `review_flag=True` for `review_required` rows.
- Does not alter price values, condition IDs, target IDs, scopes, or existing notes unless explicitly approved.
- Refreshes table refs only for touched sheets if table refs exist.
- Uses `save_workbook_safely()`.
- Reopens the workbook and prints exact counts by sheet and semantic.

### Step 5 — Regenerate as needed

If the implementation changes only workbook metadata that the live runtime does not emit, still run validators and targeted tests. If generators read/save the workbook or generated artifacts include the metadata, regenerate appropriate outputs.

Expected commands for a Z06-promoted runtime refresh:

```sh
.venv/bin/python scripts/generate_z06_form.py
.venv/bin/python scripts/generate_stingray_form.py
```

Run Grand Sport generation only if generated Grand Sport draft artifacts intentionally expose or validate the new semantic field.

### Step 6 — GREEN tests and gates

Targeted gates:

```sh
node --test tests/workbook-schema-standardization.test.mjs
node --test tests/z06-form-data-draft.test.mjs
node --test tests/z06-performance-package-interactions.test.mjs
node --test tests/z06-runtime-rule-corrections.test.mjs
node --test tests/z06-runtime-promotion.test.mjs
```

If Grand Sport generated artifacts or tests are touched:

```sh
node --test tests/grand-sport-draft-data.test.mjs tests/grand-sport-rule-audit.test.mjs
```

Runtime/generator regression if `form-app/data.js` or generic generated price output changes:

```sh
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Python/workbook gates:

```sh
.venv/bin/python -m pytest tests -q
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
```

If runtime behavior remains price-equivalent, no browser smoke is required. If any runtime pricing logic changes despite this spec's preference, add a browser smoke around Z06 package/wheel price display.

## Acceptance criteria

- All model price-rule source sheets have a `price_semantic` column.
- Every active populated price-rule row has an allowed semantic value or a deliberately flagged `review_required` value.
- Z06 PDB/PDD/PDF package-by-ROY/ROZ/STZ rows are explicitly classified as `package_price_by_component`.
- Z06 package-included component zero rows are explicitly classified as `included_zero`.
- Grand Sport and Z06 self/trim rows are explicitly classified as `self_trim_price`.
- Runtime pricing output remains equivalent for all existing covered tests.
- No price values are changed without explicit approval.
- Workbook schema and package validators pass.
- Generated Z06/live app data remain synchronized if regeneration runs.
- No dealer submission, Turnstile, styling, deployment, ZR1 promotion, or ZR1X promotion changes are introduced.

## Risks

- Adding a new source column can break strict header-parity tests if all model price-rule sheets are not updated together.
- If semantic metadata is accidentally emitted into live app data, it may create unnecessary payload churn. Prefer workbook/test use unless runtime needs it.
- Some zero price rules may be valid but ambiguous from notes alone. Use existing `includes` rows and package/default structure before marking them `review_required`.
- Z06 package price rules are order-sensitive at runtime because `optionPrice()` returns the first scoped matching override for a target. Do not reorder price-rule rows casually.
- Classifying package-by-component prices does not prove the visible UX is perfect; it only makes the business meaning auditable.

## Non-goals

- This pass does not change the runtime price algorithm.
- This pass does not repair missing base prices from CSV/backups.
- This pass does not resolve every Z06 package-product bug.
- This pass does not add ZR1/ZR1X price rows.
- This pass does not retire one-pass scripts unless implementation discovers a stale writer directly threatens price metadata preservation.

## Follow-up after this pass

Recommended next pass after Pass 4 is a focused Z06 product-behavior correction pass against the now-normalized rule/default/price structure. That pass should use the user's observed Z06 issue list and fix behavior through canonical workbook rows first, only adding generic runtime support where workbook data already expresses the intended rule.
