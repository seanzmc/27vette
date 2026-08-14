"""Pass 4 primary-runtime-only generated-contract acceptance regressions."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "workbook-manager" / "backend"
SCRIPTS = ROOT / "scripts"
for path in (BACKEND, SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.contract_parity import (  # noqa: E402
    generate_contract_snapshot,
    promoted_runtime_models,
    validate_primary_runtime_parity,
)
from app import config, db, importer, sync  # noqa: E402

WORKBOOK = ROOT / "stingray_master.xlsx"


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _protected_hashes() -> dict[str, str]:
    paths = [WORKBOOK, ROOT / "form-app" / "data.js"]
    paths.extend(
        sorted(path for path in (ROOT / "form-output").rglob("*") if path.is_file())
    )
    return {str(path.relative_to(ROOT)): _hash(path) for path in paths}


class TestWorkbookManagerGeneratedParity(unittest.TestCase):
    def test_generation_discovery_uses_canonical_default_context(self):
        class DiscoveryObserved(RuntimeError):
            pass

        def observe_discovery(workbook_path, **kwargs):
            self.assertEqual(Path(workbook_path), WORKBOOK)
            self.assertEqual(kwargs, {})
            raise DiscoveryObserved

        with tempfile.TemporaryDirectory(prefix="wbm-pass4-discovery-") as tempdir:
            with mock.patch(
                "app.contract_parity.discover_generation_model_configs",
                side_effect=observe_discovery,
            ), self.assertRaises(DiscoveryObserved):
                generate_contract_snapshot(
                    WORKBOOK,
                    Path(tempdir),
                    "stingray",
                )

    def test_runtime_contract_drift_is_a_blocking_finding(self):
        with tempfile.TemporaryDirectory(prefix="wbm-pass4-drift-") as tempdir:
            root = Path(tempdir)
            source = root / "source.xlsx"
            reconstructed = root / "reconstructed.xlsx"
            source.write_bytes(b"source")
            reconstructed.write_bytes(b"reconstructed")

            def write_contract(workbook_path, output_root, _model_key, **_kwargs):
                output = Path(output_root) / "contract.json"
                output.parent.mkdir(parents=True, exist_ok=True)
                payload = {
                    "generated_at": "ignored",
                    "value": Path(workbook_path).parent.name,
                }
                output.write_text(json.dumps(payload), encoding="utf-8")
                return output

            with mock.patch(
                "app.contract_parity.promoted_runtime_models",
                return_value=("stingray",),
            ), mock.patch(
                "app.contract_parity.generate_contract_snapshot",
                side_effect=write_contract,
            ):
                issues = validate_primary_runtime_parity(source, reconstructed, ROOT)

        self.assertEqual([issue["category"] for issue in issues], ["generated_contract_drift"])

    def test_strict_preflight_rejects_historical_artifact_type(self):
        with tempfile.TemporaryDirectory(prefix="wbm-pass4-preflight-") as tempdir:
            workbook_path = Path(tempdir) / "source.xlsx"
            shutil.copy2(WORKBOOK, workbook_path)
            workbook = load_workbook(workbook_path)
            sheet = workbook["model_registry_promotion"]
            headers = {cell.value: cell.column for cell in sheet[1]}
            model_key_column = headers["model_key"]
            artifact_type_column = headers["artifact_type"]
            assert isinstance(model_key_column, int)
            assert isinstance(artifact_type_column, int)
            for row in range(2, sheet.max_row + 1):
                if sheet.cell(row, model_key_column).value == "stingray":
                    sheet.cell(row, artifact_type_column).value = "current_generation"
                    break
            workbook.save(workbook_path)
            workbook.close()

            with self.assertRaisesRegex(ValueError, "accepts only 'runtime_contract'"):
                promoted_runtime_models(workbook_path, ROOT)

    def test_source_and_identity_reconstruction_runtime_contracts_match(self):
        before = _protected_hashes()
        with tempfile.TemporaryDirectory(prefix="wbm-pass4-parity-") as tempdir:
            temp = Path(tempdir)
            source = temp / "source" / "candidate.xlsx"
            reconstruction = temp / "reconstruction" / "candidate.xlsx"
            source.parent.mkdir()
            reconstruction.parent.mkdir()
            shutil.copy2(WORKBOOK, source)
            projection_path = temp / "projection.sqlite3"
            connection = db.connect(projection_path)
            previous_export_dir = config.EXPORT_DIR
            try:
                db.init_projection_schema(connection)
                import_report = importer.import_workbook(connection, source)
                self.assertFalse(
                    [issue for issue in import_report["issues"] if issue["severity"] == "error"]
                )
                config.EXPORT_DIR = temp / "exports"
                export = sync.export_comparison_workbook(connection, source)
                self.assertTrue(export["ok"], export)
                shutil.copy2(export["path"], reconstruction)
            finally:
                config.EXPORT_DIR = previous_export_dir
                connection.close()
            models = promoted_runtime_models(source, ROOT)
            self.assertEqual(models, ("stingray", "grand_sport", "z06"))

            for model_key in models:
                source_root = temp / "source-output" / model_key
                reconstructed_root = temp / "reconstructed-output" / model_key
                source_contract = generate_contract_snapshot(
                    source, source_root, model_key
                )
                reconstructed_contract = generate_contract_snapshot(
                    reconstruction,
                    reconstructed_root,
                    model_key,
                )
                subprocess.run(
                    [
                        "node",
                        str(ROOT / "scripts" / "compare-generated-contracts.mjs"),
                        str(source_contract),
                        str(reconstructed_contract),
                    ],
                    cwd=ROOT,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(
                    [path.relative_to(source_root).as_posix() for path in source_root.rglob("*") if path.is_file()],
                    [f"form-output/runtime/{source_contract.name}"],
                )
                self.assertEqual(
                    [path.relative_to(reconstructed_root).as_posix() for path in reconstructed_root.rglob("*") if path.is_file()],
                    [f"form-output/runtime/{reconstructed_contract.name}"],
                )
        self.assertEqual(_protected_hashes(), before)


if __name__ == "__main__":
    unittest.main()
