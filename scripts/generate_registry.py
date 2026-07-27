#!/usr/bin/env python3
"""Generate the static app model registry from promoted runtime artifacts.

This command is the only workflow entry point that writes ``form-app/data.js``.
Run the relevant model generator(s) first, then run this to publish promoted
runtime contracts into the browser registry.

The write is atomic (spec Pass 3 requirement 9): the registry lands in a
temporary file beside the target and replaces it in one step, so a crash cannot
leave the browser loading a truncated ``data.js``.

With no arguments it publishes the canonical workbook's promoted set to
``form-app/data.js``. ``--root`` / ``--output`` let a caller build the same
registry somewhere else — used by gates that must not touch a tracked artifact.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from corvette_form_generator.contract import load_model_asset_map
from corvette_form_generator.model_configs import APP_DIR, ROOT, WORKBOOK_PATH
from corvette_form_generator.output import write_app_data_registry
from corvette_form_generator.registry_promotion import (
    artifact_path_for_promotion,
    build_registry_from_artifacts,
    load_registry_promotions,
    registry_model_key,
)


def default_output_path(root: Path) -> Path:
    """Where the registry lands for a given root.

    An isolated root stays isolated on both sides: artifacts resolve from it and
    the registry is written inside it, so a caller cannot accidentally read a
    candidate's contracts and publish them over the tracked app.
    """

    return (APP_DIR if root == ROOT else root / "form-app") / "data.js"


def generate_registry(
    *,
    workbook_path: Path = WORKBOOK_PATH,
    root: Path = ROOT,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Build the registry from promoted artifacts under ``root`` and write it."""

    wb = load_workbook(workbook_path, read_only=True, data_only=True)
    try:
        promotions = load_registry_promotions(wb)
        model_assets = load_model_asset_map(wb, registry_model_key)
        registry = build_registry_from_artifacts(wb, model_assets=model_assets, root=root)
    finally:
        wb.close()

    legacy_aliases = registry.pop("legacyAliases", {})
    target = output_path if output_path is not None else default_output_path(root)
    write_app_data_registry(target, registry, legacy_aliases=legacy_aliases)

    return {
        "status": "registry_generated",
        "output": str(target),
        "default_model": registry.get("defaultModelKey"),
        "models": list(registry.get("models", {}).keys()),
        "legacy_aliases": legacy_aliases,
        "artifacts": {
            promotion.registry_key: str(artifact_path_for_promotion(root, promotion))
            for promotion in promotions
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--workbook", type=Path, default=WORKBOOK_PATH, help="workbook to read promotions from")
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="root that promoted artifact paths resolve from (default: the repository)",
    )
    parser.add_argument("--output", type=Path, help="registry file to write (default: <root>/form-app/data.js)")
    args = parser.parse_args(argv)

    print(json.dumps(generate_registry(workbook_path=args.workbook, root=args.root, output_path=args.output), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
