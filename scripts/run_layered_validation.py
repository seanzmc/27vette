#!/usr/bin/env python3
"""Select and run cataloged validation gates for CI."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = REPO_ROOT / "tests" / "validation_catalog.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--changed-file", action="append", default=[])
    return parser.parse_args()


def surfaces_for_paths(catalog: dict, paths: list[str]) -> tuple[set[str], list[str]]:
    surfaces: set[str] = set()
    unmatched: list[str] = []
    mappings = catalog["ci"]["path_surfaces"]
    for path in paths:
        matched = False
        for mapping in mappings:
            if path.startswith(mapping["prefix"]):
                surfaces.update(mapping["surfaces"])
                matched = True
        if not matched:
            unmatched.append(path)
    return surfaces, unmatched


def selected_gates(catalog: dict, paths: list[str]) -> tuple[list[dict], set[str], bool]:
    by_id = {gate["id"]: gate for gate in catalog["gates"]}
    surfaces, unmatched = surfaces_for_paths(catalog, paths)
    fallback = bool(unmatched)
    if fallback:
        surfaces.update(catalog["ci"]["fallback_surfaces"])

    selected = set(catalog["ci"]["always_gate_ids"])
    selected.update(
        gate["id"]
        for gate in catalog["gates"]
        if gate["layer"] in (2, 3) and surfaces.intersection(gate["changed_surfaces"])
    )

    shared_groups = {
        by_id[gate_id]["serial_group"]
        for gate_id in selected
        if by_id[gate_id].get("serial_group")
        and catalog["serial_groups"][by_id[gate_id]["serial_group"]].get(
            "standalone_selection"
        )
        == "select_entire_group"
    }
    selected.update(
        gate["id"]
        for gate in catalog["gates"]
        if gate.get("serial_group") in shared_groups
    )
    return [gate for gate in catalog["gates"] if gate["id"] in selected], surfaces, fallback


def main() -> int:
    args = parse_args()
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    gates, surfaces, fallback = selected_gates(catalog, args.changed_file)
    stages = []
    ok = True
    started = time.monotonic()

    for gate in gates:
        gate_started = time.monotonic()
        command = gate["command"]
        if command.startswith(".venv/bin/python"):
            command = sys.executable + command.removeprefix(".venv/bin/python")
        result = subprocess.run(
            command,
            cwd=REPO_ROOT,
            shell=True,
            text=True,
            capture_output=True,
            check=False,
        )
        duration = round(time.monotonic() - gate_started, 3)
        stages.append(
            {
                "gate_id": gate["id"],
                "layer": gate["layer"],
                "command": command,
                "duration_seconds": duration,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )
        print(f"[{gate['id']}] exit={result.returncode} duration={duration:.3f}s")
        if result.stdout:
            print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
        if result.stderr:
            print(result.stderr, end="" if result.stderr.endswith("\n") else "\n")
        if result.returncode:
            ok = False
            break

    report = {
        "schema": "27vette-layered-validation-report-1",
        "ok": ok,
        "changed_files": args.changed_file,
        "selected_surfaces": sorted(surfaces),
        "selection_fallback": fallback,
        "selected_gate_ids": [gate["id"] for gate in gates],
        "duration_seconds": round(time.monotonic() - started, 3),
        "stages": stages,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
