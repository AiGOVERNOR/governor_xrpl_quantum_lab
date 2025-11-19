import json

from ecosystem.orchestrator import run_vqm_cycle


def main() -> None:
    state = run_vqm_cycle()
    print(json.dumps(state, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
