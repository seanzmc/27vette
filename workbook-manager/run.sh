#!/usr/bin/env bash
# Start the workbook manager (FastAPI backend + built frontend) locally.
set -euo pipefail
cd "$(dirname "$0")/.."
exec .venv/bin/python -m uvicorn app.main:app \
  --app-dir workbook-manager/backend --port "${WBM_PORT:-8050}" "$@"
