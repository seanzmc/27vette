# Spec: Phase 2 — converge duplicated media/metadata assembly logic (generator/tooling extraction)

Status: implemented 2026-06-30. Generator/tooling extraction landed with parity-preserving validation;
generated timestamp-only churn was restored before handoff.

Parent: `docs/asset-media-drift-remediation-spec-2026-06-30.md` (Section 3, "Phase 2"). This file is the
standalone, exact spec for that phase, written for direct implementation. Phase 1 is complete (see
`docs/asset-media-drift/phase-1-asset-map-identity-key.md`); Phases 3-4 from the parent spec are out of
scope here and are not restated except where needed for context.

## 0. Re-validation at time of writing this phase spec

Repo state: `git status --short --branch` shows `main...origin/main [ahead 1]`, tree clean at HEAD
`d8cb649` (Phase 1 merged: `feat: Finalize Phase 1 of asset_map identity-key correctness with validation
updates and test coverage`).

Re-confirmed the parent spec's Finding 7 claims directly against current source (the parent spec's line
numbers have drifted since Phase 1 landed; the duplication shape has not):

- `scripts/corvette_form_generator/source_assembly.py:26-56` (`assemble_model_source`) branches on
  `config.model_key == "stingray"`:
  - Stingray calls `production.build_production_source_data(config)` (line 38).
  - Every other active model (`grand_sport`, `z06`) calls `inspect_model_sources(config)` (line 46),
    `build_contract_preview(config)` (line 47), then `build_form_data_draft(config, preview=preview)`
    (line 48).
  - Both branches finalize through `build_model_runtime_contract(config, source_data)` (lines 42, 52),
    confirming the audit's claim that output is unified but assembly logic is not.
- Both `production.py` and `inspection.py` independently import and call the same `contract.py` helpers
  (`bodystyle_asset_map`, `option_asset_map`/`load_asset_map`, `build_body_context_choices`,
  `build_trim_context_choices`, `context_choice_copy_rows`, `ASSET_IMAGE_FIELDS`) but assemble the
  choice/context-choice rows independently:
  - `production.py:203-204` loads `option_assets = option_asset_map(wb, MODEL_CONFIG.model_key)` and
    `bodystyle_assets = bodystyle_asset_map(wb, MODEL_CONFIG.model_key)`; `production.py:282-284` builds
    `context_choices` via `build_body_context_choices(...) + build_trim_context_choices(...)`;
    `production.py:390-391` merges `option_assets.get(option_id)` onto each choice row inline inside the
    per-variant choice-building loop (lines 332-392).
  - `inspection.py:669` loads `bodystyle_assets = bodystyle_asset_map(wb, config.model_key)` inside
    `build_contract_preview` (no `option_asset_map` call here — option-level assets are deferred to
    `build_form_data_draft`); `inspection.py:695-697` builds the same `context_choices` shape via the same
    two helper calls. `inspection.py:976` loads `asset_map = load_asset_map(wb, config.model_key)` inside
    `build_form_data_draft`; `inspection.py:1016` merges `asset_map.get(("option", option_id), {})` onto
    `option_rows[option_id]` once per option (not per choice); `inspection.py:1063-1064` conditionally
    re-applies `ASSET_IMAGE_FIELDS` onto each draft choice only `if option.get("image_url")`.
  - These are two independently-written merge points with different merge granularity (per-choice in
    `production.py` vs. per-option-then-conditional-per-choice in `inspection.py`) that happen to produce
    compatible output today because `asset_fields()` in `contract.py:21-22` always returns the full
    `ASSET_IMAGE_FIELDS` tuple (blank-filled), so `option.get("image_url")` is a reasonable but
    independently-invented gate that `production.py`'s unconditional `choice.update(asset)` does not need.
- This confirms the audit's diagnosis: every media/metadata assembly change has to be hand-kept
  consistent across two independently-maintained implementations, with three live models (`stingray`,
  `grand_sport`, `z06`) depending on that consistency holding. It is the textbook drift mechanism the
  audit flagged as second-highest risk after Phase 1's identity-key issue (which is now closed).
- Context-choice assembly (`build_body_context_choices` / `build_trim_context_choices` calls at
  `production.py:282-284` and `inspection.py:695-697`) is already byte-identical in argument shape between
  the two call sites — same four/three positional arguments in the same order. This is the lowest-risk
  extraction target and a good first slice.
- Option-asset merge is NOT byte-identical in shape: `production.py` merges per-choice from a
  `dict[option_id -> fields]` keyed only by option id (`option_asset_map`, which drops `target_type` since
  it pre-filters to `target_type == "option"` — see `contract.py:46-53`); `inspection.py` merges
  per-option from the full `dict[(target_type, target_id) -> fields]` (`load_asset_map`) using an explicit
  `("option", option_id)` key, then copies from that source option row to each new draft choice only when
  the source option row has `image_url`. This is a deliberate-looking but unverified behavioral difference
  (per-choice vs. per-option vs. conditional-on-source-image) and is the actual risk surface this phase must
  prove parity on, not just extract verbatim.
- Existing generated artifacts on disk to baseline against: `form-output/runtime/stingray-runtime-contract.json`,
  `form-output/runtime/grand-sport-runtime-contract.json`, `form-output/runtime/z06-runtime-contract.json`,
  plus Stingray's compatibility `form-output/stingray-form-data.json` / `.csv`. `scripts/compare-generated-contracts.mjs`
  exists and is the established parity comparator (ignores timestamp keys only).
- Test inventory for parity coverage: `tests/stingray-generator-stability.test.mjs` (14 tests),
  `tests/grand-sport-draft-data.test.mjs` (19), `tests/grand-sport-contract-preview.test.mjs` (6),
  `tests/z06-form-data-draft.test.mjs` (24), `tests/z06-contract-preview.test.mjs` (3),
  `tests/multi-model-runtime-switching.test.mjs` (46). These are the existing parity net the audit and
  parent spec point to; counts reconfirmed live via `grep -c "^test("`, not trusted from the parent audit.

Conclusion: the parent spec's Phase 2 diagnosis holds, and direct inspection surfaces a real risk the
parent spec's prose only implied — the two merge points are not provably equivalent today, only
coincidentally compatible. This phase must prove behavioral equivalence, not just extract code.

## 1. Diagnosis

`source_assembly.py` routes Stingray through `production.build_production_source_data()` and Grand
Sport/Z06 through `inspect_model_sources` / `build_contract_preview` / `build_form_data_draft`. Both
paths independently call the same `contract.py` asset/context-choice helpers but assemble the resulting
choice and context-choice rows with separately written, separately maintained code:

- Context-choice assembly (`build_body_context_choices` + `build_trim_context_choices` calls) is
  call-shape-identical across both paths today.
- Option-asset merge differs in granularity and conditioning between the two paths (per-choice
  unconditional merge in `production.py` vs. per-option source-row merge gated on the source option row's
  existing `image_url` in `inspection.py`), and is not proven equivalent.

Every future media/metadata assembly change (new asset field, new merge rule, new context-choice
behavior) must be hand-applied to both `production.py` and `inspection.py` and kept in sync by inspection
alone — there is no shared implementation and no test that would fail if the two drifted further apart in
a way that doesn't currently produce a visible diff. Risk level: medium, already realized as duplicated
maintenance burden today, with the added risk that the option-asset merge difference identified above may
already be latent drift rather than a no-op coincidence.

## 2. Exact files expected to change

1. `scripts/corvette_form_generator/contract.py` — add two new shared helper functions, alongside the
   existing `load_asset_map` / `option_asset_map` / `bodystyle_asset_map` / `build_body_context_choices`
   helpers already living in this module (the established shared-helpers home per the parent spec's own
   Section 3 note and per this module's existing role as the contract-surface helper file):
   - `build_model_context_choices(active_variants, context_copy_rows, model_key, body_style_display_order, bodystyle_assets)`
     — wraps the existing `build_body_context_choices(...) + build_trim_context_choices(...)` call shape
     already duplicated verbatim at `production.py:282-284` and `inspection.py:695-697`. Pure extraction,
     no behavior change — the call arguments and order are already identical at both sites.
   - `merge_option_asset_fields(destination_row, source_rows_by_option_id, *, only_if_image_present)` — a
     single shared merge function with an explicit, named boolean parameter for the granularity difference
     found in Section 0, rather than silently picking one behavior. The helper must read `option_id` from
     the destination row, retrieve the source row from `source_rows_by_option_id[option_id]`, optionally gate
     on the source row's `image_url`, and copy only `ASSET_IMAGE_FIELDS` from source to destination.
     `only_if_image_present=False` matches `production.py`'s current unconditional `choice.update(asset)`
     over option-asset rows; `only_if_image_present=True` matches `inspection.py`'s current `if
     option.get("image_url"): draft_choice.update(...)` gate, where `option` is the source option row from
     `option_rows`, not the newly-created `draft_choice` destination row. This makes the existing difference
     explicit and testable instead of resolving it by guessing which one is "more correct" — that decision
     is Section 6's approval gate, not this implementation step's to make silently.
2. `scripts/corvette_form_generator/production.py`
   - `build_production_source_data` — replace the inline `build_body_context_choices(...) +
     build_trim_context_choices(...)` call (lines 282-284) with `build_model_context_choices(...)`.
   - Replace the inline `if asset := option_assets.get(option_id): choice.update(asset)` (lines 390-391)
     with `merge_option_asset_fields(choice, option_assets, only_if_image_present=False)`, preserving
     current behavior exactly.
3. `scripts/corvette_form_generator/inspection.py`
   - `build_contract_preview` — replace the inline `build_body_context_choices(...) +
     build_trim_context_choices(...)` call (lines 695-697) with `build_model_context_choices(...)`.
   - `build_form_data_draft` — keep the existing line-1016 source-row timing where
     `option_rows[option_id]` is merged with `asset_map.get(("option", option_id), {})` once before the
     per-variant loop, then replace only the inline `if option.get("image_url"):
     draft_choice.update({field: option.get(field, "") for field in ASSET_IMAGE_FIELDS})` (lines 1063-1064)
     with `merge_option_asset_fields(draft_choice, option_rows, only_if_image_present=True)`. The helper
     must gate on the source `option_rows[option_id]["image_url"]`, not on the newly-created `draft_choice`,
     because `draft_choice` has no image fields yet at construction time. Do not force both files into an
     identical call shape if that would change which row the merge mutates or when.
4. `tests/test_corvette_form_generator_contract.py` (or the established test file for `contract.py`
   helpers — confirm exact filename during implementation; if no dedicated test file exists for
   `contract.py` today, add a small one following the `tests/test_schema_validation_metadata.py` /
   `tests/test_asset_map_sync.py` naming and `unittest` convention already used for this package's Python
   test coverage) — unit tests for the two new shared helpers:
   - `build_model_context_choices` returns the same shape as the existing direct
     `build_body_context_choices(...) + build_trim_context_choices(...)` call for representative
     fixture input.
   - `merge_option_asset_fields` with `only_if_image_present=False` always copies available
     `ASSET_IMAGE_FIELDS` from the source row selected by `destination_row["option_id"]` (matching today's
     `production.py` behavior); with `only_if_image_present=True` it copies only when `image_url` is already
     present on that source row (matching today's `inspection.py` behavior); it does not inspect the
     destination row for `image_url`; it does not copy non-asset fields; and it is a no-op when no source
     entry exists for the given option id, in both modes.
5. No changes to `tests/stingray-generator-stability.test.mjs`, `tests/grand-sport-draft-data.test.mjs`,
   `tests/grand-sport-contract-preview.test.mjs`, `tests/z06-form-data-draft.test.mjs`,
   `tests/z06-contract-preview.test.mjs`, `tests/multi-model-runtime-switching.test.mjs` — these are the
   existing parity net and must continue passing unmodified, proving the extraction did not change runtime
   contract output for any of the three active models.

## 3. Source-of-truth decision

Generator/tooling extraction only. No workbook rows change, no workbook schema change, no
runtime-contract shape change. `contract.py` already owns the underlying asset/context-choice helpers
this phase extracts a thin shared call-shape around; `production.py` and `inspection.py` keep their
existing per-model orchestration responsibilities (variant/section/option assembly, status resolution,
display-behavior resolution) — only the two duplicated media-merge call sites move to a shared
implementation.

## 4. Companion-file impact check

- `form-output/runtime/stingray-runtime-contract.json`, `form-output/runtime/grand-sport-runtime-contract.json`,
  `form-output/runtime/z06-runtime-contract.json` — must be byte-for-byte (or
  `compare-generated-contracts.mjs`-equivalent, timestamp-only-diff) identical before/after regeneration.
  This is the explicit parity bar.
- `form-output/stingray-form-data.json`, `form-output/stingray-form-data.csv` — Stingray's compatibility
  artifacts; JSON must remain unchanged after timestamp normalization because `production.py:623-629`
  writes a fresh `dataset.generated_at` on normal regeneration and `scripts/compare-generated-contracts.mjs`
  already ignores generated timestamp keys. CSV must remain byte-identical, since the compatibility
  artifact writing shape is explicitly preserved and not touched by this phase.
- `form-app/data.js` — inspected, not applicable if all three runtime contracts are unchanged; do not run
  `generate_registry.py` as a "fix" if a real diff appears — a real diff means the extraction introduced a
  behavior change and must be investigated, not republished.
- `tests/stingray-generator-stability.test.mjs`, `tests/grand-sport-draft-data.test.mjs`,
  `tests/grand-sport-contract-preview.test.mjs`, `tests/z06-form-data-draft.test.mjs`,
  `tests/z06-contract-preview.test.mjs`, `tests/multi-model-runtime-switching.test.mjs` — must continue
  passing unmodified; these are the count/ID-sensitive companion tests per the established checklist and
  the existing parity net for this exact kind of generator-internals change.
- `scripts/corvette_form_generator/source_assembly.py` — inspected; no change expected in this phase. The
  Stingray-vs-Grand-Sport/Z06 branch in `assemble_model_source` is explicitly preserved; this phase
  extracts shared sub-helpers called from both branches, it does not converge the branches themselves
  (that remains the parent spec's separately-deferred, larger item).
- `scripts/corvette_form_generator/model_configs.py:161-165` (the Finding-9 stale Grand Sport
  "not activated by the Stingray entrypoint" note cited in the parent remediation spec) — inspected,
  not applicable; this is a Phase-4 docs/notes cleanup item, out of scope for this phase, and is not
  touched here.
- README/AGENTS.md — not applicable; this does not change a documented workflow, CLI flag, or invocation
  pattern. `generate_form.py --model <model>` and `generate_registry.py` remain the entry points.

## 5. Constraints

- Do not remove or touch Stingray's compatibility artifact writing (`production.py:651-690`).
- Do not route Stingray through the same `source_assembly.py` branch as Grand Sport/Z06 in this phase —
  that is the audit's separately deferred, larger "item D" and is explicitly out of scope here.
- Prove parity for all three runtime contracts (and Stingray's compatibility JSON/CSV) before and after
  the extraction; do not claim parity without a comparator run and explicit pass/fail per artifact.
- No unrelated refactor of `production.py` or `inspection.py` beyond the two named extraction points
  (context-choice assembly call, option-asset merge call). Do not touch status resolution, display-behavior
  resolution, section/step resolution, or any other assembly logic in this phase.
- The `only_if_image_present` granularity difference identified in Section 0 must be preserved exactly as
  found (`False` for the Stingray/production path, `True` for the Grand Sport/Z06/inspection path) unless
  the user explicitly approves changing it as a deliberate behavior decision separate from this extraction.
  This phase is parity-preserving, not a behavior-unification pass.
- No new dependencies.
- New shared helpers land in `contract.py`, not a new module, because `contract.py:1` defines it as the
  shared contract-surface helper module and it already owns every helper this phase composes
  (`load_asset_map`, `option_asset_map`, `bodystyle_asset_map`, `build_body_context_choices`,
  `build_trim_context_choices`, `ASSET_IMAGE_FIELDS`, `asset_fields`).

## 6. Risks and non-goals

- **Risk**: the option-asset merge granularity difference (Section 0) may already be a real, currently
  latent drift between the two paths — for example, an option whose `image_url` arrives via the asset_map
  after the option row was first materialized without one could merge differently under
  `production.py`'s per-choice unconditional approach vs. `inspection.py`'s per-option
  conditional-on-source-row-image approach. This phase's explicit parameterization (`only_if_image_present`)
  makes that difference visible and testable for the first time; if the parity run in Section 7 surfaces a real
  contract diff traceable to this difference, stop immediately and report it as a finding requiring a
  product/owner decision rather than silently picking one behavior to "fix" the diff. Do not proceed with a
  "majority" rule or production-precedent behavior in this phase; this spec is scoped as parity-preserving
  extraction, not behavior unification.
- **Non-goal**: this phase does not converge `source_assembly.py`'s Stingray-vs-Grand-Sport/Z06 routing
  branch (parent spec's deferred "item D") — extracting the two specific duplicated merge call sites is a
  smaller, lower-risk slice than collapsing the branch itself, consistent with the
  `route-unification-characterization` extraction pattern (characterize/extract first, defer full route
  unification).
- **Non-goal**: this phase does not change `default_selection_rules` / `display_behavior` resolution logic
  (that is the parent spec's Phase 3, the hardcoded default-selected allowlist).
- **Non-goal**: this phase does not change asset_map identity-key behavior (Phase 1, already complete) or
  add wildcard/shared asset_map rows or media-coverage policy changes (parent spec's Phase 4).

## 7. Validation plan

Run in this order; report every command and its actual result, not an assumed pass:

1. Baseline current-route outputs before any code change, per the `route-unification-characterization`
   pattern:
   - `.venv/bin/python scripts/generate_form.py --model stingray`
   - `.venv/bin/python scripts/generate_form.py --model grand_sport`
   - `.venv/bin/python scripts/generate_form.py --model z06`
   - `.venv/bin/python scripts/generate_registry.py`
   - Copy `form-output/runtime/*.json` and Stingray's `form-output/stingray-form-data.{json,csv}` to a
     `/tmp` baseline directory before editing.
   - `git status --short -- form-output form-app/data.js stingray_master.xlsx` — classify any pre-existing
     diff (timestamp-only vs. substantive) before treating the baseline as clean.
2. Implement the extraction per Section 2.
3. `.venv/bin/python -m pytest tests/test_schema_validation_metadata.py tests/test_asset_map_sync.py -q`
   plus the new `contract.py` helper tests added in Section 2 item 4 — must pass.
4. Regenerate all three model artifacts again (the same `generate_form.py --model ...` commands as step 1),
   but do not run `generate_registry.py` yet.
5. `node scripts/compare-generated-contracts.mjs <before-stingray.json> <after-stingray.json>` (and the
   same for grand_sport, z06) — must report no diff other than ignored timestamp keys. If any real diff
   appears, stop and flag it immediately; do not continue to registry publication, compatibility-artifact
   comparison, majority behavior, or production-precedent behavior inside this parity-preserving phase.
6. Run `node scripts/compare-generated-contracts.mjs <before-stingray-form-data.json>
   <after-stingray-form-data.json>` (or an equivalent JSON comparison that ignores only generated timestamp
   keys such as `dataset.generated_at`) on Stingray's compatibility JSON; it must report no substantive
   diff. Keep `cmp -s` (or `shasum -a 256`) for Stingray's compatibility `stingray-form-data.csv`; the CSV
   must be byte-identical before vs. after.
7. Run `.venv/bin/python scripts/generate_registry.py` only after steps 5-6 prove parity.
8. Run the full companion test suite named in Section 4:
   ```sh
   for t in \
     tests/stingray-generator-stability.test.mjs \
     tests/grand-sport-draft-data.test.mjs \
     tests/grand-sport-contract-preview.test.mjs \
     tests/z06-form-data-draft.test.mjs \
     tests/z06-contract-preview.test.mjs \
     tests/multi-model-runtime-switching.test.mjs
   do
     node --test "$t"
   done
   ```
   — must all pass unmodified.
9. `.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx` — must remain `status:
   valid, 0 errors, 0 warnings` (no workbook change expected, but this is a cheap confirming check after
   any generator run).
10. `git status --short -- form-output form-app/data.js stingray_master.xlsx` after the full validation
   run — review and restore any unrelated/unintentional churn (timestamp-only Markdown, workbook binary
   save churn from generator runs) before final handoff, per the established gate pattern; report which
   diffs were restored and why.
11. Use the project `.venv` on the host for all of the above; if running in a sandboxed/container
    environment without a working host `.venv`, system Python plus pip-installed pytest/openpyxl is an
    acceptable substitute for the Python test run only — flag this explicitly in the handoff and recommend
    re-running on the host `.venv` before merge.

## 8. Handoff requirements for this phase

On completion, report per AGENTS.md Section 15:
- Exact diff in `contract.py` (new shared helpers), `production.py`, and `inspection.py` (call-site
  replacements), and the new/updated test file(s).
- Explicit statement of which `only_if_image_present` value each call site uses and why, confirming no
  silent behavior change.
- Confirmation that the option-asset merge granularity finding from Section 0/6 was investigated during
  parity validation, with the result (no diff found, or a diff found and reported for a decision).
- Validation results from Section 7, including the comparator output for all three models' runtime
  contracts, the Stingray compatibility artifact comparison, and the full companion test suite results.
- Confirmation that zero workbook writes occurred and `form-app/data.js` is unchanged (or, if generator
  runs produced timestamp-only/workbook-binary churn, confirmation that it was restored before handoff).
- Explicit statement that the parent spec's Phase 3 (default-selected allowlist) and Phase 4 (wildcard
  asset_map rows, media-coverage policy, Finding 9 cleanup) remain unstarted and unapproved.

## 9. Implementation evidence and closure

Implemented 2026-06-30 on branch `phase-2-shared-assembly-extraction`.

Changed source/test files:
- `scripts/corvette_form_generator/contract.py` — added `build_model_context_choices(...)` and
  `merge_option_asset_fields(...)`.
- `scripts/corvette_form_generator/production.py` — replaced the duplicated context-choice assembly call
  with `build_model_context_choices(...)`; replaced the inline per-choice option-asset update with
  `merge_option_asset_fields(choice, option_assets, only_if_image_present=False)`.
- `scripts/corvette_form_generator/inspection.py` — replaced the duplicated context-choice assembly call
  with `build_model_context_choices(...)`; preserved the existing `option_rows[option_id]` source-row merge
  timing and replaced only the per-choice copy-out with
  `merge_option_asset_fields(draft_choice, option_rows, only_if_image_present=True)`.
- `tests/test_corvette_form_generator_contract.py` — added focused helper tests for context-choice parity,
  source-row image gating, ASSET_IMAGE_FIELDS-only copying, and missing-source no-op behavior.
- `docs/asset-media-drift/phase-2-shared-assembly-extraction.md` — marked this spec implemented and
  recorded closure evidence.

Preserved surfaces:
- No workbook rows or workbook schema changed.
- No `source_assembly.py` route split collapsed; Stingray remains on the production source assembly path and
  Grand Sport/Z06 remain on the inspection/draft path.
- No Phase 3/4 behavior started: default-selected allowlist cleanup, wildcard/shared asset rows,
  media-coverage policy, and Finding 9 cleanup remain out of scope and unstarted.
- `form-app/data.js`, runtime contracts, and Stingray compatibility artifacts were regenerated for proof
  only; timestamp-only churn was restored before handoff.
- Dealer-submission runtime behavior and payloads were not touched.

Validation results:
- Baseline regenerated before code edits with `.venv/bin/python scripts/generate_form.py --model stingray`,
  `grand_sport`, `z06`, then `.venv/bin/python scripts/generate_registry.py`; baseline artifacts copied to
  `/tmp/27vette-phase2-shared-assembly-baseline-20260630215155`.
- `.venv/bin/python -m pytest tests/test_schema_validation_metadata.py tests/test_asset_map_sync.py
  tests/test_corvette_form_generator_contract.py -q` — `54 passed`.
- After implementation regeneration, `node scripts/compare-generated-contracts.mjs` reported `contracts
  match` for Stingray, Grand Sport, and Z06 runtime contracts against the baseline.
- `node scripts/compare-generated-contracts.mjs` reported `contracts match` for
  `form-output/stingray-form-data.json` against the baseline, using timestamp-normalized JSON comparison.
- `cmp -s` on `form-output/stingray-form-data.csv` against the baseline returned `0`.
- `.venv/bin/python scripts/generate_registry.py` — passed after parity proof.
- Sequential Node companion suite passed with exit `0` for each file:
  `tests/stingray-generator-stability.test.mjs`, `tests/grand-sport-draft-data.test.mjs`,
  `tests/grand-sport-contract-preview.test.mjs`, `tests/z06-form-data-draft.test.mjs`,
  `tests/z06-contract-preview.test.mjs`, and `tests/multi-model-runtime-switching.test.mjs`.
- `.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx` — `status: valid`,
  `error_count: 0`, `warning_count: 0`.
- `.venv/bin/python -m py_compile scripts/corvette_form_generator/contract.py
  scripts/corvette_form_generator/production.py scripts/corvette_form_generator/inspection.py
  tests/test_corvette_form_generator_contract.py` — exit `0`.
- `git diff --check` — passed.

Residual risk/manual verification:
- No manual browser smoke was run because this pass changed generator internals only and parity checks showed
  no substantive runtime or compatibility artifact drift.
