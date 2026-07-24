#!/usr/bin/env python3
"""Isolated executable gate for workbook-discovered model generation."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "bin" / "python"
GENERATE_FORM = ROOT / "scripts" / "generate_form.py"
WORKBOOK = ROOT / "stingray_master.xlsx"
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from corvette_form_generator.model_configs import discover_generation_model_configs  # noqa: E402

EXPECTED_MODELS = {"stingray", "grand_sport", "grand_sport_x", "z06", "zr1", "zr1x"}
KNOWN_BLOCKERS = {"z06": "StaleDerivationAllowlistError"}

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


def protected_hashes() -> dict[Path, str]:
    paths = [WORKBOOK, ROOT / "form-app" / "data.js"]
    paths.extend(path for path in (ROOT / "form-output").rglob("*") if path.is_file())
    return {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def test_cli_executes_every_discovered_model_under_isolated_root(tmp_path: Path) -> None:
    workbook_snapshot = tmp_path / "stingray_master.snapshot.xlsx"
    candidate_root = tmp_path / "candidate"
    shutil.copy2(WORKBOOK, workbook_snapshot)
    before = protected_hashes()
    observed: set[str] = set()
    configs = discover_generation_model_configs(workbook_snapshot, root=candidate_root)
    assert set(configs) == EXPECTED_MODELS

    for model_key in sorted(configs):
        result = run_generate_form(
            "--model",
            model_key,
            "--workbook",
            str(workbook_snapshot),
            "--output-root",
            str(candidate_root),
        )
        observed.add(model_key)

        if model_key in KNOWN_BLOCKERS:
            assert result.returncode != 0
            assert KNOWN_BLOCKERS[model_key] in result.stderr
            expected_runtime = candidate_root / "form-output" / "runtime" / "z06-runtime-contract.json"
            assert not expected_runtime.exists()
            continue

        assert result.returncode == 0, result.stderr
        output = json.loads(result.stdout)
        assert REQUIRED_STDOUT_KEYS <= set(output)
        assert output["model_key"] == model_key
        assert output["validation_errors"] == 0
        runtime_path = Path(output["runtime_contract_json"])
        assert runtime_path.is_relative_to(candidate_root)
        assert runtime_path.exists()
        runtime_contract = json.loads(runtime_path.read_text(encoding="utf-8"))
        assert runtime_contract["dataset"]["status"] == "runtime_active"
        assert runtime_contract["validation"] == [
            row for row in runtime_contract["validation"] if str(row.get("severity", "")).lower() != "error"
        ]

    assert observed == EXPECTED_MODELS
    assert protected_hashes() == before


def test_inspection_output_requires_emit_inspection(tmp_path: Path) -> None:
    workbook_snapshot = tmp_path / "stingray_master.snapshot.xlsx"
    shutil.copy2(WORKBOOK, workbook_snapshot)
    result = run_generate_form(
        "--model",
        "grand_sport",
        "--workbook",
        str(workbook_snapshot),
        "--output-root",
        str(tmp_path / "candidate"),
        "--inspection-output",
        str(tmp_path / "inspection"),
    )

    assert result.returncode != 0
    assert "--inspection-output requires --emit-inspection" in result.stderr
