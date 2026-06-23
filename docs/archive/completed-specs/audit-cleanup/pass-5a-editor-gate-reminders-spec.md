# Pass 5A — Editor Gate Reminder Behavior Spec

Status: Implemented 2026-06-21.
Date: 2026-06-21
Recommended reasoning level for implementation agent: medium.

## Goal

Remove the optional Grand Sport rule-audit test from the workbook editor's default post-apply gate reminders, with a focused regression test for `gate_reminders()`.

This pass is intentionally narrow: it changes workflow reminder behavior only. It does not change workbook data, generated artifacts, runtime behavior, schema validation, registry publication, or the optional Grand Sport audit/report tooling itself.

## Diagnosis

### Root cause

`AGENTS.md` classifies Grand Sport rule-audit/report refresh as optional audit/report tooling, not default readiness. `docs/Audit-route-map.md` identifies this as the small half of Pass 5 before the riskier schema-validator cleanup.

The workbook editor apply pipeline still includes the optional Grand Sport audit test in default reminder commands:

- `scripts/corvette_form_generator/editor_ops.py:578` defines `GATE_COMMANDS`.
- `scripts/corvette_form_generator/editor_ops.py:583-587` lists Grand Sport commands and includes `node --test tests/grand-sport-rule-audit.test.mjs`.
- `scripts/corvette_form_generator/editor_ops.py:595-602` exposes `gate_reminders(models)`, which deduplicates and returns those reminder commands.

There is currently no direct `gate_reminders()` test in `tests/test_editor_ops_apply.py`; that file imports several editor-op helpers but not `gate_reminders()`.

### Evidence inspected

Preflight evidence from this spec-writing pass:

- Branch/worktree:
  - current branch from `git status --short --branch`: `schema-ingestion-normalization...origin/main`.
  - worktree was clean before writing this spec.
- `docs/Audit-route-map.md:254-261` defines Pass 5 as gate/validator cleanup and says it should be split if needed:
  - editor gate reminder cleanup is the small workflow-reminder fix;
  - schema validator cleanup is a separate source-contract pass.
- `scripts/corvette_form_generator/editor_ops.py:578-602` shows `GATE_COMMANDS` and `gate_reminders()`.
- `tests/test_editor_ops_apply.py:21-28` imports editor-op helpers but does not import `gate_reminders()`.

### Risk level

Low.

This pass removes one reminder string from an editor response. It does not remove the optional test file, change `build_rule_sources.py`, modify generation behavior, or weaken workbook validation. The main risk is accidentally changing the broader gate list or losing deduplication/unknown-model behavior in `gate_reminders()`.

### Change type

Workflow reminder behavior + tests.

## Exact files to change

1. `scripts/corvette_form_generator/editor_ops.py`
   - Remove only this command from `GATE_COMMANDS["grand_sport"]`:
     - `node --test tests/grand-sport-rule-audit.test.mjs`
   - Do not add registry reminders.
   - Do not reorder or rewrite the rest of the gate list unless the test requires a minimal import/style adjustment.
   - Do not change Stingray or Z06 reminder lists.
   - Do not delete or modify `tests/grand-sport-rule-audit.test.mjs`.
   - Do not delete or modify `scripts/build_rule_sources.py`.

2. `tests/test_editor_ops_apply.py`
   - Import `gate_reminders` from `corvette_form_generator.editor_ops`.
   - Add direct focused tests for `gate_reminders()`.
   - Minimum assertions:
     - `gate_reminders({"grand_sport"})` includes:
       - `.venv/bin/python scripts/generate_form.py --model grand_sport`
       - `.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx`
       - `node --test tests/grand-sport-contract-preview.test.mjs`
       - `node --test tests/grand-sport-draft-data.test.mjs`
     - `gate_reminders({"grand_sport"})` does not include `node --test tests/grand-sport-rule-audit.test.mjs`.
     - A multi-model call such as `gate_reminders({"stingray", "grand_sport"})` deduplicates the shared schema validation reminder exactly once.
   - Keep the test behavioral; do not assert unrelated implementation details.

3. `docs/audit-cleanup/pass-5a-editor-gate-reminders-spec.md`
   - Update this spec before final handoff.
   - Change `Status` from `Spec only` to `Implemented <date>`.
   - Add completion evidence: changed files, exact gate results, and whether `docs/Audit-route-map.md` was intentionally left unchanged to preserve the narrow 5A scope.

## Constraints and boundaries

- No workbook edits.
- No generated artifact edits.
- No runtime JavaScript/CSS/HTML edits.
- No registry/dealer submission changes.
- No schema-validator cleanup in this pass.
- No `docs/Audit-route-map.md` status correction unless separately approved.
- Preserve optional Grand Sport audit/report tooling; only remove it from default editor reminders.
- Do not add new dependencies.
- Keep the pass small and reviewable.

## Explicit non-goals

- Do not implement Pass 5B.
- Do not remove `LEGACY_MODEL_SOURCES`, `HEADER_PAIRS`, or `REQUIRED_SHEETS` from `schema_validation.py`.
- Do not reclassify all editor gates.
- Do not add `generate_registry.py` reminders.
- Do not change workbook editor apply semantics beyond the returned reminder list.
- Do not update stale `docs/Audit-route-map.md:13` `MODEL_CONFIGS` evidence in this pass unless the user explicitly expands scope to a tiny route-map status correction.

## TDD plan

1. RED
   - Update `tests/test_editor_ops_apply.py` to import `gate_reminders` and add the focused Grand Sport reminder test before touching `editor_ops.py`.
   - Run:

```sh
.venv/bin/python -m pytest tests/test_editor_ops_apply.py -q
```

   - Expected failure: the new test should fail because `gate_reminders({"grand_sport"})` still returns `node --test tests/grand-sport-rule-audit.test.mjs`.

2. GREEN
   - Remove only the optional audit test command from `GATE_COMMANDS["grand_sport"]` in `scripts/corvette_form_generator/editor_ops.py`.
   - Re-run:

```sh
.venv/bin/python -m pytest tests/test_editor_ops_apply.py -q
```

3. Review
   - Confirm `git diff` only contains the test, the one-command removal, and this spec's completion update.
   - Run:

```sh
git diff --check
```

## Validation plan

Required gates for implementation:

```sh
.venv/bin/python -m pytest tests/test_editor_ops_apply.py -q
git diff --check
```

Not required for this narrow pass:

- `scripts/generate_form.py --model ...` because no generator/workbook/runtime data path changes.
- `scripts/validate_workbook_schema.py` because no workbook/schema-validation behavior changes.
- Node runtime/model tests because no generated app/runtime behavior changes.
- Grand Sport audit/report refresh because the optional audit tooling is preserved and only removed from default reminders.

## Completion requirements

Completed 2026-06-21.

Changed files:

- `scripts/corvette_form_generator/editor_ops.py`
- `tests/test_editor_ops_apply.py`
- `docs/audit-cleanup/pass-5a-editor-gate-reminders-spec.md`

Gate results:

- RED: `.venv/bin/python -m pytest tests/test_editor_ops_apply.py -q` failed as expected before the implementation because `gate_reminders({"grand_sport"})` still returned `node --test tests/grand-sport-rule-audit.test.mjs`.
- GREEN: `.venv/bin/python -m pytest tests/test_editor_ops_apply.py -q` passed with `35 passed` after removing only the optional Grand Sport audit reminder.

`docs/Audit-route-map.md` was intentionally not updated in this pass to preserve the narrow Pass 5A scope. Its stale top-level `MODEL_CONFIGS` evidence remains deferred to a separate docs/status correction.

## Historical approval prompt

Approve Pass 5A implementation as scoped above?
