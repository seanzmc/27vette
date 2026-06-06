# Rule Normalization Pass 1 — Redundant Same-Group Excludes

## Status

Spec for approval. No implementation has been done in this pass.

## User Direction

The goal is to stop preserving broken or inconsistent Z06 rule behavior as if it were canonical. We should normalize each behavior into the correct workbook-owned pathway, then fix any remaining incorrect behavior through that same pathway rather than inventing new model/RPO-specific exceptions.

This pass intentionally starts small: remove only rule rows that duplicate active exclusive-group behavior and do not carry default-replacement semantics.

## Diagnosis

The prior rule-shape audit found that mutually exclusive choices are represented inconsistently across models:

- Some peer choices are represented correctly by `*_exclusive_groups` + `*_exclusive_members`.
- Some of those same peer choices also have explicit reciprocal `*_rule_mapping` excludes.
- The runtime already handles `exclusiveGroups` generically through `single_within_group` and `required_single_within_group`.
- Keeping both pathways for the same peer relationship makes the workbook harder to reason about and creates opportunities for accidental disables, stale copied rules, and Z06-specific exceptions.

Evidence from the audit:

- Same-group explicit excludes already covered by active exclusive groups:
  - Stingray: 3
  - Grand Sport: 10
  - Z06: 19
  - ZR1: 6
  - ZR1X: 6
- Z06 also has broad rule problems, but this pass will not try to preserve every current Z06 behavior; it will preserve only clear generic semantics:
  - exclusive peer replacement belongs to exclusive groups,
  - default removal belongs to explicit `runtime_action=replace`,
  - one-to-many blockers belong to `excludes_any`,
  - package/one-of requirements belong to `requires_any`.

Risk level: Medium. Workbook source rows and generated runtime artifacts will change, but the behavior removed in this pass should be redundant with exclusive-group runtime behavior.

Change type: mixed workbook source + generated artifacts + tests. No runtime JS behavior change is expected.

## Exact Ownership Decision

Business decision owner: workbook source rows.

Canonical structure for this pass:

- Mutually exclusive peer options: `*_exclusive_groups` + `*_exclusive_members`.
- Explicit excludes inside those groups: inactive/removed unless they have intentional special semantics.
- Default replacement behavior: keep explicit `*_rule_mapping` row with `runtime_action=replace`.
- Direct non-peer conflict behavior: out of scope for this pass.
- `excludes_any` migrations: out of scope for this pass.
- Price rules: out of scope for this pass.

## Files / Sheets To Inspect

Repo files:

- `AGENTS.md`
- `codex-context.md`
- `scripts/corvette_form_generator/inspection.py`
  - `load_exclusive_groups()`
  - `exclusive_group_pairs()`
  - `build_draft_rules()`
- `form-app/app.js`
  - `exclusiveGroupByOption`
  - `removeOtherExclusiveGroupOptions()`
  - `disableReasonForChoice()`
  - `reconcileSelections()`
- Tests likely touched/added:
  - `tests/workbook-schema-standardization.test.mjs`
  - likely new targeted workbook-source guard test, or extension of an existing workbook schema/rule audit test
  - model draft/runtime tests only if generated diffs require expectation updates

Workbook sheets:

- Stingray:
  - `rule_mapping`
  - `exclusive_groups`
  - `exclusive_group_members`
- Grand Sport:
  - `grandSport_rule_mapping`
  - `grandSport_exclusive_groups`
  - `grandSport_exclusive_members`
- Z06:
  - `z06_rule_mapping`
  - `z06_exclusive_groups`
  - `z06_exclusive_members`
- ZR1 / ZR1X source-only cleanup if safe and covered by the same guard:
  - `zr1_rule_mapping`, `zr1_exclusive_groups`, `zr1_exclusive_members`
  - `zr1x_rule_mapping`, `zr1x_exclusive_groups`, `zr1x_exclusive_members`

Generated artifacts to regenerate/review, not hand-edit:

- `stingray_master.xlsx` generated `form_*` sheets via generator output
- `form-output/stingray-form-data.json`
- `form-output/stingray-form-data.csv`
- `form-output/inspection/grand-sport-form-data-draft.json`
- `form-output/inspection/z06-form-data-draft.json`
- `form-app/data.js`

## Exact Candidate Rule Policy

For each active `excludes` rule where source and target are both members of the same active exclusive group:

Keep the row active only if one of these is true:

1. `runtime_action = replace`
2. `generation_action = preserve_runtime_exclude`
3. the source/target are not actually active current-model choices after generator normalization
4. manual inspection shows the row is not a pure peer-choice duplicate

Otherwise retire the row from active runtime generation. Preferred workbook edit is to set `active=False` or equivalent source lifecycle metadata if the sheet supports it; if not, use the project’s existing source-row retirement convention after inspecting headers. Do not delete rows blindly if row history/provenance columns should be preserved.

Important: Z06 current behavior is not a preservation target by itself. The preservation target is only the canonical workbook meaning above.

## RED Test First

Before workbook changes, add a failing guard that asserts:

- no active generated/runtime-authored explicit exclude duplicates an active exclusive-group pair unless it is intentionally preserved or `runtime_action=replace`.

Expected initial RED result: the test should fail with current duplicate counts or at least with representative offending rows such as Grand Sport/Z06 rear script badge reciprocal excludes.

The test should be model-general and cover source sheets, not hardcoded RPO behavior.

## Implementation Plan After Approval

1. Inspect candidate rows with row numbers and headers from all model sheets.
2. Add the RED guard test and run it to verify failure.
3. Write a small idempotent workbook migration script or one-off safe-save helper for this pass only if direct workbook writing is needed.
   - It must use `save_workbook_safely()`.
   - It must refuse to write if an Excel lock file exists.
   - It must support dry-run/report mode first.
4. Dry-run candidate retirements and review exact rule IDs.
5. Apply only approved redundant same-group excludes.
6. Reopen workbook and verify exact row active statuses on disk.
7. Regenerate affected artifacts.
8. Run gates.
9. Review diffs and restore unrelated generated timestamp churn if any.
10. Handoff with what changed, what did not, gate results, and next pass recommendation.

## Constraints / Boundaries

- Do not hardcode model/RPO business logic in Python or JavaScript.
- Do not hand-edit generated `form_*` sheets or generated JSON/data.js.
- Do not change dealer submission endpoint, payload shape, or Turnstile behavior.
- Do not solve Z06 behavior by preserving broken explicit excludes when a generic exclusive-group pathway exists.
- Do not touch price values or price-rule behavior in this pass.
- Do not convert same-section one-to-many excludes to `excludes_any` yet; that is Pass 2.
- Do not audit/fix the 88 Z06 `replace` rules in this pass except to explicitly avoid retiring `runtime_action=replace` rows.
- Do not promote ZR1/ZR1X runtime artifacts in this pass.
- Do not use stale one-pass scripts retired in the script cleanup pass.

## Validation Plan

Preflight:

```sh
git branch --show-current
git status --short --branch
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
```

Targeted RED/GREEN tests:

```sh
node --test tests/workbook-schema-standardization.test.mjs
```

Regeneration / artifact gates, adjusted to actual generator entrypoints after inspecting current scripts:

```sh
.venv/bin/python scripts/generate_stingray_form.py
.venv/bin/python scripts/generate_grand_sport_form.py
.venv/bin/python scripts/generate_z06_form.py  # only if present/current; otherwise use the active Z06 inspection generator path
```

Runtime/model tests:

```sh
node --test tests/stingray-form-regression.test.mjs tests/stingray-generator-stability.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs tests/grand-sport-draft-data.test.mjs tests/grand-sport-rule-audit.test.mjs
node --test tests/z06-form-data-draft.test.mjs tests/z06-runtime-rule-corrections.test.mjs tests/z06-performance-package-interactions.test.mjs tests/z06-runtime-promotion.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
node --test tests/*.mjs
```

Python gates:

```sh
.venv/bin/python -m pytest tests -q
```

Workbook final validation:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
```

## Non-Goals

- No price rule semantic classification yet.
- No Z06 package/aero/wheel behavior fixes yet beyond removing redundant peer excludes.
- No broad Z06 `replace` simplification yet.
- No conversion of repeated same-section blockers to `excludes_any` yet.
- No ZR1/ZR1X runtime promotion.

## Recommended Next Pass After This

Pass 2 should convert repeated one-source/many-target blocker rows into `excludes_any`, using `gs_group_z15_excludes_non_center_stripes` as the template. That should happen only after this pass proves exclusive-group peer cleanup is safe.
