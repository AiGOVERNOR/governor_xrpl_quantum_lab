"""
ecosystem.cli.governor_cli

CLI entrypoint for the VQM ecosystem.

- Runs the latest available VQM pipeline (v4 if present, else base).
- Enriches the output with VQM scoring metadata:
  * scores.global_confidence
  * per-tool score_meta.effective_score
"""

import json

try:
    # Preferred: upgraded pipeline with Guardian + Horizon
    from ecosystem.pipeline_v4 import run_vqm_cycle_v4 as run_vqm_cycle  # type: ignore
except Exception:
    # Fallback: base orchestrator pipeline
    from ecosystem.orchestrator import run_vqm_cycle  # type: ignore

try:
    from ecosystem.scoring import enrich_with_scores
except Exception:
    # Hard fallback: identity function if scoring is missing
    def enrich_with_scores(state):
        return state


def main() -> None:
    state = run_vqm_cycle()
    state = enrich_with_scores(state)
    print(json.dumps(state, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
