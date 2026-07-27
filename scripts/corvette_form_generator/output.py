"""Output helpers shared by model generators."""

from __future__ import annotations

import os
from pathlib import Path
import stat
import tempfile
from typing import Any


def _temp_prefix(name: str) -> str:
    return f".{name}."


def _sweep_stale_temporaries(path: Path) -> None:
    """Remove temp files a previously killed write left behind.

    ``os.replace`` cannot be interrupted, and the ``finally`` below covers every
    exception — but SIGKILL between the write and the replace leaves a full-size
    temp file in the destination directory, and for ``form-app/data.js`` that is
    megabytes in a served directory with nothing to reap it. There is exactly one
    writer per destination, so anything matching the pattern is debris.
    """

    for stale in path.parent.glob(f"{_temp_prefix(path.name)}*.tmp"):
        stale.unlink(missing_ok=True)


def _destination_mode(path: Path) -> int:
    """The mode the replacement should end up with.

    ``NamedTemporaryFile`` creates at 0600 and ``os.replace`` swaps the inode, so
    without this the destination silently loses its permissions — which for a
    browser-served file like ``form-app/data.js`` means it stops being readable by
    anything but the publishing user. Preserve what is there; for a new file use
    what a plain ``open(..., "w")`` would have produced.
    """

    if path.exists():
        return stat.S_IMODE(path.stat().st_mode)
    umask = os.umask(0)
    os.umask(umask)
    return 0o666 & ~umask


def write_text_atomic(path: Path, text: str) -> None:
    """Replace ``path`` with ``text`` in one step, or leave it exactly as it was.

    The destination is never observed partially written: the bytes land in a
    temporary file in the same directory, are fsynced, and only then replace the
    target. Staging in the same directory is required — ``os.replace`` across
    filesystems raises ``OSError(EXDEV)`` rather than falling back to a copy, so a
    temp file elsewhere would make this fail outright.

    This matters most for ``form-app/data.js``: a multi-megabyte file the browser
    loads unconditionally, where a truncated copy is worse than a stale one
    (spec Pass 3 requirement 9).
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    _sweep_stale_temporaries(path)
    mode = _destination_mode(path)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=_temp_prefix(path.name),
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_path, mode)
        os.replace(temporary_path, path)
        temporary_path = None
        # Without this the *rename* is not durable: the data blocks are safe from
        # the fsync above, but a power failure can still lose the directory entry
        # and leave the previous file in place.
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def write_json_output(path: Path, data: dict[str, Any]) -> None:
    write_text_atomic(path, to_pretty_json(data))


def render_app_data_registry(
    registry: dict[str, Any],
    legacy_aliases: dict[str, str] | None = None,
) -> str:
    lines = [f"window.CORVETTE_FORM_DATA = {to_pretty_json(registry)};"]
    for global_name, model_key in (legacy_aliases or {}).items():
        lines.append(f"window.{global_name} = window.CORVETTE_FORM_DATA.models.{model_key}.data;")
    return "\n".join(lines) + "\n"


def write_app_data_registry(
    path: Path,
    registry: dict[str, Any],
    legacy_aliases: dict[str, str] | None = None,
) -> None:
    write_text_atomic(path, render_app_data_registry(registry, legacy_aliases))


def to_pretty_json(data: Any) -> str:
    import json

    return json.dumps(data, indent=2)
