#!/usr/bin/env python3
"""Normalize Pass 0 order-guide evidence into read-only candidate artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from corvette_form_generator.ingest.candidate_normalizer import normalize_order_guide_candidates  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", required=True, help="Directory containing Pass 0 evidence artifacts.")
    parser.add_argument("--workbook", default=str(ROOT / "stingray_master.xlsx"), help="Canonical workbook reference, read-only.")
    parser.add_argument("--models", default="", help="Comma-separated selected model keys for focused ingest, e.g. zr1,zr1x,z06.")
    parser.add_argument("--primary-models", default="", help="Optional comma-separated primary selected model keys.")
    parser.add_argument("--comparator-models", default="", help="Optional comma-separated comparator selected model keys.")
    parser.add_argument("--run-id", required=True, help="Run identifier used in reports/manifests.")
    parser.add_argument("--output-dir", required=True, help="Directory for transient candidate artifacts.")
    args = parser.parse_args()

    try:
        result = normalize_order_guide_candidates(
            evidence_dir=Path(args.evidence_dir),
            workbook=Path(args.workbook),
            output_dir=Path(args.output_dir),
            run_id=args.run_id,
            root=ROOT,
            selected_models=args.models or None,
            primary_models=args.primary_models or None,
            comparator_models=args.comparator_models or None,
        )
    except Exception as exc:  # noqa: BLE001 - CLI should print clean failure
        print(f"order-guide candidate normalizer failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2))
    return 1 if result["status"] != "passed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
