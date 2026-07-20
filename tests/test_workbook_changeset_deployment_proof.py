#!/usr/bin/env python3
"""ChangeSet-aware temporary deployment-proof contract tests."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import prove_workbook_changeset as cli  # noqa: E402
import corvette_form_generator.workbook_domain.deployment_proof as proof_module  # noqa: E402
from corvette_form_generator import workbook_domain  # noqa: E402
from corvette_form_generator.workbook_domain.changeset import (  # noqa: E402
    changeset_fingerprint,
)


@pytest.fixture(autouse=True)
def _accept_synthetic_compiler_artifact_graph(monkeypatch):
    monkeypatch.setattr(
        proof_module,
        "validate_artifact_graph",
        lambda _manifest, _report: None,
    )


def _changeset(workbook: Path) -> dict:
    rows = []
    for index, model in enumerate(("grand_sport_x", "zr1", "zr1x", "*")):
        key_model = "shared" if model == "*" else model
        rows.append(
            {
                "action": "add",
                "sheet": "model_master",
                "family": "model_master",
                "key": {"model_key": key_model},
                "fields": {
                    "model_key": {"before": None, "after": key_model},
                    "display_name": {"before": None, "after": key_model},
                },
                "provenance": [
                    {
                        "kind": "manifest",
                        "id": f"manifest-{index:05d}",
                        "manifestRef": f"manifest-{index:05d}",
                    }
                ],
            }
        )
    payload = {
        "schemaVersion": "workbook-changeset-1",
        "source": {"kind": "ingest", "runId": "fixture-run"},
        "targets": ["grand_sport_x", "zr1", "zr1x"],
        "workbook": {
            "sha256": hashlib.sha256(workbook.read_bytes()).hexdigest(),
            "mtimeNs": str(workbook.stat().st_mtime_ns),
        },
        "sheetCreates": [],
        "rowChanges": rows,
        "noops": [],
        "warningAcknowledgementsRequested": [],
        "bindings": {
            "canonicalManifestSha": "manifest-file-sha",
            "canonicalManifestSemanticSha": "manifest-semantic",
            "runAuthorityFingerprint": {"fingerprint": "authority"},
            "compilerBindings": {"compileReportSha": "compile-report-file-sha"},
        },
    }
    payload["semanticFingerprint"] = changeset_fingerprint(payload)
    payload["changeSetId"] = payload["semanticFingerprint"][:24]
    return payload


def _manifest() -> dict:
    models = ("grand_sport_x", "zr1", "zr1x", "*")
    return {
        "schemaVersion": "canonical-row-manifest-v1",
        "manifestSemanticSha": "manifest-semantic",
        "modelModes": {
            "grand_sport_x": "greenfield",
            "zr1": "reprocess",
            "zr1x": "reprocess",
        },
        "rows": [
            {
                "model": model,
                "family": "model_master",
                "sheet": "model_master",
                "action": "add",
                "key": {"model_key": "shared" if model == "*" else model},
                "values": {
                    "model_key": "shared" if model == "*" else model,
                    "display_name": "shared" if model == "*" else model,
                },
                "status": "ready",
                "semanticSignature": {"fixture": model},
                "derivationVersion": "fixture",
            }
            for model in models
        ],
    }


def _compile_report() -> dict:
    return {
        "models": {
            "grand_sport_x": {
                "mode": "greenfield",
                "compileReady": True,
                "blockers": [],
            },
            "zr1": {"mode": "reprocess", "compileReady": True, "blockers": []},
            "zr1x": {"mode": "reprocess", "compileReady": True, "blockers": []},
        },
        "deferrals": [],
        "sourceFeatureCoverage": [
            {
                "featureId": f"fixture:{model}",
                "model": model,
                "family": "options",
                "disposition": "compiled",
                "evidenceIds": ["fixture"],
            }
            for model in ("grand_sport_x", "zr1", "zr1x")
        ],
    }


def _prove(
    tmp_path: Path,
    workbook: Path,
    *,
    changeset: dict | None = None,
    manifest: dict | None = None,
    report: dict | None = None,
    manifest_binding: str | None = None,
    report_binding: str | None = None,
) -> dict:
    manifest_path = tmp_path / "canonical-row-manifest.json"
    report_path = tmp_path / "compile-report.json"
    manifest_path.write_text(json.dumps(manifest or _manifest()), encoding="utf-8")
    report_path.write_text(json.dumps(report or _compile_report()), encoding="utf-8")
    payload = changeset or _changeset(workbook)
    payload["bindings"]["canonicalManifestSha"] = manifest_binding or hashlib.sha256(
        manifest_path.read_bytes()
    ).hexdigest()
    payload["bindings"]["compilerBindings"]["compileReportSha"] = (
        report_binding or hashlib.sha256(report_path.read_bytes()).hexdigest()
    )
    payload["semanticFingerprint"] = changeset_fingerprint(payload)
    payload["changeSetId"] = payload["semanticFingerprint"][:24]
    return proof_module.prove_changeset_deployment(
        workbook,
        payload,
        canonical_manifest_path=manifest_path,
        compile_report_path=report_path,
    )


def test_changeset_proof_runs_exact_ordered_target_phases(tmp_path, monkeypatch):
    workbook = tmp_path / "master.xlsx"
    workbook.write_bytes(b"fixture workbook bytes")
    changeset = _changeset(workbook)
    seen: list[tuple[list[str], list[str]]] = []

    monkeypatch.setattr(proof_module.editor_ops, "extract_workbook", lambda _path: {})

    def batch_for_phase(phase_changeset, _extract):
        return {
            "items": [
                change["key"]["model_key"]
                for change in phase_changeset["rowChanges"]
            ]
        }

    monkeypatch.setattr(proof_module, "changeset_to_editor_batch", batch_for_phase)

    def probe(_self, _workbook, batch, context, *, schema_validation):
        assert schema_validation is True
        models = list(context["targets"])
        assert all(
            row["canonicalValues"] == row["values"]
            for row in context["coverage"]["manifestRows"]
        )
        assert context["sourceFeatureCoverage"]["semanticSha"]
        assert all(
            context["sourceFeatureCoverage"]["byModel"][model]["featureCount"] == 1
            for model in models
        )
        seen.append((models, list(batch["items"])))
        return {
            model: {
                "status": "deployment_probe_passed",
                "deploymentBlockers": [],
                "deploymentDeferrals": [],
            }
            for model in models
        }

    monkeypatch.setattr(
        proof_module.TemporaryDeploymentProofMixin,
        "_deployment_continuity_probe",
        probe,
    )

    result = _prove(tmp_path, workbook, changeset=changeset)

    assert result["ok"] is True
    assert result["status"] == "deployment_proof_passed"
    assert [phase["phaseId"] for phase in result["phases"]] == [
        "grand_sport_x_plus_zr1",
        "zr1x_repeatability",
        "all_targets_atomic",
    ]
    assert seen == [
        (["grand_sport_x", "zr1"], ["grand_sport_x", "zr1", "shared"]),
        (["zr1x"], ["zr1x", "shared"]),
        (
            ["grand_sport_x", "zr1", "zr1x"],
            ["grand_sport_x", "zr1", "zr1x", "shared"],
        ),
    ]
    assert result["semanticFingerprint"] == changeset["semanticFingerprint"]
    assert result["proofFingerprint"]


def test_changeset_proof_refuses_manifest_binding_mismatch(tmp_path):
    workbook = tmp_path / "master.xlsx"
    workbook.write_bytes(b"fixture workbook bytes")
    manifest = _manifest()
    manifest["manifestSemanticSha"] = "different"

    result = _prove(tmp_path, workbook, manifest=manifest)

    assert result["ok"] is False
    assert result["status"] == "binding_mismatch"
    assert "manifest" in result["errors"][0].lower()


def test_changeset_proof_refuses_invalid_compiler_artifact_graph(tmp_path, monkeypatch):
    workbook = tmp_path / "master.xlsx"
    workbook.write_bytes(b"fixture workbook bytes")

    def reject(_manifest, _report):
        raise ValueError("Canonical manifest semantic hash mismatch.")

    monkeypatch.setattr(proof_module, "validate_artifact_graph", reject)
    result = _prove(tmp_path, workbook)

    assert result["ok"] is False
    assert result["status"] == "binding_mismatch"
    assert "semantic hash mismatch" in result["errors"][0].lower()


def test_changeset_proof_refuses_non_ready_target(tmp_path):
    workbook = tmp_path / "master.xlsx"
    workbook.write_bytes(b"fixture workbook bytes")
    report = _compile_report()
    report["models"]["zr1x"]["compileReady"] = False

    result = _prove(tmp_path, workbook, report=report)

    assert result["ok"] is False
    assert result["status"] == "compiler_not_ready"
    assert "zr1x" in result["errors"][0]


def test_workbook_domain_exports_changeset_deployment_proof():
    assert workbook_domain.prove_changeset_deployment is proof_module.prove_changeset_deployment


def test_changeset_proof_refuses_file_hash_binding_mismatch(tmp_path):
    workbook = tmp_path / "master.xlsx"
    workbook.write_bytes(b"fixture workbook bytes")

    result = _prove(tmp_path, workbook, manifest_binding="wrong")

    assert result["ok"] is False
    assert result["status"] == "binding_mismatch"
    assert "file sha" in result["errors"][0].lower()


def test_changeset_proof_refuses_row_without_manifest_or_scaffold_model(tmp_path):
    workbook = tmp_path / "master.xlsx"
    workbook.write_bytes(b"fixture workbook bytes")
    changeset = _changeset(workbook)
    changeset["rowChanges"][0]["provenance"] = [
        {"kind": "fixture", "id": "unbound"}
    ]
    changeset["semanticFingerprint"] = changeset_fingerprint(changeset)
    changeset["changeSetId"] = changeset["semanticFingerprint"][:24]

    result = _prove(tmp_path, workbook, changeset=changeset)

    assert result["ok"] is False
    assert result["status"] == "phase_projection_invalid"
    assert "model authority" in result["errors"][0].lower()


def test_changeset_proof_refuses_mixed_or_unrecognized_provenance(tmp_path):
    workbook = tmp_path / "master.xlsx"
    workbook.write_bytes(b"fixture workbook bytes")
    changeset = _changeset(workbook)
    changeset["rowChanges"][0]["provenance"].append(
        {"kind": "fixture", "id": "unrecognized-extra-authority"}
    )
    changeset["semanticFingerprint"] = changeset_fingerprint(changeset)
    changeset["changeSetId"] = changeset["semanticFingerprint"][:24]

    result = _prove(tmp_path, workbook, changeset=changeset)

    assert result["ok"] is False
    assert result["status"] == "phase_projection_invalid"


def test_changeset_proof_refuses_incomplete_manifest_coverage(tmp_path):
    workbook = tmp_path / "master.xlsx"
    workbook.write_bytes(b"fixture workbook bytes")
    changeset = _changeset(workbook)
    changeset["rowChanges"].pop()
    changeset["semanticFingerprint"] = changeset_fingerprint(changeset)
    changeset["changeSetId"] = changeset["semanticFingerprint"][:24]

    result = _prove(tmp_path, workbook, changeset=changeset)

    assert result["ok"] is False
    assert result["status"] == "phase_projection_invalid"
    assert "manifest coverage" in result["errors"][0].lower()


def test_changeset_proof_refuses_manifest_reference_swapped_between_rows(tmp_path):
    workbook = tmp_path / "master.xlsx"
    workbook.write_bytes(b"fixture workbook bytes")
    changeset = _changeset(workbook)
    first = changeset["rowChanges"][0]["provenance"][0]
    second = changeset["rowChanges"][2]["provenance"][0]
    first["id"], second["id"] = second["id"], first["id"]
    first["manifestRef"], second["manifestRef"] = (
        second["manifestRef"],
        first["manifestRef"],
    )

    result = _prove(tmp_path, workbook, changeset=changeset)

    assert result["ok"] is False
    assert result["status"] == "phase_projection_invalid"
    assert "does not match its manifest row" in result["errors"][0].lower()


def test_changeset_proof_requires_exact_task8_targets(tmp_path):
    workbook = tmp_path / "master.xlsx"
    workbook.write_bytes(b"fixture workbook bytes")
    changeset = _changeset(workbook)
    changeset["targets"] = ["zr1x"]
    manifest = _manifest()
    manifest["modelModes"] = {"zr1x": "reprocess"}
    report = _compile_report()
    report["models"] = {"zr1x": report["models"]["zr1x"]}

    result = _prove(
        tmp_path,
        workbook,
        changeset=changeset,
        manifest=manifest,
        report=report,
    )

    assert result["ok"] is False
    assert result["status"] == "binding_mismatch"
    assert "exact task 8 targets" in result["errors"][0].lower()


def test_runtime_signature_check_skips_rules_with_hidden_runtime_endpoint():
    rule_row = {
        "model": "zr1",
        "family": "rule_mapping",
        "action": "add",
        "key": {"rule_id": "rule-hidden-target"},
        "canonicalValues": {
            "rule_id": "rule-hidden-target",
            "source_id": "opt_visible",
            "target_id": "opt_hidden",
            "rule_type": "includes",
            "body_style_scope": "",
        },
    }
    hidden_option_row = {
        "model": "zr1",
        "family": "options",
        "action": "add",
        "key": {"option_id": "opt_hidden"},
        "canonicalValues": {
            "option_id": "opt_hidden",
            "active": True,
            "selectable": False,
        },
    }
    plan = {
        "coverage": {
            "manifestRows": [
                rule_row,
                {
                    "model": "zr1",
                    "family": "options",
                    "action": "add",
                    "key": {"option_id": "opt_visible"},
                    "canonicalValues": {
                        "option_id": "opt_visible",
                        "active": True,
                        "selectable": True,
                    },
                },
                hidden_option_row,
            ]
        }
    }
    contract = {
        "choices": [{"option_id": "opt_visible", "rpo": "VIS"}],
        "interiors": [],
        "rules": [],
        "ruleGroups": [],
        "exclusiveGroups": [],
        "defaultSelectionRules": [],
        "priceRules": [],
    }
    engine = proof_module.TemporaryDeploymentProofMixin()

    assert engine._manifest_runtime_signature_mismatches(plan, "zr1", contract) == []

    del hidden_option_row["canonicalValues"]["selectable"]
    assert engine._manifest_runtime_signature_mismatches(plan, "zr1", contract) == [
        {
            "family": "rule_mapping",
            "key": {"rule_id": "rule-hidden-target"},
            "kind": "generated_row_missing",
        }
    ]

    hidden_option_row["canonicalValues"]["selectable"] = True
    assert engine._manifest_runtime_signature_mismatches(plan, "zr1", contract) == [
        {
            "family": "rule_mapping",
            "key": {"rule_id": "rule-hidden-target"},
            "kind": "generated_row_missing",
        }
    ]


def test_deployment_proof_cli_writes_exact_receipt(tmp_path, monkeypatch):
    workbook = tmp_path / "master.xlsx"
    workbook.write_bytes(b"fixture workbook bytes")
    changeset_path = tmp_path / "changeset.json"
    manifest_path = tmp_path / "manifest.json"
    report_path = tmp_path / "compile-report.json"
    proof_path = tmp_path / "deployment-proof.json"
    changeset_path.write_text(json.dumps(_changeset(workbook)))
    manifest_path.write_text(json.dumps(_manifest()))
    report_path.write_text(json.dumps(_compile_report()))
    expected = {
        "ok": True,
        "status": "deployment_proof_passed",
        "proofFingerprint": "proof-sha",
    }

    monkeypatch.setattr(
        cli,
        "prove_changeset_deployment",
        lambda *args, **kwargs: expected,
    )

    result = cli.main(
        [
            str(changeset_path),
            "--workbook",
            str(workbook),
            "--manifest",
            str(manifest_path),
            "--compile-report",
            str(report_path),
            "--proof-out",
            str(proof_path),
        ]
    )

    assert result == 0
    assert json.loads(proof_path.read_text()) == expected
