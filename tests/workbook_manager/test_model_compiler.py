from pathlib import Path

import pytest
from openpyxl import load_workbook

from app.catalog import LIVE_MODELS, physical_table
from app.central_compiler import compile_central_tables
from app.compile_types import DecisionRequired
from app.model_compiler import compile_direct_model_tables
from app.workbook_profile import profile_workbook


DIRECT_ROLES = (
    "options",
    "option_availability",
    "rule_mapping",
    "price_rules",
    "rule_groups",
    "rule_group_members",
    "exclusive_groups",
    "exclusive_group_members",
    "variant_overrides",
)


@pytest.fixture
def compiled_central(real_workbook):
    profile = profile_workbook(real_workbook)
    return compile_central_tables(profile, real_workbook)


@pytest.fixture
def compiled_models(real_workbook, compiled_central):
    profile = profile_workbook(real_workbook)
    return compile_direct_model_tables(profile, real_workbook, compiled_central)


def test_model_collections_have_identical_direct_roles(compiled_models):
    assert tuple((table.model_key, table.role) for table in compiled_models) == tuple(
        (model, role) for model in LIVE_MODELS for role in DIRECT_ROLES
    )
    assert all(
        table.name == physical_table(table.model_key, table.role)
        for table in compiled_models
    )


def test_options_and_availability_reconcile_real_workbook(compiled_models):
    by_name = {table.name: table for table in compiled_models}
    assert {
        model: len(by_name[f"{model}_options"].rows) for model in LIVE_MODELS
    } == {"stingray": 242, "grand_sport": 241, "z06": 244}
    assert {
        model: len(by_name[f"{model}_option_availability"].rows)
        for model in LIVE_MODELS
    } == {"stingray": 1452, "grand_sport": 1446, "z06": 1464}
    assert all(
        row.values["model_key"] == table.model_key
        for table in compiled_models
        for row in table.rows
    )


def test_direct_rows_preserve_registered_source_and_workbook_row(compiled_models):
    table = next(table for table in compiled_models if table.name == "grand_sport_options")
    first = table.rows[0]
    assert first.source_sheet == "grandSport_options"
    assert first.source_row == 2
    assert first.values["option_id"] == "opt_uvb_001"
    assert first.lineage_role == "normalized"
    assert first.mapping_parameters["price"] == {
        "original": None,
        "transform": "blank_to_zero",
        "reverse_transform": "zero_to_blank",
    }


def test_polymorphic_sources_are_typed_by_exact_membership(compiled_models):
    by_name = {table.name: table for table in compiled_models}
    for model in LIVE_MODELS:
        rules = by_name[f"{model}_rule_mapping"].rows
        prices = by_name[f"{model}_price_rules"].rows
        assert all(
            (row.values["source_option_id"] is None)
            != (row.values["source_interior_id"] is None)
            for row in rules
        )
        assert all(
            (row.values["condition_option_id"] is None)
            != (row.values["condition_interior_id"] is None)
            for row in prices
        )


def test_aliases_and_scope_normalization_retain_reversible_evidence(compiled_models):
    by_name = {table.name: table for table in compiled_models}
    rule = next(
        row
        for row in by_name["stingray_rule_mapping"].rows
        if row.values["source_interior_id"] is not None
    )
    assert rule.mapping_parameters["source_interior_id"] == {
        "source_column": "source_id",
        "transform": "typed_entity_reference",
        "reverse_transform": "coalesce_typed_entity_reference",
    }
    assert rule.mapping_parameters["target_option_id"] == {
        "source_column": "target_id",
        "transform": "option_reference",
        "reverse_transform": "identity",
    }

    unrestricted = next(
        row
        for row in by_name["z06_price_rules"].rows
        if row.mapping_parameters.get("body_style_scope", {}).get("original") == "*"
    )
    assert unrestricted.values["body_style_scope"] is None
    assert unrestricted.mapping_parameters["body_style_scope"] == {
        "original": "*",
        "transform": "unrestricted_to_null",
        "reverse_transform": "null_to_wildcard",
    }
    restricted = next(
        row
        for row in by_name["z06_price_rules"].rows
        if row.values["trim_level_scope"] == "1lz"
    )
    assert restricted.mapping_parameters["trim_level_scope"] == {
        "original": "1LZ",
        "transform": "lowercase",
        "reverse_transform": "uppercase",
    }


def _copy_with_changed_cell(
    source: Path,
    destination: Path,
    sheet_name: str,
    column: str,
    value: object,
) -> tuple[Path, int]:
    workbook = load_workbook(source)
    sheet = workbook[sheet_name]
    headers = {cell.value: cell.column for cell in sheet[1]}
    sheet.cell(2, headers[column], value)
    workbook.save(destination)
    workbook.close()
    return destination, 2


@pytest.mark.parametrize(
    ("sheet", "column", "value", "code"),
    (
        ("stingray_ovs", "option_id", "missing_option", "option_reference_missing"),
        ("rule_mapping", "source_id", "missing_source", "entity_reference_ambiguous_or_missing"),
        ("price_rules", "target_option_id", "missing_target", "option_reference_missing"),
        ("rule_groups", "body_style_scope", "sedan", "scope_reference_missing"),
    ),
)
def test_unresolved_direct_relationships_fail_closed_with_source_evidence(
    tmp_path, real_workbook, sheet, column, value, code
):
    path, source_row = _copy_with_changed_cell(
        real_workbook, tmp_path / f"broken-{sheet}.xlsx", sheet, column, value
    )
    profile = profile_workbook(path)
    central = compile_central_tables(profile, path)
    with pytest.raises(DecisionRequired) as error:
        compile_direct_model_tables(profile, path, central)
    assert error.value.code == code
    assert error.value.source_sheet == sheet
    assert error.value.source_row == source_row
    assert error.value.source_column == column
    assert error.value.value == value
