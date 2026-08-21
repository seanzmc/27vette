#!/usr/bin/env python3
"""Build the GitHub Actions validation matrix for one pull request.

The existing catalog-driven runner remains the authority for non-Manager
surfaces. Workbook Manager changes are routed to focused pytest/build shards so
normal UX and read-only API work does not expand the shared-fixture checkpoint
suite. A manual full run uses parallel shards whose individual historical cost
fits inside the 15-minute job limit.
"""

from __future__ import annotations

import argparse
import json
import shlex
from collections import OrderedDict
from pathlib import Path
from typing import Iterable

CI_CONTRACT_COMMAND = (
    ".venv/bin/python -m pytest "
    "tests/test_validation_catalog.py tests/test_run_layered_validation.py -q"
)

MANAGER_ROOT = "workbook-manager/"
MANAGER_FRONTEND_ROOT = "workbook-manager/frontend/"
MANAGER_MAIN_TEST = "tests/test_workbook_manager.py"
MANAGER_TEST_PREFIX = "tests/test_workbook_manager_"

MANAGER_EXPLORER_NODES = (
    "tests/test_workbook_manager.py::TestPass1BrowserContainment::"
    "test_checkpoint_one_shell_is_readiness_first_and_explorers_are_read_only",
    "tests/test_workbook_manager.py::TestApi::"
    "test_connected_option_detail_is_model_scoped_complete_and_read_only",
    "tests/test_workbook_manager.py::TestApi::"
    "test_connected_group_detail_leads_with_description_and_named_members",
    "tests/test_workbook_manager.py::TestApi::"
    "test_cross_entity_search_is_ranked_typed_scoped_and_stable",
    "tests/test_workbook_manager.py::TestApi::"
    "test_named_diagnostics_are_bounded_defined_scoped_and_traceable",
)

# These files own distinct protected boundaries and should never be reduced to
# the read-only explorer slice merely because they live below backend/app.
MANAGER_DRAFT_FILES = {
    "workbook-manager/backend/app/drafts.py",
    "workbook-manager/backend/app/staging.py",
}
MANAGER_APPLY_FILES = {
    "workbook-manager/backend/app/apply_rebuild.py",
}
MANAGER_PROJECTION_FILES = {
    "workbook-manager/backend/app/importer.py",
    "workbook-manager/backend/app/db.py",
    "workbook-manager/backend/app/contract_parity.py",
    "workbook-manager/backend/app/sync.py",
    "workbook-manager/backend/app/projection.py",
}
MANAGER_API_FILES = {
    "workbook-manager/backend/app/config.py",
}
MANAGER_READ_FILES = {
    "workbook-manager/backend/app/explorer.py",
}

CI_INFRA_PATHS = {
    ".github/workflows/release-candidate.yml",
    "scripts/plan_ci_validation.py",
    "scripts/run_layered_validation.py",
    "tests/test_run_layered_validation.py",
    "tests/test_validation_catalog.py",
    "tests/validation_catalog.json",
}


def _shard(
    name: str,
    command: str,
    *,
    python: bool = True,
    node: bool = False,
    description: str,
) -> dict[str, object]:
    return {
        "name": name,
        "command": command,
        "python": python,
        "node": node,
        "description": description,
    }


def _add(shards: "OrderedDict[str, dict[str, object]]", shard: dict[str, object]) -> None:
    shards.setdefault(str(shard["name"]), shard)


def _pytest_command(*targets: str, expression: str | None = None) -> str:
    parts = [".venv/bin/python", "-m", "pytest", *targets]
    if expression:
        parts.extend(["-k", expression])
    parts.append("-q")
    return shlex.join(parts)


def _manager_frontend_shard() -> dict[str, object]:
    return _shard(
        "manager-frontend",
        " && ".join(
            (
                "npm --prefix workbook-manager/frontend ci --include=dev",
                "npm --prefix workbook-manager/frontend run build",
                _pytest_command("tests/test_workbook_manager.py::TestPass1BrowserContainment"),
            )
        ),
        python=True,
        node=True,
        description="Build the changed frontend and validate its readiness-shell containment contracts.",
    )


def _manager_explorer_shard() -> dict[str, object]:
    return _shard(
        "manager-explorer",
        _pytest_command(*MANAGER_EXPLORER_NODES),
        description="Run the read-only connected-explorer API and shell acceptance slice.",
    )


def _manager_api_shard() -> dict[str, object]:
    return _shard(
        "manager-api",
        _pytest_command(MANAGER_MAIN_TEST, expression="TestApi"),
        description="Validate the complete Workbook Manager API class for shared route/config changes.",
    )


def _manager_non_api_shard() -> dict[str, object]:
    return _shard(
        "manager-non-api",
        _pytest_command(MANAGER_MAIN_TEST, expression="not TestApi"),
        description="Validate the non-API half of the large Workbook Manager regression file.",
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
        description="Validate import/projection fidelity and generated-contract reconstruction parity.",
    )


def _manager_boundaries_shard() -> dict[str, object]:
    return _shard(
        "manager-boundaries",
        _pytest_command(
            "tests/test_workbook_manager_api_concurrency.py",
            "tests/test_workbook_manager_drafts.py",
            "tests/test_workbook_manager_changeset_lifecycle.py",
            "tests/test_workbook_manager_apply_rebuild.py",
        ),
        description="Validate concurrency, draft lifecycle, and guarded Apply/Rebuild boundaries.",
    )


def _manager_drafts_shard() -> dict[str, object]:
    return _shard(
        "manager-drafts",
        _pytest_command(
            "tests/test_workbook_manager_drafts.py",
            "tests/test_workbook_manager_changeset_lifecycle.py",
        ),
        description="Validate only the durable draft and immutable ChangeSet lifecycle surfaces.",
    )


def _manager_apply_shard() -> dict[str, object]:
    return _shard(
        "manager-apply-rebuild",
        _pytest_command("tests/test_workbook_manager_apply_rebuild.py"),
        description="Validate the guarded writer, rollback, regeneration, and publication boundary.",
    )


def _manager_full_shards() -> tuple[dict[str, object], ...]:
    return (
        _manager_api_shard(),
        _manager_non_api_shard(),
        _manager_projection_shard(),
        _manager_boundaries_shard(),
    )


def _full_suite_shards() -> tuple[dict[str, object], ...]:
    manager_files = (
        "tests/test_workbook_manager.py",
        "tests/test_workbook_manager_api_concurrency.py",
        "tests/test_workbook_manager_apply_rebuild.py",
        "tests/test_workbook_manager_catalog.py",
        "tests/test_workbook_manager_changeset_lifecycle.py",
        "tests/test_workbook_manager_drafts.py",
        "tests/test_workbook_manager_fixtures.py",
        "tests/test_workbook_manager_generated_parity.py",
        "tests/test_workbook_manager_import_projection.py",
    )
    ignored = [
        *manager_files,
        "tests/test_verify_workbook_candidate.py",
        "tests/test_editor_ops_apply.py",
        "tests/test_editor_server_write_api.py",
        "tests/test_run_layered_validation.py",
        "tests/test_validation_catalog.py",
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
    return (
        _shard(
            "full-release-candidate",
            ".venv/bin/python scripts/verify_workbook_candidate.py "
            "--workbook stingray_master.xlsx --changed-model '*' "
            "--report candidate-report.json",
            python=True,
            node=True,
            description="Run the composed six-model candidate boundary once.",
        ),
        _shard(
            "full-python-core",
            core_command,
            description="Run the full Python inventory except the explicitly separated heavy owners.",
        ),
        _shard(
            "full-python-candidate-tests",
            _pytest_command("tests/test_verify_workbook_candidate.py"),
            description="Run the candidate-verifier acceptance inventory in its own budget.",
        ),
        _shard(
            "full-python-editor-writes",
            _pytest_command(
                "tests/test_editor_ops_apply.py",
                "tests/test_editor_server_write_api.py",
            ),
            description="Run the two expensive guarded editor-write owners together.",
        ),
        *_manager_full_shards(),
        _shard(
            "full-node-inventory",
            "for f in tests/*.test.mjs; do node --test \"$f\"; done",
            python=True,
            node=True,
            description="Run every Node test file serially inside one short shard.",
        ),
        _shard(
            "full-manager-frontend-build",
            "npm --prefix workbook-manager/frontend ci --include=dev && "
            "npm --prefix workbook-manager/frontend run build",
            python=False,
            node=True,
            description="Compile the production Workbook Manager frontend from its lockfile.",
        ),
    )


def _is_documentation(path: str) -> bool:
    if path in {"README.md", "AGENTS.md"}:
        return True
    if path.startswith("docs/"):
        return True
    if path in {"workbook-manager/README.md", "workbook-manager/USER-GUIDE.md"}:
        return True
    if path.startswith("fable5loop/") and path.endswith(".md"):
        return True
    return False


def _is_ci_infrastructure(path: str) -> bool:
    return path in CI_INFRA_PATHS or path.startswith(".github/")


def _direct_manager_test_shard(path: str) -> dict[str, object]:
    name = Path(path).stem.removeprefix("test_").replace("_", "-")
    return _shard(
        f"changed-{name}",
        _pytest_command(path),
        description=f"Run the directly changed Manager test owner {path}.",
    )


def plan_validation(changed_paths: Iterable[str], *, full: bool = False) -> dict[str, object]:
    """Return a GitHub matrix object with deterministic, de-duplicated shards."""

    paths = tuple(dict.fromkeys(path.strip() for path in changed_paths if path.strip()))
    shards: "OrderedDict[str, dict[str, object]]" = OrderedDict()
    _add(
        shards,
        _shard(
            "ci-contracts",
            CI_CONTRACT_COMMAND,
            description="Validate the catalog, path transport, planner, and workflow contracts.",
        ),
    )

    if full or "requirements-test.txt" in paths:
        for shard in _full_suite_shards():
            _add(shards, shard)
        return {
            "include": list(shards.values()),
            "changed_paths": list(paths),
            "full": True,
        }

    manager_source_paths = {
        path for path in paths if path.startswith(MANAGER_ROOT) and not _is_documentation(path)
    }
    manager_test_paths = {
        path
        for path in paths
        if path == MANAGER_MAIN_TEST
        or (path.startswith(MANAGER_TEST_PREFIX) and path.endswith(".py"))
    }

    frontend_changed = any(path.startswith(MANAGER_FRONTEND_ROOT) for path in manager_source_paths)
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
        | {"workbook-manager/backend/app/main.py", "workbook-manager/backend/app/__init__.py"}
    )
    unknown_manager_source = {
        path
        for path in manager_source_paths
        if not path.startswith(MANAGER_FRONTEND_ROOT)
        and path not in classified_backend
    }

    if frontend_changed:
        _add(shards, _manager_frontend_shard())

    # main.py plus explorer.py is the normal shape of a read-only explorer route
    # change. A main.py change without explorer.py runs the complete API class.
    focused_explorer = read_changed and not unknown_manager_source
    if main_changed and not read_changed:
        api_changed = True
    if focused_explorer and not api_changed and not draft_changed and not apply_changed:
        _add(shards, _manager_explorer_shard())
    elif read_changed or api_changed or main_changed:
        _add(shards, _manager_api_shard())

    if draft_changed:
        _add(shards, _manager_drafts_shard())
    if apply_changed:
        # Apply/Rebuild is the protected writer/recovery boundary. Preserve the
        # complete Manager inventory, but split it across isolated jobs so the
        # required wall-clock path remains bounded.
        for shard in _manager_full_shards():
            _add(shards, shard)
        _add(
            shards,
            _shard(
                "manager-apply-candidate",
                ".venv/bin/python scripts/verify_workbook_candidate.py "
                "--workbook stingray_master.xlsx --changed-model '*' "
                "--report candidate-report.json",
                python=True,
                node=True,
                description="Run candidate/publication validation for Apply/Rebuild changes.",
            ),
        )
    if projection_changed:
        _add(shards, _manager_projection_shard())

    if unknown_manager_source:
        for shard in _manager_full_shards():
            _add(shards, shard)

    if MANAGER_MAIN_TEST in manager_test_paths and not manager_source_paths:
        _add(shards, _manager_api_shard())
        _add(shards, _manager_non_api_shard())
    for path in sorted(manager_test_paths - {MANAGER_MAIN_TEST}):
        _add(shards, _direct_manager_test_shard(path))

    layered_paths = [
        path
        for path in paths
        if path not in manager_source_paths
        and path not in manager_test_paths
        and not _is_ci_infrastructure(path)
        and not _is_documentation(path)
    ]
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
                python=True,
                node=True,
                description="Delegate non-Manager changes to the existing catalog-driven selector.",
            ),
        )

    # A manager source file that escaped classification must never result in a
    # green CI run with only the catalog contracts.
    if manager_source_paths and len(shards) == 1:
        for shard in _manager_full_shards():
            _add(shards, shard)

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
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    changed = list(args.changed_file)
    if args.changed_file_list and args.changed_file_list.exists():
        changed.extend(args.changed_file_list.read_text(encoding="utf-8").splitlines())
    plan = plan_validation(changed, full=args.full)
    args.output.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(plan, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
