"""Contract tests for catalog-driven CI validation selection."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_layered_validation.py"
CATALOG = REPO_ROOT / "tests" / "validation_catalog.json"


def _catalog(tmp_path: Path) -> Path:
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    data["gates"] = [
        {
            "id": "layer.zero",
            "layer": 0,
            "command": f'{sys.executable} -c "print(\'zero\')"',
            "changed_surfaces": ["validation_infrastructure"],
            "serial_group": None,
        },
        {
            "id": "layer.one",
            "layer": 1,
            "command": f'{sys.executable} -c "print(\'one\')"',
            "changed_surfaces": ["workbook"],
            "serial_group": "protected_artifacts",
        },
        {
            "id": "manager.parity",
            "layer": 3,
            "command": f'{sys.executable} -c "print(\'manager\')"',
            "changed_surfaces": ["workbook_manager"],
            "serial_group": "workbook_manager",
        },
        {
            "id": "manager.peer",
            "layer": 2,
            "command": f'{sys.executable} -c "print(\'peer\')"',
            "changed_surfaces": ["workbook_manager"],
            "serial_group": "workbook_manager",
        },
        {
            "id": "asset.focused",
            "layer": 2,
            "command": f'{sys.executable} -c "print(\'asset\')"',
            "changed_surfaces": ["asset_map"],
            "serial_group": None,
        },
    ]
    data["ci"] = {
        "always_gate_ids": ["layer.zero", "layer.one"],
        "path_surfaces": [
            {"prefix": "workbook-manager/", "surfaces": ["workbook_manager"]},
            {"prefix": "docs/", "surfaces": ["docs"]},
        ],
        "fallback_surfaces": ["asset_map"],
    }
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _run(tmp_path: Path, *changed: str) -> dict:
    report = tmp_path / "report.json"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--catalog",
            str(_catalog(tmp_path)),
            "--report",
            str(report),
            *(part for path in changed for part in ("--changed-file", path)),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(report.read_text(encoding="utf-8"))


def test_always_layers_and_changed_surface_are_selected(tmp_path):
    report = _run(tmp_path, "workbook-manager/backend/app/main.py")
    assert report["selected_surfaces"] == ["workbook_manager"]
    assert report["selected_gate_ids"] == [
        "layer.zero",
        "layer.one",
        "manager.parity",
        "manager.peer",
    ]
    assert report["ok"] is True
    assert all(stage["duration_seconds"] >= 0 for stage in report["stages"])


def test_shared_serial_group_is_co_selected(tmp_path):
    report = _run(tmp_path, "workbook-manager/frontend/src/App.jsx")
    assert {"manager.parity", "manager.peer"} <= set(report["selected_gate_ids"])


def test_unknown_path_uses_conservative_fallback(tmp_path):
    report = _run(tmp_path, "unclassified/new-surface.txt")
    assert report["selection_fallback"] is True
    assert "asset.focused" in report["selected_gate_ids"]


def test_docs_only_change_skips_changed_surface_gates(tmp_path):
    report = _run(tmp_path, "docs/operator-note.md")
    assert report["selected_gate_ids"] == ["layer.zero", "layer.one"]