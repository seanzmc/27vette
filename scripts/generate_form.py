#!/usr/bin/env python3
"""Single entry point for Corvette form-data generation.

Usage:
    python scripts/generate_form.py --model stingray      # Stingray JSON/CSV/runtime-contract artifacts
    python scripts/generate_form.py --model grand_sport   # inspection/preview/draft/runtime-contract artifacts
    python scripts/generate_form.py --model z06           # inspection/preview/draft/runtime-contract artifacts
    python scripts/generate_registry.py                   # app registry from promoted runtime artifacts

This command is scoped to one model's generated artifacts. It does not publish
the browser app registry; run ``scripts/generate_registry.py`` after model
generation when promoted runtime data should be refreshed in ``form-app/data.js``.
"""

from __future__ import annotations

import argparse
import json

from corvette_form_generator.model_generation import generate_model_artifacts
from corvette_form_generator.model_configs import discover_generation_model_configs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--model",
        required=True,
        help="model key to generate",
    )
    args = parser.parse_args()

    configs = discover_generation_model_configs()
    if args.model not in configs:
        active_models = ", ".join(sorted(configs)) or "none"
        parser.error(f"Unsupported or inactive model {args.model!r}. Active generatable models: {active_models}")

    base_config = configs[args.model]
    print(json.dumps(generate_model_artifacts(base_config), indent=2))


if __name__ == "__main__":
    main()
