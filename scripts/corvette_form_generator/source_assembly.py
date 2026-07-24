"""Shared source assembly facade for active model generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from corvette_form_generator.inspection import build_contract_preview, build_form_data_draft, inspect_model_sources
from corvette_form_generator.model_config import ModelConfig
from corvette_form_generator.runtime_contract import build_model_runtime_contract


@dataclass(frozen=True)
class ModelSourceAssembly:
    """Workbook-derived source payloads plus the finalized runtime contract."""

    config: ModelConfig
    source_data: dict[str, Any]
    runtime_contract: dict[str, Any]
    report: dict[str, Any] | None = None
    preview: dict[str, Any] | None = None
    draft: dict[str, Any] | None = None
    compatibility_source: bool = False
    derivation_manifest: dict[str, Any] | None = None


def assemble_model_source(config: ModelConfig) -> ModelSourceAssembly:
    """Assemble workbook source rows for one active model.

    The orchestration layer calls this single facade for every active model.
    Stingray retains its legacy compatibility source payload while Grand Sport
    and Z06 retain their workbook inspection/preview/draft source payloads; all
    paths finalize through ``build_model_runtime_contract``.
    """

    if config.model_key == "stingray":
        from corvette_form_generator.production import build_production_source_data

        source_data = build_production_source_data(config)
        return ModelSourceAssembly(
            config=config,
            source_data=source_data,
            runtime_contract=build_model_runtime_contract(config, source_data),
            compatibility_source=True,
            derivation_manifest=source_data.get("_derivationManifest"),
        )

    report = inspect_model_sources(config)
    preview = build_contract_preview(config)
    draft = build_form_data_draft(config, preview=preview)
    return ModelSourceAssembly(
        config=config,
        source_data=draft,
        runtime_contract=build_model_runtime_contract(config, draft),
        report=report,
        preview=preview,
        draft=draft,
        derivation_manifest=draft.get("_derivationManifest"),
    )
