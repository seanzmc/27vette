#!/usr/bin/env python3
# pyright: reportMissingImports=false
"""Tests for shared runtime-contract finalization.

The expected contracts here are written out in full rather than derived from
``live_contract_data()``. A test that builds its expectation with the same
helper the code under test uses cannot fail when that helper changes — both
sides move together — so every field the builder is supposed to strip, rewrite,
or overwrite is spelled out below.
"""

from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from corvette_form_generator.model_configs import base_model_config  # noqa: E402
from corvette_form_generator.runtime_contract import build_model_runtime_contract  # noqa: E402

BASE_GRAND_SPORT_CONFIG = base_model_config("grand_sport")


def draft_payload() -> dict[str, Any]:
    """A minimal draft carrying one instance of every field class the builder touches."""

    return {
        "dataset": {
            "status": "draft_not_runtime_active",
            "name": "2027 Corvette Grand Sport form data draft",
            "source_workbook": "stingray_master.xlsx",
        },
        "choices": [
            {
                "choice_id": "choice-1",
                "label": "Carbon Flash Badges",
                # runtime choice-row trim fields
                "source_detail_raw": "raw note",
                "choice_mode": "single",
                "selection_mode": "single_select_req",
                "selection_mode_label": "Required single selection",
                # draft-only choice fields
                "source_option_name": "draft-only name",
                "source_description": "draft-only description",
                "text_cleanup_notes": ["draft-only note"],
                # draft-only provenance, nested anywhere. All six
                # DRAFT_ONLY_PROVENANCE_FIELDS appear across this payload; a
                # field left out here can be dropped from the strip list with
                # the whole suite still green.
                "review_status": "pending",
                "review_flags": ["unreviewed"],
                "raw_source_sheet": "grandSport_options",
                "raw_source_sheets": ["grandSport_options", "grandSport_ovs"],
                "copy_from_model_key": "z06",
                "suggested_copy_from": "z06",
            }
        ],
        "standardEquipment": [
            {"equipment_id": "std-1", "label": "Standard thing", "source_detail_raw": "raw note"}
        ],
        "variants": [{"variant_id": "test-variant", "suggested_copy_from": "z06"}],
        "steps": [{"step_key": "test-step"}],
        "sections": [{"section_id": "test-section"}],
        "contextChoices": [{"context_choice_id": "test-context"}],
        "orderSummary": {"sections": []},
        "ruleGroups": [],
        "exclusiveGroups": [],
        "rules": [],
        "priceRules": [],
        "interiors": [],
        "colorOverrides": [],
        "defaultSelectionRules": [],
        "validation": [
            {
                "check_id": "grand_sport_draft_status",
                "severity": "warning",
                "entity_type": "dataset",
                "entity_id": "",
                "message": "draft marker",
            },
            {
                "check_id": "active_variants",
                "severity": "pass",
                "entity_type": "variant",
                "entity_id": "",
                "message": "ok",
            },
        ],
        "draftMetadata": {"sourcePreviewStatus": "read_only_preview"},
        "_derivationManifest": {"rules": []},
    }


EXPECTED_RUNTIME_CONTRACT: dict[str, Any] = {
    "dataset": {
        # status flipped, and name/model/model_year taken from the config rather
        # than from the draft's own " form data draft" rewrite
        "status": "runtime_active",
        "name": "2027 Corvette Grand Sport operational form",
        "model": "Grand Sport",
        "model_year": "2027",
        "source_workbook": "stingray_master.xlsx",
    },
    "choices": [{"choice_id": "choice-1", "label": "Carbon Flash Badges"}],
    "standardEquipment": [{"equipment_id": "std-1", "label": "Standard thing"}],
    "variants": [{"variant_id": "test-variant"}],
    "steps": [{"step_key": "test-step"}],
    "sections": [{"section_id": "test-section"}],
    "contextChoices": [{"context_choice_id": "test-context"}],
    "orderSummary": {"sections": []},
    "ruleGroups": [],
    "exclusiveGroups": [],
    "rules": [],
    "priceRules": [],
    "interiors": [],
    "colorOverrides": [],
    "defaultSelectionRules": [],
    # the *_draft_status warning is dropped; every other row survives untouched
    "validation": [
        {
            "check_id": "active_variants",
            "severity": "pass",
            "entity_type": "variant",
            "entity_id": "",
            "message": "ok",
        }
    ],
}


class RuntimeContractBuilderTests(unittest.TestCase):
    def test_builder_output_matches_the_expected_contract_exactly(self) -> None:
        actual = build_model_runtime_contract(BASE_GRAND_SPORT_CONFIG, draft_payload())

        self.assertEqual(actual, EXPECTED_RUNTIME_CONTRACT)

    def test_config_owns_the_dataset_identity_even_when_the_draft_disagrees(self) -> None:
        """The draft's own dataset name/model/year must not survive into the contract."""

        draft = draft_payload()
        draft["dataset"].update({"name": "wrong name", "model": "ZR1", "model_year": "1999"})

        actual = build_model_runtime_contract(BASE_GRAND_SPORT_CONFIG, draft)

        self.assertEqual(actual["dataset"]["name"], BASE_GRAND_SPORT_CONFIG.dataset_name)
        self.assertEqual(actual["dataset"]["model"], BASE_GRAND_SPORT_CONFIG.model_label)
        self.assertEqual(actual["dataset"]["model_year"], BASE_GRAND_SPORT_CONFIG.model_year)

    def test_the_source_draft_is_not_mutated(self) -> None:
        draft = draft_payload()
        before = copy.deepcopy(draft)

        build_model_runtime_contract(BASE_GRAND_SPORT_CONFIG, draft)

        self.assertEqual(draft, before)

    def test_builder_rejects_an_error_severity_finding(self) -> None:
        draft = draft_payload()
        draft["validation"].append(
            {
                "check_id": "broken_reference",
                "severity": "error",
                "entity_type": "choice",
                "entity_id": "choice-1",
                "message": "dangling",
            }
        )

        with self.assertRaisesRegex(ValueError, "error-severity validation finding"):
            build_model_runtime_contract(BASE_GRAND_SPORT_CONFIG, draft)

    def test_builder_rejects_an_unknown_validation_severity(self) -> None:
        draft = draft_payload()
        draft["validation"][1]["severity"] = "critical"

        with self.assertRaisesRegex(ValueError, "invalid severities"):
            build_model_runtime_contract(BASE_GRAND_SPORT_CONFIG, draft)

    def test_builder_rejects_an_empty_required_collection(self) -> None:
        for field in ("variants", "steps", "sections", "contextChoices", "choices"):
            with self.subTest(field=field):
                draft = draft_payload()
                draft[field] = []
                with self.assertRaisesRegex(ValueError, f"{field} must not be empty"):
                    build_model_runtime_contract(BASE_GRAND_SPORT_CONFIG, draft)

    def test_builder_rejects_a_missing_or_malformed_collection(self) -> None:
        draft = draft_payload()
        del draft["rules"]
        with self.assertRaisesRegex(ValueError, "rules must be a list"):
            build_model_runtime_contract(BASE_GRAND_SPORT_CONFIG, draft)

        draft = draft_payload()
        draft["interiors"] = [["not", "an", "object"]]
        with self.assertRaisesRegex(ValueError, "interiors must contain only objects"):
            build_model_runtime_contract(BASE_GRAND_SPORT_CONFIG, draft)

        draft = draft_payload()
        draft["orderSummary"] = []
        with self.assertRaisesRegex(ValueError, "orderSummary must be an object"):
            build_model_runtime_contract(BASE_GRAND_SPORT_CONFIG, draft)

    def test_builder_rejects_a_non_object_dataset(self) -> None:
        draft = draft_payload()
        draft["dataset"] = "grand sport"

        with self.assertRaisesRegex(ValueError, "non-object dataset"):
            build_model_runtime_contract(BASE_GRAND_SPORT_CONFIG, draft)

    def test_draft_only_provenance_is_stripped_wherever_it_is_nested(self) -> None:
        """Stripping is by key at any depth, not only in the rows listed above.

        The main expectation covers provenance on a choice row and a variant
        row; this covers a container the trim-field table says nothing about,
        so a stripper narrowed to known row paths fails here.
        """

        draft = draft_payload()
        draft["orderSummary"] = {"sections": [{"section_id": "s1", "review_status": "pending"}], "review_flags": ["x"]}

        contract = build_model_runtime_contract(BASE_GRAND_SPORT_CONFIG, draft)

        self.assertNotIn("review_flags", contract["orderSummary"])
        self.assertEqual(contract["orderSummary"]["sections"], [{"section_id": "s1"}])

    def test_the_finalizer_owns_live_contract_data_and_promotion_borrows_it(self) -> None:
        """Direction check: promotion depends on the finalizer, never the reverse."""

        from corvette_form_generator import registry_promotion, runtime_contract

        self.assertIs(registry_promotion.live_contract_data, runtime_contract.live_contract_data)
        self.assertEqual(runtime_contract.live_contract_data.__module__, "corvette_form_generator.runtime_contract")


PACKAGE = ROOT / "scripts" / "corvette_form_generator"


def modules_calling(function_name: str) -> set[str]:
    """Module names whose AST contains a call to ``function_name``.

    Parsed, not grepped: a mention in a docstring, a comment, or a string
    literal is not a call, and this must not fire on the tests' own prose.
    """

    callers: set[str] = set()
    for path in sorted(PACKAGE.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
            if name == function_name:
                callers.add(path.name)
    return callers


def modules_importing_from(module: str, symbol: str) -> set[str]:
    """Module names that import ``symbol`` from ``module``, by AST."""

    importers: set[str] = set()
    for path in sorted(PACKAGE.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").endswith(module):
                if any(alias.name == symbol for alias in node.names):
                    importers.add(path.name)
    return importers


class RuntimeContractFinalizerRouteTests(unittest.TestCase):
    def test_only_the_finalizer_and_the_assembly_call_the_finalizer(self) -> None:
        """One route, one finalizer — a third caller is a second publication path.

        The break-one below proves assembly *reaches* the finalizer; it cannot
        see a second module that also calls it, because patching one path says
        nothing about another. This is that half of the guarantee.

        The retired text-grep version of this check expected
        ``{runtime_contract.py, source_assembly.py}`` because a substring search
        also matches the ``def`` line and the docstring in the defining module.
        Parsed properly, ``runtime_contract.py`` never calls its own finalizer,
        and the real caller set is one module.
        """

        self.assertEqual(modules_calling("build_model_runtime_contract"), {"source_assembly.py"})

    def test_the_generation_lane_does_not_depend_on_registry_promotion(self) -> None:
        """The reverse dependency stays retired.

        Identity of ``registry_promotion.live_contract_data`` is unchanged by a
        generation module re-importing it from there, so identity alone cannot
        police the direction — the import edge has to be checked.
        """

        importers = modules_importing_from("registry_promotion", "live_contract_data")

        self.assertEqual(importers, set())

    def test_the_finalizer_is_reachable_from_exactly_one_assembly_path(self) -> None:
        """One route, one finalizer — asserted by call, not by reading module text.

        Disabling the finalizer must break assembly for every model. If a second
        path existed, assembly would still succeed with it patched out.
        """

        from unittest.mock import patch

        from corvette_form_generator import source_assembly
        from corvette_form_generator.model_configs import discover_generation_model_configs

        configs = discover_generation_model_configs(ROOT / "stingray_master.xlsx", root=ROOT)
        with patch.object(
            source_assembly,
            "build_model_runtime_contract",
            side_effect=RuntimeError("finalizer disabled"),
        ):
            for model_key in sorted(configs):
                with self.subTest(model=model_key):
                    with self.assertRaisesRegex(RuntimeError, "finalizer disabled"):
                        source_assembly.assemble_model_source(configs[model_key])


if __name__ == "__main__":
    unittest.main()
