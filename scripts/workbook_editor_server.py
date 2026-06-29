#!/usr/bin/env python3
"""Local dev server for reviewing and editing stingray_master.xlsx.

Derives models, per-model sheet registries, schemas, and reference domains
live from the workbook — nothing is hardcoded that a workbook sheet owns.
See workbook-editor-integration-spec.md (Phase 1 read surface),
workbook-editor-phase2-spec.md (gated write API), and
workbook-editor-phase3-spec.md (read-only Review endpoints:
``/api/lints`` and ``/api/compare``), and ingest Pass 2 read-only review endpoints.
"""

from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from corvette_form_generator.editor_lints import (  # noqa: E402
    compare_options,
    lint_summary,
    load_allowlist,
    run_lints,
)
from corvette_form_generator.editor_ops import (  # noqa: E402
    EDITOR_SHEET_META,
    apply_batch,
    extract_workbook,
    jsonable,
    model_sheet_registry,
    rows_of,
)
from corvette_form_generator.ingest.review_payload import (  # noqa: E402
    IngestReviewStore,
    disabled_summary,
    validate_review_decisions,
)
from corvette_form_generator.workbook import workbook_truthy  # noqa: E402

UI_DIR = ROOT / "visualizer" / "workbook-editor"
DEFAULT_WORKBOOK = ROOT / "stingray_master.xlsx"
DEFAULT_ALLOWLIST = UI_DIR / "intentional-differences.json"

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
            # string: st_mtime_ns overflows JS Number.MAX_SAFE_INTEGER
            "mtimeNs": str(extract["mtime_ns"]),
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


def _workbook_stamp(extract: dict) -> dict:
    return {"path": extract["path"], "mtimeNs": str(extract["mtime_ns"])}


def lints_payload(extract: dict) -> dict:
    """Read-only structural lints over the current workbook state (Phase 3).
    Informational — the Phase 2 batch validator remains the write authority."""
    lints = run_lints(extract)
    return {
        "workbook": _workbook_stamp(extract),
        "summary": lint_summary(lints),
        "lints": lints,
    }


def compare_payload(extract: dict, allowlist_path: Path) -> dict:
    """Cross-model *_options comparison filtered through the committed
    intentional-differences allowlist (Phase 3)."""
    allowlist = load_allowlist(allowlist_path)
    payload = compare_options(extract, allowlist)
    payload["workbook"] = _workbook_stamp(extract)
    payload["allowlist"] = {
        "path": str(allowlist_path),
        "entryCount": len(allowlist),
    }
    return payload


CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json",
    ".svg": "image/svg+xml",
}


def _query_value(query: dict[str, list[str]], key: str, default: str = "") -> str:
    values = query.get(key)
    return values[0] if values else default


class WorkbookCache:
    """Re-extract the workbook only when its mtime changes; derived Review
    payloads (lints/compare) are memoized on the same key plus, for compare,
    the allowlist file's mtime."""

    def __init__(self, path: Path, allowlist_path: Path = DEFAULT_ALLOWLIST):
        self.path = Path(path)
        self.allowlist_path = Path(allowlist_path)
        self._extract: dict | None = None
        self._computed: dict[str, tuple] = {}

    def extract(self) -> dict:
        mtime_ns = self.path.stat().st_mtime_ns
        if self._extract is None or self._extract["mtime_ns"] != mtime_ns:
            self._extract = extract_workbook(self.path)
            self._computed.clear()
        return self._extract

    def _memo(self, key: str, stamp, build):
        cached = self._computed.get(key)
        if cached is not None and cached[0] == stamp:
            return cached[1]
        value = build()
        self._computed[key] = (stamp, value)
        return value

    def lints(self) -> dict:
        extract = self.extract()
        return self._memo("lints", extract["mtime_ns"],
                          lambda: lints_payload(extract))

    def compare(self) -> dict:
        extract = self.extract()
        allowlist_mtime = (self.allowlist_path.stat().st_mtime_ns
                           if self.allowlist_path.exists() else None)
        return self._memo("compare", (extract["mtime_ns"], allowlist_mtime),
                          lambda: compare_payload(extract, self.allowlist_path))


class EditorHandler(BaseHTTPRequestHandler):
    cache: WorkbookCache  # assigned in main()
    ingest_review: IngestReviewStore | None = None
    log_path: Path | None = None  # test override; None -> editor_ops default
    MAX_BODY = 10_000_000

    def _allowed_origins(self):
        port = self.server.server_address[1]
        return {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}

    def do_POST(self):  # noqa: N802 (stdlib API name)
        path = urlsplit(self.path).path
        if path not in ("/api/validate", "/api/apply", "/api/ingest/review/validate", "/api/ingest/workbook-build/validate"):
            self._send_json({"error": "not found"}, status=404)
            return
        origin = self.headers.get("Origin")
        if origin and origin not in self._allowed_origins():
            self._send_json({"error": "forbidden origin"}, status=403)
            return
        if "application/json" not in (self.headers.get("Content-Type") or ""):
            self._send_json({"error": "expected application/json"}, status=415)
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if not 0 < length <= self.MAX_BODY:
            self._send_json({"error": "missing or oversized body"}, status=400)
            return
        try:
            body = json.loads(self.rfile.read(length))
        except (ValueError, UnicodeDecodeError):
            self._send_json({"error": "invalid JSON body"}, status=400)
            return
        try:
            if path == "/api/ingest/review/validate":
                self._send_json(validate_review_decisions(body))
            elif path == "/api/ingest/workbook-build/validate":
                store = self._require_ingest_review()
                self._send_json(store.validate_workbook_build_decisions(body))
            elif path == "/api/validate":
                batch = body.get("batch") or {}
                result = apply_batch(self.cache.path, batch, write=False, source="server",
                                     log_path=self.log_path)
                self._send_json(result)
            else:
                batch = body.get("batch") or {}
                result = apply_batch(self.cache.path, batch, write=True, source="server",
                                     confirmed_warnings=body.get("confirmedWarnings") or [],
                                     log_path=self.log_path)
                status = 200 if result["ok"] else (409 if result["status"] == "stale" else 422)
                self._send_json(result, status=status)
        except BrokenPipeError:
            pass
        except Exception as exc:
            self._send_json({"error": f"{type(exc).__name__}: {exc}"}, status=500)

    def do_GET(self):  # noqa: N802 (stdlib API name)
        parsed = urlsplit(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        try:
            if path == "/api/workbook":
                self._send_json(build_payload(self.cache.extract()))
            elif path == "/api/lints":
                self._send_json(self.cache.lints())
            elif path == "/api/compare":
                self._send_json(self.cache.compare())
            elif path == "/api/ingest/summary":
                self._send_json(self._ingest_summary())
            elif path == "/api/ingest/candidates":
                store = self._require_ingest_review()
                self._send_json(store.list_candidates(
                    family=_query_value(query, "family", "options"),
                    status=_query_value(query, "status"),
                    model=_query_value(query, "model"),
                    reason=_query_value(query, "reason"),
                    q=_query_value(query, "q"),
                    offset=int(_query_value(query, "offset", "0") or 0),
                    limit=int(_query_value(query, "limit", "200") or 200),
                ))
            elif path == "/api/ingest/interpretations":
                store = self._require_ingest_review()
                self._send_json(store.list_interpretations(
                    confidence=_query_value(query, "confidence"),
                    model=_query_value(query, "model"),
                    reason=_query_value(query, "reason"),
                    duplicate=_query_value(query, "duplicate"),
                    q=_query_value(query, "q"),
                    include_auto=_query_value(query, "include_auto", "false").lower() == "true",
                    offset=int(_query_value(query, "offset", "0") or 0),
                    limit=int(_query_value(query, "limit", "200") or 200),
                ))
            elif path == "/api/ingest/workbook-build/selection":
                store = self._require_ingest_review()
                self._send_json(store.model_selection())
            elif path == "/api/ingest/workbook-build/summary":
                store = self._require_ingest_review()
                self._send_json(store.workbook_build_summary())
            elif path == "/api/ingest/workbook-build/units":
                store = self._require_ingest_review()
                self._send_json(store.list_workbook_build_units(
                    lane=_query_value(query, "lane"),
                    model=_query_value(query, "model"),
                    action=_query_value(query, "action"),
                    q=_query_value(query, "q"),
                    offset=int(_query_value(query, "offset", "0") or 0),
                    limit=int(_query_value(query, "limit", "200") or 200),
                ))
            elif path.startswith("/api/ingest/workbook-build/unit/"):
                store = self._require_ingest_review()
                review_unit_id = path[len("/api/ingest/workbook-build/unit/"):]
                self._send_json(store.workbook_build_unit(review_unit_id))
            elif path == "/api/ingest/interpretation/reports/duplicates":
                store = self._require_ingest_review()
                self._send_json({"items": store.interpretation_reports()["duplicates"]})
            elif path == "/api/ingest/interpretation/reports/source-coverage":
                store = self._require_ingest_review()
                self._send_json({"items": store.interpretation_reports()["source_coverage"]})
            elif path == "/api/ingest/interpretation/blocked":
                store = self._require_ingest_review()
                self._send_json(store.interpretation_reports()["blocked"])
            elif path.startswith("/api/ingest/interpretation/"):
                store = self._require_ingest_review()
                interpretation_id = path[len("/api/ingest/interpretation/"):]
                self._send_json(store.interpretation(interpretation_id))
            elif path.startswith("/api/ingest/candidate/"):
                store = self._require_ingest_review()
                candidate_id = path[len("/api/ingest/candidate/"):]
                self._send_json(store.candidate(candidate_id))
            elif path.startswith("/api/ingest/unresolved/"):
                store = self._require_ingest_review()
                unresolved_id = path[len("/api/ingest/unresolved/"):]
                self._send_json(store.unresolved(unresolved_id))
            elif path == "/api/ingest/source":
                store = self._require_ingest_review()
                self._send_json(store.source(
                    sheet=_query_value(query, "sheet"),
                    row=int(_query_value(query, "row", "0") or 0),
                ))
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
        except KeyError as exc:
            self._send_json({"error": str(exc)}, status=404)
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=400)
        except Exception as exc:  # surface server faults to the UI
            self._send_json({"error": f"{type(exc).__name__}: {exc}"}, status=500)

    def _ingest_summary(self) -> dict:
        if self.ingest_review is None:
            return disabled_summary()
        return self.ingest_review.summary()

    def _require_ingest_review(self) -> IngestReviewStore:
        if self.ingest_review is None:
            raise ValueError("No ingest evidence/candidate directories configured.")
        return self.ingest_review

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
    parser = argparse.ArgumentParser(description="Local workbook editor and read-only ingest review server.")
    parser.add_argument("--port", type=int, default=8027)
    parser.add_argument("--workbook", default=str(DEFAULT_WORKBOOK))
    parser.add_argument("--ingest-evidence-dir", default="")
    parser.add_argument("--ingest-candidates-dir", default="")
    parser.add_argument("--ingest-interpretation-dir", default="")
    args = parser.parse_args()
    workbook_path = Path(args.workbook)
    EditorHandler.cache = WorkbookCache(workbook_path)
    if args.ingest_interpretation_dir and not (args.ingest_evidence_dir and args.ingest_candidates_dir):
        raise SystemExit("--ingest-interpretation-dir requires --ingest-evidence-dir and --ingest-candidates-dir")
    if args.ingest_evidence_dir or args.ingest_candidates_dir:
        if not (args.ingest_evidence_dir and args.ingest_candidates_dir):
            raise SystemExit("--ingest-evidence-dir and --ingest-candidates-dir must be provided together")
        EditorHandler.ingest_review = IngestReviewStore(
            evidence_dir=Path(args.ingest_evidence_dir),
            candidates_dir=Path(args.ingest_candidates_dir),
            interpretation_dir=Path(args.ingest_interpretation_dir) if args.ingest_interpretation_dir else None,
            workbook_path=workbook_path,
            workbook_mtime_ns=workbook_path.stat().st_mtime_ns,
        )
    else:
        EditorHandler.ingest_review = None
    server = ThreadingHTTPServer(("127.0.0.1", args.port), EditorHandler)
    print(f"Workbook editor (read-only) at http://127.0.0.1:{args.port}/")
    print(f"Workbook: {args.workbook}")
    if EditorHandler.ingest_review is not None:
        print(f"Ingest evidence: {args.ingest_evidence_dir}")
        print(f"Ingest candidates: {args.ingest_candidates_dir}")
        if args.ingest_interpretation_dir:
            print(f"Ingest interpretation: {args.ingest_interpretation_dir}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
