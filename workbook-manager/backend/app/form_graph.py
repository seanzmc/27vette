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


def apply_draft_overlay(graph: dict, operations: list[dict]) -> dict:
    """Overlay relevant durable-draft operations on a connected graph copy.

    The projection graph remains unchanged. This is presentation-only evidence
    of proposed values; fresh-runtime parity remains pending until the normal
    final-graph preview validates the immutable ChangeSet.
    """

    result = deepcopy(graph)
    model_key = result["model_key"]
    relevant = [
        operation for operation in operations
        if operation.get("model_id") in {"", model_key}
        and operation.get("table_name") in {
            "form_steps",
            "section_presentation",
            "context_sections",
            "order_summary_sections",
            "step_order_summary_map",
            "options",
            "variant_option_overrides",
        }
    ]

    section_copies = list(result.get("section_nodes", []))
    section_copies.extend(
        section
        for step in result.get("steps", [])
        for section in step.get("sections", [])
    )
    section_copies.extend(
        section
        for bucket in result.get("buckets", [])
        for section in bucket.get("members", [])
    )
    section_copies.extend(result.get("unmapped_sections", []))

    summaries = []
    for operation in relevant:
        entity_key = operation.get("entity_key") or {}
        final = operation.get("final") or {}
        overlay = {
            "state": (
                "added" if operation.get("action") == "add"
                else "pending_deletion" if operation.get("action") == "delete"
                else "modified"
            ),
            "operation_id": operation.get("id"),
            "family": operation.get("family"),
            "action": operation.get("action"),
            "changed_fields": operation.get("changed_fields") or {},
        }
        if operation.get("table_name") == "form_steps":
            step_key = entity_key.get("step_key") or final.get("step_key")
            for step in result.get("steps", []):
                if step.get("step_key") != step_key:
                    continue
                step.update({key: value for key, value in final.items() if key in step})
                if final.get("step_label"):
                    step["display_name"] = final["step_label"]
                step["draft_overlay"] = overlay
        else:
            section_id = entity_key.get("section_id") or final.get("section_id")
            if section_id:
                for section in section_copies:
                    if section.get("section_id") != section_id:
                        continue
                    for key in (
                        "display_label", "display_behavior", "section_display_order",
                        "step_key", "active", "notes",
                    ):
                        if key in final:
                            section[key] = final[key]
                    if final.get("display_label"):
                        section["display_name"] = final["display_label"]
                    elif final.get("section_name"):
                        section["display_name"] = final["section_name"]
                    section["draft_overlay"] = overlay
        summaries.append({
            "operation_id": operation.get("id"),
            "table_name": operation.get("table_name"),
            "family": operation.get("family"),
            "action": operation.get("action"),
            "entity_key": entity_key,
            "changed_fields": operation.get("changed_fields") or {},
        })

    revision = max((int(operation.get("id") or 0) for operation in relevant), default=0)
    result["draft_overlay"] = {"revision": revision, "operations": summaries}
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
