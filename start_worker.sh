#!/usr/bin/env bash
set -euo pipefail

SERVER_URL="${NOVA_SCHOOL_SERVER_URL:-http://127.0.0.1:8877}"
WORKER_ID="${NOVA_SCHOOL_WORKER_ID:-lab-node-01}"
WORKER_TOKEN="${NOVA_SCHOOL_WORKER_TOKEN:-}"
ADVERTISE_HOST="${NOVA_SCHOOL_WORKER_HOST:-}"
WORK_ROOT="${NOVA_SCHOOL_WORKER_ROOT:-$HOME/.nova-school-worker}"

if [ -z "$WORKER_TOKEN" ]; then
  echo "Setze NOVA_SCHOOL_WORKER_TOKEN vor dem Start des Worker-Agenten." >&2
  exit 1
fi

ARGS=(
  -m nova_school_server.worker_agent
  --server "$SERVER_URL"
  --worker-id "$WORKER_ID"
  --token "$WORKER_TOKEN"
  --work-root "$WORK_ROOT"
)

if [ -n "$ADVERTISE_HOST" ]; then
  ARGS+=(--advertise-host "$ADVERTISE_HOST")
fi

python "${ARGS[@]}"
