#!/usr/bin/env python3
"""Repair Excel table metadata without changing worksheet cell data."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from corvette_form_generator.workbook_package import repair_workbook_tables


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", nargs="?", default="stingray_master.xlsx")
    parser.add_argument("--no-backup", action="store_true", help="Do not create a timestamped backup before replacing the workbook.")
    args = parser.parse_args()

    workbook_path = Path(args.workbook)
    result = repair_workbook_tables(workbook_path, backup=not args.no_backup)
    print(json.dumps(result, indent=2))
    return 1 if result["issues_after"] else 0


if __name__ == "__main__":
    sys.exit(main())
