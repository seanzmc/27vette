"""Shared model generation orchestration.

Pass 6A keeps current source-row assembly engines intact while moving output
orchestration behind one model-neutral entrypoint.
"""

from __future__ import annotations

from typing import Any

from corvette_form_generator.inspection import (
    build_contract_preview,
    build_form_data_draft,
    inspect_model_sources,
    write_contract_preview_artifacts,
    write_form_data_draft_artifacts,
    write_inspection_artifacts,
    write_runtime_contract_artifact,
)
from corvette_form_generator.model_config import ModelConfig
from corvette_form_generator.registry_promotion import export_slug, runtime_contract_artifact_path

TEMPORARY_ROUTE_ENGINES = {"stingray": "production"}
DEFAULT_ROUTE_ENGINE = "inspection_draft"


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


def _runtime_contract_json(config: ModelConfig) -> str:
    return str(runtime_contract_artifact_path(config.root, config.model_key))


def _normalize_production_result(config: ModelConfig, result: dict[str, Any]) -> dict[str, Any]:
    runtime_contract_json = result["runtime_contract_json"]
    normalized = {
        **result,
        "model_key": config.model_key,
        "model_label": config.model_label,
        "route_engine": "production",
        "runtime_contract_json": runtime_contract_json,
        "runtime_contract_artifacts": {"json": runtime_contract_json},
        "compatibility_artifacts": {
            "json": result["json"],
            "csv": result["csv"],
        },
        "inspection_artifacts": {},
        "preview_artifacts": {},
        "draft_artifacts": {},
        "counts": {
            "choices": result["choices"],
            "context_choices": result["context_choices"],
            "standard_equipment": result["standard_equipment"],
            "rules": result["rules"],
            "price_rules": result["price_rules"],
            "interiors": result["interiors"],
        },
        "notes": list(config.notes),
    }
    return normalized


def _generate_production(config: ModelConfig) -> dict[str, Any]:
    from corvette_form_generator import production

    return _normalize_production_result(config, production.generate_production_artifacts(config))


def _generate_inspection_draft(config: ModelConfig) -> dict[str, Any]:
    slug = export_slug(config.model_key)
    inspection_prefix = f"{slug}-inspection"
    rule_audit_path = config.output_dir / "inspection" / f"{slug}-rule-audit.json"
    rule_audit_markdown_path = config.output_dir / "inspection" / f"{slug}-rule-audit.md"
    rule_audit_artifacts = {}
    if rule_audit_path.exists():
        rule_audit_artifacts["json"] = str(rule_audit_path)
    if rule_audit_markdown_path.exists():
        rule_audit_artifacts["markdown"] = str(rule_audit_markdown_path)

    report = inspect_model_sources(config)
    inspection_artifacts = write_inspection_artifacts(report, config.output_dir / "inspection", inspection_prefix)
    preview = build_contract_preview(config)
    preview_artifacts = write_contract_preview_artifacts(
        preview,
        config.output_dir / "inspection",
        config.preview_artifact_prefix,
    )
    draft = build_form_data_draft(config, preview=preview)
    draft_artifacts = write_form_data_draft_artifacts(
        draft,
        config.output_dir / "inspection",
        config.draft_artifact_prefix,
    )
    runtime_contract_artifacts = write_runtime_contract_artifact(
        config,
        draft,
        runtime_contract_artifact_path(config.root, config.model_key).parent,
        runtime_contract_artifact_path(config.root, config.model_key).stem,
    )
    runtime_contract_json = runtime_contract_artifacts["json"]

    validation_errors = _validation_error_count(draft.get("validation", []))
    return {
        "model_key": config.model_key,
        "model_label": config.model_label,
        "model_year": config.model_year,
        "route_engine": "inspection_draft",
        "status": report["status"],
        "source_option_sheet": config.source_option_sheet,
        "variant_ids": list(config.variant_ids),
        "expected_variant_count": config.expected_variant_count,
        "counts": report["counts"],
        "blank_section_overrides": dict(config.blank_section_overrides),
        "warnings": report["warnings"],
        "runtime_contract_json": runtime_contract_json,
        "runtime_contract_artifacts": runtime_contract_artifacts,
        "compatibility_artifacts": {},
        "inspection_artifacts": inspection_artifacts,
        "preview": {
            "status": preview["dataset"]["status"],
            "variants": len(preview["variants"]),
            "choices": len(preview["choices"]),
            "candidate_standard_equipment": len(preview["candidateStandardEquipment"]),
            "unresolved_issues": len(preview["normalization"]["unresolvedIssues"]),
        },
        "preview_artifacts": preview_artifacts,
        "draft": {
            "status": draft["dataset"]["status"],
            "variants": len(draft["variants"]),
            "choices": len(draft["choices"]),
            "standard_equipment": len(draft["standardEquipment"]),
            "rules": len(draft["rules"]),
            "price_rules": len(draft["priceRules"]),
            "interiors": len(draft["interiors"]),
            "validation_warnings": sum(1 for row in draft["validation"] if row["severity"] == "warning"),
        },
        "draft_artifacts": draft_artifacts,
        "rule_audit_artifacts": rule_audit_artifacts,
        "validation_errors": validation_errors,
        "notes": list(config.notes),
    }


def generate_model_artifacts(config: ModelConfig) -> dict[str, Any]:
    """Generate artifacts for one workbook-discovered active model."""

    route_engine = TEMPORARY_ROUTE_ENGINES.get(config.model_key, DEFAULT_ROUTE_ENGINE)
    if route_engine == "production":
        result = _generate_production(config)
    elif route_engine == "inspection_draft":
        result = _generate_inspection_draft(config)
    else:
        raise ValueError(f"Unknown generation route {route_engine!r} for model {config.model_key!r}")

    missing_keys = [key for key in REQUIRED_RESULT_KEYS if key not in result]
    if missing_keys:
        raise ValueError(f"Generation result for {config.model_key} missing keys: {', '.join(missing_keys)}")
    result["runtime_contract_json"] = result.get("runtime_contract_json") or _runtime_contract_json(config)
    return result
