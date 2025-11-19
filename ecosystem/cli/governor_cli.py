from __future__ import annotations

import json

# Prefer the newest pipeline; fall back safely if import fails.
try:
    from ecosystem.pipeline_v9 import run_vqm_cycle_v9 as run_vqm_cycle
except Exception:
    try:
        from ecosystem.pipeline_v4 import run_vqm_cycle_v4 as run_vqm_cycle
    except Exception:
        from ecosystem.orchestrator import run_vqm_cycle  # ultimate fallback


def main() -> None:
    state = run_vqm_cycle()
    print(json.dumps(state, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
