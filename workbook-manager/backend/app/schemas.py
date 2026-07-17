"""Pydantic request/response models for the workbook manager API."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, JsonValue


class DependencyOut(BaseModel):
    model_key: str
    model_id: str = ""
    table_role: str
    table: str = ""
    sql_table: str
    field: str
    entity_key: str
    key: dict[str, JsonValue]
    source_sheet: str
    source_row: Optional[int]
    src_sheet: str = ""
    src_row: Optional[int] = None


class DependenciesRequest(BaseModel):
    key: dict[str, JsonValue] = Field(default_factory=dict)


class DependenciesOut(BaseModel):
    dependents: list[DependencyOut] = Field(default_factory=list)
    count: int


class DestinationEvidenceOut(BaseModel):
    destination_table: str
    destination_key: dict[str, JsonValue]


class ValidationIssue(BaseModel):
    model_key: str
    table_role: str
    sql_table: str
    field: str
    entity_key: str
    message: str
    source_sheet: str
    source_row: Optional[int]
    source_column: str
    code: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    dependents: Optional[list[DependencyOut]] = None
    destinations: Optional[list[DestinationEvidenceOut]] = None


class ValidationErrorDetail(BaseModel):
    errors: list[ValidationIssue]


class ValidationErrorResponse(BaseModel):
    detail: ValidationErrorDetail


class MessageErrorResponse(BaseModel):
    detail: str


class StageChangeRequest(BaseModel):
    model_key: str = ""
    table_role: str = ""
    model_id: str = ""
    table: str = ""
    op: Literal["add", "update", "delete"]
    key: dict[str, JsonValue] = Field(default_factory=dict)
    record: Optional[dict[str, JsonValue]] = None
    session_id: str = ""
    confirm_dependencies: bool = False


class ChangeValidationOut(BaseModel):
    errors: list[ValidationIssue] = Field(default_factory=list)
    dependents: list[DependencyOut] = Field(default_factory=list)


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
    op: Literal["add", "update", "delete"]
    status: str
    entity_key: Optional[dict[str, JsonValue]] = None
    old: Optional[dict[str, JsonValue]] = None
    new: Optional[dict[str, JsonValue]] = None
    validation: Optional[ChangeValidationOut] = None
    confirmed_dependencies: int = 0


class ChangeListOut(BaseModel):
    changes: list[ChangeOut]


class CommitRequest(BaseModel):
    actor: str = ""


class SyncRequest(BaseModel):
    write: bool = False
    confirmed_warnings: list[str] = Field(default_factory=list)
    expected_mtime_ns: Optional[str] = None
    confirm: str = ""


class ColumnOut(BaseModel):
    name: str
    header: str
    label: str
    ctype: str
    enum: list[str] = Field(default_factory=list)
    is_key: bool = False
    nullable: bool = False


class TableSchemaOut(BaseModel):
    model_key: str
    table_role: str
    table: str
    sql_table: str
    label: str
    key: list[str]
    model_scoped: bool
    editable: bool
    sheet: Optional[str] = None
    sheet_for_model: Optional[str] = None
    columns: list[ColumnOut]
    id_prefixes: list[str] = Field(default_factory=list)


class ImportRequest(BaseModel):
    workbook_path: str


class FindingOut(BaseModel):
    severity: str
    status: str
    code: str
    message: str
    source_sheet: str
    source_row: Optional[int]
    source_column: str
    model_key: str = ""
    sql_table: str = ""
    entity_key: str = ""
    value: JsonValue = None


class ImportReportOut(BaseModel):
    status: Literal["validated", "decision_required", "contract_mismatch"]
    live_models: list[str]
    findings: list[FindingOut]
    decision_required: list[FindingOut]
    contract_differences: list[FindingOut]
    candidate_path: Optional[str] = None
    promoted_path: Optional[str] = None


class ImportConflictDetail(BaseModel):
    status: Literal["decision_required", "contract_mismatch"]
    findings: list[FindingOut]


class ImportConflictResponse(BaseModel):
    detail: ImportConflictDetail


class ImportRunOut(BaseModel):
    id: int
    ts: str
    workbook_path: str
    workbook_mtime_ns: str
    workbook_sha256: str
    status: str
    row_counts: dict[str, JsonValue] = Field(default_factory=dict)
    issue_counts: dict[str, JsonValue] = Field(default_factory=dict)


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
    transform_parameters: dict[str, JsonValue] = Field(default_factory=dict)
    contract_status: Literal[
        "exact",
        "identifier_normalized",
        "shared_source_split",
        "semantic_alias",
        "derived_from_contract",
        "contract_mismatch",
        "decision_required",
    ]
    notes: str = ""


class SchemaMappingsOut(BaseModel):
    mappings: list[SchemaMappingOut]


class ModelOut(BaseModel):
    model_key: str
    registry_key: str
    model_label: str
    model_year: Optional[int] = None
    dataset_name: Optional[str] = None
    export_slug: Optional[str] = None
    expected_variant_count: Optional[int] = None
    default_model: str
    active: str
    notes: str
    promoted_to_runtime: str
    promotion_order: Optional[int] = None
    label: str
    scaffold: bool


class ModelsOut(BaseModel):
    models: list[ModelOut]


class ModelTableOut(BaseModel):
    model_key: str
    role: str
    sql_table: str
    source_sheets: list[str]
    source_filter: str = ""
    mapping_type: Literal["exact", "split", "derived"]
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
    records: list[dict[str, JsonValue]]


class VariantOut(BaseModel):
    model_key: str
    variant_id: str
    display_order: int
    active: int
    notes: str
    model_year: int
    trim_level: str
    body_style: str
    display_name: str
    base_price: int


class ModelVariantsOut(BaseModel):
    model_key: str
    variants: list[VariantOut]


class RuntimeStepOut(BaseModel):
    model_key: str
    step_key: str
    step_label: str
    runtime_order: int
    source: str
    active: int
    notes: str


class SectionPresentationOut(BaseModel):
    model_key: str
    section_id: str
    display_label: str
    step_key: str
    display_behavior: Optional[str]
    section_display_order: int
    standard_equipment_bucket: str
    standard_equipment_group_type: str
    auto_added_bucket: str
    active: int
    notes: str


class RuntimeContextSectionOut(BaseModel):
    model_key: str
    context_type: str
    section_id: str
    section_name: str
    selection_mode: str
    choice_mode: str
    is_required: int
    standard_behavior: str
    section_display_order: int
    step_key: str
    step_label: str
    active: int
    notes: str


class RuntimeContextChoiceOut(BaseModel):
    model_key: str
    context_choice_id: str
    context_type: str
    value: str
    label: str
    description: str
    info_tooltip: str
    section_id: str
    step_key: str
    body_style: str
    trim_level: Optional[str]
    variant_id: Optional[str]
    base_price: Optional[int]
    display_order: int
    active: int
    notes: str


class RuntimeSummarySectionOut(BaseModel):
    model_key: str
    section_key: str
    section_label: str
    display_order: int
    active: int
    notes: str


class RuntimeStepSummaryMapOut(BaseModel):
    model_key: str
    step_key: str
    section_key: str
    active: int
    notes: str


class ModelRuntimeOut(BaseModel):
    model_key: str
    steps: list[RuntimeStepOut]
    section_presentation: list[SectionPresentationOut]
    context_sections: list[RuntimeContextSectionOut]
    context_choices: list[RuntimeContextChoiceOut]
    summary_sections: list[RuntimeSummarySectionOut]
    step_summary_map: list[RuntimeStepSummaryMapOut]


class ValidationResultOut(BaseModel):
    change_id: int
    errors: list[ValidationIssue]


class ValidationOut(BaseModel):
    ok: bool
    results: list[ValidationResultOut] = Field(default_factory=list)


class CommitOut(BaseModel):
    ok: Literal[True]
    status: Literal["committed"]
    committed: int
    validation: ValidationOut


class CommitConflictDetail(BaseModel):
    ok: Literal[False]
    status: str
    committed: int
    validation: ValidationOut
    errors: list[str] = Field(default_factory=list)


class CommitConflictResponse(BaseModel):
    detail: CommitConflictDetail


class HistoryEntryOut(BaseModel):
    id: int
    ts: str
    actor: str
    model_key: str
    table_role: str
    sql_table: str
    entity_id: str
    op: str
    old: Optional[dict[str, JsonValue]]
    new: Optional[dict[str, JsonValue]]
    src_sheet: str
    src_row: Optional[int]
    validation_result: str
    status: str
    sync_status: str
    sync_detail: str
    pending_change_id: Optional[int]
    related_history_id: Optional[int]
    model_id: str
    entity_type: str
    table: str


class HistoryOut(BaseModel):
    total: int
    history: list[HistoryEntryOut]


class EditorWarningOut(BaseModel):
    id: str
    message: str


class SyncSkippedOut(BaseModel):
    history_id: int
    reason: str


class WarningPolicyOut(BaseModel):
    confirmableIds: list[str]
    blockingIds: list[str]
    unknownIds: list[str]
    fingerprint: str


class OperationCoverageOut(BaseModel):
    rawCount: int
    rawCovered: int
    preparedCount: int


class PreparedVerificationOut(BaseModel):
    ok: bool
    preparedChecked: int
    preparedCount: int
    errors: list[str]


class SchemaIssueOut(BaseModel):
    severity: str
    check_id: str
    sheet: str
    row: Optional[int]
    column: str
    value: JsonValue = None
    message: str


class SchemaValidationOut(BaseModel):
    workbook: str
    status: str
    issue_count: int
    error_count: int
    warning_count: int
    issues: list[SchemaIssueOut]


class BoolHygieneIssueOut(BaseModel):
    check_id: str
    severity: str
    sheet: str
    column: str
    message: str
    before: Optional[dict[str, JsonValue]] = None
    after: Optional[dict[str, JsonValue]] = None
    convention: str


class BoolHygieneOut(BaseModel):
    before_workbook: str
    after_workbook: str
    status: str
    before_bool_like_count: int
    after_bool_like_count: int
    issue_count: int
    error_count: int
    issues: list[BoolHygieneIssueOut]


class SyncOut(BaseModel):
    ok: bool
    status: str
    errors: list[str] = Field(default_factory=list)
    warnings: list[EditorWarningOut] = Field(default_factory=list)
    skipped: list[SyncSkippedOut] = Field(default_factory=list)
    trustedWorkbookSha256: Optional[str] = None
    workbookSha256: Optional[str] = None
    workbookMtimeNs: Optional[str] = None
    opCount: Optional[int] = None
    sheets: list[str] = Field(default_factory=list)
    warningPolicy: Optional[WarningPolicyOut] = None
    operationCoverage: Optional[OperationCoverageOut] = None
    verification: Optional[PreparedVerificationOut] = None
    schemaResult: Optional[SchemaValidationOut] = None
    boolHygieneResult: Optional[BoolHygieneOut] = None
    gateReminders: list[str] = Field(default_factory=list)
    backupPath: Optional[str] = None
    logPath: Optional[str] = None
    applied: Optional[int] = None
    warningsConfirmed: list[str] = Field(default_factory=list)


class SyncConflictResponse(BaseModel):
    detail: SyncOut


class ExportOut(BaseModel):
    ok: Literal[True]
    path: str


class BackupOut(BaseModel):
    ok: Literal[True]
    path: str
