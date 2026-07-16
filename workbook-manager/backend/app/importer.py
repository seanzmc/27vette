"""Read-only workbook compilation and fail-closed canonical import orchestration."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal, Mapping

from . import db as dbmod
from . import migration
from .catalog import LIVE_MODELS
from .central_compiler import compile_central_tables
from .compile_types import (
    CompiledTable,
    DecisionRequired,
    Finding,
    LineageEntry,
    SchemaMapping,
    SourceSheet,
    freeze_mapping,
)
from .model_compiler import compile_direct_model_tables
from .shared_compiler import compile_shared_model_tables
from .workbook_profile import profile_workbook


@dataclass(frozen=True)
class CompiledWorkbook:
    tables: tuple[CompiledTable, ...]
    source_catalog: tuple[SourceSheet, ...]
    schema_mappings: tuple[SchemaMapping, ...]
    lineage: tuple[LineageEntry, ...]
    findings: tuple[Finding, ...]


@dataclass(frozen=True)
class ImportReport:
    status: Literal["validated", "decision_required", "contract_mismatch"]
    live_models: tuple[str, ...]
    findings: tuple[Finding, ...]
    decision_required: tuple[Finding, ...]
    contract_differences: tuple[Finding, ...]
    candidate_path: Path | None
    promoted_path: Path | None

    @property
    def finding_codes(self) -> tuple[str, ...]:
        return tuple(finding.code for finding in self.findings)


def _central_schema_mappings(
    tables: tuple[CompiledTable, ...],
) -> tuple[SchemaMapping, ...]:
    """Materialize central column ownership from immutable row evidence."""
    contracts: dict[
        tuple[str, str, str, str], tuple[set[str], set[str]]
    ] = {}
    for table in tables:
        for row in table.rows:
            for destination_column in row.values:
                parameter = row.mapping_parameters.get(destination_column, {})
                if not isinstance(parameter, Mapping):
                    parameter = {}
                source_column = str(
                    parameter.get("source_column") or destination_column
                )
                key = (
                    row.source_sheet,
                    source_column,
                    table.name,
                    destination_column,
                )
                transforms, reverse_transforms = contracts.setdefault(
                    key, (set(), set())
                )
                transforms.add(str(parameter.get("transform") or "identity"))
                reverse_transforms.add(
                    str(parameter.get("reverse_transform") or "identity")
                )
    return tuple(
        SchemaMapping(
            source_sheet=source_sheet,
            source_column=source_column,
            destination_table=destination_table,
            destination_column=destination_column,
            transform="|".join(sorted(transforms)),
            reverse_transform="|".join(sorted(reverse_transforms)),
        )
        for (
            source_sheet,
            source_column,
            destination_table,
            destination_column,
        ), (transforms, reverse_transforms) in sorted(contracts.items())
    )


def _lineage(tables: tuple[CompiledTable, ...]) -> tuple[LineageEntry, ...]:
    entries: list[LineageEntry] = []
    for table in tables:
        for row in table.rows:
            entries.append(
                LineageEntry(
                    destination_table=table.name,
                    destination_key=freeze_mapping(
                        {
                            column: row.values[column]
                            for column in table.primary_key
                        }
                    ),
                    source_sheet=row.source_sheet,
                    source_row=row.source_row,
                    mapping_role=row.lineage_role,
                )
            )
    return tuple(entries)


def _classify_source_rows(
    source_catalog: tuple[SourceSheet, ...],
    lineage: tuple[LineageEntry, ...],
    findings: tuple[Finding, ...],
) -> tuple[tuple[SourceSheet, ...], tuple[Finding, ...]]:
    emitted: dict[tuple[str, int], list[dict[str, object]]] = {}
    for entry in lineage:
        emitted.setdefault((entry.source_sheet, entry.source_row), []).append(
            {
                "destination_table": entry.destination_table,
                "destination_key": dict(entry.destination_key),
            }
        )
    finding_by_row = {
        (finding.source_sheet, finding.source_row): finding
        for finding in findings
        if finding.source_row is not None
    }
    unresolved: list[Finding] = []
    classified_sheets: list[SourceSheet] = []
    for source in source_catalog:
        classified_rows = []
        for row in source.rows:
            key = (source.source_sheet, row.source_row)
            destinations = emitted.get(key, [])
            finding = finding_by_row.get(key)
            if destinations:
                classified_rows.append(
                    replace(
                        row,
                        disposition="emitted",
                        reason="Source row emitted one or more canonical rows.",
                        evidence=freeze_mapping(
                            {"destinations": tuple(destinations)}
                        ),
                    )
                )
            elif finding is not None:
                classified_rows.append(
                    replace(
                        row,
                        disposition=finding.status,
                        reason=finding.message,
                        evidence=freeze_mapping({"finding_code": finding.code}),
                    )
                )
            elif row.disposition != "emission_required":
                classified_rows.append(row)
            elif source.source_sheet == "variant_master":
                classified_rows.append(
                    replace(
                        row,
                        disposition="inactive_future_metadata",
                        reason=(
                            "Variant metadata is outside the exact live-model "
                            "membership compiled from model_variants."
                        ),
                    )
                )
            else:
                finding = Finding(
                    severity="error",
                    status="decision_required",
                    code="source_row_unreconciled",
                    message=(
                        "A nonempty workbook source row has neither emitted "
                        "lineage nor an explicit disposition."
                    ),
                    source_sheet=source.source_sheet,
                    source_row=row.source_row,
                    value=dict(row.values),
                )
                unresolved.append(finding)
                classified_rows.append(
                    replace(
                        row,
                        disposition="decision_required",
                        reason=finding.message,
                        evidence=freeze_mapping(
                            {"finding_code": finding.code}
                        ),
                    )
                )
        classified_sheets.append(replace(source, rows=tuple(classified_rows)))
    return tuple(classified_sheets), findings + tuple(unresolved)


def compile_workbook(path: Path) -> CompiledWorkbook:
    """Run the complete read-only workbook compiler sequence."""
    workbook_path = Path(path)
    profile = profile_workbook(workbook_path)
    central = compile_central_tables(profile, workbook_path)
    direct = compile_direct_model_tables(profile, workbook_path, central)
    shared = compile_shared_model_tables(
        profile, workbook_path, central, direct
    )
    tables = tuple(central) + tuple(shared.tables)
    mappings = _central_schema_mappings(tuple(central)) + tuple(
        mapping
        for table in shared.tables
        for mapping in table.schema_mappings
    )
    covered = {
        (mapping.destination_table, mapping.destination_column)
        for mapping in mappings
    }
    derived_mappings = []
    for table in tables:
        for destination_column in {
            column for row in table.rows for column in row.values
        }:
            if (table.name, destination_column) in covered:
                continue
            source_sheet = table.rows[0].source_sheet if table.rows else ""
            model_ownership = destination_column == "model_key" and bool(
                table.model_key
            )
            derived_mappings.append(
                SchemaMapping(
                    source_sheet=source_sheet,
                    source_column=(
                        "__model_table_ownership__"
                        if model_ownership
                        else "__compiler_default__"
                    ),
                    destination_table=table.name,
                    destination_column=destination_column,
                    model_key=table.model_key,
                    transform=(
                        "derive_model_table_ownership"
                        if model_ownership
                        else "compiler_default_or_null"
                    ),
                    reverse_transform="reconstruct_from_compiler_contract",
                )
            )
    mappings += tuple(derived_mappings)
    lineage = _lineage(tables)
    source_catalog, findings = _classify_source_rows(
        profile.sheets, lineage, shared.findings
    )
    return CompiledWorkbook(
        tables=tables,
        source_catalog=source_catalog,
        schema_mappings=mappings,
        lineage=lineage,
        findings=findings,
    )


def load_candidate(compiled: CompiledWorkbook, path: Path) -> Path:
    return migration.load_candidate(compiled, path)


def promote_candidate(
    candidate: Path,
    destination: Path,
    snapshot: migration.DestinationSnapshot,
) -> Path:
    return migration.promote_candidate(candidate, destination, snapshot)


def _report(
    findings: tuple[Finding, ...],
    *,
    candidate_path: Path | None = None,
    promoted_path: Path | None = None,
) -> ImportReport:
    decisions = tuple(
        finding for finding in findings if finding.status == "decision_required"
    )
    contracts = tuple(
        finding for finding in findings if finding.status == "contract_mismatch"
    )
    if decisions:
        status: Literal[
            "validated", "decision_required", "contract_mismatch"
        ] = "decision_required"
    elif contracts:
        status = "contract_mismatch"
    else:
        status = "validated"
    return ImportReport(
        status=status,
        live_models=LIVE_MODELS,
        findings=findings,
        decision_required=decisions,
        contract_differences=contracts,
        candidate_path=candidate_path,
        promoted_path=promoted_path,
    )


def _decision_finding(error: DecisionRequired) -> Finding:
    return Finding(
        severity="error",
        status="decision_required",
        code=error.code,
        message=str(error),
        source_sheet=error.source_sheet,
        source_row=error.source_row,
        source_column=error.source_column,
        value=error.value,
    )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_import_workbook(
    destination: Path,
    workbook_path: Path,
) -> ImportReport:
    destination_path = Path(destination)
    workbook = Path(workbook_path)

    snapshot = migration.capture_destination_snapshot(destination_path)
    if snapshot.findings:
        return _report(snapshot.findings)

    try:
        initial_mtime_ns = str(workbook.stat().st_mtime_ns)
        initial_sha256 = _file_sha256(workbook)
    except OSError as error:
        return _report(
            (
                Finding(
                    severity="error",
                    status="decision_required",
                    code="workbook_unavailable",
                    message=str(error),
                    value=str(workbook),
                ),
            )
        )
    try:
        compiled = compile_workbook(workbook)
    except DecisionRequired as error:
        return _report((_decision_finding(error),))
    except (KeyError, ValueError) as error:
        return _report(
            (
                Finding(
                    severity="error",
                    status="contract_mismatch",
                    code="workbook_compile_contract_mismatch",
                    message=str(error),
                ),
            )
        )
    if (
        str(workbook.stat().st_mtime_ns) != initial_mtime_ns
        or _file_sha256(workbook) != initial_sha256
    ):
        return _report(
            (
                Finding(
                    severity="error",
                    status="decision_required",
                    code="workbook_changed_during_compile",
                    message=(
                        "The workbook changed during read-only compilation; "
                        "retry from a stable source file."
                    ),
                ),
            )
        )

    blocking = tuple(
        finding
        for finding in compiled.findings
        if finding.status in {"decision_required", "contract_mismatch"}
        or finding.severity == "error"
    )
    if blocking:
        return _report(blocking)

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    candidate = destination_path.with_name(
        f".{destination_path.name}.candidate-{uuid.uuid4().hex}.sqlite3"
    )
    preserve_candidate_sidecars = False
    try:
        migration.load_candidate(
            compiled,
            candidate,
            workbook_path=workbook,
            workbook_mtime_ns=initial_mtime_ns,
            workbook_sha256=initial_sha256,
        )
        conn = dbmod.connect(candidate)
        try:
            errors = migration.candidate_integrity_errors(conn)
        finally:
            conn.close()
        if errors:
            findings = tuple(
                Finding(
                    severity="error",
                    status="contract_mismatch",
                    code=str(error.get("code") or "candidate_integrity_error"),
                    message=json.dumps(error, sort_keys=True, default=str),
                    value=error,
                )
                for error in errors
            )
            return _report(findings, candidate_path=candidate)
        promoted = promote_candidate(candidate, destination_path, snapshot)
        return _report(
            compiled.findings,
            candidate_path=candidate,
            promoted_path=promoted,
        )
    except migration.DestinationChanged as error:
        return _report(
            (
                Finding(
                    severity="error",
                    status="decision_required",
                    code="destination_changed_during_import",
                    message=str(error),
                ),
            ),
            candidate_path=candidate,
        )
    except migration.CandidateCheckpointError as error:
        preserve_candidate_sidecars = True
        return _report(
            (
                Finding(
                    severity="error",
                    status="contract_mismatch",
                    code="candidate_checkpoint_incomplete",
                    message=str(error),
                ),
            ),
            candidate_path=candidate,
        )
    except migration.BackupVerificationError as error:
        return _report(
            (
                Finding(
                    severity="error",
                    status="contract_mismatch",
                    code="backup_verification_failed",
                    message=str(error),
                ),
            ),
            candidate_path=candidate,
        )
    except (OSError, sqlite3.DatabaseError, ValueError) as error:
        return _report(
            (
                Finding(
                    severity="error",
                    status="contract_mismatch",
                    code="candidate_build_or_promotion_failed",
                    message=str(error),
                ),
            ),
            candidate_path=candidate,
        )
    finally:
        migration.remove_candidate_artifacts(
            candidate, preserve_sidecars=preserve_candidate_sidecars
        )


def import_workbook(
    db_path: Path,
    workbook_path: Path,
) -> ImportReport:
    """Fail closed until Task 7 supplies the mandatory contract auditor."""
    if not isinstance(db_path, (str, Path)):
        raise TypeError("db_path must be a filesystem destination path")
    return _report(
        (
            Finding(
                severity="error",
                status="decision_required",
                code="contract_audit_required",
                message=(
                    "Task 7 contract audit is required before canonical "
                    "candidate promotion can run."
                ),
            ),
        )
    )


_TASK6_TEST_CAPABILITY = object()


def _import_workbook_for_task6_tests(
    db_path: Path,
    workbook_path: Path,
    *,
    _capability: object,
) -> ImportReport:
    """Private structural entry removed when Task 7 wires the real auditor."""
    if _capability is not _TASK6_TEST_CAPABILITY:
        raise PermissionError("Task 6 structural import capability required")
    return _canonical_import_workbook(Path(db_path), Path(workbook_path))


def latest_report(conn: sqlite3.Connection) -> dict | None:
    row = conn.execute(
        "SELECT id FROM import_runs ORDER BY id DESC LIMIT 1").fetchone()
    if not row:
        return None
    run = conn.execute(
        "SELECT * FROM import_runs WHERE id=?", (row["id"],)
    ).fetchone()
    issues = conn.execute(
        "SELECT * FROM import_issues WHERE run_id=? ORDER BY id", (row["id"],)
    ).fetchall()
    return {"run": dict(run), "issues": [dict(issue) for issue in issues]}
