#!/usr/bin/env bash
# Start the workbook manager (FastAPI backend + built frontend) locally.
#
# Supported serving is SINGLE-PROCESS only. Manager coordination (bootstrap,
# durable-state mutation, candidate promotion, workbook apply) uses one
# process-local lock plus a process-local projection reader gate; a second
# worker process would observe neither. Multi-worker serving is unsupported and
# no distributed locking is added.
set -euo pipefail
cd "$(dirname "$0")/.."

refuse() {
  echo "workbook-manager: refusing $1. Supported serving is single-process only;" >&2
  echo "manager locks and the projection reader gate are process-local." >&2
  exit 2
}

for arg in "$@"; do
  case "$arg" in
    --workers|--workers=*) refuse "'$arg'" ;;
  esac
done

# uvicorn also takes the worker count from the environment when the flag is
# absent (uvicorn/config.py reads WEB_CONCURRENCY), so refusing only argv would
# leave multi-worker serving reachable.
if [[ -n "${WEB_CONCURRENCY:-}" && "${WEB_CONCURRENCY}" != "1" ]]; then
  refuse "WEB_CONCURRENCY=${WEB_CONCURRENCY}"
fi

exec .venv/bin/python -m uvicorn app.main:app \
  --app-dir workbook-manager/backend --port "${WBM_PORT:-8050}" "$@"
