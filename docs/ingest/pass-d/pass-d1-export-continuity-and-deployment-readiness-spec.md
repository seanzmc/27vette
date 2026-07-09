# Pass D.1 — Export continuity and deployment-readiness blocker closure

Status: Implemented 2026-07-08 after Sean approval. Tooling/tests/docs landed for bool-storage parity, `pass-c-2` plan schema, Grand Sport X registry-key correction, action-aware continuity reporting, and dry-run deployment-continuity diagnostics. Live workbook write remains unapproved until a rebuilt `pass-c-2` run is dry-run validated and separately approved. Reasoning level for Sean/Codex: high.

## 0. Decision summary

The current approved Pass C/D run must not be live-written as-is.

Run `20260707-193441-ea9e4c` remains useful evidence, but the review found that its clean dry-run did not exercise the same bool-storage guard as the real `write=True` path and that its exported workbook shape is still a skeleton for runtime continuity. This pass supersedes the prior “ready for write after approval” conclusion.

Smallest safe path:

1. Make the dry-run and write paths enforce the same bool-storage convention before any live write can be approved.
2. Fix Grand Sport X registry-key emission to match the current runtime metadata contract.
3. Add a deployment-continuity gate that proves the rebuilt plan is not only apply-valid, but produces runtime-loadable, non-skeleton draft contracts for the selected models.
4. Carry unresolved pricing/rule/media/color/component surfaces as explicit blocking or deferred deployment findings instead of letting `plan.valid=true` imply deployment readiness.
5. Rebuild the real run plan and require a new plan approval before any `--write`.

Implementation closure 2026-07-08:

- `editor_ops.apply_batch()` now mirrors the write path's bool-hygiene guard during dry-run and preserves existing/template bool storage conventions when coercing bool-typed plan values.
- `plan_builder.py` now emits `schemaVersion: "pass-c-2"`, `registry_key: "grand_sport_x"` for Grand Sport X metadata rows, per-sheet action counts, and action-aware runtime-continuity source-op diagnostics.
- `WizardSessionStore.apply_approved_plan(..., write=True)` refuses superseded non-`pass-c-2` plans; dry-run reports include `planSupersededForWrite`, bool-hygiene output, action counts, and `deploymentContinuity` diagnostics.
- The deployment-continuity probe is temp-only: it copies the workbook, applies the plan with the same apply path and bool conventions, temp-activates only the selected target models for generation discovery, runs generation assembly against the temp workbook, and reports loadability/counts/blockers/deferrals without writing `form-output/runtime/*` or `form-app/data.js`.
- Fixture coverage landed for bool text convention preservation, new-sheet convention inheritance, old-plan write refusal, Grand Sport X registry-key emission, action-aware counts, and deployment blocker labeling.

## 1. Diagnosis and current evidence

Change class: ingest wizard plan/apply tooling, fixture tests, docs/status. No workbook write is approved by this spec.

Risk level: high. This work gates the first live workbook apply for Grand Sport X / ZR1 / ZR1X source rows and the later path to runtime promotion.

Evidence inspected:

- Repo state before writing this spec: branch `ingest-wizard`, tracking `origin/ingest-wizard`, date `2026-07-08`.
- `scripts/corvette_form_generator/editor_ops.py:844-853`: dry-run applies ops to a temp workbook, saves it directly, validates package/schema, then returns `status=validated`.
- `scripts/corvette_form_generator/editor_ops.py:869-874`: real write applies the same ops to the live workbook object and then calls `save_workbook_safely()`.
- `scripts/corvette_form_generator/workbook.py:134-144`: `save_workbook_safely()` calls `compare_bool_like_workbooks()` and raises on bool-like storage migrations.
- `scripts/corvette_form_generator/workbook_bool_hygiene.py:211-266`: the guard detects both existing-row bool family flips and added rows whose bool-like storage family disagrees with an unambiguous existing `sheet.column` convention.
- Temp-copy probe against the approved plan (`stage1.items + stage2.items`, 5,771 prepared ops):
  - `_prepare_batch()` errors: 0; warnings: 41.
  - bool-hygiene errors after applying to a temp workbook: 565.
  - Largest convention mismatches: `zr1x_options.active` 172, `zr1_options.active` 171, `zr1x_options.selectable` 67, `zr1_options.selectable` 65, `runtime_steps.active` 42, `section_presentation.active` 36, `context_section_master.is_required` 6, `context_section_master.active` 6.
  - First error reproduced Codex’s finding: `context_section_master.is_required ... uses excel_boolean; existing ... convention is text`.
- `scripts/corvette_form_generator/editor_ops.py:365-396`: `coerce_value(... kind == "bool")` currently converts bool-like plan values to Excel booleans without consulting sheet/column storage convention.
- `scripts/corvette_form_generator/ingest/wizard/plan_builder.py:34-40`: `MODEL_PLAN_CONFIG["grand_sport_x"]["registryKey"]` is currently `grandSportX`.
- `scripts/corvette_form_generator/runtime_metadata.py:643-699`: runtime metadata validation expects `_registry_model_key("grand_sport_x")`, currently `grand_sport_x`, and rejects mismatched active model metadata.
- `form-output/ingest-wizard/20260707-193441-ea9e4c/apply-plan.json`: Grand Sport X model and promotion rows emit `registry_key: "grandSportX"`.
- `form-output/ingest-wizard/20260707-193441-ea9e4c/apply-dry-run-report.json`: dry-run reports `ok=true`, `status=validated`, `stage1=52`, `stage2=5719`, `combined=5771`, but the report does not include bool-hygiene output.
- Action breakdown probe over the approved plan:
  - `grandSportX_price_rules`: `create_sheet` only; no price-rule add rows.
  - `zr1_price_rules`: 0 ops.
  - `zr1x_price_rules`: 0 ops.
  - `zr1_rule_groups` / `zr1x_rule_groups`: delete-only cleanup of old scaffold rows; no add rows.
  - `asset_map`: 0 ops.
  - `color_overrides`: 0 ops.
  - `interior_components`: 0 ops.
  - `model_interior_scope`: 117 ops.
- `scripts/corvette_form_generator/inspection.py:1160-1168`: generated draft data emits warning `pricing_deferred` when a model has no valid price rules.
- `scripts/corvette_form_generator/inspection.py:1198-1204`: runtime-shaped draft data includes `ruleGroups`, `exclusiveGroups`, `rules`, `priceRules`, `interiors`, `colorOverrides`, and `defaultSelectionRules`.
- `scripts/corvette_form_generator/contract.py:29-60` and `contract.py:240-254`: runtime media fields come from `asset_map` / option asset merging.
- `scripts/corvette_form_generator/interiors.py:118-185`: runtime interiors require active `model_interior_scope` rows and consume `interior_components` through `load_interior_components()`.

Root causes:

1. Bool-storage convention is enforced only by `save_workbook_safely()`, while the current dry-run apply path saves a temp workbook directly and never compares bool storage. The apply contract also does not encode per-sheet/per-column storage family, so boolean plan values are coerced to Excel booleans even where the workbook convention is text.
2. Grand Sport X export hardcodes a new camelCase registry key instead of following the existing runtime metadata key policy for a new model key.
3. The current plan builder can create/register many canonical sheets, but it does not yet guarantee meaningful add coverage for price rules or rule groups, and it reports per-sheet totals that can hide `create_sheet` or `delete`-only coverage.
4. Runtime-consumed surfaces (`asset_map`, `color_overrides`, `interior_components`) remain outside the applied row shape or only appear as deferrals, so a clean apply would still not prove deployment continuity.

## 2. Source-of-truth decision

- The workbook remains the source of truth for model metadata, option/OVS rows, relationships, groups, defaults, prices, interiors, colors, components, assets, runtime metadata, and promotion metadata.
- The ingest plan is an approval/apply artifact. It must not become a hidden product-rule source or an excuse to bypass workbook schema conventions.
- Generated artifacts and `form-app/data.js` remain outputs. This pass may generate temp/scratch artifacts for verification, but it must not hand-edit generated runtime files.
- Runtime JavaScript must not gain model/RPO-specific exceptions for these findings.
- Grand Sport X must use the current registry metadata contract for new model keys: `model_key = "grand_sport_x"`, `registry_key = "grand_sport_x"`. Do not add a runtime alias unless a separate compatibility spec approves it.
- Standing constraints from `AGENTS.md` apply, especially source boundaries (§3), spec-first expectations (§4), workbook safety (§5), dealer boundary (§6), validation (§10), and handoff (§12).

## 3. Scope

### 3.1 Fail closed on the old apply shape

Pinned decisions:

- Bump the plan schema emitted by `plan_builder.py` from `pass-c-1` to `pass-c-2` after the fixes below land.
- `scripts/ingest_wizard_apply.py --write` must refuse `pass-c-1` plans. Dry-run may still inspect old runs, but the output must say they are superseded and not live-writable.
- The run `20260707-193441-ea9e4c` must be rebuilt after implementation; do not mutate its old `apply-plan.json` in place and do not use its old `plan-approval.json` for live write.
- A rebuilt plan requires fresh approval before `--write`.

### 3.2 Make bool storage part of the apply contract

Implement one generic bool-storage convention layer in `scripts/corvette_form_generator/editor_ops.py`.

Required behavior:

- During `_prepare_batch()`, determine the intended storage family for every bool-typed column from the target workbook extract:
  - existing target sheet + existing unambiguous bool-like `sheet.column` convention wins;
  - newly created sheet inherits bool-like conventions from its `headersFrom` template sheet;
  - if no convention exists, keep the existing typed behavior.
- Coerce bool-typed plan values to the target storage family before writing cells:
  - `excel_boolean` convention: write real `True` / `False`;
  - `text` convention: write text bools, preserving the dominant workbook casing where practical (`True`/`False` vs `TRUE`/`FALSE`), with storage family correctness as the hard requirement.
- Do not pass a blanket `approved_bool_type_migrations` allowlist for this ingest apply. The goal is preservation, not migration.
- Add the bool-hygiene comparison to the dry-run temp-save path in `apply_batch()`. If the temp workbook would fail `save_workbook_safely()` on bool storage, return a failing status such as `bool_hygiene_failed` with a structured `boolHygieneResult`.
- Include bool-hygiene summary in Pass D dry-run reports: status, issue count, error count, and the first bounded issue list.
- Keep `save_workbook_safely()` as the final real-write guard. The dry-run check is a preflight mirror, not a replacement.

Regression cases to add:

- Existing sheet convention text: adding rows to `context_section_master.is_required` / `context_section_master.active` writes text bools and dry-run is green.
- Existing Z sheet convention text: adding rows to `zr1_options.active` and `zr1_options.selectable` writes text bools.
- New sheet from template: creating `grandSportX_options` inherits bool column convention from `grandSport_options`.
- A deliberately mismatched dry-run returns `bool_hygiene_failed` before write.
- `save_workbook_safely()` still rejects an unapproved direct bool migration.

### 3.3 Fix Grand Sport X registry key emission

Required behavior:

- Change `MODEL_PLAN_CONFIG["grand_sport_x"]["registryKey"]` from `grandSportX` to `grand_sport_x`.
- Rebuild affected test fixtures and expectations that currently assert `grandSportX` in `model_master` or `model_registry_promotion` rows.
- Keep `sheetPrefix: "grandSportX_"` for this pass unless a separate sheet-naming migration is approved. The runtime blocker is the registry key, not the physical workbook sheet prefix.
- Add a regression that builds a Grand Sport X plan and asserts both planned rows use `registry_key == "grand_sport_x"`.
- Add or extend a temp-activation metadata validation test proving `load_model_config_overrides()` accepts the planned Grand Sport X metadata after the key fix.

### 3.4 Replace misleading per-sheet totals with action-aware continuity evidence

The current apply dry-run reports per-sheet totals that mix create/add/update/delete. That hid delete-only rule-group surfaces.

Required behavior:

- Add action-aware counts to `apply-plan.json` and apply reports, for example:
  - `perSheetActionCounts[sheet][action]`;
  - `runtimeContinuity[model].sourceOps.priceRules.add/update/delete/create_sheet`;
  - `runtimeContinuity[model].sourceOps.ruleGroups.add/update/delete/create_sheet`.
- Keep the old `perSheetCounts` only if consumers still need it, but do not use it as readiness evidence.
- Add a fixture regression where a sheet has only `delete` ops and prove the continuity report does not classify that as populated runtime coverage.

### 3.5 Add a deployment-continuity probe before live write

Create a deterministic, temp-only continuity probe owned by the ingest apply path. It may live in `WizardSessionStore` or a helper module, but the CLI must expose it through the dry-run report.

Required behavior:

- Copy `stingray_master.xlsx` to a temp directory.
- Apply the rebuilt combined plan to the temp copy using the same prepared ops and bool-storage conventions as live write.
- In the temp copy only, activate the candidate model metadata needed for generation/probing; do not modify the real workbook.
- Run model metadata loading and draft/runtime-contract generation for `grand_sport_x`, `zr1`, and `zr1x` against the temp copy.
- Emit a `deploymentContinuity` report per model with at least:
  - `registryLoadable` true/false and error text;
  - choice count;
  - direct rule count;
  - rule-group count;
  - exclusive-group count;
  - price-rule count;
  - `pricing_deferred` warning present/absent;
  - color override count;
  - interior count;
  - interior component line-item count;
  - option/media coverage counts from emitted option/card asset fields;
  - validation warnings/errors from generated draft data.
- Compare against promoted comparator models as context only (`grand_sport` for Grand Sport X; `z06` for ZR1/ZR1X). Do not require matching counts, but flag skeleton output when a target has zero `priceRules`, zero `ruleGroups`, zero `colorOverrides`, or no component/media coverage where the source plan explicitly deferred that surface.
- The probe must never write `form-output/runtime/*` or `form-app/data.js`. Temp outputs must go under a temp directory or run artifact diagnostic file only.

Blocking policy for this pass:

- `registryLoadable=false` is a hard blocker for live write approval.
- Any bool-hygiene error is a hard blocker for live write approval.
- `priceRules == 0` with `pricing_deferred` present for ZR1/ZR1X is a deployment blocker and must be reported as such. If the implementation keeps source-row apply separate from deployment readiness, the dry-run report must label it `not_deployment_ready` and require explicit Sean approval to write a non-deployment scaffold.
- `ruleGroups == 0` for ZR1/ZR1X is a deployment blocker unless a row-level audit proves the model genuinely has no grouped relationships to author.
- `asset_map` gaps are not by themselves live-write blockers, but they must remain visible as deployment deferrals with counts.
- `color_overrides` and `interior_components` gaps are deployment blockers if generated contracts would otherwise have zero coverage for active interiors/components that the existing Z-family runtime depends on.

### 3.6 Close export-shape gaps only when the workbook row can be authored from evidence

Do not invent missing product facts to make counts look healthy. Add workbook ops only when the reviewed decision or workbook reference provides enough structured fields.

Required changes by surface:

#### Price rules

- Add structured plan support for `*_price_rules` only when a reviewed price decision has canonical fields: `condition_option_id` or resolvable condition RPO, `price_rule_type`, `target_option_id` or resolvable target RPO, `price_value`, and optional body/trim scope.
- If current review decisions do not carry those fields for required ZR1/ZR1X package/wheel/body/trim pricing, emit a blocking `price_rules_required_for_runtime` / `price_rule_unresolved_required` gap instead of `plan.valid=true`.
- Add tests that prove zero price-rule add coverage produces a deployment blocker, not a silent pass.

#### Rule groups

- Add structured plan support for `*_rule_groups` and `*_rule_group_members` when a reviewed relationship is truly grouped (`requires_any` / `excludes_any`) and has a resolvable source plus target set.
- Keep one-to-one relationships in `*_rule_mapping`; do not force all relationships into groups.
- Treat delete-only cleanup of old scaffold rule groups as cleanup, not continuity coverage.
- Add tests for add coverage, delete-only non-coverage, and unresolved endpoint blocking.

#### Color overrides

- Keep `color_overrides` workbook-owned. The plan may write rows only if it has exact `(interior_id, option_id, rule_type)` evidence and the referenced interior/option IDs are stable after the clean reprocess.
- The existing `refdel:*color_overrides.option_id` warnings show the current plan deletes options still referenced by color overrides. The rebuilt plan must either preserve/remap those references or make color override cleanup a named blocker; it must not write while silently orphaning color behavior.

#### Interior components

- Add editor/apply metadata for `interior_components` if the plan is going to write it; otherwise keep it as an explicit deployment blocker/deferral.
- Only emit rows with canonical keys and stable pricing/reference evidence. Preserve the existing `interiors.py` runtime contract and R6X/component pricing behavior.

#### Asset map / media

- Add a deployment coverage manifest for `asset_map` targets; do not make media row creation a prerequisite for the first source-row apply unless Sean explicitly wants media completeness bundled.
- If row ops are added, add `asset_map` to editor metadata with its real workbook key and only write rows with known `model_key`, `target_type`, `target_id`, and `image_url`.
- Keep `asset_map_deferred` visible in reports until rows exist or a separate media pass owns them.

## 4. Exact files expected to change

Likely implementation files:

- `scripts/corvette_form_generator/editor_ops.py`
- `scripts/corvette_form_generator/ingest/wizard/plan_builder.py`
- `scripts/corvette_form_generator/ingest/wizard/session.py`
- `scripts/ingest_wizard_apply.py`
- `tests/ingest_wizard_fixtures.py`
- `tests/test_editor_ops_apply.py`
- `tests/test_editor_ops_global_families.py`
- `tests/test_ingest_wizard_apply.py`
- `tests/test_ingest_wizard_plan.py`

Possible if structured authoring fields are needed for price/rule/component/media decisions:

- `scripts/corvette_form_generator/ingest/wizard/decisions.py`
- `scripts/ingest_wizard_server.py`
- `visualizer/ingest-wizard/wizard.js`
- `visualizer/ingest-wizard/wizard.css`
- focused server/UI tests covering the new structured lanes

Docs/spec files:

- `docs/ingest/pass-d/pass-d1-export-continuity-and-deployment-readiness-spec.md` — close after implementation.
- `docs/ingest/pass-d/pass-d-approved-workbook-apply-spec.md` — update status so it no longer implies the old plan is write-ready.
- `docs/ingest/README.md` — point to this blocker-closure pass.
- `docs/ingest/ingest-wizard-end-to-end-completion-spec.md` — update only if the Pass D/E/F route-map summary changes.

Run artifacts:

- New/rebuilt run artifacts under `form-output/ingest-wizard/<new-or-rebuilt-run-id>/` are expected.
- Old run artifacts for `20260707-193441-ea9e4c` should not be hand-edited except for an explicit superseded/diagnostic report if the implementation chooses that route.

Not expected in implementation before separate live-write approval:

- `stingray_master.xlsx`
- `form-app/data.js`
- `form-output/runtime/*`
- dealer submission files
- runtime JS product-rule exceptions

## 5. Companion-file impact matrix

| Surface | Status for this spec | Required action |
|---|---|---|
| Workbook source | Not changed during implementation | Fixture/temp writes only; real workbook write requires new approval after rebuilt report |
| Apply path | Updated | Dry-run mirrors bool-storage write guard; reports bool hygiene and continuity |
| Plan builder | Updated | Schema `pass-c-2`, registry key fix, action-aware continuity, structured blockers |
| Ingest review/server/UI | Possible update | Only if needed to capture structured price/rule/component/media fields safely |
| Generated runtime contracts | Temp-only diagnostic | No checked-in runtime artifact changes before explicit workbook apply/generation pass |
| Tests | Updated | Bool convention, registry key, action-aware continuity, deployment probe/blockers |
| Docs/index | Updated | This spec plus stale Pass D readiness wording |
| Gate reminders / skills | Inspect after implementation | Patch `27vette-gate` only if the Pass D gate menu misses the new bool/continuity checks |
| Runtime/dealer | Not applicable | No dealer endpoint, payload, Turnstile, or live submission changes |

## 6. Constraints and non-goals

Spec-specific constraints:

- No live `stingray_master.xlsx --write` under this approval.
- No `approved_bool_type_migrations` for ingest plan application unless Sean approves a named sheet/column migration separately.
- No runtime alias for `grandSportX`; fix the workbook metadata emitted by the plan.
- No hardcoded ZR1/ZR1X product exceptions in runtime JS or generator logic.
- No count-matching against Grand Sport/Z06 as a product requirement; comparator counts are continuity smoke evidence, not a quota.
- No media completeness bundled into the first source-row apply unless Sean explicitly approves that expansion.
- No commits, pushes, or branch changes unless Sean asks.

Non-goals:

- Runtime promotion to `form-app/data.js`.
- Live dealer-submission validation.
- Broad copy cleanup or UI redesign.
- Full media/asset-map population.
- Re-reviewing every old Pass B/C decision unrelated to the blocker surfaces above.

## 7. Validation plan

Targeted implementation gates:

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
  tests/test_ingest_wizard_plan.py \
  tests/test_editor_ops_global_families.py -q
node --check visualizer/ingest-wizard/wizard.js
```

Real-run dry-run gates after rebuilding the plan:

```sh
.venv/bin/python scripts/ingest_wizard_apply.py --run <rebuilt-run-id>
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Required report assertions for the rebuilt dry-run:

- `write=false`.
- `ok=true` only if bool hygiene is clean.
- `schemaVersion` reflects the updated Pass D.1 report contract.
- `plan.schemaVersion == "pass-c-2"`.
- `boolHygieneResult.error_count == 0`.
- `deploymentContinuity.grand_sport_x.registryLoadable == true`.
- `deploymentContinuity.zr1.registryLoadable == true`.
- `deploymentContinuity.zr1x.registryLoadable == true`.
- The report explicitly labels any remaining zero `priceRules`, zero `ruleGroups`, zero `colorOverrides`, zero component coverage, or media gaps as either blocking deployment findings or approved deferrals.
- `workbookBefore == workbookAfter` for dry-run.
- `backupPath == null`, no `apply-report.json`, and session remains pre-apply.
- `git diff --name-only -- stingray_master.xlsx form-app form-output/runtime` is empty after dry-run validation.

If structured UI lanes are changed, add the ingest wizard gate:

```sh
.venv/bin/python -m pytest \
  tests/test_ingest_wizard_server.py \
  tests/test_ingest_wizard_server_pass_b.py \
  tests/test_ingest_wizard_decisions.py -q
node --check visualizer/ingest-wizard/wizard.js
```

Future live-write gate, only after separate explicit approval:

```sh
.venv/bin/python scripts/ingest_wizard_apply.py --run <rebuilt-run-id> --write --confirm-plan-warnings
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

After a live write, the next separate generation/promotion pass must regenerate and validate affected model artifacts before any `form-app/data.js` publication. This D.1 spec does not approve promotion.

## 8. Closure

Pass D.1 is implemented. The next approval checkpoint is not a live workbook write; it is a rebuilt `pass-c-2` dry-run report review. Only after that report proves bool hygiene and explicitly labels any deployment blockers/deferrals should Sean approve or reject a specific `--write` command for the rebuilt run.
