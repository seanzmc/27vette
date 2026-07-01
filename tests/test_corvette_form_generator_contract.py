#!/usr/bin/env python3
# pyright: reportMissingImports=false
"""Focused tests for shared contract-surface helpers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from corvette_form_generator.contract import (  # noqa: E402
    ASSET_IMAGE_FIELDS,
    build_body_context_choices,
    build_model_context_choices,
    build_trim_context_choices,
    merge_option_asset_fields,
)


class ContractHelperTests(unittest.TestCase):
    def test_build_model_context_choices_matches_existing_direct_call_shape(self) -> None:
        variants = [
            {
                "variant_id": "1lt_e07",
                "body_style": "coupe",
                "trim_level": "1LT",
                "display_name": "1LT Coupe",
                "base_price": 70000,
                "display_order": 2,
            },
            {
                "variant_id": "2lt_e67",
                "body_style": "convertible",
                "trim_level": "2LT",
                "display_name": "2LT Convertible",
                "base_price": 78000,
                "display_order": 1,
            },
        ]
        copy_rows = [
            {
                "model_key": "test_model",
                "context_type": "body_style",
                "value": "coupe",
                "body_style": "coupe",
                "info_tooltip": "Coupe tooltip",
            },
            {
                "model_key": "test_model",
                "context_type": "trim_level",
                "value": "2LT",
                "body_style": "convertible",
                "info_tooltip": "2LT convertible tooltip",
            },
        ]
        body_style_display_order = {"coupe": 1, "convertible": 2}
        bodystyle_assets = {
            "body_style__coupe": {
                "image_url": "coupe.jpg",
                "image_alt": "Coupe",
                "image_fit": "cover",
                "image_position": "center",
                "hover_image_url": "coupe-hover.jpg",
                "hover_image_alt": "Coupe hover",
                "hover_image_position": "center",
            }
        }

        expected = build_body_context_choices(
            variants,
            copy_rows,
            "test_model",
            body_style_display_order,
            bodystyle_assets,
        ) + build_trim_context_choices(variants, copy_rows, "test_model")

        self.assertEqual(
            build_model_context_choices(
                variants,
                copy_rows,
                "test_model",
                body_style_display_order,
                bodystyle_assets,
            ),
            expected,
        )

    def test_merge_option_asset_fields_copies_only_asset_fields_from_source_row(self) -> None:
        destination = {"option_id": "opt_q9i_001", "image_url": "stale-target.jpg", "label": "Kept"}
        source_rows = {
            "opt_q9i_001": {
                "image_url": "source.jpg",
                "image_alt": "Source image",
                "image_fit": "contain",
                "image_position": "top",
                "hover_image_url": "source-hover.jpg",
                "hover_image_alt": "Source hover",
                "hover_image_position": "bottom",
                "label": "Do not copy",
            }
        }

        merge_option_asset_fields(destination, source_rows, only_if_image_present=False)

        self.assertEqual(
            {field: destination[field] for field in ASSET_IMAGE_FIELDS},
            {field: source_rows["opt_q9i_001"].get(field, "") for field in ASSET_IMAGE_FIELDS},
        )
        self.assertEqual(destination["label"], "Kept")

    def test_merge_option_asset_fields_true_gates_on_source_row_image_url_not_destination(self) -> None:
        destination = {"option_id": "opt_q9i_001", "image_url": "target-only.jpg"}
        source_rows = {
            "opt_q9i_001": {
                "image_url": "",
                "image_alt": "Should not copy",
            }
        }

        merge_option_asset_fields(destination, source_rows, only_if_image_present=True)

        self.assertEqual(destination, {"option_id": "opt_q9i_001", "image_url": "target-only.jpg"})

        source_rows["opt_q9i_001"]["image_url"] = "source.jpg"
        merge_option_asset_fields(destination, source_rows, only_if_image_present=True)

        self.assertEqual(destination["image_url"], "source.jpg")
        self.assertEqual(destination["image_alt"], "Should not copy")

    def test_merge_option_asset_fields_is_noop_without_source_entry(self) -> None:
        destination = {"option_id": "opt_missing_001", "label": "No asset"}

        merge_option_asset_fields(destination, {}, only_if_image_present=False)
        merge_option_asset_fields(destination, {}, only_if_image_present=True)

        self.assertEqual(destination, {"option_id": "opt_missing_001", "label": "No asset"})


if __name__ == "__main__":
    unittest.main()
