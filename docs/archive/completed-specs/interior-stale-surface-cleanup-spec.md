# Interior stale-surface cleanup spec

Date: 2026-06-18
Status: Implemented after approval.

## Goal

Retire the remaining inactive interior CSV/config edge surfaces now that active interior generation is workbook-owned through `model_interior_scope`, `interior_components`, `lt_interiors`, `LZ_Interiors`, and `PriceRef`.

This pass should remove only proven-dead compatibility surfaces. It must preserve generated runtime contracts for Stingray, Grand Sport, and Z06.

## Diagnosis

Current remaining stale surfaces:

- `scripts/corvette_form_generator/model_config.py:24`
  - `ModelConfig` still carries `interior_reference_path: Path`.
- `scripts/corvette_form_generator/model_configs.py:207`
  - `base_model_config()` still assigns `ROOT / "architectureAudit" / f"{model_key}_interiors_refactor.csv"`.
- `architectureAudit/stingray_interiors_refactor.csv`
  - 243 CSV lines; hierarchy-style columns `level0..level5,interior_id`.
- `architectureAudit/grand_sport_interiors_refactor.csv`
  - 247 CSV lines; same hierarchy-style shape.

Current consumer audit findings:

- Active code references to `interior_reference_path` are limited to the dataclass field and the default assignment above.
- Active generator code no longer reads the two CSV files.
- `scripts/corvette_form_generator/interiors.py:118-185` builds interiors from workbook sheets and current model config:
  - `config.interior_source_sheet`
  - `PriceRef`
  - `config.rule_mapping_sheet`
  - `load_interior_components(wb, config.model_key)`
  - `load_model_interior_scope_map(wb, config.model_key)`
- `scripts/corvette_form_generator/interiors.py:141-145` hard-fails when active `model_interior_scope` rows are absent: `CSV/reference and trim-derived fallbacks are retired.`
- `tests/grand-sport-draft-data.test.mjs:624-647` asserts active Stingray, Grand Sport, and Z06 `model_interior_scope` rows carry workbook-owned grouping metadata.
- `tests/grand-sport-draft-data.test.mjs:671-680` already guards the shared interior builder against old fallback symbols: `read_interior_reference`, `grouping_fields_for_interior`, `fallback_interior_trims`, and `interior_component_metadata`.
- `tests/stingray-form-regression.test.mjs:44-46` and later tests assert active Stingray interiors map to active `model_interior_scope` rows.
- `tests/z06-form-data-draft.test.mjs` and `tests/z06-interior-accessory-cleanup.test.mjs` cover current Z06 interior/component behavior.

Workbook evidence:

- `model_interior_scope` has 572 rows with active rows by model:
  - Stingray: 130
  - Grand Sport: 132
  - Z06: 130
  - ZR1: 90
  - ZR1X: 90
- `interior_components` has 846 rows with active rows by model:
  - Stingray: 197
  - Grand Sport: 198
  - Z06: 197
  - ZR1: 127
  - ZR1X: 127
- `lt_interiors` has 132 source rows.
- `LZ_Interiors` has 130 source rows.

Docs evidence:

- `docs/persisting-audit-findings-2026-06-14.md:300-318` says the original runtime defect and workbook-owned grouping gap are fixed, but stale CSV/config surfaces remain.
- `docs/Report-onlyarchitecturecleanuppass.md:99-148` ranks this as a medium current-risk / high cleanup-value single-pass edge route.
- `docs/cleanup-risk-remaining.md:45-60` flags it as a high pass-risk cleanup unless consumer audit and generated-contract parity prove it safe.
- `docs/actual-tasks-remaining-6-17.md:58-61` still lists this as remaining work.

Risk level: medium for implementation, low-to-medium for live runtime if contract parity holds.

Change type: generator/config cleanup + test guard + file deletion + docs/status update. No workbook source-data change is intended.

## Exact files to change

Implementation files:

1. `scripts/corvette_form_generator/model_config.py`
   - Remove `interior_reference_path: Path` from `ModelConfig`.

2. `scripts/corvette_form_generator/model_configs.py`
   - Remove the `interior_reference_path=...` argument from `base_model_config()`.
   - Do not replace it with another config path.

3. `architectureAudit/stingray_interiors_refactor.csv`
   - Delete after contract-parity proof preflight is set up.

4. `architectureAudit/grand_sport_interiors_refactor.csv`
   - Delete after contract-parity proof preflight is set up.

Tests:

5. `tests/grand-sport-draft-data.test.mjs`
   - Extend the existing stale fallback source guard to reject `interior_reference_path` in active generator/config source.
   - Keep existing guards for `read_interior_reference`, `grouping_fields_for_interior`, `fallback_interior_trims`, and `interior_component_metadata`.
   - If this file is not the cleanest place for the config-source scan, add a small focused Python or Node source-guard test instead. Do not add new dependencies.

Docs:

6. `docs/interior-stale-surface-cleanup-spec.md`
   - Mark implemented after the pass lands and record actual gate results.

7. `docs/actual-tasks-remaining-6-17.md`
   - Move the stale-surface cleanup from `Still to do` to `Completed` after implementation.

8. `docs/persisting-audit-findings-2026-06-14.md`
   - Update section 12 after implementation so it no longer lists the config/CSV remnants as current remaining work.

Optional docs if touched by stale current workflow claims:

9. `docs/Report-onlyarchitecturecleanuppass.md`
10. `docs/cleanup-risk-remaining.md`
11. `docs/interior-pipeline-assessment.md`

Do not edit archived historical docs solely to remove old references:

- `archive-2026-05-29/**`
- `.claude/worktrees/**`

## Constraints

- No workbook edits.
- No generated workbook `form_*` sheet hand edits.
- No runtime JS changes.
- No product data changes: options, rules, prices, interiors, components, colors, assets, and promotion rows must stay unchanged.
- No new dependencies.
- No replacement CSV/reference file or parallel hierarchy source.
- Preserve `model_interior_scope` as the workbook-owned grouping/display source.
- Preserve `interior_components` as the workbook-owned component membership source.
- Preserve `lt_interiors` / `LZ_Interiors` as source interior rows.
- Preserve `PriceRef` as price reference input.
- Preserve dealer submission endpoint, payload shape, and Turnstile behavior.
- Do not broaden this pass into interior pricing, grouping redesign, standard-equipment cleanup, or future-model promotion.
- The current working tree may already contain prior-pass changes. Before implementation, inspect `git status --short --branch` and ensure this pass only edits the files listed above unless the user explicitly expands scope.
- Verify branch base against `origin/main` before implementation to avoid stale-branch workbook/generated churn.

## Non-goals

- Do not change `model_interior_scope` row contents.
- Do not change `interior_components` row contents.
- Do not change `lt_interiors` or `LZ_Interiors` row contents.
- Do not change generated payload shape except timestamp fields from regeneration.
- Do not delete `architectureAudit/` as a directory; delete only the two approved stale interior CSVs.
- Do not remove optional audit/report tooling in this pass.
- Do not normalize `sec_tech_001` / connected-service ownership in this pass.

## Implementation plan

### Step 1 — Preflight and snapshots

Run:

```sh
git branch --show-current
git status --short --branch
git fetch origin main --quiet
git merge-base --is-ancestor origin/main HEAD; echo origin_main_ancestor_of_head=$?
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Capture generated baselines before any edit:

```sh
mkdir -p /tmp/27vette-interior-stale-surface-before
cp form-output/stingray-form-data.json /tmp/27vette-interior-stale-surface-before/stingray-form-data.json
cp form-output/inspection/grand-sport-runtime-contract.json /tmp/27vette-interior-stale-surface-before/grand-sport-runtime-contract.json
cp form-output/inspection/z06-runtime-contract.json /tmp/27vette-interior-stale-surface-before/z06-runtime-contract.json
cp form-app/data.js /tmp/27vette-interior-stale-surface-before/data.js
```

Run a source-reference inventory and save the output in the implementation notes/handoff:

```sh
python3 - <<'PY'
from pathlib import Path
terms = [
    'interior_reference_path',
    'architectureAudit/stingray_interiors_refactor.csv',
    'architectureAudit/grand_sport_interiors_refactor.csv',
    'stingray_interiors_refactor.csv',
    'grand_sport_interiors_refactor.csv',
]
for term in terms:
    print('\nTERM', term)
    for path in Path('.').rglob('*'):
        if path.is_dir() or any(part in {'.git', '.venv', 'node_modules', 'backups', '.claude'} for part in path.parts):
            continue
        if path.parts and path.parts[0].startswith('archive-'):
            continue
        if path.suffix in {'.xlsx', '.png', '.jpg', '.jpeg', '.pdf'}:
            continue
        try:
            text = path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue
        if term in text:
            print(path)
PY
```

Do not proceed if an active script/test consumer outside `model_config.py` / `model_configs.py` still reads the CSV paths.

### Step 2 — Add/extend source guard

Add or extend a focused test that fails if active generator/config code reintroduces:

- `interior_reference_path`
- `read_interior_reference`
- `grouping_fields_for_interior`
- `fallback_interior_trims`
- `interior_component_metadata`
- direct references to `stingray_interiors_refactor.csv` or `grand_sport_interiors_refactor.csv`

Suggested active path scope:

- `scripts/corvette_form_generator/model_config.py`
- `scripts/corvette_form_generator/model_configs.py`
- `scripts/corvette_form_generator/interiors.py`
- `scripts/corvette_form_generator/inspection.py`
- `scripts/corvette_form_generator/production.py`
- `scripts/generate_form.py`

This guard should ignore archived docs and `.claude/worktrees/**`.

Run the test before deletion if practical and confirm it fails for the current `interior_reference_path` references. If the existing test structure makes a clean RED leg impractical, document that and still add the guard before final validation.

### Step 3 — Remove stale config and CSV surfaces

- Remove `interior_reference_path` from `ModelConfig`.
- Remove its `base_model_config()` assignment.
- Delete:
  - `architectureAudit/stingray_interiors_refactor.csv`
  - `architectureAudit/grand_sport_interiors_refactor.csv`

Do not touch workbook or generated artifacts manually.

### Step 4 — Regenerate and compare contracts

Run active model generation and registry publication:

```sh
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
.venv/bin/python scripts/generate_registry.py
```

Compare generated contracts after regeneration:

```sh
node scripts/compare-generated-contracts.mjs \
  /tmp/27vette-interior-stale-surface-before/stingray-form-data.json \
  form-output/stingray-form-data.json
node scripts/compare-generated-contracts.mjs \
  /tmp/27vette-interior-stale-surface-before/grand-sport-runtime-contract.json \
  form-output/inspection/grand-sport-runtime-contract.json
node scripts/compare-generated-contracts.mjs \
  /tmp/27vette-interior-stale-surface-before/z06-runtime-contract.json \
  form-output/inspection/z06-runtime-contract.json
```

Expected result: parity after timestamp normalization. Any non-timestamp payload drift is a stop condition unless it is directly explained and separately approved.

Inspect generated diffs. Restore unrelated timestamp-only generated churn unless the implementation intentionally retains regenerated artifacts for a documented reason.

### Step 5 — Update current docs

Update current docs only, not archives:

- Mark this spec implemented.
- Move the item out of `docs/actual-tasks-remaining-6-17.md` `Still to do`.
- Refresh `docs/persisting-audit-findings-2026-06-14.md` section 12.
- If `docs/Report-onlyarchitecturecleanuppass.md`, `docs/cleanup-risk-remaining.md`, or `docs/interior-pipeline-assessment.md` are still used as current planning references, update only the current-status lines so they do not instruct future agents to audit/delete already-retired surfaces.

## Validation plan

Focused code/static checks:

```sh
.venv/bin/python -m py_compile \
  scripts/corvette_form_generator/model_config.py \
  scripts/corvette_form_generator/model_configs.py \
  scripts/corvette_form_generator/interiors.py \
  scripts/corvette_form_generator/production.py \
  scripts/corvette_form_generator/inspection.py
.venv/bin/python -m pytest tests/test_model_config_metadata.py -q
```

Workbook/schema gates:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Generation/parity gates:

```sh
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
.venv/bin/python scripts/generate_registry.py
node scripts/compare-generated-contracts.mjs /tmp/27vette-interior-stale-surface-before/stingray-form-data.json form-output/stingray-form-data.json
node scripts/compare-generated-contracts.mjs /tmp/27vette-interior-stale-surface-before/grand-sport-runtime-contract.json form-output/inspection/grand-sport-runtime-contract.json
node scripts/compare-generated-contracts.mjs /tmp/27vette-interior-stale-surface-before/z06-runtime-contract.json form-output/inspection/z06-runtime-contract.json
```

Interior-focused runtime/data gates:

```sh
node --test tests/stingray-generator-stability.test.mjs
node --test tests/stingray-form-regression.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/z06-form-data-draft.test.mjs
node --test tests/z06-interior-accessory-cleanup.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Final hygiene:

```sh
git diff --check -- \
  scripts/corvette_form_generator/model_config.py \
  scripts/corvette_form_generator/model_configs.py \
  tests/grand-sport-draft-data.test.mjs \
  docs/interior-stale-surface-cleanup-spec.md \
  docs/actual-tasks-remaining-6-17.md \
  docs/persisting-audit-findings-2026-06-14.md
python3 - <<'PY'
from pathlib import Path
active_paths = [
    Path('scripts/corvette_form_generator/model_config.py'),
    Path('scripts/corvette_form_generator/model_configs.py'),
    Path('scripts/corvette_form_generator/interiors.py'),
    Path('scripts/corvette_form_generator/inspection.py'),
    Path('scripts/corvette_form_generator/production.py'),
    Path('scripts/generate_form.py'),
]
for term in ['interior_reference_path', 'stingray_interiors_refactor.csv', 'grand_sport_interiors_refactor.csv']:
    hits = [str(path) for path in active_paths if term in path.read_text(encoding='utf-8')]
    assert not hits, (term, hits)
assert not Path('architectureAudit/stingray_interiors_refactor.csv').exists()
assert not Path('architectureAudit/grand_sport_interiors_refactor.csv').exists()
PY
```

## Expected diffs

Expected retained diffs:

- Remove one field from `ModelConfig`.
- Remove one argument from `base_model_config()`.
- Delete two stale CSV files.
- Add or extend one focused source guard test.
- Update current docs/status files.

Expected generated diffs:

- Ideally none retained.
- Temporary timestamp-only regeneration churn is acceptable during validation, but should be restored before handoff unless the user explicitly wants regenerated artifacts retained.

## Stop conditions

Stop and report before continuing if:

- Any active script/test consumer still reads the stale CSV files.
- Removing `interior_reference_path` requires a broader constructor/API refactor outside the listed files.
- Generated contract comparison shows non-timestamp payload drift.
- Workbook schema/package validation fails.
- Node tests reveal interior grouping, pricing, component, or model-switching regressions.

## Implementation result

Implemented 2026-06-18.

Changed:

- Removed `interior_reference_path` from `scripts/corvette_form_generator/model_config.py`.
- Removed the default `architectureAudit/*_interiors_refactor.csv` assignment from `scripts/corvette_form_generator/model_configs.py`.
- Deleted:
  - `architectureAudit/stingray_interiors_refactor.csv`
  - `architectureAudit/grand_sport_interiors_refactor.csv`
- Extended `tests/grand-sport-draft-data.test.mjs` so active interior pipeline sources reject `interior_reference_path`, `stingray_interiors_refactor.csv`, and `grand_sport_interiors_refactor.csv`.
- Updated current status docs.

Behavior impact:

- No intended runtime payload, workbook source-data, option/rule/price/interior/component/color/asset, dealer payload, or browser behavior change.
- Active interior generation remains workbook-owned through `model_interior_scope`, `interior_components`, `lt_interiors`, `LZ_Interiors`, and `PriceRef`.

Validation notes:

- RED guard proof: `node --test tests/grand-sport-draft-data.test.mjs` failed while `interior_reference_path` remained in active config, then passed after removal.
- Initial baseline comparison against pre-pass generated artifacts exposed unrelated pre-existing generated artifact drift from current workbook `asset_map` state, including Stingray seatbelt image fields and the QE6 image URL. That drift is not caused by this cleanup and should not be retained as part of the pass.
- Controlled generation proof passed: generated Stingray, Grand Sport, and Z06 contracts matched between the removed-field implementation and a temporary control run with the unused field restored.
- Workbook package validation passed.
- Workbook schema validation passed.
- Python compile and `tests/test_model_config_metadata.py` passed.
- Interior-focused Node tests and `tests/multi-model-runtime-switching.test.mjs` passed.

## Historical approval prompt

Approve this interior stale-surface cleanup pass?

Recommendation: approve. Current evidence shows the active interior pipeline already uses workbook-owned metadata and hard-fails without `model_interior_scope`; the remaining `interior_reference_path` and CSV files are single-pass edge surfaces. The pass is safe only if implemented with the generated-contract parity proof above.
