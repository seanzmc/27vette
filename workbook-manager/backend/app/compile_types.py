"""Immutable value types shared by workbook compilation stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Literal, Mapping


def _empty_mapping() -> Mapping[str, object]:
    return MappingProxyType({})


class DecisionRequired(ValueError):
    """Hard stop for workbook evidence that cannot be compiled safely."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        source_sheet: str = "",
        source_row: int | None = None,
        source_column: str = "",
        value: object = None,
    ) -> None:
        super().__init__(f"decision_required:{code}: {message}")
        self.code = code
        self.source_sheet = source_sheet
        self.source_row = source_row
        self.source_column = source_column
        self.value = value


@dataclass(frozen=True)
class CompiledRow:
    values: Mapping[str, object]
    source_sheet: str
    source_row: int
    lineage_role: str = "direct"
    mapping_parameters: Mapping[str, object] = field(default_factory=_empty_mapping)


@dataclass(frozen=True)
class CompiledTable:
    name: str
    primary_key: tuple[str, ...]
    rows: tuple[CompiledRow, ...]
    model_key: str = ""
    role: str = ""


@dataclass(frozen=True)
class Finding:
    severity: Literal["info", "warning", "error"]
    status: Literal["mapped", "contract_mismatch", "decision_required"]
    code: str
    message: str
    source_sheet: str = ""
    source_row: int | None = None
    source_column: str = ""
    model_key: str = ""
    value: object = None


@dataclass(frozen=True)
class SchemaMapping:
    source_sheet: str
    source_column: str
    destination_table: str
    destination_column: str
    model_key: str = ""
    transform: str = "identity"
    reverse_transform: str = "identity"


@dataclass(frozen=True)
class LineageEntry:
    destination_table: str
    destination_key: Mapping[str, object]
    source_sheet: str
    source_row: int
    mapping_role: Literal["direct", "shared_source_split", "normalized"]


@dataclass(frozen=True)
class SourceSheet:
    source_sheet: str
    disposition: str
    headers: tuple[str, ...]
    row_count: int
    destination_tables: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class WorkbookProfile:
    workbook_path: Path
    workbook_sha256: str
    sheets: tuple[SourceSheet, ...]
    active_models: tuple[str, ...]
    active_sources: Mapping[str, Mapping[str, str]]
    findings: tuple[Finding, ...]
