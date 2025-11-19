#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/.."

echo "[DELETE] Removing VQM API artifacts..."

rm -f vqm_api.py
rm -f vqm_api.log

echo "[DELETE] NOTE: If uvicorn is still running, stop it manually:"
echo "    ps -A | grep uvicorn"
echo "    kill -9 <PID>"
echo "[DELETE] VQM Phase 2 API files removed."
