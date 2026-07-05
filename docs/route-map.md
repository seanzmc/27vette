# Route map (current)

Condensed 2026-07-05 from the completed audit program logs. Pass-by-pass history (route-map passes 0-20, cleanup passes A-E) lives in
`docs/archive/completed-specs/audit-cleanup/Audit-route-map.md` and
`docs/archive/completed-specs/audit-cleanup/audit-cleanup-overview.md`, with per-pass specs alongside them.

## Active routes

**Model generation**

`stingray_master.xlsx` → `scripts/generate_form.py --model stingray|grand_sport|z06` → `model_generation.generate_model_artifacts()` → `source_assembly.assemble_model_source()` → `build_model_runtime_contract()` → `form-output/runtime/<slug>-runtime-contract.json` → `generate_registry.py` → `form-app/data.js`.

- Active/generatable models are workbook-discovered (`model_master.active`, exact-match active `model_workbook_sources`, active `model_variants`); there is no hardcoded model list.
- Promoted rows in `model_registry_promotion` use `artifact_type=runtime_contract` pointing at `form-output/runtime/<slug>-runtime-contract.json` for all active models.
- Stingray additionally writes compatibility `form-output/stingray-form-data.json` / `.csv`; Grand Sport/Z06 inspection/preview/draft payloads are explicit review outputs via `--emit-inspection --inspection-output <dir>` only.
- `generate_registry.py` is the only writer of `form-app/data.js`.
- `scripts/compare-generated-contracts.mjs` strips only timestamp keys then deep-compares — a strict no-drift parity check, not a validator for approved shape/path migrations.

## Philosophy constraints

- The workbook owns Corvette product data and business rules; `form-output/*` and `form-app/data.js` are outputs — never hand-edit as source-of-truth fixes.
- Generators read workbook tables, normalize, validate, emit. No hidden model/RPO-specific Python branches when a workbook row can express the decision.
- Runtime JavaScript renders and evaluates generated contracts generically; product facts belong in workbook-authored metadata.
- Dealer submission endpoint, payload shape, Turnstile behavior, and live model registry semantics are out of scope unless a spec names them.
- Route/artifact changes are parity-first: timestamp-normalized contract comparison for no-behavior-change passes; targeted consumer/promotion checks for approved migrations.

## Do not delete as "cleanup"

- `runtime_action=replace` and `body_style_scope` are live direct-rule behavior consumed by `form-app/app.js` (Pass 8 classified every row; see archived report). Any migration needs generated/runtime parity proof per behavior.
- Model-scoped variant override sheets (`stingray_variant_overrides`, `grandSport_variant_overrides`, `z06_variant_overrides`) own trim-standard placement/selectability (UQT) after Pass 18; the global sheet is retired (Pass 19).
- Stingray compatibility JSON/CSV and the `window.STINGRAY_FORM_DATA` alias have real consumers (`form-app/app.js`, `data.js`, `production.py`, `registry_promotion.py`, tests); retirement needs a spec-first parity pass.

## Open candidates (each needs its own spec)

1. **`runtime_action` / `body_style_scope` migration** — remaining replacement rows split across candidate canonical owners (direct-default, exclusive-peer, default-selection, grouped-dependency, product-decision); Grand Sport/Z06 replace-row migration, column deletion, emitted-rule trim, and scope-matcher changes all still open. Evidence: archived Pass 8 report.
2. **Stingray `requires_z25` contract fork** — production path strips `requires_z25` from interiors for byte-compat; decide schema-wide include-or-strip in the shared trimming function.
3. **Stingray rule-assembly consolidation** — Stingray still has its own rule loop in `production.py`; Grand Sport/Z06 use shared `rules.py` `build_draft_rules()`. Normalize to one shared builder; express Stingray differences in workbook rows/schema fields.
4. **Fallback-constant retirement** — remove Python/JS fallback constants only after proving every promoted model has workbook-owned replacements (post-Pass E follow-up).
5. **Copy allowlist residuals** — residual copy allowlist decisions deferred from Pass 7.
6. **Naming drift residuals** — Stingray exclusive-group ID/style drift and Z06 option-ID suffix / no-RPO drift, both deferred from Pass 7.

Do not add audit/report checks back to default readiness gates without proving a current runtime-contract failure they uniquely catch.
