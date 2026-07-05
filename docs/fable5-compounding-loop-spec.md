# Fable 5 Compounding Self-Improving Loop Spec

Date: 2026-07-05
Status: Implemented 2026-07-05. See implementation closeout.
Change class: docs/tooling only.

## Purpose

Create a repo-local operating system that lets a Fable 5 orchestration session start from durable context, execute through the three tiers described in `fable5loop/source-guidance.md`, and write verified improvements back into the same loop for future runs.

This pass does not attempt to configure Anthropic-hosted Claude Managed Agents, change Hermes configuration, or modify the customer-facing Corvette app. It creates the project artifacts Fable 5 should read, follow, validate, and update.

## Diagnosis

Root cause / current-state evidence:

- `fable5loop/source-guidance.md` contains the effectiveness guidelines: a three-tier roadmap, 4-layer compound stack, independent verifier pattern, worktree/routine orchestration, STATE.md memory progression, Skills compounding, vision verification, and safety-boundary fallback handling.
- The repo had no existing `fable5loop` system files besides the source markdown and attachments; search for `fable`, `STATE.md`, `routine`, and `compound stack` found no active project-local loop scaffold.
- `docs/roadmap_wishes.md` records Sean's need for high-leverage, guardrailed Fable 5 tasks with clear goals, guardrails, and expected outcomes to avoid quota burn.
- `AGENTS.md` requires spec-first handling for non-trivial tooling/workflow changes, source-of-truth boundaries, scoped edits, and explicit validation.
- `README.md` confirms this pass should not touch the workbook, generated artifacts, `form-app/`, or dealer submission.

Risk level: low-to-medium. Risk is process drift or future agent misuse, not runtime behavior. Mitigation is a machine-readable loop contract plus validator and tests.

## Source-of-truth decision

- Source article: `fable5loop/source-guidance.md` owns the imported Fable 5 loop guidance.
- Repo-local loop contract: `fable5loop/fable5-loop-contract.json` owns the current artifact inventory and structural requirements.
- Operational entrypoint: `fable5loop/README.md` tells Fable 5 what to read first and how to execute the loop.
- Project memory: `fable5loop/STATE.md` owns verified facts, general rules, open failures, lessons learned, and the resume pointer for future Fable 5 runs.
- Procedural memory: `fable5loop/skills/27vette-fable5-compounding.md` owns the reusable workflow for compounding 27vette work.
- Validation authority: `scripts/validate_fable5_loop.py` and `tests/test_fable5_loop_contract.py` check the loop scaffold structure.

## Expected changes

- Add `fable5loop/README.md`.
- Add `fable5loop/STATE.md`.
- Add `fable5loop/fable5-loop-contract.json`.
- Add `fable5loop/outcomes/27vette-loop-outcomes.md`.
- Add `fable5loop/routines/nightly-eval-compounding.md`.
- Add `fable5loop/skills/27vette-fable5-compounding.md`.
- Add `fable5loop/evals/loop-contract-rubric.json`.
- Add `scripts/validate_fable5_loop.py`.
- Add `tests/test_fable5_loop_contract.py`.

No workbook, generated artifact, runtime app, CSS, pricing, rule, or dealer submission file changes.

## Design

The implementation maps the article into three tiers and four layers:

1. Tier 1 — capability and routing: Fable 5 is the orchestrator for ambitious, multi-stage work; Sonnet/Opus/Haiku-style roles are documented as worker, fallback, and verifier roles rather than hard-coded execution requirements.
2. Tier 2 — orchestration primitives: every run gets an objective outcome rubric, independent verification, worktree safety, dynamic workflow patterns, and routine hooks.
3. Tier 3 — self-improvement: every completed or failed run updates state, distills verified lessons into the skill, and re-validates the loop artifacts.

The 4-layer compound stack is expressed as an explicit contract:

- Layer 1: primitives — model roles, subagents, worktrees, tools.
- Layer 2: orchestration — outcomes, dynamic workflows, routines.
- Layer 3: memory — state file and skill file.
- Layer 4: self-improvement — eval rubric, independent verifier, rule distillation, vision checks where applicable.

## Constraints

- No new dependencies; use Python stdlib only.
- No repo behavior changes outside docs/tooling.
- No workbook writes; no generated artifact edits; no `form-app/` changes.
- Dealer submission endpoint, payload, Turnstile behavior, and UX remain untouched.
- Treat high-risk safety-boundary domains as explicit fallback/escalation cases, not silent loop failures.
- Future Fable 5 runs must start by reading `fable5loop/README.md`, `fable5loop/STATE.md`, and the skill file before acting.
- Future Fable 5 runs must end by updating `STATE.md`, adding only verified/generalized lessons to the skill, and running the loop validator.

## Companion-file impact

- Workbook/data: n/a, untouched.
- Generated artifacts/registry: n/a, untouched.
- Runtime/dealer flow: n/a, untouched.
- Tests/gates: updated with loop contract validator test.
- Docs: updated with this spec and fable5loop operational docs.
- README: inspected; no change needed because this is an optional Fable 5 operating scaffold, not a primary app command surface.

## Validation plan

- Run `scripts/validate_fable5_loop.py` to verify the three tiers, four stack layers, required artifacts, state sections, skill sections, routine/outcomes markers, and eval rubric.
- Run `.venv/bin/python -m pytest tests/test_fable5_loop_contract.py -q`.
- Review `git diff --stat` / `git diff --check`.

## Non-goals

- No cloud Routine creation.
- No model/provider configuration.
- No autonomous background job scheduling.
- No app visual changes.
- No workbook edits or model promotion.
- No live dealer submission tests.

## Implementation closeout

Implemented 2026-07-05 as docs/tooling only. The scaffold gives Fable 5 a deterministic entrypoint, state file, skill, outcomes rubric, routine template, eval rubric, JSON contract, validator, and pytest coverage. Validation results are reported in the handoff for the implementing session.
