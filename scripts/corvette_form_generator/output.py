"""Output helpers shared by model generators."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def write_json_output(path: Path, data: dict[str, Any]) -> None:
    path.write_text(to_pretty_json(data), encoding="utf-8")


def write_app_data(path: Path, global_name: str, data: dict[str, Any]) -> None:
    path.write_text(
        f"window.{global_name} = {to_pretty_json(data)};\n",
        encoding="utf-8",
    )


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
