#!/usr/bin/env python3
"""Apply an approved ingest-wizard plan.

Default mode is dry-run/report only. Passing --write applies to the workbook,
but only after the run is already plan_approved and all fingerprints still
match the approved plan. This CLI never promotes generated runtime artifacts.
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

from corvette_form_generator.ingest.wizard.session import (  # noqa: E402
    WizardError,
    WizardSessionStore,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, help="ingest wizard run id")
    parser.add_argument("--root", default=str(ROOT), help="project root containing form-output/ingest-wizard")
    parser.add_argument("--workbook", default=str(ROOT / "stingray_master.xlsx"), help="canonical workbook path")
    parser.add_argument("--write", action="store_true", help="write the workbook; default is dry-run/report only")
    parser.add_argument(
        "--confirm-plan-warnings",
        action="store_true",
        help="confirm all apply_batch warnings from the approved plan during --write",
    )
    parser.add_argument(
        "--no-schema-validation",
        action="store_true",
        help="disable schema validation for fixture tests only; real runs should leave it enabled",
    )
    args = parser.parse_args()

    store = WizardSessionStore(Path(args.root), workbook_path=Path(args.workbook))
    try:
        result = store.apply_approved_plan(
            args.run,
            write=args.write,
            confirm_plan_warnings=args.confirm_plan_warnings,
            schema_validation=not args.no_schema_validation,
        )
    except WizardError as exc:
        print(json.dumps({"ok": False, "status": "error", "errors": [str(exc)]}, indent=2), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
