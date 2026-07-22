# Milestone 2.3 Target Evidence Reconciliation and Presentation Pricing Outcome

Started: 2026-07-14
Source-boundary correction refreshed: 2026-07-15

## Task summary

- Goal: reconcile target-owned source evidence with comparator/profile semantics without allowing comparator data to replace target facts.
- Current correction: canonical option candidates come only from numbered Interior, Exterior, and Mechanical sheets; Equipment Groups and Color and Trim are excluded. LT/LZ interior metadata owns exact unique-interior seat/suede/stitch/two-tone compatibility.
- Target module: Grand Sport X, ZR1, and ZR1X with approved Grand Sport/Z06 comparators. This milestone does not claim arbitrary-model or generally model-agnostic support.

## Corrected behavior

- `canonical_option_sheet_eligible()` accepts only `Interior N`, `Exterior N`, and `Mechanical N`.
- The profiler recommends Equipment Groups and Color and Trim as `exclude`; the session API rejects attempts to assign either the Options role; the browser disables their Options controls.
- Target-owned price, copy, active state, and OVS status remain authoritative.
- Comparator-backed conditional prices require complete target RPO, condition RPO, numeric price, override type, model, body, trim, variant, and qualifier-clause coverage.
- Standard target options in required single-select sections remain selectable when the comparator/workbook section contract supports it. J6D is price 0 and `selectable=true` for Grand Sport X, ZR1, and ZR1X in `sec_cali_001`.
- Shared interior-code prose from Interior 3 no longer produces false one-of blockers. LT/LZ metadata filters each shared code to exact compatible unique `interior_id` rows; zero matching rows still fail closed.
- Every compiled relationship/profile effect is materially represented by a manifest row carrying its declared target dependencies.
- Target model identity remains in price source-feature identity.
- Conflicting evidence-ID semantics are rejected.

## Exact-current proof

Retained run: `form-output/ingest-wizard/20260715-035235-12e239`

- 5,999 manifest rows: 5,994 ready and 5 blocked.
- 213 typed subjects: 203 actionable and 10 missing-source/tooling.
- Reason distribution:
  - 127 `missing_section`
  - 28 `comparator_only_price_rule_proposal`
  - 17 `comparator_only_rule_group_proposal`
  - 16 `comparator_only_relationship_proposal`
  - 10 `comparator_only_exclusive_group_proposal`
  - 10 `ambiguous_existing_identity`
  - 5 `unresolved_price_scope`
  - 0 `unresolved_relationship_identity`
- 11,297 source features:
  - 3,970 compiled
  - 906 exception-open
  - 508 resolved non-workbook facts
  - 5,913 not applicable
- 447 compiled relationship features; zero without complete material target dependencies.
- 330 compiled target-price features; zero without a material target raw-price dependency.
- Same-run recompilation is byte-identical across all six retained compiler artifacts.

## Target facts

- Grand Sport X: J57 and J6D standard; J6D selectable/default; J6D price 0.
- ZR1/ZR1X: J6D, 719, EFR, and T0E defaults; J6D remains selectable.
- R8E: ZR1 3,000 and ZR1X 2,600 with exact target Price Schedule dependencies.
- N2Z: target-owned 895 and selectable on both Z targets.
- Five justified GSX price-scope blockers remain: CFV, ROY, ROZ, STZ, and VPW.

## Validation

- Focused compiler/profile/relationship/graph gate: 71 passed plus 7 subtests.
- Complete ingest-wizard gate: 314 passed plus 18 subtests.
- Python compilation, JavaScript syntax, and `git diff --check`: passed.
- Browser/API: current run resumed with 95/59/59 subjects, 203 actionable, 10 non-actionable, no `unresolved_relationship_identity` reason, and zero JavaScript errors.
- Fresh source-role browser proof: Equipment Groups and Color and Trim excluded/disabled; Interior, Exterior, and Mechanical active for Options.
- Protected workbook, publication bundle, and runtime hashes unchanged.
- Final independent source-boundary/artifact batch `deleg_fa5626eb`: PASS in both lanes; reviewers edited no files.

## Protected boundaries

- No workbook or raw-source mutation.
- No `pass-c-3` projection, runtime publication, registry promotion, deployment, live dealer submission, or dealer contract change.
- No commit or push.

## Residual scope

The 213 retained subjects remain next-pass inputs; Milestone 3 remains blocked and unapproved. No Milestone 2.3 defect is implied by the exact-current verifier.
