# Spec: Phase 4C — stale-note and runtime-summary hardcode cleanup

Status: Spec only. Do not implement until approved.

Parent: `docs/asset-media-drift-remediation-spec-2026-06-30.md` Section 5 / audit Finding 9 (`docs/asset_media-audit-6-30.md`). Predecessors: 4A, 4B (both Implemented 2026-07-01). Successor queued: 4D wildcard/shared `asset_map`.

Recommended reasoning level for implementation: medium-high (one runtime-behavior change with contract parity requirements; the rest is low-risk cleanup, but the summary-bucket derivation must be proven behavior-preserving, not assumed).

## 0. Re-validation at time of writing

- `form-app/app.js:1163-1168`: `autoAddedOptionUsesRequiredSummaryBucket(option)` returns `option?.section_id === "sec_incl_001"`; auto-added options in that section route to the `auto_added_required` order-summary bucket. This is the last hardcoded order-summary routing constant — the README states orderSummary grouping is otherwise workbook-owned via generated `orderSummary.sections`/`stepMap`, which app.js reads (`orderSummarySections()`, `orderSummaryStepMap()`, hard-fail on missing metadata at app.js:1139).
- `auto_added_required` section_key exists in all three promoted runtime contracts' `orderSummary.sections` (workbook `order_summary_sections` rows) and is consumed at app.js:2627, 2660-2661; regression coverage: `stingray-form-regression.test.mjs:1244,1275`, `stingray-generator-stability.test.mjs:187`.
- `scripts/corvette_form_generator/model_configs.py:161-165`: `_MODEL_NOTES["grand_sport"]` says "Read-only inspection only: Grand Sport generation is not activated by the Stingray entrypoint" — stale; Grand Sport is promoted and live. Notes flow into `ModelConfig.notes` (consumers: inspection/draft artifacts only).
- `model_configs.py:150-159`: `GRAND_SPORT_SECTION_LABEL_OVERRIDES` (4 labels) duplicated verbatim by active workbook `section_presentation.display_label` rows for grand_sport (verified in 4B-era probe: sec_gsce_001, sec_gsha_001, sec_spec_001, sec_colo_001). Production path reads workbook `display_label` (`production.py:248,291`); the code dict is consumed only by `inspection.py:198-199` label fallback.
- `section_presentation` for sec_incl_001: active rows with `standard_equipment_bucket=True` exist for all three models (no `standard_equipment_group_type`, unlike trim-equipment sections which carry `trim_equipment`).
- Audit Finding 9 also lists `production.py` Stingray-only legacy path items (`:161-169`, `:397-403` `active_for_stingray`); see non-goals.

## 1. Diagnosis

Three code-owned facts that belong to workbook/docs surfaces, per AGENTS.md §3:

1. Runtime hardcode (the real behavior item): app.js decides which auto-added options land in the "Auto-Added / Required" summary bucket by matching a literal section id. Adding a future section with the same semantics (or renaming sec_incl_001) silently breaks summary routing with no workbook control.
2. Stale note: `_MODEL_NOTES` grand_sport text contradicts live promotion state; it leaks into inspection/draft artifacts and misleads future agents.
3. Redundant code labels: the GS section-label dict duplicates workbook-authored `section_presentation.display_label`; two owners for the same fact violates single-ownership and will drift.

Risk: item 1 medium (runtime + contract change, behavior must be preserved exactly); items 2-3 low (inspection-artifact strings only). Change class: runtime behavior + generator/contract + docs/config cleanup — separable, so implementation must land item 1 with full gates and items 2-3 as cheap riders.

## 2. Recommended smallest safe pass

### 2.1 Workbook-owned summary-bucket routing (behavior-preserving)

Replace the app.js literal with generated metadata:

- Generator: emit a boolean field on each generated choice row, `auto_added_summary_required` (name final at implementation; additive, runtime contract only), derived from workbook metadata for the option's section. Derivation source, in preference order:
  a. If existing metadata already isolates exactly sec_incl_001 per model (e.g. `section_presentation` rows with `standard_equipment_bucket=True` and no `standard_equipment_group_type`), prove that predicate reproduces current behavior on all three contracts and use it — no workbook write needed.
  b. If (a) is not exact, add an explicit workbook column instead (`order_summary_sections` or `section_presentation`, e.g. `auto_added_bucket=True` for the intended sections) — a workbook write under full AGENTS.md §5 safety, seeded to preserve current behavior exactly (sec_incl_001 only, all three models).
  Decision between (a)/(b) is an implementation checkpoint: report which branch was taken and the parity evidence before proceeding to the runtime edit.
- Runtime: `autoAddedOptionUsesRequiredSummaryBucket(option)` reads the generated field (`option?.auto_added_summary_required === true`); no literal section ids. Fallback behavior if the field is absent: false (option routes to the normal bucket) — acceptable because regenerated contracts are a hard prerequisite of this pass and app.js already hard-fails on missing orderSummary metadata.
- Contract diff must show only the additive field (plus timestamps); every current `auto_added_required` summary row must be identical before/after.

### 2.2 Stale-note cleanup

Rewrite `_MODEL_NOTES["grand_sport"]` to current truth (promoted runtime model; options read from normalized `grandSport_options`). Touch nothing else in the dict.

### 2.3 Retire redundant GS label dict

Delete `GRAND_SPORT_SECTION_LABEL_OVERRIDES` / `_SECTION_LABEL_OVERRIDES_BY_MODEL` and the `inspection.py:198-199` fallback, making inspection read the same workbook `section_presentation.display_label` path production uses. Precondition (verify, don't assume): every label in the dict has a matching active workbook row. If any is missing, add the workbook row first (§5-gated write) rather than keeping the dict. If `ModelConfig.section_label_overrides` becomes dead, remove the field and its `model_config.py` default.

## 3. Exact files expected to change

1. `scripts/corvette_form_generator/production.py` (and/or the shared contract assembly touched in Phase 2) — emit `auto_added_summary_required` on generated choice rows from the §2.1 derivation.
2. `form-app/app.js` — `autoAddedOptionUsesRequiredSummaryBucket` reads the generated field.
3. `scripts/corvette_form_generator/model_configs.py` — §2.2 note fix; §2.3 dict removal.
4. `scripts/corvette_form_generator/inspection.py` — §2.3 fallback removal.
5. `scripts/corvette_form_generator/model_config.py` — remove `section_label_overrides` field if dead.
6. `form-output/runtime/*-runtime-contract.json`, `form-output/stingray-form-data.{json,csv}`, `form-app/data.js` — regenerated (all three models + registry).
7. `stingray_master.xlsx` — ONLY if §2.1(b) or the §2.3 precondition requires it; report as a distinct changed surface with §5 evidence.
8. Tests: extend `stingray-form-regression` / `stingray-generator-stability` (and Z06/GS contract tests if bucket rows appear there) to pin the new field's derivation and that summary routing is unchanged; add a generator test that the field appears only for the intended sections; keep/extend the existing `auto_added_required` assertions as the behavior-parity guard.
9. `docs/asset_media-audit-6-30.md` — status update on Finding 9 items resolved by this pass.
10. This spec — close per AGENTS.md §11.

## 4. Source-of-truth decision

Summary-bucket membership becomes workbook-derived generated metadata (workbook → generator → contract → runtime), removing the last hardcoded order-summary constant from app.js. Labels consolidate to the existing workbook `section_presentation.display_label` owner. Notes are code-owned config strings and just get corrected.

## 5. Companion-file impact check

- Generated contracts / `form-app/data.js`: regenerated; diffs reviewed for additive-field-only churn.
- `runtime_metadata.py`, `contract.py`: inspect for where choice rows are assembled; update only if the field emission lands there instead of `production.py`.
- Runtime tests (`multi-model-runtime-switching`, model regression/stability suites): run; extend where they pin summary buckets.
- `workbook-schema-standardization.test.mjs`: inspect only if §2.1(b)/§2.3 add a workbook column/rows.
- Workbook editor: not applicable unless a new column is added (then it appears via `model_workbook_sources`-registered sheets only; `section_presentation` is metadata/read-only in the editor — acceptable, authoring stays CLI/ops-gated).
- Dealer submission: untouched; summary-bucket routing feeds display and download grouping, so §8 verifies download/summary output, and payload construction must be confirmed unaffected.

## 6. Constraints

Standing constraints from AGENTS.md apply (§3, §4, §5 if any workbook write, §6). Spec-specific:

- Behavior parity is the gate: current auto-added summary grouping for all three models must be byte-identical in rendered semantics (same options in `auto_added_required`, same ordering) before/after.
- New contract field is additive; no renames/removals of existing generated fields.
- No new hardcoded section ids anywhere in Python or JS — the point of the pass. Derivation predicates must be generic metadata reads.
- Items 2.2/2.3 must not alter generated runtime contracts at all (inspection artifacts may change strings).
- production.py Stingray-only legacy path: do not touch (non-goal).

## 7. Risks and non-goals

Risks:

- The §2.1(a) predicate may accidentally match more sections than sec_incl_001 on some model (e.g. other bucket rows without group_type), changing routing. Mitigation: the implementation checkpoint requires enumerating matched sections per model against current behavior before any runtime edit; fall back to (b) explicit column on any mismatch.
- Regeneration may surface unrelated drift if the working tree's uncommitted 4A/4B changes interact with generator output. Mitigation: generator/runtime code changed here doesn't overlap asset_map_sync; review regenerated diffs and flag any non-additive churn as a stop condition.
- Removing the inspection label fallback changes opt-in inspection artifact strings if a workbook row is missing. Mitigation: §2.3 precondition check.

Non-goals: production.py legacy Stingray-only path and `active_for_stingray` validation (larger legacy-path retirement, separate spec); wildcard/shared `asset_map` (4D); any change to which sections exist or their workbook rows beyond the minimal §2.1(b)/§2.3 additions; dealer payload changes; UI redesign.

## 8. Validation plan

Run in order, report exact output:

1. Implementation checkpoint (§2.1): script/probe enumerating, per model, the sections matched by the chosen derivation vs the literal sec_incl_001 behavior — must be exactly equal, or switch to (b) and re-prove.
2. If workbook written: §5 on-disk verification + `validate_workbook_package.py` + negative typo check not required (boolean/rows only), then `validate_workbook_schema.py`.
3. Regenerate all three models + registry; `git diff` on contracts/data.js shows only the additive field + timestamps; every existing `auto_added_required` summary row unchanged.
4. `.venv/bin/python -m pytest tests/test_model_config_metadata.py -q` (model_configs changed) and any Python tests touching removed symbols.
5. `node --test` per README test-to-surface table: Stingray pair, GS pair, Z06 five, `z06-runtime-promotion`, `multi-model-runtime-switching`, `workbook-schema-standardization`, `workbook-visual-copy-standardization`.
6. Browser smoke (runtime behavior changed): serve form-app; per model verify auto-added rows (e.g. Stingray G0K package adds) land in "Auto-Added / Required", selected-options summary excludes them, totals unchanged, build download grouping unchanged; dealer modal opens and validates (no submission).
7. `git diff --check`; confirm `stingray_master.xlsx` diff empty unless §2.1(b)/§2.3 declared it.

Gates intentionally not required: live dealer submission (AGENTS §6); live WordPress media (out of surface); ingest suites.

## 9. Handoff requirements

Follow AGENTS.md §11. Spec-specific additions:

- Which §2.1 branch was taken (a or b) with the per-model section-match evidence.
- Regenerated-contract diff summary proving additive-only churn and unchanged auto_added_required rows.
- Browser-smoke checklist results per model.
- Whether `section_label_overrides` was fully removed or retained (and why).
- Confirmation Finding 9's remaining unresolved items (production.py legacy path) are documented as the leftover, and whether 4D or the legacy-path retirement should go next.

## 10. Approval prompt

Approve Phase 4C:

- Replace the app.js `sec_incl_001` hardcode with a workbook-derived generated choice field (`auto_added_summary_required`), behavior-preserving, with regeneration + full runtime gates + browser smoke.
- Fix the stale Grand Sport `_MODEL_NOTES` text.
- Retire the redundant GS section-label dict in favor of workbook `section_presentation.display_label` (precondition-checked).
- Workbook write only if the metadata derivation or label precondition requires it (§5 safety); production.py legacy path deferred.
