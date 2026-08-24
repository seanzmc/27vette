"""Checkpoint 3A/3B: exhaustive field-control metadata contract.

Owning specification:
docs/superpowers/specs/2026-08-21-workbook-manager-ux-recovery.md
§10.1/§10.2/§10.7/§10.8 and Checkpoint 3 subpass 3A. The test matrix is
generated directly from ``WRITABLE_COLUMNS`` so a new writable column with no
deliberate control is a failure, never an implicit free-text input (§10.8).
Failures report family and field.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "workbook-manager" / "backend"
SCRIPTS = ROOT / "scripts"
for path in (BACKEND, SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from corvette_form_generator.workbook_domain import registry  # noqa: E402

REQUIRED_CONTROL_KEYS = (
    "kind", "label", "group", "order", "blank", "help", "affects",
)

# Domains proven per spec §19.3 by workbook rows + generator parsing + runtime
# consumers. Recorded here so the proof travels with the constraint.
PROVEN_FINITE = {
    ("interior_components", "component_type"): (
        "five authored values across 1,044 workbook rows; consumers "
        "scripts/corvette_form_generator/interiors.py and runtime_metadata.py",
    ),
}
PROVEN_BOOLEAN_INHERIT = {
    # presentation_bool(): blank inherits default False; only True/blank authored.
    ("section_presentation_meta", "standard_equipment_bucket"),
    ("section_presentation_meta", "auto_added_bucket"),
}


class TestControlInventory(unittest.TestCase):
    def test_every_writable_field_has_explicit_control(self):
        missing, incomplete = [], []
        for family, columns in registry.WRITABLE_COLUMNS.items():
            controls = registry.EDITOR_SHEET_META[family].get("controls", {})
            for column in columns:
                control = controls.get(column)
                if control is None:
                    missing.append(f"{family}.{column}")
                    continue
                for key in REQUIRED_CONTROL_KEYS:
                    if key not in control:
                        incomplete.append(f"{family}.{column}.{key}")
        self.assertEqual(
            [], missing, f"writable fields with no control metadata: {missing}"
        )
        self.assertEqual(
            [], incomplete, f"control entries missing required keys: {incomplete}"
        )

    def test_new_untyped_field_does_not_get_an_implicit_text_control(self):
        columns = (*registry.WRITABLE_COLUMNS["options"], "unclassified_field")
        with mock.patch.dict(registry.WRITABLE_COLUMNS, {"options": columns}):
            controls = registry._controls_for("options")
        self.assertNotIn("unclassified_field", controls)

    def test_key_columns_are_locked_on_edit(self):
        unlocked = []
        for family, meta in registry.EDITOR_SHEET_META.items():
            controls = meta["controls"]
            for column in meta["key"]:
                if not controls[column].get("immutable_on_edit"):
                    unlocked.append(f"{family}.{column}")
        self.assertEqual([], unlocked, f"key columns editable on update: {unlocked}")

    def test_control_kinds_are_from_the_registered_vocabulary(self):
        bad = [
            f"{family}.{column}:{control['kind']}"
            for family, controls in registry.FIELD_CONTROLS.items()
            for column, control in controls.items()
            if control["kind"] not in registry.CONTROL_KINDS
        ]
        self.assertEqual([], bad, f"controls with unknown kind: {bad}")

    def test_control_coverage_is_exactly_the_writable_columns(self):
        extra = []
        for family, controls in registry.FIELD_CONTROLS.items():
            writable = set(registry.WRITABLE_COLUMNS[family])
            for column in controls:
                if column not in writable:
                    extra.append(f"{family}.{column}")
        self.assertEqual([], extra, f"controls for non-writable fields: {extra}")

    def test_kind_specific_metadata_is_complete(self):
        incomplete = []
        for family, controls in registry.FIELD_CONTROLS.items():
            for column, control in controls.items():
                kind = control["kind"]
                if kind in ("boolean", "finite") and "values" not in control:
                    incomplete.append(f"{family}.{column}.values")
                if kind == "reference" and control.get("source") != (
                        "projection_reference_options"):
                    incomplete.append(f"{family}.{column}.source")
                if kind in ("integer", "money") and control.get("step") != 1:
                    incomplete.append(f"{family}.{column}.step")
        self.assertEqual([], incomplete)


class TestControlKindParity(unittest.TestCase):
    """§10.2: metadata kind must not contradict registered structure."""

    def _contradictions(self):
        problems = []
        for family, columns in registry.WRITABLE_COLUMNS.items():
            meta = registry.EDITOR_SHEET_META[family]
            types = meta.get("types", {})
            enums = meta.get("enums", {})
            refs = meta.get("refs", {})
            unions = meta.get("ref_unions", {})
            conditional_column = (meta.get("conditional_ref") or {}).get("column")
            controls = registry.FIELD_CONTROLS[family]
            for column in columns:
                kind = controls[column]["kind"]
                proven = (family, column) in registry.PROVEN_FINITE_VALUES
                inherit_blank = (
                    (family, column) in registry.BOOLEAN_INHERIT_BLANK
                )
                structural = (
                    "reference"
                    if (refs.get(column) or unions.get(column)
                        or column == conditional_column)
                    else "finite"
                    if enums.get(column)
                    else "boolean"
                    if types.get(column) == "bool" or inherit_blank
                    else "numeric"
                    if types.get(column) == "int"
                    else "text"
                )
                if structural == "reference" and kind != "reference":
                    problems.append(f"{family}.{column}: structural reference, kind {kind}")
                elif structural == "finite" and kind not in ("finite", "reference"):
                    problems.append(f"{family}.{column}: structural finite, kind {kind}")
                elif structural == "boolean" and kind != "boolean":
                    problems.append(f"{family}.{column}: structural bool, kind {kind}")
                elif structural == "numeric" and kind not in ("integer", "money"):
                    problems.append(f"{family}.{column}: structural int, kind {kind}")
                elif structural == "text" and kind not in (
                    # deliberate reclassifications require proven evidence:
                    # finite domains per §19.3, boolean-with-inherit per
                    # presentation_bool consumption, url per the runtime
                    # cardImagePosition pattern authority.
                    "short_text", "long_text", "structured_text", "url",
                ) and not (proven and kind == "finite") and not (
                    inherit_blank and kind == "boolean"
                ):
                    problems.append(f"{family}.{column}: structural text, kind {kind}")
        return problems

    def test_no_kind_contradicts_registry_structure(self):
        self.assertEqual([], self._contradictions())

    def test_constrained_fields_never_render_as_arbitrary_text(self):
        unrestricted = []
        for family, columns in registry.WRITABLE_COLUMNS.items():
            meta = registry.EDITOR_SHEET_META[family]
            types = meta.get("types", {})
            enums = meta.get("enums", {})
            refs = meta.get("refs", {})
            unions = meta.get("ref_unions", {})
            conditional_column = (meta.get("conditional_ref") or {}).get("column")
            controls = registry.FIELD_CONTROLS[family]
            for column in columns:
                constrained = (
                    types.get(column) in ("bool", "int")
                    or enums.get(column)
                    or refs.get(column)
                    or unions.get(column)
                    or column == conditional_column
                    or (family, column) in PROVEN_BOOLEAN_INHERIT
                )
                if constrained and controls[column]["kind"] in (
                    "short_text", "long_text", "structured_text",
                ):
                    unrestricted.append(f"{family}.{column}")
        self.assertEqual(
            [], unrestricted,
            f"constrained fields classified as free text: {unrestricted}",
        )

    def test_proven_finite_domains_are_enforced(self):
        controls = registry.FIELD_CONTROLS["interior_components"]
        self.assertEqual(
            sorted(("seat", "suede", "stitching", "r6x", "two_tone")),
            sorted(controls["component_type"]["values"]),
        )
        # Context-section selection mode is owned by the generator's
        # customer-label vocabulary; the registry literal must stay in parity.
        from corvette_form_generator.model_configs import SELECTION_MODE_LABELS

        self.assertEqual(
            sorted(SELECTION_MODE_LABELS),
            sorted(
                registry.FIELD_CONTROLS["context_section_master_meta"]
                ["selection_mode"]["values"]
            ),
        )


class TestBlankSemantics(unittest.TestCase):
    """§10.2: blank behavior must agree with registry validation."""

    def test_blank_allowed_exactly_for_optional_or_blank_member_domains(self):
        wrong = []
        for family, columns in registry.WRITABLE_COLUMNS.items():
            meta = registry.EDITOR_SHEET_META[family]
            optional = set(meta.get("optional_columns", ()))
            enums = meta.get("enums", {})
            controls = registry.FIELD_CONTROLS[family]
            for column in columns:
                blank = controls[column]["blank"]
                if blank == "never_blank_key":
                    # key fields are separately proven required; skip here.
                    continue
                allowed_expected = (
                    column in optional
                    or "" in enums.get(column, ())
                    or (family, column) in PROVEN_BOOLEAN_INHERIT
                )
                actual_allowed = blank != "forbidden"
                if allowed_expected != actual_allowed:
                    wrong.append(
                        f"{family}.{column}: blank={blank!r}, "
                        f"registry optional={column in optional}"
                    )
        self.assertEqual([], wrong)


class TestSchemaResponseContract(unittest.TestCase):
    """§10.2: _schema_dict exposes normalized metadata and a version, and
    fails closed on missing/contradictory control metadata."""

    @classmethod
    def setUpClass(cls):
        import sqlite3

        from app import main as mainmod

        cls.mainmod = mainmod
        cls.conn = sqlite3.connect(":memory:")

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def _schema(self, table):
        with mock.patch.object(
            __import__("app.staging", fromlist=["target_sheet_for"]),
            "target_sheet_for",
            return_value=None,
        ):
            return self.mainmod._schema_dict(self.conn, self.mainmod.SPEC_BY_TABLE[table], None)

    def test_schema_response_carries_version_and_per_column_controls(self):
        schema = self._schema("options")
        self.assertEqual(
            "workbook-manager-table-schema-2", schema["schema_version"]
        )
        by_name = {c["name"]: c for c in schema["columns"]}
        control = by_name["price"]["control"]
        self.assertEqual("money", control["kind"])
        # price is registry-optional, so blank must be allowed.
        self.assertEqual("allowed", control["blank"])
        self.assertEqual("finite", by_name["display_behavior"]["control"]["kind"])
        self.assertEqual(
            "reference", by_name["section_id"]["control"]["kind"]
        )
        from app.schemas import TableSchemaOut

        serialized = TableSchemaOut(**schema).model_dump()
        self.assertEqual(
            "workbook-manager-table-schema-2", serialized["schema_version"]
        )
        serialized_by_name = {
            column["name"]: column for column in serialized["columns"]
        }
        self.assertEqual("money", serialized_by_name["price"]["control"]["kind"])

    def test_every_projected_family_passes_fail_closed_integrity(self):
        """Every projected spec, not only the writable ones.

        ``TABLE_SPECS`` includes the read-only projections that ``/api/tables``
        renders. Grading only ``WRITABLE_SPECS`` here let a read-only spec
        reach ``_schema_dict`` untested and 500 the whole endpoint.
        """
        from app import catalog

        self.assertTrue(
            [spec for spec in catalog.TABLE_SPECS if not spec.editable],
            "TABLE_SPECS must include the read-only projections",
        )
        for spec in catalog.TABLE_SPECS:
            with self.subTest(table=spec.table):
                with mock.patch.object(
                    __import__("app.staging", fromlist=["target_sheet_for"]),
                    "target_sheet_for",
                    return_value=None,
                ):
                    schema = self.mainmod._schema_dict(self.conn, spec, None)
                self.assertEqual(spec.editable, schema["editable"], spec.table)
                for column in schema["columns"]:
                    self.assertIn("control", column, spec.table)

    def test_read_only_projection_exposes_read_only_controls(self):
        schema = self._schema("form_sections")
        self.assertFalse(schema["editable"])
        self.assertTrue(schema["columns"])
        for column in schema["columns"]:
            self.assertEqual(
                "read_only", column["control"]["kind"], column["name"]
            )
        from app.schemas import TableSchemaOut

        # The response model requires `control` on every column, so a
        # read-only projection must serialize as well as a writable one.
        serialized = TableSchemaOut(**schema).model_dump()
        self.assertFalse(serialized["editable"])

    def test_read_only_control_metadata_gap_fails_closed(self):
        """Fail-closed still applies to read-only families (§10.2)."""
        controls = dict(registry.READONLY_SHEET_META["sections"]["controls"])
        del controls["section_id"]
        with mock.patch.dict(
            registry.READONLY_SHEET_META["sections"], {"controls": controls}
        ), mock.patch.object(
            __import__("app.staging", fromlist=["target_sheet_for"]),
            "target_sheet_for",
            return_value=None,
        ):
            with self.assertRaises(self.mainmod.SchemaIntegrityError) as caught:
                self._schema("form_sections")
        self.assertIn("form_sections.section_id", str(caught.exception))

    def test_read_only_family_with_writable_control_kind_fails_closed(self):
        controls = {
            column: dict(control)
            for column, control in
            registry.READONLY_SHEET_META["sections"]["controls"].items()
        }
        controls["section_name"] = dict(
            controls["section_name"], kind="short_text"
        )
        with mock.patch.dict(
            registry.READONLY_SHEET_META["sections"], {"controls": controls}
        ), mock.patch.object(
            __import__("app.staging", fromlist=["target_sheet_for"]),
            "target_sheet_for",
            return_value=None,
        ):
            with self.assertRaises(self.mainmod.SchemaIntegrityError):
                self._schema("form_sections")

    def test_missing_control_metadata_fails_closed(self):
        controls = dict(registry.FIELD_CONTROLS["options"])
        del controls["price"]
        with mock.patch.dict(
            registry.EDITOR_SHEET_META["options"], {"controls": controls}
        ), mock.patch.object(
            __import__("app.staging", fromlist=["target_sheet_for"]),
            "target_sheet_for",
            return_value=None,
        ):
            with self.assertRaises(self.mainmod.SchemaIntegrityError) as caught:
                self._schema("options")
        self.assertIn("options.price", str(caught.exception))

    def test_contradictory_kind_fails_closed(self):
        controls = {
            column: dict(control)
            for column, control in registry.FIELD_CONTROLS["options"].items()
        }
        controls["section_id"] = dict(controls["section_id"], kind="short_text")
        with mock.patch.dict(
            registry.EDITOR_SHEET_META["options"], {"controls": controls}
        ), mock.patch.object(
            __import__("app.staging", fromlist=["target_sheet_for"]),
            "target_sheet_for",
            return_value=None,
        ):
            with self.assertRaises(self.mainmod.SchemaIntegrityError):
                self._schema("options")

    def test_unresolved_reference_presentation_fails_closed(self):
        presentations = dict(self.mainmod.REFERENCE_OPTION_PRESENTATION)
        del presentations["form_sections"]
        with mock.patch.object(
            self.mainmod, "REFERENCE_OPTION_PRESENTATION", presentations
        ), mock.patch.object(
            __import__("app.staging", fromlist=["target_sheet_for"]),
            "target_sheet_for",
            return_value=None,
        ):
            with self.assertRaises(self.mainmod.SchemaIntegrityError):
                self._schema("options")

    def test_reference_presentation_with_unknown_column_fails_closed(self):
        presentations = dict(self.mainmod.REFERENCE_OPTION_PRESENTATION)
        presentations["form_sections"] = {
            "value": "section_id", "labels": ("missing_label",),
        }
        with mock.patch.object(
            self.mainmod, "REFERENCE_OPTION_PRESENTATION", presentations
        ), mock.patch.object(
            __import__("app.staging", fromlist=["target_sheet_for"]),
            "target_sheet_for",
            return_value=None,
        ):
            with self.assertRaises(self.mainmod.SchemaIntegrityError):
                self._schema("options")


class TestMutationPayloadGuard(unittest.TestCase):
    """Read-only/generated controls cannot enter a mutation payload."""

    def test_validate_record_rejects_read_only_fields(self):
        import sqlite3

        from app import catalog, validation

        spec = catalog.SPEC_BY_TABLE["exclusive_groups"]
        conn = sqlite3.connect(":memory:")
        try:
            # Minimal projection tables so uniqueness/reference checks run.
            cols = ", ".join(f'"{c.sql_name()}" TEXT' for c in spec.columns)
            conn.execute(f'CREATE TABLE {spec.table} ("model_id" TEXT, {cols})')
            conn.execute(
                'CREATE TABLE sheet_registry '
                '("model_key" TEXT, "sheet_name" TEXT, "source_role" TEXT)'
            )
            record = {
                "group_id": "xg_test",
                "selection_mode": "single_within_group",
                "active": "True",
            }
            base_errors = validation.validate_record(
                conn, spec, "", record, op="add"
            )
            self.assertEqual([], [e["message"] for e in base_errors])

            controls = {
                column: dict(control)
                for column, control in registry.FIELD_CONTROLS[
                    "exclusive_groups"
                ].items()
            }
            controls["notes"] = dict(controls["notes"], kind="read_only")
            record_readonly = dict(record, notes="tamper")
            with mock.patch.dict(
                registry.EDITOR_SHEET_META["exclusive_groups"],
                {"controls": controls},
            ):
                errors = validation.validate_record(
                    conn, spec, "", record_readonly, op="add"
                )
            self.assertTrue(
                any(e["field"] == "notes" for e in errors),
                f"read_only field accepted into payload: {errors}",
            )
        finally:
            conn.close()

    def test_key_field_cannot_change_on_update(self):
        import sqlite3

        from app import catalog, validation

        spec = catalog.SPEC_BY_TABLE["exclusive_groups"]
        conn = sqlite3.connect(":memory:")
        try:
            cols = ", ".join(f'"{c.sql_name()}" TEXT' for c in spec.columns)
            conn.execute(f'CREATE TABLE {spec.table} ("model_id" TEXT, {cols})')
            original = {"group_id": "xg_old"}
            changed = dict(original, group_id="xg_new",
                           selection_mode="single_within_group")
            errors = validation.validate_record(
                conn, spec, "", changed, op="update", original_key=original
            )
            self.assertTrue(
                any(e["field"] == "group_id" for e in errors),
                f"key rename accepted on update: {errors}",
            )
        finally:
            conn.close()


class TestBoundedReferenceOptions(unittest.TestCase):
    """§10.4: human-label choices are bounded, scoped, and two-query."""

    def setUp(self):
        import sqlite3

        from app import main as mainmod

        self.mainmod = mainmod
        self.conn = sqlite3.connect(":memory:", check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(
            """
            CREATE TABLE options (
              model_id TEXT, option_id TEXT, rpo TEXT, option_name TEXT,
              active TEXT
            );
            CREATE TABLE interiors (
              interior_id TEXT, interior_name TEXT, src_sheet TEXT
            );
            CREATE TABLE form_sections (
              section_id TEXT, section_name TEXT, model_context TEXT
            );
            CREATE TABLE sheet_registry (
              model_key TEXT, source_role TEXT, sheet_name TEXT
            );
            CREATE TABLE variants (
              variant_id TEXT, variant_name TEXT, active TEXT
            );
            CREATE TABLE model_variants (
              model_key TEXT, variant_id TEXT
            );
            """
        )
        self.conn.executemany(
            "INSERT INTO variants VALUES(?,?,?)",
            [
                ("var_1lt", "1LT", "True"),
                ("var_2lt", "2LT", "True"),
                ("var_1lz", "1LZ", "True"),
            ],
        )
        self.conn.executemany(
            "INSERT INTO model_variants VALUES(?,?)",
            [
                ("stingray", "var_1lt"),
                ("stingray", "var_2lt"),
                ("z06", "var_1lz"),
            ],
        )
        self.conn.executemany(
            "INSERT INTO options VALUES(?,?,?,?,?)",
            [
                ("stingray", "opt_z51_001", "Z51", "Performance Package", "True"),
                ("stingray", "opt_zz3_001", "ZZ3", "Inactive Example", "False"),
                ("z06", "opt_z07_001", "Z07", "Performance Package", "True"),
            ],
        )
        self.conn.executemany(
            "INSERT INTO interiors VALUES(?,?,?)",
            [
                ("int_black", "Jet Black", "lt_interiors"),
                ("int_z06", "Adrenaline Red", "LZ_Interiors"),
            ],
        )
        self.conn.executemany(
            "INSERT INTO form_sections VALUES(?,?,?)",
            [
                ("sec_pain_001", "Exterior Color", '["stingray","z06"]'),
                ("sec_whee_001", "Wheels", '["stingray"]'),
            ],
        )
        self.conn.executemany(
            "INSERT INTO sheet_registry VALUES(?,?,?)",
            [
                ("stingray", "interior_source_sheet", "lt_interiors"),
                ("z06", "interior_source_sheet", "LZ_Interiors"),
            ],
        )

    def tearDown(self):
        self.conn.close()

    def _options(self, table, field, **kwargs):
        return self.mainmod._reference_options(
            self.conn,
            self.mainmod.SPEC_BY_TABLE[table],
            field,
            kwargs.get("model", ""),
            kwargs.get("query", ""),
            kwargs.get("discriminator", ""),
            kwargs.get("limit", 25),
            kwargs.get("offset", 0),
        )

    def test_direct_reference_uses_human_label_stable_order_and_two_queries(self):
        statements = []
        self.conn.set_trace_callback(statements.append)
        try:
            response = self._options(
                "options", "section_id", query="exterior", limit=1
            )
        finally:
            self.conn.set_trace_callback(None)
        selects = [
            sql for sql in statements if sql.lstrip().upper().startswith("WITH")
        ]
        self.assertEqual(2, len(selects), statements)
        self.assertEqual(
            "workbook-manager-reference-options-1", response["schema_version"]
        )
        self.assertEqual(1, response["total"])
        self.assertEqual(
            {
                "value": "sec_pain_001", "label": "Exterior Color",
                "secondary": "sec_pain_001", "active": True,
            },
            response["options"][0],
        )

    def test_union_reference_is_model_scoped_and_deduplicated(self):
        response = self._options(
            "rule_mappings", "source_id", model="stingray"
        )
        by_value = {item["value"]: item for item in response["options"]}
        self.assertEqual(
            {"int_black", "opt_z51_001", "opt_zz3_001"}, set(by_value)
        )
        self.assertEqual(
            "Z51 Performance Package", by_value["opt_z51_001"]["label"]
        )
        self.assertFalse(by_value["opt_zz3_001"]["active"])

    def test_conditional_rpo_reference_uses_discriminator_and_model(self):
        response = self._options(
            "default_selection_rules",
            "condition_id",
            discriminator="unless_selected_rpo",
            model="stingray",
        )
        self.assertEqual("model", response["scope"])
        self.assertEqual(
            ["Z51", "ZZ3"], [row["value"] for row in response["options"]]
        )

    def test_conditional_no_target_domain_is_empty_without_query(self):
        statements = []
        self.conn.set_trace_callback(statements.append)
        try:
            response = self._options(
                "default_selection_rules",
                "condition_id",
                discriminator="always",
                model="stingray",
            )
        finally:
            self.conn.set_trace_callback(None)
        self.assertEqual(0, response["total"])
        self.assertEqual([], statements)

    def test_model_scoped_reference_requires_model(self):
        from fastapi import HTTPException

        with self.assertRaises(HTTPException) as caught:
            self._options("rule_mappings", "source_id")
        self.assertEqual(422, caught.exception.status_code)

    def test_global_variant_reference_is_narrowed_to_the_model(self):
        """A `global` RefSpec must still not offer another model's variants.

        `option_availability.variant_id` is declared `global`, so nothing
        filtered it and the picker offered every row of `variant_master`.
        """
        scoped = self._options(
            "option_availability", "variant_id", model="stingray"
        )
        self.assertEqual(
            ["var_1lt", "var_2lt"],
            sorted(o["value"] for o in scoped["options"]),
        )
        self.assertEqual(2, scoped["total"])

        other = self._options("option_availability", "variant_id", model="z06")
        self.assertEqual(
            ["var_1lz"], [o["value"] for o in other["options"]]
        )

    def test_global_reference_stays_unfiltered_without_a_model(self):
        """Narrowing must not newly require a model on a `global` field."""
        every = self._options("option_availability", "variant_id")
        self.assertEqual(3, every["total"])

    def test_global_interior_reference_is_narrowed_for_model_owned_rows(self):
        scoped = self._options(
            "model_interior_scope", "interior_id", model="z06"
        )
        self.assertEqual(
            ["int_z06"], [o["value"] for o in scoped["options"]]
        )

    def test_global_reference_from_unowned_row_is_not_narrowed(self):
        """`color_overrides` rows have no model identity.

        Restricting their interior choice to one model would block legitimate
        shared authoring, so a supplied model is browsing context only.
        """
        from app import catalog

        spec = catalog.SPEC_BY_TABLE["color_overrides"]
        self.assertFalse(spec.model_scoped)
        self.assertFalse(spec.has_model_key_column)
        scoped = self._options(
            "color_overrides", "interior_id", model="stingray"
        )
        self.assertEqual(
            ["int_black", "int_z06"],
            sorted(o["value"] for o in scoped["options"]),
        )

    def test_section_reference_is_not_narrowed_by_model(self):
        """Sections stay unfiltered for `global` refs.

        Projected `model_context` is empty for every section, so narrowing
        here would empty the picker rather than scope it. Deliberate: see
        `_model_partition_sql`.
        """
        self.conn.execute("UPDATE form_sections SET model_context='[]'")
        scoped = self._options("options", "section_id", model="stingray")
        self.assertEqual(2, scoped["total"])

    def test_narrowed_reference_still_uses_exactly_two_queries(self):
        statements = []
        self.conn.set_trace_callback(statements.append)
        try:
            self._options(
                "option_availability", "variant_id", model="stingray"
            )
        finally:
            self.conn.set_trace_callback(None)
        self.assertEqual(2, len(statements), statements)

    def test_http_route_is_additive_and_enforces_limit_bound(self):
        from fastapi.testclient import TestClient

        def projection_override():
            yield self.conn

        self.mainmod.app.dependency_overrides[
            self.mainmod.projection_connection
        ] = projection_override
        client = TestClient(self.mainmod.app)
        try:
            response = client.get(
                "/api/records/options/reference-options",
                params={"field": "section_id", "limit": 1},
            )
            self.assertEqual(200, response.status_code, response.text)
            self.assertEqual(2, response.json()["total"])
            refused = client.get(
                "/api/records/options/reference-options",
                params={"field": "section_id", "limit": 101},
            )
            self.assertEqual(422, refused.status_code)
        finally:
            client.close()
            self.mainmod.app.dependency_overrides.clear()


if __name__ == "__main__":
    unittest.main()
