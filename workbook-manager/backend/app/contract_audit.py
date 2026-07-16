"""Isolated runtime-contract regeneration and exact recursive comparison."""

from __future__ import annotations

import json
import hashlib
import sqlite3
import threading
import weakref
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from openpyxl import load_workbook

from corvette_form_generator.model_configs import discover_generation_model_configs
from corvette_form_generator.model_generation import generate_model_artifacts
from corvette_form_generator.registry_promotion import (
    artifact_path_for_promotion,
    load_registry_promotions,
)

from .catalog import LIVE_MODELS
from .export_adapter import export_comparison_workbook


class _Missing:
    def __repr__(self) -> str:
        return "MISSING"


MISSING = _Missing()
TIMESTAMP_KEYS = frozenset({"generated_at", "sourceGeneratedAt", "generatedAt"})
_AUTHORIZATION_LOCK = threading.Lock()
_AUDIT_AUTHORIZATIONS: dict[
    int, tuple[weakref.ReferenceType["ContractAudit"], Path, str]
] = {}


@dataclass(frozen=True)
class ContractDifference:
    model_key: str
    json_path: str
    baseline_value: object
    candidate_value: object


@dataclass(frozen=True)
class ContractAudit:
    models: tuple[str, ...]
    differences: tuple[ContractDifference, ...]
    generated_paths: Mapping[str, Path]


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _record_audit_authorization(
    audit: ContractAudit, conn: sqlite3.Connection
) -> None:
    database_row = next(
        row for row in conn.execute("PRAGMA database_list") if row[1] == "main"
    )
    candidate = Path(str(database_row[2])).resolve()
    if not candidate.is_file():
        raise ValueError("Contract audit requires a file-backed candidate database")
    identity = id(audit)

    def discard(_reference) -> None:
        with _AUTHORIZATION_LOCK:
            _AUDIT_AUTHORIZATIONS.pop(identity, None)

    reference = weakref.ref(audit, discard)
    with _AUTHORIZATION_LOCK:
        _AUDIT_AUTHORIZATIONS[identity] = (
            reference,
            candidate,
            _file_sha256(candidate),
        )


def consume_audit_authorization(
    audit: ContractAudit, candidate: Path
) -> bool:
    """Consume the one-time receipt minted by this exact audit invocation."""

    with _AUTHORIZATION_LOCK:
        receipt = _AUDIT_AUTHORIZATIONS.pop(id(audit), None)
    if receipt is None:
        return False
    reference, audited_path, audited_sha256 = receipt
    candidate_path = Path(candidate).resolve()
    return (
        reference() is audit
        and audit.models == LIVE_MODELS
        and audit.differences == ()
        and audited_path == candidate_path
        and _file_sha256(candidate_path) == audited_sha256
    )


def discard_audit_authorization(audit: ContractAudit) -> None:
    with _AUTHORIZATION_LOCK:
        _AUDIT_AUTHORIZATIONS.pop(id(audit), None)


def _without_timestamps(value: object) -> object:
    if isinstance(value, dict):
        return {
            key: _without_timestamps(child)
            for key, child in value.items()
            if key not in TIMESTAMP_KEYS
        }
    if isinstance(value, list):
        return [_without_timestamps(child) for child in value]
    return value


def _differences(
    model_key: str,
    baseline: object,
    candidate: object,
    path: str,
) -> list[ContractDifference]:
    if isinstance(baseline, dict) and isinstance(candidate, dict):
        differences: list[ContractDifference] = []
        for key in sorted(set(baseline) | set(candidate)):
            child_path = f"{path}.{key}"
            if key not in baseline:
                differences.append(
                    ContractDifference(model_key, child_path, MISSING, candidate[key])
                )
            elif key not in candidate:
                differences.append(
                    ContractDifference(model_key, child_path, baseline[key], MISSING)
                )
            else:
                differences.extend(
                    _differences(
                        model_key, baseline[key], candidate[key], child_path
                    )
                )
        return differences
    if isinstance(baseline, list) and isinstance(candidate, list):
        differences = []
        for index in range(max(len(baseline), len(candidate))):
            child_path = f"{path}[{index}]"
            if index >= len(baseline):
                differences.append(
                    ContractDifference(model_key, child_path, MISSING, candidate[index])
                )
            elif index >= len(candidate):
                differences.append(
                    ContractDifference(model_key, child_path, baseline[index], MISSING)
                )
            else:
                differences.extend(
                    _differences(
                        model_key, baseline[index], candidate[index], child_path
                    )
                )
        return differences
    if baseline != candidate:
        return [ContractDifference(model_key, path, baseline, candidate)]
    return []


def diff_contracts(
    model_key: str, baseline: object, candidate: object
) -> tuple[ContractDifference, ...]:
    return tuple(
        _differences(
            model_key,
            _without_timestamps(baseline),
            _without_timestamps(candidate),
            "$",
        )
    )


def audit_runtime_contracts(
    conn: sqlite3.Connection,
    source_workbook: Path,
    temp_dir: Path,
) -> ContractAudit:
    """Regenerate every promoted contract below ``temp_dir`` and compare."""

    source_path = Path(source_workbook)
    audit_root = Path(temp_dir)
    audit_root.mkdir(parents=True, exist_ok=True)
    comparison_workbook = export_comparison_workbook(
        conn, source_path, audit_root / source_path.name
    )
    # Promotion membership and baseline paths belong to the immutable source
    # workbook, not to SQL values reconstructed into the comparison copy.
    workbook = load_workbook(source_path, read_only=True, data_only=True)
    try:
        promotions = tuple(load_registry_promotions(workbook))
    finally:
        workbook.close()
    configs = discover_generation_model_configs(comparison_workbook)
    models = tuple(promotion.model_key for promotion in promotions)
    if set(configs) != set(models):
        raise ValueError(
            "Promoted and generatable model sets differ: "
            f"promoted={models!r}, generatable={tuple(configs)!r}"
        )

    differences: list[ContractDifference] = []
    generated_paths: dict[str, Path] = {}
    for promotion in promotions:
        model_root = audit_root / promotion.model_key
        config = configs[promotion.model_key].with_overrides(
            root=model_root,
            workbook_path=comparison_workbook,
            output_dir=model_root / "output",
            app_dir=model_root / "app",
        )
        result = generate_model_artifacts(config)
        generated_path = Path(result["runtime_contract_json"])
        generated_paths[promotion.model_key] = generated_path
        baseline_path = artifact_path_for_promotion(source_path.parent, promotion)
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        candidate = json.loads(generated_path.read_text(encoding="utf-8"))
        differences.extend(
            diff_contracts(promotion.model_key, baseline, candidate)
        )
    audit = ContractAudit(
        models=models,
        differences=tuple(differences),
        generated_paths=generated_paths,
    )
    _record_audit_authorization(audit, conn)
    return audit
