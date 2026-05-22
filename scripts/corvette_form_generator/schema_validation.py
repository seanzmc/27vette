"""Read-only workbook schema validation for Corvette form source sheets."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from openpyxl import load_workbook


BOOLEAN_COLUMNS: dict[str, tuple[str, ...]] = {
    "stingray_options": ("selectable", "active"),
    "grandSport_options": ("selectable", "active"),
    "rule_mapping": ("review_flag",),
    "grandSport_rule_mapping": ("review_flag",),
    "price_rules": ("review_flag",),
    "grandSport_price_rules": ("review_flag",),
    "rule_groups": ("active",),
    "grandSport_rule_groups": ("active",),
    "rule_group_members": ("active",),
    "grandSport_rule_group_members": ("active",),
    "exclusive_groups": ("active",),
    "grandSport_exclusive_groups": ("active",),
    "exclusive_group_members": ("active",),
    "grandSport_exclusive_members": ("active",),
    "grandSport_variant_overrides": ("active", "selectable"),
    "lt_interiors": ("active_for_stingray", "requires_r6x"),
    "LZ_Interiors": ("active_for_stingray", "requires_r6x"),
    "model_interior_scope": ("active",),
    "interior_components": ("active",),
}

PRICE_COLUMNS: dict[str, tuple[str, ...]] = {
    "stingray_options": ("price",),
    "grandSport_options": ("price",),
    "price_rules": ("price_value",),
    "grandSport_price_rules": ("price_value",),
    "PriceRef": ("Price",),
    "lt_interiors": ("Price",),
    "LZ_Interiors": ("Price",),
}

RPO_COLUMNS: dict[str, tuple[str, ...]] = {
    "stingray_options": ("rpo",),
    "grandSport_options": ("rpo",),
    "interior_components": ("rpo",),
}

HEADER_PAIRS: tuple[tuple[str, str], ...] = (
    ("stingray_options", "grandSport_options"),
    ("stingray_ovs", "grandSport_ovs"),
    ("rule_mapping", "grandSport_rule_mapping"),
    ("price_rules", "grandSport_price_rules"),
    ("rule_groups", "grandSport_rule_groups"),
    ("rule_group_members", "grandSport_rule_group_members"),
    ("exclusive_groups", "grandSport_exclusive_groups"),
    ("exclusive_group_members", "grandSport_exclusive_members"),
)

REQUIRED_SHEETS: tuple[str, ...] = (
    "variant_master",
    "section_master",
    "stingray_options",
    "stingray_ovs",
    "grandSport_options",
    "grandSport_ovs",
    "rule_mapping",
    "grandSport_rule_mapping",
    "price_rules",
    "grandSport_price_rules",
    "lt_interiors",
    "LZ_Interiors",
    "model_interior_scope",
    "interior_components",
    "PriceRef",
)

LIFECYCLE_COLUMNS: tuple[str, ...] = (
    "normalization_status",
    "normalization_reason",
    "replacement_group_id",
    "replacement_rule_id",
)

ALLOWED_GENERATION_ACTIONS: set[str] = {
    "",
    "omit_grouped_requirement",
    "omit_grouped_exclusion",
    "omit_replaced_by_d3v_include",
    "omit_soft_defaulted_caliper",
    "omit_redundant_scoped_duplicate",
    "preserve_runtime_exclude",
    "omit_replaced_by_brake_exclusive_group",
}

ALLOWED_NORMALIZATION_STATUSES: set[str] = {"", "active", "omitted", "replaced", "preserved", "review"}

GROUP_REPLACEMENT_ACTIONS: set[str] = {
    "omit_grouped_requirement",
    "omit_grouped_exclusion",
    "omit_replaced_by_brake_exclusive_group",
}

RULE_REPLACEMENT_ACTIONS: set[str] = {
    "omit_replaced_by_d3v_include",
    "omit_soft_defaulted_caliper",
    "omit_redundant_scoped_duplicate",
}

DRAFT_ONLY_CHOICE_FIELDS: set[str] = {"source_option_name", "source_description", "text_cleanup_notes"}


@dataclass
class SchemaIssue:
    severity: str
    check_id: str
    sheet: str = ""
    row: int | None = None
    column: str = ""
    value: Any = None
    message: str = ""


def nonblank_headers(ws) -> list[str]:
    return [str(value).strip() for value in next(ws.iter_rows(min_row=1, max_row=1, values_only=True)) if value]


def header_index(ws) -> dict[str, int]:
    return {
        str(value).strip(): index
        for index, value in enumerate(next(ws.iter_rows(min_row=1, max_row=1, values_only=True)), start=1)
        if value
    }


def records(ws) -> Iterable[tuple[int, dict[str, Any]]]:
    headers = [str(value).strip() if value else "" for value in next(ws.iter_rows(min_row=1, max_row=1, values_only=True))]
    for row_number, values in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        record = {header: value for header, value in zip(headers, values) if header}
        if any(value is not None for value in record.values()):
            yield row_number, record


def add_issue(
    issues: list[SchemaIssue],
    severity: str,
    check_id: str,
    *,
    sheet: str = "",
    row: int | None = None,
    column: str = "",
    value: Any = None,
    message: str,
) -> None:
    issues.append(
        SchemaIssue(
            severity=severity,
            check_id=check_id,
            sheet=sheet,
            row=row,
            column=column,
            value=value,
            message=message,
        )
    )


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def option_ids(wb, sheet: str) -> set[str]:
    if sheet not in wb.sheetnames:
        return set()
    return {str(row.get("option_id")) for _, row in records(wb[sheet]) if row.get("option_id")}


def validate_workbook_schema(workbook: str | Path, *, check_live_contract: bool = True) -> list[SchemaIssue]:
    workbook = Path(workbook)
    wb = load_workbook(workbook, read_only=True, data_only=True)
    issues: list[SchemaIssue] = []
    try:
        for sheet in REQUIRED_SHEETS:
            if sheet not in wb.sheetnames:
                add_issue(issues, "error", "missing_required_sheet", sheet=sheet, message=f"Missing required sheet {sheet}.")

        if "category_master" in wb.sheetnames:
            add_issue(
                issues,
                "error",
                "category_master_active",
                sheet="category_master",
                message="category_master should not be an active source sheet; keep only archive_category_master if historical context is needed.",
            )

        for left, right in HEADER_PAIRS:
            if left not in wb.sheetnames or right not in wb.sheetnames:
                continue
            left_headers = nonblank_headers(wb[left])
            right_headers = nonblank_headers(wb[right])
            if left_headers != right_headers:
                add_issue(
                    issues,
                    "error",
                    "header_pair_drift",
                    sheet=f"{left}/{right}",
                    value={"left": left_headers, "right": right_headers},
                    message=f"{left} and {right} headers must match after schema standardization.",
                )

        if "lt_interiors" in wb.sheetnames and "LZ_Interiors" in wb.sheetnames:
            lt_headers = nonblank_headers(wb["lt_interiors"])
            lz_headers = nonblank_headers(wb["LZ_Interiors"])
            if lt_headers != lz_headers:
                add_issue(
                    issues,
                    "error",
                    "lz_interiors_header_drift",
                    sheet="LZ_Interiors",
                    value={"lt_interiors": lt_headers, "LZ_Interiors": lz_headers},
                    message="LZ_Interiors headers must exactly match lt_interiors headers.",
                )

        for sheet, columns in BOOLEAN_COLUMNS.items():
            if sheet not in wb.sheetnames:
                continue
            ws = wb[sheet]
            headers = header_index(ws)
            for column in columns:
                if column not in headers:
                    continue
                for row_number in range(2, ws.max_row + 1):
                    value = ws.cell(row_number, headers[column]).value
                    if value is None:
                        continue
                    if not isinstance(value, bool):
                        add_issue(
                            issues,
                            "error",
                            "boolean_type_drift",
                            sheet=sheet,
                            row=row_number,
                            column=column,
                            value=value,
                            message=f"{sheet}.{column} must be a real Excel boolean, not {type(value).__name__}.",
                        )

        for sheet, columns in RPO_COLUMNS.items():
            if sheet not in wb.sheetnames:
                continue
            ws = wb[sheet]
            headers = header_index(ws)
            for column in columns:
                if column not in headers:
                    continue
                for row_number in range(2, ws.max_row + 1):
                    value = ws.cell(row_number, headers[column]).value
                    if value is None:
                        continue
                    if not isinstance(value, str):
                        add_issue(
                            issues,
                            "error",
                            "rpo_type_drift",
                            sheet=sheet,
                            row=row_number,
                            column=column,
                            value=value,
                            message=f"{sheet}.{column} must be stored as text, including numeric-looking RPOs.",
                        )

        for sheet, columns in PRICE_COLUMNS.items():
            if sheet not in wb.sheetnames:
                continue
            ws = wb[sheet]
            headers = header_index(ws)
            for column in columns:
                if column not in headers:
                    continue
                for row_number in range(2, ws.max_row + 1):
                    value = ws.cell(row_number, headers[column]).value
                    if value is None:
                        continue
                    if not is_number(value):
                        add_issue(
                            issues,
                            "error",
                            "price_type_drift",
                            sheet=sheet,
                            row=row_number,
                            column=column,
                            value=value,
                            message=f"{sheet}.{column} must be numeric or blank; blank means null/not-priced and 0 means explicit zero-price.",
                        )

        for sheet in ("rule_mapping", "grandSport_rule_mapping"):
            if sheet not in wb.sheetnames:
                continue
            ws = wb[sheet]
            headers = header_index(ws)
            for column in LIFECYCLE_COLUMNS:
                if column not in headers:
                    add_issue(
                        issues,
                        "error",
                        "missing_lifecycle_column",
                        sheet=sheet,
                        column=column,
                        message=f"{sheet} must include lifecycle column {column}.",
                    )
            if not all(column in headers for column in ("generation_action", "normalization_status")):
                continue
            for row_number, row in records(ws):
                action = str(row.get("generation_action") or "").strip()
                status = str(row.get("normalization_status") or "").strip()
                reason = str(row.get("normalization_reason") or "").strip()
                replacement_group_id = str(row.get("replacement_group_id") or "").strip()
                replacement_rule_id = str(row.get("replacement_rule_id") or "").strip()
                if action not in ALLOWED_GENERATION_ACTIONS:
                    add_issue(
                        issues,
                        "error",
                        "unknown_generation_action",
                        sheet=sheet,
                        row=row_number,
                        column="generation_action",
                        value=action,
                        message=f"Unknown generation_action {action!r}.",
                    )
                if status not in ALLOWED_NORMALIZATION_STATUSES:
                    add_issue(
                        issues,
                        "error",
                        "unknown_normalization_status",
                        sheet=sheet,
                        row=row_number,
                        column="normalization_status",
                        value=status,
                        message=f"Unknown normalization_status {status!r}.",
                    )
                if action.startswith("omit") and status not in {"omitted", "replaced"}:
                    add_issue(
                        issues,
                        "error",
                        "omitted_action_missing_status",
                        sheet=sheet,
                        row=row_number,
                        column="normalization_status",
                        value=status,
                        message="Omitted/replaced generation_action rows must have omitted or replaced normalization_status.",
                    )
                if action.startswith("omit") and not reason:
                    add_issue(
                        issues,
                        "error",
                        "omitted_action_missing_reason",
                        sheet=sheet,
                        row=row_number,
                        column="normalization_reason",
                        message="Omitted/replaced generation_action rows must retain a normalization_reason.",
                    )
                if action in GROUP_REPLACEMENT_ACTIONS and not replacement_group_id:
                    add_issue(
                        issues,
                        "error",
                        "missing_replacement_group_id",
                        sheet=sheet,
                        row=row_number,
                        column="replacement_group_id",
                        message=f"{action} rows must identify replacement_group_id.",
                    )
                if action in RULE_REPLACEMENT_ACTIONS and not replacement_rule_id:
                    add_issue(
                        issues,
                        "error",
                        "missing_replacement_rule_id",
                        sheet=sheet,
                        row=row_number,
                        column="replacement_rule_id",
                        message=f"{action} rows must identify replacement_rule_id.",
                    )
                if action == "preserve_runtime_exclude" and status != "preserved":
                    add_issue(
                        issues,
                        "error",
                        "preserved_action_status",
                        sheet=sheet,
                        row=row_number,
                        column="normalization_status",
                        value=status,
                        message="preserve_runtime_exclude rows must have normalization_status preserved.",
                    )

        for option_sheet, ovs_sheet in (("stingray_options", "stingray_ovs"), ("grandSport_options", "grandSport_ovs")):
            if option_sheet not in wb.sheetnames or ovs_sheet not in wb.sheetnames:
                continue
            valid_options = option_ids(wb, option_sheet)
            for row_number, row in records(wb[ovs_sheet]):
                option_id = row.get("option_id")
                if option_id and option_id not in valid_options:
                    add_issue(
                        issues,
                        "error",
                        "ovs_unknown_option_id",
                        sheet=ovs_sheet,
                        row=row_number,
                        column="option_id",
                        value=option_id,
                        message=f"{ovs_sheet}.option_id does not resolve to {option_sheet}.",
                    )

        if check_live_contract:
            app_data_path = workbook.parent / "form-app" / "data.js"
            if app_data_path.exists():
                text = app_data_path.read_text(encoding="utf-8")
                try:
                    registry_json = text.split("window.CORVETTE_FORM_DATA = ", 1)[1].split(
                        ";\nwindow.STINGRAY_FORM_DATA", 1
                    )[0]
                    registry = json.loads(registry_json)
                    for model_key, entry in registry.get("models", {}).items():
                        data = entry.get("data", {})
                        if "draftMetadata" in data:
                            add_issue(
                                issues,
                                "error",
                                "draft_metadata_in_live_contract",
                                sheet="form-app/data.js",
                                value=model_key,
                                message="draftMetadata is inspection provenance and must not be emitted in live app data.",
                            )
                        for index, choice in enumerate(data.get("choices", []), start=1):
                            leaked = sorted(DRAFT_ONLY_CHOICE_FIELDS & set(choice))
                            if leaked:
                                add_issue(
                                    issues,
                                    "error",
                                    "draft_choice_fields_in_live_contract",
                                    sheet="form-app/data.js",
                                    row=index,
                                    value={"model_key": model_key, "choice_id": choice.get("choice_id"), "fields": leaked},
                                    message="Draft/provenance choice fields must not leak into live app data.",
                                )
                except (IndexError, json.JSONDecodeError) as exc:
                    add_issue(
                        issues,
                        "error",
                        "app_data_parse_failed",
                        sheet="form-app/data.js",
                        message=f"Could not parse window.CORVETTE_FORM_DATA: {exc}",
                    )

        return issues
    finally:
        wb.close()


def result_payload(workbook: str | Path, issues: list[SchemaIssue]) -> dict[str, Any]:
    return {
        "workbook": str(workbook),
        "status": "valid" if not any(issue.severity == "error" for issue in issues) else "invalid",
        "issue_count": len(issues),
        "error_count": sum(1 for issue in issues if issue.severity == "error"),
        "warning_count": sum(1 for issue in issues if issue.severity == "warning"),
        "issues": [asdict(issue) for issue in issues],
    }
