# Codex Pickup

We were working in `/Users/seandm/Projects/27vette` on the Stingray CSV/shadow migration control plane and narrow projected-owned slices. The latest completed pass was **Pass 102: Interior Source Namespace Validation**. It added validation/tests so structured non-choice references must resolve to one of: active production choice, explicitly `production_guarded` option ID, or valid `data.interiors[].interior_id`. The 30 `3LT_*` IDs are now treated as valid interior runtime source IDs, not missing choices and not guarded option IDs.

Key decisions:

- Keep migration spec-first and evidence-based.
- No interior migration yet.
- No manifest rows or fake selectables for `3LT_*`.
- Rule-only/non-choice option IDs remain guarded only when they are option-like legacy references: `opt_5vm_001`, `opt_5w8_001`, `opt_5zw_001`, `opt_cf8_001`, `opt_ryq_001`.
- Interior IDs are a distinct namespace backed by `data.interiors[]`.
- Unknown non-choice structured refs should fail validation unless guarded or valid interior IDs.

Current direction:

- The CSV/shadow path now has stronger control-plane validation around projected choices, duplicate RPOs, package ownership, rule-only IDs, non-choice structured refs, and interior source IDs.
- Continue with evidence/spec-only passes before implementation.
- Likely next step: inspect whether any interior-source/control-plane documentation or future interior readiness review is needed, without migrating interiors.

Latest validation:

- Focused Pass 102 test passed.
- Adjacent control-plane tests passed.
- Full Stingray ladder passed at `367/367`.
- `git diff --check` passed.
- Intended changed files: `scripts/stingray_csv_shadow_overlay.py`, `tests/stingray/interior-source-namespace-control-plane.test.mjs`, `tests/stingray/required-badges-control-plane.test.mjs`.

User preferences/context:

- You want strict scope control, no speculative refactors, production behavior wins, and evidence from actual repo/runtime/tests.
- For evidence-only passes, do not edit.
- For implementation passes, use RED-first focused tests, preserve unrelated importer/schema work, and avoid touching production app/runtime/generator/workbook unless explicitly approved.
