"""Validated asset decisions routed into the ordinary durable draft lane."""

from __future__ import annotations

import json
import re
import sqlite3
from typing import Any
from urllib.parse import urlparse

from corvette_form_generator.asset_map_sync import AssetManagerSnapshot
from corvette_form_generator.workbook_domain.registry import EDITOR_SHEET_META

from . import drafts
from .catalog import SPEC_BY_TABLE, projection_value


ASSET_FIELDS = {
    "image_url", "image_alt", "image_fit", "image_position",
    "hover_image_url", "hover_image_alt", "hover_image_position",
    "active", "notes",
}
POSITION_FIELDS = {"image_position", "hover_image_position"}
URL_FIELDS = {"image_url", "hover_image_url"}
FIT_VALUES = set(EDITOR_SHEET_META["asset_map"]["enums"]["image_fit"])
POSITION_RE = re.compile(r"^[\w\s.%/-]+$")
RESOLUTION_KINDS = {
    "accept_safe", "select_candidate", "inventory_match", "manual_url",
    "assign_media", "edit", "resolve_wildcard_exact", "resolve_wildcard_shared",
    "deactivate", "ignore",
}


def _item(snapshot: AssetManagerSnapshot, item_id: str) -> dict[str, Any]:
    for item in snapshot.items:
        if item["id"] == item_id:
            return item
    raise drafts.DraftError(
        "asset_item_not_found", f"asset reconciliation item {item_id!r} was not found"
    )


def _validate_url(value: Any, field: str) -> None:
    if value in {None, ""} and field == "hover_image_url":
        return
    parsed = urlparse(str(value or ""))
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise drafts.DraftError(
            "invalid_asset_url", f"{field} must be an absolute http(s) URL"
        )


def _normalize_values(values: dict[str, Any]) -> dict[str, Any]:
    unknown = sorted(set(values) - ASSET_FIELDS)
    if unknown:
        raise drafts.DraftError(
            "unknown_asset_fields",
            f"asset resolution contains unsupported fields: {', '.join(unknown)}",
        )
    if "image_fit" in values and values["image_fit"] not in FIT_VALUES:
        raise drafts.DraftError(
            "invalid_asset_fit",
            f"image_fit must be one of: {', '.join(sorted(FIT_VALUES))}",
        )
    for field in POSITION_FIELDS & set(values):
        value = str(values[field] or "").strip()
        if not value and field == "hover_image_position":
            continue
        if not value or POSITION_RE.fullmatch(value) is None:
            raise drafts.DraftError(
                "invalid_asset_position",
                f"{field} contains a value the runtime sanitizer would reject",
            )
    for field in URL_FIELDS & set(values):
        _validate_url(values[field], field)

    spec = SPEC_BY_TABLE["assets"]
    normalized: dict[str, Any] = {}
    for name, value in values.items():
        column = spec.column_by_name(name)
        assert column is not None
        try:
            normalized[name] = projection_value(column, value)
        except ValueError as exc:
            raise drafts.DraftError("invalid_field_value", str(exc)) from exc
    return normalized


def _check_fingerprints(
    snapshot: AssetManagerSnapshot, fingerprints: dict[str, str]
) -> None:
    if snapshot.fingerprints != fingerprints:
        raise drafts.DraftError(
            "asset_reconciliation_stale",
            "the reviewed workbook or media inventory changed; refresh Asset Manager",
        )


def _target_key(item: dict[str, Any]) -> dict[str, str]:
    current_model = str(item.get("current_values", {}).get("model_key") or "")
    target = item.get("workbook_target") or {}
    return {
        "model_key": current_model or str(target.get("model_key") or ""),
        "target_type": str(target.get("target_type") or item.get("target_type") or ""),
        "target_id": str(target.get("target_id") or item.get("target_id") or ""),
    }


def _asset_evidence(
    *,
    snapshot: AssetManagerSnapshot,
    source_item: dict[str, Any],
    target_item: dict[str, Any],
    resolution_kind: str,
    media_url: str,
    final_values: dict[str, Any] | None,
    explicit_values: dict[str, Any],
) -> dict[str, Any]:
    candidate = source_item.get("candidate") or {}
    return {
        "item_id": source_item["id"],
        "resolution_kind": resolution_kind,
        **snapshot.fingerprints,
        "media_url": media_url,
        "candidate_source": candidate.get("source", ""),
        "candidate_reason": candidate.get("reason", ""),
        "source_status": source_item.get("status", ""),
        "source_kind": source_item.get("kind", ""),
        "target_item_id": target_item.get("id", ""),
        "workbook_target": _target_key(target_item),
        "coverage": target_item.get("coverage", {}),
        "lineage": target_item.get("lineage", {}),
        "candidate": candidate,
        "explicit_values": explicit_values,
        "final_values": final_values,
    }


def _prepare_operation(
    snapshot: AssetManagerSnapshot,
    *,
    item_id: str,
    resolution_kind: str,
    selected_url: str,
    target_item_id: str,
    values: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, str], dict[str, Any], str, dict[str, Any]]:
    if resolution_kind not in RESOLUTION_KINDS - {"ignore"}:
        raise drafts.DraftError(
            "invalid_asset_resolution", f"unsupported resolution {resolution_kind!r}"
        )
    source_item = _item(snapshot, item_id)
    target_item = source_item
    media_url = selected_url.strip()

    if resolution_kind in {"resolve_wildcard_exact", "resolve_wildcard_shared"}:
        if source_item.get("status") != "wildcard_conflict":
            raise drafts.DraftError(
                "asset_resolution_not_wildcard_conflict",
                "ownership resolution requires a wildcard conflict",
            )
        ownership = source_item.get("ownership_resolution") or {}
        operation_name = (
            "exact_operation" if resolution_kind == "resolve_wildcard_exact"
            else "shared_operation"
        )
        operation = ownership.get(operation_name) or {}
        if not operation.get("allowed"):
            raise drafts.DraftError(
                "asset_wildcard_resolution_blocked",
                operation.get("blocked_reason") or "ownership resolution is ambiguous",
            )
        media_url = str(operation.get("candidate_url") or "")
        if resolution_kind == "resolve_wildcard_exact":
            target_item = {
                **source_item,
                "current_values": {},
                "proposed_values": {
                    **(source_item.get("proposed_values") or {}),
                    "image_url": media_url,
                },
            }

    if resolution_kind == "assign_media":
        if source_item.get("status") not in {"unmatched", "unparseable"}:
            raise drafts.DraftError(
                "asset_resolution_not_allowed", "only unmatched media can be assigned"
            )
        target_item = _item(snapshot, target_item_id)
        if target_item.get("kind") != "target":
            raise drafts.DraftError(
                "invalid_asset_target", "media must be assigned to a workbook target"
            )
        media_url = str(source_item.get("proposed_values", {}).get("image_url") or "")
    elif source_item.get("kind") != "target":
        raise drafts.DraftError(
            "asset_resolution_not_allowed", "this media item requires assign or ignore"
        )

    candidate = source_item.get("candidate") or {}
    proposed: dict[str, Any] = {}
    if resolution_kind == "accept_safe":
        if source_item.get("status") != "safe_proposal":
            raise drafts.DraftError(
                "asset_resolution_not_safe", "bulk/individual acceptance is safe proposals only"
            )
        for selected in candidate.get("selected") or []:
            if selected.get("field") in ASSET_FIELDS:
                proposed[selected["field"]] = selected.get("url", "")
        media_url = str(proposed.get("image_url") or proposed.get("hover_image_url") or "")
    elif resolution_kind == "select_candidate":
        if source_item.get("status") != "ambiguous":
            raise drafts.DraftError(
                "asset_resolution_not_ambiguous", "candidate selection requires an ambiguous item"
            )
        alternatives = candidate.get("alternatives") or []
        selected = next((row for row in alternatives if row.get("url") == media_url), None)
        if selected is None:
            raise drafts.DraftError(
                "asset_candidate_not_allowed", "selected URL is not an equal-priority candidate"
            )
        proposed[selected["field"]] = media_url
    elif resolution_kind == "inventory_match":
        if source_item.get("status") != "missing" or media_url not in snapshot.media_urls:
            raise drafts.DraftError(
                "asset_inventory_match_invalid",
                "a missing target must select a URL from the bound inventory",
            )
        proposed["image_url"] = media_url
    elif resolution_kind == "manual_url":
        _validate_url(media_url, "image_url")
        proposed["image_url"] = media_url
    elif resolution_kind == "assign_media":
        proposed["image_url"] = media_url
    elif resolution_kind in {"resolve_wildcard_exact", "resolve_wildcard_shared"}:
        proposed["image_url"] = media_url
    elif resolution_kind == "deactivate":
        if source_item.get("status") != "stale_target":
            raise drafts.DraftError(
                "asset_deactivation_not_stale", "only a stale target can use this action"
            )
        proposed["active"] = False
    elif resolution_kind == "edit":
        if not target_item.get("current_values", {}).get("model_key"):
            raise drafts.DraftError(
                "asset_edit_requires_row", "presentation editing requires an existing asset row"
            )

    proposed.update(values)
    current_values = target_item.get("current_values") or {}
    proposed = {
        name: value for name, value in proposed.items()
        if not (value in {"", None} and current_values.get(name, "") in {"", None})
    }
    normalized = _normalize_values(proposed)
    key = _target_key(target_item)
    if not all(key.values()):
        raise drafts.DraftError(
            "invalid_asset_target", "asset resolution has no complete workbook target"
        )
    current_exists = bool(target_item.get("current_values", {}).get("model_key"))
    op = "update" if current_exists else "add"
    if op == "add":
        base = {
            name: value
            for name, value in (target_item.get("proposed_values") or {}).items()
            if name in ASSET_FIELDS or name in key
        }
        base.update(key)
        base.update(normalized)
        base.setdefault("image_alt", target_item.get("label", ""))
        base.setdefault("image_fit", "cover")
        base.setdefault("image_position", "center")
        base.setdefault("active", "True")
        normalized = _normalize_values({
            name: value for name, value in base.items() if name in ASSET_FIELDS
        }) | key

    evidence = _asset_evidence(
        snapshot=snapshot,
        source_item=source_item,
        target_item=target_item,
        resolution_kind=resolution_kind,
        media_url=media_url,
        final_values={name: value for name, value in normalized.items() if name in ASSET_FIELDS},
        explicit_values=values,
    )
    return target_item, key, normalized, op, evidence


def save_resolution(
    projection_conn: sqlite3.Connection,
    state_conn: sqlite3.Connection,
    *,
    snapshot: AssetManagerSnapshot,
    projection_state: str,
    base_workbook_sha256: str,
    base_workbook_mtime_ns: str,
    draft_id: str,
    item_id: str,
    resolution_kind: str,
    fingerprints: dict[str, str],
    selected_url: str = "",
    target_item_id: str = "",
    values: dict[str, Any] | None = None,
    session_id: str = "",
    actor: str = "",
    manage_transaction: bool = True,
) -> dict | None:
    _check_fingerprints(snapshot, fingerprints)
    source_item = _item(snapshot, item_id)
    prior_row = state_conn.execute(
        "SELECT * FROM draft_asset_resolutions WHERE draft_id=? AND item_id=?",
        (draft_id, item_id),
    ).fetchone()
    prior_evidence = json.loads(prior_row["evidence_json"]) if prior_row is not None else None
    if resolution_kind == "ignore":
        if source_item.get("status") not in {"unmatched", "unparseable"}:
            raise drafts.DraftError(
                "asset_ignore_not_allowed", "only unmatched/unparseable media can be ignored"
            )
        if prior_evidence is not None and prior_row["resolution_kind"] != "ignore":
            raise drafts.DraftError(
                "asset_resolution_retarget_rejected",
                "this media identity already owns a workbook operation in the draft",
            )
        media_url = str(source_item.get("proposed_values", {}).get("image_url") or "")
        evidence = _asset_evidence(
            snapshot=snapshot,
            source_item=source_item,
            target_item={},
            resolution_kind=resolution_kind,
            media_url=media_url,
            final_values=None,
            explicit_values={},
        )
        return drafts.save_asset_ignore(
            state_conn,
            draft_id=draft_id,
            session_id=session_id,
            actor=actor,
            base_workbook_sha256=base_workbook_sha256,
            base_workbook_mtime_ns=base_workbook_mtime_ns,
            evidence=evidence,
            manage_transaction=manage_transaction,
        )

    _target, key, record, op, evidence = _prepare_operation(
        snapshot,
        item_id=item_id,
        resolution_kind=resolution_kind,
        selected_url=selected_url,
        target_item_id=target_item_id,
        values=values or {},
    )
    if prior_evidence is not None:
        prior_target = prior_evidence.get("workbook_target") or {}
        if prior_row["resolution_kind"] == "ignore" or prior_target != key:
            raise drafts.DraftError(
                "asset_resolution_retarget_rejected",
                "an asset item cannot silently retarget an existing draft operation",
            )
    return drafts.save_operation(
        projection_conn,
        state_conn,
        projection_state=projection_state,
        base_workbook_sha256=base_workbook_sha256,
        base_workbook_mtime_ns=base_workbook_mtime_ns,
        draft_id=draft_id,
        table="assets",
        model_id=key["model_key"],
        op=op,
        key=key,
        record=record,
        session_id=session_id,
        actor=actor,
        asset_evidence=evidence,
        manage_transaction=manage_transaction,
    )


def save_all_safe(
    projection_conn: sqlite3.Connection,
    state_conn: sqlite3.Connection,
    **kwargs,
) -> list[dict]:
    snapshot: AssetManagerSnapshot = kwargs.pop("snapshot")
    fingerprints = kwargs.pop("fingerprints")
    model_scope = str(kwargs.pop("model", "") or "").strip()
    _check_fingerprints(snapshot, fingerprints)
    # Enforce the reconciliation view's visible model scope server-side with
    # the same predicate as filter_asset_manager_snapshot (empty scope = every
    # model), so bulk acceptance stages only what the operator can see.
    safe_items = [
        item for item in snapshot.items
        if item.get("status") == "safe_proposal"
        and (not model_scope or item.get("model_key") == model_scope)
    ]
    results: list[dict] = []
    state_conn.execute("BEGIN IMMEDIATE")
    try:
        for item in safe_items:
            result = save_resolution(
                projection_conn,
                state_conn,
                snapshot=snapshot,
                fingerprints=fingerprints,
                item_id=item["id"],
                resolution_kind="accept_safe",
                manage_transaction=False,
                **kwargs,
            )
            if result is not None:
                results.append(result)
        state_conn.commit()
    except Exception:
        state_conn.rollback()
        raise
    return results
