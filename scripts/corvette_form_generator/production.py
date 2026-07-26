"""Stingray legacy compatibility export.

This module no longer builds source data. Pass 2 receipt C absorbed the Stingray
source builder into the single workbook-driven builder in ``inspection.py``, so
every model is assembled identically and finalized through
``runtime_contract.build_model_runtime_contract``.

What remains is one secondary output: the legacy ``stingray-form-data.json`` and
``stingray-form-data.csv`` pair, retained only while a current consumer is proven
(spec Pass 2 requirement 8). It is not source-construction authority, a readiness
gate, a promotion artifact type, or a registry fallback. Nothing here reads the
workbook, holds module state, or writes to it.
"""

from __future__ import annotations

import csv
from typing import Any

from corvette_form_generator.contract import ASSET_IMAGE_FIELDS
from corvette_form_generator.model_config import ModelConfig
from corvette_form_generator.output import write_json_output

COMPATIBILITY_CSV_FIELDS = (
    "choice_id",
    "option_id",
    "rpo",
    "label",
    "section_id",
    "step_key",
    "variant_id",
    "body_style",
    "trim_level",
    "status",
    "selectable",
    "base_price",
    *ASSET_IMAGE_FIELDS,
)


def write_stingray_compatibility_artifacts(
    config: ModelConfig,
    source_data: dict[str, Any],
    runtime_data: dict[str, Any],
) -> dict[str, Any]:
    """Write the legacy Stingray JSON/CSV compatibility artifacts."""

    if config.model_key != "stingray":
        raise ValueError("compatibility artifact writer supports only stingray")

    config.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = config.output_dir / "stingray-form-data.json"
    write_json_output(json_path, runtime_data)

    csv_path = config.output_dir / "stingray-form-data.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, lineterminator="\n", fieldnames=list(COMPATIBILITY_CSV_FIELDS))
        writer.writeheader()
        for row in source_data["choices"]:
            writer.writerow({key: row.get(key, "") for key in writer.fieldnames})

    return {"json": str(json_path), "csv": str(csv_path)}
