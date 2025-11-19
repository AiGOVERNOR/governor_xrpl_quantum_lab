from fastapi import FastAPI

from ecosystem.orchestrator import run_vqm_cycle

app = FastAPI(
    title="Governor XRPL VQM Ecosystem",
    version="0.1.0",
    description="Mainnet-aware AI VQM mesh for XRPL (proposal-only mode).",
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "component": "vqm_ecosystem"}


@app.get("/mesh")
def mesh() -> dict:
    """
    Return the full mesh pulse:
    - network_state
    - tools
    - proposals
    """
    return run_vqm_cycle()


@app.get("/proposals")
def proposals() -> list[dict]:
    """
    Convenience endpoint returning just the proposals.
    """
    state = run_vqm_cycle()
    return state.get("proposals", [])
