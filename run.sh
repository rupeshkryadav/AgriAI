#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
python -m pip install -r "$ROOT/backend/requirements.txt"
python "$ROOT/backend/ml/setup_and_train.py"
python -m uvicorn app.main:app --app-dir "$ROOT/backend" --host 0.0.0.0 --port 8000 &
API_PID=$!
trap 'kill "$API_PID" 2>/dev/null || true' EXIT
cd "$ROOT/frontend"
npm install
npm run dev -- --host 0.0.0.0
