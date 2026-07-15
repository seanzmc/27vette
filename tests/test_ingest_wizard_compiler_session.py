#!/usr/bin/env python3
from __future__ import annotations

import importlib
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for entry in (ROOT / "scripts", ROOT / "tests"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from corvette_form_generator.ingest.wizard.canonical_rows import canonical_bytes  # noqa: E402
from corvette_form_generator.ingest.wizard.session import (  # noqa: E402
    COMPILER_ARTIFACTS,
    STATE_COMPILED_WITH_EXCEPTIONS,
    WizardError,
    WizardSessionStore,
    read_json,
    replace_json_artifact_set,
    write_json,
)
from corvette_form_generator.ingest.wizard.identity import option_occurrence_signature  # noqa: E402
from corvette_form_generator.ingest.wizard.decisions import model_scoped_statuses  # noqa: E402
from ingest_wizard_fixtures import build_master_workbook, build_raw_export  # noqa: E402

ROLES = {
    "Exterior 1": "exclude",
    "Mechanical 4": "options",
    "Price Schedule": "price",
    "Standard Equipment 1": "exclude",
    "Color and Trim 1": "exclude",
}


class CompilerSessionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        build_raw_export(self.root / "raw.xlsx")
        build_master_workbook(self.root / "stingray_master.xlsx")
        self.store = WizardSessionStore(self.root)
        self.run_id = self.store.create_session("raw.xlsx")["session"]["runId"]
        self.store.confirm_roles(self.run_id, ROLES)
        self.store.run_parse(self.run_id)
        self.store.select_models(self.run_id, ["zr1"], {"zr1": "z06"})
        self.run_dir = self.store.run_dir(self.run_id)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_compile_persists_coherent_set_and_explicit_state(self) -> None:
        result = self.store.compile_canonical_rows(self.run_id)
        self.assertEqual(result["session"]["state"], STATE_COMPILED_WITH_EXCEPTIONS)
        for name in COMPILER_ARTIFACTS:
            self.assertTrue((self.run_dir / name).is_file(), name)
        self.assertTrue((self.run_dir / "exception-log.jsonl").is_file())
        self.assertFalse(result["compileReport"]["models"]["zr1"]["planReady"])
        detail = self.store.compiler_detail(self.run_id)
        self.assertEqual(
            detail["manifest"]["manifestSemanticSha"],
            result["manifest"]["manifestSemanticSha"],
        )
        authority_bindings = result["manifest"]["runAuthorityFingerprint"]["bindings"]
        self.assertTrue(authority_bindings["modelWorkbookSources"])
        self.assertTrue(authority_bindings["rulePhraseMap"])

    def test_compile_refuses_downstream_plan_evidence(self) -> None:
        (self.run_dir / "apply-plan.json").write_text("{}\n")
        with self.assertRaisesRegex(WizardError, "downstream plan/apply evidence"):
            self.store.compile_canonical_rows(self.run_id)
        self.assertFalse((self.run_dir / "canonical-row-manifest.json").exists())

    def test_compile_refuses_future_downstream_artifact_names(self) -> None:
        for name in ("write-approval-v2.json", "writeapproval-v3.json", "apply-report-copy.json", "deployment-promotion-note.json"):
            with self.subTest(name=name):
                path = self.run_dir / name
                path.write_text("{}\n")
                with self.assertRaisesRegex(WizardError, "downstream plan/apply evidence"):
                    self.store.compile_canonical_rows(self.run_id)
                path.unlink()

    def test_compile_refuses_nonempty_legacy_decisions(self) -> None:
        decisions = read_json(self.run_dir / "decisions.json")
        decisions["decisions"] = {"legacy": {"action": "assign_section"}}
        write_json(self.run_dir / "decisions.json", decisions)
        with self.assertRaisesRegex(WizardError, "nonempty decisions.json"):
            self.store.compile_canonical_rows(self.run_id)

    def test_compiler_detail_rejects_mixed_artifact_generation(self) -> None:
        self.store.compile_canonical_rows(self.run_id)
        manifest = read_json(self.run_dir / "canonical-row-manifest.json")
        manifest["queueSubjectFingerprint"] = "stale"
        write_json(self.run_dir / "canonical-row-manifest.json", manifest)
        with self.assertRaisesRegex(WizardError, "Artifact graph mismatch"):
            self.store.compiler_detail(self.run_id)

    def test_compiler_detail_rejects_coherent_authority_not_bound_to_session(self) -> None:
        self.store.compile_canonical_rows(self.run_id)
        manifest = read_json(self.run_dir / "canonical-row-manifest.json")
        bindings = dict(manifest["runAuthorityFingerprint"]["bindings"])
        bindings["compilerPolicyVersion"] = "fabricated-policy"
        authority = {
            "fingerprint": hashlib.sha256(canonical_bytes(bindings)).hexdigest(),
            "bindings": bindings,
        }
        for name in COMPILER_ARTIFACTS:
            artifact = read_json(self.run_dir / name)
            artifact["runAuthorityFingerprint"] = authority
            write_json(self.run_dir / name, artifact)
        with self.assertRaisesRegex(WizardError, "bindings do not match session state"):
            self.store.compiler_detail(self.run_id)

    def test_artifact_set_replacement_rolls_back_on_partial_failure(self) -> None:
        write_json(self.run_dir / "a.json", {"value": "old-a"})
        write_json(self.run_dir / "b.json", {"value": "old-b"})
        before = {name: (self.run_dir / name).read_bytes() for name in ("a.json", "b.json")}
        session_module = importlib.import_module(
            "corvette_form_generator.ingest.wizard.session"
        )

        real_replace = session_module.os.replace
        calls = 0

        def fail_second(source: Path, target: Path) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("fixture interruption")
            real_replace(source, target)

        with mock.patch.object(session_module.os, "replace", side_effect=fail_second):
            with self.assertRaisesRegex(OSError, "fixture interruption"):
                replace_json_artifact_set(
                    self.run_dir,
                    {"a.json": {"value": "new-a"}, "b.json": {"value": "new-b"}},
                )
        self.assertEqual(
            before,
            {name: (self.run_dir / name).read_bytes() for name in ("a.json", "b.json")},
        )

    def test_unchanged_recompile_is_byte_stable_and_no_audit_append(self) -> None:
        self.store.compile_canonical_rows(self.run_id)
        before = {name: (self.run_dir / name).read_bytes() for name in COMPILER_ARTIFACTS}
        inodes_before = {name: (self.run_dir / name).stat().st_ino for name in COMPILER_ARTIFACTS}
        log_before = (self.run_dir / "exception-log.jsonl").read_bytes()
        self.store.compile_canonical_rows(self.run_id)
        after = {name: (self.run_dir / name).read_bytes() for name in COMPILER_ARTIFACTS}
        self.assertEqual(before, after)
        self.assertEqual(
            inodes_before,
            {name: (self.run_dir / name).stat().st_ino for name in COMPILER_ARTIFACTS},
        )
        self.assertEqual(log_before, (self.run_dir / "exception-log.jsonl").read_bytes())

    def test_source_reparse_evicts_aggregate_cache_and_preserves_resolutions(self) -> None:
        self.store.compile_canonical_rows(self.run_id)
        self.store.run_parse(self.run_id)
        self.assertTrue((self.run_dir / "exception-resolutions.json").is_file())
        for name in COMPILER_ARTIFACTS:
            if name != "exception-resolutions.json":
                self.assertFalse((self.run_dir / name).exists(), name)

    def test_reselect_invalidates_aggregate_cache_but_preserves_resolutions_and_log(self) -> None:
        self.store.compile_canonical_rows(self.run_id)
        resolutions = self.run_dir / "exception-resolutions.json"
        log = self.run_dir / "exception-log.jsonl"
        self.store.select_models(self.run_id, ["zr1"], {"zr1": "z06"})
        self.assertTrue(resolutions.is_file())
        self.assertTrue(log.is_file())
        for name in COMPILER_ARTIFACTS:
            if name != "exception-resolutions.json":
                self.assertFalse((self.run_dir / name).exists(), name)

    def test_compile_refuses_stale_selection_binding(self) -> None:
        payload = read_json(self.run_dir / "option-candidates.json")
        payload["candidates"][0]["description"] += " changed"
        write_json(self.run_dir / "option-candidates.json", payload)
        with self.assertRaisesRegex(WizardError, "re-select"):
            self.store.compile_canonical_rows(self.run_id)
        self.assertFalse((self.run_dir / "canonical-row-manifest.json").exists())

    def test_stale_resolution_transition_is_logged_once(self) -> None:
        self.store.compile_canonical_rows(self.run_id)
        queue = read_json(self.run_dir / "exception-queue.json")
        subject = next(
            item
            for item in queue["subjects"]
            if item["model"] == "zr1"
            and item["allowedActions"]
            and any(":candidate:" in dep["evidenceId"] for dep in item["evidenceDependencies"])
        )
        candidate_id = next(
            dep["evidenceId"].split(":candidate:", 1)[1]
            for dep in subject["evidenceDependencies"]
            if ":candidate:" in dep["evidenceId"]
        )
        resolution = read_json(self.run_dir / "exception-resolutions.json")
        action = subject["allowedActions"][0]
        payload = (
            {"sectionId": "sec_whee_001"}
            if action == "choose_section"
            else {"bodyStyleScope": "coupe"}
        )
        resolution["entries"] = [{
            "subjectId": subject["subjectId"],
            "subjectVersion": subject["subjectVersion"],
            "action": action,
            "payload": payload,
            "disposition": "resolved",
            "reviewer": "test",
            "resolvedAt": "2026-07-13T00:00:00Z",
        }]
        write_json(self.run_dir / "exception-resolutions.json", resolution)
        self.store.compile_canonical_rows(self.run_id)
        candidates = read_json(self.run_dir / "option-candidates.json")
        candidate = next(
            item
            for item in candidates["candidates"]
            if option_occurrence_signature(
                {**item, "statuses": model_scoped_statuses(item, "zr1")}
            )
            == candidate_id
        )
        candidate["sectionLabel"] = f"{candidate.get('sectionLabel') or ''} evidence revision"
        write_json(self.run_dir / "option-candidates.json", candidates)
        self.store.select_models(self.run_id, ["zr1"], {"zr1": "z06"})
        self.store.compile_canonical_rows(self.run_id)
        lines = [json.loads(line) for line in (self.run_dir / "exception-log.jsonl").read_text().splitlines() if line]
        stale = [line for line in lines if line["eventType"] == "resolution_became_stale"]
        self.assertEqual(len(stale), 1)
        recorded = [line for line in lines if line["eventType"] == "resolution_recorded"]
        self.assertEqual(len(recorded), 1)
        self.store.compile_canonical_rows(self.run_id)
        lines_again = [json.loads(line) for line in (self.run_dir / "exception-log.jsonl").read_text().splitlines() if line]
        self.assertEqual(lines, lines_again)


if __name__ == "__main__":
    unittest.main()
