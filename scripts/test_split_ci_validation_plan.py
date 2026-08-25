#!/usr/bin/env python3
"""Standard-library contracts for the bounded Manager non-API split."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLANNER = REPO_ROOT / "scripts" / "plan_ci_validation.py"
FINALIZER = REPO_ROOT / "scripts" / "finalize_ci_validation_plan.py"
SPLITTER = REPO_ROOT / "scripts" / "split_ci_validation_plan.py"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "release-candidate.yml"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise AssertionError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _legacy_plan() -> dict[str, object]:
    return {
        "full": True,
        "coverage": {"full": True},
        "include": [
            {
                "name": "before",
                "command": "python -m pytest tests/test_other.py -q",
                "python": True,
                "node": False,
                "python_dependencies": "project",
                "description": "before",
            },
            {
                "name": "manager-non-api",
                "command": (
                    ".venv/bin/python -m pytest tests/test_workbook_manager.py "
                    "-k 'not TestApi' -q"
                ),
                "python": True,
                "node": True,
                "python_dependencies": "project",
                "description": "legacy",
            },
            {
                "name": "after",
                "command": "node --test tests/after.test.mjs",
                "python": False,
                "node": True,
                "description": "after",
            },
        ],
    }


class ManagerSplitContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.planner = _load(PLANNER, "plan_ci_validation_split_contract")
        cls.finalizer = _load(FINALIZER, "finalize_ci_validation_split_contract")
        cls.splitter = _load(SPLITTER, "split_ci_validation_split_contract")

    def test_legacy_owner_becomes_three_disjoint_exhaustive_partitions(self) -> None:
        plan = self.splitter.split_manager_non_api(_legacy_plan())
        names = [str(shard["name"]) for shard in plan["include"]]

        self.assertEqual(
            names,
            [
                "before",
                "manager-non-api-core",
                "manager-non-api-sync-and-export",
                "manager-non-api-export-overlay",
                "after",
            ],
        )
        self.assertNotIn("manager-non-api", names)

        shards = {str(shard["name"]): shard for shard in plan["include"]}
        self.assertEqual(
            self.splitter._k_expression(
                str(shards["manager-non-api-core"]["command"])
            ),
            "not TestApi and not TestSyncBatch and not TestComparisonExport",
        )
        self.assertEqual(
            self.splitter._k_expression(
                str(shards["manager-non-api-sync-and-export"]["command"])
            ),
            "(TestSyncBatch or TestComparisonExport) and not "
            "test_export_overlays_registry_owned_projection_fields",
        )
        self.assertEqual(
            self.splitter._k_expression(
                str(shards["manager-non-api-export-overlay"]["command"])
            ),
            "test_export_overlays_registry_owned_projection_fields",
        )
        for name in (
            "manager-non-api-core",
            "manager-non-api-sync-and-export",
            "manager-non-api-export-overlay",
        ):
            self.assertTrue(shards[name]["python"])
            self.assertTrue(shards[name]["node"])
            self.assertEqual(shards[name]["python_dependencies"], "project")

        self.assertEqual(
            len(plan["coverage"]["manager_non_api_partitions"]),
            3,
        )

    def test_split_is_idempotent(self) -> None:
        plan = self.splitter.split_manager_non_api(_legacy_plan())
        again = self.splitter.split_manager_non_api(plan)
        self.assertEqual(again, plan)

    def test_unexpected_legacy_expression_fails_closed(self) -> None:
        plan = _legacy_plan()
        plan["include"][1]["command"] = (
            ".venv/bin/python -m pytest tests/test_workbook_manager.py "
            "-k 'not TestApi and not slow' -q"
        )
        with self.assertRaisesRegex(
            self.splitter.PlanSplitError,
            "no longer owns",
        ):
            self.splitter.split_manager_non_api(plan)

    def test_repository_full_plan_finishes_with_eighteen_owned_shards(self) -> None:
        plan = self.planner.plan_validation([], full=True)
        plan = self.finalizer.finalize_plan(plan, repo_root=REPO_ROOT)
        plan = self.splitter.split_manager_non_api(plan)
        names = [str(shard["name"]) for shard in plan["include"]]

        # Fourteen product shards plus the four narrow-plan-only smoke shards.
        self.assertEqual(len(names), 18)
        self.assertEqual(len([n for n in names if n.startswith("smoke-")]), 4)
        self.assertNotIn("manager-non-api", names)
        self.assertIn("manager-non-api-core", names)
        self.assertIn("manager-non-api-sync-and-export", names)
        self.assertIn("manager-non-api-export-overlay", names)
        self.assertTrue(plan["coverage"]["full"])
        self.assertEqual(
            len(plan["coverage"]["manager_non_api_partitions"]),
            3,
        )

    def test_workflow_tests_audits_splits_then_exports(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        ordered = (
            "python scripts/test_finalize_ci_validation_plan.py",
            "python scripts/test_split_ci_validation_plan.py",
            'python scripts/plan_ci_validation.py "${args[@]}"',
            "python scripts/finalize_ci_validation_plan.py --plan validation-matrix.json",
            "python scripts/split_ci_validation_plan.py --plan validation-matrix.json",
            'echo "matrix=$(jq',
        )
        positions = [workflow.index(item) for item in ordered]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("split_ci_validation_plan", workflow)
        self.assertIn("test_split_ci_validation_plan", workflow)


if __name__ == "__main__":
    unittest.main()
