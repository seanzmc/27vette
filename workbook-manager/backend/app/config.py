"""Paths and environment for the workbook manager backend."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# workbook-manager/backend/app/config.py -> repo root is 3 levels up.
REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

MODULE_ROOT = REPO_ROOT / "workbook-manager"
VAR_DIR = Path(os.environ.get("WBM_VAR_DIR", MODULE_ROOT / "var"))
EXPORT_DIR = VAR_DIR / "exports"
DB_BACKUP_DIR = VAR_DIR / "db-backups"
APPLY_ROLLBACK_DIR = VAR_DIR / "apply-rebuild-rollbacks"

DEFAULT_WORKBOOK = Path(
    os.environ.get("WBM_WORKBOOK", REPO_ROOT / "stingray_master.xlsx")
)
DEFAULT_DB = Path(os.environ.get("WBM_DB", VAR_DIR / "workbook_manager.sqlite3"))
DEFAULT_PROJECTION_DB = Path(
    os.environ.get("WBM_PROJECTION_DB", VAR_DIR / "workbook_projection.sqlite3")
)
APPLY_OUTPUT_ROOT = Path(os.environ.get("WBM_APPLY_OUTPUT_ROOT", REPO_ROOT))

FRONTEND_DIST = MODULE_ROOT / "frontend" / "dist"

# Written by editor_ops.apply_batch on live writes (same log the workbook
# editor uses), keeping one shared audit trail for workbook mutations.
EDIT_LOG_PATH = APPLY_OUTPUT_ROOT / "form-output" / "workbook-edit-log.jsonl"


def ensure_dirs() -> None:
    for d in (VAR_DIR, EXPORT_DIR, DB_BACKUP_DIR, APPLY_ROLLBACK_DIR):
        d.mkdir(parents=True, exist_ok=True)
