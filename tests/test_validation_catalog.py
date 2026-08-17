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

# Directories under tests/ that hold helpers or fixtures rather than gates.
# Discovery walks recursively so a future tests/unit/test_*.py cannot slip in
# uncataloged — `pytest tests/` would collect it while a flat scan would not.
NON_GATE_DIRS = {"lib", "fixtures", "__pycache__"}

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
    # Conditions 3 and 4 are defined in terms of these two. A gate that omits
    # them would otherwise be skipped by the very checks that police it.
    "generates",
    "hashes_protected_roots",
)

# A gate that writes generated output must name a concrete disposable location.
# `read_only` and `in_process` are not isolated *output* declarations — they are
# claims that there is no output — so a generating gate may not use them.
ISOLATED_OUTPUT_KINDS = {
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


def _discover_test_files() -> set[str]:
    """Every gate file on disk, as repo-relative paths.

    Recursive on purpose. `pytest tests/` collects nested packages, so a flat
    scan would let tests/unit/test_new.py exist with no catalog entry while the
    completeness check stayed green.
    """
    found: set[str] = set()
    for path in TESTS_DIR.rglob("*"):
        if not path.is_file():
            continue
        if NON_GATE_DIRS & set(path.relative_to(TESTS_DIR).parts[:-1]):
            continue
        if path.name in NON_GATE_FILES:
            continue
        if not (path.name.endswith(".test.mjs") or path.name.startswith("test_")):
            continue
        if path.suffix not in {".mjs", ".py"}:
            continue
        found.add(path.relative_to(REPO_ROOT).as_posix())
    return found


def _suite_member_gate_ids(catalog: dict, suite: dict) -> set[str]:
    """The gates a suite's command would actually run.

    Derived from the command rather than trusted from `gate_ids`, because an
    empty or short `gate_ids` is exactly how a protected-output gate slips into
    a suite that claims it can run in parallel.
    """
    owners = _gate_test_files(catalog)
    command = suite["command"]

    # `/` is in the path class so an explicit nested path (tests/unit/test_x.py)
    # is derived rather than silently under-counted.
    files = set(re.findall(r"tests/[\w./\-]+\.(?:py|mjs)", command))
    if re.search(r"tests/\*\.test\.mjs", command):
        files |= {path for path in owners if path.endswith(".test.mjs")}
    if re.search(r"pytest\s+tests/(?:\s|$)", command):
        files |= {path for path in owners if path.endswith(".py")}

    return {owners[path] for path in files if path in owners}


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
        # Typed, not merely present. `null` would satisfy a presence check and
        # then make conditions 3 and 4 skip the gate on their falsy guard.
        for flag in ("generates", "hashes_protected_roots"):
            assert isinstance(gate[flag], bool), (
                f"{gate['id']} declares {flag}={gate[flag]!r}; it must be a bool, "
                "because the isolation and serialization checks branch on it"
            )


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
    on_disk = _discover_test_files()
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
        exceptions = " ".join(gate.get("isolation_exceptions", []))
        for path in gate["writes"]:
            assert not path.startswith(tracked_roots), (
                f"{gate['id']} declares a write to the tracked generated surface: {path}"
            )
            # A write that is not under a temporary root is a real side effect on
            # the invocation directory. It may be acceptable, but it has to be
            # declared, or `isolation` reads as "nothing lands outside a temp dir"
            # to whatever schedules this gate later.
            if path.startswith("<") or path.startswith("/tmp/"):
                continue
            assert path in exceptions, (
                f"{gate['id']} writes {path!r}, which is not under a temporary root and is not "
                "listed in isolation_exceptions"
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


def test_suite_gate_ids_match_what_the_command_would_run(catalog):
    """A suite cannot under-declare its membership.

    `gate_ids` is what the serial check reads, so an empty or short list makes
    that check vacuous — `pytest tests/` with `gate_ids: []` would pass as
    parallel-safe while collecting a gate that hashes the protected roots.
    """
    for suite in catalog["suites"]:
        expected = _suite_member_gate_ids(catalog, suite)

        if not suite.get("membership_derivable", True):
            # An opt-out has to say why, or it is just the empty list again
            # wearing a different name.
            assert suite.get("membership_note", "").strip(), (
                f"{suite['id']} opts out of command-derived membership without a stated reason"
            )
            continue

        # An unparseable command must not skip the check: that is the same
        # "empty value makes the rule vacuous" hole, one level up.
        assert expected, (
            f"{suite['id']} declares derivable membership but its command parsed no gates: "
            f"{suite['command']!r}"
        )

        missing = sorted(expected - set(suite["gate_ids"]))
        extra = sorted(set(suite["gate_ids"]) - expected)
        assert not missing, f"{suite['id']} command runs gates it does not declare: {missing}"
        assert not extra, f"{suite['id']} declares gates its command does not run: {extra}"


def test_suites_containing_protected_gates_require_serial_execution(catalog):
    by_id = {gate["id"]: gate for gate in catalog["gates"]}
    for suite in catalog["suites"]:
        # Union of declared and command-derived membership: neither side alone
        # can hide a protected gate from this check.
        members = set(suite["gate_ids"]) | _suite_member_gate_ids(catalog, suite)
        protected = sorted(
            gate_id for gate_id in members if by_id[gate_id]["hashes_protected_roots"]
        )
        if protected:
            assert suite["serial_required"], (
                f"{suite['id']} contains protected-output gates {protected} "
                "but is not marked serial_required"
            )


# --- §7 condition 5: README agrees with the catalog ------------------------


def test_readme_command_blocks_match_the_catalog_command(catalog, readme_text):
    """AGENTS.md §3: README owns exact commands. Where it publishes one as a
    runnable block, the catalog's `command` must be that same string.

    The weaker `readme_reference` check below only asks that a substring appear,
    so changing an interpreter, a flag, or a path on `command` would not move
    it. This one compares the whole command.
    """
    normalized = _normalize(readme_text)
    mismatched = [
        (entry["id"], entry["command"])
        for entry in list(catalog["gates"]) + list(catalog["suites"])
        if entry.get("readme_publishes_command")
        and _normalize(entry["command"]) not in normalized
    ]
    assert not mismatched, (
        f"catalog commands README is supposed to publish verbatim but does not: {mismatched}"
    )


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
    """README states its tables are the complete set of tests/*.test.mjs.

    Discovery is recursive for the same reason the completeness check is: a
    nested gate that README never lists is the failure this is meant to catch.
    """
    normalized = _normalize(readme_text)
    missing = sorted(
        path.rsplit("/", 1)[-1].removesuffix(".test.mjs")
        for path in _discover_test_files()
        if path.endswith(".test.mjs")
        and path.rsplit("/", 1)[-1].removesuffix(".test.mjs") not in normalized
    )
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

    # condition 3, the subtler half: `in_process` is a claim that there is no
    # output at all, so it must not satisfy a generating gate.
    mutated = copy_catalog()
    next(g for g in mutated["gates"] if g["generates"])["isolation"] = "in_process"
    with pytest.raises(AssertionError):
        test_generating_gates_declare_isolated_output(mutated)

    # An undeclared write to the invocation directory is a side effect the
    # isolation kind does not describe.
    mutated = copy_catalog()
    stray = next(g for g in mutated["gates"] if g["generates"])
    stray["writes"] = list(stray["writes"]) + ["./some-report.json"]
    stray.pop("isolation_exceptions", None)
    with pytest.raises(AssertionError):
        test_generating_gates_declare_isolated_output(mutated)

    # condition 4: a protected-output gate loses its serial group
    mutated = copy_catalog()
    protected = next(g for g in mutated["gates"] if g["hashes_protected_roots"])
    protected["serial_group"] = None
    with pytest.raises(AssertionError):
        test_protected_output_gates_are_serialized(mutated)

    # condition 4 at suite level: a suite that runs a protected gate is marked
    # parallel. This is the case the original check could not see, because
    # emptying gate_ids made it vacuously true.
    mutated = copy_catalog()
    suite = next(
        s
        for s in mutated["suites"]
        if any(
            g["hashes_protected_roots"]
            for g in mutated["gates"]
            if g["id"] in _suite_member_gate_ids(mutated, s)
        )
    )
    suite["serial_required"] = False
    with pytest.raises(AssertionError):
        test_suites_containing_protected_gates_require_serial_execution(mutated)

    # ...and emptying its membership no longer hides that.
    suite["gate_ids"] = []
    with pytest.raises(AssertionError):
        test_suites_containing_protected_gates_require_serial_execution(mutated)
    with pytest.raises(AssertionError):
        test_suite_gate_ids_match_what_the_command_would_run(mutated)

    # A command the deriver cannot parse must not skip the membership check —
    # that would restore the vacuous case one level up.
    mutated = copy_catalog()
    blind = mutated["suites"][0]
    blind["command"] = "./scripts/run-everything.sh"
    blind["gate_ids"] = []
    with pytest.raises(AssertionError):
        test_suite_gate_ids_match_what_the_command_would_run(mutated)

    # Opting out of derivation requires a stated reason.
    blind["membership_derivable"] = False
    with pytest.raises(AssertionError):
        test_suite_gate_ids_match_what_the_command_would_run(mutated)

    # A null flag satisfies presence and then turns conditions 3 and 4 off.
    mutated = copy_catalog()
    mutated["gates"][0]["hashes_protected_roots"] = None
    with pytest.raises(AssertionError):
        test_every_gate_declares_the_required_fields(mutated)

    # condition 5: README disagreement, both directions
    mutated = copy_catalog()
    published = next(g for g in mutated["gates"] if g.get("readme_reference"))
    published["readme_reference"] = "a command README does not publish"
    with pytest.raises(AssertionError):
        test_readme_publishes_every_catalog_command_it_claims(mutated, README_PATH.read_text())

    mutated = copy_catalog()
    published = next(g for g in mutated["gates"] if g.get("readme_publishes_command"))
    published["command"] = published["command"] + " --a-flag-readme-does-not-publish"
    with pytest.raises(AssertionError):
        test_readme_command_blocks_match_the_catalog_command(mutated, README_PATH.read_text())

    with pytest.raises(AssertionError):
        test_readme_does_not_hand_maintain_a_collection_count("README says 678 tests collected.")
    with pytest.raises(AssertionError):
        test_readme_layer_names_are_catalog_layers(catalog, "run the Layer 9 gates")
    with pytest.raises(AssertionError):
        test_readme_lists_every_node_gate("this README lists nothing")
