# Completed Plans and Deprecated Docs Cleanout Spec

Date: 2026-06-27
Status: Completed on 2026-06-27 after approval.

## Diagnosis

The repo has accumulated completed planning artifacts in active planning locations and a few deprecated/stale documentation surfaces that now duplicate archive/history.

Evidence inspected:

- `git status --short --branch`: `## main...origin/main`; tracked tree clean at spec time.
- `.hermes/plans/`: 41 tracked markdown plan/report files.
- `docs/`: 84 tracked files plus ignored `.DS_Store` clutter under `docs/`.
- Completion/status scans found these high-confidence completed `.hermes/plans` files:
  - `.hermes/plans/asset-map-sync-hardening-spec.md` — `Status: Implemented 2026-06-25`.
  - `.hermes/plans/asset-map-sync-module-setup-spec.md` — `Status: Implemented on 2026-06-26`.
  - `.hermes/plans/asset-map-sync-apply-spec.md` — `Status: Implemented on 2026-06-26`.
  - `.hermes/plans/asset-map-sync-closure-spec.md` — `Status: Implemented on 2026-06-27`.
  - `.hermes/plans/distribution-updates-2026-06-22-tldr-workbook-spec.md` — `Status: implemented / completed 2026-06-25`.
  - `.hermes/plans/z06-cbf-grand-sport-cfv-exclusive-group-spec.md` — `Status: completed / implemented 2026-06-25`.
- The first spec draft was not approved because it did not explicitly inventory/classify every older `.hermes/plans/*.md` file and did not list this cleanup spec itself in the exact change set for completion-status update.
- Several `.hermes/plans` files mention completed work but do not carry a clear top-level implemented/completed status or still read as proposed/open; those now have an explicit keep classification below instead of being handled by a vague catch-all.
- Active docs already use `docs/archive/completed-specs/` and `docs/archive/old-reports/` as historical homes, but some completed or stale docs remain in active folders:
  - `docs/audit-cleanup/pass-14-*` through `pass-20-*` are implemented/completed but still live under `docs/audit-cleanup/`.
  - `docs/hermes-plans/rule-normalization-pass3-*`, `pass4-*`, `pass7-*`, and `z06-performance-package-rule-correction-pass3-spec.md` are implemented/verified but still live under `docs/hermes-plans/`.
  - `docs/hermes-plans/script-test-inventory-keep-delete.md` still says `awaiting deletion approval`, but later current docs (`docs/audit-cleanup-overview.md`) record the one-pass writer/script retirement outcome and say no active tracked stale one-pass writer remained.
  - `docs/metadata-runtime-redundancy-6-23.md` is a dated audit/redundancy report whose follow-up sequence has progressed through Pass 20; current route-map status should own the current path, while this dated report should become historical.
- Root tracked files inspected via `git ls-files` are limited to `.gitignore`, `2027 Chevrolet Car Corvette Export_RAW.xlsx`, `AGENTS.md`, `Order-Guide_IngestPrompt.md`, `README.md`, `requirements.txt`, and `stingray_master.xlsx`. No tracked root file is a deletion candidate in this pass. `Order-Guide_IngestPrompt.md` was already rewritten around the normalized ingest contract and remains referenced by `AGENTS.md`.
- Ignored docs clutter exists:
  - `docs/.DS_Store`
  - `docs/archive/.DS_Store`
  - `docs/ingest/.DS_Store`
  - `docs/superpowers/.DS_Store` under an otherwise ignored `docs/superpowers/` directory.

Root cause: completed specs and dated reports were left in active working directories after implementation. This makes future status scans noisy and can make old approval prompts look current.

Risk level: low-medium. This is docs/file-organization only, but deleting or moving the wrong plan/spec can hide useful active context. Use conservative classification and do not touch unclear/open plans.

Change type: docs/workflow cleanup only. No workbook, generator, runtime, tests, generated artifacts, dealer submission path, or app behavior change.

## Exact files to change after approval

1. `.hermes/plans/completed-plans-and-deprecated-docs-cleanout-spec.md`
   - Keep during implementation.
   - Before final handoff, update this spec from revised spec-only to completed/implemented with completion date, actual deleted/moved files, reference updates, validation results, residual risks, and next-step guidance, per `AGENTS.md` Spec and Plan Closure.
2. The files named in the delete/move/update sections below.

## Mandatory `.hermes/plans` inventory/classification step

Before deleting any plan file, rerun the tracked-plan inventory and verify every older `.hermes/plans/*.md` still appears in this table. If a file has changed status since this spec was written, stop and update this spec/classification before proceeding.

Classification vocabulary:

- `delete as completed`: explicit top-level completed/implemented status; remove from active `.hermes/plans` after approval.
- `keep active/open`: still reads as proposed/spec/awaiting approval or has no completion evidence; leave in `.hermes/plans`.
- `keep historical input`: not a current approval target, but retained because it is evidence/input for a named active/open workstream.

| Older `.hermes/plans/*.md` file | Classification | Named workstream / reason |
|---|---|---|
| `2026-05-19_154025-pass-3-r6x-d30-runtime-cleanup.md` | keep historical input | R6X/D30 interior-component and runtime-cleanup lineage; no clear top-level completion closure in the file. |
| `2026-05-21-stingray-grand-sport-engine-cover-structure.md` | keep active/open | Engine-cover structure migration; still says not to implement until approval. |
| `asset-map-exterior-color-url-refresh.md` | keep historical input | Asset image/content triage lineage after the asset-map sync apply/closure work; no explicit completion status. |
| `asset-map-sync-apply-spec.md` | delete as completed | `Status: Implemented on 2026-06-26`. |
| `asset-map-sync-closure-spec.md` | delete as completed | `Status: Implemented on 2026-06-27`. |
| `asset-map-sync-hardening-spec.md` | delete as completed | `Status: Implemented 2026-06-25`. |
| `asset-map-sync-module-setup-spec.md` | delete as completed | `Status: Implemented on 2026-06-26`. |
| `color-override-normalization-spec.md` | keep active/open | Color-combination override / EL9 closure candidate; no completion closure. |
| `distribution-updates-2026-06-22-tldr-workbook-spec.md` | delete as completed | `Status: implemented / completed 2026-06-25`. |
| `generator-simplification-pass2-runtime-payload-trim.md` | keep active/open | Runtime payload-trim spec; no completion closure. |
| `grand-sport-z06-stripe-workbook-rule-fix.md` | keep active/open | Stripe workbook-rule fix spec; no completion closure. |
| `layered-visualizer-integration-spec.md` | keep active/open | `Status: awaiting approval`. |
| `live-deltas-into-local-spec.md` | keep historical input | Live/local divergence and merge-back lineage; no current completion closure. |
| `live-runtime-merge-readiness-no-behavior-change-spec.md` | keep historical input | Merge-readiness/no-behavior-change lineage; no explicit completion closure. |
| `r6x-interior-components-spec.md` | keep historical input | R6X interior-component pricing/source contract lineage; contains completed-contract notes but no top-level implemented closure. |
| `rule-normalization-pass1-redundant-exclusive-excludes.md` | keep active/open | Says spec for approval and no implementation has been done. |
| `rule-normalization-pass2-grouped-excludes.md` | keep active/open | Proposed spec only. |
| `rule-normalization-pass7b-failed-fix-correction.md` | keep active/open | Proposed correction pass; do not implement until approved. |
| `stingray-engine-appearance-display-order-match-grand-sport.md` | keep active/open | Stingray display-order spec; no completion closure. |
| `vehicle-setup-progressive-disclosure-spec.md` | keep active/open | Vehicle setup progressive-disclosure follow-up; no completion closure. |
| `vehicle-setup-ux-spec.md` | keep historical input | First vehicle-setup UX pass context for the progressive-disclosure follow-up; no explicit completion closure. |
| `z-exclusive-group-note-cleanup-pass-a-spec.md` | keep historical input | Z source-hygiene cleanup Pass A context for Pass B/C provenance cleanup; no completion closure. |
| `z-exterior-paint-option-sheets-spec.md` | keep active/open | Z exterior-paint option-sheet canonicalization; no completion closure. |
| `z-option-canonical-pricing-audit.md` | keep historical input | Read-only audit input for `z-option-canonical-pricing-pass-spec.md`. |
| `z-option-canonical-pricing-pass-spec.md` | keep active/open | Z canonical-pricing pass spec; no completion closure. |
| `z-option-ovs-closure-pass-spec.md` | keep historical input | Phase 1/2 option-OVS closure input for Phase 2A/2B artifacts. |
| `z-option-ovs-closure-phase-2a-report.md` | keep historical input | Dry-run report input for Phase 2B decision closure. |
| `z-option-ovs-closure-phase-2b-decision-matrix.md` | keep historical input | Decision matrix input for `z-option-ovs-closure-phase-2b-spec.md`. |
| `z-option-ovs-closure-phase-2b-spec.md` | keep active/open | Z Option/OVS Decision Closure spec; no completion closure. |
| `z-option-pricing-section-repair-spec.md` | keep historical input | Z pricing/section repair lineage feeding canonical pricing and Z readiness work; no completion closure. |
| `z-rule-exclusive-default-closure-spec.md` | keep active/open | Z rule/exclusive/default closure spec; no completion closure. |
| `z-rule-pass-audit.md` | keep historical input | Generated Z rule audit input for `z-rule-exclusive-default-closure-spec.md`. |
| `z-rule-pass-current-compatibility-preview.md` | keep historical input | Dry-run compatibility preview input for Z rule/default closure. |
| `z-runtime-provenance-guard-pass-c-spec.md` | keep active/open | Z runtime provenance guard cleanup Pass C; no completion closure. |
| `z-sht-rule-text-cleanup-pass-b-spec.md` | keep historical input | Z source-hygiene Pass B context for Pass C provenance guard; no completion closure. |
| `z-source-hygiene-audit-spec.md` | keep historical input | Read-only audit input for Z source-hygiene Pass A/B/C. |
| `z06-carbon-wheel-package-disabled-state-spec.md` | keep active/open | Z06 carbon-wheel package disabled-state spec; no completion closure. |
| `z06-cbf-grand-sport-cfv-exclusive-group-spec.md` | delete as completed | `Status: completed / implemented 2026-06-25`. |
| `z06-interior-accessory-cleanup-pass2-spec.md` | keep active/open | Z06 interior/accessory cleanup Pass 2; still says do not implement until approved. |
| `z06-package-pricing-cascade-spec.md` | keep historical input | Input referenced by `z06-runtime-rule-correction-spec.md`; no completion closure. |
| `z06-runtime-rule-correction-spec.md` | keep historical input | Pass 1 context for `z06-interior-accessory-cleanup-pass2-spec.md`; top note still says do not implement until approved, so do not delete. |

### Delete completed `.hermes/plans` files

Delete these tracked files from the active plan directory:

1. `.hermes/plans/asset-map-sync-hardening-spec.md`
2. `.hermes/plans/asset-map-sync-module-setup-spec.md`
3. `.hermes/plans/asset-map-sync-apply-spec.md`
4. `.hermes/plans/asset-map-sync-closure-spec.md`
5. `.hermes/plans/distribution-updates-2026-06-22-tldr-workbook-spec.md`
6. `.hermes/plans/z06-cbf-grand-sport-cfv-exclusive-group-spec.md`

Leave all other older `.hermes/plans/*.md` files untouched according to the inventory table above.

### Move completed docs to `docs/archive/completed-specs/`

Use `git mv` for these completed docs:

1. `docs/audit-cleanup/pass-14-stingray-gba-zyc-runtime-rule-exception-retirement-spec.md`
   -> `docs/archive/completed-specs/audit-cleanup/pass-14-stingray-gba-zyc-runtime-rule-exception-retirement-spec.md`
2. `docs/audit-cleanup/pass-15-stingray-z51-suspension-runtime-rule-exception-retirement-spec.md`
   -> `docs/archive/completed-specs/audit-cleanup/pass-15-stingray-z51-suspension-runtime-rule-exception-retirement-spec.md`
3. `docs/audit-cleanup/pass-16-variant-override-sheet-semantics-report-spec.md`
   -> `docs/archive/completed-specs/audit-cleanup/pass-16-variant-override-sheet-semantics-report-spec.md`
4. `docs/audit-cleanup/pass-16-variant-override-sheet-semantics-report.md`
   -> `docs/archive/completed-specs/audit-cleanup/pass-16-variant-override-sheet-semantics-report.md`
5. `docs/audit-cleanup/pass-17-default-selected-display-metadata-derivation-spec.md`
   -> `docs/archive/completed-specs/audit-cleanup/pass-17-default-selected-display-metadata-derivation-spec.md`
6. `docs/audit-cleanup/pass-18-uqt-single-canonical-option-source-ownership-spec.md`
   -> `docs/archive/completed-specs/audit-cleanup/pass-18-uqt-single-canonical-option-source-ownership-spec.md`
7. `docs/audit-cleanup/pass-19-global-variant-option-overrides-retirement-spec.md`
   -> `docs/archive/completed-specs/audit-cleanup/pass-19-global-variant-option-overrides-retirement-spec.md`
8. `docs/audit-cleanup/pass-20-variant-topology-clarification-spec.md`
   -> `docs/archive/completed-specs/audit-cleanup/pass-20-variant-topology-clarification-spec.md`
9. `docs/hermes-plans/rule-normalization-pass3-z06-replace-defaults.md`
   -> `docs/archive/completed-specs/rule-normalization-pass3-z06-replace-defaults.md`
10. `docs/hermes-plans/rule-normalization-pass4-price-rule-semantics.md`
    -> `docs/archive/completed-specs/rule-normalization-pass4-price-rule-semantics.md`
11. `docs/hermes-plans/rule-normalization-pass7-z06-form-fix-list.md`
    -> `docs/archive/completed-specs/rule-normalization-pass7-z06-form-fix-list.md`
12. `docs/hermes-plans/z06-performance-package-rule-correction-pass3-spec.md`
    -> `docs/archive/completed-specs/z06-performance-package-rule-correction-pass3-spec.md`

### Move dated/stale reports to `docs/archive/old-reports/`

Use `git mv` for these stale report/history docs:

1. `docs/hermes-plans/script-test-inventory-keep-delete.md`
   -> `docs/archive/old-reports/script-test-inventory-keep-delete.md`
2. `docs/metadata-runtime-redundancy-6-23.md`
   -> `docs/archive/old-reports/metadata-runtime-redundancy-6-23.md`

### Update active references

Update active references so current docs point at archived paths instead of now-moved active paths:

1. `docs/Audit-route-map.md`
   - Change Pass 14-20 references from `docs/audit-cleanup/...` to `docs/archive/completed-specs/audit-cleanup/...`.
2. Any non-archived current doc references to moved `docs/hermes-plans/...` completed specs or `docs/metadata-runtime-redundancy-6-23.md`, if a post-move search finds them.
3. Do not rewrite archived historical prose solely to erase old path references unless a moved file would otherwise point to a current active path that no longer exists and the path is used as a current instruction.

### Remove ignored docs clutter

Delete ignored local clutter under `docs/`:

- `docs/.DS_Store`
- `docs/archive/.DS_Store`
- `docs/ingest/.DS_Store`
- `docs/superpowers/.DS_Store`
- Remove empty `docs/superpowers/` if it is empty after deleting `.DS_Store`.

## Companion-file impact check

- Workbook/source-data changes: not applicable; this pass does not touch `stingray_master.xlsx` or workbook-generated sheets.
- Generated runtime contracts / `form-app/data.js`: not applicable; no source data, generator, registry, or runtime code changes.
- Runtime tests / customer behavior: not applicable; no runtime behavior changes.
- Docs/specs: update required. Move completed/stale docs to archive locations and update active route-map references.
- This cleanup spec: update required. It must be part of the implementation diff and marked completed before handoff.
- Gate reminders / profile/Codex guidance: inspected-no-change expected. `AGENTS.md` and README already describe current workflows and do not reference the completed `.hermes/plans` files targeted for deletion. If a post-move search finds active stale references, update the active doc in the same pass.
- Active planning surfaces: update by deleting only high-confidence completed `.hermes/plans` files after verifying the explicit inventory/classification table; leave active/open and named historical-input plans in place.
- Ignored local files: remove `.DS_Store` clutter under `docs/`; no tracked artifact impact.

## Constraints repeated back

- Spec-first: no deletes or moves until Sean approves this spec.
- Conservative cleanup: delete only `.hermes/plans` files with explicit completed/implemented top-level status found in the current tree.
- Inventory completeness: every older tracked `.hermes/plans/*.md` file must be explicitly classified before implementation, and any status drift must be handled by updating this spec before deleting/moving.
- Spec closure: this cleanup spec itself is an exact file to change and must be completed before final handoff.
- No workbook writes.
- No generated artifact edits.
- No runtime JS/CSS/HTML changes.
- No refactor and no new dependencies.
- Preserve active docs that define current workflow: `AGENTS.md`, `README.md`, `docs/Audit-route-map.md`, `docs/audit-cleanup-overview.md`, `docs/ingest/`, and `Order-Guide_IngestPrompt.md` stay active unless only link paths need current-reference updates.
- Do not delete the root raw GM export or `Order-Guide_IngestPrompt.md`; current evidence does not prove either is deprecated.
- Do not touch archived historical files except for the named `git mv` destinations and any minimal path fix needed for current active references.

## Risks and non-goals

Risks:

- A completed `.hermes/plans` file may still be useful as a near-term handoff. Mitigation: target only explicit implemented/completed files after the full inventory check, and rely on git history plus archived docs for durable history.
- Moving docs can leave stale path references. Mitigation: run targeted active-doc reference scans after moves and update `docs/Audit-route-map.md` at minimum.
- Dated report docs may still be useful historical context. Mitigation: move to `docs/archive/old-reports/` instead of deleting.

Non-goals:

- No implementation of any open plan.
- No workbook/source-data cleanup.
- No deletion of `docs/archive/**` historical content beyond removing ignored `.DS_Store` files.
- No broad docs rewrite.

## Validation plan

After approval and cleanup:

1. Confirm branch/status before editing:

```sh
git status --short --branch
```

2. Rerun the older-plan inventory and confirm the table in this spec still covers every tracked older `.hermes/plans/*.md` file:

```sh
git ls-files '.hermes/plans/*.md'
```

3. Delete/move only the named files above using `git rm` / `git mv` and remove ignored `.DS_Store` clutter.

4. Check that the targeted completed `.hermes/plans` files are gone and that remaining implemented/completed matches in `.hermes/plans` are only explicit keep classifications from this spec:

```sh
git ls-files .hermes/plans
git grep -n -i "Status:.*Implemented\|Status:.*completed\|implemented / completed\|completed / implemented" -- .hermes/plans ':!.hermes/plans/completed-plans-and-deprecated-docs-cleanout-spec.md'
```

5. Check active docs do not point at moved active paths:

```sh
git grep -n "docs/audit-cleanup/pass-1[4-9]\|docs/audit-cleanup/pass-20\|docs/hermes-plans/rule-normalization-pass3\|docs/hermes-plans/rule-normalization-pass4\|docs/hermes-plans/rule-normalization-pass7\|docs/hermes-plans/z06-performance-package-rule-correction-pass3\|docs/metadata-runtime-redundancy-6-23.md" -- AGENTS.md README.md docs ':!docs/archive/**'
```

Expected result: no matches, except any explicitly reviewed current-reference exception.

6. Before handoff, update `.hermes/plans/completed-plans-and-deprecated-docs-cleanout-spec.md` from spec-only to completed with actual files changed, validation results, residual risks, and next-step guidance.

7. Docs-only diff check:

```sh
git diff --check -- .hermes/plans docs
```

8. Final status review:

```sh
git status --short --branch
```

No Node/Python runtime gates are planned because this is docs/file-organization only and does not touch workbook, generator, runtime, tests, or generated artifacts.

## Completion record

Implemented on 2026-06-27 after Sean approved the revised conservative cleanup with the corrected inventory command.

Actual `.hermes/plans` changes:

- Deleted completed top-level-status plans:
  - `.hermes/plans/asset-map-sync-hardening-spec.md`
  - `.hermes/plans/asset-map-sync-module-setup-spec.md`
  - `.hermes/plans/asset-map-sync-apply-spec.md`
  - `.hermes/plans/asset-map-sync-closure-spec.md`
  - `.hermes/plans/distribution-updates-2026-06-22-tldr-workbook-spec.md`
  - `.hermes/plans/z06-cbf-grand-sport-cfv-exclusive-group-spec.md`
- Kept the 35 remaining older tracked `.hermes/plans/*.md` files according to the active/open or historical-input classification table.
- Updated this cleanup spec from revised spec-only to completed, including this completion record.

Actual docs/archive changes:

- Moved completed Pass 14-20 audit-cleanup docs from `docs/audit-cleanup/` to `docs/archive/completed-specs/audit-cleanup/`.
- Moved completed rule-normalization/Z06 performance docs from `docs/hermes-plans/` to `docs/archive/completed-specs/`.
- Moved stale dated reports to `docs/archive/old-reports/`:
  - `docs/hermes-plans/script-test-inventory-keep-delete.md`
  - `docs/metadata-runtime-redundancy-6-23.md`
- Updated `docs/Audit-route-map.md` Pass 14-20 references to the archived completed-spec paths.
- Removed ignored `.DS_Store` clutter under `docs/`, including the empty ignored `docs/superpowers/` directory.

Validation results:

- `git status --short --branch`: preflight showed `## main...origin/main` with only this new cleanup spec untracked before implementation.
- `git ls-files '.hermes/plans/*.md'`: ran before cleanup and listed 41 older tracked plan files.
- Inventory coverage probe: 41 older tracked plan files, 41 classified, no missing/extra classifications.
- Post-cleanup `git ls-files '.hermes/plans/*.md'`: targeted deleted plans were absent; 35 older tracked plans remained.
- Post-cleanup completed-status scan excluding this cleanup spec: no matches; no remaining older top-level completed-status plan files in active `.hermes/plans`.
- Active-reference scan for moved docs returned no matches outside `docs/archive/**`.
- `git diff --check -- .hermes/plans docs`: pass before this completion update; rerun after completion update before final handoff.

What stayed unchanged:

- No workbook/source-data changes.
- No generated runtime contracts, `form-app/data.js`, app runtime, tests, gates, dealer submission endpoint, payload shape, or Turnstile behavior changed.
- Open/ambiguous/historical-input `.hermes/plans` files stayed in place.
- `AGENTS.md`, `README.md`, `docs/ingest/`, and `Order-Guide_IngestPrompt.md` stayed active and unchanged.

Residual risks / follow-up:

- Some kept historical-input `.hermes/plans` files may be archive candidates later, but this pass intentionally did not archive files without clear top-level completed status.
- No obvious next cleanup pass is implied by this conservative pass. If desired, a future pass can separately decide archival policy for historical-input plans after checking whether each named active workstream still needs them.

## Historical approval prompt

Original approval wording requested: "Approved — clean completed plans and deprecated docs as scoped." Sean approved after correcting the inventory command to `git ls-files '.hermes/plans/*.md'`.
