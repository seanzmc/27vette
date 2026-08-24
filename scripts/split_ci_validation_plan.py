#!/usr/bin/env python3
"""Validate, and if needed perform, the Workbook Manager non-API split.

The planner now emits the three non-API partitions directly, because the
monolithic owner measures roughly 810-890s in CI against a 900s job timeout and
narrow plans used it unsplit. This pass therefore usually just proves the
partitions arrived intact. The legacy path remains for a plan that still
carries the exhaustive ``not TestApi`` owner: it is replaced by three disjoint
expressions whose union is exactly the same test set. Partial splits and
unexpected expressions fail closed.
"""

from __future__ import annotations

import argparse
import json
import shlex
from pathlib import Path

MANAGER_TEST_PATH = "tests/test_workbook_manager.py"
LEGACY_SHARD_NAME = "manager-non-api"
LEGACY_EXPRESSION = "not TestApi"
MANAGER_OVERLAY_NODE = "test_export_overlays_registry_owned_projection_fields"
PARTITIONS = (
    (
        "manager-non-api-core",
        "not TestApi and not TestSyncBatch and not TestComparisonExport",
        "Run non-API Manager tests outside the measured sync/export owners.",
    ),
    (
        "manager-non-api-sync-and-export",
        "(TestSyncBatch or TestComparisonExport) and not " + MANAGER_OVERLAY_NODE,
        "Run the sync and comparison-export owners without the overlay proof.",
    ),
    (
        "manager-non-api-export-overlay",
        MANAGER_OVERLAY_NODE,
        "Run the measured changed-overlay export proof on its own.",
    ),
)


class PlanSplitError(RuntimeError):
    """Raised when the Manager test owner cannot be split safely."""


def _matrix(plan: dict[str, object]) -> list[dict[str, object]]:
    include = plan.get("include")
    if not isinstance(include, list):
        raise PlanSplitError("validation plan has no include matrix")
    if not all(isinstance(shard, dict) for shard in include):
        raise PlanSplitError("validation plan contains a non-object shard")
    return include


def _command(shard: dict[str, object]) -> str:
    command = shard.get("command")
    if not isinstance(command, str) or not command.strip():
        raise PlanSplitError(f"shard {shard.get('name')!r} has no command")
    return command


def _k_expression(command: str) -> str:
    tokens = shlex.split(command)
    indexes = [index for index, token in enumerate(tokens) if token == "-k"]
    if len(indexes) != 1 or indexes[0] + 1 >= len(tokens):
        raise PlanSplitError(f"expected exactly one complete -k expression: {command}")
    if MANAGER_TEST_PATH not in tokens:
        raise PlanSplitError(f"Manager shard does not target {MANAGER_TEST_PATH}: {command}")
    return tokens[indexes[0] + 1]


def _replace_k(command: str, *, expected: str, replacement: str) -> str:
    tokens = shlex.split(command)
    indexes = [index for index, token in enumerate(tokens) if token == "-k"]
    if len(indexes) != 1 or indexes[0] + 1 >= len(tokens):
        raise PlanSplitError(f"expected exactly one complete -k expression: {command}")
    if MANAGER_TEST_PATH not in tokens:
        raise PlanSplitError(f"Manager shard does not target {MANAGER_TEST_PATH}: {command}")
    expression_index = indexes[0] + 1
    if tokens[expression_index] != expected:
        raise PlanSplitError(
            f"refusing to split unexpected Manager expression "
            f"{tokens[expression_index]!r}; expected {expected!r}"
        )
    tokens[expression_index] = replacement
    return shlex.join(tokens)


def _named_shards(matrix: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    named: dict[str, dict[str, object]] = {}
    for shard in matrix:
        name = shard.get("name")
        if not isinstance(name, str) or not name:
            raise PlanSplitError("validation plan contains an unnamed shard")
        if name in named:
            raise PlanSplitError(f"validation plan repeats shard {name!r}")
        named[name] = shard
    return named


def _validate_partitions(named: dict[str, dict[str, object]]) -> None:
    expected = {name: expression for name, expression, _ in PARTITIONS}
    missing = sorted(set(expected) - set(named))
    if missing:
        raise PlanSplitError(
            "Manager non-API split is incomplete; missing " + ", ".join(missing)
        )
    for name, expression in expected.items():
        actual = _k_expression(_command(named[name]))
        if actual != expression:
            raise PlanSplitError(
                f"Manager partition {name!r} uses {actual!r}; expected {expression!r}"
            )


def split_manager_non_api(plan: dict[str, object]) -> dict[str, object]:
    """Replace the legacy owner with two disjoint, exhaustive bounded shards."""

    if plan.get("full") is not True:
        return plan

    matrix = _matrix(plan)
    named = _named_shards(matrix)
    partition_names = {name for name, _, _ in PARTITIONS}

    if LEGACY_SHARD_NAME in named:
        overlap = sorted(partition_names & set(named))
        if overlap:
            raise PlanSplitError(
                "legacy Manager shard cannot coexist with partition shard(s): "
                + ", ".join(overlap)
            )
        legacy = named[LEGACY_SHARD_NAME]
        legacy_command = _command(legacy)
        if _k_expression(legacy_command) != LEGACY_EXPRESSION:
            raise PlanSplitError(
                f"legacy Manager shard no longer owns {LEGACY_EXPRESSION!r}"
            )

        replacement_shards: list[dict[str, object]] = []
        for name, expression, description in PARTITIONS:
            shard = dict(legacy)
            shard["name"] = name
            shard["command"] = _replace_k(
                legacy_command,
                expected=LEGACY_EXPRESSION,
                replacement=expression,
            )
            shard["description"] = description
            replacement_shards.append(shard)

        index = matrix.index(legacy)
        matrix[index : index + 1] = replacement_shards
        named = _named_shards(matrix)
    elif partition_names & set(named):
        if not partition_names.issubset(named):
            present = sorted(partition_names & set(named))
            raise PlanSplitError(
                "partial Manager non-API split is not allowed; present "
                + ", ".join(present)
            )
    else:
        raise PlanSplitError(
            f"full plan is missing both {LEGACY_SHARD_NAME!r} and its partitions"
        )

    if LEGACY_SHARD_NAME in named:
        raise PlanSplitError("legacy Manager non-API shard survived the split")
    _validate_partitions(named)

    coverage = plan.get("coverage")
    if coverage is None:
        coverage = {}
        plan["coverage"] = coverage
    if not isinstance(coverage, dict):
        raise PlanSplitError("validation plan coverage metadata is not an object")
    coverage["manager_non_api_partitions"] = [
        {"name": name, "expression": expression}
        for name, expression, _ in PARTITIONS
    ]
    return plan


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    split = split_manager_non_api(plan)
    args.plan.write_text(json.dumps(split, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            split.get("coverage", {}).get("manager_non_api_partitions", []),
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
