#!/usr/bin/env python3
"""Compact raw GM order-guide fixture workbook for wizard Pass A tests."""

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
