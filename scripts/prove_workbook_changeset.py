#!/usr/bin/env python3
"""Run ChangeSet deployment proof on isolated temporary workbooks only."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from corvette_form_generator.workbook_domain.deployment_proof import (  # noqa: E402
    prove_changeset_deployment,
)


def _load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: str, payload: dict) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("changeset", help="path to workbook-changeset-1 JSON")
    parser.add_argument("--workbook", default=str(ROOT / "stingray_master.xlsx"))
    parser.add_argument("--manifest", required=True, help="bound canonical manifest JSON")
    parser.add_argument(
        "--compile-report",
        required=True,
        help="bound compile report JSON",
    )
    parser.add_argument("--proof-out", required=True, help="deployment proof receipt path")
    args = parser.parse_args(argv)

    proof = prove_changeset_deployment(
        Path(args.workbook),
        _load_json(args.changeset),
        canonical_manifest_path=Path(args.manifest),
        compile_report_path=Path(args.compile_report),
    )
    _write_json(args.proof_out, proof)
    print(
        f"deployment-proof: status={proof.get('status')} "
        f"ok={proof.get('ok')} proofFingerprint={proof.get('proofFingerprint')}"
    )
    for error in proof.get("errors") or []:
        print(f"error: {error}", file=sys.stderr)
    return 0 if proof.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
