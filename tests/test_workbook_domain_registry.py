#!/usr/bin/env python3
"""Tests for the shared workbook domain registry (workbook_domain.registry)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import pytest  # noqa: E402

from corvette_form_generator import editor_ops  # noqa: E402
from corvette_form_generator.workbook_domain.registry import (  # noqa: E402
    EDITOR_SHEET_META,
    GLOBAL_SHEET_FAMILIES,
    READONLY_SHEET_META,
    REGISTRY_PROMOTION_ARTIFACT_TYPES,
    SOURCE_ROLE_FAMILIES,
    WRITABLE_COLUMNS,
    family_spec,
    models_for_write_targets,
    registered_sheet_families,
)


def test_editor_ops_uses_shared_registry_objects():
    assert editor_ops.EDITOR_SHEET_META is EDITOR_SHEET_META
    assert editor_ops.GLOBAL_SHEET_FAMILIES is GLOBAL_SHEET_FAMILIES
    assert editor_ops.SOURCE_ROLE_FAMILIES is SOURCE_ROLE_FAMILIES


def test_registered_sheet_families_uses_live_workbook_rows():
    extract = {
        "sheets": {
            "model_workbook_sources": {
                "rows": [{
                    "model_key": "demo",
                    "source_role": "source_option_sheet",
                    "sheet_name": "demo_options",
                    "active": True,
                }]
            }
        }
    }
    assert registered_sheet_families(extract)["demo_options"] == "options"
    assert family_spec("options")["key"] == ("option_id",)


def test_registry_owns_promotion_artifact_type_domain():
    # Pass 3 requirement 7 narrowed this to one value. `current_generation` and
    # `draft_artifact` published something other than a strictly validated runtime
    # contract; breaking this assertion means one of them came back.
    assert REGISTRY_PROMOTION_ARTIFACT_TYPES == ("runtime_contract",)
    promotion = family_spec("model_registry_promotion")
    assert promotion["enums"]["artifact_type"] == REGISTRY_PROMOTION_ARTIFACT_TYPES


def test_registry_owns_readonly_section_master_contract():
    sections = READONLY_SHEET_META["sections"]
    assert sections["sheet"] == "section_master"
    assert sections["key"] == ("section_id",)
    assert sections["columns"] == (
        "section_id",
        "section_name",
        "selection_mode",
        "is_required",
        "display_order",
        "standard_behavior",
        "step_key",
    )
    assert sections["types"]["is_required"] == "bool"
    assert sections["types"]["display_order"] == "int"
    assert "sections" not in EDITOR_SHEET_META


def _sources_extract() -> dict:
    return {
        "sheets": {
            "model_workbook_sources": {
                "rows": [
                    {
                        "model_key": "z06",
                        "source_role": "source_option_sheet",
                        "sheet_name": "z06_options",
                        "active": True,
                    },
                    {
                        "model_key": "stingray",
                        "source_role": "source_option_sheet",
                        "sheet_name": "stingray_options",
                        "active": True,
                    },
                ]
            },
            "model_master": {
                "rows": [
                    {"model_key": "z06", "active": True},
                    {"model_key": "stingray", "active": True},
                    {"model_key": "zr1", "active": True},
                ]
            },
        }
    }


def test_models_for_write_targets_maps_model_source_sheet_to_one_model():
    touched = models_for_write_targets(_sources_extract(), [{"sheet": "z06_options"}])
    assert touched == {"z06"}


def test_models_for_write_targets_returns_all_models_for_a_global_family_target():
    # asset_map is a global family: one row can change any model's output, so the
    # touched set is deliberately widened rather than narrowed to its model_key.
    touched = models_for_write_targets(
        _sources_extract(), [{"sheet": "asset_map", "row": {"model_key": "z06"}}]
    )
    assert touched == {"z06", "stingray", "zr1"}


def test_models_for_write_targets_never_narrows_when_a_global_target_is_added():
    """Adding a target can only widen the touched set, never shrink it."""

    extract = _sources_extract()
    # A model registered as an active source owner but not active in model_master:
    # the scaffold state the editor explicitly supports.
    extract["sheets"]["model_workbook_sources"]["rows"].append(
        {
            "model_key": "grand_sport_x",
            "source_role": "source_option_sheet",
            "sheet_name": "grand_sport_x_options",
            "active": True,
        }
    )

    source_only = models_for_write_targets(extract, [{"sheet": "grand_sport_x_options"}])
    with_global = models_for_write_targets(
        extract, [{"sheet": "grand_sport_x_options"}, {"sheet": "asset_map"}]
    )

    assert source_only == {"grand_sport_x"}
    assert source_only <= with_global


def test_models_for_write_targets_rejects_an_unregistered_sheet():
    with pytest.raises(KeyError):
        models_for_write_targets(_sources_extract(), [{"sheet": "not_a_registered_sheet"}])


def test_writable_columns_cover_every_registered_family():
    assert set(WRITABLE_COLUMNS) == set(EDITOR_SHEET_META)
    for family, meta in EDITOR_SHEET_META.items():
        assert meta["columns"] == WRITABLE_COLUMNS[family]
