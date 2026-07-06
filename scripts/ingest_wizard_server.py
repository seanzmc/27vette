#!/usr/bin/env python3
"""Local dev server for the interactive ingest wizard (Passes A and B).

Read-only toward the canonical workbook and raw exports; writes only
run-scoped JSON under form-output/ingest-wizard/. Pass A: profile, roles,
parse, candidates. Pass B: model selection, decision lanes, completeness.
See docs/ingest/pass-a/interactive-ingest-wizard-pass-a-spec.md and
docs/ingest/ingest-wizard-end-to-end-completion-spec.md (Pass B).
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
            raise WizardError("JSON body must be an object.")
        return payload

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

    # ------------------------------------------------------------- routes
    def do_GET(self) -> None:  # noqa: N802 - stdlib naming
        split = urlsplit(self.path)
        path = unquote(split.path)
        query = parse_qs(split.query)
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
                    )
                )
            elif path.startswith("/api/wizard/sessions/") and path.endswith("/progress"):
                run_id = path[len("/api/wizard/sessions/"):-len("/progress")]
                self._send_json(self.store.progress(run_id))
            elif path.startswith("/api/wizard/sessions/") and path.endswith("/plan"):
                run_id = path[len("/api/wizard/sessions/"):-len("/plan")]
                self._send_json(self.store.plan_detail(run_id))
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
            if path == "/api/wizard/upload":
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
            elif path.startswith("/api/wizard/sessions/") and path.endswith("/decisions/delete"):
                run_id = path[len("/api/wizard/sessions/"):-len("/decisions/delete")]
                payload = self._json_body()
                decision_ids = payload.get("decisionIds")
                batch_id = str(payload.get("batchId") or "")
                if decision_ids is not None and not isinstance(decision_ids, list):
                    raise WizardError("decisionIds must be a list when present.")
                self._send_json(
                    self.store.delete_decisions(
                        run_id,
                        decision_ids=[str(d) for d in decision_ids] if decision_ids else None,
                        batch_id=batch_id,
                    )
                )
            elif path.startswith("/api/wizard/sessions/") and path.endswith("/decisions"):
                run_id = path[len("/api/wizard/sessions/"):-len("/decisions")]
                payload = self._json_body()
                decisions = payload.get("decisions")
                if not isinstance(decisions, list):
                    raise WizardError("Request body must carry a decisions list.")
                self._send_json(self.store.save_decisions(run_id, decisions))
            elif path.startswith("/api/wizard/sessions/") and path.endswith("/copy-decisions"):
                run_id = path[len("/api/wizard/sessions/"):-len("/copy-decisions")]
                payload = self._json_body()
                from_model = str(payload.get("fromModel") or "")
                to_model = str(payload.get("toModel") or "")
                if not from_model or not to_model:
                    raise WizardError("Request body must carry fromModel and toModel.")
                self._send_json(
                    self.store.copy_model_decisions(
                        run_id, from_model, to_model, overwrite=bool(payload.get("overwrite"))
                    )
                )
            elif path.startswith("/api/wizard/sessions/") and path.endswith("/complete"):
                run_id = path[len("/api/wizard/sessions/"):-len("/complete")]
                self._json_body()  # accept and ignore an empty JSON body
                self._send_json(self.store.mark_complete(run_id))
            elif path.startswith("/api/wizard/sessions/") and path.endswith("/plan"):
                run_id = path[len("/api/wizard/sessions/"):-len("/plan")]
                self._json_body()  # accept and ignore an empty JSON body
                self._send_json(self.store.build_apply_plan(run_id))
            elif path.startswith("/api/wizard/sessions/") and path.endswith("/plan/approve"):
                run_id = path[len("/api/wizard/sessions/"):-len("/plan/approve")]
                payload = self._json_body()
                self._send_json(self.store.approve_plan(run_id, str(payload.get("approver") or "")))
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
