#!/usr/bin/env python3
"""Workbook-editor engine: sheet metadata, op model, validation, apply.

The workbook owns its data; this module owns only what the workbook cannot
express about itself: which columns form each sheet family's primary key,
intended cell types, enum domains, and which columns reference other
workbook entities — plus the Phase 2 op pipeline (flatten -> coalesce ->
coerce/validate -> dry-run -> apply through ``save_workbook_safely``).
See workbook-editor-phase2-spec.md.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from datetime import date, datetime
from pathlib import Path

from openpyxl import load_workbook

from corvette_form_generator.schema_validation import result_payload, validate_workbook_schema
from corvette_form_generator.workbook import (
    excel_lock_path,
    remove_table_sheet_auto_filters,
    save_workbook_safely,
    workbook_truthy,
)
from corvette_form_generator.workbook_package import assert_valid_workbook_package

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOG_PATH = ROOT / "form-output" / "workbook-edit-log.jsonl"

# model_workbook_sources.source_role -> schema family
SOURCE_ROLE_FAMILIES: dict[str, str] = {
    "source_option_sheet": "options",
    "status_sheet": "ovs",
    "rule_mapping_sheet": "rule_mapping",
    "rule_groups_sheet": "rule_groups",
    "rule_group_members_sheet": "rule_group_members",
    "exclusive_groups_sheet": "exclusive_groups",
    "exclusive_group_members_sheet": "exclusive_members",
    "price_rules_sheet": "price_rules",
    "variant_option_overrides_sheet": "variant_overrides",
    "color_overrides_sheet": "color_overrides",
    "interior_source_sheet": "interiors",
}

# Per-family editing metadata. Columns absent from types/enums/refs are
# free text. Headers always come from the sheet itself, never from here.
EDITOR_SHEET_META: dict[str, dict] = {
    "options": {
        "key": ("option_id",),
        "types": {
            "price": "int",
            "display_order": "int",
            "selectable": "bool",
            "active": "bool",
        },
        "enums": {
            "display_behavior": (
                "", "default_selected", "hidden", "display_only", "auto_only",
            ),
        },
        "refs": {"section_id": "sections"},
    },
    "ovs": {
        "key": ("option_id", "variant_id"),
        "types": {},
        "enums": {"status": ("standard", "available", "unavailable")},
        "refs": {"option_id": "options", "variant_id": "variants"},
    },
    "rule_mapping": {
        "key": ("rule_id",),
        "types": {},
        "enums": {
            "rule_type": ("includes", "excludes", "requires"),
            "body_style_scope": ("", "coupe", "convertible"),
            "runtime_action": ("", "replace"),
            "normalization_status": ("active", "omitted", "replaced", "preserved"),
        },
        "refs": {
            "source_id": "options",
            "target_id": "options",
            "source_section": "sections",
            "target_section": "sections",
        },
    },
    "rule_groups": {
        "key": ("group_id",),
        "types": {"active": "bool"},
        "enums": {"group_type": ("requires_any", "excludes_any")},
        "refs": {"source_id": "options"},
    },
    "rule_group_members": {
        "key": ("group_id", "target_id"),
        "types": {"display_order": "int", "active": "bool"},
        "enums": {},
        "refs": {"group_id": "rule_groups", "target_id": "options"},
    },
    "exclusive_groups": {
        "key": ("group_id",),
        "types": {"active": "bool"},
        "enums": {
            "selection_mode": (
                "single_within_group", "required_single_within_group",
            ),
        },
        "refs": {},
    },
    "exclusive_members": {
        "key": ("group_id", "option_id"),
        "types": {"display_order": "int", "active": "bool"},
        "enums": {},
        "refs": {"group_id": "exclusive_groups", "option_id": "options"},
    },
    "price_rules": {
        "key": ("price_rule_id",),
        "types": {"price_value": "int"},
        "enums": {"price_rule_type": ("override",)},
        "refs": {
            "condition_option_id": "options",
            "target_option_id": "options",
        },
    },
    "variant_overrides": {
        "key": ("option_id", "variant_id"),
        "types": {"active": "bool"},
        "enums": {
            "selectable": ("", "True", "False"),
            "display_behavior": ("", "default_selected", "display_only", "hidden"),
        },
        "refs": {
            "option_id": "options",
            "variant_id": "variants",
            "section_id": "sections",
        },
    },
    "color_overrides": {
        "key": ("interior_id", "option_id"),
        "types": {},
        "enums": {"rule_type": ("requires",)},
        "refs": {"interior_id": "interiors", "option_id": "options"},
    },
    "interiors": {
        "key": ("interior_id",),
        "types": {
            "Price": "int",
            "active_for_stingray": "bool",
            "requires_r6x": "bool",
        },
        "enums": {},
        "refs": {"section_id": "sections", "included_option_id": "options"},
    },
}


# ─────────────────────────────────────────────────────────────
# Workbook extraction (shared with the server)
# ─────────────────────────────────────────────────────────────

def jsonable(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def extract_workbook(path: Path) -> dict:
    """Load the whole workbook into plain dicts and close the file."""
    path = Path(path)
    mtime_ns = path.stat().st_mtime_ns
    wb = load_workbook(path, read_only=True, data_only=True)
    sheets: dict[str, dict] = {}
    for ws in wb.worksheets:
        rows_iter = ws.iter_rows(values_only=True)
        header_row = next(rows_iter, None) or ()
        cols = [(i, str(v)) for i, v in enumerate(header_row) if v is not None]
        rows = []
        for raw in rows_iter:
            row = {
                name: jsonable(raw[i]) if i < len(raw) else None
                for i, name in cols
            }
            if all(v in (None, "") for v in row.values()):
                continue
            rows.append(row)
        sheets[ws.title] = {"headers": [name for _, name in cols], "rows": rows}
    wb.close()
    return {"path": str(path), "mtime_ns": mtime_ns, "sheets": sheets}


def rows_of(extract: dict, name: str) -> list[dict]:
    sheet = extract["sheets"].get(name)
    return sheet["rows"] if sheet else []


def model_sheet_registry(extract: dict) -> tuple[dict, dict]:
    """Per-model sheet registry plus a sheet-name -> family reverse map."""
    registry: dict[str, list[dict]] = {}
    sheet_family: dict[str, str] = {}
    for row in rows_of(extract, "model_workbook_sources"):
        if not workbook_truthy(row.get("active")):
            continue
        family = SOURCE_ROLE_FAMILIES.get(row.get("source_role"))
        sheet_name = row.get("sheet_name")
        model_key = row.get("model_key")
        if not (family and sheet_name and model_key):
            continue
        registry.setdefault(model_key, []).append({
            "sheet": sheet_name,
            "role": row.get("source_role"),
            "family": family,
        })
        sheet_family.setdefault(sheet_name, family)
    return registry, sheet_family


# ─────────────────────────────────────────────────────────────
# Op primitives: flatten, coalesce, coerce
# ─────────────────────────────────────────────────────────────

def flatten_items(items) -> list[dict]:
    ops: list[dict] = []
    for item in items or []:
        if isinstance(item, dict) and item.get("kind") == "composite":
            label = item.get("label") or item.get("compositeType") or "composite"
            for member in item.get("ops", []):
                member = dict(member)
                member["_composite"] = label
                ops.append(member)
        else:
            ops.append(dict(item))
    return ops


def _key_id(op: dict) -> tuple:
    return (op.get("sheet"), tuple(sorted(
        (str(k), str(v).strip()) for k, v in (op.get("key") or {}).items())))


def coalesce_ops(ops: list[dict]) -> list[dict]:
    result: list[dict | None] = []
    last_live: dict[tuple, int] = {}
    for op in ops:
        kid = _key_id(op)
        pos = last_live.get(kid)
        prev = result[pos] if pos is not None else None
        action = op.get("action")
        if prev is None or prev.get("action") == "delete":
            last_live[kid] = len(result)
            result.append(dict(op))
            continue
        prev_action = prev.get("action")
        if action == "update" and prev_action in ("add", "update"):
            prev["row"] = {**(prev.get("row") or {}), **(op.get("row") or {})}
        elif action == "delete" and prev_action == "add":
            result[pos] = None
            last_live.pop(kid, None)
        elif action == "delete" and prev_action == "update":
            result[pos] = dict(op)
        else:  # e.g. add after add/update — leave both; validation flags it
            last_live[kid] = len(result)
            result.append(dict(op))
    return [op for op in result if op is not None]


def coerce_value(family: str, column: str, value):
    meta = EDITOR_SHEET_META[family]
    if value == "":
        value = None
    enums = meta.get("enums", {}).get(column)
    if enums is not None:
        text = "" if value is None else str(value).strip()
        if text not in enums:
            raise ValueError(f"{column}: {text!r} not in enum {sorted(enums)}")
        return text or None
    kind = meta.get("types", {}).get(column)
    if kind == "int":
        if value is None:
            return None
        if isinstance(value, bool):
            raise ValueError(f"{column}: expected integer, got boolean")
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        text = str(value).strip()
        if text.lstrip("-").isdigit():
            return int(text)
        raise ValueError(f"{column}: expected integer, got {value!r}")
    if kind == "bool":
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.strip() in ("True", "False"):
            return value.strip() == "True"
        raise ValueError(f"{column}: expected True/False, got {value!r}")
    if value is None:
        return None
    return str(value).strip() or None


# ─────────────────────────────────────────────────────────────
# Batch validation (non-breaking writes only)
# ─────────────────────────────────────────────────────────────

CHILD_REFS_BY_FAMILY = {
    "options": [("ovs", "option_id"), ("rule_mapping", "source_id"), ("rule_mapping", "target_id"),
                ("rule_group_members", "target_id"), ("exclusive_members", "option_id"),
                ("price_rules", "condition_option_id"), ("price_rules", "target_option_id"),
                ("color_overrides", "option_id"), ("variant_overrides", "option_id"),
                ("interiors", "included_option_id")],
    "rule_groups": [("rule_group_members", "group_id")],
    "exclusive_groups": [("exclusive_members", "group_id")],
    "interiors": [("color_overrides", "interior_id")],
}

_REF_FAMILY = {"options": ("options", "option_id"), "rule_groups": ("rule_groups", "group_id"),
               "exclusive_groups": ("exclusive_groups", "group_id"),
               "interiors": ("interiors", "interior_id")}

_DORDER_GROUP_COL = {"options": "section_id", "rule_group_members": "group_id",
                     "exclusive_members": "group_id"}


def _registry_maps(extract):
    registry, sheet_family = model_sheet_registry(extract)
    models_by_sheet: dict[str, set] = {}
    by_model_family: dict[tuple, str] = {}
    for model_key, entries in registry.items():
        for entry in entries:
            models_by_sheet.setdefault(entry["sheet"], set()).add(model_key)
            by_model_family[(model_key, entry["family"])] = entry["sheet"]
    return registry, sheet_family, models_by_sheet, by_model_family


def _key_tuple(key, keycols):
    return tuple(str(key.get(k) or "").strip() for k in keycols)


def _sheet_key_index(extract, sheet, keycols):
    index = {}
    for row in rows_of(extract, sheet):
        kt = tuple(str(row.get(k) or "").strip() for k in keycols)
        if all(kt):
            index[kt] = row
    return index


def _ref_domain(extract, maps, batch_adds, sheet, refkind):
    _registry, _sheet_family, models_by_sheet, by_model_family = maps
    models = models_by_sheet.get(sheet, set())
    if refkind == "sections":
        return {str(r.get("section_id")).strip()
                for r in rows_of(extract, "section_master") if r.get("section_id")}
    if refkind == "variants":
        ids = {str(r.get("variant_id")).strip()
               for r in rows_of(extract, "model_variants")
               if r.get("model_key") in models and workbook_truthy(r.get("active"))}
        return ids or {str(r.get("variant_id")).strip()
                       for r in rows_of(extract, "variant_master") if r.get("variant_id")}
    family, id_col = _REF_FAMILY[refkind]
    ids = set()
    for model in models:
        src = by_model_family.get((model, family))
        if not src:
            continue
        ids |= {str(r.get(id_col)).strip() for r in rows_of(extract, src) if r.get(id_col)}
        ids |= {str((o.get("row") or {}).get(id_col)).strip()
                for o in batch_adds.get(src, []) if (o.get("row") or {}).get(id_col)}
    return ids


def _prepare_batch(extract, batch):
    errors: list[str] = []
    warnings: list[dict] = []
    ops = coalesce_ops(flatten_items(batch.get("items") or []))
    maps = _registry_maps(extract)
    _registry, sheet_family, models_by_sheet, by_model_family = maps
    promoted = {r.get("model_key"): workbook_truthy(r.get("promoted_to_runtime"))
                for r in rows_of(extract, "model_registry_promotion")}

    batch_adds: dict[str, list] = {}
    deleted_keys: set[tuple] = set()
    for o in ops:
        if o.get("action") == "add":
            batch_adds.setdefault(o.get("sheet"), []).append(o)
        if o.get("action") == "delete":
            deleted_keys.add(_key_id(o))

    key_indexes: dict[str, dict] = {}
    seen_adds: set = set()
    prepared: list[dict] = []
    scaffold_warned: set[str] = set()

    for i, o in enumerate(ops):
        action, sheet = o.get("action"), o.get("sheet")
        ctx = f"op[{i}] {action} {sheet} {o.get('key')}"
        if action not in ("add", "update", "delete"):
            errors.append(f"{ctx}: unknown action")
            continue
        family = sheet_family.get(sheet)
        if not family or str(sheet).startswith("form_"):
            errors.append(f"{ctx}: sheet is not editable")
            continue
        data = extract["sheets"].get(sheet)
        if data is None:
            errors.append(f"{ctx}: sheet not found in workbook")
            continue
        headers = set(data["headers"])
        meta = EDITOR_SHEET_META[family]
        keycols = list(meta["key"])
        key = o.get("key") or {}
        if sorted(key) != sorted(keycols):
            errors.append(f"{ctx}: key must be exactly {keycols}")
            continue
        if any(not str(v or "").strip() for v in key.values()):
            errors.append(f"{ctx}: blank key value")
            continue
        row = {k: v for k, v in (o.get("row") or {}).items() if not str(k).startswith("_")}
        unknown = sorted(c for c in row if c not in headers)
        if unknown:
            errors.append(f"{ctx}: unknown column(s) {unknown}")
            continue
        if action == "update" and any(c in row for c in keycols):
            errors.append(f"{ctx}: key columns are immutable on update")
            continue
        coerced = {}
        bad = False
        for col, val in row.items():
            try:
                coerced[col] = coerce_value(family, col, val)
            except ValueError as exc:
                errors.append(f"{ctx}: {exc}")
                bad = True
        if bad:
            continue
        for col, refkind in meta.get("refs", {}).items():
            if coerced.get(col) is not None:
                domain = _ref_domain(extract, maps, batch_adds, sheet, refkind)
                if str(coerced[col]) not in domain:
                    errors.append(f"{ctx}: {col}={coerced[col]!r} not found in {refkind}")
                    bad = True
        if bad:
            continue
        if sheet not in key_indexes:
            key_indexes[sheet] = _sheet_key_index(extract, sheet, keycols)
        kt = _key_tuple(key, keycols)
        if action == "add":
            if any(str(coerced.get(k) or "").strip() != kt[idx] for idx, k in enumerate(keycols)):
                errors.append(f"{ctx}: add row must include key columns matching the key")
                continue
            if kt in key_indexes[sheet] or (sheet, kt) in seen_adds:
                errors.append(f"{ctx}: duplicate key")
                continue
            seen_adds.add((sheet, kt))
        else:
            if kt not in key_indexes[sheet]:
                errors.append(f"{ctx}: row not found for key")
                continue
        models = models_by_sheet.get(sheet, set())
        if models and not any(promoted.get(m) for m in models) and sheet not in scaffold_warned:
            scaffold_warned.add(sheet)
            warnings.append({"id": f"scaffold:{sheet}",
                             "message": f"{sheet}: model is not promoted to runtime (scaffold)"})
        o = dict(o)
        o["_family"] = family
        o["_coerced_row"] = coerced
        o["_kt"] = kt
        prepared.append(o)

    if errors:
        return errors, warnings, prepared

    # composite-level integrity
    for o in prepared:
        if o["action"] != "add":
            continue
        family, sheet = o["_family"], o["sheet"]
        models = models_by_sheet.get(sheet, set())
        if family == "options":
            oid = o["_kt"][0]
            for model in models:
                ovs_sheet = by_model_family.get((model, "ovs"))
                if not ovs_sheet:
                    continue
                for vrow in rows_of(extract, "model_variants"):
                    if vrow.get("model_key") != model or not workbook_truthy(vrow.get("active")):
                        continue
                    vid = str(vrow.get("variant_id")).strip()
                    covered = any(p["action"] == "add" and p["sheet"] == ovs_sheet
                                  and p["_kt"] == (oid, vid) for p in prepared)
                    if not covered:
                        errors.append(f"add option {oid}: missing OVS coverage for variant {vid} in {ovs_sheet}")
        if family in ("rule_groups", "exclusive_groups"):
            member_family = "rule_group_members" if family == "rule_groups" else "exclusive_members"
            minimum = 1 if family == "rule_groups" else 2
            gid = o["_kt"][0]
            count = 0
            for model in models:
                member_sheet = by_model_family.get((model, member_family))
                count += sum(1 for p in prepared if p["action"] == "add"
                             and p["sheet"] == member_sheet and p["_kt"][0] == gid)
            if count < minimum:
                errors.append(f"add {family[:-1]} {gid}: requires at least {minimum} member row(s) in the same batch")

    # display-order collision warnings
    for o in prepared:
        if o["action"] == "delete":
            continue
        group_col = _DORDER_GROUP_COL.get(o["_family"])
        dorder = o["_coerced_row"].get("display_order")
        if group_col is None or dorder is None:
            continue
        sheet = o["sheet"]
        existing = key_indexes[sheet].get(o["_kt"], {})
        group_val = o["_coerced_row"].get(group_col) or str(existing.get(group_col) or "").strip()
        clash = False
        for kt2, row2 in key_indexes[sheet].items():
            if kt2 == o["_kt"]:
                continue
            if str(row2.get(group_col) or "").strip() == str(group_val) and \
                    str(row2.get("display_order") or "").strip() == str(dorder):
                clash = True
        for p in prepared:
            if p is o or p["sheet"] != sheet or p["action"] == "delete":
                continue
            p_group = p["_coerced_row"].get(group_col)
            if p_group is None:
                p_existing = key_indexes[sheet].get(p["_kt"], {})
                p_group = str(p_existing.get(group_col) or "").strip()
            if str(p_group) == str(group_val) and p["_coerced_row"].get("display_order") == dorder:
                clash = True
        if clash:
            warnings.append({"id": f"dorder:{sheet}:{'+'.join(o['_kt'])}",
                             "message": f"{sheet}: display_order {dorder} duplicates another row "
                                        f"in {group_col}={group_val}"})

    # referenced-delete warnings
    for o in prepared:
        if o["action"] != "delete":
            continue
        family, sheet = o["_family"], o["sheet"]
        child_specs = CHILD_REFS_BY_FAMILY.get(family)
        if not child_specs:
            continue
        target_id = o["_kt"][0]
        models = models_by_sheet.get(sheet, set())
        referencing = []
        for child_family, ref_col in child_specs:
            for model in models:
                child_sheet = by_model_family.get((model, child_family))
                if not child_sheet:
                    continue
                child_keycols = list(EDITOR_SHEET_META[child_family]["key"])
                for row in rows_of(extract, child_sheet):
                    if str(row.get(ref_col) or "").strip() != target_id:
                        continue
                    child_kt = tuple(str(row.get(k) or "").strip() for k in child_keycols)
                    child_kid = (child_sheet, tuple(sorted(zip((str(k) for k in child_keycols), child_kt))))
                    if child_kid not in deleted_keys:
                        referencing.append(f"{child_sheet}.{ref_col}")
        if referencing:
            warnings.append({"id": f"refdel:{sheet}:{'+'.join(o['_kt'])}",
                             "message": f"delete {target_id}: still referenced by {sorted(set(referencing))} "
                                        f"(repo convention for rules is normalization_status, not deletion)"})
    return errors, warnings, prepared


def validate_batch(extract, batch):
    errors, warnings, _prepared = _prepare_batch(extract, batch)
    return {"errors": errors, "warnings": warnings}


# ─────────────────────────────────────────────────────────────
# Apply pipeline
# ─────────────────────────────────────────────────────────────

GATE_COMMANDS = {
    "stingray": [".venv/bin/python scripts/generate_form.py --model stingray",
                 ".venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx",
                 "node --test tests/stingray-form-regression.test.mjs",
                 "node --test tests/stingray-generator-stability.test.mjs"],
    "grand_sport": [".venv/bin/python scripts/generate_form.py --model grand_sport",
                    ".venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx",
                    "node --test tests/grand-sport-contract-preview.test.mjs",
                    "node --test tests/grand-sport-draft-data.test.mjs",
                    "node --test tests/grand-sport-rule-audit.test.mjs"],
    "z06": [".venv/bin/python scripts/generate_form.py --model z06",
            ".venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx",
            "node --test tests/z06-contract-preview.test.mjs",
            "node --test tests/z06-form-data-draft.test.mjs"],
}


def gate_reminders(models: set[str]) -> list[str]:
    commands: list[str] = []
    for model in sorted(models):
        commands.extend(GATE_COMMANDS.get(model, [
            f".venv/bin/python scripts/generate_form.py --model {model}",
            ".venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx"]))
    seen = set()
    return [c for c in commands if not (c in seen or seen.add(c))]


def apply_ops_to_workbook(wb, prepared_ops, sheet_family) -> set[str]:
    touched: set[str] = set()
    by_sheet: dict[str, list] = {}
    for o in prepared_ops:
        by_sheet.setdefault(o["sheet"], []).append(o)
    for sheet, sheet_ops in by_sheet.items():
        ws = wb[sheet]
        col_of = {str(c.value): i + 1 for i, c in enumerate(ws[1]) if c.value is not None}
        keycols = list(EDITOR_SHEET_META[sheet_family[sheet]]["key"])

        def key_at(r):
            return tuple(str(ws.cell(row=r, column=col_of[k]).value or "").strip() for k in keycols)

        kmap = {key_at(r): r for r in range(2, ws.max_row + 1)}
        for o in (x for x in sheet_ops if x["action"] == "update"):
            r = kmap[o["_kt"]]
            for col, val in o["_coerced_row"].items():
                ws.cell(row=r, column=col_of[col]).value = val
        for r in sorted((kmap[o["_kt"]] for o in sheet_ops if o["action"] == "delete"), reverse=True):
            ws.delete_rows(r)
        for o in (x for x in sheet_ops if x["action"] == "add"):
            values = [None] * max(col_of.values())
            for col, val in o["_coerced_row"].items():
                values[col_of[col] - 1] = val
            ws.append(values)
        touched.add(sheet)
    return touched


def resize_sheet_tables(ws) -> None:
    last = 1
    for r in range(1, ws.max_row + 1):
        if any(c.value is not None for c in ws[r]):
            last = r
    last = max(last, 2)
    for name in list(ws.tables):
        table = ws.tables[name]
        ref = str(table.ref)
        if not ref.startswith("A1:"):
            continue
        end = ref.split(":", 1)[1]
        letters = "".join(ch for ch in end if ch.isalpha())
        table.ref = f"A1:{letters}{last}"


def apply_batch(path, batch, *, write=False, confirmed_warnings=(), source="cli",
                log_path=None, allow_stale=False, run_schema_validation=True) -> dict:
    path = Path(path)
    lock = excel_lock_path(path)
    if lock.exists():
        return {"ok": False, "status": "locked",
                "errors": [f"Excel lock file present: {lock}. Close Excel first."], "warnings": []}
    # mtime compares as strings: st_mtime_ns exceeds JS Number.MAX_SAFE_INTEGER,
    # so the browser must round-trip it as a string to keep full precision.
    if not allow_stale and str(batch.get("workbookMtimeNs")) != str(path.stat().st_mtime_ns):
        return {"ok": False, "status": "stale",
                "errors": ["workbook changed since this batch was prepared; reload and re-verify"],
                "warnings": []}
    extract = extract_workbook(path)
    errors, warnings, prepared = _prepare_batch(extract, batch)
    if errors:
        return {"ok": False, "status": "invalid", "errors": errors, "warnings": warnings}
    if not prepared:
        return {"ok": False, "status": "empty", "errors": ["batch contains no operations"], "warnings": []}
    confirmed = set(confirmed_warnings or ())
    unconfirmed = [w for w in warnings if w["id"] not in confirmed]
    if write and unconfirmed:
        return {"ok": False, "status": "needs_confirmation", "errors": [], "warnings": unconfirmed}

    _registry, sheet_family, models_by_sheet, _bmf = _registry_maps(extract)
    schema_result = None
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir) / path.name
        shutil.copy2(path, tmp)
        wb_tmp = load_workbook(tmp)
        touched = apply_ops_to_workbook(wb_tmp, prepared, sheet_family)
        for name in touched:
            resize_sheet_tables(wb_tmp[name])
        remove_table_sheet_auto_filters(wb_tmp)
        wb_tmp.save(tmp)
        assert_valid_workbook_package(tmp)
        if run_schema_validation:
            issues = validate_workbook_schema(str(tmp), check_live_contract=False)
            schema_result = result_payload(str(tmp), issues)
            if schema_result["error_count"]:
                return {"ok": False, "status": "schema_failed",
                        "errors": [f"dry-run schema validation failed with "
                                   f"{schema_result['error_count']} error(s)"],
                        "warnings": warnings, "schemaResult": schema_result}

    models_touched = {m for s in touched for m in models_by_sheet.get(s, set())}
    base = {"opCount": len(prepared), "sheets": sorted(touched), "warnings": warnings,
            "schemaResult": schema_result, "gateReminders": gate_reminders(models_touched)}
    if not write:
        return {"ok": True, "status": "validated", "errors": [], **base}

    wb = load_workbook(path)
    loaded_mtime = path.stat().st_mtime_ns
    touched = apply_ops_to_workbook(wb, prepared, sheet_family)
    for name in touched:
        resize_sheet_tables(wb[name])
    backup_path = save_workbook_safely(wb, path, loaded_mtime_ns=loaded_mtime)
    log_file = Path(log_path) if log_path else DEFAULT_LOG_PATH
    log_file.parent.mkdir(parents=True, exist_ok=True)
    entry = {"ts": datetime.now().isoformat(timespec="seconds"), "source": source,
             "workbook": str(path), "opCount": len(prepared),
             "composites": sorted({o["_composite"] for o in prepared if o.get("_composite")}),
             "sheets": sorted(touched), "backupPath": str(backup_path),
             "schemaErrors": None if schema_result is None else schema_result["error_count"],
             "warningsConfirmed": sorted(confirmed)}
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")
    return {"ok": True, "status": "applied", "errors": [], "applied": len(prepared),
            "backupPath": str(backup_path), "logPath": str(log_file), **base}
