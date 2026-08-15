"""Read-only Asset Manager composition and process-local reconciliation cache."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from threading import Lock
from typing import Any

from corvette_form_generator import asset_map_sync


_CACHE_LOCK = Lock()
_CACHE: dict[str, Any] = {}


def _truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _workbook_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fixture_identity(path: Path | None) -> str:
    if path is None:
        return "live"
    stat = path.stat()
    return f"{path.resolve()}:{stat.st_mtime_ns}:{stat.st_size}"


def _media_source() -> tuple[list[str], str, str]:
    configured = os.environ.get("WBM_ASSET_MEDIA_URL_LIST", "").strip()
    if configured:
        path = Path(configured).expanduser().resolve()
        return (
            asset_map_sync.read_media_url_list(path),
            f"media-url-list:{path.name}",
            _fixture_identity(path),
        )
    timeout = float(os.environ.get("WBM_ASSET_MEDIA_TIMEOUT", "10"))
    snapshot = asset_map_sync.fetch_media_stable(timeout=timeout)
    return snapshot.urls, "live-stable-wordpress", "live"


def clear_cache() -> None:
    """Clear the process-local read cache (used by refresh and focused tests)."""

    with _CACHE_LOCK:
        _CACHE.clear()


def get_asset_manager_view(
    workbook_path: Path,
    *,
    refresh: bool = False,
    model_key: str = "",
    section_id: str = "",
    target_type: str = "",
    coverage_intent: str = "",
    status: str = "",
    offset: int = 0,
    limit: int = 24,
) -> dict[str, Any]:
    """Return one filtered page without reproducing reconciliation rules here."""

    configured = os.environ.get("WBM_ASSET_MEDIA_URL_LIST", "").strip()
    fixture_path = Path(configured).expanduser().resolve() if configured else None
    source_identity = _fixture_identity(fixture_path)
    verify_existing = _truthy_env("WBM_ASSET_VERIFY_EXISTING")
    workbook_sha256 = _workbook_sha256(workbook_path)
    cache_key = f"{workbook_path.resolve()}:{workbook_sha256}:{source_identity}:{verify_existing}"

    with _CACHE_LOCK:
        snapshot = None if refresh else _CACHE.get(cache_key)
    if snapshot is None:
        media_urls, media_source, fetched_identity = _media_source()
        if fetched_identity != source_identity:
            source_identity = fetched_identity
            cache_key = f"{workbook_path.resolve()}:{workbook_sha256}:{source_identity}:{verify_existing}"
        snapshot = asset_map_sync.build_asset_manager_snapshot(
            workbook_path,
            media_urls,
            media_source=media_source,
            verify_existing=verify_existing,
            timeout=float(os.environ.get("WBM_ASSET_MEDIA_TIMEOUT", "10")),
            workers=int(os.environ.get("WBM_ASSET_MEDIA_WORKERS", "16")),
        )
        with _CACHE_LOCK:
            _CACHE.clear()
            _CACHE[cache_key] = snapshot

    return asset_map_sync.filter_asset_manager_snapshot(
        snapshot,
        model_key=model_key,
        section_id=section_id,
        target_type=target_type,
        coverage_intent=coverage_intent,
        status=status,
        offset=offset,
        limit=limit,
    )
