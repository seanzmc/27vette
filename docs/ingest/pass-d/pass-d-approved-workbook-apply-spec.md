# Pass D — Approved workbook apply CLI

Status: Implemented 2026-07-08 for CLI/tests/docs and real-run dry-run evidence. Pass D.1 has landed, but live workbook `--write` remains blocked until the approved `pass-c-1` plan is rebuilt as `pass-c-2`, the rebuilt dry-run proves bool hygiene and deployment-continuity diagnostics, and Sean explicitly approves the rebuilt write command. Reasoning level for Sean/Codex: high.

## 0. Diagnosis and current evidence

Historical diagnosis before Pass D.1 review: Pass C.2 closed the then-known real-data dry-run blocker and this spec built the missing Pass D apply entrypoint. Pass D.1 later superseded the live-write readiness conclusion for run `20260707-193441-ea9e4c`; that run is diagnostic evidence only until the Pass C plan is rebuilt as `pass-c-2` and re-approved.

Current evidence inspected:

- `docs/ingest/ingest-wizard-end-to-end-completion-spec.md` Pass D section: requires a dry-run-default `scripts/ingest_wizard_apply.py --run <run-id> [--write]`, `plan_approved` refusal, fingerprint refusal, `save_workbook_safely()`, `apply-report.json`, and on-disk verification.
- `fable5loop/runs/2026-07-08-pass-c2-real-data-dry-run-closure/verifier-report.md`: C.2 verified run `20260707-193441-ea9e4c` as dry-run clean and approved.
- Run artifact probe for `form-output/ingest-wizard/20260707-193441-ea9e4c`:
  - `session.state = plan_approved`
  - `plan-approval.json` exists, approved by `Hermes Agent` at `2026-07-08T14:39:45`
  - `plan.valid = true`
  - stage 1 = 52 ops; stage 2 = 5,719 ops
  - `blockingGaps = 0`, `gaps = 0`, uncovered approved decisions = 0
  - `dryRun.ok = true`, `stage2.ok = true`, stage2 errors = 0, schemaErrors = 0
  - stage2 warnings = 41 expected scaffold/reference warnings
  - workbook fingerprint captured in the plan: sha256 `03e8c9671185f238dde7f4bc8e7003da0f74d842d9cc2f76126f938cbb7b54d6`, mtimeNs `1783533702592245069`
- `scripts/apply_workbook_ops.py`: existing dry-run-default CLI over `editor_ops.apply_batch`, but it applies a generic exported ops file and knows nothing about ingest run approval, plan fingerprints, or apply reports.
- `scripts/corvette_form_generator/editor_ops.py:794-862`: `apply_batch()` already owns workbook op validation, Excel-lock refusal, stale mtime refusal, schema validation, save through `save_workbook_safely()`, backup path, and workbook edit logging.
- `scripts/corvette_form_generator/workbook.py:112-150`: `save_workbook_safely()` refuses Excel lock files, refuses mtime drift, validates a temp workbook package, guards bool-like storage migrations, writes a timestamped backup, and atomically replaces the workbook.
- `scripts/corvette_form_generator/ingest/wizard/session.py`: current state machine ends at `plan_approved`; decision mutation APIs can reopen a `plan_approved` run, so Pass D needs an `applied` state that locks the run after the workbook write.
- No `scripts/ingest_wizard_apply.py` or `tests/test_ingest_wizard_apply.py` exists.
- No Excel lock file was found by file search for `~$stingray_master.xlsx`.

Risk level: high. This is the first pass allowed to write `stingray_master.xlsx`. The implementation must be deterministic, dry-run-default, refusal-heavy, and backup/readback verified.

Change type: tooling/tests/docs first, then an explicitly gated workbook write. This spec approves building the apply tool after Sean approval; it does not itself approve running the live `--write`.

## 1. Source-of-truth decision

- Workbook rows become canonical only after Pass D writes them through `editor_ops.apply_batch(..., write=True)` and `save_workbook_safely()`.
- `apply-plan.json` and `plan-approval.json` are approval artifacts, not a second source of truth after apply.
- The apply CLI must not reinterpret product decisions. It applies the exact approved plan, verifies it, and records evidence.
- Generated artifacts remain outputs. Pass D does not run `generate_form.py`, `generate_registry.py`, or edit `form-output/runtime/*` / `form-app/data.js`.
- Standing constraints from `AGENTS.md` apply, especially source boundaries (§3), spec-first expectations (§4), workbook safety (§5), validation (§10), and handoff (§12).

## 2. Scope

### D.1 Build a CLI-only apply path

Create a CLI entrypoint. These examples document the implemented Pass D CLI shape; the old run id is superseded for live write by Pass D.1 and must be replaced by a rebuilt/re-approved run before any `--write`:

```sh
.venv/bin/python scripts/ingest_wizard_apply.py --run 20260707-193441-ea9e4c
.venv/bin/python scripts/ingest_wizard_apply.py --run <rebuilt-pass-c-2-run-id> --write --confirm-plan-warnings
```

Pinned decisions:

- CLI-only in this pass. No server endpoint and no UI stage-7 button. A browser write button adds risk and is not needed for the first live workbook apply.
- Dry-run by default. `--write` is required for any workbook mutation.
- `--confirm-plan-warnings` is required with `--write` if validation emits warnings. It may confirm only the warning IDs already present in the current pre-write validation; if new warning IDs appear, the write must stop and print/report them.
- The CLI prints JSON to stdout and writes run-scoped reports under `form-output/ingest-wizard/<run-id>/`.

### D.2 Add the Pass D state/methods in the wizard store

Modify `scripts/corvette_form_generator/ingest/wizard/session.py`:

- Add `STATE_APPLIED = "applied"`.
- Add a method such as `apply_approved_plan(run_id: str, *, write: bool = False, confirm_plan_warnings: bool = False) -> dict[str, Any]`.
- The method owns all run-artifact loading, approval/fingerprint refusal, combined-batch construction, dry-run/apply execution, report writing, and applied-state transition.
- After state `applied`, mutation APIs must refuse instead of reopening review state:
  - `select_models()`
  - `save_decisions()`
  - `delete_decisions()`
  - `copy_model_decisions()`
  - `mark_complete()`
  - `build_apply_plan()`
  - `approve_plan()`
- Read-only APIs may still inspect the run (`session_detail`, `plan_detail`, candidate/review views if they already support late states), but no API may alter decisions or plan artifacts after `applied`.

### D.3 Refuse unsafe or stale apply attempts

Before any dry-run or write, refuse unless all are true:

1. `session.json` exists and `session.state == "plan_approved"` for write/dry-run. If already `applied`, report the existing `apply-report.json` and refuse a second write.
2. `plan-approval.json` exists.
3. `apply-plan.json` exists and `sha256(apply-plan.json) == plan-approval.json.planSha`.
4. Source workbook export still matches the run session fingerprint through `load_session(..., verify_source=True)`.
5. Current decision state fingerprint still equals `apply-plan.json.decisionsFingerprint`.
6. Current live `stingray_master.xlsx` sha256 and mtimeNs still equal `apply-plan.json.workbookFingerprint`.
7. No Excel lock file is present for `stingray_master.xlsx`.
8. The combined apply batch validates with schema validation before any write.

Do not provide `--allow-stale` for this CLI. Stale workbook or decisions require rebuilding the plan and re-approval.

### D.4 Apply as one atomic workbook batch, not two live stages

Pass C plan artifacts have stage 1 and stage 2 for dry-run explanation, but Pass D must not write stage 1 and then risk failing stage 2.

Implementation rule:

- Build one combined batch: `stage1.items + stage2.items`, with `workbookMtimeNs` from the currently verified live workbook.
- Run `editor_ops.apply_batch(workbook, combined_batch, write=False, run_schema_validation=True)` for the Pass D dry-run.
- For `--write`, run the same combined batch through `editor_ops.apply_batch(..., write=True, source="ingest_wizard_apply:<run-id>")` only after the pre-write dry-run is green and warnings are explicitly confirmed.
- A failure before `save_workbook_safely()` must leave the workbook byte-identical.
- A failure inside `save_workbook_safely()` must rely on the existing temp-file protocol and leave the original file untouched.

### D.5 Apply report contract

Dry-run writes:

- `form-output/ingest-wizard/<run-id>/apply-dry-run-report.json`

Write mode writes:

- `form-output/ingest-wizard/<run-id>/apply-report.json`

Report schema version: `pass-d-1`.

Required fields:

```json
{
  "schemaVersion": "pass-d-1",
  "runId": "20260707-193441-ea9e4c",
  "write": false,
  "status": "validated|applied|refused|failed_verification",
  "startedAt": "...",
  "completedAt": "...",
  "planSha": "...",
  "approvedBy": "...",
  "approvedAt": "...",
  "workbookBefore": {"sha256": "...", "mtimeNs": "...", "sizeBytes": 0},
  "workbookAfter": {"sha256": "...", "mtimeNs": "...", "sizeBytes": 0},
  "opCounts": {"stage1": 52, "stage2": 5719, "combined": 5771},
  "perSheetCounts": {},
  "warnings": [],
  "confirmedWarnings": [],
  "applyResult": {},
  "backupPath": null,
  "workbookEditLogPath": null,
  "verification": {
    "sheetRowCounts": [],
    "cellExactChecks": [],
    "deletedRowChecks": [],
    "mismatches": []
  }
}
```

Rules:

- Dry-run reports have `write=false`, no backup path, and workbookBefore/workbookAfter must be identical.
- Write reports must include `backupPath` from `apply_batch()` and `workbookEditLogPath`.
- Reports must include full warning IDs and messages, not only counts.
- Reports must include the exact combined op count and per-sheet action counts from `apply-plan.json`.
- The report should be deterministic except timestamps and workbook post-write fingerprint.

### D.6 On-disk readback verification

After a successful `--write`, reload `stingray_master.xlsx` read-only and verify the saved workbook, not the in-memory workbook object.

Minimum required checks:

- Every `add` / `update` op has a row matching its key and all planned row fields cell-exact after Excel/openpyxl normalization.
- Every `delete` op key is absent from its sheet.
- Every `create_sheet` op created the sheet with the expected header row.
- Per-sheet non-empty row counts match the expected result calculated by applying the plan to the pre-apply workbook extract.
- `model_master.active` remains false for `grand_sport_x`, `zr1`, and `zr1x` after apply; promotion remains Pass F.
- `model_registry_promotion.promoted_to_runtime` remains false/inactive for those models after apply.
- No generated `form-output/runtime/*` or `form-app/data.js` change is produced by the apply script.

Any mismatch sets report status `failed_verification`, exits non-zero, and does not advance session state to `applied`. The backup path remains the rollback source.

### D.7 Live write approval boundary

This spec has two approval levels:

1. Approval to implement the CLI/tests/docs. This allows fixture workbook writes and real-run dry-runs only.
2. Separate explicit approval to run a rebuilt Pass C/D.1 plan, not the superseded `20260707-193441-ea9e4c` `pass-c-1` run:

```sh
.venv/bin/python scripts/ingest_wizard_apply.py --run <rebuilt-pass-c-2-run-id> --write --confirm-plan-warnings
```

Do not treat approval of this spec as approval for the live workbook `--write` unless Sean states that explicitly.

## 3. Exact files expected to change

Implementation files:

- Create: `scripts/ingest_wizard_apply.py`
- Modify: `scripts/corvette_form_generator/ingest/wizard/session.py`
- Create: `tests/test_ingest_wizard_apply.py`

Docs/spec files:

- Update: `docs/ingest/pass-d/pass-d-approved-workbook-apply-spec.md` after implementation with actual status, changed files, gates, residual risks, and next pass.
- Update: `docs/ingest/README.md` to point at this Pass D spec and later its implementation status.
- Update: `docs/ingest/ingest-wizard-end-to-end-completion-spec.md` only if implementation changes the Pass D contract summarized there.
- Update: `fable5loop/STATE.md` and create a run receipt if the implementation is run under the Fable loop.

Generated/workbook/runtime files:

- During implementation tests: fixture workbooks only.
- During real `--write` after separate approval: `stingray_master.xlsx` is expected to change, and `form-output/workbook-edit-log.jsonl` / run-scoped apply reports may be written.
- Not expected in this pass: `form-output/runtime/*`, `form-app/data.js`, runtime JS/CSS/HTML, dealer submission files.

## 4. Companion-file impact matrix

| Surface | Status for this spec | Required action |
|---|---|---|
| Workbook source | Applies only after separate live `--write` approval | Use `save_workbook_safely()`, verify on disk, package/schema validate |
| Generated runtime contracts / `form-app/data.js` | Not applicable | Must remain untouched in D.1/D.2/D.3; Pass E owns generation |
| Existing editor apply tests | Updated/inspected | Reuse `editor_ops.apply_batch()` behavior; keep `tests/test_editor_ops_apply.py` green |
| Ingest wizard plan tests | Inspected-no-change or updated if state constants move | Keep Pass C plan approval behavior green |
| New apply tests | Updated | Add fixture-only refusal/write/readback tests in `tests/test_ingest_wizard_apply.py` |
| Docs/index | Updated | Add this spec to `docs/ingest/README.md`; close the spec after implementation |
| Gate reminders / `27vette-gate` skill | Inspected-no-change unless command map changes | Do not edit unless implementation discovers a missing Pass D gate pattern |
| Runtime/dealer | Not applicable | No endpoint/payload/security/Turnstile changes; report preserved |
| Fable loop | Updated when run | Receipt + STATE update required for implementation closeout |

## 5. Constraints and non-goals

Spec-specific constraints:

- No live workbook `--write` during CLI implementation without separate explicit approval.
- No `--allow-stale` or equivalent bypass in `ingest_wizard_apply.py`.
- No UI apply button in this pass.
- No schema expansion to make the plan apply; the plan is already C.2 clean against canonical workbook headers.
- No generated artifact refresh and no runtime promotion.
- No cleanup of unrelated lints, stale docs, or legacy Pass 0–5 scripts.
- No branch changes, commits, pushes, or staging unless Sean asks.

Non-goals:

- Pass E scratch generation / preview gates.
- Pass F model activation/runtime promotion.
- Asset/media completion.
- Dealer-submission behavior changes or live dealer submissions.
- Re-reviewing approved decisions or changing `apply-plan.json` business content.

## 6. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Partial live apply | Use one combined `stage1 + stage2` batch and one `save_workbook_safely()` write, not two live stage writes |
| Stale approval artifacts | Check approval plan hash, decision fingerprint, source fingerprint, workbook sha256, and workbook mtime before dry-run/write |
| Warnings silently accepted | Require `--confirm-plan-warnings` for write; fail if warning IDs differ from pre-write validation |
| Workbook opened in Excel | Rely on `excel_lock_path()` / `apply_batch()` / `save_workbook_safely()` refusal; add fixture lock test |
| Apply succeeds but saved workbook differs | Reload workbook from disk and run cell/key/count verification before setting `applied` |
| Applied run can be mutated afterward | Add `applied` state and refuse decision/plan mutation APIs after apply |
| Generated/runtime drift | Do not run generators; assert `form-output/runtime/*` and `form-app/data.js` unchanged after implementation validation |
| Test fixture misses real two-stage shape | Include a fixture with `create_sheet` plus dependent add rows in the same combined batch |

## 7. Implementation tasks

1. Add `tests/test_ingest_wizard_apply.py` with RED tests for refusal cases:
   - unknown run
   - missing `plan-approval.json`
   - session not `plan_approved`
   - approval `planSha` mismatch
   - decision fingerprint mismatch after a saved decision
   - workbook sha/mtime mismatch
   - Excel lock file present
   - already `applied` refuses a second write
2. Add fixture success tests:
   - default CLI/store dry-run writes `apply-dry-run-report.json` and leaves workbook bytes unchanged
   - combined `stage1 + stage2` batch creates a sheet and writes dependent rows in one apply
   - write with unconfirmed warnings refuses
   - write with `--confirm-plan-warnings` succeeds on a fixture workbook, writes backup/log/report, reloads workbook, verifies cells/deletes/counts, and sets state `applied`
   - after `applied`, decision mutation and plan rebuild methods refuse
3. Implement `WizardSessionStore.apply_approved_plan()` and helpers in `session.py`.
4. Implement thin CLI `scripts/ingest_wizard_apply.py` around the store method.
5. Run focused gates and fix only Pass D-scoped failures.
6. Update this spec's status block and `docs/ingest/README.md` with actual implementation evidence.
7. For the real approved run, run dry-run only and report the apply command/output. Stop before live `--write` unless Sean separately approves the write.

## 8. Validation plan

Implementation validation before any live workbook write:

```sh
PYTHONPATH=scripts .venv/bin/python -m py_compile \
  scripts/ingest_wizard_apply.py \
  scripts/corvette_form_generator/ingest/wizard/session.py

.venv/bin/python -m pytest \
  tests/test_ingest_wizard_apply.py \
  tests/test_ingest_wizard_plan.py \
  tests/test_editor_ops_apply.py \
  tests/test_editor_ops_global_families.py -q

.venv/bin/python scripts/ingest_wizard_apply.py --run 20260707-193441-ea9e4c

.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
.venv/bin/python scripts/validate_fable5_loop.py
git diff --check
git status --short --branch
```

Live write validation only after separate explicit approval:

```sh
# Pre-write status and lock check.
git status --short --branch
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/ingest_wizard_apply.py --run <rebuilt-pass-c-2-run-id>

# Write only after Sean explicitly approves the rebuilt Pass C/D.1 command.
.venv/bin/python scripts/ingest_wizard_apply.py --run <rebuilt-pass-c-2-run-id> --write --confirm-plan-warnings

# Post-write gates.
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
python3 -m json.tool form-output/ingest-wizard/<rebuilt-pass-c-2-run-id>/apply-report.json >/tmp/pass-d-apply-report.pretty.json
git status --short --branch
git diff --stat -- stingray_master.xlsx form-output/workbook-edit-log.jsonl
```

Gates intentionally not included in Pass D:

- `generate_form.py` / `generate_registry.py`: Pass E/F own generated/runtime publication.
- Node runtime promotion gates: Pass F owns runtime promotion and dealer payload verification.
- Live dealer submission: prohibited as routine validation.

## 9. Rollback plan

If the live `--write` succeeds but verification or follow-up review fails:

1. Stop; do not run generators.
2. Use `backupPath` from `apply-report.json` / workbook edit log as the rollback source.
3. Restore only after Sean approves rollback.
4. Re-run package/schema validation after restore.
5. Keep the failed `apply-report.json` as evidence; do not overwrite it with a success report.

## 10. Implementation closeout — 2026-07-08

Implemented files:

- `scripts/ingest_wizard_apply.py`
- `scripts/corvette_form_generator/ingest/wizard/session.py`
- `scripts/corvette_form_generator/editor_ops.py`
- `tests/test_ingest_wizard_apply.py`
- `tests/test_editor_ops_global_families.py`

Behavior landed:

- CLI is dry-run by default and writes run-scoped JSON output.
- `WizardSessionStore.apply_approved_plan()` refuses unapproved, stale, hash-mismatched, source-mismatched, or already-applied runs.
- The apply path uses one combined `stage1 + stage2` batch through `editor_ops.apply_batch()`.
- Fixture writes exercise `save_workbook_safely()`, backup/log/report creation, on-disk readback, and `applied` state locking, including `select_models()` after verifier-found regression.
- Apply reports now use `schemaVersion: "pass-d-1"` and include `startedAt`, `completedAt`, top-level approval fields, `perSheetCounts`, and `applyResult`.
- Combined-batch validation now recognizes same-batch `model_workbook_sources` activation/registration before validating dependent model-sheet ops.
- `model_interior_scope.active` is left as workbook-text convention during editor apply so bool-storage hygiene remains intact.

Validation evidence:

- `.venv/bin/python -m pytest tests/test_ingest_wizard_apply.py tests/test_ingest_wizard_plan.py tests/test_editor_ops_global_families.py tests/test_editor_ops_apply.py -q` → `64 passed in 50.06s` after verifier-required fixes.
- `node --check visualizer/ingest-wizard/wizard.js && git diff --check` → pass.
- Real approved run dry-run only: `.venv/bin/python scripts/ingest_wizard_apply.py --run 20260707-193441-ea9e4c --workbook stingray_master.xlsx` → `schemaVersion=pass-d-1`, `ok=true`, `status=validated`, `opCount=5771`, warnings `41`, errors `0`, report `form-output/ingest-wizard/20260707-193441-ea9e4c/apply-dry-run-report.json`.
- Real dry-run report confirms `write=false`, `opCounts={stage1:52, stage2:5719, combined:5771}`, `perSheetCounts` present, `applyResult` present, workbook before/after fingerprints equal, verification mismatches `[]`.

Gates not run in this implementation checkpoint:

- Live workbook `--write` and post-write package/schema validation: not run; still requires separate explicit approval.
- Generation, registry, runtime/browser, and dealer gates: out of Pass D scope; Pass E/F own those surfaces.

## 11. Historical approval prompt — superseded by Pass D.1

Pass D's original separate live workbook write checkpoint is no longer active for run `20260707-193441-ea9e4c`.

The former command targeted run `20260707-193441-ea9e4c`; it is intentionally omitted here because that `pass-c-1` run must not be live-written.

Pass D.1 now owns the next approval question: implement bool-storage parity, the Grand Sport X `grand_sport_x` registry-key fix, action-aware coverage, deployment-continuity probing, then rebuild the plan as `pass-c-2` and seek fresh approval for the rebuilt write.
