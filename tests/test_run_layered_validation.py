"""Contract tests for catalog-driven and change-aware CI validation."""

from __future__ import annotations

import importlib.util
import json
import shlex
import subprocess
import sys
from pathlib import Path

import pytest


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
    # The catalog is classified rather than blanket-escalated, so it must not
    # sit in the unconditional full-suite trigger any more.
    assert "tests/validation_catalog\\.json$" not in workflow
    assert "python scripts/catalog_change_scope.py" in workflow
    assert "--catalog-scope catalog-scope.json" in workflow
    assert 'grep -qx \'tests/validation_catalog.json\' changed-files.txt' in workflow
    assert "DIFF_BASE=$diff_base" in workflow


def test_pr_planner_keeps_manager_partitions_when_the_diff_adds_frontend_files():
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
    # Editing tests/test_workbook_manager.py always runs its three partitions.
    # A carve-out once dropped them whenever the same diff touched a frontend
    # file, so adding a file to a diff removed coverage instead of adding it.
    assert [shard["name"] for shard in plan["include"]] == [
        "ci-contracts",
        "manager-read-ui",
        "manager-api-assets",
        "manager-api-core",
        "manager-non-api-core",
        "manager-non-api-sync-and-export",
        "manager-non-api-export-overlay",
        "fable-contracts",
    ]
    commands = "\n".join(str(shard["command"]) for shard in plan["include"])
    assert "test_workbook_manager_generated_parity.py" not in commands
    assert "test_workbook_manager_apply_rebuild.py" not in commands
    assert "test_verify_workbook_candidate.py" not in commands

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
        "manager-non-api-core",
        "manager-non-api-sync-and-export",
        "manager-non-api-export-overlay",
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
        "manager-non-api-core",
        "manager-non-api-sync-and-export",
        "manager-non-api-export-overlay",
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
    # A Fable state edit cannot change catalog, planner, or workflow contracts,
    # so it must not drag the CI contract owners along.
    assert [shard["name"] for shard in plan["include"]] == ["fable-contracts"]
    assert "scripts/validate_fable5_loop.py" in plan["include"][-1]["command"]
    assert "tests/test_fable5_loop_contract.py" in plan["include"][-1]["command"]


def test_pr_planner_covers_test_only_manager_change_in_three_partitions():
    planner = _load_planner()
    plan = planner.plan_validation(["tests/test_workbook_manager.py"])
    assert [shard["name"] for shard in plan["include"]] == [
        "ci-contracts",
        "manager-api-assets",
        "manager-api-core",
        "manager-non-api-core",
        "manager-non-api-sync-and-export",
        "manager-non-api-export-overlay",
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
    # The shard installs project dependencies, but only so its own contracts can
    # import what they collect. Running the product inventory is what this test
    # forbids, and the single-shard assertion above is what forbids it.
    assert plan["include"][0]["python_dependencies"] == "project"


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
        "manager-non-api-core",
        "manager-non-api-sync-and-export",
        "manager-non-api-export-overlay",
        "manager-projection",
        "manager-drafts",
        "manager-apply-boundaries",
        # Narrow-plan-only wiring, smoked so planner changes cannot break it
        # silently. See test_every_narrow_plan_only_shard_is_smoked_by_full_runs.
        "smoke-ci-contracts",
        "smoke-manager-review-tooling",
        "smoke-fable-contracts",
        "smoke-manager-read-explorer",
        "smoke-docs-only",
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
    # The non-API owner is partitioned in every plan, not only the full one:
    # unsplit it measures 372.77s locally, roughly 810-890s in CI against a
    # 900s job timeout.
    assert (
        "not TestApi and not TestSyncBatch and not TestComparisonExport"
        in manager_commands["manager-non-api-core"]
    )
    assert (
        "(TestSyncBatch or TestComparisonExport) and not "
        "test_export_overlays_registry_owned_projection_fields"
        in manager_commands["manager-non-api-sync-and-export"]
    )
    assert (
        "-k test_export_overlays_registry_owned_projection_fields"
        in manager_commands["manager-non-api-export-overlay"]
    )
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


def test_pr_planner_routes_review_tooling_to_its_own_owner():
    planner = _load_planner()
    plan = planner.plan_validation(
        [
            "workbook-manager/review/sync_group_display_label_review.py",
            "workbook-manager/review/group-display-label-review.csv",
        ]
    )

    # workbook-manager/review is offline tooling plus reviewed evidence files.
    # It used to land in the unclassified-source branch and drag in the entire
    # shared-fixture Manager suite.
    assert plan["full"] is False
    assert [shard["name"] for shard in plan["include"]] == ["manager-review-tooling"]
    command = str(plan["include"][0]["command"])
    assert "tests/test_group_display_label_contract.py" in command
    assert "test_workbook_manager.py" not in command
    assert "test_workbook_manager_generated_parity.py" not in command


def test_review_tooling_does_not_escalate_alongside_a_classified_backend_change():
    planner = _load_planner()
    plan = planner.plan_validation(
        [
            "workbook-manager/review/sync_group_display_label_review.py",
            "workbook-manager/backend/app/explorer.py",
        ]
    )

    names = [shard["name"] for shard in plan["include"]]
    assert "manager-review-tooling" in names
    assert "manager-read-explorer" in names
    assert "manager-projection" not in names
    assert not any(name.startswith("manager-non-api") for name in names)


def test_unclassified_manager_backend_code_still_escalates():
    planner = _load_planner()
    plan = planner.plan_validation(["workbook-manager/backend/app/new_boundary.py"])

    names = [shard["name"] for shard in plan["include"]]
    assert "manager-projection" in names
    assert "manager-non-api-core" in names
    assert "manager-non-api-export-overlay" in names


def test_an_additive_catalog_edit_runs_only_the_new_gate():
    planner = _load_planner()
    plan = planner.plan_validation(
        ["tests/validation_catalog.json"],
        catalog_gate_ids=["py.test_catalog_change_scope"],
    )

    assert plan["full"] is False
    assert [shard["name"] for shard in plan["include"]] == [
        "ci-contracts",
        "catalog-new-gates",
    ]
    command = str(plan["include"][-1]["command"])
    assert "tests/test_catalog_change_scope.py" in command
    assert "tests/test_workbook_manager.py" not in command


def test_an_unknown_catalog_gate_id_fails_closed():
    planner = _load_planner()
    with pytest.raises(KeyError):
        planner.plan_validation(
            ["tests/validation_catalog.json"],
            catalog_gate_ids=["py.does_not_exist"],
        )


def test_the_codex_disposition_owner_is_an_always_gate():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    # The ci-contracts shard runs this owner whenever no layered shard does.
    # Both paths must agree, or the gate depends on which branch CI takes.
    assert "py.test_codex_finding_disposition" in catalog["ci"]["always_gate_ids"]


def _every_shard_the_planner_can_build(planner) -> dict[str, dict]:
    """Every shard reachable from any planner factory, found by reflection.

    A hand-written list of sample diffs cannot stay exhaustive: a new route added
    later is simply absent, and the guard below then passes while proving less.
    Reflection over the factories keeps the universe honest, and
    ``test_no_shard_is_built_outside_a_factory`` stops a shard from hiding in an
    inline ``_shard(...)`` call where reflection cannot see it.
    """

    built: dict[str, dict] = {}
    for name in dir(planner):
        if not name.startswith("_") or not name.endswith(("_shard", "_shards")):
            continue
        factory = getattr(planner, name)
        if not callable(factory) or name == "_shard":
            continue
        try:
            produced = factory()
        except TypeError:
            # Parameterised factories are covered by the scenario cross-check.
            continue
        if isinstance(produced, dict):
            produced = (produced,)
        for shard in produced:
            built[str(shard["name"])] = shard
    return built


def _scenario_reachable_shards(planner) -> dict[str, dict]:
    """Shards produced by running the planner over representative diffs."""

    scenarios = (
        ["docs/operator-note.md"],
        ["scripts/corvette_form_generator/rules.py"],
        ["scripts/plan_ci_validation.py"],
        ["workbook-manager/frontend/src/components/EditorShell.jsx"],
        ["workbook-manager/review/tool.py"],
        ["workbook-manager/backend/app/explorer.py"],
        ["workbook-manager/frontend/src/x.jsx", "workbook-manager/backend/app/explorer.py"],
        ["workbook-manager/backend/app/apply_rebuild.py"],
        ["workbook-manager/backend/app/drafts.py"],
        ["workbook-manager/backend/app/projection.py"],
        ["workbook-manager/backend/app/config.py"],
        ["workbook-manager/backend/app.py"],
        ["tests/test_workbook_manager.py"],
        ["tests/test_workbook_manager_drafts.py"],
        ["tests/workbook_manager_fixtures.py"],
        ["form-app/app.js"],
        ["fable5loop/STATE.md"],
    )
    reachable = {
        str(shard["name"]): shard
        for scenario in scenarios
        for shard in planner.plan_validation(scenario)["include"]
    }
    reachable.update({
        str(shard["name"]): shard
        for shard in planner.plan_validation(
            ["tests/validation_catalog.json"],
            catalog_gate_ids=["py.test_catalog_change_scope"],
        )["include"]
    })
    return reachable


def _is_exempt(planner, name: str) -> bool:
    if name in planner.SMOKE_EXEMPT_SHARDS:
        return True
    return any(
        name.startswith(prefix) for prefix in planner.SMOKE_EXEMPT_SHARD_PREFIXES
    )


def test_no_shard_is_built_outside_a_factory():
    """Reflection is only exhaustive while every shard comes from a factory.

    A ``_shard(...)`` call inside plan_validation builds a shard that
    _every_shard_the_planner_can_build cannot see, silently shrinking the guard
    below. manager-apply-candidate was exactly that until it was extracted.

    This reads the source rather than the module: keeping a factory around while
    plan_validation still constructs the shard inline would defeat any check
    based on the names reflection can reach.
    """

    import ast

    source = (REPO_ROOT / "scripts" / "plan_ci_validation.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)

    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name.endswith(("_shard", "_shards")):
            continue
        for inner in ast.walk(node):
            if (
                isinstance(inner, ast.Call)
                and isinstance(inner.func, ast.Name)
                and inner.func.id == "_shard"
            ):
                offenders.append(f"{node.name}:{inner.lineno}")

    assert not offenders, (
        f"_shard() called outside a factory at {offenders}. Extract each into a "
        "_*_shard() factory so the smoke guard can see it."
    )


def test_every_narrow_plan_only_shard_is_smoked_by_full_runs():
    """A shard a full run never reaches is a shard no planner change can test.

    Every edit to the planner forces a full run, so without this the wiring of a
    narrow-plan-only shard is only ever executed by unrelated pull requests. That
    is exactly how ci-contracts shipped with bare pytest while its own contract
    needed openpyxl to collect anything.
    """

    planner = _load_planner()

    full_names = {
        str(shard["name"])
        for shard in planner.plan_validation([], full=True)["include"]
    }
    smoked = {
        name[len("smoke-"):] for name in full_names if name.startswith("smoke-")
    }

    universe = set(_every_shard_the_planner_can_build(planner))
    universe |= set(_scenario_reachable_shards(planner))
    universe -= {name for name in universe if name.startswith("smoke-")}

    narrow_only = universe - full_names
    unsmoked = {
        name
        for name in narrow_only
        if name not in smoked and not _is_exempt(planner, name)
    }
    assert not unsmoked, (
        f"narrow-plan-only shards a full run never exercises: {sorted(unsmoked)}. "
        "Add them to _smoke_shards() or justify them in SMOKE_EXEMPT_SHARDS."
    )


def test_smoke_exemptions_stay_honest():
    """An exemption must name a shard the planner still builds and never smokes."""

    planner = _load_planner()
    universe = set(_every_shard_the_planner_can_build(planner))
    universe |= set(_scenario_reachable_shards(planner))

    stale = set(planner.SMOKE_EXEMPT_SHARDS) - universe
    assert not stale, f"SMOKE_EXEMPT_SHARDS names no longer planned: {sorted(stale)}"

    full_names = {
        str(shard["name"])
        for shard in planner.plan_validation([], full=True)["include"]
    }
    smoked = {
        name[len("smoke-"):] for name in full_names if name.startswith("smoke-")
    }
    both = set(planner.SMOKE_EXEMPT_SHARDS) & smoked
    assert not both, f"shards both smoked and exempt: {sorted(both)}"

    unused_prefixes = {
        prefix
        for prefix in planner.SMOKE_EXEMPT_SHARD_PREFIXES
        if not any(name.startswith(prefix) for name in universe)
    }
    assert not unused_prefixes, (
        f"SMOKE_EXEMPT_SHARD_PREFIXES matches nothing planned: {sorted(unused_prefixes)}"
    )


def test_smoke_shards_keep_the_real_shard_wiring():
    """A smoke shard proves nothing if its command or toolchain has drifted."""

    planner = _load_planner()
    full = {shard["name"]: shard for shard in planner.plan_validation([], full=True)["include"]}
    originals = {
        shard["name"]: shard
        for shard in (
            planner._ci_contract_shard(),
            planner._manager_review_shard(),
            planner._fable_contract_shard(),
            planner._docs_only_shard(),
        )
    }

    assert originals, "no smoke sources to compare"
    for name, original in originals.items():
        smoke = full.get(f"smoke-{name}")
        assert smoke is not None, f"full plan lost smoke-{name}"
        for field in ("command", "python", "node", "python_dependencies"):
            assert smoke[field] == original[field], (
                f"smoke-{name} {field} drifted from the real {name} shard"
            )


def test_manager_main_partitions_are_disjoint_and_exhaustive():
    """The five -k expressions must together own every Manager main test once.

    Splitting the owner is only safe while this holds. Collection is the
    authority here; reasoning about ``-k`` precedence is not.
    """

    planner = _load_planner()
    expressions = [
        "TestApi and asset",
        "TestApi and not asset",
        *(expression for _, expression, _ in planner.MANAGER_NON_API_PARTITIONS),
    ]

    def collect(*args: str) -> set[str]:
        result = subprocess.run(
            [
                sys.executable, "-m", "pytest",
                "tests/test_workbook_manager.py",
                *args,
                "--collect-only", "-q",
            ],
            cwd=REPO_ROOT, text=True, capture_output=True, check=False,
        )
        nodes = {
            line.strip()
            for line in result.stdout.splitlines()
            if "::" in line and line.strip().startswith("tests/")
        }
        if not nodes:
            # Either the partition selects nothing or the environment cannot
            # import the owner. Both are failures, and both are unreadable as
            # a bare empty set, so report what pytest actually said.
            raise AssertionError(
                "collected no tests from the Manager main owner with "
                f"{list(args) or 'no -k'}; pytest exited {result.returncode}.\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )
        return nodes

    everything = collect()

    owners: dict[str, list[str]] = {}
    for expression in expressions:
        for node in collect("-k", expression):
            owners.setdefault(node, []).append(expression)

    duplicated = {node: owner for node, owner in owners.items() if len(owner) > 1}
    assert not duplicated, f"partitions overlap: {duplicated}"
    assert set(owners) == everything, (
        f"partitions miss {sorted(everything - set(owners))}"
    )
