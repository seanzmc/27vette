"""Shared section, status, and selection-mode mapping helpers."""

from __future__ import annotations

from collections.abc import Mapping

from corvette_form_generator.workbook import clean


def status_rank(status: str) -> int:
    return {"unavailable": 0, "available": 1, "standard": 2}.get(status, 0)


def best_status(*statuses: str) -> str:
    cleaned = [clean(status).lower() for status in statuses if clean(status)]
    if not cleaned:
        return "unavailable"
    return max(cleaned, key=status_rank)


def status_to_label(status: str) -> str:
    return {
        "available": "Available",
        "standard": "Standard",
        "unavailable": "Not Available",
    }.get(status.lower(), status or "Unknown")


def normalize_mode(selection_mode: str) -> str:
    if selection_mode.startswith("single"):
        return "single"
    if selection_mode.startswith("multi"):
        return "multi"
    return "display"


def selection_mode_label(selection_mode: str, labels: Mapping[str, str]) -> str:
    if not selection_mode:
        return ""
    return labels.get(selection_mode, selection_mode.replace("_", " ").title())


def step_for_section(
    section_id: str,
    section_name: str,
    category_id: str,
    *,
    standard_sections: set[str] | frozenset[str],
    section_step_overrides: Mapping[str, str],
) -> str:
    if section_id in standard_sections:
        return "standard_equipment"
    if section_id in section_step_overrides:
        return section_step_overrides[section_id]
    name = section_name.lower()
    if "stripe" in name or "spoiler" in name or "lpo" in name or "exhaust" in name or "wheel accessory" in name:
        return "aero_exhaust_stripes_accessories"
    if category_id == "cat_exte_001":
        return "exterior_appearance"
    if category_id == "cat_inte_001":
        return "interior_trim"
    if category_id == "cat_mech_001":
        return "packages_performance"
    return "standard_equipment"
