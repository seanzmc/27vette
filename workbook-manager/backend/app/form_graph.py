"""Connected, model-scoped form graph for Workbook Manager Checkpoint 4.

The workbook remains authoritative. This module joins its disposable verified
projection for presentation; it neither reads retained generated artifacts nor
creates a write path. Runtime section edges have three workbook-backed sources:

* active ``context_section_master`` rows (their own step_key is authoritative),
* section_master rows referenced by active model option rows, and
* section_master rows referenced by interiors applicable to the model's active
  trims.

The first two are emitted in fresh runtime ``sections`` metadata. The third is
emitted in fresh runtime ``interiors[].section_id`` metadata and rendered by the
customer runtime's ``base_interior`` step. ``standard_equipment`` remains a
non-navigable bucket, not an invented runtime step.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from collections import defaultdict
from typing import Any

from . import draft_overlay

BUCKET_STEP_KEYS = frozenset({"standard_equipment"})
STRUCTURE_GRAPH_VERSION = "cp4-1"
_TRUE_VALUES = frozenset({"1", "true", "yes", "y"})


def _clean(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _truthy(value: Any) -> bool:
    return _clean(value).lower() in _TRUE_VALUES


def _integer(value: Any, default: int = 9999) -> int:
    try:
        return int(_clean(value))
    except (TypeError, ValueError):
        return default


def _model_context(value: Any) -> set[str]:
    if not value:
        return set()
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
    except (TypeError, ValueError, json.JSONDecodeError):
        return set()
    return {_clean(item).lower() for item in parsed or () if _clean(item)}


def _interior_trim(value: Any) -> str:
    """Return the model-variant trim represented by an interior trim value."""

    return _clean(value).split("_", 1)[0].lower()


def _display_fallback(section_id: str) -> str:
    return _clean(section_id).removeprefix("sec_").replace("_", " ").title()


def build_form_graph(conn, model_key: str) -> dict:
    """Return the complete workbook-backed form graph for ``model_key``."""

    model_key = _clean(model_key).lower()

    def rows(sql: str, params: tuple = ()) -> list[dict]:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]

    all_steps = rows(
        "SELECT * FROM form_steps WHERE model_key=? "
        "ORDER BY CAST(runtime_order AS INTEGER), step_key",
        (model_key,),
    )
    active_steps = [row for row in all_steps if _truthy(row.get("active"))]
    all_presentation = rows(
        "SELECT * FROM section_presentation WHERE model_key=? "
        "ORDER BY CAST(section_display_order AS INTEGER), section_id",
        (model_key,),
    )
    active_presentation = [
        row for row in all_presentation if _truthy(row.get("active"))
    ]
    all_context = rows(
        "SELECT * FROM context_sections WHERE model_key=? "
        "ORDER BY CAST(section_display_order AS INTEGER), section_id",
        (model_key,),
    )
    active_context = [row for row in all_context if _truthy(row.get("active"))]
    all_summary_map = rows(
        "SELECT * FROM step_order_summary_map WHERE model_key=? ORDER BY id",
        (model_key,),
    )
    active_summary_map = [
        row for row in all_summary_map if _truthy(row.get("active"))
    ]
    all_order_summary = rows(
        "SELECT * FROM order_summary_sections WHERE model_key=? "
        "ORDER BY CAST(display_order AS INTEGER), section_key",
        (model_key,),
    )
    active_order_summary = [
        row for row in all_order_summary if _truthy(row.get("active"))
    ]
    section_master = {
        row["section_id"]: dict(row)
        for row in conn.execute("SELECT * FROM form_sections").fetchall()
    }
    # Preserve the endpoint's legacy presentation-row view without changing
    # graph provenance: callers expect blank placement/name cells to be
    # enriched from section_master, while resolution below must still know
    # whether the authored placement came from presentation or master.
    presentation_view = []
    for row in all_presentation:
        view = dict(row)
        master = section_master.get(row.get("section_id"), {})
        view["step_key"] = row.get("step_key") or master.get("step_key")
        view["section_name"] = master.get("section_name", "")
        view["display_name"] = (
            row.get("display_label")
            or master.get("section_name")
            or _clean(row.get("section_id")).replace("_", " ").title()
        )
        presentation_view.append(view)
    variants = rows(
        "SELECT mv.*, vm.trim_level, vm.body_style, vm.display_name, "
        "vm.base_price FROM model_variants mv LEFT JOIN variants vm ON "
        "vm.variant_id=mv.variant_id WHERE mv.model_key=? "
        "ORDER BY CAST(mv.display_order AS INTEGER)",
        (model_key,),
    )
    active_trims = {
        _clean(row.get("trim_level")).lower()
        for row in variants
        if _truthy(row.get("active")) and _clean(row.get("trim_level"))
    }

    presentation_by_section = {
        row["section_id"]: row for row in active_presentation
    }
    any_presentation_by_section = {
        row["section_id"]: row for row in all_presentation
    }
    context_by_section = {row["section_id"]: row for row in active_context}
    any_context_by_section = {row["section_id"]: row for row in all_context}

    all_options = rows(
        "SELECT * FROM options WHERE model_id=? "
        "ORDER BY CAST(display_order AS INTEGER), option_id",
        (model_key,),
    )
    option_counts: dict[str, int] = defaultdict(int)
    options_by_section: dict[str, list[dict]] = defaultdict(list)
    for row in all_options:
        if _clean(row.get("section_id")):
            options_by_section[row["section_id"]].append(row)
        if _truthy(row.get("active")) and _clean(row.get("section_id")):
            option_counts[row["section_id"]] += 1

    all_overrides = rows(
        "SELECT vo.*, v.display_name AS variant_name FROM variant_option_overrides vo "
        "LEFT JOIN variants v ON v.variant_id=vo.variant_id WHERE vo.model_id=? "
        "ORDER BY vo.id",
        (model_key,),
    )
    overrides_by_section: dict[str, list[dict]] = defaultdict(list)
    for row in all_overrides:
        if _clean(row.get("section_id")):
            overrides_by_section[row["section_id"]].append(row)

    interior_counts: dict[str, int] = defaultdict(int)
    for row in conn.execute(
        "SELECT section_id, trim, active_for_stingray, model_context "
        "FROM interiors WHERE section_id IS NOT NULL AND section_id != ''"
    ).fetchall():
        if model_key not in _model_context(row["model_context"]):
            continue
        if model_key == "stingray" and not _truthy(row["active_for_stingray"]):
            continue
        trim = _interior_trim(row["trim"])
        if trim and trim not in active_trims:
            continue
        interior_counts[row["section_id"]] += 1

    candidate_origins: dict[str, set[str]] = defaultdict(set)
    for section_id in context_by_section:
        candidate_origins[section_id].add("context_sections")
    for section_id in option_counts:
        candidate_origins[section_id].add("options")
    for section_id in interior_counts:
        candidate_origins[section_id].add("interiors")

    all_candidate_origins: dict[str, set[str]] = defaultdict(set)
    for section_id in any_context_by_section:
        all_candidate_origins[section_id].add("context_sections")
    for section_id in options_by_section:
        all_candidate_origins[section_id].add("options")
    for section_id in any_presentation_by_section:
        all_candidate_origins[section_id].add("section_presentation")
    for section_id in overrides_by_section:
        all_candidate_origins[section_id].add("variant_option_overrides")
    for section_id in interior_counts:
        all_candidate_origins[section_id].add("interiors")

    known_steps = {row["step_key"] for row in active_steps}
    sections_by_step: dict[str, list[dict]] = defaultdict(list)
    buckets_by_step: dict[str, list[dict]] = defaultdict(list)
    unmapped: list[dict] = []

    def resolved_step(section_id: str) -> tuple[str, str]:
        context = context_by_section.get(section_id) or {}
        if _clean(context.get("step_key")):
            return _clean(context["step_key"]), "context_section_master"
        presentation = presentation_by_section.get(section_id) or {}
        if _clean(presentation.get("step_key")):
            return _clean(presentation["step_key"]), "section_presentation"
        master = section_master.get(section_id) or {}
        if _clean(master.get("step_key")):
            return _clean(master["step_key"]), "section_master"
        return "", "unresolved"

    def resolved_step_all(section_id: str) -> tuple[str, str]:
        context = any_context_by_section.get(section_id) or {}
        if _clean(context.get("step_key")):
            return _clean(context["step_key"]), "context_section_master"
        presentation = any_presentation_by_section.get(section_id) or {}
        if _clean(presentation.get("step_key")):
            return _clean(presentation["step_key"]), "section_presentation"
        master = section_master.get(section_id) or {}
        if _clean(master.get("step_key")):
            return _clean(master["step_key"]), "section_master"
        return "", "unresolved"

    def section_entry(
        section_id: str,
        step_key: str,
        step_source: str,
        origins_override: set[str] | None = None,
    ) -> dict:
        origins = origins_override if origins_override is not None else candidate_origins[section_id]
        context = (
            context_by_section.get(section_id)
            or any_context_by_section.get(section_id)
            or {}
        )
        presentation = presentation_by_section.get(section_id) or {}
        any_presentation = any_presentation_by_section.get(section_id) or {}
        effective_presentation = presentation or any_presentation
        master = section_master.get(section_id) or {}
        if "context_sections" in origins:
            runtime_evidence = "sections"
            workbook_evidence = "context_section_master"
            editor = {"table": "context_sections", "record": context}
        elif "options" in origins:
            runtime_evidence = "sections"
            workbook_evidence = "section_master + active model options"
            editor = (
                {"table": "section_presentation", "record": any_presentation}
                if any_presentation
                else None
            )
        elif "interiors" in origins:
            runtime_evidence = "interiors"
            workbook_evidence = "section_master + model-scoped interiors"
            editor = (
                {"table": "section_presentation", "record": any_presentation}
                if any_presentation
                else None
            )
        else:
            runtime_evidence = "not_emitted"
            workbook_evidence = "section_presentation"
            editor = {"table": "section_presentation", "record": any_presentation}
        order = (
            context.get("section_display_order")
            or effective_presentation.get("section_display_order")
            or master.get("display_order")
        )
        display_behavior = _clean(effective_presentation.get("display_behavior"))
        return {
            "section_id": section_id,
            "display_name": (
                _clean(context.get("section_name"))
                or _clean(effective_presentation.get("display_label"))
                or _clean(master.get("section_name"))
                or _display_fallback(section_id)
            ),
            "step_key": step_key,
            "step_resolution": step_source,
            "placement_evidence": {
                "context_step_key": _clean(context.get("step_key")),
                "context_active": _truthy(context.get("active")),
                "presentation_step_key": _clean(any_presentation.get("step_key")),
                "presentation_active": _truthy(any_presentation.get("active")),
                "presentation_display_label": _clean(
                    any_presentation.get("display_label")
                ),
                "presentation_standard_equipment_bucket": _clean(
                    any_presentation.get("standard_equipment_bucket")
                ),
                "context_section_name": _clean(context.get("section_name")),
                "master_step_key": _clean(master.get("step_key")),
                "master_section_name": _clean(master.get("section_name")),
            },
            "origins": sorted(origins),
            "runtime_evidence": runtime_evidence,
            "workbook_evidence": workbook_evidence,
            "section_display_order": _clean(order),
            "display_behavior": display_behavior,
            "presentation_state": display_behavior or "active",
            "selection_mode": _clean(context.get("selection_mode"))
            or _clean(master.get("selection_mode")),
            "is_required": _clean(context.get("is_required"))
            or _clean(master.get("is_required")),
            "standard_behavior": _clean(context.get("standard_behavior"))
            or _clean(master.get("standard_behavior")),
            "standard_equipment_bucket": _clean(
                effective_presentation.get("standard_equipment_bucket")
            ),
            "auto_added_bucket": _clean(effective_presentation.get("auto_added_bucket")),
            "display_label": _clean(effective_presentation.get("display_label")),
            "option_count": option_counts.get(section_id, 0),
            "interior_count": interior_counts.get(section_id, 0),
            "options": [
                {
                    "option_id": row.get("option_id"),
                    "section_id": section_id,
                    "rpo": row.get("rpo"),
                    "option_name": row.get("option_name"),
                    "display_order": row.get("display_order"),
                    "active": row.get("active"),
                    "display_behavior": row.get("display_behavior"),
                    "destination": {
                        "workspace": "options",
                        "entity_type": "option",
                        "entity_id": row.get("option_id"),
                    },
                }
                for row in options_by_section.get(section_id, [])
            ],
            "variant_overrides": [
                {
                    "option_id": row.get("option_id"),
                    "variant_id": row.get("variant_id"),
                    "variant_name": row.get("variant_name"),
                    "selectable": row.get("selectable"),
                    "display_behavior": row.get("display_behavior"),
                    "active": row.get("active"),
                }
                for row in overrides_by_section.get(section_id, [])
            ],
            "editor": editor,
            "read_only_reason": "" if editor else (
                "Section identity and placement are owned by read-only "
                "section_master; add a section-presentation row to author "
                "model-specific display metadata."
            ),
            "src_sheet": (
                _clean(context.get("src_sheet"))
                or _clean(any_presentation.get("src_sheet"))
                or _clean(master.get("src_sheet"))
            ),
            "physical_key": (
                _clean(context.get("physical_key"))
                or _clean(any_presentation.get("physical_key"))
                or _clean(master.get("physical_key"))
            ),
        }

    for section_id in sorted(candidate_origins):
        step_key, step_source = resolved_step(section_id)
        entry = section_entry(section_id, step_key, step_source)
        presentation = presentation_by_section.get(section_id) or {}
        is_bucket = (
            step_key in BUCKET_STEP_KEYS
            or _truthy(presentation.get("standard_equipment_bucket"))
        )
        if not step_key:
            unmapped.append({
                **entry,
                "reason": "No workbook-authored step_key resolves this model-connected section.",
            })
        elif is_bucket:
            buckets_by_step[step_key].append(entry)
        elif step_key not in known_steps:
            unmapped.append({
                **entry,
                "reason": (
                    f"Resolved step {step_key!r} has no active runtime_steps row "
                    f"for model {model_key!r}."
                ),
            })
        else:
            sections_by_step[step_key].append(entry)

    def section_sort_key(row: dict) -> tuple[int, str]:
        return (_integer(row.get("section_display_order")), row["section_id"])

    steps_out: list[dict] = []
    for row in active_steps:
        section_rows = sorted(sections_by_step.get(row["step_key"], []), key=section_sort_key)
        section_count = len(section_rows)
        steps_out.append({
            **row,
            "display_name": _clean(row.get("step_label"))
            or _clean(row["step_key"]).replace("_", " ").title(),
            "sections": section_rows,
            "bucket_members": [],
            "section_count": section_count,
            "section_state": "mapped" if section_count else "empty_proven",
            "empty_reason": "" if section_count else (
                "Fresh runtime metadata contains no section edge for this step; "
                "the step is terminal or managed by another runtime surface."
            ),
            "classification": "runtime_step",
        })

    buckets = [
        {
            "step_key": step_key,
            "label": step_key.replace("_", " ").title(),
            "members": sorted(members, key=section_sort_key),
            "member_count": len(members),
            "classification": "bucket",
        }
        for step_key, members in sorted(buckets_by_step.items())
    ]

    summary_steps: dict[str, list[str]] = defaultdict(list)
    for row in active_summary_map:
        summary_steps[_clean(row.get("section_key"))].append(
            _clean(row.get("step_key"))
        )
    summary_only = [
        {
            **row,
            "step_keys": sorted(
                step for step in summary_steps.get(_clean(row.get("section_key")), [])
                if step
            ),
            "classification": "summary_only",
        }
        for row in active_order_summary
    ]

    inactive_records = {
        "steps": [row for row in all_steps if not _truthy(row.get("active"))],
        "context_sections": [
            row for row in all_context if not _truthy(row.get("active"))
        ],
        "section_presentation": [
            row for row in all_presentation if not _truthy(row.get("active"))
        ],
    }

    mapped_ids = {
        section["section_id"]
        for step in steps_out
        for section in step["sections"]
    }
    bucket_ids = {
        section["section_id"]
        for bucket in buckets
        for section in bucket["members"]
    }
    unresolved_ids = {section["section_id"] for section in unmapped}
    section_nodes = []
    for section_id in sorted(all_candidate_origins):
        step_key, step_source = resolved_step_all(section_id)
        node = section_entry(
            section_id,
            step_key,
            step_source,
            all_candidate_origins[section_id],
        )
        if section_id in mapped_ids:
            classification = "runtime_section"
        elif section_id in bucket_ids:
            classification = "bucket_section"
        elif section_id in unresolved_ids or not step_key or (
            step_key not in known_steps and step_key not in BUCKET_STEP_KEYS
        ):
            classification = "unresolved"
        elif not any(
            _truthy(row.get("active"))
            for row in options_by_section.get(section_id, [])
        ) and not _truthy(any_context_by_section.get(section_id, {}).get("active")):
            classification = "inactive"
        else:
            classification = "presentation_only"
        node["classification"] = classification
        node["active"] = classification in {"runtime_section", "bucket_section"}
        node["empty"] = not node["options"] and not node["interior_count"]
        node["draft_overlay"] = {"state": "unchanged"}
        section_nodes.append(node)

    counts = {
        "steps": len(steps_out),
        "sections": len(section_nodes),
        "active": sum(node["active"] for node in section_nodes),
        "hidden_or_conditional": sum(
            bool(node.get("display_behavior")) for node in section_nodes
        ),
        "buckets": len(buckets),
        "context": sum(
            "context_sections" in node["origins"] for node in section_nodes
        ),
        "summary_only": len(summary_only),
        "unresolved": len(unmapped),
        "inactive": sum(
            node["classification"] == "inactive" for node in section_nodes
        ),
        "draft_changes": 0,
    }

    return {
        "model_key": model_key,
        "graph_version": STRUCTURE_GRAPH_VERSION,
        "fingerprint": graph_fingerprint(model_key, steps_out, buckets),
        "steps": steps_out,
        "buckets": buckets,
        "summary_only": summary_only,
        "section_nodes": section_nodes,
        "unmapped_sections": sorted(unmapped, key=section_sort_key),
        "inactive_records": inactive_records,
        "counts": counts,
        "draft_overlay": {"revision": 0, "operations": []},
        "parity": {
            "base_status": "verified_against_fresh_generation",
            "draft_status": "unchanged",
            "findings": [],
            "owner_gate": "py.test_workbook_manager_form_graph",
        },
        "evidence": {
            "authoritative_runtime_contract": fresh_contract_evidence(),
            "projection_sources": {
                "form_steps": len(all_steps),
                "section_presentation": len(all_presentation),
                "context_sections": len(all_context),
                "order_summary_sections": len(all_order_summary),
                "step_order_summary_map": len(all_summary_map),
                "sections_master": len(section_master),
                "active_option_section_edges": sum(option_counts.values()),
                "applicable_interior_section_edges": sum(interior_counts.values()),
            },
        },
        "editing": {
            "step_table": "form_steps",
            "section_table": "section_presentation",
            "context_section_table": "context_sections",
        },
        # Preserve the endpoint's established editing/inspection surfaces.
        "section_presentation": presentation_view,
        "context_sections": all_context,
        "order_summary_sections": all_order_summary,
        "step_order_summary_map": all_summary_map,
        "sections_master": list(section_master.values()),
        "variants": variants,
    }


SECTION_OVERLAY_TABLES = frozenset({"section_presentation", "context_sections"})
SUMMARY_OVERLAY_TABLES = frozenset({
    "order_summary_sections",
    "step_order_summary_map",
})
OPTION_GRAPH_FIELDS = frozenset({"section_id", "active"})


def _overlay_metadata(operation: dict, base: dict | None = None) -> dict:
    """Graph-node overlay through the shared Checkpoint 2C adapter.

    ``apply_draft_overlay`` runs only after ``overlay_binding_conflicts`` has
    cleared the draft (``conflicted_draft_overlay`` handles the other branch), so
    node overlays carry no conflicts here.
    """
    return draft_overlay.overlay(
        draft_id=str(operation.get("draft_id") or ""),
        operation={**operation, "id": operation.get("id") or 0},
        base=base,
    )


def _node_base(node: dict, operation: dict) -> dict | None:
    editor = node.get("editor") or {}
    if editor.get("table") == operation.get("table_name"):
        return editor.get("record")
    return None


def _is_graph_operation(operation: dict, model_key: str) -> bool:
    if operation.get("model_id") not in {"", model_key}:
        return False
    table = operation.get("table_name")
    if table in {"form_steps", *SECTION_OVERLAY_TABLES, *SUMMARY_OVERLAY_TABLES}:
        return True
    if table != "options":
        return False
    if operation.get("action") in {"add", "delete"}:
        return True
    return bool(OPTION_GRAPH_FIELDS & set(operation.get("changed_fields") or {}))


def _refresh_section_placement(node: dict) -> None:
    placement = node["placement_evidence"]
    if placement.get("context_active") and placement.get("context_step_key"):
        node["step_key"] = placement["context_step_key"]
        node["step_resolution"] = "draft_context_section"
    elif placement.get("presentation_active") and placement.get("presentation_step_key"):
        node["step_key"] = placement["presentation_step_key"]
        node["step_resolution"] = "draft_section_presentation"
    elif placement.get("master_step_key"):
        node["step_key"] = placement["master_step_key"]
        node["step_resolution"] = "section_master"
    else:
        node["step_key"] = ""
        node["step_resolution"] = "unresolved"

    node["display_label"] = (
        placement.get("presentation_display_label")
        if placement.get("presentation_active") else ""
    )
    node["standard_equipment_bucket"] = (
        placement.get("presentation_standard_equipment_bucket")
        if placement.get("presentation_active") else ""
    )
    node["display_name"] = (
        placement.get("context_section_name")
        if placement.get("context_active") else ""
    ) or node["display_label"] or placement.get("master_section_name") or _display_fallback(
        node["section_id"]
    )


def _apply_section_operation(node: dict, operation: dict, overlay: dict) -> None:
    table = operation["table_name"]
    action = operation.get("action")
    final = operation.get("final") or {}
    placement = node["placement_evidence"]
    deleting = action == "delete"
    # The node's display_name becomes the draft-effective label below; keep the
    # authored one so the UI can show authored → proposed (EFFECTIVE-01).
    node.setdefault("authored_display_name", node["display_name"])

    if table == "context_sections":
        placement["context_active"] = False if deleting else _truthy(
            final.get("active", placement.get("context_active"))
        )
        if deleting:
            placement["context_step_key"] = ""
            placement["context_section_name"] = ""
        else:
            if "step_key" in final:
                placement["context_step_key"] = _clean(final.get("step_key"))
            if "section_name" in final:
                placement["context_section_name"] = _clean(final.get("section_name"))
    else:
        placement["presentation_active"] = False if deleting else _truthy(
            final.get("active", placement.get("presentation_active"))
        )
        if deleting:
            placement["presentation_step_key"] = ""
            placement["presentation_display_label"] = ""
            placement["presentation_standard_equipment_bucket"] = ""
        else:
            if "step_key" in final:
                placement["presentation_step_key"] = _clean(final.get("step_key"))
            if "display_label" in final:
                placement["presentation_display_label"] = _clean(
                    final.get("display_label")
                )
            if "standard_equipment_bucket" in final:
                placement["presentation_standard_equipment_bucket"] = _clean(
                    final.get("standard_equipment_bucket")
                )
        for key in ("display_behavior", "section_display_order", "notes"):
            if key in final:
                node[key] = final[key]

    _refresh_section_placement(node)
    node["draft_overlay"] = overlay


def _draft_section_node(result: dict, section_id: str) -> dict | None:
    master = next(
        (
            row for row in result.get("sections_master", [])
            if row.get("section_id") == section_id
        ),
        None,
    )
    if master is None:
        return None
    step_key = _clean(master.get("step_key"))
    display_name = _clean(master.get("section_name")) or _display_fallback(section_id)
    return {
        "section_id": section_id,
        "display_name": display_name,
        "step_key": step_key,
        "step_resolution": "section_master",
        "placement_evidence": {
            "context_step_key": "",
            "context_active": False,
            "presentation_step_key": "",
            "presentation_active": False,
            "presentation_display_label": "",
            "presentation_standard_equipment_bucket": "",
            "context_section_name": "",
            "master_step_key": step_key,
            "master_section_name": display_name,
        },
        "origins": ["options"],
        "runtime_evidence": "sections",
        "workbook_evidence": "section_master + draft model option",
        "section_display_order": _clean(master.get("display_order")),
        "display_behavior": "",
        "presentation_state": "active",
        "selection_mode": _clean(master.get("selection_mode")),
        "is_required": _clean(master.get("is_required")),
        "standard_behavior": _clean(master.get("standard_behavior")),
        "standard_equipment_bucket": "",
        "auto_added_bucket": "",
        "display_label": "",
        "option_count": 0,
        "interior_count": 0,
        "options": [],
        "variant_overrides": [],
        "editor": None,
        "read_only_reason": (
            "Section identity and placement are owned by read-only "
            "section_master; add a section-presentation row to author "
            "model-specific display metadata."
        ),
        "src_sheet": _clean(master.get("src_sheet")),
        "physical_key": _clean(master.get("physical_key")),
        "classification": "inactive",
        "active": False,
        "empty": True,
        "draft_overlay": {"state": "unchanged"},
    }


def _apply_option_operation(
    result: dict,
    nodes: dict[str, dict],
    operation: dict,
) -> None:
    entity_key = operation.get("entity_key") or {}
    final = operation.get("final") or {}
    option_id = entity_key.get("option_id") or final.get("option_id")
    source = None
    current = None
    for node in nodes.values():
        match = next(
            (row for row in node.get("options", []) if row.get("option_id") == option_id),
            None,
        )
        if match is not None:
            source = node
            current = match
            break

    overlay = _overlay_metadata(operation, deepcopy(current))
    action = operation.get("action")
    changed = set(operation.get("changed_fields") or {})

    def member_overlay(node: dict, before: int, after: int) -> dict:
        return draft_overlay.membership(
            draft_id=str(operation.get("draft_id") or ""),
            operation={**operation, "id": operation.get("id") or 0},
            field="options",
            before=before,
            after=after,
        )

    source_membership = None
    if source is not None and action in {"update", "delete"}:
        before = len(source["options"])
        source["options"] = [
            row for row in source["options"] if row.get("option_id") != option_id
        ]
        source_membership = member_overlay(source, before, len(source["options"]))
    if action == "delete":
        if source is not None and source_membership is not None:
            source["draft_overlay"] = source_membership
        return

    effective = deepcopy(current or {"option_id": option_id})
    fields = set(final) if action == "add" else changed
    for key in fields:
        if key in final:
            effective[key] = final[key]
    destination_id = _clean(effective.get("section_id")) or (
        _clean(source.get("section_id")) if source is not None else ""
    )
    destination = nodes.get(destination_id)
    if destination is None:
        destination = _draft_section_node(result, destination_id)
        if destination is None:
            if source is not None:
                source["options"].append(effective)
            return
        result["section_nodes"].append(destination)
        nodes[destination_id] = destination
    effective["section_id"] = destination_id
    effective["draft_overlay"] = overlay
    destination_before = len(destination["options"])
    destination["options"].append(effective)
    if source is not None and source_membership is not None:
        source["draft_overlay"] = source_membership
    if destination is not source:
        destination["draft_overlay"] = member_overlay(
            destination, destination_before, len(destination["options"])
        )


def _rebuild_effective_topology(result: dict) -> None:
    nodes = result.get("section_nodes", [])
    known_steps = {step["step_key"] for step in result.get("steps", [])}
    sections_by_step: dict[str, list[dict]] = defaultdict(list)
    buckets_by_step: dict[str, list[dict]] = defaultdict(list)
    unmapped = []

    for node in nodes:
        _refresh_section_placement(node)
        node["option_count"] = sum(
            _truthy(option.get("active")) for option in node.get("options", [])
        )
        connected = bool(
            node["placement_evidence"].get("context_active")
            or node["option_count"]
            or node.get("interior_count")
        )
        step_key = node.get("step_key") or ""
        is_bucket = step_key in BUCKET_STEP_KEYS or (
            node["placement_evidence"].get("presentation_active")
            and _truthy(node.get("standard_equipment_bucket"))
        )
        if connected and is_bucket:
            node["classification"] = "bucket_section"
            node["active"] = True
            buckets_by_step[step_key].append(node)
        elif connected and step_key in known_steps:
            node["classification"] = "runtime_section"
            node["active"] = True
            sections_by_step[step_key].append(node)
        elif connected:
            node["classification"] = "unresolved"
            node["active"] = False
            reason = (
                "No workbook-authored step_key resolves this model-connected section."
                if not step_key else
                f"Resolved step {step_key!r} has no active runtime_steps row "
                f"for model {result['model_key']!r}."
            )
            unmapped.append({**node, "reason": reason})
        else:
            node["classification"] = "inactive"
            node["active"] = False
        node["empty"] = not node.get("options") and not node.get("interior_count")

    def sort_key(row: dict) -> tuple[int, str]:
        return (_integer(row.get("section_display_order")), row["section_id"])

    for step in result.get("steps", []):
        members = sorted(sections_by_step.get(step["step_key"], []), key=sort_key)
        step["sections"] = members
        step["bucket_members"] = []
        step["section_count"] = len(members)
        step["section_state"] = "mapped" if members else "empty_proven"
        step["empty_reason"] = "" if members else (
            "Effective runtime metadata contains no section edge for this step; "
            "the step is terminal or managed by another runtime surface."
        )

    base_labels = {
        bucket["step_key"]: bucket.get("label")
        for bucket in result.get("buckets", [])
    }
    result["buckets"] = [
        {
            "step_key": step_key,
            "label": base_labels.get(step_key) or step_key.replace("_", " ").title(),
            "members": sorted(members, key=sort_key),
            "member_count": len(members),
            "classification": "bucket",
        }
        for step_key, members in sorted(buckets_by_step.items())
    ]
    result["unmapped_sections"] = sorted(unmapped, key=sort_key)
    result["counts"].update({
        "active": sum(node.get("active", False) for node in nodes),
        "hidden_or_conditional": sum(
            bool(node.get("display_behavior")) for node in nodes
        ),
        "buckets": len(result["buckets"]),
        "context": sum(
            bool(node["placement_evidence"].get("context_active")) for node in nodes
        ),
        "unresolved": len(result["unmapped_sections"]),
        "inactive": sum(node.get("classification") == "inactive" for node in nodes),
    })
    result["fingerprint"] = graph_fingerprint(
        result["model_key"], result["steps"], result["buckets"]
    )


def conflicted_draft_overlay(graph: dict, draft_id: str, conflicts: list[dict]) -> dict:
    result = deepcopy(graph)
    result["draft_overlay"] = {
        "draft_id": draft_id,
        "revision": 0,
        "state": "conflicted",
        "operations": [],
        "conflicts": conflicts,
    }
    result["counts"]["draft_changes"] = 0
    result["parity"] = {
        **result.get("parity", {}),
        "draft_status": "conflicted",
        "draft_impact": "Draft intent is not bound to the current editable projection.",
        "findings": conflicts,
    }
    return result


def apply_draft_overlay(graph: dict, operations: list[dict]) -> dict:
    """Build an effective connected graph from typed durable-draft intent."""

    result = deepcopy(graph)
    model_key = result["model_key"]
    relevant = [
        operation for operation in operations
        if _is_graph_operation(operation, model_key)
    ]
    nodes = {
        node["section_id"]: node for node in result.get("section_nodes", [])
    }
    summaries = []
    for operation in relevant:
        table = operation.get("table_name")
        entity_key = operation.get("entity_key") or {}
        final = operation.get("final") or {}
        if table == "form_steps":
            step_key = entity_key.get("step_key") or final.get("step_key")
            for step in result.get("steps", []):
                if step.get("step_key") != step_key:
                    continue
                overlay = _overlay_metadata(operation, deepcopy(step))
                step.update({key: value for key, value in final.items() if key in step})
                if final.get("step_label"):
                    step["display_name"] = final["step_label"]
                step["draft_overlay"] = overlay
        elif table in SECTION_OVERLAY_TABLES:
            section_id = entity_key.get("section_id") or final.get("section_id")
            if section_id in nodes:
                node = nodes[section_id]
                _apply_section_operation(
                    node, operation, _overlay_metadata(operation, _node_base(node, operation))
                )
        elif table == "options":
            _apply_option_operation(result, nodes, operation)
        summaries.append({
            "operation_id": operation.get("id"),
            "table_name": table,
            "family": operation.get("family"),
            "action": operation.get("action"),
            "entity_key": entity_key,
            "changed_fields": operation.get("changed_fields") or {},
        })

    _rebuild_effective_topology(result)
    revision = max((int(operation.get("id") or 0) for operation in relevant), default=0)
    result["draft_overlay"] = {
        "revision": revision,
        "state": "modified" if relevant else "unchanged",
        "operations": summaries,
        "conflicts": [],
    }
    result["counts"]["draft_changes"] = len(relevant)
    result["parity"] = {
        **result.get("parity", {}),
        "draft_status": "pending_preview" if relevant else "unchanged",
        "draft_impact": (
            "Draft graph changes require final-graph preview before Review & Apply."
            if relevant else "No draft graph changes."
        ),
    }
    return result


def fresh_contract_evidence() -> dict:
    return {
        "note": (
            "tests/test_workbook_manager_form_graph.py generates fresh runtime "
            "contracts from a copied workbook and compares every promoted model."
        ),
        "owner_gate": "py.test_workbook_manager_form_graph",
    }


def graph_fingerprint(model_key: str, steps: list[dict], buckets: list[dict]) -> str:
    """Return a stable digest of every displayed step/section graph edge."""

    payload = {"model_key": model_key, "steps": {}, "buckets": {}}
    for step in steps:
        payload["steps"][step["step_key"]] = "|".join(
            sorted(entry["section_id"] for entry in step["sections"])
        )
    for bucket in buckets:
        payload["buckets"][bucket["step_key"]] = "|".join(
            sorted(entry["section_id"] for entry in bucket["members"])
        )
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def contract_membership(
    contract: dict,
    section_steps: dict[str, str] | None = None,
) -> dict[str, dict[str, list[str]]]:
    """Extract the full step/bucket graph from fresh generated metadata.

    ``steps[].section_ids`` owns ordinary and context section edges. Interior
    section IDs live under ``interiors`` instead, so their workbook-authored
    section_master step relation is supplied independently by the projection.
    """

    section_steps = section_steps or {}
    steps: dict[str, set[str]] = {}
    buckets: dict[str, set[str]] = defaultdict(set)
    for step in contract.get("steps", []):
        step_key = _clean(step.get("step_key"))
        steps[step_key] = {
            item
            for item in _clean(step.get("section_ids")).split("|")
            if item
        }
    for section in contract.get("sections", []):
        step_key = _clean(section.get("step_key"))
        section_id = _clean(section.get("section_id"))
        if not section_id:
            continue
        if step_key in steps:
            steps[step_key].add(section_id)
        else:
            buckets[step_key].add(section_id)
    for interior in contract.get("interiors", []):
        section_id = _clean(interior.get("section_id"))
        step_key = _clean(section_steps.get(section_id))
        if section_id and step_key in steps:
            steps[step_key].add(section_id)
    return {
        "steps": {key: sorted(values) for key, values in steps.items()},
        "buckets": {key: sorted(values) for key, values in buckets.items()},
    }
