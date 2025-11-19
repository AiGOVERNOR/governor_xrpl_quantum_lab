#!/usr/bin/env bash
set -e

# Always run from repo root
cd "$(dirname "$0")/.."

echo "[VQM API] Starting on http://0.0.0.0:8000 ..."
nohup uvicorn vqm_api:app --host 0.0.0.0 --port 8000 > vqm_api.log 2>&1 &

PID=$!
echo "[VQM API] Started with PID ${PID}"
echo "[VQM API] Logs: vqm_api.log"
