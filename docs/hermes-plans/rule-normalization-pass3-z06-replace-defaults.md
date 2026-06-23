# Rule Normalization Pass 3 — Z06 Replace/Default Simplification Spec

> Status: approved and implemented on 2026-06-03. Keep as the Pass 3 implementation record.

## Goal

Normalize Z06 `runtime_action=replace` usage so `replace` remains only where it expresses true default replacement/removal behavior. Peer-choice switching, package wheel/aero selection, and one-source/many-target blockers should use the existing workbook-owned structures instead:

- `z06_exclusive_groups` + `z06_exclusive_members` for mutually exclusive peer choices.
- `z06_rule_groups.group_type = requires_any` for one-of requirements.
- `z06_rule_groups.group_type = excludes_any` for one-source/many-target blockers.
- `default_selection_rules` and generated default metadata for soft/default selections.
- Direct `z06_rule_mapping.excludes` with `runtime_action=replace` only when a selected option must remove a generated/default selected option and the relationship is not already better expressed by a group/default path.

This pass is structural cleanup before broader Z06 behavior fixes. Do not preserve current Z06 behavior merely because it is current; preserve only canonical workbook intent.

## Diagnosis

### Root cause

After Pass 1 and Pass 2, most redundant normal excludes have been moved toward canonical workbook groups. Z06 still has many active direct `excludes` rows with `runtime_action=replace`. Some represent legitimate default replacement, but many appear to encode radio/peer behavior that should be owned by existing Z06 exclusive groups and requirement groups.

Current workbook inspection shows:

- Stingray active replace excludes: 5.
  - `5ZU`, `5ZW`, `5ZZ`, `ZF1`, and `TVS` replacing `T0A`.
- Grand Sport active replace excludes: 7, with one already marked replaced/omitted by the brake exclusive group.
  - Examples: `J57 -> J6A`, `FEY -> T0E/JX6/J56`, `FEB -> JX6`, `NWI -> NGA`.
- Z06 active replace excludes: 82.
  - 27 rows where aluminum/default wheel choices replace carbon wheels (`ROU`, `ROX`, `SOA`, `SOE`, `SOM`, `SON`, `SRK`, `SRN`, `STX` -> `ROY`, `ROZ`, `STZ`).
  - 27 reciprocal rows where carbon wheels replace aluminum/default wheels (`ROY`, `ROZ`, `STZ` -> `ROU`, `ROX`, `SOA`, `SOE`, `SOM`, `SON`, `SRK`, `SRN`, `STX`).
  - 27 package rows where `PDB`, `PDD`, and `PDF` replace aluminum/default wheels.
  - 1 brake row: `J57 -> J6A`.

Z06 already has workbook-owned structures that overlap these behaviors:

- `z06_excl_carbon_wheel_packages`
  - members: `PDB`, `PDD`, `PDF`.
- `z06_group_pdb_requires_carbon_wheel`
  - requires one of `ROY`, `ROZ`, `STZ`.
- `z06_group_pdd_requires_carbon_wheel`
  - requires one of `ROY`, `ROZ`, `STZ`.
- `z06_group_pdf_requires_carbon_wheel`
  - requires one of `ROY`, `ROZ`, `STZ`.
- `z06_excl_default_and_carbon_wheels`
  - members: `SOE`, `ROY`, `ROZ`, `STZ`.
- `z06_excl_performance_brakes`
  - members include `J6A`, `J56`, `J57`.
- `z06_excl_aero_packages`
  - members: `T0E`, `T0F`, `T0G`, `5ZV`.
- `z06_group_z07_requires_aero`
  - requires one of `T0F`, `T0G`.

The main inconsistency is that Z06 still uses many direct replacement rows for wheel/package peer behavior while the same workbook already has group structures for several of those decisions.

### Evidence inspected

Files/docs:

- `AGENTS.md`
- `codex-context.md`
- `.hermes/plans/rule-normalization-pass2-grouped-excludes.md`
- `27vette-workbook-guard/references/rule-exclusive-price-normalization.md`

Workbook sheets inspected:

- `z06_options`
- `z06_rule_mapping`
- `z06_rule_groups`
- `z06_rule_group_members`
- `z06_exclusive_groups`
- `z06_exclusive_members`
- comparable Stingray/Grand Sport source rule sheets for replace-count contrast

Tests/runtime surfaces identified:

- `tests/z06-performance-package-interactions.test.mjs`
- `tests/z06-runtime-rule-corrections.test.mjs`
- `tests/z06-form-data-draft.test.mjs`
- `tests/z06-runtime-promotion.test.mjs`
- `tests/multi-model-runtime-switching.test.mjs`
- `tests/workbook-schema-standardization.test.mjs`
- `form-app/app.js` generic handling of `exclusiveGroups`, `ruleGroups`, and `runtime_action=replace`

## Proposed scope

### In scope

1. Add a Z06 replace-shape guard that classifies active `z06_rule_mapping` rows with:
   - `rule_type = excludes`
   - `runtime_action = replace`
   - `normalization_status` not already `omitted`/`replaced`

2. Keep only approved true default replacement rows active. Initial proposed keep-list:
   - `J57 -> J6A` if inspection confirms it is still needed as a selected brake package removing the default J6A brake caliper and is not fully covered by `z06_excl_performance_brakes` plus default metadata.
   - Any future confirmed Z06 default replacement row where the source removes a default-selected target and there is no existing exclusive/default-selection path that can express it more cleanly.

3. Normalize wheel/package replace rows away from direct `replace` where existing workbook structures already own the decision:
   - Package peer selection remains in `z06_excl_carbon_wheel_packages`.
   - Package-to-carbon-wheel requirement remains in `z06_group_pdb_requires_carbon_wheel`, `z06_group_pdd_requires_carbon_wheel`, and `z06_group_pdf_requires_carbon_wheel`.
   - Default/carbon wheel peer replacement should be expressed by group/default metadata, not by dozens of reciprocal direct replace rows.

4. Add or adjust workbook-owned default metadata if a replacement row is currently compensating for missing/default behavior:
   - Use existing `default_selection_rules` if the default must be seeded/restored under a condition.
   - Use `z06_options.display_behavior = default_selected` only when the row should be selected at reset/reconcile by source data.
   - Use `z06_exclusive_groups.selection_mode` only for peer replacement/last-member behavior, not to fake a requirement that belongs in `requires_any`.

5. Mark retired Z06 direct replace rows with lifecycle metadata rather than deleting them:
   - `generation_action = omit_replaced_by_canonical_group` or another schema-allowed replacement action if current schema supports it.
   - If a new action is needed, add it generically to schema validation with a narrow name and tests.
   - `normalization_status = replaced`
   - `normalization_reason = Pass 3: replacement behavior is represented by <group/default/rule id>.`
   - `replacement_group_id` and/or `replacement_rule_id` as appropriate.

6. Regenerate Z06 draft and live promoted registry after approved workbook changes:
   - Run `scripts/generate_z06_form.py` first.
   - Run `scripts/generate_stingray_form.py` second so promoted Z06 app data in `form-app/data.js` is synchronized.

7. Update tests to assert canonical structure, not the old direct replace rows:
   - Z06 tests should prove package/wheel/aero behavior still works through exclusive/rule/default data.
   - Schema guard should prevent Z06 direct replace rows from growing again outside the approved default-replacement allowlist.

### Out of scope

- Do not implement the full user-facing Z06 fix list in this pass. This pass prepares the rule shape for those fixes.
- Do not change price rule semantics; that remains Pass 4.
- Do not change dealer submission endpoint, payload shape, Turnstile behavior, styling, or deployment configuration.
- Do not promote ZR1 or ZR1X.
- Do not add a parallel workflow, staging sheet, or new module when existing workbook sheets already own the relationship.
- Do not hardcode Z06 RPO behavior in `form-app/app.js` unless tests prove a generic runtime capability is missing; if runtime changes are needed, implement them generically from workbook data.
- Do not hand-edit generated `form_*` sheets, generated JSON, or `form-app/data.js`; regenerate them.

## Exact files and sheets likely to change

### Workbook source

`stingray_master.xlsx`:

- `z06_rule_mapping`
- `z06_rule_groups`
- `z06_rule_group_members`
- `z06_exclusive_groups`
- `z06_exclusive_members`
- `z06_options` only if default/selectable/display metadata needs correction
- `default_selection_rules` only if seeded/restored Z06 defaults need canonical workbook rows

### Tests

Likely modify:

- `tests/workbook-schema-standardization.test.mjs`
  - Add Z06 replace/default shape guard.
- `tests/z06-form-data-draft.test.mjs`
  - Assert Z06 generated draft emits the canonical groups/default metadata and does not emit retired replace rows.
- `tests/z06-performance-package-interactions.test.mjs`
  - Keep/adjust behavior assertions for package peer switching, package-to-wheel requirements, and carbon-wheel/default switching.
- `tests/z06-runtime-rule-corrections.test.mjs`
  - Keep user-facing behavior tests tied to canonical workbook paths.
- `tests/z06-runtime-promotion.test.mjs`
  - Confirm promoted app data strips draft-only provenance and preserves canonical Z06 runtime behavior.
- `tests/multi-model-runtime-switching.test.mjs`
  - Run for regression; modify only if generic runtime behavior changes.

### Generated artifacts

Expected after regeneration:

- `form-output/inspection/z06-form-data-draft.json`
- `form-output/inspection/z06-form-data-draft.md`
- Possibly `form-output/inspection/z06-*` timestamp/payload artifacts depending on generator side effects
- `form-output/stingray-form-data.json`
- `form-app/data.js`
- generated `form_*` workbook sheets inside `stingray_master.xlsx`

Restore timestamp-only unrelated generated churn before handoff.

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

Add a guard that fails on active Z06 replace rows outside the approved canonical default-replacement allowlist.

The guard should report each offending row with:

- row number
- `rule_id`
- source RPO / source option id
- target RPO / target option id
- whether the source/target already share an active exclusive group
- whether the source already has a relevant `requires_any` or `excludes_any` group
- proposed canonical owner: exclusive group, rule group, default rule, or direct keep

Expected initial RED failure should include at least:

- `ROU`, `ROX`, `SOA`, `SOE`, `SOM`, `SON`, `SRK`, `SRN`, `STX` replacing `ROY`/`ROZ`/`STZ`.
- `ROY`, `ROZ`, `STZ` replacing `ROU`, `ROX`, `SOA`, `SOE`, `SOM`, `SON`, `SRK`, `SRN`, `STX`.
- `PDB`, `PDD`, `PDF` replacing aluminum/default wheel choices.

Do not fail on rows already marked `normalization_status = replaced` or `omitted`.

### Step 3 — Workbook migration design

Before writing, classify each active Z06 replace row into one of these buckets:

1. Keep as true default replacement.
   - Example candidate: `J57 -> J6A`, but only if `z06_excl_performance_brakes` plus default metadata does not already cover it.
2. Replace by active exclusive group.
   - Direct reciprocal peer rows should be retired when both choices are in an active exclusive group and runtime peer switching works from group metadata.
3. Replace by existing `requires_any` group plus default rule.
   - Package rows requiring carbon wheels should not hard-disable every aluminum wheel via direct replace if package selection can default/select a carbon wheel and the group requirement blocks invalid completion.
4. Defer with explicit reason.
   - If a row encodes a product rule that is not yet understood, mark it as out-of-pass rather than guessing.

### Step 4 — Safe-save workbook migration

Use an idempotent temporary command script or one-pass migration script that:

- Stops if `~$stingray_master.xlsx` exists.
- Loads workbook with `read_only=False` and captures `loaded_mtime_ns`.
- Updates only the approved Z06 source rows/sheets.
- Uses `save_workbook_safely()`.
- Refreshes table refs only for touched sheets if row appends occur.
- Reopens the workbook and prints exact counts:
  - remaining active Z06 `runtime_action=replace` rows
  - rows marked `normalization_status=replaced`
  - relevant group/member/default rows present

Lifecycle metadata should preserve auditability; do not delete source rows.

### Step 5 — Regenerate

Run:

```sh
.venv/bin/python scripts/generate_z06_form.py
.venv/bin/python scripts/generate_stingray_form.py
```

Do not run Grand Sport generation unless a shared generator/runtime change affects it.

### Step 6 — GREEN tests and gates

Run targeted tests first:

```sh
node --test tests/workbook-schema-standardization.test.mjs
node --test tests/z06-form-data-draft.test.mjs
node --test tests/z06-performance-package-interactions.test.mjs
node --test tests/z06-runtime-rule-corrections.test.mjs
node --test tests/z06-runtime-promotion.test.mjs
```

Run broader runtime regression if generated `form-app/data.js` or generic runtime behavior changed:

```sh
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Run Python/workbook gates:

```sh
.venv/bin/python -m pytest tests -q
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
```

If generic runtime behavior changes, add a browser smoke after Node gates by serving `form-app` and exercising Z06 package/wheel/aero selection.

## Acceptance criteria

- Z06 no longer has dozens of active direct `runtime_action=replace` rows for package/wheel peer behavior.
- Any remaining active Z06 direct `replace` row is explicitly allowlisted as true default replacement and covered by a test.
- Retired source rows retain lifecycle metadata and point to their canonical replacement group/rule/default owner.
- Z06 package/wheel/aero behavior remains green in tests using workbook-owned groups/defaults.
- Z06 generated draft and promoted app data are synchronized after regeneration.
- Workbook schema and package validators pass.
- No dealer submission, Turnstile, styling, deployment, ZR1, or ZR1X behavior changes are introduced.

## Risks

- `runtime_action=replace` has real runtime semantics; retiring a row without equivalent group/default coverage can change user-visible behavior.
- Some existing Z06 tests may encode current behavior rather than desired canonical behavior. Update them only when the workbook-owned structure is the new asserted contract.
- Package-to-wheel defaults may require default-selection metadata or generic runtime behavior if current direct replace rows are masking missing default logic.
- Cross-section wheel/package behavior is easy to over-collapse; classify rows before editing.

## Non-goals

- This pass does not resolve all Z06 product bugs.
- This pass does not classify price-rule intent.
- This pass does not rewrite interior/accessory presentation.
- This pass does not remove stale one-pass scripts unless implementation discovers a destructive script that directly blocks safe validation.

## Follow-up after this pass

Recommended next pass after Pass 3 is Pass 4: price-rule semantic classification. That should make Z06 package/component pricing and included-zero behavior easier to audit before applying the larger Z06 product-fix list.
