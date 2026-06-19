#!/usr/bin/env python3
"""Tests for workbook-owned visualizer layer metadata in asset_map."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from corvette_form_generator.contract import (  # noqa: E402
    ASSET_LAYER_FIELDS,
    asset_fields,
    interior_asset_map,
    option_asset_map,
)


def asset_workbook(rows: list[dict[str, object]]) -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.title = "asset_map"
    headers = [
        "model_key",
        "target_type",
        "target_id",
        "image_url",
        "image_alt",
        "image_fit",
        "image_position",
        "layer_url",
        "layer_url_full",
        "layer_z",
        "layer_role",
        "active",
        "notes",
    ]
    ws.append(headers)
    for row in rows:
        ws.append([row.get(header, "") for header in headers])
    return wb


class AssetVisualizerContractTests(unittest.TestCase):
    def test_asset_fields_keep_layer_metadata_separate_from_card_image_metadata(self) -> None:
        fields = asset_fields(
            {
                "image_url": "https://example.test/card.png",
                "image_alt": "Card image",
                "image_fit": "swatch",
                "image_position": "center",
                "layer_url": "https://example.test/layer.webp",
                "layer_url_full": "https://example.test/layer-full.png",
                "layer_z": "20",
                "layer_role": "interior_color",
            }
        )

        self.assertEqual(fields["image_url"], "https://example.test/card.png")
        self.assertEqual(fields["layer_url"], "https://example.test/layer.webp")
        self.assertEqual(fields["layer_url_full"], "https://example.test/layer-full.png")
        self.assertEqual(fields["layer_z"], "20")
        self.assertEqual(fields["layer_role"], "interior_color")

    def test_layer_only_asset_rows_are_loaded_for_options_and_interiors(self) -> None:
        wb = asset_workbook(
            [
                {
                    "model_key": "stingray",
                    "target_type": "option",
                    "target_id": "opt_abc_001",
                    "layer_url": "https://example.test/seat-layer.webp",
                    "layer_z": "30",
                    "layer_role": "seat",
                    "active": True,
                },
                {
                    "model_key": "stingray",
                    "target_type": "interior_code",
                    "target_id": "HTA",
                    "layer_url": "https://example.test/interior-layer.webp",
                    "layer_z": "40",
                    "layer_role": "interior_color",
                    "active": True,
                },
            ]
        )

        option_assets = option_asset_map(wb, "stingray")
        interior_assets = interior_asset_map(wb, "stingray")

        self.assertEqual(option_assets["opt_abc_001"]["layer_url"], "https://example.test/seat-layer.webp")
        self.assertEqual(option_assets["opt_abc_001"]["layer_z"], "30")
        self.assertEqual(interior_assets["HTA"]["layer_url"], "https://example.test/interior-layer.webp")
        self.assertEqual(interior_assets["HTA"]["layer_role"], "interior_color")

    def test_image_only_asset_rows_do_not_emit_blank_layer_fields(self) -> None:
        wb = asset_workbook(
            [
                {
                    "model_key": "stingray",
                    "target_type": "option",
                    "target_id": "opt_card_001",
                    "image_url": "https://example.test/card.png",
                    "image_alt": "Card image",
                    "image_fit": "cover",
                    "image_position": "center",
                    "active": True,
                }
            ]
        )

        fields = option_asset_map(wb, "stingray")["opt_card_001"]

        for field in ASSET_LAYER_FIELDS:
            self.assertNotIn(field, fields)


if __name__ == "__main__":
    unittest.main()
