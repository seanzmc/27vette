"""Pydantic request/response models for the workbook manager API."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ValidationIssue(BaseModel):
    model_key: str = ""
    table_role: str = ""
    sql_table: str = ""
    field: str = ""
    entity_key: str = ""
    message: str
    dependents: Optional[list[dict]] = None


class StageChangeRequest(BaseModel):
    model_key: str = ""
    table_role: str = ""
    model_id: str = ""
    table: str = ""
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
    model_id: str = ""
    table: str = ""
    table_name: str = ""
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
    workbook_path: str


class FindingOut(BaseModel):
    severity: str
    status: str = ""
    code: str
    message: str
    source_sheet: str = ""
    source_row: Optional[int] = None
    source_column: str = ""
    model_key: str = ""
    sql_table: str = ""
    entity_key: str = ""
    value: Any = None


class ImportReportOut(BaseModel):
    status: Literal["validated", "decision_required", "contract_mismatch"]
    live_models: list[str]
    findings: list[FindingOut]
    decision_required: list[FindingOut]
    contract_differences: list[FindingOut]
    candidate_path: Optional[str] = None
    promoted_path: Optional[str] = None


class ImportRunOut(BaseModel):
    id: int
    ts: str
    workbook_path: str
    workbook_mtime_ns: str
    workbook_sha256: str
    status: str
    row_counts: dict[str, Any] = Field(default_factory=dict)
    issue_counts: dict[str, Any] = Field(default_factory=dict)


class FindingsOut(BaseModel):
    import_run_id: int
    findings: list[FindingOut]


class SchemaMappingOut(BaseModel):
    id: int
    source_sheet: str
    source_column: str
    model_key: Optional[str] = None
    source_role: str = ""
    sql_table: str
    sql_column: str
    transform_type: str
    transform_parameters: dict[str, Any] = Field(default_factory=dict)
    contract_status: str
    notes: str = ""


class SchemaMappingsOut(BaseModel):
    mappings: list[SchemaMappingOut]


class ModelTableOut(BaseModel):
    model_key: str
    role: str
    sql_table: str
    source_sheets: list[str]
    source_filter: str = ""
    mapping_type: str
    active: bool
    count: int
    key: list[str]
    editable: bool = True


class ModelTablesOut(BaseModel):
    model_key: str
    tables: list[ModelTableOut]


class ModelTableRecordsOut(BaseModel):
    model_key: str
    table_role: str
    sql_table: str
    source_sheets: list[str]
    source_filter: str = ""
    mapping_type: str
    key: list[str]
    total: int
    records: list[dict[str, Any]]


class ModelVariantsOut(BaseModel):
    model_key: str
    variants: list[dict[str, Any]]


class ModelRuntimeOut(BaseModel):
    model_key: str
    steps: list[dict[str, Any]]
    section_presentation: list[dict[str, Any]]
    context_sections: list[dict[str, Any]]
    context_choices: list[dict[str, Any]]
    summary_sections: list[dict[str, Any]]
    step_summary_map: list[dict[str, Any]]


class ChangeListOut(BaseModel):
    changes: list[dict[str, Any]]


class ValidationOut(BaseModel):
    ok: bool
    errors: list[dict[str, Any]] = Field(default_factory=list)
    results: list[dict[str, Any]] = Field(default_factory=list)


class CommitOut(BaseModel):
    ok: bool
    status: str
    committed: int = 0
    errors: list[Any] = Field(default_factory=list)
    validation: Optional[dict[str, Any]] = None


class HistoryOut(BaseModel):
    total: int
    history: list[dict[str, Any]]


class OperationOut(BaseModel):
    model_config = ConfigDict(extra="allow")

    ok: bool
    status: str = ""
    path: str = ""
    errors: list[Any] = Field(default_factory=list)
