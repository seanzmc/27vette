# Task: Workbook Manager governance consolidation and velocity recovery

You are working in the `27vette` repository. Read `AGENTS.md` first and obey it.

## Context you must verify, not assume

The Workbook Manager remediation effort has produced three successive
specifications. The current one is the audit remediation spec containing the
§3 priority ledger (23 items, P1 closed, P2.5 through P3.8 open) and the §14
completion record. Two earlier specs sit at
`docs/superpowers/specs/2026-07-22-reliable-workbook-database-workflow.md` and
`docs/superpowers/specs/2026-08-21-workbook-manager-ux-recovery.md`.

The operator's stated pain, in his words: progress drags while time flies, and
this is the third spec written to get the Workbook Manager to work right and
not have massive gaps in coverage or capability. He has been working to remove
contradicting policies, redundancy, and gates that are too strict.

Treat that stated pain as a hypothesis to test, not a finding to act on.

## What this task is NOT

Do not write a fourth specification. Do not open an implementation checkpoint.
Do not close any ledger item. Do not touch application code, the registry,
the workbook, generated artifacts, or `form-app/data.js`.

## Phase 1 — Governance inventory (read only)

Enumerate every document that currently asserts authority over Workbook
Manager work: `AGENTS.md`, the audit report, the current spec, both prior
specs, `fable5loop/STATE.md`, both READMEs, the operator/user guide,
`tests/validation_catalog.json`, and anything else you find that constrains
implementer behavior.

For each, produce a table row: path, what it claims to own, what it actually
gets read for in practice (cite completion records or commit evidence), and
whether any other document makes a conflicting claim on the same subject.

Then produce a **conflict register**: every pair of statements across these
documents that cannot both be satisfied, or that are satisfied differently by
different checkpoints. Quote both sides with file and line. Rank by how often
each conflict has actually cost a decision, using the §14 completion records
as evidence.

Two conflicts are already known and must appear with your assessment of
whether they are the largest ones:

1. Checkpoint 1C's record states that full authored reversion still coalesces
   away, and in the same record states "Residual risk: none implied."
2. "Closed" is used three different ways across records 1B, 1C, and 1E: CI
   pending, merged, and PR open for review respectively. Determine which
   definition the exit gate actually requires and whether the other two
   closures are valid under it.

## Phase 2 — Cost accounting (measure, do not estimate)

For each recurring obligation the current spec imposes per checkpoint,
measure or reconstruct its real cost from the repository and the completion
records: the catalog-selected layered run, the RED proof, the real-browser
desktop and 390x844 proof, the protected-hash comparison, the nine-state drift
table, the closeout record, the companion-file inspection, and the branch/PR
delivery.

Report wall-clock or token cost per checkpoint for each, with the evidence you
derived it from. Where you cannot measure, say so and mark it unknown rather
than guessing.

Then classify each obligation:

- **Load-bearing**: name the specific defect class it has actually caught, or
  would catch, with evidence from the repository history.
- **Ceremonial**: it has never changed an outcome. A field that has read
  "none implied" in every record is a candidate.
- **Miscalibrated**: the right idea at the wrong trigger, for example run
  every checkpoint when the risk only exists on write-capability checkpoints.

Propose removals and retargets only from the ceremonial and miscalibrated
lists, each with the evidence that justifies it. Do not propose weakening
anything in the load-bearing list. Do not propose weakening any protected
boundary in §1.3, any approval gate in §13, or any mandatory stop, regardless
of cost.

## Phase 3 — Mechanical enforcement

Identify every invariant the current spec enforces by prose alone, where a
human must remember to check it. At minimum this includes: the 23-item ledger
completeness rule, the §4 finding-to-scenario traceability table, the
checkbox-to-completion-record correspondence, the residual-risk honesty rule,
and the "green comparison over two surfaces that both omit a family is not
parity" rule.

Propose the smallest set of executable checks that move these from prose to
CI. Write the checks. They must fail loudly on a seeded violation, and you
must demonstrate that by seeding one and showing the RED output before
reverting the seed.

Register any new test file in `tests/validation_catalog.json` as a purely
additive gate, and run `tests/test_catalog_change_scope.py` and
`tests/test_validation_catalog.py`. If your change would require editing
`schema`, `ci`, `serial_groups`, or an existing gate, stop and ask instead.

## Phase 4 — Structural proposal

The current spec attacks the problem as 23 discrete items. Assess whether they
are 23 independent defects or a smaller number of structural causes with 23
surfaces.

Specifically evaluate this hypothesis and tell me if it is wrong: the registry
at `scripts/corvette_form_generator/workbook_domain/registry.py` is declared
sole authority, but projection, editor, ChangeSet, writer, generated
consumers, and tests each maintain a separate representation of the family
universe and can drift apart silently. If that is accurate, a registry-derived
conformance matrix that forces an explicit classification for every
family-by-surface cell and fails on any unclassified or newly-absent cell
would subsume several ledger items and protect the closed ones from
regression.

Determine from live code how much of projection and generation already reads
from the registry versus hardcoding family lists. Report the real cost of
building that matrix. If the hypothesis is wrong, say so plainly and name the
actual structural cause you found instead.

## Phase 5 — Deliverable

Produce one document, not a specification, containing:

1. the conflict register with a proposed resolution for each conflict,
   naming which document wins and which text gets deleted;
2. the obligation cost table with proposed removals and retargets;
3. the executable checks you wrote and their RED evidence;
4. the structural finding from Phase 4 with a cost estimate;
5. a **deletion list**: the exact text to remove from the current spec and
   from `AGENTS.md`, with line references. This list must not be empty. If
   you believe nothing should be deleted, defend that with evidence;
6. a single recommended next action, with the reasoning for why it beats the
   alternatives.

Prose budget: the document must be shorter than the deletion list saves. If
your proposal makes the governance surface larger, you have failed the task.

## Constraints

- Change no behavior. This work is read-only against application code; the
  only new files are tests and the deliverable document.
- Cite file and line for every claim about the repository. Do not characterize
  code you have not opened.
- Where evidence is missing, mark it unknown. Do not fill gaps with plausible
  reconstruction.
- Do not accept the operator's framing where the repository contradicts it.
  If the gates are not actually the bottleneck, say so and name what is.
- Deliver on a task branch. Do not merge.
