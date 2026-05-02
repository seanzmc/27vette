#!/usr/bin/env python3
"""Extract staging evidence from a raw Chevrolet order guide export workbook."""

from __future__ import annotations

import argparse
from pathlib import Path

from order_guide_importer import extract_staging, write_staging_outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="Path to raw Chevrolet order guide .xlsx export.")
    parser.add_argument("--out", required=True, help="Directory to write staging CSVs and import_report.json.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = Path(args.source)
    if not source.exists():
        raise SystemExit(f"Source workbook does not exist: {source}")
    write_staging_outputs(Path(args.out), extract_staging(source))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
