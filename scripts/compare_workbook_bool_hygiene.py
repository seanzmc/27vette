#!/usr/bin/env python3
"""Compare bool-like workbook cell storage before and after a workbook write."""

from __future__ import annotations

import argparse
import json
import sys

from corvette_form_generator.workbook_bool_hygiene import (
    compare_bool_like_workbooks,
    result_payload,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before_workbook", help="Workbook before the write pass.")
    parser.add_argument("after_workbook", help="Workbook after the write pass.")
    parser.add_argument(
        "--approve",
        action="append",
        default=[],
        metavar="SHEET.COLUMN",
        help="Explicitly approve a bool/text storage migration for one exact sheet.column. May be repeated.",
    )
    args = parser.parse_args()

    issues = compare_bool_like_workbooks(
        args.before_workbook,
        args.after_workbook,
        approved_bool_type_migrations=args.approve,
    )
    payload = result_payload(args.before_workbook, args.after_workbook, issues)
    print(json.dumps(payload, indent=2, default=str))
    return 1 if payload["error_count"] else 0


if __name__ == "__main__":
    sys.exit(main())
