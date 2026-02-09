#!/usr/bin/env sh
set -eu

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8002}"

exec uvicorn app.main:app --host "${HOST}" --port "${PORT}"

