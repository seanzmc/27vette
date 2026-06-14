# Pass B Spec — One-pass Writer/Script Retirement

## Status

Completed. Approved by user and implemented as a docs/inventory cleanup pass.

## Diagnosis

Pass A removed the clearest audit-only workbook scaffold: `option_audit_groups`, `option_audit_group_members`, and `rule_review_groups`. The next cleanup risk is executable stale scripts: one-pass `apply_*`, `repair_*`, `populate_*`, migration, audit, or review writers that were useful for a single workbook repair but should not remain as easy-to-run pseudo-workflows after the workbook and tests are corrected.

The root problem is not every script in `scripts/`; the root problem is ambiguous ownership. Some scripts mutate the workbook but are active workflow entrypoints with safeguards. Others may be historical one-pass writers and should be deleted, quarantined, or converted to docs/tests so they cannot replay stale workbook state.

Initial evidence inspected for this spec:

- Current branch/status:
  - Branch: `generator-simplification-pass1`
  - Worktree was clean when this spec was written.
- Pass A completion output in `docs/audit-cleanup/pass-a-audit-scaffolding-retirement-spec.md` says Pass A is complete and recommends Pass B as stale writer/apply/repair script retirement.
- `AGENTS.md` active workflow references classify these as current supported entrypoints, not deletion candidates without contrary evidence:
  - `scripts/generate_form.py --model stingray|grand_sport|z06`
  - `scripts/promote_model.py --model z06 --write`
  - `scripts/apply_workbook_ops.py ops.json [--write] ...`
  - `scripts/validate_workbook_schema.py`
  - `scripts/validate_workbook_package.py`
  - `scripts/repair_workbook_tables.py`
- Current `scripts/*.py` inventory contains 27 Python files. Broad file-name searches found:
  - `*apply*.py`: only `scripts/apply_workbook_ops.py`
  - `*repair*.py`: only `scripts/repair_workbook_tables.py`
  - `*populate*.py`: none
  - `*audit*.py`: none
  - `generate_*_form.py`: none
  - `promote_*runtime*.py`: none
  - `build_*rule_sources.py`: only `scripts/build_rule_sources.py`
  - `*future*review*.py`: none
- `scripts/apply_workbook_ops.py` is a thin CLI over `corvette_form_generator.editor_ops.apply_batch`; default is dry-run, `--write` is explicit, and it is documented by the workbook editor workflow.
- `scripts/repair_workbook_tables.py` is documented in `AGENTS.md`/`README.md` for Excel repair/recovery and calls `corvette_form_generator.workbook_package.repair_workbook_tables`.
- `scripts/promote_model.py` is a dry-run-by-default, workbook-owned runtime promotion script with explicit `--write`, Excel lock refusal, `save_workbook_safely()`, and post-save verification.
- `scripts/build_rule_sources.py` is still exercised by `tests/grand-sport-rule-audit.test.mjs` and remains a read-only rule-source audit/report helper after Pass A.

Risk level: Medium.

Change type: workflow/docs/test/script cleanup. Intended runtime behavior impact: none.

Important conclusion from initial evidence: Pass B should be classification-first, not deletion-first. The obvious old per-model generator/promoter scripts already appear absent from the active tree. This pass should avoid deleting current guarded workflow entrypoints merely because their names contain `apply`, `repair`, or `audit`.

## Exact files and artifacts to inspect

### Active script entrypoints to classify

Inspect and classify every active script entrypoint under `scripts/`:

- `scripts/generate_form.py`
- `scripts/promote_model.py`
- `scripts/build_rule_sources.py`
- `scripts/apply_workbook_ops.py`
- `scripts/workbook_editor_server.py`
- `scripts/validate_workbook_schema.py`
- `scripts/validate_workbook_package.py`
- `scripts/repair_workbook_tables.py`
- `scripts/compare-generated-contracts.mjs`

Also classify package modules under `scripts/corvette_form_generator/` only when a top-level entrypoint or test makes them relevant. Do not treat normal shared modules as retirement candidates just because they are not direct CLIs.

### Historical/stale executable candidates

Search the full repo for executable writer leftovers before deleting anything. Candidate patterns:

- `apply_*.py`, `apply*.py`
- `repair_*.py`, `repair*.py`
- `populate_*.py`, `populate*.py`
- `backfill_*.py`, `migrate_*.py`, `normalize_*.py`
- `promote_*runtime*.py`
- `generate_*_form.py`
- `build_*rule_sources.py`
- `*future*review*.py`
- scripts that call `load_workbook()` plus `save_workbook_safely()` or workbook package repair/write helpers
- scripts that parse `--write`, `--dry-run`, or mutate `stingray_master.xlsx`

### Tests and docs to inspect/update

Reference scan before any deletion or doc change:

- `AGENTS.md`
- `README.md`
- `docs/audit-cleanup-overview.md`
- `docs/workbook-sheet-index.md`
- `docs/audit-cleanup/pass-a-audit-scaffolding-retirement-spec.md`
- `tests/*`
- `scripts/*`
- `scripts/corvette_form_generator/*`
- `docs/*` current workflow/spec docs

Historical folders such as `archive-2026-05-29/`, `architectureAudit/`, and completed `docs/superpowers/plans/` may mention old scripts as historical evidence. Do not edit those only to erase history unless they are actively referenced as current workflow documentation.

## Classification rules

For each candidate script, assign exactly one classification in the Pass B completion output.

### Keep: current workflow entrypoint

Keep scripts that are documented active workflows, used by tests, or required for workbook/editor/generator operation.

Current initial keep list unless deeper evidence proves otherwise:

- `scripts/generate_form.py` — single generator entrypoint.
- `scripts/promote_model.py` — active runtime promotion workflow; dry-run default and explicit `--write`.
- `scripts/apply_workbook_ops.py` — workbook editor exported-batch CLI; dry-run default and shared `apply_batch` pipeline.
- `scripts/workbook_editor_server.py` — localhost workbook review/edit UI server.
- `scripts/validate_workbook_schema.py` — schema/live-contract validator.
- `scripts/validate_workbook_package.py` — workbook package integrity validator.
- `scripts/repair_workbook_tables.py` — Excel/package recovery workflow referenced by `AGENTS.md` and `README.md`.
- `scripts/compare-generated-contracts.mjs` — generated JSON contract diff helper.

### Keep or narrow: reusable read-only report

Keep read-only report helpers when they remain useful and tests prove they do not write workbook state.

Initial candidate:

- `scripts/build_rule_sources.py` — retained as read-only rule-source audit/report helper after Pass A. Pass B may update docs to label it explicitly as optional/reporting if current docs imply it is a mandatory live runtime gate.

### Delete/retire: stale one-pass writer

Delete a script only if all are true:

1. It was created to repair/backfill/migrate one specific workbook state.
2. Its target workbook state is already represented by canonical workbook rows and guarded by tests/validators.
3. It is not documented as a current workflow entrypoint in `AGENTS.md`, `README.md`, or the workbook editor docs.
4. Active tests/scripts/docs do not import or execute it.
5. Any durable lesson has been moved into a test, active docs note, or skill/reference rather than left as executable code.

### Quarantine/convert instead of delete

If a script is still useful for diagnostics but unsafe as a writer:

- Convert it to report-only/dry-run default.
- Require explicit `--write` for mutation.
- Ensure it refuses Excel lock files.
- Ensure workbook writes go through `save_workbook_safely()`.
- Add exact post-save verification if it writes.
- Update docs/tests to label it as optional diagnostic tooling, not a normal form gate.

## Proposed implementation scope

Pass B should make the smallest safe cleanup based on the classification evidence.

Likely outcomes from current evidence:

1. Produce a committed classification record, for example:
   - `docs/audit-cleanup/pass-b-script-retirement-inventory.md`
2. Update `docs/audit-cleanup-overview.md` so Pass B reflects current evidence instead of implying many active stale scripts still exist.
3. Keep the currently supported guarded scripts listed above unless the implementation scan finds a true stale one-pass writer.
4. If implementation finds true stale executable leftovers, delete them and remove active references.
5. Do not edit `stingray_master.xlsx` in Pass B unless a candidate script removal requires a workbook reference cleanup that cannot be represented in docs/tests. Current expectation: no workbook edits.

## Exact files likely to change

Expected spec/implementation docs:

- `docs/audit-cleanup/pass-b-one-pass-script-retirement-spec.md`
- `docs/audit-cleanup/pass-b-script-retirement-inventory.md` if implementation produces a separate inventory artifact
- `docs/audit-cleanup-overview.md` if it needs current-state correction after Pass A

Possible active docs, only if references are stale or misleading:

- `AGENTS.md`
- `README.md`

Possible script/test files, only if the implementation scan finds a true stale executable or a retained script needs a safer/report-only contract:

- `scripts/<stale-one-pass-writer>.py`
- `tests/<test-that-imports-or-executes-stale-writer>.mjs`
- `tests/<test-that-imports-or-executes-stale-writer>.py`

Expected no-change boundaries:

- `stingray_master.xlsx`
- generated workbook `form_*` sheets
- `form-output/*`
- `form-app/data.js`
- `form-app/app.js`
- dealer submission code/endpoint

## Constraints

- Preserve customer-facing runtime behavior.
- Preserve dealer submission endpoint, payload shape, and Turnstile behavior.
- No visual/runtime UI changes.
- No new dependencies.
- No workbook source-data edits unless separately approved.
- No generated artifact hand edits.
- Do not delete current generators, validators, promotion scripts, or workbook editor apply paths merely because they can write; classify them by active workflow use and safety guards.
- Do not preserve stale writers as executable documentation. Move durable reasoning into docs/tests/skills instead.
- Do not rewrite historical archive documents just to remove old references unless they are misleading active workflow docs.
- Keep Pass B separate from Pass C gate splitting and Pass D runtime metadata consolidation.

## Non-goals

Pass B will not:

- Retire or redesign `runtime_steps`, `context_section_master`, `section_presentation`, `context_choice_copy`, `order_summary_sections`, `step_order_summary_map`, `runtime_rule_exceptions`, or `variant_option_overrides`.
- Change model runtime promotion behavior.
- Change generated runtime data shape.
- Clean up Z06/ZR1/ZR1X product rules, prices, interiors, or source rows.
- Reorganize the generator architecture.
- Convert the workbook editor pipeline.
- Split default/live gates from optional audit gates; that remains Pass C.

## Validation plan

Run after implementation.

### Always run for Pass B

```sh
git status --short --branch
.venv/bin/python -m py_compile scripts/*.py scripts/corvette_form_generator/*.py
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
node --test tests/stingray-form-regression.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

### If `apply_workbook_ops.py`, `editor_ops.py`, or `workbook_editor_server.py` are touched

```sh
.venv/bin/python -m pytest tests/test_editor_ops_apply.py tests/test_editor_server_payload.py tests/test_editor_server_write_api.py -q
```

### If `promote_model.py` or registry promotion code is touched

```sh
.venv/bin/python scripts/promote_model.py --model z06
node --test tests/z06-runtime-promotion.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Do not run `promote_model.py --write` in Pass B unless a separate approved implementation step explicitly changes promotion behavior. Current expectation: dry-run only.

### If `build_rule_sources.py` is touched

```sh
.venv/bin/python scripts/build_rule_sources.py --model grand_sport
node --test tests/grand-sport-rule-audit.test.mjs
```

### If only docs/inventory files change after classification

```sh
git diff -- docs/audit-cleanup README.md AGENTS.md
```

Then state that runtime/generator gates were not run because no executable/runtime/workbook behavior changed.

### Diff review requirement

After validation, run:

```sh
git diff --name-only
git diff --stat
```

If generator/test commands produce timestamp-only `form-output/*` churn, restore unrelated generated artifacts before handoff and state that they were restored.

## Expected outcome

- Every active script entrypoint is classified as current workflow, reusable report/validator, one-pass writer, or historical context.
- Any true stale one-pass writer found in active code is deleted or converted to safe report-only/dry-run behavior.
- Current guarded workflows remain intact:
  - generation
  - promotion
  - workbook editor apply
  - workbook package/schema validation
  - workbook table repair
- Normal repo docs no longer imply stale one-pass writers are current workflow.
- Runtime form behavior remains unchanged.

## Risks

- The active tree may already have removed most stale writers. If so, the correct Pass B result may be an inventory/doc correction rather than large code deletion.
- Deleting `apply_workbook_ops.py` or `repair_workbook_tables.py` would be wrong unless their documented workflows have been replaced; current evidence says they are active guarded tools.
- `build_rule_sources.py` is still test-exercised and read-only; deleting it in Pass B would collapse useful Grand Sport rule-audit coverage. Gate splitting belongs in Pass C, not this pass.
- Historical docs can contain old names intentionally. Editing archives may erase useful provenance without reducing active workflow clutter.

## Completion output — 2026-06-13T22:09:55Z

Status: Completed.

What changed:

- Added the Pass B implementation inventory:
  - `docs/audit-cleanup/pass-b-script-retirement-inventory.md`
- Updated `docs/audit-cleanup-overview.md` to mark Pass A and Pass B complete and to record the current Pass B result.
- Updated this spec status from proposed to completed.

What did not change:

- No scripts were deleted.
- No tests were edited.
- No workbook sheets or source data were changed.
- No generated workbook `form_*` sheets were changed.
- No `form-output/*`, `form-app/data.js`, `form-app/app.js`, dealer submission endpoint, payload, or Turnstile behavior changed.

Candidate script review result:

```text
Tracked top-level script entrypoints reviewed:
scripts/apply_workbook_ops.py
scripts/build_rule_sources.py
scripts/compare-generated-contracts.mjs
scripts/generate_form.py
scripts/promote_model.py
scripts/repair_workbook_tables.py
scripts/validate_workbook_package.py
scripts/validate_workbook_schema.py
scripts/workbook_editor_server.py
```

Classification result:

```text
Current workflow entrypoints kept:
- scripts/generate_form.py
- scripts/promote_model.py
- scripts/apply_workbook_ops.py
- scripts/workbook_editor_server.py
- scripts/validate_workbook_schema.py
- scripts/validate_workbook_package.py
- scripts/repair_workbook_tables.py
- scripts/compare-generated-contracts.mjs

Reusable read-only/report helper kept:
- scripts/build_rule_sources.py

One-pass workbook writers found in active tracked source:
- none

Scripts deleted or quarantined:
- none
```

Validation run:

```sh
git ls-files scripts | sort
python3 tracked-candidate-inventory snippet
git diff -- docs/audit-cleanup README.md AGENTS.md
git diff --name-only
git diff --stat
```

Gate results:

- Runtime/generator/workbook gates: not run because Pass B only changed docs/inventory files and did not edit executable code, workbook data, runtime data, or generated artifacts.
- Docs diff review: run.
- Git diff/stat review: run.

Manual verification still pending:

- None required for live form behavior; no runtime or workbook behavior changed.

Recommended next pass:

- Pass C: required gate split. Keep `build_rule_sources.py` available as read-only diagnostic/report tooling, but decide whether rule-audit tests belong in the default/live readiness path or in an optional audit/dev gate.
