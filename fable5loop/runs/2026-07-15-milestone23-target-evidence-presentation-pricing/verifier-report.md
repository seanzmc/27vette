# Independent Verification Report — Milestone 2.3 Target Evidence Reconciliation and Presentation Pricing

## Verdict

**PASS.** Milestone 2.3 may close on exact-current run `20260715-035235-12e239` and the implementation/test sentinels recorded in `proof-audit.json`.

## Criteria

1. Canonical option candidates come only from numbered Interior, Exterior, and Mechanical sheets.
2. Equipment Groups, Standard Equipment, and raw Color and Trim sheets remain excluded at profiler, API, browser, role-artifact, and candidate-artifact boundaries.
3. Standard/default J6D remains price 0 and selectable in required single-select `sec_cali_001` for Grand Sport X, ZR1, and ZR1X.
4. LT/LZ rows own exact unique-interior Seat/Suede/Stitch/Two Tone compatibility.
5. Shared interior codes bind only exact profile-compatible unique `interior_id` rows; zero-match metadata remains fail-closed.
6. No false `unresolved_relationship_identity` remains in the exact run.
7. Every compiled relationship and target-price feature is materially represented with its dependencies.
8. Producer binding, graph integrity, and deterministic recompilation hold.
9. Target pricing, defaults, model-scoped ledgers, and justified GSX price blockers remain correct.
10. Protected workbook/runtime/publication surfaces remain unchanged.
11. Documentation describes a targeted GSX/ZR1/ZR1X module and does not claim general model-agnostic support.

All criteria passed.

## Evidence inspected

- `scripts/corvette_form_generator/ingest/wizard/profiler.py`
- `scripts/corvette_form_generator/ingest/wizard/session.py`
- `scripts/corvette_form_generator/ingest/wizard/compiler.py`
- `scripts/corvette_form_generator/ingest/wizard/profile_compiler.py`
- `scripts/corvette_form_generator/ingest/wizard/relationship_compiler.py`
- `visualizer/ingest-wizard/wizard.js`
- focused profiler/session/compiler/profile/relationship tests
- `form-output/ingest-wizard/20260715-035235-12e239/`
- `proof-audit.json`, `browser-proof.json`, and `validation-output.txt`
- `docs/ingest/canonical-row-compiler-exception-queue-design.md`
- `docs/ingest/milestone-2-3-target-evidence-reconciliation-presentation-pricing-plan.md`

## Exact-current artifact findings

Run: `form-output/ingest-wizard/20260715-035235-12e239`

- Producer and authority binding reproduced canonically; authority fingerprint `d6448d316340263b7e38a8dfb4a6ef1833aa27e9518906029141c127b555a00a`.
- Two independent in-memory compiles matched each other and all retained compiler artifacts.
- Artifact graph validation passed.
- Manifest: 5,999 physical rows; 5,994 ready and 5 blocked.
- Queue: 213 unique subjects; 203 actionable and 10 non-actionable.
- Source ledger: 11,297 features = 3,970 compiled + 906 exception-open + 508 resolved non-workbook facts + 5,913 not applicable.
- Materiality: 447/447 compiled relationship features and 330/330 compiled target-price features materially represented.
- Evidence identity conflicts: zero.
- `unresolved_relationship_identity`: zero.
- Canonical option roles: Interior 1–5, Exterior 1–5, Mechanical 1–5 only.
- Forbidden-sheet option candidates: zero.

## Source-boundary and interior findings

- Profiler allowlist: `profiler.py:41-47`; non-eligible matrices forced to `exclude`: `profiler.py:113-140`.
- API Options-role rejection: `session.py:652-661`.
- Browser Options-role disabling: `wizard.js:281-290`.
- Exact profile compatibility derives from Seat, Suede, Stitch, Two Tone, and included-option metadata: `profile_compiler.py:286-332`.
- Shared-code endpoints filter to exact compatible unique IDs: `relationship_compiler.py:238-285`.
- Mixed-code regression binds only `2LT_AH2_HU6_N26`: `tests/test_ingest_wizard_relationship_compiler.py:191-226`.
- Zero compatible metadata remains a typed blocker: `tests/test_ingest_wizard_relationship_compiler.py:133-156`.
- Representative material exact IDs include `3LT_AUP_HAG`, `3LT_AUP_HVZ`, `2LT_AH2_HU6_N26_TU7`, `1LT_AE4_HTJ_N26`, and exact 36S/37S/38S stitch IDs.

## Target fact findings

- J6D compiler behavior: `compiler.py:1449-1471`.
- `section_master[sec_cali_001]`: `single_select_req`, `is_required=true`.
- `grandSport_options[opt_j6d_001]`: active, selectable, price 0.
- GSX J6D: selectable, price 0, standard on six variants, conditional default preserved.
- ZR1/ZR1X J6D: selectable, price 0, `default_selected`, standard on four variants each, section defaults preserved.
- R8E: ZR1 3,000; ZR1X 2,600; exact raw target-price dependencies retained; GSX row explicitly not applicable.
- Remaining GSX price blockers are exactly CFV, ROY, ROZ, STZ, and VPW, each justified by incompatible or other-model source scope.

## Validation Output Inspected

- Parent affected gate: 71 passed plus 7 subtests.
- Parent full ingest gate: 314 passed plus 18 subtests.
- Independent source-boundary gate: 71 passed plus 7 subtests.
- Independent profiler/API gate: 17 passed.
- Independent JavaScript syntax check: passed.
- Parent deterministic recompilation: stable.
- Independent producer reproduction and two in-memory compiles: stable.
- Browser/API lifecycle and source-role proof: passed, zero JavaScript errors.
- Protected hashes: unchanged.
- Reviewer worktree path sets and frozen sentinels: unchanged.

## Required Fixes Before Pass

None. Earlier false multi-interior blockers were corrected before this final verification by using exact LT/LZ unique-interior compatibility while preserving zero-match fail-closed behavior.

## Durable Lesson Candidates

- A shared interior code is not a directive to apply an ancillary RPO to every unique interior carrying that code. LT/LZ metadata owns the exact unique-ID subset through Seat/Suede/Stitch/Two Tone columns.
- Profile-owned compatibility may filter to exact compatible IDs, but it must emit at least one endpoint, every emitted endpoint must be compatible, and every compiled source feature must materially carry its target dependencies.
- Source-sheet scope requires enforcement at profiler, API, browser, persisted role, and candidate-artifact boundaries.
- Standard/default options in required single-select sections remain selectable when the canonical workbook/comparator contract says so.
- A targeted three-model module must not be described as generally model-agnostic.

## File Edit Statement

Both exact-current verification lanes explicitly edited no files. Pre-existing worktree changes remained untouched.

## Final disposition

PASS. The 213 retained subjects are explicit next-pass inputs rather than hidden Milestone 2.3 defects. Milestone 3 remains blocked and unapproved.
