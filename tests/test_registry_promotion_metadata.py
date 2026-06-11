#!/usr/bin/env python3
"""Tests for workbook-owned runtime registry promotion metadata."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from corvette_form_generator.registry_promotion import (  # noqa: E402
    MODEL_REGISTRY_PROMOTION_HEADERS,
    build_registry_from_promotions,
    load_registry_promotions,
)


def append_sheet(wb: Workbook, name: str, headers: list[str], rows: list[dict[str, object]] | None = None) -> None:
    ws = wb.create_sheet(name)
    ws.append(headers)
    for row in rows or []:
        ws.append([row.get(header, None) for header in headers])


def workbook_with_promotions(promotion_rows: list[dict[str, object]] | None = None) -> Workbook:
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
        [
            {
                "model_key": "stingray",
                "registry_key": "stingray",
                "model_label": "Stingray",
                "export_slug": "stingray",
                "active": True,
            },
            {
                "model_key": "grand_sport",
                "registry_key": "grandSport",
                "model_label": "Grand Sport",
                "export_slug": "grand-sport",
                "active": True,
            },
            {
                "model_key": "z06",
                "registry_key": "z06",
                "model_label": "Z06",
                "export_slug": "z06",
                "active": False,
            },
        ],
    )
    append_sheet(wb, "model_registry_promotion", MODEL_REGISTRY_PROMOTION_HEADERS, promotion_rows or [])
    return wb


def promoted_stingray_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "model_key": "stingray",
        "registry_key": "stingray",
        "promoted_to_runtime": True,
        "default_model": True,
        "artifact_path": "",
        "artifact_type": "current_generation",
        "legacy_alias": "STINGRAY_FORM_DATA",
        "active": True,
        "display_order": 1,
        "notes": "Current generated Stingray data.",
    }
    row.update(overrides)
    return row


def promoted_grand_sport_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "model_key": "grand_sport",
        "registry_key": "grandSport",
        "promoted_to_runtime": True,
        "default_model": False,
        "artifact_path": "form-output/inspection/grand-sport-runtime-contract.json",
        "artifact_type": "draft_artifact",
        "legacy_alias": "",
        "active": True,
        "display_order": 2,
        "notes": "Grand Sport draft artifact promoted to runtime registry.",
    }
    row.update(overrides)
    return row


class RegistryPromotionMetadataTests(unittest.TestCase):
    def test_header_only_promotion_sheet_returns_no_promotions_for_legacy_fallback(self) -> None:
        wb = workbook_with_promotions([])

        self.assertEqual(load_registry_promotions(wb), [])
        self.assertIsNone(
            build_registry_from_promotions(
                wb,
                current_model_key="stingray",
                current_data={"dataset": {"name": "current"}},
                model_assets={},
                root=ROOT,
            )
        )

    def test_promoted_rows_build_ordered_registry_and_aliases_from_workbook_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_path = root / "form-output" / "inspection" / "grand-sport-runtime-contract.json"
            artifact_path.parent.mkdir(parents=True)
            artifact_path.write_text(
                json.dumps(
                    {
                        "dataset": {
                            "source_sheet": "grandSport_options",
                            "status": "runtime_active",
                        },
                        "choices": [
                            {
                                "choice_id": "gs-choice",
                                "source_detail_raw": "runtime tooltip source detail",
                            }
                        ],
                        "rules": [
                            {
                                "rule_id": "rule-1",
                                "source_id": "opt_sht_001",
                                "source_type": "option",
                                "source_note": "runtime rule note",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            wb = workbook_with_promotions(
                [
                    promoted_grand_sport_row(display_order=2),
                    {**promoted_stingray_row(display_order=1)},
                    {
                        "model_key": "z06",
                        "registry_key": "z06",
                        "promoted_to_runtime": False,
                        "default_model": False,
                        "active": False,
                        "display_order": 3,
                    },
                ]
            )

            registry = build_registry_from_promotions(
                wb,
                current_model_key="stingray",
                current_data={"dataset": {"source_sheet": "stingray_options"}, "choices": []},
                model_assets={"stingray": {"image_url": "stingray.png"}, "grandSport": {"image_url": "gs.png"}},
                root=root,
            )

        assert registry is not None
        self.assertEqual(registry["defaultModelKey"], "stingray")
        self.assertEqual(list(registry["models"].keys()), ["stingray", "grandSport"])
        self.assertEqual(registry["models"]["stingray"]["label"], "Stingray")
        self.assertEqual(registry["models"]["stingray"]["exportSlug"], "stingray")
        self.assertEqual(registry["models"]["stingray"]["image_url"], "stingray.png")
        self.assertEqual(registry["models"]["grandSport"]["label"], "Grand Sport")
        self.assertEqual(registry["models"]["grandSport"]["exportSlug"], "grand-sport")
        self.assertEqual(registry["models"]["grandSport"]["data"]["dataset"]["source_sheet"], "grandSport_options")
        choice = registry["models"]["grandSport"]["data"]["choices"][0]
        self.assertEqual(choice["source_detail_raw"], "runtime tooltip source detail")
        self.assertEqual(registry["legacyAliases"], {"STINGRAY_FORM_DATA": "stingray"})

    def test_promoted_artifact_with_draft_fields_fails_fast(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_path = root / "form-output" / "inspection" / "grand-sport-runtime-contract.json"
            artifact_path.parent.mkdir(parents=True)
            artifact_path.write_text(
                json.dumps(
                    {
                        "draftMetadata": {"inspection": True},
                        "dataset": {"status": "draft_not_runtime_active"},
                        "choices": [{"choice_id": "gs-choice", "source_option_name": "draft only"}],
                    }
                ),
                encoding="utf-8",
            )
            wb = workbook_with_promotions(
                [promoted_grand_sport_row(display_order=2), promoted_stingray_row(display_order=1)]
            )
            with self.assertRaisesRegex(ValueError, "not a clean runtime contract"):
                build_registry_from_promotions(
                    wb,
                    current_model_key="stingray",
                    current_data={"dataset": {"source_sheet": "stingray_options"}, "choices": []},
                    model_assets={},
                    root=root,
                )

    def test_promotions_require_exactly_one_default_model(self) -> None:
        wb = workbook_with_promotions([promoted_stingray_row(default_model=False), promoted_grand_sport_row()])

        with self.assertRaisesRegex(ValueError, "exactly one promoted default model"):
            load_registry_promotions(wb)

    def test_duplicate_promoted_registry_keys_fail_fast(self) -> None:
        wb = workbook_with_promotions(
            [
                promoted_stingray_row(display_order=1),
                promoted_stingray_row(display_order=2, default_model=False),
            ]
        )

        with self.assertRaisesRegex(ValueError, "Duplicate promoted registry_key"):
            load_registry_promotions(wb)

    def test_non_current_promoted_rows_require_artifact_path(self) -> None:
        wb = workbook_with_promotions([promoted_stingray_row(), promoted_grand_sport_row(artifact_path="")])

        with self.assertRaisesRegex(ValueError, "artifact_path"):
            load_registry_promotions(wb)

    def test_promoted_registry_keys_must_match_model_master(self) -> None:
        wb = workbook_with_promotions([promoted_stingray_row(registry_key="wrong")])

        with self.assertRaisesRegex(ValueError, "registry_key"):
            load_registry_promotions(wb)


if __name__ == "__main__":
    unittest.main()
