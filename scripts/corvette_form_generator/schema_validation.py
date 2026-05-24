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
    "model_registry_promotion": ("promoted_to_runtime", "default_model", "active"),
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

MODEL_SOURCE_ROLES: set[str] = {
    "source_option_sheet",
    "status_sheet",
    "rule_mapping_sheet",
    "price_rules_sheet",
    "rule_groups_sheet",
    "rule_group_members_sheet",
    "exclusive_groups_sheet",
    "exclusive_group_members_sheet",
    "color_overrides_sheet",
    "variant_option_overrides_sheet",
    "interior_source_sheet",
}

LEGACY_MODEL_SOURCES: dict[str, dict[str, str]] = {
    "stingray": {
        "source_option_sheet": "stingray_options",
        "status_sheet": "stingray_ovs",
        "rule_mapping_sheet": "rule_mapping",
        "price_rules_sheet": "price_rules",
        "rule_groups_sheet": "rule_groups",
        "rule_group_members_sheet": "rule_group_members",
        "exclusive_groups_sheet": "exclusive_groups",
        "exclusive_group_members_sheet": "exclusive_group_members",
        "color_overrides_sheet": "color_overrides",
        "interior_source_sheet": "lt_interiors",
    },
    "grand_sport": {
        "source_option_sheet": "grandSport_options",
        "status_sheet": "grandSport_ovs",
        "rule_mapping_sheet": "grandSport_rule_mapping",
        "price_rules_sheet": "grandSport_price_rules",
        "rule_groups_sheet": "grandSport_rule_groups",
        "rule_group_members_sheet": "grandSport_rule_group_members",
        "exclusive_groups_sheet": "grandSport_exclusive_groups",
        "exclusive_group_members_sheet": "grandSport_exclusive_members",
        "color_overrides_sheet": "color_overrides",
        "variant_option_overrides_sheet": "grandSport_variant_overrides",
        "interior_source_sheet": "lt_interiors",
    },
}

ROLE_BOOLEAN_COLUMNS: dict[str, tuple[str, ...]] = {
    "source_option_sheet": ("selectable", "active"),
    "rule_mapping_sheet": ("review_flag",),
    "price_rules_sheet": ("review_flag",),
    "rule_groups_sheet": ("active",),
    "rule_group_members_sheet": ("active",),
    "exclusive_groups_sheet": ("active",),
    "exclusive_group_members_sheet": ("active",),
    "variant_option_overrides_sheet": ("active", "selectable"),
    "interior_source_sheet": ("active_for_stingray", "requires_r6x"),
}

ROLE_PRICE_COLUMNS: dict[str, tuple[str, ...]] = {
    "source_option_sheet": ("price",),
    "price_rules_sheet": ("price_value",),
    "interior_source_sheet": ("Price",),
}

ROLE_RPO_COLUMNS: dict[str, tuple[str, ...]] = {
    "source_option_sheet": ("rpo",),
}

HEADER_MATCH_ROLES: tuple[str, ...] = (
    "source_option_sheet",
    "status_sheet",
    "rule_mapping_sheet",
    "price_rules_sheet",
    "rule_groups_sheet",
    "rule_group_members_sheet",
    "exclusive_groups_sheet",
    "exclusive_group_members_sheet",
    "interior_source_sheet",
)

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

MODEL_REGISTRY_PROMOTION_HEADERS: tuple[str, ...] = (
    "model_key",
    "registry_key",
    "promoted_to_runtime",
    "default_model",
    "artifact_path",
    "artifact_type",
    "legacy_alias",
    "active",
    "display_order",
    "notes",
)
VALID_REGISTRY_PROMOTION_ARTIFACT_TYPES: set[str] = {"current_generation", "draft_artifact"}


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


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def truthy(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = clean_text(value).lower()
    if not text:
        return default
    if text in {"1", "true", "t", "yes", "y", "on", "active", "enabled"}:
        return True
    if text in {"0", "false", "f", "no", "n", "off", "inactive", "disabled"}:
        return False
    return default


def active_metadata_rows(wb, sheet: str, model_key: str | None = None) -> list[dict[str, Any]]:
    if sheet not in wb.sheetnames:
        return []
    rows = [row for _, row in records(wb[sheet]) if truthy(row.get("active"), default=True)]
    if model_key is None:
        return rows
    return [row for row in rows if clean_text(row.get("model_key")).lower() in {model_key.lower(), "*", "all", "shared"}]


def metadata_source_graph(wb, issues: list[SchemaIssue]) -> dict[str, dict[str, str]]:
    """Return active model source-role mapping with legacy fallback seeds."""

    graph = {model: dict(sources) for model, sources in LEGACY_MODEL_SOURCES.items()}
    active_models = {clean_text(row.get("model_key")).lower() for row in active_metadata_rows(wb, "model_master")}
    active_models.discard("")

    if "model_workbook_sources" not in wb.sheetnames:
        return graph

    seen: set[tuple[str, str]] = set()
    for row_number, row in records(wb["model_workbook_sources"]):
        if not truthy(row.get("active"), default=True):
            continue
        model_key = clean_text(row.get("model_key")).lower()
        source_role = clean_text(row.get("source_role"))
        sheet_name = clean_text(row.get("sheet_name"))
        if not model_key or not source_role or not sheet_name:
            continue
        if active_models and model_key not in active_models and model_key not in {"*", "all", "shared"}:
            continue
        if source_role not in MODEL_SOURCE_ROLES:
            add_issue(
                issues,
                "error",
                "unknown_model_source_role",
                sheet="model_workbook_sources",
                row=row_number,
                column="source_role",
                value=source_role,
                message=f"Unknown model_workbook_sources source_role {source_role!r}.",
            )
            continue
        duplicate_key = (model_key, source_role)
        if duplicate_key in seen:
            add_issue(
                issues,
                "error",
                "duplicate_model_source_role",
                sheet="model_workbook_sources",
                row=row_number,
                column="source_role",
                value={"model_key": model_key, "source_role": source_role},
                message=f"Duplicate active source role {source_role!r} for model {model_key!r}.",
            )
            continue
        seen.add(duplicate_key)
        graph.setdefault(model_key, {})[source_role] = sheet_name

    for model_key, sources in graph.items():
        for source_role, sheet_name in sources.items():
            if sheet_name and sheet_name not in wb.sheetnames:
                add_issue(
                    issues,
                    "error",
                    "missing_model_source_sheet",
                    sheet=sheet_name,
                    value={"model_key": model_key, "source_role": source_role},
                    message=f"Active {model_key}.{source_role} sheet {sheet_name!r} does not exist.",
                )
    return graph


def sheets_by_role(source_graph: dict[str, dict[str, str]]) -> dict[str, list[str]]:
    by_role: dict[str, list[str]] = {}
    for sources in source_graph.values():
        for source_role, sheet_name in sources.items():
            if not sheet_name:
                continue
            by_role.setdefault(source_role, [])
            if sheet_name not in by_role[source_role]:
                by_role[source_role].append(sheet_name)
    return by_role


def validate_registry_promotion_metadata(wb, issues: list[SchemaIssue]) -> None:
    if "model_registry_promotion" not in wb.sheetnames:
        return

    headers = nonblank_headers(wb["model_registry_promotion"])
    if headers != list(MODEL_REGISTRY_PROMOTION_HEADERS):
        add_issue(
            issues,
            "error",
            "registry_promotion_header_drift",
            sheet="model_registry_promotion",
            value={"expected": list(MODEL_REGISTRY_PROMOTION_HEADERS), "actual": headers},
            message="model_registry_promotion headers must match the workbook-owned runtime promotion contract.",
        )

    model_rows = {
        clean_text(row.get("model_key")).lower(): row
        for _, row in records(wb["model_master"])
        if clean_text(row.get("model_key"))
    }
    promoted_rows: list[tuple[int, dict[str, Any]]] = []
    seen_registry_keys: set[str] = set()
    for row_number, row in records(wb["model_registry_promotion"]):
        if not truthy(row.get("active"), default=True) or not truthy(row.get("promoted_to_runtime"), default=False):
            continue
        promoted_rows.append((row_number, row))
        model_key = clean_text(row.get("model_key")).lower()
        registry_key = clean_text(row.get("registry_key"))
        artifact_path = clean_text(row.get("artifact_path"))
        artifact_type = clean_text(row.get("artifact_type")) or "draft_artifact"
        if registry_key in seen_registry_keys:
            add_issue(
                issues,
                "error",
                "registry_promotion_duplicate_registry_key",
                sheet="model_registry_promotion",
                row=row_number,
                column="registry_key",
                value=registry_key,
                message=f"Duplicate promoted runtime registry_key {registry_key!r}.",
            )
        seen_registry_keys.add(registry_key)
        model_row = model_rows.get(model_key)
        if not model_row:
            add_issue(
                issues,
                "error",
                "registry_promotion_unknown_model",
                sheet="model_registry_promotion",
                row=row_number,
                column="model_key",
                value=model_key,
                message=f"Promoted runtime model {model_key!r} is not present in model_master.",
            )
            continue
        expected_registry_key = clean_text(model_row.get("registry_key")) or model_key
        if registry_key != expected_registry_key:
            add_issue(
                issues,
                "error",
                "registry_promotion_registry_key_mismatch",
                sheet="model_registry_promotion",
                row=row_number,
                column="registry_key",
                value={"model_key": model_key, "registry_key": registry_key, "expected": expected_registry_key},
                message=f"Promoted runtime registry_key for {model_key!r} must match model_master.registry_key {expected_registry_key!r}.",
            )
        if not truthy(model_row.get("active"), default=True):
            add_issue(
                issues,
                "error",
                "registry_promotion_inactive_model",
                sheet="model_registry_promotion",
                row=row_number,
                column="model_key",
                value=model_key,
                message=f"Promoted runtime model {model_key!r} is inactive in model_master.",
            )
        if artifact_type not in VALID_REGISTRY_PROMOTION_ARTIFACT_TYPES:
            add_issue(
                issues,
                "error",
                "registry_promotion_unknown_artifact_type",
                sheet="model_registry_promotion",
                row=row_number,
                column="artifact_type",
                value=artifact_type,
                message=f"Unsupported runtime promotion artifact_type {artifact_type!r}.",
            )
        if artifact_type != "current_generation" and not artifact_path:
            add_issue(
                issues,
                "error",
                "registry_promotion_missing_artifact_path",
                sheet="model_registry_promotion",
                row=row_number,
                column="artifact_path",
                value={"model_key": model_key, "artifact_type": artifact_type},
                message="Promoted non-current-generation runtime models must provide artifact_path.",
            )

    default_count = sum(1 for _, row in promoted_rows if truthy(row.get("default_model"), default=False))
    if promoted_rows and default_count != 1:
        add_issue(
            issues,
            "error",
            "registry_promotion_default_count",
            sheet="model_registry_promotion",
            value={"promoted_rows": len(promoted_rows), "default_count": default_count},
            message="model_registry_promotion must have exactly one active promoted default model.",
        )


def merge_sheet_columns(
    base: dict[str, tuple[str, ...]],
    by_role: dict[str, list[str]],
    role_columns: dict[str, tuple[str, ...]],
) -> dict[str, tuple[str, ...]]:
    merged = {sheet: tuple(columns) for sheet, columns in base.items()}
    for source_role, columns in role_columns.items():
        for sheet in by_role.get(source_role, []):
            merged[sheet] = tuple(dict.fromkeys((*merged.get(sheet, ()), *columns)))
    return merged


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

        source_graph = metadata_source_graph(wb, issues)
        source_sheets_by_role = sheets_by_role(source_graph)
        validate_registry_promotion_metadata(wb, issues)

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

        for source_role in HEADER_MATCH_ROLES:
            existing_sheets = [sheet for sheet in source_sheets_by_role.get(source_role, []) if sheet in wb.sheetnames]
            if len(existing_sheets) < 2:
                continue
            canonical_sheet = existing_sheets[0]
            canonical_headers = nonblank_headers(wb[canonical_sheet])
            for sheet in existing_sheets[1:]:
                current_headers = nonblank_headers(wb[sheet])
                if current_headers != canonical_headers:
                    add_issue(
                        issues,
                        "error",
                        "source_role_header_drift",
                        sheet=source_role,
                        value={
                            "canonical_sheet": canonical_sheet,
                            "canonical_headers": canonical_headers,
                            "sheet": sheet,
                            "headers": current_headers,
                        },
                        message=f"All active {source_role} sheets must share headers; {sheet} differs from {canonical_sheet}.",
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

        boolean_columns = merge_sheet_columns(BOOLEAN_COLUMNS, source_sheets_by_role, ROLE_BOOLEAN_COLUMNS)
        rpo_columns = merge_sheet_columns(RPO_COLUMNS, source_sheets_by_role, ROLE_RPO_COLUMNS)
        price_columns = merge_sheet_columns(PRICE_COLUMNS, source_sheets_by_role, ROLE_PRICE_COLUMNS)

        for sheet, columns in boolean_columns.items():
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

        for sheet, columns in rpo_columns.items():
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

        for sheet, columns in price_columns.items():
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

        rule_mapping_sheets = tuple(source_sheets_by_role.get("rule_mapping_sheet", [])) or (
            "rule_mapping",
            "grandSport_rule_mapping",
        )
        for sheet in rule_mapping_sheets:
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

        validated_ovs_pairs: set[tuple[str, str]] = set()
        for model_key, sources in source_graph.items():
            option_sheet = sources.get("source_option_sheet", "")
            ovs_sheet = sources.get("status_sheet", "")
            if not option_sheet or not ovs_sheet or (option_sheet, ovs_sheet) in validated_ovs_pairs:
                continue
            validated_ovs_pairs.add((option_sheet, ovs_sheet))
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
                        message=f"{ovs_sheet}.option_id does not resolve to {option_sheet} for model {model_key}.",
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
