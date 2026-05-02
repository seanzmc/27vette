#!/usr/bin/env python3
"""Build an ignored experimental Stingray app shell using CSV-shadow data."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_APP_DIR = ROOT / "form-app"
DEFAULT_OUT_DIR = ROOT / "build" / "experimental" / "form-app"
OVERLAY_SCRIPT = ROOT / "scripts" / "stingray_csv_shadow_overlay.py"
SHELL_FILES = ("index.html", "app.js", "styles.css")


class BuildError(ValueError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--source-app-dir", default=str(DEFAULT_SOURCE_APP_DIR))
    parser.add_argument("--python", default=sys.executable)
    return parser.parse_args()


def copy_shell_files(source_app_dir: Path, out_dir: Path) -> None:
    for filename in SHELL_FILES:
        source = source_app_dir / filename
        if not source.exists():
            if filename == "styles.css":
                continue
            raise BuildError(f"Required app shell file is missing: {source}.")
        shutil.copyfile(source, out_dir / filename)


def write_shadow_data_js(python_executable: str, out_dir: Path) -> None:
    subprocess.run(
        [
            python_executable,
            str(OVERLAY_SCRIPT),
            "--as-data-js",
            "--out",
            str(out_dir / "data.js"),
        ],
        cwd=ROOT,
        check=True,
    )


def build(source_app_dir: Path, out_dir: Path, python_executable: str) -> None:
    if not source_app_dir.exists():
        raise BuildError(f"Source app directory does not exist: {source_app_dir}.")
    out_dir.mkdir(parents=True, exist_ok=True)
    copy_shell_files(source_app_dir, out_dir)
    write_shadow_data_js(python_executable, out_dir)


def main() -> None:
    args = parse_args()
    try:
        build(Path(args.source_app_dir), Path(args.out_dir), args.python)
        print({"out_dir": str(Path(args.out_dir))})
    except (BuildError, OSError, subprocess.CalledProcessError) as error:
        print(f"experimental app build failed: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
