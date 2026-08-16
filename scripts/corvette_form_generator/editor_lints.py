#!/usr/bin/env python3
"""Workbook-editor Phase 3: read-only lints + cross-model option comparison.

Pure functions over the ``extract_workbook()`` dict. Makes the 2026-06-11
consistency-review method durable: structural lints over the *current*
workbook state (the pending-batch validator in ``editor_ops`` remains the
write authority), and an ``*_options`` cross-model diff with an
intentional-differences allowlist. See workbook-editor-phase3-spec.md.

No model- or RPO-specific knowledge lives here — checks are generic over
``EDITOR_SHEET_META`` and the workbook registries; business judgments live
in the committed allowlist data file with per-entry reasons.
"""

from __future__ import annotations

import json
from pathlib import Path

from corvette_form_generator.editor_ops import (
    _DORDER_GROUP_COL,
    _meta_ref_items,
    _ref_domain,
    _ref_label,
    _registry_maps,
    EDITOR_SHEET_META,
    rows_of,
)
from corvette_form_generator.workbook import workbook_truthy

# Severity mapped from the review's Blocker / Inconsistency / Cosmetic scale.
LINT_SEVERITY = {
    "duplicate_key": "error",
    "orphan_ref": "error",
    "display_order_type": "error",
    "display_order_collision": "warning",
    "ovs_coverage": "warning",
    "group_integrity": "warning",
    "boolean_text": "info",
    "stale_allowlist": "info",
}

COMPARE_FIELDS = ("option_name", "description", "section_id", "display_order")


def _norm(value) -> str:
    return "" if value is None else str(value).strip()


def _lint(lint_id, sheet, model, key, message, cells=()):
    return {
        "id": lint_id,
        "severity": LINT_SEVERITY[lint_id],
        "sheet": sheet,
        "model": model,
        "key": key,
        "message": message,
        "cells": list(cells),
    }


def _active(row) -> bool:
    """Treat rows without an ``active`` column as active."""
    if "active" not in row:
        return True
    return workbook_truthy(row.get("active"))


def _registered_sheets(maps):
    """Yield (sheet, family, model_label, models) for every registered sheet."""
    _registry, sheet_family, models_by_sheet, _bmf = maps
    for sheet in sorted(models_by_sheet):
        family = sheet_family.get(sheet)
        if not family:
            continue
        models = sorted(models_by_sheet[sheet])
        yield sheet, family, "+".join(models), models


def _key_of(row, keycols) -> str:
    return "+".join(_norm(row.get(k)) for k in keycols)


# ─────────────────────────────────────────────────────────────
# Lints
# ─────────────────────────────────────────────────────────────

def run_lints(extract: dict) -> list[dict]:
    maps = _registry_maps(extract)
    lints: list[dict] = []
    lints.extend(_lint_duplicate_keys(extract, maps))
    lints.extend(_lint_orphan_refs(extract, maps))
    lints.extend(_lint_display_order_types(extract, maps))
    lints.extend(_lint_display_order_collisions(extract, maps))
    lints.extend(_lint_ovs_coverage(extract, maps))
    lints.extend(_lint_group_integrity(extract, maps))
    lints.extend(_lint_boolean_text(extract, maps))
    return lints


def _lint_duplicate_keys(extract, maps):
    out = []
    for sheet, family, label, _models in _registered_sheets(maps):
        keycols = list(EDITOR_SHEET_META[family]["key"])
        seen: dict[str, int] = {}
        for row in rows_of(extract, sheet):
            kt = _key_of(row, keycols)
            if not kt.strip("+"):
                continue
            seen[kt] = seen.get(kt, 0) + 1
        for kt, count in seen.items():
            if count > 1:
                out.append(_lint(
                    "duplicate_key", sheet, label, kt,
                    f"primary key ({' + '.join(keycols)}) appears {count} times",
                    keycols))
    return out


def _lint_orphan_refs(extract, maps):
    out = []
    domains: dict[tuple, set] = {}
    for sheet, family, label, _models in _registered_sheets(maps):
        meta = EDITOR_SHEET_META[family]
        keycols = list(meta["key"])
        for col, refkind in _meta_ref_items(meta):
            dkey = (sheet, refkind)
            if dkey not in domains:
                domains[dkey] = set(_ref_domain(extract, maps, {}, sheet, refkind))
            domain = domains[dkey]
            for row in rows_of(extract, sheet):
                value = _norm(row.get(col))
                if value and value not in domain:
                    out.append(_lint(
                        "orphan_ref", sheet, label, _key_of(row, keycols),
                        f"{col}={value!r} not found in {_ref_label(refkind)}", [col]))
    return out


def _lint_display_order_types(extract, maps):
    out = []
    for sheet, family, label, _models in _registered_sheets(maps):
        meta = EDITOR_SHEET_META[family]
        keycols = list(meta["key"])
        for col, kind in meta.get("types", {}).items():
            if kind != "int":
                continue
            for row in rows_of(extract, sheet):
                value = row.get(col)
                if value is None or isinstance(value, bool):
                    continue
                if not isinstance(value, (int, float)):
                    out.append(_lint(
                        "display_order_type", sheet, label, _key_of(row, keycols),
                        f"{col} is text {value!r} (expected integer-typed cell)",
                        [col]))
    return out


def _lint_display_order_collisions(extract, maps):
    out = []
    for sheet, family, label, _models in _registered_sheets(maps):
        group_col = _DORDER_GROUP_COL.get(family)
        if group_col is None:
            continue
        keycols = list(EDITOR_SHEET_META[family]["key"])
        groups: dict[tuple, list] = {}
        for row in rows_of(extract, sheet):
            if not _active(row):
                continue
            dorder = _norm(row.get("display_order"))
            group = _norm(row.get(group_col))
            if not dorder or not group:
                continue
            groups.setdefault((group, dorder), []).append(row)
        for (group, dorder), rows in groups.items():
            if len(rows) < 2:
                continue
            keys = [_key_of(r, keycols) for r in rows]
            for row, key in zip(rows, keys):
                others = ", ".join(k for k in keys if k != key)
                out.append(_lint(
                    "display_order_collision", sheet, label, key,
                    f"display_order {dorder} duplicates {others} "
                    f"in {group_col}={group}", ["display_order", group_col]))
    return out


def _lint_ovs_coverage(extract, maps):
    out = []
    registry, _sheet_family, _models_by_sheet, by_model_family = maps
    for model in sorted(registry):
        options_sheet = by_model_family.get((model, "options"))
        ovs_sheet = by_model_family.get((model, "ovs"))
        if not options_sheet or not ovs_sheet:
            continue
        variants = [
            _norm(r.get("variant_id"))
            for r in rows_of(extract, "model_variants")
            if r.get("model_key") == model and workbook_truthy(r.get("active"))
        ]
        covered = {
            (_norm(r.get("option_id")), _norm(r.get("variant_id")))
            for r in rows_of(extract, ovs_sheet)
        }
        for row in rows_of(extract, options_sheet):
            if not (_active(row) and workbook_truthy(row.get("selectable"))):
                continue
            oid = _norm(row.get("option_id"))
            for vid in variants:
                if (oid, vid) not in covered:
                    out.append(_lint(
                        "ovs_coverage", ovs_sheet, model, f"{oid}+{vid}",
                        f"active selectable option {oid} has no OVS status row "
                        f"for active variant {vid}", ["status"]))
    return out


def _lint_group_integrity(extract, maps):
    out = []
    registry, _sheet_family, _models_by_sheet, by_model_family = maps
    specs = (
        ("exclusive_groups", "exclusive_members", "option_id", 2),
        ("rule_groups", "rule_group_members", "target_id", 1),
    )
    for model in sorted(registry):
        options_sheet = by_model_family.get((model, "options"))
        option_rows = {
            _norm(r.get("option_id")): r
            for r in rows_of(extract, options_sheet or "")
            if r.get("option_id")
        }
        for group_family, member_family, member_col, minimum in specs:
            group_sheet = by_model_family.get((model, group_family))
            member_sheet = by_model_family.get((model, member_family))
            if not group_sheet or not member_sheet:
                continue
            member_keycols = list(EDITOR_SHEET_META[member_family]["key"])
            members: dict[str, list] = {}
            for row in rows_of(extract, member_sheet):
                if _active(row):
                    members.setdefault(_norm(row.get("group_id")), []).append(row)
            for grow in rows_of(extract, group_sheet):
                if not _active(grow):
                    continue
                gid = _norm(grow.get("group_id"))
                count = len(members.get(gid, []))
                if count < minimum:
                    kind = group_family.replace("_", " ").rstrip("s")
                    out.append(_lint(
                        "group_integrity", group_sheet, model, gid,
                        f"active {kind} has {count} active member(s); "
                        f"requires at least {minimum}", ["group_id"]))
            for row in rows_of(extract, member_sheet):
                if not _active(row):
                    continue
                target = _norm(row.get(member_col))
                option = option_rows.get(target)
                if option is not None and not _active(option):
                    out.append(_lint(
                        "group_integrity", member_sheet, model,
                        _key_of(row, member_keycols),
                        f"member option {target} is inactive in {options_sheet}",
                        [member_col]))
    return out


def _lint_boolean_text(extract, maps):
    """Text 'TRUE'/'FALSE' (Excel boolean-as-text drift) anywhere in the
    workbook. Case-sensitive uppercase only so unrelated title-case text is
    not mistaken for an Excel boolean."""
    _registry, sheet_family, _models_by_sheet, _bmf = maps
    out = []
    for sheet, data in extract["sheets"].items():
        family = sheet_family.get(sheet)
        keycols = list(EDITOR_SHEET_META[family]["key"]) if family else []
        for i, row in enumerate(data["rows"]):
            cells = [col for col, v in row.items()
                     if isinstance(v, str) and v.strip() in ("TRUE", "FALSE")]
            if not cells:
                continue
            key = _key_of(row, keycols) if keycols else f"row {i + 2}"
            label = "+".join(sorted(_models_by_sheet.get(sheet, ()))) or None
            out.append(_lint(
                "boolean_text", sheet, label, key,
                f"text {'/'.join(repr(row[c]) for c in cells)} in "
                f"boolean-shaped column(s) {cells} (expected real booleans)",
                cells))
    return out


# ─────────────────────────────────────────────────────────────
# Cross-model comparison
# ─────────────────────────────────────────────────────────────

def load_allowlist(path: Path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = payload.get("entries", payload if isinstance(payload, list) else [])
    return [dict(e) for e in entries]


def _compared_models(extract, maps) -> list[str]:
    """Promoted runtime models that own an options sheet — scaffold-only
    models (ZR1/ZR1X) stay excluded, matching the review's scope."""
    registry, _sf, _mbs, by_model_family = maps
    promoted = {
        r.get("model_key")
        for r in rows_of(extract, "model_registry_promotion")
        if workbook_truthy(r.get("promoted_to_runtime"))
    }
    return sorted(
        m for m in registry
        if m in promoted and by_model_family.get((m, "options"))
    )


def _coerce_order(value):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _join_groups(model_rows: dict[str, dict[str, dict]]) -> list[dict]:
    """Join option rows across models by option_id, with an RPO fallback for
    ids that don't line up (only when the RPO is unique within every model
    that carries it — per-trim multi-row RPOs are never merged)."""
    groups: dict[str, dict] = {}
    for model, rows in model_rows.items():
        for oid, row in rows.items():
            groups.setdefault(oid, {})[model] = row

    rpo_unique: dict[str, dict[str, str]] = {}
    ambiguous: set[str] = set()
    for model, rows in model_rows.items():
        counts: dict[str, list[str]] = {}
        for oid, row in rows.items():
            rpo = _norm(row.get("rpo"))
            if rpo:
                counts.setdefault(rpo, []).append(oid)
        for rpo, oids in counts.items():
            if len(oids) > 1:
                ambiguous.add(rpo)
            else:
                rpo_unique.setdefault(rpo, {})[model] = oids[0]

    all_models = set(model_rows)
    merged: list[dict] = []
    consumed: set[str] = set()
    for oid in sorted(groups):
        if oid in consumed:
            continue
        members = dict(groups[oid])
        joined_via = "option_id"
        missing = all_models - set(members)
        if missing:
            rpo = _norm(next(iter(members.values())).get("rpo"))
            if rpo and rpo not in ambiguous:
                for model in sorted(missing):
                    other = rpo_unique.get(rpo, {}).get(model)
                    if other and other != oid and other not in consumed:
                        members[model] = model_rows[model][other]
                        consumed.add(other)
                        joined_via = "rpo"
        consumed.add(oid)
        merged.append({
            "joinKey": oid,
            "joinedVia": joined_via,
            "rpo": _norm(next(iter(members.values())).get("rpo")) or None,
            "optionIds": {m: _norm(r.get("option_id")) for m, r in members.items()},
            "rows": members,
        })
    return merged


def _section_ranks(groups, models):
    """Relative order of fully-shared options within each (model, section),
    so absolute display_order values don't matter — only sequence."""
    full = [
        g for g in groups
        if set(g["rows"]) == set(models)
        and len({_norm(r.get("section_id")) for r in g["rows"].values()}) == 1
    ]
    ranks: dict[tuple, int] = {}
    for model in models:
        by_section: dict[str, list] = {}
        for seq, g in enumerate(full):
            row = g["rows"][model]
            by_section.setdefault(_norm(row.get("section_id")), []).append(
                (_coerce_order(row.get("display_order")), seq, g["joinKey"]))
        for section, items in by_section.items():
            items.sort(key=lambda t: (t[0] is None, t[0] if t[0] is not None else 0, t[1]))
            for rank, (_d, _s, jk) in enumerate(items):
                ranks[(model, jk)] = rank
    return ranks


def _majority(values: dict[str, str]):
    """2-of-3 (or n-1 of n) agreement -> (majority_value, deviators)."""
    tally: dict[str, list[str]] = {}
    for model, value in values.items():
        tally.setdefault(value, []).append(model)
    if len(tally) < 2:
        return None, []
    ordered = sorted(tally.items(), key=lambda kv: -len(kv[1]))
    top_value, top_models = ordered[0]
    rest = [m for v, ms in ordered[1:] for m in ms]
    if len(top_models) > 1 and len(top_models) == len(values) - len(rest):
        return top_value, sorted(rest)
    return None, []


def _entry_targets(entry, group, field) -> bool:
    """Does this allowlist entry name this option (or RPO) and field?"""
    if entry.get("option_id"):
        if entry["option_id"] not in group["optionIds"].values():
            return False
    elif entry.get("rpo"):
        if _norm(entry.get("rpo")) != (group["rpo"] or ""):
            return False
    else:
        return False
    return entry.get("field", "*") in ("*", field)


def _entry_covers_deviators(entry, deviators) -> bool:
    """Intentional entries only suppress when every deviating model is one
    the entry vouches for — a targeted entry stays visible (and non-stale)
    while unrelated models also diverge (e.g. pre-C-2 Stingray copy drift)."""
    models = entry.get("models", "*")
    if models == "*":
        return True
    return bool(deviators) and set(deviators) <= set(models)


def compare_options(extract: dict, allowlist: list[dict] | None = None) -> dict:
    allowlist = allowlist or []
    maps = _registry_maps(extract)
    _registry, _sf, _mbs, by_model_family = maps
    models = _compared_models(extract, maps)

    model_rows = {
        m: {
            _norm(r.get("option_id")): r
            for r in rows_of(extract, by_model_family[(m, "options")])
            if r.get("option_id")
        }
        for m in models
    }
    groups = _join_groups(model_rows)
    ranks = _section_ranks(groups, models)
    matched_entries: set[int] = set()

    rows = []
    model_only: dict[str, list] = {m: [] for m in models}
    shared_count = 0
    for group in groups:
        present = sorted(group["rows"])
        if len(present) == 1:
            model = present[0]
            row = group["rows"][model]
            model_only[model].append({
                "id": group["joinKey"],
                "rpo": group["rpo"],
                "name": _norm(row.get("option_name")) or None,
            })
            continue
        if set(present) == set(models):
            shared_count += 1
        diffs = []
        for field in COMPARE_FIELDS:
            if field == "display_order":
                values = {
                    m: ranks.get((m, group["joinKey"])) for m in present
                }
                if any(v is None for v in values.values()):
                    continue  # not fully shared / section mismatch
                values = {m: str(v) for m, v in values.items()}
                display = {
                    m: f"#{values[m]} (display_order="
                       f"{_norm(group['rows'][m].get('display_order'))})"
                    for m in present
                }
            else:
                values = {m: _norm(group["rows"][m].get(field)) for m in present}
                display = dict(values)
            if len(set(values.values())) < 2:
                continue
            majority_value, deviators = _majority(values)
            majority_display = majority_value
            if field == "display_order" and majority_value is not None:
                majority_display = next(
                    display[m] for m in present if values[m] == majority_value)
            status, reason = "flagged", None
            for idx, entry in enumerate(allowlist):
                if not _entry_targets(entry, group, field):
                    continue
                matched_entries.add(idx)
                if entry.get("status") == "intentional":
                    if _entry_covers_deviators(entry, deviators):
                        status, reason = "intentional", entry.get("reason")
                        break
                else:
                    status, reason = "pending-review", entry.get("reason")
            diffs.append({
                "field": field,
                "values": display,
                "majority": majority_display,
                "deviators": deviators,
                "status": status,
                "reason": reason,
            })
        if diffs:
            rows.append({
                "joinKey": group["joinKey"],
                "joinedVia": group["joinedVia"],
                "rpo": group["rpo"],
                "optionIds": group["optionIds"],
                "models": present,
                "name": next(
                    (_norm(r.get("option_name")) for r in group["rows"].values()
                     if _norm(r.get("option_name"))), None),
                "diffs": diffs,
            })

    stale = [
        dict(entry) for idx, entry in enumerate(allowlist)
        if entry.get("status") == "intentional" and idx not in matched_entries
    ]
    return {
        "models": models,
        "sharedCount": shared_count,
        "rows": rows,
        "modelOnly": model_only,
        "staleAllowlist": stale,
    }


def lint_summary(lints: list[dict]) -> dict:
    summary = {"error": 0, "warning": 0, "info": 0}
    for lint in lints:
        summary[lint["severity"]] = summary.get(lint["severity"], 0) + 1
    return summary
