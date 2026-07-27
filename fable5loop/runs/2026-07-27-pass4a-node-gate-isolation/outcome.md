# Outcome rubric — Pass 4 Stage A, first slice: node gate output isolation

Written before any edit.

Run: `2026-07-27-pass4a-node-gate-isolation`
Spec: `docs/superpowers/specs/2026-07-23-validation-single-lane-active-surface-cleanup.md` §Pass 4 Stage A
Scope: the five node files that invoke `scripts/generate_form.py` without
`--output-root` and therefore rewrite tracked runtime contracts —
`grand-sport-contract-preview`, `grand-sport-draft-data`, `z06-contract-preview`,
`z06-form-data-draft`, `z06-interior-accessory-cleanup` — plus the two stale
`sec_perf_support_001` assertions those first two files carry.

This is the last known source of tracked-artifact churn from the gate set. Pass 3
requirement 9 removed the registry churn; this removes the runtime-contract churn.

Not in scope this slice — Stage A is not complete when this run closes, and none
of the following is delivered:

- the Stage A test rewrites: discovery CLI, model-generation route,
  runtime-contract builder, promotion metadata, schema-validation metadata,
  `workbook-schema-standardization`, and the `stingray-generator-stability` /
  `z06-runtime-promotion` splits;
- moving the unique runtime assertions out of the four preview/draft files and
  reclassifying or deleting them as optional diagnostics — this run keeps all
  four as they are, only isolating their output;
- repointing `z06-interior-accessory-cleanup` at current runtime-contract data
  instead of the draft artifact — it still reads the draft;
- the full README gate-matrix rewrite and the `docs/route-map.md` rewrite;
- `editor_ops.py`'s stale post-write reminder commands;
- the pinned-doc updates (`docs/superpowers/specs/2026-07-22-reliable-workbook-database-workflow.md`
  and the §9.3 `UPDATE_CURRENT_GUIDANCE` docstrings);
- the Stage A exit criteria: the bound-inventory re-run and the exact Stage B
  `git rm` list for separate approval.

## Boundaries

- No workbook write. `stingray_master.xlsx` SHA-256 identical at start and end.
- Nothing published. Every tracked file under `form-output/` and `form-app/`
  byte-identical at start and end.
- No generator, runtime, or product behavior change. Tests and docs only.

## Criteria

C1 **The churn is proven present before it is fixed.** Each of the five files is
run at the pre-change HEAD and the exact tracked path it dirties is recorded. A
claim that these gates churn is not inherited from `STATE.md`; it is re-measured.

C2 **All five files generate into a temporary `--output-root`** and none of them
writes any tracked file. Measured by hashing every tracked file under
`form-output/` and `form-app/` around each run, not by `git status` alone.

C3 **The isolation is asserted by the tests themselves, and that assertion can
fail.** A build with `--output-root` removed must fail the gate on the boundary
assertion — not merely leave a dirty worktree that a human notices later. Proven
by removing the flag from a copy and observing the failure message name the file.

C4 **The boundary helper is not vacuous.** A helper that returns an empty digest
map, or that never compares, would let all five gates pass while proving nothing.
At least one test must observe the assertion firing for modified, added, and
removed artifacts.

C5 **Every retargeted expectation is traced to the workbook cell that owns it
before it is changed.** `sec_perf_support_001` does not exist in `section_master`;
the successor id, step key, section name, and every display order touched must be
read from the workbook and from a fresh generation, and must agree. No expectation
is edited to match whatever the generator currently emits.

C6 **The removed section is pinned as removed.** After retargeting, a test asserts
`sec_perf_support_001` is absent, so its silent return is a failure rather than a
no-op.

C7 **No assertion is lost.** Every assertion in the five files is preserved,
strengthened, or explicitly replaced; the pre-change `form-app/data.js`-only
mutation check is superseded by the wider tracked-surface check, not dropped.

C8 **Gates at or above baseline.** All node gates and the Python suite run; any
failure is shown to be pre-existing at HEAD with evidence.
