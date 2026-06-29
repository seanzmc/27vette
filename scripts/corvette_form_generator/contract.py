"""Shared contract-surface helpers: assets, context choices, entity labels."""

from __future__ import annotations

from typing import Any, Mapping

from corvette_form_generator.workbook import clean, rows_from_sheet, workbook_truthy


ASSET_IMAGE_FIELDS = (
    "image_url",
    "image_alt",
    "image_fit",
    "image_position",
    "hover_image_url",
    "hover_image_alt",
    "hover_image_position",
)


def asset_fields(row: dict[str, Any]) -> dict[str, str]:
    return {field: clean(row.get(field)) for field in ASSET_IMAGE_FIELDS}


def load_asset_map(wb, model_key: str) -> dict[tuple[str, str], dict[str, str]]:
    """Active asset_map rows for one model, keyed by (target_type, target_id)."""

    if "asset_map" not in wb.sheetnames:
        return {}

    assets: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows_from_sheet(wb, "asset_map"):
        if not workbook_truthy(row.get("active")):
            continue
        if clean(row.get("model_key")) != model_key:
            continue
        target_type = clean(row.get("target_type"))
        target_id = clean(row.get("target_id"))
        fields = asset_fields(row)
        if not target_type or not target_id or not fields["image_url"]:
            continue
        assets[(target_type, target_id)] = fields
    return assets


def option_asset_map(wb, model_key: str) -> dict[str, dict[str, str]]:
    """Option-target assets for one model, keyed by option id."""

    return {
        target_id: fields
        for (target_type, target_id), fields in load_asset_map(wb, model_key).items()
        if target_type == "option"
    }


def bodystyle_asset_map(wb, model_key: str) -> dict[str, dict[str, str]]:
    """Body-style context-card assets keyed by body style context choice id."""

    return {
        target_id: fields
        for (target_type, target_id), fields in load_asset_map(wb, model_key).items()
        if target_type == "context_choice"
    }


def load_model_asset_map(wb, registry_key_for_model) -> dict[str, dict[str, str]]:
    """Model-card assets across every model, keyed by registry target id."""

    if "asset_map" not in wb.sheetnames:
        return {}
    assets: dict[str, dict[str, str]] = {}
    for row in rows_from_sheet(wb, "asset_map"):
        if not workbook_truthy(row.get("active")):
            continue
        if clean(row.get("target_type")) != "model":
            continue
        model_key = clean(row.get("model_key"))
        target_id = clean(row.get("target_id")) or registry_key_for_model(model_key)
        fields = asset_fields(row)
        if not target_id or not fields["image_url"]:
            continue
        assets[target_id] = fields
    return assets


def context_choice_copy_rows(wb, model_key: str) -> list[dict[str, str]]:
    if "context_choice_copy" not in wb.sheetnames:
        return []
    rows: list[dict[str, str]] = []
    for row in rows_from_sheet(wb, "context_choice_copy"):
        if not workbook_truthy(row.get("active")):
            continue
        row_model = clean(row.get("model_key")) or "*"
        if row_model not in {"*", model_key}:
            continue
        if clean(row.get("info_tooltip")):
            rows.append(row)
    return rows


def context_choice_info_tooltip(
    copy_rows: list[dict[str, str]],
    *,
    model_key: str,
    context_type: str,
    value: str,
    body_style: str = "",
) -> str:
    context_type_key = clean(context_type).lower()
    value_key = clean(value).lower()
    body_style_key = clean(body_style).lower()
    best: tuple[int, str] = (-1, "")
    for row in copy_rows:
        row_context_type = clean(row.get("context_type")).lower()
        row_value = clean(row.get("value")).lower()
        row_model = clean(row.get("model_key")) or "*"
        row_body_style = (clean(row.get("body_style")) or "*").lower()
        if row_context_type != context_type_key or row_value != value_key:
            continue
        if row_model not in {"*", model_key}:
            continue
        if row_body_style not in {"*", body_style_key}:
            continue
        score = (2 if row_model == model_key else 0) + (1 if row_body_style == body_style_key else 0)
        tooltip = clean(row.get("info_tooltip"))
        if tooltip and score > best[0]:
            best = (score, tooltip)
    return best[1]


def build_body_context_choices(
    variants: list[dict[str, Any]],
    copy_rows: list[dict[str, str]],
    model_key: str,
    body_style_display_order: Mapping[str, int],
    assets: Mapping[str, dict[str, str]] | None = None,
) -> list[dict[str, Any]]:
    body_context_choices: list[dict[str, Any]] = []
    assets = assets or {}
    body_styles = sorted(
        {row["body_style"] for row in variants},
        key=lambda body_style: body_style_display_order.get(body_style, 99),
    )
    for body_style in body_styles:
        body_variants = [row for row in variants if row["body_style"] == body_style]
        context_choice_id = f"body_style__{body_style}"
        choice = {
                "context_choice_id": context_choice_id,
                "context_type": "body_style",
                "value": body_style,
                "label": body_style.title(),
                "description": f"{len(body_variants)} trims available",
                "info_tooltip": context_choice_info_tooltip(
                    copy_rows,
                    model_key=model_key,
                    context_type="body_style",
                    value=body_style,
                    body_style=body_style,
                ),
                "section_id": "sec_context_body_style",
                "step_key": "body_style",
                "body_style": body_style,
                "trim_level": "",
                "variant_id": "",
                "base_price": "",
                "display_order": body_style_display_order.get(body_style, 99),
            }
        if asset := assets.get(context_choice_id):
            choice.update(asset)
        body_context_choices.append(choice)
    return body_context_choices


def build_trim_context_choices(
    variants: list[dict[str, Any]],
    copy_rows: list[dict[str, str]],
    model_key: str,
) -> list[dict[str, Any]]:
    return [
        {
            "context_choice_id": f"trim_level__{variant['body_style']}__{variant['trim_level'].lower()}",
            "context_type": "trim_level",
            "value": variant["trim_level"],
            "label": variant["trim_level"],
            "description": variant["display_name"],
            "info_tooltip": context_choice_info_tooltip(
                copy_rows,
                model_key=model_key,
                context_type="trim_level",
                value=variant["trim_level"],
                body_style=variant["body_style"],
            ),
            "section_id": "sec_context_trim_level",
            "step_key": "trim_level",
            "body_style": variant["body_style"],
            "trim_level": variant["trim_level"],
            "variant_id": variant["variant_id"],
            "base_price": variant["base_price"],
            "display_order": variant["display_order"],
        }
        for variant in variants
    ]


def label_for(
    entity_id: str,
    options: dict[str, dict[str, Any]],
    interiors_by_id: dict[str, dict[str, Any]],
) -> str:
    if entity_id in options:
        option = options[entity_id]
        return f"{option.get('rpo') or ''} {option.get('label', '')}".strip()
    if entity_id in interiors_by_id:
        interior = interiors_by_id[entity_id]
        return f"{interior.get('interior_id')} {interior.get('interior_name')}".strip()
    return entity_id
