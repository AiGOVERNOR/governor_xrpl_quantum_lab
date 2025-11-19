"""
VQM Pipeline v4 / v5 / v6 wrapper.

Builds on the existing orchestrator.run_vqm_cycle() and layers:

- Level 4: Predictive Fee Horizon
- Level 5: Adaptive Scheduler
- Level 6: Mesh Intent Router

No signing, no trading. This is a pure planning & guidance layer.
"""

from copy import deepcopy
from typing import Any, Dict

from ecosystem.predictive import FeeHorizonModel
from ecosystem.scheduler import AdaptiveScheduler
from ecosystem.mesh_intents import MeshIntentRouter
from ecosystem.orchestrator import run_vqm_cycle as base_run_vqm_cycle

# Single in-process instances so they can keep light history.
_fee_horizon_model = FeeHorizonModel()
_scheduler = AdaptiveScheduler()
_mesh_router = MeshIntentRouter()


def run_vqm_cycle_v4() -> Dict[str, Any]:
    """
    Extended cycle:

    1. Call the existing orchestrator (Level 1–3).
    2. Feed network_state into Level 4 model.
    3. Build Level 5 adaptive schedule.
    4. Build Level 6 mesh intent.

    Returns a dict superset of the original orchestrator output.
    """
    base_state = base_run_vqm_cycle()
    # Copy to avoid mutating the original state in unexpected places.
    state: Dict[str, Any] = deepcopy(base_state)

    network_state = state.get("network_state", {}) or {}

    # Level 4: predictive horizon
    fee_horizon = _fee_horizon_model.update_and_forecast(network_state)

    # Level 5: scheduler
    schedule = _scheduler.plan(fee_horizon=fee_horizon, network_state=network_state)

    # Level 6: mesh intent
    mesh_intent = _mesh_router.route(
        network_state=network_state,
        fee_horizon=fee_horizon,
        schedule=schedule,
    )

    # Attach to state
    state["fee_horizon"] = fee_horizon
    state["scheduler"] = schedule
    state["mesh_intent"] = mesh_intent

    # Bump pipeline version
    state["pipeline_version"] = "1.6.0"

    return state
