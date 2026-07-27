#!/usr/bin/env python3
"""Route-orchestration guards for generate_form."""

from __future__ import annotations

import importlib.util
import json
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = ROOT / "stingray_master.xlsx"
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from corvette_form_generator import inspection, model_generation, source_assembly  # noqa: E402
from corvette_form_generator.model_configs import discover_generation_model_configs  # noqa: E402
from corvette_form_generator.model_generation import (  # noqa: E402
    REQUIRED_RESULT_KEYS,
    ROUTE_ENGINE,
    GenerationOptions,
    generate_model_artifacts,
)
from corvette_form_generator.runtime_contract import REQUIRED_RUNTIME_LIST_FIELDS  # noqa: E402


def generated_contract(result: dict) -> dict:
    return json.loads(Path(result["runtime_contract_json"]).read_text(encoding="utf-8"))


def load_generate_form_cli():
    """Import scripts/generate_form.py as a module so its main() can be driven."""

    spec = importlib.util.spec_from_file_location("generate_form_cli", ROOT / "scripts" / "generate_form.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextmanager
def counted_source_assembly() -> Iterator[list[object]]:
    """Record every config handed to the shared builder, delegating to the real one."""

    calls: list[object] = []
    real = model_generation.assemble_model_source

    def counting(config, **kwargs):
        calls.append(config)
        return real(config, **kwargs)

    with patch.object(model_generation, "assemble_model_source", counting):
        yield calls


def discovered_model_keys() -> list[str]:
    return sorted(discover_generation_model_configs(WORKBOOK, root=ROOT))


@pytest.mark.parametrize("model_key", discovered_model_keys())
def test_every_discovered_model_routes_through_the_shared_source_assembly(model_key: str, tmp_path: Path) -> None:
    """One builder for all of them — asserted per model, not by reading the module's text.

    Parametrized over workbook discovery, so a newly activated model is covered
    the moment it exists rather than when someone remembers to add it here.
    """

    config = discover_generation_model_configs(WORKBOOK, root=tmp_path)[model_key]

    with counted_source_assembly() as calls:
        result = generate_model_artifacts(config)

    assert calls == [config], f"{model_key} did not reach assemble_model_source exactly once"
    assert result["route_engine"] == ROUTE_ENGINE
    assert set(result) == set(REQUIRED_RESULT_KEYS), f"{model_key} reports a different summary shape"
    assert Path(result["runtime_contract_json"]).is_relative_to(tmp_path)


@pytest.mark.parametrize("model_key", discovered_model_keys())
def test_no_model_can_generate_around_the_shared_builder(model_key: str, tmp_path: Path) -> None:
    """Break the one builder and every model must fail.

    This is the executable form of the retired route-table guard: if any model
    kept a private assembly path, disabling the shared one would leave it green.
    """

    config = discover_generation_model_configs(WORKBOOK, root=tmp_path)[model_key]

    with patch.object(model_generation, "assemble_model_source", side_effect=RuntimeError("shared builder disabled")):
        with pytest.raises(RuntimeError, match="shared builder disabled"):
            generate_model_artifacts(config)

    assert not (tmp_path / "form-output").exists(), f"{model_key} wrote an artifact without the shared builder"


@pytest.mark.parametrize("model_key", discovered_model_keys())
def test_the_cli_delegates_generation_to_the_shared_entry_point(model_key: str, tmp_path: Path) -> None:
    """generate_form.py owns argument parsing and discovery, nothing else.

    Parametrized over every model because a legacy branch keyed to one model —
    the shape the retired ``PRODUCTION_MODEL_KEYS`` route had — passes a
    single-model test. Generation is faked here, so the cost is parsing.
    """

    cli = load_generate_form_cli()
    captured: dict[str, object] = {}

    def fake_generate(config, *, options=None):
        captured["config"] = config
        captured["options"] = options
        return {"model_key": config.model_key}

    argv = [
        "generate_form.py",
        "--model",
        model_key,
        "--output-root",
        str(tmp_path),
        "--emit-inspection",
        "--inspection-output",
        str(tmp_path / "review"),
    ]
    with patch.object(cli, "generate_model_artifacts", fake_generate), patch.object(sys, "argv", argv):
        cli.main()

    config = captured["config"]
    options = captured["options"]
    assert config.model_key == model_key
    assert config.output_dir.is_relative_to(tmp_path), "the CLI must honour --output-root"
    assert options.emit_inspection is True
    assert options.inspection_output_dir == tmp_path / "review"


def test_normal_generation_never_builds_the_inspection_report(tmp_path: Path) -> None:
    """Reports are review output, not a dependency of the generation result summary."""

    config = discover_generation_model_configs(WORKBOOK, root=tmp_path)["z06"]

    with patch.object(
        source_assembly,
        "inspect_model_sources",
        side_effect=AssertionError("inspect_model_sources ran during normal generation"),
    ):
        result = generate_model_artifacts(config)

    assert result["inspection_artifacts"] == {}
    assert result["preview_artifacts"] == {}
    assert result["draft_artifacts"] == {}


def test_generation_summary_is_derived_from_the_validated_runtime_contract(tmp_path: Path) -> None:
    """One summary shape for every model, read back off the artifact that was validated."""

    configs = discover_generation_model_configs(WORKBOOK, root=tmp_path)

    for model_key in ("stingray", "z06"):
        # No review payloads on this path — assembly.report and assembly.preview
        # are None — so a summary rebuilt from them would come back short.
        result = generate_model_artifacts(configs[model_key])
        contract = generated_contract(result)

        assert set(result) == set(REQUIRED_RESULT_KEYS)
        assert all(result["counts"][field] > 0 for field in ("choices", "sections", "steps")), result["counts"]
        assert result["status"] == "runtime_active"
        assert result["status"] == contract["dataset"]["status"]
        assert result["dataset_name"] == contract["dataset"]["name"]
        assert result["counts"] == {field: len(contract[field]) for field in REQUIRED_RUNTIME_LIST_FIELDS}
        assert result["validation_errors"] == sum(
            1 for row in contract["validation"] if str(row.get("severity", "")).lower() == "error"
        )
        assert result["validation_warnings"] == sum(
            1 for row in contract["validation"] if str(row.get("severity", "")).lower() == "warning"
        )


@contextmanager
def tracked_workbook_loads() -> Iterator[tuple[list[object], list[object]]]:
    """Record every workbook opened and closed inside ``inspection``."""

    opened: list[object] = []
    closed: list[object] = []
    real_load = inspection.load_workbook

    def tracking_load(*args: object, **kwargs: object) -> object:
        workbook = real_load(*args, **kwargs)
        opened.append(workbook)
        real_close = workbook.close

        def close() -> None:
            closed.append(workbook)
            real_close()

        workbook.close = close
        return workbook

    with patch.object(inspection, "load_workbook", tracking_load):
        yield opened, closed


def test_each_inspection_builder_uses_one_frozen_workbook_snapshot(tmp_path: Path) -> None:
    """Every builder loads the workbook once and closes that handle."""

    config = discover_generation_model_configs(WORKBOOK, root=tmp_path)["z06"]
    preview = inspection.build_contract_preview(config)
    builders = (
        lambda: inspection.inspect_model_sources(config),
        lambda: inspection.build_contract_preview(config),
        lambda: inspection.build_form_data_draft(config, preview=preview),
    )

    for build in builders:
        with tracked_workbook_loads() as (opened, closed):
            build()
        assert len(opened) == 1
        assert closed == opened


def test_workbook_handles_close_when_a_builder_raises(tmp_path: Path) -> None:
    """A failure mid-build must not leak the workbook handle."""

    config = discover_generation_model_configs(WORKBOOK, root=tmp_path)["z06"]
    preview = inspection.build_contract_preview(config)
    failures = (
        ("rows_from_sheet", lambda: inspection.inspect_model_sources(config)),
        ("rows_from_sheet", lambda: inspection.build_contract_preview(config)),
        ("build_model_interiors", lambda: inspection.build_form_data_draft(config, preview=preview)),
    )

    for attribute, build in failures:
        with tracked_workbook_loads() as (opened, closed):
            with patch.object(inspection, attribute, side_effect=RuntimeError("injected")):
                try:
                    build()
                except RuntimeError:
                    pass
                else:
                    raise AssertionError(f"{attribute} failure was swallowed")
        assert len(opened) == 1
        assert closed == opened


def test_requested_review_artifacts_are_still_produced(tmp_path: Path) -> None:
    config = discover_generation_model_configs(WORKBOOK, root=tmp_path)["z06"]

    result = generate_model_artifacts(
        config,
        options=GenerationOptions(emit_inspection=True, inspection_output_dir=tmp_path / "review"),
    )

    for key in ("inspection_artifacts", "preview_artifacts", "draft_artifacts"):
        assert result[key], key
        for path in result[key].values():
            assert Path(path).exists()
