# Pass 7 — Runtime Rule Exception Hardcode Cleanup Spec

Status: Implemented 2026-06-22.
Date: 2026-06-22
Recommended reasoning level for implementation agent: high.

## Goal

Remove the remaining browser runtime product/RPO hardcode for the Stingray GBA/ZYC precedence rule and replace it with generic evaluation of workbook-generated `runtimeRuleExceptions` metadata.

This is the first business-rule hardcode cleanup after Pass 6C source-row assembly unification. Keep the pass narrow: prove the existing workbook row already owns the rule, make runtime JavaScript consume that generated metadata generically, and preserve current behavior.

## Implementation summary

Implemented on 2026-06-22.

Actual changed files:

- `form-app/app.js`
  - Added generic `runtimeExceptionAllowsCandidateOverSelectedTarget(candidateOptionId, selectedTargetOptionId)` helper.
  - Replaced the literal GBA/ZYC bypass in `disableReasonForChoice()` with generated `runtimeRuleExceptions` precedence logic.
- `tests/stingray-form-regression.test.mjs`
  - Strengthened `runtime defaults and RPO exceptions are workbook-generated metadata` to assert the emitted `ex_gba_zyc` source/target/type/scope fields.
  - Added a source guard rejecting active `choice.rpo === "GBA"` and `rule.source_id === "opt_zyc_001"` hardcodes in `form-app/app.js`.
  - Added runtime behavior coverage proving selected ZYC does not disable GBA, selecting GBA removes ZYC from selected/userSelected, and ZYC cannot stick while GBA is selected.
- `docs/Audit-route-map.md`
  - Marked Pass 7 implemented and moved the next recommendation to direct-rule field classification.
- `docs/audit-cleanup/pass-7-runtime-rule-exception-hardcode-cleanup-spec.md`
  - Closed this spec with implementation evidence.

Workbook/generated artifacts:

- No workbook writes.
- No generated artifacts retained.
- `git diff -- form-output form-app/data.js` returned no diff after validation.

Evidence:

- Preflight read-only workbook probe confirmed active `runtime_rule_exceptions.ex_gba_zyc`:
  - `model_key=stingray`
  - `source_option_id=opt_gba_001`
  - `target_option_id=opt_zyc_001`
  - `exception_type=remove_target_when_source_selected`
  - `active=True`
- RED verification: the new focused Stingray test failed before implementation because `form-app/app.js` still matched `/choice\.rpo\s*===\s*["']GBA["']/`.
- GREEN verification: the focused tests passed after replacing the hardcode with generated-metadata logic.
- Source guard confirmed `form-app/app.js` no longer contains the active hardcode needles `choice.rpo === "GBA"` or `rule.source_id === "opt_zyc_001"`.

Gates run:

- `node --test --test-name-pattern 'runtime defaults and RPO exceptions|GBA replaces selected ZYC' tests/stingray-form-regression.test.mjs` — RED failed as expected before implementation, then passed after implementation.
- `node --test tests/stingray-form-regression.test.mjs` — 87 passing tests.
- `node --test tests/multi-model-runtime-switching.test.mjs` — 44 passing tests.
- `node --test tests/z06-runtime-rule-corrections.test.mjs` — 14 passing tests.
- `node --test tests/z06-performance-package-interactions.test.mjs` — 17 passing tests.
- Source hardcode guard script — passed.

Residual risks:

- Browser/manual smoke was not run; this was a generic runtime rule-evaluation change covered by Node runtime tests, with no visual/CSS changes.
- This pass intentionally did not classify or migrate `runtime_action=replace`, `body_style_scope`, exclusive-group ID/style drift, Z06 no-RPO ID drift, or copy allowlist decisions.

Recommended next pass:

- Write a report/spec pass for `runtime_action=replace` and `body_style_scope` classification. It should classify current active direct-rule rows into canonical workbook owners before deleting columns or changing emitted behavior.

## Diagnosis

Change type: runtime + tests + docs. No workbook write is planned.

Risk level: medium. The code path controls live option availability and selection reconciliation in the customer-facing app. The scope is narrow and already backed by workbook metadata, but a wrong implementation can either re-disable GBA when ZYC is selected or allow invalid GBA/ZYC coexistence.

Current evidence inspected 2026-06-22:

- Branch/status:

```text
## schema-ingestion-normalization...origin/main
 M docs/Audit-route-map.md
 M scripts/corvette_form_generator/model_generation.py
 M scripts/corvette_form_generator/production.py
 M tests/test_generate_form_model_discovery_cli.py
 M tests/test_model_generation_route.py
 M tests/test_runtime_contract_builder.py
?? docs/audit-cleanup/pass-6c-source-row-assembly-unification-spec.md
?? scripts/corvette_form_generator/source_assembly.py
?? tests/test_source_assembly_characterization.py
```

Those are Pass 6C source/docs/test changes. Pass 7 implementation should inspect current status again and avoid touching unrelated work.

- `form-app/app.js` already loads generated runtime exceptions:

```js
function generatedRuleExceptions() {
  return Array.isArray(data.runtimeRuleExceptions) ? data.runtimeRuleExceptions : [];
}

function runtimeExceptionForTarget(targetOptionId) {
  return generatedRuleExceptions().find(
    (exception) =>
      exception.exception_type === "remove_target_when_source_selected" &&
      exception.target_option_id === targetOptionId &&
      exceptionApplies(exception) &&
      selectedOptionForException(exception.source_option_id)
  );
}

function removeRuntimeExceptionTargets(sourceOptionId = "") {
  for (const exception of generatedRuleExceptions()) {
    if (exception.exception_type !== "remove_target_when_source_selected") continue;
    if (!exceptionApplies(exception)) continue;
    if (sourceOptionId && exception.source_option_id !== sourceOptionId) continue;
    if (state.selected.has(exception.source_option_id)) deleteSelectedOption(exception.target_option_id);
  }
}
```

- `disableReasonForChoice()` still contains a product/RPO-specific bypass:

```js
if (choice.rpo === "GBA" && rule.source_id === "opt_zyc_001") continue;
```

This lets Black paint (`GBA`, `opt_gba_001`) remain selectable when `ZYC` is currently selected, so selecting GBA can remove ZYC instead of being blocked by the reverse direct exclude.

- The workbook already has the source-of-truth row in `runtime_rule_exceptions`:

```text
model_key: stingray
exception_id: ex_gba_zyc
source_option_id: opt_gba_001
target_option_id: opt_zyc_001
exception_type: remove_target_when_source_selected
body_style_scope: *
trim_level_scope: *
variant_scope: *
disabled_reason: ZYC Body-Color Accents are not available with Black exterior paint.
active: True
notes: Black paint removes ZYC body-color accent availability.
```

- `form-app/data.js` currently emits the Stingray `runtimeRuleExceptions` row list including `ex_gba_zyc`. Grand Sport and Z06 currently emit no `runtimeRuleExceptions` rows.

- Existing tests already prove adjacent behavior:
  - `tests/stingray-form-regression.test.mjs` asserts generated `runtimeRuleExceptions` includes `ex_gba_zyc`, `ex_nwi_nga`, `ex_z51_fe1`, and `ex_z51_fe2`.
  - `tests/multi-model-runtime-switching.test.mjs` asserts GBA blocks EDU but not CFL across active models.
  - `tests/z06-runtime-rule-corrections.test.mjs` asserts Z06 GBA blocks EDU/ZYC/D84/D86 and does not block CFL through workbook metadata.

Root cause:

The runtime has generic machinery for `remove_target_when_source_selected`, but `disableReasonForChoice()` still needs a generic precedence check for the reverse direction: when a candidate option is the `source_option_id` of an applicable runtime exception and a currently selected option is the `target_option_id`, the candidate should not be disabled by a direct reverse `excludes` rule. The current implementation expresses that precedence as a hardcoded GBA/ZYC branch.

## Ownership decision

- Workbook owns the business decision: `runtime_rule_exceptions.ex_gba_zyc` says GBA removes ZYC.
- Runtime owns generic evaluation: if generated metadata says a candidate source removes a currently selected target, the candidate may remain selectable and selection reconciliation removes the target.
- Tests own the regression contract: GBA/ZYC behavior must be preserved, and `form-app/app.js` must not contain the product-specific GBA/ZYC bypass.

No new workbook row, generator branch, or generated artifact shape is needed for this pass unless implementation evidence proves the emitted `runtimeRuleExceptions` row is incomplete. If the row is missing or not emitted, stop and report; do not replace the JavaScript hardcode with another hardcode.

## Exact files to change

Expected implementation files:

- `form-app/app.js`
  - Remove the literal `choice.rpo === "GBA" && rule.source_id === "opt_zyc_001"` branch.
  - Add or reuse a generic helper that detects whether a selected source rule should yield to an applicable generated runtime exception where the candidate choice is the exception source and the selected blocker is the exception target.
  - Keep the helper data-driven by `runtimeRuleExceptions`; no RPO/model-specific literals.

- `tests/stingray-form-regression.test.mjs`
  - Add or strengthen behavior coverage for the Stingray GBA/ZYC precedence loop.
  - Add a source guard rejecting the GBA/ZYC runtime hardcode in `form-app/app.js`.

- `docs/audit-cleanup/pass-7-runtime-rule-exception-hardcode-cleanup-spec.md`
  - Update status/evidence/gates when implementation completes.

Optional only if focused ownership tests need a better home:

- `tests/multi-model-runtime-switching.test.mjs`
  - Keep or strengthen active-model GBA/EDU/CFL coverage if the implementation touches shared rule evaluation in a way that could affect Grand Sport/Z06.

Standing doc update on completion:

- `docs/Audit-route-map.md`
  - Mark the GBA/ZYC hardcode item implemented and move the remaining Pass 7 candidates (`runtime_action=replace`, `body_style_scope`, exclusive-group ID/style drift, Z06 ID/no-RPO drift, copy allowlist decisions) to later separately scoped passes.

Files intentionally out of scope:

- `stingray_master.xlsx`
- `form-output/*`
- `form-app/data.js`
- `scripts/generate_form.py`
- `scripts/corvette_form_generator/*` except no expected changes
- dealer submission endpoint/payload/Turnstile code

## Proposed implementation shape

Add a generic helper near the existing runtime exception helpers, for example:

```js
function runtimeExceptionAllowsCandidateOverSelectedTarget(candidateOptionId, selectedTargetOptionId) {
  return generatedRuleExceptions().some(
    (exception) =>
      exception.exception_type === "remove_target_when_source_selected" &&
      exception.source_option_id === candidateOptionId &&
      exception.target_option_id === selectedTargetOptionId &&
      exceptionApplies(exception) &&
      state.selected.has(selectedTargetOptionId)
  );
}
```

Then replace the hardcoded bypass inside `disableReasonForChoice()` with generic logic:

```js
if (runtimeExceptionAllowsCandidateOverSelectedTarget(choice.option_id, rule.source_id)) continue;
```

The exact helper name/placement can change, but the semantics should stay generic and generated-data-driven.

The helper intentionally uses current `state.selected` for this pass. That matches the live GBA/ZYC behavior being retired from hardcoded logic. Do not broaden it to accept alternate selected contexts or candidate-simulation sets in this pass; if later cleanup needs broader generic selected-context evaluation, scope that separately and pass the already-computed selected set explicitly.

Important behavior boundaries:

- Do not make every `remove_target_when_source_selected` exception suppress all direct conflicts. It should only apply when the candidate is the exception source and the currently selected blocker is the exception target.
- Keep existing `runtimeExceptionForTarget()` behavior: when GBA is already selected, ZYC should show the workbook disabled reason and not stick if clicked.
- Keep `removeRuntimeExceptionTargets()` behavior: selecting GBA should remove selected ZYC during reconciliation.
- Do not change generic `excludes_any`, `requires_any`, exclusive group, include, default-selection, or price-rule evaluation.

## Constraints

- Visual preservation: no UI styling/markup changes.
- No workbook writes.
- No generated artifacts retained.
- No new dependencies.
- No refactor beyond the small generic helper and call-site replacement.
- No model/RPO-specific JavaScript replacement.
- Preserve current runtime behavior for Stingray, Grand Sport, and Z06.
- Preserve Pass 6C source assembly and Pass 6B optional inspection artifact policy.
- Preserve dealer submission endpoint, payload shape, and Turnstile behavior.
- Do not fold in `runtime_action=replace`, `body_style_scope`, exclusive-group ID/style cleanup, Z06 no-RPO ID cleanup, copy allowlist cleanup, or generated artifact slimming.

## RED test requirements

Add tests before removing the hardcode. At least one new or strengthened test should fail on the current code because the literal hardcode still exists.

Required coverage:

1. Source guard:

```js
assert.doesNotMatch(appSource, /choice\.rpo\s*===\s*["']GBA["']/);
assert.doesNotMatch(appSource, /rule\.source_id\s*===\s*["']opt_zyc_001["']/);
```

Use a precise enough regex to avoid false positives from generated fixture data; this should scan `form-app/app.js` source only.

2. Workbook/generated metadata guard:

- `data.runtimeRuleExceptions` includes `ex_gba_zyc`.
- The row has:
  - `source_option_id === "opt_gba_001"`
  - `target_option_id === "opt_zyc_001"`
  - `exception_type === "remove_target_when_source_selected"`
  - active wildcard scope or emitted scope that applies to the current Stingray variant.

3. Runtime behavior guard:

- Start a Stingray runtime in a normal active variant.
- Select or seed ZYC.
- Assert GBA has no disabled reason even while ZYC is selected.
- Select GBA.
- Reconcile selections.
- Assert GBA is selected and ZYC is removed from selected/userSelected.
- Assert with GBA selected, ZYC reports the workbook disabled reason and does not stick if clicked.

4. Regression guard for adjacent behavior:

- Existing multi-model test should still prove GBA blocks EDU but not CFL across active models.
- Existing Z06 tests should still prove Z06 GBA behavior comes from workbook groups, not Stingray-only `runtimeRuleExceptions`.

## Validation plan

Preflight before implementation:

```sh
git status --short --branch
test ! -e './~$stingray_master.xlsx' && echo excel_lock_absent
.venv/bin/python - <<'PY'
from openpyxl import load_workbook
wb = load_workbook('stingray_master.xlsx', data_only=True, read_only=True)
ws = wb['runtime_rule_exceptions']
headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
rows = [dict(zip(headers, row)) for row in ws.iter_rows(min_row=2, values_only=True)]
match = [row for row in rows if row.get('exception_id') == 'ex_gba_zyc']
assert len(match) == 1, match
row = match[0]
assert row['model_key'] == 'stingray'
assert row['source_option_id'] == 'opt_gba_001'
assert row['target_option_id'] == 'opt_zyc_001'
assert row['exception_type'] == 'remove_target_when_source_selected'
assert row['active'] is True or str(row['active']).lower() == 'true'
wb.close()
print('ex_gba_zyc workbook row OK')
PY
```

Focused implementation gates:

```sh
node --test tests/stingray-form-regression.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
node --test tests/z06-runtime-rule-corrections.test.mjs
```

Runtime/static source guard:

```sh
python3 - <<'PY'
from pathlib import Path
source = Path('form-app/app.js').read_text()
for needle in ['choice.rpo === "GBA"', "choice.rpo === 'GBA'", 'rule.source_id === "opt_zyc_001"', "rule.source_id === 'opt_zyc_001'"]:
    assert needle not in source, needle
print('GBA/ZYC runtime hardcode absent')
PY
```

Generated artifact policy check:

```sh
git diff -- form-output form-app/data.js
```

Expected: no retained generated artifact diff. If a validation command regenerates artifacts and only timestamps change, restore generated churn before handoff.

Optional broader gate if the helper touches shared disable/reconcile behavior beyond the one call site:

```sh
node --test tests/stingray-form-regression.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
node --test tests/z06-runtime-rule-corrections.test.mjs
node --test tests/z06-performance-package-interactions.test.mjs
```

Final docs/status checks:

```sh
git diff --check
git status --short --branch
rg -n 'choice\.rpo === "GBA"|rule\.source_id === "opt_zyc_001"' form-app/app.js
rg -n 'choice\.rpo === "GBA"|rule\.source_id === "opt_zyc_001"' tests docs/Audit-route-map.md docs/audit-cleanup/pass-7-runtime-rule-exception-hardcode-cleanup-spec.md || true
```

The first `rg` against `form-app/app.js` is the hard-failure target and must return no matches. The second `rg` is review-only context: historical/spec mentions may remain only where clearly labeled as pre-implementation evidence.

## Risks and mitigations

Risk: removing the hardcode makes GBA disabled whenever ZYC is selected.

Mitigation: add a behavior test that starts with ZYC selected and proves GBA remains selectable and replaces ZYC through generated exception metadata.

Risk: a generic helper suppresses real conflicts too broadly.

Mitigation: scope the helper to exact exception source/target pairs that apply to the current variant and where the selected blocker is the exception target.

Risk: Stingray behavior stays green but Grand Sport/Z06 GBA rules regress.

Mitigation: run `multi-model-runtime-switching.test.mjs` and `z06-runtime-rule-corrections.test.mjs`; do not add `runtimeRuleExceptions` to GS/Z06 unless a workbook-owned need is separately proven.

Risk: implementation replaces one hardcode with another ID/RPO-specific branch.

Mitigation: source guard rejects active `choice.rpo === "GBA"` and `rule.source_id === "opt_zyc_001"` branches in `form-app/app.js`.

Risk: docs imply the broader Pass 7 cleanup is finished.

Mitigation: this Pass 7 is only the GBA/ZYC runtime-hardcode cleanup. `runtime_action=replace`, `body_style_scope`, exclusive-group ID/style drift, Z06 no-RPO ID drift, and copy allowlist cleanup remain future separately scoped passes.

## Completion requirements

Before final handoff, update this spec with:

- final status and date;
- actual changed files;
- whether the GBA/ZYC runtime hardcode was removed from `form-app/app.js`;
- workbook row / generated metadata evidence for `ex_gba_zyc`;
- runtime behavior evidence for ZYC-selected -> GBA selectable -> ZYC removed;
- adjacent active-model GBA regression evidence;
- generated artifact diff handling;
- gates run;
- residual risks;
- recommended next pass.

Also update `docs/Audit-route-map.md` so it no longer describes GBA/ZYC as an active runtime hardcode after implementation.

## Recommended next pass after Pass 7

After the GBA/ZYC runtime hardcode is removed, the safest next cleanup is a report/spec pass for `runtime_action=replace` and `body_style_scope` classification. That pass should classify current active rule rows into canonical workbook owners before deleting columns or changing emitted rule behavior.

## Historical approval prompt

Approved by user on 2026-06-22: "pass 7 approved".
