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
from corvette_form_generator.model_configs import discover_generation_model_configs
from corvette_form_generator.registry_promotion import export_slug, runtime_contract_artifact_path

PRODUCTION_MODEL_KEYS = {"stingray"}


def run_production(base_config: ModelConfig) -> None:
    from corvette_form_generator import production

    production.main()


def run_draft(base_config: ModelConfig) -> None:
    config = base_config
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
    artifact_paths = write_inspection_artifacts(report, config.output_dir / "inspection", inspection_prefix)
    preview = build_contract_preview(config)
    preview_artifact_paths = write_contract_preview_artifacts(
        preview,
        config.output_dir / "inspection",
        config.preview_artifact_prefix,
    )
    draft = build_form_data_draft(config, preview=preview)
    draft_artifact_paths = write_form_data_draft_artifacts(
        draft,
        config.output_dir / "inspection",
        config.draft_artifact_prefix,
    )
    runtime_contract_paths = write_runtime_contract_artifact(
        config,
        draft,
        runtime_contract_artifact_path(config.root, config.model_key).parent,
        runtime_contract_artifact_path(config.root, config.model_key).stem,
    )
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
                "inspection_artifacts": artifact_paths,
                "preview": {
                    "status": preview["dataset"]["status"],
                    "variants": len(preview["variants"]),
                    "choices": len(preview["choices"]),
                    "candidate_standard_equipment": len(preview["candidateStandardEquipment"]),
                    "unresolved_issues": len(preview["normalization"]["unresolvedIssues"]),
                },
                "preview_artifacts": preview_artifact_paths,
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
                "draft_artifacts": draft_artifact_paths,
                "runtime_contract_artifacts": runtime_contract_paths,
                "rule_audit_artifacts": rule_audit_artifacts,
                "notes": list(config.notes),
            },
            indent=2,
        )
    )


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
    if args.model in PRODUCTION_MODEL_KEYS:
        run_production(base_config)
    else:
        run_draft(base_config)


if __name__ == "__main__":
    main()
