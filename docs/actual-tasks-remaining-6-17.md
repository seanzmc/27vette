# Actual remaining tasks called out by recent docs

From `docs/persisting-audit-findings-2026-06-14.md`, refreshed after 2026-06-17 passes.

## Completed

- Fallback-retirement / boundary-narrowing pass:
  - `form-app/app.js` no longer has `orderSectionDefinitions`, `orderSectionLabels`, `orderSectionOrder`, or `stepOrderSectionKeys` browser fallbacks.
  - Runtime now requires generated `data.orderSummary` metadata for promoted models.
  - `model_configs.py` / `runtime_metadata.py` constants remain only as unpromoted compatibility / completeness-check inputs.

- Stingray rear-script badge rules:
  - `exclusive_groups.excl_rear_script_badges` now owns RIK/RIN/SL8 replacement behavior.
  - Three `exclusive_group_members` rows exist at 10/20/30.
  - Six redundant pairwise Stingray `rule_mapping` excludes are gone.

- Cross-model ordering drift, confirmed active surfaces:
  - Z06 `SOM` / `ROX` wheel order now aligns with Grand Sport shared wheel sequence.
  - Grand Sport `gs_excl_ls6_engine_covers` member order now matches option-sheet order: BC7/BCP/BCS/BC4.
  - Roof ordering is guarded without workbook edit; `CF8` is active only for Grand Sport in current promoted data.

- Display-order cleanup for promoted sheets:
  - Promoted `stingray_options`, `grandSport_options`, and `z06_options` have no active duplicate `(section_id, display_order)` buckets.
  - Residual duplicates are future-model scaffold rows only: `zr1_options.sec_stan_001` and `zr1x_options.sec_stan_001` U80/WUB at order `20`.

- Earlier source-cleanup passes:
  - Active-model nonruntime option-row purge complete.
  - Stingray active seat canonicalization complete.
  - Rule-mapping column cleanup Pass 1 complete.
  - Z06 trim tooltip copy complete.
  - Z06 WKS indoor car cover membership/display order complete.

## Still to do

- Cross-model copy convergence / product decisions:
  - Shared option name/description drift remains.
  - Product-review items still need decision table; do not majority-overwrite without decisions.
  - Extend copy tests to include `z06_options` and intentional-difference allowlist.

- Active standard-tech / connected-service ownership:
  - `sec_tech_001` rows still active emitted standard equipment.
  - Do not delete until workbook-owned replacement source model exists.

- Interior stale-surface cleanup:
  - `interior_reference_path` still exists in config/model config surfaces.
  - `architectureAudit/stingray_interiors_refactor.csv` and `architectureAudit/grand_sport_interiors_refactor.csv` still exist.
  - Needs consumer audit + contract-parity proof before removal.

- Durable display-order validator:
  - Add validator/test for active promoted `(section_id, display_order)` uniqueness now that promoted sheets are clean.
  - Decide separately whether to include future ZR1/ZR1X scaffold rows.

- Optional audit/report tooling:
  - `scripts/build_rule_sources.py`
  - `tests/grand-sport-rule-audit.test.mjs`
  - `tests/audit-parser-metadata-loaders.test.mjs`
  - Still intentional opt-in tooling, not default readiness.

- Z06 option-id suffix/no-RPO ID drift:
  - U2K/U5G/UE1/VV4/CFV suffix drift remains.
  - No-RPO Z06 row IDs remain sparse.
  - Mostly tooling/cosmetic unless strict cross-model `option_id` joins are desired.

- Stingray exclusive-group ID prefix/style drift:
  - Cosmetic unless editor/tooling needs normalization.

- Later rule-mapping cleanup:
  - `body_style_scope` remains conditional retirement candidate.
  - `runtime_action` remains behavior-carrying; do not remove until replacement behavior is remodeled/tested.

## Recommended next passes

1. Copy-convergence/product-decision pass.
2. Interior stale-surface cleanup.
3. Future-model scaffold display-order decision / durable validator pass.
