# Script & Test Inventory — Keep / Delete (pre-merge cleanup)

Status: awaiting deletion approval. Read-only audit. Nothing removed yet.
Goal: protect months of hand-authored workbook logic by deleting spent,
manual-only mutating scripts before merging `z06-zr1-migration → main`.

## Method / evidence

- "Active pipeline" = reachable by import from `generate_{stingray,grand_sport,z06}_form.py`.
- "WRITES-WORKBOOK" = file contains `save_workbook_safely` / `wb.save` (can mutate source-of-truth).
- "Auto-run" = invoked by any git hook / CI / package.json. **Verified: NONE exist.**
- Generators open source option sheets `read_only=True` → cannot clobber `*_options`.
- Guard test exists asserting generator never `wb.save(WORKBOOK_PATH)`.

Conclusion up front: **no script runs by itself.** Every destructive script is
manual-only. The week-loss was a hand-run `apply_future_model_lz_interiors`.
Deleting that cluster removes the foot-gun permanently.

---

## A. KEEP — active generation pipeline (read-only on your source)

| File | Writes? | Why keep |
|---|---|---|
| `scripts/generate_stingray_form.py` | form_* only | builds data.js (all 3 models) |
| `scripts/generate_grand_sport_form.py` | no | GS draft/contract |
| `scripts/generate_z06_form.py` | no (read_only) | Z06 draft/contract |
| `scripts/corvette_form_generator/__init__.py` | — | package |
| `…/inspection.py` | no | GS/Z06 generation core |
| `…/mapping.py` | no | section/step mapping |
| `…/model_config.py` | no | ModelConfig type |
| `…/model_configs.py` | no | model registry configs |
| `…/output.py` | no | writes data.js / json |
| `…/registry_promotion.py` | no | runtime registry build + live_contract_data |
| `…/runtime_metadata.py` | no | metadata/override loaders |
| `…/validation.py` | no | generation validation count |
| `…/workbook.py` | form_* (guarded) | clean/money/rows + safe-save helper |

## B. KEEP — intentional utilities (manual, not foot-guns)

| File | Writes? | Why keep |
|---|---|---|
| `scripts/promote_z06_runtime.py` | WRITES | the legit, idempotent Z06 promotion you want live |
| `scripts/validate_workbook_package.py` | no | structural validator |
| `scripts/validate_workbook_schema.py` | no | schema validator — **trim cosmetic checks, keep price guard** |
| `…/workbook_package.py` | no | package validation support |
| `…/schema_validation.py` | no | validator logic — **keep numeric-price invariant, drop bool/lifecycle cosmetics** |
| `scripts/repair_workbook_tables.py` | no (read-only) | table-ref repair util; harmless |

## C. DELETE — spent one-time migrations (ALL write workbook, manual-only)

Purpose served; re-running any of these can overwrite your authored rows.

- `scripts/migrations/add_model_registry_promotion.py`
- `scripts/migrations/add_workbook_metadata_sheets.py`
- `scripts/migrations/apply_engine_cover_default_rules.py`
- `scripts/migrations/apply_schema_standardization.py`  ← the cosmetic fixer
- `scripts/migrations/apply_z06_z07_strict_peer_exclusions.py`
- `scripts/migrations/backfill_audit_parser_metadata.py`
- `scripts/migrations/backfill_model_config_metadata.py`
- `scripts/migrations/populate_grand_sport_bc7_defaults.py`
- `scripts/migrations/populate_grand_sport_nga_defaults.py`
- `scripts/migrations/populate_phase3_runtime_metadata.py`
- `scripts/migrations/populate_phase6_presentation_metadata.py`

(The whole `scripts/migrations/` dir.)

## D. DELETE — spent future-model ingest/audit cluster (the week-killer family)

Standalone, manual-only, not reached by any generator.

Scripts:
- `scripts/apply_future_model_compatibility_sources.py`  (WRITES)
- `scripts/apply_future_model_lz_interiors.py`  (WRITES) ← **the script that rewrote z06_options**
- `scripts/build_future_model_source_preview.py`  (read-only preview)
- `scripts/build_future_z_rule_audit.py`  (read-only)
- `scripts/build_grand_sport_rule_sources.py`  (read-only; one-time GS authoring tool)

Package modules:
- `scripts/corvette_form_generator/future_model_compatibility.py`
- `scripts/corvette_form_generator/future_model_ingest.py`
- `scripts/corvette_form_generator/future_model_lz_interiors.py`  ← week-killer core
- `scripts/corvette_form_generator/future_z_rule_audit.py`

Tests (cover only the above, become orphaned on delete):
- `tests/test_future_model_compatibility_rebase.py`
- `tests/test_future_model_ingest_preview.py`
- `tests/test_future_model_lz_interiors.py`
- `tests/test_future_model_raw_source_parser.py`
- `tests/test_future_model_source_review.py`
- `tests/test_future_z_rule_audit.py`

Verified safe: none of these are imported by `generate_*` or by `inspection.py`.
`FUTURE_MODEL_SPECS` is consumed only inside this cluster, not the live pipeline.

## E. KEEP — tests guarding LIVE behavior

- `tests/stingray-form-regression.test.mjs`
- `tests/stingray-generator-stability.test.mjs`
- `tests/grand-sport-contract-preview.test.mjs`
- `tests/grand-sport-draft-data.test.mjs`
- `tests/grand-sport-rule-audit.test.mjs`
- `tests/multi-model-runtime-switching.test.mjs`
- `tests/z06-contract-preview.test.mjs`
- `tests/z06-form-data-draft.test.mjs`
- `tests/z06-runtime-promotion.test.mjs`
- `tests/z06-runtime-rule-corrections.test.mjs`
- `tests/z06-interior-accessory-cleanup.test.mjs`
- `tests/z06-performance-package-interactions.test.mjs`
- `tests/test_model_config_metadata.py`
- `tests/test_registry_promotion_metadata.py`
- `tests/test_schema_validation_metadata.py` (after schema trim)

## F. VERIFY before deciding (case-by-case)

- `tests/workbook-schema-standardization.test.mjs` — **trim**: drop the
  boolean/lifecycle cosmetic asserts; keep numeric-price assert scoped to LIVE
  model sheets (`stingray_options`, `grandSport_options`, `z06_options`), NOT
  the future-model scaffold sheets being deleted.
- `tests/workbook-visual-copy-standardization.test.mjs` — cosmetic copy
  standardization; passes today. Keep or retire — low stakes.
- `tests/audit-parser-metadata-loaders.test.mjs` — guards `runtime_metadata`
  audit-parser loaders. Keep IF loaders stay active; the matching *migration*
  (`backfill_audit_parser_metadata`) is deleted but the loader is pipeline code.

## Schema-test reconciliation (your "keep price guard" decision)

Root cause of the 3 reds = type drift in `LZ_Interiors`, `interior_components`,
`model_interior_scope` — all **future-model scaffold sheets, not read by live
Stingray/GS generation** (proven; data.js byte-identical with/without the fix).

Resolution that needs NO mutating script on live data:
1. Delete cluster D (removes the scaffold's consumers).
2. Scope the kept price guard to live model option sheets only.
3. The boolean/lifecycle cosmetic checks retire with cluster C/D.

Net: 3 reds resolved by deletion + test scoping, not by running the fixer.

## Merge-safety guarantees (independent of cleanup)

- Workbook is one binary file; merge takes **z06-zr1's version wholesale**
  (`git checkout --theirs stingray_master.xlsx` on conflict). Main's older
  workbook never overwrites yours.
- No hook/CI re-runs any deleted script.
- Generators read source `read_only`; regen cannot clobber `*_options`.

## Proposed order

1. Approve deletions (C + D + scoped test trims).
2. Delete in one commit on this branch; run full suite → expect green.
3. Open PR `z06-zr1-migration → main`, workbook = ours on conflict.
