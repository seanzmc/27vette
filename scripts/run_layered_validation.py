#!/usr/bin/env python3
"""Select and run cataloged validation gates for CI."""

from __future__ import annotations

import argparse
import json
import shlex
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
    parser.add_argument(
        "--changed-file-list",
        type=Path,
        help="newline-delimited changed paths (preserves spaces)",
    )
    return parser.parse_args()


def surfaces_for_paths(catalog: dict, paths: list[str]) -> tuple[set[str], list[str]]:
    surfaces: set[str] = set()
    unmatched: list[str] = []
    mappings = catalog["ci"]["path_surfaces"]
    for path in paths:
        matched = False
        for mapping in mappings:
            prefix = mapping["prefix"]
            if path.startswith(prefix):
                surfaces.update(mapping["surfaces"])
                matched = True
                if mapping.get("stop_after_match"):
                    break
        if not matched:
            unmatched.append(path)
    return surfaces, unmatched


def selected_gates(catalog: dict, paths: list[str]) -> tuple[list[dict], set[str], bool]:
    by_id = {gate["id"]: gate for gate in catalog["gates"]}
    test_owner_by_path = {
        path: gate["id"]
        for gate in catalog["gates"]
        for path in gate.get("test_files", [])
    }
    surfaces, unmatched = surfaces_for_paths(
        catalog, [path for path in paths if path not in test_owner_by_path]
    )
    fallback = bool(unmatched)
    if fallback:
        surfaces.update(catalog["ci"]["fallback_surfaces"])

    selected = set(catalog["ci"]["always_gate_ids"])
    selected.update(
        test_owner_by_path[path]
        for path in paths
        if path in test_owner_by_path and by_id[test_owner_by_path[path]]["layer"] < 4
    )
    selected.update(
        gate["id"]
        for gate in catalog["gates"]
        if gate["layer"] in (0, 1, 2, 3)
        and surfaces.intersection(gate["changed_surfaces"])
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


def execution_stages(catalog: dict, gates: list[dict]) -> list[dict]:
    """Collapse shared-setup groups into their cataloged one-process suite."""
    suites = {suite["id"]: suite for suite in catalog["suites"]}
    selected_ids = {gate["id"] for gate in gates}
    stages: list[dict] = []
    emitted_groups: set[str] = set()

    for gate in gates:
        group_name = gate.get("serial_group")
        group = catalog["serial_groups"].get(group_name, {})
        suite_id = group.get("suite_id")
        if group.get("standalone_selection") == "select_entire_group" and suite_id:
            if group_name in emitted_groups:
                continue
            suite = suites[suite_id]
            gate_ids = [gate_id for gate_id in suite["gate_ids"] if gate_id in selected_ids]
            stages.append(
                {
                    "stage_id": suite_id,
                    "layer": suite["layer"],
                    "command": suite["command"],
                    "gate_ids": gate_ids,
                }
            )
            assert group_name is not None
            emitted_groups.add(group_name)
            continue

        stages.append(
            {
                "stage_id": gate["id"],
                "layer": gate["layer"],
                "command": gate["command"],
                "gate_ids": [gate["id"]],
            }
        )
    return sorted(stages, key=lambda stage: stage["layer"])


def command_for_active_interpreter(command: str) -> str:
    """Run cataloged Python commands in the interpreter running this process."""
    parts = shlex.split(command)
    if parts and parts[0] in {"python", ".venv/bin/python"}:
        return shlex.join([sys.executable, *parts[1:]])
    return command


def main() -> int:
    args = parse_args()
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    changed_files = list(args.changed_file)
    if args.changed_file_list:
        changed_files.extend(
            path
            for path in args.changed_file_list.read_text(encoding="utf-8").splitlines()
            if path
        )
    gates, surfaces, fallback = selected_gates(catalog, changed_files)
    selected_stages = execution_stages(catalog, gates)
    stages = []
    ok = True
    started = time.monotonic()

    for stage in selected_stages:
        gate_started = time.monotonic()
        command = command_for_active_interpreter(stage["command"])
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
                "stage_id": stage["stage_id"],
                "gate_ids": stage["gate_ids"],
                "layer": stage["layer"],
                "command": command,
                "duration_seconds": duration,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )
        print(f"[{stage['stage_id']}] exit={result.returncode} duration={duration:.3f}s")
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
        "changed_files": changed_files,
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
