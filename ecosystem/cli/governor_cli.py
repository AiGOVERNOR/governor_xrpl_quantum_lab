import json

try:
    # Preferred: VQM pipeline v5 (with structural intelligence)
    from ecosystem.pipeline_v5 import run_vqm_cycle_v5 as run_vqm_cycle
except Exception:
    # Fallback to previous layers if needed
    try:
        from ecosystem.pipeline_v4 import run_vqm_cycle_v4 as run_vqm_cycle
    except Exception:
        from ecosystem.orchestrator import run_vqm_cycle  # type: ignore


def main() -> None:
    state = run_vqm_cycle()
    print(json.dumps(state, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
