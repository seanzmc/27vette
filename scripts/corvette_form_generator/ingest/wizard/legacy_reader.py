#!/usr/bin/env python3
"""JSON-only display adapter for historical ingest run artifacts.

This reader intentionally exposes no mutation, approval, application, workbook,
generator, publication, or promotion methods. It exists only so the local
wizard can display immutable artifacts produced by current and historical runs.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

RUN_ID_RE = re.compile(r"^[0-9]{8}-[0-9]{6}-[0-9a-f]{6}$")


class LegacyRunReader:
    """Read run-scoped JSON without importing ingest mutation authority."""

    def __init__(self, base: Path) -> None:
        self.base = Path(base)

    def _run_dir(self, run_id: str) -> Path:
        if not RUN_ID_RE.fullmatch(str(run_id)):
            raise ValueError("Invalid run ID.")
        run_dir = self.base / run_id
        if not run_dir.is_dir():
            raise FileNotFoundError(f"Run not found: {run_id}")
        return run_dir

    @staticmethod
    def _read(path: Path) -> dict[str, Any]:
        if not path.is_file():
            raise FileNotFoundError(f"Artifact not found: {path.name}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Artifact must be a JSON object: {path.name}")
        return payload

    def changeset_detail(self, run_id: str) -> dict[str, Any]:
        run_dir = self._run_dir(run_id)
        return {
            "session": self._read(run_dir / "session.json"),
            "changeSet": self._read(run_dir / "workbook-change-set.json"),
        }

    def plan_detail(self, run_id: str) -> dict[str, Any]:
        """Return raw historical plan evidence for GET-only compatibility."""

        run_dir = self._run_dir(run_id)
        dry_run = run_dir / "apply-plan-dryrun.json"
        approval = run_dir / "plan-approval.json"
        return {
            "session": self._read(run_dir / "session.json"),
            "plan": self._read(run_dir / "apply-plan.json"),
            "dryRun": self._read(dry_run) if dry_run.is_file() else None,
            "approval": self._read(approval) if approval.is_file() else None,
        }
