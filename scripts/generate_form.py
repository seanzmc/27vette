#!/usr/bin/env python3
"""Single entry point for Corvette form-data generation.

Usage:
    python scripts/generate_form.py --model stingray      # Stingray JSON/CSV/runtime-contract artifacts
    python scripts/generate_form.py --model grand_sport   # runtime-contract artifact
    python scripts/generate_form.py --model z06           # runtime-contract artifact
    python scripts/generate_form.py --model z06 --emit-inspection --inspection-output /tmp/z06-inspection
    python scripts/generate_registry.py                   # app registry from promoted runtime artifacts

This command is scoped to one model's generated artifacts. It does not publish
the browser app registry; run ``scripts/generate_registry.py`` after model
generation when promoted runtime data should be refreshed in ``form-app/data.js``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from corvette_form_generator.model_generation import GenerationOptions, generate_model_artifacts
from corvette_form_generator.model_configs import discover_generation_model_configs

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--model",
        required=True,
        help="model key to generate",
    )
    parser.add_argument(
        "--workbook",
        type=Path,
        default=PROJECT_ROOT / "stingray_master.xlsx",
        help="exact workbook snapshot to read",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=PROJECT_ROOT,
        help="root containing candidate form-output/ and form-app/ directories",
    )
    parser.add_argument(
        "--emit-inspection",
        action="store_true",
        help="write optional inspection, contract-preview, and draft artifacts for review",
    )
    parser.add_argument(
        "--inspection-output",
        type=Path,
        help="directory for optional inspection artifacts; requires --emit-inspection",
    )
    args = parser.parse_args()

    if args.inspection_output is not None and not args.emit_inspection:
        parser.error("--inspection-output requires --emit-inspection")

    configs = discover_generation_model_configs(
        args.workbook,
        root=args.output_root,
    )
    if args.model not in configs:
        active_models = ", ".join(sorted(configs)) or "none"
        parser.error(f"Unsupported or inactive model {args.model!r}. Active generatable models: {active_models}")

    base_config = configs[args.model]
    options = GenerationOptions(
        emit_inspection=args.emit_inspection,
        inspection_output_dir=args.inspection_output,
    )
    print(json.dumps(generate_model_artifacts(base_config, options=options), indent=2))


if __name__ == "__main__":
    main()
