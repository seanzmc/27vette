"""One draft-effective overlay for a projected row plus its coalesced operation.

Checkpoint 2C (audit-spec §5.2, §7 2C): every connected read keeps two explicit
layers — the authored/base projection and the proposed effective value after the
active draft's coalesced operation for that exact physical row. This module is
the single adapter that turns ``(projected row, durable operation, binding
conflicts)`` into that overlay. Connected option/group details, the Sections &
Layout graph nodes, and Asset Manager items all call it; React renders the
result and never re-derives changed fields or state independently.

The adapter is pure: it takes already-loaded rows and operations, reads nothing,
and adds no product knowledge. Identity is the same tuple ``drafts.save_operation``
coalesces on (``source_sheet``, ``family``, ``physical_key``, model scope).
"""

from __future__ import annotations

from typing import Any

STATE_BY_ACTION = {
    "update": "modified",
    "add": "added",
    "delete": "pending_deletion",
}


def unchanged(draft_id: str = "") -> dict[str, Any]:
    """The overlay for a row the active draft does not touch."""
    return {
        "draft_id": draft_id,
        "draft_revision": 0,
        "state": "unchanged",
        "operation": None,
        "base": None,
        "proposed": None,
        "effective": None,
        "changed_fields": {},
        "direct_impact": None,
        "conflicts": [],
    }


def operation_identity(operation: dict[str, Any]) -> dict[str, Any]:
    """The exact durable operation a reviewer can locate in Review & Apply."""
    return {
        "id": int(operation["id"]),
        "action": operation.get("action"),
        "table_name": operation.get("table_name"),
        "family": operation.get("family"),
        "model_id": operation.get("model_id") or "",
        "source_sheet": operation.get("source_sheet") or "",
        "source_row": operation.get("source_row"),
        "physical_key": operation.get("physical_key") or "",
        "entity_key": operation.get("entity_key") or {},
    }


def overlay(
    *,
    draft_id: str,
    operation: dict[str, Any] | None,
    base: dict[str, Any] | None,
    conflicts: list[dict[str, Any]] | None = None,
    direct_impact: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Overlay ``operation`` on ``base``.

    ``conflicts`` (stale binding, terminal draft) come from
    ``drafts.overlay_binding_conflicts`` and produce a ``conflicted`` state whose
    ``effective`` is ``None`` so the authored value is never replaced
    (EFFECTIVE-04). A pending delete keeps ``base`` and reports ``effective``
    ``None`` so the row stays visible with deletion treatment (EFFECTIVE-02).
    """
    if operation is None:
        return unchanged(draft_id)
    action = str(operation.get("action") or "")
    operation_base = (
        operation.get("original") if action == "add"
        else operation.get("original") or base
    )
    proposed = operation.get("final")
    result = {
        "draft_id": draft_id,
        "draft_revision": int(operation["id"]),
        "state": STATE_BY_ACTION[action],
        "operation": operation_identity(operation),
        "base": operation_base,
        "proposed": proposed,
        "effective": proposed if action != "delete" else None,
        "changed_fields": dict(operation.get("changed_fields") or {}),
        "direct_impact": direct_impact,
        "conflicts": [],
    }
    if conflicts:
        result.update({
            "state": "conflicted",
            "effective": None,
            "conflicts": list(conflicts),
        })
    return result


def membership(
    *,
    draft_id: str,
    operation: dict[str, Any],
    field: str,
    before: int,
    after: int,
) -> dict[str, Any]:
    """Overlay for a parent whose membership a child-row operation changed.

    A section gains or loses an option through an ``options`` operation; the
    section's own fields are untouched, so its overlay is ``modified`` and
    carries the exact child operation plus one membership count change rather
    than the child's row diff.
    """
    return {
        **overlay(draft_id=draft_id, operation=operation, base=None),
        "state": "modified",
        "base": None,
        "proposed": None,
        "effective": None,
        "changed_fields": {field: {"before": before, "after": after}},
    }


def matches_row(
    operation: dict[str, Any],
    *,
    source_sheet: str,
    family: str,
    physical_key: str,
    model_key: str,
) -> bool:
    """True when ``operation`` is the coalesced intent for this physical row."""
    return (
        (operation.get("source_sheet") or "") == (source_sheet or "")
        and (operation.get("family") or "") == (family or "")
        and (operation.get("physical_key") or "") == (physical_key or "")
        and (operation.get("model_id") or "") in {"", model_key or ""}
    )
