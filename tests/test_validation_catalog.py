#!/usr/bin/env python3
"""Contract test for the machine-readable validation catalog.

Spec: docs/superpowers/specs/2026-08-17-fast-layered-validation-suite.md §7.

A catalog nobody enforces is a stale document. These tests are the enforcement
half. §7 names five conditions that must fail the build; each one has a test
below whose name ends in the condition it owns, plus a mutation test that proves
the check can actually fire (a check only ever observed passing is not a check).

The catalog is dependency-free JSON on purpose: everything here uses the
standard library so the contract holds wherever pytest runs.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = REPO_ROOT / "tests" / "validation_catalog.json"
README_PATH = REPO_ROOT / "README.md"
TESTS_DIR = REPO_ROOT / "tests"

# Files under tests/ that are helpers or data, not gates. Everything else must
# be cataloged. Keep this list short and explicit — an unexplained exemption is
# how a gate silently leaves the catalog.
NON_GATE_FILES = {
    "workbook_domain_fixtures.py",
}

REQUIRED_GATE_FIELDS = (
    "id",
    "command",
    "test_files",
    "layer",
    "primary_authority",
    "changed_surfaces",
    "reads",
    "writes",
    "isolation",
    "serial_group",
    "ci_policy",
    "checkpoint_policy",
    "approximate_seconds",
    "acceptance_locks",
    "disposition",
    "disposition_reason",
    "collected_tests",
    "baseline_result",
)

ISOLATED_OUTPUT_KINDS = {
    "read_only",
    "in_process",
    "tmp_path_fixture",
    "temp_output_root",
    "temp_workbook_copy",
}

PROTECTED_SERIAL_GROUP = "protected_artifacts"


@pytest.fixture(scope="module")
def catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def readme_text() -> str:
    return README_PATH.read_text(encoding="utf-8")


def _normalize(text: str) -> str:
    """Collapse whitespace so a backslash-continued README command still matches."""
    return re.sub(r"\s+", " ", text.replace("\\\n", " ")).strip()


def _gate_test_files(catalog: dict) -> dict[str, str]:
    """Map each test file to the single gate id that owns it."""
    owners: dict[str, str] = {}
    for gate in catalog["gates"]:
        for path in gate["test_files"]:
            owners.setdefault(path, gate["id"])
    return owners


# --- structural validity of the catalog itself -----------------------------


def test_catalog_is_dependency_free_json():
    data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    assert data["schema"] == "27vette-validation-catalog-1"
    for key in ("enums", "baseline", "acceptance_locks", "gates", "suites", "coverage_ledger"):
        assert key in data, f"catalog is missing required top-level key {key!r}"


def test_every_gate_declares_the_required_fields(catalog):
    enums = catalog["enums"]
    seen_ids = set()
    for gate in catalog["gates"]:
        for field in REQUIRED_GATE_FIELDS:
            assert field in gate, f"{gate.get('id')} is missing {field!r}"
        assert gate["id"] not in seen_ids, f"duplicate gate id {gate['id']!r}"
        seen_ids.add(gate["id"])
        assert gate["layer"] in enums["layer"], gate["id"]
        assert gate["primary_authority"] in enums["primary_authority"], gate["id"]
        assert gate["isolation"] in enums["isolation"], gate["id"]
        assert gate["ci_policy"] in enums["ci_policy"], gate["id"]
        assert gate["checkpoint_policy"] in enums["checkpoint_policy"], gate["id"]
        assert gate["disposition"] in enums["disposition"], gate["id"]
        assert gate["disposition_reason"].strip(), f"{gate['id']} has an empty disposition reason"


def test_every_gate_declares_exactly_one_primary_authority(catalog):
    """§4: a gate may supply secondary evidence but is counted once."""
    for gate in catalog["gates"]:
        assert isinstance(gate["primary_authority"], str), gate["id"]


def test_suite_and_ledger_references_resolve(catalog):
    gate_ids = {gate["id"] for gate in catalog["gates"]}
    lock_ids = {lock["id"] for lock in catalog["acceptance_locks"]}

    for suite in catalog["suites"]:
        for gate_id in suite["gate_ids"]:
            assert gate_id in gate_ids, f"{suite['id']} references unknown gate {gate_id!r}"

    for entry in catalog["coverage_ledger"]:
        owner = entry["primary_owner"]
        assert owner is None or owner in gate_ids, (
            f"coverage ledger entry {entry['behavior']!r} names unknown owner {owner!r}"
        )
        for gate_id in entry["secondary_evidence"]:
            assert gate_id in gate_ids, (
                f"coverage ledger entry {entry['behavior']!r} names unknown gate {gate_id!r}"
            )

    for gate in catalog["gates"]:
        for lock_id in gate["acceptance_locks"]:
            assert lock_id in lock_ids, f"{gate['id']} names unknown acceptance lock {lock_id!r}"

    for lock in catalog["acceptance_locks"]:
        owner = lock["primary_owner"]
        assert owner is None or owner in gate_ids, (
            f"acceptance lock {lock['id']!r} names unknown owner {owner!r}"
        )
        for gate_id in lock["restated_by"]:
            assert gate_id in gate_ids, (
                f"acceptance lock {lock['id']!r} names unknown restating gate {gate_id!r}"
            )


# --- §7 condition 1: no uncataloged default/checkpoint test file -----------


def test_every_test_file_has_a_catalog_entry(catalog):
    owners = _gate_test_files(catalog)
    on_disk = {
        f"tests/{path.name}"
        for path in TESTS_DIR.iterdir()
        if path.is_file()
        and path.name not in NON_GATE_FILES
        and (path.name.endswith(".test.mjs") or path.name.startswith("test_"))
        and path.suffix in {".mjs", ".py"}
    }
    uncataloged = sorted(on_disk - set(owners))
    assert not uncataloged, f"test files with no catalog entry: {uncataloged}"

    missing_on_disk = sorted(set(owners) - on_disk)
    assert not missing_on_disk, f"catalog names test files that do not exist: {missing_on_disk}"


def test_no_test_file_is_claimed_by_two_gates(catalog):
    claims: dict[str, list[str]] = {}
    for gate in catalog["gates"]:
        for path in gate["test_files"]:
            claims.setdefault(path, []).append(gate["id"])
    doubled = {path: ids for path, ids in claims.items() if len(ids) > 1}
    assert not doubled, f"test files claimed by more than one gate: {doubled}"


# --- §7 condition 2: one acceptance lock, one primary owner ----------------


def test_no_two_gates_claim_the_same_acceptance_lock(catalog):
    claims: dict[str, list[str]] = {}
    for gate in catalog["gates"]:
        for lock_id in gate["acceptance_locks"]:
            claims.setdefault(lock_id, []).append(gate["id"])
    doubled = {lock: ids for lock, ids in claims.items() if len(ids) > 1}
    assert not doubled, f"acceptance locks with more than one primary owner: {doubled}"


def test_declared_lock_owner_matches_the_owning_gate(catalog):
    by_id = {gate["id"]: gate for gate in catalog["gates"]}
    for lock in catalog["acceptance_locks"]:
        owner = lock["primary_owner"]
        if owner is None:
            continue
        if lock["status"] != "established":
            # Proposed and superseded locks are recorded for classification only;
            # §12 requires approval before a proposed lock becomes a real one.
            continue
        assert lock["id"] in by_id[owner]["acceptance_locks"], (
            f"lock {lock['id']!r} names {owner!r} as owner, but that gate does not claim it"
        )


def test_every_lock_records_why_generic_detection_is_insufficient(catalog):
    """§4.4: a lock without a stated reason is a literal wearing a badge."""
    for lock in catalog["acceptance_locks"]:
        for field in (
            "decision",
            "authoritative_source",
            "why_generic_detection_insufficient",
            "approval_to_change",
        ):
            assert str(lock[field]).strip(), f"acceptance lock {lock['id']!r} has an empty {field}"


# --- §7 condition 3: generating gates declare isolated output --------------


def test_generating_gates_declare_isolated_output(catalog):
    tracked_roots = ("form-output/", "form-app/")
    for gate in catalog["gates"]:
        if not gate["generates"]:
            continue
        assert gate["isolation"] in ISOLATED_OUTPUT_KINDS, (
            f"{gate['id']} generates but declares isolation {gate['isolation']!r}"
        )
        assert gate["isolation"] != "read_only", f"{gate['id']} generates but is declared read_only"
        assert gate["writes"], f"{gate['id']} generates but declares no output location"
        for path in gate["writes"]:
            assert not path.startswith(tracked_roots), (
                f"{gate['id']} declares a write to the tracked generated surface: {path}"
            )


# --- §7 condition 4: protected-output gates are not run in parallel --------


def test_protected_output_gates_are_serialized(catalog):
    for gate in catalog["gates"]:
        if not gate["hashes_protected_roots"]:
            continue
        assert gate["serial_group"] == PROTECTED_SERIAL_GROUP, (
            f"{gate['id']} hashes the protected roots but declares serial_group "
            f"{gate['serial_group']!r}; a concurrent writer is reported as its own violation"
        )


def test_suites_containing_protected_gates_require_serial_execution(catalog):
    by_id = {gate["id"]: gate for gate in catalog["gates"]}
    for suite in catalog["suites"]:
        protected = [
            gate_id for gate_id in suite["gate_ids"] if by_id[gate_id]["hashes_protected_roots"]
        ]
        if protected:
            assert suite["serial_required"], (
                f"{suite['id']} contains protected-output gates {protected} "
                "but is not marked serial_required"
            )


# --- §7 condition 5: README agrees with the catalog ------------------------


def test_readme_publishes_every_catalog_command_it_claims(catalog, readme_text):
    normalized = _normalize(readme_text)
    missing = [
        (gate["id"], gate["readme_reference"])
        for gate in catalog["gates"]
        if gate.get("readme_reference")
        and _normalize(gate["readme_reference"]) not in normalized
    ]
    assert not missing, f"catalog entries README does not publish: {missing}"


def test_readme_lists_every_node_gate(readme_text):
    """README states its tables are the complete set of tests/*.test.mjs."""
    normalized = _normalize(readme_text)
    missing = [
        path.name.removesuffix(".test.mjs")
        for path in sorted(TESTS_DIR.glob("*.test.mjs"))
        if path.name.removesuffix(".test.mjs") not in normalized
    ]
    assert not missing, f"node gates missing from the README matrix: {missing}"


def test_readme_does_not_hand_maintain_a_collection_count(readme_text):
    """§7: the catalog owns measured counts; a hand-kept README count goes stale."""
    hits = re.findall(r"\b\d{2,}\s+tests? collected\b", readme_text)
    assert not hits, (
        f"README hand-maintains a pytest collection count {hits}; "
        "that number belongs to tests/validation_catalog.json"
    )


def test_readme_layer_names_are_catalog_layers(catalog, readme_text):
    declared = {str(layer) for layer in catalog["enums"]["layer"]}
    referenced = set(re.findall(r"\bLayer (\d+)\b", readme_text))
    unknown = sorted(referenced - declared)
    assert not unknown, f"README names validation layers the catalog does not define: {unknown}"


# --- proof the checks can fire ---------------------------------------------


def test_checks_fail_on_a_mutated_catalog(catalog):
    """Each §7 condition, forced. A check only observed passing is not a check."""

    def copy_catalog() -> dict:
        return json.loads(json.dumps(catalog))

    # condition 1: drop a gate's file ownership
    mutated = copy_catalog()
    next(g for g in mutated["gates"] if g["test_files"])["test_files"] = []
    with pytest.raises(AssertionError):
        test_every_test_file_has_a_catalog_entry(mutated)

    # condition 2: two gates claim one lock
    mutated = copy_catalog()
    owner = next(g for g in mutated["gates"] if g["acceptance_locks"])
    other = next(g for g in mutated["gates"] if g["id"] != owner["id"])
    other["acceptance_locks"] = list(owner["acceptance_locks"])
    with pytest.raises(AssertionError):
        test_no_two_gates_claim_the_same_acceptance_lock(mutated)

    # condition 3: a generating gate loses its isolated output declaration
    mutated = copy_catalog()
    generating = next(g for g in mutated["gates"] if g["generates"])
    generating["isolation"] = "tracked_write"
    generating["writes"] = ["form-output/runtime/z06-runtime-contract.json"]
    with pytest.raises(AssertionError):
        test_generating_gates_declare_isolated_output(mutated)

    # condition 4: a protected-output gate loses its serial group
    mutated = copy_catalog()
    protected = next(g for g in mutated["gates"] if g["hashes_protected_roots"])
    protected["serial_group"] = None
    with pytest.raises(AssertionError):
        test_protected_output_gates_are_serialized(mutated)

    # condition 5: README disagreement, both directions
    mutated = copy_catalog()
    published = next(g for g in mutated["gates"] if g.get("readme_reference"))
    published["readme_reference"] = "a command README does not publish"
    with pytest.raises(AssertionError):
        test_readme_publishes_every_catalog_command_it_claims(mutated, README_PATH.read_text())
    with pytest.raises(AssertionError):
        test_readme_does_not_hand_maintain_a_collection_count("README says 678 tests collected.")
    with pytest.raises(AssertionError):
        test_readme_layer_names_are_catalog_layers(catalog, "run the Layer 9 gates")
    with pytest.raises(AssertionError):
        test_readme_lists_every_node_gate("this README lists nothing")
