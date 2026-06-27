# Root Archive Folder and Old Plan Cleanout Spec

Date: 2026-06-27
Status: Completed on 2026-06-27 after approval.

## Diagnosis

The repo still has several root-level historical/report folders and older planning surfaces that are no longer current workflow locations:

- `architectureAudit/` is a root-level historical audit folder with one tracked report: `architectureAudit/2026-06-09-python-parser-architecture-audit.md`.
- `archive-2026-05-29/` is a tracked dated archive with 85 tracked files and nested `archive/` / `archived/` subtrees, creating the recursive archive shape Sean called out.
- `archive/` already exists and contains the canonical extracted historical workbook evidence `archive/stingray_archive.xlsx`; it is the best single root-level archive home.
- `backups/` is ignored, untracked, and currently contains 247 files / 198.45 MiB of workbook backups plus `.DS_Store` clutter. These are local recovery artifacts, not source files.
- `docs/audit-cleanup/` is now an empty filesystem directory after the prior completed-doc archive pass.
- `docs/hermes-plans/` still has two old Z06 specs whose assumptions are stale against current repo guidance, which now treats Stingray, Grand Sport, and Z06 as active promoted runtime models.
- `.hermes/plans` still has 19 tracked May-or-earlier markdown files. The previous pass classified them; this pass should archive them out of the active plan directory rather than deleting them.
- Current ignored clutter remains under archive/docs folders:
  - `archive-2026-05-29/.DS_Store`
  - `archive-2026-05-29/archive/.DS_Store`
  - `archive-2026-05-29/archived/.DS_Store`
  - `archive-2026-05-29/archived/$skills/.DS_Store`
  - `archive-2026-05-29/archived/docs/.DS_Store`
  - `archive-2026-05-29/archived/referenceSheets/~$27-processed.xlsx`
  - `docs/.DS_Store`
  - `docs/archive/.DS_Store`

Evidence inspected:

- `git status --short --branch`: `## main...origin/main`; no tracked dirty files before this spec.
- Root tracked directory counts: `archive-2026-05-29` 85, `docs` 80, `.hermes` 36, `archive` 1, `architectureAudit` 1.
- `backups/` is ignored and untracked; `git status --short --ignored -- backups` reports `!! backups/`.
- `find docs -type d -empty`: `docs/audit-cleanup`.
- `docs/hermes-plans` tracked files:
  - `docs/hermes-plans/z06-full-runtime-promotion-spec.md`
  - `docs/hermes-plans/z06-runtime-preview-contract-spec.md`
- May-or-earlier tracked `.hermes/plans/*.md` files are listed in the inventory below.

Root cause: historical evidence and old specs were preserved, but not consolidated into one archive structure. The current tree has multiple archive roots and active-looking plan/spec folders containing stale historical inputs.

Risk level: medium for file-organization churn. This should not touch workbook/runtime behavior, but moving many historical files can stale references if path updates are incomplete.

Change type: docs/archive/file-organization cleanup only. No workbook source data, generated runtime data, app code, tests, or dealer submission behavior should change.

## Exact files/directories to change after approval

### This spec

- `.hermes/plans/root-archive-folder-cleanout-spec.md`
  - Keep during implementation.
  - Before final handoff, update to completed with completion date, actual moved/deleted paths, validation output, residual risks, and next-step guidance.

### Root archive consolidation

Use `archive/` as the single root archive location.

1. Move root architecture audit report:
   - from `architectureAudit/2026-06-09-python-parser-architecture-audit.md`
   - to `archive/2026-06-09/architecture-audit/2026-06-09-python-parser-architecture-audit.md`
   - remove empty `architectureAudit/`.

2. Move `archive-2026-05-29/` into normalized paths under `archive/2026-05-29/` and remove the old root folder. Use these path rules:

   | Current path prefix | New path prefix |
   |---|---|
   | `archive-2026-05-29/architectureAudit/` | `archive/2026-05-29/architecture-audit/` |
   | `archive-2026-05-29/archive/form-output/inspection/` | `archive/2026-05-29/form-output/inspection/` |
   | `archive-2026-05-29/archived/$skills/` | `archive/2026-05-29/skills/` |
   | `archive-2026-05-29/archived/docs/` | `archive/2026-05-29/docs/` |
   | `archive-2026-05-29/archived/referenceSheets/` | `archive/2026-05-29/reference-sheets/` |
   | `archive-2026-05-29/archived/Rule_Mapping.csv` | `archive/2026-05-29/reference-sheets/Rule_Mapping.csv` |
   | `archive-2026-05-29/spec-review/` | `archive/2026-05-29/spec-review/` |
   | `archive-2026-05-29/codex-context.md` | `archive/2026-05-29/codex-context.md` |
   | `archive-2026-05-29/hover-image-feasability.md` | `archive/2026-05-29/hover-image-feasability.md` |

3. Keep `archive/stingray_archive.xlsx` in place.

4. Remove ignored stale clutter under the old archive path:
   - all `.DS_Store` files listed in the diagnosis
   - stale Excel lock file `archive-2026-05-29/archived/referenceSheets/~$27-processed.xlsx`

### Root backups cleanup

- Delete ignored local `backups/` contents and the empty `backups/` folder.
- Do not change `.gitignore` backup ignore rules except to remove/update stale references to the old `archive-2026-05-29` path.
- Do not delete any tracked workbook or tracked archive workbook.

### Old docs spec folders

1. Move stale Z06 docs specs:
   - `docs/hermes-plans/z06-runtime-preview-contract-spec.md`
     -> `docs/archive/completed-specs/z06-runtime-preview-contract-spec.md`
   - `docs/hermes-plans/z06-full-runtime-promotion-spec.md`
     -> `docs/archive/completed-specs/z06-full-runtime-promotion-spec.md`

2. Remove empty docs folders after moves:
   - `docs/audit-cleanup/`
   - `docs/hermes-plans/`

3. Remove ignored docs `.DS_Store` clutter:
   - `docs/.DS_Store`
   - `docs/archive/.DS_Store`

### May-or-earlier `.hermes/plans` archival

Move these tracked May-or-earlier active-plan files out of `.hermes/plans/` and into `docs/archive/old-plans/2026-05/`:

| Last git change | Current file |
|---|---|
| 2026-05-19 | `.hermes/plans/2026-05-19_154025-pass-3-r6x-d30-runtime-cleanup.md` |
| 2026-05-21 | `.hermes/plans/2026-05-21-stingray-grand-sport-engine-cover-structure.md` |
| 2026-05-22 | `.hermes/plans/vehicle-setup-progressive-disclosure-spec.md` |
| 2026-05-22 | `.hermes/plans/vehicle-setup-ux-spec.md` |
| 2026-05-30 | `.hermes/plans/z-exclusive-group-note-cleanup-pass-a-spec.md` |
| 2026-05-30 | `.hermes/plans/z-runtime-provenance-guard-pass-c-spec.md` |
| 2026-05-30 | `.hermes/plans/z-sht-rule-text-cleanup-pass-b-spec.md` |
| 2026-05-30 | `.hermes/plans/z-source-hygiene-audit-spec.md` |
| 2026-05-31 | `.hermes/plans/z-exterior-paint-option-sheets-spec.md` |
| 2026-05-31 | `.hermes/plans/z-option-canonical-pricing-audit.md` |
| 2026-05-31 | `.hermes/plans/z-option-canonical-pricing-pass-spec.md` |
| 2026-05-31 | `.hermes/plans/z-option-ovs-closure-pass-spec.md` |
| 2026-05-31 | `.hermes/plans/z-option-ovs-closure-phase-2a-report.md` |
| 2026-05-31 | `.hermes/plans/z-option-ovs-closure-phase-2b-decision-matrix.md` |
| 2026-05-31 | `.hermes/plans/z-option-ovs-closure-phase-2b-spec.md` |
| 2026-05-31 | `.hermes/plans/z-option-pricing-section-repair-spec.md` |
| 2026-05-31 | `.hermes/plans/z-rule-exclusive-default-closure-spec.md` |
| 2026-05-31 | `.hermes/plans/z-rule-pass-audit.md` |
| 2026-05-31 | `.hermes/plans/z-rule-pass-current-compatibility-preview.md` |

Do not delete these; archive them as historical planning inputs.

### Active reference updates

Update current active references to the new archive locations:

- `README.md`
  - Replace root folder descriptions for `architectureAudit/`, `archive/`, `archive-2026-05-29/`, and `backups/` with the new consolidated archive/backups state.
- `.gitignore`
  - Remove or update stale `archive-2026-05-29/...` ignore entries.
- `docs/ingest/README.md`
  - If it mentions `archive-2026-05-29`, update to `archive/2026-05-29` or a generic archived ingest-material note.
- `docs/ingest/pass-1/schema-and-ingest-process-report.md`
  - Update active prose references from `archive-2026-05-29/...` to `archive/2026-05-29/...`.
- Any non-archived active references found by the validation grep below.

Do not rewrite historical prose inside the moved archive payload solely to erase old paths unless it appears in an active current guidance file.

## Companion-file impact check

- Workbook/source-data changes: not applicable; no writes to `stingray_master.xlsx`.
- Generated contracts / `form-app/data.js`: not applicable; no generator or runtime artifact changes.
- Runtime tests/customer behavior: not applicable; this pass is file organization only.
- Docs/specs: update required. README, `.gitignore`, ingest docs, moved spec paths, and this spec closure must be updated.
- Gate reminders/profile/Codex guidance: inspected-no-change expected unless active grep finds current references to old archive roots.
- Archive references: update active references; historical references inside archived payload may remain historical if not current guidance.
- Ignored local files: delete ignored `backups/`, `.DS_Store`, and stale Excel lock clutter.

## Constraints repeated back

- Spec-first: no moves/deletes until approved.
- Consolidate archive roots into `archive/`; do not create another dated root archive folder.
- Do not delete tracked historical reports/specs unless they are ignored local clutter; move them into archive locations.
- No workbook writes, no generated artifact edits, no runtime code changes, no tests/code changes except docs reference updates if needed.
- Do not stage ignored backup files or stale lock files; remove them locally only.
- Preserve `archive/stingray_archive.xlsx` because README and validators refer to it as extracted historical workbook evidence.
- Include this spec in the implementation diff and mark it completed before final handoff.

## Risks and non-goals

Risks:

- Large `git mv` operations can leave broken historical links. Mitigation: update active references and run grep for old root paths outside the moved archive payload.
- Deleting local ignored `backups/` removes local recovery snapshots. Mitigation: this is only after explicit approval; tracked workbook/archive files stay intact.
- Some May `.hermes/plans` might still be useful context. Mitigation: archive, do not delete.

Non-goals:

- No implementation of old specs.
- No deletion of `archive/stingray_archive.xlsx`.
- No flattening of all historical archive content into one huge directory; preserve useful subfolders under `archive/2026-05-29/` while removing recursive `archive/` / `archived/` nesting.
- No workbook/package validation unless a workbook file is unexpectedly touched.

## Validation plan

After approval:

1. Preflight status:

```sh
git status --short --branch --ignored -- architectureAudit archive archive-2026-05-29 backups docs .hermes/plans
```

2. Move files with `git mv` / remove ignored clutter with `rm`, then verify old root folders are gone or empty:

```sh
test ! -d architectureAudit
test ! -d archive-2026-05-29
test ! -d docs/audit-cleanup
test ! -d docs/hermes-plans
test ! -d backups
```

3. Verify active `.hermes/plans` no longer has May-or-earlier tracked plan files:

```sh
for f in $(find .hermes/plans -maxdepth 1 -name '*.md' -print); do
  ts=$(git log -1 --format=%cs -- "$f" 2>/dev/null || true)
  case "$ts" in 2026-05-*|2026-04-*|2026-03-*|2026-02-*|2026-01-*) echo "$ts $f";; esac
done
```

Expected: no output, except this spec if its own date/status creates a different classification issue.

4. Verify no active references to old root archive paths remain outside archived payloads:

```sh
git grep -n "archive-2026-05-29\|architectureAudit/" -- ':!archive/**' ':!docs/archive/**' ':!.hermes/plans/root-archive-folder-cleanout-spec.md' ':!*.xlsx'
```

Expected: no current-guidance matches. Historical matches under `archive/**`, `docs/archive/**`, and this completed spec are acceptable.

5. Verify tracked diff is docs/archive/file organization only:

```sh
git diff --name-status -- .hermes/plans docs README.md .gitignore architectureAudit archive archive-2026-05-29
```

6. Docs-only whitespace check:

```sh
git diff --check -- .hermes/plans/root-archive-folder-cleanout-spec.md README.md .gitignore docs/ingest/pass-1/schema-and-ingest-process-report.md
```

7. Final status:

```sh
git status --short --branch --ignored -- architectureAudit archive archive-2026-05-29 backups docs .hermes/plans
```

No Node/Python runtime gates are planned because the pass does not touch workbook data, generators, runtime code, tests, or generated artifacts.

## Completion record

Implemented on 2026-06-27 after approval.

Actual root archive changes:

- Moved `architectureAudit/2026-06-09-python-parser-architecture-audit.md` to `archive/2026-06-09/architecture-audit/2026-06-09-python-parser-architecture-audit.md` and removed the root `architectureAudit/` folder.
- Moved tracked `archive-2026-05-29/**` content under `archive/2026-05-29/`, normalizing the recursive `archive/` / `archived/` nesting into:
  - `archive/2026-05-29/architecture-audit/`
  - `archive/2026-05-29/docs/`
  - `archive/2026-05-29/form-output/inspection/`
  - `archive/2026-05-29/reference-sheets/`
  - `archive/2026-05-29/skills/`
  - `archive/2026-05-29/spec-review/`
- Kept `archive/stingray_archive.xlsx` in place.
- Removed the old root `archive-2026-05-29/` folder after moving tracked content and clearing ignored clutter.

Actual docs/plan changes:

- Moved stale Z06 docs specs from `docs/hermes-plans/` to `docs/archive/completed-specs/`:
  - `z06-runtime-preview-contract-spec.md`
  - `z06-full-runtime-promotion-spec.md`
- Removed empty `docs/audit-cleanup/` and `docs/hermes-plans/` folders.
- Moved 19 May-or-earlier `.hermes/plans/*.md` files to `docs/archive/old-plans/2026-05/`.
- Updated `README.md`, `.gitignore`, and `docs/ingest/pass-1/schema-and-ingest-process-report.md` active references to the consolidated archive paths.
- Updated this spec to completed status with this completion record.

Ignored local cleanup:

- Deleted ignored local `backups/` folder contents/folder.
- Deleted ignored `.DS_Store` files and stale Excel lock clutter under old archive/docs paths.

Validation results:

- Preflight `git status --short --branch --ignored -- architectureAudit archive archive-2026-05-29 backups docs .hermes/plans`: only this new spec was untracked plus the ignored archive/docs/backups clutter targeted by this pass.
- Directory absence check passed for `architectureAudit`, `archive-2026-05-29`, `docs/audit-cleanup`, `docs/hermes-plans`, and `backups`.
- Active `.hermes/plans` May-or-earlier worktree plan scan: no output.
- Active-reference grep for `archive-2026-05-29` / `architectureAudit/` outside `archive/**`, `docs/archive/**`, this completed spec, and workbooks: no output.
- Current authored-file whitespace check (`git diff --check -- .hermes/plans/root-archive-folder-cleanout-spec.md README.md .gitignore docs/ingest/pass-1/schema-and-ingest-process-report.md` and staged equivalent): pass. The moved historical archive payload was not normalized for pre-existing trailing whitespace.

What stayed unchanged:

- No workbook/source-data changes.
- No generated runtime contracts, `form-app/data.js`, runtime code, tests, dealer endpoint, payload shape, or Turnstile behavior changed.
- `archive/stingray_archive.xlsx` stayed in place.
- Historical path mentions inside archived payloads were left as historical prose.

Residual risks / follow-up:

- Some historical links inside archived content still point to old paths by design; active current-guidance references were updated.
- No obvious next cleanup pass is implied by this file-organization pass. A future pass should only target remaining old June `.hermes/plans` or archive payload pruning if current repo evidence shows they are no longer useful.

## Historical approval prompt

Original approval wording requested: "Approved — run the root archive/old-plan cleanup as scoped." Sean approved the spec.
