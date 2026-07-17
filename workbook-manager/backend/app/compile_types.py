"""Immutable value types shared by workbook compilation stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Collection, Literal, Mapping


CONTRACT_STATUSES = (
    "exact",
    "identifier_normalized",
    "shared_source_split",
    "semantic_alias",
    "derived_from_contract",
    "contract_mismatch",
    "decision_required",
)


def _empty_mapping() -> Mapping[str, object]:
    return MappingProxyType({})


def freeze_value(value: object) -> object:
    """Recursively freeze compiler evidence into immutable containers."""
    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: freeze_value(item) for key, item in value.items()}
        )
    if isinstance(value, tuple):
        return tuple(freeze_value(item) for item in value)
    if isinstance(value, list):
        return tuple(freeze_value(item) for item in value)
    if isinstance(value, set):
        return frozenset(freeze_value(item) for item in value)
    return value


def freeze_mapping(value: Mapping[str, object]) -> Mapping[str, object]:
    frozen = freeze_value(value)
    assert isinstance(frozen, Mapping)
    return frozen


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
    schema_mappings: tuple["SchemaMapping", ...] = ()


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
    source_role: str = ""
    transform: str = "identity"
    reverse_transform: str = "identity"
    transform_parameters: Mapping[str, object] = field(
        default_factory=_empty_mapping
    )
    contract_status: str = "exact"
    notes: str = ""

    def __post_init__(self) -> None:
        if self.contract_status not in CONTRACT_STATUSES:
            raise ValueError(
                f"unsupported schema mapping status {self.contract_status!r}"
            )
        object.__setattr__(
            self,
            "transform_parameters",
            freeze_mapping(self.transform_parameters),
        )


@dataclass(frozen=True)
class LineageEntry:
    destination_table: str
    destination_key: Mapping[str, object]
    source_sheet: str
    source_row: int
    mapping_role: Literal["direct", "shared_source_split", "normalized"]


@dataclass(frozen=True)
class SourceRowInventory:
    source_row: int
    values: Mapping[str, object]
    disposition: str = "emission_required"
    reason: str = "Canonical source row must emit lineage or be classified."
    evidence: Mapping[str, object] = field(default_factory=_empty_mapping)


@dataclass(frozen=True)
class SourceSheet:
    source_sheet: str
    disposition: str
    headers: tuple[str, ...]
    row_count: int
    destination_tables: tuple[str, ...]
    reason: str
    rows: tuple[SourceRowInventory, ...] = ()


@dataclass(frozen=True)
class WorkbookProfile:
    workbook_path: Path
    workbook_sha256: str
    sheets: tuple[SourceSheet, ...]
    known_models: tuple[str, ...]
    active_models: tuple[str, ...]
    inactive_models: tuple[str, ...]
    active_sources: Mapping[str, Mapping[str, str]]
    findings: tuple[Finding, ...]


def finding_blocks_destinations(
    finding: Finding,
    profile: WorkbookProfile,
    destination_tables: Collection[str],
) -> bool:
    """Return whether a profile finding must stop a destination-owned stage."""
    blocking = (
        finding.severity == "error"
        or finding.status in {"decision_required", "contract_mismatch"}
    )
    if not blocking:
        return False
    if finding.code != "unknown_model_row_requires_decision":
        return True
    source = next(
        (
            sheet
            for sheet in profile.sheets
            if sheet.source_sheet == finding.source_sheet
        ),
        None,
    )
    if source is None or source.disposition not in {
        "canonical_direct",
        "canonical_split",
    }:
        return True
    return bool(set(source.destination_tables) & set(destination_tables))
