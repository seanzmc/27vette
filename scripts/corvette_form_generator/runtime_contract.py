"""Model-neutral runtime-contract finalization helpers."""

from __future__ import annotations

from typing import Any

from corvette_form_generator.model_config import ModelConfig
from corvette_form_generator.registry_promotion import live_contract_data


def build_model_runtime_contract(config: ModelConfig, data: dict[str, Any]) -> dict[str, Any]:
    """Return the clean browser runtime contract for one model dataset.

    The input may be the current-generation Stingray dataset or a draft dataset
    from the inspection path. This function is intentionally model-neutral: the
    workbook/source-row builders own product behavior, and runtime finalization
    only applies the shared live-contract cleanup/status rules.
    """

    _ = config
    return live_contract_data(data)
