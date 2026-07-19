#!/usr/bin/env python3
"""Local server for the five-function current ingest path.

The server writes only run-scoped intake, profile, compile, typed-exception,
and immutable ChangeSet artifacts. Historical decision/plan evidence is GET
only; workbook approval and application belong to the shared workbook service.
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

from corvette_form_generator.ingest.wizard.legacy_reader import LegacyRunReader  # noqa: E402
from corvette_form_generator.ingest.wizard.session import (  # noqa: E402
    WizardError,
    WizardSessionStore,
)

UI_DIR = ROOT / "visualizer" / "ingest-wizard"
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/wizard.js": ("wizard.js", "text/javascript; charset=utf-8"),
    "/wizard.css": ("wizard.css", "text/css; charset=utf-8"),
}
MAX_UPLOAD_BYTES = 50 * 1024 * 1024


class WizardHandler(BaseHTTPRequestHandler):
    store: WizardSessionStore | None = None

    # ------------------------------------------------------------ plumbing
    def log_message(self, format: str, *args) -> None:  # noqa: A002 - stdlib signature
        pass

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, message: str, status: int) -> None:
        self._send_json({"error": message}, status=status)

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_UPLOAD_BYTES:
            raise WizardError("Request body too large.")
        return self.rfile.read(length) if length else b""

    def _json_body(self) -> dict:
        body = self._read_body()
        if not body:
            return {}
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise WizardError(f"Invalid JSON body: {exc}") from exc
        if not isinstance(payload, dict):
            raise WizardError("Request body must be a JSON object.")
        return payload

    @staticmethod
    def _require_exact_fields(payload: dict, fields: set[str], label: str) -> None:
        unknown = sorted(set(payload) - fields)
        missing = sorted(fields - set(payload))
        if unknown:
            raise WizardError(f"{label} has unknown fields: {', '.join(unknown)}.")
        if missing:
            raise WizardError(f"{label} is missing fields: {', '.join(missing)}.")

    @staticmethod
    def _require_query_fields(query: dict[str, list[str]], allowed: set[str], label: str) -> None:
        unknown = sorted(set(query) - allowed)
        duplicates = sorted(key for key, values in query.items() if len(values) != 1)
        if unknown or duplicates:
            raise WizardError(
                f"{label} query is invalid; unknown={unknown}, duplicate={duplicates}."
            )

    def _serve_static(self, path: str) -> None:
        name, content_type = STATIC_FILES[path]
        file_path = UI_DIR / name
        if not file_path.is_file():
            self._send_error_json(f"UI file missing: {name}", 404)
            return
        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _legacy_detail(self, run_id: str, artifact: str) -> dict:
        reader = LegacyRunReader(self.store.base)
        try:
            if artifact == "changeset":
                return reader.changeset_detail(run_id)
            return reader.plan_detail(run_id)
        except FileNotFoundError as exc:
            raise WizardError(str(exc), status=404) from exc
        except ValueError as exc:
            raise WizardError(str(exc)) from exc

    # ------------------------------------------------------------- routes
    def do_GET(self) -> None:  # noqa: N802 - stdlib naming
        split = urlsplit(self.path)
        path = unquote(split.path)
        query = parse_qs(split.query, keep_blank_values=True)
        try:
            if path in STATIC_FILES:
                self._serve_static(path)
            elif path == "/api/wizard/files":
                self._send_json({"files": self.store.list_source_files()})
            elif path == "/api/wizard/sessions":
                self._send_json({"sessions": self.store.list_sessions()})
            elif path.startswith("/api/wizard/sessions/") and path.endswith("/candidates"):
                run_id = path[len("/api/wizard/sessions/"):-len("/candidates")]
                self._send_json(
                    self.store.candidates(
                        run_id,
                        sheet=(query.get("sheet") or [""])[0],
                        price_match=(query.get("priceMatch") or [""])[0],
                        family=(query.get("family") or [""])[0],
                        query=(query.get("q") or [""])[0],
                    )
                )
            elif path.startswith("/api/wizard/sessions/") and path.endswith("/models"):
                run_id = path[len("/api/wizard/sessions/"):-len("/models")]
                self._send_json(self.store.model_options(run_id))
            elif path.startswith("/api/wizard/sessions/") and path.endswith("/reconciliation"):
                run_id = path[len("/api/wizard/sessions/"):-len("/reconciliation")]
                self._send_json(self.store.reconciliation(run_id))
            elif path.startswith("/api/wizard/sessions/") and path.endswith("/review"):
                run_id = path[len("/api/wizard/sessions/"):-len("/review")]
                self._send_json(
                    self.store.review_queue(
                        run_id,
                        (query.get("model") or [""])[0],
                        (query.get("lane") or [""])[0],
                        query=(query.get("q") or [""])[0],
                        template=(query.get("template") or [""])[0],
                        source_section=(query.get("sourceSection") or [""])[0],
                        price_match=(query.get("priceMatch") or [""])[0],
                        decision_state=(query.get("decisionState") or [""])[0],
                        price_presence=(query.get("pricePresence") or [""])[0],
                        workbook_ref=(query.get("workbookRef") or [""])[0],
                        section_state=(query.get("sectionState") or [""])[0],
                    )
                )
            elif path.startswith("/api/wizard/sessions/") and path.endswith("/progress"):
                run_id = path[len("/api/wizard/sessions/"):-len("/progress")]
                self._send_json(self.store.progress(run_id))
            elif path.startswith("/api/wizard/sessions/") and path.endswith("/compile"):
                run_id = path[len("/api/wizard/sessions/"):-len("/compile")]
                self._require_query_fields(query, set(), "Compile")
                self._send_json(self.store.compiler_summary(run_id))
            elif path.startswith("/api/wizard/sessions/") and path.endswith("/exceptions"):
                run_id = path[len("/api/wizard/sessions/"):-len("/exceptions")]
                self._require_query_fields(
                    query,
                    {"model", "decisionType", "decision", "sheet", "reviewState", "family", "reason", "severity", "state", "actionable", "q", "offset", "limit"},
                    "Exceptions",
                )
                self._send_json(
                    self.store.exception_queue_view(
                        run_id,
                        model=(query.get("model") or [""])[0],
                        decision_type=(query.get("decisionType") or query.get("decision") or [""])[0],
                        affected_sheet=(query.get("sheet") or [""])[0],
                        review_state=(query.get("reviewState") or [""])[0],
                        family=(query.get("family") or [""])[0],
                        reason=(query.get("reason") or [""])[0],
                        severity=(query.get("severity") or [""])[0],
                        state=(query.get("state") or [""])[0],
                        actionable=(query.get("actionable") or [""])[0],
                        query=(query.get("q") or [""])[0],
                        offset=(query.get("offset") or [0])[0],
                        limit=(query.get("limit") or [50])[0],
                    )
                )
            elif path.startswith("/api/wizard/sessions/") and path.endswith("/changeset"):
                run_id = path[len("/api/wizard/sessions/"):-len("/changeset")]
                self._require_query_fields(query, set(), "ChangeSet")
                self._send_json(self._legacy_detail(run_id, "changeset"))
            elif path.startswith("/api/wizard/sessions/") and path.endswith("/plan"):
                run_id = path[len("/api/wizard/sessions/"):-len("/plan")]
                self._send_json(self._legacy_detail(run_id, "plan"))
            elif path.startswith("/api/wizard/sessions/"):
                run_id = path[len("/api/wizard/sessions/"):]
                self._send_json(self.store.session_detail(run_id))
            else:
                self._send_error_json("Not found.", 404)
        except WizardError as exc:
            self._send_error_json(str(exc), exc.status)

    def do_POST(self) -> None:  # noqa: N802 - stdlib naming
        split = urlsplit(self.path)
        path = unquote(split.path)
        query = parse_qs(split.query)
        try:
            retired_suffixes = (
                "/decisions",
                "/decisions/delete",
                "/copy-decisions",
                "/complete",
                "/plan",
                "/plan/approve",
                "/write/approve",
            )
            if path.startswith("/api/wizard/sessions/") and path.endswith(retired_suffixes):
                self._send_error_json("Historical ingest mutation is retired.", 410)
            elif path == "/api/wizard/upload":
                filename = (query.get("filename") or [""])[0]
                saved = self.store.save_upload(filename, self._read_body())
                self._send_json({"file": saved})
            elif path == "/api/wizard/sessions":
                payload = self._json_body()
                file_name = str(payload.get("file") or "")
                if not file_name:
                    raise WizardError("Request body must name a source file.")
                self._send_json(self.store.create_session(file_name))
            elif path.startswith("/api/wizard/sessions/") and path.endswith("/roles"):
                run_id = path[len("/api/wizard/sessions/"):-len("/roles")]
                payload = self._json_body()
                roles = payload.get("roles")
                if not isinstance(roles, dict):
                    raise WizardError("Request body must carry a roles object.")
                session = self.store.confirm_roles(run_id, roles)
                self._send_json({"session": session})
            elif path.startswith("/api/wizard/sessions/") and path.endswith("/parse"):
                run_id = path[len("/api/wizard/sessions/"):-len("/parse")]
                self._json_body()  # accept and ignore an empty JSON body
                self._send_json(self.store.run_parse(run_id))
            elif path.startswith("/api/wizard/sessions/") and path.endswith("/models"):
                run_id = path[len("/api/wizard/sessions/"):-len("/models")]
                payload = self._json_body()
                targets = payload.get("targets")
                comparators = payload.get("comparators") or {}
                if not isinstance(targets, list) or not isinstance(comparators, dict):
                    raise WizardError("Request body must carry targets (list) and comparators (object).")
                self._send_json(self.store.select_models(run_id, [str(t) for t in targets], comparators))
            elif path.startswith("/api/wizard/sessions/") and path.endswith("/compile"):
                run_id = path[len("/api/wizard/sessions/"):-len("/compile")]
                payload = self._json_body()
                self._require_exact_fields(payload, set(), "Compile request")
                self.store.compile_canonical_rows(run_id)
                self._send_json(self.store.compiler_summary(run_id))
            elif path.startswith("/api/wizard/sessions/") and path.endswith("/changeset"):
                run_id = path[len("/api/wizard/sessions/"):-len("/changeset")]
                payload = self._json_body()
                self._require_exact_fields(payload, set(), "ChangeSet request")
                self._send_json(self.store.emit_changeset(run_id))
            elif path.startswith("/api/wizard/sessions/") and path.endswith("/exceptions/preview"):
                run_id = path[len("/api/wizard/sessions/"):-len("/exceptions/preview")]
                payload = self._json_body()
                self._require_exact_fields(
                    payload,
                    {"subjectId", "subjectVersion", "action", "payload"},
                    "Exception preview request",
                )
                typed_payload = payload.get("payload")
                if not isinstance(typed_payload, dict):
                    raise WizardError("Exception preview payload must be an object.")
                self._send_json(
                    self.store.preview_exception(
                        run_id,
                        subject_id=str(payload.get("subjectId") or ""),
                        subject_version=str(payload.get("subjectVersion") or ""),
                        action=str(payload.get("action") or ""),
                        payload=typed_payload,
                    )
                )
            elif path.startswith("/api/wizard/sessions/") and path.endswith("/exceptions/resolve"):
                run_id = path[len("/api/wizard/sessions/"):-len("/exceptions/resolve")]
                payload = self._json_body()
                self._require_exact_fields(
                    payload,
                    {"subjectId", "subjectVersion", "action", "payload", "reviewer"},
                    "Exception resolution request",
                )
                typed_payload = payload.get("payload")
                if not isinstance(typed_payload, dict):
                    raise WizardError("Exception resolution payload must be an object.")
                self._send_json(
                    self.store.resolve_exception(
                        run_id,
                        subject_id=str(payload.get("subjectId") or ""),
                        subject_version=str(payload.get("subjectVersion") or ""),
                        action=str(payload.get("action") or ""),
                        payload=typed_payload,
                        reviewer=str(payload.get("reviewer") or ""),
                    )
                )
            elif path.startswith("/api/wizard/sessions/") and path.endswith("/exceptions/reopen"):
                run_id = path[len("/api/wizard/sessions/"):-len("/exceptions/reopen")]
                payload = self._json_body()
                self._require_exact_fields(
                    payload,
                    {"subjectId", "subjectVersion", "reviewer"},
                    "Exception reopen request",
                )
                self._send_json(
                    self.store.reopen_exception(
                        run_id,
                        subject_id=str(payload.get("subjectId") or ""),
                        subject_version=str(payload.get("subjectVersion") or ""),
                        reviewer=str(payload.get("reviewer") or ""),
                    )
                )
            else:
                self._send_error_json("Not found.", 404)
        except WizardError as exc:
            self._send_error_json(str(exc), exc.status)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8040)
    parser.add_argument("--root", default=str(ROOT), help="Project root holding raw exports.")
    args = parser.parse_args()

    WizardHandler.store = WizardSessionStore(Path(args.root))
    server = ThreadingHTTPServer((args.host, args.port), WizardHandler)
    print(f"ingest wizard: http://{args.host}:{args.port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
