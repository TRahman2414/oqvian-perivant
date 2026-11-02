#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd "$(dirname "$0")/.." && pwd)"

if [[ ! -d "$project_dir/backend/.venv" ]]; then
  python3 -m venv "$project_dir/backend/.venv"
  "$project_dir/backend/.venv/bin/pip" install -e "$project_dir/backend/"
fi
if [[ ! -x "$project_dir/frontend/node_modules/.bin/vite" ]]; then
  (cd "$project_dir/frontend" && npm ci)
fi

"$project_dir/backend/.venv/bin/uvicorn" app.main:app --app-dir "$project_dir/backend" --host 127.0.0.1 --port 8010 &
backend_pid=$!
(cd "$project_dir/frontend" && "$project_dir/frontend/node_modules/.bin/vite" --config "$project_dir/frontend/vite.config.ts" --host 127.0.0.1 --port 4173 --strictPort) &
frontend_pid=$!
cleanup() {
  kill "$frontend_pid" "$backend_pid" 2>/dev/null || true
  wait "$frontend_pid" "$backend_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM
printf 'OQVIAN PERIVANT UI:  http://127.0.0.1:4173\n'
printf 'OQVIAN PERIVANT API: http://127.0.0.1:8010/docs\n'
wait -n "$backend_pid" "$frontend_pid"
