"""
VQM Pipeline v5 – Cognitive Mesh Overlay

This layer:
- Calls the existing base pipeline (v4 or orchestrator).
- Logs compact snapshots to disk.
- Runs CognitiveMeshBrain over recent history.
- Returns the base state plus a `cognitive_mesh` block.

Read-only, mainnet-friendly, no signing, no trading.
"""

from __future__ import annotations

from typing import Any, Dict

try:
    # Preferred: use the upgraded v4 pipeline if present
    from ecosystem.pipeline_v4 import run_vqm_cycle_v4 as base_run_vqm_cycle
except Exception:  # pragma: no cover
    # Fallback: direct orchestrator hook
    from ecosystem.orchestrator import run_vqm_cycle as base_run_vqm_cycle  # type: ignore

from ecosystem.cognitive.mesh_brain import CognitiveMeshBrain
from ecosystem.cognitive.state_cache import append_and_load


def _compact_snapshot(full_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a compact snapshot for disk storage – no huge blobs,
    just the key telemetry and guardian/mode info.
    """
    return {
        "pipeline_version": full_state.get("pipeline_version"),
        "timestamp": full_state.get("timestamp"),
        "network_state": full_state.get("network_state"),
        "guardian": full_state.get("guardian"),
        "fee_horizon": full_state.get("fee_horizon"),
        "mesh_intent": full_state.get("mesh_intent"),
    }


def run_vqm_cycle_v5() -> Dict[str, Any]:
    """
    Run base VQM cycle and augment it with Cognitive Mesh context.
    """
    base_state: Dict[str, Any] = base_run_vqm_cycle()

    # compact snapshot + history
    snapshot = _compact_snapshot(base_state)
    history = append_and_load(snapshot, max_items=256)

    brain = CognitiveMeshBrain()
    signal = brain.analyze(history)

    base_state["cognitive_mesh"] = {
        "scope": signal.scope,
        "version": signal.version,
        "global_mode": signal.global_mode,
        "volatility": signal.volatility,
        "fee_trend": signal.fee_trend,
        "guardian_modes": signal.guardian_modes,
        "narrative": signal.narrative,
        "history_size": len(history),
    }

    # bump pipeline version so you can see v5 in the output
    base_state["pipeline_version"] = "2.0.0"

    return base_state
