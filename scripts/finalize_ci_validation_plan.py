#!/usr/bin/env python3
"""Finalize and prove the complete GitHub Actions validation inventory.

The change-aware planner keeps ordinary pull requests economical. Full runs need
an additional invariant: every repository test must be owned by the generated
matrix, including tests added after the measured heavy shards were designed.
This standard-library-only pass expands the candidate-verifier partitions and
then audits Python, Node, composed-candidate, and frontend-build coverage before
GitHub creates the matrix jobs.
"""

from __future__ import annotations

import argparse
import ast
import json
import shlex
from pathlib import Path
from typing import Iterable

CANDIDATE_TEST_PATH = "tests/test_verify_workbook_candidate.py"
CANDIDATE_SHARDS = (
    "full-python-candidate-canonical",
    "full-python-candidate-drift-and-fast",
)
MANAGER_MAIN_TEST = "tests/test_workbook_manager.py"
MANAGER_MAIN_PARTITIONS = {
    "manager-api-assets": "TestApi and asset",
    "manager-api-core": "TestApi and not asset",
    "manager-non-api": "not TestApi",
}


class PlanCoverageError(RuntimeError):
    """Raised when a full validation plan can omit repository tests."""


def _shards(plan: dict[str, object]) -> dict[str, dict[str, object]]:
    include = plan.get("include")
    if not isinstance(include, list):
        raise PlanCoverageError("validation plan has no include matrix")

    result: dict[str, dict[str, object]] = {}
    for shard in include:
        if not isinstance(shard, dict) or not isinstance(shard.get("name"), str):
            raise PlanCoverageError("validation plan contains an unnamed shard")
        name = str(shard["name"])
        if name in result:
            raise PlanCoverageError(f"validation plan repeats shard {name!r}")
        result[name] = shard
    return result


def _command(shard: dict[str, object]) -> str:
    command = shard.get("command")
    if not isinstance(command, str) or not command.strip():
        raise PlanCoverageError(f"shard {shard.get('name')!r} has no command")
    return command


def _function_fixtures(node: ast.FunctionDef | ast.AsyncFunctionDef) -> frozenset[str]:
    args = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
    return frozenset(arg.arg for arg in args if arg.arg not in {"self", "cls"})


def discover_candidate_tests(
    repo_root: Path,
    *,
    relative_path: str = CANDIDATE_TEST_PATH,
) -> dict[str, frozenset[str]]:
    """Return stable pytest node prefixes and their fixture parameters via AST."""

    source_path = repo_root / relative_path
    if not source_path.is_file():
        raise PlanCoverageError(f"candidate verifier test file is missing: {relative_path}")

    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    discovered: dict[str, frozenset[str]] = {}

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("test_"):
                discovered[f"{relative_path}::{node.name}"] = _function_fixtures(node)
            continue
        if not isinstance(node, ast.ClassDef) or not node.name.startswith("Test"):
            continue
        for member in node.body:
            if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)) and member.name.startswith(
                "test_"
            ):
                discovered[
                    f"{relative_path}::{node.name}::{member.name}"
                ] = _function_fixtures(member)

    if not discovered:
        raise PlanCoverageError(f"no pytest tests discovered in {relative_path}")
    return discovered


def _targets(command: str, *, file_path: str | None = None) -> list[str]:
    result: list[str] = []
    for token in shlex.split(command):
        if not token.startswith("tests/"):
            continue
        normalized = token.split("[", 1)[0]
        test_file = normalized.split("::", 1)[0]
        if not test_file.endswith(".py"):
            continue
        if file_path is None or test_file == file_path:
            result.append(normalized)
    return result


def _append_target(command: str, target: str, *, file_path: str) -> str:
    tokens = shlex.split(command)
    candidate_indexes = [
        index for index, token in enumerate(tokens) if token.split("::", 1)[0] == file_path
    ]
    if not candidate_indexes:
        raise PlanCoverageError(f"candidate shard does not target {file_path}: {command}")
    tokens.insert(candidate_indexes[-1] + 1, target)
    return shlex.join(tokens)


def _choose_candidate_shard(
    fixtures: Iterable[str],
    counts: dict[str, int],
) -> str:
    fixture_set = set(fixtures)
    if fixture_set & {"canonical_run", "drifting_declared"}:
        return CANDIDATE_SHARDS[0]
    if "drifting_undeclared" in fixture_set:
        return CANDIDATE_SHARDS[1]
    return min(CANDIDATE_SHARDS, key=lambda name: (counts[name], name))


def expand_candidate_inventory(
    plan: dict[str, object],
    *,
    repo_root: Path,
    relative_path: str = CANDIDATE_TEST_PATH,
) -> list[dict[str, str]]:
    """Adopt newly added candidate-verifier tests without duplicating fixtures."""

    if plan.get("full") is not True:
        return []

    shards = _shards(plan)
    missing_shards = [name for name in CANDIDATE_SHARDS if name not in shards]
    if missing_shards:
        raise PlanCoverageError(
            "full plan is missing candidate-verifier shard(s): " + ", ".join(missing_shards)
        )

    discovered = discover_candidate_tests(repo_root, relative_path=relative_path)
    planned_by_shard = {
        name: _targets(_command(shards[name]), file_path=relative_path)
        for name in CANDIDATE_SHARDS
    }
    planned = {target for targets in planned_by_shard.values() for target in targets}
    duplicate_count = sum(len(targets) for targets in planned_by_shard.values()) - len(planned)
    if duplicate_count:
        raise PlanCoverageError("candidate-verifier tests are duplicated across full shards")

    stale = sorted(planned - set(discovered))
    if stale:
        raise PlanCoverageError(
            "candidate-verifier plan contains stale pytest node(s): " + ", ".join(stale)
        )

    counts = {name: len(targets) for name, targets in planned_by_shard.items()}
    assignments: list[dict[str, str]] = []
    for target in sorted(set(discovered) - planned):
        shard_name = _choose_candidate_shard(discovered[target], counts)
        shard = shards[shard_name]
        shard["command"] = _append_target(
            _command(shard),
            target,
            file_path=relative_path,
        )
        counts[shard_name] += 1
        assignments.append({"test": target, "shard": shard_name})

    final_targets = {
        target
        for name in CANDIDATE_SHARDS
        for target in _targets(_command(shards[name]), file_path=relative_path)
    }
    if final_targets != set(discovered):
        missing = sorted(set(discovered) - final_targets)
        extra = sorted(final_targets - set(discovered))
        raise PlanCoverageError(
            f"candidate-verifier inventory mismatch; missing={missing}, extra={extra}"
        )
    return assignments


def _ignored_paths(command: str) -> set[str]:
    tokens = shlex.split(command)
    ignored: set[str] = set()
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == "--ignore":
            if index + 1 >= len(tokens):
                raise PlanCoverageError("full-python-core ends with --ignore")
            ignored.add(tokens[index + 1])
            index += 2
            continue
        if token.startswith("--ignore="):
            ignored.add(token.partition("=")[2])
        index += 1
    return ignored


def _option_value(command: str, option: str) -> str | None:
    tokens = shlex.split(command)
    for index, token in enumerate(tokens):
        if token == option and index + 1 < len(tokens):
            return tokens[index + 1]
        if token.startswith(f"{option}="):
            return token.partition("=")[2]
    return None


def audit_full_plan(
    plan: dict[str, object],
    *,
    repo_root: Path,
    assignments: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    """Prove that every current test file is owned by the full matrix."""

    if plan.get("full") is not True:
        return {"full": False}

    shards = _shards(plan)
    required = {"full-product-readiness", "full-python-core", *CANDIDATE_SHARDS}
    missing_required = sorted(required - set(shards))
    if missing_required:
        raise PlanCoverageError(
            "full plan is missing required shard(s): " + ", ".join(missing_required)
        )

    tests_root = repo_root / "tests"
    python_files = sorted(
        path.relative_to(repo_root).as_posix()
        for path in tests_root.rglob("test_*.py")
        if path.is_file()
    )
    node_files = sorted(
        path.relative_to(repo_root).as_posix()
        for path in tests_root.rglob("*.test.mjs")
        if path.is_file()
    )
    if not python_files:
        raise PlanCoverageError("repository has no Python tests to audit")

    core_command = _command(shards["full-python-core"])
    core_tokens = shlex.split(core_command)
    if "tests/" not in core_tokens:
        raise PlanCoverageError("full-python-core does not collect the tests/ tree")
    ignored = _ignored_paths(core_command)
    unknown_ignored = sorted(ignored - set(python_files))
    if unknown_ignored:
        raise PlanCoverageError(
            "full-python-core ignores missing test file(s): " + ", ".join(unknown_ignored)
        )

    exact_file_targets: set[str] = set()
    for shard in shards.values():
        for target in _targets(_command(shard)):
            if "::" not in target:
                exact_file_targets.add(target)

    candidate_tests = discover_candidate_tests(repo_root)
    candidate_planned = {
        target
        for name in CANDIDATE_SHARDS
        for target in _targets(_command(shards[name]), file_path=CANDIDATE_TEST_PATH)
    }
    if candidate_planned != set(candidate_tests):
        raise PlanCoverageError("candidate-verifier nodes are not exhaustive after expansion")

    manager_partitioned = False
    if MANAGER_MAIN_TEST in ignored:
        manager_partitioned = all(
            name in shards and _option_value(_command(shards[name]), "-k") == expression
            for name, expression in MANAGER_MAIN_PARTITIONS.items()
        )
        if not manager_partitioned:
            raise PlanCoverageError(
                "Workbook Manager main test is ignored without three exhaustive partitions"
            )

    uncovered_ignored: list[str] = []
    for path in sorted(ignored):
        if path == CANDIDATE_TEST_PATH:
            continue
        if path == MANAGER_MAIN_TEST and manager_partitioned:
            continue
        if path in exact_file_targets:
            continue
        uncovered_ignored.append(path)
    if uncovered_ignored:
        raise PlanCoverageError(
            "full-python-core ignores test file(s) with no complete owner: "
            + ", ".join(uncovered_ignored)
        )

    product_command = _command(shards["full-product-readiness"])
    nested_node_tests = [
        path for path in node_files if Path(path).parent.as_posix() != "tests"
    ]
    if nested_node_tests:
        raise PlanCoverageError(
            "root tests/*.test.mjs glob does not cover nested Node test(s): "
            + ", ".join(nested_node_tests)
        )
    if node_files and not (
        "tests/*.test.mjs" in product_command and "node --test" in product_command
    ):
        raise PlanCoverageError("full-product-readiness does not execute every Node test")
    if not (
        "scripts/verify_workbook_candidate.py" in product_command
        and "--changed-model '*'" in product_command
    ):
        raise PlanCoverageError("full-product-readiness omits the composed candidate lane")
    if "npm --prefix workbook-manager/frontend run build" not in product_command:
        raise PlanCoverageError("full-product-readiness omits the frontend production build")

    covered_python = (set(python_files) - ignored) | ignored
    if covered_python != set(python_files):
        raise PlanCoverageError("Python inventory accounting is incomplete")

    return {
        "full": True,
        "python_test_files": len(python_files),
        "node_test_files": len(node_files),
        "candidate_verifier_tests": len(candidate_tests),
        "ignored_python_files_with_explicit_owners": len(ignored),
        "candidate_tests_auto_assigned": assignments or [],
        "composed_candidate": True,
        "frontend_build": True,
    }


def finalize_plan(plan: dict[str, object], *, repo_root: Path) -> dict[str, object]:
    assignments = expand_candidate_inventory(plan, repo_root=repo_root)
    plan["coverage"] = audit_full_plan(
        plan,
        repo_root=repo_root,
        assignments=assignments,
    )
    return plan


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    finalized = finalize_plan(plan, repo_root=args.repo_root.resolve())
    args.plan.write_text(json.dumps(finalized, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(finalized.get("coverage", {}), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
