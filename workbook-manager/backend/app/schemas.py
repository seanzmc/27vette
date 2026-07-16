"""Pydantic request/response models for the workbook manager API."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ValidationIssue(BaseModel):
    model_key: str = ""
    table_role: str = ""
    sql_table: str = ""
    field: str = ""
    entity_key: str = ""
    message: str
    dependents: Optional[list[dict]] = None


class StageChangeRequest(BaseModel):
    model_key: str
    table_role: str
    op: str = Field(pattern="^(add|update|delete)$")
    key: dict[str, str] = Field(default_factory=dict)
    record: Optional[dict[str, Any]] = None
    session_id: str = ""
    confirm_dependencies: bool = False


class ChangeOut(BaseModel):
    id: int
    ts: str
    session_id: str
    model_key: str
    table_role: str
    sql_table: str
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
    confirm: str = ""  # must equal "SYNC" for live writes


class ColumnOut(BaseModel):
    name: str
    header: str
    label: str
    ctype: str
    enum: list[str] = Field(default_factory=list)
    is_key: bool = False
    ref: Optional[dict] = None


class TableSchemaOut(BaseModel):
    table: str
    label: str
    key: list[str]
    model_scoped: bool
    editable: bool
    sheet_for_model: Optional[str] = None
    columns: list[ColumnOut]
    id_prefixes: list[str] = Field(default_factory=list)


class ImportRequest(BaseModel):
    pass
