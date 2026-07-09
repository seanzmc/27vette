#!/usr/bin/env python3
"""Run-state persistence and fail-closed state machine for the ingest wizard.

States: profiled -> roles_confirmed -> parsed (Pass A), then
models_selected -> decisions_in_progress -> decisions_complete (Pass B), then
plan_built -> plan_approved (Pass C).
Every transition persists JSON artifacts under
form-output/ingest-wizard/<run-id>/ so a run can be reopened and later passes
can consume the output. The canonical workbook is opened read-only for
pickers, variant reconciliation, presentation prefill, and Pass C dry-runs;
it and the raw source file are never written by this store.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from corvette_form_generator.ingest.wizard.decisions import (
    LANES,
    SCHEMA_VERSION_B,
    SCHEMA_VERSION_B2,
    VARIANT_RECONCILIATION_KEY,
    artifact_fingerprint,
    candidate_has_price,
    candidate_is_availability_row,
    candidate_needs_section_decision,
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
from corvette_form_generator.ingest.wizard.copy_split import FLAG_DUPLICATE_NAME, propose_copy_split
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
STATE_APPLIED = "applied"
SCHEMA_VERSION_D = "pass-d-1"
DECISION_STATES = (
    STATE_MODELS_SELECTED,
    STATE_DECISIONS_IN_PROGRESS,
    STATE_DECISIONS_COMPLETE,
    STATE_PLAN_BUILT,
    STATE_PLAN_APPROVED,
    STATE_APPLIED,
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

    def _refuse_if_applied(self, session: dict[str, Any]) -> None:
        if session.get("state") == STATE_APPLIED:
            raise WizardError("Run already applied; start a new run for further changes.", status=409)

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
        self._refuse_if_applied(session)
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
        return {
            "session": session,
            "selection": selection,
            "reconciliation": self._attach_reconciliation_decisions(dict(reconciliation), state["decisions"]),
        }

    def _attach_reconciliation_decisions(
        self, reconciliation: dict[str, Any], decisions: dict[str, dict[str, Any]]
    ) -> dict[str, Any]:
        """Show, per model, the recorded variant_reconciliation decision (any
        lane — completeness accepts any group decision with that key)."""

        for model, entry in (reconciliation.get("models") or {}).items():
            record = next(
                (
                    r
                    for r in decisions.values()
                    if r["model"] == model and r.get("groupKey") == VARIANT_RECONCILIATION_KEY
                ),
                None,
            )
            entry["decision"] = (
                {
                    "decisionId": record["decisionId"],
                    "action": record["action"],
                    "resolution": record["resolution"],
                    "reviewerNote": record.get("reviewerNote", ""),
                }
                if record
                else None
            )
        return reconciliation

    def reconciliation(self, run_id: str) -> dict[str, Any]:
        _, candidates_file, candidates = self._parsed_candidates(run_id)
        selection = self._load_selection(run_id, candidates_file)
        state = self._decision_state(run_id, candidates, selection)
        reconciliation = read_json(self.run_dir(run_id) / "variant-reconciliation.json")
        return self._attach_reconciliation_decisions(reconciliation, state["decisions"])

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
        decision_state: str = "",
        price_presence: str = "",
        workbook_ref: str = "",
        section_state: str = "",
    ) -> dict[str, Any]:
        session, candidates_file, candidates = self._parsed_candidates(run_id)
        selection = self._load_selection(run_id, candidates_file)
        if model not in selection["targets"]:
            raise WizardError(f"Model {model} is not a selected target.")
        if lane not in {entry["lane"] for entry in LANES}:
            raise WizardError(f"Unknown lane: {lane}")
        state = self._decision_state(run_id, candidates, selection)
        skipped_section_ids = {
            record.get("candidateId")
            for record in state["decisions"].values()
            if record["model"] == model
            and record["lane"] == "section"
            and record["resolution"] == "not_needed"
            and record.get("candidateId")
        }
        scoped = scope_candidates(candidates, model)
        if lane == "standard_equipment":
            # Rows without an orderable RPO, plus rows the reviewer assigned to
            # a standard-behavior section — never plain selectable options.
            # Ref-only rows that are available-to-order on THIS model's own
            # variant columns (A statuses) are options, not standard equipment.
            # Priced rows (joined price rows or a list price) are options or
            # price problems, never standard equipment (spec B9).
            standard_sections = {
                s["sectionId"] for s in workbook_sections(self._require_workbook()) if s["standardBehavior"]
            }
            # Same approved-assignment predicate as the sectionState filter —
            # a held/skipped section decision is not an assignment yet.
            standard_assigned = {
                record.get("candidateId")
                for record in state["decisions"].values()
                if record["model"] == model
                and record["lane"] == "section"
                and record["resolution"] == "approved_for_plan"
                and record.get("action") == "assign_section"
                and (record.get("payload") or {}).get("sectionId") in standard_sections
            }
            scoped = [
                c
                for c in scoped
                if not candidate_has_price(c)
                and (
                    (c["rowKind"] == "ref_only" and not candidate_is_availability_row(c, model))
                    or c["candidateId"] in standard_assigned
                )
            ]
        elif lane == "section":
            scoped = [c for c in scoped if candidate_needs_section_decision(c)]
        elif lane == "exclusive_group":
            selectable_section_ids = {
                record.get("candidateId")
                for record in state["decisions"].values()
                if record["model"] == model
                and record["lane"] == "section"
                and record["resolution"] == "approved_for_plan"
                and record.get("action") == "assign_section"
                and (record.get("payload") or {}).get("sectionId")
                and (record.get("payload") or {}).get("selectable", True) is not False
                and (record.get("payload") or {}).get("active", True) is not False
            }
            scoped = [
                c
                for c in scoped
                if (c["rpo"] or c["refOnlyRpo"])
                and c["candidateId"] in selectable_section_ids
            ]
        else:
            scoped = [c for c in scoped if c["rowKind"] == "orderable"]
        if lane != "section" and skipped_section_ids:
            scoped = [c for c in scoped if c["candidateId"] not in skipped_section_ids]
        if lane == "status_nuance":
            # Only rows whose availability symbols actually need a human read.
            scoped = [c for c in scoped if candidate_needs_status_review(c)]

        # Source group = the export's own section label where one exists, the
        # sheet name otherwise (Interior/Exterior/Mechanical sheets carry no
        # section-label rows — field note 4).
        def source_group(candidate: dict[str, Any]) -> str:
            return candidate["sectionLabel"] or candidate["sheetName"]

        source_sections = sorted({source_group(c) for c in scoped})
        if source_section:
            scoped = [c for c in scoped if source_group(c) == source_section]
        if price_match:
            scoped = [c for c in scoped if (c.get("priceMatch") or "") == price_match]
        if price_presence:
            if price_presence not in {"priced", "unpriced"}:
                raise WizardError(f"Invalid price presence filter: {price_presence}")
            want_priced = price_presence == "priced"
            scoped = [c for c in scoped if candidate_has_price(c) == want_priced]
        if workbook_ref:
            if workbook_ref not in {"in_workbook", "new"}:
                raise WizardError(f"Invalid workbook reference filter: {workbook_ref}")
            reference_index = self._option_reference()
            want_known = workbook_ref == "in_workbook"
            scoped = [
                c
                for c in scoped
                if bool(reference_index.get(c["rpo"] or c["refOnlyRpo"])) == want_known
            ]
        if section_state:
            if section_state not in {"assigned", "unassigned"}:
                raise WizardError(f"Invalid section state filter: {section_state}")
            assigned_ids = {
                record.get("candidateId")
                for record in state["decisions"].values()
                if record["model"] == model
                and record["lane"] == "section"
                and record["resolution"] == "approved_for_plan"
                and record.get("action") == "assign_section"
                and record.get("candidateId")
            }
            if section_state == "assigned":
                scoped = [c for c in scoped if c["candidateId"] in assigned_ids]
            else:
                scoped = [c for c in scoped if c["candidateId"] not in assigned_ids]
        if decision_state:
            if decision_state not in {"undecided", "decided"}:
                raise WizardError(f"Invalid decision state filter: {decision_state}")
            lane_decided_ids = {
                record.get("candidateId")
                for record in state["decisions"].values()
                if record["model"] == model and record["lane"] == lane and record.get("candidateId")
            }
            if decision_state == "decided":
                scoped = [c for c in scoped if c["candidateId"] in lane_decided_ids]
            else:
                scoped = [
                    c
                    for c in scoped
                    if c["candidateId"] not in lane_decided_ids
                ]
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
                for rpo in {c["rpo"] or c["refOnlyRpo"] for c in scoped if c["rpo"] or c["refOnlyRpo"]}
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
            # Name collisions ("Seats" — one per seat option) need a human
            # rebuild. Count distinct RPOs per name over the FULL model lane
            # scope (not the filtered view, or filters would hide collisions);
            # GM lists the same RPO on two sheets (category sheet + Additional
            # Options) — same-RPO pairs are expected, not collisions.
            rpos_by_name: dict[str, set[str]] = {}
            for candidate in scope_candidates(candidates, model):
                if candidate["rowKind"] != "orderable":
                    continue
                if candidate["candidateId"] in skipped_section_ids:
                    continue
                key = propose_copy_split(candidate)["name"].strip().lower()
                if key:
                    rpos_by_name.setdefault(key, set()).add(candidate["rpo"] or candidate["refOnlyRpo"])
            for candidate in scoped:
                split = candidate["proposedSplit"]
                if len(rpos_by_name.get(split["name"].strip().lower(), set())) > 1:
                    split["flags"].append(FLAG_DUPLICATE_NAME)
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
        self._refuse_if_applied(session)
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
        self._refuse_if_applied(session)
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
        self._refuse_if_applied(session)
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
        self._refuse_if_applied(session)
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
        if session["state"] not in (STATE_PLAN_BUILT, STATE_PLAN_APPROVED):
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

    # ------------------------------------------------------ pass d: apply
    def _combined_plan_batch(self, plan: dict[str, Any], workbook: Path) -> dict[str, Any]:
        return {
            "workbookMtimeNs": str(workbook.stat().st_mtime_ns),
            "items": [*plan["stage1"]["items"], *plan["stage2"]["items"]],
        }

    def _per_sheet_action_counts(self, items: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
        counts: dict[str, dict[str, int]] = {}
        for item in items:
            sheet = item.get("sheet")
            action = item.get("action")
            if not sheet or not action:
                continue
            sheet_counts = counts.setdefault(str(sheet), {})
            sheet_counts[str(action)] = sheet_counts.get(str(action), 0) + 1
        return {sheet: dict(sorted(actions.items())) for sheet, actions in sorted(counts.items())}

    def _deployment_continuity_from_plan(self, plan: dict[str, Any]) -> dict[str, Any]:
        """Action-aware source-coverage diagnostic for the dry-run report.

        The temp generation probe added by Pass D.1 can enrich these entries;
        this source-op layer is intentionally conservative and never treats
        create/delete-only sheet activity as runtime coverage.
        """

        report = plan.get("report") or {}
        plan_continuity = report.get("runtimeContinuity") or {}
        output: dict[str, Any] = {}
        for model in plan.get("targets") or []:
            source_ops = (plan_continuity.get(model) or {}).get("sourceOps") or {}
            price_adds = sum((source_ops.get("priceRules") or {}).get(action, 0) for action in ("add", "update"))
            rule_group_adds = sum((source_ops.get("ruleGroups") or {}).get(action, 0) for action in ("add", "update"))
            color_adds = sum((source_ops.get("colorOverrides") or {}).get(action, 0) for action in ("add", "update"))
            component_adds = sum((source_ops.get("interiorComponents") or {}).get(action, 0) for action in ("add", "update"))
            asset_adds = sum((source_ops.get("assetMap") or {}).get(action, 0) for action in ("add", "update"))
            blockers: list[dict[str, str]] = []
            deferrals: list[dict[str, str]] = []
            if model in {"zr1", "zr1x"} and price_adds == 0:
                blockers.append({"kind": "price_rules_required_for_runtime", "detail": "no price-rule add/update ops"})
            if model in {"zr1", "zr1x"} and rule_group_adds == 0:
                blockers.append({"kind": "rule_groups_required_for_runtime", "detail": "no rule-group add/update ops"})
            if color_adds == 0:
                deferrals.append({"kind": "color_overrides_deferred", "detail": "no color override add/update ops"})
            if component_adds == 0:
                deferrals.append({"kind": "interior_components_deferred", "detail": "no interior component add/update ops"})
            if asset_adds == 0:
                deferrals.append({"kind": "asset_map_deferred", "detail": "no asset_map add/update ops"})
            output[model] = {
                "status": "not_deployment_ready" if blockers else "source_ops_diagnostic",
                "registryLoadable": None,
                "registryLoadableNote": "temp generation probe not run in source-op diagnostic layer",
                "sourceOps": source_ops,
                "sourceCoverage": {
                    "priceRuleAddOrUpdateCount": price_adds,
                    "ruleGroupAddOrUpdateCount": rule_group_adds,
                    "colorOverrideAddOrUpdateCount": color_adds,
                    "interiorComponentAddOrUpdateCount": component_adds,
                    "assetMapAddOrUpdateCount": asset_adds,
                },
                "deploymentBlockers": blockers,
                "deploymentDeferrals": deferrals,
            }
        return output

    def _activate_probe_models(self, workbook: Path, models: list[str]) -> None:
        from openpyxl import load_workbook

        wb = load_workbook(workbook)
        try:
            targets = set(models)
            variant_ids: set[str] = set()
            if "model_variants" in wb.sheetnames:
                ws = wb["model_variants"]
                headers = {str(cell.value): index + 1 for index, cell in enumerate(ws[1]) if cell.value is not None}
                model_col = headers.get("model_key")
                variant_col = headers.get("variant_id")
                if model_col and variant_col:
                    for row in range(2, ws.max_row + 1):
                        model_key = str(ws.cell(row=row, column=model_col).value or "").strip().lower()
                        if model_key in targets:
                            variant_id = str(ws.cell(row=row, column=variant_col).value or "").strip()
                            if variant_id:
                                variant_ids.add(variant_id)
            for sheet_name, fields in {
                "model_master": {"active": True},
                "model_variants": {"active": True},
                "model_workbook_sources": {"active": True},
                "model_registry_promotion": {"active": True, "promoted_to_runtime": True},
            }.items():
                if sheet_name not in wb.sheetnames:
                    continue
                ws = wb[sheet_name]
                headers = {str(cell.value): index + 1 for index, cell in enumerate(ws[1]) if cell.value is not None}
                model_col = headers.get("model_key")
                if not model_col:
                    continue
                for row in range(2, ws.max_row + 1):
                    model_key = str(ws.cell(row=row, column=model_col).value or "").strip().lower()
                    if model_key not in targets:
                        if sheet_name == "model_master" and "active" in headers:
                            ws.cell(row=row, column=headers["active"], value=False)
                        continue
                    for column, value in fields.items():
                        if column in headers:
                            ws.cell(row=row, column=headers[column], value=value)
                    if sheet_name == "model_registry_promotion":
                        if "artifact_type" in headers:
                            ws.cell(row=row, column=headers["artifact_type"], value="runtime_contract")
                        if "artifact_path" in headers:
                            ws.cell(
                                row=row,
                                column=headers["artifact_path"],
                                value=f"form-output/runtime/{model_key.replace('_', '-')}-runtime-contract.json",
                            )
            if variant_ids and "variant_master" in wb.sheetnames:
                ws = wb["variant_master"]
                headers = {str(cell.value): index + 1 for index, cell in enumerate(ws[1]) if cell.value is not None}
                variant_col = headers.get("variant_id")
                active_col = headers.get("active")
                if variant_col and active_col:
                    for row in range(2, ws.max_row + 1):
                        variant_id = str(ws.cell(row=row, column=variant_col).value or "").strip()
                        if variant_id in variant_ids:
                            ws.cell(row=row, column=active_col, value=True)
            wb.save(workbook)
        finally:
            wb.close()

    def _source_count(self, payload: dict[str, Any], key: str) -> int:
        value = payload.get(key)
        return len(value) if isinstance(value, list) else 0

    def _deployment_continuity_probe(
        self,
        workbook: Path,
        batch: dict[str, Any],
        plan: dict[str, Any],
        *,
        schema_validation: bool,
    ) -> dict[str, Any]:
        """Apply the plan to a temp workbook and run temp-only generation probes."""

        import shutil
        import tempfile

        from corvette_form_generator.contract import ASSET_IMAGE_FIELDS
        from corvette_form_generator.editor_ops import apply_batch
        from corvette_form_generator.model_configs import discover_generation_model_configs
        from corvette_form_generator.source_assembly import assemble_model_source

        targets = [str(model) for model in plan.get("targets") or []]
        continuity = self._deployment_continuity_from_plan(plan)
        if not targets:
            return continuity
        with tempfile.TemporaryDirectory(prefix="ingest-d1-deployment-") as tmp_dir:
            tmp_root = Path(tmp_dir)
            tmp_workbook = tmp_root / workbook.name
            shutil.copy2(workbook, tmp_workbook)
            temp_batch = dict(batch, workbookMtimeNs=str(tmp_workbook.stat().st_mtime_ns))
            preview = apply_batch(tmp_workbook, temp_batch, write=False, run_schema_validation=schema_validation)
            confirmed = [warning["id"] for warning in preview.get("warnings", [])]
            applied = apply_batch(
                tmp_workbook,
                temp_batch,
                write=True,
                confirmed_warnings=confirmed,
                source="ingest_wizard_deployment_probe",
                log_path=tmp_root / "probe-edit-log.jsonl",
                run_schema_validation=schema_validation,
            )
            if not applied.get("ok"):
                error = "; ".join(applied.get("errors", [])) or str(applied.get("status"))
                for model in targets:
                    entry = continuity.setdefault(model, {})
                    blockers = list(entry.get("deploymentBlockers") or [])
                    blockers.append({"kind": "deployment_probe_apply_failed", "detail": error})
                    entry.update(
                        {
                            "status": "probe_apply_failed",
                            "registryLoadable": False,
                            "registryError": error,
                            "deploymentBlockers": blockers,
                        }
                    )
                return continuity

            self._activate_probe_models(tmp_workbook, targets)
            try:
                configs = discover_generation_model_configs(tmp_workbook)
            except Exception as exc:
                configs = {}
                discovery_error = str(exc)
            else:
                discovery_error = ""

            for model in targets:
                entry = continuity.setdefault(model, {})
                blockers = list(entry.get("deploymentBlockers") or [])
                deferrals = list(entry.get("deploymentDeferrals") or [])
                config = configs.get(model)
                if config is None:
                    error = discovery_error or f"model {model!r} was not discoverable after temp activation"
                    blockers.append({"kind": "registry_load_failed", "detail": error})
                    entry.update(
                        {
                            "status": "not_deployment_ready",
                            "registryLoadable": False,
                            "registryError": error,
                            "deploymentBlockers": blockers,
                            "deploymentDeferrals": deferrals,
                        }
                    )
                    continue

                config = config.with_overrides(
                    workbook_path=tmp_workbook,
                    output_dir=tmp_root / "form-output",
                    app_dir=tmp_root / "form-app",
                )
                try:
                    assembly = assemble_model_source(config)
                except Exception as exc:
                    blockers.append({"kind": "registry_load_failed", "detail": str(exc)})
                    entry.update(
                        {
                            "status": "not_deployment_ready",
                            "registryLoadable": False,
                            "registryError": str(exc),
                            "deploymentBlockers": blockers,
                            "deploymentDeferrals": deferrals,
                        }
                    )
                    continue

                source = assembly.source_data
                raw_validation = source.get("validation")
                validation: list[dict[str, Any]] = raw_validation if isinstance(raw_validation, list) else []
                pricing_deferred = any(row.get("check_id") == "pricing_deferred" for row in validation if isinstance(row, dict))
                raw_choices = source.get("choices")
                choices: list[dict[str, Any]] = raw_choices if isinstance(raw_choices, list) else []
                raw_interiors = source.get("interiors")
                interiors: list[dict[str, Any]] = raw_interiors if isinstance(raw_interiors, list) else []
                media_count = sum(
                    1
                    for choice in choices
                    if isinstance(choice, dict) and any(choice.get(field) for field in ASSET_IMAGE_FIELDS)
                )
                component_count = sum(
                    len(interior.get("interior_components") or [])
                    for interior in interiors
                    if isinstance(interior, dict) and isinstance(interior.get("interior_components"), list)
                )
                counts = {
                    "choices": len(choices),
                    "directRules": self._source_count(source, "rules"),
                    "ruleGroups": self._source_count(source, "ruleGroups"),
                    "exclusiveGroups": self._source_count(source, "exclusiveGroups"),
                    "priceRules": self._source_count(source, "priceRules"),
                    "pricingDeferred": pricing_deferred,
                    "colorOverrides": self._source_count(source, "colorOverrides"),
                    "interiors": len(interiors),
                    "interiorComponentLineItems": component_count,
                    "optionMediaCoveredChoices": media_count,
                    "optionMediaTotalChoices": len(choices),
                    "validationWarnings": sum(1 for row in validation if isinstance(row, dict) and row.get("severity") == "warning"),
                    "validationErrors": sum(1 for row in validation if isinstance(row, dict) and row.get("severity") == "error"),
                }
                if model in {"zr1", "zr1x"} and counts["priceRules"] == 0 and pricing_deferred:
                    blockers.append({"kind": "price_rules_required_for_runtime", "detail": "generated contract has pricing_deferred and zero priceRules"})
                if model in {"zr1", "zr1x"} and counts["ruleGroups"] == 0:
                    blockers.append({"kind": "rule_groups_required_for_runtime", "detail": "generated contract has zero ruleGroups"})
                if counts["colorOverrides"] == 0:
                    deferrals.append({"kind": "color_overrides_deferred", "detail": "generated contract has zero colorOverrides"})
                if counts["interiorComponentLineItems"] == 0:
                    deferrals.append({"kind": "interior_components_deferred", "detail": "generated contract has zero interior component line items"})
                if counts["optionMediaCoveredChoices"] == 0:
                    deferrals.append({"kind": "asset_map_deferred", "detail": "generated choices have zero option/card asset fields"})
                entry.update(
                    {
                        "status": "not_deployment_ready" if blockers else "deployment_probe_passed",
                        "registryLoadable": True,
                        "registryError": "",
                        "counts": counts,
                        "deploymentBlockers": blockers,
                        "deploymentDeferrals": deferrals,
                    }
                )
            return continuity

    def _verify_applied_ops(self, workbook: Path, batch: dict[str, Any]) -> dict[str, Any]:
        from corvette_form_generator.editor_ops import extract_workbook

        extract = extract_workbook(workbook)
        mismatches: list[str] = []
        checked = 0
        for item in batch.get("items") or []:
            action = item.get("action")
            if action == "create_sheet":
                checked += 1
                if item.get("sheet") not in extract["sheets"]:
                    mismatches.append(f"missing created sheet {item.get('sheet')}")
                continue
            sheet = item.get("sheet")
            key = item.get("key") or {}
            rows = extract["sheets"].get(sheet, {}).get("rows", [])
            found = next(
                (
                    row
                    for row in rows
                    if all(
                        str(row.get(column) or "").strip() == str(value or "").strip()
                        for column, value in key.items()
                    )
                ),
                None,
            )
            checked += 1
            if action in ("add", "update") and found is None:
                mismatches.append(f"missing {sheet} {key}")
            if action == "delete" and found is not None:
                mismatches.append(f"delete still present {sheet} {key}")
        return {"checked": checked, "mismatches": mismatches}

    def apply_approved_plan(
        self,
        run_id: str,
        *,
        write: bool = False,
        confirm_plan_warnings: bool = False,
        schema_validation: bool = True,
    ) -> dict[str, Any]:
        """Apply the approved Pass C plan as one combined Pass D batch.

        Default is dry-run/report only. Real writes require the run to be in
        ``plan_approved`` and all approval, source, decision, and workbook
        fingerprints to still match the built plan.
        """

        from corvette_form_generator.editor_ops import apply_batch

        started_at = datetime.now().isoformat(timespec="seconds")
        session = self.load_session(run_id)
        if session["state"] == STATE_APPLIED:
            raise WizardError("Run already applied; start a new run for further changes.", status=409)
        if session["state"] != STATE_PLAN_APPROVED:
            raise WizardError("Apply requires an approved plan.", status=409)

        run_dir = self.run_dir(run_id)
        plan_file = run_dir / "apply-plan.json"
        approval_file = run_dir / "plan-approval.json"
        if not plan_file.is_file() or not approval_file.is_file():
            raise WizardError("Apply requires apply-plan.json and plan-approval.json.", status=409)

        plan = read_json(plan_file)
        approval = read_json(approval_file)
        plan_sha = hashlib.sha256(plan_file.read_bytes()).hexdigest()
        if approval.get("planSha") != plan_sha:
            raise WizardError("Plan approval hash does not match apply-plan.json; rebuild and re-approve.", status=409)
        if not plan.get("valid"):
            raise WizardError("Apply plan is not valid; rebuild before applying.", status=409)
        plan_schema = plan.get("schemaVersion")
        if write and plan_schema != "pass-c-2":
            raise WizardError(
                f"Plan schema {plan_schema!r} is superseded for live write; rebuild as pass-c-2 and re-approve.",
                status=409,
            )

        _, candidates_file, candidates = self._parsed_candidates(run_id)
        selection = self._load_selection(run_id, candidates_file)
        state = self._decision_state(run_id, candidates, selection)
        if plan["decisionsFingerprint"] != artifact_sha(state["decisions"]):
            raise WizardError("Decisions changed after the plan was approved; rebuild the plan.", status=409)
        source_fingerprint = (plan.get("sourceFingerprint") or selection.get("sourceFingerprint") or {})
        if source_fingerprint.get("sha256") != session["fingerprint"].get("sha256"):
            raise WizardError("Source fingerprint changed after the plan was approved; start a new run.", status=409)

        workbook = self._require_workbook()
        before = file_fingerprint(workbook)
        expected = plan["workbookFingerprint"]
        if expected.get("mtimeNs") != str(before["mtimeNs"]) or expected.get("sha256") != before["sha256"]:
            raise WizardError("Workbook changed after the plan was approved; rebuild the plan.", status=409)

        batch = self._combined_plan_batch(plan, workbook)
        per_sheet_action_counts = self._per_sheet_action_counts(batch["items"])
        per_sheet_counts: dict[str, int] = {}
        for item in batch["items"]:
            sheet = item.get("sheet")
            if sheet:
                per_sheet_counts[str(sheet)] = per_sheet_counts.get(str(sheet), 0) + 1
        confirmed_warnings: list[str] = []
        if write and confirm_plan_warnings:
            preview = apply_batch(workbook, batch, write=False, run_schema_validation=schema_validation)
            confirmed_warnings = [warning["id"] for warning in preview.get("warnings", [])]
        log_path = run_dir / "apply-workbook-edit-log.jsonl"
        result = apply_batch(
            workbook,
            batch,
            write=write,
            source="ingest_wizard_apply",
            confirmed_warnings=confirmed_warnings,
            log_path=log_path,
            run_schema_validation=schema_validation,
        )
        if write and not result.get("ok"):
            return result
        after = file_fingerprint(workbook)
        completed_at = datetime.now().isoformat(timespec="seconds")
        verification = self._verify_applied_ops(workbook, batch) if write else {"checked": 0, "mismatches": []}
        deployment_continuity = (
            self._deployment_continuity_probe(
                workbook,
                batch,
                plan,
                schema_validation=schema_validation,
            )
            if result.get("ok")
            else {}
        )
        report = {
            "schemaVersion": SCHEMA_VERSION_D,
            "planSchemaVersion": plan.get("schemaVersion"),
            "planSupersededForWrite": plan.get("schemaVersion") != "pass-c-2",
            "liveWriteBlockedReason": (
                None
                if plan.get("schemaVersion") == "pass-c-2"
                else "Plan must be rebuilt as pass-c-2 and re-approved before live write."
            ),
            "runId": run_id,
            "startedAt": started_at,
            "completedAt": completed_at,
            "appliedAt": completed_at,
            "write": write,
            "status": result["status"],
            "ok": result["ok"],
            "planSha": plan_sha,
            "approvedBy": approval.get("approvedBy"),
            "approvedAt": approval.get("approvedAt"),
            "approval": approval,
            "opCounts": {
                "stage1": len(plan["stage1"]["items"]),
                "stage2": len(plan["stage2"]["items"]),
                "combined": len(batch["items"]),
            },
            "perSheetCounts": dict(sorted(per_sheet_counts.items())),
            "perSheetActionCounts": per_sheet_action_counts,
            "runtimeContinuity": (plan.get("report") or {}).get("runtimeContinuity", {}),
            "deploymentContinuity": deployment_continuity,
            "workbookBefore": before,
            "workbookAfter": after,
            "warnings": result.get("warnings", []),
            "confirmedWarnings": confirmed_warnings,
            "warningsConfirmed": confirmed_warnings,
            "applyResult": result,
            "schemaResult": result.get("schemaResult"),
            "boolHygieneResult": result.get("boolHygieneResult"),
            "gateReminders": result.get("gateReminders", []),
            "sheets": result.get("sheets", []),
            "backupPath": result.get("backupPath"),
            "workbookEditLogPath": result.get("logPath"),
            "verification": verification,
        }
        report_path = run_dir / ("apply-report.json" if write else "apply-dry-run-report.json")
        write_json(report_path, report)
        if not result.get("ok"):
            result["reportPath"] = str(report_path)
            result["verification"] = verification
            return result
        if write:
            session["state"] = STATE_APPLIED
            session["appliedAt"] = report["appliedAt"]
            session["applyReport"] = "apply-report.json"
            write_json(run_dir / "session.json", session)
        result["reportPath"] = str(report_path)
        result["verification"] = verification
        return result

    def mark_complete(self, run_id: str) -> dict[str, Any]:
        session = self.load_session(run_id, verify_source=False)
        self._refuse_if_applied(session)
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
