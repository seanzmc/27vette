"""Workbook synchronization and export.

Committed-but-unsynced ``change_history`` rows are translated into an
``editor_ops`` operation batch and handed to the repo's existing gated write
pipeline (``apply_batch`` -> ``save_workbook_safely``), which enforces:
Excel-lock refusal, mtime staleness, batch validation, dry-run on a temp
copy, package + schema validation, automatic backup, and atomic replacement.
This module never writes the workbook through any other path (AGENTS.md §5).

Dry-run is the only API-exposed mode during provisional containment. This
legacy helper still accepts ``write=True`` for direct scratch-copy regression
tests, but ``POST /api/sync`` refuses that mode until Pass 7.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import config, importer  # ensures scripts/ on sys.path
from . import db as dbmod
from corvette_form_generator import editor_ops  # noqa: E402

from .catalog import SPEC_BY_TABLE
from .staging import target_sheet_for


def _now_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def pending_history(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM change_history WHERE sync_status='pending' "
        "AND status='committed' ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def build_batch(conn, workbook_path: Path, projection_conn=None) -> dict:
    """editor_ops batch from committed-but-unsynced history rows."""
    projection = projection_conn or conn
    items = []
    skipped = []
    for row in pending_history(conn):
        spec = SPEC_BY_TABLE.get(row["entity_type"])
        if spec is None or not spec.editable:
            skipped.append({"history_id": row["id"],
                            "reason": f"no workbook write path for "
                                      f"{row['entity_type']}"})
            continue
        old = json.loads(row["old_json"]) if row["old_json"] else {}
        new = json.loads(row["new_json"]) if row["new_json"] else {}
        sheet = old.get("src_sheet") or target_sheet_for(
            projection, spec, row["model_id"])
        if not sheet:
            skipped.append({"history_id": row["id"],
                            "reason": "target sheet could not be resolved"})
            continue
        key_source = old if row["op"] != "add" else new
        key = {k: str(key_source.get(k, "")) for k in spec.key}
        op: dict = {"action": row["op"], "sheet": sheet, "key": key,
                    "_history_id": row["id"]}
        if row["op"] in ("add", "update"):
            # key columns are immutable on update in editor_ops; they travel
            # in `key` only. Adds carry the full row including keys.
            skip = set(spec.key) if row["op"] == "update" else set()
            op["row"] = {c.header: str(new.get(c.sql_name(), "") or "")
                         for c in spec.columns if c.sql_name() not in skip}
        items.append(op)
    return {
        "workbookMtimeNs": str(workbook_path.stat().st_mtime_ns),
        "items": [{k: v for k, v in op.items() if not k.startswith("_")}
                  for op in items],
        "historyIds": [op["_history_id"] for op in items],
        "skipped": skipped,
    }


def sync_workbook(conn: sqlite3.Connection, workbook_path: Path, *,
                  write: bool = False, confirmed_warnings=(),
                  expected_mtime_ns: str | None = None,
                  projection_conn=None) -> dict:
    batch = build_batch(conn, workbook_path, projection_conn)
    if not batch["items"]:
        return {"ok": False, "status": "empty", "errors":
                ["no committed changes are pending synchronization"],
                "skipped": batch["skipped"]}
    if write and expected_mtime_ns is not None and \
            str(expected_mtime_ns) != batch["workbookMtimeNs"]:
        return {"ok": False, "status": "stale",
                "errors": ["workbook changed since the reviewed dry-run; "
                           "run dry-run again"], "skipped": batch["skipped"]}
    result = editor_ops.apply_batch(
        workbook_path,
        {"workbookMtimeNs": batch["workbookMtimeNs"], "items": batch["items"]},
        write=write,
        confirmed_warnings=confirmed_warnings,
        source="workbook-manager",
        log_path=config.EDIT_LOG_PATH if write else None,
    )
    result = dict(result)
    result["skipped"] = batch["skipped"]
    result["workbookMtimeNs"] = batch["workbookMtimeNs"]
    result["opCount"] = len(batch["items"])
    if write and result.get("ok"):
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        detail = json.dumps({
            "backup": str(result.get("backupPath", "")),
            "synced_at": now,
        })
        conn.executemany(
            "UPDATE change_history SET sync_status='synced', sync_detail=? "
            "WHERE id=?", [(detail, hid) for hid in batch["historyIds"]])
        conn.commit()
    elif write and not result.get("ok"):
        conn.executemany(
            "UPDATE change_history SET sync_status='sync_failed', "
            "sync_detail=? WHERE id=?",
            [(json.dumps({"status": result.get("status"),
                          "errors": result.get("errors", [])}), hid)
             for hid in batch["historyIds"]])
        conn.commit()
        # a failed gated write leaves the workbook untouched (atomic path),
        # but flag loudly for the caller.
    return result


# ── comparison export ────────────────────────────────────────────────

def export_comparison_workbook(conn: sqlite3.Connection,
                               workbook_path: Path) -> dict:
    """Create an identity-bound, semantically verified comparison copy.

    Pass 4 has no draft overlay, so a freshly imported projection normally emits
    no operations and remains byte-identical. If registry-owned projected fields
    differ, reconstruction overlays them through ``editor_ops.apply_batch``;
    opaque workbook surfaces remain owned by the bound source copy.
    """

    config.ensure_dirs()
    bound_identity = {
        "sha256": dbmod.get_meta(conn, "workbook_sha256") or "",
        "mtime_ns": int(dbmod.get_meta(conn, "workbook_mtime_ns") or 0),
    }
    identity = importer.workbook_identity(workbook_path)
    if bound_identity != identity:
        return {
            "ok": False,
            "status": "stale",
            "errors": ["source workbook identity differs from the promoted projection"],
        }
    out_path = config.EXPORT_DIR / f"DISPOSABLE-comparison-{_now_slug()}.xlsx"
    candidate = out_path.with_name(
        f".{out_path.stem}.{uuid.uuid4().hex}.candidate.xlsx"
    )
    try:
        shutil.copy2(workbook_path, candidate)
        copied_identity = importer.workbook_identity(candidate)
        live_identity = importer.workbook_identity(workbook_path)
        if copied_identity != bound_identity or live_identity != bound_identity:
            return {
                "ok": False,
                "status": "stale",
                "errors": ["source workbook changed while comparison export was copied"],
            }
        (
            package_valid,
            schema_valid,
            semantic_equal,
            issues,
        ) = (
            importer._validate_reconstruction(
                workbook_path,
                conn,
                reconstruction_path=candidate,
            )
        )
        if not (
            package_valid
            and schema_valid
            and semantic_equal
        ):
            return {
                "ok": False,
                "status": "reconstruction_failed",
                "errors": [issue.get("message", str(issue)) for issue in issues],
            }
        if importer.workbook_identity(workbook_path) != bound_identity:
            return {
                "ok": False,
                "status": "stale",
                "errors": ["source workbook changed during comparison reconstruction"],
            }
        byte_identical = candidate.read_bytes() == workbook_path.read_bytes()
        dbmod._replace_candidate(candidate, out_path)
        return {
            "ok": True,
            "disposable": True,
            "path": str(out_path),
            "byte_identical": byte_identical,
            "semantic_readback_verified": True,
            # Runtime-contract parity is proven by the separate slow acceptance
            # gate; comparison export itself verifies only semantic readback.
            "generated_contract_parity_verified": False,
            "rewritten": {} if byte_identical else {"registry_owned_fields": "overlaid"},
        }
    finally:
        candidate.unlink(missing_ok=True)


def backup_database(conn: sqlite3.Connection, db_path: Path) -> dict:
    config.ensure_dirs()
    out = config.DB_BACKUP_DIR / f"workbook-manager-{_now_slug()}.sqlite3"
    dest = sqlite3.connect(out)
    with dest:
        conn.backup(dest)
    dest.close()
    return {"ok": True, "path": str(out)}
