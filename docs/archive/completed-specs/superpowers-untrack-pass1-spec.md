# Superpowers Session-State Untrack Spec (Simplification Pass 1)

Date: 2026-07-05
Status: Completed 2026-07-05. See completion record at end.

## Diagnosis

`.superpowers/` is a Superpowers-plugin brainstorm working directory that was committed to git. Tracked contents (`git ls-files .superpowers`, 8 files):

- 6 design mockups under `.superpowers/brainstorm/67120-1781809310/content/`:
  `form-step-layout-directions.html`, `form-step-layout-hybrid-v2.html`, `setup-to-visualizer-transition-v5.html`, `trim-to-visualizer-transition-v6.html`, `visualizer-first-flow-v3.html`, `visualizer-flow-map-v4.html` (committed 2026-06-18, `52fd9cf`).
- 2 transient process-state files under `.../state/`: `server.pid` (6 bytes), `server-stopped` — session artifacts, never source.

`.gitignore` has no `.superpowers` entry, so future brainstorm sessions would re-stage state files.

Reference scan: no tracked file references any `.superpowers/...` path (`git grep`, excluding this pass's own artifacts). `.hermes/plans/layered-visualizer-integration-spec.md` (awaiting approval) does not reference the mockups by path, but the mockups are visualizer-flow design explorations relevant to that open workstream — archive, do not delete.

Evidence source: `fable5loop/runs/2026-07-05-simplification-audit/verifier-report.md` claim 1 (verifier PASS).

Risk level: low. Docs/file-organization only. Change class: repo hygiene; no workbook, generator, runtime, styling, test, or dealer-submission surface.

Preflight worktree note: `fable5loop/STATE.md` (modified) and `fable5loop/runs/2026-07-05-simplification-audit/` (untracked) are prior-run loop artifacts already present before this pass; they are not part of this change set and stay as-is.

## Exact files to change

Archived (git mv, tracked history preserved):

| From | To |
|---|---|
| `.superpowers/brainstorm/67120-1781809310/content/form-step-layout-directions.html` | `docs/archive/brainstorm/2026-06-18-form-visualizer-flow/form-step-layout-directions.html` |
| `.superpowers/brainstorm/67120-1781809310/content/form-step-layout-hybrid-v2.html` | `docs/archive/brainstorm/2026-06-18-form-visualizer-flow/form-step-layout-hybrid-v2.html` |
| `.superpowers/brainstorm/67120-1781809310/content/setup-to-visualizer-transition-v5.html` | `docs/archive/brainstorm/2026-06-18-form-visualizer-flow/setup-to-visualizer-transition-v5.html` |
| `.superpowers/brainstorm/67120-1781809310/content/trim-to-visualizer-transition-v6.html` | `docs/archive/brainstorm/2026-06-18-form-visualizer-flow/trim-to-visualizer-transition-v6.html` |
| `.superpowers/brainstorm/67120-1781809310/content/visualizer-first-flow-v3.html` | `docs/archive/brainstorm/2026-06-18-form-visualizer-flow/visualizer-first-flow-v3.html` |
| `.superpowers/brainstorm/67120-1781809310/content/visualizer-flow-map-v4.html` | `docs/archive/brainstorm/2026-06-18-form-visualizer-flow/visualizer-flow-map-v4.html` |

Deleted (git rm, transient state — recoverable from git history if ever needed):

- `.superpowers/brainstorm/67120-1781809310/state/server-stopped`
- `.superpowers/brainstorm/67120-1781809310/state/server.pid`

Ignore rule (`.gitignore`): add `.superpowers/` beside the other tool-workspace ignores (`.pytest_cache/`, `.playwright-mcp/`). Whole-directory rule, not `state/`-only: brainstorm content is session scratch by default; anything worth keeping gets an explicit archive move like this one.

This spec file: completion record appended before handoff.

## Source-of-truth decision

Tooling/session workspace — not workbook, generator, artifact, runtime, or styling. Archived mockups become historical docs under `docs/archive/`.

## Companion-file impact

- Workbook / generated artifacts / runtime / styling / tests: n/a — untouched.
- `.gitignore`: updated (rule addition).
- README.md: inspected-no-change — does not mention `.superpowers`.
- Open plan `layered-visualizer-integration-spec.md`: inspected-no-change — no path references to the mockups.
- Loop artifacts (`fable5loop/`): updated at closeout per loop contract (receipt + STATE), separate from this change set.

## Constraints / non-goals

- Pass 1 only. No other roadmap passes (rule-audit artifacts, asset_map-Sync, docs archival, src/, route-map docs).
- No workbook writes, no generated-artifact edits, no runtime/test changes, no new dependencies.
- Archive mockups rather than delete (open visualizer workstream may want them).

## Validation plan

1. `git ls-files .superpowers` → empty.
2. `git check-ignore -v .superpowers/anything` → matches new `.gitignore:.superpowers/` rule.
3. `git status --porcelain` → only: renamed mockups, deleted state files, modified `.gitignore`, this spec, and pre-existing loop artifacts.
4. `git grep -n '\.superpowers/' -- ':!docs/archive' ':!fable5loop' ':!.hermes/plans/superpowers-untrack-pass1-spec.md'` → no active references.
5. `git diff --check` → clean.
6. Independent verifier grades the result from artifacts only.
7. `scripts/validate_fable5_loop.py` (main-repo venv) after receipt/STATE writes.

Node/pytest gates not run: no code, workbook, or generated surface changed.

## Completion record

Implemented 2026-07-05 per approved scope ("Implement Pass 1 only from the simplification audit").

Actual changes (staged, not committed):

- 6 mockups moved via `git mv` from `.superpowers/brainstorm/67120-1781809310/content/` to `docs/archive/brainstorm/2026-06-18-form-visualizer-flow/` (R status, history preserved).
- `git rm` on `state/server-stopped` and `state/server.pid`; empty local `.superpowers/` dirs removed.
- `.gitignore:7` adds `.superpowers/` beside `.pytest_cache/` / `.playwright-mcp/`.
- This spec written before edits; updated to completed.

Validation results (real output):

- Gate 1 `git ls-files .superpowers` → empty.
- Gate 2 `git check-ignore -v .superpowers/...` → `.gitignore:7:.superpowers/`.
- Gate 3 `git status --porcelain` → exactly the named changes plus pre-existing loop artifacts.
- Gate 4 reference grep → only the `.gitignore` rule line itself.
- Gate 5 `git diff --check` / `--cached --check` → clean.
- Independent verifier: PASS 9/9 (`fable5loop/runs/2026-07-05-superpowers-untrack/verifier-report.md`), including protected-surface and scope-discipline checks.
- Loop gate: `scripts/validate_fable5_loop.py` output in `fable5loop/runs/2026-07-05-superpowers-untrack/validation-output.txt`.

What stayed unchanged: workbook, `form-output/`, `form-app/`, `scripts/`, `tests/`, `visualizer/`, dealer submission; all other simplification-audit pass targets still tracked (verifier criterion 9).

Residual risks / follow-up: changes staged but uncommitted — commit when approved. Remaining roadmap passes (2-7) each need their own spec; none implied by this pass.
