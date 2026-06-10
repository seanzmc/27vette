#!/usr/bin/env python3
"""Validate standardized workbook source-schema contracts."""

from __future__ import annotations

import argparse
import json
import sys

from corvette_form_generator.schema_validation import result_payload, validate_workbook_schema


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", nargs="?", default="stingray_master.xlsx")
    parser.add_argument(
        "--skip-live-contract",
        action="store_true",
        help="Skip form-app/data.js draft/provenance leak checks.",
    )
    args = parser.parse_args()

    issues = validate_workbook_schema(args.workbook, check_live_contract=not args.skip_live_contract)
    payload = result_payload(args.workbook, issues)
    print(json.dumps(payload, indent=2, default=str))
    return 1 if payload["error_count"] else 0


if __name__ == "__main__":
    sys.exit(main())
