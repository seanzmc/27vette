from pathlib import Path

import pytest
from openpyxl import load_workbook

from app.central_compiler import compile_central_tables
from app.compile_types import DecisionRequired
from app.workbook_profile import profile_workbook


@pytest.fixture
def compiled_central(real_workbook):
    profile = profile_workbook(real_workbook)
    return compile_central_tables(profile, real_workbook)


def test_variants_link_models_body_styles_and_trims(compiled_central):
    tables = {table.name: table for table in compiled_central}
    assert {row.values["body_style"] for row in tables["variants"].rows} == {
        "coupe",
        "convertible",
    }
    assert {row.values["trim_level"] for row in tables["variants"].rows} <= {
        row.values["trim_level"] for row in tables["trim_levels"].rows
    }
    assert {row.values["model_key"] for row in tables["model_variants"].rows} >= {
        "stingray",
        "grand_sport",
        "z06",
    }


def test_runtime_structure_has_one_model_aware_route(compiled_central):
    tables = {table.name: table for table in compiled_central}
    step_keys = {
        (row.values["model_key"], row.values["step_key"])
        for row in tables["runtime_steps"].rows
    }
    assert ("stingray", "body_style") in step_keys
    assert ("grand_sport", "body_style") in step_keys
    assert ("z06", "body_style") in step_keys


def test_compiles_every_central_table_with_declared_primary_keys(compiled_central):
    assert [(table.name, table.primary_key) for table in compiled_central] == [
        ("models", ("model_key",)),
        ("model_registry_promotion", ("model_key",)),
        ("body_styles", ("body_style",)),
        ("trim_levels", ("trim_level",)),
        ("variants", ("variant_id",)),
        ("model_variants", ("model_key", "variant_id")),
        ("sections", ("section_id",)),
        ("section_presentation", ("model_key", "section_id")),
        ("runtime_route_keys", ("model_key", "route_key")),
        ("runtime_steps", ("model_key", "step_key")),
        (
            "runtime_context_sections",
            ("model_key", "context_type", "section_id"),
        ),
        ("runtime_context_choices", ("model_key", "context_type", "value")),
        ("runtime_summary_sections", ("model_key", "section_key")),
        (
            "runtime_step_summary_map",
            ("model_key", "step_key", "section_key"),
        ),
        ("model_assets", ("model_key",)),
        ("price_ref", ("option_type", "trim_level", "code")),
        ("rule_phrase_map", ("phrase",)),
    ]
    for table in compiled_central:
        assert table.rows
        assert len(
            {
                tuple(row.values[column] for column in table.primary_key)
                for row in table.rows
            }
        ) == len(table.rows)


def test_runtime_route_keys_distinguish_visible_and_hidden_routes(
    compiled_central,
):
    tables = {table.name: table for table in compiled_central}
    routes = {
        (row.values["model_key"], row.values["route_key"]): row.values[
            "route_kind"
        ]
        for row in tables["runtime_route_keys"].rows
    }
    assert routes[("stingray", "body_style")] == "visible_step"
    assert routes[("grand_sport", "body_style")] == "visible_step"
    assert routes[("z06", "body_style")] == "visible_step"
    assert routes[("z06", "standard_equipment")] == "hidden_summary_bucket"
    assert ("z06", "standard_equipment") not in {
        (row.values["model_key"], row.values["step_key"])
        for row in tables["runtime_steps"].rows
    }


def test_normalization_preserves_original_values_in_lineage_evidence(
    compiled_central,
):
    tables = {table.name: table for table in compiled_central}
    choice = next(
        row
        for row in tables["runtime_context_choices"].rows
        if row.values["model_key"] == "stingray" and row.values["value"] == "1lt"
    )
    assert choice.source_sheet == "context_choice_copy"
    assert choice.source_row == 2
    assert choice.lineage_role == "shared_source_split"
    assert choice.mapping_parameters["value"] == {
        "original": "1LT",
        "transform": "lowercase",
    }
    assert choice.mapping_parameters["body_style"] == {
        "original": "*",
        "transform": "unrestricted_to_null",
    }

    unrestricted_price = next(
        row
        for row in tables["price_ref"].rows
        if row.values["option_type"] == "r6x" and row.values["code"] == "R6X"
    )
    assert unrestricted_price.values["trim_level"] is None


def test_context_sections_stay_distinct_and_share_runtime_step_keys(
    compiled_central,
):
    tables = {table.name: table for table in compiled_central}
    option_section_ids = {
        row.values["section_id"] for row in tables["sections"].rows
    }
    runtime_step_keys = {
        (row.values["model_key"], row.values["step_key"])
        for row in tables["runtime_steps"].rows
    }
    context_rows = tables["runtime_context_sections"].rows
    assert not {
        row.values["section_id"] for row in context_rows
    } & option_section_ids
    assert all(
        (row.values["model_key"], row.values["step_key"]) in runtime_step_keys
        for row in context_rows
    )


def test_only_active_live_rows_are_compiled(compiled_central):
    tables = {table.name: table for table in compiled_central}
    assert {row.values["model_key"] for row in tables["models"].rows} == {
        "stingray",
        "grand_sport",
        "z06",
    }
    assert len(tables["variants"].rows) == 18
    assert len(tables["model_variants"].rows) == 18
    assert len(tables["model_assets"].rows) == 3


def _copy_with_broken_model_variant(
    source: Path, destination: Path
) -> Path:
    workbook = load_workbook(source)
    sheet = workbook["model_variants"]
    sheet.cell(row=2, column=2, value="variant_missing_from_master")
    workbook.save(destination)
    workbook.close()
    return destination


def test_broken_central_reference_hard_stops_as_decision_required(
    tmp_path, real_workbook
):
    path = _copy_with_broken_model_variant(
        real_workbook, tmp_path / "broken-central-reference.xlsx"
    )
    profile = profile_workbook(path)
    with pytest.raises(DecisionRequired) as error:
        compile_central_tables(profile, path)
    assert error.value.code == "model_variant_reference_missing"
    assert error.value.source_sheet == "model_variants"
    assert error.value.source_row == 2


def test_summary_only_route_does_not_require_an_option_section_key(
    tmp_path, real_workbook
):
    path = tmp_path / "summary-only-route.xlsx"
    workbook = load_workbook(real_workbook)
    workbook["step_order_summary_map"].append(
        (
            "grand_sport",
            "hidden_summary_test",
            "pricing_summary",
            True,
            "Test-only hidden summary route.",
        )
    )
    workbook.save(path)
    workbook.close()

    tables = {
        table.name: table
        for table in compile_central_tables(profile_workbook(path), path)
    }
    route = next(
        row
        for row in tables["runtime_route_keys"].rows
        if row.values["model_key"] == "grand_sport"
        and row.values["route_key"] == "hidden_summary_test"
    )
    assert route.values["route_kind"] == "hidden_summary_bucket"


def test_context_section_can_reference_the_shared_route_domain(
    tmp_path, real_workbook
):
    path = tmp_path / "context-hidden-route.xlsx"
    workbook = load_workbook(real_workbook)
    sheet = workbook["context_section_master"]
    headers = {cell.value: cell.column for cell in sheet[1]}
    for row_number in range(2, sheet.max_row + 1):
        if (
            sheet.cell(row_number, headers["model_key"]).value == "z06"
            and sheet.cell(row_number, headers["context_type"]).value
            == "body_style"
        ):
            sheet.cell(row_number, headers["step_key"]).value = (
                "standard_equipment"
            )
            break
    else:
        raise AssertionError("missing z06 body_style context row")
    workbook.save(path)
    workbook.close()

    tables = {
        table.name: table
        for table in compile_central_tables(profile_workbook(path), path)
    }
    row = next(
        row
        for row in tables["runtime_context_sections"].rows
        if row.values["model_key"] == "z06"
        and row.values["context_type"] == "body_style"
    )
    assert row.values["step_key"] == "standard_equipment"


def test_derived_route_lineage_preserves_pre_normalized_source_value(
    tmp_path, real_workbook
):
    path = tmp_path / "normalized-route.xlsx"
    workbook = load_workbook(real_workbook)
    sheet = workbook["runtime_steps"]
    headers = {cell.value: cell.column for cell in sheet[1]}
    for row_number in range(2, sheet.max_row + 1):
        if (
            sheet.cell(row_number, headers["model_key"]).value == "stingray"
            and sheet.cell(row_number, headers["step_key"]).value
            == "body_style"
        ):
            sheet.cell(row_number, headers["step_key"]).value = "BODY_STYLE"
            break
    else:
        raise AssertionError("missing stingray body_style runtime step")
    workbook.save(path)
    workbook.close()

    tables = {
        table.name: table
        for table in compile_central_tables(profile_workbook(path), path)
    }
    route = next(
        row
        for row in tables["runtime_route_keys"].rows
        if row.values["model_key"] == "stingray"
        and row.values["route_key"] == "body_style"
    )
    assert route.mapping_parameters["route_key"] == {
        "original": "BODY_STYLE",
        "transform": "lowercase_then_derived_from_runtime_steps.step_key",
    }
