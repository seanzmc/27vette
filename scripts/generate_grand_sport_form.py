#!/usr/bin/env python3
"""Read-only scaffold for future Grand Sport form generation."""

from __future__ import annotations

import json

from corvette_form_generator.inspection import (
    build_contract_preview,
    build_form_data_draft,
    inspect_model_sources,
    write_contract_preview_artifacts,
    write_form_data_draft_artifacts,
    write_inspection_artifacts,
)
from corvette_form_generator.model_configs import GRAND_SPORT_MODEL


def main() -> None:
    config = GRAND_SPORT_MODEL
    rule_audit_path = config.output_dir / "inspection" / "grand-sport-rule-audit.json"
    rule_audit_markdown_path = config.output_dir / "inspection" / "grand-sport-rule-audit.md"
    rule_audit_artifacts = {}
    if rule_audit_path.exists():
        rule_audit_artifacts["json"] = str(rule_audit_path)
    if rule_audit_markdown_path.exists():
        rule_audit_artifacts["markdown"] = str(rule_audit_markdown_path)
    report = inspect_model_sources(config)
    artifact_paths = write_inspection_artifacts(report, config.output_dir / "inspection")
    preview = build_contract_preview(config)
    preview_artifact_paths = write_contract_preview_artifacts(
        preview,
        config.output_dir / "inspection",
        config.preview_artifact_prefix,
    )
    draft = build_form_data_draft(config)
    draft_artifact_paths = write_form_data_draft_artifacts(
        draft,
        config.output_dir / "inspection",
        config.draft_artifact_prefix,
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
                    "interiors": len(draft["interiors"]),
                    "validation_warnings": sum(1 for row in draft["validation"] if row["severity"] == "warning"),
                },
                "draft_artifacts": draft_artifact_paths,
                "rule_audit_artifacts": rule_audit_artifacts,
                "notes": list(config.notes),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
