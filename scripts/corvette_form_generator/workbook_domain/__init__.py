#!/usr/bin/env python3
"""Workbook domain package: declarative workbook registry metadata."""

from __future__ import annotations

from corvette_form_generator.workbook_domain.registry import (
    EDITOR_SHEET_META,
    GLOBAL_SHEET_FAMILIES,
    SOURCE_ROLE_FAMILIES,
    family_spec,
    registered_sheet_families,
)

__all__ = [
    "EDITOR_SHEET_META",
    "GLOBAL_SHEET_FAMILIES",
    "SOURCE_ROLE_FAMILIES",
    "family_spec",
    "registered_sheet_families",
]
