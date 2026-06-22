#!/usr/bin/env python3
"""Focused characterization for shared source assembly."""

from __future__ import annotations

import json
from pathlib import Path

from corvette_form_generator.model_configs import discover_generation_model_configs
from corvette_form_generator.source_assembly import assemble_model_source

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = ROOT / "form-output" / "runtime"


def load_runtime_contract(slug: str) -> dict:
    return json.loads((RUNTIME_DIR / f"{slug}-runtime-contract.json").read_text())


def ids(rows: list[dict], key: str) -> list[str]:
    return [row[key] for row in rows]


def test_shared_assembler_preserves_stingray_runtime_drift_surfaces() -> None:
    config = discover_generation_model_configs()["stingray"]
    assembly = assemble_model_source(config)
    runtime = assembly.runtime_contract
    baseline = load_runtime_contract("stingray")

    assert ids(runtime["sections"], "section_id") == ids(baseline["sections"], "section_id")
    assert ids(runtime["rules"], "rule_id") == ids(baseline["rules"], "rule_id")
    assert len(runtime["colorOverrides"]) == len(baseline["colorOverrides"])
    assert all(choice.get("display_behavior", "") for choice in runtime["choices"] if "display_behavior" in choice)

    uqt_choices = {
        choice["choice_id"]: choice
        for choice in runtime["choices"]
        if choice.get("option_id") == "opt_uqt_002"
    }
    baseline_uqt_choices = {
        choice["choice_id"]: choice
        for choice in baseline["choices"]
        if choice.get("option_id") == "opt_uqt_002"
    }
    assert uqt_choices.keys() == baseline_uqt_choices.keys()
    for choice_id, choice in uqt_choices.items():
        baseline_choice = baseline_uqt_choices[choice_id]
        assert choice["status"] == baseline_choice["status"]
        assert choice["active"] == baseline_choice["active"]
        assert choice["selectable"] == baseline_choice["selectable"]
        assert "display_behavior" not in choice

    assert all("requires_z25" not in row for row in runtime["interiors"])


def test_shared_assembler_preserves_grand_sport_runtime_drift_surfaces() -> None:
    config = discover_generation_model_configs()["grand_sport"]
    assembly = assemble_model_source(config)
    runtime = assembly.runtime_contract
    baseline = load_runtime_contract("grand-sport")

    assert ids(runtime["sections"], "section_id") == ids(baseline["sections"], "section_id")
    assert ids(runtime["rules"], "rule_id") == ids(baseline["rules"], "rule_id")
    assert len(runtime["colorOverrides"]) == len(baseline["colorOverrides"])
    runtime_display_behavior = {
        choice["choice_id"]: choice.get("display_behavior")
        for choice in runtime["choices"]
        if "display_behavior" in choice
    }
    baseline_display_behavior = {
        choice["choice_id"]: choice.get("display_behavior")
        for choice in baseline["choices"]
        if "display_behavior" in choice
    }
    assert runtime_display_behavior == baseline_display_behavior

    runtime_requires_z25 = [row.get("requires_z25") for row in runtime["interiors"]]
    baseline_requires_z25 = [row.get("requires_z25") for row in baseline["interiors"]]
    assert runtime_requires_z25 == baseline_requires_z25
    assert any(value == "True" for value in runtime_requires_z25)
