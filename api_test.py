from fastapi import FastAPI

from agents.vqm_xrpl_agent import VQM_XRPL_Agent, VQM_XRPL_Agent_Config
from vqm_mesh import VQMMesh

app = FastAPI(
    title="Governor XRPL Quantum Lab",
    version="0.1.0",
    description="XRPL fee intelligence + VQM Mesh control surface."
)

# --- Singletons: keep one XRPL agent + one Mesh in memory ---
xrpl_agent = VQM_XRPL_Agent(VQM_XRPL_Agent_Config())
mesh = VQMMesh()


@app.get("/")
def root():
    return {
        "status": "XRPL Quantum Mesh Online",
        "services": [
            "/xrpl/snapshot",
            "/mesh/pulse",
        ],
    }


@app.get("/xrpl/snapshot")
def xrpl_snapshot():
    """
    Live XRPL network snapshot from the VQM_XRPL_Agent.
    """
    return xrpl_agent.get_network_snapshot()


@app.get("/mesh/pulse")
def mesh_pulse():
    """
    Run a full VQM Mesh optimization across all agents
    and return the mesh's global coordination output.
    """
    return mesh.optimize()
