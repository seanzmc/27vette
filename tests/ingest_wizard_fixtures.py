#!/usr/bin/env python3
"""Compact fixture workbooks for wizard tests: a raw GM order-guide export
(Pass A) and a canonical-workbook stand-in (Pass B read-only pickers)."""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

STINGRAY_VARIANTS = ["Coupe\n1YC07\n1LT", "Coupe\n1YC07\n2LT", "Convertible\n1YC67\n1LT"]
ZR1_VARIANTS = ["ZR1 Coupe\n1YR07\n1LZ", "ZR1X Coupe\n1YS07\n1LZ"]
BASE_HEADERS = ["Orderable RPO Code", "Ref. Only RPO Code", "Description"]


def matrix_sheet(wb: Workbook, name: str, family_title: str, variants: list[str], rows: list[list[object]]) -> None:
    ws = wb.create_sheet(name)
    ws.append([family_title])
    ws.append(["", "", "S = Standard Equipment  A = Available"])
    ws.append(BASE_HEADERS + variants)
    for row in rows:
        ws.append(row)


def build_raw_export(path: Path) -> Path:
    wb = Workbook()
    wb.remove(wb.active)

    ws = wb.create_sheet("Price Schedule")
    ws.append(["2027 CHEVROLET CORVETTE"])
    ws.append([])
    ws.append(["Base Model Prices"])
    ws.append(["", "Model", "Model Description", "List", "Factory", "MSRP(c)"])
    ws.append(["", "1YC07", "Corvette Stingray Coupe 1LT", 71000, 0, 71000])
    ws.append(["", "1YR07", "Corvette ZR1 Coupe 1LZ", 194700, 0, 194700])
    ws.append([])
    ws.append(["Additional Options"])
    ws.append(["", "Option Code", "Description", "List", "Factory", "MSRP(c)"])
    ws.append(["", "Additional Options:"])
    ws.append(["", "BV4", "Personalized Plaque", "", 395, 0, 395])
    ws.append(["", "PDB", "Carbon Wheel Package", "with ROY wheels", 16000, 0, 16000])
    ws.append(["", "PDB", "Carbon Wheel Package", "with ROZ wheels", 17000, 0, 17000])
    ws.append(["", "YYY", "Orphan priced option", "", 500, 0, 500])

    matrix_sheet(
        wb,
        "Equipment Groups 1",
        "Stingray",
        STINGRAY_VARIANTS,
        [
            ["Equipment Groups"],
            ["", "UQH", "Audio system feature, Bose premium", "--", "■", "--"],
            ["BV4", "", "Personalized Plaque. Not available with (PDB).", "A1", "A", "A"],
            ["E60", "", "Front Lift", "A/D1", "A", "--"],
            ["ZZZ", "", "Mystery option with odd status", "?", "A", "A"],
            ["", "", "Narrative-only detail row without any RPO", "", "", ""],
        ],
    )
    matrix_sheet(
        wb,
        "Equipment Groups 4",
        "ZR1 and ZR1X",
        ZR1_VARIANTS,
        [
            ["Equipment Groups"],
            ["PDB", "", "Carbon Wheel Package", "A", "A"],
            ["C2Z", "", "ZR1 only cosmetic pack", "A", "--"],
        ],
    )
    matrix_sheet(
        wb,
        "Standard Equipment 1",
        "Stingray",
        STINGRAY_VARIANTS,
        [
            ["", "AJ7", "Airbags, frontal and side-impact", "S1", "S1", "S1"],
            ["", "CJ2", "Air conditioning, dual-zone", "S", "S", "S"],
            ["", "UQH", "Audio, standard", "S", "S", "S"],
            ["EYT", "", "Rare orderable row on SE sheet", "A", "S", "S"],
        ],
    )

    ws = wb.create_sheet("Color and Trim 1")
    ws.append(["Recommended"])
    ws.append(["Some", "unrelated", "layout"])

    wb.save(path)
    return path


def _table(wb: Workbook, name: str, headers: list[str], rows: list[list[object]]) -> None:
    ws = wb.create_sheet(name)
    ws.append(headers)
    for row in rows:
        ws.append(row)


def build_master_workbook(path: Path) -> Path:
    """Canonical-workbook stand-in for Pass B: model metadata, section picker,
    and z06 presentation rows used as the template model. Read-only in tests."""

    wb = Workbook()
    wb.remove(wb.active)
    _table(
        wb,
        "model_master",
        ["model_key", "registry_key", "model_label", "model_year", "dataset_name", "export_slug", "expected_variant_count", "default_model", "active", "notes"],
        [
            ["z06", "z06", "Z06", 2027, "z06 dataset", "z06", 1, False, True, ""],
            ["zr1", "zr1", "ZR1", 2027, "zr1 scaffold", "zr1", 2, False, False, ""],
        ],
    )
    _table(
        wb,
        "model_registry_promotion",
        ["model_key", "registry_key", "promoted_to_runtime", "default_model", "artifact_path", "artifact_type", "legacy_alias", "active", "display_order", "notes"],
        [
            ["z06", "z06", True, False, "form-output/runtime/z06-runtime-contract.json", "runtime_contract", "", True, 1, ""],
            ["zr1", "zr1", False, False, "", "", "", False, 2, ""],
        ],
    )
    _table(
        wb,
        "variant_master",
        ["variant_id", "model_year", "trim_level", "body_style", "display_name", "base_price", "display_order", "active"],
        [
            ["1lz_r07", 2027, "1lz", "coupe", "Corvette ZR1 Coupe 1LZ", 197195, 25, False],
            ["3lz_r67", 2027, "3lz", "convertible", "Corvette ZR1 Convertible 3LZ", 218195, 28, False],
            ["1lz_s07", 2027, "1lz", "coupe", "Corvette ZR1X Coupe 1LZ", 227395, 29, False],
        ],
    )
    _table(
        wb,
        "model_variants",
        ["model_key", "variant_id", "display_order", "active", "notes"],
        [
            ["zr1", "1lz_r07", 1, False, ""],
            ["zr1", "3lz_r67", 2, False, ""],
            ["zr1x", "1lz_s07", 1, False, ""],
        ],
    )
    _table(
        wb,
        "model_workbook_sources",
        ["model_key", "source_role", "sheet_name", "active", "notes"],
        [
            ["z06", "source_option_sheet", "z06_options", True, ""],
            ["zr1", "source_option_sheet", "zr1_options", False, "inactive scaffold, must be ignored"],
        ],
    )
    option_headers = ["option_id", "rpo", "price", "option_name", "description", "detail_raw", "section_id", "selectable", "display_order", "active", "display_behavior"]
    _table(
        wb,
        "z06_options",
        option_headers,
        [
            ["opt_pdb_001", "PDB", 16000, "Carbon Fiber Wheel Package", "Visible carbon", "", "sec_whee_001", "", 10, True, ""],
        ],
    )
    _table(wb, "z06_ovs", ["option_id", "variant_id", "status"], [["opt_pdb_001", "1lz_h07", "available"]])
    # The inactive source's sheet must actually exist with a conflicting row,
    # so the active-flag filter is the only thing excluding it.
    _table(
        wb,
        "zr1_options",
        option_headers,
        [
            # Deliberately uses the id the plan builder would mint first for
            # PDB: locks in the add-after-delete seeding fix (new ids must
            # avoid keys that exist pre-batch even when deleted in-batch).
            ["opt_pdb_001", "PDB", 99999, "WRONG Scaffold Package", "must never surface", "", "sec_pain_001", "", 10, True, ""],
        ],
    )
    _table(
        wb,
        "section_master",
        ["section_id", "section_name", "selection_mode", "is_required", "display_order", "standard_behavior", "step_key"],
        [
            ["sec_pain_001", "Exterior Color", "single", True, 1, "", "paint"],
            ["sec_whee_001", "Wheels", "single", True, 2, "", "wheels"],
        ],
    )
    # Headers mirror the live workbook (probe 2026-07-06).
    presentation_rows = {
        "runtime_steps": (
            ["model_key", "step_key", "step_label", "runtime_order", "source", "active", "notes"],
            [["z06", "paint", "Paint", 1, "", True, ""], ["z06", "wheels", "Wheels", 2, "", True, ""]],
        ),
        "section_presentation": (
            ["model_key", "section_id", "display_label", "step_key", "display_behavior", "section_display_order", "standard_equipment_bucket", "standard_equipment_group_type", "auto_added_bucket", "active", "notes"],
            [["z06", "sec_pain_001", "Exterior Color", "paint", "", 1, "", "", "", True, ""]],
        ),
        "context_section_master": (
            ["model_key", "context_type", "section_id", "section_name", "selection_mode", "choice_mode", "is_required", "standard_behavior", "section_display_order", "step_key", "step_label", "active", "notes"],
            [["z06", "body", "ctx_body", "Body", "single", "", True, "", 1, "body", "Body", True, ""]],
        ),
        "order_summary_sections": (
            ["model_key", "section_key", "section_label", "display_order", "active", "notes"],
            [["z06", "sum_paint", "Exterior", 1, True, ""]],
        ),
        "step_order_summary_map": (
            ["model_key", "step_key", "section_key", "active", "notes"],
            [["z06", "paint", "sum_paint", True, ""]],
        ),
    }
    for sheet, (headers, rows) in presentation_rows.items():
        _table(wb, sheet, headers, rows)
    wb.save(path)
    return path
