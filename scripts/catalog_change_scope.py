#!/usr/bin/env python3
"""Classify a validation-catalog edit as selection-changing or additive.

``tests/validation_catalog.json`` used to force the complete validation
inventory on every edit. Adding a gate entry is routine here, so nearly every
pull request paid for the full product suite to describe one new gate.

This pass compares the base and head catalogs on the fields that actually decide
*which* gates run and *what* they run. Removing a gate, or changing an existing
gate's selection fields, still demands the full inventory. A pure addition only
needs the CI contract owners plus the newly declared gate's own command.
"""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path
from typing import Any

# Changing any of these reroutes selection for gates the edit does not name.
# ``suites`` is handled separately: a new gate legitimately joins its suites, and
# that is an addition rather than a reroute of the gates already there.
SELECTION_TOP_LEVEL = ("schema", "ci", "serial_groups")

# Per-gate fields that decide selection or execution. Everything else in a gate
# entry is descriptive: descriptions, dispositions, measured timings, notes,
# baseline results, README pointers, collected counts.
SELECTION_GATE_FIELDS = (
    "command",
    "layer",
    "test_files",
    "changed_surfaces",
    "serial_group",
)


class CatalogScopeError(RuntimeError):
    """Raised when a catalog cannot be compared."""


def _gates(catalog: dict[str, Any], *, label: str) -> dict[str, dict[str, Any]]:
    gates = catalog.get("gates")
    if not isinstance(gates, list):
        raise CatalogScopeError(f"{label} catalog has no gates list")
    result: dict[str, dict[str, Any]] = {}
    for gate in gates:
        if not isinstance(gate, dict) or not isinstance(gate.get("id"), str):
            raise CatalogScopeError(f"{label} catalog contains an unidentified gate")
        gate_id = str(gate["id"])
        if gate_id in result:
            raise CatalogScopeError(f"{label} catalog repeats gate {gate_id!r}")
        result[gate_id] = gate
    return result


def _selection_view(gate: dict[str, Any]) -> dict[str, Any]:
    return {field: gate.get(field) for field in SELECTION_GATE_FIELDS}


def _suite_entries(catalog: dict[str, Any], *, label: str) -> dict[str, dict[str, Any]]:
    suites = catalog.get("suites")
    if not isinstance(suites, list):
        raise CatalogScopeError(f"{label} catalog has no suites list")
    result: dict[str, dict[str, Any]] = {}
    for suite in suites:
        if not isinstance(suite, dict) or not isinstance(suite.get("id"), str):
            raise CatalogScopeError(f"{label} catalog contains an unidentified suite")
        result[str(suite["id"])] = suite
    return result


def _without(tokens: list[str], removable: set[str]) -> list[str]:
    return [token for token in tokens if token not in removable]


def _suite_change_is_additive(
    base_suite: dict[str, Any],
    head_suite: dict[str, Any],
    *,
    added_gate_ids: set[str],
    added_test_files: set[str],
) -> bool:
    """True when a suite only gained the newly declared gates."""

    base_ids = list(base_suite.get("gate_ids") or [])
    head_ids = list(head_suite.get("gate_ids") or [])
    if _without(head_ids, added_gate_ids) != base_ids:
        return False

    for field in set(base_suite) | set(head_suite):
        if field in {"gate_ids", "command"}:
            continue
        if base_suite.get(field) != head_suite.get(field):
            return False

    base_command = base_suite.get("command")
    head_command = head_suite.get("command")
    if base_command == head_command:
        return True
    if not isinstance(base_command, str) or not isinstance(head_command, str):
        return False
    return _without(shlex.split(head_command), added_test_files) == shlex.split(
        base_command
    )


def classify(base: dict[str, Any] | None, head: dict[str, Any]) -> dict[str, Any]:
    """Return the validation scope a catalog edit requires."""

    def full(reason: str) -> dict[str, Any]:
        return {"full": True, "reason": reason, "added_gate_ids": []}

    if base is None:
        return full("no base catalog to compare against")

    for key in SELECTION_TOP_LEVEL:
        if base.get(key) != head.get(key):
            return full(f"selection metadata changed: {key}")

    base_gates = _gates(base, label="base")
    head_gates = _gates(head, label="head")

    removed = sorted(set(base_gates) - set(head_gates))
    if removed:
        return full("gate(s) removed: " + ", ".join(removed))

    retargeted = sorted(
        gate_id
        for gate_id in set(base_gates) & set(head_gates)
        if _selection_view(base_gates[gate_id]) != _selection_view(head_gates[gate_id])
    )
    if retargeted:
        return full("gate selection fields changed: " + ", ".join(retargeted))

    added = sorted(set(head_gates) - set(base_gates))
    added_test_files = {
        path
        for gate_id in added
        for path in head_gates[gate_id].get("test_files") or []
    }

    base_suites = _suite_entries(base, label="base")
    head_suites = _suite_entries(head, label="head")
    if sorted(base_suites) != sorted(head_suites):
        return full("suite inventory changed")
    for suite_id in sorted(base_suites):
        if base_suites[suite_id] == head_suites[suite_id]:
            continue
        if not _suite_change_is_additive(
            base_suites[suite_id],
            head_suites[suite_id],
            added_gate_ids=set(added),
            added_test_files=added_test_files,
        ):
            return full(f"suite membership changed beyond the added gate(s): {suite_id}")

    if added:
        return {
            "full": False,
            "reason": "gate(s) added: " + ", ".join(added),
            "added_gate_ids": added,
        }
    return {
        "full": False,
        "reason": "descriptive catalog fields only",
        "added_gate_ids": [],
    }


def _load(path: Path | None, *, label: str) -> dict[str, Any] | None:
    if path is None:
        return None
    if str(path) == "-":
        text = sys.stdin.read()
    else:
        if not path.is_file():
            return None
        text = path.read_text(encoding="utf-8")
    if not text.strip():
        return None
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError as error:
        raise CatalogScopeError(f"{label} catalog is not valid JSON: {error}") from error
    if not isinstance(loaded, dict):
        raise CatalogScopeError(f"{label} catalog is not a JSON object")
    return loaded


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base",
        type=Path,
        help="base-revision catalog; '-' reads stdin. Missing or empty means full.",
    )
    parser.add_argument("--head", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    head = _load(args.head, label="head")
    if head is None:
        raise CatalogScopeError(f"head catalog is missing: {args.head}")
    print(json.dumps(classify(_load(args.base, label="base"), head), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
