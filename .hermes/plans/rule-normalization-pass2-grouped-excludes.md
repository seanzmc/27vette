# Rule Normalization Pass 2 — Grouped Excludes Spec

> Status: proposed spec only. Do not implement until approved.

## Goal

Normalize repeated one-source/many-target blocker rules into workbook-authored `excludes_any` rule groups across Stingray, Grand Sport, Z06, ZR1, and ZR1X, using the existing Grand Sport `gs_group_z15_excludes_non_center_stripes` shape as the canonical pattern.

The point of this pass is structural consistency: a source option that blocks a set of alternatives should be represented by one active `*_rule_groups` row plus `*_rule_group_members`, not many individual active `*_rule_mapping.excludes` rows, unless a row needs distinct runtime behavior or has an approved preservation reason.

## Diagnosis

### Root cause

The workbook currently represents similar “not available with any of this set” product rules in multiple ways:

1. Grand Sport already has one canonical grouped blocker:
   - `grandSport_rule_groups.group_id = gs_group_z15_excludes_non_center_stripes`
   - `group_type = excludes_any`
   - `source_id = opt_z15_001`
   - member rows in `grandSport_rule_group_members`
2. Most other one-source/many-target blockers remain as many direct active `excludes` rows in `*_rule_mapping`.
3. This creates inconsistent generator/runtime contracts and makes future rule corrections harder because equivalent logic must be audited as dozens of direct rows instead of one workbook-owned group.

### Evidence inspected

Files/docs:
- `AGENTS.md`
- `codex-context.md`
- `scripts/corvette_form_generator/inspection.py`
- `scripts/corvette_form_generator/schema_validation.py`
- `tests/stingray-form-regression.test.mjs`
- `tests/grand-sport-draft-data.test.mjs`
- `tests/z06-form-data-draft.test.mjs`
- `tests/workbook-schema-standardization.test.mjs`

Workbook sheets inspected:
- `rule_mapping`, `rule_groups`, `rule_group_members`, `exclusive_groups`, `exclusive_group_members`
- `grandSport_rule_mapping`, `grandSport_rule_groups`, `grandSport_rule_group_members`, `grandSport_exclusive_groups`, `grandSport_exclusive_members`
- `z06_rule_mapping`, `z06_rule_groups`, `z06_rule_group_members`, `z06_exclusive_groups`, `z06_exclusive_members`
- `zr1_rule_mapping`, `zr1_rule_groups`, `zr1_rule_group_members`, `zr1_exclusive_groups`, `zr1_exclusive_members`
- `zr1x_rule_mapping`, `zr1x_rule_groups`, `zr1x_rule_group_members`, `zr1x_exclusive_groups`, `zr1x_exclusive_members`

Runtime/generator contract observed:
- `rule_groups` / model-scoped `*_rule_groups` headers:
  - `group_id`, `group_type`, `source_id`, `body_style_scope`, `trim_level_scope`, `variant_scope`, `disabled_reason`, `active`, `notes`
- `rule_group_members` / model-scoped `*_rule_group_members` headers:
  - `group_id`, `target_id`, `display_order`, `active`
- Existing group types in live source:
  - Stingray: `requires_any`
  - Grand Sport: `excludes_any`, `requires_any`
  - Z06: `requires_any`
  - ZR1/ZR1X: currently no active rule groups
- Tests already prove grouped requirements and Grand Sport grouped exclusions are emitted and consumed.

### Current candidate counts from workbook inspection

Runtime-authored direct active `excludes` rows that are not same-exclusive-group peers, not `runtime_action=replace`, not `preserve_runtime_exclude`, and not already covered by `excludes_any`:

| Model | Candidate direct excludes | Existing `excludes_any` pairs | Existing `requires_any` pairs |
| --- | ---: | ---: | ---: |
| Stingray | 158 | 0 | 2 |
| Grand Sport | 119 | 1 | 1 |
| Z06 | 73 | 0 | 4 |
| ZR1 | 33 | 0 | 0 |
| ZR1X | 33 | 0 | 0 |

Largest one-source/many-target blocker clusters:

Stingray:
- `PCX` / `opt_pcx_001`: 24 target excludes across stripes/badges/wheels/custom delivery surfaces.
- `PDV` / `opt_pdv_001`: 16 stripe target excludes.
- `R88` / `opt_r88_001`: 15 target excludes across badges/LPO/stripes.
- `SFZ` / `opt_sfz_001`: 14 target excludes across badges/stripes.
- `CF8` / `opt_cf8_001`: 13 stripe target excludes.
- Several smaller groups: `5DG`, `5DO`, `5V7`, `5VM`, `5W8`, `RNX`, `PCU`.

Grand Sport:
- `R88` / `opt_r88_001`: 20 target excludes across badges, center stripes, full-length stripes.
- `SFZ` / `opt_sfz_001`: 19 target excludes across badges, center stripes, full-length stripes.
- `CF8` / `opt_cf8_001`: 18 target excludes across center stripes and full-length stripes.
- `SHT` / `opt_sht_001`: 17 full-length stripe/Z15 target excludes.
- Smaller candidate groups: `S47`, `SFE`, `5ZV`, and paint-specific stripe conflicts.

Z06:
- `SHT` / `opt_sht_001`: 16 stripe target excludes.
- `R88` / `opt_r88_001`: 15 badge/stripe target excludes.
- `SFZ` / `opt_sfz_001`: 14 badge/stripe target excludes.
- `CF8` / `opt_cf8_001`: 13 stripe target excludes.
- `GBA` / `opt_gba_001`: 4 exterior accent/roof target excludes (`EFY`, `ZYC`, `D84`, `D86`).
- Smaller wheel package blockers: `S47`, `SFE`.

ZR1 and ZR1X:
- `R88` / `opt_r88_001`: 15 badge/stripe target excludes in each model.
- `SFZ` / `opt_sfz_001`: 14 badge/stripe target excludes in each model.

## Proposed scope

### In scope

0. Preserve the user's newly added workbook data and check it before writing:
   - Keep the new Z06 model asset row in `asset_map` unless validation proves it conflicts with the canonical asset pipeline.
   - Treat the `interior_components` / `model_interior_scope` question as a workflow-consistency finding: if trim applicability is already owned by `model_interior_scope`, do not add or rely on a duplicate trim-scope mechanism in `interior_components` during this pass. If a future interior cleanup needs trim-scoped component behavior, first prove whether the existing `model_interior_scope`, `component_price_rules`, or `PriceRef.Trim` pipeline can express it before adding another column/module.
   - Update workspace instructions to explicitly require "workbook first, existing consistent pipelines first" before implementation changes.

1. Add a reusable guard test that identifies direct active `excludes` rows that should be normalized to `excludes_any` groups when all of the following are true:
   - The source has two or more runtime-authored direct active normal `excludes` rows to a coherent blocker set.
   - The rows do not use `runtime_action=replace`.
   - The rows are not already same-exclusive-group peers.
   - The rows are not explicitly preserved via `generation_action=preserve_runtime_exclude`.
   - The rows are not already represented by an `excludes_any` rule group.

2. Normalize a first coherent set of repeated blocker clusters into `excludes_any` groups:
   - Badge/stripe blocker clusters shared across models: `R88`, `SFZ`, `CF8`, `SHT` where the target set is a repeated stripe/badge set.
   - Z-family `R88`/`SFZ` rows for ZR1/ZR1X as source-staging consistency, while keeping those models non-promoted unless separately approved.
   - Z06 `GBA` conflict cluster (`EFY`, `ZYC`, `D84`, `D86`) if inspection confirms these four rows are true one-source/many-target blockers and not better represented as a future exclusive group.

3. For each migrated cluster:
   - Add one active `*_rule_groups` row with `group_type = excludes_any`.
   - Add active `*_rule_group_members` rows preserving deterministic target order.
   - Mark the replaced direct `*_rule_mapping` rows as:
     - `generation_action = omit_grouped_exclusion`
     - `normalization_status = omitted`
     - `normalization_reason = Pass 2: blocker set is represented by active excludes_any rule group <group_id>.`
     - `replacement_group_id = <new group_id>`
   - Preserve row identity and source evidence in `*_rule_mapping`; do not delete rows in this pass.

4. Regenerate affected artifacts for promoted/runtime models only:
   - Stingray production output via `scripts/generate_stingray_form.py` because Stingray source sheets and live `form-app/data.js` may be affected.
   - Grand Sport inspection/draft via `scripts/generate_grand_sport_form.py` and production registry refresh through Stingray generator if live registry data changes.
   - Z06 draft plus production registry via `scripts/generate_z06_form.py` then `scripts/generate_stingray_form.py` because Z06 is promoted.
   - ZR1/ZR1X are workbook source staging only; no live app promotion in this pass.

### Out of scope

- Do not normalize Z06 `runtime_action=replace` rows in this pass. That is Pass 3.
- Do not change price rule semantics. That is Pass 4.
- Do not change runtime JavaScript unless tests prove the existing generic `excludes_any` runtime path is incomplete.
- Do not change dealer submission, Turnstile, payload shape, styling, or deployment behavior.
- Do not add new dependencies.
- Do not hand-edit generated `form_*` workbook sheets, `form-output`, or `form-app/data.js`; regenerate them from source.
- Do not promote ZR1/ZR1X runtime models.
- Do not add duplicate workflow layers for assets or interiors when the current workbook sheets already own the relationship; document and use the existing pipeline first.
- Do not resolve the broader `interior_components` trim-scope question in this pass unless a Pass 2 gate proves the user's added workbook data breaks generation or validation.
- Do not preserve broken Z06 behavior for its own sake; if a Z06 rule is structurally wrong, normalize the shape and let later behavior fixes happen through canonical workbook paths.

## Exact files and sheets likely to change

### Workbook source

`stingray_master.xlsx`:
- `rule_groups`
- `rule_group_members`
- `rule_mapping`
- `grandSport_rule_groups`
- `grandSport_rule_group_members`
- `grandSport_rule_mapping`
- `z06_rule_groups`
- `z06_rule_group_members`
- `z06_rule_mapping`
- `zr1_rule_groups`
- `zr1_rule_group_members`
- `zr1_rule_mapping`
- `zr1x_rule_groups`
- `zr1x_rule_group_members`
- `zr1x_rule_mapping`

### Tests

Likely modify:
- `tests/workbook-schema-standardization.test.mjs`
  - Add/extend a generic grouped-exclude guard.
- `tests/stingray-form-regression.test.mjs`
  - Assert selected Stingray clusters emit `ruleGroups` with `group_type=excludes_any` and no corresponding direct generated rules.
- `tests/grand-sport-draft-data.test.mjs`
  - Extend existing grouped-exclusion assertions beyond Z15.
- `tests/z06-form-data-draft.test.mjs`
  - Assert selected Z06 clusters emit grouped exclusions and maintain existing Z06 package/aero behavior.
- Possibly `tests/multi-model-runtime-switching.test.mjs`
  - Only if runtime behavior needs direct coverage across promoted models.

### Generated artifacts

Expected after regeneration:
- `form-output/stingray-form-data.json`
- `form-output/stingray-form-data.csv`
- `form-app/data.js`
- `form-output/inspection/grand-sport-*`
- `form-output/inspection/z06-*`
- generated `form_*` sheets inside `stingray_master.xlsx`

Generated diffs must be reviewed and timestamp-only churn restored when unrelated.

## Implementation approach after approval

### Step 1 — RED guard

Add a failing guard that reports repeated normal direct excludes that are eligible for grouped-exclude normalization.

The guard should:
- Load workbook source sheets with `openpyxl`.
- Reuse the same runtime-authored logic used by generators:
  - `normalization_status in {omitted, replaced}` means not runtime-authored.
  - `normalization_status = preserved` means runtime-authored.
  - `generation_action` beginning with `omit` means not runtime-authored.
- Ignore:
  - `runtime_action=replace`
  - `generation_action=preserve_runtime_exclude`
  - same active exclusive-group peers
  - direct pairs already covered by `excludes_any`
- Fail with a compact list of source clusters still requiring conversion.

Initial expected RED failure should include at least:
- Stingray `PCX`, `PDV`, `R88`, `SFZ`, `CF8`
- Grand Sport `R88`, `SFZ`, `CF8`, `SHT`
- Z06 `R88`, `SFZ`, `CF8`, `SHT`, `GBA`
- ZR1 `R88`, `SFZ`
- ZR1X `R88`, `SFZ`

The exact target list can be narrowed in the test fixture to the approved pass set so this does not force every possible direct exclude to become a group in one step.

### Step 2 — Workbook migration script/runbook

Use a short, one-time safe-save Python migration from the command line or temporary script. Requirements:
- Stop if `~$stingray_master.xlsx` exists.
- Load workbook with `read_only=False`, capture `loaded_mtime_ns`.
- Add/update idempotent `*_rule_groups` rows by stable `group_id`.
- Add/update idempotent `*_rule_group_members` rows by `group_id + target_id`.
- Mark corresponding direct `*_rule_mapping` rows as omitted with replacement group metadata.
- Save through `save_workbook_safely()`.
- Reopen workbook and verify row counts and exact cells on disk.

Proposed group id convention:
- Stingray: `grp_<source_rpo_lower>_excludes_<target_family>`
- Grand Sport: `gs_group_<source_rpo_lower>_excludes_<target_family>`
- Z06: `z06_group_<source_rpo_lower>_excludes_<target_family>`
- ZR1: `zr1_group_<source_rpo_lower>_excludes_<target_family>`
- ZR1X: `zr1x_group_<source_rpo_lower>_excludes_<target_family>`

Use target-family names such as:
- `full_length_stripes`
- `badge_and_stripe_choices`
- `exterior_accent_and_roof_choices`

### Step 3 — Regenerate

Run generators in this order:

```sh
.venv/bin/python scripts/generate_grand_sport_form.py
.venv/bin/python scripts/generate_z06_form.py
.venv/bin/python scripts/generate_stingray_form.py
```

Rationale:
- Refresh model-specific inspection/draft artifacts first.
- Rebuild live app registry last so Stingray/Grand Sport/Z06 app data is synchronized.

### Step 4 — GREEN tests

Run targeted tests first:

```sh
node --test tests/workbook-schema-standardization.test.mjs
node --test tests/stingray-form-regression.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/grand-sport-rule-audit.test.mjs
node --test tests/z06-form-data-draft.test.mjs tests/z06-runtime-promotion.test.mjs tests/z06-runtime-rule-corrections.test.mjs tests/z06-performance-package-interactions.test.mjs
```

Then broader runtime/multi-model tests:

```sh
node --test tests/multi-model-runtime-switching.test.mjs
```

### Step 5 — Full gates

```sh
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python -m pytest tests -q
node --test tests/stingray-form-regression.test.mjs tests/stingray-generator-stability.test.mjs tests/grand-sport-contract-preview.test.mjs tests/grand-sport-draft-data.test.mjs tests/grand-sport-rule-audit.test.mjs tests/z06-form-data-draft.test.mjs tests/z06-runtime-promotion.test.mjs tests/z06-runtime-rule-corrections.test.mjs tests/z06-performance-package-interactions.test.mjs tests/multi-model-runtime-switching.test.mjs tests/workbook-schema-standardization.test.mjs
```

### Step 6 — Diff hygiene

Review:

```sh
git diff --stat
git diff --name-status
```

Classify generated changes:
- Real payload changes: expected for ruleGroups/rules counts and group emissions.
- Timestamp-only churn: restore if unrelated or explicitly report if retained because artifact was refreshed as part of the pass.
- Workbook binary churn: expected after safe-save, but verify with validators and row inspection.

## Risks

1. Broad grouped-exclude conversion can accidentally flatten distinct messages or special runtime behavior. Mitigation: preserve direct rows with `preserve_runtime_exclude` if a row needs distinct behavior.
2. Some large Stingray clusters, especially `PCX`, may combine multiple conceptual blocker families. Mitigation: split into multiple groups or defer ambiguous clusters instead of forcing one giant group.
3. Z06 behavior is known imperfect. Mitigation: prioritize canonical source structure, but do not make Pass 2 responsible for Pass 3 default/replacement semantics.
4. ZR1/ZR1X are non-promoted staging models. Mitigation: validate workbook/source sheets but do not require live generated runtime artifacts for them.
5. Generator side effects can rewrite timestamps or workbook generated sheets. Mitigation: run generators deliberately, then restore unrelated churn before handoff.

## Non-goals

- No price-rule taxonomy changes.
- No Z06 package/default replacement cleanup.
- No visual/UI redesign.
- No deployment.
- No removal of historical/audit rule rows; rows are retained with lifecycle metadata.

## Approval boundary

Approval for this spec would authorize:
- Adding RED tests for Pass 2 grouped-exclude consistency.
- Editing the listed workbook source sheets via safe-save to add `excludes_any` groups and mark replaced direct rows omitted.
- Regenerating affected artifacts.
- Updating tests/audits needed to reflect the canonical grouped-exclude shape.

It would not authorize:
- Pass 3 `runtime_action=replace` cleanup.
- Pass 4 price-rule semantic classification.
- Runtime model promotion changes.
- Dealer submission or UI behavior changes.
