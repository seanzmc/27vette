"""Model configuration contracts for Corvette form generation."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
import re
from typing import Any, Mapping


def validate_model_key(model_key: str) -> str:
    """Return a path-safe model key or fail before any artifact I/O."""

    if re.fullmatch(r"[a-z][a-z0-9_]*", model_key) is None:
        raise ValueError(f"Invalid model_key {model_key!r}; expected lowercase letters, digits, and underscores")
    return model_key


@dataclass(frozen=True)
class ModelConfig:
    model_key: str
    model_label: str
    model_year: str
    dataset_name: str
    source_option_sheet: str
    status_sheet: str
    variant_ids: tuple[str, ...]
    expected_variant_count: int
    root: Path
    workbook_path: Path
    output_dir: Path
    app_dir: Path
    # Both remain Python-authored because the workbook has no column for them
    # yet. Measured live, unlike the shadow fields deleted in this pass:
    # selection_mode_labels ships customer-visible copy through
    # sections[].selection_mode_label. Recorded as a workbook-shape gap.
    body_style_display_order: Mapping[str, int]
    selection_mode_labels: Mapping[str, str]
    interior_source_sheet: str = "lt_interiors"
    blank_section_overrides: Mapping[str, str] = field(default_factory=dict)
    preview_artifact_prefix: str = ""
    draft_artifact_prefix: str = ""
    rule_mapping_sheet: str = "rule_mapping"
    price_rules_sheet: str = "price_rules"
    rule_groups_sheet: str = "rule_groups"
    rule_group_members_sheet: str = "rule_group_members"
    exclusive_groups_sheet: str = "exclusive_groups"
    exclusive_group_members_sheet: str = "exclusive_group_members"
    color_overrides_sheet: str = "color_overrides"
    variant_option_overrides_sheet: str = ""
    exclusive_groups: tuple[Mapping[str, Any], ...] = ()
    special_rule_review_rpos: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def with_overrides(self, **changes: Any) -> "ModelConfig":
        """Return a copy with non-None override values applied."""

        clean_changes = {key: value for key, value in changes.items() if value is not None}
        return replace(self, **clean_changes)
