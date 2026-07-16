from collections import Counter

import pytest

from app.catalog import LIVE_MODELS, MODEL_TABLE_ROLES
from app.central_compiler import compile_central_tables
from app.model_compiler import compile_direct_model_tables
from app.shared_compiler import compile_shared_model_tables
from app.workbook_profile import profile_workbook


@pytest.fixture
def shared(real_workbook):
    profile = profile_workbook(real_workbook)
    central = compile_central_tables(profile, real_workbook)
    direct = compile_direct_model_tables(profile, real_workbook, central)
    return compile_shared_model_tables(profile, real_workbook, central, direct)


def _compile(path):
    profile = profile_workbook(path)
    central = compile_central_tables(profile, path)
    direct = compile_direct_model_tables(profile, path, central)
    return compile_shared_model_tables(profile, path, central, direct)


def test_shared_interiors_are_split_by_registered_scope(shared):
    assert {
        model: len(shared.table(f"{model}_interiors").rows)
        for model in LIVE_MODELS
    } == {"stingray": 130, "grand_sport": 132, "z06": 130}
    assert {
        model: {row.source_sheet for row in shared.table(f"{model}_interiors").rows}
        for model in LIVE_MODELS
    } == {
        "stingray": {"lt_interiors"},
        "grand_sport": {"lt_interiors"},
        "z06": {"LZ_Interiors"},
    }
    assert all(
        row.lineage_role == "shared_source_split"
        for model in LIVE_MODELS
        for row in shared.table(f"{model}_interiors").rows
    )


def test_shared_interior_lineage_preserves_one_source_to_many_destinations(shared):
    interior_id = "1LT_AQ9_HTA"
    rows = [
        next(
            row
            for row in shared.table(f"{model}_interiors").rows
            if row.values["interior_id"] == interior_id
        )
        for model in ("stingray", "grand_sport")
    ]
    assert {(row.source_sheet, row.source_row) for row in rows} == {
        ("lt_interiors", 3)
    }
    assert [row.values["model_key"] for row in rows] == [
        "stingray",
        "grand_sport",
    ]
    assert [row.mapping_parameters["model_key"]["canonical"] for row in rows] == [
        "stingray",
        "grand_sport",
    ]
    assert all(
        row.mapping_parameters["model_key"]["owner_source_sheet"]
        == "model_interior_scope"
        for row in rows
    )


def test_scope_and_components_split_only_by_exact_model_key(shared):
    assert {
        model: len(shared.table(f"{model}_interior_scope").rows)
        for model in LIVE_MODELS
    } == {"stingray": 130, "grand_sport": 132, "z06": 130}
    assert {
        model: len(shared.table(f"{model}_interior_components").rows)
        for model in LIVE_MODELS
    } == {"stingray": 197, "grand_sport": 198, "z06": 197}
    for model in LIVE_MODELS:
        for role in ("interior_scope", "interior_components"):
            table = shared.table(f"{model}_{role}")
            assert all(row.values["model_key"] == model for row in table.rows)


def test_color_override_added_option_is_a_foreign_key(shared):
    table = shared.table("grand_sport_color_overrides")
    row = table.rows[0]
    assert row.values["added_option_id"].startswith("opt_")
    assert "adds_rpo" not in row.values
    assert row.mapping_parameters["added_option_id"] == {
        "source_column": "adds_rpo",
        "original": row.values["added_option_id"],
        "canonical": row.values["added_option_id"],
        "transform": "option_reference",
        "reverse_transform": "restore_original_text_from_lineage",
    }
    assert all(
        row.values["interior_id"]
        in {
            interior.values["interior_id"]
            for interior in shared.table(f"{table.model_key}_interiors").rows
        }
        for row in table.rows
    )


def test_wildcard_option_assets_expand_to_matching_models(shared):
    source_rows = [
        row
        for model in LIVE_MODELS
        for row in shared.table(f"{model}_option_assets").rows
        if row.values["option_id"] == "opt_gba_001"
    ]
    assert {row.values["model_key"] for row in source_rows} == set(LIVE_MODELS)
    assert {(row.source_sheet, row.source_row) for row in source_rows} == {
        ("asset_map", 127)
    }
    assert all(row.lineage_role == "shared_source_split" for row in source_rows)


def test_exact_model_option_asset_overlays_matching_wildcard(
    wildcard_asset_overlay_workbook,
):
    shared = _compile(wildcard_asset_overlay_workbook)
    stingray = next(
        row
        for row in shared.table("stingray_option_assets").rows
        if row.values["option_id"] == "opt_gba_001"
    )
    grand_sport = next(
        row
        for row in shared.table("grand_sport_option_assets").rows
        if row.values["option_id"] == "opt_gba_001"
    )
    assert stingray.values["image_url"].endswith("stingray-gba-overlay.png")
    assert stingray.lineage_role == "direct"
    assert grand_sport.values["image_url"].endswith("imgi_10_gba.png")
    assert grand_sport.lineage_role == "shared_source_split"


def test_context_choice_assets_are_exact_model_rows_and_model_cards_stay_central(
    shared,
):
    for model in LIVE_MODELS:
        rows = shared.table(f"{model}_context_choice_assets").rows
        assert {row.values["context_choice_id"] for row in rows} == {
            "body_style__coupe",
            "body_style__convertible",
        }
        assert all(row.source_sheet == "asset_map" for row in rows)
    assert not [
        row
        for table in shared.tables
        for row in table.rows
        if row.source_sheet == "asset_map"
        and row.values.get("image_alt") in {
            "Corvette Stingray",
            "Corvette Grand Sport",
            "Corvette Z06",
        }
    ]


def test_unsupported_wildcard_context_asset_fails_closed_with_source_evidence(
    unsupported_wildcard_context_asset_workbook,
):
    result = _compile(unsupported_wildcard_context_asset_workbook)
    finding = next(
        finding
        for finding in result.findings
        if finding.code == "wildcard_asset_target_unsupported"
    )
    assert finding.status == "decision_required"
    assert finding.source_sheet == "asset_map"
    assert finding.source_row is not None
    assert finding.source_column == "target_type"
    assert finding.value == "context_choice"


def test_default_and_runtime_rule_rows_use_exact_model_ownership(shared):
    assert {
        model: len(shared.table(f"{model}_default_selection_rules").rows)
        for model in LIVE_MODELS
    } == {"stingray": 4, "grand_sport": 4, "z06": 4}
    assert all(
        row.values["model_key"] == table.model_key
        for table in shared.tables
        if table.role in {"default_selection_rules", "runtime_rule_exceptions"}
        for row in table.rows
    )
    assert all(
        not shared.table(f"{model}_runtime_rule_exceptions").rows
        for model in LIVE_MODELS
    )


def test_completed_model_families_have_all_17_roles(shared):
    assert tuple((table.model_key, table.role) for table in shared.tables) == tuple(
        (model, role) for model in LIVE_MODELS for role in MODEL_TABLE_ROLES
    )


def test_shared_mappings_cover_every_shared_role_and_are_deeply_immutable(shared):
    assert Counter(mapping.destination_table for mapping in shared.mappings) == Counter(
        mapping.destination_table
        for table in shared.tables
        if table.role not in MODEL_TABLE_ROLES[:9]
        for mapping in table.schema_mappings
    )
    row = shared.table("grand_sport_color_overrides").rows[0]
    with pytest.raises(TypeError):
        row.mapping_parameters["added_option_id"]["transform"] = "mutated"

    interior = shared.table("grand_sport_interiors").rows[0]
    assert interior.mapping_parameters["interior_name"] == {
        "source_column": "Interior Name",
        "original": interior.values["interior_name"],
        "canonical": interior.values["interior_name"],
        "transform": "semantic_header_alias",
        "reverse_transform": "restore_source_header",
    }
    active_mapping = next(
        mapping
        for mapping in shared.table("grand_sport_interiors").schema_mappings
        if mapping.source_column == "active_for_stingray"
    )
    assert active_mapping.transform == (
        "legacy_flag_superseded_by_active_model_scope"
    )


def test_unowned_shared_row_requires_decision(unowned_shared_row_workbook):
    result = _compile(unowned_shared_row_workbook)
    findings = [
        finding
        for finding in result.findings
        if finding.status == "decision_required"
        and finding.code == "shared_row_owner_unresolved"
    ]
    assert findings
    assert any(
        finding.source_sheet == "lt_interiors"
        and finding.source_row is not None
        and finding.source_column == "interior_id"
        and finding.value == "int_unowned_test"
        for finding in findings
    )
    assert not any(
        row.values["interior_id"] == "int_unowned_test"
        for table in result.tables
        if table.role == "interiors"
        for row in table.rows
    )
