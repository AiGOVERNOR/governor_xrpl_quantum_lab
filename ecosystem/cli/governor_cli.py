"""
Governor CLI entrypoint for the VQM Ecosystem.

Attempts to use the extended Level 4–6 pipeline. If unavailable,
falls back to the base orchestrator.
"""

import json
from typing import Any, Dict

try:
    # Preferred: extended pipeline with Level 4/5/6 intelligence
    from ecosystem.pipeline_v4 import run_vqm_cycle_v4 as run_vqm_cycle
except Exception:
    # Fallback: original orchestrator (Level 1–3)
    from ecosystem.orchestrator import run_vqm_cycle  # type: ignore


def main() -> None:
    state: Dict[str, Any] = run_vqm_cycle()
    print(json.dumps(state, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
