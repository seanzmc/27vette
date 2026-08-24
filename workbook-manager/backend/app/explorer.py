"""Connected, read-only Workbook Manager explorer projections.

These views join the disposable verified projection for presentation. They do
not interpret new business rules and expose no write path.
"""

from __future__ import annotations

import json
import re
from typing import Any


_HASH_SUFFIX = re.compile(r"_[0-9a-f]{12}$", re.IGNORECASE)


def _row(row) -> dict | None:
    return dict(row) if row is not None else None


def _rows(conn, sql: str, params: tuple = ()) -> list[dict]:
    return [dict(row) for row in conn.execute(sql, params).fetchall()]


def _lineage(record: dict) -> dict:
    raw_context = record.get("model_context")
    if isinstance(raw_context, str):
        model_context = json.loads(raw_context) if raw_context else []
    else:
        model_context = raw_context or []
    return {
        "source_sheet": record.get("src_sheet", ""),
        "source_row": record.get("src_row"),
        "source_family": record.get("src_family", ""),
        "physical_key": record.get("physical_key", ""),
        "model_context": model_context,
    }


def option_label(record: dict | None) -> str:
    if not record:
        return "Unknown option"
    rpo = (record.get("rpo") or "").strip()
    name = (record.get("option_name") or record.get("name") or "").strip()
    return " — ".join(part for part in (rpo, name) if part) or record.get("option_id", "Unknown option")


def _group_fallback(group_id: str) -> str:
    """Return a neutral status label, never a fake name derived from a hash."""
    if _HASH_SUFFIX.search(group_id or ""):
        return "Label pending workbook review"
    return (group_id or "Unnamed group").replace("_", " ").strip().title()


def _exclusive_group_label(group: dict, members: list[dict]) -> str:
    """Use factual projection context only; notes are not display-label authority."""
    display_label = (group.get("display_label") or "").strip()
    if display_label:
        return display_label
    if not _HASH_SUFFIX.search(group.get("group_id", "")):
        return _group_fallback(group.get("group_id", ""))
    if members:
        section_names = {member.get("section_name") for member in members if member.get("section_name")}
        if len(section_names) == 1:
            return f"Exclusive group · {next(iter(section_names))}"
    return _group_fallback(group.get("group_id", ""))


def _rule_group_label(group: dict, source: dict | None, members: list[dict]) -> str:
    display_label = (group.get("display_label") or "").strip()
    if display_label:
        return display_label
    source_name = option_label(source) if source else "Rule"
    behavior = (group.get("group_type") or "related options").replace("_", " ")
    if source:
        return f"{source_name}: {behavior}"
    if not _HASH_SUFFIX.search(group.get("group_id", "")):
        return _group_fallback(group.get("group_id", ""))
    if members:
        return f"Rule affecting {len(members)} options"
    return _group_fallback(group.get("group_id", ""))


def _option_lookup(conn, model_key: str, option_id: str) -> dict | None:
    return _row(conn.execute(
        "SELECT * FROM options WHERE model_id=? AND option_id=?",
        (model_key, option_id),
    ).fetchone())


def _option_member_rows(conn, model_key: str, table: str, id_column: str, group_id: str) -> list[dict]:
    return _rows(
        conn,
        f"SELECT m.*, o.rpo, o.option_name, o.section_id, s.section_name "
        f"FROM {table} m LEFT JOIN options o ON o.model_id=m.model_id "
        f"AND o.option_id=m.{id_column} LEFT JOIN form_sections s "
        f"ON s.section_id=o.section_id WHERE m.model_id=? AND m.group_id=? "
        f"ORDER BY CAST(m.display_order AS INTEGER), m.id",
        (model_key, group_id),
    )


def _label_state(group: dict, audience: str) -> dict:
    """Additive Checkpoint 2B label/audience/status exposure.

    ``display_label`` is workbook-authored; blank or an absent column means
    label pending (the factual fallback label stays authoritative until the
    approved migration fills the column). Rule-group labels are Manager-facing
    unless a separate runtime contract makes them customer-visible.
    """

    label = (group.get("display_label") or "").strip()
    if not label:
        return {"display_label": "", "audience": audience, "label_status": "pending"}
    return {"display_label": label, "audience": audience, "label_status": "authored"}


def _exclusive_group_summary(conn, model_key: str, group: dict) -> dict:
    members = _option_member_rows(
        conn, model_key, "exclusive_group_members", "option_id", group["group_id"]
    )
    return {
        "entity_type": "group",
        "group_type": "exclusive",
        "group_id": group["group_id"],
        "label": _exclusive_group_label(group, members),
        **_label_state(group, "customer"),
        "behavior": group.get("selection_mode") or "",
        "active": group.get("active") == "True",
        "notes": group.get("notes") or "",
        "member_count": len(members),
        "members": members,
        "destination": {
            "workspace": "groups",
            "entity_type": "group",
            "entity_id": f"exclusive:{group['group_id']}",
        },
        "technical": {"lineage": _lineage(group)},
    }


def _rule_group_summary(conn, model_key: str, group: dict) -> dict:
    members = _option_member_rows(
        conn, model_key, "rule_group_members", "target_id", group["group_id"]
    )
    source = _option_lookup(conn, model_key, group.get("source_id") or "")
    return {
        "entity_type": "group",
        "group_type": "rule",
        "group_id": group["group_id"],
        "label": _rule_group_label(group, source, members),
        **_label_state(group, "manager"),
        "behavior": group.get("group_type") or "",
        "active": group.get("active") == "True",
        "notes": group.get("notes") or "",
        "source_option": source,
        "member_count": len(members),
        "members": members,
        "destination": {
            "workspace": "groups",
            "entity_type": "group",
            "entity_id": f"rule:{group['group_id']}",
        },
        "technical": {"lineage": _lineage(group)},
    }


def option_detail(conn, model_key: str, option_id: str) -> dict | None:
    option = _option_lookup(conn, model_key, option_id)
    if not option:
        return None
    section = _row(conn.execute(
        "SELECT * FROM form_sections WHERE section_id=?", (option.get("section_id"),)
    ).fetchone())
    availability = _rows(
        conn,
        "SELECT oa.*, v.display_name, v.trim_level, v.body_style, mv.display_order "
        "FROM option_availability oa LEFT JOIN variants v ON v.variant_id=oa.variant_id "
        "LEFT JOIN model_variants mv ON mv.model_key=oa.model_id AND mv.variant_id=oa.variant_id "
        "WHERE oa.model_id=? AND oa.option_id=? ORDER BY CAST(mv.display_order AS INTEGER), oa.id",
        (model_key, option_id),
    )
    exclusive_rows = _rows(
        conn,
        "SELECT g.* FROM exclusive_groups g JOIN exclusive_group_members m "
        "ON m.model_id=g.model_id AND m.group_id=g.group_id "
        "WHERE g.model_id=? AND m.option_id=? ORDER BY g.id",
        (model_key, option_id),
    )
    rule_group_rows = _rows(
        conn,
        "SELECT DISTINCT g.* FROM rule_groups g LEFT JOIN rule_group_members m "
        "ON m.model_id=g.model_id AND m.group_id=g.group_id "
        "WHERE g.model_id=? AND (g.source_id=? OR m.target_id=?) ORDER BY g.id",
        (model_key, option_id, option_id),
    )
    rules = _rows(
        conn,
        "SELECT r.*, source.rpo AS source_rpo, source.option_name AS source_name, "
        "target.rpo AS target_rpo, target.option_name AS target_name "
        "FROM rule_mappings r LEFT JOIN options source ON source.model_id=r.model_id "
        "AND source.option_id=r.source_id LEFT JOIN options target ON target.model_id=r.model_id "
        "AND target.option_id=r.target_id WHERE r.model_id=? AND "
        "(r.source_id=? OR r.target_id=?) ORDER BY r.id",
        (model_key, option_id, option_id),
    )
    pricing = _rows(
        conn,
        "SELECT p.*, condition.rpo AS condition_rpo, condition.option_name AS condition_name, "
        "target.rpo AS target_rpo, target.option_name AS target_name FROM pricing p "
        "LEFT JOIN options condition ON condition.model_id=p.model_id "
        "AND condition.option_id=p.condition_option_id LEFT JOIN options target "
        "ON target.model_id=p.model_id AND target.option_id=p.target_option_id "
        "WHERE p.model_id=? AND (p.condition_option_id=? OR p.target_option_id=?) ORDER BY p.id",
        (model_key, option_id, option_id),
    )
    assets = _rows(
        conn,
        "SELECT * FROM assets WHERE (model_key=? OR model_key='*') "
        "AND target_type='option' AND (target_id=? OR target_id=?) ORDER BY model_key DESC, id",
        (model_key, option_id, option.get("rpo") or ""),
    )
    overrides = _rows(
        conn,
        "SELECT vo.*, v.display_name FROM variant_option_overrides vo LEFT JOIN variants v "
        "ON v.variant_id=vo.variant_id WHERE vo.model_id=? AND vo.option_id=? ORDER BY vo.id",
        (model_key, option_id),
    )
    defaults = _rows(
        conn,
        "SELECT * FROM default_selection_rules WHERE model_key=? AND "
        "(target_option_id=? OR condition_id=?) ORDER BY CAST(priority AS INTEGER), id",
        (model_key, option_id, option_id),
    )
    return {
        "model_key": model_key,
        "entity_type": "option",
        "destination": {
            "workspace": "options", "entity_type": "option", "entity_id": option_id,
        },
        "option": {
            **option,
            "name": option.get("option_name") or "",
            "label": option_label(option),
        },
        "section": section,
        "availability": availability,
        "exclusive_groups": [
            _exclusive_group_summary(conn, model_key, group) for group in exclusive_rows
        ],
        "rule_groups": [
            _rule_group_summary(conn, model_key, group) for group in rule_group_rows
        ],
        "rules": rules,
        "pricing": pricing,
        "variant_overrides": overrides,
        "default_rules": defaults,
        "assets": assets,
        "technical": {
            "canonical_id": option_id,
            "lineage": _lineage(option),
        },
    }


def group_detail(conn, model_key: str, group_type: str, group_id: str) -> dict | None:
    if group_type == "exclusive":
        group = _row(conn.execute(
            "SELECT * FROM exclusive_groups WHERE model_id=? AND group_id=?",
            (model_key, group_id),
        ).fetchone())
        summary = _exclusive_group_summary(conn, model_key, group) if group else None
    elif group_type == "rule":
        group = _row(conn.execute(
            "SELECT * FROM rule_groups WHERE model_id=? AND group_id=?",
            (model_key, group_id),
        ).fetchone())
        summary = _rule_group_summary(conn, model_key, group) if group else None
    else:
        return None
    if summary is None:
        return None
    return {"model_key": model_key, **summary}


def section_detail(conn, model_key: str, section_id: str) -> dict | None:
    section = _row(conn.execute(
        "SELECT * FROM form_sections WHERE section_id=? AND EXISTS (SELECT 1 "
        "FROM options o WHERE o.model_id=? AND o.section_id=form_sections.section_id)",
        (section_id, model_key),
    ).fetchone())
    if section is None:
        return None
    options = _rows(conn, "SELECT * FROM options WHERE model_id=? AND section_id=? "
                    "ORDER BY CAST(display_order AS INTEGER), rpo, option_id",
                    (model_key, section_id))
    return {
        "model_key": model_key, "entity_type": "section", "section": section,
        "label": section.get("section_name") or section_id,
        "options": [_option_result(option) for option in options],
        "destination": {"workspace": "sections", "entity_type": "section",
                        "entity_id": section_id},
        "technical": {"canonical_id": section_id, "lineage": _lineage(section)},
    }


def rule_detail(conn, model_key: str, rule_id: str) -> dict | None:
    rule = _row(conn.execute("SELECT * FROM rule_mappings WHERE model_id=? AND rule_id=?",
                             (model_key, rule_id)).fetchone())
    if rule is None:
        return None
    return {
        "model_key": model_key, "entity_type": "rule", "rule": rule,
        "source_option": _option_lookup(conn, model_key, rule.get("source_id") or ""),
        "target_option": _option_lookup(conn, model_key, rule.get("target_id") or ""),
        "destination": {"workspace": "rules", "entity_type": "rule", "entity_id": rule_id},
        "technical": {"canonical_id": rule_id, "lineage": _lineage(rule)},
    }


def _search_rank(query: str, values: list[Any]) -> int | None:
    needle = query.casefold().strip()
    normalized = [str(value or "").casefold().strip() for value in values]
    if any(value == needle for value in normalized if value):
        return 0
    if any(value.startswith(needle) for value in normalized if value):
        return 1
    if any(needle in value for value in normalized if value):
        return 2
    return None


def search(conn, model_key: str, query: str, *, limit: int = 40) -> list[dict]:
    results: list[dict] = []
    for option in _rows(conn, "SELECT o.*, s.section_name FROM options o LEFT JOIN "
                        "form_sections s ON s.section_id=o.section_id WHERE o.model_id=?",
                        (model_key,)):
        rank = _search_rank(query, [option.get("rpo"), option.get("option_name"),
                                    option.get("option_id"), option.get("section_name"),
                                    option.get("description"), option.get("detail_raw")])
        if rank is not None:
            results.append({
                "entity_type": "option", "entity_id": option["option_id"],
                "label": option_label(option), "context": option.get("section_name") or "",
                "rank": rank,
                "destination": {"workspace": "options", "entity_type": "option",
                                "entity_id": option["option_id"]},
            })
    for group in _rows(conn, "SELECT * FROM exclusive_groups WHERE model_id=?", (model_key,)):
        summary = _exclusive_group_summary(conn, model_key, group)
        rank = _search_rank(query, [summary["label"], summary["group_id"], summary["notes"]])
        if rank is not None:
            results.append({
                "entity_type": "group", "entity_id": f"exclusive:{group['group_id']}",
                "label": summary["label"], "context": "Exclusive group", "rank": rank,
                "destination": summary["destination"],
            })
    for group in _rows(conn, "SELECT * FROM rule_groups WHERE model_id=?", (model_key,)):
        summary = _rule_group_summary(conn, model_key, group)
        rank = _search_rank(query, [summary["label"], summary["group_id"], summary["notes"],
                                    summary["behavior"]])
        if rank is not None:
            results.append({
                "entity_type": "group", "entity_id": f"rule:{group['group_id']}",
                "label": summary["label"], "context": "Rule group", "rank": rank,
                "destination": summary["destination"],
            })
    for section in _rows(conn, "SELECT DISTINCT s.* FROM form_sections s JOIN options o "
                         "ON o.section_id=s.section_id WHERE o.model_id=?", (model_key,)):
        rank = _search_rank(query, [section.get("section_name"), section.get("section_id")])
        if rank is not None:
            results.append({
                "entity_type": "section", "entity_id": section["section_id"],
                "label": section.get("section_name") or section["section_id"],
                "context": "Form section", "rank": rank,
                "destination": {"workspace": "sections", "entity_type": "section",
                                "entity_id": section["section_id"]},
            })
    for rule in _rows(conn, "SELECT r.*, source.rpo source_rpo, source.option_name source_name, "
                      "target.rpo target_rpo, target.option_name target_name FROM rule_mappings r "
                      "LEFT JOIN options source ON source.model_id=r.model_id AND source.option_id=r.source_id "
                      "LEFT JOIN options target ON target.model_id=r.model_id AND target.option_id=r.target_id "
                      "WHERE r.model_id=?", (model_key,)):
        label = f"{option_label({'rpo': rule.get('source_rpo'), 'option_name': rule.get('source_name')})} " \
                f"{(rule.get('rule_type') or 'relates to').replace('_', ' ')} " \
                f"{option_label({'rpo': rule.get('target_rpo'), 'option_name': rule.get('target_name')})}"
        rank = _search_rank(query, [rule.get("rule_id"), rule.get("rule_type"), label,
                                    rule.get("original_detail_raw")])
        if rank is not None:
            results.append({
                "entity_type": "rule", "entity_id": rule["rule_id"], "label": label,
                "context": "Option relationship", "rank": rank,
                "destination": {"workspace": "rules", "entity_type": "rule",
                                "entity_id": rule["rule_id"]},
            })
    results.sort(key=lambda row: (row["rank"], row["entity_type"], row["label"].casefold(),
                                  row["entity_id"]))
    return results[:limit]


DIAGNOSTICS = (
    {"key": "missing_required_images", "label": "Options without required image coverage",
     "definition": "Active selectable options in the selected model with no active exact or shared option image."},
    {"key": "multiple_exclusive_groups", "label": "Options in more than one exclusive group",
     "definition": "Options assigned to more than one exclusive group in the selected model."},
    {"key": "where_used", "label": "Where an option or group is used",
     "definition": "Projection rows in the selected model that directly reference the supplied option or group."},
    {"key": "option_relationships", "label": "Option relationships",
     "definition": "Every incoming and outgoing conflict, requirement, inclusion, or replacement for the supplied option."},
    {"key": "variant_availability_differences", "label": "Availability differs by variant",
     "definition": "Options whose projected availability status is not identical across variants in the selected model."},
)


def diagnostic_catalog() -> list[dict]:
    return [dict(item) for item in DIAGNOSTICS]


def _option_result(option: dict, **extra) -> dict:
    return {
        "entity_type": "option", "entity_id": option["option_id"],
        "label": option_label(option),
        "destination": {"workspace": "options", "entity_type": "option",
                        "entity_id": option["option_id"]},
        "technical": {"source_sheet": option.get("src_sheet", ""),
                      "source_row": option.get("src_row")},
        **extra,
    }


def diagnostic_results(conn, model_key: str, key: str, *, entity_id: str = "",
                       limit: int = 100) -> list[dict] | None:
    if key == "missing_required_images":
        options = _rows(conn, "SELECT * FROM options o WHERE o.model_id=? AND o.active='True' "
                        "AND o.selectable='True' AND NOT EXISTS (SELECT 1 FROM assets a WHERE "
                        "(a.model_key=o.model_id OR a.model_key='*') AND a.target_type='option' "
                        "AND a.active='True' AND (a.target_id=o.option_id OR a.target_id=o.rpo)) "
                        "ORDER BY o.rpo, o.option_id LIMIT ?", (model_key, limit))
        return [_option_result(option) for option in options]
    if key == "multiple_exclusive_groups":
        options = _rows(conn, "SELECT o.*, COUNT(DISTINCT m.group_id) distinct_group_count "
                        "FROM options o JOIN exclusive_group_members m ON m.model_id=o.model_id "
                        "AND m.option_id=o.option_id WHERE o.model_id=? GROUP BY o.id "
                        "HAVING COUNT(DISTINCT m.group_id)>1 ORDER BY o.rpo LIMIT ?",
                        (model_key, limit))
        return [_option_result(option, distinct_group_count=option["distinct_group_count"])
                for option in options]
    if key == "variant_availability_differences":
        options = _rows(conn, "SELECT o.*, COUNT(DISTINCT oa.status) distinct_status_count "
                        "FROM options o JOIN option_availability oa ON oa.model_id=o.model_id "
                        "AND oa.option_id=o.option_id WHERE o.model_id=? GROUP BY o.id "
                        "HAVING COUNT(DISTINCT oa.status)>1 ORDER BY o.rpo LIMIT ?", (model_key, limit))
        return [_option_result(option, distinct_status_count=option["distinct_status_count"])
                for option in options]
    if key == "option_relationships":
        if not entity_id:
            raise ValueError("entity_id is required for option_relationships")
        return [{
            "entity_type": "rule", "entity_id": row["rule_id"],
            "label": (row.get("rule_type") or "relationship").replace("_", " "),
            "direction": "outgoing" if row.get("source_id") == entity_id else "incoming",
            "source_id": row.get("source_id"), "target_id": row.get("target_id"),
            "destination": {"workspace": "rules", "entity_type": "rule",
                            "entity_id": row["rule_id"]},
            "technical": {"source_sheet": row.get("src_sheet", ""),
                          "source_row": row.get("src_row")},
        } for row in _rows(conn, "SELECT * FROM rule_mappings WHERE model_id=? AND "
                           "(source_id=? OR target_id=?) ORDER BY id LIMIT ?",
                           (model_key, entity_id, entity_id, limit))]
    if key == "where_used":
        if not entity_id:
            raise ValueError("entity_id is required for where_used")
        group_kind = ""
        if ":" in entity_id:
            group_kind, entity_id = entity_id.split(":", 1)
        rows: list[dict] = []
        if group_kind == "exclusive":
            queries = (("Exclusive group member", "exclusive_group_members", "group_id"),)
            destination = {"workspace": "groups", "entity_type": "group",
                           "entity_id": f"exclusive:{entity_id}"}
        elif group_kind == "rule":
            queries = (("Rule group member", "rule_group_members", "group_id"),)
            destination = {"workspace": "groups", "entity_type": "group",
                           "entity_id": f"rule:{entity_id}"}
        else:
            queries = (
                ("Availability", "option_availability", "option_id"),
                ("Exclusive group membership", "exclusive_group_members", "option_id"),
                ("Rule group membership", "rule_group_members", "target_id"),
                ("Price condition", "pricing", "condition_option_id"),
                ("Price target", "pricing", "target_option_id"),
                ("Variant override", "variant_option_overrides", "option_id"),
            )
            destination = {"workspace": "options", "entity_type": "option",
                           "entity_id": entity_id}
        for label, table, column in queries:
            for row in _rows(conn, f"SELECT * FROM {table} WHERE model_id=? AND {column}=? "
                              f"ORDER BY id LIMIT ?", (model_key, entity_id, limit)):
                rows.append({
                    "entity_type": "usage", "entity_id": f"{table}:{row['id']}",
                    "label": label, "destination": destination,
                    "technical": {"source_sheet": row.get("src_sheet", ""),
                                  "source_row": row.get("src_row")},
                })
                if len(rows) >= limit:
                    return rows
        return rows
    return None
