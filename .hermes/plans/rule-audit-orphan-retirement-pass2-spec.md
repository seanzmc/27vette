# Rule-Audit Orphan Retirement Spec (Simplification Pass 2)

Date: 2026-07-05
Status: Completed 2026-07-05. See completion record at end.

## Diagnosis

`form-output/inspection/grand-sport-rule-audit.json` and `.md` are tracked with no remaining writer: `scripts/build_rule_sources.py` and `tests/grand-sport-rule-audit.test.mjs` were retired (audit-cleanup Pass D), and `model_generation.py:67-76` `_rule_audit_artifacts()` only existence-checks the paths to report them in stdout metadata. Verified in the simplification audit (verifier claim 2, PASS).

The stdout metadata key is equally dead: `rule_audit_artifacts` is not in `REQUIRED_RESULT_KEYS` (model_generation.py:32-45), appears only in `_reviewable_result()` (line 189), and `git grep rule_audit` finds no other consumer in scripts/tests/form-app. The generation result is only printed by `scripts/generate_form.py:58`.

Remaining path references are historical only: `archive/2026-05-29/**` and completed `.hermes/plans` prose.

## Exact changes

1. `git rm form-output/inspection/grand-sport-rule-audit.json form-output/inspection/grand-sport-rule-audit.md` (orphaned artifacts; no writer regenerates them).
2. `scripts/corvette_form_generator/model_generation.py`: delete `_rule_audit_artifacts()` (lines 67-76) and the `"rule_audit_artifacts": _rule_audit_artifacts(config),` entry in `_reviewable_result()` (line 189). No other code changes; `REQUIRED_RESULT_KEYS` untouched.

## Constraints / non-goals

No workbook writes. No edits to live generated artifacts (`form-output/runtime/`, `form-output/stingray-form-data.*`, `form-app/`). The three `*-derived-swap-manifest.json` files in `form-output/inspection/` are out of scope. No test-logic changes expected (no test references the key or the files).

## Validation plan

1. `git grep -n "rule_audit"` in scripts/tests/form-app → no matches.
2. `PYTHONPATH=scripts .venv/bin/python -m pytest tests/test_model_generation_route.py -q` → pass.
3. `node --test tests/grand-sport-contract-preview.test.mjs tests/grand-sport-draft-data.test.mjs` → pass (Grand Sport generation path healthy without the helper); restore any gate-induced generated-artifact timestamp churn afterward.
4. `git diff HEAD -- form-output/runtime form-output/stingray-form-data.json form-output/stingray-form-data.csv form-app` → empty.
5. Independent verifier; receipt + STATE at closeout.

## Completion record

Implemented 2026-07-05 (staged, not committed). Both orphan artifacts removed via git rm; `_rule_audit_artifacts()` and the `rule_audit_artifacts` result key deleted; `REQUIRED_RESULT_KEYS` untouched.

Validation results (real output):

- `git grep rule_audit|rule-audit` in scripts/tests/form-app/form-output → only `tests/test_editor_ops_apply.py:131`, a negative assertion that gate reminders exclude rule-audit commands (kept guard).
- `PYTHONPATH=scripts pytest tests/test_model_generation_route.py` → pass (within 36-passed combined run).
- `node --test tests/grand-sport-contract-preview.test.mjs tests/grand-sport-draft-data.test.mjs` → 25/25 pass. Gate rewrote `form-output/runtime/grand-sport-runtime-contract.json` `generated_at` (known gate-churn failure mode); restored via `git restore`.
- `git diff HEAD` on live generated surfaces (`form-output/runtime`, stingray compat JSON/CSV, `form-app`, workbook) → empty.

Residual risks / follow-up: staged pending commit approval; none other implied.
