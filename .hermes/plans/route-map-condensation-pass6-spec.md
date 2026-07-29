# Route-Map Doc Condensation Spec (Simplification Pass 6)

> **Execution status (2026-07-29): SUPERSEDED.** Commands and compatibility-artifact paths below describe an older generator topology and are historical evidence only. Use `README.md` and Pass 4 Stage A of `docs/superpowers/specs/2026-07-23-validation-single-lane-active-surface-cleanup.md` for current commands. The underlying completed record is unchanged.

Date: 2026-07-05
Status: Completed 2026-07-05. See completion record at end.

## Diagnosis

`docs/Audit-route-map.md` (382 lines) and `docs/audit-cleanup-overview.md` (157 lines) are historical program logs: route-map passes 0-20 and overview passes A-E are all implemented, each with an archived spec under `docs/archive/completed-specs/audit-cleanup/`. Verified in the simplification audit (verifier claim 6, PASS). The still-load-bearing content is small: the current normalized route, the codebase philosophy constraints, the "do not delete as cleanup" warnings, and the named open candidates (runtime_action/body_style_scope migration, Stingray `requires_z25` contract fork, Stingray `production.py` rule-assembly vs shared `rules.py`, fallback-constant retirement).

No live references to either doc path outside completed specs, receipts, and STATE prose.

## Exact changes

1. `git mv docs/Audit-route-map.md docs/archive/completed-specs/audit-cleanup/Audit-route-map.md`.
2. `git mv docs/audit-cleanup-overview.md docs/archive/completed-specs/audit-cleanup/audit-cleanup-overview.md`.
3. Write new condensed `docs/route-map.md` (~60-80 lines): current active generation/registry route, philosophy constraints, protected do-not-"cleanup" surfaces, open candidates with their evidence anchors, pointer to the archived program logs for pass-by-pass history.

## Constraints / non-goals

Content-preserving condensation: no new claims, no dropped open candidates or warnings; history stays intact in the archived files. No code, workbook, or generated-artifact changes. Pass 6 only.

## Validation plan

1. `git grep -n "Audit-route-map\|audit-cleanup-overview"` outside archives/receipts/specs → no active references.
2. Both archived files staged as R (history preserved); `docs/route-map.md` exists.
3. Condensed doc names every open candidate from the source docs' closing sections (checked by the independent verifier against the archived originals).
4. `git diff --check`; independent verifier at closeout.

## Completion record

Implemented 2026-07-05 (staged, not committed). Both program logs archived as git renames to `docs/archive/completed-specs/audit-cleanup/`; condensed `docs/route-map.md` written (active routes, philosophy constraints, do-not-delete surfaces, five open candidates, archive pointer).

Validation results (real output):

- `git grep Audit-route-map|audit-cleanup-overview` outside archives/receipts/specs/STATE → no matches.
- Both archived files staged as R; `docs/route-map.md` present.
- Open candidates carried over: runtime_action/body_style_scope migration, Stingray `requires_z25` fork, Stingray production.py rule-assembly consolidation, fallback-constant retirement, copy allowlist residuals (verifier cross-checked against archived originals).
- `git diff --check` → clean.

Residual risks / follow-up: staged pending commit approval; none other implied.
