"""
VQM Mainnet Brain – HTTP API (v1)

This FastAPI app exposes a read-only interface to the VQM ecosystem:

- /health           : basic health check
- /v1/state         : full pipeline snapshot (single cycle)
- /v1/guardian      : guardian / policy block
- /v1/tools         : tools registry
- /v1/fee-horizon   : fee horizon struct (if present)
- /v1/scheduler     : scheduler advice (if present)

Everything here is:
- Read-only
- Non-custodial
- No trading, no tx submission, no signing
"""

from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException

# Prefer the advanced pipeline_v4, but fall back to the base orchestrator.
try:  # pragma: no cover - dynamic wiring
    from ecosystem.pipeline_v4 import run_vqm_cycle_v4 as run_vqm_cycle
    PIPELINE_VERSION = "v4"
except Exception:  # pragma: no cover
    from ecosystem.orchestrator import run_vqm_cycle  # type: ignore
    PIPELINE_VERSION = "base"

app = FastAPI(
    title="Governor VQM API",
    version="1.0.0",
    description=(
        "Read-only XRPL VQM brain. Streams network-aware policy, guardian output, "
        "fee bands, and scheduler advice. No signing, no trading."
    ),
)


def _safe_cycle() -> Dict[str, Any]:
    """
    Run one VQM pipeline cycle and validate the basic shape.
    """
    try:
        state = run_vqm_cycle()
    except Exception as exc:  # pragma: no cover - runtime failure
        raise HTTPException(status_code=500, detail=f"VQM pipeline error: {exc!r}")

    if not isinstance(state, dict):
        raise HTTPException(
            status_code=500,
            detail="VQM pipeline returned non-dict state.",
        )
    return state


@app.get("/health")
def health() -> Dict[str, Any]:
    """
    Simple liveness + pipeline wiring check.
    """
    try:
        state = run_vqm_cycle()
        network_state = state.get("network_state", {})
    except Exception:
        network_state = {}

    return {
        "status": "ok",
        "pipeline": PIPELINE_VERSION,
        "has_network_state": bool(network_state),
    }


@app.get("/v1/state")
def get_state() -> Dict[str, Any]:
    """
    Full VQM state. This is the core API call.
    """
    return _safe_cycle()


@app.get("/v1/guardian")
def get_guardian() -> Dict[str, Any]:
    """
    Guardian block: policy, forge, mesh, llm.
    """
    state = _safe_cycle()
    guardian = state.get("guardian")
    if guardian is None:
        raise HTTPException(status_code=404, detail="guardian block not present in state")
    return guardian


@app.get("/v1/tools")
def get_tools() -> Dict[str, Any]:
    """
    Tools registry: list of tools with scores and metadata.
    """
    state = _safe_cycle()
    tools = state.get("tools")
    if tools is None:
        raise HTTPException(status_code=404, detail="tools not present in state")
    return {"tools": tools}


@app.get("/v1/fee-horizon")
def get_fee_horizon() -> Dict[str, Any]:
    """
    Optional: fee horizon / trends block if the pipeline exposes it.

    Returns 404 if the upstream has no 'fee_horizon' key.
    """
    state = _safe_cycle()
    horizon = state.get("fee_horizon")
    if horizon is None:
        raise HTTPException(status_code=404, detail="fee_horizon not present in state")
    return horizon


@app.get("/v1/scheduler")
def get_scheduler() -> Dict[str, Any]:
    """
    Optional: scheduler advice block.

    Returns 404 if missing.
    """
    state = _safe_cycle()
    sched = state.get("scheduler")
    if sched is None:
        raise HTTPException(status_code=404, detail="scheduler not present in state")
    return sched
