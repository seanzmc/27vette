# Outcome rubric — Refresh promoted runtime contracts and republish the registry

Spec: `docs/superpowers/specs/2026-07-23-validation-single-lane-active-surface-cleanup.md` §4 Pass 3
blocking prerequisite ("the retained Stingray runtime contract fails strict validation, so
`generate_registry.py` exits nonzero and `form-app/data.js` cannot be rebuilt").

The retained artifacts predated workbook-authored section metadata. Under the Pass G1 strict
validator the retained Stingray contract was unpublishable, which meant no end-to-end
workbook→form run could finish. The spec required regenerating through the strict path — never
hand-editing the artifact — and reviewing the bounded drift before publishing.

## Measurable criteria

| # | Criterion | Result |
|---|---|---|
| 1 | Drift reviewed in an isolated candidate root BEFORE any tracked write | PASS — three models generated into a scratch `--output-root`, diffed by stable identity |
| 2 | Every published difference traces to a workbook row | PASS — `section_master` authors each new value; `sec_perf_support_001` has **0** references anywhere in the workbook |
| 3 | Zero product-data drift: no choice, standardEquipment, rule, priceRule, interior, colorOverride, variant, ruleGroup, exclusiveGroup, contextChoice, or defaultSelectionRule added or removed | PASS — all three models |
| 4 | Stingray's large `choices` diff is order-only | PASS — identical id set, zero per-id field changes; array re-sorts because section display orders changed |
| 5 | Contract regenerated through the strict path, not hand-edited | PASS — `generate_form.py`, `validation_errors: 0` for all three |
| 6 | Canonical workbook unchanged | PASS — `git status` empty for it; SHA-256 `8858cff4…5b2166` |
| 7 | Full schema gate goes green | PASS — was 1 error (`app_registry_freshness_check_failed`), now valid / 0 issues |
| 8 | Browser/runtime gates pass against the republished registry | PASS — multi-model switching 48, stingray regression 90, z06 promotion 5, z06 package interactions 21, z06 rule corrections 15, z06 interior cleanup 7, nonruntime purge 6, unpublished contracts 2, generator stability 15, visual copy 8 |
| 9 | No new test failure | PASS — `workbook-schema-standardization` improved 7/2 → 8/1; Python suite lost `test_shared_assembler_preserves_grand_sport_runtime_drift_surfaces` from the failure set |

## Published drift, as reviewed

One coherent workbook change the artifacts had not caught up to:

- `sec_perf_support_001` → `sec_perf_001` ("Mechanical"), moved from step `wheels` to
  `packages_performance`. 12 choices per model follow it for grand_sport and z06; 1 rule's
  `source_section` follows. Stingray had zero rows in that section, so it simply disappears there.
- Two section renames: `sec_perf_z52_001` "Z52 Packages" → "Performance Packages" (order 10 → 11),
  and `sec_z06_cf_whee_001` "Z06 Carbon Fiber Wheel Selection" → "…Wheel Packages" (inert — that
  section has zero rows in the only contract carrying it).
- Nine display-order changes, not five: `sec_spec_001` 110→5, `sec_incl_001` 10→15, `sec_3lte_001`
  30→25, `sec_susp_001` 20→25, `sec_stan_001` 20→30, `sec_exha_001` 40→35, `sec_stan_002` 10→35,
  `sec_safe_001` 30→40, `sec_tech_001` 40→45. Per-model totals: 10 Stingray, 9 Grand Sport, 8 Z06.
- The migrated section also carries `standard_behavior` `user_selected` → `locked_included`. Inert:
  `app.js` reads neither `standard_behavior` nor `step.section_ids`.
- Stingray `dataset` gains `model`, `model_year`, `status: runtime_active` — required by the strict
  validator and the direct cause of the blocked registry build.

Customer-visible: section ordering within Standard Equipment and Performance & Aero (`app.js`
sorts by `section_display_order`, so `sec_spec_001` "Special Edition" moves from last to first),
one visible section label, and twelve priced options — including Front Lift Adjustable Height
(E60, $2,995) and Battery Protection Package (ERI, $100) — moving from the Wheels & Brake Calipers
step to Performance & Aero on Grand Sport and Z06. All authored in the workbook; this pass chose
no product behavior.

## Open items surfaced by the verifier (not regressions)

1. `grand-sport-x`, `zr1`, and `zr1x` retained contracts still reference `sec_perf_support_001`,
   which the workbook no longer defines. They are unpromoted and unpublished, so no gate flags
   them — but this is the same staleness class that caused the original blocker. Regenerate them
   or mark them stale-by-design.
2. `tests/grand-sport-contract-preview.test.mjs:67-68` and `tests/grand-sport-draft-data.test.mjs:826-827`
   assert on `sec_perf_support_001`. Already failing before this pass; retarget to `sec_perf_001` /
   `packages_performance`. Both tests invoke `generate_form.py` without `--output-root` and so
   rewrite tracked artifacts — fix that at the same time.

## Explicitly out of scope

Source-builder convergence (Pass 2), the composed candidate verifier `verify_workbook_candidate.py`
(Pass 3 proper), promotion of grand_sport_x / zr1 / zr1x, any workbook write, any deletion.
