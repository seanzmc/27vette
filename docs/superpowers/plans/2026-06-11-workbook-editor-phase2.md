# Workbook Editor Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Phase 2 of `workbook-editor-phase2-spec.md` — the gated, non-breaking write path: typed op engine with coalescing and server-side validation, atomic apply through `save_workbook_safely()` with dry-run + table healing, POST endpoints, `apply_workbook_ops.py` CLI, committed apply log, and the guided edit UI (structured row forms, Add Option / group wizards, Pending Changes tab).

**Architecture:** All write logic lives in `corvette_form_generator/editor_ops.py` (`flatten_items` → `coalesce_ops` → `_prepare_batch` (coerce + validate) → `apply_batch` (lock/mtime guards → dry-run on temp copy with package+schema validation → real apply via `save_workbook_safely` → log)). The server and CLI are thin shells over `apply_batch`. Workbook-extraction helpers move from the server into `editor_ops` so imports stay one-directional (server → editor_ops). The UI queues ops client-side and only the server decides.

**Tech stack:** unchanged from Phase 1 (stdlib + openpyxl; vendored Preact/htm).

**Verified facts:** see spec §1. Notably: `assert_valid_workbook_package` imports from `corvette_form_generator.workbook_package`; `validate_workbook_schema`/`result_payload` from `corvette_form_generator.schema_validation`; 4 GS table refs are stale and must be healed by resize-to-extent; all family keys are string ids; openpyxl's `ws.cell(row, col, value=None)` does NOT clear a cell — use `cell.value = None` assignment.

---

### Task 1: Extend reference domains in the payload

**Files:**
- Modify: `scripts/workbook_editor_server.py` (`build_payload` referenceDomains)
- Modify: `tests/test_editor_server_payload.py` (fixture + assertions)

Add `ruleGroupsByModel`, `exclusiveGroupsByModel`, `interiorsByModel` to `referenceDomains`, built the same way as `optionsByModel` (per model, from the registry's family sheet): groups → `{"id": group_id}`, interiors → `{"id": interior_id, "name": row["Interior Name"]}`.

- [ ] **Step 1: Extend the fixture and add failing assertions.** In `build_fixture_workbook()` add to `model_workbook_sources` two active stingray rows: `rule_groups_sheet`→`rule_groups`, `rule_group_members_sheet`→`rule_group_members`; and append the sheets:

```python
    append_sheet(
        wb, "rule_groups",
        ["group_id", "group_type", "source_id", "active", "notes"],
        [{"group_id": "grp_alpha", "group_type": "requires_any",
          "source_id": "opt_z51_001", "active": True}],
    )
    append_sheet(
        wb, "rule_group_members",
        ["group_id", "target_id", "display_order", "active"],
        [{"group_id": "grp_alpha", "target_id": "opt_gkz_001", "display_order": 10, "active": True}],
    )
```

New test in `ReferenceDomainsTest`:

```python
    def test_group_and_interior_domains(self):
        dom = self.payload["referenceDomains"]
        self.assertEqual([g["id"] for g in dom["ruleGroupsByModel"]["stingray"]], ["grp_alpha"])
        self.assertEqual(dom["exclusiveGroupsByModel"], {})
        self.assertEqual(dom["interiorsByModel"], {})
```

And in `RealWorkbookIntegrationTest`:

```python
    def test_group_domains_real(self):
        dom = self.payload["referenceDomains"]
        self.assertTrue(any(g["id"] for g in dom["exclusiveGroupsByModel"]["z06"]))
        self.assertTrue(any(i["id"] for i in dom["interiorsByModel"]["stingray"]))
```

- [ ] **Step 2: Run to verify failure** — `.venv/bin/python -m unittest tests.test_editor_server_payload -v` → FAIL (KeyError ruleGroupsByModel).
- [ ] **Step 3: Implement** in `build_payload` (next to `options_by_model`):

```python
    def _ids_by_model(family: str, id_col: str, name_col: str | None = None) -> dict:
        out: dict[str, list[dict]] = {}
        for model_key, entries in model_sheets.items():
            src = next((e["sheet"] for e in entries if e["family"] == family), None)
            if not src:
                continue
            rows = [
                ({"id": row.get(id_col), "name": row.get(name_col)} if name_col
                 else {"id": row.get(id_col)})
                for row in _rows_of(extract, src)
                if row.get(id_col)
            ]
            if rows:
                out[model_key] = rows
        return out
```

and in `referenceDomains`: `"ruleGroupsByModel": _ids_by_model("rule_groups", "group_id")`, `"exclusiveGroupsByModel": _ids_by_model("exclusive_groups", "group_id")`, `"interiorsByModel": _ids_by_model("interiors", "interior_id", "Interior Name")`.

- [ ] **Step 4: Tests pass**, then commit: `feat: serve group and interior reference domains for guided editing`.

---

### Task 2: Move extraction helpers into editor_ops; add flatten/coalesce/coerce

**Files:**
- Modify: `scripts/corvette_form_generator/editor_ops.py`
- Modify: `scripts/workbook_editor_server.py` (import the moved helpers)
- Test: `tests/test_editor_ops_apply.py` (new)

- [ ] **Step 1: Move helpers.** Cut `jsonable`, `extract_workbook` from the server; cut `_rows_of`/`_model_sheets` and re-home them in `editor_ops.py` as `rows_of(extract, name)` and `model_sheet_registry(extract)` (same bodies; `model_sheet_registry` returns `(registry, sheet_family)`). `editor_ops.py` gains imports:

```python
import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from openpyxl import load_workbook

from corvette_form_generator.workbook import (
    excel_lock_path,
    remove_table_sheet_auto_filters,
    save_workbook_safely,
    workbook_truthy,
)
from corvette_form_generator.workbook_package import assert_valid_workbook_package
from corvette_form_generator.schema_validation import result_payload, validate_workbook_schema

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOG_PATH = ROOT / "form-output" / "workbook-edit-log.jsonl"
```

(`jsonable` + `extract_workbook` move verbatim, with `datetime, date` import adjusted.) The server replaces its definitions with `from corvette_form_generator.editor_ops import extract_workbook, jsonable, model_sheet_registry, rows_of` and keeps `_rows_of = rows_of`, `_model_sheets = model_sheet_registry` aliases so `build_payload` is untouched and the Phase 1 payload tests (which import `extract_workbook` from the server module) still pass.

- [ ] **Step 2: Failing tests for flatten/coalesce/coerce** — create `tests/test_editor_ops_apply.py` with the standard sys.path header (as in `tests/test_editor_ops_meta.py`) and:

```python
from corvette_form_generator.editor_ops import (  # noqa: E402
    coalesce_ops,
    coerce_value,
    flatten_items,
)


def op(action, sheet, key, row=None, **extra):
    out = {"action": action, "sheet": sheet, "key": key}
    if row is not None:
        out["row"] = row
    out.update(extra)
    return out


class FlattenTest(unittest.TestCase):
    def test_composite_members_carry_label(self):
        items = [{"kind": "composite", "label": "Add XYZ", "ops": [
            op("add", "s", {"option_id": "a"}, {"option_id": "a"})]}]
        flat = flatten_items(items)
        self.assertEqual(flat[0]["_composite"], "Add XYZ")

    def test_plain_ops_pass_through(self):
        flat = flatten_items([op("delete", "s", {"option_id": "a"})])
        self.assertEqual(flat[0]["action"], "delete")


class CoalesceTest(unittest.TestCase):
    K = {"option_id": "a"}

    def test_update_update_merges_later_wins(self):
        out = coalesce_ops([op("update", "s", self.K, {"price": 1, "rpo": "X"}),
                            op("update", "s", self.K, {"price": 2})])
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["row"], {"price": 2, "rpo": "X"})

    def test_add_update_merges_into_add(self):
        out = coalesce_ops([op("add", "s", self.K, {"option_id": "a", "price": 1}),
                            op("update", "s", self.K, {"price": 2})])
        self.assertEqual(out[0]["action"], "add")
        self.assertEqual(out[0]["row"]["price"], 2)

    def test_add_delete_cancels(self):
        out = coalesce_ops([op("add", "s", self.K, {"option_id": "a"}),
                            op("delete", "s", self.K)])
        self.assertEqual(out, [])

    def test_update_delete_becomes_delete(self):
        out = coalesce_ops([op("update", "s", self.K, {"price": 1}),
                            op("delete", "s", self.K)])
        self.assertEqual([o["action"] for o in out], ["delete"])

    def test_delete_is_a_barrier(self):
        out = coalesce_ops([op("delete", "s", self.K),
                            op("add", "s", self.K, {"option_id": "a"})])
        self.assertEqual([o["action"] for o in out], ["delete", "add"])

    def test_different_keys_untouched(self):
        out = coalesce_ops([op("update", "s", {"option_id": "a"}, {"price": 1}),
                            op("update", "s", {"option_id": "b"}, {"price": 2})])
        self.assertEqual(len(out), 2)


class CoerceTest(unittest.TestCase):
    def test_int(self):
        self.assertEqual(coerce_value("options", "price", 500), 500)
        self.assertEqual(coerce_value("options", "price", "500"), 500)
        self.assertIsNone(coerce_value("options", "price", ""))
        with self.assertRaises(ValueError):
            coerce_value("options", "price", "abc")
        with self.assertRaises(ValueError):
            coerce_value("options", "price", True)

    def test_bool(self):
        self.assertIs(coerce_value("options", "selectable", True), True)
        self.assertIs(coerce_value("options", "selectable", "False"), False)
        with self.assertRaises(ValueError):
            coerce_value("options", "selectable", "yes")

    def test_enum(self):
        self.assertEqual(coerce_value("ovs", "status", "standard"), "standard")
        with self.assertRaises(ValueError):
            coerce_value("ovs", "status", "maybe")
        # blank allowed only when "" is in the domain
        self.assertIsNone(coerce_value("options", "display_behavior", ""))
        with self.assertRaises(ValueError):
            coerce_value("ovs", "status", "")

    def test_tristate_text_enum_stays_text(self):
        self.assertEqual(coerce_value("variant_overrides", "selectable", "True"), "True")

    def test_free_text_stripped(self):
        self.assertEqual(coerce_value("options", "option_name", "  X  "), "X")
        self.assertIsNone(coerce_value("options", "description", ""))
```

- [ ] **Step 3: Verify failure** (ImportError), then implement in `editor_ops.py`:

```python
def flatten_items(items) -> list[dict]:
    ops: list[dict] = []
    for item in items or []:
        if isinstance(item, dict) and item.get("kind") == "composite":
            label = item.get("label") or item.get("compositeType") or "composite"
            for member in item.get("ops", []):
                member = dict(member)
                member["_composite"] = label
                ops.append(member)
        else:
            ops.append(dict(item))
    return ops


def _key_id(op: dict) -> tuple:
    return (op.get("sheet"), tuple(sorted(
        (str(k), str(v).strip()) for k, v in (op.get("key") or {}).items())))


def coalesce_ops(ops: list[dict]) -> list[dict]:
    result: list[dict | None] = []
    last_live: dict[tuple, int] = {}
    for op in ops:
        kid = _key_id(op)
        pos = last_live.get(kid)
        prev = result[pos] if pos is not None else None
        action = op.get("action")
        if prev is None or prev.get("action") == "delete":
            last_live[kid] = len(result)
            result.append(dict(op))
            continue
        prev_action = prev.get("action")
        if action == "update" and prev_action in ("add", "update"):
            prev["row"] = {**(prev.get("row") or {}), **(op.get("row") or {})}
        elif action == "delete" and prev_action == "add":
            result[pos] = None
            last_live.pop(kid, None)
        elif action == "delete" and prev_action == "update":
            result[pos] = {k: v for k, v in op.items()}
        else:  # add after add/update etc. — leave both; validation flags it
            last_live[kid] = len(result)
            result.append(dict(op))
    return [op for op in result if op is not None]


def coerce_value(family: str, column: str, value):
    meta = EDITOR_SHEET_META[family]
    if value == "":
        value = None
    enums = meta.get("enums", {}).get(column)
    if enums is not None:
        text = "" if value is None else str(value).strip()
        if text not in enums:
            raise ValueError(f"{column}: {text!r} not in enum {sorted(enums)}")
        return text or None
    kind = meta.get("types", {}).get(column)
    if kind == "int":
        if value is None:
            return None
        if isinstance(value, bool):
            raise ValueError(f"{column}: expected integer, got boolean")
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        text = str(value).strip()
        if text.lstrip("-").isdigit():
            return int(text)
        raise ValueError(f"{column}: expected integer, got {value!r}")
    if kind == "bool":
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.strip() in ("True", "False"):
            return value.strip() == "True"
        raise ValueError(f"{column}: expected True/False, got {value!r}")
    if value is None:
        return None
    return str(value).strip() or None
```

- [ ] **Step 4: All editor + payload tests pass**, commit: `feat: op flattening, coalescing, and typed coercion for workbook edits`.

---

### Task 3: `_prepare_batch` — validation matrix

**Files:** modify `editor_ops.py`; extend `tests/test_editor_ops_apply.py`.

- [ ] **Step 1: Fixture + failing tests.** Add a fixture builder to the test file (richer than the payload one — stingray fully wired, zr1 scaffold):

```python
import tempfile
from openpyxl import Workbook
from openpyxl.worksheet.table import Table

from workbook_editor_server import extract_workbook  # noqa: E402  (re-exported)
from corvette_form_generator.editor_ops import validate_batch  # noqa: E402


def append_sheet(wb, name, headers, rows):
    ws = wb.create_sheet(name)
    ws.append(headers)
    for row in rows:
        ws.append([row.get(h) for h in headers])
    return ws


OPTION_HEADERS = ["option_id", "rpo", "price", "option_name", "description", "detail_raw",
                  "section_id", "selectable", "display_order", "active", "display_behavior"]


def option_row(oid, rpo, section, order):
    return {"option_id": oid, "rpo": rpo, "price": 0, "option_name": rpo,
            "section_id": section, "selectable": True, "display_order": order, "active": True}


def build_ops_fixture() -> Workbook:
    wb = Workbook()
    del wb[wb.sheetnames[0]]
    append_sheet(wb, "model_master",
                 ["model_key", "model_label", "default_model", "active"],
                 [{"model_key": "stingray", "model_label": "Stingray", "default_model": True, "active": True},
                  {"model_key": "zr1", "model_label": "ZR1", "default_model": False, "active": False}])
    append_sheet(wb, "model_registry_promotion",
                 ["model_key", "promoted_to_runtime", "display_order", "active"],
                 [{"model_key": "stingray", "promoted_to_runtime": True, "display_order": 1, "active": True}])
    src = [
        ("stingray", "source_option_sheet", "stingray_options"),
        ("stingray", "status_sheet", "stingray_ovs"),
        ("stingray", "rule_groups_sheet", "rule_groups"),
        ("stingray", "rule_group_members_sheet", "rule_group_members"),
        ("stingray", "exclusive_groups_sheet", "exclusive_groups"),
        ("stingray", "exclusive_group_members_sheet", "exclusive_group_members"),
        ("stingray", "price_rules_sheet", "price_rules"),
        ("zr1", "source_option_sheet", "zr1_options"),
        ("zr1", "status_sheet", "zr1_ovs"),
    ]
    append_sheet(wb, "model_workbook_sources",
                 ["model_key", "source_role", "sheet_name", "active"],
                 [{"model_key": m, "source_role": r, "sheet_name": s, "active": True} for m, r, s in src])
    append_sheet(wb, "variant_master", ["variant_id", "display_name", "active"],
                 [{"variant_id": "1lt", "display_name": "1LT", "active": True},
                  {"variant_id": "2lt", "display_name": "2LT", "active": True},
                  {"variant_id": "zr1_c", "display_name": "ZR1", "active": False}])
    append_sheet(wb, "model_variants", ["model_key", "variant_id", "display_order", "active"],
                 [{"model_key": "stingray", "variant_id": "1lt", "display_order": 1, "active": True},
                  {"model_key": "stingray", "variant_id": "2lt", "display_order": 2, "active": True},
                  {"model_key": "zr1", "variant_id": "zr1_c", "display_order": 1, "active": True}])
    append_sheet(wb, "section_master", ["section_id", "section_name", "step_key"],
                 [{"section_id": "sec_a", "section_name": "A", "step_key": "paint"},
                  {"section_id": "sec_b", "section_name": "B", "step_key": "wheels"}])
    ws = append_sheet(wb, "stingray_options", OPTION_HEADERS,
                      [option_row("opt_one_001", "ONE", "sec_a", 10),
                       option_row("opt_two_001", "TWO", "sec_a", 20),
                       option_row("opt_thr_001", "THR", "sec_b", 10)])
    # deliberately stale table ref: data goes to row 4, ref claims row 3
    ws.add_table(Table(displayName="tbl_fixture_options", ref="A1:K3"))
    append_sheet(wb, "stingray_ovs", ["option_id", "variant_id", "status"],
                 [{"option_id": "opt_one_001", "variant_id": "1lt", "status": "available"},
                  {"option_id": "opt_one_001", "variant_id": "2lt", "status": "standard"}])
    append_sheet(wb, "rule_groups", ["group_id", "group_type", "source_id", "active", "notes"],
                 [{"group_id": "grp_one", "group_type": "requires_any", "source_id": "opt_one_001", "active": True}])
    append_sheet(wb, "rule_group_members", ["group_id", "target_id", "display_order", "active"],
                 [{"group_id": "grp_one", "target_id": "opt_two_001", "display_order": 10, "active": True}])
    append_sheet(wb, "exclusive_groups", ["group_id", "selection_mode", "active", "notes"],
                 [{"group_id": "excl_one", "selection_mode": "single_within_group", "active": True}])
    append_sheet(wb, "exclusive_group_members", ["group_id", "option_id", "display_order", "active"],
                 [{"group_id": "excl_one", "option_id": "opt_one_001", "display_order": 10, "active": True},
                  {"group_id": "excl_one", "option_id": "opt_two_001", "display_order": 20, "active": True}])
    append_sheet(wb, "price_rules",
                 ["price_rule_id", "condition_option_id", "price_rule_type", "target_option_id",
                  "price_value", "body_style_scope", "trim_level_scope", "notes"], [])
    append_sheet(wb, "zr1_options", OPTION_HEADERS, [option_row("opt_zzz_001", "ZZZ", "sec_a", 10)])
    append_sheet(wb, "zr1_ovs", ["option_id", "variant_id", "status"],
                 [{"option_id": "opt_zzz_001", "variant_id": "zr1_c", "status": "available"}])
    append_sheet(wb, "form_steps", ["step_key"], [{"step_key": "paint"}])
    return wb


class OpsFixtureBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._dir = tempfile.TemporaryDirectory()
        cls.wb_path = Path(cls._dir.name) / "fixture.xlsx"
        build_ops_fixture().save(cls.wb_path)
        cls.extract = extract_workbook(cls.wb_path)

    @classmethod
    def tearDownClass(cls):
        cls._dir.cleanup()


def batch(*items, mtime=None):
    return {"version": 1, "workbook": "fixture.xlsx", "workbookMtimeNs": mtime, "items": list(items)}


def add_option_composite(oid="opt_new_001", statuses=("available", "available"), section="sec_a", order=30):
    row = option_row(oid, oid[4:7].upper(), section, order)
    row.update({"description": None, "detail_raw": None, "display_behavior": None})
    ops = [op("add", "stingray_options", {"option_id": oid}, row)]
    for vid, status in zip(("1lt", "2lt"), statuses):
        if status is not None:
            ops.append(op("add", "stingray_ovs", {"option_id": oid, "variant_id": vid},
                          {"option_id": oid, "variant_id": vid, "status": status}))
    return {"kind": "composite", "label": f"Add {oid}", "ops": ops}


class ValidateBatchTest(OpsFixtureBase):
    def errors_of(self, *items):
        return validate_batch(self.extract, batch(*items))["errors"]

    def warnings_of(self, *items):
        return validate_batch(self.extract, batch(*items))["warnings"]

    def test_clean_add_option_composite(self):
        result = validate_batch(self.extract, batch(add_option_composite()))
        self.assertEqual(result["errors"], [])

    def test_readonly_and_unknown_sheet(self):
        self.assertTrue(self.errors_of(op("update", "form_steps", {"step_key": "paint"}, {"step_key": "x"})))
        self.assertTrue(self.errors_of(op("update", "section_master", {"section_id": "sec_a"}, {"section_name": "X"})))
        self.assertTrue(self.errors_of(op("update", "nope", {"option_id": "a"}, {})))

    def test_unknown_column_and_immutable_key(self):
        self.assertTrue(self.errors_of(op("update", "stingray_options", {"option_id": "opt_one_001"}, {"bogus": 1})))
        self.assertTrue(self.errors_of(op("update", "stingray_options", {"option_id": "opt_one_001"}, {"option_id": "x"})))

    def test_key_existence(self):
        self.assertTrue(self.errors_of(op("update", "stingray_options", {"option_id": "missing"}, {"price": 1})))
        self.assertTrue(self.errors_of(op("add", "stingray_options", {"option_id": "opt_one_001"},
                                          option_row("opt_one_001", "ONE", "sec_a", 99))))

    def test_type_enum_ref_violations(self):
        self.assertTrue(self.errors_of(op("update", "stingray_options", {"option_id": "opt_one_001"}, {"price": "abc"})))
        self.assertTrue(self.errors_of(op("update", "stingray_ovs",
                                          {"option_id": "opt_one_001", "variant_id": "1lt"}, {"status": "maybe"})))
        self.assertTrue(self.errors_of(op("update", "stingray_options", {"option_id": "opt_one_001"},
                                          {"section_id": "sec_nope"})))

    def test_batch_aware_refs(self):
        # OVS rows referencing the option added in the same batch are fine
        result = validate_batch(self.extract, batch(add_option_composite()))
        self.assertEqual(result["errors"], [])
        # but a lone OVS add for an unknown option is not
        self.assertTrue(self.errors_of(op("add", "stingray_ovs",
                                          {"option_id": "opt_ghost_001", "variant_id": "1lt"},
                                          {"option_id": "opt_ghost_001", "variant_id": "1lt", "status": "available"})))

    def test_ovs_coverage_enforced(self):
        partial = add_option_composite(statuses=("available", None))  # missing 2lt
        errors = self.errors_of(partial)
        self.assertTrue(any("OVS coverage" in e and "2lt" in e for e in errors))

    def test_group_integrity(self):
        lone_group = op("add", "rule_groups", {"group_id": "grp_new"},
                        {"group_id": "grp_new", "group_type": "requires_any",
                         "source_id": "opt_one_001", "active": True, "notes": None})
        self.assertTrue(any("member" in e for e in self.errors_of(lone_group)))
        lone_excl = op("add", "exclusive_groups", {"group_id": "excl_new"},
                       {"group_id": "excl_new", "selection_mode": "single_within_group",
                        "active": True, "notes": None})
        self.assertTrue(any("member" in e for e in self.errors_of(lone_excl)))

    def test_display_order_collision_warns(self):
        warnings = self.warnings_of(op("update", "stingray_options", {"option_id": "opt_two_001"},
                                       {"display_order": 10}))
        self.assertTrue(any(w["id"].startswith("dorder:") for w in warnings))

    def test_referenced_delete_warns(self):
        warnings = self.warnings_of(op("delete", "stingray_options", {"option_id": "opt_one_001"}))
        self.assertTrue(any(w["id"].startswith("refdel:") for w in warnings))
        # deleting the referencing rows in the same batch silences it
        items = [op("delete", "stingray_ovs", {"option_id": "opt_one_001", "variant_id": "1lt"}),
                 op("delete", "stingray_ovs", {"option_id": "opt_one_001", "variant_id": "2lt"}),
                 op("delete", "rule_groups", {"group_id": "grp_one"}),
                 op("delete", "rule_group_members", {"group_id": "grp_one", "target_id": "opt_two_001"}),
                 op("delete", "exclusive_group_members", {"group_id": "excl_one", "option_id": "opt_one_001"}),
                 op("delete", "stingray_options", {"option_id": "opt_one_001"})]
        warnings = self.warnings_of(*items)
        self.assertFalse(any(w["id"] == "refdel:stingray_options:opt_one_001" for w in warnings))

    def test_scaffold_model_warns(self):
        warnings = self.warnings_of(op("update", "zr1_options", {"option_id": "opt_zzz_001"}, {"price": 1}))
        self.assertTrue(any(w["id"] == "scaffold:zr1_options" for w in warnings))
```

- [ ] **Step 2: Verify failure**, then implement `_prepare_batch` + `validate_batch` in `editor_ops.py`:

```python
CHILD_REFS_BY_FAMILY = {
    "options": [("ovs", "option_id"), ("rule_mapping", "source_id"), ("rule_mapping", "target_id"),
                ("rule_group_members", "target_id"), ("exclusive_members", "option_id"),
                ("price_rules", "condition_option_id"), ("price_rules", "target_option_id"),
                ("color_overrides", "option_id"), ("variant_overrides", "option_id"),
                ("interiors", "included_option_id")],
    "rule_groups": [("rule_group_members", "group_id")],
    "exclusive_groups": [("exclusive_members", "group_id")],
    "interiors": [("color_overrides", "interior_id")],
}

_REF_FAMILY = {"options": ("options", "option_id"), "rule_groups": ("rule_groups", "group_id"),
               "exclusive_groups": ("exclusive_groups", "group_id"),
               "interiors": ("interiors", "interior_id")}

_DORDER_GROUP_COL = {"options": "section_id", "rule_group_members": "group_id",
                     "exclusive_members": "group_id"}


def _registry_maps(extract):
    registry, sheet_family = model_sheet_registry(extract)
    models_by_sheet: dict[str, set] = {}
    by_model_family: dict[tuple, str] = {}
    for model_key, entries in registry.items():
        for entry in entries:
            models_by_sheet.setdefault(entry["sheet"], set()).add(model_key)
            by_model_family[(model_key, entry["family"])] = entry["sheet"]
    return registry, sheet_family, models_by_sheet, by_model_family


def _key_tuple(key, keycols):
    return tuple(str(key.get(k) or "").strip() for k in keycols)


def _sheet_key_index(extract, sheet, keycols):
    index = {}
    for row in rows_of(extract, sheet):
        kt = tuple(str(row.get(k) or "").strip() for k in keycols)
        if all(kt):
            index[kt] = row
    return index


def _ref_domain(extract, maps, batch_adds, sheet, refkind):
    _registry, _sheet_family, models_by_sheet, by_model_family = maps
    models = models_by_sheet.get(sheet, set())
    if refkind == "sections":
        return {str(r.get("section_id")).strip()
                for r in rows_of(extract, "section_master") if r.get("section_id")}
    if refkind == "variants":
        ids = {str(r.get("variant_id")).strip()
               for r in rows_of(extract, "model_variants")
               if r.get("model_key") in models and workbook_truthy(r.get("active"))}
        return ids or {str(r.get("variant_id")).strip()
                       for r in rows_of(extract, "variant_master") if r.get("variant_id")}
    family, id_col = _REF_FAMILY[refkind]
    ids = set()
    for model in models:
        src = by_model_family.get((model, family))
        if not src:
            continue
        ids |= {str(r.get(id_col)).strip() for r in rows_of(extract, src) if r.get(id_col)}
        ids |= {str((o.get("row") or {}).get(id_col)).strip()
                for o in batch_adds.get(src, []) if (o.get("row") or {}).get(id_col)}
    return ids


def _prepare_batch(extract, batch):
    errors: list[str] = []
    warnings: list[dict] = []
    ops = coalesce_ops(flatten_items(batch.get("items") or []))
    maps = _registry_maps(extract)
    _registry, sheet_family, models_by_sheet, by_model_family = maps
    promoted = {r.get("model_key"): workbook_truthy(r.get("promoted_to_runtime"))
                for r in rows_of(extract, "model_registry_promotion")}

    batch_adds: dict[str, list] = {}
    deleted_keys: set[tuple] = set()
    for o in ops:
        if o.get("action") == "add":
            batch_adds.setdefault(o.get("sheet"), []).append(o)
        if o.get("action") == "delete":
            deleted_keys.add(_key_id(o))

    key_indexes: dict[str, dict] = {}
    seen_adds: set = set()
    prepared: list[dict] = []
    scaffold_warned: set[str] = set()

    for i, o in enumerate(ops):
        action, sheet = o.get("action"), o.get("sheet")
        ctx = f"op[{i}] {action} {sheet} {o.get('key')}"
        if action not in ("add", "update", "delete"):
            errors.append(f"{ctx}: unknown action"); continue
        family = sheet_family.get(sheet)
        if not family or str(sheet).startswith("form_"):
            errors.append(f"{ctx}: sheet is not editable"); continue
        data = extract["sheets"].get(sheet)
        if data is None:
            errors.append(f"{ctx}: sheet not found in workbook"); continue
        headers = set(data["headers"])
        meta = EDITOR_SHEET_META[family]
        keycols = list(meta["key"])
        key = o.get("key") or {}
        if sorted(key) != sorted(keycols):
            errors.append(f"{ctx}: key must be exactly {keycols}"); continue
        if any(not str(v or "").strip() for v in key.values()):
            errors.append(f"{ctx}: blank key value"); continue
        row = {k: v for k, v in (o.get("row") or {}).items() if not str(k).startswith("_")}
        unknown = sorted(c for c in row if c not in headers)
        if unknown:
            errors.append(f"{ctx}: unknown column(s) {unknown}"); continue
        if action == "update" and any(c in row for c in keycols):
            errors.append(f"{ctx}: key columns are immutable on update"); continue
        coerced = {}
        bad = False
        for col, val in row.items():
            try:
                coerced[col] = coerce_value(family, col, val)
            except ValueError as exc:
                errors.append(f"{ctx}: {exc}"); bad = True
        if bad:
            continue
        for col, refkind in meta.get("refs", {}).items():
            if coerced.get(col) is not None:
                domain = _ref_domain(extract, maps, batch_adds, sheet, refkind)
                if str(coerced[col]) not in domain:
                    errors.append(f"{ctx}: {col}={coerced[col]!r} not found in {refkind}"); bad = True
        if bad:
            continue
        if sheet not in key_indexes:
            key_indexes[sheet] = _sheet_key_index(extract, sheet, keycols)
        kt = _key_tuple(key, keycols)
        if action == "add":
            if any(str(coerced.get(k) or "").strip() != kt[idx] for idx, k in enumerate(keycols)):
                errors.append(f"{ctx}: add row must include key columns matching the key"); continue
            if kt in key_indexes[sheet] or (sheet, kt) in seen_adds:
                errors.append(f"{ctx}: duplicate key"); continue
            seen_adds.add((sheet, kt))
        else:
            if kt not in key_indexes[sheet]:
                errors.append(f"{ctx}: row not found for key"); continue
        models = models_by_sheet.get(sheet, set())
        if models and not any(promoted.get(m) for m in models) and sheet not in scaffold_warned:
            scaffold_warned.add(sheet)
            warnings.append({"id": f"scaffold:{sheet}",
                             "message": f"{sheet}: model is not promoted to runtime (scaffold)"})
        o = dict(o)
        o["_family"] = family
        o["_coerced_row"] = coerced
        o["_kt"] = kt
        prepared.append(o)

    if errors:
        return errors, warnings, prepared

    # composite-level integrity
    for o in prepared:
        if o["action"] != "add":
            continue
        family, sheet = o["_family"], o["sheet"]
        models = models_by_sheet.get(sheet, set())
        if family == "options":
            oid = o["_kt"][0]
            for model in models:
                ovs_sheet = by_model_family.get((model, "ovs"))
                if not ovs_sheet:
                    continue
                for vrow in rows_of(extract, "model_variants"):
                    if vrow.get("model_key") != model or not workbook_truthy(vrow.get("active")):
                        continue
                    vid = str(vrow.get("variant_id")).strip()
                    covered = any(p["action"] == "add" and p["sheet"] == ovs_sheet
                                  and p["_kt"] == (oid, vid) for p in prepared)
                    if not covered:
                        errors.append(f"add option {oid}: missing OVS coverage for variant {vid} in {ovs_sheet}")
        if family in ("rule_groups", "exclusive_groups"):
            member_family = "rule_group_members" if family == "rule_groups" else "exclusive_members"
            minimum = 1 if family == "rule_groups" else 2
            gid = o["_kt"][0]
            count = 0
            for model in models:
                member_sheet = by_model_family.get((model, member_family))
                count += sum(1 for p in prepared if p["action"] == "add"
                             and p["sheet"] == member_sheet and p["_kt"][0] == gid)
            if count < minimum:
                errors.append(f"add {family[:-1]} {gid}: requires at least {minimum} member row(s) in the same batch")

    # display-order collisions
    for o in prepared:
        if o["action"] == "delete":
            continue
        group_col = _DORDER_GROUP_COL.get(o["_family"])
        dorder = o["_coerced_row"].get("display_order")
        if group_col is None or dorder is None:
            continue
        sheet, family = o["sheet"], o["_family"]
        keycols = list(EDITOR_SHEET_META[family]["key"])
        existing = key_indexes[sheet].get(o["_kt"], {})
        group_val = o["_coerced_row"].get(group_col) or str(existing.get(group_col) or "").strip()
        clash = False
        for kt2, row2 in key_indexes[sheet].items():
            if kt2 == o["_kt"] or (sheet, *kt2) in {(s, *k) for (s, k) in []}:
                continue
            if str(row2.get(group_col) or "").strip() == str(group_val) and \
                    str(row2.get("display_order") or "").strip() == str(dorder):
                clash = True
        for p in prepared:
            if p is o or p["sheet"] != sheet or p["action"] == "delete":
                continue
            p_group = p["_coerced_row"].get(group_col)
            if p_group is None:
                p_existing = key_indexes[sheet].get(p["_kt"], {})
                p_group = str(p_existing.get(group_col) or "").strip()
            if str(p_group) == str(group_val) and p["_coerced_row"].get("display_order") == dorder:
                clash = True
        if clash:
            warnings.append({"id": f"dorder:{sheet}:{'+'.join(o['_kt'])}",
                             "message": f"{sheet}: display_order {dorder} duplicates another row in {group_col}={group_val}"})

    # referenced deletes
    for o in prepared:
        if o["action"] != "delete":
            continue
        family, sheet = o["_family"], o["sheet"]
        child_specs = CHILD_REFS_BY_FAMILY.get(family)
        if not child_specs:
            continue
        target_id = o["_kt"][0]
        models = models_by_sheet.get(sheet, set())
        referencing = []
        for child_family, ref_col in child_specs:
            for model in models:
                child_sheet = by_model_family.get((model, child_family))
                if not child_sheet:
                    continue
                child_keycols = list(EDITOR_SHEET_META[child_family]["key"])
                for row in rows_of(extract, child_sheet):
                    if str(row.get(ref_col) or "").strip() != target_id:
                        continue
                    child_kt = tuple(str(row.get(k) or "").strip() for k in child_keycols)
                    child_kid = (child_sheet, tuple(sorted(zip((str(k) for k in child_keycols), child_kt))))
                    if child_kid not in deleted_keys:
                        referencing.append(f"{child_sheet}.{ref_col}")
        if referencing:
            warnings.append({"id": f"refdel:{sheet}:{'+'.join(o['_kt'])}",
                             "message": f"delete {target_id}: still referenced by {sorted(set(referencing))} "
                                        f"(repo convention for rules is normalization_status, not deletion)"})
    return errors, warnings, prepared


def validate_batch(extract, batch):
    errors, warnings, _prepared = _prepare_batch(extract, batch)
    return {"errors": errors, "warnings": warnings}
```

Note the deleted-keys comparison builds the same `_key_id` shape used by `coalesce_ops` — keep them consistent.

- [ ] **Step 3: All tests pass**, commit: `feat: server-side non-breaking batch validation for workbook edits`.

---

### Task 4: Apply pipeline — typed writes, table healing, dry-run, log

**Files:** modify `editor_ops.py`; extend `tests/test_editor_ops_apply.py`.

- [ ] **Step 1: Failing tests:**

```python
from corvette_form_generator.editor_ops import apply_batch  # noqa: E402
from openpyxl import load_workbook  # noqa: E402


class ApplyBatchTest(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.path = Path(self._dir.name) / "fixture.xlsx"
        build_ops_fixture().save(self.path)
        self.log = Path(self._dir.name) / "log.jsonl"

    def tearDown(self):
        self._dir.cleanup()

    def run_batch(self, *items, write=True, confirmed=(), allow_stale=False, mtime=None):
        b = batch(*items, mtime=self.path.stat().st_mtime_ns if mtime is None else mtime)
        return apply_batch(self.path, b, write=write, confirmed_warnings=confirmed,
                           log_path=self.log, run_schema_validation=False, allow_stale=allow_stale)

    def test_add_option_round_trip_and_table_heal(self):
        result = self.run_batch(add_option_composite())
        self.assertTrue(result["ok"], result)
        wb = load_workbook(self.path)
        ws = wb["stingray_options"]
        rows = {ws.cell(row=r, column=1).value: r for r in range(2, ws.max_row + 1)}
        self.assertIn("opt_new_001", rows)
        r = rows["opt_new_001"]
        self.assertIsInstance(ws.cell(row=r, column=3).value, int)   # price typed
        self.assertIsInstance(ws.cell(row=r, column=8).value, bool)  # selectable typed
        self.assertEqual(ws.tables["tbl_fixture_options"].ref, "A1:K5")  # healed 3 -> 5
        self.assertEqual(wb["stingray_ovs"].max_row, 5)  # 2 ovs rows added
        wb.close()
        self.assertTrue(self.log.exists())
        entry = json.loads(self.log.read_text().splitlines()[-1])
        self.assertEqual(entry["opCount"], 3)
        self.assertIn("stingray_options", entry["sheets"])
        backups = Path(self._dir.name) / "backups"
        self.assertTrue(any(backups.iterdir()))

    def test_update_and_delete(self):
        result = self.run_batch(
            op("update", "stingray_options", {"option_id": "opt_thr_001"}, {"price": 777, "description": "x"}),
            op("delete", "stingray_ovs", {"option_id": "opt_one_001", "variant_id": "2lt"}),
        )
        self.assertTrue(result["ok"], result)
        wb = load_workbook(self.path)
        ws = wb["stingray_options"]
        r = next(r for r in range(2, ws.max_row + 1) if ws.cell(row=r, column=1).value == "opt_thr_001")
        self.assertEqual(ws.cell(row=r, column=3).value, 777)
        self.assertEqual(wb["stingray_ovs"].max_row, 2)
        wb.close()

    def test_blanking_a_cell(self):
        result = self.run_batch(op("update", "stingray_options", {"option_id": "opt_thr_001"},
                                   {"option_name": ""}))
        self.assertTrue(result["ok"], result)
        wb = load_workbook(self.path)
        ws = wb["stingray_options"]
        r = next(r for r in range(2, ws.max_row + 1) if ws.cell(row=r, column=1).value == "opt_thr_001")
        self.assertIsNone(ws.cell(row=r, column=4).value)
        wb.close()

    def test_validate_only_makes_no_changes(self):
        before = self.path.stat().st_mtime_ns
        result = self.run_batch(add_option_composite(), write=False)
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "validated")
        self.assertEqual(self.path.stat().st_mtime_ns, before)
        self.assertFalse(self.log.exists())

    def test_warning_requires_confirmation(self):
        item = op("update", "stingray_options", {"option_id": "opt_two_001"}, {"display_order": 10})
        result = self.run_batch(item)
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "needs_confirmation")
        wid = result["warnings"][0]["id"]
        result = self.run_batch(item, confirmed=(wid,))
        self.assertTrue(result["ok"], result)

    def test_invalid_batch_refused(self):
        result = self.run_batch(op("update", "stingray_options", {"option_id": "opt_one_001"},
                                   {"section_id": "sec_nope"}))
        self.assertEqual(result["status"], "invalid")

    def test_lock_and_stale_refusal(self):
        lock = self.path.with_name(f"~${self.path.name}")
        lock.write_text("")
        self.assertEqual(self.run_batch(add_option_composite())["status"], "locked")
        lock.unlink()
        self.assertEqual(self.run_batch(add_option_composite(), mtime=1)["status"], "stale")
        result = self.run_batch(add_option_composite(), mtime=1, allow_stale=True)
        self.assertTrue(result["ok"], result)


REAL_WORKBOOK = ROOT / "stingray_master.xlsx"


@unittest.skipUnless(REAL_WORKBOOK.exists(), "canonical workbook not present")
class RealWorkbookApplyTest(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.path = Path(self._dir.name) / "copy.xlsx"
        import shutil
        shutil.copy2(REAL_WORKBOOK, self.path)
        self.log = Path(self._dir.name) / "log.jsonl"

    def tearDown(self):
        self._dir.cleanup()

    def test_gs_update_heals_stale_table_refs(self):
        wb = load_workbook(self.path)
        self.assertEqual(wb["grandSport_options"].tables["tbl_grandSport_options"].ref, "A1:K267")
        wb.close()
        b = {"version": 1, "workbookMtimeNs": self.path.stat().st_mtime_ns, "items": [
            {"action": "update", "sheet": "grandSport_options", "key": {"option_id": "opt_fey_001"},
             "row": {"detail_raw": "editor apply test"}}]}
        result = apply_batch(self.path, b, write=True, log_path=self.log, source="test")
        self.assertTrue(result["ok"], result)
        self.assertEqual((result["schemaResult"] or {}).get("error_count"), 0)
        wb = load_workbook(self.path)
        self.assertEqual(wb["grandSport_options"].tables["tbl_grandSport_options"].ref, "A1:K274")
        wb.close()

    def test_bad_ref_refused_on_real_workbook(self):
        b = {"version": 1, "workbookMtimeNs": self.path.stat().st_mtime_ns, "items": [
            {"action": "update", "sheet": "stingray_options", "key": {"option_id": "opt_z51_001"},
             "row": {"section_id": "sec_nope"}}]}
        result = apply_batch(self.path, b, write=True, log_path=self.log, source="test")
        self.assertEqual(result["status"], "invalid")
```

- [ ] **Step 2: Verify failure**, then implement in `editor_ops.py`:

```python
GATE_COMMANDS = {
    "stingray": [".venv/bin/python scripts/generate_form.py --model stingray",
                 ".venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx",
                 "node --test tests/stingray-form-regression.test.mjs",
                 "node --test tests/stingray-generator-stability.test.mjs"],
    "grand_sport": [".venv/bin/python scripts/generate_form.py --model grand_sport",
                    ".venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx",
                    "node --test tests/grand-sport-contract-preview.test.mjs",
                    "node --test tests/grand-sport-draft-data.test.mjs",
                    "node --test tests/grand-sport-rule-audit.test.mjs"],
    "z06": [".venv/bin/python scripts/generate_form.py --model z06",
            ".venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx",
            "node --test tests/z06-contract-preview.test.mjs",
            "node --test tests/z06-form-data-draft.test.mjs"],
}


def gate_reminders(models: set[str]) -> list[str]:
    commands: list[str] = []
    for model in sorted(models):
        commands.extend(GATE_COMMANDS.get(model, [
            f".venv/bin/python scripts/generate_form.py --model {model}",
            ".venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx"]))
    seen = set()
    return [c for c in commands if not (c in seen or seen.add(c))]


def apply_ops_to_workbook(wb, prepared_ops, sheet_family) -> set[str]:
    touched: set[str] = set()
    by_sheet: dict[str, list] = {}
    for o in prepared_ops:
        by_sheet.setdefault(o["sheet"], []).append(o)
    for sheet, sheet_ops in by_sheet.items():
        ws = wb[sheet]
        col_of = {str(c.value): i + 1 for i, c in enumerate(ws[1]) if c.value is not None}
        keycols = list(EDITOR_SHEET_META[sheet_family[sheet]]["key"])

        def key_at(r):
            return tuple(str(ws.cell(row=r, column=col_of[k]).value or "").strip() for k in keycols)

        kmap = {key_at(r): r for r in range(2, ws.max_row + 1)}
        for o in (x for x in sheet_ops if x["action"] == "update"):
            r = kmap[o["_kt"]]
            for col, val in o["_coerced_row"].items():
                ws.cell(row=r, column=col_of[col]).value = val
        for r in sorted((kmap[o["_kt"]] for o in sheet_ops if o["action"] == "delete"), reverse=True):
            ws.delete_rows(r)
        for o in (x for x in sheet_ops if x["action"] == "add"):
            values = [None] * max(col_of.values())
            for col, val in o["_coerced_row"].items():
                values[col_of[col] - 1] = val
            ws.append(values)
        touched.add(sheet)
    return touched


def resize_sheet_tables(ws) -> None:
    last = 1
    for r in range(1, ws.max_row + 1):
        if any(c.value is not None for c in ws[r]):
            last = r
    last = max(last, 2)
    for name in list(ws.tables):
        table = ws.tables[name]
        ref = str(table.ref)
        if not ref.startswith("A1:"):
            continue
        end = ref.split(":", 1)[1]
        letters = "".join(ch for ch in end if ch.isalpha())
        table.ref = f"A1:{letters}{last}"


def apply_batch(path, batch, *, write=False, confirmed_warnings=(), source="cli",
                log_path=None, allow_stale=False, run_schema_validation=True) -> dict:
    path = Path(path)
    lock = excel_lock_path(path)
    if lock.exists():
        return {"ok": False, "status": "locked",
                "errors": [f"Excel lock file present: {lock}. Close Excel first."], "warnings": []}
    if not allow_stale and batch.get("workbookMtimeNs") != path.stat().st_mtime_ns:
        return {"ok": False, "status": "stale",
                "errors": ["workbook changed since this batch was prepared; reload and re-verify"],
                "warnings": []}
    extract = extract_workbook(path)
    errors, warnings, prepared = _prepare_batch(extract, batch)
    if errors:
        return {"ok": False, "status": "invalid", "errors": errors, "warnings": warnings}
    if not prepared:
        return {"ok": False, "status": "empty", "errors": ["batch contains no operations"], "warnings": []}
    confirmed = set(confirmed_warnings or ())
    unconfirmed = [w for w in warnings if w["id"] not in confirmed]
    if write and unconfirmed:
        return {"ok": False, "status": "needs_confirmation", "errors": [], "warnings": unconfirmed}

    _registry, sheet_family, models_by_sheet, _bmf = _registry_maps(extract)
    schema_result = None
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir) / path.name
        shutil.copy2(path, tmp)
        wb_tmp = load_workbook(tmp)
        touched = apply_ops_to_workbook(wb_tmp, prepared, sheet_family)
        for name in touched:
            resize_sheet_tables(wb_tmp[name])
        remove_table_sheet_auto_filters(wb_tmp)
        wb_tmp.save(tmp)
        assert_valid_workbook_package(tmp)
        if run_schema_validation:
            issues = validate_workbook_schema(str(tmp), check_live_contract=False)
            schema_result = result_payload(str(tmp), issues)
            if schema_result["error_count"]:
                return {"ok": False, "status": "schema_failed",
                        "errors": [f"dry-run schema validation failed with {schema_result['error_count']} error(s)"],
                        "warnings": warnings, "schemaResult": schema_result}

    models_touched = {m for s in touched for m in models_by_sheet.get(s, set())}
    base = {"opCount": len(prepared), "sheets": sorted(touched), "warnings": warnings,
            "schemaResult": schema_result, "gateReminders": gate_reminders(models_touched)}
    if not write:
        return {"ok": True, "status": "validated", "errors": [], **base}

    wb = load_workbook(path)
    loaded_mtime = path.stat().st_mtime_ns
    touched = apply_ops_to_workbook(wb, prepared, sheet_family)
    for name in touched:
        resize_sheet_tables(wb[name])
    backup_path = save_workbook_safely(wb, path, loaded_mtime_ns=loaded_mtime)
    log_file = Path(log_path) if log_path else DEFAULT_LOG_PATH
    log_file.parent.mkdir(parents=True, exist_ok=True)
    entry = {"ts": datetime.now().isoformat(timespec="seconds"), "source": source,
             "workbook": str(path), "opCount": len(prepared),
             "composites": sorted({o["_composite"] for o in prepared if o.get("_composite")}),
             "sheets": sorted(touched), "backupPath": str(backup_path),
             "schemaErrors": None if schema_result is None else schema_result["error_count"],
             "warningsConfirmed": sorted(confirmed)}
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")
    return {"ok": True, "status": "applied", "errors": [], "applied": len(prepared),
            "backupPath": str(backup_path), "logPath": str(log_file), **base}
```

- [ ] **Step 3: All editor + payload tests pass** (`tests.test_editor_ops_apply`, `tests.test_editor_ops_meta`, `tests.test_editor_server_payload`), commit: `feat: atomic typed apply pipeline with dry-run, table healing, and apply log`.

---

### Task 5: Server POST endpoints

**Files:** modify `scripts/workbook_editor_server.py`; new `tests/test_editor_server_write_api.py`.

- [ ] **Step 1: Failing tests** — temp copy of the real workbook, real HTTP server on an ephemeral port:

```python
#!/usr/bin/env python3
"""Write-API tests for the workbook editor server (Phase 2)."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import workbook_editor_server as srv  # noqa: E402

REAL_WORKBOOK = ROOT / "stingray_master.xlsx"


@unittest.skipUnless(REAL_WORKBOOK.exists(), "canonical workbook not present")
class WriteApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._dir = tempfile.TemporaryDirectory()
        cls.wb_path = Path(cls._dir.name) / "copy.xlsx"
        shutil.copy2(REAL_WORKBOOK, cls.wb_path)
        srv.EditorHandler.cache = srv.WorkbookCache(cls.wb_path)
        srv.EditorHandler.log_path = Path(cls._dir.name) / "log.jsonl"
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), srv.EditorHandler)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls._dir.cleanup()

    def request(self, route, body, origin=None, method="POST"):
        headers = {"Content-Type": "application/json"}
        if origin:
            headers["Origin"] = origin
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{route}",
                                     data=json.dumps(body).encode(), headers=headers, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as err:
            return err.code, json.loads(err.read() or b"{}")

    def mtime(self):
        return self.wb_path.stat().st_mtime_ns

    def update_batch(self, value, mtime=None):
        return {"version": 1, "workbookMtimeNs": self.mtime() if mtime is None else mtime, "items": [
            {"action": "update", "sheet": "stingray_options", "key": {"option_id": "opt_z51_001"},
             "row": {"detail_raw": value}}]}

    def test_cross_origin_post_forbidden(self):
        status, _body = self.request("/api/apply", {"batch": self.update_batch("x")},
                                     origin="http://evil.example")
        self.assertEqual(status, 403)

    def test_stale_batch_409(self):
        status, body = self.request("/api/apply", {"batch": self.update_batch("x", mtime=1)})
        self.assertEqual(status, 409)
        self.assertEqual(body["status"], "stale")

    def test_invalid_batch_422(self):
        bad = {"version": 1, "workbookMtimeNs": self.mtime(), "items": [
            {"action": "update", "sheet": "stingray_options", "key": {"option_id": "opt_z51_001"},
             "row": {"section_id": "sec_nope"}}]}
        status, body = self.request("/api/apply", {"batch": bad})
        self.assertEqual(status, 422)
        self.assertEqual(body["status"], "invalid")

    def test_validate_then_apply_then_visible(self):
        status, body = self.request("/api/validate", {"batch": self.update_batch("write-api test")})
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"], body)
        status, body = self.request("/api/apply", {"batch": self.update_batch("write-api test"),
                                                   "confirmedWarnings": []})
        self.assertEqual(status, 200, body)
        self.assertEqual(body["status"], "applied")
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/api/sheet/stingray_options") as resp:
            rows = json.loads(resp.read())["rows"]
        row = next(r for r in rows if r["option_id"] == "opt_z51_001")
        self.assertEqual(row["detail_raw"], "write-api test")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Verify failure** (501 unsupported method POST), then implement in the server. Add to `EditorHandler`:

```python
    log_path: Path | None = None  # test override; None -> editor_ops default
    MAX_BODY = 10_000_000

    def _allowed_origins(self):
        port = self.server.server_address[1]
        return {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}

    def do_POST(self):  # noqa: N802
        path = urlsplit(self.path).path
        if path not in ("/api/validate", "/api/apply"):
            self._send_json({"error": "not found"}, status=404)
            return
        origin = self.headers.get("Origin")
        if origin and origin not in self._allowed_origins():
            self._send_json({"error": "forbidden origin"}, status=403)
            return
        if "application/json" not in (self.headers.get("Content-Type") or ""):
            self._send_json({"error": "expected application/json"}, status=415)
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if not 0 < length <= self.MAX_BODY:
            self._send_json({"error": "missing or oversized body"}, status=400)
            return
        try:
            body = json.loads(self.rfile.read(length))
        except (ValueError, UnicodeDecodeError):
            self._send_json({"error": "invalid JSON body"}, status=400)
            return
        batch = body.get("batch") or {}
        try:
            if path == "/api/validate":
                result = apply_batch(self.cache.path, batch, write=False, source="server",
                                     log_path=self.log_path)
                self._send_json(result)
            else:
                result = apply_batch(self.cache.path, batch, write=True, source="server",
                                     confirmed_warnings=body.get("confirmedWarnings") or [],
                                     log_path=self.log_path)
                status = 200 if result["ok"] else (409 if result["status"] == "stale" else 422)
                self._send_json(result, status=status)
        except BrokenPipeError:
            pass
        except Exception as exc:
            self._send_json({"error": f"{type(exc).__name__}: {exc}"}, status=500)
```

with `from corvette_form_generator.editor_ops import apply_batch` added to imports.

- [ ] **Step 3: Tests pass** (this suite runs schema validation twice on a real-workbook copy — expect ~10-20s), commit: `feat: workbook write API — validate and apply endpoints with origin guard`.

---

### Task 6: CLI — `scripts/apply_workbook_ops.py`

- [ ] **Step 1: Write it** (thin shell, mirrors `promote_model.py`'s `--write` convention):

```python
#!/usr/bin/env python3
"""Apply a workbook-editor ops batch (ops.json) to stingray_master.xlsx.

Default is validate + dry-run only; nothing is written without --write.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from corvette_form_generator.editor_ops import apply_batch  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ops", help="ops.json exported from the workbook editor")
    parser.add_argument("--workbook", default=str(ROOT / "stingray_master.xlsx"))
    parser.add_argument("--write", action="store_true", help="actually apply (default: validate + dry-run only)")
    parser.add_argument("--confirm-warnings", default="", help="comma-separated warning ids to confirm")
    parser.add_argument("--allow-stale", action="store_true",
                        help="skip the workbook-mtime match check (validation still runs against current state)")
    args = parser.parse_args()

    batch = json.loads(Path(args.ops).read_text(encoding="utf-8"))
    confirmed = [w for w in args.confirm_warnings.split(",") if w]
    result = apply_batch(args.workbook, batch, write=args.write, source="cli",
                         confirmed_warnings=confirmed, allow_stale=args.allow_stale)
    print(json.dumps(result, indent=2, default=str))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Smoke it** against a temp copy: export a tiny ops.json by hand, run default (validated, exit 0), run `--write` (applied), re-run same file (stale, exit 1), re-run with `--allow-stale` (applied). Commit: `feat: apply_workbook_ops CLI for review-then-apply workflow`.

---

### Task 7: UI — structured editing, wizards, Pending Changes

**Files:** rewrite `visualizer/workbook-editor/editor.js`; extend `editor.css`.

Component inventory (full code is authored at execution time as the file itself; the contracts are fixed here):

- `postJson(url, body)` → `{status, data}`.
- Domain helpers: `modelsOfSheet(data, sheet)`, `sheetOfFamily(data, modelKey, family)`, `refOptions(data, sheet, refKind)` → `[{value, label}]` from `referenceDomains` (options labeled `RPO — name`, interiors `id — name`).
- `FieldInput({data, metaEntry, sheetName, col, value, onChange, disabled})` — enum→select (blank option only when domain has `""`), ref→select, bool→select True/False/(blank), int→number input, else text input. **No free text for enum/ref/typed columns.**
- `RowForm({data, sheetName, mode, initial, onQueue, onCancel})` — add: emits full-row add op; edit: emits changed-columns-only update op with `_old` snapshot for the diff display; key columns immutable in edit; key fields required.
- `SheetTable` additions: Add Row (hidden on read-only sheets; on options-family sheets replaced by a hint to use the wizard), per-row Edit/Delete buttons (delete confirms, queues delete op with `_old` row).
- `AddOptionWizard({data, modelKey, onQueue, onClose})` — 3 steps: option fields (option_id prefilled `opt_<rpo>_001` while untouched; display_order prefilled max-in-section + 10 from a fetched copy of the options sheet); **OVS grid, one status select per active variant, all starting blank and required, with a "set all to…" bulk helper**; optional extras (rule-group membership picker, exclusive-group membership picker, minimal rule_mapping row adder with rule_type/target pickers and `normalization_status` defaulted to `active`). Emits one composite.
- `GroupWizard({data, modelKey, kind})` — group fields + member rows (target/option picker, display_order auto-stepped by 10); enforces ≥1 (rule) / ≥2 (exclusive) members in-form; emits one composite.
- `PendingTab({data, queue, removeItem, clearQueue, onApplied})` — items with action badges, key, per-column old→new for updates; composite grouping by label; Validate → renders errors (red) and warnings (amber with confirm checkboxes); Apply → posts confirmed warning ids, on success shows backup path, schema status, `gateReminders`, clears the queue, calls `onApplied`; Export downloads `workbook-ops-<ISO date>.json` with the batch envelope `{version: 1, workbook, workbookMtimeNs, createdAt, items}`.
- `App` — queue state, third tab `Pending Changes (n)`, `onApplied` refetches `/api/workbook` and bumps a `refreshKey` used to remount the browser tab.

- [ ] **Step 1: Write the UI code** per the contracts above.
- [ ] **Step 2: Browser verification on a scratch copy** — `cp stingray_master.xlsx /tmp/editor-scratch.xlsx`, run server with `--workbook /tmp/editor-scratch.xlsx`, then with Playwright: edit a row (typed field), see it in Pending Changes with old→new, Validate (clean), Apply, confirm the table refreshes with the new value and the result panel shows backup + gate reminders; open the Add Option wizard and verify the OVS grid blocks advance until every variant has a status; verify read-only sheets show no edit affordances; zero console errors.
- [ ] **Step 3: Commit**: `feat: guided workbook editing UI — structured forms, wizards, pending-changes apply flow`.

---

### Task 8: Docs + final gates

- [ ] **Step 1:** Update README (`workbook_editor_server.py` bullet: read-only → "review and gated editing") and the AGENTS.md "Workbook Review Tool" section: write path summary, CLI usage, the apply log, and the explicit rule that an editor apply is step 4-5 of the Workbook Update Workflow — regeneration and gates still follow.
- [ ] **Step 2:** Full gates: `unittest discover` (all python suites), `git status stingray_master.xlsx` clean, `validate_workbook_schema.py` green, one node suite as regression. Commit: `docs: document workbook editor write path and CLI`.

## Self-Review Notes

- Spec coverage: §2.1 op/batch/composite ✓ (T2/T3), §2.2 coalescing ✓ (T2), §2.3 coercion ✓ (T2), §2.4 full validation matrix ✓ (T3), §2.5 apply incl. dry-run/table-heal/log ✓ (T4), §2.6 endpoints + hardening ✓ (T5), §2.7 CLI + --allow-stale ✓ (T6), §2.8 UI ✓ (T7), §2.9 honored (validation rejects non-family sheets), domains for pickers ✓ (T1).
- `_key_id` shape is shared by coalesce and the deleted-keys check in T3 — single definition.
- `EditorHandler.log_path` exists so write-API tests don't touch the repo log; CLI/server default to `DEFAULT_LOG_PATH`.
- T7 deviates from the letter of the plan-format rule (component contracts instead of full inline JS): accepted consciously — the executor is the author, executing immediately; the Python core, where correctness lives, is fully specified and test-driven.
