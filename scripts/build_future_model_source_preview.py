#!/usr/bin/env python3
"""Build non-mutating Z06/ZR1/ZR1X source preview artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from corvette_form_generator.future_model_ingest import (  # noqa: E402
    build_future_model_preview,
    render_preview_markdown,
)
from corvette_form_generator.model_configs import OUTPUT_DIR, WORKBOOK_PATH  # noqa: E402


def main() -> int:
    inspection_dir = OUTPUT_DIR / "inspection"
    inspection_dir.mkdir(parents=True, exist_ok=True)
    json_path = inspection_dir / "future-model-source-preview.json"
    md_path = inspection_dir / "future-model-source-preview.md"

    wb = load_workbook(WORKBOOK_PATH, data_only=True, read_only=False)
    try:
        preview = build_future_model_preview(wb)
    finally:
        wb.close()

    json_path.write_text(json.dumps(preview, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(render_preview_markdown(preview), encoding="utf-8")

    print(f"Wrote {json_path.relative_to(ROOT)}")
    print(f"Wrote {md_path.relative_to(ROOT)}")
    print("Workbook source sheets were not written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
