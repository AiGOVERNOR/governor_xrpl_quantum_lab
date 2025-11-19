#!/usr/bin/env bash
set -e

echo "[DELETE] Removing VQM Level 4–6 pipeline layers..."

rm -f ecosystem/predictive.py
rm -f ecosystem/scheduler.py
rm -f ecosystem/mesh_intents.py
rm -f ecosystem/pipeline_v4.py

echo "[INFO] Level 4–6 modules removed."
echo "[INFO] CLI will automatically fall back to ecosystem.orchestrator.run_vqm_cycle()."

