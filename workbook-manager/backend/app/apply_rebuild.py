"""One rollback-protected Apply and Rebuild post-write pipeline.

The shared workbook service remains the only writer.  This module owns the
Manager's downstream boundary: prepare a durable rollback set before the
writer runs, generate affected promoted models in an isolated root, publish
only a complete candidate, and restore/hash-verify every protected path when a
downstream step fails.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from openpyxl import load_workbook

from corvette_form_generator.model_configs import discover_generation_model_configs
from corvette_form_generator.model_generation import generate_model_artifacts
from corvette_form_generator.registry_promotion import (
    export_slug,
    load_registry_promotions,
)
from corvette_form_generator.workbook import restore_workbook_backup
from generate_registry import generate_registry


EVIDENCE_SCHEMA = "workbook-manager-apply-rebuild-1"
_CACHE_PATTERN = re.compile(r'(src="\./data\.js\?v=)(\d+)(")')


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-._") or "draft"


def _model_paths(root: Path, model: str) -> list[Path]:
    slug = export_slug(model)
    return [
        root / "form-output" / "runtime" / f"{slug}-runtime-contract.json",
        root / "form-output" / "inspection" / f"{slug}-derived-swap-manifest.json",
    ]


def _protected_paths(
    *, workbook_path: Path, repository_root: Path, candidate_models: Iterable[str]
) -> list[Path]:
    result = [Path(workbook_path)]
    for model in sorted(set(candidate_models)):
        result.extend(_model_paths(repository_root, model))
    result.extend([
        repository_root / "form-app" / "data.js",
        repository_root / "form-app" / "index.html",
    ])
    seen: set[Path] = set()
    return [path for path in result if not (path in seen or seen.add(path))]


@dataclass(frozen=True)
class RollbackSet:
    id: str
    draft_id: str
    root: Path
    manifest_path: Path
    workbook_path: Path
    repository_root: Path
    candidate_models: tuple[str, ...]
    requested_by: str
    entries: tuple[dict[str, Any], ...]


def prepare_rollback_set(
    *,
    draft_id: str,
    workbook_path: Path,
    repository_root: Path,
    rollback_root: Path,
    candidate_models: Iterable[str],
    requested_by: str = "",
) -> RollbackSet:
    """Create and hash-verify a durable pre-apply workbook/output snapshot."""

    workbook_path = Path(workbook_path).resolve()
    repository_root = Path(repository_root).resolve()
    rollback_id = f"{_safe_id(draft_id)}-{uuid.uuid4().hex}"
    root = Path(rollback_root).resolve() / rollback_id
    files_dir = root / "files"
    files_dir.mkdir(parents=True, exist_ok=False)
    models = tuple(sorted(set(str(model) for model in candidate_models if str(model))))
    entries: list[dict[str, Any]] = []
    for index, source in enumerate(_protected_paths(
        workbook_path=workbook_path,
        repository_root=repository_root,
        candidate_models=models,
    )):
        existed = source.exists()
        suffix = source.suffix if source.suffix else ".bin"
        backup = files_dir / f"{index:04d}{suffix}"
        entry: dict[str, Any] = {
            "path": str(source),
            "existed": existed,
            "sha256": _sha256(source) if existed else "",
            "mtime_ns": str(source.stat().st_mtime_ns) if existed else "",
            "backup": str(backup) if existed else "",
        }
        if existed:
            shutil.copy2(source, backup)
            if _sha256(backup) != entry["sha256"]:
                raise RuntimeError(f"rollback copy verification failed for {source}")
        entries.append(entry)
    manifest = {
        "schemaVersion": EVIDENCE_SCHEMA,
        "id": rollback_id,
        "draft_id": draft_id,
        "created_at": _now(),
        "workbook_path": str(workbook_path),
        "repository_root": str(repository_root),
        "candidate_models": list(models),
        "requested_by": requested_by,
        "entries": entries,
    }
    manifest_path = root / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with manifest_path.open("rb") as handle:
        os.fsync(handle.fileno())
    return RollbackSet(
        id=rollback_id,
        draft_id=draft_id,
        root=root,
        manifest_path=manifest_path,
        workbook_path=workbook_path,
        repository_root=repository_root,
        candidate_models=models,
        requested_by=requested_by,
        entries=tuple(entries),
    )


def derive_affected_models(
    operations: Iterable[dict[str, Any]], *, promoted_models: Iterable[str]
) -> list[str]:
    """Derive impact from stored operation ownership, never selected UI state."""

    promoted = {str(model) for model in promoted_models if str(model)}
    owned: set[str] = set()
    for operation in operations:
        model_id = str(operation.get("model_id") or "")
        if model_id and model_id != "*":
            owned.add(model_id)
        owned.update(
            str(model)
            for model in (operation.get("model_context") or [])
            if str(model) and str(model) != "*"
        )
    return sorted(owned & promoted)


def _canonical_generate_candidate(
    *,
    candidate_root: Path,
    workbook_path: Path,
    repository_root: Path,
    operations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Run the existing model and registry owners in an isolated output root."""

    source_output = repository_root / "form-output"
    candidate_output = candidate_root / "form-output"
    if source_output.exists():
        shutil.copytree(source_output, candidate_output, dirs_exist_ok=True)
    wb = load_workbook(workbook_path, read_only=True, data_only=True)
    try:
        promotions = load_registry_promotions(wb)
    finally:
        wb.close()
    promoted_models = [promotion.model_key for promotion in promotions]
    affected_models = derive_affected_models(
        operations, promoted_models=promoted_models
    )
    if not affected_models:
        raise RuntimeError(
            "approved operations resolve no affected promoted model for regeneration"
        )
    configs = discover_generation_model_configs(workbook_path, root=candidate_root)
    generated_paths: list[str] = []
    generation_results: list[dict[str, Any]] = []
    for model in affected_models:
        config = configs.get(model)
        if config is None:
            raise RuntimeError(f"affected promoted model {model!r} is not generatable")
        generation_results.append(generate_model_artifacts(config))
        for path in _model_paths(candidate_root, model):
            if path.exists():
                generated_paths.append(str(path))
        runtime_path = _model_paths(candidate_root, model)[0]
        if not runtime_path.exists():
            raise RuntimeError(f"generator did not produce {runtime_path}")
    registry_result = generate_registry(
        workbook_path=workbook_path,
        root=candidate_root,
    )
    return {
        "promoted_models": promoted_models,
        "affected_models": affected_models,
        "generated_paths": generated_paths,
        "generation_results": generation_results,
        "registry_path": registry_result["output"],
        "registry_result": registry_result,
    }


def _atomic_write(path: Path, content: bytes, *, mtime_ns: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False
    ) as handle:
        temp = Path(handle.name)
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        if path.exists():
            os.chmod(temp, path.stat().st_mode)
        if mtime_ns is not None:
            os.utime(temp, ns=(mtime_ns, mtime_ns))
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def _bumped_index(index_path: Path) -> tuple[bytes, int, int]:
    text = index_path.read_text(encoding="utf-8")
    match = _CACHE_PATTERN.search(text)
    if not match:
        raise RuntimeError(f"Could not find data.js cache version in {index_path}")
    before = int(match.group(2))
    after = before + 1
    replacement = f"{match.group(1)}{after}{match.group(3)}"
    return (
        (text[: match.start()] + replacement + text[match.end() :]).encode("utf-8"),
        before,
        after,
    )


def _restore_rollback_set(rollback: RollbackSet) -> dict[str, Any]:
    restored: list[dict[str, Any]] = []
    errors: list[str] = []
    workbook_entry = next(
        entry for entry in rollback.entries if entry["path"] == str(rollback.workbook_path)
    )
    ordered = [workbook_entry] + [
        entry for entry in rollback.entries if entry is not workbook_entry
    ]
    for entry in ordered:
        target = Path(entry["path"])
        try:
            if not entry["existed"]:
                target.unlink(missing_ok=True)
                verified = not target.exists()
                observed = ""
            else:
                backup = Path(entry["backup"])
                if target == rollback.workbook_path:
                    restore_workbook_backup(target, backup)
                else:
                    _atomic_write(
                        target,
                        backup.read_bytes(),
                        mtime_ns=int(entry["mtime_ns"]),
                    )
                observed = _sha256(target)
                verified = observed == entry["sha256"]
            restored.append({
                "path": str(target),
                "expected_sha256": entry["sha256"],
                "observed_sha256": observed,
                "verified": verified,
            })
            if not verified:
                errors.append(f"restored hash mismatch for {target}")
        except Exception as exc:  # restoration failures must be reported, not hidden
            errors.append(f"{target}: {type(exc).__name__}: {exc}")
            restored.append({
                "path": str(target),
                "expected_sha256": entry["sha256"],
                "observed_sha256": _sha256(target) if target.exists() else "",
                "verified": False,
            })
    return {
        "state": "verified" if not errors else "unknown",
        "verified": not errors,
        "files": restored,
        "errors": errors,
    }


def complete_apply_rebuild(
    receipt: dict[str, Any],
    *,
    rollback: RollbackSet,
    operations: list[dict[str, Any]],
    workbook_path: Path,
    repository_root: Path,
    generate_candidate: Callable[..., dict[str, Any]] = _canonical_generate_candidate,
) -> dict[str, Any]:
    """Finish one exact applied receipt or return a restoration-bound failure."""

    workbook_path = Path(workbook_path).resolve()
    repository_root = Path(repository_root).resolve()
    result = dict(receipt)
    started = _now()
    try:
        with tempfile.TemporaryDirectory(prefix="wbm-apply-rebuild-candidate-") as raw:
            candidate_root = Path(raw)
            generated = generate_candidate(
                candidate_root=candidate_root,
                workbook_path=workbook_path,
                repository_root=repository_root,
                operations=operations,
            )
            affected_models = list(generated["affected_models"])
            generated_evidence: list[dict[str, Any]] = []
            for candidate_text in generated.get("generated_paths", []):
                candidate = Path(candidate_text)
                relative = candidate.relative_to(candidate_root)
                target = repository_root / relative
                before_sha = _sha256(target) if target.exists() else ""
                candidate_sha = _sha256(candidate)
                _atomic_write(target, candidate.read_bytes())
                observed = _sha256(target)
                if observed != candidate_sha:
                    raise RuntimeError(f"published generated hash mismatch for {target}")
                generated_evidence.append({
                    "path": str(target),
                    "before_sha256": before_sha,
                    "candidate_sha256": candidate_sha,
                    "published_sha256": observed,
                    "changed": before_sha != candidate_sha,
                })

            candidate_registry = Path(generated["registry_path"])
            registry_target = repository_root / "form-app" / "data.js"
            index_target = repository_root / "form-app" / "index.html"
            registry_before = _sha256(registry_target) if registry_target.exists() else ""
            registry_candidate = _sha256(candidate_registry)
            registry_changed = registry_before != registry_candidate
            cache_before = cache_after = None
            if registry_changed:
                index_content, cache_before, cache_after = _bumped_index(index_target)
                _atomic_write(registry_target, candidate_registry.read_bytes())
                _atomic_write(index_target, index_content)
            registry_published = _sha256(registry_target)
            if registry_published != registry_candidate:
                raise RuntimeError("published registry hash does not match candidate")
            workbook_after = _sha256(workbook_path)
            result["applyRebuild"] = {
                "schemaVersion": EVIDENCE_SCHEMA,
                "status": "current",
                "started_at": started,
                "completed_at": _now(),
                "affected_models": affected_models,
                "requested_by": rollback.requested_by,
                "rollback_set": {
                    "id": rollback.id,
                    "manifest": str(rollback.manifest_path),
                    "state": "verified_before_apply",
                },
                "workbook": {
                    "state": "applied",
                    "before_sha256": next(
                        entry["sha256"] for entry in rollback.entries
                        if entry["path"] == str(workbook_path)
                    ),
                    "after_sha256": workbook_after,
                    "package": "valid",
                    "schema": "valid",
                    "saved_row_readback": "verified",
                },
                "projection": {
                    "state": "stale",
                    "reason": "canonical workbook changed after the imported projection",
                },
                "generated_contracts": {
                    "state": "current",
                    "files": generated_evidence,
                },
                "publication": {
                    "state": "current",
                    "path": str(registry_target),
                    "before_sha256": registry_before,
                    "candidate_sha256": registry_candidate,
                    "published_sha256": registry_published,
                    "changed": registry_changed,
                    "cache_version_before": cache_before,
                    "cache_version_after": cache_after,
                },
                "rollback": {"state": "not_required", "verified": True, "files": []},
            }
            return result
    except Exception as exc:
        rollback_result = _restore_rollback_set(rollback)
        restored = rollback_result["verified"]
        result.update({
            "ok": False,
            "status": (
                "apply_rebuild_failed_rolled_back"
                if restored else "apply_rebuild_failed_restore_unknown"
            ),
            "workbookState": "restored" if restored else "unknown",
            "errors": [
                *(receipt.get("errors") or []),
                f"{type(exc).__name__}: {exc}",
                *rollback_result["errors"],
            ],
            "applyRebuild": {
                "schemaVersion": EVIDENCE_SCHEMA,
                "status": "restored" if restored else "unknown",
                "started_at": started,
                "completed_at": _now(),
                "affected_models": [],
                "requested_by": rollback.requested_by,
                "rollback_set": {
                    "id": rollback.id,
                    "manifest": str(rollback.manifest_path),
                    "state": "verified_before_apply",
                },
                "workbook": {"state": "restored" if restored else "unknown"},
                "projection": {"state": "current" if restored else "unknown"},
                "generated_contracts": {"state": "restored" if restored else "unknown"},
                "publication": {"state": "restored" if restored else "unknown"},
                "rollback": rollback_result,
            },
        })
        return result


def output_status(state_conn, *, workbook_path: Path, repository_root: Path) -> dict[str, dict[str, Any]]:
    """Verify current generated/publication hashes against latest success evidence."""

    row = state_conn.execute(
        "SELECT result_json FROM draft_apply_attempts "
        "WHERE manager_state='applied' AND active=0 ORDER BY completed_ts DESC, rowid DESC LIMIT 1"
    ).fetchone()
    fallback = {
        "generated_artifacts": {"state": "unverified", "reason": "no successful Apply and Rebuild evidence"},
        "publication": {"state": "unverified", "reason": "no successful Apply and Rebuild evidence"},
    }
    if row is None or not row["result_json"]:
        return fallback
    payload = json.loads(row["result_json"])
    evidence = payload.get("applyRebuild") or {}
    if evidence.get("status") != "current":
        return fallback
    expected_workbook = (evidence.get("workbook") or {}).get("after_sha256", "")
    if not Path(workbook_path).exists() or _sha256(Path(workbook_path)) != expected_workbook:
        reason = "workbook identity no longer matches the successful Apply and Rebuild"
        return {
            "generated_artifacts": {"state": "stale", "reason": reason},
            "publication": {"state": "stale", "reason": reason},
        }
    generated_files = (evidence.get("generated_contracts") or {}).get("files") or []
    generated_current = all(
        Path(item["path"]).exists()
        and _sha256(Path(item["path"])) == item["published_sha256"]
        for item in generated_files
    )
    publication = evidence.get("publication") or {}
    publication_path = Path(publication.get("path") or repository_root / "form-app" / "data.js")
    publication_current = (
        publication_path.exists()
        and _sha256(publication_path) == publication.get("published_sha256")
    )
    return {
        "generated_artifacts": {
            "state": "current" if generated_current else "stale",
            "affected_models": evidence.get("affected_models") or [],
            "files": generated_files,
        },
        "publication": {
            "state": "current" if publication_current else "stale",
            **publication,
        },
    }
