"""Contract for classifying validation-catalog edits.

Adding a gate entry is routine in this repository. It used to force the entire
validation inventory, so the suite paid for the full product run to describe one
new gate. These tests pin the boundary: additive edits stay cheap, and anything
that reroutes existing selection still demands the full inventory.
"""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "catalog_change_scope.py"
CATALOG = REPO_ROOT / "tests" / "validation_catalog.json"


def _load_scope():
    spec = importlib.util.spec_from_file_location("catalog_change_scope", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def scope():
    return _load_scope()


@pytest.fixture(scope="module")
def catalog() -> dict:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def _gate(catalog: dict, gate_id: str) -> dict:
    return next(gate for gate in catalog["gates"] if gate["id"] == gate_id)


def _added_gate(catalog: dict, gate_id: str = "py.test_new_owner") -> dict:
    """Return a catalog with one new gate wired into its suites, as a real add."""

    head = copy.deepcopy(catalog)
    template = copy.deepcopy(_gate(head, "py.test_codex_finding_disposition"))
    template["id"] = gate_id
    template["test_files"] = ["tests/test_new_owner.py"]
    head["gates"].append(template)
    for suite in head["suites"]:
        if suite["id"] != "suite.full_python_inventory":
            continue
        suite["gate_ids"].append(gate_id)
    return head


def test_an_unchanged_catalog_needs_no_extra_validation(scope, catalog):
    result = scope.classify(catalog, copy.deepcopy(catalog))
    assert result["full"] is False
    assert result["added_gate_ids"] == []


def test_a_missing_base_catalog_fails_closed_to_the_full_inventory(scope, catalog):
    result = scope.classify(None, catalog)
    assert result["full"] is True
    assert "no base catalog" in result["reason"]


def test_a_purely_additive_gate_runs_only_that_gate(scope, catalog):
    result = scope.classify(catalog, _added_gate(catalog))
    assert result["full"] is False
    assert result["added_gate_ids"] == ["py.test_new_owner"]


def test_a_suite_command_gaining_the_added_test_file_stays_additive(scope, catalog):
    head = _added_gate(catalog)
    suite = next(s for s in head["suites"] if s["id"] == "suite.full_python_inventory")
    suite["gate_ids"] = list(suite["gate_ids"])
    for other in head["suites"]:
        if other["id"] != "suite.workbook_manager_serial_group":
            continue
        other["gate_ids"].append("py.test_new_owner")
        other["command"] = other["command"].replace(
            "-m pytest ", "-m pytest tests/test_new_owner.py ", 1
        )
    result = scope.classify(catalog, head)
    assert result["full"] is False
    assert result["added_gate_ids"] == ["py.test_new_owner"]


def test_descriptive_only_edits_stay_narrow(scope, catalog):
    head = copy.deepcopy(catalog)
    gate = _gate(head, "py.test_workbook_truth")
    gate["disposition_reason"] = "reworded for clarity"
    gate["approximate_seconds"] = 99.9
    gate["notes"] = "remeasured"
    result = scope.classify(catalog, head)
    assert result["full"] is False
    assert result["added_gate_ids"] == []


@pytest.mark.parametrize(
    "field, value",
    [
        ("command", ".venv/bin/python -m pytest -k nothing"),
        ("layer", 4),
        ("test_files", []),
        ("changed_surfaces", []),
        ("serial_group", "workbook_manager"),
    ],
)
def test_retargeting_an_existing_gate_requires_the_full_inventory(
    scope, catalog, field, value
):
    head = copy.deepcopy(catalog)
    _gate(head, "py.test_workbook_truth")[field] = value
    result = scope.classify(catalog, head)
    assert result["full"] is True
    assert "py.test_workbook_truth" in result["reason"]


def test_removing_a_gate_requires_the_full_inventory(scope, catalog):
    head = copy.deepcopy(catalog)
    head["gates"].remove(_gate(head, "py.test_workbook_truth"))
    result = scope.classify(catalog, head)
    assert result["full"] is True
    assert "removed" in result["reason"]


@pytest.mark.parametrize("key", ["schema", "ci", "serial_groups"])
def test_selection_metadata_edits_require_the_full_inventory(scope, catalog, key):
    head = copy.deepcopy(catalog)
    head[key] = {"mutated": True} if isinstance(head[key], dict) else "mutated"
    result = scope.classify(catalog, head)
    assert result["full"] is True
    assert key in result["reason"]


def test_dropping_an_always_gate_requires_the_full_inventory(scope, catalog):
    head = copy.deepcopy(catalog)
    head["ci"]["always_gate_ids"].remove("py.test_codex_finding_disposition")
    assert scope.classify(catalog, head)["full"] is True


def test_a_suite_losing_a_gate_requires_the_full_inventory(scope, catalog):
    head = copy.deepcopy(catalog)
    head["suites"][0]["gate_ids"].pop()
    result = scope.classify(catalog, head)
    assert result["full"] is True
    assert "suite membership changed" in result["reason"]


def test_a_suite_command_change_without_a_new_gate_requires_the_full_inventory(
    scope, catalog
):
    head = copy.deepcopy(catalog)
    head["suites"][0]["command"] += " -x"
    assert scope.classify(catalog, head)["full"] is True


def test_removing_a_suite_requires_the_full_inventory(scope, catalog):
    head = copy.deepcopy(catalog)
    head["suites"].pop()
    result = scope.classify(catalog, head)
    assert result["full"] is True
    assert "suite inventory changed" in result["reason"]


def test_an_empty_base_file_fails_closed(scope, catalog, tmp_path):
    empty = tmp_path / "base.json"
    empty.write_text("", encoding="utf-8")
    assert scope._load(empty, label="base") is None


def test_malformed_json_is_reported_not_silently_narrowed(scope, tmp_path):
    broken = tmp_path / "base.json"
    broken.write_text("{not json", encoding="utf-8")
    with pytest.raises(scope.CatalogScopeError):
        scope._load(broken, label="base")


def test_a_duplicated_gate_id_is_rejected(scope, catalog):
    head = copy.deepcopy(catalog)
    head["gates"].append(copy.deepcopy(head["gates"][0]))
    with pytest.raises(scope.CatalogScopeError):
        scope.classify(catalog, head)
