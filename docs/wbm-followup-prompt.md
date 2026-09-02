# Task: Workbook Manager consolidation — follow-up pass

Repo: `27vette`. Read `AGENTS.md` first and obey it. Your prior deliverable is
`wbm-governance-consolidation.md` (2026-09-01, against `25c7234`). This task
corrects and completes it. Do not rewrite it. Do not open Checkpoint 2C.

Your prior work is accepted on three points and you should not relitigate them:
the C2 reversal (`test_workbook_manager_drafts.py:296`, DRAFT-02), the partial
falsification of the registry-drift hypothesis (`catalog._build_spec` import
failure on an unrouted family), and the §6 deletion list itself.

Three corrections follow, in required order. Each has an acceptance condition.
Do not proceed to the next until the current one is met.

---

## 1. Fix the CI classifier before shipping a docs-only PR

Inventory row 11 of your own document records that
`scripts/plan_ci_validation.py:540-541` routes `*.md` to `docs-only` while the
runner routes the spec path to 22 gates via `ci.path_surfaces`. You recorded
it, gave it no cost, made it no C-item, and then recommended a docs-only PR as
the next action.

Determine empirically, not by reading, whether
`py.test_workbook_manager_spec_governance` is selected on a diff that touches
only `workbook-manager/audit-spec.md` and `AGENTS.md`. Construct that exact
diff locally and run the real selection path.

Report which of these is true:

- (a) the gate is selected, and the two classifiers merely disagree on a
  label that changes no selection;
- (b) the gate is not selected, meaning the governance gate you registered
  does not guard the class of change it was written to guard;
- (c) selection depends on something else you must name.

If (b) or (c): the classifier fix is the first PR, not the deletion. Propose
the smallest change that makes governance-file diffs select the governance
gate. Editing `ci` or `path_surfaces` in `tests/validation_catalog.json`
requires approval under §13 — if your fix needs that, stop and ask before
implementing.

**Acceptance:** a demonstrated selection run over the real deletion diff,
with output, showing the gate selected. Not an argument that it should be.

---

## 2. Make the RED rule mean something

Your §3 finding: the cited REDs are existence failures (`1A:415` `404`,
`1B:505` absent selector, `1D:603` `ERR_MODULE_NOT_FOUND`) and caught 0 of 17
Codex findings. You classified the obligation miscalibrated and proposed "RED
must fail an assertion against existing code." That proposal appears in no
deletion, no spec edit, and no next action. It is the highest-value item in
your document and it shipped as a table cell.

Write the actual rule. It must be specific enough that an implementer cannot
satisfy it with a 404 or a missing import, and it must be checkable. Then:

- amend the spec text that defines RED proof (§11.2 item 1 and the per-checkpoint
  language) to that rule, as a diff, in the same style budget as §6;
- state plainly whether the rule is mechanically checkable. If it is, add the
  check to `test_workbook_manager_spec_governance.py` with a seeded RED
  failure and reverted diff, as you did for the other ten. If it is not
  mechanically checkable, say so and do not fake a check.

Then test it retroactively: for each of the 17 Codex findings, state whether
a RED under the new rule would plausibly have caught it. Give the count. If
the count is low, the rule is wrong and you should say so rather than ship it.

**Acceptance:** the rule as spec diff, the retroactive count with per-finding
reasoning, and either a passing seeded check or an explicit statement that
none is possible.

---

## 3. Characterize the ambient-binding class

6 of 17 review findings are, in your words, an action bound to an ambient
selector, table, or selection that changed underneath (#62, #68, #69×2, #60,
#70). This is the class that cost 44 min, 50 min, and 2h11m of post-review
remediation. You correctly declined to fix it inside a read-only task. You did
not characterize it, which you could have.

Produce, read-only, no application changes:

- the six findings side by side: the ambient state, the action bound to it,
  the event that invalidated the binding, and the surface;
- whether they share one mechanism or are several. Name it.
- an enumeration of unfixed instances of the same shape in current code, by
  file and line. This is the deliverable that matters — the six known ones are
  fixed; the question is how many remain;
- for each, whether §5.3's stale-response rule and §5.7's navigation-state
  rule already cover it in prose, and if so why the code diverges;
- whether the class is detectable by a test owner, a lint, a browser scenario,
  or only by review. Be honest if the answer is only by review.

Do not propose a fix. Propose the next authorized action, which under AGENTS
§4 is a stop for new UI behavior.

**Acceptance:** the instance enumeration with file and line. A mechanism
description without instances does not satisfy this.

---

## 4. Two loose ends

- `REQUIRED_SHEETS:84-96` and `KNOWN_PRESERVED_SHEETS:25-31` are recorded as
  not registry-derived and unpinned. Checkpoint 2D is the preserved-sheet
  write-capability expansion. State the cost of pinning them now versus the
  risk of entering 2D with them unpinned, and recommend one.
- Your deliverable is 11,994 B against 12,077 B deleted. Net reduction: 83
  bytes. Decide whether the findings document survives the consolidation PR
  or is folded into its description and deleted. Recommend one, with reasoning.

---

## Constraints

- Read-only against application code. New or amended files: the governance
  test, spec/`AGENTS.md` diffs, and this task's report.
- Cite file and line for every repository claim. Do not characterize code you
  have not opened.
- Mark unknowns as unknown.
- If any correction above rests on a premise the repository contradicts, say
  so and show the evidence rather than complying.
- Task branch. Do not merge.
