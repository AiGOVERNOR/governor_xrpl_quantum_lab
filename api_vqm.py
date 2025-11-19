"""
VQM HTTP API – Read-only XRPL Super-Brain

This API exposes:
- Full VQM state (pipeline v4)
- Network state only
- Mesh intent
- Council view
- Scheduler plan

SAFE: no signing, no trading, no on-chain writes.
"""

from typing import Any, Dict

from fastapi import FastAPI

from ecosystem.pipeline_v4 import run_vqm_cycle_v4


app = FastAPI(
    title="XRPL VQM Super-Brain API",
    version="2.0.0",
    description=(
        "Read-only API for the VQM XRPL observer: network state, fee horizon, "
        "council decisions, mesh intent, and scheduler hints."
    ),
)


def _current_state() -> Dict[str, Any]:
    """
    Single entry point for pulling the latest VQM pipeline v4 state.
    """
    return run_vqm_cycle_v4()


@app.get("/")
def root() -> Dict[str, Any]:
    """
    Basic liveness check.
    """
    return {
        "status": "ok",
        "message": "XRPL VQM Super-Brain online (read-only).",
    }


@app.get("/vqm/state")
def get_full_state() -> Dict[str, Any]:
    """
    Full VQM v4 state payload.

    Includes:
      - network_state
      - guardian
      - fee_horizon
      - council
      - mesh_intent
      - scheduler
      - tools
      - memory meta
    """
    return _current_state()


@app.get("/vqm/network")
def get_network_state() -> Dict[str, Any]:
    """
    Just the XRPL network_state section.
    """
    state = _current_state()
    return {
        "network_state": state.get("network_state", {}),
        "pipeline_version": state.get("pipeline_version"),
        "timestamp": state.get("timestamp"),
    }


@app.get("/vqm/mesh_intent")
def get_mesh_intent() -> Dict[str, Any]:
    """
    How the super-brain thinks the ecosystem should behave.
    """
    state = _current_state()
    return {
        "mesh_intent": state.get("mesh_intent", {}),
        "fee_horizon": state.get("fee_horizon", {}),
        "network_state": state.get("network_state", {}),
    }


@app.get("/vqm/council")
def get_council_view() -> Dict[str, Any]:
    """
    Council votes + aggregate view.
    """
    state = _current_state()
    return {
        "council": state.get("council", {}),
        "network_state": state.get("network_state", {}),
        "fee_horizon": state.get("fee_horizon", {}),
    }


@app.get("/vqm/scheduler")
def get_scheduler_plan() -> Dict[str, Any]:
    """
    Suggested scheduler plan for internal jobs.

    Still advisory and off-chain. This only returns a JSON plan.
    """
    state = _current_state()
    return {
        "scheduler": state.get("scheduler", {}),
        "mesh_intent": state.get("mesh_intent", {}),
        "network_state": state.get("network_state", {}),
    }
