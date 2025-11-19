import json
from typing import Any, Dict


def _resolve_pipeline() -> Any:
    """
    Prefer the most advanced pipeline available:

    1. pipeline_v8 (GENIUSCODEPROMPTV8)
    2. pipeline_v4
    3. orchestrator.run_vqm_cycle
    """
    # V8
    try:
        from ecosystem.pipeline_v8 import run_vqm_cycle_v8

        return run_vqm_cycle_v8
    except Exception:
        pass

    # V4
    try:
        from ecosystem.pipeline_v4 import run_vqm_cycle_v4

        return run_vqm_cycle_v4
    except Exception:
        pass

    # Base
    from ecosystem.orchestrator import run_vqm_cycle

    return run_vqm_cycle


def main() -> None:
    pipeline = _resolve_pipeline()
    state: Dict[str, Any] = pipeline()
    print(json.dumps(state, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
