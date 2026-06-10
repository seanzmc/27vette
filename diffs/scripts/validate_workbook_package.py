#!/usr/bin/env python3
"""Validate Excel package metadata that Excel repairs on open."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from corvette_form_generator.workbook_package import validate_workbook_package


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", nargs="?", default="stingray_master.xlsx")
    args = parser.parse_args()

    workbook_path = Path(args.workbook)
    issues = validate_workbook_package(workbook_path)
    result = {
        "workbook": str(workbook_path),
        "status": "valid" if not issues else "invalid",
        "issue_count": len(issues),
        "issues": issues,
    }
    print(json.dumps(result, indent=2))
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
