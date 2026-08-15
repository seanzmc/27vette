"""Pass 7 checkpoint 5: exact Apply and Rebuild orchestration."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openpyxl import Workbook

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "workbook-manager" / "backend"
for module_path in (str(BACKEND), str(REPO_ROOT / "scripts")):
    if module_path not in sys.path:
        sys.path.insert(0, module_path)

from app import apply_rebuild, db as dbmod, drafts, main  # noqa: E402


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _workbook(path: Path, value: str) -> None:
    wb = Workbook()
    wb.active["A1"] = value
    wb.save(path)
    wb.close()


class TestApplyRebuildPipeline(unittest.TestCase):
    def test_affected_models_use_operation_context_and_promotion(self):
        operations = [
            {"model_id": "stingray", "model_context": ["stingray"]},
            {"model_id": "", "model_context": ["z06", "zr1", "inactive"]},
        ]
        self.assertEqual(
            apply_rebuild.derive_affected_models(
                operations, promoted_models={"stingray", "z06", "zr1"}
            ),
            ["stingray", "z06", "zr1"],
        )

    def test_forced_generation_failure_restores_and_hash_verifies_every_file(self):
        with tempfile.TemporaryDirectory(prefix="wbm-apply-rebuild-") as raw:
            root = Path(raw)
            workbook = root / "fixture.xlsx"
            runtime = root / "form-output/runtime/stingray-runtime-contract.json"
            registry = root / "form-app/data.js"
            index = root / "form-app/index.html"
            rollback_root = root / "rollbacks"
            runtime.parent.mkdir(parents=True)
            registry.parent.mkdir(parents=True)
            _workbook(workbook, "before")
            runtime.write_text('{"before":true}\n', encoding="utf-8")
            registry.write_text("window.DATA = 'before';\n", encoding="utf-8")
            index.write_text('<script src="./data.js?v=31"></script>\n', encoding="utf-8")
            tracked = [workbook, runtime, registry, index]
            before = {str(path): _sha(path) for path in tracked}

            rollback = apply_rebuild.prepare_rollback_set(
                draft_id="draft-1",
                workbook_path=workbook,
                repository_root=root,
                rollback_root=rollback_root,
                candidate_models=["stingray"],
            )
            _workbook(workbook, "after")

            def fail_generation(*_args, **_kwargs):
                runtime.write_text('{"partial":true}\n', encoding="utf-8")
                registry.write_text("window.DATA = 'partial';\n", encoding="utf-8")
                raise RuntimeError("forced generation failure")

            receipt = {
                "ok": True,
                "status": "applied",
                "workbookState": "saved",
                "errors": [],
            }
            result = apply_rebuild.complete_apply_rebuild(
                receipt,
                rollback=rollback,
                operations=[{"model_id": "stingray", "model_context": ["stingray"]}],
                workbook_path=workbook,
                repository_root=root,
                generate_candidate=fail_generation,
            )

            self.assertFalse(result["ok"])
            self.assertEqual(result["status"], "apply_rebuild_failed_rolled_back")
            self.assertEqual(result["workbookState"], "restored")
            self.assertEqual(result["applyRebuild"]["rollback"]["state"], "verified")
            self.assertEqual({str(path): _sha(path) for path in tracked}, before)

    def test_success_publishes_candidate_and_bumps_cache_only_when_registry_changes(self):
        with tempfile.TemporaryDirectory(prefix="wbm-apply-rebuild-") as raw:
            root = Path(raw)
            workbook = root / "fixture.xlsx"
            runtime = root / "form-output/runtime/stingray-runtime-contract.json"
            registry = root / "form-app/data.js"
            index = root / "form-app/index.html"
            runtime.parent.mkdir(parents=True)
            registry.parent.mkdir(parents=True)
            _workbook(workbook, "before")
            runtime.write_text('{"before":true}\n', encoding="utf-8")
            registry.write_text("window.DATA = 'before';\n", encoding="utf-8")
            index.write_text('<script src="./data.js?v=31"></script>\n', encoding="utf-8")
            rollback = apply_rebuild.prepare_rollback_set(
                draft_id="draft-1",
                workbook_path=workbook,
                repository_root=root,
                rollback_root=root / "rollbacks",
                candidate_models=["stingray"],
            )
            _workbook(workbook, "after")

            def generate_candidate(*, candidate_root, **_kwargs):
                candidate_runtime = candidate_root / runtime.relative_to(root)
                candidate_registry = candidate_root / registry.relative_to(root)
                candidate_runtime.parent.mkdir(parents=True, exist_ok=True)
                candidate_registry.parent.mkdir(parents=True, exist_ok=True)
                candidate_runtime.write_text('{"after":true}\n', encoding="utf-8")
                candidate_registry.write_text("window.DATA = 'after';\n", encoding="utf-8")
                return {
                    "promoted_models": ["stingray"],
                    "affected_models": ["stingray"],
                    "generated_paths": [str(candidate_runtime)],
                    "registry_path": str(candidate_registry),
                }

            result = apply_rebuild.complete_apply_rebuild(
                {"ok": True, "status": "applied", "workbookState": "saved", "errors": []},
                rollback=rollback,
                operations=[{"model_id": "stingray", "model_context": ["stingray"]}],
                workbook_path=workbook,
                repository_root=root,
                generate_candidate=generate_candidate,
            )

            self.assertTrue(result["ok"])
            self.assertEqual(result["applyRebuild"]["generated_contracts"]["state"], "current")
            self.assertEqual(result["applyRebuild"]["publication"]["state"], "current")
            self.assertEqual(runtime.read_text(encoding="utf-8"), '{"after":true}\n')
            self.assertEqual(registry.read_text(encoding="utf-8"), "window.DATA = 'after';\n")
            self.assertIn('data.js?v=32', index.read_text(encoding="utf-8"))

    def test_status_verifies_workbook_generated_and_publication_hashes(self):
        with tempfile.TemporaryDirectory(prefix="wbm-apply-rebuild-status-") as raw:
            root = Path(raw)
            workbook = root / "fixture.xlsx"
            generated = root / "form-output/runtime/stingray-runtime-contract.json"
            publication = root / "form-app/data.js"
            generated.parent.mkdir(parents=True)
            publication.parent.mkdir(parents=True)
            _workbook(workbook, "applied")
            generated.write_text('{"current":true}\n', encoding="utf-8")
            publication.write_text("window.DATA = 'current';\n", encoding="utf-8")
            payload = {
                "applyRebuild": {
                    "status": "current",
                    "affected_models": ["stingray"],
                    "workbook": {"after_sha256": _sha(workbook)},
                    "generated_contracts": {"files": [{
                        "path": str(generated), "published_sha256": _sha(generated),
                    }]},
                    "publication": {
                        "path": str(publication), "published_sha256": _sha(publication),
                    },
                }
            }

            class EvidenceConnection:
                def execute(self, *_args):
                    return self

                def fetchone(self):
                    return {"result_json": json.dumps(payload)}

            current = apply_rebuild.output_status(
                EvidenceConnection(), workbook_path=workbook, repository_root=root
            )
            self.assertEqual(current["generated_artifacts"]["state"], "current")
            self.assertEqual(current["publication"]["state"], "current")
            generated.write_text('{"drift":true}\n', encoding="utf-8")
            stale = apply_rebuild.output_status(
                EvidenceConnection(), workbook_path=workbook, repository_root=root
            )
            self.assertEqual(stale["generated_artifacts"]["state"], "stale")


class TestApplyRebuildHookBinding(unittest.TestCase):
    def test_terminal_replay_does_not_prepare_or_run_pipeline_twice(self):
        from test_workbook_manager_changeset_lifecycle import TestDurableApplyLifecycle

        with tempfile.TemporaryDirectory(prefix="wbm-apply-rebuild-hook-") as raw:
            root = Path(raw)
            projection, state, workbook, changeset, preview, _, approval, _ = (
                TestDurableApplyLifecycle()._approved(root)
            )
            receipt = {
                "ok": True,
                "schemaVersion": "workbook-change-receipt-1",
                "changeSetId": changeset["changeSetId"],
                "semanticFingerprint": changeset["semanticFingerprint"],
                "previewFingerprint": preview["previewFingerprint"],
                "approvalFingerprint": approval["approvalFingerprint"],
                "status": "applied",
                "workbookState": "saved",
                "errors": [],
                "warnings": [],
                "backupPath": str(root / "backup.xlsx"),
                "logPath": str(root / "edit-log.jsonl"),
                "operationCoverage": {"rawCount": 1, "rawCovered": 1, "preparedCount": 1},
                "verification": {"ok": True, "preparedChecked": 1, "preparedCount": 1},
                "schemaResult": {"status": "valid", "error_count": 0},
                "boolHygieneResult": {"status": "valid", "error_count": 0},
                "gateReminders": [],
                "createdAt": "2026-08-15T00:00:00+00:00",
            }
            prepared = object()
            try:
                with patch.object(
                    drafts.workbook_service, "apply_changeset", return_value=receipt
                ):
                    prepare = unittest.mock.Mock(return_value=prepared)
                    complete = unittest.mock.Mock(return_value={
                        **receipt,
                        "applyRebuild": {"status": "current"},
                    })
                    first = drafts.apply_draft(
                        state,
                        draft_id="draft-approval",
                        workbook_path=workbook,
                        prepare_apply=prepare,
                        complete_apply=complete,
                    )
                    second = drafts.apply_draft(
                        state,
                        draft_id="draft-approval",
                        workbook_path=workbook,
                        prepare_apply=prepare,
                        complete_apply=complete,
                    )
                self.assertEqual(second, first)
                prepare.assert_called_once()
                complete.assert_called_once_with(receipt, prepared)
            finally:
                projection.close()
                state.close()


class TestApplyRebuildApi(unittest.TestCase):
    def test_route_requires_typed_confirmation_and_uses_only_bound_lifecycle(self):
        with tempfile.TemporaryDirectory(prefix="wbm-apply-rebuild-api-") as raw:
            root = Path(raw)
            projection = dbmod.connect(root / "projection.sqlite3")
            state = dbmod.connect(root / "state.sqlite3", foreign_keys=True)
            dbmod.init_projection_schema(projection)
            dbmod.init_durable_schema(state)
            operation = {"model_id": "stingray", "model_context": ["stingray", "z06"]}
            rollback = object()
            receipt = {"ok": True, "status": "applied", "workbookState": "saved"}

            def invoke_bound_lifecycle(*_args, **kwargs):
                prepared = kwargs["prepare_apply"]()
                return kwargs["complete_apply"](receipt, prepared)

            try:
                with self.assertRaises(main.HTTPException) as confirmation:
                    main.apply_and_rebuild_draft(
                        "draft-1",
                        main.ApplyRebuildRequest(actor="Sean", confirm="wrong"),
                        _lock=None,
                        conn=projection,
                        state_conn=state,
                    )
                self.assertEqual(confirmation.exception.status_code, 422)

                with (
                    patch.object(main, "_workbook_state", return_value={"state": "current"}),
                    patch.object(main, "_projection_state", return_value={"state": "current"}),
                    patch.object(main.drafts, "list_operations", return_value=[operation]),
                    patch.object(main.apply_rebuild, "prepare_rollback_set", return_value=rollback) as prepare,
                    patch.object(main.apply_rebuild, "complete_apply_rebuild", return_value={"done": True}) as complete,
                    patch.object(main.drafts, "apply_draft", side_effect=invoke_bound_lifecycle) as apply_draft,
                ):
                    result = main.apply_and_rebuild_draft(
                        "draft-1",
                        main.ApplyRebuildRequest(
                            actor="Sean", confirm="APPLY AND REBUILD"
                        ),
                        _lock=None,
                        conn=projection,
                        state_conn=state,
                    )
                self.assertEqual(result, {"done": True})
                prepare.assert_called_once()
                self.assertEqual(prepare.call_args.kwargs["candidate_models"], ["stingray", "z06"])
                self.assertEqual(prepare.call_args.kwargs["requested_by"], "Sean")
                complete.assert_called_once()
                apply_draft.assert_called_once()
                self.assertIs(apply_draft.call_args.kwargs["workbook_path"], main.config.DEFAULT_WORKBOOK)
            finally:
                projection.close()
                state.close()

    def test_unknown_state_route_reuses_independent_manual_verifier(self):
        state = unittest.mock.Mock()
        expected = {"manager_state": "manually_resolved_restored"}
        with patch.object(main.drafts, "resolve_unknown_draft", return_value=expected) as resolve:
            result = main.resolve_unknown_draft(
                "draft-unknown",
                main.ManualResolutionRequest(
                    actor="Sean",
                    resolution="restored",
                    evidence={"ticket": "recovery-proof"},
                ),
                _lock=None,
                state_conn=state,
            )
        self.assertEqual(result, expected)
        resolve.assert_called_once_with(
            state,
            draft_id="draft-unknown",
            resolution="restored",
            workbook_path=main.config.DEFAULT_WORKBOOK,
            actor="Sean",
            evidence={"ticket": "recovery-proof"},
        )


if __name__ == "__main__":
    unittest.main()
