#!/usr/bin/env bash
set -e

echo "[DELETE] Removing Protocol Graph Layer..."

rm -f ecosystem/tx/graph.py
rm -f ecosystem/cli/protocol_graph_cli.py
rm -f ecosystem/sdk/protocol_graph_adapter.py

echo "[DELETE] Done. You may also remove any imports of:",
echo "  - ecosystem.tx.graph.protocol_graph"
echo "  - ecosystem.sdk.protocol_graph_adapter"
