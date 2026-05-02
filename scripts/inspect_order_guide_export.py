#!/usr/bin/env python3
"""Profile a raw Chevrolet order guide export workbook."""

from __future__ import annotations

import argparse
from pathlib import Path

from order_guide_importer import profile_workbook, write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="Path to raw Chevrolet order guide .xlsx export.")
    parser.add_argument("--out", required=True, help="Path to write deterministic source_profile.json.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = Path(args.source)
    if not source.exists():
        raise SystemExit(f"Source workbook does not exist: {source}")
    profile = profile_workbook(source)
    write_json(Path(args.out), profile)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
