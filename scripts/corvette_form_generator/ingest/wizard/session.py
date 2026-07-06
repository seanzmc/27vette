#!/usr/bin/env python3
"""Run-state persistence and fail-closed state machine for the ingest wizard.

States: profiled -> roles_confirmed -> parsed (Pass A), then
models_selected -> decisions_in_progress -> decisions_complete (Pass B).
Every transition persists JSON artifacts under
form-output/ingest-wizard/<run-id>/ so a run can be reopened and later passes
can consume the output. The canonical workbook is opened read-only for
pickers, variant reconciliation, and presentation prefill; it and the raw
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

from corvette_form_generator.ingest.wizard.decisions import (
    LANES,
    SCHEMA_VERSION_B,
    SCHEMA_VERSION_B2,
    artifact_fingerprint,
    candidate_needs_status_review,
    completeness,
    copy_decisions,
    detect_model_options,
    duplicate_rpo_groups,
    load_decision_state,
    presentation_prefill,
    scope_candidates,
    validate_decision,
    validate_selection,
    variant_reconciliation,
    workbook_option_reference,
    workbook_sections,
)
from corvette_form_generator.ingest.wizard.copy_split import propose_copy_split
from corvette_form_generator.ingest.wizard.hints import scan_candidates
from corvette_form_generator.ingest.wizard.plan_builder import (
    artifact_sha,
    plan_markdown,
    plan_summary,
)
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
STATE_MODELS_SELECTED = "models_selected"
STATE_DECISIONS_IN_PROGRESS = "decisions_in_progress"
STATE_DECISIONS_COMPLETE = "decisions_complete"
STATE_PLAN_BUILT = "plan_built"
STATE_PLAN_APPROVED = "plan_approved"
DECISION_STATES = (
    STATE_MODELS_SELECTED,
    STATE_DECISIONS_IN_PROGRESS,
    STATE_DECISIONS_COMPLETE,
    STATE_PLAN_BUILT,
    STATE_PLAN_APPROVED,
)
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
    def __init__(self, root: Path, workbook_path: Path | None = None) -> None:
        self.root = Path(root)
        self.base = self.root / "form-output" / "ingest-wizard"
        self.uploads = self.base / "uploads"
        self.workbook_path = Path(workbook_path) if workbook_path else self.root / "stingray_master.xlsx"
        self._reference_cache: tuple[int, dict] | None = None

    def _option_reference(self) -> dict:
        path = self._require_workbook()
        mtime = path.stat().st_mtime_ns
        if self._reference_cache is None or self._reference_cache[0] != mtime:
            self._reference_cache = (mtime, workbook_option_reference(path))
        return self._reference_cache[1]

    def _require_workbook(self) -> Path:
        if not self.workbook_path.is_file():
            raise WizardError(
                f"Canonical workbook not found (read-only pickers need it): {self.workbook_path.name}",
                status=409,
            )
        return self.workbook_path

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
        selection_file = run_dir / "model-selection.json"
        return {
            "session": self.load_session(run_id, verify_source=False),
            "profile": read_json(run_dir / "sheet-profile.json"),
            "roles": read_json(roles_file)["roles"] if roles_file.is_file() else None,
            "joinReport": read_json(report_file) if report_file.is_file() else None,
            "modelSelection": read_json(selection_file) if selection_file.is_file() else None,
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
        if session["state"] not in (STATE_ROLES_CONFIRMED, STATE_PARSED) + DECISION_STATES:
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
        if session["state"] not in (STATE_PARSED,) + DECISION_STATES:
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

    # ------------------------------------------------- pass b: model scoping
    def _parsed_candidates(self, run_id: str) -> tuple[dict[str, Any], Path, list[dict[str, Any]]]:
        session = self.load_session(run_id, verify_source=False)
        if session["state"] not in (STATE_PARSED,) + DECISION_STATES:
            raise WizardError("Run the parse before Pass B model selection.")
        candidates_file = self.run_dir(run_id) / "option-candidates.json"
        return session, candidates_file, read_json(candidates_file)["candidates"]

    def _load_selection(self, run_id: str, candidates_file: Path) -> dict[str, Any]:
        selection_file = self.run_dir(run_id) / "model-selection.json"
        if not selection_file.is_file():
            raise WizardError("Select target models before reviewing decisions.")
        selection = read_json(selection_file)
        if selection.get("candidatesFingerprint") != artifact_fingerprint(candidates_file):
            raise WizardError(
                "Candidates were re-parsed after model selection; re-select target models. "
                "Existing decisions with matching evidence fingerprints will be kept.",
                status=409,
            )
        return selection

    def model_options(self, run_id: str) -> dict[str, Any]:
        session, _, candidates = self._parsed_candidates(run_id)
        run_dir = self.run_dir(run_id)
        selection_file = run_dir / "model-selection.json"
        return {
            "session": session,
            "models": detect_model_options(candidates),
            "selection": read_json(selection_file) if selection_file.is_file() else None,
        }

    def select_models(self, run_id: str, targets: list[str], comparators: dict[str, str]) -> dict[str, Any]:
        session, candidates_file, candidates = self._parsed_candidates(run_id)
        try:
            validate_selection(candidates, targets, comparators)
        except ValueError as exc:
            raise WizardError(str(exc)) from exc
        run_dir = self.run_dir(run_id)
        selection = {
            "schemaVersion": SCHEMA_VERSION_B,
            "targets": list(targets),
            "comparators": dict(comparators),
            "sourceFingerprint": session["fingerprint"],
            "candidatesFingerprint": artifact_fingerprint(candidates_file),
            "selectedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        write_json(run_dir / "model-selection.json", selection)
        reconciliation = variant_reconciliation(self._require_workbook(), candidates, list(targets))
        write_json(run_dir / "variant-reconciliation.json", reconciliation)
        # Keep only decisions that still resolve: in-target model and matching
        # candidate evidence fingerprint (re-parse invalidation, spec B2).
        state = self._decision_state(run_id, candidates, selection, prune_to_targets=True)
        self._write_decisions(run_id, state["decisions"], selection)
        session["state"] = STATE_MODELS_SELECTED if not state["decisions"] else STATE_DECISIONS_IN_PROGRESS
        write_json(run_dir / "session.json", session)
        return {"session": session, "selection": selection, "reconciliation": reconciliation}

    def reconciliation(self, run_id: str) -> dict[str, Any]:
        _, candidates_file, _ = self._parsed_candidates(run_id)
        self._load_selection(run_id, candidates_file)
        return read_json(self.run_dir(run_id) / "variant-reconciliation.json")

    # ---------------------------------------------------- pass b: decisions
    def _decision_state(
        self,
        run_id: str,
        candidates: list[dict[str, Any]],
        selection: dict[str, Any],
        *,
        prune_to_targets: bool = False,
    ) -> dict[str, Any]:
        decisions_file = self.run_dir(run_id) / "decisions.json"
        snapshot = read_json(decisions_file) if decisions_file.is_file() else None
        candidates_by_id = {c["candidateId"]: c for c in candidates}
        state = load_decision_state(snapshot, candidates_by_id)
        if prune_to_targets:
            targets = set(selection["targets"])
            state["decisions"] = {
                key: record for key, record in state["decisions"].items() if record["model"] in targets
            }
        return state

    def _write_decisions(
        self, run_id: str, decisions: dict[str, dict[str, Any]], selection: dict[str, Any]
    ) -> None:
        write_json(
            self.run_dir(run_id) / "decisions.json",
            {
                "schemaVersion": SCHEMA_VERSION_B2,
                "candidatesFingerprint": selection["candidatesFingerprint"],
                "decisions": sorted(decisions.values(), key=lambda record: record["decisionId"]),
            },
        )

    def review_queue(
        self,
        run_id: str,
        model: str,
        lane: str,
        *,
        query: str = "",
        template: str = "",
        source_section: str = "",
        price_match: str = "",
    ) -> dict[str, Any]:
        session, candidates_file, candidates = self._parsed_candidates(run_id)
        selection = self._load_selection(run_id, candidates_file)
        if model not in selection["targets"]:
            raise WizardError(f"Model {model} is not a selected target.")
        if lane not in {entry["lane"] for entry in LANES}:
            raise WizardError(f"Unknown lane: {lane}")
        state = self._decision_state(run_id, candidates, selection)
        scoped = scope_candidates(candidates, model)
        if lane == "standard_equipment":
            # Rows without an orderable RPO, plus rows the reviewer assigned to
            # a standard-behavior section — never plain selectable options.
            standard_sections = {
                s["sectionId"] for s in workbook_sections(self._require_workbook()) if s["standardBehavior"]
            }
            standard_assigned = {
                record.get("candidateId")
                for record in state["decisions"].values()
                if record["model"] == model
                and record["lane"] == "section"
                and (record.get("payload") or {}).get("sectionId") in standard_sections
            }
            scoped = [
                c for c in scoped if c["rowKind"] == "ref_only" or c["candidateId"] in standard_assigned
            ]
        else:
            scoped = [c for c in scoped if c["rowKind"] == "orderable"]
        if lane == "status_nuance":
            # Only rows whose availability symbols actually need a human read.
            scoped = [c for c in scoped if candidate_needs_status_review(c)]
        source_sections = sorted({c["sectionLabel"] for c in scoped if c["sectionLabel"]})
        if source_section:
            scoped = [c for c in scoped if c["sectionLabel"] == source_section]
        if price_match:
            scoped = [c for c in scoped if (c.get("priceMatch") or "") == price_match]
        if query:
            needle = query.lower()
            scoped = [
                c
                for c in scoped
                if needle in c["rpo"].lower()
                or needle in c["refOnlyRpo"].lower()
                or needle in c["description"].lower()
            ]
        payload: dict[str, Any] = {
            "session": session,
            "model": model,
            "lane": lane,
            "sourceSections": source_sections,
            "candidates": scoped,
            "decisions": [
                record
                for record in state["decisions"].values()
                if record["model"] == model and record["lane"] == lane
            ],
            "invalidated": [
                record
                for record in state["invalidated"]
                if record.get("model") == model and record.get("lane") == lane
            ],
        }
        lane_config = next(entry for entry in LANES if entry["lane"] == lane)
        if lane_config["perCandidate"]:
            reference = self._option_reference()
            preferred = selection["comparators"].get(model, "")
            payload["workbookReference"] = {
                rpo: sorted(rows, key=lambda row: row["modelKey"] != preferred)
                for rpo in {c["rpo"] for c in scoped if c["rpo"]}
                if (rows := reference.get(rpo))
            }
        if lane in ("section", "exclusive_group"):
            payload["sections"] = workbook_sections(self._require_workbook())
        if lane == "exclusive_group":
            # Pool picker context: each option's decided section, so the UI can
            # show selection modes and group accurately.
            payload["sectionDecisions"] = {
                record["candidateId"]: (record.get("payload") or {}).get("sectionId", "")
                for record in state["decisions"].values()
                if record["model"] == model and record["lane"] == "section" and record.get("candidateId")
            }
        if lane == "relationship":
            payload["hints"] = scan_candidates(scoped)
        if lane == "copy_split":
            for candidate in scoped:
                candidate["proposedSplit"] = propose_copy_split(candidate)
        if lane == "duplicate":
            payload["duplicateGroups"] = duplicate_rpo_groups(scoped)
        if lane == "interior_media_deferral":
            payload["suggestedDeferrals"] = [
                {
                    "groupKey": f"{model}-interior-scope",
                    "kind": "interior",
                    "label": "Interior scope rows",
                    "why": "Color & Trim sheets aren't parsed; model_interior_scope rows must be authored in the apply pass.",
                },
                {
                    "groupKey": f"{model}-color-overrides",
                    "kind": "color",
                    "label": "Color overrides check",
                    "why": "Confirm shared color_overrides rows cover this model or record what's missing.",
                },
                {
                    "groupKey": f"{model}-asset-images",
                    "kind": "asset",
                    "label": "Asset images (asset_map)",
                    "why": "Not a go-live blocker (resolved decision 5) — record so it stays on the list after promotion.",
                },
            ]
        if lane == "presentation":
            template_model = template or selection["comparators"].get(model, "")
            if not template_model:
                raise WizardError("Presentation prefill needs a template model.")
            payload["prefill"] = presentation_prefill(self._require_workbook(), template_model, model)
        return payload

    def save_decisions(self, run_id: str, decisions: list[dict[str, Any]]) -> dict[str, Any]:
        session, candidates_file, candidates = self._parsed_candidates(run_id)
        selection = self._load_selection(run_id, candidates_file)
        if not isinstance(decisions, list) or not decisions:
            raise WizardError("Request must carry a non-empty decisions list.")
        candidates_by_id = {c["candidateId"]: c for c in candidates}
        state = self._decision_state(run_id, candidates, selection)
        batch_id = uuid.uuid4().hex[:12]
        accepted: list[dict[str, Any]] = []
        for decision in decisions:
            try:
                record = validate_decision(decision, candidates_by_id)
            except ValueError as exc:
                raise WizardError(str(exc)) from exc
            if record["model"] not in selection["targets"]:
                raise WizardError(f"Decision targets non-selected model: {record['model']}")
            record["batchId"] = batch_id
            state["decisions"][record["decisionId"]] = record
            accepted.append(record)
        run_dir = self.run_dir(run_id)
        with (run_dir / "decisions-log.jsonl").open("a", encoding="utf-8") as log:
            for record in accepted:
                log.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._write_decisions(run_id, state["decisions"], selection)
        if session["state"] in (STATE_MODELS_SELECTED, STATE_DECISIONS_COMPLETE, STATE_PLAN_BUILT, STATE_PLAN_APPROVED):
            session["state"] = STATE_DECISIONS_IN_PROGRESS
            write_json(run_dir / "session.json", session)
        return {
            "session": session,
            "batchId": batch_id,
            "accepted": [record["decisionId"] for record in accepted],
        }

    def delete_decisions(
        self,
        run_id: str,
        *,
        decision_ids: list[str] | None = None,
        batch_id: str = "",
    ) -> dict[str, Any]:
        session, candidates_file, candidates = self._parsed_candidates(run_id)
        selection = self._load_selection(run_id, candidates_file)
        if not decision_ids and not batch_id:
            raise WizardError("Delete needs decisionIds or a batchId.")
        state = self._decision_state(run_id, candidates, selection)
        targets = set(decision_ids or [])
        deleted: list[str] = []
        for key, record in list(state["decisions"].items()):
            if key in targets or (batch_id and record.get("batchId") == batch_id):
                del state["decisions"][key]
                deleted.append(key)
        if deleted:
            run_dir = self.run_dir(run_id)
            with (run_dir / "decisions-log.jsonl").open("a", encoding="utf-8") as log:
                log.write(
                    json.dumps(
                        {
                            "deleted": deleted,
                            "batchId": batch_id or None,
                            "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
            self._write_decisions(run_id, state["decisions"], selection)
            if session["state"] in (STATE_DECISIONS_COMPLETE, STATE_PLAN_BUILT, STATE_PLAN_APPROVED):
                session["state"] = STATE_DECISIONS_IN_PROGRESS
                write_json(run_dir / "session.json", session)
        return {"session": session, "deleted": deleted}

    def copy_model_decisions(
        self, run_id: str, from_model: str, to_model: str, *, overwrite: bool = False
    ) -> dict[str, Any]:
        session, candidates_file, candidates = self._parsed_candidates(run_id)
        selection = self._load_selection(run_id, candidates_file)
        if from_model not in selection["targets"] or to_model not in selection["targets"]:
            raise WizardError("Copy source and target must both be selected target models.")
        state = self._decision_state(run_id, candidates, selection)
        try:
            report = copy_decisions(
                state["decisions"], candidates, from_model, to_model, overwrite=overwrite
            )
        except ValueError as exc:
            raise WizardError(str(exc)) from exc
        run_dir = self.run_dir(run_id)
        batch_id = uuid.uuid4().hex[:12]
        if report["copied"]:
            for record in report["copied"]:
                record["batchId"] = batch_id
                state["decisions"][record["decisionId"]] = record
            with (run_dir / "decisions-log.jsonl").open("a", encoding="utf-8") as log:
                for record in report["copied"]:
                    log.write(json.dumps(record, ensure_ascii=False) + "\n")
            self._write_decisions(run_id, state["decisions"], selection)
            if session["state"] in (STATE_MODELS_SELECTED, STATE_DECISIONS_COMPLETE):
                session["state"] = STATE_DECISIONS_IN_PROGRESS
                write_json(run_dir / "session.json", session)
        return {
            "session": session,
            "batchId": batch_id if report["copied"] else None,
            "copied": len(report["copied"]),
            "copiedByLane": report["copiedByLane"],
            "skipped": report["skipped"],
        }

    def progress(self, run_id: str) -> dict[str, Any]:
        session, candidates_file, candidates = self._parsed_candidates(run_id)
        selection = self._load_selection(run_id, candidates_file)
        state = self._decision_state(run_id, candidates, selection)
        reconciliation_file = self.run_dir(run_id) / "variant-reconciliation.json"
        reconciliation = read_json(reconciliation_file) if reconciliation_file.is_file() else None
        report = completeness(candidates, selection["targets"], state["decisions"], reconciliation)
        report["session"] = session
        report["invalidatedDecisions"] = len(state["invalidated"])
        return report

    # ------------------------------------------------------ pass c: plan
    def build_apply_plan(self, run_id: str, *, schema_validation: bool = True) -> dict[str, Any]:
        """Build the two-stage op plan and dry-run it. Stage 1 validates
        against the live extract; stage 2 against a scratch copy with stage 1
        applied. The live workbook is never written here.

        schema_validation=False exists for fixture-scale tests whose compact
        workbooks are not schema-complete; real runs keep it on."""

        import shutil
        import tempfile

        from corvette_form_generator.editor_ops import apply_batch
        from corvette_form_generator.ingest.wizard.plan_builder import build_plan

        session = self.load_session(run_id, verify_source=False)
        if session["state"] not in (STATE_DECISIONS_COMPLETE, STATE_PLAN_BUILT, STATE_PLAN_APPROVED):
            raise WizardError("Mark decisions complete before building the apply plan.", status=409)
        run_dir = self.run_dir(run_id)
        _, candidates_file, candidates = self._parsed_candidates(run_id)
        selection = self._load_selection(run_id, candidates_file)
        state = self._decision_state(run_id, candidates, selection)
        workbook = self._require_workbook()
        plan = build_plan(
            workbook_path=workbook,
            selection=selection,
            candidates=candidates,
            decisions=state["decisions"],
            candidates_fingerprint=selection["candidatesFingerprint"],
        )

        def summarize(result: dict[str, Any]) -> dict[str, Any]:
            return {
                "ok": result.get("ok", False),
                "status": result.get("status", ""),
                "errors": result.get("errors", []),
                "warnings": result.get("warnings", []),
                "opCount": result.get("opCount"),
                "schemaErrors": (result.get("schemaResult") or {}).get("error_count"),
            }

        dry_run: dict[str, Any] = {}
        stage1_batch = {
            "workbookMtimeNs": str(workbook.stat().st_mtime_ns),
            "items": plan["stage1"]["items"],
        }
        dry_run["stage1"] = summarize(
            apply_batch(workbook, stage1_batch, write=False, run_schema_validation=False)
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            scratch = Path(tmp_dir) / workbook.name
            shutil.copy2(workbook, scratch)
            stage1_scratch = dict(stage1_batch, workbookMtimeNs=str(scratch.stat().st_mtime_ns))
            applied = apply_batch(
                scratch, stage1_scratch, write=True, run_schema_validation=False,
                confirmed_warnings=[w["id"] for w in dry_run["stage1"]["warnings"]],
                log_path=run_dir / "scratch-apply-log.jsonl",
            )
            dry_run["stage1Scratch"] = summarize(applied)
            if applied.get("ok"):
                stage2_batch = {
                    "workbookMtimeNs": str(scratch.stat().st_mtime_ns),
                    "items": plan["stage2"]["items"],
                }
                dry_run["stage2"] = summarize(
                    apply_batch(scratch, stage2_batch, write=False, run_schema_validation=schema_validation)
                )
            else:
                dry_run["stage2"] = {"ok": False, "status": "skipped", "errors": ["stage 1 scratch apply failed"], "warnings": []}
        dry_run["ok"] = bool(
            plan["valid"] and dry_run["stage1"]["ok"] and dry_run["stage1Scratch"]["ok"] and dry_run["stage2"]["ok"]
        )

        write_json(run_dir / "apply-plan.json", plan)
        write_json(run_dir / "apply-plan-dryrun.json", dry_run)
        (run_dir / "apply-plan.md").write_text(plan_markdown(plan, dry_run), encoding="utf-8")
        session["state"] = STATE_PLAN_BUILT if dry_run["ok"] else STATE_DECISIONS_COMPLETE
        write_json(run_dir / "session.json", session)
        return {"session": session, "plan": plan_summary(plan), "dryRun": dry_run}

    def plan_detail(self, run_id: str) -> dict[str, Any]:
        run_dir = self.run_dir(run_id)
        plan_file = run_dir / "apply-plan.json"
        if not plan_file.is_file():
            raise WizardError("Build the apply plan first.", status=404)
        plan = read_json(plan_file)
        dry_file = run_dir / "apply-plan-dryrun.json"
        approval_file = run_dir / "plan-approval.json"
        return {
            "session": self.load_session(run_id, verify_source=False),
            "plan": plan_summary(plan),
            "dryRun": read_json(dry_file) if dry_file.is_file() else None,
            "approval": read_json(approval_file) if approval_file.is_file() else None,
        }

    def approve_plan(self, run_id: str, approver: str) -> dict[str, Any]:
        session = self.load_session(run_id, verify_source=False)
        if session["state"] != STATE_PLAN_BUILT:
            raise WizardError("Plan must be built (and dry-run clean) before approval.", status=409)
        if not str(approver or "").strip():
            raise WizardError("Approval needs a reviewer name.")
        run_dir = self.run_dir(run_id)
        plan = read_json(run_dir / "apply-plan.json")
        # Fail closed if anything shifted since the plan was built.
        _, candidates_file, candidates = self._parsed_candidates(run_id)
        selection = self._load_selection(run_id, candidates_file)
        state = self._decision_state(run_id, candidates, selection)
        if plan["decisionsFingerprint"] != artifact_sha(state["decisions"]):
            raise WizardError("Decisions changed after the plan was built; rebuild the plan.", status=409)
        workbook = self._require_workbook()
        if plan["workbookFingerprint"]["mtimeNs"] != str(workbook.stat().st_mtime_ns) or plan[
            "workbookFingerprint"
        ]["sha256"] != hashlib.sha256(workbook.read_bytes()).hexdigest():
            raise WizardError("Workbook changed after the plan was built; rebuild the plan.", status=409)
        approval = {
            "schemaVersion": plan["schemaVersion"],
            "approvedBy": str(approver).strip(),
            "approvedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "planSha": hashlib.sha256((run_dir / "apply-plan.json").read_bytes()).hexdigest(),
        }
        write_json(run_dir / "plan-approval.json", approval)
        session["state"] = STATE_PLAN_APPROVED
        write_json(run_dir / "session.json", session)
        return {"session": session, "approval": approval}

    def mark_complete(self, run_id: str) -> dict[str, Any]:
        report = self.progress(run_id)
        if not report["allComplete"]:
            blockers = {
                model: entry["blockers"] for model, entry in report["models"].items() if entry["blockers"]
            }
            raise WizardError(
                "Decisions are not complete; blocking items remain: " + json.dumps(blockers)[:2000],
                status=409,
            )
        run_dir = self.run_dir(run_id)
        session = self.load_session(run_id, verify_source=False)
        session["state"] = STATE_DECISIONS_COMPLETE
        write_json(run_dir / "session.json", session)
        report["session"] = session
        return report
