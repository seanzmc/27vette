# Workbook Editor Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Phase 1 of `workbook-editor-integration-spec.md` — a read-only local review tool: a stdlib Python server that derives models/sheets/schemas/reference-domains live from `stingray_master.xlsx`, plus a no-build Preact/htm UI replacing `visualizer/workbook-editor.jsx`.

**Architecture:** `scripts/workbook_editor_server.py` (stdlib `http.server`, localhost-only) extracts the whole workbook into memory per mtime, serves `GET /api/workbook` (registry/metadata) and `GET /api/sheet/<name>` (rows), and serves the static UI from `visualizer/workbook-editor/`. Sheet-meta (key columns, types, enums, refs) lives in `scripts/corvette_form_generator/editor_ops.py` keyed by the `source_role` values of `model_workbook_sources`. The UI is vendored Preact+htm (no npm, no build), two tabs: Form Structure (read-only reference) and Sheet Browser (search, pagination, expandable full-row detail).

**Tech Stack:** Python 3 stdlib + existing openpyxl; vendored `preact@10.27.2` + `htm@3.1.1` ESM modules via import map; hand-written CSS (no Tailwind).

**Verified facts this plan relies on (checked 2026-06-11):**
- `model_workbook_sources` headers: `model_key, source_role, sheet_name, active, notes`; all 11 `source_role` values map 1:1 to the JSX schema families; rows are active for stingray/grand_sport/z06.
- `model_master` headers: `model_key, registry_key, model_label, model_year, dataset_name, export_slug, expected_variant_count, default_model, active, notes`.
- `model_registry_promotion` headers include `promoted_to_runtime, default_model, display_order`.
- `runtime_steps` (`model_key, step_key, step_label, runtime_order, source, active, notes`) has rows for stingray and grand_sport only — **no z06 rows**; UI must render that state.
- `model_variants` active rows exist for all three live models; zr1/zr1x rows inactive.
- Python tests in this repo use `unittest` with `sys.path.insert` of `scripts/` (see `tests/test_model_config_metadata.py`). Run via `.venv/bin/python -m unittest tests.test_editor_server_payload -v`.
- Vendor files download cleanly from unpkg (verified): `preact@10.27.2/dist/preact.module.js` (11.6KB), `preact@10.27.2/hooks/dist/hooks.module.js` (3.8KB), `htm@3.1.1/dist/htm.module.js` (1.2KB).

---

### Task 1: Vendor Preact + htm

**Files:**
- Create: `visualizer/workbook-editor/vendor/preact.module.js`
- Create: `visualizer/workbook-editor/vendor/hooks.module.js`
- Create: `visualizer/workbook-editor/vendor/htm.module.js`

- [ ] **Step 1: Download pinned versions**

```bash
mkdir -p visualizer/workbook-editor/vendor
curl -sL -o visualizer/workbook-editor/vendor/preact.module.js https://unpkg.com/preact@10.27.2/dist/preact.module.js
curl -sL -o visualizer/workbook-editor/vendor/hooks.module.js https://unpkg.com/preact@10.27.2/hooks/dist/hooks.module.js
curl -sL -o visualizer/workbook-editor/vendor/htm.module.js https://unpkg.com/htm@3.1.1/dist/htm.module.js
```

- [ ] **Step 2: Verify sizes and module shape**

Run: `wc -c visualizer/workbook-editor/vendor/*.js && grep -c "export" visualizer/workbook-editor/vendor/preact.module.js`
Expected: ~11581 / ~3753 / ~1207 bytes; export count ≥ 1.

Note: `hooks.module.js` contains `from"preact"` — the import map in Task 6 resolves that bare specifier.

- [ ] **Step 3: Commit**

```bash
git add visualizer/workbook-editor/vendor
git commit -m "chore: vendor preact 10.27.2 and htm 3.1.1 for workbook editor UI"
```

---

### Task 2: `editor_ops.py` — sheet meta registry

**Files:**
- Create: `scripts/corvette_form_generator/editor_ops.py`
- Test: `tests/test_editor_ops_meta.py`

- [ ] **Step 1: Write the failing test**

```python
#!/usr/bin/env python3
"""Tests for the workbook-editor sheet meta registry (Phase 1)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from corvette_form_generator.editor_ops import (  # noqa: E402
    EDITOR_SHEET_META,
    SOURCE_ROLE_FAMILIES,
)


class SourceRoleFamiliesTest(unittest.TestCase):
    def test_every_role_maps_to_a_defined_family(self):
        for role, family in SOURCE_ROLE_FAMILIES.items():
            self.assertIn(family, EDITOR_SHEET_META, f"role {role} -> unknown family {family}")

    def test_known_roles_present(self):
        expected_roles = {
            "source_option_sheet", "status_sheet", "rule_mapping_sheet",
            "rule_groups_sheet", "rule_group_members_sheet",
            "exclusive_groups_sheet", "exclusive_group_members_sheet",
            "price_rules_sheet", "variant_option_overrides_sheet",
            "color_overrides_sheet", "interior_source_sheet",
        }
        self.assertEqual(set(SOURCE_ROLE_FAMILIES), expected_roles)


class EditorSheetMetaTest(unittest.TestCase):
    def test_every_family_declares_key_columns(self):
        for family, meta in EDITOR_SHEET_META.items():
            self.assertTrue(meta["key"], f"family {family} has empty key")
            self.assertIsInstance(meta["key"], tuple)

    def test_options_family_shape(self):
        meta = EDITOR_SHEET_META["options"]
        self.assertEqual(meta["key"], ("option_id",))
        self.assertEqual(meta["types"]["display_order"], "int")
        self.assertEqual(meta["types"]["selectable"], "bool")
        self.assertIn("display_behavior", meta["enums"])
        self.assertEqual(meta["refs"]["section_id"], "sections")

    def test_ovs_family_shape(self):
        meta = EDITOR_SHEET_META["ovs"]
        self.assertEqual(meta["key"], ("option_id", "variant_id"))
        self.assertEqual(
            tuple(meta["enums"]["status"]), ("standard", "available", "unavailable")
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_editor_ops_meta -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'corvette_form_generator.editor_ops'`

- [ ] **Step 3: Write the implementation**

`scripts/corvette_form_generator/editor_ops.py`:

```python
#!/usr/bin/env python3
"""Workbook-editor sheet metadata (Phase 1).

The workbook owns its data; this module owns only what the workbook cannot
express about itself: which columns form each sheet family's primary key,
intended cell types, enum domains, and which columns reference other
workbook entities. Keyed by the schema *family* names that
``model_workbook_sources.source_role`` values map onto.

Phase 2 adds op schema, coalescing, typed apply, and non-breaking
validation here (see workbook-editor-integration-spec.md §4.4).
"""

from __future__ import annotations

# model_workbook_sources.source_role -> schema family
SOURCE_ROLE_FAMILIES: dict[str, str] = {
    "source_option_sheet": "options",
    "status_sheet": "ovs",
    "rule_mapping_sheet": "rule_mapping",
    "rule_groups_sheet": "rule_groups",
    "rule_group_members_sheet": "rule_group_members",
    "exclusive_groups_sheet": "exclusive_groups",
    "exclusive_group_members_sheet": "exclusive_members",
    "price_rules_sheet": "price_rules",
    "variant_option_overrides_sheet": "variant_overrides",
    "color_overrides_sheet": "color_overrides",
    "interior_source_sheet": "interiors",
}

# Per-family editing metadata. Columns absent from types/enums/refs are
# free text. Headers always come from the sheet itself, never from here.
EDITOR_SHEET_META: dict[str, dict] = {
    "options": {
        "key": ("option_id",),
        "types": {
            "price": "int",
            "display_order": "int",
            "selectable": "bool",
            "active": "bool",
        },
        "enums": {
            "display_behavior": (
                "", "default_selected", "hidden", "display_only", "auto_only",
            ),
        },
        "refs": {"section_id": "sections"},
    },
    "ovs": {
        "key": ("option_id", "variant_id"),
        "types": {},
        "enums": {"status": ("standard", "available", "unavailable")},
        "refs": {"option_id": "options", "variant_id": "variants"},
    },
    "rule_mapping": {
        "key": ("rule_id",),
        "types": {},
        "enums": {
            "rule_type": ("includes", "excludes", "requires"),
            "body_style_scope": ("", "coupe", "convertible"),
            "runtime_action": ("", "replace"),
            "normalization_status": ("active", "omitted", "replaced", "preserved"),
        },
        "refs": {
            "source_id": "options",
            "target_id": "options",
            "source_section": "sections",
            "target_section": "sections",
        },
    },
    "rule_groups": {
        "key": ("group_id",),
        "types": {"active": "bool"},
        "enums": {"group_type": ("requires_any", "excludes_any")},
        "refs": {"source_id": "options"},
    },
    "rule_group_members": {
        "key": ("group_id", "target_id"),
        "types": {"display_order": "int", "active": "bool"},
        "enums": {},
        "refs": {"group_id": "rule_groups", "target_id": "options"},
    },
    "exclusive_groups": {
        "key": ("group_id",),
        "types": {"active": "bool"},
        "enums": {
            "selection_mode": (
                "single_within_group", "required_single_within_group",
            ),
        },
        "refs": {},
    },
    "exclusive_members": {
        "key": ("group_id", "option_id"),
        "types": {"display_order": "int", "active": "bool"},
        "enums": {},
        "refs": {"group_id": "exclusive_groups", "option_id": "options"},
    },
    "price_rules": {
        "key": ("price_rule_id",),
        "types": {"price_value": "int"},
        "enums": {"price_rule_type": ("override",)},
        "refs": {
            "condition_option_id": "options",
            "target_option_id": "options",
        },
    },
    "variant_overrides": {
        "key": ("option_id", "variant_id"),
        "types": {"active": "bool"},
        "enums": {
            "selectable": ("", "True", "False"),
            "display_behavior": ("", "default_selected", "display_only", "hidden"),
        },
        "refs": {
            "option_id": "options",
            "variant_id": "variants",
            "section_id": "sections",
        },
    },
    "color_overrides": {
        "key": ("interior_id", "option_id"),
        "types": {},
        "enums": {"rule_type": ("requires",)},
        "refs": {"interior_id": "interiors", "option_id": "options"},
    },
    "interiors": {
        "key": ("interior_id",),
        "types": {
            "Price": "int",
            "active_for_stingray": "bool",
            "requires_r6x": "bool",
        },
        "enums": {},
        "refs": {"section_id": "sections", "included_option_id": "options"},
    },
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m unittest tests.test_editor_ops_meta -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/corvette_form_generator/editor_ops.py tests/test_editor_ops_meta.py
git commit -m "feat: add workbook-editor sheet meta registry (Phase 1)"
```

---

### Task 3: Server payload derivation (TDD against a synthetic workbook)

**Files:**
- Create: `scripts/workbook_editor_server.py` (derivation functions only; HTTP wiring is Task 5)
- Test: `tests/test_editor_server_payload.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_editor_server_payload.py`:

```python
#!/usr/bin/env python3
"""Tests for the workbook-editor server payload derivation (Phase 1)."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from workbook_editor_server import (  # noqa: E402
    build_payload,
    extract_workbook,
    sheet_payload,
)

REAL_WORKBOOK = ROOT / "stingray_master.xlsx"


def append_sheet(wb: Workbook, name: str, headers: list[str], rows: list[dict]) -> None:
    ws = wb.create_sheet(name)
    ws.append(headers)
    for row in rows:
        ws.append([row.get(h) for h in headers])


def build_fixture_workbook() -> Workbook:
    wb = Workbook()
    del wb[wb.sheetnames[0]]
    append_sheet(
        wb, "model_master",
        ["model_key", "registry_key", "model_label", "model_year", "default_model", "active"],
        [
            {"model_key": "stingray", "registry_key": "stingray", "model_label": "Stingray",
             "model_year": "2027", "default_model": True, "active": True},
            {"model_key": "z06", "registry_key": "z06", "model_label": "Z06",
             "model_year": "2027", "default_model": False, "active": True},
            {"model_key": "zr1", "registry_key": "zr1", "model_label": "ZR1",
             "model_year": "2027", "default_model": False, "active": False},
        ],
    )
    append_sheet(
        wb, "model_registry_promotion",
        ["model_key", "promoted_to_runtime", "default_model", "display_order", "active"],
        [
            {"model_key": "stingray", "promoted_to_runtime": True, "default_model": True,
             "display_order": 1, "active": True},
            {"model_key": "z06", "promoted_to_runtime": True, "default_model": False,
             "display_order": 3, "active": True},
        ],
    )
    append_sheet(
        wb, "model_workbook_sources",
        ["model_key", "source_role", "sheet_name", "active", "notes"],
        [
            {"model_key": "stingray", "source_role": "source_option_sheet",
             "sheet_name": "stingray_options", "active": True},
            {"model_key": "stingray", "source_role": "status_sheet",
             "sheet_name": "stingray_ovs", "active": True},
            {"model_key": "z06", "source_role": "source_option_sheet",
             "sheet_name": "z06_options", "active": True},
            {"model_key": "zr1", "source_role": "source_option_sheet",
             "sheet_name": "zr1_options", "active": False},
            {"model_key": "stingray", "source_role": "mystery_role",
             "sheet_name": "stingray_options", "active": True},
        ],
    )
    append_sheet(
        wb, "runtime_steps",
        ["model_key", "step_key", "step_label", "runtime_order", "active"],
        [
            {"model_key": "stingray", "step_key": "paint", "step_label": "Exterior Paint",
             "runtime_order": 3, "active": True},
            {"model_key": "stingray", "step_key": "body_style", "step_label": "Body Style",
             "runtime_order": 1, "active": True},
            {"model_key": "stingray", "step_key": "old_step", "step_label": "Old",
             "runtime_order": 99, "active": False},
        ],
    )
    append_sheet(
        wb, "context_section_master",
        ["model_key", "context_type", "section_id", "section_name", "step_key", "active"],
        [
            {"model_key": "stingray", "context_type": "body_style",
             "section_id": "sec_context_body_style", "section_name": "Body Style",
             "step_key": "body_style", "active": True},
        ],
    )
    append_sheet(
        wb, "section_master",
        ["section_id", "section_name", "selection_mode", "is_required", "display_order",
         "standard_behavior", "step_key"],
        [
            {"section_id": "sec_pain_001", "section_name": "Paint",
             "selection_mode": "single", "is_required": True, "display_order": 10,
             "step_key": "paint"},
            {"section_id": "sec_whee_002", "section_name": "Wheels",
             "selection_mode": "single", "is_required": False, "display_order": 20,
             "step_key": "wheels"},
        ],
    )
    append_sheet(
        wb, "section_presentation",
        ["model_key", "section_id", "display_label", "step_key", "section_display_order", "active"],
        [
            {"model_key": "stingray", "section_id": "sec_pain_001",
             "display_label": "Exterior Paint", "step_key": "paint",
             "section_display_order": 10, "active": True},
        ],
    )
    append_sheet(
        wb, "variant_master",
        ["variant_id", "display_name", "active"],
        [
            {"variant_id": "1lt_c07", "display_name": "1LT Coupe", "active": True},
            {"variant_id": "2lt_c07", "display_name": "2LT Coupe", "active": True},
        ],
    )
    append_sheet(
        wb, "model_variants",
        ["model_key", "variant_id", "display_order", "active"],
        [
            {"model_key": "stingray", "variant_id": "1lt_c07", "display_order": 1, "active": True},
            {"model_key": "stingray", "variant_id": "2lt_c07", "display_order": 2, "active": True},
            {"model_key": "zr1", "variant_id": "zr1_c07", "display_order": 1, "active": False},
        ],
    )
    append_sheet(
        wb, "stingray_options",
        ["option_id", "rpo", "price", "option_name", "section_id", "selectable",
         "display_order", "active", "display_behavior"],
        [
            {"option_id": "opt_z51_001", "rpo": "Z51", "price": 5395,
             "option_name": "Z51 Performance Package", "section_id": "sec_pain_001",
             "selectable": True, "display_order": 30, "active": True},
            {"option_id": "opt_gkz_001", "rpo": "GKZ", "price": 0,
             "option_name": "Torch Red", "section_id": "sec_pain_001",
             "selectable": True, "display_order": 10, "active": True},
        ],
    )
    append_sheet(
        wb, "stingray_ovs",
        ["option_id", "variant_id", "status"],
        [{"option_id": "opt_z51_001", "variant_id": "1lt_c07", "status": "available"}],
    )
    append_sheet(
        wb, "z06_options",
        ["option_id", "rpo", "price", "option_name", "section_id"],
        [{"option_id": "opt_z07_001", "rpo": "Z07", "price": 9500,
          "option_name": "Z07 Performance Package", "section_id": "sec_pain_001"}],
    )
    append_sheet(
        wb, "form_steps",
        ["step_key", "label"],
        [{"step_key": "paint", "label": "Paint"}],
    )
    return wb


class PayloadTestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        wb = build_fixture_workbook()
        cls._tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        wb.save(cls._tmp.name)
        cls.extract = extract_workbook(Path(cls._tmp.name))
        cls.payload = build_payload(cls.extract)

    @classmethod
    def tearDownClass(cls):
        Path(cls._tmp.name).unlink(missing_ok=True)


class ModelsTest(PayloadTestBase):
    def test_models_sorted_by_promotion_display_order(self):
        keys = [m["key"] for m in self.payload["models"]]
        self.assertEqual(keys, ["stingray", "z06", "zr1"])

    def test_model_flags(self):
        by_key = {m["key"]: m for m in self.payload["models"]}
        self.assertTrue(by_key["stingray"]["defaultModel"])
        self.assertTrue(by_key["stingray"]["promoted"])
        self.assertTrue(by_key["z06"]["promoted"])
        self.assertFalse(by_key["zr1"]["promoted"])
        self.assertFalse(by_key["zr1"]["active"])


class ModelSheetsTest(PayloadTestBase):
    def test_active_rows_with_known_roles_only(self):
        sheets = self.payload["modelSheets"]
        stingray = {e["sheet"]: e for e in sheets["stingray"]}
        self.assertEqual(set(stingray), {"stingray_options", "stingray_ovs"})
        self.assertEqual(stingray["stingray_options"]["family"], "options")
        self.assertNotIn("zr1", sheets)


class SheetClassificationTest(PayloadTestBase):
    def test_generated_and_unregistered_sheets_read_only(self):
        by_name = {s["name"]: s for s in self.payload["sheets"]}
        self.assertTrue(by_name["form_steps"]["readOnly"])
        self.assertIsNone(by_name["form_steps"]["family"])
        self.assertTrue(by_name["section_master"]["readOnly"])

    def test_registered_source_sheet_carries_meta(self):
        by_name = {s["name"]: s for s in self.payload["sheets"]}
        entry = by_name["stingray_options"]
        self.assertFalse(entry["readOnly"])
        self.assertEqual(entry["family"], "options")
        self.assertEqual(entry["keyCols"], ["option_id"])
        self.assertEqual(entry["types"]["display_order"], "int")
        self.assertIn("display_behavior", entry["enums"])
        self.assertEqual(entry["rowCount"], 2)


class StepsAndSectionsTest(PayloadTestBase):
    def test_steps_active_only(self):
        steps = [s for s in self.payload["steps"] if s["modelKey"] == "stingray"]
        self.assertEqual([s["stepKey"] for s in steps], ["body_style", "paint"])

    def test_section_surfaces_present(self):
        self.assertEqual(len(self.payload["sections"]), 2)
        self.assertEqual(len(self.payload["sectionPresentation"]), 1)
        self.assertEqual(len(self.payload["contextSections"]), 1)


class ReferenceDomainsTest(PayloadTestBase):
    def test_sections_domain(self):
        domain = self.payload["referenceDomains"]["sections"]
        self.assertIn({"id": "sec_pain_001", "name": "Paint"}, domain)

    def test_variants_by_model_excludes_inactive(self):
        variants = self.payload["referenceDomains"]["variantsByModel"]
        self.assertEqual([v["id"] for v in variants["stingray"]], ["1lt_c07", "2lt_c07"])
        self.assertNotIn("zr1", variants)

    def test_options_by_model(self):
        options = self.payload["referenceDomains"]["optionsByModel"]
        self.assertEqual(len(options["stingray"]), 2)
        self.assertEqual(options["z06"][0]["rpo"], "Z07")


class SheetPayloadTest(PayloadTestBase):
    def test_rows_preserve_json_types(self):
        payload = sheet_payload(self.extract, "stingray_options")
        row = payload["rows"][0]
        self.assertEqual(row["price"], 5395)
        self.assertIs(row["selectable"], True)

    def test_unknown_sheet_returns_none(self):
        self.assertIsNone(sheet_payload(self.extract, "nope"))


@unittest.skipUnless(REAL_WORKBOOK.exists(), "canonical workbook not present")
class RealWorkbookIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.extract = extract_workbook(REAL_WORKBOOK)
        cls.payload = build_payload(cls.extract)

    def test_live_models_promoted(self):
        by_key = {m["key"]: m for m in self.payload["models"]}
        for key in ("stingray", "grand_sport", "z06"):
            self.assertTrue(by_key[key]["promoted"], key)
        self.assertTrue(by_key["stingray"]["defaultModel"])

    def test_model_sheet_registries(self):
        sheets = self.payload["modelSheets"]
        z06_names = {e["sheet"] for e in sheets["z06"]}
        self.assertIn("z06_options", z06_names)
        self.assertIn("LZ_Interiors", z06_names)

    def test_large_sheet_served(self):
        payload = sheet_payload(self.extract, "stingray_ovs")
        self.assertGreater(len(payload["rows"]), 1000)

    def test_form_sheets_read_only(self):
        for entry in self.payload["sheets"]:
            if entry["name"].startswith("form_"):
                self.assertTrue(entry["readOnly"], entry["name"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m unittest tests.test_editor_server_payload -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'workbook_editor_server'`

- [ ] **Step 3: Write the derivation implementation**

`scripts/workbook_editor_server.py` (HTTP wiring added in Task 5; this task ends the file after `sheet_payload`):

```python
#!/usr/bin/env python3
"""Read-only local server for reviewing stingray_master.xlsx (Phase 1).

Derives models, per-model sheet registries, schemas, and reference domains
live from the workbook — nothing is hardcoded that a workbook sheet owns.
See workbook-editor-integration-spec.md. Phase 1 has no write surface.
"""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from openpyxl import load_workbook  # noqa: E402

from corvette_form_generator.editor_ops import (  # noqa: E402
    EDITOR_SHEET_META,
    SOURCE_ROLE_FAMILIES,
)
from corvette_form_generator.workbook import workbook_truthy  # noqa: E402

UI_DIR = ROOT / "visualizer" / "workbook-editor"
DEFAULT_WORKBOOK = ROOT / "stingray_master.xlsx"


def jsonable(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def extract_workbook(path: Path) -> dict:
    """Load the whole workbook into plain dicts and close the file."""
    path = Path(path)
    mtime_ns = path.stat().st_mtime_ns
    wb = load_workbook(path, read_only=True, data_only=True)
    sheets: dict[str, dict] = {}
    for ws in wb.worksheets:
        rows_iter = ws.iter_rows(values_only=True)
        header_row = next(rows_iter, None) or ()
        cols = [(i, str(v)) for i, v in enumerate(header_row) if v is not None]
        rows = []
        for raw in rows_iter:
            row = {
                name: jsonable(raw[i]) if i < len(raw) else None
                for i, name in cols
            }
            if all(v in (None, "") for v in row.values()):
                continue
            rows.append(row)
        sheets[ws.title] = {"headers": [name for _, name in cols], "rows": rows}
    wb.close()
    return {"path": str(path), "mtime_ns": mtime_ns, "sheets": sheets}


def _rows_of(extract: dict, name: str) -> list[dict]:
    sheet = extract["sheets"].get(name)
    return sheet["rows"] if sheet else []


def _models(extract: dict) -> list[dict]:
    promotion = {
        row.get("model_key"): row
        for row in _rows_of(extract, "model_registry_promotion")
    }
    models = []
    for row in _rows_of(extract, "model_master"):
        key = row.get("model_key")
        if not key:
            continue
        promo = promotion.get(key, {})
        models.append({
            "key": key,
            "registryKey": row.get("registry_key"),
            "label": row.get("model_label"),
            "year": row.get("model_year"),
            "active": workbook_truthy(row.get("active")),
            "defaultModel": workbook_truthy(row.get("default_model")),
            "promoted": workbook_truthy(promo.get("promoted_to_runtime")),
            "displayOrder": promo.get("display_order"),
        })
    models.sort(key=lambda m: (m["displayOrder"] is None, m["displayOrder"] or 0, m["key"]))
    return models


def _model_sheets(extract: dict) -> tuple[dict, dict]:
    """Per-model sheet registry plus a sheet-name -> family reverse map."""
    registry: dict[str, list[dict]] = {}
    sheet_family: dict[str, str] = {}
    for row in _rows_of(extract, "model_workbook_sources"):
        if not workbook_truthy(row.get("active")):
            continue
        family = SOURCE_ROLE_FAMILIES.get(row.get("source_role"))
        sheet_name = row.get("sheet_name")
        model_key = row.get("model_key")
        if not (family and sheet_name and model_key):
            continue
        registry.setdefault(model_key, []).append({
            "sheet": sheet_name,
            "role": row.get("source_role"),
            "family": family,
        })
        sheet_family.setdefault(sheet_name, family)
    return registry, sheet_family


def _sheet_list(extract: dict, sheet_family: dict) -> list[dict]:
    entries = []
    for name, data in extract["sheets"].items():
        family = sheet_family.get(name)
        entry = {
            "name": name,
            "headers": data["headers"],
            "rowCount": len(data["rows"]),
            "family": family,
            "readOnly": family is None or name.startswith("form_"),
        }
        meta = EDITOR_SHEET_META.get(family) if family else None
        if meta:
            entry["keyCols"] = list(meta["key"])
            entry["types"] = dict(meta.get("types", {}))
            entry["enums"] = {k: list(v) for k, v in meta.get("enums", {}).items()}
            entry["refs"] = dict(meta.get("refs", {}))
        entries.append(entry)
    return entries


def build_payload(extract: dict) -> dict:
    models = _models(extract)
    model_sheets, sheet_family = _model_sheets(extract)

    steps = sorted(
        (
            {
                "modelKey": row.get("model_key"),
                "stepKey": row.get("step_key"),
                "label": row.get("step_label"),
                "order": row.get("runtime_order"),
            }
            for row in _rows_of(extract, "runtime_steps")
            if workbook_truthy(row.get("active"))
        ),
        key=lambda s: (s["modelKey"] or "", s["order"] or 0),
    )
    context_sections = [
        {
            "modelKey": row.get("model_key"),
            "sectionId": row.get("section_id"),
            "name": row.get("section_name"),
            "stepKey": row.get("step_key"),
        }
        for row in _rows_of(extract, "context_section_master")
        if workbook_truthy(row.get("active"))
    ]
    sections = [
        {
            "sectionId": row.get("section_id"),
            "name": row.get("section_name"),
            "selectionMode": row.get("selection_mode"),
            "isRequired": workbook_truthy(row.get("is_required")),
            "displayOrder": row.get("display_order"),
            "standardBehavior": row.get("standard_behavior"),
            "stepKey": row.get("step_key"),
        }
        for row in _rows_of(extract, "section_master")
        if row.get("section_id")
    ]
    presentation = [
        {
            "modelKey": row.get("model_key"),
            "sectionId": row.get("section_id"),
            "label": row.get("display_label"),
            "stepKey": row.get("step_key"),
            "order": row.get("section_display_order"),
        }
        for row in _rows_of(extract, "section_presentation")
        if workbook_truthy(row.get("active"))
    ]

    variant_names = {
        row.get("variant_id"): row.get("display_name")
        for row in _rows_of(extract, "variant_master")
    }
    variants_by_model: dict[str, list[dict]] = {}
    for row in sorted(
        _rows_of(extract, "model_variants"),
        key=lambda r: (r.get("model_key") or "", r.get("display_order") or 0),
    ):
        if not workbook_truthy(row.get("active")):
            continue
        variant_id = row.get("variant_id")
        variants_by_model.setdefault(row.get("model_key"), []).append(
            {"id": variant_id, "name": variant_names.get(variant_id)}
        )

    options_by_model: dict[str, list[dict]] = {}
    for model_key, entries in model_sheets.items():
        option_sheet = next(
            (e["sheet"] for e in entries if e["family"] == "options"), None
        )
        if not option_sheet:
            continue
        options_by_model[model_key] = [
            {"id": row.get("option_id"), "rpo": row.get("rpo"), "name": row.get("option_name")}
            for row in _rows_of(extract, option_sheet)
            if row.get("option_id")
        ]

    step_keys = sorted(
        {s["stepKey"] for s in steps if s["stepKey"]}
        | {s["stepKey"] for s in sections if s["stepKey"]}
    )

    return {
        "workbook": {
            "path": extract["path"],
            "mtimeNs": extract["mtime_ns"],
            "sheetCount": len(extract["sheets"]),
        },
        "models": models,
        "modelSheets": model_sheets,
        "steps": steps,
        "contextSections": context_sections,
        "sections": sections,
        "sectionPresentation": presentation,
        "sheets": _sheet_list(extract, sheet_family),
        "referenceDomains": {
            "sections": [
                {"id": s["sectionId"], "name": s["name"]} for s in sections
            ],
            "variantsByModel": variants_by_model,
            "optionsByModel": options_by_model,
            "stepKeys": step_keys,
        },
    }


def sheet_payload(extract: dict, name: str) -> dict | None:
    data = extract["sheets"].get(name)
    if data is None:
        return None
    return {"name": name, "headers": data["headers"], "rows": data["rows"]}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m unittest tests.test_editor_server_payload -v`
Expected: PASS (synthetic tests + 4 real-workbook integration tests)

- [ ] **Step 5: Run existing python tests to confirm no regression**

Run: `.venv/bin/python -m unittest tests.test_model_config_metadata tests.test_registry_promotion_metadata tests.test_schema_validation_metadata -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add scripts/workbook_editor_server.py tests/test_editor_server_payload.py
git commit -m "feat: derive workbook-editor payload live from workbook metadata"
```

---

### Task 4: (merged into Task 3 — `sheet_payload` is covered there; no separate task)

---

### Task 5: HTTP server wiring + static file serving

**Files:**
- Modify: `scripts/workbook_editor_server.py` (append below `sheet_payload`)

- [ ] **Step 1: Append HTTP wiring**

```python
import argparse  # noqa: E402
import json  # noqa: E402
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer  # noqa: E402
from urllib.parse import unquote, urlsplit  # noqa: E402

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json",
    ".svg": "image/svg+xml",
}


class WorkbookCache:
    """Re-extract the workbook only when its mtime changes."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._extract: dict | None = None

    def extract(self) -> dict:
        mtime_ns = self.path.stat().st_mtime_ns
        if self._extract is None or self._extract["mtime_ns"] != mtime_ns:
            self._extract = extract_workbook(self.path)
        return self._extract


class EditorHandler(BaseHTTPRequestHandler):
    cache: WorkbookCache  # assigned in main()

    def do_GET(self):  # noqa: N802 (stdlib API name)
        path = urlsplit(self.path).path
        try:
            if path == "/api/workbook":
                self._send_json(build_payload(self.cache.extract()))
            elif path.startswith("/api/sheet/"):
                name = unquote(path[len("/api/sheet/"):])
                payload = sheet_payload(self.cache.extract(), name)
                if payload is None:
                    self._send_json({"error": f"unknown sheet: {name}"}, status=404)
                else:
                    self._send_json(payload)
            else:
                self._serve_static(path)
        except BrokenPipeError:
            pass
        except Exception as exc:  # surface server faults to the UI
            self._send_json({"error": f"{type(exc).__name__}: {exc}"}, status=500)

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_static(self, path: str) -> None:
        rel = "index.html" if path in ("", "/") else path.lstrip("/")
        target = (UI_DIR / rel).resolve()
        if not str(target).startswith(str(UI_DIR.resolve())) or not target.is_file():
            self.send_error(404)
            return
        body = target.read_bytes()
        self.send_response(200)
        self.send_header(
            "Content-Type", CONTENT_TYPES.get(target.suffix, "application/octet-stream")
        )
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):  # quiet by default; it's a local dev tool
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only workbook review server (Phase 1).")
    parser.add_argument("--port", type=int, default=8027)
    parser.add_argument("--workbook", default=str(DEFAULT_WORKBOOK))
    args = parser.parse_args()
    EditorHandler.cache = WorkbookCache(Path(args.workbook))
    server = ThreadingHTTPServer(("127.0.0.1", args.port), EditorHandler)
    print(f"Workbook editor (read-only) at http://127.0.0.1:{args.port}/")
    print(f"Workbook: {args.workbook}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify endpoints with curl**

```bash
.venv/bin/python scripts/workbook_editor_server.py --port 8027 &
sleep 4
curl -s http://127.0.0.1:8027/api/workbook | .venv/bin/python -c "import json,sys; d=json.load(sys.stdin); print(len(d['models']), d['workbook']['sheetCount'])"
curl -s http://127.0.0.1:8027/api/sheet/stingray_options | .venv/bin/python -c "import json,sys; d=json.load(sys.stdin); print(len(d['rows']))"
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8027/api/sheet/nope
curl -s -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:8027/../README.md"
kill %1
```

Expected: `5 81` (models include zr1/zr1x scaffolds), `270` (stingray_options rows), `404`, `404`.

- [ ] **Step 3: Re-run payload tests (import side effects)**

Run: `.venv/bin/python -m unittest tests.test_editor_server_payload -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add scripts/workbook_editor_server.py
git commit -m "feat: serve workbook payload and static UI over localhost HTTP"
```

---

### Task 6: UI — `index.html` + `editor.css`

**Files:**
- Create: `visualizer/workbook-editor/index.html`
- Create: `visualizer/workbook-editor/editor.css`

- [ ] **Step 1: Write index.html**

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Corvette Workbook — Review</title>
<link rel="stylesheet" href="editor.css">
<script type="importmap">
{
  "imports": {
    "preact": "./vendor/preact.module.js",
    "preact/hooks": "./vendor/hooks.module.js",
    "htm": "./vendor/htm.module.js"
  }
}
</script>
</head>
<body>
<div id="app"></div>
<script type="module" src="editor.js"></script>
</body>
</html>
```

- [ ] **Step 2: Write editor.css** (dark slate theme matching the original component)

```css
:root {
  --bg: #020617;
  --panel: #0f172a;
  --panel-2: #1e293b;
  --border: #1e293b;
  --border-2: #334155;
  --text: #f1f5f9;
  --dim: #64748b;
  --muted: #94a3b8;
  --amber: #f59e0b;
  --amber-dark: #78350f;
  --sky: #0284c7;
  --sky-text: #7dd3fc;
  --emerald: #059669;
  --emerald-bg: #022c22;
  --emerald-border: #047857;
  --rose: #fb7185;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font: 14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
code, .mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }

header.app {
  display: flex; align-items: center; justify-content: space-between;
  flex-wrap: wrap; gap: 12px;
  padding: 14px 24px;
  background: var(--panel);
  border-bottom: 1px solid var(--border);
}
header.app h1 { font-size: 17px; margin: 0; }
header.app .sub { font-size: 12px; color: var(--dim); }
nav.tabs { display: flex; gap: 4px; background: var(--panel-2); border-radius: 10px; padding: 4px; }
nav.tabs button {
  border: 0; background: transparent; color: var(--muted);
  padding: 8px 14px; border-radius: 7px; font-size: 13px; font-weight: 600; cursor: pointer;
}
nav.tabs button.on { background: var(--amber); color: #0f172a; }
nav.tabs button:not(.on):hover { background: #33415588; }

main { max-width: 1180px; margin: 0 auto; padding: 24px; }
h2.sec {
  font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em;
  color: var(--amber); margin: 0 0 12px;
}
section { margin-bottom: 28px; }

.cards { display: grid; gap: 12px; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); }
.card {
  border: 1px solid var(--border-2); border-radius: 12px; padding: 14px;
  background: var(--panel); opacity: 0.75;
}
.card.active { border-color: var(--emerald-border); background: var(--emerald-bg); opacity: 1; }
.card .name { font-weight: 700; display: flex; justify-content: space-between; }
.card .ord { color: var(--dim); font-size: 12px; }
.badges { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px; }
.badge { font-size: 11px; padding: 2px 8px; border-radius: 999px; background: var(--panel-2); color: var(--muted); }
.badge.green { background: #065f46; color: #a7f3d0; }
.badge.blue { background: #0c4a6e; color: var(--sky-text); }
.badge.amber { background: var(--amber-dark); color: #fcd34d; }

.steps { border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }
.step {
  display: flex; gap: 12px; align-items: flex-start; padding: 10px 16px; flex-wrap: wrap;
}
.step:nth-child(odd) { background: var(--panel); }
.step .num {
  width: 30px; height: 30px; flex: none; border-radius: 999px;
  background: var(--panel-2); color: var(--amber);
  display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 13px;
}
.step .label { font-weight: 600; }
.step .key { font-size: 11px; color: var(--dim); }
.step .secs { margin-left: auto; display: flex; flex-wrap: wrap; gap: 4px; max-width: 540px; justify-content: flex-end; }
.chip { font-size: 11px; padding: 2px 8px; border-radius: 5px; background: var(--panel-2); color: var(--muted); }
.chip.shared { opacity: 0.55; }
.note { color: var(--dim); font-style: italic; font-size: 13px; }

.pills { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; align-items: center; }
.pill {
  border: 1px solid var(--border-2); background: var(--panel); color: var(--text);
  border-radius: 9px; padding: 7px 12px; font-size: 13px; font-weight: 600; cursor: pointer;
}
.pill.scaffold { color: var(--dim); }
.pill.on { background: var(--amber); border-color: var(--amber); color: #0f172a; }
.pill.sheet { border-radius: 999px; padding: 4px 11px; font-size: 12px; font-weight: 500; }
.pill.sheet.on { background: var(--sky); border-color: var(--sky); color: #fff; }
select.other {
  background: var(--panel); color: var(--muted); border: 1px solid var(--border-2);
  border-radius: 999px; padding: 4px 8px; font-size: 12px;
}

.panel { border: 1px solid var(--border); border-radius: 12px; background: var(--panel); }
.panel .bar {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  padding: 10px 16px; border-bottom: 1px solid var(--border);
}
.panel .bar .title { font-weight: 700; }
.panel .bar .meta { font-size: 11px; color: var(--dim); }
.panel .bar input[type="search"] {
  margin-left: auto; background: var(--panel-2); border: 1px solid var(--border-2);
  color: var(--text); border-radius: 8px; padding: 6px 10px; font-size: 13px; min-width: 220px;
}
.tablewrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th {
  text-align: left; font-size: 11px; text-transform: uppercase; color: var(--muted);
  padding: 8px 12px; border-bottom: 1px solid var(--border); white-space: nowrap;
}
td {
  padding: 7px 12px; border-bottom: 1px solid var(--border);
  max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  color: #cbd5e1;
}
tr.row { cursor: pointer; }
tr.row:hover { background: var(--panel-2); }
tr.detail td { white-space: normal; background: #0b1222; }
.detail dl { display: grid; grid-template-columns: max-content 1fr; gap: 4px 16px; margin: 6px 0; }
.detail dt { color: var(--dim); font-size: 12px; }
.detail dd { margin: 0; font-size: 13px; word-break: break-word; }
.dim { color: #475569; }
.pager { display: flex; align-items: center; gap: 10px; padding: 10px 16px; font-size: 12px; color: var(--muted); }
.pager button {
  background: var(--panel-2); border: 1px solid var(--border-2); color: var(--text);
  border-radius: 7px; padding: 4px 10px; cursor: pointer;
}
.pager button:disabled { opacity: 0.4; cursor: default; }
.error { color: var(--rose); padding: 18px; }
.loading { color: var(--dim); padding: 18px; font-style: italic; }
```

- [ ] **Step 3: Commit**

```bash
git add visualizer/workbook-editor/index.html visualizer/workbook-editor/editor.css
git commit -m "feat: workbook editor UI shell (import map + styles)"
```

---

### Task 7: UI — `editor.js` (Preact port, read-only)

**Files:**
- Create: `visualizer/workbook-editor/editor.js`

- [ ] **Step 1: Write the component**

```javascript
import { h, render } from "preact";
import { useEffect, useMemo, useState } from "preact/hooks";
import htm from "htm";

const html = htm.bind(h);
const PAGE_SIZE = 100;

async function fetchJson(url) {
  const res = await fetch(url);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.error || `${url} -> HTTP ${res.status}`);
  return body;
}

function fmt(v) {
  if (v === null || v === undefined || v === "") return html`<span class="dim">—</span>`;
  if (v === true) return "True";
  if (v === false) return "False";
  return String(v);
}

/* ── Form Structure tab ───────────────────────────────────── */

function ModelCards({ models }) {
  return html`<div class="cards">
    ${models.map((m, i) => html`
      <div class=${m.active ? "card active" : "card"} key=${m.key}>
        <div class="name">${m.label}<span class="ord">#${m.displayOrder ?? i + 1}</span></div>
        <div class="badges">
          <span class=${m.active ? "badge green" : "badge"}>${m.active ? "Active" : "Scaffold"}</span>
          ${m.promoted && html`<span class="badge blue">Runtime</span>`}
          ${m.defaultModel && html`<span class="badge amber">Default</span>`}
        </div>
      </div>`)}
  </div>`;
}

function stepSections(data, modelKey, stepKey) {
  const ctx = data.contextSections
    .filter((c) => c.modelKey === modelKey && c.stepKey === stepKey)
    .map((c) => ({ id: c.sectionId, label: c.name, shared: false }));
  const pres = data.sectionPresentation
    .filter((p) => p.modelKey === modelKey && p.stepKey === stepKey)
    .sort((a, b) => (a.order || 0) - (b.order || 0))
    .map((p) => {
      const master = data.sections.find((s) => s.sectionId === p.sectionId);
      return { id: p.sectionId, label: p.label || (master && master.name) || p.sectionId, shared: false };
    });
  const seen = new Set([...ctx, ...pres].map((s) => s.id));
  const shared = data.sections
    .filter((s) => s.stepKey === stepKey && !seen.has(s.sectionId))
    .map((s) => ({ id: s.sectionId, label: s.name, shared: true }));
  return [...ctx, ...pres, ...shared];
}

function StructureTab({ data, modelKey, setModelKey }) {
  const steps = data.steps.filter((s) => s.modelKey === modelKey);
  return html`
    <section>
      <h2 class="sec">Model Registry (model_master · model_registry_promotion)</h2>
      <${ModelCards} models=${data.models} />
    </section>
    <section>
      <h2 class="sec">Runtime Steps & Sections (runtime_steps · section_presentation)</h2>
      <div class="pills">
        ${data.models.map((m) => html`
          <button
            class=${"pill" + (m.key === modelKey ? " on" : "") + (m.active ? "" : " scaffold")}
            onClick=${() => setModelKey(m.key)} key=${m.key}
          >${m.label}</button>`)}
      </div>
      ${steps.length === 0
        ? html`<p class="note">No workbook-owned runtime steps for this model — runtime_steps has no active rows for “${modelKey}”.</p>`
        : html`<div class="steps">
            ${steps.map((s) => {
              const secs = stepSections(data, modelKey, s.stepKey);
              return html`<div class="step" key=${s.stepKey}>
                <span class="num">${s.order}</span>
                <div>
                  <div class="label">${s.label}</div>
                  <div class="key mono">${s.stepKey}</div>
                </div>
                <div class="secs">
                  ${secs.length === 0
                    ? html`<span class="note">no sections (computed)</span>`
                    : secs.map((sec) => html`
                        <span class=${sec.shared ? "chip shared" : "chip"} title=${sec.id} key=${sec.id}>
                          ${sec.label}
                        </span>`)}
                </div>
              </div>`;
            })}
          </div>`}
    </section>`;
}

/* ── Sheet Browser tab ────────────────────────────────────── */

function SheetTable({ data, name }) {
  const [sheet, setSheet] = useState(null);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);
  const [open, setOpen] = useState(null);

  useEffect(() => {
    setSheet(null); setError(null); setQuery(""); setPage(0); setOpen(null);
    fetchJson(`/api/sheet/${encodeURIComponent(name)}`).then(setSheet).catch((e) => setError(e.message));
  }, [name]);

  const meta = data.sheets.find((s) => s.name === name) || {};
  const filtered = useMemo(() => {
    if (!sheet) return [];
    const q = query.trim().toLowerCase();
    if (!q) return sheet.rows;
    return sheet.rows.filter((r) =>
      Object.values(r).some((v) => String(v ?? "").toLowerCase().includes(q)),
    );
  }, [sheet, query]);

  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, pages - 1);
  const rows = filtered.slice(safePage * PAGE_SIZE, safePage * PAGE_SIZE + PAGE_SIZE);
  const cols = sheet ? sheet.headers.slice(0, 8) : [];
  const extra = sheet ? sheet.headers.length - cols.length : 0;

  return html`<div class="panel">
    <div class="bar">
      <span class="title">${name}</span>
      ${meta.keyCols && html`<span class="badge">key: ${meta.keyCols.join(" + ")}</span>`}
      ${meta.readOnly && html`<span class="badge">read-only</span>`}
      <span class="meta">${filtered.length} / ${meta.rowCount ?? "?"} rows${extra > 0 ? ` · +${extra} more cols in row detail` : ""}</span>
      <input type="search" placeholder="Filter rows…" value=${query}
        onInput=${(e) => { setQuery(e.target.value); setPage(0); setOpen(null); }} />
    </div>
    ${error && html`<div class="error">${error}</div>`}
    ${!sheet && !error && html`<div class="loading">Loading ${name}…</div>`}
    ${sheet && html`<div class="tablewrap"><table>
      <thead><tr>${cols.map((c) => html`<th key=${c}>${c}</th>`)}</tr></thead>
      <tbody>
        ${rows.length === 0 && html`<tr><td colSpan=${cols.length} class="dim">No rows match.</td></tr>`}
        ${rows.map((r, i) => {
          const idx = safePage * PAGE_SIZE + i;
          return html`
            <tr class="row" key=${idx} onClick=${() => setOpen(open === idx ? null : idx)}>
              ${cols.map((c) => html`<td key=${c} title=${String(r[c] ?? "")}>${fmt(r[c])}</td>`)}
            </tr>
            ${open === idx && html`<tr class="detail"><td colSpan=${cols.length}>
              <dl>${sheet.headers.map((hcol) => html`
                <dt key=${"t" + hcol}>${hcol}</dt><dd key=${"d" + hcol}>${fmt(r[hcol])}</dd>`)}
              </dl>
            </td></tr>`}`;
        })}
      </tbody>
    </table></div>
    <div class="pager">
      <button disabled=${safePage === 0} onClick=${() => { setPage(safePage - 1); setOpen(null); }}>‹ Prev</button>
      <span>page ${safePage + 1} / ${pages}</span>
      <button disabled=${safePage >= pages - 1} onClick=${() => { setPage(safePage + 1); setOpen(null); }}>Next ›</button>
    </div>`}
  </div>`;
}

function BrowserTab({ data, modelKey, setModelKey }) {
  const modelEntries = data.modelSheets[modelKey] || [];
  const [sheetName, setSheetName] = useState(modelEntries[0]?.sheet || null);

  useEffect(() => {
    const entries = data.modelSheets[modelKey] || [];
    setSheetName(entries[0]?.sheet || null);
  }, [modelKey]);

  const modelSheetNames = new Set(modelEntries.map((e) => e.sheet));
  const otherSheets = data.sheets.map((s) => s.name).filter((n) => !modelSheetNames.has(n)).sort();

  return html`
    <div class="pills">
      ${data.models.map((m) => html`
        <button
          class=${"pill" + (m.key === modelKey ? " on" : "") + (m.active ? "" : " scaffold")}
          onClick=${() => setModelKey(m.key)} key=${m.key}
        >${m.label}${m.active ? "" : " · scaffold"}</button>`)}
    </div>
    <div class="pills">
      ${modelEntries.map((e) => html`
        <button class=${"pill sheet" + (e.sheet === sheetName ? " on" : "")}
          onClick=${() => setSheetName(e.sheet)} title=${e.role} key=${e.sheet}
        >${e.sheet}</button>`)}
      <select class="other" value=${modelSheetNames.has(sheetName) ? "" : sheetName || ""}
        onChange=${(e) => e.target.value && setSheetName(e.target.value)}>
        <option value="">other sheets…</option>
        ${otherSheets.map((n) => html`<option value=${n} key=${n}>${n}</option>`)}
      </select>
    </div>
    ${sheetName
      ? html`<${SheetTable} data=${data} name=${sheetName} key=${sheetName} />`
      : html`<p class="note">No registered source sheets for this model — pick one from “other sheets…”.</p>`}`;
}

/* ── App shell ────────────────────────────────────────────── */

function App() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("structure");
  const [modelKey, setModelKey] = useState(null);

  useEffect(() => {
    fetchJson("/api/workbook")
      .then((d) => {
        setData(d);
        const first = d.models.find((m) => m.defaultModel) || d.models[0];
        setModelKey(first ? first.key : null);
      })
      .catch((e) => setError(e.message));
  }, []);

  return html`
    <header class="app">
      <div>
        <h1>Corvette Master Workbook — Review</h1>
        <div class="sub mono">
          ${data ? `${data.workbook.path} · ${data.workbook.sheetCount} sheets · read-only (Phase 1)` : "loading…"}
        </div>
      </div>
      <nav class="tabs">
        <button class=${tab === "structure" ? "on" : ""} onClick=${() => setTab("structure")}>Form Structure</button>
        <button class=${tab === "browser" ? "on" : ""} onClick=${() => setTab("browser")}>Sheet Browser</button>
      </nav>
    </header>
    <main>
      ${error && html`<div class="error">Failed to load workbook payload: ${error}</div>`}
      ${!data && !error && html`<div class="loading">Loading workbook…</div>`}
      ${data && modelKey && tab === "structure" &&
        html`<${StructureTab} data=${data} modelKey=${modelKey} setModelKey=${setModelKey} />`}
      ${data && modelKey && tab === "browser" &&
        html`<${BrowserTab} data=${data} modelKey=${modelKey} setModelKey=${setModelKey} />`}
    </main>`;
}

render(html`<${App} />`, document.getElementById("app"));
```

- [ ] **Step 2: Verify in a real browser**

```bash
.venv/bin/python scripts/workbook_editor_server.py --port 8027 &
```

Then load `http://127.0.0.1:8027/` with the available browser tooling (Claude Preview / Playwright MCP) and confirm:
- header shows `stingray_master.xlsx · 81 sheets · read-only (Phase 1)`;
- Form Structure shows 5 model cards (Stingray Active/Runtime/Default; ZR1/ZR1X Scaffold) and 14 numbered steps for Stingray; switching to Z06 shows the "no workbook-owned runtime steps" note;
- Sheet Browser: model pills switch sheet pill sets; `stingray_ovs` paginates (1,621 rows, 17 pages); the filter box narrows rows; clicking a row expands full-column detail; "other sheets…" reaches `form_steps` with a read-only badge;
- zero console errors. Then `kill %1`.

- [ ] **Step 3: Commit**

```bash
git add visualizer/workbook-editor/editor.js
git commit -m "feat: read-only workbook review UI (Preact/htm port)"
```

---

### Task 8: Delete the JSX artifact, document the tool

**Files:**
- Delete: `visualizer/workbook-editor.jsx`
- Modify: `README.md` (Repository Structure bullet for `visualizer/`)
- Modify: `AGENTS.md` (new short workflow section)

- [ ] **Step 1: Delete the dead component**

```bash
git rm visualizer/workbook-editor.jsx
```

- [ ] **Step 2: Update README.md**

Change the `visualizer/` bullet under Repository Structure to:

```markdown
- `visualizer/`, `src/` - 2D visualizer scripts, exterior/wheel image assets, and the local workbook review tool under `visualizer/workbook-editor/` (separate from the order-form runtime).
- `scripts/workbook_editor_server.py` - localhost-only, read-only server for the workbook review UI (`.venv/bin/python scripts/workbook_editor_server.py`, then open `http://127.0.0.1:8027/`).
```

- [ ] **Step 3: Add AGENTS.md section** (after "Workbook Update Workflow")

```markdown
## Workbook Review Tool (dev only)

`scripts/workbook_editor_server.py` serves a localhost read-only UI for reviewing `stingray_master.xlsx`:

```sh
.venv/bin/python scripts/workbook_editor_server.py
# open http://127.0.0.1:8027/
```

It derives models, sheet registries, schemas, and reference domains live from the workbook (`model_master`, `model_workbook_sources`, `runtime_steps`, `section_master`/`section_presentation`); nothing is hardcoded that a workbook sheet owns. Phase 1 has no write surface — it never modifies the workbook. See `workbook-editor-integration-spec.md` for the phased plan (Phase 2 adds a gated, non-breaking write path).
```

- [ ] **Step 4: Commit**

```bash
git add README.md AGENTS.md
git commit -m "docs: document workbook review tool; remove unintegrated JSX artifact"
```

---

### Task 9: Final gates

- [ ] **Step 1: Full python test pass**

Run: `.venv/bin/python -m unittest discover -s tests -p "test_*.py" -v`
Expected: PASS (existing metadata tests + new editor tests)

- [ ] **Step 2: Workbook untouched**

Run: `git status --short stingray_master.xlsx && .venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx | tail -3`
Expected: no workbook diff; schema `status: valid`.

- [ ] **Step 3: Node test spot-check (no generator code changed, regression evidence only)**

Run: `node --test tests/workbook-schema-standardization.test.mjs`
Expected: PASS

---

## Self-Review Notes

- Spec coverage: §4.1 GET endpoints ✓ (Tasks 3/5), §4.2 vendored UI ✓ (Tasks 1/6/7), §4.3 derivation incl. reference domains ✓ (Task 3), readOnly classification ✓, Phase 1 file list ✓ (editor_ops meta Task 2, server Tasks 3/5, UI Tasks 6/7, jsx deletion + docs Task 8, payload tests Task 3). POST endpoints, lints, and edit UI are Phase 2/3 — intentionally absent.
- `tests/test_editor_ops_meta.py` is a small extra file vs. the spec's file table (spec named only the payload test); it guards the meta registry the payload test depends on. Acceptable addition, noted here.
- Type names consistent: `EDITOR_SHEET_META`/`SOURCE_ROLE_FAMILIES` (Tasks 2→3), `build_payload`/`extract_workbook`/`sheet_payload` (Tasks 3→5→tests), payload keys camelCase end-to-end (`modelSheets`, `referenceDomains`, `keyCols`).
