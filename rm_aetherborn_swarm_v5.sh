#!/data/data/com.termux/files/usr/bin/bash
set -e

cd "$(dirname "$0")"

TARGET="ecosystem/agents/aetherborn_swarm.py"

if [ -f "$TARGET" ]; then
  rm "$TARGET"
  echo "Removed $TARGET (AETHERBORN SWARM v5.0)."
else
  echo "No $TARGET found – nothing to delete."
fi

