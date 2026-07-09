# Pass D.2 — Rebuilt pass-c-2 dry-run evidence and write-decision checkpoint

Status: Implemented 2026-07-09 after Sean approval. Fresh all-target run `20260709-003524-650cae` was rebuilt as `pass-c-2`, approved for D.2 dry-run evidence only, and validated through the Pass D apply CLI without `--write`. Reasoning level for Sean/Codex: high.

## 0. Decision summary

Pass D.1 made the apply path safer, but it did not approve a live workbook write.

Smallest safe next pass:

1. Preserve the old all-target run `20260707-193441-ea9e4c` as historical `pass-c-1` evidence; do not live-write it and do not mutate its plan or approval files.
2. Create a fresh all-target rebuild run from the reviewed source/selection/decisions artifacts.
3. Build a new `pass-c-2` apply plan from current D.1 code.
4. Record a dry-run-only plan approval only after fingerprints still match and the plan is clean.
5. Run `scripts/ingest_wizard_apply.py` without `--write`.
6. Review `apply-dry-run-report.json` for bool hygiene, workbook immutability, and deployment-continuity diagnostics.
7. Stop for Sean's explicit decision: no write, non-deployment scaffold write, or source/tooling follow-up.

This spec does not approve `--write`.

## 1. Diagnosis and current evidence

Change class: ingest workflow evidence / run-artifact rebuild / docs. No workbook mutation, generated runtime publication, runtime JS, or dealer change is approved.

Risk level: high. This is the last evidence checkpoint before any possible first live workbook apply for the focused ingest rows.

Evidence inspected 2026-07-09:

- Branch/worktree preflight: `ingest-wizard`, tracking `origin/ingest-wizard`.
- `docs/ingest/pass-d/pass-d1-export-continuity-and-deployment-readiness-spec.md`: Pass D.1 is implemented and says the next checkpoint is a rebuilt `pass-c-2` dry-run report review, not a live write.
- `scripts/ingest_wizard_apply.py`: dry-run is default; `--write` is explicit; CLI delegates to `WizardSessionStore.apply_approved_plan()` and never promotes runtime artifacts.
- `scripts/corvette_form_generator/ingest/wizard/session.py`:
  - `build_apply_plan()` can rebuild a plan from run decisions and writes `apply-plan.json`, `apply-plan-dryrun.json`, and `apply-plan.md`.
  - `approve_plan()` records `plan-approval.json` only after decision and workbook fingerprints still match.
  - `apply_approved_plan()` owns dry-run/write report generation and D.1 diagnostics.
- Historical all-target run `form-output/ingest-wizard/20260707-193441-ea9e4c`:
  - `session.state = plan_approved`.
  - selected targets: `grand_sport_x`, `zr1`, `zr1x`.
  - `apply-plan.json.schemaVersion = pass-c-1`.
  - approved and dry-run clean before D.1, but superseded and non-writable.
- Existing rebuilt run `form-output/ingest-wizard/20260708-233454-e53081`:
  - `session.state = plan_approved`.
  - `apply-plan.json.schemaVersion = pass-c-2`.
  - selected targets / plan targets: `grand_sport_x` only.
  - This is useful proof that D.1 can emit `pass-c-2`, but it is not sufficient for the all-target D.2 decision because it excludes `zr1` and `zr1x`.
- `form-output/ingest-wizard/20260708-233454-e53081/apply-plan-dryrun.json` is plan-builder dry-run evidence only; it is not the Pass D apply CLI dry-run report and has no `deploymentContinuity` result.

Root cause / current blocker:

- The old approved all-target run is non-writable because it is `pass-c-1` and predates D.1 bool-hygiene/deployment-continuity diagnostics.
- The current visible `pass-c-2` run is only Grand Sport X scoped, so it cannot answer the ZR1/ZR1X write/readiness question.
- A new all-target `pass-c-2` run must be rebuilt and dry-run through the Pass D apply CLI before any specific `--write` command can be considered.

## 2. Source-of-truth decision

- Workbook source rows remain authoritative only after an explicitly approved safe workbook write. This pass must not mutate `stingray_master.xlsx`.
- Run artifacts are evidence and approval records, not product-rule sources. Rebuilt artifacts must be reproducible from persisted source/selection/decision state.
- Generated runtime contracts and `form-app/data.js` remain outputs. This pass must not publish or hand-edit runtime artifacts.
- Deployment-continuity diagnostics are a gate for the next decision. They do not authorize runtime promotion.
- Standing constraints from `AGENTS.md` apply, especially source boundaries (§3), spec-first expectations (§4), workbook safety (§5), dealer boundary (§6), validation (§10), and handoff (§12).

## 3. Scope

### 3.1 Preflight and run selection

Before rebuilding anything:

1. Check branch/status:

```sh
git status --short --branch
```

2. Check Excel lock risk:

```sh
python - <<'PY'
from pathlib import Path
lock = Path('~$stingray_master.xlsx')
print({'excelLockExists': lock.exists(), 'path': str(lock)})
PY
```

3. Summarize candidate runs mechanically from `form-output/ingest-wizard/*/session.json`, including:
   - run id;
   - session state;
   - selected targets from `model-selection.json`;
   - `apply-plan.json.schemaVersion` if present;
   - `plan.valid` if present;
   - `apply-plan-dryrun.ok` if present;
   - whether `plan-approval.json` exists;
   - whether `apply-dry-run-report.json` exists.

Selection rule:

- Preferred source evidence run: `20260707-193441-ea9e4c`, because it is the last known all-target reviewed run for `grand_sport_x`, `zr1`, and `zr1x`.
- Do not use its old `apply-plan.json`, `plan-approval.json`, `apply-plan-dryrun.json`, or `apply-dry-run-report.json` as current approval evidence.
- Do not use `20260708-233454-e53081` as the all-target D.2 run unless its selection is expanded and rebuilt from reviewed decisions; as inspected, it is Grand Sport X only.

### 3.2 Create a fresh all-target rebuild run without mutating old evidence

D.2 needs a new run id under `form-output/ingest-wizard/<new-run-id>/`.

Required clone/reset behavior:

- Copy from the selected all-target evidence run only these persisted review/source artifacts:
  - `session.json`
  - `sheet-profile.json`
  - `sheet-roles.json`
  - `option-candidates.json`
  - `price-rows.json`
  - `join-report.json`
  - `model-selection.json`
  - `variant-reconciliation.json`
  - `decisions.json`
  - `decisions-log.jsonl` if present
- In the copied `session.json`:
  - replace `runId` with the new run id;
  - set `state` to `decisions_complete` before rebuilding;
  - preserve `sourceFile`, `sourcePath`, and source fingerprint.
- Do not copy stale plan/apply evidence into the new run:
  - `apply-plan.json`
  - `apply-plan-dryrun.json`
  - `apply-plan.md`
  - `plan-approval.json`
  - `apply-dry-run-report.json`
  - `apply-report.json`
  - scratch/apply logs
- After clone/reset, verify:
  - source fingerprint still matches `sourcePath`;
  - `model-selection.json` targets are exactly `grand_sport_x`, `zr1`, `zr1x`;
  - decisions fingerprint is stable before and after the clone;
  - no `plan-approval.json` exists in the new run.

Implementation note:

- This may be done with a one-off Python command captured in the handoff/receipt, or with a tiny helper if repeatability is preferred. If a helper is added, pin it to `scripts/ingest_wizard_clone_run.py` and cover only clone/reset behavior; do not broaden D.2 into a UI/server feature.

### 3.3 Rebuild the apply plan as pass-c-2

Use the existing store method against the new run:

```sh
PYTHONPATH=scripts .venv/bin/python - <<'PY'
from pathlib import Path
from corvette_form_generator.ingest.wizard.session import WizardSessionStore
run_id = '<new-all-target-run-id>'
store = WizardSessionStore(Path('.'), workbook_path=Path('stingray_master.xlsx'))
result = store.build_apply_plan(run_id)
print(result['session']['state'])
print(result['plan'])
print(result['dryRun']['ok'])
PY
```

Required assertions:

- `session.state == "plan_built"`.
- `apply-plan.json.schemaVersion == "pass-c-2"`.
- `apply-plan.json.targets == ["grand_sport_x", "zr1", "zr1x"]`.
- `plan.valid == true`.
- `apply-plan-dryrun.json.ok == true`.
- `blockingGaps == 0`, unless the blocker is intentionally carried as a D.2 stop condition and no approval is recorded.
- Planned Grand Sport X metadata rows use `registry_key == "grand_sport_x"`.
- `perSheetActionCounts` exists and shows action-level counts, not only sheet totals.

### 3.4 Record dry-run-only plan approval

The Pass D apply CLI requires `plan_approved` even for dry-run. D.2 may record a new plan approval only after §3.3 passes.

Required behavior:

- Approval record applies only to the rebuilt all-target `pass-c-2` run and only to dry-run evidence gathering.
- The approval text/name should make this boundary visible, for example `Hermes Agent — D.2 dry-run only` if Sean does not provide a different reviewer label.
- A D.2 plan approval is not approval to run `--write`.
- If any fingerprint changed after plan build, rebuild instead of approving.

Command shape:

```sh
PYTHONPATH=scripts .venv/bin/python - <<'PY'
from pathlib import Path
from corvette_form_generator.ingest.wizard.session import WizardSessionStore
run_id = '<new-all-target-run-id>'
store = WizardSessionStore(Path('.'), workbook_path=Path('stingray_master.xlsx'))
result = store.approve_plan(run_id, 'Hermes Agent — D.2 dry-run only')
print(result['session']['state'])
print(result['approval'])
PY
```

Required assertions:

- `session.state == "plan_approved"`.
- `plan-approval.json.schemaVersion == "pass-c-2"`.
- `plan-approval.json.planSha` equals the current SHA256 of `apply-plan.json`.

### 3.5 Run the Pass D apply CLI dry-run, not write

Command:

```sh
.venv/bin/python scripts/ingest_wizard_apply.py --run <new-all-target-run-id>
```

Forbidden in D.2 unless Sean gives separate live-write approval after this report is reviewed:

```sh
.venv/bin/python scripts/ingest_wizard_apply.py --run <new-all-target-run-id> --write --confirm-plan-warnings
```

Required report:

- `form-output/ingest-wizard/<new-all-target-run-id>/apply-dry-run-report.json`.
- No `apply-report.json`.
- No workbook edit log.
- No backup path.

### 3.6 Report assertions and decision categories

D.2 succeeds as evidence if the report is mechanically reviewed and classified. It does not require deployment-ready output.

Required JSON assertions:

- `schemaVersion == "pass-d-1"`.
- `write == false`.
- `status == "validated"` or another non-write success status used by the current report contract.
- `planSchemaVersion == "pass-c-2"`.
- `planSupersededForWrite == false`.
- `boolHygieneResult.error_count == 0`.
- `workbookBefore == workbookAfter`.
- `backupPath == null`.
- `workbookEditLogPath == null`.
- `verification.mismatches == []`.
- `perSheetActionCounts` exists and includes action-level counts for workbook-owned source surfaces.
- `runtimeContinuity` exists.
- `deploymentContinuity` exists for all selected targets: `grand_sport_x`, `zr1`, `zr1x`.
- Each selected target has `registryLoadable == true`, or the report is classified as blocked before write approval.
- Any zero `priceRules`, zero `ruleGroups`, zero `colorOverrides`, zero component coverage, or media gaps are explicitly present as blockers/deferrals in `deploymentContinuity`; none may be inferred only from `plan.valid=true`.

Decision categories after review:

- `ready_for_live_write_review`: bool hygiene clean, workbook unchanged by dry-run, all selected target metadata registry-loadable, and no blocker remains except explicitly acceptable non-deployment deferrals.
- `non_deployment_scaffold_candidate`: bool hygiene clean and registry-loadable, but deployment-continuity blockers remain for pricing/rules/color/components/media. This can be written only if Sean explicitly approves a non-deployment scaffold write.
- `blocked_fix_source_or_tooling`: bool hygiene fails, fingerprint drift occurs, registry loadability fails, report fields are missing, or plan/review scope is incomplete.

### 3.7 Handoff requirements for D.2 implementation

Follow `AGENTS.md` §12 plus these D.2-specific items:

- New run id and source run id.
- Exact target set.
- Plan schema, plan SHA, and approval label/time.
- Plan op counts and per-sheet action counts summary.
- Dry-run report path.
- Bool-hygiene status and first issue list if nonzero.
- Deployment-continuity status for each selected target.
- Explicit statement that `stingray_master.xlsx`, `form-output/runtime/*`, and `form-app/data.js` were unchanged.
- Recommendation for the next decision: no write, non-deployment scaffold write approval, or follow-up source/tooling pass.

## 4. Exact files/artifacts expected to change

Expected during D.2 implementation:

- New run artifact directory under `form-output/ingest-wizard/<new-all-target-run-id>/`.
- In that new run only:
  - cloned/reset review artifacts;
  - rebuilt `apply-plan.json`;
  - rebuilt `apply-plan-dryrun.json`;
  - rebuilt `apply-plan.md`;
  - new `plan-approval.json` after §3.3 passes;
  - new `apply-dry-run-report.json` after CLI dry-run.

Expected docs/spec files for this spec-writing pass:

- `docs/ingest/pass-d/pass-d2-rebuilt-dry-run-evidence-spec.md`
- `docs/ingest/README.md`
- `docs/ingest/pass-d/pass-d1-export-continuity-and-deployment-readiness-spec.md` for closure wording that points to completed D.2 evidence
- `docs/ingest/ingest-wizard-end-to-end-completion-spec.md` for route-map wording that reflects the completed D.2 checkpoint

Possible implementation helper, only if chosen for repeatability:

- `scripts/ingest_wizard_clone_run.py`
- `tests/test_ingest_wizard_clone_run.py` or focused fixture coverage in `tests/test_ingest_wizard_apply.py`

Not expected / forbidden without separate approval:

- `stingray_master.xlsx`
- `form-output/runtime/*`
- `form-app/data.js`
- runtime JS/CSS/HTML
- dealer submission files
- commits, pushes, or branch changes

## 5. Companion-file impact matrix

| Surface | D.2 status | Required action |
|---|---|---|
| Workbook source | Must remain unchanged | Dry-run only; prove before/after fingerprint identical |
| Historical run `20260707-193441-ea9e4c` | Preserved | Do not mutate old `pass-c-1` plan/approval/report files |
| Existing GSX-only `pass-c-2` run | Evidence only | Do not treat as all-target write evidence |
| New rebuilt run artifacts | Updated/created | New all-target run directory with current `pass-c-2` plan and dry-run report |
| Apply tooling | Updated | Fixed two D.2 blocker findings: pending-registered existing sheets now preserve text bool conventions; failed dry-runs now persist `apply-dry-run-report.json` instead of stdout-only evidence |
| Generated runtime contracts / registry | Not applicable | Must remain untouched |
| Runtime/dealer | Not applicable | No endpoint, payload, Turnstile, or live submission changes |
| Docs/index | Updated | D.2 is indexed as completed evidence with the remaining write decision called out |
| Gate reminders / skills | Inspect after implementation | Patch only if D.2 reveals missing Pass D gate guidance |

## 6. Constraints and non-goals

Spec-specific constraints:

- No live workbook `--write` in D.2.
- No mutation of the old `20260707-193441-ea9e4c` plan/approval/report artifacts.
- No narrowing the all-target checkpoint to Grand Sport X only.
- No using `plan.valid=true` as a substitute for `deploymentContinuity` review.
- No product-rule fixes in Python or runtime JS to make continuity counts look healthy.
- No `approved_bool_type_migrations` allowlist to pass D.2.
- No runtime promotion or registry publication.

Non-goals:

- Final workbook apply.
- Regenerating or publishing runtime contracts.
- Resolving every deployment-continuity blocker found by the report.
- Media/asset-map population.
- UI/server button for apply.
- Dealer submission validation.

## 7. Validation plan

Docs-only spec-writing validation:

```sh
git diff --check
# Confirm D.2 is indexed and old live-write / registry-key wording is not reintroduced.
rg -n "Pass D\.2|rebuilt pass-c-2" docs/ingest
rg -n "<old run id plus --write>|<old controlled-apply readiness phrase>|<old GSX registry-key tuple>" docs/ingest
```

D.2 implementation preflight:

```sh
git status --short --branch
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

D.2 implementation targeted code gates if no helper code changes:

```sh
git diff --check
PYTHONPATH=scripts .venv/bin/python -m py_compile \
  scripts/ingest_wizard_apply.py \
  scripts/corvette_form_generator/editor_ops.py \
  scripts/corvette_form_generator/ingest/wizard/plan_builder.py \
  scripts/corvette_form_generator/ingest/wizard/session.py
.venv/bin/python -m pytest \
  tests/test_editor_ops_apply.py \
  tests/test_editor_ops_global_families.py \
  tests/test_ingest_wizard_apply.py \
  tests/test_ingest_wizard_plan.py -q
```

Add helper-specific tests if `scripts/ingest_wizard_clone_run.py` is created.

D.2 real-run dry-run command:

```sh
.venv/bin/python scripts/ingest_wizard_apply.py --run <new-all-target-run-id>
```

D.2 report verification:

```sh
PYTHONPATH=scripts .venv/bin/python - <<'PY'
import json
from pathlib import Path
run_id = '<new-all-target-run-id>'
report = json.loads((Path('form-output/ingest-wizard') / run_id / 'apply-dry-run-report.json').read_text())
required_models = {'grand_sport_x', 'zr1', 'zr1x'}
assert report['write'] is False
assert report['planSchemaVersion'] == 'pass-c-2'
assert report.get('planSupersededForWrite') is False
assert report.get('boolHygieneResult', {}).get('error_count') == 0
assert report['workbookBefore'] == report['workbookAfter']
assert report.get('backupPath') is None
assert report.get('workbookEditLogPath') is None
assert not report.get('verification', {}).get('mismatches')
assert required_models <= set((report.get('deploymentContinuity') or {}).keys())
for model in sorted(required_models):
    entry = report['deploymentContinuity'][model]
    assert 'registryLoadable' in entry, model
    assert 'blockers' in entry or 'deferrals' in entry or 'status' in entry, model
print('D.2 dry-run report assertions passed for', run_id)
PY
```

Artifact/workbook non-mutation proof:

```sh
git diff --name-only -- stingray_master.xlsx form-output/runtime form-app/data.js form-app scripts | cat
```

Expected output for the non-mutation proof is empty, unless D.2 explicitly added a clone helper under `scripts/` and that helper is reported as a code change.

Gates not required in D.2 unless code/runtime surfaces change:

- Node runtime tests: not required for a dry-run evidence pass that does not change runtime JS or generated runtime artifacts.
- Browser smoke: not required; no UI/runtime behavior changes.
- Dealer tests: not applicable; dealer boundary untouched.
- Live workbook write gates: deferred until a separate explicit `--write` approval.

## 8. Implementation closure — 2026-07-09

Pass D.2 was run to completion as a dry-run evidence pass. It did not write `stingray_master.xlsx`, did not publish runtime artifacts, and did not touch dealer-submission code.

Run evidence:

- Source evidence run: `20260707-193441-ea9e4c`.
- New rebuilt all-target run: `20260709-003524-650cae`.
- Targets: `grand_sport_x`, `zr1`, `zr1x`.
- Plan schema: `pass-c-2`.
- Plan SHA: `0dfdc9cd408a613eaf0b634fe9f0681adc222d494663e9b89b0cbd39ecd2ca99`.
- Approval label/time: `Hermes Agent — D.2 dry-run only`, `2026-07-09T00:37:06`.
- Plan op counts: stage 1 = 52, stage 2 = 5,719, combined = 5,771.
- Dry-run report: `form-output/ingest-wizard/20260709-003524-650cae/apply-dry-run-report.json`.

Blockers found and fixed during the run:

- First CLI dry-run failed with `bool_hygiene_failed` because pending `model_workbook_sources` registrations were reflected after bool-convention detection, so pending-registered existing sheets such as `zr1_options` and `zr1x_options` coerced text-bool workbook columns back to Excel booleans. `editor_ops.py` now detects bool conventions after pending source registrations are reflected.
- The failed dry-run returned the bool-hygiene payload only on stdout. `WizardSessionStore.apply_approved_plan()` now persists `apply-dry-run-report.json` for non-write failures, while preserving the existing no-report behavior for blocked live-write attempts such as unconfirmed warnings.

Final dry-run evidence:

- CLI: `.venv/bin/python scripts/ingest_wizard_apply.py --run 20260709-003524-650cae`.
- Result: `ok=true`, `status=validated`, `write=false`.
- `planSchemaVersion == "pass-c-2"` and `planSupersededForWrite == false`.
- `boolHygieneResult.error_count == 0`.
- `schemaResult.error_count == 0`.
- `workbookBefore == workbookAfter`.
- `backupPath == null` and `workbookEditLogPath == null`.
- No `apply-report.json` and no run-scoped workbook edit log.
- Session state remained `plan_approved`.

Deployment-continuity classification:

- `grand_sport_x`: `deployment_probe_passed`, registry-loadable. Counts include 1,200 choices, 19 direct rules, 7 exclusive groups, 0 price rules, 0 rule groups, 88 color overrides, 117 interiors, 0 interior component line items, and 102 media-covered choices. Source-coverage deferrals remain for price rules/rule groups/components/media follow-up.
- `zr1`: `not_deployment_ready`, registry-loadable. Blockers: zero price rules with `pricingDeferred=true`, zero rule groups. Deferrals: zero color overrides and zero media-covered choices.
- `zr1x`: `not_deployment_ready`, registry-loadable. Blockers: zero price rules with `pricingDeferred=true`, zero rule groups. Deferrals: zero color overrides and zero media-covered choices.

Validation run:

```sh
PYTHONPATH=scripts .venv/bin/python -m py_compile \
  scripts/ingest_wizard_apply.py \
  scripts/corvette_form_generator/editor_ops.py \
  scripts/corvette_form_generator/ingest/wizard/plan_builder.py \
  scripts/corvette_form_generator/ingest/wizard/session.py
.venv/bin/python -m pytest \
  tests/test_editor_ops_global_families.py \
  tests/test_ingest_wizard_apply.py \
  tests/test_ingest_wizard_plan.py \
  tests/test_editor_ops_apply.py -q
node --check visualizer/ingest-wizard/wizard.js
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
git diff --check
```

Results: Python compile passed; targeted pytest passed (`70 passed`); Node syntax check passed; workbook package validation passed; workbook schema validation passed; `git diff --check` passed.

Decision result:

- D.2 evidence is complete.
- The rebuilt run is **not deployment-ready** for the full selected target set because ZR1/ZR1X carry explicit price-rule and rule-group blockers.
- A live workbook write is still not approved by this spec. The next approval, if any, must explicitly choose either no write, a non-deployment scaffold write for run `20260709-003524-650cae`, or a follow-up source/tooling pass to resolve deployment blockers before any write.
