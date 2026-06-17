# Actual remaining tasks called out by recent docs

From docs/persisting-audit-findings-2026-06-14.md and the deferred/non-goal sections:

- Fallback-retirement / boundary-narrowing pass:
  - form-app/app.js still has orderSectionDefinitions / stepOrderSectionKeys fallbacks.
  - model_configs.py still has STEP_ORDER, STEP_LABELS, CONTEXT_SECTIONS.
  - Promoted models now have workbook metadata, so this is a valid next architecture cleanup.

- Active standard-tech / connected-service ownership:
  - sec_tech_001 rows are still active emitted standard equipment.
  - Do not delete until a workbook-owned replacement source model exists.

- Optional audit/report tooling:
  - scripts/build_rule_sources.py
  - tests/grand-sport-rule-audit.test.mjs
  - tests/audit-parser-metadata-loaders.test.mjs
  - Currently intentional opt-in tooling, not default readiness.

- Stingray rear-script badge rules:
  - Migrate RIK/RIN/SL8 pairwise excludes to a Stingray exclusive group if intended UX is radio replacement.

- Display-order guard:
  - Promoted sheets are clean; add durable validator for active promoted (section_id, display_order) uniqueness.
  - Decide separately whether to include future ZR1/ZR1X scaffold rows.

- Cross-model ordering drift:
  - Wheels/roof ordering differences.
  - Grand Sport gs_excl_ls6_engine_covers exclusive-member order still needs alignment or documentation.

- Cross-model copy convergence / product decisions:
  - Shared option name/description drift remains.
  - Product-review items should not be majority-overwritten without decisions.

- Z06 option-id suffix/no-RPO ID drift:
  - Mostly tooling/cosmetic unless strict cross-model option_id joins are desired.

- Stingray exclusive-group ID prefix/style drift:
  - Cosmetic unless editor/tooling needs normalization.

- Interior stale-surface cleanup:
  - interior_reference_path still exists in config.
  - architectureAudit/stingray_interiors_refactor.csv and architectureAudit/grand_sport_interiors_refactor.csv still exist.
  - Needs consumer audit + contract-parity proof before removal.

- Later rule-mapping cleanup:
  - body_style_scope remains a conditional retirement candidate.
  - runtime_action remains behavior-carrying and should not be removed until replacement behavior is remodeled/tested.
