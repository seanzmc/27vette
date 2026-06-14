# Pass B Script Retirement Inventory

Status: Completed on 2026-06-13.

Scope: classify active tracked script entrypoints for one-pass writer/script retirement after Pass A. This inventory intentionally ignores `.venv/`, `__pycache__/`, `.claude/worktrees/`, and historical archive documents as active source.

## Search evidence

Tracked source command:

```sh
git ls-files scripts tests
```

Tracked candidate filename search results:

```text
apply*.py: scripts/apply_workbook_ops.py
*apply*.py: scripts/apply_workbook_ops.py, tests/test_editor_ops_apply.py
repair*.py: scripts/repair_workbook_tables.py
*repair*.py: scripts/repair_workbook_tables.py
populate*.py: none
*populate*.py: none
backfill*.py: none
*backfill*.py: none
migrate*.py: none
*migrate*.py: none
normalize*.py: none
*normalize*.py: none
generate_*_form.py: none
promote_*runtime*.py: none
*promote*runtime*.py: none
*future*review*.py: none
*audit*.py: none
```

Top-level tracked script entrypoints:

```text
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

## Classification

| Script | Classification | Action | Evidence |
| --- | --- | --- | --- |
| `scripts/generate_form.py` | Current workflow entrypoint | Keep | Documented in `AGENTS.md`/`README.md`; drives Stingray production generation and Grand Sport/Z06 draft/runtime-contract generation. |
| `scripts/promote_model.py` | Current workflow entrypoint | Keep | Documented promotion workflow; dry-run default, explicit `--write`, Excel lock refusal, `save_workbook_safely()`, and post-save verification. |
| `scripts/apply_workbook_ops.py` | Current workflow entrypoint | Keep | Workbook-editor exported-batch CLI; dry-run default, explicit `--write`; delegates to guarded `editor_ops.apply_batch`. Covered by editor tests. |
| `scripts/workbook_editor_server.py` | Current workflow entrypoint | Keep | Localhost workbook review/edit UI server; documented dev workflow and tests import server payload/write API. |
| `scripts/validate_workbook_schema.py` | Current validator | Keep | Active schema/live-contract validation gate in `AGENTS.md`/`README.md`. |
| `scripts/validate_workbook_package.py` | Current validator | Keep | Active Excel package validation gate and safe-save prerequisite. |
| `scripts/repair_workbook_tables.py` | Current recovery tool | Keep | Documented Excel repair/recovery path in `AGENTS.md`/`README.md`; not a data migration writer. |
| `scripts/compare-generated-contracts.mjs` | Current comparison helper | Keep | Documented generated JSON diff helper that ignores timestamp fields. |
| `scripts/build_rule_sources.py` | Reusable read-only report/audit helper | Keep | Exercised by `tests/grand-sport-rule-audit.test.mjs`; reads workbook and writes audit artifacts, but does not write `stingray_master.xlsx`. Gate ownership can be revisited in Pass C. |

## Package modules reviewed by ownership

Tracked files under `scripts/corvette_form_generator/` are shared implementation modules, not standalone one-pass CLIs. They were not deletion candidates for Pass B. Mutation-capable modules are owned by active entrypoints:

- `production.py` writes generated `form_*` sheets through the active Stingray production generator.
- `editor_ops.py` implements the guarded workbook editor apply pipeline used by the server and CLI.
- `registry_promotion.py` supports active runtime promotion and registry generation.
- `workbook_package.py` supports active package validation and table repair.
- `workbook.py` owns shared workbook helpers including `save_workbook_safely()`.

## Retirement result

No active tracked stale one-pass workbook writer was found.

Scripts deleted: none.

Scripts converted/quarantined: none.

References removed: none.

The correct Pass B outcome is this classification record plus cleanup-overview correction: the active tree no longer contains the obvious stale one-pass script names that Pass B was designed to catch. Current guarded workflow entrypoints remain intact.

## Residual risks and follow-up

- `scripts/build_rule_sources.py` remains a read-only/reporting rule-audit helper and is still exercised by tests. If the goal is to keep old audit tooling out of normal readiness gates, handle that in Pass C gate split, not by deleting the script in Pass B.
- Historical docs and archived worktrees may still mention old script names. They were left unchanged because they are provenance, not active workflow.
- Runtime metadata sheets remain out of scope for Pass B and belong to Pass D/runtime metadata consolidation.
