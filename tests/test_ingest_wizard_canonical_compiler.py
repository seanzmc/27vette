#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for entry in (ROOT / "scripts", ROOT / "tests"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from corvette_form_generator.editor_ops import EDITOR_SHEET_META  # noqa: E402
from corvette_form_generator.ingest.wizard.canonical_rows import canonical_bytes, semantic_hash, validate_artifact_graph  # noqa: E402
from corvette_form_generator.ingest.wizard.comparator_evidence import build_comparator_evidence  # noqa: E402
from corvette_form_generator.ingest.wizard.compiler import build_family_registry, compile_canonical_rows  # noqa: E402
from corvette_form_generator.ingest.wizard.decisions import model_scoped_statuses  # noqa: E402
from corvette_form_generator.ingest.wizard.identity import option_occurrence_signature  # noqa: E402
from corvette_form_generator.ingest.wizard.joiner import join_prices  # noqa: E402
from corvette_form_generator.ingest.wizard.parser import parse_confirmed_sheets  # noqa: E402
from ingest_wizard_fixtures import build_master_workbook, build_raw_export  # noqa: E402

ROLES = {
    "Equipment Groups 1": "exclude",
    "Equipment Groups 4": "options",
    "Price Schedule": "price",
    "Standard Equipment 1": "exclude",
    "Color and Trim 1": "exclude",
}


class CanonicalCompilerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.raw = build_raw_export(base / "raw.xlsx")
        self.master = build_master_workbook(base / "master.xlsx")
        from openpyxl import load_workbook
        raw_wb = load_workbook(self.raw)
        raw_wb["Equipment Groups 4"].append(["BV4", "", "Personalized Plaque", "A", "A"])
        raw_wb.save(self.raw)
        raw_wb.close()
        master_wb = load_workbook(self.master)
        master_wb["z06_options"].append(["opt_bv4_001", "BV4", 395, "Personalized Plaque", "Fixture endpoint", "", "sec_whee_001", True, 15, True, ""])
        master_wb["zr1_options"].append(["opt_bv4_001", "BV4", 395, "Personalized Plaque", "Existing target identity", "", "sec_whee_001", True, 20, False, ""])
        master_wb.save(self.master)
        master_wb.close()
        parsed = parse_confirmed_sheets(self.raw, ROLES)
        report = join_prices(parsed["candidates"], parsed["priceRows"])
        self.option_payload = {"schemaVersion": "pass-a-1", "candidates": parsed["candidates"], "skippedRows": parsed["skippedRows"]}
        self.price_payload = {"schemaVersion": "pass-a-1", "priceRows": parsed["priceRows"], "baseModelPriceRows": parsed["baseModelPriceRows"], "skippedPriceRows": parsed["skippedPriceRows"]}
        self.join_report = report
        self.roles_payload = {"schemaVersion": "pass-a-1", "roles": ROLES}
        self.selection = {"targets": ["zr1"], "comparators": {"zr1": "z06"}}
        authority_bindings = {"sourceSha256": "a" * 64, "workbookSha256": "b" * 64, "compilerPolicyVersion": "milestone-1-v1"}
        self.authority = {
            "fingerprint": hashlib.sha256(canonical_bytes(authority_bindings)).hexdigest(),
            "bindings": authority_bindings,
        }
        self.comparator = build_comparator_evidence(self.master, self.selection["comparators"], run_authority_fingerprint=self.authority)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def compile(self, **overrides):
        args = {
            "workbook_path": self.master,
            "option_payload": self.option_payload,
            "price_payload": self.price_payload,
            "join_report": self.join_report,
            "roles_payload": self.roles_payload,
            "selection": self.selection,
            "comparator_artifact": self.comparator,
            "run_authority_fingerprint": self.authority,
            "resolution_entries": [],
        }
        args.update(overrides)
        return compile_canonical_rows(**args)

    def test_family_registry_uses_roles_and_exact_live_headers(self) -> None:
        registry = build_family_registry(self.master, ["zr1"])
        self.assertEqual(registry["zr1"]["source_option_sheet"]["sheetName"], "zr1_options")
        self.assertEqual(registry["zr1"]["source_option_sheet"]["headers"][0], "option_id")
        self.assertIn("rule_group_members_sheet", registry["zr1"])

    def test_existing_option_id_is_reused_and_no_family_is_cleared(self) -> None:
        result = self.compile()
        rows = result["canonical-row-manifest.json"]["rows"]
        pdb = next(row for row in rows if row["family"] == "options" and row["values"].get("rpo") == "PDB")
        self.assertEqual(pdb["values"]["option_id"], "opt_pdb_001")
        self.assertNotIn("clear", {row["action"] for row in rows})
        self.assertTrue(all(row["action"] != "delete" for row in rows))

    def test_compilation_does_not_mutate_shared_candidate_input(self) -> None:
        before = copy.deepcopy(self.option_payload)
        self.compile()
        self.assertEqual(self.option_payload, before)

    def test_every_option_has_explicit_boolean_values(self) -> None:
        result = self.compile()
        options = [row for row in result["canonical-row-manifest.json"]["rows"] if row["family"] == "options" and row["status"] == "ready"]
        self.assertTrue(options)
        for row in options:
            self.assertIsInstance(row["values"]["active"], bool)
            self.assertIsInstance(row["values"]["selectable"], bool)
        bv4 = next(row for row in options if row["values"]["rpo"] == "BV4")
        self.assertEqual(bv4["values"]["price"], 395)

        variant = next(
            row
            for row in result["canonical-row-manifest.json"]["rows"]
            if row["family"] == "variant_master" and row["key"] == {"variant_id": "1lz_r07"}
        )
        self.assertEqual(variant["values"]["base_price"], 197195)
        self.assertIs(variant["values"]["active"], False)
        self.assertTrue(
            any(
                row["family"] == "model_variants"
                and row["key"] == {"model_key": "zr1", "variant_id": "1lz_r07"}
                for row in result["canonical-row-manifest.json"]["rows"]
            )
        )

    def test_every_source_feature_and_family_has_one_disposition(self) -> None:
        result = self.compile()
        report = result["compile-report.json"]
        feature_ids = [item["featureId"] for item in report["sourceFeatureCoverage"]]
        self.assertEqual(len(feature_ids), len(set(feature_ids)))
        self.assertTrue(
            {item["disposition"] for item in report["sourceFeatureCoverage"]}
            <= {
                "compiled",
                "retained_existing",
                "exception_open",
                "resolved_not_a_workbook_fact",
                "resolved_not_applicable",
                "allowed_deferral",
                "unsupported_blocker",
            }
        )
        self.assertTrue(any("Color and Trim 1" in item["featureId"] and item["disposition"] == "unsupported_blocker" for item in report["sourceFeatureCoverage"]))
        family_ids = [item["featureId"] for item in report["familyCoverage"]]
        self.assertEqual(len(family_ids), len(set(family_ids)))
        self.assertTrue(any(item["family"] == "interiors" for item in report["familyCoverage"]))
        for item in report["familyCoverage"]:
            if item["disposition"] != "retained_existing":
                continue
            self.assertTrue(
                any(
                    row["family"] == item["family"]
                    and row["model"] in {item["model"], "*"}
                    and row.get("disposition") == "retained_existing"
                    for row in result["canonical-row-manifest.json"]["rows"]
                ),
                item,
            )
        self.assertEqual(result["canonical-row-manifest.json"]["modelModes"]["zr1"], "reprocess")
        self.assertEqual(report["models"]["zr1"]["mode"], "reprocess")
        self.assertEqual(report["incomingReferenceImpact"]["status"], "no_deletions_proposed")
        self.assertTrue(report["incomingReferenceImpact"]["graphBuilt"])
        self.assertGreater(report["incomingReferenceImpact"]["referenceEdges"], 0)
        self.assertTrue(report["manifestCounts"])
        compiled_status_ids = {
            item["featureId"]
            for item in report["sourceFeatureCoverage"]
            if item["family"] == "ovs" and item["disposition"] == "compiled"
        }
        emitted_status_ids = {
            dependency["evidenceId"]
            for row in result["canonical-row-manifest.json"]["rows"]
            if row["family"] == "ovs" and row["status"] == "ready"
            for dependency in row["evidenceDependencies"]
            if str(dependency["evidenceId"]).startswith("status:")
        }
        self.assertEqual(compiled_status_ids, emitted_status_ids)
        self.assertTrue(
            all(
                row["values"].get("runtime_action") in {"", "replace"}
                for row in result["canonical-row-manifest.json"]["rows"]
                if row["family"] == "rule_mapping" and row["status"] == "ready"
            )
        )
        rule_signatures = {
            (row["model"], semantic_hash(row["semanticSignature"]))
            for row in result["canonical-row-manifest.json"]["rows"]
            if row["family"] == "rule_mapping" and row["status"] == "ready"
        }
        facts = {
            (target, fact["evidenceId"]): fact
            for target, entry in result["comparator-evidence.json"]["targets"].items()
            for fact in entry["facts"]
        }
        for item in report["comparatorDispositions"]:
            if item["disposition"] != "corroborated_target_match":
                continue
            fact = facts[(item["target"], item["evidenceId"])]
            signature = fact["signature"]
            normalized = {
                "sourceRpo": signature.get("sourceRpo"),
                "ruleType": signature.get("ruleType"),
                "targetRpo": signature.get("targetRpo"),
                "bodyStyleScope": signature.get("bodyStyleScope") or "*",
                "trimLevelScope": signature.get("trimLevelScope") or "*",
                "variantScope": signature.get("variantScope") or "*",
            }
            fingerprint = semantic_hash(normalized)
            self.assertTrue(
                (item["target"], fingerprint) in rule_signatures
                or ("*", fingerprint) in rule_signatures,
                item,
            )
        for field in (
            "targetEvidenceFingerprint",
            "comparatorEvidenceFingerprint",
            "phraseEvidenceFingerprint",
            "workbookEvidenceFingerprint",
        ):
            self.assertEqual(result["canonical-row-manifest.json"][field], result["exception-queue.json"][field])
        self.assertTrue(result["canonical-row-manifest.json"]["workbookEvidenceFingerprint"])
        self.assertTrue(all(result["canonical-row-manifest.json"]["targetEvidenceFingerprint"].values()))
        self.assertNotIn(
            semantic_hash([]),
            result["canonical-row-manifest.json"]["targetEvidenceFingerprint"].values(),
        )
        self.assertTrue(
            all(
                evidence_id == evidence_id.strip()
                for evidence_id in result["canonical-row-manifest.json"]["workbookEvidenceFingerprint"]
            )
        )
        for row in result["canonical-row-manifest.json"]["rows"]:
            for column, kind in EDITOR_SHEET_META.get(row["family"], {}).get("types", {}).items():
                if kind == "int" and row["values"].get(column) not in (None, ""):
                    self.assertIsInstance(row["values"][column], int)
                    self.assertNotIsInstance(row["values"][column], bool)


    def test_missing_section_and_conditional_price_are_typed_blockers(self) -> None:
        result = self.compile()
        reasons = {item["reasonCode"] for item in result["exception-queue.json"]["subjects"]}
        self.assertIn("missing_section", reasons)
        self.assertIn("unresolved_price_scope", reasons)
        self.assertEqual(result["compile-report.json"]["models"]["zr1"]["compileReady"], False)
        self.assertFalse(result["compile-report.json"]["models"]["zr1"]["planReady"])

    def test_artifact_graph_rejects_invalid_and_conflicting_current_resolutions(self) -> None:
        result = self.compile()
        malformed_queue = copy.deepcopy(result["exception-queue.json"])
        malformed_queue["subjects"][0]["reasonCode"] = "unknown_reason"
        malformed_queue["subjects"][0]["allowedActions"] = ["choose_section"]
        with self.assertRaisesRegex(ValueError, "does not support actions"):
            validate_artifact_graph(
                result["canonical-row-manifest.json"],
                result["compile-report.json"],
                result["comparator-evidence.json"],
                malformed_queue,
                result["exception-resolutions.json"],
            )
        cyclic_queue = copy.deepcopy(result["exception-queue.json"])
        cyclic_queue["resolutionSemanticSha"] = result["exception-resolutions.json"]["resolutionSemanticSha"]
        with self.assertRaisesRegex(ValueError, "may not depend on resolution state"):
            validate_artifact_graph(
                result["canonical-row-manifest.json"],
                result["compile-report.json"],
                result["comparator-evidence.json"],
                cyclic_queue,
                result["exception-resolutions.json"],
            )
        subject = next(
            item
            for item in result["exception-queue.json"]["subjects"]
            if item["reasonCode"] == "missing_section"
        )
        invalid_entry = {
            "subjectId": subject["subjectId"],
            "subjectVersion": subject["subjectVersion"],
            "action": "choose_section",
            "payload": {"sectionId": 7},
            "disposition": "resolved",
        }
        invalid = copy.deepcopy(result["exception-resolutions.json"])
        invalid["entries"] = [invalid_entry]
        invalid["validEntries"] = [invalid_entry]
        with self.assertRaisesRegex(ValueError, "non-empty string sectionId"):
            validate_artifact_graph(
                result["canonical-row-manifest.json"],
                result["compile-report.json"],
                result["comparator-evidence.json"],
                result["exception-queue.json"],
                invalid,
            )
        first = {**invalid_entry, "payload": {"sectionId": "sec_a"}}
        second = {**invalid_entry, "payload": {"sectionId": "sec_b"}}
        conflicting = copy.deepcopy(result["exception-resolutions.json"])
        conflicting["entries"] = [first, second]
        conflicting["validEntries"] = [first, second]
        with self.assertRaisesRegex(ValueError, "Conflicting current resolutions"):
            validate_artifact_graph(
                result["canonical-row-manifest.json"],
                result["compile-report.json"],
                result["comparator-evidence.json"],
                result["exception-queue.json"],
                conflicting,
            )

    def test_choose_section_resolution_is_consumed_into_manifest(self) -> None:
        first = self.compile()
        subject = next(
            item
            for item in first["exception-queue.json"]["subjects"]
            if item["reasonCode"] == "missing_section"
        )
        candidate_id = subject["evidenceReferences"][0]
        candidate = next(
            item
            for item in self.option_payload["candidates"]
            if option_occurrence_signature(
                {**item, "statuses": model_scoped_statuses(item, "zr1")}
            )
            == candidate_id
        )
        resolution = {
            "subjectId": subject["subjectId"],
            "subjectVersion": subject["subjectVersion"],
            "action": "choose_section",
            "payload": {"sectionId": "sec_whee_001"},
            "disposition": "resolved",
        }
        second = self.compile(resolution_entries=[resolution])
        option = next(
            row
            for row in second["canonical-row-manifest.json"]["rows"]
            if row["family"] == "options"
            and row["values"].get("rpo") == candidate.get("rpo")
            and row["values"].get("section_id") == "sec_whee_001"
        )
        self.assertEqual(option["status"], "ready")
        blocker_ids = {
            item["subjectId"]
            for item in second["compile-report.json"]["models"]["zr1"]["blockers"]
        }
        self.assertNotIn(subject["subjectId"], blocker_ids)

    def test_typed_price_scope_resolution_is_consumed_into_price_rule(self) -> None:
        first = self.compile()
        subject = next(
            item
            for item in first["exception-queue.json"]["subjects"]
            if item["reasonCode"] == "unresolved_price_scope"
        )
        resolution = {
            "subjectId": subject["subjectId"],
            "subjectVersion": subject["subjectVersion"],
            "action": "provide_typed_value",
            "payload": {"trimLevelScope": "1LT", "priceValue": 1234},
            "disposition": "resolved",
        }
        second = self.compile(resolution_entries=[resolution])
        price_rule = next(
            row
            for row in second["canonical-row-manifest.json"]["rows"]
            if row["family"] == "price_rules"
            and row["values"].get("trim_level_scope") == "1LT"
            and row["values"].get("price_value") == 1234
        )
        self.assertEqual(price_rule["status"], "ready")
        self.assertEqual(
            price_rule["values"]["condition_option_id"],
            price_rule["values"]["target_option_id"],
        )
        blocker_ids = {
            item["subjectId"]
            for item in second["compile-report.json"]["models"]["zr1"]["blockers"]
        }
        self.assertNotIn(subject["subjectId"], blocker_ids)

    def test_artifacts_are_deterministic_and_resolution_independent_queue(self) -> None:
        first = self.compile()
        second = self.compile()
        for name in ("comparator-evidence.json", "canonical-row-manifest.json", "exception-queue.json", "exception-resolutions.json", "compile-report.json"):
            self.assertEqual(canonical_bytes(first[name]), canonical_bytes(second[name]), name)
        self.assertNotIn("resolutionSemanticSha", canonical_bytes(first["exception-queue.json"]).decode())

    def test_compiler_refuses_join_report_drift(self) -> None:
        drifted = copy.deepcopy(self.join_report)
        drifted["exactMatches"] += 1
        with self.assertRaisesRegex(ValueError, "Join report exactMatches"):
            self.compile(join_report=drifted)

    def test_source_row_reorder_preserves_option_semantics(self) -> None:
        reordered = copy.deepcopy(self.option_payload)
        reordered["candidates"] = list(reversed(reordered["candidates"]))
        first = self.compile()["canonical-row-manifest.json"]
        second = self.compile(option_payload=reordered)["canonical-row-manifest.json"]
        first_options = {(row["values"].get("rpo"), semantic_hash(row["semanticSignature"])) for row in first["rows"] if row["family"] == "options"}
        second_options = {(row["values"].get("rpo"), semantic_hash(row["semanticSignature"])) for row in second["rows"] if row["family"] == "options"}
        self.assertEqual(first_options, second_options)

    def test_price_row_reorder_preserves_all_semantic_hashes(self) -> None:
        first = self.compile()
        reordered = copy.deepcopy(self.price_payload)
        reordered["priceRows"] = list(reversed(reordered["priceRows"]))
        reordered["baseModelPriceRows"] = list(reversed(reordered["baseModelPriceRows"]))
        second = self.compile(price_payload=reordered)
        self.assertEqual(
            first["exception-queue.json"]["queueSubjectFingerprint"],
            second["exception-queue.json"]["queueSubjectFingerprint"],
        )
        self.assertEqual(
            first["canonical-row-manifest.json"]["manifestSemanticSha"],
            second["canonical-row-manifest.json"]["manifestSemanticSha"],
        )
        self.assertEqual(
            first["compile-report.json"]["compileReportSemanticSha"],
            second["compile-report.json"]["compileReportSemanticSha"],
        )

    def test_comparator_fact_reorder_preserves_compile_report_semantics(self) -> None:
        first = self.compile()
        reordered = copy.deepcopy(self.comparator)
        for entry in reordered["targets"].values():
            entry["facts"] = list(reversed(entry["facts"]))
        second = self.compile(comparator_artifact=reordered)
        self.assertEqual(
            first["compile-report.json"]["compileReportSemanticSha"],
            second["compile-report.json"]["compileReportSemanticSha"],
        )

    def test_source_coordinate_drift_preserves_subject_and_derivation_semantics(self) -> None:
        shifted = copy.deepcopy(self.option_payload)
        for index, candidate in enumerate(shifted["candidates"], start=100):
            sheet = str(candidate["candidateId"]).split(":", 1)[0]
            candidate["candidateId"] = f"{sheet}:{index}"
            candidate["rowIndex"] = index
        first = self.compile()
        second = self.compile(option_payload=shifted)
        self.assertEqual(
            first["canonical-row-manifest.json"]["manifestSemanticSha"],
            second["canonical-row-manifest.json"]["manifestSemanticSha"],
        )
        self.assertEqual(
            first["exception-queue.json"]["queueSubjectFingerprint"],
            second["exception-queue.json"]["queueSubjectFingerprint"],
        )
        self.assertEqual(
            first["compile-report.json"]["compileReportSemanticSha"],
            second["compile-report.json"]["compileReportSemanticSha"],
        )

    def test_comparator_price_never_populates_target_option(self) -> None:
        result = self.compile()
        bv4 = next(row for row in result["canonical-row-manifest.json"]["rows"] if row["family"] == "options" and row["values"].get("rpo") == "BV4")
        self.assertEqual(bv4["values"]["price"], 395)
        self.assertNotEqual(bv4["values"]["price"], 500)


if __name__ == "__main__":
    unittest.main()
