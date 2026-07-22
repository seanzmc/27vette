# Ingest Separation, Three-Model Integration, and Editor Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the overlapping ingest/editor write paths with one five-function ingest module, one shared `workbook-changeset-1` service, a verified Grand Sport X/ZR1/ZR1X workbook integration, and one final editor UI.

**Architecture:** Ingest ends after emitting an immutable ChangeSet. A shared workbook-domain package owns registry metadata, strict ChangeSet parsing, preview, approval, guarded apply, rollback, and receipts. The existing editor and then the Workbook Manager consume that service; SQLite remains a disposable projection and journal, never canonical product data.

**Tech Stack:** Python 3, `openpyxl`, standard-library JSON/hash/dataclasses/SQLite/HTTP, existing Preact workbook editor, existing React/Vite Workbook Manager, pytest/unittest, Node test runner. Add no dependencies.

## Global Constraints

- `stingray_master.xlsx` remains the canonical product/business source.
- Ingest owns only raw intake, profiling/target selection, canonical compilation, typed exception resolution, and ChangeSet emission.
- Ingest may not approve or perform workbook writes, generation, publication, promotion, deployment, or dealer submission.
- Use one schema named `workbook-changeset-1`; do not retain `pass-c-3` as a parallel production write contract.
- Preserve compiler keys, values, actions, stable IDs, evidence bindings, and semantic signatures.
- Add no dependency, workbook schema, generated contract, dealer change, or deployment-path change without separate approval.
- Keep historical Pass B/C/D.2 artifacts GET-only; current sessions may not enter or mutate their states.
- Keep the existing editor available until the Manager passes complete writable-surface parity.
- Every temporary workbook, database, receipt, and audit log must be isolated from tracked product/audit files.
- Phase 1 performs no live canonical-workbook write.
- Phase 2 stops for explicit approval before the one live workbook write.
- Runtime publication/promotion remains separate from workbook integration.
- Update the approved owner spec in place; do not create per-task milestone/spec documents.

## Planned File Ownership

New shared package:

- `scripts/corvette_form_generator/workbook_domain/registry.py` — sole declarative workbook family/key/type/enum/reference registry.
- `scripts/corvette_form_generator/workbook_domain/changeset.py` — `workbook-changeset-1` normalization, parsing, fingerprints, and editor-batch conversion.
- `scripts/corvette_form_generator/workbook_domain/service.py` — preview, approval, guarded apply, rollback, and receipt creation.
- `scripts/corvette_form_generator/workbook_domain/deployment_proof.py` — temporary generation/registry/runtime-contract proof relocated out of ingest.
- `scripts/corvette_form_generator/workbook_domain/__init__.py` — narrow public exports only.
- `scripts/apply_workbook_changeset.py` — shared operator CLI; preview by default, explicit approval artifact, explicit `--write` consumption.

Ingest:

- `scripts/corvette_form_generator/ingest/wizard/changeset_emitter.py` — pure canonical-manifest-to-ChangeSet projection.
- `scripts/corvette_form_generator/ingest/wizard/session.py` — current intake/profile/compile/exception/emit orchestration only after extraction.
- `scripts/corvette_form_generator/ingest/wizard/legacy_reader.py` — GET-only historical artifact reader.
- `scripts/ingest_wizard_server.py` and `visualizer/ingest-wizard/` — only the five current functions plus read-only historical display.

Editor transition:

- `scripts/corvette_form_generator/editor_ops.py` — compatibility adapter over shared registry plus the existing operation engine until all consumers move.
- `scripts/workbook_editor_server.py` and `visualizer/workbook-editor/editor.js` — existing fallback editor; remove normal Ingest Review navigation.
- `workbook-manager/backend/app/` — disposable projection, ChangeSet journal, and shared-service API adapters.
- `workbook-manager/frontend/src/` — final editor UI over the shared API.

Tests:

- `tests/test_workbook_domain_registry.py`
- `tests/test_workbook_changeset.py`
- `tests/test_workbook_changeset_service.py`
- `tests/test_ingest_wizard_changeset.py`
- Existing ingest/editor/Manager tests named in each task.

## Operator Summary

- Tasks 1–7 establish the shared contract and separate ingest. They never write the canonical workbook.
- Task 8 rebuilds and proves one exact-current three-model ChangeSet, then stops for Sean's approval.
- Task 9 is the single approved workbook integration and regeneration task.
- Tasks 10–13 convert the Manager into the one editor and retire the fallback only after parity.
- No task publishes or promotes the three models publicly; that remains a separate decision after workbook integration.

---

## Phase 1 — Separate ingest and establish the shared path

### Task 1: Freeze one authoritative Milestone 3 snapshot

**Files:**
- Modify: `docs/ingest/milestone-3-canonical-plan-deployment-proof-implementation-plan.md`
- Modify: `docs/ingest/ingest-separation-model-integration-editor-consolidation-spec.md`
- Inspect only: `form-output/ingest-wizard/20260717-091317-470292/`

**Interfaces:**
- Consumes: current manifest, plan, dry-run, compile report, exception resolutions, and protected-surface hashes.
- Produces: one documented set of authoritative hashes/counts used by Task 5's equivalence test.

- [x] **Step 1: Capture exact-current artifact hashes and counts without writing files**

```sh
shasum -a 256 \
  form-output/ingest-wizard/20260717-091317-470292/canonical-row-manifest.json \
  form-output/ingest-wizard/20260717-091317-470292/apply-plan.json \
  form-output/ingest-wizard/20260717-091317-470292/apply-plan-dryrun.json \
  form-output/ingest-wizard/20260717-091317-470292/compile-report.json \
  form-output/ingest-wizard/20260717-091317-470292/exception-resolutions.json
jq '[.stage1.items[],.stage2.items[]] | {total:length, creates:(map(select(.action=="create_sheet"))|length), rows:(map(select(.action!="create_sheet"))|length)}' \
  form-output/ingest-wizard/20260717-091317-470292/apply-plan.json
jq '.coverage | {manifestRows:(.manifestRows|length), noops:(.noops|length), uncovered:(.uncoveredManifestRows|length)}' \
  form-output/ingest-wizard/20260717-091317-470292/apply-plan.json
```

Expected current characterization before independent reconciliation: manifest SHA `b3e32dea5afeaf10eb6296d82283ff844403a80da1f3659b6ad20d5d0409926f`; 3,719 plan operations, including nine sheet creations; 6,408 covered manifest rows; 2,699 no-op receipts; zero uncovered rows.

- [x] **Step 2: Run the exact-current independent verification lane**

```sh
PYTHONPATH=scripts .venv/bin/python -m pytest \
  tests/test_ingest_wizard_plan.py \
  tests/test_ingest_wizard_apply.py \
  tests/test_ingest_wizard_compiler_session.py \
  tests/test_ingest_wizard_exception_flow.py -q
```

Expected: PASS. If the verifier reproduces different artifacts or any protected hash changes, stop under the approved spec instead of updating documentation.

- [x] **Step 3: Reconcile the closeout text to the verified snapshot**

Update the Milestone 3 completion record with the verified file hashes, operation counts, no-op counts, named nine sheet creations, and separately identified inactive Grand Sport X promotion scaffold. Remove the superseded 3,692/3,643/2,725 claims rather than keeping both snapshots.

- [x] **Step 4: Record the frozen snapshot binding in the owner spec**

Replace the characterization paragraph with the exact verified hashes/counts and state that Task 5 must reproduce the same semantic projection from the manifest.

- [x] **Step 5: Validate and commit the reconciliation**

```sh
git diff --check
git diff -- docs/ingest/milestone-3-canonical-plan-deployment-proof-implementation-plan.md \
  docs/ingest/ingest-separation-model-integration-editor-consolidation-spec.md
git add docs/ingest/milestone-3-canonical-plan-deployment-proof-implementation-plan.md \
  docs/ingest/ingest-separation-model-integration-editor-consolidation-spec.md
git commit -m "docs: freeze authoritative ingest projection evidence"
```

Expected: one docs-only commit; no run artifact or product file staged.

**Task 1 verification receipt (2026-07-18):** Completed in commit `ecd4381`
and independently reverified against the committed artifact set. The focused
lane passed `121 tests and 4 subtests`; all five protected artifact hashes,
projection counts, nine GSX sheet creations, inactive `grand_sport_x`
promotion scaffold, and readback proof matched the frozen documentation. The
verification left the worktree clean and did not modify product files or ingest
run artifacts.

### Task 2: Extract the shared workbook registry without semantic changes

**Files:**
- Create: `scripts/corvette_form_generator/workbook_domain/__init__.py`
- Create: `scripts/corvette_form_generator/workbook_domain/registry.py`
- Modify: `scripts/corvette_form_generator/editor_ops.py:41-299`
- Create: `tests/test_workbook_domain_registry.py`
- Modify: `tests/test_editor_ops_meta.py`
- Modify: `tests/test_editor_ops_global_families.py`

**Interfaces:**
- Consumes: current `SOURCE_ROLE_FAMILIES`, `EDITOR_SHEET_META`, `GLOBAL_SHEET_FAMILIES`, and live `model_workbook_sources` rows.
- Produces: `family_spec(name)`, `registered_sheet_families(extract)`, and compatibility aliases imported by `editor_ops`.

- [x] **Step 1: Write failing registry identity and resolution tests**

```python
from corvette_form_generator import editor_ops
from corvette_form_generator.workbook_domain.registry import (
    EDITOR_SHEET_META,
    GLOBAL_SHEET_FAMILIES,
    SOURCE_ROLE_FAMILIES,
    family_spec,
    registered_sheet_families,
)


def test_editor_ops_uses_shared_registry_objects():
    assert editor_ops.EDITOR_SHEET_META is EDITOR_SHEET_META
    assert editor_ops.GLOBAL_SHEET_FAMILIES is GLOBAL_SHEET_FAMILIES
    assert editor_ops.SOURCE_ROLE_FAMILIES is SOURCE_ROLE_FAMILIES


def test_registered_sheet_families_uses_live_workbook_rows():
    extract = {
        "sheets": {
            "model_workbook_sources": {
                "rows": [{
                    "model_key": "demo",
                    "source_role": "source_option_sheet",
                    "sheet_name": "demo_options",
                    "active": True,
                }]
            }
        }
    }
    assert registered_sheet_families(extract)["demo_options"] == "options"
    assert family_spec("options")["key"] == ("option_id",)
```

- [x] **Step 2: Run the tests and verify the module is absent**

```sh
PYTHONPATH=scripts .venv/bin/python -m pytest tests/test_workbook_domain_registry.py -q
```

Expected: FAIL with `ModuleNotFoundError: corvette_form_generator.workbook_domain`.

- [x] **Step 3: Move the exact registry literals and add narrow accessors**

`registry.py` must contain the current literal definitions unchanged plus:

```python
def family_spec(name: str) -> dict:
    try:
        return EDITOR_SHEET_META[name]
    except KeyError as exc:
        raise KeyError(f"Unknown workbook family: {name}") from exc


def registered_sheet_families(extract: dict) -> dict[str, str]:
    result = dict(GLOBAL_SHEET_FAMILIES)
    rows = extract.get("sheets", {}).get("model_workbook_sources", {}).get("rows", [])
    for row in rows:
        if not workbook_truthy(row.get("active")):
            continue
        family = SOURCE_ROLE_FAMILIES.get(str(row.get("source_role") or ""))
        sheet = str(row.get("sheet_name") or "")
        if family and sheet:
            result[sheet] = family
    return result
```

Import `workbook_truthy` from `corvette_form_generator.workbook`. In `editor_ops.py`, delete the three literal blocks and import/re-export the exact objects from `workbook_domain.registry`.

- [x] **Step 4: Run registry and existing editor metadata tests**

```sh
PYTHONPATH=scripts .venv/bin/python -m pytest \
  tests/test_workbook_domain_registry.py \
  tests/test_editor_ops_meta.py \
  tests/test_editor_ops_global_families.py \
  tests/test_editor_ops_apply.py -q
```

Expected: PASS with no changed validation behavior.

- [x] **Step 5: Commit the semantic-preserving extraction**

```sh
git diff --check
git add scripts/corvette_form_generator/workbook_domain \
  scripts/corvette_form_generator/editor_ops.py \
  tests/test_workbook_domain_registry.py \
  tests/test_editor_ops_meta.py \
  tests/test_editor_ops_global_families.py
git commit -m "refactor: centralize workbook domain registry"
```

**Task 2 verification receipt (2026-07-18):** Completed in commit
`1400b08` and independently reverified. The three registry literals moved
byte-identical from `editor_ops.py:40-294` to
`workbook_domain/registry.py:14-268` (diff-verified, comments and
`tuple(SOURCE_ROLE_FAMILIES)` self-reference preserved); `editor_ops`
compatibility aliases are object-identical to the shared registry objects.
Gates passed: the Task 2 lane (`test_workbook_domain_registry.py`,
`test_editor_ops_meta.py`, `test_editor_ops_global_families.py`,
`test_editor_ops_apply.py`) at 82 tests and 7 subtests, plus the consumer
lane (`test_ingest_wizard_plan.py`, `test_ingest_wizard_compiler_session.py`)
at 39 tests and 4 subtests; `py_compile` clean on the two new modules,
`editor_ops.py`, and all five alias consumers. Spec-compliance review
passed and code-quality review returned APPROVED with four deferred minor
notes (explicit-`None` extract intermediates, `model_sheet_registry`
merge-semantics alignment for the future adapter consumer, staged-API
skip-path coverage, and `family_spec` returning the live meta dict
consistent with existing `editor_ops` usage). The three
`test_editor_lints.py` `RealWorkbook*` failures were proven pre-existing at
parent `66f9d43` and are unrelated to this extraction. Worktree clean; no
product files, generated artifacts, or ingest run artifacts modified.

### Task 3: Implement the immutable `workbook-changeset-1` contract

**Files:**
- Create: `scripts/corvette_form_generator/workbook_domain/changeset.py`
- Modify: `scripts/corvette_form_generator/workbook_domain/__init__.py`
- Create: `tests/test_workbook_changeset.py`

**Interfaces:**
- Consumes: workbook registry and extracted workbook rows.
- Produces: `ChangeSetError`, `canonical_json(value)`, `changeset_fingerprint(payload)`, `parse_changeset(payload)`, and `changeset_to_editor_batch(changeset, extract)`.

- [x] **Step 1: Write failing fingerprint, parsing, delta, and stale-before tests**

```python
import copy
import pytest

from corvette_form_generator.workbook_domain.changeset import (
    ChangeSetError,
    changeset_fingerprint,
    changeset_to_editor_batch,
    parse_changeset,
)


def sample_changeset():
    payload = {
        "schemaVersion": "workbook-changeset-1",
        "source": {"kind": "editor", "runId": "test-run"},
        "targets": ["stingray"],
        "workbook": {"sha256": "a" * 64, "mtimeNs": "123"},
        "sheetCreates": [],
        "rowChanges": [{
            "action": "update",
            "sheet": "stingray_options",
            "family": "options",
            "key": {"option_id": "opt_1"},
            "fields": {"price": {"before": 100, "after": 200}},
            "provenance": [{"kind": "editor", "id": "field:price"}],
        }],
        "noops": [],
        "warningAcknowledgementsRequested": [],
        "bindings": {},
    }
    payload["semanticFingerprint"] = changeset_fingerprint(payload)
    payload["changeSetId"] = payload["semanticFingerprint"][:24]
    return payload


def test_fingerprint_ignores_mapping_order_but_not_semantics():
    payload = sample_changeset()
    reordered = copy.deepcopy(payload)
    reordered["source"] = {"runId": "test-run", "kind": "editor"}
    assert changeset_fingerprint(reordered) == payload["semanticFingerprint"]
    reordered["rowChanges"][0]["fields"]["price"]["after"] = 201
    assert changeset_fingerprint(reordered) != payload["semanticFingerprint"]


def test_update_emits_only_changed_fields_and_checks_before_value():
    parsed = parse_changeset(sample_changeset())
    extract = {"sheets": {"stingray_options": {
        "headers": ["option_id", "price"],
        "rows": [{"option_id": "opt_1", "price": 100}],
    }}}
    batch = changeset_to_editor_batch(parsed, extract)
    assert batch["items"] == [{
        "action": "update",
        "sheet": "stingray_options",
        "key": {"option_id": "opt_1"},
        "row": {"price": 200},
    }]
    extract["sheets"]["stingray_options"]["rows"][0]["price"] = 150
    with pytest.raises(ChangeSetError, match="before value"):
        changeset_to_editor_batch(parsed, extract)
```

- [x] **Step 2: Run the new tests and verify the contract is absent**

```sh
PYTHONPATH=scripts .venv/bin/python -m pytest tests/test_workbook_changeset.py -q
```

Expected: FAIL importing `workbook_domain.changeset`.

- [x] **Step 3: Implement strict normalization and parsing**

Use canonical JSON `json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)` and SHA-256. Exclude only `changeSetId` and `semanticFingerprint` from the fingerprint input. Reject unknown top-level and row-change fields, duplicate row keys, unchanged field pairs, missing provenance, invalid actions, family/key disagreement, non-64-character workbook SHA, non-string mtime, unsorted/duplicate targets, and a stored fingerprint/ID mismatch.

The public return of `parse_changeset()` is a deep-copied normalized dict; it never mutates caller data.

- [x] **Step 4: Implement field-delta conversion**

`changeset_to_editor_batch()` must:

- convert each `sheetCreates` entry to `create_sheet`;
- require updates/deletes to match exact current before values;
- require adds to be absent by canonical key;
- emit update `row` values only for changed fields;
- emit full after values for adds and no `row` for deletes;
- set `workbookMtimeNs` from the immutable ChangeSet; and
- set `workbookSha256` from the immutable ChangeSet; and
- exclude no-op receipts from mutations.

- [x] **Step 5: Run contract and editor validation tests**

```sh
PYTHONPATH=scripts .venv/bin/python -m pytest \
  tests/test_workbook_changeset.py \
  tests/test_editor_ops_apply.py -q
```

Expected: PASS.

- [x] **Step 6: Commit the contract**

```sh
git diff --check
git add scripts/corvette_form_generator/workbook_domain/changeset.py \
  scripts/corvette_form_generator/workbook_domain/__init__.py \
  tests/test_workbook_changeset.py
git commit -m "feat: add shared workbook changeset contract"
```

**Task 3 verification receipt (2026-07-18):** Completed in commits
`d55430a` (contract) and `920cac4` (review hardening), independently
reverified. The implementer subagent timed out after authoring the test
file first (TDD order preserved per file timestamps); the Step 2 red-run
output was not preserved, but the module was verifiably absent when the
tests were written. One implementer-authored test asserted conversion
reorders adds before updates; the plan mandates only sheetCreates-first
and the immutable fingerprint binds rowChanges order, so the test was
corrected to assert order preservation — a correction independently
validated by the spec-compliance review. Gates passed:
`test_workbook_changeset.py` + `test_editor_ops_apply.py` +
`test_workbook_domain_registry.py` at 93 tests and 7 subtests (33 contract
tests covering every Step 3 rejection rule and Step 4 conversion rule);
`py_compile` clean on both package modules. Spec-compliance review passed;
code-quality review returned APPROVED with two Important issues
(conversion output aliasing the parsed changeset; undocumented
before-value storage-typing contract), both fixed in `920cac4` with
regression tests and confirmed APPROVED on focused re-review. Deferred
minor notes: provenance-entry index in one error message, loose `match=`
regexes, and O(n) row lookup acceptable for the one-off apply pass. A later
independent review proved the `True == 1` edge violated the exact-before
contract; commit `7995a90` now rejects Boolean/integer type mismatches while
preserving the existing integer/float numeric equivalence, with a regression
test. Worktree clean; no product files, generated artifacts, or ingest run
artifacts modified.

### Task 4: Add the shared service and close writer race/rollback failures

**Files:**
- Create: `scripts/corvette_form_generator/workbook_domain/service.py`
- Modify: `scripts/corvette_form_generator/workbook_domain/__init__.py`
- Modify: `scripts/corvette_form_generator/editor_ops.py:1460-1640`
- Modify: `scripts/corvette_form_generator/workbook.py:98-148`
- Create: `scripts/apply_workbook_changeset.py`
- Create: `tests/test_workbook_changeset_service.py`
- Modify: `tests/test_editor_ops_apply.py:916-1055`

**Interfaces:**
- Consumes: parsed ChangeSet and current workbook path.
- Produces: `preview_changeset()`, `approve_changeset()`, `apply_changeset()`, `restore_workbook_backup()`, and CLI preview/approval/write receipts.

- [x] **Step 1: Write failing drift and rollback fault-injection tests**

```python
def test_live_apply_rechecks_original_reviewed_fingerprint(tmp_path, monkeypatch):
    workbook = make_workbook(tmp_path)
    changeset = make_valid_changeset(workbook)
    preview = preview_changeset(workbook, changeset)
    approval = approve_changeset(changeset, preview, actor="Sean", warning_ids=[])

    original_prepare = editor_ops._prepare_batch
    def mutate_after_prepare(extract, batch):
        result = original_prepare(extract, batch)
        workbook.touch()
        return result
    monkeypatch.setattr(editor_ops, "_prepare_batch", mutate_after_prepare)

    receipt = apply_changeset(workbook, changeset, preview, approval)
    assert receipt["status"] == "stale_before_save"
    assert receipt["workbookState"] == "untouched"


def test_failed_live_readback_restores_and_verifies_backup(tmp_path, monkeypatch):
    workbook = make_workbook(tmp_path)
    before = workbook.read_bytes()
    changeset = make_valid_changeset(workbook)
    preview = preview_changeset(workbook, changeset)
    approval = approve_changeset(changeset, preview, actor="Sean", warning_ids=[])
    monkeypatch.setattr(editor_ops, "verify_prepared_workbook", lambda *_: {
        "ok": False, "preparedChecked": 0, "preparedCount": 1, "errors": ["forced"],
    })

    receipt = apply_changeset(workbook, changeset, preview, approval)
    assert receipt["status"] == "apply_verification_failed_rolled_back"
    assert receipt["workbookState"] == "restored"
    assert workbook.read_bytes() == before
```

Use existing workbook fixture helpers from `tests/test_editor_ops_apply.py`; do not introduce a new workbook generator dependency.

Define the helpers in `tests/test_workbook_changeset_service.py`:

```python
import hashlib
from test_editor_ops_apply import build_ops_fixture
from corvette_form_generator.workbook_domain.changeset import changeset_fingerprint


def make_workbook(tmp_path):
    path = tmp_path / "fixture.xlsx"
    build_ops_fixture().save(path)
    return path


def make_valid_changeset(path):
    payload = {
        "schemaVersion": "workbook-changeset-1",
        "source": {"kind": "editor", "runId": "service-test"},
        "targets": ["stingray"],
        "workbook": {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "mtimeNs": str(path.stat().st_mtime_ns),
        },
        "sheetCreates": [],
        "rowChanges": [{
            "action": "update",
            "sheet": "stingray_options",
            "family": "options",
            "key": {"option_id": "opt_one_001"},
            "fields": {"price": {"before": 100, "after": 101}},
            "provenance": [{"kind": "editor", "id": "service-test:price"}],
        }],
        "noops": [],
        "warningAcknowledgementsRequested": [],
        "bindings": {},
    }
    payload["semanticFingerprint"] = changeset_fingerprint(payload)
    payload["changeSetId"] = payload["semanticFingerprint"][:24]
    return payload
```

- [x] **Step 2: Run the fault tests and verify they fail against current behavior**

```sh
PYTHONPATH=scripts .venv/bin/python -m pytest \
  tests/test_workbook_changeset_service.py \
  tests/test_editor_ops_apply.py::ApplyBatchTest::test_tampered_live_save_exposes_apply_verification_failed -q
```

Expected: FAIL because the service is absent and the current writer does not restore.

- [x] **Step 3: Preserve the reviewed workbook identity through save**

At `apply_batch()` entry, capture both expected mtime and SHA-256 from the batch/ChangeSet. Immediately before loading for live mutation and again immediately before `save_workbook_safely()`, require the same mtime and SHA. Pass the original reviewed mtime—not a newly accepted mtime—to the safe saver.

Return `stale_before_save` with `workbookState: "untouched"` when either comparison differs.

- [x] **Step 4: Add verified restoration**

Implement in `workbook.py`:

```python
def restore_workbook_backup(path: Path, backup_path: Path) -> None:
    path = Path(path)
    backup_path = Path(backup_path)
    assert_valid_workbook_package(backup_path)
    with tempfile.NamedTemporaryFile(
        prefix=f"{path.stem}-restore-", suffix=path.suffix,
        delete=False, dir=path.parent,
    ) as handle:
        restore_tmp = Path(handle.name)
    try:
        shutil.copy2(backup_path, restore_tmp)
        assert_valid_workbook_package(restore_tmp)
        check = load_workbook(restore_tmp, read_only=True, data_only=True)
        check.close()
        restore_tmp.replace(path)
    finally:
        restore_tmp.unlink(missing_ok=True)
```

On failed live readback, call this helper, reopen/rehash the restored workbook, and return `apply_verification_failed_rolled_back` only after restoration matches the backup. If restoration cannot be verified, raise a hard `workbook_restore_failed` result containing both paths and do not claim the workbook is safe.

- [x] **Step 5: Implement immutable preview, approval, and receipt binding**

`preview_changeset()` calls `parse_changeset()`, verifies workbook SHA/mtime, converts to an editor batch, and calls `apply_batch(write=False)`. `approve_changeset()` requires a passing preview and returns `workbook-change-approval-1`. `apply_changeset()` requires exact ChangeSet/preview/approval/workbook fingerprints and calls `apply_batch(write=True)` once. All three return JSON-serializable dicts.

- [x] **Step 6: Add the shared CLI**

The CLI contract is:

```sh
.venv/bin/python scripts/apply_workbook_changeset.py change-set.json --workbook stingray_master.xlsx --preview-out preview.json
.venv/bin/python scripts/apply_workbook_changeset.py change-set.json --workbook stingray_master.xlsx --approve Sean --preview preview.json --approval-out approval.json
.venv/bin/python scripts/apply_workbook_changeset.py change-set.json --workbook stingray_master.xlsx --write --preview preview.json --approval approval.json --receipt-out receipt.json
```

Preview is the default. `--approve` never writes. `--write` refuses without both exact bound files. Output paths are explicit; tests use temporary directories and never the tracked edit log.

- [x] **Step 7: Run the service, editor, package, and schema gates**

```sh
PYTHONPATH=scripts .venv/bin/python -m pytest \
  tests/test_workbook_changeset.py \
  tests/test_workbook_changeset_service.py \
  tests/test_editor_ops_apply.py -q
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Expected: tests PASS; workbook validators report zero issues/errors/warnings.

- [x] **Step 8: Commit the shared service and writer repair**

```sh
git diff --check
git add scripts/corvette_form_generator/workbook_domain \
  scripts/corvette_form_generator/editor_ops.py \
  scripts/corvette_form_generator/workbook.py \
  scripts/apply_workbook_changeset.py \
  tests/test_workbook_changeset_service.py \
  tests/test_editor_ops_apply.py
git commit -m "fix: unify guarded workbook changeset writes"
```

**Task 4 verification receipt (2026-07-18):** Completed in commits
`3c9eaf8` (service, writer repair, rollback, CLI, tests) and `befa0af`
(restore-failure and post-approval drift coverage), independently
reverified. Two implementer subagents timed out at the delegation cap:
the Part A subagent wrote nothing, so Part A (writer identity rechecks,
verified rollback, service, fault/service tests) was implemented directly
by the orchestrator; the Part B subagent landed the CLI, its tests, and
the plan commit before timing out at its report step. Plan-text
adaptations, all validated by the spec-compliance review:
`make_valid_changeset` uses fixture price `0` (the plan's `100` predates
the fixture); the plan's unconditional verify mock was made stateful (pass
scratch, fail live) because an unconditional mock fails the scratch
readback first and never reaches the live-rollback path; receipt schemas
named `workbook-change-preview-1` / `workbook-change-approval-1` /
`workbook-change-receipt-1` (spec §5.3); the tamper test kept its
plan-referenced name while asserting the rolled-back contract. Gates
passed: the Task 4 lane (`test_workbook_changeset.py`,
`test_workbook_changeset_service.py`, `test_editor_ops_apply.py`) at 108
tests and 7 subtests; the registry/meta/global-families lane at 24; the
ingest consumer lane at 39 tests and 4 subtests; `py_compile` clean on all
touched modules; `validate_workbook_package.py` and
`validate_workbook_schema.py` on `stingray_master.xlsx` both valid with
zero issues/errors/warnings. Spec-compliance review passed; two
code-quality review subagents timed out at the delegation cap, so the
orchestrator performed the quality pass directly (TOCTOU: the pre-save
recheck plus the saver's own mtime guard close the load→save window;
rollback claims `restored` only after SHA-256 equality with the backup;
fault tests verified isolated from neighboring guards; service return
paths JSON-serializable; CLI refusal and exit-code paths verified in
code) and converted the two targeted coverage gaps into the `befa0af`
tests (`workbook_restore_failed` branch; post-approval drift refusal). A later
independent review proved preview and approval fingerprint fields were compared
but not recomputed from artifact contents; commit `7995a90` now verifies both
fingerprints at approval/write boundaries and adds three tamper regressions.
Deferred minor: CLI JSON parse errors surface as tracebacks rather than clean
operator errors. No live workbook write occurred; no product files, generated
artifacts, or ingest run artifacts modified.

### Task 5: Emit an equivalent ChangeSet from the canonical compiler

**Files:**
- Create: `scripts/corvette_form_generator/ingest/wizard/changeset_emitter.py`
- Modify: `scripts/corvette_form_generator/ingest/wizard/session.py:3055-3244`
- Inspect only: `scripts/corvette_form_generator/ingest/wizard/plan_builder.py` — equivalence-test import; left untouched here so Task 6 deletes the legacy projection in the only production touch
- Create: `tests/test_ingest_wizard_changeset.py`
- Modify: `tests/test_ingest_wizard_plan.py:683-1165`
- Modify: `tests/test_ingest_wizard_compiler_session.py`

**Interfaces:**
- Consumes: exact-current canonical manifest, compile report, selection, compiler bindings, exception queue/resolutions, comparator evidence, workbook path, and shared registry.
- Produces: `emit_manifest_changeset(...) -> dict`, `WizardSessionStore.emit_changeset(run_id) -> dict`, and a new `changeset_emitted` session state stored in `session.json` and surfaced through `list_sessions()`.

- [x] **Step 1: Write failing exact projection and coverage tests**

```python
def test_manifest_emitter_covers_every_row_without_changing_semantics(current_run):
    changeset = emit_manifest_changeset(**current_run.inputs)
    covered = {
        item["provenance"][0]["manifestRef"]
        for item in changeset["rowChanges"] + changeset["noops"]
    }
    expected = {row["manifestRef"] for row in current_run.manifest["rows"]}
    assert covered == expected
    assert len(covered) == len(current_run.manifest["rows"])
    assert changeset["bindings"]["canonicalManifestSha"] == current_run.manifest_sha


def test_emitter_is_byte_deterministic_and_does_not_read_legacy_decisions(current_run):
    first = emit_manifest_changeset(**current_run.inputs)
    current_run.decisions_file.write_text('{"decisions":[{"id":"legacy"}]}')
    second = emit_manifest_changeset(**current_run.inputs)
    assert canonical_json(first) == canonical_json(second)
```

Add negative tests for target drift, stale bindings, unknown family/header, non-ready row, duplicate manifest reference, unbound projection migration, and any unsupported non-manifest mutation.

- [x] **Step 2: Run the new test and verify the emitter is absent**

```sh
PYTHONPATH=scripts .venv/bin/python -m pytest tests/test_ingest_wizard_changeset.py -q
```

Expected: FAIL importing `changeset_emitter`.

- [x] **Step 3: Port the mechanical projection into the emitter**

Port the currently verified `build_manifest_plan()` validation/projection logic into `emit_manifest_changeset()`. The legacy function itself stays in `plan_builder.py` for the Step 5 test-local equivalence comparison and is deleted in Task 6. Replace only the output assembly:

- `create_sheet` becomes `sheetCreates`;
- add/update/delete operations become field-level `rowChanges` with exact before/after values;
- manifest no-ops become `noops`;
- compiler/authority fingerprints become `bindings`; and
- the inactive Grand Sport X promotion scaffold remains one explicitly named non-manifest row change bound to the frozen projection receipt.

The function may perform mechanical sheet/header resolution and the already-verified greenfield isolation migration. It may not infer new product meaning or read `decisions.json`.

- [x] **Step 4: Add session emission and immutable artifact output**

`WizardSessionStore.emit_changeset(run_id)` requires `compiled_ready`, exact current inputs, no downstream mutation, and writes `workbook-change-set.json` atomically in the run directory. Re-emission from identical inputs must be byte-identical. A changed input invalidates the artifact and requires recompile.

Successful emission transitions the session to `changeset_emitted` (a new state constant declared next to `STATE_COMPILED_READY`). `list_sessions()` must then return the run with `runId` and `state: "changeset_emitted"` — the exact payload shape the Tasks 8/9 session lookups filter on.

- [x] **Step 5: Keep the legacy-equivalence comparison test-local**

Leave `plan_builder.py` untouched in this task. The equivalence harness lives only in the test file: `tests/test_ingest_wizard_plan.py` imports the still-present `build_manifest_plan()` and compares legacy projection semantics (sheet creates, field-level before/after rows, no-op coverage) against the new ChangeSet over the frozen snapshot. Add no production wrapper, and give the comparison no approval/write authority. Task 6 deletes `build_manifest_plan()` together with the plan stage and removes this comparison test in the same commit, so `plan_builder.py` is touched once.

- [x] **Step 6: Run exact-current and focused compiler gates**

```sh
PYTHONPATH=scripts .venv/bin/python -m pytest \
  tests/test_ingest_wizard_changeset.py \
  tests/test_ingest_wizard_plan.py \
  tests/test_ingest_wizard_compiler_session.py \
  tests/test_ingest_wizard_exception_flow.py -q
```

Expected: PASS with frozen semantic coverage and protected hashes unchanged.

- [x] **Step 7: Commit the emitter**

```sh
git diff --check
git add scripts/corvette_form_generator/ingest/wizard/changeset_emitter.py \
  scripts/corvette_form_generator/ingest/wizard/session.py \
  tests/test_ingest_wizard_changeset.py \
  tests/test_ingest_wizard_plan.py \
  tests/test_ingest_wizard_compiler_session.py
git commit -m "feat: emit shared changesets from ingest"
```

**Task 5 verification receipt (2026-07-19):** Completed in commit
`1607b67`, independently reverified. Both delegated implementer subagents
timed out at the delegation cap: the session subagent had already landed
its exact-design `session.py` diff (including the two evidence-state
extensions later validated on review); the test subagent produced
nothing. The orchestrator ported the emitter and wrote all tests
directly. Before any test existed, a throwaway probe ran both projections
over the frozen run and live workbook: 9 identical sheetCreates, 3,710
rowChanges with identical op identities and zero after-value mismatches,
2,699 noops, 6,408/6,408 coverage, one named scaffold — the same result
the committed `LegacyEquivalenceTest` now proves (3 fixture scenarios +
the frozen snapshot, which ran rather than skipped). Plan-text
adaptations, all validated by the spec-compliance review, which also
verified the validation half of the port line-for-line identical to
`build_manifest_plan`: `run_id` is a required emitter input (source
identity is signed); add/delete rowChanges omit None-after/None-before
columns (the Task 3 contract rejects None→None unchanged pairs; final
workbook state identical); update rowChanges emit only true field deltas
(legacy update ops carry all non-key columns); scaffold provenance is
kind `scaffold` with no manifestRef; targets sorted per contract;
`warningAcknowledgementsRequested` emitted empty (the service derives
accepted warnings from the live preview); the session gained
`STATE_CHANGESET_EMITTED` in `COMPILER_EVIDENCE_STATES` and the
`_parsed_candidates` allow-list (required for idempotent re-emission).
Gates passed: the Task 5 lane (`test_ingest_wizard_changeset.py`,
`test_ingest_wizard_plan.py`, `test_ingest_wizard_compiler_session.py`,
`test_ingest_wizard_exception_flow.py`) at 90 tests and 4 subtests; the
full ingest wizard lane at 183; all five Task 1 protected hashes
re-verified unchanged (manifest `b3e32dea`, apply-plan `0b91bffd`,
compile-report `ffa8215a`, resolutions `c47335d1`, workbook `03e8c967`).
Spec-compliance review passed. The code-quality reviewer timed out at the
delegation cap, so the orchestrator performed the quality pass directly:
determinism (sorted creates, explicit sortKey ordering, sorted bindings,
no timestamps — plus two passing byte-identical re-emission tests that
re-emit rather than re-read), input purity (copies throughout, only the
workbook file is read), `_existing` never serialized (explicit
construction at every output site), ValueError parity with
`build_manifest_plan` and no partial-artifact path (emission completes
before the atomic two-file replace). Deferred minors: intentional
`_manifest_key_text`/helper duplication until Task 6 deletes the legacy
projection; emitter self-parse adds ~1-2s on a 6,408-row changeset.
Worktree clean; no product files, generated artifacts, or ingest run
artifacts modified.

### Task 6: Make the browser/API expose only the five-function current path

**Files:**
- Create: `scripts/corvette_form_generator/ingest/wizard/legacy_reader.py`
- Modify: `scripts/corvette_form_generator/ingest/wizard/session.py`
- Modify: `scripts/corvette_form_generator/ingest/wizard/plan_builder.py` — delete `build_manifest_plan()` with the plan stage
- Modify: `scripts/ingest_wizard_server.py:108-343`
- Delete: `scripts/ingest_wizard_apply.py` — calls the retired `apply_approved_plan()` write surface
- Modify: `visualizer/ingest-wizard/index.html`
- Modify: `visualizer/ingest-wizard/wizard.js`
- Modify: `visualizer/ingest-wizard/wizard.css`
- Modify: `tests/test_ingest_wizard_server.py`
- Modify: `tests/test_ingest_wizard_server_pass_b.py`
- Modify: `tests/test_ingest_wizard_ui_milestone2.py`
- Modify: `tests/test_ingest_wizard_ui_blockers.py`
- Modify: `tests/test_ingest_wizard_plan.py` — drop the Task 5 legacy-equivalence comparison
- Delete: `tests/test_ingest_wizard_apply.py` — suite for the retired apply CLI

**Interfaces:**
- Consumes: `WizardSessionStore` intake/profile/select/compile/exception/emit methods and `LegacyRunReader` GET methods.
- Produces: `POST /changeset`, `GET /changeset`, the `changeset_emitted` state in `GET /api/wizard/sessions` payloads, five-function browser flow, and HTTP `410` for retired mutation routes.

- [x] **Step 1: Write failing server boundary tests**

```python
def test_current_compiled_ready_session_emits_changeset(self):
    status, payload = self.post_json(
        f"/api/wizard/sessions/{self.run_id}/changeset", {}
    )
    self.assertEqual(status, 200)
    self.assertEqual(payload["changeSet"]["schemaVersion"], "workbook-changeset-1")
    self.assertEqual(payload["session"]["state"], "changeset_emitted")


def test_sessions_list_exposes_changeset_emitted_state(self):
    status, payload = self.get_json("/api/wizard/sessions")
    self.assertEqual(status, 200)
    emitted = {
        session["runId"]
        for session in payload["sessions"]
        if session.get("state") == "changeset_emitted"
    }
    self.assertIn(self.run_id, emitted)


def test_retired_mutation_routes_are_gone(self):
    for suffix in (
        "/decisions", "/decisions/delete", "/copy-decisions", "/complete",
        "/plan", "/plan/approve", "/write/approve",
    ):
        status, payload = self.post_json(
            f"/api/wizard/sessions/{self.run_id}{suffix}", {}
        )
        self.assertEqual(status, 410)
        self.assertEqual(payload["error"], "Historical ingest mutation is retired.")
```

Add a source assertion that `wizard.js` contains no `back-to-review`, `copy-decisions`, `mark-complete`, plan approval, or write approval binding.

- [x] **Step 2: Run server/UI tests and verify current routes remain writable**

```sh
PYTHONPATH=scripts .venv/bin/python -m pytest \
  tests/test_ingest_wizard_server.py \
  tests/test_ingest_wizard_server_pass_b.py \
  tests/test_ingest_wizard_ui_milestone2.py \
  tests/test_ingest_wizard_ui_blockers.py -q
```

Expected: FAIL on the new boundary assertions.

- [x] **Step 3: Replace the current plan stage with ChangeSet completion**

The compiler summary shows one action, `Create ChangeSet`, only for `compiled_ready`. Its result screen shows targets, sheet creations, row-change counts, no-op coverage, workbook fingerprint, and download. It contains no approval or apply control and no route back into historical review. Delete the now-unreachable `build_manifest_plan()` from `plan_builder.py` and the Task 5 legacy-equivalence comparison from `tests/test_ingest_wizard_plan.py` in the same commit.

- [x] **Step 4: Retire mutation routes explicitly**

POST requests to the seven historical endpoints return HTTP `410` and the exact error above. GET historical plan/evidence display may call `LegacyRunReader`, which reads JSON only and exposes no write methods. Remove `approve_write()` and `apply_approved_plan()` from the server-reachable store surface.

Retire `scripts/ingest_wizard_apply.py` and `tests/test_ingest_wizard_apply.py` in this commit: the script calls the removed `apply_approved_plan()` surface, and `scripts/apply_workbook_changeset.py` is the only operator preview/approval/write CLI. Do not convert it to a wrapper — the pass-c-3 write contract it enforces is retired, not relocated.

- [x] **Step 5: Remove current-session imports of write/deployment orchestration**

Move temporary deployment-proof helpers from `session.py` to `workbook_domain/deployment_proof.py`. The ingest session may import the ChangeSet emitter but may not import `apply_batch`, `save_workbook_safely`, generators, registry publication, promotion, or the shared service's apply function.

- [x] **Step 6: Run focused tests and static authority checks**

```sh
PYTHONPATH=scripts .venv/bin/python -m pytest \
  tests/test_ingest_wizard_server.py \
  tests/test_ingest_wizard_server_milestone2.py \
  tests/test_ingest_wizard_server_pass_b.py \
  tests/test_ingest_wizard_ui_milestone2.py \
  tests/test_ingest_wizard_ui_blockers.py -q
node --check visualizer/ingest-wizard/wizard.js
! rg -n "apply_batch|save_workbook_safely|approve_write|apply_approved_plan|generate_registry|promote_model" \
  scripts/corvette_form_generator/ingest/wizard/session.py \
  scripts/ingest_wizard_server.py \
  visualizer/ingest-wizard/wizard.js
```

Expected: all tests and static checks PASS.

- [x] **Step 7: Commit the narrow current UI/API**

```sh
git diff --check
git add scripts/corvette_form_generator/ingest/wizard \
  scripts/corvette_form_generator/workbook_domain/deployment_proof.py \
  scripts/ingest_wizard_server.py \
  scripts/ingest_wizard_apply.py \
  visualizer/ingest-wizard \
  tests/test_ingest_wizard_server.py \
  tests/test_ingest_wizard_server_pass_b.py \
  tests/test_ingest_wizard_ui_milestone2.py \
  tests/test_ingest_wizard_ui_blockers.py \
  tests/test_ingest_wizard_plan.py \
  tests/test_ingest_wizard_apply.py
git commit -m "refactor: narrow ingest to changeset emission"
```

**Task 6 verification receipt (2026-07-19):** Completed with the current
browser/API narrowed to intake/profile, target selection, compile/typed
exceptions, and immutable ChangeSet emission. The boundary RED run failed on
the new ChangeSet, exact-410, and retired-binding assertions before the
implementation. `LegacyRunReader` now provides JSON-only historical plan and
ChangeSet display; all seven retired POST routes return the exact HTTP 410
contract; `scripts/ingest_wizard_apply.py` and its test suite are retired; the
legacy manifest projection/equivalence surface is removed; and temporary
deployment proof is isolated in `workbook_domain/deployment_proof.py`. Gates
passed: the exact Step 6 lane at `31 tests and 11 subtests`, the retained
historical projection-library lane at 13 tests, and the current
ChangeSet/compiler/exception/session lane at `68 tests and 4 subtests`;
`node --check`, Python compilation of all moved/touched entrypoints, and the
static no-write-authority search also passed. The implementer subagent reached
its iteration cap after producing the coherent implementation and RED/GREEN
evidence; the orchestrator retired the remaining store-plan tests and reran all
named gates. No canonical workbook, generated runtime artifact, publication,
promotion, deployment, or dealer surface changed.

### Task 7: Remove the embedded editor ingest workflow and close Phase 1

**Files:**
- Modify: `visualizer/workbook-editor/editor.js:946-1321,1454-1512`
- Modify: `visualizer/workbook-editor/editor.css`
- Modify: `scripts/workbook_editor_server.py`
- Delete: `visualizer/workbook-editor/workbook-editor.js`
- Modify: `tests/test_editor_ops_meta.py`
- Delete: `tests/test_editor_server_ingest_review.py` — suite for the removed `/api/ingest/*` handlers
- Modify: `docs/ingest/ingest-separation-model-integration-editor-consolidation-spec.md`
- Modify: `docs/ingest/README.md`
- Modify: `README.md`
- Modify: `AGENTS.md` — §8 ingest write-path description

**Interfaces:**
- Consumes: shared ChangeSet service and existing editor operations.
- Produces: fallback editor without Ingest Review; Phase 1 completion evidence.

- [x] **Step 1: Add failing source/UI assertions**

```python
def test_workbook_editor_has_no_ingest_review_navigation():
    source = Path("visualizer/workbook-editor/editor.js").read_text()
    assert ">Ingest Review<" not in source
    assert "/api/ingest/" not in source


def test_dead_react_prototype_is_absent():
    assert not Path("visualizer/workbook-editor/workbook-editor.js").exists()
```

- [x] **Step 2: Run the assertions and verify the old tab/prototype exist**

```sh
PYTHONPATH=scripts .venv/bin/python -m pytest tests/test_editor_ops_meta.py -q
```

Expected: FAIL on both new assertions.

- [x] **Step 3: Remove only the obsolete ingest surface and dead file**

Delete `IngestReviewTab`, its helpers/state/styles, its navigation button/render branch, and unreferenced server `/api/ingest/*` handlers. Delete the unreferenced React prototype. Delete `tests/test_editor_server_ingest_review.py` with the handlers it covers; the Pass 2 payload library (`ingest/review_payload.py`) and `tests/test_ingest_review_payload.py` stay as legacy library surface. Preserve Form Structure, Sheet Browser, Review, Pending Changes, operation payloads, and Apply behavior.

- [x] **Step 4: Run the complete Phase 1 gate**

Run the full live ingest/editor/domain suite surface, not only the files Tasks 1–6 happened to touch:

```sh
PYTHONPATH=scripts .venv/bin/python -m pytest \
  tests/test_workbook_domain_registry.py \
  tests/test_workbook_changeset.py \
  tests/test_workbook_changeset_service.py \
  tests/test_editor_ops_apply.py \
  tests/test_editor_ops_global_families.py \
  tests/test_editor_ops_meta.py \
  tests/test_editor_server_payload.py \
  tests/test_editor_server_write_api.py \
  tests/test_ingest_review_payload.py \
  tests/test_ingest_wizard_canonical_compiler.py \
  tests/test_ingest_wizard_canonical_rows.py \
  tests/test_ingest_wizard_changeset.py \
  tests/test_ingest_wizard_comparator_evidence.py \
  tests/test_ingest_wizard_compiler_session.py \
  tests/test_ingest_wizard_copy_split.py \
  tests/test_ingest_wizard_decisions.py \
  tests/test_ingest_wizard_exception_flow.py \
  tests/test_ingest_wizard_exceptions.py \
  tests/test_ingest_wizard_hints.py \
  tests/test_ingest_wizard_identity.py \
  tests/test_ingest_wizard_joiner.py \
  tests/test_ingest_wizard_parser.py \
  tests/test_ingest_wizard_plan.py \
  tests/test_ingest_wizard_profile_compiler.py \
  tests/test_ingest_wizard_profiler.py \
  tests/test_ingest_wizard_relationship_compiler.py \
  tests/test_ingest_wizard_server.py \
  tests/test_ingest_wizard_server_milestone2.py \
  tests/test_ingest_wizard_server_pass_b.py \
  tests/test_ingest_wizard_session.py \
  tests/test_ingest_wizard_ui_blockers.py \
  tests/test_ingest_wizard_ui_milestone2.py \
  tests/test_ingest_wizard_ui_reference.py \
  tests/test_ingest_wizard_ui_relationships.py \
  tests/test_order_guide_ingest_interpreter.py \
  tests/test_order_guide_ingest_profiler.py -q
node --check visualizer/ingest-wizard/wizard.js
node --check visualizer/workbook-editor/editor.js
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
git diff --check
```

Expected: all tests PASS; workbook validators clean; no protected product file changed. Two suites are absent by design: `tests/test_ingest_wizard_apply.py` (retired in Task 6) and `tests/test_editor_server_ingest_review.py` (retired in Step 3 with the `/api/ingest/*` handlers). `tests/test_editor_lints.py` is excluded from this gate: its `RealWorkbookCompareTest` reds are pre-existing workbook-data findings tracked outside this program — run it separately and confirm only the same named failures, no new ones.

- [x] **Step 5: Update owner docs with exact Phase 1 evidence**

Mark Phase 1 complete in the approved spec, name commits/files/tests, state that no workbook write occurred, and replace README descriptions of the ingest/editor surfaces with the five-function/shared-service path. Update AGENTS.md §8 so the raw-ingest write-path description names `workbook-changeset-1` emission plus the shared service and `scripts/apply_workbook_changeset.py` in place of the retired `pass-c-3`/`ingest_wizard_apply.py` contract. Do not duplicate the full spec in README or AGENTS.md.

- [x] **Step 6: Commit Phase 1 closure**

```sh
git add visualizer/workbook-editor \
  scripts/workbook_editor_server.py \
  tests/test_editor_ops_meta.py \
  tests/test_editor_server_ingest_review.py \
  docs/ingest/ingest-separation-model-integration-editor-consolidation-spec.md \
  docs/ingest/README.md README.md AGENTS.md
git commit -m "refactor: remove duplicate ingest editor workflow"
```

**Task 7 / Phase 1 verification receipt (2026-07-19):** Completed in commit
`9da2757`. The source/UI assertions failed first on the existing Ingest Review
tab and dead React prototype, then passed after the obsolete UI block/styles,
server `/api/ingest/*` handlers/options, prototype, and handler test suite were
removed. Form Structure, Sheet Browser, Review, Pending Changes, typed
operation payloads, and fallback Apply behavior were preserved. The first full
gate exposed eleven stale assertions for Task 6-retired `mark_complete` and
broad-review reference/relationship browser controls; those historical tests
were retired or rebound to the five-function/typed-exception path rather than
restoring unreachable mutation UI. The rerun passed `486 tests and 36
subtests` in 180.53 seconds. `node --check` passed for both wizard/editor
scripts; workbook package and schema validation were valid with zero issues,
errors, or warnings; and `git diff --check` passed after removing one trailing
CSS blank line. The separate editor-lint lane retained only the three known
real-workbook failures (`d1_rwj_wks_collision`,
`c2_cj2_stingray_name_deviator`, `r3_drz_pending_review`) with 23 tests
passing. No canonical workbook, generated artifact, registry, runtime,
promotion, deployment, or dealer surface changed. Phase 2 was not started.

---

## Phase 2 — Integrate Grand Sport X, ZR1, and ZR1X

### Task 8: Rebuild and prove the all-target ChangeSet, then stop for approval

**Files:**
- Generated run artifact: `form-output/ingest-wizard/$ingest_run_id/workbook-change-set.json`
- Generated receipts in an explicit temporary directory outside tracked product paths.
- Modify after proof: `docs/ingest/ingest-separation-model-integration-editor-consolidation-spec.md`

**Interfaces:**
- Consumes: current `main` workbook/source fingerprints, five-function ingest module, shared service, and ratified GSX/N26/inactive-promotion interpretation.
- Produces: one exact-current atomic ChangeSet and passing preview/deployment proof; no canonical write.

- [x] **Step 1: Reconcile the feature branch with `main` without accepting generated/audit drift**

Before any merge/rebase operation, inspect `git status`, branch divergence, workbook hash, `form-app/data.js`, tracked `form-output`, and `form-output/workbook-edit-log.jsonl`. Preserve `main`'s canonical workbook and real audit entry. Do not reuse any old approval after reconciliation.

- [x] **Step 2: Start the ingest server and re-run the five-function path through compile**

Start the ingest server if it is not already running; the browser flow and every session lookup below require it:

```sh
.venv/bin/python scripts/ingest_wizard_server.py --port 8040
```

Use the browser or service API to select the raw source, confirm roles, select `grand_sport_x`, `zr1`, and `zr1x`, and compile. Record the new run ID and compile/queue hashes in the owner spec at compile time, and set `ingest_run_id` to the new run's ID — the seed step and all later steps consume it.

- [x] **Step 3: Seed the frozen exception resolutions behind a fingerprint gate**

The frozen run carries 158 typed exception resolutions, stored strictly per-run, and resolutions shape the manifest the ChangeSet projects. A fresh compile re-emits the same queue with zero seeding; re-answering it by hand would silently invalidate the exact-equivalence argument this phase rests on. Copy the frozen resolutions into the new run only when the queue fingerprint matches exactly, and refuse otherwise:

```sh
frozen_resolutions="form-output/ingest-wizard/20260717-091317-470292/exception-resolutions.json"
run_dir="form-output/ingest-wizard/$ingest_run_id"
test "$(jq -r '.queueSubjectFingerprint' "$frozen_resolutions")" = \
  "$(jq -r '.queueSubjectFingerprint' "$run_dir/exception-queue.json")"
cp "$frozen_resolutions" "$run_dir/exception-resolutions.json"
```

Re-run projection so the manifest and compile report bind the replayed `resolutionSemanticSha`, then confirm every replayed resolution reads back valid against the current queue. Resolve by hand only genuinely newly emitted typed exceptions — the expected count is zero. A fingerprint mismatch or an invalidated replayed resolution stops the task: reconcile against the frozen snapshot instead of re-answering the queue.

- [x] **Step 4: Emit the ChangeSet and resolve the run/proof paths from the server**

Emit one ChangeSet from the seeded session, then resolve the emitted run and stable proof paths. The server lookup must return the same run ID recorded in Step 2:

```sh
curl --fail --silent http://127.0.0.1:8040/api/wizard/sessions \
  > /private/tmp/27vette-ingest-sessions.json
ingest_run_id_lookup="$(jq -r '.sessions | map(select(.state == "changeset_emitted")) | sort_by(.runId) | last | .runId' \
  /private/tmp/27vette-ingest-sessions.json)"
test -n "$ingest_run_id_lookup" && test "$ingest_run_id_lookup" != "null"
test "$ingest_run_id_lookup" = "$ingest_run_id"
changeset_path="form-output/ingest-wizard/$ingest_run_id/workbook-change-set.json"
proof_dir="/private/tmp/27vette-changeset-proof-$ingest_run_id"
test -f "$changeset_path"
mkdir -p "$proof_dir"
```

Record the emission hashes in the owner spec.

- [x] **Step 5: Preview through the shared CLI into an isolated directory**

```sh
.venv/bin/python scripts/apply_workbook_changeset.py \
  "$changeset_path" \
  --workbook stingray_master.xlsx \
  --preview-out "$proof_dir/change-preview.json"
```

Expected: preview `ok=true`, exact coverage, no unresolved blockers, and no canonical workbook mutation.

- [x] **Step 6: Run relocated deployment proof on temporary workbooks**

Call `workbook_domain.deployment_proof` for GSX+ZR1, ZR1X repeatability, and the all-target atomic ChangeSet. Require package/schema/Boolean/final-state/readback, generator contracts, registry loading, zero semantic signature mismatches, zero deployment blockers, and zero deferrals.

- [x] **Step 7: Present the approval packet and stop**

Present targets, workbook SHA/mtime, sheet creations, row changes by sheet/action, no-op coverage, warning IDs, backup/rollback behavior, preview hash, deployment-proof hash, protected-surface hashes, and the three ratified interpretation statements. Do not create `ChangeApproval` or run `--write` until Sean explicitly approves this exact packet.

**Task 8 receipt — 2026-07-19:** Completed under Sean's bounded recovery
authorization. The stale frozen packet was not copied or force-rebound. The
recovery reused 131 exact frozen `(subjectId, subjectVersion)` resolutions,
omitted eight changed-version and 19 removed subjects, reviewed all 75 current
new/changed subjects, and recompiled to 203 resolved subjects with no stale,
superseded, or deferred entries. Exact-current ChangeSet
`5f108f09bb09d4dddafa18a6` creates 12 sheets, carries 4,204 row changes, and
accounts for 2,488 noops. Shared preview fingerprint
`03ecd79f2fbad407e41ec289868625ab7620a0000dc3ea0873e718069d51e8de`
has zero blocking/unknown warnings. ChangeSet-aware temporary deployment proof
fingerprint
`0e2a72e256668d3be13628cba613341e9ddf85722efe6ad53ddc2f91c6bc7a32`
passed all three required phases with zero blockers, deferrals, or runtime
semantic mismatches. Independent temporary application covered all 4,216
prepared operations and 21,063 changed field pairs; package, schema, Boolean,
readback, formulas, generation, and registry checks passed. The exact packet is
`/private/tmp/27vette-changeset-proof-20260719-174505-0085ca/task8-approval-packet.json`
(SHA-256
`8b1574dd5622643d7820bff35fe7813792d4fec147980a9cc04f33355f10827a`).
Protected product surfaces remained byte-identical. No approval, canonical
write, publication, promotion, deployment, or dealer change occurred. Manual
approval review must include the packet's explicit note that 10 of 12
batch-created sheets preserve exact headers but not the named template's header
font/style under the existing generic writer. Task 9 remains unstarted and
requires explicit approval of this exact packet.

### Task 9: Apply the approved ChangeSet once and regenerate affected artifacts

**Files:**
- Modify: `stingray_master.xlsx`
- Create: recoverable workbook backup under `backups/`
- Modify: affected `form-output/` generated artifacts through generators only
- Modify: `form-app/data.js` only if separately authorized publication occurs; workbook integration alone must not modify it
- Modify: `docs/ingest/ingest-separation-model-integration-editor-consolidation-spec.md`
- Modify: `docs/ingest/milestone-3-canonical-plan-deployment-proof-implementation-plan.md`

**Interfaces:**
- Consumes: exact approved ChangeSet, preview, warning IDs, workbook fingerprint, and approval actor.
- Produces: one successful ChangeReceipt, verified workbook backup/readback, and regenerated three-model contracts.

- [x] **Step 1: Create the bound approval without writing**

The ingest server from Task 8 must still be running — restart it with `.venv/bin/python scripts/ingest_wizard_server.py --port 8040` if it is not. Recover the exact approved paths and refuse if its preview packet is absent:

```sh
curl --fail --silent http://127.0.0.1:8040/api/wizard/sessions \
  > /private/tmp/27vette-ingest-sessions.json
ingest_run_id="$(jq -r '.sessions | map(select(.state == "changeset_emitted")) | sort_by(.runId) | last | .runId' \
  /private/tmp/27vette-ingest-sessions.json)"
changeset_path="form-output/ingest-wizard/$ingest_run_id/workbook-change-set.json"
proof_dir="/private/tmp/27vette-changeset-proof-$ingest_run_id"
test -f "$changeset_path" && test -f "$proof_dir/change-preview.json"
```

```sh
.venv/bin/python scripts/apply_workbook_changeset.py \
  "$changeset_path" \
  --workbook stingray_master.xlsx \
  --approve Sean \
  --preview "$proof_dir/change-preview.json" \
  --approval-out "$proof_dir/change-approval.json"
```

Expected: approval created; workbook hash unchanged.

The approval invocation must also pass every exact
`warningPolicy.confirmableIds[]` value from the bound preview as a repeated
`--accept-warning` argument. The initial sample omitted those arguments and
failed closed with `warning_confirmation_mismatch`; the corrected invocation
accepted exactly the 21 packet-bound scaffold warnings and no others.

- [x] **Step 2: Confirm Excel is closed and the exact workbook fingerprint still matches**

```sh
test ! -e './~$stingray_master.xlsx'
shasum -a 256 stingray_master.xlsx
```

Expected: no lock and the exact approved SHA.

- [x] **Step 3: Perform the one authorized live write**

```sh
.venv/bin/python scripts/apply_workbook_changeset.py \
  "$changeset_path" \
  --workbook stingray_master.xlsx \
  --write \
  --preview "$proof_dir/change-preview.json" \
  --approval "$proof_dir/change-approval.json" \
  --receipt-out "$proof_dir/change-receipt.json"
```

Expected: `status=applied`, verified backup path, exact prepared/readback counts, zero validation errors, and a changed canonical workbook SHA.

- [x] **Step 4: Verify the saved workbook and backup independently**

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
test -f "$(jq -r '.backupPath' "$proof_dir/change-receipt.json")"
```

Expected: package valid, schema zero errors/warnings, backup exists.

- [x] **Step 5: Regenerate the three targets without public promotion**

Run the exact model-generation configuration discovered from the saved workbook for `grand_sport_x`, `zr1`, and `zr1x`. Do not call `promote_model.py --write` and do not publish `form-app/data.js` unless separately approved.

The applied rows intentionally remain inactive, so the production CLI correctly
does not discover them. Sean separately approved the existing deployment-proof
scratch activator for this step: activate only the three targets in a temporary
copy, validate that copy, discover configs there, then supply those configs to
the normal generator with only the three tracked runtime-contract paths rooted
in the repository. The canonical workbook and `form-app/data.js` must remain
byte-identical across this generation step.

- [x] **Step 6: Run affected and existing-model gates**

```sh
PYTHONPATH=scripts .venv/bin/python -m pytest \
  tests/test_model_config_metadata.py \
  tests/test_registry_promotion_metadata.py \
  tests/test_schema_validation_metadata.py \
  tests/test_rule_derivation.py -q
node --test tests/stingray-form-regression.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/z06-form-data-draft.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
git diff --check
```

Expected: all relevant gates PASS. Review all workbook/generated diffs and restore only proven timestamp churn.

- [x] **Step 7: Close Phase 2 and commit only verified source/generated changes**

Record exact workbook backup/hash, ChangeSet/preview/approval/receipt hashes, sheets/counts, generator/test results, preserved runtime/dealer boundaries, and residual risk in the two owner docs. Never stage the temporary proof directory or backup.

```sh
git diff --check
git add -- stingray_master.xlsx \
  form-output/runtime/grand-sport-x-runtime-contract.json \
  form-output/runtime/zr1-runtime-contract.json \
  form-output/runtime/zr1x-runtime-contract.json \
  docs/ingest/ingest-separation-model-integration-editor-consolidation-spec.md \
  docs/ingest/milestone-3-canonical-plan-deployment-proof-implementation-plan.md
git diff --cached --check
git commit -m "feat: integrate grand sport x zr1 and zr1x workbook data"
```

Expected: the backup and `/private/tmp` receipts remain unstaged; `form-app/data.js` remains unchanged.

**Task 9 receipt — 2026-07-19:** ChangeSet
`5f108f09bb09d4dddafa18a6` was approved by Sean and applied once. Receipt
SHA-256 `75095a18e240789ca06c9b333fafa1482328ebd444e270138dd39cdb4663141d`
verified all 4,216 operations and backup
`backups/stingray_master-20260719-224756.xlsx`. The integrated workbook SHA-256
is `1c9bb513b147f6b3c5d91625719b04d6f297ddfd98d75072e8f8b3771a0a3219`;
package/schema validation returned zero issues, errors, or warnings. The
separately approved scratch-activation generation produced Grand Sport X, ZR1,
and ZR1X runtime contracts with zero validation errors while leaving the
canonical workbook and `form-app/data.js` unchanged. Python passed 75 tests;
Node passed 89/89, 19/19, 24/24, and 47/47. The targets remain inactive and
unpromoted. No registry publication, deployment, runtime-code, or dealer change
occurred. Residual risk is limited to the approved header font/style difference
on 10 of 12 new sheets.

---

## Phase 3 — Consolidate to one workbook editor

### Task 10: Make Manager metadata a shared-registry adapter

**Files:**
- Modify: `workbook-manager/backend/app/specs.py`
- Modify: `workbook-manager/backend/app/validation.py`
- Modify: `workbook-manager/backend/app/importer.py`
- Modify: `tests/test_workbook_manager.py`

**Interfaces:**
- Consumes: `workbook_domain.registry` and disposable imported workbook rows.
- Produces: SQL projection metadata with no duplicate keys/types/enums/references and transactional re-import.

- [ ] **Step 1: Add failing registry parity and transactional import tests**

```python
def test_every_editable_manager_table_uses_shared_family_contract(self):
    for spec in TABLE_SPECS:
        if not spec.editable:
            continue
        shared = family_spec(spec.editor_family)
        self.assertEqual(spec.key, shared["key"])
        self.assertEqual(spec.types(), shared.get("types", {}))
        self.assertEqual(spec.enums(), shared.get("enums", {}))


def test_failed_reimport_preserves_promoted_projection(self):
    before = snapshot_imported_counts(self.conn)
    with self.assertRaises(KeyError):
        importer.run(self.conn, self.missing_required_sheet_workbook)
    self.assertEqual(snapshot_imported_counts(self.conn), before)
```

- [ ] **Step 2: Run focused Manager tests and verify the duplicated contract/failure**

```sh
PYTHONPATH=scripts .venv/bin/python -m pytest tests/test_workbook_manager.py -q
```

Expected: new parity or transactional test FAILS before implementation.

- [ ] **Step 3: Reduce `specs.py` to SQL/projection-only metadata**

Keep physical table/column naming and reversible import mapping. Resolve workbook key/type/enum/ref/model-scoping behavior from `family_spec(spec.editor_family)`. Delete duplicated workbook-domain literals.

- [ ] **Step 4: Make import build a replacement database transactionally**

Build/import/validate in a temporary database or one uncommitted transaction. Promote only after all required sheets, mappings, foreign keys, lineage, and contract gates pass. On failure, leave the active database bytes and imported counts unchanged.

- [ ] **Step 5: Run Manager and workbook gates**

```sh
PYTHONPATH=scripts .venv/bin/python -m pytest tests/test_workbook_manager.py -q
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Expected: PASS; canonical workbook unchanged.

- [ ] **Step 6: Commit the disposable-projection conversion**

```sh
git diff --check
git add workbook-manager/backend/app/specs.py \
  workbook-manager/backend/app/validation.py \
  workbook-manager/backend/app/importer.py \
  tests/test_workbook_manager.py
git commit -m "refactor: derive manager contracts from shared registry"
```

### Task 11: Replace Manager full-row sync with ChangeSet journal semantics

**Files:**
- Modify: `workbook-manager/backend/app/db.py`
- Modify: `workbook-manager/backend/app/staging.py`
- Modify: `workbook-manager/backend/app/sync.py`
- Modify: `workbook-manager/backend/app/main.py`
- Modify: `workbook-manager/backend/app/schemas.py`
- Modify: `tests/test_workbook_manager.py`

**Interfaces:**
- Consumes: shared ChangeSet parser/service and disposable projection rows.
- Produces: draft/approved/applied/failed/cancelled ChangeSet journal with retry, cancel, and rebase.

- [ ] **Step 1: Add failing conflict, atomic batch, and recovery tests**

```python
def test_two_edits_to_one_row_coalesce_to_field_deltas(self):
    stage_price(self.conn, "opt_1", 100, 200)
    stage_description(self.conn, "opt_1", "Old", "New")
    changeset = staging.build_changeset(self.conn, actor="Sean")
    row = changeset["rowChanges"][0]
    self.assertEqual(set(row["fields"]), {"price", "description"})


def test_parent_and_member_validate_atomically(self):
    stage_exclusive_group(self.conn, "grp_new")
    stage_exclusive_member(self.conn, "grp_new", "opt_1")
    preview = staging.preview_draft(self.conn, actor="Sean")
    self.assertTrue(preview["ok"])


def test_failed_sync_can_retry_cancel_or_rebase(self):
    failed_id = create_failed_changeset(self.conn)
    self.assertEqual(syncmod.retry(self.conn, failed_id)["status"], "draft")
    self.assertEqual(syncmod.cancel(self.conn, failed_id)["status"], "cancelled")
```

- [ ] **Step 2: Run the tests and verify current full-row/pending-only behavior fails**

```sh
PYTHONPATH=scripts .venv/bin/python -m pytest tests/test_workbook_manager.py -q
```

Expected: new tests FAIL.

- [ ] **Step 3: Add journal tables without making SQLite canonical**

Add `changesets` with immutable proposal JSON/fingerprint/workbook fingerprint/status and `changeset_events` with append-only actor/action/detail/timestamp. Allowed statuses are `draft`, `approved`, `applied`, `failed`, and `cancelled`. Imported row tables remain rebuildable projections.

- [ ] **Step 4: Build field-delta ChangeSets from staged edits**

Coalesce changes by `(sheet, family, canonical key)`, retain the earliest before value and latest after value per field, drop net-zero fields, validate the proposed final batch through `preview_changeset()`, and commit one ChangeSet journal record rather than full-row `change_history` snapshots as write authority.

- [ ] **Step 5: Replace sync translation with the shared service**

`sync.py` loads the immutable ChangeSet and bound preview/approval, calls `apply_changeset()`, and records the returned ChangeReceipt event. Failed status remains recoverable. Re-import is blocked while an approved or failed-unsynchronized ChangeSet exists. Rebase refreshes before values only after field-level conflict checks and emits a new fingerprint/preview; it never edits the approved proposal in place.

- [ ] **Step 6: Run all Manager backend and shared-service tests**

```sh
PYTHONPATH=scripts .venv/bin/python -m pytest \
  tests/test_workbook_manager.py \
  tests/test_workbook_changeset.py \
  tests/test_workbook_changeset_service.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit Manager ChangeSet semantics**

```sh
git diff --check
git add workbook-manager/backend/app/db.py \
  workbook-manager/backend/app/staging.py \
  workbook-manager/backend/app/sync.py \
  workbook-manager/backend/app/main.py \
  workbook-manager/backend/app/schemas.py \
  tests/test_workbook_manager.py
git commit -m "refactor: journal manager edits as shared changesets"
```

### Task 12: Make the React Manager the shared-service editor UI

**Files:**
- Modify: `workbook-manager/frontend/src/api.js`
- Modify: `workbook-manager/frontend/src/App.jsx`
- Modify: `workbook-manager/frontend/src/components/ChangesSync.jsx`
- Modify: `workbook-manager/frontend/src/components/FormStructure.jsx`
- Modify: `workbook-manager/frontend/src/components/ModelOperations.jsx`
- Modify: `workbook-manager/frontend/src/components/RecordForm.jsx`
- Modify: `workbook-manager/frontend/src/components/HistoryView.jsx`
- Modify: `workbook-manager/frontend/src/styles.css`
- Create: `tests/test_workbook_manager_frontend.mjs`

**Interfaces:**
- Consumes: Manager endpoints for registry-derived schemas, ChangeSet draft/preview/approval/apply/retry/cancel/rebase, and receipts.
- Produces: one clear editor workflow with explicit workbook/generated/publication state.

- [ ] **Step 1: Add failing frontend contract tests**

```javascript
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const api = fs.readFileSync("workbook-manager/frontend/src/api.js", "utf8");
const sync = fs.readFileSync(
  "workbook-manager/frontend/src/components/ChangesSync.jsx", "utf8"
);

test("manager uses changeset lifecycle endpoints", () => {
  for (const route of ["/api/changesets/preview", "/approve", "/apply", "/retry", "/cancel", "/rebase"]) {
    assert.match(api, new RegExp(route.replaceAll("/", "\\/")));
  }
  assert.doesNotMatch(api, /\/api\/sync/);
});

test("post-write state distinguishes workbook and publication", () => {
  assert.match(sync, /Workbook synchronized/);
  assert.match(sync, /Generated artifacts/);
  assert.match(sync, /Registry publication/);
});
```

- [ ] **Step 2: Run the Node test and verify old sync UI fails**

```sh
node --test tests/test_workbook_manager_frontend.mjs
```

Expected: FAIL.

- [ ] **Step 3: Replace staging/sync language with the ChangeSet lifecycle**

The primary flow is Edit fields → Review ChangeSet → Preview → Approve → Apply. Display exact affected rows/fields, warnings, workbook fingerprint, backup/rollback guarantee, and receipt state. Failed items expose Retry, Cancel, and Rebase. Do not expose database commit as successful workbook work.

- [ ] **Step 4: Correct Form Structure through shared registry data**

Render step/section mapping from the backend's registry-derived final structure, including the `section_master.step_key` fallback when `section_presentation.step_key` is blank. Add a backend fixture assertion in `tests/test_workbook_manager.py` and a frontend text/state assertion here.

- [ ] **Step 5: Add compact responsive behavior**

At mobile widths, show one edit/review panel, collapse evidence, and keep the action/status summary visible. Do not add a larger multi-form review surface.

- [ ] **Step 6: Run frontend contracts and build**

```sh
node --test tests/test_workbook_manager_frontend.mjs
(cd workbook-manager/frontend && npm run build)
```

Expected: Node tests PASS and Vite production build succeeds.

- [ ] **Step 7: Commit the final UI path**

```sh
git diff --check
git add workbook-manager/frontend/src tests/test_workbook_manager_frontend.mjs
git commit -m "feat: make manager the shared changeset editor"
```

### Task 13: Prove parity, retire the old editor, and close the program

**Files:**
- Modify: `tests/test_workbook_manager.py`
- Modify: `tests/test_workbook_manager_frontend.mjs`
- Modify: relevant existing editor comparison tests
- Modify: `README.md`
- Modify: `workbook-manager/README.md`
- Modify: `AGENTS.md` only if its durable editor boundary is no longer accurate
- Modify: `docs/ingest/README.md`
- Modify: `docs/ingest/ingest-separation-model-integration-editor-consolidation-spec.md`
- Retire only after parity: `scripts/workbook_editor_server.py`, `visualizer/workbook-editor/`, `scripts/apply_workbook_ops.py`

**Interfaces:**
- Consumes: shared registry/service, Manager backend/UI, saved canonical workbook, and existing editor parity fixtures.
- Produces: one supported editor, closed owner spec, and no stale route/document claims.

- [ ] **Step 1: Add a table-driven parity test covering every writable family**

```python
def test_manager_matches_shared_service_for_every_writable_family(self):
    for family, fixture in writable_family_fixtures().items():
        with self.subTest(family=family):
            changeset = manager_changeset_for_fixture(fixture)
            manager_preview = manager_preview_changeset(changeset)
            shared_preview = preview_changeset(fixture.workbook, changeset)
            self.assertEqual(manager_preview["status"], shared_preview["status"])
            self.assertEqual(manager_preview["operationCoverage"], shared_preview["operationCoverage"])
            self.assertEqual(manager_preview["warnings"], shared_preview["warnings"])
```

Fixtures must cover add/update/delete, parent/member atomic edits, direct/union/conditional references, model/shared sheets, warning confirmation, stale refusal, rollback, failed-sync recovery, and exact readback.

- [ ] **Step 2: Run backend/frontend/browser parity before deleting fallback files**

```sh
PYTHONPATH=scripts .venv/bin/python -m pytest \
  tests/test_workbook_manager.py \
  tests/test_workbook_domain_registry.py \
  tests/test_workbook_changeset.py \
  tests/test_workbook_changeset_service.py \
  tests/test_editor_ops_apply.py -q
node --test tests/test_workbook_manager_frontend.mjs
(cd workbook-manager/frontend && npm run build)
```

Then manually verify the full editor workflow at desktop and mobile widths against a disposable workbook/database. No live canonical write is part of parity testing.

- [ ] **Step 3: Retire the fallback only after every parity row passes**

Remove the old editor server/UI and its now-obsolete tests/README commands. Retire `scripts/apply_workbook_ops.py` in the same pass: `scripts/apply_workbook_changeset.py` is the single operator preview/approval/write CLI, and keeping the old ops-batch CLI would leave a second operator write path over the `editor_ops` compatibility layer. Preserve shared `editor_ops` compatibility only if another active non-editor caller still needs it; otherwise reduce it to a compatibility import layer over `workbook_domain`.

- [ ] **Step 4: Run full affected-path validation**

```sh
PYTHONPATH=scripts .venv/bin/python -m pytest -q
node --test tests/stingray-form-regression.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/z06-form-data-draft.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
node --test tests/test_workbook_manager_frontend.mjs
(cd workbook-manager/frontend && npm run build)
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
git diff --check
```

Expected: affected tests PASS; any pre-existing unrelated failures are named with unchanged evidence; workbook/package/schema/runtime/dealer boundaries remain valid.

- [ ] **Step 5: Close documentation in place**

Mark all three phases complete in the approved spec with dates, commits, files, workbook/model integration evidence, editor parity results, preserved boundaries, and residual risk. Update README and Manager README to one editor command and one ChangeSet path. Remove stale claims that the old editor or ingest plan/apply routes are supported. Do not create another closure spec.

- [ ] **Step 6: Commit the consolidation closeout**

```sh
git diff --check
git add -- README.md workbook-manager/README.md \
  docs/ingest/README.md \
  docs/ingest/ingest-separation-model-integration-editor-consolidation-spec.md \
  tests/test_workbook_manager.py tests/test_workbook_manager_frontend.mjs
git add -u -- scripts/workbook_editor_server.py visualizer/workbook-editor scripts/apply_workbook_ops.py
if ! git diff --quiet -- AGENTS.md; then git add -- AGENTS.md; fi
git commit -m "refactor: consolidate workbook editing on shared changesets"
```

Expected: one final scoped commit after review confirms no unrelated files or temporary artifacts are staged.

## Final program stop conditions

Stop and request Sean's decision if any task requires new product behavior, changes a reviewed compiler semantic, cannot represent an existing safe editor operation in `workbook-changeset-1`, disagrees with a current generator/runtime contract, cannot prove rollback, needs a new dependency/schema/public/deployment/security boundary, or would retire the fallback before parity.

Do not stop merely because a file is large, tests take time, or implementation needs several commits. Do not solve difficulty by adding another plan, state machine, database authority, or compatibility write path.
