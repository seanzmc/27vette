"""Checkpoint 4 form-graph contracts (Workbook Manager UX recovery §8, §16).

The form graph must be connected and model-scoped, must classify
standard-equipment buckets as buckets rather than broken steps, may claim
"no sections mapped" only when the complete graph proves that condition, and
must carry a proof path to fresh generated runtime metadata for every promoted
model. Spec §17 also binds these surfaces: read-only projection identity,
registry-derived editability, graph parity with fresh generation, and drawer
editing through the durable draft path.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "workbook-manager" / "backend"
SCRIPTS = ROOT / "scripts"
FORM_STRUCTURE = ROOT / "workbook-manager" / "frontend" / "src" / "components" / "FormStructure.jsx"
SECTIONS_LAYOUT = ROOT / "workbook-manager" / "frontend" / "src" / "components" / "SectionsLayout.jsx"
APP_SOURCE = ROOT / "workbook-manager" / "frontend" / "src" / "App.jsx"
NAVIGATION_SOURCE = ROOT / "workbook-manager" / "frontend" / "src" / "navigationState.js"
for path in (BACKEND, SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app import form_graph  # noqa: E402
from app import main as mainmod  # noqa: E402
from app import db as dbmod  # noqa: E402
from app import drafts  # noqa: E402
from app import staging  # noqa: E402
from app.contract_parity import (  # noqa: E402
    generate_contract_snapshot,
    promoted_runtime_models,
)
from workbook_manager_fixtures import (  # noqa: E402
    clone_combined_projection,
    verified_manager_fixture,
)


def _membership_maps(graph: dict) -> tuple[dict, dict]:
    graph_steps = {}
    for step in graph["steps"]:
        graph_steps[step["step_key"]] = sorted(
            entry["section_id"] for entry in step["sections"]
        )
    graph_buckets = {
        bucket["step_key"]: sorted(entry["section_id"] for entry in bucket["members"])
        for bucket in graph["buckets"]
    }
    return graph_steps, graph_buckets


class FormGraphCase(unittest.TestCase):
    """Focused fixture cloned from the shared verified projection."""

    tmp_path: Path
    conn: sqlite3.Connection

    @classmethod
    def setUpClass(cls):
        fixture = verified_manager_fixture()
        cls._fixture = fixture
        cls.tmp_path = Path(tempfile.mkdtemp(prefix="wbm-cp4-graph-"))
        projection = cls.tmp_path / "graph.sqlite3"
        _, _report = clone_combined_projection(projection)
        cls.conn = sqlite3.connect(projection)
        cls.conn.row_factory = sqlite3.Row

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        shutil.rmtree(cls.tmp_path, ignore_errors=True)
        cls._fixture.assert_unmutated()


class TestCheckpoint2AGraphPlanning(FormGraphCase):
    def test_guided_option_variants_come_from_active_registration_not_existing_ovs(self):
        self.conn.execute("SAVEPOINT cp2a_variants")
        try:
            before = mainmod.graph_operations.active_model_variants(self.conn, "z06")
            self.assertEqual(
                [row["variant_id"] for row in before],
                ["1lz_h07", "2lz_h07", "3lz_h07", "1lz_h67", "2lz_h67", "3lz_h67"],
            )
            self.conn.execute(
                "DELETE FROM option_availability WHERE model_id='z06'"
            )
            after = mainmod.graph_operations.active_model_variants(self.conn, "z06")
            self.assertEqual(after, before)
        finally:
            self.conn.execute("ROLLBACK TO cp2a_variants")
            self.conn.execute("RELEASE cp2a_variants")

    def test_option_dependency_plan_classifies_direct_and_transitive_rows_without_selection(self):
        plan = mainmod.graph_operations.dependency_plan(
            self.conn,
            [],
            table="options",
            model_id="stingray",
            key={"option_id": "opt_pcx_001"},
        )

        direct_group = next(
            item for item in plan["dependents"]
            if item["table"] == "rule_groups"
            and item["entity_key"]["group_id"] == "grp_pcx_excludes_blocked_choices"
        )
        self.assertEqual(direct_group["depth"], 1)
        self.assertEqual(direct_group["classification"], "direct")
        member = next(
            item for item in plan["dependents"]
            if item["table"] == "rule_group_members"
            and item["entity_key"]["group_id"] == "grp_pcx_excludes_blocked_choices"
        )
        self.assertGreater(member["depth"], 1)
        self.assertEqual(member["classification"], "transitive")
        self.assertEqual(member["selected_action"], "keep")
        self.assertIn("delete", member["allowed_actions"])
        self.assertTrue(member["src_sheet"])
        self.assertTrue(member["why"])

    def test_group_dependency_plan_uses_draft_effective_member_rows(self):
        group_id = "grp_pcx_excludes_blocked_choices"
        base_members = self.conn.execute(
            "SELECT * FROM rule_group_members WHERE model_id='stingray' "
            "AND group_id=? ORDER BY id LIMIT 2",
            (group_id,),
        ).fetchall()
        removed = dict(base_members[0])
        added_option = self.conn.execute(
            "SELECT option_id FROM options WHERE model_id='stingray' "
            "AND option_id NOT IN (SELECT target_id FROM rule_group_members "
            "WHERE model_id='stingray' AND group_id=?) ORDER BY id LIMIT 1",
            (group_id,),
        ).fetchone()["option_id"]
        operations = [
            {
                "id": 901,
                "table_name": "rule_group_members",
                "family": "rule_group_members",
                "model_id": "stingray",
                "entity_key": {
                    "group_id": group_id,
                    "target_id": removed["target_id"],
                },
                "action": "delete",
                "original": removed,
                "final": None,
            },
            {
                "id": 902,
                "table_name": "rule_group_members",
                "family": "rule_group_members",
                "model_id": "stingray",
                "entity_key": {"group_id": group_id, "target_id": added_option},
                "action": "add",
                "original": None,
                "final": {
                    "group_id": group_id,
                    "target_id": added_option,
                    "display_order": "999",
                    "active": "True",
                },
                "source_sheet": removed["src_sheet"],
                "source_row": None,
            },
        ]

        plan = mainmod.graph_operations.dependency_plan(
            self.conn,
            operations,
            table="rule_groups",
            model_id="stingray",
            key={"group_id": group_id},
        )
        member_keys = {
            item["entity_key"]["target_id"]
            for item in plan["dependents"]
            if item["table"] == "rule_group_members"
        }
        self.assertNotIn(removed["target_id"], member_keys)
        self.assertIn(added_option, member_keys)


class TestGraphMembership(FormGraphCase):

    def test_every_promoted_model_step_has_connected_sections_or_explicit_empty_evidence(self):
        promoted = ("stingray", "grand_sport", "grand_sport_x", "z06", "zr1", "zr1x")
        for model_key in promoted:
            graph = form_graph.build_form_graph(self.conn, model_key)
            self.assertTrue(graph["steps"], model_key)
            known_steps = {step["step_key"] for step in graph["steps"]}
            self.assertNotIn(
                "standard_equipment",
                known_steps,
                f"{model_key}: bucket key must never be a navigable step",
            )
            for step in graph["steps"]:
                has_content = bool(step["sections"] or step["bucket_members"])
                if not has_content:
                    self.assertEqual(step["section_state"], "empty_proven")
                    self.assertTrue(step["empty_reason"])
                    self.assertEqual(step["section_count"], 0)

    def test_z06_paint_step_carries_complete_membership_not_no_sections_mapped(self):
        # Regression anchor for the §2 defect: z06 paint previously showed
        # "no sections mapped" although sec_pain_001 owns active options.
        graph = form_graph.build_form_graph(self.conn, "z06")
        paint = next(
            step for step in graph["steps"] if step["step_key"] == "paint"
        )
        self.assertEqual(
            [entry["section_id"] for entry in paint["sections"]],
            ["sec_pain_001"],
        )

    def test_context_sections_map_to_their_authored_steps(self):
        graph = form_graph.build_form_graph(self.conn, "z06")
        body_style = next(
            step for step in graph["steps"] if step["step_key"] == "body_style"
        )
        self.assertEqual(
            [entry["section_id"] for entry in body_style["sections"]],
            ["sec_context_body_style"],
        )
        trim_level = next(
            step for step in graph["steps"] if step["step_key"] == "trim_level"
        )
        self.assertEqual(
            [entry["section_id"] for entry in trim_level["sections"]],
            ["sec_context_trim_level"],
        )

    def test_interior_sections_are_model_and_trim_scoped_to_base_interior(self):
        expected = {
            "stingray": ["sec_intc_001", "sec_intc_002", "sec_intc_003"],
            "grand_sport": ["sec_intc_001", "sec_intc_002", "sec_intc_003"],
            "grand_sport_x": ["sec_intc_001", "sec_intc_002", "sec_intc_003"],
            "z06": ["sec_lzint_001", "sec_lzint_002", "sec_lzint_003"],
            "zr1": ["sec_lzint_001", "sec_lzint_003"],
            "zr1x": ["sec_lzint_001", "sec_lzint_003"],
        }
        for model_key, section_ids in expected.items():
            graph = form_graph.build_form_graph(self.conn, model_key)
            step = next(
                row for row in graph["steps"] if row["step_key"] == "base_interior"
            )
            self.assertEqual(
                [entry["section_id"] for entry in step["sections"]],
                section_ids,
                model_key,
            )
            self.assertTrue(
                all(entry["runtime_evidence"] == "interiors" for entry in step["sections"])
            )

    def test_standard_equipment_is_a_classified_bucket_with_members(self):
        graph = form_graph.build_form_graph(self.conn, "stingray")
        keys = {bucket["step_key"] for bucket in graph["buckets"]}
        self.assertIn("standard_equipment", keys)
        bucket = next(
            bucket
            for bucket in graph["buckets"]
            if bucket["step_key"] == "standard_equipment"
        )
        self.assertTrue(bucket["members"])
        self.assertEqual(bucket["classification"], "bucket")
        presentation_ids = {
            entry["section_id"]
            for entry in bucket["members"]
            if entry["standard_equipment_bucket"] == "True"
        }
        rows = self.conn.execute(
            "SELECT section_id FROM section_presentation WHERE model_key='stingray' "
            "AND standard_equipment_bucket='True' AND active='True'"
        ).fetchall()
        self.assertEqual(presentation_ids, {row["section_id"] for row in rows})

    def test_sections_without_model_connection_are_evidence_backed_unmapped(self):
        graph = form_graph.build_form_graph(self.conn, "z06")
        unmapped_ids = {entry["section_id"] for entry in graph["unmapped_sections"]}
        for section_id in unmapped_ids:
            owners = self.conn.execute(
                "SELECT COUNT(*) c FROM options WHERE model_id='z06' "
                "AND section_id=? AND active='True'",
                (section_id,),
            ).fetchone()["c"]
            context = self.conn.execute(
                "SELECT COUNT(*) c FROM context_sections WHERE model_key='z06' "
                "AND section_id=?",
                (section_id,),
            ).fetchone()["c"]
            self.assertGreater(
                owners + context + next(
                    entry["interior_count"]
                    for entry in graph["unmapped_sections"]
                    if entry["section_id"] == section_id
                ),
                0,
            )

    def test_unmapped_never_contains_model_connected_sections(self):
        for model_key in ("stingray", "z06", "zr1x"):
            graph = form_graph.build_form_graph(self.conn, model_key)
            unmapped_ids = {
                entry["section_id"] for entry in graph["unmapped_sections"]
            }
            mapped_ids = {
                entry["section_id"]
                for step in graph["steps"]
                for entry in step["sections"] + step["bucket_members"]
            } | {
                entry["section_id"]
                for bucket in graph["buckets"]
                for entry in bucket["members"]
            }
            self.assertFalse(unmapped_ids & mapped_ids)

    def test_complete_section_nodes_attach_options_overrides_and_counts(self):
        graph = form_graph.build_form_graph(self.conn, "z06")
        nodes = {node["section_id"]: node for node in graph["section_nodes"]}
        presentation_ids = {
            row["section_id"] for row in self.conn.execute(
                "SELECT section_id FROM section_presentation WHERE model_key='z06'"
            )
        }
        self.assertTrue(presentation_ids <= set(nodes))
        self.assertTrue(nodes["sec_pain_001"]["options"])
        option = nodes["sec_pain_001"]["options"][0]
        self.assertEqual(option["destination"]["workspace"], "options")
        self.assertIn("variant_overrides", nodes["sec_pain_001"])
        self.assertEqual(graph["counts"]["sections"], len(graph["section_nodes"]))
        self.assertEqual(graph["counts"]["unresolved"], len(graph["unmapped_sections"]))

    def test_draft_overlay_marks_effective_nodes_and_pending_parity(self):
        graph = form_graph.build_form_graph(self.conn, "z06")
        overlaid = form_graph.apply_draft_overlay(graph, [{
            "id": 7,
            "action": "update",
            "table_name": "section_presentation",
            "family": "section_presentation_meta",
            "model_id": "z06",
            "entity_key": {"model_key": "z06", "section_id": "sec_pain_001"},
            "changed_fields": {"display_label": {"before": "Paint", "after": "Paint finish"}},
            "final": {
                "section_id": "sec_pain_001",
                "display_label": "Paint finish",
                "active": "True",
            },
        }])
        node = next(
            node for node in overlaid["section_nodes"]
            if node["section_id"] == "sec_pain_001"
        )
        self.assertEqual(node["display_name"], "Paint finish")
        self.assertEqual(node["draft_overlay"]["state"], "modified")
        self.assertEqual(overlaid["draft_overlay"]["revision"], 7)
        self.assertEqual(overlaid["parity"]["draft_status"], "pending_preview")

    def test_section_placement_overlay_rebuilds_topology_counts_and_fingerprint(self):
        graph = form_graph.build_form_graph(self.conn, "z06")
        before_fingerprint = graph["fingerprint"]
        overlaid = form_graph.apply_draft_overlay(graph, [{
            "id": 8,
            "action": "update",
            "table_name": "section_presentation",
            "family": "section_presentation_meta",
            "model_id": "z06",
            "entity_key": {"model_key": "z06", "section_id": "sec_pain_001"},
            "changed_fields": {"step_key": {"before": "paint", "after": "wheels"}},
            "final": {
                "section_id": "sec_pain_001",
                "step_key": "wheels",
                "active": "True",
                "standard_equipment_bucket": "False",
            },
        }])
        paint = next(step for step in overlaid["steps"] if step["step_key"] == "paint")
        wheels = next(step for step in overlaid["steps"] if step["step_key"] == "wheels")
        self.assertNotIn("sec_pain_001", {row["section_id"] for row in paint["sections"]})
        self.assertIn("sec_pain_001", {row["section_id"] for row in wheels["sections"]})
        self.assertEqual(paint["section_count"], len(paint["sections"]))
        self.assertEqual(wheels["section_count"], len(wheels["sections"]))
        self.assertNotEqual(overlaid["fingerprint"], before_fingerprint)

    def test_section_bucket_overlay_rebuilds_classification(self):
        graph = form_graph.build_form_graph(self.conn, "z06")
        overlaid = form_graph.apply_draft_overlay(graph, [{
            "id": 81,
            "action": "update",
            "table_name": "section_presentation",
            "family": "section_presentation_meta",
            "model_id": "z06",
            "entity_key": {"model_key": "z06", "section_id": "sec_pain_001"},
            "changed_fields": {
                "step_key": {"before": "paint", "after": "standard_equipment"},
                "standard_equipment_bucket": {"before": "False", "after": "True"},
            },
            "final": {
                "section_id": "sec_pain_001",
                "step_key": "standard_equipment",
                "active": "True",
                "standard_equipment_bucket": "True",
            },
        }])
        paint = next(step for step in overlaid["steps"] if step["step_key"] == "paint")
        bucket = next(
            bucket for bucket in overlaid["buckets"]
            if bucket["step_key"] == "standard_equipment"
        )
        self.assertNotIn("sec_pain_001", {row["section_id"] for row in paint["sections"]})
        self.assertIn("sec_pain_001", {row["section_id"] for row in bucket["members"]})
        node = next(
            node for node in overlaid["section_nodes"]
            if node["section_id"] == "sec_pain_001"
        )
        self.assertEqual(node["classification"], "bucket_section")
        self.assertEqual(overlaid["counts"]["buckets"], len(overlaid["buckets"]))

    def test_option_non_graph_edit_does_not_mark_or_overwrite_section(self):
        graph = form_graph.build_form_graph(self.conn, "z06")
        paint = next(
            node for node in graph["section_nodes"]
            if node["section_id"] == "sec_pain_001"
        )
        option = paint["options"][0]
        overlaid = form_graph.apply_draft_overlay(graph, [
            {
                "id": 9,
                "action": "update",
                "table_name": "options",
                "family": "options",
                "model_id": "z06",
                "entity_key": {"option_id": option["option_id"]},
                "changed_fields": {"option_name": {"before": option["option_name"], "after": "Renamed"}},
                "final": {
                    **option,
                    "section_id": "sec_pain_001",
                    "option_name": "Renamed",
                    "active": "False",
                    "display_behavior": "hidden",
                },
            },
            {
                "id": 10,
                "action": "update",
                "table_name": "variant_option_overrides",
                "family": "variant_option_overrides",
                "model_id": "z06",
                "entity_key": {"variant_id": "3lz", "option_id": option["option_id"]},
                "changed_fields": {"selectable": {"before": "True", "after": "False"}},
                "final": {
                    "variant_id": "3lz",
                    "option_id": option["option_id"],
                    "section_id": "sec_pain_001",
                    "active": "False",
                    "display_behavior": "hidden",
                    "selectable": "False",
                },
            },
        ])
        effective = next(
            node for node in overlaid["section_nodes"]
            if node["section_id"] == "sec_pain_001"
        )
        self.assertEqual(effective["draft_overlay"]["state"], "unchanged")
        self.assertEqual(effective["active"], paint["active"])
        self.assertEqual(effective["display_behavior"], paint["display_behavior"])
        self.assertEqual(overlaid["counts"]["draft_changes"], 0)
        self.assertEqual(overlaid["parity"]["draft_status"], "unchanged")
        self.assertEqual(overlaid["fingerprint"], graph["fingerprint"])

    def test_option_section_move_updates_nested_source_and_destination_lists(self):
        graph = form_graph.build_form_graph(self.conn, "z06")
        source = next(
            node for node in graph["section_nodes"]
            if node["section_id"] == "sec_pain_001"
        )
        existing_ids = {node["section_id"] for node in graph["section_nodes"]}
        known_steps = {step["step_key"] for step in graph["steps"]}
        destination_master = next(
            row for row in graph["sections_master"]
            if row["section_id"] not in existing_ids
            and row.get("step_key") in known_steps
            and row.get("step_key") != source["step_key"]
        )
        destination_id = destination_master["section_id"]
        option = source["options"][0]
        overlaid = form_graph.apply_draft_overlay(graph, [{
            "id": 10,
            "action": "update",
            "table_name": "options",
            "family": "options",
            "model_id": "z06",
            "entity_key": {"option_id": option["option_id"]},
            "changed_fields": {
                "section_id": {
                    "before": source["section_id"],
                    "after": destination_id,
                },
            },
            "final": {
                **option,
                "section_id": destination_id,
            },
        }])
        nodes = {node["section_id"]: node for node in overlaid["section_nodes"]}
        self.assertNotIn(option["option_id"], {
            row["option_id"] for row in nodes[source["section_id"]]["options"]
        })
        self.assertIn(option["option_id"], {
            row["option_id"] for row in nodes[destination_id]["options"]
        })
        destination_step = next(
            step for step in overlaid["steps"]
            if step["step_key"] == destination_master["step_key"]
        )
        self.assertIn(
            destination_id,
            {row["section_id"] for row in destination_step["sections"]},
        )
        self.assertEqual(nodes[source["section_id"]]["display_behavior"], source["display_behavior"])


class TestFreshRuntimeParity(FormGraphCase):
    """Spec §16 Checkpoint 4: prove parity against fresh generated metadata."""

    def test_projection_graph_matches_fresh_generation_for_every_promoted_model(self):
        models = promoted_runtime_models(ROOT / "stingray_master.xlsx", ROOT)
        self.assertEqual(
            models,
            (
                "stingray",
                "grand_sport",
                "grand_sport_x",
                "z06",
                "zr1",
                "zr1x",
            ),
        )
        copied_workbook = self.tmp_path / "parity-copy.xlsx"
        verified_manager_fixture().clone_workbook(copied_workbook)
        section_steps = {
            row["section_id"]: row["step_key"]
            for row in self.conn.execute(
                "SELECT section_id, step_key FROM form_sections"
            )
        }
        mismatches: list[str] = []
        for model_key in models:
            fresh_path = generate_contract_snapshot(
                copied_workbook, self.tmp_path / model_key, model_key
            )
            fresh = json.loads(fresh_path.read_text(encoding="utf-8"))
            expected = form_graph.contract_membership(fresh, section_steps)
            graph = form_graph.build_form_graph(self.conn, model_key)
            actual_steps, actual_buckets = _membership_maps(graph)
            step_keys = set(actual_steps) | set(expected["steps"])
            for step_key in step_keys:
                ids = expected["steps"].get(step_key)
                if actual_steps.get(step_key) != ids:
                    mismatches.append(
                        f"{model_key} step {step_key}: graph="
                        f"{actual_steps.get(step_key)} fresh={ids}"
                    )
            bucket_keys = set(actual_buckets) | set(expected["buckets"])
            for bucket_key in bucket_keys:
                if actual_buckets.get(bucket_key) != expected["buckets"].get(bucket_key):
                    mismatches.append(
                        f"{model_key} bucket {bucket_key}: graph="
                        f"{actual_buckets.get(bucket_key)} "
                        f"fresh={expected['buckets'].get(bucket_key)}"
                    )
        self.assertEqual(mismatches, [])


class TestStructureEndpoint(FormGraphCase):

    def test_structure_update_saves_owned_draft_intent_without_projection_write(self):
        state = sqlite3.connect(":memory:")
        state.row_factory = sqlite3.Row
        dbmod.init_durable_schema(state)
        before = dict(self.conn.execute(
            "SELECT * FROM model_registry_promotion WHERE model_key='z06'"
        ).fetchone())
        try:
            operation = drafts.save_operation(
                self.conn,
                state,
                projection_state="current",
                base_workbook_sha256=dbmod.get_meta(self.conn, "workbook_sha256"),
                base_workbook_mtime_ns=dbmod.get_meta(
                    self.conn, "workbook_mtime_ns"
                ),
                draft_id="structure-draft",
                table="model_registry_promotion",
                model_id="z06",
                op="update",
                key={"model_key": "z06"},
                record={"notes": "isolated STRUCT-02 authored fixture value"},
                actor="structure-test",
            )
            self.assertEqual(operation["family"], "model_registry_promotion")
            self.assertEqual(operation["source_sheet"], "model_registry_promotion")
            self.assertEqual(operation["entity_key"], {"model_key": "z06"})
            self.assertEqual(operation["model_context"], ["z06"])
            after = dict(self.conn.execute(
                "SELECT * FROM model_registry_promotion WHERE model_key='z06'"
            ).fetchone())
            self.assertEqual(after, before)
        finally:
            state.close()

    def test_structure_family_index_exposes_registered_management_families(self):
        response = mainmod.tables(model="z06", conn=self.conn)
        families = {item["family"]: item for item in response["structure_families"]}
        expected = {
            "model_registry_promotion",
            "model_workbook_sources",
            "variant_master",
            "model_variants",
            "order_summary_sections_meta",
            "step_order_summary_map_meta",
        }
        self.assertTrue(expected.issubset(families), expected - set(families))
        for family in expected:
            item = families[family]
            self.assertTrue(item["editable"], family)
            self.assertEqual(
                item["schema"]["schema_version"], mainmod.TABLE_SCHEMA_VERSION
            )
            self.assertEqual(
                set(item["capabilities"]), {"create", "update", "delete"}
            )
            self.assertTrue(item["generated_impact"])
        models = families["model_master"]
        self.assertFalse(models["capabilities"]["create"]["allowed"])
        self.assertEqual(
            models["capabilities"]["create"]["blocked_reason"],
            "adding a new model_master identity is outside this workflow",
        )
        self.assertTrue(models["capabilities"]["update"]["allowed"])
        self.assertTrue(models["capabilities"]["delete"]["allowed"])
        for item in families.values():
            spec = mainmod.SPEC_BY_TABLE[item["table"]]
            for action, capability in item["capabilities"].items():
                expected_capability = staging.edit_capability(
                    self.conn,
                    spec,
                    "z06",
                    op={
                        "create": "add",
                        "update": "update",
                        "delete": "delete",
                    }[action],
                )
                self.assertEqual(
                    capability, expected_capability, (item["family"], action)
                )
        read_only = families["sections"]
        self.assertFalse(read_only["editable"])
        for capability in read_only["capabilities"].values():
            self.assertFalse(capability["allowed"])
            self.assertEqual(
                capability["blocked_reason"],
                "form_sections is read-only in phase 1 (no gated workbook write "
                "path exists for its sheet)",
            )

    def test_structure_family_api_follows_a_synthetic_registered_spec(self):
        base = mainmod.SPEC_BY_FAMILY["variant_master"]
        synthetic = replace(
            base,
            family="synthetic_structure",
            table="synthetic_structure",
        )
        self.conn.execute(
            f'CREATE TABLE synthetic_structure AS SELECT * FROM "{base.table}" WHERE 0'
        )
        with mock.patch.object(
            mainmod,
            "structure_specs",
            return_value=(*mainmod.structure_specs(), synthetic),
        ):
            response = mainmod.tables(model="z06", conn=self.conn)
        item = next(
            family for family in response["structure_families"]
            if family["family"] == "synthetic_structure"
        )
        self.assertEqual(item["table"], "synthetic_structure")
        self.assertEqual(item["schema"]["schema_version"], mainmod.TABLE_SCHEMA_VERSION)
        self.assertEqual(set(item["capabilities"]), {"create", "update", "delete"})

    def test_edit_capability_delegates_to_the_durable_mutation_guard(self):
        spec = mainmod.SPEC_BY_FAMILY["model_master"]
        refusal = [{"message": "guard-owned refusal"}]
        with mock.patch.object(
            staging, "_editable_guard", return_value=refusal
        ) as guard:
            capability = staging.edit_capability(
                self.conn, spec, "z06", op="add"
            )
        self.assertEqual(capability, {
            "allowed": False,
            "blocked_reason": "guard-owned refusal",
        })
        guard.assert_called_once()

    def test_structure_response_exposes_complete_graph_and_legacy_editing_rows(self):
        response = mainmod.structure("z06", conn=self.conn)
        self.assertEqual(response["model_key"], "z06")
        self.assertEqual(response["graph"]["version"], "cp4-1")
        self.assertEqual(response["steps"], response["graph"]["steps"])
        self.assertTrue(response["section_presentation"])
        self.assertTrue(response["context_sections"])
        self.assertIn("inactive_records", response["graph"])
        self.assertNotIn("leftover_unresolved", response["graph"])
        paint = next(
            step for step in response["graph"]["steps"]
            if step["step_key"] == "paint"
        )
        self.assertEqual(
            [section["section_id"] for section in paint["sections"]],
            ["sec_pain_001"],
        )

    def test_structure_rejects_stale_and_terminal_draft_bindings(self):
        state = sqlite3.connect(":memory:")
        state.row_factory = sqlite3.Row
        dbmod.init_durable_schema(state)
        projection_sha = dbmod.get_meta(self.conn, "workbook_sha256")
        try:
            prospective = mainmod.structure(
                "z06", draft_id="not-yet-persisted", conn=self.conn, state_conn=state
            )
            self.assertEqual(
                prospective["graph"]["draft_overlay"]["state"], "unchanged"
            )
            self.assertEqual(
                prospective["graph"]["draft_overlay"]["conflicts"], []
            )

            state.execute(
                "INSERT INTO workflow_drafts(id, created_ts, updated_ts, status, "
                "base_workbook_sha256, base_workbook_mtime_ns) "
                "VALUES('bound', 't', 't', 'draft', ?, '1')",
                ("0" * 64,),
            )
            state.commit()
            stale = mainmod.structure(
                "z06", draft_id="bound", conn=self.conn, state_conn=state
            )
            self.assertEqual(stale["graph"]["draft_overlay"]["state"], "conflicted")
            self.assertEqual(
                stale["graph"]["draft_overlay"]["conflicts"][0]["code"],
                "draft_binding_stale",
            )

            state.execute(
                "UPDATE workflow_drafts SET status='cancelled', "
                "base_workbook_sha256=? WHERE id='bound'",
                (projection_sha,),
            )
            state.commit()
            terminal = mainmod.structure(
                "z06", draft_id="bound", conn=self.conn, state_conn=state
            )
            self.assertEqual(terminal["graph"]["draft_overlay"]["state"], "conflicted")
            self.assertEqual(
                terminal["graph"]["draft_overlay"]["conflicts"][0]["code"],
                "draft_terminal",
            )
        finally:
            state.close()


class TestFormStructureSource(unittest.TestCase):

    def test_form_overview_exposes_registry_structure_index_through_shared_browser(self):
        source = FORM_STRUCTURE.read_text(encoding="utf-8")
        operations = (
            ROOT / "workbook-manager" / "frontend" / "src" / "components"
            / "ModelOperations.jsx"
        ).read_text(encoding="utf-8")
        api_source = (
            ROOT / "workbook-manager" / "frontend" / "src" / "api.js"
        ).read_text(encoding="utf-8")
        styles = (
            ROOT / "workbook-manager" / "frontend" / "src" / "styles.css"
        ).read_text(encoding="utf-8")

        self.assertIn("Registered structure management", source)
        self.assertIn("api.structureFamilies", source)
        self.assertIn("collectionsOverride", source)
        self.assertIn("collectionsOverride", operations)
        self.assertIn("/api/tables", api_source)
        self.assertIn("RecordForm", operations)
        self.assertIn("editorEvidence", operations)
        self.assertIn("api.dependencies", operations)
        self.assertIn("const active = schema.columns.filter", operations)
        self.assertIn(".editor-evidence", styles)
        self.assertIn("const loadToken = useRef(0)", operations)
        self.assertIn("if (token !== loadToken.current) return", operations)
        self.assertIn("const [loadedIdentity, setLoadedIdentity]", operations)
        self.assertIn("const dataReady = loadedIdentity?.table === table", operations)
        self.assertIn("disabled={!dataReady", operations)
        self.assertIn("{dataReady && rows.map", operations)

    def test_form_overview_uses_graph_classifications_and_contextual_drawer_actions(self):
        source = FORM_STRUCTURE.read_text(encoding="utf-8")
        self.assertIn("structure.graph.steps", source)
        self.assertIn("Standard equipment buckets", source)
        self.assertIn("Summary-only review sections", source)
        self.assertIn("Unmapped authoring records", source)
        self.assertIn("No section cards", source)
        self.assertNotIn("no sections mapped", source)
        self.assertIn("Edit step", source)
        self.assertIn("Edit section", source)
        self.assertIn("Add display metadata", source)
        self.assertIn('table: "context_sections"', source)
        self.assertIn('table: "section_presentation"', source)
        self.assertIn('saveLabel: "Save section change to draft"', source)
        self.assertIn("saveLabel={editing.saveLabel}", source)
        self.assertIn("Reference only", source)

    def test_section_and_step_editing_stays_in_record_form_drawer_and_refreshes_tray(self):
        source = FORM_STRUCTURE.read_text(encoding="utf-8")
        self.assertIn("<RecordForm", source)
        self.assertIn("onSaved={saved}", source)
        self.assertIn("onChanged();", source)
        self.assertIn("title={editing.title}", source)
        self.assertIn("target={editing.target}", source)
        self.assertNotIn('<div style={{ marginTop: 14 }}>', source)

    def test_sections_layout_is_a_first_class_deep_linked_filterable_workspace(self):
        app = APP_SOURCE.read_text(encoding="utf-8")
        navigation = NAVIGATION_SOURCE.read_text(encoding="utf-8")
        source = SECTIONS_LAYOUT.read_text(encoding="utf-8")
        self.assertIn('id: "sections", label: "Sections & Layout"', app)
        self.assertIn('tab === "sections"', app)
        self.assertIn('"overview", "sections",', navigation)
        self.assertIn('navigation.type === "section"', source)
        self.assertIn("onNavigationChange", source)
        for label in (
            "All sections", "Unresolved", "Empty sections", "Inactive",
            "Buckets", "Draft changes",
        ):
            self.assertIn(label, source)
        self.assertIn("Options in this section", source)
        self.assertIn("Parity impact", source)
        self.assertIn("draft_overlay", source)
        self.assertIn("EDIT_FAMILY_LABELS", source)
        self.assertNotIn("schema.family", source)


class TestFingerprintAdapter(unittest.TestCase):

    def test_contract_membership_reads_generated_shape(self):
        contract = {
            "steps": [
                {"step_key": "paint", "section_ids": "sec_pain_001|sec_badg_001"},
                {"step_key": "base_interior", "section_ids": ""},
                {"step_key": "summary", "section_ids": ""},
            ],
            "sections": [
                {"section_id": "sec_pain_001", "step_key": "paint"},
                {"section_id": "sec_stan_001", "step_key": "standard_equipment"},
            ],
            "interiors": [
                {"interior_id": "1LT_AQ9_HTA", "section_id": "sec_intc_001"},
            ],
        }
        membership = form_graph.contract_membership(
            contract,
            {"sec_intc_001": "base_interior"},
        )
        self.assertEqual(membership["steps"]["paint"], ["sec_badg_001", "sec_pain_001"])
        self.assertEqual(membership["steps"]["summary"], [])
        self.assertEqual(
            membership["buckets"]["standard_equipment"], ["sec_stan_001"]
        )
        self.assertEqual(membership["steps"]["base_interior"], ["sec_intc_001"])

    def test_fingerprint_changes_when_membership_changes(self):
        steps_one = [
            {
                "step_key": "paint",
                "sections": [{"section_id": "sec_pain_001"}],
            }
        ]
        steps_two = [
            {
                "step_key": "paint",
                "sections": [
                    {"section_id": "sec_pain_001"},
                    {"section_id": "sec_extra_001"},
                ],
            }
        ]
        one = form_graph.graph_fingerprint("z06", steps_one, [])
        two = form_graph.graph_fingerprint("z06", steps_two, [])
        self.assertNotEqual(one, two)


if __name__ == "__main__":
    unittest.main()
