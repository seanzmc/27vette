#!/usr/bin/env python3
"""Run-state persistence and fail-closed state machine for the ingest wizard.

States: profiled -> roles_confirmed -> parsed (Pass A), then
models_selected -> decisions_in_progress -> decisions_complete (Pass B), then
plan_built -> dry_run_approved -> dry_run_validated_* (Pass C/D evidence).
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
# Historical runs used this state and may still produce dry-run evidence. It
# is never live-write authority.
STATE_PLAN_APPROVED = "plan_approved"
STATE_DRY_RUN_APPROVED = "dry_run_approved"
STATE_DRY_RUN_VALIDATED_WRITE_BLOCKED = "dry_run_validated_write_blocked"
STATE_DRY_RUN_VALIDATED_WRITE_ELIGIBLE = "dry_run_validated_write_eligible"
STATE_WRITE_APPROVED = "write_approved"
STATE_APPLIED = "applied"
STATE_APPLY_VERIFICATION_FAILED = "apply_verification_failed"
PLAN_APPROVAL_SCHEMA = "plan-approval-2"
PLAN_APPROVAL_SCOPE = "dry_run_evidence"
WRITE_APPROVAL_SCHEMA = "write-approval-1"
WRITE_APPROVAL_SCOPE = "deployment_ready_write"
SCHEMA_VERSION_D = "pass-d-2"
WRITABLE_PLAN_SCHEMA = "pass-c-3"
ALLOWED_WRITE_DEFERRAL_KINDS = {
    "asset_map_deferred",
    "color_overrides_deferred",
    "interior_components_deferred",
}
COMPILER_ARTIFACT_BINDINGS = (
    ("canonical-row-manifest.json", "canonicalManifestSha"),
    ("compile-report.json", "compileReportSha"),
    ("exception-resolutions.json", "exceptionResolutionsSha"),
)
DECISION_STATES = (
    STATE_MODELS_SELECTED,
    STATE_DECISIONS_IN_PROGRESS,
    STATE_DECISIONS_COMPLETE,
    STATE_PLAN_BUILT,
    STATE_PLAN_APPROVED,
    STATE_DRY_RUN_APPROVED,
    STATE_DRY_RUN_VALIDATED_WRITE_BLOCKED,
    STATE_DRY_RUN_VALIDATED_WRITE_ELIGIBLE,
    STATE_WRITE_APPROVED,
    STATE_APPLIED,
    STATE_APPLY_VERIFICATION_FAILED,
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
        if session.get("state") == STATE_APPLY_VERIFICATION_FAILED:
            raise WizardError(
                "The last apply failed verification; restore or reconcile it before continuing.",
                status=409,
            )

    def _compiler_artifact_bindings(self, run_dir: Path) -> dict[str, str]:
        """Return only compiler hashes that actually exist for this run.

        Milestone 0 diagnostic runs predate the compiler, so absent hashes are
        deliberately omitted rather than represented by sentinel values.
        """

        bindings: dict[str, str] = {}
        for filename, field in COMPILER_ARTIFACT_BINDINGS:
            path = run_dir / filename
            if path.is_file():
                bindings[field] = hashlib.sha256(path.read_bytes()).hexdigest()
        return bindings

    def _require_compiler_bindings(
        self,
        run_dir: Path,
        plan: dict[str, Any],
        *approvals: tuple[str, dict[str, Any]],
    ) -> dict[str, str]:
        current: dict[str, str] = {}
        for filename, field in COMPILER_ARTIFACT_BINDINGS:
            path = run_dir / filename
            if not path.is_file():
                raise WizardError(
                    f"{WRITABLE_PLAN_SCHEMA} requires current {filename}.",
                    status=409,
                )
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            current[field] = sha
            if plan.get(field) != sha:
                raise WizardError(f"Plan compiler binding {field} is absent or stale.", status=409)
            for label, approval in approvals:
                if approval.get(field) != sha:
                    raise WizardError(
                        f"{label} compiler binding {field} is absent or stale.",
                        status=409,
                    )
        return current

    def _approval_bindings(
        self,
        run_id: str,
        session: dict[str, Any],
        plan: dict[str, Any],
        run_dir: Path,
    ) -> dict[str, Any]:
        bindings = {
            "runId": run_id,
            "targets": list(plan.get("targets") or []),
            "planSchemaVersion": plan.get("schemaVersion"),
            "planSha": hashlib.sha256((run_dir / "apply-plan.json").read_bytes()).hexdigest(),
            "workbookFingerprint": dict(plan.get("workbookFingerprint") or {}),
            "sourceFingerprint": dict(session.get("fingerprint") or {}),
            "candidatesFingerprint": plan.get("candidatesFingerprint"),
            "decisionsFingerprint": plan.get("decisionsFingerprint"),
            **self._compiler_artifact_bindings(run_dir),
        }
        selection_file = run_dir / "model-selection.json"
        if selection_file.is_file():
            bindings["modelSelectionSha"] = hashlib.sha256(selection_file.read_bytes()).hexdigest()
        return bindings

    def _append_approval_audit(self, run_dir: Path, record: dict[str, Any]) -> None:
        with (run_dir / "approval-log.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

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
        if session["state"] in (
            STATE_MODELS_SELECTED,
            STATE_DECISIONS_COMPLETE,
            STATE_PLAN_BUILT,
            STATE_PLAN_APPROVED,
            STATE_DRY_RUN_APPROVED,
            STATE_DRY_RUN_VALIDATED_WRITE_BLOCKED,
            STATE_DRY_RUN_VALIDATED_WRITE_ELIGIBLE,
            STATE_WRITE_APPROVED,
        ):
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
            if session["state"] in (
                STATE_DECISIONS_COMPLETE,
                STATE_PLAN_BUILT,
                STATE_PLAN_APPROVED,
                STATE_DRY_RUN_APPROVED,
                STATE_DRY_RUN_VALIDATED_WRITE_BLOCKED,
                STATE_DRY_RUN_VALIDATED_WRITE_ELIGIBLE,
                STATE_WRITE_APPROVED,
            ):
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
        if session["state"] not in (
            STATE_DECISIONS_COMPLETE,
            STATE_PLAN_BUILT,
            STATE_PLAN_APPROVED,
            STATE_DRY_RUN_APPROVED,
            STATE_DRY_RUN_VALIDATED_WRITE_BLOCKED,
            STATE_DRY_RUN_VALIDATED_WRITE_ELIGIBLE,
        ):
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
                # A scratch save still goes through the service-level write
                # boundary. Compact tests patch the schema scan to an empty
                # issue list; production never disables it for a write call.
                scratch, stage1_scratch, write=True, run_schema_validation=True,
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
        if session["state"] not in (
            STATE_PLAN_BUILT,
            STATE_PLAN_APPROVED,
            STATE_DRY_RUN_APPROVED,
            STATE_DRY_RUN_VALIDATED_WRITE_BLOCKED,
            STATE_DRY_RUN_VALIDATED_WRITE_ELIGIBLE,
        ):
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
        if plan.get("schemaVersion") == WRITABLE_PLAN_SCHEMA:
            self._require_compiler_bindings(run_dir, plan)
        approval = {
            "schemaVersion": PLAN_APPROVAL_SCHEMA,
            "scope": PLAN_APPROVAL_SCOPE,
            "approvedBy": str(approver).strip(),
            "approvedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
            **self._approval_bindings(run_id, session, plan, run_dir),
        }
        write_json(run_dir / "plan-approval.json", approval)
        self._append_approval_audit(run_dir, approval)
        (run_dir / "write-approval.json").unlink(missing_ok=True)
        session["state"] = STATE_DRY_RUN_APPROVED
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
                # This is a saved scratch workbook, so the writer boundary
                # always keeps schema validation enabled. Compact tests patch
                # the issue scan rather than disabling the write gate.
                run_schema_validation=True,
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
                if counts["validationErrors"]:
                    blockers.append(
                        {
                            "kind": "generated_validation_errors",
                            "detail": (
                                f"generated contract has {counts['validationErrors']} validation error(s)"
                            ),
                        }
                    )
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

    def _validate_plan_approval(
        self,
        run_id: str,
        session: dict[str, Any],
        plan: dict[str, Any],
        approval: dict[str, Any],
        run_dir: Path,
        *,
        allow_legacy: bool,
    ) -> bool:
        """Validate current scoped authority; return True for a legacy record."""

        plan_sha = hashlib.sha256((run_dir / "apply-plan.json").read_bytes()).hexdigest()
        if approval.get("schemaVersion") != PLAN_APPROVAL_SCHEMA:
            if (
                allow_legacy
                and approval.get("schemaVersion") in {"pass-c-1", "pass-c-2"}
                and not approval.get("scope")
                and approval.get("planSha") == plan_sha
            ):
                return True
            raise WizardError(
                f"Apply requires {PLAN_APPROVAL_SCHEMA} {PLAN_APPROVAL_SCOPE} approval.",
                status=409,
            )
        if approval.get("scope") != PLAN_APPROVAL_SCOPE:
            raise WizardError("Plan approval scope must be dry_run_evidence.", status=409)
        expected = self._approval_bindings(run_id, session, plan, run_dir)
        for field, value in expected.items():
            if approval.get(field) != value:
                raise WizardError(
                    f"Plan approval binding {field} changed; rebuild and re-approve.",
                    status=409,
                )
        return False

    def _validate_current_plan_inputs(
        self,
        run_id: str,
        session: dict[str, Any],
        plan: dict[str, Any],
    ) -> tuple[Path, dict[str, Any]]:
        _, candidates_file, candidates = self._parsed_candidates(run_id)
        selection = self._load_selection(run_id, candidates_file)
        state = self._decision_state(run_id, candidates, selection)
        if plan.get("decisionsFingerprint") != artifact_sha(state["decisions"]):
            raise WizardError("Decisions changed after the plan was approved; rebuild the plan.", status=409)
        source_fingerprint = plan.get("sourceFingerprint") or selection.get("sourceFingerprint") or {}
        if source_fingerprint.get("sha256") != session.get("fingerprint", {}).get("sha256"):
            raise WizardError("Source fingerprint changed after the plan was approved; start a new run.", status=409)
        workbook = self._require_workbook()
        before = file_fingerprint(workbook)
        expected = plan.get("workbookFingerprint") or {}
        if expected.get("mtimeNs") != str(before["mtimeNs"]) or expected.get("sha256") != before["sha256"]:
            raise WizardError("Workbook changed after the plan was approved; rebuild the plan.", status=409)
        return workbook, before

    def _option_semantic_blockers(self, plan: dict[str, Any]) -> list[dict[str, Any]]:
        from corvette_form_generator.editor_ops import flatten_items
        from corvette_form_generator.ingest.wizard.plan_builder import MODEL_PLAN_CONFIG

        blockers: list[dict[str, Any]] = []
        items = flatten_items(
            [
                *(plan.get("stage1", {}).get("items") or []),
                *(plan.get("stage2", {}).get("items") or []),
            ]
        )
        for model in plan.get("targets") or []:
            config = MODEL_PLAN_CONFIG.get(model) or {}
            options_sheet = f"{config.get('sheetPrefix', '')}options"
            missing: list[dict[str, Any]] = []
            for item in items:
                if item.get("sheet") != options_sheet or item.get("action") not in {"add", "update"}:
                    continue
                values = item.get("row") or {}
                absent = [field for field in ("selectable", "active") if not isinstance(values.get(field), bool)]
                if absent:
                    missing.append(
                        {
                            "optionId": str((item.get("key") or {}).get("option_id") or values.get("option_id") or ""),
                            "fields": absent,
                        }
                    )
            if missing:
                blockers.append(
                    {
                        "kind": "blank_option_semantics",
                        "model": model,
                        "detail": f"{len(missing)} emitted option row(s) lack typed selectable/active values",
                        "examples": missing[:10],
                    }
                )
        return blockers

    def _identity_churn_blockers(
        self,
        workbook: Path,
        plan: dict[str, Any],
    ) -> list[dict[str, Any]]:
        from corvette_form_generator.editor_ops import extract_workbook, flatten_items
        from corvette_form_generator.ingest.wizard.plan_builder import MODEL_PLAN_CONFIG

        extract = extract_workbook(workbook)
        items = flatten_items(
            [
                *(plan.get("stage1", {}).get("items") or []),
                *(plan.get("stage2", {}).get("items") or []),
            ]
        )
        blockers: list[dict[str, Any]] = []
        for model in plan.get("targets") or []:
            config = MODEL_PLAN_CONFIG.get(model) or {}
            sheet = f"{config.get('sheetPrefix', '')}options"
            existing = {
                str(row.get("option_id") or "").strip(): str(row.get("rpo") or "").strip().upper()
                for row in extract.get("sheets", {}).get(sheet, {}).get("rows", [])
            }
            deleted = {
                option_id: existing.get(option_id, "")
                for item in items
                if item.get("sheet") == sheet and item.get("action") == "delete"
                if (option_id := str((item.get("key") or {}).get("option_id") or "").strip())
            }
            additions = [
                item.get("row") or {}
                for item in items
                if item.get("sheet") == sheet and item.get("action") == "add"
            ]
            churn: list[dict[str, str]] = []
            for old_id, rpo in deleted.items():
                if not rpo:
                    continue
                for row in additions:
                    new_id = str(row.get("option_id") or "").strip()
                    if str(row.get("rpo") or "").strip().upper() == rpo and new_id and new_id != old_id:
                        churn.append({"rpo": rpo, "oldOptionId": old_id, "newOptionId": new_id})
            if churn:
                blockers.append(
                    {
                        "kind": "identity_churn",
                        "model": model,
                        "detail": f"{len(churn)} matched option identity replacement(s) require reconciliation",
                        "examples": churn[:10],
                    }
                )
        return blockers

    def _write_eligibility(
        self,
        *,
        workbook: Path,
        plan: dict[str, Any],
        approval: dict[str, Any],
        legacy_approval: bool,
        schema_validation: bool,
        result: dict[str, Any],
        deployment: dict[str, Any],
    ) -> dict[str, Any]:
        from corvette_form_generator.editor_ops import classify_warnings

        global_blockers: list[dict[str, Any]] = []
        target_blockers: dict[str, list[dict[str, Any]]] = {
            str(model): [] for model in plan.get("targets") or []
        }
        target_deferrals: dict[str, list[dict[str, Any]]] = {
            str(model): [] for model in plan.get("targets") or []
        }
        if not schema_validation or result.get("schemaResult") is None:
            global_blockers.append(
                {
                    "kind": "schema_validation_not_run",
                    "detail": "schema-disabled diagnostics cannot establish live-write eligibility",
                }
            )
        if plan.get("schemaVersion") != WRITABLE_PLAN_SCHEMA:
            global_blockers.append(
                {
                    "kind": "plan_schema_not_writable",
                    "detail": (
                        f"plan schema {plan.get('schemaVersion')!r} is permanently diagnostic; "
                        f"{WRITABLE_PLAN_SCHEMA} is required"
                    ),
                }
            )
        if legacy_approval:
            global_blockers.append(
                {
                    "kind": "approval_schema_not_writable",
                    "detail": f"historical plan approval is diagnostic only; {PLAN_APPROVAL_SCHEMA} is required",
                }
            )
        compiler_bindings = (
            self._compiler_artifact_bindings(self.run_dir(str(approval["runId"])))
            if approval.get("runId")
            else {}
        )
        if plan.get("schemaVersion") == WRITABLE_PLAN_SCHEMA:
            for field in ("canonicalManifestSha", "compileReportSha", "exceptionResolutionsSha"):
                if not compiler_bindings.get(field) or plan.get(field) != compiler_bindings.get(field):
                    global_blockers.append(
                        {"kind": "compiler_binding_missing", "detail": f"{field} is absent or stale"}
                    )

        semantic_blockers = self._option_semantic_blockers(plan) + self._identity_churn_blockers(workbook, plan)
        for blocker in semantic_blockers:
            model = str(blocker.get("model") or "")
            if model in target_blockers:
                target_blockers[model].append(blocker)
            else:
                global_blockers.append(blocker)

        coverage = result.get("operationCoverage") or {}
        if coverage.get("rawCovered") != coverage.get("rawCount"):
            global_blockers.append(
                {"kind": "operation_coverage_failed", "detail": "raw operation coverage is incomplete"}
            )
        verification = result.get("verification") or {}
        if not verification.get("ok") or verification.get("preparedChecked") != coverage.get("preparedCount"):
            global_blockers.append(
                {"kind": "readback_failed", "detail": "prepared operation readback is incomplete"}
            )

        warning_policy = result.get("warningPolicy") or classify_warnings(result.get("warnings") or [])
        for warning_id in warning_policy.get("blockingIds") or []:
            warning_kind = str(warning_id).partition(":")[0]
            kind = {
                "refdel": "referenced_delete",
                "dorder": "display_order_collision",
            }.get(warning_kind, "unknown_warning")
            global_blockers.append({"kind": kind, "detail": str(warning_id), "warningId": str(warning_id)})

        accepted_warning_ids: list[str] = []
        for warning_id in warning_policy.get("confirmableIds") or []:
            matched_model = next(
                (
                    model
                    for model in target_blockers
                    if str(warning_id).partition(":")[2].startswith(
                        {"grand_sport_x": "grandSportX_"}.get(model, f"{model}_")
                    )
                ),
                "",
            )
            entry = deployment.get(matched_model) or {}
            if (
                matched_model
                and not (entry.get("deploymentBlockers") or [])
                and entry.get("status") == "deployment_probe_passed"
            ):
                accepted_warning_ids.append(str(warning_id))
                target_deferrals[matched_model].append(
                    {
                        "kind": "scaffold",
                        "warningId": str(warning_id),
                        "detail": "inactive target scaffold verified in scratch",
                    }
                )
            else:
                global_blockers.append(
                    {
                        "kind": "scaffold_warning_not_confirmable",
                        "detail": f"{warning_id} lacks a clean target scratch-generation probe",
                        "warningId": str(warning_id),
                    }
                )

        for model in target_blockers:
            entry = deployment.get(model) or {}
            for blocker in entry.get("deploymentBlockers") or []:
                target_blockers[model].append(
                    {
                        "kind": str(blocker.get("kind") or "deployment_blocked"),
                        "model": model,
                        "detail": str(blocker.get("detail") or "deployment continuity failed"),
                    }
                )
            for deferral in entry.get("deploymentDeferrals") or []:
                normalized = {
                    "kind": str(deferral.get("kind") or ""),
                    "model": model,
                    "detail": str(deferral.get("detail") or ""),
                }
                if normalized["kind"] not in ALLOWED_WRITE_DEFERRAL_KINDS:
                    target_blockers[model].append(
                        {
                            "kind": "unknown_deferral",
                            "model": model,
                            "detail": normalized["kind"],
                        }
                    )
                else:
                    target_deferrals[model].append(normalized)

        targets: dict[str, Any] = {}
        all_blockers = list(global_blockers)
        all_deferrals: list[dict[str, Any]] = []
        for model in target_blockers:
            blockers = target_blockers[model]
            deferrals = target_deferrals[model]
            all_blockers.extend(blockers)
            all_deferrals.extend(deferrals)
            targets[model] = {
                "eligible": not global_blockers and not blockers,
                "blockers": blockers,
                "deferrals": deferrals,
            }
        return {
            "eligible": bool(targets) and not all_blockers and all(
                entry["eligible"] for entry in targets.values()
            ),
            "blockers": all_blockers,
            "deferrals": all_deferrals,
            "targets": targets,
            "acceptedWarningIds": sorted(accepted_warning_ids),
            "warningFingerprint": warning_policy.get("fingerprint"),
        }

    def _eligible_report_contract(
        self,
        run_id: str,
        plan: dict[str, Any],
        report: dict[str, Any],
        run_dir: Path,
    ) -> None:
        from corvette_form_generator.editor_ops import classify_warnings, flatten_items

        if report.get("schemaVersion") != SCHEMA_VERSION_D:
            raise WizardError(f"Write approval requires a {SCHEMA_VERSION_D} dry-run report.", status=409)
        if not report.get("ok") or report.get("status") != "validated_write_eligible":
            raise WizardError("Write approval requires a validated_write_eligible dry-run report.", status=409)
        eligibility = report.get("writeEligibility") or {}
        if not eligibility.get("eligible"):
            raise WizardError("Dry-run report is not write eligible.", status=409)
        if eligibility.get("blockers"):
            raise WizardError("Write-eligible report still contains blockers.", status=409)
        targets = list(plan.get("targets") or [])
        report_targets = eligibility.get("targets") or {}
        if set(report_targets) != set(targets) or any(
            not (report_targets.get(model) or {}).get("eligible")
            or bool((report_targets.get(model) or {}).get("blockers"))
            for model in targets
        ):
            raise WizardError("Every target in the atomic plan must be write eligible.", status=409)
        plan_sha = hashlib.sha256((run_dir / "apply-plan.json").read_bytes()).hexdigest()
        if report.get("runId") != run_id or report.get("planSha") != plan_sha:
            raise WizardError("Dry-run report is stale for the current plan.", status=409)
        if report.get("planSchemaVersion") != WRITABLE_PLAN_SCHEMA:
            raise WizardError(f"Write approval requires {WRITABLE_PLAN_SCHEMA}.", status=409)
        if report.get("write"):
            raise WizardError("Write approval must bind a dry-run report.", status=409)
        if (
            report.get("schemaValidationEnabled") is not True
            or (report.get("schemaResult") or {}).get("error_count") != 0
        ):
            raise WizardError("Write approval requires a schema-validated eligible report.", status=409)
        reported_policy = report.get("warningPolicy") or (report.get("applyResult") or {}).get("warningPolicy")
        current_policy = classify_warnings(report.get("warnings") or [])
        if not reported_policy or reported_policy.get("fingerprint") != current_policy.get("fingerprint"):
            raise WizardError("Dry-run warning policy fingerprint is inconsistent.", status=409)
        if current_policy.get("blockingIds") or current_policy.get("unknownIds"):
            raise WizardError("Dry-run report contains blocking or unknown warnings.", status=409)
        if sorted(eligibility.get("acceptedWarningIds") or []) != sorted(
            current_policy.get("confirmableIds") or []
        ) or eligibility.get("warningFingerprint") != current_policy.get("fingerprint"):
            raise WizardError("Dry-run warning agreement is stale.", status=409)
        coverage = report.get("operationCoverage") or {}
        verification = report.get("verification") or {}
        apply_result = report.get("applyResult") or {}
        if coverage != (apply_result.get("operationCoverage") or {}):
            raise WizardError("Dry-run report does not match editor operation coverage.", status=409)
        if verification != (apply_result.get("verification") or {}):
            raise WizardError("Dry-run report does not match editor prepared readback.", status=409)
        combined_raw_count = len(
            flatten_items(
                [
                    *(plan.get("stage1", {}).get("items") or []),
                    *(plan.get("stage2", {}).get("items") or []),
                ]
            )
        )
        if coverage.get("rawCount") != combined_raw_count:
            raise WizardError("Dry-run raw operation count does not match the bound plan.", status=409)
        if coverage.get("rawCovered") != coverage.get("rawCount"):
            raise WizardError("Dry-run raw operation coverage is incomplete.", status=409)
        if not verification.get("ok") or verification.get("preparedChecked") != coverage.get("preparedCount"):
            raise WizardError("Dry-run prepared readback is incomplete.", status=409)
        deferrals = eligibility.get("deferrals") or []
        nested_deferrals = [
            item
            for model in targets
            for item in (report_targets.get(model) or {}).get("deferrals") or []
        ]
        def normalized(values: list[dict[str, Any]]) -> list[str]:
            return sorted(
                json.dumps(item, sort_keys=True, separators=(",", ":"))
                for item in values
            )
        if normalized(deferrals) != normalized(nested_deferrals):
            raise WizardError("Dry-run target deferrals do not match the atomic plan total.", status=409)
        unknown = sorted(
            {str(item.get("kind") or "") for item in deferrals}
            - ALLOWED_WRITE_DEFERRAL_KINDS
            - {"scaffold"}
        )
        if unknown:
            raise WizardError(f"Dry-run report contains unapproved deferral kinds: {unknown}", status=409)

    def approve_write(self, run_id: str, approver: str) -> dict[str, Any]:
        """Create write authority solely from current stored proof artifacts."""

        session = self.load_session(run_id)
        self._refuse_if_applied(session)
        if not str(approver or "").strip():
            raise WizardError("Write approval needs a reviewer name.")
        run_dir = self.run_dir(run_id)
        plan_file = run_dir / "apply-plan.json"
        plan_approval_file = run_dir / "plan-approval.json"
        report_file = run_dir / "apply-dry-run-report.json"
        if not plan_file.is_file() or not plan_approval_file.is_file() or not report_file.is_file():
            raise WizardError("Write approval requires plan, scoped approval, and dry-run report.", status=409)
        plan = read_json(plan_file)
        if plan.get("schemaVersion") != WRITABLE_PLAN_SCHEMA:
            raise WizardError(
                f"Write approval requires {WRITABLE_PLAN_SCHEMA}; older plans are diagnostic only.",
                status=409,
            )
        plan_approval = read_json(plan_approval_file)
        self._validate_plan_approval(
            run_id, session, plan, plan_approval, run_dir, allow_legacy=False
        )
        workbook, before = self._validate_current_plan_inputs(run_id, session, plan)
        del workbook
        self._require_compiler_bindings(
            run_dir,
            plan,
            (PLAN_APPROVAL_SCHEMA, plan_approval),
        )
        report = read_json(report_file)
        if report.get("approval") != plan_approval:
            raise WizardError("Dry-run report does not bind the current plan approval.", status=409)
        self._eligible_report_contract(run_id, plan, report, run_dir)
        if report.get("workbookBefore") != before or report.get("workbookAfter") != before:
            raise WizardError("Dry-run report workbook fingerprint is stale.", status=409)
        eligibility = report["writeEligibility"]
        approval = {
            "schemaVersion": WRITE_APPROVAL_SCHEMA,
            "scope": WRITE_APPROVAL_SCOPE,
            "approvedBy": str(approver).strip(),
            "approvedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
            **self._approval_bindings(run_id, session, plan, run_dir),
            "planApprovalSha": hashlib.sha256(plan_approval_file.read_bytes()).hexdigest(),
            "eligibleDryRunReportSha": hashlib.sha256(report_file.read_bytes()).hexdigest(),
            "acceptedWarningIds": list(eligibility.get("acceptedWarningIds") or []),
            "warningFingerprint": eligibility.get("warningFingerprint"),
            "allowedDeferrals": list(eligibility.get("deferrals") or []),
        }
        write_json(run_dir / "write-approval.json", approval)
        self._append_approval_audit(run_dir, approval)
        session["state"] = STATE_WRITE_APPROVED
        write_json(run_dir / "session.json", session)
        return {"session": session, "approval": approval}

    def _prewrite_authority(
        self,
        run_id: str,
        session: dict[str, Any],
        plan: dict[str, Any],
        plan_approval: dict[str, Any],
        run_dir: Path,
        *,
        schema_validation: bool,
    ) -> tuple[Path, dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
        """Repeat every refusal check before the first possible live mutation."""

        from corvette_form_generator.editor_ops import apply_batch, classify_warnings
        from corvette_form_generator.workbook import excel_lock_path

        if not schema_validation:
            raise WizardError("Live write requires schema validation.", status=409)
        if plan.get("schemaVersion") != WRITABLE_PLAN_SCHEMA:
            raise WizardError(
                f"Live write requires {WRITABLE_PLAN_SCHEMA}; older plans are permanently dry-run-only.",
                status=409,
            )
        self._validate_plan_approval(
            run_id, session, plan, plan_approval, run_dir, allow_legacy=False
        )
        if session.get("state") != STATE_WRITE_APPROVED:
            raise WizardError("Live write requires deployment_ready_write approval.", status=409)
        write_approval_file = run_dir / "write-approval.json"
        report_file = run_dir / "apply-dry-run-report.json"
        if not write_approval_file.is_file():
            raise WizardError("Live write requires write-approval.json.", status=409)
        if not report_file.is_file():
            raise WizardError("Live write requires the eligible dry-run report.", status=409)
        write_approval = read_json(write_approval_file)
        if write_approval.get("schemaVersion") != WRITE_APPROVAL_SCHEMA:
            raise WizardError(f"Live write requires {WRITE_APPROVAL_SCHEMA}.", status=409)
        if write_approval.get("scope") != WRITE_APPROVAL_SCOPE:
            raise WizardError("Write approval scope must be deployment_ready_write.", status=409)
        self._require_compiler_bindings(
            run_dir,
            plan,
            (PLAN_APPROVAL_SCHEMA, plan_approval),
            (WRITE_APPROVAL_SCHEMA, write_approval),
        )
        expected_bindings = self._approval_bindings(run_id, session, plan, run_dir)
        for field, value in expected_bindings.items():
            if write_approval.get(field) != value:
                raise WizardError(f"Write approval binding {field} changed.", status=409)
        if write_approval.get("planApprovalSha") != hashlib.sha256(
            (run_dir / "plan-approval.json").read_bytes()
        ).hexdigest():
            raise WizardError("Plan approval changed after write approval.", status=409)
        report_sha = hashlib.sha256(report_file.read_bytes()).hexdigest()
        if write_approval.get("eligibleDryRunReportSha") != report_sha:
            raise WizardError("Eligible dry-run report SHA changed after write approval.", status=409)
        report = read_json(report_file)
        if report.get("approval") != plan_approval:
            raise WizardError("Eligible report no longer matches plan approval.", status=409)
        self._eligible_report_contract(run_id, plan, report, run_dir)

        workbook, before = self._validate_current_plan_inputs(run_id, session, plan)
        if excel_lock_path(workbook).exists():
            raise WizardError("Excel lock file is present; close Excel before live write.", status=409)
        if report.get("workbookBefore") != before or report.get("workbookAfter") != before:
            raise WizardError("Eligible report workbook fingerprint changed.", status=409)
        eligibility = report["writeEligibility"]
        approved_deferrals = write_approval.get("allowedDeferrals") or []
        if approved_deferrals != (eligibility.get("deferrals") or []):
            raise WizardError("Allowed deferral set drifted after write approval.", status=409)
        if any(
            str(item.get("kind") or "") not in ALLOWED_WRITE_DEFERRAL_KINDS | {"scaffold"}
            for item in approved_deferrals
        ):
            raise WizardError("Write approval contains a non-allowlisted deferral.", status=409)

        batch = self._combined_plan_batch(plan, workbook)
        preview = apply_batch(
            workbook,
            batch,
            write=False,
            run_schema_validation=True,
        )
        if not preview.get("ok"):
            raise WizardError(
                "Pre-write temporary-workbook proof no longer passes: "
                + "; ".join(preview.get("errors") or [str(preview.get("status"))]),
                status=409,
            )
        current_policy = preview.get("warningPolicy") or classify_warnings(preview.get("warnings") or [])
        if current_policy.get("blockingIds"):
            raise WizardError("Pre-write proof emitted blocking or unknown warnings.", status=409)
        if write_approval.get("warningFingerprint") != current_policy.get("fingerprint"):
            raise WizardError("Warning set drifted after write approval.", status=409)
        if sorted(write_approval.get("acceptedWarningIds") or []) != sorted(
            current_policy.get("confirmableIds") or []
        ):
            raise WizardError("Accepted warning IDs drifted after write approval.", status=409)
        coverage = preview.get("operationCoverage") or {}
        verification = preview.get("verification") or {}
        if coverage != (report.get("operationCoverage") or {}):
            raise WizardError("Pre-write operation coverage drifted from the eligible report.", status=409)
        if verification != (report.get("verification") or {}):
            raise WizardError("Pre-write prepared readback drifted from the eligible report.", status=409)
        if coverage.get("rawCovered") != coverage.get("rawCount"):
            raise WizardError("Pre-write raw operation coverage is incomplete.", status=409)
        if not verification.get("ok") or verification.get("preparedChecked") != coverage.get("preparedCount"):
            raise WizardError("Pre-write prepared readback is incomplete.", status=409)
        return workbook, before, write_approval, preview, report

    def apply_approved_plan(
        self,
        run_id: str,
        *,
        write: bool = False,
        confirm_plan_warnings: bool = False,
        schema_validation: bool = True,
    ) -> dict[str, Any]:
        """Produce bound dry-run evidence or execute separately approved write authority."""

        from corvette_form_generator.editor_ops import apply_batch

        started_at = datetime.now().isoformat(timespec="seconds")
        session = self.load_session(run_id)
        self._refuse_if_applied(session)
        if session["state"] not in {
            STATE_PLAN_APPROVED,
            STATE_DRY_RUN_APPROVED,
            STATE_DRY_RUN_VALIDATED_WRITE_BLOCKED,
            STATE_DRY_RUN_VALIDATED_WRITE_ELIGIBLE,
            STATE_WRITE_APPROVED,
        }:
            raise WizardError("Apply requires an approved plan.", status=409)

        run_dir = self.run_dir(run_id)
        plan_file = run_dir / "apply-plan.json"
        approval_file = run_dir / "plan-approval.json"
        if not plan_file.is_file() or not approval_file.is_file():
            raise WizardError("Apply requires apply-plan.json and plan-approval.json.", status=409)

        plan = read_json(plan_file)
        approval = read_json(approval_file)
        plan_sha = hashlib.sha256(plan_file.read_bytes()).hexdigest()
        if not plan.get("valid"):
            raise WizardError("Apply plan is not valid; rebuild before applying.", status=409)
        if write and not schema_validation:
            raise WizardError("Live write requires schema validation.", status=409)
        if write and plan.get("schemaVersion") != WRITABLE_PLAN_SCHEMA:
            raise WizardError(
                f"Live write requires {WRITABLE_PLAN_SCHEMA}; older plans are permanently dry-run-only.",
                status=409,
            )
        if write and confirm_plan_warnings:
            raise WizardError("Blanket plan-warning confirmation is retired.", status=409)

        legacy_approval = self._validate_plan_approval(
            run_id,
            session,
            plan,
            approval,
            run_dir,
            allow_legacy=not write,
        )
        if write:
            workbook, before, write_approval, _preview, approved_report = self._prewrite_authority(
                run_id,
                session,
                plan,
                approval,
                run_dir,
                schema_validation=schema_validation,
            )
        else:
            workbook, before = self._validate_current_plan_inputs(run_id, session, plan)
            write_approval = None
            approved_report = None

        batch = self._combined_plan_batch(plan, workbook)
        per_sheet_action_counts = self._per_sheet_action_counts(batch["items"])
        per_sheet_counts: dict[str, int] = {}
        for item in batch["items"]:
            sheet = item.get("sheet")
            if sheet:
                per_sheet_counts[str(sheet)] = per_sheet_counts.get(str(sheet), 0) + 1
        confirmed_warnings = list((write_approval or {}).get("acceptedWarningIds") or [])
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
        # A pre-mutation refusal must not create or replace report evidence.
        if write and not result.get("ok") and not result.get("backupPath"):
            return result
        after = file_fingerprint(workbook)
        completed_at = datetime.now().isoformat(timespec="seconds")
        verification = result.get("verification") or {
            "ok": False,
            "preparedChecked": 0,
            "preparedCount": 0,
            "errors": ["editor result did not include prepared readback"],
        }
        if result.get("ok") and write:
            deployment_continuity = dict((approved_report or {}).get("deploymentContinuity") or {})
        elif result.get("ok"):
            deployment_continuity = self._deployment_continuity_probe(
                workbook,
                batch,
                plan,
                schema_validation=schema_validation,
            )
        else:
            deployment_continuity = {}
        if result.get("ok"):
            if write:
                write_eligibility = dict((approved_report or {}).get("writeEligibility") or {})
            else:
                write_eligibility = self._write_eligibility(
                    workbook=workbook,
                    plan=plan,
                    approval=approval,
                    legacy_approval=legacy_approval,
                    schema_validation=schema_validation,
                    result=result,
                    deployment=deployment_continuity,
                )
        else:
            execution_blocker = {
                "kind": "mechanical_validation_failed",
                "detail": "; ".join(result.get("errors") or [str(result.get("status"))]),
            }
            write_eligibility = {
                "eligible": False,
                "blockers": [execution_blocker],
                "deferrals": [],
                "targets": {
                    str(model): {"eligible": False, "blockers": [execution_blocker], "deferrals": []}
                    for model in plan.get("targets") or []
                },
                "acceptedWarningIds": [],
                "warningFingerprint": (result.get("warningPolicy") or {}).get("fingerprint"),
            }
        diagnostic_status = (
            "validated_write_eligible" if write_eligibility["eligible"] else "validated_write_blocked"
        )
        status = result.get("status") if not result.get("ok") or write else diagnostic_status
        blocked_reason = None
        if not write_eligibility["eligible"]:
            blockers = write_eligibility.get("blockers") or []
            blocked_reason = str((blockers[0] if blockers else {}).get("detail") or "write eligibility is blocked")
        report = {
            "schemaVersion": SCHEMA_VERSION_D,
            "planSchemaVersion": plan.get("schemaVersion"),
            "planSupersededForWrite": plan.get("schemaVersion") != WRITABLE_PLAN_SCHEMA,
            "liveWriteBlockedReason": blocked_reason,
            "writeEligibility": write_eligibility,
            "runId": run_id,
            "startedAt": started_at,
            "completedAt": completed_at,
            "appliedAt": completed_at,
            "write": write,
            "schemaValidationEnabled": bool(schema_validation),
            "status": status,
            "ok": result["ok"],
            "planSha": plan_sha,
            "approvedBy": approval.get("approvedBy"),
            "approvedAt": approval.get("approvedAt"),
            "approval": approval,
            "opCounts": {
                "stage1": len(plan["stage1"]["items"]),
                "stage2": len(plan["stage2"]["items"]),
                "combinedRaw": (result.get("operationCoverage") or {}).get("rawCount", 0),
                "prepared": (result.get("operationCoverage") or {}).get(
                    "preparedCount", 0
                ),
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
            "warningPolicy": result.get("warningPolicy"),
            "operationCoverage": result.get("operationCoverage"),
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
            result["writeEligibility"] = write_eligibility
            result["liveWriteBlockedReason"] = blocked_reason
            if write and result.get("status") == "apply_verification_failed":
                session["state"] = STATE_APPLY_VERIFICATION_FAILED
                session["applyReport"] = "apply-report.json"
                write_json(run_dir / "session.json", session)
            return result
        if write:
            session["state"] = STATE_APPLIED
            session["appliedAt"] = report["appliedAt"]
            session["applyReport"] = "apply-report.json"
            write_json(run_dir / "session.json", session)
        else:
            session["state"] = (
                STATE_DRY_RUN_VALIDATED_WRITE_ELIGIBLE
                if write_eligibility["eligible"]
                else STATE_DRY_RUN_VALIDATED_WRITE_BLOCKED
            )
            session["dryRunReport"] = "apply-dry-run-report.json"
            write_json(run_dir / "session.json", session)
        result["reportPath"] = str(report_path)
        result["verification"] = verification
        result["status"] = status
        result["writeEligibility"] = write_eligibility
        result["liveWriteBlockedReason"] = blocked_reason
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
