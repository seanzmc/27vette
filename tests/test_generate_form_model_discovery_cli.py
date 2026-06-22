#!/usr/bin/env python3
"""CLI tests for workbook-owned generate_form model discovery."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "bin" / "python"
GENERATE_FORM = ROOT / "scripts" / "generate_form.py"

REQUIRED_STDOUT_KEYS = {
    "model_key",
    "model_label",
    "route_engine",
    "runtime_contract_json",
    "runtime_contract_artifacts",
    "compatibility_artifacts",
    "inspection_artifacts",
    "preview_artifacts",
    "draft_artifacts",
    "counts",
    "validation_errors",
    "notes",
}


def run_generate_form(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(PYTHON), str(GENERATE_FORM), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def assert_common_generation_contract(output: dict, model_key: str, slug: str) -> None:
    assert REQUIRED_STDOUT_KEYS <= set(output)
    assert output["model_key"] == model_key
    assert output["runtime_contract_json"].endswith(f"form-output/runtime/{slug}-runtime-contract.json")
    assert output["runtime_contract_artifacts"]["json"] == output["runtime_contract_json"]
    assert isinstance(output["compatibility_artifacts"], dict)
    assert isinstance(output["inspection_artifacts"], dict)
    assert isinstance(output["preview_artifacts"], dict)
    assert isinstance(output["draft_artifacts"], dict)
    assert isinstance(output["counts"], dict)
    assert output["validation_errors"] == 0


def test_active_models_share_generation_stdout_contract() -> None:
    cases = [
        ("stingray", "stingray", "production"),
        ("grand_sport", "grand-sport", "inspection_draft"),
        ("z06", "z06", "inspection_draft"),
    ]

    for model_key, slug, route_engine in cases:
        result = run_generate_form("--model", model_key)

        assert result.returncode == 0, result.stderr
        output = json.loads(result.stdout)
        assert_common_generation_contract(output, model_key, slug)
        assert output["route_engine"] == route_engine

        if model_key == "stingray":
            assert output["workbook_backup"] is None
            assert output["json"].endswith("form-output/stingray-form-data.json")
            assert output["csv"].endswith("form-output/stingray-form-data.csv")
            assert output["compatibility_artifacts"]["json"] == output["json"]
            assert output["compatibility_artifacts"]["csv"] == output["csv"]
            assert output["inspection_artifacts"] == {}
            assert output["preview_artifacts"] == {}
            assert output["draft_artifacts"] == {}
        else:
            assert output["compatibility_artifacts"] == {}
            assert output["inspection_artifacts"]["json"].endswith("form-output/inspection/" + slug + "-inspection.json")
            assert output["preview_artifacts"]["json"].endswith("contract-preview.json")
            assert output["draft_artifacts"]["json"].endswith("form-data-draft.json")


def test_inactive_scaffold_model_is_rejected_before_generation() -> None:
    zr1_runtime = ROOT / "form-output" / "runtime" / "zr1-runtime-contract.json"
    existed_before = zr1_runtime.exists()

    result = run_generate_form("--model", "zr1")

    assert result.returncode != 0
    assert "Unsupported or inactive model 'zr1'" in result.stderr
    assert "Active generatable models: grand_sport, stingray, z06" in result.stderr
    if not existed_before:
        assert not zr1_runtime.exists()
