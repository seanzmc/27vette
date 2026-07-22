#!/usr/bin/env python3
"""Shared operator CLI over the workbook-domain ChangeSet service.

This script is the single operator entry point for the guarded workbook
ChangeSet write path owned by
``corvette_form_generator.workbook_domain.service``. Preview is the default
mode and never writes the workbook. ``--approve`` binds an actor to an exact
preview artifact and never writes the workbook. ``--write`` reaches the
workbook only when presented with both exact bound artifacts (preview +
approval) and journals a receipt.
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

from corvette_form_generator.workbook_domain.service import (  # noqa: E402
    apply_changeset,
    approve_changeset,
    preview_changeset,
)


def _load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path, payload):
    Path(path).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _summarize(kind, payload):
    parts = [kind, f"ok={payload.get('ok')}"]
    if payload.get("status"):
        parts.append(f"status={payload['status']}")
    if payload.get("changeSetId"):
        parts.append(f"changeSetId={payload['changeSetId']}")
    if payload.get("semanticFingerprint"):
        parts.append(
            f"semanticFingerprint={str(payload['semanticFingerprint'])[:24]}"
        )
    if payload.get("workbookState"):
        parts.append(f"workbookState={payload['workbookState']}")
    print(" ".join(parts))


def _print_errors(payload):
    for error in payload.get("errors") or []:
        print(f"error: {error}", file=sys.stderr)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "changeset",
        help="path to the workbook-changeset-1 JSON proposal",
    )
    parser.add_argument(
        "--workbook",
        default=str(ROOT / "stingray_master.xlsx"),
        help="canonical workbook path",
    )
    parser.add_argument(
        "--preview-out",
        help="write the preview artifact JSON here (preview mode)",
    )
    parser.add_argument(
        "--approve",
        metavar="ACTOR",
        help="bind ACTOR's approval to the --preview artifact; never writes",
    )
    parser.add_argument(
        "--preview",
        help="path to the exact bound preview artifact "
             "(required by --approve and --write)",
    )
    parser.add_argument(
        "--approval-out",
        help="write the approval artifact JSON here (--approve mode)",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="apply the ChangeSet once; requires --preview and --approval",
    )
    parser.add_argument(
        "--approval",
        help="path to the exact bound approval artifact (required by --write)",
    )
    parser.add_argument(
        "--receipt-out",
        help="write the receipt artifact JSON here (--write mode)",
    )
    parser.add_argument(
        "--accept-warning",
        action="append",
        default=[],
        metavar="WARNING_ID",
        help="accepted confirmable warning ID for --approve; repeat as needed",
    )
    parser.add_argument(
        "--log-path",
        default=None,
        help="edit-log journal override for --write (default: service default)",
    )
    args = parser.parse_args(argv)

    if args.approve and args.write:
        print(
            "error: --approve and --write are separate modes; run them as "
            "separate invocations",
            file=sys.stderr,
        )
        return 2

    changeset = _load_json(args.changeset)
    workbook = Path(args.workbook)

    if args.approve:
        if not args.preview:
            print(
                "error: --approve requires --preview (the exact bound preview "
                "artifact being approved)",
                file=sys.stderr,
            )
            return 2
        preview = _load_json(args.preview)
        approval = approve_changeset(
            changeset,
            preview,
            actor=args.approve,
            warning_ids=args.accept_warning,
        )
        if args.approval_out:
            _write_json(args.approval_out, approval)
        _summarize("approval", approval)
        if not approval.get("ok"):
            _print_errors(approval)
            return 1
        return 0

    if args.write:
        missing = [
            flag
            for flag, value in (
                ("--preview", args.preview),
                ("--approval", args.approval),
            )
            if not value
        ]
        if missing:
            print(
                f"error: --write requires both exact bound artifacts; "
                f"missing {', '.join(missing)}",
                file=sys.stderr,
            )
            return 2
        preview = _load_json(args.preview)
        approval = _load_json(args.approval)
        receipt = apply_changeset(
            workbook,
            changeset,
            preview,
            approval,
            log_path=args.log_path,
        )
        if args.receipt_out:
            _write_json(args.receipt_out, receipt)
        _summarize("receipt", receipt)
        if not receipt.get("ok"):
            _print_errors(receipt)
            return 1
        return 0

    # Default mode: preview only; never writes the workbook.
    preview = preview_changeset(workbook, changeset)
    if args.preview_out:
        _write_json(args.preview_out, preview)
    _summarize("preview", preview)
    if not preview.get("ok"):
        _print_errors(preview)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
