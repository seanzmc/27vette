#!/usr/bin/env python3
"""Read-only local server for reviewing stingray_master.xlsx (Phase 1).

Derives models, per-model sheet registries, schemas, and reference domains
live from the workbook — nothing is hardcoded that a workbook sheet owns.
See workbook-editor-integration-spec.md. Phase 1 has no write surface.
"""

from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from corvette_form_generator.editor_ops import (  # noqa: E402
    EDITOR_SHEET_META,
    extract_workbook,
    jsonable,
    model_sheet_registry,
    rows_of,
)
from corvette_form_generator.workbook import workbook_truthy  # noqa: E402

UI_DIR = ROOT / "visualizer" / "workbook-editor"
DEFAULT_WORKBOOK = ROOT / "stingray_master.xlsx"

_rows_of = rows_of


def _models(extract: dict) -> list[dict]:
    promotion = {
        row.get("model_key"): row
        for row in _rows_of(extract, "model_registry_promotion")
    }
    models = []
    for row in _rows_of(extract, "model_master"):
        key = row.get("model_key")
        if not key:
            continue
        promo = promotion.get(key, {})
        models.append({
            "key": key,
            "registryKey": row.get("registry_key"),
            "label": row.get("model_label"),
            "year": row.get("model_year"),
            "active": workbook_truthy(row.get("active")),
            "defaultModel": workbook_truthy(row.get("default_model")),
            "promoted": workbook_truthy(promo.get("promoted_to_runtime")),
            "displayOrder": promo.get("display_order"),
        })
    models.sort(key=lambda m: (m["displayOrder"] is None, m["displayOrder"] or 0, m["key"]))
    return models


_model_sheets = model_sheet_registry


def _sheet_list(extract: dict, sheet_family: dict) -> list[dict]:
    entries = []
    for name, data in extract["sheets"].items():
        family = sheet_family.get(name)
        entry = {
            "name": name,
            "headers": data["headers"],
            "rowCount": len(data["rows"]),
            "family": family,
            "readOnly": family is None or name.startswith("form_"),
        }
        meta = EDITOR_SHEET_META.get(family) if family else None
        if meta:
            entry["keyCols"] = list(meta["key"])
            entry["types"] = dict(meta.get("types", {}))
            entry["enums"] = {k: list(v) for k, v in meta.get("enums", {}).items()}
            entry["refs"] = dict(meta.get("refs", {}))
        entries.append(entry)
    return entries


def build_payload(extract: dict) -> dict:
    models = _models(extract)
    model_sheets, sheet_family = _model_sheets(extract)

    steps = sorted(
        (
            {
                "modelKey": row.get("model_key"),
                "stepKey": row.get("step_key"),
                "label": row.get("step_label"),
                "order": row.get("runtime_order"),
            }
            for row in _rows_of(extract, "runtime_steps")
            if workbook_truthy(row.get("active"))
        ),
        key=lambda s: (s["modelKey"] or "", s["order"] or 0),
    )
    context_sections = [
        {
            "modelKey": row.get("model_key"),
            "sectionId": row.get("section_id"),
            "name": row.get("section_name"),
            "stepKey": row.get("step_key"),
        }
        for row in _rows_of(extract, "context_section_master")
        if workbook_truthy(row.get("active"))
    ]
    sections = [
        {
            "sectionId": row.get("section_id"),
            "name": row.get("section_name"),
            "selectionMode": row.get("selection_mode"),
            "isRequired": workbook_truthy(row.get("is_required")),
            "displayOrder": row.get("display_order"),
            "standardBehavior": row.get("standard_behavior"),
            "stepKey": row.get("step_key"),
        }
        for row in _rows_of(extract, "section_master")
        if row.get("section_id")
    ]
    presentation = [
        {
            "modelKey": row.get("model_key"),
            "sectionId": row.get("section_id"),
            "label": row.get("display_label"),
            "stepKey": row.get("step_key"),
            "order": row.get("section_display_order"),
        }
        for row in _rows_of(extract, "section_presentation")
        if workbook_truthy(row.get("active"))
    ]

    variant_names = {
        row.get("variant_id"): row.get("display_name")
        for row in _rows_of(extract, "variant_master")
    }
    variants_by_model: dict[str, list[dict]] = {}
    for row in sorted(
        _rows_of(extract, "model_variants"),
        key=lambda r: (r.get("model_key") or "", r.get("display_order") or 0),
    ):
        if not workbook_truthy(row.get("active")):
            continue
        variant_id = row.get("variant_id")
        variants_by_model.setdefault(row.get("model_key"), []).append(
            {"id": variant_id, "name": variant_names.get(variant_id)}
        )

    options_by_model: dict[str, list[dict]] = {}
    for model_key, entries in model_sheets.items():
        option_sheet = next(
            (e["sheet"] for e in entries if e["family"] == "options"), None
        )
        if not option_sheet:
            continue
        options_by_model[model_key] = [
            {"id": row.get("option_id"), "rpo": row.get("rpo"), "name": row.get("option_name")}
            for row in _rows_of(extract, option_sheet)
            if row.get("option_id")
        ]

    step_keys = sorted(
        {s["stepKey"] for s in steps if s["stepKey"]}
        | {s["stepKey"] for s in sections if s["stepKey"]}
    )

    def _ids_by_model(family: str, id_col: str, name_col: str | None = None) -> dict:
        out: dict[str, list[dict]] = {}
        for model_key, entries in model_sheets.items():
            src = next((e["sheet"] for e in entries if e["family"] == family), None)
            if not src:
                continue
            rows = [
                ({"id": row.get(id_col), "name": row.get(name_col)} if name_col
                 else {"id": row.get(id_col)})
                for row in _rows_of(extract, src)
                if row.get(id_col)
            ]
            if rows:
                out[model_key] = rows
        return out

    return {
        "workbook": {
            "path": extract["path"],
            "mtimeNs": extract["mtime_ns"],
            "sheetCount": len(extract["sheets"]),
        },
        "models": models,
        "modelSheets": model_sheets,
        "steps": steps,
        "contextSections": context_sections,
        "sections": sections,
        "sectionPresentation": presentation,
        "sheets": _sheet_list(extract, sheet_family),
        "referenceDomains": {
            "sections": [
                {"id": s["sectionId"], "name": s["name"]} for s in sections
            ],
            "variantsByModel": variants_by_model,
            "optionsByModel": options_by_model,
            "ruleGroupsByModel": _ids_by_model("rule_groups", "group_id"),
            "exclusiveGroupsByModel": _ids_by_model("exclusive_groups", "group_id"),
            "interiorsByModel": _ids_by_model("interiors", "interior_id", "Interior Name"),
            "stepKeys": step_keys,
        },
    }


def sheet_payload(extract: dict, name: str) -> dict | None:
    data = extract["sheets"].get(name)
    if data is None:
        return None
    return {"name": name, "headers": data["headers"], "rows": data["rows"]}


CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json",
    ".svg": "image/svg+xml",
}


class WorkbookCache:
    """Re-extract the workbook only when its mtime changes."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._extract: dict | None = None

    def extract(self) -> dict:
        mtime_ns = self.path.stat().st_mtime_ns
        if self._extract is None or self._extract["mtime_ns"] != mtime_ns:
            self._extract = extract_workbook(self.path)
        return self._extract


class EditorHandler(BaseHTTPRequestHandler):
    cache: WorkbookCache  # assigned in main()

    def do_GET(self):  # noqa: N802 (stdlib API name)
        path = urlsplit(self.path).path
        try:
            if path == "/api/workbook":
                self._send_json(build_payload(self.cache.extract()))
            elif path.startswith("/api/sheet/"):
                name = unquote(path[len("/api/sheet/"):])
                payload = sheet_payload(self.cache.extract(), name)
                if payload is None:
                    self._send_json({"error": f"unknown sheet: {name}"}, status=404)
                else:
                    self._send_json(payload)
            else:
                self._serve_static(path)
        except BrokenPipeError:
            pass
        except Exception as exc:  # surface server faults to the UI
            self._send_json({"error": f"{type(exc).__name__}: {exc}"}, status=500)

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_static(self, path: str) -> None:
        rel = "index.html" if path in ("", "/") else path.lstrip("/")
        target = (UI_DIR / rel).resolve()
        if not str(target).startswith(str(UI_DIR.resolve())) or not target.is_file():
            self.send_error(404)
            return
        body = target.read_bytes()
        self.send_response(200)
        self.send_header(
            "Content-Type", CONTENT_TYPES.get(target.suffix, "application/octet-stream")
        )
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):  # quiet by default; it's a local dev tool
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only workbook review server (Phase 1).")
    parser.add_argument("--port", type=int, default=8027)
    parser.add_argument("--workbook", default=str(DEFAULT_WORKBOOK))
    args = parser.parse_args()
    EditorHandler.cache = WorkbookCache(Path(args.workbook))
    server = ThreadingHTTPServer(("127.0.0.1", args.port), EditorHandler)
    print(f"Workbook editor (read-only) at http://127.0.0.1:{args.port}/")
    print(f"Workbook: {args.workbook}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
