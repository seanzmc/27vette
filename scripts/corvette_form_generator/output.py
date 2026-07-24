"""Output helpers shared by model generators."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
from typing import Any


def write_json_output(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(to_pretty_json(data))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def write_app_data_registry(
    path: Path,
    registry: dict[str, Any],
    legacy_aliases: dict[str, str] | None = None,
) -> None:
    lines = [f"window.CORVETTE_FORM_DATA = {to_pretty_json(registry)};"]
    for global_name, model_key in (legacy_aliases or {}).items():
        lines.append(f"window.{global_name} = window.CORVETTE_FORM_DATA.models.{model_key}.data;")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def to_pretty_json(data: Any) -> str:
    import json

    return json.dumps(data, indent=2)
