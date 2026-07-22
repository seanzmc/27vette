#!/usr/bin/env python3
"""Workbook domain package: declarative workbook registry metadata."""

from __future__ import annotations

from corvette_form_generator.workbook_domain.changeset import (
    ChangeSetError,
    canonical_json,
    changeset_fingerprint,
    changeset_to_editor_batch,
    parse_changeset,
)
from corvette_form_generator.workbook_domain.deployment_proof import (
    prove_changeset_deployment,
)
from corvette_form_generator.workbook_domain.registry import (
    EDITOR_SHEET_META,
    GLOBAL_SHEET_FAMILIES,
    SOURCE_ROLE_FAMILIES,
    family_spec,
    registered_sheet_families,
)
from corvette_form_generator.workbook_domain.service import (
    apply_changeset,
    approve_changeset,
    preview_changeset,
)

__all__ = [
    "ChangeSetError",
    "EDITOR_SHEET_META",
    "GLOBAL_SHEET_FAMILIES",
    "SOURCE_ROLE_FAMILIES",
    "apply_changeset",
    "approve_changeset",
    "canonical_json",
    "changeset_fingerprint",
    "changeset_to_editor_batch",
    "family_spec",
    "parse_changeset",
    "prove_changeset_deployment",
    "preview_changeset",
    "registered_sheet_families",
]
