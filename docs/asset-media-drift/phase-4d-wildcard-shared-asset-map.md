# Spec: Phase 4D — wildcard/shared asset_map rows

Status: Phase A Implemented 2026-07-02 (approval option b). Phase B (workbook migration) awaits separate approval; checkpoint report in Section 11.

Parent: `docs/asset-media-drift-remediation-spec-2026-06-30.md` Section 5 / audit Finding 5 (`docs/asset_media-audit-6-30.md`). Predecessors: 4A, 4B (2026-07-01), 4C (2026-07-02) — all Implemented. This is the last open Phase 4 item.

Recommended reasoning level for implementation: high. Phase B is a workbook data migration whose correctness proof is generated-contract parity; the sync-awareness change in Phase A is the piece most likely to be under-thought (a naive implementation lets the next sync run silently undo the migration).

## 0. Re-validation at time of writing (live workbook probe, 2026-07-02)

All counts re-probed against `stingray_master.xlsx` on `phase-2-shared-assembly-extraction` (clean tree, 31b4db9); do not trust the 6-30 audit figures without this refresh — they matched, but were re-verified:

- `asset_map`: 194 rows, 192 active (183 option / 3 model / 6 context_choice), 2 inactive. Active by model_key: stingray 54, grand_sport 64, z06 74. Active wildcard/shared rows: 0.
- Identical option payload groups (target_id + all 7 `ASSET_IMAGE_FIELDS` values equal) repeated across >=2 models: 38. Repeated across ALL 3 promoted models: 28. Max rows removable if every multi-model group collapsed: 66; the conservative all-3-only lane removes 56 (28 groups x 3 rows -> 28 wildcard rows).
- 16 option target_ids have DIVERGENT payloads across models (brake calipers opt_j6*, opt_c2z_001, opt_cc3_001, opt_cf7_001, opt_nga_001, opt_rou_001, opt_rox_001, opt_sl9_001, opt_som_001, ...). These must remain exact per-model rows (or exact overlays over a wildcard if a subset is identical).
- `contract.py:35` (`load_asset_map`) requires exact `model_key` equality — no wildcard support anywhere in the load path. `context_choice_copy` already has the `model_key in {"*", model_key}` precedent at `contract.py:93-94`.
- `schema_validation.py:489` `validate_asset_map_uniqueness` keys active rows by `(model_key, target_type, target_id)` — a `"*"` model_key is just another key value, so duplicate wildcard rows already fail loudly with no change.
- `asset_map_sync.py:515` `existing_asset_rows` keys existing rows by `(model_key, target_type, target_id_key)` per model; `reconcile` (`:537`) plans `insert_filled` for any desired target with no existing row. With zero wildcard awareness, a post-migration sync run would classify every wildcard-covered target as missing a row and plan per-model re-inserts — undoing the migration.
- `build_coverage_classifier` (`asset_map_sync.py:482`) uses `existing_rows` for the existing-asset-row and sibling-model rules; same wildcard-awareness requirement.
- Consumers of the load path: `production.py:205-206` (`option_asset_map`, `bodystyle_asset_map`), `inspection.py:669,979` (`bodystyle_asset_map`, `load_asset_map`) — all funnel through `load_asset_map`, so wildcard support lands in exactly one function. `load_model_asset_map` (`contract.py:66`, used by `generate_registry.py:30` and `schema_validation.py:253`) is a separate loader for model-card rows and is NOT in scope.

## 1. Diagnosis

Audit Finding 5: 38 active option asset payload groups are byte-identical across models because `asset_map` can only express per-model rows. Every new active model multiplies maintenance for universally shared media (seat belts, paints, stripes). Current output is correct — this is a workbook-maintenance/growth burden, not a live bug.

Risk: low-to-medium overall. Phase A (mechanism) is low risk — additive load semantics with parity trivially preserved because zero wildcard rows exist. Phase B (migration) is medium — a workbook write plus regeneration whose only acceptable outcome is timestamp-only generated drift. Change class: generator/contract mechanism + workbook data migration + sync tooling awareness, phased.

## 2. Recommended pass shape: two ordered phases, one checkpoint

### Phase A — wildcard mechanism (code + tests, no workbook write)

1. `contract.py:load_asset_map` (lines 25-43): load in two passes over active rows — wildcard rows (`model_key == "*"`) first, exact `model_key` rows second, exact overwriting wildcard per `(target_type, target_id)` key. Follow the existing `context_choice_copy` precedent (`clean(row.get("model_key")) or "*"`? — no: asset_map blank model_key today means a skipped/invalid row; wildcard must be the explicit literal `"*"` only. Blank stays invalid). `option_asset_map` / `bodystyle_asset_map` inherit automatically; `inspection.py` inherits automatically. `load_model_asset_map` unchanged — model-card rows are inherently per-model.
2. Guard rail in `schema_validation.py`: new check (same file, same `add_issue` dict-walk shape as `validate_asset_map_uniqueness` at `:489`, registered alongside it) rejecting active `model_key="*"` rows with `target_type` of `model` or `context_choice` — the loader would either ignore them (`load_model_asset_map` filters on target_type=model with exact model_key semantics) or apply model-specific hover media to every model. Wildcard scope in this pass is `target_type=option` only. Issue id suggestion: `invalid_wildcard_asset_map_row`. Exact-duplicate wildcard rows are already covered by the existing uniqueness check (key includes model_key) — assert that in a test, don't re-implement.
3. `asset_map_sync.py` wildcard awareness (the anti-undo requirement):
   - `existing_asset_rows` (`:515`): additionally collect wildcard option rows; expose them so `reconcile` can resolve "does target (model, option, id) have a row" as exact-row OR wildcard-row. Suggested shape: return `(rows, wildcard_rows)` or fold wildcard entries into the per-model lookup at read time for each promoted model — implementer picks the smaller diff, but the observable contract is pinned by tests below.
   - `reconcile` (`:537`): a wildcard-covered target with matching hosted media is `keep`, not `insert_filled`; a wildcard-covered target whose canonical media URL differs from the wildcard row's URL must NOT plan a wildcard edit — report it as a distinct review action (suggested action token: `wildcard_conflict`) so divergence is a human decision. Sync apply never writes, edits, or inserts `model_key="*"` rows; wildcard authoring stays a manual/migration decision.
   - `build_coverage_classifier` (`:482`): existing-asset-row and sibling-model rules treat wildcard coverage as coverage; manifest `coverage.section_coverage` counts wildcard-covered targets as covered.
4. Tests:
   - Python: `tests/test_asset_map_sync.py` — wildcard-covered target -> keep/no-insert; wildcard URL conflict -> `wildcard_conflict` review action, no write plan; coverage classifier counts wildcard as covered; determinism preserved. `tests/test_schema_validation_metadata.py` — new guard: wildcard model/context_choice row -> error; wildcard option row -> clean; duplicate wildcard option rows -> existing `duplicate_active_asset_map_row`.
   - Node: `tests/multi-model-runtime-switching.test.mjs` already asserts asset application from asset_map (`:459,:496`); extend with a wildcard-vs-exact-overlay assertion at whichever layer those tests fabricate workbook-shaped data — if they only read generated artifacts, the Python side owns the loader semantics and add the loader test as a new case in the Python suite that exercises `load_asset_map` directly (small in-memory workbook fixture, pattern per `test_schema_validation_metadata.py` fixtures) covering: wildcard-only, exact-only, exact-overlays-wildcard, blank model_key still skipped.

Checkpoint (stop, report before Phase B): mechanism tests green; full regeneration of all three models + registry produces timestamp-only diffs (zero wildcard rows exist, so any other drift is a defect); report the exact migration manifest for Phase B — the list of groups to collapse with per-row evidence.

### Phase B — workbook migration (data pass, AGENTS.md §5)

1. Scope lane (conservative default): collapse ONLY the 28 groups identical across all three promoted models — delete 84 exact option rows, insert 28 `model_key="*"` rows with identical payloads. Expected active count: 192 -> 136. The 10 two-model groups and 16 divergent target_ids are explicitly deferred: two-model groups are only safe as wildcard+overlay or wildcard-where-third-model-lacks-the-option, and each needs a per-group parity proof — queue them as an optional 4D follow-up only if the maintenance win justifies it.
2. Writer: one-pass temp script through `save_workbook_safely()` (4C precedent), printing a manifest of every deleted row (row number, model_key, target_id, payload hash) and every inserted wildcard row before saving. Excel-lock check first.
3. Regenerate all three models + registry. Parity gate: timestamp-normalized contract comparison (`scripts/compare-generated-contracts.mjs` per skill/gate guidance — NOT byte/shasum on JSON) must show zero differences vs pre-migration baselines for all three runtime contracts, `form-app/data.js`, and `form-output/stingray-form-data.json`; CSV byte-identical. Any non-timestamp diff is a hard stop.
4. Post-migration sync probe (deterministic fixture): `scripts/sync_asset_map.py --report-dir <tmp> --media-url-list tests/fixtures/asset-map-sync-media-urls.txt --no-verify-existing` must plan ZERO inserts/writes for wildcard-covered targets, keep counts consistent with pre-migration coverage, `apply=false`/`state_written=false`, and manifest coverage percentages unchanged (baseline 2026-07-01: stingray 35.4%, grand_sport 40.1%, z06 45.8% — wildcard collapse must not move these, since coverage is target-level, not row-level).

## 3. Exact files expected to change

Phase A:
1. `scripts/corvette_form_generator/contract.py` — `load_asset_map` wildcard-first/exact-overlay.
2. `scripts/corvette_form_generator/schema_validation.py` — wildcard target-type guard.
3. `scripts/corvette_form_generator/asset_map_sync.py` — `existing_asset_rows`, `reconcile`, `build_coverage_classifier` wildcard awareness; new `wildcard_conflict` review action.
4. `tests/test_asset_map_sync.py`, `tests/test_schema_validation_metadata.py` — per §2 Phase A item 4 (plus the direct `load_asset_map` loader cases, in a new or existing Python test module — pin at implementation to wherever contract.py loader tests already live; if none exist, add `tests/test_contract_asset_loading.py`).
5. `asset_map-Sync/asset_map_sync.README.md` — document wildcard semantics, `wildcard_conflict`, and the never-writes-wildcard apply boundary.

Phase B:
6. `stingray_master.xlsx` — asset_map migration per §2 Phase B (§5 safety, backup, on-disk verification).
7. `form-output/runtime/*-runtime-contract.json`, `form-output/stingray-form-data.{json,csv}`, `form-app/data.js` — regenerated; timestamp-only drift proven.
8. `docs/asset_media-audit-6-30.md` — Finding 5 status update.
9. `docs/asset-media-drift-remediation-spec-2026-06-30.md` — 4D status flip in the route map.
10. This spec — close per AGENTS.md §11.

Explicitly NOT changing: `form-app/app.js` / CSS / HTML (runtime reads generated per-choice fields; wildcard resolution happens at generation), dealer submission surfaces, `load_model_asset_map` / registry model-card assets, `contract.py` non-asset helpers, section/coverage policy from 4A/4B, `production.py` Stingray legacy path (separately queued).

## 4. Source-of-truth decision

Shared-media membership is workbook-authored data: a `model_key="*"` row is the workbook stating "this option's media is model-independent," with exact rows as the override lane. Generator gains generic overlay mechanics only; no model/RPO knowledge moves into Python or JS. Sync remains maintenance tooling that respects — and never authors — wildcard rows.

## 5. Companion-file impact check

- Generated contracts / `form-app/data.js`: regenerated in Phase B; parity-gated (must be timestamp-only).
- `workbook-schema-standardization.test.mjs`: inspect — `asset_map.active` column pin at `:79` should be unaffected (column set unchanged); no header changes in this pass.
- `stingray-generator-stability.test.mjs` / model regression suites: run; inspect for any pinned asset counts or image expectations (probe found none pinned to row counts, but verify at implementation).
- `grand-sport-draft-data.test.mjs:796` (draft applies option assets): run — inherits wildcard through `load_asset_map`; must stay green with unchanged expectations.
- Workbook editor server: inspected-no-change expected (reads asset_map generically); confirm it renders a `"*"` row without error.
- `validate_workbook_package.py`: run post-save (Phase B) — required standalone gate per skill guidance, plus again in the final gate block.
- Dealer submission: untouched/preserved (AGENTS §6).
- 4A/4B fixture workbooks (`make_discovery_workbook` etc. in `tests/test_asset_map_sync.py`): must keep passing without edits unless a test explicitly opts into wildcard rows.

## 6. Constraints

Standing constraints from AGENTS.md apply (§3, §4, §5 for Phase B, §6). Spec-specific:

- Wildcard literal is exactly `"*"`; blank `model_key` remains invalid/skipped — no silent broadening.
- Wildcard scope is `target_type=option` only in this pass; model and context_choice wildcards are rejected by validation, not silently ignored.
- Sync apply must never create/modify wildcard rows; migration is the only wildcard writer, and it is a one-shot §5-gated script, not a repeatable sync mode.
- Phase B parity is the gate: zero non-timestamp generated drift, or stop and report — no "majority behavior" decisions inside the pass.
- No new dependencies; comparator is the existing `compare-generated-contracts.mjs`.

## 7. Risks and non-goals

Risks:

- Sync re-insert regression (the migration-undo failure mode) — mitigated by the Phase A anti-undo tests and the Phase B post-migration fixture probe with a zero-insert assertion.
- Case-normalization mismatch: `existing_asset_rows` lowercases option target_ids, `load_asset_map` does not; the wildcard lookup added to sync must reuse sync's existing normalization, and the loader tests must include a mixed-case target_id case to prove generator behavior is unchanged.
- A "repeated group" may be identical only because a model is missing its overriding row (latent divergence). Mitigated by the all-3-only lane: all three models already author the identical payload, so the wildcard collapse cannot change any model's output — and parity proves it.
- Editor or downstream tooling choking on `"*"` — covered in §5 companion checks.

Non-goals: two-model-group migration and wildcard+overlay authoring for divergent targets (optional follow-up, per-group proofs required); wildcard for model/context_choice targets; runtime JS changes; coverage-policy changes (4B is final); production.py `active_for_stingray` legacy path; the two documented pre-existing red gates (editor-lints RWJ/WKS, Z06 CBF replace-excludes) — separate triage.

## 8. Validation plan

Phase A (run in order, report exact output):

1. `.venv/bin/python -m pytest tests/test_asset_map_sync.py tests/test_schema_validation_metadata.py -q` plus the loader test module.
2. Deterministic sync fixture probe (command in §2 Phase B item 4, pre-migration): behavior unchanged vs current baseline; run twice into separate dirs, `diff` report CSVs for determinism (timestamp/run fields excepted).
3. `.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx` — clean (guard fires only on synthetic fixtures).
4. Regenerate all three models + registry; `compare-generated-contracts.mjs` timestamp-normalized: zero diffs; restore timestamp-only churn.
5. `git diff --check`; `git diff -- stingray_master.xlsx form-output form-app/data.js` empty at Phase A close.

Checkpoint report, then Phase B:

6. §5 evidence: lock check, `save_workbook_safely()` backup path, on-disk read-back of migrated rows (28 wildcard present, 84 exact absent, all other rows untouched), migration manifest.
7. `.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx` and `validate_workbook_schema.py` — valid/0 issues.
8. Regenerate all three models + registry; timestamp-normalized parity vs pre-migration baselines (contracts, data.js, JSON); CSV byte-identical.
9. Post-migration sync fixture probe: zero wildcard re-insert plans, keep/coverage counts stable, `apply=false`.
10. Node suite per README test-to-surface table: Stingray pair, GS pair, Z06 five, `multi-model-runtime-switching`, `workbook-schema-standardization`, `workbook-visual-copy-standardization`. The two documented pre-existing reds are expected and must be byte-identical to their pre-pass reproductions.
11. Python full: `.venv/bin/python -m pytest -q` (editor-lints pre-existing red expected, unchanged).
12. Browser smoke: not required if parity gates 8-9 are clean (runtime payloads unchanged by proof); state it was skipped on that basis per AGENTS §9. If any parity gate needed interpretation, run per-model card-media spot checks instead.

Gates intentionally not required: live WordPress fetch (deterministic fixture only), live dealer submission (§6), ingest suites.

## 9. Handoff requirements

Follow AGENTS.md §11. Spec-specific additions:

- Phase A/B split evidence: checkpoint report content, migration manifest, group counts (expected: 28 collapsed, 84 deleted, 28 inserted, active 192->136).
- Parity proof summary (timestamp-normalized comparator output per artifact).
- Post-migration sync probe output proving the anti-undo contract.
- Disposition of the deferred lanes: two-model groups, divergent target_ids, wildcard for other target types.

## 10. Approval question

Approve Phase 4D as spec'd?

a. Approve both phases, checkpoint report between them (recommended).
b. Approve Phase A (mechanism + tests) only; Phase B migration approved separately after the checkpoint. [APPROVED 2026-07-02]
c. Changes to scope first.

## 11. Phase A closure + checkpoint report (Implemented 2026-07-02)

### Changed files

- `scripts/corvette_form_generator/contract.py` — `load_asset_map` supports `model_key="*"` wildcard rows (option targets only): wildcard entries load via `setdefault`, exact rows overwrite, order-independent. `WILDCARD_MODEL_KEY` / `WILDCARD_TARGET_TYPES` constants exported. Blank model_key remains skipped.
- `scripts/corvette_form_generator/schema_validation.py` — new `validate_asset_map_wildcard_rows` (registered beside `validate_asset_map_uniqueness`): active `model_key="*"` rows with target_type model/context_choice error as `invalid_wildcard_asset_map_row`.
- `scripts/corvette_form_generator/asset_map_sync.py` — `reconcile` builds a wildcard lookup from `existing_asset_rows` output (which naturally carries `("*", type, id)` keys — no reader change needed): wildcard-covered option targets report `keep` (media-matching or no candidate) or `wildcard_conflict` (canonical media differs), never `insert_filled`, never url_writes; stale-target loop reports a wildcard row stale only when NO promoted model desires the target; `build_section_coverage_stats` counts wildcard rows as covered.
- `tests/test_corvette_form_generator_contract.py` — 6 new loader tests (wildcard-only, exact-overlay both row orders, blank model_key skipped, non-option wildcard ignored, inactive ignored, mixed-case exact unchanged).
- `tests/test_schema_validation_metadata.py` — 4 new guard tests (reject non-option wildcards, allow option wildcard + exact coexistence, duplicate wildcards hit existing uniqueness check, inactive non-option wildcard ignored).
- `tests/test_asset_map_sync.py` — 7 new sync tests (wildcard in existing rows, anti-undo keep-not-insert, keep-without-candidate, wildcard_conflict no-write, exact precedence, wildcard stale semantics, coverage counts wildcard).
- `asset_map-Sync/asset_map_sync.README.md` — wildcard semantics, anti-undo contract, `wildcard_conflict`, never-writes-wildcard boundary.
- This spec.

NOT changed: `stingray_master.xlsx`, `form-output/*`, `form-app/data.js`, `form-app/app.js`/CSS/HTML, dealer submission, `load_model_asset_map`, `production.py`/`inspection.py` (inherit via `load_asset_map`).

### Gates run (all green)

1. `.venv/bin/python -m pytest tests/test_asset_map_sync.py tests/test_schema_validation_metadata.py tests/test_corvette_form_generator_contract.py -q` — 78 passed.
2. Deterministic fixture probe twice into separate dirs — report CSVs byte-identical between runs (REPORTS-DETERMINISTIC); dry-run, 0 inserts, 0 state writes.
3. Baseline parity probe (pre-change code via git stash): report + missing-images CSVs byte-identical to baseline; manifest identical after excluding timestamp/path fields (MANIFEST-PARITY). Zero behavior change with zero wildcard rows, as required.
4. `.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx` — valid, 0 issues (new guard clean on live workbook).
5. Regenerated all 3 models + registry: `compare-generated-contracts.mjs` contracts match for stingray/grand-sport/z06 runtime contracts and stingray-form-data.json; data.js timestamp-normalized parity; CSV byte-identical. Timestamp-only churn restored via `git checkout -- form-output form-app/data.js`.
6. Companion runtime suites: `test_runtime_contract_builder` + `test_registry_promotion_metadata` (11 passed); `node --test multi-model-runtime-switching` + `grand-sport-draft-data` (65/65 pass).
7. `git diff --check` clean; `stingray_master.xlsx` / `form-output` / `form-app/data.js` diffs empty.

Gates not run: full node suite (no generated data or runtime JS changed; parity proven at gate 5), browser smoke (payloads unchanged by proof), live WordPress (out of scope per spec).

### Phase B checkpoint: migration manifest (live workbook probe 2026-07-02)

28 option payload groups identical across all three promoted models; 84 exact rows to delete, 28 wildcard rows to insert; active rows 192 -> 136. Groups (target_id, current sheet rows):

opt_379_001[3,37,65] opt_3a9_001[4,38,66] opt_3f9_001[5,39,67] opt_3m9_001[6,40,68] opt_3n9_001[7,41,69] opt_719_001[8,44,72] opt_ae4_002[130,153,185] opt_ah2_001[134,152,186] opt_aq9_001[133,151,187] opt_e60_001[126,147,178] opt_eri_001[125,146,179] opt_fa5_001[119,138,163] opt_g26_001[9,45,73] opt_g4z_001[10,46,74] opt_g8g_001[11,47,75] opt_gba_001[12,48,76] opt_gbk_001[13,49,77] opt_gec_001[14,50,78] opt_gka_001[15,51,79] opt_gkz_001[16,53,80] opt_gph_001[17,54,81] opt_gtr_001[18,55,82] opt_nwi_001[118,136,159] opt_r88_001[121,139,166] opt_sxb_001[122,141,172] opt_sxr_001[123,142,173] opt_sxt_001[124,143,174] opt_zyc_001[131,137,161]

(Row numbers are pre-migration sheet positions for evidence; the Phase B writer must re-resolve rows at apply time, not trust these.)

### Residual risks / follow-up

- Phase B (workbook migration per §2) awaits approval; gates §8 items 6-12.
- Deferred lanes unchanged: 10 two-model groups, 16 divergent target_ids, wildcard for model/context_choice.
- Fixture probe note: broad flag_missing is 458 on the current workbook/fixture (spec-era audit said 268 against a different, URL-derived media list) — baseline-identical, not a regression.
- Working tree left uncommitted for review.
