#!/usr/bin/env python3
"""Standard-library contracts for the complete full-suite matrix audit."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLANNER = REPO_ROOT / "scripts" / "plan_ci_validation.py"
FINALIZER = REPO_ROOT / "scripts" / "finalize_ci_validation_plan.py"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "release-candidate.yml"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise AssertionError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _synthetic_plan(candidate_targets: tuple[str, str]) -> dict[str, object]:
    canonical, drift = candidate_targets
    return {
        "full": True,
        "include": [
            {
                "name": "full-product-readiness",
                "command": " && ".join(
                    (
                        ".venv/bin/python scripts/verify_workbook_candidate.py "
                        "--workbook stingray_master.xlsx --changed-model '*'",
                        'for f in tests/*.test.mjs; do node --test "$f" || exit 1; done',
                        "npm --prefix workbook-manager/frontend run build",
                    )
                ),
            },
            {
                "name": "full-python-core",
                "command": ".venv/bin/python -m pytest tests/ -q "
                "--ignore tests/test_verify_workbook_candidate.py",
            },
            {
                "name": "full-python-candidate-canonical",
                "command": f".venv/bin/python -m pytest {canonical} -q",
            },
            {
                "name": "full-python-candidate-drift-and-fast",
                "command": f".venv/bin/python -m pytest {drift} -q",
            },
        ],
    }


class FullValidationPlanContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.planner = _load(PLANNER, "plan_ci_validation_inventory_contract")
        cls.finalizer = _load(FINALIZER, "finalize_ci_validation_inventory_contract")

    def test_repository_full_plan_owns_every_current_test_file(self) -> None:
        plan = self.finalizer.finalize_plan(
            self.planner.plan_validation([], full=True),
            repo_root=REPO_ROOT,
        )
        coverage = plan["coverage"]

        self.assertTrue(coverage["full"])
        self.assertEqual(
            coverage["python_test_files"],
            len(list((REPO_ROOT / "tests").rglob("test_*.py"))),
        )
        self.assertEqual(
            coverage["node_test_files"],
            len(list((REPO_ROOT / "tests").rglob("*.test.mjs"))),
        )
        self.assertGreater(coverage["candidate_verifier_tests"], 0)
        self.assertEqual(coverage["candidate_tests_auto_assigned"], [])
        self.assertTrue(coverage["composed_candidate"])
        self.assertTrue(coverage["frontend_build"])

    def test_new_candidate_test_is_auto_assigned_without_a_new_shard(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            tests = repo_root / "tests"
            tests.mkdir()
            (tests / "test_verify_workbook_candidate.py").write_text(
                "\n".join(
                    (
                        "def test_canonical(canonical_run): pass",
                        "def test_drift(drifting_undeclared): pass",
                        "def test_new_contract(): pass",
                        "",
                    )
                ),
                encoding="utf-8",
            )
            plan = _synthetic_plan(
                (
                    "tests/test_verify_workbook_candidate.py::test_canonical",
                    "tests/test_verify_workbook_candidate.py::test_drift",
                )
            )

            finalized = self.finalizer.finalize_plan(plan, repo_root=repo_root)

        combined = "\n".join(
            str(shard["command"]) for shard in finalized["include"]
        )
        self.assertIn(
            "tests/test_verify_workbook_candidate.py::test_new_contract",
            combined,
        )
        self.assertEqual(len(finalized["include"]), 4)
        self.assertEqual(
            finalized["coverage"]["candidate_tests_auto_assigned"],
            [
                {
                    "test": "tests/test_verify_workbook_candidate.py::test_new_contract",
                    "shard": "full-python-candidate-canonical",
                }
            ],
        )

    def test_stale_candidate_node_fails_before_matrix_creation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            tests = repo_root / "tests"
            tests.mkdir()
            (tests / "test_verify_workbook_candidate.py").write_text(
                "def test_current(): pass\n",
                encoding="utf-8",
            )
            plan = _synthetic_plan(
                (
                    "tests/test_verify_workbook_candidate.py::test_missing",
                    "tests/test_verify_workbook_candidate.py::test_current",
                )
            )

            with self.assertRaisesRegex(
                self.finalizer.PlanCoverageError,
                "stale pytest node",
            ):
                self.finalizer.expand_candidate_inventory(plan, repo_root=repo_root)

    def test_workflow_audits_before_exporting_the_matrix(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        test_call = "python scripts/test_finalize_ci_validation_plan.py"
        finalizer_call = (
            "python scripts/finalize_ci_validation_plan.py --plan validation-matrix.json"
        )

        self.assertIn(test_call, workflow)
        self.assertIn(finalizer_call, workflow)
        self.assertLess(workflow.index(test_call), workflow.index(finalizer_call))
        self.assertLess(workflow.index(finalizer_call), workflow.index('echo "matrix=$(jq'))
        self.assertIn("test_finalize_ci_validation_plan", workflow)


if __name__ == "__main__":
    unittest.main()
