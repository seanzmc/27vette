"""Model configuration contracts for Corvette form generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class ModelConfig:
    model_key: str
    model_label: str
    model_year: str
    dataset_name: str
    source_option_sheet: str
    variant_ids: tuple[str, ...]
    expected_variant_count: int
    root: Path
    workbook_path: Path
    output_dir: Path
    app_dir: Path
    interior_reference_path: Path
    generated_sheets: tuple[str, ...]
    step_order: tuple[str, ...]
    step_labels: Mapping[str, str]
    context_sections: tuple[Mapping[str, Any], ...]
    body_style_display_order: Mapping[str, int]
    selection_mode_labels: Mapping[str, str]
    standard_sections: frozenset[str]
    section_step_overrides: Mapping[str, str]
    blank_section_overrides: Mapping[str, str] = field(default_factory=dict)
    section_category_overrides: Mapping[str, str] = field(default_factory=dict)
    option_category_overrides: Mapping[str, str] = field(default_factory=dict)
    section_label_overrides: Mapping[str, str] = field(default_factory=dict)
    preview_artifact_prefix: str = ""
    draft_artifact_prefix: str = ""
    text_cleanup: Mapping[str, Any] = field(default_factory=dict)
    special_rule_review_rpos: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
