#!/usr/bin/env python3
"""Atomicity of the registry write (spec Pass 3 requirement 9).

`form-app/data.js` is a multi-megabyte file the browser loads unconditionally.
A stale one is survivable; a truncated one is not. These tests prove the write
either lands whole or leaves the previous file exactly as it was — and they are
written so that a plain `path.write_text()` implementation fails them.
"""

from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from corvette_form_generator import output as output_module  # noqa: E402
from corvette_form_generator.output import (  # noqa: E402
    write_app_data_registry,
    write_text_atomic,
)

REGISTRY = {"defaultModelKey": "stingray", "models": {"stingray": {"key": "stingray", "data": {"choices": []}}}}


def test_a_failure_before_the_replace_leaves_the_previous_file_intact(tmp_path, monkeypatch) -> None:
    """The core atomicity property.

    Fails against `path.write_text()`, which truncates the destination before it
    writes a byte — there is no window in which the old content survives.
    """

    target = tmp_path / "data.js"
    target.write_text("window.CORVETTE_FORM_DATA = {\"previous\": true};\n", encoding="utf-8")
    previous = target.read_bytes()

    def explode(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(output_module.os, "replace", explode)
    with pytest.raises(OSError, match="disk full"):
        write_app_data_registry(target, REGISTRY)

    assert target.read_bytes() == previous, "the destination was modified before the atomic replace"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["data.js"], "a temporary file was left behind"


def test_a_failure_while_rendering_never_creates_the_destination(tmp_path) -> None:
    """Breaks if the writer ever opens the target before it has the full payload."""

    target = tmp_path / "nested" / "data.js"

    class Unserializable:
        pass

    with pytest.raises(TypeError):
        write_app_data_registry(target, {"models": Unserializable()})

    assert not target.exists()


def test_the_temporary_file_lands_beside_the_target(tmp_path, monkeypatch) -> None:
    """Same-filesystem staging is what makes the replace work at all.

    ``os.replace`` across filesystems raises OSError(EXDEV) — it never silently
    copies. A temp file in /tmp would therefore make publishing fail outright on
    any host where the repo and /tmp are separate volumes. Breaks if the staging
    directory is ever changed.
    """

    target = tmp_path / "data.js"
    observed: list[Path] = []
    real_replace = output_module.os.replace

    def record(src, dst):
        observed.append(Path(src))
        return real_replace(src, dst)

    monkeypatch.setattr(output_module.os, "replace", record)
    write_app_data_registry(target, REGISTRY)

    assert observed and observed[0].parent == target.parent


def test_the_file_on_disk_is_loadable_javascript_with_the_expected_globals(tmp_path) -> None:
    """Asserts against a literal, not against the same renderer the writer uses.

    Comparing the written file to `render_app_data_registry(...)` would only prove
    nothing mangles the bytes in transit — it could not catch the renderer itself
    emitting the wrong shape.
    """

    target = tmp_path / "data.js"
    write_app_data_registry(target, REGISTRY, legacy_aliases={"STINGRAY_FORM_DATA": "stingray"})
    written = target.read_text(encoding="utf-8")

    assert written.startswith("window.CORVETTE_FORM_DATA = {")
    assert written.endswith(
        "window.STINGRAY_FORM_DATA = window.CORVETTE_FORM_DATA.models.stingray.data;\n"
    )
    payload = written[len("window.CORVETTE_FORM_DATA = ") : written.index(";\nwindow.STINGRAY_FORM_DATA")]
    assert json.loads(payload) == REGISTRY


def test_write_text_atomic_creates_missing_parents(tmp_path) -> None:
    target = tmp_path / "a" / "b" / "data.js"

    write_text_atomic(target, "hello\n")

    assert target.read_text(encoding="utf-8") == "hello\n"


def test_the_destinations_permissions_survive_the_replace(tmp_path) -> None:
    """Breaks if the temp file's 0600 is allowed to become the destination's mode.

    `os.replace` swaps the inode, so without an explicit chmod a browser-served
    `data.js` silently stops being world-readable after the first publish. Git
    does not track this bit, so it would only ever manifest on the publishing host.
    """

    target = tmp_path / "data.js"
    target.write_text("previous\n", encoding="utf-8")
    target.chmod(0o644)

    write_app_data_registry(target, REGISTRY)

    assert stat.S_IMODE(target.stat().st_mode) == 0o644


def test_a_new_file_gets_normal_permissions_not_0600(tmp_path) -> None:
    """Same hazard on first publish, where there is no previous mode to preserve."""

    target = tmp_path / "data.js"

    write_app_data_registry(target, REGISTRY)

    umask = os.umask(0)
    os.umask(umask)
    assert stat.S_IMODE(target.stat().st_mode) == 0o666 & ~umask


def test_the_payload_is_fsynced_before_the_replace(tmp_path, monkeypatch) -> None:
    """Breaks if the fsync is ever dropped.

    Without this, removing `handle.flush()`/`os.fsync()` while keeping same-directory
    staging passes every other test in this file — the durability property would
    have no coverage at all.
    """

    target = tmp_path / "data.js"
    events: list[str] = []
    real_fsync, real_replace = output_module.os.fsync, output_module.os.replace

    monkeypatch.setattr(output_module.os, "fsync", lambda fd: (events.append("fsync"), real_fsync(fd))[1])
    monkeypatch.setattr(output_module.os, "replace", lambda s, d: (events.append("replace"), real_replace(s, d))[1])
    write_app_data_registry(target, REGISTRY)

    assert events[0] == "fsync", "the payload must be fsynced before it replaces the target"
    assert "replace" in events
    assert events.index("fsync") < events.index("replace")
    # And the directory entry is fsynced after, or the rename itself is not durable.
    assert events[events.index("replace") + 1] == "fsync"


def test_a_temp_file_left_by_a_killed_write_is_swept(tmp_path) -> None:
    """Breaks if debris from a SIGKILLed publish is allowed to accumulate.

    SIGKILL cannot be caught, so the `finally` cleanup does not run and a
    full-size temp file stays in the served directory. The next write reaps it.
    """

    target = tmp_path / "data.js"
    debris = tmp_path / ".data.js.abcd1234.tmp"
    debris.write_text("orphaned\n", encoding="utf-8")
    unrelated = tmp_path / ".other.js.abcd1234.tmp"
    unrelated.write_text("not mine\n", encoding="utf-8")

    write_app_data_registry(target, REGISTRY)

    assert not debris.exists()
    assert unrelated.exists(), "the sweep must only reap this destination's own debris"
