"""
VQM Integrators SDK

Thin client for talking to the VQM API (api_vqm.py).
All methods are read-only and safe for mainnet telemetry.

Usage:

    from sdk.client import VQMClient

    client = VQMClient(base_url="http://localhost:8000")
    state = client.get_state()
    print(state["network_state"])
"""
from .client import VQMClient  # noqa: F401
