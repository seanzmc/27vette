#!/usr/bin/env python3
"""Focused tests for Phase 7 workbook-backed model configuration metadata."""

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

from corvette_form_generator.model_configs import (  # noqa: E402
    REQUIRED_GENERATION_SOURCE_ROLES,
    base_model_config,
    discover_generation_model_configs,
)
from corvette_form_generator.runtime_metadata import load_model_config_overrides  # noqa: E402

BASE_STINGRAY_CONFIG = base_model_config("stingray")


def workbook_with_model_metadata(
    *,
    model_rows: list[dict[str, object]] | None = None,
    source_rows: list[dict[str, object]] | None = None,
    variant_rows: list[dict[str, object]] | None = None,
) -> Workbook:
    wb = Workbook()
    del wb[wb.sheetnames[0]]
    append_sheet(
        wb,
        "model_master",
        [
            "model_key",
            "registry_key",
            "model_label",
            "model_year",
            "dataset_name",
            "export_slug",
            "expected_variant_count",
            "default_model",
            "active",
            "notes",
        ],
        model_rows or [],
    )
    append_sheet(
        wb,
        "model_workbook_sources",
        ["model_key", "source_role", "sheet_name", "active", "notes"],
        source_rows or [],
    )
    append_sheet(
        wb,
        "model_variants",
        ["model_key", "variant_id", "display_order", "active", "notes"],
        variant_rows or [],
    )
    return wb


def append_sheet(wb: Workbook, name: str, headers: list[str], rows: list[dict[str, object]]) -> None:
    ws = wb.create_sheet(name)
    ws.append(headers)
    for row in rows:
        ws.append([row.get(header, "") for header in headers])


def stingray_model_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "model_key": "stingray",
        "registry_key": "stingray",
        "model_label": "Workbook Stingray",
        "model_year": "2027",
        "dataset_name": "Workbook dataset",
        "expected_variant_count": 2,
        "active": True,
    }
    row.update(overrides)
    return row


def required_source_rows(model_key: str = "stingray", *, active: bool = True) -> list[dict[str, object]]:
    return [
        {
            "model_key": model_key,
            "source_role": role,
            "sheet_name": f"{model_key}_{role}",
            "active": active,
        }
        for role in REQUIRED_GENERATION_SOURCE_ROLES
    ]


def discover_temp_configs(wb: Workbook):
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "model-discovery.xlsx"
        wb.save(path)
        return discover_generation_model_configs(path)


class ModelConfigMetadataTests(unittest.TestCase):
    def test_generation_discovery_binds_configs_to_explicit_paths(self) -> None:
        wb = workbook_with_model_metadata(
            model_rows=[stingray_model_row()],
            source_rows=required_source_rows("stingray"),
            variant_rows=[
                {"model_key": "stingray", "variant_id": "a_variant", "display_order": 1, "active": True},
                {"model_key": "stingray", "variant_id": "z_variant", "display_order": 2, "active": True},
            ],
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            target_root = Path(tmpdir) / "candidate"
            workbook_path = Path(tmpdir) / "model-discovery.xlsx"
            output_dir = target_root / "generated"
            app_dir = target_root / "browser"
            wb.save(workbook_path)

            config = discover_generation_model_configs(
                workbook_path,
                root=target_root,
                output_dir=output_dir,
                app_dir=app_dir,
            )["stingray"]

        self.assertEqual(config.workbook_path, workbook_path)
        self.assertEqual(config.root, target_root)
        self.assertEqual(config.output_dir, output_dir)
        self.assertEqual(config.app_dir, app_dir)

    def test_header_only_metadata_falls_back_to_constants(self) -> None:
        wb = workbook_with_model_metadata()
        resolved = load_model_config_overrides(wb, BASE_STINGRAY_CONFIG)
        self.assertEqual(resolved, BASE_STINGRAY_CONFIG)

    def test_workbook_metadata_overrides_config_fields(self) -> None:
        wb = workbook_with_model_metadata(
            model_rows=[stingray_model_row()],
            source_rows=[
                {
                    "model_key": "stingray",
                    "source_role": "source_option_sheet",
                    "sheet_name": "workbook_options",
                    "active": True,
                },
                {
                    "model_key": "stingray",
                    "source_role": "status_sheet",
                    "sheet_name": "workbook_status",
                    "active": True,
                },
            ],
            variant_rows=[
                {"model_key": "stingray", "variant_id": "z_variant", "display_order": 2, "active": True},
                {"model_key": "stingray", "variant_id": "a_variant", "display_order": 1, "active": True},
            ],
        )
        resolved = load_model_config_overrides(wb, BASE_STINGRAY_CONFIG)
        self.assertEqual(resolved.model_label, "Workbook Stingray")
        self.assertEqual(resolved.dataset_name, "Workbook dataset")
        self.assertEqual(resolved.source_option_sheet, "workbook_options")
        self.assertEqual(resolved.status_sheet, "workbook_status")
        self.assertEqual(resolved.variant_ids, ("a_variant", "z_variant"))
        self.assertEqual(resolved.expected_variant_count, 2)
        self.assertEqual(BASE_STINGRAY_CONFIG.source_option_sheet, "stingray_options")

    def test_workbook_metadata_overrides_interior_source_sheet(self) -> None:
        wb = workbook_with_model_metadata(
            model_rows=[stingray_model_row()],
            source_rows=[
                {
                    "model_key": "stingray",
                    "source_role": "interior_source_sheet",
                    "sheet_name": "LZ_Interiors",
                    "active": True,
                }
            ],
            variant_rows=[
                {"model_key": "stingray", "variant_id": "1lz_h07", "display_order": 1, "active": True},
                {"model_key": "stingray", "variant_id": "3lz_h07", "display_order": 2, "active": True},
            ],
        )

        resolved = load_model_config_overrides(wb, BASE_STINGRAY_CONFIG)

        self.assertEqual(resolved.interior_source_sheet, "LZ_Interiors")
        self.assertEqual(BASE_STINGRAY_CONFIG.interior_source_sheet, "lt_interiors")

    def test_unknown_source_role_fails_fast(self) -> None:
        wb = workbook_with_model_metadata(
            source_rows=[
                {
                    "model_key": "stingray",
                    "source_role": "surprise_sheet",
                    "sheet_name": "surprise",
                    "active": True,
                }
            ]
        )
        with self.assertRaisesRegex(ValueError, "Unknown model_workbook_sources roles"):
            load_model_config_overrides(wb, BASE_STINGRAY_CONFIG)

    def test_duplicate_source_role_fails_fast(self) -> None:
        wb = workbook_with_model_metadata(
            source_rows=[
                {
                    "model_key": "stingray",
                    "source_role": "source_option_sheet",
                    "sheet_name": "first",
                    "active": True,
                },
                {
                    "model_key": "stingray",
                    "source_role": "source_option_sheet",
                    "sheet_name": "second",
                    "active": True,
                },
            ]
        )
        with self.assertRaisesRegex(ValueError, "Duplicate active model_workbook_sources roles"):
            load_model_config_overrides(wb, BASE_STINGRAY_CONFIG)

    def test_variant_count_mismatch_fails_fast(self) -> None:
        wb = workbook_with_model_metadata(
            model_rows=[stingray_model_row(expected_variant_count=2)],
            variant_rows=[{"model_key": "stingray", "variant_id": "only_one", "display_order": 1, "active": True}],
        )
        with self.assertRaisesRegex(ValueError, "expected 2 variants"):
            load_model_config_overrides(wb, BASE_STINGRAY_CONFIG)

    def test_duplicate_variant_fails_fast(self) -> None:
        wb = workbook_with_model_metadata(
            variant_rows=[
                {"model_key": "stingray", "variant_id": "dup", "display_order": 1, "active": True},
                {"model_key": "stingray", "variant_id": "dup", "display_order": 2, "active": True},
            ]
        )
        with self.assertRaisesRegex(ValueError, "Duplicate active model_variants rows"):
            load_model_config_overrides(wb, BASE_STINGRAY_CONFIG)

    def test_registry_key_mismatch_fails_fast(self) -> None:
        wb = workbook_with_model_metadata(model_rows=[stingray_model_row(registry_key="wrong")])
        with self.assertRaisesRegex(ValueError, "registry_key"):
            load_model_config_overrides(wb, BASE_STINGRAY_CONFIG)

    def test_generation_discovery_finds_active_models_with_complete_exact_metadata(self) -> None:
        wb = workbook_with_model_metadata(
            model_rows=[stingray_model_row()],
            source_rows=required_source_rows("stingray"),
            variant_rows=[
                {"model_key": "stingray", "variant_id": "a_variant", "display_order": 1, "active": True},
                {"model_key": "stingray", "variant_id": "z_variant", "display_order": 2, "active": True},
            ],
        )

        configs = discover_temp_configs(wb)

        self.assertEqual(list(configs), ["stingray"])
        self.assertEqual(configs["stingray"].variant_ids, ("a_variant", "z_variant"))
        self.assertEqual(configs["stingray"].expected_variant_count, 2)

    def test_generation_discovery_excludes_inactive_scaffolds(self) -> None:
        wb = workbook_with_model_metadata(
            model_rows=[
                stingray_model_row(),
                {
                    "model_key": "zr1",
                    "registry_key": "zr1",
                    "model_label": "ZR1",
                    "expected_variant_count": 2,
                    "active": False,
                },
            ],
            source_rows=[*required_source_rows("stingray"), *required_source_rows("zr1")],
            variant_rows=[
                {"model_key": "stingray", "variant_id": "a_variant", "display_order": 1, "active": True},
                {"model_key": "stingray", "variant_id": "z_variant", "display_order": 2, "active": True},
                {"model_key": "zr1", "variant_id": "zr1_a", "display_order": 1, "active": True},
                {"model_key": "zr1", "variant_id": "zr1_b", "display_order": 2, "active": True},
            ],
        )

        configs = discover_temp_configs(wb)

        self.assertEqual(list(configs), ["stingray"])
        self.assertNotIn("zr1", configs)

    def test_generation_discovery_requires_complete_active_exact_source_roles(self) -> None:
        incomplete_rows = [
            row for row in required_source_rows("stingray") if row["source_role"] != "status_sheet"
        ]
        wb = workbook_with_model_metadata(
            model_rows=[stingray_model_row()],
            source_rows=incomplete_rows,
            variant_rows=[
                {"model_key": "stingray", "variant_id": "a_variant", "display_order": 1, "active": True},
                {"model_key": "stingray", "variant_id": "z_variant", "display_order": 2, "active": True},
            ],
        )

        with self.assertRaisesRegex(ValueError, "missing required active model_workbook_sources roles.*status_sheet"):
            discover_temp_configs(wb)

    def test_generation_discovery_inactive_source_rows_do_not_satisfy_completeness(self) -> None:
        wb = workbook_with_model_metadata(
            model_rows=[stingray_model_row()],
            source_rows=required_source_rows("stingray", active=False),
            variant_rows=[
                {"model_key": "stingray", "variant_id": "a_variant", "display_order": 1, "active": True},
                {"model_key": "stingray", "variant_id": "z_variant", "display_order": 2, "active": True},
            ],
        )

        with self.assertRaisesRegex(ValueError, "missing required active model_workbook_sources roles"):
            discover_temp_configs(wb)

    def test_generation_discovery_global_source_rows_do_not_satisfy_model_completeness(self) -> None:
        global_rows = [
            {**row, "model_key": "shared"}
            for row in required_source_rows("stingray")
        ]
        wb = workbook_with_model_metadata(
            model_rows=[stingray_model_row()],
            source_rows=global_rows,
            variant_rows=[
                {"model_key": "stingray", "variant_id": "a_variant", "display_order": 1, "active": True},
                {"model_key": "stingray", "variant_id": "z_variant", "display_order": 2, "active": True},
            ],
        )

        with self.assertRaisesRegex(ValueError, "missing required active model_workbook_sources roles"):
            discover_temp_configs(wb)

    def test_generation_discovery_requires_positive_expected_variant_count(self) -> None:
        wb = workbook_with_model_metadata(
            model_rows=[stingray_model_row(expected_variant_count=0)],
            source_rows=required_source_rows("stingray"),
            variant_rows=[
                {"model_key": "stingray", "variant_id": "a_variant", "display_order": 1, "active": True},
            ],
        )

        with self.assertRaisesRegex(ValueError, "expected_variant_count"):
            discover_temp_configs(wb)

    def test_generation_discovery_requires_active_exact_variant_rows(self) -> None:
        wb = workbook_with_model_metadata(
            model_rows=[stingray_model_row()],
            source_rows=required_source_rows("stingray"),
            variant_rows=[],
        )

        with self.assertRaisesRegex(ValueError, "requires active model_variants rows"):
            discover_temp_configs(wb)

    def test_generation_discovery_requires_variant_count_to_match_expected_count(self) -> None:
        wb = workbook_with_model_metadata(
            model_rows=[stingray_model_row(expected_variant_count=2)],
            source_rows=required_source_rows("stingray"),
            variant_rows=[{"model_key": "stingray", "variant_id": "only_one", "display_order": 1, "active": True}],
        )

        with self.assertRaisesRegex(ValueError, "expected 2 active model_variants rows; found 1"):
            discover_temp_configs(wb)

    def test_generation_discovery_does_not_require_runtime_promotion_metadata(self) -> None:
        wb = workbook_with_model_metadata(
            model_rows=[stingray_model_row()],
            source_rows=required_source_rows("stingray"),
            variant_rows=[
                {"model_key": "stingray", "variant_id": "a_variant", "display_order": 1, "active": True},
                {"model_key": "stingray", "variant_id": "z_variant", "display_order": 2, "active": True},
            ],
        )

        configs = discover_temp_configs(wb)

        self.assertIn("stingray", configs)


if __name__ == "__main__":
    unittest.main()
