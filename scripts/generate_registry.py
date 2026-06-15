#!/usr/bin/env python3
"""Generate the static app model registry from promoted runtime artifacts.

This command is the only workflow entry point that writes ``form-app/data.js``.
Run the relevant model generator(s) first, then run this to publish promoted
runtime contracts into the browser registry.
"""

from __future__ import annotations

import json

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


def main() -> None:
    wb = load_workbook(WORKBOOK_PATH, read_only=True, data_only=True)
    try:
        promotions = load_registry_promotions(wb)
        model_assets = load_model_asset_map(wb, registry_model_key)
        registry = build_registry_from_artifacts(wb, model_assets=model_assets, root=ROOT)
    finally:
        wb.close()

    legacy_aliases = registry.pop("legacyAliases", {})
    APP_DIR.mkdir(exist_ok=True)
    output_path = APP_DIR / "data.js"
    write_app_data_registry(output_path, registry, legacy_aliases=legacy_aliases)

    print(
        json.dumps(
            {
                "status": "registry_generated",
                "output": str(output_path),
                "default_model": registry.get("defaultModelKey"),
                "models": list(registry.get("models", {}).keys()),
                "legacy_aliases": legacy_aliases,
                "artifacts": {
                    promotion.registry_key: str(artifact_path_for_promotion(ROOT, promotion))
                    for promotion in promotions
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
