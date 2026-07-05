# Fable 5 Project Memory · 27vette

This file is the durable memory surface for Fable 5 work in this repo. Read it at session start; update it before walking away.

## Memory entry contract

Every new bullet under `Verified facts`, `General rules`, `Open failures`, and `Lessons learned` must include an ISO date or timestamp and an `Evidence:` reference to a source file, run receipt, validator output, verifier report, command output, or reproducible investigation note. Do not record speculative claims as verified facts. `Last session` must reference the latest `fable5loop/runs/YYYY-MM-DD-slug/` receipt folder.

## Verified facts

- 2026-07-05: The source guidance for this loop is `fable5loop/Most people are using Claude Fable 5 like Sonnet 4.6 with a bigger….md`. It defines the three tiers, the 4-layer compound stack, independent verifier pattern, 5-stage memory progression, skill compounding, vision verification, and safety-boundary fallback handling. Evidence: `fable5loop/Most people are using Claude Fable 5 like Sonnet 4.6 with a bigger….md`.
- 2026-07-05: 27vette agent/workflow boundaries are governed by `AGENTS.md`; workbook writes, generated artifacts, runtime changes, and dealer-submission changes require their normal approval and validation paths. Evidence: `AGENTS.md`.
- 2026-07-05: The loop scaffold is docs/tooling only. It does not configure cloud routines, change model providers, mutate `stingray_master.xlsx`, edit `form-output/`, edit `form-app/data.js`, or touch dealer submission. Evidence: `docs/fable5-compounding-loop-spec.md`.
- 2026-07-05: Read-only simplification audit verified: `.superpowers/brainstorm/**` state files (incl. `server.pid`) are tracked with no `.gitignore` entry; `form-output/inspection/grand-sport-rule-audit.json/.md` have no remaining writer (`build_rule_sources.py` retired; `model_generation.py:67` only existence-checks); retired `asset_map-Sync/asset_map_sync.py` stays tracked and is guarded by `tests/test_asset_map_sync.py:949-953`; all 44 `src/*.png` files are unreferenced by any tracked file; 14+ docs/plans with explicit implemented/completed status remain in active locations. Evidence: `fable5loop/runs/2026-07-05-simplification-audit/verifier-report.md`.
- 2026-07-05: Live surfaces confirmed not cleanup targets: `visualizer/ingest-wizard/` + `visualizer/workbook-editor/` (served by `ingest_wizard_server.py:28`, `workbook_editor_server.py:47`), root raw GM export (active ingest-doc references), Stingray compatibility JSON/CSV + `window.STINGRAY_FORM_DATA` alias (real consumers in app.js/data.js/production.py/registry_promotion.py/tests — retirement needs spec-first parity pass). Evidence: `fable5loop/runs/2026-07-05-simplification-audit/verifier-report.md`.
- 2026-07-05: Simplification Pass 1 implemented: `.superpowers/` fully untracked (`git ls-files .superpowers` empty), 6 brainstorm mockups archived as git renames to `docs/archive/brainstorm/2026-06-18-form-visualizer-flow/`, transient `server.pid`/`server-stopped` deleted, `.gitignore:7` now ignores `.superpowers/`. Spec: `.hermes/plans/superpowers-untrack-pass1-spec.md`. Evidence: `fable5loop/runs/2026-07-05-superpowers-untrack/verifier-report.md`.

## General rules

- 2026-07-05: Start every Fable 5 run by reading `fable5loop/README.md`, this state file, `fable5loop/skills/27vette-fable5-compounding.md`, and the task-relevant 27vette guidance. Evidence: `fable5loop/README.md`.
- 2026-07-05: Use Fable 5 as the orchestrator for multi-stage work; delegate bounded worker tasks and use an independent verifier for pass/fail judgments. Evidence: `fable5loop/skills/27vette-fable5-compounding.md`.
- 2026-07-05: Define the outcome rubric before editing. If the done state is not gradable, pause and write the rubric first. Evidence: `fable5loop/outcomes/27vette-loop-outcomes.md`.
- 2026-07-05: Treat STATE updates as evidence-based memory. Do not record guesses as verified facts; put unresolved items under Open failures with reproduction or investigation notes. Evidence: `fable5loop/STATE.md`.
- 2026-07-05: Distill only durable, reusable procedural lessons into the skill. Do not add one-off task progress, stale artifact IDs, or temporary TODOs to the skill. Evidence: `fable5loop/skills/27vette-fable5-compounding.md`.
- 2026-07-05: For UI/visual tasks, include screenshot or vision verification when practical and record what was compared. Evidence: `fable5loop/Most people are using Claude Fable 5 like Sonnet 4.6 with a bigger….md`.
- 2026-07-05: Treat safety-boundary or protected 27vette-boundary blocks as escalation/fallback events, not silent failures. Evidence: `fable5loop/Most people are using Claude Fable 5 like Sonnet 4.6 with a bigger….md`.
- 2026-07-05: Every non-trivial Fable 5 run must leave a run receipt with outcome, verifier report, validation output, and skill-update decision before closeout. Evidence: `fable5loop/runs/README.md`.

## Open failures

- 2026-07-05: None recorded yet. Evidence: `fable5loop/runs/2026-07-05-scaffold-hardening-review/verifier-report.md`.

## Lessons learned

- 2026-07-05: A compounding Fable 5 run needs repo-local artifacts, not just chat context: entrypoint, state, skill, outcomes, routine template, eval rubric, validator, and receipt evidence. Evidence: `fable5loop/runs/2026-07-05-scaffold-hardening-review/run.json`.

## Last session

2026-07-05 (pass 1): Implemented simplification-audit Pass 1 per spec `.hermes/plans/superpowers-untrack-pass1-spec.md`; verifier passed 9/9. Changes staged, not committed. Receipt: `fable5loop/runs/2026-07-05-superpowers-untrack/`. Audit roadmap receipt: `fable5loop/runs/2026-07-05-simplification-audit/`. Next action: commit Pass 1 when Sean approves, then pick roadmap pass 2 (orphan rule-audit artifacts, needs small generator-touching spec) or pass 4 (docs archival). Note: worktrees may lack a local `.venv`; run the loop validator with the main repo venv (`/Users/seandm/Projects/27vette/.venv/bin/python`).
