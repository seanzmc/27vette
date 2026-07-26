#!/usr/bin/env python3
"""Safety tests for isolated, fail-closed model generation."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from corvette_form_generator import production  # noqa: E402
from corvette_form_generator import model_generation, output  # noqa: E402
from corvette_form_generator.model_configs import base_model_config  # noqa: E402
from corvette_form_generator.registry_promotion import (  # noqa: E402
    assert_runtime_contract,
    export_slug,
    resolve_artifact_path,
)
from corvette_form_generator.rule_derivation import write_derivation_manifest  # noqa: E402
from corvette_form_generator.rules import extend_with_derived_swap_rules  # noqa: E402
from corvette_form_generator import source_assembly  # noqa: E402
from corvette_form_generator.source_assembly import ModelSourceAssembly  # noqa: E402


REQUIRED_LIST_FIELDS = (
    "variants",
    "steps",
    "sections",
    "contextChoices",
    "choices",
    "standardEquipment",
    "ruleGroups",
    "exclusiveGroups",
    "rules",
    "priceRules",
    "interiors",
    "colorOverrides",
    "defaultSelectionRules",
    "validation",
)


def runtime_contract(*, validation: list[dict[str, str]] | None = None) -> dict[str, object]:
    data: dict[str, object] = {
        "dataset": {
            "name": "2027 Corvette Stingray operational form",
            "model": "Stingray",
            "model_year": "2027",
            "status": "runtime_active",
        },
        "orderSummary": {},
    }
    for field in REQUIRED_LIST_FIELDS:
        data[field] = []
    for field in ("variants", "steps", "sections", "contextChoices", "choices"):
        data[field] = [{"id": f"test-{field}"}]
    data["validation"] = validation or []
    return data


class GenerationPathSafetyTests(unittest.TestCase):
    def test_invalid_model_key_cannot_become_an_artifact_path(self) -> None:
        with self.assertRaisesRegex(ValueError, "Invalid model_key"):
            export_slug("../../tmp/escaped")

    def test_generation_rejects_invalid_model_key_before_assembly_or_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_root = Path(tmpdir)
            config = base_model_config("stingray").with_overrides(
                model_key="../../tmp/escaped",
                root=temp_root / "root",
                output_dir=temp_root / "output",
                app_dir=temp_root / "app",
            )
            with patch.object(model_generation, "assemble_model_source") as assemble:
                with self.assertRaisesRegex(ValueError, "Invalid model_key"):
                    model_generation.generate_model_artifacts(config)

            assemble.assert_not_called()
            self.assertFalse(config.output_dir.exists())

    def test_manifest_writer_rejects_model_key_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_root = Path(tmpdir)
            output_dir = temp_root / "output"
            with self.assertRaisesRegex(ValueError, "Invalid model_key"):
                write_derivation_manifest(output_dir, "../../escaped", {"entries": []})
            self.assertFalse((temp_root / "escaped-derived-swap-manifest.json").exists())

    def test_promoted_artifact_path_must_remain_under_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "root"
            outside = Path(tmpdir) / "outside.json"
            outside_dir = Path(tmpdir) / "outside-dir"
            root.mkdir()
            outside_dir.mkdir()
            (root / "form-output").symlink_to(outside_dir, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "outside root"):
                resolve_artifact_path(root, "../outside.json")
            with self.assertRaisesRegex(ValueError, "outside root"):
                resolve_artifact_path(root, outside)
            with self.assertRaisesRegex(ValueError, "outside root"):
                resolve_artifact_path(root, "form-output/stingray-form-data.json")

    def test_rule_derivation_does_not_write_during_source_assembly(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "form-output"
            config = base_model_config("stingray").with_overrides(output_dir=output_dir)

            manifest = extend_with_derived_swap_rules(config, [], {}, {}, {})

            self.assertEqual(manifest["model_key"], "stingray")
            self.assertFalse(output_dir.exists())

    def test_the_single_source_builder_opens_the_config_workbook(self) -> None:
        """The one builder reads the candidate workbook, never a module global."""

        config = base_model_config("stingray").with_overrides(workbook_path=Path("/tmp/candidate-workbook.xlsx"))

        with patch.object(source_assembly, "load_workbook", side_effect=RuntimeError("stop after path capture")) as loader:
            with self.assertRaisesRegex(RuntimeError, "stop after path capture"):
                source_assembly.assemble_model_source(config)

        loader.assert_called_once_with(config.workbook_path, data_only=True, read_only=True)

    def test_stingray_compatibility_writer_uses_config_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_root = Path(tmpdir)
            target_output = temp_root / "candidate" / "form-output"
            config = base_model_config("stingray").with_overrides(
                root=temp_root / "candidate",
                output_dir=target_output,
                app_dir=temp_root / "candidate" / "form-app",
            )

            artifacts = production.write_stingray_compatibility_artifacts(
                config,
                {"choices": []},
                {"dataset": {"status": "runtime_active"}},
            )

            self.assertEqual(Path(artifacts["json"]), target_output / "stingray-form-data.json")
            self.assertEqual(Path(artifacts["csv"]), target_output / "stingray-form-data.csv")


class RuntimeContractSafetyTests(unittest.TestCase):
    def test_runtime_artifact_uses_config_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_root = Path(tmpdir)
            config = base_model_config("stingray").with_overrides(
                root=temp_root / "root-must-not-own-runtime-output",
                output_dir=temp_root / "explicit-output",
                app_dir=temp_root / "explicit-app",
            )
            contract = runtime_contract()
            assembly = ModelSourceAssembly(
                config=config,
                source_data=contract,
                runtime_contract=contract,
                compatibility_source=True,
            )

            with patch.object(model_generation, "assemble_model_source", return_value=assembly):
                result = model_generation.generate_model_artifacts(config)

            expected = config.output_dir / "runtime" / "stingray-runtime-contract.json"
            self.assertEqual(Path(result["runtime_contract_json"]), expected)
            self.assertTrue(expected.exists())
            self.assertFalse((config.root / "form-output" / "runtime").exists())

    def test_runtime_contract_rejects_incomplete_payloads(self) -> None:
        cases = {
            "empty": {},
            "empty dataset": {"dataset": {}},
            "missing status": {**runtime_contract(), "dataset": {"name": "x", "model": "Stingray", "model_year": "2027"}},
            "missing collection": {key: value for key, value in runtime_contract().items() if key != "choices"},
            "malformed collection row": {**runtime_contract(), "choices": [None]},
            "empty required collection": {**runtime_contract(), "choices": []},
            "missing validation severity": {**runtime_contract(), "validation": [{"message": "missing severity"}]},
            "unknown validation severity": {**runtime_contract(), "validation": [{"severity": "fatal"}]},
        }

        for name, data in cases.items():
            with self.subTest(name=name), self.assertRaises(ValueError):
                assert_runtime_contract(data, source=name)

    def test_runtime_contract_rejects_error_findings(self) -> None:
        data = runtime_contract(
            validation=[{"check_id": "broken_source", "severity": "error", "message": "broken"}]
        )

        with self.assertRaisesRegex(ValueError, "error-severity validation"):
            assert_runtime_contract(data, source="error-bearing contract")

    def test_runtime_contract_accepts_known_info_findings(self) -> None:
        assert_runtime_contract(
            runtime_contract(validation=[{"severity": "info", "message": "known informational finding"}]),
            source="informational contract",
        )

    def test_runtime_contract_rejects_promoted_model_identity_mismatch(self) -> None:
        with self.assertRaisesRegex(ValueError, "dataset.model"):
            assert_runtime_contract(
                runtime_contract(),
                source="synthetic promotion",
                expected_model_label="Grand Sport",
            )

    def test_invalid_generation_writes_no_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "candidate"
            config = base_model_config("stingray").with_overrides(
                root=root,
                output_dir=root / "form-output",
                app_dir=root / "form-app",
            )
            invalid_contract = runtime_contract(
                validation=[{"check_id": "broken_source", "severity": "error", "message": "broken"}]
            )
            assembly = ModelSourceAssembly(
                config=config,
                source_data={
                    **invalid_contract,
                    "contextChoices": [],
                    "standardEquipment": [],
                    "priceRules": [],
                    "interiors": [],
                },
                runtime_contract=invalid_contract,
                compatibility_source=True,
            )

            with patch.object(model_generation, "assemble_model_source", return_value=assembly):
                with self.assertRaisesRegex(ValueError, "error-severity validation"):
                    model_generation.generate_model_artifacts(config)

            self.assertFalse(config.output_dir.exists())

    def test_atomic_json_write_preserves_existing_file_when_replace_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "contract.json"
            path.write_text("original\n", encoding="utf-8")

            with patch("os.replace", side_effect=OSError("replace failed")):
                with self.assertRaisesRegex(OSError, "replace failed"):
                    output.write_json_output(path, {"replacement": True})

            self.assertEqual(path.read_text(encoding="utf-8"), "original\n")
            self.assertEqual(list(path.parent.glob(f".{path.name}.*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
