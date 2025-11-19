import json

from ecosystem.orchestrator import run_vqm_cycle


def main() -> None:
    """
    Simple CLI entrypoint for the VQM XRPL ecosystem.

    It runs a single VQM cycle and prints a JSON document containing:
      - pipeline_version
      - timestamp
      - network_state
      - guardian (mesh + policy + llm + forge)
    """
    state = run_vqm_cycle()
    print(json.dumps(state, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
