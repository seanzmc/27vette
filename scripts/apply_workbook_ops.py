#!/usr/bin/env python3
"""Apply a workbook-editor ops batch (ops.json) to stingray_master.xlsx.

Default is validate + dry-run only; nothing is written without --write.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from corvette_form_generator.editor_ops import apply_batch  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ops", help="ops.json exported from the workbook editor")
    parser.add_argument("--workbook", default=str(ROOT / "stingray_master.xlsx"))
    parser.add_argument("--write", action="store_true",
                        help="actually apply (default: validate + dry-run only)")
    parser.add_argument("--confirm-warnings", default="",
                        help="comma-separated warning ids to confirm")
    parser.add_argument("--allow-stale", action="store_true",
                        help="skip the workbook-mtime match check "
                             "(validation still runs against current state)")
    args = parser.parse_args()

    batch = json.loads(Path(args.ops).read_text(encoding="utf-8"))
    confirmed = [w for w in args.confirm_warnings.split(",") if w]
    result = apply_batch(args.workbook, batch, write=args.write, source="cli",
                         confirmed_warnings=confirmed, allow_stale=args.allow_stale)
    print(json.dumps(result, indent=2, default=str))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
