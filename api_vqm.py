from fastapi import FastAPI

from ecosystem.pipeline_v5 import run_vqm_cycle_v5

app = FastAPI(
    title="VQM XRPL Guardian API",
    version="5.1.0",
    description=(
        "Read-only VQM XRPL intelligence API. "
        "No trading, no transaction submission."
    ),
)


@app.get("/")
def root() -> dict:
    return {
        "service": "vqm_xrpl_guardian",
        "version": "5.1.0",
        "read_only": True,
        "trading_enabled": False,
    }


@app.get("/vqm/state")
def vqm_state() -> dict:
    """
    Full pipeline_v5 state. This is what the SDK's HTTP
    mode expects to consume.
    """
    return run_vqm_cycle_v5()


@app.get("/vqm/network")
def vqm_network() -> dict:
    """
    XRPL network snapshot only.
    """
    state = run_vqm_cycle_v5()
    return state.get("network_state", {})


@app.get("/vqm/guardian")
def vqm_guardian() -> dict:
    """
    Guardian decision + safety info only.
    """
    state = run_vqm_cycle_v5()
    return state.get("guardian", {})


@app.get("/vqm/safety")
def vqm_safety() -> dict:
    """
    Compact safety view: network + safety + hard guarantees.
    """
    state = run_vqm_cycle_v5()
    guardian = state.get("guardian", {})
    return {
        "network_state": state.get("network_state", {}),
        "safety": guardian.get("safety"),
        "hard_guarantees": guardian.get("hard_guarantees"),
    }
