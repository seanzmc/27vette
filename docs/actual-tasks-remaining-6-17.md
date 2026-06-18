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
  - `scripts/validate_workbook_schema.py` now enforces active promoted option-sheet `(section_id, display_order)` uniqueness; the SC7 section move tripped this guard and was corrected with `stingray_options.opt_sc7_001.display_order=71`.
  - Future-model scaffold duplicates are also closed: `zr1_options.sec_stan_001` and `zr1x_options.sec_stan_001` keep U80 at display order `20` and WUB at `21`.
  - `scripts/validate_workbook_schema.py` now also guards inactive future scaffold option sheets referenced by inactive `model_workbook_sources` rows with `duplicate_future_scaffold_option_display_order`.

- Model metadata schema gate repair:
  - `model_master` is restored as the workbook-owned model metadata table for Stingray, Grand Sport, Z06, ZR1, and ZR1X.
  - `scripts/validate_workbook_schema.py` now reports direct `model_master_header_drift` and `duplicate_active_model_master_row` issues before indirect registry-promotion errors.
  - The two inactive future `model_workbook_sources` rule-mapping rows for ZR1/ZR1X were not restored because `zr1_rule_mapping` and `zr1x_rule_mapping` do not currently exist.

- Interior stale-surface cleanup:
  - `ModelConfig.interior_reference_path` and the default `architectureAudit/*_interiors_refactor.csv` config assignment are retired.
  - `architectureAudit/stingray_interiors_refactor.csv` and `architectureAudit/grand_sport_interiors_refactor.csv` are deleted.
  - `tests/grand-sport-draft-data.test.mjs` now guards active interior pipeline sources against reintroducing `interior_reference_path` or the stale CSV file names.
  - Active interior generation remains workbook-owned through `model_interior_scope`, `interior_components`, `lt_interiors`, `LZ_Interiors`, and `PriceRef`.

- Copy-convergence / product-decision pass:
  - `docs/copy-convergence-review-2026-06-17.md` records the strict shared-option drift review.
  - Safe GS/Z06-majority copy was applied to Stingray source rows, excluding reviewed/deferred allowlist fields.
  - `tests/workbook-visual-copy-standardization.test.mjs` now loads `z06_options`, enforces shared-copy parity with an allowlist, rejects trailing-period-only drift, and guards R-1 through R-6 product decisions.
  - R-1 UV6 Z06 section drift remains intentional.
  - R-2 SC7 moved to Stingray `sec_lpoe_001`, punctuation was normalized, and display order was set to `71` to avoid a promoted active duplicate.
  - R-3 DRZ, R-4 EFR/EDU, and R-5 NGA copy decisions are applied.
  - R-6 AUP seat presentation/order is applied: all promoted sheets use `Asymmetrical Seats` / `Competition Driver Seat, GT2 Passenger Seat`, with active seat order AQ9/AH2/AE4/AUP at 10/20/30/40.

- Earlier source-cleanup passes:
  - Active-model nonruntime option-row purge complete.
  - Stingray active seat canonicalization complete.
  - Rule-mapping column cleanup Pass 1 complete.
  - Z06 trim tooltip copy complete.
  - Z06 WKS indoor car cover membership/display order complete.

## Still to do

- Residual copy/product follow-up:
  - Deferred copy allowlist rows remain for later review where automatic convergence could delete detail or product meaning: AP9 description, D3V description, EYK/EYT badge copy, SFZ applicability, VYW logo applicability, ZZ3 Z06 includes-list difference, NWI description, and PIN restrictions.

- Active standard-tech / connected-service ownership:
  - `sec_tech_001` rows still active emitted standard equipment.
  - Do not delete until workbook-owned replacement source model exists.

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

1. Residual copy allowlist decision pass, if desired.
2. Active standard-tech / connected-service ownership design.
3. Optional audit/report tooling classification or later rule-mapping cleanup, if architecture cleanup continues.
