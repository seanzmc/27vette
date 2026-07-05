# Fable 5 Compounding Loop Hardening Spec

Date: 2026-07-05
Status: Implemented 2026-07-05. See implementation closeout.
Change class: docs/tooling only

## Purpose

Polish the existing `fable5loop/` scaffold so a future reviewer can confidently infer that Fable 5 will run a compounding loop rather than merely read a folder of instructions.

This pass resolves the blockers found in the 2026-07-05 viability review:

- the documented validator command is not reliably runnable,
- validation is structural and keyword-based rather than loop-behavior-oriented,
- the scaffold has no durable proof that each run used an independent verifier,
- memory updates do not require timestamped evidence references,
- skill-improvement decisions are not recorded per run,
- repo-root discoverability is weak because `README.md` owns command surfaces but does not mention the loop.

## Diagnosis

Current-state evidence:

- `docs/fable5-compounding-loop-spec.md` defines the initial scaffold and says future runs must start from `fable5loop/README.md`, update `STATE.md`, update the skill when lessons are durable, and run the loop validator.
- `fable5loop/README.md`, `fable5loop/STATE.md`, `fable5loop/skills/27vette-fable5-compounding.md`, `fable5loop/outcomes/27vette-loop-outcomes.md`, and `fable5loop/routines/nightly-eval-compounding.md` describe the intended loop in prose.
- `fable5loop/fable5-loop-contract.json` declares the three tiers, four compound-stack layers, and required artifacts.
- `scripts/validate_fable5_loop.py` currently checks artifact presence, counts, headings, and a small set of phrases.
- `tests/test_fable5_loop_contract.py` currently proves the repository scaffold validates and catches one missing compound-stack layer.
- Direct execution of `scripts/validate_fable5_loop.py` failed with `permission denied`; `.venv/bin/python scripts/validate_fable5_loop.py` passed.
- `README.md` has no `fable5loop` pointer under the repository map or validation command surface.

Risk level: medium. The affected surface is docs/tooling only, but the purpose is operational reliability for expensive, long-running agent work. A weak implementation would create false confidence and quota burn.

## Source-of-truth decision

- Source article: `fable5loop/Most people are using Claude Fable 5 like Sonnet 4.6 with a bigger….md` remains the imported conceptual guidance.
- Loop contract: `fable5loop/fable5-loop-contract.json` owns required artifact paths, required run-record fields, and validator expectations.
- Operational entrypoint: `fable5loop/README.md` owns the per-run start and closeout protocol.
- Repo command discovery: `README.md` owns the repo-root command pointer and must mention the validator invocation.
- Run proof: new per-run receipt artifacts under `fable5loop/runs/` own evidence that a specific run had a rubric, verifier result, validation output, state update, and skill-update decision.
- Project memory: `fable5loop/STATE.md` owns timestamped verified facts, general rules, open failures, lessons learned, and last-session pointer.
- Procedural memory: `fable5loop/skills/27vette-fable5-compounding.md` owns reusable workflow lessons only.
- Validation authority: `scripts/validate_fable5_loop.py` and `tests/test_fable5_loop_contract.py` own machine-checkable confidence gates.

## Expected changes

Modify:

- `README.md`
- `fable5loop/README.md`
- `fable5loop/STATE.md`
- `fable5loop/fable5-loop-contract.json`
- `fable5loop/outcomes/27vette-loop-outcomes.md`
- `fable5loop/routines/nightly-eval-compounding.md`
- `fable5loop/skills/27vette-fable5-compounding.md`
- `fable5loop/evals/loop-contract-rubric.json`
- `scripts/validate_fable5_loop.py`
- `tests/test_fable5_loop_contract.py`

Create:

- `fable5loop/runs/README.md`
- `fable5loop/runs/run-receipt-template.json`
- `fable5loop/runs/2026-07-05-scaffold-hardening-review/run.json`
- `fable5loop/runs/2026-07-05-scaffold-hardening-review/outcome.md`
- `fable5loop/runs/2026-07-05-scaffold-hardening-review/verifier-report.md`
- `fable5loop/runs/2026-07-05-scaffold-hardening-review/validation-output.txt`

Do not change:

- `stingray_master.xlsx`
- `form-output/`
- `form-app/`
- customer-facing runtime behavior
- CSS
- pricing, rules, model promotion, or dealer submission
- provider configuration, cloud Routine configuration, or hosted scheduling

## Design

The hardening pass turns the scaffold from "instructions exist" into "each run leaves auditable proof."

### 1. Stable command surface

Use `.venv/bin/python scripts/validate_fable5_loop.py` as the canonical command everywhere. Do not rely on executable file mode.

Required doc updates:

- `README.md` gets a short Fable 5 loop subsection with the validator command.
- `fable5loop/README.md`, `fable5loop/skills/27vette-fable5-compounding.md`, and `fable5loop/routines/nightly-eval-compounding.md` replace direct script execution text with the canonical venv-python command.
- The validator output remains concise and usable in handoffs.

### 2. Run receipt contract

Every non-trivial Fable 5 run must create a run folder:

```text
fable5loop/runs/YYYY-MM-DD-slug/
  outcome.md
  verifier-report.md
  validation-output.txt
  run.json
```

`run.json` must be valid JSON with these fields:

```json
{
  "id": "2026-07-05-scaffold-hardening-review",
  "started_at": "2026-07-05T00:00:00-04:00",
  "completed_at": "2026-07-05T00:00:00-04:00",
  "objective": "Resolve Fable 5 loop scaffold viability blockers.",
  "changed_surface": "docs/tooling",
  "outcome_rubric": "fable5loop/runs/2026-07-05-scaffold-hardening-review/outcome.md",
  "verifier_report": "fable5loop/runs/2026-07-05-scaffold-hardening-review/verifier-report.md",
  "validation_output": "fable5loop/runs/2026-07-05-scaffold-hardening-review/validation-output.txt",
  "state_updates": [
    {
      "section": "Last session",
      "evidence": "fable5loop/runs/2026-07-05-scaffold-hardening-review/validation-output.txt"
    }
  ],
  "skill_update": {
    "decision": "updated",
    "evidence": "fable5loop/runs/2026-07-05-scaffold-hardening-review/verifier-report.md"
  },
  "verifier": {
    "required": true,
    "independent_context": true,
    "verdict": "pass",
    "accepted_by_human": false
  },
  "boundaries_preserved": [
    "workbook",
    "generated artifacts",
    "runtime app",
    "dealer submission"
  ]
}
```

Allowed `verifier.verdict` values: `pass`, `fail`, `blocked`.

Allowed `skill_update.decision` values: `updated`, `not_applicable`, `deferred`.

If `skill_update.decision` is `not_applicable` or `deferred`, `skill_update.evidence` must point to a file explaining why no durable skill lesson was added.

### 3. Timestamped memory rules

`fable5loop/STATE.md` must explicitly require every new bullet under `Verified facts`, `General rules`, `Open failures`, and `Lessons learned` to include:

- an ISO date or timestamp,
- an `Evidence:` reference to a file, command output, validator output, verifier report, or source path,
- no speculative facts in `Verified facts`.

The `Last session` entry must point to the latest run receipt folder.

### 4. Verifier proof

`fable5loop/outcomes/27vette-loop-outcomes.md` must require the independent verifier to write `verifier-report.md`, not only a chat response.

`verifier-report.md` must include:

- verdict,
- criteria table,
- files inspected,
- validation output inspected,
- evidence-backed required fixes,
- durable lesson candidates,
- explicit statement that the verifier did not edit files.

The validator must reject run receipts with `verifier.required: true` unless the verifier report exists and contains a verdict.

### 5. Skill-improvement proof

`fable5loop/skills/27vette-fable5-compounding.md` must require every closeout to record a skill-update decision in `run.json`.

The validator must reject a run receipt when:

- `skill_update.decision` is missing,
- `skill_update.decision` is outside the allowed values,
- `skill_update.evidence` is missing,
- the evidence file does not exist.

This avoids both failure modes: pretending a skill improved when it did not, and silently skipping skill improvement after a real lesson.

### 6. Stronger validator

`scripts/validate_fable5_loop.py` must keep stdlib-only implementation and add checks for:

- canonical validator command appears in README and fable5loop docs,
- no fable5loop docs instruct direct `scripts/validate_fable5_loop.py` execution without `.venv/bin/python`,
- `fable5loop/runs/README.md` and `run-receipt-template.json` exist,
- every run folder under `fable5loop/runs/YYYY-MM-DD-*` has `run.json`, `outcome.md`, `verifier-report.md`, and `validation-output.txt`,
- every `run.json` is valid JSON and has required fields,
- every path referenced by `outcome_rubric`, `verifier_report`, `validation_output`, `state_updates[*].evidence`, and `skill_update.evidence` exists,
- verifier verdict is one of `pass`, `fail`, `blocked`,
- passed verifier reports contain `Verdict`, `Criteria`, and `Evidence inspected`,
- `completed_at` is not earlier than `started_at`,
- `STATE.md` has timestamped evidence-bearing bullets in memory sections,
- `STATE.md` Last session references the latest run folder,
- the contract and eval rubric include the run-receipt and timestamped-memory criteria.

### 7. Tests

Expand `tests/test_fable5_loop_contract.py` to cover the new behavioral contract:

- repository scaffold validates,
- validator rejects direct-script-only documentation,
- validator rejects missing run receipt files,
- validator rejects a run receipt with no verifier report,
- validator rejects a run receipt with missing skill-update evidence,
- validator rejects a `STATE.md` verified fact without timestamp/evidence,
- validator rejects `Last session` when it does not reference the latest run folder,
- validator accepts a copied fixture with a complete receipt.

Use temporary directories for negative tests; do not mutate the real repo during tests.

## Implementation tasks

### Task 1: Command discoverability

- Update `README.md` with a short "Fable 5 Compounding Loop" subsection near validation/workflow commands.
- Update fable5loop docs to use `.venv/bin/python scripts/validate_fable5_loop.py`.
- Add a test that fails if fable5loop docs contain a direct validator invocation without the venv-python prefix.

Validation:

```sh
.venv/bin/python -m pytest tests/test_fable5_loop_contract.py -q
```

### Task 2: Run receipt artifacts

- Add `fable5loop/runs/README.md`.
- Add `fable5loop/runs/run-receipt-template.json`.
- Add the initial `2026-07-05-scaffold-hardening-review` receipt folder.
- Ensure the initial receipt records the actual validation commands and current known blocker resolution from this pass.

Validation:

```sh
.venv/bin/python scripts/validate_fable5_loop.py
```

### Task 3: Validator hardening

- Refactor `scripts/validate_fable5_loop.py` into focused helpers for:
  - JSON loading,
  - markdown heading checks,
  - command-surface checks,
  - run receipt discovery,
  - run receipt validation,
  - state memory validation,
  - rubric/contract validation.
- Keep CLI behavior unchanged: return `0` on pass, `1` with bullet issues on failure.
- Do not add dependencies.

Validation:

```sh
.venv/bin/python scripts/validate_fable5_loop.py
.venv/bin/python -m pytest tests/test_fable5_loop_contract.py -q
```

### Task 4: State and skill closeout rules

- Update `fable5loop/STATE.md` to document timestamp/evidence requirements.
- Update `fable5loop/skills/27vette-fable5-compounding.md` to require a `run.json` skill-update decision every closeout.
- Update `fable5loop/outcomes/27vette-loop-outcomes.md` to require `verifier-report.md`.
- Update `fable5loop/routines/nightly-eval-compounding.md` to write receipt artifacts before closeout.

Validation:

```sh
.venv/bin/python scripts/validate_fable5_loop.py
```

### Task 5: Contract and eval rubric alignment

- Update `fable5loop/fable5-loop-contract.json` with required run receipt artifacts, required run JSON fields, allowed verifier verdicts, allowed skill-update decisions, and memory evidence rules.
- Update `fable5loop/evals/loop-contract-rubric.json` with criteria for run receipts, timestamped evidence, verifier proof, and skill-update proof.
- Add tests that mutate these fields in a temp copy and confirm the validator rejects the broken copies.

Validation:

```sh
.venv/bin/python -m pytest tests/test_fable5_loop_contract.py -q
```

### Task 6: Final proof pass

- Run the full loop validator.
- Run the loop pytest file.
- Run diff whitespace checks.
- Update the implementation spec closeout only after the above commands pass.

Validation:

```sh
.venv/bin/python scripts/validate_fable5_loop.py
.venv/bin/python -m pytest tests/test_fable5_loop_contract.py -q
git diff --check -- README.md docs/fable5-compounding-loop-hardening-spec.md fable5loop scripts/validate_fable5_loop.py tests/test_fable5_loop_contract.py
```

## Acceptance criteria

This pass is complete only when all are true:

- Repo-root `README.md` tells a future agent where the Fable 5 loop lives and how to validate it.
- All fable5loop docs use `.venv/bin/python scripts/validate_fable5_loop.py` or a path-correct equivalent from inside `fable5loop/`.
- The validator rejects missing verifier proof, missing run receipts, missing skill-update decisions, missing timestamp/evidence memory entries, and stale `Last session` references.
- A complete run receipt exists for the hardening implementation run.
- `STATE.md` records the hardening run with timestamped evidence and a pointer to the run receipt.
- The skill records either a durable procedural lesson from the hardening pass or a receipt-backed decision that no skill change was warranted.
- Pytest covers both positive and negative cases for the hardened contract.
- No workbook, generated artifact, runtime app, CSS, pricing, rule, promotion, or dealer-submission files change.

## Companion-file impact

- Workbook/data: n/a, must remain untouched.
- Generated artifacts/registry: n/a, must remain untouched.
- Runtime/dealer flow: n/a, must remain untouched.
- Docs: update README and fable5loop operational docs.
- Tooling: update validator and tests.
- Skill/state: update only to encode durable loop closeout requirements and the hardening run evidence.

## Risks and mitigations

- Risk: The validator becomes too broad and hard to maintain. Mitigation: keep checks local to fable5loop artifacts and use explicit helper functions with targeted tests.
- Risk: Run receipts become paperwork that agents skip. Mitigation: validator fails when the latest state pointer lacks a matching receipt.
- Risk: Skill updates accumulate noise. Mitigation: require a skill-update decision and evidence; allow `not_applicable` when no durable lesson exists.
- Risk: README duplicates detailed fable5loop instructions. Mitigation: README gets only a pointer and command; detailed conduct stays in `fable5loop/`.

## Non-goals

- No hosted Routine setup.
- No provider/model configuration.
- No autonomous scheduling.
- No customer-facing app changes.
- No workbook writes.
- No generated artifact regeneration.
- No dealer submission testing.

## Validation plan

Required before approval-to-land:

```sh
.venv/bin/python scripts/validate_fable5_loop.py
.venv/bin/python -m pytest tests/test_fable5_loop_contract.py -q
git diff --check -- README.md docs/fable5-compounding-loop-hardening-spec.md fable5loop scripts/validate_fable5_loop.py tests/test_fable5_loop_contract.py
```

Report any gate not run with the reason.

## Implementation closeout

Implemented 2026-07-05 as docs/tooling only. The scaffold now has repo-root discovery, canonical validator command text, timestamped evidence rules for `STATE.md`, required run receipts, verifier-report proof, explicit skill-update decisions, stronger validator checks, and positive/negative pytest coverage. Validation evidence is recorded in `fable5loop/runs/2026-07-05-scaffold-hardening-review/validation-output.txt`.
