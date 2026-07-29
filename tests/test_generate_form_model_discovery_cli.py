#!/usr/bin/env python3
"""CLI-argument behavior for ``scripts/generate_form.py``.

The six-model generation gate moved to ``tests/test_all_model_runtime_generation.py``
(spec Pass 2 requirement 10: one executable harness, not two). What stays here is
the argument handling that harness does not exercise — the flags an operator can
get wrong, proven against a workbook snapshot rather than the canonical file.
"""

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


def test_output_root_confines_every_written_path(tmp_path: Path) -> None:
    """``--output-root`` must redirect the whole write set, not only the contract."""

    workbook_snapshot = tmp_path / "stingray_master.snapshot.xlsx"
    candidate_root = tmp_path / "candidate"
    shutil.copy2(WORKBOOK, workbook_snapshot)
    before = protected_hashes()

    result = run_generate_form(
        "--model",
        "stingray",
        "--workbook",
        str(workbook_snapshot),
        "--output-root",
        str(candidate_root),
    )

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    written = [Path(output["runtime_contract_json"])]
    written.extend(Path(value) for value in output["runtime_contract_artifacts"].values())
    escaped = [path for path in written if not path.is_relative_to(candidate_root)]

    assert escaped == [], f"paths written outside --output-root: {escaped}"
    assert protected_hashes() == before


def test_unknown_model_fails_instead_of_generating(tmp_path: Path) -> None:
    workbook_snapshot = tmp_path / "stingray_master.snapshot.xlsx"
    shutil.copy2(WORKBOOK, workbook_snapshot)

    result = run_generate_form(
        "--model",
        "corvette_zora",
        "--workbook",
        str(workbook_snapshot),
        "--output-root",
        str(tmp_path / "candidate"),
    )

    assert result.returncode != 0
    assert "corvette_zora" in result.stderr


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
