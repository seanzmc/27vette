#!/usr/bin/env python3
"""Run-state persistence and fail-closed state machine for the ingest wizard.

States: profiled -> roles_confirmed -> parsed. Every transition persists JSON
artifacts under form-output/ingest-wizard/<run-id>/ so a run can be reopened
and later passes can consume the output. The canonical workbook and the raw
source file are never written.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from pathlib import Path
from typing import Any

from corvette_form_generator.ingest.wizard.joiner import join_prices
from corvette_form_generator.ingest.wizard.parser import parse_confirmed_sheets
from corvette_form_generator.ingest.wizard.profiler import (
    ROLE_EXCLUDE,
    ROLE_OPTIONS,
    ROLE_PRICE,
    SCHEMA_VERSION,
    SHEET_TYPE_OPTIONS,
    SHEET_TYPE_PRICE,
    profile_workbook,
)

STATE_PROFILED = "profiled"
STATE_ROLES_CONFIRMED = "roles_confirmed"
STATE_PARSED = "parsed"
VALID_ROLES = {ROLE_OPTIONS, ROLE_PRICE, ROLE_EXCLUDE}
RUN_ID_RE = re.compile(r"^[0-9]{8}-[0-9]{6}-[0-9a-f]{6}$")
PARSE_ARTIFACTS = ("option-candidates.json", "price-rows.json", "join-report.json")


class WizardError(ValueError):
    """User-visible wizard failure; maps to an HTTP 4xx response."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def file_fingerprint(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    stat = path.stat()
    return {"sha256": digest, "sizeBytes": stat.st_size, "mtimeNs": stat.st_mtime_ns}


class WizardSessionStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.base = self.root / "form-output" / "ingest-wizard"
        self.uploads = self.base / "uploads"

    # ------------------------------------------------------------- files
    def list_source_files(self) -> list[dict[str, Any]]:
        files: list[dict[str, Any]] = []
        for directory, origin in ((self.root, "project"), (self.uploads, "upload")):
            if not directory.is_dir():
                continue
            for path in sorted(directory.glob("*.xlsx")):
                if path.name == "stingray_master.xlsx" or path.name.startswith("~$"):
                    continue
                files.append(
                    {"name": path.name, "origin": origin, "sizeBytes": path.stat().st_size}
                )
        return files

    def save_upload(self, filename: str, data: bytes) -> dict[str, Any]:
        name = Path(str(filename)).name
        if (
            not name
            or name != filename
            or not name.lower().endswith(".xlsx")
            or name.startswith("~$")
        ):
            raise WizardError("Upload filename must be a plain .xlsx basename.")
        self.uploads.mkdir(parents=True, exist_ok=True)
        target = self.uploads / name
        target.write_bytes(data)
        return {"name": name, "origin": "upload", "sizeBytes": target.stat().st_size}

    def resolve_source(self, name: str) -> Path:
        if Path(str(name)).name != name:
            raise WizardError("Source file must be a plain basename.")
        for directory in (self.uploads, self.root):
            path = directory / name
            if path.is_file():
                return path
        raise WizardError(f"Source file not found: {name}")

    # ---------------------------------------------------------- sessions
    def create_session(self, file_name: str) -> dict[str, Any]:
        source = self.resolve_source(file_name)
        run_id = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
        run_dir = self.base / run_id
        run_dir.mkdir(parents=True)
        profile = profile_workbook(source)
        session = {
            "schemaVersion": SCHEMA_VERSION,
            "runId": run_id,
            "state": STATE_PROFILED,
            "sourceFile": file_name,
            "sourcePath": str(source),
            "fingerprint": file_fingerprint(source),
        }
        write_json(run_dir / "session.json", session)
        write_json(run_dir / "sheet-profile.json", profile)
        return {"session": session, "profile": profile}

    def run_dir(self, run_id: str) -> Path:
        if not RUN_ID_RE.fullmatch(str(run_id)):
            raise WizardError(f"Invalid run id: {run_id}")
        run_dir = self.base / run_id
        if not (run_dir / "session.json").is_file():
            raise WizardError(f"Unknown run: {run_id}", status=404)
        return run_dir

    def load_session(self, run_id: str, *, verify_source: bool = True) -> dict[str, Any]:
        session = read_json(self.run_dir(run_id) / "session.json")
        if verify_source:
            source = Path(session["sourcePath"])
            if not source.is_file():
                raise WizardError("Source file for this run is missing; start a new run.")
            if file_fingerprint(source)["sha256"] != session["fingerprint"]["sha256"]:
                raise WizardError("Source file changed since it was profiled; start a new run.")
        return session

    def list_sessions(self) -> list[dict[str, Any]]:
        if not self.base.is_dir():
            return []
        sessions = []
        for run_dir in sorted(self.base.iterdir(), reverse=True):
            session_file = run_dir / "session.json"
            if session_file.is_file():
                sessions.append(read_json(session_file))
        return sessions

    def session_detail(self, run_id: str) -> dict[str, Any]:
        run_dir = self.run_dir(run_id)
        roles_file = run_dir / "sheet-roles.json"
        report_file = run_dir / "join-report.json"
        return {
            "session": self.load_session(run_id, verify_source=False),
            "profile": read_json(run_dir / "sheet-profile.json"),
            "roles": read_json(roles_file)["roles"] if roles_file.is_file() else None,
            "joinReport": read_json(report_file) if report_file.is_file() else None,
        }

    # ------------------------------------------------------------- roles
    def confirm_roles(self, run_id: str, roles: dict[str, str]) -> dict[str, Any]:
        session = self.load_session(run_id)
        run_dir = self.run_dir(run_id)
        profile = read_json(run_dir / "sheet-profile.json")
        cards = {card["sheetName"]: card for card in profile["sheets"]}
        confirmed: dict[str, str] = {}
        for sheet, role in (roles or {}).items():
            if sheet not in cards:
                raise WizardError(f"Unknown sheet: {sheet}")
            if role not in VALID_ROLES:
                raise WizardError(f"Invalid role for {sheet}: {role}")
            confirmed[sheet] = role
        for sheet in cards:
            confirmed.setdefault(sheet, ROLE_EXCLUDE)
        for sheet, role in confirmed.items():
            sheet_type = cards[sheet]["sheetType"]
            if role == ROLE_OPTIONS and sheet_type != SHEET_TYPE_OPTIONS:
                raise WizardError(
                    f"{sheet} was not detected as an options matrix; it cannot take the options role."
                )
            if role == ROLE_PRICE and sheet_type != SHEET_TYPE_PRICE:
                raise WizardError(
                    f"{sheet} was not detected as a price sheet; it cannot take the price role."
                )
        options = [sheet for sheet, role in confirmed.items() if role == ROLE_OPTIONS]
        price = [sheet for sheet, role in confirmed.items() if role == ROLE_PRICE]
        if not options:
            raise WizardError("Confirm at least one options sheet.")
        if len(price) != 1:
            raise WizardError("Confirm exactly one price sheet.")
        write_json(run_dir / "sheet-roles.json", {"schemaVersion": SCHEMA_VERSION, "roles": confirmed})
        for stale in PARSE_ARTIFACTS:
            (run_dir / stale).unlink(missing_ok=True)
        session["state"] = STATE_ROLES_CONFIRMED
        write_json(run_dir / "session.json", session)
        return session

    # ------------------------------------------------------------- parse
    def run_parse(self, run_id: str) -> dict[str, Any]:
        session = self.load_session(run_id)
        if session["state"] not in (STATE_ROLES_CONFIRMED, STATE_PARSED):
            raise WizardError("Confirm sheet roles before parsing.")
        run_dir = self.run_dir(run_id)
        roles = read_json(run_dir / "sheet-roles.json")["roles"]
        parsed = parse_confirmed_sheets(Path(session["sourcePath"]), roles)
        report = join_prices(parsed["candidates"], parsed["priceRows"])
        write_json(
            run_dir / "option-candidates.json",
            {
                "schemaVersion": SCHEMA_VERSION,
                "candidates": parsed["candidates"],
                "skippedRows": parsed["skippedRows"],
            },
        )
        write_json(
            run_dir / "price-rows.json",
            {
                "schemaVersion": SCHEMA_VERSION,
                "priceRows": parsed["priceRows"],
                "baseModelPriceRows": parsed["baseModelPriceRows"],
                "skippedPriceRows": parsed["skippedPriceRows"],
            },
        )
        write_json(run_dir / "join-report.json", report)
        session["state"] = STATE_PARSED
        write_json(run_dir / "session.json", session)
        return {"session": session, "joinReport": report}

    # -------------------------------------------------------- candidates
    def candidates(
        self,
        run_id: str,
        *,
        sheet: str = "",
        price_match: str = "",
        family: str = "",
        query: str = "",
    ) -> dict[str, Any]:
        session = self.load_session(run_id, verify_source=False)
        if session["state"] != STATE_PARSED:
            raise WizardError("Run the parse before requesting candidates.")
        run_dir = self.run_dir(run_id)
        payload = read_json(run_dir / "option-candidates.json")
        report = read_json(run_dir / "join-report.json")
        rows = payload["candidates"]
        if sheet:
            rows = [row for row in rows if row["sheetName"] == sheet]
        if family:
            rows = [row for row in rows if row["modelFamily"] == family]
        if price_match:
            rows = [row for row in rows if (row["priceMatch"] or "") == price_match]
        if query:
            needle = query.lower()
            rows = [
                row
                for row in rows
                if needle in row["rpo"].lower()
                or needle in row["refOnlyRpo"].lower()
                or needle in row["description"].lower()
            ]
        return {
            "session": session,
            "total": len(payload["candidates"]),
            "matched": len(rows),
            "candidates": rows,
            "skippedRows": payload["skippedRows"],
            "unmatchedPriceRows": report["unmatchedPriceRows"],
        }
