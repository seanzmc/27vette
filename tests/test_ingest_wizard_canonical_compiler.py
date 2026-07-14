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

    def compile_with_ready_comparator_relationship(self, **overrides):
        preliminary = self.compile()
        subject = next(
            item
            for item in preliminary["exception-queue.json"]["subjects"]
            if item["reasonCode"] == "comparator_only_relationship_proposal"
        )
        proposal = subject["proposedRows"][0]
        required_rpos = {proposal["sourceRpo"], proposal["targetRpo"]}
        option_payload = copy.deepcopy(self.option_payload)
        price_payload = copy.deepcopy(self.price_payload)
        for candidate in option_payload["candidates"]:
            if candidate.get("rpo") in required_rpos:
                candidate["sectionLabel"] = "Wheels"
                candidate["priceMatch"] = None
                candidate["listPrice"] = None
                candidate["priceRows"] = []
        price_payload["priceRows"] = [
            row
            for row in price_payload["priceRows"]
            if str(row.get("rpo") or "").upper() not in required_rpos
        ]
        join_report = join_prices(option_payload["candidates"], price_payload["priceRows"])
        result = self.compile(
            option_payload=option_payload,
            price_payload=price_payload,
            join_report=join_report,
            **overrides,
        )
        current_subject = next(
            item
            for item in result["exception-queue.json"]["subjects"]
            if item["reasonCode"] == "comparator_only_relationship_proposal"
            and item["proposedRows"] == subject["proposedRows"]
        )
        return option_payload, price_payload, join_report, result, current_subject

    def test_family_registry_uses_roles_and_exact_live_headers(self) -> None:
        registry = build_family_registry(self.master, ["zr1"])
        self.assertEqual(registry["zr1"]["source_option_sheet"]["sheetName"], "zr1_options")
        self.assertEqual(registry["zr1"]["source_option_sheet"]["headers"][0], "option_id")
        self.assertIn("rule_group_members_sheet", registry["zr1"])

    def test_selected_comparator_compiles_shared_color_interior_and_presentation_profiles(self) -> None:
        from openpyxl import load_workbook

        workbook = load_workbook(self.master)
        workbook.save(self.master)
        workbook.close()

        result = self.compile()
        rows = result["canonical-row-manifest.json"]["rows"]
        subjects = result["exception-queue.json"]["subjects"]

        paint = next(
            row
            for row in rows
            if row["model"] == "zr1"
            and row["family"] == "options"
            and row["values"].get("rpo") == "GBA"
        )
        self.assertEqual(paint["values"]["option_id"], "opt_gba_001")
        self.assertEqual(
            {
                row["values"]["variant_id"]
                for row in rows
                if row["model"] == "zr1"
                and row["family"] == "ovs"
                and row["values"].get("option_id") == "opt_gba_001"
            },
            {"1lz_r07", "3lz_r67"},
        )
        self.assertEqual(
            {
                (row["values"]["interior_id"], row["values"]["trim_level"])
                for row in rows
                if row["model"] == "zr1" and row["family"] == "model_interior_scope"
            },
            {("1LZ_AQ9_HTA", "1LZ"), ("3LZ_AQ9_HTA", "3LZ")},
        )
        self.assertEqual(
            {
                row["values"]["interior_id"]
                for row in rows
                if row["model"] == "zr1" and row["family"] == "interior_components"
            },
            {"1LZ_AQ9_HTA", "3LZ_AQ9_HTA"},
        )
        color_override = next(
            row
            for row in rows
            if row["family"] == "color_overrides"
            and row["values"].get("interior_id") == "3LZ_AQ9_HTA"
        )
        self.assertEqual(color_override["values"]["option_id"], "opt_gba_001")
        self.assertEqual(color_override["values"]["rule_type"], "requires")
        for family in (
            "runtime_steps_meta",
            "section_presentation_meta",
            "context_section_master_meta",
            "order_summary_sections_meta",
            "step_order_summary_map_meta",
        ):
            self.assertTrue(
                any(row["model"] == "zr1" and row["family"] == family for row in rows),
                family,
            )
        self.assertFalse(
            any(subject["reasonCode"] == "unsupported_color_trim_source" for subject in subjects)
        )
        compiled_global_families = {
            "model_master",
            "model_workbook_sources",
            "model_interior_scope",
            "interior_components",
            "runtime_steps_meta",
            "section_presentation_meta",
            "context_section_master_meta",
            "order_summary_sections_meta",
            "step_order_summary_map_meta",
        }
        self.assertFalse(
            any(
                subject["reasonCode"] == "unsupported_global_family"
                and subject["model"] == "zr1"
                and subject["family"] in compiled_global_families
                for subject in subjects
            )
        )

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

    def test_status_bearing_no_rpo_standard_candidate_compiles_to_option_and_ovs(self) -> None:
        from openpyxl import load_workbook

        workbook = load_workbook(self.master)
        workbook["zr1_options"].append(
            [
                "opt_std_existing",
                "",
                0,
                "Air filtration system with pollen filter",
                "",
                "Air filtration system with pollen filter",
                "sec_whee_001",
                False,
                40,
                False,
                "",
            ]
        )
        workbook.save(self.master)
        workbook.close()
        option_payload = copy.deepcopy(self.option_payload)
        option_payload["candidates"].append(
            {
                "candidateId": "Interior 5:4",
                "sheetName": "Interior 5",
                "rowIndex": 4,
                "modelFamily": "ZR1",
                "modelFamilies": ["ZR1"],
                "sectionLabel": "Wheels",
                "rowKind": "standard_no_rpo",
                "rpo": "",
                "refOnlyRpo": "",
                "description": "Air filtration system with pollen filter",
                "statuses": [
                    {
                        "columnLetter": "D",
                        "variantLabel": "ZR1 Coupe",
                        "modelCode": "1YR07",
                        "trim": "1LZ",
                        "bodyStyle": "coupe",
                        "raw": "S",
                        "status": "standard",
                        "disclosureMarker": "",
                        "flags": [],
                    }
                ],
                "sourceEvidence": {
                    "sheetName": "Interior 5",
                    "rowIndex": 4,
                    "cells": {"C4": "Air filtration system with pollen filter", "D4": "S"},
                },
                "priceMatch": None,
                "listPrice": None,
                "priceRows": [],
            }
        )

        result = self.compile(option_payload=option_payload)
        rows = result["canonical-row-manifest.json"]["rows"]
        option = next(
            row
            for row in rows
            if row["family"] == "options"
            and row["values"].get("option_name") == "Air filtration system with pollen filter"
        )

        self.assertEqual(option["values"]["option_id"], "opt_std_existing")
        self.assertIs(option["values"]["active"], True)
        self.assertIs(option["values"]["selectable"], False)
        ovs = next(
            row
            for row in rows
            if row["family"] == "ovs"
            and row["values"].get("option_id") == option["values"]["option_id"]
        )
        self.assertEqual(ovs["values"]["status"], "standard")
        self.assertFalse(
            any(
                subject["reasonCode"] == "unsupported_source_feature"
                and "Interior 5:4" in subject.get("evidenceReferences", [])
                for subject in result["exception-queue.json"]["subjects"]
            )
        )

    def test_retain_existing_resolution_consumes_one_ambiguous_option_identity(self) -> None:
        from openpyxl import load_workbook

        workbook = load_workbook(self.master)
        for option_id in ("opt_dup_001", "opt_dup_002"):
            workbook["zr1_options"].append(
                [option_id, "DUP", 0, "Duplicate identity", "", "", "sec_whee_001", False, 30, False, ""]
            )
        workbook.save(self.master)
        workbook.close()

        option_payload = copy.deepcopy(self.option_payload)
        option_payload["candidates"].append(
            {
                "candidateId": "Equipment Groups 4:99",
                "sheetName": "Equipment Groups 4",
                "rowIndex": 99,
                "modelFamily": "ZR1",
                "modelFamilies": ["ZR1"],
                "sectionLabel": "Wheels",
                "rowKind": "orderable",
                "rpo": "DUP",
                "refOnlyRpo": "",
                "description": "Duplicate identity",
                "statuses": [
                    {
                        "columnLetter": "D",
                        "variantLabel": "ZR1 Coupe",
                        "modelCode": "1YR07",
                        "trim": "1LZ",
                        "bodyStyle": "coupe",
                        "raw": "A",
                        "status": "available",
                        "disclosureMarker": "",
                        "flags": [],
                    }
                ],
                "sourceEvidence": {
                    "sheetName": "Equipment Groups 4",
                    "rowIndex": 99,
                    "cells": {"A99": "DUP", "C99": "Duplicate identity", "D99": "A"},
                },
                "priceMatch": None,
                "listPrice": None,
                "priceRows": [],
            }
        )

        first = self.compile(option_payload=option_payload)
        subject = next(
            item
            for item in first["exception-queue.json"]["subjects"]
            if item["reasonCode"] == "ambiguous_existing_identity"
            and item["model"] == "zr1"
        )
        self.assertEqual(subject["allowedActions"], ["retain_existing"])
        self.assertEqual(
            {row["existingId"] for row in subject["proposedRows"]},
            {"opt_dup_001", "opt_dup_002"},
        )
        resolution = {
            "subjectId": subject["subjectId"],
            "subjectVersion": subject["subjectVersion"],
            "action": "retain_existing",
            "payload": {"existingId": "opt_dup_002"},
            "disposition": "retained_existing",
        }

        second = self.compile(option_payload=option_payload, resolution_entries=[resolution])
        option = next(
            row
            for row in second["canonical-row-manifest.json"]["rows"]
            if row["family"] == "options"
            and row["values"].get("rpo") == "DUP"
            and any(
                dep["evidenceId"] == f"resolution:{subject['subjectId']}"
                for dep in row["evidenceDependencies"]
            )
        )
        self.assertEqual(option["values"]["option_id"], "opt_dup_002")
        self.assertTrue(
            any(
                dep["evidenceId"] == f"resolution:{subject['subjectId']}"
                for dep in option["evidenceDependencies"]
            )
        )
        self.assertNotIn(
            subject["subjectId"],
            {
                blocker["subjectId"]
                for blocker in second["compile-report.json"]["models"]["zr1"]["blockers"]
            },
        )

    def test_choose_relationship_resolution_materializes_direct_rule(self) -> None:
        option_payload, price_payload, join_report, first, subject = (
            self.compile_with_ready_comparator_relationship()
        )
        option_rows = [
            row
            for row in first["canonical-row-manifest.json"]["rows"]
            if row["family"] == "options" and row["status"] == "ready"
        ]
        pdb_id = next(row["values"]["option_id"] for row in option_rows if row["values"].get("rpo") == "PDB")
        bv4_id = next(row["values"]["option_id"] for row in option_rows if row["values"].get("rpo") == "BV4")
        resolution = {
            "subjectId": subject["subjectId"],
            "subjectVersion": subject["subjectVersion"],
            "action": "choose_relationship",
            "payload": {
                "sourceOptionId": pdb_id,
                "ruleType": "requires",
                "targetOptionId": bv4_id,
            },
            "disposition": "resolved",
        }

        second = self.compile(
            option_payload=option_payload,
            price_payload=price_payload,
            join_report=join_report,
            resolution_entries=[resolution],
        )
        rule = next(
            row
            for row in second["canonical-row-manifest.json"]["rows"]
            if row["family"] == "rule_mapping"
            and row["values"].get("source_id") == pdb_id
            and row["values"].get("target_id") == bv4_id
        )
        self.assertEqual(rule["values"]["rule_type"], "requires")
        self.assertTrue(
            any(
                dep["evidenceId"] == f"resolution:{subject['subjectId']}"
                for dep in rule["evidenceDependencies"]
            )
        )
        self.assertNotIn(
            subject["subjectId"],
            {
                blocker["subjectId"]
                for blocker in second["compile-report.json"]["models"]["zr1"]["blockers"]
            },
        )

    def test_mark_not_applicable_consumes_comparator_proposal_without_a_row(self) -> None:
        option_payload, price_payload, join_report, _, subject = (
            self.compile_with_ready_comparator_relationship()
        )
        resolution = {
            "subjectId": subject["subjectId"],
            "subjectVersion": subject["subjectVersion"],
            "action": "mark_not_applicable",
            "payload": {"reason": "Target order guide does not establish this comparator rule."},
            "disposition": "resolved_not_applicable",
        }

        second = self.compile(
            option_payload=option_payload,
            price_payload=price_payload,
            join_report=join_report,
            resolution_entries=[resolution],
        )
        self.assertNotIn(
            subject["subjectId"],
            {
                blocker["subjectId"]
                for blocker in second["compile-report.json"]["models"]["zr1"]["blockers"]
            },
        )
        self.assertFalse(
            any(
                dep["evidenceId"] == f"resolution:{subject['subjectId']}"
                for row in second["canonical-row-manifest.json"]["rows"]
                for dep in row["evidenceDependencies"]
            )
        )
        self.assertTrue(
            any(
                item["disposition"] == "resolved_not_applicable"
                and item["evidenceId"] in subject["evidenceReferences"]
                for item in second["compile-report.json"]["comparatorDispositions"]
            )
        )
        for evidence_id in subject["evidenceReferences"]:
            ledger_entries = [
                item
                for item in second["compile-report.json"]["sourceFeatureCoverage"]
                if evidence_id in item["evidenceIds"]
            ]
            self.assertEqual(len(ledger_entries), 1)
            self.assertEqual(ledger_entries[0]["disposition"], "resolved_not_applicable")

    def test_choose_relationship_replaces_uses_canonical_excludes_runtime_action(self) -> None:
        option_payload, price_payload, join_report, first, subject = (
            self.compile_with_ready_comparator_relationship()
        )
        options_by_rpo = {
            str(row["values"].get("rpo") or "").upper(): str(row["values"].get("option_id") or "")
            for row in first["canonical-row-manifest.json"]["rows"]
            if row["family"] == "options" and row["status"] == "ready"
        }
        proposal = subject["proposedRows"][0]
        resolution = {
            "subjectId": subject["subjectId"],
            "subjectVersion": subject["subjectVersion"],
            "action": "choose_relationship",
            "payload": {
                "sourceOptionId": options_by_rpo[proposal["sourceRpo"]],
                "ruleType": "replaces",
                "targetOptionId": options_by_rpo[proposal["targetRpo"]],
            },
            "disposition": "resolved",
        }
        second = self.compile(
            option_payload=option_payload,
            price_payload=price_payload,
            join_report=join_report,
            resolution_entries=[resolution],
        )
        rule = next(
            row
            for row in second["canonical-row-manifest.json"]["rows"]
            if row["family"] == "rule_mapping"
            and any(
                dependency["evidenceId"] == f"resolution:{subject['subjectId']}"
                for dependency in row["evidenceDependencies"]
            )
        )
        self.assertEqual(rule["values"]["rule_type"], "excludes")
        self.assertEqual(rule["values"]["runtime_action"], "replace")

    def test_comparator_group_exclusive_and_price_confirmations_materialize_rows(self) -> None:
        initial = self.compile()
        proposal_subjects = [
            subject
            for subject in initial["exception-queue.json"]["subjects"]
            if subject["reasonCode"] in {
                "comparator_only_rule_group_proposal",
                "comparator_only_exclusive_group_proposal",
                "comparator_only_price_rule_proposal",
            }
        ]
        required_rpos = {
            str(value).upper()
            for subject in proposal_subjects
            for proposal in subject["proposedRows"]
            for value in (
                proposal.get("sourceRpo"),
                proposal.get("conditionRpo"),
                proposal.get("targetRpo"),
                *(proposal.get("memberRpos") or []),
            )
            if str(value or "")
        }
        option_payload = copy.deepcopy(self.option_payload)
        price_payload = copy.deepcopy(self.price_payload)
        price_payload["priceRows"] = [
            row
            for row in price_payload["priceRows"]
            if str(row.get("rpo") or "").upper() not in required_rpos
        ]
        for candidate in option_payload["candidates"]:
            if str(candidate.get("rpo") or "").upper() in required_rpos:
                candidate["priceMatch"] = {"status": "none"}
                candidate.pop("priceRows", None)
        join_report = join_prices(option_payload["candidates"], price_payload["priceRows"])
        first = self.compile(
            option_payload=option_payload,
            price_payload=price_payload,
            join_report=join_report,
        )
        price_proposal = next(
            subject["proposedRows"][0]
            for subject in first["exception-queue.json"]["subjects"]
            if subject["reasonCode"] == "comparator_only_price_rule_proposal"
        )
        option_ids_by_rpo = {
            str(row["values"].get("rpo") or "").upper(): str(row["values"].get("option_id") or "")
            for row in first["canonical-row-manifest.json"]["rows"]
            if row["family"] == "options" and row["status"] == "ready"
        }
        from openpyxl import load_workbook

        workbook = load_workbook(self.master)
        sheet = workbook["z06_price_rules"]
        headers = [str(cell.value or "") for cell in sheet[1]]
        mismatched = {
            "price_rule_id": "price_variant_mismatch",
            "condition_option_id": option_ids_by_rpo[str(price_proposal["conditionRpo"]).upper()],
            "price_rule_type": price_proposal["priceRuleType"],
            "target_option_id": option_ids_by_rpo[str(price_proposal["targetRpo"]).upper()],
            "price_value": 1,
            "body_style_scope": "coupe",
            "trim_level_scope": "1lz",
            "variant_scope": "different_variant",
        }
        sheet.append([mismatched.get(header, "") for header in headers])
        workbook.save(self.master)
        workbook.close()
        subjects = {
            subject["reasonCode"]: subject
            for subject in first["exception-queue.json"]["subjects"]
            if subject["reasonCode"] in {
                "comparator_only_rule_group_proposal",
                "comparator_only_exclusive_group_proposal",
                "comparator_only_price_rule_proposal",
            }
        }
        self.assertEqual(len(subjects), 3)
        resolutions = []
        for reason, subject in subjects.items():
            payload: dict[str, object] = {"decision": "confirm_proposal"}
            if reason == "comparator_only_exclusive_group_proposal":
                payload["selectionMode"] = "single_within_group"
            if reason == "comparator_only_price_rule_proposal":
                payload.update(
                    {
                        "priceValue": 995,
                        "bodyStyleScope": "coupe",
                        "trimLevelScope": "1lz",
                        "variantScope": "*",
                    }
                )
            resolutions.append(
                {
                    "subjectId": subject["subjectId"],
                    "subjectVersion": subject["subjectVersion"],
                    "action": "provide_typed_value",
                    "payload": payload,
                    "disposition": "resolved",
                }
            )

        second = self.compile(
            option_payload=option_payload,
            price_payload=price_payload,
            join_report=join_report,
            resolution_entries=resolutions,
        )
        rows = second["canonical-row-manifest.json"]["rows"]
        for family in (
            "rule_groups",
            "rule_group_members",
            "exclusive_groups",
            "exclusive_group_members",
            "price_rules",
        ):
            with self.subTest(family=family):
                self.assertTrue(
                    any(
                        row["family"] == family
                        and row["status"] == "ready"
                        and any(
                            dep["evidenceId"].startswith("resolution:")
                            for dep in row["evidenceDependencies"]
                        )
                        for row in rows
                    )
                )
        price = next(
            row
            for row in rows
            if row["family"] == "price_rules"
            and any(dep["evidenceId"].startswith("resolution:") for dep in row["evidenceDependencies"])
        )
        self.assertEqual(price["values"]["price_value"], 995)
        self.assertNotEqual(price["values"]["price_rule_id"], "price_variant_mismatch")
        self.assertEqual(price["values"]["variant_scope"], "")
        blocker_ids = {
            blocker["subjectId"]
            for blocker in second["compile-report.json"]["models"]["zr1"]["blockers"]
        }
        self.assertTrue(
            {subject["subjectId"] for subject in subjects.values()}.isdisjoint(blocker_ids)
        )
        for subject in subjects.values():
            for evidence_id in subject["evidenceReferences"]:
                ledger_entries = [
                    item
                    for item in second["compile-report.json"]["sourceFeatureCoverage"]
                    if evidence_id in item["evidenceIds"]
                ]
                self.assertEqual(len(ledger_entries), 1)
                self.assertEqual(ledger_entries[0]["disposition"], "compiled")
                report_entry = next(
                    item
                    for item in second["compile-report.json"]["comparatorDispositions"]
                    if item["target"] == "zr1" and item["evidenceId"] == evidence_id
                )
                self.assertEqual(report_entry["disposition"], "corroborated_target_match")

    def test_comparator_confirmations_remain_pending_when_any_option_endpoint_is_blocked(self) -> None:
        first = self.compile()
        subjects = [
            subject
            for subject in first["exception-queue.json"]["subjects"]
            if subject["reasonCode"] in {
                "comparator_only_rule_group_proposal",
                "comparator_only_exclusive_group_proposal",
                "comparator_only_price_rule_proposal",
            }
        ]
        self.assertEqual(len(subjects), 3)
        resolutions = []
        for subject in subjects:
            reason = subject["reasonCode"]
            payload: dict[str, object] = {"decision": "confirm_proposal"}
            if reason == "comparator_only_exclusive_group_proposal":
                payload["selectionMode"] = "single_within_group"
            if reason == "comparator_only_price_rule_proposal":
                payload.update(
                    {
                        "priceValue": 995,
                        "bodyStyleScope": "*",
                        "trimLevelScope": "*",
                        "variantScope": "*",
                    }
                )
            resolutions.append(
                {
                    "subjectId": subject["subjectId"],
                    "subjectVersion": subject["subjectVersion"],
                    "action": "provide_typed_value",
                    "payload": payload,
                    "disposition": "resolved",
                }
            )
        second = self.compile(resolution_entries=resolutions)
        blocker_ids = {
            blocker["subjectId"]
            for blocker in second["compile-report.json"]["models"]["zr1"]["blockers"]
        }
        self.assertTrue({subject["subjectId"] for subject in subjects} <= blocker_ids)
        self.assertFalse(
            any(
                dependency["evidenceId"].startswith("resolution:")
                for row in second["canonical-row-manifest.json"]["rows"]
                for dependency in row["evidenceDependencies"]
            )
        )

    def test_comparator_default_confirmation_requires_and_uses_target_priority(self) -> None:
        from openpyxl import load_workbook

        workbook = load_workbook(self.master)
        workbook["default_selection_rules"].append(
            [
                "z06",
                "z06_default_bv4",
                "opt_bv4_001",
                "always",
                "",
                "",
                "",
                "",
                1,
                True,
                "Comparator context only",
                "default_selected",
            ]
        )
        workbook.save(self.master)
        workbook.close()
        comparator = build_comparator_evidence(
            self.master,
            self.selection["comparators"],
            run_authority_fingerprint=self.authority,
        )

        first = self.compile(comparator_artifact=comparator)
        subject = next(
            item
            for item in first["exception-queue.json"]["subjects"]
            if item["reasonCode"] == "comparator_only_default_selection_proposal"
        )
        resolution = {
            "subjectId": subject["subjectId"],
            "subjectVersion": subject["subjectVersion"],
            "action": "provide_typed_value",
            "payload": {
                "decision": "confirm_proposal",
                "priority": 40,
                "displayBehavior": "default_selected",
            },
            "disposition": "resolved",
        }

        second = self.compile(
            comparator_artifact=comparator,
            resolution_entries=[resolution],
        )
        default = next(
            row
            for row in second["canonical-row-manifest.json"]["rows"]
            if row["family"] == "default_selection_rules"
            and row["values"].get("model_key") == "zr1"
            and any(
                dep["evidenceId"] == f"resolution:{subject['subjectId']}"
                for dep in row["evidenceDependencies"]
            )
        )
        self.assertEqual(default["values"]["priority"], 40)
        self.assertEqual(default["values"]["display_behavior"], "default_selected")
        self.assertNotIn(
            subject["subjectId"],
            {
                blocker["subjectId"]
                for blocker in second["compile-report.json"]["models"]["zr1"]["blockers"]
            },
        )

    def test_comparator_default_confirmation_stays_pending_for_blocked_target_option(self) -> None:
        from openpyxl import load_workbook

        workbook = load_workbook(self.master)
        workbook["default_selection_rules"].append(
            [
                "z06",
                "z06_default_pdb",
                "opt_pdb_001",
                "always",
                "",
                "",
                "",
                "",
                1,
                True,
                "Comparator context only",
                "default_selected",
            ]
        )
        workbook.save(self.master)
        workbook.close()
        comparator = build_comparator_evidence(
            self.master,
            self.selection["comparators"],
            run_authority_fingerprint=self.authority,
        )
        first = self.compile(comparator_artifact=comparator)
        subject = next(
            item
            for item in first["exception-queue.json"]["subjects"]
            if item["reasonCode"] == "comparator_only_default_selection_proposal"
            and item["proposedRows"][0]["targetRpo"] == "PDB"
        )
        resolution = {
            "subjectId": subject["subjectId"],
            "subjectVersion": subject["subjectVersion"],
            "action": "provide_typed_value",
            "payload": {
                "decision": "confirm_proposal",
                "priority": 40,
                "displayBehavior": "default_selected",
            },
            "disposition": "resolved",
        }
        second = self.compile(
            comparator_artifact=comparator,
            resolution_entries=[resolution],
        )
        self.assertIn(
            subject["subjectId"],
            {
                blocker["subjectId"]
                for blocker in second["compile-report.json"]["models"]["zr1"]["blockers"]
            },
        )
        self.assertFalse(
            any(
                dependency["evidenceId"] == f"resolution:{subject['subjectId']}"
                for row in second["canonical-row-manifest.json"]["rows"]
                for dependency in row["evidenceDependencies"]
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
        self.assertTrue(
            any(
                "Color and Trim 1" in item["featureId"]
                and item["disposition"] == "compiled"
                for item in report["sourceFeatureCoverage"]
            )
        )
        color_subjects = [
            subject
            for subject in result["exception-queue.json"]["subjects"]
            if "Color and Trim 1" in subject.get("evidenceReferences", [])
        ]
        self.assertEqual(color_subjects, [])
        family_ids = [item["featureId"] for item in report["familyCoverage"]]
        self.assertEqual(len(family_ids), len(set(family_ids)))
        self.assertTrue(any(item["family"] == "interiors" for item in report["familyCoverage"]))
        self.assertTrue(
            any(
                item["family"] in {"price_rules", "variant_overrides"}
                and item["disposition"] == "explicit_empty"
                for item in report["familyCoverage"]
            )
        )
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
