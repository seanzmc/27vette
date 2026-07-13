#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from corvette_form_generator.ingest.wizard.canonical_rows import (  # noqa: E402
    COMPILER_POLICY_VERSION,
    build_compile_report,
    build_exception_queue,
    build_manifest,
    canonical_bytes,
    derivation_version,
    semantic_hash,
    subject_id,
    subject_version,
    validate_artifact_graph,
)


class CanonicalRowsContractTest(unittest.TestCase):
    def setUp(self) -> None:
        bindings = {"sha256": "a" * 64, "mtimeNs": 123, "compilerPolicyVersion": COMPILER_POLICY_VERSION}
        self.authority = {
            "fingerprint": hashlib.sha256(canonical_bytes(bindings)).hexdigest(),
            "bindings": bindings,
        }
        self.dependencies = [
            {"evidenceId": "target:zr1:rpo:PDB", "semanticFingerprint": "1" * 64},
            {"evidenceId": "phrase:included with", "semanticFingerprint": "2" * 64},
        ]

    def test_canonical_bytes_are_stable_and_compact(self) -> None:
        self.assertEqual(canonical_bytes({"b": [2, 1], "a": True}), b'{"a":true,"b":[2,1]}\n')

    def test_subject_identity_is_independent_of_evidence_revision(self) -> None:
        first = subject_id("zr1", "relationship_direction", ["PDB", "PEF"])
        second = subject_id("zr1", "relationship_direction", ["PDB", "PEF"])
        self.assertEqual(first, second)
        self.assertEqual(len(first.split(":")[-1]), 16)

    def test_subject_version_depends_only_on_declared_semantic_dependencies(self) -> None:
        sid = subject_id("zr1", "relationship_direction", ["PDB", "PEF"])
        before = subject_version(sid, self.dependencies)
        authority_only = dict(self.authority, mtimeNs=999)
        after = subject_version(sid, self.dependencies)
        self.assertEqual(before, after)
        self.assertNotIn(semantic_hash(authority_only), before)
        changed = [dict(self.dependencies[0], semanticFingerprint="3" * 64), self.dependencies[1]]
        self.assertNotEqual(before, subject_version(sid, changed))

    def test_derivation_version_is_dependency_scoped(self) -> None:
        signature = {"family": "options", "model": "zr1", "rpo": "PDB", "values": {"price": 16000}}
        self.assertEqual(
            derivation_version(signature, self.dependencies),
            derivation_version(signature, list(reversed(self.dependencies))),
        )
        self.assertNotEqual(
            derivation_version(signature, self.dependencies),
            derivation_version(dict(signature, rpo="BV4"), self.dependencies),
        )

    def test_queue_has_no_resolution_dependency(self) -> None:
        sid = subject_id("zr1", "missing_scope", ["PDB"])
        subject = {
            "subjectId": sid,
            "exceptionId": f"exception:{sid}",
            "subjectVersion": subject_version(sid, self.dependencies),
            "model": "zr1",
            "family": "price_rules",
            "severity": "blocking",
            "reasonCode": "missing_scope",
            "allowedActions": ["provide_typed_value"],
            "proposedRows": [],
            "evidenceDependencies": self.dependencies,
            "evidenceReferences": ["Price Schedule!E12"],
            "gateImpact": ["compileReady"],
        }
        queue = build_exception_queue(self.authority, "c" * 64, [subject])
        self.assertEqual(queue["schemaVersion"], "exception-queue-1")
        self.assertNotIn("resolutionSemanticSha", canonical_bytes(queue).decode())
        self.assertEqual(queue["subjects"][0]["subjectId"], sid)

    def test_manifest_and_report_bind_only_upstream_artifacts(self) -> None:
        row = {
            "model": "zr1",
            "family": "options",
            "sheet": "zr1_options",
            "action": "add",
            "key": {"option_id": "opt_pdb_001"},
            "values": {"option_id": "opt_pdb_001", "rpo": "PDB", "price": 16000, "selectable": True, "active": False},
            "semanticSignature": "sig",
            "evidenceDependencies": self.dependencies,
            "derivationVersion": derivation_version("sig", self.dependencies),
            "status": "ready",
        }
        manifest = build_manifest(self.authority, "c" * 64, "q" * 64, "r" * 64, [row])
        report = build_compile_report(
            self.authority,
            "c" * 64,
            "q" * 64,
            "r" * 64,
            manifest["manifestSemanticSha"],
            {"zr1": {"compileReady": True, "planReady": False, "writeReady": False, "deploymentReady": False, "blockers": []}},
            [],
            [],
        )
        self.assertEqual(manifest["schemaVersion"], "canonical-rows-1")
        self.assertEqual(report["schemaVersion"], "compile-report-1")
        validate_artifact_graph(manifest, report)

    def test_artifact_graph_recomputes_hashes_and_authority(self) -> None:
        row = {
            "model": "zr1",
            "family": "options",
            "sheet": "zr1_options",
            "action": "add",
            "key": {"option_id": "opt_pdb_001"},
            "values": {"option_id": "opt_pdb_001", "price": 16000},
            "semanticSignature": "sig",
            "evidenceDependencies": self.dependencies,
            "derivationVersion": derivation_version("sig", self.dependencies),
            "status": "ready",
        }
        manifest = build_manifest(self.authority, "c" * 64, "q" * 64, "r" * 64, [row])
        report = build_compile_report(
            self.authority,
            "c" * 64,
            "q" * 64,
            "r" * 64,
            manifest["manifestSemanticSha"],
            {"zr1": {"compileReady": False, "planReady": False, "writeReady": False, "deploymentReady": False, "blockers": []}},
            [],
            [],
        )
        tampered = copy.deepcopy(manifest)
        tampered["rows"][0]["values"]["price"] = 1
        with self.assertRaisesRegex(ValueError, "manifest semantic hash"):
            validate_artifact_graph(tampered, report)
        enum_tampered = copy.deepcopy(manifest)
        enum_tampered["rows"][0]["family"] = "rule_mapping"
        enum_tampered["rows"][0]["values"]["runtime_action"] = "block"
        with self.assertRaisesRegex(ValueError, "Canonical enum"):
            validate_artifact_graph(enum_tampered, report)
        mixed_report = copy.deepcopy(report)
        mixed_bindings = {"sha256": "b" * 64}
        mixed_report["runAuthorityFingerprint"] = {
            "fingerprint": hashlib.sha256(canonical_bytes(mixed_bindings)).hexdigest(),
            "bindings": mixed_bindings,
        }
        with self.assertRaisesRegex(ValueError, "mixed runAuthorityFingerprint"):
            validate_artifact_graph(manifest, mixed_report)

        with self.assertRaisesRegex(ValueError, "contradicts its blocker list"):
            build_compile_report(
                self.authority,
                "c" * 64,
                "q" * 64,
                "r" * 64,
                manifest["manifestSemanticSha"],
                {"zr1": {"compileReady": True, "planReady": False, "writeReady": False, "deploymentReady": False, "blockers": [{"subjectId": "blocked"}]}},
                [],
                [],
            )

        with self.assertRaisesRegex(ValueError, "contradicts blocking coverage"):
            build_compile_report(
                self.authority,
                "c" * 64,
                "q" * 64,
                "r" * 64,
                manifest["manifestSemanticSha"],
                {"zr1": {"compileReady": True, "planReady": False, "writeReady": False, "deploymentReady": False, "blockers": []}},
                [{"featureId": "source:1", "model": "zr1", "disposition": "unsupported_blocker"}],
                [],
            )

    def test_shared_sheet_keys_are_globally_unique(self) -> None:
        rows = []
        for model in ("grand_sport_x", "zr1"):
            signature = {"model": model, "rule": "same"}
            rows.append(
                {
                    "model": model,
                    "family": "rule_mapping",
                    "sheet": "z06_rule_mapping",
                    "action": "add",
                    "key": {"rule_id": "rule_same"},
                    "values": {"rule_id": "rule_same"},
                    "semanticSignature": signature,
                    "evidenceDependencies": self.dependencies,
                    "derivationVersion": derivation_version(signature, self.dependencies),
                    "status": "ready",
                }
            )
        with self.assertRaisesRegex(ValueError, "Duplicate canonical workbook keys"):
            build_manifest(self.authority, "c" * 64, "q" * 64, "r" * 64, rows)

    def test_semantic_hash_excludes_authority_and_audit_fields(self) -> None:
        base = {"values": {"rpo": "PDB"}, "runAuthorityFingerprint": "x", "generatedAt": "a", "reviewer": "one", "rowIndex": 10, "columnLetter": "D"}
        changed = {"values": {"rpo": "PDB"}, "runAuthorityFingerprint": "y", "generatedAt": "b", "reviewer": "two", "rowIndex": 99, "columnLetter": "Z"}
        self.assertEqual(semantic_hash(base), semantic_hash(changed))


if __name__ == "__main__":
    unittest.main()
