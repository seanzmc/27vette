#!/usr/bin/env python3
"""Route-orchestration guards for generate_form."""

from __future__ import annotations

import json
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = ROOT / "stingray_master.xlsx"
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from corvette_form_generator import inspection, source_assembly  # noqa: E402
from corvette_form_generator.model_configs import discover_generation_model_configs  # noqa: E402
from corvette_form_generator.model_generation import (  # noqa: E402
    REQUIRED_RESULT_KEYS,
    GenerationOptions,
    generate_model_artifacts,
)
from corvette_form_generator.runtime_contract import REQUIRED_RUNTIME_LIST_FIELDS  # noqa: E402


def generated_contract(result: dict) -> dict:
    return json.loads(Path(result["runtime_contract_json"]).read_text(encoding="utf-8"))


def test_generate_form_delegates_to_shared_model_generation_module() -> None:
    source = (ROOT / "scripts" / "generate_form.py").read_text()

    assert "from corvette_form_generator.model_generation import GenerationOptions, generate_model_artifacts" in source
    assert "generate_model_artifacts(base_config, options=options)" in source
    assert "--emit-inspection" in source
    assert "--inspection-output" in source
    assert "def run_production" not in source
    assert "def run_draft" not in source
    assert "PRODUCTION_MODEL_KEYS" not in source
    assert "from corvette_form_generator import production" not in source
    assert "from corvette_form_generator.inspection import" not in source


def test_model_generation_uses_shared_source_assembly_without_temporary_route_split() -> None:
    module_path = ROOT / "scripts" / "corvette_form_generator" / "model_generation.py"
    source_assembly_path = ROOT / "scripts" / "corvette_form_generator" / "source_assembly.py"
    assert module_path.exists()
    assert source_assembly_path.exists()

    source = module_path.read_text()
    retired_route_table = "TEMPORARY" + "_ROUTE_ENGINES"
    retired_route_value = "inspection" + "_draft"

    assert "class GenerationOptions" in source
    assert "emit_inspection: bool = False" in source
    assert "inspection_output_dir" in source
    assert "def generate_model_artifacts" in source
    assert "assemble_model_source" in source
    assert retired_route_table not in source
    assert retired_route_value not in source
    assert "source_assembly" in source
    assert "runtime_contract_json" in source
    assert "compatibility_artifacts" in source
    assert "inspection_artifacts" in source
    assert "draft_artifacts" in source
    # The emit-inspection gate itself is asserted behaviorally below, not by source string.
    assert "options.emit_inspection" in source
    # The result summary must not be reconstructed from review payloads.
    assert "assembly.report[" not in source
    assert "assembly.preview[" not in source


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
        result = generate_model_artifacts(configs[model_key])
        contract = generated_contract(result)

        assert set(REQUIRED_RESULT_KEYS) <= set(result)
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
