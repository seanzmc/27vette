# Fable 5 Compounding Loop for 27vette

This directory is the repo-local operating system for Fable 5 runs on 27vette. It turns the source guidance in `Most people are using Claude Fable 5 like Sonnet 4.6 with a bigger….md` into artifacts a long-running agent can read, execute, verify, and improve.

## Start here for every Fable 5 run

1. Read this file.
2. Read `STATE.md` to resume from verified facts, general rules, open failures, lessons learned, and the last-session pointer.
3. Read `skills/27vette-fable5-compounding.md` for the procedural loop.
4. Read `outcomes/27vette-loop-outcomes.md` and choose or write the task-specific outcome rubric before editing.
5. Check `fable5-loop-contract.json` so the run knows the three tiers, four compound-stack layers, and required artifacts.
6. From the repo root, run `.venv/bin/python scripts/validate_fable5_loop.py` before and after changing loop artifacts.

## The three tiers implemented here

### Tier 1 — Capability and routing

Fable 5 is the orchestrator for large, multi-stage work: planning, delegating, checking, and distilling. It should not spend premium effort on high-volume worker tasks that a cheaper worker model or deterministic tool can do.

Routing rule:

- Fable 5: orchestration, multi-stage planning, synthesis, visual verification decisions, and distilled rule updates.
- Worker agents: bounded edits, lint/test fixes, doc updates, artifact generation, isolated investigations.
- Independent verifier: checks artifacts against a rubric without seeing the maker's reasoning.
- Fallback/escalation: safety-boundary domains or protected 27vette boundaries go to an approved fallback or human review rather than failing silently.

### Tier 2 — Orchestration primitives

Every non-trivial Fable 5 task should use an objective loop rather than open-ended prompting:

- Outcome rubric first: define the measurable done state in `outcomes/` or in the task handoff.
- Independent verifier: grader checks the artifact and emits pass/fail with evidence.
- Dynamic workflow pattern: fan-out-and-synthesize, adversarial verification, or loop-until-done as appropriate.
- Worktree safety: parallel makers get isolated branches/checkouts when edits may collide.
- Routine template: long-running or recurring improvement belongs in `routines/` before it is scheduled anywhere.

### Tier 3 — Self-improvement layer

Every run must leave the next run smarter:

- Write failures with enough detail to reproduce.
- Investigate causes before adding rules.
- Verify facts with tool output or source evidence.
- Distill only general lessons into the skill.
- Consult `STATE.md` and the skill at the start of the next run.

## 4-layer compound stack

| Layer | Purpose | Repo artifact |
|---|---|---|
| 1. Primitives | Models, subagents, worktrees, deterministic tools | `fable5-loop-contract.json` |
| 2. Orchestration | Outcomes, dynamic workflows, routines, stop conditions | `outcomes/`, `routines/` |
| 3. Memory | State and procedural memory | `STATE.md`, `skills/27vette-fable5-compounding.md` |
| 4. Self-improvement | Verification, evals, distilled rule updates | `evals/loop-contract-rubric.json`, `scripts/validate_fable5_loop.py` |

Outputs from layer 1 flow upward for verification and distillation. Confirmed lessons return to layer 3 so the next layer-1 run starts with sharper context.

## Required closeout for every Fable 5 run

Before declaring done:

1. Run the relevant 27vette validation gates for the changed surface.
2. Run `.venv/bin/python scripts/validate_fable5_loop.py` if loop artifacts changed.
3. Create or update the run receipt under `fable5loop/runs/YYYY-MM-DD-slug/`:
   - `outcome.md`,
   - `verifier-report.md`,
   - `validation-output.txt`,
   - `run.json`.
4. Update `STATE.md`:
   - verified facts with evidence,
   - general rules only when they are reusable,
   - unresolved failures with reproduction steps,
   - last-session resume pointer.
5. Update `skills/27vette-fable5-compounding.md` only for durable procedural lessons; otherwise record a `not_applicable` or `deferred` decision in `run.json`.
6. Report what changed, what did not change, validation results, gates not run, and residual risk.

## Protected 27vette boundaries

The loop does not override `AGENTS.md`. Workbook writes, generated artifacts, runtime behavior, styling, dealer submission, and ingest passes keep their normal spec/approval/validation requirements.
