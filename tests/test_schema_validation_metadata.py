#!/usr/bin/env python3
"""Tests for workbook metadata-derived schema validation."""

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

from corvette_form_generator.schema_validation import validate_workbook_schema  # noqa: E402


OPTION_HEADERS = ["option_id", "rpo", "selectable", "active", "price"]
OVS_HEADERS = ["option_id", "variant_id", "status"]
RULE_MAPPING_HEADERS = [
    "rule_id",
    "source_id",
    "target_id",
    "rule_type",
    "review_flag",
    "generation_action",
    "normalization_status",
    "normalization_reason",
    "replacement_group_id",
    "replacement_rule_id",
]
PRICE_RULE_HEADERS = ["rule_id", "target_id", "price_rule_type", "price_value", "review_flag"]
ACTIVE_GROUP_HEADERS = ["group_id", "active"]
ACTIVE_MEMBER_HEADERS = ["group_id", "option_id", "active"]
VARIANT_OVERRIDE_HEADERS = ["option_id", "variant_id", "active", "selectable"]
INTERIOR_HEADERS = ["interior_id", "Trim", "Price", "active_for_stingray", "requires_r6x", "Seat"]


def append_sheet(wb: Workbook, name: str, headers: list[str], rows: list[dict[str, object]] | None = None) -> None:
    ws = wb.create_sheet(name)
    ws.append(headers)
    for row in rows or []:
        ws.append([row.get(header, None) for header in headers])


def minimal_schema_workbook(
    *,
    extra_model_rows: list[dict[str, object]] | None = None,
    extra_source_rows: list[dict[str, object]] | None = None,
    extra_sheets: dict[str, tuple[list[str], list[dict[str, object]]]] | None = None,
) -> Workbook:
    wb = Workbook()
    del wb[wb.sheetnames[0]]

    append_sheet(wb, "variant_master", ["variant_id", "active"])
    append_sheet(wb, "section_master", ["section_id", "active"])
    append_sheet(wb, "model_master", ["model_key", "registry_key", "active"], extra_model_rows or [])
    append_sheet(
        wb,
        "model_workbook_sources",
        ["model_key", "source_role", "sheet_name", "active", "notes"],
        extra_source_rows or [],
    )
    append_sheet(wb, "model_variants", ["model_key", "variant_id", "display_order", "active", "notes"])

    for name in ("stingray_options", "grandSport_options"):
        append_sheet(wb, name, OPTION_HEADERS, [{"option_id": "opt_known", "rpo": "ABC", "selectable": True, "active": True, "price": 0}])
    for name in ("stingray_ovs", "grandSport_ovs"):
        append_sheet(wb, name, OVS_HEADERS, [{"option_id": "opt_known", "variant_id": "v1", "status": "available"}])
    for name in ("rule_mapping", "grandSport_rule_mapping"):
        append_sheet(wb, name, RULE_MAPPING_HEADERS)
    for name in ("price_rules", "grandSport_price_rules"):
        append_sheet(wb, name, PRICE_RULE_HEADERS)
    append_sheet(wb, "lt_interiors", INTERIOR_HEADERS)
    append_sheet(wb, "LZ_Interiors", INTERIOR_HEADERS)
    append_sheet(wb, "model_interior_scope", ["model_key", "interior_id", "active"])
    append_sheet(wb, "interior_components", ["model_key", "interior_id", "rpo", "active"])
    append_sheet(wb, "PriceRef", ["RPO", "Price"])

    for name, (headers, rows) in (extra_sheets or {}).items():
        if name in wb.sheetnames:
            del wb[name]
        append_sheet(wb, name, headers, rows)
    return wb


def validate_temp_workbook(wb: Workbook):
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "metadata-schema.xlsx"
        wb.save(path)
        return validate_workbook_schema(path, check_live_contract=False)


class SchemaValidationMetadataTests(unittest.TestCase):
    def test_metadata_discovered_ovs_sheet_validates_option_ids(self) -> None:
        wb = minimal_schema_workbook(
            extra_model_rows=[{"model_key": "z06", "registry_key": "z06", "active": True}],
            extra_source_rows=[
                {"model_key": "z06", "source_role": "source_option_sheet", "sheet_name": "z06_options", "active": True},
                {"model_key": "z06", "source_role": "status_sheet", "sheet_name": "z06_ovs", "active": True},
            ],
            extra_sheets={
                "z06_options": (OPTION_HEADERS, [{"option_id": "opt_z06_known", "rpo": "Z06", "selectable": True, "active": True, "price": 0}]),
                "z06_ovs": (OVS_HEADERS, [{"option_id": "opt_missing", "variant_id": "1lz_h07", "status": "available"}]),
            },
        )

        issues = validate_temp_workbook(wb)

        self.assertTrue(
            any(issue.check_id == "ovs_unknown_option_id" and issue.sheet == "z06_ovs" for issue in issues),
            [issue for issue in issues if issue.check_id == "ovs_unknown_option_id"],
        )

    def test_metadata_discovered_source_sheet_must_exist(self) -> None:
        wb = minimal_schema_workbook(
            extra_model_rows=[{"model_key": "zr1", "registry_key": "zr1", "active": True}],
            extra_source_rows=[
                {"model_key": "zr1", "source_role": "source_option_sheet", "sheet_name": "zr1_options", "active": True},
            ],
        )

        issues = validate_temp_workbook(wb)

        self.assertTrue(
            any(issue.check_id == "missing_model_source_sheet" and issue.sheet == "zr1_options" for issue in issues),
            issues,
        )

    def test_metadata_discovered_option_headers_match_by_role(self) -> None:
        wb = minimal_schema_workbook(
            extra_model_rows=[{"model_key": "zr1x", "registry_key": "zr1x", "active": True}],
            extra_source_rows=[
                {"model_key": "zr1x", "source_role": "source_option_sheet", "sheet_name": "zr1x_options", "active": True},
            ],
            extra_sheets={
                "zr1x_options": (
                    ["option_id", "rpo", "selectable", "active", "price", "unexpected_extra"],
                    [{"option_id": "opt_zr1x_known", "rpo": "ZX", "selectable": True, "active": True, "price": 0}],
                ),
            },
        )

        issues = validate_temp_workbook(wb)

        self.assertTrue(
            any(issue.check_id == "source_role_header_drift" and issue.sheet == "source_option_sheet" for issue in issues),
            issues,
        )

    def test_metadata_discovered_interior_source_sheet_role_is_known(self) -> None:
        wb = minimal_schema_workbook(
            extra_model_rows=[{"model_key": "z06", "registry_key": "z06", "active": True}],
            extra_source_rows=[
                {"model_key": "z06", "source_role": "interior_source_sheet", "sheet_name": "LZ_Interiors", "active": True},
            ],
        )

        issues = validate_temp_workbook(wb)

        self.assertFalse(any(issue.check_id == "unknown_model_source_role" for issue in issues), issues)

    def test_metadata_discovered_interior_source_sheet_must_exist(self) -> None:
        wb = minimal_schema_workbook(
            extra_model_rows=[{"model_key": "zr1", "registry_key": "zr1", "active": True}],
            extra_source_rows=[
                {
                    "model_key": "zr1",
                    "source_role": "interior_source_sheet",
                    "sheet_name": "missing_zr1_interiors",
                    "active": True,
                },
            ],
        )

        issues = validate_temp_workbook(wb)

        self.assertTrue(
            any(issue.check_id == "missing_model_source_sheet" and issue.sheet == "missing_zr1_interiors" for issue in issues),
            issues,
        )

    def test_metadata_discovered_lz_interiors_validates_by_interior_role(self) -> None:
        wb = minimal_schema_workbook(
            extra_model_rows=[{"model_key": "zr1x", "registry_key": "zr1x", "active": True}],
            extra_source_rows=[
                {"model_key": "zr1x", "source_role": "interior_source_sheet", "sheet_name": "LZ_Interiors", "active": True},
            ],
            extra_sheets={
                "LZ_Interiors": (
                    INTERIOR_HEADERS,
                    [
                        {
                            "interior_id": "1LZ_AQ9_HTE",
                            "Trim": "1LZ",
                            "Price": "not numeric",
                            "active_for_stingray": True,
                            "requires_r6x": False,
                            "Seat": "AQ9",
                        }
                    ],
                )
            },
        )

        issues = validate_temp_workbook(wb)

        self.assertTrue(
            any(issue.check_id == "price_type_drift" and issue.sheet == "LZ_Interiors" and issue.column == "Price" for issue in issues),
            issues,
        )

    def test_inactive_metadata_source_rows_are_ignored(self) -> None:
        wb = minimal_schema_workbook(
            extra_model_rows=[{"model_key": "future", "registry_key": "future", "active": True}],
            extra_source_rows=[
                {"model_key": "future", "source_role": "source_option_sheet", "sheet_name": "missing_future_options", "active": False},
            ],
        )

        issues = validate_temp_workbook(wb)

        self.assertFalse(any(issue.sheet == "missing_future_options" for issue in issues), issues)


if __name__ == "__main__":
    unittest.main()
