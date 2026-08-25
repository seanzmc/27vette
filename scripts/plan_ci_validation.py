#!/usr/bin/env python3
"""Build a bounded GitHub Actions validation matrix from changed paths.

The catalog-driven runner remains authoritative for workbook, generator,
runtime, editor, and other non-Manager changes. Workbook Manager changes use
narrower owners because its historical ``workbook_manager`` surface expanded
every source edit into the complete shared-fixture checkpoint suite.

Manual full runs preserve complete coverage while splitting the measured heavy
owners into parallel jobs. Every validation job has a 15-minute hard limit.
"""

from __future__ import annotations

import argparse
import json
import shlex
from collections import OrderedDict
from pathlib import Path
from typing import Iterable

MANAGER_ROOT = "workbook-manager/"
MANAGER_FRONTEND_ROOT = "workbook-manager/frontend/"
MANAGER_REVIEW_ROOT = "workbook-manager/review/"
MANAGER_REVIEW_TEST = "tests/test_group_display_label_contract.py"
MANAGER_MAIN_TEST = "tests/test_workbook_manager.py"
MANAGER_TEST_PREFIX = "tests/test_workbook_manager_"
MANAGER_FIXTURE_HELPER = "tests/workbook_manager_fixtures.py"

CI_CONTRACT_COMMAND = (
    ".venv/bin/python -m pytest "
    "tests/test_validation_catalog.py tests/test_run_layered_validation.py "
    "tests/test_codex_finding_disposition.py -q"
)

MANAGER_EXPLORER_NODES = (
    "tests/test_workbook_manager.py::TestApi::"
    "test_connected_option_detail_is_model_scoped_complete_and_read_only",
    "tests/test_workbook_manager.py::TestApi::"
    "test_connected_group_detail_leads_with_description_and_named_members",
    "tests/test_workbook_manager.py::TestApi::"
    "test_cross_entity_search_is_ranked_typed_scoped_and_stable",
    "tests/test_workbook_manager.py::TestApi::"
    "test_named_diagnostics_are_bounded_defined_scoped_and_traceable",
)
MANAGER_BROWSER_NODE = "tests/test_workbook_manager.py::TestPass1BrowserContainment"

# Measured decomposition of the non-API owner (local, 2026-08-24): a 71.01s
# verified-fixture build every shard pays, a 67.91s unchanged comparison export
# that only the acceptance test reads, and a 211.88s changed-overlay export in
# one test. Run unsplit it measures 372.77s locally, roughly 810-890s in CI
# against a 900s job timeout, so these partitions apply to every plan rather
# than only to the full inventory. They must stay disjoint and exhaustive.
MANAGER_OVERLAY_NODE = "test_export_overlays_registry_owned_projection_fields"
MANAGER_NON_API_PARTITIONS = (
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

# These two lists are the complete 17-test candidate-verifier inventory. The
# first shard owns canonical + declared-drift fixtures; the second owns the
# undeclared-drift fixture and fast/early-failure contracts.
CANDIDATE_CANONICAL_NODES = (
    "tests/test_verify_workbook_candidate.py::"
    "test_every_stage_runs_in_order_against_a_candidate_copy",
    "tests/test_verify_workbook_candidate.py::"
    "test_the_touched_model_set_never_reduces_the_generated_set",
    "tests/test_verify_workbook_candidate.py::"
    "test_declaring_drift_moves_it_out_of_unexpected_and_passes",
    "tests/test_verify_workbook_candidate.py::"
    "test_the_canonical_workbook_has_no_undeclared_drift",
    "tests/test_verify_workbook_candidate.py::"
    "test_report_is_machine_readable_with_a_stable_schema_and_field_set",
    "tests/test_verify_workbook_candidate.py::"
    "test_protected_surfaces_are_byte_identical_after_a_passing_and_a_failing_run",
    "tests/test_verify_workbook_candidate.py::"
    "test_the_lane_runs_the_browser_stage_against_a_temporary_registry",
)
CANDIDATE_DRIFT_AND_FAST_NODES = (
    "tests/test_verify_workbook_candidate.py::"
    "test_a_workbook_defect_fails_at_the_earliest_applicable_stage",
    "tests/test_verify_workbook_candidate.py::"
    "test_undeclared_semantic_drift_is_reported_and_fails",
    "tests/test_verify_workbook_candidate.py::"
    "test_all_models_marker_declares_every_model",
    "tests/test_verify_workbook_candidate.py::"
    "test_an_unknown_changed_model_fails_rather_than_being_ignored",
    "tests/test_verify_workbook_candidate.py::"
    "test_drift_detection_ignores_order_but_not_content",
    "tests/test_verify_workbook_candidate.py::"
    "test_the_browser_stage_reads_the_candidate_registry_not_the_published_one",
    "tests/test_verify_workbook_candidate.py::"
    "test_the_harness_override_env_var_is_the_one_the_harness_reads",
    "tests/test_verify_workbook_candidate.py::"
    "test_the_browser_stage_receives_the_already_built_snapshot",
    "tests/test_verify_workbook_candidate.py::"
    "test_protected_surface_hashes_ignore_macos_finder_metadata",
    "tests/test_verify_workbook_candidate.py::"
    "test_the_lane_detects_and_reports_a_protected_path_write",
)

MANAGER_DRAFT_FILES = {
    "workbook-manager/backend/app/drafts.py",
    "workbook-manager/backend/app/staging.py",
}
MANAGER_APPLY_FILES = {"workbook-manager/backend/app/apply_rebuild.py"}
MANAGER_PROJECTION_FILES = {
    "workbook-manager/backend/app/catalog.py",
    "workbook-manager/backend/app/contract_parity.py",
    "workbook-manager/backend/app/db.py",
    "workbook-manager/backend/app/importer.py",
    "workbook-manager/backend/app/projection.py",
    "workbook-manager/backend/app/sync.py",
}
MANAGER_API_FILES = {"workbook-manager/backend/app/config.py"}
MANAGER_READ_FILES = {"workbook-manager/backend/app/explorer.py"}
MANAGER_SUPPORT_TESTS = (
    "tests/test_workbook_manager_catalog.py",
    "tests/test_workbook_manager_import_projection.py",
    "tests/test_workbook_manager_fixtures.py",
    "tests/test_workbook_manager_generated_parity.py",
    "tests/test_workbook_manager_api_concurrency.py",
    "tests/test_workbook_manager_drafts.py",
    "tests/test_workbook_manager_changeset_lifecycle.py",
    "tests/test_workbook_manager_apply_rebuild.py",
)

CI_INFRA_PATHS = {
    ".github/workflows/release-candidate.yml",
    ".github/workflows/codex-finding-disposition.yml",
    ".github/scripts/codex_finding_disposition.py",
    "scripts/catalog_change_scope.py",
    "scripts/plan_ci_validation.py",
    "scripts/run_layered_validation.py",
    "tests/test_catalog_change_scope.py",
    "tests/test_codex_finding_disposition.py",
    "tests/test_run_layered_validation.py",
    "tests/test_validation_catalog.py",
    "tests/validation_catalog.json",
}
GLOBAL_TEST_ENVIRONMENT_PATHS = {"requirements-test.txt", "tests/conftest.py"}
CATALOG_PATH = "tests/validation_catalog.json"
REPO_ROOT = Path(__file__).resolve().parents[1]


def _shard(
    name: str,
    command: str,
    *,
    python: bool = True,
    node: bool = False,
    python_dependencies: str = "project",
    description: str,
) -> dict[str, object]:
    return {
        "name": name,
        "command": command,
        "python": python,
        "node": node,
        "python_dependencies": python_dependencies,
        "description": description,
    }


def _add(
    shards: "OrderedDict[str, dict[str, object]]",
    shard: dict[str, object],
) -> None:
    shards.setdefault(str(shard["name"]), shard)


def _pytest_command(*targets: str, expression: str | None = None) -> str:
    parts = [".venv/bin/python", "-m", "pytest", *targets]
    if expression:
        parts.extend(["-k", expression])
    parts.append("-q")
    return shlex.join(parts)


def _ci_contract_shard() -> dict[str, object]:
    return _shard(
        "ci-contracts",
        CI_CONTRACT_COMMAND,
        python_dependencies="pytest",
        description="Validate catalog, path transport, planner, and workflow contracts.",
    )


def _catalog_gate_shard(
    gate_ids: Iterable[str],
    *,
    repo_root: Path = REPO_ROOT,
) -> dict[str, object]:
    """Run exactly the gates a purely additive catalog edit declared."""

    catalog = json.loads((repo_root / CATALOG_PATH).read_text(encoding="utf-8"))
    by_id = {gate["id"]: gate for gate in catalog["gates"]}
    ordered = sorted(dict.fromkeys(gate_ids))
    missing = [gate_id for gate_id in ordered if gate_id not in by_id]
    if missing:
        raise KeyError("catalog has no gate(s): " + ", ".join(missing))
    return _shard(
        "catalog-new-gates",
        " && ".join(str(by_id[gate_id]["command"]) for gate_id in ordered),
        node=True,
        description="Run the newly declared catalog gate(s): " + ", ".join(ordered),
    )


def _docs_only_shard() -> dict[str, object]:
    return _shard(
        "docs-only",
        'echo "Documentation-only change; no product validation selected."',
        python=False,
        description="Satisfy the required check without provisioning a test toolchain.",
    )


def _fable_contract_shard() -> dict[str, object]:
    return _shard(
        "fable-contracts",
        ".venv/bin/python scripts/validate_fable5_loop.py && "
        ".venv/bin/python -m pytest tests/test_fable5_loop_contract.py -q",
        description="Validate Fable state, receipts, and handoff contracts.",
    )


def _manager_review_shard() -> dict[str, object]:
    return _shard(
        "manager-review-tooling",
        _pytest_command(MANAGER_REVIEW_TEST),
        description=(
            "Run the offline review-tooling owner for workbook-manager/review."
        ),
    )


def _manager_frontend_shard() -> dict[str, object]:
    return _shard(
        "manager-frontend",
        " && ".join(
            (
                "npm --prefix workbook-manager/frontend ci --include=dev",
                "npm --prefix workbook-manager/frontend run build",
                _pytest_command(MANAGER_BROWSER_NODE),
            )
        ),
        node=True,
        description="Build the frontend and validate its shell contracts.",
    )


def _manager_read_explorer_shard() -> dict[str, object]:
    return _shard(
        "manager-read-explorer",
        _pytest_command(*MANAGER_EXPLORER_NODES),
        description="Run only the read-only connected-explorer API acceptance slice.",
    )


def _manager_read_ui_shard() -> dict[str, object]:
    return _shard(
        "manager-read-ui",
        " && ".join(
            (
                "npm --prefix workbook-manager/frontend ci --include=dev",
                "npm --prefix workbook-manager/frontend run build",
                _pytest_command(MANAGER_BROWSER_NODE, *MANAGER_EXPLORER_NODES),
            )
        ),
        node=True,
        description="Build the changed UI and run only its explorer/shell tests.",
    )


def _manager_api_assets_shard() -> dict[str, object]:
    return _shard(
        "manager-api-assets",
        _pytest_command(MANAGER_MAIN_TEST, expression="TestApi and asset"),
        node=True,
        description="Run the asset-focused half of the Manager API owner.",
    )


def _manager_api_core_shard() -> dict[str, object]:
    return _shard(
        "manager-api-core",
        _pytest_command(MANAGER_MAIN_TEST, expression="TestApi and not asset"),
        node=True,
        description="Run the non-asset half of the Manager API owner.",
    )


def _manager_non_api_shards() -> tuple[dict[str, object], ...]:
    return tuple(
        _shard(
            name,
            _pytest_command(MANAGER_MAIN_TEST, expression=expression),
            node=True,
            description=description,
        )
        for name, expression, description in MANAGER_NON_API_PARTITIONS
    )


def _manager_main_shards() -> tuple[dict[str, object], ...]:
    # The prior single-file owner measured 574 seconds locally. These
    # expressions are disjoint and exhaustive, with setup/slowness headroom.
    return (
        _manager_api_assets_shard(),
        _manager_api_core_shard(),
        *_manager_non_api_shards(),
    )


def _manager_projection_shard() -> dict[str, object]:
    return _shard(
        "manager-projection",
        _pytest_command(
            "tests/test_workbook_manager_catalog.py",
            "tests/test_workbook_manager_import_projection.py",
            "tests/test_workbook_manager_fixtures.py",
            "tests/test_workbook_manager_generated_parity.py",
        ),
        node=True,
        description="Validate projection fidelity and generated reconstruction parity.",
    )


def _manager_drafts_shard() -> dict[str, object]:
    return _shard(
        "manager-drafts",
        _pytest_command(
            "tests/test_workbook_manager_drafts.py",
            "tests/test_workbook_manager_changeset_lifecycle.py",
        ),
        description="Validate durable drafts and immutable ChangeSet lifecycle.",
    )


def _manager_apply_boundaries_shard() -> dict[str, object]:
    return _shard(
        "manager-apply-boundaries",
        _pytest_command(
            "tests/test_workbook_manager_api_concurrency.py",
            "tests/test_workbook_manager_apply_rebuild.py",
        ),
        node=True,
        description="Validate concurrency plus guarded Apply/Rebuild boundaries.",
    )


def _manager_full_shards() -> tuple[dict[str, object], ...]:
    return (
        *_manager_main_shards(),
        _manager_projection_shard(),
        _manager_drafts_shard(),
        _manager_apply_boundaries_shard(),
    )


def _full_suite_shards() -> tuple[dict[str, object], ...]:
    ignored = [
        MANAGER_MAIN_TEST,
        *MANAGER_SUPPORT_TESTS,
        "tests/test_verify_workbook_candidate.py",
        "tests/test_editor_ops_apply.py",
        "tests/test_editor_server_write_api.py",
    ]
    core_command = shlex.join(
        [
            ".venv/bin/python",
            "-m",
            "pytest",
            "tests/",
            "-q",
            *(part for path in ignored for part in ("--ignore", path)),
        ]
    )
    product_command = " && ".join(
        (
            ".venv/bin/python scripts/verify_workbook_candidate.py "
            "--workbook stingray_master.xlsx --changed-model '*' "
            "--report candidate-report.json",
            'for f in tests/*.test.mjs; do node --test "$f" || exit 1; done',
            "npm --prefix workbook-manager/frontend ci --include=dev",
            "npm --prefix workbook-manager/frontend run build",
        )
    )
    return (
        _shard(
            "full-product-readiness",
            product_command,
            node=True,
            description="Run composed candidate, Node inventory, and frontend build.",
        ),
        _shard(
            "full-python-core",
            core_command,
            node=True,
            description="Run all Python owners except the measured heavy files below.",
        ),
        _shard(
            "full-python-candidate-canonical",
            _pytest_command(*CANDIDATE_CANONICAL_NODES),
            node=True,
            description="Run canonical and declared-drift candidate fixtures.",
        ),
        _shard(
            "full-python-candidate-drift-and-fast",
            _pytest_command(*CANDIDATE_DRIFT_AND_FAST_NODES),
            node=True,
            description="Run undeclared drift plus fast/early-failure contracts.",
        ),
        _shard(
            "full-python-editor-ops",
            _pytest_command("tests/test_editor_ops_apply.py"),
            node=True,
            description="Run the expensive editor operations owner independently.",
        ),
        _shard(
            "full-python-editor-server",
            _pytest_command("tests/test_editor_server_write_api.py"),
            node=True,
            description="Run the expensive editor server write owner independently.",
        ),
        *_manager_full_shards(),
    )


def _is_documentation(path: str) -> bool:
    return path in {"README.md", "AGENTS.md"} or path.endswith(".md")


def _is_ci_infrastructure(path: str) -> bool:
    return path in CI_INFRA_PATHS or path.startswith(".github/")


def _direct_manager_test_shard(path: str) -> dict[str, object]:
    name = Path(path).stem.removeprefix("test_").replace("_", "-")
    return _shard(
        f"changed-{name}",
        _pytest_command(path),
        node=True,
        description=f"Run the directly changed Manager test owner {path}.",
    )


def plan_validation(
    changed_paths: Iterable[str],
    *,
    full: bool = False,
    catalog_gate_ids: Iterable[str] = (),
) -> dict[str, object]:
    """Return a deterministic, de-duplicated GitHub matrix plan."""

    paths = tuple(dict.fromkeys(path.strip() for path in changed_paths if path.strip()))
    catalog_gates = tuple(
        dict.fromkeys(gate.strip() for gate in catalog_gate_ids if gate.strip())
    )
    if full or GLOBAL_TEST_ENVIRONMENT_PATHS.intersection(paths):
        return {
            "include": list(_full_suite_shards()),
            "changed_paths": list(paths),
            "full": True,
        }

    # workbook-manager/review holds offline review tooling and its reviewed
    # CSV/JSON evidence. No Manager runtime test imports it, so it must not
    # reach the unclassified-source escalation below; it owns one focused test.
    manager_review_paths = {
        path
        for path in paths
        if path.startswith(MANAGER_REVIEW_ROOT) and not _is_documentation(path)
    }
    manager_source_paths = {
        path
        for path in paths
        if path.startswith(MANAGER_ROOT)
        and not path.startswith(MANAGER_REVIEW_ROOT)
        and not _is_documentation(path)
    }
    manager_test_paths = {
        path
        for path in paths
        if path == MANAGER_MAIN_TEST
        or (path.startswith(MANAGER_TEST_PREFIX) and path.endswith(".py"))
    }
    manager_fixture_changed = MANAGER_FIXTURE_HELPER in paths
    fable_changed = any(path.startswith("fable5loop/") for path in paths)
    ci_changed = any(_is_ci_infrastructure(path) for path in paths)

    layered_paths = [
        path
        for path in paths
        if path not in manager_source_paths
        and path not in manager_review_paths
        and path not in manager_test_paths
        and path != MANAGER_FIXTURE_HELPER
        and not path.startswith("fable5loop/")
        and not _is_ci_infrastructure(path)
        and not _is_documentation(path)
    ]

    shards: "OrderedDict[str, dict[str, object]]" = OrderedDict()
    # The catalog runner already runs both CI contract owners as always-gates.
    if not layered_paths and (
        ci_changed
        or manager_source_paths
        or manager_test_paths
        or manager_fixture_changed
    ):
        _add(shards, _ci_contract_shard())

    frontend_changed = any(
        path.startswith(MANAGER_FRONTEND_ROOT) for path in manager_source_paths
    )
    read_changed = bool(manager_source_paths & MANAGER_READ_FILES)
    main_changed = "workbook-manager/backend/app/main.py" in manager_source_paths
    draft_changed = bool(manager_source_paths & MANAGER_DRAFT_FILES)
    apply_changed = bool(manager_source_paths & MANAGER_APPLY_FILES)
    projection_changed = bool(manager_source_paths & MANAGER_PROJECTION_FILES)
    api_changed = bool(manager_source_paths & MANAGER_API_FILES)

    classified_backend = (
        MANAGER_READ_FILES
        | MANAGER_DRAFT_FILES
        | MANAGER_APPLY_FILES
        | MANAGER_PROJECTION_FILES
        | MANAGER_API_FILES
        | {
            "workbook-manager/backend/app/main.py",
            "workbook-manager/backend/app/__init__.py",
        }
    )
    unknown_manager_source = {
        path
        for path in manager_source_paths
        if not path.startswith(MANAGER_FRONTEND_ROOT)
        and path not in classified_backend
    }

    complete_manager_required = bool(
        unknown_manager_source or manager_fixture_changed or apply_changed
    )
    if complete_manager_required:
        if frontend_changed:
            _add(shards, _manager_frontend_shard())
        for shard in _manager_full_shards():
            _add(shards, shard)
        if apply_changed:
            _add(
                shards,
                _shard(
                    "manager-apply-candidate",
                    ".venv/bin/python scripts/verify_workbook_candidate.py "
                    "--workbook stingray_master.xlsx --changed-model '*' "
                    "--report candidate-report.json",
                    node=True,
                    description="Run the composed candidate for Apply/Rebuild changes.",
                ),
            )
    else:
        focused_read = read_changed and not (
            draft_changed or projection_changed or api_changed
        )
        if main_changed and not read_changed:
            api_changed = True
            focused_read = False

        if frontend_changed and focused_read:
            _add(shards, _manager_read_ui_shard())
        else:
            if frontend_changed:
                _add(shards, _manager_frontend_shard())
            if focused_read:
                _add(shards, _manager_read_explorer_shard())

        if api_changed:
            _add(shards, _manager_api_assets_shard())
            _add(shards, _manager_api_core_shard())
        if draft_changed:
            _add(shards, _manager_api_core_shard())
            _add(shards, _manager_drafts_shard())
        if projection_changed:
            _add(shards, _manager_projection_shard())

    # Editing this owner always runs all three partitions. An earlier carve-out
    # skipped them whenever a frontend file was also touched, so adding a file
    # to a diff could remove coverage instead of adding it.
    if MANAGER_MAIN_TEST in manager_test_paths:
        for shard in _manager_main_shards():
            _add(shards, shard)
    for path in sorted(manager_test_paths - {MANAGER_MAIN_TEST}):
        _add(shards, _direct_manager_test_shard(path))

    if catalog_gates:
        _add(shards, _catalog_gate_shard(catalog_gates))

    if manager_review_paths:
        _add(shards, _manager_review_shard())

    if fable_changed:
        _add(shards, _fable_contract_shard())

    if layered_paths:
        command = [
            ".venv/bin/python",
            "scripts/run_layered_validation.py",
            "--report",
            "layered-validation-report.json",
        ]
        for path in layered_paths:
            command.extend(("--changed-file", path))
        _add(
            shards,
            _shard(
                "layered-changed-surfaces",
                shlex.join(command),
                node=True,
                description="Delegate non-Manager changes to the catalog selector.",
            ),
        )

    if manager_source_paths and not any(
        str(shard["name"]).startswith("manager-") for shard in shards.values()
    ):
        for shard in _manager_full_shards():
            _add(shards, shard)

    if not shards:
        _add(shards, _docs_only_shard())

    return {
        "include": list(shards.values()),
        "changed_paths": list(paths),
        "full": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--changed-file-list", type=Path)
    parser.add_argument("--changed-file", action="append", default=[])
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--catalog-gate", action="append", default=[])
    parser.add_argument(
        "--catalog-scope",
        type=Path,
        help="catalog_change_scope.py report; forces --full when it says full",
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    changed = list(args.changed_file)
    if args.changed_file_list and args.changed_file_list.exists():
        changed.extend(args.changed_file_list.read_text(encoding="utf-8").splitlines())
    full = args.full
    catalog_gates = list(args.catalog_gate)
    if args.catalog_scope:
        scope = json.loads(args.catalog_scope.read_text(encoding="utf-8"))
        full = full or bool(scope.get("full"))
        catalog_gates.extend(scope.get("added_gate_ids") or [])
    plan = plan_validation(changed, full=full, catalog_gate_ids=catalog_gates)
    args.output.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(plan, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
