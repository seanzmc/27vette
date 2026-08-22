"""Contract tests for catalog-driven and change-aware CI validation."""

from __future__ import annotations

import importlib.util
import json
import shlex
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_layered_validation.py"
PLANNER = REPO_ROOT / "scripts" / "plan_ci_validation.py"
CATALOG = REPO_ROOT / "tests" / "validation_catalog.json"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "release-candidate.yml"


def _load_planner():
    spec = importlib.util.spec_from_file_location("plan_ci_validation", PLANNER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _catalog(tmp_path: Path) -> Path:
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    data["gates"] = [
        {
            "id": "layer.zero",
            "layer": 0,
            "test_files": ["tests/test_layer_zero.py"],
            "command": f'{sys.executable} -c "print(\'zero\')"',
            "changed_surfaces": ["validation_infrastructure"],
            "serial_group": None,
        },
        {
            "id": "layer.one",
            "layer": 1,
            "test_files": ["tests/layer-one.test.mjs"],
            "command": f'{sys.executable} -c "print(\'one\')"',
            "changed_surfaces": ["workbook"],
            "serial_group": "protected_artifacts",
        },
        {
            "id": "manager.parity",
            "layer": 3,
            "test_files": ["tests/test_manager_parity.py"],
            "command": f'{sys.executable} -c "print(\'manager\')"',
            "changed_surfaces": ["workbook_manager"],
            "serial_group": "workbook_manager",
        },
        {
            "id": "manager.peer",
            "layer": 2,
            "test_files": ["tests/test_manager_peer.py"],
            "command": f'{sys.executable} -c "print(\'peer\')"',
            "changed_surfaces": ["workbook_manager"],
            "serial_group": "workbook_manager",
        },
        {
            "id": "asset.focused",
            "layer": 2,
            "test_files": ["tests/test_asset_focused.py"],
            "command": f'{sys.executable} -c "print(\'asset\')"',
            "changed_surfaces": ["asset_map"],
            "serial_group": None,
        },
    ]
    data["ci"] = {
        "always_gate_ids": ["layer.zero", "layer.one"],
        "path_surfaces": [
            {
                "prefix": "workbook-manager/README.md",
                "surfaces": ["docs"],
                "stop_after_match": True,
            },
            {"prefix": "workbook-manager/", "surfaces": ["workbook_manager"]},
            {"prefix": "form-app/", "surfaces": ["workbook"]},
            {"prefix": "docs/", "surfaces": ["docs"]},
        ],
        "fallback_surfaces": ["asset_map"],
    }
    data["serial_groups"] = {
        "protected_artifacts": {"standalone_selection": "selected_members"},
        "workbook_manager": {
            "standalone_selection": "select_entire_group",
            "suite_id": "suite.workbook_manager_serial_group",
        },
    }
    data["suites"] = [
        {
            "id": "suite.workbook_manager_serial_group",
            "layer": 3,
            "command": f'{sys.executable} -c "print(\'manager suite\')"',
            "gate_ids": ["manager.parity", "manager.peer"],
        }
    ]
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
    assert [stage["stage_id"] for stage in report["stages"]] == [
        "layer.zero",
        "layer.one",
        "suite.workbook_manager_serial_group",
    ]
    assert report["stages"][-1]["gate_ids"] == ["manager.parity", "manager.peer"]


def test_changed_surface_selects_matching_layer_zero_gate(tmp_path):
    catalog_path = _catalog(tmp_path)
    data = json.loads(catalog_path.read_text(encoding="utf-8"))
    data["gates"].append(
        {
            "id": "manager.fast",
            "layer": 0,
            "test_files": [],
            "command": f'{sys.executable} -c "print(\'fast\')"',
            "changed_surfaces": ["workbook_manager"],
            "serial_group": None,
        }
    )
    catalog_path.write_text(json.dumps(data), encoding="utf-8")

    report = tmp_path / "report.json"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--catalog",
            str(catalog_path),
            "--report",
            str(report),
            "--changed-file",
            "workbook-manager/backend/app/main.py",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "manager.fast" in json.loads(report.read_text(encoding="utf-8"))[
        "selected_gate_ids"
    ]


def test_changed_surface_selects_matching_layer_one_gate(tmp_path):
    report = _run(tmp_path, "form-app/app.js")
    assert "layer.one" in report["selected_gate_ids"]


def test_changed_test_selects_its_catalog_owner(tmp_path):
    report = _run(tmp_path, "tests/test_asset_focused.py")
    assert "asset.focused" in report["selected_gate_ids"]
    assert report["selected_surfaces"] == []


def test_layer_four_is_never_automatically_selected(tmp_path):
    catalog_path = _catalog(tmp_path)
    data = json.loads(catalog_path.read_text(encoding="utf-8"))
    data["gates"].append(
        {
            "id": "diagnostic.full",
            "layer": 4,
            "test_files": ["tests/test_full_diagnostic.py"],
            "command": f'{sys.executable} -c "print(\'diagnostic\')"',
            "changed_surfaces": ["workbook_manager"],
            "serial_group": None,
        }
    )
    catalog_path.write_text(json.dumps(data), encoding="utf-8")

    report = tmp_path / "report.json"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--catalog",
            str(catalog_path),
            "--report",
            str(report),
            "--changed-file",
            "tests/test_full_diagnostic.py",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "diagnostic.full" not in json.loads(report.read_text())["selected_gate_ids"]


def test_unknown_path_uses_conservative_fallback(tmp_path):
    report = _run(tmp_path, "unclassified/new-surface.txt")
    assert report["selection_fallback"] is True
    assert "asset.focused" in report["selected_gate_ids"]


def test_docs_only_change_skips_changed_surface_gates(tmp_path):
    report = _run(tmp_path, "docs/operator-note.md")
    assert report["selected_gate_ids"] == ["layer.zero", "layer.one"]


def test_nested_operator_doc_skips_workbook_manager_gates(tmp_path):
    report = _run(tmp_path, "workbook-manager/README.md")
    assert report["selected_surfaces"] == ["docs"]
    assert report["selected_gate_ids"] == ["layer.zero", "layer.one"]


def test_workflow_fetches_deleted_paths_and_runs_a_bounded_matrix():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert workflow.count("fetch-depth: 0") == 1
    assert workflow.count("fetch-depth: 1") == 1
    assert "--diff-filter=ACMRD" in workflow
    assert "timeout-minutes: 15" in workflow
    assert "timeout-minutes: 25" not in workflow
    assert "python scripts/plan_ci_validation.py" in workflow
    assert "fromJSON(needs.plan.outputs.matrix)" in workflow
    assert "matrix.python_dependencies == 'pytest'" in workflow
    assert "matrix.python_dependencies == 'project'" in workflow
    assert "cache: pip" not in workflow
    assert "VALIDATION_COMMAND" in workflow
    assert "name: release-candidate" in workflow
    assert "$(while IFS=" not in workflow


def test_pr_planner_routes_pr_37_to_changed_read_ui_and_fable_contracts():
    planner = _load_planner()
    plan = planner.plan_validation(
        [
            ".github/workflows/release-candidate.yml",
            "README.md",
            "docs/superpowers/specs/2026-08-15-workbook-manager-ux-recovery.md",
            "fable5loop/STATE.md",
            "scripts/plan_ci_validation.py",
            "tests/test_run_layered_validation.py",
            "tests/test_workbook_manager.py",
            "tests/validation_catalog.json",
            "workbook-manager/README.md",
            "workbook-manager/backend/app/explorer.py",
            "workbook-manager/backend/app/main.py",
            "workbook-manager/frontend/src/App.jsx",
            "workbook-manager/frontend/src/api.js",
            "workbook-manager/frontend/src/components/ConnectedExplorer.jsx",
            "workbook-manager/frontend/src/components/ModelOperations.jsx",
            "workbook-manager/frontend/src/styles.css",
        ]
    )

    assert plan["full"] is False
    assert [shard["name"] for shard in plan["include"]] == [
        "ci-contracts",
        "manager-read-ui",
        "fable-contracts",
    ]
    commands = "\n".join(str(shard["command"]) for shard in plan["include"])
    assert "test_workbook_manager_generated_parity.py" not in commands
    assert "test_workbook_manager_apply_rebuild.py" not in commands
    assert "test_verify_workbook_candidate.py" not in commands
    assert "TestApi and asset" not in commands

    read_ui = plan["include"][1]
    assert read_ui["python"] is True
    assert read_ui["node"] is True
    assert "npm --prefix workbook-manager/frontend run build" in read_ui["command"]
    assert "TestPass1BrowserContainment" in read_ui["command"]
    assert "test_connected_option_detail_is_model_scoped_complete_and_read_only" in read_ui["command"]
    assert "test_named_diagnostics_are_bounded_defined_scoped_and_traceable" in read_ui["command"]


def test_pr_planner_routes_frontend_only_to_build_and_shell_contracts():
    planner = _load_planner()
    plan = planner.plan_validation(["workbook-manager/frontend/src/App.jsx"])
    assert [shard["name"] for shard in plan["include"]] == [
        "ci-contracts",
        "manager-frontend",
    ]
    frontend = plan["include"][-1]
    assert frontend["python"] is True
    assert frontend["node"] is True
    assert "TestPass1BrowserContainment" in frontend["command"]


def test_pr_planner_routes_explorer_only_to_exact_api_nodes():
    planner = _load_planner()
    plan = planner.plan_validation(
        [
            "workbook-manager/backend/app/explorer.py",
            "workbook-manager/backend/app/main.py",
        ]
    )
    assert [shard["name"] for shard in plan["include"]] == [
        "ci-contracts",
        "manager-read-explorer",
    ]
    explorer = plan["include"][-1]
    assert explorer["python"] is True
    assert explorer["node"] is False
    assert "test_connected_group_detail_leads_with_description_and_named_members" in explorer["command"]
    assert "test_workbook_manager_generated_parity.py" not in explorer["command"]


def test_pr_planner_partitions_broad_api_changes():
    planner = _load_planner()
    plan = planner.plan_validation(["workbook-manager/backend/app/main.py"])
    assert [shard["name"] for shard in plan["include"]] == [
        "ci-contracts",
        "manager-api-assets",
        "manager-api-core",
    ]
    commands = {shard["name"]: shard["command"] for shard in plan["include"]}
    assert "TestApi and asset" in commands["manager-api-assets"]
    assert "TestApi and not asset" in commands["manager-api-core"]


def test_pr_planner_preserves_complete_manager_coverage_for_apply_rebuild():
    planner = _load_planner()
    plan = planner.plan_validation(["workbook-manager/backend/app/apply_rebuild.py"])
    assert [shard["name"] for shard in plan["include"]] == [
        "ci-contracts",
        "manager-api-assets",
        "manager-api-core",
        "manager-non-api",
        "manager-projection",
        "manager-drafts",
        "manager-apply-boundaries",
        "manager-apply-candidate",
    ]


def test_pr_planner_falls_back_for_unknown_manager_code():
    planner = _load_planner()
    plan = planner.plan_validation(["workbook-manager/backend/app/new_boundary.py"])
    assert [shard["name"] for shard in plan["include"]] == [
        "ci-contracts",
        "manager-api-assets",
        "manager-api-core",
        "manager-non-api",
        "manager-projection",
        "manager-drafts",
        "manager-apply-boundaries",
    ]


def test_pr_planner_routes_drafts_to_api_and_lifecycle_owners():
    planner = _load_planner()
    plan = planner.plan_validation(["workbook-manager/backend/app/drafts.py"])
    assert [shard["name"] for shard in plan["include"]] == [
        "ci-contracts",
        "manager-api-core",
        "manager-drafts",
    ]


def test_pr_planner_runs_fable_contracts_for_state_changes():
    planner = _load_planner()
    plan = planner.plan_validation(["fable5loop/STATE.md"])
    assert [shard["name"] for shard in plan["include"]] == [
        "ci-contracts",
        "fable-contracts",
    ]
    assert "scripts/validate_fable5_loop.py" in plan["include"][-1]["command"]
    assert "tests/test_fable5_loop_contract.py" in plan["include"][-1]["command"]


def test_pr_planner_covers_test_only_manager_change_in_three_partitions():
    planner = _load_planner()
    plan = planner.plan_validation(["tests/test_workbook_manager.py"])
    assert [shard["name"] for shard in plan["include"]] == [
        "ci-contracts",
        "manager-api-assets",
        "manager-api-core",
        "manager-non-api",
    ]


def test_pr_planner_delegates_non_manager_changes_without_duplicate_contract_job():
    planner = _load_planner()
    plan = planner.plan_validation(["scripts/corvette_form_generator/rules.py"])
    assert [shard["name"] for shard in plan["include"]] == [
        "layered-changed-surfaces",
    ]
    assert "--changed-file scripts/corvette_form_generator/rules.py" in plan["include"][0]["command"]


def test_pr_planner_uses_a_no_toolchain_check_for_docs_only():
    planner = _load_planner()
    plan = planner.plan_validation(["docs/operator-note.md"])
    assert [shard["name"] for shard in plan["include"]] == ["docs-only"]
    assert plan["include"][0]["python"] is False
    assert plan["include"][0]["node"] is False


def test_ci_infrastructure_only_runs_contracts_not_product_inventory():
    planner = _load_planner()
    plan = planner.plan_validation(["scripts/plan_ci_validation.py"])
    assert plan["full"] is False
    assert [shard["name"] for shard in plan["include"]] == ["ci-contracts"]
    assert plan["include"][0]["python_dependencies"] == "pytest"


def test_manual_full_plan_partitions_every_measured_heavy_owner():
    planner = _load_planner()
    plan = planner.plan_validation([], full=True)
    assert [shard["name"] for shard in plan["include"]] == [
        "full-product-readiness",
        "full-python-core",
        "full-python-candidate-canonical",
        "full-python-candidate-drift-and-fast",
        "full-python-editor-ops",
        "full-python-editor-server",
        "manager-api-assets",
        "manager-api-core",
        "manager-non-api",
        "manager-projection",
        "manager-drafts",
        "manager-apply-boundaries",
    ]

    product = plan["include"][0]
    assert "scripts/verify_workbook_candidate.py" in product["command"]
    assert "scripts/run_layered_validation.py" not in product["command"]
    assert "tests/*.test.mjs" in product["command"]
    assert "workbook-manager/frontend run build" in product["command"]

    core = next(shard for shard in plan["include"] if shard["name"] == "full-python-core")
    for heavy in (
        "tests/test_workbook_manager.py",
        "tests/test_verify_workbook_candidate.py",
        "tests/test_editor_ops_apply.py",
        "tests/test_editor_server_write_api.py",
    ):
        assert f"--ignore {heavy}" in core["command"]
    assert "--ignore tests/test_validation_catalog.py" not in core["command"]
    assert "--ignore tests/test_run_layered_validation.py" not in core["command"]

    candidate_commands = "\n".join(
        shard["command"]
        for shard in plan["include"]
        if shard["name"].startswith("full-python-candidate-")
    )
    assert candidate_commands.count("tests/test_verify_workbook_candidate.py::") == 17

    manager_commands = {
        shard["name"]: shard["command"]
        for shard in plan["include"]
        if shard["name"].startswith("manager-")
    }
    assert "TestApi and asset" in manager_commands["manager-api-assets"]
    assert "TestApi and not asset" in manager_commands["manager-api-core"]
    assert "not TestApi" in manager_commands["manager-non-api"]
    assert not any(
        command.endswith("tests/test_workbook_manager.py -q")
        for command in manager_commands.values()
    )


def test_dependency_change_escalates_to_full_plan():
    planner = _load_planner()
    plan = planner.plan_validation(["requirements-test.txt"])
    assert plan["full"] is True
    assert plan["include"][0]["name"] == "full-product-readiness"


def test_changed_file_list_preserves_paths_with_spaces(tmp_path):
    report = tmp_path / "report.json"
    changed_files = tmp_path / "changed-files.txt"
    changed_files.write_text("docs/operator note.md\n", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--catalog",
            str(_catalog(tmp_path)),
            "--report",
            str(report),
            "--changed-file-list",
            str(changed_files),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(report.read_text(encoding="utf-8"))["changed_files"] == [
        "docs/operator note.md"
    ]


def test_catalog_python_commands_use_the_runner_interpreter(tmp_path):
    catalog_path = _catalog(tmp_path)
    data = json.loads(catalog_path.read_text(encoding="utf-8"))
    marker = tmp_path / "python-command.json"
    data["gates"][0]["command"] = (
        "python -c \"import json, pathlib, sys; "
        f"pathlib.Path({str(marker)!r}).write_text(json.dumps(sys.executable))\""
    )
    catalog_path.write_text(json.dumps(data), encoding="utf-8")

    report = tmp_path / "report.json"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--catalog",
            str(catalog_path),
            "--report",
            str(report),
            "--changed-file",
            "docs/operator-note.md",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    stage = json.loads(report.read_text(encoding="utf-8"))["stages"][0]
    assert shlex.split(stage["command"])[0] == sys.executable
    assert json.loads(marker.read_text(encoding="utf-8")) == sys.executable


def test_layer_zero_runs_before_layer_one_when_catalog_order_is_reversed(tmp_path):
    catalog_path = _catalog(tmp_path)
    data = json.loads(catalog_path.read_text(encoding="utf-8"))
    data["gates"][0], data["gates"][1] = data["gates"][1], data["gates"][0]
    catalog_path.write_text(json.dumps(data), encoding="utf-8")

    report = tmp_path / "report.json"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--catalog",
            str(catalog_path),
            "--report",
            str(report),
            "--changed-file",
            "docs/operator-note.md",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert [stage["stage_id"] for stage in json.loads(report.read_text())["stages"]] == [
        "layer.zero",
        "layer.one",
    ]
