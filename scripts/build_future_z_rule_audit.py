#!/usr/bin/env python3
"""Build a read-only Z06/ZR1/ZR1X rule/exclusive/default readiness audit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from corvette_form_generator.future_z_rule_audit import (  # noqa: E402
    Z_MODEL_KEYS,
    build_z_rule_audit,
    render_z_rule_audit_markdown,
)
from corvette_form_generator.model_configs import WORKBOOK_PATH  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-key", choices=("all", *Z_MODEL_KEYS), default="all")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--workbook", type=Path, default=WORKBOOK_PATH)
    args = parser.parse_args(argv)

    model_keys = list(Z_MODEL_KEYS) if args.model_key == "all" else [args.model_key]
    wb = load_workbook(args.workbook, read_only=True, data_only=True)
    try:
        audit = build_z_rule_audit(wb, model_keys)
    finally:
        wb.close()

    if args.format == "markdown":
        print(render_z_rule_audit_markdown(audit))
    else:
        print(json.dumps(audit, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
