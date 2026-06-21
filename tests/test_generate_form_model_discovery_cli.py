#!/usr/bin/env python3
"""CLI tests for workbook-owned generate_form model discovery."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "bin" / "python"
GENERATE_FORM = ROOT / "scripts" / "generate_form.py"


def run_generate_form(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(PYTHON), str(GENERATE_FORM), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_stingray_model_uses_production_generation_path() -> None:
    result = run_generate_form("--model", "stingray")

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["workbook_backup"] is None
    assert output["json"].endswith("form-output/stingray-form-data.json")
    assert output["runtime_contract_json"].endswith("form-output/runtime/stingray-runtime-contract.json")
    assert "inspection_artifacts" not in output
    assert output["validation_errors"] == 0


def test_inactive_scaffold_model_is_rejected_before_generation() -> None:
    zr1_runtime = ROOT / "form-output" / "runtime" / "zr1-runtime-contract.json"
    existed_before = zr1_runtime.exists()

    result = run_generate_form("--model", "zr1")

    assert result.returncode != 0
    assert "Unsupported or inactive model 'zr1'" in result.stderr
    assert "Active generatable models: grand_sport, stingray, z06" in result.stderr
    if not existed_before:
        assert not zr1_runtime.exists()
