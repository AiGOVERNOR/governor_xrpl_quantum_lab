#!/usr/bin/env bash
set -e

echo "[DELETE] Removing VQM scoring layer (ecosystem.scoring + CLI wiring)..."

# Remove scoring module
rm -f ecosystem/scoring.py

# Restore a simple governor_cli that just prints the pipeline output
cat > ecosystem/cli/governor_cli.py << 'EOC'
"""
ecosystem.cli.governor_cli (restored)

Simple CLI: runs the best-available VQM pipeline and prints JSON.
"""

import json

try:
    from ecosystem.pipeline_v4 import run_vqm_cycle_v4 as run_vqm_cycle  # type: ignore
except Exception:
    from ecosystem.orchestrator import run_vqm_cycle  # type: ignore


def main() -> None:
    state = run_vqm_cycle()
    print(json.dumps(state, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
EOC

echo "[DELETE] Done. You can now: git status && git add -A && git commit -m 'Remove VQM scoring layer'"
