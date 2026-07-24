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
from corvette_form_generator.runtime_contract import assert_runtime_contract
from corvette_form_generator.source_assembly import ModelSourceAssembly, assemble_model_source
from corvette_form_generator.validation import validation_error_count

ROUTE_ENGINE = "source_assembly"


@dataclass(frozen=True)
class GenerationOptions:
    """Controls optional generated review artifacts without changing source assembly."""

    emit_inspection: bool = False
    inspection_output_dir: Path | None = None


REQUIRED_RESULT_KEYS = (
    "model_key",
    "model_label",
    "route_engine",
    "runtime_contract_json",
    "runtime_contract_artifacts",
    "compatibility_artifacts",
    "inspection_artifacts",
    "preview_artifacts",
    "draft_artifacts",
    "counts",
    "validation_errors",
    "notes",
)


def _validation_error_count(rows: list[dict[str, Any]]) -> int:
    return sum(1 for row in rows if row.get("severity") == "error")


def _runtime_contract_path(config: ModelConfig) -> Path:
    return config.output_dir / "runtime" / f"{export_slug(config.model_key)}-runtime-contract.json"


def _runtime_contract_json(config: ModelConfig) -> str:
    return str(_runtime_contract_path(config))


def _inspection_output_dir(config: ModelConfig, options: GenerationOptions) -> Path:
    return options.inspection_output_dir or config.output_dir / "inspection"


def _write_runtime_contract_artifact(config: ModelConfig, runtime_contract: dict[str, Any]) -> dict[str, str]:
    runtime_json_path = _runtime_contract_path(config)
    runtime_json_path.parent.mkdir(parents=True, exist_ok=True)
    write_json_output(runtime_json_path, runtime_contract)
    return {"json": str(runtime_json_path)}


def _inspection_artifact_prefix(config: ModelConfig) -> str:
    return f"{export_slug(config.model_key)}-inspection"


def _compatibility_result(config: ModelConfig, assembly: ModelSourceAssembly) -> dict[str, Any]:
    compatibility_artifacts = write_stingray_compatibility_artifacts(
        config,
        assembly.source_data,
        assembly.runtime_contract,
    )
    runtime_contract_artifacts = _write_runtime_contract_artifact(config, assembly.runtime_contract)
    runtime_contract_json = runtime_contract_artifacts["json"]
    return {
        "workbook": str(config.workbook_path),
        "workbook_backup": None,
        "json": compatibility_artifacts["json"],
        "runtime_contract_json": runtime_contract_json,
        "csv": compatibility_artifacts["csv"],
        "choices": len(assembly.source_data["choices"]),
        "context_choices": len(assembly.source_data["contextChoices"]),
        "standard_equipment": len(assembly.source_data["standardEquipment"]),
        "rules": len(assembly.source_data["rules"]),
        "price_rules": len(assembly.source_data["priceRules"]),
        "interiors": len(assembly.source_data["interiors"]),
        "validation_errors": validation_error_count(assembly.source_data["validation"]),
        "model_key": config.model_key,
        "model_label": config.model_label,
        "route_engine": ROUTE_ENGINE,
        "runtime_contract_artifacts": runtime_contract_artifacts,
        "compatibility_artifacts": compatibility_artifacts,
        "inspection_artifacts": {},
        "preview_artifacts": {},
        "draft_artifacts": {},
        "counts": {
            "choices": len(assembly.source_data["choices"]),
            "context_choices": len(assembly.source_data["contextChoices"]),
            "standard_equipment": len(assembly.source_data["standardEquipment"]),
            "rules": len(assembly.source_data["rules"]),
            "price_rules": len(assembly.source_data["priceRules"]),
            "interiors": len(assembly.source_data["interiors"]),
        },
        "notes": list(config.notes),
    }


def _reviewable_result(config: ModelConfig, assembly: ModelSourceAssembly, options: GenerationOptions) -> dict[str, Any]:
    if assembly.report is None or assembly.preview is None or assembly.draft is None:
        raise ValueError(f"{config.model_key} source assembly has no review payloads")

    inspection_output_dir = _inspection_output_dir(config, options)
    inspection_artifacts = {}
    if options.emit_inspection:
        inspection_artifacts = write_inspection_artifacts(
            assembly.report,
            inspection_output_dir,
            _inspection_artifact_prefix(config),
        )
    preview_artifacts = {}
    if options.emit_inspection:
        preview_artifacts = write_contract_preview_artifacts(
            assembly.preview,
            inspection_output_dir,
            config.preview_artifact_prefix,
        )
    draft_artifacts = {}
    if options.emit_inspection:
        draft_artifacts = write_form_data_draft_artifacts(
            assembly.draft,
            inspection_output_dir,
            config.draft_artifact_prefix,
        )
    runtime_contract_artifacts = _write_runtime_contract_artifact(config, assembly.runtime_contract)
    runtime_contract_json = runtime_contract_artifacts["json"]

    validation_errors = _validation_error_count(assembly.draft.get("validation", []))
    return {
        "model_key": config.model_key,
        "model_label": config.model_label,
        "model_year": config.model_year,
        "route_engine": ROUTE_ENGINE,
        "status": assembly.report["status"],
        "source_option_sheet": config.source_option_sheet,
        "variant_ids": list(config.variant_ids),
        "expected_variant_count": config.expected_variant_count,
        "counts": assembly.report["counts"],
        "blank_section_overrides": dict(config.blank_section_overrides),
        "warnings": assembly.report["warnings"],
        "runtime_contract_json": runtime_contract_json,
        "runtime_contract_artifacts": runtime_contract_artifacts,
        "compatibility_artifacts": {},
        "inspection_artifacts": inspection_artifacts,
        "preview": {
            "status": assembly.preview["dataset"]["status"],
            "variants": len(assembly.preview["variants"]),
            "choices": len(assembly.preview["choices"]),
            "candidate_standard_equipment": len(assembly.preview["candidateStandardEquipment"]),
            "unresolved_issues": len(assembly.preview["normalization"]["unresolvedIssues"]),
        },
        "preview_artifacts": preview_artifacts,
        "draft": {
            "status": assembly.draft["dataset"]["status"],
            "variants": len(assembly.draft["variants"]),
            "choices": len(assembly.draft["choices"]),
            "standard_equipment": len(assembly.draft["standardEquipment"]),
            "rules": len(assembly.draft["rules"]),
            "price_rules": len(assembly.draft["priceRules"]),
            "interiors": len(assembly.draft["interiors"]),
            "validation_warnings": sum(1 for row in assembly.draft["validation"] if row["severity"] == "warning"),
        },
        "draft_artifacts": draft_artifacts,
        "validation_errors": validation_errors,
        "notes": list(config.notes),
    }


def generate_model_artifacts(config: ModelConfig, *, options: GenerationOptions | None = None) -> dict[str, Any]:
    """Generate artifacts for one workbook-discovered active model."""

    export_slug(config.model_key)
    resolved_options = options or GenerationOptions()
    assembly = assemble_model_source(config)
    assert_runtime_contract(
        assembly.runtime_contract,
        source=f"generated {config.model_key}",
        config=config,
    )
    if assembly.derivation_manifest is not None:
        write_derivation_manifest(config.output_dir, config.model_key, assembly.derivation_manifest)
    if assembly.compatibility_source:
        result = _compatibility_result(config, assembly)
    else:
        result = _reviewable_result(config, assembly, resolved_options)

    missing_keys = [key for key in REQUIRED_RESULT_KEYS if key not in result]
    if missing_keys:
        raise ValueError(f"Generation result for {config.model_key} missing keys: {', '.join(missing_keys)}")
    result["runtime_contract_json"] = result.get("runtime_contract_json") or _runtime_contract_json(config)
    return result
