"""Shared source assembly facade for active model generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from openpyxl import load_workbook

from corvette_form_generator.inspection import build_contract_preview, build_form_data_draft, inspect_model_sources
from corvette_form_generator.model_config import ModelConfig
from corvette_form_generator.runtime_contract import build_model_runtime_contract


@dataclass(frozen=True)
class ModelSourceAssembly:
    """Workbook-derived source payload plus the finalized runtime contract.

    ``report`` and ``preview`` are optional review payloads. They are populated
    only when the caller explicitly asks for review output; nothing in the
    generation result summary may depend on them.
    """

    config: ModelConfig
    source_data: dict[str, Any]
    runtime_contract: dict[str, Any]
    report: dict[str, Any] | None = None
    preview: dict[str, Any] | None = None
    compatibility_source: bool = False
    derivation_manifest: dict[str, Any] | None = None


# Temporary: the only model still exporting the legacy JSON/CSV compatibility
# pair, kept while a current consumer remains (spec Pass 2 requirement 8). It
# selects a secondary OUTPUT, never a source-construction path.
COMPATIBILITY_EXPORT_MODEL_KEYS = frozenset({"stingray"})


def assemble_model_source(config: ModelConfig, *, include_reports: bool = False) -> ModelSourceAssembly:
    """Assemble workbook source rows for one active model.

    One builder serves every workbook-discovered model. There is no model-keyed
    source fork: the payload is built the same way for all six, and all of them
    finalize through ``build_model_runtime_contract``.
    """

    # One frozen snapshot for the whole assembly: every builder reads the same
    # open workbook, and the handle closes deterministically.
    snapshot = load_workbook(config.workbook_path, data_only=True, read_only=True)
    try:
        preview = build_contract_preview(config, wb=snapshot)
        draft = build_form_data_draft(config, preview=preview, wb=snapshot)
        report = inspect_model_sources(config, wb=snapshot) if include_reports else None
    finally:
        snapshot.close()

    return ModelSourceAssembly(
        config=config,
        source_data=draft,
        runtime_contract=build_model_runtime_contract(config, draft),
        report=report,
        preview=preview if include_reports else None,
        compatibility_source=config.model_key in COMPATIBILITY_EXPORT_MODEL_KEYS,
        derivation_manifest=draft.get("_derivationManifest"),
    )
