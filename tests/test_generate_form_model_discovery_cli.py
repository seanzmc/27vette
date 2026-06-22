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

ROUTINE_INSPECTION_FILES = (
    ROOT / "form-output" / "inspection" / "grand-sport-inspection.json",
    ROOT / "form-output" / "inspection" / "grand-sport-inspection.md",
    ROOT / "form-output" / "inspection" / "grand-sport-contract-preview.json",
    ROOT / "form-output" / "inspection" / "grand-sport-contract-preview.md",
    ROOT / "form-output" / "inspection" / "grand-sport-form-data-draft.json",
    ROOT / "form-output" / "inspection" / "grand-sport-form-data-draft.md",
    ROOT / "form-output" / "inspection" / "z06-inspection.json",
    ROOT / "form-output" / "inspection" / "z06-inspection.md",
    ROOT / "form-output" / "inspection" / "z06-contract-preview.json",
    ROOT / "form-output" / "inspection" / "z06-contract-preview.md",
    ROOT / "form-output" / "inspection" / "z06-form-data-draft.json",
    ROOT / "form-output" / "inspection" / "z06-form-data-draft.md",
)


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
        else:
            assert output["compatibility_artifacts"] == {}
        assert output["inspection_artifacts"] == {}
        assert output["preview_artifacts"] == {}
        assert output["draft_artifacts"] == {}


def test_review_mode_emits_inspection_artifacts_to_requested_output(tmp_path: Path) -> None:
    cases = [
        ("grand_sport", "grand-sport"),
        ("z06", "z06"),
    ]

    for model_key, slug in cases:
        review_dir = tmp_path / slug
        result = run_generate_form(
            "--model",
            model_key,
            "--emit-inspection",
            "--inspection-output",
            str(review_dir),
        )

        assert result.returncode == 0, result.stderr
        output = json.loads(result.stdout)
        assert_common_generation_contract(output, model_key, slug)
        assert output["inspection_artifacts"]["json"] == str(review_dir / f"{slug}-inspection.json")
        assert output["inspection_artifacts"]["markdown"] == str(review_dir / f"{slug}-inspection.md")
        assert output["preview_artifacts"]["json"] == str(review_dir / f"{slug}-contract-preview.json")
        assert output["preview_artifacts"]["markdown"] == str(review_dir / f"{slug}-contract-preview.md")
        assert output["draft_artifacts"]["json"] == str(review_dir / f"{slug}-form-data-draft.json")
        assert output["draft_artifacts"]["markdown"] == str(review_dir / f"{slug}-form-data-draft.md")
        for artifact_map in (
            output["inspection_artifacts"],
            output["preview_artifacts"],
            output["draft_artifacts"],
        ):
            for artifact_path in artifact_map.values():
                assert Path(artifact_path).exists(), artifact_path


def test_default_generation_does_not_recreate_routine_inspection_artifacts() -> None:
    for path in ROUTINE_INSPECTION_FILES:
        path.unlink(missing_ok=True)

    for model_key in ("grand_sport", "z06"):
        result = run_generate_form("--model", model_key)
        assert result.returncode == 0, result.stderr

    recreated = [path for path in ROUTINE_INSPECTION_FILES if path.exists()]
    assert recreated == []


def test_inspection_output_requires_emit_inspection() -> None:
    result = run_generate_form("--model", "grand_sport", "--inspection-output", "/tmp/unused-pass6b-output")

    assert result.returncode != 0
    assert "--inspection-output requires --emit-inspection" in result.stderr


def test_inactive_scaffold_model_is_rejected_before_generation() -> None:
    zr1_runtime = ROOT / "form-output" / "runtime" / "zr1-runtime-contract.json"
    existed_before = zr1_runtime.exists()

    result = run_generate_form("--model", "zr1")

    assert result.returncode != 0
    assert "Unsupported or inactive model 'zr1'" in result.stderr
    assert "Active generatable models: grand_sport, stingray, z06" in result.stderr
    if not existed_before:
        assert not zr1_runtime.exists()
