#!/usr/bin/env bash
set -e

echo "[DELETE] Removing VQM pipeline modules..."

rm -f ecosystem/orchestrator.py
rm -f ecosystem/guardian.py

rm -rf ecosystem/pipelines
rm -rf ecosystem/protocols

rm -rf data/xrpl_vqm_telemetry.log
rm -rf code_proposals

echo "[DELETE] Done. You may also clean up imports in other files if needed."
