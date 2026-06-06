# Z Runtime Readiness Spec 3 — Rule / Exclusive / Default Closure

## Diagnosis

The Z06/ZR1/ZR1X option and OVS universe is now stable enough to build rules on top of it. The next runtime-readiness blocker is workbook-owned rule behavior: requires, includes, excludes, exclusive groups, rule groups, and defaults.

This pass should stay simple and schema-aligned. Do not recreate the confusing option-review matrix pattern. Stingray and Grand Sport runtime rule behavior comes from a small set of workbook source sheets and generic generator/runtime concepts. Z should use the same shape.

Evidence inspected on branch `z06-zr1-migration`:

- Branch/status/lock:
  - branch: `z06-zr1-migration`
  - Excel lock file: absent at inspection time.
  - tracked tree was clean at inspection time; only existing repo clutter/untracked archives/backups/`.DS_Store` were present.
- Option/OVS closure state:
  - `z06_options`: 239 rows; `z06_ovs`: 1434 rows; blank sections: 0.
  - `zr1_options`: 203 rows; `zr1_ovs`: 812 rows; blank sections: 0.
  - `zr1x_options`: 204 rows; `zr1x_ovs`: 816 rows; blank sections: 0.
  - Final dry-run after simplified section approval had `error_count=0`, `would_add=0`, `would_remove=0` for all three Z models.
- Rule mapping surfaces:
  - `z06_rule_mapping`: 100 rows; rule types: 76 excludes, 15 includes, 9 requires.
  - `zr1_rule_mapping`: 56 rows; rule types: 39 excludes, 14 includes, 3 requires.
  - `zr1x_rule_mapping`: 56 rows; rule types: 39 excludes, 14 includes, 3 requires.
  - All current Z rule rows resolve to existing active source/target options:
    - missing source IDs: 0 for all three.
    - missing target option IDs: 0 for all three.
    - inactive source/target references: 0 for all three.
  - All current Z rule rows have `review_flag=False` and `normalization_status=active`.
- Exclusive group surfaces:
  - `z06_exclusive_groups`: 7 groups; `z06_exclusive_members`: 16 members; missing member option IDs: 0.
  - `zr1_exclusive_groups`: 4 groups; `zr1_exclusive_members`: 10 members; missing member option IDs: 0.
  - `zr1x_exclusive_groups`: 4 groups; `zr1x_exclusive_members`: 10 members; missing member option IDs: 0.
- Rule group/default/price surfaces:
  - `z06_rule_groups`: 0; `z06_rule_group_members`: 0.
  - `zr1_rule_groups`: 0; `zr1_rule_group_members`: 0.
  - `zr1x_rule_groups`: 0; `zr1x_rule_group_members`: 0.
  - `default_selection_rules`: 7 rows total, currently Stingray/Grand Sport only; no Z rows.
  - `z06_price_rules`, `zr1_price_rules`, `zr1x_price_rules`: all 0 rows. Pricing is not part of this pass.
- Compatibility rebase preview:
  - `scripts/apply_future_model_compatibility_sources.py --model-key all` now proposes the same current rule/exclusive counts already present in the workbook. Re-running the compatibility write is not expected to add rows.
  - Current rebase skip counts still include target-RPO-not-found rows. These are expected surfaces where Grand Sport is not an authoritative source for Z because Z models use different RPOs for engine covers, stripes, performance packages, wheels, and exterior colors.
- Grand Sport mention check:
  - No `Grand Sport` / `grand sport` text remains in Z rule mapping, rule group, or exclusive group rows.

Root cause / current gap:

- Z rule sheets have a mechanically valid Grand Sport-derived baseline, but they are not yet proven runtime-ready.
- The largest known gaps are not option IDs anymore; they are:
  1. missing or incomplete Z-specific rule groups for grouped requirements/exclusions;
  2. missing Z default-selection rules;
  3. Z-specific RPO logic not captured by Grand Sport rebase, especially engine covers, stripes, performance packages, wheels, suspension, brakes, aero/ground effects, and exterior accents;
  4. no generated Z runtime contract yet, because Z models remain inactive/unpromoted.

Change type:

- Workbook/data + audit/test pass.
- No runtime promotion.
- No `form-app/data.js` update unless explicitly expanded later.
- No pricing/interior completion in this pass except where a rule directly points to an already-existing option.

Risk level: medium-high. Rules decide whether runtime users can build invalid combinations. However, this pass should be simpler than the prior matrix work: prove current rules, add only workbook-shaped missing rules/groups/defaults, and defer pricing/interior/runtime promotion.

## Decision / Ownership

Rules belong in workbook source sheets:

- `z06_rule_mapping`, `zr1_rule_mapping`, `zr1x_rule_mapping`
- `z06_rule_groups`, `zr1_rule_groups`, `zr1x_rule_groups`
- `z06_rule_group_members`, `zr1_rule_group_members`, `zr1x_rule_group_members`
- `z06_exclusive_groups`, `zr1_exclusive_groups`, `zr1x_exclusive_groups`
- `z06_exclusive_members`, `zr1_exclusive_members`, `zr1x_exclusive_members`
- `default_selection_rules` for model-scoped defaults

Generator/runtime code should remain generic. Do not add RPO-specific JavaScript or model-specific Python exceptions.

Simplified rule-pass definition:

A Z rule is ready when:

1. source and target option IDs exist and are active for the model;
2. the rule uses existing workbook concepts: `requires`, `includes`, `excludes`, `single_within_group`, `required_single_within_group`, `requires_any`, `excludes_any`, and default-selection rules;
3. group members resolve to active options;
4. defaults do not fight exclusive groups or auto-add behavior;
5. any model-specific behavior is encoded in workbook rows, not runtime branches.

## Exact Files / Sheets to Change

Expected workbook sheets:

- `stingray_master.xlsx`
  - Likely source sheets for this pass:
    - `z06_rule_mapping`
    - `zr1_rule_mapping`
    - `zr1x_rule_mapping`
    - `z06_rule_groups`
    - `zr1_rule_groups`
    - `zr1x_rule_groups`
    - `z06_rule_group_members`
    - `zr1_rule_group_members`
    - `zr1x_rule_group_members`
    - `z06_exclusive_groups`
    - `zr1_exclusive_groups`
    - `zr1x_exclusive_groups`
    - `z06_exclusive_members`
    - `zr1_exclusive_members`
    - `zr1x_exclusive_members`
    - `default_selection_rules`
  - Possible read-only evidence sheets:
    - Z option/OVS sheets
    - `future_model_option_review`
    - `variant_master`
    - `section_master`
    - raw Z source/review sheets as evidence for rule prose

Expected code/test artifacts:

- Add a Z rule audit/report script or extend existing audit helpers only if needed to keep the pass repeatable.
  - Candidate artifact path: `scripts/build_future_z_rule_audit.py` or a generic helper under `scripts/corvette_form_generator/` if reuse is clean.
  - Keep report-only dry-run behavior by default.
- Add tests only for reusable validation/guard behavior, not for every row manually.
  - Candidate test file: `tests/test_future_z_rule_audit.py` if a new audit script is introduced.
  - Existing future-model compatibility tests should continue passing.

Expected report artifacts:

- `.hermes/plans/z-rule-pass-audit.json`
- `.hermes/plans/z-rule-pass-audit.md`

Do not change in this pass unless separately approved:

- `form-app/data.js`
- live model activation/promotion sheets
- dealer submission endpoint/payload/Turnstile
- generated `form_*` sheets by hand
- pricing rules except where a rule row must remain price-neutral
- interior component/scope semantics except where an option rule directly includes/requires an existing non-interior option

## Proposed Implementation Steps

### Step 1 — Build a Z rule audit, read-only

Produce a compact audit for each Z model using the same workbook concepts the runtime consumes.

For each model report:

- rule mapping count by type;
- source/target option reference integrity;
- current exclusive groups and member counts;
- current rule groups and member counts;
- default-selection rows for the model;
- duplicated semantic rule pairs;
- direct excludes already covered by exclusive groups;
- rules whose source or target is not runtime-emittable for a selected variant;
- grouped requirement/exclusion candidates implied by source prose but not yet represented;
- Z-specific hot spots:
  - engine appearance / engine covers;
  - exhaust defaults/replacements;
  - suspension defaults/options;
  - brake/caliper defaults and required brake groups;
  - performance packages (`Z07`, `ZTK`, Z52-like package rows);
  - wheels and wheel packages;
  - ground effects / aero;
  - stripes / exterior accents.

This audit should stay report-only and should not decide pricing/interiors.

### Step 2 — Close low-ambiguity workbook rule structures

After reviewing the audit, make only simple workbook-shaped changes first.

Likely low-ambiguity targets:

- Add missing `*_rule_groups` / `*_rule_group_members` when a current option clearly requires any of a small set or excludes a group.
- Add missing `default_selection_rules` only where the model clearly has a standard/default option that should seed selection and restore when peers are removed.
- Add missing exclusive groups/members only when there are at least two active members and behavior is the same generic peer-replacement pattern already used by Stingray/Grand Sport.
- Keep existing rule mapping rows that already resolve and are active.

Do not mechanically copy Grand Sport where Z has different RPO logic. Grand Sport is only a comparison seed.

### Step 3 — Verify workbook rule contract

After workbook writes, verify:

- every rule source/target option ID resolves to an active option;
- every exclusive/rule-group member resolves to an active option;
- required exclusive groups have at least two active members and at least one member available/standard for each relevant variant;
- default rules target active options and do not fight exclusive groups;
- no `Grand Sport` contamination in Z-facing rule/group notes or disabled reasons;
- compatibility rebase preview does not unexpectedly overwrite/erase manual Z-specific work.

### Step 4 — Stop before runtime promotion

This pass should end with workbook rule readiness evidence, not active runtime promotion.

Runtime promotion should remain a later spec after:

1. rule/exclusive/default closure;
2. interior readiness proof;
3. pricing pass;
4. registry activation/promotion plan.

## Constraints Repeated Back

- Keep this simpler than the option-review matrix work.
- Use the same schema concepts as Stingray and Grand Sport.
- Workbook source of truth: rules belong in workbook source rows, not runtime code branches.
- Do not refactor runtime structure.
- Do not add new dependencies.
- Do not alter live Stingray or Grand Sport behavior.
- Do not alter dealer submission endpoint, payload, or Turnstile behavior.
- Do not promote Z06/ZR1/ZR1X to runtime in this pass.
- Do not regenerate `form-app/data.js` unless a later approved promotion pass says so.
- Use `.venv/bin/python` for Python commands.
- For any workbook write: require Excel lock absent, use `save_workbook_safely()`, and verify saved workbook cells on disk.

## Non-goals

- Do not revisit option/OVS closure except to verify references.
- Do not complete pricing in this pass.
- Do not complete interior component/runtime behavior in this pass.
- Do not activate `model_master` or `model_registry_promotion`.
- Do not infer Z-specific package/wheel/stripe rules from Grand Sport alone.
- Do not create a separate review taxonomy outside the workbook schema.

## Risks

- Some current Z rules are Grand Sport-derived by RPO matching. They resolve mechanically, but Z-specific logic may still differ.
- Compatibility preview skip counts are not automatically errors; many are expected where Z RPOs differ from Grand Sport. Treat them as audit clues, not a mandate to copy more.
- Required exclusive groups/defaults can create runtime loops if defaults and peer-replacement groups are not coordinated.
- Grouped requirement/exclusion rows are currently empty for Z; adding them without evidence may over-constrain the form.
- Pricing and rule behavior are related for packages, but price rules should remain a later pass unless needed for rule identity.

## Validation Plan

Read-only/audit phase:

```sh
.venv/bin/python scripts/apply_future_model_compatibility_sources.py --model-key all --format json > .hermes/plans/z-rule-pass-current-compatibility-preview.json
.venv/bin/python scripts/apply_future_model_compatibility_sources.py --model-key all --format markdown > .hermes/plans/z-rule-pass-current-compatibility-preview.md
```

If a new Z rule audit script is added:

```sh
.venv/bin/python scripts/build_future_z_rule_audit.py --model-key all --format json > .hermes/plans/z-rule-pass-audit.json
.venv/bin/python scripts/build_future_z_rule_audit.py --model-key all --format markdown > .hermes/plans/z-rule-pass-audit.md
.venv/bin/python -m pytest tests/test_future_z_rule_audit.py -q
```

After any workbook write:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Future-model staging gates:

```sh
.venv/bin/python -m pytest \
  tests/test_future_model_source_review.py \
  tests/test_future_model_source_population.py \
  tests/test_future_model_option_review.py \
  tests/test_future_model_option_population.py \
  tests/test_future_model_compatibility_rebase.py \
  tests/test_future_model_lz_interiors.py \
  tests/test_future_model_option_pricing.py \
  -q
```

If generator/draft artifacts are touched unexpectedly, run relevant Grand Sport/runtime tests and explain why.

No Node runtime tests are required unless this pass changes generated app data or runtime code.

## Approval Gate

Approve Spec 3 to start with Step 1: build the read-only Z rule audit using the existing workbook rule schema, then review the audit before workbook writes.
