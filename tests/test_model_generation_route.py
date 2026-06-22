#!/usr/bin/env python3
"""Route-orchestration guards for generate_form."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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


def test_model_generation_module_names_temporary_route_split_and_optional_inspection_output() -> None:
    module_path = ROOT / "scripts" / "corvette_form_generator" / "model_generation.py"
    assert module_path.exists()
    source = module_path.read_text()

    assert "class GenerationOptions" in source
    assert "emit_inspection: bool = False" in source
    assert "inspection_output_dir" in source
    assert "def generate_model_artifacts" in source
    assert "TEMPORARY_ROUTE_ENGINES" in source
    assert '"stingray": "production"' in source
    assert "inspection_draft" in source
    assert "runtime_contract_json" in source
    assert "compatibility_artifacts" in source
    assert "inspection_artifacts" in source
    assert "draft_artifacts" in source
    assert "if options.emit_inspection" in source
