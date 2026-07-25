#!/usr/bin/env python3
"""Workbook domain package: declarative workbook registry metadata."""

from __future__ import annotations

from importlib import import_module

from corvette_form_generator.workbook_domain.changeset import (
    ChangeSetError,
    canonical_json,
    changeset_fingerprint,
    changeset_to_editor_batch,
    parse_changeset,
)
from corvette_form_generator.workbook_domain.registry import (
    EDITOR_SHEET_META,
    GLOBAL_SHEET_FAMILIES,
    SOURCE_ROLE_FAMILIES,
    family_spec,
    registered_sheet_families,
)
_SERVICE_EXPORTS = ("apply_changeset", "approve_changeset", "preview_changeset")


def __getattr__(name: str):
    """Load the guarded write service lazily.

    ``service`` pulls in ``editor_ops`` and ``schema_validation``, both of which
    read this package's registry metadata. Importing it eagerly makes any module
    that only needs registry shape participate in that cycle.
    """

    if name in _SERVICE_EXPORTS or name == "service":
        # import_module, not `from . import service`: the from-import form calls
        # getattr on this package and recurses back into __getattr__.
        service = import_module("corvette_form_generator.workbook_domain.service")
        return service if name == "service" else getattr(service, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

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
    "preview_changeset",
    "registered_sheet_families",
]
