"""Validation helpers shared by model generators."""

from __future__ import annotations

from typing import Any


def validation_row(
    check_id: str,
    severity: str,
    entity_type: str,
    entity_id: str,
    message: str,
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "severity": severity,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "message": message,
    }


def validation_error_count(rows: list[dict[str, Any]]) -> int:
    return sum(1 for row in rows if row.get("severity") == "error")

