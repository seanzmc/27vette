#!/usr/bin/env python3
"""Deprecated compatibility entry point for asset_map sync.

Use the safe project command instead:

    .venv/bin/python scripts/sync_asset_map.py --workbook stingray_master.xlsx --report-dir /tmp/asset-map-sync
"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SAFE_COMMAND = ROOT / "scripts" / "sync_asset_map.py"


def main() -> int:
    print(
        "asset_map-Sync/asset_map_sync.py is retired. "
        f"Use .venv/bin/python {SAFE_COMMAND.relative_to(ROOT)} instead.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
