# Route map (current)

Condensed 2026-07-05 from the completed audit program logs. Pass-by-pass history (route-map passes 0-20, cleanup passes A-E) lives in
`docs/archive/completed-specs/audit-cleanup/Audit-route-map.md` and
`docs/archive/completed-specs/audit-cleanup/audit-cleanup-overview.md`, with per-pass specs alongside them.

## Active routes

**Model generation**

`stingray_master.xlsx` → `scripts/generate_form.py --model <active-model>` → `model_generation.generate_model_artifacts()` → `source_assembly.assemble_model_source()` → `build_model_runtime_contract()` → `form-output/runtime/<slug>-runtime-contract.json` → `generate_registry.py` → `form-app/data.js`.

- Active/generatable models are workbook-discovered (`model_master.active`, exact-match active `model_workbook_sources`, active `model_variants`); there is no hardcoded model list.
- `runtime_contract` is the only promotable artifact type. Promotion rows require explicit `artifact_path` values; there is no generated-output fallback.
- Normal generation writes one strict runtime contract. Optional source/preview/draft diagnostics exist only behind `--emit-inspection --inspection-output <dir>` and are not readiness or publication authority.
- `generate_registry.py` is the only writer of `form-app/data.js`; it supports isolated workbook/root/output paths and writes atomically.
- The default gate lane generates below temporary roots and checks that `form-output/` and `form-app/` remain byte-identical. Registry publication is a separate isolated gate.
- `scripts/compare-generated-contracts.mjs` strips only timestamp keys then deep-compares — a strict no-drift parity check, not a validator for approved shape/path migrations.

**Retired raw ingest**

The former ingest wizard, canonical compiler/exception queue, ChangeSet emitter, ingest-specific deployment proof, and browser UI were removed on 2026-07-23 because their imported data was not trustworthy enough to remain an executable route. Historical evidence is archived under `docs/archive/retired-ingest/2026-07-23/`; it is not a current route or implementation template. The generic workbook-domain ChangeSet service remains only as the approved target write contract for later Workbook Manager passes.

## Philosophy constraints

- The workbook owns Corvette product data and business rules; `form-output/*` and `form-app/data.js` are outputs — never hand-edit as source-of-truth fixes.
- Generators read workbook tables, normalize, validate, emit. No hidden model/RPO-specific Python branches when a workbook row can express the decision.
- Runtime JavaScript renders and evaluates generated contracts generically; product facts belong in workbook-authored metadata.
- Dealer submission endpoint, payload shape, Turnstile behavior, and live model registry semantics are out of scope unless a spec names them.
- Route/artifact changes are parity-first: timestamp-normalized contract comparison for no-behavior-change passes; targeted consumer/promotion checks for approved migrations.

## Protected current surfaces

- `runtime_action=replace` and `body_style_scope` are live direct-rule behavior consumed by `form-app/app.js` (Pass 8 classified every row; see archived report). Any migration needs generated/runtime parity proof per behavior.
- Model-scoped variant override sheets (`stingray_variant_overrides`, `grandSport_variant_overrides`, `z06_variant_overrides`) own trim-standard placement/selectability (UQT) after Pass 18; the global sheet is retired (Pass 19).
- `window.STINGRAY_FORM_DATA` remains the active browser-registry alias for the published Stingray runtime contract.
- The six retained `form-output/runtime/*-runtime-contract.json` files are current generated contracts. The six `form-output/inspection/*-derived-swap-manifest.json` files remain explicit derivation diagnostics until their owning follow-up retires them.

## Open bounded follow-ups

1. **Exclusive-group runtime peer guard** — `app.js` ignores same-group explicit excludes only when the rule targets a choice, not when the choice is the source. Workbook rows are clean and the schema gate blocks recurrence; changing runtime behavior is a separate pass.
2. **Registry type drift** — nine workbook cells still contain text where the workbook-domain registry declares bool/int. The schema gate pins that exact allowlist; correcting the cells requires a scoped workbook write.

Do not add audit/report checks back to default readiness gates without proving a current runtime-contract failure they uniquely catch.
