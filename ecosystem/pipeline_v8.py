from __future__ import annotations

from typing import Any, Dict

from ecosystem.neural import build_neuromesh_state
from ecosystem.meta_advisors import (
    advise_fee_strategy,
    advise_network_posture,
)
from ecosystem.context_engine import build_context


def _base_pipeline() -> Dict[str, Any]:
    """
    Try to use the most advanced existing pipeline;
    fall back gracefully if unavailable.
    """
    try:
        from ecosystem.pipeline_v4 import run_vqm_cycle_v4  # type: ignore

        return run_vqm_cycle_v4()
    except Exception:
        # Fall back to the original orchestrator-only view
        from ecosystem.orchestrator import run_vqm_cycle  # type: ignore

        return run_vqm_cycle()


def run_vqm_cycle_v8() -> Dict[str, Any]:
    """
    GENIUSCODEPROMPTV8 pipeline.

    - Calls the underlying VQM pipeline (v4 or base)
    - Builds NeuroMesh
    - Runs meta-advisors
    - Builds global context
    """
    base = _base_pipeline()

    neuro = build_neuromesh_state(base)
    fee_meta = advise_fee_strategy(neuro, base)
    net_meta = advise_network_posture(neuro, base)

    meta = {"fee": fee_meta, "network": net_meta}
    context = build_context(base, neuro, meta)

    # Merge everything into a single state object
    merged = dict(base)
    merged["neuro_mesh"] = neuro
    merged["meta"] = meta
    merged["context"] = context
    merged["pipeline_version"] = "1.8.0"

    return merged
