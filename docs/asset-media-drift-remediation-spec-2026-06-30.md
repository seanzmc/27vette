# Spec: Asset/Media Drift Remediation (validates 2026-06-30 audit)

Status: proposed, awaiting approval per AGENTS.md Section 4. No code changed by this document.

## 0. Validation of the audit

Repo state: `git status --short` clean at HEAD `1e3fa24`, matching the audit's stated baseline.

Re-inspected source for every cited finding rather than trusting the audit's line numbers at face value:

- Finding 3 (asset_map_sync identity collapse): confirmed. `asset_map_sync.py` keys `desired` and `existing_rows` by `(model_key, target_id)` at lines 390, 411, 426, 436-455, 555 — `target_type` is dropped. `contract.py:42` proves the canonical identity is `(target_type, target_id)` per model. The three target namespaces (`opt_*` option ids, bare `model_key`/`registry_key` model ids, `body_style__*` context-choice ids) don't currently overlap, so this is latent, not active.
- Finding 4 (no duplicate-row guard): confirmed. `contract.py:31-43` builds `assets[(target_type, target_id)] = fields` with a plain dict comprehension-style loop — a later duplicate active row silently overwrites an earlier one. Grepped `schema_validation.py` for `asset_map`: zero matches, so no validation layer catches this either.
- Finding 7 (dual assembly paths): confirmed. `source_assembly.py:35-56` branches on `config.model_key == "stingray"` to call `production.build_production_source_data()`; every other active model goes through `inspect_model_sources` / `build_contract_preview` / `build_form_data_draft`. Both converge on `build_model_runtime_contract()`, matching the audit's claim that output is unified but logic is not.
- Finding 8 (hardcoded default-selected allowlist): confirmed, and one detail the audit didn't call out — `_DEFAULT_SELECTED_DISPLAY_RULE_IDS_BY_MODEL` in `runtime_metadata.py:20-26` has entries for `stingray` and `grand_sport` only. Z06 has no entry, so Z06 currently derives zero `default_selected` display behavior through this gate. Worth flagging to a product owner — may be intentional, may be a gap — but it's outside this spec's scope to change product behavior.
- Findings 5, 6, 9: confirmed by direct read — `contract.py:35` does exact `model_key` equality (no wildcard); `asset_map_sync.py:379-396` treats every active+selectable option row as a desired media target with no separate "should have an image" classification; `model_configs.py:161-165` still says Grand Sport generation "is not activated by the Stingray entrypoint" while the audit's own promoted-models list shows Grand Sport is promoted; `production.py:400-403,643` still gates on legacy `active_for_stingray`; `app.js:1163-1165` hardcodes `sec_incl_001` for summary bucket routing.
- Reran `tests/test_asset_map_sync.py`: 19 passed, matching the audit. (Ran via system Python + pip-installed pytest/openpyxl in this sandbox, since the repo's `.venv` is a macOS-host venv with a broken interpreter symlink here — not reproducible in this container. Use the project `.venv` on the host for any real validation run.) Did not re-run the Node suite or re-derive workbook row counts (192 active asset_map rows, 268 flag_missing, etc.) — those require opening `stingray_master.xlsx`, which this audit step didn't need to touch and which AGENTS.md says not to write casually. No reason in the codebase to doubt them.

Conclusion: the audit's findings and risk reasoning hold up against the current code. The disagreement in this spec is about **sequencing**, not facts — see below.

## 1. Re-ranking by drift risk, not by stated label

The audit labels findings 3, 4, 6, 7, 8 all "medium." For *drift* specifically — meaning two representations of the same fact/policy that can silently diverge as models and assets are added — they are not equivalent:

- **Findings 3 and 4 are the same root cause**: the asset_map identity model is enforced in one place (`contract.py`) and not in the two places that write/reconcile it (`asset_map_sync.py`, and the absence of any uniqueness check on load). Today it's silent-safe by accident (the three target-id namespaces don't collide), not by design. This is the only finding where a future data-entry mistake or a new target type would produce a *silently wrong* generated artifact with no error and no test failing. Highest drift risk.
- **Finding 7 is an active, ongoing duplication**: every media/metadata change to the generator has to be made twice (production.py and inspection.py) and kept manually consistent, with three live models depending on both paths staying in sync. This is the textbook drift mechanism and it's already in production. Second-highest.
- **Finding 8 is a structural duplication of authority**: workbook `default_selection_rules` are the stated source of truth, but a Python allowlist gates which of those rules actually get `default_selected` display behavior. Every new model or new default-selection row requires a matching Python edit that the workbook can't enforce or even surface as missing. Third-highest — same shape as Finding 7 but lower blast radius (one display flag, not the whole media/metadata path).
- **Findings 5 and 6 are maintenance-burden and workflow-noise risks**, not silent-correctness risks. They get worse as models/options grow, but a wrong value isn't produced — workbook authors do more repetitive work, or get a noisier report. Lower priority than 3/4/7/8.
- **Finding 9 is already-realized drift** (the stale Grand Sport "not activated" note, the legacy `active_for_stingray` gate, the hardcoded `sec_incl_001`), not a future risk. Cheap to fix, low blast radius, but doesn't compound the way 3/4/7/8 do.

This spec proposes four phases in that order. Phases 1-3 are the ones with "highest risk of creating drift"; Phase 4 is the audit's lower-risk remainder, included for completeness but not the focus of this remediation pass.

## 2. Phase 1 (highest priority): asset_map identity-key correctness

**Diagnosis**: `asset_map_sync.py` reconciles desired vs. existing asset rows keyed by `(model_key, target_id)`, while the runtime/generator loader (`contract.py:42`) keys by `(target_type, target_id)` per model. There is no uniqueness validation anywhere on active asset_map rows. Risk level: medium-now, but it is the only finding that degrades to silent wrong output with zero test or validation signal, which makes it highest priority to close before more models/target types are added.

**Exact files expected to change**:
- `scripts/corvette_form_generator/asset_map_sync.py` — `read_option_sheets`, `read_model_targets`, `read_bodystyle_targets`, `existing_asset_rows`, `reconcile` (and the `add_report` lookups keyed off `desired`) move from `(model_key, target_id)` to `(model_key, target_type, target_id)`.
- `scripts/corvette_form_generator/schema_validation.py` (or `contract.py`'s `load_asset_map`, whichever owns workbook-row validation today) — add a duplicate-active-row check on `(model_key, target_type, target_id)` that fails loudly instead of last-write-wins.
- `tests/test_asset_map_sync.py` — add a case with the same `target_id` string under two different `target_type` values to prove no collision, plus a duplicate-active-row validation test.

**Source-of-truth decision**: generator/tooling fix only. No workbook rows change. The workbook's existing `target_type` column already carries the right information; the code is what's behind the contract.

**Companion-file impact check**:
- `contract.py` — inspected, no change (already correct).
- `form-app/app.js`, `form-app/data.js` — not applicable, no runtime/generated-data shape change.
- Report CSV emitted by `sync_asset_map.py` — inspected; audit's own smallest-safe-pass note says keep it unchanged or add explicit key fields only. Confirm column additions are additive, not a rename, so any existing report consumers don't break.
- README/AGENTS.md — not applicable; this doesn't change a documented workflow.

**Constraints**: no workbook writes; no change to `contract.py`'s already-correct keying; no unrelated refactor of `asset_map_sync.py` beyond the key shape; preserve current report CSV columns.

**Risks / non-goals**: not fixing this does not break today's data (0 active duplicates currently), so this is a guard against future drift, not a live bug fix. Non-goal: this phase does not add wildcard/shared rows (that's Phase 4) and does not change media-coverage policy (Phase 4).

**Validation plan**: `.venv/bin/python -m pytest tests/test_asset_map_sync.py -q`; run the report-only sync probe again and confirm `keep`/`flag_missing`/`writes`/`inserts` counts are unchanged from the audit's baseline (192/268/0/0) since this phase is a pure identity-key correctness fix with no behavior change on current data; `.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx`.

## 3. Phase 2: converge duplicated media/metadata assembly logic

**Diagnosis**: `source_assembly.py:35-56` routes Stingray through `production.build_production_source_data()` and Grand Sport/Z06 through `inspect_model_sources`/`build_contract_preview`/`build_form_data_draft`. Both paths independently merge asset_map media (`production.py:203-204,282-284,390-391` vs. `inspection.py:668-697,976,1016,1063-1064`). Every media/metadata change must be hand-kept consistent across both paths today, with three live models depending on that consistency holding.

**Exact files expected to change**: new shared helper module (exact location TBD during implementation — likely alongside `contract.py` since that's the existing shared-helpers home) extracting the media/context-choice/choice-row assembly logic out of `production.py` and `inspection.py` into one implementation called by both. `production.py` and `inspection.py` are reduced to calling the shared helper. `source_assembly.py` itself does not need to change in this phase — Stingray keeps its compatibility-source path, it just stops duplicating assembly logic.

**Source-of-truth decision**: generator/tooling refactor. No workbook or runtime-contract shape change — this phase is explicitly an extraction, not a behavior change.

**Companion-file impact check**:
- `form-output/*-runtime-contract.json` (all three models) — must be byte-for-byte (or semantically) identical before/after; this is the parity bar the audit recommends.
- `form-app/data.js` — inspected, not applicable if contracts are unchanged.
- `tests/multi-model-runtime-switching.test.mjs`, `tests/stingray-generator-stability.test.mjs`, `tests/grand-sport-draft-data.test.mjs`, `tests/z06-form-data-draft.test.mjs` — must continue passing unchanged; these are the existing parity net.
- `production.py:651-690` compatibility artifact writing — explicitly preserved, Stingray-only, not touched in this phase per the audit's own smallest-safe-pass guidance.

**Constraints**: do not remove Stingray's compatibility artifacts; do not route Stingray through the same `source_assembly` branch as Grand Sport/Z06 yet (that's the audit's deferred item D, separate and larger); prove parity for all three runtime contracts before/after; no unrelated cleanup of `production.py`/`inspection.py` beyond the extraction.

**Risks / non-goals**: this is the largest diff of the three phases and touches the most-tested surface (model generation for all three active models). Non-goal: this phase does not converge Stingray onto the Grand Sport/Z06 assembly path — that remains explicitly deferred (audit item D) because it's a bigger, separate risk once this phase proves the shared helpers are correct.

**Validation plan**: regenerate all three model artifacts and diff against pre-change artifacts (expect no diff or only intentional, explained diff); run the full generator test suite (`pytest`) plus `node --test tests/multi-model-runtime-switching.test.mjs`; manual smoke of model switching in the static app for all three models.

## 4. Phase 3: remove the hardcoded default-selected allowlist as a structural drift source

**Diagnosis**: `runtime_metadata.py:20-26` gates which workbook `default_selection_rules` become `display_behavior=default_selected` through a hardcoded `_DEFAULT_SELECTED_DISPLAY_RULE_IDS_BY_MODEL` allowlist, applied at `runtime_metadata.py:302-340`/317-322. The workbook is still the rule owner, but a code allowlist intercepts which rules get display treatment — a second source of truth that must be hand-updated whenever a new model or new default-selection row needs this behavior. Z06 currently has no entry, so it gets none of this display behavior; that's a side effect worth surfacing to a product owner before this phase starts, since the fix could either (a) make Z06 newly eligible or (b) need an explicit decision that Z06 doesn't want this yet.

**Exact files expected to change**: `scripts/corvette_form_generator/runtime_metadata.py` (remove or replace the allowlist gate with a workbook-authored signal — e.g., a column/flag on `default_selection_rules` rows themselves). Possibly the workbook schema (`default_selection_rules` sheet) if the audit's recommended fix ("move default-selected presentation intent fully into workbook-authored rows/metadata") is adopted, which would make this a workbook + generator change, not generator-only.

**Source-of-truth decision**: needs a decision before implementation — this is the one phase where the audit's "smallest safe pass" implies a workbook schema change, which is a bigger surface than a pure code fix. Recommend resolving the Z06-gap question with a product owner first, then deciding whether the workbook gets a new authoring surface or whether the allowlist is simply expanded/parameterized without a schema change as an interim step.

**Companion-file impact check**: `model_configs.py` (no expected change, but inspect for related model-specific gates); generated runtime contracts for all three models (display_behavior field); runtime tests asserting `default_selected` behavior; `form-app/app.js` consumers of `display_behavior`.

**Constraints**: keep generated output parity for Stingray and Grand Sport (the two models with existing allowlist entries) unless a product decision explicitly changes Z06 behavior; add a test that fails if new default-selection display behavior requires a Python edit, per the audit's own recommendation.

**Risks / non-goals**: touches workbook schema if the full fix is adopted — higher process cost (Excel-closed check, safe-save, schema validation, on-disk verification per AGENTS.md Section 7). Non-goal: this phase does not change which rows in `default_selection_rules` exist today, only how the existing rule set gets translated into display behavior.

**Validation plan**: `validate_workbook_schema.py` if the workbook changes; full generator regeneration with contract diff review for all three models; targeted runtime tests for default-selection display behavior; explicit confirmation with a product owner on the Z06 gap before or alongside this phase.

## 5. Phase 4 (lower priority, included for completeness): the audit's remaining items

Not the focus of this remediation pass, but tracked so they aren't lost:

- **Finding 5** (wildcard/shared asset_map rows): reduces workbook maintenance burden as models grow, not a correctness-drift risk. Pursue after Phase 1 lands so the identity-key fix and any wildcard matching logic aren't built on the same change at the same time.
- **Finding 6** (media coverage policy too broad): add a workbook/metadata-derived "image expected" classification so the 268 `flag_missing` rows aren't dominated by non-visual sections. Workflow-quality fix, no runtime risk.
- **Finding 9** (stale labels/notes, legacy `active_for_stingray` gate, hardcoded `sec_incl_001`): cheap, low-risk cleanup. The Grand Sport stale note in `model_configs.py:161-165` is worth an immediate doc-only fix independent of this spec's approval, since it's actively misleading (says "not activated" about a promoted model) and AGENTS.md treats stale-note cleanup as low-ceremony.

## 6. Overall constraints (apply to all phases)

- Spec-first per AGENTS.md Section 4: wait for approval before implementing any phase.
- No workbook writes without an explicit Excel-closed check and on-disk save verification (AGENTS.md Section 7).
- No dependency additions.
- Each phase regenerates and diff-reviews affected artifacts; no hand-editing generated output.
- Each phase's handoff reports companion-surface impact as updated / inspected-no-change / not applicable, per AGENTS.md Section 13.

## 7. Suggested sequencing

Phase 1 first (smallest, closes the only silent-correctness gap), then Phase 2 (largest test surface, do it next while Phase 1's parity habits are fresh), then Phase 3 (needs a product decision on the Z06 gap, so start that conversation now in parallel even though implementation comes third), then Phase 4 opportunistically.
