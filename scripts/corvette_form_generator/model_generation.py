"""Shared model generation orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from corvette_form_generator.inspection import (
    write_contract_preview_artifacts,
    write_form_data_draft_artifacts,
    write_inspection_artifacts,
)
from corvette_form_generator.model_config import ModelConfig
from corvette_form_generator.output import write_json_output
from corvette_form_generator.production import write_stingray_compatibility_artifacts
from corvette_form_generator.registry_promotion import export_slug
from corvette_form_generator.rule_derivation import write_derivation_manifest
from corvette_form_generator.runtime_contract import (
    REQUIRED_RUNTIME_LIST_FIELDS,
    assert_runtime_contract,
    validation_severity_count,
)
from corvette_form_generator.source_assembly import ModelSourceAssembly, assemble_model_source

ROUTE_ENGINE = "source_assembly"


@dataclass(frozen=True)
class GenerationOptions:
    """Controls optional generated review artifacts without changing source assembly."""

    emit_inspection: bool = False
    inspection_output_dir: Path | None = None


# The published summary contract. Asserted in tests/test_model_generation_route.py;
# `_summary_from_runtime_contract` supplies every key unconditionally.
REQUIRED_RESULT_KEYS = (
    "model_key",
    "model_label",
    "model_year",
    "route_engine",
    "status",
    "dataset_name",
    "workbook",
    "source_option_sheet",
    "variant_ids",
    "expected_variant_count",
    "runtime_contract_json",
    "runtime_contract_artifacts",
    "compatibility_artifacts",
    "inspection_artifacts",
    "preview_artifacts",
    "draft_artifacts",
    "counts",
    "validation_errors",
    "validation_warnings",
    "notes",
)


def _runtime_contract_path(config: ModelConfig) -> Path:
    return config.output_dir / "runtime" / f"{export_slug(config.model_key)}-runtime-contract.json"


def _inspection_output_dir(config: ModelConfig, options: GenerationOptions) -> Path:
    return options.inspection_output_dir or config.output_dir / "inspection"


def _write_runtime_contract_artifact(config: ModelConfig, runtime_contract: dict[str, Any]) -> dict[str, str]:
    runtime_json_path = _runtime_contract_path(config)
    runtime_json_path.parent.mkdir(parents=True, exist_ok=True)
    write_json_output(runtime_json_path, runtime_contract)
    return {"json": str(runtime_json_path)}


def _inspection_artifact_prefix(config: ModelConfig) -> str:
    return f"{export_slug(config.model_key)}-inspection"


def _write_review_artifacts(
    config: ModelConfig,
    assembly: ModelSourceAssembly,
    options: GenerationOptions,
) -> dict[str, dict[str, str]]:
    """Write the optional review artifacts from payloads already held in memory."""

    empty: dict[str, dict[str, str]] = {
        "inspection_artifacts": {},
        "preview_artifacts": {},
        "draft_artifacts": {},
    }
    if not options.emit_inspection or assembly.compatibility_source:
        return empty
    if assembly.report is None or assembly.preview is None:
        raise ValueError(f"{config.model_key} review output was requested without review payloads")

    output_dir = _inspection_output_dir(config, options)
    return {
        "inspection_artifacts": write_inspection_artifacts(
            assembly.report,
            output_dir,
            _inspection_artifact_prefix(config),
        ),
        "preview_artifacts": write_contract_preview_artifacts(
            assembly.preview,
            output_dir,
            config.preview_artifact_prefix,
        ),
        "draft_artifacts": write_form_data_draft_artifacts(
            assembly.source_data,
            output_dir,
            config.draft_artifact_prefix,
        ),
    }


def _summary_from_runtime_contract(
    config: ModelConfig,
    runtime_contract: dict[str, Any],
    artifacts: dict[str, Any],
) -> dict[str, Any]:
    """Describe the run from the validated contract, not from review payloads.

    Every model reports the same shape. Counts are the published collections'
    own lengths, so the summary cannot disagree with the artifact it describes.
    """

    dataset = runtime_contract["dataset"]
    validation = runtime_contract.get("validation")
    return {
        "model_key": config.model_key,
        "model_label": config.model_label,
        "model_year": config.model_year,
        "route_engine": ROUTE_ENGINE,
        "status": dataset["status"],
        "dataset_name": dataset["name"],
        "workbook": str(config.workbook_path),
        "source_option_sheet": config.source_option_sheet,
        "variant_ids": list(config.variant_ids),
        "expected_variant_count": config.expected_variant_count,
        "counts": {field: len(runtime_contract.get(field) or []) for field in REQUIRED_RUNTIME_LIST_FIELDS},
        "validation_errors": validation_severity_count(validation, "error"),
        "validation_warnings": validation_severity_count(validation, "warning"),
        "notes": list(config.notes),
        **artifacts,
    }


def generate_model_artifacts(config: ModelConfig, *, options: GenerationOptions | None = None) -> dict[str, Any]:
    """Generate artifacts for one workbook-discovered active model."""

    export_slug(config.model_key)
    resolved_options = options or GenerationOptions()
    assembly = assemble_model_source(config, include_reports=resolved_options.emit_inspection)
    runtime_contract = assembly.runtime_contract
    assert_runtime_contract(
        runtime_contract,
        source=f"generated {config.model_key}",
        config=config,
    )
    if assembly.derivation_manifest is not None:
        write_derivation_manifest(config.output_dir, config.model_key, assembly.derivation_manifest)

    compatibility_artifacts: dict[str, str] = {}
    if assembly.compatibility_source:
        compatibility_artifacts = write_stingray_compatibility_artifacts(
            config,
            assembly.source_data,
            runtime_contract,
        )
    runtime_contract_artifacts = _write_runtime_contract_artifact(config, runtime_contract)

    return _summary_from_runtime_contract(
        config,
        runtime_contract,
        {
            "runtime_contract_json": runtime_contract_artifacts["json"],
            "runtime_contract_artifacts": runtime_contract_artifacts,
            "compatibility_artifacts": compatibility_artifacts,
            **_write_review_artifacts(config, assembly, resolved_options),
        },
    )
