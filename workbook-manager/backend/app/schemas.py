"""Pydantic request/response models for the workbook manager API."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ValidationIssue(BaseModel):
    table: str = ""
    model_id: str = ""
    field: str = ""
    entity_key: str = ""
    message: str
    dependents: Optional[list[dict]] = None


class StageChangeRequest(BaseModel):
    table: str
    model_id: str = ""
    op: str = Field(pattern="^(add|update|delete)$")
    key: dict[str, str] = Field(default_factory=dict)
    record: Optional[dict[str, Any]] = None
    session_id: str = ""



class DraftOperationRequest(BaseModel):
    table: str
    model_id: str = ""
    op: str = Field(pattern="^(add|update|delete)$")
    key: dict[str, str] = Field(default_factory=dict)
    record: Optional[dict[str, Any]] = None
    session_id: str = ""
    actor: str = ""


class ApprovalRequest(BaseModel):
    actor: str = ""
    warning_ids: list[str] = Field(default_factory=list)


class ApplyRebuildRequest(BaseModel):
    actor: str = ""
    confirm: str


class ManualResolutionRequest(BaseModel):
    actor: str
    resolution: str = Field(pattern="^(restored|applied|abandoned_unknown)$")
    evidence: dict[str, Any] = Field(default_factory=dict)


class AssetResolutionRequest(BaseModel):
    item_id: str
    resolution_kind: str = Field(
        pattern="^(accept_safe|select_candidate|inventory_match|manual_url|assign_media|edit|deactivate|ignore)$"
    )
    fingerprints: dict[str, str]
    selected_url: str = ""
    target_item_id: str = ""
    values: dict[str, Any] = Field(default_factory=dict)
    session_id: str = ""
    actor: str = ""


class AssetSafeBulkRequest(BaseModel):
    fingerprints: dict[str, str]
    session_id: str = ""
    actor: str = ""


class ChangeOut(BaseModel):
    id: int
    ts: str
    session_id: str
    table_name: str
    model_id: str
    op: str
    status: str
    entity_key: Optional[dict] = None
    old: Optional[dict] = None
    new: Optional[dict] = None
    validation: Optional[dict] = None
    confirmed_dependencies: int = 0


class CommitRequest(BaseModel):
    actor: str = ""


class SyncRequest(BaseModel):
    write: bool = False
    confirmed_warnings: list[str] = Field(default_factory=list)
    expected_mtime_ns: Optional[str] = None
    confirm: str = ""  # legacy payload field; provisional API writes are refused


class ColumnOut(BaseModel):
    name: str
    header: str
    label: str
    ctype: str
    enum: list[str] = Field(default_factory=list)
    is_key: bool = False
    optional: bool = False
    required_on_add: bool = False
    required_on_effective_active_row: bool = False
    field_kind: str
    finite_values: list[str] = Field(default_factory=list)
    reference: Optional[dict] = None
    ref: Optional[dict] = None


class TableSchemaOut(BaseModel):
    table: str
    label: str
    key: list[str]
    model_scoped: bool
    model_context: dict
    editable: bool
    sheet_for_model: Optional[str] = None
    columns: list[ColumnOut]
    id_prefixes: list[str] = Field(default_factory=list)


class ImportRequest(BaseModel):
    pass
