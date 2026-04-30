#!/usr/bin/env python3
"""Read-only scaffold for future Grand Sport form generation."""

from __future__ import annotations

import json

from corvette_form_generator.inspection import inspect_model_sources, write_inspection_artifacts
from corvette_form_generator.model_configs import GRAND_SPORT_MODEL


def main() -> None:
    config = GRAND_SPORT_MODEL
    report = inspect_model_sources(config)
    artifact_paths = write_inspection_artifacts(report, config.output_dir / "inspection")
    print(
        json.dumps(
            {
                "model_key": config.model_key,
                "model_label": config.model_label,
                "model_year": config.model_year,
                "status": report["status"],
                "source_option_sheet": config.source_option_sheet,
                "variant_ids": list(config.variant_ids),
                "expected_variant_count": config.expected_variant_count,
                "counts": report["counts"],
                "blank_section_overrides": dict(config.blank_section_overrides),
                "warnings": report["warnings"],
                "artifacts": artifact_paths,
                "notes": list(config.notes),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
