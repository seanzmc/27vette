#!/usr/bin/env python3
"""Profile a raw GM Corvette order-guide export into Pass 0 evidence artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from corvette_form_generator.ingest.source_profiler import profile_order_guide  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-export", required=True, help="Official raw GM order-guide .xlsx export.")
    parser.add_argument("--workbook", default=str(ROOT / "stingray_master.xlsx"), help="Canonical workbook reference, read-only.")
    parser.add_argument("--run-id", required=True, help="Run identifier used in reports/manifests.")
    parser.add_argument("--output-dir", required=True, help="Directory for run-scoped evidence artifacts.")
    args = parser.parse_args()

    try:
        result = profile_order_guide(
            raw_export=Path(args.raw_export),
            workbook=Path(args.workbook),
            output_dir=Path(args.output_dir),
            run_id=args.run_id,
            root=ROOT,
        )
    except Exception as exc:  # noqa: BLE001 - CLI should print clean failure
        print(f"order-guide ingest profiler failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2))
    return 1 if result["status"] != "passed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
