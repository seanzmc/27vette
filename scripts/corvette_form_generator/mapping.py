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
    if selection_mode not in labels:
        raise ValueError(
            f"Selection mode {selection_mode!r} has no authored label. "
            "Add it to the workbook's selection-mode labels rather than title-casing the key."
        )
    return labels[selection_mode]


def step_for_section(section_id: str, section_step_key: str = "") -> str:
    """Return the workbook-authored step for one section.

    ``section_master.step_key`` is the only authority. The former Python
    override map, standard-section set, and section-name substring heuristic
    were all unreachable against the canonical workbook and are gone: a section
    with no authored step is a workbook defect, not something to guess at.
    """

    step_key = clean(section_step_key)
    if not step_key:
        raise ValueError(
            f"Section {section_id!r} has no workbook-authored step_key. "
            "Author section_master.step_key; generation does not infer it."
        )
    return step_key
